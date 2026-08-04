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

## Work log

- *(in progress — updated as steps land)*

## Deferred / not this session

- Deploy drain fix (verified real, stays filed)
- Transcription accuracy (`base.en`, `beam_size=5`, no VAD) + dictated-email known-values snap
- Deploying `ca993fe` / `15b9a41` / `0f2ca6c` — parallel window owns deploy
- `ROADMAP.md` Track D trim — must be item-by-item by whoever works Track D
