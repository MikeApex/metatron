"""
tests/test_session_shape_baseline.py — the one-off Stage 2 baseline script counts exactly,
writes nothing, and never prints the clarification text.

Synthetic traces in a tmp root; no model, no network.

Run:  python3 tests/test_session_shape_baseline.py   (or pytest)
"""

from __future__ import annotations

import io
import json
import sys
import tempfile
from contextlib import redirect_stdout
from datetime import date
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import session_shape_baseline as B  # noqa: E402

DAY = "2026-11-20"
SECRET = "Ella or Bella — which one?"


def _synth(text: str, tool_rounds: int = 0) -> dict:
    turns = [{"turn": i + 1, "output_text": "", "tool_calls": [{"name": "run_subagent"}]}
             for i in range(tool_rounds)]
    turns.append({"turn": tool_rounds + 1, "output_text": text, "tool_calls": []})
    return {"agent": "synthesizer", "turns": turns, "subagents": []}


def _coord(text: str) -> dict:
    return {"agent": "coordinator", "turns": [{"output_text": text, "tool_calls": []}],
            "subagents": []}


def _trace(*agents, proactive=False, user_input="hi", annotations=None) -> dict:
    t = {"is_proactive": proactive, "user_input": user_input, "pipeline": list(agents)}
    if annotations:
        t["annotations"] = annotations
    return t


TRACES = [
    _trace(_synth('Reply.[CONTEXT]{"open_threads": []}[/CONTEXT]', tool_rounds=4)),
    _trace(_synth('Reply.[CONTEXT]```json\n{"open_threads": []}\n```[/CONTEXT]')),
    _trace(_synth('R.[CONTEXT]{"open_threads": ["a", "b"], "patterns": [oops not json], '
                  '"follow_ups": ["call"]}[/CONTEXT]')),
    _trace(_synth("R.[CONTEXT]nothing like json at all[/CONTEXT]")),
    _trace(_synth("Plain reply, no block.")),
    # M7: one annotated (shadow), two pre-deploy fallbacks.
    _trace(_coord("x"), _synth("ok"), annotations={"clarification": {
        "value_shape": "free text", "chars": len(SECRET), "user_turn": True,
        "would_hold": ["logistics", "relationships"], "would_skip_writes": [],
        "synth_redispatched": ["logistics"]}}),
    _trace(_coord("CLARIFICATION_NEEDED: none\n"), _synth("ok")),
    _trace(_coord(f"CLARIFICATION_NEEDED: {SECRET}\n"), _synth("ok")),
    # A scheduled brief with Physical Health only.
    _trace({"agent": "physical_health", "turns": [], "subagents": []}, _synth("ok"),
           proactive=True, user_input="BRIEF PROMPT"),
]


def _root(tmp: Path) -> Path:
    tdir = tmp / "data" / "personas" / "zz_p" / "traces"
    tdir.mkdir(parents=True)
    (tdir / f"{DAY}.jsonl").write_text("\n".join(json.dumps(t) for t in TRACES) + "\n")
    ldir = tmp / "data" / "personas" / "zz_p" / "logs"
    ldir.mkdir(parents=True)
    ldir.joinpath("quality_events.json").write_text("\n".join(json.dumps(e) for e in [
        {"timestamp": f"{DAY}T10:00:00Z", "event_type": "CONTEXT_BLOCK_UNPARSED"},
        {"timestamp": f"{DAY}T10:00:00Z", "event_type": "ROUTING_MISS", "scheduled": True},
        {"timestamp": "2026-10-01T10:00:00Z", "event_type": "ROUTING_MISS"},
    ]) + "\n")
    return tmp


def _run(tmp: Path) -> str:
    buf = io.StringIO()
    with mock.patch("core.orchestrator.session_kind",
                    lambda text, persona=None: "morning_brief" if text == "BRIEF PROMPT" else None), \
            redirect_stdout(buf):
        assert B.main(["--persona", "zz_p", "--since", DAY, "--until", DAY,
                       "--root", str(tmp)]) == 0
    return buf.getvalue()


def _snapshot(root: Path) -> dict:
    return {str(p): p.stat().st_mtime_ns for p in root.rglob("*")}


def test_counts_exact():
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(_root(Path(tmp)))
    assert "- clean: 1" in out, out
    assert "- repaired:fences/prose stripped: 1" in out
    assert "- partial salvage: 1" in out
    assert "- unrecoverable: 1" in out
    assert "- absent: 5" in out            # one plain reply + four "ok" replies
    assert "lossy (partial salvage + unrecoverable): 2 of 9" in out
    assert "CONTEXT_BLOCK_UNPARSED events: 1" in out
    assert "replies reaching 4 rounds: 1" in out
    assert "ROUTING_MISS events: 1 (tagged scheduled: 1)" in out
    assert "user turns: 8; passing the parser: 2" in out
    assert "- shape free text: 2" in out and "- shape null-ish: 1" in out
    assert "read from the Coordinator output (pre-annotation): 2" in out
    assert "mean would_hold size: 2.00" in out
    assert "with synth_redispatched non-empty: 1 of 1" in out
    assert "- morning_brief: 1 runs; mental_wellbeing 0, physical_health 1" in out


def test_writes_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        root = _root(Path(tmp))
        before = _snapshot(root)
        _run(root)
        assert _snapshot(root) == before


def test_never_prints_clarification_text():
    with tempfile.TemporaryDirectory() as tmp:
        out = _run(_root(Path(tmp)))
    assert SECRET not in out and "Ella" not in out and "Bella" not in out


def test_docstring_names_retirement():
    assert "deleted in the commit that records the #4 decision" in B.__doc__


if __name__ == "__main__":
    failures = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:  # noqa: BLE001
                failures += 1
                print(f"  FAIL  {name} — {type(exc).__name__}: {exc}")
    print(f"\n{'all passed' if not failures else f'{failures} failed'}")
    sys.exit(1 if failures else 0)
