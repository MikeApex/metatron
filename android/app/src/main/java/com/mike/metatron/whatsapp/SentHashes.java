package com.mike.metatron.whatsapp;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.security.GeneralSecurityException;
import java.security.SecureRandom;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Collections;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * The sent-hash list (build plan § 3.4): per message key, what was sent — <b>never the text, never
 * the sender</b>, only keyed hashes of them under a per-install random salt, and the message's
 * whole second. It is what lets the nightly job send an unchanged message never again, a changed
 * one as an {@code update}, and what "This should have come up" looks a shared text up in (§ 3.11).
 *
 * <p><b>Files</b> in the state folder: {@code salt.bin} (32 bytes from {@link SecureRandom}) and
 * {@code sent.json} ({@code {"v":1,"keys":{key:[textHashHex, senderHashHex, second]}}}). Both are
 * written atomically — a temporary file, synced, renamed over the old one — before the mutating
 * call returns; a failed write leaves memory as it was and throws {@link UncheckedIOException}.
 *
 * <p><b>Keys.</b> A received message: {@code chat|second|ordinal}, the VM's {@code native_key}. A reply
 * marker: {@code r|chat|second|ordinal} — so a from-me row never collides with a received one.
 *
 * <p><b>One instance per state folder per process</b> ({@link #open}); every method is synchronized,
 * because the nightly job and the live listener both write it.
 *
 * <p><b>Recovery on open</b> — never a crash, never a half-read list:
 * <ul>
 * <li>{@code sent.json} unreadable in any way (bad JSON, wrong shape, a bad hash length) → start
 *     empty and write the empty list over it. The next night re-sends the overlap once: unchanged
 *     messages are duplicates the VM drops (the cost of a reinstall, § 8 Unseen 2).</li>
 * <li>{@code salt.bin} missing or not 32 bytes → the stored hashes can no longer be compared with
 *     anything, so {@code sent.json} is deleted first, then a new salt and an empty list are
 *     written. A crash between the steps leaves either nothing (fresh start) or a salt without a
 *     list (empty) — never old hashes under a new salt.</li>
 * <li>{@code sent.json} missing with a good salt → empty.</li>
 * </ul>
 *
 * <p><b>"Turn off"</b> is {@link #deleteAll}: both files removed and the instance forgotten; that
 * instance then refuses every write and hash and reads as empty, so a listener racing the turn-off
 * cannot bring the files back. {@link #open} afterwards starts afresh with a new salt.
 */
public final class SentHashes {
    /** The overlap (8 days, decision 2) plus one: keys older than this before the newest cursor go. */
    public static final long KEEP_SECONDS = 9L * 24 * 3600;
    public static final int TEXT_HASH_BYTES = 16;
    public static final int SENDER_HASH_BYTES = 8;
    static final int SALT_BYTES = 32;
    static final String SENT_FILE = "sent.json";
    static final String SALT_FILE = "salt.bin";

    /** What {@link #open} found on disk — for tests and the screen's diagnostics; never content. */
    enum Opened { LOADED, FRESH, UNREADABLE_RESET, SALT_LOST_RESET }

    private static final Map<String, SentHashes> INSTANCES = new HashMap<>();
    private static final byte[] NO_SENDER = new byte[0];

    public static final class Entry {
        public final byte[] textHash;
        public final byte[] senderHash;
        /** The message's whole second — the key's second, which {@link #prune} compares with the cursor. */
        public final long second;

        Entry(byte[] textHash, byte[] senderHash, long second) {
            this.textHash = textHash;
            this.senderHash = senderHash;
            this.second = second;
        }

        /** Hash lengths and the second only. */
        @Override
        public String toString() {
            return "Entry(" + textHash.length + "+" + senderHash.length + " bytes, second " + second + ")";
        }
    }

    private final String path;
    private final File sentFile, saltFile;
    private final Map<String, Entry> entries = new HashMap<>();
    private byte[] salt;
    private Mac mac;
    private boolean deleted;
    final Opened opened;

    /** The list for {@code stateDir}, loaded or created; the same instance for the same canonical path. */
    public static SentHashes open(File stateDir) {
        String path;
        try {
            path = stateDir.getCanonicalPath();
        } catch (IOException e) {
            path = stateDir.getAbsolutePath();
        }
        synchronized (SentHashes.class) {
            SentHashes s = INSTANCES.get(path);
            if (s == null) {
                s = new SentHashes(new File(path));
                INSTANCES.put(path, s);
            }
            return s;
        }
    }

    /** Forgets every open instance, so a test can reopen from disk as a new process would. */
    static void forgetInstancesForTest() {
        synchronized (SentHashes.class) {
            INSTANCES.clear();
        }
    }

    private SentHashes(File dir) {
        path = dir.getPath();
        sentFile = new File(dir, SENT_FILE);
        saltFile = new File(dir, SALT_FILE);
        if (!dir.isDirectory() && !dir.mkdirs() && !dir.isDirectory()) {
            throw new UncheckedIOException(new IOException("state folder cannot be created"));
        }
        byte[] s = readSalt();
        if (s == null) {
            boolean hadList = sentFile.exists();
            if (hadList && !sentFile.delete() && sentFile.exists()) {
                throw new UncheckedIOException(new IOException("stale sent list cannot be removed"));
            }
            s = new byte[SALT_BYTES];
            new SecureRandom().nextBytes(s);
            writeAtomically(saltFile, s);
            salt = s;
            initMac();
            writeAtomically(sentFile, serialise(entries));
            opened = hadList ? Opened.SALT_LOST_RESET : Opened.FRESH;
            return;
        }
        salt = s;
        initMac();
        if (!sentFile.exists()) {
            opened = Opened.FRESH;
            return;
        }
        Map<String, Entry> loaded = parse(readAll(sentFile));
        if (loaded == null) {
            writeAtomically(sentFile, serialise(entries));
            opened = Opened.UNREADABLE_RESET;
        } else {
            entries.putAll(loaded);
            opened = Opened.LOADED;
        }
    }

    // --- reads -------------------------------------------------------------------------------

    /** The entry for {@code key}, or null. */
    public synchronized Entry lookup(String key) {
        if (deleted) return null;
        return entries.get(key);
    }

    /** Every key whose text hash equals {@code textHash} — newest second first, then by key. */
    public synchronized List<String> keysForText(byte[] textHash) {
        List<Map.Entry<String, Entry>> hits = new ArrayList<>();
        if (deleted || textHash == null) return new ArrayList<>();
        for (Map.Entry<String, Entry> e : entries.entrySet()) {
            if (Arrays.equals(e.getValue().textHash, textHash)) hits.add(e);
        }
        Collections.sort(hits, (a, b) -> a.getValue().second != b.getValue().second
                ? Long.compare(b.getValue().second, a.getValue().second) : a.getKey().compareTo(b.getKey()));
        List<String> out = new ArrayList<>(hits.size());
        for (Map.Entry<String, Entry> e : hits) out.add(e.getKey());
        return out;
    }

    public synchronized int size() {
        return deleted ? 0 : entries.size();
    }

    // --- hashes ------------------------------------------------------------------------------

    /** First 16 bytes of HMAC-SHA256(salt, "t\0" + text as UTF-8). */
    public synchronized byte[] textHash(String text) {
        return hmac("t\u0000", text == null ? "" : text, TEXT_HASH_BYTES);
    }

    /** An empty array for a null or empty sender; else the first 8 bytes of HMAC-SHA256(salt, "s\0" + sender). */
    public synchronized byte[] senderHash(String sender) {
        if (sender == null || sender.isEmpty()) {
            live();
            return NO_SENDER.clone();
        }
        return hmac("s\u0000", sender, SENDER_HASH_BYTES);
    }

    // --- writes ------------------------------------------------------------------------------

    /** Records one key (replacing any earlier entry for it) and writes the list before returning. */
    public synchronized void record(String key, byte[] textHash, byte[] senderHash, long second) {
        live();
        Entry e = checked(key, textHash, senderHash, second);
        Entry before = entries.put(key, e);
        try {
            save();
        } catch (RuntimeException ex) {
            if (before == null) entries.remove(key);
            else entries.put(key, before);
            throw ex;
        }
    }

    /**
     * Records every given event in one write — what the nightly job does with a batch the VM
     * accepted (W5 records only those). All or nothing: a failed write records none of them.
     */
    public synchronized void recordAll(Iterable<EventPlan.Event> accepted) {
        live();
        Map<String, Entry> add = new HashMap<>();
        for (EventPlan.Event ev : accepted) add.put(ev.key, checked(ev.key, ev.textHash, ev.senderHash, ev.second));
        if (add.isEmpty()) return;
        Map<String, Entry> before = new HashMap<>(entries);
        entries.putAll(add);
        try {
            save();
        } catch (RuntimeException ex) {
            entries.clear();
            entries.putAll(before);
            throw ex;
        }
    }

    /** Drops keys whose second is before {@code newestCursorSeconds − 9 days}; exactly 9 days is kept. */
    public synchronized void prune(long newestCursorSeconds) {
        live();
        long floor = newestCursorSeconds - KEEP_SECONDS;
        Map<String, Entry> before = null;
        for (java.util.Iterator<Map.Entry<String, Entry>> it = entries.entrySet().iterator(); it.hasNext(); ) {
            Map.Entry<String, Entry> e = it.next();
            if (e.getValue().second < floor) {
                if (before == null) before = new HashMap<>(entries);
                it.remove();
            }
        }
        if (before == null) return;
        try {
            save();
        } catch (RuntimeException ex) {
            entries.clear();
            entries.putAll(before);
            throw ex;
        }
    }

    /**
     * A chat's merge (F2): every {@code from|…} key becomes {@code to|…} and every {@code r|from|…}
     * becomes {@code r|to|…}, in one write — so the night a shared chat gains its link, the messages
     * already sent under the old id are not sent again as new facts. An existing {@code to} key wins.
     * All or nothing: a failed write renames none. Returns how many keys moved.
     */
    public synchronized int rekeyChat(String from, String to) {
        live();
        if (from == null || to == null || from.isEmpty() || to.isEmpty() || from.equals(to)) return 0;
        String fromKey = from + "|", fromReply = "r|" + from + "|";
        Map<String, Entry> moved = new HashMap<>();
        List<String> gone = new ArrayList<>();
        for (Map.Entry<String, Entry> e : entries.entrySet()) {
            String k = e.getKey(), nk = null;
            if (k.startsWith(fromKey)) nk = to + "|" + k.substring(fromKey.length());
            else if (k.startsWith(fromReply)) nk = "r|" + to + "|" + k.substring(fromReply.length());
            if (nk == null) continue;
            gone.add(k);
            if (!entries.containsKey(nk)) moved.put(nk, e.getValue());
        }
        if (gone.isEmpty()) return 0;
        Map<String, Entry> before = new HashMap<>(entries);
        for (String k : gone) entries.remove(k);
        entries.putAll(moved);
        try {
            save();
        } catch (RuntimeException ex) {
            entries.clear();
            entries.putAll(before);
            throw ex;
        }
        return gone.size();
    }

    /**
     * Forgets everything sent for one chat ({@code chat|…} and {@code r|chat|…}) in one write — a
     * chat the user ticks again after un-ticking it was purged on the VM, so it is sent again (F3).
     * Returns how many keys went.
     */
    public synchronized int removeChat(String chat) {
        live();
        if (chat == null || chat.isEmpty()) return 0;
        String key = chat + "|", reply = "r|" + chat + "|";
        Map<String, Entry> before = null;
        int n = 0;
        for (java.util.Iterator<Map.Entry<String, Entry>> it = entries.entrySet().iterator(); it.hasNext(); ) {
            String k = it.next().getKey();
            if (!k.startsWith(key) && !k.startsWith(reply)) continue;
            if (before == null) before = new HashMap<>(entries);
            it.remove();
            n++;
        }
        if (before == null) return 0;
        try {
            save();
        } catch (RuntimeException ex) {
            entries.clear();
            entries.putAll(before);
            throw ex;
        }
        return n;
    }

    /**
     * Empties the list and keeps the salt and this instance — unlike {@link #deleteAll}. For a VM
     * that has forgotten everything (its cursor is null): nothing recorded here is there (F3).
     */
    public synchronized void clear() {
        live();
        if (entries.isEmpty()) return;
        Map<String, Entry> before = new HashMap<>(entries);
        entries.clear();
        try {
            save();
        } catch (RuntimeException ex) {
            entries.putAll(before);
            throw ex;
        }
    }

    /** "Turn off": removes both files, wipes the salt from memory and forgets this instance. */
    public void deleteAll() {
        synchronized (SentHashes.class) {
            synchronized (this) {
                deleted = true;
                entries.clear();
                if (salt != null) Arrays.fill(salt, (byte) 0);
                salt = null;
                mac = null;
                if (INSTANCES.get(path) == this) INSTANCES.remove(path);
                boolean ok = true;
                for (File f : new File[]{sentFile, tmp(sentFile), saltFile, tmp(saltFile)}) {
                    if (!f.delete() && f.exists()) ok = false;
                }
                if (!ok) throw new UncheckedIOException(new IOException("sent list or salt cannot be removed"));
            }
        }
    }

    /** Counts only. */
    @Override
    public synchronized String toString() {
        return "SentHashes(" + (deleted ? "deleted" : entries.size() + " keys") + ")";
    }

    // --- internals ---------------------------------------------------------------------------

    private void live() {
        if (deleted) throw new IllegalStateException("the sent list was deleted; open it again");
    }

    private static Entry checked(String key, byte[] textHash, byte[] senderHash, long second) {
        if (key == null || key.isEmpty()) throw new IllegalArgumentException("no key");
        if (textHash == null || textHash.length != TEXT_HASH_BYTES) throw new IllegalArgumentException("text hash length");
        if (senderHash == null || (senderHash.length != 0 && senderHash.length != SENDER_HASH_BYTES)) {
            throw new IllegalArgumentException("sender hash length");
        }
        if (second < 0) throw new IllegalArgumentException("negative second");
        return new Entry(textHash.clone(), senderHash.clone(), second);
    }

    private byte[] hmac(String prefix, String value, int n) {
        live();
        mac.reset();
        mac.update(prefix.getBytes(StandardCharsets.UTF_8));
        mac.update(value.getBytes(StandardCharsets.UTF_8));
        return Arrays.copyOf(mac.doFinal(), n);
    }

    private void initMac() {
        try {
            mac = Mac.getInstance("HmacSHA256");
            mac.init(new SecretKeySpec(salt, "HmacSHA256"));
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("HmacSHA256 unavailable", e);
        }
    }

    private byte[] readSalt() {
        if (!saltFile.isFile() || saltFile.length() != SALT_BYTES) return null;
        byte[] b = readAll(saltFile);
        return b != null && b.length == SALT_BYTES ? b : null;
    }

    private void save() {
        writeAtomically(sentFile, serialise(entries));
    }

    static byte[] serialise(Map<String, Entry> entries) {
        List<String> keys = new ArrayList<>(entries.keySet());
        Collections.sort(keys);
        JsonOut.Obj k = JsonOut.obj();
        for (String key : keys) {
            Entry e = entries.get(key);
            k.put(key, JsonOut.arr().add(hex(e.textHash)).add(hex(e.senderHash)).add(e.second));
        }
        return JsonOut.obj().put("v", 1).put("keys", k).toString().getBytes(StandardCharsets.UTF_8);
    }

    /** The entries in {@code raw}, or null if any part of it is not exactly the written shape. */
    static Map<String, Entry> parse(byte[] raw) {
        if (raw == null) return null;
        Object root;
        try {
            root = Json.parse(new String(raw, StandardCharsets.UTF_8));
        } catch (Json.Malformed | RuntimeException e) {
            return null;
        }
        if (!(root instanceof Map)) return null;
        Map<?, ?> m = (Map<?, ?>) root;
        if (m.size() != 2 || !Long.valueOf(1).equals(m.get("v")) || !(m.get("keys") instanceof Map)) return null;
        Map<String, Entry> out = new HashMap<>();
        for (Map.Entry<?, ?> e : ((Map<?, ?>) m.get("keys")).entrySet()) {
            String key = (String) e.getKey();
            if (key.isEmpty() || !(e.getValue() instanceof List)) return null;
            List<?> l = (List<?>) e.getValue();
            if (l.size() != 3 || !(l.get(0) instanceof String) || !(l.get(1) instanceof String)
                    || !(l.get(2) instanceof Long)) return null;
            byte[] t = unhex((String) l.get(0)), s = unhex((String) l.get(1));
            long second = (Long) l.get(2);
            if (t == null || t.length != TEXT_HASH_BYTES || s == null
                    || (s.length != 0 && s.length != SENDER_HASH_BYTES) || second < 0) return null;
            out.put(key, new Entry(t, s, second));
        }
        return out;
    }

    private static final char[] HEX = "0123456789abcdef".toCharArray();

    static String hex(byte[] b) {
        char[] c = new char[b.length * 2];
        for (int i = 0; i < b.length; i++) {
            c[2 * i] = HEX[(b[i] >> 4) & 0xf];
            c[2 * i + 1] = HEX[b[i] & 0xf];
        }
        return new String(c);
    }

    static byte[] unhex(String s) {
        if (s.length() % 2 != 0) return null;
        byte[] b = new byte[s.length() / 2];
        for (int i = 0; i < b.length; i++) {
            int hi = Character.digit(s.charAt(2 * i), 16), lo = Character.digit(s.charAt(2 * i + 1), 16);
            if (hi < 0 || lo < 0) return null;
            b[i] = (byte) ((hi << 4) | lo);
        }
        return b;
    }

    private static File tmp(File f) {
        return new File(f.getParentFile(), f.getName() + ".tmp");
    }

    /** Temp file, synced, renamed over {@code target}. On failure the temp file is removed and the old file stands. */
    private static void writeAtomically(File target, byte[] data) {
        File t = tmp(target);
        boolean ok = false;
        try {
            try (FileOutputStream out = new FileOutputStream(t)) {
                out.write(data);
                out.getFD().sync();
            }
            if (!t.renameTo(target)) throw new IOException("rename failed");
            ok = true;
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        } finally {
            if (!ok) t.delete();
        }
    }

    private static byte[] readAll(File f) {
        try (InputStream in = new FileInputStream(f)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
            return out.toByteArray();
        } catch (IOException e) {
            return null;
        }
    }
}
