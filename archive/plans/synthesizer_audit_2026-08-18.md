# Synthesizer instruction file audit — proposal for approval

*2026-08-18. Source handoff: `archive/handoffs/2026-08-18-synthesizer-audit-prompt.md`.
No edits have been applied — every change below waits on Mike's approval.*

**Measured:** `config/agents/synthesizer.md` is **50,704 chars / ~12,700 tokens** (handoff said
50,703 — confirmed). It is the dominant share of every interactive Synthesizer prompt and of
cache creation once the caching fix lands.

**Proposed landing: ~9,000–9,300 tokens (≈28% cut)** — moving ~2,600 tokens to three on-demand
modules and cutting ~800 of duplication. **The D2 target of 3,500–5,000 tokens is not reachable
without cutting incident-backed behavioural rules**, which the handoff forbids and which would be
reverted. The honest finding is structural, stated in § 5.

> **Economics updated 2026-08-18, after the caching fix landed (other window):** the cost case
> for this trim fell **4×** ($11.49 → $2.87 per 1,000 turns), and output + thinking is now 69%
> of turn cost. **This audit proceeds on adherence grounds, not cost** — a 12.7k-token
> instruction file dilutes its own every-turn rules (the project's documented length→adherence
> effect), and the Synthesizer's live failures are adherence failures. Two consequences carried
> into the verdicts: the case *against* squeezing behavioural rules toward the D2 number is now
> stronger (§ 5), and the module pattern spends an extra model round — thinking, the expensive
> side — to save cached input, the cheap side. That nets out only because loads are rare
> (2–3 scheduled sessions/day, occasional research dispatches). **Do not extend the module
> pattern to any per-turn load signal on the old economics** — it would cost more than it saves.
> The thinking budget is the bigger cost lever and is recorded separately; independent of this
> audit.

---

## 1. Where the growth came from (step 1, done before judging)

| Date | Commit | Added | Bytes |
|---|---|---|---|
| ≤ 06-26 | initial design → `5df05aa` | the body: role, integration, proactive anticipation, `[CONTEXT]` contract, onboarding, research requests | ~36k base |
| 08-02/03 | `b184d92` `799aa3f` `6601479` `7ced40b` `2f74cd2` `8e2983f` | clock authority, recap guardrail, check-in restraint (5 rules), scheduler grants, `update_goal` | → 40,727 |
| 08-04 | `ca993fe` | provenance rule, enforced confirmation gate | 40,727 |
| 08-08 | `c4ff279` `7c70cd9` | profile misattribution hardening; clinical thread lifecycle | 43,655 |
| 08-09 | `82d394b` `6330029` `b9ea29f` | scheduler prompt ≠ user speech; sleep comparability; obligations + passed events | 48,073 |
| 08-10 | `a36d8c2` | provenance line semantics (SOURCES / RETRIEVAL: NONE) | 48,862 |
| 08-15 | `6913ad7` `1831730` `2602e2e` | −19 lines (evening ritual → persona layer); ACTIONS EXECUTED line; approval-tap completion | 49,174 |
| 08-16 | `360b843` | knowledge layer (`read_wisdom`/`write_wisdom` conduct) | 51,086 |

**Verdict on the +17% since 08-08: it is not bloat.** Ten commits of 4–8 lines, each with a
named incident behind it. There is nothing in the recent growth to bulk-delete; the leverage is
in the June body (episodic conduct that loads on every turn) and in duplication that accreted
across the whole period.

---

## 2. Per-section verdicts

Sizes are ~tokens. **KEEP** = stays in file. **MOVE** = to a `config/modules/synthesizer_*.yaml`
loaded via `read_agent_config`. **CUT** = removed (destination stated).

