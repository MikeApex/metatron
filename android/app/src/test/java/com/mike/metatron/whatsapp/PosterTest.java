package com.mike.metatron.whatsapp;

import static com.mike.metatron.whatsapp.NightlyFakes.accepted;
import static com.mike.metatron.whatsapp.NightlyFakes.dropped;
import static com.mike.metatron.whatsapp.NightlyFakes.ok;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.nio.charset.StandardCharsets;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Deque;
import java.util.List;
import java.util.Map;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** Posting in batches (plan § 3.2; review 1, review 3, verify new 4). Every id and text is made up. */
public class PosterTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final String CHAT = "made-up-chat@s.test";
    private static final String TEXT = "planted-text-ochre-plover-601";
    private static final long S = 1_700_000_000L;

    private final List<String> log = new ArrayList<>();
    private final Deque<DeviceApi.Result> replies = new ArrayDeque<>();
    private NightlyFakes.FakeApi api;
    private NightlyFakes.PosterHost host;
    private SentHashes sent;

    @Before
    public void setUp() throws Exception {
        SentHashes.forgetInstancesForTest();
        sent = SentHashes.open(tmp.newFolder("state"));
        api = new NightlyFakes.FakeApi(log, c -> {
            DeviceApi.Result r = replies.poll();
            if (r != null) return r;
            int n = ((List<?>) c.json().get("events")).size();
            return accepted(n);
        });
        host = new NightlyFakes.PosterHost(api);
    }

    private List<EventPlan.Event> events(int n, int textChars) {
        List<EventPlan.Event> out = new ArrayList<>();
        StringBuilder t = new StringBuilder(TEXT);
        while (t.length() < textChars) t.append('x');
        for (int i = 0; i < n; i++) {
            byte[] th = sent.textHash(t.toString() + i);
            out.add(new EventPlan.Event(EventPlan.MESSAGE, CHAT, S + i, 0, t.toString(), "",
                    EventPlan.key(CHAT, S + i, 0), th, new byte[0]));
        }
        return out;
    }

    private static int eventsIn(NightlyFakes.Call c) {
        return ((List<?>) c.json().get("events")).size();
    }

    private static Long cursorOf(NightlyFakes.Call c) {
        Object v = c.json().get("cursor");
        return v == null ? null : (Long) v;
    }

    private List<NightlyFakes.Call> posts() {
        return api.posts(Poster.PATH);
    }

    @Test
    public void batchesHoldAtMostOneHundredEventsOldestFirstWithA120SecondTimeout() {
        List<EventPlan.Event> ev = events(250, 10);
        Poster.Outcome o = Poster.post(host, sent, ev, null);
        assertEquals("", o.error);
        assertEquals(3, posts().size());
        assertEquals(Arrays.asList(100, 100, 50), Arrays.asList(eventsIn(posts().get(0)), eventsIn(posts().get(1)), eventsIn(posts().get(2))));
        for (NightlyFakes.Call c : posts()) assertEquals(120_000, c.timeout);
        assertEquals(250, sent.size());
        assertEquals(250, o.messages);
        // the first event of the run is the oldest
        assertEquals(S, (long) (Long) ((Map<?, ?>) ((List<?>) posts().get(0).json().get("events")).get(0)).get("time"));
    }

    @Test
    public void batchesStayUnder256KiB() {
        List<EventPlan.Event> ev = events(150, 4000);
        Poster.Outcome o = Poster.post(host, sent, ev, null);
        assertEquals("", o.error);
        int total = 0;
        for (NightlyFakes.Call c : posts()) {
            assertTrue(c.body.getBytes(StandardCharsets.UTF_8).length <= 256 * 1024);
            assertTrue(eventsIn(c) < 100);
            total += eventsIn(c);
        }
        assertEquals(150, total);
        assertEquals(150, sent.size());
    }

    @Test
    public void eachAcceptedBatchCarriesItsNewestSecondAsTheCursor() {
        Poster.Outcome o = Poster.post(host, sent, events(250, 10), null);
        assertEquals(Long.valueOf(S + 99), cursorOf(posts().get(0)));
        assertEquals(Long.valueOf(S + 199), cursorOf(posts().get(1)));
        assertEquals(Long.valueOf(S + 249), cursorOf(posts().get(2)));
        assertEquals(S + 249, o.cursorSent);
    }

    @Test
    public void theCursorNeverMovesBehindTheOneTheRunStartedFrom() {
        Poster.Outcome o = Poster.post(host, sent, events(150, 10), S + 120);
        assertEquals(Long.valueOf(S + 120), cursorOf(posts().get(0))); // newest in batch is S + 99
        assertEquals(Long.valueOf(S + 149), cursorOf(posts().get(1)));
        assertEquals(S + 149, o.cursorSent);
    }

    @Test
    public void a413HalvesTheBatchRetriesOnceAndWithholdsTheCursorFromThenOn() {
        replies.add(new DeviceApi.Result(413, "", ""));
        Poster.Outcome o = Poster.post(host, sent, events(150, 10), null);
        assertEquals("", o.error);
        List<NightlyFakes.Call> p = posts();
        assertEquals(100, eventsIn(p.get(0)));
        assertEquals(50, eventsIn(p.get(1)));
        for (int i = 1; i < p.size(); i++) {
            assertTrue(eventsIn(p.get(i)) <= 50);
            assertNull("no cursor after a post that was not accepted", cursorOf(p.get(i)));
        }
        assertEquals(150, sent.size());
        assertEquals(0, o.cursorSent);
    }

    @Test
    public void aTimeoutHalvesTheBatchToo() {
        replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "SocketTimeoutException"));
        Poster.Outcome o = Poster.post(host, sent, events(100, 10), null);
        assertEquals("", o.error);
        assertEquals(50, eventsIn(posts().get(1)));
        assertEquals(100, sent.size());
    }

    @Test
    public void aSecondFailureInARowEndsTheRunWithNothingRecorded() {
        replies.add(new DeviceApi.Result(413, "", ""));
        replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "SocketTimeoutException"));
        Poster.Outcome o = Poster.post(host, sent, events(100, 10), null);
        assertEquals(RunReport.POST_FAILED, o.error);
        assertEquals(2, posts().size());
        assertEquals(0, sent.size());
    }

    @Test
    public void aServerErrorRetriesOnceAtTheSameSize() {
        replies.add(new DeviceApi.Result(502, "", ""));
        Poster.Outcome o = Poster.post(host, sent, events(80, 10), null);
        assertEquals("", o.error);
        assertEquals(80, eventsIn(posts().get(1)));
        assertEquals(80, sent.size());
    }

    @Test
    public void aDropRecordsNothingRepostsTheShareListAndRetriesOnce() {
        replies.add(dropped(3));
        Poster.Outcome o = Poster.post(host, sent, events(10, 10), null);
        assertEquals("", o.error);
        assertEquals(1, host.reposts);
        assertEquals(Arrays.asList("POST " + Poster.PATH, "repost", "POST " + Poster.PATH), log);
        assertEquals(10, sent.size());
        assertEquals(3, o.droppedNotShared);
        assertFalse(host.shareOutOfStep);
    }

    @Test
    public void aRepeatedDropEndsTheRunAsOutOfStepWithNothingRecorded() {
        replies.add(dropped(3));
        replies.add(dropped(2));
        Poster.Outcome o = Poster.post(host, sent, events(10, 10), null);
        assertEquals(RunReport.SHARE_OUT_OF_STEP, o.error);
        assertTrue(host.shareOutOfStep);
        assertEquals(0, sent.size());
        assertEquals(2, posts().size());
    }

    @Test
    public void aRepostThatIsNotAcceptedEndsTheRunWithoutRetrying() {
        replies.add(dropped(1));
        host.repost = ShareList.Post.FAILED;
        Poster.Outcome o = Poster.post(host, sent, events(10, 10), null);
        assertEquals(RunReport.SHARE_OUT_OF_STEP, o.error);
        assertEquals(1, posts().size());
        assertEquals(0, sent.size());
    }

    @Test
    public void aRejectedEventIsRecordedAsSentAndCountedNeverRetried() {
        replies.add(ok("{\"accepted\":2,\"dropped_not_shared\":0,\"rejected\":[{\"index\":1,\"reason\":\"made-up\"}]}"));
        List<EventPlan.Event> ev = events(3, 10);
        Poster.Outcome o = Poster.post(host, sent, ev, null);
        assertEquals("", o.error);
        assertEquals(1, posts().size());
        assertEquals(1, o.rejected);
        assertEquals(2, o.messages);
        assertNotNull(sent.lookup(ev.get(1).key));
        assertEquals(3, sent.size());
    }

    @Test
    public void a401Or403EndsTheRunAtOnce() {
        for (int status : new int[] {401, 403}) {
            replies.clear();
            log.clear();
            api.calls.clear();
            replies.add(new DeviceApi.Result(status, "", status == 403 ? "consented_off" : ""));
            Poster.Outcome o = Poster.post(host, sent, events(150, 10), null);
            assertTrue(o.authEnded);
            assertEquals(1, posts().size());
            assertEquals(0, sent.size());
        }
    }

    @Test
    public void everyReplyGoesThroughTheGate() {
        replies.add(new DeviceApi.Result(403, "", "consented_off"));
        Poster.post(host, sent, events(5, 10), null);
        assertEquals(Gate.State.CONSENTED_OFF, host.state);
    }

    @Test
    public void aCancelBetweenBatchesStopsAfterTheBatchInFlight() {
        final int[] seen = {0};
        api.handler = c -> {
            seen[0]++;
            return accepted(eventsIn(c));
        };
        host.cancelled = () -> seen[0] >= 1;
        Poster.Outcome o = Poster.post(host, sent, events(250, 10), null);
        assertTrue(o.stopped);
        assertEquals(1, seen[0]);
        assertEquals(100, sent.size());
    }

    @Test
    public void noEventsMeansNoPost() {
        Poster.Outcome o = Poster.post(host, sent, new ArrayList<EventPlan.Event>(), 5L);
        assertEquals("", o.error);
        assertEquals(0, api.calls.size());
    }

    @Test
    public void theOutcomeCarriesNoContent() {
        Poster.Outcome o = Poster.post(host, sent, events(3, 10), null);
        assertFalse(o.toString().contains(TEXT));
        assertFalse(o.toString().contains(CHAT));
    }
}
