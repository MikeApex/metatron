"""
tests/test_pattern_report.py — the weekly Pattern Miner's fixed steps run as code, and code writes
its report (instructions-to-code Stage 4, 4e: #20 and M16).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #20 tests 1–7.
Offline: no model call (the OpenAI client and every run_session_* entry point are stubbed), no
network, the embedder is never loaded; the persona tree is a temp directory
(tests/support/stage3_fixtures.sandbox).

    python3 tests/test_pattern_report.py
"""

from __future__ import annotations

import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")
os.environ.setdefault("HF_HUB_OFFLINE", "1")

import core.orchestrator as ORC  # noqa: E402
import core.prefetch as PF  # noqa: E402
import core.trace as TR  # noqa: E402
import tools.context_tracker as CT  # noqa: E402
import tools.pattern_report as PR  # noqa: E402
import tools.wisdom as W  # noqa: E402
from tests.support.stage3_fixtures import PERSONA, patched, sandbox  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except Exception as e:  # noqa: BLE001
            import traceback
            _results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc()}"))
        return fn
    return wrap


TODAY = date.today()

REPLY = """## 7-day

[EVIDENCE] Logged sleep_hours: 5.5 on three weekdays; "felt flat all afternoon" on each.
[OBSERVATION] Short-sleep days are followed by a flat afternoon in the user's own words.
[HYPOTHESIS] This suggests the afternoon dip may track sleep debt more than workload.
[CONFIDENCE] 7 days, trailing window — weak.
[ACTION] Ask whether the dip shows up after a long night too.

## 30-day

[EVIDENCE] Exercise logged 11 of 30 days; mood "positive" on 9 of those 11.
[OBSERVATION] Exercise days carry a positive mood far more often than other days.
[HYPOTHESIS] Movement may be lifting the day, or good days may invite movement.
[CONFIDENCE] 30 days, trailing window, moderate.
[ACTION] Suggest a two-week experiment: a short walk on low days.

**[EVIDENCE]** Writing sessions logged on 6 mornings, none in the evenings.
**[OBSERVATION]** All logged writing happens before noon.
**[HYPOTHESIS]** Mornings may be the protected window worth defending.
**[CONFIDENCE]** strong — 30 days, every instance.
**[ACTION]** Raise keeping two mornings a week clear.

Merged wisdom: sleep_debt_a into sleep_debt.
"""


def _rec(*calls):
    """An agent record whose turns carry the given (name, result, ok) tool calls."""
    rec = TR.AgentRecord(agent="pattern_miner", provider="gemini", model="m")
    for i, (name, result, ok) in enumerate(calls, 1):
        TR.record_tool_call(rec, i, name, {}, result, 1.0, ok=ok)
    return rec


def _insights(sb) -> list[Path]:
    d = sb["data"] / "insights"
    return sorted(d.glob("*.json")) if d.is_dir() else []


def _events(sb) -> list[dict]:
    p = sb["data"] / "logs" / "quality_events.json"
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


def _seed_tracker(sb) -> dict:
    seed = {
        "last_session": "2026-01-02",
        "open_threads": [{"text": "chase the plumber quote", "added": TODAY.isoformat()}],
        "patterns": ["writing stalls when sleep is short"],
        "follow_ups": ["ask how the chapter went"],
        "held_items": [{"text": "Held: SLEEP_POOR — surface when mood lifts",
                        "held_since": (TODAY - timedelta(days=4)).isoformat()}],
        "clinical_threads": [{"flag": "MEDICATION_MISSED_CRITICAL", "tier": 1,
                              "raised": TODAY.isoformat(), "status": "watch", "note": "seeded"}],
    }
    (sb["data"] / "context.json").write_text(json.dumps(seed))
    return seed


# --- 1. a valid reply is parsed and written once -----------------------------------------------

