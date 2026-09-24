"""
tests/test_build_doors.py — the read doors: what crosses, what is refused, for whom.

Plan section 12, Doors row, verbatim:

    `presence=<id>` runs the salvaged fixed call and returns no content; an
    argument outside the per-tool schema or over its cap -> 400 with the schema;
    any live-feed name -> 403 (finding 9)

Three assertions are added beyond that row, because it says what the endpoint
DOES and not what it IS:

    AUTH           a request with no bearer, and one with a wrong bearer, is
                   refused. The door is a monitor route and inherits
                   require_auth; this suite is what says so, since a future
                   OPEN_PATHS edit would open it silently.
    PERSONA BOUND  a door bound to persona A cannot read persona B's data. The
                   binding is the query parameter plus the absence of a
                   `persona` property in every schema — `get_log_window` takes
                   one, for dev testing, and this is what keeps it unreachable.
    NOT YET BUILT  an allowlisted name whose tool does not exist is refused as
                   UNREGISTERED (501, reason needs_tool) rather than 500ing.

THE SUITE RUNS THE REAL ENDPOINT, not doors.py alone. Half of what is asserted
here — the 401s, the 422-vs-400 shape, the JSON body a refusal carries — lives in
the middleware and the route signature, and a suite that called `doors.presence()`
directly would pass with the endpoint wired to nothing.

TestClient IS NOT USED AS A CONTEXT MANAGER, deliberately. Entering it runs the
app's startup event, which opens the exchange database and warms the embedding
model; neither has anything to do with a door, and the first writes to a real
file. Outside `with`, Starlette dispatches to the app without the lifespan.

NO REAL PERSONA IS TOUCHED. `core.persona._ROOT` is repointed at a temp tree and
two fixture personas are seeded there, so this suite cannot dirty the tracked
`data/personas/*` fixtures the way a live gate run does.

Usage:
    python3 tests/test_build_doors.py
"""

import json
import os
import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# BEFORE core.auth is imported by anything. The worktree symlinks the real .env
# and core.auth reads it at import time with setdefault(), so an explicit
# assignment here wins and pins the signing key to a test value — the suite
# neither depends on the real password nor exercises it.
os.environ["METATRON_AUTH_PASSWORD"] = "doors-suite-password"

from fastapi.testclient import TestClient                     # noqa: E402

import core.persona as persona_mod                            # noqa: E402
from core import auth                                         # noqa: E402
from core.build import doors as D                             # noqa: E402
from core.build import manifest as M                          # noqa: E402
from tests.support.runner import Suite                        # noqa: E402

import core.server as S                                       # noqa: E402

suite = Suite("build doors")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-doors-"))

# Every read tool in the set resolves its files through core.persona's _ROOT, so
# one rebind covers data/ (logs) and config/ (profile) for every one of them.
persona_mod._ROOT = _TMP

PERSONA_A = "door_a"
PERSONA_B = "door_b"
SECRET_A = "door-a-only-marker"
SECRET_B = "door-b-only-marker"

TODAY = date.today()


def _seed() -> None:
    """Three log days for A, one for B — so a count alone distinguishes them."""
    for persona, offsets, marker in ((PERSONA_A, (1, 2, 3), SECRET_A),
                                     (PERSONA_B, (1,), SECRET_B)):
        logs = _TMP / "data" / "personas" / persona / "logs"
        logs.mkdir(parents=True, exist_ok=True)
        for offset in offsets:
            day = (TODAY - timedelta(days=offset)).isoformat()
            (logs / f"{day}.json").write_text(
                json.dumps({"date": day, "note": marker}))
        cfg = _TMP / "config" / "personas" / persona
        cfg.mkdir(parents=True, exist_ok=True)
        (cfg / "profile.yaml").write_text(f"home_town: {marker}\n")


_seed()

client = TestClient(S.app)

# Every call the door actually made, as (tool, kwargs). This is how "the fixed
# call" and "no outbound call" stop being claims: the spy sits where the door
# resolves a handler, so nothing reaches a tool without being recorded.
_CALLS: list[tuple[str, dict]] = []
_real_handler = D._handler


