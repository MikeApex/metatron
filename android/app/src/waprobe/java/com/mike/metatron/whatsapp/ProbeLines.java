package com.mike.metatron.whatsapp;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.TimeZone;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Plain-Java pieces of the probe — no Android and no org.json types — so they run under
 * {@code testWaprobeUnitTest} on the JVM (src/testWaprobe/). Two jobs: the one-line-per-event
 * report used by the survival test, and picking the newest nightly increment file (either form).
 *
 * An event line carries times and a MASKED chat id only: no names, no text, no lengths.
 */
final class ProbeLines {
    /** Unknown receipt time: events recorded before {@code rx} existed. */
    static final long UNKNOWN = -1;

    /**
     * The nightly increments, both forms seen on the phone: the live set is undated,
     * msgstore-increment-N.db.crypt15 (11-22); the dated msgstore-increment-N-YYYY-MM-DD.1.db.crypt15
     * appears once the next full backup rotates the set (10-30). Group 2, the date, is null when undated.
     */
    static final Pattern INCREMENT =
            Pattern.compile("msgstore-increment-(\\d+)(?:-(\\d{4}-\\d{2}-\\d{2})\\.1)?\\.db\\.crypt15");

    private ProbeLines() {}

    static String kind(boolean summary, boolean style, boolean group) {
        if (summary) return "summary";
        if (!style) return "other";
        return group ? "group" : "one-to-one";
    }

    /** "post HH:MM:SS · rx HH:MM:SS · delay +4s · one-to-one · aaa{5}@lid" */
    static String eventLine(long post, long rx, String kind, String maskedChat, TimeZone tz) {
        StringBuilder b = new StringBuilder("post ").append(clock(post, tz)).append(" · rx ");
        if (rx <= 0) b.append("?       · delay ?");
        else b.append(clock(rx, tz)).append(" · delay ").append(delay(rx - post));
        return b.append(" · ").append(kind).append(" · ").append(maskedChat).toString();
    }

    /** Day heading for the event list, so each line can stay HH:MM:SS. */
    static String day(long t, TimeZone tz) {
        return format("MM-dd EEE", t, tz);
    }

    static String clock(long t, TimeZone tz) {
        return format("HH:mm:ss", t, tz);
    }

    /** Signed, coarse enough to read at a glance: +4s, +2m 05s, +3h 07m. */
    static String delay(long ms) {
        String sign = ms < 0 ? "-" : "+";
        long s = Math.abs(ms) / 1000;
        if (s < 60) return sign + s + "s";
        if (s < 3600) return String.format(Locale.US, "%s%dm %02ds", sign, s / 60, s % 60);
        return String.format(Locale.US, "%s%dh %02dm", sign, s / 3600, (s % 3600) / 60);
    }

    static boolean isIncrement(String name) {
        return INCREMENT.matcher(name).matches();
    }

    /** The rotated form, msgstore-increment-N-YYYY-MM-DD.1.db.crypt15. */
    static boolean isDatedIncrement(String name) {
        Matcher m = INCREMENT.matcher(name);
        return m.matches() && m.group(2) != null;
    }

    /** {undated, dated} increment files in a listing — directories and other names ignored. */
    static int[] countIncrements(File[] files) {
        int[] n = new int[2];
        if (files == null) return n;
        for (File f : files) {
            if (!f.isFile() || !isIncrement(f.getName())) continue;
            n[isDatedIncrement(f.getName()) ? 1 : 0]++;
        }
        return n;
    }

    /**
     * The newest increment, either form: latest modification time; on a tie, the undated (live)
     * form before a dated (rotated) one, then the later date, then the higher N. Null when the folder holds none. Full backups are never returned —
     * {@link BackupLocator#newest} owns those and is unchanged.
     */
    static File newestIncrement(File[] files) {
        if (files == null) return null;
        File best = null;
        for (File f : files) {
            if (!f.isFile() || !isIncrement(f.getName())) continue;
            if (best == null || newer(f, best)) best = f;
        }
        return best;
    }

    private static boolean newer(File a, File b) {
        if (a.lastModified() != b.lastModified()) return a.lastModified() > b.lastModified();
        Matcher x = INCREMENT.matcher(a.getName()), y = INCREMENT.matcher(b.getName());
        x.matches();
        y.matches();
        String dx = x.group(2), dy = y.group(2);
        if ((dx == null) != (dy == null)) return dx == null; // the live set was written after the rotated one
        if (dx != null) {
            int byDate = dx.compareTo(dy);
            if (byDate != 0) return byDate > 0;
        }
        return Long.parseLong(x.group(1)) > Long.parseLong(y.group(1));
    }

    private static String format(String pattern, long t, TimeZone tz) {
        SimpleDateFormat f = new SimpleDateFormat(pattern, Locale.US);
        f.setTimeZone(tz);
        return f.format(new Date(t));
    }
}
