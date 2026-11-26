"""
tests/test_routing_miss_scheduled.py — a ROUTING_MISS on a scheduler-opened turn is refused
when it only remarks that the session was scheduled ([DB-0902-01], second half).

Live 2026-11-26: ~25 of 56 ROUTING_MISS events since 10-29 were the Coordinator describing a
scheduled session as if it were a fault. The binding assertion: no genuine miss is refused,
including genuine misses on a proactive turn. Corpus paraphrased from the live machine log with
generic names; the guard applies only on a no-user-words turn.

Usage: python3 tests/test_routing_miss_scheduled.py
"""

import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.logger as logger  # noqa: E402
from tools.logger import describes_scheduled_session, write_quality_event  # noqa: E402
from core.trace import start_request_trace  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


NOISE = [
    "User message was a scheduled quiet check-in",
    "Scheduled session prompt processed without user input",
    "The scheduled anticipatory logistics pass was treated as a user message and routed to "
    "specialists instead of being handled as a system prompt directive.",
    "Automated scheduled session triggered; no user message present",
    "Coordinator agent skipped routing package production during a scheduled silent check-in "
    "session",
    "Coordinator received a scheduled day-close session prompt ('How did today go?'), but "
    "Coordinator was not instructed on how to handle it.",
    "The user did not send a new message; this was a scheduled prompt for a quiet check-in. "
    "The system routed it incorrectly as a user input.",
    "Scheduled job to check inbox arrived as user input instead of background trigger",
    "User prompt was a system instruction for a scheduled morning brief, not a user message.",
    "Quiet check-in processed as a scheduled background pass with no user message; routing "
    "handled via standard context check.",
    "System prompt requested routing for day-close session with no user utterance present; "
    "coordinator correctly packaged context.",
    "Coordinator output a scheduled greeting instead of respecting the quiet check-in signal.",
    "Scheduled session directive about plant watering arrived as user message, but "
    "coordinator processed it directly as an automated background check.",
    "Scheduled session input received with no user message; handled via evening close sequence.",
]

GENUINE = [  # on a proactive turn or any turn: all must survive
    "Coordinator missed routing the morning greeting session to Mental Wellbeing and Physical "
    "Health as mandated by the cross-domain routing rule for morning briefs.",
    "Morning brief triggered but Coordinator produced no specialist calls; morning briefs "
    "require whole-person sessions.",
    "Coordinator attempted output without valid structured format or handled an empty "
    "scheduled check-in trigger incorrectly.",
    "Coordinator omitted specialist routing for a scheduled morning check-in that required "
    "domain data lookup and task tracking.",
    "Coordinator incorrectly routed a scheduled prompt directly to output instead of "
    "packaging it for the Synthesizer.",
    "Routed the automated morning check-in to Synthesizer without any specialist consultation "
    "despite active conflicting morning schedule items.",
    "Coordinator routed previous message instead of current message.",
    "User asked which goal is next but the Coordinator did not route to any goals specialist.",
    "Coordinator failed to dispatch Physical Health during the scheduled day-close session.",
    "Logistics missed the meeting time from the active thread context.",
]


def _proactive():
    start_request_trace("scheduled prompt", "test", is_proactive=True)


def _user_turn():
    start_request_trace("hello", "test", is_proactive=False)


def _write(detail):
    with tempfile.TemporaryDirectory() as d:
        orig = logger._logs_dir
        logger._logs_dir = lambda: Path(d)
        try:
            # a fresh trace each call, so the same-trace dedup never hides a result
            return write_quality_event("ROUTING_MISS", "coordinator", detail, "t")
        finally:
            logger._logs_dir = orig


def _refused(detail):
    try:
        _write(detail)
    except ValueError:
        return True
    return False


@check("noise phrasings are refused on a proactive trace")
def _():
    kept = []
    for d in NOISE:
        _proactive()
        if not _refused(d):
            kept.append(d)
    print(f"  noise refused on proactive trace: {len(NOISE) - len(kept)} of {len(NOISE)}")
    assert not kept, "accepted:\n" + "\n".join(f"  - {d[:110]}" for d in kept)


@check("genuine misses are accepted on a proactive trace (0 refused)")
def _():
    wrongly = []
    for d in GENUINE:
        _proactive()
        if _refused(d):
            wrongly.append(d)
    print(f"  genuine refused on proactive trace: {len(wrongly)} of {len(GENUINE)}")
    assert not wrongly, "refused:\n" + "\n".join(f"  - {d[:110]}" for d in wrongly)


@check("the same noise phrasings are accepted when the user spoke (guard is proactive-only)")
def _():
    refused = []
    for d in NOISE:
        _user_turn()
        if _refused(d):
            refused.append(d)
    # a user turn can really report a scheduled thing going wrong; do not decide for them
    assert not refused, "refused on a user turn:\n" + "\n".join(refused)


@check("the predicate alone never flags a genuine miss")
def _():
    assert not [d for d in GENUINE if describes_scheduled_session(d)]


if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
