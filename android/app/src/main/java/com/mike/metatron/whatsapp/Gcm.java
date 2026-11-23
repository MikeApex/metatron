package com.mike.metatron.whatsapp;

import java.security.GeneralSecurityException;

import javax.crypto.Cipher;
import javax.crypto.spec.SecretKeySpec;

/**
 * AES-GCM decryption as a true stream (NIST SP 800-38D), with no associated data.
 *
 * Why not {@code Cipher.getInstance("AES/GCM/NoPadding")}: both the desktop JVM's provider
 * and Android's Conscrypt hold back the entire ciphertext until {@code doFinal}, so a
 * backup of tens of megabytes would sit in memory whole — the thing format description
 * § 6.5 forbids. This class releases plaintext as it goes; the caller must therefore treat
 * every byte as unauthenticated until {@link #tag()} matches, which is why the reader
 * writes to a temporary file that is deleted on any failure.
 *
 * The block cipher comes from the platform (AES/ECB on counter blocks); only the GCM mode
 * — counter generation with inc32 and GHASH — is implemented here. GHASH uses the 4-bit
 * table method (Shoup). Cross-checked against the platform GCM in the unit tests.
 */
final class Gcm {
    private static final int KS_BLOCKS = 256; // keystream generated 4 KB at a time

    /** Reduction constants for the 4-bit GHASH table method. */
    private static final long[] LAST4 = {
            0x0000L, 0x1c20L, 0x3840L, 0x2460L, 0x7080L, 0x6ca0L, 0x48c0L, 0x54e0L,
            0xe100L, 0xfd20L, 0xd940L, 0xc560L, 0x9180L, 0x8da0L, 0xa9c0L, 0xb5e0L,
    };

    private final Cipher aes;
    private final long[] hh = new long[16];
    private final long[] hl = new long[16];
    private final byte[] ekJ0;
    private final byte[] counter;
    private final byte[] ctrBuf = new byte[KS_BLOCKS * 16];
    private final byte[] ksBuf = new byte[KS_BLOCKS * 16];
    private int ksPos = ksBuf.length;

    // GHASH accumulator over the ciphertext.
    private long zh, zl;
    private final byte[] partial = new byte[16];
    private int partialLen;
    private long ctBytes;

    private final long[] tmp = new long[2];

    Gcm(byte[] key, byte[] iv) throws GeneralSecurityException {
        if (iv.length == 0) throw new IllegalArgumentException("empty IV");
        aes = Cipher.getInstance("AES/ECB/NoPadding");
        aes.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"));
        byte[] h = aes.doFinal(new byte[16]);
        initTable(be64(h, 0), be64(h, 8));
        java.util.Arrays.fill(h, (byte) 0);

        byte[] j0 = new byte[16];
        if (iv.length == 12) {
            System.arraycopy(iv, 0, j0, 0, 12);
            j0[15] = 1;
        } else {
            // J0 = GHASH(IV || 0^(s+64) || [len(IV) in bits]_64)
            long[] y = {0, 0};
            byte[] block = new byte[16];
            for (int off = 0; off < iv.length; off += 16) {
                java.util.Arrays.fill(block, (byte) 0);
                System.arraycopy(iv, off, block, 0, Math.min(16, iv.length - off));
                absorb(y, be64(block, 0), be64(block, 8));
            }
            absorb(y, 0, (long) iv.length * 8);
            put64(j0, 0, y[0]);
            put64(j0, 8, y[1]);
        }
        ekJ0 = aes.doFinal(j0);
        counter = j0.clone();
        inc32(counter);
    }

    /** Decrypts {@code len} bytes of ciphertext into {@code out} and absorbs them into GHASH. */
    void update(byte[] in, int off, int len, byte[] out, int outOff) throws GeneralSecurityException {
        for (int i = 0; i < len; i++) {
            if (ksPos == ksBuf.length) refillKeystream();
            byte c = in[off + i];
            out[outOff + i] = (byte) (c ^ ksBuf[ksPos++]);
            partial[partialLen++] = c;
            if (partialLen == 16) {
                tmp[0] = zh; tmp[1] = zl;
                absorb(tmp, be64(partial, 0), be64(partial, 8));
                zh = tmp[0]; zl = tmp[1];
                partialLen = 0;
            }
        }
        ctBytes += len;
    }

