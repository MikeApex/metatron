# 2026-08-02 — SEQ 021 Logistics Turn Burn: Clock Injection, Tool Error Hints, Failure Reporting

Single-exchange troubleshoot of `mike` SEQ 021 (2026-08-02 19:26), via `/metatron-troubleshoot`.
User's question: *"Logistics seems to be called correctly by Coord. Why did it take so many turns?"*

**Status at close: code written and validated locally. NOT committed, NOT deployed** — see "Blocked on" below.

---

## The exchange

User: *"I require a strong reminder on the 15th of every month to pay the credit card bills."*
Response: *"The reminder for the 15th is set…"* — **it was not.**

Routing was correct. Coordinator ran 1 turn (1.8s) and dispatched Logistics properly. All the excess sat inside Logistics: **6 turns, 4 of them wasted.**

| Turn | Action | Outcome |
|---|---|---|
| 1 | `write_log(log_date="2025-05-22")` | Wrote — to a hallucinated date 14 months in the past |
| 2 | `write_agent_config(agent_name, **content**=…)` | ❌ unexpected keyword argument |
| 3 | `write_agent_config(agent_name, **recurring_obligations**=…)` | ❌ unexpected keyword argument |
| 4 | `write_agent_config(agent_name, **data**=…)` | ❌ unexpected keyword argument |
| 5 | `write_log(…"I need to verify the schema for write_agent_config"…)` | Gave up, logged an apology to itself |
| 6 | Text response to Synthesizer | — |

Timings: Coordinator 1.8s · Logistics 6.3s · Synthesizer 14.2s.

---

## Root causes (three, all confirmed)

1. **Logistics guessed the tool signature and never found it.** Real signature is `write_agent_config(agent_name, key, value)` — a flat key/value store taking JSON-encoded strings. It never tried `key`/`value`. Two contributing causes: (a) `logistics.md` describes a "comprehensive recurring obligation calendar that Logistics owns," priming a structured-object call; (b) `dispatch_tool()` returned the raw Python `TypeError`, which says the guess was wrong but not what is right.

2. **The reminder was never saved, and the user was told it was.** `data/personas/mike/config/logistics.json` still held only the old `preferences` key. The three failures never surfaced to the Synthesizer, which saw only Logistics' confident prose summary and reported success.

3. **Specialists receive no system clock.** Confirmed from trace `context_sections`: Coordinator and Synthesizer both get `recent_context` carrying *"System clock (authoritative…) Sunday, August 2, 2026, 7:26 PM."* Logistics got `agent_file` + `goals` only. By design (`_run_single_agent`: *"Specialists: goals.yaml only. Context arrives via the Coordinator directive"*) — but the directive carries no date, so Logistics invented one.

---

## Fixes written (validated locally, uncommitted)

**`tools/ambient.py`** — new `current_clock_line()`, wording matched to `load_ambient_context()`.

**`core/orchestrator.py`:**

1. **`clock_line()`** — wrapper returning `""` on failure rather than raising. Injected into the specialist branch of `_run_single_agent()` **via the user message**, not the system prompt, so the cacheable prefix stays stable (per the 2026-06-19 prefix-caching work and the Vertex 4096-token floor).
2. **`_signature_hint()` + bind-before-call in `dispatch_tool()`** — `inspect.signature(fn).bind(**inputs)` runs first; on failure returns `Correct usage: write_agent_config(required: agent_name, key, value)`. Binding separately keeps the hint off genuine `TypeError`s raised *inside* a tool body (verified).
3. **`_failed_tool_calls()` + `[TOOL FAILURES]` block** appended to specialist output. Excludes head/routing layer (Synthesizer output goes straight to the user; Coordinator output is parsed for `SPECIALISTS_TO_CALL`).

