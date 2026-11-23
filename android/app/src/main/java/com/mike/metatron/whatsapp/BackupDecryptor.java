package com.mike.metatron.whatsapp;

import java.io.BufferedInputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.security.GeneralSecurityException;
import java.security.MessageDigest;
import java.util.Arrays;
import java.util.zip.DataFormatException;
import java.util.zip.Inflater;

/**
 * Decrypts a WhatsApp crypt15 backup into the SQLite database it holds, as a stream.
 *
 * Written from archive/plans/whatsapp_backup_format_2026-10-26.md alone (clean room, plan
 * W9). One pass over the file: the MD5 is computed as it goes, the last 32 bytes are held
 * back, and only at the end — once it is known whether the file carries an MD5 trailer
 * (§ 3) — are they read as tag or as ciphertext.
 *
 * Nothing is exposed until every check has passed: output goes to a temporary file beside
 * the destination and is renamed only after the GCM tag verifies, the zlib stream has
 * ended with nothing after it, and the result begins with the SQLite header. On any
 * failure the temporary file is deleted (§ 6.5). Nothing is logged.
 */
public final class BackupDecryptor {
    /** Free space required, as a multiple of the encrypted size, until Phase 0 measures the ratio (§ 6.5). */
    public static final int SPACE_FACTOR = 10;

    private static final int BUF = 64 * 1024;
    static final byte[] SQLITE_HEADER = "SQLite format 3\0".getBytes(java.nio.charset.StandardCharsets.US_ASCII);

    /** How much space the destination directory has. Injectable so the check is testable. */
    public interface SpaceProbe {
        long usableBytes(File dir);
    }

    public static final SpaceProbe FILESYSTEM = File::getUsableSpace;

    public static final class Result {
        public final File database;
        public final long encryptedBytes;
        public final long decryptedBytes;
        public final boolean compressed;
        public final boolean md5Trailer;
        public final boolean featureMarker;
        public final long millis;

        Result(File database, long encryptedBytes, long decryptedBytes, boolean compressed,
               boolean md5Trailer, boolean featureMarker, long millis) {
            this.database = database;
            this.encryptedBytes = encryptedBytes;
            this.decryptedBytes = decryptedBytes;
            this.compressed = compressed;
            this.md5Trailer = md5Trailer;
            this.featureMarker = featureMarker;
            this.millis = millis;
        }
    }

    private BackupDecryptor() {}

