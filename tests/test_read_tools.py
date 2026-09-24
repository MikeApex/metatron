"""
tests/test_read_tools.py — the two read tools the Librarian needs, Build v4.11 phase D.

`search_conversations` (tools/conversations.py) and `read_journal_range`
(tools/diarist.py). Section 12 of the plan gives phase D no row of its own — the
pair is proven through phase B's Doors row once both have landed — so this suite
is what stands behind them until then.

What it asserts, in the order the phase prompt names:

  1. Each tool returns what it claims on a persona WITH data, and an empty
     result rather than an error on one WITHOUT.
  2. The caps hold: a request above the ceiling returns the ceiling, not
     everything — checked on `k`, on `max_entries`, and on the journal window.
  3. A range read spanning dates with no journal entries does not error. Nor
     does a damaged day file, a stray non-dated file, or an unparseable line.
  4. Both are registered: register_tools() returns each in the schema list AND
     in the handler map, and the phase-A presence table's fixed call reaches
     each one without a TypeError.

(4) is the one worth stating plainly. `core/build/manifest.py`'s `_SOURCES`
table specifies both calls — `{"start": "", "end": "", "max_entries": 40}` and
`{"query": "", "k": 20}` — and the read door issues them verbatim. That file's
docstring records what a mismatched argument costs: a TypeError recorded as
`state: error`, which reaches the Librarian as "the code could not read it"
rather than as "there is nothing there". So the probe arguments are asserted
against the real signatures here, not left to be discovered on the VM.

Usage:
    python3 tests/test_read_tools.py
"""

import json
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import tools.conversations as CONV  # noqa: E402
import tools.diarist as DIARIST  # noqa: E402

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


class _temp_persona:
    """
    Redirect both modules' persona root at a throwaway directory.

    Patching the module-level `persona_data_dir` rather than using
    `persona_scope`, for the reason tests/test_degradation_paths.py does the
    same: `persona_data_dir` resolves against the repository root, so a real
    scope would write into the tracked fixture personas — which SESSION.md's
    standing rule names as a way a worktree run dirties tracked files.
    """

    def __enter__(self) -> Path:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self._conv = CONV.persona_data_dir
        self._diarist = DIARIST.persona_data_dir
        CONV.persona_data_dir = lambda persona=None: self.root
        DIARIST.persona_data_dir = lambda persona=None: self.root
        return self.root

    def __exit__(self, *exc) -> None:
        CONV.persona_data_dir = self._conv
        DIARIST.persona_data_dir = self._diarist
        self._tmp.cleanup()


def _turn(day: str, seq: int, user: str, response: str, agent: str = "coordinator",
          proactive: bool = False) -> str:
    return json.dumps({
        "ts": f"{day}T09:{seq:02d}:00.000000",
        "seq": f"{seq:03d}",
        "agent": agent,
        "persona": "fixture",
        "proactive": proactive,
        "user": user,
        "response": response,
    })


def _write_conversations(root: Path, days: dict[str, list[str]]) -> None:
    conv = root / "conversations"
    conv.mkdir(parents=True, exist_ok=True)
    for day, lines in days.items():
        (conv / f"{day}.jsonl").write_text("\n".join(lines) + "\n")


def _write_journal(root: Path, day: str, texts: list[str]) -> None:
    journal = root / "journal"
    journal.mkdir(parents=True, exist_ok=True)
    (journal / f"{day}.json").write_text(json.dumps({
        "date": day,
        "entries": [{"timestamp": f"{day}T20:00:00", "text": t, "tags": []} for t in texts],
    }))


def _days_back(n: int) -> str:
    return (date.today() - timedelta(days=n)).isoformat()


# ---------------------------------------------------------------------------
# 1. search_conversations — what it claims, on a persona with data
# ---------------------------------------------------------------------------

@check("search finds a turn by a term in the user's words")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "did I water the plants?", "Not since Tuesday.")],
            "2026-09-21": [_turn("2026-09-21", 1, "book the dentist", "Booked for Thursday.")],
        })
        out = CONV.search_conversations("water")
        assert out["error"] == "", out["error"]
        assert out["returned"] == 1, out
        assert out["match_count"] == 1, out
        hit = out["matches"][0]
        assert hit["date"] == "2026-09-20", hit
        assert hit["seq"] == "001", hit
        assert hit["agent"] == "coordinator", hit
        assert "water the plants" in hit["user"], hit