    /** The authentication tag over everything passed to {@link #update} so far. Does not change state. */
    byte[] tag() {
        long[] y = {zh, zl};
        if (partialLen > 0) {
            byte[] block = new byte[16];
            System.arraycopy(partial, 0, block, 0, partialLen);
            absorb(y, be64(block, 0), be64(block, 8));
        }
        absorb(y, 0, ctBytes * 8); // [len(A)=0]_64 || [len(C)]_64
        byte[] t = new byte[16];
        put64(t, 0, y[0]);
        put64(t, 8, y[1]);
        for (int i = 0; i < 16; i++) t[i] ^= ekJ0[i];
        return t;
    }

    /** Overwrites keystream and partial-block buffers (the cipher's key schedule is the platform's). */
    void wipe() {
        java.util.Arrays.fill(ksBuf, (byte) 0);
        java.util.Arrays.fill(ctrBuf, (byte) 0);
        java.util.Arrays.fill(partial, (byte) 0);
        java.util.Arrays.fill(hh, 0);
        java.util.Arrays.fill(hl, 0);
    }

    private void refillKeystream() throws GeneralSecurityException {
        for (int b = 0; b < KS_BLOCKS; b++) {
            System.arraycopy(counter, 0, ctrBuf, b * 16, 16);
            inc32(counter);
        }
        aes.doFinal(ctrBuf, 0, ctrBuf.length, ksBuf, 0);
        ksPos = 0;
    }

    /** Increments the low 32 bits only, wrapping, as GCM requires — not the whole 128-bit block. */
    static void inc32(byte[] block) {
        for (int i = 15; i >= 12; i--) {
            if (++block[i] != 0) return;
        }
    }

    // ---- GHASH -------------------------------------------------------------------------

    private void initTable(long vh, long vl) {
        hh[8] = vh;
        hl[8] = vl;
        for (int i = 4; i > 0; i >>= 1) {
            long t = (vl & 1) * 0xe1000000L;
            vl = (vh << 63) | (vl >>> 1);
            vh = (vh >>> 1) ^ (t << 32);
            hh[i] = vh;
            hl[i] = vl;
        }
        for (int i = 2; i <= 8; i *= 2) {
            long ih = hh[i], il = hl[i];
            for (int j = 1; j < i; j++) {
                hh[i + j] = ih ^ hh[j];
                hl[i + j] = il ^ hl[j];
            }
        }
    }

    /** y = (y XOR x) · H in GF(2^128). */
    private void absorb(long[] y, long xh, long xl) {
        xh ^= y[0];
        xl ^= y[1];
        int b = byteAt(xh, xl, 15);
        long zh = hh[b & 0xf], zl = hl[b & 0xf];
        for (int i = 15; i >= 0; i--) {
            b = byteAt(xh, xl, i);
            int lo = b & 0xf, hi = (b >>> 4) & 0xf;
            int rem;
            if (i != 15) {
                rem = (int) (zl & 0xf);
                zl = (zh << 60) | (zl >>> 4);
                zh = (zh >>> 4) ^ (LAST4[rem] << 48);
                zh ^= hh[lo];
                zl ^= hl[lo];
            }
            rem = (int) (zl & 0xf);
            zl = (zh << 60) | (zl >>> 4);
            zh = (zh >>> 4) ^ (LAST4[rem] << 48);
            zh ^= hh[hi];
            zl ^= hl[hi];
        }
        y[0] = zh;
        y[1] = zl;
    }

    private static int byteAt(long h, long l, int i) {
        return i < 8 ? (int) (h >>> (56 - 8 * i)) & 0xff : (int) (l >>> (56 - 8 * (i - 8))) & 0xff;
    }

    private static long be64(byte[] b, int off) {
        long v = 0;
        for (int i = 0; i < 8; i++) v = (v << 8) | (b[off + i] & 0xff);
        return v;
    }

    private static void put64(byte[] b, int off, long v) {
        for (int i = 7; i >= 0; i--) {
            b[off + i] = (byte) v;
            v >>>= 8;
        }
    }
}
