#!/usr/bin/env python3
"""
scripts/check_day_plan_step2.py — did day planner step 2 behave live? Run ON THE VM, read-only.

Step 2 (2026-10-29, `3d3524a`) turned on `nudges` and `owns_checkins`. Its five live checks
(handoff 2026-10-27 § 2.3) are decided by real days passing, so they are read from the records
those days leave rather than watched:

  1. a leave-now nudge reaches the phone with its text   day_plan/state.json + push_log.jsonl
  2. a nudge the model holds leaves no conversation row  day_plan/state.json + metatron.db
  3. no fixed companion_checkin fires                    the scheduler unit's journal
  4. an empty-day check-in arrives after idle hours      day_plan/log.jsonl
  5. nothing is sent inside quiet hours                  day_plan/log.jsonl + push_log.jsonl

plus the delivery picture behind all of them: pings sent, fetched, and fallen back, with the
phone's own reasons. Each check prints PASS, FAIL or NOT SEEN YET (the situation has not come up),
with ids, counts and times only — never a title or a message.

    gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \\
      --tunnel-through-iap --command='cd ~/multi-model-mcp && \\
      .venv/bin/python scripts/check_day_plan_step2.py --persona mike --since 2026-10-29T12:00'

WHAT RETIRES IT (.claude/rules/deploy.md, the standing rule on new machinery): the backlog item
that carries these checks. When all five pass, the item closes and this file is deleted with it.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def _jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text().splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            pass
    return rows


def _t(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(s)[:19])
    except ValueError:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--persona", required=True)
    ap.add_argument("--since", required=True, help="persona-local, e.g. 2026-10-29T12:00")
    a = ap.parse_args()
    since = datetime.fromisoformat(a.since)
    p = a.persona

    from core.persona import persona_scope
    from core.scheduler import _load_config, time_in_quiet_hours
    import tools.obligations as O
    with persona_scope(p):
        local_now = O._now()
        cfg = _load_config(p)
    # Three clocks: the plan is persona-local, push_log is the VM's local time, the DB is UTC.
    to_local_from_utc = timedelta(minutes=round((local_now - datetime.utcnow()).total_seconds() / 900) * 15)
    to_local_from_vm = timedelta(minutes=round((local_now - datetime.now()).total_seconds() / 900) * 15)

    data = ROOT / "data" / "personas" / p
    state = json.loads((data / "day_plan" / "state.json").read_text()) \
        if (data / "day_plan" / "state.json").exists() else {}
    handled = [(k, v.get("outcome"), _t(v.get("at")))
               for day in (state.get("handled") or {}).values() for k, v in day.items()]
    handled = [h for h in handled if h[2] and h[2] >= since]
    plan_log = [r for r in _jsonl(data / "day_plan" / "log.jsonl") if (_t(r.get("at")) or since) >= since]
    push = []
    for r in _jsonl(data / "push_log.jsonl"):
        at = _t(r.get("at"))
        if at and at + to_local_from_vm >= since:
            push.append({**r, "_at": at + to_local_from_vm})
    sent = {r["id"]: r["_at"] for r in push if r.get("event") == "fcm_sent"}
    fetched = {r["id"] for r in push if r.get("event") == "fcm_fetched"}

    def delivered(at: datetime) -> str:
        """The first ping sent within two minutes after `at`: fetched, or fell back."""
        ids = [i for i, s in sent.items() if at - timedelta(seconds=30) <= s <= at + timedelta(minutes=2)]
        if not ids:
            return "no ping"
        return "fetched" if ids[0] in fetched else "FALLBACK"

    results = []

    # 1. leave-now nudge with its text
    leave = [h for h in handled if h[0].startswith("nudge:travel:") and h[1] == "sent"]
    if not leave:
        results.append(("1 leave-now nudge arrives with text", "NOT SEEN YET", "no leave-now nudge sent"))
    else:
        d = [(h[2], delivered(h[2])) for h in leave]
        ok = all(x == "fetched" for _, x in d)
        results.append(("1 leave-now nudge arrives with text", "PASS" if ok else "FAIL",
                        ", ".join(f"{t:%m-%d %H:%M} {x}" for t, x in d)))

    # 2. a held nudge leaves no conversation row
    held = [h for h in handled if h[1] == "held"]
    if not held:
        results.append(("2 held nudge leaves no row", "NOT SEEN YET", "no nudge held"))
    else:
        db = ROOT / "data" / "conversations" / "metatron.db"
        rows = []
        if db.exists():
            with sqlite3.connect(db) as c:
                rows = [datetime.fromisoformat(ts.rstrip("Z")[:19]) + to_local_from_utc
                        for (ts,) in c.execute("SELECT ts FROM exchanges WHERE persona = ? AND "
                                               "proactive = 1", (p,))]
        leaks = [h for h in held if any(h[2] - timedelta(minutes=5) <= r <= h[2] + timedelta(minutes=1)
                                        for r in rows)]
        results.append(("2 held nudge leaves no row", "FAIL" if leaks else "PASS",
                        f"{len(held)} held, {len(leaks)} with a proactive row beside them"))

    # 3. no fixed companion_checkin fires
    j = subprocess.run(["journalctl", "-u", f"metatron-scheduler@{p}", "--since",
                        (since - to_local_from_vm).strftime("%Y-%m-%d %H:%M"), "--no-pager"],
                       capture_output=True, text=True).stdout
    fired = j.count("firing companion_checkin")
    skipped = j.count("skipping companion_checkin — the day plan owns check-ins")
    results.append(("3 no fixed check-in fires",
                    "FAIL" if fired else ("PASS" if skipped else "NOT SEEN YET"),
                    f"fired {fired}, skipped as owned {skipped}"))

    # 4. empty-day check-in
    ci = [r for r in plan_log if r.get("event") == "checkin"]
    sent_ci = [r for r in ci if r.get("outcome") == "sent"]
    results.append(("4 empty-day check-in arrives", "PASS" if sent_ci else "NOT SEEN YET",
                     ", ".join(f"{r['at'][5:16]} {r.get('outcome')} "
                               f"{delivered(_t(r['at']))}" for r in ci) or "none yet"))

    # 5. quiet hours
    def quiet(t: datetime) -> bool:
        return time_in_quiet_hours(cfg, t.time())
    loud = [r for r in plan_log if r.get("event") in ("nudge", "checkin", "reminder")
            and r.get("outcome") == "sent" and quiet(_t(r["at"]))]
    loud_push = [i for i, s in sent.items() if quiet(s)]
    nights = (local_now - since).total_seconds() >= 24 * 3600
    results.append(("5 quiet hours hold", "FAIL" if (loud or loud_push)
                    else ("PASS" if nights else "NOT SEEN YET"),
                    f"{len(loud)} sends and {len(loud_push)} pings in quiet hours"
                    + ("" if nights else " (no full night observed yet)")))

    for name, verdict, why in results:
        print(f"{verdict:<13} {name}: {why}")

    fails = [r for r in push if r.get("event") == "fcm_fetch_failed"]
    fallback = [i for i in sent if i not in fetched]
    print(f"\ndelivery since {since:%m-%d %H:%M}: {len(sent)} pings, {len(sent) - len(fallback)} "
          f"fetched, {len(fallback)} fell back"
          + (f" at {', '.join(sent[i].strftime('%m-%d %H:%M') for i in fallback)}" if fallback else ""))
    for r in fails:
        print(f"  phone reported: {r.get('reason')} (ping {r.get('id')}, phone time {r.get('phone_at')})")
    return 1 if any(v == "FAIL" for _, v, _ in results) else 0


if __name__ == "__main__":
    sys.exit(main())
