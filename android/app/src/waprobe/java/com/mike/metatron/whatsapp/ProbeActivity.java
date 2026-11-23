package com.mike.metatron.whatsapp;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.ClipData;
import android.content.ComponentName;
import android.content.Intent;
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
import androidx.core.content.FileProvider;

import java.io.File;
import java.util.Arrays;

/**
 * The Phase 0 probe screen (plan § 4, M1). Native, never the WebView (P4). Shows counts and
 * formats only, and is selectable so the report can be copied as text.
 */
public class ProbeActivity extends Activity {
    private TextView status, report;
    private Button runBackup, runIncrement, runFieldMap, runProof, runSample;

    @Override
    protected void onCreate(Bundle saved) {
        super.onCreate(saved);
        sweepDecrypted();

        LinearLayout col = new LinearLayout(this);
        col.setOrientation(LinearLayout.VERTICAL);
        int pad = (int) (12 * getResources().getDisplayMetrics().density);
        col.setPadding(pad, pad, pad, pad);

        TextView title = new TextView(this);
        title.setText("WhatsApp probe — Phase 0 (counts and formats only; nothing leaves the phone)");
        title.setTextSize(16);
        col.addView(title);

        status = new TextView(this);
        status.setPadding(0, pad, 0, pad);
        col.addView(status);

        col.addView(button("1. Notification access", v -> openNotificationAccess()));
        col.addView(button("2. All-files access", v -> openAllFilesAccess()));
        col.addView(button("3. Enter backup key", v -> enterKey()));
        runBackup = button("4. Run backup probe", v -> runBackupProbe());
        col.addView(runBackup);
        runIncrement = button("5. Try newest increment", v -> runIncrementTest());
        col.addView(runIncrement);
        runFieldMap = button("6. Field map counts (P3)", v -> runFieldMapCounts());
        col.addView(runFieldMap);
        runProof = button("7. Read the set (P3 proof)", v -> runSetProof());
        col.addView(runProof);
        runSample = button("8. Export a labelling sample (M2)", v -> runSampleExport());
        col.addView(runSample);
        col.addView(button("Refresh", v -> refresh()));
        col.addView(button("Delete all probe data", v -> confirmDelete()));

        report = new TextView(this);
        report.setTypeface(Typeface.MONOSPACE);
        report.setTextSize(11);
        report.setTextIsSelectable(true);
        report.setPadding(0, pad, 0, pad);
        col.addView(report);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(col);
        setContentView(scroll);
    }

    @Override
    protected void onResume() {
        super.onResume();
        refresh();
    }

    private Button button(String label, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(label);
        b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }

    private boolean listenerEnabled() {
        return NotificationManagerCompat.getEnabledListenerPackages(this).contains(getPackageName());
    }

    private boolean allFilesGranted() {
        return Build.VERSION.SDK_INT < 30 || Environment.isExternalStorageManager();
    }

    private void refresh() {
        status.setText("1. Notification access: " + (listenerEnabled() ? "ON" : "off")
                + "\n2. All-files access: " + (allFilesGranted() ? "ON" : "off")
                + "\n3. Backup key: " + (ProbeKeyVault.present(this) ? "stored (Keystore-wrapped)" : "not entered")
                + "\n8. Labelling sample on this phone: " + (ProbeM2Run.sampleFile(this).exists()
                        ? "PRESENT — removed at the next launch after 15 min, or by Delete all probe data" : "none"));
        String saved = ProbeStore.savedReport(this);
        String inc = ProbeStore.savedIncrementReport(this);
        String map = ProbeStore.savedFieldMapReport(this);
        String proof = ProbeStore.savedProofReport(this);
        String m2 = ProbeStore.savedM2Report(this);
        report.setText((m2 == null ? "" : m2 + "\n") + (proof == null ? "" : proof + "\n") + (map == null ? "" : map + "\n") + ProbeReport.device(this) + "\n" + ProbeReport.survival(this) + "\n"
                + ProbeReport.events(this) + "\n"
                + ProbeReport.listener(this) + "\n" + (saved == null ? "== BACKUP PROBE ==\nnot run yet\n" : saved)
                + "\n" + (inc == null ? "== INCREMENT TEST ==\nnot run yet\n" : inc));
    }

