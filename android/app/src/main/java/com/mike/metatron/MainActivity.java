package com.mike.metatron;

import android.Manifest;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.os.Build;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;

import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.BridgeWebChromeClient;

public class MainActivity extends BridgeActivity {
    private static final int STARTUP_PERMISSION_REQUEST = 1;

    @Override
    public void onCreate(android.os.Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // How MetatronHeadsetService reaches this page. Registered before anything
        // else that could start the service.
        BridgeHolder.register(this);

        // Subclass Capacitor's own chrome client rather than replacing it.
        //
        // This used to install a bare `new WebChromeClient()`, which granted the mic
        // but silently discarded everything else Capacitor's client implements — in
        // particular onShowFileChooser, without which `<input type="file">` opens
        // nothing at all in the app. Attaching a photo was therefore impossible in the
        // APK while working fine in the browser.
        //
        // Only onPermissionRequest is overridden, and it keeps the immediate grant the
        // app has always had: the stock implementation routes an audio request through
        // a runtime-permission launcher first, and the mic path is not something to
        // change blind alongside an unrelated feature.
        getBridge().getWebView().setWebChromeClient(new BridgeWebChromeClient(getBridge()) {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                request.grant(request.getResources());
            }
        });

        // The page's only route to native code. The app ships zero Capacitor plugins
        // (capacitor.plugins.json is []), and a plugin would mean a Gradle module, a
        // registry entry and another thing `npx cap add android` can regenerate away —
        // for two methods.
        //
        // addJavascriptInterface exposes this object to any page in the WebView. That is
        // acceptable here and only here: this WebView loads bundled local assets, never
        // remote content.
        getBridge().getWebView().addJavascriptInterface(new HeadsetBridge(), "Metatron");

        requestStartupPermissions();
    }

    /**
     * Mic and (on Android 13+) notifications, asked for in ONE call.
     *
     * Two sequential requestPermissions calls do not queue: the second arrives while
     * the first dialog is showing and Android drops it silently. Written that way, the
     * notification permission was never actually requested on a first launch — and
     * without it the headset service runs invisibly, holding the media button with
     * nothing on screen to say so, which is the exact state the notification exists to
     * prevent.
     */
    private void requestStartupPermissions() {
        java.util.List<String> wanted = new java.util.ArrayList<>();

        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO)
                != PackageManager.PERMISSION_GRANTED) {
            wanted.add(Manifest.permission.RECORD_AUDIO);
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU
                && ContextCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS)
                   != PackageManager.PERMISSION_GRANTED) {
            wanted.add(Manifest.permission.POST_NOTIFICATIONS);
        }

        if (!wanted.isEmpty()) {
            ActivityCompat.requestPermissions(
                    this, wanted.toArray(new String[0]), STARTUP_PERMISSION_REQUEST);
        }
    }

    @Override
    public void onDestroy() {
        // The service must never outlive the page that armed it.
        //
        // The dangerous direction is not the obvious one. If the Activity is destroyed
        // for memory and the user relaunches from the launcher BEFORE pressing anything,
        // they get a fresh page whose headset flag starts false while the service, the
        // session and the "Metatron is listening" notification are all still live — a
        // button that does nothing under a notification claiming it works.
        //
        // Stopping the service here closes that window at the destruction rather than
        // waiting for a press to discover it. The service's own null-WebView check is a
        // backstop for the race, not the rule.
        // Guarded on the same condition as the registration, and for the same reason:
        // two Activity instances overlap briefly during a relaunch, and an outgoing
        // one's late onDestroy would otherwise stop a service the INCOMING page has
        // just armed — leaving 🎧 lit over a dead button, which is the state this
        // method exists to prevent rather than create.
        if (BridgeHolder.clear(this)) {
            stopService(new Intent(this, MetatronHeadsetService.class));
        }
        super.onDestroy();
    }

    /** Exposed to the page as `window.Metatron`. */
    public class HeadsetBridge {
        /** @return true if the service was started; false means headset mode is NOT live. */
        @JavascriptInterface
        public boolean arm() {
            // A microphone-typed foreground service without RECORD_AUDIO granted makes
            // startForeground throw SecurityException — on the service's main thread,
            // where nothing on the JS side can catch it, so tapping 🎧 after declining
            // the mic would take the whole app down. Refuse here instead, and let the
            // page say so.
            if (ContextCompat.checkSelfPermission(MainActivity.this, Manifest.permission.RECORD_AUDIO)
                    != PackageManager.PERMISSION_GRANTED) {
                requestStartupPermissions();
                return false;
            }

            Intent intent = new Intent(MainActivity.this, MetatronHeadsetService.class)
                    .setAction(MetatronHeadsetService.ACTION_ARM);
            // Started from the Activity while it is visible, which is not incidental:
            // from Android 14 a microphone-type foreground service may only be STARTED
            // while the app is visible. Arming is a tap in the page, so it always is —
            // and that is why the service can never be started from the background.
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                startForegroundService(intent);
            } else {
                startService(intent);
            }
            return true;
        }

        @JavascriptInterface
        public void disarm() {
            stopService(new Intent(MainActivity.this, MetatronHeadsetService.class));
        }
    }
}
