#!/usr/bin/env python3
"""
Referent-resolution probe for [DB-0826-01] — the before/after harness for the fix.

WHAT THIS ANSWERS: does a short referring turn ("undo that merge", "approved",
"cancel my previous request") reach the right specialist, on the model the
Coordinator actually runs today, in the condition production actually runs in?

It is deliberately NOT tests/run_coord_model_probe.py. That script's question was
"Flash-Lite or Pro" — closed on 2026-08-28 (Pro declined on latency), and its two
model ids are both gone from the fleet. This one holds the model fixed at the live
Coordinator model and varies the two things that are still open:

  * `--arm none` — the Coordinator receives neither the conversation nor a referent
    block. THIS IS THE PRE-FIX BASELINE THAT MATTERS, and no previously recorded figure
    measured it: every number the old probe produced, including the 6/12 of 2026-08-28,
    was taken with `history` supplied, a condition the live pipeline never provided.
  * `--arm history` — the first half of the fix: the last six messages, as the
    Synthesizer already received.
  * `--arm full` — both halves, adding tools/turn_referent.context_block().

Cases and scoring are imported from run_coord_model_probe so there is exactly one
definition of the four recovered ROUTING_MISS failures and one scorer.

THREE OUTCOMES, not two. score_b returns CLARIFIED when the Coordinator raised
CLARIFICATION_NEEDED instead of guessing. That is a PASS of the agent file's rule
even when the referent is unresolved, and the ask-rate over the suite is the stated
pass condition for the fix — a model that asks has stopped confidently mis-routing.

Usage:
    python tests/run_referent_probe.py --dry-run
    python tests/run_referent_probe.py --arm all --repeat 3
Cost: 4 cases x repeat x arms Flash-Lite calls (~7k input each, mostly cached). Pennies.
"""

import argparse
import json
import shutil
import sys
import tempfile
from collections import Counter
from datetime import datetime
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.run_coord_model_probe import (  # noqa: E402
    SUITE_B_HARD, run_turn, score_b,
)
from core import orchestrator as orch  # noqa: E402
from tools import turn_referent as _tref  # noqa: E402

# The live Coordinator model, config/modules/routing_cloud.yaml:34. Not a comparison axis
# here — the model question is closed; this probe measures a code change.
COORD_MODEL = "gemini-3.5-flash-lite"

# THE THREE ARMS. Each is a real state of core/orchestrator.py, not a hypothetical.
#
#   none    — what shipped until 2026-09-03: the Coordinator receives no conversation and
#             no referent block. This is the condition all five live failures happened in,
#             and the condition tests/run_coord_model_probe.py has never measured.
#   history — the first half of the fix: _coord_history() hands the Coordinator the last
#             six messages, mirroring what the Synthesizer already got.
#   full    — both halves: history plus tools/turn_referent.context_block(), which states
#             what the previous turn actually DID, including a pending or declined action
#             the transcript reports as done.
#
# Running all three is what attributes the win. If `history` alone closes it, the block is
# carrying nothing and should be argued for on the 2026-08-29 case alone.
ARMS = {
    "none":    {"history": False, "block": False},
    "history": {"history": True,  "block": False},
    "full":    {"history": True,  "block": True},
}

# Reconstructed tool calls for the prior turn of each case, so the block has something to
# report. These are RECONSTRUCTIONS from the [DB-0826-01] descriptions, in the same sense
# and with the same limits as the suite's own two-turn setups: the live traces are in
# `mike`'s VM-owned data and nothing replayable exists on this machine. A pass here is
# evidence about the class, not proof the exact live turn now works.
#
# B4h carries a PENDING card and no completed send. That is the 2026-08-29 shape and the
# one case where the transcript and the truth disagree — the reply said the draft was
# ready, the action was never taken, and "Approved." has to resolve to the waiting one.
PRIOR = {
    "B1h": {"tools": [{"name": "merge_contacts",
                       "args": {"primary_id": "c_88", "duplicate_id": "c_91",
                                "name": "Marcus Delgado"}, "ok": True}],
            "pending": [], "declined": []},
    "B2h": {"tools": [{"name": "write_log",
                       "args": {"kind": "food", "date": "today"}, "ok": True}],
            "pending": [], "declined": []},
    "B3h": {"tools": [{"name": "write_calendar_event",
                       "args": {"title": "Table at Fumbally", "when": "Thursday 12:30"},
                       "ok": True}],
            "pending": [], "declined": []},
    # send_email with a pending card and no completed send is the LIVE shape, not a
    # stand-in: tools/confirm.py gates the send, so the call records ok=True having done
    # nothing but raise the card, and only the ledger knows the difference. This is the
    # 2026-08-29 instance reproduced exactly, and the one case where the transcript and
    # the truth disagree — "Approved." has to resolve to the waiting action.
    "B4h": {"tools": [{"name": "send_email",
                       "args": {"to": "landlord", "subject": "The boiler"}, "ok": True}],
            "pending": ["Send the email to the landlord about the boiler"],
            "declined": []},
}


