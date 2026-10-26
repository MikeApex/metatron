"""
tools/routines.py — the user can pause a routine Metatron runs for them, and resume it.

WHY THIS EXISTS
---------------
Mike, 2026-10-24 and again 10-26: he had asked several times for the Franklin virtue review to
be dropped from the evening check-in "for the time being", and it kept coming back. Not an
adherence failure — an ability one. The review is `config/personas/mike/evening_ritual.md`,
which core/orchestrator.py `_owned_rituals()` injects into every evening close; nothing a model
could call changed that, so each "skip it for now" was agreed to in one reply and replaced by
the same thirty lines the next night. The user's own scheduled check-ins (scheduler.yaml) had
the same gap: `delete_schedule` reaches only the jobs an agent wrote.
Plan: archive/plans/routine_pause_plan_2026-10-26.md.

WHAT CAN BE PAUSED (Mike, 10-26: rituals + the check-ins that talk to the user)
-------------------------------------------------------------------------------
- **Rituals** — every `*_ritual.md` in the persona's config. Id = the file stem
  (`evening_ritual`); `manny_school` is both a ritual owner and a schedule key, so the owner
  name alone would be ambiguous. `evening` resolves to `evening_ritual` as a convenience.
- **Check-ins** — the user's own `scheduler.yaml` jobs that are enabled, run an agent, and
  notify the user (push/both). Not the machinery Metatron runs over them: function jobs (the
  clinical review, travel alerts), terminal-only analyses, and every `_DEFAULT_JOBS` key.

THE SCOPE IS DELIBERATELY NARROW (Mike: "ensure users have limited scope to change things that
they otherwise didn't initiate and that Metatron did")
---------------------------------------------------------------------------------------------
1. **Pause and resume only.** Nothing here edits, rewrites or deletes a ritual file or
   scheduler.yaml; a pause is a separate record, so resuming restores the routine exactly.
2. **Only the user's own words.** Inside a pipeline turn that carries no user speech — a
   scheduled run, the system talking to itself — a pause or resume is refused. Keyed on the
   turn's `user_turn`, which both pipeline twins bind (`close_gate`/`user_text` exist on the
   streaming twin only — plan review finding 4). No bound turn (a direct call) is allowed.
   The turn's real words are stored beside the model's `evidence` as `user_said`.
3. **Only routines that exist and are pausable**; anything else is refused with the real list.

THE REVISIT
-----------
A pause may carry a `revisit` date. On or after it, the next morning brief or evening close is
told once to ask whether to bring the routine back (`revisit_note`), and the turn's close
stamps it (`mark_revisits_raised`) — only once a reply was actually delivered, so a failed run
does not consume the one question (review finding 2). Re-pausing replaces the date — empty
means "for good" — and clears the stamp (finding 3).

Store: `data/personas/{p}/routine_pauses.yaml` —
`{paused: {<id>: {kind, at, evidence, user_said, revisit, revisit_raised}}}`.
"""

from __future__ import annotations

import os
import threading
from datetime import date, datetime
from pathlib import Path

import yaml

from core.persona import persona_config_dir, persona_data_dir

_LOCK = threading.RLock()
_RITUAL_SUFFIX = "_ritual.md"
# Where a revisit question is raised: the two fixed points of the day, which never get the
# quiet "nothing new" directive (core/orchestrator.py _FIXED_SESSION_KINDS).
_REVISIT_KINDS = ("morning_brief", "evening_close")


def _store(persona: str | None) -> Path:
    return persona_data_dir(persona) / "routine_pauses.yaml"


def _load(persona: str | None) -> dict:
    p = _store(persona)
    try:
        doc = yaml.safe_load(p.read_text()) if p.exists() else None
    except (OSError, yaml.YAMLError):
        doc = None
    doc = doc if isinstance(doc, dict) else {}
    if not isinstance(doc.get("paused"), dict):
        doc["paused"] = {}
    return doc