@check("search finds a turn by a term in the reply")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "anything today?", "Your dentist is at four.")],
        })
        assert CONV.search_conversations("dentist")["returned"] == 1


@check("every term must appear — an unmatched second term excludes the turn")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "water the plants", "Done.")],
        })
        assert CONV.search_conversations("water plants")["returned"] == 1
        assert CONV.search_conversations("water dentist")["returned"] == 0


@check("matching is case-insensitive and matches inside a longer word")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "Watering the Plants", "Done.")],
        })
        assert CONV.search_conversations("water")["returned"] == 1
        assert CONV.search_conversations("PLANTS")["returned"] == 1


@check("results are newest first, across days and within a day")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "plants a", "x"),
                           _turn("2026-09-20", 2, "plants b", "x")],
            "2026-09-22": [_turn("2026-09-22", 1, "plants c", "x")],
        })
        out = CONV.search_conversations("plants", k=5)
        got = [(m["date"], m["seq"]) for m in out["matches"]]
        assert got == [("2026-09-22", "001"), ("2026-09-20", "002"), ("2026-09-20", "001")], got


@check("an empty query matches every turn — the presence-check call")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "a", "b"), _turn("2026-09-20", 2, "c", "d")],
        })
        out = CONV.search_conversations("", k=20)
        assert out["error"] == "", out["error"]
        assert out["match_count"] == 2, out


@check("since excludes earlier days and is reported back")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-01": [_turn("2026-09-01", 1, "plants", "x")],
            "2026-09-20": [_turn("2026-09-20", 1, "plants", "x")],
        })
        out = CONV.search_conversations("plants", since="2026-09-10")
        assert out["match_count"] == 1, out
        assert out["searched_days"] == 1, out
        assert out["searched_from"] == "2026-09-20", out
        assert out["matches"][0]["date"] == "2026-09-20"


@check("since on the boundary date is inclusive")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "plants", "x")],
        })
        assert CONV.search_conversations("plants", since="2026-09-20")["match_count"] == 1


@check("a bad since is reported, not silently dropped for a wider window")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "plants", "x")],
        })
        out = CONV.search_conversations("plants", since="last Tuesday")
        assert out["error"], "a bad since must be reported"
        assert out["matches"] == [], out
        assert out["match_count"] == 0, out


@check("the span actually searched is reported, so an empty result says what was read")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-01": [_turn("2026-09-01", 1, "a", "b")],
            "2026-09-20": [_turn("2026-09-20", 1, "c", "d")],
        })
        out = CONV.search_conversations("nothing matches this")
        assert out["returned"] == 0 and out["error"] == "", out
        assert out["searched_days"] == 2, out
        assert out["searched_from"] == "2026-09-01" and out["searched_to"] == "2026-09-20", out


# ---------------------------------------------------------------------------
# 1b. search_conversations — a persona without data
# ---------------------------------------------------------------------------

@check("no conversations directory returns an empty result, not an error")
def _():
    with _temp_persona():
        out = CONV.search_conversations("anything")
        assert out["error"] == "", out["error"]
        assert out["matches"] == [] and out["match_count"] == 0, out
        assert out["searched_days"] == 0, out
        assert out["searched_from"] == "" and out["searched_to"] == "", out


@check("an empty conversations directory returns an empty result")
def _():
    with _temp_persona() as root:
        (root / "conversations").mkdir(parents=True)
        out = CONV.search_conversations("anything")
        assert out["error"] == "" and out["match_count"] == 0, out


@check("an unparseable line is skipped, not fatal to the file")
def _():
    with _temp_persona() as root:
        conv = root / "conversations"
        conv.mkdir(parents=True)
        (conv / "2026-09-20.jsonl").write_text(
            "{ half a line\n" + _turn("2026-09-20", 2, "plants", "x") + "\n\n"
        )
        out = CONV.search_conversations("plants")
        assert out["error"] == "" and out["match_count"] == 1, out


@check("a file whose name is not a date is ignored")
def _():
    with _temp_persona() as root:
        conv = root / "conversations"
        conv.mkdir(parents=True)
        (conv / "backup.jsonl").write_text(_turn("2026-09-20", 1, "plants", "x") + "\n")
        out = CONV.search_conversations("plants")
        assert out["searched_days"] == 0 and out["match_count"] == 0, out


