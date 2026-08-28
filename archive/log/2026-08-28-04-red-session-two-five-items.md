### 2026-08-28 (supervised Red session ② — five items, six commits, all deployed same evening) — `core/{scheduler,orchestrator}.py`, both routing files, five agent files, `tools/{logger,diarist,context_tracker,confirm,location,places}.py`, 5 new test files — `20c17d0`, `bfbdbb5`, `4eb0dbb`, `d9b4843`, `f519749`, `d750fbb` — **deployed by Mike (VM on `d750fbb`)**

**The revised 2026-08-28 order's session ② ran end to end with Mike present, building the
decisions batch exactly as ruled — nothing re-decided.** Fable throughout per the handoff.

- **Scheduler pair (`20c17d0`).** Interval session jobs yield within 30 min (configurable,
  `interval_near_fixed_minutes`) of a fixed-time session job — the 07:23/07:30 collision that
  fed `[DB-0815-11]`'s false claim. `fire_function` now runs the shared `_gates_block`
  ([DB-0808-11] closed); every `_DEFAULT_JOBS` entry sets `respect_quiet_hours: False`
  explicitly, and the template's `daily_travel_check` gets the flag. 23 new checks + old 16.
- **Grants pass (`bfbdbb5`).** All 24 ruled pairs: 19 grants in both routing files (parity
  asserted), 5 resolved by text (journals route through the Diarist; learning_growth's
  skill-goals line → `write_agent_config`). Two code backstops shipped with it:
  `write_archive` updates a title-matched row instead of appending a twin, and
  `write_quality_event` no-ops a same-trace/same-type duplicate. **A7 check 10 unblocked.**
- **A4 measures "safe WITH standing knowledge" (`4eb0dbb`), then Step-6 (`d9b4843`).** The
  runner self-seeds a knowledge fixture (two entries deliberately contradicting the clinical
  read — values carry no test annotation, which would leak the pass condition). Run on the
  VM store (host named in the report): clinical deep/quick + pipeline all 3/3. Step-6 then
  moved MW+PH plus the Flash-Lite six onto the cached Vertex path — **gated twice**, with a
  post-change 9/9 re-run on the native loop, beyond what the disposition required, because
  the pre-change run could not exercise the loop the change moves the clinical agents onto.
- **Medication ranking (`f519749`).** `discontinuation_risk` in the profile spec, the flag
  carries the medication name, `_thread_tier()` ranks a risk-marked miss tier 2 with every
  failure direction falling to tier 1. Live A4 run showed the model emitting the name suffix
  unprompted. 10/10 tests.
- **Zone suggestion (`d750fbb`).** Option b as ruled: away ping + calendar-expected place →
  name-only Places geocode (per-name cache, fail-soft) → local compare → confirm card →
  `append_zone`, the one consume-gated write path to `zones.yaml`. Candidates from the
  structured CalDAV query only. 24 checks incl. the outbound-payload byte assertion.

**Wrong-belief corrections.** (1) The handoff's "the scheduler has none of its own gates
tested today" was stale — `tests/test_scheduler_quiet_hours.py` existed; what was untested
was `fire_function` and the collision class. (2) Item 5(d) "Mike creates the Places key"
was already done 2026-08-26 — the key is in the VM `.env`, so zone suggestion went live at
deploy, not dormant. (3) `core/orchestrator.py:4019` had drifted; the real branch was :4555.

**Found at close-out, urgent, handed to Mike:** his VM `scheduler.yaml` defines
`daily_travel_check` without the new flag, so **the travel check is silently skipped every
morning since this deploy** — one-line fix, instructions (with zones-file and APK steps) in
`archive/handoffs/2026-08-28-post-session-two-mike-steps.md`.

**Rejected/negotiated in-session:** auto-accepting Red edit prompts (the ask rules are the
supervision mechanism; batched edits per file instead — ~7 prompts, not ~20). Mike's style
ruling saved to memory: conversational, problem-first, worked examples — this and generally.
Tier lesson for session ③'s handoff: items 3/5's Amber halves could have gone to Opus
workers under the standing build/review split; "Fable throughout" was the handoff's call.
