package com.mike.metatron.whatsapp;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

/**
 * After a reboot (plan § 3.2): make sure the nightly job is scheduled. The job is persisted, so
 * this is the second lock — {@link NightlyJob#ensureScheduled} schedules nothing when one is
 * pending, or when the gate and the user's grants do not allow a job. Not exported: only the
 * system's BOOT_COMPLETED reaches it.
 */
public class WaBootReceiver extends BroadcastReceiver {
    @Override
    public void onReceive(Context context, Intent intent) {
        if (intent == null || !Intent.ACTION_BOOT_COMPLETED.equals(intent.getAction())) return;
        final PendingResult pending = goAsync();
        final Context app = context.getApplicationContext();
        new Thread(() -> {
            try {
                NightlyJob.ensureScheduled(app);
            } catch (RuntimeException ignored) {
                // the app-open rule schedules it next time
            } finally {
                pending.finish();
            }
        }, "metatron-wa-boot").start();
    }
}
