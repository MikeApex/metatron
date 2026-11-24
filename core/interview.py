"""
core/interview.py — the first interview, in the app: goals and the shape of the day, one
conversation (plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.7, Mike's ruling 8).

While a user's interview is **active**, a message sent in the app goes straight to the Goals
Interviewer with the whole interview so far as its history — not through the Coordinator →
Synthesizer pipeline, whose five-turn history would lose the thread and whose relay would put
a second voice between her and the interviewer. Paused or complete, messages go back to the
pipeline as normal.

**One file decides everything:** `data/personas/{p}/interview/state.json`, written first by
`scripts/accounts.py approve` (`status: not_started`). It exists only for approved account
users, never for `mike` or a test persona, so *no file means no interview mode, ever*. The
scheduler's hold gate (§ 4.6) reads the same file and nothing else; neither looks at
`goals.yaml`, which `new_persona.sh` creates as three empty lists before she has signed in.

    status: not_started | active | paused | complete

**Coverage comes from what is stored, not from the model's memory.** Each turn the
interviewer gets a code-built block — goals per horizon, mission and prime directive written /
awaiting her confirmation / not yet, a baseline period, each day-shape section set or
missing, calendars when one is connected. That is what lets a paused interview resume days
later knowing exactly what is left, and it cannot drift from what was saved.

**A pending write is never reported as done (review L1).** `write_config` raises a card and
returns PENDING_CONFIRMATION; the pipeline's `enforce_pending_receipt()` stops a reply claiming
otherwise, and the single-agent path this runs on did not call it. `run_turn` does, the
coverage block shows the third state, and `finish_interview()` refuses while one is waiting.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

AGENT = "goals_interviewer"
STATUSES = ("not_started", "active", "paused", "complete")

# The transcript handed back each turn is capped (plan § 4.7): ~60K tokens of the most recent
# history, at ~4 characters a token. Older turns drop; coverage and what was saved carry the
# facts, which is why the coverage block exists.
HISTORY_CHAR_BUDGET = 240_000

# The prompt for the opening turn. Written by code, never shown to her as something she said.
OPENING_PROMPT = ("(The user has just signed in for the first time and the app has opened straight "
                  "into this conversation. Open the interview.)")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def state_path(persona: str) -> Path:
    from core.persona import persona_data_dir
    return persona_data_dir(persona) / "interview" / "state.json"


def read_state(persona: str) -> dict | None:
    """The interview state, or None when the persona has no interview (every existing one)."""
    path = state_path(persona)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def status(persona: str) -> str | None:
    state = read_state(persona)
    return state.get("status") if state else None


def holds_proactive(persona: str) -> bool:
    """The scheduler's hold gate (D2, review L6): only a state file saying not_started or
    active holds proactive sessions. No file — every existing persona — never holds."""
    return status(persona) in ("not_started", "active")


# While she has paused setup, scheduled sessions run (D2) — so they carry a light invitation to
# finish it: at most once a day, and RESUME_INVITES_MAX times in all, so an interview she has
# chosen to leave is not nagged about forever (Mike, 2026-11-23: "start on pause, but encourage
# her to complete the interview").
RESUME_INVITES_MAX = 3

RESUME_INVITATION = (
    "Their first setup conversation is paused, so you know little about them yet. In this "
    "message, once and lightly, invite them to finish it with the app's 'Continue setting up' "
    "button, saying in a few words what it would change for them — check-ins and a plan that "
    "fit their life. Do not press, and do not raise it again in this message.")


def resume_invitation(persona: str, today: str | None = None) -> str:
    """The invitation line for a scheduled run, or "" — and records that it was given."""
    if status(persona) != "paused":       # checked before the lock: no file is ever created
        return ""
    day = today or datetime.now().date().isoformat()
    with _locked(persona) as path:
        state = read_state(persona)
        if not state or state.get("status") != "paused":
            return ""
        given = list(state.get("resume_invites") or [])
        if day in given or len(given) >= RESUME_INVITES_MAX:
            return ""
        state["resume_invites"] = given + [day]
        _write(path, state)
    return RESUME_INVITATION


@contextlib.contextmanager
def _locked(persona: str):
    path = state_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield path
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def _write(path: Path, state: dict) -> None:
    fd, tmp = tempfile.mkstemp(prefix=".state.", dir=str(path.parent))
    with os.fdopen(fd, "w") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _transition(persona: str, allowed_from: tuple[str, ...], to: str, **extra) -> bool:
    """Move the state if, and only if, it is currently one of `allowed_from`. Atomic."""
    with _locked(persona) as path:
        state = read_state(persona)
        if not state or state.get("status") not in allowed_from:
            return False
        state.update(status=to, updated_at=_now(), **extra)
        _write(path, state)
    return True


def claim_start(persona: str) -> bool:
    """
    Mark a not_started interview active, BEFORE the opening is generated — so two sockets
    connecting at once (a reconnect race, a phone and a browser) start it exactly once.
    True for the one caller that should run the opening.
    """
    return _transition(persona, ("not_started",), "active", started_at=_now())


def release_start(persona: str) -> bool:
    """Undo a claim whose opening failed (Stage 2 review F4): back to not_started, so her next
    connection claims and opens again instead of leaving an active interview with no first
    message. Only while no turn has completed — never rewinds a conversation in progress."""
    with _locked(persona) as path:
        state = read_state(persona)
        if not state or state.get("status") != "active" or int(state.get("turns") or 0) > 0:
            return False
        state.update(status="not_started", updated_at=_now())
        _write(path, state)
    return True


def pause(persona: str) -> bool:
    return _transition(persona, ("active",), "paused")


def resume(persona: str) -> bool:
    return _transition(persona, ("paused",), "active")


def count_turn(persona: str) -> None:
    with _locked(persona) as path:
        state = read_state(persona)
        if state:
            state["turns"] = int(state.get("turns") or 0) + 1
            state["updated_at"] = _now()
            _write(path, state)


# ---------------------------------------------------------------------------
# Coverage — from what is stored
# ---------------------------------------------------------------------------

_PLACEHOLDER = "<!-- Populated by the Goals Interview"


def _tier_state(persona: str, filename: str, waiting: set[str]) -> str:
    from core.persona import persona_config_dir
    path = persona_config_dir(persona) / filename
    text = path.read_text().strip() if path.exists() else ""
    if text and not text.startswith(_PLACEHOLDER):
        return "written"
    if filename in waiting:
        return "awaiting the user's confirmation in the app"
    return "not yet"


def pending_config_files(persona: str) -> set[str]:
    """Which Tier 1/2 files have a write_config card waiting on her — server state."""
    try:
        from tools import confirm
        live = {p["token"] for p in confirm.pending(persona) if p.get("action") == "write_config"}
        return {(e.get("args") or {}).get("filename")
                for t, e in confirm._load(persona).items() if t in live} - {None}
    except Exception:  # noqa: BLE001 — coverage must never take the turn down
        return set()


def _goal_counts(persona: str) -> str:
    import yaml
    from core.persona import persona_config_dir
    path = persona_config_dir(persona) / "goals.yaml"
    try:
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
    except Exception:  # noqa: BLE001
        data = {}
    parts = [f"{h} {len(v) if isinstance(v, list) else 0}"
             for h, v in (data or {}).items()]
    return ", ".join(parts) if parts else "none recorded"


def _baseline_recorded(persona: str) -> bool:
    from core.persona import persona_scope
    try:
        from tools.baselines import read_baseline_periods
        with persona_scope(persona):
            return bool(read_baseline_periods())
    except Exception:  # noqa: BLE001
        return False


# Plain words, never the section identifiers: this block travels inside the turn's input, and
# filter_output() exempts identifiers the user "typed" — an identifier here would let the same
# identifier through in the reply.
_SHAPE_SECTIONS = {"day": "when the day starts and ends", "windows": "when each kind of work goes",
                   "meals": "meals", "routines": "routines", "children_home":
                   "when anyone in their care is home", "travel_mode": "how they get around",
                   "location_sharing": "whether they share their location"}


def _practicalities(persona: str) -> list[str]:
    """The people-and-practicalities half (goals_interviewer.md, 2026-11-23): what is saved,
    in plain words, plus any contact still waiting on her tap — a contact card left untapped is
    never saved, and nothing else would tell the interviewer so (plan review L7)."""
    from core.persona import persona_scope
    lines: list[str] = []
    try:
        from tools import crm, profile, wisdom
        with persona_scope(persona):
            people = len(crm._load_contacts())
            facts = sum(1 for e in wisdom._all_entries()
                        if isinstance(e, dict) and not e.get("archived") and not e.get("merged_into"))
            prof = profile._load()
        # write_profile keeps a scalar field at the top level and a contact field (address,
        # email, phone) under `contact` — tools/profile.py write_profile.
        home = [label for label, present in (
            ("who they live with", prof.get("household")),
            ("home address", (prof.get("contact") or {}).get("address")))
            if present]
        lines += [f"- People saved: {people}",
                  f"- Standing facts saved: {facts}",
                  f"- Home — set: {', '.join(home) or 'nothing yet'}"]
    except Exception:  # noqa: BLE001 — coverage must never take the turn down
        pass
    try:
        from tools import confirm
        cards = [p for p in confirm.pending(persona) if p.get("action") == "write_contact"]
        if cards:
            # A card lapses unseen after confirm.TTL_SECONDS, and nothing then tells the
            # interviewer (review 2026-11-23, finding 2) — so the line says so while it can.
            lines.append(f"- {len(cards)} contact change(s) are waiting for the user's tap in the "
                         "app and lapse after ten minutes; until they tap, they are not saved. If "
                         "one lapses, the people count will not have risen: ask again.")
    except Exception:  # noqa: BLE001
        pass
    return lines


def _calendar_connected(persona: str) -> bool:
    import yaml
    from core.persona import persona_config_dir
    path = persona_config_dir(persona) / "caldav.yaml"
    try:
        return bool((yaml.safe_load(path.read_text()) or {}).get("enabled")) if path.exists() else False
    except Exception:  # noqa: BLE001
        return False


def coverage_block(persona: str, capture_lines: str = "") -> str:
    """The code-built account of what this interview has saved so far (plan § 4.7, 2.2/2.9).

    `capture_lines` is what the user said on an earlier turn that nothing saved — capture
    fidelity's one-turn-late channel (archive/plans/capture_fidelity_plan_2026-11-18.md § 4.1)."""
    from tools.day_shape import read_shape
    waiting = pending_config_files(persona)
    try:
        shape = read_shape(persona) or {}
    except Exception:  # noqa: BLE001
        shape = {}
    sections = dict(_SHAPE_SECTIONS)
    if _calendar_connected(persona):
        sections["calendars"] = "which calendars are theirs, shared or to ignore"
    have = [label for key, label in sections.items() if shape.get(key) not in (None, [], {}, "")]
    missing = [label for key, label in sections.items() if label not in have]
    lines = [
        "INTERVIEW COVERAGE — read from what is saved, not from memory of the conversation:",
        f"- Goals saved: {_goal_counts(persona)}",
        f"- Mission: {_tier_state(persona, 'mission.md', waiting)}",
        f"- Prime directive: {_tier_state(persona, 'prime_directive.md', waiting)}",
        f"- Remembered good period: {'recorded' if _baseline_recorded(persona) else 'not yet'}",
        f"- Shape of the day — set: {', '.join(have) or 'nothing yet'}; "
        f"missing: {', '.join(missing) or 'nothing'}",
        *_practicalities(persona),
    ]
    if waiting:
        lines.append("- Something is waiting for the user's confirmation in the app; tell them "
                     "plainly it needs their tap before it is saved.")
    if capture_lines:
        lines.append(capture_lines)
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# The two tools the interviewer holds (registered in core/orchestrator.py)
# ---------------------------------------------------------------------------

