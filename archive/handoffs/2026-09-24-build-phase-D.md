# Build v4.11 — phase D: the two read tools the Librarian needs

**Date:** 2026-09-24 · **Model:** Opus 5 (1M context) · **Worktree:**
`/Users/md-homefolder/Desktop/metatron-wt-v4d-readtools`, branch `wt/v4d-readtools`, base `5ed1abf`
· **Patch:** [`archive/handoffs/2026-09-24-build-phase-D.patch`](2026-09-24-build-phase-D.patch)
· **Nothing committed, nothing pushed, nothing deployed. Worktree left in place.**

---

## What shipped

**Two questions the system could not answer before, and can now.** *"What did we actually say about
X, and when"* — there was no conversation search at all. And *"how does he write about this over
time"* — journal reads were one date at a time, so any question about a pattern across days was
unaskable rather than merely unanswered.

| Tool | Module | Answers |
|---|---|---|
| `search_conversations(query, k, since)` | **`tools/conversations.py`** (new) | verbatim turns containing every given term, newest first, each addressed by `date` + `seq` |
| `read_journal_range(start, end, max_entries)` | **`tools/diarist.py`** (beside `read_journal`) | journal entries across a window, oldest first, days with no file omitted |

Both are registered in `core/orchestrator.py` `register_tools()` — schema list and handler map —
and **granted to no agent**. They enter phase B's read-door allowlist, which is phase B's file.
No routing file and no agent file was touched.

**A fifth file had to change, and it is the guard working.** `core/actions.py` carries an explicit
read-vs-action classification of every registered tool, and `tests/test_action_provenance.py` fails
when a registered tool appears in neither set — it failed 9/10 the moment I registered these two.
Both are classified as reads. Left unclassified, `is_action()` would have fallen back to guessing
from the name prefix; `search_conversations` starts with `search_` and would have guessed right,
`read_journal_range` likewise — so this was latent rather than live, but the guard is what makes
that a fact rather than a hope. It is the `[DB-0810-13]` class of defect, and it is why the file
exists.

---

## Where each one reads, and the one thing the phase prompt's pointer got wrong

**The prompt said conversation turns live in "a per-persona SQLite database." They live in two
stores, and the SQLite one is neither per-persona nor complete.**

1. `data/personas/{p}/conversations/YYYY-MM-DD.jsonl` — appended by `core.server._log_conversation()`
   on **all five** turn paths: `/session`, `/session/stream`, the WebSocket loop, `/confirm`,
   `/decline`.
2. `data/conversations/metatron.db`, table `exchanges` — written by `_save_exchange()` on **three**
   of those five, and **shared across personas with a `persona` column** rather than being
   per-persona.

`search_conversations` reads (1). Four reasons, in order of weight:

1. It is the complete record. The database misses the `/session` and `/session/stream` paths
   entirely (`core/server.py:655`, `:753` call `_log_conversation` and not `_save_exchange`).
2. Scoping is by **directory**, not by a column — so a search cannot return another persona's turn
   even if the scoping were wrong. The database cannot say that.
3. It carries `agent` and `seq`, which the database row does not.
4. It is already what `/monitor/conversations` and `core/scheduler.py:175` read, so a hit here and
   a hit in The Book are the same row.

**A hit is addressed by `date` + `seq` deliberately** — that is the pair `/metatron-troubleshoot`
already takes, so anything found can be re-read in full through a path that exists rather than by
widening this tool.

**The legacy shared `data/conversations/*.jsonl` directory is not read, and that is a bound worth
stating.** `_conversation_files()` in `core/server.py` falls back to it for personas predating the
per-persona layout. A tool doing the same would put another persona's turns inside a persona-scoped
result, so it does not. No such file exists on the Mac (the directory holds only `metatron.db`). **If
one exists on the VM, pre-per-persona `mike` turns are outside this tool's reach** — check at phase E
and say so rather than discovering it as a false `absent`. A test pins the non-fallback.

`read_journal_range` reads `data/personas/{p}/journal/YYYY-MM-DD.json` through `_journal_dir()` —
the same store and the same helper as `read_journal`. It is a sibling, not a new module, exactly as
the prompt said it should be.

**Neither takes a `persona` argument**, though `get_log_window` does. The door is persona-bound from
the query (§ 6, finding 9), so the door's binding stays the only persona selector; a model-callable
`persona=` would be a second one, reachable from a prompt.

---

## The parameter names are the plan's, not the codebase's — and this was the find of the phase

**Phase A's landed `core/build/manifest.py` already specifies both calls.** `_SOURCES` carries:

