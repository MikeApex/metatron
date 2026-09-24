# Build phase B — the read doors

*2026-09-24 · Opus 5 · worktree `/Users/md-homefolder/Desktop/metatron-wt-v4b-doors`, branched
from `5ed1abf` · patch `archive/handoffs/2026-09-24-build-phase-B.patch` · **nothing committed,
nothing deployed, worktree left in place.***

---

## What shipped

**The Librarian can now read the persona's data where it lives, and only results cross.** One
endpoint on the VM server, `GET /monitor/tool`, beside `/monitor/file` — bearer-authenticated by
the same middleware every `/monitor` route already answers to, Tailscale-only, and bound to one
persona from the query. Two modes:

1. **`?presence=<source_id>`** — the model names a source; **code chooses the call.** The server
   runs the fixed, literal call from `core/build/manifest.py`'s `_SOURCES` and answers
   `{state, count, window}` with no content. `_SOURCES` was not touched: the D4 argument repairs
   and the seven `live: True` rows are phase A's, verbatim.
2. **`?name=&args=`** — a research read. The name must be in the door's allowlist; arguments are
   validated server-side against a per-tool schema with caps; a refusal carries the schema.

**The Mac half is `scripts/vm_read.py`** — the Librarian subagent's only permitted Bash form.
`--list` answers from the tracked allowlist in the local checkout rather than by a round trip,
since the VM runs the same code.

**Nothing user-visible, nothing deployed.** The endpoint is inert until `./deploy.sh` at phase E.

### The allowlist

Run 1's five plus phase D's two, as instructed — **listed before they exist**, so the door refuses
them as *unregistered* rather than as *unauthorised*:

```
get_log_window · read_wisdom · search_memory · list_schedules · read_profile      (run 1)
search_conversations · read_journal_range                                        (phase D)
```

**No outbound tool sits behind a door.** The seven live feeds are refused with a 403, and the list
is **derived from `_SOURCES`'s `live: True` rows** rather than written out a second time — an
eighth outbound tool added to the manifest is refused by this door on the day it lands, with no
edit here. Beneath that sits a structural floor: `doors._assert_no_outbound_door()` runs at import
and refuses to load the module if an outbound tool, or a name with no schema, is ever added to the
allowlist. `core/server.py` imports `doors` **inside the endpoint** so that failure takes down the
door and not the user's sessions.

### Caps

Window ≤ 90 days, `k` ≤ 50, `max_entries` ≤ 200, and beneath them `tools/wisdom.py:345`'s
`READ_CAP = 15`. The wisdom cap holds because **`uncapped` is absent from the schema** — the one
lever that switches `READ_CAP` off is an unknown argument and therefore a 400.

---

## The § 12 Doors row, with its output

| Piece | Command | Proves |
|---|---|---|
| Doors | `python3 tests/test_build_doors.py` | `presence=<id>` runs the salvaged fixed call and returns no content; an argument outside the per-tool schema or over its cap → 400 with the schema; any live-feed name → 403 (finding 9) |

```
PASS  presence=log answers with state, count and window
PASS  presence returns NO CONTENT — the log's own text is nowhere in the body
PASS  the call is the FIXED one from _SOURCES — start_date/end_date, not days
PASS  presence takes a SOURCE ID, not arguments — ?args= cannot move the window
PASS  a source with no data reads as no_data, not as an error
PASS  a live source is reported `live` and is NEVER called
PASS  every live source is `live` and none of the seven is called
PASS  a source whose tool is not registered reads as needs_tool
PASS  an unknown source id is a 400 naming the source list, not a 500
PASS  a raising probe reads as `error` and STILL returns no content
PASS  a TypeError KEEPS its text — it is the D4 argument diagnosis
PASS  a well-formed read inside the caps SUCCEEDS — the validator is not a wall
PASS  an unknown argument is a 400 with the schema
PASS  k over the cap of 50 is a 400 with the schema
PASS  max_entries over the cap of 200 is a 400 with the schema
PASS  a window wider than 90 days is a 400 with the schema and the cap
PASS  a window exactly at the cap is accepted — the boundary is not off by one
PASS  a backwards window is a 400, not an empty read
PASS  a missing required argument is a 400 with the schema
PASS  a wrong type is a 400 with the schema
PASS  a boolean is not an integer — True must not slip past a cap as 1
PASS  a bad date is a 400 with the schema
PASS  read_wisdom's `uncapped` is unreachable — READ_CAP holds behind the door
PASS  an unknown enum value is a 400 listing what is allowed
PASS  a signature drift between schema and handler is a 400, never a 500
PASS  args that is not JSON, or not an object, is a 400
PASS  neither mode, or both modes, is a 400
PASS  every one of the seven live feeds is a 403, and none is called
PASS  the live-feed list is DERIVED from manifest._SOURCES, not listed twice
PASS  no outbound tool is in the read set
PASS  the import-time invariant REFUSES an outbound tool added to the allowlist
PASS  the import-time invariant REFUSES an allowlisted name with no schema
PASS  a read tool outside the read set is a 403 naming the set
PASS  a WRITE tool is a 403 and never dispatched
```

