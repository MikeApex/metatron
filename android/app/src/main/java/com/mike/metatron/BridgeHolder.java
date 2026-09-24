package com.mike.metatron;

import android.os.Handler;
import android.os.Looper;
import android.webkit.ValueCallback;
import android.webkit.WebView;

import java.lang.ref.WeakReference;

/**
 * The one way MetatronHeadsetService can reach the page.
 *
 * A Service has no getBridge() — that is a BridgeActivity method — so the media-button
 * callback has no route to the WebView on its own. MainActivity registers itself here on
 * create and clears it on destroy; the service asks for the WebView and gets null when
 * there isn't one.
 *
 * A WeakReference, not a strong one: a static field holding an Activity for the life of
 * the process is the textbook leak, and the whole point of this class is to be consulted
 * long after the Activity may have gone.
 *
 * A Binder was the alternative and buys nothing here — one nullable reference, one
 * process, no IPC boundary to cross.
 */
final class BridgeHolder {

    private static WeakReference<MainActivity> sActivity = new WeakReference<>(null);
    private static final Handler MAIN = new Handler(Looper.getMainLooper());

    private BridgeHolder() {}

    static void register(MainActivity activity) {
        sActivity = new WeakReference<>(activity);
    }

    /**
     * @return true if this Activity was still the registered one. The caller uses that
     *         to decide whether to stop the service: a late onDestroy from an OUTGOING
     *         Activity must not take down a service the incoming page just armed.
     */
    static boolean clear(MainActivity activity) {
        // Only clear if it is still ours. Two Activity instances can overlap briefly
        // during a relaunch, and a late onDestroy from the outgoing one would otherwise
        // wipe the incoming one's registration — leaving a live page unreachable.
        if (sActivity.get() == activity) {
            sActivity = new WeakReference<>(null);
            return true;
        }
        return false;
    }

    /**
     * Run an expression in the page and report whether it actually reached a live page.
     *
     * The result is NOT the boolean return of this method. evaluateJavascript is
     * asynchronous, so a synchronous return can only ever say "there was an Activity
     * reference" — which is true of a destroyed or blank WebView too, and reporting that
     * as "press handled" is how the button goes inert under a notification that says it
     * is listening. So the expression's own result is read back through a ValueCallback
     * and handed to {@code onResult}: "true" means the page ran it.
     *
     * @param js       an expression that evaluates to true when the page handled it
     * @param onResult called with the verdict, on the main thread; never called if no
     *                 Activity reference exists at all (the method returns false then)
     * @return false if there is no live Activity — the fast path, no callback
     */
    static boolean evaluate(final String js, final Consumer onResult) {
        final MainActivity activity = sActivity.get();
        if (activity == null || activity.isFinishing() || activity.isDestroyed()) {
            return false;
        }
        MAIN.post(new Runnable() {
            @Override
            public void run() {
                try {
                    WebView view = activity.getBridge().getWebView();
                    if (view == null) {
                        if (onResult != null) onResult.accept(false);
                        return;
                    }
                    view.evaluateJavascript(js, new ValueCallback<String>() {
                        @Override
                        public void onReceiveValue(String value) {
                            // "true" only if the page's own handler said so. A blank or
                            // half-loaded page returns "null" here, which is precisely
                            // the case a synchronous return could never see.
                            if (onResult != null) onResult.accept("true".equals(value));
                        }
                    });
                } catch (Exception e) {
                    // The Activity died between the null check and this post.
                    if (onResult != null) onResult.accept(false);
                }
            }
        });
        return true;
    }

    /** Minimal callback — java.util.function.Consumer needs API 24+ desugaring. */
    interface Consumer {
        void accept(boolean handled);
    }
}
