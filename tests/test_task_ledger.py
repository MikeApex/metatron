"""
tests/test_task_ledger.py — the task ledger (tools/obligations.py), one check per failure the
history audit measured. Plan: archive/plans/task_ledger_plan_2026-10-23.md § 11.

Measured on the live store 09-20 → 10-23: sixteen items raised after they were done, decided or
moot, ~85 stale raises. Each block below is one of those classes, built on synthetic data in a
temp directory — no persona data. Run it, do not read it:

    python3 tests/test_task_ledger.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.obligations as O  # noqa: E402
import tools.turn_context as TC  # noqa: E402

_results: list[tuple[str, bool, str]] = []
_TMP = Path(tempfile.mkdtemp(prefix="task_ledger_"))
_CLOCK = {"now": datetime(2026, 10, 23, 9, 0, 0)}


def _fresh(name: str) -> Path:
    d = _TMP / name
    d.mkdir(parents=True, exist_ok=True)
    O.persona_data_dir = lambda persona=None, _d=d: _d
    return d


def _at(y, m, d, hh=9, mm=0):
    _CLOCK["now"] = datetime(y, m, d, hh, mm, 0)


O._now = lambda: _CLOCK["now"]


def check(name: str):
    def deco(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as exc:  # noqa: BLE001
            _results.append((name, False, f"{type(exc).__name__}: {exc}"))
        return fn
    return deco


def _id(msg: str) -> str:
    assert msg.startswith("task "), msg
    return msg.split()[1]


def _task(tid: str) -> dict:
    return next(t for t in O._load() if t["id"] == tid)


def _history() -> list[dict]:
    return O._history_rows()


# --- The store: import, never write v1, roll-forward re-merge --------------------------------

_V1 = """obligations:
- id: ob_260819_77a126
  what: Finalise Apex migration plan
  status: open
  opened_at: '2026-08-19T15:15:11'
  domain: finance
  due: '2026-08-31'
- id: ob_261001_aaaaaa
  what: Call the plumber
  status: open
  opened_at: '2026-10-01T10:00:00'
  due: next week
- id: ob_261010_bbbbbb
  what: Pay council tax
  status: closed
  opened_at: '2026-10-10T10:00:00'
  closed_at: '2026-10-12T10:00:00'
  evidence: paid it this morning
"""


@check("v1 import keeps ids, maps closed→done, moves a vague due into the note")
def _():
    d = _fresh("import")
    (d / "obligations.yaml").write_text(_V1)
    tasks = {t["id"]: t for t in O._load()}
    assert set(tasks) == {"ob_260819_77a126", "ob_261001_aaaaaa", "ob_261010_bbbbbb"}, tasks
    assert tasks["ob_261010_bbbbbb"]["status"] == "done"
    assert tasks["ob_261010_bbbbbb"]["evidence"] == "paid it this morning"
    assert "due" not in tasks["ob_261001_aaaaaa"]
    assert "next week" in tasks["ob_261001_aaaaaa"]["note"]
    assert tasks["ob_260819_77a126"]["due"] == "2026-08-31"
    assert (d / "tasks.yaml").exists()


@check("obligations.yaml is byte-identical after import AND after a write through the new tools")
def _():
    d = _fresh("v1_untouched")
    (d / "obligations.yaml").write_text(_V1)
    before = (d / "obligations.yaml").read_bytes()
    O._load()
    O.update_task("ob_260819_77a126", "done", evidence="sorted")
    O.open_task("Renew passport", kind="deadline", due="2026-12-01")
    O.update_task("ob_261001_aaaaaa", "done", evidence="plumber came")
    assert (d / "obligations.yaml").read_bytes() == before


@check("rollback re-merge: v1 may add and may close, never reopen; a v1 twin is skipped")
def _():
    import os
    import time
    d = _fresh("remerge")
    (d / "obligations.yaml").write_text(_V1)
    O._load()
    O.update_task("ob_261001_aaaaaa", "done", evidence="plumber came Tuesday")
    tid = _id(O.open_task("Book the boiler service", kind="deadline"))
    # Old code during a rollback: closes Apex, "reopens" the plumber, adds a new id and a twin.
    rolled = _V1.replace("""  domain: finance
  due: '2026-08-31'""", """  domain: finance
  due: '2026-08-31'
  status: closed""").replace("status: open\n  opened_at: '2026-08-19T15:15:11'\n",
                              "opened_at: '2026-08-19T15:15:11'\n")
    rolled += """- id: ob_261020_cccccc
  what: Return library books
  status: open
  opened_at: '2026-10-20T10:00:00'