**Data:** hallucinated `data/personas/mike/logs/2025-05-22.json` moved on the VM to `data/diagnostics/bogus_logs/2025-05-22_hallucinated-date_seq021_2026-08-02.json`. Contained only Logistics' own bogus entry — merge semantics confirm no pre-existing real data was overwritten.

---

## Live validation — full pipeline, `sarah_chen`, same message

`python3 core/orchestrator.py --persona sarah_chen --local --input "I require a strong reminder…"`

- **Clock injected** ✓ — `context_sections.clock` present; `write_log` wrote to **2026-08-02**, no invented date.
- **Self-correction works** ✓ — turn 2 failed with the hint, **turn 3 got it right and saved**. `recurring_obligations` verified in `data/personas/sarah_chen/config/logistics.json`. Previously: 3 failures, gave up, nothing saved.
- Still 6 turns, but for a different and legitimate reason — turns 4–5 were Logistics attempting `write_config(filename="scheduler.yaml")` to create an actual scheduled notification, correctly refused by the allowlist. **That is a capability gap, not a bug** (see Finding 3 of the gap doc).

**Two refinements the live run forced:**
- Retry-then-succeed must not be reported as a failure, or the Synthesizer would tell the user a save failed when it landed. `_failed_tool_calls()` now suppresses any tool that succeeded anywhere in the session.
- Broadened the match from three `"Error running/calling/unknown tool"` prefixes to any result starting `"Error"` — the turn-5 permission denial (`Error: 'scheduler.yaml' is not allowed`) would otherwise have slipped through, and a *blocked* write is exactly the silent failure this is meant to catch.

Both refinements unit-tested against a replay of the real turn sequence.

---

## Deliverable: capability gap survey

[archive/plans/agent_capability_gap_2026-08-02.md](../plans/agent_capability_gap_2026-08-02.md) — written at user's direction instead of reconciling `logistics.md` downward, since a calendar is arriving shortly and narrowing the instructions now would only have to be undone.

Headline findings:

- **Finding 0 (security-relevant): the per-agent tool whitelist does not restrict anything.** `_run_single_agent()` filters `tool_schemas` but passes `tool_handlers` unfiltered, and `dispatch_tool()` does no whitelist check. Any agent can invoke any of the 43 registered tools. **Proven live:** `logistics` is *not* granted `write_agent_config` in `routing_cloud.yaml`, yet called it three times in production and the dispatcher executed each. Implication: every "told-but-not-offered" row currently works *by accident*, so closing this (Track B / B2, PoLP) without first fixing the allowlists breaks them all at once. **Fix the lists, then enforce.**
- **Finding 1:** every one of the 13 agents names at least one tool it is not advertised. Worst: `logistics` (8), `finance` (7), `recreation_hobbies` (7). Also — `run_subagent` appears in nine specialist files but `tools/subagent.py` has a hard recursion guard, so those are dead instructions.
- **Finding 2:** `physical_health.md` names `get_environmental_snapshot`, which does not exist anywhere.
- **Finding 3 (the one behind the original complaint): nothing in the system can actually set a reminder.** All three paths closed — CalDAV `enabled: false` with empty password; `scheduler.yaml` jobs are static with no tool to add one; `write_config` allowlisted to `mission.md`/`prime_directive.md` only. A reminder can be *recorded* but never *delivered*. Build order proposed: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store delivery preference.
- **Finding 4:** `WRITE_AGENT_CONFIG_SCHEMA` still documents the pre-persona path `data/config/{agent_name}.json`.

Four agent-file edits proposed **but not applied** — `config/agents/*.md` are frozen post-review (`parallel_chats_index_2026-06-11.md` rule 3: audit work proposes, never edits).

---

## Blocked on

**Commit and deploy held at user's instruction.** `core/orchestrator.py` carries a parallel chat's uncommitted work (Dev Backlog / Synth self-development: `_persist_dev_request`, `_DEV_REQUEST_TYPES`, `self_development.md` loader) plus a modified `config/agents/synthesizer.md`, `DEV_BACKLOG.md`, `scripts/sync_dev_backlog.py`, `config/personas/sarah_chen/self_development.md`. Both sessions' edits sit in the same file, so a clean split wasn't possible without surgery. User chose to close out the parallel chat first, then commit and deploy in one pass.

