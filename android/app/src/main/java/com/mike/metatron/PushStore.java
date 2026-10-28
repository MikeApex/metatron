package com.mike.metatron;

import android.content.Context;
import android.content.SharedPreferences;

import org.json.JSONObject;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

/**
 * What the native push code needs when the page is not running: the server, the sign-in
 * token and this phone's FCM token — plus a tiny HTTP client that carries the token.
 *
 * The page hands the server and sign-in token over through window.Metatron.setPushAuth
 * (MainActivity). They are the same values the page already keeps in localStorage, so this is
 * a second copy of an existing secret, not a new one; clearPushAuth removes it on sign-out.
 *
 * Why native at all (day planner Stage C, 2026-10-28): a data-only FCM message that arrives
 * while the app is killed is handled only by a FirebaseMessagingService — the page is not
 * running. The ping carries a message id and nothing else; the text is fetched from the VM
 * here, over the signed-in channel, so it never travels through Google.
 */
final class PushStore {
    private static final String PREFS = "metatron_push";
    private static final int TIMEOUT_MS = 8000;

    private PushStore() {}

    private static SharedPreferences prefs(Context c) {
        return c.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    static void setAuth(Context c, String server, String token, String persona) {
        prefs(c).edit().putString("server", server).putString("token", token)
                .putString("persona", persona).apply();
    }

    static void clearAuth(Context c) {
        prefs(c).edit().remove("server").remove("token").remove("persona")
                .remove("registered").apply();
    }

    static boolean signedIn(Context c) {
        return !str(c, "server").isEmpty() && !str(c, "token").isEmpty();
    }

    static void setFcmToken(Context c, String t) {
        prefs(c).edit().putString("fcm", t).apply();
    }

    static String fcmToken(Context c) {
        return str(c, "fcm");
    }

    /** The task list behind one shown notification, so a button can move to the next task. */
    static void putPending(Context c, int nid, JSONObject pending) {
        prefs(c).edit().putString("pending_" + nid, pending.toString()).apply();
    }

    static JSONObject pending(Context c, int nid) {
        try {
            String s = str(c, "pending_" + nid);
            return s.isEmpty() ? null : new JSONObject(s);
        } catch (Exception e) {
            return null;
        }
    }

    static void removePending(Context c, int nid) {
        prefs(c).edit().remove("pending_" + nid).apply();
    }

    private static String str(Context c, String key) {
        String v = prefs(c).getString(key, "");
        return v == null ? "" : v;
    }

    /**
     * Register this phone's FCM token for the signed-in persona. The server binds it to the
     * persona of the sign-in token, never one this request names. Blocking — call off the
     * main thread. Re-registering the same pair is harmless, so it is not de-duplicated.
     */
    static void registerToken(Context c) {
        String fcm = fcmToken(c);
        if (fcm.isEmpty() || !signedIn(c)) return;
        try {
            JSONObject body = new JSONObject().put("token", fcm);
            String failure = str(c, "last_fetch_failure");
            if (!failure.isEmpty()) body.put("last_error", failure);
            Result r = request(c, "POST", "/push/fcm/register", body);
            if (r.status == 200) {
                prefs(c).edit().putString("registered", fcm).remove("last_fetch_failure").apply();
            }
        } catch (Exception ignored) {
            // The next app start or token refresh registers again.
        }
    }

    /**
     * Why a pushed message could not be fetched — content-free: a reason ("HTTP 401",
     * "SocketTimeoutException"), the first 8 characters of the message id and the time. Reported
     * with the next registration, which every app start makes, and cleared once the VM has it.
     */
    static void noteFetchFailure(Context c, String reason, String msgId) {
        String id8 = msgId == null ? "" : msgId.substring(0, Math.min(8, msgId.length()));
        String at = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss", java.util.Locale.UK)
                .format(new java.util.Date());
        prefs(c).edit().putString("last_fetch_failure", reason + "|" + id8 + "|" + at).apply();
    }

    /**
     * Sign-out: forget the sign-in at once, then tell the server with a captured copy. Cleared
     * first so a quick sign-in as someone else cannot be wiped by this call returning late.
     */
    static void unregisterAndClear(Context c) {
        String fcm = fcmToken(c), server = str(c, "server"), token = str(c, "token");
        clearAuth(c);
        try {
            if (!fcm.isEmpty() && !server.isEmpty() && !token.isEmpty()) {
                request(server, token, "POST", "/push/fcm/unregister",
                        new JSONObject().put("token", fcm));
            }
        } catch (Exception ignored) {
            // The token stays registered server-side until FCM reports it dead or the
            // phone signs in as someone else, which moves it.
        }
    }

    static final class Result {
        final int status;
        final String body;
        Result(int status, String body) { this.status = status; this.body = body; }
        JSONObject json() {
            try { return new JSONObject(body); } catch (Exception e) { return null; }
        }
    }

    /** One authenticated request to the VM. Blocking; never on the main thread. */
    static Result request(Context c, String method, String path, JSONObject body) throws Exception {
        return request(str(c, "server"), str(c, "token"), method, path, body);
    }

    private static Result request(String server, String token, String method, String path,
                                  JSONObject body) throws Exception {
        while (server.endsWith("/")) server = server.substring(0, server.length() - 1);
        HttpURLConnection conn = (HttpURLConnection) new URL(server + path).openConnection();
        conn.setRequestMethod(method);
        conn.setConnectTimeout(TIMEOUT_MS);
        conn.setReadTimeout(TIMEOUT_MS);
        conn.setRequestProperty("Authorization", "Bearer " + token);
        conn.setRequestProperty("Accept", "application/json");
        try {
            if (body != null) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(body.toString().getBytes(StandardCharsets.UTF_8));
                }
            }
            int status = conn.getResponseCode();
            InputStream in = status < 400 ? conn.getInputStream() : conn.getErrorStream();
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            if (in != null) {
                byte[] buf = new byte[4096];
                int n;
                while ((n = in.read(buf)) > 0) out.write(buf, 0, n);
                in.close();
            }
            return new Result(status, out.toString("UTF-8"));
        } finally {
            conn.disconnect();
        }
    }
}
