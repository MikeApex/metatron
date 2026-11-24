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


@check("the plain path: the day planner gets 16,384 output tokens, every other agent 4,096")
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
        for agent, want in (("day_planner", 16384), ("logistics", 4096)):
            sent.clear()
            O.run_session_gemini("sys", "in", [], {},
                                 max_output_tokens=O._WIDE_OUTPUT_AGENTS.get(agent, 4096))
            assert sent and sent[0].get("max_tokens") == want, (agent, sent[:1])
        sent.clear()
        O.run_session_gemini("sys", "in", [], {})                 # default unchanged
        assert sent[0].get("max_tokens") == 4096, sent[:1]
    finally:
        openai.OpenAI, O._resolve_gemini_credentials = real_client, real_creds


@check("the plain path: the day planner runs with thinking 0, nobody else's is capped")
def _():
    # 2026-10-28: a live reshuffle ran out at 15,726 thinking + 654 out of 16,384.
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
        for agent, want in (("day_planner", 0), ("logistics", None)):
            sent.clear()
            O.run_session_gemini("sys", "in", [], {},
                                 max_output_tokens=O._WIDE_OUTPUT_AGENTS.get(agent, 4096),
                                 thinking_budget=O._PLAIN_THINKING_CAPS.get(agent))
            got = (((sent[0].get("extra_body") or {}).get("extra_body") or {}).get("google") or {}
                   ).get("thinking_config", {}).get("thinking_budget")
            assert got == want, (agent, sent[:1])
        assert sent[0].get("max_tokens") == 4096 and "extra_body" not in sent[0], sent[:1]
        assert O._WIDE_OUTPUT_AGENTS["day_planner"] == 16384     # the ceiling is kept
        # The day planner's retry after a cut reply asks for 0, and 0 is sent — not the cap.
        sent.clear()
        O.run_session_gemini("sys", "in", [], {}, max_output_tokens=16384, thinking_budget=0)
        assert sent[0]["extra_body"]["extra_body"]["google"]["thinking_config"] == {
            "thinking_budget": 0}, sent[:1]
        import inspect
        src = inspect.getsource(O._run_single_agent)
        assert "if thinking_budget is not None" in src and "_PLAIN_THINKING_CAPS.get(agent_name)" in src
        assert "thinking_budget=thinking_budget" in inspect.getsource(O.run_session)
    finally:
        openai.OpenAI, O._resolve_gemini_credentials = real_client, real_creds


@check("capacity errors are told apart from the rest")
def _():
    assert O._is_capacity_error(_Capacity("x"))
    assert O._is_capacity_error(type("ReadTimeout", (Exception,), {})("x"))
    assert O._is_capacity_error(type("E", (Exception,), {"code": 503})("x"))
    assert not O._is_capacity_error(ValueError("x"))
    assert not O._is_capacity_error(type("E", (Exception,), {"code": 400})("x"))


# --- Stage 2 #10: CHAIN_LIMIT_REACHED and B4's final-round wording ---------------------------
# The round cap (_SYNTH_MAX_ROUNDS) already ended tool use; nothing recorded it and the final
# prompt said nothing about what was left undone. No call is ever refused.

import core.trace as _TR  # noqa: E402
import tools.logger as _L  # noqa: E402


class _Events:
    """Captures write_quality_event calls made through tools.logger (no file is written)."""

    def __enter__(self):
        self.events: list[tuple[str, dict]] = []
        self._real = _L.write_quality_event
        _L.write_quality_event = lambda event_type="", **k: (
            self.events.append((event_type, k)) or "ok")
        return self

    def __exit__(self, *exc):
        _L.write_quality_event = self._real

    def kinds(self):
        return [k for k, _ in self.events]


def _as_agent(name):
    rec = _TR.AgentRecord(agent=name, provider="", model="")
    _TR._set_current_agent(rec)
    return rec


def _calls_only(n):
    return [lambda: [_Chunk([_call("probe_tool")])]] * n