@check("the shared cross-persona conversations directory is never read")
def _():
    # data/conversations/*.jsonl predates the per-persona layout and carries a
    # `persona` field rather than being scoped by directory. Reading it as a
    # fallback would put another persona's turns inside a persona-scoped result.
    with _temp_persona() as root:
        shared = root.parent / "conversations"
        shared.mkdir(parents=True, exist_ok=True)
        (shared / "2026-09-20.jsonl").write_text(_turn("2026-09-20", 1, "plants", "x") + "\n")
        out = CONV.search_conversations("plants")
        assert out["match_count"] == 0, "the shared directory must not be a fallback"


# ---------------------------------------------------------------------------
# 2. search_conversations — the caps
# ---------------------------------------------------------------------------

@check("k above the ceiling returns the ceiling, not everything")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", i, f"plants {i}", "x") for i in range(1, 81)],
        })
        out = CONV.search_conversations("plants", k=500)
        assert out["k"] == CONV.MAX_K == 50, out["k"]
        assert out["returned"] == 50, out["returned"]
        assert out["match_count"] == 80, out["match_count"]
        assert out["truncated"] is True, out


@check("k defaults to 10 when omitted, zero or negative")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", i, f"plants {i}", "x") for i in range(1, 31)],
        })
        for arg in ({}, {"k": 0}, {"k": -5}):
            out = CONV.search_conversations("plants", **arg)
            assert out["returned"] == CONV.DEFAULT_K == 10, (arg, out["returned"])
            assert out["match_count"] == 30, out


@check("match_count counts past k, so truncated is honest")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", i, f"plants {i}", "x") for i in range(1, 21)],
        })
        out = CONV.search_conversations("plants", k=3)
        assert (out["returned"], out["match_count"], out["truncated"]) == (3, 20, True), out


@check("a long field is excerpted around the match and flagged")
def _():
    with _temp_persona() as root:
        body = ("filler " * 400) + "MARKER" + (" filler" * 400)
        _write_conversations(root, {"2026-09-20": [_turn("2026-09-20", 1, "q", body)]})
        out = CONV.search_conversations("marker")
        hit = out["matches"][0]
        assert len(hit["response"]) <= CONV.SNIPPET_CHARS + 8, len(hit["response"])
        assert "MARKER" in hit["response"], "the excerpt must contain the match"
        assert hit["excerpted"] is True, hit


@check("a short field is returned whole and not flagged")
def _():
    with _temp_persona() as root:
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", 1, "water the plants?", "Not since Tuesday.")],
        })
        hit = CONV.search_conversations("water")["matches"][0]
        assert hit["user"] == "water the plants?", hit
        assert hit["response"] == "Not since Tuesday.", hit
        assert hit["excerpted"] is False, hit


@check("the whole returned payload is bounded by k times the snippet cap")
def _():
    with _temp_persona() as root:
        body = "plants " * 2000
        _write_conversations(root, {
            "2026-09-20": [_turn("2026-09-20", i, body, body) for i in range(1, 61)],
        })
        out = CONV.search_conversations("plants", k=999)
        size = sum(len(m["user"]) + len(m["response"]) for m in out["matches"])
        assert size <= CONV.MAX_K * 2 * (CONV.SNIPPET_CHARS + 8), size


# ---------------------------------------------------------------------------
# 3. read_journal_range — what it claims, on a persona with data
# ---------------------------------------------------------------------------

@check("a range returns every day in it, oldest first")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(3), ["three days ago"])
        _write_journal(root, _days_back(1), ["yesterday a", "yesterday b"])
        out = DIARIST.read_journal_range(start=_days_back(4), end=_days_back(0))
        assert out["error"] == "", out["error"]
        assert [d["date"] for d in out["days"]] == [_days_back(3), _days_back(1)], out["days"]
        assert out["day_count"] == 2 and out["entry_count"] == 3, out
        assert out["total_entries"] == 3 and out["truncated"] is False, out
        assert out["days"][1]["entries"][0]["text"] == "yesterday a"


@check("the dates actually read are echoed back")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(2), ["x"])
        out = DIARIST.read_journal_range(start=_days_back(5), end=_days_back(1))
        assert out["start"] == _days_back(5) and out["end"] == _days_back(1), out