**Everything in this session is Mac-local until `./deploy.sh` runs.** The VM is unchanged except the moved junk log.

---

## `/metatron-troubleshoot` rewritten (done this session)

Third session in a row where the command's stale paths broke the first data pull, so it was fixed rather than worked around. `.claude/commands/metatron-troubleshoot.md` rewritten at user's explicit instruction. Six defects:

1. **Conversation path stale** — `data/conversations/{DATE}.jsonl` → `data/personas/{PERSONA}/conversations/{DATE}.jsonl`. Hard failure on every run. Made worse by `data/conversations/` still existing (now holds only the live `metatron.db`), so the error is `FileNotFoundError` on the *file* and reads like a wrong date rather than a wrong path.
2. **Persona hardcoded to `mike`** in the trace path — nine personas exist on the VM; non-Mike validation runs were undiagnosable.
3. **Missing `--tunnel-through-iap`** — `metatron-net` has had no public SSH ingress since the 2026-07-31 rebuild.
4. **Argument substitution broken** — header used `$1/$2/$3` while the script body hardcoded `DATE='YYYY-MM-DD'`, `SEQ='027'`. A real invocation yielded `DATE = 2`, `SEQ = $2`, `ISSUE = $3`. Now instructs the assistant to parse the user's message when substitution fails, and to echo the four resolved values back before running.
5. **Brittle SEQ match** — `l.get('seq') == SEQ` failed on unpadded input and gave no list of valid values. Now `.zfill(3)` on both sides, and lists available seqs/dates on a miss.
6. **Trace window bug documented but not fixed** — the exact `HH:MM` prefix match false-negatives when a pipeline straddles a minute boundary (trace stamped at pipeline start, conversation record at completion; SEQ 021 spanned 22s). Now a native ±2-minute window.

**Added:** `context_sections` printed per pipeline step as `[ctx:...]`. This was the decisive evidence for root cause 3 today and previously required a separate hand-written query — the Coordinator/Logistics context asymmetry is now visible in the default output. Also refreshed the server-log symptom list (`[token_budget] OVER_8K`, `[spend_guard]`, `[context] clock line failed`, `[vertex_cache] 404`) and the trace checklist (turn-count-per-agent, `Correct usage:` self-correction, `Error: … not allowed` permission denials, `[TOOL FAILURES]`).

**Verified against live data**, not just read back: `mike`/`2026-08-02`/`21` (deliberately unpadded) returned the full record, logs and trace with `[ctx:]` sections. All three error paths tested — bad SEQ lists the 23 valid seqs, wrong date lists the 5 available dates, missing persona names the exact absent path.

**No commit or deploy needed:** `.claude/` is gitignored in full, so this file is Mac-local and untracked. It therefore has **no backup and does not reach the VM or GitHub** — the original version of this prompt was already lost once (per the 2026-07-28 archive it existed "only in the chat transcript, never saved"). Worth considering whether it should live somewhere tracked.

## Process notes
- One transient IAP tunnel drop (`Connection is already closed`); succeeded on retry.
- **New standing communication preference recorded:** pair every technical explanation with a plain day-to-day one — keep both, never substitute. Saved to memory as `feedback_pair_technical_with_plain`.

## Open / not addressed

- `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char 82852)` — fired twice during SEQ 021 against a 276-byte file. Offset doesn't match the file, so the memory indexer is likely choking on a different or concatenated source. Unexamined.
- Pre-2026 logs (`2025-01-24`, `2025-05-13`–`2025-05-16`) remain in `data/personas/mike/logs/`. Believed genuine early-dev data; worth a glance to confirm none are further hallucinations.
