"""
tests/test_places_phase3.py — the user's places (data-objects phase 3).

archive/plans/data_objects_phase3_build_plan_2026-11-25.md § 10 (plan § 6 test 4, the parts that
are not phase 4). Same check-decorator convention as tests/test_data_objects.py (no pytest).
Every fixture is synthetic and every venue and street name is invented. Each check runs in its
own tempdir data root (core.persona._ROOT), so no real persona file is read or written.

Every live meter is stubbed: the Places lookup (tools.places.geocode_candidates /
geocode_place_name), CalDAV (the zone-suggestion path is never reached: no calendar candidates),
and model calls (none on these paths — places are code only). FCM is not on any path here.

Each check imports what it needs INSIDE its body, so on HEAD (no tools/saved_places.py) the
checks that pin new behaviour fail one by one.
"""
from __future__ import annotations

import json
import re
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.persona as P  # noqa: E402
from core.persona import persona_scope  # noqa: E402

_results = []
PERSONA = "placetest"

# Invented geography. HOME and three venues a few hundred metres away; FAR is 3 km out.
HOME = (51.50000, -0.10000)
NEAR_PIZZA = (51.50200, -0.10000)       # ~220 m north
NEAR_BRASSERIE = (51.50000, -0.09500)   # ~350 m east
NEAR_AVOID = (51.49800, -0.10100)       # ~230 m south
NEAR_CHEMIST = (51.50100, -0.10200)     # ~180 m
FAR = (51.52700, -0.10000)              # ~3 km


def check(name):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


@contextmanager
def _sandbox(caller: str = ""):
    """A tempdir data root with a home zone; the Places lookup stubbed; the data-object caller
    stubbed (empty = code). Yields (user_dir, state)."""
    import tools.data_objects as DO
    import tools.places as PL
    import tools.location as L

    state = {"lookups": [], "caller": caller, "candidates": {}}
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        saved = (P._ROOT, DO._caller, PL.geocode_candidates, PL.geocode_place_name,
                 L._last_suggest_attempt, DO.TAG_IN_BACKGROUND, DO._call_tagger)
        P._ROOT = root
        DO._caller = lambda: state["caller"]                      # noqa: E731
        DO.TAG_IN_BACKGROUND = False
        DO._call_tagger = lambda payload, persona: "[]"           # noqa: E731

        def _cands(text, max_results=3, hours=False):
            state["lookups"].append(text)
            for k, v in state["candidates"].items():
                if k.casefold() in text.casefold():
                    return {"candidates": [dict(c) for c in v]}
            return {"error": f"No place found for '{text}'."}
        PL.geocode_candidates = _cands
        PL.geocode_place_name = lambda name: {"error": "stubbed"}  # noqa: E731
        L._last_suggest_attempt = 10 ** 12          # the zone-suggestion path never runs
        user = root / "data" / "personas" / PERSONA
        user.mkdir(parents=True)
        (user / "zones.yaml").write_text(
            "zones:\n- {name: home, lat: %s, lon: %s, radius_m: 150}\n" % HOME)
        try:
            with persona_scope(PERSONA):
                yield user, state
        finally:
            (P._ROOT, DO._caller, PL.geocode_candidates, PL.geocode_place_name,
             L._last_suggest_attempt, DO.TAG_IN_BACKGROUND, DO._call_tagger) = saved


def _cand(name, lat_lon, address):
    return {"name": name, "address": address, "lat": lat_lon[0], "lon": lat_lon[1]}


def _place(state, name, lat_lon, address, **item):
    """Save a place as the Coordinator's PLACES would, and locate it (stubbed lookup)."""
    import tools.saved_places as SP
    state["candidates"][name] = [_cand(name, lat_lon, address)]
    out = SP.save({"name": name, **item}, persona=PERSONA)
    SP.locate(name, persona=PERSONA)
    return out


def _rows(user):
    p = user / "archive" / "places.json"
    return json.loads(p.read_text()) if p.exists() else []


_COORD_RE = re.compile(r"-?\d{1,3}\.\d{1,}")
_FIXTURE_COORDS = {str(v) for pt in (HOME, NEAR_PIZZA, NEAR_BRASSERIE, NEAR_AVOID, NEAR_CHEMIST,
                                    FAR) for v in pt} | {"51.5", "-0.1", "51.51", "-0.11"}


def _no_coords(text: str, where: str) -> None:
    """Any decimal number at all is suspect in these strings: distances are whole metres or
    "1.2 km". So a decimal is allowed only as "<n>.<n> km"."""
    t = re.sub(r"\b\d+\.\d km\b", "", text or "")
    hits = _COORD_RE.findall(t)
    assert not hits, f"{where} carries a coordinate-like number: {hits}\n{text}"
    for c in _FIXTURE_COORDS:
        assert c not in t, f"{where} carries a fixture coordinate {c}:\n{text}"


# ---------------------------------------------------------------------------
# 1–4: location
# ---------------------------------------------------------------------------

@check("1. zone_for matches a saved place (smallest circle wins over the home zone)")
def _():
    import tools.location as L
    with _sandbox() as (user, st):
        _place(st, "Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row")
        assert L.zone_for(*NEAR_PIZZA) == "Rossi Pizzeria"
        assert L.zone_for(*HOME) == "home"
        assert L.zone_for(*FAR) == L.AWAY
        names = [p["name"] for p in L.known_places()]
        assert names == ["home", "Rossi Pizzeria"], names


@check("2. _start_point resolves a place the user arrived at today, not home; travel is "
       "measured from it")
