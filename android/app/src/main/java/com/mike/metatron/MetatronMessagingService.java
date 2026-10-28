package com.mike.metatron;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

import org.json.JSONObject;

import java.net.URLEncoder;

/**
 * Receives the VM's FCM ping — with the app open, in the background, or killed.
 *
 * The ping is data-only and carries `m`, a random message id, and nothing else (core/push.py).
 * This fetches the text from the VM over the signed-in channel and shows it. If the fetch fails
 * — the phone is off Tailscale, or the sign-in expired — it shows a content-free notification
 * that opens the app, rather than nothing: a nudge that silently vanishes is the failure this
 * whole channel exists to remove.
 *
 * onMessageReceived already runs off the main thread, so the fetch can block here (FCM allows
 * a high-priority message about ten seconds; PushStore's timeouts are eight).
 */
public class MetatronMessagingService extends FirebaseMessagingService {

    @Override
    public void onNewToken(String token) {
        PushStore.setFcmToken(this, token);
        PushStore.registerToken(this);
    }

    @Override
    public void onMessageReceived(RemoteMessage message) {
        String id = message.getData().get("m");
        if (id == null || id.isEmpty()) return;
        int nid = PushNotifications.idFor(id);
        JSONObject msg = null;
        if (PushStore.signedIn(this)) {
            try {
                PushStore.Result r = PushStore.request(
                        this, "GET", "/push/message/" + URLEncoder.encode(id, "UTF-8"), null);
                if (r.status == 200) msg = r.json();
            } catch (Exception ignored) {
                // Falls through to the content-free notification.
            }
        }
        if (msg == null) {
            PushNotifications.showFallback(this, nid);
            return;
        }
        PushNotifications.showMessage(this, nid, msg);
    }
}
