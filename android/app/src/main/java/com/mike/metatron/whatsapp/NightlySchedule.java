package com.mike.metatron.whatsapp;

import java.util.Arrays;
import java.util.Calendar;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.TimeZone;

/**
 * When the nightly read runs, and whether it may (plan §§ 3.2, 3.12). Plain Java, unit-tested;
 * {@link NightlyJob} turns these into JobScheduler calls.
 *
 * <ul>
 * <li>Nightly: earliest {@value #EARLIEST_HOUR}:00 local (WhatsApp writes at 02:00), charging
 *     preferred, override deadline {@value #DEADLINE_HOUR}:00 — after which it runs without the
 *     constraint.</li>
 * <li>{@code being_written}, {@code no_backup_found} and an I/O failure retry +30 min, at most
 *     {@value #MAX_RETRIES} times, then wait for the next night.</li>
 * <li>App opened with no successful run for 26 h → run now (a force-stop cancels jobs silently) —
 *     but not again within 30 min of the last attempt, so an outage is not retried on every resume.</li>
 * <li>A dry run only before the channel has ever opened: on the user's tap, or nightly for 7 days
 *     after it (review 4, verify new 3).</li>
 * </ul>
 */
final class NightlySchedule {
    static final int EARLIEST_HOUR = 3, DEADLINE_HOUR = 6;
    static final long RETRY_MS = 30 * 60 * 1000L;
    /** A retry runs at +30 min, or by +45 min without the charging constraint. */
    static final long RETRY_SLACK_MS = 15 * 60 * 1000L;
    static final int MAX_RETRIES = 6;
    static final long OVERDUE_MS = 26 * 3600 * 1000L;
    static final long APP_OPEN_GAP_MS = 30 * 60 * 1000L;
    static final long DRY_WINDOW_MS = 7 * 24 * 3600 * 1000L;

    /** The three the plan retries; every other code waits for the next night. */
    static final Set<String> RETRY_LATER = Collections.unmodifiableSet(new HashSet<>(Arrays.asList(
            BackupError.BEING_WRITTEN.code, BackupError.NO_BACKUP_FOUND.code, RunReport.IO_ERROR)));

    /** A job that found a run in progress, or a run the system stopped, runs again this soon (F5). */
    static final long SOON_MS = 5 * 60 * 1000L;

    /** What a run's end asks for: the next night, +30 min, +5 min (F5), or nothing (the user's cancel). */
    enum Next { NIGHT, RETRY, SOON, NONE }

    private NightlySchedule() {}

    /** {earliest, deadline} in ms: the next 03:00 after {@code nowMs}, and 06:00 that same morning. */
    static long[] nextNight(long nowMs, TimeZone tz) {
        Calendar c = Calendar.getInstance(tz);
        c.setTimeInMillis(nowMs);
        c.set(Calendar.HOUR_OF_DAY, EARLIEST_HOUR);
        c.set(Calendar.MINUTE, 0);
        c.set(Calendar.SECOND, 0);
        c.set(Calendar.MILLISECOND, 0);
        if (c.getTimeInMillis() <= nowMs) c.add(Calendar.DAY_OF_MONTH, 1);
        long earliest = c.getTimeInMillis();
        c.set(Calendar.HOUR_OF_DAY, DEADLINE_HOUR);
        return new long[] {earliest, c.getTimeInMillis()};
    }

    /** {earliest, deadline} for a retry. */
    static long[] retry(long nowMs) {
        return new long[] {nowMs + RETRY_MS, nowMs + RETRY_MS + RETRY_SLACK_MS};
    }

    /**
     * After a run that ended with {@code error}: retry for the three, while retries remain; else
     * the next night. Updates {@code state.retries}: counted up on a retry, reset otherwise.
     */
    static Next after(String error, NightlyState state) {
        if (RETRY_LATER.contains(error) && state.retries < MAX_RETRIES) {
            state.retries++;
            return Next.RETRY;
        }
        state.retries = 0;
        return Next.NIGHT;
    }

