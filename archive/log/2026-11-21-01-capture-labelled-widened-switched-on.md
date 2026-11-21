### 2026-11-21 (capture fidelity labelled three times, widened to five kinds plus "other", switched on at 87% precision by Mike's ruling) — `f573250`, `61a73cd`, `3f47391`, `9451caa`, `6e8ed5d`, `f878ead` — **VM at `6e8ed5d` (deployed by Mike); `f878ead` (the switch) NOT yet deployed**

**Outgoing handoff carried forward:** the 11-18 session built capture fidelity, measured it on
mike's backfill and left it off pending Mike's labels; labelling was handed to a chat
(`archive/handoffs/2026-11-18-capture-labels-in-chat-prompt.md`). This session ran that chat
(11-18 → 11-21).

**Pass 1 (11-18 backfill): precision 72%, recall 18%, matcher 100%.** Recall failed for two
reasons: the extractor skipped facts its kinds covered ("when in doubt, leave it out"), and most
misses Mike named had **no kind at all** — appointments, places, people, health facts,
corrections. Precision failed mostly on invented day-shape values (one night's sleep → every
day; focus-block times the user never gave).

**Built (Mike's rulings 11-20):** five kinds for ordinary turns — event, place, person, health,
correction — each kept by its own tool or a home (`KIND_TOOLS`/`KIND_HOMES`); and **`other`**,
never shown, kept on the VM (capped 200), raised **once per recurring category** (5 in 30 days)
or by volume (15) as a `CAPTURE_NEW_CATEGORY` **Inbox** event — Mike: "so long as misses are
caught". Health's clinical review deferred to the pre-launch pass (Mike). Alerts carry three
example facts (Mike, `61a73cd`) — they reach the tracked, pushed `DEV_BACKLOG.md`.
**Fable reviewed the diff: nine findings, all fixed** — the sharpest: a second category alert
overwrote the first in the Inbox (prose-similarity merge; raise-once made it permanent); a
correction read as kept when the write repeated the wrong value (now `{right, wrong}`); an
event read as kept on the wrong date (now ISO date/time must match); `other` would inflate
recall (now outside both labelling pools).

**Believed true, wrong:** (1) the first re-run's jump to 96/150 unsaved looked like a real
finding — it was the **backfill resolving "tomorrow" against the run's own date**, not the
message's (`3f47391`; live turns never affected). (2) The extractor's examples were assumed
harmless — Mike: they were his own sentences, so the retest measured recognition, a small model
can learn names instead of rules, and **the shared instruction file put his life into Iva's
prompts**. Replaced with invented examples (`6e8ed5d`). (3) A commit-guard override was assumed
necessary for shell-appended files; the auto-mode classifier denied it, and a plain stage
passed — the guard only blocks lines it cannot attribute.

**Pass 2: 84 / 86 / 96. Pass 3 (rules only, invented examples): precision 87%, recall 90%,
matcher 98%.** Tasks 43/43, events 12/13; weak: preferences 11/16, goals 1/3 (both "a goal for
next week" said by the user). Pass 3's new "not a fact" lines cost 4 recall finds.
**Mike switched it on as planned (shadow for ordinary turns, interviewer on), below the 90%
precision minimum by recorded ruling.** Rejected: both writers in shadow (Iva's first interview
would get no help); a fourth instruction round (diminishing, tunes to mike's 60 days).

**Deployed without being announced: goal–task network phase 1.** A parallel session committed
`98f158f` "not deployed" on 11-18; `deploy.sh` ships the branch, so Mike's capture deploys
(`f573250` onward) took it live on 11-20. Found only at this close-out. Its pre-deploy check
holds — `mike`'s fixed jobs exist under the expected names, and the shield rule now covers every
coordinator-run fixed job (`shield_jobs: []` by design). Its four live checks are owed.
**Lesson for any session asking Mike to deploy: list every undeployed commit the deploy will
carry, not just your own** — `git log <vm-head>..HEAD`.

**Found, not built:** no runtime mechanism for **custom logs** (the cardiac log was made by hand)
and no **places with GPS** — planning prompt `archive/handoffs/2026-11-21-custom-logs-and-places-planning-prompt.md`.
**Iva's quality events never reach the backlog** (the sync fetches mike's only) — every type,
pre-existing. **New kinds have no "already held" check** — must exist before the Synthesizer's
mode goes `on`. Cross-store duplicates are unchecked (raised, not filed by Mike's choice).

