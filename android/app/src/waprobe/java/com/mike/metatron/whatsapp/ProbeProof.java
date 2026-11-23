package com.mike.metatron.whatsapp;

import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Probe only — P3 step 4's comparisons, plain Java so testWaprobeUnitTest can plant values and
 * assert they never appear. Every input is already canonical (BackupCombiner.canonicalise).
 * Output is counts only.
 */
final class ProbeProof {
    private ProbeProof() {}

    static Map<String, WaMessage> index(List<WaMessage> canonical) {
        Map<String, WaMessage> m = new HashMap<>();
        for (WaMessage x : canonical) m.put(BackupCombiner.key(x), x);
        return m;
    }

    /** One increment's decoded messages against the newest full backup, field by field. */
    static String agreement(List<WaMessage> inc, Map<String, WaMessage> newest) {
        int matched = 0, time = 0, sender = 0, senderBoth = 0, text = 0, textDiffers = 0, textBothNull = 0, row = 0;
        for (WaMessage m : inc) {
            WaMessage n = newest.get(BackupCombiner.key(m));
            if (n == null) continue;
            matched++;
            if (m.timeMs / 1000 == n.timeMs / 1000) time++;
            if (m.senderJid != null || n.senderJid != null) {
                senderBoth++;
                if (m.senderJid != null && m.senderJid.equals(n.senderJid)) sender++;
            }
            if (m.text == null && n.text == null) textBothNull++;
            else if (m.text != null && m.text.equals(n.text)) text++;
            else textDiffers++;
            if (m.rowId == n.rowId) row++;
        }
        return "matched by (chat, from-me, key_id) " + matched + " of " + inc.size()
                + "; of those: time " + time + ", group sender " + sender + " of " + senderBoth
                + ", text equal " + text + " / differs " + textDiffers + " / both none " + textBothNull
                + ", row id " + row;
    }

    /** The combined set against the newest full backup over the same window. */
    static String versus(List<WaMessage> combined, List<WaMessage> newestWindow, long baseWrittenMs) {
        return versus(combined, newestWindow, baseWrittenMs, null);
    }

    /**
     * As above; with {@code types} (the newest backup's message._id → message_type) it also counts
     * the message_type of the messages the increments carried and of those only the newest holds —
     * the latter split by from-me and chat kind, because V6's reply markers are the user's own
     * messages in one-to-one chats (Phase 1 step 0). Small integers only.
     */
    static String versus(List<WaMessage> combined, List<WaMessage> newestWindow, long baseWrittenMs, Map<Long, Integer> types) {
        Map<String, WaMessage> n = index(newestWindow);
        int both = 0, textEqual = 0, textDiffers = 0, onlyCombined = 0;
        java.util.TreeMap<Integer, Integer> carried = new java.util.TreeMap<>();
        for (WaMessage c : combined) {
            WaMessage x = n.remove(BackupCombiner.key(c));
            if (x == null) { onlyCombined++; continue; }
            both++;
            boolean eq = c.text == null ? x.text == null : c.text.equals(x.text);
            if (eq) textEqual++; else textDiffers++;
            if (types != null) bump(carried, typeOf(types, x.rowId));
        }
        String out = "combined " + combined.size() + " vs newest " + newestWindow.size() + " in the same window: in both " + both
                + " (text equal " + textEqual + ", differs " + textDiffers + "), only combined " + onlyCombined
                + ", only newest " + n.size() + onlyNewest(n.values(), baseWrittenMs);
        if (types != null) out += "\n    message_type, in both " + carried + onlyNewestTypes(n.values(), types);
        return out;
    }

    /** message_type of the messages only the newest backup holds: from me in one-to-one / in groups / other chats, and not from me. */
    static String onlyNewestTypes(java.util.Collection<WaMessage> rest, Map<Long, Integer> types) {
        java.util.TreeMap<Integer, Integer> meOne = new java.util.TreeMap<>(), meGroup = new java.util.TreeMap<>(),
                meOther = new java.util.TreeMap<>(), notMe = new java.util.TreeMap<>();
        for (WaMessage m : rest) {
            int t = typeOf(types, m.rowId);
            if (!m.fromMe) bump(notMe, t);
            else if (m.chatJid.endsWith("@g.us")) bump(meGroup, t);
            else if (m.chatJid.endsWith("@s.whatsapp.net") || m.chatJid.endsWith("@lid")) bump(meOne, t);
            else bump(meOther, t);
        }
        return "; only newest — from me in one-to-one " + meOne + ", from me in groups " + meGroup
                + ", from me elsewhere " + meOther + ", not from me " + notMe;
    }

    private static int typeOf(Map<Long, Integer> types, long rowId) {
        Integer t = types.get(rowId);
        return t == null ? -1 : t;
    }

    private static void bump(java.util.TreeMap<Integer, Integer> m, int k) {
        m.put(k, m.containsKey(k) ? m.get(k) + 1 : 1);
    }

    /** What the messages only the newest backup holds are: chat kind, from-me, text, before or after the base. Counts only. */
    static String onlyNewest(java.util.Collection<WaMessage> rest, long baseWrittenMs) {
        if (rest.isEmpty()) return "";
        java.util.TreeMap<String, Integer> kinds = new java.util.TreeMap<>();
        int fromMe = 0, withText = 0, beforeBase = 0;
        java.util.Set<String> chats = new java.util.HashSet<>();
        for (WaMessage m : rest) {
            int at = m.chatJid.lastIndexOf('@');
            String kind = at < 0 ? "(no @)" : m.chatJid.substring(at + 1);
            if (!kind.matches("[a-z.]{1,20}")) kind = "(other)";
            kinds.put(kind, kinds.containsKey(kind) ? kinds.get(kind) + 1 : 1);
            if (m.fromMe) fromMe++;
            if (m.text != null) withText++;
            if (m.timeMs < baseWrittenMs) beforeBase++;
            chats.add(m.chatJid);
        }
        return "\n    only newest, by chat kind " + kinds + " in " + chats.size() + " chats; from me " + fromMe + ", with text " + withText
                + ", timed before the base was written " + beforeBase;
    }
}
