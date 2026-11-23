package com.mike.metatron.whatsapp;

import android.Manifest;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.os.Build;

import java.util.Collections;
import java.util.EnumSet;
import java.util.Set;

/**
 * How the user is told the WhatsApp link has broken (plan § 3.6, decision 3): a native
 * notification once per onset, and a standing line on the WhatsApp screen for as long as the
 * condition holds. The two link states (off / needs consent) are screen-only — no notification.
 *
 * Every word is written here. Nothing from a backup, a reply or an exception reaches a notice.
 */
public final class Notices {
    public enum Notice { BACKUP_STALE, TEXT_GONE, READ_REFUSED, REPAIR_NEEDED, SHARE_OUT_OF_STEP, LINK_OFF, NEEDS_CONSENT }

    private static final String K_ACTIVE = "notices_active";
    private static final int ID_BASE = 0x57410100;

    private Notices() {}

    // ---- plain Java, unit-tested -------------------------------------------------------------

    /** The link states are shown on the screen only. */
    static boolean notifies(Notice n) {
        return n != Notice.LINK_OFF && n != Notice.NEEDS_CONSENT;
    }

    /** The set of active notices, and whether raising one is an onset that posts. */
    static final class Ledger {
        private final EnumSet<Notice> active;

        Ledger(Set<Notice> active) {
            this.active = active.isEmpty() ? EnumSet.noneOf(Notice.class) : EnumSet.copyOf(active);
        }

        /** Marks it active. True when this is an onset that should post a notification. */
        boolean raise(Notice n) {
            boolean onset = active.add(n);
            return onset && notifies(n);
        }

        /** True when it was active. */
        boolean clear(Notice n) {
            return active.remove(n);
        }

        Set<Notice> active() {
            return Collections.unmodifiableSet(EnumSet.copyOf(active));
        }

        String encode() {
            StringBuilder b = new StringBuilder();
            for (Notice n : active) {
                if (b.length() > 0) b.append(',');
                b.append(n.name());
            }
            return b.toString();
        }

        static Ledger decode(String s) {
            EnumSet<Notice> set = EnumSet.noneOf(Notice.class);
            if (s != null) {
                for (String part : s.split(",")) {
                    try {
                        if (!part.isEmpty()) set.add(Notice.valueOf(part));
                    } catch (IllegalArgumentException ignored) {
                        // A notice an older build knew and this one does not: dropped.
                    }
                }
            }
            return new Ledger(set);
        }
    }

    /** The heading, as shown in the notification and as the screen's standing line. */
    static String title(Notice n) {
        switch (n) {
            case BACKUP_STALE: return "WhatsApp has stopped backing up";
            case TEXT_GONE: return "WhatsApp changed how it stores messages";
            case READ_REFUSED: return "The nightly read is refused";
            case REPAIR_NEEDED: return "WhatsApp link needs re-pairing";
            case SHARE_OUT_OF_STEP: return "Your chosen chats are out of step with Metatron";
            case LINK_OFF: return "WhatsApp link is off";
            case NEEDS_CONSENT: return "WhatsApp needs your consent first";
            default: return "WhatsApp link";
        }
    }

    /** One line saying what to do about it. */
    static String text(Notice n) {
        switch (n) {
            case BACKUP_STALE:
                return "No new WhatsApp backup has been written for a while, so new messages are not "
                        + "reaching Metatron. Check that WhatsApp's chat backup is on.";
            case TEXT_GONE:
                return "The latest backups carry no message text Metatron can read. An app update may be needed.";
            case READ_REFUSED:
                return "Metatron could not read the WhatsApp backup. Open the WhatsApp link screen for the reason.";
            case REPAIR_NEEDED:
                return "Metatron no longer recognises this phone. Open the WhatsApp link screen and pair it again.";
            case SHARE_OUT_OF_STEP:
                return "Metatron does not have your current list of chats. Open the WhatsApp link screen to send it again.";
            case LINK_OFF:
                return "Your consent is recorded. Metatron has not switched the link on yet.";
            case NEEDS_CONSENT:
                return "Nothing is read until you give your consent in Metatron.";
            default:
                return "";
        }
    }

    // ---- on the phone --------------------------------------------------------------------------

    /** Records it active; posts a notification only on onset, and never for the link states. */
    public static synchronized void raise(Context ctx, Notice n) {
        Ledger l = load(ctx);
        boolean post = l.raise(n);
        save(ctx, l);
        if (post) post(ctx, n);
    }

    public static synchronized void clear(Context ctx, Notice n) {
        Ledger l = load(ctx);
        if (l.clear(n)) save(ctx, l);
        cancel(ctx, n);
    }

    public static synchronized Set<Notice> active(Context ctx) {
        return load(ctx).active();
    }

    /** "Turn off WhatsApp link": every notice cleared, every notification withdrawn. */
    static synchronized void clearAll(Context ctx) {
        prefs(ctx).edit().remove(K_ACTIVE).commit();
        for (Notice n : Notice.values()) cancel(ctx, n);
    }

    private static Ledger load(Context ctx) {
        return Ledger.decode(prefs(ctx).getString(K_ACTIVE, ""));
    }

    private static void save(Context ctx, Ledger l) {
        prefs(ctx).edit().putString(K_ACTIVE, l.encode()).commit();
    }

    private static void post(Context ctx, Notice n) {
        try {
            if (Build.VERSION.SDK_INT >= 33 && ctx.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)
                    != PackageManager.PERMISSION_GRANTED) {
                return; // the standing line on the screen still shows it
            }
            NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
            if (nm == null) return;
            Notification.Builder b;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                if (nm.getNotificationChannel(WaFiles.NOTICE_CHANNEL) == null) {
                    NotificationChannel ch = new NotificationChannel(WaFiles.NOTICE_CHANNEL,
                            "WhatsApp link", NotificationManager.IMPORTANCE_DEFAULT);
                    ch.setDescription("When WhatsApp messages stop reaching Metatron.");
                    nm.createNotificationChannel(ch);
                }
                b = new Notification.Builder(ctx, WaFiles.NOTICE_CHANNEL);
            } else {
                b = new Notification.Builder(ctx);
            }
            Intent open = new Intent(ctx, WhatsAppActivity.class).setFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
            PendingIntent pi = PendingIntent.getActivity(ctx, id(n), open, PendingIntent.FLAG_UPDATE_CURRENT
                    | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M ? PendingIntent.FLAG_IMMUTABLE : 0));
            b.setSmallIcon(android.R.drawable.stat_notify_error)
                    .setContentTitle(title(n))
                    .setContentText(text(n))
                    .setStyle(new Notification.BigTextStyle().bigText(text(n)))
                    .setContentIntent(pi)
                    .setAutoCancel(true);
            nm.notify(id(n), b.build());
        } catch (RuntimeException ignored) {
            // A notification that cannot be shown leaves the notice active on the screen.
        }
    }

    private static void cancel(Context ctx, Notice n) {
        NotificationManager nm = (NotificationManager) ctx.getSystemService(Context.NOTIFICATION_SERVICE);
        if (nm != null) nm.cancel(id(n));
    }

    private static int id(Notice n) {
        return ID_BASE + n.ordinal();
    }

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(Gate.PREFS, Context.MODE_PRIVATE);
    }
}
