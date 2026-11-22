"""
tests/test_data_objects.py — the user's logs and lists (data objects), phase 1.

archive/plans/custom_logs_and_places_plan_2026-11-21.md § 6 tests 1–3 (the phase 1 parts).
Same check-decorator convention as tests/test_health_notes_feed.py (no pytest). Every fixture
is synthetic, in a tempdir. Every live meter is stubbed: the relevance tagger's model call, the
Diarist's model call, push (FCM / web push) and the memory index write_log would start. No
CalDAV or Places call is reachable from this suite — the calendar read is stubbed where a
delegated read is exercised.

Each check imports the module it needs INSIDE its body, so that on HEAD (where
tools/data_objects.py does not exist) the checks that pin a fix fail one by one rather than
the whole file failing at import.
"""
from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import persona_scope  # noqa: E402

_results = []


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


# Grants used by the read-rule checks — a stub, so the suite does not depend on what the
# routing files grant today.
_GRANTS = {
    "diarist": ["write_journal", "write_archive", "write_log", "write_wisdom",
                "list_data_objects", "read_data_object", "write_data_object",
                "amend_data_object"],
    "synthesizer": ["list_data_objects", "read_data_object", "amend_data_object",
                    "list_tasks"],
    "physical_health": ["read_log", "write_log", "write_archive", "read_data_object"],
    "finance": ["write_archive", "read_data_object"],
    "relationships": ["read_contact", "list_contacts", "write_contact", "read_data_object"],
    "logistics": ["read_calendar", "read_data_object"],
    "mental_wellbeing": ["read_data_object"],
}


@contextmanager
def _sandbox(caller: str = "diarist", persona: str = "mike"):
    """A tempdir user folder; the archive, the registry, the caller, the grants and the
    tagger all pointed at stubs. Yields (user_dir, state) where state records stub calls."""
    import tools.diarist as DI
    import tools.data_objects as DO

    state = {"tagger_calls": 0, "pushes": [], "events": [], "caller": caller}
    with tempfile.TemporaryDirectory() as td:
        user = Path(td)
        saved = (DI._archive_dir, DO._user_dir, DO._caller, DO._allowed_tools,
                 DO._call_tagger, DO._send_push, DO._quality_event, DO.TAG_IN_BACKGROUND)
        DI._archive_dir = lambda: user / "archive"              # noqa: E731
        DO._user_dir = lambda: user                              # noqa: E731
        DO._caller = lambda: state["caller"]                     # noqa: E731
        DO._allowed_tools = lambda agent: _GRANTS.get(agent)     # noqa: E731

        def _tagger(payload, persona):
            state["tagger_calls"] += 1
            return '["recreation_hobbies"]'
        DO._call_tagger = _tagger
        DO._send_push = lambda title, body, persona: state["pushes"].append(body)  # noqa: E731
        DO._quality_event = lambda **kw: state["events"].append(kw)               # noqa: E731
        DO.TAG_IN_BACKGROUND = False
        try:
            with persona_scope(persona):
                yield user, state
        finally:
            (DI._archive_dir, DO._user_dir, DO._caller, DO._allowed_tools,
             DO._call_tagger, DO._send_push, DO._quality_event, DO.TAG_IN_BACKGROUND) = saved


def _rows(user: Path, cat: str) -> list:
    p = user / "archive" / f"{cat}.json"
    return json.loads(p.read_text()) if p.exists() else []


# ---------------------------------------------------------------------------
# The archive tool: `_` names, repeat merges, unregistered byte-identity
# ---------------------------------------------------------------------------

@check("write_archive refuses a category name starting with '_' (the registry cannot be reached)")
def _():
    import tools.diarist as DI
    with tempfile.TemporaryDirectory() as td:
        saved = DI._archive_dir
        DI._archive_dir = lambda: Path(td) / "archive"   # noqa: E731
        try:
            out = DI.write_archive("_registry", {"title": "x"})
            assert out.startswith("Not recorded"), out
            assert not (Path(td) / "archive" / "_registry.json").exists()
        finally:
            DI._archive_dir = saved


