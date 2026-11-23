package com.mike.metatron.whatsapp;

import android.app.Activity;
import android.content.Context;
import android.content.Intent;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.widget.Toast;

/**
 * The "Should have come up" share target (build plan § 3.11): the user long-presses a message in
 * WhatsApp → Share → Metatron. Disabled in the manifest; {@link Gate} enables it only while the
 * channel is open (§ 3.12). Translucent, no layout.
 *
 * A thin adapter — the decision is {@link MissedShare}. On {@code ACTION_SEND} {@code text/plain},
 * and only when the gate is OPEN: read {@code EXTRA_TEXT}, take it out of the intent, and finish at
 * once so nothing sits over WhatsApp; off the main thread, hash it ({@link MissedShare#hashOf}) and
 * drop the reference, build the flag, post it with {@link DeviceClient}, pass the reply through
 * {@link Gate#observe}, and toast a short confirmation.
 *
 * <b>The shared text is never posted, stored, logged or shown.</b> Nothing here logs at all, and a
 * failure is told by a fixed sentence, never an exception's message (§ 3.7).
 */
public class MissedShareActivity extends Activity {
    static final String NOTED = "Noted — thanks";
    static final String UNREACHABLE = "Couldn't reach Metatron — try again later";
    static final String LINK_NOT_ON = "The WhatsApp link is not on";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Intent in = getIntent();
        final Context app = getApplicationContext();
        if (in == null || !Intent.ACTION_SEND.equals(in.getAction())
                || in.getType() == null || !in.getType().startsWith("text/plain")) {
            finish();
            return;
        }
        if (Gate.state(app) != Gate.State.OPEN) {
            in.removeExtra(Intent.EXTRA_TEXT);
            Toast.makeText(app, LINK_NOT_ON, Toast.LENGTH_SHORT).show();
            finish();
            return;
        }
        CharSequence cs = in.getCharSequenceExtra(Intent.EXTRA_TEXT);
        in.removeExtra(Intent.EXTRA_TEXT);
        final String[] held = {cs == null ? null : cs.toString()};
        cs = null;
        finish();

        Thread t = new Thread(() -> {
            String toast;
            try {
                SentHashes sent = SentHashes.open(WaFiles.stateDir(app));
                byte[] hash = MissedShare.hashOf(held[0], sent);
                held[0] = null;
                MissedShare.Flag flag = MissedShare.flagFor(hash, sent);
                DeviceApi.Result r = new DeviceClient(app).post(MissedShare.PATH, flag.toJson(),
                        MissedShare.READ_TIMEOUT_MS);
                Gate.State after = Gate.observe(app, r);
                if (r.status == 200) toast = NOTED;
                else if (after != Gate.State.OPEN) toast = LINK_NOT_ON;
                else toast = UNREACHABLE;
            } catch (RuntimeException e) {
                toast = UNREACHABLE;
            } finally {
                held[0] = null;
            }
            final String shown = toast;
            new Handler(Looper.getMainLooper()).post(
                    () -> Toast.makeText(app, shown, Toast.LENGTH_SHORT).show());
        }, "wa-missed-share");
        t.start();
    }
}
