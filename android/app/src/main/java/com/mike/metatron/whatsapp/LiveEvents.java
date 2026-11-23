package com.mike.metatron.whatsapp;

import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.Iterator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.Executor;

/**
 * The live feed's decisions (build plan § 3.10), in plain Java so they run under the JVM tests.
 * {@link WaListener} is a thin adapter: it turns a {@code StatusBarNotification} into a
 * {@link Posted} and hands it here; everything that decides lives in this class.
 *
 * <p><b>What is sent.</b> A WhatsApp post that is not a group summary, carries a conversation
 * shortcut id, and whose chat the share list shares — canonicalised through the stored link map,
 * so a one-to-one under a hidden id the map does not link is left for the backup. Of its
 * messaging-style messages, each one received (not the user's own) with text: time floored to
 * the whole second, sender {@code ""} (no person key was observed, 10-30; the backup supplies a
 * group's sender as an {@code update} — review 2), text cut by {@link EventPlan#cut} and that cut
 * text hashed. Nothing else: no chat id, nothing sent.
 *
 * <p><b>The ordinal</b> is by arrival among the chat's received messages in that second, and stays
 * the same across re-posts — a notification re-shows earlier messages — by looking the text hash
 * up: in the sent-hash list (a message recorded as {@code chat|second|k} is that key and is not
 * sent again) and in this process's memo of what it has already placed (pending, recorded, or
 * given up). The j-th copy of one text in one second within a notification matches the j-th known
 * ordinal with that hash; a message with no known ordinal takes the smallest free one.
 *
 * <p><b>Posting.</b> Only while the gate is OPEN and the VM has accepted the current share-list
 * version; at once; {@code {"events": [...]}} with {@code "source": "live"} and no cursor (only
 * the nightly run moves the cursor). Every reply goes through {@link GateView#observe}. <b>A key
 * is recorded in the sent-hash list only when the VM took it</b>: a reply that counts any event as
 * {@code dropped_not_shared} records none of the post, and an event listed in {@code rejected} is
 * not recorded (verify 1) — so the backup sends it. A failure (no answer, 5xx, 429, a share list
 * not yet accepted) is retried <b>in memory</b> for {@link #RETRY_WINDOW_MS}, then left to the
 * backup. Text is never written to disk, logged or put in a notification; it lives only in a
 * pending item until that item is posted or given up.
 *
 * <p><b>Not here:</b> pruning the sent-hash list. Pruning is against the VM's cursor, which only
 * the nightly run moves, so the nightly run prunes.
 *
 * <p><b>Threads.</b> {@link #onPosted} and {@link #tick} return at once; the work runs on the given
 * executor — one global queue to canonicalise, then one queue per canonical chat, so a chat's
 * ordinals are placed and posted one at a time.
 */
public final class LiveEvents {
    public static final String WHATSAPP = "com.whatsapp";
    public static final String EVENTS_PATH = "/device/whatsapp/events";
    /** A failed post is retried in memory for this long after its message arrived, then left to the backup. */
    public static final long RETRY_WINDOW_MS = 10L * 60 * 1000;
    static final long FIRST_RETRY_GAP_MS = 15_000;
    static final long MAX_RETRY_GAP_MS = 2L * 60 * 1000;
    /** A live post is a handful of events; the VM translates each before replying. */
    static final int READ_TIMEOUT_MS = 30_000;
    static final int MAX_EVENTS_PER_POST = 100;
    /** Ordinals looked at per (chat, second). A second with more received messages than this is left to the backup. */
    static final int MAX_ORDINAL = 64;
    /**
     * How long this process remembers where it placed a message (hashes and ordinals only) — by
     * its <b>live</b> text hash, so a line re-shown after the nightly run sent an {@code update}
     * (which replaced the stored hash with the backup's text) still maps to its original key and
     * is not sent again (F7). Memory only.
     */
    static final long MEMO_MS = 72L * 3600 * 1000;
    /** At most this many memo entries per chat; past it, the oldest settled ones go (F7). */
    static final int MEMO_MAX = 5_000;

    // ---- what the adapter supplies -----------------------------------------------------------

    /** The share list, as the live feed needs it ({@link ShareList} on the phone). */
    public interface Shares {
        /** The canonical id for a notification's raw chat id when shared; null otherwise. */
        String canonicalShared(String rawChatId);

        /** "group" | "one_to_one" while shared; null once un-ticked. */
        String kindOf(String canonicalChatId);

        /** Whether the VM has accepted the list's current version. */
        boolean acceptedCurrent();
    }

