package com.mike.metatron;

import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.content.pm.ServiceInfo;
import android.media.AudioAttributes;
import android.media.AudioFormat;
import android.media.AudioManager;
import android.media.AudioTrack;
import android.media.session.MediaSession;
import android.media.session.PlaybackState;
import android.os.Build;
import android.os.IBinder;
import android.view.KeyEvent;

/**
 * Holds the media session that receives the headset button, for exactly as long as the
 * user has armed headset mode in the page.
 *
 * Why a foreground service rather than something in MainActivity: without one, Android
 * silences microphone capture for an app that is not in the foreground, so a press with
 * the screen locked would record two minutes of nothing and the empty-transcript guard
 * would file it as "No speech detected" — a clean-looking no-op on the one case the
 * feature exists for. The service type therefore declares BOTH mediaPlayback (for the
 * session) and microphone (for the capture).
 */
public class MetatronHeadsetService extends Service {

    static final String ACTION_ARM = "com.mike.metatron.ARM";
    static final String ACTION_DISARM = "com.mike.metatron.DISARM";

    private static final String CHANNEL_ID = "metatron_headset";
    private static final int NOTIFICATION_ID = 0x4D54;  // "MT"

    private MediaSession session;
    private AudioTrack silence;

    @Override
    public void onCreate() {
        super.onCreate();
        createChannel();
        startSilentLoop();
        startSession();
    }

    @Override
    public int onStartCommand(Intent intent, int flags, int startId) {
        if (intent != null && ACTION_DISARM.equals(intent.getAction())) {
            // The notification's Stop action. Tell the page first — it owns the mirror
            // flag and the spoken-reply override — then take ourselves down.
            BridgeHolder.evaluate(
                    "window.__metatronDisarm && window.__metatronDisarm()", null);
            stopSelf();
            return START_NOT_STICKY;
        }

        startForegroundCompat();

        // START_NOT_STICKY, and this is load-bearing rather than a default worth leaving
        // alone. The default is START_STICKY, under which a process killed for memory has
        // this service restarted by the system into a process with NO Activity and NO
        // page — and onDestroy never runs on a process death, so the lifecycle rule in
        // MainActivity cannot catch it. On Android 14+ the restarted service's
        // startForeground with type microphone throws ForegroundServiceStartNotAllowedException
        // from the background and takes the app down; on older versions it comes up as a
        // live "Metatron is listening" notification over nothing at all.
        //
        // This service is worth running only while the user has armed it. A restart
        // without them is not a restart worth having.
        return START_NOT_STICKY;
    }

    @Override
    public void onTaskRemoved(Intent rootIntent) {
        // Swiped away from recents. The Activity is finished and the WebView is gone, and
        // the service cannot bring either back: background activity launches are blocked
        // from API 29 and a foreground service is not an exemption, so startActivity here
        // would be denied and logged and show the user nothing.
        //
        // So swipe-away disarms. The notification disappearing is how you know.
        stopSelf();
        super.onTaskRemoved(rootIntent);
    }

    @Override
    public IBinder onBind(Intent intent) {
        return null;
    }

    @Override
    public void onDestroy() {
        if (session != null) {
            session.setActive(false);
            session.release();
            session = null;
        }
        stopSilentLoop();
        super.onDestroy();
    }

    // ------------------------------------------------------------------
    // Media session
    // ------------------------------------------------------------------

    private void startSession() {
        session = new MediaSession(this, "Metatron");
        session.setFlags(MediaSession.FLAG_HANDLES_MEDIA_BUTTONS
                | MediaSession.FLAG_HANDLES_TRANSPORT_CONTROLS);
        session.setCallback(new MediaSession.Callback() {
            @Override
            public boolean onMediaButtonEvent(Intent mediaButtonIntent) {
                KeyEvent event = mediaButtonIntent.getParcelableExtra(Intent.EXTRA_KEY_EVENT);
                // Act on the down edge only. Bluetooth stacks deliver down and up as two
                // events; the page debounces as well, but not sending the second one is
                // cheaper than relying on that alone.
                if (event != null && event.getAction() == KeyEvent.ACTION_DOWN) {
                    press();
                }
                return true;
            }

            @Override
            public void onPlay() { press(); }

            @Override
            public void onPause() { press(); }

            @Override
            public void onStop() { press(); }
        });

        // STATE_PLAYING backed by a track that is genuinely playing, not a pose. Android
        // routes the media button to the MOST RECENTLY PLAYING session, so a session that
        // is merely active loses the button to whatever app played last and arming would
        // appear to do nothing at all.
        session.setPlaybackState(new PlaybackState.Builder()
                .setActions(PlaybackState.ACTION_PLAY_PAUSE
                        | PlaybackState.ACTION_PLAY
                        | PlaybackState.ACTION_PAUSE
                        | PlaybackState.ACTION_STOP)
                .setState(PlaybackState.STATE_PLAYING, 0, 1.0f)
                .build());
        session.setActive(true);
    }

