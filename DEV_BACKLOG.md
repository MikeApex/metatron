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
  **What is left: read a week of traces and judge whether the focus guidance holds**, and confirm
  the first live check-in shows `SCHEDULER DIRECTIVE`. Do not re-word anything before then.
  *filed 2026-08-09 · rewritten 2026-08-09 after measurement inverted it · full reasoning in
  `archive/PROJECT_LOG.md`*

- **2. [DB-0809-21] Three deployed behaviour changes are unverified on the running system.** Mike
  deferred the runs to batch them (*"test later with other changes"*), so this is the outstanding
  half of `6330029`, `b9ea29f` and `88b7614` — all live for `mike` now. Four things, one VM trip
  (**there is no `vertex-key.json` on the Mac**, so `provider: gemini` cannot resolve credentials
  locally): (1) **A4 `clinical` suite** against `sarah_chen` — 3 scenarios, ~$0.10–0.30, a regression
  check only, since its pass criteria are `MEDICATION_MISSED_CRITICAL` and the clinical flags and
  cannot reach the sleep edits; (2) **three targeted Physical Health calls** which *do* assert them —
  5.5h single night (hours on the `SLEEP:` line, **no** `SLEEP_POOR`), two consecutive such nights
  (flag fires), a logged run (`duration_minutes` + `intensity_rpe` pass through, not "logged");
  (3) the **05:40 `daily_calendar_reconcile`** output once a real candidate exists — it must raise at
  most one, as a question, never as a miss (may take days to arise naturally); (4) the first
  `companion_checkin` after 07:00 showing `SCHEDULER DIRECTIVE`. Project the cost and get approval
  before running, per `docs/CONVENTIONS.md` § Testing Cost Convention.
  *filed 2026-08-09 · **Mike deferred it explicitly** — ranked 3 by Mike: cheapest item that can
  actually move, since 4 and 5 are blocked on an APK rebuild and a device*

- **3. [DB-0803-01] Text doubling / input cut off mid-sentence in the app.** Reported 2026-08-03
  17:12Z; still live 2026-08-04 (SEQ 004). **Verified 2026-08-09 — it splits, and the doubling
  half is already fixed in code.** Doubling is the same defect as the now-closed `[DB-0803-06]`,
  fixed by `c4ff279` ([static/index.html:713-715](static/index.html#L713), call sites
  [:952](static/index.html#L952)/[:979](static/index.html#L979)). **The fix is not on the phone** —
  the bundled APK asset still has `shownIds.clear()` (`[DB-0809-18]`), so the gating step is a
  rebuild and re-test, not code. **Half two is now diagnosed (2026-08-09) and is server-side, not
  the app.** Ruled out the client: all five recordings from the report window end in silence with
  terminal energy at 1–3% of their own mean, and the `SILENCE_MS = 2500` auto-stop waits out 2.5s of
  quiet by construction, so it cannot cut mid-word. Cause is `vad_filter=True` at
  [core/voice_pipeline.py:153](core/voice_pipeline.py#L153) — Silero drops the quiet tail before
  Whisper decodes. `data/audio/2026-08-03/18-16-16.webm` is the clean case: VAD-on ends
  *"...communicating"*, VAD-off continues *"...with what we put in."* Second effect, unexpected: VAD
  also costs punctuation, turning that file into a run-on. **Do not simply set
  `METATRON_WHISPER_VAD=0`** — [:53](core/voice_pipeline.py#L53) records why it is on (~7% faster,
  suppresses the *"Thank you."* Whisper hallucinates on room tone). Tune Silero's `threshold` down
  and `speech_pad_ms` up, and measure against the **12 days of retained audio on the VM**, which is
  a regression corpus at zero API cost. Fix is mechanical from here.
  *filed 2026-08-03 by Mike via Synthesizer · origin SEQ 012 · **verified 2026-08-09; half two
  diagnosed 2026-08-09***

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
  but the known-values pass fixes it independently. **⚠ Live collision (2026-08-09):** this edits
  `write_contact` at `tools/crm.py:149-158`, the exact function the parallel session's deferred
  tone-pipeline Step 1 modifies (plan: `~/.claude/plans/3-everything-is-on-declarative-kurzweil.md`).
  Whoever moves first commits before the other starts — and diff the file before staging it, per
  `CLAUDE.md` § Deploy safety rule 4, which exists because that discipline already failed once today.
  *filed 2026-08-09, consolidating the 2026-08-02 reports · Mike via Synthesizer · origin SEQ 006
  · **verified 2026-08-09; collision noted 2026-08-09***

- **6. [DB-0809-06] The browser tab does not live-refresh on messages sent from elsewhere.** A
  message from the terminal or the Android app appears only after a manual reload; app and
  terminal sync fine. Transport is ruled out by the entry's own diagnosis — this is a
  client-side render path — **confirmed 2026-08-09, with two code-provable causes found:**
  **(a) catch-up wipes the transcript.** `core/server.py:675` answers a `catchup` request with
  `{type: "history", messages: <delta only>}`, and `renderHistory()` opens by clearing the
  conversation (`static/index.html:942`). So any reconnect that missed anything replaces the
  visible history with just the delta; a manual reload restores it because a fresh load sends no
  catch-up. Fix: give catch-up its own type and route each row through the existing `case
  'message'` handler, which already dedupes on `shownIds` and advances `lastSeenId`.
  **(b) a hidden tab never checks its own socket.** Both liveness paths — the
  `visibilitychange` handler (`:818`) and the 20s backstop (`:826`) — are gated on
  `visibilityState === 'visible'`, so a background tab never runs the `STALE_AFTER_MS` detector
  that exists precisely for sockets whose `onclose` never fires. Fix: one ungated interval.
  Both end at "appears only after a manual reload", which is why the symptom was ambiguous.
  (a) is a protocol change, so it needs the APK rebuild — `[DB-0809-18]` is upstream.
  *filed 2026-08-01/02 from conversation — the only `## Now` item whose provenance line does not
  name its reporter; treat "Mike raised it" as likely but unconfirmed · **diagnosed 2026-08-09**,
  both causes located; the fixes are small and mechanical*

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
