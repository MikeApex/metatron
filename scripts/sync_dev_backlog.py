#!/usr/bin/env python3
"""
Pull user-reported change requests from the VM into DEV_BACKLOG.md.

The Synthesizer records requests on the VM, into a gitignored data directory.
Development sessions run on the Mac. This bridges that gap using the server's
existing /monitor/file endpoint over Tailscale — no new server code, no SSH.

Design constraints, both deliberate:

  * Standard library only. This runs from a Claude Code SessionStart hook, which
    gets no virtualenv.
  * Fails silent, exits 0, always. The VM is routinely stopped for cost control
    (scripts/metatron-pause.sh), so "unreachable" is a normal state, not an
    error. A backlog sync must never block or noise up a development session.

Only '## Inbox' is written. Everything below it is hand-curated and never touched.

Usage:  python3 scripts/sync_dev_backlog.py [--persona mike] [--server URL]
"""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

# HTTPS, and the Tailscale hostname rather than the raw IP: the server runs
# behind a Tailscale-issued cert, so the IP form fails hostname verification.
# This matches the orchestrator CLI's own --server default.
DEFAULT_SERVER = "https://metatron-vm.tail0acc5d.ts.net:8001"
DEFAULT_PERSONA = "mike"
TIMEOUT_SECONDS = 3

# The self-improvement stream carries ROUTING_MISS / USER_CORRECTION too; those
# are for the Pattern Miner health pass, not for a human backlog. Filter here so
# nothing extra has to be built on the writing side.
WANTED = {"SELF_APPLIED", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST",
          "TOOL_DENIED", "RULE_CONFLICT"}

LABELS = {
    "FEATURE_REQUEST": "needs building",
    "INSTRUCTION_CHANGE_REQUEST": "instruction change",
    "SELF_APPLIED": "already applied by the tool",
    # Emitted by dispatch_tool when an agent reaches for a tool it was not
    # granted. The agent instruction files are a specification written ahead of
    # the tools, so an attempt is evidence of designed intent — the signal that
    # says grant it, build it, or drop the instruction. Deduplicated per
    # (agent, tool) at the source.
    "TOOL_DENIED": "agent wanted a tool it lacks",
    # From the daily rule audit: a stated preference that appears to restate a
    # rule already in force. Nobody asked for these — they are the sweep finding
    # its own work, which is why they belong in a development backlog and never
    # in front of the user.
    "RULE_CONFLICT": "same rule in two places",
}

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "DEV_BACKLOG.md"

# Which events have already been pulled. A separate ledger, not a scan of the
# markdown: keying off "does this timestamp appear in the file" means an entry
# resurfaces the moment it is curated out of Inbox — resolved items would come
# back forever, and rewording one would duplicate it.
SEEN = ROOT / ".dev_backlog_seen"
# Anchored to line start with its own newlines: the intro prose mentions
# "## Inbox" inline, and a bare substring match finds that first — which would
# splice new entries into the middle of a paragraph.
INBOX_HEADING = "\n## Inbox\n"
DONE_HEADING = "\n## Done\n"
# Both spellings have been in the file. Matching only one leaves a stale
# placeholder sitting in the middle of a populated Inbox forever.
INBOX_PLACEHOLDERS = ("*(nothing yet)*", "*(nothing new)*")


def _auth_header() -> dict:
    """
    Mint a short-lived bearer token for /monitor/file.

    The endpoint requires authentication as of 2026-08-03. This script holds the same
    password the server does (both read .env), and the signing key derives from it, so
    the token is minted locally rather than by calling /auth/login.

    core.auth is stdlib-only by design, which is what keeps this script's
    standard-library-only constraint intact. Returns {} if the password is not set —
    consistent with this script's fail-silent contract; the request then 401s and the
    caller treats it like any other unreachable-VM case.
    """
    sys.path.insert(0, str(Path(__file__).parent.parent))
    try:
        from core.auth import bearer_header
        return bearer_header(ttl_seconds=300)
    except Exception:
        return {}