    /**
     * @param backup      the .crypt15 file — the caller has already checked it is not being written
     * @param key         the derived key from {@link BackupKey}
     * @param destination where the database should appear; replaced only on success
     */
    public static Result decrypt(File backup, BackupKey key, File destination, SpaceProbe space)
            throws BackupException, IOException {
        long started = System.nanoTime();
        final long len = backup.length();

        byte[] prefix = new byte[BackupHeader.MAX_PREFIX];
        int prefixLen;
        try (InputStream in = new FileInputStream(backup)) {
            prefixLen = readFully(in, prefix);
        }
        BackupHeader header = BackupHeader.parse(prefix, prefixLen);

        File dir = destination.getAbsoluteFile().getParentFile();
        if (space.usableBytes(dir) / SPACE_FACTOR < len) {
            throw new BackupException(BackupError.INSUFFICIENT_SPACE);
        }

        final long dataStart = header.dataStart;
        if (len - dataStart < 16) throw new BackupException(BackupError.TRUNCATED);
        // [tailStart, len) is held back: 32 bytes (tag + MD5) or, for a tiny file, 16..31.
        final long tailStart = Math.max(dataStart, len - 32);
        final long md5End = len - 16;

        File temp = new File(dir, destination.getName() + ".partial");
        boolean ok = false;
        Gcm gcm = null;
        Sink sink = null;
        byte[] buf = new byte[BUF];
        byte[] plain = new byte[BUF];
        byte[] tail = new byte[(int) (len - tailStart)];
        try {
            gcm = new Gcm(key.aesKey(), header.iv);
            MessageDigest md5 = MessageDigest.getInstance("MD5");
            sink = new Sink(new FileOutputStream(temp));

            try (InputStream in = new BufferedInputStream(new FileInputStream(backup), BUF)) {
                long pos = 0;
                int n;
                while ((n = in.read(buf)) > 0) {
                    if (pos + n > len) throw new BackupException(BackupError.BEING_WRITTEN);
                    long chunkEnd = pos + n;
                    // MD5 over [0, len-16)
                    if (pos < md5End) md5.update(buf, 0, (int) (Math.min(chunkEnd, md5End) - pos));
                    // ciphertext certainly in [dataStart, tailStart)
                    long cs = Math.max(pos, dataStart), ce = Math.min(chunkEnd, tailStart);
                    if (cs < ce) {
                        int off = (int) (cs - pos), cn = (int) (ce - cs);
                        gcm.update(buf, off, cn, plain, 0);
                        sink.write(plain, 0, cn);
                    }
                    // the held-back tail
                    long ts = Math.max(pos, tailStart);
                    if (ts < chunkEnd) {
                        System.arraycopy(buf, (int) (ts - pos), tail, (int) (ts - tailStart), (int) (chunkEnd - ts));
                    }
                    pos = chunkEnd;
                }
                if (pos != len || backup.length() != len) throw new BackupException(BackupError.BEING_WRITTEN);
            }

            byte[] digest = md5.digest();
            boolean md5Trailer = tail.length == 32
                    && MessageDigest.isEqual(digest, Arrays.copyOfRange(tail, 16, 32));
            byte[] expectedTag;
            if (md5Trailer) {
                expectedTag = Arrays.copyOfRange(tail, 0, 16);
            } else {
                // No-trailer form: everything before the last 16 bytes is ciphertext.
                int extra = tail.length - 16;
                if (extra > 0) {
                    gcm.update(tail, 0, extra, plain, 0);
                    sink.write(plain, 0, extra);
                }
                expectedTag = Arrays.copyOfRange(tail, extra, tail.length);
            }
            boolean tagOk = MessageDigest.isEqual(gcm.tag(), expectedTag);
            sink.finish(tagOk);
            sink.close();

            if (!temp.renameTo(destination)) throw new IOException("rename failed");
            ok = true;
            long millis = (System.nanoTime() - started) / 1_000_000L;
            return new Result(destination, len, sink.outBytes, sink.mode == Mode.ZLIB, md5Trailer,
                    header.featureMarker, millis);
        } catch (GeneralSecurityException e) {
            // AES/ECB and MD5 are mandatory platform algorithms; this is a broken runtime.
            throw new IllegalStateException("platform crypto unavailable", e);
        } finally {
            if (sink != null) sink.closeQuietly();
            if (gcm != null) gcm.wipe();
            Arrays.fill(buf, (byte) 0);
            Arrays.fill(plain, (byte) 0);
            if (!ok) temp.delete();
        }
    }

    /** Deletes a decrypted copy, and any half-written one a crash left behind (plan P3's app-start sweep). */
    public static void deleteDecrypted(File destination) {
        destination.delete();
        new File(destination.getAbsoluteFile().getParentFile(), destination.getName() + ".partial").delete();
        // SQLite side files, should anything have opened the copy.
        new File(destination.getPath() + "-journal").delete();
        new File(destination.getPath() + "-wal").delete();
        new File(destination.getPath() + "-shm").delete();
    }

    private static int readFully(InputStream in, byte[] b) throws IOException {
        int n = 0, r;
        while (n < b.length && (r = in.read(b, n, b.length - n)) > 0) n += r;
        return n;
    }

    /** UNKNOWN: the first bytes are none of the known kinds — output is discarded and the tag decides. */
    private enum Mode { UNDECIDED, ZLIB, RAW, UNKNOWN }

    /**
     * Receives plaintext: identifies the payload from its first block (§ 6.2), inflates or
     * copies it to the temporary file, and judges completeness at the end.
     */
    private static final class Sink {
        private final FileOutputStream out;
        private Mode mode = Mode.UNDECIDED;
        private final byte[] first = new byte[16];
        private int firstLen;
        private final Inflater inflater = new Inflater();
        private final byte[] inflated = new byte[BUF];
        private final byte[] outHead = new byte[16];
        private int outHeadLen;
        long outBytes;
        private long trailing;
        private boolean closed;

        Sink(FileOutputStream out) {
            this.out = out;
        }

        void write(byte[] b, int off, int len) throws BackupException, IOException {
            if (len == 0) return;
            if (mode == Mode.UNDECIDED) {
                int take = Math.min(len, 16 - firstLen);
                System.arraycopy(b, off, first, firstLen, take);
                firstLen += take;
                off += take;
                len -= take;
                if (firstLen < 16) return;
                decide();
                feed(first, 0, 16);
            }
            feed(b, off, len);
        }