def _():
    import tools.location as L
    import tools.day_plan as DP
    with _sandbox() as (user, st):
        _place(st, "Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row")
        res = L.record_position(*NEAR_PIZZA, ts=datetime.now().isoformat(timespec="seconds"))
        assert res["zone"] == "Rossi Pizzeria" and res["changed"], res
        coords, name = DP._start_point(PERSONA, date.today())
        assert name == "Rossi Pizzeria", (coords, name)
        assert coords == f"{NEAR_PIZZA[0]},{NEAR_PIZZA[1]}", coords
        # The travel loop's origin is _start_point's coords; _zone_coords resolves the place
        # the same way, so a leg from it is measured from the pizzeria, not from home.
        assert DP._zone_coords("Rossi Pizzeria", PERSONA) == coords
        assert DP._zone_coords("home", PERSONA) == f"{HOME[0]},{HOME[1]}"
        # The arrival is a visit on the place, and confirms it.
        row = next(r for r in _rows(user) if r["name"] == "Rossi Pizzeria")
        assert [o.get("kind") for o in row.get("occurrences", [])] == ["visit"], row
        assert row["confirmed"] is True


@check("3. the task `zone` check accepts a saved place's name and refuses an unknown one")
def _():
    import tools.obligations as O
    with _sandbox() as (user, st):
        _place(st, "Hillcrest Chemist", NEAR_CHEMIST, "9 Hill Street")
        out = O.open_task("Collect the prescription", kind="deadline", zone="Hillcrest Chemist")
        assert not out.startswith("error"), out
        t = next(t for t in O._load(PERSONA) if t["what"] == "Collect the prescription")
        assert t["zone"] == "hillcrest chemist", t
        bad = O.open_task("Z", kind="deadline", zone="nowhere at all")
        assert bad.startswith("error: no place named"), bad


@check("4. location_last.json is one row, overwritten by each report, rounded to ~100 m")
def _():
    import tools.location as L
    with _sandbox() as (user, st):
        L.record_position(51.5012345, -0.1012345, ts="2026-11-25T09:00:00")
        L.record_position(51.5098765, -0.1098765, ts="2026-11-25T09:05:00")
        raw = (user / "location_last.json").read_text()
        row = json.loads(raw)
        assert set(row) == {"lat", "lon", "at"}, row
        assert row == {"lat": 51.51, "lon": -0.11, "at": "2026-11-25T09:05:00"}, row
        # A client clock ahead of ours is taken as now, so the row cannot stay "fresh".
        L.record_position(51.5, -0.1, ts="2099-01-01T00:00:00")
        assert json.loads((user / "location_last.json").read_text())["at"] < "2099"
        assert raw.count("{") == 1
        assert oct((user / "location_last.json").stat().st_mode)[-3:] == "600"
        # The transitions log still never holds a coordinate.
        _no_coords((user / "location_transitions.jsonl").read_text(), "transitions log")


# ---------------------------------------------------------------------------
# 5: no coordinate reaches a prompt
# ---------------------------------------------------------------------------

@check("5. no coordinate appears in any string that reaches a prompt (places block, Logistics "
       "directive, ACTIONS rows, read_data_object, the card, the location block)")
def _():
    import core.orchestrator as OR
    import tools.data_objects as DO
    import tools.location as L
    import tools.saved_places as SP
    import tools.confirm as C
    with _sandbox() as (user, st):
        st["candidates"]["Rossi Pizzeria"] = [_cand("Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row")]
        st["candidates"]["Oak Brasserie"] = [_cand("Oak Brasserie", NEAR_BRASSERIE, "2 Oak Lane")]
        L.record_position(*HOME, ts=datetime.now().isoformat(timespec="seconds"))
        coord = ('PLACES: [{"name": "Rossi Pizzeria", "act": "save", "verdict": "go_to", '
                 '"occasion": {"kind": "meal", "what": "pizza"}}, {"name": "Oak Brasserie", '
                 '"act": "save", "verdict": "try", "occasion": {"kind": "meal"}}]')
        turn = OR._resolve_places(coord, persona=PERSONA, user_text="Bianco's? no — where "
                                  "should we eat tonight?", user_turn=True)
        block = OR._places_block(turn, PERSONA, True)
        assert "Rossi Pizzeria" in block, block
        _no_coords(block, "places block")
        # Same turn again — the places near now include both, and the directive carries them.
        turn2 = OR._resolve_places("", persona=PERSONA, user_text="where should we eat tonight?",
                                   user_turn=True)
        assert turn2["near"]["lines"], turn2
        _no_coords("\n".join(turn2["near"]["lines"]), "near lines")
        directive = OR._data_object_directive({"places": turn2}, "logistics")
        assert "Rossi Pizzeria" in directive, directive
        _no_coords(directive, "Logistics directive")
        _no_coords("\n".join(OR._data_object_action_rows({"places": turn})), "ACTIONS rows")
        st["caller"] = "synthesizer"
        read = json.dumps(DO.read_data_object("places"))
        assert "Rossi Pizzeria" in read and '"lat"' not in read and '"lon"' not in read, read
        _no_coords(read, "read_data_object")
        st["caller"] = ""
        for p in C.pending(PERSONA):
            _no_coords(json.dumps(p.get("description")), "a card")
        _no_coords(L.context_block(PERSONA), "location block")
        # And the stored row DOES hold the place's public position (it is code's to use).
        row = next(r for r in _rows(user) if r["name"] == "Rossi Pizzeria")
        assert abs(row["lat"] - NEAR_PIZZA[0]) < 1e-9


# ---------------------------------------------------------------------------
# 6–8: places_near, declines, ambiguity
# ---------------------------------------------------------------------------

