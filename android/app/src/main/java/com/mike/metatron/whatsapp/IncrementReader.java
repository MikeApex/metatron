package com.mike.metatron.whatsapp;

import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;
import java.nio.charset.CharacterCodingException;
import java.nio.charset.CodingErrorAction;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipInputStream;

/**
 * Reads one nightly increment — msgstore-increment-N.db.crypt15 — into an {@link Increment}
 * (format description § 12). A separate entry point from {@link BackupDecryptor}, whose
 * accept and refuse behaviour is unchanged: it still refuses this payload as
 * not_a_message_database.
 *
 * Written clean-room from the probe's counts on Mike's phone — no reference implementation and no
 * published schema (plan W9, clean-room rule 5). An increment is ~0.1 MB, so it is read in memory
 * under hard caps: the container is checked as §§ 3–5 describe (tag, MD5 trailer), the zlib payload
 * is inflated, and the ZIP inside is read entry by entry. messages.bin is decoded through the adopted
 * field map only; every other field is ignored. Every decrypted buffer is zeroed before returning,
 * and nothing is logged. A refusal names what is wrong in code-written words, never content.
 */
public final class IncrementReader {
    /** Observed ≤ 0.15 MB encrypted (§ 12). */
    public static final long MAX_ENCRYPTED_BYTES = 4L * 1024 * 1024;
    /** Inflated payload, and separately the sum of the ZIP entries. */
    public static final long MAX_INFLATED_BYTES = 32L * 1024 * 1024;

    static final String FORMAT_VERSION = "1.0";
    static final String MESSAGES_FORMAT = "protobuf";

    /** The text of a message: the first of these present, relative to the content block (1.2). */
    static final int[][] TEXT_PATHS = {{1}, {6, 1}, {3, 3}, {12, 14, 1}, {12, 14, 6, 1}, {75, 3}};

    private static final byte[] ZIP_MAGIC = {'P', 'K', 3, 4};

    private IncrementReader() {}

    /**
     * @param file   an increment file; the caller has already checked it is not being written
     * @param number N, from its name
     */
    public static Increment read(File file, long number, BackupKey key) throws BackupException, IOException {
        long len = file.length();
        if (len > MAX_ENCRYPTED_BYTES) throw new BackupException(BackupError.INCREMENT_TOO_LARGE, len + " bytes encrypted");
        byte[] raw = readAll(file, (int) len);
        byte[] plain = null, inflated = null;
        Map<String, byte[]> entries = null;
        try {
            plain = container(raw, key);
            inflated = inflate(plain);
            entries = unzip(inflated);
            return decode(entries, number);
        } catch (TooLarge e) {
            throw new BackupException(BackupError.INCREMENT_TOO_LARGE, "inflated over " + MAX_INFLATED_BYTES + " bytes");
        } finally {
            Arrays.fill(raw, (byte) 0);
            if (plain != null) Arrays.fill(plain, (byte) 0);
            if (inflated != null) Arrays.fill(inflated, (byte) 0);
            if (entries != null) for (byte[] e : entries.values()) Arrays.fill(e, (byte) 0);
        }
    }

    // ---- container (§§ 3–5) ----------------------------------------------------------------

