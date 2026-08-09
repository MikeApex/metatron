#!/usr/bin/env python3
"""
Pull change requests and runtime signals from the VM into DEV_BACKLOG.md.

The Synthesizer records these on the VM, into a gitignored data directory.
Development sessions run on the Mac. This bridges that gap using the server's
existing /monitor/file endpoint over Tailscale — no new server code, no SSH.

Design constraints, all three deliberate:

  * Standard library only. This runs from a Claude Code SessionStart hook, which
    gets no virtualenv.
  * Fails silent, exits 0, always. The VM is routinely stopped for cost control
    (scripts/metatron-pause.sh), so "unreachable" is a normal state, not an
    error. A backlog sync must never block or noise up a development session.
  * Two destinations, not one. What Mike said goes to '## Inbox'; what the
    runtime noticed goes to '## Machine log'. Mixing them is what let five
    copies of one complaint sit alongside a tool denial as if they ranked the
    same. Everything else in the file is hand-curated and never touched.

Usage:  python3 scripts/sync_dev_backlog.py [--persona mike] [--server URL]
"""

import argparse
import json
import re
import subprocess
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

# What Mike asked for, in his own words. These reach '## Inbox' and are the
# only events a routine triage pass looks at.
USER_TYPES = {"FEATURE_REQUEST", "INSTRUCTION_CHANGE_REQUEST"}

# What the runtime noticed about itself. Real signals, but nobody asked for
# them, and they arrive far faster than they are worked. They reach
# '## Machine log', collapsed by signature — see ESCALATE_AT.
MACHINE_TYPES = {"TOOL_DENIED", "RULE_CONFLICT", "SELF_APPLIED"}

WANTED = USER_TYPES | MACHINE_TYPES

# A machine signature seen this many times stops being noise and starts being
# evidence the runtime is failing repeatedly — the point at which a process
# event has become a user-facing problem. It gets a ⚠ in the file and a line in
# the sync output. Three is the threshold because one is an accident and two is
# a coincidence.
ESCALATE_AT = 3

