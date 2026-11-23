package com.mike.metatron.whatsapp;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.TreeMap;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * The live set: the current full backup plus its undated increments 1..k in N order (format
 * description § 12). Rotated (dated) sets are history and are not read — the live full backup
 * already contains them.
 *
 * A missing N stops the set at the gap with a named refusal that says how many were readable;
 * it never silently skips. A gap does not heal until the next full backup starts a new set.
 */
public final class IncrementSet {
    /** Live increments only: msgstore-increment-N.db.crypt15. The dated form is a rotated set. */
    static final Pattern LIVE = Pattern.compile("msgstore-increment-(\\d{1,6})\\.db\\.crypt15");

    public final File base;
    /** In N order, N = 1..k. */
    public final List<File> increments;

    private IncrementSet(File base, List<File> increments) {
        this.base = base;
        this.increments = Collections.unmodifiableList(increments);
    }

    /** N of an increment in this set, from its name. */
    public static long number(File increment) {
        Matcher m = LIVE.matcher(increment.getName());
        if (!m.matches()) throw new IllegalArgumentException("not a live increment name");
        return Long.parseLong(m.group(1));
    }

    public static IncrementSet locate(File dir) throws BackupException {
        String path = dir.getAbsolutePath();
        if (path.contains("com.whatsapp.w4b") || path.contains("WhatsApp Business")) {
            throw new BackupException(BackupError.BUSINESS_OUT_OF_SCOPE);
        }
        File base = new File(dir, BackupLocator.CURRENT);
        if (!base.isFile()) throw new BackupException(BackupError.NO_BACKUP_FOUND);
        File[] files = dir.listFiles();
        TreeMap<Long, File> byN = new TreeMap<>();
        if (files != null) {
            for (File f : files) {
                if (!f.isFile()) continue;
                Matcher m = LIVE.matcher(f.getName());
                if (m.matches()) byN.put(Long.parseLong(m.group(1)), f);
            }
        }
        List<File> out = new ArrayList<>();
        long expect = 1;
        for (long n : byN.keySet()) {
            if (n != expect) {
                throw new BackupException(BackupError.INCREMENT_GAP,
                        "increment " + expect + " missing; " + (expect - 1) + " readable before it, " + byN.size() + " present");
            }
            out.add(byN.get(n));
            expect++;
        }
        return new IncrementSet(base, out);
    }

    /**
     * Refuses the set while WhatsApp may be writing any of it: every file must be at least 10
     * minutes old, and no size may change across one 5-second look (format description § 1,
     * applied once to the whole set rather than 5 seconds per file).
     */
    public void requireComplete(BackupLocator.Clock clock, BackupLocator.Sleeper sleeper)
            throws BackupException, InterruptedException {
        List<File> all = new ArrayList<>();
        all.add(base);
        all.addAll(increments);
        long[] sizes = new long[all.size()];
        for (int i = 0; i < all.size(); i++) {
            File f = all.get(i);
            if (clock.nowMillis() - f.lastModified() < BackupLocator.RECENT_WRITE_MS) {
                throw new BackupException(BackupError.BEING_WRITTEN);
            }
            sizes[i] = f.length();
        }
        sleeper.sleep(BackupLocator.SIZE_RECHECK_MS);
        for (int i = 0; i < all.size(); i++) {
            if (all.get(i).length() != sizes[i]) throw new BackupException(BackupError.BEING_WRITTEN);
        }
    }
}
