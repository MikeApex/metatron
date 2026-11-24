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


@check("4. the caps hold: 3 people, 6 lines each, 160 characters a line")
def _():
    with sandbox():
        people = [{"id": f"c{i}", "name": f"Person{i} Last", "first_name": f"Person{i}"}
                  for i in range(5)]
        _seed(people)
        hits = [{"text": f"Person{i} note {j} " + "x" * 300} for i in range(5) for j in range(8)]

        def search(query, k=5):
            return [h for h in hits if h["text"].startswith(query.split()[0] + " ")][:k]
        with patched([(MEM, "search_memory", search), (RC, "MEMORY_HITS", 10),
                      (RC, "_MEMORY_K", 10)]):
            block = RC.on_file_block(people)
        heads = [ln for ln in block.splitlines()[1:] if ln.endswith("):")]
        assert len(heads) == 3, block
        assert all(len(ln) <= RC.LINE_CHARS + 2 for ln in block.splitlines()[1:]), block
        for i in range(3):
            assert sum(1 for ln in block.splitlines()
                       if ln.startswith(f"- past entry: Person{i} ")) == RC.MAX_LINES, block


@check("5. a broken contacts file gives \"\" (and never fails the dispatch)")
def _():
    with sandbox():
        p = CRM._crm_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("{not json")
        with patched([(MEM, "search_memory", _memory([]))]):
            block = PF.build("relationships", "Message Sam Lee.", "", PERSONA, now=NOW)
        assert RC.HEADING not in block, block
        assert RC.on_file_block([{"no": "id"}]) == "" and RC.on_file_block(None) == ""
        with patched([(RC, "_names", lambda c: 1 / 0)]):
            assert RC.on_file_block([SAM]) == ""


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


@check("7. a source the agent is not granted is never read (list_tasks for Relationships)")
def _():
    with sandbox():
        _seed([SAM])
        called = []
        with patched([(MEM, "search_memory", _memory([])),
                      (RC, "_task_lines", lambda c, n: called.append(1) or ["open task t1: x"])]):
            RC.on_file_block([SAM], "relationships")
        from core.router import get_allowed_tools
        if "list_tasks" not in (get_allowed_tools("relationships") or []):
            assert called == [], "list_tasks is not granted to Relationships — never read"


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