def _save(persona: str | None, doc: dict) -> None:
    p = _store(persona)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(doc, sort_keys=True, allow_unicode=True))
    os.chmod(tmp, 0o600)
    os.replace(tmp, p)


def _paused(persona: str | None) -> dict:
    """The paused records. Never raises: an unreadable store pauses nothing, so the worst
    failure is a routine running as it always has."""
    try:
        return _load(persona)["paused"]
    except Exception:
        return {}


def paused_routines(persona: str | None = None) -> frozenset[str]:
    """Ids of every paused routine."""
    return frozenset(_paused(persona))


def paused_checkins(persona: str | None = None) -> frozenset[str]:
    """Ids of the paused scheduled check-ins only — what the scheduler holds. Rituals are
    excluded so an agent-written job sharing a ritual's name is never held (finding 5)."""
    return frozenset(k for k, r in _paused(persona).items()
                     if isinstance(r, dict) and r.get("kind") == "checkin")


# ---------------------------------------------------------------------------
# What exists
# ---------------------------------------------------------------------------

def _rituals(persona: str | None) -> dict[str, str]:
    """{id: one-line description} for each ritual file."""
    out: dict[str, str] = {}
    try:
        paths = sorted(persona_config_dir(persona).glob(f"*{_RITUAL_SUFFIX}"))
    except OSError:
        return out
    for path in paths:
        try:
            first = next((ln.strip() for ln in path.read_text().splitlines() if ln.strip()), "")
        except OSError:
            first = ""
        owner = path.name[: -len(_RITUAL_SUFFIX)]
        out[path.stem] = f"part of the {owner} check-in: {first[:100]}"
    return out


def _checkins(persona: str | None) -> dict[str, str]:
    """{schedule key: one-line description} for the user's own user-facing check-ins."""
    try:
        cfg = yaml.safe_load((persona_config_dir(persona) / "scheduler.yaml").read_text()) or {}
    except (OSError, yaml.YAMLError):
        return {}
    try:
        from core.scheduler import _DEFAULT_JOBS
        machinery = set(_DEFAULT_JOBS)
    except Exception:
        machinery = set()
    out: dict[str, str] = {}
    for key, job in (cfg.get("schedules") or {}).items():
        if not isinstance(job, dict) or key in machinery:
            continue
        if not job.get("enabled", True) or not job.get("agent") or job.get("function"):
            continue
        if job.get("notification") not in ("push", "both"):
            continue
        if job.get("interval_minutes"):
            when = f"every {job['interval_minutes']} min when quiet"
        else:
            when = f"{job.get('day') or job.get('days') or 'daily'} {job.get('time', '')}".strip()
        prompt = " ".join(str(job.get("prompt") or "").split())
        out[str(key)] = f"check-in, {when}: \"{prompt[:80]}\""
    return out


def _available(persona: str | None) -> dict[str, tuple[str, str]]:
    """{id: (kind, description)}."""
    out = {k: ("ritual", d) for k, d in _rituals(persona).items()}
    out.update({k: ("checkin", d) for k, d in _checkins(persona).items()})
    return out


def _resolve(routine: str, persona: str | None) -> tuple[str | None, str | None]:
    name = (routine or "").strip().lower().removesuffix(".md").replace(" ", "_")
    real = _available(persona)
    for candidate in (name, f"{name}_ritual"):
        if candidate in real:
            return candidate, None
    listed = ", ".join(sorted(real)) or "none"
    return None, (f"error: no routine called {routine!r} that can be paused. The user's "
                  f"routines are: {listed}.")


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------

def _user_words_refusal() -> str | None:
    """Only a user turn may pause or resume. No bound turn (a direct call) allows."""
    try:
        from tools.turn_context import current
        turn = current()
    except Exception:
        turn = None
    if turn is None or turn.get("user_turn"):
        return None
    return ("error: not changed — a routine can be paused or resumed only when the user asks "
            "for it, and this turn has nothing from the user.")


def _user_said() -> str:
    try:
        from tools.turn_context import current
        return str((current() or {}).get("user_text") or "").strip()[:300]
    except Exception:
        return ""


