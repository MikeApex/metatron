package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.util.Calendar;
import java.util.Collections;
import java.util.List;
import java.util.TimeZone;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** When the nightly read runs (plan § 3.2), its state, and the run-status lines. All made up. */
public class NightlyScheduleTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final TimeZone TZ = TimeZone.getTimeZone("Europe/Sofia");
    private static final long MIN = 60_000L, HOUR = 60 * MIN, DAY = 24 * HOUR;

    private static long at(int y, int mo, int d, int h, int mi) {
        return at(TZ, y, mo, d, h, mi);
    }

    private static long at(TimeZone tz, int y, int mo, int d, int h, int mi) {
        Calendar c = Calendar.getInstance(tz);
        c.clear();
        c.set(y, mo - 1, d, h, mi, 0);
        return c.getTimeInMillis();
    }

    @Test
    public void theNextNightIsThreeToSixLocal() {
        long[] w = NightlySchedule.nextNight(at(2026, 11, 23, 14, 0), TZ);
        assertEquals(at(2026, 11, 24, 3, 0), w[0]);
        assertEquals(at(2026, 11, 24, 6, 0), w[1]);
        w = NightlySchedule.nextNight(at(2026, 11, 23, 1, 30), TZ);
        assertEquals(at(2026, 11, 23, 3, 0), w[0]);
        w = NightlySchedule.nextNight(at(2026, 11, 23, 3, 0), TZ);
        assertEquals("a run finishing at 03:00 waits for tomorrow", at(2026, 11, 24, 3, 0), w[0]);
    }

    @Test
    public void theNextNightHoldsAcrossADaylightSavingChange() {
        // A zone whose clocks change at 02:00, so 03:00 exists exactly once on both change days.
        TimeZone z = TimeZone.getTimeZone("Europe/Berlin");
        for (int[] d : new int[][] {{3, 28}, {10, 24}}) {
            long[] w = NightlySchedule.nextNight(at(z, 2026, d[0], d[1], 22, 0), z);
            assertEquals(at(z, 2026, d[0], d[1] + 1, 3, 0), w[0]);
            assertEquals(at(z, 2026, d[0], d[1] + 1, 6, 0), w[1]);
            assertEquals(3 * HOUR, w[1] - w[0]);
        }
    }

    @Test
    public void exactlyTheThreeRetryLaterCodesRetryThirtyMinutesOnSixTimes() {
        for (String code : new String[] {"being_written", "no_backup_found", "io_error"}) {
            NightlyState s = new NightlyState();
            for (int i = 1; i <= 6; i++) {
                assertEquals(code + " " + i, NightlySchedule.Next.RETRY, NightlySchedule.after(code, s));
                assertEquals(i, s.retries);
            }
            assertEquals(NightlySchedule.Next.NIGHT, NightlySchedule.after(code, s));
            assertEquals(0, s.retries);
        }
        for (String code : new String[] {"", "integrity", "wrong_key", "post_failed", "share_out_of_step", "no_key"}) {
            NightlyState s = new NightlyState();
            s.retries = 3;
            assertEquals(code, NightlySchedule.Next.NIGHT, NightlySchedule.after(code, s));
            assertEquals(0, s.retries);
        }
        long[] r = NightlySchedule.retry(1_000_000L);
        assertEquals(1_000_000L + 30 * MIN, r[0]);
        assertTrue(r[1] > r[0]);
    }

    @Test
    public void onlyTheUsersCancelEndsWithNothingScheduled() {
        // F5: a system stop resumes soon; the user's cancel (gate closed, "Turn off") ends it.
        NightlyState s = new NightlyState();
        assertEquals(NightlySchedule.Next.NONE, NightlySchedule.afterEnd(true, false, "", s));
        assertEquals("the user's cancel wins over a system stop",
                NightlySchedule.Next.NONE, NightlySchedule.afterEnd(true, true, "", s));
        assertEquals(0, s.retries);
        assertEquals(NightlySchedule.Next.SOON, NightlySchedule.afterEnd(false, true, "", s));
        assertEquals(1, s.retries);
        assertEquals("a finished run is after()", NightlySchedule.Next.NIGHT, NightlySchedule.afterEnd(false, false, "", s));
        assertEquals(0, s.retries);
        assertEquals(NightlySchedule.Next.RETRY, NightlySchedule.afterEnd(false, false, "io_error", s));
        // Within the retry cap, then the next night — never nothing.
        s.retries = 0;
        for (int i = 1; i <= NightlySchedule.MAX_RETRIES; i++) {
            assertEquals(NightlySchedule.Next.SOON, NightlySchedule.afterEnd(false, true, "", s));
        }
        assertEquals(NightlySchedule.Next.NIGHT, NightlySchedule.afterEnd(false, true, "", s));
        long[] w = NightlySchedule.soon(1_000_000L);
        assertEquals(1_000_000L + 5 * MIN, w[0]);
        assertTrue(w[1] > w[0]);
    }

    @Test
    public void aJobThatFindsARunInProgressRunsAgainSoonNeverNothing() {
        NightlyState s = new NightlyState();
        for (int i = 1; i <= NightlySchedule.MAX_RETRIES; i++) {
            assertEquals(NightlySchedule.Next.SOON, NightlySchedule.whenBusy(s));
        }
        assertEquals(NightlySchedule.Next.NIGHT, NightlySchedule.whenBusy(s));
        assertEquals(0, s.retries);
    }

    @Test
    public void anAppOpenRechecksAClosedGateOnceItHasBeenOpenAtMostEvery30Minutes() {
        // F6: recovery after a 403 without the WhatsApp screen being opened.
        long now = 10 * DAY;
        for (Gate.State st : new Gate.State[] {Gate.State.CONSENTED_OFF, Gate.State.NO_CONSENT, Gate.State.UNPAIRED}) {
            assertTrue(st.name(), NightlySchedule.recheckGate(true, true, st, now, 0));
        }
        assertFalse("already open", NightlySchedule.recheckGate(true, true, Gate.State.OPEN, now, 0));
        assertFalse("not paired", NightlySchedule.recheckGate(false, true, Gate.State.CONSENTED_OFF, now, 0));
        assertFalse("never open: the screen asks", NightlySchedule.recheckGate(true, false, Gate.State.CONSENTED_OFF, now, 0));
        assertFalse("asked ten minutes ago", NightlySchedule.recheckGate(true, true, Gate.State.CONSENTED_OFF, now, now - 10 * MIN));
        assertTrue(NightlySchedule.recheckGate(true, true, Gate.State.CONSENTED_OFF, now, now - 30 * MIN));
        assertTrue("a clock set back", NightlySchedule.recheckGate(true, true, Gate.State.CONSENTED_OFF, now, now + HOUR));
    }

    @Test
    public void theDryRunTapNeverClaimsNothingIsSentUnconditionally() {
        // F9.
        assertEquals(NightlySchedule.RUN_STARTED, NightlySchedule.dryTapLabel(Gate.State.OPEN, true));
        assertEquals(NightlySchedule.RUN_STARTED, NightlySchedule.dryTapLabel(Gate.State.OPEN, false));
        String dry = NightlySchedule.dryTapLabel(Gate.State.CONSENTED_OFF, false);
        assertEquals(NightlySchedule.DRY_STARTED, dry);
        assertTrue(dry.contains("while the link is off"));
        assertEquals("", NightlySchedule.dryTapLabel(Gate.State.CONSENTED_OFF, true));
        assertEquals("", NightlySchedule.dryTapLabel(Gate.State.NO_CONSENT, false));
        assertEquals("", NightlySchedule.dryTapLabel(Gate.State.UNPAIRED, false));
    }

    @Test
    public void theAppOpenRuleIs26HoursWithoutSuccessAndNotWithin30MinutesOfAnAttempt() {
        long now = 10 * DAY;
        assertTrue("never succeeded", NightlySchedule.overdue(now, 0, 0));
        assertFalse(NightlySchedule.overdue(now, now - 25 * HOUR, now - 25 * HOUR));
        assertFalse(NightlySchedule.overdue(now, now - 26 * HOUR, now - 26 * HOUR));
        assertTrue(NightlySchedule.overdue(now, now - 26 * HOUR - 1, now - 26 * HOUR - 1));
        assertFalse("tried ten minutes ago", NightlySchedule.overdue(now, now - 30 * HOUR, now - 10 * MIN));
        assertTrue(NightlySchedule.overdue(now, now - 30 * HOUR, now - 31 * MIN));
    }

    @Test
    public void theDryWindowIsSevenDaysFromTheTap() {
        long tap = 5 * DAY;
        assertFalse(NightlySchedule.inDryWindow(tap, 0));
        assertTrue(NightlySchedule.inDryWindow(tap, tap));
        assertTrue(NightlySchedule.inDryWindow(tap + 7 * DAY - 1, tap));
        assertFalse(NightlySchedule.inDryWindow(tap + 7 * DAY, tap));
        assertFalse(NightlySchedule.inDryWindow(tap - 1, tap));
    }

    @Test
    public void aJobOnlyWithTheChannelOpenOrADryWindowBeforeTheFirstOpenAndBothGrants() {
        for (Gate.State s : Gate.State.values()) {
            assertFalse(NightlySchedule.jobAllowed(s, false, true, false, true));
            assertFalse(NightlySchedule.jobAllowed(s, false, true, true, false));
        }
        assertTrue(NightlySchedule.jobAllowed(Gate.State.OPEN, true, false, true, true));
        assertTrue(NightlySchedule.jobAllowed(Gate.State.CONSENTED_OFF, false, true, true, true));
        assertFalse(NightlySchedule.jobAllowed(Gate.State.CONSENTED_OFF, false, false, true, true));
        assertFalse(NightlySchedule.jobAllowed(Gate.State.CONSENTED_OFF, true, true, true, true));
        assertFalse(NightlySchedule.jobAllowed(Gate.State.NO_CONSENT, false, true, true, true));
        assertFalse(NightlySchedule.jobAllowed(Gate.State.UNPAIRED, false, true, true, true));
    }

    @Test
    public void theJobStateSurvivesAReloadAndAnUnreadableFileReadsEmpty() throws Exception {
        File dir = tmp.newFolder("state");
        NightlyState.update(dir, s -> {
            s.lastSuccessMs = 11;
            s.lastAttemptMs = 12;
            s.dryTapMs = 13;
            s.backupWritten = 14;
            s.fullBackupWritten = 15;
            s.retries = 2;
            s.gateCheckMs = 16;
        });
        NightlyState s = NightlyState.load(dir);
        assertEquals(11, s.lastSuccessMs);
        assertEquals(13, s.dryTapMs);
        assertEquals(15, s.fullBackupWritten);
        assertEquals(2, s.retries);
        assertEquals(16, s.gateCheckMs);
        java.nio.file.Files.write(new File(dir, NightlyState.FILE).toPath(), "{not json".getBytes("UTF-8"));
        assertEquals(0, NightlyState.load(dir).lastSuccessMs);
    }

    @Test
    public void theLastReportRoundTripsAndTheStatusLinesCarryCountsAndLabelsOnly() throws Exception {
        File dir = tmp.newFolder("state2");
        RunReport r = new RunReport();
        r.runAt = 1_700_000_000L;
        r.dryRun = 1;
        r.postedMessages = 4;
        r.baseReceived = 30;
        LastReport.ChatCount c = new LastReport.ChatCount("made-up-label-heron-with-a-much-longer-name-than-fits");
        c.messages = 4;
        new LastReport(r, Collections.singletonList(c), Collections.singletonList("TEXT_GONE")).save(dir);
        LastReport back = LastReport.load(dir);
        assertNotNull(back);
        assertEquals(4, back.report.postedMessages);
        assertEquals(LastReport.MAX_LABEL, back.chats.get(0).label.length());
        assertTrue(new File(dir, LastReport.FILE).length() < 1024);
        NightlyState st = new NightlyState();
        st.dryTapMs = 1_700_000_000_000L;
        List<String> lines = RunStatusView.lines(back, st, 7, 1_700_000_000_000L + DAY, TimeZone.getTimeZone("UTC"));
        String all = String.join("\n", lines);
        assertTrue(all.contains("Nothing was sent"));
        assertTrue(all.contains("made-up-label-heron"));
        assertTrue(all.contains(Notices.title(Notices.Notice.TEXT_GONE)));
        assertTrue(all.contains("Dry runs nightly until"));
        assertTrue(all.contains("remembered as sent: 7"));
        assertEquals("No nightly read has run yet.",
                RunStatusView.lines(null, new NightlyState(), -1, 0, TimeZone.getTimeZone("UTC")).get(0));
    }

    @Test
    public void aRefusalIsShownInItsWrittenWordsNeverAsAnExceptionMessage() {
        RunReport r = new RunReport();
        r.error = "wrong_key";
        String first = new LastReport(r, Collections.<LastReport.ChatCount>emptyList(), Collections.<String>emptyList())
                .lines(TimeZone.getTimeZone("UTC")).get(0);
        assertTrue(first.contains(BackupError.WRONG_KEY.userText));
        assertEquals(LastReport.reason(NightlyRead.NO_KEY), "no backup key is stored");
    }
}
