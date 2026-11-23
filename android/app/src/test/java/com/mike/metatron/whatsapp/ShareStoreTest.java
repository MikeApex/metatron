package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayDeque;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.Deque;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The share list's store (build plan § 3.9, verify new 2, reviews 1 and 6, § 3.6 SHARE_OUT_OF_STEP).
 * Every id, name and subject here is made up; the planted ones are asserted never to leave the phone.
 */
public class ShareStoreTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    // Made-up ids: never a real number.
    private static final String ONE = "100000000001@s.whatsapp.net";
    private static final String TWO = "100000000002@s.whatsapp.net";
    private static final String HIDDEN = "900000000009@lid";
    private static final String LINKED = "100000000003@s.whatsapp.net";
    private static final String GROUP = "100000000004-1600000000@g.us";
    private static final String MEMBER_KNOWN = "100000000005@s.whatsapp.net";
    private static final String MEMBER_UNKNOWN = "100000000006@s.whatsapp.net";
    private static final String MEMBER_HIDDEN = "900000000010@lid";

    private static final String NAME_ONE = "Contact Alpha";
    private static final String NAME_LINKED = "Contact Gamma";
    private static final String NAME_MEMBER = "Contact Delta";
    private static final String SUBJECT = "Planted subject quartz";
    private static final String PLANTED_DISPLAY = "PLANTED-DISPLAY-NAME-lantern-7741";
    private static final String PLANTED_DISPLAY_2 = "PLANTED-DISPLAY-NAME-orchid-3319";

    private File dir;
    private FakeApi api;
    private FakeHooks hooks;
    private FakeContacts contacts;
    private ShareStore store;

    @Before
    public void setUp() {
        dir = new File(tmp.getRoot(), "wa_state");
        api = new FakeApi();
        hooks = new FakeHooks();
        contacts = new FakeContacts();
        contacts.names.put("100000000001", NAME_ONE);
        contacts.names.put("100000000003", NAME_LINKED);
        contacts.names.put("100000000005", NAME_MEMBER);
        store = new ShareStore(dir, contacts, hooks);
    }

    // ---- fakes ---------------------------------------------------------------------------------

    static final class FakeApi implements DeviceApi {
        final List<String> bodies = new ArrayList<>();
        final Deque<Result> replies = new ArrayDeque<>();

        void accept(int shared, int removed) {
            replies.add(new Result(200, "{\"shared\":" + shared + ",\"removed\":" + removed + ",\"purged_facts\":0}", ""));
        }

        @Override public Result get(String path) { throw new AssertionError("no GET expected"); }

        @Override
        public Result post(String path, String jsonBody, int readTimeoutMs) {
            assertEquals(ShareStore.PATH, path);
            bodies.add(jsonBody);
            Result r = replies.poll();
            return r == null ? new Result(200, "{\"shared\":0,\"removed\":0,\"purged_facts\":0}", "") : r;
        }

        Map<?, ?> last() throws Json.Malformed {
            return (Map<?, ?>) Json.parse(bodies.get(bodies.size() - 1));
        }
    }

    static final class FakeHooks implements ShareStore.Hooks {
        int observed;
        Boolean outOfStep;
        int raised;

        @Override public void observe(DeviceApi.Result reply) { observed++; }

        @Override
        public void outOfStep(boolean on) {
            outOfStep = on;
            if (on) raised++;
        }
    }

    static final class FakeContacts implements ShareStore.Contacts {
        boolean granted = true;
        final Map<String, String> names = new HashMap<>();

        @Override public boolean available() { return granted; }
        @Override public String nameFor(String digits) { return names.get(digits); }
    }

    private static ChatList.Chat oneToOne(String id, String displayName) {
        return new ChatList.Chat(id, ChatList.ONE_TO_ONE, null, displayName, 1_700_000_000L);
    }

    private static ChatList.Chat group(String id, String subject) {
        return new ChatList.Chat(id, ChatList.GROUP, subject, null, 1_700_000_000L);
    }

    private static Map<String, ChatList.Chat> available(ChatList.Chat... chats) {
        Map<String, ChatList.Chat> m = new LinkedHashMap<>();
        for (ChatList.Chat c : chats) m.put(c.id, c);
        return m;
    }

    private Map<String, ChatList.Chat> all() {
        return available(oneToOne(ONE, PLANTED_DISPLAY), oneToOne(TWO, PLANTED_DISPLAY_2),
                oneToOne(HIDDEN, PLANTED_DISPLAY), oneToOne(LINKED, PLANTED_DISPLAY_2), group(GROUP, SUBJECT));
    }

    private ShareStore.Saved save(String... ids) {
        return store.saveAndPost(api, Arrays.asList(ids), all());
    }

    private static Map<String, Set<String>> senders(String group, String... ids) {
        Map<String, Set<String>> m = new HashMap<>();
        m.put(group, new LinkedHashSet<>(Arrays.asList(ids)));
        return m;
    }

    private ShareList.Post nightly() {
        return store.postNightly(api, Collections.<String, String>emptyMap(),
                Collections.<String, Set<String>>emptyMap(), Collections.<String, String>emptyMap());
    }

    private File file() {
        return new File(dir, ShareStore.FILE);
    }

    private String fileText() throws IOException {
        return new String(Files.readAllBytes(file().toPath()), StandardCharsets.UTF_8);
    }

    private void writeFile(String s) throws IOException {
        dir.mkdirs();
        try (FileOutputStream out = new FileOutputStream(file())) {
            out.write(s.getBytes(StandardCharsets.UTF_8));
        }
    }

    private static Map<?, ?> chatIn(Map<?, ?> body, String id) {
        for (Object o : (List<?>) body.get("chats")) {
            Map<?, ?> c = (Map<?, ?>) o;
            if (id.equals(c.get("chat"))) return c;
        }
        return null;
    }

    // ---- never saved / lost state (verify new 2) -----------------------------------------------

    @Test
    public void neverSavedPostsNothing() {
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));
        assertTrue(api.bodies.isEmpty());
        assertFalse(file().exists());
        assertTrue(store.sharedKinds().isEmpty());
        assertFalse(store.acceptedCurrent());
    }

    @Test
    public void fileWithoutTheUsersSaveIsNotSaved() throws IOException {
        save(ONE);
        String text = fileText().replace("\"saved_by_user\":true", "\"saved_by_user\":false");
        writeFile(text);
        api.bodies.clear();
        assertEquals(ShareStore.Found.NOT_SAVED, store.read().found);
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));
        assertTrue(api.bodies.isEmpty());
        assertTrue(store.sharedKinds().isEmpty());
        assertNull(store.canonicalShared(ONE));
    }

    @Test
    public void missingUnreadableOrTruncatedFilePostsNothingAndPurgesNothing() throws IOException {
        save(ONE, GROUP);
        String good = fileText();
        api.bodies.clear();
        hooks.observed = 0;

        file().delete();
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));

        for (String bad : new String[] {
                good.substring(0, good.length() / 2),        // truncated
                "",                                           // empty
                "not json at all",                            // unreadable
                good.replace("\"v\":1", "\"v\":2"),           // another format
                good.replace("\"pending\":[]", "\"pending\":{}")}) {
            writeFile(bad);
            assertEquals(ShareStore.Found.UNREADABLE, store.read().found);
            assertEquals(ShareList.Post.NOT_SAVED, nightly());
            assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));
            assertTrue(store.sharedKinds().isEmpty());
            // Left as found: an unattended run never rewrites a file it cannot read.
            assertEquals(bad, fileText());
        }
        assertTrue("no post, so the VM purges nothing", api.bodies.isEmpty());
        assertEquals(0, hooks.observed);
    }

    // ---- the empty list ------------------------------------------------------------------------

    @Test
    public void emptyListGoesOnlyAtTheUsersTap() throws Json.Malformed {
        save(ONE);
        ShareStore.Saved s = save();
        assertEquals(ShareList.Post.ACCEPTED, s.post);
        assertEquals(2, api.bodies.size());
        assertTrue(((List<?>) api.last().get("chats")).isEmpty());
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));
        assertEquals(2, api.bodies.size());
    }

    @Test
    public void emptyUntickNotAcceptedIsNotRetriedUnattended() {
        save(ONE);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        assertEquals(ShareList.Post.FAILED, save().post);
        int posts = api.bodies.size();
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(ShareList.Post.NOT_SAVED, store.repost(api));
        assertEquals(posts, api.bodies.size());
        assertNull("the un-tick already stops sending", store.canonicalShared(ONE));
        assertFalse(store.acceptedCurrent());
    }

    // ---- un-ticking ----------------------------------------------------------------------------

    @Test
    public void pendingUntickIsRepostedAndExcludedUntilTheReplyShowsItRemoved() throws Json.Malformed {
        save(ONE, TWO);
        api.replies.add(new DeviceApi.Result(403, "{\"detail\":\"consented_off\"}", "consented_off"));
        ShareStore.Saved s = save(TWO);
        assertEquals(ShareList.Post.REFUSED, s.post);
        assertEquals(0, s.removedConfirmed);
        assertEquals(Collections.singleton(ONE), store.read().state.pending);
        assertFalse(store.sharedKinds().containsKey(ONE));
        assertNull(store.canonicalShared(ONE));
        assertEquals("", store.label(ONE));

        // The next run re-posts the user's save — ONE absent from the body, so the VM removes it.
        api.accept(1, 1);
        assertEquals(ShareList.Post.ACCEPTED, nightly());
        assertNull(chatIn(api.last(), ONE));
        assertTrue(store.read().state.pending.isEmpty());
        assertTrue(store.acceptedCurrent());
    }

    @Test
    public void untickConfirmedOnlyByAnAcceptedReplyCarryingRemoved() {
        save(ONE, TWO);
        api.replies.add(new DeviceApi.Result(200, "<html>proxy</html>", ""));
        ShareStore.Saved s = save(TWO);
        assertEquals(ShareList.Post.REFUSED, s.post);
        assertEquals(0, s.removedConfirmed);
        assertFalse(store.read().state.pending.isEmpty());
        api.accept(1, 1);
        assertEquals(1, save(TWO).removedConfirmed);
        assertTrue(store.read().state.pending.isEmpty());
    }

    @Test
    public void retickingAPendingRemovalSharesItAgain() {
        save(ONE, TWO);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        save(TWO);
        save(ONE, TWO);
        assertTrue(store.read().state.pending.isEmpty());
        assertEquals(ONE, store.canonicalShared(ONE));
    }

    // ---- F3: a re-ticked chat is sent again ----------------------------------------------------

    private SentHashes sentWith(String... chats) {
        SentHashes.forgetInstancesForTest();
        SentHashes sent = SentHashes.open(dir);
        for (String c : chats) {
            sent.record(EventPlan.key(c, 1_700_000_000L, 0), sent.textHash("made-up"), sent.senderHash(""), 1_700_000_000L);
            sent.record(EventPlan.replyKey(c, 1_700_000_001L, 0), sent.textHash(""), sent.senderHash(""), 1_700_000_001L);
        }
        return sent;
    }

    @Test
    public void retickingAfterAConfirmedUntickForgetsWhatWasSentSoItIsSentAgain() {
        save(ONE, TWO);
        SentHashes sent = sentWith(ONE, TWO);
        api.accept(1, 1);
        assertEquals(1, save(TWO).removedConfirmed); // purged on the VM
        assertNotNullKey(sent, ONE);
        api.accept(2, 0);
        save(ONE, TWO);
        assertNull(sent.lookup(EventPlan.key(ONE, 1_700_000_000L, 0)));
        assertNull(sent.lookup(EventPlan.replyKey(ONE, 1_700_000_001L, 0)));
        assertNotNullKey(sent, TWO); // shared throughout: kept
        SentHashes.forgetInstancesForTest();
    }

    @Test
    public void aSaveWithNoSentListCreatesNone() {
        save(ONE);
        assertFalse(new File(dir, SentHashes.SALT_FILE).exists());
        assertFalse(new File(dir, SentHashes.SENT_FILE).exists());
    }

    private static void assertNotNullKey(SentHashes sent, String chat) {
        assertTrue(sent.lookup(EventPlan.key(chat, 1_700_000_000L, 0)) != null);
    }

    // ---- accepted version and SHARE_OUT_OF_STEP ------------------------------------------------

    @Test
    public void acceptedVersionTracking() {
        api.replies.add(new DeviceApi.Result(403, "{\"detail\":\"no_consent\"}", "no_consent"));
        assertEquals(ShareList.Post.REFUSED, save(ONE).post);
        assertFalse(store.acceptedCurrent());
        api.accept(1, 0);
        assertEquals(ShareList.Post.ACCEPTED, nightly());
        assertEquals(2, api.bodies.size());
        assertTrue(store.acceptedCurrent());
        // A change makes the VM's copy behind again until accepted.
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        save(ONE, TWO);
        assertFalse(store.acceptedCurrent());
        api.accept(2, 0);
        assertEquals(ShareList.Post.ACCEPTED, store.repost(api));
        assertTrue(store.acceptedCurrent());
        assertEquals(4, hooks.observed);
    }

    @Test
    public void outOfStepAfterTwoFailuresInARowClearedOnAccept() {
        save(ONE);
        assertEquals(Boolean.FALSE, hooks.outOfStep);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        assertEquals(ShareList.Post.FAILED, nightly());
        assertEquals(0, hooks.raised);
        api.replies.add(new DeviceApi.Result(500, "", ""));
        assertEquals(ShareList.Post.REFUSED, nightly());
        assertEquals(1, hooks.raised);
        assertEquals(Boolean.TRUE, hooks.outOfStep);
        api.accept(1, 0);
        assertEquals(ShareList.Post.ACCEPTED, nightly());
        assertEquals(Boolean.FALSE, hooks.outOfStep);
        // One failure after an accept is not two in a row.
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        nightly();
        assertEquals(Boolean.FALSE, hooks.outOfStep);
        assertEquals(1, hooks.raised);
    }

    @Test
    public void aClosedGateIsNotOutOfStep() {
        // Before the channel opens the VM refuses every share-list post with a 403 (the gate). Any
        // number of them raises nothing; the list stays not-accepted, so it is re-posted later.
        save(ONE);
        int before = hooks.raised;
        for (int i = 0; i < 3; i++) {
            api.replies.add(new DeviceApi.Result(403, "", "consented_off"));
            assertEquals(ShareList.Post.REFUSED, nightly());
        }
        assertEquals(before, hooks.raised);
        assertEquals(Boolean.FALSE, hooks.outOfStep);
        // A 403 does not reset a real failure streak either: one failure, a 403, one failure → raised.
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        nightly();
        api.replies.add(new DeviceApi.Result(403, "", "consented_off"));
        nightly();
        api.replies.add(new DeviceApi.Result(500, "", ""));
        nightly();
        assertEquals(Boolean.TRUE, hooks.outOfStep);
    }

    // ---- migration and merges ------------------------------------------------------------------

    @Test
    public void migrationOnNewLinksAndTheMergesBody() throws Json.Malformed {
        save(HIDDEN, GROUP);
        assertEquals("", store.read().state.chats.get(HIDDEN).label);
        Map<String, String> newLinks = new LinkedHashMap<>();
        newLinks.put(HIDDEN, LINKED);
        newLinks.put("900000000011@lid", "100000000007@s.whatsapp.net"); // not shared: no merge
        Map<String, String> links = new LinkedHashMap<>(newLinks);
        links.put(MEMBER_HIDDEN, MEMBER_KNOWN);                          // not a shared chat: not stored
        api.accept(3, 0);
        assertEquals(ShareList.Post.ACCEPTED,
                store.postNightly(api, newLinks, Collections.<String, Set<String>>emptyMap(), links));

        Map<?, ?> body = api.last();
        List<?> merges = (List<?>) body.get("merges");
        assertEquals(1, merges.size());
        assertEquals(HIDDEN, ((Map<?, ?>) merges.get(0)).get("from"));
        assertEquals(LINKED, ((Map<?, ?>) merges.get(0)).get("to"));
        // The hidden id is posted alongside its canonical one, so the VM merges before it purges.
        assertEquals(NAME_LINKED, chatIn(body, LINKED).get("label"));
        assertEquals("", chatIn(body, HIDDEN).get("label"));
        assertEquals(ChatList.ONE_TO_ONE, chatIn(body, HIDDEN).get("kind"));

        assertEquals(ChatList.ONE_TO_ONE, store.sharedKinds().get(LINKED));
        assertFalse(store.sharedKinds().containsKey(HIDDEN));
        assertEquals(LINKED, store.canonicalShared(HIDDEN));
        assertEquals(LINKED, store.canonicalShared(LINKED));
        assertFalse(store.read().state.links.containsKey(MEMBER_HIDDEN));

        // Accepted: the merge and the hidden id are gone from the next post.
        api.accept(2, 1);
        assertEquals(ShareList.Post.ACCEPTED, store.repost(api));
        body = api.last();
        assertTrue(((List<?>) body.get("merges")).isEmpty());
        assertNull(chatIn(body, HIDDEN));
        assertEquals(LINKED, store.canonicalShared(HIDDEN));
    }

    @Test
    public void aSharedHiddenIdWhoseLinkWasAlreadyInTheFullBackupMigrates() throws Json.Malformed {
        // F1: newLinks is empty — the link was in the base tables — and the chat still migrates.
        save(HIDDEN);
        Map<String, String> migrations = new LinkedHashMap<>();
        api.accept(2, 0);
        assertEquals(ShareList.Post.ACCEPTED, store.postNightly(api, Collections.<String, String>emptyMap(),
                Collections.<String, Set<String>>emptyMap(), Collections.singletonMap(HIDDEN, LINKED), migrations));
        assertEquals(Collections.singletonMap(HIDDEN, LINKED), migrations);
        Map<?, ?> body = api.last();
        List<?> merges = (List<?>) body.get("merges");
        assertEquals(1, merges.size());
        assertEquals(HIDDEN, ((Map<?, ?>) merges.get(0)).get("from"));
        assertEquals(LINKED, ((Map<?, ?>) merges.get(0)).get("to"));
        assertEquals("", chatIn(body, HIDDEN).get("label")); // posted once more alongside, so the VM merges first
        assertEquals(NAME_LINKED, chatIn(body, LINKED).get("label"));
        assertEquals(ChatList.ONE_TO_ONE, store.sharedKinds().get(LINKED));
        assertEquals(LINKED, store.canonicalShared(HIDDEN));
        assertEquals(LINKED, store.canonicalShared(LINKED));
        // The next night: nothing left to migrate, both ids still resolve.
        migrations.clear();
        api.accept(1, 1);
        assertEquals(ShareList.Post.ACCEPTED, store.postNightly(api, Collections.<String, String>emptyMap(),
                Collections.<String, Set<String>>emptyMap(), Collections.singletonMap(HIDDEN, LINKED), migrations));
        assertTrue(migrations.isEmpty());
        assertTrue(((List<?>) api.last().get("merges")).isEmpty());
        assertNull(chatIn(api.last(), HIDDEN));
        assertEquals(LINKED, store.canonicalShared(HIDDEN));
        assertEquals(LINKED, store.canonicalShared(LINKED));
    }

    @Test
    public void anUnacceptedMergeIsReportedAgainForTheSentList() {
        save(HIDDEN);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        Map<String, String> migrations = new LinkedHashMap<>();
        store.postNightly(api, null, null, Collections.singletonMap(HIDDEN, LINKED), migrations);
        assertEquals(Collections.singletonMap(HIDDEN, LINKED), migrations);
        migrations.clear();
        api.accept(2, 0);
        store.postNightly(api, null, null, Collections.singletonMap(HIDDEN, LINKED), migrations);
        assertEquals("carried over until accepted", Collections.singletonMap(HIDDEN, LINKED), migrations);
    }

    @Test
    public void unacceptedMergeIsKeptAndPostedAgain() throws Json.Malformed {
        save(HIDDEN);
        Map<String, String> newLinks = Collections.singletonMap(HIDDEN, LINKED);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        assertEquals(ShareList.Post.FAILED, store.postNightly(api, newLinks,
                Collections.<String, Set<String>>emptyMap(), newLinks));
        assertFalse(store.acceptedCurrent());
        api.accept(2, 0);
        assertEquals(ShareList.Post.ACCEPTED, store.repost(api));
        assertEquals(1, ((List<?>) api.last().get("merges")).size());
        assertTrue(store.acceptedCurrent());
    }

    @Test
    public void migrationOntoAnUntickedCanonicalChatUnsharesBoth() {
        save(HIDDEN, LINKED);
        api.replies.add(new DeviceApi.Result(DeviceApi.NETWORK, "", "IOException"));
        save(HIDDEN);
        Map<String, String> newLinks = Collections.singletonMap(HIDDEN, LINKED);
        assertEquals(ShareList.Post.NOT_SAVED, store.postNightly(api, newLinks,
                Collections.<String, Set<String>>emptyMap(), newLinks));
        assertNull(store.canonicalShared(HIDDEN));
        assertNull(store.canonicalShared(LINKED));
        assertTrue(store.sharedKinds().isEmpty());
    }

    // ---- names ---------------------------------------------------------------------------------

    @Test
    public void sendersHoldContactNamesOnly() throws Json.Malformed {
        save(GROUP);
        api.accept(1, 0);
        store.postNightly(api, Collections.<String, String>emptyMap(),
                senders(GROUP, MEMBER_KNOWN, MEMBER_UNKNOWN, MEMBER_HIDDEN), Collections.<String, String>emptyMap());
        Map<?, ?> g = chatIn(api.last(), GROUP);
        assertEquals(SUBJECT, g.get("label"));
        assertEquals(ChatList.GROUP, g.get("kind"));
        Map<?, ?> s = (Map<?, ?>) g.get("senders");
        assertEquals(1, s.size());
        assertEquals(NAME_MEMBER, s.get(MEMBER_KNOWN));
        assertFalse(s.containsKey(MEMBER_UNKNOWN));
        assertFalse(s.containsKey(MEMBER_HIDDEN));

        // A contact saved later is named the same night.
        contacts.names.put("100000000006", "Contact Epsilon");
        store.postNightly(api, Collections.<String, String>emptyMap(), senders(GROUP, MEMBER_UNKNOWN),
                Collections.<String, String>emptyMap());
        s = (Map<?, ?>) chatIn(api.last(), GROUP).get("senders");
        assertEquals("Contact Epsilon", s.get(MEMBER_UNKNOWN));
        assertEquals(NAME_MEMBER, s.get(MEMBER_KNOWN));
    }

    @Test
    public void oneToOneNotInContactsPostsAnEmptyLabel() throws Json.Malformed {
        save(ONE, TWO, HIDDEN);
        Map<?, ?> body = api.last();
        assertEquals(NAME_ONE, chatIn(body, ONE).get("label"));
        assertEquals("", chatIn(body, TWO).get("label"));
        assertEquals("", chatIn(body, HIDDEN).get("label"));
        assertFalse(chatIn(body, ONE).containsKey("senders"));
    }

    @Test
    public void withoutTheContactsGrantNoNameIsInvented() throws Json.Malformed {
        contacts.granted = false;
        save(ONE, GROUP);
        assertEquals("", chatIn(api.last(), ONE).get("label"));
        store.postNightly(api, Collections.<String, String>emptyMap(), senders(GROUP, MEMBER_KNOWN),
                Collections.<String, String>emptyMap());
        assertTrue(((Map<?, ?>) chatIn(api.last(), GROUP).get("senders")).isEmpty());
    }

    @Test
    public void aPlantedDisplayNameNeverLeavesThePhone() throws IOException, Json.Malformed {
        contacts.names.clear();                   // nothing from contacts: the display name is the only name there is
        save(ONE, TWO, HIDDEN, GROUP);
        store.postNightly(api, Collections.singletonMap(HIDDEN, LINKED), senders(GROUP, ONE, TWO),
                Collections.singletonMap(HIDDEN, LINKED));
        store.repost(api);
        save(TWO);
        assertTrue(api.bodies.size() >= 4);
        for (String b : api.bodies) {
            assertFalse(b.contains(PLANTED_DISPLAY));
            assertFalse(b.contains(PLANTED_DISPLAY_2));
            assertFalse(b.contains("PLANTED-DISPLAY"));
        }
        assertFalse(fileText().contains("PLANTED-DISPLAY"));
        assertEquals("", store.label(TWO));
    }

    // ---- the live feed's lookup ----------------------------------------------------------------

    @Test
    public void canonicalSharedThroughTheLinkMap() {
        save(LINKED, GROUP);
        api.accept(2, 0);
        store.postNightly(api, Collections.<String, String>emptyMap(), Collections.<String, Set<String>>emptyMap(),
                Collections.singletonMap(HIDDEN, LINKED));
        assertEquals(LINKED, store.canonicalShared(HIDDEN));
        assertEquals(LINKED, store.canonicalShared(LINKED));
        assertEquals(GROUP, store.canonicalShared(GROUP));
        assertNull("an unlinked hidden one-to-one is held for the backup", store.canonicalShared("900000000012@lid"));
        assertNull("not shared", store.canonicalShared(TWO));
        assertNull(store.canonicalShared(null));
        assertEquals(ChatList.GROUP, store.kindOf(GROUP));
        assertNull(store.kindOf(TWO));
        assertEquals(SUBJECT, store.label(GROUP));
    }

    @Test
    public void unlinkedHiddenOneToOneIsHeldEvenWhenShared() {
        save(HIDDEN);
        assertNull(store.canonicalShared(HIDDEN));
        assertEquals(ChatList.ONE_TO_ONE, store.sharedKinds().get(HIDDEN));
    }

    // ---- turning off ---------------------------------------------------------------------------

    @Test
    public void deleteAllForgetsEverything() {
        save(LINKED, GROUP);
        store.postNightly(api, Collections.<String, String>emptyMap(), Collections.<String, Set<String>>emptyMap(),
                Collections.singletonMap(HIDDEN, LINKED));
        assertTrue(store.acceptedCurrent());
        store.deleteAll();
        assertFalse(file().exists());
        assertEquals(ShareStore.Found.ABSENT, store.read().found);
        assertTrue(store.sharedKinds().isEmpty());
        assertFalse(store.acceptedCurrent());
        assertNull(store.canonicalShared(HIDDEN));
        assertEquals("", store.label(GROUP));
        int posts = api.bodies.size();
        assertEquals(ShareList.Post.NOT_SAVED, nightly());
        assertEquals(posts, api.bodies.size());
    }

    @Test
    public void aPostOutDuringTurnOffWritesNothingBack() {
        save(ONE);
        DeviceApi turningOff = new DeviceApi() {
            @Override public Result get(String path) { throw new AssertionError(); }

            @Override
            public Result post(String path, String body, int t) {
                store.deleteAll();
                return new Result(200, "{\"shared\":1,\"removed\":0}", "");
            }
        };
        assertEquals(ShareList.Post.ACCEPTED, store.repost(turningOff));
        assertFalse(file().exists());
    }

    // ---- helpers -------------------------------------------------------------------------------

    @Test
    public void phoneDigitsOnlyFromAPhoneNumberId() {
        assertEquals("100000000001", ShareStore.phoneDigits(ONE));
        assertEquals("100000000001", ShareStore.phoneDigits("100000000001:7@s.whatsapp.net"));
        assertNull(ShareStore.phoneDigits(HIDDEN));
        assertNull(ShareStore.phoneDigits(GROUP));
        assertNull(ShareStore.phoneDigits("abc@s.whatsapp.net"));
        assertNull(ShareStore.phoneDigits(null));
    }

    @Test
    public void storeRoundTripsAndLabelsAreOneLine() {
        assertEquals("a b", ShareStore.clean(" a\n\tb "));
        assertEquals(ShareStore.MAX_LABEL, ShareStore.clean(new String(new char[100]).replace('\0', 'x')).length());
        store.saveAndPost(api, Arrays.asList(GROUP), available(group(GROUP, "line one\nline two")));
        assertEquals("line one line two", store.label(GROUP));
        ShareStore.State s = store.read().state;
        assertEquals(ShareStore.encode(s), ShareStore.encode(new ShareStore(dir, contacts, hooks).read().state));
    }
}
