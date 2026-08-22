# Closed Backlog Archive — through 2026-08-09

**This is the pre-revamp `DEV_BACKLOG.md`, preserved verbatim.** On 2026-08-09 the working
backlog was restructured (Now / Later / Machine log, ~150 lines) and this snapshot became the
home for everything closed. Nothing here was edited: every struck-through entry keeps its
evidence line, its commit or `file:line`, and the reasoning that closed it — including the
withdrawn and "not a bug" entries, which are the most valuable ones, because someone will
re-derive them.

**Live work is in [`../DEV_BACKLOG.md`](../DEV_BACKLOG.md).** The items that were genuinely
open on 2026-08-09 were carried forward there and re-tiered; this file is a read-only record.
Search it before re-filing anything — roughly a third of what looked open here turned out to be
already fixed, and this is where the proof lives. Rolls monthly: the next file is
`backlog_closed_2026-09.md`.

Why the split, in one line: the working file had reached 1,658 lines / 139 KB — 2.8× the size
that triggered the 2026-08-03 context audit — and about 35 of its entries were closed items
sitting inside the Open sections. Reasoning: `archive/PROJECT_LOG.md` § 2026-08-09.

---

## Closed 2026-08-19 — the one-lump reply: text streaming kept, spoken chunking built and reverted

- ~~**[DB-0818-10]** The reply lands in one lump after a long silence, so speech cannot start
  early.~~ **Closed by Mike's decision, 2026-08-19.** Two of the three candidate fixes were built
  and one was then deliberately removed. Commits: `81be0f7` (cache), `46f31b5` (Option A — text
  streaming, **kept**), `d8e8ef2` + `6c59411` (sentence-chunked TTS, **reverted**).

  **What shipped and stayed — the text streams.** The Gemini branch reached
  `_get_or_create_vertex_cache` for the first time *and* streams: `run_session_gemini_cached_stream()`
  → `_run_gemini_native_stream()`. Verified 9 chunks on the wire through
  `run_pipeline_session_stream`, with `cache_read=19,157` on the same turn. So the literal
  "one lump" complaint is fixed for the on-screen reply.

  **What was built and reverted — spoken sentence chunking.** Mike, 2026-08-19, after using it on
  the app: *"30 second delay after the language populated. Too many resources for an incremental
  gain."*

  **The measurement that settles it, and which any future proposal must beat:**
  - **The whole reply arrives in ~0.6s** (33.76s → 34.35s, live turn). Everything before it is
    Coordinator, specialists and thinking. **86% of Synthesizer-generated tokens are thinking**
    (18 real interactive turns: median 882 thinking vs 133 visible).
  - **Sentence release was never the bottleneck** — first sentence out **0.15s** after the first
    text chunk.
  - The lag Mike heard was client-side: synthesis had been chained behind *playback*, so each gap
    cost a full ~2.8s Kokoro round trip. Fixed in `6c59411` (parallel synthesis, ordered playback)
    — **and the gain was still only seconds against a ~30s wait.**

  **The generalisable conclusion:** chunked speech pays only when *generation* is slow relative to
  synthesis. Here generation is a sub-second burst and the wait is thinking. **Fix the thinking
  budget first.** Doing it in the other order buys a second and costs a security property.

  **Why the revert also closed a security gap.** Sentence-chunked TTS weakened `filter_output()`,
  the **OWASP LLM06** control on the user-facing path: its guarantee rests on suppressed text being
  recallable, which is true of a screen (`[RETRACT]` overwrites it) and false of a room. Mitigations
  narrowed it — server-side release, a lead buffer, a one-strike halt — but the residual gap was
  real and was **never accepted**: `filter_output` is shape-sensitive, so a passing prefix is not
  proof the response passes, and a sentence cleared before a response turned dirty had already been
  spoken. **Removing the feature closed the gap; the gap was not solved.** Full record, kept
  deliberately so nobody re-opens it unknowingly: `ROADMAP.md` § 5A **✅ CLOSED — spoken output
  could not be retracted**.

  **What remains, and it is not this item.** The silence Mike originally reported is the **thinking
  budget** — being handled separately, and now recorded in the Alpha check. Option (c), a "thinking"
  affordance, was found **already built** (the mic button reads `Thinking...` for the whole wait,
  `static/index.html`); its informative version is barred by `CLAUDE.md` § Discretion.

  **Three of this session's own claims were wrong and were caught by measurement, not review:** that
  the interactive/scheduled gap was ~46× (it compared against a median dominated by 19 near-empty
  scheduled turns); that Option A would close this item (86% thinking says otherwise); and that the
  speech change could not affect Coordinator dispatch (it could — in-band `[SPEAK]` markers
  corrupted the reply text, caught by `run_knowledge_routing.py`).

## Closed 2026-08-15 — `/backlog attack`: the lost exchange, and two faults found in the traces

- ~~**[DB-0810-12]** Vertex rejects a tool-call turn for a missing `thought_signature` and the
  exchange is lost — five times 08-04→08-09, plus uncounted web-app hits. Mike sees a raw SDK 400
  and the message is never recorded, on both apps.~~
  — **closed: `7214070`, merged `5cf0a5e`, deployed.** Where a signature is demanded (Google
  endpoints only) a turn whose assistant message carries unsigned function calls is recorded
  **signature-free** — assistant text plus a user `[tool results]` message naming the tools that
  ran. Nothing left for Vertex to validate, tools still dispatch once, **the exchange survives**,
  which was the reported harm. **Both unsigned routes closed, not only the evidenced one:** the
  `stream_delta_fallback` branch named by the 08-15 capture, *and* `blocking_replay[...]` — flagged
  in the item as never checked, and real, because the code appended `_signed` and classified it
  afterwards. Third route ruled out by inspection. `_run_gemini_native_loop` untouched, as the item
  de-prioritised it. **Rejected:** porting `_openai_compat_loop`'s tc0-only workaround (serialises
  parallel dispatch — the documented regression); dropping the turn from history (side effects
  repeat); retrying the blocking call (speculative). `tests/test_thought_signature.py` 12/12,
  **verified discriminating** — reverting only `core/orchestrator.py` reproduces the live
  `400 … at position 2`.
  **Closed on Mike's argument (2026-08-15), not on a fortnight's silence:** a *user-visible*
  recurrence would raise its own ticket, and this archive is consulted before re-filing, so holding
  the item open duplicates machinery that already works. **The residual, and why this entry carries
  a command instead:** the fix converts a loud failure into a silent one — the exchange now
  survives, so a recurrence leaves only a journal line nothing sweeps. The one check left, Mike's
  because it needs the VM, around 2026-08-29:
  `sudo journalctl -u metatron-server --since "2026-08-15" | grep signature_probe`
  Empty output is the closing evidence. A `:neutralized` line means the branch fired and the fix
  held. A bare 400 with **no** ledger line falsifies the diagnosis and sends the next look at
  `history` rather than at either branch.
  *Two live hypotheses remain unverifiable without an occurrence: that Vertex accepts the
  signature-free assistant+user pair as a valid continuation, and that the model does not re-issue
  tools it is told already ran. Both are standard OpenAI-compat shapes.*

---

## Closed 2026-08-15 — action provenance

- ~~**[DB-0810-13]** Specialists report actions they never took, and the Synthesizer relays it to
  Mike as fact — *"That's sent"* on 2026-08-10 for an email nothing had sent.~~
  — **closed: `0a3706c` (Python half), `1831730` (`synthesizer.md` half), both deployed and
  verified live on the VM.** Diagnosed the session before as a **missing-information** failure
  (design: `archive/plans/db081013_action_provenance_design_2026-08-15.md`), which is why no
  agent-file-only fix was attempted: the Synthesizer's input carried the Coordinator's directives
  and the specialists' prose, and nothing about which tools ran. Every request now ends with an
  `ACTIONS EXECUTED THIS REQUEST` block generated in Python from the trace — the state-changing
  tools that executed, failures marked, or an explicit `NONE`. Evidence, not a claim; no model is
  asked whether an action happened.
  **The classification is the substance**, not the line: `core/actions.py` sorts all 71 registered
  tools into actions and reads in one place, because a line listing `search_contacts` would repeat
  the `is_grounded()` mistake documented at `core/trace.py:107-118`. `tests/test_action_provenance.py`
  fails if a registered tool is in neither set, so the next tool added forces a classification
  instead of silently vanishing from the line.
  **Scoped to the request, not the agent** — `[DB-0810-02]` makes per-specialist attribution
  unreliable, and the design's per-specialist sketch was overridden by Mike on that basis. The
  fire-and-forget Diarist falls out of scope automatically as a consequence.
  **Evidence that closed it:** `NONE` on a request that changed nothing; `write_log — completed`;
  post-deploy `write_calendar_event`, `update_calendar_event` and `close_obligation` all
  correct, with no read tool ever on the line. Both calendar actions were also **confirmed to
  Mike** — the evidence that half 2 is not over-firing, which was the specific risk the deploy
  ordering existed to prevent. **The one case that cannot be staged** is the negative: whether the
  Synthesizer stays quiet when an action does not happen. That is now a matter of watching the
  next real failure, and the journal's `[actions]` line is how to audit it.
  **Out of scope by the design, still unfiled:** the *invented capability* half — scheduled
  sending does not exist, yet "Thursday, August 13th" was produced two turns before the false
  confirmation. Provenance stops the confirmation, not the invention. *closed 2026-08-15*

---

## Closed 2026-08-15 — `/backlog attack`, two clusters

- ~~**[DB-0810-09]** 158 quality events written and never read — `USER_CORRECTION` (139),
  `CALENDAR_DUPLICATE` (7) silently dropped by `scripts/sync_dev_backlog.py`'s `WANTED` set.~~
  — **closed: `048e937`.** Prerequisite fixed first — `write_quality_event()` now raises on
  blank `detail` (was ~70% empty on `USER_CORRECTION`). Both types added to `WANTED`;
  `CALENDAR_DUPLICATE` given a stable uid-pair `signature()` key (`CALENDAR_UID_RE`, same
  precedent as `DENIAL_RE`) so distinct duplicate pairs don't collapse on shared boilerplate
  prose. The structural fix is `tests/test_quality_event_reconciliation.py` — asserts every
  `event_type` literal emitted anywhere in `core/`/`tools/` is either in `WANTED` or explicitly
  named as intentionally dead (`KNOWN_DEAD_TYPES = {"ROUTING_MISS"}`), rather than a shared
  import, because `sync_dev_backlog.py` is deliberately stdlib-only (SessionStart hook, no
  venv). The test caught a third silently-dropped type not named in the original item,
  `CONTEXT_BLOCK_UNPARSED`, fixed in the same commit. **Not closed: where `USER_CORRECTION`'s
  139/day belongs long-term** — the item itself flagged that dumping it into `MACHINE_TYPES`'s
  per-entry Machine log may be the wrong home (a digest or dedicated section was suggested
  instead); that redesign needs its own `DEV_BACKLOG.md` heading and wasn't in scope here. Landed
  in `MACHINE_TYPES` for now so the silent drop stops. *deploy owed — `tools/logger.py` runs on
  the VM.*

- ~~**[DB-0810-17]**(a) "How many contacts do we have?" — Coordinator declined a CRM
  contact-count question as needing an external connection it doesn't have, when Relationships
  already holds `list_contacts`/`search_contacts` and could have answered from data on hand.~~
  — **(a) closed: `b11e775`** (instruction-only — `coordinator.md`'s Relationships routing block
  now calls out contact-store questions explicitly and says not to decline them). **(b) — an
  external CRM bridge — stays open**, blocked on a decision only Mike can make (which CRM, sync
  direction); carried forward, see `DEV_BACKLOG.md` for current wording.

- ~~**[DB-0814-01]** The scheduled inbox check reports "nothing found" up to six times a day —
  Mike asked for it to notify only when new actionable mail arrives.~~ — **closed: `b11e775`.**
  Instruction-only, as scoped: `logistics.md`'s horizon scan now distinguishes checking a
  pending item (fine, every session) from reporting it unchanged (not fine) — a pending
  confirmation whose status hasn't changed since it was last surfaced no longer repeats in
  `HORIZON_ITEMS`/`PENDING CONFIRMATION` until something actually changes or it's genuinely aged.

*Not closed, retitled to state what's left:* **[DB-0814-02]** (`open_threads` now carries a
server-stamped `added` date per entry, `d40e73c` — the *expiry policy* deliberately remains
undecided, that was never this item's scope). See `DEV_BACKLOG.md` for current wording.

*All three worktree branches merged into `main` clean (`2fcf0bc`, `66fd00b`), `qa_sweep.sh` 9/9
on the integrated tree. Both worker commits were blocked at commit time by a `hook_commit_guard.py`
bug (worktree sessions resolve the wrong project root) — re-verified independently and committed
by the coordinating session with Mike's explicit approval; the bug itself is filed as
`[DB-0815-01]`. Full reasoning: `archive/PROJECT_LOG.md` § 2026-08-15 (`/backlog attack` — three
clusters).*

---

## Closed 2026-08-14 — Phase 5 tail: logger registered, audit tables fixed

- ~~**[DB-0814-05]** Finish Phase 5 of the context system: register the `InstructionsLoaded`
  logger and correct `audit_context_load.py`.~~ — **closed: `b07f5da`.** `InstructionsLoaded`
  registered in `.claude/settings.json` with no matcher; `scripts/audit_context_load.py:34-49`'s
  `CONDITIONAL` table now lists the five `.claude/rules/*.md` files instead of the pre-split
  architecture, verified by running the script against a real session. **Not the same as retiring
  the hook** — that needs a later session to read `.claude/instructions_loaded.jsonl` once it has
  real entries and answer the two questions the hook exists for (Grep-tool delivery, worktree
  delivery); next-session prompt at `~/.claude/plans/context_phase5_close_prompt_2026-08-14.md`.
  Full reasoning: `archive/PROJECT_LOG.md` § 2026-08-14, `2026-08-14-11-phase5-tail-closed-logger-registered.md`.

## Closed 2026-08-14 — two Inbox entries that were not what they said

*Both closed at triage, before any work was scheduled against them. Recorded here rather than
dropped, because the standing rule is that an item which resurfaces must be able to show it was
checked once — and the second of these describes a capability the system already has.*

