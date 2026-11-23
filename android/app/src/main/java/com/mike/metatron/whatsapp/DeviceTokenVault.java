package com.mike.metatron.whatsapp;

import android.content.Context;

import java.io.File;
import java.nio.charset.StandardCharsets;
import java.util.Arrays;

/**
 * This phone's device token for /device/* (plan § 3.8, P5), sealed like the backup key but
 * under its own Keystore alias, so removing the key never unpairs the phone and unpairing
 * never touches the key.
 *
 * The token arrives from POST /whatsapp/device/pair in native code and goes only into
 * DeviceClient's Authorization header: it is never shown on a screen and never handed to the
 * page.
 */
final class DeviceTokenVault {
    private static final String ALIAS = "metatron_wa_device_token_wrap";
    private static final String FILE = "device_token.bin";

    private DeviceTokenVault() {}

    static boolean present(Context ctx) {
        return file(ctx).isFile();
    }

    static void store(Context ctx, String token) throws Exception {
        byte[] b = token.getBytes(StandardCharsets.UTF_8);
        try {
            KeyVault.seal(ALIAS, file(ctx), b);
        } finally {
            Arrays.fill(b, (byte) 0);
        }
    }

    /** The token, or null when none is stored or it cannot be opened. */
    static String load(Context ctx) {
        try {
            byte[] b = KeyVault.open(ALIAS, file(ctx));
            if (b == null) return null;
            try {
                return new String(b, StandardCharsets.UTF_8);
            } finally {
                Arrays.fill(b, (byte) 0);
            }
        } catch (Exception e) {
            return null;
        }
    }

    static void delete(Context ctx) throws Exception {
        KeyVault.remove(ALIAS, file(ctx));
    }

    private static File file(Context ctx) {
        return new File(WaFiles.keyDir(ctx), FILE);
    }
}
