package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Before;
import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TimeZone;

/**
 * ProbeShapes on synthetic entries. The shapes are only worth having if they never carry a value,
 * so every case plants values a report must not show — a phone number as a string and as a
 * number, a display name as a value and as a key, message text, a key_id — and asserts each is
 * absent, alongside what the report must say.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'
 */
public class ProbeShapesTest {
    private static final long NEWEST = 1_763_870_400_000L;   // 2025-11-23 04:00 UTC
    private FakeFull full;

    @Before public void setUp() {
        ProbeShapes.zone = TimeZone.getTimeZone("UTC");
        full = new FakeFull();
    }

    @Test public void jsonReportsPathsAndTypesButNeverAValue() {
        String json = "{\"table\":\"jid\",\"rows\":["
                + "{\"_id\":12,\"user\":\"447700900123\",\"server\":\"s.whatsapp.net\",\"ts\":1763870400000,"
                + "\"big\":447700900123,\"note\":\"Alice Example\",\"flag\":true,\"gone\":null,\"ratio\":0.5},"
                + "{\"_id\":13000,\"user\":\"447700900124\",\"server\":\"lid\",\"ts\":1763874000000,"
                + "\"big\":447700900124,\"note\":\"Bob Example\",\"flag\":false,\"gone\":null,\"ratio\":1.5}],"
                + "\"Alice Example\":{\"x\":1}}";
        String r = shape("jid_modified_1.json", json);

        assertTrue(r, r.contains("— JSON"));
        assertTrue(r, r.contains(".rows  array×1 len 2..2"));
        assertTrue(r, r.contains(".rows[]._id  int×2 12..13000"));
        assertTrue(r, r.contains(".rows[].user  text×2 len 12..12"));
        assertTrue(r, r.contains(".rows[].ts  time(ms)×2 2025-11-23 04:00 .. 2025-11-23 05:00; newer than the full backup's newest message 1"));
        assertTrue(r, r.contains(".rows[].big  large number×2 (up to 12 digits)"));
        assertTrue(r, r.contains("bool×2"));
        assertTrue(r, r.contains("null×2"));
        assertTrue(r, r.contains("decimal×2"));
        assertTrue(r, r.contains(".table  text×1 len 3..3, schema names 1 [jid]"));
        assertTrue("a non-identifier key is folded", r.contains(".{*}  object×1"));
        assertTrue(r, r.contains("_id values: 2 — already in the full backup's jid: 1, not there: 1"));

        for (String leak : new String[]{"447700900123", "447700900124", "Alice", "Bob", "whatsapp.net", "0.5", "1763870400000"}) {
            assertFalse("leaked " + leak + ":\n" + r, r.contains(leak));
        }
    }

    @Test public void schemaNamesAreListedOnlyWhenEveryValueIsOne() {
        String r = shape("props_modified_1.json", "{\"cols\":[\"_id\",\"user\",\"Carol\"],\"names\":[\"_id\",\"user\"]}");
        assertTrue(r, r.contains(".cols[]  text×3 len 3..5, schema names 2\n"));
        assertTrue(r, r.contains(".names[]  text×2 len 3..4, schema names 2 [_id, user]"));
        assertFalse(r, r.contains("Carol"));
        assertFalse("no numeric _id, so no overlap line", r.contains("_id values"));
    }

    @Test public void aTableTheFullBackupLacksIsSaidSo() {
        String r = shape("labels_deleted_1.json", "[{\"_id\":5},{\"_id\":6}]");
        assertTrue(r, r.contains("_id values: 2 — the full backup has no table labels"));
    }

    @Test public void malformedJsonStopsCleanlyAndKeepsWhatItSaw() {
        String r = shape("chat_modified_1.json", "{\"rows\":[{\"_id\":1},{\"_id\":2");
        assertTrue(r, r.contains("JSON parse stopped at character"));
        assertTrue(r, r.contains(".rows[]._id  int×2 1..2"));
    }

    @Test public void protobufRecordsAreWalkedByFieldPath() throws Exception {
        ByteArrayOutputStream msg = new ByteArrayOutputStream();
        varintField(msg, 1, 2);
        String[] keyIds = {"ABCDEF0123456789", "0123456789ABCDEF", "FEDCBA9876543210"};
        long[] times = {NEWEST - 60_000, NEWEST, NEWEST + 60_000};
        for (int i = 0; i < 3; i++) {
            ByteArrayOutputStream sub = new ByteArrayOutputStream();
            textField(sub, 1, keyIds[i]);
            textField(sub, 5, i == 0 ? "123456789012345@lid" : "999999999999999@lid");
            varintField(sub, 2, times[i]);
            textField(sub, 3, "secret words number " + i);
            bytesField(sub, 4, new byte[]{0x00, 0x01, (byte) 0xff});
            bytesField(msg, 2, sub.toByteArray());
        }
        byte[] record = msg.toByteArray();
        ByteArrayOutputStream file = new ByteArrayOutputStream();
        writeVarint(file, record.length);
        file.write(record);

        StringBuilder b = new StringBuilder();
        ProbeShapes.entry("messages.bin", file.toByteArray(), full, b);
        String r = b.toString();

        assertTrue(r, r.contains("not JSON; generic protobuf wire-format test"));
        assertTrue(r, r.contains("varint-length-delimited records: YES — 1 record(s), sizes " + record.length + ".." + record.length));
        assertTrue(r, r.contains("rec.1  int×1 2..2"));
        assertTrue(r, r.contains("rec.2  message×3"));
        assertTrue(r, r.contains("rec.2.1  text×3 len 16..16, hex-like 3, equal to a full-backup message key_id 2"));
        assertTrue(r, r.contains("rec.2.2  time(ms)×3 2025-11-23 03:59 .. 2025-11-23 04:01; newer than the full backup's newest message 1"));
        assertTrue(r, r.contains("rec.2.3  text×3 len 21..21"));
        assertTrue(r, r.contains("rec.2.4  bytes×3 len 3..3"));
        assertTrue(r, r.contains("rec.2.5  text×3 len 19..19, equal to a full-backup jid 1"));
        for (String leak : new String[]{"secret", "ABCDEF", "0123456789", "FEDCBA", "@lid", "123456789012345"}) {
            assertFalse("leaked " + leak + ":\n" + r, r.contains(leak));
        }
    }

