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
**Each item is ranked as it arrives:** it is put to Mike with a recommended position and the
reasoning — who raised it, what it blocks, what it costs while it sits — and he makes the call.
Not inferred, not appended, not left to sort out later.

*The eight below were set equal on 2026-08-09, so their current order carries no meaning — work
whichever fits the session. The next item to arrive is ranked against them properly, and from
then on the order means what it says.*

**The entry bar is that Mike raised it.** A dev session finding a real bug files it to `## Later`
however good the find is — that asymmetry is the whole point, and it is what stopped this list
growing faster than it shrank. One standing exception, stated so it does not quietly widen:
a **live credential exposure or data-loss risk** enters regardless of who found it, because the
cost of waiting is not proportional to who noticed.

- **[DB-0809-02] Check-in brevity rule is not obeyed — Mike has restated it five times.** The
  preference is saved (`config/personas/mike.md:11`, and again in `scheduler.yaml`) and the
  Synthesizer keeps listing pending items anyway. Five restatements 2026-08-07 → 08-09 is the
  most-repeated complaint in the system's history. The instruction layer has demonstrably
  failed; treat it as a mechanism problem (prompt assembly order, or enforcement below the
  model) rather than re-wording the rule a sixth time.
  *filed 2026-08-09 from 5 Inbox entries (2026-08-07T09:13 → 2026-08-09T09:06) · Mike via
  Synthesizer*

- **[DB-0808-18] ⚠ Live `OPENAI_API_KEY` sits in plaintext in `~/.zshrc` and leaked into a
  session transcript.** *(A dev-session find, kept here under the credential-exposure exception
  above — the rotation clock does not care who noticed.)* Rotate at platform.openai.com (assume
  burned), move the replacement to
  the gitignored project `.env`, delete the `export` line. Then confirm it never reached the
  repo — `archive/transcripts/` is gitignored ([.gitignore:97](.gitignore#L97)) so exposure is
  probably local, but `git log -S` for the fragment is the check, not the assumption. The
  2026-07-29 history rewrite is the precedent for what "yes, it reached the remote" costs.
  *filed 2026-08-08 by dev session · surfaced incidentally by a `tail ~/.zshrc`*

- **[DB-0803-01] Text doubling / input cut off mid-sentence in the app.** `static/index.html`.
  Reported 2026-08-03 17:12Z; still live 2026-08-04 (SEQ 004 references it). Untouched and
  unverified since — the calendar half of the same report shipped, this half never did.
  *filed 2026-08-03 by Mike via Synthesizer · origin SEQ 012 · not verified since*

- **[DB-0805-02] Email approval prompt does not render in the app.** Two reports 2026-08-04
  (12:42Z, 12:49Z). The confirm mechanism works server-side (`tools/confirm.py`,
  `POST /confirm`) — what Mike cannot do is *approve* from the phone, which makes every gated
  outward action unusable in practice. The "no live Google Contacts read" half of the original
  report was answered by vCard import and is not part of this item.
  *filed 2026-08-04 by Mike via Synthesizer · origin SEQ 016/017 · not verified*

- **[DB-0809-03] Dictated contact details come through wrong and need correcting by hand.**
  Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus
  `diamond.like.gmail.com` at SEQ 006. `write_contact` now refuses an exact self-match and
  `write_profile` gates changes, but nothing snaps a near-miss to a known value. The user's own
  addresses are in `profile.yaml` and contacts are in the CRM — a transcript token close to a
  known string should snap rather than pass through. Partly Whisper accuracy (`[DB-0808-08]`),
  but the known-values pass fixes it outright and independently.
  *filed 2026-08-09, consolidating the 2026-08-02 reports · Mike via Synthesizer · origin SEQ 006*

- **[DB-0809-04] Sleep is nearly the only thing consistently logged, so everything gets
  explained by sleep.** Mike's *"once again you're making too much of the sleep disruption"*,
  raised more than once. The 2026-08-03 `synthesizer.md` rules (don't over-read a thin record;
  ask for what's missing) are mitigation — they tell it to distrust its only signal without
  giving it a second one. **Measure first:** count populated keys per day per domain in
  `data/personas/mike/logs/*.json` over 30 days. Then decide whether check-ins should rotate
  which domain they ask about, and what can be captured passively the way sleep is. **Do not
  build a weighting algorithm before checking whether the column is simply empty.** Mike has
  separately asked that sleep itself be logged as total hours plus interruptions rather than a
  disruption narrative. Also blocks trusting any Pattern Miner cross-domain result.
  *filed 2026-08-09, merging two overlapping entries from 2026-08-01/02 · Mike via Synthesizer*

- **[DB-0809-05] Nothing notices a calendar event that passed without happening.** Mike's ask:
  detect it and prompt to reschedule; keep financial tasks (payroll) prominent in daily
  proactive checks until explicitly closed. Neither exists — the scheduler fires jobs, it does
  not reconcile the calendar against reality.
  *filed 2026-08-09 from Inbox (2026-08-05T15:19Z) · Mike via Synthesizer*

- **[DB-0809-06] The browser tab does not live-refresh on messages sent from elsewhere.** A
  message from the terminal or the Android app appears only after a manual reload; app and
  terminal sync fine. Transport is ruled out by the entry's own diagnosis — this is a
  client-side render path. `ace22c7` (2026-08-01) fixed the adjacent half-open-socket case
  (`STALE_AFTER_MS`) and never runs when the socket was not actually dead. **Needs live
  reproduction before code:** open the tab, send from the terminal, watch.
  *filed 2026-08-01/02 from conversation — the only `## Now` item whose provenance line does not
  name its reporter; treat "Mike raised it" as likely but unconfirmed · re-checked 2026-08-05,
  adjacent fix found but different code path*

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
- **[DB-0803-06]** After ~100 exchanges the app renders messages twice: `shownIds` does a full
  `.clear()` at [static/index.html:944](static/index.html#L944) and [:971](static/index.html#L971)
  instead of evicting oldest-first, so the next reconnect repopulates and immediately empties it
  and any catch-up `'message'` looks unseen. `eea3faf` fixed a narrower ordering bug in the same
  lines. **Dev-session find, never reported — promote it the day Mike sees a doubled message.**
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
- **[DB-0809-12]** Hallucinated log dates in mike's tree (`2024-08-04.json` alongside a correct
  `2026-08-04.json`; earlier `2025-*` files). **Needs the VM** — the Mac copy is a stale mirror.
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
  shipped 2026-08-04 and sent for real 2026-08-05, three lines below.

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
  `2026-08-05T04:30:19.777295Z`

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

---

## Agent-file enhancement backlogs

**These live in the agent files, and only there.** Each specialist's `## Enhancement backlog`
at the bottom of `config/agents/{name}.md` is the single copy. A mirror sat here for one day in
August 2026 — 32% of the file, and it made the backlog look three times its real size.

`grep -l "## Enhancement backlog" config/agents/*.md`