@check("the archive's private reader refuses a '_' name, and the registry is not inside archive/")
def _():
    import tools.diarist as DI
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        (user / "archive").mkdir(parents=True)
        (user / "archive" / "_hidden.json").write_text("[1]")
        try:
            DI._read_archive_category("_hidden")
            raise AssertionError("expected a refusal")
        except ValueError:
            pass
        DO.create_object("Migraines", description="headaches with the time and trigger")
        reg = DO._registry_path()
        assert reg.exists() and "archive" not in reg.relative_to(user).parts, reg


@check("read_archive is no longer a tool any model can call")
def _():
    from core.orchestrator import register_tools
    schemas, handlers = register_tools()
    assert "read_archive" not in handlers
    assert "read_archive" not in {s["name"] for s in schemas}
    assert {"list_data_objects", "read_data_object", "write_data_object",
            "amend_data_object"} <= set(handlers)


@check("a repeat write_archive of the same book merges and adds no occurrence — templated or not")
def _():
    import tools.diarist as DI
    with _sandbox() as (user, _s):
        # `books` is a template (thing+occurrences); `games` is unregistered.
        for cat in ("books", "games"):
            DI.write_archive(cat, {"title": "Middlemarch", "status": "reading"})
            DI.write_archive(cat, {"title": "middlemarch", "status": "read"})
            rows = _rows(user, cat)
            assert len(rows) == 1, (cat, rows)
            assert rows[0]["status"] == "read"
            assert "occurrences" not in rows[0], rows[0]


@check("an unregistered category's file is byte-identical to the HEAD writer's")
def _():
    import tools.diarist as DI
    from datetime import date
    with _sandbox() as (user, _s):
        DI.write_archive("games", {"title": "Go", "notes": "with Iva"})
        DI.write_archive("games", {"title": "Chess"})
        DI.write_archive("games", {"title": "go", "rating": 4})
        today = date.today().isoformat()
        expected = [{"title": "go", "notes": "with Iva", "date_added": today,
                     "rating": 4, "date_updated": today},
                    {"title": "Chess", "date_added": today}]
        assert (user / "archive" / "games.json").read_text() == json.dumps(expected, indent=2)


@check("an occurrence-identity object always appends, even through write_archive")
def _():
    import tools.diarist as DI
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        DO.create_object("Cardiac events", identity="occurrence", class_="health",
                         object_id="cardiac_events")
        DI.write_archive("cardiac_events", {"text": "irregular heartbeat"})
        DI.write_archive("cardiac_events", {"text": "irregular heartbeat"})
        assert len(_rows(user, "cardiac_events")) == 2


# ---------------------------------------------------------------------------
# The registry: create, close-match refusal, aliases, relevance, history, status, merge
# ---------------------------------------------------------------------------

@check("create tags relevance once; class health always adds both health agents")
def _():
    import tools.data_objects as DO
    with _sandbox() as (_u, s):
        out = DO.create_object("Heart log", description="heart monitor events",
                               class_="health")
        assert out["created"], out
        obj = DO.resolve("heart log")
        assert {"physical_health", "mental_wellbeing", "recreation_hobbies"} <= set(
            obj["relevant_agents"]), obj["relevant_agents"]
        assert s["tagger_calls"] == 1


@check("a close match is refused and returns the existing object instead")
def _():
    import tools.data_objects as DO
    with _sandbox() as (_u, s):
        DO.create_object("Migraines", description="headaches")
        out = DO.create_object("my migraine log")
        assert not out["created"] and out["match"]["name"] == "Migraines", out
        assert s["tagger_calls"] == 1


@check("aliases resolve; a merged object resolves to where it moved")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Cardiac events", object_id="cardiac_events",
                         identity="occurrence", aliases=["heart log"])
        assert DO.resolve("the heart log")["id"] == "cardiac_events"
        DO.create_object("Palpitations", identity="occurrence")
        DO.write_data_object("Palpitations", entry={"text": "fluttering"})
        DO.amend_data_object("Palpitations", action="merge", into="cardiac_events")
        assert DO.resolve("palpitations")["id"] == "cardiac_events"


