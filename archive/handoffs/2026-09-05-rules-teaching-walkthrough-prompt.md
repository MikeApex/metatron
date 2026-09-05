# Rules-teaching walkthrough — session prompt

Model: Opus 5 (medium reasoning). A guided (M)-walkthrough: Mike decides dispositions live;
the session prepares each step and executes his word. Not delegable — the judgement about
who his senders are IS the work.

---

Read `SESSION.md` and `ROADMAP.md` first (pre-edit context check), then run this walkthrough
with Mike present.

## The task — [DB-0820-03]'s ruled direction: teach `rules:`

Mike ruled 2026-09-05: intake classification improves through the **code tier**, not the model
extractor (which stays parked — no confidence threshold passes its gate affordably; evidence in
`DEV_BACKLOG.md` `[DB-0820-03]` and `tests/intake_confidence_sweep_2026-09-05_gemini-flash-lite.md`).
The code tier resolves 9/33 corpus messages with just five taught rules, and forward unwrapping
(`effa68a`) now exposes true senders on the 18/33 that are self-forwards — 19 distinct senders
total. Teaching rules for the rest is deterministic, inspectable, and each rule is Mike's own
word rather than a model's guess.

## Ground rules

1. **Rules live in the VM's `config/personas/mike/intake.yaml` — the VM owns persona config.**
   Never edit a Mac copy and never scp one over the top. Teach through the running system
   (`teach_intake`, the tool built for this) or, if editing the file directly, edit it ON the
   VM and only there.
2. **The unrecognised-key trap is real:** a rule whose match block names no recognised key —
   `sender_contains` is the plausible typo, being `teach_intake`'s own parameter name — used to
   match EVERY message and silence the whole inbox. It now matches nothing with a warning
   (`effa68a`), but verify each taught rule actually fires before moving on.
3. **Do not enable the extractor and do not relax its gate.** Out of scope by ruling.
4. **The measurement loop costs nothing:** `tests/run_intake_eval.py` free mode is code-only —
   no model calls, no spend-guard interaction. (Only `--extractor` calls a model; not used here.)
   Fixtures are in `tests/intake_fixtures/` on the VM (personal data, gitignored — never commit).

## Steps

1. **Baseline.** On the VM: run the free-mode eval against the labelled corpus with
   `--persona mike`. Record the resolved count (expect ~9/33 with the five existing rules).
2. **Sender inventory.** List the 19 distinct senders from the corpus (post-unwrap), grouped by
   how they currently classify. For each unresolved sender, prepare a one-line proposal:
   suggested category/domain/disposition, and why.
3. **Mike rules, sender by sender.** Walk the list. He picks the disposition (or says skip —
   a sender he doesn't recognise or doesn't want a standing rule for is a valid answer, not a
   gap). Teach each accepted rule via `teach_intake`, then confirm it fires on that sender's
   corpus message before the next.
4. **Re-measure.** Free-mode eval again. Record before/after resolved counts and what remains
   `unclear`. Remaining unclears surface to Mike by design — that is the sweep working, not a
   failure; do not chase 33/33.
5. **Close out.** Update `[DB-0820-03]` in `DEV_BACKLOG.md` with the before/after figures and
   what the item still owes, if anything — if the code tier + rules now covers real inbound to
   Mike's satisfaction, propose closing it with this session as the evidence, extractor parked
   permanently with its own record. His call. No deploy is owed (rules live on the VM already);
   commit any Mac-side record edits only.

## What done looks like

The corpus resolved count is measurably up from 9/33, every taught rule fired at least once on
real mail, nothing was enabled or relaxed on the extractor, and `[DB-0820-03]` records the
numbers with Mike's disposition on whether it closes.
