### 2026-11-22, third (clean-room — WhatsApp Phase 0 close-out prompt Fable-reviewed over four rounds and split into a build session and Mike's walkthrough) — no code, nothing deployed

**Incoming handoff:** `SESSION.md` § WhatsApp — next was
`archive/handoffs/2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt.md`, never run.
Mike asked for a Fable review before anything was built. This session read no crypt
implementation, no transcript and no reference-reading log fragment — it is **clean-room**.

**What changed and why.** `/adversarial-review` (Fable, medium) found 1 structural + 3 local;
four verify rounds closed all six, the last returning nothing new. Report, verbatim with every
round: `archive/plans/adversarial_review_2026-10-31-whatsapp-phase-0-close-survival-lm-increments-prompt_2026-11-22.md`.
The prompt was revised in place (header note names the review):
- **Increments option (a) may not exist** — nothing shows the reference covers increment files,
  and how an increment combines with a full backup may be database behaviour no decryptor holds.
  So an **increment test comes first**: a throwaway probe button runs the existing reader on the
  newest increment (`BackupDecryptor.decrypt` takes any `File`). Decrypts → no reference session;
  fails → a narrowed 0a′ whose gating question is "does the reference handle increments at all".
- **Option (b) is loss, not lag** — the 72-hour sent-key list (`ProbeStore.KEEP_MS`, plan § 6)
  means a backup copy arriving later is dropped as a duplicate: no group sender, no edits,
  answered questions re-surface. The full-backup cadence is one unforced sample (10-22).
- **The survival read could not fail** — a silent night reads the same dead or quiet; a killed
  process writes no `disconnected` mark; the probe shares Metatron's app. Now a **planted-message
  test**, after a probe update that records receipt time (`rx`) and lists every event.
- **The clean-room fence** became an allowlist (no transcripts at all; only the 10-30-02 fragment
  and later "clean-room" fragments), `/private/tmp` deletion is Mike's step 0, and the edit-time
  hook (`_log_hits`) will skip session 1's fragment by filename plus any "reference-reading"
  heading. **Every WhatsApp session now titles its fragment "clean-room" or "reference-reading".**

**Believed earlier, wrong:** (1) that the probe report could show whether a given message was
caught — it prints no per-event times, and `post` is WhatsApp's post time; (2) my own first hook
fence ("skip any fragment mentioning WhatsApp") — it would have silently dropped four unrelated
fragments, incl. the whole-codebase review and its fixes, from every briefing, permanently;
(3) my first test spec — probe tests in `src/test/` break the debug compile and the 19 reader
tests; `org.json` is a JVM stub. All three corrected before handoff.

**Rejected:** turning off Metatron's pushes for the survival night (the real listener lives in
the same app and gets them; a push-clear window instead); one combined session (Mike wanted his
25 minutes as its own block).

**Outgoing:** two prompts — `archive/handoffs/2026-11-22-whatsapp-phase-0-probe-build-prompt.md`
(Opus; hook fence first, probe update, tests, APK; no Mike steps) and
`archive/handoffs/2026-11-22-whatsapp-phase-0-mike-walkthrough-prompt.md` (Opus; items 0, 2–5 and
both rulings; makes no edit until the fence is in the working tree). The WhatsApp code tree stays
uncommitted for Mike's review.

