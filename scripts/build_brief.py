#!/usr/bin/env python3
"""
Print one Build job's brief — the document read at gate [N9].

READ-ONLY, AND SAFE ON EITHER MACHINE. It renders from the job's artifacts and
writes nothing, so running it on the Mac against a job that lives on the VM
prints "no such job" rather than doing something surprising. The board's write
commands are the ones that must run over ssh; this is not one of them.

RENDERED FRESH, NOT READ FROM DISK. `--raw` prints the brief.md the writer
landed; the default re-renders from the artifacts. The difference matters when
a job has moved on since its brief was written — a stale document is the one
thing worse than no document at the moment someone is deciding.

REDACTION IS APPLIED ON THE WAY OUT, both paths. core/build/brief.py masks every
literal profile value and reports what it had to mask. A masked value here is a
defect in the renderer, not a success of the mask, so this script says so rather
than printing a clean-looking page.

WHAT RETIRES THIS (.claude/rules/deploy.md's standing rule): the same thing that
retires build_board.py — `tools.build.context_block()` becoming how Build is
worked conversationally. Until then the brief is a document someone reads at a
terminal, and this is the reader.

Zero model tokens.

NEEDS A PERSONA, like the board — `--persona mike` or `METATRON_PERSONA`.

Usage:
    python3 scripts/build_brief.py BLD-0919-01 --persona mike
    python3 scripts/build_brief.py BLD-0919-01 --persona mike --raw
    python3 scripts/build_brief.py BLD-0919-01 --persona mike --needs-tool
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import brief as BR             # noqa: E402
from core.build import jobs as J               # noqa: E402


def render(job_id: str, persona: str | None = None) -> str:
    job = J.get(job_id, persona)
    if job is None:
        return (f"{job_id}: no such job. If you are on the Mac, the ledger lives "
                f"on the VM — this reads only what is local.")
    body = BR.approval_brief(
        job,
        J.read_artifact(job_id, "question_set", persona) or {},
        J.read_artifact(job_id, "answer_ledger", persona) or {},
        J.read_artifact(job_id, "build_plan", persona) or {},
        J.read_artifact(job_id, "estimate", persona),
        (J.read_artifact(job_id, "verification", persona) or {}).get("summary", ""),
        persona,
    )
    leaked = BR.findings(body, persona)
    if leaked:
        body += ("\n\n> ⚠ The redactor masked "
                 f"{len(leaked)} persona value(s) on the way here. That is a defect "
                 "in what the renderer emitted, not a clean result — the structural "
                 "layer is what is supposed to hold.\n")
    return body


def raw(job_id: str, persona: str | None = None) -> str:
    path = J.job_dir(job_id, persona) / "brief.md"
    if not path.exists():
        return f"{job_id}: no brief.md on disk yet — the job has not reached N10."
    return path.read_text(encoding="utf-8")


def needs_tool(job_id: str, persona: str | None = None) -> str:
    directory = J.job_dir(job_id, persona)
    if not directory.is_dir():
        return f"{job_id}: no job directory"
    briefs = sorted(directory.glob("needs_tool_*.md"))
    if not briefs:
        return f"{job_id}: no needs_tool briefs — nothing was missing a tool."
    return "\n\n---\n\n".join(p.read_text(encoding="utf-8") for p in briefs)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("job_id")
    ap.add_argument("--persona", default=None)
    ap.add_argument("--raw", action="store_true",
                    help="print the brief.md the writer landed, not a fresh render")
    ap.add_argument("--needs-tool", action="store_true",
                    help="print the needs_tool briefs instead")
    args = ap.parse_args()

    # Same reason as the board: every path below reads a persona tree, and a
    # traceback is the least useful thing to return over ssh.
    from core.persona import PersonaError, resolve_persona
    try:
        args.persona = resolve_persona(args.persona)
    except PersonaError:
        print("No persona is bound. Pass --persona mike, or export "
              "METATRON_PERSONA=mike in the shell first.")
        return 2

    if args.needs_tool:
        print(needs_tool(args.job_id, args.persona))
    elif args.raw:
        print(raw(args.job_id, args.persona))
    else:
        print(render(args.job_id, args.persona))
    return 0


if __name__ == "__main__":
    sys.exit(main())
