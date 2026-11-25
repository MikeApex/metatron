# Claude Code time tracking — plan (draft for Mike's approval, 2026-11-25)

**Goal.** Measure *human time in front of Claude Code*, per project per day, from the session
logs — separating it from time the agent ran unattended — and keep the record from here on.
Not built. Awaiting approval.

## 0. What changed since the first answer (correction)

The first answer said exact timestamps reached back only to 2026-10-24. **That was wrong.**
The live log folder keeps ~30 days (Claude Code's default; no `cleanupPeriodDays` is set), but
`/archive` has been copying the verbatim logs to `archive/transcripts/raw/` — **459 files,
2026-04-03 → 2026-11-24, every event carrying an ISO timestamp** (1,033 typed messages there vs
329 in the live folder). So exact timing exists for April onward wherever a session was archived.
Gaps = sessions never archived and older than 30 days. April is thin (77 events in the whole month).

## 1. The metric — "human time in front of CC"

Evidence available per event: a timestamp, a kind (a message Mike typed / assistant output / tool
result / subagent / hook), the session, the project (folder), and text length. Typed message =
a `user` event whose content is a string, minus injected/scheduled prompts ("quiet check-in",
slash-command wrappers, hook text) — to be classified and checked by hand on a sample.

Per session, each **turn** = typed message at `T_u` → agent's last event `E` → next typed message
`T_next`. Pickup latency `L = T_next − E`.

1. **Writing time `W`** — before each typed message: estimated from its length (typing/dictation
   rate, parameter), floor and ceiling.
2. **Reading time `R`** — after each agent turn ends: estimated from the visible reply length
   (reading-rate parameter).
3. **Placement (revised after the check).** Reading is placed at the *start* of the latency
   window (reading happens when the reply lands, at `E`); writing at the *end* (just before
   `T_next`). Anything between them beyond `R + W + grace` is *away* and not counted. If
   `L ≤ R + W + grace` the whole latency is human time.
4. **Waiting counts when pickup was prompt (Mike).** Pickup is judged on the **residual
   `L − (R + W)`** (not raw `L`, which already contains reading and writing), against `P`
   (set from the histogram of that residual — expected bimodal). A prompt residual means the run
   was watched; a late one means its duration is **unattended agent time**, reported separately.
   **Runs are split (revised):** a run is cut at every event Mike did not cause (scheduled
   check-ins, `task-notification` wake-ups, resumes after a permission or plan prompt) and at any
   internal gap longer than `P`; only the piece adjacent to a prompt pickup counts as watched.
   A tool result that follows a permission/plan prompt is evidence Mike was present at that
   moment, not agent time.
5. **Simultaneous chats (Mike) (revised).** All sessions go onto one timeline and attended
   intervals are **unioned — never summed**. Another chat's activity credits only a window
   around that activity (± its own `R`/`W`/`bridge`), **never the whole of a walked-away run**;
   `bridge` joins two actual human-evidence intervals only, and the chain is capped at
   `max_chain` links so unrelated chats cannot merge into continuous false time. That is how a
   deeper multi-window session shows up as continuous time without a single quick message in
   window B crediting a 3-hour unattended build in window A.
   *Evidence times:* a message Mike typed during a run is logged as `queue-operation enqueue`
   at typing time — use that timestamp, not the later dequeue.
6. **Attribution (Mike, 11-25: per-chat metrics are not important — focus on session metrics).**
   The union total is the headline. Report **work sessions**: a maximal block of attended time with
   gaps ≤ `session_gap` (default 30 min) — with start, end, attended hours, unattended agent hours
   inside it, and chats involved. Per-project credit stays simple (an attended interval goes to
   the project of the chat read/typed in; overlap split equally) and is a secondary column, not a
   tuned output. No per-chat reporting.

Outputs per day and per project: **attended hours (headline) · unattended agent hours ·
span (first→last event, upper bound) · coverage flag** (archived / live / gap). Parameters
(`typing_rate`, `reading_rate`, `grace`, `P`, `bridge`) live in one config block and are reported
with every figure.

## 2. Phases

**Phase 1 — Month of exact data (live folder, 2026-10-24 → now; multi-model-mcp only — the other
three project folders hold no session logs, verified 11-25).**
- 1a. `cc_time_events.py` (global tool beside `archive_chats.py`): parse logs → *event ledger*
  rows (`ts, project, session, kind, chars, key`) — **no message text**. Session taken from the
  `sessionId` field, never the filename; skip the live folder's `.!NNNNN!<uuid>.jsonl` partial
  copies (292 present); rows with no `uuid` (e.g. `queue-operation`) keyed on
  (sessionId, timestamp, type, content hash). Idempotent; test that the live and raw copies of one
  session produce one row set. Subagent logs (`<session>/subagents/`, 141 files) are read in
  Phase 1 but flagged — the archive never copied them.
- 1b. Typed-vs-injected classifier by explicit allow/deny on tag prefix, `isSidechain`/path and
  compaction-summary flags (deny: `task-notification`, "This session is being continued…",
  command wrappers, scheduled check-ins, subagent dispatch prompts); hand-check stratified by
  kind, not a flat 50.
- 1c. Metric engine as §1, unit-tested on synthetic timelines (prompt pickup, late pickup,
  two overlapping chats, one chat spanning midnight, subagent-only activity).
- 1d. Latency histogram → choose `P`, `grace`; report sensitivity (attended hours at 3 values of
  each parameter) so the headline's uncertainty is visible.
- 1e. First report: per project/day for the month.

**Phase 2 — April → October from `archive/transcripts/raw/`.** Same engine, same parameters.
**Parameters are re-checked on this data, not assumed** — the archive holds top-level session
files only (no subagent logs) and each copy ends where the session stood at its last `/archive`,
so Phase 2 is a different measurement from Phase 1. Coverage is carried **per session** (a session
is marked *partial* when its last archived event is not a closing one), not per day. Coverage
audit per day against git commit times and `archive/transcripts/` filenames. **Gap-fill:** days
with commits but no archived log are shown as "worked, unmeasured" with commit span, plus an
*estimated* attended-hours **interval** (spread of the hours-per-commit ratio across covered days);
never mixed into the exact column. Caveat recorded: commits cluster on archive days, so the ratio
is biased — the interval, not a point figure, is the output.

**Phase 3 — Keep it from here on.**
- 3a. Ledger update runs at every session start (a global `SessionStart` hook) so nothing depends
  on `/archive` being run or on the 30-day window. Hook rules: incremental byte offsets per file,
  atomic write under a lock (two windows start together), **no stdout** (hook output is injected
  into context), and startup time measured on the real folder before it is called ~1 s.
- 3b. `archive_chats.py` edited (targeted edits, it is the only copy): call the ledger update,
  and stamp each `**You:**` line in the readable `.md` transcripts with its local time. Old
  transcripts are not regenerated.
- 3c. Weekly/on-demand report command.

**Phase 4 — Benchmark (Mike).** On chosen days Mike logs precise in-front-of-CC time (start/stop
list); compare to the engine, tune the five parameters, record the residual error. Option O1:
macOS app-focus history (frontmost VS Code) as a second ground truth — needs a Full Disk Access
grant; Mike's call.

## 3. Where things live

- Tool + ledger: `~/.claude/tools/cc_time_events.py`, `~/.claude/time_ledger/` (global, because
  the union spans projects). Reports: `~/.claude/time_ledger/reports/cc_time_report_YYYY-MM-DD_*.md`.
- Nothing in the Metatron repo changes except this plan. Time zone: system local time
  (assumption — confirm).

## 4. Decisions for Mike

- **D1 Parallel-chat attribution** — rec: credit the chat being read/typed in; split waiting equally.
- **D2 Ground truth** — rec: manual benchmark days first; O1 only if the manual days disagree.
- **D3 Retention** — rec: do **not** raise the 30-day log window (~10× disk, ~1.5 GB/yr, holds
  full text longer); the text-free ledger is the durable record.
- **D4 Other projects (chat, Gloz, actuarial)** — history is single-project (those folders hold no
  logs). Rec: keep the ledger global so they are collected from Phase 3 on; nothing to decide for
  the past.
- **D5 Time zone** — convert each event UTC → local with a named zone (rec: `Europe/London`,
  confirm), not a fixed offset: summer sessions are +0200/+0100 and 25 Oct has a repeated hour;
  intervals split at local midnight; unit-test 25 October.

## 5. Costs (Build · Run · Ancillary · Unseen)

- **Build:** ~one focused session; est. 150–300k tokens (≈ $2–6 on Sonnet 5.5; ≈ 1.5–2× on Opus) —
  estimate, not measured. No API spend beyond that.
- **Run:** 0 tokens. Ledger ≈ 1–2 MB/month, no text. Hook adds ~1 s to session start.
- **Ancillary:** disk only; no retention change (D3).
- **Unseen:** (a) parameter error — headline hours are a model, not a measurement, until Phase 4;
  (b) the ledger has no owner/expiry — it is Mike's, grows ~20 MB/yr, deleting it loses the record;
  no meter reports it; (c) a hook that fails silently would stop the ledger — add a "last updated"
  line to the report so staleness is visible.

## 6. Test plan

Synthetic-timeline unit tests (§1c); a hand-labelled day compared to the engine (Phase 4);
idempotency (run ledger twice → identical); coverage audit reconciles days to commits;
`archive_chats.py` output diffed before/after on one session (only the `**You:**` lines change).

## 7. Model & review

**Opus 5.5 adversarial check (11-25): ten defects, all accepted and folded into §§1–3 above**
(three high-confidence structural: an unattended wake-up can make a whole run look watched;
pickup was tested on raw latency that already contains reading and writing; the multi-chat rule
could credit a 3-hour unattended run for one short message elsewhere). I verified two of its
factual claims against the disk: the other three project folders hold no session logs, and the
live folder holds 141 subagent logs the archiver never copies. Its remaining points
(classifier edge cases, uuid-less rows, DST, hook concurrency, gap-fill bias) are in the revised
phases. The model assumptions in §1 stay unvalidated until Phase 4.

**Build model: Opus 5.5 for the metric engine and classifier (1b–1d); Sonnet 5.5 for the
mechanical parts (ledger parser 1a, hook and `archive_chats.py` edits 3a–3b, report 3c).**
Reason: the defects were all in what counts as human evidence, not in parsing — a Sonnet build
would implement the plan literally and pass its own synthetic tests. Review: a different model
reads the finished engine against the hand-labelled day.
