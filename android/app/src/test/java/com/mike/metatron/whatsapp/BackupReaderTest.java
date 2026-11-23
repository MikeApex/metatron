package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
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
import java.util.TreeMap;
import java.util.zip.Deflater;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.junit.AfterClass;
import org.junit.Before;
import org.junit.BeforeClass;
import org.junit.Rule;
import org.junit.Test;
import org.junit.rules.TemporaryFolder;

/**
 * Phase 0b's acceptance suite: every entry in tests/fixtures/whatsapp_backup/expected.json,
 * then the refusals the vectors cannot reach. Each test records which row of the format
 * description's § 7 (and § 6) it covers; the coverage table is written to
 * build/reports/whatsapp_backup_coverage.txt and printed.
 */
public class BackupReaderTest {
    @Rule public TemporaryFolder tmp = new TemporaryFolder();

    private static File fixtures;
    private static Map<String, Object> expected;
    private static final Map<String, List<String>> COVERAGE = new LinkedHashMap<>();
    private static final BackupDecryptor.SpaceProbe PLENTY = dir -> Long.MAX_VALUE;

    static {
        String[] rows = {
                "§7 crypt15 single-file, zlib, marker byte -> handle",
                "§7 crypt15 uncompressed SQLite -> handle",
                "§7 crypt15 no-trailer form -> handle (tag still verified)",
                "§7 crypt15 older header -> handle",
                "§7 crypt15 without marker byte -> handle",
                "§7 crypt15 ZIP payload -> not_a_message_database",
                "§7 crypt14 -> crypt14_end_to_end_off",
                "§7 crypt12 / unparseable header -> unknown_format",
                "§7 password-protected backup -> refuse at key entry",
                "§7 WhatsApp Business -> out of scope",
                "§7 file being written -> being_written",
                "§7 not enough free space -> insufficient_space",
                "§6.2 wrong key -> wrong_key",
                "§6.2 right key, unfamiliar payload -> unknown_format",
                "§6.2 tag or MD5 failure -> integrity",
                "§6.2 decompression ends early -> truncated",
                "§6.3 key input (64 hex, separators, case) -> key_format",
                "§6.5 stream, temp file, delete on failure",
                "§6.7 schema drift -> schema_changed",
        };
        for (String r : rows) COVERAGE.put(r, new ArrayList<>());
        COVERAGE.get("§7 password-protected backup -> refuse at key entry").add(
                "NOT TESTABLE FROM A FILE (§2: indistinguishable on disk). Handled by the key screen's text, "
                        + "which tells the user to choose the 64-digit option; any non-64-hex entry is key_format (tested)");
    }

    private static void covered(String row, String by) {
        List<String> l = COVERAGE.get(row);
        if (l == null) throw new IllegalStateException("unknown coverage row " + row);
        synchronized (COVERAGE) { l.add(by); }
    }

    @BeforeClass
    @SuppressWarnings("unchecked")
    public static void loadFixtures() throws IOException {
        File dir = new File(System.getProperty("user.dir")).getAbsoluteFile();
        while (dir != null && !new File(dir, "tests/fixtures/whatsapp_backup/expected.json").isFile()) {
            dir = dir.getParentFile();
        }
        if (dir == null) throw new IllegalStateException("tests/fixtures/whatsapp_backup not found above user.dir");
        fixtures = new File(dir, "tests/fixtures/whatsapp_backup");
        expected = (Map<String, Object>) MiniJson.parse(
                new String(Files.readAllBytes(new File(fixtures, "expected.json").toPath()), StandardCharsets.UTF_8));
    }

    private File dest;

    @Before
    public void setUp() throws IOException {
        dest = new File(tmp.newFolder("no_backup"), "msgstore.db");
    }

    // ---- every vector in expected.json -------------------------------------------------

