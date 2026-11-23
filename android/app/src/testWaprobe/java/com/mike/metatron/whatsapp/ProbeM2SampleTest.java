package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertTrue;

import org.junit.Test;

import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Random;
import java.util.regex.Pattern;

/**
 * Button 8's sample on planted messages: received-only, the row shape, the stratification, the
 * per-chat cap, and no id or name in any row or in the report.
 * Run: ./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.ProbeM2SampleTest'
 */
public class ProbeM2SampleTest {
    static final long NOW = 1_763_870_400_000L;
    static final long DAY = 24L * 3600 * 1000;
    static final String ALICE = "447700900123@s.whatsapp.net", HIDDEN = "99887766554433@lid",
            GROUP = "120363000000000001@g.us", BOB = "447700900222@s.whatsapp.net",
            STATUS = "status@broadcast", CHANNEL = "120363999999999999@newsletter", LIST = "1763870000@broadcast";
    static final Pattern ROW = Pattern.compile(
            "\\{\"n\":\\d+,\"chat_kind\":\"(one_to_one|group)\",\"time_s\":\\d+,\"text\":\"(?:[^\"\\\\]|\\\\.)*\"\\}");

    private static int row = 1;

    static WaMessage msg(String chat, boolean fromMe, long ago, String sender, String text) {
        return new WaMessage(chat, "KEYPLANT" + row, fromMe, NOW - ago, sender, text, row++);
    }

    @Test public void receivedWithTextOnlyAndNoIdOrNameAnywhere() {
        List<WaMessage> in = new ArrayList<>();
        in.add(msg(ALICE, false, DAY, null, "secret alpha, are you free Sat 19:00?"));
        in.add(msg(HIDDEN, false, DAY, null, "secret hidden-id one-to-one"));
        in.add(msg(GROUP, false, 2 * DAY, BOB, "secret group line from Bob"));
        in.add(msg(ALICE, true, DAY, null, "secret SENT BY ME"));                 // from me
        in.add(msg(GROUP, true, DAY, null, "secret SENT BY ME in group"));        // from me
        in.add(msg(ALICE, false, DAY, null, null));                               // no text
        in.add(msg(ALICE, false, DAY, null, "   "));                              // blank
        in.add(msg(STATUS, false, DAY, BOB, "secret STATUS update"));             // not a chat
        in.add(msg(CHANNEL, false, DAY, null, "secret CHANNEL post"));            // not a chat
        in.add(msg(LIST, false, DAY, null, "secret BROADCAST list"));             // not a chat
        in.add(msg(ALICE, false, 31 * DAY, null, "secret TOO OLD"));              // outside
        StringBuilder huge = new StringBuilder("secret HUGE ");
        while (huge.length() <= ProbeM2Sample.MAX_TEXT_CHARS) huge.append('x');
        in.add(msg(ALICE, false, DAY, null, huge.toString()));                    // the VM would refuse it

        ProbeM2Sample.Result r = ProbeM2Sample.sample(in, NOW, new Random(7));
        assertEquals(3, r.rows.size());
        String out = ProbeM2Sample.jsonl(r.rows);
        String[] lines = out.split("\n");
        assertEquals(3, lines.length);
        int one = 0, group = 0;
        for (String line : lines) {
            assertTrue(line, ROW.matcher(line).matches());
            if (line.contains("\"chat_kind\":\"group\"")) group++; else one++;
        }
        assertEquals(2, one);
        assertEquals(1, group);
        assertTrue(out.contains("\"time_s\":" + (NOW - DAY) / 1000 + ","));
        for (String excluded : new String[]{"SENT BY ME", "STATUS", "CHANNEL", "BROADCAST", "TOO OLD", "HUGE"}) {
            assertFalse(excluded, out.contains(excluded));
        }
        // No chat id, sender id, key or number reaches a row; no planted value reaches the report.
        for (String leak : new String[]{"447700900", "99887766", "120363", "whatsapp.net", "@lid", "g.us", "KEYPLANT", "broadcast", "sender"}) {
            assertFalse(leak, out.contains(leak));
        }
        for (String leak : new String[]{"secret", "447700900", "99887766", "120363", "KEYPLANT", "Bob", "alpha"}) {
            assertFalse(leak, r.report.contains(leak));
        }
        assertTrue(r.report, r.report.contains("received with text: 3 — one-to-one 2 (Cyrillic 0), group 1 (Cyrillic 0)"));
        assertTrue(r.report, r.report.contains("left out: sent by you 2, no text 2, not a chat (status, channels, broadcast lists) 3, "
                + "over 4000 characters 1, outside the window 1"));
        // n runs 1..k
        for (int i = 0; i < r.rows.size(); i++) assertEquals(i + 1, r.rows.get(i).n);
    }

