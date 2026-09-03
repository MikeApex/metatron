"""
tests/test_intake_queue_empty.py — an empty intake queue is never reported as an
empty inbox ([DB-0902-02]).

On 2026-08-30 two inbox jobs disagreed about the same inbox inside one minute:

- **14:45:03**, the pipeline job (*"summarize any relevant logistics details"*): the
  `logistics` agent called `read_intake_queue("logistics")`, got
  `{"count": 0, "items": "(nothing new for this domain)"}`, and the user was told
  **"I've checked the inbox, and there are no new messages."**
- **14:45:29**, the direct job: the same agent called `read_email` instead and found ten
  unread — a dental reminder, a ticket booking and a GCP budget alert.

The queue was not drained, it was never filled. Measured on the live store 2026-09-03:
**24 of 25 intake records carry `domain: null` and `category: "unclear"`**, because the
extractor is off behind [DB-0820-03]'s eval gate, the persona has zero `rules:`, and
`unclear` maps to a null domain. Under that configuration `read_intake_queue` returns
zero for every domain permanently, whatever is in the inbox.

The old return value said none of that, and "nothing new for this domain" reads as "the
inbox is empty". The fix is that the empty answer now carries its own reason, computed
from config and the store.

Note what is NOT claimed here: this is not the cause of [DB-0822-09]'s failed surfacing.
On 2026-09-02 both the 11:36 pipeline run and the 11:37 direct run called `read_email`
with the same arguments, so they read the same source — that miss is downstream, in the
Synthesizer, and is a separate (Red) fix.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python3 tests/test_intake_queue_empty.py

Exits 0 if every check passes, 1 otherwise.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.intake as INTAKE  # noqa: E402

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


# The live store's shape on 2026-09-03: 24 unrouted, one classified.
_LIVE_RECORDS = ([{"domain": None, "category": "unclear", "seen_at": "2026-08-29T13:54:57"}] * 24
                 + [{"domain": "recreation", "category": "promotion",
                     "seen_at": "2026-08-29T13:54:57"}])


# ---------------------------------------------------------------------------

@check("the empty answer says the inbox was not what was checked")
def _():
    note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "NOT about the user's inbox" in note, note
    assert "does not mean there are no new messages" in note, note


@check("it names read_email as the thing to call instead")
def _():
    note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "read_email" in note, note


@check("it forbids the sentence the user actually heard on 2026-08-30")
def _():
    note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "Do not tell the user their inbox is empty" in note, note


@check("it counts the 24 records that carry no domain")
def _():
    note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "24 ingested message(s) currently carry no domain" in note, note


@check("it reports the extractor being off, which is why the queue cannot fill")
def _():
    # Needs a persona: the config half is per-persona, unlike the record count.
    from core.persona import persona_scope
    with persona_scope("mike"):
        note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "extractor is disabled" in note, note


@check("a config it cannot read produces no config claim, rather than a guessed one")
def _():
    # Outside a persona scope load_config() raises. The note must still be produced and
    # must NOT assert that the extractor is disabled — that would be this function
    # inventing the explanation it exists to supply.
    note = INTAKE._empty_queue("logistics", _LIVE_RECORDS)["note"]
    assert "extractor is disabled" not in note, note
    assert "sweep is switched off" not in note, note
    assert "NOT about the user's inbox" in note, note
    # The record count is gathered independently and survives the config failure.
    assert "24 ingested message(s)" in note, note


@check("count and items are unchanged — only the explanation is new")
def _():
    out = INTAKE._empty_queue("logistics", _LIVE_RECORDS)
    assert out["count"] == 0
    assert out["items"] == "(nothing new for this domain)"


@check("an unreadable store still yields a queue answer, never an exception")
def _():
    # A queue read must not fail because its own explanation could not be computed.
    class _Boom(list):
        def __iter__(self):
            raise OSError("store unreadable")
    out = INTAKE._empty_queue("logistics", _Boom())
    assert out["count"] == 0
    assert "NOT about the user's inbox" in out["note"]


@check("a non-empty queue is untouched by this path")
def _():
    import inspect
    src = inspect.getsource(INTAKE.read_intake_queue)
    assert "_empty_queue(domain, records)" in src, src
    assert "if not rows:" in src, "the explanation must apply only to the empty case"


@check("the append-only store is read once per call, not twice")
def _():
    import inspect
    src = inspect.getsource(INTAKE.read_intake_queue)
    assert src.count("read_records()") == 1, (
        "records.jsonl is append-only forever — a second full read per call is a cost "
        "that only grows:\n" + src)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    sys.exit(1 if failed else 0)