def _spy_handler(tool_name: str):
    fn = _real_handler(tool_name)
    if fn is None:
        return None

    def wrapped(**kwargs):
        _CALLS.append((tool_name, dict(kwargs)))
        return fn(**kwargs)

    return wrapped


D._handler = _spy_handler  # type: ignore[assignment]


def _get(params: dict, token: str = "valid"):
    if token == "valid":
        headers = auth.bearer_header(120)
    elif token == "wrong":
        headers = {"Authorization": "Bearer 99999999999.not-a-real-signature"}
    elif token == "expired":
        headers = {"Authorization": f"Bearer {auth.issue_token(-60)}"}
    else:
        headers = {}
    return client.get("/monitor/tool", params=params, headers=headers)


def _detail(response) -> dict:
    body = response.json()
    return body.get("detail", body) if isinstance(body, dict) else {}


def _calls_to(tool: str) -> list[dict]:
    return [kwargs for name, kwargs in _CALLS if name == tool]


# ===========================================================================
# Section 12, part 1 — presence runs the SALVAGED FIXED CALL and returns NO
# CONTENT
# ===========================================================================

@check("presence=log answers with state, count and window")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["state"] == "data", body
    assert body["count"] == 3, body
    assert body["window"]["days"] == 14, body
    assert body["window"]["end"] == TODAY.isoformat(), body


@check("presence returns NO CONTENT — the log's own text is nowhere in the body")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"})
    assert SECRET_A not in r.text, r.text
    assert set(r.json()) == {"mode", "source", "tool", "state", "count",
                             "window", "note"}, sorted(r.json())


@check("the call is the FIXED one from _SOURCES — start_date/end_date, not days")
def _():
    # The D4 repair, asserted rather than trusted: `{"days": 14}` fitted no
    # signature, so every probe of the richest source in the system raised
    # TypeError and read as an empty corpus.
    _CALLS.clear()
    _get({"persona": PERSONA_A, "presence": "log"})
    calls = _calls_to("get_log_window")
    assert len(calls) == 1, calls
    assert set(calls[0]) == {"start_date", "end_date"}, calls[0]
    assert "days" not in calls[0], calls[0]
    span = date.fromisoformat(calls[0]["end_date"]) - date.fromisoformat(
        calls[0]["start_date"])
    assert span.days == 14, calls[0]


@check("presence takes a SOURCE ID, not arguments — ?args= cannot move the window")
def _():
    _CALLS.clear()
    _get({"persona": PERSONA_A, "presence": "log",
          "args": json.dumps({"start_date": "1999-01-01",
                              "end_date": "1999-12-31"})})
    calls = _calls_to("get_log_window")
    assert len(calls) == 1, calls
    assert calls[0]["end_date"] == TODAY.isoformat(), calls[0]
    assert "1999" not in json.dumps(calls[0]), calls[0]


@check("a source with no data reads as no_data, not as an error")
def _():
    r = _get({"persona": PERSONA_B, "presence": "wisdom"})
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "no_data", r.json()


@check("a live source is reported `live` and is NEVER called")
def _():
    _CALLS.clear()
    r = _get({"persona": PERSONA_A, "presence": "weather"})
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "live", r.json()
    assert r.json()["count"] == 0, r.json()
    assert _CALLS == [], _CALLS


@check("every live source is `live` and none of the seven is called")
def _():
    _CALLS.clear()
    live = [s for s in M.sources(registered=set()) if s.get("live")]
    assert len(live) == 7, [s["id"] for s in live]
    for source in live:
        body = _get({"persona": PERSONA_A, "presence": source["id"]}).json()
        assert body["state"] == "live", (source["id"], body)
    assert _CALLS == [], _CALLS


@check("a source whose tool is not registered reads as needs_tool")
def _():
    # Forced absent rather than named, for the same reason the 501 check below
    # is: this used to probe `conversations`, true as an unregistered tool for
    # the hours between phase B and phase D and false afterwards. The assertion
    # is about the STATE, so the state is what gets arranged — a fixture that
    # another phase is scheduled to invalidate is a test with a shelf life.
    D._handler = lambda tool: None
    try:
        r = _get({"persona": PERSONA_A, "presence": "conversations"})
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "needs_tool", r.json()