```python
{"id": "journal_range", "tool": "read_journal_range", ...
 "probe": {"start": "", "end": "", "max_entries": 40}},
{"id": "conversations", "tool": "search_conversations", ...
 "probe": {"query": "", "k": 20}},
```

The door issues these **verbatim** — "the model names a source and code chooses the call." So the
probe is the specification, written before the tool, and it forced three decisions:

1. **`start`/`end`, not `start_date`/`end_date`.** Inconsistent with `get_log_window(start_date,
   end_date)` and with `write_journal(entry_date)`, and I would have chosen otherwise. But
   `manifest.py`'s own docstring records what a mismatched argument costs — a `TypeError`, recorded
   as `state: error`, reaching the Librarian as *"the code could not read it"* rather than *"there is
   nothing there"* — and it names `get_log_window`'s `{"days": 14}` as the instance that made the
   richest source in the system read as empty for three review rounds. Fitting the tool to the landed
   probe is free; editing another phase's landed file to suit my naming preference is not. The
   docstring says why, so the inconsistency does not read as a slip.
2. **An empty `query` must be legal**, because the presence check is `{"query": "", "k": 20}`. It
   matches every turn and returns the newest `k` — which is precisely "is there a corpus here, and
   how much." This falls out for free: the matcher is `all(term in haystack for term in terms)` and
   `all([])` is `True`. Note the `memory` row solved the same problem the other way, with a
   code-written generic word (`{"query": "day"}`), because `search_memory` requires one.
3. **An empty `start` must resolve to something wide**, because the journal probe passes `""` for
   both dates and carries no `probe_dates`. Empty `end` → today; empty `start` → the full 90-day
   ceiling back from `end`, i.e. the widest this tool will serve, so a presence check finds the
   corpus if there is one. `max_entries` bounds the payload, not the window.

**No edit to `core/build/manifest.py` was needed**, and a test asserts the fixed calls reach both
signatures without a `TypeError` — so the phase-B door cannot discover this on the VM.

---

## The caps I chose, and the one place I deliberately did not cap

Both tools carry ceilings **equal to** the door's published caps rather than below them: a tool
ceiling under the door's would make the door's published cap a lie.

| Tool | Parameter | Default | Ceiling | On `0`/negative |
|---|---|---|---|---|
| `search_conversations` | `k` | **10** | **50** | default, never "unlimited" |
| `read_journal_range` | `max_entries` | **50** | **200** | default, never "unlimited" |
| `read_journal_range` | window | 90 days back from `end` | **90 days** | — |

Four choices inside that worth naming:

1. **`0` does not mean "no limit."** `get_log_window`'s `max_entries=0` means unbounded, and copying
   that convention is exactly how a read tool ends up unbounded by default. Here `≤ 0` means "use the
   default." Stated in both docstrings, because the divergence from the neighbouring tool will
   otherwise look accidental.
2. **A result count bounds rows, not bytes — so there is a second cap.** A Synthesizer reply runs to
   thousands of characters; 50 rows of them is not a bounded payload. Each returned field is
   excerpted to **400 characters centred on the first matching term**, marked `excerpted: true`.
   Centred rather than head-taken because the head of a long reply is its preamble and the match is
   the reason the turn came back. A test asserts the whole payload is bounded by
   `k × 2 × (400 + markers)`.
3. **Truncation keeps the most recent, and says so.** Matching `get_log_window`'s stated reason —
   the freshest material is what should survive. `read_journal_range` walks back from the newest day
   and drops whole days once the budget is spent, including a partial day at the boundary, and puts
   the count dropped in `note`. `search_conversations` keeps counting past `k` so `match_count` and
   `truncated` are honest rather than clipped at the cap.
4. **The search window is NOT capped, and that is the one deliberate divergence from the door's
   numbers.** § 13.6 makes the Librarian's `absent` verdict a finding. A search silently narrowed to
   a recent window manufactures false ones — "he never mentions X" when X was mentioned four months
   ago. So with no `since` this reads all of history, and every result reports `searched_days`,
   `searched_from` and `searched_to`, so an empty result carries the evidence of what was looked at.
   A bad `since` is **reported**, never dropped: silently ignoring it would widen the window past
   what the caller asked for and say so nowhere. The journal window *is* clamped, because there the
   window is the output size — and the clamp names itself in `note`.

**Neither tool can raise.** A missing directory, an unreadable file, a half-written JSONL line, a
malformed day file, a stray non-dated filename: each reads as "nothing there" and the rest of the
window still returns. A research read must not be able to fail a turn.

---

## Tests, and what they assert

