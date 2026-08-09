"""
tools/calendar_reconcile.py — events whose time has passed with nothing in the record
about them.

THE REFRAME THAT SHAPES EVERY LINE BELOW
----------------------------------------
**The system cannot detect that something did not happen.** A passed event is not evidence
of a miss — most things happen and nobody reports them. What is detectable is *absence of
evidence*, which is a far weaker claim and can only ever be a question.

So nothing here asserts a miss, and nothing here notifies. Any wording that tells the user
an event "was missed" is a bug, not a phrasing preference.

A FUNCTION JOB MAY GATHER BUT MUST NOT JUDGE
--------------------------------------------
This runs as a `function:` scheduler job on tools/travel_watch.py's shape — seen-set,
report-once, never raises into the daemon — so a clean day costs no model tokens.

But a function job has no model. Deciding whether the day's log or conversation "references
an event" is crude text matching here, and it *will* produce false "no evidence" hits: the
user says "sorted the swim thing" and the title says "Manny — swim class, Aquatics Centre".
That is exactly why this **never returns `{"notify": True}`**, unlike travel_watch which
does. It writes candidates; a session with a model and the context already loaded decides
whether any is worth raising, and how. travel_watch can notify because a cancelled flight
is a fact from an airline; this has no equivalent authority behind it.

The counterpart rule: a model session may judge but must not poll. Neither half does the
other's work.

FIXED TIME, NOT AN INTERVAL
---------------------------
`fire_function` runs no gate stack — `days`, `respect_quiet_hours` and the activity gate
are all checked inside `fire_session` only (DEV_BACKLOG `[DB-0808-11]`). An
`interval_minutes` job would therefore be capable of firing at 3am with nothing to stop it.
This is the **third** workaround around that same missing gate stack, after
`daily_travel_check` at 06:45 and the maintenance jobs at 05:30/05:35. Pinning is cheap
here because the output is consumed by the morning brief rather than pushed — but the gap
should not be allowed a fourth dependent.

It registers in `_DEFAULT_JOBS` (core/scheduler.py), not config/templates/scheduler.yaml.
Silent token-free infrastructure belongs there: the template is copied **once**, at persona
creation, and nothing propagates a later change — `daily_calendar_dedup_audit` shipped to
the template on 2026-08-05 and had never run for mike three days later.

SCOPE, AND THE KNOB THAT NARROWS IT
-----------------------------------
Mike's decision, 2026-08-09: **every passed event**, not only ones tied to an obligation,
with narrowing wanted later as a calibration knob rather than a rewrite. So scope lives in
config/modules/calendar_reconcile.yaml and every filter is one edit away.

Named risk, honoured rather than pre-empted: recurring events are included by default
because "every event" was the decision, and they are the likeliest source of noise — asking
whether a daily standup happened is the kind of question that trains someone to stop
reading. `include_recurring: false` is the single line that fixes it if that turns out to
bite, and `ignore_titles` handles routine blocks individually.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timedelta
from pathlib import Path

import yaml

from core.persona import persona_config_dir, persona_data_dir, resolve_persona
from tools.caldav import _query_events
from tools.scheduling import _parse_dt

_MODULE_CONFIG = Path(__file__).parent.parent / "config" / "modules" / "calendar_reconcile.yaml"

# Defaults if the module config is missing. Deliberately inclusive — see § SCOPE.
_DEFAULTS = {
    "enabled": True,
    "lookback_hours": 30,        # covers yesterday evening through to a pre-dawn run
    "settle_minutes": 90,        # an event that ended 10 minutes ago is not unreported yet
    "scope": "all",              # "all" | "obligations" — the calibration knob Mike asked for
    "include_recurring": True,
    "include_all_day": False,    # a day-long "Holiday" block is not a thing that can not-happen
    "max_candidates": 5,
    "candidate_ttl_hours": 48,
    "ignore_titles": ["lunch", "commute", "focus time", "break", "travel", "wfh",
                      "out of office", "ooo", "holiday", "block"],
}

_STOPWORDS = {
    "the", "and", "for", "with", "from", "that", "this", "your", "you", "our",
    "was", "were", "will", "have", "has", "had", "not", "but", "all", "any",
    "meeting", "call", "appointment", "session", "class", "check", "review",
    "am", "pm", "mon", "tue", "wed", "thu", "fri", "sat", "sun",
}


def _config() -> dict:
    cfg = dict(_DEFAULTS)
    if _MODULE_CONFIG.exists():
        try:
            loaded = yaml.safe_load(_MODULE_CONFIG.read_text()) or {}
            if isinstance(loaded, dict):
                cfg.update({k: v for k, v in loaded.items() if k in _DEFAULTS})
        except Exception:
            pass
    return cfg


def _seen_path(persona: str) -> Path:
    return persona_data_dir(persona) / "logs" / ".calendar_reconcile_seen"


def _candidates_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "reconcile_candidates.json"


def _load_seen(persona: str) -> set[str]:
    p = _seen_path(persona)
    if not p.exists():
        return set()
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()}


def _record_seen(persona: str, keys: set[str]) -> None:
    p = _seen_path(persona)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a") as fh:
        for k in sorted(keys):
            fh.write(f"{k}\n")


def _event_key(uid: str, start: str) -> str:
    """Keyed on the occurrence, not the event — a recurring standup must be askable
    about on Tuesday even if Monday's was already reported once."""
    return hashlib.sha256(f"{uid}|{start}".encode()).hexdigest()[:16]


