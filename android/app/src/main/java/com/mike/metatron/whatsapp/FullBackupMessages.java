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
     * @param sinceSeconds read messages from the start of this whole second on (timestamp ≥
     *                     sinceSeconds × 1000), so a second is never cut in half and
     *                     {@link BackupCombiner#combine} numbers each one whole (review finding 5)
     */
    public static FullBackupMessages read(File database, long sinceSeconds) {
        SQLiteDatabase db = SQLiteDatabase.openDatabase(database.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            List<WaMessage> out = new ArrayList<>();
            int noKey = 0, noChat = 0;
            try (Cursor c = db.rawQuery("SELECT m.key_id, m._id, m.from_me, m.timestamp, cj.raw_string, sj.raw_string, m.text_data "
                    + "FROM message m LEFT JOIN chat c ON c._id = m.chat_row_id LEFT JOIN jid cj ON cj._id = c.jid_row_id "
                    + "LEFT JOIN jid sj ON sj._id = m.sender_jid_row_id WHERE m.timestamp >= ?",
                    new String[]{String.valueOf(sinceSeconds * 1000L)})) {
                while (c.moveToNext()) {
                    if (c.isNull(4)) { noChat++; continue; }
                    if (c.isNull(0)) { noKey++; continue; }
                    String chat = c.getString(4);
                    boolean fromMe = c.getInt(2) == 1;
                    String sender = !fromMe && chat.endsWith("@g.us") && !c.isNull(5) ? c.getString(5) : null;
                    out.add(new WaMessage(chat, c.getString(0), fromMe, c.getLong(3), sender,
                            c.isNull(6) ? null : c.getString(6), c.getLong(1)));
                }
            }
            BackupCombiner.JidTables t = new BackupCombiner.JidTables();
            try (Cursor c = db.rawQuery("SELECT _id, raw_string FROM jid WHERE raw_string IS NOT NULL", null)) {
                while (c.moveToNext()) t.putJid(c.getLong(0), c.getString(1));
            }
            try (Cursor c = db.rawQuery("SELECT lid_row_id, jid_row_id FROM jid_map", null)) {
                while (c.moveToNext()) t.putLink(c.getLong(0), c.getLong(1));
            }
            return new FullBackupMessages(out, t, noKey, noChat);
        } finally {
            db.close();
        }
    }
}