def _four(st):
    _place(st, "Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row", verdict="go_to",
           occasion={"kind": "meal", "what": "pizza"})
    _place(st, "Oak Brasserie", NEAR_BRASSERIE, "2 Oak Lane", verdict="try",
           occasion={"kind": "meal", "what": "a meal out"})
    _place(st, "Grey Gull Grill", NEAR_AVOID, "7 Wharf Road", verdict="avoid",
           occasion={"kind": "meal"})
    _place(st, "Bean Shed", NEAR_CHEMIST, "1 Hill Street", verdict="go_to",
           occasion={"kind": "coffee"})


@check("6. places_near filters by occasion and private, returns avoid-places, and never a "
       "try-place on a walk past")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        _four(st)
        _place(st, "Quiet Corner", NEAR_PIZZA, "5 Lantern Row", verdict="go_to",
               occasion={"kind": "meal"})
        SP.set_flag("Quiet Corner", "private", True, persona=PERSONA)
        where = {"lat": HOME[0], "lon": HOME[1]}
        walk = {p["name"]: p for p in SP.places_near(where, "meal", planned=False, persona=PERSONA)}
        assert set(walk) == {"Rossi Pizzeria", "Grey Gull Grill"}, walk
        assert walk["Grey Gull Grill"]["verdict"] == "avoid"
        plan = {p["name"] for p in SP.places_near(where, "meal", planned=True, persona=PERSONA)}
        assert plan == {"Rossi Pizzeria", "Oak Brasserie", "Grey Gull Grill"}, plan
        coffee = {p["name"] for p in SP.places_near(where, "coffee", planned=True, persona=PERSONA)}
        assert coffee == {"Bean Shed"}, coffee
        far = SP.places_near({"lat": FAR[0], "lon": FAR[1]}, "meal", planned=True, persona=PERSONA)
        assert far == [], far
        for p in SP.places_near(where, "meal", planned=True, persona=PERSONA):
            assert set(p) == {"name", "distance_m", "verdict", "occasion", "open", "signature"}


@check("7. a declined raise is not repeated until the verdict or occasion changes")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        _four(st)
        where = {"lat": HOME[0], "lon": HOME[1]}
        near = SP.places_near(where, "meal", planned=True, persona=PERSONA)
        attached = [{"name": p["name"], "occasion": "meal", "signature": p["signature"],
                     "verdict": p["verdict"]} for p in near]
        n = SP.note_reply(PERSONA, "Rossi Pizzeria is close — your usual pizza?", attached)
        assert n == 1, n
        SP.note_response(PERSONA, "no, not tonight", True)
        rows = [json.loads(x) for x in (user / "place_mentions.jsonl").read_text().splitlines()]
        assert rows[-1]["response"] == "declined", rows
        again = {p["name"] for p in SP.places_near(where, "meal", planned=True, persona=PERSONA)}
        assert "Rossi Pizzeria" not in again, again
        # The verdict changes (stated) → it may be raised again.
        SP.save({"name": "Rossi Pizzeria", "verdict": "try"}, persona=PERSONA)
        back = {p["name"] for p in SP.places_near(where, "meal", planned=True, persona=PERSONA)}
        assert "Rossi Pizzeria" in back, back


@check("8. an ambiguous name is saved confirmed: false, as the branch in the area said; a visit "
       "confirms it")
def _():
    import tools.saved_places as SP
    import tools.location as L
    with _sandbox() as (user, st):
        st["candidates"]["Corner Chemist"] = [
            _cand("Corner Chemist", FAR, "1 Far Road, Northfield"),
            _cand("Corner Chemist", NEAR_CHEMIST, "9 Hill Street, Southvale")]
        SP.save({"name": "Corner Chemist"}, persona=PERSONA)
        res = SP.locate("Corner Chemist", area="Southvale", persona=PERSONA)
        assert res["ambiguous"] and res["confirmed"] is False, res
        assert "Southvale" in res["address"], res
        assert st["lookups"] == ["Corner Chemist Southvale"], st["lookups"]
        row = next(r for r in _rows(user) if r["name"] == "Corner Chemist")
        assert row["confirmed"] is False and abs(row["lat"] - NEAR_CHEMIST[0]) < 1e-9
        # No area said: the branch nearest home.
        st["candidates"]["Twin Bakery"] = [_cand("Twin Bakery", FAR, "Far"),
                                           _cand("Twin Bakery", NEAR_PIZZA, "Near")]
        SP.save({"name": "Twin Bakery"}, persona=PERSONA)
        assert SP.locate("Twin Bakery", persona=PERSONA)["address"] == "Near"
        # One result → confirmed.
        _place(st, "Solo Deli", NEAR_BRASSERIE, "3 Oak Lane")
        assert next(r for r in _rows(user) if r["name"] == "Solo Deli")["confirmed"] is True
        L.record_position(*NEAR_CHEMIST, ts=datetime.now().isoformat(timespec="seconds"))
        assert next(r for r in _rows(user) if r["name"] == "Corner Chemist")["confirmed"] is True


# ---------------------------------------------------------------------------
# 9–10: "keeps coming up", errands
# ---------------------------------------------------------------------------

