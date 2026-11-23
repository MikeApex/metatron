package com.mike.metatron.whatsapp;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Reads what {@link BackupCombiner} starts from out of a decrypted full backup: its messages since
 * a whole second, and its jid / jid_map tables. Android-only (SQLite); everything after it is platform-free.
 * Opens read-only, closes before returning, and returns no column the reader does not use. The
 * caller owns the decrypted file and deletes it ({@link BackupDecryptor#deleteDecrypted}).
 */
public final class FullBackupMessages {
    public final List<WaMessage> messages;
    public final BackupCombiner.JidTables tables;
    /** Rows since the since-time that carry no key_id, so cannot be keyed. Reported, not returned. */
    public final int withoutKeyId;
    /** Rows whose chat (or the chat's jid) is not in the backup, so belong to no chat. Reported, not returned. */
    public final int withoutChat;

    private FullBackupMessages(List<WaMessage> messages, BackupCombiner.JidTables tables, int withoutKeyId, int withoutChat) {
        this.messages = messages;
        this.tables = tables;
        this.withoutKeyId = withoutKeyId;
        this.withoutChat = withoutChat;
    }

    /**
     * Checks the schema (names only) before any query, so a renamed column is
     * {@link BackupError#SCHEMA_CHANGED}, never an SQLite crash (Phase 2 plan § 2 item 3).
     *
     * @param sinceSeconds read messages from the start of this whole second on (timestamp ≥
     *                     sinceSeconds × 1000), so a second is never cut in half and
     *                     {@link BackupCombiner#combine} numbers each one whole (review finding 5)
     */
    public static FullBackupMessages read(File database, long sinceSeconds) throws BackupException {
        SQLiteDatabase db = SQLiteDatabase.openDatabase(database.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            BackupSchema.require(db);
            List<WaMessage> out = new ArrayList<>();
            int[] noKey = {0}, noChat = {0};
            try (Cursor c = db.rawQuery("SELECT m.key_id, m._id, m.from_me, m.timestamp, cj.raw_string, sj.raw_string, m.text_data, "
                    + "m.message_type "
                    + "FROM message m LEFT JOIN chat c ON c._id = m.chat_row_id LEFT JOIN jid cj ON cj._id = c.jid_row_id "
                    + "LEFT JOIN jid sj ON sj._id = m.sender_jid_row_id WHERE m.timestamp >= ?",
                    new String[]{String.valueOf(sinceSeconds * 1000L)})) {
                while (c.moveToNext()) {
                    WaMessage m = row(c.isNull(0) ? null : c.getString(0), c.getLong(1), c.getInt(2) == 1, c.getLong(3),
                            c.isNull(4) ? null : c.getString(4), c.isNull(5) ? null : c.getString(5),
                            c.isNull(6) ? null : c.getString(6), c.isNull(7) ? null : c.getInt(7), noKey, noChat);
                    if (m != null) out.add(m);
                }
            }
            BackupCombiner.JidTables t = new BackupCombiner.JidTables();
            try (Cursor c = db.rawQuery("SELECT _id, raw_string FROM jid WHERE raw_string IS NOT NULL", null)) {
                while (c.moveToNext()) t.putJid(c.getLong(0), c.getString(1));
            }
            try (Cursor c = db.rawQuery("SELECT lid_row_id, jid_row_id FROM jid_map", null)) {
                while (c.moveToNext()) t.putLink(c.getLong(0), c.getLong(1));
            }
            return new FullBackupMessages(out, t, noKey[0], noChat[0]);
        } finally {
            db.close();
        }
    }

    /**
     * One message row, mapped — plain Java, so the mapping is unit-tested without SQLite. Null (and
     * counted) for a row with no chat or no key_id. The sender is kept only on a group message not
     * from the user; a null type is unknown (-1). hasContent is null: a full backup does not say.
     */
    static WaMessage row(String keyId, long rowId, boolean fromMe, long timestampMs, String chat, String sender,
                         String text, Integer type, int[] withoutKeyId, int[] withoutChat) {
        if (chat == null) { withoutChat[0]++; return null; }
        if (keyId == null) { withoutKeyId[0]++; return null; }
        String s = !fromMe && chat.endsWith("@g.us") ? sender : null;
        return new WaMessage(chat, keyId, fromMe, timestampMs, s, text, rowId, type == null ? -1 : type, null);
    }
}
