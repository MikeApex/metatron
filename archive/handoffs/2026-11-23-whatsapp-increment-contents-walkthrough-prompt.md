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

## Then

Record the shapes in plan § 4 under INCREMENTS RULED and write the log fragment. Its first heading
says **"clean-room"** and never the other phrase: the hook's match fails closed. Then write the
prompt for the **reader extension (P3)**: which increments to read, how they combine with the full
backup, a synthetic fixture built from the observed shapes, `src/main/` + `src/test/` (the 19 tests
grow). Estimate ~0.5–1M Opus tokens, clean-room. Close with `/archive`.

**Budget:** ~0.1M Opus tokens; Mike ~5 minutes. Run cost: none — throwaway probe.
