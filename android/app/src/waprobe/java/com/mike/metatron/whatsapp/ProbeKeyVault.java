package com.mike.metatron.whatsapp;

import android.content.Context;
import android.security.keystore.KeyGenParameterSpec;
import android.security.keystore.KeyProperties;

import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.security.KeyStore;
import java.util.Arrays;

import javax.crypto.Cipher;
import javax.crypto.KeyGenerator;
import javax.crypto.SecretKey;
import javax.crypto.spec.GCMParameterSpec;

/**
 * The user's 32-byte backup root key, wrapped by an Android Keystore AES key (plan P4).
 *
 * The wrapped blob lives in no_backup/, which Android's auto-backup never copies, and the
 * manifest's allowBackup is false as a second lock. The Keystore key itself never leaves
 * secure hardware. No user-authentication binding: the nightly reader (P3) runs unattended.
 */
final class ProbeKeyVault {
    private static final String ALIAS = "metatron_whatsapp_backup_key_wrap";
    private static final String FILE = "wa_key.bin";

    private ProbeKeyVault() {}

    static boolean present(Context ctx) {
        return file(ctx).isFile();
    }

    static void store(Context ctx, byte[] root) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, wrappingKey());
        byte[] iv = c.getIV();
        byte[] sealed = c.doFinal(root);
        byte[] blob = new byte[1 + iv.length + sealed.length];
        blob[0] = (byte) iv.length;
        System.arraycopy(iv, 0, blob, 1, iv.length);
        System.arraycopy(sealed, 0, blob, 1 + iv.length, sealed.length);
        File f = file(ctx);
        File tmp = new File(f.getPath() + ".tmp");
        try (FileOutputStream o = new FileOutputStream(tmp)) {
            o.write(blob);
            o.getFD().sync();
        }
        if (!tmp.renameTo(f)) {
            tmp.delete();
            throw new IOException("could not store the key");
        }
    }

    /** The root key, or null when none is stored. The caller wipes it. */
    static byte[] load(Context ctx) throws Exception {
        File f = file(ctx);
        if (!f.isFile()) return null;
        byte[] blob = new byte[(int) f.length()];
        try (FileInputStream in = new FileInputStream(f)) {
            int n = 0, r;
            while (n < blob.length && (r = in.read(blob, n, blob.length - n)) > 0) n += r;
            if (n != blob.length) throw new IOException("short read");
        }
        int ivLen = blob[0] & 0xff;
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, wrappingKey(), new GCMParameterSpec(128, Arrays.copyOfRange(blob, 1, 1 + ivLen)));
        return c.doFinal(blob, 1 + ivLen, blob.length - 1 - ivLen);
    }

    static void delete(Context ctx) throws Exception {
        file(ctx).delete();
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(ALIAS)) ks.deleteEntry(ALIAS);
    }

    private static SecretKey wrappingKey() throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(ALIAS)) return (SecretKey) ks.getKey(ALIAS, null);
        KeyGenerator g = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        g.init(new KeyGenParameterSpec.Builder(ALIAS, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return g.generateKey();
    }

    private static File file(Context ctx) {
        File dir = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        dir.mkdirs();
        return new File(dir, FILE);
    }
}
