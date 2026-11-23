package com.mike.metatron.whatsapp;

import java.io.File;
import java.io.UncheckedIOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

/**
 * One run of the nightly job, decided (plan §§ 3.2, 3.3, 3.5, 3.6) — plain Java over {@link Host},
 * so the order of a run, the dry run and every notice decision are unit-tested. {@link NightlyJob}
 * is the Android half: JobScheduler, the thread, the real {@link Host}.
 *
 * <p><b>Per run:</b> {@code GET /device/whatsapp/cursor} → the gate →
 * <ul>
 * <li><b>open:</b> {@link NightlyRead} (from cursor − 8 days, or now − 90 days) → <b>the share-list
 *     post, after the read</b> (verify 6) — anything but accepted means no events tonight → the
 *     events ({@link EventPlan}) → {@link Poster} → prune the sent-hash list to the newest cursor →
 *     {@code POST /device/whatsapp/run} → raise or clear the notices;</li>
 * <li><b>consent recorded, channel never yet open, and the user tapped "Dry run now" or is within
 *     7 days of the tap:</b> the dry run — read, combine and build from now − 90 days, and <b>post
 *     nothing, not even the share list or the report, and record nothing</b> in the sent-hash list.
 *     What it would have sent, per chat, and the notices it would have raised are kept for the
 *     screen ({@link LastReport});</li>
 * <li><b>anything else:</b> nothing is read. The gate has already disabled and cancelled what it
 *     must.</li>
 * </ul>
 * When the cursor call gets no answer the last known gate state decides: open → retry later; a
 * dry run still runs, since it needs nothing from the VM.
 */
final class NightlyRun {
    static final String CURSOR_PATH = "/device/whatsapp/cursor";
    static final String RUN_PATH = "/device/whatsapp/run";
    static final int REPORT_TIMEOUT_MS = 15_000;

    static final long STALE_BACKUP_SECONDS = 52 * 3600L;
    static final long STALE_FULL_BACKUP_SECONDS = 8 * 24 * 3600L;
    static final int TEXT_GONE_MIN_RECEIVED = 20;

    enum Trigger { NIGHT, DRY_TAP, APP_OPEN }

    /** What the run did. */
    enum Kind {
        /** A real read (successful or refused). */
        REAL,
        /** A dry run. */
        DRY,
        /** Nothing was read: the gate is shut, or no dry run is due. */
        NOTHING,
        /** Stopped by a cancel, or the VM could not be asked and the channel is open: see {@link Outcome#error}. */
        STOPPED
    }

    /** Everything a run needs from outside plain Java. */
    interface Host extends Poster.Host {
        long nowMs();

        /** The last known gate state, and whether the channel was ever open on this install. */
        Gate.State state();

        boolean everOpened();

        NightlyRead.Env readEnv();

        /**
         * The nightly share-list post ({@link ShareList#postNightly}); {@code migrationsOut} receives
         * the merges not yet accepted (from → to), which the sent-hash list follows (F2).
         */
        ShareList.Post postShareList(BackupCombiner.Combined combined, Map<String, String> hiddenToCanonical,
                                     Map<String, String> migrationsOut);

        Map<String, String> sharedKinds();

        Set<String> allowlist();

        String label(String canonicalChatId);

        /** The real sent-hash list (only ever opened when a salt exists, or for a real run). */
        SentHashes sent();

        /** {@code wa_state/}: the sent-hash list, the job state and the last report live here. */
        File stateDir();

        /** A folder for a throwaway sent-hash list, when a dry run finds none yet. Emptied after. */
        File dryScratchDir();

        void raise(Notices.Notice n);

        void clear(Notices.Notice n);
    }

    static final class Outcome {
        final Kind kind;
        /** The run's code: "" when clean. */
        final String error;
        /** The report as kept on the phone; null when none was made. */
        final RunReport report;

        Outcome(Kind kind, String error, RunReport report) {
            this.kind = kind;
            this.error = error;
            this.report = report;
        }

        @Override
        public String toString() {
            return "NightlyRun.Outcome(" + kind + (error.isEmpty() ? "" : ", " + error) + ")";
        }
    }

    private final Host h;

    NightlyRun(Host host) {
        this.h = host;
    }

