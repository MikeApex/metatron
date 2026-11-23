package com.mike.metatron.whatsapp;

import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.Map;
import java.util.Set;

/**
 * Reads a decrypted database's schema — table and column NAMES only, never a row — and hands it to
 * the platform-free {@link SchemaCheck} (format description § 6.7). Android-only (SQLite). Moved
 * from the probe's ProbeBackup so every read in main checks the schema before its first query, and
 * a renamed column is {@code schema_changed}, never an SQLite crash.
 */
final class BackupSchema {
    private BackupSchema() {}

    /** Refuses with {@link BackupError#SCHEMA_CHANGED} unless every name {@link SchemaCheck#REQUIRED} lists is present. */
    static void require(SQLiteDatabase db) throws BackupException {
        SchemaCheck.require(read(db, SchemaCheck.REQUIRED.keySet()));
    }

    /** Table name → its column names, for each of these tables that exists; a missing table is absent. */
    static Map<String, Set<String>> read(SQLiteDatabase db, Iterable<String> tables) {
        Map<String, Set<String>> out = new LinkedHashMap<>();
        for (String t : tables) {
            Set<String> c = columns(db, t);
            if (!c.isEmpty()) out.put(t, c);
        }
        return out;
    }

    /** One table's column names; empty when the table does not exist. */
    static Set<String> columns(SQLiteDatabase db, String table) {
        Set<String> c = new LinkedHashSet<>();
        try (Cursor cur = db.rawQuery("PRAGMA table_info(\"" + table.replace("\"", "\"\"") + "\")", null)) {
            while (cur.moveToNext()) c.add(cur.getString(1));
        }
        return c;
    }
}
