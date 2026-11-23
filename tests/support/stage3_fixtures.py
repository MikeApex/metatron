"""
tests/support/stage3_fixtures.py — the offline harness the Stage 3 suites share
(archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md).

Two pieces, both model-free:

- `sandbox()` — a temporary persona tree (config + data) for a synthetic persona, with the ledger
  clock, push, tagging and background indexing stubbed. Nothing under the real `data/personas/`
  is touched.
- `pipeline()` — the REAL pipeline twins and the REAL `_run_single_agent` (so H1, the Finance
  hooks, `_after_specialists` and the twin wiring all run as shipped), with the provider layer
  replaced: `run_session_openai` answers per agent from a script (the agent is read from the
  trace's current record, which `_run_single_agent` pushes), and `_openai_compat_stream` yields
  the Synthesizer's scripted reply. Context loaders and side-effect helpers that would read the
  real store or call a model are stubbed to empty. Every call's input is recorded.

Run nothing directly; imported by tests/test_medication_check.py, test_crisis_line.py,
test_finance_totals.py and test_a4_runner_offline.py.
"""

from __future__ import annotations

import contextlib
import json
import tempfile
import threading
from datetime import datetime
from pathlib import Path

PERSONA = "sarah_chen"


@contextlib.contextmanager
def patched(pairs):
    """Set each (obj, name, value) and restore it on exit, in reverse."""
    saved = []
    try:
        for obj, name, value in pairs:
            saved.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)
        yield
    finally:
        for obj, name, value in reversed(saved):
            setattr(obj, name, value)


@contextlib.contextmanager
def sandbox(persona: str = PERSONA, profile: dict | None = None, clock: datetime | None = None,
            location_country: str | None = None):
    """A temp persona tree; yields {"root", "data", "config", "state"}. `profile`: a
    medication_profile dict seeded into Physical Health's agent config. `state["clock"]` drives
    the task ledger's clock (tools.obligations._now)."""
    from core import persona as persona_mod, trace as trace_mod
    from core.persona import persona_scope
    import tools.data_objects as DO
    import tools.diarist as DI
    import tools.logger as LOG
    import tools.obligations as O

    state = {"clock": clock or datetime.now().replace(second=0, microsecond=0)}
    with tempfile.TemporaryDirectory(prefix="metatron-stage3-") as td:
        root = Path(td)
        cfg = root / "config" / "personas" / persona
        data = root / "data" / "personas" / persona
        cfg.mkdir(parents=True)
        data.mkdir(parents=True)
        if profile is not None:
            (data / "config").mkdir(parents=True, exist_ok=True)
            (data / "config" / "physical_health.json").write_text(
                json.dumps({"medication_profile": json.dumps(profile)}))
        if location_country is not None:
            import yaml
            (cfg / "profile.yaml").write_text(yaml.safe_dump(
                {"location": {"country": location_country}}))
        pairs = [(persona_mod, "_ROOT", root), (trace_mod, "ROOT", root),
                 (O, "_now", lambda: state["clock"]),
                 (LOG, "run_background", lambda *a, **k: None),
                 (DI, "run_background", lambda *a, **k: None),
                 (DO, "_call_tagger", lambda payload, persona: "[]"),
                 (DO, "_send_push", lambda *a, **k: None),
                 (DO, "_quality_event", lambda **k: None),
                 (DO, "TAG_IN_BACKGROUND", False)]
        with patched(pairs), persona_scope(persona):
            yield {"root": root, "data": data, "config": cfg, "state": state}


def linked_habit(state: dict, what: str, medication: str, days: int = 1) -> str:
    """A daily dose habit linked to `medication`, opened `days` before the clock (so the
    creation-day rule does not excuse today's dose)."""
    from datetime import timedelta
    import tools.obligations as O
    now = state["clock"]
    state["clock"] = now - timedelta(days=days)
    try:
        out = O.open_task(what, kind="habit", every="day", times=1, new_instance=True,
                          medication=medication)
    finally:
        state["clock"] = now
    assert out.startswith("task "), out
    return out.split()[1]


def coordinator_package(specs: list[dict]) -> str:
    return "USER_STATE: ordinary\nSPECIALISTS_TO_CALL: " + json.dumps(specs) + "\n\nNOTES: none"