    private void press() {
        // The expression returns true only if the page's handler actually ran. Anything
        // else — no Activity, a destroyed WebView, a blank or half-loaded page — is a
        // press that went nowhere, and it must take the service down rather than be
        // swallowed. An inert button under a notification that says "listening" is the
        // exact state this design exists to prevent.
        boolean haveActivity = BridgeHolder.evaluate(
                "!!(window.__metatronHeadsetButton && window.__metatronHeadsetButton())",
                new BridgeHolder.Consumer() {
                    @Override
                    public void accept(boolean handled) {
                        if (!handled) stopSelf();
                    }
                });
        if (!haveActivity) {
            stopSelf();
        }
    }

    // ------------------------------------------------------------------
    // Silent loop — what makes the session win media-button arbitration
    // ------------------------------------------------------------------

    private void startSilentLoop() {
        try {
            int rate = 8000;
            int frames = rate / 10;            // 100ms of silence, looped
            byte[] quiet = new byte[frames * 2];  // 16-bit mono, all zeroes

            silence = new AudioTrack(
                    new AudioAttributes.Builder()
                            .setUsage(AudioAttributes.USAGE_MEDIA)
                            .setContentType(AudioAttributes.CONTENT_TYPE_MUSIC)
                            .build(),
                    new AudioFormat.Builder()
                            .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                            .setSampleRate(rate)
                            .setChannelMask(AudioFormat.CHANNEL_OUT_MONO)
                            .build(),
                    quiet.length,
                    AudioTrack.MODE_STATIC,
                    AudioManager.AUDIO_SESSION_ID_GENERATE);

            silence.write(quiet, 0, quiet.length);
            silence.setLoopPoints(0, frames, -1);   // -1 = forever

            // Deliberately NOT setVolume(0f). The buffer is already all zeroes, so the
            // track is inaudible on its own merits and the call bought nothing — while
            // a zero-volume track is exactly the kind of thing a platform may decline
            // to count as "playing". The whole purpose of this track is to win
            // most-recently-playing arbitration for the media button; anything that
            // might disqualify it defeats the point, and the failure would be silent.
            silence.play();
        } catch (Exception e) {
            // Not fatal: the session still exists and will receive the button whenever
            // nothing else has played more recently. Losing arbitration to a music app
            // is a documented trade, not a crash.
            silence = null;
        }
    }

    private void stopSilentLoop() {
        if (silence == null) return;
        try {
            silence.stop();
            silence.release();
        } catch (Exception ignored) {
        }
        silence = null;
    }

    // ------------------------------------------------------------------
    // Notification — which is also the disarm control
    // ------------------------------------------------------------------

    private void createChannel() {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) return;
        NotificationChannel channel = new NotificationChannel(
                CHANNEL_ID, "Headset mode", NotificationManager.IMPORTANCE_LOW);
        channel.setDescription("Shown while the headset button controls Metatron.");
        channel.setShowBadge(false);
        NotificationManager nm = getSystemService(NotificationManager.class);
        if (nm != null) nm.createNotificationChannel(channel);
    }

    private void startForegroundCompat() {
        Intent stop = new Intent(this, MetatronHeadsetService.class).setAction(ACTION_DISARM);
        PendingIntent stopPending = PendingIntent.getService(
                this, 0, stop,
                PendingIntent.FLAG_UPDATE_CURRENT
                        | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                           ? PendingIntent.FLAG_IMMUTABLE : 0));

        Intent open = new Intent(this, MainActivity.class)
                .setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent openPending = PendingIntent.getActivity(
                this, 0, open,
                PendingIntent.FLAG_UPDATE_CURRENT
                        | (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M
                           ? PendingIntent.FLAG_IMMUTABLE : 0));

        Notification.Builder b = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? new Notification.Builder(this, CHANNEL_ID)
                : new Notification.Builder(this);

        Notification notification = b
                .setContentTitle("Metatron is listening")
                .setContentText("Press your headset button to speak")
                .setSmallIcon(android.R.drawable.ic_btn_speak_now)
                .setOngoing(true)
                .setContentIntent(openPending)
                // The notification is the disarm control, not decoration. Android makes
                // us show one; making it the way out is free.
                .addAction(new Notification.Action.Builder(
                        null, "Stop", stopPending).build())
                .build();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(NOTIFICATION_ID, notification,
                    ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK
                            | ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE);
        } else {
            startForeground(NOTIFICATION_ID, notification);
        }
    }
}
