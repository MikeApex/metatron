package com.mike.metatron.whatsapp;

import android.content.Context;
import android.database.Cursor;
import android.database.sqlite.SQLiteDatabase;
import android.os.Build;
import android.os.Environment;

import java.io.File;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.TimeZone;

/**
 * Phase 0 backup probe (plan P3, § 4 probes 2–3): find the newest complete backup, decrypt it
 * with the clean-room reader, and report counts, sizes, timings and schema NAMES — then the
 * two questions only the backup can answer about the live feed: does a notification's chat
 * ID map to a chat (P1), and does its message time match the backup's (the dedup key, P2).
 *
 * Every query returns a count, a length, a date or a schema name. No message text, no name
 * and no phone number is read into the report. The decrypted copy is deleted before
 * returning, whatever happens.
 */
final class ProbeBackup {
    private static final String[] PROBED_TABLES = {"message", "chat", "jid", "jid_map", "lid_display_name", "message_media"};
    /** Candidate names for message text — UNCONFIRMED (§ 9); used only for length(), only if present. */
    private static final String[] TEXT_COLUMN_CANDIDATES = {"text_data", "data"};

    private ProbeBackup() {}

    static String run(Context ctx) {
        StringBuilder b = new StringBuilder("== BACKUP PROBE ==\n");
        b.append("run at: ").append(ProbeReport.ts(System.currentTimeMillis())).append('\n');
        File out = new File(new File(ctx.getNoBackupFilesDir(), "wa_probe"), "msgstore.db");
        SQLiteDatabase db = null;
        try {
            if (Build.VERSION.SDK_INT >= 30 && !Environment.isExternalStorageManager()) {
                return b.append("All-files access: NOT GRANTED — step 2\n").toString();
            }
            File dir = new File(Environment.getExternalStorageDirectory(), BackupLocator.RELATIVE_DIR);
            b.append("All-files access: granted; WhatsApp Databases folder readable: ").append(dir.canRead()).append('\n');
            File[] files = dir.listFiles();
            if (files != null) {
                Arrays.sort(files, (x, y) -> Long.compare(y.lastModified(), x.lastModified()));
                for (File f : files) {
                    if (!f.getName().startsWith("msgstore")) continue;
                    b.append("  ").append(f.getName()).append("  ").append(mb(f.length()))
                            .append("  written ").append(ProbeReport.ts(f.lastModified())).append('\n');
                }
            }
            File f = BackupLocator.newest(dir);
            b.append("chosen: ").append(f.getName()).append('\n');
            BackupLocator.requireComplete(f, BackupLocator.SYSTEM_CLOCK, BackupLocator.THREAD_SLEEP);

            byte[] root = ProbeKeyVault.load(ctx);
            if (root == null) return b.append("no key stored — step 3\n").toString();
            BackupKey key;
            try {
                key = BackupKey.fromRoot(root);
            } finally {
                Arrays.fill(root, (byte) 0);
            }
            BackupDecryptor.Result r;
            try {
                r = BackupDecryptor.decrypt(f, key, out, BackupDecryptor.FILESYSTEM);
            } finally {
                key.destroy();
            }
            b.append("DECRYPT OK in ").append(String.format(Locale.US, "%.1f s", r.millis / 1000.0))
                    .append("  encrypted ").append(mb(r.encryptedBytes)).append(" -> decrypted ").append(mb(r.decryptedBytes))
                    .append(String.format(Locale.US, "  (ratio %.1fx)", (double) r.decryptedBytes / r.encryptedBytes)).append('\n');
            b.append("  payload ").append(r.compressed ? "zlib" : "uncompressed").append(", MD5 trailer ")
                    .append(r.md5Trailer ? "yes" : "no").append(", feature marker ").append(r.featureMarker ? "yes" : "no").append('\n');

            db = SQLiteDatabase.openDatabase(out.getPath(), null,
                    SQLiteDatabase.OPEN_READONLY | SQLiteDatabase.NO_LOCALIZED_COLLATORS);
            Map<String, Set<String>> cols = schema(db, b);
            SchemaCheck.require(cols);
            counts(db, b);
            Jids jids = new Jids(db, cols.get("jid"));
            live(ctx, db, jids, cols.get("message"), f.lastModified(), b);
        } catch (BackupException e) {
            b.append("REFUSED: ").append(e.error.code).append(" — ").append(e.error.userText).append('\n');
            if (e.error == BackupError.SCHEMA_CHANGED) b.append("  ").append(e.getMessage()).append('\n');
        } catch (Throwable t) {
            b.append("FAILED: ").append(t.getClass().getSimpleName()).append(": ").append(String.valueOf(t.getMessage())).append('\n');
        } finally {
            if (db != null) db.close();
            BackupDecryptor.deleteDecrypted(out);
            b.append("decrypted copy deleted: ").append(out.exists() ? "NO — STILL PRESENT" : "yes").append('\n');
        }
        return b.toString();
    }