def _install_prior_turn(case: dict, tmp: Path) -> None:
    """Write the case's prior turn where tools/turn_referent.py will read it.

    Points the module's persona_data_dir at a tmp tree rather than the persona's own, so a
    probe run never writes into data/personas/ — git-tracked for danny_park, and a trace
    file dated today would otherwise show up in every subsequent `git status`.
    """
    prior = PRIOR[case["id"]]
    hist = case["history"]
    rec = {
        "trace_id": "probe", "ts": datetime.now().isoformat(), "persona": "probe",
        "user_input": hist[-2]["content"], "synth_response": hist[-1]["content"],
        "is_proactive": False,
        "pipeline": [{"agent": "coordinator", "turns": [], "subagents": [
            {"agent": "specialist", "subagents": [],
             "turns": [{"turn": 1, "tool_calls": prior["tools"]}]}]}],
    }
    traces = tmp / "traces"
    if traces.exists():
        shutil.rmtree(traces)
    traces.mkdir(parents=True, exist_ok=True)
    (traces / f"{datetime.now().date().isoformat()}.jsonl").write_text(
        json.dumps(rec) + "\n")
    _tref.persona_data_dir = lambda persona=None: tmp
    _tref._pending_and_declined = lambda persona: (prior["pending"], prior["declined"])


def _disable_block(tmp: Path) -> None:
    """The `none` and `history` arms must see no block at all, from any source."""
    empty = tmp / "empty"
    empty.mkdir(parents=True, exist_ok=True)
    _tref.persona_data_dir = lambda persona=None: empty
    _tref._pending_and_declined = lambda persona: ([], [])


# Did RESOLVED_INTENT name the right thing — separately from which specialist was picked.
#
# These two questions came out different on 2026-09-03 and conflating them understated the
# fix. On B4h ("Approved.") with the referent block, the Coordinator named the landlord
# boiler draft and nothing else, 3 runs of 3 — the referent was resolved correctly every
# time — and then dispatched `logistics` rather than `relationships` on two of them. That
# is a taxonomy disagreement about who owns emailing a landlord, not the failure
# [DB-0826-01] is about. score_b keeps scoring the dispatch, because that is what the
# regression gate has always meant; this metric scores the referent.
#
# `must_not` is what makes the measurement discriminating. Given only the transcript, the
# Coordinator named BOTH pending approvals on every B4h run — the Apex quarterly review
# and the landlord email. Naming the right one is not evidence if the wrong one is named
# beside it, so an intent mentioning a `must_not` marker fails regardless.
REFERENT_MARKERS = {
    "B1h": {"must": ["contact", "marcus", "delgado", "merge of the two", "duplicate"],
            "must_not": ["apex", "prudential", "branch", "repository"]},
    "B2h": {"must": ["food", "ate", "porridge", "salad", "pasta", "meal", "log"],
            "must_not": ["prudential schedule", "quarterly", "handover", "retro"]},
    "B3h": {"must": ["fumbally", "thursday", "12:30", "half twelve"],
            "must_not": ["aoife", "brother hubbard", "monday"]},
    "B4h": {"must": ["landlord", "boiler"],
            "must_not": ["apex", "quarterly review"]},
}


def referent_ok(row: dict) -> bool | None:
    m = REFERENT_MARKERS.get(row["id"])
    if not m:
        return None
    intent = (row.get("resolved_intent") or "").lower()
    if not intent:
        return False
    if any(bad in intent for bad in m["must_not"]):
        return False            # named the competing referent too — not a resolution
    return any(good in intent for good in m["must"])