    @Test public void stratifiedByScriptWithAFloorAndByKindInProportion() {
        List<WaMessage> in = new ArrayList<>();
        // Latin: 600 one-to-one over 60 chats, 300 group over 30 chats — 10 per chat, under the cap.
        for (int c = 0; c < 60; c++) for (int i = 0; i < 10; i++)
            in.add(msg((447000000000L + c) + "@s.whatsapp.net", false, DAY, null, "plain words " + i));
        for (int c = 0; c < 30; c++) for (int i = 0; i < 10; i++)
            in.add(msg((120363000000L + c) + "@g.us", false, DAY, BOB, "group words " + i));
        // Cyrillic: 100 one-to-one over 20 chats — 10% of traffic, so 20 by share; the floor lifts it to 30.
        for (int c = 0; c < 20; c++) for (int i = 0; i < 5; i++)
            in.add(msg((359000000000L + c) + "@s.whatsapp.net", false, DAY, null, "Здравей, как си " + i));

        ProbeM2Sample.Result r = ProbeM2Sample.sample(in, NOW, new Random(11));
        assertEquals(ProbeM2Sample.TARGET, r.rows.size());
        int cyr = 0, latGroup = 0, latOne = 0;
        for (ProbeM2Sample.Row row : r.rows) {
            if (ProbeM2Sample.cyrillic(row.text)) cyr++;
            else if (row.kind.equals("group")) latGroup++;
            else latOne++;
        }
        assertEquals(30, cyr);
        // 170 Latin, a third of Latin traffic is group: round(170 / 3) = 57.
        assertEquals(57, latGroup);
        assertEquals(113, latOne);
        assertTrue(r.report, r.report.contains("Cyrillic in the sample: 30 (floor 30)"));
    }

    @Test public void fewCyrillicAreAllTakenAndSaidSo() {
        List<WaMessage> in = new ArrayList<>();
        for (int c = 0; c < 40; c++) for (int i = 0; i < 10; i++)
            in.add(msg((447000000000L + c) + "@s.whatsapp.net", false, DAY, null, "plain words " + i));
        for (int i = 0; i < 12; i++) in.add(msg((359000000000L + i) + "@s.whatsapp.net", false, DAY, null, "Къде си " + i));
        ProbeM2Sample.Result r = ProbeM2Sample.sample(in, NOW, new Random(3));
        int cyr = 0;
        for (ProbeM2Sample.Row row : r.rows) if (ProbeM2Sample.cyrillic(row.text)) cyr++;
        assertEquals(12, cyr);
        assertEquals(ProbeM2Sample.TARGET, r.rows.size());
        assertTrue(r.report, r.report.contains("(floor 30; only 12 in the window)"));
    }

    @Test public void perChatCapKeepsOneBusyGroupFromFillingTheSample() {
        List<WaMessage> in = new ArrayList<>();
        for (int i = 0; i < 500; i++) in.add(msg(GROUP, false, DAY, BOB, "busy group " + i));
        for (int c = 0; c < 10; c++) for (int i = 0; i < 10; i++)
            in.add(msg((447000000000L + c) + "@s.whatsapp.net", false, DAY, null, "one to one " + i));
        ProbeM2Sample.Result r = ProbeM2Sample.sample(in, NOW, new Random(5));
        Map<String, Integer> byKind = new HashMap<>();
        for (ProbeM2Sample.Row row : r.rows) byKind.merge(row.kind, 1, Integer::sum);
        assertEquals(Integer.valueOf(ProbeM2Sample.PER_CHAT_CAP), byKind.get("group"));
        assertEquals(Integer.valueOf(100), byKind.get("one_to_one")); // the group's shortfall topped up
        assertTrue(r.report, r.report.contains("drawn from 11 chats; per-chat cap 15"));
    }

    @Test public void scriptRuleMatchesTheVm() {
        assertTrue(ProbeM2Sample.cyrillic("Здравей, как си?"));
        assertTrue(ProbeM2Sample.cyrillic("ok Здравей"));      // 2 Latin, 7 Cyrillic letters
        assertFalse(ProbeM2Sample.cyrillic("hello there"));
        assertFalse(ProbeM2Sample.cyrillic("12:30 👍"));        // no letters: Latin, as script_of says
        assertFalse(ProbeM2Sample.cyrillic("Καλημέρα"));        // Greek: not Cyrillic (the VM holds it back)
    }

    @Test public void jsonEscapesStayOneValidLine() {
        List<ProbeM2Sample.Row> rows = new ArrayList<>();
        rows.add(new ProbeM2Sample.Row(1, "one_to_one", 1_763_870_400L, "say \"hi\"\\ now\nline two\ttab\u0001 Здрасти 😀 \u2028end"));
        String out = ProbeM2Sample.jsonl(rows);
        assertEquals(1, out.split("\n").length);
        assertTrue(out, out.contains("say \\\"hi\\\"\\\\ now\\nline two\\ttab\\u0001 Здрасти 😀 \\u2028end"));
        rows.set(0, new ProbeM2Sample.Row(1, "group", 1L, "lone \uD800 surrogate"));
        assertTrue(ProbeM2Sample.jsonl(rows).contains("lone \\ud800 surrogate"));
    }
}