    // ---- schema (names only) ------------------------------------------------------------

    private static Map<String, Set<String>> schema(SQLiteDatabase db, StringBuilder b) {
        b.append("\n-- schema (names only) --\n");
        b.append("tables: ").append(longOf(db, "SELECT COUNT(*) FROM sqlite_master WHERE type='table'")).append('\n');
        Map<String, Set<String>> cols = new LinkedHashMap<>();
        for (String t : PROBED_TABLES) {
            Set<String> c = new LinkedHashSet<>();
            try (Cursor cur = db.rawQuery("PRAGMA table_info(" + t + ")", null)) {
                while (cur.moveToNext()) c.add(cur.getString(1));
            }
            if (!c.isEmpty()) cols.put(t, c);
            b.append(t).append(c.isEmpty() ? ": TABLE MISSING" : " (" + c.size() + "): " + c).append('\n');
        }
        return cols;
    }

    // ---- counts against the 2026-10-26 Mac run ----------------------------------------

    private static void counts(SQLiteDatabase db, StringBuilder b) {
        b.append("\n-- counts (Mac 10-26 in brackets) --\n");
        b.append("messages: ").append(longOf(db, "SELECT COUNT(*) FROM message")).append("  [50,316]\n");
        b.append("chats: ").append(longOf(db, "SELECT COUNT(*) FROM chat")).append("  [4,603: 3,842 phone, 629 lid, 130 groups]\n");
        b.append("chats by jid server:\n");
        try (Cursor c = db.rawQuery("SELECT j.server, COUNT(*) FROM chat c JOIN jid j ON c.jid_row_id = j._id GROUP BY j.server ORDER BY 2 DESC", null)) {
            while (c.moveToNext()) b.append("  ").append(c.getString(0)).append(": ").append(c.getLong(1)).append('\n');
        }
        b.append("jid_map rows: ").append(longOf(db, "SELECT COUNT(*) FROM jid_map")).append('\n');
        long oldest = longOf(db, "SELECT MIN(timestamp) FROM message WHERE timestamp > 0");
        b.append("oldest message: ").append(day(oldest)).append("  [2017-10-23]\n");
        long since = System.currentTimeMillis() - 30L * 86_400_000L;
        b.append("last 30 days: ").append(longOf(db, "SELECT COUNT(*) FROM message WHERE timestamp > " + since))
                .append(" (sent ").append(longOf(db, "SELECT COUNT(*) FROM message WHERE from_me = 1 AND timestamp > " + since))
                .append(", received ").append(longOf(db, "SELECT COUNT(*) FROM message WHERE from_me = 0 AND timestamp > " + since))
                .append(")  [1,844: 675 sent, 1,168 received — as of 10-26]\n");

        b.append("messages per year:\n  ");
        List<String> months = new ArrayList<>();
        try (Cursor c = db.rawQuery("SELECT strftime('%Y', timestamp / 1000, 'unixepoch') y, COUNT(*) FROM message WHERE timestamp > 0 GROUP BY y ORDER BY y", null)) {
            while (c.moveToNext()) b.append(c.getString(0)).append(": ").append(c.getLong(1)).append("   ");
        }
        b.append('\n');
        try (Cursor c = db.rawQuery("SELECT DISTINCT strftime('%Y-%m', timestamp / 1000, 'unixepoch') FROM message WHERE timestamp > 0 ORDER BY 1", null)) {
            while (c.moveToNext()) months.add(c.getString(0));
        }
        b.append("months with no messages between the oldest and now (history gaps): ").append(gaps(months)).append('\n');
    }