    /** The consent gate ({@link Gate} on the phone). */
    public interface GateView {
        boolean open();

        /** Passes a reply through the gate; returns whether the gate is open after it. */
        boolean observe(DeviceApi.Result reply);
    }

    public interface Clock {
        long nowMs();
    }

    /** One messaging-style message as the notification carried it. {@link #toString()} carries no text. */
    public static final class Line {
        final long timeMs;
        final String text;
        final boolean own;

        public Line(long timeMs, String text, boolean own) {
            this.timeMs = timeMs;
            this.text = text;
            this.own = own;
        }

        @Override
        public String toString() {
            return "Line(" + (own ? "own" : "received") + ", " + (text == null ? "no text" : "text") + ")";
        }
    }

    /** One notification post, reduced to what the decisions need. {@link #toString()} carries no content. */
    public static final class Posted {
        final String packageName;
        final boolean summary;
        final String shortcutId;
        final List<Line> lines;

        public Posted(String packageName, boolean summary, String shortcutId, List<Line> lines) {
            this.packageName = packageName;
            this.summary = summary;
            this.shortcutId = shortcutId;
            this.lines = lines == null ? Collections.<Line>emptyList() : new ArrayList<>(lines);
        }

        @Override
        public String toString() {
            return "Posted(" + (summary ? "summary, " : "") + (shortcutId == null ? "no chat id, " : "")
                    + lines.size() + " lines)";
        }
    }

    /** What happened, counted. Counts only — no ids, no text. */
    public static final class Counts {
        public int ignoredOtherApp, ignoredGateClosed, summaries, noChatId, notShared;
        public int ownSkipped, noTextSkipped, alreadyKnown, ordinalOverflow;
        public int posts, recorded, droppedNotShared, rejected, retried, gaveUp, recordFailed, errors;

        @Override
        public synchronized String toString() {
            return "Counts(posts " + posts + ", recorded " + recorded + ", known " + alreadyKnown
                    + ", dropped " + droppedNotShared + ", rejected " + rejected + ", retried " + retried
                    + ", gave up " + gaveUp + ", not shared " + notShared + ", no chat id " + noChatId
                    + ", summaries " + summaries + ", errors " + errors + ")";
        }
    }

    // ---- state -------------------------------------------------------------------------------

    private static final int PENDING = 0, SENT = 1, GAVE_UP = 2;

    /** Where this process placed one message: its text hash and what became of it. */
    private static final class Memo {
        final byte[] textHash;
        int state;
        long atMs;

        Memo(byte[] textHash, int state, long atMs) {
            this.textHash = textHash;
            this.state = state;
            this.atMs = atMs;
        }
    }

    /** A message waiting to be posted. The only place text is held; dropped once posted or given up. */
    private static final class Pend {
        final String key;
        final long second;
        final int ordinal;
        String text;
        final byte[] textHash;
        final long arrivedMs;
        long nextAttemptMs;
        int attempts;

        Pend(String key, long second, int ordinal, String text, byte[] textHash, long arrivedMs) {
            this.key = key;
            this.second = second;
            this.ordinal = ordinal;
            this.text = text;
            this.textHash = textHash;
            this.arrivedMs = arrivedMs;
            this.nextAttemptMs = arrivedMs;
        }

        @Override
        public String toString() {
            return "Pend(second " + second + ", ordinal " + ordinal + ", attempts " + attempts + ")";
        }
    }

    /** One chat's memo and pending posts — touched only from that chat's queue. */
    private static final class Chat {
        final String id;
        final Serial queue;
        final Map<String, Memo> memo = new HashMap<>();
        final List<Pend> pending = new ArrayList<>();

        Chat(String id, Serial queue) {
            this.id = id;
            this.queue = queue;
        }
    }

    private final DeviceApi api;
    private final Clock clock;
    private final Shares shares;
    private final GateView gate;
    private final SentHashes sent;
    private final Executor pool;
    private final Serial intake;
    private final Map<String, Chat> chats = new ConcurrentHashMap<>();
    public final Counts counts = new Counts();

    public LiveEvents(DeviceApi api, Clock clock, Shares shares, GateView gate, SentHashes sent, Executor pool) {
        this.api = api;
        this.clock = clock;
        this.shares = shares;
        this.gate = gate;
        this.sent = sent;
        this.pool = pool;
        this.intake = new Serial(pool, counts);
    }

    // ---- entry points --------------------------------------------------------------------------

