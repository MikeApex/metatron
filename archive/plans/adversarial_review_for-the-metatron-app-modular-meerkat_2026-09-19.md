# Adversarial review — for-the-metatron-app-modular-meerkat.md (headset button → talk to Metatron)
Model: fable · Effort: medium · Date: 2026-09-19 · Plan reviewed: /Users/md-homefolder/.claude/plans/for-the-metatron-app-modular-meerkat.md

## STRUCTURAL

1. [§ Five things #0, § Step 1 "Recover the reply", § Verification 7] [core/server.py:796 `history` send; static/index.html:1645 `renderHistory`; static/index.html:1454 `onclose`]
Wrong: The premise that a reply landing on a dead socket is "unrecoverable without a page reload" is false — every reconnect already receives a full `history` frame and `renderHistory` wipes and rebuilds the conversation because `onclose` has nulled `ownBubble`, so a stored reply is rendered today and the `[Connection lost]` bubble is a detached node before any `catchup` row arrives.
Fails: The planned `applyCatchupRow` orphan branch writes into a DOM node `renderHistory` already discarded, and the genuinely lost case — the reply completing *after* reconnect — is delivered by `done`/`message` frames to an exchange id the plan has just deleted from `shownIds`, which the catch-up branch never sees, so the fix targets the wrong path in both cases and the dedupe rule is modified for nothing.
Costs: Step 1's most expensive component ships as dead code, verification 7 passes on the stored-reply case by the existing `history` mechanism rather than the plan's, and the in-flight case stays silent in the pocket — high.

2. [§ Step 1 "Armed state is deliberately NOT persisted", § Step 2a "No `isArmed()`", § Step 4 memory-pressure rule] [android/app/src/main/AndroidManifest.xml:16 `launchMode="singleTask"`; MainActivity.java:17 `onCreate`]
Wrong: The invariant the design rests on — "every path that destroys the service also destroys the page" — is the inverse of the one needed; the Activity can be destroyed under memory pressure and relaunched (launcher, notification tap) *before* any press, giving a fresh page whose mirror flag starts false while the service, session and "Metatron is listening" notification are all still live.
Fails: The next press reaches a live `WeakReference`, calls `__metatronHeadsetButton()` on a page that "returns immediately unless armed", and the null-reference disarm rule never fires — the exact state the plan says the notification makes impossible, with no `isArmed()` query to reconcile it by design.
Costs: Silent inert button under a notification that says listening, on the pocket path the feature exists for, and the fix changes who owns armed state across Steps 1, 2a and 4 — high.

## LOCAL

3. [§ Step 1 "120s hard cap", § Costs "Unseen"] [static/index.html:1856 empty-transcript guard; core/server.py:1433 `_transcribe`]
Wrong: The cap "stops, sends" — so with the silence auto-stop disabled while armed, an accidental pocket press that never gets a second press becomes a guaranteed 120-second Whisper job and, because pocket noise is not an empty transcript, very often a full pipeline turn.
Fails: The empty-transcript guard the Costs section counts as control #3 only catches silence, and the cap converts the one stray-press case arming cannot prevent into the most expensive possible send instead of a discard.
Costs: Each unattended press is ~26k input tokens plus two minutes of VM Whisper, and the plan names the cap's duration without naming this cost beside it — medium.

4. [§ Step 0 probe 2, § Step 4 "Doze is a separate limit"] [static/index.html:1476-1492 backgrounded-socket comment and unconditional `ensureConnected` interval]
Wrong: The plan asserts a foreground service is not an exemption from Doze's network suspension; Android's network policy treats a UID holding a foreground service as foreground for the idle/restrict-power rule, so the Step 4 service is expected to keep the socket and the `/transcribe` and `/tts` fetches alive where the plan says it cannot.
Fails: Probe 2 is explicitly designed to refuse a before/after reading, so the plan cannot learn that Step 4 changes the socket's survival, and Step 1's catch-up speech is promoted to "the real mitigation" on a model the code's own comment (WebView frozen while backgrounded, a cached-process behaviour the service also lifts) does not support.
Costs: Misattributed probe results and a Doze mitigation built where the service already covers it, while the in-flight case from finding 1 stays unaddressed — medium.

5. [§ Step 4 "Add all four to the permission allowlist"] [scripts/check_apk_sync.sh:59 permission loop; android/app/src/main/AndroidManifest.xml:11-22]
Wrong: The guard extension covers the four new `<uses-permission>` lines but not the hand-added `<service>` element, which the same `npx cap add android` regeneration the guard exists for also discards.
Fails: `startForegroundService` against an undeclared service logs "Unable to start service Intent" and returns; arming appears to succeed, no notification appears, the button is inert, and the guard prints "Verified".
Costs: A regenerated manifest reproduces the exact silent-failure class the plan cites as costing a week, in the one component the plan added and left unguarded — medium.

## VERIFY — 2026-09-19 (revision claimed to close findings 1–5)

1. CHANGED — [static/index.html:1645 `renderHistory`; core/server.py:388 `_get_recent_exchanges`; core/server.py:956 `message` broadcast `exclude=websocket`] The premise is now correct and case (b) is deliverable (the dead socket's handler stays in its send loop, saves, and broadcasts `message` to the reconnected socket, which the de-listed orphan id lets through), but the `renderHistory` half is specified as "speaks the newest own-exchange reply" and history rows carry no own-marker (`id, exchange_id, user, assistant, ts, attachments, proactive`), so unless it is keyed on the same orphan id — which the plan reserves "for the narrower case" — it will speak a foreign or proactive reply on every armed reconnect.

2. CLOSED — [android/app/src/main/java/com/mike/metatron/MainActivity.java:13 `MainActivity extends BridgeActivity` (no `onDestroy` today); AndroidManifest.xml:12 `configChanges`] An Activity destroyed to reclaim memory while the process lives is finished normally, so an `onDestroy` override that stops the service closes the relaunch window; rotation is genuinely covered by the existing `configChanges` list.

3. CLOSED — [static/index.html:1829 `mediaRecorder.onstop` (POSTs `/transcribe` unconditionally); static/index.html:1775 `SILENCE_MS`] The cap now discards, and verification 3 checks the server log for the absent `/transcribe` request, which is the only observable that distinguishes discard from send given `onstop` posts today.

4. CLOSED — [static/index.html:1476-1492 backgrounded-socket comment and unconditional `ensureConnected` interval] Probe 2 is now a before/after measurement of Step 4, and the speech fix is justified on the verified fact that neither `renderHistory` nor `applyCatchupRow` calls `speakResponse`, independent of Doze.

5. CLOSED — [scripts/check_apk_sync.sh:59 permission loop; AndroidManifest.xml:11-22] The `<service>` element assertion is now in scope of the guard extension alongside the four permissions.

## STRUCTURAL
none

## LOCAL

6. [§ Step 4 "Memory pressure is handled at the destruction", § Costs "What deletes it"] [android/app/src/main/AndroidManifest.xml:11 (the `<service>` to be added); `android.app.Service.onStartCommand` default return `START_STICKY`]
Wrong: The plan enumerates three destruction paths but never names the service's restart flag, and a `Service` whose `onStartCommand` is not overridden returns `START_STICKY`, so a process killed under memory pressure has the service restarted by the system into a process with no Activity and no page.
Fails: On Android 14+ the restarted service's `startForeground` with type `microphone` from the background throws `ForegroundServiceStartNotAllowedException` and crashes the app; on older versions it comes up as a live "Metatron is listening" notification over nothing — the finding-2 state through the one door `onDestroy` cannot close, because `onDestroy` never runs on process death.
Costs: Either a visible crash or the exact silent lying-notification state the revision was made to eliminate, reachable on any low-memory day — medium.

## VERIFY — 2026-09-19, round two (revision claimed to close findings 1 and 6)

1. CLOSED — [static/index.html:1632 `applyCatchupRow` / :1645 `renderHistory`; core/server.py:388-399 `_get_recent_exchanges` column list; core/server.py:956 `message` broadcast] Both speech paths are now keyed on the single `orphanedOwnId` set in `onclose`, which is the only origin marker the row shape allows, and verification 7(c) is the negative case that fails a "newest reply" key.

6. CLOSED — [android/app/src/main/AndroidManifest.xml:11-22 (the `<service>` to be added beside the Activity); `Service.onStartCommand` default `START_STICKY`] `onStartCommand` returning `START_NOT_STICKY` is now a named requirement with its rationale, listed as the fourth destruction path and in the Run-cost "what deletes it" line.

## STRUCTURAL
none

## LOCAL

7. [§ Verification 12 "kill the whole process (`adb shell am kill com.mike.metatron`)"] [android/app/src/main/AndroidManifest.xml:11-22; the foreground `<service>` Step 4 adds]
Wrong: `am kill` only kills processes the system deems safe to kill, and a process hosting a foreground service is not one, so the command is a no-op against an armed app.
Fails: The test observes "no notification reappears" because nothing was killed, and the `START_NOT_STICKY` check passes whether or not the flag was set; `am force-stop` would kill it but also cancels any restart regardless of flag, so neither command exercises the path.
Costs: The one verification step added for finding 6 cannot fail, leaving the restart flag unverified on the device where a wrong default crashes the app — medium.

## VERIFY — 2026-09-19, round three (revision claimed to close finding 7)

7. CLOSED — [android/app/src/main/AndroidManifest.xml:11-22 (host of the `<service>` Step 4 adds); `MetatronHeadsetService.onStartCommand` return value, the line the plan now names as the check] `am crash` is an abnormal termination Android performs on a foreground-service process and does leave a sticky restart possible, and the plan additionally states the device run only surfaces the Android 14+ crash while the flag itself is confirmed by reading the `START_NOT_STICKY` return — the criterion can now fail.

## STRUCTURAL
none

## LOCAL
none
