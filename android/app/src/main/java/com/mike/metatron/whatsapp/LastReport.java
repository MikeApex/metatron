package com.mike.metatron.whatsapp;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

/**
 * The last run, as kept on the phone for the WhatsApp screen (plan § 8 "Last run report"):
 * {@code wa_state/last_report.json}, overwritten each run, deleted by "Turn off". <b>Counts, codes
 * and labels only — never a message's text, never a sender.</b>
 *
 * <p>It holds the run's {@link RunReport}; for a dry run, what it would have sent per chat
 * (labelled by {@link ShareList#label} — the user's own contact name or the group subject, which
 * never leave the phone) and the notices it would have raised. At most {@value #MAX_CHATS}
 * chats, each label cut to {@value #MAX_LABEL} characters, so the file stays near 1 KB.
 */
final class LastReport {
    static final String FILE = "last_report.json";
    static final int MAX_CHATS = 12;
    static final int MAX_LABEL = 32;

    /** What one shared chat would have sent. */
    static final class ChatCount {
        final String label;
        long messages, updates, replyMarkers;

        ChatCount(String label) {
            this.label = label;
        }

        long total() {
            return messages + updates + replyMarkers;
        }
    }

    final RunReport report;
    final List<ChatCount> chats;
    /** {@link Notices.Notice} names a dry run would have raised. Empty for a real run (it raised them). */
    final List<String> wouldRaise;

    LastReport(RunReport report, List<ChatCount> chats, List<String> wouldRaise) {
        this.report = report;
        this.chats = Collections.unmodifiableList(new ArrayList<>(chats));
        this.wouldRaise = Collections.unmodifiableList(new ArrayList<>(wouldRaise));
    }

    String toJson() {
        JsonOut.Arr cs = JsonOut.arr();
        int n = 0;
        for (ChatCount c : chats) {
            if (n++ >= MAX_CHATS) break;
            cs.add(JsonOut.obj().put("label", cutLabel(c.label)).put("messages", c.messages)
                    .put("updates", c.updates).put("reply_markers", c.replyMarkers));
        }
        JsonOut.Arr w = JsonOut.arr();
        for (String s : wouldRaise) w.add(s);
        return JsonOut.obj().put("v", 1).put("report", report.toJson()).put("chats", cs).put("would_raise", w).toString();
    }

    /** Null when absent or not exactly this shape. */
    static LastReport fromJson(String json) {
        if (json == null) return null;
        Object v;
        try {
            v = Json.parse(json);
        } catch (Json.Malformed e) {
            return null;
        }
        if (!(v instanceof Map)) return null;
        Map<?, ?> m = (Map<?, ?>) v;
        if (!Long.valueOf(1).equals(m.get("v")) || !(m.get("report") instanceof String)) return null;
        RunReport r = RunReport.fromJson((String) m.get("report"));
        if (r == null) return null;
        List<ChatCount> chats = new ArrayList<>();
        if (m.get("chats") instanceof List) {
            for (Object o : (List<?>) m.get("chats")) {
                if (!(o instanceof Map)) continue;
                Map<?, ?> c = (Map<?, ?>) o;
                if (!(c.get("label") instanceof String)) continue;
                ChatCount cc = new ChatCount((String) c.get("label"));
                cc.messages = num(c, "messages");
                cc.updates = num(c, "updates");
                cc.replyMarkers = num(c, "reply_markers");
                chats.add(cc);
            }
        }
        List<String> would = new ArrayList<>();
        if (m.get("would_raise") instanceof List) {
            for (Object o : (List<?>) m.get("would_raise")) if (o instanceof String) would.add((String) o);
        }
        return new LastReport(r, chats, would);
    }

    void save(File stateDir) {
        NightlyState.writeAtomically(new File(stateDir, FILE), toJson().getBytes(StandardCharsets.UTF_8));
    }

    static LastReport load(File stateDir) {
        byte[] raw = NightlyState.read(new File(stateDir, FILE));
        return raw == null ? null : fromJson(new String(raw, StandardCharsets.UTF_8));
    }

    /** The screen's lines — code-written words around counts and labels. */
    List<String> lines(TimeZone tz) {
        List<String> out = new ArrayList<>();
        SimpleDateFormat f = new SimpleDateFormat("EEE d MMM, HH:mm", Locale.getDefault());
        f.setTimeZone(tz);
        RunReport r = report;
        boolean dry = r.dryRun == 1;
        out.add((dry ? "Last dry run: " : "Last run: ") + f.format(new Date(r.runAt * 1000L))
                + (r.error.isEmpty() ? "" : " — stopped: " + reason(r.error)));
        if (r.backupWritten > 0) out.add("WhatsApp last backed up: " + f.format(new Date(r.backupWritten * 1000L)));
        out.add("Read: " + r.baseReceived + " received in the full backup (" + r.baseReceivedText + " with text), "
                + r.incReceived + " in the nightly backups (" + r.incReceivedText + " with text)");
        long odd = r.withoutKeyId + r.withoutChat + r.textUndecodable + r.baseKeyCollisions;
        if (odd > 0) {
            out.add("Unreadable rows: " + r.withoutKeyId + " without an id, " + r.withoutChat + " without a chat, "
                    + r.textUndecodable + " undecodable texts, " + r.baseKeyCollisions + " duplicate ids");
        }
        out.add((dry ? "Would send: " : "Sent: ") + r.postedMessages + " messages, " + r.postedUpdates + " updates, "
                + r.postedReplyMarkers + " reply markers; " + r.skippedUnchanged + " unchanged"
                + (dry ? "" : "; " + r.rejected + " rejected, " + r.droppedNotShared + " dropped"));
        if (dry) {
            out.add("Nothing was sent to Metatron.");
            for (ChatCount c : chats) {
                String label = c.label.isEmpty() ? "A chosen chat" : c.label;
                out.add("  " + label + ": " + c.messages + " messages, " + c.updates + " updates, "
                        + c.replyMarkers + " reply markers");
            }
            for (String n : wouldRaise) {
                try {
                    out.add("Would warn: " + Notices.title(Notices.Notice.valueOf(n)));
                } catch (IllegalArgumentException ignored) {
                    // a notice this build does not know
                }
            }
        }
        return out;
    }

    /** A code's words for the screen: a {@link BackupError}'s userText, else a written line per code. */
    static String reason(String code) {
        for (BackupError e : BackupError.values()) if (e.code.equals(code)) return e.userText;
        switch (code) {
            case RunReport.IO_ERROR: return "the phone could not read or write a file";
            case RunReport.SHARE_OUT_OF_STEP: return Notices.title(Notices.Notice.SHARE_OUT_OF_STEP);
            case RunReport.POST_FAILED: return "Metatron could not be reached";
            case NightlyRead.NO_KEY: return "no backup key is stored";
            case NightlyRead.NO_ACCESS: return "All-files access is not allowed";
            default: return code;
        }
    }

    static String cutLabel(String s) {
        if (s == null) return "";
        if (s.codePointCount(0, s.length()) <= MAX_LABEL) return s;
        return s.substring(0, s.offsetByCodePoints(0, MAX_LABEL));
    }

    private static long num(Map<?, ?> m, String k) {
        Object v = m.get(k);
        return v instanceof Long && (Long) v >= 0 ? (Long) v : 0;
    }

    /** Counts only. */
    @Override
    public String toString() {
        return "LastReport(" + (report.dryRun == 1 ? "dry" : "real") + ", " + chats.size() + " chats)";
    }
}
