package com.mike.metatron.whatsapp;

import android.app.Notification;
import android.content.Context;
import android.os.Build;
import android.service.notification.NotificationListenerService;
import android.service.notification.StatusBarNotification;

import androidx.core.app.NotificationCompat;
import androidx.core.app.Person;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.ScheduledExecutorService;
import java.util.concurrent.TimeUnit;

/**
 * The live feed (build plan § 3.10) — a thin adapter. It acts only on {@code com.whatsapp} posts,
 * only while {@link Gate} is OPEN, reduces each to a {@link LiveEvents.Posted} on the main thread
 * (in memory, no I/O) and hands it to {@link LiveEvents}, which decides and posts off the main
 * thread. Disabled in the manifest; {@link Gate} enables it only while the channel is open (§ 3.12).
 *
 * Nothing is logged: a failure is counted in {@link LiveEvents#counts}, because a stack trace
 * could carry notification content. Pending posts live in memory only, so a disconnect drops them
 * and the nightly backup sends them.
 */
public class WaListener extends NotificationListenerService {
    /** How often due retries are tried and expired ones given up. */
    static final long TICK_SECONDS = 15;

    private volatile LiveEvents live;
    private ExecutorService pool;
    private ScheduledExecutorService timer;

    @Override
    public void onListenerConnected() {
        start();
    }

    @Override
    public void onListenerDisconnected() {
        stop();
    }

    @Override
    public void onDestroy() {
        stop();
        super.onDestroy();
    }

    @Override
    public void onNotificationPosted(StatusBarNotification sbn) {
        LiveEvents l = live;
        if (l == null || sbn == null || !LiveEvents.WHATSAPP.equals(sbn.getPackageName())) return;
        try {
            l.onPosted(toPosted(sbn));
        } catch (Throwable t) {
            synchronized (l.counts) {
                l.counts.errors++;
            }
        }
    }

    private synchronized void start() {
        if (live != null) return;
        final Context app = getApplicationContext();
        try {
            SentHashes sent = SentHashes.open(WaFiles.stateDir(app));
            pool = Executors.newCachedThreadPool();
            timer = Executors.newSingleThreadScheduledExecutor();
            DeviceApi api = new DeviceClient(app);
            LiveEvents.Shares shares = new LiveEvents.Shares() {
                @Override
                public String canonicalShared(String raw) {
                    return ShareList.canonicalShared(app, raw);
                }

                @Override
                public String kindOf(String canonical) {
                    return ShareList.kindOf(app, canonical);
                }

                @Override
                public boolean acceptedCurrent() {
                    return ShareList.acceptedCurrent(app);
                }
            };
            LiveEvents.GateView gate = new LiveEvents.GateView() {
                @Override
                public boolean open() {
                    return Gate.state(app) == Gate.State.OPEN;
                }

                @Override
                public boolean observe(DeviceApi.Result reply) {
                    return Gate.observe(app, reply) == Gate.State.OPEN;
                }
            };
            final LiveEvents l = new LiveEvents(api, System::currentTimeMillis, shares, gate, sent, pool);
            timer.scheduleWithFixedDelay(() -> {
                try {
                    l.tick();
                } catch (Throwable t) {
                    synchronized (l.counts) {
                        l.counts.errors++;
                    }
                }
            }, TICK_SECONDS, TICK_SECONDS, TimeUnit.SECONDS);
            live = l;
        } catch (Throwable t) {
            // The state folder cannot be opened: no live feed this connection; the backup still runs.
            stop();
        }
    }

    private synchronized void stop() {
        live = null;
        if (timer != null) timer.shutdownNow();
        if (pool != null) pool.shutdownNow();
        timer = null;
        pool = null;
    }

    /** The notification as the decisions need it. Text is copied into memory only. */
    static LiveEvents.Posted toPosted(StatusBarNotification sbn) {
        Notification n = sbn.getNotification();
        boolean summary = (n.flags & Notification.FLAG_GROUP_SUMMARY) != 0;
        String shortcut = Build.VERSION.SDK_INT >= 26 ? n.getShortcutId() : null;
        List<LiveEvents.Line> lines = new ArrayList<>();
        if (!summary && shortcut != null && !shortcut.isEmpty()) {
            NotificationCompat.MessagingStyle style =
                    NotificationCompat.MessagingStyle.extractMessagingStyleFromNotification(n);
            if (style != null) {
                Person user = style.getUser();
                for (NotificationCompat.MessagingStyle.Message m : style.getMessages()) {
                    CharSequence text = m.getText();
                    lines.add(new LiveEvents.Line(m.getTimestamp(), text == null ? null : text.toString(),
                            isOwn(m.getPerson(), user)));
                }
            }
        }
        return new LiveEvents.Posted(sbn.getPackageName(), summary, shortcut, lines);
    }

    /**
     * Whether a message is the user's own. By the platform's MessagingStyle convention a message
     * with no person is the user's; one whose person matches the style's user by key, or by name
     * when neither has a key, is treated as the user's too. When unsure, it errs toward "own" — not
     * sent live, so the user's text can never go out as a received message; the backup still
     * reads every row.
     */
    static boolean isOwn(Person p, Person user) {
        if (p == null) return true;
        if (user == null) return false;
        if (p == user) return true;
        if (p.getKey() != null && user.getKey() != null) return p.getKey().equals(user.getKey());
        CharSequence pn = p.getName(), un = user.getName();
        return pn != null && un != null && pn.toString().equals(un.toString());
    }
}
