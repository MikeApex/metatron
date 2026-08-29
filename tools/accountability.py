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

STORED SHAPE — TWO OF THEM, BOTH READ.
  - **Legacy (scalar).** `write_log` merged `intention` into the day file as a
    plain top-level string, and `_deep_merge` replaces a scalar wholesale — so a
    second intention logged the same day overwrote the first with no trace.
    Files written that way still exist and are never rewritten.
  - **Current (list).** Mike's ruling (a) of 2026-08-28: the day file carries a
    top-level `intentions` list, one entry per statement, appended by
    `tools/logger.py`'s `_split_intention`. **Restatements are kept, not
    deduped** — how often an intention is voiced is the signal.
A day file mid-transition can hold both; `read_intentions` reads both.

RESTATEMENTS GROUP, AND THE COUNT IS THE POINT. Statements whose normalized
text matches collapse into ONE intention carrying `times_stated`. The window is
anchored to the FIRST statement — restating a thing does not buy it more time,
it raises how much it presses. `times_stated` rides in every resolution row and
in the `--report` table, so frequency reads as urgency where a person sees it.

EVIDENCE SPLIT BY CHECKABILITY (Mike's design, point 1)
Two structured outcomes join deterministically, in code, no model call:
  - a calendar event occurred (tools/caldav.py, matched by title against the
    intention text)
  - an obligation was closed (tools/obligations.py, matched by `what`)
Anything that cannot be resolved this way — no structured match found in the
window — is free-text territory and goes through the nightly judgment gate
(`run_judgment_gate`, 05:45, `config/agents/accountability_judge.md`, bare
model, `intake_extractor` pattern). Until the gate has seen a case it lands as
`indeterminate` with `reason: "awaiting judgment gate"` — never forced to
`unfulfilled`, because "no structured match" is not evidence of absence.

THE GATE JUDGES EACH INTENTION AT MOST ONCE, AND NEVER RE-LITIGATES CODE.
Verdicts are appended to `data/personas/{p}/accountability/verdicts.jsonl`
(0600). A stored gate verdict — **including `indeterminate`** — is final: the
case is not re-dispatched on a later night, because a second opinion from the
same model on the same evidence is not new information, it is a second bill. A
verdict code resolved (calendar/obligation match, or a window still open) never
reaches the gate at all: only rows still reading "awaiting judgment gate" are
eligible, which is the same rule stated in the judge's own instructions.

PRIVACY. The gate's evidence is journal text and day-log free text — Sensitive
tier. The basis on which that may travel the Vertex path is recorded once, in
`config/modules/routing_cloud.yaml` under `accountability_judge`, and is not
restated here: one home per rule. Everything this module writes stays local at
0600, and nothing it produces reaches the user directly — `context_block`
hands numbers and the user's own words to the Synthesizer, which decides what
is said.

COST NOTE (CLAUDE.md § Costs) — three standing costs, named where they are set:
  - **Run.** The gate is a handful of *bare* Flash-Lite calls, one per leftover
    intention, and only on nights that have leftovers at all. A day with no
    unresolved intention makes zero model calls; `_MAX_EVIDENCE_CHARS` bounds
    the input of the ones it does make. Bare dispatch means no constitution, no
    goals, no recent context — the prompt is the agent file plus one window of
    text.
  - **Ancillary (storage).** `verdicts.jsonl` is append-only, one short JSON row
    per judged intention, and nothing deletes it — deliberately: it is the audit
    trail `[DB-0828-01]` samples, and at a few rows a week it is measured in
    kilobytes per year. If it ever needs an expiry, that is a decision, not a
    default.
  - **Unseen.** The weekly state file (`weekly_state.json`) is the only thing
    here that persists between calls without an owner. It is *replaced* every
    Sunday and cleared by `context_block` on delivery, so it holds at most one
    week's summary and cannot accumulate; a crash or redeploy leaves at worst one
    stale summary that the next Sunday overwrites. No meter reports either file —
    they are small enough that none needs to.

WINDOW (Mike's design, point 2)
  - `stated_for` present and parseable: window is [stated_for, stated_for + 2
    days grace].
  - Undated: window is [logged_date, logged_date + 7 days].
The index reports a fulfilment rate over a trailing 30 days (point 2) and
Mike said it surfaces both ways (point 3): a content-free count into the A9
rollup (see tools/analytics.py) and qualitative surfacing in the weekly
retrospective. The second of those is `context_block` — it parks the trailing-7d
numbers and the names of the open ones for the head layer. **How that is voiced
is not this module's business**: `config/modules/synthesizer_scheduled_sessions.md`
§ Intention follow-through governs the wording, and is not restated here.

MATCHING IS A COARSE, DOCUMENTED HEURISTIC, NOT SEMANTIC UNDERSTANDING.
`_match_score` is token-overlap plus substring containment on normalized
text. It is deterministic and cheap, which is exactly why it belongs in code
rather than behind a model call — but it will also miss real matches phrased
differently ("go for a run" vs "5k around the block"). Those misses are the
free-text cases the judgment gate exists to pick up; this module does not
try to close that gap with a bigger heuristic.

COST NOTE, THE NETWORK HALF (CLAUDE.md § Costs — Ancillary / Unseen)
The calendar half of the join is a network CalDAV query
(`tools.caldav._query_events`). `build_index` (used by the CLI report and any
future audit) performs it. `daily_accountability_counts` (used by the A9
nightly rollup, `tools/analytics.py`) deliberately does NOT — it only runs
the obligation join (a local YAML read, no network) so the unattended nightly
rollup does not pick up a new network dependency and cannot fail the whole
analytics row if CalDAV is unreachable. This means the daily A9 counts
undercount calendar-fulfilled intentions relative to the full CLI report;
documented here so it isn't rediscovered as a bug later.

`run_judgment_gate` sits on the OTHER side of that line and does query the
calendar, which is not an inconsistency: it already cannot work without the
network (it calls a model), and skipping the calendar there would send
calendar-fulfilled intentions to the gate as leftovers — buying model calls to
re-answer a question code had already answered. An unreachable CalDAV degrades
it to more indeterminates, never to a crash (`_fetch_calendar_events` returns
[] on any failure).
"""
from __future__ import annotations

import argparse
import json
import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent

_GRACE_DAYS = 2
_DEFAULT_WINDOW_DAYS = 7
_TRAILING_DAYS = 30

# How far past a window's end to keep looking for a late structured match, so a
# match that occurred can be distinguished from one that never did. Generous but
# bounded — a match found a year late is not useful evidence either way.
_LATE_LOOKAHEAD_DAYS = 30

_MATCH_THRESHOLD = 0.5

# How far back the nightly gate reads. Its scope is "yesterday's leftovers", but that is
# a cadence, not a filter: the eligibility test is window-closed + still awaiting the
# gate + never judged, and a bounded lookback means one missed night (VM asleep, model
# unreachable) is picked up the next one instead of leaving a permanent hole. Judged-once
# is enforced by the verdict store, not by the lookback, so widening this cannot cause a
# re-judgement — only the discovery of something genuinely never seen.
_GATE_LOOKBACK_DAYS = 30

# Ceiling on the evidence handed to one judge call. A window is at most 9 days of journal
# text; a prolific week would otherwise put the whole of it in a Flash-Lite prompt on a
# schedule. Truncation costs a verdict's precision at the margin, which the judge is
# already instructed to answer as `indeterminate`.
_MAX_EVIDENCE_CHARS = 4000

# How long a parked weekly summary keeps being offered after its first read — the same
# 30 minutes and the same reason as tools/intake.py's digest: coordinator and synthesizer
# load context seconds apart in one session, and popping on first read feeds the routing
# layer and starves the agent that actually writes to the user.
_WEEKLY_DELIVERY_WINDOW_MIN = 30

_WEEKLY_TRAILING_DAYS = 7

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


def _journal_dir(persona: str, root: Path = ROOT) -> Path:
    # tools/diarist.py writes here (persona_data_dir()/journal); resolved root-relative
    # for the same reason as the logs dir above — so a test can point at a tempdir.
    return _persona_dir(persona, root) / "journal"


def _accountability_dir(persona: str, root: Path = ROOT) -> Path:
    return _persona_dir(persona, root) / "accountability"


def _verdicts_path(persona: str, root: Path = ROOT) -> Path:
    return _accountability_dir(persona, root) / "verdicts.jsonl"


def _weekly_state_path(persona: str, root: Path = ROOT) -> Path:
    return _accountability_dir(persona, root) / "weekly_state.json"


# ---------------------------------------------------------------------------
# Reading intentions
# ---------------------------------------------------------------------------

def _day_statements(data: dict, logged_date: str) -> list[dict]:
    """
    Every intention statement in one day file, in both stored shapes.

    Legacy scalar first (it was written first), then the `intentions` list. A file can
    hold both — one written before the list shape landed and appended to afterwards —
    and dropping either would lose a statement that was really made.
    """
    rows: list[dict] = []

    legacy = data.get("intention")
    if isinstance(legacy, str) and legacy.strip():
        stated_for = data.get("stated_for")
        rows.append({
            "intention": legacy.strip(),
            "stated_for": stated_for.strip() if isinstance(stated_for, str) else "",
            "logged_date": logged_date,
        })

    feed = data.get("intentions")
    if isinstance(feed, list):
        for entry in feed:
            if isinstance(entry, str):
                entry = {"intention": entry}
            if not isinstance(entry, dict):
                continue
            text = entry.get("intention")
            if not isinstance(text, str) or not text.strip():
                continue
            stated_for = entry.get("stated_for")
            rows.append({
                "intention": text.strip(),
                "stated_for": stated_for.strip() if isinstance(stated_for, str) else "",
                "logged_date": logged_date,
            })

    return rows


def read_statements(persona: str, since_date: str | None = None,
                     *, root: Path = ROOT) -> list[dict]:
    """
    Every intention STATEMENT, ungrouped, oldest first — restatements included.

    Only files named YYYY-MM-DD.json are day-log files; other files in the same
    directory (e.g. quality_events.json, a JSON Lines file) are skipped because their
    filename does not parse as a date.
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

        logged_date = data.get("date") or path.stem
        if since_date and logged_date < since_date:
            continue
        out.extend(_day_statements(data, logged_date))

    return out


def read_intentions(persona: str, since_date: str | None = None,
                     *, root: Path = ROOT) -> list[dict]:
    """
    Logged intentions, restatements GROUPED — one row per distinct intention.

    Grouping key is the normalized text, so "start running again" said on three
    separate days is one intention with `times_stated: 3`, not three that each expire
    separately. Two consequences, both deliberate:

    - **The window is anchored to the FIRST statement.** Restating does not extend the
      deadline; it raises how much the thing presses, which is what `times_stated` is
      for. Anchoring to the last statement would make a frequently-voiced intention
      permanently un-judgeable.
    - **Grouping happens AFTER the `since_date` filter**, so a trailing-30d index groups
      only the statements inside its own window and an older first statement does not
      drag an intention into a report that should not carry it.

    `stated_for` is taken from the first statement that carries one — a user who names a
    date once and then restates the intention bare has not withdrawn the date.
    """
    grouped: dict[str, dict] = {}
    for row in read_statements(persona, since_date, root=root):
        key = _normalize(row["intention"])
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = {
                "intention": row["intention"],
                "stated_for": row["stated_for"],
                "logged_date": row["logged_date"],
                "times_stated": 1,
                "statement_dates": [row["logged_date"]],
            }
            continue
        existing["times_stated"] += 1
        existing["statement_dates"].append(row["logged_date"])
        if not existing["stated_for"] and row["stated_for"]:
            existing["stated_for"] = row["stated_for"]

    return sorted(grouped.values(), key=lambda i: (i["logged_date"], i["intention"]))


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
# The gate's verdict store — append-only, local, 0600
# ---------------------------------------------------------------------------

_AWAITING_GATE = "awaiting judgment gate"


def _intention_key(logged_date: str, text: str) -> str:
    """Identity of one intention across runs: the day it was first stated + its text.

    Normalized text, not raw, so the key survives the punctuation and casing drift that
    `_normalize` already absorbs everywhere else — and so it matches the same grouping
    `read_intentions` uses. Two genuinely different intentions first stated the same day
    keep different keys; the same one restated keeps one key, which is the point.
    """
    return f"{logged_date}|{_normalize(text)}"


def read_gate_verdicts(persona: str, *, root: Path = ROOT) -> dict[str, dict]:
    """Stored gate verdicts by intention key. Unreadable rows are skipped, never fatal.

    Last row wins if a key somehow appears twice — the file is append-only and the gate
    judges once, so that should not happen; if it does, the newer judgement is the one
    that was written most recently on purpose.
    """
    path = _verdicts_path(persona, root)
    if not path.exists():
        return {}
    out: dict[str, dict] = {}
    try:
        lines = path.read_text().splitlines()
    except OSError:
        return {}
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if not isinstance(row, dict):
            continue
        key = row.get("key")
        if isinstance(key, str) and key:
            out[key] = row
    return out


def _append_gate_verdict(persona: str, row: dict, *, root: Path = ROOT) -> None:
    path = _verdicts_path(persona, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    try:
        path.chmod(0o600)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Resolving one intention
# ---------------------------------------------------------------------------

def resolve_intention(intention: dict, calendar_events: list[dict], obligations: list[dict],
                       as_of: date, gate_verdicts: dict[str, dict] | None = None) -> dict:
    """
    One verdict: fulfilled | unfulfilled | indeterminate. Never forced — see module docstring.

    `gate_verdicts` (keyed by `_intention_key`) is merged in LAST and only over the
    "awaiting judgment gate" state. It cannot overturn a structured match or reopen a
    window that is still running: code beats the model on the questions code can answer,
    which is the same rule the judge's own instructions state from the other side.
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
            reason = (f"{_AWAITING_GATE} — no structured (calendar/obligation) match "
                      "found; free-text confirmation not yet run")

    judged_by = ""
    if verdict == "indeterminate" and reason.startswith(_AWAITING_GATE) and gate_verdicts:
        stored = gate_verdicts.get(_intention_key(intention["logged_date"], text))
        if stored and stored.get("verdict") in ("fulfilled", "unfulfilled", "indeterminate"):
            verdict = stored["verdict"]
            reason = str(stored.get("reason") or "").strip() or "judged, no reason recorded"
            judged_by = "gate"

    return {
        "intention": text,
        "stated_for": intention.get("stated_for") or "",
        "logged_date": intention["logged_date"],
        "times_stated": int(intention.get("times_stated") or 1),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "verdict": verdict,
        "reason": reason,
        "judged_by": judged_by,
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
                 obligations: list[dict] | None = None,
                 gate_verdicts: dict[str, dict] | None = None) -> dict:
    """
    The fulfilment index over a trailing window.

    `calendar_events` / `obligations` are injectable — tests pass synthetic
    lists directly; real callers leave them None and this fetches from the
    live calendar (network) and local obligations store.

    Stored judgment-gate verdicts are read from disk unless supplied, and replace the
    "awaiting judgment gate" indeterminates — so they land in both the table and the
    fulfilment rate, which is where a `fulfilled`/`unfulfilled` from the gate is
    supposed to count. An `indeterminate` from the gate stays out of the denominator
    exactly as an unjudged one does: the gate saying "the record does not say" is not
    evidence either way any more than silence was.
    """
    as_of = as_of or date.today()
    since = (as_of - timedelta(days=trailing_days)).isoformat()
    intentions = read_intentions(persona, since_date=since, root=root)

    if calendar_events is None:
        calendar_events = _fetch_calendar_events(persona, intentions, as_of)
    if obligations is None:
        obligations = _fetch_obligations(persona, root=root)
    if gate_verdicts is None:
        gate_verdicts = read_gate_verdicts(persona, root=root)

    items = [resolve_intention(i, calendar_events, obligations, as_of, gate_verdicts)
             for i in intentions]

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
      - intentions_stated: intention STATEMENTS made on this calendar day —
        restatements counted, because the series is meant to show how often a
        person voices intentions, and a restatement is a voicing. This is the
        one place statements are counted rather than distinct intentions.
      - intentions_resolved_*: intentions whose window closes on this day,
        bucketed by verdict (computed as of this day)

    Deliberately calendar-free (see module docstring § Cost note) — only the
    local obligations store is joined here, no network CalDAV query, so the
    unattended nightly rollup never depends on the calendar being reachable.

    Gate verdicts are deliberately NOT merged here. The 05:40 rollup runs before the
    05:45 gate, so on the day itself there is nothing to merge; folding them in would
    only mean a row re-derived months later disagreed with the row that was stored,
    for a series whose value is that it is comparable across days.
    """
    as_of = date.fromisoformat(day)
    lookback = _DEFAULT_WINDOW_DAYS + _GRACE_DAYS + 3
    since = (as_of - timedelta(days=lookback)).isoformat()
    intentions = read_intentions(persona, since_date=since, root=root)

    stated_today = sum(1 for s in read_statements(persona, since_date=day, root=root)
                       if s["logged_date"] == day)

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
# The judgment gate — one bare Flash-Lite call per leftover, nightly
# ---------------------------------------------------------------------------

# Day-log keys that hold text about what actually happened. Deliberately a fixed list,
# not "every string in the file": the gate must not be shown `intention`/`intentions`
# (a restatement is not a fulfilment, and the judge is told so explicitly, but the
# cheapest way to honour that is not to hand it the restatement at all), and it has no
# use for `date` or the `_written_at` bookkeeping map.
_EVENTISH_KEYS = ("notes", "wins", "blockers", "focus", "tasks_completed", "events")


def _flatten_text(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, list):
        return "; ".join(t for t in (_flatten_text(v) for v in value) if t)
    if isinstance(value, dict):
        return "; ".join(f"{k}: {t}" for k, v in value.items()
                         if (t := _flatten_text(v)))
    return ""


def window_evidence(persona: str, start: date, end: date, *, root: Path = ROOT) -> str:
    """
    The window's recorded text: journal entries first, then day-log event-ish fields.

    Sensitive tier — journal text is the most personal thing this system stores. It
    leaves the machine only inside the judge's bare dispatch, on the basis recorded in
    `config/modules/routing_cloud.yaml` under `accountability_judge`. Truncated to
    `_MAX_EVIDENCE_CHARS` so one prolific week cannot make one nightly call large.
    """
    parts: list[str] = []
    day = start
    while day <= end:
        stamp = day.isoformat()

        jpath = _journal_dir(persona, root) / f"{stamp}.json"
        if jpath.exists():
            try:
                jdata = json.loads(jpath.read_text())
            except (OSError, ValueError):
                jdata = {}
            for entry in (jdata.get("entries") or []):
                if isinstance(entry, dict):
                    text = _flatten_text(entry.get("text"))
                    if text:
                        parts.append(f"[journal {stamp}] {text}")

        lpath = _logs_dir(persona, root) / f"{stamp}.json"
        if lpath.exists():
            try:
                ldata = json.loads(lpath.read_text())
            except (OSError, ValueError):
                ldata = {}
            if isinstance(ldata, dict):
                for key in _EVENTISH_KEYS:
                    text = _flatten_text(ldata.get(key))
                    if text:
                        parts.append(f"[log {stamp} {key}] {text}")

        day += timedelta(days=1)

    joined = "\n".join(parts)
    if len(joined) > _MAX_EVIDENCE_CHARS:
        joined = joined[:_MAX_EVIDENCE_CHARS] + "\n[…evidence truncated]"
    return joined


def _build_judge_input(item: dict, evidence: str) -> str:
    """One intention, its window, and the window's text. The framing is ours; the
    evidence is the user's own record and travels wrapped either way."""
    from tools.untrusted import UNTRUSTED_CONTENT_INSTRUCTION, wrap_untrusted

    header = json.dumps({
        "intention": item["intention"],
        "stated_on": item["logged_date"],
        "window": f"{item['window_start']} to {item['window_end']}",
        "times_stated": item.get("times_stated", 1),
    }, indent=2, ensure_ascii=False)
    body = evidence or "(no journal or log text was recorded in this window)"
    return (
        f"{UNTRUSTED_CONTENT_INSTRUCTION}\n\n"
        f"Judge whether this intention happened. Return only the JSON object described "
        f"in your instructions.\n\n{header}\n\n"
        f"{wrap_untrusted(body, source='journal and log text from the window')}"
    )


_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)
_VALID_VERDICTS = frozenset({"fulfilled", "unfulfilled", "indeterminate"})


def parse_verdict(raw: str) -> dict:
    """The judge's answer, or the indeterminate floor. Never raises.

    Same posture as tools/intake_extract.py's `_parse`, and the floor is the same kind
    of answer: junk, prose, an echoed injection payload, or a verdict outside the enum
    all collapse to `indeterminate`. That is the safe direction here — an unparseable
    response resolving to `unfulfilled` would let a malformed reply tell the user they
    failed at something.
    """
    fallback = {"verdict": "indeterminate", "reason": "judge returned no usable verdict"}
    if not isinstance(raw, str) or not raw.strip():
        return fallback
    match = _JSON_RE.search(raw)
    if not match:
        return fallback
    try:
        data = json.loads(match.group(0))
    except ValueError:
        return fallback
    if not isinstance(data, dict):
        return fallback
    verdict = str(data.get("verdict", "")).strip().lower()
    if verdict not in _VALID_VERDICTS:
        logger.warning(f"[accountability] judge returned unknown verdict {verdict!r}")
        return fallback
    reason = str(data.get("reason", "")).strip() or "no reason given"
    return {"verdict": verdict, "reason": reason[:500]}


def _judge(item: dict, evidence: str, persona: str | None) -> dict:
    """One intention, one bare Flash-Lite call — the tools/intake_extract.py dispatch.

    `bare=True` (agent file only: no constitution, goals, profile or recent context) and
    `complexity="quick"`. The empty tool grant is in the routing file, not here, so the
    model cannot emit a tool call at all. A failed call is `indeterminate`, never an
    exception: one bad intention must not cost the night the rest of them.
    """
    from core.orchestrator import run_session

    try:
        raw = run_session(
            "accountability_judge",
            user_input=_build_judge_input(item, evidence),
            persona=persona,
            complexity="quick",   # Flash-Lite tier — one closed enum, one sentence
            bare=True,            # agent file only; no personal context, by design
        )
    except Exception as exc:
        logger.warning(f"[accountability] judge call failed for "
                       f"{item['logged_date']}: {exc}")
        return {"verdict": "indeterminate", "reason": "judge call failed"}
    return parse_verdict(raw)


def _weekly_summary(items: list[dict], as_of: date) -> dict:
    """Trailing-7d follow-through: counts, plus the names of what is not done.

    Names only for `unfulfilled` and `indeterminate` — the ones a retrospective has
    something to say about. Fulfilled intentions are counted, not listed: reading back a
    list of things someone did is the shape of a report, and the weekly session is a
    conversation.
    """
    counts = {"fulfilled": 0, "unfulfilled": 0, "indeterminate": 0}
    unfulfilled: list[str] = []
    open_items: list[str] = []
    for it in items:
        counts[it["verdict"]] += 1
        if it["verdict"] == "unfulfilled":
            unfulfilled.append(it["intention"])
        elif it["verdict"] == "indeterminate":
            open_items.append(it["intention"])
    return {
        "as_of": as_of.isoformat(),
        "trailing_days": _WEEKLY_TRAILING_DAYS,
        "counts": {**counts, "total": len(items)},
        "unfulfilled": unfulfilled,
        "open": open_items,
    }


def run_judgment_gate(persona: str | None = None, as_of: date | None = None,
                       *, root: Path = ROOT, judge=None) -> str:
    """
    Scheduler entry point (05:45 daily, `core/scheduler.py` `_DEFAULT_JOBS`).

    Judges the post-join leftovers: intentions whose window has CLOSED, whose structured
    join still reads "awaiting judgment gate", and which the gate has never judged. One
    bare model call each; the verdict is appended to `verdicts.jsonl` and is final —
    including `indeterminate`, which is a real answer and not a retry token.

    On Sundays it then parks a trailing-7d follow-through summary for `context_block`.

    Always returns a plain string and never raises. This runs in the scheduler daemon,
    where an exception is a log line nobody reads and a notify dict would put an
    unreviewed model verdict in front of the user — neither is wanted here.

    `judge` is injectable for tests: a callable `(item, evidence) -> {"verdict", "reason"}`.
    """
    try:
        if persona is None:
            from core.persona import resolve_persona
            persona = resolve_persona()
        as_of = as_of or date.today()

        idx = build_index(persona, as_of=as_of, trailing_days=_GATE_LOOKBACK_DAYS,
                          root=root)
        stored = read_gate_verdicts(persona, root=root)

        leftovers = [
            it for it in idx["items"]
            if it["verdict"] == "indeterminate"
            and it["reason"].startswith(_AWAITING_GATE)
            and date.fromisoformat(it["window_end"]) < as_of
            and _intention_key(it["logged_date"], it["intention"]) not in stored
        ]

        judged = {"fulfilled": 0, "unfulfilled": 0, "indeterminate": 0}
        for item in leftovers:
            start = date.fromisoformat(item["window_start"])
            end = date.fromisoformat(item["window_end"])
            evidence = window_evidence(persona, start, end, root=root)
            call = judge or (lambda i, e: _judge(i, e, persona))
            result = call(item, evidence)
            if not isinstance(result, dict) or result.get("verdict") not in _VALID_VERDICTS:
                result = {"verdict": "indeterminate", "reason": "judge returned no usable verdict"}
            key = _intention_key(item["logged_date"], item["intention"])
            _append_gate_verdict(persona, {
                "key": key,
                "logged_date": item["logged_date"],
                "intention": item["intention"],
                "window_start": item["window_start"],
                "window_end": item["window_end"],
                "verdict": result["verdict"],
                "reason": result.get("reason", ""),
                "judged_at": datetime.now().isoformat(timespec="seconds"),
            }, root=root)
            stored[key] = {"verdict": result["verdict"], "reason": result.get("reason", "")}
            judged[result["verdict"]] += 1
            item["verdict"] = result["verdict"]
            item["reason"] = result.get("reason", "")
            item["judged_by"] = "gate"

        parts = [f"accountability gate: {len(leftovers)} judged "
                 f"({judged['fulfilled']}f/{judged['unfulfilled']}u/"
                 f"{judged['indeterminate']}i)"]

        # Sunday — weekday() 6. Computed from the index already in hand rather than
        # rebuilding it, so the weekly summary costs no second CalDAV query.
        if as_of.weekday() == 6:
            since = (as_of - timedelta(days=_WEEKLY_TRAILING_DAYS)).isoformat()
            week = [it for it in idx["items"] if it["logged_date"] >= since]
            summary = _weekly_summary(week, as_of)
            _park_weekly_summary(persona, summary, root=root)
            c = summary["counts"]
            parts.append(f"weekly summary parked ({c['total']} stated, "
                         f"{c['fulfilled']} done)")

        return "; ".join(parts)
    except Exception as exc:  # noqa: BLE001 — daemon context, see docstring
        logger.warning(f"[accountability] judgment gate failed: {exc}")
        return f"accountability gate: failed ({type(exc).__name__}: {exc})"


# ---------------------------------------------------------------------------
# Weekly follow-through — parked for the head layer, delivered once
# ---------------------------------------------------------------------------

def _read_weekly_state(persona: str, *, root: Path = ROOT) -> dict:
    path = _weekly_state_path(persona, root)
    if not path.exists():
        return {}
    try:
        state = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        logger.warning(f"[accountability] weekly_state.json unreadable, starting empty: {exc}")
        return {}
    return state if isinstance(state, dict) else {}


def _write_weekly_state(persona: str, state: dict, *, root: Path = ROOT) -> None:
    path = _weekly_state_path(persona, root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(state, indent=2, sort_keys=True, ensure_ascii=False))
    tmp.replace(path)
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _park_weekly_summary(persona: str, summary: dict, *, root: Path = ROOT) -> None:
    """REPLACE, never accumulate — the file holds at most one week's summary.

    Whatever last week parked and nobody collected is gone, deliberately: an
    undelivered follow-through summary about a week that is now two weeks old is not
    something to catch up on, and a file that grows by one summary a week forever is the
    standing cost § Costs asks about at the moment the parameter is set.
    """
    _write_weekly_state(persona, {
        "pending_summary": summary,
        "built_at": datetime.now().isoformat(timespec="seconds"),
    }, root=root)


def context_block(persona: str | None = None, *, root: Path | None = None) -> str:
    """
    The parked weekly follow-through, for the head layer's context. "" when quiet.

    Delivered once, on the same mechanism as tools/intake.py's digest: offered to every
    context load inside a 30-minute window (coordinator and synthesizer of one session
    both see it), then cleared by the first load after the window closes.

    This hands over NUMBERS AND THE USER'S OWN WORDS, nothing else. How it is said —
    whether it is said — belongs to `config/modules/synthesizer_scheduled_sessions.md`
    § Intention follow-through, and is not restated here. Nothing in this block is
    externally-authored text, so it is not wrapped: it is the user's own record coming
    back to them, and wrapping first-party words as untrusted would teach the head layer
    to hold the user at arm's length.
    """
    try:
        # `root` is resolved here rather than as a default argument: a default binds the
        # module-level ROOT at import time, which a test cannot then redirect.
        root = root or ROOT
        if persona is None:
            from core.persona import resolve_persona
            persona = resolve_persona()

        state = _read_weekly_state(persona, root=root)
        summary = state.get("pending_summary")
        if not isinstance(summary, dict) or not summary:
            return ""

        now = datetime.now()
        started = state.get("delivery_started")
        if started is None:
            state["delivery_started"] = now.isoformat(timespec="seconds")
            _write_weekly_state(persona, state, root=root)
        else:
            try:
                minutes = (now - datetime.fromisoformat(started)).total_seconds() / 60
            except (TypeError, ValueError):
                minutes = float("inf")
            if minutes > _WEEKLY_DELIVERY_WINDOW_MIN:
                _write_weekly_state(persona, {
                    "delivered_at": now.isoformat(timespec="seconds"),
                }, root=root)
                return ""

        counts = summary.get("counts") or {}
        lines = [
            f"[Intention follow-through — trailing "
            f"{summary.get('trailing_days', _WEEKLY_TRAILING_DAYS)} days to "
            f"{summary.get('as_of', '')}. Data for the weekly retrospective.]",
            f"{counts.get('total', 0)} stated · {counts.get('fulfilled', 0)} done · "
            f"{counts.get('unfulfilled', 0)} not done · "
            f"{counts.get('indeterminate', 0)} no record either way",
        ]
        for text in (summary.get("unfulfilled") or []):
            lines.append(f"- not done: {text}")
        for text in (summary.get("open") or []):
            lines.append(f"- no record either way: {text}")
        return "\n".join(lines)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[accountability] context block failed: {exc}")
        return ""


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
        # `×3` only when it was restated: frequency scores urgency, and a `×1` on every
        # row is noise that makes the ×3 harder to see rather than easier.
        times = it.get("times_stated", 1)
        freq = f" ×{times}" if times > 1 else ""
        judged = " [gate]" if it.get("judged_by") == "gate" else ""
        lines.append(f"  [{it['verdict']:13}] {it['logged_date']}{freq}  "
                     f"{it['intention'][:70]!r}{judged}  — {it['reason']}")
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