@check("an unknown source id is a 400 naming the source list, not a 500")
def _():
    r = _get({"persona": PERSONA_A, "presence": "no_such_source"})
    assert r.status_code == 400, r.text
    detail = _detail(r)
    assert detail["reason"] == "unknown_source", detail
    assert "log" in detail["sources"], detail


@check("a raising probe reads as `error` and STILL returns no content")
def _():
    # str(exc) on a YAML or JSON failure quotes the document that failed to
    # parse — and that document is persona data. Mode 1 promises no content, so
    # the error path has to promise it too.
    D._handler = lambda tool: (lambda **kw: (_ for _ in ()).throw(
        ValueError(f"malformed near {SECRET_A!r}")))
    try:
        r = _get({"persona": PERSONA_A, "presence": "wisdom"})
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]
    assert r.status_code == 200, r.text
    assert r.json()["state"] == "error", r.json()
    assert "ValueError" in r.json()["note"], r.json()
    assert SECRET_A not in r.text, r.text


@check("a TypeError KEEPS its text — it is the D4 argument diagnosis")
def _():
    def _wrong_signature(**kwargs):
        raise TypeError("read_wisdom() got an unexpected keyword argument 'days'")

    D._handler = lambda tool: _wrong_signature
    try:
        r = _get({"persona": PERSONA_A, "presence": "wisdom"})
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]
    assert r.json()["state"] == "error", r.json()
    assert "probe arguments do not fit" in r.json()["note"], r.json()
    assert "unexpected keyword argument" in r.json()["note"], r.json()


# ===========================================================================
# Section 12, part 2 — an argument outside the schema or over its cap is a 400
# CARRYING THE SCHEMA
# ===========================================================================

def _read(name: str, args: dict, persona: str = PERSONA_A, token: str = "valid"):
    return _get({"persona": persona, "name": name, "args": json.dumps(args)},
                token=token)


def _assert_schema_400(r, name: str, fragment: str = "") -> dict:
    assert r.status_code == 400, r.text
    detail = _detail(r)
    assert detail["reason"] in ("schema", "signature_mismatch"), detail
    schema = detail.get("schema") or {}
    assert schema.get("tool") == name, detail
    assert schema.get("properties") is not None, detail
    if fragment:
        assert fragment in detail["error"], detail
    return detail


@check("a well-formed read inside the caps SUCCEEDS — the validator is not a wall")
def _():
    r = _read("list_schedules", {})
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "list_schedules", r.json()
    assert "result" in r.json(), r.json()


@check("an unknown argument is a 400 with the schema")
def _():
    detail = _assert_schema_400(
        _read("search_memory", {"query": "x", "limit": 3}),
        "search_memory", "unknown argument")
    assert "limit" in detail["error"], detail


@check("k over the cap of 50 is a 400 with the schema")
def _():
    detail = _assert_schema_400(_read("search_memory", {"query": "x", "k": 500}),
                                "search_memory", "capped at 50")
    assert detail["schema"]["properties"]["k"]["max"] == D.MAX_K == 50, detail


@check("max_entries over the cap of 200 is a 400 with the schema")
def _():
    start = (TODAY - timedelta(days=5)).isoformat()
    detail = _assert_schema_400(
        _read("get_log_window", {"start_date": start,
                                 "end_date": TODAY.isoformat(),
                                 "max_entries": 5000}),
        "get_log_window", "capped at 200")
    assert D.MAX_ENTRIES == 200, D.MAX_ENTRIES
    assert detail["schema"]["properties"]["max_entries"]["max"] == 200, detail


@check("a window wider than 90 days is a 400 with the schema and the cap")
def _():
    start = (TODAY - timedelta(days=400)).isoformat()
    detail = _assert_schema_400(
        _read("get_log_window", {"start_date": start,
                                 "end_date": TODAY.isoformat()}),
        "get_log_window", "caps it at 90")
    assert detail["schema"]["window"]["max_days"] == D.MAX_WINDOW_DAYS == 90, detail


