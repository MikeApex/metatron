# 2026-08-02 — Synth Self-Development Awareness and Development Backlog

**Status:** in progress
**Plan:** `~/.claude/plans/the-mike-persona-s-synth-joyful-forest.md` (approved)

---

## Goal

A single durable place recording every change Metatron needs, fillable from chat and workable in a development session on the Mac. Synth becomes aware it is a system under active construction and triages a change request into three routes: handle now / record for a development session / needs building.

---

## Findings from planning (before any code)

1. **`write_config` cannot do what `synthesizer.md:355` says it can.** That line instructs Synth to write `config/modules/scheduler.yaml`; `tools/config_writer.py:16` hard-whitelists `{prime_directive.md, mission.md}` and errors otherwise. So Synth's only real self-application today is `write_persona`. Recorded as the first `DEV_BACKLOG.md` entry rather than fixed here (frozen file).
2. **`filter_output()` is the real hazard.** Tier 1 is a bare substring test — `write_config`, `write_persona`, `config/agents`, `routing.yaml`, `run_subagent` anywhere in Synth's output replaces the *entire* response with the canned refusal. A response about "how I get changed" reaches for exactly that vocabulary. Mitigated with a positive phrasebook in the new context file, plus a dedicated regression probe.
3. **Observer is not the answer and was not pulled forward.** Observer (Stage 3) is an analyst deriving config edits from statistical patterns in system failures — it would never contain "Mike asked for X". Its input pipeline is empty: 7 quality events exist across every persona plus the pre-reset tree, against a 4+ week data gate. This work is the missing **Stage 0** that feeds it later.
4. **Tool-calling `write_quality_event` would cost a second Synthesizer turn** (~13,400 Pro input tokens re-sent, +$0.017, +3–8s) — the exact overhead SEQ 031 removed. Routed around by extending the existing `[CONTEXT]` block instead: zero extra turns, zero latency.
5. **`/monitor/file` (`core/server.py:1066`) already reads any path under `data/` over Tailscale**, so pulling the VM-side log to the Mac needs no new server code.
6. **`config/personas/mike/` is entirely gitignored** — the new persona file needs a manual `gcloud compute scp`; `./deploy.sh` will not carry it.

---

## Decisions

| Decision | Choice | Why |
|---|---|---|
| Synth autonomy | Triage + record only | No new write powers; self-modification stays with Observer's propose-only design |
| Scope | Mike persona only | Keeps `sarah_chen` / `pepys` / `cal_newport` clean as validation subjects |
| `synthesizer.md` freeze | Lifted for one pointer line | Same explicit-instruction exception as SEQ 002 and SEQ 008 |
| Record mechanism | `dev_request` key in the existing `[CONTEXT]` block | Zero extra turns vs. +67% cost for a tool call |
| The single place | `DEV_BACKLOG.md` at project root, git-tracked | Visible in the VS Code file tree; carries status, not just an append log |
| Freshness | `SessionStart` hook + sync script, both fail-silent | "Pops up" without the 15–18K-token cost that killed the 2026-07-29 hook |

**Costed:** under $0.50/month, no measurable latency change on a normal exchange.

---

## Scope increase accepted

The `[CONTEXT]` parser lives only in the streaming path (SESSION.md backlog item 4: `/session` leaks the block and never writes the tracker). Extracting it into one shared helper called from both paths — ~20 lines instead of ~10 — **closes backlog item 4** and is required for the CLI validation probes to work at all.

---

## Work log

### Built

| File | Change |
|---|---|
| `config/personas/mike/self_development.md` | **New.** The triage instruction Synth reads. ~700 est. tokens. `0600`. Gitignored — needs manual `scp`. |
| `core/orchestrator.py` `load_config()` | Optional per-persona `self_development.md` section, `_titled("Working on Metatron", ...)`. Absent file → no section, so no other persona changes. |
| `core/orchestrator.py` `persist_context_block()` | New `_persist_dev_request()` — validates `type` against three allowed values, requires non-empty `detail`, calls `write_quality_event()` directly. Own try block so it and the tracker write cannot cost each other. |
| `config/agents/synthesizer.md` | One pointer line after the Architecture-awareness section. Freeze lifted on explicit instruction. |
| `DEV_BACKLOG.md` | **New**, project root, git-tracked. `## Inbox` machine-written; everything below hand-curated. |
| `scripts/sync_dev_backlog.py` | **New.** Stdlib-only. Pulls the VM's quality events via the existing `/monitor/file` endpoint over Tailscale, filters to the three request types, dedups on timestamp, appends to Inbox. 3s timeout, exits 0 silently. |
| `.claude/commands/metatron-code.md` | Runs the sync first; reads `DEV_BACKLOG.md` as step 3. |