@check("9. three mentions of an unsaved place raise the question once; a decline keeps it hidden")
def _():
    import tools.saved_places as SP
    import tools.confirm as C
    with _sandbox() as (user, st):
        assert SP.on_place_fact(PERSONA, "Lantern Bar", "we ended up at Lantern Bar") \
            == "place_counted"
        SP.on_place_fact(PERSONA, "Lantern Bar", "Lantern Bar again")
        assert SP.take_offer(PERSONA, True) is None           # two: nothing yet
        assert SP.on_place_fact(PERSONA, "lantern bar", "...") == "place_offer_held"
        assert SP.take_offer(PERSONA, False) is None          # never on a scheduled turn
        offer = SP.take_offer(PERSONA, True)
        assert offer and "Lantern Bar" in offer["question"], offer
        again = SP.take_offer(PERSONA, True)
        assert again and again.get("still_open"), again
        cards = [p for p in C.pending(PERSONA) if p.get("action") == "save_place"]
        assert len(cards) == 1, cards
        C.decline(cards[0]["token"], PERSONA)
        assert SP.take_offer(PERSONA, True) is None
        assert SP.find("Lantern Bar") is None                 # out of every list
        hidden = SP.find("Lantern Bar", include_hidden=True)
        assert hidden and hidden["hidden"] is True, hidden
        assert "Lantern Bar" not in [p["name"] for p in SP.positioned(PERSONA)]
        # Further mentions count again; at double the count it is asked once more.
        for _ in range(3):
            SP.on_place_fact(PERSONA, "Lantern Bar", "...")
        assert SP.take_offer(PERSONA, True), "re-offered at double"


@check("9b. Yes on the card saves the place with its mentions carried over")
def _():
    import tools.saved_places as SP
    import tools.confirm as C
    with _sandbox() as (user, st):
        st["candidates"]["Fern Cafe"] = [_cand("Fern Cafe", NEAR_PIZZA, "6 Fern Walk")]
        for _ in range(3):
            SP.on_place_fact(PERSONA, "Fern Cafe", "Fern Cafe")
        SP.take_offer(PERSONA, True)
        card = next(p for p in C.pending(PERSONA) if p.get("action") == "save_place")
        C.approve(card["token"], PERSONA)
        out = C.execute(card["token"], PERSONA)
        assert "Saved Fern Cafe" in json.dumps(out), out
        import threading
        for th in threading.enumerate():
            if th.name == "place_lookup":
                th.join(5)
        row = SP.find("Fern Cafe")
        assert row and [o["kind"] for o in row["occurrences"]] == ["mention"] * 3, row
        assert "lat" in row


@check("10. a task's place joins in code: near the chemist, the open task there is raised")
def _():
    import tools.obligations as O
    import tools.saved_places as SP
    import tools.location as L
    with _sandbox() as (user, st):
        _place(st, "Hillcrest Chemist", NEAR_CHEMIST, "9 Hill Street")
        O.open_task("Collect the prescription", kind="deadline", zone="Hillcrest Chemist")
        L.record_position(*HOME, ts=datetime.now().isoformat(timespec="seconds"))
        errs = SP.errands_near({"lat": HOME[0], "lon": HOME[1]}, PERSONA)
        assert [e["task"] for e in errs] == ["Collect the prescription"], errs
        turn = SP.turn_places(PERSONA, "anything I should do while I'm out?", True)
        assert any("Collect the prescription" in ln for ln in turn["lines"]), turn
        assert not SP.errands_near({"lat": FAR[0], "lon": FAR[1]}, PERSONA)
        # Named in the reply → raised once today; not attached again the same day.
        SP.note_reply(PERSONA, "Hillcrest Chemist is round the corner — the prescription?",
                      turn["attached"])
        again = SP.turn_places(PERSONA, "anything else?", True)
        assert not any("prescription" in ln for ln in again["lines"]), again


# ---------------------------------------------------------------------------
# 11–13: provenance, one writer, occasion kinds
# ---------------------------------------------------------------------------

@check("11. guarded fields: a derived value never replaces a stated one (held; asked on the "
       "second time); a stated change wins, keeps the old in previous and is said once")
def _():
    import tools.data_objects as DO
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        SP.save({"name": "Rossi Pizzeria", "verdict": "avoid"}, persona=PERSONA)
        o = DO.get("places")
        DO.archive_write(o, {"name": "Rossi Pizzeria", "verdict": "go_to", "derived": True},
                         by_code=True)
        row = SP.find("Rossi Pizzeria")
        assert row["verdict"] == "avoid" and row["pending_verdict"]["count"] == 1, row
        assert DO.take_change_notes() == []
        DO.archive_write(o, {"name": "Rossi Pizzeria", "verdict": "go_to", "derived": True},
                         by_code=True)
        notes = DO.take_change_notes()
        assert len(notes) == 1 and "Ask once" in notes[0], notes
        SP.save({"name": "Rossi Pizzeria", "verdict": "go_to"}, persona=PERSONA)
        row = SP.find("Rossi Pizzeria")
        assert row["verdict"] == "go_to" and "pending_verdict" not in row, row
        assert row["previous"][-1]["value"]["verdict"] == "avoid", row["previous"]
        notes = DO.take_change_notes()
        assert len(notes) == 1 and "changed from \"avoid\" to \"go to\"" in notes[0], notes
        assert DO.take_change_notes() == []                    # said once
        # The reader never sees the provenance bookkeeping.
        st["caller"] = "synthesizer"
        entry = DO.read_data_object("places")["entries"][0]
        assert not any(k.endswith("_source") or k.startswith("pending_") for k in entry), entry


