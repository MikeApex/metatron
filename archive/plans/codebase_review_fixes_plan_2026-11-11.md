# Fix plan — the 2026-11-05 whole-codebase review, High and Medium only — 2026-11-11

**Source:** `archive/plans/codebase_review_2026-11-05_fable-5-1.md` (verified; finding numbers below are that report's).
**Base:** `main` at `2dd492a`. No commits since the review.
**Scope rules (Mike, 2026-11-11):**
1. **High and Medium only, by the verified severity** (the report's § 1a). Low, Low-Medium, disproved and accepted-risk items are out — a later review will catch the Lows again.
2. **Nothing that may interfere with a current active build.** Active builds identified: **WhatsApp input** (uncommitted `android/…/whatsapp/`, `android/app/src/test/`, `waprobe/`, modified `AndroidManifest.xml`, `build.gradle`, `.gitignore`) and **the Build vertical** (uncommitted `.claude/agents/build-inquiry.md`, `archive/plans/inquiry_rewrite_2026-09-26.md`; bench test 2 next). The **day planner** has no build in flight but has an undeployed commit (`547c446`) awaiting Mike's live checks. Any finding in those areas is held to Phase 1 for Mike's call rather than built by default.
3. **Everything that needs Mike runs first, in the main chat**, where it is either done on the spot or deferred to a later plan.

---

## Phase 1 — Mike's items, in the main chat (no subagents)

| # | Item | What Mike does / decides | Recommendation |
|---|---|---|---|
| W1 | **#1** — a request field can route the pipeline to OpenAI | Runs `grep -c '^OPENAI_API_KEY=.' ~/multi-model-mcp/.env` (and the same for `ANTHROPIC_API_KEY`) on the VM; removes keys nothing needs | Remove both if set — nothing on the routed path uses them (to be confirmed by grep of `routing_cloud.yaml` before he removes) |
| W2 | **#11** — a second user's data reaching developer channels her consent does not name | Rules on which signal types a second user's data may reach | Report's option: pull her machine-type signals only; `build_read` consent scope fail-closed in the doors; `BUILD_PROPOSED` detail without gap text. **If ruled now, the build is held with the Build items (W6b)** since it lands in `core/build/doors.py` and `tools/build.py` |
| W3 | **#27** (Red) — Synthesizer told to tell the user "I'd need [capability] built first" | Approves Edit prompts in this chat: delete the "tell the user directly" clause at `config/agents/synthesizer.md:360`; delete or re-home the flags section `:354-362` | Delete the clause; delete the section's claim that flags "appear in the context tracker note" (no reader exists) rather than add a `[CONTEXT]` key |
| W4 | **#29** (Red) — Synthesizer holds `read_wishes` / `generate_emergency_card` while its file says no reads before Phase 6 legal review | Chooses: drop both grants from both routing files, or rewrite `synthesizer.md:382` to describe the read path | Drop the grants (keeps the recorded deferral true); fix `archive/plans/future_phases.md:63`'s claim that Logistics holds `read_wishes` |
| W5 | **#44** — the "Recreate from scratch" runbook cannot rebuild the VM | (a) Allows a read of the live VM's `metatron-cert-renew.{service,timer}`, `metatron-server.service.d/host.conf` and the `stop-billing` source so they can be committed under `infra/`; (b) the Android `network_security_config.xml` / `file_paths` tracking is **held for WhatsApp** (it edits `.gitignore`, which is modified uncommitted) | (a) now if he allows the read; the doc steps (cert issue, timers, swap, playwright) go to builder C regardless; (b) after the WhatsApp commit |
| W6a | **Day planner — #5** (nudge due near a fixed session marked carried and dropped, High) **and #33** (paused check-ins keep coming, Medium) | Release to build now, or hold until `547c446` is deployed and live-checked | **Build now, separate commit.** Both are live on the VM today; neither touches `547c446`'s Now/Next rendering; the commit order lets him deploy `547c446` alone first if he wants a clean live check |
| W6b | **Build — #9** (no capability can land at N13, High, dev-only), **#10** (VM tick rewrites a tracked file after the first landing), **#41** (tickets keyed without persona), **#40** (Build block narrated to a second user, `tools/build.py`) | Release or hold | **Hold #9, #10, #41 for a Build session** — bench test 2 exercises Inquiry only and never reaches N13, so nothing is blocked; one prompt written for it. **Build #40 now** — it is user-visible to a second user, lives in `tools/build.py:context_block` only, and touches nothing bench test 2 runs |
| W7 | **Deploy** | `./deploy.sh` is Denied to Claude Code; Mike runs it after the commits | Deploy order in § 4 |

---

## Phase 2 — builders (Opus 5.5 subagents, one worktree each, Amber/Green files only)

Each builder: reads `SESSION.md`, this plan, its findings in the review report and the governing `.claude/rules/*.md` for its files; writes the fix and a test that **fails on `2dd492a` and passes after**; stubs every live meter (no model call, no CalDAV/IMAP/Maps network, no VM); runs `qa_sweep.sh` in its worktree; commits nothing. The lead diffs every file, re-runs the sweep on `main`, and commits one batch at a time.

### Builder A — `core/orchestrator.py`, `core/server.py`, `tools/wisdom.py`

| # | Fix | Test |
|---|---|---|
| 1 | **Unconditionally, for every token role:** drop `provider` from `SessionRequest` (a plain pydantic `BaseModel`, so an extra key from an older client is ignored, not a 422) and stop reading `data.get("provider")` on `/ws`; pass `provider=None` to the pipeline. The only service-token sender, `core/remote_client._send_one` (`:299-305`), always sends `"provider": None` — not a caller that needs it; remove the key there in the same commit, and from the `--remote` REPL path (`core/remote_client._run` `:252-257`, fed by `run_interactive_remote(provider=args.provider)` at `core/orchestrator.py:7864`), which would otherwise send a real value the server now ignores — the orchestrator CLI's `--provider` stays for local runs and prints that it is ignored with `--remote`. Remove the dead `--provider` CLI arg (`core/server.py:2960`). **`static/index.html` is NOT edited** (rev. 1, review #3): its selector offers only "Auto", and changing the file forces an APK rebuild through the WhatsApp tree. Internal `provider=` parameters on orchestrator functions stay (tests and the CLI use them) | `tests/test_multi_user_isolation.py`: a `provider` from a user-role **and** a service-role token on `POST /session` and `/ws` never reaches `run_pipeline_session_stream` / `run_session` |
| 2 | `_log_api_failure`: `who = agent or getattr(_tr.get_current_agent(), "agent", None) or "unknown"` (`:3928`); pass `.agent` at `:4067` | Push an agent record, call `_log_api_failure`; assert no `context_sections` text in the log record and the `MODEL_CALL_FAILED` quality event was written |
| 3 (dispatch half) | `dispatch_tool` drops a `persona` key from model-supplied `inputs` before `fn(**inputs)` (`:2839-2847`) | Dispatch a persona-bearing call; the bound persona is used |
| 4 | Add `RECORD_WISDOM_RESPONSE_SCHEMA` in `tools/wisdom.py` matching the registered handler's signature; add it to `register_tools()`'s schema list. **And the guard, in the same builder (rev. 1, review #2 — moved from C so it never runs in a tree without the schema):** `scripts/check_agent_tools.py:192-196` counts a granted name as built only if an advertised **schema** exists, not a handler alone, and that class drives the exit code | Schema present in `register_tools()` output under the Synthesizer's allowed tools; a call through `dispatch_tool` records the response; the guard fails with the schema removed and passes with it |
| 15 | `run_session_gemini_cached`: track `dispatched` in `_run_gemini_native_loop` as the stream twin does (2026-10-24); retry/fallback only when nothing was dispatched, else return what was said plus a tool-failure note | Fake client raising after a round that dispatched a write: the write handler runs once |
| 16 | `_run_pipeline_session_stream_inner`: on exception `_tr.set_trace(None)` and clear the current agent, mirroring the non-stream twin (`:7250-7252`) | Force both Coordinator legs to fail; the thread's trace is `None` afterwards and the next `run_session` passes through `_spend_gate()` |
| 21 | `_file_wisdom_proposals`: force `observed` provenance on proposals from a turn whose trace shows `read_email`, `fetch_url` or `fetch_rendered` | A proposal from a turn that read mail is stored `observed`, not `stated` |

### Builder B — `tools/` (no file shared with A)

| # | Fix | Test |
|---|---|---|
| 3 (schema half) | Delete the `persona` property and its `required` entries from the six schemas in `tools/pattern_miner.py` and `tools/baselines.py`; keep the Python parameter | Mirror `tests/test_build_doors.py:581-599`: no schema in `register_tools()` declares `persona` |
| 6 | `travel_watch`, `calendar_audit`, `calendar_reconcile`: `"error" in raw` is its own outcome — one quality event deduped per day per job, distinct return; `intake`: surface a channel-failure count in `context_block` | Each job given an error dict returns the failure outcome, not the clean-day string, and writes one event on two runs the same day |
| 7 | `update_calendar_event`: edit the fetched .ics in place — replace SUMMARY/DTSTART/DTEND/DESCRIPTION/LOCATION/RRULE of the master VEVENT only, keep VALARM, EXDATE and RECURRENCE-ID siblings, PUT that; `build_invite_ics` carries EXDATEs | .ics fixture (master + sibling + VALARM + EXDATE) through the update path; the PUT body keeps all three; a time-only change keeps the alarm |
| 22 | `tools/context_tracker.py` (rev. 1, review #1 — the existing `_preserve_corrupt` keeps nothing for a zero-length file, so it cannot be the recovery source): **(a)** cross-process `FileLock` around every read-modify-write, temp file + `os.replace` — after this a reader can no longer observe a torn file from our own writers; **(b)** a **last-known-good copy**, `context.json.lastgood` beside the tracker, refreshed inside the lock on each successful write by **copying** the outgoing valid tracker to a temp file and `os.replace`-ing that onto `.lastgood` — the tracker itself is never moved, so there is no instant at which it is absent (rev. 2, verify NEW 1); only then is the new temp file `os.replace`d onto the tracker; **(c)** on a decode error, a zero-length tracker, **or a missing tracker while `.lastgood` exists**, carry `clinical_threads` and `_CARRIED_KEYS` from `.lastgood` (and from nothing only if it too is unreadable), keeping `_preserve_corrupt` as is. The new persisted artifact is costed in § 5 | Zero-length, half-written **and missing** tracker with a valid `.lastgood` + `close_scheduled_run`: clinical threads survive; a brand-new persona (no tracker, no `.lastgood`) still starts empty; two processes writing concurrently never leave an unparseable tracker; extend `tests/test_degradation_paths.py:163-176` to assert survival, not just the copy |

### Builder C — `deploy.sh`, `scripts/`, `docs/INFRASTRUCTURE.md`

| # | Fix | Test |
|---|---|---|
| 8 | In the remote heredoc, before the restarts: `.venv/bin/python -c "import core.server, core.scheduler"` — abort with the old processes still serving. After the restarts, a crash-loop check that a restart's own side effects cannot trip (rev. 1, review #5 — a generic `Traceback` grep fires on in-flight turns the restart kills): read each unit's `NRestarts` **immediately after** the explicit `systemctl restart` (which resets it — the pre-restart figure is not a baseline; rev. 2, verify NEW 2), wait a settle interval longer than the units' `RestartSec=10` (~20 s), then require `systemctl is-active` for `metatron-server` and every `metatron-scheduler@*`, `NRestarts` unchanged from that post-restart baseline, `/health` 200 with the token already minted for the drain, and no `REFUSING TO START` in the journal since the restart. The success line depends on all four | Static: `bash -n deploy.sh`; a shell test feeding the verdict function failing `is-active` / `NRestarts` / health / journal inputs, plus a pipeline `Traceback` in the journal that must NOT fail the verdict. **Not executed** (Denied) |
| 48 | `scripts/metatron-resume.sh`: after the health check, `getent hosts aiplatform.googleapis.com` on the VM; on failure print infrastructure trap 7's fix line and exit 1 | `bash -n`; dry-run with the remote command stubbed |
| 44 (docs) | `docs/INFRASTRUCTURE.md` § Recreate: add cert issue, cert-renew timers, swap and playwright steps; point at the `infra/` files W5(a) adds | — |

### Builder D — day planner (only if W6a releases it; runs after A merges, since it touches one call site in `core/orchestrator.py`)

| # | Fix | Test |
|---|---|---|
| 5 | `_day_plan_block` reads `state["handled"][day]` entries with outcome `carried` not yet surfaced, passes them as `due_now` at `core/orchestrator.py:6155`, stamps them; narrow the shield to conversational jobs via a `shield_jobs:` list in `config/modules/day_plan.yaml` read by `tools/day_plan.py` — **no change to `core/scheduler.py`** (Red) | Scheduler-level test at 07:15 with the template config: the item reaches the 07:30 brief's block under DUE NOW; the Sunday analysis jobs no longer shield |
| 33 | `owns_checkins` branch skips when any `replaces_jobs` name is in `paused_checkins`, and when `shield` is set | Paused check-in + empty day → no check-in; shielded → no check-in |

### Builder E — `tools/build.py` only (only if W6b releases #40)

| # | Fix | Test |
|---|---|---|
| 40 | `context_block(persona)` returns `""` unless the persona is the developer's (resolved from the account role, not a hard-coded name, if such a role exists; else the `mike` persona with a comment); delete the "mention these" sentence | Non-developer persona with a pending ticket → empty block |

---

## 3. Out of scope, stated so nothing is assumed done

- **Every Low and Low-Medium** (including #28, #34, #42, #58, and the downgraded #12–14, #17–20, #23–26, #31–32, #37–39, #43, #45–47, #49), and #50's components except the tests attached to the fixes above.
- **Disproved / accepted:** #30, #35, #36, #51.
- **#64** (`proactive`/`nudge` honoured from any token) is Low and stays out, though builder A's #1 fix sits beside it.

## 4. Commits and deploy

One commit per builder, in order A → B → C → (D) → (E), plus one for the W3/W4 Red edits if made. No `Co-Authored-By`, no push. Deploy is Mike's: **if he wants `547c446` live-checked alone, he deploys before D's commit lands**; otherwise one deploy carries all. VM-affecting: A, B, D, E, W3, W4. Mac-only: C.

After the commits: an optional Fable `/code-review` of the High-item diffs (#1, #2, #3, #5, #7, #8) and #22.

## 5. Budget and model

- **Build:** Opus 5.5 builders (`docs/WORKFLOW.md`: build in Opus). A ~$12–18 (the orchestrator is ~7,800 lines), B ~$12–18, C ~$5, D ~$8, E ~$3 → **$40–55**. Lead (this chat, Opus 5.5) ~$15–20. This Fable plan review ~$8–15. Optional Fable code review ~$20–30. **Total ~$85–120; cap $150.**
- **Run:** two things persist per persona, both from #22. **(1)** a zero-byte lock file. **(2)** `context.json.lastgood` — unit: disk bytes, one copy, the size of the tracker (single-digit KB), overwritten on every write, so it cannot grow; a longer retention buys nothing and is not offered. **Deleted by:** whatever deletes the persona's tree (`accounts.py purge`); a restart or crash leaves one valid copy, which is the point. **Meter:** none reports it, and at this size none needs to — stated so it is not assumed covered. Both are copied to the Mac by the existing backup, which already copies the tracker itself.
- **Ancillary:** `deploy.sh` gains roughly 5–10 s (import check, health, journal grep).
- **Unseen:** none added.

## 6. Risks the lead will watch

1. Builder A and D both touch `core/orchestrator.py` — D runs only after A is committed. **The SubagentStop gate sweeps every dirty worktree** (`scripts/hook_subagent_gate.py:_dirty_worktrees`), so no builder may leave its tree failing `qa_sweep.sh` at any point it could stop; a builder that cannot get green reports back with the failure rather than stopping dirty. Builders B, C and E carry no step that depends on another builder's code (rev. 1, review #2).
2. #7 changes how every calendar edit is written; the fixture must cover a plain single event as well as a series, so the common case is not regressed.
3. #22's lock must be cross-process (the scheduler is a separate process) — a `threading.Lock` alone is the known non-fix.
4. #1 removal must not break any caller that sends `provider` — grep `static/`, `android/`, `scripts/`, `tools/metatron_monitor.py`, `core/scheduler.py` and `core/remote_client.py` first. A caller sending `None` is not one that needs it; a caller sending a real value is reported to the lead, not accommodated.
5. **No builder edits `static/index.html`, `android/` or `.gitignore`** — each forces an APK rebuild or touches the WhatsApp tree (review #3).

*Rev. 2, 2026-11-11: `.lastgood` refreshed by copy, never by moving the tracker; missing tracker triggers recovery; `NRestarts` baseline taken after the restart; `--remote` REPL stops sending `provider`.*

*Rev. 1, 2026-11-11 — after the Fable adversarial review (`archive/plans/adversarial_review_codebase_review_fixes_plan_2026-11-11.md`): #22 recovery source, guard moved into builder A, `static/index.html` dropped from #1, #1 made unconditional, #8's verdict rebuilt on `NRestarts`.*

---

## Phase 1 outcomes (Mike, 2026-11-11)

- **W1** — VM `.env` key check: asked; pending Mike's result. Code fix proceeds regardless (unconditional).
- **W2 (#11)** — **deferred** to a later plan.
- **W3 (#27)** — **done** in the main chat: `config/agents/synthesizer.md` § Internal flags — the "tell the user directly … built first" clause replaced with "never tell the user a capability is missing"; the false claims that the flags reach the context tracker removed. Not yet committed or deployed.
- **W4 (#29)** — **skipped** for later.
- **W5 (#44 VM files)** — asked; pending. Builder C does the doc half only.
- **W6** — **all held**: #5, #33 (day planner) and #9, #10, #40, #41 (Build) are not built in this pass. Builders D and E do not run.
- Builders A, B, C launched in worktrees.