@check("1. a three-block final reply gives a parsed report, written once, with its notes kept")
def _():
    with sandbox() as sb:
        status = PR.write_from_reply(REPLY, _rec(), PERSONA, today=TODAY)
        files = _insights(sb)
        assert len(files) == 1 and files[0].name == f"{TODAY.isoformat()}.json", (files, status)
        report = json.loads(files[0].read_text())
        assert not _events(sb)
    obs = report["observations"]
    assert len(obs) == 3, obs
    assert [o["scale"] for o in obs] == ["7-day", "30-day", "30-day"], obs
    assert [o["confidence_level"] for o in obs] == ["weak", "moderate", "strong"], obs
    assert obs[2]["observation"] == "All logged writing happens before noon.", obs[2]
    assert obs[0]["evidence"].startswith("Logged sleep_hours"), obs[0]
    assert set(obs[0]) >= {"evidence", "observation", "hypothesis", "confidence", "action"}
    assert report["date"] == TODAY.isoformat() and "written_by" in report
    assert "Merged wisdom" in report.get("notes", ""), report
    assert "Merged wisdom" not in obs[2]["action"], obs[2]


# --- 2. the run already wrote it ---------------------------------------------------------------

@check("2. when the run already called write_insight_report, code writes no second report")
def _():
    with sandbox() as sb:
        rec = _rec(("write_insight_report", "Insight report written: x", True))
        status = PR.write_from_reply(REPLY, rec, PERSONA, today=TODAY)
        assert _insights(sb) == [] and "nothing written" in status, status
        # A failed call by the run is not a report: code writes from the reply.
        rec = _rec(("write_insight_report", "Error: bad content", False))
        PR.write_from_reply(REPLY, rec, PERSONA, today=TODAY)
        assert len(_insights(sb)) == 1


# --- 3. exhaustion: one tools-off round ---------------------------------------------------------

class _Fake:
    """A stand-in openai.OpenAI: `tool_rounds` tool-call responses, then a text reply."""

    def __init__(self, tool_rounds: int, final_text: str):
        self.calls: list[dict] = []
        self.tool_rounds = tool_rounds
        self.final_text = final_text
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def __call__(self, *a, **k):
        return self

    def _create(self, **kw):
        self.calls.append(kw)
        if len(self.calls) <= self.tool_rounds:
            tc = SimpleNamespace(id=f"c{len(self.calls)}", function=SimpleNamespace(
                name="read_recent_insights", arguments="{}"))
            msg = SimpleNamespace(content=None, tool_calls=[tc])
            choice = SimpleNamespace(finish_reason="tool_calls", message=msg)
        else:
            msg = SimpleNamespace(content=self.final_text, tool_calls=None)
            choice = SimpleNamespace(finish_reason="stop", message=msg)
        return SimpleNamespace(choices=[choice], usage=None)


_SCHEMA = [{"name": "read_recent_insights", "description": "x",
            "input_schema": {"type": "object", "properties": {}, "required": []}}]
_HANDLERS = {"read_recent_insights": lambda **k: '{"tool": "result body"}'}


def _loop(fake, rec=None, handlers=None, **kw):
    TR._set_current_agent(rec)
    try:
        with patched([(ORC.openai, "OpenAI", fake)]):
            return ORC._openai_compat_loop("sys", "go", _SCHEMA, dict(handlers or _HANDLERS),
                                           api_key="k", base_url="https://example.googleapis.com",
                                           model="m", **kw)
    finally:
        TR._set_current_agent(None)


@check("3. exhaustion: 8 tool rounds, then exactly one call with no tools and the final prompt; "
       "its reply is returned")
def _():
    fake = _Fake(8, REPLY)
    rec = _rec()
    got = _loop(fake, rec, final_round=True, final_prompt=PR.FINAL_PROMPT)
    assert rec.reply_source == "model", rec.reply_source
    assert len(fake.calls) == 9, len(fake.calls)
    assert all("tools" in c for c in fake.calls[:8])
    last = fake.calls[8]
    assert "tools" not in last, last.keys()
    assert last["messages"][-1] == {"role": "user", "content": PR.FINAL_PROMPT}
    assert got == REPLY.strip()