@check("#10.1 the cap ending a Synthesizer reply records CHAIN_LIMIT_REACHED and runs the final round")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        client = _FakeClient(_calls_only(O._SYNTH_MAX_ROUNDS) + [lambda: [_Chunk([_text("Done.")])]])
        with _Events() as ev:
            out, _ = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert out == "Done." and client.models.calls == O._SYNTH_MAX_ROUNDS + 1, out
    assert ev.kinds() == ["CHAIN_LIMIT_REACHED"], ev.events
    detail = ev.events[0][1]["detail"]
    assert f"{O._SYNTH_MAX_ROUNDS}-round tool limit" in detail and "probe_tool" in detail, detail


# Stage 4 Step 0 changed 1b: the final round now runs after a last round that spoke beside its
# calls (that text may be only a preamble), told to reply with nothing if the user is already
# answered. 1b's final round therefore runs (calls = cap + 1); it returns empty here, and the
# output is still exactly the answer, which is what 1b protects.
@check("#10.1b round-4 answer beside a call, then the cap: event written, empty final round dropped")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda: [_Chunk([_text("Friday is booked; Saturday I could not check."),
                                      _call("probe_tool")])]]
                  + [lambda: [_Chunk([_text("   ")])]])
        client = _FakeClient(rounds)
        with _Events() as ev:
            out, hist = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert ev.kinds() == ["CHAIN_LIMIT_REACHED"]
    assert client.models.calls == O._SYNTH_MAX_ROUNDS + 1, client.models.calls
    assert out == "Friday is booked; Saturday I could not check.", repr(out)
    assert hist[-1]["content"] == out


def _capture_contents(client):
    seen = []
    real = client.models.generate_content_stream
    client.models.generate_content_stream = lambda model, contents, config: (
        seen.append(list(contents)) or real(model, contents, config))
    return seen


def _last_user_text(contents):
    c = contents[-1]
    return "".join(getattr(p, "text", "") or "" for p in (c.parts or []))


@check("Step0.1 preamble beside calls at the cap: final round runs, follows after a blank line")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda: [_Chunk([_text("Let me check Saturday."), _call("probe_tool")])]]
                  + [lambda: [_Chunk([_text("Saturday is still unchecked.")])]])
        client = _FakeClient(rounds)
        seen = _capture_contents(client)
        with _Events():
            out, hist = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert client.models.calls == O._SYNTH_MAX_ROUNDS + 1, client.models.calls
    assert out == "Let me check Saturday.\n\nSaturday is still unchecked.", repr(out)
    assert hist[-1]["content"] == out
    final_prompt = _last_user_text(seen[-1])
    assert final_prompt == O._FINAL_REPLY_PROMPT + O._FINAL_REPLY_IF_ANSWERED, final_prompt


@check("Step0.1 answer beside calls at the cap, empty final reply: output is just the answer")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda: [_Chunk([_text("All three are booked."), _call("probe_tool")])]]
                  + [lambda: []])
        client = _FakeClient(rounds)
        with _Events():
            out, hist = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert out == "All three are booked.", repr(out)
    assert hist[-1]["content"] == out


@check("Step0.1 a silent last round's final round carries the plain prompt (no answered clause)")
def _():
    _reset()
    client = _FakeClient(_calls_only(O._SYNTH_MAX_ROUNDS) + [lambda: [_Chunk([_text("Done.")])]])
    seen = _capture_contents(client)
    out, _ = _run(client)
    assert out == "Done."
    assert _last_user_text(seen[-1]) == O._FINAL_REPLY_PROMPT


@check("Step0.2 whitespace-only text beside calls counts as no text: plain final round, no blank-line prefix")
def _():
    _reset()
    rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
              + [lambda: [_Chunk([_text("  \n"), _call("probe_tool")])]]
              + [lambda: [_Chunk([_text("Here it is.")])]])
    client = _FakeClient(rounds)
    seen = _capture_contents(client)
    out, _ = _run(client)
    assert _last_user_text(seen[-1]) == O._FINAL_REPLY_PROMPT
    assert out == "  \nHere it is.", repr(out)    # the whitespace was already streamed; no "\n\n"