**`tests/test_read_tools.py` — 44 checks, 44 pass.** Plain-script convention, as § 12's rows use:

```
cd /Users/md-homefolder/Desktop/metatron-wt-v4d-readtools && .venv/bin/python tests/test_read_tools.py
→ 44 passed, 0 failed, 44 total
```

Against the four things the phase prompt asked for:

| Asked | Checks |
|---|---|
| **each returns what it claims on a persona with data** | term in the user's words; term in the reply; every term required (AND, not OR); case-insensitive and matching inside a longer word; newest-first across days *and* within a day; `since` inclusive on its boundary; the span searched is reported · a range returns every day oldest-first; dates echoed back; empty `end` = today; empty `start` = the 90-day ceiling; **a single-day range agrees entry-for-entry with `read_journal` on that day** |
| **an empty result rather than an error on a persona without** | no conversations directory; an empty one; an unparseable line skipped; a non-dated filename ignored; the shared cross-persona directory never read · no journal directory; a window with no file in it; a day file with an empty `entries` list omitted rather than returned blank; a damaged day file skipped with the rest of the window intact |
| **the cap holds — the ceiling, not everything** | `k=500` over 80 matches → 50 returned, `match_count` 80, `truncated` true; `k` omitted/`0`/negative → 10; a long field excerpted to the cap *and still containing the match*; a short field returned whole and not flagged; total payload bounded · `max_entries=5000` over 300 entries → 200; omitted/`0`/negative → 50; truncation keeps the most recent, across days and within a day; a 365-day window narrowed to 90 **with a note**; a window at exactly 90 not narrowed |
| **a range spanning dates with no entries does not error** | covered above; plus a bad `start`/`end` reported rather than guessed at, and `start` after `end` refused rather than silently swapped |
| **both are registered** | in the schema list **and** the handler map, callable, no duplicate name; every schema property is a real keyword argument of the handler; **`_SOURCES`' fixed probe calls reach both without a `TypeError`**; `manifest.unavailable()` no longer lists `conversations` or `journal_range`; both classified as **reads** in `core/actions.py` so neither joins the ACTIONS line |

### Run against real data, not only fixtures

Worktree code, main tree's `danny_park` store, read-only:

```
search_conversations('')          → 1 match, 1 day searched, 2026-09-24, seq 001, agent coordinator
search_conversations('calendar')  → 1 match
search_conversations('zzzz …')    → 0 matches, error '', searched_days 1   ← empty, not an error
read_journal_range('2025-01-01','2026-09-24')
   → window of 632 days narrowed to the most recent 90 (note says so), 3 days, 12 entries
read_journal_range('2026-08-01','2026-08-31')        → 3 days, 12 entries, no note
read_journal_range(… , max_entries=1)                → 1 entry, 'll older entries not shown…'
read_journal('2026-08-18')                           → 8 entries (agrees with the range read)
```

The 632-day narrowing did hide two 2025 journal files — and named the clamp in `note`. That is the
designed behaviour, and it is the reason the search window is not clamped the same way.

### Regression net

| Ran | Result |
|---|---|
| `./scripts/qa_sweep.sh` | **12/12** |
| `tests/test_action_provenance.py` | 9/10 → **10/10** after the `core/actions.py` classification |
| all eleven `tests/test_build_*.py` suites | **236/236** (schemas 36, gates 52, driver 19, wiring 19, jobs 18, registry 19, coherence 20, tick 14, tickets 14, table 13, spine 12) |
| `tests/test_turn_referent.py` | 22/22 |
| `tests/test_synth_module_injection.py` | 16/16 |
| `tests/test_a4_complexity_threading.py` | PASS |
| `scripts/check_agent_tools.py` | exit 0, classes 1 and 2 empty |
| `scripts/check_build_registration.py` | 0 findings |
| import gate: `core.{orchestrator,server,scheduler,router}`, `tools.subagent` | all import; `register_tools()` → 80 schemas, 81 handlers |
| `git apply --check` of the patch against the main tree | clean, all five files |

**Not run, named so it does not read as skipped:** `tests/run_knowledge_routing.py --persona
danny_park`. It exercises `run_pipeline_session_stream` and makes live Vertex calls; the worktree has
no `vertex-key.json` (absent from the main tree at link time), and § 10 names it as the gate for the
*seams removal*, not for every `core/orchestrator.py` edit. This change is three lines inside
`register_tools()` and touches no load seam. **It rides phase E's deploy checklist.**

**No fixture-persona file was dirtied** — every test writes into a `TemporaryDirectory` with both
modules' `persona_data_dir` patched, and the live run above was read-only. `git status` in both trees
confirms: five files in the worktree, main tree carries only the pre-existing phase-A patch.

