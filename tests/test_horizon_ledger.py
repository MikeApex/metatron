"""
tests/test_horizon_ledger.py — a horizon finding reaches the user once, and only once
([DB-0822-09]).

On 2026-09-02 `logistics` judged a Death Cab for Cutie ticket confirmation worth Mike's
attention, attached the coordination legs, and emitted it as HORIZON_ITEMS in a 536-token
package. The Synthesizer received 21,630 input tokens including that package and replied
with 177 words about something else. The item never reached him.

The fix delivers such findings structurally — which is only safe because of the ledger this
file tests. The three runs where specialist output survives in the traces:

    08-29 10:31   dental · Jimmy Carr · George School socials
    08-30 20:46   dental · Jimmy Carr
    09-02 11:37   Jimmy Carr · Death Cab · George School London

Jimmy Carr in all three. **Guaranteed delivery without the ledger would have told Mike about
the same comedy show every day until 13 September** — the [DB-0822-06] carried-state failure
through a new channel, and strictly worse than the silent drop it replaces. So the binding
assertion here is the dedupe across the *real* prose variants, which share no title string.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_horizon_ledger.py

Exits 0 if every check passes, 1 otherwise.
"""

import json
import shutil
import sys
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.horizon as H  # noqa: E402

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


# --- isolate the ledger from any real persona -------------------------------

_TMP = Path(tempfile.mkdtemp(prefix="horizon-test-"))
_LEDGER = _TMP / "ledger.json"
H._store_path = lambda persona=None: _LEDGER          # noqa: E305
H.resolve_persona = lambda persona=None: "test"       # noqa: E305


def reset():
    if _LEDGER.exists():
        _LEDGER.unlink()


def ledger() -> dict:
    return json.loads(_LEDGER.read_text()) if _LEDGER.exists() else {}


FUTURE = (date.today() + timedelta(days=20)).isoformat()
LATER = (date.today() + timedelta(days=40)).isoformat()

# Near enough that `_due_now` serves it — see NEAR_BY below.
NEAR_BY = (date.today() + timedelta(days=1)).isoformat()

# Both fixtures carry a near `precursor_by`, and that is deliberate. Since 2026-09-05 a
# finding more than `_NEAR_DAYS` out is HELD unless it is a deadline or has a precursor
# falling now (`_due_now`), so a bare far-dated event no longer reaches `context_block()` at
# all. These fixtures exist to exercise the LEDGER — dedupe, offers, discharge — which needs
# an item that actually serves. The gate itself is tested separately below, on bare items.
# `precursor_by` is not part of `item_key`, so identity and dedupe are unaffected by it.
DEATH_CAB = {"title": "Death Cab for Cutie at Troxy", "date": FUTURE,
             "venue": "Troxy, London", "kind": "event",
             "detail": "Mobile tickets confirmed via Ticketmaster",
             "precursor": "book return travel", "precursor_by": NEAR_BY}

# The same Jimmy Carr show as written by two different runs. No title string in common.
CARR_0829 = {"title": "Jimmy Carr Performance", "date": LATER,
             "venue": "The London Palladium", "kind": "event",
             "detail": "September 13th at 9:30 PM",
             "precursor": "book return travel", "precursor_by": NEAR_BY}
CARR_0902 = {"title": "Jimmy Carr: Laughs Funny", "date": LATER,
             "venue": "the london palladium, London", "kind": "event",
             "detail": "Tickets booked, reference 26224N-69S3AH8RKL",
             "precursor": "book return travel", "precursor_by": NEAR_BY}


# ---------------------------------------------------------------------------

@check("the real Jimmy Carr prose variants resolve to one finding")
def _():
    assert H.item_key(CARR_0829) == H.item_key(CARR_0902), (
        f"{H.item_key(CARR_0829)!r} != {H.item_key(CARR_0902)!r} — the same show would be "
        f"raised twice")


@check("filing the same show from three runs leaves one ledger entry")
def _():
    reset()
    assert H.record([CARR_0829])["new"] == 1
    assert H.record([CARR_0829])["new"] == 0
    assert H.record([CARR_0902])["new"] == 0
    assert len(ledger()) == 1, ledger()


