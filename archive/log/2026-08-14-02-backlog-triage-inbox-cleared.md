### 2026-08-14 (Inbox cleared: two entries that were not what they said)

`/backlog` default pass, same session as the `[H7]` close. Inbox **4 → 0**, `## Now` **8 → 10 (at
cap)**, `## Later` 31 → 32. No runtime code changed, nothing deployed.

**The pass's whole value was the standing rule — no item is triaged on the strength of its own
description. Two of four survived contact with the code; two did not.**

**Rejected: building a calendar reconciliation loop.** The Inbox asked to *"stop assuming passed
calendar events are completed"* and build a loop that *"actively alerts/pushes the user."* It
already exists — `daily_calendar_reconcile`, a `_DEFAULT_JOBS` entry firing 05:40 daily for every
persona, calling `reconcile_check()` at `tools/calendar_reconcile.py:323`. **And the push half was
already rejected in code, with the reason recorded at the point of temptation:** the job comment
states `notification: False` is *"not a preference — `reconcile_check` returns a plain string and
never a notify dict, because the check is crude text matching and cannot support the claim that
anything was missed."* Pushing on a crude text match is precisely the false-confidence failure
`[DB-0810-13]` exists for. Closed, folded into `[DB-0809-21]`(3), which is the genuinely open
remainder and is time-gated on a real unreferenced calendar event existing. **Had this been filed
on its description it would have re-commissioned a built feature and reversed a deliberate safety
decision in the same ticket.**

**The sharpest finding: `[DB-0809-02]`'s fix did not hold, and only the timestamps show it.** The
Inbox reported evening close firing 3 repetitive messages on **2026-08-12**. `82d394b` — *"Stop the
scheduler's own prompt being read as user speech"* — landed **2026-08-09**, and `_frame_proactive()`
is live in both pipeline copies (`core/orchestrator.py:3089`, called at `:3134` and `:3264`). So
this is a **post-fix recurrence**, not a new bug: either the fix is incomplete, `evening_close`
reaches a path it does not cover, or the cause was never what the fix addressed. Merged into
`[DB-0809-02]` as falsifying evidence rather than filed separately — a second ticket would have
been worked as a fresh bug by someone who never saw the first. **Read the 08-12 trace specifically**
rather than sampling the week; a recurrence with a known date is worth more than seven ordinary
days. *Rejected again: the ≤2-sentence cap* — rejected originally because focus is the target and
length only its symptom, and a recurrence is not a reason to reverse that.

**Two new `## Now` items, both Mike's, both verified before filing.** `[DB-0814-01]` #9 — the inbox
check reports "nothing found" six times a day (`check_interval_minutes: 240`,
`config/templates/email.yaml:67`); an instruction change, not a build. `[DB-0814-02]` #10 —
nothing ages out stale context, and it is **structurally impossible today**: `open_threads` is a
bare `list[str]` (`tools/context_tracker.py:198`) with **no timestamps**, so the first deliverable
is a timestamp, not an expiry policy. Deliberately *not* modelled on `clinical_threads`, whose
tier-2 entries never auto-expire by design. Both ranked below the existing eight because those are
live correctness failures; stale context misleads rather than making a false claim.

**Standing rule stated by Mike this session, and it changes a default:** *most of what he states as
a preference is him authoring the general design, not describing a deviation; a deviation is
normally flagged as the exception to a design edit.* So the default filing is the **agent layer**,
not the persona layer, and promotion deletes the original. Previously `CLAUDE.md` framed this as a
question to ask each time; it is now a default with a flagged exception. Saved to project memory.
Applied immediately: the *"stop reading back triaged emails"* preference, already applied at the
persona level, is recorded in the closed archive as a **promotion candidate** rather than a
refinement.

**Found and fixed in passing — `/archive` step 2 told you to hand-edit a generated file.** It said
*"append one entry to `archive/PROJECT_LOG.md`, at the top of the file"*, three sessions after
`build_project_log.py` made that file generated. Following it would have written an entry that the
next build silently discarded. **The same stale claim was in `archive/log/_preamble.md`** —
*"appended at the close of every session — never rewritten"* — which is worse, because the preamble
is rendered into the generated file's own header, so the file was actively instructing readers to
edit it. Both corrected: the command now says write a fragment and regenerate, and the preamble
carries a generated-file warning naming the script and the `--check` verification. **This is the
`[DB-0809-11]` class the claims linter was built for** — but that linter checks whether paths and
hooks exist, not whether prose about a file's write discipline is still true, so it passed cleanly
over both.

**Deferred, not done:** `DEV_BACKLOG.md` is **577 lines against its ~450 ceiling** and was already
over before this session — `## Later` is accumulating narrative. A `deep` pass is the right
response, after §10b. The `⚠ machine: ×5` on `mike.md:13`'s consolidated-check-in preference is
also unactioned; by the new default it is design and belongs in `synthesizer.md`.

