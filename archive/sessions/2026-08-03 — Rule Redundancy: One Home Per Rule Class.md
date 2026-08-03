# 2026-08-03 — Rule Redundancy: One Home Per Rule Class

Continuation of [2026-08-03 — Check-in Restraint, Persona Config Ownership, Profile Capture](2026-08-03%20—%20Check-in%20Restraint,%20Persona%20Config%20Ownership,%20Profile%20Capture.md), which deferred the Rule Redundancy plan. This session executed all four items.

Not to be confused with the parallel window's [2026-08-03 — SEQ 021 Logistics Turn Burn, Clock Injection, Tool Error Hints](2026-08-03%20—%20SEQ%20021%20Logistics%20Turn%20Burn,%20Clock%20Injection,%20Tool%20Error%20Hints.md), which was editing `synthesizer.md` and `logistics.md` concurrently — see §6.

**Commits:** `0077a63`, `a03ed7e`, `7f1e6c8`, `2fc0f4e`. VM-side edits to `mike.md` and `mike/scheduler.yaml` are not in git by design.

---

## 1. The problem, restated from the debt

Five of Mike's preferences sat in **both** `config/personas/mike.md` and `config/agents/synthesizer.md`. Both copies were written the same afternoon — Synth self-applied them during conversation, and the same rules were generalised into the agent file hours later. Nothing detected the overlap; it took reading both files side by side by hand.

The failure mode is not untidiness. Editing one copy leaves the other stale, and **the stale copy keeps firing**, silently, because nothing reads both.

## 2. Detection: classes, not text similarity

The first implementation scored word overlap between rules. It was a dead end, and the reason matters for anyone tempted to rebuild it that way:

> *"Stop repetitive reminders for pending tasks"* and *"Raise a thing once. An open item that you have already surfaced is not raised again"* are **the same instruction with almost no words in common.** Any bag-of-words score puts them near zero.

Threshold sweep on the real set: at 0.45, zero of five found. At 0.25, one of five, plus noise. Lexical similarity cannot do this job.

[`core/rule_classes.py`](../../core/rule_classes.py) instead sorts rules into **classes** (repetition, sycophancy, brevity, evidence weighting, session timing, justification, follow-up style, confidentiality, capture), each with the layer that owns it. Class match supplies recall; word overlap only *ranks* candidates within a class.

**Patterns must match the complaint, not just the instruction.** The first pass missed *"Stop bringing up the same pending task over and over"* because the `repetition` pattern only covered the vocabulary the agent files use. Widened to the phrasings a user actually reaches for — `over and over`, `same thing/task/point`, `every time`, `keep telling`. Same fix for `evidence_weighting`: added `reading too much into`, `making too much of`, `one bad night`, which is what catches the real complaint *"once again, you're making too much of the sleep disruption."*

**Measured, not asserted** — against the actual 2026-08-03 set:

| | Result |
|---|---|
| Recall, which preference is duplicated | **5/5** |
| False positives, eleven novel preferences | **0** |
| Correct *partner* named | **2/5** |

That last row is why the finding text says "candidate rule(s) it may restate" and CLAUDE.md carries a *Known limits* paragraph. The flagged preference is the trustworthy output; the partner is a starting point.

## 3. Three checks at three speeds

| Speed | Where | Sees | Cost |
|---|---|---|---|
| Write time | `write_persona` → `check_new_rule()` | preferences **the tool records** | regex, no model call |
| Daily 05:30 | `daily_rule_audit`, a `function:` job | everything currently written down | **zero model tokens** |
| On demand | `scripts/check_rule_overlap.py` | same, interactively, incl. `--all-pairs` | — |

**The write-time check warns and never blocks.** Refusing a write to keep a file tidy discards something the user actually said — the same error made earlier the same day with the `write_persona` section whitelist, which had to be reverted (`8659c4d`).

**The daily audit was the user's suggestion and is the more important half.** The write-time check can only see what Synth writes. *The five duplicates were written by hand, by Claude Code, in a development session* — no write-time guard could ever have seen them. Findings become `RULE_CONFLICT` quality events and travel the path already built: sync → `DEV_BACKLOG.md` → the count shown when a development session opens. Each finding is reported **once**; a daily re-report is precisely the noise that "raise a thing once" exists to prevent, and it would be poor form to build a tool that commits the failure it is checking for.

## 4. What was cut, and why