def fetch_events(server: str, persona: str) -> list[dict]:
    """Fetch and parse the persona's quality event log. Returns [] on any failure."""
    path = f"data/personas/{persona}/logs/quality_events.json"
    url = f"{server.rstrip('/')}/monitor/file?{urllib.parse.urlencode({'path': path})}"
    try:
        req = urllib.request.Request(url, headers=_auth_header())
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, OSError, ValueError, json.JSONDecodeError):
        return []

    content = payload.get("content", "")
    if not isinstance(content, str):
        return []

    # JSON Lines, but /monitor/file pretty-prints anything ending in .json. If it
    # did, the whole body is one re-serialized blob rather than one object a line.
    events = []
    for line in content.splitlines():
        line = line.strip().rstrip(",")
        if not line.startswith("{"):
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and "event_type" in obj:
            events.append(obj)

    if not events:
        try:
            blob = json.loads(content)
            events = blob if isinstance(blob, list) else [blob]
        except json.JSONDecodeError:
            pass

    return [e for e in events if isinstance(e, dict) and e.get("event_type") in WANTED]


def count_items(text: str) -> tuple[int, int]:
    """
    Return (untriaged, open) — two different kinds of work, counted separately.

    WHY THIS IS NOT A ONE-LINER. It used to be:

        live = text.partition(INBOX_HEADING)[2].partition(DONE_HEADING)[0]
        open_count = sum(1 for line in live.splitlines() if line.startswith("- "))

    which was wrong three ways at once, and reported 48 then 62 in the same
    session on 2026-08-05 while nothing was filed:

      1. DEV_BACKLOG.md had no '## Done' heading, so partitioning on it returned
         the whole rest of the file. "Live region" meant Inbox to EOF.
      2. Struck-through entries (- ~~closed~~) still start with '- ', so
         **closing an item made the number go up**. The count drifted upward as
         work got done, which is the opposite of what it is for.
      3. Untriaged Inbox entries were folded in with curated items, so a pile of
         machine-written denials read as a growing engineering backlog.

    Anything indented is a sub-bullet inside an item's body, not an item — hence
    startswith("- ") rather than lstrip().startswith("- ").
    """
    def _items(block: str) -> int:
        return sum(1 for line in block.splitlines()
                   if line.startswith("- ") and not line.startswith("- ~~"))

    after_inbox = text.partition(INBOX_HEADING)[2]
    if not after_inbox:
        return 0, 0

    # Inbox runs to the next '## ' heading, whatever it is — sections get added
    # and renamed, and hardcoding the successor would silently break the split.
    inbox_block = after_inbox
    for i, line in enumerate(after_inbox.splitlines()):
        if line.startswith("## "):
            inbox_block = "\n".join(after_inbox.splitlines()[:i])
            break

    curated = after_inbox[len(inbox_block):].partition(DONE_HEADING)[0]
    return _items(inbox_block), _items(curated)


def render(event: dict) -> str:
    """One backlog bullet. Timestamp is last — it doubles as the dedup key."""
    kind = event.get("event_type", "")
    label = LABELS.get(kind, kind)
    detail = " ".join(str(event.get("detail", "")).split()) or "(no detail recorded)"
    return f"- **[{label}]** {detail}  \n  `{event.get('timestamp', '')}`"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--persona", default=DEFAULT_PERSONA)
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--quiet", action="store_true", help="print nothing when there is nothing new")
    args = ap.parse_args()

    if not BACKLOG.exists():
        return 0

    text = BACKLOG.read_text()
    if INBOX_HEADING not in text:
        return 0

    events = fetch_events(args.server, args.persona)

    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    # First run against an existing backlog: adopt whatever is already written in
    # rather than re-adding every historical event as "new".
    if not SEEN.exists():
        seen = {str(e.get("timestamp", "")) for e in events if str(e.get("timestamp", "")) in text}

    new = [
        e for e in events
        if (ts := str(e.get("timestamp", ""))) and ts not in seen
    ]

    if new:
        seen.update(str(e.get("timestamp", "")) for e in new)
        SEEN.write_text("\n".join(sorted(seen)) + "\n")

        head, _, tail = text.partition(INBOX_HEADING)
        body = tail
        for placeholder in INBOX_PLACEHOLDERS:
            body = body.replace(f"\n{placeholder}\n", "\n", 1)
        block = "\n".join(render(e) for e in new)
        text = f"{head}{INBOX_HEADING}\n{block}\n\n{body.lstrip(chr(10))}"
        BACKLOG.write_text(text)

    untriaged, open_count = count_items(text)
    if new or not args.quiet:
        print(f"DEV_BACKLOG.md: {len(new)} new · {untriaged} untriaged · {open_count} open")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never let a backlog sync break a session start.
        sys.exit(0)
