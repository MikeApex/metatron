# 2026-08-05 — Backlog Trust Repair: Counter Bug, Verify-and-Triage Sweep, Provenance IDs

*Written during the session, not after. Updated as work lands.*

## Why this session

Asked to work `DEV_BACKLOG.md` down to a manageable state, with an explicit constraint: make
sure the work has real value and isn't legacy or tail-chasing. Scoping found the list could not
be worked safely as it stood.

## Findings before any work started

### 1. The backlog did not balloon — the counter is wrong

`scripts/sync_dev_backlog.py` reported **48 open** at the session-start hook and **62 open**
twenty minutes later. Neither is real. The count sums every line starting with `- ` between
`## Inbox` and `## Done` — and **`DEV_BACKLOG.md` has no `## Done` heading**, so the region is
Inbox → EOF.

| | |
|---|---|
| Reported "open" | 62 |
| Untriaged `## Inbox` entries | 11 |
| Already struck-through / withdrawn | 8 |
| Actual candidate items | ~43 |

**Closing an item increases the reported number** — a struck-through entry still starts with
`- `. The count drifted upward as work got *done*. That alone explains "30-something to
60-something" with no new problems filed.

### 2. About a third of spot-checked items are stale

| Item | Reality |
|---|---|
| "transcription times out — no `run_in_executor`" | **Fixed 2026-08-01** (`d42eefc`, `81fc6e2`) — `_STT_EXECUTOR`/`_TTS_EXECUTOR` at `core/server.py:178`, Whisper warm-loads |
| "`write_config()` stores the heading verbatim", cites `_titled()` | `tools/config_writer.py` is 84 lines, contains no such code |
| "`shownIds` eviction cliff at `static/index.html:567`" | now at `:706`+ — file moved several hundred lines |
| "`/session` leaks `[CONTEXT]`" | `run_session` calls `split_context_block` + `filter_output` (`orchestrator.py:2690`) — probably fixed |
| "`deploy.sh` drain is decorative" | **Real** — `/active` counts only `_active_streams`, incremented solely in the SSE generator (`:433`); the WebSocket loop (`:600-655`) never touches it |
| "`deploy.sh` guard checks wrong machine" | correctly withdrawn in-file already |

### 3. No item identity, no provenance

`#7`/`#19` are positional and shift on every add or triage. Nothing records how an item arrived
or who filed it — the missing evidence behind "why did this list grow."

## Decisions taken this session

- **Local/Ollama path: dormant.** Vertex-ZDR is the operating position under the 2026-06-18
  amendment. Keep `routing.yaml` and local code paths intact; drop all "run it against ollama"
  verification items; annotate rather than delete the affected roadmap lines. The binding
  privacy ruling itself is **not** amended.
- **Backlog ID format:** `DB-MMDD-NN` + provenance line carrying date, filer, method, origin
  SEQ, and a `verified` reference.
- **One bin, count-only visibility.** `DEV_BACKLOG.md` stays the single bin. A `/backlog`
  command carries the triage ritual. `/metatron-code` and `/archive` report only a
  `new · untriaged · open` count — no recurring bulk chore.

## Tool-denial walkthrough (Step 3)

Nine Inbox `TOOL_DENIED` entries, six distinct cases. Matched to the live conversation record
on the VM. *(Denial timestamps UTC, conversation `ts` VM-local +1h; mapping is inference
corroborated by content.)*

| Denial | Exchange | Motivation |
|---|---|---|
| `logistics` → `write_agent_config` | 08-03 SEQ 006 — step counter, calendar items | persist a standing arrangement |
| `finance` → `read_archive` | 08-03 SEQ 008 — "credit card payments, what can you tell me" | recall stored records |
| `logistics` → `read_agent_config` | 08-03 SEQ 011 — plant check frequency in hot weather | read back a recurring rule to amend it |
| `physical_health` → `read_agent_config` | 08-04 SEQ 001 — morning check-in | **already granted since** (`b3229ff`) — stale |
| `logistics` → `write_agent_config` | 08-04 SEQ 001 — Apex consolidation brief | persist a multi-item plan |
| `logistics` → ×3 in one parallel batch | 08-04 SEQ 003 — proactive check-in | look up whether anything was outstanding |
| `work_vocation` → `search_memory` | 08-04 SEQ 004 — "put that on your active items" | recall the morning's Apex context |

**Conclusion: not overreach.** Five of six are the same motivation — the agents are improvising
around **a store that does not exist**. `write_agent_config` stands in for "record this standing
commitment"; `search_memory`/`read_archive` for "recall what we established." The real fix is
the `write_schedule`/`list_schedules`/`delete_schedule` + CalDAV path already in the backlog —
which the parallel window is building.

**Quality consequence worth its own line:** at 08-04 SEQ 003 the proactive check-in was denied
all three lookups and answered *"Nothing urgent on my end"* — while that morning's Apex brief
sat unrecorded. A false negative caused by the missing store, and exactly the failure the
"unsurfaced opportunities" item says nothing can measure.

**Drift noted:** `work_vocation` and `finance` hold `write_agent_config`
(`routing_cloud.yaml:75,85`) while clinical `physical_health` was deliberately denied it.

## Correction made mid-session — worth its own heading

The tool-denial analysis above was **wrong on first pass**, and the user acted on it before the
error surfaced. Recorded because the failure mode is the session's whole subject.

I concluded logistics was "improvising around a store that does not exist" and recommended
holding `write_agent_config` pending schedule/CalDAV work. Both halves were false:

