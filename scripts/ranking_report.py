#!/usr/bin/env python3
"""
Ranking Part B, phase 1 — the shadow comparison: today's top ten by Part A's score and by the
regret of delay, side by side (archive/plans/ranking_values_plan_2026-11-23.md § 5, § 7.2 item 2).

    .venv/bin/python scripts/ranking_report.py --compare --persona mike
    .venv/bin/python scripts/ranking_report.py --compare --persona mike --day 2026-11-25
    .venv/bin/python scripts/ranking_report.py --compare --persona mike --live
    .venv/bin/python scripts/ranking_report.py --protected --persona mike [--day …]
    .venv/bin/python scripts/ranking_report.py --behind --persona mike [--day …]
    .venv/bin/python scripts/ranking_report.py --back-burner --persona mike [--day …]
    .venv/bin/python scripts/ranking_report.py --signals --persona mike [--month 2026-12]

Phase 2 (plan § 11b): `--protected` lists each task placed in protected time that day and what
`protected_v2` would have done — asked (its cost of delay beat the intrusion cost) or kept it out —
with the window's class, k and both costs; once the flag acts, the questions actually put and
their decisions. `--behind` prints what `behind_v2` read at the first build after waking: behind
or not and why, the quick wins and the hard task it would have led with, and the raises it would
have made beside Part A's slipped-task asks. Both read `trace` in ranking_state.json (14 days).

Phase 3 (plan § 11c): `--back-burner` prints the day's back-burner reading — what would be parked
(trivia nobody has mentioned for 21 days), what is close (14+ days, to be said in the weekly
conversation first) and what is guarded (a person, an obligation, health, a goal, more than trivia:
asked about, never parked) — and whether the pass ran as the dry run, notices only, or live. It is
the dry-run walkthrough's list. `--signals` prints one month of ranking_signals.jsonl for the
monthly review (§ 7.2): the ledger's daily rows summed, and the user's own words, by kind.

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


def trace(persona: str, day: date | None, what: str) -> str:
    """Phase 2's kept shadow for one day: `protected` or `behind`, as text."""
    import tools.obligations as O
    from tools import ranking as RK
    with persona_scope(persona):
        day = day or O._today()
        tr = ((RK.load_state(persona).get("trace") or {}).get(day.isoformat())) or {}
        titles = {t["id"]: str(t.get("what") or "?") for t in (O._norm(x) for x in O._load(persona))}

        def title(tid) -> str:
            return titles.get(str(tid or "").split("@")[0], str(tid))[:44]

        out = [f"Ranking phase 2 — {what} — {persona}, {day.isoformat()}", ""]
        if what == "protected":
            rows = list((tr.get("protected") or {}).values())
            out.append("SHADOW — placed in protected time by today's rule; protected_v2 would have:")
            for r in rows:
                w = r.get("windows") or [{}]
                out.append(f"  {title(r.get('task_id')):<46} {str(w[0].get('class')):<9} "
                           f"k {_num(w[0].get('k'), '{:.2f}')}  intrusion {_num(r.get('cost'))}  "
                           f"delay {_num(r.get('cod'))}  → {r.get('would')}"
                           + (f" (suggest {r['recommend']})" if r.get("recommend") else ""))
            if not rows:
                out.append("  (nothing took protected time)")
            acted = list((tr.get("intrusions") or {}).values())
            if acted:
                out += ["", "ACTING — questions and decisions:"]
                for x in acted:
                    out.append(f"  {title(x.get('task_id')):<46} {str(x.get('class')):<9} "
                               f"intrusion {_num(x.get('cost'))}  delay {_num(x.get('cod'))}  "
                               f"→ {x.get('decision')}")
        else:
            b = tr.get("behind")
            if not b:
                return "\n".join(out + ["  (no behind reading kept for this day)"])
            out.append(f"behind: {'YES — ' + b.get('why', '') if b.get('behind') else 'no'} "
                       f"(overdue {b.get('overdue')}, top task skipped {b.get('top_skipped')})")
            if b.get("behind"):
                out.append(f"hard task: {title(b.get('hard')) if b.get('hard') else '—'}")
                out.append("quick wins first: " + (", ".join(title(t) for t in b.get("quick_wins") or [])
                                                   or "none fit")
                           + (" (the first is a step of the hard task)" if b.get("first_step") else ""))
            out.append("would raise: " + (", ".join(title(t) for t in b.get("raises") or []) or "nothing"))
            out.append("to the weekly list: " + (", ".join(title(t) for t in b.get("weekly") or []) or "nothing"))
            out.append("Part A asks instead: " + (", ".join(title(t) for t in b.get("part_a_slips") or [])
                                                  or "nothing"))
        return "\n".join(out)


