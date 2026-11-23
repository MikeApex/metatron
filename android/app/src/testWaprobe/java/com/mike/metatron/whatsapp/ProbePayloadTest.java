package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertNull;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import org.junit.Before;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.List;
import java.util.zip.CRC32;
import java.util.zip.Deflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipOutputStream;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

/**
 * ProbePayload on synthetic crypt15 files built from our own reading of the format description
 * § 3 (as BackupReaderTest does). Each case first confirms the READER refuses the file as
 * not_a_message_database — so the probe is tested on exactly the refusal seen on the phone — then
 * checks the probe names the branch and reports what is inside, and leaves nothing behind.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'
 */
public class ProbePayloadTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();
    private File work;
    private byte[] root;

    @Before public void setUp() throws Exception {
        work = tmp.newFolder("wa_probe");
        root = new byte[32];
        Arrays.fill(root, (byte) 0x42);
    }

    @Test public void zipPayloadIsTheDecideBranchAndListsItsEntries() throws Exception {
        byte[] zip = zip(new Object[][]{
                {"msgstore.db", fakeDatabase(5000), ZipEntry.DEFLATED},
                {"media/447700900123.txt", "not sqlite".getBytes(StandardCharsets.US_ASCII), ZipEntry.STORED}});
        File f = crypt15(zip, true);
        expectReaderRefuses(f);

        ProbePayload.Inspection r = ProbePayload.inspect(f, key(), work);
        assertTrue(r.tagOk);
        assertTrue(r.md5Trailer);
        assertEquals("zip", r.kind);
        assertTrue(r.branch, r.branch.contains("decide()"));
        assertEquals("50 4b 03 04", r.payloadHead8.substring(0, 11));
        assertEquals("payload", r.zipIn);
        assertEquals(2, r.entryCount);
        assertEquals(2, r.entries.size());

        ProbePayload.Entry db = r.entries.get(0), other = r.entries.get(1);
        assertEquals("msgstore.db", db.name);
        assertEquals(5000, db.size);
        assertTrue(db.sqlite);
        assertNotNull(db.extracted);
        assertEquals(5000, db.extracted.length());
        assertTrue(db.extracted.getName().startsWith(ProbePayload.PREFIX));
        assertFalse(other.sqlite);
        assertNull(other.extracted);
        assertEquals("media/#{12}.txt", other.name); // digit runs never shown
        assertEquals(1, r.sqliteEntries().size());

        String text = report(r);
        assertTrue(text, text.contains("SQLite: YES"));
        assertFalse(text, text.contains("447700900123"));
        assertFalse(text, text.contains("not sqlite")); // entry contents never shown

        assertEquals(0, ProbePayload.sweep(work));
        assertEquals(0, work.listFiles().length);
    }

    @Test public void inflatedNonSqliteIsTheFinishBranchWithSizeAndMagic() throws Exception {
        byte[] inner = new byte[3000];
        for (int i = 0; i < inner.length; i++) inner[i] = (byte) (i * 7);
        inner[0] = 0x11; inner[1] = 0x22; inner[2] = 0x33;
        File f = crypt15(zlib(inner), true);
        expectReaderRefuses(f);

        ProbePayload.Inspection r = ProbePayload.inspect(f, key(), work);
        assertEquals("zlib", r.kind);
        assertTrue(r.branch, r.branch.contains("finish()"));
        assertNull(r.inflateError);
        assertEquals(3000, r.inflatedBytes);
        assertEquals(0, r.trailingAfterZlib);
        assertTrue(r.inflatedHead16, r.inflatedHead16.startsWith("11 22 33"));
        assertEquals(16, r.inflatedHead16.split(" ").length);
        assertNull(r.zipIn);
        assertTrue(r.sqliteEntries().isEmpty());
        assertEquals(0, ProbePayload.sweep(work));
    }

    @Test public void zipInsideZlibIsListedFromTheInflatedOutput() throws Exception {
        byte[] zip = zip(new Object[][]{{"increment.db", fakeDatabase(2000), ZipEntry.DEFLATED}});
        File f = crypt15(zlib(zip), false); // and the no-trailer container form
        expectReaderRefuses(f);

        ProbePayload.Inspection r = ProbePayload.inspect(f, key(), work);
        assertFalse(r.md5Trailer);
        assertEquals("zlib", r.kind);
        assertTrue(r.branch, r.branch.contains("finish()"));
        assertEquals("inflated output", r.zipIn);
        assertEquals(1, r.entryCount);
        List<ProbePayload.Entry> dbs = r.sqliteEntries();
        assertEquals(1, dbs.size());
        assertEquals(2000, dbs.get(0).extracted.length());
        assertEquals(0, ProbePayload.sweep(work));
    }

    @Test public void moreSqliteEntriesThanTheCapAreListedNotExtracted() throws Exception {
        Object[][] entries = new Object[ProbePayload.MAX_SQLITE_ENTRIES + 2][];
        for (int i = 0; i < entries.length; i++) entries[i] = new Object[]{"part" + i + ".db", fakeDatabase(100 + i), ZipEntry.DEFLATED};
        ProbePayload.Inspection r = ProbePayload.inspect(crypt15(zip(entries), true), key(), work);
        assertEquals(entries.length, r.entries.size());
        assertEquals(ProbePayload.MAX_SQLITE_ENTRIES, r.sqliteEntries().size());
        assertTrue(report(r).contains("over the cap"));
        assertEquals(0, ProbePayload.sweep(work));
    }

    @Test public void aFailedTagDiscardsThePlaintextUnread() throws Exception {
        File f = crypt15(zip(new Object[][]{{"msgstore.db", fakeDatabase(1000), ZipEntry.DEFLATED}}), false);
        byte[] b = Files.readAllBytes(f.toPath());
        b[b.length - 1] ^= 1; // the tag
        Files.write(f.toPath(), b);

        ProbePayload.Inspection r = ProbePayload.inspect(f, key(), work);
        assertFalse(r.tagOk);
        assertTrue(r.entries.isEmpty());
        assertEquals("", r.payloadHead8);
        assertEquals(0, work.listFiles().length);
        assertTrue(report(r).contains("FAILED"));
    }

    @Test public void sweepTouchesOnlyItsOwnFiles() throws Exception {
        File key = new File(work, "wa_key.bin");
        File events = new File(work, "live.jsonl");
        assertTrue(key.createNewFile());
        assertTrue(events.createNewFile());
        assertTrue(new File(work, ProbePayload.PREFIX + "entry1.db-wal").createNewFile());
        assertEquals(0, ProbePayload.sweep(work));
        assertTrue(key.exists());
        assertTrue(events.exists());
        assertEquals(2, work.listFiles().length);
    }

    @Test public void hexAndMaskHelpers() {
        assertEquals("50 4b 03 04", ProbePayload.hex(new byte[]{'P', 'K', 3, 4, 9}, 4));
        assertEquals("(empty)", ProbePayload.hex(new byte[0], 8));
        assertEquals("a/#{6}/b12345", ProbePayload.maskDigits("a/123456/b12345"));
    }

    // ---- helpers -----------------------------------------------------------------------

    private BackupKey key() {
        return BackupKey.fromRoot(root.clone());
    }

    private void expectReaderRefuses(File f) throws Exception {
        File out = new File(tmp.getRoot(), "reader-out.db");
        try {
            BackupDecryptor.decrypt(f, key(), out, dir -> Long.MAX_VALUE);
            fail("the reader accepted it");
        } catch (BackupException e) {
            assertEquals(BackupError.NOT_A_MESSAGE_DATABASE, e.error);
        }
        assertFalse(out.exists());
    }

    private static String report(ProbePayload.Inspection r) {
        StringBuilder b = new StringBuilder();
        ProbePayload.lines(r, b);
        return b.toString();
    }

    /** A crypt15 file: [len][marker] header{version, c15{iv}}, AES-GCM(payload)+tag, optional MD5. */
    private File crypt15(byte[] payload, boolean md5Trailer) throws Exception {
        byte[] aes = BackupKey.hkdfSha256(new byte[32], root, "backup encryption".getBytes(StandardCharsets.US_ASCII), 32);
        byte[] iv = new byte[16];
        Arrays.fill(iv, (byte) 0x24);
        byte[] c15 = concat(new byte[]{0x0a, 16}, iv);
        byte[] header = concat(new byte[]{0x08, 0x00, 0x1a, (byte) c15.length}, c15);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(aes, "AES"), new GCMParameterSpec(128, iv));
        byte[] body = concat(new byte[]{(byte) header.length, 0x01}, header, c.doFinal(payload));
        if (md5Trailer) body = concat(body, MessageDigest.getInstance("MD5").digest(body));
        File f = tmp.newFile();
        Files.write(f.toPath(), body);
        return f;
    }

    /** {name, bytes, method} rows. */
    private static byte[] zip(Object[][] entries) throws Exception {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        try (ZipOutputStream z = new ZipOutputStream(bo)) {
            for (Object[] e : entries) {
                byte[] data = (byte[]) e[1];
                ZipEntry ze = new ZipEntry((String) e[0]);
                int method = (Integer) e[2];
                ze.setMethod(method);
                if (method == ZipEntry.STORED) {
                    CRC32 crc = new CRC32();
                    crc.update(data);
                    ze.setSize(data.length);
                    ze.setCompressedSize(data.length);
                    ze.setCrc(crc.getValue());
                }
                z.putNextEntry(ze);
                z.write(data);
                z.closeEntry();
            }
        }
        return bo.toByteArray();
    }

    private static byte[] fakeDatabase(int size) {
        byte[] db = new byte[size];
        System.arraycopy(BackupDecryptor.SQLITE_HEADER, 0, db, 0, 16);
        for (int i = 16; i < size; i++) db[i] = (byte) ('a' + i % 8);
        return db;
    }

    private static byte[] zlib(byte[] data) {
        Deflater d = new Deflater(1);
        d.setInput(data);
        d.finish();
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        byte[] buf = new byte[8192];
        while (!d.finished()) bo.write(buf, 0, d.deflate(buf));
        d.end();
        return bo.toByteArray();
    }

    private static byte[] concat(byte[]... parts) {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        for (byte[] p : parts) bo.write(p, 0, p.length);
        return bo.toByteArray();
    }
}