@check("a window exactly at the cap is accepted — the boundary is not off by one")
def _():
    start = (TODAY - timedelta(days=90)).isoformat()
    r = _read("get_log_window", {"start_date": start, "end_date": TODAY.isoformat()})
    assert r.status_code == 200, r.text


@check("a backwards window is a 400, not an empty read")
def _():
    _assert_schema_400(
        _read("get_log_window", {"start_date": TODAY.isoformat(),
                                 "end_date": (TODAY - timedelta(days=5)).isoformat()}),
        "get_log_window", "ends before it starts")


@check("a missing required argument is a 400 with the schema")
def _():
    detail = _assert_schema_400(_read("search_memory", {"k": 3}),
                                "search_memory", "missing required")
    assert detail["schema"]["required"] == ["query"], detail


@check("a wrong type is a 400 with the schema")
def _():
    _assert_schema_400(_read("search_memory", {"query": "x", "k": "five"}),
                       "search_memory", "must be an integer")


@check("a boolean is not an integer — True must not slip past a cap as 1")
def _():
    _assert_schema_400(_read("search_memory", {"query": "x", "k": True}),
                       "search_memory", "must be an integer")


@check("a bad date is a 400 with the schema")
def _():
    _assert_schema_400(
        _read("get_log_window", {"start_date": "last Tuesday",
                                 "end_date": TODAY.isoformat()}),
        "get_log_window", "ISO date")


@check("read_wisdom's `uncapped` is unreachable — READ_CAP holds behind the door")
def _():
    # tools/wisdom.py:345 READ_CAP = 15, and `uncapped=True` is the one lever
    # that switches it off. It is absent from the schema, so it is an unknown
    # argument and a 400 — which is what keeps the tool's own cap in force
    # beneath the door's.
    from tools.wisdom import READ_CAP
    assert READ_CAP == 15, READ_CAP
    assert "uncapped" not in D.public_schema("read_wisdom")["properties"]
    _assert_schema_400(_read("read_wisdom", {"uncapped": True}),
                       "read_wisdom", "unknown argument")


@check("an unknown enum value is a 400 listing what is allowed")
def _():
    detail = _assert_schema_400(_read("read_wisdom", {"domains": ["gardening"]}),
                                "read_wisdom", "unknown value")
    assert "home" in detail["schema"]["properties"]["domains"]["values"], detail


@check("a signature drift between schema and handler is a 400, never a 500")
def _():
    def _drifted(**kwargs):
        raise TypeError("list_schedules() got an unexpected keyword argument 'q'")

    D._handler = lambda tool: _drifted
    try:
        r = _read("list_schedules", {})
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]
    detail = _assert_schema_400(r, "list_schedules")
    assert detail["reason"] == "signature_mismatch", detail


@check("args that is not JSON, or not an object, is a 400")
def _():
    r = _get({"persona": PERSONA_A, "name": "list_schedules", "args": "{not json"})
    assert r.status_code == 400 and _detail(r)["reason"] == "bad_args", r.text
    r = _get({"persona": PERSONA_A, "name": "list_schedules", "args": "[1,2]"})
    assert r.status_code == 400 and _detail(r)["reason"] == "bad_args", r.text


@check("neither mode, or both modes, is a 400")
def _():
    r = _get({"persona": PERSONA_A})
    assert r.status_code == 400 and _detail(r)["reason"] == "mode", r.text
    r = _get({"persona": PERSONA_A, "presence": "log", "name": "list_schedules"})
    assert r.status_code == 400 and _detail(r)["reason"] == "mode", r.text


# ===========================================================================
# Section 12, part 3 — ANY LIVE-FEED NAME IS A 403 (finding 9)
# ===========================================================================

@check("every one of the seven live feeds is a 403, and none is called")
def _():
    _CALLS.clear()
    outbound = sorted(D.live_feed_tools())
    assert len(outbound) == 7, outbound
    for name in outbound:
        r = _read(name, {})
        assert r.status_code == 403, (name, r.status_code, r.text)
        assert _detail(r)["reason"] == "live_feed", (name, _detail(r))
    assert _CALLS == [], _CALLS


@check("the live-feed list is DERIVED from manifest._SOURCES, not listed twice")
def _():
    from_manifest = {s["tool"] for s in M.sources(registered=set()) if s.get("live")}
    assert D.live_feed_tools() == from_manifest, (
        D.live_feed_tools() ^ from_manifest)


