# Persona Unification — Complete (Phases 0-8, Strict Mode Live)
**Date:** 2026-07-28
**Type:** Architecture — planning + full execution. Shipped and verified.

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

---

## Phases 3-8 — COMPLETE

### Phase 3+4 (commit `92b51f7` + scheduler crash fix)
- **Persona-blind tools fixed:** `agent_config` (7 live health/finance state files, moved on both machines in the same change so agents kept their memory), `wishes` (estate/medical/POA), `caldav`, `ambient`. `server._log_conversation` now writes `data/personas/{p}/conversations/` — where the monitoring reader always looked.
- **Settings per-persona:** `profile.yaml`, `scheduler.yaml`, `caldav.yaml` under `config/personas/{p}/`, gitignored; tracked originals became `config/templates/`. **Files scp'd to the VM BEFORE the code deploy** — the tracked originals are deleted by the commit and the replacements are gitignored, so the reverse order would have left the VM with neither.
- **`load_profile()` / `load_goals()` root fallback removed.** Verified: a fresh persona now reports `leaks Mike?: False`.
- **Scheduler:** `fire_function()` takes and binds a persona (closing the `ambient_refresh` leak); schedules load per-persona; per-job try/except so registration can't crash-loop; `--persona` now **required**; `fire_session`/`_notify_push` take persona explicitly.
- **Security:** `write_calendar_event` no longer accepts a model-supplied `calendar_url`. It overrode config and let the model choose the destination server for a tool that ships event titles and descriptions — an exfiltration path reachable through untrusted calendar content.
- **`PersonaError` made unswallowable** in the best-effort blocks (memory indexing, ambient load, insight preload). Misfiled data must be loud, not silently absent — this mattered because the user audits traces, and absence is invisible.
- Router diagnostics moved to `data/diagnostics/` — daemon-level, deliberately not per-persona, kept out of user data.

### Phase 5 (commit `af32b5f`)
- `scripts/new_persona.sh` — provisions from templates, validates the name with the same regex the resolver enforces.
- `scripts/check_personas.py` — read-only linter. Severities corrected after first run to match actual runtime behaviour: missing tier files are warnings (`load_config` tolerates them), only genuine breakage errors. Found `data/personas/'Ryan Holiday'` (space in name — resolver rejects it) and an orphaned `test_a3` dir.

