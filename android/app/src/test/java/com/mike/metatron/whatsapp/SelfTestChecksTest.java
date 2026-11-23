package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertEquals;
import static org.junit.Assert.assertFalse;
import static org.junit.Assert.assertNotEquals;
import static org.junit.Assert.assertTrue;
import static org.junit.Assert.fail;

import java.io.File;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeMap;

import org.junit.Test;

/**
 * The reader self-test's plain-Java half ({@link SelfTestChecks}). The SQL half runs only on the
 * phone ({@link SelfTest}); here the fixture's rows are joined in plain Java the way the reader's
 * SQL joins them, fed to the reader's platform-free mapping, and every on-device comparison must
 * pass — so the expected outcomes are proven to match the fixture before a phone ever runs them.
 * Every value is made up, and none may appear in any result the self-test can show.
 */
public class SelfTestChecksTest {

    // ---- the plain-Java stand-in for the reader's SQL ------------------------------------------

    static final class Sim {
        final List<WaMessage> messages = new ArrayList<>();
        final int[] withoutKeyId = {0}, withoutChat = {0};
        final BackupCombiner.JidTables tables = new BackupCombiner.JidTables();
        ChatList chats;
    }

    /** FullBackupMessages.read's LEFT JOINs and since filter, and ChatList.read's queries, over the rows. */
    static Sim simulate(List<SelfTestChecks.Row> rows) {
        Map<Long, String> raw = new HashMap<>();
        Map<Long, Long> chatJid = new HashMap<>();
        Map<Long, ChatList.ChatRow> chatRows = new TreeMap<>();
        Map<Long, String> names = new TreeMap<>();
        Map<Long, Long> last = new TreeMap<>();
        List<Map<String, Object>> messageRows = new ArrayList<>();
        Sim s = new Sim();
        for (SelfTestChecks.Row r : rows) {
            Map<String, Object> v = r.values;
            switch (r.table) {
                case "jid":
                    if (v.get("raw_string") != null) {
                        raw.put((Long) v.get("_id"), (String) v.get("raw_string"));
                        s.tables.putJid((Long) v.get("_id"), (String) v.get("raw_string"));
                    }
                    break;
                case "jid_map":
                    s.tables.putLink((Long) v.get("lid_row_id"), (Long) v.get("jid_row_id"));
                    break;
                case "chat":
                    chatJid.put((Long) v.get("_id"), (Long) v.get("jid_row_id"));
                    chatRows.put((Long) v.get("_id"), new ChatList.ChatRow((Long) v.get("jid_row_id"), (String) v.get("subject")));
                    break;
                case "lid_display_name":
                    if (v.get("display_name") != null) names.put((Long) v.get("lid_row_id"), (String) v.get("display_name"));
                    break;
                case "message":
                    messageRows.add(v);
                    Long chat = (Long) v.get("chat_row_id"), ts = (Long) v.get("timestamp");
                    if (chat != null && ts != null) {
                        Long prev = last.get(chat);
                        if (prev == null || ts / 1000 > prev) last.put(chat, ts / 1000);
                    }
                    break;
                default:
                    fail("row for a table the reader does not read: " + r.table);
            }
        }
        for (Map<String, Object> v : messageRows) {
            long ts = (Long) v.get("timestamp");
            if (ts < SelfTestChecks.SINCE_SECONDS * 1000L) continue;
            Long jr = chatJid.get((Long) v.get("chat_row_id"));
            Long sr = (Long) v.get("sender_jid_row_id");
            Long type = (Long) v.get("message_type");
            WaMessage m = FullBackupMessages.row((String) v.get("key_id"), (Long) v.get("_id"), (Long) v.get("from_me") == 1L,
                    ts, jr == null ? null : raw.get(jr), sr == null ? null : raw.get(sr), (String) v.get("text_data"),
                    type == null ? null : type.intValue(), s.withoutKeyId, s.withoutChat);
            if (m != null) s.messages.add(m);
        }
        BackupCombiner.JidTables chatTables = new BackupCombiner.JidTables();
        for (Map.Entry<Long, String> e : raw.entrySet()) chatTables.putJid(e.getKey(), e.getValue());
        chatTables.lidToJid.putAll(s.tables.lidToJid);
        s.chats = new ChatList(chatTables, chatRows, names, last, new TreeMap<String, Long>());
        return s;
    }

    static Map<String, Set<String>> sets(Map<String, List<String>> schema) {
        Map<String, Set<String>> m = new LinkedHashMap<>();
        for (Map.Entry<String, List<String>> e : schema.entrySet()) m.put(e.getKey(), new LinkedHashSet<>(e.getValue()));
        return m;
    }

