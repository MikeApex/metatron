package com.mike.metatron.whatsapp;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * "6. Field map counts" — P3 step 1. Every increment in the folder, grouped into its set, is
 * decoded (ProbeFieldMap) and matched by key_id to the newest full backup and to its set's own
 * base, and the agreement of each candidate field is counted. Counts and field paths only; every
 * decrypted copy is deleted and every held entry zeroed before returning.
 */
final class ProbeFieldMapRun {
    static final int MAX_INCREMENTS = 24;
    private static final Pattern HEADER_COUNT = Pattern.compile("\"(messages_count_on_backup|messages_updated|messages_deleted)\"\\s*:\\s*(\\d+)");
    private static final String[] SHAPED = {"header.json", "jid_modified_", "jid_map_modified_", "lid_display_name_modified_",
            "chat_modified_", "jid_deleted_", "jid_map_deleted_", "lid_display_name_deleted_", "chat_deleted_", "deletedMessages_"};

    private ProbeFieldMapRun() {}

    /** One increment file, decoded. */
    private static final class Inc {
        File file;
        String set; // null = live (undated)
        long n;
        ProbeFieldMap.Decoded dec;
        List<Long> deleted = new ArrayList<>();
        String headerCounts = "", headerMarkers = "";
        byte[] bin; // held only between decode and the newest backup's census; zeroed there
        String error;
        final StringBuilder out = new StringBuilder();
        int[] baseText, newestText;
    }