    @Test
    @SuppressWarnings("unchecked")
    public void everyVectorInExpectedJson() throws Exception {
        Map<String, String> keys = (Map<String, String>) expected.get("keys");
        Map<String, Object> vectors = (Map<String, Object>) expected.get("vectors");
        assertEquals("expected.json vector count", 14, vectors.size());
        StringBuilder failures = new StringBuilder();
        for (Map.Entry<String, Object> e : vectors.entrySet()) {
            Map<String, Object> v = (Map<String, Object>) e.getValue();
            String fileName = v.containsKey("file") ? (String) v.get("file") : e.getKey();
            File src = new File(fixtures, fileName);
            BackupKey key = BackupKey.fromDigits(keys.get((String) v.get("key")));
            File out = new File(dest.getParentFile(), e.getKey().replace('#', '_') + ".db");
            String outcome;
            try {
                BackupDecryptor.Result r = BackupDecryptor.decrypt(src, key, out, PLENTY);
                outcome = "ok sha256=" + sha256(r.database);
                assertEquals(r.decryptedBytes, r.database.length());
            } catch (BackupException ex) {
                outcome = ex.error.code;
                assertFalse(e.getKey() + ": no output after refusal", out.exists());
                assertFalse(e.getKey() + ": no partial after refusal", new File(out.getPath() + ".partial").exists());
            } finally {
                key.destroy();
            }
            boolean pass;
            if (Boolean.TRUE.equals(v.get("ok"))) {
                pass = outcome.equals("ok sha256=" + v.get("sha256"));
            } else {
                List<Object> alt = (List<Object>) v.get("also_acceptable");
                pass = outcome.equals(v.get("error")) || (alt != null && alt.contains(outcome));
            }
            System.out.println("VECTOR " + (pass ? "PASS " : "FAIL ") + e.getKey() + " -> " + outcome);
            if (!pass) failures.append(e.getKey()).append(" got ").append(outcome).append('\n');
            else recordVector(e.getKey(), outcome);
        }
        if (failures.length() > 0) fail("vectors failed:\n" + failures);
    }

    private static void recordVector(String name, String outcome) {
        String by = "vector " + name + " (" + (outcome.startsWith("ok") ? "sha256 match" : outcome) + ")";
        if (name.startsWith("v01_standard.crypt15#")) covered("§6.2 wrong key -> wrong_key", by);
        else if (name.startsWith("v01") || name.startsWith("v02")) covered("§7 crypt15 single-file, zlib, marker byte -> handle", by);
        else if (name.startsWith("v03")) covered("§7 crypt15 uncompressed SQLite -> handle", by);
        else if (name.startsWith("v04")) covered("§7 crypt15 no-trailer form -> handle (tag still verified)", by);
        else if (name.startsWith("v05")) covered("§7 crypt15 older header -> handle", by);
        else if (name.startsWith("v06")) covered("§7 crypt15 without marker byte -> handle", by);
        else if (name.startsWith("r01") || name.startsWith("r02") || name.startsWith("r03")) covered("§6.2 tag or MD5 failure -> integrity", by);
        else if (name.startsWith("r04")) covered("§6.2 decompression ends early -> truncated", by);
        else if (name.startsWith("r05")) covered("§7 crypt14 -> crypt14_end_to_end_off", by);
        else if (name.startsWith("r06")) covered("§7 crypt12 / unparseable header -> unknown_format", by);
        else if (name.startsWith("r07")) covered("§7 crypt15 ZIP payload -> not_a_message_database", by);
        if (!outcome.startsWith("ok")) covered("§6.5 stream, temp file, delete on failure", "vector " + name + ": no output, no .partial");
    }

    // ---- key input ---------------------------------------------------------------------

    @Test
    @SuppressWarnings("unchecked")
    public void keyAcceptsSpacesDashesAndUpperCase() throws Exception {
        String a = ((Map<String, String>) expected.get("keys")).get("A");
        StringBuilder typed = new StringBuilder();
        for (int i = 0; i < 64; i += 4) typed.append(a.substring(i, i + 4).toUpperCase()).append(i % 8 == 0 ? " " : "-");
        BackupKey k = BackupKey.fromDigits(typed);
        BackupDecryptor.Result r = BackupDecryptor.decrypt(new File(fixtures, "v01_standard.crypt15"), k, dest, PLENTY);
        assertEquals("eac8c03184bdf0fbbd801c65dc8351af8be7b3efc54df922763ef13433894279", sha256(r.database));
        covered("§6.3 key input (64 hex, separators, case) -> key_format", "grouped, upper-case key decrypts v01");
    }

