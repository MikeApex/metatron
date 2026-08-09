"""
tools/obligations.py — commitments that stay open until something closes them.

WHY THIS IS DATA AND NOT SCHEDULER JOBS
---------------------------------------
tools/schedule.py § "Why obligations are not jobs" settled this before any of it was
built: twenty obligations each polling themselves daily is ~$15/month and twenty
interruptions. The intended shape is "a small number of sweeps that read all tracked
obligations at once, with individual obligations living as data." `MAX_AGENT_JOBS = 6`
and `MIN_INTERVAL_MINUTES = 360` exist to make the other shape impossible. This file is
the store that position assumed and nobody had written — that absence was the actual gap,
not any missing scheduling capability.

WHAT WENT WRONG WITHOUT IT
--------------------------
2026-08-07, 17:22: "I thought I already told you that the Rowan transfer was handled.
That is completed." Something was re-raising the payroll transfer and nothing could close
it. The nearest existing mechanism was `held_items` in tools/context_tracker.py, which is
ephemeral session state — it forgets, which is the opposite of the requirement.

So the failure to fix is not "we did not remind him enough". It is that **he closed it and
nothing recorded the closure.** That single fact sets three of the decisions below.

CLOSURE IS INFERRED, AND ITS EVIDENCE IS THE USER'S OWN WORDS
-------------------------------------------------------------
Mike's call, 2026-08-09: closure is inferred from conversation, not an explicit user
action — "in a dialogue these things will come up naturally." There is no "mark done"
gesture to perform, because requiring one is what produced the 08-07 failure.

Two consequences the code enforces rather than trusts:

1. **`close_obligation` requires evidence and stores it verbatim.** The backlog's own rule
   is that closed-without-evidence is not closed; the same standard applies here, and for
   the same reason — an inferred close with no record of what was inferred from cannot be
   audited or argued with later.
2. **Closing is reversible.** Inference is fallible by construction. `reopen_obligation`
   exists so a wrong close costs a sentence rather than a lost commitment, and the reopen
   keeps the original close on file instead of erasing it.

WHY NOTHING HERE BLOCKS
-----------------------
Over the cap, `open_obligation` still writes and warns. This project has settled that
argument once already (`check_new_rule` in core/rule_classes.py warns and never blocks):
refusing a write to keep a file tidy discards something the user actually said, which is
the worse failure. The cap is a signal to the reader, not a gate.

WHAT THIS FILE DOES NOT DO
--------------------------
It does not decide when to raise anything. The store is what a session **may** draw on,
never a list to recite — config/agents/synthesizer.md § Scheduled session conduct owns
that judgement, and the "open on one thing" guidance governs it. An obligation store wired
straight to a notification is the six-times-in-one-day problem rebuilt.
"""

from __future__ import annotations

import hashlib
from datetime import datetime
from pathlib import Path

import yaml

from core.persona import persona_data_dir

# Above this many open at once, every write carries a warning. Not a limit — see the
# module docstring on why nothing here blocks. The number is set where a morning session
# could no longer plausibly hold them all in view, which is the point at which the store
# has stopped being useful and started being a to-do list.
_SOFT_CAP = 12

# How many open obligations reach the session context block. Beyond this the block says
# how many more there are rather than listing them, because a long list in front of every
# session is exactly what "open on one thing" is meant to prevent.
_CONTEXT_MAX = 6


def _store_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "obligations.yaml"


def _load(persona: str | None = None) -> list[dict]:
    path = _store_path(persona)
    if not path.exists():
        return []
    try:
        data = yaml.safe_load(path.read_text()) or {}
    except Exception:
        # A corrupt store must not take down the session that read it. Returning empty
        # loses visibility for one call; raising would break every session until fixed.
        return []
    items = data.get("obligations")
    return items if isinstance(items, list) else []


def _save(items: list[dict], persona: str | None = None) -> None:
    path = _store_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump({"obligations": items}, sort_keys=False,
                                   allow_unicode=True))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _new_id(what: str) -> str:
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    digest = hashlib.sha256(f"{stamp}|{what}".encode()).hexdigest()[:6]
    return f"ob_{stamp[2:8]}_{digest}"


def _find(items: list[dict], obligation_id: str) -> dict | None:
    for it in items:
        if it.get("id") == obligation_id:
            return it
    return None


