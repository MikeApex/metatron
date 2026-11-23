"""
tests/test_noticed_logs.py — the user's logs, phase 2: noticing and promotion.

archive/plans/data_objects_phase2_build_plan_2026-11-22.md § 5 (tests 1–17); parent plan
archive/plans/custom_logs_and_places_plan_2026-11-21.md § 6 tests 3 and 5 (phase 2 parts).

No model is called and no meter is touched: the matcher (`noticed_logs._call_matcher`), the
relevance tagger (`data_objects._call_tagger`) and push (`data_objects._send_push`) are stubbed;
nothing here reaches FCM, CalDAV or the Places API. The persona tree is a temporary directory.
Same check-decorator convention as tests/test_data_objects.py (no pytest): each check imports
what it needs inside its body, so on HEAD — where tools/noticed_logs.py does not exist — the
checks fail one by one rather than the file failing at import.

Run:
    python tests/test_noticed_logs.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from contextlib import contextmanager
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core import persona as persona_mod  # noqa: E402
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


P = "nl_test"
P2 = "nl_other"
_GRANTS = {
    "synthesizer": ["list_data_objects", "read_data_object", "amend_data_object"],
    "diarist": ["write_archive", "list_data_objects", "read_data_object", "write_data_object"],
}


@contextmanager
def _sandbox(matcher=None, persona: str = P, cfg: dict | None = None):
    """A fresh persona tree in a tempdir; capture's config, the matcher, the tagger, push and
    the grants stubbed. Yields (user_dir, state)."""
    import tools.capture as C
    import tools.data_objects as DO
    import tools.noticed_logs as NL

    state = {"matcher_calls": [], "caller": ""}
    base = {**C._DEFAULTS, "enabled": True, "holdout_rate": 0.0,
            "modes": {"synthesizer": "shadow", "goals_interviewer": "on"},
            "noticed_logs": "ask", "noticed_raise_count": 3, "noticed_window_days": 30,
            "noticed_card_ttl_hours": 2, "derived_entries": "shadow"}
    base.update(cfg or {})

    def _matcher(payload, persona):
        state["matcher_calls"].append(json.loads(payload))
        out = matcher(json.loads(payload)) if matcher else {"verdict": "none"}
        return json.dumps(out) if isinstance(out, dict) else str(out)

    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for p in (P, P2):
            (tmp / "config" / "personas" / p).mkdir(parents=True, exist_ok=True)
            (tmp / "data" / "personas" / p).mkdir(parents=True, exist_ok=True)
        saved = [(persona_mod, "_ROOT", persona_mod._ROOT), (C, "config", C.config),
                 (NL, "_call_matcher", NL._call_matcher),
                 (NL, "MATCH_IN_BACKGROUND", NL.MATCH_IN_BACKGROUND),
                 (DO, "_call_tagger", DO._call_tagger), (DO, "_send_push", DO._send_push),
                 (DO, "_quality_event", DO._quality_event),
                 (DO, "_allowed_tools", DO._allowed_tools), (DO, "_caller", DO._caller),
                 (DO, "TAG_IN_BACKGROUND", DO.TAG_IN_BACKGROUND)]
        persona_mod._ROOT = tmp
        C.config = lambda: dict(base)                                  # noqa: E731
        NL._call_matcher = _matcher
        NL.MATCH_IN_BACKGROUND = False
        DO._call_tagger = lambda payload, persona: "[]"                # noqa: E731
        DO._send_push = lambda *a, **k: None                           # noqa: E731
        DO._quality_event = lambda **k: None                           # noqa: E731
        DO._allowed_tools = lambda agent: _GRANTS.get(agent)           # noqa: E731
        DO._caller = lambda: state["caller"]                           # noqa: E731
        DO.TAG_IN_BACKGROUND = False
        try:
            with persona_scope(persona):
                yield tmp / "data" / "personas" / persona, state
        finally:
            for obj, name, value in saved:
                setattr(obj, name, value)


def _mention(category: str, say: str, n: int = 1, days_ago: int = 0, persona: str = P):
    """Record `n` uncategorised facts the way capture's `other` route does."""
    import tools.capture as C
    for i in range(n):
        saved = C._now
        C._now = lambda d=days_ago: datetime.now() - timedelta(days=d)   # noqa: E731
        try:
            C.record_uncategorised(persona, "synthesizer",
                                   {"category": category, "say": f"{say} {i + 1}"})
        finally:
            C._now = saved


def _new(name="Places to try", ask="a list of the places you've mentioned wanting to try"):
    return lambda payload: {"verdict": "new", "name": name, "description": "Places the user "
                            "wants to try.", "ask": ask, "identity": "thing"}


def _pending(persona: str = P) -> list[dict]:
    from tools.confirm import pending
    return pending(persona)


def _tap_yes(token: str, persona: str = P) -> dict:
    from tools.confirm import approve, execute
    assert approve(token, persona)
    return execute(token, persona)


def _rows(user: Path, cat: str) -> list:
    p = user / "archive" / f"{cat}.json"
    return json.loads(p.read_text()) if p.exists() else []


# ---------------------------------------------------------------------------
# 1. The detector
# ---------------------------------------------------------------------------

