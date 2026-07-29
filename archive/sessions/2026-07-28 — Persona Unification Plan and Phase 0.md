# Persona Unification — Plan and Phase 0
**Date:** 2026-07-28
**Type:** Architecture — planning + execution (in progress)

---

## What prompted this

Started as a CalDAV setup task (new Google account `diamond.mike.mt@gmail.com` for a London base). User flagged that a single global `config/modules/caldav.yaml` doesn't scale — "each persona or user will need their own link to their own calendar." That opened an audit of the whole persona mechanism.

## What the audit found

The persona system is half-implemented. 20 code sites independently read `AI_TEST_PERSONA` and each silently falls back to a global path when unset. Consequences, all verified against the Mac tree:

1. **Split history** — cutover ~2026-06-26 when the browser started sending `persona=mike`. 9 logs + 6 journals + FAISS index in `data/`; 1 file each in `data/personas/mike/`. Pattern Miner reads the persona tree, so sees almost nothing.
2. **Commingled data** — `data/logs/1660-06-01.json` (Pepys test artifact) beside `data/logs/2026-06-21.json` (real clinical content: mania/hyper-arousal, sleep deficit).
3. **Three persona-blind tools** — `tools/caldav.py`, `tools/agent_config.py` (7 live health/finance state files), `tools/wishes.py` (estate/medical/POA).
4. **Three global config files holding per-user data** — `caldav.yaml`, `scheduler.yaml`, `profile.yaml`. `load_profile()` falls back to root, so **every synthetic persona is injected with "Name: Mike, London, Europe/London."**
5. **`## Development Persona`** injected into every system prompt (`core/orchestrator.py:162`) — including real sessions.
6. **Persona name unvalidated** — arrives in HTTP body, goes straight into a file path. `write_persona` makes it an arbitrary-path write.

Also found: concurrency hazard — identity lives in process-global env but sessions run on a *pooled* executor thread (`core/server.py:238`) and specialists fan out across more threads, so overlapping requests from different personas can cross-contaminate.

## Corrections made during the session

- **Earlier claim was wrong:** I said `config/goals.yaml` / `mission.md` / `prime_directive.md` were empty and the Goals Interview write-back had failed. Wrong files — the real output is at `config/personas/mike/{goals.yaml, mission.md, prime_directive.md}`, populated 2026-06-13, chmod 600, substantive. Root-level files are unused stub templates. `archive/plans/goals_interview_fix_prompt_2026-07-28.md` overstates the problem and needs correcting.

## Decisions taken (user)

1. **Fail closed** — no persona resolved = hard error. Deliberately surfaces every path that should require a user but doesn't.
2. **Data reset** — global `data/` contents are all test output; move aside (not delete) to a timestamped archive. Keep `config/personas/mike/*` and `data/baselines/*`.
3. **Full sweep now** including `core/orchestrator.py` — A8 refactor is gated behind blocked A7, not imminent. But: "wary of breaking what we have, take extreme care."
4. **All three config files go per-persona.** One scheduler daemon serves all personas for now.
5. **Vocabulary** — `persona` stays the code term, "users" casually. Strip qualifiers only: `AI_TEST_PERSONA` → `METATRON_PERSONA`, `## Development Persona` → `## User`. Directory names, `--persona`, systemd units, APK all untouched.
6. **Every interaction treated as real, always** — pragmatic shift to get the tool working, not a philosophical claim.

## Plan

Approved plan at `~/.claude/plans/review-the-above-review-polymorphic-squid.md`. Nine phases, 0–8, each independently verifiable and revertible. Key safety mechanism: `METATRON_PERSONA_STRICT` switch — phases 2–6 ship in **audit mode** (logs which code paths fail to pass a persona, behaves exactly as today), flip to hard errors only after 7 clean days including a Sunday (two weekly scheduler jobs only fire then).

Highest-risk step identified: **Phase 4 ordering.** `config/profile.yaml` and `config/modules/scheduler.yaml` are git-tracked; their per-persona replacements are gitignored. Deploying first pushes the *deletion* to the VM but not the *replacements* — scheduler loses all jobs. Files must be scp'd to the VM before the code deploy.

Security fix folded into Phase 4: `write_calendar_event` accepts a model-supplied `calendar_url` that overrides config — an exfiltration path reachable via untrusted calendar content. Parameter to be removed.

## Session log

