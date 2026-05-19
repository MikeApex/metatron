# Testing Framework — AI Life Manager
*Established Phase 3 (2026-05-18). Update as methodology evolves.*

---

## Purpose

This document captures the testing methodology, evaluation criteria, and running conclusions from model comparison tests across development phases. It is the reference for designing new test suites as new agents are built, and the record of which models perform best at which tasks.

---

## What We Test For

Every test suite evaluates three things:

**1. Tool compliance** — Does the model call the right tools, in the right order, with appropriately populated arguments? Does it log before responding? Does it read context and wisdom at session start without being told each time?

**2. Argument quality** — Are log content fields populated with real data (not empty dicts)? Are archive items fully formed (title, author, status, notes)? Does the model use multiple destinations when appropriate (journal + archive + log for a meaningful event)?

**3. Response behavior** — Does the response reflect knowledge of the persona? Does it pick up open threads from the context tracker? Does it engage with the actual content (not just reflect it back)? Does it ask questions that would matter to this specific person?

---

## Standard Scenario Set (Phase 3 baseline)

Designed to stress seven distinct behaviors in sequence. Re-run these for any new agent or major prompt change.

| ID | Persona | Input type | What it tests |
|---|---|---|---|
| T1 | Ryan Holiday | Morning check-in (sleep + activity + writing struggle) | Logging on check-in; wisdom/context read at open |
| T2 | Ryan Holiday | Book mentioned in passing | Proactive archive; context tracker continuity across separate sessions |
| T3 | Ryan Holiday | "How has my writing been?" | search_memory for history; pattern synthesis |
| T4 | Oliver Burkeman | Philosophical realization in morning pages | Capturing reflective/abstract content; ideas archive |
| T5 | Oliver Burkeman | End-of-day recap (good day) | Multi-destination capture; thread follow-up from context tracker |
| T6 | Arthur Brooks | Recurring missed habit | Pattern recognition; write_wisdom proactively; behavioral depth in response |
| T1-T3-same | Ryan Holiday | T1 → T2 → T3 as one session | Session accumulation; in-session memory; chained context |

**Session modes tested:** single-turn (each prompt as fresh session) AND multi-turn (T1→T3 chained). Both matter: separate sessions test context tracker persistence; chained tests in-session accumulation.

**Personas used:** Ryan Holiday (author/stoic, structured writing process, index cards), Oliver Burkeman (philosophical writer, morning pages, Rowan), Arthur Brooks (columnist, 4:30am gym anchor, Harvard). Each persona has pre-seeded logs, wisdom, and memory fixtures under `data/personas/{name}/`.

---

## Evaluation Dimensions

Score each dimension per test, per model. Use ✓ / ✓✓ / ✗ / partial.

### Tool behavior
- `context_tracker + wisdom read at session open` — every separate session, not just the first
- `write before respond` — logging happens before the reply, not after or not at all
- `log content populated` — actual fields (mood, sleep_hours, blockers) not empty `{}`
- `archive item populated` — full fields (title, author, status, notes, rating), not bare `{}`
- `multi-destination capture` — meaningful events hit journal + log + archive as appropriate
- `proactive write_wisdom` — model identifies a recurring pattern and writes it without being asked
- `search_memory for history` — used for "how has X been going" questions, not read_log by date
- `multiple search queries` — model tries more than one query strategy when first results are thin

### Response behavior
- `persona specificity` — references details from persona file (index cards, Rowan, 4:30am gym)
- `content engagement` — engages with the actual subject matter (Stoic philosophy, book structure) not just reflects back
- `thread pickup` — references open_threads from context tracker without prompting
- `diagnostic questions` — asks follow-ups that would actually help (not generic "how are you feeling?")
- `duplicate awareness` — notices existing log entry for same day, declines to write duplicate

---

## Running the Tests

```bash
# Single provider
python tests/run_phase3.py --provider openai    # o3
python tests/run_phase3.py --provider gemini    # Gemini 3.1 Pro
python tests/run_phase3.py --provider claude    # Sonnet 4.6

# All three in sequence
python tests/run_phase3.py --provider all

# Reports written to:
# tests/phase3_report_openai.md
# tests/phase3_report_gemini.md
# tests/phase3_report_claude.md
```

Reports are human-readable: inputs, tool calls with args and results (truncated), and responses side by side. Read the tool calls section first — it tells you more than the response about what the model is actually doing.

---

## Phase 3 Findings (2026-05-18) — Baseline

Benchmark: **Gemini 2.5 Flash**. Contestants: o3, Gemini 3.1 Pro, Claude Sonnet 4.6, Claude Opus 4.7 (partial).

### Summary table