@check("3b. pin: final_round=False (every other caller) returns the last tool result, unchanged")
def _():
    fake = _Fake(8, REPLY)
    rec = _rec()
    got = _loop(fake, rec)
    assert len(fake.calls) == 8 and got == '{"tool": "result body"}', (len(fake.calls), got)
    assert rec.reply_source == "tool_result", rec.reply_source
    import inspect
    sig = inspect.signature(ORC._openai_compat_loop)
    assert sig.parameters["final_round"].default is False
    assert inspect.signature(ORC.run_session_gemini).parameters["final_round"].default is False


@check("3c. _run_single_agent sets the final round for pattern_miner only — on the cloud "
       "(Gemini), OpenAI and local (Ollama) routes alike; the local loop hands its text back")
def _():
    seen: dict[tuple[str, str], dict] = {}

    def fake(route):
        def run(system_prompt, user_input, tool_schemas, tool_handlers, **kw):
            seen[(route, TR.get_current_agent().agent)] = kw
            return "done"
        return run
    with sandbox(), patched([(ORC, "run_session_gemini", fake("gemini")),
                             (ORC, "run_session_openai", fake("openai")),
                             (ORC, "run_session_ollama", fake("ollama"))]):
        for route in ("gemini", "openai", "ollama"):
            for agent in ("pattern_miner", "goals_interviewer"):
                ORC._run_single_agent(agent, "x", persona=PERSONA, provider=route,
                                      model_override="m")
    for route in ("gemini", "openai", "ollama"):
        pm, other = seen[(route, "pattern_miner")], seen[(route, "goals_interviewer")]
        assert pm.get("final_round") is True and pm.get("final_prompt") == PR.FINAL_PROMPT, route
        assert "final_round" not in other and "return_text" not in other, (route, other)
    assert seen[("ollama", "pattern_miner")].get("return_text") is True
    assert seen[("gemini", "pattern_miner")]["max_output_tokens"] >= 16384      # review C


@check("3d. the local Ollama loop: 8 tool rounds, then one call with no tools; its text is "
       "returned and recorded as a model reply")
def _():
    calls: list[dict] = []

    def chat(**kw):
        calls.append(kw)
        if kw.get("stream"):
            tc = SimpleNamespace(function=SimpleNamespace(name="read_recent_insights",
                                                          arguments={}))
            chunk = SimpleNamespace(message=SimpleNamespace(tool_calls=[tc], content=None),
                                    prompt_eval_count=1, eval_count=1, done_reason="stop")
            return iter([chunk])
        return SimpleNamespace(message=SimpleNamespace(content="<think>x</think>" + REPLY),
                               done_reason="stop", prompt_eval_count=1, eval_count=1)
    import ollama
    rec = _rec()
    TR._set_current_agent(rec)
    try:
        with patched([(ollama, "chat", chat)]):
            got = ORC.run_session_ollama("sys", "go", _SCHEMA, dict(_HANDLERS),
                                         final_round=True, final_prompt=PR.FINAL_PROMPT,
                                         return_text=True)
    finally:
        TR._set_current_agent(None)
    assert len(calls) == 9 and "tools" not in calls[8], [sorted(c) for c in calls[8:]]
    assert calls[8]["messages"][-1]["content"].endswith(PR.FINAL_PROMPT)
    assert got == REPLY.strip() and rec.reply_source == "model"


@check("3d2. the local Ollama loop out of rounds WITHOUT a final round returns the last model "
       "text, or \"\" if none — it no longer raises")
def _():
    import ollama

    def make_chat(texts):
        calls: list[dict] = []

        def chat(**kw):
            calls.append(kw)
            n = len(calls)
            tc = SimpleNamespace(function=SimpleNamespace(name="read_recent_insights",
                                                          arguments={}))
            chunk = SimpleNamespace(message=SimpleNamespace(tool_calls=[tc],
                                                            content=texts.get(n)),
                                    prompt_eval_count=1, eval_count=1, done_reason="stop")
            return iter([chunk])
        return chat, calls
    for texts, expect in (({2: "Checking the logs.", 5: "Now the wisdom store."},
                           "Now the wisdom store."), ({}, "")):
        chat, calls = make_chat(texts)
        rec = _rec()
        TR._set_current_agent(rec)
        try:
            with patched([(ollama, "chat", chat)]):
                got = ORC.run_session_ollama("sys", "go", _SCHEMA, dict(_HANDLERS))
        finally:
            TR._set_current_agent(None)
        assert len(calls) == 8 and got == expect, (len(calls), got)
        assert rec.reply_source == ("model" if expect else "none"), rec.reply_source


