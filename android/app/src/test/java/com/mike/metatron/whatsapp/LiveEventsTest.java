package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The live feed's decisions (build plan § 3.10) on synthetic notifications, a fake VM and a fake
 * clock. Every chat id and text here is made up.
 */
public class LiveEventsTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final String RAW_GROUP = "raw-group-shortcut-1";
    private static final String GROUP = "100000000001-1600000000@g.test";
    private static final String RAW_ONE = "raw-one-shortcut-2";
    private static final String ONE = "100000000002@s.test";
    private static final String RAW_HIDDEN = "raw-hidden-shortcut-3";
    private static final String RAW_UNSHARED = "raw-unshared-shortcut-4";

    private static final String T1 = "planted-live-text-amber-heron-7731";
    private static final String T2 = "planted-live-text-cobalt-otter-1904";
    private static final String T3 = "planted-live-text-dune-falcon-4418";
    private static final String OWN = "planted-own-text-ember-gull-6062";

    /** 2026-11-23 10:00:00 UTC, in ms; the message times sit in this second and the next. */
    private static final long BASE_MS = 1_795_428_000_000L;
    private static final long SECOND = BASE_MS / 1000;

    private File stateDir;
    private SentHashes sent;
    private FakeApi api;
    private FakeShares shares;
    private FakeGate gate;
    private long now;
    private LiveEvents live;

    private PrintStream realOut, realErr;
    private final ByteArrayOutputStream captured = new ByteArrayOutputStream();

    @Before
    public void setUp() {
        SentHashes.forgetInstancesForTest();
        stateDir = new File(tmp.getRoot(), "wa_state");
        sent = SentHashes.open(stateDir);
        api = new FakeApi();
        shares = new FakeShares();
        shares.link.put(RAW_GROUP, GROUP);
        shares.link.put(RAW_ONE, ONE);
        shares.kinds.put(GROUP, EventPlan.GROUP);
        shares.kinds.put(ONE, EventPlan.ONE_TO_ONE);
        gate = new FakeGate();
        now = BASE_MS + 5_000;
        live = new LiveEvents(api, () -> now, shares, gate, sent, Runnable::run);

        realOut = System.out;
        realErr = System.err;
        PrintStream cap = new PrintStream(captured, true);
        System.setOut(cap);
        System.setErr(cap);
    }

    @After
    public void tearDown() {
        System.setOut(realOut);
        System.setErr(realErr);
        SentHashes.forgetInstancesForTest();
    }

    // ---- fakes -------------------------------------------------------------------------------

    static final class FakeApi implements DeviceApi {
        final List<String> bodies = new ArrayList<>();
        final List<String> paths = new ArrayList<>();
        final List<Integer> timeouts = new ArrayList<>();
        final Deque<Result> scripted = new ArrayDeque<>();

        @Override
        public Result get(String path) {
            throw new AssertionError("the live feed makes no GET");
        }

        @Override
        public Result post(String path, String jsonBody, int readTimeoutMs) {
            paths.add(path);
            bodies.add(jsonBody);
            timeouts.add(readTimeoutMs);
            Result r = scripted.poll();
            return r != null ? r : acceptedAll(jsonBody);
        }

        static Result acceptedAll(String body) {
            int n = countEvents(body);
            return ok("{\"accepted\": " + n + ", \"duplicates\": 0, \"updated\": 0, \"dropped_not_shared\": 0,"
                    + " \"held_back\": 0, \"rejected\": [], \"action_needed\": false}");
        }
    }

    static DeviceApi.Result ok(String body) {
        return new DeviceApi.Result(200, body, "");
    }

    static final class FakeShares implements LiveEvents.Shares {
        final Map<String, String> link = new HashMap<>();
        final Map<String, String> kinds = new HashMap<>();
        boolean accepted = true;

        @Override
        public String canonicalShared(String raw) {
            String c = link.get(raw);
            return c != null && kinds.containsKey(c) ? c : null;
        }

        @Override
        public String kindOf(String canonical) {
            return kinds.get(canonical);
        }

        @Override
        public boolean acceptedCurrent() {
            return accepted;
        }
    }

    static final class FakeGate implements LiveEvents.GateView {
        boolean open = true;
        final List<Integer> observed = new ArrayList<>();

        @Override
        public boolean open() {
            return open;
        }

        @Override
        public boolean observe(DeviceApi.Result r) {
            observed.add(r.status);
            Gate.State s = Gate.next(open ? Gate.State.OPEN : Gate.State.NO_CONSENT, r.status, r.detail);
            open = s == Gate.State.OPEN;
            return open;
        }
    }

    // ---- helpers -----------------------------------------------------------------------------

    private static LiveEvents.Line in(long ms, String text) {
        return new LiveEvents.Line(ms, text, false);
    }

    private static LiveEvents.Posted post(String raw, LiveEvents.Line... lines) {
        return new LiveEvents.Posted(LiveEvents.WHATSAPP, false, raw, Arrays.asList(lines));
    }

    @SuppressWarnings("unchecked")
    private static List<Map<String, Object>> events(String body) {
        try {
            return (List<Map<String, Object>>) ((Map<String, Object>) Json.parse(body)).get("events");
        } catch (Json.Malformed e) {
            throw new AssertionError("body is not JSON");
        }
    }

    private static int countEvents(String body) {
        return events(body).size();
    }

    private List<Map<String, Object>> allPosted() {
        List<Map<String, Object>> out = new ArrayList<>();
        for (String b : api.bodies) out.addAll(events(b));
        return out;
    }

    // ---- what is not sent --------------------------------------------------------------------

    @Test
    public void groupSummaryIsSkipped() {
        live.onPosted(new LiveEvents.Posted(LiveEvents.WHATSAPP, true, RAW_GROUP, Arrays.asList(in(BASE_MS, T1))));
        assertTrue(api.bodies.isEmpty());
        assertEquals(1, live.counts.summaries);
        assertEquals(0, sent.size());
    }

    @Test
    public void noChatIdSendsNothing() {
        live.onPosted(new LiveEvents.Posted(LiveEvents.WHATSAPP, false, null, Arrays.asList(in(BASE_MS, T1))));
        live.onPosted(new LiveEvents.Posted(LiveEvents.WHATSAPP, false, "", Arrays.asList(in(BASE_MS, T1))));
        assertTrue(api.bodies.isEmpty());
        assertEquals(2, live.counts.noChatId);
    }

    @Test
    public void notSharedSendsNothing() {
        live.onPosted(post(RAW_UNSHARED, in(BASE_MS, T1)));
        assertTrue(api.bodies.isEmpty());
        assertEquals(1, live.counts.notShared);
        assertEquals(0, live.pendingCount());
    }

    @Test
    public void unlinkedHiddenOneToOneSendsNothing() {
        // A hidden id the link map does not link: canonicalShared answers null — held for the backup.
        live.onPosted(post(RAW_HIDDEN, in(BASE_MS, T1)));
        assertTrue(api.bodies.isEmpty());
        assertEquals(1, live.counts.notShared);
        assertEquals(0, sent.size());
    }

    @Test
    public void otherAppIsIgnored() {
        live.onPosted(new LiveEvents.Posted("com.example.other", false, RAW_GROUP, Arrays.asList(in(BASE_MS, T1))));
        assertTrue(api.bodies.isEmpty());
        assertEquals(1, live.counts.ignoredOtherApp);
    }

    @Test
    public void gateNotOpenSendsNothing() {
        gate.open = false;
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertTrue(api.bodies.isEmpty());
        assertEquals(0, live.pendingCount());
        assertEquals(1, live.counts.ignoredGateClosed);
    }

    @Test
    public void ownMessagesAndEmptyTextAreNotSent() {
        live.onPosted(post(RAW_ONE, new LiveEvents.Line(BASE_MS, OWN, true), in(BASE_MS, null), in(BASE_MS, ""),
                in(BASE_MS + 100, T1)));
        List<Map<String, Object>> ev = allPosted();
        assertEquals(1, ev.size());
        assertEquals(T1, ev.get(0).get("text"));
        assertEquals(0L, ev.get(0).get("ordinal"));
        for (String b : api.bodies) assertFalse(b.contains(OWN));
    }

    // ---- the event ---------------------------------------------------------------------------

    @Test
    @SuppressWarnings("unchecked")
    public void timeIsFlooredToTheSecondAndTheEventHasTheLiveShape() {
        live.onPosted(post(RAW_GROUP, in(BASE_MS + 999, T1)));
        assertEquals(1, api.bodies.size());
        assertEquals(LiveEvents.EVENTS_PATH, api.paths.get(0));
        Map<String, Object> root;
        try {
            root = (Map<String, Object>) Json.parse(api.bodies.get(0));
        } catch (Json.Malformed e) {
            throw new AssertionError("body is not JSON");
        }
        assertEquals(1, root.size()); // "events" only — no cursor
        Map<String, Object> e = events(api.bodies.get(0)).get(0);
        assertEquals("message", e.get("kind"));
        assertEquals(GROUP, e.get("chat"));
        assertEquals(SECOND, e.get("time"));
        assertEquals(0L, e.get("ordinal"));
        assertEquals(T1, e.get("text"));
        assertEquals("", e.get("sender"));
        assertEquals("live", e.get("source"));
    }

    @Test
    public void twoMessagesInOneSecondTakeOrdinalsZeroAndOne() {
        live.onPosted(post(RAW_GROUP, in(BASE_MS + 10, T1), in(BASE_MS + 900, T2)));
        List<Map<String, Object>> ev = allPosted();
        assertEquals(2, ev.size());
        assertEquals(T1, ev.get(0).get("text"));
        assertEquals(0L, ev.get(0).get("ordinal"));
        assertEquals(T2, ev.get(1).get("text"));
        assertEquals(1L, ev.get(1).get("ordinal"));
        assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, 0)));
        assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, 1)));
    }

    @Test
    public void rePostSendsOnlyTheNewMessageAndTheEarlierKeepsItsKey() {
        live.onPosted(post(RAW_GROUP, in(BASE_MS + 10, T1)));
        byte[] first = sent.lookup(EventPlan.key(GROUP, SECOND, 0)).textHash;
        live.onPosted(post(RAW_GROUP, in(BASE_MS + 10, T1), in(BASE_MS + 500, T2)));
        assertEquals(2, api.bodies.size());
        List<Map<String, Object>> second = events(api.bodies.get(1));
        assertEquals(1, second.size());
        assertEquals(T2, second.get(0).get("text"));
        assertEquals(1L, second.get(0).get("ordinal"));
        assertArrayEquals(first, sent.lookup(EventPlan.key(GROUP, SECOND, 0)).textHash);
        assertEquals(1, live.counts.alreadyKnown);
    }

    @Test
    public void aKeyTheBackupRecordedIsNotResentAndAnotherTextTakesTheNextFreeOrdinal() {
        // The nightly run recorded T1 at ordinal 0 (with a sender) and some other text at ordinal 1.
        sent.record(EventPlan.key(GROUP, SECOND, 0), sent.textHash(T1), sent.senderHash("member-a@test.invalid"), SECOND);
        sent.record(EventPlan.key(GROUP, SECOND, 1), sent.textHash(T3), sent.senderHash(""), SECOND);
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), in(BASE_MS + 1, T2)));
        List<Map<String, Object>> ev = allPosted();
        assertEquals(1, ev.size());
        assertEquals(T2, ev.get(0).get("text"));
        assertEquals(2L, ev.get(0).get("ordinal"));
    }

    @Test
    public void theSameTextTwiceInOneSecondIsTwoMessagesAndStaysTwoOnRePost() {
        live.onPosted(post(RAW_ONE, in(BASE_MS, T1), in(BASE_MS + 1, T1)));
        assertEquals(2, allPosted().size());
        live.onPosted(post(RAW_ONE, in(BASE_MS, T1), in(BASE_MS + 1, T1), in(BASE_MS + 2, T1)));
        List<Map<String, Object>> ev = events(api.bodies.get(api.bodies.size() - 1));
        assertEquals(1, ev.size());
        assertEquals(2L, ev.get(0).get("ordinal"));
    }

    @Test
    public void aLineReShownAfterTheNightlyUpdateReplacedItsHashIsNotSentAgain() {
        // F7: posted live and accepted; the nightly run then sent an update with the backup's text
        // and sender, which replaced the stored hash. Ten hours later the notification re-shows it.
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertEquals(1, api.bodies.size());
        sent.record(EventPlan.key(GROUP, SECOND, 0), sent.textHash(T3), sent.senderHash("member-b@test.invalid"), SECOND);
        now += 10 * 3600 * 1000L;
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertEquals("nothing new sent", 1, api.bodies.size());
        assertEquals(1, live.counts.alreadyKnown);
        // Past the memo's 72 h it is the sent-hash list alone that decides.
        assertTrue(LiveEvents.MEMO_MS >= 72 * 3600 * 1000L);
    }

    @Test
    public void theMemoIsBoundedOldestSettledFirst() {
        shares.accepted = false; // nothing posts: every line is placed, then given up
        int n = LiveEvents.MEMO_MAX + 25;
        LiveEvents.Line[] lines = new LiveEvents.Line[n];
        for (int i = 0; i < n; i++) lines[i] = in(BASE_MS + i * 1000L, T1);
        live.onPosted(post(RAW_GROUP, lines));
        now += LiveEvents.RETRY_WINDOW_MS;
        live.tick();
        assertEquals(0, live.pendingCount());
        live.tick();
        assertEquals(LiveEvents.MEMO_MAX, live.memoSize(GROUP));
        assertTrue(api.bodies.isEmpty());
    }

    @Test
    public void acceptedIsRecordedWithTheCutTextHashAndAnEmptySenderHash() {
        StringBuilder b = new StringBuilder();
        while (b.length() < EventPlan.MAX_TEXT_CODE_POINTS + 50) b.append("planted-long-text-");
        String longText = b.toString();
        String cut = EventPlan.cut(longText);
        live.onPosted(post(RAW_GROUP, in(BASE_MS, longText)));
        assertEquals(cut, allPosted().get(0).get("text"));
        SentHashes.Entry e = sent.lookup(EventPlan.key(GROUP, SECOND, 0));
        assertNotNull(e);
        assertArrayEquals(sent.textHash(cut), e.textHash);
        assertEquals(0, e.senderHash.length);
        assertEquals(SECOND, e.second);
        assertEquals(1, live.counts.recorded);
    }

    // ---- what the VM did with it --------------------------------------------------------------

    @Test
    public void droppedNotSharedRecordsNothing() {
        api.scripted.add(ok("{\"accepted\": 0, \"duplicates\": 0, \"updated\": 0, \"dropped_not_shared\": 2,"
                + " \"held_back\": 0, \"rejected\": [], \"action_needed\": false}"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), in(BASE_MS + 1, T2)));
        assertEquals(1, api.bodies.size());
        assertEquals(0, sent.size());
        assertEquals(0, live.pendingCount());
        assertEquals(2, live.counts.droppedNotShared);
        // A re-post does not loop: left to the backup.
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), in(BASE_MS + 1, T2)));
        assertEquals(1, api.bodies.size());
    }

    @Test
    public void rejectedRecordsNothingForThatEventOnly() {
        api.scripted.add(ok("{\"accepted\": 1, \"duplicates\": 0, \"updated\": 0, \"dropped_not_shared\": 0,"
                + " \"held_back\": 0, \"rejected\": [{\"index\": 0, \"reason\": \"bad ordinal\"}], \"action_needed\": false}"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), in(BASE_MS + 1, T2)));
        assertNull(sent.lookup(EventPlan.key(GROUP, SECOND, 0)));
        assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, 1)));
        assertEquals(1, live.counts.rejected);
        assertEquals(0, live.pendingCount());
    }

    @Test
    public void notPostedWhileTheShareListIsNotAccepted() {
        shares.accepted = false;
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertTrue(api.bodies.isEmpty());
        assertEquals(1, live.pendingCount());
        now += LiveEvents.FIRST_RETRY_GAP_MS;
        live.tick();
        assertTrue(api.bodies.isEmpty());
        // Accepted inside the window: it goes then.
        shares.accepted = true;
        now += LiveEvents.MAX_RETRY_GAP_MS;
        live.tick();
        assertEquals(1, api.bodies.size());
        assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, 0)));
    }

    @Test
    public void neverAcceptedWithinTheWindowIsLeftToTheBackup() {
        shares.accepted = false;
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        now += LiveEvents.RETRY_WINDOW_MS;
        live.tick();
        shares.accepted = true;
        now += LiveEvents.MAX_RETRY_GAP_MS;
        live.tick();
        assertTrue(api.bodies.isEmpty());
        assertEquals(0, live.pendingCount());
        assertEquals(0, sent.size());
    }

    @Test
    public void failureIsRetriedWithinTenMinutesThenDropped() {
        for (int i = 0; i < 50; i++) api.scripted.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "SocketTimeoutException"));
        long arrived = now;
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertEquals(1, api.bodies.size());
        assertEquals(1, live.pendingCount());
        // Not due yet: no second attempt.
        live.tick();
        assertEquals(1, api.bodies.size());
        // Retried, more than once, inside the window.
        while (now < arrived + LiveEvents.RETRY_WINDOW_MS - 1000) {
            now += 1000;
            live.tick();
        }
        int attempts = api.bodies.size();
        assertTrue("retried: " + attempts, attempts >= 3);
        assertEquals(1, live.pendingCount());
        // Past the window: given up, never posted again.
        now = arrived + LiveEvents.RETRY_WINDOW_MS;
        live.tick();
        assertEquals(0, live.pendingCount());
        now += LiveEvents.MAX_RETRY_GAP_MS * 3;
        live.tick();
        assertEquals(attempts, api.bodies.size());
        assertEquals(0, sent.size());
        assertEquals(1, live.counts.gaveUp);
    }

    @Test
    public void aFailureThenSuccessRecordsOnce() {
        api.scripted.add(new DeviceApi.Result(503, "", ""));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertEquals(0, sent.size());
        now += LiveEvents.FIRST_RETRY_GAP_MS;
        live.tick();
        assertEquals(2, api.bodies.size());
        assertEquals(api.bodies.get(0), api.bodies.get(1));
        assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, 0)));
    }

    @Test
    public void aRePostWhileStillPendingDoesNotSendTwiceOrMoveTheOrdinal() {
        api.scripted.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), in(BASE_MS + 1, T2)));
        // The re-post placed T2 at ordinal 1, kept T1 at 0, and the pending T1 was not due yet.
        assertEquals(2, api.bodies.size());
        List<Map<String, Object>> ev = events(api.bodies.get(1));
        assertEquals(1, ev.size());
        assertEquals(T2, ev.get(0).get("text"));
        assertEquals(1L, ev.get(0).get("ordinal"));
        now += LiveEvents.FIRST_RETRY_GAP_MS;
        live.tick();
        List<Map<String, Object>> retry = events(api.bodies.get(2));
        assertEquals(1, retry.size());
        assertEquals(T1, retry.get(0).get("text"));
        assertEquals(0L, retry.get(0).get("ordinal"));
    }

    @Test
    public void aClosedGateOnReplyDropsEverythingPending() {
        api.scripted.add(new DeviceApi.Result(403, "{\"detail\": \"channel_off\"}", "channel_off"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertFalse(gate.open);
        assertEquals(0, live.pendingCount());
        assertEquals(0, sent.size());
        assertEquals(Integer.valueOf(403), gate.observed.get(0));
    }

    @Test
    public void aClientErrorIsNotRetried() {
        api.scripted.add(new DeviceApi.Result(413, "", ""));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        now += LiveEvents.MAX_RETRY_GAP_MS;
        live.tick();
        assertEquals(1, api.bodies.size());
        assertEquals(0, live.pendingCount());
    }

    @Test
    public void anUnTickInsideTheWindowDropsThePending() {
        api.scripted.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        shares.kinds.remove(GROUP);
        now += LiveEvents.FIRST_RETRY_GAP_MS;
        live.tick();
        assertEquals(1, api.bodies.size());
        assertEquals(0, live.pendingCount());
    }

    @Test
    public void theListenerDoesNotPrune() {
        long old = SECOND - 30L * 24 * 3600;
        sent.record(EventPlan.key(ONE, old, 0), sent.textHash(T3), sent.senderHash(""), old);
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertNotNull(sent.lookup(EventPlan.key(ONE, old, 0)));
    }

    @Test
    public void replyParsing() {
        assertNull(LiveEvents.Reply.parse(""));
        assertNull(LiveEvents.Reply.parse("{\"accepted\": 1}"));
        assertNull(LiveEvents.Reply.parse("{\"dropped_not_shared\": 0, \"rejected\": [{\"reason\": \"x\"}]}"));
        LiveEvents.Reply r = LiveEvents.Reply.parse("{\"dropped_not_shared\": 0, \"rejected\": [{\"index\": 3, \"reason\": \"x\"}]}");
        assertEquals(0, r.droppedNotShared);
        assertTrue(r.rejected.contains(3));
        assertTrue(LiveEvents.retryable(DeviceApi.NETWORK));
        assertTrue(LiveEvents.retryable(502));
        assertFalse(LiveEvents.retryable(DeviceApi.NOT_HTTPS));
        assertFalse(LiveEvents.retryable(DeviceApi.UNPAIRED));
        assertFalse(LiveEvents.retryable(400));
    }

    @Test
    public void anUnparseableReplyIsRetriedNotRecorded() {
        api.scripted.add(ok("not json"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertEquals(0, sent.size());
        assertEquals(1, live.pendingCount());
    }

    @Test
    public void afterTurnOffNothingIsSentAndNoFileComesBack() {
        sent.deleteAll();
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1)));
        assertTrue(api.bodies.isEmpty());
        assertEquals(0, live.pendingCount());
        File[] left = stateDir.listFiles();
        assertTrue(left == null || left.length == 0);
    }

    @Test
    public void oneChatNeverHasTwoPostsInFlight() throws Exception {
        final java.util.concurrent.atomic.AtomicInteger inFlight = new java.util.concurrent.atomic.AtomicInteger();
        final java.util.concurrent.atomic.AtomicInteger maxInFlight = new java.util.concurrent.atomic.AtomicInteger();
        final List<String> bodies = java.util.Collections.synchronizedList(new ArrayList<String>());
        DeviceApi slow = new DeviceApi() {
            @Override
            public DeviceApi.Result get(String path) {
                throw new AssertionError();
            }

            @Override
            public DeviceApi.Result post(String path, String body, int timeout) {
                int n = inFlight.incrementAndGet();
                maxInFlight.accumulateAndGet(n, Math::max);
                try {
                    Thread.sleep(20);
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
                bodies.add(body);
                inFlight.decrementAndGet();
                return FakeApi.acceptedAll(body);
            }
        };
        java.util.concurrent.ExecutorService pool = java.util.concurrent.Executors.newFixedThreadPool(4);
        try {
            LiveEvents threaded = new LiveEvents(slow, () -> now, shares, gate, sent, pool);
            List<LiveEvents.Line> lines = new ArrayList<>();
            for (int i = 0; i < 6; i++) {
                lines.add(in(BASE_MS + i, "planted-thread-text-" + i));
                threaded.onPosted(new LiveEvents.Posted(LiveEvents.WHATSAPP, false, RAW_GROUP, new ArrayList<>(lines)));
            }
            long deadline = System.currentTimeMillis() + 10_000;
            while (sent.size() < 6 && System.currentTimeMillis() < deadline) Thread.sleep(10);
            assertEquals(6, sent.size());
            assertEquals(1, maxInFlight.get());
            for (int k = 0; k < 6; k++) assertNotNull(sent.lookup(EventPlan.key(GROUP, SECOND, k)));
            int events = 0;
            for (String b : bodies) events += countEvents(b);
            assertEquals(6, events);
        } finally {
            pool.shutdownNow();
        }
    }

    // ---- no text anywhere but the post ---------------------------------------------------------

    @Test
    public void plantedTextsNeverAppearOnDiskInToStringOrInAnyLog() throws IOException {
        String[] planted = {T1, T2, T3, OWN};
        // Every path: accepted, failed-then-retried, rejected, dropped, own, summary, unshared.
        live.onPosted(post(RAW_GROUP, in(BASE_MS, T1), new LiveEvents.Line(BASE_MS, OWN, true)));
        api.scripted.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        LiveEvents.Posted p2 = post(RAW_ONE, in(BASE_MS + 1000, T2));
        live.onPosted(p2);
        String mid = live.toString() + live.counts + p2 + p2.lines.get(0);
        api.scripted.add(ok("{\"accepted\": 0, \"duplicates\": 0, \"updated\": 0, \"dropped_not_shared\": 0,"
                + " \"held_back\": 0, \"rejected\": [{\"index\": 0, \"reason\": \"x\"}], \"action_needed\": false}"));
        live.onPosted(post(RAW_GROUP, in(BASE_MS + 2000, T3)));
        live.onPosted(new LiveEvents.Posted(LiveEvents.WHATSAPP, true, RAW_GROUP, Arrays.asList(in(BASE_MS, T3))));
        live.onPosted(post(RAW_UNSHARED, in(BASE_MS, T3)));
        now += LiveEvents.FIRST_RETRY_GAP_MS;
        live.tick();

        List<String> texts = new ArrayList<>();
        texts.add(mid);
        texts.add(live.toString());
        texts.add(live.counts.toString());
        texts.add(sent.toString());
        texts.add(captured.toString("UTF-8"));
        File[] files = stateDir.listFiles();
        assertNotNull(files);
        assertTrue(files.length > 0);
        for (File f : files) texts.add(new String(Files.readAllBytes(f.toPath()), StandardCharsets.UTF_8));
        for (String t : texts) {
            for (String p : planted) assertFalse("planted text leaked", t.contains(p));
        }
        assertTrue("the run did post", live.counts.recorded >= 2);
    }
}