An early version also compared shared rules against each other. **Unusable.** The specialist agent files carry intentional parallel boilerplate — *"Mandatory pass. Runs every session"*, *"Voice mode:"*, *"The system clock in your context is authoritative"* — which scores as near-identical because it **is** near-identical, deliberately. Those findings drowned the real ones. Dropped from the daily job; still reachable via `check_rule_overlap.py --all-pairs`.

Also suppressed: preferences whose class the **persona layer owns**. `follow_up_style` is personal by definition, so flagging it against a scheduler prompt containing "follow-up" is noise the reader dismisses on every run.

## 5. Clearing the debt — the VM check that mattered

Each removal from the live `mike.md` was made **only after confirming the replacement was live on the VM**, not merely committed on the Mac. That check earned its keep:

| Removed | Rehomed to | Verified |
|---|---|---|
| Never say "enjoy" | `synthesizer.md:82` | ✓ VM |
| Stop repetitive reminders | `synthesizer.md:78` | ✓ VM |
| Don't over-emphasize sleep | `synthesizer.md:84` | ✓ VM |
| Keep check-ins brief | `scheduler.yaml` → `companion_checkin.prompt` | ✓ VM |
| Only check in when no active dialogue | `quiet_after_user_minutes` gate | **partial** |

The fifth only covered `companion_checkin`. `morning_brief` and `evening_close` are time-anchored and carry no gate — so removing it would have dropped coverage. Held back, and flagged rather than quietly dropped.

**Then the user resolved it by changing the requirement**: morning and evening should fire regardless of an active conversation, with an explicit redirect (*"Now let's turn to the evening close"*) rather than folding in silently. That made the `mike.md` line not merely duplicated but **actively contradictory**, and it was removed. New rule in `synthesizer.md` under *Scheduled session conduct*.

Live audit on `mike.md` went **5 findings → 1**. Backups: `~/metatron-backups/mike.md.pre-dedup*`.

**One finding adjudicated, not acted on.** `mike.md:9` *"No commendation or validation… drop affirmations, compliments, filler"* flagged against `synthesizer.md:82` *"Do not tell the user to enjoy things."* Same class, but :82 forbids sign-offs and only *mentions* commendation as an analogy — it does not forbid it. Mike's rule says something the shared rule does not, so it stays in the persona layer. Promotion would need the user's call; they have so far said "universal" only about "enjoy".

## 6. Concurrency with the parallel window

`config/agents/synthesizer.md`, `logistics.md` and both routing files carried **uncommitted** edits from the parallel session throughout. Handling:

- Only **surgical `Edit` calls** to `synthesizer.md`, in a region (lines 78–90, 155) far from their edits (~364, tools list). No full rewrites — a rewrite from stale context is exactly how concurrent work gets destroyed.
- **Staged files individually.** Never `git add -A`; never staged their files.
- The parallel session's `2f74cd2` then swept up both of my `synthesizer.md` rules, and my deploys carried them. **Verified present in the deployed file on the VM** rather than inferred from the commit graph — a backlog entry claiming they were pending had to be corrected because of it.

## 7. Also done

- **`data/personas/sarah_chen/` gitignored.** It is the validation-probe persona, so every run writes into that tree; the three seed logs (2025-05-05/12/19) stay tracked and a genuinely new fixture needs `git add -f`. Plus never-fixture rules for all personas: `traces/`, `config/`, `schedules.yaml`, `logs/quality_events.json`.
- **CLAUDE.md → *One Home Per Rule Class*** — the layer-ownership table, "promotion deletes the original", the three checks, and the known limits.
- **`RULE_CONFLICT`** added to `sync_dev_backlog.py`'s `WANTED` and `LABELS`.
- End-to-end verified: VM audit → quality event → sync → `DEV_BACKLOG.md` Inbox. Second run reports `0 newly reported`.

## Open

- **The scheduler cannot defer a time-based job.** `_activity_gate_blocks` returns "skip", and a `time:`-anchored job that skips is gone for the day, not postponed. Fine under the current decision — morning and evening are deliberately not interruptible — but a real "hold until they're quiet" gate for a fixed-time session needs a deferral mechanism, not a skip.
- **`CLASSES` is incomplete by construction.** Add a class when a duplicate slips through; do not read a clean report as proof.
- Carried forward from the previous session: no user-facing review of what `write_profile` has stored; data breadth remains the root cause behind sleep over-weighting.