@check("change an entry keeps its previous value; nothing is ever removed from a file")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (user, _s):
        DO.create_object("Migraines", identity="occurrence")
        for t in ("left side", "behind the eyes", "after the train"):
            DO.write_data_object("migraines", entry={"text": t})
        before = len(_rows(user, "migraines"))
        s = _s
        s["caller"] = "synthesizer"
        out = DO.amend_data_object("migraines", action="change_entry", entry=2,
                                   changes={"text": "behind the right eye"})
        assert "Changed" in out, out
        rows = _rows(user, "migraines")
        assert len(rows) == before == 3
        assert rows[1]["text"] == "behind the right eye"
        assert rows[1]["previous"][0]["value"] == {"text": "behind the eyes"}


@check("archive takes a log out of the lists without deleting it; it still reads by name")
def _():
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (user, s):
        s["caller"] = "diarist"
        DO.create_object("Migraines", identity="occurrence")
        DO.write_data_object("migraines", entry={"text": "left side"})
        s["caller"] = "synthesizer"
        DO.amend_data_object("migraines", action="archive")
        assert "Migraines" not in [o["name"] for o in DO.list_data_objects()]
        assert len(_rows(user, "migraines")) == 1
        got = DO.read_data_object("migraines")
        assert got["status"] == "archived" and len(got["entries"]) == 1, got


@check("thing+occurrences: an explicit occurrence write appends to the row; counts tell them apart")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.write_data_object("films", entry={"title": "Heat"})
        DO.write_data_object("films", entry={"title": "Heat"}, action="add_occurrence",
                             occurrence={"at": "2026-11-20", "notes": "again, with Iva"})
        DO.write_data_object("films", entry={"title": "Ran"})
        got = DO.read_data_object("films", count_only=True)
        assert got["things"] == 2 and got["occurrences"] == 1, got


# ---------------------------------------------------------------------------
# The read rule (review finding 7, verify NEW 1)
# ---------------------------------------------------------------------------

@check("an archive-store object is served only to its relevant agents and the standing readers")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.create_object("Cardiac events", object_id="cardiac_events",
                         identity="occurrence", class_="health")
        s["caller"] = "physical_health"
        assert "entries" in DO.read_data_object("cardiac events")
        s["caller"] = "synthesizer"
        assert "entries" in DO.read_data_object("cardiac events")
        s["caller"] = "finance"
        got = DO.read_data_object("cardiac events")
        assert "error" in got and "entries" not in got, got
        s["caller"] = ""
        assert "error" in DO.read_data_object("cardiac events")


@check("a native store is refused to an agent lacking that store's own read tool")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.register_store("contacts", name="Contacts", description="people")
        s["caller"] = "finance"
        got = DO.read_data_object("contacts")
        assert "error" in got and "list_contacts" in got["error"], got


@check("a delegated calendar read returns the calendar tool's own wrapping, unchanged")
def _():
    import tools.data_objects as DO
    from tools.untrusted import wrap_untrusted
    wrapped = wrap_untrusted("Dentist 10:00", source="calendar test")
    saved = dict(DO._NATIVE_READERS)
    DO._NATIVE_READERS["calendar"] = lambda obj, agent, f: {"events": wrapped}
    try:
        with _sandbox("diarist") as (_u, s):
            DO.register_store("calendar", name="Calendar", description="events")
            s["caller"] = "logistics"
            got = DO.read_data_object("calendar")
            assert got["result"] == {"events": wrapped}, got
    finally:
        DO._NATIVE_READERS.clear()
        DO._NATIVE_READERS.update(saved)


@check("a contact write is handed to write_contact, and its placeholder refusal still fires")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.register_store("contacts", name="Contacts", description="people")
        s["caller"] = "relationships"
        out = DO.write_data_object("contacts", entry={"name": "Unknown"})
        assert "write_contact" not in out or "refus" in out.lower() or "not" in out.lower(), out
        s["caller"] = "diarist"          # holds no write_contact
        out = DO.write_data_object("contacts", entry={"name": "Sam Ortiz"})
        assert "write_contact" in out and out.startswith("Not recorded"), out


