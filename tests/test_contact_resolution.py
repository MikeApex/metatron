"""
tests/test_contact_resolution.py — the people a Relationships dispatch names, matched exactly by
code (instructions-to-code Stage 4, 4c: #12, M2, M3) and the NEWLY SAVED read-back line (M1).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #12 tests 1–12
and 14 (13 is tests/test_recipient_context.py), § 1 M1 tests 1–5. Offline: a temp persona tree
(tests/support/stage3_fixtures.sandbox), every model entry point scripted, no network. Generic
names only.

    python3 tests/test_contact_resolution.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.orchestrator as ORC  # noqa: E402
import core.prefetch as PF  # noqa: E402
import core.trace as TR  # noqa: E402
import tools.contact_resolution as CR  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.recipient_context as RC  # noqa: E402
import tools.tone as TONE  # noqa: E402
from support.stage3_fixtures import (PERSONA, Script, collect_stream,  # noqa: E402
                                     coordinator_package, patched, pipeline, sandbox)
from tools import turn_context as T  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return wrap


def _c(cid, name, first="", last="", **kw):
    return {"id": cid, "name": name, "first_name": first, "last_name": last, **kw}


CONTACTS = [
    _c("c_will", "Will Turner", "Will", "Turner", contact_frequency_preference="weekly",
       last_contact="2026-11-01"),
    _c("c_mark", "Mark Ellis", "Mark", "Ellis"),
    _c("c_bill", "Bill Grant", "Bill", "Grant"),
    _c("c_rose", "Rose Patel", "Rose", "Patel", important_dates=[{"label": "birthday",
                                                                   "date": "12-30"}]),
    _c("c_anna", "Anna Turner", "Anna", "Turner"),
    _c("c_jon", "Jonathan Hale", "Jonathan", "Hale"),
    _c("c_bex", "Rebecca Moss", "Rebecca", "Moss", nickname="Bex"),
    _c("c_tom", "Tom Reyes", "Tom", "Reyes", referred_to_as=["my brother"]),
    _c("c_sam1", "Sam Lee", "Sam", "Lee", occupation="nurse"),
    _c("c_sam2", "Sam Ortiz", "Sam", "Ortiz", occupation="plumber"),
]


def _seed(contacts=None):
    path = CRM._crm_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(CONTACTS if contacts is None else contacts))


def _ids(texts, contacts=None):
    got = CR.resolve(texts if isinstance(texts, list) else [texts], contacts)
    return [c["id"] for c in got["resolved"]], got


# --- 1–5: who resolves ------------------------------------------------------------------------

@check("1. exact match on a full name (any case), a mid-sentence first name, a nickname and a "
       "referred_to_as phrase")
def _():
    with sandbox():
        _seed()
        assert _ids("I bumped into rose patel at the shop")[0] == ["c_rose"]
        assert _ids("Tonight I should call Mark about the trip")[0] == ["c_mark"]
        assert _ids("We had lunch and Bex was there")[0] == ["c_bex"]
        assert _ids("Apparently my brother is coming over")[0] == ["c_tom"]


@check("2. two tokens resolve at sentence start ('Will Turner called'); a lone first name at "
       "sentence start does not")
def _():
    with sandbox():
        _seed()
        assert _ids("Will Turner called this morning")[0] == ["c_will"]
        assert _ids("Mark called this morning")[0] == []
        assert _ids("It rained. Mark called after")[0] == []


@check("3. common-word names: Will/Mark/Bill/Rose never resolve from ordinary words; they do "
       "from 'call Will tomorrow' and 'ask Mark about it'")
def _():
    with sandbox():
        _seed()
        for text in ("Will it rain", "I will call later", "please mark the date",
                     "I need to pay the bill", "we planted a rose bush"):
            ids, got = _ids(text)
            assert ids == [] and not got["ambiguous"] and not got["prefix"], (text, got)
        assert _ids("I need to call Will tomorrow")[0] == ["c_will"]
        assert _ids("I should ask Mark about it")[0] == ["c_mark"]


@check("4. a shared surname alone resolves no one ('the Turners', 'ask Turner')")
def _():
    with sandbox():
        _seed()
        for text in ("we are seeing the Turners", "I should ask Turner first"):
            ids, got = _ids(text)
            assert ids == [] and not got["ambiguous"], (text, got)


@check("5. a non-name capital ('Tomorrow') is not a candidate")
def _():
    with sandbox():
        _seed()
        ids, got = _ids("Remind me about it, Tomorrow is busy and Friday too")
        assert ids == [] and not got["ambiguous"] and not got["prefix"], got


# --- 6–8: many, prefixes, merges --------------------------------------------------------------

@check("6. multi-match: the remembered answer is used when present; otherwise ask-which, capped")
def _():
    with sandbox():
        _seed()
        ids, got = _ids("I want to text Sam later")
        assert ids == [] and got["ambiguous"][0][0] == "Sam", got
        assert {c["id"] for c in got["ambiguous"][0][1]} == {"c_sam1", "c_sam2"}
        block, _, _ = CR.people_block("I want to text Sam later", "", date(2026, 11, 20))
        assert "Sam matches 2 contacts — ask which:" in block, block
        assert '"occupation": "plumber"' in block and '"occupation": "nurse"' in block
        assert CRM._record_resolution("Sam", "c_sam2", "test")
        assert _ids("I want to text Sam later")[0] == ["c_sam2"]
    with sandbox():
        many = [_c(f"c_s{i}", f"Sam Name{i}", "Sam", f"Name{i}") for i in range(7)]
        _seed(many)
        block, _, _ = CR.people_block("then text Sam", "", date(2026, 11, 20))
        rows = [ln for ln in block.splitlines() if ln.startswith('{"id": "c_s')]
        assert len(rows) == CR.MAX_ASK_WHICH == 5, block
        assert "(+2 more)" in block and "Sam matches 7 contacts" in block


@check("7. a name prefix is offered but never resolved; a 2-letter prefix is refused")
def _():
    with sandbox():
        _seed()
        ids, got = _ids("I need to talk to Jon about it")
        assert ids == [] and [c["id"] for _, c in got["prefix"]] == ["c_jon"], got
        block, _, _ = CR.people_block("I need to talk to Jon about it", "", date(2026, 11, 20))
        assert ('possibly Jonathan Hale (c_jon) for "Jon" (name prefix): read the record before '
                'writing a new contact') in block, block
        ids, got = _ids("I need to talk to Jo about it")
        assert ids == [] and got["prefix"] == [], got


@check("8. a merged-away name follows merged_into to the surviving record")
def _():
    with sandbox():
        _seed()
        arch = CRM._crm_archive_dir()
        arch.mkdir(parents=True, exist_ok=True)
        (arch / "c_old_20261101T000000.json").write_text(json.dumps(
            _c("c_old", "Ida Grey", "Ida", "Grey", merged_into="c_rose")))
        assert _ids("Yesterday I met Ida at the park")[0] == ["c_rose"]
        assert _ids("ida grey sent a card")[0] == ["c_rose"]


# --- 9–10: overdue and dates ------------------------------------------------------------------

@check("9. the overdue list: most overdue first, capped at 8 with the remainder counted")
def _():
    with sandbox():
        people = [_c(f"c_o{i}", f"Person{i} Last", f"Person{i}", "Last",
                     contact_frequency_preference="weekly",
                     last_contact=f"2026-10-{10 + i:02d}") for i in range(10)]
        _seed(people + [_c("c_fresh", "Fresh Face", "Fresh", "Face",
                           contact_frequency_preference="monthly",
                           last_contact=date.today().isoformat())])
        lines = CR.overdue_lines(date.today())
        assert len(lines) == 9 and lines[-1].startswith("- (+2 more"), lines
        assert lines[0].startswith("- Person0 Last · c_o0 · 2026-10-10 · "), lines
        assert lines[7].startswith("- Person7 Last"), lines
        assert not any("Fresh" in x for x in lines)


@check("10. M3 date window: 12-30 seen from 12-20, 01-03 seen across the year end, 29 Feb on "
       "28 Feb in a non-leap year, a YYYY-MM-DD not yet reached is not due")
def _():
    people = [_c("a", "Rose Patel", "Rose", "Patel",
                 important_dates=[{"label": "birthday", "date": "12-30"}]),
              _c("b", "Ana Ruiz", "Ana", "Ruiz",
                 important_dates=[{"label": "anniversary", "date": "2015-01-03"}]),
              _c("c", "Leap Kid", "Leap", "Kid",
                 important_dates=[{"label": "birthday", "date": "02-29"}]),
              _c("d", "Far Off", "Far", "Off",
                 important_dates=[{"label": "wedding", "date": "2030-01-02"}])]
    lines = CR.upcoming_lines(people, date(2026, 12, 20), 14)
    assert lines[0] == "- Rose Patel · a · birthday · 2026-12-30 (in 10 days)", lines
    assert lines[1] == "- Ana Ruiz · b · anniversary · 2027-01-03 (in 14 days)", lines
    assert len(lines) == 2, lines                      # Far Off's 2030 date is not due yet
    leap = CR.upcoming_lines(people, date(2027, 2, 20), 14)
    assert leap == ["- Leap Kid · c · birthday · 2027-02-28 (in 8 days)"], leap
    assert CR.upcoming_lines(people, date(2028, 2, 20), 14) == [
        "- Leap Kid · c · birthday · 2028-02-29 (in 9 days)"]


# --- 11–12: tone shape ------------------------------------------------------------------------

def _no_tone(*a, **k):
    raise AssertionError("get_tone_shape must never be called from prefetch")


@check("11. M2: the STORED tone shape only; get_tone_shape is never called")
def _():
    with sandbox():
        people = [dict(CONTACTS[0], tone_shape="warm, short, first names"), CONTACTS[1]]
        _seed(people)
        with patched([(CRM, "_tone_profiles_permitted", lambda: True),
                      (TONE, "get_tone_shape", _no_tone)]):
            block, _, resolved = CR.people_block("Then call Will and ask Mark too", "",
                                                 date(2026, 11, 20))
        recs = [json.loads(ln) for ln in block.splitlines() if ln.startswith('{"id"')]
        by = {r["id"]: r for r in recs}
        assert by["c_will"]["tone_shape"] == "warm, short, first names", by
        assert by["c_mark"]["tone_shape"].startswith("none stored; call `get_tone_shape`"), by
        assert [c["id"] for c in resolved] == ["c_will", "c_mark"]


@check("12. not_permitted: no tone shape and no tone line at all")
def _():
    with sandbox():
        _seed([dict(CONTACTS[0], tone_shape="warm, short")])
        with patched([(CRM, "_tone_profiles_permitted", lambda: False),
                      (TONE, "get_tone_shape", _no_tone)]):
            block, _, _ = CR.people_block("Then call Will", "", date(2026, 11, 20))
        assert "c_will" in block and "tone" not in block, block


@check("12b. the handed-over record is compact: notes cut at 300, last 3 interactions only")
def _():
    log = [{"date": f"2026-11-0{i}", "summary": f"talk {i}"} for i in range(1, 7)]
    rec = CR.project(dict(CONTACTS[0], notes="x" * 900, interaction_log=log,
                          tone_shape="secret"), permitted=False)
    assert len(rec["notes"]) == 301 and rec["recent_interactions"] == log[-3:], rec
    assert "tone_shape" not in rec and "interaction_log" not in rec


# --- 14: the prefetch read, and the user's words ----------------------------------------------

@check("14. the people read through prefetch: names from the directive always, the user's words "
       "only on a real user turn")
def _():
    with sandbox():
        _seed()
        with patched([(RC, "_memory_lines", lambda c, n: []),
                      (TONE, "get_tone_shape", _no_tone)]):
            plan = [e["read"] for e in PF.plan_for("relationships")]
            assert "people" in plan, plan
            now = datetime(2026, 11, 20, 10, 0)
            off = PF.build("relationships", "Help with a message.", "I want to call Will tonight",
                           PERSONA, user_turn=False, now=now)
            on = PF.build("relationships", "Help with a message.", "I want to call Will tonight",
                          PERSONA, user_turn=True, now=now)
            directive = PF.build("relationships", "Help the user call Will tonight.", "",
                                 PERSONA, user_turn=False, now=now)
        assert "### people named here" in off and '"c_will"' not in off, off
        assert '"id": "c_will"' in on, on
        assert '"id": "c_will"' in directive, directive


# --- M1: the read-back line -------------------------------------------------------------------

def _trace_with(calls: list[tuple[str, dict, str, bool]]):
    t = TR.RequestTrace("u", PERSONA)
    rec = TR.AgentRecord(agent="relationships", provider="", model="")
    for name, args, result, ok in calls:
        TR.record_tool_call(rec, 1, name, args, result, 1.0, ok=ok)
    return t, rec


@check("M1.1 a new contact: every detail its write received is listed")
def _():
    with sandbox():
        _seed()
        t, rec = _trace_with([("write_contact",
                               {"name": "Kate Lowe", "first_name": "Kate", "last_name": "Lowe",
                                "contact_info": {
                                   "email": "kate@mail.test", "phone": "020 7946 0000"}},
                               "c_new", True)])
        CR.take_snapshot(t, True, True)
        t.pipeline.append(rec)
        block = CR.readback_block(t, True)
        assert block.startswith(CR.READBACK_HEADING), block
        assert "- new contact Kate Lowe" in block, block
        assert "Kate Lowe — email: kate@mail.test" in block
        assert "Kate Lowe — phone: 020 7946 0000" in block
        assert "— name:" not in block, "first/last names inside the full name are said once"


@check("M1.2 an existing contact: an unchanged email is not listed, a new phone is")
def _():
    with sandbox():
        _seed([dict(CONTACTS[1], contact_info={"email": "mark@mail.test", "phone": "111"})])
        t, rec = _trace_with([("write_contact",
                               {"name": "Mark Ellis", "contact_id": "c_mark", "contact_info": {
                                   "email": "MARK@mail.test", "phone": "0161 496 0999"}},
                               "c_mark", True)])
        CR.take_snapshot(t, True, False)
        t.pipeline.append(rec)
        block = CR.readback_block(t, True)
        assert "— email" not in block and "Mark Ellis — phone: 0161 496 0999" in block, block
        assert "new contact" not in block and "Mark Ellis — name" not in block, block


@check("M1.3 a failed, refused or still-to-confirm write is not listed")
def _():
    with sandbox():
        _seed()
        pending = json.dumps({"status": "PENDING_CONFIRMATION", "token": "x"})
        t, rec = _trace_with([
            ("write_contact", {"name": "Ann One", "contact_info": {"email": "a@mail.test"}},
             "Error: not saved. placeholder", False),
            ("write_contact", {"name": "Ann Two", "contact_info": {"email": "b@mail.test"}},
             pending, True),
            ("write_profile", {"field": "email", "value": "me@mail.test"}, pending, True),
            ("write_profile", {"field": "phone", "value": "07700 900111"},
             "Error: not changed.", False)])
        CR.take_snapshot(t, True, True)
        t.pipeline.append(rec)
        assert CR.readback_block(t, True) == ""


@check("M1.3b a new profile detail is listed; an unchanged one is not")
def _():
    with sandbox() as sb:
        import yaml
        (sb["config"] / "profile.yaml").write_text(yaml.safe_dump(
            {"contact": {"email": "me@mail.test"}}))
        t, rec = _trace_with([
            ("write_profile", {"field": "email", "value": "me@mail.test"},
             "Profile updated: contact.email", True),
            ("write_profile", {"field": "address", "value": "1 High Street, AB1 2CD"},
             "Profile updated: contact.address", True)])
        CR.take_snapshot(t, False, True)
        t.pipeline.append(rec)
        block = CR.readback_block(t, True)
        assert "the user's own address: 1 High Street, AB1 2CD" in block, block
        assert "own email" not in block, block


@check("M1.4 a turn with no user words produces nothing")
def _():
    with sandbox():
        _seed()
        t, rec = _trace_with([("write_contact", {"name": "Kate Lowe"}, "c_new", True)])
        CR.take_snapshot(t, True, True)
        t.pipeline.append(rec)
        assert CR.readback_block(t, False) == ""
        assert CR.readback_block(t, True) != ""


def _relationships_writes():
    TR.record_tool_call(TR.get_current_agent(), 1, "write_contact",
                        {"name": "Kate Lowe", "contact_info": {"email": "kate@mail.test"}},
                        "c_new", 1.0, ok=True)


@check("M1.5 both pipeline twins carry the NEWLY SAVED line into the Synthesizer's input")
def _():
    for stream in (False, True):
        with sandbox():
            _seed()
            spec = {"agent": "relationships", "directive": "Save Kate's email."}
            s = Script({"coordinator": coordinator_package([spec]),
                        "relationships": "Saved Kate."},
                       side_effects={"relationships": _relationships_writes},
                       synth_reply="Got it.")
            with patched([(RC, "_memory_lines", lambda c, n: []),
                          (TONE, "get_tone_shape", _no_tone)]), pipeline(s):
                text = "Kate's email is kate@mail.test, save her please"
                if stream:
                    collect_stream(ORC.run_pipeline_session_stream(text, persona=PERSONA,
                                                                   provider="openai"))
                else:
                    ORC.run_pipeline_session(text, persona=PERSONA, provider="openai")
            synth = s.last("synthesizer")
            assert CR.READBACK_HEADING in synth, (stream, synth[-800:])
            assert "Kate Lowe — email: kate@mail.test" in synth, (stream, synth[-800:])
            # The Relationships dispatch got its people block (prefetch, in the user message).
            assert "### people named here" in s.last("relationships"), s.last("relationships")


@check("R1. names come from the Coordinator's own directive and the user's words — never from a "
       "block code appended (knowledge, PROACTIVE_FLAGS)")
def _():
    with sandbox():
        _seed()
        spec = {"agent": "relationships", "directive": "Help the user call Will Turner."}
        coord = coordinator_package([spec]) + "\nPROACTIVE_FLAGS:\n- Rose Patel seemed low\n"
        s = Script({"relationships": "ok"})
        with patched([(RC, "_memory_lines", lambda c, n: []),
                      (ORC, "_knowledge_block", lambda *a, **k: "KNOWN: Mark Ellis plays golf")]), \
                pipeline(s), T.turn_scope(user_turn=True):
            ORC._dispatch_from_coordinator(coord, persona=PERSONA, provider="openai",
                                           knowledge=[{"key": "k"}], user_turn=True,
                                           user_text="Can you help me with a call")
        got = s.last("relationships")
        assert "KNOWN: Mark Ellis plays golf" in got, "the appended block still reaches it"
        assert '"id": "c_will"' in got, got
        assert '"id": "c_mark"' not in got and '"id": "c_rose"' not in got, got


@check("R3. a contact saved by full name only ('Sam Hale', no first_name) counts as a Sam: "
       "'Sam' then asks which")
def _():
    with sandbox():
        people = [_c("c_a", "Sam Lee", "Sam", "Lee"), {"id": "c_h", "name": "Sam Hale"}]
        _seed(people)
        ids, got = _ids("I need to ask Sam today")
        assert ids == [] and {c["id"] for c in got["ambiguous"][0][1]} == {"c_a", "c_h"}, got
        assert _ids("Then ask Sam Hale today")[0] == ["c_h"]


@check("R9. a two-word name never matches across punctuation ('Sam, Lee and Jo')")
def _():
    phrases, _ = CR._index([_c("c_sl", "Sam Lee", "Sam", "Lee")])
    for text in ("invite Sam, Lee and Jo", "ask Sam. Lee will come", "Sam; Lee"):
        hits, _ = CR._two_token_hits(text, phrases)
        assert hits == [], (text, hits)
    hits, _ = CR._two_token_hits("invite Sam Lee and Jo", phrases)
    assert [w for w, _ in hits] == ["Sam Lee"], hits


@check("R7. M1: a contact created then enriched in one turn is read back once; phones compare "
       "by crm._normalize_phone_digits")
def _():
    with sandbox():
        _seed([dict(CONTACTS[1], contact_info={"phone": "020 7946 0000"})])
        t, rec = _trace_with([
            ("write_contact", {"name": "Kate Lowe", "contact_info": {"email": "kate@mail.test"}},
             "c_new", True),
            ("write_contact", {"contact_id": "c_new", "name": "Kate Lowe", "contact_info": {
                "email": "kate@mail.test", "phone": "07700 900 555"}}, "c_new", True),
            ("write_contact", {"contact_id": "c_mark", "contact_info": {
                "phone": "(020) 7946-0000"}}, "c_mark", True)])
        CR.take_snapshot(t, True, False)
        t.pipeline.append(rec)
        block = CR.readback_block(t, True)
        items = [ln for ln in block.splitlines() if ln.startswith("- ")]
        assert items == ["- new contact Kate Lowe", "- Kate Lowe — email: kate@mail.test",
                         "- Kate Lowe — phone: 07700 900 555"], items


@check("S1. a lone name beside someone else's capitalised name is not resolved, only offered "
       "('Sam Peters', 'Michael Jordan'); 'Sam said' and 'Yesterday Sam called' resolve; a "
       "name-only record's first word never resolves alone ('the City council')")
def _():
    with sandbox():
        people = [_c("c_hale", "Sam Hale", "Sam", "Hale"), _c("c_jl", "Jordan Lee", "Jordan", "Lee"),
                  {"id": "c_city", "name": "City Dental"}]
        _seed(people)
        ids, got = _ids("I had lunch with Sam Peters today")
        assert ids == [] and [(w, c["id"]) for w, c in got["possibly"]] == [
            ("Sam Peters", "c_hale")], got
        block, _, _ = CR.people_block("I had lunch with Sam Peters today", "", date(2026, 11, 20))
        assert 'possibly Sam Hale (c_hale)? "Sam Peters" may be someone else' in block, block
        ids, got = _ids("We watched Michael Jordan highlights")
        assert ids == [] and [c["id"] for _, c in got["possibly"]] == ["c_jl"], got
        assert _ids("Then Sam said hello")[0] == ["c_hale"]
        assert _ids("Yesterday Sam called me")[0] == ["c_hale"]
        assert _ids("Sam Hale and Sam Peters came")[0] == ["c_hale"], "the full name still does"
        ids, got = _ids("I wrote to the City council")
        assert ids == [] and [c["id"] for _, c in got["possibly"]] == ["c_city"], got
        assert _ids("I booked the City Dental check-up")[0] == ["c_city"]


@check("S3. two specs for one agent each resolve from their own directive; a fire-and-forget "
       "Relationships resolves from the Coordinator's directive, not code-appended blocks")
def _():
    import threading
    with sandbox():
        _seed()
        specs = [{"agent": "relationships", "directive": "Help call Will Turner."},
                 {"agent": "relationships", "directive": "Help text Mark Ellis."}]
        s = Script({"relationships": "ok"})
        with patched([(RC, "_memory_lines", lambda c, n: [])]), pipeline(s), \
                T.turn_scope(user_turn=True):
            ORC._dispatch_from_coordinator(coordinator_package(specs), persona=PERSONA,
                                           provider="openai", user_turn=True, user_text="")
        ins = s.inputs.get("relationships") or []
        assert len(ins) == 2, len(ins)
        will = [x for x in ins if "Help call Will Turner." in x][0]
        mark = [x for x in ins if "Help text Mark Ellis." in x][0]
        assert '"id": "c_will"' in will and '"id": "c_mark"' not in will, will[:1500]
        assert '"id": "c_mark"' in mark and '"id": "c_will"' not in mark, mark[:1500]

        seen, done = {}, threading.Event()

        def fake_run_session(agent, user_input="", **kw):
            seen.update(agent=agent, user_input=user_input, prefetch=kw.get("prefetch"))
            done.set()
            return ""
        spec = [{"agent": "relationships", "directive": "Help call Will Turner.",
                 "fire_and_forget": True}]
        with patched([(RC, "_memory_lines", lambda c, n: []),
                      (ORC, "_knowledge_block", lambda *a, **k: "KNOWN: Mark Ellis plays golf"),
                      (ORC, "run_session", fake_run_session)]), pipeline(Script({})):
            ORC._dispatch_from_coordinator(coordinator_package(spec), persona=PERSONA,
                                           provider="openai", knowledge=[{"key": "k"}],
                                           user_turn=True, user_text="")
            assert done.wait(10), "the fire-and-forget thread never ran"
        assert "KNOWN: Mark Ellis plays golf" in seen["user_input"], seen
        assert '"id": "c_will"' in (seen["prefetch"] or ""), seen["prefetch"]
        assert '"id": "c_mark"' not in (seen["prefetch"] or ""), seen["prefetch"]


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