@check("no outbound tool is in the read set")
def _():
    assert not (D.READ_SET & D.live_feed_tools()), D.READ_SET & D.live_feed_tools()


@check("the import-time invariant REFUSES an outbound tool added to the allowlist")
def _():
    original = D.READ_SET
    D.READ_SET = frozenset(original | {"find_places"})  # type: ignore[assignment]
    try:
        D._assert_no_outbound_door()
    except RuntimeError as exc:
        assert "find_places" in str(exc), exc
    else:
        raise AssertionError("an outbound tool in READ_SET was not refused")
    finally:
        D.READ_SET = original  # type: ignore[assignment]


@check("the import-time invariant REFUSES an allowlisted name with no schema")
def _():
    original = D.READ_SET
    D.READ_SET = frozenset(original | {"read_email"})  # type: ignore[assignment]
    try:
        D._assert_no_outbound_door()
    except RuntimeError as exc:
        assert "no" in str(exc) and "schema" in str(exc), exc
    else:
        raise AssertionError("a name with no schema was not refused")
    finally:
        D.READ_SET = original  # type: ignore[assignment]


@check("a read tool outside the read set is a 403 naming the set")
def _():
    for name in ("read_email", "read_calendar", "list_contacts"):
        r = _read(name, {})
        assert r.status_code == 403, (name, r.text)
        assert _detail(r)["reason"] == "not_in_read_set", (name, _detail(r))


@check("a WRITE tool is a 403 and never dispatched")
def _():
    _CALLS.clear()
    for name in ("send_email", "write_log", "write_calendar_event",
                 "run_subagent", "merge_contacts"):
        r = _read(name, {})
        assert r.status_code == 403, (name, r.text)
    assert _CALLS == [], _CALLS


# ===========================================================================
# ADDED 1 — AUTH
# ===========================================================================

@check("a request with NO bearer is refused")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"}, token="none")
    assert r.status_code == 401, r.text


@check("a request with a WRONG bearer is refused")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"}, token="wrong")
    assert r.status_code == 401, r.text


@check("a request with an EXPIRED bearer is refused")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"}, token="expired")
    assert r.status_code == 401, r.text


@check("a request with a VALID bearer is served — 401 is not the only answer")
def _():
    r = _get({"persona": PERSONA_A, "presence": "log"}, token="valid")
    assert r.status_code == 200, r.text


@check("/monitor/tool is not an open path — the door cannot be opened by omission")
def _():
    assert not auth.is_open_path("/monitor/tool")
    assert "/monitor/tool" not in auth.OPEN_PATHS


# ===========================================================================
# ADDED 2 — PERSONA BINDING
# ===========================================================================

@check("presence bound to A sees A's corpus; bound to B it sees B's")
def _():
    a = _get({"persona": PERSONA_A, "presence": "log"}).json()
    b = _get({"persona": PERSONA_B, "presence": "log"}).json()
    assert (a["count"], b["count"]) == (3, 1), (a, b)


@check("a read bound to A returns A's rows and NONE of B's")
def _():
    start = (TODAY - timedelta(days=10)).isoformat()
    args = {"start_date": start, "end_date": TODAY.isoformat()}
    a = _read("get_log_window", args, persona=PERSONA_A)
    b = _read("get_log_window", args, persona=PERSONA_B)
    assert a.status_code == b.status_code == 200, (a.text, b.text)
    assert SECRET_A in a.text and SECRET_B not in a.text, a.text
    assert SECRET_B in b.text and SECRET_A not in b.text, b.text


@check("read_profile bound to A cannot read B's profile")
def _():
    a = _read("read_profile", {}, persona=PERSONA_A)
    assert a.status_code == 200, a.text
    assert SECRET_A in a.text and SECRET_B not in a.text, a.text


