package com.mike.metatron.whatsapp;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.io.File;
import java.util.ArrayList;
import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeMap;

/**
 * The user's chats, for choosing which Metatron may see (Phase 2 plan § 2 item 5, § 3.9): per chat
 * its canonical id, kind, group subject, the hidden id's own WhatsApp display name, and its last
 * message time in whole seconds — newest activity first.
 *
 * Two halves. {@link #read} is Android-only (SQLite): it checks the schema, then reads the chat,
 * jid, jid_map and lid_display_name tables and each chat's newest message time from a decrypted
 * full backup; it is exercised by the on-device self-test. Everything else — the row model, the
 * {@link #fold} through the increments' chat, jid, jid_map and lid_display_name deltas, and the
 * resolution into {@link Chat}s — is platform-free.
 *
 * Group subjects and display names are set by other people, so are untrusted; a display name is
 * for the phone's screen only and never leaves it. {@link #toString} carries counts only.
 */
public final class ChatList {
    public static final String GROUP = "group", ONE_TO_ONE = "one_to_one";

    /** One chat, resolved. */
    public static final class Chat {
        /** Canonical chat id. */
        public final String id;
        /** {@link #GROUP} when the canonical id ends {@code @g.us}, else {@link #ONE_TO_ONE}. */
        public final String kind;
        /** Group subject; null for a one-to-one or a group without one. */
        public final String subject;
        /** One-to-one only: the hidden id's lid_display_name — the person's own WhatsApp name; null when none. */
        public final String displayName;
        /** Newest message time, whole seconds; 0 when no message is known. */
        public final long lastMessageSeconds;

        Chat(String id, String kind, String subject, String displayName, long lastMessageSeconds) {
            this.id = id;
            this.kind = kind;
            this.subject = subject;
            this.displayName = displayName;
            this.lastMessageSeconds = lastMessageSeconds;
        }

        /** Deliberately no id, subject or name. */
        @Override
        public String toString() {
            return "Chat(" + kind + ")";
        }
    }

    /** A chat table row: its jid row and subject. */
    static final class ChatRow {
        final long jidRowId;
        final String subject;

        ChatRow(long jidRowId, String subject) {
            this.jidRowId = jidRowId;
            this.subject = subject;
        }
    }

    /** Newest activity first, then by id: the same tables always give the same order. */
    public final List<Chat> chats;
    /** Chat rows whose jid row is not in the jid table, so have no id. Not listed; expected 0. */
    public final int withoutJid;

    // The source tables, kept so the increments can be folded in. Not modified once built.
    final BackupCombiner.JidTables jids;
    final Map<Long, ChatRow> chatRows;
    final Map<Long, String> displayNames;
    /** chat._id → newest message second, from the full backup. */
    final Map<Long, Long> lastByChatRow;
    /** Raw chat jid → newest message second, from the increments' messages. */
    final Map<String, Long> lastByRawJid;

    ChatList(BackupCombiner.JidTables jids, Map<Long, ChatRow> chatRows, Map<Long, String> displayNames,
             Map<Long, Long> lastByChatRow, Map<String, Long> lastByRawJid) {
        this.jids = jids;
        this.chatRows = chatRows;
        this.displayNames = displayNames;
        this.lastByChatRow = lastByChatRow;
        this.lastByRawJid = lastByRawJid;
        int[] noJid = {0};
        this.chats = Collections.unmodifiableList(resolve(noJid));
        this.withoutJid = noJid[0];
    }

    // ---- the Android half ----------------------------------------------------------------------

