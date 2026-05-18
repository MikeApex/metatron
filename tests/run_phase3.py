"""
tests/run_phase3.py — Phase 3 validation test runner.

Runs 6 test scenarios across 3 personas, in two session modes for the
sequential Holiday tests (same-session multi-turn and separate sessions).

Generates tests/phase3_report.md — a human-readable side-by-side of
inputs, tool calls, and responses for review.

Usage:
    python tests/run_phase3.py
"""

import json
import os
import sys
import textwrap
from datetime import datetime
from pathlib import Path

# Ensure project root is on the path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

os.environ["AI_TEST_PERSONA"] = ""  # reset; set per test

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

from core.orchestrator import (
    load_config, load_agent, load_recent_context, register_tools, _to_openai_tools,
    dispatch_tool, OPENAI_MODEL,
)
import openai

PROVIDER = "openai"
OPENAI_BASE_URL = None  # standard OpenAI endpoint
REPORT_PATH = ROOT / "tests" / "phase3_report.md"

# ---------------------------------------------------------------------------
# Tool-intercepting session runner
# ---------------------------------------------------------------------------

def run_session_captured(
    system_prompt: str,
    turns: list[str],
    tool_schemas: list[dict],
    tool_handlers: dict,
    max_iterations: int = 10,
) -> list[dict]:
    """
    Run a multi-turn conversation, capturing every tool call and response.

    Returns a list of turn dicts:
        {
          "input": str,
          "tool_calls": [{"name": str, "args": dict, "result": str}],
          "response": str,
        }
    """
    api_key = os.environ.get("OPENAI_API_KEY", "")
    client = openai.OpenAI(api_key=api_key, base_url=OPENAI_BASE_URL)
    oai_tools = _to_openai_tools(tool_schemas)

    messages = [{"role": "system", "content": system_prompt}]
    results = []

    for user_input in turns:
        messages.append({"role": "user", "content": user_input})
        turn_tool_calls = []
        response_text = ""
        iterations = 0

        while iterations < max_iterations:
            iterations += 1
            resp = client.chat.completions.create(
                model=OPENAI_MODEL,
                max_tokens=2048,
                tools=oai_tools,
                messages=messages,
            )
            choice = resp.choices[0]
            msg = choice.message
            messages.append(msg)

            if choice.finish_reason != "tool_calls" or not msg.tool_calls:
                response_text = msg.content or ""
                break

            for tc in msg.tool_calls:
                args = json.loads(tc.function.arguments)
                raw_result = dispatch_tool(tc.function.name, args, tool_handlers)
                # Truncate long results for the report
                display_result = raw_result if len(raw_result) < 300 else raw_result[:297] + "..."
                turn_tool_calls.append({
                    "name": tc.function.name,
                    "args": args,
                    "result": display_result,
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": raw_result,
                })

        results.append({
            "input": user_input,
            "tool_calls": turn_tool_calls,
            "response": response_text,
        })

    return results


def _build_system_prompt(persona: str, agent: str) -> str:
    config = load_config(persona=persona)
    agent_text = load_agent(agent)
    recent = load_recent_context(persona=persona)
    context_block = f"\n\n---\n\n{recent}" if recent else ""
    return f"{config}{context_block}\n\n---\n\n## Your Role for This Session\n\n{agent_text}"


def run_single_session(persona: str, agent: str, prompt: str) -> dict:
    """Run one prompt as a fresh single-turn session. Returns one turn dict."""
    os.environ["AI_TEST_PERSONA"] = persona
    system_prompt = _build_system_prompt(persona, agent)
    schemas, handlers = register_tools()
    turns = run_session_captured(system_prompt, [prompt], schemas, handlers)
    return turns[0]


def run_multi_turn(persona: str, agent: str, prompts: list[str]) -> list[dict]:
    """Run a list of prompts as one continuous conversation."""
    os.environ["AI_TEST_PERSONA"] = persona
    system_prompt = _build_system_prompt(persona, agent)
    schemas, handlers = register_tools()
    return run_session_captured(system_prompt, prompts, schemas, handlers)


# ---------------------------------------------------------------------------
# Test definitions
# ---------------------------------------------------------------------------

HOLIDAY_PROMPTS = [
    # T1 — morning check-in
    (
        "Rough night. Maybe five hours. Got the walk in with the boys though — "
        "Liam found a turtle near the mailbox. Writing this morning felt like "
        "pushing through mud. Couldn't get the Cato section to move."
    ),
    # T2 — book mention in passing
    (
        "Finished rereading Letters from a Stoic on the run today. Good timing "
        "given what I'm working through with the Cato chapter. Seneca on "
        "wasted time hit differently this read."
    ),
    # T3 — memory recall
    "How has my writing been going this week? Any patterns you're noticing?",
]

BURKEMAN_PROMPTS = [
    # T4 — morning pages realization
    (
        "Something happened in morning pages today. I kept writing about how "
        "the Aliveness argument feels forced — like I'm trying to make "
        "unclenching into a system. Which is exactly the thing the book is "
        "supposed to argue against. Sat with that for a while."
    ),
    # T5 — end of good day
    (
        "Good day. Solid newsletter draft, didn't force it. Picked Rowan up "
        "from school and we walked home the long way — he told me about a "
        "kid in his class who collects rocks. Felt like an actually present day."
    ),
]