@check("3e. on the local route the Pattern Miner's block is held to local_cap_chars; the cloud "
       "route is not")
def _():
    big = {k: (lambda kind: (lambda agent, e, ctx: (f"{kind} heading", "x" * 30000, False)))(k)
           for k in PF._READERS}
    cap = int(PF.load_config()["local_cap_chars"])
    assert cap == 16000
    TR.start_request_trace("weekly", PERSONA, is_proactive=True)
    TR.get_trace().scheduled_job = "weekly_pattern_miner"
    try:
        with sandbox(), patched([(PF, "_READERS", big)]):
            local = PF.build("pattern_miner", "d", "", PERSONA, local=True)
            cloud = PF.build("pattern_miner", "d", "", PERSONA)
    finally:
        TR.set_trace(None)
    assert len(local) <= cap + 400 and "cut to fit the local model" in local, len(local)
    assert len(cloud) > 6 * 19000, len(cloud)
    seen: dict = {}
    with sandbox(), patched([(PF, "build", lambda *a, **k: seen.update(k) or ""),
                             (ORC, "run_session_ollama", lambda *a, **k: "")]):
        ORC._run_single_agent("pattern_miner", "x", persona=PERSONA, provider="ollama",
                              model_override="m")
    assert seen.get("local") is True, seen


# --- 4. an invalid reply writes nothing ---------------------------------------------------------

@check("4. a JSON tool-result body, an 'Error…' string and prose with no [EVIDENCE] block each "
       "write nothing, keep the previous report and file one PATTERN_REPORT_MISSING event")
def _():
    with sandbox() as sb:
        prev = sb["data"] / "insights"
        prev.mkdir(parents=True)
        old = prev / "2026-08-30.json"
        old.write_text(json.dumps({"date": "2026-08-30", "observations": []}))
        before = old.read_text()
        bad = ('{"entries": [], "total": 0}', "Error: tool failed",
               "Log written for today.", "",
               "Here is what I found: sleep looks short this week. [CONFIDENCE] weak")
        for i, reply in enumerate(bad, 1):
            status = PR.write_from_reply(reply, _rec(), PERSONA, today=TODAY)
            assert status.startswith("no report"), (reply, status)
            assert _insights(sb) == [old] and old.read_text() == before
            ev = _events(sb)
            assert len(ev) == i and ev[-1]["event_type"] == "PATTERN_REPORT_MISSING", ev
            assert ev[-1]["source_agent"] == "pattern_miner"
            assert "2026-08-30" in ev[-1]["detail"], ev[-1]


@check("4b. a reply cut off at the output ceiling is never written (event reason: truncated)")
def _():
    with sandbox() as sb:
        rec = _rec()
        rec.reply_source, rec.reply_finish_reason = "model", "length"
        status = PR.write_from_reply(REPLY, rec, PERSONA, today=TODAY)
        assert _insights(sb) == [] and "truncated" in status, status
        ev = _events(sb)
        assert len(ev) == 1 and ev[0]["event_type"] == "PATTERN_REPORT_MISSING"
        assert "truncated" in ev[0]["detail"], ev[0]
        rec.reply_finish_reason = "stop"
        PR.write_from_reply(REPLY, rec, PERSONA, today=TODAY)
        assert len(_insights(sb)) == 1


_OLD_INSIGHTS = [{"date": "2026-08-30", "observations": [{
    "evidence": "[EVIDENCE] five short nights", "observation": "[OBSERVATION] flat afternoons",
    "confidence": "[CONFIDENCE] moderate"}]}]


@check("4c. a list-shaped read_recent_insights result carrying old [EVIDENCE] text is refused — "
       "at the source (the loop marks it a tool result) and, failing that, by its repr body")
