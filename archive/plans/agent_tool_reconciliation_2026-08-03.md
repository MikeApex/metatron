# Agent Tool Reconciliation — Decision Table

*2026-08-03. Phase 2 of [capability_gap_gameplan](capability_gap_gameplan_2026-08-03.md). **For approval before applying.***

## The principle

The `allowed_tools` lists were set deliberately on 2026-06-24 (~95,000t → ~30,000t, *"highest-leverage single change"*). **Those decisions stand.** What was never done is reconciling the agent instruction files to them — the files still name tools from before the whitelist existed.

So the default is **remove the reference from the file**, and a grant has to earn its place. Net effect below: **11 grants, 30 removals.**

Grants cost roughly 100–200 tokens each, charged only to the agent that gets them. Total additive cost is ~1,500 tokens across six agents, against 65,000 saved.

---

## A. Grants — capability genuinely needed

| Tool | To | Why |
|---|---|---|
| `read_agent_config`, `write_agent_config` | logistics, physical_health, recreation_hobbies, relationships | **The SEQ 021 bug's family.** `mental_wellbeing`, `finance`, `work_vocation` and `learning_growth` already have these; `WRITE_AGENT_CONFIG_SCHEMA` itself lists all eight domain specialists as valid `agent_name` values. The current split is an oversight, not a design. Logistics specifically is told to maintain a recurring-obligation calendar with nowhere to keep it. |
| `search_memory` | logistics | Its operating loop names it explicitly: *"Use `search_memory` for prior logistics context — past travel patterns, recurring appointments, how the user has handled similar situations."* Removing the reference would delete a real step. |
| `read_archive`, `write_archive` | recreation_hobbies | The archive **is** movies, books, experiences and ideas. This is the one agent whose domain is literally that store. |
| `read_wisdom`, `find_duplicate_wisdom` | pattern_miner | Deduplicating the Wisdom Depot is its job; it cannot dedupe what it cannot read. |
| `write_log`, `write_wisdom` | diarist — **`routing.yaml` only** | **Parity bug.** The 2026-07-27 fix added these to `routing_cloud.yaml` and missed `routing.yaml`, so the Diarist silently loses both in local mode. |

---

## B. Removals — reference deleted from the agent file

| Tool | From | Why |
|---|---|---|
| `run_subagent` | finance, learning_growth, logistics, mental_wellbeing, physical_health, recreation_hobbies, relationships, work_vocation | `tools/subagent.py` enforces a hard recursion guard: only the Coordinator may spawn subagents; a specialist calling it gets an error telling it to do the work itself. **Eight files of dead instructions.** |
| `read_goals` | finance, work_vocation | Redundant — `goals.yaml` is already injected into every specialist's system prompt by `_run_single_agent()`. Spending a tool call to fetch what is already in context. |
| `write_config` | learning_growth, logistics | **Security-relevant.** `write_config` writes `mission.md` and `prime_directive.md` — Tier 1/2, user-owned. A domain specialist must not edit the user's terminal values. (Logistics tried exactly this during validation and was correctly refused.) |
| `write_journal` | finance, learning_growth, logistics | The journal is the Diarist's. Three specialists writing into it produces an incoherent record. |
| `read_archive`, `write_archive` | finance, learning_growth, logistics, physical_health, work_vocation | Passing mentions, no dependent step. Kept only for recreation_hobbies (above). |
| `read_wisdom` | finance, learning_growth, recreation_hobbies, relationships, work_vocation | Wisdom reaches the user through the Synthesizer, which holds the full stack. Per-domain reads duplicate that. |
| `search_memory` | finance, recreation_hobbies, relationships, work_vocation, pattern_miner | No dependent step in any of these files. Pattern Miner has `get_log_window` for its actual data. |
| `write_context_tracker` | pattern_miner | The tracker is the Synthesizer's session state. Pattern Miner's output channel is `write_insight_report`. |
| `write_quality_event` | coordinator | The Coordinator is deliberately tool-free (`allowed_tools: []`, single-pass directive assembly, 1 turn). The instruction cannot execute. The Synthesizer already holds this tool — logging belongs there. |
| `write_log` | synthesizer | Logging is the specialists'. Synth's job is the response. |
| `write_baseline_period` | goals_interviewer | Pattern Miner's tool. Goals Interviewer has `write_aspirational_baseline` and `create_semantic_anchor`, which are the right ones. |

---

## C. File corrections — not tool grants

1. **`research_agent.md`** — `get_weather` and `get_environmental_snapshot` sit under *"Phase 6 tools (deferred)"* but **were built today**. Promote them to the live list. Leave `get_news`, `get_market_snapshot`, `get_transit_status` deferred — they are correctly labelled and match the roadmap E1 table.
2. **`research_agent.md`** — `web_search(query, n_results)` is marked *"Build immediately — prerequisite for first real use."* **Stale:** web search already works via `run_session_gemini_grounded` (Google Search grounding), which is how Research Agent runs. Correct the note rather than building a redundant tool.
3. **`logistics.md`** — state `write_agent_config`'s real contract: one `key`, one `value`, JSON-encoded string for structured values. This is what SEQ 021 got wrong. Keep it to one or two lines.
4. **`synthesizer.md`** — handle the `[TOOL FAILURES]` block specialists now emit: never report an action as done when it appears there.
5. **`WRITE_AGENT_CONFIG_SCHEMA`** (`tools/agent_config.py`) — description still cites the pre-persona path `data/config/{agent_name}.json`; correct to persona-scoped.
6. **`physical_health.md:198`** — the `get_environmental_snapshot` mention sits in a deferred-features block. Now partly real; reword so it doesn't imply the vitamin-D feature ships today (that still needs GPS).

---

## D. One genuine fork — needs your call

**Should Logistics get `get_weather` directly?**

`logistics.md:197` lists it *"for travel planning context."* Two defensible answers:

- **Route via Research** (consistent with the stated design — Research fetches, Synth colours decisions). Keeps Logistics lean. Costs an extra hop: a weather-dependent logistics question needs Research invoked too.
- **Grant it directly.** Travel planning genuinely turns on weather, and the round-trip is a whole extra specialist call (~$0.025 and seconds) for one number.

**Recommendation: grant it.** The plant-watering case is a *logistics* condition, and making the cheapest, most common weather consumer go through another agent to get a number is the kind of purity that costs real money per exchange. Research keeps `get_weather` too — it has all tools.
