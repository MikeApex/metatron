package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotNull;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.io.ByteArrayOutputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * ProbeFieldMap on a synthetic messages.bin built in the observed shape. The counts are only worth
 * having if they never carry a value, so every case plants phone numbers, jids, key_ids and message
 * text and asserts each is absent from the report.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.ProbeFieldMapTest'
 */
public class ProbeFieldMapTest {
    static final String GROUP = "120363000000000001@g.us", ALICE = "447700900123@s.whatsapp.net",
            ALICE_LID = "111111111111111@lid", BOB_LID = "222222222222222@lid";
    static final long T = 1_763_870_400L; // seconds

    @Test public void decodeHoldsEveryLeafByPathRelativeToTheMessage() {
        byte[] bin = file(chat(ALICE, msg(ALICE, 0, "KEYAAAA1", T, null, "hello there friend", null, 101)));
        ProbeFieldMap.Decoded d = ProbeFieldMap.decode(bin);
        assertEquals(null, d.malformed);
        assertEquals(1, d.records);
        assertEquals(1, d.chatBlocks);
        assertEquals(1, d.msgs.size());
        ProbeFieldMap.Msg m = d.msgs.get(0);
        assertEquals(ALICE, m.chatJid);
        assertEquals("KEYAAAA1", m.text("1.1.3"));
        assertEquals(Long.valueOf(0), m.num("1.1.2"));
        assertEquals(Long.valueOf(T), m.num("1.3"));
        assertEquals("hello there friend", m.text("1.2.1"));
        assertEquals(Long.valueOf(101), m.num("2"));
        d.wipe();
        assertTrue(d.msgs.isEmpty());
    }

    @Test public void countsAgreementPerCandidateAndNeverAValue() {
        byte[] bin = file(
                chat(ALICE, msg(ALICE, 0, "KEYAAAA1", T, null, "hello there friend", null, 101),
                            msg(ALICE, 1, "KEYAAAA2", T + 5, null, null, "edited words here", 102)),
                chat(GROUP, msg(GROUP, 0, "KEYBBBB1", T + 9, BOB_LID, "group words here", null, 103),
                            msg(GROUP, 0, "KEYBBBB2", T + 10, BOB_LID, null, null, 104)),
                chat(ALICE_LID, msg(ALICE_LID, 0, "KEYCCCC1", T + 20, null, "lid chat words", null, 105)));
        ProbeFieldMap.Decoded d = ProbeFieldMap.decode(bin);
        assertEquals(5, d.msgs.size());

        FakeRows rows = new FakeRows();
        rows.add("KEYAAAA1", 101, 0, T * 1000 + 400, ALICE, null, "hello there friend");
        rows.add("KEYAAAA2", 102, 1, T * 1000 + 5000, ALICE, null, "the original words");   // an edit
        rows.add("KEYBBBB1", 103, 0, T * 1000 + 9000, GROUP, BOB_LID, "group words here");
        rows.add("KEYBBBB2", 104, 0, T * 1000 + 10000, GROUP, BOB_LID, "caption hidden elsewhere");
        rows.add("KEYCCCC1", 105, 0, T * 1000 + 20000, ALICE, null, "lid chat words");         // chat keyed by number
        rows.links.add(ALICE_LID + "|" + ALICE);

        StringBuilder b = new StringBuilder();
        int[] out = ProbeFieldMap.compare(d.msgs, rows, "newest", b);
        ProbeFieldMap.selfChecks(d, b);
        String r = b.toString();

        assertTrue(r, r.contains("matched by key_id 1.1.3 5 of 5 (not in this backup 0"));
        assertTrue(r, r.contains("key flag 1.1.2 vs from_me: equal 5, differs 0, absent 0"));
        assertTrue(r, r.contains("time 1.3 vs timestamp/1000: equal 5, differs 0, absent 0"));
        assertTrue(r, r.contains("chat block jid (record.2.1) vs chat's jid.raw_string: equal 4, differs 1, absent 0"));
        assertTrue(r, r.contains("(of the differing, linked by jid_map: 1)"));
        assertTrue(r, r.contains("sender 1.5 vs sender's raw_string (group rows, not from me): equal 2, differs 0, absent 0"));
        assertTrue(r, r.contains("row id 2 vs message._id: equal 5, differs 0, absent 0"));
        assertTrue(r, r.contains("text 1.2.1 vs text_data: equal 3, differs 0, absent while backup has text 2"));
        assertTrue(r, r.contains("text 1.2.6.1 vs text_data: equal 0, differs 1, absent while backup has text 4"));
        assertTrue(r, r.contains("text_data non-null on 5 matched rows: equal to some leaf 3, found nowhere in the message 2"));
        assertTrue(r, r.contains("text_data found at: 1.2.1 ×3\n"));
        assertTrue(r, r.contains("message._id found at: 2 ×5"));
        assertTrue(r, r.contains("messages 5, distinct key_ids 5"));
        assertEquals(ProbeFieldMap.T_DIFFERS, out[1]);
        assertEquals(ProbeFieldMap.T_EQUAL, out[0]);

        for (String leak : new String[]{"447700900123", "120363", "111111111111111", "222222222222222", "KEYAAAA", "KEYBBBB",
                "hello", "edited", "original", "group words", "caption", "lid chat", "whatsapp.net", "@g.us", "@lid",
                String.valueOf(T)}) {
            assertFalse("leaked " + leak + ":\n" + r, r.contains(leak));
        }
    }