@check("1. three mentions in 30 days hold an offer; two do not; three outside the window do not")
def _():
    import tools.noticed_logs as NL
    with _sandbox(_new()) as (_u, st):
        _mention("place to try", "wants to try a place", n=2)
        assert not NL.offers(P), NL.offers(P)
        _mention("old thing", "an old fact", n=2, days_ago=40)
        _mention("old thing", "an old fact", n=1)
        assert not NL.offers(P), "facts outside the window crossed the threshold"
        _mention("place to try", "wants to try a place", n=1)
        held = [o for o in NL.offers(P) if o["status"] == "held"]
        assert len(held) == 1 and held[0]["kind"] == "create", NL.offers(P)
        assert len(st["matcher_calls"]) == 1
        assert not _pending(), "a card was raised at detection"


@check("2. a match on an archive log becomes an alias card; a match on a store raises none")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(lambda p: {"verdict": "match", "log": "restaurants",
                             "about": "the places you've mentioned wanting to try"}) as (_u, _s):
        DO.create_object("Restaurants", description="Restaurants to try.", identity="thing")
        _mention("place to try", "wants to try a place", n=3)
        offer = NL.take_offer(P)
        assert offer and offer["kind"] == "alias", offer
        cards = _pending()
        assert [c["action"] for c in cards] == ["alias_data_object"], cards
        assert "Restaurants" in cards[0]["description"], cards
    with _sandbox(lambda p: {"verdict": "match", "log": "contacts",
                             "about": "the people you've met"}) as (_u, _s):
        DO.register_store("contacts", "Contacts", "People the user knows.")
        _mention("person met", "met someone", n=3)
        assert NL.take_offer(P) is None and not _pending()
        assert any(o["status"] == "home" for o in NL.offers(P)), NL.offers(P)


@check("3. a declined category is not re-offered at 5 mentions, and is at 6 (declined at 3)")
def _():
    import tools.noticed_logs as NL
    from tools.confirm import decline
    with _sandbox(_new()) as (_u, st):
        _mention("place to try", "wants to try a place", n=3)
        offer = NL.take_offer(P)
        assert decline(offer["token"], P)
        NL.reconcile(P)
        assert any(o["status"] == "no" for o in NL.offers(P)), NL.offers(P)
        _mention("place to try", "another place", n=2)
        assert NL.take_offer(P) is None, "re-offered before the count doubled"
        _mention("place to try", "one more place", n=1)
        again = NL.take_offer(P)
        assert again and again["kind"] == "create", NL.offers(P)


@check("4. yes creates the log with origin noticed, the category as an alias, the held facts in")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(_new()) as (user, _s):
        _mention("place to try", "wants to try Bianco", n=3)
        offer = NL.take_offer(P)
        _mention("place to try", "wants to try Clipstone", n=1)    # between question and tap
        out = _tap_yes(offer["token"])
        assert out["status"] == "executed", out
        o = DO.resolve("Places to try")
        assert o and o["origin"] == "noticed" and "place to try" in o["aliases"], o
        rows = _rows(user, o["id"])
        assert len(rows) == 4 and all(r.get("source") == "noticed" for r in rows), rows
        assert any("Clipstone" in r["text"] for r in rows), rows
        NL.reconcile(P)
        assert [x["status"] for x in NL.offers(P)] == ["yes"], NL.offers(P)


# ---------------------------------------------------------------------------
# 5. The derived writer
# ---------------------------------------------------------------------------

@check("5. the derived writer writes nothing in shadow, and records the proposal")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox() as (user, _s):
        DO.create_object("Migraines", identity="occurrence")
        before = (user / "archive" / "migraines.json").exists()
        c = {"kind": "entry", "target": "migraines", "disposition": "save",
             "proposal": {"text": "a migraine this morning"}, "say": "had a migraine",
             "quote": "migraine this morning"}
        out = NL.derived(P, "rid1", c, [], frozenset(), user_text="I had a migraine")
        assert out == "derived_shadow", out
        assert not before and not (user / "archive" / "migraines.json").exists()
        recs = [json.loads(ln) for ln in (user / "capture" / "derived.jsonl").read_text()
                .splitlines()]
        assert recs and recs[0]["target"] == "migraines", recs


@check("17. the derived writer skips a log the turn started, added to, amended or delegated")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(cfg={"derived_entries": "on"}) as (user, _s):
        DO.create_object("Migraines", identity="occurrence")
        c = {"kind": "entry", "target": "migraines", "disposition": "save",
             "proposal": {"text": "a migraine"}, "say": "migraine", "quote": "migraine"}
        assert NL.derived(P, "r", c, [], frozenset({"migraines"})) == "derived_kept"
        assert NL.derived(P, "r", c, [("write_data_object", {"object": "migraines"})],
                          frozenset()) == "derived_kept"
        assert not _rows(user, "migraines")
        assert NL.derived(P, "r", c, [], frozenset()) == "derived_written"
        rows = _rows(user, "migraines")
        assert len(rows) == 1 and rows[0]["derived"] is True and rows[0]["source_turn"] == "r"


@check("17b. a derived entry carries when it was said; a second mention of a thing joins its "
       "one entry, adding to the note and keeping the first write's provenance")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(cfg={"derived_entries": "on"}) as (user, _s):
        DO.create_object("Films", identity="thing")
        DO.archive_write(DO.get("films"), {"title": "Champions", "notes": "on olympics.com"})
        c = {"kind": "entry", "target": "films", "disposition": "save",
             "proposal": {"title": "champions", "notes": "made by a producer I met"},
             "say": "film", "quote": "film"}
        assert NL.derived(P, "r2", c, [], frozenset()) == "derived_written"
        rows = _rows(user, "films")
        assert len(rows) == 1, rows
        assert rows[0]["notes"] == "on olympics.com; made by a producer I met", rows
        assert "derived" not in rows[0] and "said_at" not in rows[0], rows
        DO.create_object("Snacks", identity="occurrence")
        c2 = {**c, "target": "snacks", "proposal": {"text": "an apple"}}
        assert NL.derived(P, "r3", c2, [], frozenset()) == "derived_written"
        s = _rows(user, "snacks")[0]
        assert s["said_at"] and s["derived"] is True, s


