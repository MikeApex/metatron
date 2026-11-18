# Capture fidelity — the agent is shown what it was told and did not keep

*Plan, 2026-11-18. Opus 5.5. Brief: `archive/handoffs/2026-10-29-capture-fidelity-plan-prompt.md`;
the review of that brief: `archive/plans/adversarial_review_capture-fidelity-plan-prompt_2026-10-29.md`.
Mike's decisions so far are in § 9 and are not re-opened here. "Review finding N" = the 10-29 review of the brief; "plan review N" = `archive/plans/adversarial_review_capture_fidelity_plan_2026-11-18.md`.*

---

## 1. The need

**A user tells Metatron a fact about their life; it is acknowledged and not kept.** Nothing tells
them, nothing tells the agent, and the next session plans around a gap the user believes they
filled. Today the only way a miss is found is a developer reading transcripts.

**Evidence (trial_1029, 2026-10-29).** In a first interview the user gave eight day-shape facts.
The interviewer saved five. It missed "work is 9–5 but often runs late" (said twice, in two turns
with no tool call), weekend times ("out later on weekends and sleep in until around 10") and the
after-lunch slump ("crash out after lunch"). It also saved dinner for all seven days when the user
had described weekdays. The instruction to save each fact in the turn it is given was already in
the file. **An instruction alone did not hold.**

**What the record of that case is, stated plainly (review finding 3).** The trial accounts were
deleted on 2026-10-29, their data directories and conversation rows with them
(`scripts/accounts.py`). The three phrases above, from the brief, are the only surviving record.
The replay fixture in § 7 is therefore **authored from paraphrase, not recovered**, and is a
regression test of the mechanism, not a measurement of the miss rate.

**The measurement that is possible.** The VM keeps every day of `mike`'s traces since June:
each request's exact user words, `is_proactive`, and every tool call with its full arguments
(`core/trace.py:_serialize`, `ToolCallRecord`). No job deletes them. That makes `mike`'s
ordinary turns measurable now, before and after. **`mike` has never run in interview mode**, so
the interviewer half cannot be measured from history at all; its first real evidence is Iva's
interview (Mike: test with Iva; § 7.3 adds a rehearsal before it).

## 2. Survey — who records what a user says, and v1 scope

| Writer | Fact types | Tool | v1? | Why |
|---|---|---|---|---|
| Goals Interviewer | day shape | `set_day_shape` | **yes** | the known case |
| Goals Interviewer | goals | `update_goal` | **yes** | same turn shape, same coverage channel |
| Goals Interviewer | remembered good period | `write_baseline_period` | no — coverage already tracks presence | one record per interview; the coverage block already says "not yet" |
| Goals Interviewer | purpose, guiding star | `write_config` (approval-gated) | no | already tracked by the coverage block and the confirm card |
| Synthesizer | tasks the user mentions | `open_task` | **yes** | the most frequent fact in ordinary use |
| Synthesizer | day-shape changes in passing | `set_day_shape` (incl. `day_overrides`) | **yes** | same schema as the interviewer's |
| Synthesizer | preferences | `write_persona` | **yes** | |
| Synthesizer | profile facts | `write_profile` | **yes** | |
| Synthesizer | goals mentioned in passing | `update_goal` | **yes** | it holds the grant (`routing_cloud.yaml:81`) |
| Relationships | contacts | `write_contact` | **later** | the Synthesizer does not hold `write_contact`; the note would have to reach a specialist mid-dispatch — a second channel, built once v1 has data |
| Diarist | what the user reported doing | `write_log` | **later** | fire-and-forget on a daemon thread with no trace of its own (`check_false_action_claims` docstring) — nothing to compare against until it has one |
| — | task completions | `update_task` | **excluded** | owned by `_task_hint_block`, in code, already live; two notes about one fact would compete |

Measured vs estimated: **nothing in this table's miss rates is measured yet.** Step 1 of the build
(§ 6) is the measurement — the backfill over `mike`'s history, labels guessed by the tool and
corrected by Mike (§ 5.6).

