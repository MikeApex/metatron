package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The skip / update / message / reply-marker decision (build plan § 3.4). Every chat id, sender id
 * and text is made up; the texts are checked never to appear in any toString().
 */
public class EventPlanTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final String GROUP = "made-up-group@g.test";
    private static final String ONE = "made-up-person@p.test";
    private static final String UNSHARED = "made-up-unshared@p.test";
    private static final String MEMBER = "made-up-member@p.test";
    private static final String T1 = "planted-text-amber-heron-301";
    private static final String T2 = "planted-text-cobalt-finch-302";
    private static final long S = 1_700_000_000L;
    /** A reply rule for the test: any from-me row with text is a reply. The real one is W1's ReplyRule. */
    private static final Predicate<WaMessage> REPLY = m -> m.fromMe && m.text != null;

    private SentHashes sent;
    private Map<String, String> kinds;
    private final List<String> planted = new ArrayList<>(Arrays.asList(T1, T2, "amber-heron", "cobalt-finch"));

    @Before
    public void setUp() {
        SentHashes.forgetInstancesForTest();
        sent = SentHashes.open(new File(tmp.getRoot(), "wa_state"));
        kinds = new HashMap<>();
        kinds.put(GROUP, EventPlan.GROUP);
        kinds.put(ONE, EventPlan.ONE_TO_ONE);
    }

    @After
    public void tearDown() {
        SentHashes.forgetInstancesForTest();
    }

    private static WaMessage in(String chat, long second, int ordinal, String sender, String text) {
        return new WaMessage(chat, "k" + second + "-" + ordinal, false, second * 1000 + 123, sender, text, second).withOrdinal(ordinal);
    }

    private static WaMessage mine(String chat, long second, int ordinal, String text) {
        return new WaMessage(chat, "m" + second + "-" + ordinal, true, second * 1000, null, text, second).withOrdinal(ordinal);
    }

    private EventPlan build(WaMessage... ms) {
        EventPlan p = EventPlan.build(Arrays.asList(ms), sent, kinds, REPLY);
        assertNoContent(p.toString());
        for (EventPlan.Event e : p.events) assertNoContent(e.toString());
        return p;
    }

    private void assertNoContent(String s) {
        for (String t : planted) assertFalse("content in toString", s.contains(t));
        assertFalse(s.contains(GROUP) || s.contains(ONE) || s.contains(MEMBER));
    }

    /** What a live post leaves in the list: the live path sends sender "" (plan § 3.10). */
    private void recordLive(String chat, long second, int ordinal, String text) {
        sent.record(EventPlan.key(chat, second, ordinal), sent.textHash(text), sent.senderHash(""), second);
    }

    @Test
    public void newReceivedTextIsAMessage() throws Exception {
        EventPlan p = build(in(ONE, S, 0, null, T1), in(GROUP, S + 1, 0, MEMBER, T2));
        assertEquals(2, p.messages);
        assertEquals(0, p.updates + p.skippedUnchanged + p.replyMarkers + p.receivedNoText + p.notShared);
        EventPlan.Event one = p.events.get(0), grp = p.events.get(1);
        assertEquals(EventPlan.MESSAGE, one.kind);
        assertEquals(ONE + "|" + S + "|0", one.key);
        assertEquals("", one.sender);                // a one-to-one never carries a sender
        assertEquals(MEMBER, grp.sender);            // a group message from the backup carries its sender
        @SuppressWarnings("unchecked")
        Map<String, Object> j = (Map<String, Object>) Json.parse(grp.toJson());
        assertEquals(Arrays.asList("kind", "chat", "time", "ordinal", "text", "sender", "source"), new ArrayList<>(j.keySet()));
        assertEquals("message", j.get("kind"));
        assertEquals(GROUP, j.get("chat"));
        assertEquals(S + 1, j.get("time"));          // whole seconds, never ms
        assertEquals(0L, j.get("ordinal"));
        assertEquals(T2, j.get("text"));
        assertEquals(MEMBER, j.get("sender"));
        assertEquals("backup", j.get("source"));
        assertEquals(0, sent.size());                // build never writes the list
    }

    @Test
    public void unchangedIsSkippedAndChangedIsAnUpdate() {
        EventPlan first = build(in(ONE, S, 0, null, T1), in(GROUP, S, 0, MEMBER, T2));
        sent.recordAll(first.events);
        EventPlan again = build(in(ONE, S, 0, null, T1), in(GROUP, S, 0, MEMBER, T2));
        assertEquals(0, again.events.size());
        assertEquals(2, again.skippedUnchanged);
        // An edit: same key, new text → update.
        String edited = "planted-text-edited-303";
        planted.add(edited);
        EventPlan edit = build(in(ONE, S, 0, null, edited), in(GROUP, S, 0, MEMBER, T2));
        assertEquals(1, edit.updates);
        assertEquals(1, edit.skippedUnchanged);
        assertEquals(EventPlan.UPDATE, edit.events.get(0).kind);
        assertEquals(edited, edit.events.get(0).text);
        // A different sender on the same key and text → update too.
        EventPlan other = build(in(GROUP, S, 0, "made-up-other@p.test", T2));
        assertEquals(1, other.updates);
    }

    @Test
    public void aLiveGroupCopyWithoutSenderIsSentAgainAsAnUpdate() {
        recordLive(GROUP, S, 0, T1);                 // arrived live, sender ""
        EventPlan p = build(in(GROUP, S, 0, MEMBER, T1));
        assertEquals("review 2: the backup supplies the sender", 1, p.updates);
        EventPlan.Event e = p.events.get(0);
        assertEquals(EventPlan.UPDATE, e.kind);
        assertEquals(MEMBER, e.sender);
        sent.recordAll(p.events);
        assertEquals(1, build(in(GROUP, S, 0, MEMBER, T1)).skippedUnchanged);
        // A group row whose sender the backup lacks matches the live copy.
        recordLive(GROUP, S + 5, 0, T2);
        assertEquals(1, build(in(GROUP, S + 5, 0, null, T2)).skippedUnchanged);
    }

    @Test
    public void aOneToOneRecordedLiveIsSkipped() {
        recordLive(ONE, S, 0, T1);
        // Even if a sender id were present on the row, a one-to-one goes with "" on both paths.
        EventPlan p = build(in(ONE, S, 0, MEMBER, T1));
        assertEquals(0, p.events.size());
        assertEquals(1, p.skippedUnchanged);
    }

    @Test
    public void aLongTextIsCutAt4000CodePointsWithoutSplittingAPair() {
        String emoji = new String(Character.toChars(0x1F642));
        StringBuilder b = new StringBuilder("planted-long-");
        while (b.codePointCount(0, b.length()) < 3999) b.append('x');
        b.append(emoji).append(emoji).append("planted-tail-beyond-the-cut");   // code point 4000 is a pair
        String longText = b.toString();
        planted.add("planted-tail-beyond-the-cut");
        planted.add("planted-long-");
        assertEquals(4000, EventPlan.cut(longText).codePointCount(0, EventPlan.cut(longText).length()));
        assertTrue(EventPlan.cut(longText).endsWith(emoji));
        assertFalse(Character.isHighSurrogate(EventPlan.cut(longText).charAt(EventPlan.cut(longText).length() - 1)));

        EventPlan p = build(in(ONE, S, 0, null, longText));
        EventPlan.Event e = p.events.get(0);
        assertEquals(4000, e.text.codePointCount(0, e.text.length()));
        assertEquals(4001, e.text.length());         // 3,999 single chars and one pair
        assertTrue(e.toJson().contains(emoji));
        assertFalse(e.toJson().contains("planted-tail"));
        sent.recordAll(p.events);
        EventPlan next = build(in(ONE, S, 0, null, longText));
        assertEquals("the cut text is what was hashed: not re-sent nightly", 1, next.skippedUnchanged);
        assertEquals(0, next.events.size());
        // At or under the limit, untouched.
        assertEquals("short", EventPlan.cut("short"));
        assertEquals(null, EventPlan.cut(null));
    }

    @Test
    public void receivedWithoutTextIsSkipped() {
        // An empty text is no text too: the VM would otherwise build a fact from nothing.
        EventPlan p = build(in(ONE, S, 0, null, null), in(GROUP, S, 0, MEMBER, null), in(ONE, S + 1, 0, null, ""));
        assertEquals(0, p.events.size());
        assertEquals(3, p.receivedNoText);
    }

    @Test
    public void aReplyIsMarkedOncePerKeyAndCarriesNoText() throws Exception {
        String reply = "planted-reply-text-304";
        planted.add(reply);
        EventPlan p = build(mine(ONE, S, 0, reply), mine(ONE, S + 1, 0, null));   // the second is not a reply
        assertEquals(1, p.replyMarkers);
        assertEquals(1, p.events.size());
        EventPlan.Event e = p.events.get(0);
        assertEquals(EventPlan.REPLY_MARKER, e.kind);
        assertEquals("r|" + ONE + "|" + S + "|0", e.key);
        assertEquals(0, e.senderHash.length);
        assertTrue(Arrays.equals(sent.textHash(""), e.textHash));
        String json = e.toJson();
        assertFalse(json.contains(reply));
        @SuppressWarnings("unchecked")
        Map<String, Object> j = (Map<String, Object>) Json.parse(json);
        assertEquals(Arrays.asList("kind", "chat", "time", "ordinal", "source"), new ArrayList<>(j.keySet()));
        sent.recordAll(p.events);
        assertEquals(0, build(mine(ONE, S, 0, reply)).events.size());
        // A received row with the same chat, second and ordinal is a different key.
        assertEquals(1, build(in(ONE, S, 0, null, T1)).messages);
    }

    @Test
    public void aChatNotSharedSendsNothing() {
        EventPlan p = build(in(UNSHARED, S, 0, null, T1), mine(UNSHARED, S, 0, T2));
        assertEquals(0, p.events.size());
        assertEquals(2, p.notShared);
    }

    @Test
    public void eventsGoOldestFirst() {
        EventPlan p = build(
                in(ONE, S + 2, 0, null, T1),
                in(GROUP, S + 1, 1, MEMBER, T1),
                in(ONE, S + 1, 0, null, T2),
                in(GROUP, S + 1, 0, MEMBER, T2),
                mine(GROUP, S, 0, T1));
        List<String> keys = new ArrayList<>();
        for (EventPlan.Event e : p.events) keys.add(e.key);
        assertEquals(Arrays.asList(
                "r|" + GROUP + "|" + S + "|0",
                GROUP + "|" + (S + 1) + "|0",
                GROUP + "|" + (S + 1) + "|1",
                ONE + "|" + (S + 1) + "|0",
                ONE + "|" + (S + 2) + "|0"), keys);
    }

    @Test
    public void sameSecondGroupsCountsReceivedRowsInSharedChats() {
        List<WaMessage> ms = Arrays.asList(
                in(GROUP, S, 0, MEMBER, T1), in(GROUP, S, 1, MEMBER, null),      // a pair: counts, text or not
                in(GROUP, S + 1, 0, MEMBER, T1),                                  // alone
                in(ONE, S, 0, null, T1), mine(ONE, S, 0, T2),                     // from-me does not count
                in(ONE, S + 3, 0, null, T1), in(ONE, S + 3, 1, null, T2), in(ONE, S + 3, 2, null, T2), // a triple: one group
                in(UNSHARED, S, 0, null, T1), in(UNSHARED, S, 1, null, T2));      // not shared
        assertEquals(2, EventPlan.sameSecondGroups(ms, new HashSet<>(kinds.keySet())));
        assertEquals(0, EventPlan.sameSecondGroups(ms, new HashSet<String>()));
    }
}
