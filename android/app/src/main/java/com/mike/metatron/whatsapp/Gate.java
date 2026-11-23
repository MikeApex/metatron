package com.mike.metatron.whatsapp;

import android.content.ComponentName;
import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;

/**
 * The phone's half of the consent gate (plan § 3.12, § 4.0): one APK for every user, and nothing
 * switched on until the VM says this user's WhatsApp consent is recorded.
 *
 * Every /device/* reply passes through {@link #observe}. The state is the last thing the VM
 * said, persisted; it only ever moves on an answer — a network failure, a 5xx or a refused
 * address leaves it where it was.
 *
 * - 200                     → OPEN: the listener and the share target are enabled;
 * - 401                     → UNPAIRED: the pairing was refused; the re-pairing notice;
 * - 403 exactly consented_off → CONSENTED_OFF: key, grants and the share list are offered,
 *                              the job may run dry (§ 3.2);
 * - any other 403           → NO_CONSENT. This includes the bare "channel_off" an older VM
 *                              answers for every closed gate, so the APK fails closed against
 *                              a VM that predates § 4.0 (verify new 1);
 * - −3 (no device token, or it cannot be opened) → UNPAIRED, with the re-pairing notice;
 * - −2 (the server address is not https://, e.g. empty after the page signed out) → UNPAIRED.
 *   Neither is silent (F10): the listener is disabled and the job cancelled through {@link #apply}.
 *
 * Outside OPEN the listener and share target are disabled; and once the channel has been open
 * on this install, any state other than OPEN cancels the nightly job — switching the channel
 * off stops reading on the phone as well as on the VM (verify new 3).
 */
public final class Gate {
    public enum State { NO_CONSENT, CONSENTED_OFF, OPEN, UNPAIRED }

    static final String PREFS = "metatron_whatsapp";
    private static final String K_STATE = "gate_state";
    private static final String K_EVER_OPENED = "ever_opened";
    static final String K_DEVICE_ID = "device_id";

    private Gate() {}

    // ---- plain Java, unit-tested -------------------------------------------------------------

    /** What a reply means for the gate; {@code current} when it says nothing about consent. */
    static State next(State current, int status, String detail) {
        if (status == 200) return State.OPEN;
        if (status == 401) return State.UNPAIRED;
        if (status == 403) return "consented_off".equals(detail) ? State.CONSENTED_OFF : State.NO_CONSENT;
        if (status == DeviceApi.UNPAIRED || status == DeviceApi.NOT_HTTPS) return State.UNPAIRED;
        return current;
    }

    /**
     * Once the channel has been open, anything short of open stops all reading. Without a
     * consent record or a pairing there is no job at all, dry or not (§ 3.12) — only
     * CONSENTED_OFF before the first open keeps one, for the dry run (§ 3.2).
     */
    static boolean shouldCancelJob(State s, boolean everOpened) {
        if (s == State.OPEN) return false;
        return everOpened || s == State.NO_CONSENT || s == State.UNPAIRED;
    }

    // ---- on the phone --------------------------------------------------------------------------

    /** The last known state. UNPAIRED with no device token; NO_CONSENT when never learned. */
    public static State state(Context ctx) {
        if (!DeviceTokenVault.present(ctx)) return State.UNPAIRED;
        String s = prefs(ctx).getString(K_STATE, null);
        if (s == null) return State.NO_CONSENT;
        try {
            return State.valueOf(s);
        } catch (IllegalArgumentException e) {
            return State.NO_CONSENT;
        }
    }

    public static boolean everOpened(Context ctx) {
        return prefs(ctx).getBoolean(K_EVER_OPENED, false);
    }

    /** Asks the VM where the gate stands (the cursor call) and applies the answer. Blocking. */
    public static State refresh(Context ctx, DeviceApi api) {
        return observe(ctx, api.get("/device/whatsapp/cursor"));
    }

    /**
     * Every /device/* reply comes through here. Returns the state after it. With no device token
     * stored — after "Turn off", or a reply that raced it — nothing is persisted: a late 200 must
     * not bring back {@code ever_opened} or OPEN.
     */
    public static synchronized State observe(Context ctx, DeviceApi.Result r) {
        if (!DeviceTokenVault.present(ctx)) {
            apply(ctx, State.UNPAIRED);
            return State.UNPAIRED;
        }
        State before = state(ctx);
        State after = next(before, r.status, r.detail);
        SharedPreferences.Editor e = prefs(ctx).edit().putString(K_STATE, after.name());
        if (after == State.OPEN) e.putBoolean(K_EVER_OPENED, true);
        e.commit();

        if (r.status == 401 || r.status == DeviceApi.UNPAIRED) {
            Notices.raise(ctx, Notices.Notice.REPAIR_NEEDED);
        } else if (r.status == 200 || r.status == 403) {
            // The VM accepted the device token, so the pairing stands.
            Notices.clear(ctx, Notices.Notice.REPAIR_NEEDED);
        }
        linkNotices(ctx, after);
        apply(ctx, state(ctx));
        return state(ctx);
    }

    /** Pairing succeeded: consent not yet learned, nothing switched on until the VM answers. */
    static synchronized void paired(Context ctx, String deviceId) {
        prefs(ctx).edit().remove(K_STATE).putString(K_DEVICE_ID, deviceId).commit();
        Notices.clear(ctx, Notices.Notice.REPAIR_NEEDED);
        apply(ctx, state(ctx));
    }

    static String deviceId(Context ctx) {
        return prefs(ctx).getString(K_DEVICE_ID, "");
    }

    /** "Turn off WhatsApp link": forget the state, the device id and that it was ever open. */
    static synchronized void reset(Context ctx) {
        prefs(ctx).edit().remove(K_STATE).remove(K_EVER_OPENED).remove(K_DEVICE_ID).commit();
        setComponents(ctx, false);
    }

    /** The effects of a state: components on only when OPEN; the job stopped as above. */
    static void apply(Context ctx, State s) {
        setComponents(ctx, s == State.OPEN);
        if (shouldCancelJob(s, everOpened(ctx))) NightlyJob.cancel(ctx);
    }

    private static void linkNotices(Context ctx, State s) {
        if (s == State.CONSENTED_OFF) {
            Notices.raise(ctx, Notices.Notice.LINK_OFF);
            Notices.clear(ctx, Notices.Notice.NEEDS_CONSENT);
        } else if (s == State.NO_CONSENT) {
            Notices.raise(ctx, Notices.Notice.NEEDS_CONSENT);
            Notices.clear(ctx, Notices.Notice.LINK_OFF);
        } else {
            Notices.clear(ctx, Notices.Notice.LINK_OFF);
            Notices.clear(ctx, Notices.Notice.NEEDS_CONSENT);
        }
    }

    static void setComponents(Context ctx, boolean on) {
        PackageManager pm = ctx.getPackageManager();
        int want = on ? PackageManager.COMPONENT_ENABLED_STATE_ENABLED
                      : PackageManager.COMPONENT_ENABLED_STATE_DISABLED;
        for (Class<?> k : new Class<?>[] {WaListener.class, MissedShareActivity.class}) {
            ComponentName cn = new ComponentName(ctx, k);
            if (pm.getComponentEnabledSetting(cn) != want) {
                pm.setComponentEnabledSetting(cn, want, PackageManager.DONT_KILL_APP);
            }
        }
    }

    private static SharedPreferences prefs(Context ctx) {
        return ctx.getApplicationContext().getSharedPreferences(PREFS, Context.MODE_PRIVATE);
    }
}
