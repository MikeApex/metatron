package com.mike.metatron.whatsapp;

import java.util.Collections;
import java.util.List;
import java.util.Map;

/**
 * One nightly increment, decoded (format description § 12). Platform-free; built only by
 * {@link IncrementReader}. Holds no decrypted bytes — only the decoded fields below.
 */
public final class Increment {
    /** The tables P1–P3 read from an increment; any other table's entries are ignored. */
    public static final List<String> TABLES = Collections.unmodifiableList(
            java.util.Arrays.asList("jid", "jid_map", "lid_display_name", "chat"));

    /** One table's changes: full rows to upsert by {@link #idField}, and ids to delete. */
    public static final class TableDelta {
        public final String table;
        /** The header's table_id_field — the column both the rows and the deleted ids are keyed by. */
        public final String idField;
        public final List<Map<String, Object>> modified;
        public final List<Long> deletedIds;
        /** Deleted-id files the header names that the ZIP does not hold — read as empty, counted here. */
        public final int absentDeletedFiles;

        TableDelta(String table, String idField, List<Map<String, Object>> modified, List<Long> deletedIds, int absentDeletedFiles) {
            this.table = table;
            this.idField = idField;
            this.modified = Collections.unmodifiableList(modified);
            this.deletedIds = Collections.unmodifiableList(deletedIds);
            this.absentDeletedFiles = absentDeletedFiles;
        }
    }

    /** N, from the file name. */
    public final long number;
    public final long creationDateMs;
    public final long messagesCountOnBackup, messagesUpdated, messagesDeleted;
    public final List<WaMessage> messages;
    /**
     * deletedMessages ids (message._id). Counted, never applied: every one observed was still in
     * the newest full backup (§ 12; Mike, 11-23).
     */
    public final List<Long> deletedMessageIds;
    /** By table name; a table with no changes that night is absent. */
    public final Map<String, TableDelta> tables;
    /** Text fields that were present but not valid UTF-8, so read as no text. Expected 0. */
    public final int textUndecodable;

    Increment(long number, long creationDateMs, long countOnBackup, long updated, long deleted,
              List<WaMessage> messages, List<Long> deletedMessageIds, Map<String, TableDelta> tables, int textUndecodable) {
        this.number = number;
        this.creationDateMs = creationDateMs;
        this.messagesCountOnBackup = countOnBackup;
        this.messagesUpdated = updated;
        this.messagesDeleted = deleted;
        this.messages = Collections.unmodifiableList(messages);
        this.deletedMessageIds = Collections.unmodifiableList(deletedMessageIds);
        this.tables = Collections.unmodifiableMap(tables);
        this.textUndecodable = textUndecodable;
    }
}