@check("12. one writer: every model door into places refuses; the derived writer skips it")
def _():
    import tools.data_objects as DO
    import tools.diarist as DI
    import tools.saved_places as SP
    import tools.noticed_logs as NL
    with _sandbox(caller="diarist") as (user, st):
        st["caller"] = ""
        SP.save({"name": "Rossi Pizzeria"}, persona=PERSONA)
        for agent in ("diarist", "logistics", "recreation_hobbies", "synthesizer"):
            st["caller"] = agent
            a = DI.write_archive("places", {"name": "Rossi Pizzeria", "lat": 1, "lon": 2,
                                            "verdict": "avoid"})
            b = DO.write_data_object("places", {"name": "Somewhere New"})
            c = DO.amend_data_object("places", "change_entry", entry=1,
                                     changes={"verdict": "avoid"})
            assert all(x.startswith("Not ") for x in (a, b, c)), (agent, a, b, c)
        st["caller"] = ""
        row = SP.find("Rossi Pizzeria")
        assert "lat" not in row and "verdict" not in row, row
        assert SP.find("Somewhere New") is None
        out = NL.derived(PERSONA, "rid1", {"target": "places", "proposal": {"name": "X"}},
                         [], frozenset(), user_text="")
        assert out in ("derived_code_kept", "derived_off"), out


@check("13. a user's own occasion kind is added to their kinds, never mapped onto a base kind; "
       "'avoid' is a verdict, not an occasion")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        assert "climbing" not in SP.occasion_kinds()
        SP.save({"name": "Crag Wall", "occasion": {"kind": "Climbing", "what": "bouldering"}},
                persona=PERSONA)
        assert "climbing" in SP.occasion_kinds(), SP.occasion_kinds()
        assert SP.find("Crag Wall")["occasion"] == {"kind": "climbing", "what": "bouldering"}
        assert SP.normalise_occasion("avoid") is None
        assert SP.normalise_verdict("not again") == "avoid"
        assert SP.normalise_verdict("go-to") == "go_to"


@check("14. two different verdicts for one place in one turn: neither written, one question")
def _():
    import core.orchestrator as OR
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        coord = ('PLACES: [{"name": "Rossi Pizzeria", "act": "save", "verdict": "go_to"}, '
                 '{"name": "rossi pizzeria", "act": "save", "verdict": "avoid"}]')
        turn = OR._resolve_places(coord, persona=PERSONA, user_text="x", user_turn=True)
        assert turn["conflicts"] == ["Rossi Pizzeria"], turn
        assert SP.find("Rossi Pizzeria") is None
        assert "ask once which" in OR._places_block(turn, PERSONA, True)
        # A scheduled turn writes nothing at all.
        turn = OR._resolve_places('PLACES: [{"name": "Rossi Pizzeria", "act": "save"}]',
                                  persona=PERSONA, user_text="", user_turn=False)
        assert not turn["saved"] and SP.find("Rossi Pizzeria") is None


@check("15. a meal said in the past tense is a log, not an occasion; planning words mark a plan")
def _():
    import tools.saved_places as SP
    assert SP.occasion_for_turn("we had pizza last night") is None
    assert SP.occasion_for_turn("where should we eat tonight?") == ("meal", True)
    assert SP.occasion_for_turn("I'm hungry") == ("meal", False)
    assert SP.occasion_for_turn("fancy a coffee later?") == ("coffee", True)
    assert SP.occasion_for_turn("booked the dentist") is None


# ---------------------------------------------------------------------------
# Fable diff review, 2026-11-26 — one check per finding fixed
# ---------------------------------------------------------------------------

@check("R1. a merge INTO places is refused — a model cannot carry a position in that way")
def _():
    import tools.data_objects as DO
    import tools.location as L
    with _sandbox() as (user, st):
        DO.create_object("Eateries", description="d", identity="thing")
        DO.write_data_object("Eateries", {"name": "Fake Cafe", "lat": NEAR_PIZZA[0],
                                          "lon": NEAR_PIZZA[1], "radius_m": 5000})
        st["caller"] = "synthesizer"
        out = DO.amend_data_object("Eateries", "merge", into="Places")
        assert out.startswith("Not merged"), out
        assert L.zone_for(*FAR) == L.AWAY


@check("R2. DATA_OBJECTS add/amend on Places marks nothing on its way and says it is code's")
def _():
    import core.orchestrator as OR
    with _sandbox() as (user, st):
        turn = OR._resolve_data_objects('DATA_OBJECTS: [{"name": "my places", "act": "add"}, '
                                        '{"name": "Places", "act": "amend"}]', persona=PERSONA)
        assert not turn["adding"] and not turn["amending"], turn
        assert [o["id"] for o in turn["code_kept"]] == ["places"], turn
        block = OR._data_object_block(turn, [])
        assert "kept by code" in block and "being added" not in block, block
        assert not OR._data_object_directive(turn, "diarist")


@check("R3. a bare 'no' to another question declines nothing; an avoid raise is never declined")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        _four(st)
        where = {"lat": HOME[0], "lon": HOME[1]}
        near = SP.places_near(where, "meal", planned=True, persona=PERSONA)
        att = [{"name": p["name"], "occasion": "meal", "signature": p["signature"],
                "verdict": p["verdict"]} for p in near]
        SP.note_reply(PERSONA, "Rossi Pizzeria is close — not the Grey Gull Grill, though. Did "
                      "you take your meds?", att)
        SP.note_response(PERSONA, "no, not yet", True)
        rows = [json.loads(x) for x in (user / "place_mentions.jsonl").read_text().splitlines()]
        assert {r["response"] for r in rows} == {"none"}, rows
        SP.note_reply(PERSONA, "The Grey Gull Grill is the one to skip.", att)
        SP.note_response(PERSONA, "no, definitely not there, somewhere else", True)
        rows = [json.loads(x) for x in (user / "place_mentions.jsonl").read_text().splitlines()]
        gull = [r for r in rows if r["place"] == "Grey Gull Grill"]
        assert gull and all(r["response"] == "none" for r in gull), gull
        # Past the 12 h cooldown it is raised again — a decline never silences it.
        SP._now = lambda: datetime.now() + timedelta(hours=13)
        try:
            again = {p["name"] for p in SP.places_near(where, "meal", planned=True,
                                                       persona=PERSONA)}
        finally:
            SP._now = lambda: datetime.now()
        assert "Grey Gull Grill" in again, again
        # A real decline of the one place offered is remembered.
        SP.note_reply(PERSONA, "Oak Brasserie?", [a for a in att if a["name"] == "Oak Brasserie"])
        SP.note_response(PERSONA, "rather not tonight", True)
        assert "Oak Brasserie" not in {p["name"] for p in
                                       SP.places_near(where, "meal", planned=True,
                                                      persona=PERSONA)}