def back_burner(persona: str, day: date | None) -> str:
    """Phase 3's back-burner reading for one day, as text (the dry-run walkthrough's list)."""
    import tools.obligations as O
    from tools import ranking as RK
    with persona_scope(persona):
        day = day or O._today()
        tr = ((RK.load_state(persona).get("trace") or {}).get(day.isoformat())) or {}
        bb = tr.get("back_burner")
        out = [f"Ranking phase 3 — back burner — {persona}, {day.isoformat()}", ""]
        if not bb:
            return "\n".join(out + ["  (no back-burner reading kept for this day — the pass runs on "
                                    "the first tick after midnight)"])
        titles = {t["id"]: str(t.get("what") or "?") for t in (O._norm(x) for x in O._load(persona))}

        def row(r: dict) -> str:
            return (f"  {titles.get(r['task_id'], r['task_id'])[:52]:<54} silent {r['silent']:>3} d  "
                    f"delay {_num(r.get('cod'))}"
                    + (f"  said {r['noticed']}" if r.get("noticed") else "")
                    + (f"  [{r['why']}]" if r.get("why") else ""))
        out.append(f"mode: {bb.get('mode')}  (dry run = nothing parked or said; notices only = said "
                   f"in the weekly conversation, nothing parked; live = parked a week after it is said)")
        for key, head in (("would_archive", "WOULD BE PARKED (21+ days, trivia):"),
                          ("would_notice", "CLOSE — said in the weekly conversation first (14–20 days):"),
                          ("guarded", "GUARDED — asked about once in the weekly conversation, never parked:")):
            rows = bb.get(key) or []
            out += ["", head] + ([row(r) for r in rows] or ["  (none)"])
        return "\n".join(out)