## 3. The relatives, and the decision for each

| Relative | What it does | Decision |
|---|---|---|
| `_task_hint_block()` (`core/orchestrator.py:7072`, `tools/obligations.py:completion_hints`) | code reads the user's words before the Synthesizer, names the task that may be done | **Same family, sits beside it.** The capture note is placed next to `task_hint` in both pipeline twins and follows its rules: user turns only, read-only, built before the sign-off decision. Completions stay the hint's; capture excludes them. |
| Interview coverage block (`core/interview.py:228`) | code-built account of what is saved, trusted over memory | **Extended.** Pending capture lines are appended to it — the channel the interviewer already trusts. |
| `check_false_action_claims()` / `FALSE_ACTION_CLAIM` (`:6940`) | a reply claims a save that never happened | **Separate — the inverse failure.** Reuse its trace readers (`_trace_tool_names`, `_is_write_tool`) for "what was written this turn"; no shared state. |
| `enforce_pending_receipt()` (`:2074`) | stops a reply claiming an approval-gated action is done | **Separate.** Already runs in `run_turn`; untouched. |
| `ROUTING_MISS` (`tools/logger.py`) | the Synthesizer reports what no specialist surfaced — self-reported, unreliable (`[DB-0902-01]`) | **Not repeated.** No agent reports its own misses: an independent extractor proposes, code compares. Capture outcomes do **not** go to `quality_events.json` (which feeds the backlog) — a per-turn stream there is the volume that teaches a reader to skip it. |

## 4. The design

### 4.1 Shape — prevent where a stage allows it, catch one turn later where it does not

**Ordinary turns (Synthesizer): prevented in the same turn, no added latency.** The extractor is
started on a thread the moment the pipeline has the user's words, **concurrently with the
Coordinator**. It is joined after the specialists return, so their writes are already in the
trace. Code then compares, and the misses go into the Synthesizer's input as a CAPTURE NOTE, next to
`task_hint`. **The Synthesizer runs once, as today.** The Coordinator and specialist dispatch take
seconds, while the extractor is one short bulk-tier call, so the join should not wait. If it does
not finish in time, the join does not wait: the turn proceeds without the note, and the result is
held for the next turn.

**The note makes the Synthesizer's unprompted behaviour unobservable, so a holdout measures it
(plan review 1).** For every kind except a specialist's `open_task`, the Synthesizer is the
writer, and it runs after the join. Showing it every candidate would leave nothing to compare
against: "saved unprompted" and "saved because told" would be indistinguishable. So, during each
user's **measurement window** (their first 14 days with capture on), **1 eligible turn in 5** is a
holdout, chosen by a seeded random draw. On a holdout turn:

- the extractor runs and the comparison is made, exactly as on any other turn;
- **no note is shown**;
- after the Synthesizer, code records whether each candidate was saved anyway
  (`held_out_saved` / `held_out_unsaved`).

The holdout's unsaved share **is the live miss rate**. Shown turns' accept rate is read against
it. Outside the window the holdout rate is 0.

The rate and the window live in `config/modules/capture.yaml`, so a later user's window is a
config fact, not a code change. The cost is that 1 in 5 of a new user's turns goes without
prevention for two weeks; that is the price of a number that means something.

**Interviews: caught one turn later, no added latency.** The interviewer has no stage before it to
hide a call behind. The extractor starts on a thread alongside the interviewer's own call. After
the reply, code compares its candidates against **what this turn changed in the stored record**,
and the misses go into the **next** turn's coverage block. In an interview the next turn is
seconds away, so late-by-one costs nothing. No holdout is needed here: the comparison happens
after the writer's turn and before any note, so the unprompted miss rate is observed directly.

**Why a record snapshot, not the trace (plan review 2).** `run_turn` never holds a trace:
`run_session` opens one on entry and `finish_request_trace` clears it before returning. So
`run_turn` reads the day shape (`read_shape`) and the goals file before calling `run_session`,
reads them again after, and diffs the two — the diff is what this turn wrote. Both interviewer v1
kinds live in those two records. Trace and spend-gate ownership stay where they are.