def summarise(rows: list[dict]) -> dict:
    """Ask-rate and failure count per mode — the stated pass condition."""
    out = {}
    def _arm(r):
        return r.get("arm") or r.get("history_mode")

    for mode in sorted({_arm(r) for r in rows},
                       key=lambda m: list(ARMS).index(m) if m in ARMS else 99):
        sub = [r for r in rows if _arm(r) == mode]
        v = Counter(r["verdict"] for r in sub)
        n = len(sub)
        out[mode] = {
            "n": n,
            "verdicts": dict(v),
            "resolved": v["PASS"],
            "asked": v["CLARIFIED"],
            "failed": v["FAIL"] + v["ERROR"],
            # A turn the Coordinator did not get wrong: it either resolved the
            # referent or declined to guess. The fix is allowed to buy safety with
            # clarifying questions; it is not allowed to buy it with silence.
            "not_wrong": v["PASS"] + v["CLARIFIED"],
            "ask_rate": round(100 * v["CLARIFIED"] / n) if n else 0,
            "referent_ok": sum(1 for r in sub if referent_ok(r)),
            "referent_rate": round(100 * sum(1 for r in sub if referent_ok(r)) / n) if n else 0,
            "not_wrong_rate": round(100 * (v["PASS"] + v["CLARIFIED"]) / n) if n else 0,
        }
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", default="danny_park",
                    help="git-tracked test persona. 'mike' is refused — real data, VM-owned.")
    ap.add_argument("--arm", choices=list(ARMS) + ["all"], default="all",
                    help="which state of core/orchestrator.py to measure. Default all "
                         "three, which is what attributes the win to a half of the fix.")
    ap.add_argument("--repeat", type=int, default=3,
                    help="runs per cell. Routing is not deterministic; one sample cannot "
                         "separate a real change from noise.")
    ap.add_argument("--label", default="baseline",
                    help="tag for the output filename, e.g. baseline / with-referent-block")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    if args.persona == "mike":
        raise SystemExit("refusing to probe against 'mike' — real person's data, VM-owned")

    modes = list(ARMS) if args.arm == "all" else [args.arm]
    cells = len(SUITE_B_HARD) * len(modes) * args.repeat

    print(f"Referent probe — model {COORD_MODEL}, persona {args.persona}")
    print(f"{len(SUITE_B_HARD)} cases x {len(modes)} arm(s) x {args.repeat} "
          f"= {cells} calls\n")
    for c in SUITE_B_HARD:
        print(f"  {c['id']:>3}  {c['message']!r}")
        print(f"       {c['label']}")
        print(f"       expect_any={c['expect_any']} forbid={c['forbid']} "
              f"expect_referent={c.get('expect_referent', [])}")
    if args.dry_run:
        print("\n--dry-run: no API calls made.")
        return 0

    import os
    if not os.environ.get("GOOGLE_CLOUD_PROJECT"):
        raise SystemExit("GOOGLE_CLOUD_PROJECT is not set — load the project .env and re-run.")

    rows: list[dict] = []
    tmp = Path(tempfile.mkdtemp(prefix="referent_probe_"))
    try:
        for mode in modes:
            arm = ARMS[mode]
            print("\n" + "=" * 78)
            print(f"arm: {mode}   history={arm['history']}  referent-block={arm['block']}"
                  + ("   <- what shipped before 2026-09-03" if mode == "none" else ""))
            print("=" * 78)
            for case in SUITE_B_HARD:
                # Re-installed per case: the block must describe THIS case's prior turn.
                if arm["block"]:
                    _install_prior_turn(case, tmp)
                else:
                    _disable_block(tmp)
                print(f"\n{case['id']}: {case['message']!r}")
                for rep in range(1, args.repeat + 1):
                    res = run_turn(case, COORD_MODEL, args.persona,
                                   with_history=arm["history"])
                    verdict, note = score_b(case, res)
                    res.update(verdict=verdict, note=note, rep=rep, arm=mode,
                               label=case.get("label", ""),
                               live_failure=case.get("live_failure", ""))
                    print(f"  #{rep} {verdict:<10} {res['latency_s']:>6}s  "
                          f"in={res['input_tokens']:>6} cached={res['cached_tokens']:>6}  "
                          f"{note}")
                    rows.append(res)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    summary = summarise(rows)
    print("\n" + "=" * 78)
    print("SUMMARY — pass condition is the ask-rate rising, not only the score")
    print("=" * 78)
    print(f"{'arm':<12} {'n':>3} {'referent':>9} {'dispatch':>9} {'asked':>6} "
          f"{'referent%':>10} {'not-wrong%':>11}")
    for mode, st in summary.items():
        print(f"{mode:<12} {st['n']:>3} {st['referent_ok']:>9} {st['resolved']:>9} "
              f"{st['asked']:>6} {str(st['referent_rate']) + '%':>10} "
              f"{str(st['not_wrong_rate']) + '%':>11}")

    run_date = date.today().isoformat()
    out = Path(args.out) if args.out else (
        ROOT / "tests" / f"referent_probe_{run_date}_{args.label}_flash-lite.json")
    out.write_text(json.dumps(
        {"date": run_date, "model": COORD_MODEL, "persona": args.persona,
         "label": args.label, "repeat": args.repeat,
         "summary": summary, "rows": rows}, indent=2, default=str))
    print(f"\nraw -> {out.relative_to(ROOT)}")

    errs = sum(1 for r in rows if r["verdict"] == "ERROR")
    print(f"{errs} call errors.")
    return 1 if errs else 0


if __name__ == "__main__":
    sys.exit(main())