@check("Step0.2 whitespace-only text and an empty final reply: the fixed line, never a blank reply")
def _():
    _reset()
    rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
              + [lambda: [_Chunk([_text("   "), _call("probe_tool")])]]
              + [lambda: []])
    out, hist = _run(_FakeClient(rounds))
    assert out == "   " + O._NO_REPLY_LINE, repr(out)
    assert hist[-1]["content"] == O._NO_REPLY_LINE


@check("Step0.3 a final reply that repeats or pads what was shown is dropped; one that extends "
       "a preamble into the answer is kept")
def _():
    shown = "All three are booked for Friday."
    for final, dropped in (("All three are booked for Friday.", True),       # a repeat
                           ("all three are BOOKED — for Friday", True),      # normalised repeat
                           ("booked for Friday", True),                      # contained in it
                           ("All three are booked for Friday. Done.", True),  # pads it
                           ("(Nothing further.)", True), ("nothing", True), ("—", True),
                           ("All three are booked for Friday. Saturday could not be checked "
                            "because the calendar did not answer.", False),  # a real addition
                           ("Saturday is still unchecked.", False)):
        _reset()
        rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda: [_Chunk([_text(shown), _call("probe_tool")])]]
                  + [lambda f=final: [_Chunk([_text(f)])]])
        out, hist = _run(_FakeClient(rounds))
        # A kept reply that restates the shown text contributes only what follows it.
        tail = ("Saturday could not be checked because the calendar did not answer."
                if final.startswith(shown) else final)
        expect = shown if dropped else f"{shown}\n\n{tail}"
        assert out == expect, (final, out)
        assert hist[-1]["content"] == out
    # A reply that restates the shown preamble and goes on: only the new part is appended.
    for shown2, final, expect in (
            ("Let me check.", "Let me check. Saturday is free.",
             "Let me check.\n\nSaturday is free."),
            ("Let me check.", "let me CHECK — Saturday is free from two o'clock.",
             "Let me check.\n\nSaturday is free from two o'clock."),
            ("Let me check.", "Saturday is free, as I said: let me check the rest.",
             "Let me check.\n\nSaturday is free, as I said: let me check the rest.")):
        _reset()
        rounds = (_calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda s2=shown2: [_Chunk([_text(s2), _call("probe_tool")])]]
                  + [lambda f=final: [_Chunk([_text(f)])]])
        out, hist = _run(_FakeClient(rounds))
        assert out == expect, (final, out)
        assert hist[-1]["content"] == out
    # Nothing shown and a no-content final reply: the fixed line, never "nothing".
    _reset()
    out, _ = _run(_FakeClient(_calls_only(O._SYNTH_MAX_ROUNDS)
                              + [lambda: [_Chunk([_text("(nothing further)")])]]))
    assert out == O._NO_REPLY_LINE, out


@check("Step0.4 a round with no call whose only text is whitespace counts as no text: the "
       "fixed line")
def _():
    _reset()
    out, hist = _run(_FakeClient([lambda: [_Chunk([_call("probe_tool")])],
                                  lambda: [_Chunk([_text("  \n ")])]]))
    assert out == "  \n " + O._NO_REPLY_LINE, repr(out)
    assert hist[-1]["content"] == O._NO_REPLY_LINE
    _reset()
    out, _ = _run(_FakeClient([lambda: [_Chunk([_text("   ")])]]))
    assert out.endswith(O._NO_REPLY_LINE), repr(out)


@check("#10.1c round-1 text, rounds 2-4 silent, then the cap: final round runs after a blank line")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        rounds = ([lambda: [_Chunk([_text("Let me check."), _call("probe_tool")])]]
                  + _calls_only(O._SYNTH_MAX_ROUNDS - 1)
                  + [lambda: [_Chunk([_text("Friday is still unchecked.")])]])
        client = _FakeClient(rounds)
        with _Events() as ev:
            out, hist = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert client.models.calls == O._SYNTH_MAX_ROUNDS + 1, client.models.calls
    assert out == "Let me check.\n\nFriday is still unchecked.", repr(out)
    assert hist[-1]["content"] == out            # history records what was shown
    assert ev.kinds() == ["CHAIN_LIMIT_REACHED"]


