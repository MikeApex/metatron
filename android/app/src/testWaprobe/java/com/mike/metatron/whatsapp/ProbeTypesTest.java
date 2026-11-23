package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;

/**
 * ProbeTypes on planted values: the counts must be right and no planted value may appear.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.ProbeTypesTest'
 */
public class ProbeTypesTest {
    static final String[] LEAKS = {"secret", "KEY", "447700900", "120363", "Ada Example"};

    @Test public void fullSummarySplitsFromMeByChatKindAndShowsNoValue() {
        String s = ProbeTypes.fullSummary(Arrays.asList(
                new ProbeTypes.Group(0, "s.whatsapp.net", false, 50, 48),
                new ProbeTypes.Group(0, "s.whatsapp.net", true, 30, 29),
                new ProbeTypes.Group(0, "g.us", true, 5, 5),
                new ProbeTypes.Group(7, "lid", true, 4, 0),
                new ProbeTypes.Group(7, null, false, 2, 0),
                new ProbeTypes.Group(9, "Ada Example 447700900", true, 1, 1)));
        assertEquals("  type 0: rows 85, with text 82; from me 35, with text 34 — from me by chat kind {g.us=5/5, s.whatsapp.net=30/29}\n"
                + "  type 7: rows 6, with text 0; from me 4, with text 0 — from me by chat kind {lid=4/0}\n"
                + "  type 9: rows 1, with text 1; from me 1, with text 1 — from me by chat kind {(other)=1/1}\n", s);
        for (String leak : LEAKS) assertFalse(leak, s.contains(leak));
    }

    private static ProbeFieldMap.Msg msg(long rowId, String keyId, long fromMe, String text, Object... extra) {
        ProbeFieldMap.Msg m = new ProbeFieldMap.Msg();
        m.chatJid = "447700900123@s.whatsapp.net";
        m.add(ProbeFieldMap.ROW_ID, rowId);
        m.add(ProbeFieldMap.KEY_JID, m.chatJid);
        m.add(ProbeFieldMap.KEY_ID, keyId);
        m.add(ProbeFieldMap.KEY_FLAG, fromMe);
        m.add(ProbeFieldMap.TIME, 1_763_870_400L);
        if (text != null) m.add(ProbeFieldMap.TEXT_A, text);
        for (int i = 0; i < extra.length; i += 2) m.add((String) extra[i], extra[i + 1]);
        return m;
    }

    @Test public void tallyFindsAFieldThatTracksTheTypeAndNotOneThatIsConstant() {
        Map<Long, ProbeTypes.Row> rows = new HashMap<>();
        ProbeTypes.Tally t = new ProbeTypes.Tally();
        // 12 type-0 text messages: "1.9" absent (a zero left out), "1.4" = 0 always (constant, must not be listed).
        for (int i = 0; i < 12; i++) {
            rows.put((long) i, new ProbeTypes.Row(0, "KEY" + i));
            t.add(msg(i, "KEY" + i, i % 2, "secret words " + i, "1.4", 0L), rows);
        }
        // 12 type-7 from-me messages with no text, a different content shape, "1.9" = 7.
        for (int i = 100; i < 112; i++) {
            rows.put((long) i, new ProbeTypes.Row(7, "KEY" + i));
            t.add(msg(i, "KEY" + i, 1, null, "1.2.24.1", 3L, "1.9", 7L, "1.4", 0L), rows);
        }
        // 12 type-9 from-me messages, "1.9" = 9.
        for (int i = 200; i < 212; i++) {
            rows.put((long) i, new ProbeTypes.Row(9, "KEY" + i));
            t.add(msg(i, "KEY" + i, 1, null, "1.2.3.1", 1L, "1.9", 9L, "1.4", 0L), rows);
        }
        t.add(msg(300, "KEYX", 0, "secret unmatched"), rows);       // not in the backup
        rows.put(301L, new ProbeTypes.Row(0, "KEYOTHER"));
        t.add(msg(301, "KEYY", 0, "secret wrong key"), rows);       // key_id differs
        String r = t.report();

        assertTrue(r, r.contains("increment messages 38: matched to the newest backup by row id and key_id 36; "
                + "no row id 0, row id not in the backup 1, key_id differs 1"));
        assertTrue(r, r.contains("{0=6/6, 6/6, 7=0/0, 12/0, 9=0/0, 12/0}"));
        assertTrue(r, r.contains("    type 0: {1} ×12\n    type 7: {24} ×12\n    type 9: {3} ×12\n"));
        assertTrue(r, r.contains("    1.9: present 24, equal 24, types equal [7, 9]; absent on matched, by type {0=12}\n"));
        assertFalse("a constant field is not a type", r.contains("    1.4:"));
        for (String leak : LEAKS) assertFalse(leak, r.contains(leak));
    }

    @Test public void tallySaysNoneWhenNothingTracksTheType() {
        Map<Long, ProbeTypes.Row> rows = new HashMap<>();
        ProbeTypes.Tally t = new ProbeTypes.Tally();
        for (int i = 0; i < 20; i++) {
            rows.put((long) i, new ProbeTypes.Row(i % 2 == 0 ? 0 : 7, "KEY" + i));
            t.add(msg(i, "KEY" + i, 1, "secret " + i), rows);
        }
        assertTrue(t.report(), t.report().contains("    none — no numeric field tracks the type\n"));
    }

    @Test public void signatureIsTheContentBlocksOwnFieldNumbers() {
        assertEquals("{}", ProbeTypes.signature(msg(1, "K", 0, null)));
        assertEquals("{1}", ProbeTypes.signature(msg(1, "K", 0, "x")));
        assertEquals("{1,6,24}", ProbeTypes.signature(msg(1, "K", 0, "x", "1.2.6.1", "y", "1.2.24.3.2", 5L)));
    }

    @Test public void kindLabelsOnlyServerShapedText() {
        assertEquals("g.us", ProbeTypes.kind("g.us"));
        assertEquals("(no chat)", ProbeTypes.kind(null));
        assertEquals("(other)", ProbeTypes.kind("447700900123"));
    }
}
