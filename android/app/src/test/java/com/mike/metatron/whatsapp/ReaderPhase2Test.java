package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The Phase 2 reader additions (plan § 2 items 1–7): message type and content presence, the reply
 * rule, the schema names the read now requires, the chat list and its fold, the night's new links
 * and the group senders. Plain Java; every id, name and text is made up, and planted texts are
 * checked never to appear in any toString.
 */
public class ReaderPhase2Test {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    static final String ALICE = IncrementReaderTest.ALICE, ALICE_LID = IncrementReaderTest.ALICE_LID,
            GROUP = IncrementReaderTest.GROUP, BOB_LID = IncrementReaderTest.BOB_LID,
            BOB = "447700900222@s.whatsapp.net", GROUP2 = "120363000000000002@g.us",
            CAROL_LID = "444444444444444@lid", CAROL = "447700900444@s.whatsapp.net";
    static final long T = IncrementReaderTest.T;
    /** Planted values that must never reach a toString. */
    static final String[] PLANTED = {"PLANTED-TEXT", "PLANTED-SUBJECT", "PLANTED-NAME", "447700900", "@lid", "@g.us",
            "whatsapp.net"};

    // ---- 1. message type and content presence ---------------------------------------------------

    @Test public void theRowMappingCarriesTypeAndLeavesContentUnknown() {
        int[] noKey = {0}, noChat = {0};
        WaMessage m = FullBackupMessages.row("KEYT1", 10, false, T * 1000 + 5, GROUP, BOB_LID, "PLANTED-TEXT one", 3, noKey, noChat);
        assertEquals(3, m.type);
        assertNull("a full backup does not say", m.hasContent);
        assertEquals("group, not from me: sender kept", BOB_LID, m.senderJid);
        assertEquals(T * 1000 + 5, m.timeMs);
        WaMessage unknown = FullBackupMessages.row("KEYT2", 11, true, T * 1000, GROUP, BOB_LID, null, null, noKey, noChat);
        assertEquals("a null type is unknown", -1, unknown.type);
        assertNull("from me: no sender", unknown.senderJid);
        assertNull("one-to-one: no sender", FullBackupMessages.row("KEYT3", 12, false, T * 1000, ALICE, BOB_LID, null, 0,
                noKey, noChat).senderJid);
        assertNull(FullBackupMessages.row(null, 13, false, T * 1000, ALICE, null, "x", 0, noKey, noChat));
        assertNull(FullBackupMessages.row("KEYT4", 14, false, T * 1000, null, null, "x", 0, noKey, noChat));
        assertEquals(1, noKey[0]);
        assertEquals(1, noChat[0]);
        assertClean(m.toString());
    }

    @Test public void theSevenArgumentConstructorStillMeansUnknown() {
        WaMessage m = new WaMessage(ALICE, "KEYU1", true, T * 1000, null, "PLANTED-TEXT", 1);
        assertEquals(-1, m.type);
        assertNull(m.hasContent);
        assertFalse(ReplyRule.isReply(m));
    }

    @Test public void anIncrementRowSaysWhetherItsContentBlockWasPresent() throws Exception {
        IncrementReaderTest.Inc b = new IncrementReaderTest.Inc();
        b.chat(ALICE,
                IncrementReaderTest.msg(ALICE, 1, "KEYH1", T, null, IncrementReaderTest.content(1, "PLANTED-TEXT here"), 201),
                IncrementReaderTest.msg(ALICE, 1, "KEYH2", T + 1, null, null, 202),
                IncrementReaderTest.msg(ALICE, 1, "KEYH3", T + 2, null, IncrementReaderTest.decoys(), 203));
        Increment inc = read(b, 1);
        assertEquals(Boolean.TRUE, inc.messages.get(0).hasContent);
        assertEquals(Boolean.FALSE, inc.messages.get(1).hasContent);
        assertEquals("a content block with no text is still content", Boolean.TRUE, inc.messages.get(2).hasContent);
        assertNull(inc.messages.get(2).text);
        for (WaMessage m : inc.messages) assertEquals("increments carry no type", -1, m.type);
        assertClean(inc.messages.get(0).toString());
    }

