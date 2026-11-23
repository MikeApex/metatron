package com.mike.metatron.whatsapp;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;
import java.util.zip.ZipEntry;
import java.util.zip.ZipFile;
import java.util.zip.ZipInputStream;

/**
 * Probe only — what is inside a crypt15 whose payload the reader refuses as
 * not_a_message_database. Plain Java (no Android types), so it runs under testWaprobeUnitTest.
 *
 * The container steps (header, AES-GCM, the MD5-trailer test, the tag) are re-done here with the
 * reader's own package-private parts — {@link BackupHeader}, {@link Gcm}, {@link BackupKey} — so
 * {@code src/main/} is not touched and its accept/refuse behaviour cannot change. Nothing is
 * judged until the tag has verified; a failed tag deletes the plaintext at once.
 *
 * Reports SHAPES only: which refusal branch, format magic (first 8 bytes, or 16 after
 * inflation), sizes, and for a ZIP each entry's name (digit runs masked), size and whether it
 * begins with the SQLite header. SQLite entries are extracted for the caller's shape report; other
 * entries are held in memory (never on disk) for ProbeShapes, and {@link #wipe} zeroes them.
 * Every file written starts with {@link #PREFIX} in the work dir; {@link #sweep} removes them all.
 */
final class ProbePayload {
    /** Every file this probe writes in the work dir starts with this — and only these are swept. */
    static final String PREFIX = "increment.";
    static final int MAX_SQLITE_ENTRIES = 4;
    static final int MAX_LISTED_ENTRIES = 40;
    /** An increment is ~0.1 MB; stop well short of filling the phone if something is odd. */
    static final long INFLATE_CAP = 512L * 1024 * 1024;
    /** Non-SQLite entries are kept in memory for their shape report — never written to disk. */
    static final int KEEP_ENTRY_CAP = 8 * 1024 * 1024;
    static final long KEEP_TOTAL_CAP = 32L * 1024 * 1024;

    private static final int BUF = 64 * 1024;
    private static final byte[] ZIP_MAGIC = {'P', 'K', 3, 4};

    static final class Entry {
        String name;
        long size = -1, compressedSize = -1;
        int method = -1;
        String head8 = "";
        boolean sqlite;
        File extracted;
        /** A non-SQLite entry's bytes, held in memory for ProbeShapes; zeroed by {@link #wipe}. */
        byte[] bytes;
    }

    static final class Inspection {
        boolean tagOk, md5Trailer;
        long payloadBytes;
        String payloadHead8 = "";
        /** sqlite | zlib | zip | other */
        String kind = "";
        /** Which of BackupDecryptor's refusals this is, in words. */
        String branch = "";
        long inflatedBytes = -1, trailingAfterZlib;
        String inflatedHead16 = "";
        boolean inflateCapped;
        String inflateError;
        /** "payload" or "inflated output" — whichever held the ZIP; null when there is no ZIP. */
        String zipIn;
        String zipReader, zipError;
        int entryCount;
        final List<Entry> entries = new ArrayList<>();
        long keptBytes;

        List<Entry> sqliteEntries() {
            List<Entry> out = new ArrayList<>();
            for (Entry e : entries) if (e.extracted != null) out.add(e);
            return out;
        }
    }

    private ProbePayload() {}

    static Inspection inspect(File backup, BackupKey key, File work) throws BackupException, IOException {
        Inspection r = new Inspection();
        File payload = new File(work, PREFIX + "payload");
        decryptRaw(backup, key, payload, r);
        if (!r.tagOk) {
            payload.delete();
            r.kind = "unverified";
            r.branch = "tag did not verify — plaintext discarded unread";
            return r;
        }
        byte[] head = head(payload, 16);
        r.payloadHead8 = hex(head, 8);
        if (head.length == 16 && Arrays.equals(head, BackupDecryptor.SQLITE_HEADER)) {
            r.kind = "sqlite";
            r.branch = "raw SQLite — the reader would ACCEPT this; not the refusal seen";
        } else if (head.length >= 2 && isZlibHeader(head[0] & 0xff, head[1] & 0xff)) {
            r.kind = "zlib";
            File inflated = new File(work, PREFIX + "inflated");
            inflate(payload, inflated, r);
            byte[] ih = head(inflated, 16);
            r.inflatedHead16 = hex(ih, 16);
            if (r.inflateError != null) {
                r.branch = "zlib that does not inflate cleanly (" + r.inflateError + ") — the reader says integrity/truncated, not this";
            } else if (ih.length == 16 && Arrays.equals(ih, BackupDecryptor.SQLITE_HEADER)) {
                r.branch = "inflated SQLite — the reader would ACCEPT this; not the refusal seen";
            } else {
                r.branch = "inflated, tag passed, output NOT SQLite — refused in Sink.finish()";
                if (startsWith(ih, ZIP_MAGIC)) listZip(inflated, "inflated output", work, r);
            }
        } else if (startsWith(head, ZIP_MAGIC)) {
            r.kind = "zip";
            r.branch = "ZIP payload (PK\\x03\\x04) — refused in Sink.decide()";
            listZip(payload, "payload", work, r);
        } else {
            r.kind = "other";
            r.branch = "neither SQLite, zlib nor ZIP — the reader says wrong_key for this, not the refusal seen";
        }
        return r;
    }