    // ---- the live feed against the backup ---------------------------------------------

    private static void live(Context ctx, SQLiteDatabase db, Jids jids, Set<String> messageCols, long backupTime, StringBuilder b) {
        b.append("\n-- live notifications against this backup --\n");
        List<ProbeStore.Event> events = ProbeStore.load(ctx);
        if (events.isEmpty()) {
            b.append("no live notifications recorded yet\n");
            return;
        }
        if (jids.rawExpr == null) {
            b.append("CANNOT COMPARE: jid has neither raw_string nor user (columns listed above)\n");
            return;
        }
        b.append("jid identifier column used: ").append(jids.rawExpr).append('\n');

        // P1: which field carries the chat ID, and does it resolve to a chat?
        b.append("chat-ID candidates (distinct values -> found in jid -> resolves to a chat), by server of the jid row:\n");
        resolveField(jids, "shortcut", distinct(events, 0), b);
        resolveField(jids, "locus", distinct(events, 1), b);
        resolveField(jids, "tag", distinct(events, 2), b);

        // Group senders: does the person key resolve to a jid?
        Set<String> pks = new LinkedHashSet<>();
        for (ProbeStore.Event e : events) if (e.group) for (ProbeStore.Msg m : e.msgs) if (m.personKey != null) pks.add(m.personKey);
        resolveField(jids, "group person key", pks, b);

        // P2: the dedup key — canonical chat + message time.
        String textCol = null;
        for (String c : TEXT_COLUMN_CANDIDATES) if (messageCols.contains(c)) { textCol = c; break; }
        Map<String, ProbeStore.Msg> firstSeen = new HashMap<>(), lastSeen = new HashMap<>();
        Map<String, ProbeStore.Event> eventOf = new HashMap<>();
        for (ProbeStore.Event e : events) {
            String chat = e.chatId();
            if (chat == null) continue;
            for (ProbeStore.Msg m : e.msgs) {
                if (m.t <= 0 || m.t >= backupTime) continue; // not in this backup yet
                String k = chat + "|" + m.t;
                if (!firstSeen.containsKey(k)) firstSeen.put(k, m);
                lastSeen.put(k, m);
                eventOf.put(k, e);
            }
        }
        int considered = 0, unresolved = 0, exact = 0, dupTs = 0, w1s = 0, w60s = 0, w10m = 0, none = 0;
        int lenEqual = 0, backupLonger = 0, backupShorter = 0, editedLive = 0, editedBackupMatchesLast = 0;
        int senderChecked = 0, senderMatch = 0;
        for (Map.Entry<String, ProbeStore.Msg> en : lastSeen.entrySet()) {
            considered++;
            ProbeStore.Event e = eventOf.get(en.getKey());
            ProbeStore.Msg m = en.getValue();
            Long chatRow = jids.chatRowFor(e.chatId());
            if (chatRow == null) { unresolved++; continue; }
            String[] a = {String.valueOf(chatRow), String.valueOf(m.t)};
            long n = longOf(db, "SELECT COUNT(*) FROM message WHERE chat_row_id = ? AND from_me = 0 AND timestamp = ?", a);
            if (n >= 1) {
                exact++;
                if (n > 1) dupTs++;
                if (n == 1 && textCol != null && m.len >= 0) {
                    long bl = longOf(db, "SELECT IFNULL(length(" + textCol + "), -1) FROM message WHERE chat_row_id = ? AND from_me = 0 AND timestamp = ?", a);
                    if (bl == m.len) lenEqual++;
                    else if (bl > m.len) backupLonger++;
                    else backupShorter++;
                    ProbeStore.Msg first = firstSeen.get(en.getKey());
                    if (first.len != m.len) {
                        editedLive++;
                        if (bl == m.len) editedBackupMatchesLast++;
                    }
                }
                if (n == 1 && e.group && m.personKey != null) {
                    senderChecked++;
                    Long senderRow = longOrNull(db, "SELECT sender_jid_row_id FROM message WHERE chat_row_id = ? AND from_me = 0 AND timestamp = ?", a);
                    Long pkRow = jids.rowOf(m.personKey);
                    if (senderRow != null && pkRow != null && jids.canon(senderRow) == jids.canon(pkRow)) senderMatch++;
                }
                continue;
            }
            long d = longOf(db, "SELECT IFNULL(MIN(ABS(timestamp - ?)), -1) FROM message WHERE chat_row_id = ? AND from_me = 0 AND timestamp BETWEEN ? AND ?",
                    new String[]{String.valueOf(m.t), String.valueOf(chatRow), String.valueOf(m.t - 600_000), String.valueOf(m.t + 600_000)});
            if (d < 0) none++;
            else if (d <= 1000) w1s++;
            else if (d <= 60_000) w60s++;
            else w10m++;
        }
        b.append("dedup key (live messages timed before this backup was written): ").append(considered).append('\n');
        b.append("  chat not resolvable: ").append(unresolved).append('\n');
        b.append("  exact time match: ").append(exact).append("  (of which more than one backup row at that time: ").append(dupTs).append(")\n");
        b.append("  nearest within 1 s: ").append(w1s).append(", within 60 s: ").append(w60s)
                .append(", within 10 min: ").append(w10m).append(", none within 10 min: ").append(none).append('\n');
        b.append("  text length vs backup (").append(textCol == null ? "no text column found" : "column " + textCol)
                .append("): equal ").append(lenEqual).append(", backup longer (trimmed live) ").append(backupLonger)
                .append(", backup shorter ").append(backupShorter).append('\n');
        b.append("  re-posted live with a new length: ").append(editedLive).append(", backup equals the later length: ")
                .append(editedBackupMatchesLast).append('\n');
        b.append("  group sender: person key matches backup sender (canonical): ").append(senderMatch).append(" of ").append(senderChecked).append('\n');
    }

