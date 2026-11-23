package com.mike.metatron.whatsapp;

import java.io.File;
import java.util.regex.Pattern;

/**
 * Finds the backup to read and refuses one WhatsApp is still writing (format description § 1).
 */
public final class BackupLocator {
    /** WhatsApp's database folder on Android, relative to shared storage. */
    public static final String RELATIVE_DIR = "Android/media/com.whatsapp/WhatsApp/Databases";

    static final String CURRENT = "msgstore.db.crypt15";
    /** Dated copies, exactly as § 1 names them: msgstore-YYYY-MM-DD.1.db.crypt15. */
    static final Pattern DATED = Pattern.compile("msgstore-\\d{4}-\\d{2}-\\d{2}\\.1\\.db\\.crypt15");
    static final Pattern CRYPT14 = Pattern.compile("msgstore(-\\d{4}-\\d{2}-\\d{2}\\.1)?\\.db\\.crypt14");

    static final long RECENT_WRITE_MS = 10 * 60 * 1000L;
    static final long SIZE_RECHECK_MS = 5 * 1000L;

    public interface Clock {
        long nowMillis();
    }

    public interface Sleeper {
        void sleep(long millis) throws InterruptedException;
    }

    public static final Clock SYSTEM_CLOCK = System::currentTimeMillis;
    public static final Sleeper THREAD_SLEEP = Thread::sleep;

    private BackupLocator() {}

    /**
     * The newest backup in {@code dir} by modification time; on a tie the undated current
     * file wins. A WhatsApp Business folder is refused outright rather than read as if it
     * were the same format (§ 1: out of scope).
     *
     * A crypt14 file written after the newest crypt15 means end-to-end backup was switched
     * off since: WhatsApp now writes crypt14, and the crypt15 left behind only grows stale.
     * Reading it would look like a quiet week, so it is refused as crypt14_end_to_end_off
     * (review finding 3). A crypt14 no newer than the crypt15 is history and does not block.
     */
    public static File newest(File dir) throws BackupException {
        String path = dir.getAbsolutePath();
        if (path.contains("com.whatsapp.w4b") || path.contains("WhatsApp Business")) {
            throw new BackupException(BackupError.BUSINESS_OUT_OF_SCOPE);
        }
        File[] files = dir.listFiles();
        if (files == null) throw new BackupException(BackupError.NO_BACKUP_FOUND);
        File best = null;
        boolean sawCrypt14 = false;
        long newestCrypt14 = Long.MIN_VALUE;
        for (File f : files) {
            if (!f.isFile()) continue;
            String name = f.getName();
            if (CRYPT14.matcher(name).matches()) {
                sawCrypt14 = true;
                newestCrypt14 = Math.max(newestCrypt14, f.lastModified());
            }
            boolean current = name.equals(CURRENT);
            if (!current && !DATED.matcher(name).matches()) continue;
            if (best == null
                    || f.lastModified() > best.lastModified()
                    || (f.lastModified() == best.lastModified() && current)) {
                best = f;
            }
        }
        if (best != null && !(sawCrypt14 && newestCrypt14 > best.lastModified())) return best;
        if (sawCrypt14) throw new BackupException(BackupError.CRYPT14_END_TO_END_OFF);
        throw new BackupException(BackupError.NO_BACKUP_FOUND);
    }

    /**
     * Refuses a file modified in the last 10 minutes, or whose size changes across a
     * 5-second look. A modification time in the future also counts as recent: deferring is
     * recoverable, half-reading a file is not, and the freshness check reports a backup that
     * stays deferred.
     */
    public static void requireComplete(File f, Clock clock, Sleeper sleeper)
            throws BackupException, InterruptedException {
        if (clock.nowMillis() - f.lastModified() < RECENT_WRITE_MS) {
            throw new BackupException(BackupError.BEING_WRITTEN);
        }
        long size = f.length();
        sleeper.sleep(SIZE_RECHECK_MS);
        if (f.length() != size) throw new BackupException(BackupError.BEING_WRITTEN);
    }
}