    @Test public void editsShowAsDiffersFromBaseEqualsNewest() {
        StringBuilder b = new StringBuilder();
        ProbeFieldMap.edits(new int[]{ProbeFieldMap.T_DIFFERS, ProbeFieldMap.T_EQUAL, ProbeFieldMap.T_NOT_MATCHED},
                new int[]{ProbeFieldMap.T_EQUAL, ProbeFieldMap.T_EQUAL, ProbeFieldMap.T_EQUAL}, b);
        assertTrue(b.toString(), b.toString().contains("differs from base but equals newest 1, equals both 1, differs from both 0"));
    }

    @Test public void unmatchedAndNotWireFormatAreCountedNotHidden() {
        byte[] bin = file(chat(ALICE, msg(ALICE, 0, "KEYZZZZ9", T, null, "nobody has this", null, 9)));
        StringBuilder b = new StringBuilder();
        ProbeFieldMap.compare(ProbeFieldMap.decode(bin).msgs, new FakeRows(), "base", b);
        assertTrue(b.toString(), b.toString().contains("matched by key_id 1.1.3 0 of 1 (not in this backup 1"));
        assertFalse(b.toString().contains("nobody"));

        ProbeFieldMap.Decoded bad = ProbeFieldMap.decode(new byte[]{(byte) 0xff, (byte) 0xff, (byte) 0xff});
        assertNotNull(bad.malformed);
        assertTrue(bad.msgs.isEmpty());
    }

    @Test public void deletedIdsAreReadAsNumbers() {
        List<Long> ids = ProbeFieldMap.deletedIds("{\"deleted_ids\": [56987, 57001 ,57030]}".getBytes(StandardCharsets.UTF_8));
        assertEquals(3, ids.size());
        assertEquals(Long.valueOf(57030), ids.get(2));
        assertTrue(ProbeFieldMap.deletedIds("{}".getBytes(StandardCharsets.UTF_8)).isEmpty());
    }

    @Test public void round2CountsTextPerPathDeletionsAndTheRecordsOtherFields() {
        byte[] bin = file(
                chat(GROUP, msg(GROUP, 0, "KEYDDDD1", T, BOB_LID, "first words here", null, 201),
                            msg(GROUP, 0, "KEYDDDD2", T + 1, BOB_LID, null, null, 202)),
                chat(ALICE, msg(ALICE, 1, "KEYDDDD3", T + 2, null, null, "quoted reply words", 203)));
        ProbeFieldMap.Decoded d = ProbeFieldMap.decode(bin);
        FakeRows rows = new FakeRows();
        rows.add("KEYDDDD1", 201, 0, T * 1000, GROUP, BOB_LID, "first words here");
        rows.add("KEYDDDD2", 202, 0, T * 1000 + 1000, GROUP, BOB_LID, null);
        rows.add("KEYDDDD3", 203, 1, T * 1000 + 2000, ALICE, null, "quoted reply words");
        rows.byId(202).messageType = 15;
        StringBuilder b = new StringBuilder();
        ProbeFieldMap.round2(d.msgs, java.util.Arrays.asList(202L, 999L), rows, b);
        ProbeFieldMap.census(bin, new HashSet<>(java.util.Arrays.asList("KEYDDDD1", "KEYDDDD2", "KEYDDDD3")), b);
        String r = b.toString();
        assertTrue(r, r.contains("1.2.1 1/0/0; 1.2.6.1 1/0/0;"));
        assertTrue(r, r.contains("vs text_data: equal 2, differs 0, none while backup has text 0, text while backup null 0, both none 1"));
        assertTrue(r, r.contains("deleted ids 2: row absent here 1, present with text_data 0, present without 1; message_type of those present {15=1}; re-sent in this increment 1 (with rule text 0, same key_id as this row 1)"));
        assertTrue(r, r.contains("top-level fields: {2(len)=2}"));
        assertTrue(r, r.contains("a full-backup key_id found at: rec.2.2.1.1.3 ×3"));
        for (String leak : new String[]{"KEYDDDD", "first words", "quoted", "120363", "222222222222222", "447700900123"}) {
            assertFalse("leaked " + leak + ":\n" + r, r.contains(leak));
        }
    }

