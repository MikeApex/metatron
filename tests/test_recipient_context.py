"""
tests/test_recipient_context.py — what is on file about the people a Relationships turn names
(instructions-to-code Stage 4, 4c: #16, DECISION 4-3).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #12 test 13
(Stage 5's list, items 1–6). Offline: a temp persona tree, the FAISS search stubbed, no model, no
network. Generic names only.

    python3 tests/test_recipient_context.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")

import core.memory as MEM  # noqa: E402
import core.orchestrator as ORC  # noqa: E402
import core.prefetch as PF  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.data_objects as DO  # noqa: E402
import tools.recipient_context as RC  # noqa: E402
import tools.tone as TONE  # noqa: E402
import tools.wisdom as WIS  # noqa: E402
from support.stage3_fixtures import PERSONA, patched, sandbox  # noqa: E402

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


SAM = {"id": "c_sam", "name": "Sam Lee", "first_name": "Sam", "last_name": "Lee"}
NOW = datetime(2026, 11, 20, 10, 0)


def _seed(contacts):
    p = CRM._crm_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(contacts))


def _no_tone(*a, **k):
    raise AssertionError("get_tone_shape must never be called")


def _memory(hits):
    return lambda query, k=5: list(hits)


@check("1. a gift idea for Sam appears when the directive names Sam (the Relationships read rule "
       "binds, as for read_contact)")
def _():
    with sandbox():
        _seed([SAM])
        DO.archive_write(DO.get("gift_ideas"), {"title": "a climbing chalk bag", "for": "Sam"})
        with patched([(MEM, "search_memory", _memory([])), (TONE, "get_tone_shape", _no_tone)]):
            block = PF.build("relationships", "Draft a birthday message to Sam Lee.", "",
                             PERSONA, user_turn=False, now=NOW)
        assert RC.HEADING in block, block
        assert "climbing chalk bag" in block, block
        # The same entry the Relationships specialist would see through read_contact.
        with RC._as_agent("relationships"):
            assert [r["title"] for r in DO.entries_for_contact(SAM)] == ["a climbing chalk bag"]


@check("2. no hits, no block (nothing is appended)")
def _():
    with sandbox():
        _seed([SAM])
        with patched([(MEM, "search_memory", _memory([]))]):
            assert RC.on_file_block([SAM]) == ""
            block = PF.build("relationships", "Say hello to Sam Lee.", "", PERSONA, now=NOW)
        assert RC.HEADING not in block and '"id": "c_sam"' in block, block


@check("3. a memory hit without the name, literally, is dropped; one with it is kept")
def _():
    with sandbox():
        _seed([SAM])
        hits = [{"text": "Planning a surprise party for Sam in March", "date": "2026-11-01"},
                {"text": "Planning a surprise party in March", "date": "2026-11-02"},
                {"text": "Samantha's recital was lovely", "date": "2026-11-03"}]
        with patched([(MEM, "search_memory", _memory(hits))]):
            block = RC.on_file_block([SAM])
        assert "past entry (2026-11-01): Planning a surprise party for Sam in March" in block, block
        assert "2026-11-02" not in block and "recital" not in block, block


NAMES = ["Alder", "Birch", "Cedar", "Dahlia", "Elm"]


@check("4. the caps hold: 3 people, 6 lines each, 160 characters a line")
def _():
    with sandbox():
        people = [{"id": f"c{i}", "name": f"{n} Last", "first_name": n, "last_name": "Last"}
                  for i, n in enumerate(NAMES)]
        _seed(people)
        hits = [{"text": f"{n} note {j} " + "x" * 300} for n in NAMES for j in range(8)]

        def search(query, k=5):
            return [h for h in hits if h["text"].startswith(query.split()[0] + " ")][:k]
        with patched([(MEM, "search_memory", search), (RC, "MEMORY_HITS", 10),
                      (RC, "_MEMORY_K", 10)]):
            block = RC.on_file_block(people)
        heads = [ln for ln in block.splitlines()[1:] if ln.endswith("):")]
        assert len(heads) == 3, block
        assert all(len(ln) <= RC.LINE_CHARS + 2 for ln in block.splitlines()[1:]), block
        for n in NAMES[:3]:
            assert sum(1 for ln in block.splitlines()
                       if ln.startswith(f"- past entry: {n} ")) == RC.MAX_LINES, block


@check("4b. the cap is across ALL sources together: lists + tasks + facts + past entries → 6")
def _():
    import tools.obligations as O
    with sandbox():
        _seed([SAM])
        for i in range(2):
            DO.archive_write(DO.get("gift_ideas"), {"title": f"gift {i}", "for": "Sam"})
        O.open_task("Book a table for Sam Lee's birthday", kind="deadline", due="2026-12-01",
                    new_instance=True)
        O.open_task("Return the book Sam Lee lent me", kind="deadline", due="2026-12-02",
                    new_instance=True)
        WIS._wisdom_path().parent.mkdir(parents=True, exist_ok=True)
        WIS._wisdom_path().write_text(json.dumps([
            {"key": f"k{i}", "value": f"Sam Lee fact {i}", "domain": "relationships"}
            for i in range(2)]))
        hits = [{"text": f"Sam Lee memory {i}", "date": f"2026-11-0{i + 1}"} for i in range(3)]
        with patched([(MEM, "search_memory", _memory(hits))]):
            block = RC.on_file_block([SAM], contacts=[SAM])
        body = [ln for ln in block.splitlines() if ln.startswith("- ")]
        assert len(body) == RC.MAX_LINES, block
        assert sum(ln.startswith("- in your") for ln in body) == 2, block
        assert sum(ln.startswith("- open task: ") for ln in body) == 2, block
        assert sum(ln.startswith("- on file: ") for ln in body) == 2, block
        assert not any(ln.startswith("- past entry") for ln in body), "cut at the cap"


@check("5. a broken contacts file gives no block, and never fails the dispatch")
def _():
    with sandbox():
        p = CRM._crm_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json")
        with patched([(MEM, "search_memory", _memory([]))]):
            block = PF.build("relationships", "Message Sam Lee.", "", PERSONA, now=NOW)
        assert RC.HEADING not in block, block
        assert RC.on_file_block([{"no": "id"}]) == "" and RC.on_file_block(None) == ""
        with patched([(RC, "matcher", lambda c, cs: 1 / 0)]):
            assert RC.on_file_block([SAM], contacts=[SAM]) == ""


@check("6. the prefetch-is-None door (a run_subagent follow-up) carries the block")
def _():
    with sandbox():
        _seed([SAM])
        WIS._wisdom_path().parent.mkdir(parents=True, exist_ok=True)
        WIS._wisdom_path().write_text(json.dumps([
            {"key": "sam_surprise", "value": "Sam's 40th is a surprise party on 12 March",
             "domain": "relationships"}]))
        seen = {}

        def fake_openai(system_prompt, user_input, tool_schemas, tool_handlers, **kw):
            seen["input"] = user_input
            seen["system"] = system_prompt
            return "ok"
        with patched([(MEM, "search_memory", _memory([])), (ORC, "run_session_openai",
                                                            fake_openai)]):
            ORC._run_single_agent("relationships", "Help draft a note to Sam Lee about March.",
                                  persona=PERSONA, provider="openai")
        assert RC.HEADING in seen["input"], seen["input"][:2000]
        assert "Sam's 40th is a surprise party" in seen["input"]
        assert RC.HEADING not in seen["system"], "in the USER message, never the system prompt"


SAM2 = {"id": "c_sam2", "name": "Sam Ortiz", "first_name": "Sam", "last_name": "Ortiz"}


@check("8. two Sams: a fact saying only 'Sam' is attributed to neither; 'Sam Lee' (either "
       "order) to Sam Lee only")
def _():
    with sandbox():
        _seed([SAM, SAM2])
        WIS._wisdom_path().parent.mkdir(parents=True, exist_ok=True)
        WIS._wisdom_path().write_text(json.dumps([
            {"key": "a", "value": "Sam loves jazz", "domain": "relationships"},
            {"key": "b", "value": "Sam Lee is planning a surprise", "domain": "relationships"},
            {"key": "c", "value": "Lee Sam prefers calls", "domain": "relationships"}]))
        hits = [{"text": "Sam said the surprise is on", "date": "2026-11-01"}]
        with patched([(MEM, "search_memory", _memory(hits))]):
            block = RC.on_file_block([SAM, SAM2], contacts=[SAM, SAM2])
        assert "Sam Lee is planning a surprise" in block and "Lee Sam prefers calls" in block
        assert "jazz" not in block and "surprise is on" not in block, block
        assert "c_sam2" not in block, block


WILL = {"id": "c_will", "name": "Will Turner", "first_name": "Will", "last_name": "Turner"}
BIRCH = {"id": "c_birch", "name": "Birch Moss", "first_name": "Birch", "last_name": "Moss"}


@check("9. a contact named Will: facts containing 'will' or a lone 'Will' are not about him; "
       "'Will Turner' is; another domain needs the full name")
def _():
    with sandbox():
        _seed([WILL, BIRCH])
        WIS._wisdom_path().parent.mkdir(parents=True, exist_ok=True)
        WIS._wisdom_path().write_text(json.dumps([
            {"key": "a", "value": "The user will travel in May", "domain": "relationships"},
            {"key": "b", "value": "Will said the plan is fine", "domain": "relationships"},
            {"key": "c", "value": "Will Turner's party is a surprise", "domain": "relationships"},
            {"key": "d", "value": "Birch is allergic to nuts", "domain": "food"},
            {"key": "e", "value": "Birch likes handwritten cards", "domain": "relationships"}]))
        with patched([(MEM, "search_memory", _memory([]))]):
            block = RC.on_file_block([WILL, BIRCH], contacts=[WILL, BIRCH])
        assert "Will Turner's party is a surprise" in block, block
        assert "travel in May" not in block and "plan is fine" not in block, block
        assert "handwritten cards" in block and "allergic" not in block, block


@check("10. _task_lines: open tasks naming the person, wording and due date only — never a "
       "medication link or other fields")
def _():
    import tools.obligations as O
    with sandbox():
        _seed([SAM, SAM2])
        O.open_task("Buy flowers for Sam Lee", kind="deadline", due="2026-12-05",
                    new_instance=True)
        O.open_task("Call Sam about the trip", kind="deadline", due="2026-12-06",
                    new_instance=True)
        O.open_task("Renew the car insurance", kind="deadline", due="2026-12-07",
                    new_instance=True)
        doc = O._load_doc()
        for t in doc.get("tasks", []):
            if t.get("what") == "Buy flowers for Sam Lee":
                t["medication"] = "a medicine name"
                t["notes"] = "private note"
        O._save_doc(doc)
        by_rule, _ = RC.matcher(SAM, [SAM, SAM2])
        lines = RC._task_lines(by_rule)
        assert lines == ["open task: Buy flowers for Sam Lee (due 2026-12-05)"], lines


@check("11. a slow past-entry search never costs the records; the block waits ≤1.5 s for it")
def _():
    import time as _time
    with sandbox():
        _seed([SAM])

        def slow(query, k=5):
            _time.sleep(5)
            return [{"text": "Sam Lee late hit"}]
        with patched([(MEM, "search_memory", slow)]):
            t0 = _time.monotonic()
            block = PF.build("relationships", "Draft a note to Sam Lee.", "", PERSONA, now=NOW)
            took = _time.monotonic() - t0
        assert '"id": "c_sam"' in block and "overdue for contact" in block, block
        assert "late hit" not in block and took < 3.0, (took, block)


JL = {"id": "c_jl", "name": "Jordan Lee", "first_name": "Jordan", "last_name": "Lee"}
MJ = {"id": "c_mj", "name": "Michael Jordan", "first_name": "Michael", "last_name": "Jordan"}


@check("12. another contact's surname makes a first name not unique, and a hit inside another "
       "contact's full name is not about this one ('Call Michael Jordan …' ≠ Jordan Lee)")
def _():
    import tools.obligations as O
    with sandbox():
        _seed([JL, MJ])
        O.open_task("Call Michael Jordan about the surprise party", kind="deadline",
                    due="2026-12-01", new_instance=True)
        by_rule, _ = RC.matcher(JL, [JL, MJ])
        assert not by_rule("Call Michael Jordan about the surprise party")
        assert by_rule("Jordan Lee's surprise party")
        with patched([(MEM, "search_memory", _memory([]))]):
            block = RC.on_file_block([JL], contacts=[JL, MJ])
        assert "surprise party" not in block, block
        # Beside a capitalised word not on the record, even when the first name is unique.
        solo = {"id": "c_b", "name": "Birch Moss", "first_name": "Birch", "last_name": "Moss"}
        by_rule, _ = RC.matcher(solo, [solo])
        assert by_rule("Birch said yes") and not by_rule("Ask Birch Wood about it")


@check("13. unlinked list entries follow the only-this-person rule: a bare 'Sam' with two Sams "
       "is neither's; 'Sam Lee' is Sam Lee's; a linked entry stays with its contact")
def _():
    rows = [{"title": "chalk bag", "for": "Sam"}, {"title": "scarf", "for": "sam lee"},
            {"title": "book", "for": "Sam", "for_contact": "c_sam2"}]
    obj = {"id": "gifts", "name": "Gift ideas", "store": "archive", "status": "active",
           "fields": {"for": {}}}
    with sandbox(), patched([(DO, "objects", lambda: [obj]), (DO, "_rows", lambda oid: rows),
                             (DO, "may_read", lambda agent, o: (True, ""))]):
        by = lambda c, cs: RC.matcher(c, cs)[0]  # noqa: E731
        got = [r["title"] for r in RC._list_rows(SAM, "relationships", by(SAM, [SAM, SAM2]))]
        assert got == ["scarf"], got
        got = [r["title"] for r in RC._list_rows(SAM2, "relationships", by(SAM2, [SAM, SAM2]))]
        assert got == ["book"], got
        got = [r["title"] for r in RC._list_rows(SAM, "relationships", by(SAM, [SAM]))]
        assert got == ["chalk bag", "scarf"], got


@check("14. the people records are their own prefetch read: emitted even when the on-file "
       "read runs out of time")
def _():
    import time as _time
    with sandbox():
        _seed([SAM])
        cfg = dict(PF.load_config())
        cfg["read_timeout_s"] = 1
        with patched([(PF, "load_config", lambda: cfg),
                      (RC, "on_file_block", lambda *a, **k: _time.sleep(4) or "late")]):
            t0 = _time.monotonic()
            block = PF.build("relationships", "Draft a note to Sam Lee.", "", PERSONA, now=NOW)
            took = _time.monotonic() - t0
        assert '"id": "c_sam"' in block and "overdue for contact" in block, block
        assert "(not read in advance: call `read_contact`)" in block and "late" not in block
        assert took < 2.5, took


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
