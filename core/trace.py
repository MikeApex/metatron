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
import re
import threading
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

# Matches absolute paths that contain /data/... and relative data/... paths,
# both ending in a recognisable file extension.
_DATA_PATH_RE = re.compile(
    r'(?:/[^\s]+/)?(data/[a-zA-Z0-9._/\-]+\.(?:json|jsonl|md|txt|yaml|csv))'
)

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
    duration_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    ok: bool = True


@dataclass
class TurnRecord:
    turn: int
    input_tokens: int = 0
    output_tokens: int = 0
    thinking_tokens: int = 0
    output_text: str = ""
    thinking_text: str = ""
    tool_calls: list[ToolCallRecord] = field(default_factory=list)


@dataclass
class AgentRecord:
    agent: str
    provider: str
    model: str
    context_sections: dict = field(default_factory=dict)
    turns: list[TurnRecord] = field(default_factory=list)
    subagents: list[AgentRecord] = field(default_factory=list)
    output_files: list[str] = field(default_factory=list)
    # Server-side retrieval (Vertex-native Google Search grounding). Populated only
    # by the grounded path, which produces no tool calls — so these two lists are the
    # only record that retrieval happened. See is_grounded() below.
    search_queries: list[str] = field(default_factory=list)
    retrieved_sources: list[str] = field(default_factory=list)
    retrieval_recorded: bool = False
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

    def total_thinking_tokens(self) -> int:
        return sum(t.thinking_tokens for t in self.turns)

    def has_tool_calls(self) -> bool:
        return any(t.tool_calls for t in self.turns) or any(s.has_tool_calls() for s in self.subagents)

    def is_grounded(self) -> bool | None:
        """Did this agent's answer rest on something retrieved from outside the model?

        Returns None when the question does not apply — which is most agents. Grounding
        is a claim about *retrieval*, and only an agent that can retrieve can fail it.

        This replaced `any(has_tool_calls())`, which measured the wrong thing in both
        directions: Vertex-native grounded search fires server-side and produces zero
        tool calls, so a genuinely grounded Research answer scored false, while an agent
        that merely called `write_log` scored true. That is why the flag added in
        `cb9f459` did not catch the fabricated-sources exchange it was built for.

        Note what is deliberately *not* here: a `has_tool_calls()` fallback. An agent
        that called `write_log` is active, not grounded, and folding tool activity back
        in would rebuild the same false signal one level down.

        Nor is it `sources or search_queries`, which the 2026-08-10 plan specified and
        a live run disproved: asking six questions and retrieving nothing scored as
        grounded while the response it accompanied said `[RETRIEVAL: NONE]`. Two
        provenance signals disagreeing about the same answer is the failure this whole
        change exists to remove. Searching and finding nothing means the answer came
        from training knowledge — that is ungrounded, and it is the more dangerous
        shape of the two, because the model has *tried* and may still assert freely.
        The queries remain on the record as diagnostics: they explain a wrong answer
        that was nonetheless grounded, which the source list alone cannot.
        """
        if not self.retrieval_recorded:
            return None
        return bool(self.retrieved_sources)


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
            # `or not t.pipeline`: a depth>0 agent with no parent to nest under
            # was silently dropped from the trace. That is the fire-and-forget
            # Diarist, which runs on its own thread with _SUBAGENT_DEPTH=1 but
            # owns a fresh trace with an empty pipeline. Root it instead.
            if depth == 0 or not t.pipeline:
                t.pipeline.append(rec)
            else:
                # Subagent — nest under the first pipeline entry (coordinator)
                t.pipeline[0].subagents.append(rec)
    _set_current_agent(rec)
    return rec


def pop_agent(rec: AgentRecord) -> None:
    rec.duration_ms = int((time.monotonic() - rec.start_mono) * 1000)


# ---------------------------------------------------------------------------
# Per-turn event recording
# ---------------------------------------------------------------------------

