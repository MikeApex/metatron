"""
tests/run_phase4.py — Phase 4 test runner.

Verifies the Pattern Miner against 8 weeks of synthetic Ryan Holiday data.
Generates tests/phase4_report.md on completion.

Prerequisites:
    python tests/generate_synthetic_data.py --index

Usage:
    python tests/run_phase4.py
    python tests/run_phase4.py --provider openai     # force o3
    python tests/run_phase4.py --scales 7 30         # run specific scales only
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_ROOT = Path(__file__).parent.parent
_PERSONA = "ryan_holiday"


def _report_path(label: str) -> Path:
    today = date.today().isoformat()
    safe = label.replace("/", "-").replace(" ", "_")
    return _ROOT / "tests" / f"phase4_report_{today}_{safe}.md"


def _count_entries(persona: str) -> dict:
    logs_dir = _ROOT / "data" / "personas" / persona / "logs"
    journal_dir = _ROOT / "data" / "personas" / persona / "journal"
    insights_dir = _ROOT / "data" / "personas" / persona / "insights"
    return {
        "logs": len(list(logs_dir.glob("*.json"))) if logs_dir.exists() else 0,
        "journal": len(list(journal_dir.glob("*.json"))) if journal_dir.exists() else 0,
        "insights": len(list(insights_dir.glob("*.json"))) if insights_dir.exists() else 0,
    }


def run_pattern_miner(scale_days: int, provider: str | None, model: str | None = None) -> dict:
    """Fire one Pattern Miner session for the given scale."""
    import os
    from core.orchestrator import run_session

    os.environ["AI_TEST_PERSONA"] = _PERSONA

    today = date.today()
    end = today.isoformat()
    start = (today - timedelta(days=scale_days)).isoformat()

    scale_label = {7: "7-day", 30: "30-day", 90: "90-day", 365: "365-day"}.get(
        scale_days, f"{scale_days}-day"
    )

    prompt = (
        f"Run a {scale_label} pattern analysis. "
        f"Date window: {start} to {end}. "
        f"Issue at least 5 targeted search_memory queries, then pull the log window, "
        f"synthesize findings in the required format, check for wisdom duplicates, "
        f"and write the insight report."
    )

    t0 = time.time()
    response = run_session(
        agent_name="pattern_miner",
        user_input=prompt,
        persona=_PERSONA,
        provider=provider,
        model_override=model,
    )
    elapsed = round(time.time() - t0, 1)

    return {
        "scale": scale_label,
        "elapsed_s": elapsed,
        "response_length": len(response),
        "response": response,
    }


def run_tests(scales: list[int], provider: str | None, model: str | None = None) -> list[dict]:
    results = []
    for scale in scales:
        print(f"\n--- Pattern Miner: {scale}-day scale ---", flush=True)
        try:
            r = run_pattern_miner(scale, provider, model)
            print(f"  Done in {r['elapsed_s']}s — {r['response_length']} chars")
            results.append(r)
        except Exception as e:
            print(f"  ERROR: {e}")
            results.append({"scale": f"{scale}-day", "error": str(e)})
    return results


def write_report(results: list[dict], entry_counts: dict, label: str) -> None:
    lines = [
        "# Phase 4 Test Report — Pattern Miner",
        f"*Generated: {date.today().isoformat()}*",
        f"*Persona: {_PERSONA}  |  Model: {label}*",
        "",
        "## Data inventory",
        f"- Log entries: {entry_counts['logs']}",
        f"- Journal entries: {entry_counts['journal']}",
        f"- Existing insight reports before this run: {entry_counts['insights']}",
        "",
        "## Scale results",
        "",
    ]

    for r in results:
        lines.append(f"### {r['scale']}")
        if "error" in r:
            lines.append(f"**ERROR:** {r['error']}")
        else:
            lines.append(f"- Elapsed: {r['elapsed_s']}s")
            lines.append(f"- Response length: {r['response_length']} chars")
            lines.append("")
            lines.append("**Response:**")
            lines.append("")
            lines.append(r["response"])
        lines.append("")

    lines += [
        "## Evaluation checklist",
        "",
        "Manual review — mark each after reading the reports above:",
        "",
        "- [ ] 7-day: At least one observation backed by specific log evidence",
        "- [ ] 7-day: Confidence correctly labeled as weak (limited data)",
        "- [ ] 30-day: Monthly rhythm pattern surfaced",
        "- [ ] 30-day: At least one belief validation/challenge with data",
        "- [ ] 90-day: Multi-week trend identified",
        "- [ ] All scales: Output format followed (OBSERVATION / EVIDENCE / HYPOTHESIS / CONFIDENCE / ACTION)",
        "- [ ] Wisdom duplicates flagged (if any exist)",
        "- [ ] Routing fallback log written to data/logs/routing_fallbacks.json",
        "- [ ] Insight report files written to data/personas/ryan_holiday/insights/",
        "",
        "## Notes",
        "",
        "*Add observations here after reviewing.*",
    ]

    path = _report_path(label)
    path.write_text("\n".join(lines))
    print(f"\nReport written: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Phase 4 Pattern Miner test runner")
    parser.add_argument("--provider", default=None,
                        choices=["anthropic", "openai", "ollama", "gemini"],
                        help="Force provider (default: auto-routed)")
    parser.add_argument("--model", default=None,
                        help="Override model ID (e.g. models/gemini-3.1-pro-preview)")
    parser.add_argument("--scales", nargs="+", type=int, default=[7, 30, 90],
                        help="Time scales to test in days (default: 7 30 90)")
    args = parser.parse_args()

    import os
    os.environ["AI_TEST_PERSONA"] = _PERSONA

    counts = _count_entries(_PERSONA)
    print(f"Data inventory: {counts['logs']} logs, {counts['journal']} journal entries")

    if counts["logs"] < 7:
        print("\nWARNING: Fewer than 7 log entries found.")
        print("Run: python tests/generate_synthetic_data.py --index")
        print("Then re-run this script.\n")

    label = args.model or args.provider or "auto-routed"
    results = run_tests(args.scales, args.provider, args.model)
    write_report(results, counts, label)


if __name__ == "__main__":
    main()
