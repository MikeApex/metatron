#!/usr/bin/env python3
"""Generate archive/PROJECT_LOG.md from fragments in archive/log/.

WHY THIS EXISTS
---------------
PROJECT_LOG.md is append-only and two sessions still collide in it, because both
append at the *top* of a newest-first file and land on the same lines. Append-only
is not the property that saves you; "one file per write" is. Unique filenames
cannot collide, so two windows closing out at once produce two fragments rather
than one conflict.

WHAT IS AND IS NOT A FRAGMENT
-----------------------------
Everything dated 2026-08-13 and earlier lives frozen in `_history.md`, as one
blob, byte-for-byte as it was.

That is a deliberate deviation from the plan, which called for splitting the whole
file into one fragment per entry. The split is not mechanically reliable: of 93
`###` headings only 44 are date-prefixed, entry headings and sub-headings *within*
entries are both H3 and nothing distinguishes them (`### Deploy verification —
2026-08-03` is a sub-heading; `### Also done 2026-08-03 (...)` is an entry), and
there are two separate `## Dated history` sections. Splitting on `^### ` shreds
entries; splitting on `^### 2026` misses half of them.

The migration buys nothing, either: historical entries are never edited again, so
they never collide. All the collision risk is in *new* entries. Freezing the
history and fragmenting only what comes next gets the whole benefit at none of the
risk — and makes the result provable, which a heuristic split never could be:

    python3 scripts/build_project_log.py --check

with no new fragments must reproduce the file byte-for-byte.

FRAGMENT NAMING
---------------
    archive/log/YYYY-MM-DD-NN-slug.md

`NN` is an optional two-digit sequence for multiple sessions on one day. Higher NN
sorts as *later on that day* and therefore appears *above* lower NN in the
newest-first output. Omit it and it reads as 00.

The filename is the collision control. Two windows closing out on the same day
must not pick the same name -- include enough slug to be distinct, which is the
same discipline that stops two windows reserving one backlog ID.

USAGE
-----
    python3 scripts/build_project_log.py            # regenerate the flat file
    python3 scripts/build_project_log.py --check    # verify, change nothing
    python3 scripts/build_project_log.py --init     # one-shot: seed from the
                                                    # existing flat file
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "archive" / "log"
FLAT = ROOT / "archive" / "PROJECT_LOG.md"

PREAMBLE = LOG_DIR / "_preamble.md"
HISTORY = LOG_DIR / "_history.md"

# Fragments are date-led. The leading digit keeps them clear of the underscore
# files, which are structural rather than entries.
FRAGMENT_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2})(?:-(\d{2}))?-(.+)\.md$")

# The line that ends the preamble in the current flat file. Used only by --init.
DATED_HISTORY_MARKER = "## Dated history"


def fragment_sort_key(path: Path):
    """Newest first: date descending, then sequence descending.

    Sorting on the parsed date rather than the raw string matters because a
    fragment may or may not carry the NN sequence, and a plain string sort would
    put `2026-08-13-worktrees.md` and `2026-08-13-05-worktrees.md` in an order
    that depends on where the hyphen falls rather than on when they happened.
    """
    m = FRAGMENT_RE.match(path.name)
    if not m:
        raise ValueError(f"not a fragment name: {path.name}")
    year, month, day, seq, slug = m.groups()
    return (-int(year), -int(month), -int(day), -int(seq or 0), slug)


def collect_fragments() -> list[Path]:
    if not LOG_DIR.is_dir():
        return []
    frags = [p for p in LOG_DIR.iterdir() if FRAGMENT_RE.match(p.name)]
    return sorted(frags, key=fragment_sort_key)


def render() -> str:
    missing = [p for p in (PREAMBLE, HISTORY) if not p.is_file()]
    if missing:
        names = ", ".join(str(p.relative_to(ROOT)) for p in missing)
        raise SystemExit(
            f"error: missing structural file(s): {names}\n"
            f"  run `python3 scripts/build_project_log.py --init` once to seed them\n"
            f"  from the existing {FLAT.relative_to(ROOT)}."
        )

    parts = [PREAMBLE.read_text(encoding="utf-8")]

    for frag in collect_fragments():
        text = frag.read_text(encoding="utf-8")
        # Fragments are concatenated verbatim. Each is responsible for its own
        # trailing blank line; normalising here would mean the --check guarantee
        # depended on this function's whitespace opinions rather than on the
        # files, and a byte-comparison that quietly rewrites bytes is not one.
        parts.append(text)
        if not text.endswith("\n"):
            parts.append("\n")

    parts.append(HISTORY.read_text(encoding="utf-8"))
    return "".join(parts)


def cmd_init() -> int:
    """Seed _preamble.md and _history.md from the existing flat file.

    One-shot. Refuses to clobber an existing split, because re-running this after
    fragments have accumulated would fold them into the frozen history and they
    would then appear twice.
    """
    if PREAMBLE.exists() or HISTORY.exists():
        print(
            f"error: {PREAMBLE.relative_to(ROOT)} or {HISTORY.relative_to(ROOT)}"
            " already exists.\n"
            "  --init is a one-shot seed and will not overwrite. If you genuinely"
            " need to\n"
            "  re-seed, move the existing files aside first and check whether any"
            " fragments\n"
            "  would be duplicated into the history.",
            file=sys.stderr,
        )
        return 1

    if not FLAT.is_file():
        print(f"error: {FLAT.relative_to(ROOT)} not found.", file=sys.stderr)
        return 1

    text = FLAT.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)

    idx = next(
        (i for i, ln in enumerate(lines) if ln.rstrip("\n") == DATED_HISTORY_MARKER),
        None,
    )
    if idx is None:
        print(
            f"error: no '{DATED_HISTORY_MARKER}' line in {FLAT.relative_to(ROOT)};"
            " cannot find the preamble boundary.",
            file=sys.stderr,
        )
        return 1

    # The preamble keeps the marker itself and any blank line after it, so that
    # concatenation needs no separator logic at all.
    cut = idx + 1
    while cut < len(lines) and lines[cut].strip() == "":
        cut += 1

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    PREAMBLE.write_text("".join(lines[:cut]), encoding="utf-8")
    HISTORY.write_text("".join(lines[cut:]), encoding="utf-8")

    print(f"  seeded   {PREAMBLE.relative_to(ROOT)}  ({cut} lines)")
    print(f"  seeded   {HISTORY.relative_to(ROOT)}  ({len(lines) - cut} lines)")
    print()
    print("Now verify the split is lossless:")
    print("  python3 scripts/build_project_log.py --check")
    return 0


def cmd_check() -> int:
    built = render()
    current = FLAT.read_text(encoding="utf-8") if FLAT.is_file() else ""

    if built == current:
        n = len(collect_fragments())
        print(f"PROJECT_LOG.md is current — {n} fragment(s) + frozen history.")
        return 0

    print(
        f"DRIFT: {FLAT.relative_to(ROOT)} does not match its fragments.",
        file=sys.stderr,
    )
    print(file=sys.stderr)
    print(
        "  Someone edited the generated file by hand, or a fragment changed and"
        " the\n"
        "  file was not rebuilt. The fragments are the source of truth:\n"
        "    python3 scripts/build_project_log.py\n"
        "  If the hand edit is the version you want, move it into the relevant"
        " fragment\n"
        "  first — a rebuild will discard it.",
        file=sys.stderr,
    )

    import difflib

    diff = difflib.unified_diff(
        current.splitlines(keepends=True),
        built.splitlines(keepends=True),
        fromfile="on-disk PROJECT_LOG.md",
        tofile="rebuilt from fragments",
        n=1,
    )
    sys.stderr.writelines(list(diff)[:60])
    return 1


def cmd_build() -> int:
    built = render()
    if FLAT.is_file() and FLAT.read_text(encoding="utf-8") == built:
        print(f"PROJECT_LOG.md already current — {len(collect_fragments())} fragment(s).")
        return 0
    FLAT.write_text(built, encoding="utf-8")
    frags = collect_fragments()
    print(f"Wrote {FLAT.relative_to(ROOT)} — {len(frags)} fragment(s) + frozen history.")
    for f in frags:
        print(f"  {f.name}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Generate archive/PROJECT_LOG.md from archive/log/ fragments."
    )
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--check", action="store_true", help="verify only; change nothing")
    g.add_argument("--init", action="store_true", help="one-shot seed from the flat file")
    args = ap.parse_args()

    if args.init:
        return cmd_init()
    if args.check:
        return cmd_check()
    return cmd_build()


if __name__ == "__main__":
    sys.exit(main())