@check("an empty end means today")
def _():
    with _temp_persona() as root:
        _write_journal(root, date.today().isoformat(), ["today"])
        out = DIARIST.read_journal_range(start=_days_back(2))
        assert out["end"] == date.today().isoformat(), out
        assert out["entry_count"] == 1, out


@check("an empty start means the widest window the ceiling allows")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(60), ["two months ago"])
        out = DIARIST.read_journal_range()
        assert out["start"] == _days_back(DIARIST.JOURNAL_RANGE_MAX_DAYS - 1), out["start"]
        assert out["end"] == date.today().isoformat(), out
        assert out["entry_count"] == 1, out


@check("a single-day range agrees with read_journal on that day")
def _():
    with _temp_persona() as root:
        day = _days_back(1)
        _write_journal(root, day, ["one", "two"])
        single = DIARIST.read_journal(day)
        ranged = DIARIST.read_journal_range(start=day, end=day)
        assert ranged["days"][0]["entries"] == single["entries"], (ranged, single)


# ---------------------------------------------------------------------------
# 3b. read_journal_range — gaps, absence and damage are not errors
# ---------------------------------------------------------------------------

@check("a range spanning dates with no journal entries does not error")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(1), ["yesterday"])
        out = DIARIST.read_journal_range(start=_days_back(30), end=_days_back(0))
        assert out["error"] == "", out["error"]
        assert out["day_count"] == 1, out


@check("a range with no journal file anywhere in it returns an empty result")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(40), ["old"])
        out = DIARIST.read_journal_range(start=_days_back(10), end=_days_back(5))
        assert out["error"] == "" and out["days"] == [], out
        assert out["day_count"] == 0 and out["entry_count"] == 0, out


@check("no journal directory at all returns an empty result, not an error")
def _():
    with _temp_persona():
        out = DIARIST.read_journal_range(start=_days_back(7))
        assert out["error"] == "" and out["days"] == [], out


@check("a day file holding an empty entries list is omitted rather than returned blank")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(1), [])
        out = DIARIST.read_journal_range(start=_days_back(3))
        assert out["days"] == [] and out["error"] == "", out


@check("a damaged day file is skipped and the rest of the window still returns")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(1), ["good"])
        (root / "journal" / f"{_days_back(2)}.json").write_text("{ not json")
        out = DIARIST.read_journal_range(start=_days_back(4))
        assert out["error"] == "", out["error"]
        assert out["entry_count"] == 1, out


@check("a bad start or end date is reported rather than guessed at")
def _():
    with _temp_persona():
        assert DIARIST.read_journal_range(start="yesterday")["error"]
        assert DIARIST.read_journal_range(end="09/24/2026")["error"]


@check("start after end is refused rather than silently swapped")
def _():
    with _temp_persona():
        out = DIARIST.read_journal_range(start=_days_back(1), end=_days_back(5))
        assert out["error"] and out["days"] == [], out


# ---------------------------------------------------------------------------
# 4. read_journal_range — the caps
# ---------------------------------------------------------------------------

@check("max_entries above the ceiling returns the ceiling, not everything")
def _():
    with _temp_persona() as root:
        for back in range(1, 11):
            _write_journal(root, _days_back(back), [f"d{back} e{i}" for i in range(30)])
        out = DIARIST.read_journal_range(start=_days_back(20), max_entries=5000)
        assert out["entry_count"] == DIARIST.JOURNAL_RANGE_MAX_ENTRIES == 200, out["entry_count"]
        assert out["total_entries"] == 300, out["total_entries"]
        assert out["truncated"] is True and out["note"], out


@check("max_entries defaults to 50 when omitted, zero or negative")
def _():
    with _temp_persona() as root:
        for back in range(1, 6):
            _write_journal(root, _days_back(back), [f"e{i}" for i in range(30)])
        for arg in ({}, {"max_entries": 0}, {"max_entries": -3}):
            out = DIARIST.read_journal_range(start=_days_back(10), **arg)
            assert out["entry_count"] == DIARIST.JOURNAL_RANGE_DEFAULT_ENTRIES == 50, (arg, out)
            assert out["total_entries"] == 150, out


