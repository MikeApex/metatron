Model: Opus 5.5 — a short guided session with Mike plus reading a shapes-only report; it must never read a crypt implementation (W9).

# WhatsApp Phase 0 — install the increment-contents probe, tap 5, read what is inside (clean-room walkthrough)

**Clean-room rules 1–4 of `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`
bind in full:** open nothing in `archive/transcripts/`; WhatsApp log entries only
`2026-10-30-02-…` and fragments titled "clean-room"; nothing under `/private/tmp` outside your
scratchpad; no crypt implementation, no web. Read log § 11-23 second (the probe build) and plan
`archive/plans/whatsapp_input_plan_2026-10-26.md` § 4 INCREMENTS RULED.

## Mike's steps (~5 min)

1. **Serve the APK** from the Mac: `android/app/build/outputs/apk/waprobe/app-waprobe.apk`. First
   check `shasum -a 256` begins `e204b170582780d7` — if not, it was rebuilt; say so before serving.
   Serve it the way the 11-23 walkthrough did (log § 11-23 first).
2. Mike installs **over** the current probe — an update keeps notification access, the stored key
   and the events. Open **WA probe**; the status lines should still show access ON and the key stored.
3. Tap **5. Try newest increment** (waits ~10 s, then decrypts). Long-press the report → Select all
   → Share → **Tailscale** → the Mac (lands in `~/Downloads`).

## Read the report — shapes only

- `increment files in the folder:` how many of each form exist; `chosen:` is the live undated one
  unless a full backup ran overnight.
- `refusal branch:` — **ZIP (`decide()`)** or **inflated non-SQLite (`finish()`)**.
- **If ZIP:** the entries — names, sizes, which are SQLite — and for each SQLite entry the shape
  block: tables, `message`/`chat`/`jid` counts, min/max message time, ids also in the newest full
  backup, ids newer than it. These answer the design questions: does an increment hold only rows
  newer than the last full backup, do ids overlap, is it a whole database or a delta?
- **If inflated non-SQLite:** the size and first 16 bytes. If these match no format we can name
  without a reference, that is the case for a **narrowed Phase 0a′**. Write its prompt for a
  separate session (fragment titled "reference-reading"); **do not do 0a′ here.**
- `decrypted copies deleted: yes` must be the last line.

## Mike reviews and commits the WhatsApp code (~15 min, guided — agreed 11-23)

It has been uncommitted since 10-30; the reader extension should start from a clean base.
Walk Mike through the diff area by area and let him approve each before staging. Stage an
explicit list, never a glob, and **`git diff` every tracked file first**: two windows share this
tree, so lines another session wrote stop the commit.
1. The reader: `android/app/src/main/java/com/mike/metatron/whatsapp/` and its tests in
   `android/app/src/test/java/com/mike/metatron/whatsapp/`. Before staging, run
   `./gradlew :app:testDebugUnitTest --tests 'com.mike.metatron.whatsapp.*'`; 19 must pass.
2. The probe (throwaway, but committed so the record is whole): `android/app/src/waprobe/`,
   `android/app/src/testWaprobe/`, the `waprobe` build type in `android/app/build.gradle`.
3. `android/app/src/main/AndroidManifest.xml` (`allowBackup="false"`) and the `.gitignore`
   admissions. Show their diffs; they may carry other sessions' lines.
4. The hook fence: `scripts/hook_context_gate.py` + `tests/test_hook_context_gate_fence.py`.
Leave out what is not WhatsApp: `.claude/agents/build-inquiry.md`,
`archive/plans/inquiry_rewrite_2026-09-26.md`, the `2026-09-24-build-phase-*.patch` files.
`android/app/src/test/java/com/getcapacitor/myapp/ExampleUnitTest.java` is Capacitor boilerplate;
ask. Commit message without attribution lines; push; assert `HEAD` equals `origin/main`.

## Then

Record the shapes in plan § 4 under INCREMENTS RULED and write the log fragment. Its first heading
says **"clean-room"** and never the other phrase: the hook's match fails closed. Then write the
prompt for the **reader extension (P3)**: which increments to read, how they combine with the full
backup, a synthetic fixture built from the observed shapes, `src/main/` + `src/test/` (the 19 tests
grow). Estimate ~0.5–1M Opus tokens, clean-room. Close with `/archive`.

**Budget:** ~0.15M Opus tokens; Mike ~20 minutes (5 for the tap, 15 for the review). Run cost: none — throwaway probe.