def signals(persona: str, month: str | None) -> str:
    """One month of ranking_signals.jsonl for the monthly review (plan § 7.2, B32), as text."""
    import tools.obligations as O
    from tools import ranking_review as RR
    with persona_scope(persona):
        month = month or O._today().strftime("%Y-%m")
        rows = [r for r in RR.read_signals(persona) if str(r.get("day") or "").startswith(month)]
        out = [f"Ranking signals — {persona}, {month} ({len(rows)} rows)", ""]
        if not rows:
            return "\n".join(out + ["  (nothing recorded this month — is ranking_signals on?)"])
        led = [r for r in rows if r.get("source") == "ledger"]
        days = sorted({r["day"] for r in led})
        out.append(f"LEDGER — {len(days)} day(s), {days[0] if days else '—'} to {days[-1] if days else '—'}")
        states: dict = {}
        tot = {"opened": 0, "parked": 0, "goal_steps_done": 0, "missed_max": 0, "intrusions": 0,
               "prompts": 0, "raises": 0, "weekly_items": 0, "notices": 0,
               "grade_corrections": 0, "replans": 0}
        within = clocks = 0
        decisions: dict = {}
        for r in led:
            k = r.get("kind")
            if k == "completion":
                for st, n in (r.get("states") or {}).items():
                    states[st] = states.get(st, 0) + int(n)
                tot["opened"] += int(r.get("opened") or 0)
                tot["parked"] += int(r.get("parked") or 0)
            elif k == "momentum":
                tot["goal_steps_done"] += int(r.get("goal_steps_done") or 0)
                within += int(r.get("clocks_within") or 0)
                clocks += int(r.get("clocks") or 0)
            elif k == "missed_obligations":
                tot["missed_max"] = max(tot["missed_max"], int(r.get("n") or 0))
            elif k == "intrusions":
                tot["intrusions"] += int(r.get("n") or 0)
                for d, n in (r.get("decisions") or {}).items():
                    decisions[d] = decisions.get(d, 0) + int(n)
            elif k == "questions":
                for f in ("prompts", "raises", "weekly_items", "notices"):
                    tot[f] += int(r.get(f) or 0)
            elif k == "overrides":
                tot["grade_corrections"] += int(r.get("grade_corrections") or 0)
                tot["replans"] += int(r.get("replans") or 0)
        out += [f"  completion: {', '.join(f'{k} {v}' for k, v in sorted(states.items())) or 'nothing'}"
                f"; opened {tot['opened']}; parked {tot['parked']}",
                f"  momentum: goal steps done {tot['goal_steps_done']}; clocks inside their cadence "
                f"{within} of {clocks} day-readings",
                f"  missed obligations (worst day): {tot['missed_max']}",
                f"  protected time taken: {tot['intrusions']}; questions "
                f"{', '.join(f'{k} {v}' for k, v in sorted(decisions.items())) or 'none'}",
                f"  questions this plan asked: prompts {tot['prompts']}, raises {tot['raises']}, "
                f"weekly items {tot['weekly_items']}, notices {tot['notices']}",
                f"  overrides (recorded, not scored): grade corrections {tot['grade_corrections']}, "
                f"replans {tot['replans']}"]
        said = [r for r in rows if r.get("source") == "user"]
        out += ["", f"IN THEIR WORDS — {len(said)}"]
        for kind in RR.SIGNAL_KINDS:
            mine = [r for r in said if r.get("kind") == kind]
            if mine:
                out.append(f"  {kind}:")
                out += [f"    {r.get('day')} {'(asked) ' if r.get('asked') else ''}\"{r.get('text')}\""
                        for r in mine]
        other = [r for r in rows if r.get("source") not in ("ledger", "user")]
        if other:
            out += ["", f"OTHER ROWS (read, not written here — e.g. goal network satisfaction): {len(other)}"]
            kinds: dict = {}
            for r in other:
                kinds[str(r.get("kind"))] = kinds.get(str(r.get("kind")), 0) + 1
            out.append("  " + ", ".join(f"{k} {v}" for k, v in sorted(kinds.items())))
        return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--compare", action="store_true", help="print both top tens side by side")
    ap.add_argument("--protected", action="store_true", help="phase 2: protected time, shadow")
    ap.add_argument("--behind", action="store_true", help="phase 2: behind and raises, shadow")
    ap.add_argument("--back-burner", dest="back_burner", action="store_true",
                    help="phase 3: what would be parked, what is close, what is guarded")
    ap.add_argument("--signals", action="store_true", help="phase 3: one month of signals")
    ap.add_argument("--month", help="YYYY-MM for --signals (default: this month)")
    ap.add_argument("--persona", required=True)
    ap.add_argument("--day", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--live", action="store_true", help="compute now instead of the kept build")
    a = ap.parse_args()
    if not (a.compare or a.protected or a.behind or a.back_burner or a.signals):
        ap.error("one of --compare, --protected, --behind, --back-burner, --signals")
    from core import consent
    with persona_scope(a.persona):
        if not consent.is_granted("base_configuration", a.persona):
            print(f"{a.persona}: excluded — no base_configuration consent on file. Nothing read.")
            return 1
    day = date.fromisoformat(a.day) if a.day else None
    if a.compare:
        print(compare(a.persona, day, live=a.live))
    for what in ("protected", "behind"):
        if getattr(a, what):
            print(trace(a.persona, day, what))
    if a.back_burner:
        print(back_burner(a.persona, day))
    if a.signals:
        print(signals(a.persona, a.month))
    return 0


if __name__ == "__main__":
    sys.exit(main())
