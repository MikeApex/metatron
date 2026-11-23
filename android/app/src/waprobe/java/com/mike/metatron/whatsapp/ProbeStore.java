package com.mike.metatron.whatsapp;

import android.app.Notification;
import android.content.Context;
import android.content.SharedPreferences;
import android.os.Build;
import android.service.notification.StatusBarNotification;

import androidx.core.app.NotificationCompat;
import androidx.core.app.Person;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;

/**
 * What the listener saw, kept on the phone for 72 hours (plan P2's private sent-key list).
 *
 * Holds identifiers raw — the backup probe has to look them up in the decrypted database —
 * but **never message text**: only its length. Lives in no_backup/, is never sent anywhere,
 * and the report shows identifiers only through {@link ProbeMask}.
 */
final class ProbeStore {
    static final long KEEP_MS = 72L * 3600 * 1000;
    private static final String PREFS = "wa_probe";

    private ProbeStore() {}

    /** One message inside a notification. */
    static final class Msg {
        long t;
        int len;
        String personKey;
        String personUriFormat;
        boolean personName;
    }

    /** One posted WhatsApp notification. */
    static final class Event {
        long post, when;
        /** When the listener heard it (System.currentTimeMillis()); ProbeLines.UNKNOWN for events recorded before rx existed. */
        long rx = ProbeLines.UNKNOWN;
        String shortcut, locus, tag, channel;
        boolean group, style, summary, convTitle;
        int textLen = -1;
        final List<Msg> msgs = new ArrayList<>();

        /** The best chat-ID candidate, in the order the plan expects them (P2: the shortcut first). */
        String chatId() {
            if (shortcut != null && !shortcut.isEmpty()) return shortcut;
            if (locus != null && !locus.isEmpty()) return locus;
            return tag;
        }
    }

    /** @param rx receipt time, taken first thing in onNotificationPosted — post is WhatsApp's time, not ours. */
    static void record(Context ctx, StatusBarNotification sbn, long rx) throws Exception {
        Notification n = sbn.getNotification();
        Event e = new Event();
        e.post = sbn.getPostTime();
        e.rx = rx;
        e.when = n.when;
        e.tag = sbn.getTag();
        if (Build.VERSION.SDK_INT >= 26) {
            e.shortcut = n.getShortcutId();
            e.channel = n.getChannelId();
        }
        if (Build.VERSION.SDK_INT >= 29 && n.getLocusId() != null) e.locus = n.getLocusId().getId();
        e.summary = (n.flags & Notification.FLAG_GROUP_SUMMARY) != 0;
        NotificationCompat.MessagingStyle style =
                NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(n);
        if (style != null) {
            e.style = true;
            e.group = style.isGroupConversation();
            e.convTitle = style.getConversationTitle() != null;
            for (NotificationCompat.MessagingStyle.Message m : style.getMessages()) {
                Msg x = new Msg();
                x.t = m.getTimestamp();
                // Code points, not UTF-16 units: SQLite's length() counts characters, so an
                // emoji would otherwise read as a length mismatch in the dedup comparison.
                CharSequence text = m.getText();
                x.len = text == null ? -1 : Character.codePointCount(text, 0, text.length());
                Person p = m.getPerson();
                if (p != null) {
                    x.personKey = p.getKey();
                    x.personUriFormat = p.getUri() == null ? null : ProbeMask.format(p.getUri());
                    x.personName = p.getName() != null;
                }
                e.msgs.add(x);
            }
        } else {
            CharSequence text = n.extras.getCharSequence(Notification.EXTRA_TEXT);
            e.textLen = text == null ? -1 : text.length();
        }
        append(ctx, toJson(e));
    }

    static synchronized List<Event> load(Context ctx) {
        List<Event> out = new ArrayList<>();
        File f = file(ctx);
        if (!f.isFile()) return out;
        long cutoff = System.currentTimeMillis() - KEEP_MS;
        boolean pruned = false;
        List<String> kept = new ArrayList<>();
        try (BufferedReader r = new BufferedReader(new FileReader(f))) {
            String line;
            while ((line = r.readLine()) != null) {
                try {
                    Event e = fromJson(new JSONObject(line));
                    if (e.post < cutoff) { pruned = true; continue; }
                    out.add(e);
                    kept.add(line);
                } catch (Exception bad) {
                    pruned = true;
                }
            }
        } catch (IOException ignored) {
            return out;
        }
        if (pruned) rewrite(ctx, kept);
        return out;
    }

    // ---- listener lifecycle, for the survival probe -------------------------------------

