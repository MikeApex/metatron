package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.File;
import java.io.IOException;
import java.util.TimeZone;

/**
 * The probe's plain-Java helper (ProbeLines): the survival test's event line and the
 * increment-file pick. Lives in src/testWaprobe/, never src/test/ — a debug-variant test that
 * names a waprobe class breaks that variant's compile and the 19 reader tests with it.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'
 */
public class ProbeLinesTest {
    private static final TimeZone UTC = TimeZone.getTimeZone("UTC");
    /** 2026-11-23 07:15:30 UTC. */
    private static final long POST = 1_763_882_130_000L;

    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    // ---- event line --------------------------------------------------------------------

    @Test public void eventLineCarriesPostRxDelayKindAndMaskedChat() {
        String line = ProbeLines.eventLine(POST, POST + 4_200, "one-to-one", ProbeMask.format("123456789012345@lid"), UTC);
        assertEquals("post 07:15:30 · rx 07:15:34 · delay +4s · one-to-one · #{15}@lid", line);
    }

    @Test public void unknownRxReadsAsUnknownNotAsZero() {
        String line = ProbeLines.eventLine(POST, ProbeLines.UNKNOWN, "group", "(none)", UTC);
        assertEquals("post 07:15:30 · rx ?       · delay ? · group · (none)", line);
        assertEquals(line, ProbeLines.eventLine(POST, 0, "group", "(none)", UTC));
    }

    @Test public void maskedChatNeverShowsTheDigits() {
        String line = ProbeLines.eventLine(POST, POST, "one-to-one", ProbeMask.format("447700900123@s.whatsapp.net"), UTC);
        assertFalse(line, line.contains("447700900123"));
        assertTrue(line, line.endsWith("#{12}@s.whatsapp.net"));
    }

    @Test public void delayScalesSecondsMinutesHoursAndKeepsSign() {
        assertEquals("+0s", ProbeLines.delay(999));
        assertEquals("+59s", ProbeLines.delay(59_999));
        assertEquals("+2m 05s", ProbeLines.delay(125_000));
        assertEquals("+3h 07m", ProbeLines.delay((3 * 3600 + 7 * 60 + 12) * 1000L));
        assertEquals("-3s", ProbeLines.delay(-3_000)); // listener clock behind the post time
    }

    @Test public void kindSplitsSummaryGroupOneToOneOther() {
        assertEquals("summary", ProbeLines.kind(true, true, true));
        assertEquals("group", ProbeLines.kind(false, true, true));
        assertEquals("one-to-one", ProbeLines.kind(false, true, false));
        assertEquals("other", ProbeLines.kind(false, false, false));
    }

    @Test public void dayHeadingUsesTheGivenZone() {
        assertEquals("11-23 Sun", ProbeLines.day(POST, UTC));
    }

    // ---- increment pick ----------------------------------------------------------------

