### 2026-09-01 (the Gemini fleet leaves 3.1 Pro, and a catalogue listing turns out not to mean available) — `config/modules/{routing_cloud,routing,spend_guard}.yaml`, `core/{spend_guard,orchestrator}.py`, `tools/mail.py`, `scripts/check_model_availability.py` (new), `SESSION.md`, `ROADMAP.md`, `DEV_BACKLOG.md`, `docs/CONVENTIONS.md`, plus `~/.claude/mcp_servers/ask_gemini.py` and Chorus (`~/Desktop/chat/{server,insult_sim}.py`) — **not deployed; owes `./deploy.sh`**

**The whole fleet moved off `gemini-3.1-pro-preview` and `gemini-3.1-flash-lite` in one pass.**
Reasoning tier (synthesizer, pattern_miner, goals_interviewer, mental_wellbeing, physical_health,
research_agent) → `gemini-3.7-flash`; bulk tier (twelve agents + `quick_override`) →
`gemini-3.5-flash-lite`. 3.1 Flash-Lite was **deprecated**, which made this time-sensitive rather
than opportunistic. **There is no Pro in the fleet any more**: the Flash and Pro lines have
desynced, 3.5 Pro never became reachable, and 3.7 Flash outscores 3.1 Pro at a fraction of the
price — so the reasoning tier is a Flash model now, and the routing comments say so.

**The finding that changes how this is checked in future: a catalogue listing is not
availability.** `gemini-3.8-flash` and `gemini-3.5-pro` both return `200 GA` from the Vertex
publisher-model metadata endpoint and **`404` from `generateContent` on `global`**. A check that
enumerated the catalogue would have recommended migrating to 3.8 Flash and the migration would
have 404'd in production. This is the `us-central1` trap inverted — an endpoint that does not
serve a model answers quietly rather than loudly. Every model id in this migration was confirmed
with a real call, not a listing.

**A briefing document written outside Claude Code drove the work, and three of its claims did not
survive contact.** *(1)* Its blocker check for `thinking_level="MINIMAL"` does not apply — this
codebase uses `thinking_budget` (integer, `types.ThinkingConfig`), not the string enum, so
`_SYNTH_THINKING_BUDGET = 4096` migrated untouched. *(2)* It said 3.5 Pro "has never shipped";
it has, it is GA in the catalogue, and it is simply unreachable — same conclusion, different
reason, and the difference matters because the monthly check has to test for reachability rather
than existence. *(3)* It flagged the 3.5 Flash-Lite model id as UNCONFIRMED; confirmed live on
both Vertex and the Developer API.

**Mike's cache figures were also corrected, from the authoritative source he named.** He reported
no published cache-storage SKU for 3.7 Flash and said not to populate it. The Cloud Billing SKU
catalogue **does** publish one — `Gemini 3.7 Flash Text Input Caching Storage`, $1.00/1M/hour —
so the Flash-class $1.00 went in as sourced rather than inferred. The pricing *page* he checked
genuinely has no 3.7 row; the SKU catalogue is the better source and is what
`docs/CONVENTIONS.md` now points at. **This mattered more than it looks:**
`core/spend_guard.py:257` reads `cache_storage_per_hour` with `.get(..., 0.0)`, so an entry that
exists but omits the key bills cache storage at **zero** — leaving it unpopulated would have made
the guard blind to the exact line that caused the 08-19 incident ($2.63 estimated against a $6.12
bill, the gap being ten abandoned caches), not conservatively over-estimated as intended.

**Pricing is now date-aware, which is a new shape in this file.** 3.7 Flash is on introductory
pricing that ends 2026-12-31; input and cache-read both double on 2027-01-01 while storage stays
flat. Pinning the intro rates under-reports by 2× from New Year's Day, silently, on the model
carrying most traffic; pinning list rates over-reports 2× now, and with caps at $100/$175 a
spurious hard-cap trip is an **outage** on this project. Neither constant is safe, so a model
entry may now carry a `from:` map of ISO dates to rate overrides, applied by
`_apply_dated_overrides()`. **The date is in the table rather than in someone's calendar
reminder.**

**The cache TTL was re-derived and deliberately not changed.** The 10-minute window's
justification was computed for a Pro cache and Pro left the fleet, so it had to be redone; the
old comment's 0.0417 hits/min for Pro reproduced exactly, which validated the model. New figures:
3.7 Flash 0.0247 hits/min (0.123 from 2027, when the read saving doubles against flat storage),
3.5 Flash-Lite 0.0617. A 10-minute hold pays for itself at **under one cache hit on every model**,
and the reasoning tier is now *cheaper* to hold than it was on Pro. The constant stands; only its
reasoning was rewritten. Noted for the next migration: storage is a flat $1.00/1M/hour across
every Flash-class model, so a cheaper bulk model shrinks the read saving without shrinking the
fee — Flash-Lite is the worst row for exactly that reason.

**Cache creation itself was verified by creating and deleting real `CachedContent` objects on all
four models.** Both targets keep the 4096-token floor that `_pad_for_vertex_cache()` already
clears (it pads to ~4263 actual). Worth recording because it was luck, not design: 3.1 Pro is the
only one of the four with a **1024** floor, and the Synthesizer sat on it. Had anyone tuned the
padding down to Pro's floor, this migration would have silently killed Synthesizer caching —
trap #6 exactly. The padding is a single global constant, so it held.

