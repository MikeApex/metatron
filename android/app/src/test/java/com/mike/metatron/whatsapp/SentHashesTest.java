package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicReference;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** The sent-hash list (build plan § 3.4). Every text and sender here is made up. */
public class SentHashesTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final String TEXT = "planted-text-lantern-quartz-5521";
    private static final String SENDER = "planted-member-x7@test.invalid";
    private static final long DAY = 24 * 3600;
    private File dir;

    @Before
    public void setUp() throws IOException {
        SentHashes.forgetInstancesForTest();
        dir = new File(tmp.getRoot(), "wa_state");
    }

    @After
    public void tearDown() {
        SentHashes.forgetInstancesForTest();
    }

    private SentHashes reopen() {
        SentHashes.forgetInstancesForTest();
        return SentHashes.open(dir);
    }

    private byte[] raw(String name) throws IOException {
        return Files.readAllBytes(new File(dir, name).toPath());
    }

    private static void write(File f, byte[] b) throws IOException {
        try (FileOutputStream out = new FileOutputStream(f)) {
            out.write(b);
        }
    }

    private static boolean contains(byte[] hay, String needle) {
        return new String(hay, StandardCharsets.ISO_8859_1).contains(needle)
                || new String(hay, StandardCharsets.UTF_8).contains(needle);
    }

    @Test
    public void roundTripAcrossReopen() throws IOException {
        SentHashes s = SentHashes.open(dir);
        assertEquals(SentHashes.Opened.FRESH, s.opened);
        byte[] th = s.textHash(TEXT), sh = s.senderHash(SENDER);
        assertEquals(16, th.length);
        assertEquals(8, sh.length);
        s.record("chat-a@test|1700000000|0", th, sh, 1_700_000_000L);
        s.record("r|chat-a@test|1700000001|0", s.textHash(""), s.senderHash(""), 1_700_000_001L);
        assertSame(s, SentHashes.open(dir));
        assertSame(s, SentHashes.open(new File(dir.getParentFile(), "./wa_state")));

        SentHashes t = reopen();
        assertEquals(SentHashes.Opened.LOADED, t.opened);
        assertEquals(2, t.size());
        SentHashes.Entry e = t.lookup("chat-a@test|1700000000|0");
        assertNotNull(e);
        assertArrayEquals(th, e.textHash);
        assertArrayEquals(sh, e.senderHash);
        assertEquals(1_700_000_000L, e.second);
        assertEquals(0, t.lookup("r|chat-a@test|1700000001|0").senderHash.length);
        assertNull(t.lookup("chat-a@test|1700000000|1"));
        // The salt persists, so the same text hashes the same after a restart.
        assertArrayEquals(th, t.textHash(TEXT));
        assertArrayEquals(sh, t.senderHash(SENDER));
    }

    @Test
    public void theFilesNeverHoldTheTextOrSender() throws IOException {
        SentHashes s = SentHashes.open(dir);
        s.record("chat-a@test|1700000000|0", s.textHash(TEXT), s.senderHash(SENDER), 1_700_000_000L);
        for (String f : new String[]{SentHashes.SENT_FILE, SentHashes.SALT_FILE}) {
            byte[] b = raw(f);
            assertFalse(f, contains(b, TEXT));
            assertFalse(f, contains(b, SENDER));
            assertFalse(f, contains(b, "lantern"));
            assertFalse(f, contains(b, "planted-member"));
        }
        assertFalse(s.toString().contains(TEXT));
        assertFalse(s.lookup("chat-a@test|1700000000|0").toString().contains(SENDER));
        String[] left = dir.list();
        Arrays.sort(left);
        assertEquals(Arrays.asList(SentHashes.SALT_FILE, SentHashes.SENT_FILE), Arrays.asList(left));   // no temp file left
    }

    @Test
    public void hashesFollowTheContract() throws Exception {
        SentHashes s = SentHashes.open(dir);
        byte[] salt = raw(SentHashes.SALT_FILE);
        assertEquals(32, salt.length);
        javax.crypto.Mac mac = javax.crypto.Mac.getInstance("HmacSHA256");
        mac.init(new javax.crypto.spec.SecretKeySpec(salt, "HmacSHA256"));
        byte[] want = Arrays.copyOf(mac.doFinal(("t\u0000" + TEXT).getBytes(StandardCharsets.UTF_8)), 16);
        assertArrayEquals(want, s.textHash(TEXT));
        want = Arrays.copyOf(mac.doFinal(("s\u0000" + SENDER).getBytes(StandardCharsets.UTF_8)), 8);
        assertArrayEquals(want, s.senderHash(SENDER));
        assertEquals(0, s.senderHash(null).length);
        assertEquals(0, s.senderHash("").length);
        // The prefixes keep a text and a sender of the same string apart.
        assertFalse(Arrays.equals(Arrays.copyOf(s.textHash("same"), 8), s.senderHash("same")));
        // Another install's salt hashes differently.
        File other = new File(tmp.getRoot(), "other_state");
        assertFalse(Arrays.equals(s.textHash(TEXT), SentHashes.open(other).textHash(TEXT)));
    }

    @Test
    public void pruneKeepsExactlyNineDays() {
        SentHashes s = SentHashes.open(dir);
        long cursor = 1_700_000_000L;
        byte[] th = s.textHash("x"), sh = s.senderHash("");
        s.record("k|kept-exact", th, sh, cursor - 9 * DAY);
        s.record("k|dropped", th, sh, cursor - 9 * DAY - 1);
        s.record("k|recent", th, sh, cursor - 1);
        s.record("k|future", th, sh, cursor + 100);
        s.prune(cursor);
        assertEquals(3, s.size());
        assertNull(s.lookup("k|dropped"));
        assertNotNull(s.lookup("k|kept-exact"));
        SentHashes t = reopen();
        assertEquals(3, t.size());
        assertNull(t.lookup("k|dropped"));
        t.prune(cursor + DAY);
        assertEquals(2, t.size());
    }

    @Test
    public void keysForTextNewestFirstWithEveryMatch() {
        SentHashes s = SentHashes.open(dir);
        byte[] ok = s.textHash("made-up-ok"), other = s.textHash("made-up-other");
        s.record("chat-b@test|300|0", ok, s.senderHash(""), 300);
        s.record("chat-a@test|500|0", ok, s.senderHash(""), 500);
        s.record("chat-c@test|100|0", ok, s.senderHash(""), 100);
        s.record("chat-a@test|500|1", ok, s.senderHash(""), 500);
        s.record("chat-a@test|400|0", other, s.senderHash(""), 400);
        assertEquals(Arrays.asList("chat-a@test|500|0", "chat-a@test|500|1", "chat-b@test|300|0", "chat-c@test|100|0"),
                s.keysForText(ok));
        assertEquals(Arrays.asList("chat-a@test|400|0"), s.keysForText(other));
        assertTrue(s.keysForText(s.textHash("never-sent")).isEmpty());
    }

    @Test
    public void aCorruptedListStartsEmptyWithoutACrash() throws IOException {
        SentHashes s = SentHashes.open(dir);
        s.record("chat-a@test|1|0", s.textHash(TEXT), s.senderHash(""), 1);
        byte[] salt = raw(SentHashes.SALT_FILE);
        String[] corrupt = {"", "{", "not json at all", "[]", "{\"v\":2,\"keys\":{}}", "{\"v\":1}",
                "{\"v\":1,\"keys\":{\"k\":[\"zz\",\"\",1]}}",                               // not hex
                "{\"v\":1,\"keys\":{\"k\":[\"00\",\"\",1]}}",                               // wrong length
                "{\"v\":1,\"keys\":{\"k\":[\"00000000000000000000000000000000\",\"\",-1]}}", // negative
                "{\"v\":1,\"keys\":{\"good\":[\"00000000000000000000000000000000\",\"\",1],\"bad\":[1,2]}}"};
        for (String c : corrupt) {
            write(new File(dir, SentHashes.SENT_FILE), c.getBytes(StandardCharsets.UTF_8));
            SentHashes t = reopen();
            assertEquals(c, SentHashes.Opened.UNREADABLE_RESET, t.opened);
            assertEquals(c, 0, t.size());   // never a half-read list
            assertArrayEquals("the salt is kept", salt, raw(SentHashes.SALT_FILE));
            assertEquals(SentHashes.Opened.LOADED, reopen().opened);   // the empty list was written over it
        }
        write(new File(dir, SentHashes.SENT_FILE), new byte[]{(byte) 0xff, (byte) 0xfe, 0, 1});
        assertEquals(0, reopen().size());
    }

    @Test
    public void aLostSaltClearsTheList() throws IOException {
        SentHashes s = SentHashes.open(dir);
        byte[] oldHash = s.textHash(TEXT);
        s.record("chat-a@test|1|0", oldHash, s.senderHash(""), 1);
        byte[] oldSalt = raw(SentHashes.SALT_FILE);
        assertTrue(new File(dir, SentHashes.SALT_FILE).delete());
        SentHashes t = reopen();
        assertEquals(SentHashes.Opened.SALT_LOST_RESET, t.opened);
        assertEquals(0, t.size());
        assertNull(t.lookup("chat-a@test|1|0"));
        assertFalse(Arrays.equals(oldSalt, raw(SentHashes.SALT_FILE)));
        assertFalse(Arrays.equals(oldHash, t.textHash(TEXT)));
        assertEquals(0, reopen().size());
        // A salt of the wrong length is a lost salt too.
        SentHashes u = SentHashes.open(dir);
        u.record("chat-a@test|2|0", u.textHash(TEXT), u.senderHash(""), 2);
        write(new File(dir, SentHashes.SALT_FILE), new byte[5]);
        SentHashes v = reopen();
        assertEquals(SentHashes.Opened.SALT_LOST_RESET, v.opened);
        assertEquals(0, v.size());
        assertEquals(32, raw(SentHashes.SALT_FILE).length);
    }

    @Test
    public void deleteAllRemovesBothFilesAndTheInstance() {
        SentHashes s = SentHashes.open(dir);
        s.record("chat-a@test|1|0", s.textHash(TEXT), s.senderHash(SENDER), 1);
        s.deleteAll();
        assertFalse(new File(dir, SentHashes.SENT_FILE).exists());
        assertFalse(new File(dir, SentHashes.SALT_FILE).exists());
        assertEquals(0, s.size());
        assertNull(s.lookup("chat-a@test|1|0"));
        assertTrue(s.keysForText(new byte[16]).isEmpty());
        try {
            s.record("chat-a@test|2|0", new byte[16], new byte[0], 2);
            fail("a deleted list refuses writes, so a racing listener cannot bring the file back");
        } catch (IllegalStateException expected) {
            // ok
        }
        assertFalse(new File(dir, SentHashes.SENT_FILE).exists());
        try {
            s.textHash(TEXT);
            fail("the salt is gone");
        } catch (IllegalStateException expected) {
            // ok
        }
        s.deleteAll();   // twice is harmless
        SentHashes fresh = SentHashes.open(dir);
        assertTrue(fresh != s);
        assertEquals(SentHashes.Opened.FRESH, fresh.opened);
        assertEquals(0, fresh.size());
    }

    @Test
    public void concurrentRecordsLoseNothing() throws Exception {
        final int perThread = 300;
        CountDownLatch go = new CountDownLatch(1);
        AtomicReference<Throwable> err = new AtomicReference<>();
        List<Thread> threads = new ArrayList<>();
        for (final String who : new String[]{"nightly", "live"}) {
            Thread t = new Thread(() -> {
                try {
                    SentHashes s = SentHashes.open(dir);   // each path opens it itself
                    go.await();
                    for (int i = 0; i < perThread; i++) {
                        s.record(who + "@test|" + i + "|0", s.textHash(who + i), s.senderHash(""), i);
                    }
                } catch (Throwable e) {
                    err.set(e);
                }
            });
            threads.add(t);
            t.start();
        }
        go.countDown();
        for (Thread t : threads) t.join(60_000);
        assertNull(err.get());
        assertEquals(2 * perThread, SentHashes.open(dir).size());
        assertEquals(2 * perThread, reopen().size());
    }

    @Test
    public void recordAllIsOneWriteAndRefusesBadHashes() {
        SentHashes s = SentHashes.open(dir);
        try {
            s.record("k", new byte[15], new byte[0], 1);
            fail("text hash length");
        } catch (IllegalArgumentException expected) {
            // ok
        }
        try {
            s.record("k", new byte[16], new byte[3], 1);
            fail("sender hash length");
        } catch (IllegalArgumentException expected) {
            // ok
        }
        assertEquals(0, s.size());
        byte[] th = s.textHash("made-up");
        // recordAll is exercised with real events in EventPlanTest; empty is a no-op.
        s.recordAll(new ArrayList<EventPlan.Event>());
        assertEquals(0, s.size());
        s.record("k", th, new byte[0], 1);
        assertEquals(1, reopen().size());
    }
    // ---- F2 / F3: a chat's merge, a re-ticked chat, a forgotten VM -----------------------------

    @Test
    public void rekeyChatRenamesBothKeyFormsAndAnExistingTargetWins() throws IOException {
        SentHashes s = SentHashes.open(dir);
        String from = "made-up-hidden-9@lid", to = "made-up-phone-9@s.test", other = "made-up-other-9@s.test";
        byte[] a = s.textHash(TEXT), b = s.textHash(TEXT + "-changed"), empty = s.textHash("");
        s.record(from + "|100|0", a, s.senderHash(SENDER), 100);
        s.record(from + "|101|0", a, s.senderHash(""), 101);
        s.record("r|" + from + "|102|0", empty, s.senderHash(""), 102);
        s.record(to + "|101|0", b, s.senderHash(""), 101); // already under the new id: it wins
        s.record(other + "|100|0", a, s.senderHash(""), 100);
        assertEquals(3, s.rekeyChat(from, to));
        assertNull(s.lookup(from + "|100|0"));
        assertNull(s.lookup("r|" + from + "|102|0"));
        assertArrayEquals(a, s.lookup(to + "|100|0").textHash);
        assertArrayEquals(s.senderHash(SENDER), s.lookup(to + "|100|0").senderHash);
        assertArrayEquals(b, s.lookup(to + "|101|0").textHash);
        assertNotNull(s.lookup("r|" + to + "|102|0"));
        assertNotNull(s.lookup(other + "|100|0"));
        assertEquals(4, s.size());
        assertEquals(0, s.rekeyChat(from, to));
        assertEquals(0, s.rekeyChat(to, to));
        SentHashes again = reopen();
        assertEquals(4, again.size());
        assertNotNull(again.lookup("r|" + to + "|102|0"));
        byte[] file = raw(SentHashes.SENT_FILE);
        assertFalse(contains(file, TEXT));
        assertFalse(contains(file, SENDER));
    }

    @Test
    public void removeChatDropsOnlyThatChatsKeys() {
        SentHashes s = SentHashes.open(dir);
        String chat = "made-up-phone-8@s.test", other = "made-up-phone-80@s.test";
        byte[] a = s.textHash(TEXT);
        s.record(chat + "|100|0", a, s.senderHash(""), 100);
        s.record("r|" + chat + "|101|0", s.textHash(""), s.senderHash(""), 101);
        s.record(other + "|100|0", a, s.senderHash(""), 100);
        assertEquals(2, s.removeChat(chat));
        assertEquals(1, s.size());
        assertNotNull(s.lookup(other + "|100|0"));
        assertEquals(0, s.removeChat(chat));
        assertEquals(1, reopen().size());
    }

    @Test
    public void clearEmptiesTheListAndKeepsTheSaltAndInstance() throws IOException {
        SentHashes s = SentHashes.open(dir);
        byte[] before = s.textHash(TEXT);
        s.record("made-up-phone-7@s.test|100|0", before, s.senderHash(""), 100);
        byte[] salt = raw(SentHashes.SALT_FILE);
        s.clear();
        assertEquals(0, s.size());
        assertSame(s, SentHashes.open(dir));
        assertArrayEquals(salt, raw(SentHashes.SALT_FILE));
        assertArrayEquals(before, s.textHash(TEXT));
        assertEquals(0, reopen().size());
    }
}