## The three added assertions, with their output

**1 — Auth.** The door inherits `require_auth`; this is what says so, since a future `OPEN_PATHS`
edit would otherwise open it silently.

```
PASS  a request with NO bearer is refused
PASS  a request with a WRONG bearer is refused
PASS  a request with an EXPIRED bearer is refused
PASS  a request with a VALID bearer is served — 401 is not the only answer
PASS  /monitor/tool is not an open path — the door cannot be opened by omission
```

**2 — Persona binding.** Two fixture personas with different corpora, and the door is bound from
the query. `get_log_window` takes a `persona=` keyword for dev testing; the binding holds because
no schema admits it, so naming another persona in the arguments is a 400 rather than a redirect.

```
PASS  presence bound to A sees A's corpus; bound to B it sees B's
PASS  a read bound to A returns A's rows and NONE of B's
PASS  read_profile bound to A cannot read B's profile
PASS  a `persona` ARGUMENT cannot reach the tool — it is a 400, not a redirect
PASS  NO schema declares a `persona` property — asserted, not left to habit
PASS  a request with no persona is a 400
PASS  a persona name that is a traversal is a 400, and never reaches a path
```

**3 — The not-yet-built case.** Refused as unregistered, never as unauthorised and never a 500.

```
      [phase D: read_journal_range is not built yet]
      [phase D: search_conversations is not built yet]
PASS  the two phase-D tools are in the read set — listed before they exist
PASS  an allowlisted-but-unregistered tool is 501 needs_tool, never 500 or 403
PASS  search_conversations and read_journal_range behave per phase D's state
PASS  arguments are validated BEFORE the tool is found missing

50/50 passed
```

---

## What else was run

| Check | Result |
|---|---|
| `python3 tests/test_build_doors.py` | **50/50** |
| The other eleven `tests/test_build_*.py` suites | **236/236**, unchanged |
| `./scripts/qa_sweep.sh` | **12/12** |
| `git apply --check` of the patch against the main tree at `5ed1abf` | clean, 5 files |
| **Server started for real on 127.0.0.1:8077**, `/health` → `{"status":"ok"}` | boots clean with the endpoint |
| `scripts/vm_read.py` against that server, over HTTP, with a real minted token | presence, a 403 on `get_weather`, a 400 carrying the schema, and a content read all correct |

**A negative control was run, because a suite that cannot fail proves nothing.** Three defects were
injected into `doors.py` — the live-feed branch removed, `str(exc)` restored on the presence error
path, the integer cap check disabled — and the suite dropped to **45/50**, naming all three. The
file was restored from a byte-copy and re-verified at 50/50.

**One thing that negative control surfaced, worth knowing before anyone edits the refusal order:**
with the live-feed branch removed, all seven live feeds *still* returned 403 — via
`not_in_read_set`, because they are not in the allowlist either. The status code alone therefore
does not distinguish the two refusals; the `reason` field does, and the test asserts on `reason`.
Finding 9's refusal is defended twice, and the specific one is the one that tells a Librarian
"this leaves the machine" rather than "ask for something else".

---

## Judgement calls, stated so they can be reversed

1. **`core/build/__init__.py` is in the patch, one hunk, beyond the stated file list.** Its module
   map ended with *"`doors.py` (phase B) is the VM-side read endpoint and is not here yet"* — a
   claim this phase makes false, sitting next to the file. Replaced with a map entry. **Drop this
   hunk if you would rather the file list held exactly**; nothing depends on it.
2. **The presence error path no longer returns `str(exc)`.** The salvaged `probe.py` reported
   `f"{type(exc).__name__}: {exc}"`. A `str(exc)` from a YAML or JSON failure quotes the document
   that failed to parse, and that document is persona data — so mode 1's stated contract
   (*"{state, count, window}, no content"*) had a content channel through it. **A `TypeError` keeps
   its full text**, because that is the D4 signature diagnosis and it names parameters, not values.
   Everything else reports its exception type only. This is the one place I tightened a salvaged
   behaviour rather than carrying it verbatim.
