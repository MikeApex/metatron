### 2026-10-26 (the phone app's mic went silent for a day, and now says so instead of vanishing) — `24d5c24` — **committed; Mike deploys and sideloads the rebuilt APK**

**Outgoing handoff carried:** the day planner's Stage A (`45739a2`) still owes its deploy, the APK
and one ordinary day of watching the Plan panel; Stage B and the ritual-pause session are unchanged
and next. This session touched neither.

**The report (Mike):** in the APK, not the webapp, the record button worked but no transcript and no
trace of the recording followed.

**Diagnosed from the VM, not reasoned about.** The server keeps every clip and its transcript in
`data/audio/<date>/`. Phone clips (Opus, from `100.121.216.94`, with a CORS preflight) transcribed
normally through 2026-10-25 12:02 — on the APK built 10-24 19:52, the same one still installed.
From 12:26 that day every phone clip was **digital silence, -91 dB** (a 28 s clip was 6.8 KB);
Whisper returned `''`, and the client's `empty` branch deleted the snippet with only a transient
"No speech detected" status. The Mac's browser clips (AAC, `100.70.67.45`) at the same hour were
fine. The APK's bundled `index.html` was byte-identical to `static/index.html`, and the native code
forces no audio routing — so the cause was phone-side state. **A phone restart fixed it**; which
state it was (system mic block, another app holding the mic) was not identified.

**Built (`24d5c24`, `static/index.html` only):** the silence poller now records the peak level the
mic delivered (`micPeakRms`, counted only while the `AudioContext` is `running`, since a suspended
context also reads zero). A clip with ≥ 5 samples (~0.75 s) all under `MIC_DEAD_RMS = 0.01` is not
uploaded and stays in the tray as a failed snippet — "The microphone picked up nothing — check
microphone access, or close any app using the mic" — with the timeout tone in headset mode in place
of "sent". Mike asked for it even after the fix, so the next occurrence is seen.

**Rejected:** sending the dead clip anyway and labelling an empty transcript — it costs a Whisper
job for audio known to be silent, and an empty transcript cannot tell a dead mic from a quiet
speaker. **Unverified:** the 0.01 threshold against a real mic's noise floor with WebView noise
suppression on — reasoned from the dead clips (every bin zero), not measured on a live quiet room.
APK rebuilt and `check_apk_sync.sh` passed; served at `http://100.70.67.45:8888/app-debug.apk`.

