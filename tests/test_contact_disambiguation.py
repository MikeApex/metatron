#!/usr/bin/env python3
"""
Two failures that pull in opposite directions, in one file deliberately.

**One person becoming several records** (a short form not recognised as the same
person) and **several people collapsing into one** (a shared first name silently
resolved to whoever was stored first) are the same problem seen from two sides, and a
fix aimed at either one can worsen the other. Loosening the match until "Jon" reaches
"Jonathan" also drags every Bill toward every other Bill; tightening until the Bills
stay apart re-splits Jonathan. So both directions are asserted together — a change that
trades one for the other fails here rather than in front of the user.

Run: python tests/test_contact_disambiguation.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.crm import (  # noqa: E402
    _NAME_SIMILARITY_THRESHOLD,
    _ambiguous_match,
    _dedup_candidates,
    _disambiguation_entry,
    _name_similarity,
)

_FAILURES: list[str] = []


def check(label: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"  PASS  {label}")
    else:
        print(f"  FAIL  {label}" + (f"  — {detail}" if detail else ""))
        _FAILURES.append(label)


# The four Bills. One spoken name, four people, and a surname shared inside the set —
# so surname alone does not separate them either.
BILLS = [
    {"id": "c1", "name": "Bill Thompson", "last_name": "Thompson",
     "relationship_type": "colleague", "employer": "Meridian", "occupation": "analyst"},
    {"id": "c2", "name": "Bill Reyes", "last_name": "Reyes",
     "relationship_type": "service", "occupation": "plumber"},
    {"id": "c3", "name": "William Hart", "last_name": "Hart",
     "relationship_type": "friend", "nickname": "Bill"},
    {"id": "c4", "name": "William Hart Sr", "last_name": "Hart",
     "relationship_type": "friend_parent", "how_met": "father of William Hart"},
]


def test_short_form_is_recognised() -> None:
    """A nickname is a prefix, not a typo — edit distance alone scores it below the bar."""
    print("\nOne person must not become several records")
    for short, full in [("Jon", "Jonathan"), ("Jon", "Jonathan Whitfield"),
                        ("Dave", "David Okonkwo"), ("Tom", "Thomas Reed")]:
        score = _name_similarity(short, full)
        check(f"{short!r} reaches {full!r}  ({score:.2f} >= {_NAME_SIMILARITY_THRESHOLD})",
              score >= _NAME_SIMILARITY_THRESHOLD, f"scored {score:.2f}")

    # The pair that already worked. Guards against a "fix" that trades one for the other.
    score = _name_similarity("Jonathan", "Jonathan Whitfield")
    check(f"'Jonathan' still reaches 'Jonathan Whitfield'  ({score:.2f})", score >= 0.99)

    # Transcription near-misses the original guard was built for must keep clearing it.
    for a, b in [("Eva", "Iva Diamond"), ("Kathaleen", "Kathleen")]:
        score = _name_similarity(a, b)
        check(f"transcription near-miss {a!r}/{b!r} still caught  ({score:.2f})",
              score >= _NAME_SIMILARITY_THRESHOLD, f"scored {score:.2f}")

    candidates = _dedup_candidates(
        [{"id": "x", "name": "Jonathan Whitfield", "first_name": "Jonathan"}], "Jon")
    check("writing 'Jon' surfaces the existing Jonathan as a candidate",
          len(candidates) == 1 and candidates[0]["id"] == "x",
          f"got {candidates}")


def test_strangers_stay_apart() -> None:
    """
    The other direction — and the first draft of this test asserted it in the wrong
    place, which is worth keeping on the record.

    It expected two different Bills to score *below* the similarity threshold. They
    score 1.00, because they share a first name, and they did so long before the prefix
    signal was added. **That is correct.** The threshold feeds `_dedup_candidates`,
    which is an advisory list: `write_contact` creates the record either way and no code
    path merges anyone automatically. So the score was never what keeps two Bills apart,
    and tuning it down to "protect" them would only hide real duplicates while
    protecting nothing.

    What actually keeps different people from collapsing into one is structural, and is
    what this asserts: nothing auto-merges, and a name reaching several people refuses
    to resolve.
    """
    print("\nDifferent people must not be merged")

    # Sharing a first name SHOULD surface as a candidate. It is a real question about
    # real people, and the answer comes from asking, not from a score.
    for a, b in [("Bill Thompson", "Bill Reyes"), ("Sam", "Samir Haddad"),
                 ("Jon", "Joanna")]:
        score = _name_similarity(a, b)
        check(f"{a!r}/{b!r} surfaces to be asked about, not silently split  ({score:.2f})",
              score >= _NAME_SIMILARITY_THRESHOLD, f"scored {score:.2f}")

    # Genuinely unrelated names must still score clear of the bar, or the candidate
    # list becomes every contact and stops carrying information.
    for a, b in [("Ann", "Daniel"), ("Priya", "Marcus")]:
        score = _name_similarity(a, b)
        check(f"{a!r} does not reach {b!r}  ({score:.2f} < {_NAME_SIMILARITY_THRESHOLD})",
              score < _NAME_SIMILARITY_THRESHOLD, f"scored {score:.2f}")

    # Two-character prefixes reach too many names to be evidence of anything.
    score = _name_similarity("Jo", "Jordan")
    check(f"two-letter prefix 'Jo' does not reach 'Jordan'  ({score:.2f})",
          score < _NAME_SIMILARITY_THRESHOLD, f"scored {score:.2f}")

    # The structural guard, asserted directly: a candidate is evidence, never a verdict.
    #
    # Three of the four Bills surface, and the fourth is the useful part. "William Hart"
    # is reached only because someone recorded `nickname: Bill`; "William Hart Sr" has
    # no such record, so "Bill" does not reach him at all. **Matching is only ever as
    # good as the aliases someone stored** — which is what `nickname` and
    # `referred_to_as` are for, and why the ambiguity response below asks the user
    # rather than trying to infer the link. A fourth match here would mean the matcher
    # had started guessing that any William might be a Bill, which is the failure this
    # whole file exists to prevent.
    candidates = _dedup_candidates(BILLS, "Bill")
    check("every Bill with a recorded alias is offered, and none is chosen",
          len(candidates) == 3 and all("similarity" in c for c in candidates),
          f"got {candidates}")
    check("the William with no recorded alias is NOT guessed into the set",
          not any(c["id"] == "c4" for c in candidates))


def test_ambiguity_refuses_to_choose() -> None:
    """Four Bills: the tool must ask, not pick, and must not write."""
    print("\nA shared name must produce a question, not an answer")
    payload = json.loads(_ambiguous_match("Bill", BILLS, "returned"))

    check("flagged as ambiguous", payload.get("ambiguous") is True)
    check("all four candidates offered", len(payload.get("matches", [])) == 4,
          f"got {len(payload.get('matches', []))}")
    check("no contact record leaked into the response",
          not any(k in payload for k in ("relationship_quality", "contact_info", "notes")))

    instruction = payload.get("_instruction", "")
    check("tells the agent not to pick the first", "first" in instruction.lower())
    check("tells the agent to ask the user", "ask the user" in instruction.lower())

    # Each candidate must carry something a person could actually be asked about.
    for entry in payload["matches"]:
        distinguishing = set(entry) - {"id", "name"}
        check(f"{entry['name']!r} carries a distinguishing handle",
              bool(distinguishing), "only id and name")

    # A write must refuse, not file against a guess.
    write_payload = json.loads(_ambiguous_match("Bill", BILLS, "logged"))
    check("a write says nothing was logged",
          "nothing was logged" in write_payload.get("_instruction", ""))


def test_handle_is_not_the_whole_record() -> None:
    print("\nThe question must not come with the answer attached")
    full = dict(BILLS[0], notes="private", contact_info={"email": "b@example.org"},
                relationship_quality="close")
    handle = _disambiguation_entry(full)
    check("notes withheld", "notes" not in handle)
    check("contact_info withheld", "contact_info" not in handle)
    check("employer offered as a handle", handle.get("employer") == "Meridian")

    sparse = _disambiguation_entry({"id": "z", "name": "Bill"})
    check("a sparse contact yields no empty keys", set(sparse) == {"id", "name"},
          f"got {sorted(sparse)}")


if __name__ == "__main__":
    print("Contact disambiguation — both directions")
    print("=" * 60)
    test_short_form_is_recognised()
    test_strangers_stay_apart()
    test_ambiguity_refuses_to_choose()
    test_handle_is_not_the_whole_record()
    print("=" * 60)
    if _FAILURES:
        print(f"FAIL — {len(_FAILURES)} check(s) failed:")
        for f in _FAILURES:
            print(f"  · {f}")
        sys.exit(1)
    print("PASS — all checks passed.")