@check("17c. meal times (Mike's rule + the 11-23 review): a time said wins; 'just had' is when "
       "it was said; else the usual time — never later than when it was said; the meal named is "
       "the one eaten; yesterday moves the date; a habit names an unnamed meal")
def _():
    from datetime import time as _t
    import tools.day_shape as DS
    import tools.noticed_logs as NL
    import tools.wisdom as W
    real_s, real_w = DS.shape_for, W._all_entries
    DS.shape_for = lambda day, persona=None: {"meals": [
        {"name": "breakfast", "earliest": _t(7, 30), "target": None, "source": "stated"},
        {"name": "lunch", "earliest": _t(12, 0), "target": _t(12, 45), "source": "stated"},
        {"name": "dinner", "earliest": _t(18, 0), "target": _t(18, 30), "source": "stated"}]}
    W._all_entries = lambda: [
        {"key": "standard_breakfast", "domain": "food", "value": "Standard oatmeal: 60g oats."},
        {"key": "dinner_time", "domain": "food", "value": "prefers dinner before seven"}]
    def f(at, q, when, what="x", meal=None):
        prop = {"at": at, "what": what, **({"meal": meal} if meal else {})}
        return NL._meal_at(P, prop, q, when)
    d = lambda h, m=0, day=20: datetime(2026, 11, day, h, m)
    try:
        with _sandbox() as (user, _s):
            # the usual time, and never in the future
            assert f("11:49", "This morning for breakfast, I had toast", d(11, 49)) == \
                {"at": "2026-11-20T07:30", "meal": "breakfast", "time_from": "usual"}
            assert f("", "Lunch today was schnitzel", d(15, 0))["at"] == "2026-11-20T12:45"
            assert f("", "Had soup for dinner", d(17, 10)) == \
                {"at": "2026-11-20T17:10", "meal": "dinner", "time_from": "said"}
            assert f("", "Had pizza for dinner", d(0, 30, day=21))["at"] == "2026-11-20T18:30"
            # said as happening now
            assert f("", "I just had eggs for breakfast", d(10, 40))["time_from"] == "said"
            assert f("", "I just had a cookie and a walnut", d(11, 49))["at"] == "2026-11-20T11:49"
            # the meal named is the one eaten
            assert f("", "After lunch I had a cookie", d(15, 0))["meal"] == ""
            assert f("", "had the leftover lunch curry for dinner", d(20, 0))["meal"] == "dinner"
            assert f("", "a breakfast burrito", d(20, 0), what="breakfast burrito",
                     meal="dinner")["meal"] == "dinner"
            assert f("", "brunch was eggs", d(11, 30)) == \
                {"at": "2026-11-20T11:30", "meal": "brunch", "time_from": "said"}
            # times the user said
            assert f("08:10", "breakfast at 8:10 was eggs", d(11, 0))["time_from"] == "stated"
            assert f("07:30", "breakfast at half past seven", d(11, 0))["at"] == "2026-11-20T07:30"
            assert f("07:30", "breakfast at 730", d(11, 0))["at"] == "2026-11-20T07:30"
            assert f("15:58", "6 crackers as a snack about an hour age", d(11, 49))["at"] \
                == "2026-11-20T10:49"
            assert f("", "lunch a couple of hours ago", d(15, 0))["at"] == "2026-11-20T13:00"
            assert f("", "ate an hour and a half ago", d(15, 0))["at"] == "2026-11-20T13:30"
            assert f("", "four hours ago I had soup", d(15, 0))["at"] == "2026-11-20T11:00"
            assert f("10:30", "a cup of coffee mid morning", d(15, 56))["at"] == "2026-11-20T10:30"
            assert f("", "a cup of coffee mid-morning", d(15, 56))["at"] == "2026-11-20T10:30"
            assert f("", "ate 6 crackers with brie as a snack", d(11, 49))["time_from"] == "said"
            # the date
            assert f("2026-11-19", "yesterday's breakfast was oatmeal", d(11, 0))["at"] \
                == "2026-11-19T07:30"
            assert f("yesterday", "dinner yesterday was pasta", d(11, 0))["at"] == "2026-11-19T18:30"
            # a habit names an unnamed meal; a food fact's ordinary words do not
            assert f("", "Today was the usual oatmeal", d(17, 57), what="oatmeal") == \
                {"at": "2026-11-20T07:30", "meal": "breakfast", "time_from": "usual"}
            assert f("", "I just had an oatmeal-raisin cookie", d(11, 47),
                     what="an oatmeal-raisin cookie")["at"] == "2026-11-20T11:47"
            assert f("", "chicken before the meeting", d(20, 0), what="chicken before")["meal"] == ""
    finally:
        DS.shape_for, W._all_entries = real_s, real_w


@check("17e. dinner with no time: the design's usual 18:30 when the user set none")
def _():
    from datetime import time as _t
    import tools.day_shape as DS
    import tools.noticed_logs as NL
    real = DS.shape_for
    try:
        DS.shape_for = lambda day, persona=None: {"meals": [
            {"name": "dinner", "earliest": _t(18, 0), "target": None, "source": "design"}]}
        assert NL._meal_at(P, {"what": "x"}, "For dinner I had a salad",
                           datetime(2026, 10, 26, 21, 29))["at"] == "2026-10-26T18:30"
    finally:
        DS.shape_for = real


