package com.mike.metatron.whatsapp;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Date;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;

/**
 * "5. Try newest increment" — the increment test (Phase 0 close-out, item 3). Does the reader we
 * already have open a nightly increment (msgstore-increment-N.db.crypt15, or the rotated
 * msgstore-increment-N-YYYY-MM-DD.1.db.crypt15)? Runs the newest one
 * through the existing decrypt path, unchanged, and reports SHAPES only: decrypted yes/no (and
 * the BackupError if not), bytes in/out, the tables present, row counts for message/chat/jid,
 * the min/max message time, and how many of its message ids also appear in the newest full
 * backup. If the reader refuses the payload as not_a_message_database, ProbePayload says which
 * branch and what is inside (format magic, ZIP entry names and sizes; any SQLite entry gets the
 * same shape report). Since 11-23 (second round) every non-SQLite entry also gets ProbeShapes'
 * report — JSON by key path, anything else by a generic protobuf wire-format walk — compared, as
 * counts, with the newest full backup, which is decrypted once and first. No text, no names, no
 * identifiers. Every decrypted or extracted copy is deleted and every held entry zeroed before
 * returning.
 */
final class ProbeIncrement {
    private static final String[] COUNTED = {"message", "chat", "jid"};

    private ProbeIncrement() {}

    static String run(Context ctx) {
        StringBuilder b = new StringBuilder("== INCREMENT TEST ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File work = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        File incOut = new File(work, "increment.db");
        File fullOut = new File(work, "msgstore.db");
        BackupKey[] key = {null};
        SQLiteDatabase[] inc = {null};
        try {
            steps(ctx, b, incOut, fullOut, key, inc);
        } catch (BackupException e) {
            b.append("REFUSED: ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
        } finally {
            if (inc[0] != null) inc[0].close();
            if (key[0] != null) key[0].destroy();
            BackupDecryptor.deleteDecrypted(incOut);
            BackupDecryptor.deleteDecrypted(fullOut);
            int left = ProbePayload.sweep(work); // the payload, inflated output and extracted ZIP entries
            b.append("decrypted copies deleted: ").append(incOut.exists() || fullOut.exists() || left > 0 ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        // Built after the finally, so an early stop still reports the cleanup line.
        return b.toString();
    }

    /** The test proper. Returns early on any stop; {@link #run} reports and cleans up. */
    private static void steps(Context ctx, StringBuilder b, File incOut, File fullOut,
                              BackupKey[] key, SQLiteDatabase[] inc) throws Exception {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            b.append("All-files access: NOT GRANTED — step 2\n");
            return;
        }
        File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
        File[] files = dir.listFiles();
        int[] forms = ProbeLines.countIncrements(files);
        b.append("increment files in the folder: ").append(forms[0]).append(" undated (live set), ")
                .append(forms[1]).append(" dated (rotated)\n");
        File f = ProbeLines.newestIncrement(files);
        if (f == null) {
            b.append("no increment file found — try after 02:00\n");
            return;
        }
        b.append("chosen: ").append(f.getName()).append("  ").append(mb(f.length()))
                .append("  written ").append(ProbeReport.ts(f.lastModified())).append('\n');
        BackupLocator.requireComplete(f, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);

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

        BackupDecryptor.Result r;
        try {
            r = BackupDecryptor.decrypt(f, key[0], incOut, BackupDecryptor.FILESYSTEM);
        } catch (BackupException e) {
            b.append("decrypted: NO — ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
            if (e.error == BackupError.NOT_A_MESSAGE_DATABASE) inside(f, key[0], dir, fullOut, b, inc);
            return;
        }
        b.append("decrypted: YES in ").append(String.format(Locale.US, "%.1f s", r.millis / 1000.0))
                .append("  bytes in ").append(r.encryptedBytes).append(" -> out ").append(r.decryptedBytes).append('\n');
        b.append("  payload ").append(r.compressed ? "zlib" : "uncompressed").append(", MD5 trailer ")
                .append(r.md5Trailer ? "yes" : "no").append(", feature marker ").append(r.featureMarker ? "yes" : "no").append('\n');

        inc[0] = open(incOut);
        SQLiteDatabase[] full = {null};
        try {
            if (shape(inc[0], b)) overlap(inc[0], key[0], dir, fullOut, b, full);
        } finally {
            if (full[0] != null) full[0].close();
        }
    }

    /**
     * The reader refused the payload as not_a_message_database: say which branch, and what is
     * inside (ProbePayload). Each SQLite entry of a ZIP gets the same shape report and overlap as a
     * decrypted increment; the full backup is decrypted once for all of them. Copies are left for
     * {@link #run}'s sweep.
     */
    private static void inside(File f, BackupKey key, File dir, File fullOut, StringBuilder b, SQLiteDatabase[] inc) {
        b.append("\n-- what is inside (probe's own container pass; the reader is unchanged) --\n");
        ProbePayload.Inspection p;
        try {
            p = ProbePayload.inspect(f, key, fullOut.getParentFile());
        } catch (BackupException e) {
            b.append("inspection stopped — ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
            return;
        } catch (Throwable t) {
            b.append("inspection FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
            return;
        }
        ProbePayload.lines(p, b);
        SQLiteDatabase[] full = {null};
        try {
            // The full backup is opened once, first, so every entry's shape can be compared with it.
            ProbeShapes.Full against = ProbeShapes.NONE;
            b.append("\n-- the newest full backup, for comparison --\n");
            try {
                openFull(key, dir, fullOut, b, full);
                against = new SqliteFull(full[0]);
                b.append("full backup's newest message time: ").append(when(against.newestMessageTime())).append('\n');
            } catch (BackupException e) {
                b.append("not opened — ").append(e.error.code).append(" — comparisons omitted\n");
            } catch (Throwable t) {
                b.append("not opened — ").append(t.getClass().getSimpleName()).append(" — comparisons omitted\n");
            }
            b.append("\n-- entry shapes (paths, types, lengths, counts — never a value) --\n");
            int shaped = 0;
            for (ProbePayload.Entry e : p.entries) {
                if (e.bytes == null) continue;
                b.append('[').append(++shaped).append("] ");
                try {
                    ProbeShapes.entry(e.name, e.bytes, against, b);
                } catch (Throwable t) {
                    b.append("\n  shape FAILED: ").append(t.getClass().getSimpleName()).append('\n');
                }
            }
            if (shaped == 0) b.append("no non-SQLite entries held\n");
            int k = 0;
            for (ProbePayload.Entry e : p.sqliteEntries()) {
                b.append("\n-- ZIP entry ").append(++k).append(": ").append(e.name).append(" --\n");
                SQLiteDatabase db = null;
                try {
                    db = open(e.extracted);
                    if (shape(db, b)) overlap(db, key, dir, fullOut, b, full);
                } catch (Throwable t) {
                    b.append("entry shape FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
                } finally {
                    if (db != null) db.close();
                }
            }
        } finally {
            if (full[0] != null) full[0].close();
            ProbePayload.wipe(p);
        }
    }

    /** Decrypts and opens the newest full backup into held[0], once. */
    private static void openFull(BackupKey key, File dir, File fullOut, StringBuilder b, SQLiteDatabase[] held) throws Exception {
        if (held[0] != null) {
            b.append("full backup: as above\n");
            return;
        }
        File ff = BackupLocator.newest(dir);
        b.append("full backup: ").append(ff.getName()).append("  written ").append(ProbeReport.ts(ff.lastModified())).append('\n');
        BackupLocator.requireComplete(ff, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
        BackupDecryptor.decrypt(ff, key, fullOut, BackupDecryptor.FILESYSTEM);
        held[0] = open(fullOut);
    }

    /** ProbeShapes' view of the full backup: schema names, message key_ids, newest time, _id presence. */
    private static final class SqliteFull implements ProbeShapes.Full {
        private final SQLiteDatabase db;
        private final Set<String> tables;
        private Set<String> schema, keyIds, jids;
        private long newest = Long.MIN_VALUE;

        SqliteFull(SQLiteDatabase db) {
            this.db = db;
            this.tables = tables(db);
        }

        public Set<String> schemaNames() {
            if (schema == null) {
                schema = new java.util.HashSet<>(tables);
                for (String t : tables) schema.addAll(columns(db, "\"" + t.replace("\"", "\"\"") + "\""));
            }
            return schema;
        }

        public Set<String> messageKeyIds() {
            if (keyIds == null) {
                keyIds = new java.util.HashSet<>();
                if (tables.contains("message") && columns(db, "message").contains("key_id")) {
                    try (Cursor c = db.rawQuery("SELECT key_id FROM message WHERE key_id IS NOT NULL", null)) {
                        while (c.moveToNext()) keyIds.add(c.getString(0));
                    }
                }
            }
            return keyIds;
        }

        public Set<String> jidRawStrings() {
            if (jids == null) {
                jids = new java.util.HashSet<>();
                if (tables.contains("jid") && columns(db, "jid").contains("raw_string")) {
                    try (Cursor c = db.rawQuery("SELECT raw_string FROM jid WHERE raw_string IS NOT NULL", null)) {
                        while (c.moveToNext()) jids.add(c.getString(0));
                    }
                }
            }
            return jids;
        }

        public long newestMessageTime() {
            if (newest == Long.MIN_VALUE) {
                newest = tables.contains("message") ? longOf(db, "SELECT MAX(timestamp) FROM message WHERE timestamp > 0") : -1;
            }
            return newest;
        }

        public int idsPresent(String table, List<Long> ids) {
            if (!tables.contains(table)) return -1; // the name is only ever one sqlite_master listed
            String quoted = "\"" + table.replace("\"", "\"\"") + "\"";
            if (!columns(db, quoted).contains("_id")) return -2;
            int found = 0;
            for (int i = 0; i < ids.size(); i += 400) {
                List<Long> chunk = ids.subList(i, Math.min(ids.size(), i + 400));
                StringBuilder q = new StringBuilder("SELECT COUNT(*) FROM ").append(quoted).append(" WHERE _id IN (");
                String[] args = new String[chunk.size()];
                for (int j = 0; j < chunk.size(); j++) {
                    q.append(j == 0 ? "?" : ",?");
                    args[j] = String.valueOf(chunk.get(j));
                }
                q.append(')');
                try (Cursor c = db.rawQuery(q.toString(), args)) {
                    if (c.moveToFirst()) found += c.getInt(0);
                }
            }
            return found;
        }
    }

    /** Tables, row counts, message columns and time range. Returns whether a message table exists. */
    private static boolean shape(SQLiteDatabase db, StringBuilder b) {
        Set<String> tables = tables(db);
        b.append("tables present (").append(tables.size()).append("): ").append(tables).append('\n');
        for (String t : COUNTED) {
            b.append("rows in ").append(t).append(": ")
                    .append(tables.contains(t) ? String.valueOf(longOf(db, "SELECT COUNT(*) FROM " + t)) : "table absent").append('\n');
        }
        if (!tables.contains("message")) {
            b.append("no message table — overlap not computed\n");
            return false;
        }
        b.append("message columns (names): ").append(columns(db, "message")).append('\n');
        b.append("message time min/max: ")
                .append(when(longOf(db, "SELECT MIN(timestamp) FROM message WHERE timestamp > 0"))).append(" / ")
                .append(when(longOf(db, "SELECT MAX(timestamp) FROM message WHERE timestamp > 0"))).append('\n');
        return true;
    }

    /**
     * Message ids (message._id) in the increment that the newest full backup also holds — and,
     * of those, how many are the same row there (same chat and time), not a reused number.
     * Its own failure is reported here and does not discard what the increment already showed.
     */
    private static void overlap(SQLiteDatabase inc, BackupKey key, File dir, File fullOut, StringBuilder b,
                                SQLiteDatabase[] held) {
        b.append("\n-- against the newest full backup --\n");
        try {
            openFull(key, dir, fullOut, b, held);
            SQLiteDatabase full = held[0];
            long fullMax = longOf(full, "SELECT MAX(timestamp) FROM message WHERE timestamp > 0");
            b.append("full backup's newest message time: ").append(when(fullMax)).append('\n');

            int total = 0, idInFull = 0, sameRow = 0, newer = 0;
            try (Cursor c = inc.rawQuery("SELECT _id, chat_row_id, timestamp FROM message", null)) {
                while (c.moveToNext()) {
                    total++;
                    long ts = c.getLong(2);
                    if (fullMax > 0 && ts > fullMax) newer++;
                    try (Cursor d = full.rawQuery("SELECT chat_row_id, timestamp FROM message WHERE _id = ?",
                            new String[]{String.valueOf(c.getLong(0))})) {
                        if (!d.moveToFirst()) continue;
                        idInFull++;
                        if (d.getLong(0) == c.getLong(1) && d.getLong(1) == ts) sameRow++;
                    }
                }
            }
            b.append("increment message ids also in the full backup: ").append(idInFull).append(" of ").append(total)
                    .append("  (same chat and time there: ").append(sameRow).append(")\n");
            b.append("increment messages newer than the full backup's newest: ").append(newer).append(" of ").append(total).append('\n');
        } catch (BackupException e) {
            b.append("overlap not computed — ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("overlap FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
        }
        // held[0] stays open for the next ZIP entry; the caller closes it.
    }

    private static SQLiteDatabase open(File f) {
        return SQLiteDatabase.openDatabase(f.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
    }

    private static Set<String> tables(SQLiteDatabase db) {
        List<String> names = new ArrayList<>();
        try (Cursor c = db.rawQuery("SELECT name FROM sqlite_master WHERE type='table'", null)) {
            while (c.moveToNext()) names.add(c.getString(0));
        }
        Collections.sort(names);
        return new LinkedHashSet<>(names);
    }

    private static List<String> columns(SQLiteDatabase db, String table) {
        List<String> out = new ArrayList<>();
        try (Cursor c = db.rawQuery("PRAGMA table_info(" + table + ")", null)) {
            while (c.moveToNext()) out.add(c.getString(1));
        }
        return out;
    }

    private static long longOf(SQLiteDatabase db, String sql) {
        try (Cursor c = db.rawQuery(sql, null)) {
            return c.moveToFirst() && !c.isNull(0) ? c.getLong(0) : -1;
        }
    }

    private static String when(long ms) {
        return ms <= 0 ? "-" : new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.US).format(new Date(ms));
    }

    private static String mb(long bytes) {
        return String.format(Locale.US, "%.2f MB", bytes / 1e6);
    }
}
