package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.function.Predicate;

/**
 * What one night sends, decided — a pure function of the combined messages, the sent-hash list,
 * the share list and the reply rule (build plan § 3.4). <b>It reads the sent-hash list and never
 * writes it:</b> the caller records only the events the VM accepted (§ 3.2, review 1).
 *
 * Per message in a shared chat:
 * <ul>
 * <li>received, with text — key absent → {@code message}; both hashes equal → skipped; either hash
 *     different → {@code update}. So a group message that went live with sender {@code ""} is sent
 *     again as an {@code update} the night the backup supplies the sender (review 2); a one-to-one
 *     carries {@code ""} on both paths and is skipped;</li>
 * <li>received, no text ({@code text == null}) — skipped;</li>
 * <li>from me and a reply by the given rule — a {@code reply_marker}, once per key
 *     ({@code r|chat|second|ordinal}, hashes of {@code ""});</li>
 * <li>from me and not a reply — nothing; a chat not in the share list — nothing.</li>
 * </ul>
 *
 * A text is cut to its first {@value #MAX_TEXT_CODE_POINTS} code points, never splitting a
 * surrogate pair, <b>before</b> it is hashed — so the cut text is both what is sent and what is
 * hashed, and an over-long message is not re-sent nightly (§ 3.2, review 3). The VM's limit is the
 * same 4,000, counted by Python's {@code len}, which counts code points.
 */
public final class EventPlan {
    public static final int MAX_TEXT_CODE_POINTS = 4000;
    public static final String MESSAGE = "message", UPDATE = "update", REPLY_MARKER = "reply_marker";
    public static final String GROUP = "group", ONE_TO_ONE = "one_to_one";

    /** One event to post. {@link #toString()} carries no content. */
    public static final class Event {
        public final String kind;
        public final String chat;
        public final long second;
        public final int ordinal;
        /** The text as sent (already cut); "" for a reply marker, which never posts it. */
        public final String text;
        /** The canonical sender id for a group message from the backup, else ""; never posted on a reply marker. */
        public final String sender;
        /** The sent-hash list key: the VM's native key, or {@code r|…} for a reply marker. */
        public final String key;
        public final byte[] textHash;
        public final byte[] senderHash;

        Event(String kind, String chat, long second, int ordinal, String text, String sender, String key,
              byte[] textHash, byte[] senderHash) {
            this.kind = kind;
            this.chat = chat;
            this.second = second;
            this.ordinal = ordinal;
            this.text = text;
            this.sender = sender;
            this.key = key;
            this.textHash = textHash;
            this.senderHash = senderHash;
        }

        /**
         * {@code {"kind","chat","time","ordinal","text","sender","source":"backup"}} — the shape the
         * VM's {@code _validate} takes. A reply marker carries no {@code text} and no {@code sender}.
         */
        public String toJson() {
            JsonOut.Obj o = JsonOut.obj().put("kind", kind).put("chat", chat).put("time", second).put("ordinal", ordinal);
            if (!REPLY_MARKER.equals(kind)) o.put("text", text).put("sender", sender);
            return o.put("source", "backup").toString();
        }

        /** Kind and position only — never the chat, text or sender. */
        @Override
        public String toString() {
            return "Event(" + kind + ", second " + second + ", ordinal " + ordinal + ")";
        }
    }

    /** Oldest first: by second, then chat, then ordinal, then key (a received row before its reply-marker twin). */
    public final List<Event> events;
    public final int messages, updates, replyMarkers, skippedUnchanged, receivedNoText, notShared;

    private EventPlan(List<Event> events, int messages, int updates, int replyMarkers, int skippedUnchanged,
                      int receivedNoText, int notShared) {
        this.events = Collections.unmodifiableList(events);
        this.messages = messages;
        this.updates = updates;
        this.replyMarkers = replyMarkers;
        this.skippedUnchanged = skippedUnchanged;
        this.receivedNoText = receivedNoText;
        this.notShared = notShared;
    }

    /** The VM's {@code native_key}: {@code chat|second|ordinal}. */
    public static String key(String chat, long second, int ordinal) {
        return chat + "|" + second + "|" + ordinal;
    }

    /** A reply marker's sent-hash key: {@code r|chat|second|ordinal}. */
    public static String replyKey(String chat, long second, int ordinal) {
        return "r|" + key(chat, second, ordinal);
    }

