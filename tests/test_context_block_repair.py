"""
tests/test_context_block_repair.py — [CONTEXT] block parsing and repair.

The Synthesizer appends [CONTEXT]{json}[/CONTEXT] to its response instead of
spending a tool-call turn on write_context_tracker. Until 2026-08-08 a block
that did not parse produced one log line and a silent drop: the context-tracker
update, and any dev_request riding along in it, were gone with no retry and no
record. `strict=False` (2026-08-02) covered exactly one malformation — a literal
newline inside a string value — and nothing else.

These cases are the malformations a model actually emits: a markdown fence,
prose either side, a trailing comma, a block truncated by a token limit, smart
quotes, single quotes, and one broken value in an otherwise-good object. Every
one of them used to lose the whole update.

Offline — no model calls, no persona data written.

Run:
    python tests/test_context_block_repair.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.orchestrator import (_balance, _repair_context_json,  # noqa: E402
                                split_context_block)


def _parse(raw: str):
    return _repair_context_json(raw)


# --- the ladder ------------------------------------------------------------

def test_clean_block_is_not_reported_as_repaired():
    parsed, how = _parse('{"open_threads": ["a"], "patterns": [], "follow_ups": []}')
    assert parsed == {"open_threads": ["a"], "patterns": [], "follow_ups": []}
    assert how == "clean", f"clean block reported as {how!r} — would log a repair every turn"


def test_literal_newline_in_a_string_value():
    """The 2026-08-02 live failure. strict=False covers it; this pins that."""
    parsed, _ = _parse('{"open_threads": ["line one\nline two"], "patterns": []}')
    assert parsed["open_threads"] == ["line one\nline two"]


def test_markdown_fence():
    parsed, _ = _parse('```json\n{"open_threads": ["a"], "patterns": []}\n```')
    assert parsed == {"open_threads": ["a"], "patterns": []}


def test_prose_either_side_of_the_object():
    parsed, _ = _parse('Here is the context:\n{"open_threads": ["a"]}\nHope that helps.')
    assert parsed == {"open_threads": ["a"]}


def test_trailing_comma():
    parsed, _ = _parse('{"open_threads": ["a"], "patterns": [],}')
    assert parsed == {"open_threads": ["a"], "patterns": []}


def test_truncated_mid_array_keeps_what_was_written():
    parsed, _ = _parse('{"open_threads": ["a", "b"], "patterns": ["c"')
    assert parsed == {"open_threads": ["a", "b"], "patterns": ["c"]}


def test_truncated_mid_string_keeps_what_was_written():
    parsed, _ = _parse('{"open_threads": ["a"], "patterns": ["unfinished val')
    assert parsed["open_threads"] == ["a"]
    assert parsed["patterns"] == ["unfinished val"]


def test_smart_quotes():
    parsed, _ = _parse('{“open_threads”: [“a”], “patterns”: []}')
    assert parsed == {"open_threads": ["a"], "patterns": []}


def test_single_quoted_python_style_block():
    parsed, _ = _parse("{'open_threads': ['a'], 'patterns': []}")
    assert parsed == {"open_threads": ["a"], "patterns": []}


def test_apostrophe_in_a_value_is_not_mangled():
    """
    The single-quote conversion must not fire on a block that merely contains an
    apostrophe — "mum's birthday" is ordinary content, and converting it would
    corrupt a block that already parses.
    """
    parsed, how = _parse('{"follow_ups": ["mum\'s birthday"]}')
    assert parsed == {"follow_ups": ["mum's birthday"]}
    assert how == "clean"


def test_array_closed_with_the_wrong_bracket():
    parsed, _ = _parse('{"open_threads": ["a",}')
    assert parsed == {"open_threads": ["a"]}


# --- partial salvage -------------------------------------------------------

def test_one_broken_value_does_not_cost_the_others():
    raw = ('{"open_threads": ["a", "b"], "patterns": [oops not json], '
           '"follow_ups": ["call mum"]}')
    parsed, how = _parse(raw)
    assert parsed["open_threads"] == ["a", "b"]
    assert parsed["follow_ups"] == ["call mum"]
    assert "patterns" not in parsed
    assert "salvage" in how


def test_dev_request_survives_a_salvage():
    """
    The dev_request is the half of the block with no other route into the
    system — a lost context-tracker update is re-derivable from the next turn,
    a lost change request is not.
    """
    raw = ('{"patterns": [nope], "dev_request": {"type": "FEATURE_REQUEST", '
           '"detail": "add a snooze button"}}')
    parsed, _ = _parse(raw)
    assert parsed["dev_request"]["type"] == "FEATURE_REQUEST"
    assert parsed["dev_request"]["detail"] == "add a snooze button"


def test_unrecoverable_block_returns_none():
    parsed, how = _parse("total gibberish, no json here at all")
    assert parsed is None
    assert how == "unrecoverable"


# --- the splitter ----------------------------------------------------------

def test_split_keeps_visible_text_and_repairs_the_block():
    visible, ctx = split_context_block(
        'Here is your answer.\n\n[CONTEXT]{"open_threads": ["a",}[/CONTEXT]'
    )
    assert visible == "Here is your answer."
    assert ctx == {"open_threads": ["a"]}


def test_split_without_a_block_is_untouched():
    visible, ctx = split_context_block("Just an answer.")
    assert visible == "Just an answer."
    assert ctx is None


def test_block_never_reaches_the_visible_text():
    visible, _ = split_context_block(
        'Answer.[CONTEXT]{"open_threads": ["secret thread"]}[/CONTEXT]'
    )
    assert "CONTEXT" not in visible and "secret thread" not in visible


def test_balance_leaves_valid_json_alone():
    good = '{"a": [1, 2], "b": {"c": "d"}}'
    assert _balance(good) == good


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc}")
    print()
    if failures:
        print(f"{len(failures)} failed")
        sys.exit(1)
    print("all passed")