def _():
    body = str(_OLD_INSIGHTS)                      # what dispatch hands back for a list result
    assert body.startswith("[{'date'") and "[EVIDENCE]" in body
    fake = _Fake(8, REPLY)
    rec = _rec()
    got = _loop(fake, rec, handlers={"read_recent_insights": lambda **k: body})
    assert got == body and rec.reply_source == "tool_result"
    with sandbox() as sb:
        status = PR.write_from_reply(got, rec, PERSONA, today=TODAY)
        assert "tool result" in status and _insights(sb) == [], status
        status = PR.write_from_reply(body, _rec(), PERSONA, today=TODAY)     # no marker
        assert status.startswith("no report") and _insights(sb) == [], status
        assert len(_events(sb)) == 2
    assert PR.is_tool_result_body(body) and PR.is_tool_result_body(json.dumps(_OLD_INSIGHTS))
    assert not PR.is_tool_result_body(REPLY) and not PR.is_tool_result_body("[EVIDENCE] x")


# --- 5. bands before 2026-08-09 -----------------------------------------------------------------

@check("5. entries before 2026-08-09 lose their free-text bands and keep sleep_hours; later ones "
       "keep everything; the handed-over windows carry the stripped copy")
def _():
    entries = [
        {"date": "2026-08-08", "wellbeing": {"mood": "low/depleted", "intensity": "a lot",
                                             "notes": "kept"},
         "health": {"sleep_hours": 6.5, "energy": "masked by overdrive"}},
        {"date": "2026-08-09", "wellbeing": {"mood": "low", "intensity": "high"},
         "health": {"sleep_hours": 7, "energy": "low"}},
    ]
    got = PR.strip_free_text_bands(entries)
    assert got[0]["wellbeing"] == {"notes": "kept"}, got[0]
    assert got[0]["health"] == {"sleep_hours": 6.5}, got[0]
    assert got[1] == entries[1]
    assert entries[0]["wellbeing"]["mood"] == "low/depleted"      # the input is not mutated

    with sandbox() as sb:
        logs = sb["data"] / "logs"
        logs.mkdir(parents=True)
        for e in entries:
            (logs / f"{e['date']}.json").write_text(json.dumps(e))
        ctx = {"today": date(2026, 9, 1), "cap": 100000}
        _h, text, untrusted = PF._read_log_windows("pattern_miner", {"max_entries": 45}, ctx)
    assert "masked by overdrive" not in text and '"sleep_hours": 6.5' in text, text
    assert '"energy": "low"' in text and not untrusted
    assert "30-day window 2026-08-03 → 2026-09-01: 2 days logged" in text, text
    assert "7-day window 2026-08-26 → 2026-09-01: 0 days logged" in text, text


# --- 6. span → baseline row ---------------------------------------------------------------------

@check("6. the data span maps to the baseline-table row at each boundary")
def _():
    table = PR.baseline_table()
    assert table and len(table) == 6, table
    f = date(2025, 1, 15)
    cases = [
        (date(2025, 1, 15), 0), (date(2025, 4, 14), 0), (date(2025, 4, 15), 1),
        (date(2025, 7, 14), 1), (date(2025, 7, 15), 2), (date(2026, 1, 14), 2),
        (date(2026, 1, 15), 3), (date(2027, 1, 14), 3), (date(2027, 1, 15), 4),
        (date(2028, 1, 14), 4), (date(2028, 1, 15), 5), (date(2031, 6, 1), 5),
    ]
    for last, idx in cases:
        assert PR.baseline_row((f, last), table) == table[idx], (last, idx)
    assert PR.baseline_row(None) is None
    assert "no logs on file" in PR.baseline_label(None)
    # A table that no longer has the six expected rows selects nothing; the span still goes over.
    broken = "## Baseline selection\n\n| Data | Baseline |\n|---|---|\n| < 3 months | x |\n\n## Next"
    assert PR.baseline_table(broken) is None
    reordered = PR.baseline_table().copy()
    reordered[0], reordered[1] = reordered[1], reordered[0]
    text = "## Baseline selection\n\n| Data available | Baseline to use |\n|---|---|\n" + \
        "\n".join(f"| {a} | {b} |" for a, b in reordered) + "\n\n## Output format\n"
    assert PR.baseline_table(text) is None
    assert "pick it from your table" in PR.baseline_label((f, date(2025, 2, 1)), table=[])
    with sandbox() as sb:
        logs = sb["data"] / "logs"
        logs.mkdir(parents=True)
        for d in ("2026-03-01", "2026-11-20", "2026-06-05"):
            (logs / f"{d}.json").write_text("{}")
        (logs / "quality_events.json").write_text("")
        assert PR.data_span() == (date(2026, 3, 1), date(2026, 11, 20))
        label = PR.baseline_label(PR.data_span())
    assert "(8 whole months): 6–12 months → Day-of-week granularity" in label, label