    private static void resolveField(Jids jids, String label, Set<String> values, StringBuilder b) {
        int found = 0, chat = 0, mapped = 0;
        Map<String, Integer> servers = new LinkedHashMap<>();
        for (String v : values) {
            Long row = jids.rowOf(v);
            if (row == null) continue;
            found++;
            String server = jids.server(row);
            ProbeReport.bump(servers, server == null ? "(null)" : server);
            if ("lid".equals(server) && jids.canon(row) != row) mapped++;
            if (jids.chatRowFor(v) != null) chat++;
        }
        b.append("  ").append(label).append(": ").append(values.size()).append(" -> ").append(found).append(" -> ").append(chat)
                .append("   servers ").append(servers).append(mapped > 0 ? "   lid mapped to a number: " + mapped : "").append('\n');
    }

    /** field: 0 shortcut, 1 locus, 2 tag. */
    private static Set<String> distinct(List<ProbeStore.Event> events, int field) {
        Set<String> s = new LinkedHashSet<>();
        for (ProbeStore.Event e : events) {
            String v = field == 0 ? e.shortcut : field == 1 ? e.locus : e.tag;
            if (v != null && !v.isEmpty()) s.add(v);
        }
        return s;
    }

    /** WhatsApp IDs, canonicalised through jid_map exactly as plan P1 specifies. */
    private static final class Jids {
        final SQLiteDatabase db;
        final String rawExpr;

