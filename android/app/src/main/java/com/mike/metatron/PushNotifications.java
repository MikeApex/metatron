package com.mike.metatron;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.os.Build;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * The nudge and check-in notifications (day planner Stage C).
 *
 * A message about ledger tasks offers Done / Not yet / Skipped on ONE task at a time; acting on
 * it moves the same notification to the next task until none are left (Mike, 2026-10-28).
 * "Not yet" turns the notification into "remind me in …" with the durations the server sent —
 * none of which lands after the user's bedtime. A message about no task just opens the app.
 */
final class PushNotifications {
    static final String CHANNEL_ID = "metatron_nudges";

    static final String ACTION_DONE = "com.mike.metatron.push.DONE";
    static final String ACTION_SKIP = "com.mike.metatron.push.SKIP";
    static final String ACTION_NOT_YET = "com.mike.metatron.push.NOT_YET";
    static final String ACTION_REMIND = "com.mike.metatron.push.REMIND";
    static final String EXTRA_NID = "nid";
    static final String EXTRA_MINUTES = "minutes";
    /** EXTRA_MINUTES for the "Tomorrow" button — the server picks the time from the day shape. */
    static final int TOMORROW = -1;

    private PushNotifications() {}

    /** A stable notification id per message, so a button press replaces, never stacks. */
    static int idFor(String msgId) {
        return 0x4D000000 | (msgId.hashCode() & 0x00FFFFFF);
    }

    static void ensureChannel(Context c) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        if (nm == null || nm.getNotificationChannel(CHANNEL_ID) != null) return;
        NotificationChannel ch = new NotificationChannel(
                CHANNEL_ID, "Nudges and check-ins", NotificationManager.IMPORTANCE_HIGH);
        ch.setDescription("What your day plan says is due, and check-ins.");
        nm.createNotificationChannel(ch);
    }

    /** First show of a fetched message: {title, body, tasks: [{id, title, remind: [min…]}]}. */
    static void showMessage(Context c, int nid, JSONObject msg) {
        JSONObject pending = new JSONObject();
        try {
            pending.put("title", msg.optString("title", "Metatron"));
            pending.put("body", msg.optString("body", ""));
            pending.put("tasks", msg.optJSONArray("tasks") != null
                    ? msg.optJSONArray("tasks") : new JSONArray());
            pending.put("idx", 0);
        } catch (Exception ignored) {
            return;
        }
        PushStore.putPending(c, nid, pending);
        render(c, nid, pending, null);
    }

    /** The fetch failed: say there is something, say nothing about what. */
    static void showFallback(Context c, int nid) {
        ensureChannel(c);
        post(c, nid, builder(c)
                .setContentTitle("Metatron")
                .setContentText("You have a message — open Metatron to read it.")
                .setContentIntent(openApp(c, nid))
                .setAutoCancel(true)
                .build());
    }

    /**
     * Draw the notification for the task at `idx`. `note` replaces the body when set — "Saved"
     * failures and the next-task line use it.
     */
    static void render(Context c, int nid, JSONObject pending, String note) {
        ensureChannel(c);
        JSONArray tasks = pending.optJSONArray("tasks");
        int idx = pending.optInt("idx", 0);
        String title = pending.optString("title", "Metatron");
        String text = note != null ? note : pending.optString("body", "");
        Notification.Builder b = builder(c)
                .setContentTitle(title)
                .setContentIntent(openApp(c, nid))
                .setAutoCancel(true);
        if (tasks != null && idx < tasks.length()) {
            JSONObject t = tasks.optJSONObject(idx);
            String taskTitle = t == null ? "" : t.optString("title", "");
            if (idx > 0 && note == null) text = "Next: " + taskTitle;
            else if (!taskTitle.isEmpty() && tasks.length() > 1) text = text + "\n▸ " + taskTitle;
            b.addAction(action(c, nid, ACTION_DONE, "Done", 0))
             .addAction(action(c, nid, ACTION_NOT_YET, "Not yet", 0))
             .addAction(action(c, nid, ACTION_SKIP, "Skipped", 0));
        }
        b.setContentText(text).setStyle(new Notification.BigTextStyle().bigText(text));
        post(c, nid, b.build());
    }

    /** "Not yet" → the durations to choose from. None left today → move on. */
    static boolean renderRemindChoices(Context c, int nid, JSONObject pending) {
        JSONArray tasks = pending.optJSONArray("tasks");
        int idx = pending.optInt("idx", 0);
        JSONObject t = tasks == null ? null : tasks.optJSONObject(idx);
        JSONArray opts = t == null ? null : t.optJSONArray("remind");
        if (opts == null || opts.length() == 0) return false;
        ensureChannel(c);
        String text = "Remind me about " + t.optString("title", "this") + " in…";
        Notification.Builder b = builder(c)
                .setContentTitle(pending.optString("title", "Metatron"))
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setContentIntent(openApp(c, nid))
                .setOnlyAlertOnce(true)
                .setAutoCancel(true);
        for (int i = 0; i < Math.min(opts.length(), 3); i++) {
            boolean tomorrow = "tomorrow".equals(opts.optString(i));
            int m = tomorrow ? TOMORROW : opts.optInt(i);
            b.addAction(action(c, nid, ACTION_REMIND, tomorrow ? "Tomorrow" : label(m), m));
        }
        post(c, nid, b.build());
        return true;
    }

    static void cancel(Context c, int nid) {
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        if (nm != null) nm.cancel(nid);
        PushStore.removePending(c, nid);
    }

    private static String label(int minutes) {
        if (minutes < 60) return minutes + " min";
        if (minutes % 60 == 0) return (minutes / 60) + (minutes == 60 ? " hour" : " hours");
        return minutes + " min";
    }

    private static Notification.Builder builder(Context c) {
        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(c, CHANNEL_ID)
                : new Notification.Builder(c);
        return b.setSmallIcon(android.R.drawable.ic_popup_reminder)
                .setCategory(Notification.CATEGORY_REMINDER);
    }

    private static Notification.Action action(Context c, int nid, String act, String label,
                                              int minutes) {
        Intent i = new Intent(c, PushActionReceiver.class).setAction(act)
                .putExtra(EXTRA_NID, nid).putExtra(EXTRA_MINUTES, minutes);
        // A distinct request code per button: PendingIntents that compare equal are shared,
        // and three buttons on one notification would otherwise all fire the last one.
        int code = nid ^ (act.hashCode() * 31 + minutes);
        PendingIntent pi = PendingIntent.getBroadcast(c, code, i, PendingIntent.FLAG_UPDATE_CURRENT
                | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
        return new Notification.Action.Builder(null, label, pi).build();
    }

    private static PendingIntent openApp(Context c, int nid) {
        Intent open = new Intent(c, MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        return PendingIntent.getActivity(c, nid, open, PendingIntent.FLAG_UPDATE_CURRENT
                | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
    }

    private static void post(Context c, int nid, Notification n) {
        NotificationManager nm = c.getSystemService(NotificationManager.class);
        if (nm != null) nm.notify(nid, n);
    }
}