@check("a re-file refreshes the wording but never the offer count")
def _():
    reset()
    H.record([CARR_0829])
    H.context_block()                      # charges one offer
    before = list(ledger().values())[0]
    assert before["offers"] == 1, before
    H.record([CARR_0902])                  # richer wording arrives on a later run
    after = list(ledger().values())[0]
    assert after["offers"] == 1, "re-filing reset the offer count"
    assert "26224N" in after["item"]["detail"], "the later, fuller wording was not kept"


@check("different events stay distinct")
def _():
    reset()
    H.record([DEATH_CAB, CARR_0829])
    assert len(ledger()) == 2, ledger()


@check("an undelivered finding appears in the block, with its detail")
def _():
    reset()
    H.record([DEATH_CAB])
    block = H.context_block()
    assert "Death Cab" in block, block
    assert "Troxy" in block, block
    assert "Ticketmaster" in block, block


@check("the block tells the model to place it, not to decide whether")
def _():
    reset()
    H.record([DEATH_CAB])
    block = H.context_block()
    assert "do not judge whether to mention them" in block, block
    assert "NOT yet been told" in block, block


def _age_offer_stamp():
    """Push every last-offer stamp outside the window, so the next block counts a new
    session. Cheaper and more deterministic than sleeping through _OFFER_WINDOW_SECONDS."""
    data = ledger()
    for row in data.values():
        row["last_offered_at"] = (datetime.now() - timedelta(hours=1)).isoformat(
            timespec="seconds")
    _LEDGER.write_text(json.dumps(data))


@check("nothing waiting costs nothing — no block, no tokens")
def _():
    reset()
    assert H.context_block() == "", "an empty ledger produced a block"


@check("a finding is written off after _MAX_OFFERS sessions, not carried forever")
def _():
    reset()
    H.record([DEATH_CAB])
    for _ in range(H._MAX_OFFERS):
        assert "Death Cab" in H.context_block()
        _age_offer_stamp()
    assert H.context_block() == "", (
        f"still offered after {H._MAX_OFFERS} sessions — this is the groundhog-day failure")


@check("the two head-layer reads of one session count as ONE offer")
def _():
    reset()
    H.record([DEATH_CAB])
    H.context_block()          # coordinator
    H.context_block()          # synthesizer, same exchange
    assert list(ledger().values())[0]["offers"] == 1, ledger()


@check("a second session counts a second offer, and then it stops being shown")
def _():
    reset()
    H.record([DEATH_CAB])
    H.context_block()
    _age_offer_stamp()
    assert "Death Cab" in H.context_block(), "dropped after only one offer"
    assert list(ledger().values())[0]["offers"] == 2
    _age_offer_stamp()
    assert H.context_block() == "", "a finding is being pressed a third time"


@check("the user engaging with a finding discharges it immediately")
def _():
    reset()
    H.record([DEATH_CAB])
    assert H.mark_engaged("tell me more about the Death Cab gig at Troxy") == 1
    assert list(ledger().values())[0]["delivered_at"]
    assert H.context_block() == "", "a discharged finding is still being offered"


@check("an unrelated user turn discharges nothing")
def _():
    reset()
    H.record([DEATH_CAB])
    assert H.mark_engaged("what's on my calendar tomorrow") == 0
    assert "Death Cab" in H.context_block()


@check("system text can never discharge a finding — no user words, no discharge")
def _():
    reset()
    H.record([DEATH_CAB])
    assert H.mark_engaged(None) == 0
    assert H.mark_engaged("") == 0
    assert "Death Cab" in H.context_block()


@check("a finding whose date has passed is dropped, never delivered late")
def _():
    reset()
    past = {"title": "Old gig", "date": (date.today() - timedelta(days=3)).isoformat(),
            "venue": "Somewhere", "kind": "event", "detail": "over"}
    H.record([past])
    assert H.context_block() == "", "a past event was offered to the user"


@check("a malformed item is rejected, not repaired into an invented date")
def _():
    reset()
    tally = H.record([
        {"title": "No date given", "date": "next Tuesday", "venue": "X"},   # unparseable
        {"date": FUTURE, "venue": "X"},                                     # no title
        "not a dict",
        {"title": "", "date": FUTURE},                                      # empty title
    ])
    assert tally["invalid"] == 4, tally
    assert ledger() == {}, ledger()