    Outcome run(Trigger trigger) {
        final long now = h.nowMs();
        NightlyState st = NightlyState.update(h.stateDir(), s -> s.lastAttemptMs = now);

        DeviceApi.Result r = h.api().get(CURSOR_PATH);
        Gate.State gate = h.observe(r);
        if (h.cancelled()) return new Outcome(Kind.STOPPED, "", null);
        boolean answered = r.status == 200 || r.status == 401 || r.status == 403;
        Long cursor = null;
        if (r.status == 200) {
            Object[] c = parseCursor(r.body);
            if (c == null) answered = false;
            else cursor = (Long) c[0];
        }
        if (!answered) gate = h.state();

        if (gate == Gate.State.OPEN) {
            if (!answered) return new Outcome(Kind.STOPPED, RunReport.IO_ERROR, null);
            return real(cursor, now);
        }
        if (gate == Gate.State.CONSENTED_OFF && !h.everOpened()
                && (trigger == Trigger.DRY_TAP || NightlySchedule.inDryWindow(now, st.dryTapMs))) {
            return dry(now);
        }
        return new Outcome(Kind.NOTHING, "", null);
    }

    // ---- the real run --------------------------------------------------------------------------

    private Outcome real(Long cursor, long now) {
        RunReport rep = new RunReport();
        rep.runAt = now / 1000;
        NightlyRead.Result rd = NightlyRead.run(h.readEnv(), cursor, h.allowlist(), now, rep);
        if (rd.cancelled || h.cancelled()) return new Outcome(Kind.STOPPED, "", null);
        rememberBackupTimes(rep);
        if (!rd.ok()) return finishReal(rep, rd.error, false, false);

        Map<String, String> migrations = new LinkedHashMap<>();
        ShareList.Post share = h.postShareList(rd.combined, rd.hiddenToCanonical, migrations);
        if (h.cancelled()) return new Outcome(Kind.STOPPED, "", null);
        if (share != ShareList.Post.ACCEPTED) {
            // NOT_SAVED is not a refusal: no list the user saved here, so no events — the screen asks.
            String code = share == ShareList.Post.REFUSED ? RunReport.SHARE_OUT_OF_STEP
                    : share == ShareList.Post.FAILED ? RunReport.POST_FAILED : "";
            return finishReal(rep, code, true, false);
        }

        Map<String, String> kinds = h.sharedKinds();
        SentHashes sent;
        EventPlan plan;
        try {
            sent = h.sent();
            // The VM has forgotten everything (delete-all, or a fresh VM): nothing the phone
            // remembers sending is there, so nothing is skipped as already sent (F3). Only when the VM
            // once had a cursor for this install — a null cursor before any is just the first night,
            // and the live feed's keys from that day must survive it (verify NEW-1).
            if (cursor == null && NightlyState.load(h.stateDir()).cursorSeen > 0 && sent.size() > 0) sent.clear();
            if (cursor != null) {
                final long c = cursor;
                NightlyState.update(h.stateDir(), s -> s.cursorSeen = Math.max(s.cursorSeen, c));
            }
            // A chat that moved to its canonical id: what was sent under the old id is the same
            // message under the new one, not a new fact (F2). Every hidden id tonight's tables link,
            // not only the merges this night's post carried — a merge accepted from the screen, or a
            // run cancelled after its post, would otherwise leave keys under the old id (verify, F2
            // residual). Idempotent: an id with no keys renames nothing.
            for (Map.Entry<String, String> m : migrations.entrySet()) sent.rekeyChat(m.getKey(), m.getValue());
            for (Map.Entry<String, String> m : rd.hiddenToCanonical.entrySet()) {
                if (!m.getKey().equals(m.getValue())) sent.rekeyChat(m.getKey(), m.getValue());
            }
            plan = EventPlan.build(rd.combined.messages, sent, kinds, ReplyRule::isReply);
        } catch (UncheckedIOException e) {
            return finishReal(rep, RunReport.IO_ERROR, true, false);
        }
        rep.skippedUnchanged = plan.skippedUnchanged;
        rep.sameSecondGroups = EventPlan.sameSecondGroups(rd.combined.messages, kinds.keySet());

        Poster.Outcome po = Poster.post(h, sent, plan.events, cursor);
        rep.postedMessages = po.messages;
        rep.postedUpdates = po.updates;
        rep.postedReplyMarkers = po.replyMarkers;
        rep.rejected = po.rejected;
        rep.droppedNotShared = po.droppedNotShared;
        if (po.stopped || h.cancelled()) return new Outcome(Kind.STOPPED, "", null);

        long newest = Math.max(cursor == null ? 0 : cursor, po.cursorSent);
        if (newest > 0) {
            try {
                sent.prune(newest);
            } catch (UncheckedIOException ignored) {
                // Kept until the next prune; the list only grows by a night.
            }
        }
        return finishReal(rep, po.error, true, po.authEnded);
    }

