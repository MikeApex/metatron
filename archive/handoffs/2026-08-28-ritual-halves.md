# Handoff — ritual code halves [DB-0809-02] build outcome (2026-08-28)

*From the Green/Amber spinoff chat (Fable review, Opus worker). Merged `6451b51`. VM deploy
owed (Mike) — `core/orchestrator.py` + `tools/context_tracker.py`.*

## What now happens differently

A scheduled run with nothing new says little; a question the tool already asked is not asked
again by the next job; a ritual belongs to the job that owns it. All three are computed in
Python and injected — none relies on the Synthesizer following an instruction it already had
and ignored.

1. **Asked-state memory** — `asked_questions` in the persona's `context.json` (0600, same
   lifecycle as threads, everything server-stamped, archived never deleted). Questions are
   extracted from a scheduled run's delivered reply; a user turn that engages one clears it
   (reuses `_user_engages_thread`). The verbatim question text is **withheld from the model**
   — it cannot recite what it never receives. Thresholds (named constants, reasoned not
   measured): re-ask interval 20h, max 3 asks per question, **max 1 re-ask per day across all
   jobs** (the one that actually closes the measured four-jobs-one-day hole), 14-day expiry.
2. **Nothing-new focus gate** — a content-hashed context fingerprint stamped when a scheduled
   run *closes* (stamping at open would count the run's own writes as news and the gate would
   be permanently inert); empty delta → the run's directive becomes a short check-in. **A
   condition, not a length cap** — a test asserts the directive contains no sentence/word
   limit, so the rejected ≤2-sentence cap cannot creep back silently.
3. **Ritual ownership** — `session_kind()`'s evening gate generalised: any `X_ritual.md` in
   the persona config is injected only into schedule key `X`/`X_*`. Ownership is declared by
   filename — no second copy of schedule names to go stale. `evening_ritual.md` →
   `evening_close`, exactly as before ([DB-0822-10] tests still 11/11).

Both pipeline twins wired identically. Tests: `tests/test_ritual_focus_gate.py` 33/33, plus
evening-gate, synth-injection, thread-expiry, clinical-thread and context suites re-run clean
(three pre-existing environmental failures verified identical on HEAD).

## The one Red line — for the email-surfacing session (③)

**File:** `config/agents/synthesizer.md`, § *What you receive*, new paragraph immediately
after the `ACTIONS EXECUTED THIS REQUEST` bullets (the file already teaches there that a
code-generated block is evidence, not a claim). **Proposed text:**

> **A `SCHEDULED RUN — FOCUS FOR THIS RUN` block, when present, is binding and is evidence,
> not advice.** It is generated from what actually happened, not written by you or by any
> specialist: which scheduled job this is, whether anything has changed since the last one,
> and which questions have already gone to the user unanswered. A question listed there has
> been asked — do not ask it again, however natural it feels given the context in front of
> you, and do not rephrase it into a new question. Those are open items you may pick up only
> if the user's own words this turn lead there. Where the block and your reading of the
> context disagree, the block is right, for the same reason the actions line is.

**Why it is still needed with the code in place:** the code suppresses the question's *text*,
but the model can re-derive the same question from the unchanged context that produced it the
first time — no code gate catches that residual. No change is needed in
`config/modules/synthesizer_scheduled_sessions.md`; its "raise a thing once" paragraphs were
right and ignored, which is why this build is code.

## Confirmation after deploy

One scheduled-run day: the same unanswered question appears in at most one run; a run with an
empty delta reads as a short check-in; the 20:00 `evening_close` still carries the virtues and
no other run does. (This also serves `[DB-0822-08]`'s owed re-measure day.)