@check("an undated finding is still keyed and still delivered")
def _():
    reset()
    H.record([{"title": "Renew passport", "date": "", "venue": "",
               "kind": "deadline", "detail": "photos needed"}])
    assert "Renew passport" in H.context_block()


@check("soonest first — this week outranks October")
def _():
    reset()
    H.record([CARR_0829, DEATH_CAB])       # LATER, then FUTURE
    block = H.context_block()
    assert block.index("Death Cab") < block.index("Jimmy Carr"), block


@check("an unreadable ledger degrades to silence, never an exception")
def _():
    reset()
    _LEDGER.write_text("{ this is not json")
    assert H.context_block() == ""
    assert H.record([DEATH_CAB])["new"] == 1


# --- the tool, which is how findings actually arrive ------------------------

@check("the tool files a finding and says it is new")
def _():
    reset()
    out = H.record_horizon_item(title="Death Cab for Cutie at Troxy", date=FUTURE,
                                venue="Troxy, London", kind="event",
                                detail="Mobile tickets confirmed",
                                precursor="book return travel", precursor_by=NEAR_BY)
    assert "Filed" in out, out
    assert "not been told" in out, out
    assert "Death Cab" in H.context_block()


@check("filing the same finding twice says so, and does not duplicate it")
def _():
    reset()
    H.record_horizon_item(title="Jimmy Carr Performance", date=LATER,
                          venue="The London Palladium")
    out = H.record_horizon_item(title="Jimmy Carr: Laughs Funny", date=LATER,
                                venue="the london palladium, London")
    assert "Already on file" in out, out
    assert len(ledger()) == 1, ledger()


@check("a bad date is refused with a correction, never guessed at")
def _():
    reset()
    out = H.record_horizon_item(title="Something", date="next Tuesday")
    assert "Not filed" in out, out
    assert "YYYY-MM-DD" in out, out
    assert ledger() == {}, "an unparseable date reached the ledger"


@check("a past date is refused, and is not reported as an error")
def _():
    reset()
    gone = (date.today() - timedelta(days=2)).isoformat()
    out = H.record_horizon_item(title="Last week's gig", date=gone, venue="Troxy")
    assert "already passed" in out, out
    assert "not an error" in out, out


@check("title is the only required argument — an undated finding still files")
def _():
    reset()
    assert "Filed" in H.record_horizon_item(title="Renew passport")
    assert "Renew passport" in H.context_block()


@check("the schema tells the specialist NOT to pre-filter on what was already raised")
def _():
    # The whole hazard: an agent that skips a familiar-feeling item removes the only
    # chance the ledger has to decide. logistics.md says this too; the schema must, since
    # it is what the model sees at the moment of the call.
    desc = H.RECORD_HORIZON_ITEM_SCHEMA["description"]
    assert "never skip an item" in desc, desc
    assert "exactly once" in desc, desc


@check("the tool is registered, granted to logistics, and named in its agent file")
def _():
    orch = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    assert '"record_horizon_item": record_horizon_item,' in orch, "not in the handlers dict"
    assert "RECORD_HORIZON_ITEM_SCHEMA," in orch, "schema not registered"
    for routing in ("routing.yaml", "routing_cloud.yaml"):
        text = (ROOT / "config" / "modules" / routing).read_text(encoding="utf-8")
        logistics = [ln for ln in text.splitlines()
                     if "allowed_tools:" in ln and "get_regional_transit_info" in ln]
        assert logistics, f"{routing}: could not find the logistics grant line"
        assert "record_horizon_item" in logistics[0], f"{routing}: not granted to logistics"
    agent = (ROOT / "config" / "agents" / "logistics.md").read_text(encoding="utf-8")
    assert "record_horizon_item" in agent, (
        "granted but not named in logistics.md — a tool the agent is never told to call")


# --- pipeline wiring --------------------------------------------------------