    @Test
    public void keyRefusals() {
        String[] bad = {"", "abc", repeat('a', 63), repeat('a', 65), repeat('a', 63) + "g", repeat('a', 62) + "/a", null};
        for (String s : bad) {
            try {
                BackupKey.fromDigits(s);
                fail("accepted " + (s == null ? "null" : s.length() + " chars"));
            } catch (BackupException e) {
                assertEquals(BackupError.KEY_FORMAT, e.error);
                assertFalse("no key material in message", s != null && s.length() > 3 && e.getMessage().contains(s));
            }
        }
        covered("§6.3 key input (64 hex, separators, case) -> key_format", "63/65 digits, non-hex, unexpected separator, empty, null");
    }

    @Test
    public void hkdfMatchesRfc5869TestCase1() throws Exception {
        byte[] ikm = new byte[22];
        Arrays.fill(ikm, (byte) 0x0b);
        byte[] salt = hex("000102030405060708090a0b0c");
        byte[] info = hex("f0f1f2f3f4f5f6f7f8f9");
        byte[] okm = BackupKey.hkdfSha256(salt, ikm, info, 42);
        assertEquals("3cb25f25faacd57a90434f64d0362f2a2d2d0a90cf1a5a4c5db02d56ecc4c5bf34007208d5b887185865", toHex(okm));
    }

    // ---- refusals the vectors do not reach ---------------------------------------------

    @Test
    @SuppressWarnings("unchecked")
    public void insufficientSpaceRefusesBeforeWriting() throws Exception {
        File src = new File(fixtures, "v01_standard.crypt15");
        BackupKey k = BackupKey.fromDigits(((Map<String, String>) expected.get("keys")).get("A"));
        long need = src.length() * BackupDecryptor.SPACE_FACTOR;
        try {
            BackupDecryptor.decrypt(src, k, dest, dir -> need - 1);
            fail("decrypted with too little space");
        } catch (BackupException e) {
            assertEquals(BackupError.INSUFFICIENT_SPACE, e.error);
        }
        assertFalse(new File(dest.getPath() + ".partial").exists());
        BackupDecryptor.decrypt(src, k, dest, dir -> need);
        assertTrue(dest.exists());
        covered("§7 not enough free space -> insufficient_space", "10x - 1 byte refused before any write; exactly 10x accepted");
    }

    @Test
    public void beingWrittenByRecentModification() throws Exception {
        File f = tmp.newFile("msgstore.db.crypt15");
        f.setLastModified(1_000_000_000_000L);
        long now = 1_000_000_000_000L + BackupLocator.RECENT_WRITE_MS - 1;
        expectBeingWritten(f, () -> now, ms -> {});
        long future = 1_000_000_000_000L - 60_000L;
        expectBeingWritten(f, () -> future, ms -> {});
        BackupLocator.requireComplete(f, () -> 1_000_000_000_000L + BackupLocator.RECENT_WRITE_MS, ms -> {});
        covered("§7 file being written -> being_written", "modified <10 min ago, and modified in the future: deferred; at 10 min: read");
    }

    @Test
    public void beingWrittenBySizeChange() throws Exception {
        File f = tmp.newFile("msgstore.db.crypt15");
        f.setLastModified(1_000_000_000_000L);
        expectBeingWritten(f, () -> 2_000_000_000_000L, ms -> {
            assertEquals(BackupLocator.SIZE_RECHECK_MS, ms);
            try (FileOutputStream o = new FileOutputStream(f, true)) { o.write(1); } catch (IOException e) { throw new RuntimeException(e); }
        });
        covered("§7 file being written -> being_written", "size changed across the 5 s look: deferred");
    }