# --- 7. the tracker: patterns only, through Stage 2's merge -----------------------------------

@check("7. the tracker path calls merge_pattern_findings — never the replace writer — and leaves "
       "follow_ups, open_threads, held_items and clinical threads untouched")
def _():
    calls: list[dict] = []
    real_merge = CT.merge_pattern_findings

    def spy(**kw):
        calls.append(kw)
        return real_merge(**kw)

    def forbidden(*a, **k):
        raise AssertionError("the replace-semantics writer was called")
    with sandbox() as sb, patched([(CT, "merge_pattern_findings", spy),
                                   (CT, "write_context_tracker", forbidden)]):
        seed = _seed_tracker(sb)
        PR.write_from_reply(REPLY, _rec(), PERSONA, today=TODAY)
        data = json.loads((sb["data"] / "context.json").read_text())
        # A run whose own step 7 merged already gets no second merge from code.
        PR.write_from_reply(REPLY, _rec(("write_context_tracker", "Patterns: 1 added.", True)),
                            PERSONA, today=TODAY)
    assert len(calls) == 1 and set(calls[0]) == {"patterns"}, calls
    pats = calls[0]["patterns"]
    assert pats[0] == "All logged writing happens before noon." and len(pats) == 3, pats
    for key in ("open_threads", "follow_ups", "held_items", "clinical_threads"):
        assert data[key] == seed[key], key
    assert data["patterns"] == seed["patterns"] + pats


# --- 8. end to end on the scheduled path --------------------------------------------------------

_JOB_PROMPT = "Run a full pattern analysis for this week, the past 30 days, and the past 90 days."


def _seed_schedule(sb, agent: str = "pattern_miner") -> None:
    import yaml
    (sb["config"] / "scheduler.yaml").write_text(yaml.safe_dump({"schedules": {
        "weekly_pattern_miner": {"enabled": True, "day": "sunday", "time": "09:00",
                                 "agent": agent, "prompt": _JOB_PROMPT}}}))


def _seed_logs(sb, days: int = 10):
    logs = sb["data"] / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    for i in range(days):
        d = TODAY - timedelta(days=i)
        (logs / f"{d.isoformat()}.json").write_text(json.dumps(
            {"health": {"sleep_hours": 6 + i % 3}, "wellbeing": {"mood": "neutral"}}))


@check("8. the scheduler's weekly job (run_session(scheduled_job=True), the /internal/session "
       "path): the fixed reads arrive in the USER message, the report is written by code and the "
       "tracker gains patterns only")
