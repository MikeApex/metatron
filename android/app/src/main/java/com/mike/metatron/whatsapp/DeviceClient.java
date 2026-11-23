package com.mike.metatron.whatsapp;

import android.content.Context;

import com.mike.metatron.PushStore;

import java.io.ByteArrayOutputStream;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Map;

/**
 * The phone's client for the VM's /device/* routes (plan § 3.8): bearer = this phone's device
 * token, server = the address the page handed PushStore.
 *
 * It refuses any server address that is not https:// before a byte is sent. The network
 * security config permits cleartext — the WebView's local mode needs it — so the guard has to
 * be here, in code, not in config. The same guard covers the two session-token calls
 * (pairing, revoking), which go through {@link PushStore#sessionPost}.
 */
public final class DeviceClient implements DeviceApi {
    static final int CONNECT_TIMEOUT_MS = 8000;
    static final int GET_READ_TIMEOUT_MS = 8000;
    /** A reply larger than this is not something the VM sends; reading stops there. */
    private static final int MAX_REPLY_BYTES = 1 << 20;

    private final Context ctx;

    public DeviceClient(Context ctx) {
        this.ctx = ctx.getApplicationContext();
    }

    @Override
    public Result get(String path) {
        return call("GET", path, null, GET_READ_TIMEOUT_MS);
    }

    @Override
    public Result post(String path, String jsonBody, int readTimeoutMs) {
        return call("POST", path, jsonBody == null ? "{}" : jsonBody, readTimeoutMs);
    }

    private Result call(String method, String path, String body, int readTimeoutMs) {
        String server = PushStore.server(ctx);
        if (!isHttps(server)) return new Result(NOT_HTTPS, "", "not_https");
        String token = DeviceTokenVault.load(ctx);
        if (token == null || token.isEmpty()) return new Result(UNPAIRED, "", "unpaired");
        return send(server, token, method, path, body, readTimeoutMs);
    }

    /**
     * One request with a bearer token. Shared with PushStore's session-token calls so both
     * read replies, and fail, the same way. Never throws: a failure is {@link #networkFailure}.
     */
    public static Result send(String server, String bearer, String method, String path,
                              String body, int readTimeoutMs) {
        if (!isHttps(server)) return new Result(NOT_HTTPS, "", "not_https");
        HttpURLConnection conn = null;
        try {
            while (server.endsWith("/")) server = server.substring(0, server.length() - 1);
            conn = (HttpURLConnection) new URL(server + path).openConnection();
            conn.setRequestMethod(method);
            conn.setConnectTimeout(CONNECT_TIMEOUT_MS);
            conn.setReadTimeout(readTimeoutMs);
            conn.setInstanceFollowRedirects(false);
            conn.setRequestProperty("Authorization", "Bearer " + bearer);
            conn.setRequestProperty("Accept", "application/json");
            if (body != null) {
                conn.setDoOutput(true);
                conn.setRequestProperty("Content-Type", "application/json");
                try (OutputStream os = conn.getOutputStream()) {
                    os.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int status = conn.getResponseCode();
            InputStream in = status < 400 ? conn.getInputStream() : conn.getErrorStream();
            String text = "";
            if (in != null) {
                try {
                    ByteArrayOutputStream out = new ByteArrayOutputStream();
                    byte[] buf = new byte[4096];
                    int n;
                    while ((n = in.read(buf)) > 0 && out.size() < MAX_REPLY_BYTES) out.write(buf, 0, n);
                    text = new String(out.toByteArray(), StandardCharsets.UTF_8);
                } finally {
                    in.close();
                }
            }
            return new Result(status, text, detailOf(text));
        } catch (Exception e) {
            return networkFailure(e);
        } finally {
            if (conn != null) conn.disconnect();
        }
    }

    // ---- plain Java, unit-tested -------------------------------------------------------------

    /** True only for an https:// address with something after the scheme (scheme case-insensitive). */
    public static boolean isHttps(String url) {
        return url != null && url.length() > 8 && url.regionMatches(true, 0, "https://", 0, 8);
    }

    /** A failed request: the exception's simple class name, never its message (§ 3.7). */
    static Result networkFailure(Exception e) {
        return new Result(NETWORK, "", e.getClass().getSimpleName());
    }

    /** The reply's JSON {"detail": "..."} string, or "" when there is none or it is not a string. */
    static String detailOf(String body) {
        if (body == null || body.isEmpty()) return "";
        try {
            Object v = Json.parse(body);
            if (v instanceof Map) {
                Object d = ((Map<?, ?>) v).get("detail");
                if (d instanceof String) return (String) d;
            }
        } catch (Json.Malformed ignored) {
            // Not JSON (a proxy's HTML error page): no detail.
        }
        return "";
    }

    /** A JSON string literal, for the few request bodies built here. */
    static String jsonString(String s) {
        StringBuilder b = new StringBuilder(s.length() + 2).append('"');
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            switch (c) {
                case '"': b.append("\\\""); break;
                case '\\': b.append("\\\\"); break;
                case '\n': b.append("\\n"); break;
                case '\r': b.append("\\r"); break;
                case '\t': b.append("\\t"); break;
                default:
                    if (c < 0x20) b.append(String.format("\\u%04x", (int) c));
                    else b.append(c);
            }
        }
        return b.append('"').toString();
    }
}
