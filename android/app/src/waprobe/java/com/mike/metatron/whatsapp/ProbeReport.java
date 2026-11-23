package com.mike.metatron.whatsapp;

import android.app.ActivityManager;
import android.content.Context;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.os.Build;
import android.os.Environment;
import android.os.PowerManager;
import android.os.StatFs;

import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Collections;
import java.util.Date;
import java.util.HashMap;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.TimeZone;

/**
 * The listener, survival and device sections of the probe screen. Counts and formats only:
 * identifiers pass through {@link ProbeMask}, text appears only as a length.
 */
final class ProbeReport {
    private ProbeReport() {}

    static String listener(Context ctx) {
        List<ProbeStore.Event> events = ProbeStore.load(ctx);
        StringBuilder b = new StringBuilder("== LIVE NOTIFICATIONS (last 72 h) ==\n");
        int errors = ProbeStore.errors(ctx);
        if (events.isEmpty()) {
            return b.append("none recorded yet").append(errors > 0 ? " — listener errors: " + errors : "").append('\n').toString();
        }

        int style = 0, groupStyle = 0, summary = 0, convTitle = 0;
        Map<String, Integer> sc = new HashMap<>(), lo = new HashMap<>(), tag = new HashMap<>(), ch = new HashMap<>();
        Map<String, Integer> pkGroup = new HashMap<>(), pk1to1 = new HashMap<>(), pu = new HashMap<>();
        int personNamed = 0, personTotal = 0, withTime = 0;
        Map<String, int[]> seen = new LinkedHashMap<>(); // chat|t -> {firstLen, lastLen, group}
        for (ProbeStore.Event e : events) {
            if (e.style) style++;
            if (e.style && e.group) groupStyle++;
            if (e.summary) summary++;
            if (e.convTitle) convTitle++;
            bump(sc, ProbeMask.format(e.shortcut));
            bump(lo, ProbeMask.format(e.locus));
            bump(tag, ProbeMask.format(e.tag));
            bump(ch, e.channel == null ? "(none)" : e.channel.replaceAll("[0-9]", "#"));
            for (ProbeStore.Msg m : e.msgs) {
                personTotal++;
                bump(e.group ? pkGroup : pk1to1, ProbeMask.format(m.personKey));
                if (m.personUriFormat != null) bump(pu, m.personUriFormat);
                if (m.personName) personNamed++;
                if (m.t > 0) withTime++;
                String k = e.chatId() + "|" + m.t;
                int[] v = seen.get(k);
                if (v == null) seen.put(k, new int[]{m.len, m.len, e.group ? 1 : 0});
                else v[1] = m.len;
            }
        }
        int edited = 0, groupMsgs = 0;
        List<Integer> lens = new ArrayList<>();
        for (int[] v : seen.values()) {
            if (v[0] != v[1]) edited++;
            if (v[2] == 1) groupMsgs++;
            if (v[1] >= 0) lens.add(v[1]);
        }
        Collections.sort(lens);

        b.append("notifications posted: ").append(events.size())
                .append("  (messaging-style ").append(style).append(", of which group ").append(groupStyle)
                .append("; group summaries ").append(summary).append("; with conversation title ").append(convTitle).append(")\n");
        b.append("distinct messages: ").append(seen.size()).append("  (group ").append(groupMsgs)
                .append(", one-to-one ").append(seen.size() - groupMsgs).append("; with a message time ")
                .append(withTime).append(" of ").append(personTotal).append(" entries)\n");
        b.append("text length min/median/max: ").append(lens.isEmpty() ? "-" :
                lens.get(0) + " / " + lens.get(lens.size() / 2) + " / " + lens.get(lens.size() - 1)).append('\n');
        b.append("same message re-posted with a different length (edit or trim seen live): ").append(edited).append('\n');
        // Chat-ID fields split by notification kind: a summary's IDs are not a message's (Phase 0, 10-30).
        Map<String, Map<String, Integer>> scByKind = new LinkedHashMap<>(), tagByKind = new LinkedHashMap<>();
        Map<String, Integer> kinds = new LinkedHashMap<>();
        for (ProbeStore.Event e : events) {
            String kind = e.summary ? "summary" : e.style ? (e.group ? "group message" : "one-to-one message") : "other";
            bump(kinds, kind);
            if (!scByKind.containsKey(kind)) { scByKind.put(kind, new HashMap<>()); tagByKind.put(kind, new HashMap<>()); }
            bump(scByKind.get(kind), ProbeMask.format(e.shortcut));
            bump(tagByKind.get(kind), ProbeMask.format(e.tag));
        }
        b.append("\nCHAT-ID FIELDS BY NOTIFICATION KIND:\n");
        for (Map.Entry<String, Integer> k : kinds.entrySet()) {
            b.append("[").append(k.getKey()).append(": ").append(k.getValue()).append("]\n");
            b.append(" shortcut:\n").append(top(scByKind.get(k.getKey())));
            b.append(" tag:\n").append(top(tagByKind.get(k.getKey())));
        }
        b.append("\nshortcut ID formats (all kinds):\n").append(top(sc));
        b.append("locus ID formats:\n").append(top(lo));
        b.append("tag formats (all kinds):\n").append(top(tag));
        b.append("channel IDs (digits masked):\n").append(top(ch));
        b.append("person key formats — group messages:\n").append(top(pkGroup));
        b.append("person key formats — one-to-one messages:\n").append(top(pk1to1));
        b.append("person URI formats:\n").append(top(pu));
        b.append("person has a display name: ").append(personNamed).append(" of ").append(personTotal).append('\n');
        if (errors > 0) b.append("listener errors (counted, not logged): ").append(errors).append('\n');
        return b.toString();
    }

