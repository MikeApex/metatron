package com.mike.metatron.whatsapp;

import static com.mike.metatron.whatsapp.NightlyFakes.GROUP;
import static com.mike.metatron.whatsapp.NightlyFakes.HIDDEN;
import static com.mike.metatron.whatsapp.NightlyFakes.LABEL;
import static com.mike.metatron.whatsapp.NightlyFakes.MEMBER;
import static com.mike.metatron.whatsapp.NightlyFakes.OTHER;
import static com.mike.metatron.whatsapp.NightlyFakes.PHONE;
import static com.mike.metatron.whatsapp.NightlyFakes.T1;
import static com.mike.metatron.whatsapp.NightlyFakes.T2;
import static com.mike.metatron.whatsapp.NightlyFakes.T3;
import static com.mike.metatron.whatsapp.NightlyFakes.accepted;
import static com.mike.metatron.whatsapp.NightlyFakes.count;
import static com.mike.metatron.whatsapp.NightlyFakes.mine;
import static com.mike.metatron.whatsapp.NightlyFakes.ok;
import static com.mike.metatron.whatsapp.NightlyFakes.received;
import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Map;
import java.util.TimeZone;
import java.util.function.Function;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** One run of the nightly job (plan §§ 3.2, 3.5, 3.6; review 4, verify 6, verify new 3). All made up. */
public class NightlyRunTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final long NOW = 1_700_000_000_000L;
    private static final long NOW_S = NOW / 1000;
    private static final long DAY = 24 * 3600L;
    private static final long H = 3600L;

    private final List<String> log = new ArrayList<>();
    private NightlyFakes.FakeApi api;
    private NightlyFakes.FakeEnv env;
    private NightlyFakes.RunHost host;
    private File state, scratch;
    /** What the cursor call answers. */
    private DeviceApi.Result cursorReply = ok("{\"cursor\":" + (NOW_S - DAY) + "}");

    @Before
    public void setUp() throws IOException {
        SentHashes.forgetInstancesForTest();
        NightlyRead.forgetChatList();
        state = tmp.newFolder("wa_state");
        scratch = tmp.newFolder("wa_dry_sent");
        env = new NightlyFakes.FakeEnv(tmp.newFolder("root"), NOW, log);
        api = new NightlyFakes.FakeApi(log, defaultVm());
        host = new NightlyFakes.RunHost(api, env, state, scratch, NOW);
        host.kinds.put(PHONE, EventPlan.ONE_TO_ONE);
        host.kinds.put(GROUP, EventPlan.GROUP);
        env.baseMessages.add(received(PHONE, NOW_S - 2 * H, T1, 1));
        env.baseMessages.add(new WaMessage(GROUP, "made-up-key-2", false, (NOW_S - H) * 1000, MEMBER, T2, 2, 0, null));
        env.baseMessages.add(mine(PHONE, NOW_S - 30 * 60, 3));
        env.baseMessages.add(received(OTHER, NOW_S - H, T3, 4)); // not shared
    }

    @After
    public void tearDown() {
        NightlyRead.forgetChatList();
        SentHashes.forgetInstancesForTest();
    }

    private Function<NightlyFakes.Call, DeviceApi.Result> defaultVm() {
        return c -> {
            if (c.path.equals(NightlyRun.CURSOR_PATH)) return cursorReply;
            if (c.path.equals(Poster.PATH)) return accepted(((List<?>) c.json().get("events")).size());
            return ok("{\"ok\":true}");
        };
    }

    private NightlyRun.Outcome run(NightlyRun.Trigger t) throws IOException {
        env.files();
        return new NightlyRun(host).run(t);
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> postedReport() {
        List<NightlyFakes.Call> p = api.posts(NightlyRun.RUN_PATH);
        assertEquals(1, p.size());
        return (Map<String, Object>) p.get(0).json().get("report");
    }

    private String lastReportFile() throws IOException {
        return new String(Files.readAllBytes(new File(state, LastReport.FILE).toPath()), StandardCharsets.UTF_8);
    }

    private void assertNoContent(String s) {
        for (String t : new String[] {T1, T2, T3, PHONE, GROUP, MEMBER, OTHER}) assertFalse(s.contains(t));
    }

    // ---- the open channel ----------------------------------------------------------------------

    @Test
    public void theReadComesBeforeTheShareListPostAndEventsOnlyAfterItIsAccepted() throws IOException {
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals(NightlyRun.Kind.REAL, o.kind);
        assertEquals("", o.error);
        assertEquals(Arrays.asList("GET " + NightlyRun.CURSOR_PATH, "decrypt", "share", "POST " + Poster.PATH,
                "POST " + NightlyRun.RUN_PATH), log);
        Map<String, Object> rep = postedReport();
        assertEquals(2L, rep.get("posted_messages"));
        assertEquals(1L, rep.get("posted_reply_markers"));
        assertEquals(0L, rep.get("dry_run"));
        assertEquals(3L, rep.get("base_received"));
        assertEquals("", rep.get("error"));
        assertEquals(3, SentHashes.open(state).size());
        // the cursor the batch carried is its newest second (the reply marker, half an hour ago)
        Object cursor = api.posts(Poster.PATH).get(0).json().get("cursor");
        assertEquals(NOW_S - 30 * 60, (long) (Long) cursor);
    }

    @Test
    public void aNightWithNoSavedShareListSendsNoEventsButStillReports() throws IOException {
        host.share = ShareList.Post.NOT_SAVED;
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals("", o.error);
        assertTrue(api.posts(Poster.PATH).isEmpty());
        assertEquals("", postedReport().get("error"));
        assertEquals(0, SentHashes.open(state).size());
    }

    @Test
    public void aRefusedShareListPostSendsNoEventsAndReportsOutOfStep() throws IOException {
        host.share = ShareList.Post.REFUSED;
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals(RunReport.SHARE_OUT_OF_STEP, o.error);
        assertTrue(api.posts(Poster.PATH).isEmpty());
        assertEquals(RunReport.SHARE_OUT_OF_STEP, postedReport().get("error"));
    }

    @Test
    public void aFirstReadWithNoCursorStartsNinetyDaysBack() throws IOException {
        cursorReply = ok("{\"cursor\":null}");
        run(NightlyRun.Trigger.NIGHT);
        assertEquals(Long.valueOf(NOW_S - 90 * DAY), env.sinceSeen);
    }

    @Test
    public void theSentHashListIsPrunedToTheNewestCursor() throws IOException {
        SentHashes s = SentHashes.open(state);
        s.record("made-up-old|1|0", s.textHash("x"), new byte[0], NOW_S - 30 * DAY);
        run(NightlyRun.Trigger.NIGHT);
        assertNull(SentHashes.open(state).lookup("made-up-old|1|0"));
    }

    // ---- F2 / F3: a merge night, a forgotten VM ------------------------------------------------

    @Test
    public void aMergeNightSendsNothingForMessagesAlreadySentUnderTheOldId() throws IOException {
        host.kinds.remove(GROUP);
        SentHashes s = SentHashes.open(state);
        // Sent on an earlier night under the hidden id: the message and the reply marker.
        s.record(EventPlan.key(HIDDEN, NOW_S - 2 * H, 0), s.textHash(T1), s.senderHash(""), NOW_S - 2 * H);
        s.record(EventPlan.replyKey(HIDDEN, NOW_S - 30 * 60, 0), s.textHash(""), s.senderHash(""), NOW_S - 30 * 60);
        host.migrations.put(HIDDEN, PHONE);
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals("", o.error);
        assertTrue("nothing new to send", api.posts(Poster.PATH).isEmpty());
        assertEquals(1L, postedReport().get("skipped_unchanged"));
        SentHashes after = SentHashes.open(state);
        assertNotNull(after.lookup(EventPlan.key(PHONE, NOW_S - 2 * H, 0)));
        assertNull(after.lookup(EventPlan.key(HIDDEN, NOW_S - 2 * H, 0)));
    }

    @Test
    public void aNullCursorWithANonEmptyListClearsItAndBuildsEvents() throws IOException {
        cursorReply = ok("{\"cursor\":null}");
        // The VM once answered a cursor for this install, and now answers none: it forgot this user.
        NightlyState.update(state, st -> st.cursorSeen = NOW_S - 3 * DAY);
        SentHashes s = SentHashes.open(state);
        s.record(EventPlan.key(PHONE, NOW_S - 2 * H, 0), s.textHash(T1), s.senderHash(""), NOW_S - 2 * H);
        s.record("made-up-gone|1|0", s.textHash("z"), new byte[0], NOW_S - DAY);
        run(NightlyRun.Trigger.NIGHT);
        Map<String, Object> rep = postedReport();
        assertEquals("the VM forgot it: sent again", 2L, rep.get("posted_messages"));
        assertEquals(0L, rep.get("skipped_unchanged"));
        SentHashes after = SentHashes.open(state);
        assertNull(after.lookup("made-up-gone|1|0"));
        assertEquals(3, after.size());
    }

    @Test
    public void theFirstNightsNullCursorKeepsWhatTheLiveFeedRecorded() throws IOException {
        // Before any batch has carried a cursor the VM answers null — the normal first night, since
        // live posts never carry one. What the live feed recorded that day must survive (verify NEW-1).
        cursorReply = ok("{\"cursor\":null}");
        SentHashes s = SentHashes.open(state);
        s.record(EventPlan.key(PHONE, NOW_S - 2 * H, 0), s.textHash(T1), s.senderHash(""), NOW_S - 2 * H);
        s.record("made-up-live|1|0", s.textHash("z"), new byte[0], NOW_S - H);
        run(NightlyRun.Trigger.NIGHT);
        assertEquals("recorded live: not sent again", 1L, postedReport().get("skipped_unchanged"));
        assertNotNull(SentHashes.open(state).lookup("made-up-live|1|0"));
    }

    @Test
    public void aCursorOnceAnsweredIsRemembered() throws IOException {
        cursorReply = ok("{\"cursor\":" + (NOW_S - DAY) + "}");
        run(NightlyRun.Trigger.NIGHT);
        assertEquals(NOW_S - DAY, NightlyState.load(state).cursorSeen);
    }

    @Test
    public void everyLinkedHiddenIdIsRekeyedEvenWithoutAMergeTonight() throws IOException {
        // The merge was accepted from the screen (or the run that carried it was cancelled): no
        // migration reaches this run, but tonight's tables still link the hidden id (verify, F2 residual).
        host.kinds.remove(GROUP);
        env.tables.putJid(901L, HIDDEN);
        env.tables.putJid(902L, PHONE);
        env.tables.putLink(901L, 902L);
        SentHashes s = SentHashes.open(state);
        s.record(EventPlan.key(HIDDEN, NOW_S - 2 * H, 0), s.textHash(T1), s.senderHash(""), NOW_S - 2 * H);
        assertTrue(host.migrations.isEmpty());
        run(NightlyRun.Trigger.NIGHT);
        SentHashes after = SentHashes.open(state);
        assertNotNull(after.lookup(EventPlan.key(PHONE, NOW_S - 2 * H, 0)));
        assertNull(after.lookup(EventPlan.key(HIDDEN, NOW_S - 2 * H, 0)));
        assertEquals("the same message under its new id: not sent again", 1L, postedReport().get("skipped_unchanged"));
    }

    @Test
    public void aDryRunNeverClearsTheList() throws IOException {
        consentedOff();
        cursorReply = new DeviceApi.Result(403, "", "consented_off");
        SentHashes s = SentHashes.open(state);
        s.record("made-up-prior|1|0", s.textHash("y"), new byte[0], NOW_S - DAY);
        host.migrations.put(HIDDEN, PHONE);
        run(NightlyRun.Trigger.DRY_TAP);
        SentHashes.forgetInstancesForTest();
        assertEquals(1, SentHashes.open(state).size());
        assertNotNull(SentHashes.open(state).lookup("made-up-prior|1|0"));
    }

    @Test
    public void aRefusedReadIsReportedByCodeAndRaisesReadRefused() throws IOException {
        env.decryptThrows = new BackupException(BackupError.INTEGRITY, "made-up detail");
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals("integrity", o.error);
        assertEquals("integrity", postedReport().get("error"));
        assertEquals(Boolean.TRUE, host.notices.get(Notices.Notice.READ_REFUSED));
        assertFalse(log.contains("share"));
    }

    @Test
    public void aRetryLaterCodeDoesNotRaiseReadRefused() throws IOException {
        env.decryptThrows = new IOException("made-up");
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals(RunReport.IO_ERROR, o.error);
        assertNull(host.notices.get(Notices.Notice.READ_REFUSED));
    }

    @Test
    public void aCleanRunClearsReadRefusedAndRecordsSuccess() throws IOException {
        run(NightlyRun.Trigger.NIGHT);
        assertEquals(Boolean.FALSE, host.notices.get(Notices.Notice.READ_REFUSED));
        assertEquals(NOW, NightlyState.load(state).lastSuccessMs);
    }

    @Test
    public void noAnswerFromTheVmWithTheChannelOpenIsARetryAndReadsNothing() throws IOException {
        cursorReply = new DeviceApi.Result(DeviceApi.NETWORK, "", "UnknownHostException");
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals(NightlyRun.Kind.STOPPED, o.kind);
        assertEquals(RunReport.IO_ERROR, o.error);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void noConsentReadsNothing() throws IOException {
        cursorReply = new DeviceApi.Result(403, "", "no_consent");
        assertEquals(NightlyRun.Kind.NOTHING, run(NightlyRun.Trigger.DRY_TAP).kind);
        assertEquals(0, env.decrypts);
        assertEquals(1, api.calls.size());
    }

    @Test
    public void aCancelDuringTheRunStopsWithoutAReport() throws IOException {
        env.cancelAfterDecrypt = true;
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertEquals(NightlyRun.Kind.STOPPED, o.kind);
        assertEquals(0, api.postCount());
        assertEquals(0, count(env.workDir));
    }

    @Test
    public void plantedTextsNeverReachTheReportsOrTheLastReportFile() throws IOException {
        NightlyRun.Outcome o = run(NightlyRun.Trigger.NIGHT);
        assertNoContent(api.posts(NightlyRun.RUN_PATH).get(0).body);
        assertNoContent(lastReportFile());
        assertNoContent(o.toString());
        assertNoContent(o.report.toString());
    }

    // ---- the dry run -----------------------------------------------------------------------------

    private void consentedOff() {
        cursorReply = new DeviceApi.Result(403, "", "consented_off");
        host.state = Gate.State.CONSENTED_OFF;
    }

    @Test
    public void theDryRunPostsNothingAndRecordsNothing() throws IOException {
        consentedOff();
        SentHashes s = SentHashes.open(state);
        s.record("made-up-prior|1|0", s.textHash("y"), new byte[0], NOW_S - DAY);
        byte[] before = Files.readAllBytes(new File(state, SentHashes.SENT_FILE).toPath());
        NightlyRun.Outcome o = run(NightlyRun.Trigger.DRY_TAP);
        assertEquals(NightlyRun.Kind.DRY, o.kind);
        assertEquals("only the cursor call", 1, api.calls.size());
        assertEquals(0, api.postCount());
        assertFalse(log.contains("share"));
        assertArrayEquals(before, Files.readAllBytes(new File(state, SentHashes.SENT_FILE).toPath()));
        SentHashes.forgetInstancesForTest();
        assertEquals(1, SentHashes.open(state).size());
    }

    @Test
    public void theDryRunReadsNinetyDaysAndKeepsWhatItWouldSendPerChat() throws IOException {
        consentedOff();
        run(NightlyRun.Trigger.DRY_TAP);
        assertEquals(Long.valueOf(NOW_S - 90 * DAY), env.sinceSeen);
        LastReport last = LastReport.load(state);
        assertNotNull(last);
        assertEquals(1, last.report.dryRun);
        assertEquals(2, last.report.postedMessages);
        assertEquals(1, last.report.postedReplyMarkers);
        assertEquals(2, last.chats.size());
        assertEquals(LABEL, last.chats.get(0).label);
        assertEquals(3, last.chats.get(0).total() + last.chats.get(1).total());
        String file = lastReportFile();
        assertNoContent(file);
        for (String line : last.lines(TimeZone.getTimeZone("UTC"))) assertNoContent(line);
    }

    @Test
    public void aDryRunWithNoSentListCreatesNoneAndLeavesNoScratch() throws IOException {
        consentedOff();
        run(NightlyRun.Trigger.DRY_TAP);
        assertFalse(new File(state, SentHashes.SALT_FILE).exists());
        assertFalse(new File(state, SentHashes.SENT_FILE).exists());
        assertEquals(0, count(scratch));
        assertEquals(2, LastReport.load(state).report.postedMessages);
    }

    @Test
    public void theDryRunKeepsTheNoticesItWouldRaiseWithoutRaisingThem() throws IOException {
        consentedOff();
        env.nowMs = NOW;
        host.nowMs = NOW + 3 * DAY * 1000; // the backup is now three days old
        run(NightlyRun.Trigger.DRY_TAP);
        assertTrue(host.notices.isEmpty());
        assertTrue(LastReport.load(state).wouldRaise.contains(Notices.Notice.BACKUP_STALE.name()));
    }

    @Test
    public void nightlyDryRunsRunForSevenDaysAfterTheTapThenStop() throws IOException {
        consentedOff();
        NightlyState.update(state, s -> s.dryTapMs = NOW - 6 * DAY * 1000);
        assertEquals(NightlyRun.Kind.DRY, run(NightlyRun.Trigger.NIGHT).kind);
        NightlyState.update(state, s -> s.dryTapMs = NOW - 7 * DAY * 1000 - 1);
        int decrypts = env.decrypts;
        assertEquals(NightlyRun.Kind.NOTHING, run(NightlyRun.Trigger.NIGHT).kind);
        assertEquals(decrypts, env.decrypts);
    }

    @Test
    public void noDryRunAtNightWithoutATap() throws IOException {
        consentedOff();
        assertEquals(NightlyRun.Kind.NOTHING, run(NightlyRun.Trigger.NIGHT).kind);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void neverADryRunOnceTheChannelHasBeenOpen() throws IOException {
        consentedOff();
        host.everOpened = true;
        NightlyState.update(state, s -> s.dryTapMs = NOW - 1000);
        assertEquals(NightlyRun.Kind.NOTHING, run(NightlyRun.Trigger.DRY_TAP).kind);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void aDryRunNeedsNothingFromTheVm() throws IOException {
        host.state = Gate.State.CONSENTED_OFF;
        cursorReply = new DeviceApi.Result(DeviceApi.NETWORK, "", "UnknownHostException");
        assertEquals(NightlyRun.Kind.DRY, run(NightlyRun.Trigger.DRY_TAP).kind);
        assertEquals(0, api.postCount());
    }

    // ---- the notice decisions ------------------------------------------------------------------

    private static RunReport report(long backupWritten, long fullWritten, long received, long text, String error) {
        RunReport r = new RunReport();
        r.backupWritten = backupWritten;
        r.fullBackupWritten = fullWritten;
        r.baseReceived = received;
        r.baseReceivedText = text;
        r.error = error;
        return r;
    }

    @Test
    public void staleWhenTheSetIsOlderThan52HoursOrTheFullBackupOlderThan8Days() {
        long n = NOW_S;
        Notices.Notice st = Notices.Notice.BACKUP_STALE;
        assertEquals(Boolean.TRUE, NightlyRun.decide(report(n - 52 * H - 1, n - DAY, 0, 0, ""), true, n, 0, 0).get(st));
        assertEquals(Boolean.FALSE, NightlyRun.decide(report(n - 52 * H, n - DAY, 0, 0, ""), true, n, 0, 0).get(st));
        assertEquals(Boolean.TRUE, NightlyRun.decide(report(n - H, n - 8 * DAY - 1, 0, 0, ""), true, n, 0, 0).get(st));
        assertEquals(Boolean.FALSE, NightlyRun.decide(report(n - H, n - 7 * DAY, 0, 0, ""), true, n, 0, 0).get(st));
    }

    @Test
    public void staleUsesTheLastWriteSeenWhenTheBackupCannotBeFound() {
        long n = NOW_S;
        Map<Notices.Notice, Boolean> d = NightlyRun.decide(report(0, 0, 0, 0, "no_backup_found"), false, n, n - 3 * DAY, n - 3 * DAY);
        assertEquals(Boolean.TRUE, d.get(Notices.Notice.BACKUP_STALE));
        assertNull("never seen: left alone", NightlyRun.decide(report(0, 0, 0, 0, "no_backup_found"), false, n, 0, 0)
                .get(Notices.Notice.BACKUP_STALE));
    }

    @Test
    public void textGoneNeedsTwentyReceivedRowsAndNoneWithText() {
        Notices.Notice tg = Notices.Notice.TEXT_GONE;
        assertEquals(Boolean.TRUE, NightlyRun.decide(report(0, 0, 20, 0, ""), true, NOW_S, 0, 0).get(tg));
        assertNull(NightlyRun.decide(report(0, 0, 19, 0, ""), true, NOW_S, 0, 0).get(tg));
        assertEquals(Boolean.FALSE, NightlyRun.decide(report(0, 0, 20, 1, ""), true, NOW_S, 0, 0).get(tg));
        assertNull("a read that did not finish says nothing", NightlyRun.decide(report(0, 0, 20, 0, "integrity"), false, NOW_S, 0, 0).get(tg));
    }

    @Test
    public void readRefusedForEveryRefusalButTheRetryLaterThreeAndThePostingCodes() {
        Notices.Notice rr = Notices.Notice.READ_REFUSED;
        for (BackupError e : BackupError.values()) {
            Boolean d = NightlyRun.decide(report(0, 0, 0, 0, e.code), false, NOW_S, 0, 0).get(rr);
            if (e == BackupError.BEING_WRITTEN || e == BackupError.NO_BACKUP_FOUND) assertNull(e.code, d);
            else assertEquals(e.code, Boolean.TRUE, d);
        }
        for (String c : new String[] {RunReport.IO_ERROR, RunReport.SHARE_OUT_OF_STEP, RunReport.POST_FAILED}) {
            assertNull(c, NightlyRun.decide(report(0, 0, 0, 0, c), true, NOW_S, 0, 0).get(rr));
        }
        assertEquals(Boolean.TRUE, NightlyRun.decide(report(0, 0, 0, 0, NightlyRead.NO_KEY), false, NOW_S, 0, 0).get(rr));
        assertEquals(Boolean.FALSE, NightlyRun.decide(report(0, 0, 0, 0, ""), true, NOW_S, 0, 0).get(rr));
    }

    @Test
    public void theCursorReplyIsReadStrictly() {
        assertArrayEquals(new Object[] {null}, NightlyRun.parseCursor("{\"cursor\":null}"));
        assertArrayEquals(new Object[] {5L}, NightlyRun.parseCursor("{\"cursor\":5}"));
        assertNull(NightlyRun.parseCursor("{}"));
        assertNull(NightlyRun.parseCursor("{\"cursor\":\"5\"}"));
        assertNull(NightlyRun.parseCursor("not json"));
    }
}