3. **An unregistered-but-allowlisted tool answers 501, not 503.** 501 is the closer reading
   ("this server does not support this") and 503 implies a retry that will not help. The client is
   meant to branch on `reason: needs_tool`, which is a field rather than a code, so the choice of
   code is not load-bearing.
4. **The phase-D test branches on whether the tools are registered.** Phase D landed in the main
   tree while this ran (`archive/handoffs/2026-09-24-build-phase-D.patch` is now sitting there).
   Written naively, the 501 assertion would fail the moment both patches are in one tree. It now
   asserts *unregistered → 501 `needs_tool`* and *registered → not 403, not 500* — either branch is
   a pass, and it prints which one ran. A separate check pins the 501 mechanism deterministically
   by forcing the handler lookup to report the tool absent, so the guarantee does not rest on
   phase D's state.

---

## Was `core/server.py` clean when I touched it?

**Yes.** `git diff core/server.py` was empty in the main tree at session start, at `5ed1abf`, with
the only untracked file being phase A's patch. The worktree branched from that commit, so it could
not carry another chat's uncommitted lines. The resulting diff is **one hunk, 85 insertions, zero
deletions**, immediately after `monitor_file` — `@@ -1945,6 +1945,91 @@`.

No Red file was touched. No `config/agents/*.md`, no `routing*.yaml`, no `core/{router,persona,
scheduler,spend_guard}.py`. None was needed.

---

## What is left open

1. **The door is untested against real VM data.** Everything above ran on the Mac, against
   temp-tree fixture personas and the worktree's hollow `danny_park`. The first real exercise is
   phase E's deploy followed by a `vm_read.py` call against `mike` on the VM — worth doing as the
   first thing after that deploy, because a door that answers `no_data` for everything looks
   identical to one that is working.
2. **`search_conversations` and `read_journal_range` schemas are written from `_SOURCES`'s probe
   arguments, not from phase D's signatures.** If phase D landed a different signature the
   mismatch surfaces as a **400 naming it** (`reason: signature_mismatch`), never a 500 — that path
   is tested. But it should be checked once, by hand, after both patches are in one tree:
   `python3 scripts/vm_read.py --list` prints both schemas beside each other.
3. **Nothing consumes the doors yet.** `build-librarian.md` and `/build` are phase C. Until then
   the endpoint has exactly one caller, `scripts/vm_read.py`, and it is run by hand.
4. **`archive/handoffs/2026-09-24-build-phase-D.patch` appeared in the main tree during this
   session** and is not mine — left untouched.

**No backlog item was filed.** Nothing here is a defect and none was asked for.

---

## Cost

**Roughly $6–8 against the § 14 budget of $8–12 — inside it.** One session, no subagents, no
model calls beyond this window; the largest single cost was reading the 998-line plan, the
1,064-line roadmap and the four dependency files in full, which is what the phase is priced for.
**Nothing was spent on Vertex** — no Build node calls a Vertex model (ruling 1), and the only
server run was a local uvicorn on a spare port serving `/health` and `/monitor/tool`, which makes
no model call.

**Run cost of what shipped: $0 until deploy, and ~$0 after.** The VM gains one endpoint that
executes only when asked, with no cache, index, warm pool or scheduled job behind it — nothing
persists between calls, so there is no standing cost to expire and no meter that needs to learn
about it. A door call moves a tool result over Tailscale instead of running in-process: the same
tool, one hop, already priced in § 14's Ancillary line.

---

## To land it

```bash
cd /Users/md-homefolder/Desktop/multi-model-mcp
git apply archive/handoffs/2026-09-24-build-phase-B.patch
git diff -- core/server.py core/build/__init__.py core/build/doors.py \
             scripts/vm_read.py tests/test_build_doors.py
python3 tests/test_build_doors.py && ./scripts/qa_sweep.sh
```

Then stage those five paths explicitly and commit. **Do not deploy** — phase E carries 0, A, B,
B-Red and D as one deploy, and its checklist must separate Build from the 18 commits of catch-up
riding with it.

The worktree is **left in place** at `/Users/md-homefolder/Desktop/metatron-wt-v4b-doors`; remove
it with `./scripts/rm_worktree.sh v4b-doors` once the patch is committed.
