"""
tools/accountability.py — Accountability Index (DEV_BACKLOG.md [DB-0827-09]).

Design decided by Mike 2026-08-28; this is the code half only. Do not re-decide
anything here — the shape below is what was agreed, not a fresh proposal.

WHAT THIS JOINS
The Diarist logs user-voiced intentions via `write_log` with a fixed shape
(`config/agents/diarist.md` § "A user-stated intention IS loggable"):
    write_log(content={"intention": "<what, in their words>",
                        "stated_for": "<when, if they said — YYYY-MM-DD>"})
`stated_for` is optional and free-text-ish in practice (the agent instruction
says "when, if they said", not "a parsed date"); this module only trusts it
when it parses as YYYY-MM-DD, and falls back to the undated default otherwise
rather than guessing.

STORED SHAPE, AS FOUND (read from tools/logger.py and data/personas/*/logs
before writing this): `write_log` merges `content` into the day's flat
`data/personas/{persona}/logs/YYYY-MM-DD.json` file via `_deep_merge`, which
replaces non-dict, non-list top-level keys wholesale. `intention` is a plain
top-level string, not a list — so a SECOND intention logged on the same
calendar day overwrites the first with no trace. That is a real gap in the
collection half (not something this build was asked to fix), and is called
out in the build report rather than patched silently here.

EVIDENCE SPLIT BY CHECKABILITY (Mike's design, point 1)
Two structured outcomes join deterministically, in code, no model call:
  - a calendar event occurred (tools/caldav.py, matched by title against the
    intention text)
  - an obligation was closed (tools/obligations.py, matched by `what`)
Anything that cannot be resolved this way — no structured match found in the
window — is free-text territory and is meant to go through a nightly
Flash-Lite judgment gate (bare model, `intake_extractor` pattern). That gate
is a Red-tier agent file and is NOT built here (see the handoff proposal in
the build report). Until it exists, an unresolved case lands as
`indeterminate` with `reason: "awaiting judgment gate"` — never forced to
`unfulfilled`, because "no structured match" is not evidence of absence.

WINDOW (Mike's design, point 2)
  - `stated_for` present and parseable: window is [stated_for, stated_for + 2
    days grace].
  - Undated: window is [logged_date, logged_date + 7 days].
The index reports a fulfilment rate over a trailing 30 days (point 2) and
Mike said it surfaces both ways (point 3): a content-free count into the A9
rollup (see tools/analytics.py) and qualitative surfacing in the weekly
retrospective (also Red — agent-file text, in the handoff proposal, not here).

MATCHING IS A COARSE, DOCUMENTED HEURISTIC, NOT SEMANTIC UNDERSTANDING.
`_match_score` is token-overlap plus substring containment on normalized
text. It is deterministic and cheap, which is exactly why it belongs in code
rather than behind a model call — but it will also miss real matches phrased
differently ("go for a run" vs "5k around the block"). Those misses are the
free-text cases the judgment gate exists to pick up; this module does not
try to close that gap with a bigger heuristic.

COST NOTE (CLAUDE.md § Costs — Ancillary / Unseen)
The calendar half of the join is a network CalDAV query
(`tools.caldav._query_events`). `build_index` (used by the CLI report and any
future audit) performs it. `daily_accountability_counts` (used by the A9
nightly rollup, `tools/analytics.py`) deliberately does NOT — it only runs
the obligation join (a local YAML read, no network) so the unattended nightly
rollup does not pick up a new network dependency and cannot fail the whole
analytics row if CalDAV is unreachable. This means the daily A9 counts
undercount calendar-fulfilled intentions relative to the full CLI report;
documented here so it isn't rediscovered as a bug later.
"""
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

_GRACE_DAYS = 2
_DEFAULT_WINDOW_DAYS = 7
_TRAILING_DAYS = 30

# How far past a window's end to keep looking for a late structured match, so a
# match that occurred can be distinguished from one that never did. Generous but
# bounded — a match found a year late is not useful evidence either way.
_LATE_LOOKAHEAD_DAYS = 30

_MATCH_THRESHOLD = 0.5

