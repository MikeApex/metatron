package com.mike.metatron.whatsapp;

import static org.junit.Assert.assertArrayEquals;
import static org.junit.Assert.assertFalse;

import java.util.Arrays;
import java.util.Random;

import javax.crypto.Cipher;
import javax.crypto.spec.GCMParameterSpec;
import javax.crypto.spec.SecretKeySpec;

import org.junit.Test;

/**
 * The streaming GCM against the platform's own (buffering) GCM — the platform is used here
 * only as an oracle, never at run time.
 */
public class GcmTest {
    private static final int[] LENGTHS = {0, 1, 15, 16, 17, 31, 32, 33, 4095, 4096, 4097, 70_001};

    @Test
    public void matchesPlatformGcmWithSixteenByteIv() throws Exception {
        crossCheck(16);
    }

    @Test
    public void matchesPlatformGcmWithTwelveByteIv() throws Exception {
        crossCheck(12);
    }

    @Test
    public void matchesPlatformGcmWithOddIvLength() throws Exception {
        crossCheck(20);
    }

    @Test
    public void detectsAFlippedCiphertextBit() throws Exception {
        Random rnd = new Random(7);
        byte[] key = bytes(rnd, 32), iv = bytes(rnd, 16), pt = bytes(rnd, 1000);
        byte[] sealed = seal(key, iv, pt);
        sealed[500] ^= 1;
        Gcm g = new Gcm(key, iv);
        byte[] out = new byte[1000];
        g.update(sealed, 0, 1000, out, 0);
        assertFalse(Arrays.equals(g.tag(), Arrays.copyOfRange(sealed, 1000, 1016)));
    }

    @Test
    public void inc32WrapsTheLowWordOnly() {
        byte[] b = new byte[16];
        Arrays.fill(b, (byte) 0x11);
        b[12] = b[13] = b[14] = b[15] = (byte) 0xff;
        Gcm.inc32(b);
        byte[] want = new byte[16];
        Arrays.fill(want, (byte) 0x11);
        want[12] = want[13] = want[14] = want[15] = 0;
        assertArrayEquals(want, b);
    }

    private static void crossCheck(int ivLen) throws Exception {
        Random rnd = new Random(ivLen);
        for (int len : LENGTHS) {
            for (int chunk : new int[]{1, 7, 16, 4096, Integer.MAX_VALUE}) {
                byte[] key = bytes(rnd, 32), iv = bytes(rnd, ivLen), pt = bytes(rnd, len);
                byte[] sealed = seal(key, iv, pt);
                Gcm g = new Gcm(key, iv);
                byte[] out = new byte[len];
                for (int off = 0; off < len; off += Math.min(chunk, len - off)) {
                    g.update(sealed, off, Math.min(chunk, len - off), out, off);
                }
                assertArrayEquals("plaintext len=" + len + " chunk=" + chunk, pt, out);
                assertArrayEquals("tag len=" + len + " chunk=" + chunk,
                        Arrays.copyOfRange(sealed, len, len + 16), g.tag());
            }
        }
    }

    private static byte[] seal(byte[] key, byte[] iv, byte[] pt) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, new SecretKeySpec(key, "AES"), new GCMParameterSpec(128, iv));
        return c.doFinal(pt);
    }

    private static byte[] bytes(Random rnd, int n) {
        byte[] b = new byte[n];
        rnd.nextBytes(b);
        return b;
    }
}
