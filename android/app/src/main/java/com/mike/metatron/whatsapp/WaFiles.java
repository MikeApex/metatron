package com.mike.metatron.whatsapp;

import android.content.Context;

import java.io.File;

/**
 * Where the WhatsApp link keeps things on the phone (Phase 2 plan § 3.1, § 3.8), and the two
 * identifiers every part of it shares.
 *
 * Everything lives under no_backup/, which Android's auto-backup never copies (the manifest's
 * allowBackup="false" is the second lock). The folders are kept apart on purpose:
 * - wa_work/  the nightly read's scratch — a decrypted copy lives here for one run, and the
 *             sweep empties the whole folder, so it must hold nothing else;
 * - wa_key/   the wrapped backup key and the wrapped device token, out of the sweep's reach;
 * - wa_state/ the share list, the sent-hash list and its salt, the last run report — all of
 *             it deleted by "Turn off WhatsApp link".
 */
public final class WaFiles {
    /** The one nightly JobScheduler job. Fixed, so scheduling again replaces rather than adds. */
    public static final int NIGHTLY_JOB_ID = 0x57410001;
    /** The single notification channel every WhatsApp-link notice is posted on. */
    public static final String NOTICE_CHANNEL = "whatsapp_link";

    private WaFiles() {}

    public static File noBackup(Context c) {
        return c.getNoBackupFilesDir();
    }

    public static File workDir(Context c) {
        return dir(c, "wa_work");
    }

    /** The file lock that keeps the nightly read to one at a time across processes. */
    public static File workLock(Context c) {
        return new File(noBackup(c), "wa_work.lock");
    }

    public static File stateDir(Context c) {
        return dir(c, "wa_state");
    }

    public static File keyDir(Context c) {
        return dir(c, "wa_key");
    }

    private static File dir(Context c, String name) {
        File d = new File(noBackup(c), name);
        d.mkdirs();
        return d;
    }
}