    private static void expectBeingWritten(File f, BackupLocator.Clock c, BackupLocator.Sleeper s) throws InterruptedException {
        try {
            BackupLocator.requireComplete(f, c, s);
            fail("not deferred");
        } catch (BackupException e) {
            assertEquals(BackupError.BEING_WRITTEN, e.error);
        }
    }

    @Test
    public void locatorPicksNewestAndRefusesTheRest() throws Exception {
        File dir = tmp.newFolder("Databases");
        File current = touch(dir, "msgstore.db.crypt15", 2_000L);
        touch(dir, "msgstore-2026-10-25.1.db.crypt15", 1_000L);
        touch(dir, "msgstore-2026-10-26.2.db.crypt15", 9_000L); // not the named pattern — ignored
        touch(dir, "wa.db.crypt15", 9_000L);
        assertEquals(current, BackupLocator.newest(dir));
        File dated = touch(dir, "msgstore-2026-10-27.1.db.crypt15", 3_000L);
        assertEquals(dated, BackupLocator.newest(dir));
        touch(dir, "msgstore.db.crypt15", 3_000L);
        assertEquals("tie -> undated current file", current, BackupLocator.newest(dir));

        File only14 = tmp.newFolder("only14");
        touch(only14, "msgstore.db.crypt14", 1_000L);
        assertLocatorError(only14, BackupError.CRYPT14_END_TO_END_OFF);
        covered("§7 crypt14 -> crypt14_end_to_end_off", "a folder holding only msgstore.db.crypt14");

        // End-to-end switched off after the last crypt15: the crypt14 is newer, so the stale crypt15 is not read.
        File switchedOff = tmp.newFolder("switchedOff");
        File c15 = touch(switchedOff, "msgstore.db.crypt15", 2_000L);
        touch(switchedOff, "msgstore-2026-10-25.1.db.crypt15", 1_000L);
        File c14 = touch(switchedOff, "msgstore-2026-10-27.1.db.crypt14", 3_000L);
        assertLocatorError(switchedOff, BackupError.CRYPT14_END_TO_END_OFF);
        assertTrue(c14.setLastModified(2_000L));
        assertEquals("a crypt14 as old as the crypt15 does not block it", c15, BackupLocator.newest(switchedOff));
        assertTrue(c14.setLastModified(1_000L));
        assertEquals("an older crypt14 is history", c15, BackupLocator.newest(switchedOff));
        touch(switchedOff, "msgstore.db.crypt14", 3_000L);
        assertLocatorError(switchedOff, BackupError.CRYPT14_END_TO_END_OFF);
        covered("§7 crypt14 -> crypt14_end_to_end_off", "a crypt14 newer than the newest crypt15 (dated or current name); older or equal is read past");

        assertLocatorError(tmp.newFolder("empty"), BackupError.NO_BACKUP_FOUND);
        File biz = new File(tmp.getRoot(), "Android/media/com.whatsapp.w4b/WhatsApp Business/Databases");
        assertTrue(biz.mkdirs());
        touch(biz, "msgstore.db.crypt15", 1_000L);
        assertLocatorError(biz, BackupError.BUSINESS_OUT_OF_SCOPE);
        covered("§7 WhatsApp Business -> out of scope", "the com.whatsapp.w4b folder is refused, never read");
    }

    private static void assertLocatorError(File dir, BackupError want) {
        try {
            BackupLocator.newest(dir);
            fail("located a backup in " + dir.getName());
        } catch (BackupException e) {
            assertEquals(want, e.error);
        }
    }