*Change from the 2026-11-18 chat:* a code-only pre-hint for the interviewer (clock times, day
names) was proposed alongside this. It is dropped. Given the one-turn lag above, it would be a
second extraction mechanism to maintain for no measurable gain.

**Exits that skip the writer.** The sign-off skip ("over and out", `:7252`) and the spend-cap
refusal never reach the Synthesizer. On a sign-off, the result is held for the next user turn. On
a spend refusal the extractor never starts: the gate runs first, and the extractor is a model call
like any other.

**Never on a proactive turn.** The thread starts only when `has_real_user_turn()` is true. A
scheduled session has no user words by construction.

### 4.2 The extractor

- **Agent:** `capture_extractor`. Code-only, added to `CODE_ONLY_AGENTS` (`tools/subagent.py:30`).
  It is called `bare=True` with `complexity="quick"`, has an empty tool grant, and runs on the bulk
  tier (`gemini-3.5-flash-lite`). This is the `accountability_judge` shape exactly
  (`tools/accountability.py:858`).
- **Its input**, built in code:
  1. the user's words this turn;
  2. the last six messages, the Coordinator's window (`_COORD_HISTORY_MESSAGES`), so that "dinner's
     at six" can be read as *weekdays*;
  3. **what is already saved** for the v1 fact types, rendered as compact readable text: the
     day-shape sections from `read_shape()` (*not* `day_shape.digest()`, which is a 16-character
     hash for the planner's change gate — plan review 4), open task titles, goal titles, and
     profile and preference keys;
  4. the fact catalogue, generated from `SECTIONS`/`FIELDS` (`tools/day_shape.py:109,130`) and the
     v1 tools' schemas, so it cannot drift from what the tools accept.
- **Its output:** a JSON list, one object per candidate, with closed enums:

  ```
  {kind: day_shape|goal|task|preference|profile,
   target: <section or field, from the catalogue>,
   proposal: <an entry shaped exactly as the tool takes it — days included>,
   disposition: save | ask | declined,
   quote: <the user's words it rests on, ≤ 120 chars>}
  ```

  Anything that fails to parse is dropped and counted (§ 4.5).

  **Day-shape proposals** are validated by the tool's own `day_shape._validate_entry` /
  `_validate`, so a day-shape note never proposes what `set_day_shape` would refuse.

  **The other four kinds have no validator separate from their write** (plan review 5):
  `open_task`, `update_goal`, `write_persona` and `write_profile` all validate inline. Their
  proposals are therefore **plain-language only** ("keep: a task to call the dentist this week").
  The agent makes the call, and the tool validates it as it always does. No tool file is
  refactored for v1.
- **Tracing (plan review 3).**
  - **Inside the pipeline**, the extractor thread binds the request's trace (`set_trace`) and
    `persona_scope`, so `run_session` nests the call in the user's turn, where the spend meter
    counts it.
  - **Everywhere else** — the interviewer thread, `--backfill`, `--eval` — `tools/capture.py` checks the
    spend guard itself (`check_before_session` only — **not** `_spend_gate()`, whose
    `note_session_start` would count each call toward the 60-an-hour stop and could refuse a
    live interview; found at commit time), then opens a trace with `is_proactive=True, source="capture"` and
    closes it after the call.

  `tools/analytics.py:rollup_day` skips `source == "capture"`, so A9 counts these calls as neither
  user nor proactive sessions. The backfill's turn reader skips them too, so a measurement run can
  never measure itself.

### 4.3 What counts as a fact (review finding 5)

The fact definition belongs to the extractor's instruction file and to these rules, **not to a
test fixture**:

- **save:** stated as standing or habitual ("work is 9–5", "I sleep in until 10 on weekends"), or
  with an explicit date ("I'm free of childcare today" → a `day_overrides` entry).
- **ask:** a pattern stated loosely enough that saving it would be a guess about firmness or days
  ("crash out after lunch" → is early afternoon a light window, and on which days?). The note
  tells the agent to ask, not to save.
- **not a fact:** a state of the moment ("I'm so tired today"), an opinion, or something the user
  is reporting about someone else.
- **declined:** the user said not to keep it, or answered "no" to the agent's own offer to keep it
  (read from the previous assistant message). It is never shown, only counted.

### 4.4 The comparison — value-level, not presence (review finding 1)

This is all code, with no model. "What this turn wrote" is read from different places on each path:

- **ordinary turns:** the trace's write-tool calls, read with `_trace_tool_names`' walker extended
  to carry each call's arguments;
- **interviews:** the before/after record diff (§ 4.1).

**When the comparison runs.** On an ordinary turn it runs twice:

- **before the Synthesizer**, to drop what a specialist already wrote this turn and what the
  stored record already holds;
- **after the Synthesizer**, to record each outcome (§ 4.5). The writer has then had its turn,
  which is what makes `saved_by_agent` reachable (plan review 1).

**How a write is matched — two rules, by kind (plan review 6):**

1. **Day shape, matched structurally.** A write matches a candidate when it has the same section
   and the same `_entry_key` (`tools/day_shape.py:648`). Within a match, the comparison is on days
   and times:
   - **equal** → `saved_by_agent` / `accepted`;
   - **different** → `mismatch` / `edited`.

   This is the only kind with a mismatch. It is the seven-day dinner, shown as *"dinner was saved
   for every day; they described weekdays."*
2. **Tasks, goals, preferences and profile facts, matched by words.** Each is a free-text field
   written in the model's own phrasing. A write matches a candidate when it is the **same tool**
   and its text shares **≥ 50% of the candidate's content words**. Content words are tokenised the
   way `tools/obligations._task_tokens` does it, with stop-words removed. These kinds are only
   ever saved or unsaved: there is **no mismatch and no edited outcome for free text**, because
   no rule here could tell an edit from a rephrasing.

**The matcher can be wrong, so it is labelled.** Its saved/unsaved call is one of the things
Mike's labels check (§ 5.2).

A candidate the stored record already holds, from an earlier turn or session, is dropped silently.
That is what the saved-record input is for: a fact the user repeats is not a miss.

### 4.5 How a miss reaches the agent, and its lifecycle

- **Plain words, never identifiers.** Both notes travel inside the turn's input, and
  `filter_output()` exempts identifiers the user "typed" (the comment at `core/interview.py:209`).
  An identifier in the note would therefore let the same identifier through in the reply. The note
  says "when work ends", never `work_end`. The agent maps plain words to its tool, as it already
  does from the coverage block.
- **The Synthesizer's note:** `CAPTURE NOTE — from what the user said this turn, not yet kept`,
  followed by at most **three** lines, each worded as a proposal ("keep: work ends 17:00 on
  weekdays, often later" / "ask: whether early afternoon should stay light"). There is no note when
  nothing is pending.
- **The interviewer's lines:** appended to the coverage block under `Said but not yet saved:`, in
  the same format.
- **Shown once.** After the turn that shows a proposal, code reads that turn's writes and records
  one outcome:
  - `accepted` — saved as proposed;
  - `edited` — saved with a different value or days (day shape only);
  - `not_acted` — nothing saved, including when the agent asked a question.

  On a holdout turn the outcome is `held_out_saved` or `held_out_unsaved` instead, and nothing
  is pending.

  The proposal is then cleared, whatever the outcome. Showing it again is how a list becomes noise.
  A `not_acted` that was really a question is separated by the labels in § 5.6, not guessed at in
  code.
- **Cap and expiry.** At most three pending proposals per persona, newest kept. Each expires
  24 hours after it was extracted, unshown, so a sign-off-held fact from this morning does not
  surface tomorrow.

### 4.6 The training record — content-free

`data/personas/{p}/capture/outcomes.jsonl`, append-only, one row per candidate:

```
{ts, request_id, agent, kind, target, disposition, outcome, holdout, window_day,
 extractor_ms, extractor_tokens_in, extractor_tokens_out}
```

**No `proposal`, no `quote`, no values.** A test asserts the allowed key set (§ 7). This follows
the A9 rollup discipline (`ROADMAP.md` § A9).

The proposals themselves, which do contain the user's facts, live only in
`data/personas/{p}/capture/pending.json`. That file is sensitive tier, in the persona's own
directory like every other record of theirs, holds at most three entries, and each expires in a
day.

**How it is read (decision 5: a weekly report, built for the Observer):**
`python3 -m tools.capture --report [--persona p] [--since YYYY-MM-DD]` prints the table per agent
× kind:

- eligible turns, and turns the extractor ran on;
- candidates by disposition;
- outcome counts;
- **miss rate**:
  - ordinary turns: `held_out_unsaved` / all held-out candidates;
  - interviews: candidates unsaved at the post-reply comparison;
- **accept rate**: (`accepted` + `edited`) / all shown proposals;
- each figure beside its benchmark from `capture.yaml` (§ 5.3), marked pass or fail.

A weekly scheduler `function:` job writes the same table to `capture/weekly.jsonl`, which is the
file the Observer (`project_observer_agent`) will read when it exists. The Observer is not built
here.

## 5. Measuring whether it works (review finding 4)

### 5.1 The baseline, from `mike`'s history — the first build step

`python3 -m tools.capture --backfill --persona mike --days 60` runs on the VM. It takes every real
user turn from the traces, skipping proactive turns and `source == "capture"` traces. It runs the
extractor on each one, then compares the candidates against **that turn's own tool calls**, which
the traces keep with their arguments. Candidates not saved that turn are checked against the
record **as it stands today**.

This is the **pre-deploy baseline** and the input to the labels. The live miss rate comes from the
holdout (§ 4.1), which is a concurrent control and the better number. The backfill is the
"before" it is compared with.

**Known distortion:** a fact saved in a later turn reads as already held against today's record,
so the baseline **under-counts** misses. The direction is stated, so the comparison is
conservative.

### 5.2 Labels — guessed by the tool, corrected by Mike (decision 6)

The backfill writes a review file on the VM, `capture/backfill_review_2026-11-<dd>.jsonl`, holding
the user's words, each candidate, the matcher's saved/unsaved call, and the **tool's guessed
label**:

- `real` — a fact that should have been kept;
- `not_a_fact`;
- `wrong_kind`;
- `matcher_wrong` — saved and unsaved are the wrong way round.

Mike corrects the sample in a walkthrough, using `python3 -m tools.capture --label` on the VM: it
shows one item at a time, Enter accepts the guess, and one keystroke changes it. It takes about
25–30 minutes.

- **Precision:** a sample of **100 candidates**.
- **Recall:** **50 turns where the extractor found nothing**. Mike confirms each, or names the fact
  it missed.

The higher bars in § 5.3 need these sizes. At 50 labels, precision is only known to about ±8
points, which cannot tell 90% from 82%.

### 5.3 Pass criteria — fixed minimums now, raised to measured results (Mike, 2026-11-18)

| Measure | Source | **Minimum** |
|---|---|---|
| Extractor precision | § 5.2, 100 labels | **≥ 90%** real facts |
| Extractor recall | § 5.2, found + missed facts | **≥ 80%** |
| Live miss rate | holdout, 14-day window | **≤ ¼ of the backfill baseline**, per kind with ≥ 20 candidates |
| Accept + edit rate on shown proposals | `outcomes.jsonl`, 14-day window | **≥ 75%** |
| Matcher accuracy | § 5.2 `matcher_wrong` | **≥ 90%** |
| Mismatch catches | `outcomes.jsonl` | reported only — too rare to benchmark |

**Gates:**

- Precision, recall and matcher accuracy **gate step 5**: no live note until they pass.
- If precision or recall fails, fix in this order: the extractor's instruction file first, then
  the reasoning tier (≈ $0.0035 a turn, roughly 2.5×). Moving to the reasoning tier is Mike's call,
  made with the measured number in hand.

**The benchmark for every later user.** After `mike`'s 14-day window, each bar becomes:

- **max(minimum, `mike`'s measured − 5 points)**. For the miss rate the same rule applies to the
  reduction.

The bars are written to `config/modules/capture.yaml` with the date and sample size. Iva's window,
and every later user's, is measured against them by `--report`.

- **Raised** only by a new measurement on a sample at least as large.
- **Lowered** only by Mike.
- The 5-point margin keeps normal variation between users from failing someone the tool serves
  well.

## 6. Build order and files

**Build in Opus 5.5 with Mike present. Red work is not delegated.**

1. **`tools/capture.py` (new, Amber).** Contains:
   - the extractor call;
   - the catalogue built from `SECTIONS`/`FIELDS` and the tool schemas;
   - validation through `day_shape`'s own validator (day shape only — § 4.2);
   - the comparison and both matchers of § 4.4;
   - the holdout draw;
   - the trace owner for calls with no parent trace (§ 4.2);
   - `pending.json` (cap 3, expiry 24h, a lock like `core/interview.py:_locked`);
   - `outcomes.jsonl`;
   - `--report`, `--backfill`, `--label` and `--eval`.

   Also in this step:
   - **`config/modules/capture.yaml` (new):** the holdout rate (0.2), the window (14 days), the
     join bound, the cap (3), the expiry (24h), the minimums of § 5.3, and the benchmark block that
     § 5.3 fills in later;
   - **`tools/analytics.py` (Amber):** `rollup_day` skips `source == "capture"` (plan review 3).
2. **`config/agents/capture_extractor.md` (new, RED)** and its entry in **both routing files
   (RED)**:
   - cloud: bulk tier, empty grant, the privacy-tier comment in the `accountability_judge` form;
   - local: `local: true`, mirroring `accountability_judge` in `routing.yaml:76`.
3. **`tools/subagent.py` (Amber):** add `capture_extractor` to `CODE_ONLY_AGENTS`, so no agent can
   dispatch it.
4. **Backfill and labels (§ 5.1–5.2).** Deploy steps 1–3 first. They are inert, because nothing
   calls them yet. Then run the backfill on the VM, then the labelling walkthrough with Mike.
   **The live note waits until precision, recall and matcher accuracy pass § 5.3.** Steps 5–8
   are built and deployed behind `enabled: false` in `capture.yaml`, which keeps the extractor
   from running on live turns. Turning the switch on is the gate.
5. **`core/orchestrator.py` (Amber), both pipeline twins (`:7199`ff and `:7475`ff) — kept
   identical:**
   - start the thread after the spend gate and before the Coordinator;
   - join after the specialists, with a bounded join;
   - build the CAPTURE NOTE beside `task_hint`;
   - after the Synthesizer, record outcomes.

   The thread binds the request's trace (`core/trace.set_trace`) and runs inside
   `persona_scope(persona)`. Both are thread-local (`core/trace.py:37`, `.claude/rules/personas.md`):
   without them the extractor's tokens are invisible to the spend meter and its persona does not
   resolve.

   On a holdout turn the note is not built. Its outcomes are still recorded after the Synthesizer.
6. **`core/interview.py` (Amber):**
   - `run_turn` snapshots the day shape and goals, starts the extractor thread (which owns its own
     `source="capture"` trace), and calls `run_session` unchanged;
   - after the reply, it diffs the snapshot and records outcomes and pending;
   - `coverage_block` appends `Said but not yet saved:`.
7. **`config/agents/synthesizer.md` and `config/agents/goals_interviewer.md` (RED):** one short
   paragraph each:
   - keep a `keep:` line if it matches what the user meant;
   - ask on an `ask:` line;
   - ignore a line that is wrong;
   - **never mention the note to the user** (Discretion).
8. **The weekly job (`core/scheduler.py` `_DEFAULT_JOBS`, which is RED):** a `function:` job, no
   model tokens.
9. **Deploy, then live checks (§ 7.3).**

**Collision check:** the reply-latency work (`archive/handoffs/2026-10-28-reply-latency-defer-thinking-cache-prompt.md`)
has not started. Whichever of the two builds runs second picks up the other's version of the
pipeline. Nothing else open touches these files (checked 2026-11-18: four idle peer sessions;
uncommitted work on `main` is the WhatsApp phone reader and the Build Inquiry drafts).

## 7. Tests — every live meter stubbed

### 7.1 Suite (`tests/test_capture_fidelity.py`, new)

1. **Day-shape matcher:**
   - same section, `_entry_key`, days and times → saved;
   - days differ → mismatch;
   - absent → unsaved;
   - already in the stored record → dropped.
2. **Free-text matcher:**
   - same tool with ≥ 50% shared content words → saved;
   - a rephrasing still matches;
   - an unrelated write of the same tool does not;
   - there is never a mismatch outcome.
3. **Validation:** a day-shape proposal its validator refuses is never shown. Malformed extractor
   JSON gives no candidates, counted.
4. **The trial_1029 replay** (authored, § 1): the stubbed extractor returns the eight facts; the
   interviewer stub writes the five it wrote, dinner for all seven days. The test asserts, via the
   snapshot diff:
   - work hours and weekend times pending as `keep:`;
   - the slump pending as `ask:`;
   - dinner shown as a mismatch;
   - the five correct saves silent.

   **Fails on today's code**, since no note exists.
5. **Both twins:**
   - the CAPTURE NOTE appears in the non-streaming and streaming Synthesizer input alike;
   - on a proactive turn the extractor is never called, asserted by a stub that fails if it is;
   - the extractor's tokens appear in the user turn's own trace.
6. **Holdout:** with the draw forced on, no note is shown and the outcome after the Synthesizer is
   `held_out_saved` / `held_out_unsaved`. Outside the window, the draw is never on.
7. **Sign-off:** a fact in an "over and out" turn is held, then shown on the next user turn.
8. **Interviewer:** the next turn's coverage block carries the line; the turn after does not
   (shown once).
9. **Lifecycle:** cap 3, newest kept; expiry at 24h.
10. **Content-free:** every `outcomes.jsonl` row's keys ⊆ the allowed set. No proposal or quote
    text appears anywhere in the file.
11. **Analytics:** a `source="capture"` trace is not counted by `rollup_day`, and the backfill
    reader skips it.
12. **Isolation:** `pending`/`outcomes` resolve under the request's persona. A thread started for
    `mike` cannot write under another persona.
13. **No identifiers in either note:** none of the catalogue's snake_case targets appears in the
    rendered note.
14. **Latency:** an extractor stub that sleeps past the join bound does not delay the Synthesizer;
    its result appears on the next turn.
15. **Saved-record input:** the extractor's saved-record text contains readable day-shape entries,
    never a 16-character hash.

### 7.2 One opt-in live eval

`python3 -m tools.capture --eval tests/fixtures/capture/trial_1029.json` makes real extractor calls
on the authored turns, capped at 20 calls. It **is not in the suite.** It checks the real
extractor against § 4.3 before the backfill spends money.

### 7.3 Live checks after deploy

1. **`mike`, ordinary turn.** In one message, say three day-shape facts and a task. Pass: the reply
   keeps all four in that same turn (or it was a holdout turn, which `outcomes.jsonl` says), and
   the rows are there.
2. **Iva's real interview** — the interviewer half's first live run. There is no rehearsal account
   (Mike, 2026-11-18). Read `--report --persona <hers>` the same day.

## 8. Cost

Prices are from `config/modules/spend_guard.yaml`:
- bulk `gemini-3.5-flash-lite`: $0.30 / $2.50 per M tokens;
- reasoning `gemini-3.8-flash`: $0.75 / $3.75 per M tokens.

Token counts are **estimates until step 4 measures them**.

- **Build:** ~1.0–1.4M Opus tokens over steps 1–9; ~0.15M Fable for this review, plus a cheap
  verify.
- **Run:**
  - per user turn, one extractor call: ~2,500 tokens in (instructions ~1,200, six messages ~800,
    digest ~500) and ~250 out, so **≈ $0.0014 per turn**;
  - per user: at 20–50 user turns a day, **$0.03–0.07/day**;
  - both users active: **$0.06–0.14/day, about 3–9% of Mike's $1.50–2.00/day**;
  - bounded by: user turns only (never proactive), the v1 writers only, and the bulk tier.
- **Ancillary:**
  - Synthesizer input grows ~150 tokens on turns with a note, ≈ $0.0001 each on the reasoning tier.
    It sits in the user message, so the cached prefix and the Vertex 4,096-token floor are
    untouched;
  - the backfill is one-off: ~16 user turns/day × 60 days ≈ 1,000 turns, so **≈ $1.50**, plus
    ~$0.03 for the eval;
  - Mike's labelling time: ~25–30 minutes, once;
  - disk: `outcomes.jsonl` ~200 bytes a row, ~10 KB/day/user, ~4 MB a year; `pending.json` is
    bounded at three entries.
- **Unseen:**
  1. **A dead extractor reads as "no misses."** The report prints *ran on N of M eligible turns*
     first, so silence is visible.
  2. **An untraced thread is unmetered.** Step 5 binds the trace in the thread, and test 5
     asserts the extractor's tokens appear in the request trace. Calls with no parent own a
     `source="capture"` trace, so they show in The Book and A9 skips them. The spend meter counts
     every model call directly (`core/spend_guard.record_tokens`), with or without a trace.
- **Things that persist** (§ Costs, three questions):
  - **`pending.json`:**
    1. its unit is bytes, at most three entries;
    2. it is deleted by being shown or by the 24h expiry, and a restart leaves it intact and still
       expiring by timestamp;
    3. no meter reports it, and none is needed at that size.
  - **`outcomes.jsonl`:**
    1. its unit is bytes, about 4 MB a year;
    2. nothing deletes it, deliberately: like the A9 rows, it is the asset;
    3. no meter reports it, and that is acceptable at this size.
- **Model recommendation:**
  - **build in Opus 5.5** (orchestrator twins, threading, the Red files with Mike present);
  - **review in Fable**, now on this plan and again on the diff before deploy;
  - the extractor runs on the **bulk tier** (decision 4).

## 9. Decisions

**Settled by Mike, 2026-11-18:**

1. v1 covers **both** the interviewer (day shape, goals) and ordinary turns (§ 2), and is tested
   with Iva.
2. **The extractor proposes; the agent writes** (accept, correct or dismiss). Whether a capture
   layer becomes the writer is decided at the agent rewrite, from the accept rate in § 5.3.
3. **Ambiguous facts are `ask`, not `save`** (§ 4.3).
4. **Bulk tier** for the extractor, revisited only if § 5.2's labels show it missing subtle facts.
5. **Weekly report, built for the Observer** (§ 4.6).
6. **Labels are guessed by the tool and corrected by Mike** (§ 5.2).
7. **Built now**, ahead of stage 2 and reply latency.
8. **Iva's data carries exactly `mike`'s clearances, universally** (recorded in `ROADMAP.md` § 0,
   amendment 2026-11-18), so the extractor and the training record need no per-user carve-out.

9. **Thresholds: raised, and benchmarked from measured results** (§ 5.3).
10. **No rehearsal account**: Iva's interview is the interviewer half's first live run.
11. **Backfill window: 60 days.**
12. **Shown once.**

**Made in the build, flagged for Mike:**

- **Holdout: 1 turn in 5, during each user's first 14 days** (§ 4.1, plan review 1). It is the
  only way to measure the Synthesizer's unprompted miss rate once the note exists. The cost is that
  a fifth of a new user's turns go without prevention for two weeks. It is a config value in
  `capture.yaml`, so it can be changed without code.
