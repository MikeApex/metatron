# Session — B1–B4 Security Scoping — 2026-08-04

Scoping only. No code changed, nothing deployed.

## Ask

Scope out executing Track B security hardening (B1–B4, `ROADMAP.md` lines 189–273): time,
number of sessions, and resource weight (API spend, VM/deploy load).

## What was found

Read the roadmap's own language against the actual code rather than trusting either at face
value. Result: B1, B3, B4 are genuinely not started. **B2 is roughly 60% done already** —
`SESSION.md` said PoLP tool permissions were "in warn mode by decision"; the code
(`core/orchestrator.py:2190-2193`, `core/router.py:128`) shows the per-agent `allowed_tools`
whitelist is enforced, not warned. Also already built and believed open: auth + `send_email`
confirmation gate (`ca993fe`), CORS restriction (`server.py:75-81`), and
`run_session_anthropic`'s iteration limit (already matches the other provider loops at `8`).

Real remaining B2 scope: `research_agent` missing an `allowed_tools` key entirely (defaults to
all 53 tools); extending the existing `tools/confirm.py` gate to
`write_agent_config`/`write_config`; formal confused-deputy enforcement + test; upgrading
`filter_output()` from substring matching to regex/semantic; confirming `run_model_conference`
is scoped to head-layer-only.

## Decision — two waves, not one pass

Mike's question: since email/web access just shipped and calendar/CardDAV integrations are
still coming, is running the full red-team suite now premature — will it need repeating?

Answer: B1 splits cleanly. The **direct-injection** half (9 categories — tool inquiry, persona
adoption, prefix forcing, etc.) tests the Coordinator/Synthesizer's own prompt handling and
doesn't depend on which integrations exist. The **indirect-injection** half (email body,
calendar title, web page, contact note) tests integration-specific untrusted-content handling
and would need re-running for every new integration added after.

- **Wave 1 — run now:** B1a (direct-injection suite) + B2 (remainder) + B4 (error
  handling/degradation). None depend on integration count. ≈ 4.5–5.5 sessions, about a week.
- **Wave 2 — hold:** B1b (indirect-injection — spot-check each new integration as it ships,
  then one consolidated pass) + B3 (baseline doc, written once, not rewritten per integration),
  gated on Track E reaching feature-complete for this phase. Lines up with CLAUDE.md's existing
  deferred item, "Full OWASP audit before Beta." ≈ 1–1.5 sessions plus near-free per-integration
  checks.

## Addition — recurring security-review protocol

Added at Mike's request, after confirming it's advisable rather than pushing back: a one-time
pass doesn't answer "is it still safe after the next feature ships." Two triggers:

1. **Event-triggered:** every new untrusted-content integration gets its indirect-injection
   spot-check before/at deploy — the incremental version of B1b, and what actually prevents
   "repeat the whole exercise."
2. **Calendar-triggered:** quarterly (or per-roadmap-phase) re-run of the B1a suite + B2's
   cross-agent exfiltration probes as a health check.

To be written into B3's baseline document (`archive/security/security_baseline_*.md`) rather
than a new standing file, per CLAUDE.md's "One Home Per Rule Class."

## Options considered and rejected

- Running the full B1 sweep now as one pass — rejected, would force repeating the
  integration-dependent half per future integration.
- Writing B3 before B1/B2 settle — rejected, it's a synthesis document; premature writing means
  rewriting.

## Deferred

All actual B1–B4 execution — this session was scoping only. Wave 1 (B1a, B2 remainder, B4) is
ready to start next session with no further scoping needed.

## Where the detail lives

Full plan document (estimate tables, per-item resource weight, plain-language summary):
`~/.claude/plans/scope-out-executing-b1-b4-deep-sun.md` — **not repo-tracked**, it's a Claude
Code plan-mode artifact outside the project. This writeup and the
[PROJECT_LOG.md](../PROJECT_LOG.md) entry carry its substance so nothing is lost if that file is
later cleared. Backlog entry: `DEV_BACKLOG.md` (see `/archive` step 5).