### Pre-work (before plan mode)
- `config/modules/caldav.yaml` untracked from git (`git rm --cached`) + added to `.gitignore` under "CalDAV credentials — sensitive". **Not yet committed** — user asked to hold commits until done.
- `caldav.yaml` pre-filled with `calendar_url` (Google CalDAV pattern), `username: diamond.mike.mt@gmail.com`, `timezone: Europe/London`. `enabled: false`, `password: ""` pending app password — Google App Passwords requires 2FA enabled first; user reported the link non-functional (expected on a new account without 2FA).
- `archive/plans/goals_interview_fix_prompt_2026-07-28.md` written (needs correction per above).

### Phase 0 — COMPLETE
- `git tag pre-persona-unification` → resolves to `814e6c3`. Local rollback point.
- **VM backup verified:** `~/metatron-backups/pre-persona-unification-2026-07-28-persona-unification.tar.gz` (7.1 MB). Restore test into scratch dir: data 243/243 files, config 53/53 files. `sqlite3` not installed on VM so DB row count unverified, but file captured and out of scope anyway.
- **VM inventory taken** — and it overturned the plan's central data assumption (below).

### MAJOR CORRECTION — the VM's global tree is not test leftovers

My Phase 6 strategy was built on the Mac's layout. The VM is materially different:

| | global tree | `personas/mike/` |
|---|---|---|
| 2026 journal | **160 KB, 24 days** (Jun 22 – Jul 27), 15–25 entries/day | 21 KB, 10 days |
| logs | 31 files | 11 |
| conversations | 7 | 0 |
| FAISS memory | 179 KB (Jun 25) | 147 KB (Jun 29) — **both populated, different content** |

Newest global journal entry (2026-07-27) is real personal writing. The global tree holds ~8× more journal content than the persona tree.

**Root cause — not a date cutover, a process split:**
1. `metatron-server.service` runs `--persona mike`; **`metatron-scheduler.service` had no `--persona` flag** and no persona in `.env`. Every scheduled check-in / Diarist / Pattern Miner run wrote to the global tree.
2. The Diarist thread race — `run_session` sets then *pops* process-global env while the Diarist runs fire-and-forget on a daemon thread; if the request finishes first, the Diarist's write lands globally even for app sessions.

Both are fixed by the plan (Phase 2 thread-local identity, Phase 3 scheduler persona). Only the *data strategy* was wrong.

**User decision after seeing the evidence:** expunge anyway (this is test-phase output; move-aside + backup makes it doubly recoverable). Scheduler fix applied immediately.

### Scheduler fix — APPLIED (VM)
- Unit backed up: `~/metatron-backups/metatron-scheduler.service.pre-persona-2026-07-28`
- `ExecStart` now ends `core/scheduler.py --persona mike`; `daemon-reload` + restart; verified `active` and the running process carries the flag.
- `CLAUDE.md` systemd block updated to match, with a note explaining why the flag is load-bearing.

### Pre-existing bugs found in scheduler logs (NOT fixed, backlog)
1. **`companion_checkin` errors on every fire** (07:35, 09:05, 10:35, 12:05) — error logged ~90 min after firing, suggesting a timeout. A core proactive feature failing silently.
2. `Object of type AgentRecord is not JSON serializable` — trace serialization, every scheduler job.
3. `[vertex_cache] native loop failed (404 … cached content metadata for 3167247740363079680)` — stale cache ID reused after expiry, falling back to compat on every call.

### Phase 1 — COMPLETE
- **`core/persona.py`** (new, stdlib-only so no circular-import risk): `resolve_persona()`, `validate_persona_name()`, `persona_scope()`, `persona_config_dir/data_dir/md()`, `list_personas()`, `current_persona()`, `is_strict()`.
  - Resolution order: explicit arg → thread-local → `METATRON_PERSONA` → `AI_TEST_PERSONA` (deprecated, warns once) → fail.
  - **Fail-closed by default.** Audit mode requires `METATRON_PERSONA_STRICT=0` **and** `METATRON_PERSONA_FALLBACK=<name>` together — setting strict=0 alone still raises, so a half-configured deploy can't silently write to the wrong persona.
  - Audit log at `data/diagnostics/persona_audit.jsonl` (deliberately *not* under `data/logs/`, which Phase 6 expunges).
  - Name validated against `^[a-z0-9][a-z0-9_]{0,39}$` — closes the path-traversal hole where `persona` went from HTTP body straight into a filesystem path.
  - Thread-local identity + env mirror for unconverted code; both restored on exit including on exception.
