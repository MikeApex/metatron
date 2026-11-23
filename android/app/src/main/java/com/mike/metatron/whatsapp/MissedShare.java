package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/**
 * "This should have come up" (build plan § 3.11, review 7): what a text shared from WhatsApp to
 * Metatron becomes — the body of {@code POST /device/whatsapp/missed}. Plain Java, so the whole
 * decision is unit-tested; {@link MissedShareActivity} only reads the intent and posts.
 *
 * <p>The shared text is cut exactly as the events were ({@link EventPlan#cut}), hashed under the
 * sent-hash list's salt ({@link SentHashes#textHash}) and looked up by that hash
 * ({@link SentHashes#keysForText}, newest first). Reply-marker keys ({@code r|…}) are never a
 * match: they are the user's own messages, recorded under the hash of {@code ""}. An empty or
 * blank shared text matches nothing.
 *
 * <ul>
 * <li>one match → {@code {"keys":[k]}};</li>
 * <li>two to {@value #MAX_KEYS} → all of them, newest first, {@code "ambiguous":true} — a short
 *     text sent in several chats, which the share intent cannot tell apart (it carries no chat
 *     and no time);</li>
 * <li>more than {@value #MAX_KEYS} → {@code {"keys":[],"ambiguous_over":n}};</li>
 * <li>none → {@code {"keys":[]}}.</li>
 * </ul>
 *
 * <p><b>The text is never in the body, never stored and never in a {@code toString()}</b> — only
 * keys, a flag and a count leave this class. The VM's limit on keys is the same
 * ({@code MAX_MISSED_KEYS} in {@code tools/intake_whatsapp.py}).
 */
public final class MissedShare {
    /** The VM route. */
    public static final String PATH = "/device/whatsapp/missed";
    /** At most this many keys per flag — the VM refuses more. */
    public static final int MAX_KEYS = 5;
    /** The VM looks each key up in its index and records one row: quick, but not a GET. */
    public static final int READ_TIMEOUT_MS = 15_000;

    private MissedShare() {}

    /** One flag, ready to post. {@link #toString()} carries counts only — a key names a chat. */
    public static final class Flag {
        /** The keys to post, newest first: empty, one, or two to {@value #MAX_KEYS} when ambiguous. */
        public final List<String> keys;
        public final boolean ambiguous;
        /** The number of matches when there were more than {@value #MAX_KEYS}, else -1. */
        public final int ambiguousOver;

        Flag(List<String> keys, boolean ambiguous, int ambiguousOver) {
            this.keys = Collections.unmodifiableList(new ArrayList<>(keys));
            this.ambiguous = ambiguous;
            this.ambiguousOver = ambiguousOver;
        }

        /** {@code {"keys":[…]}}, plus {@code "ambiguous":true} or {@code "ambiguous_over":n} when they apply. */
        public String toJson() {
            JsonOut.Arr k = JsonOut.arr();
            for (String key : keys) k.add(key);
            JsonOut.Obj o = JsonOut.obj().put("keys", k);
            if (ambiguous) o.put("ambiguous", true);
            if (ambiguousOver >= 0) o.put("ambiguous_over", ambiguousOver);
            return o.toString();
        }

        @Override
        public String toString() {
            return "MissedShare.Flag(" + keys.size() + " keys" + (ambiguous ? ", ambiguous" : "")
                    + (ambiguousOver >= 0 ? ", over " + ambiguousOver : "") + ")";
        }
    }

    /**
     * The hash a shared text is looked up by: the text cut as events are, under {@code sent}'s
     * salt — or null for a null, empty or blank text, which matches nothing.
     */
    public static byte[] hashOf(String shared, SentHashes sent) {
        if (isBlank(shared)) return null;
        return sent.textHash(EventPlan.cut(shared));
    }

    /** The flag for a hash from {@link #hashOf}; null → no match. */
    public static Flag flagFor(byte[] textHash, SentHashes sent) {
        if (textHash == null) return fromMatches(Collections.<String>emptyList());
        return fromMatches(sent.keysForText(textHash));
    }

    /** {@link #hashOf} then {@link #flagFor}. */
    public static Flag flag(String shared, SentHashes sent) {
        return flagFor(hashOf(shared, sent), sent);
    }

    /** The flag for keys matched by text hash, newest first; reply-marker keys are dropped first. */
    static Flag fromMatches(List<String> matches) {
        List<String> received = new ArrayList<>();
        for (String k : matches) {
            if (k != null && !k.startsWith("r|")) received.add(k);
        }
        int n = received.size();
        if (n > MAX_KEYS) return new Flag(Collections.<String>emptyList(), false, n);
        return new Flag(received, n >= 2, -1);
    }

    /** Null, empty, or nothing but whitespace and spacing characters (any script's). */
    static boolean isBlank(String s) {
        if (s == null) return true;
        for (int i = 0; i < s.length(); ) {
            int cp = s.codePointAt(i);
            if (!Character.isWhitespace(cp) && !Character.isSpaceChar(cp)) return false;
            i += Character.charCount(cp);
        }
        return true;
    }
}
