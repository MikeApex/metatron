package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;
import java.util.TreeSet;

/**
 * Probe only — Phase 2 step 0, review finding 6: which message_type values the user's own rows
 * carry, with and without text, and whether a nightly increment's messages carry a type at all.
 * Plain Java so testWaprobeUnitTest can plant values and assert they never appear.
 *
 * Nothing here assumes what any field or type number means. "Does an increment carry a type" is
 * answered by measurement only: each increment message is matched to the newest full backup by
 * row id (and key_id), and two things are counted against the backup's message_type — which
 * content field numbers the message has, and which numeric fields equal the type. Output is
 * type numbers, field-number paths, chat-kind labels and counts.
 */
final class ProbeTypes {
    private ProbeTypes() {}

    /** One GROUP BY row of the newest full backup: message_type × chat kind × from-me. */
    static final class Group {
        final int type;
        final String kind;
        final boolean fromMe;
        final long rows, withText;

        Group(int type, String server, boolean fromMe, long rows, long withText) {
            this.type = type;
            this.kind = kind(server);
            this.fromMe = fromMe;
            this.rows = rows;
            this.withText = withText;
        }
    }

    /** What an increment message is matched against: the full-backup row with its _id. */
    static final class Row {
        final int type;
        final String keyId;

        Row(int type, String keyId) {
            this.type = type;
            this.keyId = keyId;
        }
    }

    /** A jid's server part as a label; anything not shaped like one is "(other)". */
    static String kind(String server) {
        if (server == null) return "(no chat)";
        return server.matches("[a-z.]{1,20}") ? server : "(other)";
    }

    /** The newest full backup, one line per message_type. */
    static String fullSummary(List<Group> groups) {
        TreeMap<Integer, long[]> tot = new TreeMap<>(); // rows, with text, from me, from me with text
        TreeMap<Integer, TreeMap<String, long[]>> meKinds = new TreeMap<>();
        for (Group g : groups) {
            long[] t = tot.get(g.type);
            if (t == null) tot.put(g.type, t = new long[4]);
            t[0] += g.rows;
            t[1] += g.withText;
            if (!g.fromMe) continue;
            t[2] += g.rows;
            t[3] += g.withText;
            TreeMap<String, long[]> k = meKinds.get(g.type);
            if (k == null) meKinds.put(g.type, k = new TreeMap<>());
            long[] kv = k.get(g.kind);
            if (kv == null) k.put(g.kind, kv = new long[2]);
            kv[0] += g.rows;
            kv[1] += g.withText;
        }
        StringBuilder b = new StringBuilder();
        for (Map.Entry<Integer, long[]> e : tot.entrySet()) {
            long[] t = e.getValue();
            b.append("  type ").append(e.getKey()).append(": rows ").append(t[0]).append(", with text ").append(t[1])
                    .append("; from me ").append(t[2]).append(", with text ").append(t[3]);
            TreeMap<String, long[]> k = meKinds.get(e.getKey());
            if (k != null) {
                b.append(" — from me by chat kind {");
                boolean first = true;
                for (Map.Entry<String, long[]> x : k.entrySet()) {
                    b.append(first ? "" : ", ").append(x.getKey()).append('=').append(x.getValue()[0]).append('/').append(x.getValue()[1]);
                    first = false;
                }
                b.append('}');
            }
            b.append('\n');
        }
        return b.toString();
    }

    /** The increment side: every decoded message, matched to the newest full backup. */
    static final class Tally {
        /** A numeric field is listed as carrying the type only when present on at least this many matched messages. */
        static final int MIN_SEEN = 10;
        static final int MAX_SIGNATURES = 6, MAX_CANDIDATES = 8;

        int messages, noRowId, notInBackup, keyIdDiffers, matched;
        /** By type: received, received with text, from me, from me with text. */
        final TreeMap<Integer, int[]> byType = new TreeMap<>();
        final TreeMap<Integer, TreeMap<String, Integer>> signatures = new TreeMap<>();
        /** By numeric field path: seen on matched messages, equal to the type. */
        final Map<String, int[]> numeric = new HashMap<>();
        final Map<String, Set<Integer>> numericTypes = new HashMap<>();
        /** By type: matched messages; used to say where a candidate field is absent. */
        final TreeMap<Integer, Integer> matchedByType = new TreeMap<>();
        final Map<String, TreeMap<Integer, Integer>> presentByType = new HashMap<>();

        void add(ProbeFieldMap.Msg m, Map<Long, Row> rows) {
            messages++;
            Long rowId = m.num(ProbeFieldMap.ROW_ID);
            if (rowId == null) { noRowId++; return; }
            Row r = rows.get(rowId);
            if (r == null) { notInBackup++; return; }
            String keyId = m.text(ProbeFieldMap.KEY_ID);
            if (keyId == null || !keyId.equals(r.keyId)) { keyIdDiffers++; return; }
            matched++;
            bump(matchedByType, r.type);
            Long flag = m.num(ProbeFieldMap.KEY_FLAG);
            boolean fromMe = flag != null && flag == 1;
            boolean text = ProbeFieldMap.ruleText(m) != null;
            int[] t = byType.get(r.type);
            if (t == null) byType.put(r.type, t = new int[4]);
            t[fromMe ? 2 : 0]++;
            if (text) t[fromMe ? 3 : 1]++;

            TreeMap<String, Integer> s = signatures.get(r.type);
            if (s == null) signatures.put(r.type, s = new TreeMap<>());
            String sig = signature(m);
            s.put(sig, s.containsKey(sig) ? s.get(sig) + 1 : 1);

            for (Map.Entry<String, List<Object>> e : m.leaves.entrySet()) {
                boolean numericLeaf = false, equal = false;
                for (Object o : e.getValue()) {
                    if (!(o instanceof Long)) continue;
                    numericLeaf = true;
                    if ((Long) o == r.type) equal = true;
                }
                if (!numericLeaf) continue;
                int[] n = numeric.get(e.getKey());
                if (n == null) numeric.put(e.getKey(), n = new int[2]);
                n[0]++;
                TreeMap<Integer, Integer> p = presentByType.get(e.getKey());
                if (p == null) presentByType.put(e.getKey(), p = new TreeMap<>());
                bump(p, r.type);
                if (equal) {
                    n[1]++;
                    Set<Integer> ts = numericTypes.get(e.getKey());
                    if (ts == null) numericTypes.put(e.getKey(), ts = new HashSet<>());
                    ts.add(r.type);
                }
            }
        }