def _parse_revisit(revisit: str) -> tuple[str | None, str | None]:
    text = (revisit or "").strip()
    if not text:
        return None, None
    try:
        d = date.fromisoformat(text[:10])
    except ValueError:
        return None, f"error: `revisit` must be a date like 2027-01-26, not {revisit!r}."
    if d <= date.today():
        return None, "error: `revisit` must be a date after today."
    return d.isoformat(), None


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def pause_routine(routine: str, evidence: str = "", revisit: str = "",
                  persona: str | None = None) -> str:
    """Pause one of the user's routines until they ask for it back."""
    words = (evidence or "").strip()
    if not words:
        return "error: `evidence` is required — the user's own words asking for the pause."
    refusal = _user_words_refusal()
    if refusal:
        return refusal
    name, err = _resolve(routine, persona)
    if err:
        return err
    when, err = _parse_revisit(revisit)
    if err:
        return err
    back = f"; Metatron will ask about it once on or after {when}" if when else ""
    with _LOCK:
        doc = _load(persona)
        rec = doc["paused"].get(name)
        if rec is not None:
            # Re-pausing is how "keep it off" answers a revisit: the date is replaced, never
            # kept — empty means for good — so a past date cannot re-ask every run.
            rec["revisit"] = when
            rec["revisit_raised"] = None
            # The latest words are the reason it is still off (diff review finding 3).
            rec["evidence"] = words
            rec["user_said"] = _user_said() or rec.get("user_said", "")
            rec["renewed"] = datetime.now().isoformat(timespec="seconds")
            _save(persona, doc)
            since = str(rec.get("at", "?"))[:10]
            return f"{name} stays paused (since {since}){back or '; no check-back date'}"
        doc["paused"][name] = {
            "kind": _available(persona)[name][0],
            "at": datetime.now().isoformat(timespec="seconds"),
            "evidence": words,
            "user_said": _user_said(),
            "revisit": when,
            "revisit_raised": None,
        }
        _save(persona, doc)
    return (f"{name} is paused until the user asks for it back{back}. Nothing in it was "
            f"changed; resuming restores it exactly.")


def resume_routine(routine: str, evidence: str = "", persona: str | None = None) -> str:
    """Bring a paused routine back, exactly as it was."""
    if not (evidence or "").strip():
        return "error: `evidence` is required — the user's own words asking for it back."
    refusal = _user_words_refusal()
    if refusal:
        return refusal
    name, err = _resolve(routine, persona)
    if err:
        return err
    with _LOCK:
        doc = _load(persona)
        if name not in doc["paused"]:
            return f"{name} is not paused — it runs as usual"
        doc["paused"].pop(name)
        _save(persona, doc)
    return f"{name} is back, exactly as it was"


