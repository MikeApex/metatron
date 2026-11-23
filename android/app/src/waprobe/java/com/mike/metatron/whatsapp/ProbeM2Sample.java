package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.Set;

/**
 * "8. Export a labelling sample" — the platform-free half (WhatsApp M2; the session prompt is
 * archive/handoffs/2026-11-23-whatsapp-m2-labelling-prep-prompt.md). Plain Java, so it runs under
 * testWaprobeUnitTest.
 *
 * From combined messages it keeps the last 30 days of RECEIVED messages that have text, in a
 * one-to-one or group chat (status updates, channels and broadcast lists are left out), and draws
 * about {@link #TARGET} of them:
 * <ul>
 *   <li>Cyrillic messages at their own share of that traffic, but at least {@link #MIN_CYRILLIC};</li>
 *   <li>within each script, one-to-one against group in the traffic's own proportions;</li>
 *   <li>at most {@link #PER_CHAT_CAP} from any one chat, so a busy group cannot fill the sample
 *       (Mike, 11-23). A kind the cap leaves short is topped up from the other kind.</li>
 * </ul>
 *
 * A row holds {@code n}, {@code chat_kind}, {@code time_s} and {@code text} — **no chat id, no
 * sender id, no name** — and rows are shuffled, so their order says nothing about who wrote them.
 * The report is counts only and never carries a value from a message.
 */
final class ProbeM2Sample {
    static final int TARGET = 200;
    static final int MIN_CYRILLIC = 30;
    static final int PER_CHAT_CAP = 15;
    /** The VM refuses a longer text (tools/intake_whatsapp.py MAX_TEXT_CHARS), so it is not sampled. */
    static final int MAX_TEXT_CHARS = 4000;
    static final long WINDOW_MS = 30L * 24 * 3600 * 1000;
    /** tools/intake_whatsapp.py script_of: a message is Cyrillic when more than this share of its letters are. */
    static final double SCRIPT_SHARE = 0.5;

    static final String ONE_TO_ONE = "one_to_one", GROUP = "group";

    private ProbeM2Sample() {}

    static final class Row {
        final int n;
        final String kind;
        final long timeS;
        final String text;

        Row(int n, String kind, long timeS, String text) {
            this.n = n;
            this.kind = kind;
            this.timeS = timeS;
            this.text = text;
        }

        /** Deliberately no content. */
        @Override
        public String toString() {
            return "Row(" + n + ")";
        }
    }

    static final class Result {
        final List<Row> rows;
        final String report;

        Result(List<Row> rows, String report) {
            this.rows = Collections.unmodifiableList(rows);
            this.report = report;
        }
    }

    /** "one_to_one", "group", or null for anything that is not a person-to-person chat. */
    static String kindOf(String chatJid) {
        if (chatJid == null) return null;
        if (chatJid.endsWith("@g.us")) return GROUP;
        if (chatJid.endsWith("@s.whatsapp.net") || chatJid.endsWith("@lid")) return ONE_TO_ONE;
        return null; // status@broadcast, broadcast lists, @newsletter channels, anything unknown
    }

    /** The same rule as tools/intake_whatsapp.py script_of, reduced to "is it Cyrillic". */
    static boolean cyrillic(String text) {
        int n = 0, cyr = 0, lat = 0;
        for (int i = 0; i < text.length(); ) {
            int cp = text.codePointAt(i);
            i += Character.charCount(cp);
            if (!Character.isLetter(cp)) continue;
            n++;
            Character.UnicodeScript s = Character.UnicodeScript.of(cp);
            if (s == Character.UnicodeScript.CYRILLIC) cyr++;
            else if (s == Character.UnicodeScript.LATIN) lat++;
        }
        if (n == 0) return false;
        if ((double) cyr / n > SCRIPT_SHARE) return true;
        if ((double) (n - cyr - lat) / n > SCRIPT_SHARE) return false;
        return cyr > lat;
    }

    private static final class Pool {
        final List<WaMessage> items = new ArrayList<>();
        int pos;

        int remaining() {
            return items.size() - pos;
        }
    }

    private static final class Draw {
        final Map<String, Integer> perChat = new HashMap<>();
        final List<WaMessage> chosen = new ArrayList<>();
        int capSkipped;

        int take(Pool p, int k) {
            int taken = 0;
            while (taken < k && p.pos < p.items.size()) {
                WaMessage m = p.items.get(p.pos++);
                int had = perChat.containsKey(m.chatJid) ? perChat.get(m.chatJid) : 0;
                if (had >= PER_CHAT_CAP) {
                    capSkipped++;
                    continue;
                }
                perChat.put(m.chatJid, had + 1);
                chosen.add(m);
                taken++;
            }
            return taken;
        }
    }