LABELS = {
    "FEATURE_REQUEST": "needs building",
    "INSTRUCTION_CHANGE_REQUEST": "instruction change",
    "SELF_APPLIED": "already applied by the tool",
    # Emitted by dispatch_tool when an agent reaches for a tool it was not
    # granted. The agent instruction files are a specification written ahead of
    # the tools, so an attempt is evidence of designed intent — the signal that
    # says grant it, build it, or drop the instruction.
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

# Anchored to line start with its own newlines: the intro prose mentions these
# headings inline, and a bare substring match finds that first — which would
# splice new entries into the middle of a paragraph.
INBOX_HEADING = "\n## Inbox\n"
NOW_HEADING = "\n## Now\n"
LATER_HEADING = "\n## Later\n"
MACHINE_HEADING = "\n## Machine log\n"
DONE_HEADING = "\n## Done\n"

# A shape, not a literal list: the placeholder has been written at least four
# ways, including a dated form ("*(nothing new — last triaged 2026-08-09)*")
# that no fixed tuple can anticipate. Matching only some spellings leaves a
# stale "nothing new" sitting under a freshly-added entry — which is exactly
# what happened to the tuple this regex replaced.
PLACEHOLDER_RE = re.compile(r"^\*\(nothing[^)]*\)\*\s*$|^\*\(empty\)\*\s*$")

# How alike two user-voice entries must read before the second is treated as a
# repeat rather than a new request. Dice coefficient over content words, not
# difflib.SequenceMatcher — measured against the real 2026-08-07..09 Inbox,
# character-level similarity on those five entries ranged 0.11–0.42, which is
# indistinguishable from noise.
#
# **Know what this does not do.** These entries are the Synthesizer's own
# summaries, written fresh each time, so five restatements of one complaint
# share a topic and almost no phrasing (Dice 0.06–0.34 pairwise — one pair
# scored the same as a completely unrelated calendar request). Measured on the
# real data at this threshold: five check-in-brevity repeats collapse to **two**
# entries, not one, and all four contemporaneous unrelated requests stay
# separate. Chosen for that second property: a wrong merge silently destroys a
# distinct request Mike made, which is strictly worse than showing one complaint
# twice. Lowering it to 0.12 gets three-into-one and buys no false merges on
# this sample, but the margin against future items gets thin.
#
# The reliable dedup is `signature()` on the machine side, which keys on
# structure rather than prose. Human triage in `/backlog` is what actually
# merges the rest — this only takes the top off the pile.
SIMILARITY_THRESHOLD = 0.15

# Words carrying no topic signal. Kept short deliberately: a long stop list
# starts deciding what a request is about.
STOPWORDS = frozenset(
    "the a an is are was were be been being to of in on for and or but it its "
    "this that with as at by from user system must need needs should have has "
    "had not no".split()
)

# Trailing "  ×3" on an entry's first line. Two leading spaces are a markdown
# hard break, so the count must be matched before them, not after.
COUNT_RE = re.compile(r"\s+×(\d+)\s*$")

# TOOL_DENIED details read "`finance` attempted `search_memory` (query) but ...",
# so (agent, tool) is recoverable and is a far better dedup key than the prose,
# which varies with the arguments. Falls back to prose similarity when the
# shape does not match.
DENIAL_RE = re.compile(r"`([a-z_0-9]+)`\s+attempted\s+`([a-z_0-9]+)`")


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


def vm_status() -> str:
    """
    Best-effort GCE instance status ("RUNNING", "STOPPED", ...), or "" on any
    failure (gcloud not installed, no creds, timeout). Same fail-silent posture
    as fetch_events — this is a diagnostic add-on, never a hard dependency.

    Only called when fetch_events() already came back empty, so a healthy VM
    never pays for this extra round-trip on the common path.
    """
    try:
        result = subprocess.run(
            ["gcloud", "compute", "instances", "describe", "metatron-vm",
             "--zone=us-central1-a", "--project=metatron-ai-499810",
             "--format=value(status)"],
            capture_output=True, text=True, timeout=5,
        )
        return result.stdout.strip()
    except Exception:
        return ""


def _section(text: str, heading: str) -> str:
    """
    The body of one '## ' section: everything from its heading to the next one.

    Runs to the next '## ' rather than to a named successor, because sections
    get added and renamed and hardcoding the order is how a split silently
    starts returning the rest of the file.
    """
    after = text.partition(heading)[2]
    if not after:
        return ""
    lines = after.splitlines()
    for i, line in enumerate(lines):
        if line.startswith("## "):
            return "\n".join(lines[:i])
    return after


def _items(block: str) -> int:
    """
    Count top-level entries in a section body.

    Anything indented is a sub-bullet inside an item's body, not an item — hence
    startswith("- ") rather than lstrip().startswith("- "). Struck-through lines
    are skipped: closed items live in archive/backlog_closed_*.md, but one can
    sit here briefly between being closed and being rolled over, and a count
    that rises when work gets done is worse than useless.
    """
    return sum(1 for line in block.splitlines()
               if line.startswith("- ") and not line.startswith("- ~~"))


def count_items(text: str) -> tuple[int, int, int]:
    """
    Return (inbox, now, later) — three different kinds of work, counted apart.

    WHY THIS IS NOT A ONE-LINER, kept from the version it replaced because the
    bug recurred twice. It used to be:

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

    The 2026-08-05 fix caught (1) and (2) and missed a fourth: a line opening
    '- **✅' does not start '- ~~', so three tick-marked closed items counted as
    open for four days. That class of trap is gone by construction now — closed
    items leave the file entirely — but the section-scoped counting below is
    what keeps it gone.
    """
    return (
        _items(_section(text, INBOX_HEADING)),
        _items(_section(text, NOW_HEADING)),
        _items(_section(text, LATER_HEADING)),
    )


def escalated(text: str) -> list[str]:
    """
    Every machine-log entry at or past ESCALATE_AT, read from the file.

    Scanned rather than tracked per run: the docs promise "surfaced in the sync
    output line", and a one-shot alert printed only on the run where the count
    crossed the threshold scrolls past in a SessionStart hook and is never seen
    again. The ⚠ stays in the line until the entry is swept out by a
    `/backlog deep` pass — which is when it has actually been looked at.
    """
    out = []
    for line in _section(text, MACHINE_HEADING).splitlines():
        if not line.startswith("- ⚠"):
            continue
        count = COUNT_RE.search(line)
        tally = f" ×{count.group(1)}" if count else ""
        denial = DENIAL_RE.search(line)
        name = (f"{denial.group(1)}/{denial.group(2)}" if denial
                else _entry_text(line)[:40].rstrip())
        out.append(f"{name}{tally}")
    return out


def signature(event: dict) -> str:
    """
    The dedup key for a machine event: (type, agent, tool) where recoverable.

    A denial's prose carries the arguments, which vary per call, so nine entries
    covering six real cases is the normal shape. Keying on the pair collapses
    them at the source instead of at triage time.
    """
    kind = event.get("event_type", "")
    detail = " ".join(str(event.get("detail", "")).split())
    match = DENIAL_RE.search(detail)
    if match:
        return f"{kind}:{match.group(1)}/{match.group(2)}"
    return f"{kind}:{detail[:80].lower()}"


def _entry_text(line: str) -> str:
    """An entry's comparable prose: label, count and markdown stripped."""
    body = COUNT_RE.sub("", line.lstrip("- ").strip())
    body = re.sub(r"^⚠\s*", "", body)
    body = re.sub(r"^\*\*\[[^\]]*\]\*\*\s*", "", body)
    return re.sub(r"[`*_]", "", body).lower()


def _content_words(text: str) -> set[str]:
    """Topic-bearing words: lowercased, stopped, and short tokens dropped."""
    return {w for w in re.findall(r"[a-z][a-z'-]+", text.lower())
            if w not in STOPWORDS and len(w) > 2}


def similar(a: str, b: str) -> float:
    """
    Dice coefficient over content words — 0.0 to 1.0.

    Dice rather than Jaccard because it weights the shared half more heavily,
    which matters when one entry is a truncated event (the 2026-08-08 Inbox has
    one that stops mid-sentence at "The system must output strictly 'What").
    """
    x, y = _content_words(a), _content_words(b)
    if not x or not y:
        return 0.0
    return 2 * len(x & y) / (len(x) + len(y))


def render(event: dict, count: int = 1) -> str:
    """One backlog bullet. Timestamp is last — it doubles as the dedup key."""
    kind = event.get("event_type", "")
    label = LABELS.get(kind, kind)
    detail = " ".join(str(event.get("detail", "")).split()) or "(no detail recorded)"
    warn = "⚠ " if count >= ESCALATE_AT else ""
    tally = f"  ×{count}" if count > 1 else ""
    return f"- {warn}**[{label}]** {detail}{tally}  \n  `{event.get('timestamp', '')}`"


def merge(block: str, event: dict, machine: bool) -> tuple[str, bool, int]:
    """
    Fold one event into a section body.

    Returns (new_block, was_appended, count). A repeat increments the ×N on the
    entry it matches and refreshes its timestamp rather than adding a bullet —
    the whole point, since five restatements of one complaint are one complaint
    restated five times, and reading them as five items is what made the Inbox
    look like a queue when it was a single unfixed bug.
    """
    lines = block.splitlines()
    incoming = _entry_text(render(event))
    sig = signature(event) if machine else None

    for i, line in enumerate(lines):
        if not line.startswith("- "):
            continue
        if machine:
            # Machine entries carry a stable (agent, tool) key; compare on that
            # when both sides expose one, and fall back to prose otherwise.
            # The prose fallback only runs against a line of the same label —
            # a RULE_CONFLICT and a SELF_APPLIED about the same config key can
            # read alike, and merging across types corrupts both counts.
            existing_sig = None
            match = DENIAL_RE.search(line)
            if match:
                existing_sig = f"{event.get('event_type','')}:{match.group(1)}/{match.group(2)}"
            same_label = f"**[{LABELS.get(event.get('event_type', ''), '')}]**" in line
            alike = (existing_sig == sig) if existing_sig else (
                same_label
                and similar(_entry_text(line), incoming) >= SIMILARITY_THRESHOLD
            )
        else:
            alike = similar(_entry_text(line), incoming) >= SIMILARITY_THRESHOLD
        if not alike:
            continue

        existing = COUNT_RE.search(line)
        count = (int(existing.group(1)) if existing else 1) + 1
        rendered = render(event, count).splitlines()
        lines[i] = rendered[0]
        # Refresh the timestamp line beneath it, so the entry dates from the
        # most recent restatement rather than the first — "still happening as of"
        # is the useful reading.
        if i + 1 < len(lines) and lines[i + 1].strip().startswith("`"):
            lines[i + 1] = rendered[1]
        return "\n".join(lines), False, count

    # No match — insert a new entry, newest first, but *after* the section's
    # italic preamble: prepending at the very top put entries above the text
    # explaining what the section is. Before the first existing bullet if there
    # is one; otherwise before the closing "---"; otherwise at the end.
    kept = [ln for ln in lines if not PLACEHOLDER_RE.match(ln)]
    idx = next((i for i, ln in enumerate(kept) if ln.startswith("- ")), None)
    if idx is None:
        idx = next((i for i, ln in enumerate(kept) if ln.strip() == "---"), len(kept))
    kept[idx:idx] = render(event).splitlines() + [""]
    body = re.sub(r"\n{3,}", "\n\n", "\n".join(kept))
    return body, True, 1


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--persona", default=DEFAULT_PERSONA)
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--quiet", action="store_true", help="print nothing when there is nothing new")
    args = ap.parse_args()

    if not BACKLOG.exists():
        return 0

    text = BACKLOG.read_text()
    if INBOX_HEADING not in text or MACHINE_HEADING not in text:
        return 0

    events = fetch_events(args.server, args.persona)

    # A stopped VM (routine, cost control) and a running-but-unreachable VM
    # (an outage) both surface here as "no events" — indistinguishable without
    # asking GCE directly. Only ask when the happy path already came back
    # empty, so a healthy VM never pays for the extra round-trip.
    vm_warning = ""
    if not events and vm_status() == "RUNNING":
        vm_warning = " · ⚠ VM running but unreachable"

    seen = set(SEEN.read_text().split()) if SEEN.exists() else set()
    # First run against an existing backlog: adopt whatever is already written in
    # rather than re-adding every historical event as "new".
    if not SEEN.exists():
        seen = {str(e.get("timestamp", "")) for e in events if str(e.get("timestamp", "")) in text}

    new = [e for e in events if (ts := str(e.get("timestamp", ""))) and ts not in seen]

    added = 0
    if new:
        seen.update(str(e.get("timestamp", "")) for e in new)
        SEEN.write_text("\n".join(sorted(seen)) + "\n")

        for event in new:
            machine = event.get("event_type") in MACHINE_TYPES
            heading = MACHINE_HEADING if machine else INBOX_HEADING
            head, _, tail = text.partition(heading)
            block = _section(text, heading)
            rest = tail[len(block):]
            merged, appended, _count = merge(block, event, machine)
            text = f"{head}{heading}{merged}{rest}"
            if appended:
                added += 1

        BACKLOG.write_text(text)

    inbox, now, later = count_items(text)
    escalations = escalated(text)
    alert = f" · ⚠ machine: {', '.join(escalations)}" if escalations else ""
    if new or not args.quiet or vm_warning:
        print(f"DEV_BACKLOG.md: {added} new · {inbox} inbox · {now} now · "
              f"{later} later{alert}{vm_warning}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never let a backlog sync break a session start.
        sys.exit(0)