    /** Post the report (unless the VM has just refused this device or channel), apply the notices, keep it. */
    private Outcome finishReal(RunReport rep, String error, boolean readDone, boolean authEnded) {
        rep.error = error;
        if (!authEnded) {
            h.observe(h.api().post(RUN_PATH, "{\"report\":" + rep.toJson() + "}", REPORT_TIMEOUT_MS));
        }
        NightlyState st = NightlyState.load(h.stateDir());
        Map<Notices.Notice, Boolean> d = decide(rep, readDone, h.nowMs() / 1000, st.backupWritten, st.fullBackupWritten);
        for (Map.Entry<Notices.Notice, Boolean> e : d.entrySet()) {
            if (e.getValue()) h.raise(e.getKey());
            else h.clear(e.getKey());
        }
        new LastReport(rep, Collections.<LastReport.ChatCount>emptyList(), Collections.<String>emptyList()).save(h.stateDir());
        if (error.isEmpty()) markSuccess();
        return new Outcome(Kind.REAL, error, rep);
    }

    // ---- the dry run ---------------------------------------------------------------------------

    private Outcome dry(long now) {
        RunReport rep = new RunReport();
        rep.runAt = now / 1000;
        rep.dryRun = 1;
        NightlyRead.Result rd = NightlyRead.run(h.readEnv(), null, h.allowlist(), now, rep);
        if (rd.cancelled || h.cancelled()) return new Outcome(Kind.STOPPED, "", null);
        rememberBackupTimes(rep);
        List<LastReport.ChatCount> chats = new ArrayList<>();
        if (rd.ok()) {
            Map<String, String> kinds = new HashMap<>(h.sharedKinds());
            // The share list would migrate these tonight (postNightly, F1); count them as it would.
            Map<String, String> migrations = new LinkedHashMap<>();
            for (Map.Entry<String, String> e : rd.hiddenToCanonical.entrySet()) {
                String k = kinds.get(e.getKey());
                if (k == null || e.getKey().equals(e.getValue())) continue;
                migrations.put(e.getKey(), e.getValue());
                if (!kinds.containsKey(e.getValue())) kinds.put(e.getValue(), k);
            }
            EventPlan plan;
            try {
                plan = dryPlan(rd.combined.messages, kinds, migrations);
            } catch (UncheckedIOException e) {
                rep.error = RunReport.IO_ERROR;
                plan = null;
            }
            if (plan != null) {
                rep.postedMessages = plan.messages;
                rep.postedUpdates = plan.updates;
                rep.postedReplyMarkers = plan.replyMarkers;
                rep.skippedUnchanged = plan.skippedUnchanged;
                rep.sameSecondGroups = EventPlan.sameSecondGroups(rd.combined.messages, kinds.keySet());
                chats = perChat(plan);
            }
        } else {
            rep.error = rd.error;
        }
        NightlyState seen = NightlyState.load(h.stateDir());
        Map<Notices.Notice, Boolean> d = decide(rep, rd.ok(), h.nowMs() / 1000, seen.backupWritten, seen.fullBackupWritten);
        List<String> would = new ArrayList<>();
        for (Map.Entry<Notices.Notice, Boolean> e : d.entrySet()) if (e.getValue()) would.add(e.getKey().name());
        new LastReport(rep, chats, would).save(h.stateDir());
        if (rep.error.isEmpty()) markSuccess();
        return new Outcome(Kind.DRY, rep.error, rep);
    }

    /**
     * The events a dry run would send, against the real sent-hash list read only — or, when none
     * exists yet, a throwaway one, so the dry run creates no salt and no list in {@code wa_state/}.
     * The night's migrations are applied to the throwaway list only: a dry run writes nothing to
     * the real one, and never clears it.
     */
    private EventPlan dryPlan(List<WaMessage> messages, Map<String, String> kinds, Map<String, String> migrations) {
        boolean none = !new File(h.stateDir(), SentHashes.SALT_FILE).isFile();
        if (!none) return EventPlan.build(messages, h.sent(), kinds, ReplyRule::isReply);
        SentHashes scratch = SentHashes.open(h.dryScratchDir());
        try {
            for (Map.Entry<String, String> m : migrations.entrySet()) scratch.rekeyChat(m.getKey(), m.getValue());
            return EventPlan.build(messages, scratch, kinds, ReplyRule::isReply);
        } finally {
            try {
                scratch.deleteAll();
            } catch (UncheckedIOException ignored) {
                // a throwaway salt and an empty list; the next dry run reuses the folder
            }
        }
    }