@check("R4. an avoid with no occasion is avoided for anything; 'dinner' is a meal; a user's own "
       "kind fires when the turn names it")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        where = {"lat": HOME[0], "lon": HOME[1]}
        _place(st, "Clip Stone", NEAR_AVOID, "7 Wharf Road", verdict="avoid")
        _place(st, "Dino Diner", NEAR_PIZZA, "4 Lantern Row", verdict="go_to",
               occasion={"kind": "dinner"})
        _place(st, "Crag Wall", NEAR_BRASSERIE, "2 Oak Lane", verdict="go_to",
               occasion={"kind": "climbing", "what": "bouldering"})
        meal = {p["name"] for p in SP.places_near(where, "meal", planned=True, persona=PERSONA)}
        assert meal == {"Clip Stone", "Dino Diner"}, meal
        assert SP.find("Dino Diner")["occasion"] == {"kind": "meal", "what": "dinner"}
        import tools.location as L
        L.record_position(*HOME, ts=datetime.now().isoformat(timespec="seconds"))
        turn = SP.turn_places(PERSONA, "thinking of some bouldering this afternoon", True)
        assert any("Crag Wall" in ln for ln in turn["lines"]), turn


@check("R5. saving a similar name never overwrites a different place")
def _():
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        SP.save({"name": "Nandor's Brixton", "verdict": "go_to"}, persona=PERSONA)
        out = SP.save({"name": "Nandor's Brighton", "verdict": "avoid"}, persona=PERSONA)
        assert out["status"] == "saved" and out["name"] == "Nandor's Brighton", out
        assert SP.find("Nandor's Brixton")["verdict"] == "go_to"
        assert SP.set_flag("Nandor's Brightn", "removed", persona=PERSONA) == "unknown"


@check("R6. arriving at a zone never records a visit on a similarly named saved place")
def _():
    import tools.saved_places as SP
    import tools.location as L
    with _sandbox() as (user, st):
        st["candidates"]["The Home"] = [_cand("The Home", FAR, "Far"),
                                        _cand("The Home", NEAR_PIZZA, "Near")]
        SP.save({"name": "The Home"}, persona=PERSONA)
        SP.locate("The Home", persona=PERSONA)
        L.record_position(*FAR, ts="2026-11-26T08:00:00")
        L.record_position(*HOME, ts=datetime.now().isoformat(timespec="seconds"))
        row = SP.find("The Home")
        assert not row.get("occurrences") and row["confirmed"] is False, row


@check("R7. a private place's name is not in the block's header, the task-zone error, or another "
       "agent's read; a hidden name is in nobody's read")
def _():
    import tools.saved_places as SP
    import tools.obligations as O
    import tools.data_objects as DO
    import tools.location as L
    with _sandbox() as (user, st):
        _four(st)
        clinic = (51.50150, -0.10350)
        _place(st, "Quiet Clinic", clinic, "8 Hill Street")
        SP.set_flag("Quiet Clinic", "private", True, persona=PERSONA)
        DO.archive_write(DO.get("places"), {"name": "Never Saved Bar", "hidden": True},
                         by_code=True)
        L.record_position(*clinic, ts=datetime.now().isoformat(timespec="seconds"))
        assert L.current_zone()["zone"] == "Quiet Clinic", L.current_zone()
        turn = SP.turn_places(PERSONA, "where should we eat tonight?", True)
        assert turn["lines"] and "Quiet Clinic" not in "\n".join(turn["lines"]), turn
        err = O.open_task("Z", kind="deadline", zone="nowhere")
        assert "quiet clinic" not in err, err
        assert not O.open_task("Y", kind="deadline", zone="Quiet Clinic").startswith("error")
        for agent in ("logistics", "recreation_hobbies"):
            st["caller"] = agent
            names = [e["name"] for e in DO.read_data_object("places")["entries"]]
            assert "Quiet Clinic" not in names and "Never Saved Bar" not in names, (agent, names)
        st["caller"] = "synthesizer"
        names = [e["name"] for e in DO.read_data_object("places")["entries"]]
        assert "Quiet Clinic" in names and "Never Saved Bar" not in names, names


@check("R8. 'save it and keep it private' in one turn does both")
def _():
    import core.orchestrator as OR
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        turn = OR._resolve_places('PLACES: [{"name": "Rossi Pizzeria", "act": "save", '
                                  '"verdict": "go_to"}, {"name": "Rossi Pizzeria", '
                                  '"act": "private"}]', persona=PERSONA, user_text="x",
                                  user_turn=True)
        assert SP.find("Rossi Pizzeria")["private"] is True
        assert [f["flag"] for f in turn["flags"]] == ["kept private"], turn
        OR._resolve_places('PLACES: [{"name": "Bean Shed", "act": "save", "private": true}]',
                           persona=PERSONA, user_text="x", user_turn=True)
        assert SP.find("Bean Shed")["private"] is True


