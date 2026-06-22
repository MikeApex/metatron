"""
core/trace.py — per-request trace collection for The Book monitor.

Captures the full internal flow of each pipeline run: agent sequence,
per-turn token counts, tool calls, and context sections loaded.

Writes to data/traces/YYYY-MM-DD.jsonl (or data/personas/{persona}/traces/)
one JSON line per completed request. The monitor tool reads these files
via the /monitor API endpoints on the FastAPI server.

Usage is entirely passive — callers emit events; nothing here blocks.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Thread-local storage — one trace context per thread.
# Worker threads (parallel subagent dispatch) inherit the parent trace
# reference manually via _set_trace() before running.
_ctx = threading.local()


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class ToolCallRecord:
    name: str
    args: dict
    result_preview: str
    duration_ms: int


@dataclass
class TurnRecord:
    turn: int
    input_tokens: int = 0
    output_tokens: int = 0
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


@dataclass
class AgentRecord:
    agent: str
    provider: str
    model: str
    context_sections: dict = field(default_factory=dict)
    turns: list[TurnRecord] = field(default_factory=list)
    subagents: list[AgentRecord] = field(default_factory=list)
    start_mono: float = field(default_factory=time.monotonic)
    duration_ms: int = 0

    def ensure_turn(self, turn_num: int) -> TurnRecord:
        while len(self.turns) < turn_num:
            self.turns.append(TurnRecord(turn=len(self.turns) + 1))
        return self.turns[turn_num - 1]

    def total_input_tokens(self) -> int:
        return sum(t.input_tokens for t in self.turns)

    def total_output_tokens(self) -> int:
        return sum(t.output_tokens for t in self.turns)


class RequestTrace:
    def __init__(self, user_input: str, persona: str | None, is_proactive: bool = False):
        self.trace_id = str(uuid.uuid4())[:8]
        self.ts = datetime.now().isoformat()
        self.persona = persona
        self.user_input = user_input
        self.synth_response: str = ""
        self.is_proactive = is_proactive
        self.pipeline: list[AgentRecord] = []
        self.start_mono = time.monotonic()
        self._lock = threading.Lock()  # guards pipeline/subagent list mutations from worker threads


# ---------------------------------------------------------------------------
# Thread-local accessors
# ---------------------------------------------------------------------------

def get_trace() -> RequestTrace | None:
    return getattr(_ctx, "trace", None)


def set_trace(t: RequestTrace | None) -> None:
    _ctx.trace = t


def get_current_agent() -> AgentRecord | None:
    return getattr(_ctx, "current_agent", None)


def _set_current_agent(rec: AgentRecord | None) -> None:
    _ctx.current_agent = rec


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

def start_request_trace(user_input: str, persona: str | None, is_proactive: bool = False) -> RequestTrace:
    t = RequestTrace(user_input, persona, is_proactive)
    set_trace(t)
    return t


def finish_request_trace(synth_response: str) -> dict | None:
    t = get_trace()
    if t is None:
        return None
    t.synth_response = synth_response
    duration_ms = int((time.monotonic() - t.start_mono) * 1000)
    data = _serialize(t, duration_ms)
    _write(data, t.persona)
    set_trace(None)
    _set_current_agent(None)
    return data


# ---------------------------------------------------------------------------
# Agent lifecycle
# ---------------------------------------------------------------------------

def push_agent(agent: str, provider: str, model: str, context_sections: dict | None = None) -> AgentRecord:
    """
    Register the start of an agent execution. Returns the AgentRecord —
    callers should pass it to pop_agent() when the agent finishes.
    """
    rec = AgentRecord(agent=agent, provider=provider, model=model,
                      context_sections=context_sections or {})
    t = get_trace()
    if t is not None:
        depth = int(os.environ.get("_SUBAGENT_DEPTH", "0"))
        with t._lock:
            if depth == 0:
                t.pipeline.append(rec)
            else:
                # Subagent — nest under the first pipeline entry (coordinator)
                if t.pipeline:
                    t.pipeline[0].subagents.append(rec)
    _set_current_agent(rec)
    return rec


def pop_agent(rec: AgentRecord) -> None:
    rec.duration_ms = int((time.monotonic() - rec.start_mono) * 1000)


# ---------------------------------------------------------------------------
# Per-turn event recording
# ---------------------------------------------------------------------------

def record_turn_tokens(rec: AgentRecord | None, turn_num: int,
                       input_tokens: int, output_tokens: int) -> None:
    if rec is None:
        return
    tr = rec.ensure_turn(turn_num)
    tr.input_tokens = input_tokens
    tr.output_tokens = output_tokens


def record_tool_call(rec: AgentRecord | None, turn_num: int,
                     name: str, args: dict, result: str, duration_ms: int) -> None:
    if rec is None:
        return
    # Truncate large results so the trace file stays readable
    preview = result[:800] if len(result) > 800 else result
    tr = rec.ensure_turn(turn_num)
    tr.tool_calls.append(ToolCallRecord(
        name=name, args=args, result_preview=preview, duration_ms=duration_ms
    ))


# ---------------------------------------------------------------------------
# Serialisation and persistence
# ---------------------------------------------------------------------------

def _agent_to_dict(a: AgentRecord) -> dict:
    return {
        "agent": a.agent,
        "provider": a.provider,
        "model": a.model,
        "context_sections": a.context_sections,
        "turns": [
            {
                "turn": tr.turn,
                "input_tokens": tr.input_tokens,
                "output_tokens": tr.output_tokens,
                "tool_calls": [
                    {
                        "name": tc.name,
                        "args": tc.args,
                        "result_preview": tc.result_preview,
                        "duration_ms": tc.duration_ms,
                    }
                    for tc in tr.tool_calls
                ],
            }
            for tr in a.turns
        ],
        "subagents": [_agent_to_dict(s) for s in a.subagents],
        "total_input_tokens": a.total_input_tokens(),
        "total_output_tokens": a.total_output_tokens(),
        "duration_ms": a.duration_ms,
    }


def _serialize(t: RequestTrace, duration_ms: int) -> dict:
    return {
        "trace_id": t.trace_id,
        "ts": t.ts,
        "persona": t.persona,
        "user_input": t.user_input,
        "synth_response": t.synth_response,
        "is_proactive": t.is_proactive,
        "duration_ms": duration_ms,
        "pipeline": [_agent_to_dict(a) for a in t.pipeline],
    }


def _write(data: dict, persona: str | None) -> None:
    if persona:
        traces_dir = ROOT / "data" / "personas" / persona / "traces"
    else:
        traces_dir = ROOT / "data" / "traces"
    traces_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    trace_file = traces_dir / f"{date_str}.jsonl"
    with open(trace_file, "a") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")