**The 200K price cliff is gone and the code that avoided it was kept anyway.** `tools/mail.py`
sized its correspondence sample to stay under the step where 3.1 Pro's pricing rose. The SKU
catalogue publishes **no `(Long)` variant for any Gemini 3.x model** and every 3.x text SKU is a
single untiered band — all 149 long-context SKUs are 1.5/2.0/2.5. But the budget was never *only*
a cliff-avoidance device: it is a plain cost cap, and deleting it would raise spend linearly. So
the rationale was corrected and the number kept, now explicitly raisable on its merits.

**Rejected: putting the monthly model check in the scheduler — Mike's call, and he was right.**
It was built as a `function:` job with a new `monthly` cadence in `_is_active_day` and a
`tools/model_watch.py` module. He asked whether the scheduler was the right place. It was not:
the scheduler runs the *product*, and model availability is a development concern whose only
actionable outcome is a developer's Red-tier routing edit. It would have added Red-tier shared
scheduling logic and a runtime `tools/` module no agent ever calls, worsening the dev-vs-product
machinery ratio `.claude/rules/deploy.md` already warns about. **Reverted `core/scheduler.py` to
byte-identical with HEAD, deleted the module**, and the recurrence went to `[DB-0901-01]` as a
`due:` item — an existing convention that wakes itself on the sync line at session start, in a
dev session, which is where the decision would actually be made.

**Two defects in the new script, both found by running it rather than reading it.** *(1)*
SKU-catalogue discovery **misses `gemini-3.8-flash` entirely** — a model gets a SKU when it gets a
price, and the newest ones have none, so a SKU-only check is blind to precisely the releases it
exists to catch. Discovery is now two-source: SKU catalogue plus generated version ids, both
funnelled through the free metadata endpoint before any billable call. *(2)* With Pro dropped
from the fleet, the per-tier "newer than" floor had no Pro entry, so **every Pro that ever
existed scored as new** — the first run duly reported `gemini-2.5-pro` as newer than
`gemini-3.7-flash`. Absent tiers now fall back to the fleet-wide best version.

**A4 safety testing suspended for the remainder of the capstone buildout (Mike's ruling).**
Recorded at `ROADMAP.md` § Section 0 point 8, beside the gate it suspends, and in `SESSION.md`.
Broader than the 2026-08-05 note, which parked only the local run — this parks the Vertex-path
run too, so **no clinical hard-fail is being exercised anywhere** for the duration. Stated plainly
in all three places because it has a consequence that would otherwise be discovered later: the
fleet moved `mental_wellbeing` and `physical_health` to 3.7 Flash **without** running
`tests/run_a4_safety.py`, so `MUST_SURFACE`, `CLINICAL_CONCERN` and `MEDICATION_MISSED_CRITICAL`
are **unverified on the model now serving them** — by decision, not oversight. The last clean 6/6
was on a model no longer in the fleet. 3.7 Flash benchmarks above 3.1 Pro so no regression is
expected, but this project's own rule is that a flag never exercised by a test is not known to
work, and a benchmark is not that test. Expiry: capstone close.

**Mike's earlier instruction to move all six Pro agents together was reaffirmed after the
bisectability concern was raised once**, and built as asked.

**Also refreshed, both on the Gemini Developer API (a different catalogue from Vertex — 3.5 Pro
and 3.8 Flash are not reachable there at all):** `ask_gemini`'s alias table, where `flash` and
`pro` were two generations stale, now repointed to current gen with every previous target kept
under an explicit pinned alias so nothing became unreachable; default moved to 3.7 Flash. Chorus
(`server.py`, `insult_sim.py`) took the same swap, keys deliberately unchanged. **Chorus's cost
table was already wrong before this** — it understated both 3.1 models — so its readouts have
been low for some time; corrected, with the 2027 step noted inline.

**Verification.** qa_sweep 9/9; `tests/test_vertex_cache_ttl.py` 23/23; `check_agent_tools.py`
0 named-as-live-but-unbuilt, 0 not-granted; all 18 cloud agents resolve to the new ids under
`DEPLOYMENT_MODE=cloud`; one real end-to-end `research_agent` call returned correctly on 3.7
Flash and the spend guard priced it at **$0.002548**, matching (2843×0.75 + 111×3.75)/1e6 exactly
— against $0.0070 had it fallen through to `default`, which is the check that proves the pricing
entry is live. A4 not run, per the ruling above.

**Deploy, and a no-op deploy worth recording.** Mike ran `./deploy.sh` and reported "deploy
complete" — **and it shipped none of this.** `deploy.sh` runs `git push origin main` and a VM
`git pull`; it **never commits**. The whole migration was still uncommitted in the working tree,
local `HEAD` and `origin/main` were both on the previous session's `d26c610`, so the VM pulled a
branch without a line of it and carried on running 3.1 Pro and the deprecated 3.1 Flash-Lite.
Nothing broke — the failure mode is silent success.

**The wording that caused it was mine:** the handoff said this "owes `./deploy.sh`" without
saying it first owed a **commit**. That reads as one action and is two, and the deploy step is
the one that reports success. **Say "owes a commit, then a deploy" wherever an undeployed change
is handed over** — `deploy.sh` will happily push a branch that does not contain the work and
exit 0. Caught only because a post-deploy `git status` was run to confirm what the VM would have
pulled; without that check the fleet would have looked migrated and been unchanged.

The MCP (`~/.claude/mcp_servers/ask_gemini.py`) and Chorus edits are outside this repo, are not
carried by any commit here, and need no deploy — they were live the moment they were written.