---

## Three things I disagree with or found, per standing rule 7

1. **The prompt predicted a class-2 advisory from `check_agent_tools.py`; there is none, and that is
   better.** Class 2 is *"named but not granted"* — it keys on a tool being **mentioned in an agent
   file** with no matching routing grant. These two are named in no agent file and granted to nobody,
   so they appear in no class at all. Registered count went 79 → 81, classes 1 and 2 stay empty. The
   16 `request_build` advisories SESSION.md describes are class **3** (*granted but never named*),
   which is the opposite shape. Nothing to act on — but do not go looking for the advisory the prompt
   expects, or you will conclude the registration did not land.

2. **`tests/test_build_manifest.py` does not exist.** `core/build/manifest.py`'s docstring cites it
   twice as the thing enforcing the content-free rule — *"still enforced by
   `tests/test_build_manifest.py`'s grep of every profile value"* — and § 12 gives manifest no row of
   its own. So the rule that keeps the manifest safe to render into a prompt currently has **no test
   behind it**, and the docstring says otherwise, which is worse than silence. A phase-A gap, not
   mine, and outside this phase's files. **It should land before run 1**, because the Librarian is the
   agent the manifest is rendered to.

3. **`register_tools()` returns 80 schemas against 81 handlers, and has since before this phase.**
   `record_wisdom_response` is in the handler map with no schema in the list — confirmed identical on
   the base tree (78/79 there, so my delta is exactly +2/+2). A handler with no schema is never
   advertised to a model and so is unreachable except through `dispatch_tool`; whether that is
   deliberate is not recorded anywhere I found. Not filed — no unrequested backlog items.

One note for **A8**: `register_tools()` moves wholesale to `core/tools.py` under the module split, so
both additions travel with it and need no special handling. `core/actions.py` is untouched by A8.

---

## Deploy

**Nothing deploys here.** Per § 16, phases 0, A, B, B-Red and D reach the VM as **one** deploy at
phase E, and E is 18 commits deep (`b2b1dc7..HEAD`) — a catch-up deploy with Build inside it.
`core/{orchestrator,actions}.py` and `tools/{conversations,diarist}.py` are all VM-side, so all four
ride that deploy. Nothing user-visible ships: no agent holds either tool.

**The one thing phase B needs from this phase.** Both tools return a `dict` with a stable shape on
every path including failure, so the door's `{state, count, window}` can be derived without
branching on key presence:

| Door field | `search_conversations` | `read_journal_range` |
|---|---|---|
| `count` | `match_count` (total matched, not `returned`) | `total_entries` (total found, not `entry_count`) |
| `window` | `searched_from` … `searched_to` | `start` … `end` (post-clamp) |
| `state` | `error` non-empty → error; else `match_count` 0 → no data | same, on `error` / `total_entries` |

`error` is `""` on success, always present. Content must be stripped for a presence response —
`matches` and `days` are the content.

---

## Cost

**Roughly $4–5 against the § 14 budget of $4–7. Inside it; no overrun to report.** One Opus 5
session, no subagents, no model calls to any API but this one. The bulk went on reading `ROADMAP.md`
in full (94 KB), the four plan sections, and the storage-shape verification that turned up the landed
`_SOURCES` probe — which was the phase's load-bearing find, so it earned its share.

**Run:** $0. Two local-file read tools, no model call, no network, nothing persisted between calls.
Behind the door each costs one Tailscale hop for a result that would otherwise be computed in-process
— § 14's Ancillary line, unchanged.

**Unseen, named because no meter reports it:** `search_conversations` with no `since` scans every day
file for this persona. On the Mac that is one file; on the VM after months of use it is a few hundred,
tens of MB, low single-digit seconds. Bounded by disk and by a door a person calls deliberately, not
by a cap — and capping it is the thing that would manufacture false `absent` verdicts. **If the scan
ever becomes the slow part, the fix is an index, not a narrower default window.**

---

## Left open

1. **Whether a legacy shared `data/conversations/*.jsonl` exists on the VM.** If it does, pre-
   per-persona `mike` turns are outside `search_conversations`' reach. One `ls` at phase E settles it.
   Left open rather than guessed at because the answer is only visible on the VM.
2. **`tests/test_build_manifest.py`** — the absent suite in (2) above. Phase A's, owed before run 1.
3. **Phase B's allowlist lines.** Both names now resolve in `register_tools()`, so the door will stop
   refusing them as unregistered the moment B lands. Nothing to do here.