    @Test
    public void headerRefusals() throws Exception {
        byte[] iv16 = new byte[16];
        // valid: field 3 { field 1: 16 bytes }
        byte[] c15 = concat(new byte[]{0x0a, 16}, iv16);
        byte[] good = concat(new byte[]{0x1a, (byte) c15.length}, c15);
        assertEquals(1 + good.length, BackupHeader.parse(prefix(good, false), 1 + good.length + 40).dataStart);
        BackupHeader marked = BackupHeader.parse(prefix(good, true), 2 + good.length + 40);
        assertTrue(marked.featureMarker);
        assertEquals(2 + good.length, marked.dataStart);
        // unknown fields are skipped: field 9 varint, field 10 fixed32, field 11 fixed64
        byte[] withUnknown = concat(good, new byte[]{0x48, 0x05, 0x55, 1, 2, 3, 4, 0x59, 1, 2, 3, 4, 5, 6, 7, 8});
        BackupHeader.parse(prefix(withUnknown, true), 200);

        byte[][] refuse = {
                new byte[0],                                                      // empty header
                {0x08, 0x01},                                                     // key_type only: neither 2 nor 3
                concat(good, new byte[]{0x12, 0x00}),                             // both crypt14 and crypt15 blocks
                concat(good, new byte[]{0x1a, (byte) c15.length}, c15),           // c15 twice
                concat(new byte[]{0x1a, 19, 0x0a, 16}, iv16),                     // length runs past the header
                {0x1a, 0x06, 0x0a, 0x04, 1, 2, 3, 4},                             // IV of 4 bytes, not 16
                concat(good, new byte[]{0x0b}),                                   // group wire type
                concat(good, new byte[]{0x00, 0x00}),                             // field 0
                {(byte) 0xff, (byte) 0xff},                                       // varint never ends
        };
        for (byte[] h : refuse) {
            try {
                BackupHeader.parse(prefix(h, true), 300);
                fail("parsed header " + toHex(h));
            } catch (BackupException e) {
                assertEquals(toHex(h), BackupError.UNKNOWN_FORMAT, e.error);
            }
        }
        try {
            BackupHeader.parse(prefix(new byte[]{0x12, 0x02, 0x0a, 0x00}, true), 300);
            fail("parsed a crypt14 header");
        } catch (BackupException e) {
            assertEquals(BackupError.CRYPT14_END_TO_END_OFF, e.error);
        }
        covered("§7 crypt12 / unparseable header -> unknown_format",
                "synthetic headers: empty, neither block, both blocks, duplicate, overrun, short IV, group, field 0, endless varint");
    }

    // ---- synthetic files for paths the vectors do not reach -----------------------------

    @Test
    public void trailingBytesAfterTheZlibStreamAreRefused() throws Exception {
        byte[] db = fakeDatabase(5000);
        byte[] payload = concat(zlib(db), new byte[]{0, 0, 0});
        expectSynthetic(payload, true, BackupError.INTEGRITY);
        expectSynthetic(zlib(db), true, null);  // control: same file without the extra bytes
        expectSynthetic(zlib(db), false, null); // and without the MD5 trailer
        covered("§6.2 tag or MD5 failure -> integrity", "synthetic: 3 bytes after a complete zlib stream refused");
    }

    @Test
    public void aZlibPayloadThatIsNotADatabaseIsRefused() throws Exception {
        expectSynthetic(zlib(new byte[4000]), true, BackupError.NOT_A_MESSAGE_DATABASE);
        covered("§7 crypt15 ZIP payload -> not_a_message_database", "synthetic: zlib of non-SQLite bytes refused too");
    }