    static boolean refusedBySchemaCheck(Map<String, List<String>> schema) {
        try {
            SchemaCheck.require(sets(schema));
            return false;
        } catch (BackupException e) {
            return e.error == BackupError.SCHEMA_CHANGED;
        }
    }

    /** Every check, in the order SelfTest.run makes them, over the simulated reads. */
    static SelfTestChecks.Result simulatedRun(Sim s) {
        SelfTestChecks.Result r = new SelfTestChecks.Result();
        r.check(SelfTestChecks.S_PLANTED, SelfTestChecks.plantedExact(sets(SelfTestChecks.plantedSchema())));
        r.pass(SelfTestChecks.M_READ);
        SelfTestChecks.messages(s.messages, s.withoutKeyId[0], s.withoutChat[0], s.tables, r);
        SelfTestChecks.replies(s.messages, r);
        r.pass(SelfTestChecks.C_READ);
        SelfTestChecks.chats(s.chats, r);
        r.check(SelfTestChecks.S_MESSAGES, refusedBySchemaCheck(SelfTestChecks.renamedSchema()));
        r.check(SelfTestChecks.S_CHATS, refusedBySchemaCheck(SelfTestChecks.renamedSchema()));
        r.pass(SelfTestChecks.CLEANUP);
        return r;
    }

    // ---- the fixture and its expected outcomes -------------------------------------------------

    @Test
    public void theExpectedOutcomesMatchTheFixture() {
        SelfTestChecks.Result r = simulatedRun(simulate(SelfTestChecks.plantedRows()));
        assertEquals("failed: " + r.failed(), 0, r.failed().size());
        assertEquals(SelfTestChecks.ALL, r.passedNames);
        assertEquals(26, r.total());
        assertTrue(r.allPassed());
        assertEquals("Reader self-test: 26 of 26 passed", r.summary());
    }

    @Test
    public void everyCheckIsNamedOnce() {
        assertEquals(SelfTestChecks.ALL.size(), new HashSet<>(SelfTestChecks.ALL).size());
        assertEquals(1 + 1 + SelfTestChecks.MESSAGE_CHECKS.length + SelfTestChecks.REPLY_CHECKS.length + 1
                + SelfTestChecks.CHAT_CHECKS.length + 2 + 1, SelfTestChecks.ALL.size());
    }