    @Test public void theCombineKeepsTheBasesTypeAndTakesContentFromTheIncrement() throws Exception {
        List<WaMessage> base = new ArrayList<>();
        base.add(new WaMessage(ALICE, "KEYR1", true, T * 1000 + 300, null, "PLANTED-TEXT before", 301, 9, null));
        base.add(new WaMessage(ALICE, "KEYR2", true, T * 1000 + 400, null, null, 302, 7, null));
        IncrementReaderTest.Inc one = new IncrementReaderTest.Inc();
        // Replaces KEYR1 (under the hidden id), and adds KEYR3 — new, so its type stays unknown.
        one.chat(ALICE_LID,
                IncrementReaderTest.msg(ALICE_LID, 1, "KEYR1", T, null, IncrementReaderTest.content(1, "PLANTED-TEXT after"), 301),
                IncrementReaderTest.msg(ALICE_LID, 1, "KEYR3", T + 5, null, IncrementReaderTest.content(1, "PLANTED-TEXT new"), 305));
        IncrementReaderTest.Inc two = new IncrementReaderTest.Inc();
        // Replaces KEYR1 again, now without its content block: the type is still the base's.
        two.chat(ALICE, IncrementReaderTest.msg(ALICE, 1, "KEYR1", T, null, null, 301));
        BackupCombiner.Combined c = BackupCombiner.combine(base, aliceLinked(), Arrays.asList(read(one, 1), read(two, 2)),
                set(ALICE), 0);
        Map<String, WaMessage> by = byKey(c);
        assertEquals("kept from the base through two replacements", 9, by.get("KEYR1").type);
        assertEquals("the increment's own", Boolean.FALSE, by.get("KEYR1").hasContent);
        assertEquals("untouched base row", 7, by.get("KEYR2").type);
        assertNull(by.get("KEYR2").hasContent);
        assertEquals("new in an increment: unknown", -1, by.get("KEYR3").type);
        assertEquals(Boolean.TRUE, by.get("KEYR3").hasContent);
        assertEquals("the base's milliseconds still kept", T * 1000 + 300, by.get("KEYR1").timeMs);
        for (WaMessage m : c.messages) assertClean(m.toString());
    }

    @Test public void aLaterCopyWithoutTextKeepsTheEarlierText() throws Exception {
        // F4: a lost message is the failure the combine guards; a later text still replaces.
        List<WaMessage> base = new ArrayList<>();
        base.add(new WaMessage(ALICE, "KEYF1", false, T * 1000 + 100, null, "PLANTED-TEXT kept", 401, 0, null));
        base.add(new WaMessage(ALICE, "KEYF2", false, T * 1000 + 200, null, "PLANTED-TEXT old", 402, 0, null));
        Increment one = inc(1, Arrays.asList(
                new WaMessage(ALICE, "KEYF1", false, T * 1000, null, null, 401, -1, Boolean.FALSE),
                new WaMessage(ALICE, "KEYF2", false, T * 1000, null, "PLANTED-TEXT edited", 402, -1, Boolean.TRUE)));
        Increment two = inc(2, Collections.singletonList(
                new WaMessage(ALICE, "KEYF2", false, T * 1000, null, null, 402, -1, Boolean.FALSE)));
        BackupCombiner.Combined c = BackupCombiner.combine(base, aliceLinked(), Arrays.asList(one, two), set(ALICE), 0);
        Map<String, WaMessage> by = byKey(c);
        assertEquals("PLANTED-TEXT kept", by.get("KEYF1").text);
        assertEquals("the edit stands through a later copy without text", "PLANTED-TEXT edited", by.get("KEYF2").text);
        assertEquals("the increment's own", Boolean.FALSE, by.get("KEYF1").hasContent);
        assertEquals("still counted as a text change", 3, c.textChanged);
        for (WaMessage m : c.messages) assertClean(m.toString());
        // An empty-string copy is no text too (verify, F4 residual).
        Increment empty = inc(1, Collections.singletonList(
                new WaMessage(ALICE, "KEYF1", false, T * 1000, null, "", 401, -1, Boolean.FALSE)));
        BackupCombiner.Combined e = BackupCombiner.combine(base, aliceLinked(), Collections.singletonList(empty), set(ALICE), 0);
        assertEquals("PLANTED-TEXT kept", byKey(e).get("KEYF1").text);
    }