    /** The verified plaintext. Wrong key, damage and the payload's kind are told apart as § 6.2 says. */
    static byte[] container(byte[] f, BackupKey key) throws BackupException {
        BackupHeader header = BackupHeader.parse(f, Math.min(f.length, BackupHeader.MAX_PREFIX));
        int start = header.dataStart;
        if (f.length - start < 16 + 1) throw new BackupException(BackupError.TRUNCATED);
        boolean md5Trailer = false;
        if (f.length - start >= 32 + 1) {
            try {
                MessageDigest md5 = MessageDigest.getInstance("MD5");
                md5.update(f, 0, f.length - 16);
                md5Trailer = MessageDigest.isEqual(md5.digest(), Arrays.copyOfRange(f, f.length - 16, f.length));
            } catch (GeneralSecurityException e) {
                throw new IllegalStateException("platform crypto unavailable", e);
            }
        }
        int tagStart = f.length - (md5Trailer ? 32 : 16);
        byte[] plain = new byte[tagStart - start];
        Gcm gcm = null;
        try {
            gcm = new Gcm(key.aesKey(), header.iv);
            gcm.update(f, start, plain.length, plain, 0);
            boolean tagOk = MessageDigest.isEqual(gcm.tag(), Arrays.copyOfRange(f, tagStart, tagStart + 16));
            boolean zlib = plain.length >= 2 && isZlibHeader(plain[0] & 0xff, plain[1] & 0xff);
            boolean known = zlib || startsWith(plain, ZIP_MAGIC) || startsWith(plain, BackupDecryptor.SQLITE_HEADER);
            if (!known) throw new BackupException(BackupError.WRONG_KEY);
            if (!tagOk) throw new BackupException(BackupError.INTEGRITY);
            if (!zlib) throw new BackupException(BackupError.INCREMENT_FORMAT_UNKNOWN, "payload is not zlib");
            byte[] out = plain;
            plain = null;
            return out;
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("platform crypto unavailable", e);
        } finally {
            if (gcm != null) gcm.wipe();
            if (plain != null) Arrays.fill(plain, (byte) 0);
        }
    }

    private static byte[] inflate(byte[] plain) throws BackupException {
        Inflater inf = new Inflater();
        Capped out = new Capped();
        byte[] buf = new byte[64 * 1024];
        try {
            inf.setInput(plain);
            while (!inf.finished()) {
                int n = inf.inflate(buf);
                if (n > 0) {
                    out.write(buf, 0, n);
                } else if (inf.needsDictionary()) {
                    throw new BackupException(BackupError.INTEGRITY);
                } else if (inf.needsInput()) {
                    throw new BackupException(BackupError.TRUNCATED);
                }
            }
            if (inf.getRemaining() > 0) throw new BackupException(BackupError.INTEGRITY, inf.getRemaining() + " bytes after the zlib stream");
            byte[] r = out.take();
            if (!startsWith(r, ZIP_MAGIC)) {
                Arrays.fill(r, (byte) 0);
                throw new BackupException(BackupError.INCREMENT_FORMAT_UNKNOWN, "inflated payload is not a ZIP");
            }
            return r;
        } catch (DataFormatException e) {
            throw new BackupException(BackupError.INTEGRITY);
        } finally {
            inf.end();
            out.wipe();
            Arrays.fill(buf, (byte) 0);
        }
    }

    /** Entry name → bytes. A ZIP the platform cannot read, or a repeated name, is malformed. */
    private static Map<String, byte[]> unzip(byte[] zip) throws BackupException {
        Map<String, byte[]> out = new LinkedHashMap<>();
        long total = 0;
        byte[] buf = new byte[64 * 1024];
        try (ZipInputStream z = new ZipInputStream(new ByteArrayInputStream(zip))) {
            ZipEntry e;
            while ((e = z.getNextEntry()) != null) {
                if (e.isDirectory()) continue;
                Capped c = new Capped();
                c.limit = MAX_INFLATED_BYTES - total;
                int n;
                while ((n = z.read(buf)) > 0) c.write(buf, 0, n);
                byte[] b = c.take();
                total += b.length;
                if (out.put(e.getName(), b) != null) throw new BackupException(BackupError.INCREMENT_MALFORMED, "a ZIP entry name repeats");
            }
        } catch (IOException e) {
            for (byte[] b : out.values()) Arrays.fill(b, (byte) 0);
            throw new BackupException(BackupError.INCREMENT_MALFORMED, "the ZIP does not read");
        } catch (BackupException e) {
            for (byte[] b : out.values()) Arrays.fill(b, (byte) 0);
            throw e;
        } finally {
            Arrays.fill(buf, (byte) 0);
        }
        if (out.isEmpty()) throw new BackupException(BackupError.INCREMENT_MALFORMED, "the ZIP has no entries");
        return out;
    }

