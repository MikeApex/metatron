package com.mike.metatron.whatsapp;

import static com.mike.metatron.whatsapp.NightlyFakes.GROUP;
import static com.mike.metatron.whatsapp.NightlyFakes.HIDDEN;
import static com.mike.metatron.whatsapp.NightlyFakes.OTHER;
import static com.mike.metatron.whatsapp.NightlyFakes.PHONE;
import static com.mike.metatron.whatsapp.NightlyFakes.T1;
import static com.mike.metatron.whatsapp.NightlyFakes.T2;
import static com.mike.metatron.whatsapp.NightlyFakes.T3;
import static com.mike.metatron.whatsapp.NightlyFakes.count;
import static com.mike.metatron.whatsapp.NightlyFakes.destroyed;
import static com.mike.metatron.whatsapp.NightlyFakes.inc;
import static com.mike.metatron.whatsapp.NightlyFakes.link;
import static com.mike.metatron.whatsapp.NightlyFakes.mine;
import static com.mike.metatron.whatsapp.NightlyFakes.received;
import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertSame;
import static org.junit.Assert.assertTrue;

import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

import org.junit.After;
import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/** The one owner of the decrypt (plan § 3.1, § 3.3, § 3.5). Every id and text is made up. */
public class NightlyReadTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static final long NOW = 1_700_000_000_000L;
    private static final long NOW_S = NOW / 1000;
    private static final long DAY = 24 * 3600L;

    private final List<String> log = new ArrayList<>();
    private NightlyFakes.FakeEnv env;

    @Before
    public void setUp() throws IOException {
        NightlyRead.forgetChatList();
        env = new NightlyFakes.FakeEnv(tmp.newFolder("root"), NOW, log);
    }

    @After
    public void tearDown() {
        NightlyRead.forgetChatList();
    }

    private static Set<String> set(String... s) {
        return new HashSet<>(Arrays.asList(s));
    }

    // ---- the kill path ---------------------------------------------------------------------------

    @Test
    public void aDecryptThatFailsAfterWritingLeavesTheWorkFolderEmptyAndTheKeyDestroyed() throws IOException {
        env.files();
        env.decryptThrows = new IOException("made-up");
        RunReport rep = new RunReport();
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, rep);
        assertEquals(RunReport.IO_ERROR, r.error);
        assertEquals("the decrypt ran", 1, env.decrypts);
        assertEquals("work folder empty", 0, count(env.workDir));
        assertTrue("key destroyed", destroyed(env.key));
    }

    @Test
    public void aNamedRefusalMidDecryptAlsoLeavesNothingAndIsReportedByCode() throws IOException {
        env.files();
        env.decryptThrows = new BackupException(BackupError.INTEGRITY, "made-up detail");
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertEquals("integrity", r.error);
        assertEquals(0, count(env.workDir));
        assertTrue(destroyed(env.key));
    }

    @Test
    public void aReadThatFailsAfterTheDecryptLeavesNothing() throws IOException {
        env.files();
        env.readBaseThrows = new BackupException(BackupError.SCHEMA_CHANGED);
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertEquals("schema_changed", r.error);
        assertEquals(0, count(env.workDir));
        assertTrue(destroyed(env.key));
    }

    @Test
    public void aKilledRunsLeftoversAreSweptBeforeTheNextDecrypt() throws IOException {
        // A run killed after its decrypt: a copy, its side files and a .partial left behind.
        for (String n : new String[] {"base.db", "base.db-journal", "base.db-wal", "base.db.partial", "unforeseen"}) {
            try (FileOutputStream o = new FileOutputStream(new File(env.workDir, n))) {
                o.write(1);
            }
        }
        env.baseMessages.add(received(PHONE, NOW_S - DAY, T1, 1));
        env.files();
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertTrue(r.toString(), r.ok());
        assertEquals("swept before the decrypt", 0, env.workFilesAtDecrypt);
        assertEquals(0, count(env.workDir));
    }

    @Test
    public void theDecryptWritesIntoTheWorkFolderOnlyAndASuccessfulReadDeletesItAndTheKey() throws IOException {
        env.baseMessages.add(received(PHONE, NOW_S - DAY, T1, 1));
        env.files();
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertTrue(r.ok());
        assertEquals(env.workDir.getCanonicalFile(), env.destinationSeen.getCanonicalFile().getParentFile());
        assertEquals(0, count(env.workDir));
        assertTrue(destroyed(env.key));
    }

    @Test
    public void deleteDecryptedTakesTheCopyAndEverySideFile() throws IOException {
        File db = new File(env.workDir, "base.db");
        for (String suffix : new String[] {"", ".partial", "-journal", "-wal", "-shm"}) {
            new FileOutputStream(new File(db.getPath() + suffix)).close();
        }
        assertEquals(5, count(env.workDir));
        BackupDecryptor.deleteDecrypted(db);
        assertEquals(0, count(env.workDir));
    }

    @Test
    public void aCancelAfterTheDecryptStopsWithNothingLeft() throws IOException {
        env.files();
        env.cancelAfterDecrypt = true;
        NightlyRead.Result r = NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertTrue(r.cancelled);
        assertNull(r.combined);
        assertEquals(0, count(env.workDir));
        assertTrue(destroyed(env.key));
    }

    // ---- refusals before the decrypt -------------------------------------------------------------

    @Test
    public void noAllFilesAccessIsRefusedBeforeAnythingIsRead() throws IOException {
        env.files();
        env.granted = false;
        assertEquals(NightlyRead.NO_ACCESS, NightlyRead.run(env, null, set(PHONE), NOW, new RunReport()).error);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void noKeyIsRefusedBeforeTheDecrypt() throws IOException {
        env.files();
        env.keyMissing = true;
        assertEquals(NightlyRead.NO_KEY, NightlyRead.run(env, null, set(PHONE), NOW, new RunReport()).error);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void aSetBeingWrittenIsRefusedButItsWriteTimeIsStillReported() throws IOException {
        env.files();
        env.nowMs = new File(env.backupDir, "msgstore.db.crypt15").lastModified() + 60_000L;
        RunReport rep = new RunReport();
        assertEquals("being_written", NightlyRead.run(env, null, set(PHONE), env.nowMs, rep).error);
        assertTrue(rep.backupWritten > 0);
        assertEquals(0, env.decrypts);
    }

    @Test
    public void noBackupIsNoBackupFound() {
        assertEquals("no_backup_found", NightlyRead.run(env, null, set(PHONE), NOW, new RunReport()).error);
    }

    // ---- where the read starts -------------------------------------------------------------------

    @Test
    public void theReadStartsEightDaysBeforeTheCursor() throws IOException {
        long cursor = NOW_S - 2 * DAY;
        env.baseMessages.add(received(PHONE, cursor - 8 * DAY - 1, T1, 1)); // one second too old
        env.baseMessages.add(received(PHONE, cursor - 8 * DAY, T2, 2));     // the first second read
        env.files();
        NightlyRead.Result r = NightlyRead.run(env, cursor, set(PHONE), NOW, new RunReport());
        assertEquals(Long.valueOf(cursor - 8 * DAY), env.sinceSeen);
        assertEquals(cursor - 8 * DAY, r.sinceSeconds);
        assertEquals(1, r.combined.messages.size());
        assertEquals(2, r.combined.messages.get(0).rowId);
    }

    @Test
    public void withNoCursorTheReadStartsNinetyDaysAgo() throws IOException {
        env.files();
        NightlyRead.run(env, null, set(PHONE), NOW, new RunReport());
        assertEquals(Long.valueOf(NOW_S - 90 * DAY), env.sinceSeen);
        assertEquals(NOW_S - 90 * DAY, NightlyRead.since(null, NOW));
        assertEquals(0, NightlyRead.since(1_000L, NOW)); // never before the epoch
    }

    // ---- the re-combine on a new-link night -----------------------------------------------------

    @Test
    public void aSharedHiddenIdThatGainedALinkTonightIsNotDroppedForANight() throws IOException {
        env.tables.putJid(1, HIDDEN);
        env.tables.putJid(2, PHONE);
        env.baseMessages.add(received(HIDDEN, NOW_S - DAY, T1, 1));
        env.increments.add(inc(1, Collections.singletonList(received(HIDDEN, NOW_S - 100, T2, 2)), 0, link(1, 2)));
        env.files();
        NightlyRead.Result r = NightlyRead.run(env, null, set(HIDDEN), NOW, new RunReport());
        assertTrue(r.toString(), r.ok());
        assertEquals(Collections.singletonMap(HIDDEN, PHONE), r.combined.newLinks);
        assertEquals("both messages, under the new canonical id", 2, r.combined.messages.size());
        for (WaMessage m : r.combined.messages) assertEquals(PHONE, m.chatJid);
        assertEquals(Collections.singletonMap(HIDDEN, PHONE), r.hiddenToCanonical);
    }

    @Test
    public void aSharedHiddenIdWhoseLinkIsAlreadyInTheFullBackupIsRead() throws IOException {
        // F1: the link is in the base tables, so nothing is "new tonight" — the allowlist is still canonical.
        env.tables.putJid(1, HIDDEN);
        env.tables.putJid(2, PHONE);
        env.tables.putLink(1, 2);
        env.baseMessages.add(received(HIDDEN, NOW_S - DAY, T1, 1));
        env.increments.add(inc(1, Collections.singletonList(received(PHONE, NOW_S - 100, T2, 2)), 0));
        env.files();
        NightlyRead.Result r = NightlyRead.run(env, null, set(HIDDEN), NOW, new RunReport());
        assertTrue(r.toString(), r.ok());
        assertTrue(r.combined.newLinks.isEmpty());
        assertEquals("both messages pass the allowlist, under the canonical id", 2, r.combined.messages.size());
        for (WaMessage m : r.combined.messages) assertEquals(PHONE, m.chatJid);
        assertEquals(Collections.singletonMap(HIDDEN, PHONE), r.hiddenToCanonical);
    }

    @Test
    public void theAllowlistGainsOnlyTheCanonicalIdsOfAllowedIds() {
        Set<String> allow = set(PHONE);
        assertSame(allow, NightlyRead.canonicalAllowlist(allow, Collections.<String, String>emptyMap()));
        assertSame(allow, NightlyRead.canonicalAllowlist(allow, Collections.singletonMap(HIDDEN, OTHER)));
        assertEquals(set(HIDDEN, PHONE), NightlyRead.canonicalAllowlist(set(HIDDEN), Collections.singletonMap(HIDDEN, PHONE)));
        Set<String> both = set(HIDDEN, PHONE);
        assertSame(both, NightlyRead.canonicalAllowlist(both, Collections.singletonMap(HIDDEN, PHONE)));
    }

    // ---- the counts ----------------------------------------------------------------------------

    @Test
    public void theCountsAreAcrossAllChatsNotJustSharedOnes() throws IOException {
        env.baseMessages.add(received(PHONE, NOW_S - DAY, T1, 1));
        env.baseMessages.add(received(OTHER, NOW_S - DAY, T2, 2));
        env.baseMessages.add(received(GROUP, NOW_S - DAY, null, 3));
        env.baseMessages.add(mine(PHONE, NOW_S - DAY, 4));
        env.withoutKeyId = 4;
        env.withoutChat = 5;
        env.increments.add(inc(1, Arrays.asList(received(OTHER, NOW_S - 50, T3, 10), received(OTHER, NOW_S - 40, null, 11),
                mine(OTHER, NOW_S - 30, 12)), 1));
        env.files();
        RunReport rep = new RunReport();
        NightlyRead.Result r = NightlyRead.run(env, null, Collections.<String>emptySet(), NOW, rep);
        assertTrue(r.ok());
        assertEquals(0, r.combined.messages.size());
        assertEquals(3, rep.baseReceived);
        assertEquals(2, rep.baseReceivedText);
        assertEquals(2, rep.incReceived);
        assertEquals(1, rep.incReceivedText);
        assertEquals(4, rep.withoutKeyId);
        assertEquals(5, rep.withoutChat);
        assertEquals(1, rep.textUndecodable);
        assertEquals(new File(env.backupDir, "msgstore.db.crypt15").lastModified() / 1000, rep.fullBackupWritten);
        assertEquals(new File(env.backupDir, "msgstore-increment-1.db.crypt15").lastModified() / 1000, rep.backupWritten);
        for (String s : new String[] {rep.toString(), r.toString(), rep.toJson()}) {
            for (String t : new String[] {T1, T2, T3, PHONE, OTHER}) assertFalse(s.contains(t));
        }
    }

    // ---- the chat list -------------------------------------------------------------------------

    @Test
    public void theChatListIsKeptInMemoryAfterAReadAndAnOnDemandReadDoesNotDecryptAgain() throws Exception {
        env.files();
        assertTrue(NightlyRead.run(env, null, set(PHONE), NOW, new RunReport()).ok());
        int before = env.decrypts;
        assertNotNull(NightlyRead.readChatList(env));
        assertEquals(before, env.decrypts);
    }

    @Test
    public void anOnDemandChatListReadDecryptsDeletesAndDestroys() throws Exception {
        env.files();
        ChatList l = NightlyRead.readChatList(env);
        assertNotNull(l);
        assertEquals(1, env.decrypts);
        assertEquals(0, count(env.workDir));
        assertTrue(destroyed(env.key));
    }

    @Test
    public void anOnDemandChatListWithoutAKeyIsNullAndANamedRefusalIsThrown() throws Exception {
        env.files();
        env.keyMissing = true;
        assertNull(NightlyRead.readChatList(env));
        env.keyMissing = false;
        env.decryptThrows = new BackupException(BackupError.WRONG_KEY);
        try {
            NightlyRead.readChatList(env);
            throw new AssertionError("expected a refusal");
        } catch (BackupException e) {
            assertEquals(BackupError.WRONG_KEY, e.error);
        }
        assertEquals(0, count(env.workDir));
    }
}
