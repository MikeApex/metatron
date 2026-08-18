#!/usr/bin/env python3
"""
scripts/backlog_close_scan.py — surface backlog items this session may have closed.

Run at `/archive` step 4, before the manual close pass.

## Why this exists

Step 4 has always said "close first", and its method was: list the files the session
touched, grep `DEV_BACKLOG.md` for those filenames. That catches an item that *names a
file*. It misses an item written in symptom language — which is most of them, because the
filing bar is "a user would notice", and a user notices behaviour, not paths.

`[DB-0808-16]` is the worked example. Its fix — a docstring line naming an ordinary-life
persona, plus a guard that fails loudly when `read_email` was never called — shipped inside
`7c70cd9`, a commit aimed at something else entirely. The item's text names no file. Nobody
was looking for it, the filename grep could not see it, and it sat closed-but-open for ten
days until a `/backlog deep` sweep opened it against the code by hand.

**That is the gap: incidental closures.** A session closes what it aimed at. What it closes
by accident is invisible until an expensive periodic sweep finds it, which is why roughly a
third of what `deep` checks turns out already fixed.

## What it does, and deliberately does not do

It reports **evidence, not a verdict** — the same pattern as `tools/scheduling.py`, the
calendar duplicate audit, and `write_contact`'s near-match surfacing. It ranks candidate
items by overlap between the session's diff and each item's text, across three signals:

1. **paths** — filenames and directories touched (the old behaviour, kept)
2. **symbols** — function, method and constant names added or removed by the diff, which is
   what an item usually cites when it cites anything (`_thread_tier()`, `pop_agent`,
   `_CONTEXT_MAX`)
3. **words** — content words shared between the commit subjects and the item's title line

It never edits `DEV_BACKLOG.md` and never closes anything. A high score means *open this item
against the diff*, not *this is done*. The standing rule — no item is acted on, or re-filed,
on the strength of its own description — applies to this script's output too: it is a
description, generated from a description.

## What it retires

Per the standing rule in `.claude/rules/deploy.md` — no new harness script without naming
what it retires — this replaces the **filename-grep half of `/archive` step 4**. That step's
manual instruction ("grep the backlog for those filenames") is deleted from the command file
in the same commit, not left beside this as a second method. The judgement half of step 4 —
reading each candidate against the diff, deciding fully/partly/untouched — is unchanged and
stays a human step, because that is the part that was never the bottleneck.

Usage:
    python3 scripts/backlog_close_scan.py                 # commits since origin/main
    python3 scripts/backlog_close_scan.py --since HEAD~5
    python3 scripts/backlog_close_scan.py --since <sha>..<sha>
    python3 scripts/backlog_close_scan.py --min-score 2   # widen or narrow the report
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "DEV_BACKLOG.md"

# Sections that hold live items. `## Inbox` is untriaged and machine-written, `## Machine
# log` is the runtime talking to itself, `## Done` is already closed — none of the three is
# something a session closes, so scanning them would only add noise.
LIVE_SECTIONS = ("## Now", "## Later")

ID_RE = re.compile(r"\[DB-\d{4}-\d{2}\]")

# Backticked tokens inside an item: `read_email`, `_thread_tier()`, `injection`. This file
# quotes identifiers constantly, and they are the item's own statement of what it is about
# — far more precise than prose. Searched against the diff BODY, not the commit subject.
TICKED_RE = re.compile(r"`([A-Za-z_][A-Za-z0-9_./]{2,})`")

# A changed symbol: the name on an added/removed def, class, or module-level assignment.
# Deliberately loose — it is a search key, not a parse. A false key costs one weak match;
# a missed key costs a missed closure, which is the failure this script exists to prevent.
SYMBOL_RE = re.compile(
    r"^[+-]\s*(?:async\s+)?(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)"
    r"|^[+-]\s*([A-Z_][A-Z0-9_]{3,})\s*(?::[^=]+)?=",
    re.MULTILINE,
)

# Words too common in this codebase to carry signal. Not a general stopword list — these are
# the terms that appear in nearly every item and would match everything.
NOISE = {
    "the", "and", "for", "that", "this", "with", "from", "into", "not", "but", "its",
    "user", "users", "agent", "agents", "tool", "tools", "call", "calls", "code", "file",
    "files", "item", "items", "fix", "fixed", "test", "tests", "run", "runs", "add",
    "added", "when", "what", "which", "was", "were", "has", "have", "been", "does",
    "metatron", "session", "sessions", "one", "two", "all", "any", "than", "then",
}

WORD_RE = re.compile(r"[a-z_][a-z0-9_]{2,}")

# Record files are excluded from the DIFF EVIDENCE — not from the scan, from the evidence.
# A close-out commit rewrites DEV_BACKLOG.md, SESSION.md and the log in the same breath as
# the code, so their added lines contain every item's own text. Left in, the scan scores
# 44 of ~50 items as candidates: each one matching itself. This is the single exclusion
# that separates a usable report from noise, and it is why the first run looked like it
# was working when it was not.
RECORD_PATHS = (
    "DEV_BACKLOG.md", "SESSION.md", "ROADMAP.md", "CLAUDE.md",
    "CODEBASE_INDEX.md", "archive/", ".claude/", "docs/",
)


def _is_record(path: str) -> bool:
    return any(path == r or path.startswith(r) for r in RECORD_PATHS)


def _git(*args: str) -> str:
    """Run a read-only git command in the repo root; empty string on failure."""
    try:
        out = subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        )
        return out.stdout
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _default_range() -> str:
    """
    Commits this session added, as a git range.

    `origin/main..HEAD` is the honest default: it is what a close-out is about to commit or
    has just committed on a branch. Falls back to HEAD~1 on a repo with no upstream, rather
    than scanning the whole history and reporting every item ever.
    """
    if _git("rev-parse", "--verify", "--quiet", "origin/main").strip():
        rng = "origin/main..HEAD"
        if _git("rev-list", "--count", rng).strip() not in ("", "0"):
            return rng
    return "HEAD~1..HEAD"


def session_evidence(rev_range: str) -> tuple[set[str], set[str], set[str], str]:
    """
    (paths, symbols, subject words, added-line text) for the commits in `rev_range`.

    The fourth value is the one that does the real work, and it was added after the first
    version of this script failed its own worked example. `7c70cd9` closed `[DB-0808-16]`
    with the subject *"Fix memory race, add clinical thread lifecycle, upgrade output
    filter"* — which names none of it. The evidence that the item was closed is in the
    **added lines**: `read_email` ten times, `danny_park`, `INCONCLUSIVE`. An incidental
    closure is by definition one the commit message does not mention, so matching subjects
    can never find the class this script exists for.
    """
    all_paths = [p for p in _git("diff", "--name-only", rev_range).split() if p]
    paths = {p for p in all_paths if not _is_record(p)}
    code = sorted(paths)
    if not code:
        return set(), set(), set(), ""

    # Restrict the diff to non-record files by name, so an item cannot match its own text.
    diff = _git("diff", "-U0", rev_range, "--", *code)
    symbols = {m for pair in SYMBOL_RE.findall(diff) for m in pair if m}

    added = "\n".join(
        ln[1:] for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")
    ).lower()

    subjects = _git("log", "--format=%s", rev_range).lower()
    words = {w for w in WORD_RE.findall(subjects) if w not in NOISE}

    # Bare filenames and their parent directory: an item says "obligations.py" or "the
    # scheduler", almost never the repo-relative path a diff reports.
    for p in list(paths):
        parts = Path(p).parts
        paths.add(Path(p).name)
        paths.add(Path(p).stem)
        if parts:
            paths.add(parts[0])
    return paths, symbols, words, added


def _sections(text: str) -> str:
    """
    Concatenated bodies of the live sections.

    Matches a heading only when it is the WHOLE line. A substring match splits on the first
    literal "## Now" in the file — which is inside backticks in the Markers prose, hundreds
    of lines above the real heading — and silently returns a few lines of explanation as the
    section body. That is how the first version of this script reported zero candidates
    against a commit that demonstrably closed one.
    """
    lines = text.splitlines()
    out = []
    for heading in LIVE_SECTIONS:
        try:
            start = next(i for i, ln in enumerate(lines) if ln.strip() == heading)
        except StopIteration:
            continue
        end = next(
            (j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
            len(lines),
        )
        out.append("\n".join(lines[start + 1 : end]))
    return "\n".join(out)


def _entries(block: str) -> list[str]:
    """
    Split a section body into top-level entries — one per '- ' bullet plus its indented
    continuation lines. Mirrors `sync_dev_backlog.py._entries()` deliberately: two parsers
    disagreeing about what an item is would be worse than either being imperfect.
    """
    entries: list[str] = []
    current: list[str] = []
    for line in block.splitlines():
        if line.startswith("- ~~"):
            if current:
                entries.append("\n".join(current))
            current = []
        elif line.startswith("- "):
            if current:
                entries.append("\n".join(current))
            current = [line]
        elif current:
            current.append(line)
    if current:
        entries.append("\n".join(current))
    return entries


def score(
    entry: str, paths: set[str], symbols: set[str], words: set[str], added: str
) -> tuple[int, list[str]]:
    """
    Overlap score for one item, with the evidence that produced it.

    Symbols are weighted above paths, and paths above words. An item citing a function the
    diff changed is a much stronger signal than one sharing the word "calendar" with a
    commit subject — and the weighting is what keeps a long, well-documented item from
    outranking a short precise one purely by surface area.
    """
    low = entry.lower()
    hits: list[str] = []
    total = 0

    # Strongest signal: a thing the item names in backticks, appearing in lines the session
    # added. This is what catches an incidental closure — see session_evidence().
    # Only identifier-shaped tokens count. A backtick in this file wraps `mike`, `base`,
    # `name` and `other` as often as it wraps `read_email` — the short bare words match
    # almost any diff and were what kept the report at 42 of ~50 items. Requiring a `_`,
    # `.` or `/`, or real length, keeps the precise citations and drops the vocabulary.
    ticked = {t.lower().rstrip("()") for t in TICKED_RE.findall(entry)}
    ticked = {
        t for t in ticked
        if t not in NOISE and (len(t) >= 8 or any(c in t for c in "_./"))
    }
    matched = sorted(t for t in ticked if t in added)
    # Capped: a long, heavily-quoted item must not outrank a short precise one on volume.
    total += min(len(matched), 3) * 4
    hits.extend(f"added:`{t}`" for t in matched[:4])

    matched_syms = sorted(s for s in symbols if len(s) > 4 and s.lower() in low)
    total += min(len(matched_syms), 3) * 3
    hits.extend(f"symbol:{s}" for s in matched_syms[:3])

    matched_paths = sorted(p for p in paths if len(p) > 3 and p.lower() in low)
    total += min(len(matched_paths), 3) * 2
    hits.extend(f"path:{p}" for p in matched_paths[:3])

    # Weakest signal, and capped hardest. Uncapped it is a length contest: the longest,
    # best-documented items share the most vocabulary with any commit subject and float to
    # the top regardless of relevance — which is the opposite of what a close scan is for.
    entry_words = set(WORD_RE.findall(low)) - NOISE
    shared = sorted(entry_words & words)
    if shared:
        total += min(len(shared), 3)
        hits.append("words:" + ",".join(shared[:4]))

    return total, hits


def title_of(entry: str) -> str:
    """The item's first line, trimmed — enough for a human to recognise it."""
    first = entry.splitlines()[0].lstrip("- ").strip()
    first = re.sub(r"\*\*|`", "", first)
    return first[:110]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--since", default=None, help="git rev or range (default: origin/main..HEAD)")
    ap.add_argument("--min-score", type=int, default=8, help="report threshold (default 4)")
    ap.add_argument("--limit", type=int, default=12, help="max candidates to print")
    args = ap.parse_args()

    if not BACKLOG.exists():
        print(f"backlog-close-scan: {BACKLOG} not found", file=sys.stderr)
        return 1

    rev_range = args.since or _default_range()
    if rev_range and ".." not in rev_range:
        rev_range = f"{rev_range}..HEAD"

    paths, symbols, words, added = session_evidence(rev_range)
    if not paths and not symbols:
        print(f"backlog-close-scan: no diff in {rev_range} — nothing to match against.")
        return 0

    entries = _entries(_sections(BACKLOG.read_text()))
    scored = []
    for entry in entries:
        ids = ID_RE.findall(entry)
        if not ids:
            continue
        total, hits = score(entry, paths, symbols, words, added)
        if total >= args.min_score:
            scored.append((total, ids[0], title_of(entry), hits))

    scored.sort(key=lambda r: -r[0])

    print(f"backlog-close-scan: {rev_range} — {len(paths)} paths, {len(symbols)} symbols")
    if not scored:
        print("  no candidates above threshold. Still read the items you aimed at.")
        return 0

    print(f"  {len(scored)} candidate(s) — OPEN EACH AGAINST THE DIFF. This is evidence, not a verdict.\n")
    for total, item_id, title, hits in scored[: args.limit]:
        print(f"  [{total:>3}] {item_id}  {title}")
        print(f"        {' · '.join(hits[:4])}")
    if len(scored) > args.limit:
        print(f"\n  ({len(scored) - args.limit} more below the cut — rerun with --limit)")

    print(
        "\n  Fully done → move to archive/backlog_closed_YYYY-MM.md with the commit."
        "\n  Partly done → stays open, retitled to state what is left."
        "\n  Untouched → leave it alone. Do not re-word an item because you read it."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