        Jids(SQLiteDatabase db, Set<String> jidCols) {
            this.db = db;
            if (jidCols != null && jidCols.contains("raw_string")) rawExpr = "raw_string";
            else if (jidCols != null && jidCols.contains("user")) rawExpr = "user || '@' || server";
            else rawExpr = null;
        }

        Long rowOf(String id) {
            return longOrNull(db, "SELECT _id FROM jid WHERE " + rawExpr + " = ? LIMIT 1", new String[]{id});
        }

        String server(long row) {
            try (Cursor c = db.rawQuery("SELECT server FROM jid WHERE _id = ?", new String[]{String.valueOf(row)})) {
                return c.moveToFirst() ? c.getString(0) : null;
            }
        }

        /** A hidden ID linked by jid_map becomes the number's row; anything else stays itself. */
        long canon(long row) {
            if (!"lid".equals(server(row))) return row;
            Long mapped = longOrNull(db, "SELECT jid_row_id FROM jid_map WHERE lid_row_id = ?", new String[]{String.valueOf(row)});
            return mapped == null ? row : mapped;
        }

        /** The chat whose canonical ID equals this ID's canonical form — the share-list key match. */
        Long chatRowFor(String id) {
            Long row = rowOf(id);
            if (row == null) return null;
            long canonical = canon(row);
            try (Cursor c = db.rawQuery("SELECT _id, jid_row_id FROM chat WHERE jid_row_id IN (?, ?)",
                    new String[]{String.valueOf(row), String.valueOf(canonical)})) {
                while (c.moveToNext()) {
                    if (canon(c.getLong(1)) == canonical) return c.getLong(0);
                }
            }
            // A chat keyed by a hidden ID that maps to this number.
            try (Cursor c = db.rawQuery("SELECT c._id FROM chat c JOIN jid_map m ON c.jid_row_id = m.lid_row_id WHERE m.jid_row_id = ? LIMIT 1",
                    new String[]{String.valueOf(canonical)})) {
                return c.moveToFirst() ? c.getLong(0) : null;
            }
        }
    }

    // ---- helpers ----------------------------------------------------------------------

    private static long longOf(SQLiteDatabase db, String sql) {
        return longOf(db, sql, null);
    }

    private static long longOf(SQLiteDatabase db, String sql, String[] args) {
        Long v = longOrNull(db, sql, args);
        return v == null ? -1 : v;
    }

    private static Long longOrNull(SQLiteDatabase db, String sql, String[] args) {
        try (Cursor c = db.rawQuery(sql, args)) {
            return c.moveToFirst() && !c.isNull(0) ? c.getLong(0) : null;
        }
    }

    private static String gaps(List<String> present) {
        if (present.isEmpty()) return "-";
        Set<String> have = new LinkedHashSet<>(present);
        List<String> missing = new ArrayList<>();
        int y = Integer.parseInt(present.get(0).substring(0, 4)), mo = Integer.parseInt(present.get(0).substring(5, 7));
        String now = new SimpleDateFormat("yyyy-MM", Locale.US).format(new Date());
        while (true) {
            String k = String.format(Locale.US, "%04d-%02d", y, mo);
            if (k.compareTo(now) > 0) break;
            if (!have.contains(k)) missing.add(k);
            if (++mo == 13) { mo = 1; y++; }
        }
        return missing.isEmpty() ? "none" : missing.size() + " " + missing;
    }

    private static String day(long ms) {
        if (ms <= 0) return "-";
        SimpleDateFormat f = new SimpleDateFormat("yyyy-MM-dd", Locale.US);
        f.setTimeZone(TimeZone.getDefault());
        return f.format(new Date(ms));
    }

    private static String mb(long bytes) {
        return String.format(Locale.US, "%.1f MB", bytes / 1e6);
    }
}