        String report() {
            StringBuilder b = new StringBuilder();
            b.append("  increment messages ").append(messages).append(": matched to the newest backup by row id and key_id ")
                    .append(matched).append("; no row id ").append(noRowId).append(", row id not in the backup ").append(notInBackup)
                    .append(", key_id differs ").append(keyIdDiffers).append('\n');
            b.append("  by the backup's type {type=received/with text, from me/with text}: {");
            boolean first = true;
            for (Map.Entry<Integer, int[]> e : byType.entrySet()) {
                int[] t = e.getValue();
                b.append(first ? "" : ", ").append(e.getKey()).append('=').append(t[0]).append('/').append(t[1])
                        .append(", ").append(t[2]).append('/').append(t[3]);
                first = false;
            }
            b.append("}\n");
            b.append("  content field numbers (1.2.N present), by the backup's type:\n");
            for (Map.Entry<Integer, TreeMap<String, Integer>> e : signatures.entrySet()) {
                List<Map.Entry<String, Integer>> l = new ArrayList<>(e.getValue().entrySet());
                Collections.sort(l, (x, y) -> y.getValue() != x.getValue().intValue() ? y.getValue() - x.getValue() : x.getKey().compareTo(y.getKey()));
                b.append("    type ").append(e.getKey()).append(": ");
                for (int i = 0; i < l.size() && i < MAX_SIGNATURES; i++) {
                    b.append(i == 0 ? "" : ", ").append(l.get(i).getKey()).append(" ×").append(l.get(i).getValue());
                }
                if (l.size() > MAX_SIGNATURES) b.append(", +").append(l.size() - MAX_SIGNATURES).append(" more shapes");
                b.append('\n');
            }
            b.append("  numeric fields equal to the backup's type (present on ≥").append(MIN_SEEN)
                    .append(" matched, equal on ≥90% of those, across ≥2 types):\n");
            List<String> cands = new ArrayList<>();
            for (Map.Entry<String, int[]> e : numeric.entrySet()) {
                int[] n = e.getValue();
                Set<Integer> ts = numericTypes.get(e.getKey());
                if (n[0] >= MIN_SEEN && n[1] * 10 >= n[0] * 9 && ts != null && ts.size() >= 2) cands.add(e.getKey());
            }
            Collections.sort(cands, (x, y) -> numeric.get(y)[1] != numeric.get(x)[1] ? numeric.get(y)[1] - numeric.get(x)[1] : x.compareTo(y));
            if (cands.isEmpty()) b.append("    none — no numeric field tracks the type\n");
            for (int i = 0; i < cands.size() && i < MAX_CANDIDATES; i++) {
                String p = cands.get(i);
                int[] n = numeric.get(p);
                b.append("    ").append(p).append(": present ").append(n[0]).append(", equal ").append(n[1])
                        .append(", types equal ").append(new TreeSet<>(numericTypes.get(p)))
                        .append("; absent on matched, by type ").append(absent(p)).append('\n');
            }
            if (cands.size() > MAX_CANDIDATES) b.append("    +").append(cands.size() - MAX_CANDIDATES).append(" more\n");
            return b.toString();
        }

        private TreeMap<Integer, Integer> absent(String path) {
            TreeMap<Integer, Integer> out = new TreeMap<>();
            TreeMap<Integer, Integer> p = presentByType.get(path);
            for (Map.Entry<Integer, Integer> e : matchedByType.entrySet()) {
                int present = p == null || !p.containsKey(e.getKey()) ? 0 : p.get(e.getKey());
                if (e.getValue() - present > 0) out.put(e.getKey(), e.getValue() - present);
            }
            return out;
        }
    }

    /** The content block's own field numbers (1.2.N), e.g. "{1}" or "{3,24}"; "{}" when there is no content. */
    static String signature(ProbeFieldMap.Msg m) {
        TreeSet<Integer> n = new TreeSet<>();
        for (String p : m.leaves.keySet()) {
            if (!p.startsWith("1.2.")) continue;
            int dot = p.indexOf('.', 4);
            try {
                n.add(Integer.parseInt(dot < 0 ? p.substring(4) : p.substring(4, dot)));
            } catch (NumberFormatException ignored) {
                // a path is digits and dots by construction; nothing else to count
            }
        }
        StringBuilder b = new StringBuilder("{");
        for (Integer x : n) b.append(b.length() == 1 ? "" : ",").append(x);
        return b.append('}').toString();
    }

    private static void bump(TreeMap<Integer, Integer> m, int k) {
        m.put(k, m.containsKey(k) ? m.get(k) + 1 : 1);
    }
}