    // ---- the ZIP's contents (§ 12) --------------------------------------------------------

    static Increment decode(Map<String, byte[]> entries, long number) throws BackupException {
        Map<String, Object> h = object(json(entries, "header.json"), "header.json");
        Map<String, Object> hdr = object(need(h, "header", "header.json"), "header");
        Object version = need(hdr, "format_version", "header");
        if (!FORMAT_VERSION.equals(version)) throw new BackupException(BackupError.INCREMENT_FORMAT_UNKNOWN, "header.format_version");
        long created = integer(need(hdr, "creation_date", "header"), "header.creation_date");
        Map<String, Object> added = object(need(h, "added_messages", "header.json"), "added_messages");
        if (!MESSAGES_FORMAT.equals(need(added, "format", "added_messages"))) {
            throw new BackupException(BackupError.INCREMENT_FORMAT_UNKNOWN, "added_messages.format");
        }
        String messagesFile = string(need(added, "filename", "added_messages"), "added_messages.filename");
        long onBackup = integer(need(added, "messages_count_on_backup", "added_messages"), "added_messages.messages_count_on_backup");
        long updated = integer(need(added, "messages_updated", "added_messages"), "added_messages.messages_updated");
        long deleted = integer(need(added, "messages_deleted", "added_messages"), "added_messages.messages_deleted");

        byte[] bin = entries.get(messagesFile);
        if (bin == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "the messages file the header names");
        int[] undecodable = {0};
        List<WaMessage> messages = messages(bin, undecodable);

        List<Long> deletedIds = new ArrayList<>();
        Object dm = h.get("deleted_messages");
        // Observed on the phone 11-23: a night with no deletions still has deleted_messages, without
        // its file list. So the list is required exactly when the header counts a deletion.
        Object files = dm == null ? null : object(dm, "deleted_messages").get("deleted_message_ids_files");
        if (files == null && deleted > 0) {
            throw new BackupException(BackupError.INCREMENT_MISSING_PART, "deleted_messages.deleted_message_ids_files");
        }
        if (files != null) {
            for (Object f : list(files, "deleted_messages.deleted_message_ids_files")) {
                deletedIds.addAll(deletedIds(entries, string(f, "a deleted-ids file name")));
            }
        }

        Map<String, Increment.TableDelta> tables = new LinkedHashMap<>();
        Object ent = h.get("entities");
        if (ent != null) {
            for (Object group : object(ent, "entities").values()) {
                for (Object t : list(group, "an entities group")) {
                    Map<String, Object> td = object(t, "an entities entry");
                    String name = string(need(td, "table_name", "an entities entry"), "table_name");
                    if (!Increment.TABLES.contains(name)) continue;
                    if (tables.containsKey(name)) throw new BackupException(BackupError.INCREMENT_MALFORMED, "table " + name + " listed twice");
                    tables.put(name, table(entries, name, td));
                }
            }
        }
        return new Increment(number, created, onBackup, updated, deleted, messages, deletedIds, tables, undecodable[0]);
    }

    private static Increment.TableDelta table(Map<String, byte[]> entries, String name, Map<String, Object> td) throws BackupException {
        String idField = string(need(td, "table_id_field", "the entities entry for " + name), "table_id_field");
        List<Map<String, Object>> rows = new ArrayList<>();
        Object mf = td.get("modified_entity_files");
        if (mf != null) {
            for (Object f : list(mf, "modified_entity_files")) {
                String file = string(f, "a modified-entity file name");
                Map<String, Object> o = object(json(entries, file), file);
                for (Object r : list(need(o, name, file), file + "." + name)) {
                    Map<String, Object> row = object(r, "a row of " + name);
                    need(row, idField, "a row of " + name);
                    rows.add(row);
                }
            }
        }
        List<Long> del = new ArrayList<>();
        int absent = 0;
        Object df = td.get("deleted_id_files");
        if (df != null) {
            for (Object f : list(df, "deleted_id_files")) {
                String file = string(f, "a deleted-ids file name");
                // Observed 11-23: a header naming chat_deleted_1.json that its ZIP does not hold. A
                // deletion list that is absent is read as empty and counted, never silently.
                if (!entries.containsKey(file)) { absent++; continue; }
                del.addAll(deletedIds(entries, file));
            }
        }
        return new Increment.TableDelta(name, idField, rows, del, absent);
    }