@check("17f. a gift idea links to the one contact it names; that contact's read lists it; "
       "a reader the list is not for sees nothing; two matching contacts → no link")
def _():
    import tools.crm as CRM
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        real_load, real_caller = CRM._load_contacts, DO._caller
        try:
            CRM._load_contacts = lambda: [{"id": "c1", "name": "Manny Diamond", "first_name": "Manny"}]
            DO.archive_write(DO.get("gift_ideas"), {"title": "T-ball tee", "for": "Manny"})
            assert _rows(user, "gift_ideas")[0]["for_contact"] == "c1"
            DO._caller = lambda: "relationships"
            got = DO.entries_for_contact({"id": "c1", "name": "Manny Diamond"})
            assert [g["title"] for g in got] == ["T-ball tee"] and "for_contact" not in got[0], got
            DO._caller = lambda: "finance"
            assert DO.entries_for_contact({"id": "c1", "name": "Manny Diamond"}) == []
            CRM._load_contacts = lambda: [{"id": "c1", "name": "Manny Diamond"},
                                          {"id": "c2", "name": "Manny Ortiz"}]
            DO.archive_write(DO.get("gift_ideas"), {"title": "kite", "for": "Manny"})
            kite = [r for r in _rows(user, "gift_ideas") if r["title"] == "kite"][0]
            assert "for_contact" not in kite, kite
            DO._caller = lambda: "relationships"
            got = DO.entries_for_contact({"id": "c2", "name": "Manny Ortiz", "first_name": "Manny"})
            assert [g["title"] for g in got] == ["kite"], got
        finally:
            CRM._load_contacts, DO._caller = real_load, real_caller


@check("17h. review 11-23: an agent's note replaces (only a derived mention adds); a note "
       "already holding the old one replaces it; the same gift for two people is two entries; "
       "a re-mention for an unlinkable name drops the stale link; names link whole, never by substring")
def _():
    import tools.crm as CRM
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        DO.create_object("Films", identity="thing")
        F = lambda: DO.get("films")
        DO.archive_write(F(), {"title": "Dune", "notes": "want to watch"})
        DO.archive_write(F(), {"title": "Dune", "notes": "watched, 4/5"})
        assert _rows(user, "films")[0]["notes"] == "watched, 4/5", _rows(user, "films")
        DO.archive_write(F(), {"title": "Dune", "notes": "seen at the IMAX", "derived": True})
        DO.archive_write(F(), {"title": "Dune", "notes": "watched, 4/5; seen at the IMAX; loved it",
                               "derived": True})
        assert _rows(user, "films")[0]["notes"] == "watched, 4/5; seen at the IMAX; loved it"
        real = CRM._load_contacts
        try:
            CRM._load_contacts = lambda: [{"id": "m", "name": "Mum"}, {"id": "i", "name": "Iva Diamond"},
                                          {"id": "v", "name": "Vlad"}, {"id": "j", "name": "James"}]
            G = lambda: DO.get("gift_ideas")
            DO.archive_write(G(), {"title": "a scarf", "for": "Mum"})
            DO.archive_write(G(), {"title": "a scarf", "for": "Iva"})
            rows = _rows(user, "gift_ideas")
            assert [(r["for"], r.get("for_contact")) for r in rows] == [("Mum", "m"), ("Iva", "i")], rows
            DO.archive_write(G(), {"title": "socks", "for": "Dad"})
            DO.archive_write(G(), {"title": "a book", "for": "me"})
            assert all("for_contact" not in r for r in _rows(user, "gift_ideas")[2:]), _rows(user, "gift_ideas")
            # a stale link is dropped when the row's `for` no longer links
            rows = _rows(user, "gift_ideas")
            rows[0]["for"] = "mum"
            (user / "archive" / "gift_ideas.json").write_text(json.dumps(rows))
            CRM._load_contacts = lambda: [{"id": "m", "name": "Mum"}, {"id": "m2", "name": "Mum"}]
            DO.archive_write(G(), {"title": "a scarf", "for": "mum", "notes": "blue"})
            assert "for_contact" not in _rows(user, "gift_ideas")[0], _rows(user, "gift_ideas")[0]
        finally:
            CRM._load_contacts = real


@check("17i. a time or date given as a word ('now', 'today') is written as when it was said")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(cfg={"derived_entries": "on"}) as (user, _s):
        DO.create_object("Cardiac events", identity="occurrence",
                         fields={"date": "date", "time": "text", "description": "text"})
        c = {"kind": "entry", "target": "cardiac_events", "disposition": "save",
             "proposal": {"date": "today", "time": "now", "description": "reclined in bed"},
             "say": "x", "quote": "x"}
        assert NL.derived(P, "r9", c, [], frozenset(), said=datetime(2026, 11, 13, 19, 9)) \
            == "derived_written"
        row = _rows(user, "cardiac_events")[0]
        assert (row["date"], row["time"]) == ("2026-11-13", "19:09"), row


@check("17j. remove_entry takes an entry out of view and keeps it; numbers stay put; a removed "
       "entry cannot be changed, is never merged into, never counted, never read; restore brings it back")
