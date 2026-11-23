package com.mike.metatron.whatsapp;

import android.content.ContentValues;
import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;

import java.io.File;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * "Check this phone's reader" (Phase 2 plan § 1, § 7 item 7): the on-device self-test that stands
 * in for Robolectric. It writes a synthetic database — every value made up, the schema exactly
 * {@link SchemaCheck#REQUIRED} — and runs the reader's SQL half against it on this phone's own
 * SQLite: {@link FullBackupMessages#read}, {@link ChatList#read}, the schema check on a second
 * database with one required column renamed, and {@link ReplyRule#isReply} over the rows read.
 * The fixture, the expected outcomes and the comparisons are {@link SelfTestChecks}, plain Java
 * and JVM-tested; this class is only the SQLite half.
 *
 * It works in its own folder, no_backup/wa_selftest/ — never wa_work/, which the nightly read
 * sweeps and owns. Both databases and their side files are deleted in {@code finally}, whatever
 * happened, and the deletion is itself a check. Blocking: call it off the main thread.
 *
 * The result is pass/fail counts and failed check names only — never a row value, never an
 * exception's message.
 */
final class SelfTest {
    static final String DIR = "wa_selftest";
    private static final String[] SIDE_FILES = {"", "-journal", "-wal", "-shm"};

    private SelfTest() {}

    static SelfTestChecks.Result run(Context ctx) {
        SelfTestChecks.Result r = new SelfTestChecks.Result();
        File dir = new File(ctx.getNoBackupFilesDir(), DIR);
        File planted = new File(dir, "planted.db"), renamed = new File(dir, "renamed.db");
        try {
            clear(dir); // a run killed half-way leaves its files behind; start from nothing
            dir.mkdirs();
            checks(planted, renamed, r);
        } finally {
            delete(planted);
            delete(renamed);
            clear(dir);
            dir.delete();
        }
        r.check(SelfTestChecks.CLEANUP, gone(planted) && gone(renamed) && !dir.exists());
        return r;
    }

    private static void checks(File planted, File renamed, SelfTestChecks.Result r) {
        // 1. The planted database, and that its schema is exactly what the reader requires.
        try {
            write(planted, SelfTestChecks.plantedSchema(), SelfTestChecks.plantedRows());
            r.check(SelfTestChecks.S_PLANTED, SelfTestChecks.plantedExact(schemaOf(planted)));
        } catch (RuntimeException e) {
            r.threw(SelfTestChecks.S_PLANTED, e);
        }

        // 2. FullBackupMessages.read, then the reply rule over the rows it returned.
        FullBackupMessages m = null;
        try {
            m = FullBackupMessages.read(planted, SelfTestChecks.SINCE_SECONDS);
            r.pass(SelfTestChecks.M_READ);
        } catch (Exception e) {
            r.threw(SelfTestChecks.M_READ, e);
        }
        if (m != null) {
            SelfTestChecks.messages(m.messages, m.withoutKeyId, m.withoutChat, m.tables, r);
            SelfTestChecks.replies(m.messages, r);
        } else {
            r.notRun(SelfTestChecks.MESSAGE_CHECKS);
            r.notRun(SelfTestChecks.REPLY_CHECKS);
        }

        // 3. ChatList.read — its SQL half is checked nowhere else.
        ChatList c = null;
        try {
            c = ChatList.read(planted);
            r.pass(SelfTestChecks.C_READ);
        } catch (Exception e) {
            r.threw(SelfTestChecks.C_READ, e);
        }
        if (c != null) SelfTestChecks.chats(c, r);
        else r.notRun(SelfTestChecks.CHAT_CHECKS);

        // 4. One required column renamed: both reads refuse by name, never with an SQLite exception.
        try {
            write(renamed, SelfTestChecks.renamedSchema(), new ArrayList<SelfTestChecks.Row>());
        } catch (RuntimeException e) {
            r.threw(SelfTestChecks.S_MESSAGES, e);
            r.threw(SelfTestChecks.S_CHATS, e);
            return;
        }
        refused(SelfTestChecks.S_MESSAGES, r, () -> FullBackupMessages.read(renamed, SelfTestChecks.SINCE_SECONDS));
        refused(SelfTestChecks.S_CHATS, r, () -> ChatList.read(renamed));
    }

    private interface Read {
        void run() throws Exception;
    }

    /** Passes only on a {@link BackupException} with {@link BackupError#SCHEMA_CHANGED}. */
    private static void refused(String name, SelfTestChecks.Result r, Read read) {
        try {
            read.run();
            r.check(name, false); // read a database the reader cannot use
        } catch (BackupException e) {
            if (e.error == BackupError.SCHEMA_CHANGED) r.pass(name);
            else r.threw(name, e);
        } catch (Exception e) {
            r.threw(name, e);
        }
    }

    // ---- SQLite --------------------------------------------------------------------------------

    /** Creates the database with this schema and rows. No android_metadata table: NO_LOCALIZED_COLLATORS. */
    private static void write(File f, Map<String, List<String>> schema, List<SelfTestChecks.Row> rows) {
        SQLiteDatabase db = SQLiteDatabase.openDatabase(f.getPath(), null,
                SQLiteDatabase.CREATE_IF_NECESSARY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            db.beginTransaction();
            try {
                for (String sql : SelfTestChecks.createStatements(schema)) db.execSQL(sql);
                for (SelfTestChecks.Row row : rows) db.insertOrThrow(row.table, null, values(row));
                db.setTransactionSuccessful();
            } finally {
                db.endTransaction();
            }
        } finally {
            db.close();
        }
    }

    private static ContentValues values(SelfTestChecks.Row row) {
        ContentValues cv = new ContentValues();
        for (Map.Entry<String, Object> e : row.values.entrySet()) {
            Object v = e.getValue();
            if (v == null) cv.putNull(e.getKey());
            else if (v instanceof Long) cv.put(e.getKey(), (Long) v);
            else cv.put(e.getKey(), (String) v);
        }
        return cv;
    }

    /** Every table in the database and its column names — names only. */
    private static Map<String, Set<String>> schemaOf(File f) {
        SQLiteDatabase db = SQLiteDatabase.openDatabase(f.getPath(), null,
                SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
        try {
            List<String> tables = new ArrayList<>();
            try (Cursor c = db.rawQuery("SELECT name FROM sqlite_master WHERE type = 'table'", null)) {
                while (c.moveToNext()) tables.add(c.getString(0));
            }
            return BackupSchema.read(db, tables);
        } finally {
            db.close();
        }
    }

    // ---- files ---------------------------------------------------------------------------------

    /** The database and its side files. SQLiteDatabase.deleteDatabase also takes any -mj journals. */
    private static void delete(File db) {
        try {
            SQLiteDatabase.deleteDatabase(db);
        } catch (RuntimeException ignored) {
            // the explicit deletes below still run; the cleanup check reports what is left
        }
        for (String s : SIDE_FILES) new File(db.getPath() + s).delete();
    }

    private static boolean gone(File db) {
        for (String s : SIDE_FILES) if (new File(db.getPath() + s).exists()) return false;
        return true;
    }

    /** Deletes everything inside the folder (it holds only this test's files). */
    private static void clear(File dir) {
        File[] kids = dir.listFiles();
        if (kids == null) return;
        for (File k : kids) {
            if (k.isDirectory()) clear(k);
            k.delete();
        }
    }
}