    // ---- 2. the reply rule ----------------------------------------------------------------------

    @Test public void eachAllowedTypeFromMeIsAReply() {
        for (int t : new int[]{0, 1, 2, 3, 4, 9}) assertTrue("type " + t, ReplyRule.isReply(mine(t, null)));
        assertEquals(6, ReplyRule.ALLOWED.size());
    }

    @Test public void aTypeNotInTheSetIsNotAReply() {
        for (int t : new int[]{5, 7, 15, 90, 99, 1000}) assertFalse("type " + t, ReplyRule.isReply(mine(t, null)));
        assertFalse("a known type ignores content", ReplyRule.isReply(mine(7, Boolean.TRUE)));
    }

    @Test public void anUnknownTypeIsAReplyOnlyWithContent() {
        assertTrue(ReplyRule.isReply(mine(-1, Boolean.TRUE)));
        assertFalse(ReplyRule.isReply(mine(-1, Boolean.FALSE)));
        assertFalse(ReplyRule.isReply(mine(-1, null)));
    }

    @Test public void aMessageNotFromMeIsNeverAReply() {
        for (int t : new int[]{0, 1, 9}) {
            assertFalse(ReplyRule.isReply(new WaMessage(ALICE, "KEYN" + t, false, T * 1000, null, "PLANTED-TEXT", 1, t, null)));
        }
        assertFalse(ReplyRule.isReply(new WaMessage(ALICE, "KEYN-", false, T * 1000, null, null, 1, -1, Boolean.TRUE)));
        assertFalse(ReplyRule.isReply(null));
    }

    @Test public void theAllowedSetCannotBeChanged() {
        try {
            ReplyRule.ALLOWED.add(7);
            fail("ALLOWED is modifiable");
        } catch (UnsupportedOperationException expected) {
            assertFalse(ReplyRule.ALLOWED.contains(7));
        }
    }

    // ---- 3. the schema names the read requires --------------------------------------------------