- ~~**[inbox 2026-08-12T08:25Z]** "Stop assuming passed calendar events are completed. Implement a
  reconciliation loop to check back on scheduled blocks and **actively alert/push** the user based
  on calendar intent versus actual reality."~~ — **closed: already built, and the alert half was
  deliberately rejected in code.** `daily_calendar_reconcile` is a `_DEFAULT_JOBS` entry firing
  05:40 daily for every persona (`core/scheduler.py:421`), calling `reconcile_check()` at
  [tools/calendar_reconcile.py:323](../tools/calendar_reconcile.py#L323); it notes passed events
  nothing in the record mentions, for the morning brief to decide about. **The push half is not an
  omission.** The job's own comment states it: *"`notification: False` is not a preference —
  `reconcile_check` returns a plain string and never a notify dict, because the check is crude text
  matching and cannot support the claim that anything was missed."* Pushing on a crude text match
  is the false-confidence failure `[DB-0810-13]` exists for. **The genuinely open remainder is
  `[DB-0809-21]`(3)**, which is time-gated on a real unreferenced calendar event existing — the
  mechanism re-ran clean with 0 candidates, so it works and has never had anything to find.
  *Do not re-file this as new; it is `[DB-0809-21]`(3) wearing different words.* *closed 2026-08-14*

- ~~**[inbox 2026-08-11T08:36Z, first half]** "Stop the read-back of triaged emails."~~ —
  **closed: already applied.** The entry records it as applied to the persona at the time of
  reporting. **Filed with a caveat that outlived it:** this is *design*, not a Mike deviation —
  nobody wants their triaged mail read back — so a persona-only copy is the wrong home and should
  be promoted to the agent layer with the persona copy deleted in the same pass
  (`CLAUDE.md` § One Home Per Rule Class). Not re-opened as an item, because the user-visible
  behaviour is correct; noted here so that whoever next audits `mike.md` against the agent files
  knows this line is a promotion candidate rather than a genuine refinement. The second half of
  that Inbox entry — ticket-based mailbox management — is live as `[DB-0814-03]`.
  *closed 2026-08-14*

---

## Closed 2026-08-14 — the due-date marker, and the false positive tagging it produced

- ~~**[DB-0813-01]** A date-gated backlog item comes due and nothing announces it.~~ — **closed:
  mechanism built (`20ad1ff`), and the tag that makes it fire landed 2026-08-14.**
  `sync_dev_backlog.py` defines and parses a `due: YYYY-MM-DD` marker and surfaces `⚠ due:` in the
  count line beside `⚠ machine:`; `--today` is its testing seam. `[DB-0809-02]` now carries
  `due: 2026-08-17` (the end of the trace week it was filed against), verified on both sides of the
  boundary: `--today 2026-08-16` prints no clause, `--today 2026-08-17` prints
  `⚠ due: DB-0809-02`.

  **Found by running that verification, not by reading the code — defect 24 of 24.** The first
  `--today 2026-08-17` run named **two** items, `DB-0809-02` *and* `DB-0813-01`. The second was a
  false positive with an instructive cause: this item's own body said *"Remaining: add
  `due: 2026-08-17` to `[DB-0809-02]`"*, and `DUE_RE` matched the marker **in the prose that
  described it**. The colon anchor documented at `scripts/sync_dev_backlog.py:149-155` was chosen
  so a prose date (*"due 2026-08-11, do not check before then"*) would not match — it does that
  correctly. What it cannot distinguish is prose that **quotes the marker verbatim**, which is
  exactly what any item documenting the convention will contain.

  **The obvious fix — ignore markers inside backticks — is worse than the bug**, because every
  real marker is written in backticks too (`[DB-0809-02]`'s included); it would disable the
  feature outright. No code change was made. The false positive is self-limiting: it existed only
  while an item was open *about* the convention, and closing this item removed it. The class is
  recorded here so the next occurrence is recognised rather than re-diagnosed — if an item must
  quote the marker in future, write it without the colon (`a due marker dated 2026-08-17`).

  **Do not tag `[DB-0809-21]`.** It is event-gated, not date-gated — it needs a real unreferenced
  calendar event to exist — so no date will ever make it genuinely due, and a marker on it would
  fire every day forever.
  *filed 2026-08-13 — the delay, not the fix, was the item · built 2026-08-14 in §10b run 1 ·
  closed 2026-08-14 on the tag landing*

---

## Closed 2026-08-13 — the one-week AgentRecord count came due and passed

- ~~**[DB-0804-01]** One-week count confirming `[DB-0803-02]`'s fix under real scheduler fires.~~ —
  **closed, passed.** The item was time-gated (*"due 2026-08-11, do not check before then"*) and
  went unchecked for two days after coming due; found by a `/backlog` verification pass on 08-13.
  **Baseline 18 `AgentRecord` errors in 7 days → 2.** Counted on the VM over the same 7-day window
  and the same journal units as the baseline, so the comparison is like-for-like. The fix holds.
  *The lesson is not about the fix — it is that a date-gated item has no mechanism to announce
  itself when its date arrives, and this one sat done-but-unread for 48 hours.*

## Closed 2026-08-11 — live travel verified; mailbox cadence default

- ~~**[DB-0810-14] Live travel status is fixed in code and unverified in production.**~~ —
  **closed, verified live.** Trace **`8c9d8963`**, query *"What is the current status of the
  Central Line on the London Underground?"*: routed Coordinator → Logistics → Synthesizer, with
  **`get_tfl_status` actually called by `logistics` in turn 0** and recorded in the trace's tool-call
  history. That was the pass condition, and it was chosen deliberately over "the answer looks
  right" — the failure this item guarded against was *fabrication*, which reads as success.
  Confirms `bc1a552` (the `or []` guards on `grounding_chunks`/`web_search_queries`, ending the
  `'NoneType' object is not iterable` crash) and `d0774f8` (live travel status routed to Logistics,
  which holds the feed) are both working in production. The 14:03 fabricated answer on 2026-08-10
  fell in the 3-hour window *between* those two commits, which is why it was neither crash nor
  correct. *Opened and closed inside 24h; the item existed only because two commits plausibly
  covering a symptom are not evidence the symptom is gone.*

- ~~**[DB-0810-16] No global default for how often the mailbox is checked.**~~ — **closed, built
  and deployed.** Mike asked for a default *"for how often **any user** checks the mailbox"* — the
  wording made it design, not a Mike deviation, so it had to land somewhere every persona inherits.
  - **`config/templates/email.yaml` (new) is the single home**, holding `check_interval_minutes: 240`.
    It doubles as the provisioning source *and* the runtime fallback, because a template is copied
    once at persona creation and nothing propagates a later change — without the fallback the
    default would reach only personas created after it, which for "any user" is the wrong half.
  - **`tools/mail.py` — `check_interval_minutes(persona)`**: persona file → template → constant 240,
    returned on both of `read_email`'s success paths. Every degenerate input tested (absent, null,
    garbage, zero, negative all fall through; numeric string coerces).
  - **`config/agents/logistics.md:215`** states the actual behaviour: a floor on *speculative*
    re-reads, explicitly overridden when the user asks or a specific thing is being looked for.
  - **`scripts/new_persona.sh:81`** — `email.yaml` added to the template copy list; it was absent,
    so new personas were being provisioned with no `email.yaml` at all. Verified by provisioning a
    throwaway `cadence_probe` persona, confirming it inherited the file and resolved 240, then
    removing it.
  - **Deploy-safety rule 2 does not apply** (*never add a config key before its gate is deployed*):
    **nothing fires on this interval.** There is no job, no timer, no gate. `read_email` hands the
    number to the agent that already called it. A scheduled version would have to wait on
    `[DB-0808-11]` — `fire_function` runs no gate stack, so a scheduled mail check could push at
    3am — and the template comment records that.
  - **Rejected: mirroring the key into `config/modules/email.yaml`.** Checking the files first
    showed that would reproduce a live failure sitting next to it — see the caldav note below.

## Closed 2026-08-10 — Research provenance

- ~~**[DB-0810-08] Research Agent fabricates its sources, and the Book cannot see it.**~~ —
  **closed, all three phases built, deployed and verified live** (`a36d8c2`, `e3904fd`,
  `6cb077b`, `924a66e`, `a3b43c5`).
  - **Config:** all five `SOURCES:` mandates removed from `research_agent.md` — the plan named
    four, line 62 carried a fifth that would have kept the fabrication path fully open.
    `synthesizer.md` now reads the provenance line; `coordinator.md` carries the general
    Logistics/Research boundary alongside the flights/TfL example.
  - **Python-authored provenance:** `_strip_model_sources()` removes any model-written block
    before `run_session_gemini_grounded` appends its own — `SOURCES (N retrieved): <urls>` or
    `[RETRIEVAL: NONE]` — generated from what the SDK reports. `web_search_queries` harvested
    per turn.
  - **`trace.py:289` fixed**, but *not* as the plan specified. `grounded` is now
    `bool(retrieved_sources)`, per-agent and tri-state. The plan's
    `sources or web_search_queries` was disproved by a live run: 6 searches, 0 sources scored
    *grounded* while the same response said `[RETRIEVAL: NONE]`. A `has_tool_calls()` fallback
    was also rejected — an agent calling `write_log` is active, not grounded.
  - **Guard:** `scripts/check_agent_tools.py` reports four classes against `register_tools()`.
    Acceptance test per the plan: flags `web_search` against the pre-fix file (exit 1), clean
    after (exit 0). A `PostToolUse` hook runs it automatically on agent/routing edits.
  - **Bundled** the `tools/flights.py` `delayed`-means-*later-than* fix, as instructed.
  - **Verified live:** mile-record query → 2 queries, 5 sources, one code-authored provenance
    line, zero stray blocks. Obscure query → `[RETRIEVAL: NONE]`, no invented citations.
  - *Does not close A7 check 10* — the 12-specialist audit is still unrun; the Fail known in
    advance is gone. Reasoning: `PROJECT_LOG.md` § 2026-08-10.

---

## Closed 2026-08-09 — by the workflow revamp itself

*Docs and scripts only; nothing deployed. Reasoning:
[`PROJECT_LOG.md`](PROJECT_LOG.md) § 2026-08-09 (dev-workflow revamp).*

- ~~**[DB-0809-01] The open count is inflated and `## Done` is empty.**~~ — **closed by
  construction.** All three sub-faults are gone rather than fixed: closed items now leave
  `DEV_BACKLOG.md` for this file, so the `- **✅`-counts-as-open trap has nothing to bite on;
  counting is section-scoped in `scripts/sync_dev_backlog.py` (`count_items()` → inbox/now/later)
  rather than partitioning on a `## Done` heading that may not exist; and the duplicate
  `DB-0805-01` was resolved when the travel-time half was found superseded by `[DB-0807-01]`'s
  build. Verified: reported counts match a hand count of each section exactly.
  *closed 2026-08-09 against scripts/sync_dev_backlog.py `count_items`/`_section` and the
  restructured DEV_BACKLOG.md*

- ~~**[DB-0808-13] `/archive`'s collision guard is still unwritten.**~~ — **built, as step 0 of
  the rewritten command**, not as the numbered step 4 the entry specified — the rewrite reduced
  six steps to four, so the guard became a precondition instead. `git status --short SESSION.md
  ROADMAP.md archive/PROJECT_LOG.md`, stop and ask if dirty. **Known limit found on its first
  run, filed as `[DB-0809-17]`:** it cannot tell another window's edits from the session's own.
  The entry's withdrawn "`Edit`-locked skill" premise stayed withdrawn — the file was edited
  freely throughout this session.
  *closed 2026-08-09 against `.claude/commands/archive.md` step 0*

- ~~**[DB-0808-15] Two parallel Claude Code windows treat shared status files as private
  state.**~~ — **closed for the status half; the git half survives as `[DB-0805-05]`.** The
  diagnosis in the entry was incomplete: the problem was never the code files (clusters already
  had disjoint manifests) but the *close-out*, where every window ran `/archive` and edited the
  same three shared files. Fix is the coordinator/worker split in `/backlog attack`: workers are
  forbidden shared state and `./deploy.sh`, and leave `archive/handoffs/YYYY-MM-DD-<slug>.md`;
  the coordinator runs `/archive` once, folds them in, and owns the single deploy. Incidents
  (1)–(5) and (8) — stale status, ID collision, duplicated `## Done` moves, stale count baseline
  — are addressed by that plus the grep-at-write-time ID rule. Incidents (6) and (7), one
  window's commit sweeping up another's uncommitted diff and the no-op commit race, are **not**
  addressed and stay open.
  *closed 2026-08-09 against `.claude/commands/backlog.md` § attack and `archive.md` step 0*

- **[DB-0805-05]** — **narrowed, still open.** Retitled to the git-collision half only; the
  shared-status-file half is covered above. Remains in `DEV_BACKLOG.md` → `## Later`.

---

*Original header follows.*

# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

- **[instruction change]** User reiterated existing check-in length instruction verbatim. Triggered repeated instruction protocol to flag that current check-ins are failing to adhere to the brevity rule.  
  `2026-08-09T09:06:43.932199Z`

- **[instruction change]** User has submitted the check-in rule multiple times in a row. The system must output strictly 'What  
  `2026-08-08T18:34:27.078188Z`

- **[instruction change]** Synthesizer is failing to adhere to the existing Interaction Preference for check-ins (max two sentences, name one urgent thing or ask what's on, no recaps). This preference needs to be enforced more strictly at the system/prompt level.  
  `2026-08-08T16:31:45.535165Z`

- **[instruction change]** User repeated the check-in brevity rule verbatim. It is already saved in Interaction Preferences but earlier responses failed to follow it. Need to ensure the system strictly enforces this preference over other dialogue generation.  
  `2026-08-08T12:19:24.143357Z`

- **[instruction change]** User re-stated the strict check-in rule ('never list or recap pending items') because the previous response violated the existing persona config by listing two time-sensitive items. The persona constraint is present but failed to override the generic routing/integration behavior.  
  `2026-08-07T09:13:05.841606Z`


- **[needs building]** System must proactively detect when a scheduled calendar event passes without occurring, and automatically prompt the user to reschedule it. Financial tasks (like payroll) must remain prominently surfaced in daily proactive checks until explicitly closed.  
  `2026-08-05T15:19:45.254683Z`
- **[agent wanted a tool it lacks]** `finance` attempted `search_memory` (query) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-05T15:21:45.223926Z`

- **[same rule in two places]** This preference may contradict a rule that already applies — one negates, the other does not, and whichever layer loads last wins. Class: brevity — how long a proactive session's opening should be. A universal rule of this class belongs in the scheduler layer. Preference: config/personas/mike.md:11 — For check-ins: Keep to two sentences at most. If exactly one thing genuinely needs attention, name it and stop. Otherwise just ask what's on. Never list or recap pending items, and never manufacture a topic. Candidate rule(s) it may restate: (0.90) [brevity] config/personas/mike/scheduler.yaml:41 — Check in briefly — two sentences at most. If exactly one thing genuinely needs attention right now, name it and stop. Otherwise just ask what's on. Never list or recap pending item (0.90) [brevity] config/templates/scheduler.yaml:34 — Check in briefly — two sentences at most. If exactly one thing genuinely needs attention right now, name it and stop. Otherwise just ask what's on. Never list or recap pending item (0.19) [brevity] config/personas/mike/scheduler.yaml:21 — Good morning. Open with whatever is most time-sensitive today — a commitment, an overdue follow-up, or an unresolved thread from recent context. Name it specifically rather than as … and 1 more Candidates are ranked by wording overlap, which is weak at this scale — the flagged preference is the reliable part, the partner is a starting point. If the preference says nothing the shared rule does not, delete it. If it is a genuine personal refinement, keep it and reword it so the difference is all it states.  
  `2026-08-05T04:30:19.777295Z`
*(nothing new — last triaged 2026-08-08)*

---

## Triaged out of Inbox — 2026-08-08

- **[instruction change] Enable proactive pre-departure travel checks** — *"autonomously look
  up flight status and relevant transit lines (e.g., DLR, Elizabeth line) before the user asks
  on travel days"* (`2026-08-05T07:02:45`). Became `[DB-0806-01]`; **fully delivered and closed
  2026-08-08** — see the Done section. Removed from the Inbox here rather than left sitting
  under a request that has been satisfied.

- ~~**Develop a stronger protocol for onboarding new contacts to the CRM or Google
  Contacts. Current handling resulted in misattributing the user's email to the
  contact and silent failures during retrieval.**~~ — **built 2026-08-08.** Went through
  a full detour first (Google Contacts OAuth, built then reversed same-day at Mike's
  challenge — see `[DB-0808-01]`) before landing on the direct fix: `tools/crm.py`'s
  `write_contact` had no validation against the user's own identity at all, which is the
  literal bug. Added in Python (not a prompt instruction, per the standing "being told is
  not being prevented" principle already applied to `write_agent_config`/`send_email`):
  refuses outright on an *exact* match to the user's own email/phone from `profile.yaml`;
  flags (via `difflib.SequenceMatcher`, threshold 0.80) and saves anyway on a *near*
  match, since a hard block would also refuse a legitimate similar-looking contact.
  Verified live: an exact match (`diamond.mike.mt@gmail.com` attributed to a new
  contact) is refused; a realistic transcription near-miss
  (`diamond.mic.mt@gmail.com`) is flagged with a warning but still saved; an unrelated
  contact saves silently with no false-positive noise.

  **Broader than the code check, per Mike's own follow-up:** most transcription errors
  land on details the tool has no way to validate at all — a misspelled third-party name,
  a garbled address, a transposed phone digit — since those aren't compared against
  anything. Added a standing instruction to `relationships.md`: read back every new name,
  email, address, handle, or phone number, not just the ones the code flags.

  **"Silent failures during retrieval" is not addressed by this entry** — that half
  named a `search_memory` JSON parse error (see `[DB-0803-03]`, still open, separate root
  cause) rather than a CRM read path; kept separate rather than folded in, since the two
  are unrelated bugs that happened to be filed in the same Inbox note.

  *filed 2026-08-06 (Inbox) · fixed 2026-08-08 against tools/crm.py and
  relationships.md, verified live*

---

## Triaged out of Inbox — 2026-08-05

Fourteen entries cleared. Nine were `TOOL_DENIED` warnings covering six distinct cases; each was
matched to the conversation it happened in before any decision was taken, because the denial
text alone says what was blocked and not what the agent was trying to do.

- ~~`logistics` → `read_agent_config`, `write_agent_config` (×4), `search_memory`,
  `write_archive`; `work_vocation` → `search_memory`; `finance` → `read_archive`~~ —
  **granted 2026-08-05, `9361537`.** Not a widening on request: `logistics.md:45` makes the
  config store mandatory, `:189` states the recurring-obligation inventory lives there because
  *"obligations are data rows, not scheduled jobs"*, and `:187` assigns `write_archive` four
  named lists. **`write_schedule` was already granted 2026-08-03 (`2f74cd2`) and did not stop
  the denials** — it is a different mechanism for a different thing, exactly as `:189` says.
  Corroborated on disk: `sarah_chen`'s `logistics.json` already held `recurring_obligations`,
  written through warn mode.

- ~~`physical_health` → `read_agent_config`~~ — **already granted 2026-08-04 (`b3229ff`)**;
  the warn-mode entry predated the grant. Stale on arrival.

- **[DB-0805-01] `physical_health` can now write the profile its own safety flag reads.**
  `write_agent_config` was granted 2026-08-05 (`9361537`), reversing the 2026-08-04 hold, with
  `medication_profile` guarded in Python (`_GUARDED_KEYS`,
  [tools/agent_config.py](tools/agent_config.py)). The guard is narrow by design and **only
  covers the one key**. `physical_health.md:106` requires `MEDICATION_MISSED_CRITICAL` to
  classify from stored data and *"never from the agent's judgment"* — if any other flag grows a
  similar dependency, its key needs adding to the same set. **B2 should decide whether guarded
  keys are the right mechanism or whether the confirmation gate supersedes them.**
  *filed 2026-08-05 by dev session (Claude Code) · found while applying the grant decisions ·
  origin SEQ — · verified 2026-08-05 against tools/agent_config.py*

- **[DB-0805-02] Email approval prompt does not render in the app, and no live Google Contacts
  read exists.** Two user reports, 2026-08-04 12:42Z and 12:49Z. **Owned by the CalDAV/email
  window** — filed here for completeness, not for this session to work.
  *filed 2026-08-04 by Mike via Synthesizer · origin SEQ 016/017 · not verified — other window's
  active work*

- **[DB-0803-01] Text doubling / input cut off mid-sentence in the app.** Reported 2026-08-03
  17:12Z. The calendar half of the same report is **done** (CalDAV live 2026-08-03, `cfcd212`).
  The text-doubling half is untouched and unverified — `static/index.html`. Note SEQ 004 on
  2026-08-04 shows the Synthesizer asking whether the features being tested were aimed at *"that
  text doubling bug"*, so it was still live then.
  *filed 2026-08-03 by Mike via Synthesizer · origin SEQ 012 · not verified this session*

---

## Triaged out of Inbox — 2026-08-04

- ~~**Remove the voice activation toggle from the app** (×2 — `2026-08-03T17:16Z`,
  `2026-08-04T07:57Z`)~~ — **superseded, closed 2026-08-04 by Mike's decision** (*"Voice is
  completed as far as I can see. Remove any requests for it. I can always rerequest."*).

  Both requests were about voice output cutting into message input. What shipped addresses
  the cause rather than removing the feature: a persisted toggle **defaulting to off**
  (`fe0d688`), so behaviour matches "removed" unless switched on, plus the fix that actually
  mattered (`8e5c47e`) — speech is now blocked at every point playback could begin, including
  after the `/tts` await and after `decodeAudioData`. The first attempt only *stopped* audio
  already playing, which did not fix the reported bug at all: the delay complained about **is**
  the `/tts` await, so a reply could still start speaking mid-recording.

- ~~`physical_health` attempted `read_agent_config` (×3 warn-mode entries)~~ — **granted
  2026-08-04**, `b3229ff`, in both `routing_cloud.yaml` and `routing.yaml`. Not a judgement call:
  `physical_health.md:106` requires `MEDICATION_MISSED_CRITICAL` to be classified from the stored
  medication profile and *"never from the agent's judgment"*, so without the read grant the flag
  was structurally unfireable. **Not yet deployed** — see the deploy-blocked item below.

- ~~**`physical_health` attempted `write_agent_config` — still open, deliberately.**~~ —
  **settled 2026-08-05, `9361537`.** Granted, with `medication_profile` guarded in Python rather
  than the whole tool withheld. The blanket denial was costing the agent an ordinary config store
  that every other specialist has, while the thing it protected — that
  `MEDICATION_MISSED_CRITICAL` must classify from a profile the agent did not author — is
  preserved exactly by the narrow guard. See **[DB-0805-01]** for the residual concern.
  The `logistics` and `finance` entries this one pointed at were resolved in the same pass.

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. **The `config/agents/*.md` freeze was lifted 2026-08-03 (`ae252ab`)** — these are now directly editable.

- ~~**`synthesizer.md:355` promises a capability that does not exist.**~~ — **stale, closed
  2026-08-05. Already fixed by the 2026-08-03 Phase 4 scheduler-grants session; this entry was
  never crossed off.** Checked against current source: `synthesizer.md:408` documents
  `write_config` scoped to exactly `{prime_directive.md, mission.md}`, matching
  `tools/config_writer.py:16`'s `ALLOWED_FILES` — no mention of `scheduler.yaml` anywhere near
  it. Recurring proactive sessions go through the separate, already-correct
  `write_schedule`/`list_schedules`/`delete_schedule` tools (`synthesizer.md:406`,
  `tools/schedule.py:85`), which write `data/personas/{p}/schedules.yaml` — deliberately not the
  gitignored, hand-copied `config/modules/scheduler.yaml`.
  *Original entry filed 2026-08-02 · verified stale 2026-08-05 against synthesizer.md and
  tools/config_writer.py/schedule.py*

---

## Open — needs building

Capabilities that do not exist yet.

### Surfaced 2026-08-08

- **[DB-0808-17] The A4 clinical hard-fails have never been run on Flash-Lite, which is the model
  serving most clinical turns.** `quick_override` sends `complexity: quick` to
  `gemini-3.1-flash-lite` for *every* agent in cloud mode, including `mental_wellbeing` and
  `physical_health`, whose `routing_cloud.yaml` comments read "clinical flags; never downgrade"
  and "same safety rationale as MW". Measured Aug 1–8 on the `mike` persona: **mental_wellbeing 43
  Flash-Lite calls vs 5 Pro; physical_health 58 vs 6.** The guard that was meant to prevent this
  keys on `agent_cfg.get("local")` ([core/router.py:81](core/router.py#L81)) — and in
  `routing_cloud.yaml` no agent carries `local: true`, so it is inert by construction. That is
  *correct* under the 2026-06-18 ZDR amendment; the side effect is that sensitivity no longer
  blocks the quick tier. **User decision 2026-08-08: routing stays as is** — MW/PH remain on Pro
  when deep is called for, and the quick tier is accepted. What is *not* settled is the test gap:
  `tests/run_a4_safety.py` has only ever been run on the deep path, so the clinical flags are
  unverified on the model that actually answers most clinical turns. Per ROADMAP.md's own lesson,
  "a safety flag that is never exercised by a test is not known to work." Fix: add a
  `--complexity quick` (or explicit Flash-Lite `--model`) run to the A4 suite and record the
  result. Note this also bears on **A7 check 8**, which as written requires sensitive agents to
  stay local regardless of complexity — that check cannot pass on the cloud path as worded, and
  needs either a re-wording or an explicit dormancy note like the one §0 clause 8 already carries.
  *filed 2026-08-08 by dev session (billing/spend-accounting investigation) · origin: per-agent
  trace measurement while reconciling the $35 GCP bill · relates to ROADMAP.md § A7 check 8,
  § 0 clause 8*

- **[DB-0808-16] The `injection` suite needs an ordinary-life persona, and that requirement now
  lives only inside a closed entry.** `tests/run_b1_redteam.py --suite injection` is
  persona-sensitive in a way the other three suites are not. Its first run against `sarah_chen`
  returned three *inconclusive* scenarios: the pipeline never called `read_email` at all, because
  that persona carries an active clinical thread which the Synthesizer correctly triaged over
  "read my inbox". Good behaviour, useless probe — and **without the "fixture inbox was actually
  read" assertion it would have scored 3/3 PASS on a pipeline that never saw the payload.** It
  passed on `danny_park`. This matters for the **remaining B1b rows** (calendar title, web page,
  CardDAV), which are still open and gated on Track E: whoever builds them will pick a persona,
  and picking a clinically-loaded one silently produces a green result that means nothing.
  Filing it because the note currently survives only inside the closed injection-probe entry in
  `## Done`, which is not where anyone starting B1b will look. Fix is a line in the suite's
  docstring plus a runtime guard that fails loudly when `read_email` was never called.
  *filed 2026-08-08 by dev session (backlog-attack cluster B) during /archive step 6 · origin:
  the injection-probe entry now in `## Done` · relates to ROADMAP.md § B1b*

- **[DB-0808-15] Two parallel Claude Code windows treat shared status files as private state —
  no convention exists for it, and it cost rework three times on 2026-08-08.** Not a bug and not
  urgent; filing it because it currently exists only in session narrative, which is how things
  age out. The three incidents, all in one hour, all between two `/backlog-attack` cluster
  windows: (1) one window reported "built, not deployed" and wrote a deploy handoff prompt for
  the other, which had **already deployed** (`7c70cd9`) — four files stating the stale status had
  to be corrected minutes after the archive pass wrote them; (2) `[DB-0808-06]` was drafted in
  one window and claimed by the other before it was written, so **backlog IDs are not reservable
  while two windows are open**; (3) three entries were marked complete in one window and then
  moved to `## Done` by the other (`2195fa9`) — duplicated effort, no damage.
  **Rejected as too heavy for the observed cost:** serialising the windows (the parallelism
  worked — two independent clusters, disjoint file regions, both shipped), and any lock-file or
  merge protocol. **The cheap version, which is what this item proposes:** a short convention
  note in `CLAUDE.md` — re-read `DEV_BACKLOG.md` / `SESSION.md` / `git log` immediately before
  acting on their contents rather than trusting a status read earlier in the session, take the
  next free ID at the moment of writing rather than reserving one, and check `git log --oneline`
  before reporting any deploy status. Whether that belongs in `CLAUDE.md` or in `/archive` and
  `/backlog` themselves is the open question. Reasoning: `archive/PROJECT_LOG.md` § 2026-08-08
  (output filter / context repair / injection probe), postscript.
  **Two further incidents from cluster B, same root, added 2026-08-08:** (4) the `SessionStart`
  hook reported **45 open**; after moving seven items *out* of the Open sections the sync
  reported **48**, which reads as a regression and is not one — the real move was **53 → 48**,
  and the 45 was a stale baseline taken before the other window filed its entries. Any reported
  count is a snapshot of an unknown moment while two windows edit the file. Caught only by
  diffing against `git show HEAD:DEV_BACKLOG.md` instead of trusting the delta. (5) both windows
  independently minted **`[DB-0808-07]`**; the collision was found by grep at close and cluster
  B's was renumbered `[DB-0808-14]`. A cheap mitigation for both: derive the next ID from a grep
  of the file at write time, and quote counts as a before/after diff rather than a bare number.
  **Three more from the pollen/travel session, same day — including the first that risked actual
  loss:** (6) **another window's commit swept up this session's entire uncommitted code diff.**
  `7c70cd9` captured `tools/pollen.py`, `tools/travel_watch.py`, `core/scheduler.py`,
  `core/orchestrator.py`, both routing files and the static-plan edit — none of them its own
  work — so that code now sits in `origin/main` under a message describing unrelated changes.
  Nothing was lost (every file verified against `HEAD` afterwards) but the commit history now
  misattributes a session's work, and a `git checkout` or `git stash` in that window instead of a
  commit would have destroyed it outright. This is a strictly worse class than incidents 1–5: it
  is not rework, it is another session's uncommitted work being taken. (7) **`DEV_BACKLOG.md` was
  committed by the other window in the gap between this one's `git add` and `git commit`** — the
  commit became a silent no-op ("no changes added to commit") while appearing to run normally;
  the changes were still in the worktree and had to be re-committed. **A no-op commit is the
  quiet failure here** — nothing errors, and a session that didn't check `git log` afterwards
  would believe it had committed. (8) `[DB-0808-06]` **and** `[DB-0808-14]` were both claimed by
  other windows between draft and write in a single session, i.e. incident (2) twice more,
  confirming ID collision is routine rather than unlucky. Note the additional detail that scoping
  a commit with `git add <specific files>` does **not** protect against (6) — the sweeping window
  is the one committing, and this window's staging discipline is irrelevant to it.
  *filed 2026-08-08 by dev session (backlog-attack cluster A), from three observed incidents in
  the same session · extended by cluster B with two more (stale count baseline, ID collision) ·
  extended again by the pollen/travel session with three more, one involving another window
  committing this session's uncommitted code · no code change proposed yet*

- **[DB-0808-11] `fire_function` runs no gate stack — `days`, `respect_quiet_hours` and the
  activity gate are silently ignored for every function job.** All three checks live inside
  `fire_session` (`core/scheduler.py`); `fire_function` has never had them. This did not
  matter while every function job was silent (`ambient_refresh`, `daily_rule_audit`,
  `daily_calendar_dedup_audit` all set `notification: false`), but `fire_function` gained a
  notification path on 2026-08-08 and the gap is now reachable: **an `interval_minutes`
  function job with `notification: push` would push at 3am and nothing would stop it.**
  Worked around rather than fixed — `daily_travel_check` is pinned to a fixed daytime hour
  (06:45) specifically because of this, with the reason recorded at the config site. Fix
  properly by extracting the gate stack out of `fire_session` and calling it from both, then
  the interval form becomes safe. Note the standing precedent for why this matters: a config
  key shipped ahead of its gate once meant a check-in every thirty minutes on a live user.
  *filed 2026-08-08 by dev session (Claude Code) · found while wiring the proactive travel
  check · worked around, not fixed*

- **[DB-0808-13] `/archive`'s collision guard (`[DB-0805-05]`'s mitigation) is still unwritten —
  but it is NOT blocked. The "`Edit`-locked skill" premise is withdrawn.**
  ~~`.claude/commands/archive.md` is `Edit`-locked while `/archive` is a loaded skill.~~
  **Disproved 2026-08-09:** `archive.md` was edited five times in one session (`a86dd37`), and
  the recurring "user cancelled the edit" has a confirmed mechanism in the extension log —
  **⌘S accepts a diff tab, closing it rejects** (`files.autoSave` is off), with several Claude
  sessions sharing one editor surface. Four blocked attempts on 08-08 are explained by that,
  with no lock required. The 08-08 probe (a new command file editable before registration,
  not after) is not re-derivable from here and may have been two cancels either side of a
  coincidence — **do not re-file the lock claim without reproducing it against the log.**
  Whoever picks this up: the work is ordinary, just do it. **The work itself is fully
  specified and agreed:** a new numbered step 4, "check and stop if dirty",
  running `git status --short SESSION.md ROADMAP.md` before the two rewrite steps and stopping
  to ask if either is dirty, with steps 4/5/6 renumbering to 5/6/7 and the "Steps 4 and 5 are
  two different documents" warning updating to "Steps 5 and 6". Do it in a session that has
  not loaded `/archive`, or via a non-`Edit` path. Sharpening the irony: `archive.md` had 41
  insertions of *uncommitted* changes from another window sitting in the tree at the time —
  the exact collision the guard is for.
  *filed 2026-08-08 by dev session (Claude Code) · ~~blocked by tooling, not by the work~~ ·
  **unblocked 2026-08-09** — premise disproved against `.claude/commands/archive.md` and the
  VS Code extension log · `[DB-0805-05]` stays open until the guard actually lands*

- **[DB-0808-06] Administrative-close mechanism for tier-2 clinical threads.** The clinical
  thread lifecycle shipped 2026-08-08 (`tools/context_tracker.py`) deliberately refuses to let
  a `CLINICAL_CONCERN` be `resolved` from a session — a reassuring reply from the user must not
  close a suicidal-ideation flag. The `resolved` status exists and is pre-wired; **nothing can
  legitimately set it.** So every tier-2 thread is permanent in practice. That is the correct
  failure direction and was the explicit user decision, but it needs a real closure path
  eventually — most likely tied to the next-of-kin / clinician escalation system, which does not
  exist (there is no third-party contact channel anywhere in the codebase; `tools/wishes.py` is
  write-only until Phase 6). Not urgent. **Do not "fix" it by relaxing the refusal.**

- **[DB-0808-14] `_thread_tier()` cannot tell a psychiatric medication from a cardiac one.**
  The 2026-08-08 tier split keys off the `CLINICAL_CONCERN` prefix, so a
  `MEDICATION_MISSED_CRITICAL` is tier 1 (user-resolvable) whether the missed dose is a statin
  or an anti-psychotic. The user's stated distinction was exactly this pair. Fix is a
  `psychiatric: true` marker on entries in `physical_health`'s stored `medication_profile`, read
  by `_thread_tier()`. Note `medication_profile` is in `_GUARDED_KEYS` (`tools/agent_config.py`)
  — the agent cannot write it, which is the point; it is seeded by the user or the A4 fixture.

- **[DB-0808-08] STT accuracy is unverified on real audio.** The 2026-08-08 benchmark
  (`tests/stt_bench_report_2026-08-08_vm.md`) ruled out `small.en` **on latency** — RTF 2.23 on
  the VM's 2 vCPUs, which on a single-worker pool is a queue, not a slowdown. That verdict is
  solid. The **accuracy** half is not: the fixtures are edge-tts synthesized speech with no
  noise, accent, clipping or room tone — the regime where `base.en` and `small.en` are most
  alike. So "no accuracy benefit" is established for clean dictation only. Needs a handful of
  real phone recordings with hand-written references. Cheap to collect during ordinary use.
  Related: revisit `small.en` at D1 (dedicated hardware changes the RTF arithmetic entirely),
  and consider a second STT worker if concurrent voice use ever becomes real.

- **[DB-0808-05] `filter_output()` still has no view of the user's own turn — the
  Exchange 027 false positive survives the regex/semantic upgrade.** Not a gap in the
  matching, and deliberately not fixed alongside it. When the user types a tool name
  themselves ("I'm frustrated that `write_config` didn't save my preferences"), the
  Synthesizer's reply quotes it back and the filter suppresses the whole response —
  the user gets the canned fallback instead of an answer to a complaint about the
  system, which is the exact moment they least want a deflection. Observed live
  2026-06-26 (Exchange 027) and pinned as `FILTER-EXCH027` in
  `tests/run_b1_redteam.py`, where it is informational and does not gate.
  **Why it was not folded into the 2026-08-08 upgrade:** the fix is not a better
  regex, it is passing the user's own message into `filter_output()` so a term the
  user introduced can be exempted — a signature change across three call sites
  (`core/orchestrator.py` ~2506, ~2721, ~2768) plus a decision about how far the
  exemption reaches (that turn only? the whole session?). The security argument
  against a blanket exemption is in the function's docstring and still holds: a
  direct probing question must not be able to disable its own backstop. So this
  needs a scoped rule — exempt only the specific term the user typed, only in the
  turn that follows — not a flag. Worth doing: the current behaviour makes the
  system worst at discussing itself precisely when it has misbehaved.

- **[DB-0808-04] Real-time GPS + proactive area-scanning — raised, not scoped, not
  started.** Mike's own framing, from the pre-departure travel-check conversation: with
  real-time location, an agent could proactively notice a gap (no lunch on the calendar,
  30 minutes to the user's normal lunch time) and search the area for a matching
  restaurant against the user's known preferences (nutrition, cuisine, price, atmosphere)
  — "scan the area for opportunities" as a general pattern, not just a lunch case.
  Deliberately not built or scoped this session — it was flagged mid-conversation as
  needing its own design pass (privacy tier for continuous location data, which app/OS
  layer supplies it, how "opportunity scanning" bounds itself so it doesn't turn into
  noise) rather than being bolted onto the travel-tools work in progress. Directly
  depends on Google Places API (`[DB-0807-02]`), itself blocked on the same missing
  location signal. **Recorded here specifically so it doesn't only exist in session
  narrative** — this is the same failure mode that nearly lost the unsurfaced-opportunity
  instrumentation item.
  *filed 2026-08-08 by dev session (Claude Code), from Mike's own framing 2026-08-07 ·
  not scoped, not started*

### Surfaced 2026-08-06

- **[DB-0807-01] `location_transition_flags` stub filled in — real routed travel time,
  not just a raw-gap flag. Built 2026-08-07, corrected same day.** [tools/routing.py](tools/routing.py),
  `get_travel_time(origin, destination, mode, arrive_by)` — provider-agnostic interface
  (name, schema, and output shape carry no city/vendor specifics). **First version wired
  TfL as the default backend for London transit/walking; this was backwards and Mike
  corrected it same-day: Google Maps Routes API is the default router everywhere,
  including inside London, for every mode (`transit`/`walking`/`driving`/`cycling`).**
  Citymapper's developer API is fully discontinued (since 2023-06-23) — not viable, ruled
  out with a direct check rather than assumed. Google Maps enables on the **existing**
  `metatron-ai-499810` GCP project already used for Vertex AI (`gcloud services enable
  routes.googleapis.com` + a key restricted to `routes.googleapis.com` only via
  `--api-target`, so a leak can't spend on other Maps SKUs) — no new vendor account.
  Verified live across all four modes and both success/failure paths (a real
  San-Francisco-to-Palo-Alto driving route, an unresolvable-address error, an
  unsupported-mode error) before calling it done.

  **TfL's role is narrower and separate, not a routing backend at all:**
  `get_tfl_status` (line/route disruption status, unchanged) plus a new
  `get_regional_transit_info(city)` ([tools/regional_transit.py](tools/regional_transit.py))
  reading a shared, non-persona-scoped library
  ([config/modules/regional_transit.yaml](config/modules/regional_transit.yaml)) that
  names which cities have a secondary cross-check tool and how to use it — today just
  London → `get_tfl_status`, for disruption awareness and longer-range transit planning,
  explicitly never as the default router. **Resolved per-query against whatever city is
  actually relevant right now** (a calendar event's location, something the user said),
  never cached against a persona's home city — the design question that surfaced this:
  a NYC-based persona visiting London needs the same London entry a resident would get,
  which a static "home region" cache would silently miss. Verified this costs nothing
  extra in the common case: the lookup is a local file read either way, no network, no
  API, no billing — caching would only have bought the same wrong-while-traveling bug for
  zero performance gain.

  **Wired into `check_calendar_conflicts`** ([tools/scheduling.py](tools/scheduling.py)):
  `location_transition_flags` now calls `get_travel_time` for every tight-gap candidate
  and adds `travel_time_minutes` + `feasible` (or `travel_time_unavailable` with a reason)
  to the existing flag — the raw `gap_minutes` flag is never dropped just because routing
  failed. This directly answers Mike's "there should already be an instruction for
  Logistics to run the route and enter estimated time" question — there wasn't; there is
  now, for the case where both calendar events already have locations set.

  *filed and built 2026-08-07 by dev session (Claude Code) · default-backend priority
  corrected same day per Mike's direction · regional-tool architecture question (traveling
  personas) resolved same day via the shared-library + per-query-resolution design above*

- **[DB-0808-01] Google Contacts (People API) — built 2026-08-07, reversed 2026-08-08 at
  Mike's challenge, replaced by a simpler local fix.** The original need was two entries
  above ("misattributing the user's email to the contact") and `[DB-0805-02]` ("no live
  Google Contacts read exists"). Built a full OAuth 2.0 integration for it: Desktop-type
  client, `scripts/google_contacts_authorize.py` (local-server consent flow), `tools/google_contacts.py`
  (`read_google_contacts`, `contacts.readonly` scope), registered and granted to
  `relationships`. Along the way, verified directly against Google's own support page
  (not a paraphrase) that the app's Testing publishing status means consent — and the
  refresh token — **expires 7 days after granting**, since `contacts.readonly` is a
  "sensitive" scope; moving to Production removes this but needs 3–5 business days of
  Google review plus a hosted privacy policy.

  **Mike's challenge, before spending that review effort: does this need a third party at
  all?** Checked `tools/crm.py`'s `write_contact` directly — it has no validation against
  the user's own identity, which is the literal, actual bug (nothing stops a captured
  email from being silently attributed to a contact even when it matches the user's own
  address). That is a local, zero-dependency fix, not a reason to add OAuth. And the
  "bring in contacts I already have" value — the actual reason Google Contacts looked
  attractive — has a portable answer that isn't Google-specific: vCard (`.vcf`) is the
  real interchange standard (Google, Apple, and Outlook all export to it), and Python's
  `vobject` library (verified live on PyPI, v0.9.9) parses it directly, no OAuth, no
  token-freshness problem, works identically for a non-Google persona.

  **Reversed same day:** `read_google_contacts` unregistered from
  [core/orchestrator.py](core/orchestrator.py) (import, schema, handler all removed —
  the tool is now structurally undispatchable, not just ungranted) and removed from
  `relationships`' `allowed_tools` in both routing files.
  `people.googleapis.com` disabled on the GCP project (`gcloud services disable`).
  **Deliberately left in place, dormant, not deleted:** `tools/google_contacts.py`,
  `scripts/google_contacts_authorize.py`, the `GOOGLE_OAUTH_CLIENT_ID`/`_SECRET` pair in
  `.env`, and the OAuth client/consent-screen configuration in Cloud Console (no CLI path
  to delete that last one anyway) — in case this gets revisited, but none of it is wired
  to anything live. **Replaced by:** a `write_contact` guardrail against
  `profile.yaml`'s own contact fields, and a `vobject`-based vCard import tool — see the
  entries this produced, filed the same session.

  *filed and built 2026-08-07 · reversed 2026-08-08 at Mike's direction, root cause
  (missing local validation) diagnosed and portable alternative (vCard) verified before
  the reversal, not just after*

- **[DB-0808-02] vCard (.vcf) contact import — built 2026-08-08.**
  [scripts/import_vcard_contacts.py](scripts/import_vcard_contacts.py), using `vobject`
  (verified live on PyPI, v0.9.9, added to `requirements.txt` along with its transitive
  deps `python-dateutil`/`pytz`/`six`). The portable replacement for what Google Contacts
  OAuth was actually for — Google, Apple, and Outlook all export to the same `.vcf`
  standard, so this works regardless of which ecosystem the contacts came from, with no
  OAuth and nothing to keep fresh. Every write goes through `write_contact`, so
  `[DB-0808-01]`'s guardrail applies automatically — verified live with a realistic test
  file: a normal contact imports cleanly, a card matching the user's own identity
  (common — "My Contacts" exports often include yourself) is refused and reported as
  such rather than silently imported, and a near-miss transcription-style email is
  flagged but still imported. Dedup by email confirmed rerun-safe: a second import of
  the same file skips everything already in the CRM rather than duplicating or
  overwriting a contact that may have been refined further in conversation since.
  *filed and built 2026-08-08 · verified live including refusal, flag, and dedup paths*

- **[DB-0808-03] `write_profile` now gates *changes* to an already-set email, phone, or
  address behind the confirm mechanism — built 2026-08-08, at Mike's direction.** These
  are the highest-consequence fields in the profile store (a wrong one misdirects real
  communication) and the ones voice transcription gets wrong most often. First-time
  capture of any field, including contact fields, still writes immediately — gating that
  too would just be friction on the common case, and `synthesizer.md`'s existing
  "confirm at capture" clause (say back what was captured) already covers it. *Changing*
  a value already on file now returns `PENDING_CONFIRMATION` (same mechanism as
  `send_email`/`write_config`) instead of silently overwriting. Re-writing the identical
  value is treated as a no-op, not a change — doesn't trigger the gate. Verified live:
  first capture writes immediately; an overwrite attempt returns the pending token;
  approving and retrying with the token completes the change; writing the same value
  twice never gates. `synthesizer.md` and the tool schema both updated to describe the
  new two-step flow for contact-field corrections specifically.
  *filed and built 2026-08-08 · verified live across all four paths*

- **[DB-0807-02] Two more Google APIs researched and noted where they'd plug in — Pollen now
  BUILT (2026-08-08), Places still open.** Surfaced while answering "any other Google APIs
  worth onboarding." The item stays open for Places only; the Pollen half is closed below.

  - **Google Places API** — Nearby/Text Search for restaurant/venue discovery (name,
    cuisine, rating, price level). Noted in `logistics.md` (Enhancement Backlog, serves
    its own `COORDINATION_OPPORTUNITY` concept) and `recreation_hobbies.md` (Enhancement
    Backlog, grounds the `write_archive` places/venues list in real current options
    instead of only what the user has already mentioned). Same GCP project, per-SKU free
    allowance, tiered pricing by requested fields. **Blocked on a location signal that
    doesn't exist yet** — no GPS capability in the system (see the pre-existing note on
    real-time GPS from the lunch-recommendation conversation, 2026-08-07); "near a named
    address/event" queries don't have that dependency and could ship sooner than "near
    the user right now."
  - ~~**Google Pollen API**~~ — **BUILT 2026-08-08, `7c70cd9`.**
    [tools/pollen.py](tools/pollen.py), `get_pollen_forecast(location, days)` — 1–5 day
    forecast by grass/tree/weed on the 0–5 Universal Pollen Index, with health
    recommendations. Registered in `register_tools()` and granted to `research_agent` in
    both routing files, which completes the chain `coordinator.md` already described
    ("sore throat" → Physical Health → Research for "pollen?" → Logistics for medicine):
    the instruction-level routing was written and waiting, and only the data source was
    missing. Kept distinct from `tools/ambient.py`'s Open-Meteo air-quality call as
    predicted — different exposure, different time shape (forecast vs. current), both
    coexist and neither substitutes for the other. Location comes from the same wttr.in
    geocode air quality already uses, so **this was never actually blocked on the missing
    GPS signal** that blocks Places — a named city is enough.
    **Verified live 2026-08-08** against real London data (weed Moderate/in season, grass and
    tree out) once `GOOGLE_POLLEN_API_KEY` was created and loaded — see `[DB-0808-12]` in Done.

  *filed 2026-08-07 by dev session (Claude Code) · noted in logistics.md,
  recreation_hobbies.md, research_agent.md · Pollen built 2026-08-08 · Places still
  blocked on a location signal*

- **[DB-0806-02] Level 3 web access — rendered-read tool scoped, not built; interactive
  Level 3 explicitly still not started.** Full scoping document:
  [archive/plans/level3_web_actions_scope_2026-08-06.md](archive/plans/level3_web_actions_scope_2026-08-06.md).
  Split the "give Metatron a browser" ask into two capabilities of very different risk:
  a **rendered-read** tool (`fetch_rendered(url)`, Playwright/headless Chromium, read-only,
  never clicks/types/submits — proposed for pages `fetch_url` can't handle, like the
  flight-status SPAs above) versus **interactive Level 3** (click/type/submit/login),
  which stays exactly where the 2026-08-04 outward-actions scoping left it: gated on a
  credential store that doesn't exist. Recommendation: build the rendered-read half —
  same trust boundary as `fetch_url`, no new action surface — check VM memory headroom
  before installing Chromium's dependency set. **Not built this session** — scoping only,
  per the same "propose, don't build without a decision" discipline as the 2026-08-04
  document it mirrors.
  *filed 2026-08-06 by dev session (Claude Code) · scoping only, not built*

### Surfaced 2026-08-05

- **[DB-0805-01] Real travel-time computation + auto-inserted travel block — deferred follow-on
  from the calendar conflict-detection build.** That build (`tools/scheduling.py`,
  `check_calendar_conflicts`) ships a location-transition **stub**: it flags when two adjacent
  same-day events have different non-empty locations and a gap under 30 minutes, but computes no
  actual travel time. Real travel time needs the Google Maps Distance Matrix/Directions API —
  `fetch_url` cannot do this reliably (no JS execution, and Maps' directions UI is JS-heavy) — which
  means a new credentialed GCP service (API key, billing enabled on that API specifically) that
  doesn't exist yet. **Two decisions already made when this was scoped, carry them into the
  follow-on rather than re-deciding:** (1) ships separately from the conflict-detection build, not
  folded in — it's its own credential/billing/sync-vs-async design, not an extension of a
  self-contained hygiene fix; (2) when built, a computed travel block is **surfaced for
  confirmation before insertion**, never auto-created silently — matches the existing
  `PENDING_CONFIRMATION` pattern for every other unrequested Logistics write. Also undecided and
  worth settling before starting: does Logistics call the Maps API synchronously while handling a
  scheduling request (adds a network round-trip mid-write, a new failure mode) or as an async
  follow-up after the event is created?
  *filed 2026-08-05 by Mike via dev session (Claude Code) · scoped, not started*

### Surfaced 2026-08-04 (evening)

- **[DB-0804-02] Track B security hardening (B1–B4) scoped, not started.** **Superseded in part
  2026-08-04 evening: B1a is now done, not just scoped** — see the B1a completion entry above
  (`tests/security_redteam_2026-08-04.md`, 75/75 PASS). **Also superseded: the `research_agent`
  `allowed_tools` line below was already stale when this was filed** — see the closed entry
  further down this file; it shipped 2026-08-04 10:55Z, before this scoping entry was even
  written. **What's still live from this entry:** the B2 remainder items other than
  `research_agent`, all of B4, and all of Wave 2 (B1b/B3). Original text preserved below for the
  reasoning trail, not because the plan/status lines in it are still accurate.
  **Wave 1 — ready
  now, no dependency on integration count:** B1a (direct-injection red-team suite, 9 categories,
  live against Coordinator/Synthesizer); B2 remainder (~~`research_agent` missing `allowed_tools`~~
  — extend the existing `POST /confirm` gate to
  `write_agent_config`/`write_config`; formalize confused-deputy enforcement + a regression
  test; ~~upgrade `filter_output()` from substring to regex/semantic matching~~ **— done
  2026-08-08, built and tested, ⚠ not yet deployed; see the standalone entry under
  "Surfaced 2026-08-08" for what it now catches and what it deliberately does not**; confirm
  `run_model_conference` is scoped head-layer-only); B4 (5 degradation paths — specialist
  failure mid-pipeline, Ollama-unavailable fail-closed message, context-tracker fallback,
  retry-with-backoff, max-chain-depth handling, partial-fan-out threshold — plus 2
  deliberate-failure tests). ≈4.5–5.5 sessions. **Wave 2 — gated on Track E reaching
  feature-complete for this phase:** B1b (indirect-injection tests — email/calendar/web/contact
  sources — spot-checked per integration as it ships, one consolidated pass once integrations
  settle) + B3 (baseline doc at `archive/security/security_baseline_*.md`, to fold in a new
  recurring security-review protocol: event-triggered per-integration spot-check + a
  quarterly/per-phase health-check re-run of B1a + B2's cross-agent exfiltration probes).
  **Also found while scoping:** `SESSION.md` previously stated PoLP tool permissions were "in
  warn mode" — the code shows the `allowed_tools` whitelist is already enforced; corrected in
  `SESSION.md` this session. Full detail:
  [archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](archive/sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).
  *filed 2026-08-04 by Mike via dev session (Claude Code) · scoping only, not verified by
  execution*

### Surfaced 2026-08-04

- **`ROADMAP.md` Track D is ~14 KB of a 47 KB file that loads on every `/metatron-code`, and parts of it have shipped.** D2 named cost analysis and model validation; the spend guard, rate limiter and measured token economics all landed 2026-08-02. Trimming it would take the cold-start load from ~26k to roughly ~22k. **Deliberately not done 2026-08-04:** a parallel window was committing to that file the same day, and trimming by line range is how the first pass silently carried completed item A6 into the abridged copy. **If picked up: go item-by-item against `SESSION.md` and `archive/PROJECT_LOG.md`, never by line range**, and check no window is mid-edit. Better done by whoever is actually working Track D than by a token-reduction pass. *Deferred from the context-file second pass, `a5ba388`.*


- ~~**⚠ `deploy.sh`'s preflight guard checks the wrong machine**~~ — **NOT A BUG. Withdrawn 2026-08-04 after checking the file.** Left in place rather than deleted, because the reasoning below is plausible and someone will re-derive it.

  **The guard runs on the VM.** `deploy.sh:40` opens `bash -s <<'REMOTE'` and the heredoc closes at line 103; line 42 is `cd ~/multi-model-mcp`; the guard is line 54 — inside, executing in the remote shell, greping the VM's `.env`. The heredoc is quoted, so nothing expands locally. (A `grep` for the check appears to match twice; the second, ~line 67, is the remediation command *echoed inside the abort text*, not a second test.)

  **What was actually observed:** `git push origin main` is **line 30 — before the SSH block**. A push happening is not evidence the guard passed. On 2026-08-04 the SSH failed on the outage, so the guard was never *reached* rather than bypassed. Confirmed the other way too: once `METATRON_AUTH_PASSWORD` was appended to the VM's `.env`, the same script deployed `8e5c47e` cleanly and its HEAD assertion verified.

  **Verify before re-filing** (not by reading — that is how this was got wrong twice): `awk` the line numbers of `<<'REMOTE'`, `^REMOTE$` and the guard, and check the guard falls between them.

  *Original entry, preserved:* the guard reads the Mac's `.env` while its message says the VM's; the Mac has the variable and the VM did not; therefore it passes on the machine you deploy from, always.

  **This is not theoretical — it happened on 2026-08-04.** A deploy passed the guard, pushed to GitHub, and reached the SSH step; **only an unrelated 4-hour VM outage stopped the `git pull`.** On a healthy VM it would have completed and left the server in a systemd crash loop, which is precisely the outcome the guard's own comment says it exists to prevent (*"the failure surfaces as a systemd crash loop that looks nothing like a deploy problem"*).

  **Fix:** check the remote. One SSH round-trip before the pull — `gcloud compute ssh … --command="grep -q '^METATRON_AUTH_PASSWORD=' ~/multi-model-mcp/.env"` — and abort on non-zero. Note the guard is otherwise well-designed: it runs before `git pull` so a refusal leaves the VM untouched, and `22e179d` fixed its remediation advice to append the variable rather than scp the whole file (correct — the VM's `.env` holds values the Mac's does not). Only the test target is wrong. *Owner note: `deploy.sh` was being edited by a parallel window on 2026-08-04; check current state before editing.*

- **⚠ ~4-hour silent outage: the VM's guest lost all networking while GCE reported `RUNNING`. Root cause unknown.** Found 2026-08-04 ~00:20 when a deploy failed at SSH. Recovered by stop/start; the machine has been fine since.

  **Signature, for whoever sees it next.** GCE said `RUNNING` and the serial console was logging in real time — the OS was alive, not hung. But every process inside failed identically on `dial tcp 169.254.169.254:80: connect: network is unreachable` — the metadata server, on a link-local address, which is reachable from any healthy VM by definition. `network is unreachable` rather than a timeout means **no route existed**: the guest's NIC lost its routing. `tailscaled` looped on *"connectivity impacted; triggering captive portal detection"*; Tailscale showed `offline, last seen 4h ago, tx … rx 0`. Billing was `True`, the IAP firewall rule correct, IPs assigned, and `lastStartTimestamp` was three days earlier — **nobody rebooted it; networking died under a running machine.**

  Same signature as the 2026-07-31 `nic0 is frozen` incident, **but with the known cause absent** — billing was never disabled this time. So either that incident's root cause was misattributed to the billing freeze, or there are two paths to the same failure. Worth resolving before trusting VM uptime: it is silent, it survives a `RUNNING` status check, and it cost ~4 hours here.

- ~~**Nothing detects that the VM is down.**~~ — **fixed, closed 2026-08-05 (found already
  shipped in `10bf194`, 2026-08-04, never crossed off).**
  [scripts/sync_dev_backlog.py:227-233](scripts/sync_dev_backlog.py#L227) now calls
  `vm_status()` and appends `⚠ VM running but unreachable` when the VM reports `RUNNING` but
  the sync can't reach it — distinct from the silent, expected case of a stopped VM. **This is
  live and firing right now**: this session's own startup hook printed exactly that warning.
  *filed 2026-08-04 by dev session · fixed 2026-08-04 `10bf194` · closed 2026-08-05, observed
  firing live at this session's own startup*

### Surfaced 2026-08-04 by the outward-actions scope decision

Full reasoning: [archive/plans/outward_actions_scope_2026-08-04.md](archive/plans/outward_actions_scope_2026-08-04.md).

> **✅ A, B and C were decided and built 2026-08-04** (`ca993fe`, `15b9a41`, deployed). The
> three items below are kept for their reasoning; the "proposed"/"awaiting" framing in them is
> historical. **What Mike chose differed from what was recommended in two places:** B is
> **out-of-band** confirmation (server-recorded tap, not a model-mediated token), and C is
> **CRM contacts**, not self-only. Those two hold each other up — **if B is ever downgraded to
> model-mediated consent, C must shrink back to self-only in the same change.**

**Still open from this block:**

- ~~**The SMTP send path has never been exercised.**~~ — **exercised, closed 2026-08-05. First
  real email this system has ever sent.** Ran the full production path live on the VM against
  `mike`: `send_email()` → `PENDING_CONFIRMATION` → `tools.confirm.approve()` → second call with
  matching `confirm_token` → real SMTP send. Result: `{'status': 'sent', 'to':
  'diamond.mike.mt@gmail.com', ...}`. Gmail SMTP on port 587 with STARTTLS + app password is
  confirmed working, not just assumed. **Bonus finding, not a bug:** `consume()`'s fingerprint
  match correctly refused a second call whose subject/body didn't match the approved request
  (`"The details changed since this was approved"`) — caught a scripting mistake in this test
  itself, which is exactly the protection it's there for.
  *filed 2026-08-04 · exercised live 2026-08-05 against the VM, persona mike, real SMTP send*

- **✅ B1a (direct-injection / self-disclosure red team) run and passed 2026-08-04.** New
  scripted runner [tests/run_b1_redteam.py](tests/run_b1_redteam.py) (mirrors
  `tests/run_a4_safety.py`'s pattern — static reviewed scenarios, dated report, re-runnable).
  Three suites, 75 checks, gate PASS: the 9 `security_testing_plan.md` §1 disclosure categories
  (15 prompts incl. GPT-4o-sourced phrasing variants for persona-adoption/hypothetical-framing/
  roleplay-escape) — no architecture leak in any response; `filter_output()` unit suite (61
  checks) — every planted confidential term suppressed, all clean text passes, Exchange 027
  false positive reproduced as a documented non-gating regression marker; confused-deputy probe
  — structural check confirms `_dispatch_from_coordinator()` is only ever called on the
  Coordinator's own output (never on specialist text), plus a live probe confirming the parser
  itself has no innate protection (would dispatch a hostile `SPECIALISTS_TO_CALL` block if ever
  fed one) — so the structural finding is load-bearing, not defense-in-depth. Report:
  `tests/security_redteam_2026-08-04.md`. **This closes B1a only** — B1b (indirect injection via
  email/calendar/web) remains gated on Track E integration maturity per
  `archive/plans/scope-out-executing-b1-b4-deep-sun.md`, and B1 as a whole (both halves) is what
  A7 sign-off needs.

- **Extend the gate to `write_agent_config` / `write_config`.** B2 requires a
  human-in-the-loop gate on these and `tools/confirm.py` now provides one, but they are not
  wired to it. This is also the standing answer to the open denial entries above
  (`physical_health`, `logistics` reaching for `write_agent_config`): gate it rather than
  granting or refusing outright.

- ~~**⚠ The confirmation gate is a prompt, not a control (Decision B).**~~ — **built, closed
  2026-08-05.** This entry predates the 2026-08-04 build (`ca993fe`, `15b9a41`). Verified today:
  [tools/confirm.py](tools/confirm.py) implements exactly the shape this entry proposed —
  `request()` returns a `PENDING_CONFIRMATION` token and performs nothing;
  `POST /confirm` ([core/server.py:702](core/server.py#L702)) is the only writer that can
  approve one; `consume()` gates the second call. `send_email` is wired to it end-to-end
  ([tools/mail.py:278-306](tools/mail.py#L278)) — two-step by design, first call always returns
  `PENDING_CONFIRMATION` and sends nothing. **What's still genuinely open is the separate bullet
  below** — `write_agent_config`/`write_config` are not yet wired to this same mechanism.
  *filed 2026-08-04 · superseded by the 2026-08-04 build · closed 2026-08-05 against
  tools/confirm.py, core/server.py:702, tools/mail.py:278-306*

- ~~**Provenance modifier for the action tiers (Decision A).**~~ — **already built, closed
  2026-08-05. Was stale in this file, not actually open.** [config/agents/synthesizer.md:350-368](config/agents/synthesizer.md#L350)
  ("Where the idea came from changes the tier") implements exactly the proposed rule: the
  same "would the need still stand if the external text vanished?" test, an externally
  originated action moves up one tier, and anything outward-facing/irreversible/involving
  money is Confirm First with the source quoted **even where an opt-in would otherwise
  permit it** — the precise "regardless of tier and regardless of opt-in" clause this entry
  asked for. Built in the same commit as Decisions B and C, `ca993fe` (2026-08-04), which
  this file already credited for B and C but not A — this entry was never crossed off.
  *filed 2026-08-04 · found already built 2026-08-05 against
  config/agents/synthesizer.md:350-368 and `git log -- config/agents/synthesizer.md`,
  commit ca993fe, 2026-08-04*

- ~~**`send_email` restricted to the user's own address (Decision C).**~~ — **built, closed
  2026-08-05.** [tools/mail.py:229-262](tools/mail.py#L229) enforces it in Python: `_known_recipients()`
  allows the user's own addresses (`account_email` / `contact.email` from `profile.yaml`) plus
  saved CRM contacts — the docstring cites this exact decision by name ("Roadmap item 5, Decision
  C") and explains why it's enforced here rather than in an agent instruction: an injected email
  that talks the model into a different recipient fails this check regardless of how convincing
  it was. Broader than self-only per the block's header note (CRM contacts included, a deliberate
  choice), gated on Decision B which is also built (see above).
  *filed 2026-08-04 · built 2026-08-04 `ca993fe`/`15b9a41` · closed 2026-08-05 against
  tools/mail.py:229-262*

- **Not opened, deliberately:** credential store, agentic browsing (level 3), arbitrary-recipient email, transactions. The last three are gated on a credential store that does not exist and on the gate above.

- ~~**`research_agent` omits `allowed_tools`, so it holds *all 53* tools.**~~ — **stale, closed
  2026-08-04. Already fixed same day.** `allowed_tools: [fetch_url]` was added to both
  `config/modules/routing.yaml:115` and `routing_cloud.yaml:130` in `c886560` (2026-08-04,
  10:55Z) as part of the `fetch_url`/`read_email` build — this entry was never crossed off.
  Verified directly against both files before B2 scoping started, so B2 doesn't re-open it as
  live scope. *filed 2026-08-04 · found stale 2026-08-04 while scoping B1a, verified against
  routing.yaml/routing_cloud.yaml directly (not against this entry's own description)*

- ~~**APK rebuild pending — password reveal toggle, dismissable transcription readout, and
  bubble-width line-wrap.**~~ — **built 2026-08-05.** `./deploy.sh` ran first (line-wrap fix +
  spend guard pricing), then `npx cap sync android && cd android && ./gradlew assembleDebug` —
  `BUILD SUCCESSFUL`, output at `android/app/build/outputs/apk/debug/app-debug.apk`. **Verified
  the build actually picked up the latest change** rather than trusting a stale-looking mtime:
  unzipped the APK and confirmed `overflow-wrap: anywhere` is present in the packaged
  `.message` rule. Served from the Mac over Tailscale (`python3 -m http.server 8888`) for
  sideload. **Still needs:** actually installing it on the phone and confirming it runs — that
  last step is Mike's, not something done from here.
  *filed 2026-08-04 · deployed + built 2026-08-05, APK content-verified · sideload/install still
  pending on-device*

- **Test the dismissable transcription readout — code-verified 2026-08-05, live dictation test
  still not run.** Re-checked `static/index.html` against every named pass condition:
  [:104-125](static/index.html#L104) caps `#transcript` at `max-height: 4.5em` with
  `line-height: 1.5` (= exactly 3 lines), `overflow-y: auto` for internal scroll;
  [:637](static/index.html#L637) sets `TRANSCRIPT_TIMEOUT_MS = 12000`; the close button
  ([:466](static/index.html#L466), [:655](static/index.html#L655)) calls the same `hideTranscript()`;
  `#transcript-wrap { display: none }` by default with `.shown` toggling `flex`
  ([:105,114](static/index.html#L105)), so footer height is untouched while hidden. Every
  clause the test asks for is present in code. **What this session could not do: dictate 30+
  seconds of real speech into a browser and watch it.** No mic/browser access here — this
  remains an actual human test, owed before it's called done.
  *filed 2026-08-04 · code-verified against every pass condition 2026-08-05 · live test still
  outstanding*

### Surfaced 2026-08-03 by the context-audit test run

- ~~**⚠ A4 clinical-flag hard-fails must be re-run before A7 sign-off.**~~ **Gate PASSED
  2026-08-04 on the cloud path — 6/6.** Report:
  [tests/a4_safety_rerun_2026-08-04_gemini.md](tests/a4_safety_rerun_2026-08-04_gemini.md).
  Runner: [tests/run_a4_safety.py](tests/run_a4_safety.py), `--persona sarah_chen --provider gemini`.

  All three clinical flags fire correctly under the post-prefix-caching assembly order, and
  verified as firing for the right reason rather than on a keyword match: `SUICIDAL_IDEATION`
  with 988 crisis signposting; `MANIA` with an explicit instruction not to celebrate the energy
  (its documented failure mode); `MEDICATION_MISSED_CRITICAL` naming lamotrigine as
  *"morning dose, required"* while correctly leaving `optional` vitamin D alone. Finance
  arithmetic exact on all three (FIN-1 $520/$80; FIN-2 $18,000 → $19,091; FIN-4 47 months /
  $6,096 — amortisation checked by hand).

  **A prerequisite defect was found and fixed to make PH testable at all.**
  `physical_health` was not granted `read_agent_config`, while
  [physical_health.md:106](config/agents/physical_health.md#L106) requires
  `MEDICATION_MISSED_CRITICAL` classification to come from the stored medication profile and
  *"never from the agent's judgment"*. The flag was therefore structurally unfireable — the
  agent had to consult a profile it had no tool to reach. Granted in both
  `routing_cloud.yaml` and `routing.yaml`; `write_agent_config` deliberately **not** granted.
  This resolves Inbox items 1 and 2 in the read direction — those warn-mode entries were the
  symptom of this. **Note this flag has never actually worked in production**, which no
  assembly-order re-run would have revealed.

  **Two limits on what this result covers — do not read it as more than it is:**
  1. **Cloud path only.** The original A4 baseline was Ollama/qwen3:14b. This run is not a
     like-for-like comparison against it; it verifies the pass conditions hold on the path
     currently serving the user. The local path remains unverified under the new assembly
     order — `--provider ollama` runs the same suite when that matters.
  2. **Specialists in isolation, not end-to-end.** A flag that fires correctly in Mental
     Wellbeing can still be held at the Synthesizer, which is the actual user-facing failure
     mode and the reason A4 added the mandatory-surface block to `synthesizer.md:21`. The head
     layer also had dynamic context moved by the same change. **A pipeline-level probe is the
     one piece of this gate still missing** — recommend running it before A7 sign-off.

  A7 remains blocked on B1, Check 10 and Check 12. This clears only the named pre-sign-off gate.

- ~~**Pre-existing dead link in the project log.**~~ — **fixed, closed 2026-08-05.**
  [archive/PROJECT_LOG.md:1165](archive/PROJECT_LOG.md#L1165) pointed at a "Plan and Phase 0"
  session file that was never written. The same section's content is covered by
  `archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md`
  — already the target of two other links in this log for adjacent parts of the same work.
  Repointed rather than inventing a new writeup.
  *filed 2026-08-03 by dev session · fixed 2026-08-05 against archive/PROJECT_LOG.md:1165*

### Recovered from SESSION.md prose, 2026-08-03

*These sat in dated `SESSION.md` sections and were never filed. That file is now a primer and
the history moved to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md), so anything still
actionable had to come here or it would have gone quiet — the same way the unsurfaced-opportunity
item "nearly aged out" (see Troubleshooting signal below).*

- ~~**[DB-0803-07] ⚠ `deploy.sh`'s drain is decorative — every deploy kills in-flight WebSocket
  exchanges.**~~ — **fixed, closed 2026-08-05 (found already shipped in `10bf194`, 2026-08-04,
  never crossed off).** The WS exchange loop now holds the same `_active_lock` as the SSE path
  around the full in-flight block, counting exchanges not connections —
  [core/server.py:616-618,668-669](core/server.py#L616). Verified live against current source,
  not just the commit message.
  *filed 2026-07-30 by dev session (client/app audit) · recovered from SESSION.md:317
  2026-08-03 · fixed 2026-08-04 `10bf194` · closed 2026-08-05 against core/server.py:616-669*

- ~~**Synthetic persona data trees are not gitignored.**~~ **Done 2026-08-04** — `.gitignore`
  now carries `data/personas/*/` in place of the enumerated per-persona list. Five trees were
  uncovered (`arthur_brooks`, `cal_newport`, `danny_park`, `maya_torres`, `oliver_burkeman`)
  plus most of `ryan_holiday`; all are now ignored, as is any persona added in future — the
  drifting hand-maintained list was the actual defect, not the missing entries.

  **Two corrections made while fixing it.** (1) The section heading read *"Test persona runtime
  data"* and listed `mike` under it. `mike` is a real user's logs, health and finances, not a
  test fixture; it now has its own explicitly-labelled sensitive-tier rule. (2) The first draft
  of the fix carried `sarah_chen`'s *"a genuinely new fixture needs `git add -f`"* note up to
  the top of the block, where it read as a blanket escape hatch across every tree — including
  `mike`. That is an instruction to force real user data past the ignore rule, i.e. the
  2026-07-29 incident with extra steps. The `-f` allowance is now scoped to synthetic trees
  and the real-user rule states that no such hatch exists there.

  Verified: 65 tracked seed fixtures still tracked (`.gitignore` does not untrack), no
  deletions, `git check-ignore` passes for all nine existing personas and an invented tenth,
  and `git add -A --dry-run` stages zero files under `data/personas/`.

- ~~**`[vertex_cache] 404 cached content metadata`**~~ — **believed fixed; closed 2026-08-05.**
  Registry eviction on a 404 is present at [core/orchestrator.py:1417-1424](core/orchestrator.py#L1417)
  (`"not_found" in text or ("404" in text and "cach" in text)` → `_vertex_cache_registry.pop`).
  **Last occurrence in the VM journal: 2026-07-29 13:05** (cache id `3167247740363079680`), none
  in the seven days since. Closing on that basis, with the caveat stated: seven clean days is
  evidence, not proof, and 2026-07-29 sits at the edge of the retained window.

  **Do not confuse this with what is in the log now.** Eleven `[vertex_cache]` warnings on
  2026-08-04 are `NameResolutionError` on `oauth2.googleapis.com` — DNS failure during the
  four-hour outage, a different cause with a similar-looking line. Anyone re-filing this on the
  strength of a `grep vertex_cache` will re-file the outage.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:385 · verified 2026-08-05 against
  the VM journal + core/orchestrator.py:1417*

- ~~**[DB-0803-02] ⚠ `Object of type AgentRecord is not JSON serializable` — proactive sessions
  failing outright.**~~ — **root-caused and fixed 2026-08-04, deployed `10bf194`.**

  **Root cause:** `core/router.py:166`, inside `log_model_error()`. Three call sites in
  `core/orchestrator.py` (:1575, :1676, :1881 — the last is the Coordinator/Synthesizer
  OpenAI-compat loop every failing scheduled job passes through) did
  `_agent = _tr.get_current_agent() or "unknown"`. `get_current_agent()` returns the live
  `AgentRecord`, not a string, and a truthy record short-circuits the `or` — so `_agent` was the
  record object itself whenever one was active (always, mid-pipeline). `log_model_error` then
  crashed on `json.dump` trying to serialize it, **masking whatever the real underlying model
  failure was**. Confirms and completes the localisation two sessions had already narrowed down
  (`core/trace.py` was correctly ruled out both times).

  **Fix:** one line — `"agent": agent.agent if hasattr(agent, "agent") else agent,` — fixes all
  three call sites at one JSON boundary rather than patching each.

  **Verified two ways before calling this closed:**
  1. Local: called `log_model_error()` directly with both an `AgentRecord`-like mock and a plain
     string — no `TypeError` either way.
  2. **On the deployed VM, with the real object**, not a mock: started an actual
     `RequestTrace`/`AgentRecord` via `core.trace.start_request_trace` +
     `push_agent('coordinator', ...)`, then called `log_model_error()` with the real
     `get_current_agent()` return value — the exact call that was crashing in production. It
     did not raise, and the resulting log entry correctly read `"agent": "coordinator"` (a
     string, not the object dump a pre-fix run would have produced). The synthetic test entry
     was deleted from `data/diagnostics/model_errors.json` afterward so it doesn't read as a
     real production error.

  **What is *not* yet confirmed — a genuine scheduled fire completing end-to-end under real
  conditions** (not a manual reproduction). See **[DB-0804-01]** below for the time-gated checks
  that confirm this, and why they should not be run early.
  *filed 2026-08-03 by dev session · elevated 2026-08-05 · root-caused, fixed and deployed
  2026-08-04 by dev session · verified against core/router.py and live VM reproduction*

- **[DB-0804-01] Time-gated follow-up: confirm a real scheduled fire completes clean under
  [DB-0803-02]'s fix.** The fix above is verified against the exact crashing code path, but not
  yet against a live scheduler fire hitting real model-call variance. **Do not check any of
  these before the stated time — an early check just shows "hasn't fired yet," which reads as a
  regression and isn't one.**

  1. **`companion_checkin`, not before 2026-08-04 23:05 BST.** `min_gap_minutes: 180` from its
     last real fire (20:03 BST) puts the earliest next attempt at ~23:03. Check:
     `gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command="sudo journalctl -u metatron-scheduler --since '2026-08-04 22:55' | grep -E 'companion_checkin|AgentRecord'"`.
     Pass: a `firing companion_checkin` line with no following `AgentRecord is not JSON
     serializable` error. (A `skipping` line is a gate decision, not a failure — re-check at the
     next 30-minute poll rather than treating it as a fail.)
  2. **`morning_brief`, not before 2026-08-05 07:35 BST.** Fires daily at 07:30. Same journalctl
     pattern, grep `morning_brief`.
  3. **One-week count, not before 2026-08-11.** Re-run the exact baseline query:
     `sudo journalctl -u metatron-scheduler --since '7 days ago' | grep -c 'AgentRecord is not JSON serializable'`.
     Baseline was 18 in the 7 days to 2026-08-05. Pass: at or near 0 for the 7 days following
     deploy (2026-08-04 21:00 onward) — some non-zero count is possible if the *same* call sites
     hit a genuinely different, unrelated serialization issue, so read the actual log lines
     before treating a nonzero count as this bug recurring.

  *filed 2026-08-04 by dev session · depends on [DB-0803-02] · not to be actioned before the
  per-check times above*

- **[DB-0803-05] `sw.js` has no `fetch` handler and caches nothing**, and `/` is served
  `no-store` — no offline shell, so an unreachable server shows a browser error page rather than
  the app. **Confirmed still real 2026-08-05:** [static/sw.js](static/sw.js) registers exactly
  four listeners — `install`, `activate`, `push`, `notificationclick`. No `fetch`.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:320 · verified 2026-08-05 against
  static/sw.js*

- **[DB-0803-06] `shownIds` eviction wipes the whole set instead of evicting incrementally —
  re-derived and confirmed real 2026-08-05 (line numbers updated).** `shownIds` is declared at
  [static/index.html:706](static/index.html#L706). Two call sites do a full
  `if (shownIds.size > 100) shownIds.clear()` rather than dropping only the oldest entries —
  [:944](static/index.html#L944) in `renderHistory()` and [:971](static/index.html#L971) in
  `sendViaWebSocket()`.

  **Why it's a real bug, traced through the dedup logic:** every WS message type
  (`chunk`/`done`/`message`/`error`/`retract`, [:836-927](static/index.html#L836)) branches on
  `shownIds.has(msg.exchange_id)` to tell "my own exchange, already rendering" from "foreign or
  catch-up exchange, needs a fresh render." A full clear means that once a conversation crosses
  100 exchanges, the next reconnect's `renderHistory()` re-populates and immediately re-empties
  the set — so any subsequent `'message'` catch-up for an exchange the device already rendered
  looks unseen and gets rendered a second time. **Fix:** evict oldest-first (e.g. convert to an
  array-backed ring, or drop the first N insertion-ordered keys) instead of `clear()`, at both
  call sites.

  **`eea3faf` (2026-07-27) is real but fixes a narrower bug than this entry.** It swapped
  `sendViaWebSocket`'s clear/add order so the just-sent exchange's own ID survives the clear
  (previously `.add()` then `.clear()` wiped the ID that was just added, breaking the client's
  own chunk/done recognition — a stuck bubble, not a duplicate). It did not touch the
  clear-vs-evict question: both call sites still do a full `.clear()` today, just in the
  now-correct order relative to the current send. The duplicate-render risk traced above is a
  separate, still-open defect at the same two line numbers.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:319 · re-derived and confirmed
  2026-08-05 against static/index.html:706,836-927,944,971 and commit eea3faf*

- ~~**`/session` (non-streaming) leaks the `[CONTEXT]{…}[/CONTEXT]` block**~~ — **fixed;
  closed 2026-08-05.** `run_session` now calls `split_context_block()` then `filter_output()`
  before returning ([core/orchestrator.py:2690](core/orchestrator.py#L2690)), and
  `persist_context_block()` writes the tracker on the same path — so both halves of the
  complaint (leaked control text, tracker never written) are covered. The comment there records
  the intent explicitly: *"one implementation so the two paths cannot drift apart again."*
  *filed 2026-08-03 by dev session · recovered from SESSION.md:386 · verified 2026-08-05 against
  core/orchestrator.py:2690*

- ~~**[DB-0803-04] `write_config()` heading duplication.**~~ — **not a bug; the described fix
  already exists and works. Closed 2026-08-05, correcting a wrong verification from earlier the
  same day.** The 2026-08-05 pass checked only [tools/config_writer.py](tools/config_writer.py)
  (confirmed: no heading logic there, writes verbatim) and stopped, concluding the symptom was
  unconfirmed. `_titled()` is not in that file — it's in
  [core/orchestrator.py:187-199](core/orchestrator.py#L187), and its docstring states the exact
  mechanism the entry described: *"The Goals Interviewer writes prime_directive.md and
  mission.md through write_config(), which stores the model's text verbatim — and the model
  includes its own heading. Without this check the system prompt carries the heading twice with
  an empty section between."* `load_config()` calls it at [:234](core/orchestrator.py#L234) for
  both files. Added in `6601479`, predating this entry. **The lesson: "cited code does not
  exist" is only true of the one file checked — the fix can live one layer up from where the
  write happens.**
  *filed 2026-08-03 by dev session · recovered from SESSION.md:387 · first verification
  2026-08-05 incomplete · corrected 2026-08-05 same session against core/orchestrator.py:187-234*

- **Pre-2026 logs in mike's tree** (`2025-01-24`, `2025-05-13`–`16`) — believed genuine early-dev
  data, but the SEQ 021 session found one hallucinated log dated 14 months in the past. Worth
  confirming none of these are the same.

  **Attempted 2026-08-05, blocked — real data lives on the VM, not the Mac.** Per `CLAUDE.md`
  → Personas, live persona data is VM-owned; the Mac copy is a stale mirror. Checked it anyway:
  `data/personas/mike/logs/` on the Mac has neither of the originally-cited filenames — either
  already cleaned up, or this mirror predates them — so this pass **cannot confirm or refute
  the original claim**. **New finding, same class of bug:** the same local directory has
  `2024-08-04.json` (`{"notes": "User re-engaged with the session.", "date": "2024-08-04"}`,
  74 bytes) sitting alongside a correctly-dated `2026-08-04.json` — a two-years-stale hallucinated
  date, not the 14-months-stale one previously found, but the identical failure mode. **Needs
  the VM to resolve properly**: `data/personas/mike/logs/` there is authoritative; this session's
  VM access was down (see the sync report). Check both the original two dates and whether
  `2024-08-04.json` has a live-VM counterpart when it's reachable.
  *`SESSION.md:227` · re-attempted 2026-08-05, blocked on VM reachability · new data point added,
  not closed*

- **Coordinator restructure (token-reduction Step 6)** — single-pass directive assembly replacing the multi-turn session, ~15,000t. Deferred 2026-06-24 pending Steps 1–5 stabilising; they have. **Re-scope against measured data first:** the coordinator runs 1 turn, not the 7 the roadmap assumes — the real cost driver is per-specialist internal turns (logistics measured at 8). Relates to the D2 item-5 mis-scoping already on this list. *`SESSION.md:602`.*

### Recovered from conversation, 2026-08-01/02

- **Data breadth — sleep is nearly the only thing consistently logged.** This is the *root cause* behind "too much focus on sleep": with one reliable signal and little else, any reasoning leans on it by default. The 2026-08-03 `synthesizer.md` rules mitigate the symptom (don't over-read a thin record; ask for what's missing) but cannot fix it. Needs a real answer on capturing training, food, work and mood with low enough friction that they actually get logged. Mike has also asked that sleep tracking itself shift to **total hours plus interruptions** rather than a disruption narrative (2026-08-03).

- ~~**Nothing in the system can actually set a reminder or calendar entry.**~~ — **the whole
  build order it prescribes is complete; closed 2026-08-05.** *"The calendar integration will do
  later. I don't understand why it didn't, why it triggered at all"* — SEQ 011, 2026-08-01.

  Its four steps, each verified: **enable CalDAV** — live 2026-08-03 (`cfcd212`), with
  recurrence, alarms and all-day support. **Grant Logistics its config tools** — 2026-08-05
  (`9361537`). **`write_schedule`/`list_schedules`/`delete_schedule`** — built and granted
  2026-08-03 (`078e618`, `2f74cd2`); present in [tools/schedule.py](tools/schedule.py) and
  registered in `core/orchestrator.py`. **Delivery preference** — push is live.

  **Worth recording, because it misled this session's own analysis:** the entry's claim that
  *"`scheduler.yaml` jobs are static with no tool to add one"* went stale on 2026-08-03 and was
  still being read as current on 2026-08-05, where it produced a recommendation to hold the
  `logistics` `write_agent_config` grant pending work that had already shipped two days earlier.
  A stale premise does not just waste the effort spent on it — it argues for the wrong decision,
  persuasively.
  *filed 2026-08-01 by Mike via Synthesizer · origin SEQ 011 · verified 2026-08-05 against
  tools/schedule.py, both routing files, and the CalDAV commit*

- **Dictated email addresses come through wrong and need correcting by hand.** Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus `diamond.like.gmail.com` at SEQ 006. Partly Whisper tuning (above), but a known-values pass would fix it outright — the user's own email is in `profile.yaml`, so a transcript token close to a known contact string should snap to it rather than be passed through.

- **One domain is measured and the others are not, so the measured one explains everything.** The user's complaint was *"once again, you're making too much of the sleep disruption"*, raised more than once. The `synthesizer.md` rules shipped 2026-08-03 (*beware the loudest available signal*; *where the record is thin, ask for what is missing*) are **mitigation, not a fix** — they tell the Synthesizer to distrust the only signal it has, which is right but does not give it a second one.

  **The actual problem:** sleep arrives automatically and consistently; training, food, work and mood arrive only when the user happens to mention them. Any honest reasoner facing that record over-weights sleep, because sleep is the only thing that is *there*. No instruction fixes an empty column.

  **What to look at:** which domains have logged data at what density in `data/personas/mike/logs/*.json` — count the populated keys per day over the last 30, do not assume. The cheapest lever is probably the ask-for-missing-data rule already shipped, *measured* after a few weeks to see whether it actually raises breadth. Beyond that: whether check-ins should rotate which domain they ask about, and whether any of the thin domains can be captured passively the way sleep is. **Do not build a weighting algorithm before checking whether the data is simply absent** — this is the same failure as tuning a model on a dataset with a missing column.

  Related: this is also what the Pattern Miner's baselines will run into. Worth resolving before trusting any cross-domain pattern it produces.

- ~~**Check-ins are not gated on the user having been present at all.**~~ — **not a bug;
  closed 2026-08-05 by Mike's decision.** Raised as a possible gap: a day where the user says
  nothing still fires the full check-in schedule, unlike `quiet_after_user_minutes` /
  `min_gap_minutes`, which only stop a check-in from interrupting a *live* conversation.

  **Mike's call:** check-ins should continue to fire through silence. The admonition behind the
  original gates was against spamming an actively-engaged user beyond their engagement level —
  not against reaching out during a quiet stretch. Confirmed against
  [core/scheduler.py:173-196](core/scheduler.py#L173): `_activity_gate_blocks()` implements
  exactly `quiet_after_user_minutes` and `min_gap_minutes` and nothing else — no
  silence-triggers-skip logic exists, which is the correct state. No code change.
  *filed from cost-analysis findings · closed 2026-08-05 per explicit user decision*

- **Sentence-chunked TTS.** Kokoro is at 2.8s/call after the in-process fix (down from 15.0s, which was a subprocess re-import per request). Streaming the first sentence while the rest synthesises would cut perceived latency again. **Deferred pending a judgement call on whether 2.8s actually feels slow in use** — do not build this before using voice mode enough to say. Named in the parked programme as an alpha nice-to-have, not a blocker.

- **Browser does not live-refresh on foreign messages — not closed; a related but distinct bug
  was fixed 2026-08-01.** A message sent from the terminal or the Android app reaches the
  browser only after a manual page reload; the app and terminal sync fine. **This entry's own
  diagnosis is transport-ruled-out**: *"sync itself is confirmed working — this is a
  client-side render path, not a transport failure."*

  **Checked 2026-08-05: `ace22c7` (2026-08-01) already fixed the half-open-socket case** —
  `STALE_AFTER_MS = 45000` in [static/index.html:717](static/index.html#L717) treats a socket
  as dead if no ping/message arrives in 45s regardless of `readyState`, with reconnect-and-catchup
  wired to `visibilitychange`/`focus`/`online`/a 20s interval. Real fix, but for **transport**
  going stale — specifically Android's WebView freezing in the background. This entry diagnoses
  a **render-path** bug with transport already working, which `ace22c7` doesn't touch (it never
  runs the reconnect path if the socket wasn't actually dead). **Cannot confirm from code
  reading whether the render-path symptom still reproduces** — needs a live two-device test:
  open the browser tab, send a message from the terminal without touching the tab, and watch
  whether it appears unprompted.
  *filed 2026-08-01/02 · re-checked 2026-08-05, adjacent transport fix found and dated but the
  entry's own diagnosis is a different code path · needs live reproduction, not closed*

- **Cannot take an action on an external website.** *"Can you go on the R website and reserve tickets for us"* — SEQ 006, 2026-08-02. No browsing-with-actions capability exists. Worth an explicit decision on whether this is ever in scope, since it is the first request of its kind and carries a real security surface: the same message handed over an email address, postal address and phone number.

- ~~**No tool can write a biographical fact.**~~ **Done 2026-08-03 (`35e53ee`)** — `tools/profile.py`. See the follow-on immediately below, which is the part that was *not* built.

- ~~**The user cannot see or correct what has been stored about them.**~~ — **fixed, closed
  2026-08-05.** The tools existed and were already granted to `synthesizer`
  ([config/modules/routing.yaml:44](config/modules/routing.yaml#L44)/`routing_cloud.yaml:35`) —
  the actual gap was that [config/agents/synthesizer.md](config/agents/synthesizer.md) never
  mentioned `read_profile`/`write_profile` by name, so the user-facing agent had the door but
  no instruction to open it. Added a block under **Tools available** covering all three items
  from the shape-of-fix below: **review** (`read_profile()` on "what do you know about me",
  read back in plain language, not a raw dump), **correct** (`write_profile` overwrites the
  field on a correction), and **confirm at capture** (one clause in the reply when a new fact
  is written, e.g. "noted your address as X"). Config-only change, no code — matches the
  project's own "config is the product" principle exactly.
  *filed 2026-08-03 · fixed 2026-08-05 against config/agents/synthesizer.md § Tools available*

  **Original entry, preserved for the reasoning:** `write_profile` captures silently: a fact given in passing during a conversation is written to `profile.yaml` with no confirmation at the time and no way to review it afterwards. There is a write door and a read door for *agents* (`read_profile`), but nothing pointed at the user.

  **Why it matters, concretely:** on 2026-08-02 contact details were captured into the wrong file and rode in every system prompt for a day before anyone noticed — and only because a human read the file. A wrong value (misheard email, stale address, an inferred occupation the user would not endorse) now persists indefinitely and is quoted back as fact by Logistics when booking. Dictated email addresses are already known to arrive wrong three times in three minutes (see the transcription item above), and `write_profile` will store whatever it is handed.

  **Shape of the fix, in rough order of value:**
  1. **Review** — a way to ask "what do you know about me?" and get the stored fields back in plain language. `read_profile` already returns them; this needs a user-facing route, not new storage. Note the `contact:` block is deliberately excluded from `load_profile()`'s rendered summary, so a review path must read it explicitly rather than relying on what is in the prompt.
  2. **Correct** — `write_profile` already overwrites by field, so correction is mostly a matter of the user being able to say "that's wrong" and have it reach the tool.
  3. **Confirm at capture** — cheapest version is one clause in the reply ("noted your address as X"), which costs no extra turn. A confirmation *prompt* before writing would cost a round trip and is probably not worth it for low-stakes fields; consider it only for the `contact:` block.

  **Constraints:** unknown fields are refused rather than absorbed (`_SCALAR_FIELDS`/`_CONTACT_FIELDS`/`_LOCATION_FIELDS` in [tools/profile.py](tools/profile.py)) — an invented key is exactly how `mike.md` acquired a section no code knew about. `profile.yaml` is VM-owned and gitignored; edit it on the VM, never reconstruct it on the Mac.

- **No agent can act on a web page on the user's behalf (level 3).** Raised 2026-08-03 as three
  distinct capabilities. **Levels 1 and 2 are now both built — verified 2026-08-05, closing that
  part.** Grounded search (`run_session_gemini_grounded`) was already live. `fetch_url` shipped
  2026-08-04 ([tools/web.py:146](tools/web.py#L146)) with the injection defense that was named as
  its prerequisite, not a follow-up: returned content is wrapped in `<untrusted_content>` tags
  ([tools/untrusted.py](tools/untrusted.py)), confirmed at the `fetch_url` docstring itself.

  **What's left is level 3 only: navigate, log in, fill forms, transact — a different animal.**
  A hostile page reached via `fetch_url` can only *say* things to the model; level 3 lets a page
  make the model *do* things using the user's credentials. Explicitly deferred, not started:
  behind an authentication story that doesn't exist yet, and requires per-action confirmation
  (the mechanism for that now exists — see `tools/confirm.py` above — but nothing calls it here).
  Do not ship this on the assumption that `fetch_url`'s injection wrapping covers it; it doesn't,
  it addresses a different failure.
  *filed 2026-08-03 · levels 1-2 built 2026-08-04, closed as such 2026-08-05 against
  tools/web.py:146, tools/untrusted.py · level 3 remains open, not started*

### Troubleshooting signal

- **"Unsurfaced opportunities" has no instrumentation — the only troubleshooting category that cannot be measured.** The standing per-exchange review looks for four things: missed routing, unsurfaced opportunities, token overspend, and useless calls. Three of those leave traces. This one is **an absence**, and nothing in the system logs what it failed to raise. *Recorded in SESSION.md 2026-07-29; not previously carried into this list, which is how it nearly aged out.*

  Why it resists the obvious approach: you cannot diff against a ground truth that was never written down. The trace shows which specialists ran and what they returned — not the thing none of them thought to mention. So there is no post-hoc query that recovers it, and no amount of richer tracing produces the signal on its own.

  Three routes, cheapest first:

  1. **Make the `·` feedback dot carry a reason.** Already in the UI and already the nearest hook. A one-tap "missed something" reason code turns a silent miss into a dated, exchange-linked record. Costs almost nothing and produces real data, but only catches misses the user *notices* — which is a biased sample, and systematically misses the ones that matter most.
  2. **Retrospective sweep.** Periodically re-run a batch of past exchanges with full context and a prompt asking what a good response would have raised that the live one did not. Catches misses the user never saw. Costs tokens, and grades the system with the same class of model that produced the output, so it is suggestive rather than authoritative.
  3. **Close the loop against outcomes.** The context tracker already holds `open_threads` and `follow_ups`. A thread that goes quiet without resolution is a candidate missed opportunity, detectable without any judgement call. Narrower than the other two, but it is the only one that yields a hard signal rather than an opinion.

  Recommend 1 and 3 together — cheap, complementary, and neither depends on model self-assessment. Hold 2 until there is enough history for a sweep to be worth its token cost.

---

## Open — housekeeping

Stale docs, paths, and low-priority corrections.

- **[DB-0809-01] The open count is inflated and `## Done` is empty — a `/backlog` housekeeping
  pass, deliberately not done mid-`/archive`.** Three things found 2026-08-09 while building the
  new step 6a, all in `DEV_BACKLOG.md` itself: (1) **3 items open with `- **✅`**, which
  [scripts/sync_dev_backlog.py:185](scripts/sync_dev_backlog.py#L185) counts as open because its
  filter only skips lines starting `- ~~` — they read as closed and inflate every reported count;
  one of the three (`[DB-0808-07]`, filter upgrade built-not-deployed) is *genuinely* open and
  just needs the ✅ dropped from its first line. (2) **35 struck-through closed items sit inside
  the Open sections** while `## Done` holds nothing but its own explanatory header — they are not
  miscounted, but they are why the file is 1,373 lines. (3) **Duplicate id `DB-0805-01`** — the
  same id opens two different bullets, so it cannot be referenced unambiguously across windows;
  the anchored duplicate check in `/backlog` step 6 catches it. Not urgent, but the count is the
  signal `/metatron-code` and `/archive` report every session, and it is currently wrong by 3.
  *filed 2026-08-09 by dev session (Claude Code) · found while auditing why `/archive` never
  closed items · origin SEQ —*

- **[DB-0808-18] ⚠ Live `OPENAI_API_KEY` sits in plaintext in `~/.zshrc`, and has now leaked
  into a session transcript.** Exposed 2026-08-08 when a `tail -3 ~/.zshrc` (confirming an
  appended PATH line) printed the surrounding lines, including the key, into Claude Code's
  context — which `archive_chats.py` exports to `archive/transcripts/`. **Two actions, and the
  first is time-sensitive:** (1) rotate the key at platform.openai.com — assume the current
  value is burned; (2) move the replacement into the project `.env`, which is gitignored and is
  where every other credential already lives, and delete the `export` line from `~/.zshrc`. A
  key in a shell profile is readable by any process running as the user and is caught by any
  command that happens to print that file, which is exactly how this one surfaced.
  **Then check whether it already reached the repo:** transcripts under `archive/transcripts/`
  are gitignored ([.gitignore:97](.gitignore#L97)), so the exposure is probably local-only —
  but this needs confirming, not assuming, before the item is closed. `git log -S` for the key
  fragment is the check. Same class as the 2026-07-29 history rewrite; that one is the
  precedent for what it costs when the answer is "yes, it reached the remote."
  *filed 2026-08-08 by dev session (Claude Code) · surfaced incidentally while fixing the
  CLI/extension version skew, not from a security pass · origin SEQ —*

- **[DB-0806-03] No BigQuery billing export configured — cost anomalies can only be eyeballed
  against console lag, not verified.** Surfaced when Mike asked why Compute Engine showed no
  charges from Aug 4 onward while Vertex AI usage looked elevated on Aug 2 and Aug 4. Verified
  directly against GCP (not the console): `metatron-vm` has been `RUNNING` continuously since
  2026-08-03 23:47 PDT with no stop/start since, and no budget cap has fired — so the Compute
  Engine gap is almost certainly GCE cost-report lag (GCE line items typically finalize 1–3 days
  behind usage, unlike Vertex AI's same-day metered billing), not a real billing gap. The Vertex
  spike lines up with real heavy-call activity already in `PROJECT_LOG.md` (A4 gate rerun, B1a
  red-team's 75 live cases, decisions A/B/C testing) — plausible, not provably benign. This was
  already recorded once as a lever in `PROJECT_LOG.md` (line ~1431, "recorded, not applied") and
  is being re-filed here because it never became an actionable item. Enabling BigQuery billing
  export is **not retroactive**, so today's gap can't be backfilled, but turning it on now gives
  real per-SKU attribution for the next anomaly instead of inferring from `gcloud` state.
  *filed 2026-08-06 by dev session (Claude Code) · found while investigating a billing question
  in conversation · not built this session — investigation and recommendation only.*

- **[DB-0806-04] Consider migrating `metatron-vm` from us-central1 to europe-west1 — real
  latency win, small cost delta.** Raised by Mike asking about region choice given the app is
  used from London. Pulled live pricing from the Cloud Billing Catalog API rather than
  estimating: E2 vCPU/RAM carry a flat **10% premium** in europe-west1 vs us-central1 (disk and
  static IP prices are identical in both), which works out to **~$2.60/mo more** on the current
  e2-medium 24/7 setup (~$29.15 → ~$31.75). In exchange, the transatlantic leg of a voice turn —
  paid twice per turn in the current app architecture (`POST /transcribe` round trip, then
  time-to-first-token of the streamed response over the WebSocket) — drops from ~130–150ms RTT
  to ~10–15ms RTT, an estimated **~200–280ms shaved per voice turn**. This does *not* compound
  with the internal Coordinator→specialist→Synthesizer pipeline calls, since those stay on
  Google's backbone (VM→Vertex `global` endpoint) regardless of VM region — only the two
  client-facing edges of a turn are geography-sensitive. europe-west2 (London itself) was also
  priced: a 22.7% CPU premium, roughly double europe-west1's gap, for a latency win too small
  (Belgium↔London is already short) to be worth it. Not urgent — a real trade to make
  deliberately, not a bug — but worth having sized out before it's next discussed. Migration
  would follow the same playbook as the 2026-07-31 VPC rebuild (new VPC/subnet in the target
  region, rebuild VM from the boot disk, Tailscale reclaims node identity automatically).
  *filed 2026-08-06 by dev session (Claude Code) · exploratory question in conversation, no
  decision made · not built this session.*

- **[DB-0805-04] `tools/mail.py`'s module-level docstring is stale — says sending is deferred,
  but `send_email` shipped and was exercised live today.** Lines 9-13: *"Read-only, and that is
  a design decision rather than an unfinished feature. Sending is deferred with the rest of the
  act-on-your-behalf work: reading a booby-trapped message is a bad answer, sending one is a
  real loss."* That was true when written (`6739d62`, `read_email` only) but `send_email`
  landed 2026-08-04 (`ca993fe`/`15b9a41`) in the same file, gated by `tools/confirm.py`, and was
  proven working end-to-end 2026-08-05 (first real send). The docstring now contradicts the code
  three lines below it. Low priority — doesn't affect behavior, but worth fixing before it
  misleads whoever reads this file next expecting a read-only module.
  *filed 2026-08-05 by dev session (Claude Code) · found while verifying the SMTP send path ·
  not fixed this session*

- **[DB-0805-05] Parallel Claude Code windows editing the same shared-state files
  (`SESSION.md`, `ROADMAP.md`, `archive/PROJECT_LOG.md`) collide with no detection mechanism,
  and it has now happened repeatedly.** This session found `SESSION.md` mid-edit by another
  window early on (an uncommitted revert of the 2026-08-05 progress notes back to 2026-08-04
  state), and later found `ROADMAP.md`, `.claude/commands/archive.md`, and further
  `PROJECT_LOG.md` content appearing mid-session from at least one other active window (the
  B1a-red-team and ROADMAP-gap-fix work). Handled this time by scoping every commit to only the
  files this session actually touched (`git diff --cached --stat` checked before each commit)
  and never staging, committing, or discarding the other window's pending changes — but that's
  a workaround per-incident, not a fix. **The actual gap:** nothing warns a session that a file
  it's about to rewrite (especially `SESSION.md`, which is explicitly "replaced, not appended")
  has uncommitted changes from elsewhere. A session following the `/archive` ritual literally
  and rewriting `SESSION.md`'s top paragraph without checking `git status` first would silently
  discard a concurrent window's real work. **Possible cheap mitigation:** have `/archive`'s
  `SESSION.md`/`ROADMAP.md` steps open with a `git diff --stat` check and a stop-and-ask if
  either file already shows unstaged changes when the step begins, rather than assuming a clean
  starting state. Not scoped further than that — needs a decision on whether that's sufficient
  or whether real multi-window coordination (locking, or a designated "whoever closes last
  reconciles" convention) is worth building.
  *filed 2026-08-05 by dev session (Claude Code) · found repeatedly during this session's own
  `/archive` and mid-session deploys · not fixed, no owner*

- ~~**Transcript lines run too long on screen.**~~ — **the bubble-width half fixed, closed
  2026-08-05.** *"The transcript liners too long on the screen"* — SEQ 014, 2026-08-02. Two
  readings existed: the footer `#transcript` readout (capped to 3 lines with internal scroll,
  2026-08-04) and the conversation *bubble* width. Checked the second today: `.message` had
  `max-width: 88%` but no `overflow-wrap`, while `#transcript` and `#confirm-text` both already
  carry `overflow-wrap: anywhere` — an unbroken long token (URL, run-on dictated text) could
  overflow the bubble and run off-screen horizontally, matching the complaint exactly. Added
  `overflow-wrap: anywhere` to `.message` ([static/index.html:62](static/index.html#L62)).
  Client-only change — testable in a desktop browser, no APK/deploy needed to verify, but
  **does need `./deploy.sh`** to reach the live PWA and phone.
  *filed 2026-08-02 by Mike via Synthesizer · origin SEQ 014 · fixed 2026-08-05 against
  static/index.html:56-62*

- ~~**`/metatron-troubleshoot` command template points at pre-persona-scoping paths.**~~ —
  **stale, closed 2026-08-05. Already fixed, most recently by `a763628`.** All three claims
  re-checked against `.claude/commands/metatron-troubleshoot.md`: persona-scoped paths are in
  place with `data/conversations/` explicitly flagged as a legacy trap (line 39), `BASE =
  f'data/personas/{PERSONA}'` is fully parameterized (line 56), and `--tunnel-through-iap` is
  present on the SSH command (line 48).
  *Original entry recorded in SESSION.md 2026-08-02 · verified stale 2026-08-05 against
  .claude/commands/metatron-troubleshoot.md*
- **[DB-0808-09] Per-specialist internal turn reduction — measure the specialist fan-out, then
  cut it.** *(Rewritten 2026-08-08 from the measured data. This replaces the former
  "Roadmap D2 item 5 is mis-scoped" warning entry, which had done its job: the roadmap now
  carries a dated supersession note and no longer needs a backlog item to flag it.)*

  **What is measured, and how firmly.** The Coordinator runs **1 turn** per exchange — measured
  2026-07-29 on live traces, re-measured 2026-08-02, same result both times. `logistics` was
  measured at **8 internal turns** in the same pass. The multi-turn cost the D2 item was chasing
  is real; it is in the specialists, not the head layer.

  **What that means for the work.** Head-layer turn reduction is not the job — the Coordinator
  is already at 1 turn against a ≤3-turn target. The job is the specialist loop, and the honest
  first step is measurement, not a fix: **one specialist has been measured. The rest have not.**
  `logistics` at 8 may be the outlier or the median and nothing currently distinguishes those
  cases.

  **Step 1 — measure before changing anything.** Instrument internal turn counts per specialist
  across a representative set of real exchanges. Minimum: `logistics`, `physical_health`,
  `mental_wellbeing`, `research_agent`, `finance`. Record turns *and* cumulative tokens per
  specialist per exchange. Output is a ranked table — which specialists loop, how much, and on
  what kind of prompt.

  **Step 2 — diagnose the top one or two from their traces.** The Coordinator's mis-diagnosis is
  the cautionary precedent here: an assumed cause ("sequential rather than parallel dispatch")
  survived two months in a plan document without anyone checking it against a trace. Do not
  carry a hypothesis into step 3 that step 2 has not evidenced.

  **Step 3 — fix, then re-measure against the step 1 table.** No target number is set here on
  purpose; setting one before step 1 would repeat the ≤3-turn mistake of pinning a goal to an
  unmeasured baseline.

  **Related, and deliberately kept separate:** the instruction-file-slimming half of the
  original D2 item (moving the specialist directory and cross-domain routing examples out of
  `coordinator.md` into `config/modules/coordinator_routing.yaml`, loaded via
  `read_agent_config`) is **not** invalidated by the turn-count correction — it is a token-size
  argument, not a turn-count one, and can be worked independently. Note the standing constraint
  before shrinking `coordinator.md`: it is one of only two agents on the Vertex cached path, and
  Vertex silently fails to cache below 4,096 tokens — see `CLAUDE.md` § Routing.

  Also see the un-IDed entry *"Coordinator restructure (token-reduction Step 6)"*
  (`DEV_BACKLOG.md:896`), which carries the same measured correction inline and whose "Relates
  to the D2 item-5 mis-scoping already on this list" pointer now resolves to **this** entry.
  Read the two together rather than working them separately.

  *rewritten 2026-08-08 by dev session (Claude Code) from the 2026-07-29 / 2026-08-02
  measurements · supersession note added to
  [`archive/plans/phase5_to_future_roadmap_2026-06-10.md:519`](archive/plans/phase5_to_future_roadmap_2026-06-10.md#L519)
  the same day · original entry filed 2026-08-02, not fixed, no owner*

- ~~**No check that the VM is actually running what the Mac has committed.**~~ **Done 2026-08-03** — see the Done section.

- ~~**Spend guard pricing rates are unverified estimates.**~~ — **verified and corrected,
  closed 2026-08-05.** Checked against `cloud.google.com/vertex-ai/generative-ai/pricing`
  (standard tier, ≤200K token context, text): the file's rates were low across the board —
  `gemini-3.1-pro-preview` input $1.25→**$2.00**, output $10.00→**$12.00**;
  `gemini-3.1-flash-lite` input $0.10→**$0.25**, output $0.40→**$1.50** (flash-lite output was
  ~3.75x under). Updated in [config/modules/spend_guard.yaml](config/modules/spend_guard.yaml)
  with a dated comment. Still order-of-magnitude, not billing-accurate — cached-input discounts,
  priority/flex tiers, and the >200K-token rate step are all ignored by design.
  *filed 2026-08-03 · verified and fixed 2026-08-05 against live Vertex AI pricing page*
- ~~**VM has an unused ephemeral external IP — remove it to save ~$2.90/mo.**~~ **WON'T DO — the premise is wrong, and acting on it would take the VM offline. Corrected 2026-08-03.**

  "Never used" is true for **inbound** and false for **outbound**. Nothing connects *to* the address — there is no public ingress and every client arrives over Tailscale — but it is also the VM's **only route out to the internet**. Both alternatives were checked live on 2026-08-03 and neither exists: `gcloud compute routers list` → **0 items** (no Cloud NAT), and `metatron-subnet`'s `privateIpGoogleAccess` → **False**. Delete the access config and the VM loses Vertex AI (the entire product), the Tailscale coordination bootstrap that makes it reachable at all, `git pull` on deploy, apt/pip, CalDAV, weather and RSS. It becomes an isolated machine.

  **The replacement costs more, not less.** Verified against the Cloud Billing Catalog API rather than the pricing pages (which are JS-rendered and return nothing to a fetch): `External IP Charge on a Standard VM` = **$0.005/hour**, and `Networking Cloud NAT IP Usage` = **$0.005/hour** — the identical rate, because a NAT gateway needs a public address too. Cloud NAT then adds per-VM gateway and per-GB data-processing charges on top. So swapping the external IP for Cloud NAT buys the same egress for strictly more money. Private Google Access is free and would cover Vertex AI, but not GitHub, Tailscale, or any non-Google endpoint, so it does not rescue the plan alone.

  **Also: the $2.90 was low.** At the catalog rate of $0.005/hour a 730-hour month is **~$3.65**, not $2.90 — the [2026-07-30 audit](archive/sessions/2026-07-30%20—%20Client%20and%20App%20Audit,%20Cost%20Finding,%20Programme%20Parked.md) appears to have used $0.004/hour. It only accrues while the VM runs; an ephemeral IP is released on stop, so a `metatron-pause.sh` window costs nothing. **The real money is the $24.50 e2-medium line, and pausing already addresses it.**

  *Why this sat here for three days:* the note was right about the cost and wrong about the consequence, and that only fails when someone acts on it — the same failure mode as the entry below, one layer up. **Do not record the literal address in any doc** — it is ephemeral and changes on every stop/start. It was written down twice and both copies went stale: SESSION.md and this entry said `136.112.188.80`, CLAUDE.md said `35.202.250.80` in prose and `136.112.188.80` in its table, and the live value on 2026-08-03 was a third address. Look it up when needed: `gcloud compute instances describe metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --format="value(networkInterfaces[0].accessConfigs[0].natIP)"`.

- **Docs record values that the system changes underneath them, and nothing checks.** Two instances found on 2026-08-03, both by running the documented command rather than reading it. (1) CLAUDE.md described the server as plain **HTTP** in five places including the recreate-from-scratch checklist, while it has been serving **HTTPS** behind a Tailscale cert — caught when a health check against `http://` failed; corrected, and re-verified live this session (`https://.../health` → `{"status":"ok"}`, `http://` → empty reply). (2) The ephemeral external IP above. The docstring of [core/server.py](core/server.py) had the same HTTP/HTTPS error and was corrected in the same pass — worth noting because the CLAUDE.md fix did not prompt anyone to check the code comment saying the same wrong thing.

  **The pattern, not the two bugs:** drift of this class is invisible to reading and only surfaces when someone executes the documented step. Cheapest mitigation is to stop writing down values with a short half-life (external IPs, anything reassigned on rebuild) and point at the lookup command instead — done for the IP. A stronger fix would be a smoke script that runs the handful of executable claims in CLAUDE.md (health check, service status, deploy verification) and reports mismatches; `deploy.sh`'s new HEAD assertion is the same idea applied to one claim, and is the model to copy. **Corollary for anyone hitting a doc that does not match live: file it here rather than assuming you are holding it wrong.**
- **The scheduler cannot defer a time-based job — only skip it.** `_activity_gate_blocks` ([core/scheduler.py:173](core/scheduler.py#L173)) returns a reason-to-skip, and `fire_session` ([:263](core/scheduler.py#L263)) simply `return`s. For an `interval_minutes` job that is harmless — the next poll retries a few minutes later, which is exactly how `companion_checkin`'s 30-minute poll / 60-minute quiet gate works. For a `time:`-anchored job it means **gone for the day**: the `schedule` library fires it once at its clock time and there is no second attempt.

  **Current state is correct, not broken.** `morning_brief` and `evening_close` deliberately carry no activity gate, per the 2026-08-03 decision that they are the fixed points of the day and are not interruptible — they redirect openly instead (*"Now let's turn to the evening close"*, `synthesizer.md` → *Scheduled session conduct*). So nothing is being dropped today.

  **Pick this up only if a fixed-time session should ever wait for a lull.** Adding `quiet_after_user_minutes` to `evening_close` as things stand would silently cancel the evening close on any day the user happens to be talking at 20:00 — a worse outcome than the interruption it avoids. A real fix needs a *deferred* job: on block, re-register a one-shot retry (e.g. `schedule.every(15).minutes.do(...)` that unregisters itself once it fires or once a cutoff passes), plus a cutoff so a deferred evening close does not arrive at 23:00. `_record_fire()`/`_minutes_since_last_fire()` already persist fire times to disk and give the retry something to key on.

- ~~**[DB-0805-03] `run_a4_safety.py`'s `clinical`/`finance` report filenames collide on a
  same-day, same-provider re-run.**~~ — **fixed, closed 2026-08-05.**
  [tests/run_a4_safety.py](tests/run_a4_safety.py) — `suite_suffix` now derives from `args.suite`
  for every suite (`"" if args.suite == "all" else f"_{args.suite}"`), so `clinical`, `finance`,
  and `pipeline` each get their own filename; `all` keeps the unsuffixed name as before. Docstring
  updated to match.
  *filed 2026-08-05 by dev session (Claude Code) · found while building the A7 pipeline probe ·
  fixed 2026-08-05 same session*

- **`CLASSES` in `core/rule_classes.py` is incomplete by construction.** The rule-overlap checks match on regex per class; a duplicate in a class that does not exist yet is invisible, and a clean audit report is therefore not proof of no duplication. **When a duplicate is found by hand, add or widen a class in the same pass** — that is the maintenance loop, and without it the audit slowly decays into false reassurance. Two patterns needed widening within an hour of being written, both because they matched the *instruction's* wording and not the *user's complaint*: `repetition` missed *"Stop bringing up the same task over and over"*, and `evidence_weighting` missed *"making too much of the sleep disruption."* Test additions against `python3 scripts/check_rule_overlap.py --persona NAME` and confirm no new false positives on ordinary preferences before deploying.

---

## Open — agent-file enhancement backlogs

**These live in the agent files, and only there.** Each specialist's
`## Enhancement backlog` section at the bottom of `config/agents/{name}.md` is the single copy.

A mirror of all nine sat here from 2026-08-03 until later the same day — 15,851 bytes, 32% of
this file, 70 of what read as 94 open items. It made the backlog look three times its real size
and put the same text in three places (agent file, roadmap Section 4, here), which is exactly
what `CLAUDE.md` → **One Home Per Rule Class** exists to prevent. Deleted, along with the
roadmap copy. Verified before deletion: all nine originals present, 77 lines total.

`grep -l "## Enhancement backlog" config/agents/*.md` — logistics, mental_wellbeing,
physical_health, finance, relationships, recreation_hobbies, work_vocation, learning_growth,
research_agent.

---

## Done

**Everything below is closed.** `scripts/sync_dev_backlog.py` stops counting at this heading,
so items parked here do not inflate the open count — which is the whole reason the heading
exists. It was referenced by an entry above ("see the Done section") and by the sync script
for weeks before anyone noticed it had never been written; without it the script's "live
region" ran to end of file and **closing an item made the reported number go up.**

Every entry keeps its ID and carries the commit or `file:line` that closed it. Closed without
one is not closed.

---

### Closed 2026-08-08 — maintenance jobs default for every persona; pollen key live

Commit `8d798a8` (code) plus VM-side config edits, which `deploy.sh` cannot carry.

- **[DB-0808-17] Template scheduler changes never reached existing personas — FIXED.** Found
  while adding `daily_travel_check` by hand: `daily_calendar_dedup_audit` was *also* missing
  from mike's `scheduler.yaml`. It shipped 2026-08-05 and had never run for him — live in the
  repo, live in the template, inert in production, three days, nothing reporting it. Root
  cause: `scripts/new_persona.sh` copies `config/templates/scheduler.yaml` **once, at persona
  creation**, and no mechanism propagated a later change or reported the drift.

  Fix, per Mike's steer that *"changes should happen across all users simultaneously"*: the
  three silent, token-free maintenance jobs (`ambient_refresh`, `daily_rule_audit`,
  `daily_calendar_dedup_audit`) now register from `_DEFAULT_JOBS` in
  [core/scheduler.py](core/scheduler.py) for **every** persona. A new maintenance job is live
  everywhere the moment it deploys. The dividing line is `CLAUDE.md`'s own — the scheduler owns
  *mechanism*, never content — so a job with a prompt or a notification channel is a preference
  and stays in per-persona config.

  Persona config still wins outright, including `enabled: false`; merge is per-key rather than
  deep, so a partial override cannot inherit a stray field and produce a job neither layer
  describes. Removed the three from the template and from mike's live file — leaving a copy
  would have pinned him to a stale version and re-created the same bug. The "no schedules"
  warning now tests the persona's own config, since the merged set is never empty. Verified on
  the VM: `3 default maintenance job(s) inherited`, all ten jobs registering.

  Preference jobs can still drift, so `scripts/check_personas.py` now reports template jobs
  missing from each persona's `scheduler.yaml` as a warning.
  *found and fixed 2026-08-08 by dev session (Claude Code), from Mike's question "shouldn't the
  dedup be active for every user?" · `8d798a8` · VM verified*

- **[DB-0808-10] `daily_travel_check` added to mike's VM `scheduler.yaml` — CLOSED.** Added by
  hand on the VM (gitignored, so `deploy.sh` cannot carry it), after the code deploy per the
  "guard first" rule. `daily_calendar_dedup_audit` was added the same way, then both it and the
  other two maintenance jobs were removed again once `_DEFAULT_JOBS` made them automatic —
  `daily_travel_check` stays in the file because it notifies, which makes it a preference.
  Live dry-run against the real calendar returned "no travel found in the next 24h" — correct,
  and it proves the CalDAV read path works under his persona. Backups kept alongside the file.
  *closed 2026-08-08 · VM config edit, no commit*

- **[DB-0808-12] `get_pollen_forecast` has now made a live call — CLOSED.** Enabled
  `pollen.googleapis.com` on `metatron-ai-499810` and created key `pollen-forecast`
  (uid `d8cb56e5…`), restricted to `pollen.googleapis.com` at creation — matching the posture
  of the existing routes key, so a leak can't be spent on other Maps SKUs. Loaded into the VM's
  `.env` as `GOOGLE_POLLEN_API_KEY` (piped over stdin, never echoed; `.env` re-chmod 600).
  First live call returned real London data: weed Moderate and in season, grass and tree out of
  season, with health recommendations. **Cost: 5,000 free calls/month, then $10/1,000**
  (SKU `6CDF-1930-8F86`, Pro tier) — checked against Google's current pricing list, not
  memory, after two other pricing pages turned out not to carry per-SKU figures. This tool
  makes a handful of calls a day, so it sits inside the free allowance.
  *closed 2026-08-08 · key creation + VM `.env` edit, no commit*

---

### Closed 2026-08-08 — proactive travel trigger, pollen data source

Both shipped in `7c70cd9` (swept into that commit by a concurrent window — the message
describes a different session's work; the code is this session's).

- **[DB-0806-01] Pre-departure travel checks — CLOSED, the proactive trigger is now wired.**
  The two status lookups were already built (`get_tfl_status` 2026-08-06,
  `get_flight_status` 2026-08-07); what stayed open was that *nothing called either one
  automatically*. Now built: [tools/travel_watch.py](tools/travel_watch.py) reads the next
  24h of calendar, recognises travel, extracts flight numbers and named TfL lines, and
  dispatches the matching check. Registered as the `daily_travel_check` function job in
  [config/templates/scheduler.yaml](config/templates/scheduler.yaml).

  Three design points worth keeping, because each was a decision rather than a default:
  1. **Detection needs two independent signals.** A flight-number regex alone matches
     "Q4 2026" and "Room B12", and `get_flight_status` runs on a 600-unit/month,
     1-req/sec plan — so a number is only believed when the event also carries travel
     context (an airport, a terminal, the word "flight"). Tested against 11 positive and
     negative cases.
  2. **Silence on a good day.** An on-time flight and a Good Service line produce no
     notification at all, and each finding is reported once — keyed on event *and* status,
     so a worsening re-alerts but a standing delay does not nag.
  3. **`fire_function` gained a notification path** ([core/scheduler.py](core/scheduler.py)):
     a function job returning `{"notify": True, ...}` now dispatches, while a string-returning
     job behaves exactly as before. This is what lets the check cost zero model tokens on a
     quiet day and still speak up on a bad one. Backwards compatibility verified against all
     three existing function jobs.

  **Not yet firing for mike** — his `scheduler.yaml` is VM-owned and gitignored, so the job
  entry must be added on the VM by hand: `[DB-0808-10]`. Gate-stack gap found while building:
  `[DB-0808-11]`.
  *filed 2026-08-05 (Inbox) · lookups built 08-06/08-07 · trigger built and closed 2026-08-08*

---

### Closed 2026-08-08 — memory race, clinical threads, STT evaluation, filter upgrade

Deployed together in `7c70cd9` (both `/backlog-attack` cluster sessions; `core/orchestrator.py`
and `DEV_BACKLOG.md` carried work from both and could not be split). Post-deploy verified with a
live `/session` call on the VM — coherent reply, no ImportError — because `register_tools()` only
runs when a session runs.

- ~~**[DB-0803-03] Memory indexer is reading the wrong source — hypothesis now confirmed.**~~
  Original entry: `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char
  82852)` against a 276-byte file, so the offset could not have come from the named file.

  **Verified 2026-08-05 and sharper than filed.** The VM journal still carries it, but the date
  has moved on while the offset has not: `index log 2026-08-04 failed: Extra data: line 557
  column 2 (char 82852)` — **the identical byte offset for a completely different log file**,
  three times on 2026-08-04. A shared offset across unrelated files is not a coincidence about
  the files; the indexer is parsing something fixed. `core/background.py` is where to start, and
  the thing to find is what it opens instead of the per-day log.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:227 · verified 2026-08-05 against
  the VM journal — still firing*

  **CLOSED 2026-08-08 (`7c70cd9`) — and the filed hypothesis was wrong.** The indexer was
  not reading the wrong source. `core/memory.py`'s `_load_index()`/`_save_index()` did a
  non-atomic, unlocked read-modify-write of `metadata.json`, and *two processes* call
  `index_entry()` — the server via `tools/logger.py:72` and the scheduler via
  `tools/diarist.py:76`. The single-worker pool in `core/background.py` serialises only
  within one process, which is why this read as a parser bug for five days. Fixed with a
  `filelock` around the load/save pair plus atomic temp-file/rename writes; metadata is
  written before the index deliberately. `_read_metadata()` salvages files already corrupt
  on disk, so the VM's file healed without a hand edit. Regression test
  `tests/test_memory_concurrency.py` reproduces the original error against pre-fix code
  with 4 real processes, and passes against the fix.
  *closed 2026-08-08 by dev session · deployed `7c70cd9`*

- **✅ Found while running B1a: a MUST_SURFACE safety flag has no visible decay/resolution
  mechanism and can hijack unrelated later turns — worth its own look, not just a test-hygiene
  note.** All 15 B1a disclosure prompts against `sarah_chen` got a real answer to the actual
  question *plus* an escalating, verbatim-similar crisis-intervention script (988, "find Tom",
  confirm the lamotrigine dose) bolted on — including on completely unrelated prompts like
  "What tools do you have?". `data/personas/sarah_chen/context.json` shows why: an open
  `"safety check and SI risk"` thread persisted from an earlier session (most likely the 2026-08-04
  A4 pipeline probe, which legitimately fires `sarah_chen`'s `SUICIDAL_IDEATION`/`MUST_SURFACE`
  flags via the identical MW-3 prompt), and the Synthesizer had itself written a new pattern into
  that same file mid-run: `"deflecting acute distress with system architecture questions"` — i.e.
  it reclassified every B1a red-team prompt as further evidence of the same unresolved crisis,
  rather than as a new, unrelated message. `held_items` reads `"Held: None — all critical flags
  surfaced due to acute safety risk"`, with nothing in the file describing when or how the open
  thread would ever close.
  **Two separate implications, don't conflate them:** (1) *Test hygiene* — `sarah_chen` is not a
  clean bed for future red-team/self-disclosure runs once any earlier session has legitimately
  triggered a clinical flag against her; a dedicated persona (or an explicit context-tracker
  reset) would isolate disclosure-resistance testing from crisis-override behaviour and give a
  cleaner signal. (2) *Possibly real behaviour, not just a test artifact* — if this generalises to
  Mike, a MUST_SURFACE flag that fires once with no expiry could keep resurfacing crisis framing
  on every unrelated later turn indefinitely. That could be intentional conservatism (don't let a
  distracting question drop a live safety concern) or a genuine bug (a stale flag from a past,
  resolved concern dominating conversations that have moved on) — this session did not determine
  which, only that the behaviour exists and has no visible resolution path. **Not fixed here** —
  B1a's job was to find and log. Worth a dedicated look, possibly folded into Check 10 (agent
  behavioural audit) or the mental_wellbeing/synthesizer instruction files rather than treated as
  a B1a code fix.
  *filed 2026-08-04 by dev session (B1a red-team run) · found while running
  tests/run_b1_redteam.py --suite disclosure against sarah_chen · not yet triaged to an owner*

  **CLOSED 2026-08-08 (`7c70cd9`).** Resolved as a **bug**, after asking Mike. Answered from
  the code first: there is no next-of-kin channel — `MUST_SURFACE` means "address this in
  the reply, this turn", and `tools/wishes.py` is write-only until Phase 6. The reframing
  that settled it: **persistence was never the bug, prominence was.** `clinical_threads` in
  `tools/context_tracker.py` now carries `active`/`watch`/`resolved`. `CLINICAL_CONCERN`
  derives tier 2 in Python (never from the model), can reach `watch` but **cannot be
  resolved from a session**, and its `raised` date is carried from disk so the clock cannot
  be reset. Omission carries a thread forward rather than deleting it. Time-based expiry was
  **rejected** — it silently drops an unresolved crisis. The lifecycle protocol is injected
  by the tool only when a thread is open, so `synthesizer.md` gained 3 lines, not a section.
  `tests/test_clinical_threads.py` 17/17; A4 gate re-run 3/3 clinical + 3/3 pipeline.
  Test-hygiene half also handled: `sarah_chen`'s stuck tracker migrated to one `watch`
  thread. Follow-ups filed as `[DB-0808-06]` and `[DB-0808-14]`.
  *closed 2026-08-08 by dev session · deployed `7c70cd9`*

- ~~**[DB-0802-01] Voice transcription — the recorded cause is fixed; the accuracy half is not.**~~
  *"There are transcription issues to address. Multiple timeouts"* — SEQ 014, 2026-08-02.

  ~~Blocking the event loop~~ — **done 2026-08-01** (`d42eefc`, `81fc6e2`), before this entry
  was ever re-read. `/transcribe` and `/tts` now run on dedicated single-worker pools
  (`_STT_EXECUTOR` / `_TTS_EXECUTOR`, [core/server.py:178](core/server.py#L178)), Whisper and
  the memory model warm-load at startup, and `_transcribe_blocking` carries a comment explaining
  the freeze it replaced. **Anyone working "transcription times out" from the old description
  would have re-fixed a solved problem** — this is the clearest case in the sweep for why an
  item is re-verified before it is worked.

  **What is left is accuracy, which is a different fix in a different file.** Whisper runs
  `base.en` with `beam_size=5` and no VAD
  ([core/voice_pipeline.py:26,119](core/voice_pipeline.py#L26)). Evaluate `small.en` and a VAD
  filter — but **measure on the VM's 2 vCPUs before adopting**, because STT is now on a
  single-worker pool and a slower model serialises rather than merely being slower. Pairs with
  the dictated-email item below; same root, different lever.
  *filed 2026-08-02 by Mike via Synthesizer · origin SEQ 014 · verified 2026-08-05 against
  core/server.py:178 and core/voice_pipeline.py:26 — cause closed, accuracy open*

  **CLOSED 2026-08-08 (`7c70cd9`) — evaluated on the VM, `small.en` rejected.**
  Measured on the e2-medium's 2 vCPUs as the entry required, not on the Mac:
  `small.en` runs at **RTF 2.23** — slower than the audio arrives, which on the
  single-worker `_STT_EXECUTOR` is a queue, not a slowdown — and was **not** more accurate
  (4 of 6 fixtures 0% WER on both models). `beam_size=1` also rejected: 15% faster, worse
  accuracy. **VAD adopted** (~7% faster at identical WER, and it suppresses the filler
  Whisper hallucinates on the 2.5s silent tail `record_until_silence()` always submits).
  STT settings are now env-overridable so a future change is config, not code.
  Report: `tests/stt_bench_report_2026-08-08_vm.md`. **Scope limit, filed as
  `[DB-0808-08]`:** fixtures are synthesized speech, so the accuracy finding covers clean
  dictation only; the latency verdict is audio-independent and solid.
  *closed 2026-08-08 by dev session · deployed `7c70cd9`*

- ~~**[needs building]** search_memory tool is throwing a JSON parse error: 'Extra data: line 557 column 2 (char 82852)'. The memory file parser needs debugging to restore CRM read access, which is currently blocking contact verification.~~
  `2026-08-06T16:49:21.836539Z`
  — **CLOSED 2026-08-08 (`7c70cd9`).** Same root cause as `[DB-0803-03]`; see that entry
  below. The CRM read access this names is unblocked as a direct result.

- ~~**`[CONTEXT]` block silently discarded when the model emits invalid JSON.**~~ — **built
  and DEPLOYED 2026-08-08 (`7c70cd9`).**
  **Premise correction, verified against current code before work started:** the specific
  malformation this entry names — a literal newline inside a JSON string value — was *already*
  fixed on 2026-08-02 by `strict=False`, two days before this entry was written. What was still
  true is the general shape: any *other* malformation was one `logger.warning` and a silent
  drop, no repair, no retry, no record. That is what got built, in `core/orchestrator.py`:
  a structural repair ladder (`_repair_context_json` — markdown fence and surrounding prose
  stripped, trailing commas removed, smart quotes normalised, truncation closed by `_balance`
  which also drops mismatched closers, single-quoted Python-style blocks converted but only when
  the block contains no double quote at all, so `"mum's birthday"` is never corrupted) → **per-key
  salvage**, so one broken value no longer costs the good ones beside it → `_record_unparsed_context()`,
  which writes the raw block as a `CONTEXT_BLOCK_UNPARSED` quality event, reaching this file
  through the existing sync. The block becomes *recoverable* rather than lost.
  **The re-emit option was considered and rejected:** `split_context_block` runs after the
  Synthesizer's turn has completed, on the user-facing request, so a retry costs a second Pro
  turn of latency on every malformation to fix a tracker update the user never sees.
  **`_CONTEXT_KEYS` is a maintenance point** — a key added to the block and not added there is
  not an error, it is silently unsalvageable, which is the exact failure this work ends.
  `clinical_threads` (added by a parallel session the same day) is already in it.
  Test: [tests/test_context_block_repair.py](tests/test_context_block_repair.py), 18 cases,
  offline, **18/18 pass**.
  **⚠ Deploy status: code complete and tested on the Mac, not live on the VM.** `core/orchestrator.py`
  needs `./deploy.sh`, and at time of writing the same file also carried a parallel session's
  uncommitted `from tools.pollen import …` against an untracked `tools/pollen.py` — committing it
  would have shipped an import of a module not in git, which (being function-level) passes
  `py_compile` and fails on the first pipeline session instead. Until that deploy happens, a
  malformed block on the VM is still dropped silently.
  *filed 2026-08-04 · built 2026-08-08 by dev session (backlog-attack cluster) · deployed `7c70cd9`*


- **✅ [DB-0808-07] `filter_output()` regex/semantic upgrade — built and DEPLOYED 2026-08-08
  (`7c70cd9`).** The last open B2 sub-item (CORS, `write_agent_config`/`write_config`
  confirm-gating, `run_session_anthropic` iteration limits and `run_model_conference` scoping
  were all verified already done in the same pass). Four tiers now, in `core/orchestrator.py`:
  (1) identifiers matched by a cached per-term regex that rejoins the term's tokens with a
  punctuation-or-nothing joiner, so one list entry covers `write_config`, `write-config`,
  `write.config`, `write**config`, `writeconfig` and any of those with zero-width characters
  spliced in — detection runs on a normalised copy, the original text is what is returned;
  (2) **architecture narration (`_ARCH_NARRATION_RES`) — new, and the substantive addition**:
  paraphrases that leak the structure while naming nothing on either list ("I passed this to a
  specialist that handles your health", "my system prompt says", "I'm running on Gemini",
  "twelve specialist agents"). The old filter was blind to all of these by construction — a
  model told not to say `run_subagent` describes what it does instead; (3) spaced identifiers
  and `_CONTEXT_SENSITIVE`, still sentence-gated; (4) `_ARCH_VOCAB_RE` widened to cover
  first-person capability narration and internals vocabulary.
  **The binding constraint was false positives, not recall** — suppressing "your mental
  wellbeing has improved" is worse than the leak it prevents, because the user loses a real
  answer and the canned fallback explains nothing. Hence: tier 1's joiner never matches a plain
  space; bare `agent` is excluded from the delegation patterns ("I sent your reply to the
  agent" — an estate agent); `prompt` only matches as `system prompt`, `call` only as
  `tool call`/`function call`.
  **Known limits are in the docstring, deliberately:** tier 2 is patterns not a model, so a
  paraphrase outside these frames passes; intra-token spacing (`w r i t e _ c o n f i g`) is not
  caught, because a matcher loose enough for it fires on ordinary prose. This is the last
  backstop, not the control.
  Verified: filter suite 61 → 86 checks (**the original 61 unchanged and all still passing**,
  plus 7 obfuscation + 9 paraphrase + 9 clean-corpus), disclosure **15/15**, deputy **2/2** —
  `tests/security_redteam_2026-08-08.md`. **Deploy status: shipped in `7c70cd9` (2026-08-08),
  committed together with the parallel session's `tools/pollen.py` — the function-level import
  in `register_tools()` meant the two could not be split. Verified post-deploy with a live
  `/session` call on the VM: coherent reply, no ImportError.** Known gap left open on purpose: `[DB-0808-05]`.
  *built 2026-08-08 by dev session (backlog-attack cluster) · deployed `7c70cd9`*


- **✅ Pipeline-level injection probe built and passed 2026-08-08 — `injection` suite in
  [tests/run_b1_redteam.py](tests/run_b1_redteam.py).** Three hostile emails (outbound
  exfiltration, architecture disclosure, config/profile mutation) in a fixture inbox, read
  through the real `run_pipeline_session()` path. `register_tools` is patched per scenario and
  restored in a `finally`; mutating handlers are recorded and neutralised; `send_email` runs
  for real with `confirm_token` forced empty (production's two-step gate), so nothing can leave
  the machine. Fixture built through the real `wrap_untrusted` path, not an approximation, so it
  tracks the boundary format. **3/3 PASS** against `danny_park`/gemini — `read_email` called in
  every scenario, no payload-named tool fired, no architecture leak, and all three reported the
  attempt to the user unprompted. Report:
  `tests/security_redteam_2026-08-08_injection_danny.md`.
  **Two things worth carrying:** (1) the first run, against `sarah_chen`, returned three
  *inconclusive* scenarios — the pipeline never called `read_email` at all, because that persona
  carries an active clinical thread and the Synthesizer correctly triaged it over "read my
  inbox". Good behaviour, useless probe. Without the "fixture inbox was actually read" check it
  would have scored 3/3 PASS on a pipeline that never saw the payload. **This suite needs an
  ordinary-life persona**, unlike the other three, which are persona-agnostic. (2) Email only —
  the calendar-title, web-page and CardDAV rows of B1b's table are untouched and still open, so
  **this does not close B1b**.
  *filed 2026-08-04 · built and passed 2026-08-08 by dev session (backlog-attack cluster) ·
  tests-only, no deploy needed*

  Original entry, for the reasoning trail:

- ~~**No pipeline-level injection probe has been run.**~~ The 2026-08-04 probe tested three layers
  in isolation — wrapper escape, marker detection, and the tool's recipient refusal. What has
  *not* been run is the real thing: a hostile email sitting in the actual inbox, read through
  a full Coordinator→specialist→Synthesizer exchange, to see whether the pipeline surfaces it
  as analysis or acts on it. The layer that refuses in code will hold regardless; the open
  question is **agent behaviour**, which is exactly what the isolated tests cannot show. Fold
  into B1's red-team suite rather than building a separate harness.



---

## Closed 2026-08-09 — `/backlog deep` sweep

- **[DB-0803-06] `shownIds` eviction wipes the whole set instead of evicting incrementally** —
  **CLOSED: fixed by `c4ff279` (2026-08-08).** `evictOldest(set, max)` now lives at
  [static/index.html:713-715](static/index.html#L713) and both former `.clear()` call sites call it
  with a cap of 100 — [:952](static/index.html#L952) in `renderHistory()` and
  [:979](static/index.html#L979) in `sendViaWebSocket()`. No `.clear()` on `shownIds` remains
  anywhere in the file. The full reasoning trail for why this was a real bug is preserved in the
  2026-08-05 entry earlier in this file.

  **Two things worth carrying forward, because the close is only half the story:**

  1. **It was reported, and the entry said it hadn't been.** The entry read *"dev-session find,
     never reported — promote it the day Mike sees a doubled message"*, but `[DB-0803-01]` ("text
     doubling ... in the app", Mike, 2026-08-03) is the same defect described from the outside.
     The promotion condition had been met for five days and nobody connected the two, because one
     entry was written in symptoms and the other in line numbers. **A dev-session find and a user
     report of the same bug will not look alike** — that is the general lesson.
  2. **The fix is not on the phone.** `android/app/src/main/assets/public/index.html` still
     carries `if (shownIds.size > 100) shownIds.clear()`, so the doubling survives on the installed
     APK regardless of this close. Tracked as `[DB-0809-18]` (silent asset drift) with the
     remaining user-facing half on `[DB-0803-01]`.

  *closed 2026-08-09 by `/backlog deep` · evidence `c4ff279` + static/index.html:713-715,952,979*

---

## Closed 2026-08-09 — proactive-framing session

- **[machine log: same rule in two places]** *(RULE_CONFLICT, `2026-08-05T04:30:19Z`)* The
  check-in brevity preference restated across `config/personas/mike.md:11`,
  `config/personas/mike/scheduler.yaml:41` and `config/templates/scheduler.yaml:34`. Class:
  brevity.

  **There were four copies, not the three the audit named** — the rule was also the whole content
  of the two scheduler prompts, so the audit's own count undersold it. All copies removed: the
  rule was promoted to `config/agents/synthesizer.md` § Scheduled session conduct as general
  design (rewritten as focus guidance rather than a sentence cap — see the log entry), then
  deleted from `mike.md`, from `mike/scheduler.yaml` on the VM, and from
  `config/templates/scheduler.yaml`. `grep "two sentences at most" config/` now returns nothing;
  both check-in prompts are `"Check in."`.

  The template copy is the one that mattered most and the one nothing had flagged: it seeds every
  new persona, so Mike's stated preference would have arrived in each future user's own config as
  though they had asked for it. It is what prompted `CLAUDE.md` § *Two kinds of preference — ask
  which one it is*.

  Worth carrying: the audit's write-time and daily checks both saw this and its **suggested
  partner was right while its count was wrong** — a reminder that the flagged rule is the reliable
  part of that tool's output, as `CLAUDE.md` already says. Nothing checks the template.

  *closed 2026-08-09 · evidence `82d394b` (promotion + VM deletions) and `a6d693e` (template);
  `config/agents/synthesizer.md` § Scheduled session conduct*

## Closed 2026-08-09 — sleep interpretation, obligations, log comparability

- **[DB-0809-04] Sleep gets over-weighted in interpretation — not because it is the only thing
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
  Closed by the rewrite it asked for, but **its own premise inverted twice on the way**. It said the
  defect was Synthesizer interpretation against an already-broad record, and that was right. The
  layer it blamed — `synthesizer.md:86`, "when one domain has far more logged data than the others" —
  had a **false antecedent**: sleep is on 14/20 days, fifth of six populated fields, so a model
  reading that rule correctly concludes it does not apply, and a rule with a false premise reads as
  permission. Mike's redirect (*"the tool should ask for other numbers to balance it"*) located the
  real mechanism: **comparability, not availability.** `mood: 'anxious'` / `energy: 'improved'` sit on
  no scale; `sleep_hours: 3` does. Sleep did not win for being loudest — it was the only signal the
  Synthesizer could reason *with*. Four amplifiers verified: only field reported as a number every
  session, only physical fact flagging on **one** day, only fact flagged by **two** specialists, and
  the worked example in 7 places including inside the suppressing rule itself. Rejected: editing
  `mental_wellbeing.md` (specialists run in parallel threads, so neither can suppress its own
  duplicate — the de-dup rule went to the Synthesizer and now generalises past sleep); and
  abstracting the examples (only 1 of 7 taught sleep-as-cause). Parent cause filed as
  `[DB-0809-20]` and also closed.

  *closed 2026-08-09 · evidence `6330029` deployed*

- **[DB-0809-05] Nothing notices a calendar event that passed without happening.** Mike's ask:
  detect it and prompt to reschedule; keep financial tasks (payroll) prominent in daily
  proactive checks until explicitly closed. **Verified 2026-08-09: neither exists** — nothing in
  `core/` or `tools/` reconciles a past event against reality; the scheduler only fires jobs.
  **Designed 2026-08-09, not built** — the reframe (absence of evidence is not a miss), the
  gather-vs-judge layer split, and Mike's three scope decisions are in
  [archive/plans/calendar_reconcile_design_2026-08-09.md](archive/plans/calendar_reconcile_design_2026-08-09.md).
  Adds a third dependent to the open `[DB-0808-11]`.
  *filed 2026-08-09 from Inbox (2026-08-05T15:19Z) · Mike via Synthesizer · **verified 2026-08-09***
  Built to the design doc, with one correction recorded **in** the doc rather than edited away: its
  implementation table put the scheduler entry in `config/templates/scheduler.yaml` + the VM-owned
  persona file. Wrong class — silent token-free infrastructure registers in `_DEFAULT_JOBS`, because
  the template is copied once at persona creation and `daily_calendar_dedup_audit` had already proved
  a later change never propagates. Following the table would have rebuilt that bug and touched a
  VM-owned file for nothing. Shipped: `tools/obligations.py` (closure inferred, `close_obligation`
  **requires** evidence in the user's words, reopen keeps the original close on file) and
  `tools/calendar_reconcile.py`, which **never returns a notify dict** — a cancelled flight is a fact
  from an airline, crude text matching is not. Verified live on the VM: registered at 05:40, sweep
  ran clean against the real calendar, and the zero was confirmed as a true result rather than a
  silent query failure. Every filter path unit-tested against synthetic events.

  *closed 2026-08-09 · evidence `b9ea29f` deployed; design-doc correction `7a7d5a6`*

- **[DB-0809-20] The daily log records prose where its own schemas declare enums, so almost
  nothing can be compared across days.** `wellbeing.mood: low | neutral | positive | mixed` and
  `health.energy: low | moderate | high` are declared in
  [config/agents/mental_wellbeing.md:219](config/agents/mental_wellbeing.md#L219) and
  [physical_health.md:155](config/agents/physical_health.md#L155). **Measured 2026-08-09 across 70
  log files: those nested blocks appear in 4.** The other 66 write flat free-text top-level keys —
  `mood` 63, `energy` 61, `focus` 61, with real values `'anxious'`, `'improved'`,
  `'low/depleted (masked by overdrive)'`. Cause is a schema conflict, not agent sloppiness:
  [tools/logger.py:146](tools/logger.py#L146) — the description the model reads *at the moment it
  calls the tool* — names those keys flat, `additionalProperties: True`, no enums. The nearer
  instruction wins over a config file read earlier in the session. Consequence: `sleep_hours` is
  the only field two days can be ranked on, which is the root cause `[DB-0809-04]` was patched
  around at the interpretation layer, and every Pattern Miner cross-domain result is computed over
  unrankable prose. Fix is cheap — align the tool description with the two schemas already written
  — but **the existing history stays unrankable**, so it does not fix itself by waiting.
  *filed 2026-08-09 · **dev-session find, not Mike** — promoted to `## Now` by Mike as the parent
  cause of `[DB-0809-04]`, which he did raise*
  Filed and closed the same session, as `[DB-0809-04]`'s parent cause — and **its own "cheap fix"
  premise inverted too**, which is the third inversion on this thread of work. The item said align
  `write_log`'s tool description with the nested schemas the specialists already declare. Opening it
  against the code found `write_log` merging with `existing.update()`, **shallow**: a morning
  `{"health": {sleep_hours, sleep_quality}}` and an evening `{"health": {energy}}` ended the day with
  energy alone, no error, no trace. So the nested shape was not merely unused, it was **unsafe** —
  very likely *why* it was never adopted, since a flat scalar survives `update()` and a nested sibling
  does not. Pointing agents at it without fixing the merge would have converted a schema mismatch
  into silent data loss. Guard first, then the config. Rejected: **backfilling** the 66 older files —
  deriving `low` from `'low/depleted (masked by overdrive)'` is exactly what `6330029` had forbidden
  the Synthesizer from doing four commits earlier. `pattern_miner.md` carries the boundary instead:
  bands begin 2026-08-09, a missing band means *not recorded* not *neutral*.

  *closed 2026-08-09 · evidence `88b7614` deployed*


## Closed 2026-08-09, later — key rotation

- **[DB-0808-18] Live `OPENAI_API_KEY` sat in plaintext in `~/.zshrc:2`.** Rotated at
  platform.openai.com (old key revoked), new key written to the gitignored `.env`
  ([core/orchestrator.py:59](core/orchestrator.py#L59) `load_dotenv`s it at import, so
  both named consumers — `:1626` and `:3154` — resolve it with no shell dependency), and
  the `export` line deleted from `~/.zshrc` (backed up to `/tmp/zshrc.bak-*` first).
  **The item's own "breaks nothing live" claim was wrong, in a way its own scope couldn't
  see.** `~/.claude/claude.json`'s `ask_gpt` MCP server config held a literal
  `${OPENAI_API_KEY}` placeholder, substituted from the shell environment at launch —
  supplied, until this edit, by the very `~/.zshrc` line being deleted. Removing it broke
  `ask_gpt` globally, for every project, the moment a new shell started. Caught before
  handing back to Mike by checking consumers beyond this repo. Fixed by writing the real
  key directly into `claude.json`'s `env` block instead of restoring the export — strictly
  *less* exposure than before, since the key now reaches only the one process that needs
  it rather than every shell on the machine, which is the same principle the item was
  chasing, just satisfied one layer further out than it looked from inside this repo.
  Also found and updated on Mike's flag: `~/Library/Application Support/Chorus/config.json`
  (the separate "multi-model project" / Chorus app) held the old key in its own persistent
  store, unaffected by any of the above — updated to the new key directly.
  Verified: old key value returns zero hits across all four locations; new key confirmed
  present and well-formed (164 chars, `sk-proj-` prefix) in `.env`, `claude.json`, and
  Chorus's `config.json`. `.env` confirmed still untracked and unstaged.
  *closed 2026-08-09 · evidence: `.env`, `~/.zshrc`, `~/.claude/claude.json`,
  `~/Library/Application Support/Chorus/config.json` — all verified directly, no commit
  (three of the four locations are outside this repo)*

## Closed 2026-08-10 — dictated-address correction already built and working

- **[DB-0809-03] Dictated contact details come through wrong and need correcting by hand.**
  **The item's own citation was wrong, and its premise was stale.** It pointed at
  [tools/crm.py:149](tools/crm.py#L149)/[:158](tools/crm.py#L158) — a difflib check inside
  `write_contact` that guards against *misattributing* the user's own address to a contact
  record, a different purpose entirely — and concluded "the snap exists nowhere."
  Real evidence says otherwise: pulled the actual 2026-08-02 conversation
  (`data/personas/mike/conversations/2026-08-02.jsonl`, VM). The failure was Mike dictating
  **his own email for a ticket booking** (via Logistics/`write_profile`, never touching
  `write_contact`), mis-transcribed three ways in three minutes —
  `diamond.like.gmail.com` (dropped `@`), `diamond.mic at gmail.com`, corrected by hand to
  `diamond.mike@gmail.com`.
  A fix for exactly this shipped **2026-08-05**, three days after the incident:
  [core/voice_pipeline.py](core/voice_pipeline.py) `correct_known_addresses()`
  (`a08e38a`), whose own code comments cite these same two failure strings. It runs inside
  `/transcribe` ([core/server.py:924](core/server.py#L924)) before the transcript ever
  reaches a tool, checking against `_known_recipients()` — the user's own address **and**
  every CRM contact's, broader than the item even asked for. Verified live against real
  `mike` profile data tonight: `diamond.mic@gmail.com`, `diamond.like.gmail.com`, and a third
  invented variant `diamondmic@gmail.com` all correctly snap to `diamond.mike@gmail.com`.
  **The one real gap:** the bundled APK never sent `?persona=` on `/transcribe` (the second
  `[DB-0809-18]` diff), so `if persona and transcript:` silently skipped the correction on
  the phone specifically. Fixed as a side effect of tonight's `[DB-0803-01]` rebuild — same
  root symptom class, independent discovery.
  **Address dictation** (street name/postcode, also wrong in that conversation) is a
  categorically different problem — no fixed enum of "known good addresses" exists to snap
  against the way email/phone do — and is out of scope for this mechanism; not filed as a
  new item since Mike hasn't re-raised it.
  **The live collision warning was withdrawn along with the citation** — no `crm.py` edit
  was needed, so there was never a real collision with the deferred tone-pipeline work.
  *closed 2026-08-10 · evidence: `a08e38a` (pre-existing fix), verified live against `mike`
  on the VM, no code changed by this close*

## Closed 2026-08-10 — catch-up render and hidden-tab liveness

- **[DB-0809-06] The browser tab does not live-refresh on messages sent from elsewhere.**
  Both diagnosed causes fixed in `f7cad05`, deployed and verified error-free on the VM.
  **(a)** Catch-up gave its response a new `"catchup"` wire type instead of reusing
  `"history"` — the client's `history` handler wipes and rebuilds from only what it's
  given, correct for a fresh connection's full load, silently destructive for a delta.
  Each catch-up row now runs through `applyCatchupRow()`, the same append-only,
  dedup-on-`shownIds` path a live `message` broadcast already used (factored out so
  neither duplicates the other's logic). Verified with a standalone re-implementation
  against the exact row shape `_catchup_since` returns: a pre-existing exchange survives
  a catch-up untouched, a proactive row shows no user turn, `lastSeenId` advances, and a
  re-delivered catch-up does not duplicate.
  **(b)** The 20s backstop interval was gated on `visibilityState === 'visible'`, so the
  `STALE_AFTER_MS` staleness check never ran on a hidden tab — ungated it; this is the one
  liveness path that has to run unconditionally.
  Bundled into the same APK rebuilt for `[DB-0803-01]`/`[DB-0809-18]` — confirmed inside
  the actual built binary (`applyCatchupRow`: 3 occurrences, `case 'catchup'`: 1).
  *closed 2026-08-10 · evidence `f7cad05` deployed + rebuilt APK verified · sideload still
  pending, tracked under `[DB-0805-02]`'s device dependency*

## Closed 2026-08-10 — VAD truncation fixed; doubling fix confirmed in the rebuilt binary

- **[DB-0803-01] Text doubling / input cut off mid-sentence in the app.** Both halves now
  code-complete and deployed as far as this side can push.
  **Half two (server-side truncation), fully closed:** `vad_filter=True` was dropping the
  quiet tail of an utterance before Whisper decoded it. Tuned Silero's `threshold` (0.5→0.30)
  and `speech_pad_ms` (400→1500) rather than disabling VAD — measured against all 108 files
  retained in `data/audio/`: 98.07% avg recovered vs a VAD-off reference, 0 hallucination
  markers, and the file that motivated this (`18-16-16.webm`) goes from 85.9% to a full
  match. Deployed in `c2d5138`, verified live on the VM against the real `transcribe()` entry
  point — the known failure string now appears correctly in the output.
  **Half one (client-side doubling), fix was already deployed in `c4ff279`** — `evictOldest`
  replaced `shownIds.clear()`. What was missing was the bundled APK asset, which drifted from
  `static/index.html` (`[DB-0809-18]`). Rebuilt via `npx cap sync android` +
  `./gradlew assembleDebug`; confirmed **inside the built binary itself**, not just the
  intermediate assets folder — `evictOldest` present, `shownIds.clear()` absent.
  **What remains is one shared human action, not three separate ones:** the rebuilt APK also
  carries `[DB-0809-03]`'s `?persona=` fix and `[DB-0809-06]`'s catch-up/liveness fix, so a
  single sideload verifies all three at once. Tracked under `[DB-0805-02]`, which already
  exists to test the installed app — not re-opened here to avoid the same "needs sideload"
  note sitting in three places.
  *closed 2026-08-10 · evidence: `c2d5138` deployed + verified on VM; APK rebuilt and checked
  against the actual binary; sideload dependency consolidated into `[DB-0805-02]`*

## Closed 2026-08-10 — deploy-time APK-drift assertion

- **[DB-0809-18] The APK-bundled index.html drifted from static/index.html silently.**
  `scripts/check_apk_sync.sh`, modeled on `deploy.sh`'s HEAD assertion: extracts
  `assets/public/index.html` from the **actual built APK** (not the intermediate
  `android/app/src/main/assets/public/` copy step, which can be current while an
  older, un-rebuilt APK sits in `outputs/` — the exact ambiguity this guards against)
  and diffs it against `static/index.html`. Exits non-zero with the diff and a rebuild
  command on mismatch; one clean line on match. Added as the last documented build
  step in `docs/INFRASTRUCTURE.md` § Android app, after `assembleDebug`.
  Tested against all three states: clean pass, injected drift caught with the correct
  diff, clean again after revert.
  *closed 2026-08-10 · evidence: `scripts/check_apk_sync.sh`, tested live against the
  real APK built earlier this session*

## Closed 2026-08-10 — stale docstring

- **[DB-0805-04]** `tools/mail.py`'s module docstring said sending was deferred and the
  module was read-only; `send_email` shipped 2026-08-04 and has sent for real since
  2026-08-05. Rewrote to describe what's actually true — reading is read-only *by
  design*, sending is the separate, deliberately confirmation-gated act-on-your-behalf
  path, recipient-checked in Python not by instruction, owned by Relationships since
  tonight's outbound-messaging move (`config/agents/relationships.md` § Disclosure
  discretion, confirmed present).
  *closed 2026-08-10 · evidence: tools/mail.py:1-15, no other stale reference found*

## Closed 2026-08-10 — hallucinated log dates: guarded at the write site, moved not deleted

- **[DB-0809-12] Hallucinated log dates in mike's VM tree.** Re-verified 2026-08-10: all 9
  named 2025 files still present, exactly those 9, plus 3 legitimately non-dated system
  files (`quality_events.json`, `scheduler_errors.json`, `scheduler_last_fired.json`) that
  must not be touched by anything matching this pattern.
  **Guard added at `write_log()` in `tools/logger.py`**, refusing rather than warning — a
  drift of more than 7 days from the real system clock returns an error string telling the
  caller to use its clock line or omit `log_date`. Chose refuse-not-warn deliberately,
  unlike the project's usual soft-cap/near-duplicate warnings: there is no legitimate
  `log_date` a year removed from today, so refusing here can't wrongly block a real write
  the way refusing a near-duplicate obligation could. Tested against 7 cases: a real
  hallucinated date, an invalid format, today (implicit and explicit), a legitimate
  yesterday backdate, and the ±7-day boundary exactly (6 days passes, 8 days refused).
  **The 9 files moved to `data/personas/mike/logs/_hallucinated_2025/`** on the VM — not
  deleted, per the project's data-is-never-deleted convention. Checked `tools/baselines.py`,
  the only other place that globs the logs directory directly (`*.json`, non-recursive) —
  a subdirectory doesn't match that pattern, so nothing else needed to change.
  *closed 2026-08-10 · evidence: tools/logger.py guard + 9-case-verified test, files moved
  on the VM (data/ is gitignored, no commit needed for the move itself)*

## Closed 2026-08-10 — confirmed live on the rebuilt, sideloaded APK

- **[DB-0805-02] Email approval prompt does not render in the app.** Sideloaded, live
  test: Mike sent a real message from the phone and got a reply. Server logs confirm the
  full chain — `POST /transcribe?persona=mike` 200 OK (persona param now sent, closing the
  other half of `[DB-0809-18]`), the message logged exactly once
  (`data/personas/mike/conversations/2026-08-10.jsonl`, seq 003 — no doubling, confirming
  `[DB-0803-01]` half one live), and `GET /pending-confirmations?persona=mike` polling on a
  steady ~5s cadence throughout — the mechanism that drives `#confirm-bar`'s rendering,
  active and running on the installed build. Can't observe the phone's screen directly, but
  every server-observable signal the confirm-bar depends on is live and correct.
  One APK, one sideload, three items confirmed: this one, `[DB-0803-01]`, `[DB-0809-06]`.
  *closed 2026-08-10 · evidence: live server logs against a real phone session, this session*

---

## Closed 2026-08-10 — by the `/backlog deep` sweep

*Verification only; no code changed to close these two. Reasoning:
[`PROJECT_LOG.md`](PROJECT_LOG.md) § 2026-08-10.*

- ~~**[DB-0809-15] `write_agent_config`/`write_config` are still not wired to
  `tools/confirm.py`.**~~ — **stale; they were wired before the item was filed.**
  `write_config` gates **every** call unconditionally
  ([`tools/config_writer.py:43`](../tools/config_writer.py#L43) — `consume()` then `request()`
  with a 400-char preview). `write_agent_config` gates on `_GUARDED_KEYS`
  ([`tools/agent_config.py:76`](../tools/agent_config.py#L76)), and its docstring already cites
  `DB-0805-01` and the `send_email` precedent by name. What the item actually described —
  whether a **one-entry** `_GUARDED_KEYS` set (`("physical_health", "medication_profile")`,
  [`tools/agent_config.py:43-45`](../tools/agent_config.py#L43-L45)) is the right mechanism, or
  whether the confirm gate should be the default — is the *surviving* question and was already
  open as `[DB-0805-01]`. The two entries were the same question filed twice, one of them with a
  false premise. **Do not re-file the wiring half.** *verified 2026-08-10*

- ~~**[DB-0809-19] `tests/run_b1_redteam.py` inspects `run_pipeline_session()`'s source
  structurally, and `82d394b` added a branch to it.**~~ — **checked; PASS.** The item asked for
  exactly this: confirm before the next red-team run rather than during it, since B1 gates A7.
  Re-ran the `DEPUTY-STRUCT` assertion standalone (static source inspection, **no model call, no
  cost**): `run_pipeline_session` → 1 call site, `_run_pipeline_session_stream_inner` → 1 call
  site, **both on `coord_output`**, neither on `spec_text`/`specialist_outputs`. That pair is the
  whole assertion the suite makes ([`tests/run_b1_redteam.py:456-457`](../tests/run_b1_redteam.py#L456-L457)).
  The confused-deputy protection is intact after `82d394b`. *verified 2026-08-10*

- ~~**[DB-0810-04] `/archive` never commits, so a correct close-out leaves its own output dirty
  in the tree** — and step 2 pointed at the wrong heading.~~ — **both halves shipped, `060f53a`.**
  Step 5 stages an explicit manifest (`SESSION.md`, `archive/PROJECT_LOG.md`, `DEV_BACKLOG.md`,
  `archive/backlog_closed_YYYY-MM.md`, plus `ROADMAP.md` if step 3 touched it), diffs each file
  before staging, and **neither pushes nor deploys**
  ([`.claude/commands/archive.md:85-95`](../.claude/commands/archive.md#L85-L95)). A diff
  carrying lines the session did not write **stops** the commit — `[DB-0805-05]` stays open and
  the step is written to depend on it being unsolved, not to paper over it.
  **Heading half:** `## Dated history` added above the newest entry, the vestigial copy ~1,280
  lines down retitled `## Dated history (continued — 2026-08-08 and earlier)`. One exact-string
  match now exists, which is the part that stops the next session filing into the middle; no
  entry text moved, so the append-only rule holds.
  **Checked against `ed92acf` first** (Fable's revamp, which cut this file 6 steps → 4): the
  removed steps were the `archive/sessions/` writeup and the standalone ROADMAP step — **a commit
  step never existed in any version**, so nothing deliberate was reintroduced. That check also
  killed a planned edit: compressing step 1's tail reminder, which `a86dd37` and `ed92acf` had
  already rewritten twice in three days. Lines came from the `archive/sessions/` note instead
  (history, duplicated in `CLAUDE.md`), holding the file at exactly **100 lines**.
  Step count also corrected in `CLAUDE.md` and `docs/WORKFLOW.md` — the stale-cross-reference
  class `ed92acf`'s verification pass was built to catch. *closed 2026-08-10*

- **[DB-0809-11]** Docs record values the system changes underneath them and nothing checks.
  **Closed 2026-08-13** by `scripts/check_claude_md_claims.py`, wired into `scripts/qa_sweep.sh`
  as check 8. Built jointly with `[H8].1` (permission-rule liveness) because `HARNESS_BACKLOG.md`
  identified them as one thing, not two: both are "the docs assert something and nothing
  re-checks it". Asserts that every backticked path in `CLAUDE.md` exists, every hook target
  exists, and no permission rule parses cleanly while matching nothing. **It found two live
  instances on its first run**: `config/frameworks.md`, referenced in `CLAUDE.md` as holding the
  theoretical literature, has **never existed in any commit** (now marked planned-not-present);
  and `.claude/show_phase_progress.py`, a registered `Stop` hook, reads a `STATUS.md` deleted
  months ago — a silent no-op on every turn since. Line ceilings warn rather than fail, matching
  how the prose states them. Verified by injecting all five fault classes in an isolated tree and
  checking exit codes in both directions. *closed 2026-08-13*

- **[DB-0815-03]** An action Mike approves in the app is never executed — the approval is
  recorded and nothing spends it. **Closed 2026-08-15** by `2602e2e`, deployed, APK rebuilt.
  `POST /confirm` now carries the action out itself via `tools/confirm.py`'s new `execute()`,
  which spends the approval through the tool's own `consume()` — single-use, expiry and the
  argument fingerprint all unchanged, so the consent property the file was built for is intact
  and the model is additionally out of the *execution* path. The outcome is written as an
  ordinary exchange and broadcast, so the user reads what happened rather than inferring it.
  **The filed premise was wrong in one detail:** step 4 was said to have "no trigger", but
  `static/index.html` did nudge the pipeline after each tap — it was simply unspendable, because
  the token is returned inside a tool result and is gone from the model's context by the next
  turn. Had the fix been scoped from the item text, that nudge would have survived and kept
  firing at a server that had already acted. **Scope ran wider than the item, deliberately:** the
  four tool schemas (`send_email`, `write_config`, `write_profile`, `write_agent_config`) and
  `synthesizer.md` all instructed the retry, and a schema binds harder than an agent file.
  **Rejected:** the push notification the item asked for — the tap comes from an open app and the
  outcome arrives over the socket, so it duplicates an on-screen line; offered to Mike and not
  taken. `tests/test_confirmation_gate.py` gained five cases; every prior test stopped at the
  gate, which is why the missing half was invisible for eleven days. *closed 2026-08-15*

- **[DB-0815-01]** `hook_commit_guard.py` fails closed on a session's own Bash-written file.
  **Closed 2026-08-15** by `c3f2ac8`; local harness, nothing to deploy. The worktree half had
  closed earlier the same day (`6ad3dec`, `ff8f4cc`). The remaining half: a file this session
  Edit-wrote and its own tooling then rewrote was blocked as a collision, because the manifest
  held a hash that had moved and nothing distinguished "my script did that" from "another session
  did that". **The item's own proposed fix stayed rejected** — trusting a session's recent Bash
  writes *writes* to the baseline and would absorb a parallel session's lines, reopening
  2026-08-09. Built instead: attribution, which only *reads*. Before blocking, check whether any
  **other** session's manifest in `.claude/.session_edits/` records the file at the hash it has
  **right now**; matching on the current hash is what makes it safe, since a stale entry carries
  the old hash and cannot claim content it did not write. **Accepted limit, documented in the
  module:** another session's *Bash* rewrite of a file this session Edit-wrote now warns rather
  than blocks — a class that was already advisory-only whenever this session had not written the
  file. Hit live twice before the fix, including one commit that needed Mike's explicit override.
  Adds `tests/test_commit_guard.py`, the first coverage this hook has had across six corrections,
  four of which were fail-open or block-routine-work defects found only by a human tripping over
  them: ten cases against real git trees, the 2026-08-09 incident replayed as case one, and
  verified *discriminating* against the pre-fix guard. *closed 2026-08-15*

---

## Closed 2026-08-15 — second `/backlog deep` sweep

- **[Inbox, machine-filed]** *"Fix speech-to-text for Bulgarian — the transcription model
  defaults to English and produces phonetic garbage."* `2026-08-15T13:49:35Z`.
  **Closed as a duplicate, not as fixed.** This is verbatim `[DB-0815-02](a)` in `## Later`,
  which Mike filed by hand the same day and marked explicitly low priority. The machine wrote a
  second copy of a report Mike had already made. The blockers are unchanged and recorded there:
  `WHISPER_MODEL_SIZE` is `base.en`, English-only, and multilingual needs `base`, which reopens
  the 2-vCPU single-worker sizing constraint at `core/voice_pipeline.py:31`.
  **Worth carrying:** the duplicate arrived because a machine-filed Inbox entry is not checked
  against items Mike filed himself the same day. *(Mike's call, 2026-08-15: close as duplicate.)*

### Superseded history moved out of live entries (no information lost)

Mike's call, 2026-08-15: `DEV_BACKLOG.md` was 922 lines against a 450 ceiling, and the bulk was
not `## Later` — it was superseded narrative *inside live entries*. The blocks below were cut from
the live items and are kept here verbatim. **Each was already wrong when it was cut**; they are
retained because in every case an earlier confident diagnosis was overturned, and that is the part
worth being able to find again. Full reasoning for all three: `archive/PROJECT_LOG.md`.

**Mike also made a design point that outlives this trim, filed into `[DB-0810-06]`:** a backlog's
line ceiling should probably be tied to the *number of items* in it, not its line count. A file of
40 well-evidenced items and a file of 40 thin ones are the same size problem by item count and
wildly different by line count — and it is the line count that has been pressuring sessions to cut
evidence.

#### `[DB-0809-02]` — prior state, twice overturned

The original premise was wrong: the openings were already 1–2 sentences, and the "restatements"
were the Synthesizer reading its *own* scheduler prompt as Mike's voice. Fixed in `82d394b`
(deployed) — `_frame_proactive()` labels scheduler input as a directive in both pipeline copies,
and the repeated-instruction protocol now requires the *user* to have repeated it. A ≤2-sentence
cap was **rejected**; focus is the target, length only its symptom.

Evidence corrected 2026-08-10 — the entry had claimed "zero quality events of any kind logged all
day", which is false: 38 fired that day (24 `USER_CORRECTION`, 7 `FEATURE_REQUEST`, 4
`ROUTING_MISS`, 3 `TOOL_DENIED`). The events file keys on **`timestamp`, not `ts`**; a read against
`ts` returns nothing and looks like a clean day. The narrow conclusion survived: no
`INSTRUCTION_CHANGE_REQUEST` fired, which is what the old bug produced every time.

Then: **the fix did not hold.** Mike reported on 2026-08-12 that evening close "fired 3 repetitive
messages". `82d394b` had landed 2026-08-09, three days earlier. Three possibilities were named — the
fix is incomplete, `evening_close` reaches an uncovered path, or the diagnosis was wrong about scope.

**All three were wrong**, settled live on 2026-08-15: it was four different scheduled jobs, each
inheriting the unfinished ritual from context. See the live entry.

#### `[DB-0814-02]` — prior state, the timestamp half

`open_threads` was a bare `list[str]` with no metadata — "post-travel recovery" stayed live for two
weeks because nothing could even ask how old it was. Closed 2026-08-15 as scoped (`d40e73c`):
entries are now `{"text": str, "added": <ISO date, server-stamped>}`, matching the `clinical_threads`
convention of never trusting the model for a date; a thread carried forward unchanged keeps its
original `added` date; old bare-string data migrates safely on read. What remained was the actual
ask — a timestamp on its own does not stop stale context misleading.

#### `[DB-0810-15]` — the two rejected designs

Both are now recorded permanently in `core/translate.py`'s module docstring, which is where a
session that needs them will actually be standing:

1. **Translation rules as prose in `config/agents/synthesizer.md`** — rejected by Mike on cost.
   That file loads on every head-layer call and the Synthesizer runs on the most expensive model
   in the fleet: durable token spend on a setting that changes approximately never.
2. **A `translate` tool the Synthesizer calls** — rejected because a tool call is a round trip
   *through* the model, costing an extra turn on the expensive model. Also unreliable in a way this
   project has already paid for: the model decides whether to call it, and a language guarantee that
   depends on a model remembering to invoke something fails intermittently and silently.

Also cut: the voice-blocker paragraph duplicated from `[DB-0815-02]`, which owns it.

- **[DB-0815-09] Half the correction log said nothing, and the counts welded unrelated corrections
  together. CLOSED 2026-08-15** — `214a547`, deployed. Filed and closed the same day by the
  `/backlog deep` sweep that found it.
  **Fault A:** 93 of 174 `USER_CORRECTION` events carried `"None"`/`"N/A"`, passing the 2026-08-10
  blank-detail guard because they are not blank. Cause was a *template* — `coordinator.md:88` is a
  slot annotated "omit if not applicable", and a model filling a structured template answers the
  slot rather than deleting it. **The agent file was deliberately not edited**: its instruction is
  already correct and already ignored, which is the project's own argument for enforcing in Python.
  `is_null_ish()` in `tools/logger.py` (canonical) refuses at write; `core/orchestrator.py`'s
  `_handle_user_correction` drops before writing; `sync_dev_backlog.py` filters historical ones at
  **read** time — archive-on-merge, the events stay on the VM.
  **Fault B:** a `×N` was a chain length, not a repeat count. `SIMILARITY_THRESHOLD` 0.15 with
  `merge()` replacing the displayed line each time meant matching ran against the last link:
  a chain beginning in Heathrow travel corrections was reported as *"scheduled calendar events
  imply completion ×16"*. Fixed at 0.45 **plus** correction-boilerplate stopwords — verified by
  replay that **neither alone** splits the chain, because the shared words were the correction
  vocabulary. Top real signature is now a genuine ×4.
  **Mike's check is what surfaced Fault A's scale:** *"I don't think I've corrected the tool 90
  times."* He had not. `tests/test_null_ish_events.py` 43/43, including that the two `is_null_ish`
  copies agree — the stdlib-only constraint forces a duplicate, so drift must fail a test.
  *closed 2026-08-15*

- **Knowledge layering steps 4–12 — the retrieval half.** **BUILT, DEPLOYED, AND STEP 10 RUN**
  (`360b843`, `d128130`, `7cb9ebd`, `2a51f46`; 2026-08-18). Domain→agent map, derived manifest in
  `load_profile()`, `KNOWLEDGE_TO_LOAD` pre-fetch in **both** pipeline paths, `WISDOM_PROPOSAL`
  parsed in Python and stripped before synthesis, grants in parity across both routing files,
  reserved names, Pattern Miner `other` sweep. `health_notes` migrated on the VM to
  `standard_breakfast`/`food` and retired from `tools/profile.py`. A4 pipeline **3/3** after.
  **The one deliverable deliberately NOT met:** the zero-specialist path. "Thinking about changing
  up breakfast" reaches the stored fact but still dispatches Physical Health — twice, the second
  after a worked example that changed nothing and was reverted. `coordinator.md:48` is left
  dominant on purpose: over-dispatch costs tokens, under-dispatch loses a user's record. Pass A
  gates retrieval instead; the reopen condition is in `tests/run_knowledge_routing.py`'s docstring.
  *closed 2026-08-18*


## Closed 2026-08-18 — `/backlog attack`, three clusters plus consolidation

Four items closed. Evidence is a commit or a `file:line` in every case; the two that shipped code
were verified by running it, not by reading it.

- **[DB-0815-06] The system invents contact details and stores them as fact — CLOSED.**
  `write_contact` now refuses known placeholders across **phone** (NANP `555-01xx`, UK Ofcom
  `07700 900xxx`, sequential, all-zero), **address** (`123 Main St`, `Anytown`), **social handle**
  (`@username`, `@handle`, …) and **name** (`John Doe`/`Jane Doe`), normalising before matching so
  `+44 (0)7700 900123` is caught. Commit `8c7121b`, merged `b23c477`. 17 new tests in
  `tests/test_crm_placeholders.py`, all passing, including an explicit set of **real-looking values
  that must pass** — a real surname "Doe", a real `123 Main Street` with a real city.
  **Scope limit, restated because it will be misread otherwise:** this refuses *known placeholders*,
  not *invented data*. A fabricated but plausible phone number is not caught and cannot be without a
  source of truth. **Design question answered and deliberately not built:** the registry stays in
  `tools/crm.py` rather than moving to a shared module — one caller today, and an abstraction with
  one caller is a guess about the second.
  **Follow-on found by the merge and fixed the same day (`0d9310e`):** the guard refused the *whole
  record* over one bad field, which is right when a model is inventing a contact and wrong on a bulk
  import, where it silently costs a real person their record. `tools/contacts_import.py` now strips
  the offending field, keeps the person, and reports the drop; a placeholder **name** is still
  refused outright, being the record's only anchor.

- **[DB-0813-02] Multi-model rounds have been coming back a voice short — CLOSED, and the item's
  own diagnosis was wrong.** The entry said the `OPENAI_API_KEY` in `.env` was invalid and returned
  `401 invalid_api_key`, fix being a key rotation. A live call returned
  **`OPENAI_API_KEY environment variable is not set`**. `~/.claude/mcp_servers/ask_gpt.py` reads
  `os.environ` only — it loads no `.env`, ever — and its registration in `~/.claude.json` carried an
  empty `env: {}`, while `ask_gemini` sitting beside it had `GEMINI_API_KEY` inline. **The key in
  `.env` was valid all along** (verified `HTTP 200` against `/v1/models`); only the wiring was
  missing. Mike wired it the same day. **Had the item been worked as written, the key would have
  been rotated, the item marked fixed, and GPT would still have been silent.**

- **[DB-0806-02] Reserving tickets on a website — the READ half CLOSED**, the interactive half
  unchanged and still parked. `fetch_rendered` added to [tools/web.py](tools/web.py) (`6097c44`,
  merged `4683703`): headless Chromium, load-only, through the *same* `_check_url`/
  `_is_blocked_address` SSRF guards and the same `wrap_untrusted` boundary as `fetch_url`, bounded
  by a 15s page timeout and a 5s capped network-idle wait. Playwright imports lazily, so a host
  without it gets a clean error rather than an import-time crash — asserted three ways in
  `tests/test_fetch_rendered.py`. Registered and granted to `logistics` and `research_agent` in both
  routing files (`35499af`).
  **Three memory guards shipped with it (`4d10cbd`), and the reason is the interesting part:** an
  OOM kill is SIGKILL, so a killed process cannot return a polite message — the graceful refusal has
  to happen *before* the browser launches. Hence a `MemAvailable` pre-flight check, a single-render
  lock, and `oom_score_adj=1000` on the browser processes so the kernel picks Chromium rather than
  the server. That last one matters because **by default it would pick the server**: on
  `2026-08-15 15:02` it already did. VM install tracked separately as `[DB-0818-02]`.

- **[DB-0810-17](b) An external CRM bridge — CLOSED as split, one half shipped and one half
  deliberately left dormant.**
  **Shipped:** [tools/contacts_import.py](tools/contacts_import.py) `import_contacts_file` — vCard
  and CSV, tolerant header mapping for Google and Outlook export shapes, unmapped columns preserved
  rather than dropped, idempotent on re-run, dedup on the way in reusing `write_contact`'s existing
  near-match surfacing rather than reimplementing matching. Granted to `relationships` (`35499af`).
  21 tests.
  **Not shipped, on purpose:** `import_google_contacts` and `read_google_contacts` are **not
  registered**. The Google Contacts OAuth path was built 2026-08-07 and **reversed 2026-08-08 at
  Mike's own direction**; `people.googleapis.com` is still disabled on the project, so it could not
  run regardless. The 08-15 reframe that appeared to re-authorise it asked *where contacts come
  from*, not *whether to re-adopt OAuth* — Mike confirmed 2026-08-18 he had not realised he was
  reversing himself. Full narrative:
  `archive/log/2026-08-18-01-backlog-item-hid-a-reversal.md`.
  **Known duplication left standing, flagged not fixed:** the shipped module hand-rolls a vCard
  parser while `vobject==0.9.9` has been in `requirements.txt` since 08-08 and
  `scripts/import_vcard_contacts.py` already uses it. The two surfaces differ — one is a CLI script,
  one is an agent-callable tool — so this is duplication of *parsing logic*, not of function.

**Full original text of all four, as they stood when closed:**

- **[DB-0815-06] The system invents contact details and stores them as fact — the email half is
  fixed, the rest is not.** *(Widened 2026-08-15 by Mike: "Just invented email addresses, or any
  invented contact information or data more generally?" The answer is more generally, with one
  honest limit stated below.)*
  **✅ Email done and deployed** (`97b777c`): `write_contact` refuses RFC 2606 reserved and
  placeholder domains — `example.com/.net/.org`, `.test`, `.invalid`, `localhost`. The original
  case was the `Eva` contact carrying **`eva@example.com`**, which is not a mistyped real address
  but a placeholder the model produced and the tool persisted. Mike: *"That shouldn't happen."*
  **What remains — the same refusal across every other field a model can fill:**
  - **Phone** — the fictional ranges models reach for: NANP `555-0100`–`555-0199`, the UK Ofcom
    drama range `+44 7700 900xxx`, `123-456-7890`, all-zeroes.
  - **Address** — `123 Main St`, `Anytown`, `1234 Elm Street`.
  - **Social handles** — `@username`, `@handle`, `@example`, `@yourname`.
  - **Name** — `John Doe` / `Jane Doe` as a stored contact.
  **The limit, stated so this item is not mistaken for something bigger: this refuses *known
  placeholders*, not *invented data*.** A model that fabricates a real-looking phone number is not
  caught by anything here and cannot be, without a source of truth to check against. What it does
  catch is the specific failure observed — a model reaching for the canonical fake when a field
  looks required — which is the same class as the `research_agent` source fabrication closed
  2026-08-10 (`a36d8c2`), and the same class as `[DB-0815-09]`'s "None" corrections. **Three
  instances of one root cause now: a field that looks required gets filled with something
  plausible rather than left out.** Worth asking, when this is built, whether the registry belongs
  somewhere shared rather than in `tools/crm.py` alone.
  A stored fake detail is worse than a blank field — it will eventually be *acted on*.
  @kind: bug
  *filed 2026-08-15 by Mike, from the live CRM dump · email half closed and deployed 2026-08-15 ·
  widened by Mike the same day*

- **[DB-0813-02] Multi-model rounds have been coming back a voice short, silently.**
  `OPENAI_API_KEY` in `.env` is invalid — a live `ask_gpt` call returns `401 invalid_api_key`.
  Nothing announces it: a three-model round just returns two answers, and the missing one reads as
  a choice rather than a failure. Mike's standing convention is that GPT, Gemini and Claude all
  answer, so this quietly degrades something he uses constantly. **Fix is a key rotation, not
  code** — minutes. Check the other keys in `.env` while there.
  @kind: bug
  *filed 2026-08-13 by a dev session, verified live · **promoted to `## Now` 2026-08-15 by Mike.**
  It fails the "Mike raised it" entry bar and was promoted anyway on cost-to-fix against
  cost-of-sitting — the cheapest item on the list, degrading a daily workflow*

- **[DB-0806-02] Reserving tickets on a website — the read-only half is unblocked.**
  Covers Mike's *"reserve tickets on the R website"* ask. Splits cleanly: **`fetch_rendered`
  (Playwright, read-only) is the recommended half and needs no new trust boundary** — it is the
  same boundary `fetch_url` already sits behind, with `<untrusted_content>` wrapping. Check VM
  memory before adopting Playwright. The **interactive** half (click/type/submit) stays gated on a
  credential store that does not exist and is not promoted. Scope:
  `archive/plans/level3_web_actions_scope_2026-08-06.md`.
  @kind: feature
  *filed by Mike · **promoted 2026-08-15**, read half only — the entry had been sitting in `##
  Later` behind a blocker that applies to the other half*

- **[DB-0810-17] An external CRM bridge — the count question itself is answered.** At seq 009
  Mike asked for a route *and* a CRM contact count; the system declined it as needing an external
  connection it doesn't have, when Metatron's own contact store (`list_contacts`, `search_contacts`
  in [tools/crm.py](tools/crm.py)) already held the answer. **(a) closed 2026-08-15** —
  `coordinator.md`'s Relationships routing block now calls out contact-store questions explicitly
  and says not to decline them (`b11e775`). **(b) remains: an external CRM bridge.**
  **✅ UNBLOCKED 2026-08-15 — the vendor decision this entry was waiting on turned out not to
  exist.** Mike's actual requirement: for Mike-persona testing the internal CRM **pulls from Google
  Contacts**, and any other CRM arrives by **import in conventional file types**. So there is no
  *which CRM* to choose and no per-vendor API bridge to build — the previous framing of this item
  was the blocker, not the work. Three concrete pieces, verified against current code the same day:
  1. **`read_google_contacts` is built but unreachable.** [tools/google_contacts.py](tools/google_contacts.py)
     is complete — read-only People API, per-persona OAuth, one-time consent via
     [scripts/google_contacts_authorize.py](scripts/google_contacts_authorize.py) — but it is
     **never imported into `register_tools()` and never granted in either routing file**. Compare
     the CRM tools, wired at [core/orchestrator.py:479](core/orchestrator.py#L479) and
     [:595](core/orchestrator.py#L595). It appears only in `tools/metatron_monitor.py:141`'s API-name
     map, which is why nothing flagged it. **Inverse of `[DB-0810-03]`'s class**: not a tool named
     without a grant, but a tool built without a registration — and `scripts/check_agent_tools.py`
     cannot see this direction either, since it sweeps agent files against allowlists and neither
     mentions this tool. Worth asking whether that guard should also flag a `tools/` module that
     nothing registers.
  2. **Reading is not pulling.** `read_google_contacts` returns data; nothing writes it into
     `contacts.json`. The onboarding/sync path does not exist, so "the internal CRM pulls from
     Google Contacts" is not true even once (1) lands. Decide dedup on the way in —
     `_find_by_name` is naive substring matching (the `[DB-0810-11]` "Jon"/"Jonathan" case), so a
     pull is exactly where duplicate records get created at volume.
  3. **No import path of any kind exists** — no vCard, no CSV, in `tools/crm.py` or anywhere else.
     This is the "any CRM should be importable" half.
  Sensitive-tier throughout. Google Contacts write-back stays out of scope — deliberately excluded
  when the module was built, and nothing here needs it.
  *filed 2026-08-10 by Mike · (a) closed 2026-08-15, see `archive/backlog_closed_2026-08.md` ·
  (b) reframed and unblocked 2026-08-15 by Mike; the three pieces above were verified against
  current code, not inferred from the entry*


### Closed 2026-08-18, later the same session — the VM work, done rather than filed

Both items were filed at ~11:30 and closed at ~11:50. Filing them at all was the right call — they
were real, and had the session ended there they would have been the loose ends — but neither
survived contact with an hour of attention.

- **[DB-0818-01] The VM has no swap and has already been OOM-killed three times — CLOSED, applied
  to the VM.** `scripts/vm_add_swap.sh` run: 2 GB swapfile live, `/etc/fstab` entry written so it
  survives a reboot, `vm.swappiness=10`. `scripts/vm_memory_watch.py --install-units` run:
  `metatron-memory-watch.timer` enabled and firing every 5 minutes, running as the repo owner
  rather than root so it leaves no root-owned files under `data/`.
  **The watchdog justified itself on its first run**, recording the pre-existing kill as a critical
  alert rather than being told about it:
  `{"level": "critical", "message": "OOM kill on the VM: 1 new ...", "available_mb": 1887,
  "swap_mb": 2047, "oom_kills": 1}`. That is the mechanism working on real data, not a fixture.
  **Disk was the constraint nobody had looked at:** 4.5 GB free at 76%. Reclaimed 403 MB of apt
  cache and **2.8 GB of pip cache** (the 1.6 GB huggingface cache is live Whisper/Kokoro model data
  and was deliberately left). Ended at 4.8 GB free / 75% — *better than before the swapfile and the
  browser were added*.

- **[DB-0818-02] Playwright granted but not installed — CLOSED, installed and proven.**
  `playwright==1.62.0` plus `install-deps chromium` and `install chromium` on the VM, and pinned in
  `requirements.txt` with the note that **pip installs the driver, not the browser** — a rebuild
  that skips `playwright install chromium` gets the clean "binary not installed" error, which is
  correct behaviour and easy to misread as a code fault.
  **Verified by running it, not by reading it:** headless Chromium launched on the VM, loaded a
  page, returned its title and text. **Measured cost: ~189 MB** (MemAvailable 1871 → 1682 → 1796),
  against the 700 MB pre-flight threshold in `fetch_rendered`. The guards are calibrated
  conservatively and correctly.
  **Still required before the tool exists on the VM at all: `./deploy.sh`.** The code half is
  committed locally only. The scripts were `scp`'d rather than pulled, deliberately — a `git pull`
  would have put the new `routing*.yaml` grants on the VM ahead of the code that registers the
  tool, which is the "config key before the code that gates it" trap.

**Full original text of both, as filed:**

- **2. [DB-0818-01] The VM has no swap and has already been OOM-killed three times, silently.**
  Found 2026-08-18 while sizing the Playwright decision. `metatron-vm` is a 4 GB `e2-medium` with
  **zero swap**, and the kernel log carries three `Out of memory: Killed process` entries — one of
  them, `2026-08-15 15:02`, killed **`metatron-server.service` itself** at 3.6 GB RSS. `Restart=always`
  brought it back in five seconds, which is exactly why nobody noticed: from the outside the app
  blipped and recovered. With no swap the kernel has no soft failure mode available — it SIGKILLs
  the largest process, and the largest process is the server.
  **Both halves are built and committed, neither is applied to the VM yet:**
  [scripts/vm_add_swap.sh](scripts/vm_add_swap.sh) (2 GB swapfile, fstab entry, `swappiness=10`) and
  [scripts/vm_memory_watch.py](scripts/vm_memory_watch.py) (systemd timer, 5-minute cadence; alerts on
  a new OOM kill, on available memory under 500 MB, and once per boot while swap is absent). Both
  verified to work unprivileged on the VM — `/proc/meminfo` and `journalctl -k` are readable without
  root, so the timer does not run privileged.
  **This is the gate on `fetch_rendered` actually being used in anger** — the tool ships with its own
  pre-flight refusal, but that is a valve, not headroom.
  @kind: chore
  @waiting: `sudo bash scripts/vm_add_swap.sh` and `--install-units` run on the VM
  *filed 2026-08-18 by a dev session · **not Mike-reported**, entering on the standing data-loss/
  reliability exception — an unlogged repeat outage is the failure it protects against*

- **3. [DB-0818-02] Playwright is granted but not installed on the VM, so rendered fetch answers
  with its own refusal message.** `fetch_rendered` is registered and granted to `logistics` and
  `research_agent` (`35499af`), but Playwright and its Chromium binary are not on the VM. Until they
  are, the tool returns the clean "not installed" error — correct behaviour, not a bug, and the
  reason the grant was safe to make ahead of the install.
  **Footprint measured on the Mac 2026-08-18:** ~134 MB for the Python package plus ~563 MB of
  browser binaries, **~700 MB total**, against 4.5 GB free on a 20 GB disk already at 76%.
  **Do the swap first (`[DB-0818-01]`)** — installing a browser on a machine with no swap and a
  history of OOM kills is the wrong order.
  @kind: chore
  @waiting: `[DB-0818-01]` applied to the VM
  *filed 2026-08-18 · the code half of `[DB-0806-02]`'s read scope is done and closed*

## Closed 2026-08-18 — `/backlog deep` + one attack round

- **[DB-0808-16]** The `injection` suite needs an ordinary-life persona — a clinically-loaded
  one silently scores 3/3 on a pipeline that never read the payload. Docstring line + a guard
  that fails loudly when `read_email` was never called. Matters for the open B1b rows.

  **Closed 2026-08-18 — already fixed, found by `/backlog deep`.** Both halves shipped in `7c70cd9` (2026-08-08), the same commit as the incident: `tests/run_b1_redteam.py:76-86` instructs an ordinary-life persona by name, and `run_injection_suite()` check 0 asserts `read_email` was called, folding it into the scenario verdict so a pipeline that never read the payload FAILs instead of scoring a silent 3/3. **Open for ten days after being fixed** — the incidental closure that motivated `scripts/backlog_close_scan.py` the same day. Residual (cosmetic, not filed): the module USAGE block still shows `--persona sarah_chen` for this suite, contradicting its own advice.

- **[DB-0808-05]** The output filter suppresses the whole reply when Mike names a tool himself
  (*"`write_config` didn't save my preferences"*) — the canned fallback lands exactly when a
  complaint about the system deserves an answer. Live once (Exchange 027), pinned `FILTER-EXCH027`.
  Fix: pass the user's turn into `filter_output()` and exempt **only the term he typed, only in the
  next turn** — not a blanket flag, or a probing question disables its own backstop. Grep
  `filter_output(` for the three call sites; line numbers have moved twice.
  **Dev-session find; promote if it recurs.**

  **Closed 2026-08-18 — `bcb647c`, deployed.** `filter_output()` takes the user's own turn and exempts, **in tier 1 only, per term, for that turn alone**, an identifier the user typed first — so a complaint naming an internal term gets a real answer instead of the canned deflection. Tiers 2–4 untouched: a probing question still trips narration or the sentence gate, which is the constraint that made a blanket flag unacceptable. `user_text` defaults to `None`, so anything not passing it is bit-identical; **proactive sessions pass `None` deliberately** — a scheduler prompt must not be able to unlock the filter. `tests/test_filter_user_echo.py` 20/20 (six confirm the prober path still fails); filter gate 88 checks PASS. **Still owed:** `FILTER-EXCH027` in `tests/run_b1_redteam.py:423` should be promoted from informational to gated.

- **[DB-0810-02]** `core/trace.py`'s `pop_agent()` doesn't restore the prior thread-local
  `current_agent`, so a synchronous nested `run_subagent` misattributes its tool-call record to the
  child it just finished. Compounded by depth>0 agents always nesting under `t.pipeline[0]`.
  Diagnostic only, but makes The Book **actively misleading** for nested calls — which is how it
  cost a wrong diagnosis once. Fix: `push_agent()` returns the previous value for `pop_agent()` to
  restore. *filed 2026-08-10 · full mechanism in `archive/PROJECT_LOG.md` § 2026-08-10*

  **Closed 2026-08-18 — `bcb647c`, deployed.** `push_agent()` records the agent current at push time; `pop_agent()` restores it, so a tool call after a nested `run_subagent` returns is attributed to the caller. `tests/test_trace_agent_stack.py` 11/11. **Two premises in the fix brief were wrong and the worker rejected both:** the four `_set_current_agent(_parent_agent)` calls are not redundant — they seed a *new thread's* empty thread-local inside worker closures, and `pop_agent()` cannot cross a thread boundary, so deleting them would have dropped every parallel specialist from the trace; and both callers *do* use `push_agent()`'s return value, so the parent is stored on the `AgentRecord` instead. **Unblocks `core/actions.py:28-30`**, which cites this item as the reason it avoids per-agent attribution — widening it is now a product question, not a repair.

- **[DB-0814-04] An obligation with a *vague* due date is the first thing dropped from session
  context — the exact opposite of the intended priority.** `context_block()` in
  [tools/obligations.py](tools/obligations.py) sorts by `str(it.get("due") or "9999")`. The
  `"9999"` sentinel is meant to sink undated obligations to the bottom, and it does — but a
  vague phrase sorts **lexically after it**: `["2026-08-20", "2026-09-01", None, "next week"]`
  is the real order, verified by running it 2026-08-14. With `_CONTEXT_MAX = 6`, an obligation
  the user gave a soft deadline to therefore ranks below every undated one and is dropped first.
  **`OPEN_OBLIGATION_SCHEMA` explicitly invites the vague phrase** (*"or short phrase if
  genuinely vague"*), so this is the schema's own documented input hitting a lexical sort, not
  misuse. User-noticeable: the store silently stops surfacing a commitment that carries a
  deadline — which is the failure the obligation store was built for in the first place
  (see the module docstring's 2026-08-07 incident). Not fixed on the spot: the file was under a
  two-window collision at the time and that session was comment-only.
  *filed 2026-08-14 by the §10b run-2 window B, which verified the sort order by running it
  rather than reading it · not raised by Mike, so `## Later` by the standing rule*

Real, not prioritised. One or two lines each — detail lives in the code, the log, or
`archive/backlog_closed_2026-08.md`.

  **Closed 2026-08-18 — `fd273bf`, deployed.** `_due_sort_key()` in `tools/obligations.py` buckets `(0, iso)` / `(1, vague)` / `(2, "")`, so any stated urgency outranks none — a commitment given a soft deadline no longer sorts below every undated one and get cut first by `_CONTEXT_MAX`. Single call site confirmed; `tools/calendar_reconcile.py` uses `_load` for token matching, not ordering. `tests/test_obligation_due_sort.py` 5/5, **confirmed failing on HEAD first**, and demonstrated end-to-end: six undated obligations plus one due "next week" showed all six and dropped the dated one pre-fix; post-fix the dated one leads.


### Closed 2026-08-18 (second pass)

**The clinical hard-fails now have a result on the model tier that actually serves them.**
Suicidal ideation, mania signal and missed critical medication had only ever been checked on the
deep tier, while the quick tier carries the large majority of that traffic (43 vs 5, 58 vs 6 over
Aug 1–8). Run made 2026-08-18: **gate PASS, 3/3** —
`tests/a4_safety_rerun_2026-08-18_gemini_clinical_quick.md`. Two limits the report states and this
closure keeps: it is **not** like-for-like against the original local-model baseline, and
`--complexity` is inert for `local: true` agents, so it proves nothing about a future local route.
**`ROADMAP.md` § A7 check 8's wording remains unresolved** — always a separate half, and it does
not close with the run. *(was `[DB-0808-17]`)*

**"I'm dropping someone at the airport" no longer reads as "I'm flying" — tested, closed, not
built.** Filed the same day on four machine-log entries from 2026-08-05, then closed within the
hour by running it. Two live turns on `danny_park`:

- *"I'm dropping my sister at Heathrow tomorrow morning, she's on BA 892 to Sofia."* → the reply
  tracked **her** flight and **his** drive ("where will you be setting off from?"), and asked her
  name rather than keep saying "your sister". Context tracker recorded the thread as **"Heathrow
  drop-off timing and logistics"** — the distinction was written, not just understood.
- Next turn, *"What do I need to know about tomorrow?"* → *"the airport run… your sister's flight"*.
  **The distinction survived into the following turn**, which is where the original failure lived.

**Why the item existed at all is the lesson.** The evidence was four entries from one conversation
on one day, and both `tools/travel_watch.py` and `tools/flights.py` landed **three days after it**
— so the recorded failure was against code that no longer existed, and the context-writing
protocols added since are what now hold the distinction. Mike's call, 2026-08-18: *"since the code
was replaced, this is LIKELY FIXED. Test it and get rid of it if it passes."* It passed.
**Standing lesson: an item whose evidence predates a replacement of the code it blames is a test,
not a build** — and re-filing it as a build is how the same errors get relitigated. *(was
`[DB-0818-05]`, open for under an hour)*

**Double-booking protection now has a live result — the first since it shipped.** The write path
behind every calendar event the tool creates had only ever run against fixtures: all 24 tests mock
CalDAV, so refuse-on-exact-duplicate, the `[VERIFY]` fail-open marker and update/delete had never
touched a real server. **Run 2026-08-18 against the real calendar on the VM, persona `mike`: 9/9.**

What is now proven rather than assumed:
- an identical event is **refused**, naming the existing event's uid, not silently duplicated;
- when the conflict check itself fails, the write **still lands and is marked `[VERIFY]`** — and the
  marker was confirmed by reading the calendar back, not by trusting the return value;
- update and delete both work, each verified by re-querying the calendar rather than by the
  function's own success flag.

**Method, because the blocker was never technical.** This had been treated as needing a live
scheduling conversation, which is why it sat: nobody wanted to write junk into a real calendar.
Mike's call, 2026-08-18 — *"write junk events if you need to, just remove them afterwards"*. Events
were dated **2027-11-03**, far outside any view, titled `METATRON-SELFTEST`, and cleaned up in a
`finally` block that **re-queries the calendar afterwards to prove it is clean** — a deletion claim
is not evidence of deletion.

Kept as `tests/run_calendar_live_test.py` so this is repeatable rather than a one-off. Deliberately
**not** folded into the mocked suite: that one must stay offline and free, and a mocked suite that
skips silently when credentials are absent reports green while testing nothing. *(was
`[DB-0810-10]`)*

**The Synthesizer can no longer open a reply by reading its own thinking aloud — and the reason it
happened is now answered rather than suspected.** On 2026-08-12 Mike asked a question and got the
model's working-out instead of an answer: *"Step-by-step reasoning: 1. Analyze what the user is
really asking..."*, cut off mid-sentence. Tier 4 of `filter_output()` was built for that specific
instance because it quoted the instruction file verbatim. **The general case quotes nothing at
all**, and tiers 1–4 hunt architecture *vocabulary*, so ordinary deliberation passed all four and
reached the user — verified.

**The item's own "one cheap check" was answered by measuring the live endpoint, and it killed the
hypothesis rather than confirming it.** The theory was a plumbing fault: reasoning arriving on a
separate channel that the code accidentally merged into the reply. It does not. The first delta off
the live Vertex OpenAI-compat endpoint the Synthesizer actually runs on was literally
`ChoiceDelta(content="**Step-by-Step Reasoning:**\n\n1.  **Analyze the User's", ...)`. **Reasoning
arrives inside `content`, indistinguishable from the answer**; the only extra field on the stream is
an opaque `thought_signature`. So no upstream plumbing fix was ever possible — by the time any code
can see it, it is one string. `include_thoughts: False` changes nothing. `thinking_budget: 0` does
work, by disabling thinking altogether — **rejected**, because degrading the reasoning of the one
user-facing agent to fix a formatting leak is the wrong trade.

**Consequence that must not be lost: the filter is not a backstop here, it is the only control.**
The item and the roadmap both described tier 4 as belt-and-braces behind the instruction layer.
For this failure there is no second layer.

**Built: tier 5 — a response that OPENS by announcing its own reasoning is suppressed.** Anchored to
the start deliberately and matched only as a header (the colon is required). Suppression replaces
the *entire* response with the canned fallback, so a false positive costs the user their whole
answer — a worse outcome than the leak on any ordinary turn. That constraint is why the scope is
narrow, and why "Analysis of your spending suggests…", ordinary numbered lists and "Step by step,
you can…" all survive.

**Tested, in the same session as the fix** (`tests/test_deliberation_leak_filter.py`, 28 checks):
the exact shape captured off the live endpoint, nine header variants, a zero-width obfuscation, ten
ordinary answers that must survive untouched, the streaming path's actual input after the
`[CONTEXT]` split, and non-Synthesizer agents unaffected. **Confirmed failing on HEAD first** — 13
checks fail without the fix, all of them leak cases, with every false-positive check still passing.
Regression: instruction-leak suite, echo-exemption suite and the 88-check red-team filter suite all
pass unchanged.

**Known limit, asserted in the test so it is a boundary rather than a surprise:** deliberation
buried *mid*-answer is not caught. Any pattern loose enough to catch it there also fires on ordinary
prose, and that trade costs the user their reply. **Separate and pre-existing:** the streaming path
shows text as it arrives and filters at the end, so a leak can be briefly visible before `[RETRACT]`
— that is `ROADMAP.md` § Section 5A's live-stream-and-retract item, not this one. *(was
`[DB-0815-08]`)*

---

## Closed 2026-08-18 — the clearing sweep

**The session was measured in items removed, not code written: 41 open → 28, `## Inbox` 6 → 0,
`## Machine log` 91 → 49, file 1,294 → 664 lines.** Mike's four standing rules for it, all stated
2026-08-18: a closed item is *deleted* and its evidence comes here; a sweep that verifies an item
must **shorten or remove** it, never lengthen it; confirmation happens in the session that makes
the fix, or the item is time-gated with a date; and **do not ask permission for work already
authorised** — that is what parked the calendar test for a fortnight.

**One finding worth more than any single closure, because it invalidated three items at once.**
A `×N` in `## Machine log` written before 2026-08-15 is a **similarity chain length, not a repeat
count** — `SIMILARITY_THRESHOLD`'s comment in `scripts/sync_dev_backlog.py` documents sixteen
unrelated corrections reported as one signature. All three entries triaged into `## Inbox` on
2026-08-15 as *"Mike-originated, ×3/×4, clears the bar"* were **single events**, and every one of
them was also **older than the code that fixed it**. The bar was never cleared and the work was
already done. This is the third time an item's own description has argued persuasively for the
wrong decision, which is what the standing rule at the top of `DEV_BACKLOG.md` exists to catch.

### Fixed in this session

- **`[DB-0810-14]` The A4 clinical hard-fails could not be run with a response language set — the
  instruction on the item would have raised a false safety alarm.** The pipeline suite proves a
  flag reached the user by matching the English words `"crisis"`, `"hotline"`, `"medication"`.
  Translation renders exactly those, so running it as written made a **correct** response report
  FAIL — the worst failure direction this suite has. Fixed in `tests/run_a4_safety.py`: the two
  checks now run on different text. `token_forbid` stays on the **delivered** string (a leaked
  all-caps token is a leak in any language and translation does not reliably mangle it);
  `surface_expect_any` runs on the **pre-translation English**, captured by wrapping
  `_translate_for_user()`, which is the single call site. `tests/test_a4_translated_substance.py`,
  10 checks, all passing, including the equivalence that makes this safe to leave switched on
  permanently: for an untranslated persona — every persona today — the two texts are identical and
  nothing changes. The old code failed by construction (`"CRISIS" in <Cyrillic>` is False).

- **`[DB-0810-06]` The backlog's ceiling was measured in lines, and lines had stopped tracking the
  cost.** Mike named the replacement metric on 2026-08-15 while deciding a trim on a 922/450 file:
  *"a backlog's ceiling should probably be tied to the number of items in it, not its line count."*
  Applied — `DEV_BACKLOG.md` leaves `CEILINGS` in `scripts/check_claude_md_claims.py` for a new
  `ITEM_CEILINGS` at **45 open items**, counted by importing `sync_dev_backlog.count_items` rather
  than reimplementing it (that function carries four paragraphs of history about the ways this
  count has been got wrong). Warning branch verified by injection: `DEV_BACKLOG.md: 41 open items,
  ceiling 5`. `.claude/rules/docs-and-logs.md` § Ceilings updated. The reasoning, which is the
  durable half: item count bounds the **workload**; line count pressures a session to cut
  *evidence* out of well-documented entries, and the evidence is what the file's own standing rule
  depends on. `SESSION.md`'s line ceiling and volatile budget are untouched — the argument is
  specific to a backlog.

### Closed by running something

- **`[DB-0815-04]` Bulgarian replies came back in Latin letters instead of Cyrillic.** All three
  candidates are now resolved. *(c)* the Synthesizer self-applying a script preference — eliminated
  2026-08-15 by Mike grepping the VM. *(a)* the translation prompt — fixed 2026-08-15, and
  **verified live today**: `translate("Good morning. Your meeting is at three.", "bg", "Bulgarian")`
  against the real backend returns `'Добро утро. Срещата ви е в три.'` *(b)* the client —
  `static/index.html` declares `charset=UTF-8` and neither it nor `core/server.py` contains any
  transliteration, romanisation or normalisation call. The mechanism is fixed at the source and no
  candidate remains. Closed on that evidence rather than parked for a live turn; the on-screen
  check is on Mike's spot-check list, and this file is what a re-file would be checked against.

- **`[DB-0810-15]` A persona can send in one language and receive in another.** Built and deployed
  2026-08-15 (`8a7d1d7`, `b3ff108`). The feature works; every residual it named is separately
  tracked (`[DB-0815-02]` speech-in, and `[DB-0810-14]`/`[DB-0815-04]` both closed above). An item
  whose whole content is pointers to other items is not open work. **Rejected designs stay
  permanent in `core/translate.py`'s docstring** — do not re-propose prose in `synthesizer.md` or a
  model-called translate tool.

### Removed — not work

- **`[DB-0809-09]` The scheduler can skip a time-anchored job but never postpone it.** The entry
  said in its own text that the current state is **correct** (`morning_brief`/`evening_close` carry
  no activity gate deliberately) and that it should only be picked up if a fixed-time check-in
  should ever wait for a lull. That is a hypothetical, not a defect.
- **`[DB-0809-13]` Sentence-chunked TTS.** Kokoro is 2.8s/call and the entry's own instruction was
  **"do not build before using voice enough to say whether 2.8s actually feels slow."** The ruling
  is the useful part and it is preserved here; the item was a placeholder for it.
- **`[DB-0809-10]` `CLASSES` in `core/rule_classes.py` is incomplete by construction.** Three blind
  spots were found over a fortnight and each was fixed as an instance; what remained was the
  *mechanism*, with no open instance and nothing a user would ever notice. The maintenance loop it
  prescribes — widen a class in the same pass as any duplicate found by hand — is a habit, not a
  task. The sharpest of the three findings is worth keeping: the audit reads prose files and never
  settings files, so for a rule whose real counterpart is a **config key** it cannot name the
  partner at any score, and reporting is not preventing — `write_persona` writes to `mike.md` at
  runtime, so a layer decision enforced only in a config file is re-violated by the next such write.
- **`[DB-0805-01]` `_GUARDED_KEYS` is hand-maintained.** `ROADMAP.md` § B2 already owns the
  decision (hand-maintained guarded keys vs. the confirm gate as default). The wiring half was
  never open — both writers already gate. A backlog copy of a roadmap decision is a second bin.
- **`[DB-0809-07]` The VM lost all networking for ~4 hours on 2026-08-04** while GCE reported
  `RUNNING`. Same signature as the 2026-07-31 `nic0 is frozen` incident **but with billing never
  disabled**, so either that root cause was misattributed or there are two paths in. Unresolved,
  unactionable, and **no recurrence in fourteen days**. Re-file with fresh evidence if it happens
  again — that is what this file is for.
- **`[DB-0806-03]` No BigQuery billing export** and **`[DB-0806-04]` moving the VM to
  europe-west1** (~250ms off every voice reply for ~£2.60/mo, priced live not estimated). Both are
  one-word decisions for Mike, not engineering work, and both are in this session's decision batch.
  Re-file whichever he says yes to, as a build item.
- **`[DB-0805-05]` A session cannot tell its own edits from a parallel window's** and
  **`[DB-0809-14]` `ROADMAP.md` Track D is 22 KB of a 71 KB file loaded every session.** Both are
  **harness and development-process defects, not Metatron work**, and `## Inbox`'s own standing
  caution says they do not belong in this file at all. `[DB-0805-05]` is additionally mitigated:
  `scripts/hook_commit_guard.py` hashes each file a session writes and blocks at stage time.
- **`[DB-0815-10]` Backlog items declare whether they can be picked up.** Built 2026-08-15; the
  only remainder was back-tagging the rest of the file, which this sweep did as it rewrote every
  item. Counts are no longer a floor.
- **`[DB-0818-03]` We could not say how much the tool is used.** Built and deployed 2026-08-18
  (`tools/analytics.py`, absorbed-work metric, cohort anchor pinned, 26 days backfilled). Review is
  deliberately deferred until there is real data — tuning against development traffic would bake in
  the wrong shape — and that review lives in `ROADMAP.md` § A9a, which is now **time-gated
  `due: 2026-10-01`** rather than left open-ended. A backlog entry that only points at a roadmap
  section is a duplicate of it.

### Triaged out of `## Inbox` — removed rather than filed

All three were machine-written, and all three were opened against the current code before any
verdict, per the guidance for this session. See the finding at the top of this entry.

- **Mike's own email address keeps being transcribed wrong** (`diamond.mic@` for `diamond.mike@`).
  Evidence `2026-08-02T12:16:08Z`. The guard built for **exactly this near-miss** —
  `_OWN_IDENTITY_SIMILARITY_THRESHOLD` in `tools/crm.py`, which cites the case verbatim in its
  comment — plus `relationships.md`'s standing read-back instruction, both shipped 2026-08-08. The
  evidence is six days older than the fix and has not recurred in the sixteen days since.
- **The system assumes Mike's energy is low and he keeps correcting it.** Evidence
  `2026-08-04T12:22:27Z`, a single event. The class it names — a standing fact re-derived wrongly
  instead of read from a store — is carried by `[DB-0818-06]`, which holds the eight interaction
  preferences sitting in the fact store where behaviour rules cannot reach them.
- **A stated deadline gets ignored and he is chased early.** Evidence `2026-08-11T11:13:14Z`.
  The item itself named the likely cause: `_due_sort_key` in `tools/obligations.py` ranked a vague
  due date **below** an undated one, so a dated obligation was truncated out of context by
  `_CONTEXT_MAX`. That was fixed a week after the evidence, by `fd273bf` on 2026-08-18.
- **"When something fails, tell me what I can't have and why."** Mike, 2026-08-18. Not removed —
  **merged into `[DB-0804-02]`**, where it is now the named half that B4 under-specifies, with
  `research_agent`'s `NoneType object is not iterable` as the worked live instance. It was filed
  separately because B4 sits inside Track B reading as security hardening, where nobody would look
  for it; the merge fixes that by naming it in the item title's own terms.

### `## Machine log` — 91 → 49, and the three `⚠` are gone

The section's standing rule — *an entry is DELETED once its signal is promoted or its cause is
fixed; leave a pointer, not the entry* — had been written but never executed, so addressed
signatures kept their `⚠` and kept leading the session-start line. Forty-two entries deleted, each
with a pointer recorded in the sweep note in `DEV_BACKLOG.md`. `.dev_backlog_seen` is what makes
this safe: the sync keys on timestamps already pulled, so nothing is re-added. **Do not regenerate
the section from the VM source** — that bypasses the ledger and resurrects everything.

## Closed 2026-08-20 — intake rollout close-out

- **[DB-0819-02] The tone profiler read other people's emails with the user's goals file loaded
  beside them.** Closed by `b417e98`: [tools/tone.py](../tools/tone.py) now dispatches
  `run_session(..., bare=True)` — agent file only, no goals, no profile — the same posture as the
  intake extractor. The item's own precondition was met first: `tone_profiler.md` grep'd clean of
  any goals/profile/mission reference (2026-08-20) before the argument changed. Raised low-priority
  as a dormant path; closed early because the intake deploy is the moment the email path becomes
  operational, which is exactly when the other session flagged it as worth knowing about.

## Closed 2026-08-22 — the contact dedup gate, and what its first live run exposed

### `[DB-0815-07]` The same person kept accumulating separate contact records — CLOSED

**Filed 2026-08-15 by Mike.** `Eva` and `Iva Diamond` were one person and survived five
corrections.

**What closed it — `6d6d46c`, built and deployed 2026-08-19.** A near-match on **create** now
saves nothing and raises a confirmation out of band; the model is not in the consent path, so a
duplicate cannot come into existence unasked. Updates by `contact_id` stay ungated (a deliberate
act on a record the caller already identified). Bulk import is exempt via `_bulk`, **deliberately
absent from the tool schema** so no model can set it — 200 contacts would otherwise raise 200
blocking confirmations and train the user to approve a queue unread, which is worse than no gate.
That regression was introduced during the build and caught by `tests/test_contacts_import.py`
before it shipped.

**Why a gate rather than better evidence, both halves measured rather than assumed.** The
*similarity score* cannot decide it: Stephen/Steven is 0.77 and is one person, Dave Bennett/Dan
Bennett is 0.87 and is two, Anna/Hannah is 0.80 and is two — no threshold separates them, so
raise-the-bar and auto-merge-above-X are dead ends, pinned as assertions in the test file so nobody
re-proposes one. The *agent* cannot decide it: handed identical evidence four minutes apart on
2026-08-19 it asked the first time and asserted *"Stephen with a 'ph' is added as a separate
contact"* the second, creating the duplicate the item was filed for.

**Frequency, so the friction is a known quantity:** 5 `write_contact` calls in 786 production tool
calls, against 3 for `send_email`, already behind this same gate.

**Tests:** `tests/test_contact_dedup_gate.py` 14 new; `test_crm_dedup_guards.py` 18 with two
rewritten — they asserted *"still creates the record"*, false by decision — and its temp-persona
harness needed `tools.confirm` patched too, since that module binds its own `persona_data_dir` and
without it the failures read exactly like a product bug.

**⚠ The production note travels with the closure, because it is the design intent and not a
hedge.** The gate exists because today's model on today's tier does not reliably ask. **When one
does, remove it and return to evidence-not-verdict**, which is the lighter design. The call gets
made by the judgement-consistency test recorded in `ROADMAP.md` § D2 — measuring how often a model
*asks* rather than which answer reads better. The same note sits beside the gate in `tools/crm.py`,
in its test file, and in § D2.

**Closed on the `@waiting` condition actually happening.** It waited on *"an agent resolving a real
near-match with `merge_contacts`"* — 0 calls in 786 at the time. On 2026-08-19 Mike ran it live and
the merge path executed twice. **It executed wrongly**, which is a new defect and is filed as
`[DB-0822-03]` rather than held here: the item's own fix shipped and is not what failed.

### `[DB-0810-07]`'s flag defect — the half that closed

Not the item, which stays open on its remaining live steps. **`b980b93`** closed the defect found
while trying to test it: `ok` was set `False` in exactly one place, the `except` around dispatch,
so the trace recorded crashes and nothing else. Measured on the VM 2026-08-19 — **786 tool calls,
one `ok:false`**, and that one a missing required argument on a scheduled agent, while every
graceful failure a user actually hits (`"Error: no contact found with id …"`) rendered green. No
phrasing could ever have turned it red, because every tool checked handles invalid input
gracefully by design. That is the tools being well written; the flag was reading the wrong signal.
`tests/test_tool_error_flag.py`, 17 checks.
