package com.mike.metatron;

import android.app.Application;

import com.mike.metatron.whatsapp.WaProcessStart;

/**
 * The app's process start. It exists for one thing (WhatsApp plan § 3.1): sweeping the nightly
 * read's work folder at every process start, so a run killed after its decrypt never leaves a
 * decrypted copy behind. Keep it light — it runs before every screen, service and receiver.
 */
public class MetatronApp extends Application {
    @Override
    public void onCreate() {
        super.onCreate();
        WaProcessStart.run(this);
    }
}
