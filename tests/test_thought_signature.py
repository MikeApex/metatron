"""
tests/test_thought_signature.py — an unsigned tool-call turn never goes back to
Vertex, so the exchange is not lost ([DB-0810-12]).

The bug: `_openai_compat_stream` rebuilds an assistant tool-call message out of
stream deltas when the blocking replay diverges. Stream deltas carry no
`thought_signature`, so that message is unsigned *by construction*; the next
request sends it back, Vertex 400s the whole request at "position 12", and the
user's exchange is never recorded. Five occurrences 08-04 → 08-09, four more
after, and one captured on 2026-08-15 naming the branch
(`src=stream_delta_fallback`).

What is asserted here:

  * an unsigned delta-reconstructed message never appears in a later request
  * the signed happy path is byte-identical — same message object, same tool turn
  * the same guard covers an *unsigned blocking replay*, which nothing had ever
    checked (the replay is the mitigation; it was assumed to return signed calls)
  * parallel tool calls are still dispatched in one turn, not serialised into N —
    porting `_openai_compat_loop`'s tc0-only workaround would have done exactly that
  * OpenAI/Ollama endpoints are untouched: they never demanded a signature and the
    original reconstruction is still what they get
  * the `_note_unsigned` ledger still fires on the fixed branch, so a future 400
    is still attributable
  * `_thought_signature_state()` classifies signed / unsigned / partial correctly

No network, no credentials: the OpenAI client is replaced with a scripted fake for
both the streaming and blocking calls.

Run:  python3 tests/test_thought_signature.py
"""

import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.orchestrator as orch  # noqa: E402

VERTEX_URL = "https://us-central1-aiplatform.googleapis.com/v1beta1/projects/p/locations/us-central1/endpoints/openapi/"

SCHEMAS = [
    {"name": "write_quality_event", "description": "", "input_schema": {"type": "object", "properties": {}}},
    {"name": "run_subagent", "description": "", "input_schema": {"type": "object", "properties": {}}},
]


# --- fakes ------------------------------------------------------------------

class _Fn:
    def __init__(self, name, arguments):
        self.name = name
        self.arguments = arguments


class _ToolCall:
    """A tool call as the OpenAI SDK hands it back, signature optional."""

    def __init__(self, id, name, arguments="{}", signature=None):
        self.id = id
        self.function = _Fn(name, arguments)
        self.extra_content = (
            {"google": {"thought_signature": signature}} if signature else None
        )


class _Message:
    """Stands in for ChatCompletionMessage — enough of it for this loop."""

    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls

    def model_copy(self, update=None):
        m = _Message(self.content, self.tool_calls)
        for k, v in (update or {}).items():
            setattr(m, k, v)
        return m


class _Delta:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class _ChunkChoice:
    def __init__(self, delta, finish_reason=None):
        self.delta = delta
        self.finish_reason = finish_reason


class _Chunk:
    def __init__(self, choices, usage=None):
        self.choices = choices
        self.usage = usage


class _RespChoice:
    def __init__(self, message):
        self.message = message


class _Response:
    def __init__(self, message):
        self.choices = [_RespChoice(message)]
        self.usage = None


def _tc_delta(index, id, name, arguments):
    return _Delta(tool_calls=[type("D", (), {
        "index": index, "id": id, "function": _Fn(name, arguments)})()])


def _stream_tool_turn(calls):
    """calls: list of (id, name, arguments) — a stream that ends in tool_calls."""
    chunks = [_Chunk([_ChunkChoice(_tc_delta(i, cid, name, args))])
              for i, (cid, name, args) in enumerate(calls)]
    chunks.append(_Chunk([_ChunkChoice(_Delta(), finish_reason="tool_calls")]))
    return chunks


def _stream_text_turn(text):
    return [_Chunk([_ChunkChoice(_Delta(content=text))]),
            _Chunk([_ChunkChoice(_Delta(), finish_reason="stop")])]


class FakeClient:
    """Scripted OpenAI client. `script` is consumed one create() call at a time.

    With `enforce_signatures`, it rejects a request the way Vertex does: any
    assistant message carrying function calls it has not signed is a 400 naming
    the position. That is the whole failure being fixed, so the fake reproduces it
    rather than only recording what was sent.
    """

    def __init__(self, script, enforce_signatures=False):
        self.script = list(script)
        self.calls = []          # (stream: bool, messages snapshot)
        self.enforce_signatures = enforce_signatures
        self.chat = type("C", (), {"completions": self})()

    def create(self, **kw):
        self.calls.append((bool(kw.get("stream")), list(kw["messages"])))
        if self.enforce_signatures:
            for pos, m in enumerate(kw["messages"]):
                has_calls = (m.get("tool_calls") if isinstance(m, dict)
                             else getattr(m, "tool_calls", None))
                if has_calls and orch._thought_signature_state(m) != "signed":
                    raise RuntimeError(
                        "Error code: 400 - Unable to submit request because it must "
                        f"include a thought_signature for the function call at position {pos}.")
        if not self.script:
            raise AssertionError("fake client ran out of scripted responses")
        return self.script.pop(0)

    # request bookkeeping
    def request_messages(self, n):
        return self.calls[n][1]

    @property
    def stream_turns(self):
        return sum(1 for streaming, _ in self.calls if streaming)