    @Test
    public void theExpectedCountsMatchTheRows() {
        long since = SelfTestChecks.SINCE_SECONDS * 1000L;
        Set<Long> chats = new HashSet<>();
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) if (r.table.equals("chat")) chats.add((Long) r.values.get("_id"));
        int all = 0, before = 0, atBoundary = 0, keyed = 0, noKey = 0, noChat = 0;
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) {
            if (!r.table.equals("message")) continue;
            all++;
            long ts = (Long) r.values.get("timestamp");
            if (ts < since) { before++; continue; }
            if (ts == since) atBoundary++;
            if (!chats.contains((Long) r.values.get("chat_row_id"))) noChat++;
            else if (r.values.get("key_id") == null) noKey++;
            else keyed++;
        }
        assertEquals(13, all);
        assertEquals("a row just before the since-second is planted, and left out", 1, before);
        assertEquals("a row at the since-second's first ms is planted, and read", 1, atBoundary);
        assertEquals(SelfTestChecks.MESSAGES.size(), keyed);
        assertEquals(SelfTestChecks.EXPECTED_WITHOUT_KEY_ID, noKey);
        assertEquals(SelfTestChecks.EXPECTED_WITHOUT_CHAT, noChat);

        Set<Integer> replyTypes = new HashSet<>();
        int replies = 0, receivedGroupWithSender = 0, sendersExpected = 0;
        for (SelfTestChecks.ExpectedMessage e : SelfTestChecks.MESSAGES) {
            if (e.reply) { replies++; replyTypes.add(e.type); }
            if (e.senderJid != null) sendersExpected++;
            if (!e.fromMe && e.chatJid.endsWith("@g.us") && e.senderJid != null) receivedGroupWithSender++;
        }
        assertEquals(6, replies);
        assertEquals("the fixture plants a reply of every allowed type", ReplyRule.ALLOWED, replyTypes);
        assertEquals(1, sendersExpected);
        assertEquals(1, receivedGroupWithSender);

        assertEquals(3, SelfTestChecks.CHATS.size());
        for (int i = 1; i < SelfTestChecks.CHATS.size(); i++) {
            assertTrue("distinct times, so newest-first order is tested",
                    SelfTestChecks.CHATS.get(i - 1).lastMessageSeconds > SelfTestChecks.CHATS.get(i).lastMessageSeconds);
        }
    }

    @Test
    public void theDisallowedTypeIsOutsideTheAllowedSet() {
        assertTrue(SelfTestChecks.DISALLOWED_TYPE >= 0);
        assertFalse(ReplyRule.ALLOWED.contains(SelfTestChecks.DISALLOWED_TYPE));
    }

    // ---- the planted schema --------------------------------------------------------------------

    @Test
    public void thePlantedSchemaIsExactlyWhatTheReaderRequires() {
        assertTrue(SchemaCheck.missing(sets(SelfTestChecks.plantedSchema())).isEmpty());
        assertTrue(SelfTestChecks.plantedExact(sets(SchemaCheck.REQUIRED)));
        // Every row uses only planted columns, and every planted column is given a value somewhere.
        Map<String, Set<String>> used = new HashMap<>();
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) {
            List<String> cols = SchemaCheck.REQUIRED.get(r.table);
            assertTrue("planted table " + r.table, cols != null);
            assertTrue(r.table + " row columns", cols.containsAll(r.values.keySet()));
            if (!used.containsKey(r.table)) used.put(r.table, new HashSet<String>());
            used.get(r.table).addAll(r.values.keySet());
        }
        assertEquals(sets(SchemaCheck.REQUIRED).keySet(), used.keySet());
        for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) {
            assertEquals(e.getKey(), new HashSet<>(e.getValue()), used.get(e.getKey()));
        }
    }

    @Test
    public void plantedExactRefusesAnythingElse() {
        Map<String, Set<String>> extraColumn = sets(SchemaCheck.REQUIRED);
        extraColumn.get("message").add("extra_column");
        assertFalse(SelfTestChecks.plantedExact(extraColumn));
        Map<String, Set<String>> extraTable = sets(SchemaCheck.REQUIRED);
        extraTable.put("extra_table", new HashSet<>(Arrays.asList("_id")));
        assertFalse(SelfTestChecks.plantedExact(extraTable));
        Map<String, Set<String>> missingTable = sets(SchemaCheck.REQUIRED);
        missingTable.remove("jid_map");
        assertFalse(SelfTestChecks.plantedExact(missingTable));
        assertFalse(SelfTestChecks.plantedExact(sets(SelfTestChecks.renamedSchema())));
        assertFalse(SelfTestChecks.plantedExact(null));
    }

    @Test
    public void theRenamedSchemaMissesExactlyOneRequiredName() throws Exception {
        assertEquals(Arrays.asList(SelfTestChecks.RENAMED_TABLE + "." + SelfTestChecks.RENAMED_COLUMN),
                SchemaCheck.missing(sets(SelfTestChecks.renamedSchema())));
        assertTrue(refusedBySchemaCheck(SelfTestChecks.renamedSchema()));
        assertEquals(SchemaCheck.REQUIRED.keySet(), SelfTestChecks.renamedSchema().keySet());
    }

    /**
     * The reader binds its since-time as a string; SQLite compares it as a number only against a
     * column with numeric affinity. So every column planted with numbers is declared INTEGER —
     * the timestamp above all — and every column planted with text is declared TEXT.
     */
    @Test
    public void everyPlantedValueSitsInAColumnOfItsType() {
        assertEquals("INTEGER", SelfTestChecks.columnType("message", "timestamp"));
        for (String tc : SelfTestChecks.TEXT_COLUMNS) {
            String[] p = tc.split("\\.");
            assertTrue(tc, SchemaCheck.REQUIRED.get(p[0]).contains(p[1]));
        }
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) {
            for (Map.Entry<String, Object> e : r.values.entrySet()) {
                if (e.getValue() == null) continue;
                String want = e.getValue() instanceof Long ? "INTEGER" : "TEXT";
                assertEquals(r.table + "." + e.getKey(), want, SelfTestChecks.columnType(r.table, e.getKey()));
            }
        }
        String message = SelfTestChecks.createStatements(SelfTestChecks.plantedSchema()).get(0);
        assertTrue(message, message.contains("\"timestamp\" INTEGER"));
        assertTrue(message, message.contains("\"key_id\" TEXT"));
    }

    @Test
    public void theCreateStatementsCarryEveryNameQuoted() {
        List<String> sql = SelfTestChecks.createStatements(SelfTestChecks.plantedSchema());
        assertEquals(SchemaCheck.REQUIRED.size(), sql.size());
        int i = 0;
        for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) {
            String s = sql.get(i++);
            assertTrue(s, s.startsWith("CREATE TABLE \"" + e.getKey() + "\" ("));
            for (String c : e.getValue()) assertTrue(s, s.contains("\"" + c + "\""));
        }
        String renamedChat = SelfTestChecks.createStatements(SelfTestChecks.renamedSchema()).get(1);
        assertTrue(renamedChat, renamedChat.startsWith("CREATE TABLE \"chat\""));
        assertTrue(renamedChat.contains("\"" + SelfTestChecks.RENAMED_TO + "\""));
        assertFalse(renamedChat.contains("\"" + SelfTestChecks.RENAMED_COLUMN + "\""));
    }

    // ---- the comparisons catch what they claim to ----------------------------------------------

    @Test
    public void aMissingRowFailsTheSinceAndFieldChecks() {
        Sim s = simulate(SelfTestChecks.plantedRows());
        s.messages.remove(0);
        List<String> failed = simulatedRun(s).failed();
        assertTrue(failed.toString(), failed.contains(SelfTestChecks.M_SINCE));
        assertTrue(failed.toString(), failed.contains(SelfTestChecks.M_FIELDS));
    }

    @Test
    public void aLostTypeFailsTheTypeAndReplyChecks() {
        Sim s = simulate(SelfTestChecks.plantedRows());
        for (int i = 0; i < s.messages.size(); i++) {
            WaMessage m = s.messages.get(i);
            if (m.fromMe && m.type == 9) s.messages.set(i, m.withType(-1));
        }
        List<String> failed = simulatedRun(s).failed();
        assertTrue(failed.toString(), failed.contains(SelfTestChecks.M_TYPE));
        assertTrue(failed.toString(), failed.contains(SelfTestChecks.R_ALLOWED));
        assertTrue(failed.toString(), failed.contains(SelfTestChecks.R_COUNT));
    }

    @Test
    public void aSenderKeptOnAFromMeRowFailsTheSenderCheck() {
        Sim s = simulate(SelfTestChecks.plantedRows());
        for (int i = 0; i < s.messages.size(); i++) {
            WaMessage m = s.messages.get(i);
            if (m.fromMe) s.messages.set(i, m.with(m.chatJid, SelfTestChecks.SENDER, m.timeMs));
        }
        assertEquals(Arrays.asList(SelfTestChecks.M_SENDER), simulatedRun(s).failed());
    }

    @Test
    public void wrongCountsFail() {
        Sim s = simulate(SelfTestChecks.plantedRows());
        s.withoutKeyId[0] = 0;
        s.withoutChat[0] = 2;
        assertEquals(Arrays.asList(SelfTestChecks.M_NO_KEY, SelfTestChecks.M_NO_CHAT), simulatedRun(s).failed());
    }

    @Test
    public void aHiddenIdLeftUnlinkedFailsTheCanonicalChecks() {
        List<SelfTestChecks.Row> rows = new ArrayList<>();
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) if (!r.table.equals("jid_map")) rows.add(r);
        List<String> failed = simulatedRun(simulate(rows)).failed();
        for (String n : new String[] {SelfTestChecks.M_LINKS, SelfTestChecks.C_COUNT, SelfTestChecks.C_ORDER,
                SelfTestChecks.C_CANON, SelfTestChecks.C_NAME}) {
            assertTrue(n + " in " + failed, failed.contains(n));
        }
    }

    @Test
    public void aLostNameOrSubjectFails() {
        List<SelfTestChecks.Row> rows = new ArrayList<>();
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) {
            if (r.table.equals("lid_display_name") || r.table.equals("chat") && r.values.get("subject") != null
                    && r.values.get("_id").equals(SelfTestChecks.CHAT_GROUP)) continue;
            rows.add(r);
        }
        // the group's chat row comes back without its subject
        rows.add(new SelfTestChecks.Row("chat", new LinkedHashMap<String, Object>() {{
            put("_id", SelfTestChecks.CHAT_GROUP);
            put("jid_row_id", SelfTestChecks.J_GROUP);
            put("subject", null);
        }}));
        List<String> failed = simulatedRun(simulate(rows)).failed();
        assertEquals(Arrays.asList(SelfTestChecks.C_SUBJECT, SelfTestChecks.C_NAME), failed);
    }

    @Test
    public void aComparisonThatThrowsIsNamedByTheCheckAndTheClass() {
        Sim s = simulate(SelfTestChecks.plantedRows());
        SelfTestChecks.Result r = new SelfTestChecks.Result();
        SelfTestChecks.messages(s.messages, 1, 1, null, r);
        assertEquals(Arrays.asList(SelfTestChecks.M_LINKS + " (NullPointerException)"), r.failed());
        assertEquals(SelfTestChecks.MESSAGE_CHECKS.length - 1, r.passed());
    }

    // ---- the result: names and counts, never content -------------------------------------------

    @Test
    public void theSummaryNamesFailuresAndCounts() {
        SelfTestChecks.Result r = new SelfTestChecks.Result();
        r.pass("a.one");
        r.check("a.two", false);
        r.threw("a.three", new IllegalStateException(SelfTestChecks.text(2)));
        r.notRun("a.four");
        assertEquals(1, r.passed());
        assertEquals(4, r.total());
        assertFalse(r.allPassed());
        assertEquals("Reader self-test: 1 of 4 passed — failed: a.two, a.three (IllegalStateException), a.four (not run)",
                r.summary());
        assertEquals(r.summary(), r.toString());
        assertFalse("an empty result is not a pass", new SelfTestChecks.Result().allPassed());
    }

    @Test
    public void aFailureIsNamedNotDescribed() {
        SelfTestChecks.Result r = new SelfTestChecks.Result();
        r.threw("x", new IllegalStateException(SelfTestChecks.text(3)));
        r.threw("y", new BackupException(BackupError.SCHEMA_CHANGED, SelfTestChecks.SUBJECT));
        r.threw("z", new RuntimeException(SelfTestChecks.PHONE) {});
        assertEquals(Arrays.asList("x (IllegalStateException)", "y (BackupException schema_changed)", "z (Exception)"),
                r.failed());
    }

    @Test
    public void noPlantedValueReachesAnyResult() {
        List<String> outputs = new ArrayList<>();
        outputs.add(simulatedRun(simulate(SelfTestChecks.plantedRows())).summary());
        // every check failed, the throwing ones carrying planted values in their messages
        SelfTestChecks.Result bad = new SelfTestChecks.Result();
        List<Object> planted = plantedValues();
        int i = 0;
        for (String name : SelfTestChecks.ALL) {
            String v = String.valueOf(planted.get(i++ % planted.size()));
            switch (i % 4) {
                case 0: bad.threw(name, new IllegalStateException(v)); break;
                case 1: bad.threw(name, new BackupException(BackupError.SCHEMA_CHANGED, v)); break;
                case 2: bad.notRun(name); break;
                default: bad.check(name, false);
            }
        }
        outputs.add(bad.summary());
        outputs.add(bad.failed().toString());
        // a run over mismatching reads
        Sim s = simulate(SelfTestChecks.plantedRows());
        s.messages.remove(0);
        outputs.add(simulatedRun(s).summary());
        outputs.add(new SelfTestChecks.Result().summary());
        for (String out : outputs) {
            for (Object v : planted) {
                assertFalse("a planted value reached a result", out.contains(String.valueOf(v)));
            }
        }
    }

    /** Every String in the planted rows, and every number long enough to be recognisable. */
    static List<Object> plantedValues() {
        List<Object> out = new ArrayList<>();
        for (SelfTestChecks.Row r : SelfTestChecks.plantedRows()) {
            for (Object v : r.values.values()) {
                if (v instanceof String) out.add(v);
                else if (v instanceof Long && (Long) v >= 1000) out.add(v);
            }
        }
        assertTrue(out.size() > 40);
        return out;
    }

    // ---- where the on-device half works --------------------------------------------------------

    @Test
    public void theSelfTestWorksInItsOwnFolderAndDeletesSideFiles() throws IOException {
        assertEquals("wa_selftest", SelfTest.DIR);
        assertNotEquals("wa_work", SelfTest.DIR);
        File src = new File("src/main/java/com/mike/metatron/whatsapp/SelfTest.java");
        String code = new String(Files.readAllBytes(src.toPath()), StandardCharsets.UTF_8);
        assertFalse("never the nightly read's folder", code.contains("WaFiles.workDir"));
        assertTrue(code.contains("getNoBackupFilesDir()"));
        for (String side : new String[] {"\"-journal\"", "\"-wal\"", "\"-shm\""}) assertTrue(side, code.contains(side));
        assertTrue("deletion runs in finally", code.contains("} finally {\n            delete(planted);\n            delete(renamed);"));
    }
}