### Phase 6 — data reset
- **Mac:** global tree moved to `data/_pre_reset_2026-07-28/`.
- **VM:** same, with a full `MANIFEST.txt`. **Deliberately preserved:** `metatron.db` (the Android app's entire chat history), `push_subscriptions.json` (loss silently kills notifications until the user re-grants permission), `data/baselines/`.

### Phase 8 — rename
- `AI_TEST_PERSONA` -> `METATRON_PERSONA` in the test harnesses (old name still works, warns once).
- Prompt header `## Development Persona` -> `## User`.
- `_titled()` helper dedups tier headings — `write_config()` stores the Goals Interviewer's text verbatim including its own `## Prime Directive` heading, so the prompt carried each twice with an empty section between.

### Constitution (Tier 0, explicitly user-approved)
`## Development Note` **removed**. It made discretion conditional on a development/production distinction the model cannot observe; it contradicted `filter_output()` (plausibly behind SEQ 031, where "daily logistics" tripped the filter and the user got "I can't help with that right now"); and after this work it was the last test/production split left in the runtime, sitting at the highest-precedence context. No visibility lost — that comes from `core/trace.py`, not model self-report. Proposal: `archive/plans/constitution_development_note_proposal_2026-07-28.md`. Lines 1-30 untouched.

### Strict mode — LIVE
Exercised all 21 persona-dependent paths on the VM first; audit log stayed empty. Then removed `METATRON_PERSONA_STRICT=0` / `METATRON_PERSONA_FALLBACK` from both units. Verified with a real session: coherent response, writes to `data/personas/mike/{logs,conversations,traces}`, global tree unchanged, no `PersonaError`, no audit file.

**Decision changed mid-session:** the original plan waited 7 days in audit mode. The user pushed back — worst case looked like a visible error. The counter was that swallowed exceptions make it silent instead, and the Sunday-only jobs were unexercised. Resolution: fix the swallowing, force-exercise every path including the Sunday ones, and flip *before* the test week rather than after. Better outcome — the user gets guaranteed-clean data instead of a week of audit-mode uncertainty.

### Docs
`CLAUDE.md` gained a Personas section (layout, fail-closed resolution, thread-local identity, "never read the env var directly"); tier table repointed at `config/personas/{persona}/`. `CODEBASE_INDEX.md` gained `core/persona.py` and a Scripts section. **Roadmap Section 0: the carve-out permitting persona data on any cloud model is SUPERSEDED** — it rested on a distinction the runtime no longer makes, and the failure mode is real user data on a cloud model.

---

## Two process lessons (both cost real time)

1. **`deploy.sh` restarts services, so systemd unit edits need `daemon-reload` BEFORE the deploy.** Adding `Environment=` lines then deploying meant the services restarted without them — production briefly ran fail-closed. Caught in deploy output.
2. **`py_compile` cannot catch a `NameError`.** A stale `_SCHEDULER_CONFIG` reference in `main()` crash-looped the scheduler after the phase 3+4 deploy. I had grepped for the other removed constants but not that one. Grep for every removed symbol, and actually *run* the daemon — which is how the six-job registration was finally confirmed.

---

## Open / next

- **CalDAV still needs the Google App Password** (requires 2FA enabled first). `config/personas/mike/caldav.yaml` is pre-filled with the address, URL and `Europe/London`; `enabled: false` pending the password.
- **User testing week** — phone browser, MacBook browser, terminal. `--persona` is now required on CLI.
- **Backlog (pre-existing, none introduced here):**
  1. `companion_checkin` errors on every fire, ~90 min after firing — timeout suspected. **Diagnosing next.**
  2. `Object of type AgentRecord is not JSON serializable` on every scheduler job.
  3. `[vertex_cache] 404 cached content metadata` — stale cache ID reused after expiry.
  4. `/session` (non-streaming) leaks `[CONTEXT]` and never writes the context tracker.
- **Goals interview fix prompt** (`archive/plans/goals_interview_fix_prompt_2026-07-28.md`) still overstates the problem — written before I found the real files at `config/personas/mike/`. Needs correcting.

---

## Diagnosis: `companion_checkin` failing on every fire

**Symptom:** 223 scheduler errors — 189 `companion_checkin`, 18 `evening_close`, 14 `morning_brief`, 1 each for both Sunday jobs. Every scheduled job affected.

**My initial hypothesis was wrong.** I read the ~90-minute gap between firing and error as a timeout. It was not — 90 minutes is simply the job interval. The actual error text was `Object of type AgentRecord is not JSON serializable`, which also collapsed two backlog items into one: they were the same bug.

**Investigation:** ruled out the push path (the two `terminal`-notification jobs failed too), then `dispatch_tool` (args are the model's own, no AgentRecord injected), then `context_sections` (all strings, no post-hoc mutation). Rather than keep guessing, reproduced the exact scheduler call path on the VM with a monkeypatched `_log_error` to capture the traceback that the real one discards.

**Result: no error.** The job completed cleanly.

**Root cause: the missing `--persona` on the scheduler unit.** Fixed earlier in this session as a side effect of stopping data divergence — it also fixed 189 recurring failures. Precise mechanism not pinned down (most likely the process-global env var being popped while background threads were mid-flight, crossing thread-local trace state); the resolver's thread-local identity removes that class of failure regardless.

### The more valuable finding, surfaced by the reproduction

The notification body contained the raw `[CONTEXT]{...}[/CONTEXT]` block.

The Synthesizer appends that block instead of spending a tool-call turn on `write_context_tracker` — but **only the streaming path parsed and removed it.** Everything through `run_pipeline_session` leaked it verbatim:
- **every scheduled job** — so push notifications on the phone contained raw JSON
- the non-streaming `/session` endpoint

Those sessions also **never wrote the context tracker**, so proactive check-ins never updated state. The tracker was stuck at `last_session: 2026-06-29`.

**Fix:** `split_context_block()` / `persist_context_block()` extracted and shared by both paths so they cannot drift apart again. Malformed JSON still strips the block (it just does not persist), so it can never reach a user. Verified live: notification body clean, tracker advanced 2026-06-29 -> 2026-07-29 with current threads, no errors.

### Two supporting fixes
- **Scheduler error log now records a traceback.** It stored only `str(e)`; 189 identical one-line entries needed a live reproduction to diagnose.
- **`COORD PACKAGE` debug dump gated behind `AI_TRACE`.** It printed the full routing package to stderr on every session including every scheduled job — flooding journalctl and burying real errors, right before a week of audited testing. A8 scopes it as a deletion; gating keeps the capability.

### Backlog now
1. ~~`companion_checkin` fails every fire~~ — **fixed** (missing `--persona`).
2. ~~`AgentRecord not JSON serializable`~~ — **same bug, fixed**.
3. ~~`/session` leaks `[CONTEXT]` / skips the context tracker~~ — **fixed**, and it was worse than recorded: it affected every scheduled job and every push notification.
4. `[vertex_cache] 404 cached content metadata` — stale cache ID reused after expiry, falls back to compat on every call. **Still open**, cost/latency only.
5. Coordinator ran 7 turns / 48K cumulative tokens on the reproduction — the known coordinator-slimming item (target <=3 turns, <=40K). **Still open.**

---

## Vertex cache — two bugs, one masking the other

**Symptom:** `[vertex_cache] native loop failed (404 NOT_FOUND ... cached content metadata for 3167247740363079680)` on every call, falling back to the compat path.

### Bug 1 — the registry never expired
`_vertex_cache_registry` mapped content hash to cache name and was never invalidated, but Vertex deletes each cache at its `expire_time` (midnight UTC). After the first midnight the registry kept returning a dead name: every call paid a wasted round trip, 404'd, and fell back. It then ran **uncached for the rest of the process lifetime**. The same cache id appeared at 07:35, 09:05, 10:35 and 12:05 — one stale entry, reused all day.

The docstring claimed "rebuild happens automatically on the next miss." There was no eviction anywhere, so there was never a miss to rebuild from.

**Fix:** the registry stores `(name, expire_time)` and treats an entry within 60s of expiry as a miss, so the cache rebuilds *before* it can 404. Plus, on a not-found from the native loop, the dead entry is evicted and rebuilt once before falling back — a cache can vanish early (deleted, or project-evicted), which previously also meant uncached forever.

Deliberately not thread-locked: concurrent specialists could both create a cache for the same hash, but both are valid and the loser is simply unused. A lock would add contention on every cached call to avoid a rare, harmless duplicate.

### Bug 2 — padding under-shot the floor (a regression from earlier today)
Fixing bug 1 stopped the 404 firing *before* creation was attempted, which exposed:

`400 INVALID_ARGUMENT — The cached content is of 3898 tokens. The minimum token count to start explicit caching is 4096.`

**Caused by this session's own work.** Removing the Constitution's Development Note and de-duplicating the tier headings shrank the system prompt below what the padding could absorb — precisely the failure the SESSION.md monitoring note was added to catch after the 2026-06-24 token-reduction pass. The note worked; it just needed someone to read the log.

Root cause: `_pad_for_vertex_cache()` estimated 4 chars/token. That is *optimistic* — it overestimates the token count and therefore under-pads. The real ratio on this codebase's prompts is ~4.4, so a prompt padded to an estimated 4296 tokens arrived as 3898 actual.

**Fix:** assume 5 chars/token and target 25% above the floor plus a flat margin. Underestimating is the safe direction — it pads more than needed, and surplus padding costs nothing because the cache is read rather than regenerated.

### Verified live
| Agent | Real tokens | Result |
|---|---|---|
| Synthesizer | 8,826 (no padding needed) | cache created |
| Coordinator | 4,938 -> 6,127 padded | cache created |

Registry reuse confirmed (`second call reused: True`); `cache_read=9691` present in token-budget lines; zero cache failures after the 14:48:47 restart.

**Lesson recorded:** a fallback that works can hide a bug indefinitely. The 404 was "harmless" because compat caught it — so it sat there for over a month, silently paying full token cost on every call.

### Backlog after this session
- ~~`companion_checkin` fails every fire~~ — fixed (missing `--persona`)
- ~~`AgentRecord not JSON serializable`~~ — same bug, fixed
- ~~`/session` leaks `[CONTEXT]` / skips tracker~~ — fixed; affected every push notification
- ~~stale Vertex cache 404~~ — fixed
- ~~cache padding below the 4096 floor~~ — fixed
- **Open:** Coordinator ran 7 turns / 48K cumulative tokens — the known coordinator-slimming item (target <=3 turns, <=40K). Now the largest remaining cost/latency lever.

---

## Terminal made a real client (`core/remote_client.py`)

**Problem:** `python core/orchestrator.py --persona mike` ran the pipeline in-process, writing to whichever machine ran the command. Used alongside the phone and browser that is not a fourth client — it is a second parallel history for the same person on a different machine, i.e. the same split-brain the persona work exists to prevent, at the Mac-vs-VM boundary instead of global-vs-persona.

**Design finding that changed the implementation:** the plan was to POST to the SSE endpoint. Reading the code first showed that would only half-work — **only the WebSocket path calls `_save_exchange()` and `manager.broadcast()`**. `POST /session/stream` writes the daily JSONL log but neither persists to the shared store nor notifies other clients, so the terminal would have stopped fragmenting the tree while staying invisible to the phone and browser.

**Built:** `core/remote_client.py` connects to `wss://<server>/ws?persona=<p>`. Remote is the default for interactive coordinator sessions; `--local` opts out and warns. New module rather than adding to `core/orchestrator.py`, which A8 will restructure.

**Verified live:** handshake returned 4 exchanges of shared history; message persisted as row #5 in `metatron.db` and seq 005 in the VM conversation log; before/after mtime check confirmed the Mac tree was untouched.

### Also fixed while here
- **Orchestrator CLI was broken** — `import core.trace` at line 28 with the `sys.path` fix at line 57. Broken since the "Add The Book" commit (`c66ed03`); `server.py` and `scheduler.py` both set the path before their imports, the CLI never did. Pre-existing, not caused by this session's work.
- `--persona` made required on the CLI, matching the scheduler.
- **Android APK rebuilt** — the installed build was from Jun 21 and missing five weeks of client fixes including `eea3faf` (WS `shownIds` cap wiping the in-flight exchange id, which hangs the response bubble with no error). Rebuilt and verified to contain current code and target the right server.

### Git history rewrite (user-approved)
`git add -A` swept `data/_pre_reset_2026-07-28/` — 41 files of journals, clinical logs, conversations and `metatron.db` — into commit `89ac3ed`, which reached GitHub before it was noticed. **My error.**

Rewritten with a soft-reset rather than `git filter-repo`: the offending commit was `HEAD~1`, so filter-repo's fresh-clone-and-swap dance was unnecessary risk against a repo containing live gitignored data (`config/personas/mike/`, `.env`, `.venv`). The soft reset touched only git metadata.

**Verified against a fresh clone from GitHub** — four independent tests, no support request needed:
1. Data path in zero commits of a fresh clone
2. `git fetch origin <sha>` for both orphaned commits — GitHub refuses ("couldn't find remote ref")
3. Journal blob unreadable by SHA path
4. Zero objects matching the path across all history

Test 2 is the meaningful one: GitHub *will* serve reachable commits by direct SHA, which is the usual post-force-push concern. It refused both. Object stores garbage-collected on Mac and VM.

**Honest caveat recorded:** this proves unreachability by any client, not that GitHub has physically gc'd its storage, and it cannot prove nothing accessed the data during the ~40 minutes it was live. Only GitHub support can confirm the former.

Also gitignored `dummy` and `data/_pre_reset_*/` so the same sweep cannot recur.

---

## Proactive check-ins were invisible (found during live testing)

User saw an unnumbered "What's going on?" in The Book they had not sent. That is `companion_checkin`'s configured prompt, firing every 90 minutes — **working for the first time**, since it had failed on every fire until the `--persona` fix earlier today.

**The gap:** the scheduler ran the pipeline in-process, so a check-in produced a trace and a push notification but **no conversation record and no database row**. Consequences: no seq (unnumbered in The Book), and completely absent from the phone and browser. Metatron opened a conversation that then appeared nowhere in the user's history. `scheduler.py` had zero references to `_log_conversation`, `_save_exchange` or `metatron.db`.

Same class of bug as the terminal running in-process — a component doing its own pipeline run instead of going through the server.

**Fix:** coordinator jobs now call `remote_client.send_one()`, so a proactive session is an ordinary exchange: conversation record, seq, shared database row, live broadcast to connected devices. Single-agent jobs (`pattern_miner`, `physical_health`) still run in-process — they are analysis runs that write their own outputs, not conversation. Raises on failure rather than falling back, since a silent fallback recreates the invisibility.

Also threaded `is_proactive` through the WS send into the trace; it was hardcoded `False`, so traces could not distinguish a check-in Metatron initiated from a user message.

**Verified live:** check-in landed as conversation `#013` with seq, `metatron.db` row #14, trace `is_proactive=True`.

### Also fixed: The Book numbering live exchanges
Two feeds. `/monitor/conversations` serves the JSONL (has seq); `/monitor/stream` serves trace records (no seq — it is assigned by `_log_conversation` after the trace is written). So exchanges on disk at load time were numbered and live ones were not. Server now attaches seq by matching the conversation record on user text; the monitor carries it into the Column 1 entry, which it had been discarding. Both halves were needed.

### Terminal client regressions (reported immediately, both mine)
- **Ctrl-C hung** — `sys.stdin.readline()` is uninterruptible and `run_in_executor(None, ...)` uses non-daemon threads, so the interpreter waited forever at exit. Replaced with a daemon reader thread feeding an asyncio queue.
- **Responses invisible** — chunks written with no label or colour were indistinguishable from the terminal's echo of the typed input. Now green with a leading newline, plus a prompt on connect.

### Confirmed working during testing
Sync across browser, app and terminal. **Open:** the browser appears to need a manual refresh to show foreign messages — the WS broadcast should push them live, so that is a client-side bug in `static/index.html`, separate from this work.

---

## Trace instrumentation + timezone (and a correction to the coordinator claim)

**Specialists were absent from every trace.** Trace context is thread-local; the specialist fan-out in `_dispatch_from_coordinator` propagated persona but not trace, so each specialist's `push_agent()` landed on an empty context and the record was dropped. The Book showed only coordinator and synthesizer. Predates this session (the original `executor.submit` did not propagate either).

**Correction — the 7-8 turns are NOT the coordinator.** With traces fixed, a specialist-heavy session records:

```
coordinator          turns=[1]
physical_health      turns=[1,2,3,4,5,6,7,8]
synthesizer          turns=[1]
```

The coordinator does **one** turn. The multi-turn sequence is a *specialist* doing 8 internal tool-call turns. The interleaved `turn=2` x3, `turn=3` x3 pattern in the logs was three specialists running **concurrently** — i.e. parallel fan-out already works.

This contradicts the roadmap's D2 item 5, which states "the coordinator makes multiple sequential specialist calls across turns rather than fanning out in parallel" and targets "<=3 turns" at coordinator. The coordinator already meets that. **The real cost driver is per-specialist internal tool-call turns**, which that item does not address. The slimming item needs re-scoping against measured behaviour before any work starts.

**VM timezone was `Etc/UTC` while the user is in Europe/London.** Not merely a display offset in The Book: `scheduler.yaml` times are wall clock, so `morning_brief 07:30` fired at 08:30 BST, `evening_close 20:00` at 21:00, and quiet hours 22:00-07:00 were really 23:00-08:00. Set to `Europe/London`; fixes timestamps and firing times together and follows DST. Scheduler re-registered and confirmed.

**Terminal client now reconnects** with backoff (capped 30s) instead of dying on close code 1012 — a deploy restarting the server killed a live session with an unretrieved-task traceback.

---

## Proactive exchanges, check-in prompts, DST contingency

**Metatron opening a conversation was rendered as though the user typed the prompt**, so Synth appeared to answer itself. The prompt is an internal instruction to the pipeline, not user speech.

Exchanges now carry a `proactive` flag: `exchanges` table (ALTER wrapped for existing DBs), both read paths, persistence, the `stream_start` broadcast, and the conversation log. **All three client render paths** — `history`, `stream_start`, `message` (catch-up) — skip the user bubble when set. Terminal shows `[Metatron checking in]`.

**Deliberate decision:** the prompt stays in the *model* history. History is a strict user/assistant alternation and an empty user turn risks provider rejection — so display and model context are separated rather than conflated. Synth still knows why it spoke; the user never sees a message they didn't send.

Verified: `db #16 proactive=1`, `log #016 proactive=True`, `trace is_proactive=True`. APK rebuilt (3 guards present).

**Check-in prompts rewritten** to lead with a specific outstanding item, and to stop rather than manufacture a topic when nothing is open. The context tracker already held `open_threads` and `follow_ups` and was already in the Coordinator's context — nothing told it to use them. First run produced: *"the most practical one to resolve tonight is how we handle your exercise. We haven't logged any workouts yet this week against your goal"* — specific, tracker-grounded, no generic opener.

**DST contingency.** The OS handles the zone change (verified: Oct 26 -> GMT, Mar 29 -> BST). The gap was the `schedule` library, which computes each `next_run` once at registration while this daemon runs for weeks — so the first firing after a transition would be an hour off and stay stale. The main loop now compares the UTC offset each tick and re-registers on change. No cron entry, no manual step.

Incidentally confirmed the timezone fix working: a test check-in at 22:04 BST was correctly suppressed by quiet hours (22:00-07:00), which under UTC would not have triggered until 23:00 local.

---

## Voice/latency work, client resilience, and a correction

### Fix 2 — blocking the event loop (the "Failed to fetch" cause)
`/transcribe` ran ffmpeg + Whisper and `/tts` ran Kokoro **synchronously inside `async def`**, freezing the whole server for the duration: no HTTP responses, no WebSocket pings. A second voice message during the first transcription reached a live-but-deaf server, which the client surfaced as "Failed to fetch". Both now run on dedicated single-worker executors (not `run_in_executor(None, …)` — the default pool is shared with the LLM producer threads). `/transcribe` gained a semaphore returning a fast 503, ffmpeg reads from memory, and real status codes replaced a bare `FileNotFoundError` catch. `/tts` leaked a wav on every Kokoro failure; fixed.

**Verified:** server answered health checks 3/3 *during* TTS synthesis.

### Kokoro was reloading its model on every single request
Measured on the VM: **15.0s per `/tts` call, three consecutive calls identical.** Breakdown: `import kokoro` 7.3s + build `KPipeline` 3.0s + **actual synthesis only ~3s**. About 10s of every call was model loading, repeated forever.

Cause: `/tts` shelled out to `tools/kokoro/speak.py` as a **subprocess**, so each request spawned a fresh interpreter. `speak.py` even caches the pipeline in a module global — but a new process every time meant that cache could never hit.

The subprocess existed because Kokoro once had its own venv with conflicting dependencies. It was installed into the main venv on the VM on 2026-06-27, making the isolation obsolete — but the workaround stayed, and `CLAUDE.md` still documented the isolated venv as current, which kept it invisible.

Now loaded once in-process, cached behind a lock, warmed at boot. **15.0s → 2.8s.**

### Model warm-up at startup
Embedding (15.7s) and Whisper (14.4s) loaded lazily, so the **first log or journal write after every deploy paid ~15s inside a user's response**. All three models now warm at boot in a background task; memory 2.1GB of 3.9GB with all resident.

### Memory indexing off the critical path
`index_entry()` ran inline in `write_log`/`write_journal` during tool dispatch — ~150-200ms on the VM for a result nothing reads. Moved to `core/background.py` (single worker, drops past a queue cap so it can never become back-pressure). Persona resolved on the calling thread and re-bound in the worker, preserving fail-closed behaviour. **write_log: 150-200ms → 1ms.**

### Conversation anchoring
`#conversation` is a flex column with no bottom alignment, so short conversations packed at the top. Not an ordering bug. Fixed with `margin-top:auto` on the first child rather than `justify-content:flex-end`, which can make overflowing content unreachable in a scroll container. Scrolling now holds position if the user has scrolled up to read (120px slack); history load forces the scroll behind a double rAF.

### WebSocket resilience — the "Tailscale falling silent" cause
Android freezes the WebView on background; the socket dies **half-open** with `readyState` still `OPEN`, `onclose` never fires, and sends vanish silently. The existing 3s reconnect only ran on close, so it never ran. Restarting Tailscale forced a network-change event that finally killed the socket — which is what made Tailscale look responsible.

Added: explicit `ping` handling (>45s silence = dead regardless of `readyState`), `visibilitychange`/`focus`/`online` liveness checks on resume, a 20s backstop interval, `onerror` force-close, and single-flight reconnect that closes the corpse first.

### Corrections recorded
- **"Block connections without VPN" was bad advice.** Tailscale is split-tunnel; Android lockdown blocks non-VPN traffic, so it would have cut general internet on the phone. Only the battery-optimisation exemption is both effective and safe.
- **`companion_checkin` is 180 minutes, not 90** — the user had already changed it, and also replaced the generic `"What's going on?"` prompt with one instructing the Coordinator to lead with a specific outstanding item. My cost estimate of "10-12 pipeline runs/day" was based on the stale 90-minute value; with 180 min and 22:00-07:00 quiet hours it is **~5 check-ins + 2 scheduled = ~7/day**.

### Open
- APK with anchoring + reconnect fixes built (10:00) but **not yet installed** — user testing later.
- Activity-gating for check-ins (skip when no user-originated exchange since the last) still unimplemented; identified in the parked programme as the largest cost lever.
- Sentence-chunked TTS deferred pending judgement on whether 2.8s still feels slow.
