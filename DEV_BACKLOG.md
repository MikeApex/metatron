# Development Backlog

Work outside the roadmap, in priority order. **`## Now` is the list** — everything else is
staging or reference. Refresh with `python3 scripts/sync_dev_backlog.py`; how and when to work
it is [docs/WORKFLOW.md](docs/WORKFLOW.md).

> **The one standing rule: no item is acted on, or re-filed, on the strength of its own
> description.** Open it against the current code first. A 2026-08-05 sweep found roughly a
> third of checked items stale — and a stale premise does not merely waste the check, it argues
> for the wrong decision, persuasively.

**Priority is Mike's call.** Claude proposes a tier; Mike sets it. The ordering within `## Now`
is the priority order. Closed items move to `archive/backlog_closed_2026-08.md` with the commit
or `file:line` that closed them — closed without evidence is not closed.

---

## Inbox

*Machine-written from what Mike said on the VM. Do not hand-edit — triage entries out into
`## Now` or `## Later`, rewritten properly, and delete them from here.*

*(nothing new — last triaged 2026-08-09)*

---

## Now

**Ranked — position is priority.** Capped at ~10, so something enters by displacing something.
**The entry bar is that Mike raised it**, with one standing exception that must not widen: a live
credential exposure or data-loss risk enters regardless of who found it. Both rituals — ranking
each item as it arrives, and the reporter asymmetry — are in [docs/WORKFLOW.md](docs/WORKFLOW.md).

*Ranked 2026-08-09 by Mike after a `/backlog deep` sweep verified every entry against current code;
re-ranked later that day when three closed and `[DB-0809-21]` entered at 3. Every entry carries what
was checked and when; a verdict without that line is a description, and descriptions are what the
standing rule distrusts.*

- **1. [DB-0809-02] Do proactive sessions actually stay focused? — the mechanism half is fixed
  and deployed; the guidance half is unproven.** **The original premise was wrong.** All 22 August
  `companion_checkin` openings were 1–2 sentences: the rule was obeyed, and four of the five
  "restatements" were the Synthesizer reading its *own* scheduler prompt as Mike's voice and firing
  the repeated-instruction protocol against text he never sent. Mike said it twice, both 08-03.
  Fixed in `82d394b` (deployed): `_frame_proactive()` labels scheduler input as a directive in both
  pipeline copies, and the protocol now requires the *user* to have repeated it. A ≤2-sentence cap
  was **rejected** — the real target is focus, with length as its symptom — so
  `config/agents/synthesizer.md` § Scheduled session conduct carries guidance instead.
  **Confirmed 2026-08-10: the first two live firings since deploy are clean.** Both
  `companion_checkin` (07:20) and `morning_brief` (07:30) recorded `is_proactive: true` in
  their trace, and — the decisive check — **zero quality events of any kind logged all
  day**, meaning no `INSTRUCTION_CHANGE_REQUEST` fired, which is what the old bug produced
  every time. (Traces don't retain raw prompt text, by design, so this is the strongest
  check available without re-running something artificially.) Both responses also matched
  the focus guidance's shape: one thing, a pending action referred to not recited, ends on
  a real question. **What remains: read a week of traces** — one clean day is a good early
  signal, not the week this item asked for. Do not re-word anything before then.
  *filed 2026-08-09 · rewritten 2026-08-09 after measurement inverted it · **first live
  firing confirmed clean 2026-08-10, day 1 of 7** · full reasoning in `archive/PROJECT_LOG.md`*