| | 2.5 Flash | 3.1 Pro | o3 | Sonnet 4.6 |
|---|---|---|---|---|
| Context + wisdom at open | ✓ | ✓✓ | ✓✓ | ✓✓ |
| Log content populated | ✓ | ✓✓ | ✓ | ✓✓ |
| Archive item populated | partial | ✓✓ | partial | ✓✓ |
| Multi-destination capture | ✓ | ✓✓ | ✓ | ✓ |
| Proactive write_wisdom | ✓ | ✓ | ✓✓ | ✓ |
| Multi-query search | ✗ | ✗ | ✓✓ | ✓ |
| Persona specificity | ✓ | ✓✓ | ✓✓ | ✓✓ |
| Content engagement | ✓ | ✓ | ✓✓ | ✓✓ |
| Thread pickup | ✓ | ✓✓ | ✓ | ✓✓ |
| Diagnostic questions | ✓ | ✓ | ✓✓ | ✓✓ |
| Duplicate awareness | ✗ | ✗ | ✗ | ✓ |
| **Speed** | Very fast | Very slow | Medium | Fast |

### Standout moments (set the quality ceiling to beat)

**Sonnet 4.6 — T2 Holiday:** Quoted Seneca in Latin ("Omnia, Lucili, aliena sunt, tempus tantum nostrum est"), translated, and connected it to three mornings stuck on Cato. No other model attempted this.

**Sonnet 4.6 — T6 Brooks:** *"The column becomes the reason, and then the gym becomes the casualty, and then the column gets done by someone who's sharper and less patient than he would have been. That's a bad trade."* Best single response of the series.

**Sonnet 4.6 — T5 Burkeman:** Read existing log, detected duplicate, declined to write. Only model to show this awareness.

**o3 — T3 Holiday:** Named data gaps ("we don't have Tuesday–Thursday"), asked for word-count per session to quantify "stuck." Best analytical synthesis.

**o3 — T6 Brooks:** Ran search_memory before writing wisdom — verified the pattern before committing it.

**Gemini 3.1 Pro — T1 Holiday:** Only model to archive Liam's turtle as an *experiences* entry.

**Gemini 3.1 Pro — T2 Holiday (same session):** Full archive item every time — title, author, status, notes, rating — best archive field quality of any model.

### Known issues as of Phase 3

- `write_log` and `write_archive` called without required arguments by some models — fixed with None defaults and coercion, but sparse records (`{"date": "..."}`) still result when model omits content
- Wisdom deduplication: multiple near-identical entries for same pattern (different keys each round); upsert is key-based not semantic
- o3 date hallucination in T1: wrote log entries for tomorrow's date
- Gemini 3.1 Pro very slow (~27 min for 7 tests); may improve with stable release

---

## Sub-Agent Model Assignments (from Phase 3)

| Agent | Model | Rationale |
|---|---|---|
| Diarist | Sonnet 4.6 | Best conversational depth, persona engagement, content engagement |
| Pattern Miner | o3 | Best analytical synthesis, multi-query search, data gap identification |
| Archiving-heavy sessions | Gemini 3.1 Pro | Most thorough multi-destination capture, best archive field quality |
| Fast / fallback / mobile | Gemini 2.5 Flash | Reliable, low-latency, good enough |
| **Dev consultant — architecture** | o3 | Edge cases, logic review, schema trade-offs |
| **Dev consultant — instruction design** | Sonnet 4.6 | Whether an agent prompt will produce the right behavior |
| **Dev consultant — coverage** | Gemini 3.1 Pro | What the design is missing |

For Phase 4 design decisions, use all three models in **conversation mode** rather than routing one question to one model — multi-model discussion surfaces more than sequential single-model queries.

---

## How to Extend for Future Phases

### Adding a new agent

1. Add scenarios to `TESTS` in `tests/run_phase3.py` covering the new agent's core behaviors
2. Create persona fixtures for any new personas tested (logs, wisdom, memory seeds)
3. Add the agent's key tool calls to the evaluation dimensions above
4. Run `--provider all`, read the reports, update the summary table

### Adding a new model

Add a new provider branch in `run_session_captured()` in `tests/run_phase3.py`. For OpenAI-compatible APIs (most of them), only `api_key`, `base_url`, and `model` need to change. Add the model name to `PROVIDER_LABELS`.

### Raising the bar

When a model clears all ✓✓ on the standard set, add harder scenarios: multi-week pattern recall, contradiction detection (user says something that conflicts with a past log), persona drift detection (user behavior changing over time). The standard set should represent a floor, not a ceiling.

### What makes a good test scenario

- **One clear behavior under test** — the scenario should be designed to reveal something specific, not test everything at once
- **Realistic input** — terse, natural, the way someone actually talks. Not "Please log my sleep and note that I had a bad writing day."
- **A right answer that isn't obvious** — the model should have to use context, persona knowledge, or memory to respond well. Generic responses should fail the test.
- **Persona-specific details** — include details that only appear in the persona file (Liam, Rowan, index cards, 4:30am) so you can tell whether the model is reading it

---

## Cost Reference

| Model | Relative cost | Notes |
|---|---|---|
| Opus 4.7 | ~$1 / 7 tests | Reserve for final phase validation only |
| Sonnet 4.6 | ~20× cheaper than Opus | Dev default for Anthropic |
| o3 | Moderate | Worth it for analytical tasks |
| Gemini 3.1 Pro | TBD (preview) | |
| Gemini 2.5 Flash | Low | Benchmark / fallback |