_STOPWORDS = {
    "a", "an", "the", "to", "for", "and", "or", "of", "in", "on", "at", "with",
    "i", "we", "will", "going", "gonna", "start", "starting", "again", "my",
    "this", "that", "up", "out", "back",
}


# ---------------------------------------------------------------------------
# Paths — root-relative, like tools/analytics.py's own _persona_dir, so a
# caller (analytics.py, tests) can override `root` without going through
# core.persona at all. Real runtime usage leaves `root` as ROOT, which is the
# same directory core.persona.persona_data_dir resolves against anyway.
# ---------------------------------------------------------------------------

def _persona_dir(persona: str, root: Path = ROOT) -> Path:
    return root / "data" / "personas" / persona


def _logs_dir(persona: str, root: Path = ROOT) -> Path:
    return _persona_dir(persona, root) / "logs"


def _obligations_path(persona: str, root: Path = ROOT) -> Path:
    return _persona_dir(persona, root) / "obligations.yaml"


# ---------------------------------------------------------------------------
# Reading intentions
# ---------------------------------------------------------------------------

def read_intentions(persona: str, since_date: str | None = None,
                     *, root: Path = ROOT) -> list[dict]:
    """
    Scan data/personas/{persona}/logs/*.json for logged intentions.

    Only files named YYYY-MM-DD.json are day-log files; other files in the
    same directory (e.g. quality_events.json, a JSON Lines file) are skipped
    because their filename does not parse as a date.
    """
    logs_dir = _logs_dir(persona, root)
    out: list[dict] = []
    if not logs_dir.exists():
        return out

    for path in sorted(logs_dir.glob("*.json")):
        try:
            date.fromisoformat(path.stem)
        except ValueError:
            continue  # not a day-log file (e.g. quality_events.json)
        try:
            data = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        intention = data.get("intention")
        if not intention or not isinstance(intention, str):
            continue

        logged_date = data.get("date") or path.stem
        if since_date and logged_date < since_date:
            continue

        stated_for = data.get("stated_for") or ""
        out.append({
            "intention": intention,
            "stated_for": stated_for if isinstance(stated_for, str) else "",
            "logged_date": logged_date,
        })

    return out


# ---------------------------------------------------------------------------
# Window
# ---------------------------------------------------------------------------

def intention_window(intention: dict) -> tuple[date, date]:
    """(start, end) inclusive, per Mike's design: stated_for + 2d grace, else logged_date + 7d."""
    logged = date.fromisoformat(intention["logged_date"])
    stated_for = (intention.get("stated_for") or "").strip()
    if stated_for:
        try:
            base = date.fromisoformat(stated_for)
            return base, base + timedelta(days=_GRACE_DAYS)
        except ValueError:
            pass  # unparseable stated_for — fall through to the undated default
    return logged, logged + timedelta(days=_DEFAULT_WINDOW_DAYS)


# ---------------------------------------------------------------------------
# Matching — coarse, deterministic, documented (see module docstring)
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()


def _tokens(text: str) -> set[str]:
    return {w for w in _normalize(text).split() if w not in _STOPWORDS and len(w) > 1}


def _match_score(a: str, b: str) -> float:
    na, nb = _normalize(a), _normalize(b)
    if na and nb and (na in nb or nb in na):
        return 1.0
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / min(len(ta), len(tb))


def _event_date(event: dict) -> date | None:
    start = str(event.get("start") or "")[:10]
    try:
        return date.fromisoformat(start)
    except ValueError:
        return None


def _closed_date(obligation: dict) -> date | None:
    closed_at = str(obligation.get("closed_at") or "")[:10]
    try:
        return date.fromisoformat(closed_at)
    except ValueError:
        return None


@dataclass
class _Match:
    source: str          # "calendar" | "obligation"
    matched_on: str       # the title/what that matched, for audit
    occurred: date
    in_window: bool


def _find_calendar_match(text: str, events: list[dict], start: date, end: date) -> _Match | None:
    best: _Match | None = None
    for ev in events:
        title = ev.get("title", "")
        if _match_score(text, title) < _MATCH_THRESHOLD:
            continue
        occurred = _event_date(ev)
        if occurred is None:
            continue
        m = _Match("calendar", title, occurred, start <= occurred <= end)
        if best is None or occurred < best.occurred:
            best = m
    return best


