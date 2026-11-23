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
 * The user's 32-byte backup root key, wrapped by an Android Keystore AES key (plan § 3.8, P4).
 *
 * The probe's vault (ProbeKeyVault) moved to the shipped app as a new class: its own folder
 * (no_backup/wa_key/, out of the nightly sweep's reach) and its own Keystore alias, so the probe
 * build — which carries both — can never delete this key by removing its own. A key the probe
 * stored is not migrated: the user enters it once here.
 *
 * The Keystore key never leaves secure hardware. No user-authentication binding: the nightly
 * read runs unattended. {@link DeviceTokenVault} seals the device token the same way, under a
 * separate alias.
 */
final class KeyVault {
    private static final String ALIAS = "metatron_wa_backup_key_wrap";
    private static final String FILE = "backup_key.bin";

    private KeyVault() {}

    static boolean present(Context ctx) {
        return file(ctx).isFile();
    }

    /** Seals the root key. The caller wipes {@code root}. */
    static void store(Context ctx, byte[] root) throws Exception {
        seal(ALIAS, file(ctx), root);
    }

    /** The root key, or null when none is stored. The caller wipes it. */
    static byte[] load(Context ctx) throws Exception {
        return open(ALIAS, file(ctx));
    }

    /** The derived backup key, or null when none is stored; the root key is wiped here. */
    static BackupKey loadKey(Context ctx) throws Exception {
        byte[] root = load(ctx);
        if (root == null) return null;
        try {
            return BackupKey.fromRoot(root);
        } finally {
            Arrays.fill(root, (byte) 0);
        }
    }

    /** "Remove key" and "Turn off": the sealed file and the Keystore key that opens it. */
    static void delete(Context ctx) throws Exception {
        remove(ALIAS, file(ctx));
    }

    private static File file(Context ctx) {
        return new File(WaFiles.keyDir(ctx), FILE);
    }

    // ---- shared sealing, also used by DeviceTokenVault -----------------------------------------

    static void seal(String alias, File f, byte[] plain) throws Exception {
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.ENCRYPT_MODE, wrappingKey(alias));
        byte[] iv = c.getIV();
        byte[] sealed = c.doFinal(plain);
        byte[] blob = new byte[1 + iv.length + sealed.length];
        blob[0] = (byte) iv.length;
        System.arraycopy(iv, 0, blob, 1, iv.length);
        System.arraycopy(sealed, 0, blob, 1 + iv.length, sealed.length);
        File tmp = new File(f.getPath() + ".tmp");
        try (FileOutputStream o = new FileOutputStream(tmp)) {
            o.write(blob);
            o.getFD().sync();
        }
        if (!tmp.renameTo(f)) {
            tmp.delete();
            throw new IOException("could not store");
        }
    }

    static byte[] open(String alias, File f) throws Exception {
        if (!f.isFile()) return null;
        byte[] blob = new byte[(int) f.length()];
        try (FileInputStream in = new FileInputStream(f)) {
            int n = 0, r;
            while (n < blob.length && (r = in.read(blob, n, blob.length - n)) > 0) n += r;
            if (n != blob.length) throw new IOException("short read");
        }
        int ivLen = blob[0] & 0xff;
        Cipher c = Cipher.getInstance("AES/GCM/NoPadding");
        c.init(Cipher.DECRYPT_MODE, wrappingKey(alias),
                new GCMParameterSpec(128, Arrays.copyOfRange(blob, 1, 1 + ivLen)));
        return c.doFinal(blob, 1 + ivLen, blob.length - 1 - ivLen);
    }

    static void remove(String alias, File f) throws Exception {
        f.delete();
        new File(f.getPath() + ".tmp").delete();
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(alias)) ks.deleteEntry(alias);
    }

    private static SecretKey wrappingKey(String alias) throws Exception {
        KeyStore ks = KeyStore.getInstance("AndroidKeyStore");
        ks.load(null);
        if (ks.containsAlias(alias)) return (SecretKey) ks.getKey(alias, null);
        KeyGenerator g = KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore");
        g.init(new KeyGenParameterSpec.Builder(alias, KeyProperties.PURPOSE_ENCRYPT | KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM)
                .setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE)
                .setKeySize(256)
                .build());
        return g.generateKey();
    }
}
