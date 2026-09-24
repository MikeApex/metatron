#!/usr/bin/env python3
"""
The Build board — every job, what it is waiting for, and what it has cost.

WHERE THIS RUNS, AND WHY IT MATTERS. Under ruling 0.1 all of Build runs on the
VM: every node, the writer, verification, the ledger and this board's data. The
Mac holds development, this script and build_brief.py as READ-ONLY views, and
the needs_tool builds Mike does by ordinary development.

So the commands split by machine, and the split is not cosmetic:

  READ ANYWHERE     --list --show --costs --run-cost --coherence --registry
  WRITE ON THE VM   --queue --approve --accept --refuse --resume --tick

A write command run on the Mac acts on the MAC'S build tree, which is empty.
It will not error — it will cheerfully report "no such job" about a job that
exists perfectly well on the VM. Run the write half over ssh.

RAISING A JOB'S SPEND LIMIT IS NOT A BOARD COMMAND AT ALL, deliberately
(correction v3.5 C2). An over-budget job parks at `awaiting_approval` and the
approval is:

    ssh <vm> 'cd ~/metatron && METATRON_PERSONA=mike python3 -c "from core.build \
        import cost; cost.approve_limit(\"BLD-MMDD-NN\", 5.00)"'
    ssh <vm> 'cd ~/metatron && python3 scripts/build_board.py --persona mike \
        --resume BLD-MMDD-NN'

Two acts, not one, and neither is a tap. A confirm card would need an executor
entry and would make raising Build's own spend limit a one-tap action, in a
design whose hardcoded deny list exists precisely so Build cannot raise its own
ceiling.

WHAT RETIRES THIS (.claude/rules/deploy.md's standing rule on new machinery). It
retires nothing today — it is the BOOTSTRAP surface, and plan section 5 says so:
Mike uses two surfaces, and this one is "the primary interface during
bootstrap". The build that retires it is `tools.build.context_block()` growing
into the whole of how Build is worked conversationally. Until a gate can be
cleared without a terminal, this is how they are cleared; the read commands
survive it regardless, because a board is a legitimate read view.

Zero model tokens except --coherence, which runs one advisory pass.

EVERY COMMAND NEEDS A PERSONA — `--persona mike`, or `METATRON_PERSONA` in the
shell. Without one the first path call raises and you get a traceback, which
over ssh is the least useful output available. The examples below all carry it.

Usage:
    python3 scripts/build_board.py --persona mike                  # the board
    python3 scripts/build_board.py --persona mike --show BLD-0919-01
    python3 scripts/build_board.py --persona mike --costs
    python3 scripts/build_board.py --persona mike --run-cost       # tier + run lines
    python3 scripts/build_board.py --persona mike --coherence      # one pass
    python3 scripts/build_board.py --persona mike --registry       # docs/BUILD_REGISTRY.md
    python3 scripts/build_board.py --persona mike --queue BLD-0919-01    # VM
    python3 scripts/build_board.py --persona mike --approve BLD-0919-01  # VM — [N9]
    python3 scripts/build_board.py --persona mike --accept BLD-0919-01   # VM — [N13]
    python3 scripts/build_board.py --persona mike --refuse BLD-0919-01   # VM — reverts
    python3 scripts/build_board.py --persona mike --resume BLD-0919-01   # VM — after approve_limit
    python3 scripts/build_board.py --persona mike --tick           # VM — one tick now
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import cost                    # noqa: E402
from core.build import jobs as J               # noqa: E402
from core.build import registry as R           # noqa: E402

# What a state is waiting for, in the terms the person reading this cares about.
# A state name alone makes the reader translate; this is the translation.
_WAITING_FOR = {
    "proposed": "your triage — nothing starts until you queue it",
    "needs_interview": "answers only you can give",
    "awaiting_approval": "a raised spend limit, or a raised ceiling",
    "briefed": "you to read the brief and approve [N9]",
    "verifying": "you to accept or refuse it [N13] — it is already live",
}


def board(persona: str | None = None) -> str:
    states = J.states(persona)
    notice = cost.budget_notice(persona=persona)
    lines: list[str] = []

    # The placeholder notice leads, because it is a warning about a number that
    # governs everything below it, and it self-clears the moment a real figure
    # is configured — so it can never become a header anyone learns to skip.
    if notice:
        lines += [notice, ""]

    if not states:
        return "\n".join(lines + ["No Build jobs."])

    open_jobs = {k: v for k, v in states.items() if v["state"] not in J.TERMINAL}
    done = {k: v for k, v in states.items() if v["state"] in J.TERMINAL}

    lines.append(f"BUILD BOARD — {len(open_jobs)} open, {len(done)} closed")
    lines.append("")
    for job_id, job in sorted(open_jobs.items()):
        spend = cost.job_spend(job_id, persona)
        limit = cost.job_limit(job_id, persona)
        flag = f"  @blocked: {job['blocked']}" if job.get("blocked") else ""
        lines.append(f"  {job_id}  {job['state']:<18} "
                     f"attempt {job.get('attempt', 1)}  ${spend:.4f}/${limit:.2f}")
        lines.append(f"      {str(job.get('gap', ''))[:100]}")
        waiting = _WAITING_FOR.get(job["state"])
        if waiting:
            lines.append(f"      waiting for: {waiting}")
        if flag:
            lines.append(f"    {flag}")
    if done:
        lines.append("")
        lines.append("closed:")
        for job_id, job in sorted(done.items()):
            lines.append(f"  {job_id}  {job['state']:<12} "
                         f"{str(job.get('detail', ''))[:70]}")

    status = R.tier_status(persona)
    lines += ["",
              f"leaf capabilities under the Coordinator: {status['leaves']} of "
              f"{status['due_at']}"
              + ("  — THE TIER IS DUE" if status["due"] else "")]
    return "\n".join(lines)


def show(job_id: str, persona: str | None = None) -> str:
    job = J.get(job_id, persona)
    if job is None:
        return (f"{job_id}: no such job. If you are on the Mac, the ledger lives "
                f"on the VM — this board reads only what is local.")
    lines = [f"{job_id}  [{job['state']}]  attempt {job.get('attempt', 1)}",
             f"  mode:      {job.get('mode')}",
             f"  gap:       {job.get('gap')}",
             f"  trigger:   {job.get('trigger')}",
             f"  depth:     {job.get('depth')}"]
    if job.get("blocked"):
        lines.append(f"  @blocked:  {job['blocked']}")
    if job.get("detail"):
        lines.append(f"  last:      {job['detail']}")

    directory = J.job_dir(job_id, persona)
    if directory.is_dir():
        artifacts = sorted(p.name for p in directory.iterdir())
        lines.append(f"  artifacts: {', '.join(artifacts) or '(none)'}")

    tokens = cost.job_tokens(job_id, persona)
    lines.append(f"  spend:     ${tokens['usd']:.4f} over {tokens['calls']} call(s) "
                 f"({tokens['tokens_in']} in / {tokens['tokens_out']} out)")
    waiting = _WAITING_FOR.get(job["state"])
    if waiting:
        lines.append(f"  waiting:   {waiting}")
    return "\n".join(lines)


def costs(persona: str | None = None) -> str:
    day = cost.day_total(persona)
    lines = [f"Build spend today: ${day['usd']:.4f} over {day['calls']} call(s) "
             f"across {day['jobs']} job(s)", ""]
    for job_id, job in sorted(J.states(persona).items()):
        tokens = cost.job_tokens(job_id, persona)
        if tokens["calls"]:
            lines.append(f"  {job_id}  ${tokens['usd']:.4f}  "
                         f"{tokens['calls']} call(s)  [{job['state']}]")
    notice = cost.budget_notice(persona=persona)
    if notice:
        lines += ["", notice]
    return "\n".join(lines)


def run_cost(persona: str | None = None) -> str:
    """
    THE PRODUCT, NOT THE FACTORY. What each landed capability costs to keep.

    Everything else in this script meters the BUILD, which ends. A landed agent
    is dispatched on every matching turn, forever, at that turn's model price.
    """
    live = R.capabilities(persona)
    status = R.tier_status(persona)
    lines = [f"RUN LINES — {len(live)} live capability(ies)", ""]
    if not live:
        lines.append("  nothing has landed yet")
    for name, row in sorted(live.items()):
        run = row.get("run") or {}
        actual = run.get("dispatches_actual_per_day")
        expected = run.get("dispatches_expected_per_day")
        lines.append(
            f"  {name:<24} v{row.get('version')}  {run.get('execution_mode', '?'):<10} "
            f"budget {run.get('latency_budget_ms', '?')}ms")
        lines.append(
            f"      dispatches/day  expected "
            f"{'—' if expected is None else expected}  "
            f"actual {'not counted yet' if actual is None else actual}"
            + (f"  (over {run['counted_over_days']}d to {run['counted_at']})"
               if run.get("counted_over_days") else ""))
    lines += ["",
              f"  {status['leaves']} of {status['due_at']} leaf capabilities under "
              f"the Coordinator"
              + ("  — THE TIER IS DUE" if status["due"]
                 else "; the tier becomes due at the fourth")]
    return "\n".join(lines)


def _resolve_persona(explicit: str | None) -> str | None:
    """
    The persona to read, or None after printing how to supply one.

    A named error beats a traceback: every command in this script reads a
    persona tree, and the ones documented for the VM are run over ssh where a
    stack trace is the least useful possible output.
    """
    from core.persona import PersonaError, resolve_persona
    try:
        return resolve_persona(explicit)
    except PersonaError:
        print("No persona is bound. Pass --persona mike, or export "
              "METATRON_PERSONA=mike in the shell first.\n"
              "  python3 scripts/build_board.py --persona mike")
        return None


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    # THE PERSONA IS RESOLVED BEFORE ANYTHING ELSE RUNS, and the failure says
    # what to do. Every command here reads a persona tree, so with no
    # --persona and no METATRON_PERSONA in the shell the first path call
    # raised PersonaError and printed a traceback — the documented VM
    # one-liners included, which is where it is least recoverable.
    ap.add_argument("--persona", default=None,
                    help="whose Build tree to read (or export METATRON_PERSONA)")
    ap.add_argument("--show", metavar="JOB_ID")
    ap.add_argument("--costs", action="store_true")
    ap.add_argument("--run-cost", action="store_true")
    ap.add_argument("--coherence", action="store_true")
    ap.add_argument("--registry", action="store_true",
                    help="write docs/BUILD_REGISTRY.md (Mac; Mike commits it)")
    ap.add_argument("--refresh-counts", action="store_true",
                    help="VM: recount dispatches from the traces")
    for command in ("queue", "approve", "accept", "refuse", "resume"):
        ap.add_argument(f"--{command}", metavar="JOB_ID",
                        help=f"VM only — {command} a job")
    ap.add_argument("--tick", action="store_true", help="VM only — run one tick now")
    args = ap.parse_args()

    persona = _resolve_persona(args.persona)
    if persona is None:
        return 2

    if args.show:
        print(show(args.show, persona))
        return 0
    if args.costs:
        print(costs(persona))
        return 0
    if args.run_cost:
        print(run_cost(persona))
        return 0
    if args.registry:
        print(R.write_markdown(ROOT / "docs" / "BUILD_REGISTRY.md", persona))
        return 0
    if args.refresh_counts:
        print(R.refresh_run_counts(persona))
        return 0
    if args.coherence:
        from core.build import coherence
        print(coherence.render(coherence.review(persona)))
        return 0

    from core.build import runner
    for command in ("queue", "approve", "accept", "refuse", "resume"):
        job_id = getattr(args, command)
        if job_id:
            print(getattr(runner, command)(job_id, persona))
            return 0
    if args.tick:
        print(runner.tick(persona))
        return 0

    print(board(persona))
    return 0


if __name__ == "__main__":
    sys.exit(main())