    /** Report lines for an inspection. Shapes only. */
    static void lines(Inspection r, StringBuilder b) {
        b.append("container: tag ").append(r.tagOk ? "verified" : "FAILED").append(", MD5 trailer ")
                .append(r.md5Trailer ? "yes" : "no").append(", payload ").append(r.payloadBytes).append(" bytes\n");
        b.append("refusal branch: ").append(r.branch).append('\n');
        if (!r.tagOk) return;
        b.append("payload first 8 bytes: ").append(r.payloadHead8).append("  (kind: ").append(r.kind).append(")\n");
        if ("zlib".equals(r.kind)) {
            b.append("inflated size: ").append(r.inflatedBytes).append(" bytes").append(r.inflateCapped ? " (STOPPED at cap)" : "")
                    .append(", bytes after the zlib stream: ").append(r.trailingAfterZlib).append('\n');
            b.append("inflated first 16 bytes: ").append(r.inflatedHead16).append('\n');
        }
        if (r.zipIn == null) return;
        b.append("ZIP in the ").append(r.zipIn).append(", read by ").append(r.zipReader)
                .append(r.zipError == null ? "" : " (ZipFile refused: " + r.zipError + ")").append('\n');
        b.append("ZIP entries: ").append(r.entryCount).append('\n');
        int i = 0;
        for (Entry e : r.entries) {
            b.append("  [").append(++i).append("] ").append(e.name).append("  size ").append(e.size)
                    .append("  stored ").append(e.compressedSize).append("  method ").append(method(e.method))
                    .append("  first 8: ").append(e.head8).append("  SQLite: ").append(e.sqlite ? "YES" : "no")
                    .append(e.sqlite && e.extracted == null ? " (not extracted — over the cap)" : "").append('\n');
        }
        if (r.entryCount > r.entries.size()) {
            b.append("  … ").append(r.entryCount - r.entries.size()).append(" more not listed\n");
        }
    }

    /** Zeroes and drops every entry held in memory. Safe to call twice. */
    static void wipe(Inspection r) {
        if (r == null) return;
        for (Entry e : r.entries) {
            if (e.bytes != null) {
                Arrays.fill(e.bytes, (byte) 0);
                e.bytes = null;
            }
        }
        r.keptBytes = 0;
    }

    /** Deletes every file this probe wrote in the work dir (and SQLite side files). Returns how many remain. */
    static int sweep(File work) {
        File[] files = work.listFiles();
        if (files == null) return 0;
        int left = 0;
        for (File f : files) {
            if (!f.getName().startsWith(PREFIX)) continue;
            if (!f.delete() && f.exists()) left++;
        }
        return left;
    }

    static String hex(byte[] b, int n) {
        StringBuilder s = new StringBuilder();
        for (int i = 0; i < Math.min(n, b.length); i++) {
            if (i > 0) s.append(' ');
            s.append(String.format(Locale.US, "%02x", b[i] & 0xff));
        }
        return s.length() == 0 ? "(empty)" : s.toString();
    }

    /** Entry names are shown, but a run of 6+ digits (a phone number, a jid) is reduced to its length. */
    static String maskDigits(String name) {
        java.util.regex.Matcher m = java.util.regex.Pattern.compile("\\d{6,}").matcher(name);
        StringBuffer sb = new StringBuffer();
        while (m.find()) m.appendReplacement(sb, "#{" + m.group().length() + "}");
        m.appendTail(sb);
        return sb.toString();
    }

    // ---- container -----------------------------------------------------------------------