def list_routines(persona: str | None = None) -> str:
    """The user's routines that can be paused, and which are."""
    real = _available(persona)
    if not real:
        return "no routines are set up"
    paused = _paused(persona)
    lines = []
    for name in sorted(real):
        kind, desc = real[name]
        rec = paused.get(name)
        if rec:
            state = f"PAUSED since {str(rec.get('at', '?'))[:10]}"
            if rec.get("revisit"):
                state += f", check back {rec['revisit']}"
        else:
            state = "running"
        lines.append(f"- {name} ({kind}) — {state} — {desc}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# What the pipeline reads
# ---------------------------------------------------------------------------

def _revisit_kind_ok(kind: str, persona: str | None) -> bool:
    paused = _paused(persona)
    running = [k for k in _checkins(persona) if k not in paused]
    if kind not in running:
        return False
    # Prefer the day's fixed points, but only ones still running: a user who paused both
    # must still be asked somewhere (diff review finding 2).
    fixed = [k for k in _REVISIT_KINDS if k in running]
    return kind in fixed if fixed else True


def _due(kind: str | None, persona: str | None) -> list[tuple[str, dict]]:
    if not kind or not _revisit_kind_ok(kind, persona):
        return []
    today = date.today().isoformat()
    return [(name, rec) for name, rec in sorted(_paused(persona).items())
            if rec.get("revisit") and str(rec["revisit"]) <= today and not rec.get("revisit_raised")]


def focus_lines(kind: str | None, persona: str | None = None) -> list[str]:
    """
    Lines for a scheduled run's focus block: every paused routine (so nothing else — the
    morning catch-up rule, a log showing the ritual on earlier days, an old unanswered
    question — brings it back; plan review finding 1), then any revisit now due.
    Read-only: the revisit is stamped by mark_revisits_raised() once a reply went out.
    """
    if not kind:
        return []
    paused = _paused(persona)
    if not paused:
        return []
    real = _available(persona)
    lines = ["PAUSED BY THE USER — do not run, offer, catch up on, or mention these unless "
             "the user raises them (or a CHECK BACK line below asks you to):"]
    for name in sorted(paused):
        lines.append(f"  - {name}: {real.get(name, ('', 'no longer set up'))[1]}")
    for name, rec in _due(kind, persona):
        evidence = str(rec.get("evidence") or "")[:120]
        lines += ["", (f"CHECK BACK, ONCE: on {str(rec.get('at', '?'))[:10]} the user paused "
                       f"{name} (\"{evidence}\") and asked to revisit around {rec['revisit']}. "
                       f"Ask once, briefly, whether to bring it back (resume_routine) or keep it "
                       f"off (pause_routine again, with a new revisit date or none). If they "
                       f"don't answer, leave it paused.")]
    return lines


def mark_revisits_raised(kind: str | None, delivered: bool, persona: str | None = None) -> None:
    """Stamp the revisits this run carried — only when its reply reached the user (the caller
    decides: core/orchestrator.py _stamp_routine_revisits, after the confidentiality filter)."""
    if not delivered:
        return
    due = _due(kind, persona)
    if not due:
        return
    with _LOCK:
        doc = _load(persona)
        stamp = datetime.now().isoformat(timespec="seconds")
        for name, _ in due:
            if name in doc["paused"]:
                doc["paused"][name]["revisit_raised"] = stamp
        _save(persona, doc)


_ROUTINE_ARG = {"type": "string",
                "description": "The routine's id as list_routines shows it, e.g. 'evening_ritual'."}
_EVIDENCE_ARG = {"type": "string", "description": "The user's own words asking for this."}

PAUSE_ROUTINE_SCHEMA = {
    "name": "pause_routine",
    "description": (
        "Pause one of the user's routines — a structured part of a check-in (such as an evening "
        "review) or a scheduled check-in itself — when the user asks to drop, skip or stop it "
        "for a while. It stops until they ask for it back; nothing in it is changed or deleted. "
        "Only on the user's own request, with their words as evidence. `revisit`: a date "
        "(YYYY-MM-DD) to ask once whether to bring it back — the end of a period they named, "
        "about three months out for 'for now' or 'for a while', omitted for 'for good'. "
        "Calling it on an already paused routine replaces the revisit date."
    ),
    "input_schema": {"type": "object",
                     "properties": {"routine": _ROUTINE_ARG, "evidence": _EVIDENCE_ARG,
                                    "revisit": {"type": "string",
                                                "description": "Optional date, YYYY-MM-DD."}},
                     "required": ["routine", "evidence"]},
}
RESUME_ROUTINE_SCHEMA = {
    "name": "resume_routine",
    "description": "Bring back a routine the user paused, exactly as it was. Only on their request.",
    "input_schema": {"type": "object", "properties": {"routine": _ROUTINE_ARG,
                                                      "evidence": _EVIDENCE_ARG},
                     "required": ["routine", "evidence"]},
}
LIST_ROUTINES_SCHEMA = {
    "name": "list_routines",
    "description": "The user's routines that can be paused, and which are.",
    "input_schema": {"type": "object", "properties": {}, "required": []},
}