1. **`write_schedule`/`list_schedules`/`delete_schedule` already existed** — built `078e618`
   and granted to logistics `2f74cd2`, both **2026-08-03 14:48**, *before every one of the
   denials*. The work being waited on had shipped two days earlier.
2. **`write_agent_config` is not a workaround for logistics — it is the specified store.**
   `logistics.md:189` draws the distinction itself: the recurring-obligation inventory lives
   there because *"obligations are data rows, not scheduled jobs."* `:45` makes it mandatory.

The source of the error: I trusted the backlog's own line *"`scheduler.yaml` jobs are static
with no tool to add one"*, true when written on 2026-08-01, stale by 2026-08-03. **A stale
premise does not merely waste the effort spent on it — it produces a well-reasoned
recommendation for the wrong decision.** That is now the stated rationale in `CLAUDE.md` and
`/backlog` for verifying before acting, and it is a better argument than "checking is tidy."

## Work log

**Step 1 — counter fixed (`9361537`).** `count_items()` in `scripts/sync_dev_backlog.py`;
`## Done` heading added to `DEV_BACKLOG.md`; struck-through excluded; untriaged and open
reported separately. Reconciled by hand against `awk`. Fail-silent contract verified intact
(exit 0 against an unreachable server, `--quiet` still silent).

**Step 3 — nine denials resolved (`9361537`).** Granted: `logistics` +`read_agent_config`
+`write_agent_config` +`search_memory` +`read_archive` +`write_archive`; `work_vocation`
+`search_memory`; `finance` +`read_archive`; `physical_health` +`write_agent_config`. Both
routing files in parity, verified by parsing both and diffing the tool lists.

`_GUARDED_KEYS` added to `tools/agent_config.py` — `(physical_health, medication_profile)` is
refused with an explanatory error. Tested four ways: blocked for that pair, allowed for another
key on the same agent, allowed for the same key on another agent, reads unaffected. Test
artifacts cleaned from `sarah_chen`'s tree.

**Step 2 — sweep (`23057ee`).** Inbox 14 → 0 (plus 3 that arrived mid-session). Four items
closed with evidence, three corrected, all survivors given `DB-MMDD-NN` IDs and provenance.

*Live-journal evidence proved decisive three times, where code reading had been misleading:*

- **AgentRecord serialization — elevated.** Filed as "trace serialization fails". Actually 18
  occurrences in 7 days against 19 total scheduler errors, so **essentially every scheduler
  failure is this bug**, and it kills proactive check-ins (`companion_checkin` ×13). `trace.py`
  is clean — `_agent_to_dict` has recursed `AgentRecord` since `c66ed03` — so the failing path
  is server-side via `send_one`. Localised; root cause open.
- **vertex_cache 404 — closed.** Eviction present at `orchestrator.py:1417`; last occurrence
  2026-07-29. The 11 `[vertex_cache]` warnings currently in the log are `NameResolutionError`
  from the outage — a near-miss that would have caused a re-file on a `grep`.
- **Memory indexer — confirmed and sharpened.** Same byte offset (`char 82852`) now appears
  against `2026-08-04` as it did against `2025-05-22`. A shared offset across unrelated files
  proves the indexer parses something fixed.

**Step 4 — `/backlog` (`812ef1a`).** New command carrying the triage ritual. `/metatron-code`
and `/archive` report the count and stop — no bulk chore attached to commands that run every
session. `CLAUDE.md` gets a pointer plus the one rule.

**Local path dormant (`23057ee`).** `ROADMAP.md` §A7 residual gap 1 and §0 item 8 annotated.
Marked, not deleted; binding privacy ruling untouched.

## Result

`0 new · 0 untriaged · 45 open` — and all three numbers now mean what they say.

## Needs deploying

`9361537` touches `config/modules/routing*.yaml` and `tools/agent_config.py` — **needs
`./deploy.sh`**. Coordinate with the CalDAV/email window, which owns `.env` and deploy. Until
then the grants are Mac-only and warn mode continues to let the calls through on the VM.

## Commits

| Hash | What |
|---|---|
| `9361537` | Counter fix + nine tool denials resolved + `_GUARDED_KEYS` |
| `23057ee` | The sweep: IDs, provenance, closures with evidence, ROADMAP dormant notes |
| `812ef1a` | `/backlog` command; count-only visibility in `/metatron-code` and `/archive` |
| `8ee150f` | This writeup |

## Deferred / not this session

- **A7 pipeline probe** — Step 5 of the approved plan, not reached. Self-contained; start fresh.
  Plan detail: `~/.claude/plans/let-s-look-at-the-glistening-pinwheel.md` § Step 5.
- **[DB-0803-02] AgentRecord / proactive check-ins failing** — the highest-value open item to
  come out of this session. Needs the server-side traceback.
- **[DB-0803-07] deploy drain** — confirmed real with evidence; fix scoped, not applied.
- Transcription accuracy (`base.en`, `beam_size=5`, no VAD) + dictated-email known-values snap.
- `ROADMAP.md` Track D trim — must be item-by-item by whoever works Track D.

## Method note, for the next sweep

Three claims were settled by the VM journal that code reading would have got wrong — twice in the
direction of "looks fixed, still firing", once "looks broken, stopped weeks ago". **A runtime
claim needs the journal, not the file.** One SSH round-trip answered four questions at once:

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
  --tunnel-through-iap --command="sudo journalctl -u metatron-server -u metatron-scheduler \
  --since '7 days ago' --no-pager | grep -c 'PATTERN'"
```

Watch for near-misses: eleven `[vertex_cache]` warnings looked like a filed 404 bug and were DNS
failures from an unrelated outage.