@check("the real 09-02 output is parsed and stripped from what Synth reads")
def _():
    reset()
    import core.orchestrator as O
    out = {"logistics": (
        "ACTIONS TAKEN:\n  - Checked the inbox.\n\n"
        'HORIZON_ITEMS: [{"title": "Death Cab for Cutie", "date": "' + FUTURE + '", '
        '"venue": "Troxy, London", "kind": "event", "detail": "Mobile tickets confirmed"}]'
        "\n\nFLAGS:\n  - none")}
    cleaned = O._file_horizon_items(out, persona="test")
    assert "HORIZON_ITEMS" not in cleaned["logistics"], (
        "left in the specialist prose — the Synthesizer would see every finding twice, "
        "including the ones the ledger suppressed:\n" + cleaned["logistics"])
    assert "Checked the inbox" in cleaned["logistics"], "the rest of the output was lost"
    # The ledger, not the block: this real 09-02 item is a bare far-dated event, so `_due_now`
    # correctly holds it back from delivery. What this test is about is that it was PARSED and
    # FILED — holding is the gate's job and is asserted on its own below.
    assert any("Death Cab" in r["item"]["title"] for r in ledger().values()), ledger()


@check("a fenced HORIZON_ITEMS block parses too")
def _():
    reset()
    import core.orchestrator as O
    out = {"logistics": 'HORIZON_ITEMS: ```json\n[{"title": "Gig", "date": "' + FUTURE +
           '", "venue": "Troxy"}]\n```'}
    O._file_horizon_items(out, persona="test")
    assert any("Gig" in r["item"]["title"] for r in ledger().values()), ledger()


@check("prose HORIZON_ITEMS are logged and dropped, never crash the turn")
def _():
    reset()
    import core.orchestrator as O
    out = {"logistics": "HORIZON_ITEMS:\n  - Death Cab for Cutie at Troxy, Sept 26"}
    cleaned = O._file_horizon_items(out, persona="test")   # must not raise
    assert isinstance(cleaned["logistics"], str)
    assert H.context_block() == "", "unparseable prose was filed as a finding"


@check("the block is built after the sign-off veto, at BOTH pipeline sites")
def _():
    # Building it before the veto charges an offer on a turn where the Synthesizer never
    # runs — the finding would burn a chance on a reply the user never got.
    # Sliced from the file rather than inspect.getsource, which truncates the streaming
    # generator at 30 of its ~200 lines and silently reports the wiring as absent.
    text = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    # The streaming path's body lives in `_run_pipeline_session_stream_inner`;
    # `run_pipeline_session_stream` is a thin wrapper around it.
    for name in ("run_pipeline_session", "_run_pipeline_session_stream_inner"):
        body = text.split(f"\ndef {name}(", 1)[1].split("\ndef ", 1)[0]
        assert "_horizon_block(persona, session=kind)" in body, (
            f"{name} never builds the block — or builds it without the session kind, which "
            f"is what switches on the evening review")
        assert body.index("_signoff_skip(") < body.index("_horizon_block(persona"), (
            f"{name} builds the horizon block before the sign-off veto — a finding would "
            f"be charged an offer on a turn where the Synthesizer never runs")
        assert "horizon_text" in body.split("synthesizer_input = ")[1][:600], (
            f"{name} builds the block but never passes it to the Synthesizer")


# ---------------------------------------------------------------------------
# The proximity gate (2026-09-05). Mike: "you're looking ahead too far in the future...
# only items with precursors, deadlines, or other reasons get highlighted deeply in
# advance." Before this, `context_block()` served everything undelivered at any distance
# and told the Synthesizer not to judge whether to mention it.
# ---------------------------------------------------------------------------

TOMORROW = (date.today() + timedelta(days=1)).isoformat()

def _bare(when: str, kind: str = "event", **extra) -> dict:
    """A finding with nothing to make it urgent — no precursor, plain kind."""
    return {"title": f"Thing on {when}", "date": when, "venue": f"Venue {when}",
            "kind": kind, "detail": "d", **extra}


@check("gate: today and tomorrow speak for themselves")
def _():
    reset()
    H.record([_bare(date.today().isoformat()), _bare(TOMORROW)])
    block = H.context_block()
    assert date.today().isoformat() in block, block
    assert TOMORROW in block, block


