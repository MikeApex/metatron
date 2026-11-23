Model: Opus 5.5 — a judgement session: reading a month of signals with Mike and turning what he decides into values; the reasoning is the work.

# Ranking Part B, phase 3 — the first monthly signals review (walkthrough)

**Who runs it:** Mike with a Claude Code session, about a month after `ranking_signals` is
switched on. **~30 minutes.**
(`archive/plans/ranking_values_plan_2026-11-23.md` § 4.13, § 7.2 item 3, B30–B32.)

**What it is for:** looking at whether the ranking is doing its job. That means momentum on what
matters, obligations kept, protected time held, few questions, and no nagging. Each decision goes
into `config/modules/ranking.yaml`, which applies to every user, or `config/personas/mike/ranking.yaml`
(yours only; VM-owned, Mike edits). **Overrides are read, never scored** (B30): an override can be the
ranking's mistake or yours, and the conversation decides which.

**Before:** `ranking_signals: true` has been on for most of the month. If it went on mid-month,
read from that day.

---

## The session

1. Print the month on the VM:
   ```
   cd ~/multi-model-mcp && .venv/bin/python scripts/ranking_report.py --signals --persona mike --month YYYY-MM
   ```
2. Read it together, in this order:
   1. **In their words.** Start with what you said: regret answers, how things felt, any remark
      about overload, nagging or satisfaction. Regret is a short-term signal (B30).
   2. **Momentum.** Goal steps done, and how often the keep-in-touch and upkeep clocks stayed inside
      their cadence. This is the long-term signal.
   3. **Missed obligations** (the worst day). Anything above 0 is looked at by name, in the ledger.
   4. **Protected time.** How often it was taken, and what was asked and decided. Fewer is the
      system working, not proof nothing needs adjusting.
   5. **Attention.** Questions this plan's paths asked (prompts, raises, weekly items, notices),
      against what you felt was too many.
   6. **Overrides.** Grades you corrected and days the Synthesizer reworked. Each is a question:
      was the ranking wrong, or was the moment special?
   7. **Other rows.** Any row this plan did not write (e.g. the goal network's satisfaction rows,
      once built) is read here and never duplicated.
3. For each thing Mike wants changed, the session names the value and its file and proposes the
   edit. Examples: the intrusion bases, the raise caps, the back burner's days, a neglect cadence.
   Mike decides. Universal changes are committed for his next deploy. Changes for him alone go to
   his persona overlay, which he edits on the VM.
4. Record the review as a dated sub-section of the plan, § 11c, and set the next month's date.

**Done when** each signal has been read and every change has a home or an explicit "leave it".
