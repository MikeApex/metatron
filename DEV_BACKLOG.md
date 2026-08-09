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

*Ranked 2026-08-09 by Mike after a `/backlog deep` sweep verified all eight against current code.
Every entry carries what was checked and when; a verdict without that line is a description, and
descriptions are what the standing rule distrusts.*

- **1. [DB-0808-18] ⚠ Live `OPENAI_API_KEY` sits in plaintext in `~/.zshrc:2`.** *(Dev-session
  find, kept here under the credential-exposure exception above.)* Rotate at platform.openai.com
  (assume burned), move it into the gitignored `.env` — which does **not** carry it — and delete
  the `export` line. **The repo question is answered: it never reached git** (`git log --all -S`
  on the trailing fragment → 0 commits, 0 tracked files; `archive/transcripts/` gitignored at
  [.gitignore:99](.gitignore#L99), not :97 as filed). No history rewrite; exposure is local only
  — `~/.zshrc` plus 3 files in `archive/transcripts/raw/`. First because it is the cheapest item
  here and the only one with a clock.
  *filed 2026-08-08 by dev session · **verified 2026-08-09***

- **2. [DB-0809-02] Check-in brevity rule is not obeyed — Mike has restated it five times.** Five
  restatements 2026-08-07 → 08-09, the most-repeated complaint in the system's history. Treat it
  as a mechanism problem (prompt assembly order, or enforcement below the model), not a sixth
  re-wording. **Verified 2026-08-09 on the VM — premise holds exactly, plus one narrowing fact:**
  the rule is at `config/personas/mike.md:11` and near-verbatim at
  `config/personas/mike/scheduler.yaml:41`, and `mike.md` is **11 lines long in total** — its
  final line, in a file too short to bury anything. "Lost in a long prompt" is therefore not the
  explanation. Resolve the duplication (see `## Machine log`) in the same pass.
  *filed 2026-08-09 from 5 Inbox entries (2026-08-07T09:13 → 2026-08-09T09:06) · Mike via
  Synthesizer · **verified 2026-08-09** against both live VM files*

- **3. [DB-0803-01] Text doubling / input cut off mid-sentence in the app.** Reported 2026-08-03
  17:12Z; still live 2026-08-04 (SEQ 004). **Verified 2026-08-09 — it splits, and the doubling
  half is already fixed in code.** Doubling is the same defect as the now-closed `[DB-0803-06]`,
  fixed by `c4ff279` ([static/index.html:713-715](static/index.html#L713), call sites
  [:952](static/index.html#L952)/[:979](static/index.html#L979)). **The fix is not on the phone** —
  the bundled APK asset still has `shownIds.clear()` (`[DB-0809-18]`), so the gating step is a
  rebuild and re-test, not code. **"Input cut off mid-sentence" is a separate, untouched half.**
  *filed 2026-08-03 by Mike via Synthesizer · origin SEQ 012 · **verified 2026-08-09***

- **4. [DB-0805-02] Email approval prompt does not render in the app.** Two reports 2026-08-04
  (12:42Z, 12:49Z). **Verified 2026-08-09 — premise drifted, the UI now exists:** `#confirm-bar`
  at [static/index.html:470-477](static/index.html#L470) (handlers
  [:1367-1384](static/index.html#L1367)) against `/pending-confirmations` and `POST /confirm`
  ([core/server.py:693-717](core/server.py#L693)), landed `ca993fe` at 11:39Z — **three minutes
  before the first report** — and present in the bundled APK asset too. So this is a stale install
  or a runtime failure of code that exists: **live repro on a rebuilt APK is the next step, not a
  build.** Ranked high because until approval works on the phone, every gated outward action is
  unusable.
  *filed 2026-08-04 by Mike via Synthesizer · origin SEQ 016/017 · **verified 2026-08-09***

- **5. [DB-0809-03] Dictated contact details come through wrong and need correcting by hand.**
  Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus
  `diamond.like.gmail.com` at SEQ 006. **Verified 2026-08-09:**
  [tools/crm.py:149](tools/crm.py#L149)/[:158](tools/crm.py#L158) already run difflib near-miss
  detection against the user's own email and phone, but they **refuse** the write rather than snap
  it — a different behaviour from what this asks for, and the snap exists nowhere. The user's
  addresses are in `profile.yaml` and contacts in the CRM, so a token close to a known string
  should snap rather than pass through or be rejected. Partly Whisper accuracy (`[DB-0808-08]`),
  but the known-values pass fixes it independently.
  *filed 2026-08-09, consolidating the 2026-08-02 reports · Mike via Synthesizer · origin SEQ 006
  · **verified 2026-08-09***

- **6. [DB-0809-05] Nothing notices a calendar event that passed without happening.** Mike's ask:
  detect it and prompt to reschedule; keep financial tasks (payroll) prominent in daily
  proactive checks until explicitly closed. **Verified 2026-08-09: neither exists** — nothing in
  `core/` or `tools/` reconciles a past event against reality; the scheduler only fires jobs.
  *filed 2026-08-09 from Inbox (2026-08-05T15:19Z) · Mike via Synthesizer · **verified 2026-08-09***

- **7. [DB-0809-06] The browser tab does not live-refresh on messages sent from elsewhere.** A
  message from the terminal or the Android app appears only after a manual reload; app and
  terminal sync fine. Transport is ruled out by the entry's own diagnosis — this is a
  client-side render path. `ace22c7` (2026-08-01) fixed the adjacent half-open-socket case
  (`STALE_AFTER_MS`, confirmed still at [:724](static/index.html#L724) and
  [:728](static/index.html#L728)) and never runs when the socket was not actually dead.
  **Needs live reproduction before code:** open the tab, send from the terminal, watch.
  *filed 2026-08-01/02 from conversation — the only `## Now` item whose provenance line does not
  name its reporter; treat "Mike raised it" as likely but unconfirmed · re-checked 2026-08-05 and
  2026-08-09, adjacent fix confirmed but a different code path*

- **8. [DB-0809-04] Sleep gets over-weighted in interpretation — not because it is the only thing
  logged.** Mike's *"once again you're making too much of the sleep disruption"*, raised more than
  once. **Rewritten 2026-08-09: the entry blamed a thin record and the measurement it demanded
  refutes that.** 20 days of `data/personas/mike/logs/2026-*.json` on the VM: `mood` 90%, `notes`
  90%, `focus` 75%, `health` 70%, `energy` 70%, `tasks_completed` 60%; sleep is on 14/20 days
  (70%) — roughly the **fifth** most-populated signal, not the only one. Its own guard (*don't
  build weighting before checking the column is empty*) resolves the other way: **the columns are
  not empty**, so domain-rotating check-ins and passive capture are both off the table. What
  remains is a Synthesizer interpretation defect against an already-broad record — fix the
  2026-08-03 `synthesizer.md` rules, not the log schema. The separate "hours plus interruptions,
  not a narrative" ask is **largely already structural**: `sleep_hours` (11 days) and
  `sleep_quality` (12 days) are distinct fields. Last because the expensive half just disappeared.
  Still gates trusting any Pattern Miner cross-domain result.
  *filed 2026-08-09 merging two 2026-08-01/02 entries · Mike via Synthesizer · **premise measured
  and inverted 2026-08-09***

---

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
- **[DB-0809-12]** Hallucinated log dates in mike's VM tree. **Re-verified 2026-08-09 and the
  premise drifted: there is no `2024-08-04.json`.** The impossible set is 9 files, all 2025 —
  `2025-01-24`, `2025-05-13/14/15/16`, `2025-07-20/21/25`, `2025-08-02`. The `2026-06-*` and
  `2026-07-*` files are legitimate history, so a raw "23 of 32 are not 2026-08" count misleads.
  Fix is a dated-filename guard at the write site, then move the 9 aside — not a bulk delete.
- **[DB-0809-18]** The APK-bundled `android/app/src/main/assets/public/index.html` drifts from
  `static/index.html` silently and nothing checks. Found 2026-08-09 while verifying
  `[DB-0803-01]`: 3 diffs today — the `evictOldest` fix, and `/transcribe` missing its
  `?persona=` param, so the phone transcribes without naming a persona. Small now, but it makes
  every app-side bug report ambiguous about whether the shipped code was under test. Cheap fix: a
  deploy-time assertion that the two files match, on `deploy.sh`'s HEAD-assertion model
  (`[DB-0809-11]`). *filed 2026-08-09 by dev session*
- **[DB-0809-11]** Docs record values the system changes underneath them and nothing checks.
  Mitigation in force (don't write down short-half-life values); the stronger fix is a smoke
  script running CLAUDE.md's executable claims. `deploy.sh`'s HEAD assertion is the model.
- **[DB-0809-10]** `CLASSES` in `core/rule_classes.py` is incomplete by construction, so a clean
  rule-overlap report is not proof. **Widen a class in the same pass as any duplicate found by
  hand** — that is the maintenance loop.
- **[DB-0809-14]** ROADMAP.md Track D is ~14 KB of a file loaded every `/metatron-code`, and
  parts have shipped. **Trim item-by-item against the log, never by line range.**
- **[DB-0809-16]** Live dictation test of the dismissable transcription readout — code-verified
  against every pass condition 2026-08-05, never run by a human with a microphone.
- **[DB-0805-04]** `tools/mail.py`'s module docstring says sending is deferred; `send_email`
  shipped 2026-08-04 and sent for real 2026-08-05. **Confirmed still wrong 2026-08-09** —
  [tools/mail.py:9-11](tools/mail.py#L9). One-line fix.

---

## Machine log

*Auto-appended runtime signals — tool denials, rule conflicts, self-applied changes. Collapsed
by signature. Nobody asked for these: they are the system reporting on itself, and they are
**not** part of an ordinary triage pass. A signature reaching ×3 gets a ⚠ and is surfaced in the
sync output line — repetition is the signal that a process event has become a real one. Promote
anything user-impacting into `## Now` or `## Later` like any other item; this is a holding pen,
not a blackhole. Swept during `/backlog deep`.*

- **[agent wanted a tool it lacks]** `finance` attempted `search_memory` (query) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-05T15:21:45.223926Z`

- **[same rule in two places]** The check-in brevity preference at `config/personas/mike.md:11` restates rules already in `config/personas/mike/scheduler.yaml:41` and `config/templates/scheduler.yaml:34`. Class: brevity. Superseded in practice by `[DB-0809-02]` — the rule is not being obeyed anywhere, which is the larger problem; resolve the duplication as part of that fix.  
  `2026-08-05T04:30:19.777295Z` — **still valid: both live VM files confirmed by hand 2026-08-09.**

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
