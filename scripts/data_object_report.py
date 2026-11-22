#!/usr/bin/env python3
"""
The logs users invent, side by side — the developer's view for promotion (R6, R21, R29).

archive/plans/data_objects_phase2_build_plan_2026-11-22.md § 3.7. Every user's ASKED and NOTICED
logs — names, aliases, field names — grouped by their distinguishing words, so a log several
users invent stands out as a candidate template. Mike reads it and decides what becomes a
template (a config/data_objects/*.yaml file, plus whatever code the object then needs — R29).
Each user's offer yes rate is printed beside them (R34's measure).

VM ONLY, DEVELOPER ONLY. It prints to the terminal and WRITES NOTHING — no file, no tracked
output, no model call. Run it over SSH:

    .venv/bin/python scripts/data_object_report.py

CONSENT, ENFORCED HERE IN CODE: a user is read only with a current `base_configuration` record
in `data/personas/{p}/consents.json` — the sign-up consent whose text says Mike, as developer,
can read what they tell Metatron (ROADMAP.md § Section 0). Anyone without it is named as
excluded and nothing of theirs is read. No developer special case: `mike` is covered by the same
record (seeded with `scripts/accounts.py seed-consent`).

R21's rejected alternative stands: no model compares users' names — that would put two users'
content in one prompt. Grouping is lexical, by code.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_scope  # noqa: E402

_INVENTED = ("asked", "noticed")


def _personas(personas_dir: Path) -> list[str]:
    return sorted(p.name for p in personas_dir.iterdir()
                  if p.is_dir() and not p.name.startswith((".", "_")))


def report(personas_dir: Path | None = None) -> str:
    from core import consent
    from tools import data_objects as DO
    from tools import noticed_logs as NL
    personas_dir = personas_dir or (ROOT / "data" / "personas")
    included, excluded = [], []
    groups: dict[str, list[str]] = {}
    rates: list[str] = []
    for p in _personas(personas_dir):
        try:
            ok = consent.is_granted("base_configuration", p)
        except Exception:  # noqa: BLE001 — an unreadable record is no record
            ok = False
        if not ok:
            excluded.append(p)
            continue
        included.append(p)
        with persona_scope(p):
            for o in DO._stored():
                if str(o.get("origin") or "") not in _INVENTED:
                    continue
                fields = [f for f in (o.get("fields") or {}) if f != "notes"]
                aka = f" (also: {', '.join(o['aliases'])})" if o.get("aliases") else ""
                fl = f" [fields: {', '.join(fields)}]" if fields else ""
                line = (f"    {p}: {o['name']}{aka}{fl} — {o.get('origin')}"
                        + (f", {o.get('status')}" if o.get("status") != "active" else ""))
                groups.setdefault(DO._core(o["name"]), []).append(line)
            s = NL.summary(p)
            rate = "—" if s["yes_rate"] is None else f"{s['yes_rate']:.0%}"
            rates.append(f"  {p}: {s['cards']} offers raised · yes rate {rate} · "
                         + (", ".join(f"{k} {v}" for k, v in sorted(s["by_status"].items()))
                            or "none"))
    out = [f"Logs users invented — {len(included)} user(s): {', '.join(included) or 'none'}"]
    if excluded:
        out.append(f"  excluded, no base_configuration consent: {', '.join(excluded)}")
    out.append("")
    if not groups:
        out.append("  no asked or noticed logs yet")
    # Most widely invented first: the number of different users is the promotion signal.
    for key, lines in sorted(groups.items(),
                             key=lambda kv: (-len({ln.split(':')[0] for ln in kv[1]}), kv[0])):
        users = len({ln.split(":")[0].strip() for ln in lines})
        out.append(f"  \"{key}\" — {users} user(s)")
        out.extend(lines)
    out.append("")
    out.append("Offers (noticed logs):")
    out.extend(rates or ["  none"])
    return "\n".join(out)


def main() -> int:
    argparse.ArgumentParser(prog="data_object_report", description=__doc__.split("\n")[1]) \
        .parse_args()
    print(report())
    return 0


if __name__ == "__main__":
    sys.exit(main())