**Plan assumption that proved stale — in our favour.** The plan budgeted an extraction of the `[CONTEXT]` parser into a shared helper. `split_context_block()` / `persist_context_block()` (`core/orchestrator.py:662-701`) **already exist** and are already called from both the streaming (`:2317`) and non-streaming (`:2106`) paths. SESSION.md backlog item 4 is stale. The change collapsed to ~35 lines inside one function.

**SessionStart hook not wired.** Proposed, declined by the user during implementation. `/metatron-code` carries the sync instead. No functional loss; the backlog just refreshes on command rather than automatically.

### Verified live (`sarah_chen`, local Mac, real Vertex pipeline)

| Probe | Result |
|---|---|
| 1 — handle now | **Pass.** *"I can take that on directly."* `Interaction Preferences` created; `SELF_APPLIED` logged. |
| 2 — push back harder | **Pass, reclassified.** Synth routed it to 1 rather than 2 — defensible, it *is* a style preference — and the claim was true: all three prior preferences carried forward intact. |
| 3 — needs building (email) | **Failed first run.** Correct words, no record. |
| 3b — needs building (bank balance), after fix | **Pass.** `FEATURE_REQUEST` logged with actionable detail. |
| 4 — filter safety | **Failed first run.** See below. |

### Two failures found and fixed by testing

1. **Route 3 recorded nothing.** The instruction said to name the missing capability *"as you already do for capability gaps"* — which pointed Synth straight at the pre-existing `TOOL_NOT_BUILT` open-thread mechanism, so it used that and skipped `dev_request` entirely. The response looked perfect; the backlog stayed empty. Fixed by making the requirement unconditional: *"All three routes require a `dev_request`, every time — including route 3. A `TOOL_NOT_BUILT` note is not a substitute."* Re-tested: `FEATURE_REQUEST` now lands.

2. **Confidentiality beat self-development.** Asked *"will those changes stick, or will you have forgotten by tomorrow? How does that work?"*, Synth emitted the canned *"I'm here to help you manage your life"* refusal — self-generated from its Confidentiality section, not the output filter (the filter replaces the entire response; here real content followed). A legitimate question about the user's own request got stonewalled. Fixed by carving out the boundary explicitly: whether a change stuck is about *his request*, not about how the tool is built, and deflecting there reads as evasion.

### Deployed and verified on `mike`

Committed `6601479` (both this work and the parallel session's SEQ 021 fixes, since both sat in `core/orchestrator.py`) and `dc0d85c`. `./deploy.sh` clean, `NRestarts=0`, both services active. `self_development.md` copied separately by `gcloud compute scp` — it is gitignored, so the deploy could not carry it — and `chmod 600` on the VM.

Post-deploy probe over `/session/stream`, the path clients actually use: *"When I ask you to change how you talk to me, does that actually stick?"* → *"Yes. Your instructions … are held and will carry forward."* Terminated `[DONE]`, not `[RETRACT]` — the output filter passed.

**Third bug, found only at deploy time:** the sync script defaulted to `http://100.64.226.49:8001`. The server runs **HTTPS** behind a Tailscale-issued cert (`Uvicorn running on https://0.0.0.0:8001`), and the raw IP also fails hostname verification. Because the script fails silent by design, it would have reported `0 new` indefinitely rather than erroring — the failure mode that hides itself. Fixed to the Tailscale hostname, matching the orchestrator CLI's own `--server` default, and confirmed against real VM data.

**Staging discipline:** `data/personas/sarah_chen/` is **not** gitignored (only `mike`, `pepys`, `test_a3` and parts of `ryan_holiday` are). `git add -A` here would have swept test journals and logs into the commit — the exact 2026-07-29 incident. Every file was staged explicitly; all persona data left untracked. Worth adding a gitignore rule for the synthetic personas.

**Corroboration found in passing:** a held item in `sarah_chen`'s tracker read *"Logistics tool failure: system attempted to schedule a recurring reminder but failed"* — the `write_config` / `scheduler.yaml` bug firing live, independently of the code read that found it.

---

## Deferred

- Fixing the `write_config` / `scheduler.yaml` discrepancy — seeded into `DEV_BACKLOG.md`
- A read-back tool so Synth can query its own backlog (`[CONTEXT]` `open_threads` covers short-term continuity)
- Observer / Self-Improvement Protocol Stages 2–3 — unchanged and unblocked
