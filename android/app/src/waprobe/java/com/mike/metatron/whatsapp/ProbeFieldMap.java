package com.mike.metatron.whatsapp;

import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Probe only — P3 step 1: confirm the field map of an increment's messages.bin BY COUNTS (clean-room
 * rule 5: a mapping is adopted only when counts on Mike's data show it, never from memory of any
 * published schema). Plain Java, so it runs under testWaprobeUnitTest.
 *
 * messages.bin is walked as the generic protobuf wire format (ProbeShapes' varint and message
 * tests). Every scalar leaf of every message is held, by path relative to the message, IN MEMORY
 * ONLY; {@link Decoded#wipe} drops them. Each message is matched to a full backup's message row by
 * the key_id candidate, and every candidate field is compared with the column it is thought to be.
 * Independently of the candidates, every leaf is searched for the column's value, so a field the
 * candidates miss shows up as a path with a count.
 *
 * THE REPORT CARRIES COUNTS AND FIELD PATHS ONLY — never a value, a length of a value beyond a
 * range, or a name. Tests plant values and assert their absence.
 */
final class ProbeFieldMap {
    /** Candidate paths, relative to a message block (record.2.2). From the 11-23 shapes; on trial here. */
    static final String KEY_JID = "1.1.1", KEY_FLAG = "1.1.2", KEY_ID = "1.1.3", TIME = "1.3", SENDER = "1.5",
            TEXT_A = "1.2.1", TEXT_B = "1.2.6.1", ROW_ID = "2";
    static final int MAX_DEPTH = 12;

    /** One message: its chat block's jid candidate (record.2.1) and every scalar leaf by relative path. */
    static final class Msg {
        String chatJid;
        final Map<String, List<Object>> leaves = new LinkedHashMap<>();

        String text(String path) {
            List<Object> v = leaves.get(path);
            if (v == null) return null;
            for (Object o : v) if (o instanceof String) return (String) o;
            return null;
        }

        Long num(String path) {
            List<Object> v = leaves.get(path);
            if (v == null) return null;
            for (Object o : v) if (o instanceof Long) return (Long) o;
            return null;
        }

        void add(String path, Object v) {
            List<Object> l = leaves.get(path);
            if (l == null) leaves.put(path, l = new ArrayList<>());
            l.add(v);
        }
    }

    static final class Decoded {
        final List<Msg> msgs = new ArrayList<>();
        int records, chatBlocks, chatBlocksWithoutJid;
        /** Non-null when the bytes are not varint-length-delimited wire records. */
        String malformed;

        void wipe() {
            for (Msg m : msgs) m.leaves.clear();
            msgs.clear();
        }
    }

    /** One full-backup message row, as the comparison needs it. Held in memory only. */
    static final class Row {
        long id;
        int fromMe, messageType;
        long timestamp;
        String chatJid, senderJid, text;
    }

    /** What a decrypted full backup answers. SQLite on the phone (ProbeFieldMapRun); faked in tests. */
    interface Rows {
        /** Every row whose key_id equals this one; empty when none. */
        List<Row> byKeyId(String keyId);
        boolean hasMessageId(long id);
        /** The row with this message._id, or null. */
        Row byId(long id);
        /** True when jid_map links the two raw strings (either way round). */
        boolean linked(String a, String b);
    }

    private ProbeFieldMap() {}

    // ---- decode ------------------------------------------------------------------------------

    static Decoded decode(byte[] d) {
        Decoded out = new Decoded();
        List<int[]> recs = ProbeShapes.delimited(d);
        if (recs == null) {
            out.malformed = ProbeShapes.isMessage(d, 0, d.length) ? "one undelimited message (not the observed shape)" : "not wire-format records";
            if (!ProbeShapes.isMessage(d, 0, d.length)) return out;
            recs = Collections.singletonList(new int[]{0, d.length});
        }
        out.records = recs.size();
        for (int[] r : recs) record(d, r[0], r[1], out);
        return out;
    }

    private static void record(byte[] d, int off, int end, Decoded out) {
        int pos = off;
        while (pos < end) {
            long[] t = ProbeShapes.varint(d, pos, end);
            int field = (int) (t[0] >>> 3), wt = (int) (t[0] & 7);
            pos = (int) t[1];
            if (wt != 2) { pos = skip(d, pos, end, wt); continue; }
            long[] l = ProbeShapes.varint(d, pos, end);
            int s = (int) l[1], e = s + (int) l[0];
            pos = e;
            if (field == 2 && ProbeShapes.isMessage(d, s, e)) chat(d, s, e, out);
        }
    }

    /** A chat block (record.2): .1 a jid, .2 messages. Two passes so the jid is known whatever the order. */
    private static void chat(byte[] d, int off, int end, Decoded out) {
        out.chatBlocks++;
        String jid = null;
        List<int[]> messages = new ArrayList<>();
        int pos = off;
        while (pos < end) {
            long[] t = ProbeShapes.varint(d, pos, end);
            int field = (int) (t[0] >>> 3), wt = (int) (t[0] & 7);
            pos = (int) t[1];
            if (wt != 2) { pos = skip(d, pos, end, wt); continue; }
            long[] l = ProbeShapes.varint(d, pos, end);
            int s = (int) l[1], e = s + (int) l[0];
            pos = e;
            if (field == 1 && jid == null && ProbeShapes.isText(d, s, e)) jid = new String(d, s, e - s, StandardCharsets.UTF_8);
            else if (field == 2 && ProbeShapes.isMessage(d, s, e)) messages.add(new int[]{s, e});
        }
        if (jid == null) out.chatBlocksWithoutJid++;
        for (int[] m : messages) {
            Msg msg = new Msg();
            msg.chatJid = jid;
            leaves(d, m[0], m[1], "", 0, msg);
            out.msgs.add(msg);
        }
    }

    /**
     * Every scalar leaf, by path. Bytes that are text are a text leaf; text that ALSO tiles as a
     * message (a sub-message starting 0x0a 0x0a, say) is walked as well, so neither reading is lost.
     */
    private static void leaves(byte[] d, int off, int end, String path, int depth, Msg msg) {
        int pos = off;
        while (pos < end) {
            long[] t = ProbeShapes.varint(d, pos, end);
            int field = (int) (t[0] >>> 3), wt = (int) (t[0] & 7);
            pos = (int) t[1];
            String p = path.isEmpty() ? String.valueOf(field) : path + "." + field;
            if (wt == 0) {
                long[] v = ProbeShapes.varint(d, pos, end);
                pos = (int) v[1];
                msg.add(p, v[0]);
            } else if (wt == 2) {
                long[] l = ProbeShapes.varint(d, pos, end);
                int s = (int) l[1], e = s + (int) l[0];
                pos = e;
                boolean text = ProbeShapes.isText(d, s, e);
                if (text) msg.add(p, new String(d, s, e - s, StandardCharsets.UTF_8));
                if (depth < MAX_DEPTH && (!text || e - s > 1) && ProbeShapes.isMessage(d, s, e)) leaves(d, s, e, p, depth + 1, msg);
            } else {
                pos = skip(d, pos, end, wt);
            }
        }
    }

    private static int skip(byte[] d, int pos, int end, int wt) {
        if (wt == 0) return (int) ProbeShapes.varint(d, pos, end)[1];
        if (wt == 1) return pos + 8;
        if (wt == 5) return pos + 4;
        long[] l = ProbeShapes.varint(d, pos, end);
        return (int) (l[1] + l[0]);
    }

    // ---- compare -----------------------------------------------------------------------------

    /** Text outcome per message against one backup, kept so two backups can be crossed (edits). */
    static final int T_NONE = 0, T_EQUAL = 1, T_DIFFERS = 2, T_NOT_MATCHED = 3;

    /** The candidate text: TEXT_A, else TEXT_B. */
    static String candidateText(Msg m) {
        String a = m.text(TEXT_A);
        return a != null ? a : m.text(TEXT_B);
    }

    /**
     * Agreement counts for one increment's messages against one full backup. Returns the per-message
     * text outcome (T_*) so {@link #edits} can cross two backups.
     */
    static int[] compare(List<Msg> msgs, Rows rows, String label, StringBuilder b) {
        int[] textOutcome = new int[msgs.size()];
        int noKey = 0, matched = 0, unmatched = 0, ambiguous = 0, resolved = 0;
        Tally flag = new Tally("key flag " + KEY_FLAG + " vs from_me");
        Tally time = new Tally("time " + TIME + " vs timestamp/1000");
        int timeWithin1 = 0;
        Tally chatJid = new Tally("chat block jid (record.2.1) vs chat's jid.raw_string");
        Tally keyJid = new Tally("key jid " + KEY_JID + " vs chat's jid.raw_string");
        int chatJidLinked = 0, keyJidLinked = 0;
        Tally sender = new Tally("sender " + SENDER + " vs sender's raw_string (group rows, not from me)");
        int senderLinked = 0, senderOnFromMe = 0, senderOnOneToOne = 0, groupRowsNoBackupSender = 0;
        Tally rowId = new Tally("row id " + ROW_ID + " vs message._id");
        int[][] text = new int[2][5]; // [candidate][equal, differs, absent while backup has text, present while backup null, both absent]
        int anyEqual = 0, backupHasText = 0, foundNowhere = 0;
        Map<String, Integer> textFoundAt = new TreeMap<>(), timeFoundAt = new TreeMap<>(), timeMsFoundAt = new TreeMap<>(),
                idFoundAt = new TreeMap<>(), chatFoundAt = new TreeMap<>(), senderFoundAt = new TreeMap<>(),
                otherTextWhenNoCandidate = new TreeMap<>();

        for (int i = 0; i < msgs.size(); i++) {
            Msg m = msgs.get(i);
            textOutcome[i] = T_NOT_MATCHED;
            String key = m.text(KEY_ID);
            if (key == null) { noKey++; continue; }
            List<Row> found = rows.byKeyId(key);
            Row r;
            if (found.isEmpty()) { unmatched++; continue; }
            if (found.size() == 1) {
                r = found.get(0);
            } else {
                ambiguous++;
                r = null;
                for (Row c : found) {
                    if (c.chatJid != null && c.chatJid.equals(m.chatJid)) {
                        if (r != null) { r = null; break; }
                        r = c;
                    }
                }
                if (r == null) continue;
                resolved++;
            }
            matched++;

            Long f = m.num(KEY_FLAG);
            flag.add(f == null ? null : f == r.fromMe);
            Long s = m.num(TIME);
            time.add(s == null ? null : s == r.timestamp / 1000);
            if (s != null && s != r.timestamp / 1000 && Math.abs(s * 1000 - r.timestamp) <= 1000) timeWithin1++;
            Boolean cj = eq(m.chatJid, r.chatJid);
            chatJid.add(cj);
            if (Boolean.FALSE.equals(cj) && rows.linked(m.chatJid, r.chatJid)) chatJidLinked++;
            String kj = m.text(KEY_JID);
            Boolean kjEq = eq(kj, r.chatJid);
            keyJid.add(kjEq);
            if (Boolean.FALSE.equals(kjEq) && rows.linked(kj, r.chatJid)) keyJidLinked++;

            String snd = m.text(SENDER);
            boolean group = r.chatJid != null && r.chatJid.endsWith("@g.us");
            if (group && r.fromMe == 0) {
                if (r.senderJid == null) groupRowsNoBackupSender++;
                else {
                    Boolean se = eq(snd, r.senderJid);
                    sender.add(se);
                    if (Boolean.FALSE.equals(se) && rows.linked(snd, r.senderJid)) senderLinked++;
                }
            } else if (snd != null) {
                if (r.fromMe == 1) senderOnFromMe++;
                else senderOnOneToOne++;
            }

            Long rid = m.num(ROW_ID);
            rowId.add(rid == null ? null : rid == r.id);

            String[] cand = {m.text(TEXT_A), m.text(TEXT_B)};
            for (int c = 0; c < 2; c++) {
                if (cand[c] != null && r.text != null) text[c][cand[c].equals(r.text) ? 0 : 1]++;
                else if (cand[c] == null && r.text != null) text[c][2]++;
                else if (cand[c] != null) text[c][3]++;
                else text[c][4]++;
            }
            String ct = candidateText(m);
            textOutcome[i] = r.text == null ? (ct == null ? T_NONE : T_DIFFERS) : (ct == null ? T_DIFFERS : ct.equals(r.text) ? T_EQUAL : T_DIFFERS);
            if (r.text != null) {
                backupHasText++;
                boolean any = false;
                for (Map.Entry<String, List<Object>> e : m.leaves.entrySet()) {
                    if (e.getValue().contains(r.text)) { bump(textFoundAt, e.getKey()); any = true; }
                }
                if (any) anyEqual++; else foundNowhere++;
            }
            if (cand[0] == null && cand[1] == null) {
                for (Map.Entry<String, List<Object>> e : m.leaves.entrySet()) {
                    if (e.getKey().equals(KEY_ID) || e.getKey().equals(KEY_JID) || e.getKey().equals(SENDER)) continue;
                    for (Object o : e.getValue()) {
                        if (o instanceof String && proseLike((String) o)) { bump(otherTextWhenNoCandidate, e.getKey()); break; }
                    }
                }
            }
            search(m, r.timestamp / 1000, timeFoundAt);
            search(m, r.timestamp, timeMsFoundAt);
            search(m, r.id, idFoundAt);
            if (r.chatJid != null) search(m, r.chatJid, chatFoundAt);
            if (r.senderJid != null) search(m, r.senderJid, senderFoundAt);
        }

        b.append("  vs ").append(label).append(": matched by key_id ").append(KEY_ID).append(' ').append(matched)
                .append(" of ").append(msgs.size()).append(" (not in this backup ").append(unmatched)
                .append(", no key_id ").append(noKey).append(", key_id on more than one row ").append(ambiguous)
                .append(" of which settled by chat ").append(resolved).append(")\n");
        if (matched == 0) return textOutcome;
        flag.line(b);
        time.line(b);
        if (timeWithin1 > 0) b.append("      (of the differing, within 1 s: ").append(timeWithin1).append(")\n");
        chatJid.line(b);
        if (chatJidLinked > 0) b.append("      (of the differing, linked by jid_map: ").append(chatJidLinked).append(")\n");
        keyJid.line(b);
        if (keyJidLinked > 0) b.append("      (of the differing, linked by jid_map: ").append(keyJidLinked).append(")\n");
        sender.line(b);
        if (senderLinked > 0) b.append("      (of the differing, linked by jid_map: ").append(senderLinked).append(")\n");
        b.append("    group rows not from me with no backup sender: ").append(groupRowsNoBackupSender)
                .append("; ").append(SENDER).append(" present on from-me rows ").append(senderOnFromMe)
                .append(", on one-to-one rows ").append(senderOnOneToOne).append('\n');
        rowId.line(b);
        String[] names = {TEXT_A, TEXT_B};
        for (int c = 0; c < 2; c++) {
            b.append("    text ").append(names[c]).append(" vs text_data: equal ").append(text[c][0]).append(", differs ")
                    .append(text[c][1]).append(", absent while backup has text ").append(text[c][2])
                    .append(", present while backup null ").append(text[c][3]).append(", both absent ").append(text[c][4]).append('\n');
        }
        b.append("    text_data non-null on ").append(backupHasText).append(" matched rows: equal to some leaf ").append(anyEqual)
                .append(", found nowhere in the message ").append(foundNowhere).append('\n');
        found(b, "text_data", textFoundAt);
        found(b, "timestamp/1000", timeFoundAt);
        found(b, "timestamp (ms)", timeMsFoundAt);
        found(b, "message._id", idFoundAt);
        found(b, "chat jid", chatFoundAt);
        found(b, "sender jid", senderFoundAt);
        if (!otherTextWhenNoCandidate.isEmpty()) found(b, "prose-like text on messages with neither text candidate", otherTextWhenNoCandidate);
        return textOutcome;
    }

    /** Crosses the text outcomes against two backups: differs from the older, equals the newer — an edit's signature. */
    static void edits(int[] base, int[] newest, StringBuilder b) {
        int edit = 0, both = 0, neither = 0;
        for (int i = 0; i < base.length && i < newest.length; i++) {
            if (base[i] == T_DIFFERS && newest[i] == T_EQUAL) edit++;
            else if (base[i] == T_EQUAL && newest[i] == T_EQUAL) both++;
            else if (base[i] == T_DIFFERS && newest[i] == T_DIFFERS) neither++;
        }
        b.append("  text vs base and newest: differs from base but equals newest ").append(edit)
                .append(", equals both ").append(both).append(", differs from both ").append(neither).append('\n');
    }

    /** Within the increment alone: the chat block jid vs the key jid, and key_id repeats. */
    static void selfChecks(Decoded dec, StringBuilder b) {
        int eq = 0, ne = 0, missing = 0, multiKey = 0, distinctIds = 0;
        java.util.Set<String> ids = new java.util.HashSet<>();
        for (Msg m : dec.msgs) {
            String kj = m.text(KEY_JID);
            if (kj == null || m.chatJid == null) missing++;
            else if (kj.equals(m.chatJid)) eq++;
            else ne++;
            List<Object> k = m.leaves.get(KEY_ID);
            if (k != null && k.size() > 1) multiKey++;
            String key = m.text(KEY_ID);
            if (key != null && ids.add(key)) distinctIds++;
        }
        b.append("  records ").append(dec.records).append(", chat blocks ").append(dec.chatBlocks)
                .append(dec.chatBlocksWithoutJid > 0 ? " (" + dec.chatBlocksWithoutJid + " without a jid)" : "")
                .append(", messages ").append(dec.msgs.size()).append(", distinct key_ids ").append(distinctIds).append('\n');
        b.append("  key jid ").append(KEY_JID).append(" vs its chat block's jid: equal ").append(eq).append(", differs ").append(ne)
                .append(", one missing ").append(missing).append("; messages with more than one ").append(KEY_ID).append(": ").append(multiKey).append('\n');
    }

    /** Ids from a {"deleted_ids":[...]} entry; empty when absent. Numbers only. */
    static List<Long> deletedIds(byte[] json) {
        String s = new String(json, StandardCharsets.UTF_8);
        List<Long> out = new ArrayList<>();
        Matcher m = Pattern.compile("\"deleted_ids\"\\s*:\\s*\\[([^\\]]*)\\]").matcher(s);
        if (!m.find()) return out;
        for (String part : m.group(1).split(",")) {
            String t = part.trim();
            if (t.isEmpty()) continue;
            try { out.add(Long.parseLong(t)); } catch (NumberFormatException e) { /* counted as absent */ }
        }
        return out;
    }

    /** Row-id candidates (ROW_ID) of these messages — for matching deletions to earlier increments. */
    static java.util.Set<Long> rowIds(List<Msg> msgs) {
        java.util.Set<Long> out = new java.util.HashSet<>();
        for (Msg m : msgs) { Long r = m.num(ROW_ID); if (r != null) out.add(r); }
        return out;
    }

    // ---- round 2 (11-23): text by priority, deletions, the record's other fields ---------------

    /** Every path where text_data was found on 11-23's first tap, in the order a reader would try them. */
    static final String[] TEXT_PATHS = {"1.2.1", "1.2.6.1", "1.2.3.3", "1.2.12.14.1", "1.2.12.14.6.1", "1.2.75.3", "1.2.6.2", "1.26"};
    /** The rule on trial: the first of these present is the text. 1.2.6.2 and 1.26 are measured, not in the rule. */
    static final int RULE_LEN = 6;

    static String ruleText(Msg m) {
        for (int i = 0; i < RULE_LEN; i++) {
            String t = m.text(TEXT_PATHS[i]);
            if (t != null) return t;
        }
        return null;
    }

    /**
     * Per text path: equal / differs / present while text_data is null; then the priority rule as a
     * whole. And for each deleted id: is the row still in this backup, with text or not, by
     * message_type; and does this increment re-send it, with rule text or not.
     */
    static void round2(List<Msg> msgs, List<Long> deleted, Rows rows, StringBuilder b) {
        int[][] per = new int[TEXT_PATHS.length][3];
        int ruleEq = 0, ruleDiff = 0, ruleNone = 0, ruleExtra = 0, bothNone = 0;
        Map<Long, Msg> byRow = new LinkedHashMap<>();
        for (Msg m : msgs) {
            Long rid = m.num(ROW_ID);
            if (rid != null) byRow.put(rid, m);
            String key = m.text(KEY_ID);
            if (key == null) continue;
            Row r = pick(rows.byKeyId(key), m, rows);
            if (r == null) continue;
            for (int i = 0; i < TEXT_PATHS.length; i++) {
                String t = m.text(TEXT_PATHS[i]);
                if (t == null) continue;
                if (r.text == null) per[i][2]++;
                else per[i][t.equals(r.text) ? 0 : 1]++;
            }
            String rt = ruleText(m);
            if (r.text != null && rt != null) { if (rt.equals(r.text)) ruleEq++; else ruleDiff++; }
            else if (r.text != null) ruleNone++;
            else if (rt != null) ruleExtra++;
            else bothNone++;
        }
        b.append("    round 2 — text per path (equal / differs / present while text_data null):");
        for (int i = 0; i < TEXT_PATHS.length; i++) {
            if (per[i][0] + per[i][1] + per[i][2] == 0) continue;
            b.append(' ').append(TEXT_PATHS[i]).append(' ').append(per[i][0]).append('/').append(per[i][1]).append('/').append(per[i][2]).append(';');
        }
        b.append('\n');
        b.append("    round 2 — rule (first present of ").append(String.join(", ", Arrays.asList(TEXT_PATHS).subList(0, RULE_LEN)))
                .append(") vs text_data: equal ").append(ruleEq).append(", differs ").append(ruleDiff)
                .append(", none while backup has text ").append(ruleNone).append(", text while backup null ").append(ruleExtra)
                .append(", both none ").append(bothNone).append('\n');
        if (deleted.isEmpty()) return;
        int gone = 0, keptText = 0, keptNoText = 0, resent = 0, resentText = 0, resentSameKey = 0;
        Map<Integer, Integer> types = new TreeMap<>();
        for (Long d : deleted) {
            Row r = rows.byId(d);
            Msg m = byRow.get(d);
            if (m != null) {
                resent++;
                if (ruleText(m) != null) resentText++;
                if (r != null && m.text(KEY_ID) != null && !rows.byKeyId(m.text(KEY_ID)).isEmpty()
                        && rows.byKeyId(m.text(KEY_ID)).get(0).id == r.id) resentSameKey++;
            }
            if (r == null) { gone++; continue; }
            if (r.text == null) keptNoText++; else keptText++;
            Integer v = types.get(r.messageType);
            types.put(r.messageType, v == null ? 1 : v + 1);
        }
        b.append("    round 2 — deleted ids ").append(deleted.size()).append(": row absent here ").append(gone)
                .append(", present with text_data ").append(keptText).append(", present without ").append(keptNoText)
                .append("; message_type of those present ").append(types)
                .append("; re-sent in this increment ").append(resent).append(" (with rule text ").append(resentText)
                .append(", same key_id as this row ").append(resentSameKey).append(")\n");
    }

    /** The row for a message: the only one, or the one whose chat equals (or jid_map-links) the message's chat. */
    static Row pick(List<Row> found, Msg m, Rows rows) {
        if (found.size() == 1) return found.get(0);
        Row hit = null;
        for (Row c : found) {
            if (c.chatJid == null || m.chatJid == null) continue;
            if (c.chatJid.equals(m.chatJid) || rows.linked(c.chatJid, m.chatJid)) {
                if (hit != null) return null;
                hit = c;
            }
        }
        return hit;
    }

    /** Top-level fields of each record, and every path in the whole record holding a known key_id. */
    static void census(byte[] d, java.util.Set<String> keyIds, StringBuilder b) {
        List<int[]> recs = ProbeShapes.delimited(d);
        if (recs == null) return;
        Map<String, Integer> top = new TreeMap<>();
        Msg bag = new Msg();
        for (int[] r : recs) {
            int pos = r[0];
            while (pos < r[1]) {
                long[] t = ProbeShapes.varint(d, pos, r[1]);
                int field = (int) (t[0] >>> 3), wt = (int) (t[0] & 7);
                bump(top, field + (wt == 2 ? "(len)" : wt == 0 ? "(varint)" : "(fixed)"));
                pos = skip(d, (int) t[1], r[1], wt);
            }
            leaves(d, r[0], r[1], "rec", 0, bag);
        }
        Map<String, Integer> keyAt = new TreeMap<>();
        for (Map.Entry<String, List<Object>> e : bag.leaves.entrySet()) {
            int n = 0;
            for (Object o : e.getValue()) if (o instanceof String && keyIds.contains(o)) n++;
            if (n > 0) keyAt.put(e.getKey(), n);
        }
        bag.leaves.clear();
        b.append("  round 2 — top-level fields: ").append(top).append('\n');
        found(b, "  round 2 — a full-backup key_id", keyAt);
    }

    private static final Pattern FORMAT_VERSION = Pattern.compile("\"format_version\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern FORMAT = Pattern.compile("\"format\"\\s*:\\s*\"([^\"]*)\"");
    private static final Pattern FILENAME = Pattern.compile("\"filename\"\\s*:\\s*\"([^\"]*)\"");

    /**
     * header.json's format markers. A value is shown only when its shape rules out anything personal:
     * format_version only if digits and dots, format only if lower-case letters/underscore; the
     * messages filename only as "equals messages.bin" yes/no.
     */
    static String headerMarkers(byte[] header) {
        String s = new String(header, StandardCharsets.UTF_8);
        StringBuilder b = new StringBuilder();
        Matcher v = FORMAT_VERSION.matcher(s);
        b.append("format_version ").append(!v.find() ? "(absent)" : v.group(1).matches("[0-9.]{1,8}") ? v.group(1) : "(not digits-and-dots, length " + v.group(1).length() + ")");
        Matcher f = FORMAT.matcher(s);
        b.append(", added_messages.format ").append(!f.find() ? "(absent)" : f.group(1).matches("[a-z_]{1,16}") ? f.group(1) : "(other, length " + f.group(1).length() + ")");
        Matcher n = FILENAME.matcher(s);
        b.append(", filename is messages.bin: ").append(!n.find() ? "(absent)" : n.group(1).equals("messages.bin") ? "yes" : "no");
        return b.toString();
    }

    // ---- helpers -----------------------------------------------------------------------------

    /** equal / differs / null when the candidate (or the backup value) is absent. */
    private static Boolean eq(String candidate, String backup) {
        if (candidate == null || backup == null) return null;
        return candidate.equals(backup);
    }

    /** Looks like something a person wrote: contains a letter and a space, and is not a jid or URL. */
    static boolean proseLike(String s) {
        if (s.indexOf('@') >= 0 || s.startsWith("http") || s.startsWith("/")) return false;
        boolean letter = false;
        for (int i = 0; i < s.length(); i++) if (Character.isLetter(s.charAt(i))) { letter = true; break; }
        return letter && s.indexOf(' ') >= 0;
    }

    private static void search(Msg m, Object value, Map<String, Integer> at) {
        for (Map.Entry<String, List<Object>> e : m.leaves.entrySet()) if (e.getValue().contains(value)) bump(at, e.getKey());
    }

    private static void bump(Map<String, Integer> m, String k) {
        Integer v = m.get(k);
        m.put(k, v == null ? 1 : v + 1);
    }

    private static void found(StringBuilder b, String what, Map<String, Integer> at) {
        b.append("    ").append(what).append(" found at: ");
        if (at.isEmpty()) { b.append("nowhere\n"); return; }
        boolean first = true;
        for (Map.Entry<String, Integer> e : at.entrySet()) {
            b.append(first ? "" : ", ").append(e.getKey()).append(" ×").append(e.getValue());
            first = false;
        }
        b.append('\n');
    }

    /** equal / differs / candidate absent, for one candidate. */
    static final class Tally {
        final String what;
        int equal, differs, absent;

        Tally(String what) { this.what = what; }

        void add(Boolean r) {
            if (r == null) absent++;
            else if (r) equal++;
            else differs++;
        }

        void line(StringBuilder b) {
            b.append("    ").append(what).append(": equal ").append(equal).append(", differs ").append(differs)
                    .append(", absent ").append(absent).append('\n');
        }
    }

    /** For tests and the caller: zero a byte array (the entry bytes are the caller's to wipe). */
    static void zero(byte[] b) {
        if (b != null) Arrays.fill(b, (byte) 0);
    }
}