    /**
     * The container steps as BackupDecryptor does them: plaintext for [dataStart, tailStart) is
     * written as it goes; the last 32 bytes are held back and read as tag + MD5, or as ciphertext +
     * tag when the MD5 does not match. The caller must not read {@code out} unless tagOk.
     */
    private static void decryptRaw(File backup, BackupKey key, File out, Inspection r) throws BackupException, IOException {
        final long len = backup.length();
        byte[] prefix = new byte[BackupHeader.MAX_PREFIX];
        int prefixLen;
        try (InputStream in = new FileInputStream(backup)) {
            prefixLen = readFully(in, prefix);
        }
        BackupHeader header = BackupHeader.parse(prefix, prefixLen);
        final long dataStart = header.dataStart;
        if (len - dataStart < 16) throw new BackupException(BackupError.TRUNCATED);
        final long tailStart = Math.max(dataStart, len - 32);
        final long md5End = len - 16;

        byte[] buf = new byte[BUF], plain = new byte[BUF];
        byte[] tail = new byte[(int) (len - tailStart)];
        Gcm gcm = null;
        try (OutputStream o = new FileOutputStream(out)) {
            gcm = new Gcm(key.aesKey(), header.iv);
            MessageDigest md5 = MessageDigest.getInstance("MD5");
            long written = 0;
            try (InputStream in = new BufferedInputStream(new FileInputStream(backup), BUF)) {
                long pos = 0;
                int n;
                while ((n = in.read(buf)) > 0) {
                    if (pos + n > len) throw new BackupException(BackupError.BEING_WRITTEN);
                    long chunkEnd = pos + n;
                    if (pos < md5End) md5.update(buf, 0, (int) (Math.min(chunkEnd, md5End) - pos));
                    long cs = Math.max(pos, dataStart), ce = Math.min(chunkEnd, tailStart);
                    if (cs < ce) {
                        int off = (int) (cs - pos), cn = (int) (ce - cs);
                        gcm.update(buf, off, cn, plain, 0);
                        o.write(plain, 0, cn);
                        written += cn;
                    }
                    long ts = Math.max(pos, tailStart);
                    if (ts < chunkEnd) System.arraycopy(buf, (int) (ts - pos), tail, (int) (ts - tailStart), (int) (chunkEnd - ts));
                    pos = chunkEnd;
                }
                if (pos != len || backup.length() != len) throw new BackupException(BackupError.BEING_WRITTEN);
            }
            byte[] digest = md5.digest();
            r.md5Trailer = tail.length == 32 && MessageDigest.isEqual(digest, Arrays.copyOfRange(tail, 16, 32));
            byte[] expectedTag;
            if (r.md5Trailer) {
                expectedTag = Arrays.copyOfRange(tail, 0, 16);
            } else {
                int extra = tail.length - 16;
                if (extra > 0) {
                    gcm.update(tail, 0, extra, plain, 0);
                    o.write(plain, 0, extra);
                    written += extra;
                }
                expectedTag = Arrays.copyOfRange(tail, extra, tail.length);
            }
            r.tagOk = MessageDigest.isEqual(gcm.tag(), expectedTag);
            r.payloadBytes = written;
        } catch (GeneralSecurityException e) {
            throw new IllegalStateException("platform crypto unavailable", e);
        } finally {
            if (gcm != null) gcm.wipe();
            Arrays.fill(buf, (byte) 0);
            Arrays.fill(plain, (byte) 0);
        }
    }

    private static boolean isZlibHeader(int cmf, int flg) {
        return cmf == 0x78 && (flg & 0x20) == 0 && ((cmf << 8) | flg) % 31 == 0;
    }

    // ---- payload ---------------------------------------------------------------------------

    private static void inflate(File in, File out, Inspection r) throws IOException {
        Inflater inf = new Inflater();
        byte[] buf = new byte[BUF], o = new byte[BUF];
        long produced = 0;
        try (InputStream is = new FileInputStream(in); OutputStream os = new FileOutputStream(out)) {
            int n;
            outer:
            while ((n = is.read(buf)) > 0) {
                if (inf.finished()) {
                    r.trailingAfterZlib += n;
                    continue;
                }
                inf.setInput(buf, 0, n);
                while (!inf.needsInput() && !inf.finished()) {
                    int k = inf.inflate(o);
                    if (k > 0) {
                        os.write(o, 0, k);
                        produced += k;
                        if (produced >= INFLATE_CAP) {
                            r.inflateCapped = true;
                            break outer;
                        }
                    } else if (inf.needsDictionary()) {
                        r.inflateError = "needs a preset dictionary";
                        break outer;
                    }
                }
                if (inf.finished()) r.trailingAfterZlib += inf.getRemaining();
            }
            if (r.inflateError == null && !r.inflateCapped && !inf.finished()) r.inflateError = "stream ends before the zlib end";
        } catch (DataFormatException e) {
            r.inflateError = "bad deflate data";
        } finally {
            inf.end();
            Arrays.fill(o, (byte) 0);
        }
        r.inflatedBytes = produced;
    }