    private void openNotificationAccess() {
        Intent i;
        if (Build.VERSION.SDK_INT >= 30) {
            i = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_DETAIL_SETTINGS);
            i.putExtra(Settings.EXTRA_NOTIFICATION_LISTENER_COMPONENT_NAME,
                    new ComponentName(this, ProbeListener.class).flattenToString());
        } else {
            i = new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS);
        }
        try {
            startActivity(i);
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS));
        }
    }

    private void openAllFilesAccess() {
        if (Build.VERSION.SDK_INT < 30) {
            Toast.makeText(this, "Not needed on this Android version", Toast.LENGTH_SHORT).show();
            return;
        }
        try {
            startActivity(new Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION,
                    Uri.parse("package:" + getPackageName())));
        } catch (Exception e) {
            startActivity(new Intent(Settings.ACTION_MANAGE_ALL_FILES_ACCESS_PERMISSION));
        }
    }

    /** P4: a native field, password-type so keyboards neither learn nor suggest it, screenshots blocked. */
    private void enterKey() {
        EditText field = new EditText(this);
        field.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_VISIBLE_PASSWORD
                | InputType.TYPE_TEXT_FLAG_NO_SUGGESTIONS);
        if (Build.VERSION.SDK_INT >= 26) field.setImportantForAutofill(View.IMPORTANT_FOR_AUTOFILL_NO);
        field.setTypeface(Typeface.MONOSPACE);
        field.setHint("64 digits and letters a–f; spaces are fine");
        AlertDialog d = new AlertDialog.Builder(this)
                .setTitle("WhatsApp backup key")
                .setMessage("The 64-digit key WhatsApp showed when you turned on end-to-end backup. "
                        + "If you chose a password instead, there is no key to enter: switch the backup "
                        + "to the 64-digit key option in WhatsApp first.")
                .setView(field)
                .setPositiveButton("Save", (dlg, w) -> saveKey(field))
                .setNegativeButton("Cancel", (dlg, w) -> field.getText().clear())
                .create();
        d.getWindow().setFlags(WindowManager.LayoutParams.FLAG_SECURE, WindowManager.LayoutParams.FLAG_SECURE);
        d.show();
    }

    private void saveKey(EditText field) {
        byte[] root = null;
        try {
            root = BackupKey.parseRoot(field.getText());
            ProbeKeyVault.store(this, root);
            Toast.makeText(this, "Key saved", Toast.LENGTH_SHORT).show();
        } catch (BackupException e) {
            Toast.makeText(this, e.error.userText, Toast.LENGTH_LONG).show();
        } catch (Exception e) {
            Toast.makeText(this, "Could not store the key: " + e.getClass().getSimpleName(), Toast.LENGTH_LONG).show();
        } finally {
            if (root != null) Arrays.fill(root, (byte) 0);
            field.getText().clear();
            refresh();
        }
    }

    /** P3's app-start sweep: a decrypted copy a crash left behind does not survive a launch. */
    private void sweepDecrypted() {
        File work = new File(getNoBackupFilesDir(), "wa_probe");
        BackupDecryptor.deleteDecrypted(new File(work, "msgstore.db"));
        BackupDecryptor.deleteDecrypted(new File(work, "increment.db"));
        ProbePayload.sweep(work); // increment payload, inflated output, extracted ZIP entries
        ProbeM2Run.sweepStale(this); // button 8's sample, once Taildrop has had time to read it
    }

    /** Buttons 4–8 share the decrypted-copy work dir, so only one runs at a time. */
    private void setRunning(boolean running) {
        runBackup.setEnabled(!running);
        runIncrement.setEnabled(!running);
        runFieldMap.setEnabled(!running);
        runProof.setEnabled(!running);
        runSample.setEnabled(!running);
    }

    private void runSampleExport() {
        setRunning(true);
        report.setText("Exporting a labelling sample… (decrypts the current full backup and reads its live increments)");
        new Thread(() -> {
            ProbeM2Run.Outcome o = ProbeM2Run.run(getApplicationContext());
            ProbeStore.saveM2Report(getApplicationContext(), o.report);
            runOnUiThread(() -> {
                setRunning(false);
                refresh();
                if (o.sample != null) shareSample(o.sample);
            });
        }, "wa-probe-m2").start();
    }

    /** The share sheet: Mike picks Tailscale and sends it to the Mac (Taildrop). Read grant only. */
    private void shareSample(File sample) {
        try {
            Uri uri = FileProvider.getUriForFile(this, getPackageName() + ".fileprovider", sample);
            Intent send = new Intent(Intent.ACTION_SEND)
                    .setType("application/octet-stream")
                    .putExtra(Intent.EXTRA_STREAM, uri)
                    .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION);
            send.setClipData(ClipData.newRawUri("", uri));
            startActivity(Intent.createChooser(send, "Send the labelling sample to the Mac (Tailscale)"));
        } catch (Exception e) {
            Toast.makeText(this, "Could not open the share sheet: " + e.getClass().getSimpleName(), Toast.LENGTH_LONG).show();
        }
    }

    private void runSetProof() {
        setRunning(true);
        report.setText("Reading the sets with the new reader… (decrypts the newest full backup and each set's base in turn)");
        new Thread(() -> {
            String r = ProbeProofRun.run(getApplicationContext());
            ProbeStore.saveProofReport(getApplicationContext(), r);
            runOnUiThread(() -> {
                setRunning(false);
                refresh();
            });
        }, "wa-probe-proof").start();
    }

    private void runFieldMapCounts() {
        setRunning(true);
        report.setText("Counting the field map… (decodes every increment, then decrypts the newest full backup and each set's base in turn)");
        new Thread(() -> {
            String r = ProbeFieldMapRun.run(getApplicationContext());
            ProbeStore.saveFieldMapReport(getApplicationContext(), r);
            runOnUiThread(() -> {
                setRunning(false);
                refresh();
            });
        }, "wa-probe-fieldmap").start();
    }

    private void runBackupProbe() {
        setRunning(true);
        report.setText("Running the backup probe… (waits 5 s to check WhatsApp is not writing, then decrypts)");
        new Thread(() -> {
            String r = ProbeBackup.run(getApplicationContext());
            ProbeStore.saveReport(getApplicationContext(), r);
            runOnUiThread(() -> {
                setRunning(false);
                refresh();
            });
        }, "wa-probe-backup").start();
    }

    private void runIncrementTest() {
        setRunning(true);
        report.setText("Trying the newest increment… (two 5 s write checks, then decrypts the increment and the newest full backup)");
        new Thread(() -> {
            String r = ProbeIncrement.run(getApplicationContext());
            ProbeStore.saveIncrementReport(getApplicationContext(), r);
            runOnUiThread(() -> {
                setRunning(false);
                refresh();
            });
        }, "wa-probe-increment").start();
    }

    private void confirmDelete() {
        new AlertDialog.Builder(this)
                .setTitle("Delete all probe data?")
                .setMessage("Removes the stored key and its Keystore key, everything the listener recorded, "
                        + "the saved reports and the labelling sample. Turn Notification access off in Settings as well.")
                .setPositiveButton("Delete", (dlg, w) -> {
                    try {
                        ProbeKeyVault.delete(this);
                    } catch (Exception e) {
                        Toast.makeText(this, "Key delete failed: " + e.getClass().getSimpleName(), Toast.LENGTH_LONG).show();
                    }
                    ProbeStore.deleteAll(this);
                    if (!ProbeM2Run.deleteSample(this)) {
                        Toast.makeText(this, "The labelling sample could not be deleted", Toast.LENGTH_LONG).show();
                    }
                    sweepDecrypted();
                    refresh();
                })
                .setNegativeButton("Cancel", null)
                .show();
    }
}
