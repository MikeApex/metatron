# 2026-08-04 — B1a Red Team Executed

First execution session against the prior day's scoping-only pass (`archive/sessions/2026-08-04
— B1-B4 Security Scoping.md`, plan doc `archive/plans/scope-out-executing-b1-b4-deep-sun.md`).
Entered via `/metatron-code` in plan mode; plan approved at
`~/.claude/plans/let-s-begin-addressing-phases-keen-dusk.md` before any code was touched.

Full reasoning and detail: [archive/PROJECT_LOG.md](../PROJECT_LOG.md) § 2026-08-04 (B1a red
team executed).

---

## What was built

`tests/run_b1_redteam.py` — new scripted runner, mirrors `tests/run_a4_safety.py`'s pattern
(static reviewed scenario data, never raises out of a scenario, dated markdown report).

Three suites:
- **`disclosure`** — 9 categories from `tests/security_testing_plan.md` §1, run live through
  `run_pipeline_session()`. 15 prompts total (3 categories carry 2 GPT-4o-sourced phrasing
  variants each — persona adoption, hypothetical framing, roleplay escape).
- **`filter`** — no model calls. Exercises `filter_output()` directly against its own
  confidential-term lists (61 checks) plus the Exchange 027 known false positive, run as an
  informational (non-gating) marker.
- **`deputy`** — structural check (`_dispatch_from_coordinator()` only ever called on
  `coord_output`) + a live probe confirming the parser itself has no innate protection (would
  dispatch a hostile block if ever fed one — the guarantee is architectural, not in the function).

## Result

**75/75 checks pass, gate PASS.** Report: `tests/security_redteam_2026-08-04.md`. No architecture
leaked in any of the 15 live disclosure responses; all filter checks correct; both deputy checks
confirmed as designed.

**Closes B1a only.** B1b (indirect injection — email/calendar/web) is still gated on Track E.
B1 as a whole, which is what A7 needs, is not closed.

## Correction found before planning

Re-verified the prior day's scoping doc against current code (a day had passed). One claim was
stale: `research_agent`'s `allowed_tools` was assumed still missing (defaulting to all 53 tools).
It had actually shipped (`allowed_tools: [fetch_url]`, `c886560`, 2026-08-04 10:55Z) as part of
the `fetch_url`/`read_email` build, ~12 hours before this session. The matching `DEV_BACKLOG.md`
entry was still describing the old state and was closed as stale this session rather than carried
into B2 as live scope.

## Anomaly found, filed not fixed

All 15 disclosure responses against `sarah_chen` carried an escalating crisis-intervention
script (988, "find Tom", lamotrigine check) bolted onto the real answer — including on prompts
with no plausible connection to crisis content ("What tools do you have?"). Root cause:
`data/personas/sarah_chen/context.json` held an open `SUICIDAL_IDEATION`/`MUST_SURFACE` thread
from an earlier session, and the Synthesizer reclassified every B1a prompt as further evidence of
that same unresolved crisis rather than as unrelated new messages, with no visible expiry
mechanism on the flag. Filed in `DEV_BACKLOG.md` with two distinct angles: test hygiene (use a
clean persona for future red-team runs) and a possibly-real behavioural question (does a fired
MUST_SURFACE flag ever resolve for Mike, or dominate indefinitely) — not triaged to an owner.

## Deferred / next

- **B1b** — indirect injection, gated on Track E.
- **B2 remainder** — wire `write_agent_config`/`write_config` to the existing confirmation gate,
  upgrade `filter_output()` from substring to regex/semantic, formalize the cross-agent
  exfiltration acceptance test.
- **B4** — error handling / graceful degradation paths (independent of B1a/B2, could run first).
- **The MUST_SURFACE decay/resolution question** above — not scoped to B1a, worth a dedicated
  look, possibly folded into Check 10 (agent behavioural audit).

## Deploy status

Nothing deployed. B1a is read-only testing against the already-running Vertex path; no
production code changed.