def _run(script, base_url=VERTEX_URL, handlers=None, enforce_signatures=False):
    """Drive _openai_compat_stream against a fake client.

    Returns (client, text, dispatched, failures). `failures` captures what would
    have reached _log_api_failure — asserted on directly, and kept off disk, since
    the real one writes a quality event into the live persona tree.
    """
    dispatched = []
    failures = []

    def _record(name):
        def fn(**kw):
            dispatched.append(name)
            return "ok"
        return fn

    handlers = handlers or {s["name"]: _record(s["name"]) for s in SCHEMAS}
    client = FakeClient(script, enforce_signatures=enforce_signatures)
    orig_client, orig_log = orch.openai.OpenAI, orch._log_api_failure
    orch.openai.OpenAI = lambda **kw: client
    orch._log_api_failure = lambda loop, model, exc, **kw: failures.append(
        (loop, str(exc), kw.get("extra", "")))
    try:
        text = "".join(orch._openai_compat_stream(
            "sys", "hello", SCHEMAS, handlers,
            api_key="k", base_url=base_url, model="google/gemini-3.1-pro-preview",
        ))
    finally:
        orch.openai.OpenAI, orch._log_api_failure = orig_client, orig_log
    return client, text, dispatched, failures


def _has_tool_call_part(messages):
    """True if any message carries function-call content Vertex would want signed."""
    for m in messages:
        if isinstance(m, dict):
            if m.get("tool_calls") or m.get("role") == "tool":
                return True
        elif getattr(m, "tool_calls", None):
            return True
    return False


class _CaptureProbe(logging.Handler):
    def __init__(self):
        super().__init__()
        self.lines = []

    def emit(self, record):
        if "[signature_probe]" in record.getMessage():
            self.lines.append(record.getMessage())


# --- the branch that lost the exchange --------------------------------------

def test_unsigned_delta_message_never_reaches_a_later_request():
    """The [DB-0810-12] failure: pos=12 src=stream_delta_fallback."""
    client, text, dispatched, _ = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}")]),
        _Response(_Message(content="thinking out loud", tool_calls=None)),  # replay diverges
        _stream_text_turn("Here is your answer."),
    ])
    assert text == "Here is your answer.", text
    assert dispatched == ["write_quality_event"], dispatched
    later = client.request_messages(2)      # the request that used to 400
    assert not _has_tool_call_part(later), (
        f"an unsigned function-call part survived into the next request: {later}")
    assert any(isinstance(m, dict) and m.get("role") == "user"
               and "[tool results]" in (m.get("content") or "")
               for m in later), later


def test_the_exchange_is_not_lost_against_a_rejecting_endpoint():
    """The user-visible harm was a dropped exchange, not a log line.

    The fake enforces signatures here, so this is the end-to-end shape of the bug:
    before the fix the second request 400s and nothing reaches the user.
    """
    _, text, dispatched, failures = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}")]),
        _Response(_Message(content=None, tool_calls=None)),
        _stream_text_turn("You logged that."),
    ], enforce_signatures=True)
    assert not failures, f"the endpoint rejected a request: {failures}"
    assert text == "You logged that."
    assert dispatched == ["write_quality_event"]


def test_a_rejecting_endpoint_still_accepts_the_signed_path():
    """The enforcement above is real, not vacuous — a signed turn passes it."""
    signed = _Message(content=None, tool_calls=[
        _ToolCall("c1", "write_quality_event", "{}", signature="sig-abc")])
    _, text, _, failures = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}")]),
        _Response(signed),
        _stream_text_turn("Signed and sent."),
    ], enforce_signatures=True)
    assert not failures, failures
    assert text == "Signed and sent."


def test_parallel_dispatch_is_not_serialised():
    """A tc0-only port would re-request the rest — N calls become N turns."""
    client, text, dispatched, _ = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}"),
                           ("c2", "run_subagent", "{}")]),
        _Response(_Message(content=None, tool_calls=None)),
        _stream_text_turn("Done."),
    ])
    assert sorted(dispatched) == ["run_subagent", "write_quality_event"], dispatched
    assert client.stream_turns == 2, (
        f"{client.stream_turns} model turns for 2 parallel calls — the loop was serialised")


def test_ledger_still_fires_on_the_fixed_branch():
    """Instrumentation survives the fix, so a future 400 is still attributable."""
    probe = _CaptureProbe()
    orch.logger.addHandler(probe)
    try:
        _run([
            _stream_tool_turn([("c1", "write_quality_event", "{}")]),
            _Response(_Message(content=None, tool_calls=None)),
            _stream_text_turn("ok"),
        ])
    finally:
        orch.logger.removeHandler(probe)
    assert probe.lines, "the _note_unsigned ledger stopped recording this branch"
    assert "src=stream_delta_fallback:neutralized" in probe.lines[0], probe.lines
    assert "tools=write_quality_event" in probe.lines[0], probe.lines


