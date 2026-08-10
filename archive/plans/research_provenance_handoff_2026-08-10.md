# Research provenance + Book grounding — implementation handoff

*Written 2026-08-10 at the close of the SEQ 011/014 troubleshoot session. Everything below is
verified against the live VM and the running code, not recalled. Paste the prompt in § Prompt
into a fresh session.*

---

## What was already done (do not redo)

| Change | State |
|---|---|
| `config/agents/coordinator.md:171` — live travel status routes to Logistics, not Research | **committed `d0774f8`, deployed, verified live in exchange 016** |
| `tools/flights.py` — `delayed` now means *later than* scheduled, not *different from*; added `delay_minutes` (negative = early) | **edited + compiled + arithmetic tested locally. UNCOMMITTED, UNDEPLOYED** |

Nothing else has been touched.

---

## The findings, with evidence

**1. `web_search` does not exist.** Zero hits across `core/` and `tools/`. Yet
`config/agents/research_agent.md` instructs the agent to use it at lines **24, 52, 56, 80**.

**2. Research's real web access is Vertex-native grounding**, attached server-side at
`core/orchestrator.py:2048` (`types.Tool(google_search=types.GoogleSearch())`). It is **not a
tool** — it never appears as a tool call. This is why exchanges 008 and 014 showed "zero tool
calls" while the agent still had genuine web reach.

**3. The mandatory `SOURCES:` rule causes fabrication.** `research_agent.md:80` requires a
`SOURCES:` field on *every* response. With no retrieval performed and no tool to call, the
model invents one. Verbatim from exchange 014's trace, on a turn with zero tool calls:

> `SOURCES: Flightradar24, FlightAware, Trip.com real-time flight trackers (via live web search)`

That was emitted in direct response to the user asking whether it "actively got live
information." It had not.

**4. Two provenance claims end up in one string.** The model writes its own `SOURCES:` block
into the text; then `core/orchestrator.py:2145-2149` appends the *honest*
`SOURCES: training knowledge` when the real `sources` list is empty. Synthesizer receives both
and believes the specific, confident, fabricated one.

**5. The Book's `grounded` flag cannot detect grounding.** `core/trace.py:289` computes it as
`any(a.has_tool_calls() for a in t.pipeline)`, rendered at `tools/metatron_monitor.py:1153` as
`"no — no tool calls fired"`. Grounded search produces **zero** tool calls by construction, so a
genuinely grounded Research answer and a fabricated one both read `false`, while an agent that
merely called `write_log` reads `true`. The flag measures tool activity, not grounding. This is
why the detector added in `cb9f459` did not catch exchange 014.

**6. Nothing checks that a tool named in an agent file exists.** That is how `web_search`
survived in a live instruction file. Same class as the `logistics`/`write_agent_config` case in
`CLAUDE.md` § Security Architecture.

---

## What the SDK exposes (verified against the installed `google-genai`)

`types.GroundingMetadata` fields:

```
web_search_queries      grounding_chunks       grounding_supports
retrieval_queries       search_entry_point     retrieval_metadata
image_search_queries    source_flagging_uris   google_maps_widget_context_token
```

- `web_search_queries` — **the actual queries Gemini issued.** This is what the Book should show.
- `grounding_chunks[].web.uri` — retrieved source URLs (already harvested at `orchestrator.py:2113`).
- `grounding_supports[]` — has `segment`, `grounding_chunk_indices`, `confidence_scores`. Maps
  *individual sentences* to the chunks supporting them. This distinguishes "search fired" from
  "**this claim** was supported" — the subtler form of the BA464 failure. Capture is optional in
  phase 2; note it as available rather than building on it immediately.

---

## Design decisions already settled — do not re-litigate

1. **Do not rename `web_search` → `fetch_url`.** They are different operations. Search takes a
   query and returns candidates; fetch takes a URL you must already have. The rename would make
   the instruction unsatisfiable and the model would invent URLs — a quieter bug than invented
   citations, not a fixed one.
