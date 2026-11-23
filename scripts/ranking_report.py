#!/usr/bin/env python3
"""
Ranking Part B, phase 1 — the shadow comparison: today's top ten by Part A's score and by the
regret of delay, side by side (archive/plans/ranking_values_plan_2026-11-23.md § 5, § 7.2 item 2).

    .venv/bin/python scripts/ranking_report.py --compare --persona mike
    .venv/bin/python scripts/ranking_report.py --compare --persona mike --day 2026-11-25
    .venv/bin/python scripts/ranking_report.py --compare --persona mike --live

By default it reads the first build of the day at or after waking, which every day plan build
keeps (data/personas/{p}/day_plan/ranking_state.json, 14 days). `--live` computes both orders now,
from the ledger as it stands, without building or writing a plan.

For each v2 row: the tier (MUST — today's list or must start today; ADV — advance work, a
suggestion), the importance G, who bears it (×), the shape and its factor today, the slack in
days, the attention blocks and the cost of delay. A row marked "(fallback)" has no cost record
yet and is read from Part A's stakes. It also says whether v2 would have reshuffled.

VM ONLY, DEVELOPER ONLY. It prints to the terminal and WRITES NOTHING — no file, no model call.
CONSENT, ENFORCED HERE IN CODE: a persona is read only with a current `base_configuration`
record (core/consent.py) — the sign-up consent whose text says the developer can read what the
user tells Metatron (ROADMAP.md § Section 0). No developer special case.
"""
from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_scope  # noqa: E402


def _num(x, fmt: str = "{:.1f}") -> str:
    return "—" if x is None else fmt.format(x)


def _live(day: date, persona: str) -> dict:
    import tools.day_plan as D
    # Part A's order, whatever the flag says: built exactly as `_candidates` builds it flag-off.
    import tools.day_plan_config as C
    saved = C._OVERRIDE
    try:
        cfg = C.load()
        cfg["flags"]["ranking_v2"] = False
        C._OVERRIDE = cfg
        v1 = D._candidates(day, persona)
    finally:
        C._OVERRIDE = saved
    sh = D._shadow(day, persona, v1, None)
    sh.pop("_assessed", None)
    return {"built_at": "now (live)", **sh}


def compare(persona: str, day: date | None = None, live: bool = False) -> str:
    """Both top tens for one persona and day, as text."""
    import tools.obligations as O
    from tools import ranking as RK
    with persona_scope(persona):
        day = day or O._today()
        st = RK.load_state(persona)
        sh = None if live else (st.get("shadow") or {}).get(day.isoformat())
        if sh is None:
            if not live and day != O._today():
                return f"{persona}: no shadow kept for {day.isoformat()} (kept 14 days)."
            sh = _live(day, persona)
        titles = {t["id"]: str(t.get("what") or "?") for t in (O._norm(x) for x in O._load(persona))}

        def title(ref: str) -> str:
            return titles.get(str(ref).split("@")[0], ref)[:44]

        out = [f"Ranking comparison — {persona}, {day.isoformat()} (build {sh.get('built_at')})",
               "", "PART A (live today)                               score"]
        for i, (ref, score) in enumerate((sh.get("v1") or [])[:10], 1):
            out.append(f"{i:>2}. {title(ref):<46}{score:>5}")
        if not sh.get("v1"):
            out.append("    (nothing)")
        out += ["", "REGRET OF DELAY (shadow)                         tier     G   ×   shape     "
                    "factor  slack  blocks   cost"]
        for i, r in enumerate((sh.get("v2") or [])[:10], 1):
            fb = "" if r.get("recorded") else " (fallback)"
            out.append(f"{i:>2}. {(title(r['ref']) + fb)[:46]:<46} "
                       f"{'MUST' if r.get('tier') == 'must' else 'ADV ':<5}"
                       f"{_num(r.get('G'), '{:>5.0f}')} {_num(r.get('bearer'), '{:.1f}')} "
                       f"{str(r.get('shape') or ''):<9}{_num(r.get('factor'), '{:>6.2f}')} "
                       f"{_num(r.get('slack'), '{:>6.1f}')} {_num(r.get('blocks'), '{:>6.1f}')} "
                       f"{_num(r.get('cod'), '{:>6.1f}')}")
        if not sh.get("v2"):
            out.append("    (nothing — the day would be the user's own)")
        out += ["", f"v2 would have reshuffled this build: "
                    f"{'yes — ' + sh.get('why', '') if sh.get('would_reshuffle') else 'no'}"]
        return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--compare", action="store_true", help="print both top tens side by side")
    ap.add_argument("--persona", required=True)
    ap.add_argument("--day", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--live", action="store_true", help="compute now instead of the kept build")
    a = ap.parse_args()
    if not a.compare:
        ap.error("only --compare exists in phase 1")
    from core import consent
    with persona_scope(a.persona):
        if not consent.is_granted("base_configuration", a.persona):
            print(f"{a.persona}: excluded — no base_configuration consent on file. Nothing read.")
            return 1
    print(compare(a.persona, date.fromisoformat(a.day) if a.day else None, live=a.live))
    return 0


if __name__ == "__main__":
    sys.exit(main())
