"""
tests/test_native_stream_limits.py — the Synthesizer's reply loop always ends with something said.

Plan: archive/plans/reply_latency_plan_2026-10-24.md § 3. On 2026-10-24 one reply never came
(a Vertex call waited 586 s with no timeout anywhere) and another came back blank after nine
minutes (eight rounds of tool calls, then the loop fell through with nothing). Nothing in tests/
exercised `_run_gemini_native_stream` before this file.

Fakes only — no model is called, so no live meter is reached. Each fake returns REAL
google-genai `types.Part` objects, because the loop rebuilds `types.Content` from them and a
stand-in object would fail validation in a way production never does.

    python3 tests/test_native_stream_limits.py
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from google.genai import types  # noqa: E402

import core.orchestrator as O  # noqa: E402
from tools import turn_context as T  # noqa: E402

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
    def __init__(self, parts):
        self.usage_metadata = None
        self.candidates = [type("C", (), {"content": types.Content(role="model", parts=parts)})()]


def _call(name):
    return types.Part(function_call=types.FunctionCall(name=name, args={}))


def _text(t):
    return types.Part(text=t)


class _Capacity(Exception):
    """Shaped like a DSQ refusal."""
    code = 429


class _FakeModels:
    def __init__(self, script):
        # script: list of callables, one per generate_content_stream call; each returns an
        # iterable of chunks or raises.
        self.script = list(script)
        self.calls = 0

    def generate_content_stream(self, model, contents, config):
        self.calls += 1
        step = self.script.pop(0) if self.script else (lambda: [_Chunk([_call("probe_tool")])])
        return step()


class _FakeClient:
    def __init__(self, script):
        self.models = _FakeModels(script)


_dispatched: list[str] = []
_SCHEMAS = [{"name": "probe_tool", "description": "test",
             "input_schema": {"type": "object", "properties": {}}}]
_HANDLERS = {"probe_tool": lambda: (_dispatched.append("probe_tool") or "ok")}


def _run(client, **kw) -> tuple[str, list[dict]]:
    history: list[dict] = []
    out = "".join(O._run_gemini_native_stream(
        client, "fake-model", "system", "hello", _SCHEMAS, _HANDLERS,
        history=history, max_iterations=kw.pop("max_iterations", O._SYNTH_MAX_ROUNDS), **kw))
    return out, history


def _reset():
    _dispatched.clear()
    O.time.sleep = lambda s: None   # the 2 s capacity pause, not under test


# Live meters stubbed: log_model_error appends to data/diagnostics/model_errors.json, and the
# first run of this file wrote three fake-model rows there.
import core.router as _router  # noqa: E402
_router.log_model_error = lambda *a, **k: None


@check("a turn that only ever calls tools ends with the forced reply, within the round cap")
def _():
    _reset()
    rounds = [lambda: [_Chunk([_call("probe_tool")])]] * O._SYNTH_MAX_ROUNDS
    client = _FakeClient(rounds + [lambda: [_Chunk([_text("Here is what I did.")])]])
    out, hist = _run(client)
    assert out == "Here is what I did.", out
    assert len(_dispatched) == O._SYNTH_MAX_ROUNDS, _dispatched
    assert client.models.calls == O._SYNTH_MAX_ROUNDS + 1
    assert hist[-1]["content"] == "Here is what I did."


@check("if the forced reply is empty too, the fixed line is said — never a blank reply")
def _():
    _reset()
    rounds = [lambda: [_Chunk([_call("probe_tool")])]] * (O._SYNTH_MAX_ROUNDS + 1)
    out, _ = _run(_FakeClient(rounds))
    assert out == O._NO_REPLY_LINE, out


@check("the forced reply never runs a tool the model asks for anyway")
def _():
    _reset()
    rounds = [lambda: [_Chunk([_call("probe_tool")])]] * O._SYNTH_MAX_ROUNDS
    client = _FakeClient(rounds + [lambda: [_Chunk([_call("probe_tool"), _text("Done.")])]])
    out, _ = _run(client)
    assert out == "Done." and len(_dispatched) == O._SYNTH_MAX_ROUNDS, (out, _dispatched)


def _raise(exc):
    def f():
        raise exc
    return f


@check("a 429 before anything arrives is retried exactly once, then the turn proceeds")
def _():
    _reset()
    client = _FakeClient([_raise(_Capacity("busy")), lambda: [_Chunk([_text("Answer.")])]])
    out, _ = _run(client)
    assert out == "Answer." and client.models.calls == 2, (out, client.models.calls)


@check("two capacity failures end the turn with the fixed line, not an exception")
def _():
    _reset()
    client = _FakeClient([_raise(_Capacity("busy")), _raise(_Capacity("busy"))])
    out, _ = _run(client)
    assert out == O._NO_REPLY_LINE and client.models.calls == 2


@check("a non-capacity failure with nothing done is raised, so the compat fallback can run")
def _():
    _reset()
    try:
        _run(_FakeClient([_raise(ValueError("schema"))]))
    except ValueError:
        return
    raise AssertionError("expected the error to reach the caller")


@check("after a tool has run, no failure is re-raised — the caller must not re-run the turn")
def _():
    _reset()
    client = _FakeClient([lambda: [_Chunk([_call("probe_tool")])], _raise(ValueError("boom"))])
    out, _ = _run(client)
    assert out == O._NO_REPLY_LINE and _dispatched == ["probe_tool"], (out, _dispatched)


@check("a connection lost after text was shown keeps the text and adds the cut line")
def _():
    _reset()

    def partial():
        yield _Chunk([_text("The first half")])
        raise _Capacity("dropped")
    out, hist = _run(_FakeClient([partial]))
    assert out == "The first half" + O._CUT_REPLY_LINE, out
    assert hist[-1]["content"].startswith("The first half")


@check("past the soft deadline no new round starts; the turn answers from what it has")
def _():
    _reset()
    rounds = [lambda: [_Chunk([_call("probe_tool")])], lambda: [_Chunk([_text("Wrapped up.")])]]
    client = _FakeClient(rounds)
    with T.turn_scope(user_turn=True) as turn:
        turn[O._TURN_SOFT_DEADLINE_KEY] = time.monotonic() - 1   # already past
        out, _ = _run(client)
    assert out == "Wrapped up." and client.models.calls == 2 and _dispatched == ["probe_tool"]


@check("a round with neither text nor a call says the fixed line")
def _():
    _reset()
    out, _ = _run(_FakeClient([lambda: [_Chunk([])]]))
    assert out == O._NO_REPLY_LINE, out


@check("the output ceiling leaves reply room above the thinking budget (the ceiling is still shared)")
def _():
    # 09-17 → 10-26: thinking + reply = 4,092 at a shared 4,096 ceiling left ~160 tokens to say
    # anything, and some turns nothing at all.
    _reset()
    seen = []
    client = _FakeClient([lambda: [_Chunk([_text("ok")])]])
    real = client.models.generate_content_stream
    client.models.generate_content_stream = lambda model, contents, config: (
        seen.append(config) or real(model, contents, config))
    _run(client, thinking_budget=O._SYNTH_THINKING_BUDGET)
    assert seen[0].max_output_tokens == O._SYNTH_THINKING_BUDGET + O._REPLY_OUTPUT_TOKENS, \
        seen[0].max_output_tokens
    assert O._max_output_tokens(None) == O._REPLY_OUTPUT_TOKENS


@check("the forced reply's instruction is its own user turn, never merged into the tool results")
def _():
    # A merged turn (function responses + text) is refused by Vertex with a 400 — probed
    # 2026-10-26 — which turned every round-cap exit into the fixed line.
    _reset()
    seen = []
    rounds = [lambda: [_Chunk([_call("probe_tool")])]] * O._SYNTH_MAX_ROUNDS
    client = _FakeClient(rounds + [lambda: [_Chunk([_text("Done.")])]])
    real = client.models.generate_content_stream
    client.models.generate_content_stream = lambda model, contents, config: (
        seen.append(list(contents)) or real(model, contents, config))
    out, _ = _run(client)
    last, prev = seen[-1][-1], seen[-1][-2]
    assert out == "Done.", out
    assert last.role == "user" and [p.text for p in last.parts] == [O._FINAL_REPLY_PROMPT]
    assert prev.role == "user" and all(p.function_response for p in prev.parts), prev.parts


@check("a cut-reply event fires at the hard ceiling, not at the overshot thinking budget")
def _():
    events = []
    import tools.logger as L
    real = L.write_quality_event
    L.write_quality_event = lambda kind, **k: events.append(kind)
    try:
        b = O._SYNTH_THINKING_BUDGET
        O._note_thinking_cap_hit(b, 5673, 485, 1)          # overshoot, reply whole: silent
        assert events == [], events
        O._note_thinking_cap_hit(b, O._max_output_tokens(b) - 300, 290, 1)  # at the ceiling
        assert events == ["THINKING_CAP_HIT"], events
    finally:
        L.write_quality_event = real


@check("the plain path: the day planner gets 8,192 output tokens, every other agent 4,096")
def _():
    # Day planner smoke test, 2026-10-27: thinking ~3,930 + ~163 out = the 4,096 ceiling, and
    # every placement JSON was cut mid-line. The request is captured, never sent.
    sent = []

    class _Resp:
        def __init__(self):
            msg = type("M", (), {"content": '{"placements": []}', "tool_calls": None})()
            self.choices = [type("C", (), {"message": msg, "finish_reason": "stop"})()]
            self.usage = None

    class _Client:
        def __init__(self, *a, **k):
            self.chat = type("Ch", (), {"completions": type("Co", (), {
                "create": staticmethod(lambda **kw: sent.append(kw) or _Resp())})()})()

    import openai
    real_client, real_creds = openai.OpenAI, O._resolve_gemini_credentials
    openai.OpenAI = _Client
    O._resolve_gemini_credentials = lambda model=None: ("k", "https://x.googleapis.com", "m")
    try:
        for agent, want in (("day_planner", 8192), ("logistics", 4096)):
            sent.clear()
            O.run_session_gemini("sys", "in", [], {},
                                 max_output_tokens=O._WIDE_OUTPUT_AGENTS.get(agent, 4096))
            assert sent and sent[0].get("max_tokens") == want, (agent, sent[:1])
        sent.clear()
        O.run_session_gemini("sys", "in", [], {})                 # default unchanged
        assert sent[0].get("max_tokens") == 4096, sent[:1]
    finally:
        openai.OpenAI, O._resolve_gemini_credentials = real_client, real_creds


@check("capacity errors are told apart from the rest")
def _():
    assert O._is_capacity_error(_Capacity("x"))
    assert O._is_capacity_error(type("ReadTimeout", (Exception,), {})("x"))
    assert O._is_capacity_error(type("E", (Exception,), {"code": 503})("x"))
    assert not O._is_capacity_error(ValueError("x"))
    assert not O._is_capacity_error(type("E", (Exception,), {"code": 400})("x"))


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