- id: ob_261020_dddddd
  what: Book the boiler service
  status: open
  opened_at: '2026-10-20T10:00:00'
"""
    time.sleep(0.02)
    (d / "obligations.yaml").write_text(rolled)
    os.utime(d / "obligations.yaml", None)
    tasks = {t["id"]: t for t in O._load()}
    assert tasks["ob_260819_77a126"]["status"] == "done", tasks["ob_260819_77a126"]
    assert tasks["ob_261001_aaaaaa"]["status"] == "done", "v1 must never reopen a v2 close"
    assert "ob_261020_cccccc" in tasks, "a new v1 id is imported"
    assert "ob_261020_dddddd" not in tasks, "a v1 twin of an open v2 task is skipped"
    assert tid in tasks


@check("an unreadable tasks.yaml: writes refused, the damaged file preserved, reads empty")
def _():
    d = _fresh("corrupt")
    (d / "tasks.yaml").write_text("version: 2\ntasks: [unclosed\n")
    msg = O.open_task("Anything", kind="deadline")
    assert msg.startswith("error:"), msg
    assert any(p.name.startswith("tasks.yaml.corrupt-") for p in d.iterdir())
    assert (d / "tasks.yaml").read_text().startswith("version: 2\ntasks: [unclosed")
    assert O._load() == []
    assert O.context_block() == ""


# --- Dedupe: the Chase re-mint, the inbox twin ----------------------------------------------

@check("Chase re-mint: re-filing a task closed yesterday is refused unless new_instance")
def _():
    _fresh("chase")
    _at(2026, 10, 15)
    tid = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-17",
                          domain="finance"))
    O.update_task(tid, "done", evidence="already handled as of a few days ago")
    _at(2026, 10, 16, 19)
    again = O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-17")
    assert not again.startswith("task "), again
    assert tid in again and "already handled" in again, again
    forced = O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-11-17",
                         new_instance=True)
    assert forced.startswith("task "), forced


@check("inbox twin: two jobs filing from the same message — the second is refused")
def _():
    _fresh("twin")
    a = O.open_task("Send signed e-file forms to S.A.R.", kind="deadline", due="2026-10-15",
                    source_id="env_abc123")
    b = O.open_task("Return the 2025 e-file signature pages", kind="deadline",
                    source_id="env_abc123")
    assert a.startswith("task ") and not b.startswith("task "), (a, b)
    assert "same message" in b


@check("open near-duplicates are still refused (the v1 guard survives)")
def _():
    _fresh("neardup")
    O.open_task("Rowan payroll transfer", kind="deadline")
    msg = O.open_task("rowan payroll transfer", kind="deadline")
    assert msg.startswith("already open"), msg


# --- Kinds: deadline, moot, interval, waiting, habits ----------------------------------------

@check("RSVP: moot after its event — out of Now, and the sweep records it moot")
def _():
    _fresh("rsvp")
    _at(2026, 9, 18)
    tid = _id(O.open_task("RSVP to Schwab client event", kind="deadline", due="2026-09-24",
                          moot_after="2026-10-01"))
    _at(2026, 9, 26)
    assert "overdue since 2026-09-24" in O.context_block()
    _at(2026, 10, 2)
    block = O.context_block()
    assert tid not in block.split("**Closed recently")[0], block
    O.sweep()
    assert _task(tid)["status"] == "moot"
    assert any(r["task_id"] == tid and r["state"] == "moot" for r in _history())


@check("a deadline with no moot date stays overdue until done or dismissed (Mike's default)")
def _():
    _fresh("overdue")
    _at(2026, 8, 19)
    tid = _id(O.open_task("Finalise Apex migration plan", kind="deadline", due="2026-08-31"))
    _at(2026, 10, 23)
    O.sweep()
    assert _task(tid)["status"] == "open"
    assert "overdue since 2026-08-31" in O.context_block()
    O.update_task(tid, "dismissed", evidence="dropping it")
    assert tid not in O.context_block().split("**Closed recently")[0]


@check("reschedule keeps history, reopens nothing it should not, and the close counts late")
def _():
    _fresh("resched")
    _at(2026, 8, 19)
    tid = _id(O.open_task("Finalise Apex migration plan", kind="deadline", due="2026-08-31"))
    _at(2026, 10, 19)
    O.update_task(tid, "reschedule", new_due="2026-11-15",
                  evidence="defer Apex migration tasks to mid-November")
    t = _task(tid)
    assert t["due"] == "2026-11-15"
    assert t["history"][-1]["from"] == "2026-08-31" and t["history"][-1]["was_overdue"]
    _at(2026, 11, 20)
    O.update_task(tid, "done", evidence="finally done")
    row = [r for r in _history() if r["task_id"] == tid][-1]
    assert row["late"] is True and row.get("rescheduled") is True, row


@check("plant watering: due from the last time it was done, never from a frozen date")
def _():
    _fresh("plants")
    _at(2026, 10, 20)
    tid = _id(O.open_task("Water the plants", kind="interval", interval_days=3,
                          last_done="2026-10-20"))
    _at(2026, 10, 22)
    assert "Water the plants" not in O.context_block().split("**Later")[0]
    _at(2026, 10, 23)
    block = O.context_block()
    assert f"`{tid}@2026-10-23` Water the plants — due today" in block, block
    O.update_task(tid, "done", evidence="watered them this morning")
    t = _task(tid)
    assert t["last_done"] == "2026-10-23"
    assert O._interval_due(t, date(2026, 10, 23)) == date(2026, 10, 26)
    assert "done today; next due 2026-10-26" in O.context_block()


@check("waiting on someone: never overdue; surfaced at check-back as their move, not the user's")
def _():
    _fresh("waiting")
    _at(2026, 10, 2)
    tid = _id(O.open_task("Sirva furniture claim inspection", kind="waiting",
                          waiting_on="Sirva", expect_from="sirva.com"))
    _at(2026, 10, 5)
    block = O.context_block()
    assert "1 waiting on others" in block and tid not in block, block
    _at(2026, 10, 9)
    block = O.context_block()
    assert "waiting on Sirva since 2026-10-02" in block and "overdue" not in block.split(
        "never present")[0], block


@check("3×/week gym (M/W/F): a missed Monday can be made up Tuesday; week ends 2/3 → missed")
def _():
    _fresh("gym")
    _at(2026, 10, 18)  # Sunday — the task starts in week 42
    tid = _id(O.open_task("Gym", kind="habit", every="week", times=3,
                          on_days=["mon", "wed", "fri"]))
    _at(2026, 10, 19)  # Monday, week 43: planned day
    assert "today is a planned day" in O.context_block()
    _at(2026, 10, 20)  # Tuesday: Monday missed
    block = O.context_block()
    assert "0 of 3 this week" in block and "made up today" in block, block
    O.update_task(tid, "done", evidence="went to the gym")
    _at(2026, 10, 21)
    O.update_task(tid, "done", evidence="gym again")
    _at(2026, 10, 27)  # the next Tuesday — week 43 has ended at 2/3
    O.sweep()
    rows = [r for r in _history() if r["task_id"] == tid]
    w42 = [r for r in rows if r["occurrence"].endswith("2026-W42")]
    w43 = [r for r in rows if r["occurrence"].endswith("2026-W43")]
    assert w42 and w42[0]["partial"] is True, rows
    assert w43 and w43[0]["state"] == "missed" and w43[0]["done"] == 2, rows
    stats = [s for s in O.adherence(days=30) if s["task_id"] == tid][0]
    assert stats["target"] == 3 and stats["completed"] == 2 and stats["partial"] == 1, stats


@check("daily stretching: missed at midnight, recorded once however often the sweep runs")
def _():
    _fresh("stretch")
    _at(2026, 10, 21)
    tid = _id(O.open_task("Stretching", kind="habit", every="day"))
    _at(2026, 10, 22, 7)
    O.update_task(tid, "done", evidence="did my stretches")
    _at(2026, 10, 24, 0, 15)
    O.sweep()
    O.sweep()
    rows = [r for r in _history() if r["task_id"] == tid]
    states = {r["occurrence"].split("@")[1]: r["state"] for r in rows}
    assert states == {"2026-10-21": "missed", "2026-10-22": "done", "2026-10-23": "missed"}, states
    assert len(rows) == 3, rows


@check("planned is not done: nothing marks a habit done without a done record")
def _():
    _fresh("planned")
    _at(2026, 10, 22, 7)
    O.open_task("Home stretches", kind="habit", every="day")
    assert "Home stretches — today" in O.context_block()


@check("dormant until eligible: a deferred task stays out of view until its date")
def _():
    _fresh("eligible")
    _at(2026, 10, 1)
    tid = _id(O.open_task("Book flu jab", kind="deadline", eligible_from="2026-10-15"))
    assert tid not in O.context_block() and "1 not yet eligible" in O.context_block()
    _at(2026, 10, 15)
    assert tid in O.context_block()


# --- The hint --------------------------------------------------------------------------------

@check("hint fires on the real phrasing — 'paid the Chase bill' — and not on 'still need to'")
def _():
    _fresh("hint")
    tid = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-17"))
    assert tid in O.completion_hints("I paid the Chase bill this morning")
    assert tid in O.completion_hints("Paid the credit card, don't remind me again")
    assert O.completion_hints("I still need to pay Chase") == ""
    assert O.completion_hints("haven't paid the chase bill yet") == ""
    # A known, accepted over-fire: the other party acting ("Chase called") reads like a
    # completion. The note only asks the Synthesizer to check and to ask if unsure — it
    # never records anything — so a false hint costs one question, not a wrong close.
    assert tid in O.completion_hints("Chase called about the card")


@check("hint: single-token tasks (Stretching) and the real chiropractor-forms phrasing")
def _():
    _fresh("hint2")
    s = _id(O.open_task("Stretching", kind="habit", every="day"))
    f = _id(O.open_task("Greenwich clinic patient registration and history forms",
                        kind="deadline"))
    assert s in O.completion_hints("did my stretches this morning")
    assert f in O.completion_hints("Patient registration stuff submitted")


@check("hint: a bare 'yes, done' confirms what the previous reply raised")
def _():
    _fresh("hint3")
    _at(2026, 10, 23)
    tid = _id(O.open_task("Water the plants", kind="interval", interval_days=3,
                          last_done="2026-10-20"))
    note = O.completion_hints("yes, done", prev_assistant="Have you watered the plants yet?")
    assert tid in note and "confirming" in note, note
    assert O.completion_hints("yes, done", prev_assistant="How was the drive?") == ""


# --- Raise once, in code ---------------------------------------------------------------------

@check("raise-once: held back on a later check-in, shown on a user turn and the evening close")
def _():
    _fresh("raise")
    _at(2026, 10, 23, 9)
    tid = _id(O.open_task("Water the plants", kind="interval", interval_days=3,
                          last_done="2026-10-20"))
    assert O.note_raised("Morning — the plants are due a water today.") == 1
    _at(2026, 10, 23, 14)
    with TC.turn_scope(user_turn=False) as turn:
        turn["kind"] = "companion_checkin"
        b = O.context_block()
        assert tid not in b and "1 more already raised today" in b, b
        turn["kind"] = "evening_close"
        assert tid in O.context_block()
        turn["kind"] = "morning_brief"
        turn["weekly_review"] = True
        assert tid in O.context_block()
    with TC.turn_scope(user_turn=True):
        b = O.context_block()
        assert tid in b and "already raised today" in b, b
    assert tid in O.context_block()  # no bound turn: nothing hidden
    _at(2026, 10, 24, 9)
    O.update_task(tid, "reschedule", new_due="2026-10-24", evidence="rain")
    with TC.turn_scope(user_turn=False) as turn:
        turn["kind"] = "companion_checkin"
        assert tid in O.context_block(), "a new day is a new raise"


# --- The block's other sections --------------------------------------------------------------

@check("closed recently: the close is shown beside the stale copies, with the user's words")
def _():
    _fresh("recent")
    _at(2026, 10, 15)
    tid = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-17"))
    O.update_task(tid, "done", evidence="already handled as of a few days ago")
    _at(2026, 10, 17)
    block = O.context_block()
    part = block.split("**Closed recently")[1]
    assert tid in part and "already handled" in part, block
    _at(2026, 10, 22)
    assert O.context_block() == "", "past the recent window, a closed task says nothing"


@check("errors carry the lowercase error: prefix the tool-error flag keys on")
def _():
    _fresh("errors")
    for msg in (O.update_task("nope-1234", "done", evidence="x"),
                O.update_task("nope-1234", "done"),
                O.open_task("", kind="deadline"),
                O.open_task("Gym", kind="habit"),
                O.open_task("x", kind="deadline", due="next week")):
        assert msg.startswith("error:"), msg


# --- Correspondence proposals, the app tap ---------------------------------------------------

@check("a proposal stores ids and dates only; accept closes with fixed evidence; decline sticks")
def _():
    d = _fresh("proposal")
    tid = _id(O.open_task("2025 tax e-file confirmation from S.A.R.", kind="waiting",
                          waiting_on="S.A.R.", expect_from="sar-cpa.com"))
    assert O.add_proposal(tid, "env_1", "sender", "2026-10-24T10:00:00")
    assert not O.add_proposal(tid, "env_1", "sender"), "one proposal per message"
    raw = (d / "tasks.yaml").read_text()
    assert "IGNORE PREVIOUS" not in raw
    pend = O.pending_proposals()
    assert len(pend) == 1 and set(pend[0]) >= {"proposal_id", "task_id", "envelope_id"}
    assert "Waiting for the user's tap" in O.context_block()
    out = O.resolve_proposal(pend[0]["proposal_id"], accept=False)
    assert "will not be offered again" in out and O.pending_proposals() == []
    assert not O.add_proposal(tid, "env_1", "sender")
    assert O.add_proposal(tid, "env_2", "thread")
    p2 = O.pending_proposals()[0]["proposal_id"]
    out = O.resolve_proposal(p2, accept=True)
    assert out.startswith(f"{tid} done"), out
    assert _task(tid)["evidence"].startswith(O._CORRESPONDENCE_EVIDENCE)


@check("the Today panel: actionable items with actions; a tap records the tap as evidence")
def _():
    _fresh("tap")
    _at(2026, 10, 23)
    a = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-22"))
    b = _id(O.open_task("Stretching", kind="habit", every="day"))
    items = {i["task_id"]: i for i in O.today_items()}
    assert set(items) == {a, b}, items
    assert items[a]["actions"] == ["done", "done_with_followup", "dismissed"] and items[b]["actions"] == ["done", "skipped"]
    assert O.act_from_app(a, "done").startswith(f"{a} done")
    assert _task(a)["evidence"] == "marked in the app"
    assert O.act_from_app(a, "delete").startswith("error:")


@check("the Today panel leaves out what is merely upcoming; the Tasks block still carries it")
def _():
    _fresh("tap_upcoming")
    _at(2026, 10, 24)
    s = _id(O.open_task("Review Schwab Treasury maturities", kind="deadline", due="2026-10-26"))
    t = _id(O.open_task("Post babysitter job", kind="deadline", due="2026-10-24"))
    assert {i["task_id"] for i in O.today_items()} == {t}
    assert s in O.context_block(), "the head layer keeps the two-day lead"


@check("done with a loose end closes the task and opens the loose end as its own task")
def _():
    # The Thanksgiving case: done, but no contact details to send the invitation to.
    _fresh("followup")
    _at(2026, 10, 24)
    a = _id(O.open_task("Plan Thanksgiving invitation for Aisha", kind="deadline",
                        due="2026-10-23", domain="logistics"))
    assert O.update_task(a, "done_with_followup", evidence="planned it").startswith("error:"), \
        "a loose end has to be named"
    out = O.update_task(a, "done_with_followup", evidence="the invite is written",
                        followup="Get Aisha's contact details")
    assert out.startswith(f"{a} done") and "Loose end tracked" in out, out
    assert _task(a)["status"] == "done"
    loose = [t for t in O._load() if t.get("source_id") == a]
    assert len(loose) == 1 and loose[0]["what"] == "Get Aisha's contact details", loose
    assert loose[0]["status"] == "open" and loose[0].get("domain") == "logistics"
    again = O.update_task(a, "done_with_followup", evidence="x", followup="y")
    assert "already" in again and len([t for t in O._load() if t.get("source_id") == a]) == 1


@check("an app drop carries its reason; the shipped app, which sends none, still works")
def _():
    _fresh("app_reason")
    _at(2026, 10, 24)
    a = _id(O.open_task("Post babysitter job", kind="deadline", due="2026-10-23"))
    b = _id(O.open_task("Book plumber", kind="deadline", due="2026-10-24"))
    assert O.act_from_app(a, "dismissed", reason="hired through a friend").startswith(f"{a} dismissed")
    assert _task(a)["evidence"] == "marked in the app: hired through a friend"
    assert O.act_from_app(b, "dismissed").startswith(f"{b} dismissed")
    assert _task(b)["evidence"] == "marked in the app"
    c = _id(O.open_task("Send invites", kind="deadline", due="2026-10-24"))
    assert "Loose end tracked" in O.act_from_app(c, "done_with_followup", followup="Chase RSVPs")


@check("a task carries how long it takes, stated or estimated, and shows it where it is listed")
def _():
    _fresh("minutes")
    _at(2026, 10, 24)
    gym = _id(O.open_task("Gym", kind="habit", every="day", minutes=60, minutes_source="stated"))
    tidy = _id(O.open_task("Tidy the garage", kind="deadline", due="2026-10-24", minutes=90))
    assert _task(tidy)["minutes_source"] == "estimated", "an unlabelled figure is a guess"
    block = O.context_block()
    assert "(~60 min)" in block and "(~90 min, estimated)" in block, block
    labels = {i["task_id"]: i["label"] for i in O.today_items()}
    assert labels[gym].endswith("(~60 min)"), labels
    # the user's figure outranks a model's guess; a stated correction replaces an estimate
    assert "keeps the user's own figure" in O.update_task(gym, "set_minutes", minutes=30)
    assert _task(gym)["minutes"] == 60
    assert O.update_task(tidy, "set_minutes", minutes=45, minutes_source="stated").startswith(tidy)
    assert _task(tidy)["minutes"] == 45 and _task(tidy)["minutes_source"] == "stated"
    for bad in (dict(minutes=0), dict(minutes="soon"), dict(minutes=10, minutes_source="vibes")):
        assert O.open_task("Bad", kind="deadline", **bad).startswith("error:"), bad
    assert O.update_task(tidy, "set_minutes").startswith("error:")


def _in_turn(text: str, prev: str = "", user_turn: bool = True):
    """Bind a pipeline turn the way run_pipeline_session_stream does, gate on."""
    from tools import turn_context as T
    cm = T.turn_scope(user_turn=user_turn)
    turn = cm.__enter__()
    turn.update(close_gate=True, user_text=text if user_turn else "", prev_assistant=prev)
    return cm


@check("the close gate: a model may close only what the user's words name (live check 4d)")
def _():
    _fresh("gate")
    _at(2026, 10, 24)
    schwab = _id(O.open_task("Review and allocate Charles Schwab Treasury note maturities",
                             kind="deadline", due="2026-10-26", domain="finance"))
    chase = _id(O.open_task("Pay Chase credit card bill", kind="habit", every="month",
                            domain="finance"))
    rowan = _id(O.open_task("Rowan monthly payroll transfer", kind="habit", every="month",
                            domain="finance"))
    plants = _id(O.open_task("Water indoor and garden plants", kind="interval",
                             interval_days=3, last_done="2026-10-21"))
    run = _id(O.open_task("Run 5k three times a week", kind="habit", every="week", times=3))
    food = _id(O.open_task("Buy plant food", kind="deadline", due="2026-10-30"))

    # The 15:01 message, verbatim: the plants close; the finance close is refused, with the
    # candidates named so the model can ask.
    cm = _in_turn("It's raining today, so consider the plants watered. I sorted the finance stuff.")
    try:
        r = O.update_task(schwab, "done", evidence="I sorted the finance stuff.")
        assert r.startswith("error: not recorded") and "Ask the user which" in r, r
        assert "Pay Chase credit card bill" in r, r
        assert _task(schwab)["status"] == "open"
        assert O.update_task(plants, "done", evidence="raining").startswith(plants)
        # "plants watered" names "Water … plants" better than "Buy plant food"
        assert O.update_task(food, "done", evidence="x").startswith("error:")
    finally:
        cm.__exit__(None, None, None)

    for text, target, ok in (
        ("paid the Chase bill", chase, True),
        ("went for a run this morning", run, True),
        ("I still haven't paid Chase", chase, False),
        ("remind me to do the Rowan transfer", rowan, False),
    ):
        _fresh("gate_" + text[:8].replace(" ", "_"))
        _at(2026, 10, 24)
        a = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-24"))
        b = _id(O.open_task("Rowan monthly payroll transfer", kind="deadline", due="2026-10-24"))
        c = _id(O.open_task("Run 5k three times a week", kind="habit", every="week", times=3))
        tid = {chase: a, rowan: b, run: c}[target]
        cm = _in_turn(text)
        try:
            r = O.update_task(tid, "done", evidence=text)
        finally:
            cm.__exit__(None, None, None)
        assert r.startswith("error:") != ok, (text, r)

    # a tie refuses both; "yes, both" after a reply that raised two closes both
    _fresh("gate_tie")
    _at(2026, 10, 24)
    d1 = _id(O.open_task("Pay Chase card statement", kind="deadline", due="2026-10-24"))
    d2 = _id(O.open_task("Claim Chase rewards", kind="deadline", due="2026-10-24"))
    cm = _in_turn("did the Chase thing")
    try:
        r = O.update_task(d1, "done", evidence="did the Chase thing")
        assert r.startswith("error:") and "more than one" in r, r
    finally:
        cm.__exit__(None, None, None)
    cm = _in_turn("yes, both", prev="Did you pay the Chase card statement and claim the Chase rewards?")
    try:
        assert O.update_task(d1, "done", evidence="yes, both").startswith(d1)
        assert O.update_task(d2, "done", evidence="yes, both").startswith(d2)
    finally:
        cm.__exit__(None, None, None)


@check("the close gate: scheduled turns cannot close; a tap or an approved card always can")
def _():
    _fresh("gate_sched")
    _at(2026, 10, 24)
    a = _id(O.open_task("Pay Chase credit card bill", kind="deadline", due="2026-10-24"))
    b = _id(O.open_task("Post babysitter job", kind="deadline", due="2026-10-24"))
    cm = _in_turn("Quiet check-in", user_turn=False)
    try:
        r = O.update_task(a, "done", evidence="the plan says so")
        assert r.startswith("error: not recorded") and "nothing from the user" in r, r
        # a tap during a bound turn (a leaked turn on a worker thread) is the user's act
        assert O.act_from_app(b, "done").startswith(b)
        # the non-closing actions are not gated
        assert O.update_task(a, "reschedule", new_due="2026-10-30", evidence="moved").startswith(a)
    finally:
        cm.__exit__(None, None, None)
    # no bound turn (the app endpoint, the CLI): ungated, as before
    assert O.update_task(a, "done", evidence="paid").startswith(a)


@check("list_tasks answers a span when asked: today, this week, this month")
def _():
    _fresh("horizon")
    _at(2026, 10, 24)
    soon = _id(O.open_task("Review Schwab maturities", kind="deadline", due="2026-10-26"))
    later = _id(O.open_task("Renew passport", kind="deadline", due="2026-11-20"))
    now = _id(O.open_task("Post babysitter job", kind="deadline", due="2026-10-23"))
    today = O.list_tasks(horizon="today")
    assert now in today and soon not in today and later not in today, today
    week = O.list_tasks(horizon="week")
    assert soon in week and later not in week, week
    assert later in O.list_tasks(horizon="month") and later in O.list_tasks()
    assert O.list_tasks(horizon="year").startswith("error:")


@check("the Today panel is the waking day: Mike's nine-row Saturday list becomes two")
def _():
    # The list Mike pasted on Saturday 2026-10-24 ("This is overwhelming"), rebuilt.
    _fresh("waking_day")
    _at(2026, 10, 24)
    job = _id(O.open_task("Post hybrid programmer/babysitter job", kind="deadline", due="2026-10-23"))
    _id(O.open_task("Review Schwab Treasury maturities", kind="deadline", due="2026-10-26"))
    stretch = _id(O.open_task("Stretching", kind="habit", every="day", times=2))
    gym = _id(O.open_task("Gym", kind="habit", every="week", times=3, on_days=["mon", "wed", "fri"]))
    _id(O.open_task("Pay Chase credit card bill", kind="habit", every="month", times=1))
    _id(O.open_task("Weekly grocery shop", kind="habit", every="week", times=1))
    _id(O.open_task("Check status on TfL refund", kind="deadline"))
    plants = _id(O.open_task("Water the plants", kind="interval", interval_days=3,
                             last_done="2026-10-23"))
    assert {i["task_id"] for i in O.today_items()} == {job, stretch}
    assert "needed today" not in O.context_block(), "a partial first week does not nag"
    _at(2026, 10, 26)   # Monday: a planned gym day, the plants due, Schwab due
    ids = {i["task_id"] for i in O.today_items()}
    assert {gym, plants, stretch, job} <= ids and len(ids) == 5, ids


# --- Adherence, counts, Accountability -------------------------------------------------------

@check("daily counts are content-free and Accountability sees closed work in its old shape")
def _():
    _fresh("counts")
    _at(2026, 10, 20)
    a = _id(O.open_task("Pay council tax", kind="deadline", due="2026-10-21"))
    g = _id(O.open_task("Gym", kind="habit", every="day"))
    O.update_task(a, "done", evidence="paid")
    O.update_task(g, "done", evidence="went")
    _at(2026, 10, 21, 0, 15)
    O.sweep()
    counts = O.daily_task_counts("2026-10-20")
    assert counts["tasks_done"] == 2 and counts["deadlines_met"] == 1, counts
    assert all(isinstance(v, int) for v in counts.values())
    items = O.accountability_items()
    assert {"what": "Pay council tax", "status": "closed"}.items() <= items[0].items() or any(
        i["what"] == "Pay council tax" for i in items)
    assert any(i["what"] == "Gym" and i["closed_at"].startswith("2026-10-20") for i in items), items


@check("the v1 tool names are gone — replaced outright, not kept as aliases")
def _():
    import core.actions as A
    for name in ("open_obligation", "close_obligation", "reopen_obligation", "list_obligations"):
        assert not hasattr(O, name), name
        assert name not in A.ACTION_TOOLS and name not in A.READ_TOOLS, name
    for name in ("open_task", "update_task"):
        assert name in A.ACTION_TOOLS, name
    assert "list_tasks" in A.READ_TOOLS


@check("the clock is the persona-local one tools/ambient shows the models")
def _():
    import importlib
    import tools.ambient as A
    real_now = O._now
    try:
        importlib.reload(O)  # restore the module's real _now for this check only
        orig = A._now_local
        A._now_local = lambda: datetime(2026, 10, 23, 23, 30)
        assert O._today() == date(2026, 10, 23)
        A._now_local = orig
    finally:
        O._now = real_now


def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