- **2. [DB-0809-21] Two of four verification steps done and passed; two are genuinely time-gated,
  not yet observable.** Projected cost ~$0.08 (token-based estimate against `_run_single_agent`'s
  actual single-agent shape, not the blended $8.44/50-session historical average, which is
  dominated by B1's full-pipeline scenarios and would have overstated this run) — under the $1.00
  approval line, ran without blocking per `docs/CONVENTIONS.md` § Testing Cost Convention.
  **Done:** (1) **A4 `clinical` suite** against `sarah_chen` — 3/3 pass, confirms the regression
  gate held; as expected it cannot reach the sleep edits, since its pass criteria are
  `MEDICATION_MISSED_CRITICAL` and the clinical flags. (2) **Three targeted Physical Health calls**
  against `danny_park`, which *do* assert `6330029`/`88b7614` — all three passed: a single 5.5h
  night reported hours with **no** `SLEEP_POOR`; a second consecutive night under 6h fired the
  flag; a 45-minute RPE-7 run passed those figures through rather than flattening to "logged" —
  and the model correctly drew on the prior nights' sleep to contextualize the run's perceived
  exertion, which is exactly what the deep-merge fix in `88b7614` was protecting.
  **Still open, not a failure — time hasn't passed yet:** (3) `daily_calendar_reconcile` re-run
  manually against `mike`'s real calendar (zero cost, no model call) — clean, 0 candidates, same
  as its first run last night; confirms the mechanism still works, but **no live candidate has
  existed yet to observe being raised as a question**, which needs a real unreferenced event, not
  a forced one. (4) The first natural `companion_checkin` after 07:00 — deliberately **not**
  forced by manually firing a session against Mike's real persona, since that would insert a
  synthetic exchange into his actual conversation history for no real need. Check both again once
  they've had a chance to occur naturally.
  *filed 2026-08-09 · **Mike deferred it explicitly** · **half done, half genuinely time-gated
  2026-08-10** — half the reason it can't move further today*

## Later

Real, not prioritised. One or two lines each — detail lives in the code, the log, or
`archive/backlog_closed_2026-08.md`.

**Safety and test gaps**
- **[DB-0808-17]** A4 clinical hard-fails have never run on Flash-Lite, which serves most MW/PH
  turns (43 vs 5, 58 vs 6, Aug 1–8). Routing stays as-is by Mike's decision; the *test* gap is
  the item. Add `--complexity quick` to the A4 suite. Bears on ROADMAP § A7 check 8's wording.
- **[DB-0808-16]** The `injection` suite needs an ordinary-life persona — a clinically-loaded
  one silently scores 3/3 on a pipeline that never read the payload. Docstring line + a guard
  that fails loudly when `read_email` was never called. Matters for the open B1b rows.
- **[DB-0808-06]** No administrative close for tier-2 clinical threads — `resolved` exists and
  nothing can legitimately set it, so every tier-2 thread is permanent. Correct failure
  direction; needs a real path eventually, tied to escalation that doesn't exist. **Do not fix
  by relaxing the refusal.**
- **[DB-0808-14]** `_thread_tier()` cannot tell a psychiatric medication from a cardiac one — a
  missed statin and a missed anti-psychotic are both tier 1. Fix: `psychiatric: true` on
  `medication_profile` entries, read by `_thread_tier()`.
- **[DB-0805-01]** `physical_health`'s `write_agent_config` grant is guarded on one key only
  (`medication_profile`, `_GUARDED_KEYS`). Another flag growing the same dependency needs its
  key added. B2 should decide whether guarded keys or the confirm gate is the mechanism.
- **[DB-0809-15]** `write_agent_config`/`write_config` are still not wired to `tools/confirm.py`
  — the standing B2 requirement, and the standing answer to every agent tool-denial.
- **[DB-0804-02]** Track B remainder: B4's 5 degradation paths, B2's confused-deputy regression
  test, and Wave 2 (B1b, B3) gated on Track E. Detail in the archive file.

**Reliability**
- **[DB-0808-11]** `fire_function` runs no gate stack — `days`, `respect_quiet_hours` and the
  activity gate are ignored for every function job. Reachable since it gained a notification
  path: an `interval_minutes` job with `notification: push` would push at 3am.
  `daily_travel_check` is pinned to 06:45 to work around it. Fix by extracting the gate stack.
- **[DB-0809-07]** ⚠ The VM's guest lost all networking for ~4 hours on 2026-08-04 while GCE
  reported `RUNNING` — `network is unreachable` to the metadata server, so no route existed.
  Same signature as the 2026-07-31 `nic0 is frozen` incident **but with billing never
  disabled**, so either that root cause was misattributed or there are two paths in. Unresolved.
- **[DB-0809-09]** The scheduler can only skip a time-anchored job, never defer it — blocked
  means gone for the day. Current state is correct (`morning_brief`/`evening_close` carry no
  activity gate deliberately). Only pick up if a fixed-time session should ever wait for a lull.
- **[DB-0804-01]** One-week count confirming `[DB-0803-02]`'s fix under real scheduler fires —
  **due 2026-08-11, do not check before then.** Baseline 18 `AgentRecord` errors in 7 days.
- **[DB-0803-05]** `sw.js` registers no `fetch` handler and `/` is served `no-store` — no
  offline shell, so an unreachable server shows a browser error page instead of the app.
- **[DB-0808-05]** The output filter suppresses the whole reply when Mike names a tool himself
  (*"`write_config` didn't save my preferences"*) — the canned fallback lands exactly when a
  complaint about the system deserves an answer. Observed live once (Exchange 027, 2026-06-26),
  pinned non-gating as `FILTER-EXCH027`. Fix: pass the user's turn into `filter_output()` and
  exempt **only the term he typed, only in the next turn** — three call sites
  (`core/orchestrator.py` ~2506, ~2721, ~2768). Not a blanket flag: a probing question must not
  disable its own backstop. **Dev-session find; promote if it recurs.**

**Capability**
- **[DB-0806-02]** Level 3 web access. Split into rendered-read (`fetch_rendered`, Playwright,
  read-only — recommended, same trust boundary as `fetch_url`; check VM memory first) and
  interactive click/type/submit, which stays gated on a credential store that does not exist.
  Covers Mike's *"reserve tickets on the R website"* ask. Scope:
  `archive/plans/level3_web_actions_scope_2026-08-06.md`.
- **[DB-0808-04]** Real-time GPS + proactive area-scanning ("notice no lunch on the calendar,
  find somewhere matching known preferences"). Mike's framing; needs its own design pass —
  privacy tier for continuous location, which layer supplies it, how scanning bounds itself.
- **[DB-0807-02]** Google Places API — venue discovery for `logistics` and `recreation_hobbies`.
  Blocked on the same missing location signal; "near a named address" could ship sooner.
- **[DB-0809-13]** Sentence-chunked TTS. Kokoro is at 2.8s/call. **Do not build before using
  voice enough to say whether 2.8s actually feels slow.**
- **[DB-0809-08]** "Unsurfaced opportunities" is the one troubleshooting category with no
  instrumentation — it is an absence, so no richer tracing recovers it. Recommended: a reason
  code on the `·` feedback dot, plus detecting `open_threads` that go quiet unresolved.

**Performance and cost**
- **[DB-0808-09]** Per-specialist internal turn reduction. Coordinator is 1 turn (measured
  twice); `logistics` is 8; the other specialists are unmeasured. **Measure first, then diagnose
  from traces, then fix.** Absorbs the old "Coordinator restructure" entry. Slimming
  `coordinator.md` is a separate token-size argument — watch the 4,096-token Vertex cache floor.
- **[DB-0806-04]** Migrating the VM us-central1 → europe-west1: ~200–280ms off every voice turn
  for ~$2.60/mo. Priced live, not estimated. A deliberate trade, not a bug.
- **[DB-0806-03]** No BigQuery billing export, so cost anomalies can only be eyeballed against
  console lag. Not retroactive — turning it on now only helps the next anomaly.

**Housekeeping**
- **[DB-0805-05]** Parallel Claude Code windows still collide in *git*, which the handoff
  protocol does not cover: one window's commit swept up another's entire uncommitted diff
  (2026-08-08), and a `git add`/`commit` race produced a silent no-op commit. Scoping a commit
  with `git add <files>` does not protect you — the sweeping window is the one committing.
- **[DB-0809-17]** `/archive` step 0's dirty-file check cannot tell whose edits it is looking at
  — on its first run it flagged this session's own `SESSION.md`/`PROJECT_LOG.md`. A session that
  reasons "dirty means mine" and rewrites anyway hits the exact failure the guard exists to
  prevent, so it is advisory, not protective. Possible fix: compare against the session's start
  commit, or record touched files as the session goes. **Do not remove the check** — a prompt to
  look beats no prompt. *filed 2026-08-09 by dev session (first run of the new `/archive`)*
- **[DB-0809-11]** Docs record values the system changes underneath them and nothing checks.
  Mitigation in force (don't write down short-half-life values); the stronger fix is a smoke
  script running CLAUDE.md's executable claims. `deploy.sh`'s HEAD assertion is the model.
- **[DB-0809-10]** `CLASSES` in `core/rule_classes.py` is incomplete by construction, so a clean
  rule-overlap report is not proof. **Widen a class in the same pass as any duplicate found by
  hand** — that is the maintenance loop. **Second blind spot, found 2026-08-09:** nothing checks
  `config/templates/`, so a rule deleted from a persona survives in the file that seeds every new
  one. That is how the check-in rule reached four copies with only three flagged.
- **[DB-0809-19]** `tests/run_b1_redteam.py:52` inspects `run_pipeline_session()`'s *source*
  structurally, and `82d394b` added a branch to it. Probably still passes, but B1 gates A7, so
  confirm before the next red-team run rather than during it.
  *filed 2026-08-09 by dev session*
- **[DB-0809-14]** ROADMAP.md Track D is ~14 KB of a file loaded every `/metatron-code`, and
  parts have shipped. **Trim item-by-item against the log, never by line range.**
- **[DB-0809-16]** Live dictation test of the dismissable transcription readout — code-verified
  against every pass condition 2026-08-05, never run by a human with a microphone.
---

## Machine log

*Auto-appended runtime signals — tool denials, rule conflicts, self-applied changes. Collapsed
by signature. Nobody asked for these: they are the system reporting on itself, and they are
**not** part of an ordinary triage pass. A signature reaching ×3 gets a ⚠ and is surfaced in the
sync output line — repetition is the signal that a process event has become a real one. Promote
anything user-impacting into `## Now` or `## Later` like any other item; this is a holding pen,
not a blackhole. Swept during `/backlog deep`.*

- **[agent wanted a tool it lacks]** `relationships` attempted `search_memory` (query) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-10T06:30:12.978385Z`

- **[agent wanted a tool it lacks]** `finance` attempted `search_memory` (query) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-05T15:21:45.223926Z`

---
## Done

**Closed items live in [`archive/backlog_closed_2026-08.md`](archive/backlog_closed_2026-08.md)**,
with the commit or `file:line` that closed them. Rolls monthly. Nothing is ever deleted — an
item that resurfaces must be able to show it was checked once, and the withdrawn and
"not a bug" entries are the most valuable ones in there.

Closed by the 2026-08-09 workflow revamp itself: `[DB-0809-01]` (inflated open count — the
notation trap is gone by construction), `[DB-0808-13]` (`/archive` collision guard — now step 0),
`[DB-0808-15]` (parallel-window status collisions — coordinator/handoff protocol, with the git
half kept open as `[DB-0805-05]`).

Closed by the 2026-08-09 `/backlog deep` sweep: `[DB-0803-06]` (`shownIds` full-`clear()` →
oldest-first eviction, fixed by `c4ff279`; its "promote when Mike sees a doubled message"
condition had already been met by `[DB-0803-01]`, which now carries the remaining APK half).

---

## Agent-file enhancement backlogs

**These live in the agent files, and only there.** Each specialist's `## Enhancement backlog`
at the bottom of `config/agents/{name}.md` is the single copy. A mirror sat here for one day in
August 2026 — 32% of the file, and it made the backlog look three times its real size.

`grep -l "## Enhancement backlog" config/agents/*.md`