def pause_interview(resume_on: str = "") -> str:
    """She wants to stop for now. Nothing is lost; the app offers *Continue setting up*."""
    from core.persona import resolve_persona
    persona = resolve_persona()
    # The first interview first — the server routes to it ahead of a goal talk, so a "let's stop"
    # in it must stop it (Fable L10). Then a goal talk (goal network plan § 18), which stops
    # through the same tool: the Safety section and "let's stop" reach it with no second grant.
    if status(persona) != "active":
        try:
            from tools import goal_talk
            if goal_talk.active(persona):
                return goal_talk.pause_tool(persona, resume_on)
        except Exception:  # noqa: BLE001
            pass
    if pause(persona):
        return ("Paused. Everything saved so far is kept; the user can pick this up from the "
                "app's 'Continue setting up' button whenever they like.")
    return "There is no active interview to pause."


def finish_interview() -> str:
    """The first draft is done and she agrees. Refuses while a Tier 1/2 write awaits her tap."""
    from core.persona import resolve_persona
    persona = resolve_persona()
    waiting = pending_config_files(persona)
    if waiting:
        return ("Not finished: " + " and ".join(sorted(waiting)) + " is still waiting for the "
                "user's confirmation in the app. Ask them to approve it (or say they'd rather "
                "leave it), then finish.")
    if _transition(persona, ("active", "paused"), "complete", completed_at=_now()):
        return "Interview complete. From their next message they are talking to Metatron as usual."
    return "There is no interview in progress to finish."


