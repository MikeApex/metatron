package com.mike.metatron.whatsapp;

import android.content.Context;

/**
 * What the WhatsApp link does at every process start (plan § 3.1 (a)), from MetatronApp.onCreate:
 * on a background thread, sweep the nightly read's work folder if no run holds it — so a run
 * killed after its decrypt never leaves a decrypted copy behind — then make sure the nightly job
 * is scheduled, which {@link NightlyJob#ensureScheduled} does only when the gate state and the
 * user's grants already allow it. Returns at once.
 */
public final class WaProcessStart {
    private WaProcessStart() {}

    public static void run(Context ctx) {
        final Context app = ctx.getApplicationContext();
        Thread t = new Thread(() -> {
            WorkFolder.sweepIfIdle(WaFiles.workDir(app), WaFiles.workLock(app));
            try {
                NightlyJob.ensureScheduled(app);
            } catch (RuntimeException ignored) {
                // the next app open, boot or screen visit schedules it
            }
        }, "metatron-wa-start");
        t.start();
    }
}