    /** A notification was posted. Returns at once; the work runs on the executor. */
    public void onPosted(Posted p) {
        intake.execute(() -> intake(p));
    }

    /** Retries what is due and gives up what is past the window. Called by a timer. */
    public void tick() {
        for (Chat c : chats.values()) c.queue.execute(() -> flush(c));
    }

    /** Messages waiting to be posted, across all chats. Counts only; for the adapter's timer and tests. */
    public int pendingCount() {
        int n = 0;
        for (Chat c : chats.values()) {
            synchronized (c) {
                n += c.pending.size();
            }
        }
        return n;
    }

    @Override
    public String toString() {
        return "LiveEvents(" + chats.size() + " chats, " + pendingCount() + " pending, " + counts + ")";
    }

    // ---- intake: which chat, if any ------------------------------------------------------------

    private void intake(Posted p) {
        synchronized (counts) {
            if (!WHATSAPP.equals(p.packageName)) { counts.ignoredOtherApp++; return; }
            if (p.summary) { counts.summaries++; return; }
            if (p.shortcutId == null || p.shortcutId.isEmpty()) { counts.noChatId++; return; }
        }
        if (!gate.open()) {
            bump(() -> counts.ignoredGateClosed++);
            return;
        }
        String canonical = shares.canonicalShared(p.shortcutId);
        if (canonical == null || canonical.isEmpty() || shares.kindOf(canonical) == null) {
            // Not shared, or a one-to-one hidden id the link map does not link: held for the backup.
            bump(() -> counts.notShared++);
            return;
        }
        Chat c = chats.computeIfAbsent(canonical, id -> new Chat(id, new Serial(pool, counts)));
        c.queue.execute(() -> place(c, p.lines));
    }

    // ---- placing: the ordinal ------------------------------------------------------------------

    private void place(Chat c, List<Line> lines) {
        long now = clock.nowMs();
        evictMemo(c, now);
        // Received messages with text, by second, in arrival order.
        Map<Long, List<String>> bySecond = new LinkedHashMap<>();
        for (Line l : lines) {
            if (l.own) { bump(() -> counts.ownSkipped++); continue; }
            if (l.text == null || l.text.isEmpty() || l.timeMs <= 0) { bump(() -> counts.noTextSkipped++); continue; }
            long second = BackupCombiner.second(l.timeMs);
            List<String> list = bySecond.get(second);
            if (list == null) bySecond.put(second, list = new ArrayList<>());
            list.add(EventPlan.cut(l.text));
        }
        for (Map.Entry<Long, List<String>> e : bySecond.entrySet()) {
            long second = e.getKey();
            Map<String, Integer> seen = new HashMap<>();
            for (String text : e.getValue()) {
                byte[] h;
                try {
                    h = sent.textHash(text);
                } catch (RuntimeException deleted) {
                    // The sent list was turned off under us: nothing more goes out.
                    bump(() -> counts.errors++);
                    return;
                }
                String hx = SentHashes.hex(h);
                int j = seen.containsKey(hx) ? seen.get(hx) : 0;
                seen.put(hx, j + 1);
                List<Integer> known = knownOrdinals(c, second, h);
                if (j < known.size()) {
                    bump(() -> counts.alreadyKnown++);
                    continue;
                }
                int k = freeOrdinal(c, second);
                if (k < 0) {
                    bump(() -> counts.ordinalOverflow++);
                    continue;
                }
                synchronized (c) {
                    c.memo.put(second + "|" + k, new Memo(h, PENDING, now));
                    c.pending.add(new Pend(EventPlan.key(c.id, second, k), second, k, text, h, now));
                }
            }
        }
        flush(c);
    }

    /** Ordinals already holding this text in this second — in the sent-hash list or this process's memo. Ascending. */
    private List<Integer> knownOrdinals(Chat c, long second, byte[] h) {
        List<Integer> out = new ArrayList<>();
        for (int k = 0; k < MAX_ORDINAL; k++) {
            SentHashes.Entry e = sent.lookup(EventPlan.key(c.id, second, k));
            Memo m;
            synchronized (c) {
                m = c.memo.get(second + "|" + k);
            }
            if ((e != null && Arrays.equals(e.textHash, h)) || (m != null && Arrays.equals(m.textHash, h))) out.add(k);
        }
        return out;
    }

    /** The smallest ordinal in this second that neither the sent-hash list nor the memo holds; -1 if none. */
    private int freeOrdinal(Chat c, long second) {
        for (int k = 0; k < MAX_ORDINAL; k++) {
            if (sent.lookup(EventPlan.key(c.id, second, k)) != null) continue;
            synchronized (c) {
                if (c.memo.containsKey(second + "|" + k)) continue;
            }
            return k;
        }
        return -1;
    }