def _():
    got: dict = {}

    def fake_gemini(system_prompt, user_input, tool_schemas, tool_handlers, **kw):
        got.update(system=system_prompt, user=user_input, kw=kw)
        return REPLY
    with sandbox() as sb, patched([(ORC, "run_session_gemini", fake_gemini),
                                   (ORC, "_spend_gate", lambda *a, **k: None),
                                   (W, "find_duplicate_wisdom", lambda *a, **k: [
                                       {"keys": ["a", "b"], "similarity": 0.9,
                                        "values": ["x", "x."]}])]):
        _seed_logs(sb)
        _seed_schedule(sb)
        seed = _seed_tracker(sb)
        ORC.run_session("pattern_miner", _JOB_PROMPT, persona=PERSONA, provider="gemini",
                        model_override="m", proactive=True, scheduled_job=True)
        files = _insights(sb)
        data = json.loads((sb["data"] / "context.json").read_text())
    user, system = got["user"], got["system"]
    assert "[PREFETCHED" in user and "[PREFETCHED" not in system
    for piece in ("read_recent_insights(n=2)", "read_wisdom()", "get_log_window",
                  "find_duplicate_wisdom()", "Your baseline row: data span",
                  "read_baseline_periods()", '"keys": ["a", "b"]',
                  "7-day window", "90-day window"):
        assert piece in user, (piece, user[:3000])
    assert user.rstrip().endswith(_JOB_PROMPT)
    server_src = (ROOT / "core" / "server.py").read_text()
    assert "proactive=True,\n                                      scheduled_job=True)" in \
        server_src, "the /internal/session route no longer marks the scheduled run"
    assert got["kw"].get("final_round") is True
    assert len(files) == 1, files
    assert data["follow_ups"] == seed["follow_ups"] and data["held_items"] == seed["held_items"]
    assert data["open_threads"] == seed["open_threads"]
    assert len(data["patterns"]) == len(seed["patterns"]) + 3


@check("8b. no marker, no procedure: a user's-turn run, a proactive run without the scheduler's "
       "marker (a fire-and-forget hand-off), a marked run whose job is another agent's, and a "
       "Coordinator dispatch on a proactive pipeline get no bulk reads and write nothing")
def _():
    got: list[str] = []

    def fake_gemini(system_prompt, user_input, tool_schemas, tool_handlers, **kw):
        got.append(user_input)
        return REPLY                                   # valid: only the marker keeps it out
    with sandbox() as sb, patched([(ORC, "run_session_gemini", fake_gemini),
                                   (ORC, "_spend_gate", lambda *a, **k: None)]):
        _seed_logs(sb)
        _seed_schedule(sb)
        # 1. inside a user's turn (run_subagent / the Coordinator's dispatch)
        TR.start_request_trace("how is my sleep", PERSONA, is_proactive=False)
        try:
            ORC.run_session("pattern_miner", "check sleep", persona=PERSONA, provider="gemini",
                            model_override="m")
        finally:
            TR.set_trace(None)
            TR._set_current_agent(None)
        # 2. a proactive run with no marker — how a fire-and-forget hand-off arrives, even
        #    carrying the job's own prompt
        ORC.run_session("pattern_miner", _JOB_PROMPT, persona=PERSONA, provider="gemini",
                        model_override="m", proactive=True)
        # 3. marked, but the matched job belongs to another agent
        _seed_schedule(sb, agent="physical_health")
        ORC.run_session("pattern_miner", _JOB_PROMPT, persona=PERSONA, provider="gemini",
                        model_override="m", proactive=True, scheduled_job=True)
        _seed_schedule(sb)
        # 4. dispatched by the Coordinator on a proactive pipeline — even if a marker were set,
        #    the Pattern Miner is not the request's root agent
        TR.start_request_trace(_JOB_PROMPT, PERSONA, is_proactive=True)
        TR.get_trace().scheduled_job = "weekly_pattern_miner"
        coord = TR.push_agent("coordinator", "gemini", "m")
        try:
            ORC._run_single_agent("pattern_miner", _JOB_PROMPT, persona=PERSONA,
                                  provider="gemini", model_override="m")
        finally:
            TR.pop_agent(coord)
            TR.set_trace(None)
            TR._set_current_agent(None)
        assert _insights(sb) == [] and _events(sb) == [], (_insights(sb), _events(sb))
    assert len(got) == 4 and all("[PREFETCHED" not in u for u in got), [u[:200] for u in got]


if __name__ == "__main__":
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"\n        {detail}" if detail else ""))
    failed = sum(1 for _, ok, _ in _results if not ok)
    print(f"\n{len(_results) - failed} passed, {failed} failed, {len(_results)} total")
    sys.exit(1 if failed else 0)