@check("gate: a distant event with nothing to do about it waits")
def _():
    reset()
    H.record([_bare(FUTURE)])
    assert H.context_block() == "", "a far-off event with no precursor was pushed anyway"


@check("gate: a deadline carries at any distance")
def _():
    reset()
    H.record([_bare(LATER, kind="deadline")])
    assert LATER in H.context_block(), "a deadline was held back"


@check("gate: a distant thing whose precursor falls now is raised now")
def _():
    reset()
    H.record([_bare(FUTURE, precursor="post the packet", precursor_by=TOMORROW)])
    assert FUTURE in H.context_block(), (
        "the mover's-claim shape — deadline weeks out, the action due tomorrow — was held")


@check("gate: a precursor still far off does not pull the item forward")
def _():
    reset()
    H.record([_bare(LATER, precursor="book travel", precursor_by=FUTURE)])
    assert H.context_block() == "", "a precursor 20 days out surfaced the item today"


@check("gate: an undated finding is never held — there is nothing to measure")
def _():
    reset()
    H.record([{"title": "Undated thing", "date": "", "venue": "", "kind": "event",
               "detail": "d"}])
    assert "Undated thing" in H.context_block()


@check("gate: a held finding keeps its offers — quieter, never lossier")
def _():
    reset()
    H.record([_bare(FUTURE)])
    for _ in range(H._MAX_OFFERS + 2):
        H.context_block()
        _age_offer_stamp()
    assert list(ledger().values())[0]["offers"] == 0, (
        "a finding was charged for an offer the user never saw — it would be written off "
        "before it ever came near enough to be said")


@check("gate: a bad precursor_by is refused at filing, not guessed at")
def _():
    reset()
    out = H.record_horizon_item(title="X", date=FUTURE, venue="V",
                                precursor="do a thing", precursor_by="next Tuesday")
    assert "Not filed" in out, out
    assert ledger() == {}, ledger()


# ---------------------------------------------------------------------------
# The evening review (2026-09-05). Mike: "Daily wrap up should run through all of
# tomorrow's events whether previously stated or not. It's a review."
# ---------------------------------------------------------------------------

@check("review: tomorrow is read out even after it has already been delivered")
def _():
    reset()
    H.record([_bare(TOMORROW)])
    assert H.mark_engaged("tell me about the thing on " + TOMORROW) == 1
    assert H.context_block() == "", "precondition: it should be discharged for normal turns"
    assert TOMORROW in H.review_block(), (
        "the evening review skipped an item the user had already heard — that is exactly "
        "the half a review must not drop")


@check("review: reading tomorrow out charges nothing and delivers nothing")
def _():
    reset()
    H.record([_bare(TOMORROW)])
    before = json.dumps(ledger(), sort_keys=True)
    H.review_block()
    H.review_block()
    assert json.dumps(ledger(), sort_keys=True) == before, (
        "the review wrote to the ledger — it must be read-only, or it would consume the "
        "finding's chance to be raised properly")


@check("review: stops at tomorrow — today and the rest of the week are not its job")
def _():
    reset()
    H.record([_bare(date.today().isoformat()), _bare(TOMORROW), _bare(FUTURE)])
    block = H.review_block()
    assert TOMORROW in block, block
    assert FUTURE not in block, "the review reached into next month"
    assert date.today().isoformat() not in block, "the review re-ran today"


@check("review: an empty tomorrow costs nothing")
def _():
    reset()
    H.record([_bare(FUTURE)])
    assert H.review_block() == ""


@check("review: fires on evening_close only, and never on an ordinary turn")
def _():
    text = (ROOT / "core" / "orchestrator.py").read_text(encoding="utf-8")
    body = text.split("\ndef _horizon_block(", 1)[1].split("\ndef ", 1)[0]
    assert 'session == "evening_close"' in body, (
        "the review is not gated on the evening session — it would repeat delivered "
        "findings on every turn, which is the groundhog-day failure this module exists "
        "to prevent")
    assert "review_block" in body


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    shutil.rmtree(_TMP, ignore_errors=True)
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