@check("an unregistered archive category reads raw, only for an agent holding write_archive")
def _():
    import tools.diarist as DI
    import tools.data_objects as DO
    with _sandbox("finance") as (_u, s):
        DI.write_archive("games", {"title": "Go"})
        assert DO.read_data_object("games")["entries"][0]["title"] == "Go"
        s["caller"] = "mental_wellbeing"
        assert "error" in DO.read_data_object("games")


@check("a location-tier result never carries a coordinate")
def _():
    import tools.data_objects as DO
    out = DO._strip_coordinates({"name": "Bianco 43", "lat": 51.5, "lng": -0.1,
                                 "visits": [{"at": "x", "latitude": 1, "longitude": 2}]})
    assert out == {"name": "Bianco 43", "visits": [{"at": "x"}]}, out


# ---------------------------------------------------------------------------
# Writers: the pending marker, verification, one retry, the "didn't save" note
# ---------------------------------------------------------------------------

@check("a read straight after an add waits out the pending write")
def _():
    import threading
    import time
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.create_object("Migraines", identity="occurrence")
        tok = DO.mark_pending("migraines")

        def _late():
            def run(d, m):
                time.sleep(0.4)
                DO.write_data_object("migraines", entry={"text": "left side"})
            DO.run_verified_write(run, "d", [tok], persona="mike", retry_model=None)
        # The writer runs on its own thread inside a verified run, as the Diarist does; the
        # stubbed caller is module-wide so it sees "diarist" too.
        threading.Thread(target=_late).start()
        t0 = time.time()
        got = DO.read_data_object("migraines")
        assert len(got["entries"]) == 1, got
        # It waited for the write, not for the whole window (that would mean the write
        # never cleared its marker).
        assert time.time() - t0 < 3, time.time() - t0


def _verified(DO, behaviour):
    """Run DO.run_verified_write with a fake Diarist. `behaviour(attempt, model)` writes or
    not. Returns the models each attempt ran on."""
    seen = []

    def run(directive, model):
        seen.append(model)
        behaviour(len(seen), model)
    tok = DO.mark_pending("migraines")
    DO.run_verified_write(run, "directive", [tok], persona="mike", retry_model="reasoning-x")
    return seen


@check("a Diarist run that writes nothing is retried once, on the reasoning tier, then lands")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (user, s):
        DO.create_object("Migraines", identity="occurrence")
        seen = _verified(DO, lambda n, m: n == 2 and DO.write_data_object(
            "migraines", entry={"text": "x"}))
        assert seen == [None, "reasoning-x"], seen
        assert not s["pushes"] and not DO.pending_tokens()


@check("a Diarist run that files to write_archive in the right category counts as landed")
def _():
    import tools.diarist as DI
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.create_object("Migraines", identity="occurrence")
        seen = _verified(DO, lambda n, m: DI.write_archive("migraines", {"text": "x"}))
        assert seen == [None], seen


@check("filed elsewhere twice: one retry, then a push, a quality event and the next-reply note")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.create_object("Migraines", identity="occurrence")
        DO.create_object("Sleep notes", identity="occurrence")
        seen = _verified(DO, lambda n, m: DO.write_data_object(
            "sleep notes", entry={"text": "x"}))
        assert len(seen) == 2
        assert len(s["pushes"]) == 1 and "Migraines" in s["pushes"][0], s["pushes"]
        assert s["events"] and s["events"][0]["event_type"] == "DATA_OBJECT_WRITE_FAILED"
        notes = DO.take_turn_notes()
        assert notes == ["Migraines"], notes
        assert DO.take_turn_notes() == []          # shown once


@check("a Diarist run that raises is retried, and a marker that expires unverified is never silent")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, s):
        DO.create_object("Migraines", identity="occurrence")

        def boom(n, m):
            raise RuntimeError("model down")
        seen = _verified(DO, boom)
        assert len(seen) == 2 and len(s["pushes"]) == 1
        s["pushes"].clear()
        DO.take_turn_notes()
        # An orphaned marker (the process restarted mid-write) expires on a later turn.
        DO.mark_pending("migraines", set_at=0.0)
        assert DO.take_turn_notes() == ["Migraines"]
        assert len(s["pushes"]) == 1


