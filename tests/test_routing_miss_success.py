"""
tests/test_routing_miss_success.py — a ROUTING_MISS never records a success
([DB-0902-01]).

From 2026-06-22 to 2026-08-29 every ROUTING_MISS in the live log was a real routing
fault, and several became work: the referent-resolution build of [DB-0826-01] started
as one of them. From 2026-09-01 the same event type began carrying *"Coordinator
handled morning session prompt successfully."* and *"Routed inbox check and logistics
task appropriately."* — the miss log filling with non-misses, so the one signal that
finds routing faults stops being readable.

Measured on the live log 2026-09-03 (34 events): 19 before 09-01 of which 0 are noise,
15 from 09-01 on of which 13 are. The break is exactly the fleet migration to
gemini-3.7-flash, with no code change in between — so the remaining half is an
instruction gap in `config/agents/coordinator.md`, which never defines ROUTING_MISS at
all. That half is Red and is not fixed here.

**The corpus below is the real one**, verbatim from
`data/personas/mike/logs/quality_events.json`, because the guard's whole justification
is its measured precision. The binding assertion is the first one: **no genuine miss is
ever rejected.** Dropping a noise event costs nothing; dropping a real routing fault
costs the signal this event type exists to carry.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_routing_miss_success.py

Exits 0 if every check passes, 1 otherwise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.logger import asserts_routing_success  # noqa: E402

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


# --- The live corpus, verbatim ----------------------------------------------

# Real routing faults. Every one of these must survive the guard.
GENUINE = [
    "Mike's last message did not come through in the previous session — this is a "
    "recurring issue (two sessions now). Message content is unknown and cannot be replied to.",
    "Both Physical Health and Mental Wellbeing agents returned file-not-found errors. "
    "Coordinator routing package used space-separated agent names (\"Physical Health\", "
    "\"Mental Wellbeing\") rather than underscore-separated filenames (physical_health, "
    "mental_wellbeing). Agents not called successfully — Synthesizer responded from "
    "context alone.",
    "Previous user message received no response and an expected write_config call was "
    "not executed — pipeline/execution failure in last exchange.",
    "Coordinator attempted to route to 'research' instead of 'research_agent', and "
    "'research_agent' itself returned no data.",
    "Coordinator called 'research' instead of 'research_agent', causing subagent failure.",
    "Coordinator processed the user's previous message rather than their current one.",
    "Logistics missed the meeting time (4pm) and location (Google Meet) from the active "
    "thread context, prompting the user for details they already provided.",
    "Coordinator missed that the user message was a system instruction about check-in "
    "formatting, instead resolving intent as a literal request for a check-in.",
    "Coordinator misunderstood 'previous request' as the Iva lunch instead of the "
    "immediate prior turn asking for Transport, Weather, and Pollen research.",
    "Logistics received scheduling directives but only returned a log write confirmation "
    "instead of taking the calendar actions.",
    "Relationships agent failed to send an email to the explicitly provided address "
    "because it attempted a CRM lookup for the user.",
    "Coordinator misidentified the missing email as the old Prudential email, missing "
    "that the user was asking about the Kathaleen test email they approved moments prior.",
    "The system failed to route the user's explicit request to check the inbox to the "
    "logistics agent in the previous turn.",
    "Coordinator interpreted 'Approved' as referring to the credit card payment and "
    "Prudential call, but the user was approving the test email to Kathleen from the "
    "previous turn.",
    "Coordinator misinterpreted phonetic Bulgarian speech-to-text bug report as a "
    "psychological pivot to rest.",
    "Coordinator interpreted 'Read that back to me again' as a request about Prudential "
    "scheduling, but it was a direct request to repeat the food profile data.",
    "Coordinator routed \"Undo that merge\" to work_vocation thinking it referred to the "
    "Prudential/Apex project, completely missing the conversational context.",
    "Coordinator routed user's query about 'who is the appointment for' to past health "
    "logs (Aug 26) instead of checking the recent Sept 15 dental email.",
    "Coordinator misinterpreted a contact name correction ('set it back to Iva') as an "
    "instruction to resend a previously declined email.",
    # The two genuine ones from AFTER the migration — the guard must not treat the whole
    # post-09-01 period as noise.
    "Coordinator attempted output without valid structured format or handled an empty "
    "scheduled check-in trigger incorrectly.",
    "Morning brief triggered but Coordinator produced no specialist calls; morning briefs "
    "require whole-person sessions (Mental Wellbeing and Physical Health).",
]

# The noise, verbatim. Each asserts the routing worked.
NOISE_CAUGHT = [
    "Morning check-in routine handled scheduled session prompt correctly without routing miss",
    "Coordinator handled morning session prompt successfully.",
    "Routed inbox check and logistics task appropriately.",
    "Day-close session initialization triggered by scheduler; routing to Mental Wellbeing, "
    "Physical Health, and Diarist as required by cross-domain routing rules for day-close "
    "sessions.",
    "Coordinator generated valid structured package for evening check-in session start "
    "without user input",
    "Coordinator output generated successfully for morning check-in schedule directive.",
    "Scheduled proactive logistic session triggered without user input; coordinator "
    "successfully handled anticipatory logistics pass without routing error.",
    "User uploaded a Cheder schedule PDF to add to their schedule. Coordinator routed to "
    "Logistics and Diarist without routing error.",
]

# Noise the guard deliberately does NOT catch: these assert nothing about success, they
# just describe the session. Separating them from a real report needs semantic judgement
# the guard refuses to attempt. Recorded here so the limit is stated rather than
# discovered — this is what the coordinator.md proposal is for.
NOISE_UNCAUGHT = [
    "Coordinator produced context package for user update about evening family time and "
    "fun coding after a busy work day.",
    "Coordinator test run check",
    "Coordinator received a scheduled programmatic morning briefing directive instead of "
    "a direct user message; handled appropriately as an anticipatory logistics pass.",
    "Scheduled session trigger opening a quiet check-in at 5:10 PM on Wednesday Sept 2, "
    "2026. Coordinator routing for quiet evening check-in covering active work deadlines.",
    "Coordinator routing test session for day-close / scheduled trigger without user message",
]


# ---------------------------------------------------------------------------

@check("no genuine routing miss is ever rejected (21 live events)")
def _():
    wrongly = [d for d in GENUINE if asserts_routing_success(d)]
    assert not wrongly, (
        f"{len(wrongly)} real routing fault(s) would be refused, which costs the signal "
        f"this event type exists to carry:\n" + "\n".join(f"  - {d[:120]}" for d in wrongly))


@check("'agents not called successfully' is a failure report, not a success claim")
def _():
    # The 2026-06-26 event. A naive keyword rule rejects this on the word "successfully"
    # and loses a real miss — negation handling is the whole reason the guard is shaped
    # the way it is.
    assert not asserts_routing_success(GENUINE[1])


@check("the eight self-contradicting noise events are refused")
def _():
    kept = [d for d in NOISE_CAUGHT if not asserts_routing_success(d)]
    assert not kept, "noise no longer caught:\n" + "\n".join(f"  - {d[:120]}" for d in kept)


@check("measured precision on the live corpus is stated, not assumed")
def _():
    caught = sum(1 for d in NOISE_CAUGHT + NOISE_UNCAUGHT if asserts_routing_success(d))
    rejected_genuine = sum(1 for d in GENUINE if asserts_routing_success(d))
    assert rejected_genuine == 0, rejected_genuine
    assert caught == 8, f"expected 8 of 13 noise events caught, got {caught}"


@check("a detail that claims success AND names a failure is kept — ambiguity keeps the event")
def _():
    assert not asserts_routing_success(
        "Coordinator handled the morning prompt successfully but missed the dental email.")


@check("write_quality_event refuses a ROUTING_MISS that reports a success")
def _():
    from tools.logger import write_quality_event
    try:
        write_quality_event(event_type="ROUTING_MISS", source_agent="coordinator",
                            detail="Coordinator handled morning session prompt successfully.")
    except ValueError as e:
        assert "describes routing that WORKED" in str(e), str(e)
    else:
        raise AssertionError("the noise event was accepted")


@check("the guard applies only to ROUTING_MISS, not to every event type")
def _():
    # A USER_CORRECTION saying the user confirmed something worked is a real event.
    assert asserts_routing_success("Handled correctly."), "precondition"
    from tools.logger import write_quality_event
    import inspect
    src = inspect.getsource(write_quality_event)
    assert 'event_type == "ROUTING_MISS"' in src, (
        "the guard is not scoped to ROUTING_MISS — it would eat other event types")


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