BROOKS_PROMPTS = [
    # T6 — gym streak broke
    (
        "Missed the gym this morning for the third time this week. Kept telling "
        "myself I'd go after the column draft but it didn't happen. Noticed I'm "
        "sharper and less patient when I skip it. Should not be surprised by this."
    ),
]

TESTS = [
    # (id, label, persona, prompts, mode)
    ("T1", "Ryan Holiday / Morning check-in", "ryan_holiday", [HOLIDAY_PROMPTS[0]], "single"),
    ("T2", "Ryan Holiday / Book mention", "ryan_holiday", [HOLIDAY_PROMPTS[1]], "single"),
    ("T3", "Ryan Holiday / Memory recall", "ryan_holiday", [HOLIDAY_PROMPTS[2]], "single"),
    ("T4", "Oliver Burkeman / Morning pages realization", "oliver_burkeman", [BURKEMAN_PROMPTS[0]], "single"),
    ("T5", "Oliver Burkeman / End of good day", "oliver_burkeman", [BURKEMAN_PROMPTS[1]], "single"),
    ("T6", "Arthur Brooks / Gym streak broke", "arthur_brooks", [BROOKS_PROMPTS[0]], "single"),
    ("T1-T3-same", "Ryan Holiday / T1→T3 (same session)", "ryan_holiday", HOLIDAY_PROMPTS, "multi"),
]


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

DIV = "━" * 68

def _fmt_args(args: dict) -> str:
    """Format tool args compactly for the report."""
    parts = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 80:
            v = v[:77] + "..."
        elif isinstance(v, dict):
            v = "{" + ", ".join(f"{kk}: ..." for kk in v) + "}"
        elif isinstance(v, list):
            v = f"[{len(v)} items]"
        parts.append(f"{k}={json.dumps(v, ensure_ascii=False)}")
    return ", ".join(parts)


def _wrap(text: str, width: int = 80, indent: str = "  ") -> str:
    lines = text.splitlines()
    wrapped = []
    for line in lines:
        if line.strip() == "":
            wrapped.append("")
        else:
            wrapped.extend(textwrap.wrap(line, width=width, initial_indent=indent,
                                         subsequent_indent=indent))
    return "\n".join(wrapped)


def render_turn(turn_num: int | None, turn: dict, total_turns: int) -> str:
    blocks = []

    label = f"TURN {turn_num}/{total_turns}" if turn_num and total_turns > 1 else "INPUT"
    blocks.append(f"\n**{label}**\n")
    blocks.append(_wrap(turn["input"]))

    if turn["tool_calls"]:
        blocks.append("\n**TOOL CALLS**\n")
        for i, tc in enumerate(turn["tool_calls"], 1):
            blocks.append(f"  {i}. `{tc['name']}({_fmt_args(tc['args'])})`")
            # Truncate result display
            result_lines = tc["result"].splitlines()
            preview = "\n".join(result_lines[:6])
            if len(result_lines) > 6:
                preview += f"\n     ... ({len(result_lines) - 6} more lines)"
            blocks.append(f"     → {preview}")
    else:
        blocks.append("\n**TOOL CALLS**\n")
        blocks.append("  *(none)*")

    blocks.append("\n**RESPONSE**\n")
    blocks.append(_wrap(turn["response"]))

    return "\n".join(blocks)


def render_test(test_id: str, label: str, turns: list[dict]) -> str:
    lines = [f"\n{DIV}", f"### {test_id} — {label}", DIV]
    for i, turn in enumerate(turns, 1):
        lines.append(render_turn(i if len(turns) > 1 else None, turn, len(turns)))
        if i < len(turns):
            lines.append("\n" + "─" * 40)
    return "\n".join(lines)


def build_report(results: list[tuple[str, str, list[dict]]]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    header = f"""# Phase 3 Test Report
*Generated {now} — Provider: GPT-4o — Agent: Diarist*

Tests validate tool selection, argument quality, and response behavior across
three personas. Sequential Holiday tests (T1→T3) run in both separate sessions
and a single chained session.

---
"""
    body = "\n".join(render_test(tid, label, turns) for tid, label, turns in results)
    return header + body + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Phase 3 test run — {datetime.now().strftime('%H:%M:%S')}")
    print(f"Report will be written to: {REPORT_PATH}\n")

    collected: list[tuple[str, str, list[dict]]] = []

    for test_id, label, persona, prompts, mode in TESTS:
        print(f"  Running {test_id}: {label} ({mode}) ...", end=" ", flush=True)
        try:
            if mode == "multi":
                turns = run_multi_turn(persona, "diarist", prompts)
            else:
                turns = [run_single_session(persona, "diarist", prompts[0])]
            collected.append((test_id, label, turns))
            print("done")
        except Exception as e:
            print(f"ERROR: {e}")
            collected.append((test_id, label, [{
                "input": prompts[0],
                "tool_calls": [],
                "response": f"[ERROR: {e}]",
            }]))

    report = build_report(collected)
    REPORT_PATH.write_text(report)
    print(f"\nReport written: {REPORT_PATH}")


if __name__ == "__main__":
    main()