    private static List<Long> deletedIds(Map<String, byte[]> entries, String file) throws BackupException {
        Map<String, Object> o = object(json(entries, file), file);
        List<Long> out = new ArrayList<>();
        for (Object v : list(need(o, "deleted_ids", file), file + ".deleted_ids")) out.add(integer(v, file + ".deleted_ids[]"));
        return out;
    }

    // ---- messages.bin — the adopted field map (§ 12) --------------------------------------

    /**
     * Varint-length-prefixed records; in each, field 2 is a chat block {1 jid, 2 messages}; a message
     * is {1 info, 2 row id}; info is {1 key {1 jid, 2 from-me, 3 key_id}, 2 content, 3 time in
     * seconds, 5 group sender}. Every other field is skipped by its wire type.
     */
    static List<WaMessage> messages(byte[] d, int[] undecodable) throws BackupException {
        List<WaMessage> out = new ArrayList<>();
        int pos = 0;
        if (d.length == 0) throw new BackupException(BackupError.INCREMENT_MALFORMED, "the messages file is empty");
        while (pos < d.length) {
            long[] len = varint(d, pos, d.length);
            if (len == null || len[0] <= 0 || len[0] > d.length - len[1]) {
                throw new BackupException(BackupError.INCREMENT_MALFORMED, "a record length");
            }
            int s = (int) len[1], e = (int) (len[1] + len[0]);
            for (Field f : fields(d, s, e, "a record")) {
                if (f.number == 2) {
                    if (f.wire != 2) throw new BackupException(BackupError.INCREMENT_MALFORMED, "a chat block's wire type");
                    chat(d, f.start, f.end, out, undecodable);
                }
            }
            pos = e;
        }
        return out;
    }