2. **Do not merge Research and Logistics.** Research is decontextualized by construction, which
   is the sole basis for cloud-routing it under the ZDR ruling; Logistics holds calendar/email/
   profile and *writes*. Merging would put personal context into the one agent designed never to
   hold it, and give write tools to the web-facing agent (confused-deputy surface).
3. **Do not build L2.5 (`fetch_rendered`) now.** Scoped in
   `archive/plans/level3_web_actions_scope_2026-08-06.md` because `fetch_url` returned an app
   shell for Heathrow's page — a need now served properly by `get_flight_status`. Build it when a
   real query needs it and no API serves it.
4. **Provenance is authored by Python, never by the model.** Same principle as `tone_shape`,
   which only `tools/tone.py` writes. A model's claim about its own retrieval is not evidence of
   retrieval.
5. **Keep the concrete flights/TfL example in `coordinator.md`** when adding the general
   principle. It is one of the clear dividers that must be correct every time; the principle is
   added *alongside* it, not in place of it.

---

## The work

### Phase 1 — config (no deploy risk)

1. **`config/agents/research_agent.md`**
   - Delete all four `web_search` references (lines 24, 52, 56, 80).
   - Delete the mandatory-`SOURCES:` rule at line 80. Replace with one line:
     *"Do not write a sources section — it is added for you."*
   - **Write L1 in immediately adjacent to the existing L2 `fetch_url` bullet at line 112**, so
     the two read as a pair. Line 112 is already good and says *"search chooses its own sources
     and cannot be pointed at a chosen page"* — L1 should describe live search as a capability
     the agent **has**, not one it calls. Keep it short; this file is token-sensitive.