        void finish(boolean tagOk) throws BackupException, IOException {
            if (mode == Mode.UNDECIDED) {
                if (firstLen == 0) throw new BackupException(BackupError.TRUNCATED);
                decide();
                feed(first, 0, firstLen);
            }
            // Unfamiliar first bytes: a verified tag proves the key right, so the format changed.
            if (mode == Mode.UNKNOWN) throw new BackupException(tagOk ? BackupError.UNKNOWN_FORMAT : BackupError.WRONG_KEY);
            if (mode == Mode.ZLIB && !inflater.finished()) throw new BackupException(BackupError.TRUNCATED);
            if (!tagOk) throw new BackupException(BackupError.INTEGRITY);
            if (trailing > 0) throw new BackupException(BackupError.INTEGRITY, trailing + " bytes after the zlib stream");
            if (outHeadLen < 16 || !Arrays.equals(outHead, SQLITE_HEADER)) {
                throw new BackupException(BackupError.NOT_A_MESSAGE_DATABASE);
            }
            out.getFD().sync();
        }

        /**
         * With the right key the payload begins zlib, SQLite or ZIP. Anything else is either
         * the wrong key or a format WhatsApp changed, and only the tag can tell them apart —
         * so it is not refused here: the payload is discarded (nothing more reaches the
         * temporary file) and the decryptor carries on to the tag, which {@link #finish}
         * judges: tag fails → wrong_key, tag verifies → unknown_format (review finding 7).
         * Without this a correct key would be reported as wrong every night after a change.
         * The zlib test is the full RFC 1950 header check, not just 0x78, so a wrong key has
         * a ~1/8000 rather than 1/256 chance of passing it — and if it does, the tag still
         * fails and the file is refused as damaged, never accepted.
         */
        private void decide() throws BackupException {
            if (firstLen == 16 && Arrays.equals(first, SQLITE_HEADER)) {
                mode = Mode.RAW;
            } else if (firstLen >= 2 && isZlibHeader(first[0] & 0xff, first[1] & 0xff)) {
                mode = Mode.ZLIB;
            } else if (firstLen >= 4 && first[0] == 'P' && first[1] == 'K' && first[2] == 3 && first[3] == 4) {
                throw new BackupException(BackupError.NOT_A_MESSAGE_DATABASE);
            } else {
                mode = Mode.UNKNOWN;
                Arrays.fill(first, (byte) 0);
            }
        }

        private static boolean isZlibHeader(int cmf, int flg) {
            return cmf == 0x78                    // deflate (CM=8), 32 KB window (CINFO=7) — § 5's observed header
                    && (flg & 0x20) == 0          // no preset dictionary
                    && ((cmf << 8) | flg) % 31 == 0;
        }

        private void feed(byte[] b, int off, int len) throws BackupException, IOException {
            if (len == 0 || mode == Mode.UNKNOWN) return;
            if (mode == Mode.RAW) {
                emit(b, off, len);
                return;
            }
            if (inflater.finished()) {
                trailing += len;
                return;
            }
            inflater.setInput(b, off, len);
            try {
                while (!inflater.needsInput() && !inflater.finished()) {
                    int n = inflater.inflate(inflated);
                    if (n > 0) emit(inflated, 0, n);
                    else if (inflater.needsDictionary()) throw new BackupException(BackupError.INTEGRITY);
                }
            } catch (DataFormatException e) {
                throw new BackupException(BackupError.INTEGRITY);
            }
            if (inflater.finished()) trailing += inflater.getRemaining();
        }

        private void emit(byte[] b, int off, int len) throws IOException {
            if (outHeadLen < 16) {
                int take = Math.min(len, 16 - outHeadLen);
                System.arraycopy(b, off, outHead, outHeadLen, take);
                outHeadLen += take;
            }
            out.write(b, off, len);
            outBytes += len;
        }

        void close() throws IOException {
            if (closed) return;
            closed = true;
            out.close();
            inflater.end();
        }

        void closeQuietly() {
            try {
                close();
            } catch (IOException ignored) {
                // the temporary file is deleted by the caller on failure
            }
            Arrays.fill(inflated, (byte) 0);
            Arrays.fill(first, (byte) 0);
        }
    }
}