@check("a `persona` ARGUMENT cannot reach the tool — it is a 400, not a redirect")
def _():
    # get_log_window takes persona= for dev testing. If a door passed it through,
    # a Librarian reading persona A's corpus could name persona B in the args and
    # be served it. It is not in the schema, so it is an unknown argument.
    start = (TODAY - timedelta(days=10)).isoformat()
    r = _read("get_log_window",
              {"start_date": start, "end_date": TODAY.isoformat(),
               "persona": PERSONA_B},
              persona=PERSONA_A)
    _assert_schema_400(r, "get_log_window", "unknown argument")
    assert SECRET_B not in r.text, r.text


@check("NO schema declares a `persona` property — asserted, not left to habit")
def _():
    for name in sorted(D.READ_SET):
        props = D.public_schema(name)["properties"]
        assert "persona" not in props, (name, sorted(props))


@check("a request with no persona is a 400")
def _():
    r = _get({"presence": "log"})
    assert r.status_code == 400 and _detail(r)["reason"] == "no_persona", r.text


@check("a persona name that is a traversal is a 400, and never reaches a path")
def _():
    for bad in ("../../etc", "door_a/../door_b", "Door_A", ""):
        r = _get({"persona": bad, "presence": "log"})
        assert r.status_code == 400, (bad, r.status_code, r.text)
        assert _detail(r)["reason"] in ("bad_persona", "no_persona"), (bad, _detail(r))


# ===========================================================================
# ADDED 3 — THE NOT-YET-BUILT CASE
# ===========================================================================

@check("the read set names a tool before it exists, and `pending` is derived not written")
def _():
    # The read set is written ahead of the tools (section 6: "plus
    # search_conversations and read_journal_range ONCE BUILT"), so listing a name
    # that does not resolve yet is the design.
    assert {"search_conversations", "read_journal_range"} <= D.READ_SET

    # What is NOT a written list is which of them are still pending. This
    # asserted the old hardcoded frozenset's contents and so passed only while
    # phase D had not landed. Now: pending is exactly the read-set names with no
    # handler, whatever those happen to be today.
    assert D.pending_tools() == frozenset(
        n for n in D.READ_SET if D._handler(n) is None)

    # And the derivation actually tracks the registry, proven by moving it: with
    # every handler absent, every read-set name is pending.
    D._handler = lambda tool: None
    try:
        assert D.pending_tools() == D.READ_SET
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]


@check("an allowlisted-but-unregistered tool is 501 needs_tool, never 500 or 403")
def _():
    # Deterministic regardless of phase D: _handler is forced to report the tool
    # as absent, which is exactly the state a not-yet-built tool is in.
    D._handler = lambda tool: None
    try:
        r = _read("list_schedules", {})
    finally:
        D._handler = _spy_handler  # type: ignore[assignment]
    assert r.status_code == 501, r.text
    assert _detail(r)["reason"] == "needs_tool", _detail(r)


@check("search_conversations and read_journal_range behave per phase D's state")
def _():
    # Written to survive phase D landing in the same tree. Until it does, both
    # are refused as unregistered; once it does, they must validate and run
    # rather than reverting to 403. Either branch is a pass; a 403 or a 500 is
    # not.
    from core.orchestrator import register_tools
    _, handlers = register_tools()
    for name in ("search_conversations", "read_journal_range"):
        built = name in handlers
        r = _read(name, {"query": "x"} if name == "search_conversations"
                  else {"start": (TODAY - timedelta(days=3)).isoformat(),
                        "end": TODAY.isoformat()})
        if built:
            assert r.status_code in (200, 400), (name, r.status_code, r.text)
            assert r.status_code != 403, (name, r.text)
        else:
            assert r.status_code == 501, (name, r.status_code, r.text)
            assert _detail(r)["reason"] == "needs_tool", (name, _detail(r))
            assert _detail(r)["pending_build"] is True, (name, _detail(r))
        print(f"      [phase D: {name} is "
              f"{'BUILT' if built else 'not built yet'}]")


@check("arguments are validated BEFORE the tool is found missing")
def _():
    # Order matters for the Librarian: "your arguments are wrong" and "this tool
    # does not exist" are different corrections, and a 501 on a malformed call
    # would send it off to file a needs_tool brief for a typo.
    r = _read("search_conversations", {"query": "x", "k": 9000})
    _assert_schema_400(r, "search_conversations", "capped at 50")


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
