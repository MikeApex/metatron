"""
tests/test_medication_taken.py — "Medication taken today": one record per dose.

Sweep ruling D11 (archive/plans/agent_instructions_to_code_sweep_2026-11-23.md) and the owner's
follow-up ruling of 2026-11-23: a default data object that is a READ-ONLY VIEW over the doses
already recorded as habit occurrences in the task ledger. A habit is a dose habit only when it
carries `medication` — the name of an entry in the stored medication_profile, checked when it
is set — and each row joins that profile entry. `write_log` no longer stores
`health.medications_logged`, so the ledger is the one record of a dose.

Covers the link (open_task `medication`, update_task `set_medication`), the reader
(tools/obligations.medication_taken), the object (config/data_objects/medication_taken.yaml,
tools/data_objects.READ_ONLY_STORES) and the write_log strip.

Synthetic fixtures only (generic medicines, test personas), in a tempdir. No model, push,
memory index, CalDAV or Places call is reachable: the tagger, push, quality events and
write_log's background indexing are stubbed. Same check-decorator convention as
tests/test_data_objects.py (no pytest).

Run:
    python tests/test_medication_taken.py
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from contextlib import contextmanager
from datetime import date, datetime
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


P = "med_view_test"
P2 = "med_view_other"
DAY = date(2026, 11, 20)
_GRANTS = {
    "diarist": ["write_archive", "list_data_objects", "read_data_object", "write_data_object",
                "amend_data_object"],
    "synthesizer": ["list_data_objects", "read_data_object", "amend_data_object", "list_tasks",
                    "open_task", "update_task"],
    "physical_health": ["read_log", "write_log", "write_archive", "read_data_object",
                        "read_agent_config"],
    "mental_wellbeing": ["read_data_object"],
    "finance": ["write_archive", "read_data_object", "open_task", "update_task"],
}
# Generic medicines, not anyone's.
PROFILE = {"medications": [
    {"name": "Atorvastatin", "dose": "20mg", "schedule": "daily, evening",
     "criticality": "required", "discontinuation_risk": False},
    {"name": "Salbutamol inhaler", "dose": "100mcg", "schedule": "as needed",
     "criticality": "as_needed"},
    {"name": "Vitamin D", "dose": "1000IU", "schedule": "daily", "criticality": "optional"},
]}
PROFILE_2 = {"medications": [
    {"name": "Levothyroxine", "dose": "50mcg", "schedule": "daily, morning",
     "criticality": "required", "discontinuation_risk": False}]}


def _seed_profile(persona: str, profile) -> None:
    d = persona_mod._ROOT / "data" / "personas" / persona / "config"
    d.mkdir(parents=True, exist_ok=True)
    value = profile if isinstance(profile, str) else json.dumps(profile)
    (d / "physical_health.json").write_text(json.dumps({"medication_profile": value}))


@contextmanager
def _sandbox(caller: str = "physical_health", persona: str = P, profile=PROFILE):
    """Two persona trees in a tempdir with a medication profile each; the ledger clock, the
    grants, the caller, the tagger, push, quality events and write_log's indexing stubbed.
    Yields (data_dir, state)."""
    import tools.data_objects as DO
    import tools.logger as LOG
    import tools.obligations as O

    state = {"caller": caller, "clock": datetime(2026, 11, 20, 9)}
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        saved = [(persona_mod, "_ROOT", persona_mod._ROOT), (O, "_now", O._now),
                 (LOG, "run_background", LOG.run_background),
                 (DO, "_call_tagger", DO._call_tagger), (DO, "_send_push", DO._send_push),
                 (DO, "_quality_event", DO._quality_event),
                 (DO, "_allowed_tools", DO._allowed_tools), (DO, "_caller", DO._caller),
                 (DO, "TAG_IN_BACKGROUND", DO.TAG_IN_BACKGROUND)]
        persona_mod._ROOT = tmp
        for p in (P, P2):
            (tmp / "config" / "personas" / p).mkdir(parents=True, exist_ok=True)
            (tmp / "data" / "personas" / p).mkdir(parents=True, exist_ok=True)
        if profile is not None:
            _seed_profile(P, profile)
        _seed_profile(P2, PROFILE_2)
        O._now = lambda: state["clock"]                                     # noqa: E731
        LOG.run_background = lambda *a, **k: None                           # noqa: E731
        DO._call_tagger = lambda payload, persona: "[]"                      # noqa: E731
        DO._send_push = lambda *a, **k: None                                 # noqa: E731
        DO._quality_event = lambda **k: None                                 # noqa: E731
        DO._allowed_tools = lambda agent: _GRANTS.get(agent)                 # noqa: E731
        DO._caller = lambda: state["caller"]                                 # noqa: E731
        DO.TAG_IN_BACKGROUND = False
        try:
            with persona_scope(persona):
                yield tmp / "data" / "personas" / persona, state
        finally:
            for obj, name, value in saved:
                setattr(obj, name, value)


def _habit(what: str, times: int = 1, medication: str | None = None) -> str:
    import tools.obligations as O
    out = O.open_task(what, kind="habit", every="day", times=times, new_instance=True,
                      medication=medication)
    assert out.startswith("task "), out
    return out.split()[1]


def _old_habit(state: dict, what: str, times: int = 1, medication: str | None = None,
               days: int = 1) -> str:
    """A habit opened `days` before the sandbox clock — one the user has had all along, so the
    creation-day rule (no dose owed that fell due before the habit existed) does not apply."""
    from datetime import timedelta
    now = state["clock"]
    state["clock"] = now - timedelta(days=days)
    try:
        return _habit(what, times=times, medication=medication)
    finally:
        state["clock"] = now


def _dose(tid: str, at: datetime, state: dict) -> None:
    import tools.obligations as O
    state["clock"] = at
    out = O.update_task(tid, "done", evidence="took it")
    assert "recorded" in out, out


def _task(tid: str) -> dict:
    import tools.obligations as O
    return next(t for t in O._load() if t["id"] == tid)


def _row(view: dict, tid: str) -> dict:
    return next(r for r in view["medications"] if r["task_id"] == tid)


def _linked(view: dict) -> list[dict]:
    return [r for r in view["medications"] if r["linked"]]


# ---------------------------------------------------------------------------
# The link: by data, checked against the profile
# ---------------------------------------------------------------------------

@check("linking refused for a name the profile does not hold — open_task and set_medication "
       "— and nothing is written")
def _():
    import tools.obligations as O
    with _sandbox("synthesizer") as (data, _s):
        out = O.open_task("Take a beta blocker", kind="habit", every="day",
                          medication="Bisoprolol")
        assert out.startswith("error:") and "not a medication in the user's stored profile" \
            in out and "Nothing was written" in out, out
        assert "Atorvastatin" in out, "a health-view reader is told the names it can use"
        assert not (data / "tasks.yaml").exists() or not O._load()
        tid = _habit("Evening tablet")
        out = O.update_task(tid, "set_medication", medication="Bisoprolol")
        assert out.startswith("error:"), out
        assert "medication" not in _task(tid)


@check("a refusal never hands the profile's names to an agent outside the health view")
def _():
    import tools.obligations as O
    with _sandbox("finance") as (_d, _s):
        out = O.open_task("Take a beta blocker", kind="habit", every="day",
                          medication="Bisoprolol")
        assert out.startswith("error:") and "Atorvastatin" not in out and "Vitamin" not in out, out


@check("linking refused with no profile, an unreadable profile, or a task that is not a habit")
def _():
    import tools.obligations as O
    with _sandbox(profile=None) as (_d, _s):
        out = O.open_task("A statin", kind="habit", every="day", medication="Atorvastatin")
        assert out.startswith("error:") and "names no medications yet" in out, out
    with _sandbox(profile="{not json") as (_d, _s):
        out = O.open_task("A statin", kind="habit", every="day", medication="Atorvastatin")
        assert out.startswith("error:") and "could not be read" in out, out
    with _sandbox() as (_d, _s):
        out = O.open_task("Renew the prescription", kind="deadline", medication="Atorvastatin")
        assert out.startswith("error:") and "links a habit" in out, out


@check("linking accepted (case and spacing ignored, the profile's spelling kept), the habit "
       "is essential by data, and its row joins the profile entry")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _habit("Evening tablet", medication="  atorvastatin ")
        t = _task(tid)
        assert t["medication"] == "Atorvastatin", t
        assert O.is_essential(t), "a linked habit is essential whatever its name"
        _dose(tid, datetime(2026, 11, 20, 20, 5), state)
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["medication"], r["linked"], r["in_profile"]) == ("Atorvastatin", True, True), r
        assert (r["criticality"], r["discontinuation_risk"], r["dose"], r["schedule"]) == \
            ("required", False, "20mg", "daily, evening"), r


@check("set_medication links an existing habit, takes the caller's done words only when the "
       "habit has none, records the change, and an empty name unlinks")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        a = _habit("Morning capsule")
        out = O.update_task(a, "set_medication", medication="Vitamin D",
                            done_words=["vitamin", "capsule"], evidence="that one is my vitamin D")
        assert "linked to 'Vitamin D'" in out, out
        t = _task(a)
        assert t["medication"] == "Vitamin D" and t["done_words"] == ["vitamin", "capsule"], t
        assert t["history"][-1]["event"] == "medication_linked", t["history"]
        b = O.open_task("Evening pill", kind="habit", every="day", new_instance=True,
                        done_words=["pill"]).split()[1]
        out = O.update_task(b, "set_medication", medication="Atorvastatin", done_words=["statin"])
        assert "keeps the done words it already had" in out and _task(b)["done_words"] == ["pill"]
        assert "done_words" not in _task(_habit("Other", medication="Salbutamol inhaler"))
        out = O.update_task(a, "set_medication", medication="")
        assert "unlinked" in out and "medication" not in _task(a), out
        assert O.update_task(a, "set_medication").startswith("error:")


@check("set_medication is refused on a one-off, and offered whatever the planner flag says")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        tid = O.open_task("Collect the prescription", kind="deadline").split()[1]
        assert O.update_task(tid, "set_medication",
                             medication="Atorvastatin").startswith("error: only a habit")
        assert "set_medication" in O.UPDATE_TASK_SCHEMA["input_schema"]["properties"][
            "action"]["enum"]
        assert "medication" in O.OPEN_TASK_SCHEMA["input_schema"]["properties"]
        for s in O.task_schemas()[:2]:
            assert "medication" in json.dumps(s)


@check("a profile entry no habit links appears as linked: false — no dose record, not missed")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        tid = _habit("Evening tablet", medication="Atorvastatin")
        view = O.medication_taken(day=DAY)
        unlinked = {r["medication"]: r for r in view["medications"] if not r["linked"]}
        assert set(unlinked) == {"Salbutamol inhaler", "Vitamin D"}, view
        v = unlinked["Vitamin D"]
        assert (v["task_id"], v["expected"], v["done"], v["doses"]) == (None, None, None, []), v
        assert v["criticality"] == "optional" and v["dose"] == "1000IU", v
        assert _row(view, tid)["linked"] is True


@check("a habit whose medication the profile no longer holds stays listed, in_profile: false")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        tid = _habit("Evening tablet", medication="Atorvastatin")
        _seed_profile(P, {"medications": [m for m in PROFILE["medications"]
                                          if m["name"] != "Atorvastatin"]})
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["linked"], r["in_profile"], r["criticality"]) == (True, False, None), r


@check("a habit named like a medicine but not linked is never in the view — no name guessing")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _habit("Take my pills")
        _dose(tid, datetime(2026, 11, 20, 8), state)
        assert not _linked(O.medication_taken(day=DAY)), "an unlinked habit is not a dose"


# ---------------------------------------------------------------------------
# The reader
# ---------------------------------------------------------------------------

@check("doses expected vs done for one day, with each dose's record (day and when recorded)")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _habit("Statin", times=2, medication="Atorvastatin")
        _dose(tid, datetime(2026, 11, 20, 8, 5), state)
        view = O.medication_taken(day=DAY)
        assert view["ok"] and view["day"] == "2026-11-20", view
        r = _row(view, tid)
        assert (r["expected"], r["done"], r["skipped"]) == (2, 1, False), r
        assert r["period"] == "2026-11-20" and r["what"] == "Statin", r
        assert r["doses"] == [{"on": "2026-11-20", "recorded_at": "2026-11-20T08:05:00"}], r
        assert r["dose_times"] == "recorded", r


@check("two medications are reported separately, each with its own count")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        a = _habit("Statin", medication="Atorvastatin")
        b = _habit("Vitamin", times=2, medication="Vitamin D")
        _dose(a, datetime(2026, 11, 20, 8), state)
        _dose(b, datetime(2026, 11, 20, 8, 30), state)
        _dose(b, datetime(2026, 11, 20, 20), state)
        view = O.medication_taken(day=DAY)
        assert len(_linked(view)) == 2, view
        assert (_row(view, a)["expected"], _row(view, a)["done"]) == (1, 1)
        assert (_row(view, b)["expected"], _row(view, b)["done"]) == (2, 2)
        assert len(_row(view, b)["doses"]) == 2


@check("a day with none done: the medication is listed with 0 done, not left out")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        tid = _habit("Statin", medication="Atorvastatin")
        view = O.medication_taken(day=DAY)
        assert view["ok"], view
        r = _row(view, tid)
        assert (r["expected"], r["done"], r["doses"]) == (1, 0, []), r


@check("a habit that is not a medication is never in the view")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        med = _habit("Statin", medication="Atorvastatin")
        other = _habit("Stretching")
        _dose(other, datetime(2026, 11, 20, 7), state)
        ids = [r["task_id"] for r in _linked(O.medication_taken(day=DAY))]
        assert ids == [med], ids


@check("persona isolation: another user's doses and profile never appear, in either direction")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        mine = _habit("Statin", medication="Atorvastatin")
        _dose(mine, datetime(2026, 11, 20, 8), state)
        with persona_scope(P2):
            assert O.open_task("Thyroid", kind="habit", every="day",
                               medication="Atorvastatin").startswith("error:"), \
                "linking checks the persona's OWN profile"
            theirs = _habit("Thyroid tablet", medication="Levothyroxine")
            _dose(theirs, datetime(2026, 11, 20, 9), state)
        a = O.medication_taken(day=DAY)
        b = O.medication_taken(persona=P2, day=DAY)
        assert [r["task_id"] for r in _linked(a)] == [mine], a
        assert [r["task_id"] for r in _linked(b)] == [theirs], b
        assert "Levothyroxine" not in json.dumps(a) and "Atorvastatin" not in json.dumps(b)


@check("no persona bound: refused (fail-closed), never another user's record")
def _():
    import tools.obligations as O
    saved = getattr(persona_mod._state, "persona", None)
    persona_mod._state.persona = None
    env = os.environ.pop("METATRON_PERSONA", None)
    try:
        view = O.medication_taken(day=DAY)
    finally:
        if env is not None:
            os.environ["METATRON_PERSONA"] = env
        persona_mod._state.persona = saved
    assert view["ok"] is False and view["medications"] == [], view


@check("default day is today on the persona's clock; a past, swept day keeps its count only")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _habit("Statin", times=2, medication="Atorvastatin")
        _dose(tid, datetime(2026, 11, 20, 8), state)
        _dose(tid, datetime(2026, 11, 20, 20), state)
        assert O.medication_taken()["day"] == "2026-11-20"
        state["clock"] = datetime(2026, 11, 21, 0, 15)
        O.sweep()
        past = _row(O.medication_taken(day=DAY), tid)
        assert (past["done"], past["expected"], past["dose_times"]) == (2, 2, "not_kept"), past
        today = O.medication_taken()
        assert today["day"] == "2026-11-21" and _row(today, tid)["done"] == 0, today


@check("a habit started after the day is not listed for that day (its medication reads unlinked)")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        state["clock"] = datetime(2026, 11, 22, 9)
        _habit("Statin", medication="Atorvastatin")
        assert not _linked(O.medication_taken(day=DAY))
        assert _linked(O.medication_taken(day=date(2026, 11, 22)))


@check("missing ledger: ok, every profile entry unlinked; corrupt ledger or profile: not ok, "
       "never raises, and nothing is written — the damaged file is left exactly as it was")
def _():
    import tools.obligations as O
    with _sandbox() as (data, _s):
        view = O.medication_taken(day=DAY)
        assert view["ok"] is True and not _linked(view) and len(view["medications"]) == 3, view
        assert not (data / "tasks.yaml").exists() and not (data / "tasks.yaml.lock").exists()
        (data / "tasks.yaml").write_text("tasks: [this is: not: yaml")
        before = (data / "tasks.yaml").read_text()
        view = O.medication_taken(day=DAY)
        assert view["ok"] is False and "could not be read" in view["reason"], view
        assert (data / "tasks.yaml").read_text() == before
        (data / "tasks.yaml").write_text("just a string")
        assert O.medication_taken(day=DAY)["ok"] is False
    with _sandbox(profile="{not json") as (_d, _s):
        view = O.medication_taken(day=DAY)
        assert view["ok"] is False and "profile" in view["reason"], view


@check("the reader never raises, whatever fails underneath")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        saved = O._load_doc
        O._load_doc = lambda persona=None: (_ for _ in ()).throw(RuntimeError("boom"))
        try:
            view = O.medication_taken(day=DAY)
        finally:
            O._load_doc = saved
        assert view["ok"] is False and view["medications"] == [], view


# ---------------------------------------------------------------------------
# One record per dose, per medicine: write_log drops only a LINKED medicine's entries (fix 1)
# ---------------------------------------------------------------------------

@check("fix 1: write_log drops medications_logged entries only for medicines with a linked "
       "habit, keeps the unlinked ones (a misplaced top-level list moves under health), keeps "
       "every other field, names what it dropped, and merges with the day's earlier entries by "
       "name")
def _():
    import tools.logger as LOG
    with _sandbox() as (data, state):
        state["clock"] = datetime.now().replace(microsecond=0)  # the log file uses the real date
        _habit("Evening tablet", medication="Atorvastatin")
        day = date.today().isoformat()
        (data / "logs").mkdir(parents=True, exist_ok=True)
        old = {"date": day, "health": {"energy": "low", "medications_logged": [
            {"name": "Vitamin D", "taken": False}, {"name": "Salbutamol inhaler", "taken": True}]}}
        (data / "logs" / f"{day}.json").write_text(json.dumps(old))
        out = LOG.write_log({"health": {"sleep_hours": 7, "energy": "high",
                                        "symptoms": "a headache", "exercise": {"type": "walk"},
                                        "medications_logged": [
                                            {"name": "atorvastatin ", "taken": True},
                                            {"name": "Vitamin D", "taken": True}]},
                             "medications_logged": [{"name": "Iron tablet", "taken": True}],
                             "notes": "fine"})
        assert "entry for atorvastatin was not stored" in out and "Medication taken today" in out \
            and "Vitamin D" not in out, out
        got = json.loads((data / "logs" / f"{day}.json").read_text())
        h = got["health"]
        assert (h["sleep_hours"], h["energy"], h["symptoms"], h["exercise"]) == \
            (7, "high", "a headache", {"type": "walk"}), h
        assert [(e["name"], e["taken"]) for e in h["medications_logged"]] == [
            ("Salbutamol inhaler", True), ("Vitamin D", True), ("Iron tablet", True)], \
            h["medications_logged"]
        assert "logged_at" not in h["medications_logged"][0], "an earlier entry is left as it was"
        assert all(e["logged_at"] == state["clock"].isoformat()
                   for e in h["medications_logged"][1:]), "kept entries stamped on the persona clock"
        assert "medications_logged" not in got and got["notes"] == "fine", got
        out = LOG.write_log({"health": {"energy": "moderate"}})
        assert "medications_logged" not in out, out
        assert len(json.loads((data / "logs" / f"{day}.json").read_text())["health"][
            "medications_logged"]) == 3, "a write without the list leaves the day's entries"


@check("fix 1: a write carrying only a linked medicine's entry stores nothing for it and the "
       "capture check does not count it; an unlinked medicine's entry is stored and counted; "
       "with the ledger unreadable nothing is dropped")
def _():
    import tools.capture as C
    import tools.logger as LOG
    with _sandbox() as (data, _s):
        _habit("Evening tablet", medication="Atorvastatin")
        out = LOG.write_log({"health": {"medications_logged": [{"name": "Atorvastatin"}]}})
        assert "not stored" in out, out
        got = json.loads(next((data / "logs").glob("*.json")).read_text())
        assert "health" not in got, got
        args = {"content": {"health": {"medications_logged": [{"name": "Atorvastatin"}],
                                       "symptoms": "dizzy"}}}
        text = C._home_text("health", "write_log", args)
        assert "atorvastatin" not in text.lower() and "dizzy" in text, text
        args = {"content": {"health": {"medications_logged": [{"name": "Vitamin D"}]}}}
        assert "vitamin" in C._home_text("health", "write_log", args).lower()
        out = LOG.write_log({"health": {"medications_logged": [{"name": "Vitamin D"}]}})
        assert "not stored" not in out, out
        (data / "tasks.yaml").write_text("tasks: [this is: not: yaml")
        out = LOG.write_log({"health": {"medications_logged": [{"name": "Atorvastatin"}]}})
        assert "not stored" not in out, "an unreadable ledger drops nothing"
        h = json.loads(next((data / "logs").glob("*.json")).read_text())["health"]
        assert {e["name"] for e in h["medications_logged"]} == {"Vitamin D", "Atorvastatin"}, h


# ---------------------------------------------------------------------------
# The data object
# ---------------------------------------------------------------------------

@check("the default object exists for every user: health class, read-only, listed as a log")
def _():
    import tools.data_objects as DO
    with _sandbox() as (_d, _s):
        o = DO.resolve("Medication taken today")
        assert o and o["id"] == "medication_taken" and o["class"] == "health", o
        assert DO.read_only(o) and o["store"] in DO.STORES
        assert {"physical_health", "mental_wellbeing"} <= DO.readers(o)
        names = [r["name"] for r in DO.list_data_objects()]
        assert "Medication taken today" in names, names
        assert "Medication taken today" in DO.manifest_for("physical_health")
        assert "Medication taken today" not in DO.manifest_for("finance")


@check("read_data_object returns today's view to a health agent and refuses a non-health one")
def _():
    import tools.data_objects as DO
    with _sandbox("physical_health") as (_d, state):
        tid = _habit("Statin", medication="Atorvastatin")
        _dose(tid, datetime(2026, 11, 20, 8), state)
        got = DO.read_data_object("Medication taken today")
        assert got["store"] == "medication" and got["result"]["ok"], got
        assert got["result"]["day"] == "2026-11-20"
        assert _row(got["result"], tid)["done"] == 1, got
        state["caller"] = "mental_wellbeing"
        assert DO.read_data_object("medication_taken").get("result"), "mental_wellbeing"
        state["caller"] = "finance"
        refused = DO.read_data_object("Medication taken today")
        assert "error" in refused and "result" not in refused, refused
        state["caller"] = ""
        assert "error" in DO.read_data_object("Medication taken today")


@check("a dated read (since=) returns that day's view")
def _():
    import tools.data_objects as DO
    with _sandbox("physical_health") as (_d, _s):
        _habit("Statin", medication="Atorvastatin")
        got = DO.read_data_object("Medication taken today", since="2026-11-19")
        assert got["result"]["day"] == "2026-11-19", got


@check("every write and amend door refuses it, plainly, and nothing lands on disk")
def _():
    import tools.data_objects as DO
    import tools.diarist as DI
    with _sandbox("diarist") as (data, s):
        DO.mark_pending("medication_taken")
        for out in (DO.write_data_object("Medication taken today", {"text": "took a statin"}),
                    DO.write_data_object("medication_taken", {"text": "x"},
                                         action="add_occurrence", occurrence={"at": "08:00"}),
                    DO.write_data_object("medication_taken", action="add_field", field="dose"),
                    DI.write_archive("medication_taken", {"text": "took a statin"}),
                    DI.write_archive("medications", {"text": "took a statin"}),
                    DO.archive_write(DO.get("medication_taken"), {"text": "x"})):
            assert out.startswith("Not recorded") and "read-only" in out, out
        s["caller"] = "synthesizer"
        for action, kw in (("change_entry", {"entry": 1, "changes": {"text": "y"}}),
                           ("remove_entry", {"entry": 1}), ("rename", {"new_name": "Pills"}),
                           ("add_alias", {"alias": "pills"}), ("archive", {}),
                           ("private", {}), ("merge", {"into": "health_events"})):
            out = DO.amend_data_object("Medication taken today", action, **kw)
            assert out.startswith("Not changed") and "read-only" in out, (action, out)
        assert DO.add_alias("medication_taken", "pills") is False
        assert DO.resolve("pills") is None
        assert not (data / "archive" / "medication_taken.json").exists()
        assert not (data / "archive" / "medications.json").exists()
        assert all(o["id"] != "medication_taken" for o in DO._stored()), DO._stored()


@check("a second 'medication log' cannot be started beside it")
def _():
    import tools.data_objects as DO
    with _sandbox() as (_d, _s):
        out = DO.create_object("medication log")
        assert not out.get("created") and out["match"]["id"] == "medication_taken", out


@check("the derived writer never targets it, and the extractor is never offered it")
def _():
    import tools.capture as C
    import tools.noticed_logs as NL
    saved = C.config
    C.config = lambda: {**C._DEFAULTS, "enabled": True, "derived_entries": "on"}  # noqa: E731
    try:
        with _sandbox() as (data, _s):
            c = {"kind": "entry", "target": "medication_taken", "disposition": "save",
                 "proposal": {"text": "took a statin"}, "say": "took a statin",
                 "quote": "took my statin"}
            assert NL.derived(P, "r", c, [], frozenset()) == "derived_invalid"
            assert not (data / "archive" / "medication_taken.json").exists()
            assert "medication_taken" not in C.user_logs_text(P)
    finally:
        C.config = saved


@check("the Coordinator's 'add' or 'amend' marks nothing pending and tells the Synthesizer "
       "plainly; a 'read' goes to a health agent")
def _():
    import core.orchestrator as OR
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (_d, _s):
        coord = ('SPECIALISTS_TO_CALL: []\n\nDATA_OBJECTS: [{"name": "medication taken today", '
                 '"act": "add"}, {"name": "medication taken today", "act": "amend"}]')
        turn = OR._resolve_data_objects(coord, persona=P, user_turn=True)
        assert not turn["adding"] and not DO.pending_tokens("medication_taken"), turn
        assert [o["id"] for o in turn["read_only"]] == ["medication_taken"], turn
        block = OR._data_object_block(turn, [])
        assert "nothing was added to it" in block, block
        coord = ('SPECIALISTS_TO_CALL: []\n\nDATA_OBJECTS: [{"name": "medication taken today", '
                 '"act": "read"}]')
        turn = OR._resolve_data_objects(coord, persona=P, user_turn=True)
        assert turn["delegated"] and turn["delegated"][0]["agent"] == "physical_health", turn


# ---------------------------------------------------------------------------
# Review round, 2026-11-23: fixes 1–10
# ---------------------------------------------------------------------------

def _edit_task(tid: str, **fields) -> None:
    """Set stored fields on a task directly (fields the planner flag gates, like `after`)."""
    import tools.obligations as O

    def apply(doc):
        t = O._find(doc["tasks"], tid)
        for k, v in fields.items():
            if v is None:
                t.pop(k, None)
            else:
                t[k] = v
    O._with_store(None, apply)


def _write_day_log(data: Path, day: date, entries) -> None:
    (data / "logs").mkdir(parents=True, exist_ok=True)
    body = {"date": day.isoformat(), "health": {"energy": "low"}}
    if entries is not None:
        body["health"]["medications_logged"] = entries
    (data / "logs" / f"{day.isoformat()}.json").write_text(json.dumps(body))


def _by_name(view: dict, name: str) -> dict:
    return next(r for r in view["medications"] if r["medication"] == name)


@check("fix 1: an unlinked row carries the day's log evidence — required and nothing logged is "
       "missed and needs_link; logged (taken) is not missed; taken: false is missed; as_needed "
       "is never missed; an unreadable log is UNKNOWN (None), never 'not missed'")
def _():
    import tools.obligations as O
    with _sandbox() as (data, _s):
        r = _by_name(O.medication_taken(day=DAY), "Atorvastatin")
        assert (r["linked"], r["logged"], r["logged_entries"], r["missed"], r["needs_link"],
                r["link_broken"], r["due_now"]) == (False, False, [], True, True, False, None), r
        v = _by_name(O.medication_taken(day=DAY), "Vitamin D")
        assert (v["needs_link"], v["missed"]) == (False, True), "optional: informational only"
        s = _by_name(O.medication_taken(day=DAY), "Salbutamol inhaler")
        assert (s["needs_link"], s["missed"]) == (False, False), "as_needed is never due"
        _write_day_log(data, DAY, [{"name": "atorvastatin", "taken": True, "notes": None}])
        r = _by_name(O.medication_taken(day=DAY), "Atorvastatin")
        assert (r["logged"], r["missed"], len(r["logged_entries"])) == (True, False, 1), r
        assert r["needs_link"] is True, "still untracked by a habit, so still offered a link"
        _write_day_log(data, DAY, [{"name": "Atorvastatin", "taken": False}])
        assert _by_name(O.medication_taken(day=DAY), "Atorvastatin")["missed"] is True
        (data / "logs" / f"{DAY.isoformat()}.json").write_text("{not json")
        view = O.medication_taken(day=DAY)
        r = _by_name(view, "Atorvastatin")
        assert view["ok"] and (r["logged"], r["missed"]) == (None, None), r
        assert _by_name(view, "Salbutamol inhaler")["missed"] is False


@check("item 2: a renamed medicine joins its broken habit — one row, the new profile fields, the "
       "habit's doses, link_broken and relink_to, and the rename alone is never a miss; two "
       "candidate names join nothing")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _old_habit(state, "Evening tablet", medication="Atorvastatin")
        _dose(tid, datetime(2026, 11, 20, 8), state)
        renamed = [dict(m, name="Atorvastatin 40mg", dose="40mg") if m["name"] == "Atorvastatin"
                   else m for m in PROFILE["medications"]]
        _seed_profile(P, {"medications": renamed})
        view = O.medication_taken(day=DAY)
        r = _row(view, tid)
        assert (r["medication"], r["linked_name"], r["relink_to"], r["link_broken"],
                r["in_profile"], r["dose"], r["criticality"], r["done"], r["missed"]) == \
            ("Atorvastatin 40mg", "Atorvastatin", "Atorvastatin 40mg", True, False, "40mg",
             "required", 1, False), r
        assert [x["medication"] for x in view["medications"]].count("Atorvastatin 40mg") == 1
        _seed_profile(P, {"medications": renamed + [
            {"name": "Atorvastatin 80mg", "criticality": "required"}]})
        view = O.medication_taken(day=DAY)
        r = _row(view, tid)
        assert (r["medication"], r["link_broken"], "relink_to" in r) == \
            ("Atorvastatin", True, False), "ambiguous: reported broken, not joined"
        assert _by_name(view, "Atorvastatin 40mg")["needs_link"] is True


@check("item 2: writing the profile relinks a habit whose name vanished to its one new spelling, "
       "in the habit's history; an ambiguous rename relinks nothing")
def _():
    import tools.agent_config as AC
    import tools.confirm as CF
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        tid = _habit("Evening tablet", medication="Atorvastatin")
        renamed = [dict(m, name="Atorvastatin 40mg") if m["name"] == "Atorvastatin" else m
                   for m in PROFILE["medications"]]
        saved = CF.consume
        CF.consume = lambda token, tool, args: (True, "")                   # noqa: E731
        try:
            out = AC.write_agent_config("physical_health", "medication_profile",
                                        json.dumps({"medications": renamed}), confirm_token="t")
        finally:
            CF.consume = saved
        assert "now follows its new name 'Atorvastatin 40mg'" in out, out
        t = _task(tid)
        assert t["medication"] == "Atorvastatin 40mg", t
        assert t["history"][-1]["event"] == "medication_relinked" and \
            t["history"][-1]["from"] == "Atorvastatin", t["history"]
        two = _habit("Inhaler", medication="Salbutamol inhaler")
        _seed_profile(P, {"medications": [m for m in renamed if m["name"] != "Salbutamol inhaler"]
                          + [{"name": "Salbutamol inhaler 100"}, {"name": "Salbutamol inhaler 200"}]})
        assert O.relink_after_profile_write() == []
        assert _task(two)["medication"] == "Salbutamol inhaler"


@check("fix 2: a reported dose is recorded through the close gate when the user names the "
       "medicine or the habit's done words, not its title; the link shows in the Tasks block and, "
       "for a caller who may set it, in list_tasks")
def _():
    import tools.obligations as O
    from tools import turn_context as T
    with _sandbox("synthesizer") as (_d, state):
        tid = _habit("Evening tablet", medication="Atorvastatin")
        other = O.open_task("Morning capsule", kind="habit", every="day", new_instance=True,
                            done_words=["omega"]).split()[1]
        with T.turn_scope(user_turn=True) as turn:          # the gate is live: a control
            turn.update(close_gate=True, user_text="I sorted the paperwork", prev_assistant="")
            assert O.update_task(tid, "done", evidence="sorted").startswith("error: not recorded")
        for text, target in (("I took my atorvastatin", tid), ("had my omega", other)):
            with T.turn_scope(user_turn=True) as turn:
                turn.update(close_gate=True, user_text=text, prev_assistant="")
                out = O.update_task(target, "done", evidence=text)
            assert "recorded" in out, (text, out)
        state["clock"] = datetime(2026, 11, 21, 9)
        hint = O.completion_hints("took the atorvastatin with breakfast")
        assert tid in hint, hint
        assert "[medication: Atorvastatin]" in O.context_block(P, audience="synthesizer")
        for who in ("coordinator", None, "finance"):
            assert "[medication:" not in O.context_block(P, audience=who), who
        assert "[medication: Atorvastatin]" in O.list_tasks()
        state["caller"] = "finance"
        assert "[medication:" not in O.list_tasks(), "no profile name to a non-setter"


@check("fix 3: due_now and missed follow the ledger — a Friday weekly habit is due 0 on a "
       "Tuesday and 1 on Friday; a quota is due only when it can no longer fit; once-daily is "
       "due from the day's start, or from its `after` time")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        state["clock"] = datetime(2026, 11, 16, 8)                       # a Monday
        fri = O.open_task("Weekly injection", kind="habit", every="week", times=1,
                          on_days=["fri"], new_instance=True, medication="Atorvastatin")
        fri = fri.split()[1]
        state["clock"] = datetime(2026, 11, 17, 9)                       # Tuesday
        r = _row(O.medication_taken(), fri)
        assert (r["due_now"], r["done"], r["missed"]) == (0, 0, False), r
        state["clock"] = datetime(2026, 11, 20, 9)                       # Friday
        r = _row(O.medication_taken(), fri)
        assert (r["due_now"], r["missed"]) == (1, True), r
        _dose(fri, datetime(2026, 11, 20, 9, 30), state)
        assert _row(O.medication_taken(), fri)["missed"] is False
    with _sandbox() as (_d, state):
        state["clock"] = datetime(2026, 11, 16, 8)
        q = O.open_task("Weekly tablet", kind="habit", every="week", times=1,
                        new_instance=True, medication="Atorvastatin").split()[1]
        state["clock"] = datetime(2026, 11, 20, 9)
        assert _row(O.medication_taken(), q)["due_now"] == 0, "can still fit by Sunday"
        state["clock"] = datetime(2026, 11, 22, 9)
        r = _row(O.medication_taken(), q)
        assert (r["due_now"], r["missed"]) == (1, True), r
    with _sandbox() as (_d, state):
        tid = _old_habit(state, "Statin", medication="Atorvastatin")
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["due_now"], r["missed"]) == (1, True), "once-daily: due from the day's start"
        _edit_task(tid, after="20:00")
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["due_now"], r["missed"]) == (0, False), "an evening dose is not due at 09:00"
        state["clock"] = datetime(2026, 11, 20, 20, 30)
        assert _row(O.medication_taken(day=DAY), tid)["missed"] is True


@check("fix 3: a twice-daily habit owes its first dose by midday and the rest only by the day's "
       "end; a day that is over owes them all")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _old_habit(state, "Statin", times=2, medication="Atorvastatin")
        state["clock"] = datetime(2026, 11, 20, 9)
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["expected"], r["due_now"], r["missed"]) == (2, 0, False), r
        state["clock"] = datetime(2026, 11, 20, 12, 30)
        assert _row(O.medication_taken(day=DAY), tid)["missed"] is True
        _dose(tid, datetime(2026, 11, 20, 12, 40), state)
        state["clock"] = datetime(2026, 11, 20, 22)
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["due_now"], r["done"], r["missed"]) == (1, 1, False), r
        state["clock"] = datetime(2026, 11, 21, 9)
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["due_now"], r["done"], r["missed"]) == (2, 1, True), r


@check("fix 4: a skipped occurrence and a paused habit are never missed")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        a = _old_habit(state, "Statin", medication="Atorvastatin")
        out = O.update_task(a, "skipped", evidence="doctor said to skip today")
        assert "skipped" in out, out
        r = _row(O.medication_taken(day=DAY), a)
        assert (r["skipped"], r["due_now"], r["missed"]) == (True, 1, False), r
        b = _habit("Vitamin", medication="Vitamin D")
        _edit_task(b, eligible_from="2026-11-25")
        r = _row(O.medication_taken(day=DAY), b)
        assert (r["paused"], r["paused_until"], r["due_now"], r["missed"]) == \
            (True, "2026-11-25", 0, False), r


@check("fix 5: a linked dose beyond the period's count is refused, and the same dose marked "
       "again within 10 minutes is refused as a repeat; other habits count as before")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        one = _habit("Statin", medication="Atorvastatin")
        _dose(one, datetime(2026, 11, 20, 8), state)
        state["clock"] = datetime(2026, 11, 20, 9)
        out = O.update_task(one, "done", evidence="took it")
        assert out.startswith("error:") and "already recorded 1 of 1 today" in out, out
        two = _habit("Vitamin", times=2, medication="Vitamin D")
        _dose(two, datetime(2026, 11, 20, 8), state)
        state["clock"] = datetime(2026, 11, 20, 8, 5)
        out = O.update_task(two, "done", evidence="took it")
        assert out.startswith("error:") and "reported twice" in out, out
        assert _row(O.medication_taken(day=DAY), two)["done"] == 1
        _dose(two, datetime(2026, 11, 20, 8, 20), state)
        assert _row(O.medication_taken(day=DAY), two)["done"] == 2
        plain = _habit("Stretching")
        _dose(plain, datetime(2026, 11, 20, 9), state)
        _dose(plain, datetime(2026, 11, 20, 9), state)
        assert _task(plain)["occurrences"]["2026-11-20"]["done"] == 2, "unlinked: unchanged"


@check("fix 6: a second open habit cannot be linked to the same medicine — open_task and "
       "set_medication both refuse and name the habit that holds it")
def _():
    import tools.obligations as O
    with _sandbox("synthesizer") as (_d, _s):
        first = _habit("Evening tablet", medication="Atorvastatin")
        out = O.open_task("Statin", kind="habit", every="day", new_instance=True,
                          medication="atorvastatin")
        assert out.startswith("error:") and first in out and "Evening tablet" in out, out
        second = _habit("Statin")
        out = O.update_task(second, "set_medication", medication="Atorvastatin")
        assert out.startswith("error:") and first in out, out
        assert "medication" not in _task(second)
        assert "linked" in O.update_task(first, "set_medication", medication="Atorvastatin")
        O.update_task(first, "set_medication", medication="")
        assert "linked to 'Atorvastatin'" in O.update_task(second, "set_medication",
                                                            medication="Atorvastatin")


@check("fix 7: a linked habit is essential and weighted only when the profile says required — "
       "an optional supplement titled 'tablets' is neither; an unreadable criticality is")
def _():
    import tools.day_plan as DP
    import tools.obligations as O
    with _sandbox() as (_d, _s):
        vit = _task(_habit("Vitamin D tablets", medication="Vitamin D"))
        statin = _task(_habit("Evening statin", medication="Atorvastatin"))
        prn = _task(_habit("Inhaler check", medication="Salbutamol inhaler"))
        assert not O.is_essential(vit) and not O.is_essential(prn)
        assert O.is_essential(statin)
        w = {"medication": 100}

        def score(t):
            return DP._score(t, O._view(t, DAY), DAY, {}, w)
        assert score(statin) - score(vit) == 100, (score(statin), score(vit))
        assert O.is_essential(_task(_habit("Take my pills"))), "unlinked: the name net stays"
        _seed_profile(P, {"medications": [m for m in PROFILE["medications"]
                                          if m["name"] != "Vitamin D"]})
        assert O.is_essential(vit), "a broken link's criticality is unknown: never demoted"


@check("fix 8: only the Synthesizer, the health agents and code may set a link; anyone else "
       "gets one refusal, identical for a real and an unknown name")
def _():
    import tools.obligations as O
    with _sandbox("finance") as (_d, state):
        real = O.open_task("A", kind="habit", every="day", medication="Atorvastatin")
        fake = O.open_task("B", kind="habit", every="day", medication="Bisoprolol")
        assert real == fake == O._LINK_REFUSAL, (real, fake)
        assert not O._load(), "nothing written"
        state["caller"] = "logistics"
        tid = O.open_task("Evening tablet", kind="habit", every="day").split()[1]
        assert O.update_task(tid, "set_medication", medication="Atorvastatin") == \
            O.update_task(tid, "set_medication", medication="Bisoprolol") == \
            O.update_task(tid, "set_medication", medication="") == O._LINK_REFUSAL
        assert O.open_task("C", kind="habit", every="day", medication="Atorvastatin",
                           new_instance=True) == O._LINK_REFUSAL
        for agent in ("synthesizer", "physical_health", "mental_wellbeing", ""):
            state["caller"] = agent
            out = O.update_task(tid, "set_medication", medication="Atorvastatin")
            assert "linked to 'Atorvastatin'" in out or "already linked" in out, (agent, out)
            O.update_task(tid, "set_medication", medication="")


@check("fix 9: 'add X to my medications' still finds the view (so no second list is started), "
       "and every refusal says a medication change goes to the profile Physical Health keeps")
def _():
    import core.orchestrator as OR
    import tools.data_objects as DO
    with _sandbox("synthesizer") as (_d, _s):
        assert DO.resolve("medications")["id"] == "medication_taken"
        out = DO.write_data_object("medications", {"text": "add a new statin"})
        assert "medication profile" in out and "Physical Health" in out, out
        coord = ('SPECIALISTS_TO_CALL: []\n\nDATA_OBJECTS: [{"name": "medications", '
                 '"act": "add"}]')
        turn = OR._resolve_data_objects(coord, persona=P, user_turn=True)
        block = OR._data_object_block(turn, [])
        assert "medication profile" in block and "Physical Health" in block, block


def _a4_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location("run_a4_safety_mod",
                                                  ROOT / "tests" / "run_a4_safety.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@check("fix 10: PH-MED-UNLINKED is on the designated safety path — same prompt as PH-MED, "
       "expects MEDICATION_MISSED_CRITICAL, and each scenario names the ledger state it needs")
def _():
    A4 = _a4_module()
    by_id = {s["id"]: s for s in A4.CLINICAL}
    linked, unlinked = by_id["PH-MED"], by_id["PH-MED-UNLINKED"]
    assert unlinked["agent"] == "physical_health" and unlinked["prompt"] == linked["prompt"]
    assert unlinked["expect_any"] == ["MEDICATION_MISSED_CRITICAL"]
    assert "MUST_SURFACE" in unlinked["also_require"]
    assert (linked["med_state"], unlinked["med_state"]) == ("linked", "unlinked")
    pipe = next(s for s in A4.PIPELINE if s["id"] == "PH-MED-PIPE")
    assert pipe["med_state"] == "linked"
    src = (ROOT / "tests" / "run_a4_safety.py").read_text()
    assert 'prepare_medication_state(args.persona, s["med_state"])' in src


@check("fix 10: the fixture makes each state for real — linked: lamotrigine's habit, nothing "
       "done, missed; unlinked: no habit, nothing logged, missed and needs_link; and back again "
       "without a second habit")
def _():
    import tools.obligations as O
    A4 = _a4_module()
    with _sandbox("", persona=P2) as (data, state):
        A4.seed_medication_fixture(P2)
        A4.prepare_medication_state(P2, "linked")
        lam = _by_name(O.medication_taken(), "lamotrigine")
        assert (lam["linked"], lam["done"], lam["missed"]) == (True, 0, True), lam
        assert _by_name(O.medication_taken(), "vitamin D")["linked"] is True
        _dose(lam["task_id"], datetime(2026, 11, 20, 9, 5), state)
        _write_day_log(data, DAY, [{"name": "lamotrigine", "taken": True}])
        A4.prepare_medication_state(P2, "unlinked")
        lam = _by_name(O.medication_taken(), "lamotrigine")
        assert (lam["linked"], lam["logged"], lam["missed"], lam["needs_link"]) == \
            (False, False, True, True), lam
        assert _by_name(O.medication_taken(), "vitamin D")["linked"] is True
        A4.prepare_medication_state(P2, "linked")
        lam = _by_name(O.medication_taken(), "lamotrigine")
        assert (lam["linked"], lam["done"], lam["missed"]) == (True, 0, True), lam
        habits = [t for t in O._load() if t.get("kind") == "habit"]
        assert len(habits) == 2, habits


# ---------------------------------------------------------------------------
# Second review, 2026-11-23: A1 and items 1–9
# ---------------------------------------------------------------------------

_PH_OUT = ("SLEEP: 5 / poor\nFOOD: not logged\nENERGY: low\n"
           "- **MEDICATION_TAKEN:** atorvastatin at 08:00; Bisoprolol; Vitamin D.\n"
           "FLAGS: none")


@check("A1: the MEDICATION_TAKEN line parses tolerantly but never fuzzily — marks before the "
       "key, ' at <time>', quotes and a full stop dropped; 'none' and the template ignored")
def _():
    import tools.obligations as O
    assert O.parse_medication_taken(_PH_OUT) == ["atorvastatin", "Bisoprolol", "Vitamin D"]
    assert O.parse_medication_taken("MEDICATION_TAKEN: none") == []
    assert O.parse_medication_taken("MEDICATION_TAKEN: [each dose the user reported]") == []
    assert O.parse_medication_taken("MEDICATION_TAKEN: `Atorvastatin`; Atorvastatin") == \
        ["Atorvastatin", "Atorvastatin"]
    assert O.parse_medication_taken("I took my MEDICATION_TAKEN stuff") == []


@check("A1 end to end: Physical Health's line is recorded by code on the linked habit, whatever "
       "the user's words — the view reads it done, and the Synthesizer gets the note line")
def _():
    import core.orchestrator as OR
    import tools.obligations as O
    from tools import turn_context as T
    with _sandbox("physical_health") as (_d, state):
        tid = _old_habit(state, "Evening tablet", medication="Atorvastatin")
        with T.turn_scope(user_turn=True) as turn:   # the close gate would refuse these words
            turn.update(close_gate=True, user_text="rough morning, heading to work",
                        prev_assistant="")
            note = OR._record_reported_doses({"physical_health": _PH_OUT}, P, True)
        # Vitamin D is a profile medicine with no linked habit: since Stage 3 (Revision 2 L4)
        # code writes its medications_logged entry too.
        assert note.startswith("MEDICATION NOTE (from code): Recorded by code: ") \
            and "Atorvastatin (1 of 1 today)" in note \
            and "Vitamin D (logged as taken today)" in note \
            and "do not record them again" in note, note
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["done"], r["missed"]) == (1, False), r
        assert "Physical Health reported 1 dose" in _task(tid)["occurrences"]["2026-11-20"][
            "completions"][0]["evidence"]
        state["clock"] = datetime(2026, 11, 20, 9, 30)
        again = OR._record_reported_doses({"physical_health": _PH_OUT}, P, True)
        assert "Atorvastatin — already recorded, not counted again" in again, again
        assert _row(O.medication_taken(day=DAY), tid)["done"] == 1
        assert OR._record_reported_doses({"physical_health": _PH_OUT}, P, False) == "", \
            "a scheduled turn records nothing"


@check("A1: a name not in the profile and a near-miss spelling are left alone — no dose, no "
       "note; a profile name with no linked habit is logged by code (Stage 3, Revision 2 L4)")
def _():
    import core.orchestrator as OR
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _old_habit(state, "Evening tablet", medication="Atorvastatin")
        out = ("MEDICATION_TAKEN: Bisoprolol; Atorvastatin 20mg; Atorvastatn")
        assert OR._record_reported_doses({"physical_health": out}, P, True) == ""
        vit = OR._record_reported_doses({"physical_health": "MEDICATION_TAKEN: Vitamin D"}, P, True)
        assert "Vitamin D (logged as taken today)" in vit, vit
        assert _row(O.medication_taken(day=DAY), tid)["done"] == 0
        assert OR._record_reported_doses({"finance": "MEDICATION_TAKEN: Atorvastatin"}, P,
                                         True) == "", "only Physical Health's line counts"
        note = OR._record_reported_doses(
            {"physical_health": "MEDICATION_TAKEN: Atorvastatin; Atorvastatin"}, P, True)
        assert "Atorvastatin (1 of 1 today)" in note, "a once-daily medicine counts once: " + note
        assert _row(O.medication_taken(day=DAY), tid)["done"] == 1


@check("A1 / finding 6: a negated clause never names the medicine — 'I haven't taken my "
       "atorvastatin yet' is refused by the close gate")
def _():
    import tools.obligations as O
    from tools import turn_context as T
    with _sandbox("synthesizer") as (_d, state):
        tid = _old_habit(state, "Evening tablet", medication="Atorvastatin")
        for text in ("I haven't taken my atorvastatin yet", "still need to take the atorvastatin"):
            with T.turn_scope(user_turn=True) as turn:
                turn.update(close_gate=True, user_text=text, prev_assistant="")
                out = O.update_task(tid, "done", evidence=text)
            assert out.startswith("error: not recorded"), (text, out)
        assert _row(O.medication_taken(day=DAY), tid)["done"] == 0


@check("item 1: a habit linked mid-day takes the day's logged 'taken' doses — open_task and "
       "set_medication — so linking never erases a dose already logged")
def _():
    import tools.obligations as O
    with _sandbox() as (data, state):
        _write_day_log(data, DAY, [
            {"name": "Atorvastatin", "taken": True, "logged_at": "2026-11-20T08:05:00"},
            {"name": "Vitamin D", "taken": False, "logged_at": "2026-11-20T08:05:00"}])
        state["clock"] = datetime(2026, 11, 20, 12)
        out = O.open_task("Evening tablet", kind="habit", every="day", new_instance=True,
                          medication="Atorvastatin")
        assert "1 dose(s) already logged as taken today counted on it" in out, out
        tid = out.split()[1]
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["done"], r["missed"], r["doses"][0]["recorded_at"]) == \
            (1, False, "2026-11-20T08:05:00"), r
        other = _habit("Morning capsule")
        out = O.update_task(other, "set_medication", medication="Vitamin D")
        assert "already logged" not in out, "taken: false is not a dose"
        _write_day_log(data, DAY, [{"name": "Vitamin D", "taken": True,
                                    "logged_at": "2026-11-20T08:00:00"}])
        O.update_task(other, "set_medication", medication="")
        assert "1 dose(s)" in O.update_task(other, "set_medication", medication="Vitamin D")


@check("item 1: a once-daily habit created at 21:00 owes nothing that day, and owes the next "
       "day's dose from its start")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        state["clock"] = datetime(2026, 11, 20, 21)
        tid = _habit("Statin", medication="Atorvastatin")
        r = _row(O.medication_taken(day=DAY), tid)
        assert (r["due_now"], r["missed"]) == (0, False), r
        state["clock"] = datetime(2026, 11, 21, 9)
        assert _row(O.medication_taken(day=DAY), tid)["missed"] is False, "the creation day " \
            "stays owed nothing once over"
        r = _row(O.medication_taken(), tid)
        assert (r["due_now"], r["missed"]) == (1, True), r


@check("item 3: yesterday's dose reported now and today's dose a minute later are two doses; "
       "'took both' records both of a twice-daily medicine; the cap still holds")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        tid = _old_habit(state, "Statin", medication="Atorvastatin", days=3)
        state["clock"] = datetime(2026, 11, 20, 9)
        assert "recorded" in O.update_task(tid, "done", evidence="took it yesterday",
                                           on_date="2026-11-19")
        state["clock"] = datetime(2026, 11, 20, 9, 1)
        assert "recorded" in O.update_task(tid, "done", evidence="and today's")
        assert _row(O.medication_taken(day=date(2026, 11, 19)), tid)["done"] == 1
        assert _row(O.medication_taken(day=DAY), tid)["done"] == 1
        two = _old_habit(state, "Vitamin", times=2, medication="Vitamin D")
        for _ in range(2):
            out = O.update_task(two, "done", evidence="took both this morning")
            assert "recorded" in out, out
        out = O.update_task(two, "done", evidence="took both this morning")
        assert "already recorded 2 of 2 today" in out, out


@check("item 4: one skip of a three-a-week medicine skips one dose — the others are still owed")
def _():
    import tools.obligations as O
    with _sandbox() as (_d, state):
        state["clock"] = datetime(2026, 11, 15, 9)                       # the Sunday before
        tid = O.open_task("Weekly tablet", kind="habit", every="week", times=3,
                          on_days=["mon", "wed", "fri"], new_instance=True,
                          medication="Atorvastatin").split()[1]
        state["clock"] = datetime(2026, 11, 20, 9)                       # Friday
        O.update_task(tid, "done", evidence="took Monday's", on_date="2026-11-16")
        out = O.update_task(tid, "skipped", evidence="skipped Wednesday on advice")
        assert "one dose skipped" in out, out
        r = _row(O.medication_taken(), tid)
        assert (r["due_now"], r["done"], r["skipped_count"], r["skipped"], r["missed"]) == \
            (3, 1, 1, False, True), r
        assert O._view(_task(tid), DAY)["state"] != "skipped", "the week is not skipped whole"
        _dose(tid, datetime(2026, 11, 20, 9, 30), state)
        r = _row(O.medication_taken(), tid)
        assert (r["missed"], r["skipped"]) == (False, False), r
        assert "already done or skipped" in O.update_task(tid, "skipped", evidence="x")
        assert "no longer skipped" in O.update_task(tid, "reopen", evidence="I did take it")
        assert _row(O.medication_taken(), tid)["skipped_count"] == 0


@check("item 5: on a day that starts at 04:00, a dose logged at 01:30 (in the next date's file) "
       "counts for the day before; a legacy entry with no stamp keeps its file's date")
def _():
    import tools.logger as LOG
    import tools.obligations as O
    with _sandbox() as (data, state):
        O._with_store(None, lambda doc: doc.setdefault("settings", {}).update(day_starts="04:00"))
        nxt = date(2026, 11, 21)
        _write_day_log(data, nxt, [
            {"name": "Atorvastatin", "taken": True, "logged_at": "2026-11-21T01:30:00"},
            {"name": "Vitamin D", "taken": True}])
        state["clock"] = datetime(2026, 11, 21, 1, 45)
        view = O.medication_taken()
        assert view["day"] == "2026-11-20", view["day"]
        assert _by_name(view, "Atorvastatin")["logged"] is True
        assert _by_name(view, "Vitamin D")["logged"] is False, "legacy: its file's own date"
        assert _by_name(O.medication_taken(day=nxt), "Vitamin D")["logged"] is True
        assert _by_name(O.medication_taken(day=nxt), "Atorvastatin")["logged"] is False
        e = {"name": "Atorvastatin", "logged_at": "2026-11-21T01:30:00"}
        assert LOG._entry_day(e, "2026-11-21") == "2026-11-20"


@check("item 7: a dose refusal names the medicine only to a caller that may set a link")
def _():
    import tools.obligations as O
    with _sandbox("finance") as (_d, state):
        state["caller"] = ""
        tid = _old_habit(state, "Evening tablet", medication="Atorvastatin")
        _dose(tid, datetime(2026, 11, 20, 8), state)
        state["caller"] = "finance"
        out = O.update_task(tid, "done", evidence="took it")
        assert out.startswith("error:") and "Atorvastatin" not in out and \
            "this medication" in out, out
        state["caller"] = "synthesizer"
        assert "Atorvastatin" in O.update_task(tid, "done", evidence="took it")


@check("item 8: a second dose list under another name finds the read-only view — every fixed "
       "name, through write_archive and when starting a log")
def _():
    import tools.data_objects as DO
    import tools.diarist as DI
    with _sandbox("diarist") as (data, _s):
        for name in ("meds", "medicine", "medicines", "med log", "doses", "pills (taken)",
                     "Pills taken"):
            assert DO.resolve(name)["id"] == "medication_taken", name
            out = DI.write_archive(name, {"text": "took my tablets"})
            assert out.startswith("Not recorded") and "read-only" in out, (name, out)
            out = DO.create_object(name)
            assert not out.get("created") and out["match"]["id"] == "medication_taken", (name, out)
        assert DO.resolve("pills") is None, "bare 'pills' is not claimed"
        assert not (data / "archive").exists() or not any((data / "archive").glob("*"))


@check("item 9: the safety prep clears a skip an earlier run left on a fixture habit")
def _():
    import tools.obligations as O
    A4 = _a4_module()
    with _sandbox("", persona=P2) as (_d, _s):
        A4.seed_medication_fixture(P2)
        A4.prepare_medication_state(P2, "linked")
        lam = _by_name(O.medication_taken(), "lamotrigine")
        O.update_task(lam["task_id"], "skipped", evidence="leftover from a run")
        assert _by_name(O.medication_taken(), "lamotrigine")["missed"] is False
        A4.prepare_medication_state(P2, "linked")
        lam = _by_name(O.medication_taken(), "lamotrigine")
        assert (lam["skipped_count"], lam["missed"]) == (0, True), lam


if __name__ == "__main__":
    for name, ok, err in _results:
        print(("PASS " if ok else "FAIL ") + name + ("" if ok else f"\n     {err}"))
    failed = [r for r in _results if not r[1]]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