# ---------------------------------------------------------------------------
# The manifest (plan § 6 test 2)
# ---------------------------------------------------------------------------

@check("the manifest lists only objects the agent may read, and never a private one")
def _():
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (_u, _s):
        DO.create_object("Cardiac events", object_id="cardiac_events",
                         identity="occurrence", class_="health")
        DO.create_object("Gift ideas", description="presents to buy")
        DO.amend_data_object("gift ideas", action="private")
        ph = DO.manifest_for("physical_health")
        fin = DO.manifest_for("finance")
        coord = DO.manifest_for("coordinator")
        assert "Cardiac events" in ph and "Cardiac events" not in fin, (ph, fin)
        assert "Cardiac events" in coord and "Gift ideas" not in coord
        assert DO.manifest_for("pattern_miner") == ""     # no read grant until phase 5


@check("a registered store is not listed in a manifest; a log kept in the daily log is")
def _():
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (_u, _s):
        DO.register_store("log", name="Daily log", description="the day by day log")
        ph = DO.manifest_for("physical_health")
        assert "Daily log" not in ph and "Sleep" in ph, ph


@check("creating an object leaves the Coordinator's and Synthesizer's cached system prompt unchanged")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    from core.router import ModelConfig
    captured = []
    saved = (O.run_session_openai, O.load_recent_context)

    def fake(system_prompt, user_input, *a, **k):
        captured.append((system_prompt, user_input))
        return "SPECIALISTS_TO_CALL: []"
    import core.router as R
    saved_resolve = R.resolve_model
    R.resolve_model = lambda agent, complexity=None: ModelConfig(   # noqa: E731
        provider="openai", model="stub", base_url=None, allowed_tools=None)
    O.run_session_openai = fake
    O.load_recent_context = lambda persona=None: ""                # noqa: E731
    try:
        # danny_park: a tracked fixture persona — the head layer loads its persona file.
        with _sandbox("diarist", persona="danny_park") as (_u, _s):
            for agent in ("coordinator", "synthesizer"):
                captured.clear()
                O._run_single_agent(agent, "hello", persona="danny_park")
                before_sys, before_user = captured[-1]
                DO.create_object(f"Migraines {agent}", identity="occurrence")
                O._run_single_agent(agent, "hello", persona="danny_park")
                after_sys, after_user = captured[-1]
                assert before_sys == after_sys, f"{agent} system prompt changed"
                assert f"Migraines {agent}" in after_user and \
                    f"Migraines {agent}" not in after_sys, agent
    finally:
        O.run_session_openai, O.load_recent_context = saved
        R.resolve_model = saved_resolve


# ---------------------------------------------------------------------------
# The Coordinator's line → code (resolution, pre-fetch, the Diarist directive, Synth block)
# ---------------------------------------------------------------------------

@check("DATA_OBJECTS start+add: created before the reply, marker set, Synth told 'being added'")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        coord = ('SPECIALISTS_TO_CALL: []\n\nDATA_OBJECTS: [{"name": "migraines", '
                 '"act": "start", "description": "headaches"}, '
                 '{"name": "migraines", "act": "add"}]')
        turn = O._resolve_data_objects(coord, persona="mike", user_turn=True)
        assert DO.resolve("migraines") is not None
        assert turn["adding"] and DO.pending_tokens()
        block = O._data_object_block(turn, [])
        assert "Migraines" in block and "not saved yet" in block, block
        directive = O._data_object_directive(turn, "diarist")
        assert "write_data_object" in directive and "migraines" in directive, directive


@check("DATA_OBJECTS read: entries pre-fetched for the Synthesizer; an unknown name is reported")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Migraines", identity="occurrence")
        DO.write_data_object("migraines", entry={"text": "left side"})
        coord = ('DATA_OBJECTS: [{"name": "my migraine log", "act": "read"}, '
                 '{"name": "dream journal", "act": "read"}]')
        turn = O._resolve_data_objects(coord, persona="mike", user_turn=True)
        block = O._data_object_block(turn, [])
        assert "left side" in block and "dream journal" in block, block


