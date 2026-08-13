#!/usr/bin/env python3
"""What a worker actually costs — measured, not estimated.

Every dispatch decision in `/backlog verify` and `/backlog attack` rests on a
number: what does one cold worker cost? That number was guessed at ~32k for most
of this build, and the guess was wrong in both directions — trivial probes land
at 30k, real investigations at 59k, and the worst observed run cost 108,792.
Deciding how many items to give a worker from a wrong constant is how three
probes came to cost 96k of a 170k session.

The data was there the whole time. Claude Code writes every subagent's usage
into the session transcript, so this reads what already happened rather than
instrumenting anything: no hook, no worker, no model tokens, and it works
retrospectively over every session this project has ever run.

    python3 scripts/worker_ledger.py                # all sessions, summary + table
    python3 scripts/worker_ledger.py --session ID   # one session (a fan-out)
    python3 scripts/worker_ledger.py --quiet        # summary only

WHAT IT CANNOT TELL YOU, so nobody over-reads the output: `subagent_tokens` is
cumulative usage across the worker's turns, not its final context occupancy.
Because each turn resends the conversation, cumulative usage grows roughly
quadratically with context — so a worker at 59k is nowhere near 59k of context.
Do not use these figures to reason about window limits; use them for cost.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from statistics import median

# TWO formats exist in the transcripts and matching only one is not a partial
# result, it is a wrong one: the first version of this script reported 3 runs out
# of 41 and looked entirely plausible doing it. Older sessions carry XML-ish
# element tags, newer ones a plain `key: value` block. Found by running it.
#   <usage><subagent_tokens>68131</subagent_tokens><tool_uses>15</tool_uses>…
#   <usage>subagent_tokens: 81561\ntool_uses: 17\nduration_ms: 77080</usage>
USAGE_RE = re.compile(
    r"<usage>\s*(?:<subagent_tokens>\s*(?P<t1>\d+)|subagent_tokens:\s*(?P<t2>\d+))"
    r".*?(?:<tool_uses>\s*(?P<c1>\d+)|tool_uses:\s*(?P<c2>\d+))"
    r".*?(?:<duration_ms>\s*(?P<d1>\d+)|duration_ms:\s*(?P<d2>\d+))",
    re.S,
)
TOOL_USE_ID_RE = re.compile(r"<tool-use-id>(\S+?)</tool-use-id>")
TASK_ID_RE = re.compile(r"<task-id>(\S+?)</task-id>")
SUMMARY_RE = re.compile(r"<summary>Agent \"(.*?)\" finished</summary>", re.S)


def _project_root() -> Path:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True, text=True, timeout=10,
        )
        if out.returncode == 0 and out.stdout.strip():
            return Path(out.stdout.strip())
    except (OSError, subprocess.TimeoutExpired):
        pass
    return Path.cwd()


def _transcript_dir(root: Path) -> Path:
    """Claude Code's per-project transcript directory.

    The path is the project's absolute path with separators replaced by '-',
    which is the harness's own convention -- derived, never configured, so a
    project that moves gets a new directory rather than a stale one.
    """
    slug = str(root.resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug


def collect(transcripts: Path, session: str | None) -> list[dict]:
    """Join dispatched Agent calls to their completion notifications.

    Two record shapes, in separate lines and often separate files: the assistant
    message carrying the Agent tool_use (which holds the brief -- model, type,
    description, prompt size), and a queue-operation notification carrying the
    result (which holds the usage). `tool-use-id` is the join key.

    A task may notify more than once -- the harness says so explicitly, because
    a finished agent can be resumed -- so notifications are keyed by tool-use-id
    and the largest usage wins. Summing them would double-count a resumed agent.
    """
    briefs: dict[str, dict] = {}
    results: dict[str, dict] = {}

    files = sorted(transcripts.glob("*.jsonl"))
    if session:
        files = [f for f in files if session in f.name]

    for path in files:
        try:
            lines = path.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for line in lines:
            if '"Agent"' not in line and "subagent_tokens" not in line:
                continue
            try:
                rec = json.loads(line)
            except ValueError:
                continue

            msg = rec.get("message")
            if isinstance(msg, dict):
                for block in msg.get("content") or []:
                    if not isinstance(block, dict) or block.get("name") != "Agent":
                        continue
                    args = block.get("input") or {}
                    briefs[block.get("id", "")] = {
                        "session": path.stem[:8],
                        "model": args.get("model") or "inherited",
                        "type": args.get("subagent_type") or "general-purpose",
                        "desc": args.get("description") or "(none)",
                        "brief_chars": len(args.get("prompt") or ""),
                    }
                continue

            content = rec.get("content")
            if not isinstance(content, str) or "subagent_tokens" not in content:
                continue
            usage = USAGE_RE.search(content)
            tuid = TOOL_USE_ID_RE.search(content)
            if not usage or not tuid:
                continue
            g = usage.groupdict()
            tokens = int(g["t1"] or g["t2"])
            tool_uses = int(g["c1"] or g["c2"])
            duration = int(g["d1"] or g["d2"])
            key = tuid.group(1)
            prior = results.get(key)
            if prior and prior["tokens"] >= tokens:
                continue
            summary = SUMMARY_RE.search(content)
            task = TASK_ID_RE.search(content)
            results[key] = {
                "tokens": tokens,
                "tool_uses": tool_uses,
                "minutes": duration / 60000.0,
                "summary": summary.group(1).strip() if summary else "",
                "task": task.group(1)[:9] if task else "",
                "session": path.stem[:8],
            }

    rows = []
    for key, res in results.items():
        brief = briefs.get(key, {})
        rows.append({
            "session": brief.get("session") or res["session"],
            "model": brief.get("model", "?"),
            "desc": brief.get("desc") or res["summary"] or "(unpaired)",
            "brief_chars": brief.get("brief_chars", 0),
            "paired": key in briefs,
            **res,
        })
    return sorted(rows, key=lambda r: r["tokens"], reverse=True)


def report(rows: list[dict], quiet: bool) -> None:
    if not rows:
        print("worker_ledger: no subagent runs found.")
        return

    if not quiet:
        print(f"{'session':<9} {'model':<10} {'tokens':>8} {'calls':>6} {'min':>6}  task")
        print("-" * 78)
        for r in rows:
            print(
                f"{r['session']:<9} {r['model']:<10} {r['tokens']:>8,} "
                f"{r['tool_uses']:>6} {r['minutes']:>6.1f}  {r['desc'][:34]}"
            )
        print()

    tokens = [r["tokens"] for r in rows]
    print(f"{len(rows)} worker runs · floor {min(tokens):,} · "
          f"median {int(median(tokens)):,} · worst {max(tokens):,} · "
          f"total {sum(tokens):,}")

    by_model: dict[str, list[int]] = {}
    for r in rows:
        by_model.setdefault(r["model"], []).append(r["tokens"])
    for model, vals in sorted(by_model.items(), key=lambda kv: -len(kv[1])):
        print(f"  {model:<10} n={len(vals):<3} floor {min(vals):>7,} · "
              f"median {int(median(vals)):>7,} · worst {max(vals):>7,}")

    unpaired = sum(1 for r in rows if not r["paired"])
    if unpaired:
        print(f"  ({unpaired} run(s) had no matching dispatch record in these "
              f"transcripts — usage is real, the brief is unknown)")
    print("\nThe floor is the briefing: a worker pays it before reading anything.")
    print("Budget from the median for real work, not the floor.")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--session", help="limit to one session id (prefix match)")
    ap.add_argument("--quiet", action="store_true", help="summary only, no table")
    args = ap.parse_args()

    transcripts = _transcript_dir(_project_root())
    if not transcripts.is_dir():
        print(f"worker_ledger: no transcripts at {transcripts}", file=sys.stderr)
        return 1
    report(collect(transcripts, args.session), args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())
