#!/usr/bin/env python3
"""
The Build board — what is filed, what is in flight, and what each capability costs.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 5.

WHAT THIS IS NO LONGER. Under v3 all of Build ran on the VM, so this script had
a write half — `--queue`, `--approve`, `--accept`, `--refuse`, `--resume` — that
had to be run over ssh or it would cheerfully report "no such job" about a job
that existed perfectly well on the other machine. Every one of those was a
command to move VM STATE.

Ruling 1 removes the whole category: Build runs on the Mac, in a session Mike is
sitting in, and `/build` is how a job moves. THE SESSION IS THE STATE. What is
left here is a READ VIEW joining three sources, plus one write that is not a
state change at all:

    --tickets    the VM's inbox, FETCHED read-only over the existing monitor
                 route. No write path from the Mac to the VM exists or is added.
    --jobs       the job directories on this machine
    --registry   the tracked registry, and docs/BUILD_REGISTRY.md from it
    --run-cost   what each landed capability costs, standing, per day
    --abandon    writes an `abandoned` row into the WORKING TREE for Mike to
                 commit. A decision recorded in a tracked file, not a state
                 transition on another machine.

THE ONE NUMBER THAT HAS TO BE ON THIS BOARD, and the reason finding 7 exists: a
ticket Mike decided on the Mac stays OPEN on the VM until the next deploy
carries its registry row. Those tickets are not gaps still waiting — they are
already answered — and a board that showed them in the open count would read as
a backlog that never shrinks. `N decided, awaiting deploy` is printed beside the
open count so the lag is visible rather than inferred.

Zero model tokens. Stdlib plus PyYAML.

Usage:
    python3 scripts/build_board.py --persona mike
    python3 scripts/build_board.py --persona mike --tickets
    python3 scripts/build_board.py --persona mike --jobs
    python3 scripts/build_board.py --persona mike --registry
    python3 scripts/build_board.py --persona mike --run-cost
    python3 scripts/build_board.py --persona mike --abandon BLD-0924-01 "not worth it"
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DEFAULT_SERVER = "https://metatron-vm.tail0acc5d.ts.net:8001"

# Short, like sync_dev_backlog's. The VM being stopped is an ordinary state on
# this project, and a board that hangs for thirty seconds to tell you so is a
# board nobody runs.
TIMEOUT_SECONDS = 5


def _auth_header() -> dict:
    """The same locally-minted bearer sync_dev_backlog.py uses. {} on failure."""
    try:
        from core.auth import bearer_header
        return bearer_header(ttl_seconds=300)
    except Exception:
        return {}


def fetch_tickets(server: str, persona: str) -> tuple[list[dict], str]:
    """
    (rows, note). READ-ONLY, over the existing /monitor/file route.

    An unreachable VM returns ([], reason) rather than raising: the VM is
    stopped most of the time on this project, and every other half of this
    board is local and still worth printing.
    """
    path = f"data/personas/{persona}/build/tickets.jsonl"
    url = f"{server.rstrip('/')}/monitor/file?{urllib.parse.urlencode({'path': path})}"
    try:
        req = urllib.request.Request(url, headers=_auth_header())
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        return [], f"the VM did not answer ({type(exc).__name__}) — local halves only"

    content = payload.get("content", "")
    if not isinstance(content, str):
        return [], "the monitor route returned no content"

    rows = []
    for line in content.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("job_id"):
            rows.append(row)
    return rows, ""


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

def show_tickets(rows: list[dict], note: str) -> None:
    from core.build import tickets as T

    print("## Tickets — the VM's inbox\n")
    if note:
        print(f"  ({note})\n")
    if not rows:
        print("  nothing filed.\n")
        return

    ids = [str(r["job_id"]) for r in rows]
    decided = set(T.decided_awaiting_deploy(ids))
    for row in rows:
        job_id = str(row["job_id"])
        mark = "decided, awaiting deploy" if job_id in decided else "open"
        mode = row.get("mode", "construct")
        print(f"  {job_id}  [{mark}]"
              + ("  (repair)" if mode == "repair" else "")
              + f"\n      {str(row.get('gap') or '')[:140]}")
    open_count = len(ids) - len(decided)
    print(f"\n  {open_count} open"
          + (f", {len(decided)} decided, awaiting deploy" if decided else "")
          + ".\n")
    if decided:
        print("  A decided ticket stays open on the VM until the deploy that")
        print("  carries its registry row. It is answered, not waiting.\n")


def show_jobs(persona: str) -> None:
    from core.build import driver as D
    from core.build import jobs as J

    print("## Jobs — on this machine\n")
    ids = J.known_jobs(persona)
    if not ids:
        print("  no job directories yet.\n")
        return
    for job_id in ids:
        step = D.next_step(job_id, persona)
        where = (f"waiting at {step.node} — {step.detail}" if step.is_gate
                 else f"next: {step.node}"
                 + (f" (attempt {step.attempt})" if step.attempt > 1 else ""))
        attempts = len(J.attempts(job_id, persona))
        print(f"  {job_id}  {where}\n      {attempts} node attempt(s) recorded")
    print()


def show_registry() -> None:
    from core.build import registry as R
    print(R.render_markdown())


def show_run_cost() -> None:
    from core.build import registry as R

    print("## Run cost — what each landed capability costs, standing\n")
    live = R.capabilities()
    if not live:
        print("  nothing landed.\n")
        return
    for name, row in sorted(live.items()):
        run = row.get("run") or {}
        actual = run.get("dispatches_actual_per_day")
        measured = run.get("counted_over_days")
        rate = ("not counted yet" if actual is None
                else f"{actual}/day over {measured}d")
        print(f"  {name}  {run.get('execution_mode', '?')}, "
              f"budget {run.get('latency_budget_ms', '?')}ms — {rate}")

    status = R.tier_status()
    print(f"\n  {status['leaves']} leaf capability(ies); the tier review is due "
          f"at {status['due_at']}"
          + (" — DUE NOW." if status["due"] else ".") + "\n")
    print("  `not counted yet` is not zero. A capability that landed today has")
    print("  no full day of use behind it, and writing 0.0 would report it as")
    print("  unused rather than unmeasured.\n")


def abandon(job_id: str, reason: str, persona: str) -> int:
    """
    Record Mike's decision not to build a ticket. WRITES THE WORKING TREE ONLY.

    The row lands in config/build/registry.yaml for Mike to read in a diff and
    commit. Nothing reaches the VM until he deploys — which is exactly the lag
    the board prints, and the reason `abandoned` is the one status that counts
    against max_proposed while it waits.
    """
    from core.build import registry as R
    if not reason.strip():
        print("An abandoned row with no reason is indistinguishable from a lost "
              "one. Say why.", file=sys.stderr)
        return 1
    row = R.mark_abandoned(job_id, reason, persona)
    print(f"Wrote an `abandoned` row for {job_id} into "
          f"{R.REGISTRY_PATH.relative_to(ROOT)}.\n")
    print(f"  reason: {row['reason']}\n")
    print("  Nothing has reached the VM. Commit it, and the ticket closes on")
    print("  the next deploy — until then it still counts toward max_proposed.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", default="mike")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--tickets", action="store_true")
    ap.add_argument("--jobs", action="store_true")
    ap.add_argument("--registry", action="store_true",
                    help="print the registry, and rewrite docs/BUILD_REGISTRY.md")
    ap.add_argument("--run-cost", action="store_true")
    ap.add_argument("--abandon", nargs=2, metavar=("BLD-MMDD-NN", "REASON"))
    args = ap.parse_args()

    if args.abandon:
        return abandon(args.abandon[0], args.abandon[1], args.persona)

    chosen = args.tickets or args.jobs or args.registry or args.run_cost
    if args.tickets or not chosen:
        rows, note = fetch_tickets(args.server, args.persona)
        show_tickets(rows, note)
    if args.jobs or not chosen:
        show_jobs(args.persona)
    if args.run_cost or not chosen:
        show_run_cost()
    if args.registry:
        from core.build import registry as R
        show_registry()
        R.write_markdown()
        print(f"(rewrote docs/BUILD_REGISTRY.md)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
