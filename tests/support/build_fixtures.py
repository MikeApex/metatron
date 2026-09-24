"""
tests/support/build_fixtures.py — valid Build artifacts, one place.

THE METHOD EVERY BUILD SUITE USES: start from a VALID artifact, introduce
EXACTLY ONE defect, assert that defect is reported. Asserting on a hand-built
broken artifact proves much less — a validator that rejected everything would
pass that version of the test.

Which is why these live in one module rather than in each suite. Six suites
each with their own idea of "a valid plan" is six chances for one of them to
drift into being valid only against the check it is paired with, and the drift
is invisible: every suite still passes.
"""

from __future__ import annotations

from copy import deepcopy

JOB_ID = "BLD-0924-01"
PERSONA = "fixture_persona"

CAPABILITIES = {"logistics", "physical_health", "relationships", "diarist"}


def question(qid: str, klass: str, text: str) -> dict:
    return {
        "id": qid, "class": klass, "text": text,
        "why_it_matters": f"because {klass} decides the shape of the answer",
        "blocks": "design",
        "expected_answer_shape": "a short statement",
    }


def question_set() -> dict:
    """A valid Question Set — ORDERED BY CLASS INDEX, which is the compass rule."""
    return deepcopy({
        "schema": "question_set/1",
        "job_id": JOB_ID,
        "generated_at": "2026-09-24T10:00:00",
        "upstream_fingerprint": "a" * 16,
        "mode": "construct",
        "request": "nothing tracks when the plants were last watered",
        "depth": "standard",
        "proposed_depth": "standard",
        "disposition": "new",
        "disposition_evidence": (
            "logistics owns errands and appointments and performs no standing "
            "judgement over a history, so it cannot answer a last-done date"),
        "generalizes_to": "any recurring household task with a cadence",
        "declined_to_ask": [],
        "spine": [
            question("q1", "intent", "What is keeping the plants alive in service of?"),
            question("q2", "cost", "What does asking every day consume that nothing meters?"),
            question("q3", "feasibility", "Is there any record of a watering at all?"),
            question("q4", "surface", "What else operates on a watering record once it exists?"),
            question("q5", "authority", "Is a reminder decided here or surfaced, and what happens on silence?"),
        ],
    })


def ledger_row(qid: str, **overrides) -> dict:
    row = {
        "question_id": qid,
        "verdict": "found",
        "kind": "history",
        "answerable_by": "data",
        "data_kind": "behavioural",
        "inventory": {
            "source": "log",
            "form": "log",
            "coverage": {"from": "2026-07-01", "to": "2026-09-24"},
            "completeness": "most days have an entry; weekends are thin",
            "freshness": "yesterday",
            "gap": "",
        },
    }
    row.update(overrides)
    return row


def answer_ledger() -> dict:
    """A valid ledger — ONE ROW PER QUESTION, which ruling 6 requires."""
    return deepcopy({
        "schema": "answer_ledger/1",
        "job_id": JOB_ID,
        "generated_at": "2026-09-24T10:05:00",
        "upstream_fingerprint": "b" * 16,
        "interview_items": [],
        "variable_proposals": [],
        "policies_matched": [],
        "rows": [
            ledger_row("q1", kind="judgment", answerable_by="judgment",
                       verdict="ask_user", data_kind="none",
                       inventory={"source": "user", "form": "conversation",
                                  "gap": "nobody has said why the plants matter"},
                       decision="treat it as a standing care commitment",
                       decision_options=["a standing commitment", "an ad-hoc chore"],
                       assumption="the user wants the plants alive, not merely watered",
                       assumption_falsifier="the user declines a reminder twice",
                       if_user_lacks_it="ask"),
            ledger_row("q2"),
            ledger_row("q3", verdict="inadequate",
                       inventory={"source": "log", "form": "log",
                                  "coverage": {"from": "2026-07-01", "to": "2026-09-24"},
                                  "completeness": "watering appears 4 times in 12 weeks",
                                  "freshness": "11 days",
                                  "gap": "no entry names WHICH plant, so a per-plant cadence cannot be derived"}),
            ledger_row("q4", kind="profile_fact", verdict="absent",
                       data_kind="single_point",
                       inventory=None,
                       gap="no plant inventory exists anywhere",
                       variable_scope="this_persona",
                       variable_name="plant_inventory",
                       variable_type="string",
                       data_home="config/personas/{p}/profile.yaml",
                       if_user_lacks_it="ask"),
            ledger_row("q5", kind="judgment", answerable_by="judgment",
                       data_kind="none",
                       decision="surface, never decide",
                       decision_options=["surface", "decide silently"],
                       assumption="an unasked-for watering reminder is welcome once a week",
                       assumption_falsifier="the user dismisses it twice running",
                       if_user_lacks_it="degrade: ask on the next ordinary turn"),
        ],
        "surface_map": surface_map(),
    })


