package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.List;
import java.util.Map;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** "This should have come up" (build plan § 3.11, review 7). Every text and chat id here is made up. */
public class MissedShareTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final String TEXT = "planted-missed-text-heron-cobalt-8817";
    private static final String OTHER = "planted-other-text-walnut-2290";
    private static final String CHAT_A = "chat-a@test.invalid";
    private static final String CHAT_B = "chat-b@test.invalid";
    private static final byte[] NO_SENDER = new byte[0];
    private File dir;
    private SentHashes sent;

    @Before
    public void setUp() {
        SentHashes.forgetInstancesForTest();
        dir = new File(tmp.getRoot(), "wa_state");
        sent = SentHashes.open(dir);
    }

    @After
    public void tearDown() {
        SentHashes.forgetInstancesForTest();
    }

    private void recordReceived(String chat, long second, int ordinal, String text) {
        sent.record(EventPlan.key(chat, second, ordinal), sent.textHash(EventPlan.cut(text)), NO_SENDER, second);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> parse(String json) throws Json.Malformed {
        return (Map<String, Object>) Json.parse(json);
    }

    private static List<Object> keysOf(Map<String, Object> body) {
        @SuppressWarnings("unchecked") List<Object> k = (List<Object>) body.get("keys");
        return k;
    }

    // --- one / several / more than five / none -------------------------------------------------

    @Test
    public void oneMatchPostsItsKey() throws Exception {
        recordReceived(CHAT_A, 1_700_000_000L, 0, TEXT);
        recordReceived(CHAT_A, 1_700_000_100L, 0, OTHER);
        String json = MissedShare.flag(TEXT, sent).toJson();
        Map<String, Object> body = parse(json);
        assertEquals(Collections.singletonList(EventPlan.key(CHAT_A, 1_700_000_000L, 0)), keysOf(body));
        assertEquals(1, body.size());
        assertEquals("{\"keys\":[\"" + CHAT_A + "|1700000000|0\"]}", json);
    }

    @Test
    public void twoToFiveMatchesAreAllPostedNewestFirstAndAmbiguous() throws Exception {
        for (int n = 2; n <= 5; n++) {
            SentHashes.forgetInstancesForTest();
            File d = new File(tmp.getRoot(), "state" + n);
            sent = SentHashes.open(d);
            List<String> expected = new ArrayList<>();
            for (int i = 0; i < n; i++) {
                long second = 1_700_000_000L + i * 60;
                recordReceived(i % 2 == 0 ? CHAT_A : CHAT_B, second, 0, TEXT);
                expected.add(0, EventPlan.key(i % 2 == 0 ? CHAT_A : CHAT_B, second, 0));
            }
            recordReceived(CHAT_A, 1_600_000_000L, 0, OTHER);
            MissedShare.Flag f = MissedShare.flag(TEXT, sent);
            Map<String, Object> body = parse(f.toJson());
            assertEquals("n=" + n, new ArrayList<Object>(expected), keysOf(body));
            assertEquals("n=" + n, Boolean.TRUE, body.get("ambiguous"));
            assertFalse("n=" + n, body.containsKey("ambiguous_over"));
            assertEquals(2, body.size());
        }
    }

    @Test
    public void moreThanFiveMatchesPostNoKeysAndTheCount() throws Exception {
        for (int i = 0; i < 6; i++) recordReceived(CHAT_A, 1_700_000_000L + i, 0, TEXT);
        Map<String, Object> body = parse(MissedShare.flag(TEXT, sent).toJson());
        assertEquals(Collections.emptyList(), keysOf(body));
        assertEquals(6L, body.get("ambiguous_over"));
        assertFalse(body.containsKey("ambiguous"));
        assertEquals(2, body.size());

        for (int i = 6; i < 40; i++) recordReceived(CHAT_B, 1_700_000_000L + i, 1, TEXT);
        body = parse(MissedShare.flag(TEXT, sent).toJson());
        assertEquals(Collections.emptyList(), keysOf(body));
        assertEquals(40L, body.get("ambiguous_over"));
    }

    @Test
    public void noMatchPostsAnEmptyList() throws Exception {
        recordReceived(CHAT_A, 1_700_000_000L, 0, OTHER);
        assertEquals("{\"keys\":[]}", MissedShare.flag(TEXT, sent).toJson());
        SentHashes.forgetInstancesForTest();
        SentHashes empty = SentHashes.open(new File(tmp.getRoot(), "empty"));
        assertEquals("{\"keys\":[]}", MissedShare.flag(TEXT, empty).toJson());
    }

    // --- reply markers -------------------------------------------------------------------------

    @Test
    public void replyMarkerKeysAreNeverAMatch() throws Exception {
        long s = 1_700_000_000L;
        // A reply marker recorded under the same hash — never so on the phone, but the rule must hold.
        sent.record(EventPlan.replyKey(CHAT_A, s, 0), sent.textHash(TEXT), NO_SENDER, s + 50);
        assertEquals("{\"keys\":[]}", MissedShare.flag(TEXT, sent).toJson());

        recordReceived(CHAT_B, s, 0, TEXT);
        assertEquals("{\"keys\":[\"" + EventPlan.key(CHAT_B, s, 0) + "\"]}", MissedShare.flag(TEXT, sent).toJson());

        // Five received and two markers: five keys, ambiguous — the markers count toward nothing.
        for (int i = 1; i < 5; i++) recordReceived(CHAT_B, s + i, 0, TEXT);
        sent.record(EventPlan.replyKey(CHAT_B, s, 7), sent.textHash(TEXT), NO_SENDER, s + 60);
        Map<String, Object> body = parse(MissedShare.flag(TEXT, sent).toJson());
        assertEquals(5, keysOf(body).size());
        for (Object k : keysOf(body)) assertFalse(((String) k).startsWith("r|"));
        assertEquals(Boolean.TRUE, body.get("ambiguous"));
        assertFalse(body.containsKey("ambiguous_over"));
    }

    @Test
    public void fromMatchesDropsReplyMarkersBeforeCounting() {
        List<String> m = new ArrayList<>();
        for (int i = 0; i < 5; i++) m.add("c|" + i + "|0");
        for (int i = 0; i < 3; i++) m.add("r|c|" + i + "|0");
        MissedShare.Flag f = MissedShare.fromMatches(m);
        assertEquals(5, f.keys.size());
        assertTrue(f.ambiguous);
        assertEquals(-1, f.ambiguousOver);
        f = MissedShare.fromMatches(Arrays.asList("r|c|1|0", "r|c|2|0"));
        assertEquals("{\"keys\":[]}", f.toJson());
    }

    // --- the cut -------------------------------------------------------------------------------

    @Test
    public void aTextOverTheLimitMatchesTheKeyRecordedForItsCut() throws Exception {
        StringBuilder b = new StringBuilder();
        // Supplementary code points, so the cut is by code point, not by char.
        while (b.codePointCount(0, b.length()) < EventPlan.MAX_TEXT_CODE_POINTS + 250) {
            b.append("planted-😀-");
        }
        String longText = b.toString();
        String cut = EventPlan.cut(longText);
        assertEquals(EventPlan.MAX_TEXT_CODE_POINTS, cut.codePointCount(0, cut.length()));
        long s = 1_700_000_000L;
        // What the nightly job records: the hash of the cut text.
        sent.record(EventPlan.key(CHAT_A, s, 2), sent.textHash(cut), NO_SENDER, s);
        assertEquals("{\"keys\":[\"" + EventPlan.key(CHAT_A, s, 2) + "\"]}",
                MissedShare.flag(longText, sent).toJson());
        assertEquals("{\"keys\":[\"" + EventPlan.key(CHAT_A, s, 2) + "\"]}",
                MissedShare.flag(cut, sent).toJson());
        // A text that differs only after the cut still matches; one that differs before it does not.
        assertEquals(1, MissedShare.flag(longText + "-tail", sent).keys.size());
        assertEquals(0, MissedShare.flag("x" + longText, sent).keys.size());
    }

    // --- empty and blank -------------------------------------------------------------------------

    @Test
    public void emptyOrBlankTextMatchesNothing() throws Exception {
        long s = 1_700_000_000L;
        // Reply markers carry the hash of "" — an empty share must not find them, nor anything else.
        sent.record(EventPlan.replyKey(CHAT_A, s, 0), sent.textHash(""), NO_SENDER, s);
        String[] blanks = {null, "", " ", "   \n\t ", " ", " 　", "\r\n"};
        for (String blank : blanks) {
            if (blank != null && !blank.isEmpty()) {
                // Even were a blank text somehow recorded under its own hash, it is not looked up.
                sent.record(EventPlan.key(CHAT_B, s, blank.length()), sent.textHash(blank), NO_SENDER, s);
            }
        }
        for (String blank : blanks) {
            assertNull(MissedShare.hashOf(blank, sent));
            assertEquals("{\"keys\":[]}", MissedShare.flag(blank, sent).toJson());
        }
        assertEquals("{\"keys\":[]}", MissedShare.flagFor(null, sent).toJson());
        assertFalse(MissedShare.isBlank(" a "));
    }

    // --- the body's limits match the VM's ---------------------------------------------------------

    @Test
    public void theBodyHasOnlyTheVmsKeysAndAtMostFiveOfThem() throws Exception {
        assertEquals(5, MissedShare.MAX_KEYS);
        assertEquals("/device/whatsapp/missed", MissedShare.PATH);
        for (int n = 0; n <= 12; n++) {
            List<String> m = new ArrayList<>();
            for (int i = 0; i < n; i++) m.add(EventPlan.key(CHAT_A, 1_700_000_000L - i, 0));
            Map<String, Object> body = parse(MissedShare.fromMatches(m).toJson());
            for (String k : body.keySet()) {
                assertTrue(k, k.equals("keys") || k.equals("ambiguous") || k.equals("ambiguous_over"));
            }
            assertTrue(keysOf(body).size() <= MissedShare.MAX_KEYS);
            if (n == 1) assertEquals(1, body.size());
        }
    }

    // --- the text never leaves -------------------------------------------------------------------

    @Test
    public void aPlantedTextNeverAppearsInTheBodyTheStateFilesOrAnyToString() throws IOException {
        long s = 1_700_000_000L;
        for (int i = 0; i < 3; i++) recordReceived(CHAT_A, s + i, 0, TEXT);
        List<String> outputs = new ArrayList<>();
        for (String shared : new String[]{TEXT, OTHER}) {
            byte[] h = MissedShare.hashOf(shared, sent);
            MissedShare.Flag f = MissedShare.flagFor(h, sent);
            outputs.add(f.toJson());
            outputs.add(f.toString());
            outputs.add(MissedShare.flag(shared, sent).toJson());
        }
        for (int i = 3; i < 9; i++) recordReceived(CHAT_B, s + i, 0, TEXT);
        MissedShare.Flag over = MissedShare.flag(TEXT, sent);
        outputs.add(over.toJson());
        outputs.add(over.toString());
        outputs.add(sent.toString());
        outputs.add(String.valueOf(sent.lookup(EventPlan.key(CHAT_A, s, 0))));
        for (String out : outputs) {
            assertFalse(out, out.contains(TEXT));
            assertFalse(out, out.contains(OTHER));
            assertFalse(out, out.contains("heron"));
        }
        // A Flag's toString names no chat (a chat id can be a phone number).
        for (int i = 0; i < 2; i++) {
            String str = MissedShare.flag(i == 0 ? TEXT : OTHER, sent).toString();
            assertFalse(str, str.contains(CHAT_A));
            assertFalse(str, str.contains(CHAT_B));
        }

        byte[] t = TEXT.getBytes(StandardCharsets.UTF_8), o = OTHER.getBytes(StandardCharsets.UTF_8);
        File[] files = dir.listFiles();
        assertTrue(files != null && files.length > 0);
        for (File f : files) {
            byte[] raw = Files.readAllBytes(f.toPath());
            assertFalse(f.getName(), contains(raw, t));
            assertFalse(f.getName(), contains(raw, o));
            String asText = new String(raw, StandardCharsets.UTF_8);
            assertFalse(f.getName(), asText.contains("heron"));
            assertFalse(f.getName(), asText.contains("walnut"));
        }
    }

    @Test
    public void lookingUpWritesNothing() throws IOException {
        recordReceived(CHAT_A, 1_700_000_000L, 0, TEXT);
        byte[] before = Files.readAllBytes(new File(dir, SentHashes.SENT_FILE).toPath());
        int sizeBefore = sent.size();
        MissedShare.flag(TEXT, sent);
        MissedShare.flag(OTHER, sent);
        MissedShare.flag("", sent);
        assertEquals(sizeBefore, sent.size());
        assertTrue(Arrays.equals(before, Files.readAllBytes(new File(dir, SentHashes.SENT_FILE).toPath())));
        String[] names = dir.list();
        assertTrue(names != null);
        Arrays.sort(names);
        assertEquals(Arrays.asList(SentHashes.SALT_FILE, SentHashes.SENT_FILE), Arrays.asList(names));
    }

    private static boolean contains(byte[] hay, byte[] needle) {
        outer:
        for (int i = 0; i + needle.length <= hay.length; i++) {
            for (int j = 0; j < needle.length; j++) if (hay[i + j] != needle[j]) continue outer;
            return true;
        }
        return false;
    }
}
