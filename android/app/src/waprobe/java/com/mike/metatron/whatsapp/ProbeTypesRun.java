package com.mike.metatron.whatsapp;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.regex.Matcher;

/**
 * "9. Message types (Phase 2)" — Phase 2 step 0, review finding 6. Decodes every nightly
 * increment (in memory; ProbePayload), then decrypts the newest full backup once and counts:
 * its rows by message_type × chat kind × from-me, with text; and, for each increment message
 * matched by row id and key_id, its type from the backup against its content field numbers and
 * its numeric fields (ProbeTypes). Counts, type numbers and field paths only; every decrypted
 * copy is deleted and every decoded message wiped before returning.
 */
final class ProbeTypesRun {
    private ProbeTypesRun() {}

    static String run(Context ctx) {
        StringBuilder b = new StringBuilder("== MESSAGE TYPES (Phase 2 step 0, finding 6) ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File work = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        work.mkdirs();
        File fullOut = new File(work, ProbePayload.PREFIX + "full.db");
        BackupKey[] key = {null};
        List<ProbeFieldMap.Decoded> decoded = new ArrayList<>();
        String[] stage = {"start"};
        try {
            steps(ctx, b, work, fullOut, key, decoded, stage);
        } catch (BackupException e) {
            b.append("REFUSED at ").append(stage[0]).append(": ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("FAILED at ").append(stage[0]).append(": ").append(t.getClass().getSimpleName()).append('\n');
        } finally {
            for (ProbeFieldMap.Decoded d : decoded) d.wipe();
            if (key[0] != null) key[0].destroy();
            BackupDecryptor.deleteDecrypted(fullOut);
            int left = ProbePayload.sweep(work);
            b.append("decrypted copies deleted: ").append(fullOut.exists() || left > 0 ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        return b.toString();
    }

    private static void steps(Context ctx, StringBuilder b, File work, File fullOut, BackupKey[] key,
                              List<ProbeFieldMap.Decoded> decoded, String[] stage) throws Exception {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            b.append("All-files access: NOT GRANTED — step 2\n");
            return;
        }
        File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
        File[] files = dir.listFiles();
        if (files == null) throw new BackupException(BackupError.NO_BACKUP_FOUND);
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

        // 1. Every increment, live and rotated, decoded in memory.
        List<File> incs = new ArrayList<>();
        for (File f : files) {
            Matcher m = ProbeLines.INCREMENT.matcher(f.getName());
            if (f.isFile() && m.matches()) incs.add(f);
        }
        Collections.sort(incs, (x, y) -> Long.compare(x.lastModified(), y.lastModified()));
        if (incs.size() > ProbeFieldMapRun.MAX_INCREMENTS) incs = incs.subList(incs.size() - ProbeFieldMapRun.MAX_INCREMENTS, incs.size());
        int skipped = 0, failed = 0;
        Set<Long> wanted = new HashSet<>();
        for (File f : incs) {
            if (System.currentTimeMillis() - f.lastModified() < BackupLocator.RECENT_WRITE_MS) { skipped++; continue; }
            stage[0] = "an increment";
            ProbePayload.Inspection p = null;
            try {
                p = ProbePayload.inspect(f, key[0], work);
                byte[] bin = null;
                if (p.tagOk && p.zipIn != null) {
                    for (ProbePayload.Entry e : p.entries) if (e.bytes != null && e.name.equals("messages.bin")) bin = e.bytes;
                }
                if (bin == null) { failed++; continue; }
                ProbeFieldMap.Decoded d = ProbeFieldMap.decode(bin);
                decoded.add(d);
                for (ProbeFieldMap.Msg m : d.msgs) {
                    Long id = m.num(ProbeFieldMap.ROW_ID);
                    if (id != null) wanted.add(id);
                }
            } catch (BackupException e) {
                failed++;
                b.append("increment REFUSED: ").append(e.error.code).append('\n');
            } catch (java.io.IOException e) {
                failed++;
                b.append("increment FAILED: IOException\n");
            } finally {
                ProbePayload.wipe(p);
                ProbePayload.sweep(work);
            }
        }
        b.append("increments: ").append(incs.size()).append(" found, ").append(decoded.size()).append(" decoded, ")
                .append(skipped).append(" being written (skipped), ").append(failed).append(" not decoded\n");

        // 2. The newest full backup, once.
        File newest = BackupLocator.newest(dir);
        stage[0] = "newest full backup: write check";
        if (newest.getName().equals(BackupLocator.CURRENT)) {
            BackupLocator.requireComplete(newest, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
        } else if (System.currentTimeMillis() - newest.lastModified() < BackupLocator.RECENT_WRITE_MS) {
            throw new BackupException(BackupError.BEING_WRITTEN);
        }
        stage[0] = "newest full backup: decrypt";
        BackupDecryptor.decrypt(newest, key[0], fullOut, BackupDecryptor.FILESYSTEM);
        List<ProbeTypes.Group> groups = new ArrayList<>();
        Map<Long, ProbeTypes.Row> rows = new HashMap<>();
        SQLiteDatabase db = null;
        try {
            stage[0] = "newest full backup: count";
            db = SQLiteDatabase.openDatabase(fullOut.getPath(), null, SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
            try (Cursor c = db.rawQuery("SELECT IFNULL(m.message_type, -1), cj.server, IFNULL(m.from_me, 0), COUNT(*), "
                    + "SUM(m.text_data IS NOT NULL) FROM message m LEFT JOIN chat c ON c._id = m.chat_row_id "
                    + "LEFT JOIN jid cj ON cj._id = c.jid_row_id GROUP BY 1, 2, 3", null)) {
                while (c.moveToNext()) {
                    groups.add(new ProbeTypes.Group(c.getInt(0), c.isNull(1) ? null : c.getString(1), c.getInt(2) == 1,
                            c.getLong(3), c.getLong(4)));
                }
            }
            stage[0] = "newest full backup: rows the increments name";
            try (Cursor c = db.rawQuery("SELECT _id, IFNULL(message_type, -1), key_id FROM message", null)) {
                while (c.moveToNext()) {
                    long id = c.getLong(0);
                    if (wanted.contains(id)) rows.put(id, new ProbeTypes.Row(c.getInt(1), c.isNull(2) ? null : c.getString(2)));
                }
            }
        } finally {
            if (db != null) db.close();
            BackupDecryptor.deleteDecrypted(fullOut);
        }
        b.append("\n-- newest full backup (").append(newest.getName()).append(", written ").append(ProbeReport.ts(newest.lastModified()))
                .append(") by message_type; from-me chat kinds as rows/with text --\n");
        b.append(ProbeTypes.fullSummary(groups));

        // 3. The increments against it.
        stage[0] = "tally";
        ProbeTypes.Tally t = new ProbeTypes.Tally();
        for (ProbeFieldMap.Decoded d : decoded) for (ProbeFieldMap.Msg m : d.msgs) t.add(m, rows);
        rows.clear();
        b.append("\n-- the increments' messages, typed by the newest backup --\n");
        b.append(t.report());
    }
}
