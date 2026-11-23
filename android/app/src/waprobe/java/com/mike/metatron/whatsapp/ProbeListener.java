package com.mike.metatron.whatsapp;

import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

/**
 * Phase 0 listener probe (plan P2): records the shape of every WhatsApp notification —
 * identifiers, times, text LENGTHS — and nothing else. Never reads the text out, never
 * sends anything, never touches another app's notifications.
 */
public class ProbeListener extends NotificationListenerService {
    static final String WHATSAPP = "com.whatsapp";

    @Override
    public void onListenerConnected() {
        ProbeStore.mark(this, "connected");
    }

    @Override
    public void onListenerDisconnected() {
        ProbeStore.mark(this, "disconnected");
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        long rx = System.currentTimeMillis(); // receipt time — first, before any work (survival test)
        if (!WHATSAPP.equals(sbn.getPackageName())) return;
        try {
            ProbeStore.record(this, sbn, rx);
        } catch (Throwable t) {
            // Counted, not logged: a stack trace could carry notification content.
            ProbeStore.countError(this);
        }
    }
}
