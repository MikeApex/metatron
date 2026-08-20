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
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.intake as intake                        # noqa: E402
from tools.intake import Envelope                    # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "intake_fixtures"

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


def classify_code_only(env: Envelope, cfg: dict) -> str:
    """The free path: rules → ledger → headers → unclear. No ledger state in eval —
    the corpus measures the rules and headers as shipped, not one mailbox's history."""
    return intake.classify(env, cfg, ledger={}).category


def classify_with_extractor(env: Envelope, cfg: dict) -> str:
    """Phase 3+: code stages first, the extractor agent on what they leave unclear.

    Dispatched exactly as production will: bare (no personal context), quick tier.
    Import is deferred so the free mode never touches the model stack.
    """
    category = classify_code_only(env, cfg)
    if category != "unclear":
        return category
    from tools.intake_extract import extract_category   # Phase 3 module
    return extract_category(env)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--extractor", action="store_true",
                        help="also run the intake_extractor agent on unclear messages")
    args = parser.parse_args()

    fixtures = load_fixtures()
    if not fixtures:
        print("Corpus is empty.")
        return 2
    cfg = intake.load_config()
    if not cfg.get("categories"):
        # Template only — eval never needs a persona's taught rules.
        cfg = intake._template_defaults()

    classify = classify_with_extractor if args.extractor else classify_code_only

    per_label: dict[str, dict] = defaultdict(lambda: {"tp": 0, "fn": 0, "fp": 0})
    action_required_misses: list[tuple[str, str]] = []
    unclear_count = 0
    results = []

    for fx in fixtures:
        expected = fx["label"]
        got = classify(to_envelope(fx), cfg)
        results.append((fx["_file"], expected, got))
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

    return 1 if action_required_misses else 0


if __name__ == "__main__":
    sys.exit(main())