def _():
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        real = DO._caller
        try:
            DO._caller = lambda: "synthesizer"
            DO.create_object("Films", identity="thing")
            for t in ("Edge of Tomorrow", "Pain", "A Real Pain"):
                DO.archive_write(DO.get("films"), {"title": t})
            out = DO.amend_data_object("films", "remove_entry", entry=2, reason="a duplicate")
            assert out.startswith("Removed entry 2 from Films"), out
            rows = _rows(user, "films")
            assert len(rows) == 3 and rows[1]["removed"]["reason"] == "a duplicate", rows
            seen = DO.read_entries(DO.get("films"))
            assert [(e["n"], e["title"]) for e in seen["entries"]] == \
                [(1, "Edge of Tomorrow"), (3, "A Real Pain")], seen
            assert DO.read_entries(DO.get("films"), count_only=True)["things"] == 2
            assert DO.amend_data_object("films", "change_entry", entry=2,
                                        changes={"notes": "x"}).startswith("Not changed")
            assert "already removed" in DO.amend_data_object("films", "remove_entry", entry=2)
            DO.archive_write(DO.get("films"), {"title": "Pain", "notes": "a new mention"})
            assert len(_rows(user, "films")) == 4 and "removed" in _rows(user, "films")[1]
            assert DO.amend_data_object("films", "restore_entry", entry=2) == "Restored entry 2 to Films."
            r2 = _rows(user, "films")[1]
            assert "removed" not in r2 and r2["previous"][-1]["value"]["removed"]["reason"] == "a duplicate"
            DO.archive_write(DO.get("gift_ideas"), {"title": "kite", "for": "Manny"})
            assert DO.amend_data_object("gift_ideas", "remove_entry", entry=1,
                                        reason="bought").startswith("Removed")
            DO._caller = lambda: "relationships"
            assert DO.entries_for_contact({"id": "c", "name": "Manny"}) == []
        finally:
            DO._caller = real


@check("17k. the writer switch: YAML's bare on (True) is on, off (False) is off — never silently off")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    for raw, want in ((True, "derived_written"), ("on", "derived_written"), (False, "derived_off"),
                      ("shadow", "derived_shadow")):
        with _sandbox(cfg={"derived_entries": raw}) as (user, _s):
            DO.create_object("Migraines", identity="occurrence")
            c = {"kind": "entry", "target": "migraines", "disposition": "save",
                 "proposal": {"text": "a migraine"}, "say": "m", "quote": "m"}
            got = NL.derived(P, "r", c, [], frozenset())
            assert got == want, (raw, got)


@check("17l. live check 11-23: a meal the Diarist writes with no time gets the usual time; the "
       "same meal re-sent minutes later is not filed twice; a different meal is")
def _():
    from datetime import time as _t
    import tools.day_shape as DS
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    real_s, real_now = DS.shape_for, NL._now
    DS.shape_for = lambda day, persona=None: {"meals": [
        {"name": "lunch", "earliest": _t(11, 45), "target": _t(12, 0), "source": "stated"}]}
    try:
        with _sandbox() as (user, _s):
            M = lambda: DO.get("meals")
            today = datetime.now().date().isoformat()
            first = {"at": today, "meal": "lunch", "what": "ramen", "notes": "Mike had a bowl of ramen"}
            assert DO.archive_write(M(), dict(first)).startswith("Added an entry")
            row = _rows(user, "meals")[0]
            if datetime.now().time() >= _t(12, 0):
                assert row["at"] == f"{today}T12:00" and row["time_from"] == "usual", row
            assert "not added twice" in DO.archive_write(M(), dict(first))
            assert DO.archive_write(M(), {"at": today, "meal": "lunch", "what": "a sandwich"}) \
                .startswith("Added an entry")
            assert len(_rows(user, "meals")) == 2, _rows(user, "meals")
            kept = DO.archive_write(M(), {"at": f"{today}T07:10", "meal": "breakfast", "what": "eggs"})
            assert _rows(user, "meals")[-1]["at"] == f"{today}T07:10", kept
    finally:
        DS.shape_for, NL._now = real_s, real_now


@check("17d. a new entry in a dev-backlog list also files a FEATURE_REQUEST; a merge does not")
def _():
    import tools.data_objects as DO
    import tools.logger as L
    with _sandbox() as (user, _s):
        got, real_q, real_l = [], L.write_quality_event, DO.limits
        L.write_quality_event = lambda t, source_agent="", detail="", session_id="": got.append((t, detail))
        DO.limits = lambda: {**real_l(), "dev_backlog_logs": ["app_backlog"]}
        try:
            DO.create_object("App backlog", identity="thing")
            DO.archive_write(DO.get("app_backlog"), {"title": "revisit the GPS tool"})
            DO.archive_write(DO.get("app_backlog"), {"title": "revisit the GPS tool", "notes": "x"})
            DO.create_object("Ideas", identity="thing")
            DO.archive_write(DO.get("ideas"), {"title": "a gift"})
        finally:
            L.write_quality_event, DO.limits = real_q, real_l
        assert got == [("FEATURE_REQUEST", "From the user's App backlog list: revisit the GPS tool")], got


@check("11. an entry candidate never reaches a CAPTURE NOTE or pending.json, on time or late")
def _():
    import tools.capture as C
    import tools.data_objects as DO
    with _sandbox(cfg={"modes": {"synthesizer": "on", "goals_interviewer": "on"}}) as (user, _s):
        DO.create_object("Migraines", identity="occurrence")
        cand = {"kind": "entry", "target": "migraines", "disposition": "save",
                "proposal": {"text": "a migraine"}, "say": "had a migraine", "quote": "m"}
        shown = C._triage(P, "synthesizer", "r1", [cand], [], False, 0)
        assert shown == [], shown

        class _Job:
            request_id, persona, agent, user_text = "r2", P, "synthesizer", "x"

            def wait(self, timeout, late=None):
                late({"ok": True, "candidates": [cand]})
                return None
        turn = C.note_for_synthesizer(P, _Job(), None)
        assert not (turn and turn.note), turn.note
        assert not C._read_json(C._pending_path(P), []), "an entry was pended"