# --- the happy path must not move -------------------------------------------

def test_signed_happy_path_is_unchanged():
    signed = _Message(content=None, tool_calls=[
        _ToolCall("c1", "write_quality_event", "{}", signature="sig-abc")])
    client, text, dispatched, _ = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}")]),
        _Response(signed),
        _stream_text_turn("All good."),
    ])
    assert text == "All good."
    assert dispatched == ["write_quality_event"]
    later = client.request_messages(2)
    assert signed in later, "the signed Vertex message object was not sent back verbatim"
    assert any(isinstance(m, dict) and m.get("role") == "tool" for m in later), later
    assert not any(isinstance(m, dict) and "[tool results]" in (m.get("content") or "")
                   for m in later), "the guard fired on a signed turn"


def test_signed_parallel_replay_still_reduces_to_tc0():
    """The known Vertex parallel-call bug: only tc0 is signed, and only tc0 is sent."""
    signed = _Message(content=None, tool_calls=[
        _ToolCall("c1", "write_quality_event", "{}", signature="sig-abc"),
        _ToolCall("c2", "run_subagent", "{}"),
    ])
    client, _, dispatched, _ = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}"),
                           ("c2", "run_subagent", "{}")]),
        _Response(signed),
        _stream_text_turn("ok"),
    ])
    assert dispatched == ["write_quality_event"], dispatched
    later = client.request_messages(2)
    appended = [m for m in later if getattr(m, "tool_calls", None)]
    assert len(appended) == 1 and len(appended[0].tool_calls) == 1, appended


def test_openai_endpoint_keeps_the_original_reconstruction():
    """No Google endpoint, no signature demand — behaviour must not change."""
    client, text, dispatched, _ = _run([
        _stream_tool_turn([("c1", "write_quality_event", "{}")]),
        _Response(_Message(content=None, tool_calls=None)),
        _stream_text_turn("fine"),
    ], base_url=None)
    assert text == "fine"
    later = client.request_messages(2)
    assert _has_tool_call_part(later), "the OpenAI path lost its tool-call turn"
    assert any(isinstance(m, dict) and m.get("role") == "tool" for m in later), later


# --- the candidate nothing had ever checked ---------------------------------

def test_unsigned_blocking_replay_is_also_neutralised():
    """The replay is the mitigation; nothing verified it returns signed calls."""
    unsigned = _Message(content=None, tool_calls=[
        _ToolCall("c1", "write_quality_event", "{}")])   # no signature
    probe = _CaptureProbe()
    orch.logger.addHandler(probe)
    try:
        client, text, dispatched, _ = _run([
            _stream_tool_turn([("c1", "write_quality_event", "{}")]),
            _Response(unsigned),
            _stream_text_turn("ok"),
        ])
    finally:
        orch.logger.removeHandler(probe)
    assert dispatched == ["write_quality_event"], "the tool stopped running"
    later = client.request_messages(2)
    assert not _has_tool_call_part(later), later
    assert probe.lines and "blocking_replay[unsigned]:neutralized" in probe.lines[0], probe.lines


# --- the classifier ---------------------------------------------------------

def test_thought_signature_state_classifies():
    sig = lambda i: _ToolCall(f"c{i}", "t", "{}", signature="s")
    bare = lambda i: _ToolCall(f"c{i}", "t", "{}")
    assert orch._thought_signature_state(_Message(tool_calls=[sig(1)])) == "signed"
    assert orch._thought_signature_state(_Message(tool_calls=[bare(1)])) == "unsigned"
    assert orch._thought_signature_state(_Message(tool_calls=[sig(1), sig(2)])) == "signed"
    assert orch._thought_signature_state(_Message(tool_calls=[sig(1), bare(2)])) == "signed=1/2"
    assert orch._thought_signature_state(_Message(tool_calls=[bare(1), bare(2)])) == "unsigned"
    assert orch._thought_signature_state(_Message(content="hi")) == "n/a"


def test_thought_signature_state_reads_the_delta_reconstructed_dict():
    """The exact shape the fallback branch builds — must read as unsigned, not n/a."""
    reconstructed = {"role": "assistant", "content": None, "tool_calls": [
        {"id": "c1", "type": "function",
         "function": {"name": "write_quality_event", "arguments": "{}"}}]}
    assert orch._thought_signature_state(reconstructed) == "unsigned"
    assert orch._thought_signature_state({"role": "assistant", "content": "x"}) == "n/a"


def test_thought_signature_state_never_raises():
    """Instrumentation must not cost a live conversation its turn."""
    class Hostile:
        @property
        def tool_calls(self):
            raise RuntimeError("boom")
    assert orch._thought_signature_state(Hostile()) == "unknown"
    assert orch._thought_signature_state(None) == "n/a"


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print()
    print(f"{len(failures)} failed" if failures else "all passed")
    sys.exit(1 if failures else 0)
