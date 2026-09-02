# Session ⑥ — three-bug code session, and the capstone closes at its end (launch prompt)

Model: Opus 5. Green/Amber code work per the model split (plan/review Fable, build Opus);
nothing here is Red — where a diagnosis lands on an agent file, this session stages a proposal
and stops rather than editing it.

**Budget:** ~half a day of build. Run-cost delta ≈ zero (all three fixes remove or gate writes;
the derived-facts rider adds one code-computed line per session on existing reads). No standing
resources created. Diagnosis needs VM trace reads (free) and journalctl over IAP.

---

/metatron-code Session ⑥ — the capstone's last build session: three bugs, one rider, one
diagnosis. All evidence is in each item's `DEV_BACKLOG.md` entry — verified 2026-09-02 against
live traces; **still re-open each against current code before fixing** (the standing rule).

1. **The log records an email as sent while it is still waiting for approval — and it was then
   declined ([DB-0829-01]).** The receipt enforcer already knows the action is pending; the same
   signal must gate (or reword) any same-turn log/journal dispatch describing the gated action
   as done, and the actions logger must stop writing `completed` for a merely-gated call
   (journalctl 08-29 13:00:18 is the instance). A declined action must never survive in the log
   as performed.

2. **The quality log fills with "misses" that describe successes ([DB-0902-01]).** Since the
   09-01 migration the Coordinator files ROUTING_MISS events like *"handled morning session
   prompt successfully"* — 5 in two days. Diagnose first: template misuse by 3.7 Flash
   (instruction side — stage a proposal, do not edit `coordinator.md`) vs a slot code can
   sanity-check (build it). The closed `[DB-0827-07]` is the adjacent class; its `is_null_ish()`
   fix is the wrong tool here (payloads are non-empty) — do not widen it into semantic guessing
   without a measured rule.

3. **The two inbox jobs disagree about the same inbox ([DB-0902-02]).** 08-30 14:45:03
   (pipeline summarize) said "no new messages"; 14:45:29 (direct run) found three items in the
   same minute. Map what each path actually reads (intake queue vs raw inbox is the suspect —
   intake went live 08-29 13:54) and fix the one that is lying, or make them read the same
   source. **This diagnosis feeds `[DB-0822-09]`'s failed surfacing half** (Death Cab: legs
   generated one layer down, user told "all clear") — diagnose whether the surfacing miss is
   this same split; if the remaining fix is Synthesizer wording, stage it as a Red proposal for
   Mike, do not edit.

4. **Rider — stale carried state ([DB-0822-06]):** the item's own re-open condition fired (the
   hiatus described three wrong ways across three days, post-annotation). Build the
   code-computed derived-facts line the item deliberately deferred: compute date-derived counts
   (day N of X, days-since) at read time from stored dates and inject them as evidence beside
   the model-authored text they correct. Keep it to genuinely code-derivable facts.

**A4 is suspended and its re-run is off the capstone close path (ROADMAP § Section 0 pt 8,
amended 2026-09-02)** — do not run it. Regression gates that do apply: the tests each touched
module already carries, plus `tests/test_false_action_claim.py` (item 1 borders it) and the
pipeline suite if `core/orchestrator.py` is touched.

**The capstone no longer closes here (amended 2026-09-02, same day):** Mike folded the three
never-scheduled items into a session ⑦
(`archive/handoffs/2026-09-02-session-seven-capstone-remainder-prompt.md`), which now carries
the close ritual. This session ends with a dated status note in the capstone tracker and a
plain statement of whether **the work owes a commit, then a deploy.** /archive at close.
