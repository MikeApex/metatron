package com.mike.metatron;

import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;

import org.json.JSONArray;
import org.json.JSONObject;

/**
 * Done / Not yet / Skipped, and "remind me in …", pressed on a nudge notification.
 *
 * Done and Skipped go to /tasks/act exactly as a tap in the Today panel does — the ledger's
 * evidence is the user's own act ("marked in the app: from the notification"). A reminder goes
 * to /tasks/remind; the day plan sends it by code when it comes due. After each, the same
 * notification moves to the next task, until none are left.
 *
 * goAsync + a thread: a receiver's onReceive runs on the main thread, where network is
 * forbidden, and the process may be killed as soon as onReceive returns unless it is told the
 * work is still running.
 */
public class PushActionReceiver extends BroadcastReceiver {

    @Override
    public void onReceive(Context context, Intent intent) {
        final PendingResult result = goAsync();
        final Context c = context.getApplicationContext();
        new Thread(() -> {
            try {
                handle(c, intent);
            } finally {
                result.finish();
            }
        }, "metatron-push-action").start();
    }

    private static void handle(Context c, Intent intent) {
        int nid = intent.getIntExtra(PushNotifications.EXTRA_NID, 0);
        JSONObject pending = PushStore.pending(c, nid);
        String act = intent.getAction();
        if (pending == null || act == null) {
            PushNotifications.cancel(c, nid);
            return;
        }
        JSONArray tasks = pending.optJSONArray("tasks");
        int idx = pending.optInt("idx", 0);
        JSONObject task = tasks == null ? null : tasks.optJSONObject(idx);
        if (task == null) {
            PushNotifications.cancel(c, nid);
            return;
        }
        String taskId = task.optString("id", "");

        if (PushNotifications.ACTION_NOT_YET.equals(act)) {
            if (!PushNotifications.renderRemindChoices(c, nid, pending)) advance(c, nid, pending);
            return;
        }

        boolean ok;
        try {
            JSONObject body = new JSONObject().put("task_id", taskId);
            String path;
            if (PushNotifications.ACTION_REMIND.equals(act)) {
                path = "/tasks/remind";
                int m = intent.getIntExtra(PushNotifications.EXTRA_MINUTES, 30);
                if (m == PushNotifications.TOMORROW) body.put("when", "tomorrow");
                else body.put("minutes", m);
            } else {
                path = "/tasks/act";
                body.put("action", PushNotifications.ACTION_DONE.equals(act) ? "done" : "skipped");
                body.put("reason", "from the notification");
            }
            PushStore.Result r = PushStore.request(c, "POST", path, body);
            JSONObject j = r.json();
            String status = j == null ? "" : j.optString("status", j.optString("result", ""));
            ok = r.status == 200 && !status.startsWith("error");
        } catch (Exception e) {
            ok = false;
        }
        if (!ok) {
            // Say so on the notification itself, and keep the buttons: a press that silently
            // failed would read as recorded.
            PushNotifications.render(c, nid, pending,
                    "Couldn't save that — check your connection and try again.");
            return;
        }
        advance(c, nid, pending);
    }

    private static void advance(Context c, int nid, JSONObject pending) {
        JSONArray tasks = pending.optJSONArray("tasks");
        int next = pending.optInt("idx", 0) + 1;
        if (tasks == null || next >= tasks.length()) {
            PushNotifications.cancel(c, nid);
            return;
        }
        try {
            pending.put("idx", next);
        } catch (Exception e) {
            PushNotifications.cancel(c, nid);
            return;
        }
        PushStore.putPending(c, nid, pending);
        PushNotifications.render(c, nid, pending, null);
    }
}
