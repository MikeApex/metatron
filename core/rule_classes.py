"""
core/rule_classes.py — what class of instruction a behavioural rule belongs to.

A rule should have exactly one home. Duplication is not untidiness: when the same
instruction sits in a persona file and an agent file, editing one leaves the
other stale and the stale copy keeps firing. On 2026-08-03 five of the user's
preferences sat in both `config/personas/mike.md` and
`config/agents/synthesizer.md`, and nothing noticed until they were read side by
side by hand.

This module holds the class definitions and the matcher, shared by two callers
with different jobs:

  - `tools/persona.py` calls `check_new_rule()` **at write time**, so a
    preference that restates an existing rule is caught as it is being recorded
    rather than months later.
  - `scripts/check_rule_overlap.py` sweeps everything already written, for the
    rules that predate the guard and for classes the list does not yet cover.

Why classes rather than text similarity: the real duplicates share no vocabulary.
"Stop repetitive reminders for pending tasks" and "Raise a thing once. An open
item you have already surfaced is not raised again" are the same instruction with
almost no words in common — any bag-of-words score puts them near zero. Matching
the *class* finds them; similarity is then useful only for ranking candidates
within a class.

Stdlib only: this is imported by a script that runs without the venv.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# The classes
#
# `home` is where a *universal* rule of this class belongs. A persona file may
# still carry a personal variant — that is the point of having a persona layer —
# so a collision is reported, never blocked. What is illegitimate is the two
# saying the same thing.
#
# Patterns are deliberately generous. A false positive costs a glance; a false
# negative costs another five-rule duplicate set nobody notices for months.
# ---------------------------------------------------------------------------

CLASSES: dict[str, dict] = {
    "repetition": {
        "home": "agent",
        "desc": "raising the same item again; re-listing; standing reminders",
        # Phrasings users reach for, not just the ones the agent files use.
        # "Stop bringing up the same task over and over" is this class and
        # shares no vocabulary with "Raise a thing once" — if the pattern only
        # covers the instruction's wording it never matches the complaint.
        "pat": r"\b(raise[ds]? (it |the |a )?(thing |item )?once|already surfaced|"
               r"repetitive|repeat(ed|ing|s)?|re-?list|re-?rais|again and again|"
               r"over and over|same (thing|item|task|point|subject)|each time|"
               r"every (time|message|response)|keep (bringing|telling|mentioning|asking)|"
               r"bring(ing)? (it |them |that )?up|"
               r"reminder[s]?|recap|restate|summaris|summariz|re-?justif)\b",
    },
    "sycophancy": {
        "home": "agent",
        "desc": "praise, validation, filler, conversational sign-offs",
        "pat": r"\b(commendation|validation|affirmation|complimen|sycophan|flatter|"
               r"filler|enjoy|sign-?off|great question|well done)\b",
    },
    "brevity": {
        "home": "scheduler",
        "desc": "how long a proactive session's opening should be",
        "pat": r"\b(brief|briefly|short|shorter|concise|terse|two sentences|"
               r"one line|at most|keep it (to|short)|length)\b",
    },
    "evidence_weighting": {
        "home": "agent",
        "desc": "how much to infer from thin or lopsided data",
        "pat": r"\b(over-?emphasi|over-?read|over-?index|over-?weight|loudest|"
               r"single data point|not a pattern|thin record|available signal|"
               r"minor (health|sleep)|read(ing)? (so much |too much )?into|"
               r"making too much of|one (bad|poor|rough) night|"
               r"blow(ing)? .{0,20}out of proportion|fixat(e|ed|ing|ion))\b",
    },
    "session_timing": {
        "home": "scheduler",
        "desc": "when a proactive session may fire, and whether it yields",
        "pat": r"\b(active (dialogue|conversation)|mid-?conversation|interrupt|"
               r"quiet hours|check-?in (if|only|when)|fold (them|it) |"
               r"trigger scheduled|not responding|gone quiet)\b",
    },
    "justification": {
        "home": "agent",
        "desc": "when to give the reasoning behind a recommendation",
        "pat": r"\b(give the reason|explain(ing)? (a |the )?recommendation|"
               r"re-?justif|why it matters|rationale|first time,? not every)\b",
    },
    "follow_up_style": {
        "home": "persona",
        "desc": "what a follow-up question should do",
        "pat": r"\b(follow(ing)?[- ]up|build into something new|deeper knowledge|"
               r"ask a question that)\b",
    },
    "confidentiality": {
        "home": "agent",
        "desc": "what must never be named in output",
        "pat": r"\b(never name|confidential|do not reveal|internal mechanism|"
               r"withheld|system prompt|architecture)\b",
    },
    "capture": {
        "home": "agent",
        "desc": "what gets written down, and where",
        "pat": r"\b(durable preference|write it down|record(ed|ing)? it|"
               r"biographical|standing preference|stored)\b",
    },
}

for _c in CLASSES.values():
    _c["re"] = re.compile(_c["pat"], re.I)


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "but", "by", "can", "do",
    "does", "each", "for", "from", "get", "give", "had", "has", "have", "how",
    "if", "in", "into", "is", "it", "its", "just", "make", "makes", "may", "more",
    "most", "much", "no", "nor", "not", "of", "on", "once", "one", "only", "or",
    "other", "out", "over", "own", "put", "rather", "say", "says", "should", "so",
    "some", "such", "than", "that", "the", "their", "them", "then", "there",
    "these", "they", "thing", "things", "this", "those", "to", "too", "up", "use",
    "user", "users", "very", "was", "way", "were", "what", "when", "where",
    "which", "while", "who", "why", "will", "with", "would", "you", "your",
}

NEGATIVE = re.compile(
    r"\b(never|not|no|don't|dont|do not|stop|avoid|drop|without|refrain|skip)\b", re.I
)

# Fewest content words a rule may have and still be judged by the overlap coefficient.
# See similarity(): below this the coefficient degenerates to "does this common word
# appear", and a one-word rule becomes a perfect match for everything.
_OVERLAP_MIN_WORDS = 3


class Rule:
    __slots__ = ("text", "source", "layer", "line", "words", "classes")

    def __init__(self, text: str, source: str, layer: str, line: int = 0):
        self.text = text
        self.source = source
        self.layer = layer
        self.line = line
        self.words = content_words(text)
        self.classes = {n for n, c in CLASSES.items() if c["re"].search(text)}

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<Rule {self.source}:{self.line} {sorted(self.classes)}>"


def content_words(text: str) -> set[str]:
    text = re.sub(r"`[^`]*`", " ", text)          # code spans name mechanisms, not rules
    text = re.sub(r"\*+|_+|#+|>|\[|\]", " ", text)
    return {w for w in re.findall(r"[a-z']{3,}", text.lower()) if w not in STOPWORDS}


def similarity(a: Rule, b: Rule) -> float:
    """Overlap coefficient, not Jaccard.

    A one-line persona preference and a four-line agent rule can state the same
    instruction at very different lengths; Jaccard penalises that difference and
    scores the real duplicates below any usable threshold. Dividing by the
    smaller set asks the right question: is the shorter rule contained in the
    longer one?

    **A rule of one or two content words is not a home, and before 2026-09-05 it was
    the best-scoring one available.** The overlap coefficient divides by the smaller
    set, so a rule reducing to `{check}` — which is all `prompt: "Check in."` in
    `config/templates/scheduler.yaml` amounts to after stopwords — scores a perfect
    1.000 against *any* rule mentioning a check-in, and out-ranks every genuine match
    permanently. That is what refused Mike's check-in instruction on 2026-09-05 while
    citing a line reading `prompt: "Check in."` as the place the rule was held.

    Below the floor the coefficient answers the wrong question — "is this common word
    present" rather than "is the shorter rule contained in the longer" — so it falls
    back to Jaccard, which penalises the length gap exactly as intended here and puts
    such a pair well under any usable threshold. Three, because two content words is
    still a bare subject and a verb; genuine short rules ("Do not tell the user to
    enjoy things" → four content words) are untouched.
    """
    if not a.words or not b.words:
        return 0.0
    inter = len(a.words & b.words)
    if min(len(a.words), len(b.words)) < _OVERLAP_MIN_WORDS:
        return inter / len(a.words | b.words)
    return inter / min(len(a.words), len(b.words))


def contradicts(a: Rule, b: Rule) -> bool:
    """One negates and the other does not — worth a closer look than duplication.

    Two rules on the same subject where one forbids and the other permits is a
    contradiction, and whichever layer loads last silently wins.
    """
    return bool(NEGATIVE.search(a.text)) != bool(NEGATIVE.search(b.text))


# ---------------------------------------------------------------------------
# Readers — one per layer, since each stores rules differently
# ---------------------------------------------------------------------------

def read_bullets(path: Path, layer: str, section: str | None = None) -> list[Rule]:
    """Markdown list items, optionally only those under a given `## Section`."""
    if not path.exists():
        return []
    rules, in_section = [], section is None
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        if line.startswith("#"):
            in_section = section is None or line.lstrip("# ").strip().lower() == section.lower()
            continue
        if in_section and re.match(r"^[-*]\s+\S", line):
            rules.append(Rule(line.lstrip("-* ").strip(), _rel(path), layer, i))
    return rules


def read_bold_rules(path: Path, layer: str = "agent") -> list[Rule]:
    """Agent-file rules: a paragraph opening with a **bolded imperative**."""
    if not path.exists():
        return []
    out = []
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        if re.match(r"^\*\*[^*]{6,}?\*\*", line) and len(line) > 60:
            out.append(Rule(line, _rel(path), layer, i))
    return out


def read_scheduler_prompts(path: Path, layer: str = "scheduler") -> list[Rule]:
    """`prompt:` values, read as text to avoid a yaml dependency."""
    if not path.exists():
        return []
    out = []
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        m = re.match(r'^\s*prompt:\s*"(.+)"\s*$', raw)
        if m:
            out.append(Rule(m.group(1), _rel(path), layer, i))
    return out


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(ROOT))
    except ValueError:
        return str(path)


def shared_rules(persona: str | None = None) -> list[Rule]:
    """Every rule that applies beyond a single persona file.

    Agent files and the shared `config/modules/*.md` conduct (all personas), plus
    scheduler prompts (this persona, and the template every new persona inherits).
    These are what a new personal preference might be restating.

    **`config/modules/*.md` was missing until 2026-09-05, and the corpus had gone stale
    rather than been written wrong.** It covered agent files because that is where the
    scheduled-session conduct lived — until the 2026-08-27 synthesizer audit moved it out
    to `config/modules/synthesizer_scheduled_sessions.md`, and nothing moved the corpus
    with it. The failure is not that a rule was missed but that a *worse* partner was then
    cited as its home: on 2026-09-05 `write_persona` refused Mike's check-in instruction
    naming `config/templates/scheduler.yaml:52`, a line reading `prompt: "Check in."`,
    while the rule it was actually restating sat in the module file this glob now reads.
    A refusal the user cannot verify is worse than no refusal, because it sends them to
    edit the wrong file.

    Same consequence for `tools/rule_audit.py`, which sweeps this corpus every morning and
    shared the blind spot.
    """
    rules: list[Rule] = []
    for f in sorted((ROOT / "config" / "agents").glob("*.md")):
        rules += read_bold_rules(f)
    # Same bolded-imperative convention as the agent files, which is why the same reader
    # works. Only `*.md` — `config/modules/` also holds routing and spend YAML, which is
    # configuration rather than instruction and has no business in a rule corpus.
    for f in sorted((ROOT / "config" / "modules").glob("*.md")):
        rules += read_bold_rules(f)
    if persona:
        rules += read_scheduler_prompts(
            ROOT / "config" / "personas" / persona / "scheduler.yaml")
    rules += read_scheduler_prompts(ROOT / "config" / "templates" / "scheduler.yaml")
    return rules


def check_new_rule(text: str, persona: str | None = None,
                   limit: int = 2) -> list[tuple[str, Rule, float]]:
    """Is this preference already covered by a rule at a shared layer?

    Returns `(class_name, existing_rule, similarity)` best-first, empty if
    nothing matches. Pure regex and set arithmetic — no model call, no I/O
    beyond reading the config files, so it is safe on a write path.

    Callers should **warn, never block**. A preference the user actually stated
    must be recorded; refusing the write to enforce tidiness loses what they
    said, which is a worse failure than a duplicate.
    """
    candidate = Rule(text, "<new>", "persona")
    if not candidate.classes:
        return []

    hits: list[tuple[str, Rule, float]] = []
    for existing in shared_rules(persona):
        common = candidate.classes & existing.classes
        if common:
            hits.append((sorted(common)[0], existing, similarity(candidate, existing)))

    hits.sort(key=lambda h: -h[2])
    return hits[:limit]