    static String run(Context ctx) {
        StringBuilder b = new StringBuilder("== FIELD MAP COUNTS (P3 step 1) ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File work = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        work.mkdirs();
        File fullOut = new File(work, ProbePayload.PREFIX + "full.db");
        BackupKey[] key = {null};
        List<Inc> incs = new ArrayList<>();
        try {
            steps(ctx, b, work, fullOut, key, incs);
        } catch (BackupException e) {
            b.append("REFUSED: ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
        } finally {
            for (Inc i : incs) {
                if (i.dec != null) i.dec.wipe();
                ProbeFieldMap.zero(i.bin);
            }
            if (key[0] != null) key[0].destroy();
            BackupDecryptor.deleteDecrypted(fullOut);
            int left = ProbePayload.sweep(work);
            b.append("decrypted copies deleted: ").append(fullOut.exists() || left > 0 ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        return b.toString();
    }

    private static void steps(Context ctx, StringBuilder b, File work, File fullOut, BackupKey[] key, List<Inc> incs) throws Exception {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            b.append("All-files access: NOT GRANTED — step 2\n");
            return;
        }
        File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
        File[] files = dir.listFiles();
        if (files == null) throw new BackupException(BackupError.NO_BACKUP_FOUND);

        b.append("\n-- the folder (names, sizes, written) --\n");
        List<File> sorted = new ArrayList<>(Arrays.asList(files));
        Collections.sort(sorted, (x, y) -> x.getName().compareTo(y.getName()));
        for (File f : sorted) {
            if (!f.isFile()) continue;
            b.append("  ").append(ProbePayload.maskDigits(f.getName())).append("  ").append(f.length())
                    .append("  ").append(ProbeReport.ts(f.lastModified())).append('\n');
        }

        // Sets: live (undated) and one per rotation date; each in N order.
        TreeMap<String, List<Inc>> sets = new TreeMap<>();
        for (File f : sorted) {
            Matcher m = ProbeLines.INCREMENT.matcher(f.getName());
            if (!f.isFile() || !m.matches()) continue;
            Inc i = new Inc();
            i.file = f;
            i.set = m.group(2);
            i.n = Long.parseLong(m.group(1));
            String k = i.set == null ? "~live" : i.set;
            if (!sets.containsKey(k)) sets.put(k, new ArrayList<>());
            sets.get(k).add(i);
        }
        if (sets.isEmpty()) {
            b.append("no increment files — try after 02:00\n");
            return;
        }
        b.append("\n-- sets --\n");
        for (Map.Entry<String, List<Inc>> e : sets.entrySet()) {
            Collections.sort(e.getValue(), (x, y) -> Long.compare(x.n, y.n));
            List<Long> ns = new ArrayList<>();
            for (Inc i : e.getValue()) ns.add(i.n);
            File base = base(dir, e.getValue().get(0).set);
            b.append("  ").append(e.getKey().equals("~live") ? "live (undated)" : "rotated " + e.getKey())
                    .append(": N ").append(ns).append(gap(ns)).append("; base ")
                    .append(base.isFile() ? base.getName() + " written " + ProbeReport.ts(base.lastModified())
                            + (base.lastModified() < e.getValue().get(0).file.lastModified() ? " (before increment " + ns.get(0) + ")" : " (NOT before increment " + ns.get(0) + ")")
                            : "not found by name").append('\n');
            for (Inc i : e.getValue()) if (incs.size() < MAX_INCREMENTS) incs.add(i);
        }

        byte[] root = ProbeKeyVault.load(ctx);
        if (root == null) {
            b.append("no key stored — step 3\n");
            return;
        }
        try {
            key[0] = BackupKey.fromRoot(root);
        } finally {
            Arrays.fill(root, (byte) 0);
        }

        // 1. Decode every increment; hold leaves in memory, wipe the entries at once.
        Inc newestInc = null;
        for (Inc i : incs) if (newestInc == null || i.file.lastModified() > newestInc.file.lastModified()) newestInc = i;
        for (Inc i : incs) decode(i, key[0], work, i == newestInc);

        // 2. Each full backup once: the newest, then each set's base.
        File newest = BackupLocator.newest(dir);
        Map<File, List<Inc>> asBase = new LinkedHashMap<>();
        for (Inc i : incs) {
            File base = base(dir, i.set);
            if (!base.isFile()) continue;
            if (!asBase.containsKey(base)) asBase.put(base, new ArrayList<>());
            asBase.get(base).add(i);
        }
        b.append("\n-- full backups compared --\n");
        compareWith(newest, incs, key[0], fullOut, b, "newest full backup (" + newest.getName() + ")", false, null);
        for (Map.Entry<File, List<Inc>> e : asBase.entrySet()) {
            compareWith(e.getKey(), e.getValue(), key[0], fullOut, b, "the set's base (" + e.getKey().getName() + ")", true, incs);
        }

        // 3. Per increment, in set and N order.
        for (Inc i : incs) {
            b.append("\n-- ").append(i.file.getName()).append("  ").append(i.file.length()).append(" bytes, written ")
                    .append(ProbeReport.ts(i.file.lastModified())).append(" --\n");
            if (i.error != null) {
                b.append("  ").append(i.error).append('\n');
                continue;
            }
            b.append("  header: ").append(i.headerCounts).append("; ").append(i.headerMarkers).append('\n');
            b.append(i.out);
            if (i.baseText != null && i.newestText != null) ProbeFieldMap.edits(i.baseText, i.newestText, b);
            // Deletions: by row id. Which earlier increment of the set carried them?
            if (!i.deleted.isEmpty()) {
                int inEarlier = 0, inThis = 0;
                java.util.Set<Long> own = ProbeFieldMap.rowIds(i.dec.msgs);
                java.util.Set<Long> earlier = new java.util.HashSet<>();
                for (Inc j : incs) {
                    if (j == i || j.dec == null || !eqSet(j.set, i.set) || j.n >= i.n) continue;
                    earlier.addAll(ProbeFieldMap.rowIds(j.dec.msgs));
                }
                for (Long d : i.deleted) {
                    if (own.contains(d)) inThis++;
                    if (earlier.contains(d)) inEarlier++;
                }
                b.append("  deleted ids ").append(i.deleted.size()).append(": equal to a row id ").append(ProbeFieldMap.ROW_ID)
                        .append(" in this increment ").append(inThis).append(", in an earlier increment of the set ").append(inEarlier).append('\n');
            }
        }
    }

    private static void decode(Inc i, BackupKey key, File work, boolean shapes) {
        ProbePayload.Inspection p = null;
        try {
            p = ProbePayload.inspect(i.file, key, work);
            if (!p.tagOk || p.zipIn == null) {
                i.error = "not a ZIP increment: " + p.branch;
                return;
            }
            byte[] bin = null, header = null;
            for (ProbePayload.Entry e : p.entries) {
                if (e.bytes == null) continue;
                if (e.name.equals("messages.bin")) bin = e.bytes;
                else if (e.name.equals("header.json")) header = e.bytes;
                else if (e.name.startsWith("deletedMessages_") && e.name.endsWith(".json")) i.deleted.addAll(ProbeFieldMap.deletedIds(e.bytes));
            }
            if (header != null) {
                i.headerMarkers = ProbeFieldMap.headerMarkers(header);
                Matcher m = HEADER_COUNT.matcher(new String(header, StandardCharsets.UTF_8));
                StringBuilder h = new StringBuilder();
                while (m.find()) h.append(h.length() == 0 ? "" : ", ").append(m.group(1)).append(' ').append(m.group(2));
                i.headerCounts = h.length() == 0 ? "(no counts found)" : h.toString();
            } else {
                i.headerCounts = "(no header.json)";
            }
            if (bin == null) {
                i.error = "no messages.bin held";
                return;
            }
            i.dec = ProbeFieldMap.decode(bin);
            i.bin = bin.clone();
            if (i.dec.malformed != null) i.out.append("  messages.bin: ").append(i.dec.malformed).append('\n');
            ProbeFieldMap.selfChecks(i.dec, i.out);
            if (shapes) {
                i.out.append("  shapes of the table entries this reader will need (newest increment only):\n");
                for (ProbePayload.Entry e : p.entries) {
                    if (e.bytes == null || !wanted(e.name)) continue;
                    StringBuilder s = new StringBuilder();
                    ProbeShapes.entry(e.name, e.bytes, ProbeShapes.NONE, s);
                    for (String line : s.toString().split("\n")) i.out.append("    ").append(line).append('\n');
                }
            }
        } catch (BackupException e) {
            i.error = "REFUSED: " + e.error.code;
        } catch (Throwable t) {
            i.error = "FAILED: " + t.getClass().getSimpleName();
        } finally {
            ProbePayload.wipe(p);
            ProbePayload.sweep(work);
        }
    }

    private static boolean wanted(String name) {
        for (String s : SHAPED) if (name.equals(s) || (s.endsWith("_") && name.startsWith(s) && name.endsWith(".json"))) return true;
        return false;
    }

    /**
     * Decrypts one full backup, compares the given increments with it, deletes the copy.
     * asBase: store the text outcome as the base's, else as the newest's.
     */
    private static void compareWith(File full, List<Inc> incs, BackupKey key, File fullOut, StringBuilder b, String label,
                                     boolean asBase, List<Inc> all) {
        SQLiteDatabase db = null;
        try {
            if (full.getName().equals(BackupLocator.CURRENT)) {
                BackupLocator.requireComplete(full, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
            } else if (System.currentTimeMillis() - full.lastModified() < BackupLocator.RECENT_WRITE_MS) {
                throw new BackupException(BackupError.BEING_WRITTEN);
            }
            BackupDecryptor.decrypt(full, key, fullOut, BackupDecryptor.FILESYSTEM);
            db = SQLiteDatabase.openDatabase(fullOut.getPath(), null, SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
            b.append("  ").append(label).append(": decrypted; message rows with a key_id ")
                    .append(longOf(db, "SELECT COUNT(*) FROM message WHERE key_id IS NOT NULL"))
                    .append(", distinct key_ids ").append(longOf(db, "SELECT COUNT(DISTINCT key_id) FROM message WHERE key_id IS NOT NULL"))
                    .append(", distinct (chat, from_me, key_id) ")
                    .append(longOf(db, "SELECT COUNT(*) FROM (SELECT DISTINCT chat_row_id, from_me, key_id FROM message WHERE key_id IS NOT NULL)"))
                    .append('\n');
            SqliteRows rows = new SqliteRows(db);
            java.util.Set<String> allKeys = null;
            List<String> keys = new ArrayList<>();
            for (Inc i : incs) if (i.dec != null) for (ProbeFieldMap.Msg m : i.dec.msgs) { String k = m.text(ProbeFieldMap.KEY_ID); if (k != null) keys.add(k); }
            rows.prefetch(keys);
            for (Inc i : incs) {
                if (i.dec == null) continue;
                int[] t = ProbeFieldMap.compare(i.dec.msgs, rows, label, i.out);
                if (asBase) i.baseText = t; else i.newestText = t;
                ProbeFieldMap.round2(i.dec.msgs, i.deleted, rows, i.out);
                if (!asBase && i.bin != null) {
                    if (allKeys == null) allKeys = rows.allKeyIds();
                    ProbeFieldMap.census(i.bin, allKeys, i.out);
                    ProbeFieldMap.zero(i.bin);
                    i.bin = null;
                }
                if (!i.deleted.isEmpty()) {
                    int present = 0;
                    for (Long d : i.deleted) if (rows.hasMessageId(d)) present++;
                    i.out.append("    deleted ids present as message._id here: ").append(present).append(" of ").append(i.deleted.size()).append('\n');
                }
            }
        } catch (BackupException e) {
            b.append("  ").append(label).append(": not compared — ").append(e.error.code).append('\n');
        } catch (Throwable t) {
            b.append("  ").append(label).append(": FAILED — ").append(t.getClass().getSimpleName()).append('\n');
        } finally {
            if (db != null) db.close();
            BackupDecryptor.deleteDecrypted(fullOut);
        }
    }

    private static final class SqliteRows implements ProbeFieldMap.Rows {
        private final SQLiteDatabase db;
        private final Map<String, List<ProbeFieldMap.Row>> byKey = new HashMap<>();

        static final String SELECT = "SELECT m.key_id, m._id, m.from_me, m.timestamp, cj.raw_string, sj.raw_string, m.text_data, m.message_type "
                + "FROM message m LEFT JOIN chat c ON c._id = m.chat_row_id LEFT JOIN jid cj ON cj._id = c.jid_row_id "
                + "LEFT JOIN jid sj ON sj._id = m.sender_jid_row_id ";

        SqliteRows(SQLiteDatabase db) { this.db = db; }

        static ProbeFieldMap.Row row(Cursor c) {
            ProbeFieldMap.Row r = new ProbeFieldMap.Row();
            r.id = c.getLong(1);
            r.fromMe = c.getInt(2);
            r.timestamp = c.getLong(3);
            r.chatJid = c.isNull(4) ? null : c.getString(4);
            r.senderJid = c.isNull(5) ? null : c.getString(5);
            r.text = c.isNull(6) ? null : c.getString(6);
            r.messageType = c.isNull(7) ? -1 : c.getInt(7);
            return r;
        }

        void prefetch(List<String> keys) {
            for (int i = 0; i < keys.size(); i += 400) {
                List<String> chunk = keys.subList(i, Math.min(keys.size(), i + 400));
                StringBuilder q = new StringBuilder(SELECT + "WHERE m.key_id IN (");
                for (int j = 0; j < chunk.size(); j++) q.append(j == 0 ? "?" : ",?");
                q.append(')');
                try (Cursor c = db.rawQuery(q.toString(), chunk.toArray(new String[0]))) {
                    while (c.moveToNext()) {
                        ProbeFieldMap.Row r = row(c);
                        String k = c.getString(0);
                        if (!byKey.containsKey(k)) byKey.put(k, new ArrayList<>());
                        byKey.get(k).add(r);
                    }
                }
            }
        }

        public List<ProbeFieldMap.Row> byKeyId(String keyId) {
            List<ProbeFieldMap.Row> r = byKey.get(keyId);
            return r == null ? Collections.emptyList() : r;
        }

        public ProbeFieldMap.Row byId(long id) {
            try (Cursor c = db.rawQuery(SELECT + "WHERE m._id = " + id, null)) {
                return c.moveToNext() ? row(c) : null;
            }
        }

        java.util.Set<String> allKeyIds() {
            java.util.Set<String> out = new java.util.HashSet<>();
            try (Cursor c = db.rawQuery("SELECT key_id FROM message WHERE key_id IS NOT NULL", null)) {
                while (c.moveToNext()) out.add(c.getString(0));
            }
            return out;
        }

        public boolean hasMessageId(long id) {
            return longOf(db, "SELECT COUNT(*) FROM message WHERE _id = " + id) > 0;
        }

        public boolean linked(String a, String b) {
            if (a == null || b == null) return false;
            try (Cursor c = db.rawQuery("SELECT COUNT(*) FROM jid_map jm JOIN jid l ON l._id = jm.lid_row_id JOIN jid p ON p._id = jm.jid_row_id "
                    + "WHERE (l.raw_string = ? AND p.raw_string = ?) OR (l.raw_string = ? AND p.raw_string = ?)", new String[]{a, b, b, a})) {
                return c.moveToFirst() && c.getLong(0) > 0;
            }
        }
    }

    /** The set's base by name: the live set's is msgstore.db.crypt15; a set rotated on D, msgstore-D.1.db.crypt15. */
    private static File base(File dir, String set) {
        return new File(dir, set == null ? BackupLocator.CURRENT : "msgstore-" + set + ".1.db.crypt15");
    }

    private static String gap(List<Long> ns) {
        for (int i = 0; i < ns.size(); i++) if (ns.get(i) != i + 1) return " (NOT 1..k — gap or offset)";
        return " (1.." + ns.size() + ", no gap)";
    }

    private static boolean eqSet(String a, String b) {
        return a == null ? b == null : a.equals(b);
    }

    private static long longOf(SQLiteDatabase db, String sql) {
        try (Cursor c = db.rawQuery(sql, null)) {
            return c.moveToFirst() && !c.isNull(0) ? c.getLong(0) : -1;
        }
    }
}
