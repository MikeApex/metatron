"""
tests/test_turn_source_marker.py — a turn started from a headset button is
distinguishable from one the user typed, all the way into the trace.

**Why this is a test and not a manual check.** A headset press starts a full pipeline
turn — Coordinator, specialists and Synthesizer, a median ~26k input tokens. It is the
only turn origin that can happen *by accident*, in a pocket, and once a trace is written
nothing else in it separates a stray press from a real question. The plan that added
headset mode names this as the one cost it cannot otherwise see, and notes that the field
cannot be back-filled: a turn already taken has no record of how it started.

**The failure this guards against is a half-wired field, not a wrong value.** The client
can send `source` and the server can ignore it, or the server can read it and never pass
it on, or the orchestrator can accept it and never hand it to the trace. Each of those
leaves every row reading "ui" forever, with nothing anywhere reporting a problem — the
field would look implemented and measure nothing. So the chain itself is asserted,
link by link, not just the endpoints.

Standalone runner (no pytest dependency), matching the convention of the other tests.
"""

import ast
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print(f"  FAIL  {name}" + (f"\n        {detail}" if detail else ""))


# ---------------------------------------------------------------------------
# 1. The trace stores and emits it, and defaults to "ui"
# ---------------------------------------------------------------------------
print("\nTrace storage")

from core import trace as _tr  # noqa: E402

t = _tr.start_request_trace("hello", "mike", is_proactive=False, source="headset")
check("a headset turn is stored as headset", t.source == "headset", f"got {t.source!r}")
check("and survives serialisation",
      _tr._serialize(t, 10).get("source") == "headset")

t_default = _tr.start_request_trace("hello", "mike")
check("a turn with no source given defaults to ui",
      t_default.source == "ui", f"got {t_default.source!r}")
_tr.set_trace(None)


# ---------------------------------------------------------------------------
# 2. The client cannot write arbitrary text into the trace
# ---------------------------------------------------------------------------
print("\nInput normalisation")

from core.server import normalise_turn_source  # noqa: E402

check("headset is accepted", normalise_turn_source("headset") == "headset")
check("ui is accepted", normalise_turn_source("ui") == "ui")
check("an unknown string falls back to ui",
      normalise_turn_source("scheduler") == "ui")
check("a missing field falls back to ui", normalise_turn_source(None) == "ui")
# Not decoration: this value is written verbatim into every trace row for the turn.
check("a non-string cannot get through",
      normalise_turn_source({"x": 1}) == "ui")
check("a long injected string cannot get through",
      normalise_turn_source("headset" * 500) == "ui")


# ---------------------------------------------------------------------------
# 3. The chain is actually wired — the half-implemented case
# ---------------------------------------------------------------------------
print("\nEnd-to-end wiring")

from core.orchestrator import run_pipeline_session_stream  # noqa: E402

sig = inspect.signature(run_pipeline_session_stream)
check("the streaming pipeline accepts a source", "source" in sig.parameters)
check("and defaults it to ui, so existing callers stay legible",
      sig.parameters["source"].default == "ui"
      if "source" in sig.parameters else False)

sig_trace = inspect.signature(_tr.start_request_trace)
check("start_request_trace accepts a source", "source" in sig_trace.parameters)

# The two call sites, read from source. A parameter that exists and is never passed
# is the exact half-wired failure this file is here to catch, and it cannot be seen
# from a signature.
server_src = (ROOT / "core" / "server.py").read_text()
orch_src = (ROOT / "core" / "orchestrator.py").read_text()


def passes_source_kwarg(source_text, callee):
    """True if some call to `callee` passes a keyword argument named `source`."""
    for node in ast.walk(ast.parse(source_text)):
        if not isinstance(node, ast.Call):
            continue
        fn = node.func
        name = fn.attr if isinstance(fn, ast.Attribute) else getattr(fn, "id", None)
        if name != callee:
            continue
        if any(kw.arg == "source" for kw in node.keywords):
            return True
    return False


check("the server hands the source to the pipeline",
      passes_source_kwarg(server_src, "run_pipeline_session_stream"),
      "core/server.py calls the pipeline without source= — every row will read 'ui'")
check("the pipeline hands the source to the trace",
      passes_source_kwarg(orch_src, "start_request_trace"),
      "core/orchestrator.py starts the trace without source= — the field is inert")
check("the server normalises before passing it on",
      "normalise_turn_source(" in server_src,
      "raw client input would reach the trace unchecked")

# Every function that READS `source` must also BIND it. This is not hypothetical
# tidiness: on 2026-09-24 a parallel session split run_pipeline_session_stream into a
# wrapper plus _run_pipeline_session_stream_inner, leaving the `source=source` call in
# the inner half while the parameter stayed on the outer. `source` became an unbound
# name — a NameError on every streaming turn, i.e. the main user path.
#
# Nothing above caught it. The checks either side are structural ("some call passes
# source=") and both still passed against broken code, and `py_compile` does not
# execute, so the QA sweep passed too. A name is only safe if it is bound in the same
# scope that reads it, and that is what this asserts.
orch_tree = ast.parse(orch_src)
unbound = []
for fn in ast.walk(orch_tree):
    if not isinstance(fn, ast.FunctionDef):
        continue
    reads = [n.lineno for n in ast.walk(fn)
             if isinstance(n, ast.Name) and n.id == "source" and isinstance(n.ctx, ast.Load)]
    if not reads:
        continue
    bound = {a.arg for a in fn.args.args} | {a.arg for a in fn.args.kwonlyargs}
    bound |= {t.id for n in ast.walk(fn) if isinstance(n, ast.Assign)
              for t in n.targets if isinstance(t, ast.Name)}
    bound |= {n.target.id for n in ast.walk(fn)
              if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)}
    if "source" not in bound:
        unbound.append(f"{fn.name}() reads `source` at line(s) {reads} but never binds it")

check("every function reading `source` also binds it",
      not unbound,
      "; ".join(unbound) or "")


# ---------------------------------------------------------------------------
# 4. The client sends it
# ---------------------------------------------------------------------------
print("\nClient")

client = (ROOT / "static" / "index.html").read_text()
check("the send frame carries a source field", "source:" in client)
check("and reports headset only when headset mode is armed",
      "headsetMode ? 'headset' : 'ui'" in client,
      "a hardcoded value would mark every turn the same and measure nothing")


print(f"\n{passed} passed, {failed} failed, {passed + failed} total")
sys.exit(1 if failed else 0)
