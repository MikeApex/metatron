package com.mike.metatron.whatsapp;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.ComponentName;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.Settings;
import android.text.InputType;
import android.view.View;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.app.NotificationManagerCompat;

import com.mike.metatron.PushStore;

import java.io.File;
import java.util.Arrays;
import java.util.Map;

/**
 * The WhatsApp link screen (plan § 3.8, § 3.12), built in code. What it offers follows the
 * gate's state, refreshed from the VM each time it opens:
 *
 * - UNPAIRED      → "not set up" and, for a signed-in user, "Pair this phone";
 * - NO_CONSENT    → "needs your consent first" and nothing else — no key, no grant, no job;
 * - CONSENTED_OFF → the key, All-files access, contacts, the share list and (before the
 *                   channel has ever opened) the dry run;
 * - OPEN          → the same without the dry run, plus notification access; the nightly job
 *                   is scheduled once All-files access is held and a key is stored.
 *
 * All-files access and contacts are asked for only here, only at the user's own tap, and only
 * once the VM has said consent is recorded. FLAG_SECURE: the key is typed on this screen.
 * Errors are shown as code-written text, never an exception's message (§ 3.7).
 */
public class WhatsAppActivity extends Activity {
    private static final int REQ_STORAGE = 1;
    private static final int REQ_CONTACTS = 2;
    /** Longer than any WhatsApp device model name; the VM stores it as a label only. */
    private static final int MAX_LABEL = 60;

