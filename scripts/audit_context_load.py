#!/usr/bin/env python3
"""
Audit what a Claude Code session actually loaded into context.

Written 2026-08-03 alongside the context-file split, to answer with evidence what
would otherwise be guesswork: does `/metatron-code` load what it is supposed to,
does it load anything it shouldn't, and did the session need a file that is no
longer in the default set?

Usage (from the project root):

    python3 scripts/audit_context_load.py                 # most recent session
    python3 scripts/audit_context_load.py --list          # pick from recent sessions
    python3 scripts/audit_context_load.py <session-id>    # a specific one
    python3 scripts/audit_context_load.py --exclude-self  # ignore the session running this

Reads only ~/.claude/projects/<slug>/*.jsonl. Writes nothing.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# What the split expects. Update these when the context architecture changes.
# ---------------------------------------------------------------------------

EXPECTED = {                      # /metatron-code should read these
    "SESSION.md":        "current state",
    "ROADMAP.md":        "abridged live roadmap",
    "DEV_BACKLOG.md":    "outstanding work",
}
CONDITIONAL = {
    "CODEBASE_INDEX.md": "only when locating a file/tool/plan",
}
DO_NOT_READ_BY_DEFAULT = {        # deliberately outside the default load
    "archive/PROJECT_LOG.md":  "dated history — consult deliberately",
    "docs/INFRASTRUCTURE.md":  "deploy/recovery — consult when deploying",
}
SUPERSEDED = {                    # reading these means the anchor parse broke
    "archive/plans/phase5_to_future_roadmap_2026-06-10.md":
        "the FULL static plan — /metatron-code should load ROADMAP.md instead",
}


def project_root() -> Path:
    try:
        out = subprocess.run(["git", "rev-parse", "--show-toplevel"],
                             capture_output=True, text=True, check=True)
        return Path(out.stdout.strip())
    except (subprocess.CalledProcessError, FileNotFoundError):
        return Path.cwd()


def jsonl_dir(root: Path) -> Path:
    return Path.home() / ".claude" / "projects" / str(root).replace("/", "-")


def load_events(path: Path) -> list[dict]:
    events = []
    with open(path, errors="replace") as fh:
        for line in fh:
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return events


def reads_and_prompts(events: list[dict], root: Path):
    """Return (ordered file reads, user prompts, ran_metatron_code)."""
    reads: list[str] = []
    prompts: list[str] = []
    ran_cmd = False

    for ev in events:
        msg = ev.get("message") or {}
        content = msg.get("content")

        if msg.get("role") == "user" and isinstance(content, str):
            text = content.strip()
            if text and not text.startswith("<"):
                prompts.append(text)
                if "metatron-code" in text:
                    ran_cmd = True

        if not isinstance(content, list):
            continue
        for blk in content:
            if not isinstance(blk, dict):
                continue
            if blk.get("type") == "text" and msg.get("role") == "user":
                text = str(blk.get("text", "")).strip()
                # Skip system-injected blocks — they are not what the human typed.
                if text and not text.startswith("<"):
                    prompts.append(text)
                if "metatron-code" in text:
                    ran_cmd = True
            if blk.get("type") != "tool_use":
                continue
            name = blk.get("name")
            inp = blk.get("input") or {}
            fp = None
            if name == "Read":
                fp = inp.get("file_path")
            elif name == "Bash":
                cmd = str(inp.get("command", ""))
                if "metatron-code" in cmd:
                    ran_cmd = True
            if fp:
                try:
                    rel = str(Path(fp).resolve().relative_to(root))
                except ValueError:
                    rel = fp
                reads.append(rel)
    return reads, prompts, ran_cmd


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("session", nargs="?", help="session id (uuid), default = most recent")
    ap.add_argument("--list", action="store_true", help="list recent sessions and exit")
    ap.add_argument("--exclude-self", action="store_true",
                    help="skip the session that is running this script")
    args = ap.parse_args()

    root = project_root()
    src = jsonl_dir(root)
    if not src.is_dir():
        print(f"No transcripts at {src}", file=sys.stderr)
        return 1

    files = sorted(src.glob("*.jsonl"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("No sessions found.", file=sys.stderr)
        return 1

    if args.list:
        print(f"Recent sessions in {src}:\n")
        for p in files[:12]:
            ts = datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
            print(f"  {ts}  {p.stem}  ({p.stat().st_size // 1024} KB)")
        return 0

    if args.session:
        match = [p for p in files if p.stem.startswith(args.session)]
        if not match:
            print(f"No session matching {args.session!r}", file=sys.stderr)
            return 1
        target = match[0]
    else:
        self_id = os.environ.get("CLAUDE_SESSION_ID", "")
        cands = [p for p in files if not (args.exclude_self and p.stem == self_id)]
        target = cands[0]

    events = load_events(target)
    reads, prompts, ran_cmd = reads_and_prompts(events, root)
    uniq = list(dict.fromkeys(reads))

    ts = datetime.fromtimestamp(target.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    print("=" * 74)
    print(f"CONTEXT LOAD AUDIT   session {target.stem[:8]}   last active {ts}")
    print("=" * 74)
    print(f"\n  {len(prompts)} user prompts · {len(reads)} file reads "
          f"({len(uniq)} distinct) · /metatron-code invoked: "
          f"{'yes' if ran_cmd else 'NO'}")

    if not ran_cmd:
        print("\n  ⚠  No /metatron-code invocation detected — the checks below only")
        print("     mean something for a session that ran it.")

    total = 0
    print("\n── 1. Expected files ─────────────────────────────────────────────")
    for f, why in EXPECTED.items():
        hit = f in uniq
        size = (root / f).stat().st_size if (root / f).exists() else 0
        if hit:
            total += size
        print(f"  {'✓' if hit else '✗'} {f:<26} {size:>7,} B   {why}")

    print("\n── 2. Conditional ────────────────────────────────────────────────")
    for f, why in CONDITIONAL.items():
        hit = f in uniq
        size = (root / f).stat().st_size if (root / f).exists() else 0
        if hit:
            total += size
        print(f"  {'read' if hit else 'skipped':<7} {f:<26} {size:>7,} B   {why}")

    print("\n── 3. Should NOT be in the default load ──────────────────────────")
    any_bad = False
    for f, why in SUPERSEDED.items():
        if f in uniq:
            any_bad = True
            print(f"  ✗ ANCHOR PARSE LIKELY BROKEN — read {f}")
            print(f"    {why}")
    if not any_bad:
        print("  ✓ superseded/static plan not loaded")

    print("\n── 4. Consulted deliberately (fine — shows the pointers work) ─────")
    for f, why in DO_NOT_READ_BY_DEFAULT.items():
        if f in uniq:
            print(f"  · {f} — consulted. {why}")
    if not any(f in uniq for f in DO_NOT_READ_BY_DEFAULT):
        print("  (neither consulted this session)")

    print(f"\n── 5. Measured load ──────────────────────────────────────────────")
    print(f"  {total:,} bytes ≈ {total // 4000}k tokens across the files above")
    print(f"  (pre-split baseline was 350,663 B ≈ 87k tokens)")

    other = [f for f in uniq
             if f not in EXPECTED and f not in CONDITIONAL
             and f not in DO_NOT_READ_BY_DEFAULT and f not in SUPERSEDED]
    if other:
        print("\n── 6. Everything else the session read ───────────────────────────")
        print("  Look for a file it had to go find because the default set didn't")
        print("  answer the question — that is content to consider putting back.\n")
        for f in other[:30]:
            print(f"    {f}")
        if len(other) > 30:
            print(f"    … and {len(other) - 30} more")

    if prompts:
        print("\n── 7. What was asked ─────────────────────────────────────────────")
        for p in prompts[:12]:
            one = " ".join(p.split())
            print(f"    · {one[:88]}{'…' if len(one) > 88 else ''}")

    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