@check("no DATA_OBJECTS line, no change: nothing created, nothing marked, no block")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        turn = O._resolve_data_objects("SPECIALISTS_TO_CALL: []", persona="mike",
                                       user_turn=True)
        assert O._data_object_block(turn, []) == ""
        assert not DO.pending_tokens()


@check("a scheduled session cannot start a log or set a marker")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        coord = 'DATA_OBJECTS: [{"name": "migraines", "act": "start"}]'
        O._resolve_data_objects(coord, persona="mike", user_turn=False)
        assert DO.resolve("migraines") is None


# ---------------------------------------------------------------------------
# Fable review fixes, 2026-11-22
# ---------------------------------------------------------------------------

@check("the ACTIONS line names a log started by code and an entry queued, never NONE")
def _():
    import core.orchestrator as O
    from core.actions import action_provenance_block
    turn = {"started": [{"name": "Migraines"}],
            "adding": [{"object": {"name": "Migraines", "id": "migraines"}}]}
    rows = O._data_object_action_rows(turn)
    block = action_provenance_block(None, rows)
    assert "NONE" not in block, block
    assert "started (created)" in block and "QUEUED, NOT YET SAVED" in block, block
    assert action_provenance_block(None, []).count("NONE") == 1


@check("a specialist's write into the same log does not clear the Diarist's marker")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (user, s):
        DO.create_object("Migraines", identity="occurrence")

        def behaviour(attempt, model):
            s["caller"] = "physical_health"
            DO.archive_write(DO.get("migraines"), {"text": "specialist wrote it"})
            s["caller"] = "diarist"
            if attempt == 2:
                DO.write_data_object("migraines", entry={"text": "diarist wrote it"})
        seen = _verified(DO, behaviour)
        assert seen == [None, "reasoning-x"], seen      # the first run was NOT verified
        assert not DO.pending_tokens()


@check("a marker a restart orphaned is not cleared by the next write; it expires and is told")
def _():
    import time
    import tools.data_objects as DO
    with _sandbox("diarist") as (user, s):
        DO.create_object("Migraines", identity="occurrence")
        stale = DO.mark_pending("migraines", set_at=time.time() - 10)   # nobody owns it
        seen = _verified(DO, lambda a, m: DO.write_data_object(
            "migraines", entry={"text": "this turn"}))
        assert seen == [None], seen                     # this turn's token cleared first time
        assert len(_rows(user, "migraines")) == 1       # no duplicate from a retry
        assert DO.pending_tokens() == [stale]
        saved = DO.limits
        DO.limits = lambda: {**saved(), "pending_expiry_seconds": 1}  # noqa: E731
        try:
            assert DO.take_turn_notes() == ["Migraines"]
        finally:
            DO.limits = saved
        assert s["pushes"], "the orphaned entry was never reported"


@check("the retry is handed the entry alone, not the whole directive again")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Migraines", identity="occurrence")
        got = []
        tok = DO.mark_pending("migraines")
        DO.run_verified_write(lambda d, m: got.append(d), "FULL DIRECTIVE", [tok],
                              persona="mike", retry_model="r", retry_directive="ENTRY ONLY")
        assert got[0] == "FULL DIRECTIVE" and got[1].startswith("ENTRY ONLY"), got
        assert "FULL DIRECTIVE" not in got[1]


@check("a log kept in the daily log: a wrong-field entry is refused; a refusal never clears")
def _():
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        calls = []
        saved = DO._native_write_fn
        DO._native_write_fn = lambda store: (lambda **kw: calls.append(kw) or "Logged.")  # noqa: E731
        try:
            tok = DO.mark_pending("sleep")
            DO._LIVE.add(tok)
            out = DO.write_data_object("sleep", entry={"text": "slept 7 hours"})
            assert out.startswith("Not recorded") and not calls, out
            assert DO.pending_tokens() == [tok]
            DO._native_write_fn = lambda store: (lambda **kw: "Error: disk full")  # noqa: E731
            DO.write_data_object("sleep", entry={"sleep_hours": 7})
            assert DO.pending_tokens() == [tok], "a refusal cleared the marker"
            DO._native_write_fn = lambda store: (lambda **kw: calls.append(kw) or "Logged.")  # noqa: E731
            DO.write_data_object("sleep", entry={"sleep_hours": 7, "text": "x"})
            assert calls == [{"content": {"health": {"sleep_hours": 7}}}], calls
            assert not DO.pending_tokens()
        finally:
            DO._native_write_fn = saved
            DO._LIVE.clear()