    /** The full backup's chat list. Checks the schema (names only) before any query. */
    public static ChatList read(File database) throws BackupException {
        SQLiteDatabase db = SQLiteDatabase.openDatabase(database.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            BackupSchema.require(db);
            BackupCombiner.JidTables t = new BackupCombiner.JidTables();
            try (Cursor c = db.rawQuery("SELECT _id, raw_string FROM jid WHERE raw_string IS NOT NULL", null)) {
                while (c.moveToNext()) t.putJid(c.getLong(0), c.getString(1));
            }
            try (Cursor c = db.rawQuery("SELECT lid_row_id, jid_row_id FROM jid_map", null)) {
                while (c.moveToNext()) t.putLink(c.getLong(0), c.getLong(1));
            }
            Map<Long, ChatRow> chats = new TreeMap<>();
            try (Cursor c = db.rawQuery("SELECT _id, jid_row_id, subject FROM chat WHERE jid_row_id IS NOT NULL", null)) {
                while (c.moveToNext()) chats.put(c.getLong(0), new ChatRow(c.getLong(1), c.isNull(2) ? null : c.getString(2)));
            }
            Map<Long, String> names = new TreeMap<>();
            try (Cursor c = db.rawQuery("SELECT lid_row_id, display_name FROM lid_display_name WHERE display_name IS NOT NULL", null)) {
                while (c.moveToNext()) names.put(c.getLong(0), c.getString(1));
            }
            Map<Long, Long> last = new TreeMap<>();
            try (Cursor c = db.rawQuery("SELECT chat_row_id, MAX(timestamp) FROM message WHERE chat_row_id IS NOT NULL "
                    + "GROUP BY chat_row_id", null)) {
                while (c.moveToNext()) if (!c.isNull(1)) last.put(c.getLong(0), c.getLong(1) / 1000);
            }
            return new ChatList(t, chats, names, last, new TreeMap<String, Long>());
        } finally {
            db.close();
        }
    }

    // ---- the platform-free half ----------------------------------------------------------------

    /**
     * This list with the set's increments folded in, N = 1..k in order: jid and jid_map as the
     * combiner folds them; chat rows upserted or deleted by chat._id; display names by
     * lid_row_id; and each increment message's second as its chat's activity. A delta keyed by
     * another column, or a row without its key column, is refused as
     * {@link BackupError#INCREMENT_MISSING_PART} — never read as "no value", which would drop or
     * mislabel chats silently. A row without its subject or display_name keeps the one it had.
     * This list is not modified.
     */
    public ChatList fold(List<Increment> increments) throws BackupException {
        for (int i = 0; i < increments.size(); i++) {
            if (increments.get(i).number != i + 1) {
                throw new BackupException(BackupError.INCREMENT_GAP, "increment " + (i + 1) + " missing; " + i + " readable before it");
            }
        }
        BackupCombiner.JidTables t = jids.copy();
        Map<Long, ChatRow> rows = new TreeMap<>(chatRows);
        Map<Long, String> names = new TreeMap<>(displayNames);
        Map<Long, Long> last = new TreeMap<>(lastByChatRow);
        Map<String, Long> lastRaw = new TreeMap<>(lastByRawJid);
        for (Increment inc : increments) {
            t.fold(inc);
            foldChats(inc.tables.get("chat"), rows, last);
            foldNames(inc.tables.get("lid_display_name"), names);
            for (WaMessage m : inc.messages) {
                long s = BackupCombiner.second(m.timeMs);
                Long prev = lastRaw.get(m.chatJid);
                if (prev == null || s > prev) lastRaw.put(m.chatJid, s);
            }
        }
        return new ChatList(t, rows, names, last, lastRaw);
    }