def _summarise(it: dict) -> str:
    bits = [it.get("what", "?")]
    if it.get("due"):
        bits.append(f"due {it['due']}")
    if it.get("domain"):
        bits.append(str(it["domain"]))
    return " — ".join(bits)


def open_obligation(what: str, domain: str | None = None, due: str | None = None,
                    note: str | None = None) -> str:
    """Record a commitment that stays open until it is closed."""
    what = (what or "").strip()
    if not what:
        return "error: `what` is required — an obligation with no description cannot be closed later"

    items = _load()
    open_now = [it for it in items if it.get("status") == "open"]

    # Near-duplicate guard. Two entries for one commitment is how a store starts
    # re-raising something the user already dealt with under the other id.
    lowered = what.lower()
    for it in open_now:
        existing = str(it.get("what", "")).lower()
        if existing == lowered or (len(lowered) > 12 and lowered in existing) \
                or (len(existing) > 12 and existing in lowered):
            return (f"already open as {it['id']}: {_summarise(it)}. "
                    f"Not filed twice — update or close that one instead.")

    entry = {
        "id": _new_id(what),
        "what": what,
        "status": "open",
        "opened_at": datetime.now().isoformat(timespec="seconds"),
    }
    if domain:
        entry["domain"] = domain.strip()
    if due:
        entry["due"] = due.strip()
    if note:
        entry["note"] = note.strip()

    items.append(entry)
    _save(items)

    msg = f"obligation {entry['id']} opened: {_summarise(entry)}"
    if len(open_now) + 1 > _SOFT_CAP:
        msg += (f"\n\nNOTE: {len(open_now) + 1} obligations are now open, past the {_SOFT_CAP} "
                f"this store is sized for. Written anyway. Several are probably done and "
                f"unclosed — worth asking about the oldest rather than carrying them all.")
    return msg


def close_obligation(obligation_id: str, evidence: str) -> str:
    """
    Close an obligation, recording what the user said that closed it.

    `evidence` is required and is stored verbatim. See the module docstring: an inferred
    close with no record of what it was inferred from cannot be checked afterwards, and
    the 2026-08-07 failure was precisely a closure that left no trace.
    """
    evidence = (evidence or "").strip()
    if not evidence:
        return ("error: `evidence` is required — quote what the user said that closes this. "
                "A close with no evidence cannot be verified or reversed sensibly.")

    items = _load()
    it = _find(items, (obligation_id or "").strip())
    if it is None:
        return f"error: no obligation with id {obligation_id!r}"
    if it.get("status") == "closed":
        return (f"{it['id']} was already closed at {it.get('closed_at', 'unknown')} "
                f"— nothing to do, and no second closure recorded.")

    it["status"] = "closed"
    it["closed_at"] = datetime.now().isoformat(timespec="seconds")
    it["evidence"] = evidence
    _save(items)
    return f"obligation {it['id']} closed: {_summarise(it)}"


def reopen_obligation(obligation_id: str, reason: str) -> str:
    """
    Reverse a close. The original close stays on file rather than being erased —
    a wrong inference is itself worth being able to look back at.
    """
    reason = (reason or "").strip()
    if not reason:
        return "error: `reason` is required — say why this is open again"

    items = _load()
    it = _find(items, (obligation_id or "").strip())
    if it is None:
        return f"error: no obligation with id {obligation_id!r}"
    if it.get("status") != "closed":
        return f"{it['id']} is already open — nothing to reopen"

    history = it.setdefault("close_history", [])
    history.append({
        "closed_at": it.get("closed_at"),
        "evidence": it.get("evidence"),
        "reopened_at": datetime.now().isoformat(timespec="seconds"),
        "reopen_reason": reason,
    })
    it["status"] = "open"
    for k in ("closed_at", "evidence"):
        it.pop(k, None)
    _save(items)
    return f"obligation {it['id']} reopened: {_summarise(it)} ({reason})"


