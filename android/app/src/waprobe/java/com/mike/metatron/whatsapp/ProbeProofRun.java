package com.mike.metatron.whatsapp;

import android.content.Context;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeMap;
import java.util.regex.Matcher;

/**
 * "7. Read the set (P3 proof)" — P3 step 4. Runs the NEW reader (src/main: IncrementReader,
 * FullBackupMessages, BackupCombiner) on the real sets: the live one if it exists, and each rotated
 * one. Reports counts only: messages decoded per increment and how many match the newest full
 * backup, fields agreeing, edits seen, deletions listed (counted, not applied — Mike, 11-23), and the
 * combined count since a test since-time, set against the newest full backup over the same window.
 * Every decrypted copy is deleted before returning.
 */
final class ProbeProofRun {
    /** The test since-time: this long before the set's base was written. */
    static final long SINCE_BEFORE_BASE_MS = 3L * 24 * 3600 * 1000;

    private ProbeProofRun() {}

    static String run(Context ctx) {
        StringBuilder b = new StringBuilder("== SET PROOF (P3 step 4 — the new reader) ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File work = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        work.mkdirs();
        File fullOut = new File(work, ProbePayload.PREFIX + "full.db");
        BackupKey[] key = {null};
        String[] stage = {"start"};
        try {
            steps(ctx, b, fullOut, key, stage);
        } catch (BackupException e) {
            b.append("REFUSED: ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("FAILED at ").append(stage[0]).append(": ").append(t.getClass().getSimpleName()).append(": ")
                    .append(ProbePayload.maskDigits(String.valueOf(t.getMessage()))).append('\n');
        } finally {
            if (key[0] != null) key[0].destroy();
            BackupDecryptor.deleteDecrypted(fullOut);
            int left = ProbePayload.sweep(work);
            b.append("decrypted copies deleted: ").append(fullOut.exists() || left > 0 ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        return b.toString();
    }

    /**
     * Phase 1 step 0: every row's message_type (message._id → type) into {@code out}, and a
     * per-type summary of the whole backup — rows and rows with text_data. Small integers only;
     * read-only, closed before returning. The caller deletes the decrypted file.
     */
    static String readTypes(File database, java.util.Map<Long, Integer> out) {
        android.database.sqlite.SQLiteDatabase db = android.database.sqlite.SQLiteDatabase.openDatabase(database.getPath(), null,
                android.database.sqlite.SQLiteDatabase.OPEN_READONLY | android.database.sqlite.SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            try (android.database.Cursor c = db.rawQuery("SELECT _id, message_type FROM message", null)) {
                while (c.moveToNext()) out.put(c.getLong(0), c.isNull(1) ? -1 : c.getInt(1));
            }
            StringBuilder sum = new StringBuilder("{");
            try (android.database.Cursor c = db.rawQuery("SELECT IFNULL(message_type, -1), COUNT(*), SUM(text_data IS NOT NULL) "
                    + "FROM message GROUP BY 1 ORDER BY 1", null)) {
                while (c.moveToNext()) {
                    if (sum.length() > 1) sum.append(", ");
                    sum.append(c.getInt(0)).append('=').append(c.getLong(1)).append('/').append(c.getLong(2));
                }
            }
            return sum.append('}').toString();
        } finally {
            db.close();
        }
    }

    private static String absentFiles(Increment inc) {
        int n = 0;
        for (Increment.TableDelta t : inc.tables.values()) n += t.absentDeletedFiles;
        return n == 0 ? "" : ", listed deletion files absent " + n;
    }

    private static final class Set1 {
        String label;
        File base;
        final List<File> files = new ArrayList<>();
        final List<Long> ns = new ArrayList<>();
        boolean live;
    }

    private static void steps(Context ctx, StringBuilder b, File fullOut, BackupKey[] key, String[] stage) throws Exception {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            b.append("All-files access: NOT GRANTED — step 2\n");
            return;
        }
        File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
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

        List<Set1> sets = new ArrayList<>();
        try {
            IncrementSet live = IncrementSet.locate(dir);
            if (!live.increments.isEmpty()) {
                live.requireComplete(BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
                Set1 s = new Set1();
                s.label = "live";
                s.live = true;
                s.base = live.base;
                for (File f : live.increments) { s.files.add(f); s.ns.add(IncrementSet.number(f)); }
                sets.add(s);
            } else {
                b.append("live set: no undated increment yet (one appears after each 02:00 run)\n");
            }
        } catch (BackupException e) {
            b.append("live set: REFUSED ").append(e.error.code).append(" — ").append(e.getMessage()).append('\n');
        }
        TreeMap<String, TreeMap<Long, File>> rotated = new TreeMap<>();
        File[] files = dir.listFiles();
        if (files != null) {
            for (File f : files) {
                Matcher m = ProbeLines.INCREMENT.matcher(f.getName());
                if (!f.isFile() || !m.matches() || m.group(2) == null) continue;
                if (!rotated.containsKey(m.group(2))) rotated.put(m.group(2), new TreeMap<>());
                rotated.get(m.group(2)).put(Long.parseLong(m.group(1)), f);
            }
        }
        for (String d : rotated.keySet()) {
            Set1 s = new Set1();
            s.label = "rotated " + d;
            s.base = new File(dir, "msgstore-" + d + ".1.db.crypt15");
            for (java.util.Map.Entry<Long, File> e : rotated.get(d).entrySet()) { s.ns.add(e.getKey()); s.files.add(e.getValue()); }
            sets.add(s);
        }
        if (sets.isEmpty()) {
            b.append("no sets to read\n");
            return;
        }

        // The newest full backup, read once with the new reader, as the comparison.
        File newestFile = new File(dir, BackupLocator.CURRENT);
        stage[0] = "newest full backup: write check";
        BackupLocator.requireComplete(newestFile, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
        stage[0] = "newest full backup: decrypt";
        BackupDecryptor.decrypt(newestFile, key[0], fullOut, BackupDecryptor.FILESYSTEM);
        FullBackupMessages newest;
        java.util.Map<Long, Integer> types = new java.util.HashMap<>();
        String typeSummary;
        stage[0] = "newest full backup: read messages";
        try {
            newest = FullBackupMessages.read(fullOut, 0);
            stage[0] = "newest full backup: read message_type";
            typeSummary = readTypes(fullOut, types);
        } finally {
            BackupDecryptor.deleteDecrypted(fullOut);
        }
        List<WaMessage> newestCanon = BackupCombiner.canonicalise(newest.messages, newest.tables);
        java.util.Map<String, WaMessage> newestByKey = ProbeProof.index(newestCanon);
        b.append("newest full backup: ").append(newest.messages.size()).append(" messages with a key_id (")
                .append(newest.withoutKeyId).append(" without; ").append(newest.withoutChat).append(" belonging to no chat, not returned)\n");
        b.append("newest full backup by message_type {type=rows/with text}: ").append(typeSummary).append('\n');
        Set<String> allChats = new HashSet<>();
        for (WaMessage m : newest.messages) allChats.add(m.chatJid);
        for (WaMessage m : newestCanon) allChats.add(m.chatJid);

        boolean allDecoded = true;
        for (Set1 s : sets) {
            stage[0] = "set " + s.label;
            b.append("\n-- set ").append(s.label).append(": N ").append(s.ns).append(" --\n");
            for (int i = 0; i < s.ns.size(); i++) {
                if (s.ns.get(i) != i + 1) {
                    b.append("  NOT 1..k — the reader would refuse this set as increment_gap\n");
                    allDecoded = false;
                    break;
                }
            }
            List<Increment> incs = new ArrayList<>();
            for (int i = 0; i < s.files.size(); i++) {
                File f = s.files.get(i);
                if (!s.live && System.currentTimeMillis() - f.lastModified() < BackupLocator.RECENT_WRITE_MS) {
                    b.append("  increment ").append(s.ns.get(i)).append(": being written — skipped\n");
                    allDecoded = false;
                    continue;
                }
                stage[0] = "set " + s.label + ", increment " + s.ns.get(i);
                try {
                    Increment inc = IncrementReader.read(f, s.ns.get(i), key[0]);
                    incs.add(inc);
                    List<WaMessage> canon = BackupCombiner.canonicalise(inc.messages, newest.tables);
                    for (WaMessage m : inc.messages) allChats.add(m.chatJid);
                    for (WaMessage m : canon) allChats.add(m.chatJid);
                    b.append("  increment ").append(inc.number).append(": decoded ").append(inc.messages.size())
                            .append(" (header updated ").append(inc.messagesUpdated).append("), deletions listed ")
                            .append(inc.deletedMessageIds.size()).append(", tables ").append(inc.tables.keySet())
                            .append(", undecodable text ").append(inc.textUndecodable).append(absentFiles(inc)).append('\n');
                    b.append("    vs newest: ").append(ProbeProof.agreement(canon, newestByKey)).append('\n');
                } catch (BackupException e) {
                    allDecoded = false;
                    b.append("  increment ").append(s.ns.get(i)).append(": REFUSED ").append(e.error.code)
                            .append(" — ").append(e.getMessage()).append('\n');
                } catch (java.io.IOException e) {
                    allDecoded = false;
                    b.append("  increment ").append(s.ns.get(i)).append(": FAILED IOException: ")
                            .append(ProbePayload.maskDigits(String.valueOf(e.getMessage()))).append('\n');
                }
            }
            if (incs.size() != s.files.size() || !s.base.isFile()) {
                b.append("  combine skipped: ").append(!s.base.isFile() ? "base not found" : "an increment did not decode").append('\n');
                continue;
            }
            // The reader takes whole seconds; the window below is compared in ms, so it starts on
            // the same whole second.
            long sinceSeconds = (s.base.lastModified() - SINCE_BEFORE_BASE_MS) / 1000;
            long since = sinceSeconds * 1000L;
            try {
                stage[0] = "set " + s.label + ": base decrypt";
                BackupDecryptor.decrypt(s.base, key[0], fullOut, BackupDecryptor.FILESYSTEM);
                stage[0] = "set " + s.label + ": base read and combine";
                FullBackupMessages base;
                try {
                    base = FullBackupMessages.read(fullOut, sinceSeconds);
                } finally {
                    BackupDecryptor.deleteDecrypted(fullOut);
                }
                for (WaMessage m : base.messages) allChats.add(m.chatJid);
                for (WaMessage m : BackupCombiner.canonicalise(base.messages, base.tables)) allChats.add(m.chatJid);
                BackupCombiner.Combined c = BackupCombiner.combine(base.messages, base.tables, incs, allChats, sinceSeconds);
                long end = incs.get(incs.size() - 1).creationDateMs;
                b.append("  combined since ").append(ProbeReport.ts(since)).append(" (base ").append(base.messages.size())
                        .append(" since then): ").append(c.messages.size()).append(" messages — added ").append(c.added)
                        .append(", replaced ").append(c.replaced).append(", edits seen (text changed) ").append(c.textChanged)
                        .append(", deletions listed (not applied) ").append(c.deletionsListed).append('\n');
                List<WaMessage> combinedWindow = new ArrayList<>(), newestWindow = new ArrayList<>();
                for (WaMessage m : c.messages) if (m.timeMs < end) combinedWindow.add(m);
                for (WaMessage m : newestCanon) if (m.timeMs >= since && m.timeMs < end) newestWindow.add(m);
                b.append("  window to the last increment (").append(ProbeReport.ts(end)).append("): ")
                        .append(ProbeProof.versus(combinedWindow, newestWindow, s.base.lastModified(), types)).append('\n');
            } catch (BackupException e) {
                b.append("  combine REFUSED ").append(e.error.code).append(" — ").append(e.getMessage()).append('\n');
                allDecoded = false;
            }
        }
        b.append("\nevery increment decoded: ").append(allDecoded ? "yes" : "NO").append('\n');
    }
}