@check("'read me my sleep log' sends the area holding the reader; the Synthesizer is told so")
def _():
    import core.orchestrator as O
    with _sandbox("diarist") as (_u, _s):
        turn = O._resolve_data_objects('DATA_OBJECTS: [{"name": "sleep log", "act": "read"}]',
                                       persona="mike", user_turn=True)
        assert [r["agent"] for r in turn["delegated"]] == ["physical_health"], turn
        assert "read back by a specialist" in O._data_object_block(turn, [])
        d = O._data_object_directive(turn, "physical_health")
        assert "LOG TO READ BACK" in d and 'object "sleep"' in d, d
        assert O._data_object_directive(turn, "finance") == ""


@check("add and read in one message: no wait, and the read says the new entry is on its way")
def _():
    import time
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Migraines", identity="occurrence")
        t0 = time.time()
        turn = O._resolve_data_objects(
            'DATA_OBJECTS: [{"name": "migraines", "act": "add"}, '
            '{"name": "migraines", "act": "read"}]', persona="mike", user_turn=True)
        assert time.time() - t0 < 2, time.time() - t0
        assert "not among them yet" in O._data_object_block(turn, [])


@check("a near name is not taken as the log; the Synthesizer is given the closest to ask about")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Wins", identity="occurrence")
        turn = O._resolve_data_objects('DATA_OBJECTS: [{"name": "wine log", "act": "add"}]',
                                       persona="mike", user_turn=True)
        assert not turn["adding"] and not DO.pending_tokens(), turn
        block = O._data_object_block(turn, [])
        assert 'No log is called "wine log"' in block and '"Wins"' in block, block


@check("an add to an archived log is not dropped silently")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox("diarist") as (_u, _s):
        DO.create_object("Migraines", identity="occurrence")
        DO.amend_data_object("migraines", "archive")
        turn = O._resolve_data_objects('DATA_OBJECTS: [{"name": "migraines", "act": "add"}]',
                                       persona="mike", user_turn=True)
        assert "is archived" in O._data_object_block(turn, []) and not DO.pending_tokens()


@check("a category carrying a path is refused by every door")
def _():
    import tools.diarist as DI
    import tools.data_objects as DO
    with _sandbox("physical_health") as (user, _s):
        (user / "archive").mkdir(parents=True)
        DO.create_object("Migraines", identity="occurrence")   # the registry file exists
        out = DI.write_archive("../x", {"title": "t"})
        assert out.startswith("Not recorded") and not (user / "x.json").exists(), out
        got = DO.read_data_object("../data_objects")
        assert "error" in got, got


@check("the places category strips coordinates though it is stored as an archive category")
def _():
    import tools.data_objects as DO
    with _sandbox("logistics") as (user, _s):
        (user / "archive").mkdir(parents=True)
        (user / "archive" / "places.json").write_text(json.dumps(
            [{"name": "Cafe", "lat": 51.4, "latlng": "51.4,-0.1", "notes": "nice"}]))
        DO.create_object("Places", identity="thing", object_id="places",
                         relevant_agents=["logistics"], tag=False)
        got = DO.read_data_object("places")
        row = got["entries"][0]
        assert "lat" not in row and "latlng" not in row and row["notes"] == "nice", row


@check("changing an entry by a word instead of a number is refused, not raised")
def _():
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (_u, _s):
        DO.create_object("Migraines", identity="occurrence")
        out = DO.amend_data_object("migraines", "change_entry", entry="two",
                                   changes={"text": "x"})
        assert out.startswith("Not changed"), out


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {err}" if err else ""))
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