    private void evictMemo(Chat c, long now) {
        synchronized (c) {
            for (Iterator<Memo> it = c.memo.values().iterator(); it.hasNext(); ) {
                Memo m = it.next();
                if (m.state != PENDING && now - m.atMs > MEMO_MS) it.remove();
            }
            if (c.memo.size() <= MEMO_MAX) return;
            List<Map.Entry<String, Memo>> settled = new ArrayList<>();
            for (Map.Entry<String, Memo> e : c.memo.entrySet()) if (e.getValue().state != PENDING) settled.add(e);
            Collections.sort(settled, (a, b) -> Long.compare(a.getValue().atMs, b.getValue().atMs));
            int excess = c.memo.size() - MEMO_MAX;
            List<String> drop = new ArrayList<>();
            for (int i = 0; i < excess && i < settled.size(); i++) drop.add(settled.get(i).getKey());
            for (String k : drop) c.memo.remove(k);
        }
    }

    /** Memo entries held for a chat — a count, for tests. */
    int memoSize(String canonicalChatId) {
        Chat c = chats.get(canonicalChatId);
        if (c == null) return 0;
        synchronized (c) {
            return c.memo.size();
        }
    }

    // ---- posting -------------------------------------------------------------------------------

    private void flush(Chat c) {
        List<Pend> due;
        long now = clock.nowMs();
        synchronized (c) {
            if (c.pending.isEmpty()) {
                evictMemo(c, now);
                return;
            }
        }
        if (!gate.open() || shares.kindOf(c.id) == null) {
            // The channel closed, or the chat was un-ticked: nothing more goes out for it.
            giveUp(c, null, now);
            return;
        }
        synchronized (c) {
            for (Iterator<Pend> it = c.pending.iterator(); it.hasNext(); ) {
                Pend p = it.next();
                if (now - p.arrivedMs >= RETRY_WINDOW_MS) {
                    it.remove();
                    settle(c, p, GAVE_UP, now);
                    bump(() -> counts.gaveUp++);
                }
            }
            due = new ArrayList<>();
            for (Pend p : c.pending) {
                if (p.nextAttemptMs <= now && due.size() < MAX_EVENTS_PER_POST) due.add(p);
            }
        }
        if (due.isEmpty()) return;
        if (!shares.acceptedCurrent()) {
            // Posted only while the VM holds the current share list; wait, inside the window.
            later(c, due, now);
            return;
        }
        post(c, due, now);
    }

    private void post(Chat c, List<Pend> due, long now) {
        JsonOut.Arr events = JsonOut.arr();
        for (Pend p : due) {
            events.add(JsonOut.obj().put("kind", EventPlan.MESSAGE).put("chat", c.id).put("time", p.second)
                    .put("ordinal", p.ordinal).put("text", p.text).put("sender", "").put("source", "live"));
        }
        String body = JsonOut.obj().put("events", events).toString();
        bump(() -> counts.posts++);
        DeviceApi.Result r = api.post(EVENTS_PATH, body, READ_TIMEOUT_MS);
        boolean open = gate.observe(r);
        if (r.status == 200) {
            Reply reply = Reply.parse(r.body);
            if (reply == null) {
                later(c, due, now);
                return;
            }
            if (reply.droppedNotShared > 0) {
                // The VM does not hold this chat as shared: record nothing (verify 1); the backup sends it.
                bump(() -> counts.droppedNotShared += due.size());
                giveUp(c, due, now);
                return;
            }
            List<Pend> took = new ArrayList<>();
            List<Pend> refused = new ArrayList<>();
            for (int i = 0; i < due.size(); i++) (reply.rejected.contains(i) ? refused : took).add(due.get(i));
            if (!refused.isEmpty()) {
                bump(() -> counts.rejected += refused.size());
                giveUp(c, refused, now);
            }
            byte[] noSender;
            try {
                noSender = sent.senderHash("");
            } catch (RuntimeException deleted) {
                bump(() -> counts.recordFailed += took.size());
                giveUp(c, took, now);
                return;
            }
            for (Pend p : took) {
                boolean ok;
                try {
                    sent.record(p.key, p.textHash, noSender, p.second);
                    ok = true;
                } catch (RuntimeException writeFailed) {
                    ok = false;
                }
                synchronized (c) {
                    c.pending.remove(p);
                    settle(c, p, ok ? SENT : GAVE_UP, now);
                }
                if (ok) bump(() -> counts.recorded++);
                else bump(() -> counts.recordFailed++);
            }
            return;
        }
        if (!open) {
            giveUp(c, null, now);
            return;
        }
        if (retryable(r.status)) {
            later(c, due, now);
            return;
        }
        giveUp(c, due, now);
    }