    private static void listZip(File zip, String where, File work, Inspection r) {
        r.zipIn = where;
        try (ZipFile z = new ZipFile(zip)) {
            r.zipReader = "ZipFile (central directory)";
            Enumeration<? extends ZipEntry> en = z.entries();
            while (en.hasMoreElements()) {
                ZipEntry ze = en.nextElement();
                r.entryCount++;
                if (r.entries.size() >= MAX_LISTED_ENTRIES || ze.isDirectory()) continue;
                Entry e = start(ze);
                try (InputStream in = z.getInputStream(ze)) {
                    readEntry(in, e, work, r);
                } catch (IOException ex) {
                    e.head8 = "(unreadable: " + ex.getClass().getSimpleName() + ")";
                }
                r.entries.add(e);
            }
            return;
        } catch (IOException ex) {
            r.zipError = ex.getClass().getSimpleName();
            r.entries.clear();
            r.entryCount = 0;
        }
        // Fallback: read the local headers in order.
        r.zipReader = "ZipInputStream (local headers)";
        try (ZipInputStream zin = new ZipInputStream(new BufferedInputStream(new FileInputStream(zip)))) {
            ZipEntry ze;
            while ((ze = zin.getNextEntry()) != null) {
                r.entryCount++;
                if (r.entries.size() >= MAX_LISTED_ENTRIES || ze.isDirectory()) continue;
                Entry e = start(ze);
                long read = readEntry(zin, e, work, r);
                if (e.size < 0) e.size = read;
                r.entries.add(e);
            }
        } catch (IOException ex) {
            r.zipReader += ", stopped: " + ex.getClass().getSimpleName();
        }
    }

    private static Entry start(ZipEntry ze) {
        Entry e = new Entry();
        e.name = maskDigits(ze.getName());
        e.size = ze.getSize();
        e.compressedSize = ze.getCompressedSize();
        e.method = ze.getMethod();
        return e;
    }

    /** Reads an entry once: its first 16 bytes decide; a SQLite entry under the cap is copied out. Returns bytes read. */
    private static long readEntry(InputStream in, Entry e, File work, Inspection r) throws IOException {
        byte[] head = new byte[16];
        int hn = readFully(in, head);
        e.head8 = hex(Arrays.copyOf(head, hn), 8);
        e.sqlite = hn == 16 && Arrays.equals(head, BackupDecryptor.SQLITE_HEADER);
        long total = hn;
        byte[] buf = new byte[BUF];
        if (e.sqlite && r.sqliteEntries().size() < MAX_SQLITE_ENTRIES) {
            File out = new File(work, PREFIX + "entry" + (r.sqliteEntries().size() + 1) + ".db");
            try (OutputStream os = new FileOutputStream(out)) {
                os.write(head, 0, hn);
                int n;
                while ((n = in.read(buf)) > 0) {
                    os.write(buf, 0, n);
                    total += n;
                }
            }
            e.extracted = out;
        } else if (!e.sqlite && e.size <= KEEP_ENTRY_CAP && r.keptBytes < KEEP_TOTAL_CAP) {
            // Held for ProbeShapes. A size the central directory does not state (-1) is read up to the cap.
            java.io.ByteArrayOutputStream kept = new java.io.ByteArrayOutputStream();
            kept.write(head, 0, hn);
            int n;
            boolean over = false;
            while ((n = in.read(buf)) > 0) {
                total += n;
                if (!over && kept.size() + n <= KEEP_ENTRY_CAP) kept.write(buf, 0, n);
                else over = true;
            }
            if (!over) {
                e.bytes = kept.toByteArray();
                r.keptBytes += e.bytes.length;
            }
        } else {
            int n;
            while ((n = in.read(buf)) > 0) total += n;
        }
        Arrays.fill(head, (byte) 0);
        Arrays.fill(buf, (byte) 0);
        return total;
    }

    // ---- small helpers ---------------------------------------------------------------------

    private static byte[] head(File f, int n) throws IOException {
        if (!f.isFile()) return new byte[0];
        byte[] b = new byte[n];
        int got;
        try (InputStream in = new FileInputStream(f)) {
            got = readFully(in, b);
        }
        return Arrays.copyOf(b, got);
    }

    private static boolean startsWith(byte[] b, byte[] magic) {
        if (b.length < magic.length) return false;
        for (int i = 0; i < magic.length; i++) if (b[i] != magic[i]) return false;
        return true;
    }

    private static String method(int m) {
        return m == ZipEntry.STORED ? "stored" : m == ZipEntry.DEFLATED ? "deflated" : String.valueOf(m);
    }

    private static int readFully(InputStream in, byte[] b) throws IOException {
        int n = 0, k;
        while (n < b.length && (k = in.read(b, n, b.length - n)) > 0) n += k;
        return n;
    }
}