    private LinearLayout col;
    private int pad;
    private volatile boolean busy;
    private Gate.State rendered;
    private TextView checkingLine;
    /** The last reader self-test's summary — counts and check names only; kept across redraws. */
    private volatile String selfTestLine;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        pad = (int) (12 * getResources().getDisplayMetrics().density);
        col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        col.setPadding(pad, pad, pad, pad);
        ScrollView scroll = new ScrollView(this);
        scroll.addView(col);
        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        render(Gate.state(this), true);
        refreshFromVm();
    }

    /** Asks the VM where the gate stands, off the main thread, then redraws. */
    private void refreshFromVm() {
        final Context app = getApplicationContext();
        new Thread(() -> {
            Gate.State s = DeviceTokenVault.present(app)
                    ? Gate.refresh(app, new DeviceClient(app)) : Gate.state(app);
            if (s == Gate.State.OPEN && allFilesGranted(app) && KeyVault.present(app)) {
                NightlyJob.ensureScheduled(app);
            }
            // § 3.9: a list the VM has not accepted is re-posted on the next run, change or app open.
            // Only while open — before that every post is refused by the gate, by design. A list the
            // user never saved on this install posts nothing (ShareList.repost → NOT_SAVED).
            if (s == Gate.State.OPEN && !ShareList.acceptedCurrent(app)) {
                ShareList.repost(app, new DeviceClient(app));
            }
            final Gate.State shown = s;
            runOnUiThread(() -> {
                if (isFinishing()) return;
                // Unchanged: only drop the "checking" line, so a key being typed is not wiped.
                if (shown == rendered && checkingLine != null) checkingLine.setVisibility(View.GONE);
                else render(shown, false);
            });
        }, "metatron-wa-gate").start();
    }

    // ---- the screen ---------------------------------------------------------------------------

    private void render(Gate.State s, boolean checking) {
        col.removeAllViews();
        rendered = s;
        text("WhatsApp link", 18, true);
        checkingLine = checking ? text("Checking with Metatron…", 13, false) : null;

        for (Notices.Notice n : Notices.active(this)) {
            if (!Notices.notifies(n)) continue; // the link states are the state line below
            text("⚠ " + Notices.title(n) + " — " + Notices.text(n), 14, false);
        }

        switch (s) {
            case UNPAIRED:
                text("WhatsApp link: not set up", 15, false);
                if (PushStore.signedIn(this)) {
                    col.addView(button("Pair this phone", v -> runAction(WhatsAppActivity::pair)));
                } else {
                    text("Sign in to Metatron first", 14, false);
                }
                break;
            case NO_CONSENT:
                text(Notices.title(Notices.Notice.NEEDS_CONSENT), 15, false);
                break;
            case CONSENTED_OFF:
                text(Notices.title(Notices.Notice.LINK_OFF) + ". " + Notices.text(Notices.Notice.LINK_OFF), 15, false);
                consentedControls(false);
                if (!Gate.everOpened(this)) {
                    col.addView(button("Dry run now", v -> {
                        String said = NightlyJob.runDryNow(getApplicationContext());
                        if (!said.isEmpty()) Toast.makeText(this, said, Toast.LENGTH_SHORT).show();
                    }));
                }
                RunStatusView.addTo(col, this);
                break;
            case OPEN:
                text("WhatsApp link is on", 15, false);
                consentedControls(true);
                RunStatusView.addTo(col, this);
                break;
        }

        if (DeviceTokenVault.present(this)) {
            col.addView(button("Turn off WhatsApp link", v -> confirmTurnOff()));
        }
    }

    /** What a user with a consent record is offered: key, grants, the share list. */
    private void consentedControls(boolean open) {
        boolean hasKey = KeyVault.present(this);
        text("Backup key: " + (hasKey ? "stored" : "not entered"), 14, false);
        final EditText field = new EditText(this);
        // Password-type so keyboards neither learn nor suggest it; visible so 64 digits can be
        // checked as typed — the screen itself is FLAG_SECURE (the probe's protections, § 3.8).
        field.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        if (Build.VERSION.SDK_INT >= 26) field.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        field.setTypeface(Typeface.MONOSPACE);
        field.setHint("The 64-digit end-to-end backup key");
        col.addView(field);
        col.addView(button(hasKey ? "Replace key" : "Save key", v -> saveKey(field)));
        if (hasKey) col.addView(button("Remove key", v -> removeKey()));

        boolean files = allFilesGranted(this);
        col.addView(button(files ? "All-files access: allowed" : "Allow all-files access",
                v -> requestAllFiles()));
        boolean contacts = checkSelfPermission(Manifest.permission.READ_CONTACTS) == PackageManager.PERMISSION_GRANTED;
        col.addView(button(contacts ? "Contacts: allowed" : "Allow contacts (to name your chats)",
                v -> requestContacts()));
        col.addView(button("Choose chats", v -> startActivity(new Intent(this, ShareListActivity.class))));
        // The on-device reader self-test (SelfTest): synthetic data only, off the main thread.
        col.addView(button("Check this phone's reader", v -> runAction(c -> selfTestLine = SelfTest.run(c).summary())));
        if (selfTestLine != null) text(selfTestLine, 14, false);
        if (open) {
            boolean listening = NotificationManagerCompat.getEnabledListenerPackages(this).contains(getPackageName());
            col.addView(button(listening ? "Notification access: allowed" : "Allow notification access",
                    v -> openNotificationAccess()));
        }
    }

    private TextView text(String s, int size, boolean bold) {
        TextView t = new TextView(this);
        t.setText(s);
        t.setTextSize(size);
        if (bold) t.setTypeface(Typeface.DEFAULT_BOLD);
        t.setPadding(0, pad / 2, 0, pad / 2);
        col.addView(t);
        return t;
    }

    private Button button(String label, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }

    // ---- the key ------------------------------------------------------------------------------

    private void saveKey(EditText field) {
        byte[] root = null;
        try {
            root = BackupKey.parseRoot(field.getText());
            KeyVault.store(this, root);
            Toast.makeText(this, "Key saved", Toast.LENGTH_SHORT).show();
        } catch (BackupException e) {
            Toast.makeText(this, e.error.userText, Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Could not store the key (" + e.getClass().getSimpleName() + ")", Toast.LENGTH_LONG).show();
        } finally {
            if (root != null) Arrays.fill(root, (byte) 0);
            field.getText().clear();
        }
        render(Gate.state(this), false);
        refreshFromVm();
    }

    private void removeKey() {
        try {
            KeyVault.delete(this);
            Toast.makeText(this, "Key removed", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Could not remove the key (" + e.getClass().getSimpleName() + ")", Toast.LENGTH_LONG).show();
        }
        render(Gate.state(this), false);
    }

    // ---- grants -------------------------------------------------------------------------------

    static boolean allFilesGranted(Context ctx) {
        if (Build.VERSION.SDK_INT >= 30) return Environment.isExternalStorageManager();
        return ctx.checkSelfPermission(Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
    }

    /** All-files access and contacts are never asked for without the consent record (§ 3.12). */
    private boolean consentRecorded() {
        Gate.State s = Gate.state(this);
        return s == Gate.State.CONSENTED_OFF || s == Gate.State.OPEN;
    }

    private void requestContacts() {
        if (!consentRecorded()) return;
        requestPermissions(new String[] {Manifest.permission.READ_CONTACTS}, REQ_CONTACTS);
    }

    private void requestAllFiles() {
        if (!consentRecorded()) return;
        if (Build.VERSION.SDK_INT < 30) {
            requestPermissions(new String[] {Manifest.permission.READ_EXTERNAL_STORAGE}, REQ_STORAGE);
            return;
        }
        try {
            startActivity(new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                    Uri.parse("package:" + getPackageName())));
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
        }
    }

    private void openNotificationAccess() {
        Intent i;
        if (Build.VERSION.SDK_INT >= 30) {
            i = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS);
            i.putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME,
                    new ComponentName(this, WaListener.class).flattenToString());
        } else {
            i = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
        }
        try {
            startActivity(i);
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        }
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        render(Gate.state(this), false);
        refreshFromVm();
    }

    // ---- pairing and turning off --------------------------------------------------------------

    private interface Action {
        String run(Context ctx);
    }

    /** Runs a blocking action off the main thread, shows its code-written outcome, redraws. */
    private void runAction(Action a) {
        if (busy) return;
        busy = true;
        final Context app = getApplicationContext();
        new Thread(() -> {
            String said;
            try {
                said = a.run(app);
            } catch (RuntimeException e) {
                said = "Something went wrong (" + e.getClass().getSimpleName() + ")";
            }
            final String shown = said;
            runOnUiThread(() -> {
                busy = false;
                if (isFinishing()) return;
                Toast.makeText(this, shown, Toast.LENGTH_LONG).show();
                render(Gate.state(this), false);
                refreshFromVm();
            });
        }, "metatron-wa-action").start();
    }

    /**
     * "Pair this phone": the sign-in token mints a device token on the VM; the device token is
     * sealed here and never shown or handed to the page. Blocking.
     */
    static String pair(Context ctx) {
        if (!PushStore.signedIn(ctx)) return "Sign in to Metatron first";
        String label = Build.MODEL == null || Build.MODEL.trim().isEmpty() ? "Android phone" : Build.MODEL.trim();
        if (label.length() > MAX_LABEL) label = label.substring(0, MAX_LABEL);
        DeviceApi.Result r = PushStore.sessionPost(ctx, "/whatsapp/device/pair",
                "{\"label\":" + DeviceClient.jsonString(label) + "}");
        if (r.status == DeviceApi.NOT_HTTPS) return "Pairing needs a secure (https) connection to Metatron";
        if (r.status == DeviceApi.NETWORK) return "Could not reach Metatron (" + r.detail + ")";
        if (r.status == 401) return "Sign in to Metatron again, then pair";
        if (r.status != 200) return "Pairing was refused (HTTP " + r.status + ")";
        String token = null, deviceId = null;
        try {
            Object v = Json.parse(r.body);
            if (v instanceof Map) {
                Object t = ((Map<?, ?>) v).get("token"), d = ((Map<?, ?>) v).get("device_id");
                if (t instanceof String) token = (String) t;
                if (d instanceof String) deviceId = (String) d;
            }
        } catch (Json.Malformed ignored) {
            // falls through to the refusal below
        }
        if (token == null || token.isEmpty() || deviceId == null || deviceId.isEmpty()) {
            return "Pairing failed: Metatron's reply was not understood";
        }
        try {
            DeviceTokenVault.store(ctx, token);
        } catch (Exception e) {
            return "Could not store the pairing (" + e.getClass().getSimpleName() + ")";
        }
        Gate.paired(ctx, deviceId);
        Gate.refresh(ctx, new DeviceClient(ctx));
        return "This phone is paired";
    }

    private void confirmTurnOff() {
        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("Turn off WhatsApp link?")
                .setMessage("This phone stops reading WhatsApp and is unpaired from Metatron. The key, "
                        + "your chosen chats and everything else the link kept on this phone are deleted.")
                .setPositiveButton("Turn off", (dlg, w) -> runAction(WhatsAppActivity::turnOff))
                .setNegativeButton("Cancel", null)
                .create();
        d.show();
    }

    /**
     * "Turn off WhatsApp link" (§ 3.8): revoke on the VM, then — whatever it answered — delete
     * the key, the device token and everything in wa_state/, stop the job, switch the listener
     * and share target off, forget that the channel was ever open, clear every notice. Blocking.
     */
    static String turnOff(Context ctx) {
        String id = Gate.deviceId(ctx);
        boolean told = false;
        if (!id.isEmpty() && PushStore.signedIn(ctx)) {
            DeviceApi.Result r = PushStore.sessionPost(ctx, "/whatsapp/device/revoke",
                    "{\"device_id\":" + DeviceClient.jsonString(id) + "}");
            told = r.status == 200 || r.status == 404; // 404: already revoked
        }
        int failed = 0;
        try { NightlyJob.cancel(ctx); } catch (RuntimeException e) { failed++; }
        try { Gate.reset(ctx); } catch (RuntimeException e) { failed++; }
        try { KeyVault.delete(ctx); } catch (Exception e) { failed++; }
        try { DeviceTokenVault.delete(ctx); } catch (Exception e) { failed++; }
        // The in-memory copies first, so no write later in this process can bring a file back: the
        // sent-hash list's cached instance (its salt and entries), the share list, the chat list.
        try { SentHashes.open(WaFiles.stateDir(ctx)).deleteAll(); } catch (RuntimeException e) { failed++; }
        try { ShareList.deleteAll(ctx); } catch (RuntimeException e) { failed++; }
        NightlyRead.forgetChatList();
        if (!emptyDir(WaFiles.stateDir(ctx))) failed++;
        try { Notices.clearAll(ctx); } catch (RuntimeException e) { failed++; }
        if (failed > 0) return "WhatsApp link turned off, but " + failed + " item(s) could not be deleted — try again";
        return told ? "WhatsApp link turned off. Everything it kept on this phone is deleted"
                    : "WhatsApp link turned off on this phone. Metatron could not be told; "
                      + "the pairing lapses by itself after 30 days unused";
    }

    /** Deletes everything inside {@code dir}, keeping the folder. True when it is empty after. */
    static boolean emptyDir(File dir) {
        File[] kids = dir.listFiles();
        if (kids == null) return !dir.exists() || dir.isDirectory();
        boolean ok = true;
        for (File k : kids) {
            if (k.isDirectory() && !emptyDir(k)) ok = false;
            if (!k.delete() && k.exists()) ok = false;
        }
        return ok;
    }
}