def list_obligations(include_closed: bool = False) -> str:
    """List tracked obligations. Open ones by default."""
    items = _load()
    if not items:
        return "no obligations tracked"

    open_items = [it for it in items if it.get("status") == "open"]
    lines = [f"{len(open_items)} open:"] if open_items else ["nothing open"]
    for it in open_items:
        lines.append(f"  {it['id']}  {_summarise(it)}  (since {it.get('opened_at', '?')[:10]})")

    if include_closed:
        closed = [it for it in items if it.get("status") == "closed"]
        lines.append(f"\n{len(closed)} closed:")
        for it in closed:
            lines.append(f"  {it['id']}  {_summarise(it)}  closed {it.get('closed_at', '?')[:10]}"
                         f" — evidence: {str(it.get('evidence', ''))[:80]}")
    return "\n".join(lines)


def context_block(persona: str | None = None) -> str:
    """
    Open obligations as a section for load_recent_context — no model call, no tool call.

    In the context rather than behind a tool because the point of the store is that
    something outstanding cannot be missed for want of the session thinking to look. It is
    labelled as material to draw on precisely so it does not read as an agenda: see
    config/agents/synthesizer.md § Scheduled session conduct.
    """
    try:
        items = [it for it in _load(persona) if it.get("status") == "open"]
    except Exception:
        return ""
    if not items:
        return ""

    items.sort(key=lambda it: str(it.get("due") or "9999"))
    shown = items[:_CONTEXT_MAX]
    lines = ["## Open obligations",
             "Commitments recorded as outstanding. Material you may draw on — not an agenda, "
             "and not a list to read out. If the conversation shows one is done, close it."]
    for it in shown:
        lines.append(f"- `{it['id']}` {_summarise(it)}")
    if len(items) > len(shown):
        lines.append(f"- (+{len(items) - len(shown)} more — `list_obligations` if needed)")
    return "\n".join(lines)


OPEN_OBLIGATION_SCHEMA = {
    "name": "open_obligation",
    "description": (
        "Record a commitment that stays outstanding until it is closed — a payment to make, "
        "a form to send, a call owed to someone. Use this for things that persist across "
        "days and would matter if they were forgotten, not for today's task list. "
        "Do not file the same commitment twice; near-duplicates are refused."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "what": {"type": "string",
                     "description": "The commitment, in a form that still makes sense in a "
                                    "week. 'Rowan payroll transfer', not 'that transfer'."},
            "domain": {"type": "string",
                       "description": "Optional life domain — finance, logistics, health, work."},
            "due": {"type": "string",
                    "description": "Optional date (YYYY-MM-DD) or short phrase if genuinely vague."},
            "note": {"type": "string", "description": "Optional one line of context."},
        },
        "required": ["what"],
    },
}

CLOSE_OBLIGATION_SCHEMA = {
    "name": "close_obligation",
    "description": (
        "Close an obligation once the conversation shows it is done. Closure is inferred "
        "from what the user says — there is no action they have to perform — so close it "
        "as soon as you hear it rather than waiting to be told twice. `evidence` must "
        "quote their words: a close with no record of what closed it cannot be checked "
        "or sensibly reversed. Use reopen_obligation if you got it wrong."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "obligation_id": {"type": "string", "description": "The id, e.g. ob_260809_a1b2c3."},
            "evidence": {"type": "string",
                         "description": "What the user said that closes this, quoted or closely "
                                        "paraphrased. Required."},
        },
        "required": ["obligation_id", "evidence"],
    },
}

REOPEN_OBLIGATION_SCHEMA = {
    "name": "reopen_obligation",
    "description": (
        "Reverse a close that turned out to be wrong. The original close stays on file. "
        "Use this when the user indicates something you closed is in fact still outstanding."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "obligation_id": {"type": "string", "description": "The id to reopen."},
            "reason": {"type": "string", "description": "Why it is open again."},
        },
        "required": ["obligation_id", "reason"],
    },
}

LIST_OBLIGATIONS_SCHEMA = {
    "name": "list_obligations",
    "description": (
        "List tracked obligations. Open ones are already in your session context, so call "
        "this only when you need ids, closed history, or the full set beyond what context shows."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "include_closed": {"type": "boolean",
                               "description": "Include closed obligations and their evidence."},
        },
        "required": [],
    },
}


if __name__ == "__main__":  # manual: python3 -m tools.obligations <persona>
    import sys
    from core.persona import persona_scope

    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        print(list_obligations(include_closed=True))
        print()
        print(context_block() or "(no context block)")
