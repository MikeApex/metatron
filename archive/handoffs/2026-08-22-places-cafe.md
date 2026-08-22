# Handoff — venue discovery near a named address (`[DB-0808-04]`)

**Shipped.** `find_places(query, near, max_results=5)` returns real named venues — cafés,
pharmacies, pubs, shops — near any address, postcode or landmark, with rating + count,
price level, open-now and a `lat,lon` that hands straight to `get_travel_time`. **No GPS
needed**, which is the whole reason the item was parked for months behind an unrelated
real-time-location question. Registered in `register_tools()`.

**Commit:** `8754222` (worktree `metatron-wt-places-cafe`, branch `main`) — `tools/places.py`,
`tests/test_places.py`, and exactly three lines in `core/orchestrator.py` (import, schema,
dispatch). `git diff` confirmed no other session's hunks were in that file.

**Close `[DB-0808-04]`** on: 28/28 assertions in `tests/test_places.py` (`./.venv/bin/python
tests/test_places.py`, exit 0) — unconfigured-key error, happy-path parse, empty-results
returns an *error* not an empty list, max_results capped at 10 / floored at 1, timeout and
HTTP-error return `{"error": ...}`, and a schema-hygiene check that the tool description
names no provider. Plus `python3 -c 'import core.orchestrator'` clean and
`tests/test_check_agent_tools_personas.py` still PASS.

**Not yet usable in production — two acts outside this worker's scope:**
1. **Mike:** create a *new* API key on `metatron-ai-499810` restricted to the **Places API**
   and put it in `.env` as `GOOGLE_PLACES_API_KEY`. The existing `GOOGLE_MAPS_API_KEY` is
   restricted to `routes.googleapis.com` at creation and Places calls on it WILL fail — the
   separate key is deliberate leak containment, one key one SKU, not duplication.
2. **Coordinator:** the two Red-tier `find_places` grants in `config/agents/*.md` and
   `config/modules/routing*.yaml` (`logistics`, `recreation_hobbies`). Untouched here by
   instruction.

**Needs `./deploy.sh`** (`tools/` + `core/`) once both land.

**For `SESSION.md`:** cost note — Places API (New) bills by FieldMask tier, not per call.
`_FIELD_MASK` is pinned to basic/pro fields with a comment saying so; adding an Enterprise
field (reviews, editorial summary) raises the per-call price silently. This is a **Run**
cost with no standing/persistent component — no cache, no job, nothing that outlives the
call — so `spend_guard` is not blind to it in the way the Vertex cache-storage leak was.

**Verbatim transcript not run from here:** `archive_chats.py` resolves the JSONL from the
git root, and no JSONL exists for the worktree path — this worker's messages live in the
parent session's `-Users-md-homefolder-Desktop-multi-model-mcp` log. The coordinator's own
`/archive` captures them; running the script from the main tree was declined as out of scope.