    @Test
    public void anUnfamiliarPayloadWithTheRightKeyIsAFormatChangeNotAWrongKey() throws Exception {
        // Neither zlib, SQLite nor ZIP — as if WhatsApp changed the compression. ~200 KB, so the
        // decryptor must carry on through many buffers to reach the tag.
        byte[] payload = concat("NEWCOMPRESSION01".getBytes(StandardCharsets.US_ASCII), fakeDatabase(200_000));
        expectSynthetic(payload, true, BackupError.UNKNOWN_FORMAT);
        expectSynthetic(payload, false, BackupError.UNKNOWN_FORMAT); // no-trailer form: the held-back tail is ciphertext too
        byte[] tiny = "NEWFORMAT".getBytes(StandardCharsets.US_ASCII); // shorter than one block
        expectSynthetic(tiny, true, BackupError.UNKNOWN_FORMAT);
        byte[] otherRoot = new byte[32];
        Arrays.fill(otherRoot, (byte) 0x43);
        expectSynthetic(payload, true, BackupError.WRONG_KEY, otherRoot);
        expectSynthetic(payload, false, BackupError.WRONG_KEY, otherRoot);
        expectSynthetic(zlib(fakeDatabase(5000)), true, BackupError.WRONG_KEY, otherRoot);
        covered("§6.2 right key, unfamiliar payload -> unknown_format",
                "synthetic: tag verifies on a payload that is not zlib/SQLite/ZIP (with and without MD5, and under one block); "
                        + "the same with another key -> wrong_key");
        covered("§6.2 wrong key -> wrong_key", "synthetic: another key on an unfamiliar and on a zlib payload");
    }

    @Test
    public void aTinyFileIsRefusedNotMisread() throws Exception {
        // header followed by fewer than 16 bytes: no room for a tag
        byte[] c15 = concat(new byte[]{0x0a, 16}, new byte[16]);
        byte[] h = concat(new byte[]{0x1a, (byte) c15.length}, c15);
        File f = tmp.newFile("tiny.crypt15");
        Files.write(f.toPath(), concat(prefix(h, true), new byte[10]));
        try {
            BackupDecryptor.decrypt(f, BackupKey.fromDigits(repeat('a', 64)), dest, PLENTY);
            fail("decrypted a tiny file");
        } catch (BackupException e) {
            assertEquals(BackupError.TRUNCATED, e.error);
        }
        covered("§6.2 decompression ends early -> truncated", "synthetic: header with <16 bytes after it");
    }

    @Test
    public void largeFileStreamsThroughSmallBuffers() throws Exception {
        // ~3 MB of database through a 64 KB buffer: many keystream refills and inflate rounds.
        byte[] db = fakeDatabase(3_000_000);
        File out = expectSynthetic(zlib(db), true, null);
        assertTrue(Arrays.equals(db, Files.readAllBytes(out.toPath())));
        covered("§6.5 stream, temp file, delete on failure",
                "synthetic 3 MB database decrypts byte-exact through 64 KB buffers (plus v02, ~200 KB)");
    }