class Script:
    """What each agent answers, and everything each was given."""

    def __init__(self, replies: dict, synth_reply: str = "Noted.", side_effects: dict | None = None):
        self.replies = dict(replies)
        self.synth_reply = synth_reply
        self.side_effects = dict(side_effects or {})
        self.inputs: dict[str, list[str]] = {}
        self.lock = threading.Lock()

    def record(self, agent: str, text: str) -> None:
        with self.lock:
            self.inputs.setdefault(agent, []).append(text)

    def last(self, agent: str) -> str:
        return (self.inputs.get(agent) or [""])[-1]


@contextlib.contextmanager
def pipeline(script: Script, extra: list | None = None):
    """The real twins over a scripted provider — see the module docstring. Use inside
    sandbox()."""
    from core import orchestrator as ORC
    import tools.capture as CAP

    def fake_openai(system_prompt, user_input, tool_schemas, tool_handlers, model=None,
                    history=None, **kw):
        rec = ORC._tr.get_current_agent()
        agent = rec.agent if rec is not None else "?"
        script.record(agent, user_input)
        fx = script.side_effects.get(agent)
        if fx:
            fx()
        if agent == "synthesizer":
            return script.synth_reply
        reply = script.replies.get(agent, f"{agent}: nothing to add")
        return reply() if callable(reply) else reply

    def fake_stream(system_prompt, augmented_input, tool_schemas, tool_handlers, **kw):
        script.record("synthesizer", augmented_input)
        text = script.synth_reply
        for i in range(0, len(text), 7):
            yield text[i:i + 7]

    empty = lambda *a, **k: ""          # noqa: E731
    none = lambda *a, **k: None         # noqa: E731
    # EVERY provider entry point is scripted, not only the one a test names: a path that passes
    # no provider (run_subagent, the scheduler) resolves routing, which may name a local Ollama
    # or Vertex model — and an offline suite must never reach either.
    pairs = [
        (ORC, "run_session_openai", fake_openai),
        (ORC, "run_session_ollama", fake_openai),
        (ORC, "run_session_gemini", fake_openai),
        (ORC, "run_session_gemini_cached", fake_openai),
        (ORC, "run_session_gemini_grounded", fake_openai),
        (ORC, "run_session_anthropic", fake_openai),
        (ORC, "_openai_compat_stream", fake_stream),
        (ORC, "run_session_gemini_cached_stream", fake_stream),
        (ORC, "_anthropic_stream", fake_stream),
        (ORC, "_spend_gate", none),
        (ORC, "_pending_tokens", lambda *a, **k: set()),
        (ORC, "_load_coordinator_context", empty),
        (ORC, "session_kind", none),
        (ORC, "_bind_turn_kind", none),
        (ORC, "_scheduled_focus_block", empty),
        (ORC, "_name_note", empty),
        (ORC, "_resolve_knowledge", lambda *a, **k: {}),
        (ORC, "_resolve_data_objects", none),
        (ORC, "_task_hint_block", empty),
        (ORC, "_take_log_offer", none),
        (ORC, "_unsaved_log_notes", lambda *a, **k: []),
        (ORC, "_data_object_block", empty),
        (ORC, "_data_object_manifest", empty),
        (ORC, "_day_plan_block", empty),
        (ORC, "_horizon_block", empty),
        (ORC, "persist_context_block", none),
        (ORC, "_close_turn_bookkeeping", none),
        (ORC, "check_false_action_claims", none),
        (ORC, "_stamp_routine_revisits", none),
        (ORC, "_handle_user_correction", none),
        (ORC, "_handle_misheard", none),
        (ORC, "_handle_schedule_impact", none),
        (ORC, "load_recent_context", empty),
        (ORC, "load_config", empty),
        (CAP, "start", none),
        (CAP, "note_for_synthesizer", none),
        (CAP, "after_synthesizer", none),
        (CAP, "defer", none),
        *(extra or []),
    ]
    with patched(pairs):
        yield script


def collect_stream(chunks) -> str:
    """The text a client is left holding, read the way core/server.py consumes the stream:
    `[RETRACT_WITH]<text>` replaces what streamed, `[RETRACT]` empties it and ends, `[DONE]`
    ends, `[HOLD]` is a signal and never text."""
    shown = ""
    for c in chunks:
        if c == "[DONE]":
            break
        if c == "[RETRACT]":
            return ""
        if c.startswith("[RETRACT_WITH]"):
            shown = c[len("[RETRACT_WITH]"):]
            continue
        if c == "[HOLD]":
            continue
        shown += c
    return shown
