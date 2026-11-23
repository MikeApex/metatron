package com.mike.metatron.whatsapp;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * The nightly job's own small state (plan § 3.2), in {@code wa_state/job.json} — times and a
 * count, nothing else: the last successful run and the last attempt (the 26-h app-open rule), the
 * retries used tonight, the last "Dry run now" tap (the 7-night window), and the last backup
 * write times seen (so "WhatsApp has stopped backing up" still ages while the backup cannot be
 * found), and when an app open last re-asked a closed gate. Deleted with the rest of {@code wa_state/} by "Turn off".
 *
 * <p>Read and written under one class lock, through {@link #update}, so the user's tap and a
 * finishing run cannot overwrite each other. An unreadable file reads as empty.
 */
final class NightlyState {
    static final String FILE = "job.json";

    long lastSuccessMs, lastAttemptMs, dryTapMs, backupWritten, fullBackupWritten;
    /** The last time an app open asked the VM where a closed gate stands (F6). */
    long gateCheckMs;
    /**
     * The newest cursor the VM has ever answered on this install (0 = never one). A null cursor after
     * a non-zero one means the VM forgot this user (delete-all, a fresh VM); a null cursor before any
     * is merely the first night — live posts never carry a cursor (verify NEW-1).
     */
    long cursorSeen;
    int retries;

    interface Change {
        void apply(NightlyState s);
    }

    static synchronized NightlyState load(File dir) {
        NightlyState s = new NightlyState();
        byte[] raw = read(new File(dir, FILE));
        if (raw == null) return s;
        try {
            Object v = Json.parse(new String(raw, StandardCharsets.UTF_8));
            if (!(v instanceof Map)) return s;
            Map<?, ?> m = (Map<?, ?>) v;
            s.lastSuccessMs = num(m, "last_success_ms");
            s.lastAttemptMs = num(m, "last_attempt_ms");
            s.dryTapMs = num(m, "dry_tap_ms");
            s.backupWritten = num(m, "backup_written");
            s.fullBackupWritten = num(m, "full_backup_written");
            s.gateCheckMs = num(m, "gate_check_ms");
            s.cursorSeen = num(m, "cursor_seen");
            s.retries = (int) Math.min(num(m, "retries"), Integer.MAX_VALUE);
        } catch (Json.Malformed e) {
            return new NightlyState();
        }
        return s;
    }

    /** Load, change, save — atomically with respect to every other caller. Returns the saved state. */
    static synchronized NightlyState update(File dir, Change c) {
        NightlyState s = load(dir);
        c.apply(s);
        s.save(dir);
        return s;
    }

    private void save(File dir) {
        String json = JsonOut.obj()
                .put("last_success_ms", lastSuccessMs)
                .put("last_attempt_ms", lastAttemptMs)
                .put("dry_tap_ms", dryTapMs)
                .put("backup_written", backupWritten)
                .put("full_backup_written", fullBackupWritten)
                .put("gate_check_ms", gateCheckMs)
                .put("cursor_seen", cursorSeen)
                .put("retries", retries)
                .toString();
        writeAtomically(new File(dir, FILE), json.getBytes(StandardCharsets.UTF_8));
    }

    private static long num(Map<?, ?> m, String k) {
        Object v = m.get(k);
        return v instanceof Long && (Long) v > 0 ? (Long) v : 0;
    }

    /** Temp file, synced, renamed over the target. A failure leaves the old file and is not fatal. */
    static boolean writeAtomically(File target, byte[] data) {
        File dir = target.getParentFile();
        if (dir != null && !dir.isDirectory() && !dir.mkdirs()) return false;
        File t = new File(dir, target.getName() + ".tmp");
        try {
            try (FileOutputStream out = new FileOutputStream(t)) {
                out.write(data);
                out.getFD().sync();
            }
            if (t.renameTo(target)) return true;
        } catch (IOException ignored) {
            // falls through
        }
        t.delete();
        return false;
    }

    static byte[] read(File f) {
        if (!f.isFile()) return null;
        try (InputStream in = new FileInputStream(f)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[4096];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        } catch (IOException e) {
            return null;
        }
    }

    @Override
    public String toString() {
        return "NightlyState(retries " + retries + ")";
    }
}