    private static void foldChats(Increment.TableDelta d, Map<Long, ChatRow> rows, Map<Long, Long> last) throws BackupException {
        if (d == null) return;
        if (!"_id".equals(d.idField)) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "chat keyed by _id");
        for (Long id : d.deletedIds) {
            rows.remove(id);
            last.remove(id);
        }
        for (Map<String, Object> row : d.modified) {
            long id = integer(row, "_id", "chat");
            long jid = integer(row, "jid_row_id", "chat");
            ChatRow prev = rows.get(id);
            String subject = prev == null ? null : prev.subject;
            if (row.containsKey("subject")) subject = text(row.get("subject"), "chat row's subject");
            rows.put(id, new ChatRow(jid, subject));
        }
    }

    private static void foldNames(Increment.TableDelta d, Map<Long, String> names) throws BackupException {
        if (d == null) return;
        if (!"lid_row_id".equals(d.idField)) {
            throw new BackupException(BackupError.INCREMENT_MISSING_PART, "lid_display_name keyed by lid_row_id");
        }
        for (Long id : d.deletedIds) names.remove(id);
        for (Map<String, Object> row : d.modified) {
            long id = integer(row, "lid_row_id", "lid_display_name");
            if (!row.containsKey("display_name")) continue;
            String n = text(row.get("display_name"), "lid_display_name row's display_name");
            if (n == null) names.remove(id);
            else names.put(id, n);
        }
    }

    private static long integer(Map<String, Object> row, String field, String table) throws BackupException {
        Object v = row.get(field);
        if (!(v instanceof Long)) throw new BackupException(BackupError.INCREMENT_MISSING_PART, table + " row's " + field);
        return (Long) v;
    }

    private static String text(Object v, String what) throws BackupException {
        if (v == null || v instanceof String) return (String) v;
        throw new BackupException(BackupError.INCREMENT_MALFORMED, what + " is not text");
    }

    /** The tables as they stand → one Chat per canonical id. */
    private List<Chat> resolve(int[] withoutJid) {
        BackupCombiner.Canon canon = new BackupCombiner.Canon(jids);
        final class Acc {
            String subject, displayName;
            long last;
        }
        Map<String, Acc> byId = new TreeMap<>();
        for (Map.Entry<Long, ChatRow> e : chatRows.entrySet()) {
            String raw = jids.raw.get(e.getValue().jidRowId);
            if (raw == null) { withoutJid[0]++; continue; }
            String id = canon.of(raw);
            Acc a = byId.get(id);
            if (a == null) {
                a = new Acc();
                byId.put(id, a);
            }
            // One chat under both its ids: the lowest chat._id with a subject gives it.
            if (a.subject == null) a.subject = e.getValue().subject;
            Long s = lastByChatRow.get(e.getKey());
            if (s != null && s > a.last) a.last = s;
        }
        for (Map.Entry<String, Long> e : lastByRawJid.entrySet()) {
            Acc a = byId.get(canon.of(e.getKey()));
            if (a != null && e.getValue() > a.last) a.last = e.getValue();
        }
        // A display name belongs to whichever chat its hidden id canonicalises to; lowest lid_row_id first.
        for (Map.Entry<Long, String> e : displayNames.entrySet()) {
            String raw = jids.raw.get(e.getKey());
            if (raw == null) continue;
            Acc a = byId.get(canon.of(raw));
            if (a != null && a.displayName == null) a.displayName = e.getValue();
        }
        List<Chat> out = new ArrayList<>();
        for (Map.Entry<String, Acc> e : byId.entrySet()) {
            boolean group = e.getKey().endsWith("@g.us");
            Acc a = e.getValue();
            out.add(new Chat(e.getKey(), group ? GROUP : ONE_TO_ONE, group ? a.subject : null,
                    group ? null : a.displayName, a.last));
        }
        Collections.sort(out, (x, y) -> x.lastMessageSeconds != y.lastMessageSeconds
                ? Long.compare(y.lastMessageSeconds, x.lastMessageSeconds) : x.id.compareTo(y.id));
        return out;
    }

    /** By canonical id, for lookups. */
    public Map<String, Chat> byId() {
        Map<String, Chat> m = new LinkedHashMap<>();
        for (Chat c : chats) m.put(c.id, c);
        return m;
    }

    /** Counts only — never an id, subject or name. */
    @Override
    public String toString() {
        return "ChatList(" + chats.size() + " chats, " + withoutJid + " without a jid)";
    }
}