    private static void chat(byte[] d, int s, int e, List<WaMessage> out, int[] undecodable) throws BackupException {
        String jid = null;
        List<Field> msgs = new ArrayList<>();
        for (Field f : fields(d, s, e, "a chat block")) {
            if (f.number == 1 && f.wire == 2 && jid == null) jid = text(d, f, "a chat jid");
            else if (f.number == 2 && f.wire == 2) msgs.add(f);
        }
        if (msgs.isEmpty()) return;
        if (jid == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a chat block's jid (record.2.1)");
        for (Field m : msgs) out.add(message(d, m, jid, undecodable));
    }

    private static WaMessage message(byte[] d, Field m, String chatJid, int[] undecodable) throws BackupException {
        Field info = null;
        Long rowId = null;
        for (Field f : fields(d, m.start, m.end, "a message")) {
            if (f.number == 1 && f.wire == 2 && info == null) info = f;
            else if (f.number == 2 && f.wire == 0 && rowId == null) rowId = f.value;
        }
        if (info == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a message's info (1)");
        if (rowId == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a message's row id (2)");
        Field key = null, content = null;
        Long seconds = null;
        String sender = null;
        for (Field f : fields(d, info.start, info.end, "a message's info")) {
            if (f.number == 1 && f.wire == 2 && key == null) key = f;
            else if (f.number == 2 && f.wire == 2 && content == null) content = f;
            else if (f.number == 3 && f.wire == 0 && seconds == null) seconds = f.value;
            else if (f.number == 5 && f.wire == 2 && sender == null) sender = text(d, f, "a sender jid");
        }
        if (key == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a message's key (1.1)");
        if (seconds == null || seconds <= 0) throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a message's time (1.3)");
        String keyJid = null, keyId = null;
        Long flag = null;
        for (Field f : fields(d, key.start, key.end, "a message key")) {
            if (f.number == 1 && f.wire == 2 && keyJid == null) keyJid = text(d, f, "a key jid");
            else if (f.number == 2 && f.wire == 0 && flag == null) flag = f.value;
            else if (f.number == 3 && f.wire == 2 && keyId == null) keyId = text(d, f, "a key_id");
        }
        if (keyJid == null || flag == null || keyId == null) {
            throw new BackupException(BackupError.INCREMENT_MISSING_PART, "a message key's jid, from-me flag or key_id (1.1.1-3)");
        }
        if (flag != 0 && flag != 1) throw new BackupException(BackupError.INCREMENT_MALFORMED, "a from-me flag that is not 0 or 1");
        // 612 of 612 observed: the key names its chat block's chat. A message that names another chat
        // could be filed under the wrong chat, past the allowlist, so it is refused rather than guessed.
        if (!keyJid.equals(chatJid)) throw new BackupException(BackupError.INCREMENT_MALFORMED, "a message key's jid differs from its chat block");
        boolean fromMe = flag == 1;
        String text = content == null ? null : text(d, content.start, content.end, undecodable);
        String groupSender = !fromMe && chatJid.endsWith("@g.us") ? sender : null;
        return new WaMessage(chatJid, keyId, fromMe, seconds * 1000L, groupSender, text, rowId);
    }

    /** The first TEXT_PATHS entry present in the content block; null when none. Lenient below 1.2. */
    private static String text(byte[] d, int s, int e, int[] undecodable) {
        for (int[] path : TEXT_PATHS) {
            int[] at = find(d, s, e, path, 0);
            if (at == null) continue;
            String t = utf8(d, at[0], at[1]);
            if (t != null) return t;
            undecodable[0]++;
        }
        return null;
    }

    /** [start, end) of the first length-delimited field at this path, or null; a hop that is not a message is absent. */
    private static int[] find(byte[] d, int s, int e, int[] path, int depth) {
        List<Field> fs;
        try {
            fs = fields(d, s, e, "");
        } catch (BackupException ex) {
            return null;
        }
        for (Field f : fs) {
            if (f.number != path[depth] || f.wire != 2) continue;
            if (depth == path.length - 1) return new int[]{f.start, f.end};
            int[] r = find(d, f.start, f.end, path, depth + 1);
            if (r != null) return r;
        }
        return null;
    }

    // ---- wire format (generic protobuf encoding: varints, wire types 0/1/2/5) ----------------

    static final class Field {
        int number, wire, start, end;
        long value;
    }

    /** The fields of [s, e), strictly: every byte must belong to a well-formed field. */
    static List<Field> fields(byte[] d, int s, int e, String what) throws BackupException {
        List<Field> out = new ArrayList<>();
        int pos = s;
        while (pos < e) {
            long[] t = varint(d, pos, e);
            if (t == null) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
            Field f = new Field();
            long number = t[0] >>> 3;
            f.wire = (int) (t[0] & 7);
            if (number < 1 || number > 536_870_911L) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
            f.number = (int) number;
            pos = (int) t[1];
            switch (f.wire) {
                case 0: {
                    long[] v = varint(d, pos, e);
                    if (v == null) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
                    f.value = v[0];
                    pos = (int) v[1];
                    break;
                }
                case 1: pos += 8; break;
                case 5: pos += 4; break;
                case 2: {
                    long[] l = varint(d, pos, e);
                    if (l == null || l[0] < 0 || l[0] > e - l[1]) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
                    f.start = (int) l[1];
                    f.end = (int) (l[1] + l[0]);
                    pos = f.end;
                    break;
                }
                default:
                    throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
            }
            if (pos > e) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
            out.add(f);
        }
        return out;
    }

    /** {value, next position}, or null when malformed or past end. */
    static long[] varint(byte[] d, int pos, int end) {
        long v = 0;
        for (int shift = 0; shift < 64; shift += 7) {
            if (pos >= end) return null;
            int x = d[pos++] & 0xff;
            v |= (long) (x & 0x7f) << shift;
            if ((x & 0x80) == 0) return new long[]{v, pos};
        }
        return null;
    }

    private static String text(byte[] d, Field f, String what) throws BackupException {
        String t = utf8(d, f.start, f.end);
        if (t == null || t.isEmpty()) throw new BackupException(BackupError.INCREMENT_MALFORMED, what);
        return t;
    }

    private static String utf8(byte[] d, int s, int e) {
        try {
            return StandardCharsets.UTF_8.newDecoder()
                    .onMalformedInput(CodingErrorAction.REPORT).onUnmappableCharacter(CodingErrorAction.REPORT)
                    .decode(ByteBuffer.wrap(d, s, e - s)).toString();
        } catch (CharacterCodingException ex) {
            return null;
        }
    }

    // ---- JSON helpers: a missing key is a missing part; a wrong type is malformed -------------

    private static Object json(Map<String, byte[]> entries, String name) throws BackupException {
        byte[] b = entries.get(name);
        if (b == null) throw new BackupException(BackupError.INCREMENT_MISSING_PART, name);
        try {
            return Json.parse(new String(b, StandardCharsets.UTF_8));
        } catch (Json.Malformed e) {
            throw new BackupException(BackupError.INCREMENT_MALFORMED, name + ": " + e.getMessage());
        }
    }

    private static Object need(Map<String, Object> o, String key, String where) throws BackupException {
        if (!o.containsKey(key)) throw new BackupException(BackupError.INCREMENT_MISSING_PART, where + "." + key);
        return o.get(key);
    }

    @SuppressWarnings("unchecked")
    private static Map<String, Object> object(Object v, String what) throws BackupException {
        if (!(v instanceof Map)) throw new BackupException(BackupError.INCREMENT_MALFORMED, what + " is not an object");
        return (Map<String, Object>) v;
    }

    @SuppressWarnings("unchecked")
    private static List<Object> list(Object v, String what) throws BackupException {
        if (!(v instanceof List)) throw new BackupException(BackupError.INCREMENT_MALFORMED, what + " is not a list");
        return (List<Object>) v;
    }

    private static String string(Object v, String what) throws BackupException {
        if (!(v instanceof String)) throw new BackupException(BackupError.INCREMENT_MALFORMED, what + " is not text");
        return (String) v;
    }

    private static long integer(Object v, String what) throws BackupException {
        if (!(v instanceof Long)) throw new BackupException(BackupError.INCREMENT_MALFORMED, what + " is not an integer");
        return (Long) v;
    }

    // ---- small helpers -------------------------------------------------------------------

    private static byte[] readAll(File f, int len) throws IOException, BackupException {
        byte[] b = new byte[len];
        int n = 0, r;
        try (InputStream in = new FileInputStream(f)) {
            while (n < len && (r = in.read(b, n, len - n)) > 0) n += r;
            if (n != len || in.read() != -1) throw new BackupException(BackupError.BEING_WRITTEN);
        }
        return b;
    }

    private static boolean isZlibHeader(int cmf, int flg) {
        return cmf == 0x78 && (flg & 0x20) == 0 && ((cmf << 8) | flg) % 31 == 0;
    }

    private static boolean startsWith(byte[] b, byte[] magic) {
        if (b.length < magic.length) return false;
        for (int i = 0; i < magic.length; i++) if (b[i] != magic[i]) return false;
        return true;
    }

    /** A growable buffer that refuses past its limit and can be zeroed. */
    private static final class Capped extends ByteArrayOutputStream {
        long limit = MAX_INFLATED_BYTES;

        @Override
        public synchronized void write(byte[] b, int off, int len) {
            if (count + (long) len > limit) {
                wipe();
                throw new TooLarge();
            }
            super.write(b, off, len);
        }

        byte[] take() {
            byte[] r = toByteArray();
            wipe();
            return r;
        }

        void wipe() {
            Arrays.fill(buf, (byte) 0);
            count = 0;
        }
    }

    /** Unchecked so it can leave ByteArrayOutputStream.write; converted at the entry point. */
    private static final class TooLarge extends RuntimeException {}
}