| Section | ~tok | Verdict | Reasoning |
|---|---|---|---|
| Preamble + Role | 213 | KEEP | identity; cheap |
| Confidentiality | 221 | KEEP verbatim | B1 disclosure suite tests exactly this wording |
| CRITICAL — mandatory surface rules | 468 | KEEP verbatim | A4 clinical hard-fails; peak-attention position is deliberate (D2 ordering principle) |
| What you receive | 555 | KEEP | clock authority (SEQ 008) and the ACTIONS EXECUTED line (`1831730`, doubled-confirmation incident) are both incident-backed |
| Direction and prioritization | 1,220 | KEEP | eight rules, every one an incident (recap, raise-once, explain-once, "enjoy", sleep comparability, double-counting, repeated-instruction ×2); all fire every turn — the module pattern cannot touch every-turn judgement |
| Constructing research requests, steps 1–5 | ~600 | **MOVE** → `synthesizer_research_requests.yaml` | used only when the Synthesizer itself dispatches Research; load signal: "before calling Research" |
| — provenance line semantics (bullet 6) | ~260 | KEEP | research output usually arrives via the Coordinator's dispatch, so this must be present on turns that never loaded the module. Still live post-guard: Python now **withholds** the searched-and-failed case, but `[RETRIEVAL: NONE]` still marks never-searched answers and this text governs those. One sentence to trim: the "or ask the specialist that holds the real feed" phrasing predates the guard; re-word to match the directive style. **No provenance judgement is reintroduced** |
| Multi-round specialist chains | 365 | KEEP, trim example | chain limit + mid-chain updates are behavioural; the sore-throat worked example (~80 tok) can go |
| Keeping the conversation alive | 77 | KEEP | cheap |
| Onboarding and baseline interviews | 305 | **MOVE** → `synthesizer_onboarding.yaml` | fires only on `BASELINE_INCOMPLETE` or a new user; load signal is the flag itself |
| Scheduled session conduct + morning + evening | 1,330 | **MOVE** → `synthesizer_scheduled_sessions.yaml` | needed only when a scheduler prompt opens the session; interactive turns (the 46×, 22,967-token path) never use it. Cost: one `read_agent_config` round on 2–3 scheduled sessions/day — the cheap, cached path. The obligations and passed-event rules (`b9ea29f`) move with it intact |
| What you handle directly | 84 | KEEP | cheap |
| Response length and tone | 154 | KEEP | voice-mode formatting matters on every spoken turn |
| Response format — `[CONTEXT]` | 697 | KEEP verbatim | load-bearing: `split_context_block()` / `persist_context_block()` parse it every turn; changes only with a matching test |
| Integrating specialist outputs | 736 | KEEP, dedupe | sanity-check + catch-up rules are behavioural; the two held-items bullets restate Response format's `held_items` definition — consolidate (−~150) |
| Cross-domain divergence | 320 | KEEP | every-turn judgement |
| Overcommitment pattern | 296 | KEEP | every-turn judgement; trim the Phase 6+ personalization note into § Enhancement backlog (below) |
| Architecture awareness | 527 | KEEP trigger, **MOVE** field spec | the "notice gaps" duty stays (~150); the five-field `ARCHITECTURE_GAP` report format moves to `synthesizer_onboarding.yaml`'s sibling or inline in Internal flags as one line — the full spec is needed only when actually filing one |
| Proactive Anticipation + scan + tiers | 584 | KEEP | mandatory every-exchange pass; tiers table is the safety/opt-in contract |
| How confirmation actually happens | 337 | KEEP verbatim | `2602e2e`, four days old, incident-backed |
| Where the idea came from changes the tier | 462 | KEEP verbatim | external-origin escalation is security posture for attacker-writable text |
| Social outreach | 171 | KEEP, trim | keep the two modes + opt-in; the agent-to-agent Phase 6+ paragraph → § Enhancement backlog |
| When the tool isn't built yet | ~180 | CUT to one line | `TOOL_NOT_BUILT` is already defined in Internal flags; keep the "say so directly" sentence there |
| Two "Note for future development" italics (voice.md / vocal stress) | ~440 | **CUT from live text** → new `## Enhancement backlog` | developer notes, zero runtime work; see § 3 |
| Internal flags | 431 | KEEP, dedupe | the authoritative flag list; ROUTING_MISS + `write_quality_event` instructions currently appear in 4 places — this section becomes the single home, others keep one-line triggers (−~200 net across the file) |
| Tools available | 1,800 | KEEP, light copy-edit only | the entries for `read_profile`, `read_wisdom`, `update_goal`, `write_schedule` are long **because they are recent incident-backed conduct** (08-15/08-16); a named tool is a specification. One reword: line 432's "`send_email`" reference (see § 4.2) |

**Net movement:** MOVE ≈ 2,600 tok · CUT/dedupe ≈ 800 tok · file lands ≈ 9,000–9,300 tok
(~36 KB). Still comfortably above the 4,096-token Vertex cache floor (trap 6) — checked, not
assumed — and `_pad_for_vertex_cache()` remains the backstop.

---

## 3. The Enhancement backlog premise was false — and the fix is to create one