    /** No answer, or an answer that may differ next time. A refused address or no token never will. */
    static boolean retryable(int status) {
        return status == DeviceApi.NETWORK || status == 408 || status == 429 || (status >= 500 && status < 600);
    }

    /** Schedules another attempt for each, inside the window; the next {@link #tick} after the window gives them up. */
    private void later(Chat c, List<Pend> due, long now) {
        synchronized (c) {
            for (Pend p : due) {
                long gap = Math.min(MAX_RETRY_GAP_MS, FIRST_RETRY_GAP_MS << Math.min(p.attempts, 8));
                p.attempts++;
                p.nextAttemptMs = now + gap;
            }
        }
        bump(() -> counts.retried += due.size());
    }

    /** Leaves these (or, when null, every pending item of the chat) to the backup. */
    private void giveUp(Chat c, List<Pend> which, long now) {
        synchronized (c) {
            List<Pend> list = which == null ? new ArrayList<>(c.pending) : which;
            for (Pend p : list) {
                c.pending.remove(p);
                settle(c, p, GAVE_UP, now);
            }
            final int n = list.size();
            bump(() -> counts.gaveUp += n);
        }
    }

    /** Final for this process: the memo keeps the hash and the ordinal, the text goes. Caller holds the chat. */
    private static void settle(Chat c, Pend p, int state, long now) {
        p.text = null;
        Memo m = c.memo.get(p.second + "|" + p.ordinal);
        if (m != null) {
            m.state = state;
            m.atMs = now;
        }
    }

    private void bump(Runnable r) {
        synchronized (counts) {
            r.run();
        }
    }

    // ---- the VM's reply ------------------------------------------------------------------------

    /** The parts of handle_events' reply the live feed acts on. */
    static final class Reply {
        final long droppedNotShared;
        final Set<Integer> rejected;

        private Reply(long droppedNotShared, Set<Integer> rejected) {
            this.droppedNotShared = droppedNotShared;
            this.rejected = rejected;
        }

        /** Null when the body is not the reply's shape — treated as no answer. */
        static Reply parse(String body) {
            Object root;
            try {
                root = Json.parse(body);
            } catch (Json.Malformed | RuntimeException e) {
                return null;
            }
            if (!(root instanceof Map)) return null;
            Map<?, ?> m = (Map<?, ?>) root;
            Object dropped = m.get("dropped_not_shared");
            if (!(dropped instanceof Long)) return null;
            Set<Integer> rejected = new HashSet<>();
            Object rej = m.get("rejected");
            if (rej != null) {
                if (!(rej instanceof List)) return null;
                for (Object o : (List<?>) rej) {
                    if (!(o instanceof Map) || !(((Map<?, ?>) o).get("index") instanceof Long)) return null;
                    rejected.add(((Long) ((Map<?, ?>) o).get("index")).intValue());
                }
            }
            return new Reply((Long) dropped, rejected);
        }
    }

    // ---- one at a time per key -----------------------------------------------------------------

    /** Runs its tasks one at a time, in order, on the pool. A task's failure is counted, never logged. */
    static final class Serial implements Executor {
        private final Executor pool;
        private final Counts counts;
        private final ArrayDeque<Runnable> queue = new ArrayDeque<>();
        private boolean running;

        Serial(Executor pool, Counts counts) {
            this.pool = pool;
            this.counts = counts;
        }

        @Override
        public void execute(Runnable r) {
            synchronized (this) {
                queue.add(r);
                if (running) return;
                running = true;
            }
            try {
                pool.execute(this::drain);
            } catch (RuntimeException refused) {
                // The pool was shut down (the listener disconnected): drop what is queued.
                synchronized (this) {
                    queue.clear();
                    running = false;
                }
            }
        }

        private void drain() {
            while (true) {
                Runnable r;
                synchronized (this) {
                    r = queue.poll();
                    if (r == null) {
                        running = false;
                        return;
                    }
                }
                try {
                    r.run();
                } catch (Throwable t) {
                    synchronized (counts) {
                        counts.errors++;
                    }
                }
            }
        }
    }
}