    static void mark(Context ctx, String what) {
        SharedPreferences p = prefs(ctx);
        String prev = p.getString(what, "");
        String next = System.currentTimeMillis() + (prev.isEmpty() ? "" : "," + prev);
        String[] parts = next.split(",");
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < Math.min(10, parts.length); i++) b.append(i == 0 ? "" : ",").append(parts[i]);
        p.edit().putString(what, b.toString()).apply();
    }

    static long[] marks(Context ctx, String what) {
        String s = prefs(ctx).getString(what, "");
        if (s.isEmpty()) return new long[0];
        String[] parts = s.split(",");
        long[] out = new long[parts.length];
        for (int i = 0; i < parts.length; i++) out[i] = Long.parseLong(parts[i]);
        return out;
    }

    static void countError(Context ctx) {
        SharedPreferences p = prefs(ctx);
        p.edit().putInt("errors", p.getInt("errors", 0) + 1).apply();
    }

    static int errors(Context ctx) {
        return prefs(ctx).getInt("errors", 0);
    }

    static void saveReport(Context ctx, String report) {
        prefs(ctx).edit().putString("backup_report", report).apply();
    }

    static String savedReport(Context ctx) {
        return prefs(ctx).getString("backup_report", null);
    }

    static void saveIncrementReport(Context ctx, String report) {
        prefs(ctx).edit().putString("increment_report", report).apply();
    }

    static String savedIncrementReport(Context ctx) {
        return prefs(ctx).getString("increment_report", null);
    }

    static void saveProofReport(Context ctx, String report) {
        prefs(ctx).edit().putString("proof_report", report).apply();
    }

    static String savedProofReport(Context ctx) {
        return prefs(ctx).getString("proof_report", null);
    }

    static void saveFieldMapReport(Context ctx, String report) {
        prefs(ctx).edit().putString("fieldmap_report", report).apply();
    }

    static String savedFieldMapReport(Context ctx) {
        return prefs(ctx).getString("fieldmap_report", null);
    }

    /** Button 8's counts-only report (ProbeM2Run). */
    static void saveM2Report(Context ctx, String report) {
        prefs(ctx).edit().putString("m2_report", report).apply();
    }

    static String savedM2Report(Context ctx) {
        return prefs(ctx).getString("m2_report", null);
    }

    /** "Delete probe data": events, lifecycle marks, saved reports. The key is ProbeKeyVault's. */
    static synchronized void deleteAll(Context ctx) {
        file(ctx).delete();
        prefs(ctx).edit().clear().apply();
    }

    // ---- storage ----------------------------------------------------------------------

    private static synchronized void append(Context ctx, JSONObject o) throws IOException {
        try (FileOutputStream out = new FileOutputStream(file(ctx), true)) {
            out.write((o.toString() + "\n").getBytes(StandardCharsets.UTF_8));
        }
    }

    private static void rewrite(Context ctx, List<String> lines) {
        File f = file(ctx);
        File tmp = new File(f.getPath() + ".tmp");
        try (FileOutputStream out = new FileOutputStream(tmp)) {
            for (String l : lines) out.write((l + "\n").getBytes(StandardCharsets.UTF_8));
        } catch (IOException e) {
            tmp.delete();
            return;
        }
        tmp.renameTo(f);
    }

    private static JSONObject toJson(Event e) throws Exception {
        JSONObject o = new JSONObject();
        o.put("post", e.post).put("rx", e.rx).put("when", e.when)
                .put("sc", e.shortcut).put("lo", e.locus).put("tag", e.tag).put("ch", e.channel)
                .put("grp", e.group).put("ms", e.style).put("sum", e.summary).put("conv", e.convTitle)
                .put("tl", e.textLen);
        JSONArray a = new JSONArray();
        for (Msg m : e.msgs) {
            a.put(new JSONObject().put("t", m.t).put("l", m.len).put("pk", m.personKey)
                    .put("pu", m.personUriFormat).put("pn", m.personName));
        }
        o.put("m", a);
        return o;
    }

    private static Event fromJson(JSONObject o) throws Exception {
        Event e = new Event();
        e.post = o.getLong("post");
        e.rx = o.optLong("rx", ProbeLines.UNKNOWN);
        e.when = o.optLong("when");
        e.shortcut = opt(o, "sc");
        e.locus = opt(o, "lo");
        e.tag = opt(o, "tag");
        e.channel = opt(o, "ch");
        e.group = o.optBoolean("grp");
        e.style = o.optBoolean("ms");
        e.summary = o.optBoolean("sum");
        e.convTitle = o.optBoolean("conv");
        e.textLen = o.optInt("tl", -1);
        JSONArray a = o.optJSONArray("m");
        if (a != null) {
            for (int i = 0; i < a.length(); i++) {
                JSONObject j = a.getJSONObject(i);
                Msg m = new Msg();
                m.t = j.getLong("t");
                m.len = j.optInt("l", -1);
                m.personKey = opt(j, "pk");
                m.personUriFormat = opt(j, "pu");
                m.personName = j.optBoolean("pn");
                e.msgs.add(m);
            }
        }
        return e;
    }

    private static String opt(JSONObject o, String k) {
        return o.isNull(k) ? null : o.optString(k, null);
    }

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }

    private static File file(Context ctx) {
        File dir = new File(ctx.getNoBackupFilesDir(), "wa_probe");
        dir.mkdirs();
        return new File(dir, "live.jsonl");
    }
}