PAUSE_INTERVIEW_SCHEMA = {
    "name": "pause_interview",
    "description": ("Pause this first conversation because the user wants to stop for now. "
                    "Everything saved is kept and they can resume from the app."),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}

def pause_schema() -> dict:
    """PAUSE_INTERVIEW_SCHEMA as models should see it: with `goal_talk` on, it also pauses a talk
    about one goal and takes the day to carry on (Fable S7). Off, the constant, unchanged."""
    try:
        from tools.goal_talk import on
        talk = on()
    except Exception:  # noqa: BLE001
        talk = False
    if not talk:
        return PAUSE_INTERVIEW_SCHEMA
    import copy
    s = copy.deepcopy(PAUSE_INTERVIEW_SCHEMA)
    s["description"] = ("Pause this conversation — the first one, or a talk about one goal — "
                        "because the user wants to stop for now. Everything saved is kept.")
    s["input_schema"]["properties"]["resume_on"] = {
        "type": "string",
        "description": "In a talk about one goal: YYYY-MM-DD the user picked to carry on, if they "
                       "picked one. The talk comes back on their list that day."}
    return s


FINISH_INTERVIEW_SCHEMA = {
    "name": "finish_interview",
    "description": ("Finish this first conversation once the first draft is saved and the user "
                    "agrees it is done. Refused while anything awaits their confirmation."),
    "input_schema": {"type": "object", "properties": {}, "required": []},
}


