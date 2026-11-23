package com.mike.metatron.whatsapp;

import android.content.Context;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;
import java.io.Writer;
import java.nio.charset.StandardCharsets;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/**
 * "8. Export a labelling sample" — the Android half (WhatsApp M2). Reads the live set with the
 * phone's own reader (the current full backup plus its live increments, combined by
 * {@link BackupCombiner}), hands the messages to {@link ProbeM2Sample}, and writes
 * {@code m2_sample.jsonl} to the app's private cache, where the share sheet's FileProvider
 * (src/main's {@code cache-path}) can offer it to Taildrop.
 *
 * The decrypted backup is deleted before this returns, as every probe button does. The sample
 * itself holds other people's words in plain text: it is replaced by the next run, deleted at the
 * next probe launch once it is {@link #STALE_MS} old, and deleted by "Delete all probe data".
 * Nothing here reports a value from a message — counts only.
 */
final class ProbeM2Run {
    static final String DIR = "wa_m2", FILE = "m2_sample.jsonl";
    /** Long enough for Taildrop to finish reading after the share sheet returns. */
    static final long STALE_MS = 15L * 60 * 1000;

    private ProbeM2Run() {}

    static final class Outcome {
        final String report;
        /** The written sample, or null when nothing was written. */
        final File sample;

        Outcome(String report, File sample) {
            this.report = report;
            this.sample = sample;
        }
    }

    static File sampleFile(Context ctx) {
        return new File(new File(ctx.getCacheDir(), DIR), FILE);
    }

    /** True when no sample is left on the phone. */
    static boolean deleteSample(Context ctx) {
        File f = sampleFile(ctx);
        return (!f.exists() || f.delete()) && !f.exists();
    }

    /** The launch sweep: a sample older than {@link #STALE_MS} does not survive a probe start. */
    static void sweepStale(Context ctx) {
        File f = sampleFile(ctx);
        if (f.exists() && System.currentTimeMillis() - f.lastModified() > STALE_MS) deleteSample(ctx);
    }

    static Outcome run(Context ctx) {
        StringBuilder b = new StringBuilder("== LABELLING SAMPLE (M2) ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File work = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        work.mkdirs();
        File fullOut = new File(work, ProbePayload.PREFIX + "m2.db");
        BackupKey[] key = {null};
        String[] stage = {"start"};
        File written = null;
        deleteSample(ctx); // an earlier sample never lingers behind a new one
        try {
            written = steps(ctx, b, fullOut, key, stage);
        } catch (BackupException e) {
            b.append("REFUSED: ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
        } catch (Throwable t) {
            b.append("FAILED at ").append(stage[0]).append(": ").append(t.getClass().getSimpleName()).append(": ")
                    .append(ProbePayload.maskDigits(String.valueOf(t.getMessage()))).append('\n');
        } finally {
            if (key[0] != null) key[0].destroy();
            BackupDecryptor.deleteDecrypted(fullOut);
            int left = ProbePayload.sweep(work);
            if (written == null) deleteSample(ctx); // a half-written sample never survives a failure
            b.append("decrypted copies deleted: ").append(fullOut.exists() || left > 0 ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        return new Outcome(b.toString(), written);
    }

    /** Returns the written sample, or null when nothing was written. */
    private static File steps(Context ctx, StringBuilder b, File fullOut, BackupKey[] key, String[] stage) throws Exception {
        if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
            b.append("All-files access: NOT GRANTED — step 2\n");
            return null;
        }
        File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
        byte[] root = ProbeKeyVault.load(ctx);
        if (root == null) {
            b.append("no key stored — step 3\n");
            return null;
        }
        try {
            key[0] = BackupKey.fromRoot(root);
        } finally {
            Arrays.fill(root, (byte) 0);
        }

        stage[0] = "locate the live set";
        IncrementSet set = IncrementSet.locate(dir);
        stage[0] = "write check";
        set.requireComplete(BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);
        long now = System.currentTimeMillis();
        long since = now - ProbeM2Sample.WINDOW_MS;

        stage[0] = "full backup: decrypt";
        BackupDecryptor.decrypt(set.base, key[0], fullOut, BackupDecryptor.FILESYSTEM);
        FullBackupMessages base;
        stage[0] = "full backup: read";
        try {
            base = FullBackupMessages.read(fullOut, since);
        } finally {
            BackupDecryptor.deleteDecrypted(fullOut);
        }
        List<Increment> incs = new ArrayList<>();
        for (File f : set.increments) {
            stage[0] = "increment " + IncrementSet.number(f);
            incs.add(IncrementReader.read(f, IncrementSet.number(f), key[0]));
        }
        // Every chat, raw and canonical: the sample is drawn from all of them.
        Set<String> chats = new HashSet<>();
        for (WaMessage m : base.messages) chats.add(m.chatJid);
        for (WaMessage m : BackupCombiner.canonicalise(base.messages, base.tables)) chats.add(m.chatJid);
        for (Increment inc : incs) {
            for (WaMessage m : inc.messages) chats.add(m.chatJid);
            for (WaMessage m : BackupCombiner.canonicalise(inc.messages, base.tables)) chats.add(m.chatJid);
        }
        stage[0] = "combine";
        BackupCombiner.Combined c = BackupCombiner.combine(base.messages, base.tables, incs, chats, since);
        b.append("read: the current full backup and ").append(incs.size()).append(" live increments → ")
                .append(c.messages.size()).append(" messages in the window\n");

        stage[0] = "sample";
        ProbeM2Sample.Result r = ProbeM2Sample.sample(c.messages, now, new SecureRandom());
        b.append(r.report);
        if (r.rows.isEmpty()) {
            b.append("sample file: NOT written — nothing to sample\n");
            return null;
        }
        stage[0] = "write the sample";
        File out = sampleFile(ctx);
        out.getParentFile().mkdirs();
        try (Writer w = new OutputStreamWriter(new FileOutputStream(out), StandardCharsets.UTF_8)) {
            w.write(ProbeM2Sample.jsonl(r.rows));
        }
        b.append("sample file: written, ").append(r.rows.size()).append(" rows — send it to the Mac with Tailscale. ")
                .append("It is deleted at the next probe launch after 15 minutes, or by \"Delete all probe data\".\n");
        return out;
    }
}