    @Test public void aMissingTypeOrChatIdIsSchemaChanged() {
        for (String[] gone : new String[][]{{"message", "message_type"}, {"chat", "_id"}}) {
            Map<String, Set<String>> actual = new TreeMap<>();
            for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) actual.put(e.getKey(), new HashSet<>(e.getValue()));
            assertTrue(gone[1] + " is required", actual.get(gone[0]).remove(gone[1]));
            try {
                SchemaCheck.require(actual);
                fail(gone[0] + "." + gone[1] + " missing, accepted");
            } catch (BackupException e) {
                assertEquals(BackupError.SCHEMA_CHANGED, e.error);
                assertEquals("schema_changed", e.error.code);
                assertTrue(e.getMessage(), e.getMessage().endsWith(": " + gone[0] + "." + gone[1]));
            }
        }
    }

    // ---- 5. the chat list and its fold ----------------------------------------------------------

    @Test public void theBaseListIsCanonicalNewestFirstWithKindsSubjectsAndNames() {
        ChatList l = baseList();
        assertEquals(Arrays.asList(GROUP, ALICE, CAROL_LID), ids(l));
        ChatList.Chat g = l.byId().get(GROUP), a = l.byId().get(ALICE), c = l.byId().get(CAROL_LID);
        assertEquals(ChatList.GROUP, g.kind);
        assertEquals("PLANTED-SUBJECT old", g.subject);
        assertNull(g.displayName);
        assertEquals(T + 50, g.lastMessageSeconds);
        assertEquals(ChatList.ONE_TO_ONE, a.kind);
        assertNull("one-to-one: no subject", a.subject);
        assertEquals("the hidden id's name reaches its canonical chat", "PLANTED-NAME alice", a.displayName);
        assertEquals("both rows of the chat count", T + 40, a.lastMessageSeconds);
        assertEquals(ChatList.ONE_TO_ONE, c.kind);
        assertEquals("PLANTED-NAME carol", c.displayName);
        assertEquals(0, c.lastMessageSeconds);
        assertEquals(1, l.withoutJid);
        assertClean(l.toString());
        for (ChatList.Chat x : l.chats) assertClean(x.toString());
    }

    @Test public void aSubjectChangeANewChatALinkAndANameChangeAreFolded() throws Exception {
        ChatList base = baseList();
        Map<String, Object> subject = row("_id", 3L, "jid_row_id", 30L, "subject", "PLANTED-SUBJECT new");
        Map<String, Object> newGroup = row("_id", 4L, "jid_row_id", 40L, "subject", "PLANTED-SUBJECT second");
        Increment one = inc(1, Arrays.asList(
                        new WaMessage(GROUP2, "KEYF1", false, (T + 90) * 1000, BOB, "PLANTED-TEXT", 900)),
                delta("chat", "_id", subject, newGroup),
                delta("jid", "_id", row("_id", 40L, "raw_string", GROUP2), row("_id", 61L, "raw_string", CAROL)),
                delta("jid_map", "lid_row_id", row("lid_row_id", 60L, "jid_row_id", 61L)),
                delta("lid_display_name", "lid_row_id", row("lid_row_id", 900L, "display_name", "PLANTED-NAME renamed")));
        ChatList l = base.fold(Collections.singletonList(one));
        Map<String, ChatList.Chat> by = l.byId();
        assertEquals("subject changed", "PLANTED-SUBJECT new", by.get(GROUP).subject);
        assertEquals("new chat", ChatList.GROUP, by.get(GROUP2).kind);
        assertEquals("PLANTED-SUBJECT second", by.get(GROUP2).subject);
        assertEquals("an increment message is activity", T + 90, by.get(GROUP2).lastMessageSeconds);
        assertTrue("the hidden id gained a link: listed under its new canonical id", by.containsKey(CAROL));
        assertFalse(by.containsKey(CAROL_LID));
        assertEquals("its name follows it", "PLANTED-NAME carol", by.get(CAROL).displayName);
        assertEquals("display name changed", "PLANTED-NAME renamed", by.get(ALICE).displayName);
        assertEquals(Arrays.asList(GROUP2, GROUP, ALICE, CAROL), ids(l));
        assertEquals("the base list is not modified", "PLANTED-SUBJECT old", base.byId().get(GROUP).subject);
        assertTrue(base.byId().containsKey(CAROL_LID));
        assertClean(l.toString());
        for (ChatList.Chat x : l.chats) assertClean(x.toString());
    }

    @Test public void aRowWithoutItsSubjectOrNameKeepsTheOneItHad() throws Exception {
        Increment one = inc(1, Collections.<WaMessage>emptyList(),
                delta("chat", "_id", row("_id", 3L, "jid_row_id", 30L)),
                delta("lid_display_name", "lid_row_id", row("lid_row_id", 900L)));
        Map<String, ChatList.Chat> by = baseList().fold(Collections.singletonList(one)).byId();
        assertEquals("PLANTED-SUBJECT old", by.get(GROUP).subject);
        assertEquals("PLANTED-NAME alice", by.get(ALICE).displayName);
        // An explicit null clears, and deletions apply.
        Map<String, Object> cleared = row("_id", 3L, "jid_row_id", 30L);
        cleared.put("subject", null);
        Increment two = inc(1, Collections.<WaMessage>emptyList(), delta("chat", "_id", cleared),
                new Increment.TableDelta("lid_display_name", "lid_row_id", new ArrayList<Map<String, Object>>(),
                        Arrays.asList(900L), 0));
        by = baseList().fold(Collections.singletonList(two)).byId();
        assertNull(by.get(GROUP).subject);
        assertNull(by.get(ALICE).displayName);
        Increment three = inc(1, Collections.<WaMessage>emptyList(),
                new Increment.TableDelta("chat", "_id", new ArrayList<Map<String, Object>>(), Arrays.asList(3L), 0));
        assertFalse("a deleted chat leaves the list", baseList().fold(Collections.singletonList(three)).byId().containsKey(GROUP));
    }

    @Test public void aMissingKeyColumnIsRefused() throws Exception {
        List<Increment> bad = Arrays.asList(
                inc(1, Collections.<WaMessage>emptyList(), delta("chat", "_id", row("_id", 3L, "subject", "PLANTED-SUBJECT"))),
                inc(1, Collections.<WaMessage>emptyList(), delta("chat", "jid_row_id", row("_id", 3L, "jid_row_id", 30L))),
                inc(1, Collections.<WaMessage>emptyList(), delta("lid_display_name", "lid_row_id",
                        row("display_name", "PLANTED-NAME"))),
                inc(1, Collections.<WaMessage>emptyList(), delta("lid_display_name", "_id",
                        row("_id", 1L, "lid_row_id", 900L, "display_name", "PLANTED-NAME"))),
                inc(1, Collections.<WaMessage>emptyList(), delta("jid_map", "lid_row_id", row("lid_row_id", 60L))));
        for (Increment i : bad) {
            try {
                baseList().fold(Collections.singletonList(i));
                fail("a delta without its key column was folded");
            } catch (BackupException e) {
                assertEquals(e.getMessage(), BackupError.INCREMENT_MISSING_PART, e.error);
                assertClean(e.getMessage());
            }
        }
        try {
            baseList().fold(Collections.singletonList(inc(1, Collections.<WaMessage>emptyList(),
                    delta("chat", "_id", row("_id", 3L, "jid_row_id", 30L, "subject", 5L)))));
            fail("a subject that is not text was folded");
        } catch (BackupException e) {
            assertEquals(BackupError.INCREMENT_MALFORMED, e.error);
        }
        try {
            baseList().fold(Collections.singletonList(inc(2, Collections.<WaMessage>emptyList())));
            fail("a set starting at 2 was folded");
        } catch (BackupException e) {
            assertEquals(BackupError.INCREMENT_GAP, e.error);
        }
    }

    // ---- 6. new links ---------------------------------------------------------------------------

    @Test public void aNightWithNoNewLinkHasNoNewLinks() throws Exception {
        IncrementReaderTest.Inc plain = new IncrementReaderTest.Inc().standard();
        // Tonight re-sends ALICE_LID's link, which the base already had: not new.
        plain.jidRows.add(IncrementReaderTest.jidRow(900, ALICE_LID));
        plain.jidMapRows.add(IncrementReaderTest.linkRow(900, 901));
        BackupCombiner.Combined c = BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(),
                Collections.singletonList(read(plain, 1)), set(ALICE), 0);
        assertTrue(c.newLinks.isEmpty());
        assertTrue(BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(), new ArrayList<Increment>(),
                set(ALICE), 0).newLinks.isEmpty());
    }

    @Test public void aHiddenIdThatGainsALinkIsListedOnce() throws Exception {
        BackupCombiner.JidTables tables = aliceLinked();
        tables.putJid(910, CAROL_LID); // no link in the base
        IncrementReaderTest.Inc one = new IncrementReaderTest.Inc();
        one.chat(CAROL_LID, IncrementReaderTest.msg(CAROL_LID, 0, "KEYL1", T, null, IncrementReaderTest.content(1, "PLANTED-TEXT"), 700));
        one.jidRows.add(IncrementReaderTest.jidRow(911, CAROL));
        one.jidMapRows.add(IncrementReaderTest.linkRow(910, 911));
        BackupCombiner.Combined c = BackupCombiner.combine(new ArrayList<WaMessage>(), tables,
                Collections.singletonList(read(one, 1)), set(CAROL), 0);
        assertEquals(Collections.singletonMap(CAROL_LID, CAROL), c.newLinks);
        assertEquals("the message is filed under the new canonical id", CAROL, c.messages.get(0).chatJid);
    }

    @Test public void aLinkLostOrMovedIsNotANewLink() throws Exception {
        // ALICE_LID was linked to ALICE; tonight its link points at another id. A merge would move
        // ALICE's facts, so it is not listed.
        IncrementReaderTest.Inc moved = new IncrementReaderTest.Inc();
        moved.jidRows.add(IncrementReaderTest.jidRow(905, CAROL));
        moved.jidMapRows.add(IncrementReaderTest.linkRow(900, 905));
        moved.standard();
        assertTrue(BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(), Collections.singletonList(read(moved, 1)),
                set(ALICE), 0).newLinks.isEmpty());
    }

    // ---- 7. group senders -----------------------------------------------------------------------

    @Test public void groupSendersAreCanonicalAndFromAllowedGroupsOnly() throws Exception {
        BackupCombiner.JidTables tables = aliceLinked();
        tables.putJid(5, BOB_LID);
        tables.putJid(6, BOB);
        tables.putLink(5, 6);
        List<WaMessage> base = new ArrayList<>();
        base.add(new WaMessage(GROUP, "KEYS1", false, T * 1000, BOB_LID, "PLANTED-TEXT a", 1, 0, null));
        base.add(new WaMessage(GROUP, "KEYS2", false, T * 1000 + 2000, CAROL, null, 2, 1, null));
        base.add(new WaMessage(GROUP, "KEYS3", true, T * 1000 + 3000, null, "PLANTED-TEXT mine", 3, 0, null));
        base.add(new WaMessage(GROUP, "KEYS0", false, (T - 100) * 1000, "447700900555@s.whatsapp.net", null, 4, 0, null));
        base.add(new WaMessage(GROUP2, "KEYS4", false, T * 1000, BOB_LID, "PLANTED-TEXT not shared", 5, 0, null));
        base.add(new WaMessage(ALICE, "KEYS5", false, T * 1000, null, "PLANTED-TEXT one-to-one", 6, 0, null));
        BackupCombiner.Combined c = BackupCombiner.combine(base, tables, new ArrayList<Increment>(), set(GROUP, ALICE), T);
        Map<String, Set<String>> want = new HashMap<>();
        want.put(GROUP, new HashSet<>(Arrays.asList(BOB, CAROL)));
        assertEquals("canonical, allowed groups only, inside the window", want, toHashSets(c.groupSenders));
        try {
            c.groupSenders.get(GROUP).add("x");
            fail("groupSenders is modifiable");
        } catch (UnsupportedOperationException expected) {
            assertEquals(2, c.groupSenders.get(GROUP).size());
        }
        assertTrue(BackupCombiner.combine(base, tables, new ArrayList<Increment>(), set(ALICE), 0).groupSenders.isEmpty());
    }

    @Test public void canonicalisationIsPublic() {
        BackupCombiner.Canon canon = new BackupCombiner.Canon(aliceLinked());
        assertEquals(ALICE, canon.of(ALICE_LID));
        assertEquals(ALICE, canon.of(ALICE));
        assertEquals(CAROL_LID, canon.of(CAROL_LID));
        assertNull(canon.of(null));
        List<WaMessage> out = BackupCombiner.canonicalise(Collections.singletonList(
                new WaMessage(ALICE_LID, "KEYP1", false, T * 1000, null, "PLANTED-TEXT", 1, 4, null)), aliceLinked());
        assertEquals(ALICE, out.get(0).chatJid);
        assertEquals("canonicalise carries the type", 4, out.get(0).type);
    }

    // ---- helpers --------------------------------------------------------------------------------

    /**
     * A base list: GROUP (chat 3, jid 30); ALICE under both ids (chats 1 and 2, jids 901 and 900,
     * linked); CAROL_LID unlinked (chat 5, jid 60, no messages); one chat row with no jid (chat 9).
     */
    private static ChatList baseList() {
        BackupCombiner.JidTables t = aliceLinked();
        t.putJid(30, GROUP);
        t.putJid(60, CAROL_LID);
        Map<Long, ChatList.ChatRow> chats = new TreeMap<>();
        chats.put(1L, new ChatList.ChatRow(901, null));
        chats.put(2L, new ChatList.ChatRow(900, null));
        chats.put(3L, new ChatList.ChatRow(30, "PLANTED-SUBJECT old"));
        chats.put(5L, new ChatList.ChatRow(60, null));
        chats.put(9L, new ChatList.ChatRow(999, null));
        Map<Long, String> names = new TreeMap<>();
        names.put(900L, "PLANTED-NAME alice");
        names.put(60L, "PLANTED-NAME carol");
        names.put(777L, "PLANTED-NAME nobody"); // a hidden id the jid table does not hold
        Map<Long, Long> last = new TreeMap<>();
        last.put(1L, T + 10);
        last.put(2L, T + 40);
        last.put(3L, T + 50);
        return new ChatList(t, chats, names, last, new TreeMap<String, Long>());
    }

    private static Increment inc(long n, List<WaMessage> messages, Increment.TableDelta... deltas) {
        Map<String, Increment.TableDelta> tables = new LinkedHashMap<>();
        for (Increment.TableDelta d : deltas) tables.put(d.table, d);
        return new Increment(n, 0, 0, 0, 0, new ArrayList<>(messages), new ArrayList<Long>(), tables, 0);
    }

    @SafeVarargs
    private static Increment.TableDelta delta(String table, String idField, Map<String, Object>... rows) {
        return new Increment.TableDelta(table, idField, new ArrayList<>(Arrays.asList(rows)), new ArrayList<Long>(), 0);
    }

    private static Map<String, Object> row(Object... kv) {
        Map<String, Object> m = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) m.put((String) kv[i], kv[i + 1]);
        return m;
    }

    private Increment read(IncrementReaderTest.Inc b, long n) throws Exception {
        File f = b.write(tmp.newFile());
        return IncrementReader.read(f, n, BackupKey.fromRoot(IncrementReaderTest.ROOT.clone()));
    }

    private static BackupCombiner.JidTables aliceLinked() {
        BackupCombiner.JidTables t = new BackupCombiner.JidTables();
        t.putJid(900, ALICE_LID);
        t.putJid(901, ALICE);
        t.putLink(900, 901);
        return t;
    }

    private static WaMessage mine(int type, Boolean hasContent) {
        return new WaMessage(ALICE, "KEYM" + type, true, T * 1000, null, null, 1, type, hasContent);
    }

    private static Set<String> set(String... ids) {
        return new HashSet<>(Arrays.asList(ids));
    }

    private static List<String> ids(ChatList l) {
        List<String> out = new ArrayList<>();
        for (ChatList.Chat c : l.chats) out.add(c.id);
        return out;
    }

    private static Map<String, WaMessage> byKey(BackupCombiner.Combined c) {
        Map<String, WaMessage> out = new HashMap<>();
        for (WaMessage m : c.messages) out.put(m.keyId, m);
        return out;
    }

    private static Map<String, Set<String>> toHashSets(Map<String, Set<String>> m) {
        Map<String, Set<String>> out = new HashMap<>();
        for (Map.Entry<String, Set<String>> e : m.entrySet()) out.put(e.getKey(), new HashSet<>(e.getValue()));
        return out;
    }

    private static void assertClean(String s) {
        for (String p : PLANTED) assertFalse(p + " in " + s, s.contains(p));
    }
}