    @Test public void incrementNameMatchesOnlyTheNightlyPattern() {
        assertTrue(ProbeLines.isIncrement("msgstore-increment-1-2026-11-22.1.db.crypt15"));
        assertTrue(ProbeLines.isIncrement("msgstore-increment-12-2026-11-22.1.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-2026-11-22.1.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1-2026-11-22.1.db.crypt14"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-2026-11-22.1.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1-2026-11-22.1.db.crypt15.tmp"));
    }

    @Test public void undatedLiveIncrementMatchesToo() {
        assertTrue(ProbeLines.isIncrement("msgstore-increment-1.db.crypt15"));
        assertTrue(ProbeLines.isIncrement("msgstore-increment-14.db.crypt15"));
        assertFalse(ProbeLines.isDatedIncrement("msgstore-increment-14.db.crypt15"));
        assertTrue(ProbeLines.isDatedIncrement("msgstore-increment-1-2026-11-22.1.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1.1.db.crypt15"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1.db.crypt14"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1.db.crypt15.tmp"));
        assertFalse(ProbeLines.isIncrement("msgstore-increment-1-2026-11-22.db.crypt15")); // dated needs .1
        assertFalse(ProbeLines.isDatedIncrement("msgstore.db.crypt15"));
    }

    @Test public void countsEachFormAndIgnoresTheRest() throws IOException {
        File[] listing = {
                file("msgstore-increment-1.db.crypt15", 1_000L),
                file("msgstore-increment-2.db.crypt15", 2_000L),
                file("msgstore-increment-1-2026-11-16.1.db.crypt15", 500L),
                file("msgstore.db.crypt15", 3_000L),
                file("msgstore-2026-11-17.1.db.crypt15", 3_000L),
                tmp.newFolder("msgstore-increment-3.db.crypt15")};
        int[] n = ProbeLines.countIncrements(listing);
        assertEquals(2, n[0]);
        assertEquals(1, n[1]);
        assertEquals(0, ProbeLines.countIncrements(null)[0]);
    }

    @Test public void newestAcrossBothFormsIsByTime() throws IOException {
        File rotated = file("msgstore-increment-5-2026-11-16.1.db.crypt15", 1_000_000L);
        File live = file("msgstore-increment-2.db.crypt15", 2_000_000L);
        assertEquals(live, ProbeLines.newestIncrement(new File[]{rotated, live}));
        // After an overnight full backup the newest may be a freshly rotated, dated one.
        File freshRotated = file("msgstore-increment-6-2026-11-23.1.db.crypt15", 3_000_000L);
        assertEquals(freshRotated, ProbeLines.newestIncrement(new File[]{rotated, live, freshRotated}));
    }

    @Test public void tieOnTimeGoesToTheUndatedThenHigherN() throws IOException {
        File dated = file("msgstore-increment-9-2026-11-22.1.db.crypt15", 5_000_000L);
        File live2 = file("msgstore-increment-2.db.crypt15", 5_000_000L);
        File live10 = file("msgstore-increment-10.db.crypt15", 5_000_000L);
        assertEquals(live2, ProbeLines.newestIncrement(new File[]{dated, live2}));
        assertEquals(live10, ProbeLines.newestIncrement(new File[]{live2, dated, live10}));
    }

    @Test public void newestIncrementByTimeIgnoringFullBackups() throws IOException {
        File old = file("msgstore-increment-3-2026-11-20.1.db.crypt15", 1_000_000L);
        File mid = file("msgstore-increment-1-2026-11-22.1.db.crypt15", 2_000_000L);
        File full = file("msgstore.db.crypt15", 9_000_000L); // newer, but a full backup
        File dated = file("msgstore-2026-11-22.1.db.crypt15", 9_000_000L);
        assertEquals(mid, ProbeLines.newestIncrement(new File[]{old, full, mid, dated}));
    }

    @Test public void tieOnTimeGoesToLaterDateThenHigherN() throws IOException {
        File a = file("msgstore-increment-9-2026-11-21.1.db.crypt15", 5_000_000L);
        File b = file("msgstore-increment-2-2026-11-22.1.db.crypt15", 5_000_000L);
        File c = file("msgstore-increment-10-2026-11-22.1.db.crypt15", 5_000_000L);
        assertEquals(c, ProbeLines.newestIncrement(new File[]{a, c, b}));
        assertEquals(b, ProbeLines.newestIncrement(new File[]{a, b}));
    }

    @Test public void noIncrementOrNoListingIsNull() throws IOException {
        assertNull(ProbeLines.newestIncrement(null));
        assertNull(ProbeLines.newestIncrement(new File[]{file("msgstore.db.crypt15", 1_000L)}));
        File dir = tmp.newFolder("msgstore-increment-1-2026-11-22.1.db.crypt15"); // a directory, not a file
        assertNull(ProbeLines.newestIncrement(new File[]{dir}));
    }

    private File file(String name, long mtime) throws IOException {
        File f = tmp.newFile(name);
        assertTrue(f.setLastModified(mtime));
        return f;
    }
}
