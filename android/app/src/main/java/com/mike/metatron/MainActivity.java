package com.mike.metatron;

import android.Manifest;
import android.content.Intent;
import android.media.AudioManager;
import android.media.ToneGenerator;
import android.os.Bundle;
import android.speech.tts.TextToSpeech;
import android.speech.tts.UtteranceProgressListener;

import java.util.Locale;
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

    // Spoken headset cues. A short synthetic beep arrives through SCO as a squelch —
    // SCO is a NARROWBAND VOICE codec, built to carry speech and poor at anything else,
    // so the channel mangles exactly the kind of sound a tone is. Speech is what it is
    // designed for, which is why the cue is a voice rather than a louder beep.
    private TextToSpeech tts;
    private volatile boolean ttsReady = false;

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

        // Initialised here because init is asynchronous and the first cue must not be
        // the one that waits for it.
        tts = new TextToSpeech(this, status -> {
            ttsReady = (status == TextToSpeech.SUCCESS);
            if (ttsReady) {
                tts.setLanguage(Locale.UK);
                tts.setOnUtteranceProgressListener(new UtteranceProgressListener() {
                    @Override public void onStart(String id) {}
                    @Override public void onError(String id) { cueFinished(); }
                    @Override public void onDone(String id) { cueFinished(); }
                });
            }
        });

        requestStartupPermissions();
    }

    /**
     * Tell the page the cue has finished speaking.
     *
     * The page waits for this before it starts the recorder, so the cue cannot be
     * captured by the microphone it is announcing. Without that ordering a bled-in
     * "I'm here" would set the silence detector's speechSeen flag, and a turn in which
     * the user said nothing would send itself carrying only the cue.
     */
    private void cueFinished() {
        BridgeHolder.evaluate("window.__metatronCueDone && window.__metatronCueDone()", null);
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
        if (tts != null) {
            try { tts.stop(); tts.shutdown(); } catch (Exception ignored) {}
            tts = null;
            ttsReady = false;
        }
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

        /**
         * Sound a headset cue on the stream the user is actually listening to.
         *
         * This exists because the page cannot do it. Web Audio plays on the MEDIA
         * stream, and the instant the mic opens Android moves a Bluetooth headset from
         * A2DP to SCO (call mode), which does not carry the media stream — so the
         * mic-open cue, the one that says "speak now", is inaudible on a headset every
         * single time. Measured 2026-09-24: the only sign the mic had opened was the
         * SCO hiss. STREAM_VOICE_CALL is the stream SCO does carry.
         *
         * The stream is chosen per call rather than fixed: when no headset is in call
         * mode, VOICE_CALL routes to the earpiece, which is far too quiet for a phone
         * in a pocket, so the media stream is right in that case.
         */
        @JavascriptInterface
        public void playCue(String kind) {
            AudioManager am = (AudioManager) getSystemService(AUDIO_SERVICE);
            boolean scoActive = false;
            try {
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
                    android.media.AudioDeviceInfo dev = am.getCommunicationDevice();
                    scoActive = dev != null
                            && dev.getType() == android.media.AudioDeviceInfo.TYPE_BLUETOOTH_SCO;
                } else {
                    scoActive = am.isBluetoothScoOn();
                }
            } catch (Exception ignored) {
            }

            int stream = scoActive ? AudioManager.STREAM_VOICE_CALL : AudioManager.STREAM_MUSIC;

            int tone;
            int ms;
            if ("sent".equals(kind)) {
                tone = ToneGenerator.TONE_PROP_ACK;   // two quick pips — turn sent
                ms = 200;
            } else if ("timeout".equals(kind)) {
                tone = ToneGenerator.TONE_SUP_ERROR;  // distinct low buzz — discarded
                ms = 350;
            } else {
                tone = ToneGenerator.TONE_PROP_BEEP;  // single beep — mic is live
                ms = 150;
            }

            String phrase;
            if ("sent".equals(kind)) {
                phrase = "Got it";
            } else if ("timeout".equals(kind)) {
                phrase = "Cancelled";
            } else {
                phrase = "I'm here";
            }

            if (ttsReady) {
                Bundle params = new Bundle();
                params.putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, stream);
                int r = tts.speak(phrase, TextToSpeech.QUEUE_FLUSH, params, "metatron-cue");
                if (r == TextToSpeech.SUCCESS) return;
            }

            // Fallback: the engine is missing or still initialising. A mangled beep is
            // better than no cue at all, and the page's timeout releases it either way.
            ToneGenerator tg = null;
            try {
                tg = new ToneGenerator(stream, 90);
                tg.startTone(tone, ms);
                final ToneGenerator finalTg = tg;
                getBridge().getWebView().postDelayed(() -> {
                    try { finalTg.release(); } catch (Exception ignored) {}
                    cueFinished();
                }, ms + 150);
            } catch (Exception e) {
                if (tg != null) { try { tg.release(); } catch (Exception ignored) {} }
                cueFinished();
            }
        }

        /**
         * When this APK was installed, so the page can prove which build is running.
         *
         * Sideloading publishes a COPY of the APK to a staging directory, and a rebuild
         * does not update that copy — so "reinstall and retest" can silently retest the
         * previous build. On 2026-09-24 that wasted a round of cue debugging. Reading
         * lastUpdateTime needs no build-time stamping and cannot drift from reality.
         */
        @JavascriptInterface
        public String buildStamp() {
            try {
                long t = getPackageManager()
                        .getPackageInfo(getPackageName(), 0).lastUpdateTime;
                return new java.text.SimpleDateFormat("d MMM HH:mm:ss", Locale.UK)
                        .format(new java.util.Date(t));
            } catch (Exception e) {
                return "unknown";
            }
        }

        @JavascriptInterface
        public void disarm() {
            stopService(new Intent(MainActivity.this, MetatronHeadsetService.class));
        }
    }
}
