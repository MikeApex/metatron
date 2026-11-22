Model: Opus 5.5 — clean-room Android code with a hook change every session runs; it must never read a crypt implementation (W9).

# WhatsApp Phase 0 — the probe build (clean-room; no Mike steps)

Run **item 1 only** of `archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`
— read that whole prompt first, including its clean-room rules (1–4), which bind this session.
A separate walkthrough session (`archive/handoffs/2026-11-22-whatsapp-phase-0-mike-walkthrough-prompt.md`)
runs Mike's steps and the rulings in parallel; **do not walk Mike through anything, and do not
edit the WhatsApp plan or record rulings** — that session owns them.

**Order, binding:**
1. **Your first edit is the hook fence** (item 1, first bullet) in `scripts/hook_context_gate.py`
   `_log_hits`: skip `2026-10-26-04-whatsapp-input-explored-planned-phase-0a.md` and any fragment
   whose first heading says "reference-reading" — filename and heading only, never a mention of
   WhatsApp. Its test case includes a passing-mention fragment that must still be shown. The
   walkthrough session waits for this before its own first edit, so do it first and tell Mike
   when it is in the working tree.
2. The probe update (item 1, remaining bullets): `rx` receipt time, the 72-hour per-event list,
   the **"5. Try newest increment"** button — `src/waprobe/` only, `BackupLocator.newest`
   unchanged.
3. Tests: plain-Java helper, `src/testWaprobe/` admitted in `.gitignore`,
   `./gradlew :app:testWaprobeUnitTest --tests 'com.mike.metatron.whatsapp.*'`, then
   `testDebugUnitTest` — the 19 reader tests must still pass (`JAVA_HOME` = Homebrew openjdk@21).
4. `./gradlew assembleWaprobe` — tell Mike the APK path; he installs it in the walkthrough session.

**Nothing is committed, pushed or deployed** — the WhatsApp tree stays uncommitted for Mike's
review, as before. Fable diff review of the hook change before Mike installs (it runs for every
session in every area). Close with `/archive`; the log fragment's title says **"clean-room"**
(clean-room rule 2).

**Budget:** ~0.3–0.5M Opus tokens plus a small Fable diff review; Mike's time: none. Run cost:
none — throwaway probe; the hook adds one set lookup and one heading check per fragment.