    @Test public void headerMarkersShowOnlyFormatShapedValues() {
        String ok = ProbeFieldMap.headerMarkers(("{\"header\":{\"format_version\":\"2.0\"},\"added_messages\":"
                + "{\"filename\":\"messages.bin\",\"format\":\"protobuf\"}}").getBytes(StandardCharsets.UTF_8));
        assertEquals("format_version 2.0, added_messages.format protobuf, filename is messages.bin: yes", ok);
        String odd = ProbeFieldMap.headerMarkers(("{\"header\":{\"format_version\":\"Alice 447700900123\"},\"added_messages\":"
                + "{\"filename\":\"Alice.bin\",\"format\":\"Bob Example\"}}").getBytes(StandardCharsets.UTF_8));
        assertFalse(odd, odd.contains("Alice") || odd.contains("4477") || odd.contains("Bob"));
        assertTrue(odd, odd.contains("filename is messages.bin: no"));
    }

    // ---- an encoder for the observed shape ----------------------------------------------------

    static byte[] msg(String keyJid, int fromMe, String keyId, long seconds, String sender, String textA, String textB, long rowId) {
        ByteArrayOutputStream key = new ByteArrayOutputStream();
        text(key, 1, keyJid);
        varint(key, 2, fromMe);
        text(key, 3, keyId);
        ByteArrayOutputStream info = new ByteArrayOutputStream();
        bytes(info, 1, key.toByteArray());
        if (textA != null || textB != null) {
            ByteArrayOutputStream content = new ByteArrayOutputStream();
            if (textA != null) text(content, 1, textA);
            if (textB != null) {
                ByteArrayOutputStream ext = new ByteArrayOutputStream();
                text(ext, 1, textB);
                bytes(content, 6, ext.toByteArray());
            }
            bytes(info, 2, content.toByteArray());
        }
        varint(info, 3, seconds);
        if (sender != null) text(info, 5, sender);
        ByteArrayOutputStream m = new ByteArrayOutputStream();
        bytes(m, 1, info.toByteArray());
        varint(m, 2, rowId);
        return m.toByteArray();
    }

    static byte[] chat(String jid, byte[]... messages) {
        ByteArrayOutputStream c = new ByteArrayOutputStream();
        text(c, 1, jid);
        for (byte[] m : messages) bytes(c, 2, m);
        return c.toByteArray();
    }

    static byte[] file(byte[]... chats) {
        ByteArrayOutputStream rec = new ByteArrayOutputStream();
        for (byte[] c : chats) bytes(rec, 2, c);
        byte[] r = rec.toByteArray();
        ByteArrayOutputStream f = new ByteArrayOutputStream();
        writeVarint(f, r.length);
        f.write(r, 0, r.length);
        return f.toByteArray();
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

    static final class FakeRows implements ProbeFieldMap.Rows {
        final Map<String, List<ProbeFieldMap.Row>> rows = new HashMap<>();
        final Set<Long> ids = new HashSet<>();
        final Set<String> links = new HashSet<>();

        void add(String key, long id, int fromMe, long ts, String chat, String sender, String text) {
            ProbeFieldMap.Row r = new ProbeFieldMap.Row();
            r.id = id;
            r.fromMe = fromMe;
            r.timestamp = ts;
            r.chatJid = chat;
            r.senderJid = sender;
            r.text = text;
            if (!rows.containsKey(key)) rows.put(key, new ArrayList<>());
            rows.get(key).add(r);
            ids.add(id);
        }

        public List<ProbeFieldMap.Row> byKeyId(String k) {
            List<ProbeFieldMap.Row> r = rows.get(k);
            return r == null ? Collections.emptyList() : r;
        }

        public boolean hasMessageId(long id) { return ids.contains(id); }

        public ProbeFieldMap.Row byId(long id) {
            for (List<ProbeFieldMap.Row> l : rows.values()) for (ProbeFieldMap.Row r : l) if (r.id == id) return r;
            return null;
        }

        public boolean linked(String a, String b) { return links.contains(a + "|" + b) || links.contains(b + "|" + a); }
    }
}