@check("truncation keeps the MOST RECENT entries, as get_log_window does")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(3), ["oldest"])
        _write_journal(root, _days_back(2), ["middle"])
        _write_journal(root, _days_back(1), ["newest"])
        out = DIARIST.read_journal_range(start=_days_back(5), max_entries=2)
        texts = [e["text"] for d in out["days"] for e in d["entries"]]
        assert texts == ["middle", "newest"], texts
        assert out["total_entries"] == 3 and out["truncated"] is True, out


@check("truncation inside a day keeps that day's most recent entries")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(1), ["a", "b", "c", "d"])
        out = DIARIST.read_journal_range(start=_days_back(2), max_entries=2)
        texts = [e["text"] for d in out["days"] for e in d["entries"]]
        assert texts == ["c", "d"], texts


@check("a window wider than the ceiling is narrowed to the most recent 90 days and says so")
def _():
    with _temp_persona() as root:
        _write_journal(root, _days_back(200), ["long ago"])
        _write_journal(root, _days_back(2), ["recent"])
        out = DIARIST.read_journal_range(start=_days_back(365), end=_days_back(0))
        assert out["start"] == _days_back(DIARIST.JOURNAL_RANGE_MAX_DAYS - 1), out["start"]
        assert out["note"], "a narrowed window must be stated"
        assert out["entry_count"] == 1, out
        assert [d["date"] for d in out["days"]] == [_days_back(2)], out["days"]


@check("a window at exactly the ceiling is not narrowed")
def _():
    with _temp_persona():
        out = DIARIST.read_journal_range(
            start=_days_back(DIARIST.JOURNAL_RANGE_MAX_DAYS - 1), end=_days_back(0))
        assert out["start"] == _days_back(DIARIST.JOURNAL_RANGE_MAX_DAYS - 1), out
        assert out["note"] == "", out["note"]


# ---------------------------------------------------------------------------
# 5. Registration, and the phase-A presence table's fixed calls
# ---------------------------------------------------------------------------

@check("both tools are in register_tools()'s schema list and handler map")
def _():
    from core.orchestrator import register_tools
    schemas, handlers = register_tools()
    names = [s["name"] for s in schemas]
    for tool in ("search_conversations", "read_journal_range"):
        assert tool in names, f"{tool} missing from the schema list"
        assert tool in handlers, f"{tool} missing from the handler map"
        assert callable(handlers[tool]), tool
    assert len(names) == len(set(names)), "a duplicate tool name in the schema list"


@check("each schema is well formed and its name matches the handler key")
def _():
    from core.orchestrator import register_tools
    schemas, handlers = register_tools()
    for tool in ("search_conversations", "read_journal_range"):
        schema = next(s for s in schemas if s["name"] == tool)
        assert schema.get("description"), f"{tool} has no description"
        props = schema["input_schema"]["properties"]
        assert props, tool
        # Every property the schema advertises must be a real keyword argument.
        import inspect
        params = inspect.signature(handlers[tool]).parameters
        for prop in props:
            assert prop in params, f"{tool} schema advertises {prop!r}, not in the signature"


@check("the phase-A presence table's fixed call reaches each tool without a TypeError")
def _():
    from core.build.manifest import _SOURCES
    from core.orchestrator import register_tools
    _, handlers = register_tools()
    with _temp_persona():
        for source in _SOURCES:
            if source["tool"] not in ("search_conversations", "read_journal_range"):
                continue
            result = handlers[source["tool"]](**source["probe"])
            assert isinstance(result, dict), (source["id"], type(result))
            assert result["error"] == "", (source["id"], result["error"])


@check("both are classified as READS in core/actions.py, so neither joins the ACTIONS line")
def _():
    # test_action_provenance.py guards that every registered tool is classified at
    # all. This pins WHICH side: a read appearing on the ACTIONS line would tell
    # the user the system did something when it only looked something up.
    from core.actions import READ_TOOLS, is_action, is_classified
    for tool in ("search_conversations", "read_journal_range"):
        assert tool in READ_TOOLS, f"{tool} is not classified as a read"
        assert is_classified(tool) and not is_action(tool), tool


@check("the presence table now reports both sources available")
def _():
    from core.build.manifest import unavailable
    still_missing = unavailable()
    for source_id in ("conversations", "journal_range"):
        assert source_id not in still_missing, f"{source_id} still reads as unavailable"


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")
    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
