package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.zip.Deflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * The increment reader and the combine (format description § 12), on synthetic increments built by
 * our own encoder from the shapes observed on Mike's phone: a crypt15 container (§ 3, as
 * BackupReaderTest builds one), zlib, and a ZIP of header.json, sequences.json, a messages.bin
 * written through the adopted field map, jid_modified_1.json, jid_map_modified_1.json and
 * deletedMessages_1.json. All values are made up; refusal messages are checked for leaks.
 */
public class IncrementReaderTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    static final String ALICE = "447700900123@s.whatsapp.net", ALICE_LID = "111111111111111@lid",
            GROUP = "120363000000000001@g.us", BOB_LID = "222222222222222@lid", ME = "447700900999@s.whatsapp.net";
    static final long T = 1_763_870_400L; // seconds
    static final byte[] ROOT = filled(32, 0x42), IV = filled(16, 0x24);

    // ---- decode ------------------------------------------------------------------------------

    @Test public void decodesAnIncrementThroughTheAdoptedFieldMapOnly() throws Exception {
        Inc b = new Inc();
        b.chat(ALICE,
                msg(ALICE, 0, "KEYA1", T, null, content(1, "plain words"), 101),
                msg(ALICE, 1, "KEYA2", T + 1, null, content2(6, 1, "extended words"), 102));
        b.chat(GROUP,
                msg(GROUP, 0, "KEYG1", T + 2, BOB_LID, caption("a caption"), 103),
                msg(GROUP, 1, "KEYG2", T + 3, ME, content(1, "mine in a group"), 104),
                msg(GROUP, 0, "KEYG3", T + 4, BOB_LID, nested("deep words"), 105),
                msg(GROUP, 0, "KEYG4", T + 5, BOB_LID, decoys(), 106));
        b.topLevelExtras = true;
        b.jidRows.add(jidRow(900, ALICE_LID));
        b.jidMapRows.add(linkRow(900, 901));
        b.deletedMessages = Arrays.asList(103L);
        Increment inc = IncrementReader.read(b.write(tmp.newFile()), 1, key());

        assertEquals(1, inc.number);
        assertEquals(52031, inc.messagesCountOnBackup);
        assertEquals(6, inc.messages.size());
        WaMessage a1 = inc.messages.get(0);
        assertEquals(ALICE, a1.chatJid);
        assertEquals("KEYA1", a1.keyId);
        assertFalse(a1.fromMe);
        assertEquals(T * 1000, a1.timeMs);
        assertEquals("plain words", a1.text);
        assertNull("one-to-one: no sender", a1.senderJid);
        assertEquals(101, a1.rowId);
        assertTrue(inc.messages.get(1).fromMe);
        assertEquals("extended words", inc.messages.get(1).text);
        assertEquals("a caption", inc.messages.get(2).text);
        assertEquals("group, not from me: sender kept", BOB_LID, inc.messages.get(2).senderJid);
        assertNull("group, from me: 1.5 ignored", inc.messages.get(3).senderJid);
        assertEquals("deep words", inc.messages.get(4).text);
        assertNull("1.2.6.2 and 1.26 are not text", inc.messages.get(5).text);
        assertEquals(Arrays.asList(103L), inc.deletedMessageIds);
        assertEquals(1, inc.tables.get("jid").modified.size());
        assertEquals("_id", inc.tables.get("jid").idField);
        assertEquals(Arrays.asList(950L), inc.tables.get("jid").deletedIds);
        assertEquals(1, inc.tables.get("jid_map").modified.size());
        assertFalse("tables P1–P3 do not read are ignored", inc.tables.containsKey("receipt_user"));
        assertEquals(0, inc.textUndecodable);
        assertFalse("toString carries no content", a1.toString().contains("plain"));
    }

    @Test public void aNightWithNoDeletionsHasNoFileListAndIsRead() throws Exception {
        // Observed 11-23: deleted_messages present, without deleted_message_ids_files, when none were deleted.
        Increment inc = IncrementReader.read(new Inc().standard().write(tmp.newFile()), 1, key());
        assertTrue(inc.deletedMessageIds.isEmpty());
        assertEquals(1, inc.messages.size());
    }

    @Test public void aListedDeletionFileThatIsAbsentIsReadAsEmptyAndCounted() throws Exception {
        Inc b = new Inc().standard();
        b.omitJidDeletedFile = true;
        Increment inc = IncrementReader.read(b.write(tmp.newFile()), 1, key());
        assertTrue(inc.tables.get("jid").deletedIds.isEmpty());
        assertEquals(1, inc.tables.get("jid").absentDeletedFiles);
        Inc m = new Inc().standard();
        m.omitJidModifiedFile = true;
        expect(m, BackupError.INCREMENT_MISSING_PART);
    }

    @Test public void theFullBackupPathStillRefusesTheZipPayload() throws Exception {
        File f = new Inc().standard().write(tmp.newFile());
        File out = new File(tmp.newFolder(), "msgstore.db");
        try {
            BackupDecryptor.decrypt(f, key(), out, dir -> Long.MAX_VALUE);
            fail("the full-backup path accepted an increment");
        } catch (BackupException e) {
            assertEquals(BackupError.NOT_A_MESSAGE_DATABASE, e.error);
        }
        assertFalse(out.exists());
        assertFalse(new File(out.getPath() + ".partial").exists());
    }

    // ---- combine -----------------------------------------------------------------------------

    @Test public void combineAppliesIncrementsInOrderAndALaterVersionWins() throws Exception {
        List<WaMessage> base = new ArrayList<>();
        base.add(new WaMessage(ALICE, "KEYA1", false, T * 1000 + 250, null, "the original words", 101));
        base.add(new WaMessage(ALICE, "KEYA9", false, T * 1000 - 86_400_000L, null, "old, before since", 90));
        base.add(new WaMessage(GROUP, "KEYG1", false, T * 1000 + 3000, BOB_LID, "kept despite a deletion list", 103));
        base.add(new WaMessage("999@s.whatsapp.net", "KEYX1", false, T * 1000, null, "a chat not shared", 99));
        BackupCombiner.JidTables tables = new BackupCombiner.JidTables();
        tables.putJid(901, ALICE);
        tables.putJid(902, "333333333333333@lid");
        tables.putJid(903, "447700900333@s.whatsapp.net");
        tables.putLink(902, 903);

        // 1: edits KEYA1 (sent under Alice's hidden id, which this increment's jid / jid_map link),
        //    adds a new message, and lists KEYG1's row as deleted.
        Inc one = new Inc();
        one.chat(ALICE_LID, msg(ALICE_LID, 0, "KEYA1", T, null, content(1, "first edit"), 101),
                msg(ALICE_LID, 0, "KEYA3", T + 10, null, content(1, "a new message"), 110));
        one.jidRows.add(jidRow(900, ALICE_LID));
        one.jidMapRows.add(linkRow(900, 901));
        one.deletedMessages = Arrays.asList(103L);
        // 2: edits KEYA1 again, now under the phone id; removes the text of KEYA3 (a re-sent copy without text).
        Inc two = new Inc();
        two.chat(ALICE, msg(ALICE, 0, "KEYA1", T, null, content(1, "second edit"), 101),
                msg(ALICE, 0, "KEYA3", T + 10, null, null, 110));
        List<Increment> incs = Arrays.asList(
                IncrementReader.read(one.write(tmp.newFile()), 1, key()),
                IncrementReader.read(two.write(tmp.newFile()), 2, key()));

        Set<String> allowed = new HashSet<>(Arrays.asList(ALICE, GROUP));
        BackupCombiner.Combined c = BackupCombiner.combine(base, tables, incs, allowed, T - 3600);

        assertEquals(3, c.messages.size());
        WaMessage a1 = c.messages.get(0);
        assertEquals("KEYA1", a1.keyId);
        assertEquals("the later version wins", "second edit", a1.text);
        assertEquals("canonical chat", ALICE, a1.chatJid);
        assertEquals("the full backup's milliseconds are kept for the same second", T * 1000 + 250, a1.timeMs);
        assertEquals("KEYG1", c.messages.get(1).keyId);
        assertEquals("deletions are counted, never applied", "kept despite a deletion list", c.messages.get(1).text);
        assertEquals("KEYA3", c.messages.get(2).keyId);
        assertEquals("a re-sent copy without text keeps the earlier text (F4)", "a new message", c.messages.get(2).text);
        assertEquals(1, c.deletionsListed);
        assertEquals(4, c.incrementMessages);
        assertEquals(1, c.added);
        assertEquals(3, c.replaced);
        assertEquals(3, c.textChanged);
        assertEquals(4, c.baseMessages);
        assertEquals(0, c.baseKeyCollisions);

        BackupCombiner.Combined none = BackupCombiner.combine(base, tables, incs, new HashSet<>(), 0);
        assertTrue("an empty allowlist returns nothing", none.messages.isEmpty());
    }

    @Test public void aGroupSenderIsCanonicalised() throws Exception {
        BackupCombiner.JidTables tables = new BackupCombiner.JidTables();
        tables.putJid(5, BOB_LID);
        tables.putJid(6, "447700900222@s.whatsapp.net");
        tables.putLink(5, 6);
        Inc one = new Inc();
        one.chat(GROUP, msg(GROUP, 0, "KEYG7", T, BOB_LID, content(1, "hello group"), 120));
        BackupCombiner.Combined c = BackupCombiner.combine(new ArrayList<>(), tables,
                Arrays.asList(IncrementReader.read(one.write(tmp.newFile()), 1, key())), new HashSet<>(Arrays.asList(GROUP)), 0);
        assertEquals("447700900222@s.whatsapp.net", c.messages.get(0).senderJid);
    }

    @Test public void sameSecondMessagesAreNumberedByRowIdReceivedApartFromMine() throws Exception {
        BackupCombiner.JidTables tables = aliceLinked();
        List<WaMessage> base = new ArrayList<>();
        // From the full backup, with its milliseconds: received, the lower row id.
        base.add(new WaMessage(ALICE, "KEYO1", false, T * 1000 + 700, null, "first in the second", 300));
        // The user's own message in the same second, lowest row id of all: numbered apart.
        base.add(new WaMessage(ALICE, "KEYO0", true, T * 1000 + 100, null, "my own words", 299));
        base.add(new WaMessage(GROUP, "KEYO9", false, T * 1000 + 50, BOB_LID, "a group in the same second", 298));
        // New in the increment, so …000 ms, sent under the chat's hidden id; the higher row id.
        Inc one = new Inc();
        one.chat(ALICE_LID, msg(ALICE_LID, 0, "KEYO2", T, null, content(1, "second in the second"), 301));
        List<Increment> incs = Arrays.asList(IncrementReader.read(one.write(tmp.newFile()), 1, key()));

        BackupCombiner.Combined c = BackupCombiner.combine(base, tables, incs, new HashSet<>(Arrays.asList(ALICE)), T);
        assertEquals(3, c.messages.size());
        assertEquals("by second, then row id — not ahead of the full backup's message for ending in 000",
                Arrays.asList("KEYO0", "KEYO1", "KEYO2"), keyIds(c));
        Map<String, Integer> o = ordinals(c);
        assertEquals(0, (int) o.get("KEYO1"));
        assertEquals("numbered with the phone-id copy of the chat: canonical before counting", 1, (int) o.get("KEYO2"));
        assertEquals("from-me rows are numbered on their own", 0, (int) o.get("KEYO0"));
        assertEquals(ALICE, c.messages.get(2).chatJid);

        // A received row without text, lower row id, still counts — and shifts both.
        List<WaMessage> withPhoto = new ArrayList<>(base);
        withPhoto.add(new WaMessage(ALICE, "KEYOP", false, T * 1000 + 900, null, null, 297));
        Map<String, Integer> p = ordinals(BackupCombiner.combine(withPhoto, tables, incs, new HashSet<>(Arrays.asList(ALICE)), T));
        assertEquals(0, (int) p.get("KEYOP"));
        assertEquals(1, (int) p.get("KEYO1"));
        assertEquals(2, (int) p.get("KEYO2"));
        assertEquals(0, (int) p.get("KEYO0"));

        // The allowlist changes what is returned, never a number.
        Map<String, Integer> g = ordinals(BackupCombiner.combine(withPhoto, tables, incs, new HashSet<>(Arrays.asList(ALICE, GROUP)), T));
        assertEquals(1, (int) g.get("KEYO1"));
        assertEquals(2, (int) g.get("KEYO2"));
        assertEquals(0, (int) g.get("KEYO9"));
        assertEquals("read straight from a file: no ordinal yet", 0, incs.get(0).messages.get(0).ordinal);
    }

    @Test public void theSinceBoundaryIsAWholeSecond() throws Exception {
        List<WaMessage> base = new ArrayList<>();
        base.add(new WaMessage(ALICE, "KEYB0", false, (T - 1) * 1000 + 999, null, "a second before", 400));
        base.add(new WaMessage(ALICE, "KEYB1", false, T * 1000, null, "at the start of the second", 401));
        base.add(new WaMessage(ALICE, "KEYB2", false, T * 1000 + 999, null, "at its end", 402));
        BackupCombiner.Combined c = BackupCombiner.combine(base, new BackupCombiner.JidTables(), new ArrayList<Increment>(),
                new HashSet<>(Arrays.asList(ALICE)), T);
        assertEquals(Arrays.asList("KEYB1", "KEYB2"), keyIds(c));
        assertEquals(0, c.messages.get(0).ordinal);
        assertEquals(1, c.messages.get(1).ordinal);
    }

    @Test public void baseRowsThatShareAKeyAreCounted() throws Exception {
        List<WaMessage> base = new ArrayList<>();
        // One chat under both its ids, the same key_id: after canonicalising, one combine key.
        base.add(new WaMessage(ALICE, "KEYC1", false, T * 1000, null, "under the phone id", 600));
        base.add(new WaMessage(ALICE_LID, "KEYC1", false, T * 1000, null, "under the hidden id", 601));
        base.add(new WaMessage(ALICE, "KEYC2", false, T * 1000 + 5000, null, "no clash", 602));
        BackupCombiner.Combined c = BackupCombiner.combine(base, aliceLinked(), new ArrayList<Increment>(),
                new HashSet<>(Arrays.asList(ALICE)), 0);
        assertEquals(1, c.baseKeyCollisions);
        assertEquals(2, c.messages.size());
        assertEquals("the later row is kept, as before", 601, c.messages.get(0).rowId);
    }

    @Test public void aJidRowWithoutItsColumnRefusesRatherThanUnlinking() throws Exception {
        Inc renamed = new Inc().standard();
        renamed.jidRows.add("{\"_id\":901,\"user\":\"447700900123\",\"server\":\"s.whatsapp.net\",\"raw_text\":\"" + ALICE + "\"}");
        BackupException e = expectCombine(renamed, BackupError.INCREMENT_MISSING_PART);
        assertTrue(e.getMessage(), e.getMessage().contains("raw_string"));
        assertFalse(e.getMessage(), e.getMessage().contains("447700900123"));

        Inc wrongType = new Inc().standard();
        wrongType.jidRows.add("{\"_id\":901,\"raw_string\":5}");
        expectCombine(wrongType, BackupError.INCREMENT_MALFORMED);

        Inc mapKey = new Inc().standard();
        mapKey.jidMapIdField = "sort_id";
        mapKey.jidMapRows.add(linkRow(900, 901));
        expectCombine(mapKey, BackupError.INCREMENT_MISSING_PART);

        // An explicit null still removes the id: the hidden id no longer canonicalises.
        Set<String> both = new HashSet<>(Arrays.asList(ALICE, ALICE_LID));
        Inc nulled = new Inc();
        nulled.chat(ALICE_LID, msg(ALICE_LID, 0, "KEYN1", T, null, content(1, "some words"), 500));
        Inc control = new Inc();
        control.chat(ALICE_LID, msg(ALICE_LID, 0, "KEYN1", T, null, content(1, "some words"), 500));
        nulled.jidRows.add("{\"_id\":901,\"raw_string\":null}");
        assertEquals(ALICE, BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(),
                Arrays.asList(IncrementReader.read(control.write(tmp.newFile()), 1, key())), both, 0).messages.get(0).chatJid);
        assertEquals(ALICE_LID, BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(),
                Arrays.asList(IncrementReader.read(nulled.write(tmp.newFile()), 1, key())), both, 0).messages.get(0).chatJid);
    }

    private BackupException expectCombine(Inc inc, BackupError want) throws Exception {
        Increment read = IncrementReader.read(inc.write(tmp.newFile()), 1, key());
        try {
            BackupCombiner.combine(new ArrayList<WaMessage>(), aliceLinked(), Arrays.asList(read), new HashSet<>(Arrays.asList(ALICE)), 0);
            fail("expected " + want.code);
            return null;
        } catch (BackupException e) {
            assertEquals(e.getMessage(), want, e.error);
            return e;
        }
    }

    /** Alice's hidden id (900) linked to her phone id (901), as a full backup's tables hold them. */
    private static BackupCombiner.JidTables aliceLinked() {
        BackupCombiner.JidTables t = new BackupCombiner.JidTables();
        t.putJid(900, ALICE_LID);
        t.putJid(901, ALICE);
        t.putLink(900, 901);
        return t;
    }

    private static List<String> keyIds(BackupCombiner.Combined c) {
        List<String> out = new ArrayList<>();
        for (WaMessage m : c.messages) out.add(m.keyId);
        return out;
    }

    private static Map<String, Integer> ordinals(BackupCombiner.Combined c) {
        Map<String, Integer> out = new LinkedHashMap<>();
        for (WaMessage m : c.messages) out.put(m.keyId, m.ordinal);
        return out;
    }

    // ---- refusals ----------------------------------------------------------------------------

    @Test public void aGapInNIsRefusedWithTheCountRead() throws Exception {
        File dir = tmp.newFolder("Databases");
        for (String n : new String[]{"msgstore.db.crypt15", "msgstore-increment-1.db.crypt15", "msgstore-increment-2.db.crypt15",
                "msgstore-increment-4.db.crypt15", "msgstore-increment-3-2026-11-17.1.db.crypt15"}) {
            assertTrue(new File(dir, n).createNewFile());
        }
        try {
            IncrementSet.locate(dir);
            fail("gap accepted");
        } catch (BackupException e) {
            assertEquals(BackupError.INCREMENT_GAP, e.error);
            assertTrue(e.getMessage(), e.getMessage().contains("increment 3 missing; 2 readable before it"));
        }
        assertTrue(new File(dir, "msgstore-increment-4.db.crypt15").delete());
        IncrementSet s = IncrementSet.locate(dir);
        assertEquals("the dated (rotated) increment is not part of the live set", 2, s.increments.size());
        assertEquals(2, IncrementSet.number(s.increments.get(1)));

        Increment two = IncrementReader.read(new Inc().standard().write(tmp.newFile()), 2, key());
        try {
            BackupCombiner.combine(new ArrayList<>(), new BackupCombiner.JidTables(), Arrays.asList(two), new HashSet<>(), 0);
            fail("combine accepted a set starting at 2");
        } catch (BackupException e) {
            assertEquals(BackupError.INCREMENT_GAP, e.error);
        }
    }

    @Test public void aSetBeingWrittenIsDeferred() throws Exception {
        File dir = tmp.newFolder("Databases");
        File base = new File(dir, "msgstore.db.crypt15");
        assertTrue(base.createNewFile());
        assertTrue(new File(dir, "msgstore-increment-1.db.crypt15").createNewFile());
        long now = System.currentTimeMillis();
        assertTrue(base.setLastModified(now - 3_600_000L));
        try {
            IncrementSet.locate(dir).requireComplete(() -> now, ms -> { });
            fail("a just-written increment was accepted");
        } catch (BackupException e) {
            assertEquals(BackupError.BEING_WRITTEN, e.error);
        }
    }

    @Test public void anUnknownFormatIsRefused() throws Exception {
        Inc v = new Inc().standard();
        v.formatVersion = "2.0";
        expect(v, BackupError.INCREMENT_FORMAT_UNKNOWN);
        Inc f = new Inc().standard();
        f.messagesFormat = "json";
        expect(f, BackupError.INCREMENT_FORMAT_UNKNOWN);
        Inc notZip = new Inc().standard();
        notZip.rawPayload = "not a zip at all".getBytes(StandardCharsets.UTF_8);
        expect(notZip, BackupError.INCREMENT_FORMAT_UNKNOWN);
    }

    @Test public void aMalformedRecordIsRefused() throws Exception {
        Inc cut = new Inc().standard();
        cut.truncateMessagesBin = 3;
        expect(cut, BackupError.INCREMENT_MALFORMED);
        Inc json = new Inc().standard();
        json.brokenJidJson = true;
        expect(json, BackupError.INCREMENT_MALFORMED);
        Inc wrongChat = new Inc();
        wrongChat.chat(ALICE, msg(GROUP, 0, "KEYW1", T, null, content(1, "filed under the wrong chat"), 1));
        expect(wrongChat, BackupError.INCREMENT_MALFORMED);
    }

    @Test public void aMissingPartIsRefusedByName() throws Exception {
        Inc noAdded = new Inc().standard();
        noAdded.omitAddedMessages = true;
        BackupException e = expect(noAdded, BackupError.INCREMENT_MISSING_PART);
        assertTrue(e.getMessage(), e.getMessage().contains("added_messages"));
        Inc noBin = new Inc().standard();
        noBin.omitMessagesBin = true;
        expect(noBin, BackupError.INCREMENT_MISSING_PART);
        Inc noKey = new Inc();
        noKey.chat(ALICE, msgWithoutKeyId(ALICE, T, 7));
        expect(noKey, BackupError.INCREMENT_MISSING_PART);
        Inc noList = new Inc().standard();
        noList.deletedMessages = Arrays.asList(1L);
        noList.omitDeletedList = true;
        BackupException l = expect(noList, BackupError.INCREMENT_MISSING_PART);
        assertTrue(l.getMessage(), l.getMessage().contains("deleted_message_ids_files"));
        Inc noFile = new Inc().standard();
        noFile.deletedMessages = Arrays.asList(1L);
        noFile.omitDeletedFile = true;
        expect(noFile, BackupError.INCREMENT_MISSING_PART);
    }

    @Test public void overTheCapIsRefused() throws Exception {
        File big = tmp.newFile();
        try (RandomAccessFile r = new RandomAccessFile(big, "rw")) {
            r.setLength(IncrementReader.MAX_ENCRYPTED_BYTES + 1);
        }
        try {
            IncrementReader.read(big, 1, key());
            fail("over the encrypted cap");
        } catch (BackupException e) {
            assertEquals(BackupError.INCREMENT_TOO_LARGE, e.error);
        }
        Inc bomb = new Inc().standard();
        bomb.rawPayload = new byte[(int) IncrementReader.MAX_INFLATED_BYTES + 1];
        expect(bomb, BackupError.INCREMENT_TOO_LARGE);
        // Control: exactly at the cap inflates, and is then refused for not being a ZIP.
        Inc atCap = new Inc().standard();
        atCap.rawPayload = new byte[(int) IncrementReader.MAX_INFLATED_BYTES];
        expect(atCap, BackupError.INCREMENT_FORMAT_UNKNOWN);
        // The ZIP's entries summed: small compressed, over the cap once read — refused mid-ZIP.
        Inc padded = new Inc().standard();
        padded.paddingEntryBytes = (int) IncrementReader.MAX_INFLATED_BYTES;
        expect(padded, BackupError.INCREMENT_TOO_LARGE);
        assertEquals("the cap is 8 MiB", 8L * 1024 * 1024, IncrementReader.MAX_INFLATED_BYTES);
    }

    @Test public void anUnfamiliarPayloadWithTheRightKeyIsAFormatChangeNotAWrongKey() throws Exception {
        Inc changed = new Inc();
        changed.containerPayload = "a newer compression, not zlib".getBytes(StandardCharsets.UTF_8);
        expect(changed, BackupError.INCREMENT_FORMAT_UNKNOWN);
        File f = changed.write(tmp.newFile());
        try {
            IncrementReader.read(f, 1, BackupKey.fromRoot(filled(32, 0x43)));
            fail("wrong key accepted");
        } catch (BackupException e) {
            assertEquals("the tag fails as well: the key is wrong", BackupError.WRONG_KEY, e.error);
        }
    }

    @Test public void aMillisecondShapedTimeIsRefused() throws Exception {
        Inc ms = new Inc();
        ms.chat(ALICE, msg(ALICE, 0, "KEYM1", T * 1000, null, content(1, "some words"), 1));
        BackupException e = expect(ms, BackupError.INCREMENT_FORMAT_UNKNOWN);
        assertTrue(e.getMessage(), e.getMessage().contains("1.3"));
        Inc edge = new Inc();
        edge.chat(ALICE, msg(ALICE, 0, "KEYM2", IncrementReader.MS_SHAPED_SECONDS - 1, null, content(1, "some words"), 2));
        assertEquals(1, IncrementReader.read(edge.write(tmp.newFile()), 1, key()).messages.size());
    }

    @Test public void aCrypt14NewerThanTheBaseIsRefusedAndTheSetGivesItsWriteTime() throws Exception {
        File dir = tmp.newFolder("Databases");
        touch(dir, "msgstore.db.crypt15", 1_000_000L);
        touch(dir, "msgstore-increment-1.db.crypt15", 3_000_000L);
        touch(dir, "msgstore-increment-2.db.crypt15", 2_000_000L);
        touch(dir, "msgstore-increment-3-2026-11-17.1.db.crypt15", 9_000_000L); // rotated: not in the live set
        IncrementSet s = IncrementSet.locate(dir);
        assertEquals("the newest of the base and its increments", 3_000_000L, s.newestWriteMs());

        File c14 = touch(dir, "msgstore-2026-11-20.1.db.crypt14", 999_000L);
        assertEquals("an older crypt14 is history", 2, IncrementSet.locate(dir).increments.size());
        assertTrue(c14.setLastModified(1_000_000L));
        assertEquals("as old as the base: still read", 2, IncrementSet.locate(dir).increments.size());
        assertTrue(c14.setLastModified(1_001_000L)); // newer than the base, older than the increments
        try {
            IncrementSet.locate(dir);
            fail("a crypt14 newer than the base was read past");
        } catch (BackupException e) {
            assertEquals(BackupError.CRYPT14_END_TO_END_OFF, e.error);
        }
    }

    private static File touch(File dir, String name, long mtime) throws IOException {
        File f = new File(dir, name);
        if (!f.exists()) assertTrue(f.createNewFile());
        assertTrue(f.setLastModified(mtime));
        return f;
    }

    @Test public void wrongKeyAndDamageAreToldApart() throws Exception {
        File f = new Inc().standard().write(tmp.newFile());
        try {
            IncrementReader.read(f, 1, BackupKey.fromRoot(filled(32, 0x43)));
            fail("wrong key accepted");
        } catch (BackupException e) {
            assertEquals(BackupError.WRONG_KEY, e.error);
        }
        byte[] b = Files.readAllBytes(f.toPath());
        b[b.length - 20] ^= 1; // inside the tag
        Files.write(f.toPath(), b);
        try {
            IncrementReader.read(f, 1, key());
            fail("damaged tag accepted");
        } catch (BackupException e) {
            assertEquals(BackupError.INTEGRITY, e.error);
        }
    }

    @Test public void refusalsCarryNoContent() throws Exception {
        Inc noKey = new Inc();
        noKey.chat(ALICE, msg(ALICE, 0, "KEYSECRET", T, null, content(1, "secret words"), 5), msgWithoutKeyId(ALICE, T, 7));
        BackupException e = expect(noKey, BackupError.INCREMENT_MISSING_PART);
        for (String leak : new String[]{"KEYSECRET", "secret", "447700900123", "whatsapp.net"}) {
            assertFalse(leak + " in " + e.getMessage(), e.getMessage().contains(leak));
        }
    }

    // ---- the synthetic increment --------------------------------------------------------------

    private BackupException expect(Inc inc, BackupError want) throws Exception {
        try {
            IncrementReader.read(inc.write(tmp.newFile()), 1, key());
            fail("expected " + want.code);
            return null;
        } catch (BackupException e) {
            assertEquals(e.getMessage(), want, e.error);
            return e;
        }
    }

    private static BackupKey key() {
        return BackupKey.fromRoot(ROOT.clone());
    }

    /** Builder for one increment, in the shapes of § 12. */
    static final class Inc {
        final List<byte[]> chats = new ArrayList<>();
        final List<String> jidRows = new ArrayList<>(), jidMapRows = new ArrayList<>();
        List<Long> deletedMessages = new ArrayList<>();
        String formatVersion = "1.0", messagesFormat = "protobuf", jidMapIdField = "lid_row_id";
        boolean topLevelExtras, omitAddedMessages, omitMessagesBin, omitDeletedFile, omitDeletedList, brokenJidJson,
                omitJidDeletedFile, omitJidModifiedFile;
        int truncateMessagesBin;
        /** Zero bytes in an extra ZIP entry, read before messages.bin. */
        int paddingEntryBytes;
        /** Zlib'd in place of the ZIP. */
        byte[] rawPayload;
        /** Encrypted as is, with no zlib: the container's payload itself. */
        byte[] containerPayload;

        Inc standard() {
            chat(ALICE, msg(ALICE, 0, "KEYS1", T, null, content(1, "standard words"), 1));
            return this;
        }

        void chat(String jid, byte[]... messages) {
            ByteArrayOutputStream c = new ByteArrayOutputStream();
            text(c, 1, jid);
            for (byte[] m : messages) bytes(c, 2, m);
            varint(c, 6, 3); // an unread-count-shaped field: ignored
            chats.add(c.toByteArray());
        }

        byte[] messagesBin() {
            ByteArrayOutputStream rec = new ByteArrayOutputStream();
            varint(rec, 1, 0);
            for (byte[] c : chats) bytes(rec, 2, c);
            if (topLevelExtras) {
                ByteArrayOutputStream pair = new ByteArrayOutputStream();
                text(pair, 1, ALICE_LID);
                text(pair, 2, ALICE);
                bytes(rec, 15, pair.toByteArray());
                varint(rec, 5, 1);
            }
            byte[] r = rec.toByteArray();
            ByteArrayOutputStream f = new ByteArrayOutputStream();
            writeVarint(f, r.length);
            f.write(r, 0, r.length);
            byte[] out = f.toByteArray();
            return truncateMessagesBin > 0 ? Arrays.copyOf(out, out.length - truncateMessagesBin) : out;
        }

        String header() {
            StringBuilder h = new StringBuilder("{\"header\":{\"creation_date\":1763776800000,\"os\":\"Android\",\"os_version\":\"13\","
                    + "\"app_name\":\"WhatsApp\",\"app_version\":\"2.25.99.99\",\"format_version\":\"" + formatVersion + "\"}");
            if (!omitAddedMessages) {
                h.append(",\"added_messages\":{\"filename\":\"messages.bin\",\"format\":\"").append(messagesFormat)
                        .append("\",\"messages_count_on_backup\":52031,\"messages_updated\":83,\"messages_deleted\":")
                        .append(deletedMessages.size()).append(",\"chunks\":[{\"chunk_number\":0,\"messages_count\":83}]}");
            }
            if (!deletedMessages.isEmpty() && !omitDeletedList) h.append(",\"deleted_messages\":{\"deleted_message_ids_files\":[\"deletedMessages_1.json\"]}");
            else h.append(",\"deleted_messages\":{}"); // as observed on a night with no deletions
            h.append(",\"entities\":{\"jid\":[{\"table_name\":\"jid\",\"table_id_field\":\"_id\",\"modified_entity_files\":[\"jid_modified_1.json\"],"
                    + "\"deleted_id_files\":[\"jid_deleted_1.json\"],\"records_count_in_db\":122867}],"
                    + "\"lid\":[{\"table_name\":\"jid_map\",\"table_id_field\":\"" + jidMapIdField + "\",\"modified_entity_files\":[\"jid_map_modified_1.json\"],"
                    + "\"records_count_in_db\":9800}],"
                    + "\"receipt\":[{\"table_name\":\"receipt_user\",\"table_id_field\":\"_id\",\"modified_entity_files\":[\"receipt_user_modified_1.json\"],"
                    + "\"records_count_in_db\":164}],\"away_messages\":[]}}");
            return h.toString();
        }

        byte[] zip() throws IOException {
            Map<String, String> json = new LinkedHashMap<>();
            json.put("header.json", header());
            json.put("sequences.json", "[{\"name\":\"message\",\"value\":57035}]");
            StringBuilder jid = new StringBuilder("{\"jid\":[");
            for (int i = 0; i < jidRows.size(); i++) jid.append(i == 0 ? "" : ",").append(jidRows.get(i));
            if (!omitJidModifiedFile) json.put("jid_modified_1.json", brokenJidJson ? "{\"jid\":[{\"_id\":1," : jid.append("]}").toString());
            if (!omitJidDeletedFile) json.put("jid_deleted_1.json", "{\"deleted_ids\":[950]}");
            StringBuilder map = new StringBuilder("{\"jid_map\":[");
            for (int i = 0; i < jidMapRows.size(); i++) map.append(i == 0 ? "" : ",").append(jidMapRows.get(i));
            json.put("jid_map_modified_1.json", map.append("]}").toString());
            json.put("receipt_user_modified_1.json", "{\"receipt_user\":[{\"_id\":1}]}");
            if (!deletedMessages.isEmpty() && !omitDeletedFile) {
                StringBuilder d = new StringBuilder("{\"deleted_ids\":[");
                for (int i = 0; i < deletedMessages.size(); i++) d.append(i == 0 ? "" : ",").append(deletedMessages.get(i));
                json.put("deletedMessages_1.json", d.append("]}").toString());
            }
            ByteArrayOutputStream bo = new ByteArrayOutputStream();
            try (ZipOutputStream z = new ZipOutputStream(bo)) {
                for (Map.Entry<String, String> e : json.entrySet()) {
                    z.putNextEntry(new ZipEntry(e.getKey()));
                    z.write(e.getValue().getBytes(StandardCharsets.UTF_8));
                    z.closeEntry();
                }
                if (paddingEntryBytes > 0) {
                    z.putNextEntry(new ZipEntry("padding.bin"));
                    z.write(new byte[paddingEntryBytes]);
                    z.closeEntry();
                }
                if (!omitMessagesBin) {
                    z.putNextEntry(new ZipEntry("messages.bin"));
                    z.write(messagesBin());
                    z.closeEntry();
                }
            }
            return bo.toByteArray();
        }

        File write(File f) throws Exception {
            byte[] payload = containerPayload != null ? containerPayload : zlib(rawPayload != null ? rawPayload : zip());
            byte[] aes = BackupKey.hkdfSha256(new byte[32], ROOT, "backup encryption".getBytes(StandardCharsets.US_ASCII), 32);
            byte[] c15 = concat(new byte[]{0x0a, 16}, IV);
            byte[] header = concat(new byte[]{0x08, 0x00, 0x1a, (byte) c15.length}, c15);
            Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
            c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(aes, "AES"), new GCMParameterSpec(128, IV));
            byte[] body = concat(new byte[]{(byte) header.length, 0x01}, header, c.doFinal(payload));
            body = concat(body, MessageDigest.getInstance("MD5").digest(body));
            Files.write(f.toPath(), body);
            return f;
        }
    }

    static String jidRow(long id, String raw) {
        return "{\"_id\":" + id + ",\"user\":\"" + raw.substring(0, raw.indexOf('@')) + "\",\"server\":\"lid\",\"agent\":0,\"device\":0,\"type\":0,\"raw_string\":\"" + raw + "\"}";
    }

    static String linkRow(long lid, long jid) {
        return "{\"lid_row_id\":" + lid + ",\"jid_row_id\":" + jid + ",\"sort_id\":1276328}";
    }

    /** {1 info {1 key {1 jid, 2 from-me, 3 key_id}, 2 content, 3 seconds, 5 sender, 41 reaction-shaped}, 2 row id} */
    static byte[] msg(String keyJid, int fromMe, String keyId, long seconds, String sender, byte[] content, long rowId) {
        ByteArrayOutputStream key = new ByteArrayOutputStream();
        text(key, 1, keyJid);
        varint(key, 2, fromMe);
        text(key, 3, keyId);
        ByteArrayOutputStream info = new ByteArrayOutputStream();
        bytes(info, 1, key.toByteArray());
        if (content != null) bytes(info, 2, content);
        varint(info, 3, seconds);
        if (sender != null) text(info, 5, sender);
        ByteArrayOutputStream reaction = new ByteArrayOutputStream();
        text(reaction, 2, "ok");
        bytes(info, 41, reaction.toByteArray());
        ByteArrayOutputStream m = new ByteArrayOutputStream();
        bytes(m, 1, info.toByteArray());
        varint(m, 2, rowId);
        return m.toByteArray();
    }

    static byte[] msgWithoutKeyId(String keyJid, long seconds, long rowId) {
        ByteArrayOutputStream key = new ByteArrayOutputStream();
        text(key, 1, keyJid);
        varint(key, 2, 0);
        ByteArrayOutputStream info = new ByteArrayOutputStream();
        bytes(info, 1, key.toByteArray());
        varint(info, 3, seconds);
        ByteArrayOutputStream m = new ByteArrayOutputStream();
        bytes(m, 1, info.toByteArray());
        varint(m, 2, rowId);
        return m.toByteArray();
    }

    static byte[] content(int field, String t) {
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        text(c, field, t);
        return c.toByteArray();
    }

    /** content {f {g text}} — e.g. 1.2.6.1, with a 1.2.6.2 decoy beside it. */
    static byte[] content2(int f, int g, String t) {
        ByteArrayOutputStream inner = new ByteArrayOutputStream();
        text(inner, g, t);
        text(inner, 2, "a link title, not the text");
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        bytes(c, f, inner.toByteArray());
        return c.toByteArray();
    }

    /** A media-shaped content block with its caption at 1.2.3.3. */
    static byte[] caption(String t) {
        ByteArrayOutputStream media = new ByteArrayOutputStream();
        text(media, 1, "https://example.invalid/media");
        text(media, 3, t);
        bytes(media, 4, filled(32, 0x11));
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        bytes(c, 3, media.toByteArray());
        return c.toByteArray();
    }

    /** Text at 1.2.12.14.6.1, the deepest adopted path. */
    static byte[] nested(String t) {
        ByteArrayOutputStream six = new ByteArrayOutputStream();
        text(six, 1, t);
        ByteArrayOutputStream fourteen = new ByteArrayOutputStream();
        bytes(fourteen, 6, six.toByteArray());
        ByteArrayOutputStream twelve = new ByteArrayOutputStream();
        bytes(twelve, 14, fourteen.toByteArray());
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        bytes(c, 12, twelve.toByteArray());
        return c.toByteArray();
    }

    /** Only the paths § 12 did not adopt: 1.2.6.2 (alone) and a 1.26-shaped field inside content. */
    static byte[] decoys() {
        ByteArrayOutputStream six = new ByteArrayOutputStream();
        text(six, 2, "a link title only");
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        bytes(c, 6, six.toByteArray());
        text(c, 26, "not text either");
        return c.toByteArray();
    }

    static void writeVarint(ByteArrayOutputStream o, long v) {
        while ((v & ~0x7fL) != 0) {
            o.write((int) ((v & 0x7f) | 0x80));
            v >>>= 7;
        }
        o.write((int) v);
    }

    static void varint(ByteArrayOutputStream o, int field, long v) {
        writeVarint(o, (long) field << 3);
        writeVarint(o, v);
    }

    static void bytes(ByteArrayOutputStream o, int field, byte[] d) {
        writeVarint(o, ((long) field << 3) | 2);
        writeVarint(o, d.length);
        o.write(d, 0, d.length);
    }

    static void text(ByteArrayOutputStream o, int field, String s) {
        bytes(o, field, s.getBytes(StandardCharsets.UTF_8));
    }

    static byte[] zlib(byte[] data) {
        Deflater d = new Deflater(1);
        d.setInput(data);
        d.finish();
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        while (!d.finished()) bo.write(buf, 0, d.deflate(buf));
        d.end();
        return bo.toByteArray();
    }

    static byte[] concat(byte[]... parts) {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        for (byte[] p : parts) bo.write(p, 0, p.length);
        return bo.toByteArray();
    }

    static byte[] filled(int n, int v) {
        byte[] b = new byte[n];
        Arrays.fill(b, (byte) v);
        return b;
    }
}