# ---------------------------------------------------------------------------
# 6–7. Promotion
# ---------------------------------------------------------------------------

@check("6. the analytics row carries no log name, alias or field name")
def _():
    import tools.analytics as A
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        saved = A.ROOT
        A.ROOT = user.parent.parent.parent
        try:
            DO.create_object("Zanzibar sightings", aliases=["quokka log"],
                             fields={"wingspan": "text"}, identity="occurrence")
            DO.write_data_object("Zanzibar sightings", action="add_field", field="plumage")
            day = datetime.now().date().isoformat()
            (user / "traces").mkdir(exist_ok=True)
            (user / "traces" / f"{day}.jsonl").write_text(
                json.dumps({"is_proactive": False, "duration_ms": 10, "pipeline": []}) + "\n")
            row = A.rollup_day(day, P)
        finally:
            A.ROOT = saved
        assert row and row["data_objects_asked"] == 1 and row["data_object_fields_added"] == 1, row
        flat = json.dumps(row).casefold()
        for w in ("zanzibar", "quokka", "wingspan", "plumage"):
            assert w not in flat, (w, row)


@check("7. the cross-user report excludes a user without a base_configuration record")
def _():
    import importlib
    import tools.data_objects as DO
    from core import consent
    with _sandbox() as (user, _s):
        DO.create_object("Frog sightings", identity="occurrence")
        consent.grant("base_configuration", P, "v1", evidence="test")
        with persona_scope(P2):
            DO.create_object("Secret moth log", identity="occurrence")
        R = importlib.import_module("scripts.data_object_report")
        text = R.report(user.parent)
        assert "Frog sightings" in text and "Secret moth" not in text, text
        assert P2 in text and "excluded" in text, text


# ---------------------------------------------------------------------------
# 8–10, 12–16. The card
# ---------------------------------------------------------------------------

@check("8. the card is raised at the next real user turn, never at detection or on a scheduled turn")
def _():
    import core.orchestrator as O
    with _sandbox(_new()) as (_u, _s):
        _mention("place to try", "wants to try a place", n=3)
        assert not _pending()
        assert O._take_log_offer(P, user_turn=False) is None and not _pending()
        offer = O._take_log_offer(P, user_turn=True)
        assert offer and [c["action"] for c in _pending()] == ["create_data_object"]
        assert offer["question"].startswith("Want me to start a list of the places"), offer
        block = O._data_object_block(None, [], offer)
        assert "Want me to start a list" in block and "card" in block, block
        again = O._take_log_offer(P, user_turn=True)
        assert again and again.get("still_open") and len(_pending()) == 1, again
        block = O._data_object_block(None, [], again)
        assert "Still waiting" in block and "Do not ask it again" in block, block


@check("9. an invalid matcher answer raises no card")
def _():
    import tools.noticed_logs as NL
    bad = [{"verdict": "new", "name": "", "ask": "a list of x"},
           {"verdict": "new", "name": "Ok", "description": "d", "ask": "places_to_try list"},
           {"verdict": "match", "log": "no_such_log", "about": "x"}, "not json"]
    for answer in bad:
        with _sandbox(lambda p, a=answer: a) as (_u, _s):
            _mention("place to try", "wants to try a place", n=3)
            assert NL.take_offer(P) is None and not _pending(), answer
            assert any(o["status"] == "matcher_failed" for o in NL.offers(P)), answer


@check("10. 'belongs in my X list': the alias withdraws the card and raises one on X; nothing filed")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    from tools.confirm import declined
    with _sandbox(_new()) as (user, st):
        DO.create_object("Restaurants", description="Restaurants to try.", identity="thing")
        _mention("place to try", "wants to try a place", n=3)
        first = NL.take_offer(P)
        st["caller"] = "synthesizer"
        out = DO.amend_data_object("Restaurants", "add_alias", alias="places I want to try")
        st["caller"] = ""
        assert out.startswith("'places I want to try' now finds"), out
        cards = _pending()
        assert [c["action"] for c in cards] == ["alias_data_object"], cards
        assert first["token"] not in {c["token"] for c in cards}
        assert not declined(None, P), "the withdrawal was written as a decline"
        assert not _rows(user, "restaurants"), "facts filed without a tap"
        out = _tap_yes(cards[0]["token"])
        assert out["status"] == "executed", out
        assert len(_rows(user, "restaurants")) == 3
        assert DO.resolve("place to try")["id"] == "restaurants"
        NL.reconcile(P)
        assert sorted(o["status"] for o in NL.offers(P)) == ["superseded", "yes"], NL.offers(P)


@check("12. an offer turn keeps a reply that says 'I've added milk', appends the question, no event")
def _():
    import core.orchestrator as O
    with _sandbox(_new()) as (_u, _s):
        _mention("place to try", "wants to try a place", n=3)
        before = O._pending_tokens(P)
        O._take_log_offer(P, user_turn=True)
        reply = "I've added milk to your shopping list."
        events = []
        import tools.logger as L
        saved = L.write_quality_event
        L.write_quality_event = lambda **kw: events.append(kw)          # noqa: E731
        try:
            kept = O.enforce_pending_receipt(reply, O._pending_raised_since(before, P))
        finally:
            L.write_quality_event = saved
        assert kept == reply and not events, (kept, events)
        final = O._offer_receipt(kept, P, before)
        assert final.startswith(reply) and "Want me to start a list" in final, final
        pointed = ("Want me to start a list of the places you've mentioned wanting to try? "
                   "Tap Yes in the app.")
        assert O._offer_receipt(pointed, P, before) == pointed
        asked = "Want me to start a list of the places you've mentioned wanting to try?"
        assert O._offer_receipt(asked, P, before).endswith("Tap Yes or No in the app to answer.")