    static String survival(Context ctx) {
        long now = System.currentTimeMillis();
        StringBuilder b = new StringBuilder("== SURVIVAL ==\n");
        b.append("now: ").append(ts(now)).append('\n');
        b.append("listener connected at: ").append(list(ProbeStore.marks(ctx, "connected"))).append('\n');
        b.append("listener disconnected at: ").append(list(ProbeStore.marks(ctx, "disconnected"))).append('\n');
        List<ProbeStore.Event> events = ProbeStore.load(ctx);
        if (events.isEmpty()) return b.append("no events yet\n").toString();
        long last = 0;
        long[] posts = new long[events.size()];
        for (int i = 0; i < posts.length; i++) posts[i] = events.get(i).post;
        java.util.Arrays.sort(posts);
        last = posts[posts.length - 1];
        b.append("first event: ").append(ts(posts[0])).append("   last event: ").append(ts(last))
                .append("  (").append((now - last) / 60000).append(" min ago)\n");
        long gap = 0, gapAt = 0;
        for (int i = 1; i < posts.length; i++) {
            if (posts[i] - posts[i - 1] > gap) { gap = posts[i] - posts[i - 1]; gapAt = posts[i - 1]; }
        }
        b.append("longest gap between events: ").append(gap / 60000).append(" min, from ").append(ts(gapAt)).append('\n');
        b.append("events per hour, last 48 h (oldest first):\n");
        int[] hours = new int[48];
        for (long p : posts) {
            long h = (now - p) / 3_600_000L;
            if (h >= 0 && h < 48) hours[47 - (int) h]++;
        }
        for (int i = 0; i < 48; i++) b.append(hours[i]).append(i % 12 == 11 ? "\n" : " ");
        return b.toString();
    }