def _find_obligation_match(text: str, obligations: list[dict], start: date, end: date) -> _Match | None:
    best: _Match | None = None
    for ob in obligations:
        if ob.get("status") != "closed":
            continue
        what = ob.get("what", "")
        if _match_score(text, what) < _MATCH_THRESHOLD:
            continue
        occurred = _closed_date(ob)
        if occurred is None:
            continue
        m = _Match("obligation", what, occurred, start <= occurred <= end)
        if best is None or occurred < best.occurred:
            best = m
    return best


# ---------------------------------------------------------------------------
# Resolving one intention
# ---------------------------------------------------------------------------

def resolve_intention(intention: dict, calendar_events: list[dict], obligations: list[dict],
                       as_of: date) -> dict:
    """
    One verdict: fulfilled | unfulfilled | indeterminate. Never forced — see module docstring.
    """
    start, end = intention_window(intention)
    text = intention["intention"]

    cal = _find_calendar_match(text, calendar_events, start, end)
    ob = _find_obligation_match(text, obligations, start, end)
    matches = [m for m in (cal, ob) if m is not None]

    in_window = [m for m in matches if m.in_window]
    if in_window:
        m = min(in_window, key=lambda m: m.occurred)
        verdict, reason = "fulfilled", f"matched {m.source} ({m.matched_on!r}) within window"
    else:
        out_of_window = [m for m in matches if not m.in_window]
        if out_of_window:
            m = min(out_of_window, key=lambda m: m.occurred)
            verdict = "unfulfilled"
            reason = f"matched {m.source} ({m.matched_on!r}) but outside the grace window"
        elif as_of <= end:
            verdict, reason = "indeterminate", "window still open"
        else:
            verdict = "indeterminate"
            reason = ("awaiting judgment gate — no structured (calendar/obligation) match "
                      "found; free-text confirmation not yet run")

    return {
        "intention": text,
        "stated_for": intention.get("stated_for") or "",
        "logged_date": intention["logged_date"],
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "verdict": verdict,
        "reason": reason,
    }


# ---------------------------------------------------------------------------
# Fetchers for the real (non-test) path
# ---------------------------------------------------------------------------

def _fetch_calendar_events(persona: str, intentions: list[dict], as_of: date) -> list[dict]:
    if not intentions:
        return []
    from tools.caldav import _query_events
    windows = [intention_window(i) for i in intentions]
    start = min(w[0] for w in windows)
    end = max(max(w[1], as_of) for w in windows) + timedelta(days=_LATE_LOOKAHEAD_DAYS)
    try:
        raw = _query_events(start.isoformat(), end.isoformat(), persona)
    except Exception:
        return []
    if "error" in raw:
        return []
    return raw.get("events", [])


def _fetch_obligations(persona: str, *, root: Path = ROOT) -> list[dict]:
    from tools.obligations import _load as _load_obligations
    try:
        return _load_obligations(persona)
    except Exception:
        return []


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------

def build_index(persona: str, as_of: date | None = None, trailing_days: int = _TRAILING_DAYS,
                 *, root: Path = ROOT,
                 calendar_events: list[dict] | None = None,
                 obligations: list[dict] | None = None) -> dict:
    """
    The fulfilment index over a trailing window.

    `calendar_events` / `obligations` are injectable — tests pass synthetic
    lists directly; real callers leave them None and this fetches from the
    live calendar (network) and local obligations store.
    """
    as_of = as_of or date.today()
    since = (as_of - timedelta(days=trailing_days)).isoformat()
    intentions = read_intentions(persona, since_date=since, root=root)

    if calendar_events is None:
        calendar_events = _fetch_calendar_events(persona, intentions, as_of)
    if obligations is None:
        obligations = _fetch_obligations(persona, root=root)

    items = [resolve_intention(i, calendar_events, obligations, as_of) for i in intentions]

    fulfilled = sum(1 for it in items if it["verdict"] == "fulfilled")
    unfulfilled = sum(1 for it in items if it["verdict"] == "unfulfilled")
    indeterminate = sum(1 for it in items if it["verdict"] == "indeterminate")
    denom = fulfilled + unfulfilled
    rate = round(fulfilled / denom, 3) if denom else None

    return {
        "persona": persona,
        "as_of": as_of.isoformat(),
        "trailing_days": trailing_days,
        "counts": {
            "fulfilled": fulfilled,
            "unfulfilled": unfulfilled,
            "indeterminate": indeterminate,
            "total": len(items),
        },
        # Rate excludes indeterminate from the denominator on purpose: an
        # indeterminate case is not evidence either way, and folding it into
        # the rate (as a failure or a pass) would be exactly the forced
        # verdict the design rules out.
        "fulfilment_rate": rate,
        "items": items,
    }


