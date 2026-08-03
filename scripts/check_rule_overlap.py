#!/usr/bin/env python3
"""
Report behavioural rules that are stated in more than one place.

A rule should have exactly one home (CLAUDE.md, "One home per rule class").
Duplication is not untidiness: when the same instruction sits in a persona file
and an agent file, editing one leaves the other stale and the stale copy keeps
firing. On 2026-08-03 five of the user's stated preferences sat in both
`config/personas/mike.md` and `config/agents/synthesizer.md`, and nothing noticed
until they were read side by side by hand.

Two passes, because one is not enough:

  1. **Class collision** — the rules are sorted into classes (repetition,
     brevity, evidence weighting, ...). A class appearing in both the persona
     layer and the agent layer is the signature of promotion debt: a personal
     rule was generalised upward and the original was never deleted. This is the
     pass that matters. Bag-of-words comparison cannot find these — "Stop
     repetitive reminders for pending tasks" and "Raise a thing once. An open
     item you have already surfaced is not raised again" are the same rule and
     share no content words at all.

  2. **Near-duplicate text** — a plain overlap score, which catches restatements
     the class list has no entry for. A coarse net, kept because the class list
     will always be incomplete.

Neither pass decides anything. Both report candidates for a human to judge, and
the script exits 0 regardless: a persona rule in the same class as an agent rule
is often legitimate (a personal override of a universal baseline). What is *not*
legitimate is the two saying the same thing.

Stdlib only, so it runs without the venv.

Usage
-----
    python3 scripts/check_rule_overlap.py                  # all local personas
    python3 scripts/check_rule_overlap.py --persona mike
    python3 scripts/check_rule_overlap.py --near-only 0.3  # pass 2 only, stricter

The live `mike` files are VM-owned and deliberately absent from the Mac (see
CLAUDE.md, "The VM owns live persona config"). To check them, run on the VM:

    gcloud compute ssh metatron-vm --zone=us-central1-a \\
      --project=metatron-ai-499810 --tunnel-through-iap \\
      --command='cd ~/multi-model-mcp && python3 scripts/check_rule_overlap.py --persona mike'
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# Rule classes
#
# Each entry is a class of behavioural instruction and the layer that owns it.
# `home` is where a *universal* rule of this class belongs; a persona file may
# still carry a personal variant, which is why a collision is reported rather
# than failed. Patterns are deliberately generous — a false positive costs a
# glance, a false negative costs another 2026-08-03.
# ---------------------------------------------------------------------------

CLASSES: dict[str, dict] = {
    "repetition": {
        "home": "agent",
        "desc": "raising the same item again; re-listing; standing reminders",
        "pat": r"\b(raise[ds]? (it |the |a )?(thing |item )?once|already surfaced|"
               r"repetitive|repeat(ed|ing|s)?|re-?list|re-?rais|again and again|"
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
               r"minor (health|sleep))\b",
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


class Rule:
    __slots__ = ("text", "source", "layer", "line", "words", "classes")

    def __init__(self, text: str, source: str, layer: str, line: int):
        self.text = text
        self.source = source
        self.layer = layer
        self.line = line
        self.words = _content_words(text)
        self.classes = {n for n, c in CLASSES.items() if c["re"].search(text)}


def _content_words(text: str) -> set[str]:
    text = re.sub(r"`[^`]*`", " ", text)          # code spans name mechanisms, not rules
    text = re.sub(r"\*+|_+|#+|>|\[|\]", " ", text)
    return {w for w in re.findall(r"[a-z']{3,}", text.lower()) if w not in STOPWORDS}


def _similarity(a: Rule, b: Rule) -> float:
    """Overlap coefficient, not Jaccard.

    A one-line persona preference and a four-line agent rule can state the same
    instruction at very different lengths; Jaccard penalises that difference and
    scores the real duplicates below any usable threshold. Dividing by the
    smaller set asks the right question: is the shorter rule contained in the
    longer one?
    """
    if not a.words or not b.words:
        return 0.0
    return len(a.words & b.words) / min(len(a.words), len(b.words))


# ---------------------------------------------------------------------------
# Extraction — one reader per layer, since each stores rules differently
# ---------------------------------------------------------------------------

def _bullets(path: Path, layer: str, section: str | None = None) -> list[Rule]:
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
            rules.append(Rule(line.lstrip("-* ").strip(), str(path.relative_to(ROOT)), layer, i))
    return rules


def _bold_rules(path: Path, layer: str) -> list[Rule]:
    """Agent-file rules: a paragraph opening with a **bolded imperative**."""
    if not path.exists():
        return []
    out = []
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        line = raw.strip()
        if re.match(r"^\*\*[^*]{6,}?\*\*", line) and len(line) > 60:
            out.append(Rule(line, str(path.relative_to(ROOT)), layer, i))
    return out


def _scheduler_prompts(path: Path, layer: str) -> list[Rule]:
    """`prompt:` values, read as text to avoid a yaml dependency."""
    if not path.exists():
        return []
    out = []
    for i, raw in enumerate(path.read_text(errors="replace").splitlines(), 1):
        m = re.match(r'^\s*prompt:\s*"(.+)"\s*$', raw)
        if m:
            out.append(Rule(m.group(1), str(path.relative_to(ROOT)), layer, i))
    return out


def collect(persona: str | None) -> list[Rule]:
    rules: list[Rule] = []

    for f in sorted((ROOT / "config" / "agents").glob("*.md")):
        rules += _bold_rules(f, "agent")

    names = [persona] if persona else [
        p.stem for p in sorted((ROOT / "config" / "personas").glob("*.md"))
    ]
    for name in names:
        rules += _bullets(ROOT / "config" / "personas" / f"{name}.md",
                          "persona", section="Interaction Preferences")
        rules += _scheduler_prompts(
            ROOT / "config" / "personas" / name / "scheduler.yaml", "scheduler")

    rules += _scheduler_prompts(ROOT / "config" / "templates" / "scheduler.yaml", "scheduler")
    return rules


# ---------------------------------------------------------------------------

def _report_collisions(rules: list[Rule], show: int = 3) -> int:
    """Pass 1: a persona rule whose class is also carried by a shared layer.

    The class match supplies recall — it finds pairs with no vocabulary in
    common. Similarity is then used only to *rank* the candidates within the
    class, because a class like `repetition` legitimately holds a dozen agent
    rules and listing them all buries the one that matters.
    """
    found = 0
    for r in rules:
        if r.layer != "persona":
            continue
        for name in sorted(r.classes):
            partners = [o for o in rules
                        if o.layer != "persona" and name in o.classes]
            if not partners:
                continue
            partners.sort(key=lambda o: -_similarity(r, o))
            found += 1
            meta = CLASSES[name]
            print(f"── {r.source}:{r.line}  [class: {name}]")
            print(f"       {r.text[:170]}")
            print(f"   {meta['desc']}; a universal rule of this class "
                  f"belongs in the {meta['home']} layer.")
            print(f"   Closest existing rule(s) elsewhere:\n")
            for o in partners[:show]:
                contradiction = bool(NEGATIVE.search(r.text)) != bool(NEGATIVE.search(o.text))
                flag = "   ⚠ one negates, one does not" if contradiction else ""
                print(f"     [{_similarity(r, o):.2f}] {o.layer}  {o.source}:{o.line}{flag}")
                print(f"           {o.text[:150]}")
            if len(partners) > show:
                print(f"     … and {len(partners) - show} more in this class")
            print("\n   → Does the persona rule say anything these do not? If not,")
            print("     delete it: the promotion left the original behind.\n")
    return found


def _report_near_duplicates(rules: list[Rule], threshold: float) -> int:
    """Pass 2: near-verbatim restatements across layers."""
    hits = []
    for i, a in enumerate(rules):
        for b in rules[i + 1:]:
            if a.layer == b.layer:
                continue
            score = _similarity(a, b)
            if score >= threshold:
                contradiction = bool(NEGATIVE.search(a.text)) != bool(NEGATIVE.search(b.text))
                hits.append((score, contradiction, a, b))

    hits.sort(key=lambda h: (-h[1], -h[0]))
    for score, contradiction, a, b in hits:
        flag = "  ⚠ one negates, one does not" if contradiction else ""
        print(f"[{score:.2f}] {a.layer} ↔ {b.layer}{flag}")
        print(f"   {a.source}:{a.line}\n       {a.text[:150]}")
        print(f"   {b.source}:{b.line}\n       {b.text[:150]}\n")
    return len(hits)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", help="check one persona (default: all local ones)")
    ap.add_argument("--threshold", type=float, default=0.25,
                    help="near-duplicate overlap score, 0-1 (default 0.25)")
    ap.add_argument("--near-only", action="store_true", help="skip the class pass")
    ap.add_argument("--classes-only", action="store_true", help="skip the near-duplicate pass")
    args = ap.parse_args()

    rules = collect(args.persona)
    if not rules:
        print("No rules found — wrong directory?", file=sys.stderr)
        return 0

    counts: dict[str, int] = {}
    for r in rules:
        counts[r.layer] = counts.get(r.layer, 0) + 1
    print("Scanned " + ", ".join(f"{n} {l}" for l, n in sorted(counts.items())))
    if "persona" not in counts:
        print("\nNote: no persona preferences found. The live `mike` files are "
              "VM-only —\nrun this on the VM to check them (see the docstring).")

    collisions = near = 0

    if not args.near_only:
        print("\n" + "=" * 72)
        print("PASS 1 — rule classes carried in more than one layer")
        print("=" * 72 + "\n")
        collisions = _report_collisions(rules)
        if not collisions:
            print("None. No class is stated at both the persona and a shared layer.\n")

    if not args.classes_only:
        print("=" * 72)
        print(f"PASS 2 — near-duplicate wording across layers (>= {args.threshold})")
        print("=" * 72 + "\n")
        near = _report_near_duplicates(rules, args.threshold)
        if not near:
            print("None.\n")

    print("=" * 72)
    print(f"{collisions} class collision(s), {near} near-duplicate pair(s).")
    print("Candidates, not verdicts. For each: pick the one correct home,")
    print("keep that copy, delete the other.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