    /** {@code text} cut to its first {@value #MAX_TEXT_CODE_POINTS} code points; a pair is never split. */
    public static String cut(String text) {
        if (text == null || text.length() <= MAX_TEXT_CODE_POINTS) return text;
        if (text.codePointCount(0, text.length()) <= MAX_TEXT_CODE_POINTS) return text;
        return text.substring(0, text.offsetByCodePoints(0, MAX_TEXT_CODE_POINTS));
    }

    /**
     * @param combined    {@code BackupCombiner.Combined.messages} — canonical, with ordinals
     * @param sent        the sent-hash list; read only
     * @param sharedKinds canonical chat id → {@link #GROUP} or {@link #ONE_TO_ONE}
     * @param isReply     the reply rule ({@code ReplyRule::isReply})
     */
    public static EventPlan build(List<WaMessage> combined, SentHashes sent, Map<String, String> sharedKinds,
                                  Predicate<WaMessage> isReply) {
        List<Event> out = new ArrayList<>();
        int messages = 0, updates = 0, markers = 0, skipped = 0, noText = 0, notShared = 0;
        byte[] emptyText = null, noSender = null;
        for (WaMessage m : combined) {
            String kind = sharedKinds.get(m.chatJid);
            if (kind == null) {
                notShared++;
                continue;
            }
            long second = BackupCombiner.second(m.timeMs);
            if (m.fromMe) {
                if (!isReply.test(m)) continue;
                String rk = replyKey(m.chatJid, second, m.ordinal);
                if (sent.lookup(rk) != null) continue;
                if (emptyText == null) {
                    emptyText = sent.textHash("");
                    noSender = sent.senderHash("");
                }
                out.add(new Event(REPLY_MARKER, m.chatJid, second, m.ordinal, "", "", rk, emptyText, noSender));
                markers++;
                continue;
            }
            if (m.text == null || m.text.isEmpty()) {
                noText++;
                continue;
            }
            String text = cut(m.text);
            String sender = GROUP.equals(kind) && m.senderJid != null ? m.senderJid : "";
            byte[] th = sent.textHash(text), sh = sent.senderHash(sender);
            String k = key(m.chatJid, second, m.ordinal);
            SentHashes.Entry prior = sent.lookup(k);
            String eventKind;
            if (prior == null) {
                eventKind = MESSAGE;
                messages++;
            } else if (Arrays.equals(prior.textHash, th) && Arrays.equals(prior.senderHash, sh)) {
                skipped++;
                continue;
            } else {
                eventKind = UPDATE;
                updates++;
            }
            out.add(new Event(eventKind, m.chatJid, second, m.ordinal, text, sender, k, th, sh));
        }
        Collections.sort(out, (a, b) -> {
            if (a.second != b.second) return Long.compare(a.second, b.second);
            int c = a.chat.compareTo(b.chat);
            if (c != 0) return c;
            if (a.ordinal != b.ordinal) return Integer.compare(a.ordinal, b.ordinal);
            return a.key.compareTo(b.key);
        });
        return new EventPlan(out, messages, updates, markers, skipped, noText, notShared);
    }

    /**
     * The number of (chat, second) groups with two or more received rows, text or not, in shared
     * chats — § 3.5's measure of how often the live path's arrival ordinal can disagree with the
     * backup's (§ 1).
     */
    public static int sameSecondGroups(List<WaMessage> combined, Set<String> sharedChats) {
        Map<String, Integer> counts = new HashMap<>();
        for (WaMessage m : combined) {
            if (m.fromMe || !sharedChats.contains(m.chatJid)) continue;
            String g = m.chatJid + '\u0000' + BackupCombiner.second(m.timeMs);
            Integer n = counts.get(g);
            counts.put(g, n == null ? 1 : n + 1);
        }
        int groups = 0;
        for (int n : counts.values()) if (n >= 2) groups++;
        return groups;
    }

    /** Counts only. */
    @Override
    public String toString() {
        return "EventPlan(" + events.size() + " events: " + messages + " messages, " + updates + " updates, "
                + replyMarkers + " reply markers; skipped " + skippedUnchanged + " unchanged, " + receivedNoText
                + " without text, " + notShared + " not shared)";
    }
}