    /** Would-send per shared chat, by label, most first. Labels only — never an id, a text or a sender. */
    private List<LastReport.ChatCount> perChat(EventPlan plan) {
        Map<String, LastReport.ChatCount> byChat = new TreeMap<>();
        for (EventPlan.Event e : plan.events) {
            LastReport.ChatCount c = byChat.get(e.chat);
            if (c == null) {
                String label = h.label(e.chat);
                c = new LastReport.ChatCount(label == null ? "" : label);
                byChat.put(e.chat, c);
            }
            if (EventPlan.MESSAGE.equals(e.kind)) c.messages++;
            else if (EventPlan.UPDATE.equals(e.kind)) c.updates++;
            else c.replyMarkers++;
        }
        List<LastReport.ChatCount> out = new ArrayList<>(byChat.values());
        Collections.sort(out, (a, b) -> Long.compare(b.total(), a.total()));
        return out;
    }

    // ---- shared ----------------------------------------------------------------------------------

    private void rememberBackupTimes(final RunReport rep) {
        if (rep.backupWritten <= 0 && rep.fullBackupWritten <= 0) return;
        NightlyState.update(h.stateDir(), s -> {
            if (rep.backupWritten > 0) s.backupWritten = rep.backupWritten;
            if (rep.fullBackupWritten > 0) s.fullBackupWritten = rep.fullBackupWritten;
        });
    }

    private void markSuccess() {
        final long t = h.nowMs();
        NightlyState.update(h.stateDir(), s -> s.lastSuccessMs = t);
    }

    /** {cursor} — a Long, or null for the VM's {@code null}; null when the body is not that shape. */
    static Object[] parseCursor(String body) {
        Object v;
        try {
            v = Json.parse(body);
        } catch (Json.Malformed e) {
            return null;
        }
        if (!(v instanceof Map) || !((Map<?, ?>) v).containsKey("cursor")) return null;
        Object c = ((Map<?, ?>) v).get("cursor");
        if (c == null) return new Object[] {null};
        if (c instanceof Long && (Long) c > 0) return new Object[] {c};
        return null;
    }

    /** The codes a run reports that are the read itself refused — not retry-later, not a posting matter. */
    private static final Set<String> NOT_READ_REFUSALS = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            "", BackupError.BEING_WRITTEN.code, BackupError.NO_BACKUP_FOUND.code, RunReport.IO_ERROR,
            RunReport.SHARE_OUT_OF_STEP, RunReport.POST_FAILED)));

    /**
     * The notice decisions of one run (§ 3.6): true = raise, false = clear, absent = leave as is.
     * ({@code Notices} makes a raise a notification only on onset.)
     *
     * <ul>
     * <li>{@code BACKUP_STALE}: WhatsApp's last write of the set older than 52 h, or of the full
     *     backup older than 8 days — from this run's read, else the last times seen. Cleared when
     *     both known times are fresh. Left when none was ever seen.</li>
     * <li>{@code TEXT_GONE}: a completed read of ≥ 20 received rows with none carrying text.
     *     Cleared by a completed read with text.</li>
     * <li>{@code READ_REFUSED}: any refusal but the retry-later three (and the two posting codes,
     *     which are not the read). Cleared by a clean run.</li>
     * </ul>
     */
    static Map<Notices.Notice, Boolean> decide(RunReport r, boolean readDone, long nowSeconds,
                                               long lastBackupWritten, long lastFullBackupWritten) {
        Map<Notices.Notice, Boolean> out = new EnumMap<>(Notices.Notice.class);
        long bw = r.backupWritten > 0 ? r.backupWritten : lastBackupWritten;
        long fw = r.fullBackupWritten > 0 ? r.fullBackupWritten : lastFullBackupWritten;
        if (bw > 0 || fw > 0) {
            boolean stale = (bw > 0 && nowSeconds - bw > STALE_BACKUP_SECONDS)
                    || (fw > 0 && nowSeconds - fw > STALE_FULL_BACKUP_SECONDS);
            out.put(Notices.Notice.BACKUP_STALE, stale);
        }
        if (readDone) {
            long received = r.baseReceived + r.incReceived, text = r.baseReceivedText + r.incReceivedText;
            if (received >= TEXT_GONE_MIN_RECEIVED && text == 0) out.put(Notices.Notice.TEXT_GONE, true);
            else if (text > 0) out.put(Notices.Notice.TEXT_GONE, false);
        }
        if (r.error.isEmpty()) out.put(Notices.Notice.READ_REFUSED, false);
        else if (!NOT_READ_REFUSALS.contains(r.error)) out.put(Notices.Notice.READ_REFUSED, true);
        return out;
    }
}