@check("13. an offer card sorts behind a send_email card raised after it")
def _():
    import tools.noticed_logs as NL
    from tools.confirm import request
    with _sandbox(_new()) as (_u, _s):
        _mention("place to try", "wants to try a place", n=3)
        NL.take_offer(P)
        request("send_email", {"to": "a@b.c"}, "Email A the plan", persona=P)
        assert [c["action"] for c in _pending()] == ["send_email", "create_data_object"]


@check("14. yes with a close-match log files nothing; the alias executor refuses a bad target")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(_new("Place to try list")) as (user, _s):
        _mention("place to try", "wants to try a place", n=3)
        offer = NL.take_offer(P)
        DO.create_object("Places to try", identity="thing")       # asked for in words meanwhile
        out = _tap_yes(offer["token"])
        assert out["status"] == "failed" and "already keep" in out["message"], out
        assert not _rows(user, "places_to_try"), "facts filed into a near-named log"
    with _sandbox(lambda p: {"verdict": "match", "log": "restaurants", "about": "places"}) as (
            user, _s):
        DO.create_object("Restaurants", identity="thing")
        _mention("place to try", "wants to try a place", n=3)
        offer = NL.take_offer(P)
        saved = DO._caller
        DO._caller = lambda: "synthesizer"                               # noqa: E731
        try:
            DO.amend_data_object("Restaurants", "archive")
        finally:
            DO._caller = saved
        out = _tap_yes(offer["token"])
        assert out["status"] == "failed", out
        assert not _rows(user, "restaurants")


@check("15. a same_offer verdict raises no card and attaches the category to the earlier offer")
def _():
    import tools.noticed_logs as NL
    from tools.confirm import decline
    with _sandbox(_new()) as (_u, st):
        _mention("place to try", "wants to try a place", n=3)
        first = NL.take_offer(P)
        decline(first["token"], P)
        NL.reconcile(P)
        first_id = next(o["id"] for o in NL.offers(P) if o["status"] == "no")
        NL._call_matcher = (lambda payload, persona, fid=first_id:     # restored on exit
                            json.dumps({"verdict": "same_offer", "offer": fid}))
        _mention("restaurant wishlist", "a restaurant to try", n=3)
        assert NL.take_offer(P) is None and len(_pending()) == 0
        earlier = next(o for o in NL.offers(P) if o["id"] == first_id)
        assert "restaurant wishlist" in earlier["categories"], earlier


@check("16. the decline line for an offer card does not promise never to ask again")
def _():
    from tools.confirm import decline_line
    for action in ("create_data_object", "alias_data_object"):
        line = decline_line(action)
        assert "won't ask about it again" not in line and line, line
    assert "won't ask about it again" in decline_line("send_email")


@check("the matcher is given earlier declined offers and never an entry")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    from tools.confirm import decline
    with _sandbox(_new()) as (user, st):
        DO.create_object("Migraines", identity="occurrence")
        DO.write_data_object("Migraines", entry={"text": "SECRET-ENTRY-TEXT"})
        _mention("place to try", "wants to try a place", n=3)
        decline(NL.take_offer(P)["token"], P)
        NL.reconcile(P)
        _mention("eatery", "an eatery", n=3)
        payload = st["matcher_calls"][-1]
        assert payload["earlier_offers"] and "SECRET-ENTRY-TEXT" not in json.dumps(payload)
        assert any(lg["id"] == "migraines" for lg in payload["logs"]), payload


@check("the detector is off when noticed_logs is off")
def _():
    import tools.noticed_logs as NL
    with _sandbox(_new(), cfg={"noticed_logs": "off"}) as (_u, st):
        _mention("place to try", "wants to try a place", n=3)
        assert not NL.offers(P) and not st["matcher_calls"]


# ---------------------------------------------------------------------------
# The diff review's eight findings (2026-11-22), one check each
# ---------------------------------------------------------------------------

def _same_if_shown(payload):
    """A matcher that behaves as instructed: shown an earlier offer, it says "the same"."""
    if payload.get("earlier_offers"):
        return {"verdict": "same_offer", "offer": payload["earlier_offers"][0]["offer"]}
    return _new()(payload)


@check("F1. a declined list IS offered again at double, without asking the matcher again")
def _():
    import tools.noticed_logs as NL
    from tools.confirm import decline
    with _sandbox(_same_if_shown) as (_u, st):
        _mention("place to try", "wants to try a place", n=3)
        decline(NL.take_offer(P)["token"], P)
        NL.reconcile(P)
        calls = len(st["matcher_calls"])
        _mention("place to try", "another place", n=3)
        again = NL.take_offer(P)
        assert again and again["kind"] == "create", NL.offers(P)
        assert len(st["matcher_calls"]) == calls, "the matcher was asked again"
        assert len(NL.offers(P)) == 2, NL.offers(P)