- **`tests/test_persona_resolver.py`** (standalone runner, no pytest — matches existing `tests/run_phase*.py` convention). **23/23 pass**, including a concurrency test proving two threads in overlapping scopes never see each other's persona.
- Verified nothing imports the new module yet; `orchestrator`, `scheduler`, `router`, `memory` all still import cleanly.
- Noted: `aiosqlite` missing from the **Mac** venv (in `requirements.txt`, so VM is fine) — pre-existing local dev gap, `core.server` won't import locally.

### Phase 2 — COMPLETE (committed `82e583a`, deployed)

**All 20 read sites converted.** `grep AI_TEST_PERSONA core/ tools/` outside `core/persona.py` is now empty (code *and* docstrings).

- 11 files gained `from core.persona import persona_data_dir / persona_config_dir / persona_md`: `logger`, `crm`, `context_tracker`, `persona`, `goals`, `config_writer`, `pattern_miner`, `diarist`, `baselines`, `wisdom`, `core/memory`.
- `core/orchestrator.py`: `load_recent_context()` and `_load_coordinator_context()` converted; both env-var bridges (`run_session`, `run_pipeline_session_stream`) replaced with `persona_scope()`.
- `run_pipeline_session_stream` split into a thin scoped wrapper + `_run_pipeline_session_stream_inner` — avoids re-indenting a large generator body while still binding the persona on the thread that iterates it (the executor thread, not the event loop).
- **Four thread boundaries bound:** 3 parallel tool-dispatch sites (2 Anthropic-style, 1 Gemini-style) + the specialist fan-out, each capturing `current_persona()` alongside the existing `_parent_trace`/`_parent_agent` pattern.
- **`tools/subagent.py`**: `os.environ.get("AI_TEST_PERSONA")` → `current_persona()` on both paths. This is the Diarist fix — a fire-and-forget subagent outlives its request, so it must resolve identity on the *calling* thread before the parent scope exits.
- `core/server.py` needed **no changes** — both endpoints already pass `persona` explicitly into functions that now enter the scope on the executor thread.

**Verification:**
- 23/23 resolver tests pass on Mac *and* VM.
- Smoke test: paths resolve per-persona; a different persona gets different paths; unbound access raises `PersonaError`; `../../etc` rejected.
- Live end-to-end session through the running VM server returned a coherent, personalised response.
- **`data/diagnostics/persona_audit.jsonl` does not exist** — zero unresolved lookups under real traffic.
- **Today's writes all landed in `data/personas/mike/`** (`journal/2026-07-29.json`, `traces/2026-07-29.jsonl`); the global tree received nothing new. The journal entry is the decisive proof — that is the Diarist path that previously scattered.

**Near-miss worth recording:** `deploy.sh` restarted the services *before* `systemctl daemon-reload`, so the newly-added `Environment=` lines were not loaded — the services briefly ran with `METATRON_PERSONA_STRICT` unset, i.e. fail-closed by default, in production. Caught from deploy output, fixed with `daemon-reload` + restart, verified via `systemctl show -p Environment`. **Lesson: unit-file edits need `daemon-reload` before, not after, a deploy that restarts services.**

`config/modules/caldav.yaml` deletion propagated to the VM as expected — confirmed safe first (`enabled: false`, empty URL/password, so behaviour is identical).

### New backlog item found
`/session` (non-streaming) leaks the `[CONTEXT]{...}[/CONTEXT]` block into the response body — the parser that strips it lives only in `run_pipeline_session_stream`. No user impact (the app uses the streaming/WebSocket path), but the non-streaming endpoint also never writes the context tracker.

### Next: Phase 3
`caldav` / `agent_config` / `wishes` persona-awareness, scheduler `fire_function` persona, `_log_conversation` → per-persona path. Move `data/config/`'s 7 live health/finance state files in the *same* change as the read-path switch.

## Deferred / open

- **Roadmap privacy carve-out wording** — `archive/plans/phase5_to_future_roadmap_2026-06-10.md:38-41` permits persona data on any cloud model as "test data." After this work nothing at runtime distinguishes synthetic from real, so the rule's enforcement depends on a distinction the system no longer makes. Needs explicit sign-off; documentation-only (no code keys cloud-routing off persona).
- **CalDAV password** — blocked on Google App Password generation.
- **`data/baselines/aspirational_baseline.json`** has `"persona": ""` — untagged. Fix during the sweep.
- **Goals interview fix prompt** needs rewriting to reflect the corrected finding.