def _naive(dt: datetime | None) -> datetime | None:
    """Local naive. CalDAV may hand back UTC-marked times, and comparing an aware
    datetime to datetime.now() raises — in a daemon, silently killing the job."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt
    return dt.astimezone().replace(tzinfo=None)


def _tokens(text: str) -> set[str]:
    """Distinctive words from an event title, for crude reference matching."""
    words = re.findall(r"[a-z0-9']{3,}", (text or "").lower())
    return {w for w in words if w not in _STOPWORDS}


def _day_record_text(persona: str, days: tuple[str, ...]) -> str:
    """
    Everything written on the given days: the daily log plus the conversation record.

    Read as flat text on purpose. This is a presence check, not comprehension — and it is
    the crude half of the design, which is why its output can only ever be a candidate.
    """
    parts = []
    data_dir = persona_data_dir(persona)
    for day in days:
        log = data_dir / "logs" / f"{day}.json"
        if log.exists():
            try:
                parts.append(log.read_text())
            except OSError:
                pass
        conv = data_dir / "conversations" / f"{day}.jsonl"
        if conv.exists():
            try:
                for line in conv.read_text().splitlines():
                    line = line.strip()
                    if not line.startswith("{"):
                        continue
                    try:
                        rec = json.loads(line)
                    except ValueError:
                        continue
                    # The user's own words and the response both count as a reference.
                    parts.append(str(rec.get("user") or ""))
                    parts.append(str(rec.get("response") or ""))
            except OSError:
                pass
    return " ".join(parts).lower()


def find_unreferenced_events(persona: str | None = None) -> list[dict]:
    """
    Passed events with nothing in the day's record that looks like a reference.

    Returns evidence, never a verdict: {"uid", "title", "start", "end", "location",
    "matched_tokens", "checked_tokens"}. An event is only a candidate when **none** of its
    distinctive title words appear anywhere in the day's log or conversation — one match is
    enough to treat it as referenced, because a false candidate costs more than a missed one
    here (a wrong question trains the user to ignore the right one).
    """
    cfg = _config()
    resolved = resolve_persona(persona)
    now = datetime.now()
    window_start = now - timedelta(hours=int(cfg["lookback_hours"]))
    settle = timedelta(minutes=int(cfg["settle_minutes"]))

    raw = _query_events(window_start.date().isoformat(), now.date().isoformat(),
                        persona=resolved)
    if "error" in raw:
        return []

    days = tuple(sorted({
        (window_start + timedelta(days=d)).strftime("%Y-%m-%d")
        for d in range(0, (now.date() - window_start.date()).days + 1)
    }))
    record = _day_record_text(resolved, days)

    ignore = [t.lower() for t in cfg.get("ignore_titles") or []]
    obligation_tokens: set[str] = set()
    if cfg.get("scope") == "obligations":
        try:
            from tools.obligations import _load as _load_obligations
            for ob in _load_obligations(resolved):
                if ob.get("status") == "open":
                    obligation_tokens |= _tokens(str(ob.get("what", "")))
        except Exception:
            obligation_tokens = set()

    out: list[dict] = []
    for ev in raw.get("events", []):
        title = str(ev.get("title") or "").strip()
        if not title:
            continue
        if str(ev.get("status") or "").upper() == "CANCELLED":
            continue
        if any(tok in title.lower() for tok in ignore):
            continue
        if ev.get("recurrence") and not cfg.get("include_recurring", True):
            continue

        start = _naive(_parse_dt(str(ev.get("start") or "")))
        end = _naive(_parse_dt(str(ev.get("end") or ""))) or start
        if start is None:
            continue

        all_day = (start.hour, start.minute) == (0, 0) and \
                  (end is None or (end - start) >= timedelta(hours=23))
        if all_day and not cfg.get("include_all_day", False):
            continue

        # Passed, settled, and inside the lookback window.
        if end is None or end + settle > now or end < window_start:
            continue

        checked = _tokens(title)
        if not checked:
            continue
        if obligation_tokens and not (checked & obligation_tokens):
            continue

        matched = {t for t in checked if t in record}
        if matched:
            continue

        out.append({
            "uid": str(ev.get("uid") or ""),
            "title": title,
            "start": str(ev.get("start") or ""),
            "end": str(ev.get("end") or ""),
            "location": str(ev.get("location") or ""),
            "checked_tokens": sorted(checked),
            "matched_tokens": [],
        })

    out.sort(key=lambda c: c["start"])
    return out[:int(cfg["max_candidates"])]


def _write_candidates(persona: str, fresh: list[dict]) -> int:
    """
    Merge fresh candidates into the store, dropping anything past its TTL.

    A candidate nobody picked up in two days is not going to be usefully asked about, and
    keeping it means the morning brief is drawing on a widening pool of increasingly stale
    questions.
    """
    cfg = _config()
    path = _candidates_path(persona)
    ttl = timedelta(hours=int(cfg["candidate_ttl_hours"]))
    now = datetime.now()

    existing: list[dict] = []
    if path.exists():
        try:
            data = json.loads(path.read_text())
            existing = data.get("candidates", []) if isinstance(data, dict) else []
        except Exception:
            existing = []

    kept = []
    for c in existing:
        noted = _parse_dt(str(c.get("noted_at") or ""))
        if noted is not None and now - noted <= ttl:
            kept.append(c)

    known = {(c.get("uid"), c.get("start")) for c in kept}
    for c in fresh:
        if (c["uid"], c["start"]) in known:
            continue
        entry = dict(c)
        entry["noted_at"] = now.isoformat(timespec="seconds")
        kept.append(entry)

    kept.sort(key=lambda c: str(c.get("start") or ""))
    kept = kept[-int(cfg["max_candidates"]):]

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"candidates": kept}, indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass
    return len(kept)


def reconcile_check() -> str:
    """
    Scheduler entry point. Takes no arguments; persona comes from the scope.

    **Always returns a plain string, never a notify dict.** `fire_function` pushes only on
    a dict with `notify: True`, so returning a string is what makes this structurally
    incapable of interrupting the user — see § A FUNCTION JOB MAY GATHER BUT MUST NOT JUDGE.
    The string is printed to the journal and goes no further.

    Never raises: this runs unattended in a daemon.
    """
    cfg = _config()
    if not cfg.get("enabled", True):
        return "calendar reconcile disabled in config/modules/calendar_reconcile.yaml"

    try:
        persona = resolve_persona()
        candidates = find_unreferenced_events(persona)
    except Exception as e:
        return f"calendar reconcile skipped: {e}"

    if not candidates:
        return "no unreferenced passed events"

    try:
        seen = _load_seen(persona)
        fresh = [c for c in candidates if _event_key(c["uid"], c["start"]) not in seen]
        if not fresh:
            return f"{len(candidates)} unreferenced event(s), all already noted"

        _record_seen(persona, {_event_key(c["uid"], c["start"]) for c in fresh})
        held = _write_candidates(persona, fresh)
    except Exception as e:
        return f"calendar reconcile failed writing candidates: {e}"

    titles = ", ".join(c["title"] for c in fresh)
    return f"{len(fresh)} new candidate(s) for the morning brief ({held} held): {titles}"


def context_block(persona: str | None = None) -> str:
    """
    Candidates as a section for load_recent_context.

    The wording is load-bearing. It says what was actually established — the time passed and
    nothing in the record mentions it — and explicitly not that anything was missed, because
    the check cannot support that claim. It also states that most such events did happen,
    since a list of "possibly missed" items with no base rate reads as an accusation.
    """
    try:
        path = _candidates_path(persona)
        if not path.exists():
            return ""
        data = json.loads(path.read_text())
        candidates = data.get("candidates", []) if isinstance(data, dict) else []
    except Exception:
        return ""
    if not candidates:
        return ""

    lines = [
        "## Passed events with nothing in the record",
        "Their time has passed and nothing in the day's log or conversation mentions them. "
        "**This is absence of evidence, not evidence of absence** — most of these happened "
        "and simply went unmentioned, so treat any as a question at most, never as a miss, "
        "and never read the list out. If one is worth asking about, ask about one.",
    ]
    for c in candidates[:3]:
        when = str(c.get("start") or "")[:16].replace("T", " ")
        where = f" ({c['location']})" if c.get("location") else ""
        lines.append(f"- {when} — {c.get('title', '?')}{where}")
    if len(candidates) > 3:
        lines.append(f"- (+{len(candidates) - 3} more)")
    return "\n".join(lines)


if __name__ == "__main__":  # manual: python3 -m tools.calendar_reconcile <persona>
    import sys
    from core.persona import persona_scope

    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        found = find_unreferenced_events(who)
        print(f"{len(found)} unreferenced passed event(s):")
        for c in found:
            print(f"  {c['start']}  {c['title']!r}  tokens={c['checked_tokens']}")
        print()
        print(reconcile_check())
        print()
        print(context_block() or "(no context block)")