    @Test public void theRealEntrysFramingIsRecognised() {
        // messages.bin on the phone began bf f6 03 08 02 12 e9 04 and was 64,322 bytes: a varint
        // prefix of 64,319 (3 bytes) then one record. Build that framing around a valid message.
        long[] v = ProbeShapes.varint(new byte[]{(byte) 0xbf, (byte) 0xf6, 0x03}, 0, 3);
        assertEquals(64_319L, v[0]);
        assertEquals(3L, v[1]);
        assertTrue(ProbeShapes.isMessage(new byte[]{0x08, 0x02}, 0, 2));
        assertFalse("field 0 is not a field", ProbeShapes.isMessage(new byte[]{0x00, 0x02}, 0, 2));
        assertFalse("wire type 3 (group) is refused", ProbeShapes.isMessage(new byte[]{0x0b}, 0, 1));
        assertFalse("a length past the end is refused", ProbeShapes.isMessage(new byte[]{0x12, 0x05, 0x01}, 0, 3));
    }

    @Test public void bytesWithNoStructureSaySo() {
        byte[] noise = new byte[64];
        Arrays.fill(noise, (byte) 0xff);
        StringBuilder b = new StringBuilder();
        ProbeShapes.entry("mystery.bin", noise, full, b);
        String r = b.toString();
        assertTrue(r, r.contains("varint-length-delimited records: no"));
        assertTrue(r, r.contains("whole entry as one message: no"));
        assertTrue(r, r.contains("no protobuf structure found; zero bytes 0%"));
    }

    @Test public void withoutAFullBackupComparisonsAreSimplyAbsent() {
        StringBuilder b = new StringBuilder();
        ProbeShapes.entry("jid_modified_1.json", "[{\"_id\":1,\"t\":1763870400000}]".getBytes(StandardCharsets.UTF_8), ProbeShapes.NONE, b);
        String r = b.toString();
        assertFalse(r, r.contains("newer than"));
        assertTrue(r, r.contains("_id values: 1 — the full backup has no table jid"));
    }

    // ---- helpers ---------------------------------------------------------------------------

    private String shape(String name, String json) {
        StringBuilder b = new StringBuilder();
        ProbeShapes.entry(name, json.getBytes(StandardCharsets.UTF_8), full, b);
        return b.toString();
    }

    private static void writeVarint(ByteArrayOutputStream o, long v) {
        while ((v & ~0x7fL) != 0) {
            o.write((int) ((v & 0x7f) | 0x80));
            v >>>= 7;
        }
        o.write((int) v);
    }

    private static void varintField(ByteArrayOutputStream o, int field, long v) {
        writeVarint(o, ((long) field << 3));
        writeVarint(o, v);
    }

    private static void bytesField(ByteArrayOutputStream o, int field, byte[] data) {
        writeVarint(o, ((long) field << 3) | 2);
        writeVarint(o, data.length);
        o.write(data, 0, data.length);
    }

    private static void textField(ByteArrayOutputStream o, int field, String s) {
        bytesField(o, field, s.getBytes(StandardCharsets.UTF_8));
    }

    private static final class FakeFull implements ProbeShapes.Full {
        final Set<String> schema = new HashSet<>(Arrays.asList("jid", "chat", "message", "_id", "user", "raw_string"));
        final Set<String> keys = new HashSet<>(Arrays.asList("ABCDEF0123456789", "0123456789ABCDEF"));
        final Set<String> jids = new HashSet<>(Arrays.asList("123456789012345@lid"));
        final Set<Long> jidIds = new HashSet<>(Arrays.asList(12L));

        public Set<String> schemaNames() { return schema; }
        public Set<String> messageKeyIds() { return keys; }
        public Set<String> jidRawStrings() { return jids; }
        public long newestMessageTime() { return NEWEST; }
        public int idsPresent(String table, List<Long> ids) {
            if (!"jid".equals(table)) return -1;
            int n = 0;
            for (Long id : ids) if (jidIds.contains(id)) n++;
            return n;
        }
    }
}
