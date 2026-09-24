#!/bin/bash
# scripts/check_apk_sync.sh — DB-0809-18. Fail loudly if the built APK's bundled
# index.html has drifted from static/index.html, instead of a silent app-side bug
# report of ambiguous origin (was the shipped code even under test?).
#
# Modeled on deploy.sh's HEAD assertion: compute expected state, check actual
# state, exit non-zero with a loud message on mismatch, one clean "Verified" line
# on success. Checks the ACTUAL built APK, not the intermediate
# android/app/src/main/assets/public/ copy step — that copy can be current while
# an older, un-rebuilt APK sits in outputs/, which is the exact ambiguity this
# guards against.
#
# Usage: run after ./gradlew assembleDebug, before sideloading.
#   ./scripts/check_apk_sync.sh
set -euo pipefail
cd "$(dirname "$0")/.."

APK="android/app/build/outputs/apk/debug/app-debug.apk"
SOURCE="static/index.html"

if [ ! -f "$APK" ]; then
    echo "!!! No APK found at $APK — build one first (npx cap sync android && cd android && ./gradlew assembleDebug)." >&2
    exit 1
fi

BUNDLED=$(mktemp)
trap 'rm -f "$BUNDLED"' EXIT
unzip -p "$APK" assets/public/index.html > "$BUNDLED" 2>/dev/null || {
    echo "!!! Could not extract assets/public/index.html from $APK — is it a Capacitor build?" >&2
    exit 1
}

if ! diff -q "$SOURCE" "$BUNDLED" > /dev/null 2>&1; then
    echo "!!! APK DRIFT — $APK's bundled index.html does not match $SOURCE." >&2
    echo "    The APK was built before the last change to static/index.html, or" >&2
    echo "    'npx cap sync android' was skipped. Diff:" >&2
    diff "$SOURCE" "$BUNDLED" >&2 || true
    echo "    Rebuild: npx cap sync android && cd android && ./gradlew assembleDebug" >&2
    exit 1
fi

# ── Permissions the app cannot work without ──────────────────────────────────
# Asserted on the MANIFEST SOURCE, because regeneration is the failure being caught:
# `npx cap add android` rewrites this file with its default four permissions, and
# .gitignore's own comment tells people to run it. Location then dies at the OS level
# with no permission prompt and no error — the app says "could not get a location fix",
# which reads as a GPS problem and is not one. Found 2026-09-04 by the first real ping
# [DB-0815-12], a week after the feature was called shipped.
#
# Checked here rather than in the built APK on purpose: an aapt2 read is a second
# toolchain dependency that behaves differently under `set -euo pipefail`, and the
# manifest is the thing that gets destroyed. Fix the source, rebuild, and the APK follows.
MANIFEST="android/app/src/main/AndroidManifest.xml"
if [ ! -f "$MANIFEST" ]; then
    echo "!!! $MANIFEST is missing — the Android project was removed or never generated." >&2
    exit 1
fi
MISSING=""
for PERM in ACCESS_COARSE_LOCATION ACCESS_FINE_LOCATION RECORD_AUDIO INTERNET VIBRATE \
            FOREGROUND_SERVICE FOREGROUND_SERVICE_MEDIA_PLAYBACK \
            FOREGROUND_SERVICE_MICROPHONE POST_NOTIFICATIONS; do
    grep -q "android.permission.$PERM" "$MANIFEST" || MISSING="$MISSING $PERM"
done
if [ -n "$MISSING" ]; then
    echo "!!! MANIFEST IS MISSING PERMISSIONS:$MISSING" >&2
    echo "    It was probably regenerated (npx cap add android), which discards" >&2
    echo "    hand-added permissions. $MANIFEST is tracked in git for exactly this" >&2
    echo "    reason — restore it with 'git checkout -- $MANIFEST', then rebuild." >&2
    exit 1
fi

# The <service> element, checked separately because the loop above only sees
# <uses-permission> lines — and the same regeneration discards both. An undeclared
# service makes startForegroundService log "Unable to start service Intent" and
# return: arming appears to succeed, no notification appears, the headset button is
# inert, and this script prints "Verified". That is the same silent-failure class the
# permission loop was written for, in the component it does not cover.
if ! grep -q 'android:name=".MetatronHeadsetService"' "$MANIFEST"; then
    echo "!!! MANIFEST IS MISSING THE <service> ELEMENT for MetatronHeadsetService." >&2
    echo "    Headset mode will arm silently and do nothing: startForegroundService" >&2
    echo "    against an undeclared service logs and returns, with no error in the app." >&2
    echo "    Restore with 'git checkout -- $MANIFEST', then rebuild." >&2
    exit 1
fi
if ! grep -q 'foregroundServiceType="mediaPlayback|microphone"' "$MANIFEST"; then
    echo "!!! MetatronHeadsetService is missing foregroundServiceType=\"mediaPlayback|microphone\"." >&2
    echo "    Without the microphone type, Android 11+ silences mic capture whenever the" >&2
    echo "    app is not in the foreground — every pocket turn records silence and is" >&2
    echo "    reported as 'No speech detected'. The feature fails only where it matters." >&2
    exit 1
fi

# The Java sources, which were untracked until 2026-09-19 and are the other half of
# this feature. A regenerated android/ project drops them with no diff to show it.
for SRC in MainActivity.java BridgeHolder.java MetatronHeadsetService.java; do
    [ -f "android/app/src/main/java/com/mike/metatron/$SRC" ] || {
        echo "!!! MISSING android/app/src/main/java/com/mike/metatron/$SRC" >&2
        echo "    The Android project was regenerated. These files ARE tracked in git" >&2
        echo "    (.gitignore carve-out) — restore with 'git checkout -- android/'." >&2
        exit 1
    }
done

echo "Verified: manifest declares location, mic, internet, vibrate and headset-service"
echo "          permissions; the <service> element and its type are present; all three"
echo "          Java sources exist."

echo "Verified: $APK's bundled index.html matches $SOURCE."