@check("R9. 'no, the one in Southvale' relocates to another branch, unconfirmed; an ambiguous "
       "unconfirmed place is not raised; a late ambiguity is asked on the next turn")
def _():
    import core.orchestrator as OR
    import tools.saved_places as SP
    with _sandbox() as (user, st):
        st["candidates"]["Corner Chemist"] = [
            _cand("Corner Chemist", FAR, "1 Far Road, Northfield"),
            _cand("Corner Chemist", NEAR_CHEMIST, "9 Hill Street, Southvale")]
        SP.save({"name": "Corner Chemist", "verdict": "go_to",
                 "occasion": {"kind": "errand"}}, persona=PERSONA)
        SP.locate("Corner Chemist", area="Northfield", persona=PERSONA)   # the wrong branch
        row = SP.find("Corner Chemist")
        first = (row["lat"], row["lon"])
        assert row["ambiguous"] and not row["confirmed"]
        assert SP.places_near({"lat": first[0], "lon": first[1]}, "errand", planned=True,
                              persona=PERSONA) == []
        lines = SP.unsaid_ambiguities(PERSONA)
        assert [a["name"] for a in lines] == ["Corner Chemist"] and SP.unsaid_ambiguities(
            PERSONA) == []
        turn = OR._resolve_places('PLACES: [{"name": "Corner Chemist", "act": "relocate", '
                                  '"area": "Southvale"}]', persona=PERSONA, user_text="x",
                                  user_turn=True)
        OR._places_block(turn, PERSONA, True)
        for b in turn["lookups"]:
            b["thread"].join(5)
        row = SP.find("Corner Chemist")
        assert (row["lat"], row["lon"]) != first and "Southvale" in row["address"], row
        assert row["confirmed"] is False
        assert row["previous"], "the old position is kept in history"
        SP.confirm("Corner Chemist", persona=PERSONA)
        assert SP.places_near({"lat": HOME[0], "lon": HOME[1]}, "errand", planned=True,
                              persona=PERSONA)


@check("R12. a user's own field ending in _source is not hidden from readers")
def _():
    import tools.data_objects as DO
    with _sandbox() as (user, st):
        DO.create_object("Recipes", description="d", identity="thing")
        DO.write_data_object("Recipes", {"title": "Dal", "protein_source": "lentils"})
        st["caller"] = "synthesizer"
        DO.get("recipes")
        e = DO.read_data_object("Recipes")["entries"][0]
        assert e.get("protein_source") == "lentils", e


@check("R14. a saved place inside the home zone never turns 'home' into the cafe; an inaccurate "
       "fix never matches a place")
def _():
    import tools.location as L
    with _sandbox() as (user, st):
        _place(st, "Next Door Cafe", (HOME[0] + 0.0003, HOME[1]), "3 Home Street")
        assert L.zone_for(HOME[0] + 0.0003, HOME[1]) == "home"
        _place(st, "Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row")
        assert L.zone_for(*NEAR_PIZZA, accuracy=500) == L.AWAY
        assert L.zone_for(*NEAR_PIZZA, accuracy=20) == "Rossi Pizzeria"


@check("C1. read_data_object(contains=<digits of a position>) finds nothing")
def _():
    import tools.data_objects as DO
    with _sandbox() as (user, st):
        _place(st, "Rossi Pizzeria", NEAR_PIZZA, "4 Lantern Row")
        st["caller"] = "synthesizer"
        assert DO.read_data_object("places", contains="51.502")["entries"] == []
        assert DO.read_data_object("places", contains="Lantern")["entries"]


@check("C2. every origin and path that reaches a prompt carries no coordinate — last position, "
       "planned, home, errands, change notes, the card's result, an ambiguity line")
def _():
    import core.orchestrator as OR
    import tools.data_objects as DO
    import tools.location as L
    import tools.saved_places as SP
    import tools.obligations as O
    import tools.confirm as C
    with _sandbox() as (user, st):
        _four(st)
        _place(st, "Hillcrest Chemist", NEAR_CHEMIST, "9 Hill Street")
        O.open_task("Collect the prescription", kind="deadline", zone="Hillcrest Chemist")
        texts = []
        L.record_position(51.5003, -0.1003, ts=datetime.now().isoformat(timespec="seconds"))
        L.record_position(51.5300, -0.1500, ts=datetime.now().isoformat(timespec="seconds"))
        L.record_position(*HOME, accuracy=500,
                          ts=datetime.now().isoformat(timespec="seconds"))
        for txt in ("where should we eat tonight?", "dinner tomorrow?", "anything nearby?"):
            t = OR._resolve_places("", persona=PERSONA, user_text=txt, user_turn=True)
            texts.append(OR._places_block(t, PERSONA, True))
            texts.append(OR._data_object_directive({"places": t}, "logistics"))
        SP.save({"name": "Rossi Pizzeria", "verdict": "avoid"}, persona=PERSONA)
        texts += DO.take_change_notes()
        st["candidates"]["Twin Bakery"] = [_cand("Twin Bakery", FAR, "Far Lane"),
                                           _cand("Twin Bakery", NEAR_PIZZA, "Near Lane")]
        t = OR._resolve_places('PLACES: [{"name": "Twin Bakery", "act": "save"}]',
                               persona=PERSONA, user_text="x", user_turn=True)
        texts.append(OR._places_block(t, PERSONA, True))
        for _ in range(3):
            SP.on_place_fact(PERSONA, "Lantern Bar", "Lantern Bar")
        st["candidates"]["Lantern Bar"] = [_cand("Lantern Bar", NEAR_PIZZA, "1 Lantern Row")]
        texts.append(json.dumps(SP.take_offer(PERSONA, True)))
        card = next(p for p in C.pending(PERSONA) if p.get("action") == "save_place")
        texts.append(json.dumps(card.get("description")))
        C.approve(card["token"], PERSONA)
        texts.append(json.dumps(C.execute(card["token"], PERSONA)))
        texts.append(json.dumps(DO.list_data_objects()))
        texts.append(L.context_block(PERSONA))
        texts.append(O.open_task("Z", kind="deadline", zone="nowhere"))
        st["caller"] = "synthesizer"
        texts.append(json.dumps(DO.read_data_object("places")))
        assert any("Twin Bakery" in x for x in texts) and any("Rossi" in x for x in texts)
        for i, x in enumerate(texts):
            _no_coords(x, f"text {i}")