    @Test
    public void schemaDriftIsRefusedByName() {
        Map<String, Set<String>> actual = new TreeMap<>();
        for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) actual.put(e.getKey(), new HashSet<>(e.getValue()));
        try {
            SchemaCheck.require(actual);
        } catch (BackupException e) {
            fail("complete schema refused");
        }
        actual.get("message").remove("timestamp");
        actual.remove("jid_map");
        try {
            SchemaCheck.require(actual);
            fail("drifted schema accepted");
        } catch (BackupException e) {
            assertEquals(BackupError.SCHEMA_CHANGED, e.error);
            assertTrue(e.getMessage().contains("message.timestamp"));
            assertTrue(e.getMessage().contains("jid_map"));
        }
        covered("§6.7 schema drift -> schema_changed", "a missing column and a missing table are both named");
    }

    // ---- coverage table ----------------------------------------------------------------

    @AfterClass
    public static void writeCoverage() throws IOException {
        StringBuilder sb = new StringBuilder("WhatsApp backup reader — coverage against the format description\n\n");
        int uncovered = 0;
        for (Map.Entry<String, List<String>> e : COVERAGE.entrySet()) {
            boolean ok = !e.getValue().isEmpty();
            if (!ok) uncovered++;
            sb.append(ok ? "[x] " : "[ ] ").append(e.getKey()).append('\n');
            for (String by : e.getValue()) sb.append("      - ").append(by).append('\n');
        }
        sb.append('\n').append(uncovered == 0 ? "Every row covered." : uncovered + " row(s) without a test or a stated reason.").append('\n');
        File report = new File("build/reports/whatsapp_backup_coverage.txt");
        report.getParentFile().mkdirs();
        Files.write(report.toPath(), sb.toString().getBytes(StandardCharsets.UTF_8));
        System.out.println(sb);
    }

    // ---- helpers -----------------------------------------------------------------------

    /** Builds a crypt15 file from our own reading of § 3 and checks the reader's verdict (null = ok). */
    private File expectSynthetic(byte[] payload, boolean md5Trailer, BackupError want) throws Exception {
        return expectSynthetic(payload, md5Trailer, want, null);
    }

    /** As above, decrypting with {@code readRoot} instead of the key it was written with (null = the same key). */
    private File expectSynthetic(byte[] payload, boolean md5Trailer, BackupError want, byte[] readRoot) throws Exception {
        byte[] root = new byte[32];
        Arrays.fill(root, (byte) 0x42);
        byte[] aes = BackupKey.hkdfSha256(new byte[32], root, "backup encryption".getBytes(StandardCharsets.US_ASCII), 32);
        byte[] iv = new byte[16];
        Arrays.fill(iv, (byte) 0x24);
        byte[] c15 = concat(new byte[]{0x0a, 16}, iv);
        byte[] header = concat(new byte[]{0x08, 0x00, 0x1a, (byte) c15.length}, c15);
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(aes, "AES"), new GCMParameterSpec(128, iv));
        byte[] body = concat(prefix(header, true), c.doFinal(payload));
        if (md5Trailer) body = concat(body, MessageDigest.getInstance("MD5").digest(body));
        File f = tmp.newFile();
        Files.write(f.toPath(), body);
        File out = new File(dest.getParentFile(), f.getName() + ".db");
        try {
            BackupDecryptor.decrypt(f, BackupKey.fromDigits(toHex(readRoot != null ? readRoot : root)), out, PLENTY);
            if (want != null) fail("expected " + want.code);
        } catch (BackupException e) {
            if (want == null) throw e;
            assertEquals(want, e.error);
            assertFalse(out.exists());
            assertFalse(new File(out.getPath() + ".partial").exists());
        }
        return out;
    }

    private static byte[] fakeDatabase(int size) {
        byte[] db = new byte[size];
        System.arraycopy(BackupDecryptor.SQLITE_HEADER, 0, db, 0, 16);
        java.util.Random r = new java.util.Random(size);
        for (int i = 16; i < size; i++) db[i] = (byte) ("abcdefgh".charAt(r.nextInt(8)));
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

    private static byte[] prefix(byte[] header, boolean marker) {
        byte[] lead = marker ? new byte[]{(byte) header.length, 0x01} : new byte[]{(byte) header.length};
        return concat(lead, header);
    }

    private static File touch(File dir, String name, long mtime) throws IOException {
        File f = new File(dir, name);
        if (!f.exists()) assertTrue(f.createNewFile());
        assertTrue(f.setLastModified(mtime));
        return f;
    }

    private static String sha256(File f) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(f)) {
            byte[] b = new byte[65536];
            int n;
            while ((n = in.read(b)) > 0) md.update(b, 0, n);
        }
        return toHex(md.digest());
    }

    private static byte[] concat(byte[]... parts) {
        ByteArrayOutputStream bo = new ByteArrayOutputStream();
        for (byte[] p : parts) bo.write(p, 0, p.length);
        return bo.toByteArray();
    }

    private static String repeat(char c, int n) {
        char[] a = new char[n];
        Arrays.fill(a, c);
        return new String(a);
    }

    private static byte[] hex(String s) {
        byte[] b = new byte[s.length() / 2];
        for (int i = 0; i < b.length; i++) b[i] = (byte) Integer.parseInt(s.substring(2 * i, 2 * i + 2), 16);
        return b;
    }

    private static String toHex(byte[] b) {
        StringBuilder sb = new StringBuilder();
        for (byte x : b) sb.append(String.format("%02x", x));
        return sb.toString();
    }
}