def record_turn_tokens(rec: AgentRecord | None, turn_num: int,
                       input_tokens: int, output_tokens: int,
                       thinking_tokens: int = 0,
                       output_text: str = "", thinking_text: str = "") -> None:
    if rec is None:
        return
    tr = rec.ensure_turn(turn_num)
    tr.input_tokens = input_tokens
    tr.output_tokens = output_tokens
    tr.thinking_tokens = thinking_tokens
    tr.output_text = output_text
    tr.thinking_text = thinking_text

    # Every provider path already reports here, so this is the one place the
    # spend guard needs to observe. It never raises.
    try:
        from core.spend_guard import record_tokens
        # Thinking tokens are billed as output tokens by every provider that
        # reports them separately — spend_guard needs the combined figure.
        record_tokens(rec.model or "", input_tokens, output_tokens + thinking_tokens)
    except Exception:
        pass


def record_retrieval(rec: AgentRecord | None,
                     search_queries: list[str] | None,
                     sources: list[str] | None) -> None:
    """Record server-side retrieval for an agent, from the SDK's own report.

    Called once, after the grounded loop finishes. `retrieval_recorded` is set even
    when both lists are empty — "we asked and nothing was retrieved" is a different
    and much more useful state than "this agent never retrieves", and collapsing the
    two is what made the old flag unreadable.
    """
    if rec is None:
        return
    rec.search_queries = list(search_queries or [])
    rec.retrieved_sources = list(sources or [])
    rec.retrieval_recorded = True


def record_tool_call(rec: AgentRecord | None, turn_num: int,
                     name: str, args: dict, result: str, duration_ms: float,
                     input_tokens: int = 0, output_tokens: int = 0,
                     ok: bool = True) -> None:
    if rec is None:
        return
    preview = result[:800] if len(result) > 800 else result
    tr = rec.ensure_turn(turn_num)
    tr.tool_calls.append(ToolCallRecord(
        name=name, args=args, result_preview=preview, duration_ms=duration_ms,
        input_tokens=input_tokens, output_tokens=output_tokens, ok=ok,
    ))
    # Extract any file paths written by this tool call (from args values + result)
    candidates: set[str] = set()
    for v in args.values():
        if isinstance(v, str):
            for m in _DATA_PATH_RE.finditer(v):
                candidates.add(m.group(1))
    for m in _DATA_PATH_RE.finditer(result):
        candidates.add(m.group(1))
    for path in candidates:
        if path not in rec.output_files:
            rec.output_files.append(path)


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
                "thinking_tokens": tr.thinking_tokens,
                "output_text": tr.output_text,
                "thinking_text": tr.thinking_text,
                "tool_calls": [
                    {
                        "name": tc.name,
                        "args": tc.args,
                        "result_preview": tc.result_preview,
                        "duration_ms": tc.duration_ms,
                        "input_tokens": tc.input_tokens,
                        "output_tokens": tc.output_tokens,
                        "ok": tc.ok,
                    }
                    for tc in tr.tool_calls
                ],
            }
            for tr in a.turns
        ],
        "subagents": [_agent_to_dict(s) for s in a.subagents],
        "output_files": a.output_files,
        "search_queries": a.search_queries,
        "retrieved_sources": a.retrieved_sources,
        # None = grounding does not apply to this agent. The monitor renders the
        # three states differently; do not collapse it to a bool here.
        "grounded": a.is_grounded(),
        "total_input_tokens": a.total_input_tokens(),
        "total_output_tokens": a.total_output_tokens(),
        "total_thinking_tokens": a.total_thinking_tokens(),
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
        # Trace-level roll-up, for the one-line header tag only. False means an agent
        # that *can* retrieve did not — the state worth flagging. It is deliberately
        # NOT `any(has_tool_calls())`: see AgentRecord.is_grounded().
        "grounded": _trace_grounded(t),
    }


def _walk_agents(agents: list[AgentRecord]):
    for a in agents:
        yield a
        yield from _walk_agents(a.subagents)


def _trace_grounded(t: RequestTrace) -> bool | None:
    """True if every retrieval-capable agent retrieved something; False if any did not.

    None when no agent in the pipeline performs retrieval at all — the ordinary case,
    and one the monitor must not render as a warning. Most conversations never touch a
    live source and there is nothing wrong with that.
    """
    states = [a.is_grounded() for a in _walk_agents(t.pipeline)]
    applicable = [s for s in states if s is not None]
    if not applicable:
        return None
    return all(applicable)


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