@check("C4. a Plus Code never survives in a lookup's address")
def _():
    import tools.places as PL
    assert PL._no_plus_code("GV4C+XV, Southvale") == "Southvale"
    assert PL._no_plus_code("9C3XGV4C+XV") is None
    assert PL._no_plus_code("4 Lantern Row, Southvale") == "4 Lantern Row, Southvale"


@check("M3. the seed corrects a row before its lookup: a rename (no alias unless asked), a "
       "postcode-only lookup that sends nothing else, skip, visits, private, purpose; hours "
       "stored and kept out of reads")
def _():
    import importlib.util
    import tools.data_objects as DO
    import tools.saved_places as SP
    spec = importlib.util.spec_from_file_location(
        "seed_places", Path(__file__).parent.parent / "scripts" / "seed_places.py")
    seed = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seed)
    seed._ask = lambda prompt: True
    with _sandbox() as (user, st):
        o = DO.get("places")
        for name, loc in (("Old Curry House", "Lane Street"), ("Tripx", "Abroad"),
                          ("Friends' home Pvel", "1 Quiet Road, ZZ1 2YY")):
            DO.archive_write(o, {"name": name, "location": loc, "notes": "from before"},
                             by_code=True)
        periods = [{"open": {"day": d, "hour": 12, "minute": 0},
                    "close": {"day": d, "hour": 22, "minute": 0}} for d in range(7)]
        st["candidates"]["New Curry House"] = [dict(_cand("New Curry House", NEAR_PIZZA,
                                                          "2 Lane Street"), hours=periods)]
        st["candidates"]["ZZ1 2YY"] = [_cand("ZZ1 2YY", NEAR_BRASSERIE, "ZZ1 2YY")]
        adds = [
            {"was": "Old Curry House", "name": "New Curry House", "verdict": "go_to",
             "occasion": {"kind": "meal", "what": "Indian"}, "visits": ["2026-10-04"],
             "notes": "a favourite"},
            {"name": "Tripx", "skip": True},
            {"was": "Friends' home Pvel", "name": "Friends' home Pavel", "private": True,
             "lookup_text": "ZZ1 2YY", "keep_old_name": True, "visits": ["2026-09-13"]},
        ]
        rows = [r for r in SP._rows() if SP._live(r, include_hidden=True)]
        steps, unmatched = seed.plan(rows, adds)
        assert not unmatched and all(s["fix"] for s in steps), (steps, unmatched)
        before = dict(SP.find("Tripx"))
        for stp in steps:
            seed.apply_step(stp, PERSONA, SP, DO)
        assert st["lookups"] == ["New Curry House Lane Street", "ZZ1 2YY"], st["lookups"]
        curry = SP.find("New Curry House")
        assert curry["verdict"] == "go_to" and "lat" in curry and curry["hours"] == periods
        assert curry["notes"] == "from before; a favourite", curry["notes"]
        assert [o["at"] for o in curry["occurrences"]] == ["2026-10-04"]
        assert SP.find("Old Curry House") is None, "no alias for a wrong name"
        assert SP.find("Tripx") == before, "a skipped row is untouched"
        home = SP.find("Friends' home Pavel")
        assert home["private"] is True and "lat" in home
        assert SP.find("Friends' home Pvel")["name"] == "Friends' home Pavel", "typo alias kept"
        # Opening hours: stored, used by code, never in what an agent reads.
        st["caller"] = "synthesizer"
        e = next(x for x in DO.read_data_object("places")["entries"]
                 if x["name"] == "New Curry House")
        assert "hours" not in e and "last_said_at" not in e, e
        # A re-run (the first live run found no key) corrects the same rows again and adds
        # nothing twice: the renamed row is still matched, the note is not appended again.
        rows = [r for r in SP._rows() if SP._live(r, include_hidden=True)]
        steps, unmatched = seed.plan(rows, adds)
        assert not unmatched, unmatched
        for stp in steps:
            seed.apply_step(stp, PERSONA, SP, DO)
        curry = SP.find("New Curry House")
        assert curry["notes"] == "from before; a favourite", curry["notes"]
        assert len(curry["occurrences"]) == 1, curry["occurrences"]
        closed_at = datetime.now().replace(hour=8, minute=0)
        assert SP.places_near({"lat": HOME[0], "lon": HOME[1]}, "meal", at=closed_at,
                              planned=True, persona=PERSONA) == []
        assert SP.places_near({"lat": HOME[0], "lon": HOME[1]}, "meal", at=None,
                              planned=True, persona=PERSONA)


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {err}" if err else ""))
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
