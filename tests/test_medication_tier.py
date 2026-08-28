"""
tests/test_medication_tier.py — a missed anti-psychotic no longer ranks like a
missed statin ([DB-0808-14], spec: archive/plans/medication_ranking_spec_2026-08-27.md).

`_thread_tier()` ranks a `MEDICATION_MISSED_CRITICAL: <name>` flag tier 2 (the
non-resolvable watch lifecycle) when the STORED medication profile marks that
medication `discontinuation_risk: true` — and tier 1 otherwise. The classification
comes from the profile, never the flag text or the model's note, and every failure
direction falls back to tier 1 (today's safe-but-undifferentiated behaviour).

Run: python3 tests/test_medication_tier.py
"""

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.context_tracker import _thread_tier  # noqa: E402
import tools.agent_config as agent_config  # noqa: E402

PROFILE = json.dumps({
    "medications": [
        {"name": "sertraline", "criticality": "required", "discontinuation_risk": True},
        {"name": "atorvastatin", "criticality": "required", "discontinuation_risk": False},
        {"name": "lamotrigine", "criticality": "required"},   # field absent — legacy entry
    ]
})

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


def tier(flag: str, profile: str | None = PROFILE, raises: bool = False):
    if raises:
        patcher = mock.patch.object(agent_config, "read_agent_config",
                                    side_effect=OSError("store unreadable"))
    else:
        patcher = mock.patch.object(agent_config, "read_agent_config",
                                    return_value=profile)
    with patcher:
        return _thread_tier(flag)


def main() -> int:
    # The distinction the module's own design comment named and never wired in.
    check("missed sertraline (discontinuation_risk: true) ranks tier 2",
          tier("MEDICATION_MISSED_CRITICAL: sertraline") == 2)
    check("missed atorvastatin (risk: false) stays tier 1",
          tier("MEDICATION_MISSED_CRITICAL: atorvastatin") == 1)
    check("name matching is case-insensitive",
          tier("MEDICATION_MISSED_CRITICAL: Sertraline") == 2)

    # The fallback directions — every failure lands on tier 1, never invents risk.
    check("bare flag with no name suffix falls back to tier 1",
          tier("MEDICATION_MISSED_CRITICAL") == 1)
    check("a medication not in the profile falls back to tier 1",
          tier("MEDICATION_MISSED_CRITICAL: unknowndrug") == 1)
    check("a legacy entry without the field falls back to tier 1",
          tier("MEDICATION_MISSED_CRITICAL: lamotrigine") == 1)
    check("an unreadable profile store falls back to tier 1",
          tier("MEDICATION_MISSED_CRITICAL: sertraline", raises=True) == 1)
    check("a not-found message instead of JSON falls back to tier 1",
          tier("MEDICATION_MISSED_CRITICAL: sertraline",
               profile="No config found for physical_health") == 1)

    # The existing behaviour is untouched.
    check("CLINICAL_CONCERN is still tier 2, no profile read involved",
          tier("CLINICAL_CONCERN: SUICIDAL_IDEATION", raises=True) == 2)
    check("an ordinary flag is still tier 1",
          tier("SLEEP_POOR") == 1)

    print()
    failed = [label for ok, label in _results if not ok]
    if failed:
        print(f"{len(failed)} check(s) FAILED:")
        for label in failed:
            print(f"  - {label}")
        return 1
    print(f"All {len(_results)} medication-tier checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
