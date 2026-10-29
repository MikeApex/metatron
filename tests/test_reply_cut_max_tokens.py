"""
tests/test_reply_cut_max_tokens.py — a reply cut at MAX_TOKENS is replaced, never delivered,
[DB-1026-01] (reopened 2026-10-29).

Live 2026-10-28 18:35 a scheduled quiet check-in thought 7,865 tokens against the 8,192 ceiling;
the round ended MAX_TOKENS and the 323 tokens it had emitted — a fragment of its own prompt,
"ALREADY ASKED AND STILL UNANSWERED — DO NOT ASK THESE AGAIN…" — reached Mike as the reply.

What is pinned here is the provider half, where the decision is made: `_run_gemini_native_stream`
yields the replacement behind `_REPLACE_REPLY_SENTINEL`, and `_final_reply_round` runs on a
smaller thinking target and refuses its own MAX_TOKENS text. The pipeline's interception of the
sentinel (`_run_pipeline_session_stream_inner`) has no stub harness in tests/ and is NOT run here.

Fakes only — no model is called. Same fake shapes as tests/test_native_stream_limits.py.

    python3 tests/test_reply_cut_max_tokens.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types  # noqa: E402

import core.orchestrator as O  # noqa: E402
import core.router as _router  # noqa: E402

_router.log_model_error = lambda *a, **k: None   # live meter: data/diagnostics/model_errors.json

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


class _Chunk:
    def __init__(self, parts, finish=None):
        self.usage_metadata = None
        cand = type("C", (), {})()
        cand.content = types.Content(role="model", parts=parts)
        cand.finish_reason = finish
        self.candidates = [cand]


class _FakeModels:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.configs = []

    def generate_content_stream(self, model, contents, config):
        self.calls += 1
        self.configs.append(config)
        return self.script.pop(0)()


class _FakeClient:
    def __init__(self, script):
        self.models = _FakeModels(script)


_dispatched: list[str] = []
_SCHEMAS = [{"name": "probe_tool", "description": "test",
             "input_schema": {"type": "object", "properties": {}}}]
_HANDLERS = {"probe_tool": lambda: (_dispatched.append("probe_tool") or "ok")}

_FRAGMENT = 'Wait, look at:\n"ALREADY ASKED AND STILL UNANSWERED — DO NOT ASK THESE AGAIN:'


def _run(client):
    history: list[dict] = []
    chunks = list(O._run_gemini_native_stream(
        client, "fake-model", "system", "Quiet check-in", _SCHEMAS, _HANDLERS,
        history=history, max_iterations=O._SYNTH_MAX_ROUNDS, thinking_budget=4096))
    return chunks, history


def _text(t):
    return types.Part(text=t)


@check("a round cut at MAX_TOKENS ends with the sentinel carrying the final round's reply")
def _():
    _dispatched.clear()
    client = _FakeClient([lambda: [_Chunk([_text(_FRAGMENT)], finish="MAX_TOKENS")],
                          lambda: [_Chunk([_text("Nothing pressing tonight, Mike.")], finish="STOP")]])
    chunks, hist = _run(client)
    assert chunks[-1] == O._REPLACE_REPLY_SENTINEL + "Nothing pressing tonight, Mike.", chunks
    assert client.models.calls == 2
    assert hist[-1]["content"] == "Nothing pressing tonight, Mike.", hist
    assert _FRAGMENT not in hist[-1]["content"]


@check("the final round runs on the smaller thinking target")
def _():
    client = _FakeClient([lambda: [_Chunk([_text(_FRAGMENT)], finish="MAX_TOKENS")],
                          lambda: [_Chunk([_text("ok")], finish="STOP")]])
    _run(client)
    first, final = client.models.configs
    assert first.thinking_config.thinking_budget == 4096, first.thinking_config
    assert final.thinking_config.thinking_budget == O._FINAL_ROUND_THINKING_BUDGET, final.thinking_config


@check("if the final round is cut too, the fixed line replaces the fragment — never a fragment")
def _():
    client = _FakeClient([lambda: [_Chunk([_text(_FRAGMENT)], finish="MAX_TOKENS")],
                          lambda: [_Chunk([_text("half a sen")], finish="MAX_TOKENS")]])
    chunks, hist = _run(client)
    assert chunks[-1] == O._REPLACE_REPLY_SENTINEL + O._NO_REPLY_LINE, chunks
    assert hist[-1]["content"] == O._NO_REPLY_LINE


@check("a round that finished (STOP) is delivered untouched, with no extra call")
def _():
    client = _FakeClient([lambda: [_Chunk([_text("All clear.")], finish="STOP")]])
    chunks, _ = _run(client)
    assert "".join(chunks) == "All clear." and client.models.calls == 1, (chunks, client.models.calls)
    assert not any(c.startswith(O._REPLACE_REPLY_SENTINEL) for c in chunks)


@check("a MAX_TOKENS round that asked for a tool runs the tool and carries on as before")
def _():
    _dispatched.clear()
    call = types.Part(function_call=types.FunctionCall(name="probe_tool", args={}))
    client = _FakeClient([lambda: [_Chunk([call], finish="MAX_TOKENS")],
                          lambda: [_Chunk([_text("Done.")], finish="STOP")]])
    chunks, _ = _run(client)
    assert _dispatched == ["probe_tool"] and "".join(chunks) == "Done.", (_dispatched, chunks)


@check("the scheduler's client returns a replaced reply's text, not a blank")
def _():
    src = (Path(__file__).resolve().parent.parent / "core" / "remote_client.py").read_text()
    assert 'kind == "retract":\n' in src and 'return msg.get("text", "")' in src, \
        "remote_client._send_one must return the retract payload's text"


if __name__ == "__main__":
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if not ok else ""))
    print(f"\n{passed} passed, {len(_results) - passed} failed, {len(_results)} total")
    sys.exit(0 if passed == len(_results) else 1)
