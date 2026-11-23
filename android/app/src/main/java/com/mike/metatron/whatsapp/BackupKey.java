package com.mike.metatron.whatsapp;

import java.security.GeneralSecurityException;
import java.util.Arrays;

import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/**
 * The user's 64-digit end-to-end backup key, and the AES key derived from it.
 *
 * Format description § 2: 64 hexadecimal characters once separators are removed decode to
 * the 32-byte root key; the AES key is HKDF-SHA256 (RFC 5869) of it with a 32-byte zero
 * salt and info "backup encryption". Neither key is ever logged or put in an exception.
 */
public final class BackupKey {
    private static final byte[] INFO = "backup encryption".getBytes(java.nio.charset.StandardCharsets.US_ASCII);

    private final byte[] aesKey;

    private BackupKey(byte[] aesKey) {
        this.aesKey = aesKey;
    }

    /** Parses the key as typed and derives the backup key. The root key is wiped before returning. */
    public static BackupKey fromDigits(CharSequence typed) throws BackupException {
        byte[] root = parseRoot(typed);
        try {
            return fromRoot(root);
        } finally {
            Arrays.fill(root, (byte) 0);
        }
    }

    /** From the 32-byte root key, e.g. as unwrapped from storage. The caller wipes {@code root}. */
    static BackupKey fromRoot(byte[] root) {
        if (root.length != 32) throw new IllegalArgumentException("root key must be 32 bytes");
        try {
            return new BackupKey(hkdfSha256(new byte[32], root, INFO, 32));
        } catch (GeneralSecurityException e) {
            // HmacSHA256 is mandatory on every Java and Android platform; reaching this is
            // a broken runtime, not a bad key.
            throw new IllegalStateException("HmacSHA256 unavailable", e);
        }
    }

    /**
     * Strips whitespace and the common separators people type between digit groups, then
     * requires exactly 64 hex digits. Any other character is refused rather than skipped:
     * dropping an unexpected character could silently turn a mistyped key into a different
     * 64-digit one.
     */
    static byte[] parseRoot(CharSequence typed) throws BackupException {
        if (typed == null) throw new BackupException(BackupError.KEY_FORMAT);
        char[] hex = new char[64];
        int n = 0;
        try {
            for (int i = 0; i < typed.length(); i++) {
                char c = typed.charAt(i);
                if (Character.isWhitespace(c) || c == '-' || c == ':' || c == '_' || c == '.' || c == ',') continue;
                if (Character.digit(c, 16) < 0 || n == 64) throw new BackupException(BackupError.KEY_FORMAT);
                hex[n++] = c;
            }
            if (n != 64) throw new BackupException(BackupError.KEY_FORMAT);
            byte[] root = new byte[32];
            for (int i = 0; i < 32; i++) {
                root[i] = (byte) ((Character.digit(hex[2 * i], 16) << 4) | Character.digit(hex[2 * i + 1], 16));
            }
            return root;
        } finally {
            Arrays.fill(hex, '\0');
        }
    }

    /** RFC 5869 extract-then-expand with HMAC-SHA256. */
    static byte[] hkdfSha256(byte[] salt, byte[] ikm, byte[] info, int length) throws GeneralSecurityException {
        Mac mac = Mac.getInstance("HmacSHA256");
        mac.init(new SecretKeySpec(salt, "HmacSHA256"));
        byte[] prk = mac.doFinal(ikm);
        try {
            mac.init(new SecretKeySpec(prk, "HmacSHA256"));
            byte[] out = new byte[length];
            byte[] t = new byte[0];
            int done = 0;
            for (int i = 1; done < length; i++) {
                mac.update(t);
                mac.update(info);
                mac.update((byte) i);
                t = mac.doFinal();
                int take = Math.min(t.length, length - done);
                System.arraycopy(t, 0, out, done, take);
                done += take;
            }
            Arrays.fill(t, (byte) 0);
            return out;
        } finally {
            Arrays.fill(prk, (byte) 0);
        }
    }

    byte[] aesKey() {
        return aesKey;
    }

    /** Overwrites the derived key. The object is unusable afterwards. */
    public void destroy() {
        Arrays.fill(aesKey, (byte) 0);
    }
}
