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
for PERM in ACCESS_COARSE_LOCATION ACCESS_FINE_LOCATION RECORD_AUDIO INTERNET VIBRATE; do
    grep -q "android.permission.$PERM" "$MANIFEST" || MISSING="$MISSING $PERM"
done
if [ -n "$MISSING" ]; then
    echo "!!! MANIFEST IS MISSING PERMISSIONS:$MISSING" >&2
    echo "    It was probably regenerated (npx cap add android), which discards" >&2
    echo "    hand-added permissions. $MANIFEST is tracked in git for exactly this" >&2
    echo "    reason — restore it with 'git checkout -- $MANIFEST', then rebuild." >&2
    exit 1
fi
echo "Verified: manifest declares location, mic, internet and vibrate permissions."

echo "Verified: $APK's bundled index.html matches $SOURCE."
