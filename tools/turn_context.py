"""
tools/turn_context.py — what this turn is, for code that has to tell an event from an echo.

[DB-0827-01] A declined action must not come back except on a genuinely new trigger. The
hard part is not recording the decline — tools/confirm.py already does — it is that at the
moment a tool proposes an action, nothing in scope can tell whether the proposal came from
the user asking for it or from the model re-reading the same carried context that produced
it the first time. Both look identical inside the tool.

So the turn states its own provenance. The orchestrator opens a turn at the top of each
session with whether it carries real user speech, and `new_trigger_since()` answers the only
question the guard needs: has anything happened since the user said no?

Thread-local, on core/persona.py's reasoning: sessions run on a pooled executor thread and
specialists fan out across further threads, so a process-global lets concurrent requests read
each other's turn. It is propagated into the fan-out workers the same way the trace context
is — an explicit `adopt()` at the top of the worker, beside `_tr.set_trace()`.

FAIL CLOSED. A thread with no turn bound answers "no new trigger", so an unbound path
suppresses a re-proposal rather than allowing one. The cost of suppressing wrongly is the
user saying it a second time; the cost of allowing wrongly is the loop this exists to end,
whose only exit was approving the thing you had just refused.
"""

from __future__ import annotations

import threading
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Iterator

_state = threading.local()


@contextmanager
def turn_scope(user_turn: bool, started_at: float | None = None) -> Iterator[dict]:
    """
    Bind this turn for the duration of the block, on this thread.

    `user_turn`: did the user actually say something — core/orchestrator.py's
    has_real_user_turn(), which is already decisive about a scheduled session's opening text
    being the system talking to itself rather than speech.
    """
    turn = {"user_turn": bool(user_turn),
            "started_at": float(started_at if started_at is not None else time.time())}
    previous = getattr(_state, "turn", None)
    _state.turn = turn
    try:
        yield turn
    finally:
        _state.turn = previous


def current() -> dict | None:
    """This thread's turn, or None if nothing bound one."""
    return getattr(_state, "turn", None)


def adopt(turn: dict | None) -> None:
    """
    Bind a parent turn's state on this thread — for a worker thread, which has no turn of
    its own. Mirrors `_tr.set_trace()` at the same call sites; a context manager would not
    fit, because the worker body is a plain function.
    """
    _state.turn = turn


def _newer_intake_row(since: float, persona: str | None = None) -> bool:
    """
    Did anything arrive in the intake queue after `since`?

    The other half of "genuinely new": mail and calendar reach the system through intake,
    and its rows carry `seen_at`, so an item that landed after the decline is an external
    event rather than the model re-reading its own context. Never raises — intake being
    off, absent or unreadable means no new trigger, which is the fail-closed direction.
    """
    try:
        from tools.intake import read_records
        for row in read_records(persona=persona) or []:
            seen = row.get("seen_at")
            if not seen:
                continue
            try:
                if datetime.fromisoformat(str(seen)).timestamp() > since:
                    return True
            except (TypeError, ValueError):
                continue
    except Exception:  # noqa: BLE001
        return False
    return False


def new_trigger_since(when: float, persona: str | None = None) -> bool:
    """
    Has a genuinely new trigger occurred since `when`?

    True on either of two things, and nothing else:

      * the user spoke, in a turn that started after `when` — a person asking again is the
        strongest new trigger there is, and the one that must never be blocked;
      * an intake row arrived after `when` — a new message or event, i.e. the world
        changed rather than the context being re-read.

    A scheduled run with no new external item is neither, which is exactly the case this
    is for: carried context cannot resurrect a refused proposal on its own.
    """
    turn = current()
    if turn is None:
        return False  # fail closed — see the module docstring
    if turn["user_turn"] and turn["started_at"] >= when:
        return True
    return _newer_intake_row(when, persona)