**The handoff's constraint "`## Enhancement backlog` … survives verbatim" is moot:
`synthesizer.md` has never had one** (verified: no commit ever added the string; nine specialist
files have the section, the Synthesizer does not).

Proposal: **create** `## Enhancement backlog` at the bottom of the file — matching the
nine-agent convention and the "only copy" rule — and move into it the four future-development
fragments currently sitting in live instruction text: voice.md style guide (Voss/Socratic),
vocal stress detection, the Phase 6+ personalization note, and agent-to-agent outreach
coordination. This follows `.claude/rules/agent-files.md` exactly: aspiration under a deferred
heading is the build queue; aspiration in live text is what the model reads as capability.
Net token change ≈ 0 (moved, not cut) — the gain is that the model stops reading them as
instruction. Cutting them to `DEV_BACKLOG.md` instead would save ~450 tok but breaks the
"agent file is the only copy" convention; not recommended.

---

## 4. Required companion changes (both Red-tier, both in this pass)

1. **Grant `read_agent_config` to the Synthesizer** in `routing_cloud.yaml` and `routing.yaml`
   — the module pattern's "no code change needed" holds only if the grant exists, and it
   currently does not. Without it the three modules are unreachable (and would only work by
   accident via the known warn-mode dispatcher gap, which is not a foundation).
2. **Reword line 432** — "gated the same way `send_email` is" names a tool the Synthesizer is
   not granted; `check_agent_tools.py` flags it in the live-but-ungranted class. Reword to
   "gated the same two-step way outgoing mail is" (no backticked name). Pre-existing, cheap,
   same file.
3. **Flag only, not folded in:** `read_wishes` is *granted* (cloud) while the file says read
   access to the wishes store is deferred to Phase 6 with legal review. One of the two is wrong.
   This belongs to the 39-grants decision (`[DB-0810-03]`, @session, blocks A7 check 10) — not
   decided here.

---

## 5. The honest structural finding

The D2 target (Synthesizer at 3,500–5,000 tok) was written in June against a smaller file and
before ten incident-backed rules accrued. **What remains after this audit is almost entirely
every-turn behavioural judgement** — direction rules, clinical surfacing, the ACTIONS line,
confirmation conduct, external-origin escalation, the `[CONTEXT]` contract, tool discipline.
The context-file pattern only relocates *episodic* content, and the episodic content is ~2,600
tok of a 12,700-tok file. Reaching 5,000 would mean deleting rules each bought with a live
defect. Recommendation: **take the ~28% now, treat the D2 number as superseded for this agent**,
and revisit only if D2's output-compression work changes what the Synthesizer receives. The
growth *rate* is the thing to watch (+17% in 8 days); the per-file briefing hook already
surfaces this file's history at edit time.

---

## 6. New files this creates

1. `config/modules/synthesizer_scheduled_sessions.yaml` — scheduled conduct, morning, evening,
   obligations, passed events. Load line in file: on a scheduler-prompt opening.
2. `config/modules/synthesizer_research_requests.yaml` — construction steps 1–5. Load line: before
   dispatching to Research.
3. `config/modules/synthesizer_onboarding.yaml` — baseline interview conduct + the
   `ARCHITECTURE_GAP` field spec. Load line: on `BASELINE_INCOMPLETE` / new user / when filing a gap.

---

## 7. Regression gate (unchanged from handoff, runs after approved edits)

1. `python tests/run_a4_safety.py --suite pipeline` — clinical substance survives.
2. `python tests/run_b1_redteam.py` disclosure suite — Confidentiality holds.
3. One live pipeline turn — `[CONTEXT]` still parses; post-caching-fix, `cache_read` reappears
   under the new (expected) cache hash.
4. `bash scripts/qa_sweep.sh` and `python3 scripts/check_agent_tools.py`.
5. **Addition:** one scheduled-session probe (morning_brief prompt) confirming the module
   actually loads — the one behaviour the A4/B1 suites never exercise.

---

## 8. Execution cost and model

Applying this is mechanical once approved: ~10 edits to one file, 3 new YAML files, 2 routing-file
grant lines, then the gate (§ 7 — the live probes are the slow part, ~30–45 min total). Estimated
~150–250k tokens of session work. **Sonnet 5 can execute the approved table; the judgement was
this document.** Deploy is Denied — the commit is handed back to Mike, alongside the two already
owed (`f4cc812`, research guard).