    /**
     * @param combined messages with canonical chat ids (BackupCombiner's output), any order
     * @param nowMs    the window ends here and starts {@link #WINDOW_MS} before
     */
    static Result sample(List<WaMessage> combined, long nowMs, Random rnd) {
        long since = nowMs - WINDOW_MS;
        int outside = 0, fromMe = 0, noText = 0, notChat = 0, tooLong = 0;
        // pools[cyrillic ? 1 : 0][group ? 1 : 0]
        Pool[][] pools = {{new Pool(), new Pool()}, {new Pool(), new Pool()}};
        for (WaMessage m : combined) {
            if (m.timeMs < since || m.timeMs > nowMs) { outside++; continue; }
            if (m.fromMe) { fromMe++; continue; }
            if (m.text == null || m.text.trim().isEmpty()) { noText++; continue; }
            String kind = kindOf(m.chatJid);
            if (kind == null) { notChat++; continue; }
            if (m.text.length() > MAX_TEXT_CHARS) { tooLong++; continue; }
            pools[cyrillic(m.text) ? 1 : 0][GROUP.equals(kind) ? 1 : 0].items.add(m);
        }
        for (Pool[] byKind : pools) for (Pool p : byKind) Collections.shuffle(p.items, rnd);

        int latAvail = pools[0][0].items.size() + pools[0][1].items.size();
        int cyrAvail = pools[1][0].items.size() + pools[1][1].items.size();
        int total = latAvail + cyrAvail;
        int cyrT = total == 0 ? 0 : Math.min(cyrAvail, Math.max(MIN_CYRILLIC, (int) Math.round((double) TARGET * cyrAvail / total)));
        int latT = Math.min(latAvail, TARGET - cyrT);
        cyrT = Math.min(cyrAvail, TARGET - latT); // a short Latin side gives its room back

        Draw d = new Draw();
        int[] targets = {latT, cyrT};
        for (int s = 0; s < 2; s++) {
            Pool one = pools[s][0], group = pools[s][1];
            int avail = one.items.size() + group.items.size();
            if (targets[s] == 0 || avail == 0) continue;
            int gq = (int) Math.round((double) targets[s] * group.items.size() / avail);
            int got = d.take(one, targets[s] - gq) + d.take(group, gq);
            // The cap left this script short: top up from whichever kind has more left. Each take
            // either fills the gap or runs its pool to the end, so this loop ends.
            while (got < targets[s] && (one.remaining() > 0 || group.remaining() > 0)) {
                got += d.take(one.remaining() >= group.remaining() ? one : group, targets[s] - got);
            }
        }

        Collections.shuffle(d.chosen, rnd);
        List<Row> rows = new ArrayList<>(d.chosen.size());
        int[][] drawn = new int[2][2];
        Set<String> chats = new HashSet<>();
        for (int i = 0; i < d.chosen.size(); i++) {
            WaMessage m = d.chosen.get(i);
            String kind = kindOf(m.chatJid);
            rows.add(new Row(i + 1, kind, m.timeMs / 1000, m.text));
            drawn[cyrillic(m.text) ? 1 : 0][GROUP.equals(kind) ? 1 : 0]++;
            chats.add(m.chatJid);
        }

        StringBuilder b = new StringBuilder();
        b.append("window: the last 30 days\n");
        b.append("received with text: ").append(total).append(" — one-to-one ")
                .append(pools[0][0].items.size() + pools[1][0].items.size()).append(" (Cyrillic ").append(pools[1][0].items.size())
                .append("), group ").append(pools[0][1].items.size() + pools[1][1].items.size()).append(" (Cyrillic ")
                .append(pools[1][1].items.size()).append(")\n");
        b.append("left out: sent by you ").append(fromMe).append(", no text ").append(noText)
                .append(", not a chat (status, channels, broadcast lists) ").append(notChat)
                .append(", over ").append(MAX_TEXT_CHARS).append(" characters ").append(tooLong)
                .append(", outside the window ").append(outside).append('\n');
        b.append("sample: ").append(rows.size()).append(" of a target ").append(TARGET).append(" — one-to-one ")
                .append(drawn[0][0] + drawn[1][0]).append(" (Cyrillic ").append(drawn[1][0]).append("), group ")
                .append(drawn[0][1] + drawn[1][1]).append(" (Cyrillic ").append(drawn[1][1]).append(")\n");
        b.append("Cyrillic in the sample: ").append(drawn[1][0] + drawn[1][1]).append(" (floor ").append(MIN_CYRILLIC)
                .append(cyrAvail < MIN_CYRILLIC ? "; only " + cyrAvail + " in the window" : "").append(")\n");
        b.append("drawn from ").append(chats.size()).append(" chats; per-chat cap ").append(PER_CHAT_CAP)
                .append(", messages it passed over ").append(d.capSkipped).append('\n');
        return new Result(rows, b.toString());
    }

    /** One JSON object per line: n, chat_kind, time_s, text. UTF-8 is the caller's encoding. */
    static String jsonl(List<Row> rows) {
        StringBuilder b = new StringBuilder();
        for (Row r : rows) {
            b.append("{\"n\":").append(r.n).append(",\"chat_kind\":\"").append(r.kind)
                    .append("\",\"time_s\":").append(r.timeS).append(",\"text\":");
            quote(r.text, b);
            b.append("}\n");
        }
        return b.toString();
    }

    static void quote(String s, StringBuilder b) {
        b.append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20 || c == ' ' || c == ' ' || Character.isSurrogate(c)
                            && !(Character.isHighSurrogate(c) && i + 1 < s.length() && Character.isLowSurrogate(s.charAt(i + 1)))
                            && !(Character.isLowSurrogate(c) && i > 0 && Character.isHighSurrogate(s.charAt(i - 1)))) {
                        // A lone surrogate cannot be written as UTF-8; escaping keeps the line valid JSON.
                        b.append(String.format("\\u%04x", (int) c));
                    } else {
                        b.append(c);
                    }
            }
        }
        b.append('"');
    }
}