def surface_map() -> list[dict]:
    """Every operation carries a disposition. Absence is the defect."""
    return [
        {"entity": "watering", "operation": "create", "status": "in_scope"},
        {"entity": "watering", "operation": "read", "status": "in_scope"},
        {"entity": "watering", "operation": "update", "status": "in_scope"},
        {"entity": "watering", "operation": "delete", "status": "deferred",
         "ticket": "DB-0924-99"},
        {"entity": "watering", "operation": "move", "status": "not_applicable",
         "reason": "a watering has no location to move between"},
        {"entity": "watering", "operation": "dedupe", "status": "in_scope"},
        {"entity": "watering", "operation": "merge", "status": "not_applicable",
         "reason": "two waterings are two events, never one"},
        {"entity": "watering", "operation": "expire", "status": "deferred",
         "ticket": "DB-0924-98"},
        {"entity": "watering", "operation": "reconcile", "status": "not_applicable",
         "reason": "there is no external system to reconcile against"},
    ]


def build_plan() -> dict:
    """A valid plan — every gate cited, every file halved by tier."""
    return deepcopy({
        "schema": "build_plan/1",
        "job_id": JOB_ID,
        "generated_at": "2026-09-24T10:30:00",
        "upstream_fingerprint": "c" * 16,
        "capability": {
            "id": "home_care",
            "kind": "agent",
            "one_line": "keeps standing household care tasks from going unnoticed",
            "replaces": [],
            "execution_mode": "deferred",
            "latency_budget_ms": 4000,
            "theme": "household",
            "disposition": "new",
            "disposition_evidence": (
                "logistics owns errands and performs no standing judgement over "
                "a history, so it cannot answer a last-done date"),
            "generalizes_to": "any recurring household task with a cadence",
        },
        "surface_map": surface_map(),
        "files": [
            {"path": "tools/home_care.py", "half": "implementer"},
            {"path": "tests/test_home_care.py", "half": "implementer"},
            {"path": "config/build/registry.yaml", "half": "implementer"},
            {"path": "config/agents/home_care.md", "half": "main_session"},
            {"path": "config/modules/routing.yaml", "half": "main_session"},
            {"path": "config/modules/routing_cloud.yaml", "half": "main_session"},
        ],
        "registration": [
            {"what": "routing entry", "path": "config/modules/routing.yaml"},
            {"what": "routing entry", "path": "config/modules/routing_cloud.yaml"},
            {"what": "directory entry", "path": "config/agents/coordinator.md"},
        ],
        "information_sources": [
            {"row_id": "q2", "tool": "get_log_window",
             "arguments": {"start_date": "", "end_date": ""},
             "if_user_lacks_it": "ask"},
            {"row_id": "q4", "tool": "read_profile",
             "arguments": {"field": "plant_inventory"},
             "if_user_lacks_it": "ask"},
        ],
        "integrations": [],
        "tests": ["tests/test_home_care.py"],
        "acceptance": {"primary": "mike", "fixture": "danny_park"},
        "variables": [
            {"name": "plant_inventory", "scope": "this_persona",
             "home": "config/personas/{p}/profile.yaml",
             "if_user_lacks_it": "ask"},
        ],
        # What the content gate reads. Required on an agent plan since phase C:
        # every one of these was hand-assembled at N13 from Red prose that had
        # just been typed, and `routing.allowed_tools` is where the
        # told-not-granted scan reads the grant — absent, that scan is SKIPPED
        # rather than failed, so an agent file naming an ungranted tool passed.
        "record": {
            "name": "home_care",
            "display_name": "Home Care",
            "directory_entry": "keeps standing household care from going unnoticed",
            "unavailable_consequence": "you will not be reminded about the plants",
            "routing": {"allowed_tools": ["get_log_window", "read_profile"]},
        },
        # The question ids the capability cannot work without. The ledger's
        # if_user_lacks_it rule is enforced on exactly these rows and no others.
        "required_inputs": ["q2", "q4"],
        "risks": ["grants read_profile, which is inside the read set"],
        "citations": [
            {"gate": "capability", "question_id": "q1", "ledger_row": "q1"},
            {"gate": "surface_map", "question_id": "q4", "ledger_row": "q4"},
            {"gate": "information_sources", "question_id": "q2", "ledger_row": "q2"},
            {"gate": "variables", "question_id": "q4", "ledger_row": "q4"},
        ],
        "estimate": {"subagent_calls": 4, "files_touched": 6, "tools_granted": 2},
    })


def registry_row(name: str = "home_care", status: str = "landed",
                 ticket: str = JOB_ID) -> dict:
    return deepcopy({
        "name": name,
        "display_name": "Home Care",
        "kind": "agent",
        "ticket": ticket,
        "job_id": ticket,
        "persona": PERSONA,
        "version": 1,
        "status": status,
        "at": "2026-09-24",
        "acceptance": None,
        "knowledge_domain": "",
        "run": {
            "execution_mode": "deferred",
            "latency_budget_ms": 4000,
            "dispatches_expected_per_day": None,
            "dispatches_actual_per_day": None,
            "counted_over_days": None,
            "counted_at": None,
        },
    })


def question_ids() -> set[str]:
    return {q["id"] for q in question_set()["spine"]}


def red_paths() -> set[str]:
    """The Red half of the tier table, as the driver resolves it at N7."""
    return {
        "config/constitution.md", "core/router.py", "core/persona.py",
        "core/scheduler.py", "core/spend_guard.py", "deploy.sh", ".env",
        "config/agents/home_care.md",
        "config/modules/routing.yaml", "config/modules/routing_cloud.yaml",
    }