@check("#10.2 a Physical Health follow-up in round 4 runs, and its result reaches the final round")
def _():
    _reset()
    ran = []
    schemas = _SCHEMAS + [{"name": "run_subagent", "description": "t", "input_schema": {
        "type": "object", "properties": {"agent_name": {"type": "string"}}}}]
    handlers = {**_HANDLERS,
                "run_subagent": lambda agent_name="", **k: ran.append(agent_name) or "PH: all clear"}
    seen = []
    sub = types.Part(function_call=types.FunctionCall(
        name="run_subagent", args={"agent_name": "physical_health"}))
    rounds = _calls_only(O._SYNTH_MAX_ROUNDS - 1) + [lambda: [_Chunk([sub])]] + [
        lambda: [_Chunk([_text("Reply.")])]]
    client = _FakeClient(rounds)
    real = client.models.generate_content_stream
    client.models.generate_content_stream = lambda model, contents, config: (
        seen.append(list(contents)) or real(model, contents, config))
    _as_agent("synthesizer")
    try:
        with _Events() as ev:
            out = "".join(O._run_gemini_native_stream(
                client, "fake-model", "system", "hello", schemas, handlers,
                history=[], max_iterations=O._SYNTH_MAX_ROUNDS))
    finally:
        _TR._set_current_agent(None)
    assert ran == ["physical_health"], ran
    responses = [p.function_response.response for c in seen[-1] for p in (c.parts or [])
                 if getattr(p, "function_response", None)]
    assert {"result": "PH: all clear"} in responses, responses
    assert "run_subagent(physical_health)" in ev.events[0][1]["detail"], ev.events
    assert out == "Reply."


@check("#10.3 a soft-deadline exit records no CHAIN_LIMIT_REACHED")
def _():
    _reset()
    _as_agent("synthesizer")
    real = O._past_soft_deadline
    O._past_soft_deadline = lambda: True
    try:
        client = _FakeClient([lambda: [_Chunk([_call("probe_tool")])],
                              lambda: [_Chunk([_text("Wrapped up.")])]])
        with _Events() as ev:
            out, _ = _run(client)
    finally:
        O._past_soft_deadline = real
        _TR._set_current_agent(None)
    assert out == "Wrapped up." and "CHAIN_LIMIT_REACHED" not in ev.kinds(), ev.events


@check("#10.4 a reply that ends with text in round 2 records nothing")
def _():
    _reset()
    _as_agent("synthesizer")
    try:
        client = _FakeClient([lambda: [_Chunk([_call("probe_tool")])],
                              lambda: [_Chunk([_text("Answer.")])]])
        with _Events() as ev:
            out, _ = _run(client)
    finally:
        _TR._set_current_agent(None)
    assert out == "Answer." and ev.kinds() == []


@check("#10.5 cap exhaustion under a non-Synthesizer agent records nothing")
def _():
    _reset()
    _as_agent("logistics")
    try:
        client = _FakeClient(_calls_only(O._SYNTH_MAX_ROUNDS) + [lambda: [_Chunk([_text("x")])]])
        with _Events() as ev:
            _run(client)
    finally:
        _TR._set_current_agent(None)
    assert ev.kinds() == []


@check("#10.6 the final round's request carries B4's consequence wording")
def _():
    assert "say so in one plain sentence" in O._FINAL_REPLY_PROMPT
    assert "never why, and never how you work" in O._FINAL_REPLY_PROMPT
    assert O._FINAL_REPLY_PROMPT.startswith("Your tool budget for this turn is spent.")


@check("#10.7 the event is written on a no-user-words turn too (not a refused type)")
def _():
    import tempfile
    from unittest import mock
    _reset()
    _as_agent("synthesizer")
    try:
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.object(_L, "_logs_dir", return_value=Path(tmp)), \
                T.turn_scope(user_turn=False):
            client = _FakeClient(_calls_only(O._SYNTH_MAX_ROUNDS) + [lambda: [_Chunk([_text("x")])]])
            _run(client)
            lines = (Path(tmp) / "quality_events.json").read_text().splitlines()
    finally:
        _TR._set_current_agent(None)
    assert len(lines) == 1 and '"CHAIN_LIMIT_REACHED"' in lines[0], lines


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