    /**
     * Every event of the last 72 h, newest first, one line each (survival test, item 2): when
     * WhatsApp posted it, when the listener heard it, the gap, its kind and a MASKED chat id.
     * Times and masked ids only — no names, no text, no lengths.
     */
    static String events(Context ctx) {
        List<ProbeStore.Event> events = new ArrayList<>(ProbeStore.load(ctx));
        StringBuilder b = new StringBuilder("== EVENTS, last 72 h (newest first; rx = when the listener heard it) ==\n");
        if (events.isEmpty()) return b.append("none recorded yet\n").toString();
        Collections.sort(events, (x, y) -> Long.compare(y.post, x.post));
        TimeZone tz = TimeZone.getDefault();
        String day = null;
        for (ProbeStore.Event e : events) {
            String d = ProbeLines.day(e.post, tz);
            if (!d.equals(day)) {
                b.append("-- ").append(d).append(" --\n");
                day = d;
            }
            b.append(ProbeLines.eventLine(e.post, e.rx, ProbeLines.kind(e.summary, e.style, e.group),
                    ProbeMask.format(e.chatId()), tz)).append('\n');
        }
        return b.toString();
    }

    static String device(Context ctx) {
        StringBuilder b = new StringBuilder("== DEVICE (checkpoint LM) ==\n");
        b.append("model: ").append(Build.MANUFACTURER).append(' ').append(Build.MODEL);
        if (Build.VERSION.SDK_INT >= 31) b.append("   SoC: ").append(Build.SOC_MANUFACTURER).append(' ').append(Build.SOC_MODEL);
        b.append('\n');
        b.append("Android: ").append(Build.VERSION.RELEASE).append(" (API ").append(Build.VERSION.SDK_INT)
                .append("), security patch ").append(Build.VERSION.SECURITY_PATCH).append('\n');
        ActivityManager am = (ActivityManager) ctx.getSystemService(Context.ACTIVITY_SERVICE);
        ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
        am.getMemoryInfo(mi);
        b.append("RAM: ").append(gb(mi.totalMem)).append(" total, ").append(gb(mi.availMem)).append(" available\n");
        StatFs fs = new StatFs(Environment.getDataDirectory().getPath());
        b.append("storage: ").append(gb(fs.getAvailableBytes())).append(" free of ").append(gb(fs.getTotalBytes())).append('\n');
        b.append("AICore: ").append(pkg(ctx, "com.google.android.aicore")).append('\n');
        b.append("WhatsApp: ").append(pkg(ctx, "com.whatsapp")).append('\n');
        PowerManager pm = (PowerManager) ctx.getSystemService(Context.POWER_SERVICE);
        b.append("battery optimisation for this app: ")
                .append(pm.isIgnoringBatteryOptimizations(ctx.getPackageName()) ? "OFF (unrestricted)" : "ON (default)").append('\n');
        return b.toString();
    }

    private static String pkg(Context ctx, String name) {
        try {
            PackageInfo pi = ctx.getPackageManager().getPackageInfo(name, 0);
            return "installed, version " + pi.versionName + (pi.applicationInfo != null && !pi.applicationInfo.enabled ? " (DISABLED)" : "");
        } catch (PackageManager.NameNotFoundException e) {
            return "not installed";
        }
    }

    static void bump(Map<String, Integer> m, String k) {
        Integer v = m.get(k);
        m.put(k, v == null ? 1 : v + 1);
    }

    static String top(Map<String, Integer> m) {
        List<Map.Entry<String, Integer>> l = new ArrayList<>(m.entrySet());
        Collections.sort(l, (x, y) -> y.getValue() - x.getValue());
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < Math.min(8, l.size()); i++) {
            b.append("  ").append(l.get(i).getValue()).append(" × ").append(l.get(i).getKey()).append('\n');
        }
        if (l.size() > 8) b.append("  … ").append(l.size() - 8).append(" more formats\n");
        if (l.isEmpty()) b.append("  (none)\n");
        return b.toString();
    }

    static String ts(long t) {
        return new SimpleDateFormat("MM-dd HH:mm", Locale.US).format(new Date(t));
    }

    private static String list(long[] marks) {
        if (marks.length == 0) return "never";
        StringBuilder b = new StringBuilder();
        for (int i = 0; i < marks.length; i++) b.append(i == 0 ? "" : ", ").append(ts(marks[i]));
        return b.toString();
    }

    static String gb(long bytes) {
        return String.format(Locale.US, "%.1f GB", bytes / 1e9);
    }
}