2. **`config/agents/synthesizer.md`** — on `[RETRIEVAL: NONE]` accompanying a time-sensitive
   claim, never state it as current fact. Either caveat in plain user language (*"I don't have
   live confirmation on that"*) or ask for the agent holding the real feed. The user-facing
   wording must name no tool, agent, or routing — confidentiality rule is unchanged.

3. **`config/agents/coordinator.md`** — add the boundary principle, **keeping** the existing
   line 171 flights/TfL example:
   > Logistics owns live feeds about the state of the user's world — anything with a schedule or
   > status that changes plans. Research owns open-ended knowledge — anything where the answer is
   > understanding rather than current state.

### Phase 2 — core: Python authors provenance

4. **`core/orchestrator.py:2145-2149`** — strip any model-authored `SOURCES:` block from `text`
   (regex) *before* appending. Append exactly one code-generated line:
   - retrieved → `SOURCES (N retrieved): <urls>`
   - empty → `[RETRIEVAL: NONE — not checked against any live source]`

5. **`core/orchestrator.py:2106-2116`** — alongside the existing `grounding_chunks` harvest,
   collect `web_search_queries` per turn (accumulate across turns like `sources` does).

6. **`core/trace.py`** — carry search queries, retrieved URLs, and retrieval state into the
   trace record. **Fix `trace.py:289`**: `grounded` must not be `any(has_tool_calls())`. Grounding
   is retrieval-based, and for `research_agent` it is `len(sources) > 0 or bool(web_search_queries)`.
   Decide whether `grounded` becomes per-agent rather than per-trace — currently it is a single
   trace-level boolean, which is part of why it is meaningless.

7. **The Book — `tools/metatron_monitor.py`.** This was missed in the first plan and is
   explicitly wanted. Surface: whether search fired, **the actual search queries**, and the
   retrieved source count. Touch points: `191-206` (the `GROUNDED_TAG` on the header line),
   `1020`, `1153` (`"Grounded: … no tool calls fired"` — wording is wrong, see finding 5), and
   the plainspeak resource labels at `102-124`. A Research step should read something like
   `Web Research — 2 queries → 3 sources` or `Web Research — no retrieval`.
   > **`tools/metatron_monitor.py` is LOCAL ONLY. It is not deployed to the VM.**

8. **`UNGROUNDED_ANSWER` quality event** so these become countable rather than anecdotal,
   reaching `DEV_BACKLOG.md` through the existing quality-event sync (same path as
   `RULE_CONFLICT`).

### Phase 3 — the guard (mechanical; a cheaper model is fine here)

9. **`scripts/check_agent_tools.py`** — parse every `` `tool_name(...)` `` reference in
   `config/agents/*.md`; compare against `register_tools()` in `core/orchestrator.py` and each
   agent's `allowed_tools` in `config/modules/routing*.yaml`. Report three classes:
   **named-but-nonexistent** (`web_search`), **named-but-not-granted**, **granted-but-never-named**.
   Same shape as `scripts/check_rule_overlap.py`; can run as a `function:` scheduler job at
   **zero model tokens**, like `daily_rule_audit`.

---

## Constraints

- **Mandatory pre-edit context check** (`CLAUDE.md`): read `SESSION.md`, `ROADMAP.md`, and the
  current state of each file before editing. `config/agents/*.md` are ordinary editable config
  (freeze lifted 2026-08-02) but they are the product and token-sensitive — keep additions short.
- **`run_session_gemini_grounded` is slated to move to `core/providers` in the A8 refactor**, and
  `core/trace.py` was rewritten today by the Book work (`ffaf7a7`). Phase 2 edits will need
  re-homing at A8. Additive is fine; know it rather than discover it.
- **Vertex prompt-cache floor:** `coordinator` and `synthesizer` are the only two agents on the
  cached path. Any edit that *shrinks* their prompts must keep real prompt size clear of the
  4,096-token floor, or confirm `_pad_for_vertex_cache()` still covers it. Phase 1 items 2–3 both
  add text, so this should be safe — verify, don't assume.
- **Staging discipline:** two sessions often share this working tree. `git diff` every file before
  staging it; never `git add` by directory.
- **Deploy:** `config/` and `core/` need `./deploy.sh`. `tools/metatron_monitor.py` does not.
  The `tools/flights.py` fix is pending deploy and should be bundled.

---

## Test plan

**Phase 1 (after deploy)** — in the app:
- `"What's the status of BA464 from Heathrow to Madrid?"`
  → **pass:** trace shows `logistics` calling `get_flight_status`. (This already passes as of 016.)
- `"What's the current world record for the mile?"` — a Research question where grounding should fire
  → **pass:** Research output carries code-generated `SOURCES (N retrieved):` with real URLs, and
  **no** model-authored sources block.
- A deliberately obscure question where grounding will return nothing
  → **pass:** `[RETRIEVAL: NONE]` reaches Synthesizer; the user sees a natural caveat naming no
  architecture; **no invented citations anywhere.**

**Phase 2** — pull the trace with `/metatron-troubleshoot` and confirm the Book shows the actual
search queries and a correct grounded state for `research_agent`.

**Phase 3** — `python3 scripts/check_agent_tools.py` must report `web_search` as
named-but-nonexistent **before** Phase 1 lands, and report clean after.

---

## Prompt for the fresh session

> Read `archive/plans/research_provenance_handoff_2026-08-10.md` in full, then run the mandatory
> pre-edit context check from `CLAUDE.md` (`SESSION.md`, `ROADMAP.md`, current state of each file
> you will touch).
>
> Implement Phases 1, 2 and 3 in that document, in order. The findings, the settled design
> decisions, the file/line pointers and the constraints are all recorded there and were verified
> against the live VM — but re-check the current state of each file before editing it rather than
> trusting the line numbers, since another session may have moved them.
>
> `tools/flights.py` already carries an uncommitted, locally tested fix; bundle it into the deploy
> rather than reverting or redoing it. Do not deploy until Phase 1 and 2 are both complete and you
> have shown me the diff. Show me the todo list before you start executing.