# ---------------------------------------------------------------------------
# One turn
# ---------------------------------------------------------------------------

def trim_history(pairs: list[dict]) -> list[dict]:
    """Keep the most recent turns within HISTORY_CHAR_BUDGET, whole user/assistant pairs."""
    total, kept = 0, []
    for msg in reversed(pairs):
        total += len(str(msg.get("content") or ""))
        if total > HISTORY_CHAR_BUDGET:
            break
        kept.append(msg)
    kept.reverse()
    if kept and kept[0].get("role") == "assistant":
        kept = kept[1:]     # never open on a half pair
    return kept


def run_turn(persona: str, user_input: str, history: list[dict], proactive: bool = False) -> str:
    """
    One interviewer turn. The reply has passed `filter_output()` (inside run_session — the
    interviewer is a user-facing agent) and `enforce_pending_receipt()` (here), so neither a
    leak nor a false "recorded" reaches her.
    """
    from core.orchestrator import (_pending_raised_since, _pending_tokens,
                                   enforce_pending_receipt, run_session)
    from tools import capture
    before = _pending_tokens(persona)
    # Capture fidelity: the extractor runs beside the interviewer; what this turn wrote is the
    # before/after diff of the record, because run_session's trace is gone when it returns
    # (plan review 2). Misses reach the NEXT turn's coverage block, shown once.
    # The app's opening words are not the user's; the mode is the interviewer's own
    # (config/modules/capture.yaml `modes`), on or shadow.
    live = capture.mode(AGENT) != "off" and not proactive
    shown = capture.take_for_interview(persona) if live else []
    snap = capture.snapshot(persona) if live else None
    job = capture.start(persona, user_input, history, AGENT) if live else None
    message = (f"{coverage_block(persona, capture.coverage_lines(shown))}"
               f"\n\n---\n\n{user_input}")
    reply = run_session(AGENT, message, persona=persona, history=list(trim_history(history)))
    reply = enforce_pending_receipt(reply, _pending_raised_since(before, persona))
    if snap is not None:
        capture.after_interview_turn(persona, job, snap, capture.snapshot(persona), shown)
    count_turn(persona)
    return reply
