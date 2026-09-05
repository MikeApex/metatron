"""
tests/run_intake_eval.py — measure intake classification against a labelled corpus.

THE GATE THIS ENFORCES (intake plan, verification § 1–3): before the extractor agent
ever sees a live inbox, it must clear a hand-labelled corpus of real messages on the
model that will actually serve it — A4's standing lesson, applied to triage. The one
number that gates is the FALSE-NEGATIVE RATE ON `action_required`: **zero**, where
`unclear` counts as a pass, because an unclassifiable message surfacing to the user is
the correct failure direction and a small model forced to always pick will pick
confidently and wrongly.

THE CORPUS IS NEVER COMMITTED. `tests/intake_fixtures/` is gitignored — it holds real
messages from the user's own inbox, which are personal data by definition. This runner
is tracked; its data is not. Build the corpus on the machine that holds the mailbox
(the VM, for mike).

Fixture format — one JSON file per message in tests/intake_fixtures/, any filename:

    {
      "label": "bill_statement",          // expected category (required)
      "subject": "...", "sender": "billing@example.com",
      "body": "...",                       // optional but needed for extractor eval
      "signals": {"bulk": true, "list_unsubscribe": true, "labels": []},
      "note": "why this label, if not obvious"
    }

Two modes:

    python3 tests/run_intake_eval.py               # rules/ledger/headers only (free)
    python3 tests/run_intake_eval.py --extractor   # + the intake_extractor agent on
                                                   #   everything the code stages
                                                   #   leave `unclear` (Phase 3+)

The free mode is meaningful on its own: it reports how much of the corpus Python
classifies without a model, which is the fraction of real mail the pipeline handles
at zero token cost.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.intake as intake                        # noqa: E402
from tools.intake import Envelope                    # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "intake_fixtures"

# Filled by _score() so --runs can tabulate without re-plumbing every return value.
_LAST: dict = {"misses": 0, "domain_hit": 0, "domain_scored": 0, "unclear": 0}

# --dump-confidence (2026-09-05). The confidence floor is a dial with a cost on both
# sides — too low silences obligations, too high hands the user back their inbox — and
# picking a number for it needs the model's self-reported confidence PER MESSAGE, not an
# aggregate. `extract()` already returns the field; nothing was recording it. Rows are
# appended only when the flag is set, so the default path is unchanged.
_CONFIDENCE_ROWS: list[dict] = []
_DUMP: dict = {"on": False, "run": 1}

# The categories the corpus may label with — kept in lockstep with
# config/templates/intake.yaml. A label outside this set is a fixture error.
CATEGORIES = {
    "action_required", "correspondence", "booking_confirmation", "bill_statement",
    "invitation", "announcement", "promotion", "notification", "unclear",
}


def load_fixtures() -> list[dict]:
    if not FIXTURES_DIR.exists():
        print(f"No corpus at {FIXTURES_DIR} — create it and add labelled messages.\n"
              f"(Gitignored on purpose: real messages are personal data. Build it on\n"
              f"the machine that holds the mailbox.)")
        sys.exit(2)
    fixtures = []
    for path in sorted(FIXTURES_DIR.glob("*.json")):
        try:
            fx = json.loads(path.read_text())
        except Exception as exc:
            print(f"  SKIP {path.name}: unreadable ({exc})")
            continue
        label = fx.get("label")
        if label not in CATEGORIES:
            print(f"  SKIP {path.name}: label {label!r} not in the closed enum")
            continue
        fx["_file"] = path.name
        fixtures.append(fx)
    return fixtures


def to_envelope(fx: dict) -> Envelope:
    return Envelope(
        channel="eval", native_id=fx["_file"],
        received=fx.get("received") or datetime.now().isoformat(timespec="seconds"),
        sender_address=(fx.get("sender") or "").lower(),
        sender_display=fx.get("sender_display") or fx.get("sender") or "",
        subject=fx.get("subject") or "",
        body=(fx.get("body") or "")[:2000],
        thread_id="", signals=fx.get("signals") or {},
    )


def classify_code_only(env: Envelope, cfg: dict) -> tuple[str, str | None]:
    """The free path: rules → ledger → headers → unclear. No ledger state in eval —
    the corpus measures the rules and headers as shipped, not one mailbox's history.

    Returns `(category, domain)`. The code tier has no domain *opinion* — it reads the
    per-category default out of config — so a domain score in this mode measures the
    defaults table, not a classifier. Reported separately for that reason.
    """
    result = intake.classify(env, cfg, ledger={})
    return result.category, result.domain


def classify_with_extractor(env: Envelope, cfg: dict) -> tuple[str, str | None]:
    """Phase 3+: code stages first, the extractor agent on what they leave unclear.

    Dispatched exactly as production will: bare (no personal context), quick tier.
    Import is deferred so the free mode never touches the model stack.

    Mirrors the sweep's precedence (tools/intake.py): the model's domain beats the
    category default; no opinion falls through to the default.
    """
    category, domain = classify_code_only(env, cfg)
    if category != "unclear":
        return category, domain
    from tools.intake_extract import extract, has_domain_opinion   # Phase 3 module
    found = extract(env)
    if _DUMP["on"]:
        _CONFIDENCE_ROWS.append({
            "run": _DUMP["run"], "file": env.native_id,
            "category": found.get("category"),
            "confidence": found.get("confidence"),
            "domain": (found["domain"] if has_domain_opinion(found) else "_unresolved"),
            "important": found.get("important"),
        })
    if found["category"] == "unclear":
        return "unclear", domain
    resolved = (found["domain"] if has_domain_opinion(found)
                else intake._effective_domain(found["category"], cfg))
    return found["category"], resolved


def _norm_domain(value) -> str:
    """Fixture and runtime domains onto one vocabulary. `""` means unlabelled."""
    if value is None:
        return "null"
    text = str(value).strip().lower()
    return "null" if text in ("null", "none") else text


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--extractor", action="store_true",
                        help="also run the intake_extractor agent on unclear messages")
    # Added 2026-09-03: without it the runner dies in resolve_persona() before reading
    # a single fixture. Fail-closed persona resolution is correct and this runner had
    # simply never supplied one — it had never been run against a real corpus.
    parser.add_argument("--persona", default="mike",
                        help="whose intake.yaml supplies the rules (default: mike)")
    # Added 2026-09-04. A single run cannot gate this: measured on one corpus and one
    # unchanged agent file, five consecutive runs returned 1, 3, 1, 1 and 2
    # `action_required` false negatives. The model's answer moves between identical
    # runs, so "the gate passed" from one run means only that it passed that time.
    # THE GATE IS SCORED ON THE WORST RUN, never the last or the mean — a classifier
    # that silences an obligation one time in five silences it in production.
    parser.add_argument("--runs", type=int, default=1,
                        help="repeat N times and gate on the worst run (model modes only)")
    parser.add_argument("--variant", default="",
                        help="agent file to test instead of intake_extractor "
                             "(e.g. intake_extractor_counterargue)")
    parser.add_argument("--dump-confidence", default="", metavar="PATH",
                        help="write one JSONL row per model-answered message "
                             "(run, file, category, confidence, domain) — the raw "
                             "material for choosing extractor.confidence_threshold")
    args = parser.parse_args()

    fixtures = load_fixtures()
    if not fixtures:
        print("Corpus is empty.")
        return 2
    if args.variant:
        os.environ["METATRON_INTAKE_EXTRACTOR_AGENT"] = args.variant
        print(f"variant agent: {args.variant}")

    _DUMP["on"] = bool(args.dump_confidence and args.extractor)
    if args.dump_confidence and not args.extractor:
        print("--dump-confidence needs --extractor: the code tier reports no confidence.")
        return 2

    from core.persona import persona_scope
    with persona_scope(args.persona):
        if args.runs <= 1:
            rc = _score(fixtures, args)
            _write_confidence_dump(args)
            return rc

        worst, summaries = 0, []
        for i in range(1, args.runs + 1):
            print(f"\n{'=' * 62}\nRUN {i} of {args.runs}\n{'=' * 62}")
            _DUMP["run"] = i
            rc = _score(fixtures, args)
            _write_confidence_dump(args)   # after every run: a crash mid-sweep
                                           # must not cost the runs already paid for
            if rc == 3:
                summaries.append((i, None, 0, 0, 0))   # INVALID — never scored
                continue
            summaries.append((i, _LAST["misses"], _LAST["domain_hit"],
                              _LAST["domain_scored"], _LAST["unclear"]))
            worst = max(worst, rc)

        print(f"\n{'=' * 62}\nACROSS {args.runs} RUNS\n{'=' * 62}")
        print(f"{'run':>4} {'gate misses':>12} {'domain':>10} {'said unclear':>13}")
        for i, misses, dh, ds, unc in summaries:
            dom = f"{dh}/{ds}" if ds else "-"
            shown = "INVALID" if misses is None else misses
            print(f"{i:>4} {shown:>12} {dom:>10} {unc:>13}")

        # An INVALID run is excluded, not counted as a clean zero. Averaging a refused
        # run into the gate is exactly how three void runs once read as three passes.
        scored = [s for s in summaries if s[1] is not None]
        if not scored:
            print("\nNO RUN WAS SCORED — every run hit the spend guard. Re-run each "
                  "pass as its own process.")
            return 3
        if len(scored) < len(summaries):
            print(f"\n⚠ {len(summaries) - len(scored)} of {args.runs} runs INVALID and "
                  f"excluded — the gate below rests on {len(scored)} run(s).")
        worst_misses = max(s[1] for s in scored)
        best_misses = min(s[1] for s in scored)
        print(f"\ngate misses: worst {worst_misses}, best {best_misses}")
        if worst_misses != best_misses:
            print("  ⚠ the gate's answer is not stable across identical runs — "
                  "the worst run is the honest one")
        print(f"unclear rate: "
              f"{sum(s[4] for s in scored)}/{len(fixtures) * len(scored)} "
              f"across {len(scored)} scored run(s)")
        return 1 if worst_misses else 0


def _guard_state(n: int) -> tuple[bool, str]:
    """`(safe_to_score, message)` — will the spend guard refuse part of this run?

    ADDED 2026-09-05, AFTER A SWEEP SCORED THREE VOID RUNS AS PASSES. The rate guard
    counts every extractor call as a pipeline session in an in-process deque, and stops
    at `stop_sessions_per_hour` (60). A `--runs 5` sweep over 33 fixtures asks for 165
    in one process, so runs 3-5 were refused wholesale. `extract()` turns any failure
    into `unclear` by design, `unclear` counts as a gate PASS by design, and the two
    correct behaviours compose into a runner that printed **0 gate misses** for three
    runs in which the model was never called at all.

    This is the same shape as the 2026-09-04 A/B/C observation that "run 3 of every
    variant collapsed identically to 32/33 unclear" — attributed then to a transient API
    failure. It was the guard, and it was deterministic: the third run is exactly where
    a 33-message corpus crosses 60 calls in one process.

    A run that cannot be scored must say so instead of scoring well. Invoke each run as
    its own process (`--runs 1` in a shell loop) to reset the counter; do not lift the
    guard, which is a safety net and not this runner's to move.
    """
    try:
        from core import spend_guard
        cfg = spend_guard._load_config()
        stop = int(cfg.get("stop_sessions_per_hour", 0) or 0)
        if not stop:
            return True, ""
        used = spend_guard._sessions_last_hour()
        if used + n > stop:
            return False, (f"spend guard: {used} sessions used this hour, this run needs "
                           f"{n} more, limit is {stop}. {used + n - stop} message(s) "
                           f"would be REFUSED and scored as `unclear` — which counts as "
                           f"a gate pass. Run each pass as its own process instead.")
        return True, ""
    except Exception:
        return True, ""   # never let the check itself stop an eval


def _write_confidence_dump(args) -> None:
    """Rewrite the JSONL from scratch each call — the rows are cumulative in memory,
    so this is idempotent and safe to call after every run."""
    if not _DUMP["on"]:
        return
    path = Path(args.dump_confidence)
    path.write_text("\n".join(json.dumps(r) for r in _CONFIDENCE_ROWS) + "\n")
    print(f"\nconfidence dump: {len(_CONFIDENCE_ROWS)} rows -> {path}")


def _score(fixtures: list[dict], args) -> int:
    cfg = intake.load_config()
    if not cfg.get("categories"):
        # Template only — eval never needs a persona's taught rules.
        cfg = intake._template_defaults()

    classify = classify_with_extractor if args.extractor else classify_code_only

    if args.extractor:
        safe, why = _guard_state(len(fixtures))
        if not safe:
            print(f"\n*** RUN NOT SCORED — {why}")
            return 3   # INVALID, distinct from pass (0) and gate failure (1)

    per_label: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0})
    action_required_misses: list[tuple[str, str]] = []
    unclear_count = 0
    results = []

    domain_hit = domain_miss = 0
    domain_unlabelled = 0
    domain_mismatches: list[tuple[str, str, str]] = []

    for fx in fixtures:
        expected = fx["label"]
        got, got_domain = classify(to_envelope(fx), cfg)
        results.append((fx["_file"], expected, got))

        # The second axis, scored separately and never gating. A fixture with no
        # `domain` written is skipped rather than counted wrong — the corpus was
        # labelled on one axis before this one existed, and silently scoring those
        # as failures would make a partial corpus look like a broken classifier.
        want_domain = (fx.get("domain") or "").strip()
        if not want_domain:
            domain_unlabelled += 1
        elif _norm_domain(want_domain) == _norm_domain(got_domain):
            domain_hit += 1
        else:
            domain_miss += 1
            domain_mismatches.append(
                (fx["_file"], _norm_domain(want_domain), _norm_domain(got_domain)))
        if got == "unclear":
            unclear_count += 1
        if got == expected:
            per_label[expected]["tp"] += 1
        else:
            per_label[expected]["fn"] += 1
            per_label[got]["fp"] += 1
            # THE number: an action_required message classified as anything that is
            # not surfaced-by-default. `unclear` surfaces, so it is a pass here.
            if expected == "action_required" and got != "unclear":
                action_required_misses.append((fx["_file"], got))

    print(f"\nCorpus: {len(fixtures)} messages · mode: "
          f"{'code + extractor' if args.extractor else 'code only (no model)'}\n")
    print(f"{'label':<22} {'n':>4} {'precision':>10} {'recall':>8}")
    for label in sorted(per_label):
        s = per_label[label]
        n = s["tp"] + s["fn"]
        prec = s["tp"] / (s["tp"] + s["fp"]) if (s["tp"] + s["fp"]) else float("nan")
        rec = s["tp"] / n if n else float("nan")
        print(f"{label:<22} {n:>4} {prec:>10.2f} {rec:>8.2f}")

    resolved = len(fixtures) - unclear_count
    print(f"\nClassified without surfacing to user: {resolved}/{len(fixtures)} "
          f"({100 * resolved / len(fixtures):.0f}%) — the zero-token fraction"
          if not args.extractor else
          f"\nStill unclear after extractor: {unclear_count}/{len(fixtures)}")

    # ── Domain axis (2026-09-03) ─────────────────────────────────────────────
    scored = domain_hit + domain_miss
    print(f"\ndomain axis: {domain_hit}/{scored} correct"
          + (f" ({100 * domain_hit / scored:.0f}%)" if scored else "")
          + (f" · {domain_unlabelled} fixture(s) carry no domain label"
             if domain_unlabelled else ""))
    if not args.extractor and scored:
        print("  (code-only mode: this scores the per-category defaults in "
              "intake.yaml, not a classifier — the model is what answers this axis)")
    for name, want, got in domain_mismatches:
        print(f"  DOMAIN {name}: expected {want}, got {got}")

    print(f"\naction_required false negatives (the gate — must be 0): "
          f"{len(action_required_misses)}")
    for name, got in action_required_misses:
        print(f"  MISS {name}: classified {got}")

    mismatches = [(f, e, g) for f, e, g in results if e != g and g != "unclear"]
    if mismatches:
        print(f"\nOther hard mismatches ({len(mismatches)}):")
        for name, expected, got in mismatches:
            if expected != "action_required":
                print(f"  {name}: expected {expected}, got {got}")

    _LAST.update(misses=len(action_required_misses), domain_hit=domain_hit,
                 domain_scored=domain_hit + domain_miss, unclear=unclear_count)
    return 1 if action_required_misses else 0


if __name__ == "__main__":
    sys.exit(main())