@check("F1. an expired offer comes back after three more mentions")
def _():
    import tools.noticed_logs as NL
    from tools import confirm
    with _sandbox(_same_if_shown) as (_u, _s):
        _mention("place to try", "wants to try a place", n=3)
        tok = NL.take_offer(P)["token"]
        data = confirm._load(P)
        data[tok]["expires_at"] = 0
        confirm._save(data, P)
        NL.reconcile(P)
        assert [o["status"] for o in NL.offers(P)] == ["expired"]
        _mention("place to try", "more", n=2)
        assert NL.take_offer(P) is None
        _mention("place to try", "more", n=1)
        assert NL.take_offer(P) is not None, NL.offers(P)


@check("F2. 'belongs in X' said on the NEXT turn still raises the alias card")
def _():
    import core.orchestrator as O
    import tools.data_objects as DO
    with _sandbox(_new()) as (_u, st):
        DO.create_object("Restaurants", identity="thing")
        _mention("place to try", "wants to try a place", n=3)
        O._take_log_offer(P, user_turn=True)                  # turn N: the question
        later = O._take_log_offer(P, user_turn=True)          # turn N+1: the answer
        assert later and later["still_open"], later
        st["caller"] = "synthesizer"
        DO.amend_data_object("Restaurants", "add_alias", alias="my wishlist")
        st["caller"] = ""
        assert [c["action"] for c in _pending()] == ["alias_data_object"], _pending()


@check("F3. the question is appended even when another card's receipt line was added")
def _():
    import core.orchestrator as O
    from tools.confirm import request
    with _sandbox(_new()) as (_u, _s):
        _mention("place to try", "wants to try a place", n=3)
        before = O._pending_tokens(P)
        O._take_log_offer(P, user_turn=True)
        request("send_email", {"to": "a@b.c"}, "Email A the plan", persona=P)
        reply = "I've drafted the email to A."
        receipted = O.enforce_pending_receipt(reply, O._pending_raised_since(before, P))
        assert "Waiting for your approval" in receipted, receipted
        final = O._offer_receipt(receipted, P, before, reply)
        assert "Want me to start a list" in final, final


@check("F4. a new list matching an archived log raises no card")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    with _sandbox(_new()) as (_u, st):
        DO.create_object("Places to try", identity="thing")
        st["caller"] = "synthesizer"
        DO.amend_data_object("Places to try", "archive")
        st["caller"] = ""
        _mention("place tried", "wants to try a place", n=3)
        assert NL.take_offer(P) is None and not _pending(), NL.offers(P)
        assert NL.offers(P)[0]["status"] == "home", NL.offers(P)


@check("F5. a matcher call that cannot be made is deferred and retried, never closed")
def _():
    import tools.noticed_logs as NL
    with _sandbox(_new()) as (_u, st):
        saved = NL._call_matcher
        NL._call_matcher = lambda payload, persona: None            # noqa: E731
        _mention("place to try", "wants to try a place", n=3)
        for _ in range(4):
            _mention("place to try", "again", n=1)
        assert [o["status"] for o in NL.offers(P)] == ["deferred"], NL.offers(P)
        NL._call_matcher = saved
        _mention("place to try", "once more", n=1)
        assert NL.take_offer(P) is not None and len(NL.offers(P)) == 1, NL.offers(P)


@check("F6. declining the alias card from an unrelated alias hands the topic back to the list offer")
def _():
    import tools.data_objects as DO
    import tools.noticed_logs as NL
    from tools.confirm import decline
    with _sandbox(_new()) as (_u, st):
        DO.create_object("Restaurants", identity="thing")
        _mention("place to try", "wants to try a place", n=3)
        NL.take_offer(P)
        st["caller"] = "synthesizer"
        DO.amend_data_object("Restaurants", "add_alias", alias="eateries")
        st["caller"] = ""
        decline(_pending()[0]["token"], P)
        NL.reconcile(P)
        parent = next(o for o in NL.offers(P) if o["kind"] == "create")
        assert parent["status"] == "expired", NL.offers(P)
        _mention("place to try", "more", n=3)
        again = NL.take_offer(P)
        assert again and again["kind"] == "create", NL.offers(P)


@check("F7. an entry's outcome row carries the kind, never the user's log id")
def _():
    import tools.capture as C
    import tools.data_objects as DO
    with _sandbox() as (user, _s):
        DO.create_object("Zanzibar sightings", identity="occurrence")
        cand = {"kind": "entry", "target": "zanzibar_sightings", "disposition": "save",
                "proposal": {"text": "saw one"}, "say": "saw one", "quote": "saw one"}
        C._triage(P, "synthesizer", "r1", [cand], [], False, 0)
        text = (user / "capture" / "outcomes.jsonl").read_text()
        assert "zanzibar" not in text.casefold() and '"target": "entry"' in text, text


@check("F8. an orphaned 'matching' offer is re-asked in place, not duplicated")
def _():
    import tools.noticed_logs as NL
    with _sandbox(_new()) as (_u, _s):
        saved = NL.MATCH_IN_BACKGROUND
        NL._judge, real = (lambda persona, oid: None), NL._judge      # the thread "died"
        try:
            _mention("place to try", "wants to try a place", n=3)
        finally:
            NL._judge = real
        st = NL._load(P)
        st["offers"][0]["created"] = "2000-01-01T00:00:00"
        NL._save(P, st)
        _mention("place to try", "again", n=1)
        assert len(NL.offers(P)) == 1 and NL.offers(P)[0]["status"] == "held", NL.offers(P)
        NL.MATCH_IN_BACKGROUND = saved


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, err in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {err}" if err else ""))
    print(f"\n{passed}/{len(_results)} passed")
    sys.exit(0 if passed == len(_results) else 1)