    /** {earliest, deadline} for a soon run (F5). */
    static long[] soon(long nowMs) {
        return new long[] {nowMs + SOON_MS, nowMs + SOON_MS + RETRY_SLACK_MS};
    }

    /**
     * After a run ends (F5): the user's {@code cancel()} (the gate closed, "Turn off") ends it
     * with nothing scheduled; a system stop ({@code onStopJob}) runs again soon — the backfill
     * resumes from the advanced cursor — while retries remain, else the next night; any other
     * end is {@link #after}. Updates {@code state.retries}.
     */
    static Next afterEnd(boolean userCancelled, boolean systemStopped, String error, NightlyState state) {
        if (userCancelled) return Next.NONE;
        if (systemStopped) return soonOrNight(state);
        return after(error == null ? "" : error, state);
    }

    /**
     * A scheduled job that found a run still in progress (F5): never finished with nothing — run
     * again soon while retries remain, else the next night. Updates {@code state.retries}.
     */
    static Next whenBusy(NightlyState state) {
        return soonOrNight(state);
    }

    private static Next soonOrNight(NightlyState state) {
        if (state.retries < MAX_RETRIES) {
            state.retries++;
            return Next.SOON;
        }
        state.retries = 0;
        return Next.NIGHT;
    }

    /**
     * The app-open recheck of a closed gate (F6): paired, the channel open once on this install,
     * the last known state not OPEN, and not within 30 min of the last recheck — so a 403 that has
     * since lifted is noticed without the WhatsApp screen being opened.
     */
    static boolean recheckGate(boolean paired, boolean everOpened, Gate.State s, long nowMs, long lastCheckMs) {
        if (!paired || !everOpened || s == Gate.State.OPEN) return false;
        return lastCheckMs <= 0 || nowMs < lastCheckMs || nowMs - lastCheckMs >= APP_OPEN_GAP_MS;
    }

    static final String DRY_STARTED = "Dry run started — nothing is sent while the link is off";
    static final String RUN_STARTED = "Run started";

    /**
     * What the screen says for a "Dry run now" tap (F9): a dry run before the channel has ever
     * opened, with consent recorded — never claiming "nothing is sent" unconditionally, since the
     * VM's answer at run time decides; the real run when the gate is already OPEN; else "" (nothing
     * started).
     */
    static String dryTapLabel(Gate.State s, boolean everOpened) {
        if (s == Gate.State.OPEN) return RUN_STARTED;
        if (s == Gate.State.CONSENTED_OFF && !everOpened) return DRY_STARTED;
        return "";
    }

    /** Within 7 days of the user's last "Dry run now" tap. */
    static boolean inDryWindow(long nowMs, long tapMs) {
        return tapMs > 0 && nowMs >= tapMs && nowMs - tapMs < DRY_WINDOW_MS;
    }

    /**
     * Whether a job may be scheduled at all: the channel open, or — before it has ever opened —
     * consent recorded and a dry-run window running; and in both cases a key stored and All-files
     * access held (§ 3.12: the job is scheduled only after the user's own grants).
     */
    static boolean jobAllowed(Gate.State s, boolean everOpened, boolean inDryWindow, boolean keyStored, boolean filesGranted) {
        if (!keyStored || !filesGranted) return false;
        if (s == Gate.State.OPEN) return true;
        return s == Gate.State.CONSENTED_OFF && !everOpened && inDryWindow;
    }

    /** The app-open rule: no successful run for 26 h, and no attempt in the last 30 min. */
    static boolean overdue(long nowMs, long lastSuccessMs, long lastAttemptMs) {
        if (lastAttemptMs > 0 && nowMs - lastAttemptMs < APP_OPEN_GAP_MS && nowMs >= lastAttemptMs) return false;
        return lastSuccessMs <= 0 || nowMs - lastSuccessMs > OVERDUE_MS;
    }
}
