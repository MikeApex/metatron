package com.mike.metatron.whatsapp;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * The reader self-test's plain-Java half (Phase 2 plan § 1, § 7 item 7): the synthetic database
 * {@link SelfTest} plants, what the reader must return from it, the comparisons, and the result.
 * Platform-free, so the fixture and its expected outcomes are JVM-tested; the SQL half of
 * {@link FullBackupMessages#read} and {@link ChatList#read} runs only on the phone, against this.
 *
 * Every value here is made up. The {@link Result} carries check names and counts only — never a
 * row value — and a check that throws is named with its exception's simple class name.
 */
final class SelfTestChecks {
    private SelfTestChecks() {}

    // ---- the check names: one fixed set, so every run reports the same total -----------------

    static final String M_READ = "messages.read", M_SINCE = "messages.since", M_FIELDS = "messages.fields",
            M_TYPE = "messages.type", M_CONTENT = "messages.hasContent", M_SENDER = "messages.sender",
            M_NO_KEY = "messages.withoutKeyId", M_NO_CHAT = "messages.withoutChat", M_LINKS = "messages.jidLinks";
    static final String R_ALLOWED = "reply.allowedFromMe", R_DISALLOWED = "reply.disallowedType",
            R_UNKNOWN = "reply.unknownType", R_RECEIVED = "reply.received", R_COUNT = "reply.count";
    static final String C_READ = "chats.read", C_COUNT = "chats.count", C_ORDER = "chats.order", C_KIND = "chats.kind",
            C_SUBJECT = "chats.subject", C_NAME = "chats.displayName", C_LAST = "chats.lastMessage",
            C_CANON = "chats.canonical";
    static final String S_PLANTED = "schema.planted", S_MESSAGES = "schema.messagesRefused",
            S_CHATS = "schema.chatsRefused";
    static final String CLEANUP = "cleanup.deleted";

    /** Run after a successful {@link FullBackupMessages#read}; not run (failed) when it threw. */
    static final String[] MESSAGE_CHECKS = {M_SINCE, M_FIELDS, M_TYPE, M_CONTENT, M_SENDER, M_NO_KEY, M_NO_CHAT, M_LINKS};
    /** {@link ReplyRule#isReply} over the rows read; not run when the read threw. */
    static final String[] REPLY_CHECKS = {R_ALLOWED, R_DISALLOWED, R_UNKNOWN, R_RECEIVED, R_COUNT};
    /** Run after a successful {@link ChatList#read}; not run when it threw. */
    static final String[] CHAT_CHECKS = {C_COUNT, C_ORDER, C_KIND, C_SUBJECT, C_NAME, C_LAST, C_CANON};

    /** Every check a run reports, in order. */
    static final List<String> ALL;

    static {
        List<String> a = new ArrayList<>();
        a.add(S_PLANTED);
        a.add(M_READ);
        Collections.addAll(a, MESSAGE_CHECKS);
        Collections.addAll(a, REPLY_CHECKS);
        a.add(C_READ);
        Collections.addAll(a, CHAT_CHECKS);
        a.add(S_MESSAGES);
        a.add(S_CHATS);
        a.add(CLEANUP);
        ALL = Collections.unmodifiableList(a);
    }

    // ---- the fixture ---------------------------------------------------------------------------

    /** Messages are read from the start of this whole second on. */
    static final long SINCE_SECONDS = 1_700_000_000L;

    // jid rows: a phone-number id, a hidden id linked to it by jid_map, a group, a hidden id with
    // no link, and a group member who sends.
    static final long J_PHONE = 1, J_HIDDEN_LINKED = 2, J_GROUP = 3, J_HIDDEN_ALONE = 4, J_SENDER = 5;
    static final String PHONE = "100000000001@s.whatsapp.net", HIDDEN_LINKED = "200000000002@lid",
            GROUP = "300000000003@g.us", HIDDEN_ALONE = "200000000004@lid", SENDER = "100000000005@s.whatsapp.net";
    // chat rows: the phone id and the linked hidden id are one chat under two ids. CHAT_ABSENT has no row.
    static final long CHAT_PHONE = 10, CHAT_HIDDEN_LINKED = 11, CHAT_GROUP = 12, CHAT_HIDDEN_ALONE = 13, CHAT_ABSENT = 77;

    static final String SUBJECT = "selftest-planted-subject",
            SUBJECT_ON_ONE_TO_ONE = "selftest-planted-subject-not-shown",
            NAME_LINKED = "selftest-planted-name-linked", NAME_ALONE = "selftest-planted-name-alone";

    /** A type outside {@link ReplyRule#ALLOWED} — the first non-negative one, so it stays outside if the set changes. */
    static final int DISALLOWED_TYPE = firstOutside(ReplyRule.ALLOWED);

    static String text(int n) {
        return "selftest-planted-text-" + n;
    }

    static String key(int n) {
        return "SELFTEST-K" + n;
    }

    /** A timestamp in ms: this many seconds after the since-second, plus a few ms. */
    static long ms(int secondsAfter, int extraMs) {
        return (SINCE_SECONDS + secondsAfter) * 1000L + extraMs;
    }

    /** One row to insert: its table and column → value (Long, String or null). */
    static final class Row {
        final String table;
        final Map<String, Object> values;

        Row(String table, Map<String, Object> values) {
            this.table = table;
            this.values = Collections.unmodifiableMap(values);
        }
    }

    /** The planted schema: exactly {@link SchemaCheck#REQUIRED}, nothing beyond it. */
    static Map<String, List<String>> plantedSchema() {
        return SchemaCheck.REQUIRED;
    }

    static final String RENAMED_TABLE = "chat", RENAMED_COLUMN = "jid_row_id", RENAMED_TO = "jid_row_id_renamed";

    /**
     * The planted schema with one required column renamed. chat.jid_row_id is read by both
     * {@link FullBackupMessages#read} and {@link ChatList#read}, so without the schema check each
     * query would fail inside SQLite instead of refusing by name.
     */
    static Map<String, List<String>> renamedSchema() {
        Map<String, List<String>> m = new LinkedHashMap<>();
        for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) {
            List<String> cols = new ArrayList<>(e.getValue());
            if (e.getKey().equals(RENAMED_TABLE)) cols.set(cols.indexOf(RENAMED_COLUMN), RENAMED_TO);
            m.put(e.getKey(), Collections.unmodifiableList(cols));
        }
        return Collections.unmodifiableMap(m);
    }

    /** The planted columns holding text; every other planted column holds a number. */
    static final Set<String> TEXT_COLUMNS = Collections.unmodifiableSet(new HashSet<>(java.util.Arrays.asList(
            "message.key_id", "message.text_data", "chat.subject", "jid.server", "jid.user", "jid.raw_string",
            "lid_display_name.display_name")));

    /**
     * A column's declared type: TEXT for {@link #TEXT_COLUMNS}, else INTEGER. The type matters:
     * {@link FullBackupMessages#read} binds its since-time as a string, which SQLite compares as a
     * number only against a column with numeric affinity — a typeless column would compare every
     * row as less than the string, and the read would wrongly return nothing.
     */
    static String columnType(String table, String column) {
        return TEXT_COLUMNS.contains(table + "." + column) ? "TEXT" : "INTEGER";
    }

    /** CREATE TABLE statements for a schema, each column with its {@link #columnType}. */
    static List<String> createStatements(Map<String, List<String>> schema) {
        List<String> out = new ArrayList<>();
        for (Map.Entry<String, List<String>> e : schema.entrySet()) {
            StringBuilder sb = new StringBuilder("CREATE TABLE ").append(quote(e.getKey())).append(" (");
            for (int i = 0; i < e.getValue().size(); i++) {
                String c = e.getValue().get(i);
                sb.append(i == 0 ? "" : ", ").append(quote(c)).append(' ').append(columnType(e.getKey(), c));
            }
            out.add(sb.append(")").toString());
        }
        return out;
    }

    /** The planted database's rows, in insert order. */
    static List<Row> plantedRows() {
        List<Row> r = new ArrayList<>();
        r.add(jid(J_PHONE, PHONE));
        r.add(jid(J_HIDDEN_LINKED, HIDDEN_LINKED));
        r.add(jid(J_GROUP, GROUP));
        r.add(jid(J_HIDDEN_ALONE, HIDDEN_ALONE));
        r.add(jid(J_SENDER, SENDER));
        r.add(row("jid_map", "lid_row_id", J_HIDDEN_LINKED, "jid_row_id", J_PHONE));
        r.add(row("lid_display_name", "lid_row_id", J_HIDDEN_LINKED, "display_name", NAME_LINKED));
        r.add(row("lid_display_name", "lid_row_id", J_HIDDEN_ALONE, "display_name", NAME_ALONE));
        r.add(row("chat", "_id", CHAT_PHONE, "jid_row_id", J_PHONE, "subject", null));
        r.add(row("chat", "_id", CHAT_HIDDEN_LINKED, "jid_row_id", J_HIDDEN_LINKED, "subject", null));
        r.add(row("chat", "_id", CHAT_GROUP, "jid_row_id", J_GROUP, "subject", SUBJECT));
        r.add(row("chat", "_id", CHAT_HIDDEN_ALONE, "jid_row_id", J_HIDDEN_ALONE, "subject", SUBJECT_ON_ONE_TO_ONE));
        // _id, key_id, timestamp, from_me, chat_row_id, sender_jid_row_id, text_data, message_type
        r.add(message(1001, key(1), ms(-1, 999), false, CHAT_PHONE, null, text(1), 0L)); // before the since-second
        r.add(message(1002, key(2), ms(0, 0), true, CHAT_PHONE, null, text(2), 0L));     // the since-second itself
        r.add(message(1003, key(3), ms(1, 250), false, CHAT_HIDDEN_LINKED, J_SENDER, text(3), 0L));
        r.add(message(1004, key(4), ms(2, 0), false, CHAT_GROUP, J_SENDER, text(4), 1L));
        r.add(message(1005, key(5), ms(3, 0), true, CHAT_GROUP, J_SENDER, text(5), 9L));
        r.add(message(1006, key(6), ms(4, 0), true, CHAT_HIDDEN_ALONE, null, null, 2L));
        r.add(message(1007, key(7), ms(5, 0), true, CHAT_PHONE, null, text(7), 3L));
        r.add(message(1008, key(8), ms(6, 0), true, CHAT_GROUP, null, text(8), 4L));
        r.add(message(1009, key(9), ms(7, 0), true, CHAT_HIDDEN_ALONE, null, text(9), 1L));
        r.add(message(1010, key(10), ms(8, 0), true, CHAT_PHONE, null, text(10), (long) DISALLOWED_TYPE));
        r.add(message(1011, key(11), ms(9, 0), true, CHAT_HIDDEN_LINKED, null, text(11), null)); // type unknown
        r.add(message(1012, null, ms(10, 0), true, CHAT_HIDDEN_ALONE, null, text(12), 0L));     // no key_id
        r.add(message(1013, key(13), ms(11, 0), false, CHAT_ABSENT, null, text(13), 0L));       // no chat
        return r;
    }

    // ---- the expected outcomes, stated independently of the rows -------------------------------

    static final class ExpectedMessage {
        final String keyId, chatJid, senderJid, text;
        final long rowId, timeMs;
        final boolean fromMe, reply;
        final int type;

        ExpectedMessage(String keyId, long rowId, String chatJid, boolean fromMe, long timeMs, String senderJid,
                        String text, int type, boolean reply) {
            this.keyId = keyId;
            this.rowId = rowId;
            this.chatJid = chatJid;
            this.fromMe = fromMe;
            this.timeMs = timeMs;
            this.senderJid = senderJid;
            this.text = text;
            this.type = type;
            this.reply = reply;
        }
    }

    /**
     * What {@link FullBackupMessages#read} returns from the since-second: raw chat ids (the read
     * does not canonicalise), the sender only on the received group row, a null type as -1.
     */
    static final List<ExpectedMessage> MESSAGES = Collections.unmodifiableList(java.util.Arrays.asList(
            new ExpectedMessage(key(2), 1002, PHONE, true, ms(0, 0), null, text(2), 0, true),
            new ExpectedMessage(key(3), 1003, HIDDEN_LINKED, false, ms(1, 250), null, text(3), 0, false),
            new ExpectedMessage(key(4), 1004, GROUP, false, ms(2, 0), SENDER, text(4), 1, false),
            new ExpectedMessage(key(5), 1005, GROUP, true, ms(3, 0), null, text(5), 9, true),
            new ExpectedMessage(key(6), 1006, HIDDEN_ALONE, true, ms(4, 0), null, null, 2, true),
            new ExpectedMessage(key(7), 1007, PHONE, true, ms(5, 0), null, text(7), 3, true),
            new ExpectedMessage(key(8), 1008, GROUP, true, ms(6, 0), null, text(8), 4, true),
            new ExpectedMessage(key(9), 1009, HIDDEN_ALONE, true, ms(7, 0), null, text(9), 1, true),
            new ExpectedMessage(key(10), 1010, PHONE, true, ms(8, 0), null, text(10), DISALLOWED_TYPE, false),
            new ExpectedMessage(key(11), 1011, HIDDEN_LINKED, true, ms(9, 0), null, text(11), -1, false)));
    static final int EXPECTED_WITHOUT_KEY_ID = 1, EXPECTED_WITHOUT_CHAT = 1;

    static final class ExpectedChat {
        final String id, kind, subject, displayName;
        final long lastMessageSeconds;

        ExpectedChat(String id, String kind, String subject, String displayName, long lastMessageSeconds) {
            this.id = id;
            this.kind = kind;
            this.subject = subject;
            this.displayName = displayName;
            this.lastMessageSeconds = lastMessageSeconds;
        }
    }

    /**
     * What {@link ChatList#read} returns, newest first: the phone id and its linked hidden id as one
     * chat whose newest message came under the hidden id; the subject on the group only; each
     * one-to-one's name from the hidden id that canonicalises to it.
     */
    static final List<ExpectedChat> CHATS = Collections.unmodifiableList(java.util.Arrays.asList(
            new ExpectedChat(HIDDEN_ALONE, ChatList.ONE_TO_ONE, null, NAME_ALONE, SINCE_SECONDS + 10),
            new ExpectedChat(PHONE, ChatList.ONE_TO_ONE, null, NAME_LINKED, SINCE_SECONDS + 9),
            new ExpectedChat(GROUP, ChatList.GROUP, SUBJECT, null, SINCE_SECONDS + 6)));

    // ---- the comparisons -----------------------------------------------------------------------

    /** The planted database's tables and their columns are exactly {@link SchemaCheck#REQUIRED}'s. */
    static boolean plantedExact(Map<String, Set<String>> actual) {
        if (actual == null || !actual.keySet().equals(SchemaCheck.REQUIRED.keySet())) return false;
        for (Map.Entry<String, List<String>> e : SchemaCheck.REQUIRED.entrySet()) {
            if (!new HashSet<>(e.getValue()).equals(actual.get(e.getKey()))) return false;
        }
        return true;
    }

    /** The {@link #MESSAGE_CHECKS} over what {@link FullBackupMessages#read} returned. */
    static void messages(final List<WaMessage> got, final int withoutKeyId, final int withoutChat,
                         final BackupCombiner.JidTables tables, Result r) {
        final Map<String, WaMessage> byKey = new HashMap<>();
        for (WaMessage m : got) byKey.put(m.keyId, m);
        r.check(M_SINCE, () -> {
            Set<String> want = new HashSet<>();
            for (ExpectedMessage e : MESSAGES) want.add(e.keyId);
            return got.size() == MESSAGES.size() && byKey.keySet().equals(want);
        });
        r.check(M_FIELDS, () -> everyExpected(byKey, (m, e) -> m.rowId == e.rowId && eq(m.chatJid, e.chatJid)
                && m.fromMe == e.fromMe && m.timeMs == e.timeMs && eq(m.text, e.text)));
        r.check(M_TYPE, () -> everyExpected(byKey, (m, e) -> m.type == e.type));
        r.check(M_CONTENT, () -> {
            for (WaMessage m : got) if (m.hasContent != null) return false;
            return !got.isEmpty();
        });
        r.check(M_SENDER, () -> everyExpected(byKey, (m, e) -> eq(m.senderJid, e.senderJid)));
        r.check(M_NO_KEY, () -> withoutKeyId == EXPECTED_WITHOUT_KEY_ID);
        r.check(M_NO_CHAT, () -> withoutChat == EXPECTED_WITHOUT_CHAT);
        r.check(M_LINKS, () -> {
            BackupCombiner.Canon c = new BackupCombiner.Canon(tables);
            return PHONE.equals(c.of(HIDDEN_LINKED)) && HIDDEN_ALONE.equals(c.of(HIDDEN_ALONE)) && GROUP.equals(c.of(GROUP));
        });
    }

    /** The {@link #REPLY_CHECKS}: {@link ReplyRule#isReply} over the rows read. */
    static void replies(final List<WaMessage> got, Result r) {
        r.check(R_ALLOWED, () -> {
            Set<Integer> seen = new HashSet<>();
            for (WaMessage m : got) {
                if (!m.fromMe || !ReplyRule.ALLOWED.contains(m.type)) continue;
                if (!ReplyRule.isReply(m)) return false;
                seen.add(m.type);
            }
            return seen.equals(ReplyRule.ALLOWED); // the fixture plants every allowed type
        });
        r.check(R_DISALLOWED, () -> noneReply(got, true, DISALLOWED_TYPE));
        r.check(R_UNKNOWN, () -> noneReply(got, true, -1));
        r.check(R_RECEIVED, () -> noneReply(got, false, null));
        r.check(R_COUNT, () -> {
            Set<String> want = new HashSet<>(), seen = new HashSet<>();
            for (ExpectedMessage e : MESSAGES) if (e.reply) want.add(e.keyId);
            for (WaMessage m : got) if (ReplyRule.isReply(m)) seen.add(m.keyId);
            return seen.equals(want);
        });
    }

    /** The {@link #CHAT_CHECKS} over what {@link ChatList#read} returned. */
    static void chats(final ChatList list, Result r) {
        final Map<String, ChatList.Chat> byId = list.byId();
        r.check(C_COUNT, () -> list.chats.size() == CHATS.size());
        r.check(C_ORDER, () -> {
            if (list.chats.size() != CHATS.size()) return false;
            for (int i = 0; i < CHATS.size(); i++) if (!CHATS.get(i).id.equals(list.chats.get(i).id)) return false;
            return true;
        });
        r.check(C_KIND, () -> everyChat(byId, (c, e) -> eq(c.kind, e.kind)));
        r.check(C_SUBJECT, () -> everyChat(byId, (c, e) -> eq(c.subject, e.subject)));
        r.check(C_NAME, () -> everyChat(byId, (c, e) -> eq(c.displayName, e.displayName)));
        r.check(C_LAST, () -> everyChat(byId, (c, e) -> c.lastMessageSeconds == e.lastMessageSeconds));
        r.check(C_CANON, () -> byId.containsKey(PHONE) && !byId.containsKey(HIDDEN_LINKED) && list.withoutJid == 0);
    }

    // ---- the result ----------------------------------------------------------------------------

    interface Cond {
        boolean ok();
    }

    /** Pass/fail counts and failed check names. Never a row value, never an exception's message. */
    static final class Result {
        final List<String> passedNames = new ArrayList<>();
        private final List<String> failed = new ArrayList<>();

        void pass(String name) {
            passedNames.add(name);
        }

        void check(String name, boolean ok) {
            if (ok) passedNames.add(name);
            else failed.add(name);
        }

        /** Runs a comparison; one that throws is a failure named by the check and the exception's class. */
        void check(String name, Cond c) {
            boolean ok;
            try {
                ok = c.ok();
            } catch (RuntimeException e) {
                threw(name, e);
                return;
            }
            check(name, ok);
        }

        void threw(String name, Throwable t) {
            failed.add(name + " (" + describe(t) + ")");
        }

        /** Checks that could not run because what they compare was never read. */
        void notRun(String... names) {
            for (String n : names) failed.add(n + " (not run)");
        }

        int passed() {
            return passedNames.size();
        }

        int total() {
            return passedNames.size() + failed.size();
        }

        List<String> failed() {
            return Collections.unmodifiableList(failed);
        }

        boolean allPassed() {
            return failed.isEmpty() && !passedNames.isEmpty();
        }

        /** e.g. "Reader self-test: 26 of 26 passed", or the same with "— failed: name, name". */
        String summary() {
            StringBuilder sb = new StringBuilder("Reader self-test: ")
                    .append(passed()).append(" of ").append(total()).append(" passed");
            for (int i = 0; i < failed.size(); i++) sb.append(i == 0 ? " — failed: " : ", ").append(failed.get(i));
            return sb.toString();
        }

        @Override
        public String toString() {
            return summary();
        }
    }

    /** The exception's simple class name, plus a BackupException's code — both code-written. */
    static String describe(Throwable t) {
        String n = t.getClass().getSimpleName();
        if (n.isEmpty()) n = "Exception";
        if (t instanceof BackupException && ((BackupException) t).error != null) n += " " + ((BackupException) t).error.code;
        return n;
    }

    // ---- helpers -------------------------------------------------------------------------------

    private interface MessageMatch {
        boolean ok(WaMessage m, ExpectedMessage e);
    }

    private interface ChatMatch {
        boolean ok(ChatList.Chat c, ExpectedChat e);
    }

    private static boolean everyExpected(Map<String, WaMessage> byKey, MessageMatch match) {
        for (ExpectedMessage e : MESSAGES) {
            WaMessage m = byKey.get(e.keyId);
            if (m == null || !match.ok(m, e)) return false;
        }
        return true;
    }

    private static boolean everyChat(Map<String, ChatList.Chat> byId, ChatMatch match) {
        for (ExpectedChat e : CHATS) {
            ChatList.Chat c = byId.get(e.id);
            if (c == null || !match.ok(c, e)) return false;
        }
        return true;
    }

    /** At least one row read with this from-me and type (null: any type), and none of them a reply. */
    private static boolean noneReply(List<WaMessage> got, boolean fromMe, Integer type) {
        int n = 0;
        for (WaMessage m : got) {
            if (m.fromMe != fromMe || (type != null && m.type != type)) continue;
            n++;
            if (ReplyRule.isReply(m)) return false;
        }
        return n > 0;
    }

    private static boolean eq(Object a, Object b) {
        return a == null ? b == null : a.equals(b);
    }

    private static int firstOutside(Set<Integer> set) {
        int t = 0;
        while (set.contains(t)) t++;
        return t;
    }

    private static String quote(String name) {
        return "\"" + name.replace("\"", "\"\"") + "\"";
    }

    private static Row jid(long id, String raw) {
        int at = raw.indexOf('@');
        return row("jid", "_id", id, "server", raw.substring(at + 1), "user", raw.substring(0, at), "raw_string", raw);
    }

    private static Row message(long id, String keyId, long timestampMs, boolean fromMe, long chat, Long sender,
                               String text, Long type) {
        return row("message", "_id", id, "key_id", keyId, "timestamp", timestampMs, "from_me", fromMe ? 1L : 0L,
                "chat_row_id", chat, "sender_jid_row_id", sender, "text_data", text, "message_type", type);
    }

    private static Row row(String table, Object... kv) {
        Map<String, Object> v = new LinkedHashMap<>();
        for (int i = 0; i < kv.length; i += 2) {
            Object val = kv[i + 1];
            v.put((String) kv[i], val instanceof Integer ? Long.valueOf((Integer) val) : val);
        }
        return new Row(table, v);
    }
}