# ---------------------------------------------------------------------------
# A9 rollup hook — content-free counts only (§ A9, tools/analytics.py)
# ---------------------------------------------------------------------------

def daily_accountability_counts(day: str, persona: str, *, root: Path = ROOT) -> dict:
    """
    Content-free counts for ONE day, for tools/analytics.py's rollup row.

    Counts only — no intention text, no names, no dates beyond `day` itself.
    Two buckets, both re-derivable from stored data at any time:
      - intentions_stated: intentions logged on this calendar day
      - intentions_resolved_*: intentions whose window closes on this day,
        bucketed by verdict (computed as of this day)

    Deliberately calendar-free (see module docstring § Cost note) — only the
    local obligations store is joined here, no network CalDAV query, so the
    unattended nightly rollup never depends on the calendar being reachable.
    """
    as_of = date.fromisoformat(day)
    lookback = _DEFAULT_WINDOW_DAYS + _GRACE_DAYS + 3
    since = (as_of - timedelta(days=lookback)).isoformat()
    intentions = read_intentions(persona, since_date=since, root=root)

    stated_today = sum(1 for i in intentions if i["logged_date"] == day)

    resolved = {"fulfilled": 0, "unfulfilled": 0, "indeterminate": 0}
    if intentions:
        obligations = _fetch_obligations(persona, root=root)
        for i in intentions:
            start, end = intention_window(i)
            if end != as_of:
                continue
            item = resolve_intention(i, [], obligations, as_of)
            resolved[item["verdict"]] += 1

    return {
        "intentions_stated": stated_today,
        "intentions_resolved_fulfilled": resolved["fulfilled"],
        "intentions_resolved_unfulfilled": resolved["unfulfilled"],
        "intentions_resolved_indeterminate": resolved["indeterminate"],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def report(persona: str, days: int = _TRAILING_DAYS) -> str:
    idx = build_index(persona, trailing_days=days)
    c = idx["counts"]
    rate = idx["fulfilment_rate"]
    lines = [
        f"Accountability Index — {persona}, trailing {days}d (as of {idx['as_of']})",
        f"  fulfilled: {c['fulfilled']}  unfulfilled: {c['unfulfilled']}  "
        f"indeterminate: {c['indeterminate']}  (total {c['total']})",
        f"  fulfilment rate: {rate if rate is not None else 'n/a'} "
        f"(excludes indeterminate from the denominator)",
        "",
    ]
    for it in idx["items"]:
        lines.append(f"  [{it['verdict']:13}] {it['logged_date']}  "
                     f"{it['intention'][:70]!r}  — {it['reason']}")
    return "\n".join(lines)


if __name__ == "__main__":  # manual: python3 -m tools.accountability --report
    ap = argparse.ArgumentParser(description="Accountability Index (DB-0827-09)")
    ap.add_argument("--persona", default="mike")
    ap.add_argument("--days", type=int, default=_TRAILING_DAYS)
    ap.add_argument("--report", action="store_true", help="print the human-readable report")
    ap.add_argument("--json", action="store_true", help="print the raw index as JSON")
    args = ap.parse_args()
    if args.json:
        print(json.dumps(build_index(args.persona, trailing_days=args.days), indent=2))
    else:
        print(report(args.persona, args.days))
