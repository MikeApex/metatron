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
from datetime import date
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
#
# USER_CORRECTION and CALENDAR_DUPLICATE landed here 2026-08-15 ([DB-0810-09]),
# closing the gap where write_quality_event emitted them and nothing collected
# them — 158 events, 139 of them USER_CORRECTION, silently discarded before
# this. CALENDAR_DUPLICATE gets a stable uid-pair signature() below, same
# precedent as DENIAL_RE, so distinct duplicate pairs do not collapse into one
# entry on prose alone. USER_CORRECTION does not: [DB-0810-09] itself flags
# that Machine log's per-entry, prose-collapsed shape may be the wrong home for
# 139/day of these (it suggested a digest or a dedicated section instead) —
# that redesign needs a new DEV_BACKLOG.md heading, out of scope for this pass,
# which only had to stop the silent drop. Revisit if Machine log volume from
# this type alone becomes the noise problem the item predicted.
MACHINE_TYPES = {"TOOL_DENIED", "RULE_CONFLICT", "SELF_APPLIED", "UNGROUNDED_ANSWER",
                 "MODEL_CALL_FAILED", "USER_CORRECTION", "CALENDAR_DUPLICATE",
                 "CONTEXT_BLOCK_UNPARSED",
                 # Marked dead 2026-08-13 ([DB-0810-09]) on a grep of core/ and tools/
                 # only — the emitter is not Python. The Synthesizer calls the
                 # registered write_quality_event tool at runtime per instructions in
                 # config/agents/synthesizer.md (8 call sites); 5 ROUTING_MISS events
                 # landed on the live VM since 08-11 while this set called the type
                 # dead. Restored to WANTED 2026-08-27 ([DB-0827-05]). Lesson: a type
                 # is only dead when neither Python code nor an agent instruction file
                 # under config/agents/*.md emits it — grep both before naming one here.
                 "ROUTING_MISS",
                 # Emitted by the false-action-claim detector, 2026-08-27.
                 "FALSE_ACTION_CLAIM"}

WANTED = USER_TYPES | MACHINE_TYPES

# A type belongs here only when a grep of BOTH core/Python (write_quality_event call
# sites) AND every config/agents/*.md instruction file turns up no emitter — the
# 2026-08-13 pass checked only the former, declared ROUTING_MISS dead, and 5 events
# were silently discarded on the live VM before the gap was caught ([DB-0827-05]).
# Nothing lives here today. Do not add a type on the strength of a code-only grep;
# do not delete this comment either, it is the record that the lesson was learned.
KNOWN_DEAD_TYPES = set()

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
    # Research answered with no search queries issued and no sources retrieved. One is
    # unremarkable — plenty of questions do not need the web. A recurring signature is
    # the thing to look at: it means an agent that is supposed to be checking the world
    # has stopped doing so, which is invisible from the answer itself.
    "UNGROUNDED_ANSWER": "answered without retrieving anything",
    # A model API call that failed outright, tagged with the loop that made it.
    # One is weather. A repeating signature is a code path that cannot complete
    # a turn — the user sees an error and the exchange is never recorded, which
    # is invisible from the conversation log precisely because nothing was written.
    "MODEL_CALL_FAILED": "a model call failed outright",
    # The user re-stated or corrected a prior turn. By volume the largest signal
    # in the events file — see the MACHINE_TYPES comment above for why it lands
    # here rather than a dedicated section, for now.
    "USER_CORRECTION": "user corrected a prior turn",
    # From the calendar audit: two events that look like the same thing twice.
    # Application-level dedup already suppresses a uid pair once seen
    # (tools/calendar_audit.py's .calendar_dedup_seen ledger); signature() below
    # gives distinct pairs a stable key so they don't also collapse into each
    # other here on prose alone.
    "CALENDAR_DUPLICATE": "possible duplicate calendar entries",
    # A [CONTEXT] block from the Synthesizer that survived neither parsing nor
    # repair — found by building the reconciliation test for [DB-0810-09], not
    # named in the item itself. _record_unparsed_context()'s own docstring in
    # core/orchestrator.py claims this "already reaches DEV_BACKLOG.md via the
    # existing sync"; it did not until this line. Carries the raw block, so a
    # dropped context-tracker update is now recoverable instead of just logged.
    "CONTEXT_BLOCK_UNPARSED": "a [CONTEXT] block was dropped, unrecovered",
    # From the Synthesizer's own context-tracker note: a signal in the original
    # message that no specialist surfaced. Restored to WANTED 2026-08-27
    # ([DB-0827-05]) after being wrongly classed dead — see MACHINE_TYPES above.
    "ROUTING_MISS": "a specialist missed a signal it should have caught",
    # From the false-action-claim detector, 2026-08-27: the runtime told the user
    # an action happened (sent, scheduled, saved) that the logs show never did.
    "FALSE_ACTION_CLAIM": "the runtime claimed an action it didn't take",
}

ROOT = Path(__file__).resolve().parent.parent
BACKLOG = ROOT / "DEV_BACKLOG.md"
# One file per filed item, folded into '## Inbox' on each sync. See
# fold_fragments() for why this is a directory rather than a hand-edited section.
INBOX_FRAGMENTS = ROOT / ".claude" / "backlog_inbox"

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
# 0.15 -> 0.45 on 2026-08-15 (Mike's call, [DB-0815-09]).
#
# At 0.15 with Dice over content words, two entries merged on ~15% shared words — and
# because `merge()` REPLACES the displayed line with the newest member's text, matching
# is against the last link rather than the original. Adjacent pairs each cleared 0.15
# while the endpoints were unrelated, so clusters drifted:
#
#   "the impossibility of having [done X] in the timeline"      08-01  <- chain starts
#   "multiple rail options exist for Heathrow"                  08-04
#   "their Heathrow departure was today, August 5th"            08-05
#   "the calendar event for the Horatiu Stefan meeting"         08-06
#   "scheduled calendar events imply completion"                08-12  <- headline
#
# All sixteen were reported to Mike as one signature. A ×N is therefore a CHAIN LENGTH,
# not a repeat count — and the ×3 machine-promotion bar is read off exactly these counts.
#
# Two changes together, and both are needed: this threshold, and the correction-boilerplate
# stopwords above. Raising the threshold alone would not have split that chain, because the
# shared words WERE the correction vocabulary; stopping the boilerplate alone would not
# either, because 0.15 is low enough for two topic words to clear it by accident.
SIMILARITY_THRESHOLD = 0.45

# Words carrying no topic signal. Kept short deliberately: a long stop list
# starts deciding what a request is about.
STOPWORDS = frozenset(
    "the a an is are was were be been being to of in on for and or but it its "
    "this that with as at by from user system must need needs should have has "
    "had not no "
    # [DB-0815-09] Correction *boilerplate*, added 2026-08-15 (Mike's call). Every
    # USER_CORRECTION detail is phrased "the user corrected the system's assumption
    # that ...", so these words are present in nearly all of them and carried most of
    # the similarity score — meaning entries merged on the fact that both were
    # corrections, not on what either was about. That is how a chain of Heathrow
    # travel corrections ended up filed under "scheduled calendar events imply
    # completion ×16". Dropping them leaves the score to run on topic words only.
    "corrected correcting correction corrects clarified clarifying clarification "
    "assumption assumed assuming previously prior previous stated stating restated "
    "noting noted note requested requesting request confirming confirmed "
    "instead rather actually turn message response".split()
)

# Trailing "  ×3" on an entry's first line. Two leading spaces are a markdown
# hard break, so the count must be matched before them, not after.
COUNT_RE = re.compile(r"\s+×(\d+)\s*$")

# The due-date marker convention this script defines ([DB-0813-01] — nothing
# machine-parseable existed before). Written inline in an item's own text as
# "due: YYYY-MM-DD". Anchored on "due:" *with the colon* so it never matches a
# prose date ("due 2026-08-11, do not check before then" — the exact case that
# went unread for two days and is why this exists) or the "*filed 2026-08-13 by
# ...*" footer every item carries; neither has a colon after "due".
DUE_RE = re.compile(r"\bdue:\s*(\d{4}-\d{2}-\d{2})\b")


# [DB-0815-09] Deliberate second copy of tools/logger.py's is_null_ish(), which is the
# canonical one. This script is STDLIB-ONLY by design — that constraint is what lets it run
# from a SessionStart hook with no venv — and importing tools.logger would pull in
# core.persona and core.background. The rule this bends is "One Home Per Rule Class"
# (.claude/rules/agent-files.md), so the exception is named rather than silent: if the
# forms change, change both. tests/test_null_ish_events.py asserts the two agree, so a
# drift fails a test rather than going unnoticed.
_NULL_ISH = {
    "none", "n/a", "na", "null", "nil", "nothing", "no correction", "not applicable",
    "no corrections", "-", "--", "—", "[none]", "[n/a]", "()", "[]",
}


def _is_null_ish(text: str) -> bool:
    """True when `text` is a model's way of saying "this field does not apply"."""
    stripped = (text or "").strip().strip("[](){}\"'").strip().rstrip(".!?").strip().lower()
    if not stripped:
        return True
    if stripped in _NULL_ISH:
        return True
    return any(stripped.startswith(f"{tag} -") or stripped.startswith(f"{tag} —")
               for tag in ("n/a", "na", "none"))

# An item's own id, e.g. "[DB-0809-02]". Used to name what's due in the count
# line rather than quoting the whole entry.
ID_RE = re.compile(r"\[DB-\d{4}-\d{2}\]")

# TOOL_DENIED details read "`finance` attempted `search_memory` (query) but ...",
# so (agent, tool) is recoverable and is a far better dedup key than the prose,
# which varies with the arguments. Falls back to prose similarity when the
# shape does not match.
DENIAL_RE = re.compile(r"`([a-z_0-9]+)`\s+attempted\s+`([a-z_0-9]+)`")

# CALENDAR_DUPLICATE details read "...'<title>' (<start>, uid=<uid1>) and
# '<title>' (<start>, uid=<uid2>). title_similarity=..." (tools/calendar_audit.py
# _detail()) — almost all of that is shared boilerplate across every finding, so
# the uid pair, not the prose, is what tells two distinct duplicate pairs apart.
# Same precedent as DENIAL_RE: without this, SIMILARITY_THRESHOLD's prose
# fallback would collapse unrelated pairs that merely share the boilerplate
# wording ([DB-0810-09] reason (b)).
CALENDAR_UID_RE = re.compile(r"uid=([^\s,)]+).*?uid=([^\s,)]+)")


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

    # [DB-0815-09] Drop events whose detail carries no information ("None", "N/A",
    # "[N/A - ...]"). core/orchestrator.py stops writing these as of 2026-08-15, but
    # ~93 are already on the VM and this is a READ-time filter on purpose: the project
    # rule is archive-on-merge, data is never deleted, so the events stay on disk and
    # simply stop reaching the human-facing backlog. Without this the historical
    # `None. ×90` entry would keep leading the session-start line forever.
    return [
        e for e in events
        if isinstance(e, dict)
        and e.get("event_type") in WANTED
        and not _is_null_ish(str(e.get("detail", "")))
    ]


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


# [DB-0815-10] State and kind markers, added 2026-08-15 (Mike's request). Written inline in
# an item's own text, exactly like `due:`, so they need no new section and no re-ranking —
# an item keeps its position in `## Now` while declaring that it cannot be picked up today.
#
# WHY MARKERS AND NOT SECTIONS: `## Now` is Mike's ranked priority order. Moving a blocked
# item to a "Waiting" section would destroy its rank and force a re-ranking when it unblocks,
# which is the churn the `due:` convention was introduced to avoid on 2026-08-15.
#
# `waiting:` is for an EVENT or condition ("waiting: a real unreferenced calendar event");
# `due:` stays for a CLOCK date. They overlap deliberately — an item may carry both, meaning
# "blocked on this, re-check on that date".
# ⚠ THE `@` SIGIL IS LOAD-BEARING, and it took two tries to get here. This is the trap DUE_RE
# documents — prose reading as a marker — which DUE_RE escaped only because a date is a strict
# value shape and these markers have none.
#
#   Attempt 1, bare `\bsession:` — matched "Fixed same session: `_imap_quote()` added" and
#   "never given its own session:". Two false positives on the first live run.
#   Attempt 2, the same anchored at line start — still matched, because [DB-0810-11]'s prose
#   *wraps* onto a line beginning "session: **where should code replace LLM judgment**".
#
# A prose sentence can begin with any word, so no amount of anchoring separates a marker from
# a wrapped line. The sigil does, because "@session:" does not occur in English. Line-anchoring
# is kept as well, which makes the written convention "one marker, at the start of its own line".
_MARKER = r"^[\s\-*`>]*@{}:\s*(.+?)\s*`?\s*$"

WAITING_RE = re.compile(_MARKER.format("waiting"), re.MULTILINE)

# `session:` marks work that needs a working session with Mike — a design decision, a
# scoping conversation, a judgement only he can make — as opposed to work a session or a
# worker can simply do. This is the distinction that made a `/backlog attack` fail on
# 2026-08-15: three of six `## Now` items were unworkable and nothing in the file said so.
SESSION_RE = re.compile(_MARKER.format("session"), re.MULTILINE)

# `kind:` separates a defect from a request. Mike, 2026-08-15: "Filed requests through this
# pipeline will be both bugs and requested features, and differentiating would help me tackle
# the workload." The pipeline already knows which is which at filing time — LABELS maps
# FEATURE_REQUEST to "needs building" and USER_CORRECTION to "user corrected a prior turn" —
# so triage carries that forward rather than re-deriving it by reading.
KIND_RE = re.compile(r"^[\s\-*`>]*@kind:\s*(bug|feature|chore)\b", re.IGNORECASE | re.MULTILINE)


def _marked(block: str, pattern: re.Pattern) -> int:
    """Count top-level entries in `block` carrying a marker. Entry-scoped, not line-scoped."""
    return sum(1 for entry in _entries(block) if pattern.search(entry))


def count_machine(text: str) -> tuple[int, int]:
    """
    (entries, escalated) in `## Machine log` — **monitoring, not workload.**

    Counted separately and never folded into `later`, because they are not tasks: nobody
    asked for them, they are the runtime reporting on itself, and one signature reaching ×3
    is what promotes it into real work. Mike, 2026-08-15: he could not tell from the sync
    line whether the 109 entries here were part of the 40 in `## Later` or invisible. They
    were invisible, which made the backlog look smaller than the thing being monitored.
    """
    block = _section(text, MACHINE_HEADING)
    lines = [ln for ln in block.splitlines() if ln.startswith("- ") and not ln.startswith("- ~~")]
    return len(lines), sum(1 for ln in lines if ln.startswith("- ⚠"))


def count_states(text: str) -> dict:
    """
    Cross-cutting counts over `## Now` + `## Later` — how much of the list is actually
    pickable, and how it splits between defects and requests.

    Deliberately NOT a fourth section count. These are *properties of items already
    counted*, so they must never be added to inbox/now/later — double-counting the same
    item is the bug `count_items` carries three paragraphs of history about.
    """
    live = _section(text, NOW_HEADING) + "\n" + _section(text, LATER_HEADING)
    kinds = [m.group(1).lower() for m in KIND_RE.finditer(live)]
    return {
        "waiting": _marked(live, WAITING_RE),
        "session": _marked(live, SESSION_RE),
        "bug": kinds.count("bug"),
        "feature": kinds.count("feature"),
    }


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


def _entries(block: str) -> list[str]:
    """
    Split a section body into top-level entries — one per '- ' bullet, plus its
    indented/continuation lines — using the same boundary _items() counts
    against, so a due-date marker anywhere in an item's body (not just its
    first line) is still associated with the right item.

    A struck-through line ('- ~~') ends the entry in progress without starting
    a new one, matching _items()'s "closed items don't count" rule — a due
    marker should not fire again off an item that is already gone from Now/Later
    in every way except still sitting on the page for a moment.
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


def due_now(text: str, today: str) -> list[str]:
    """
    Ids of Now/Later items whose 'due: YYYY-MM-DD' marker has arrived — on or
    before `today`, an ISO date string.

    A garbage or unparseable date (the marker itself missing, `today` malformed,
    or a date like 2026-13-99) is treated as "no usable due date", not an error —
    consistent with this script's fail-silent contract. That is also why this
    returns [] rather than raising: a broken date must never be the reason the
    whole sync line disappears.
    """
    try:
        cutoff = date.fromisoformat(today)
    except ValueError:
        return []

    ids = []
    for heading in (NOW_HEADING, LATER_HEADING):
        for entry in _entries(_section(text, heading)):
            due_match = DUE_RE.search(entry)
            if not due_match:
                continue
            try:
                due = date.fromisoformat(due_match.group(1))
            except ValueError:
                continue
            id_match = ID_RE.search(entry)
            if id_match and due <= cutoff:
                ids.append(id_match.group(0)[1:-1])
    return ids


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
    them at the source instead of at triage time. CALENDAR_DUPLICATE gets the
    same treatment via the uid pair rather than DENIAL_RE's (agent, tool) shape
    — see CALENDAR_UID_RE.
    """
    kind = event.get("event_type", "")
    detail = " ".join(str(event.get("detail", "")).split())
    match = DENIAL_RE.search(detail)
    if match:
        return f"{kind}:{match.group(1)}/{match.group(2)}"
    if kind == "CALENDAR_DUPLICATE":
        uid_match = CALENDAR_UID_RE.search(detail)
        if uid_match:
            uid_a, uid_b = sorted((uid_match.group(1), uid_match.group(2)))
            return f"{kind}:{uid_a}/{uid_b}"
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
            elif event.get("event_type") == "CALENDAR_DUPLICATE":
                uid_match = CALENDAR_UID_RE.search(line)
                if uid_match:
                    uid_a, uid_b = sorted((uid_match.group(1), uid_match.group(2)))
                    existing_sig = f"CALENDAR_DUPLICATE:{uid_a}/{uid_b}"
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


def fold_fragments(text: str) -> tuple[str, list]:
    """Fold `.claude/backlog_inbox/*.md` into '## Inbox'.

    Why fragments exist at all: '## Inbox' is hand-edited, and two windows filing
    an item at the same time collide on the same lines. A file per item cannot
    collide, and it kills "never reserve an ID" as a rule you have to remember —
    two windows cannot create the same filename without one of them noticing.

    Fragments are deliberately NOT committed (`.claude/*` is gitignored). They are
    transient: written by whichever window has something to file, folded into
    DEV_BACKLOG.md on the next sync, then deleted. Their permanent home is the
    backlog, which is tracked.

    Write one item per file, in the same bullet form '## Inbox' already uses:

        .claude/backlog_inbox/tone-profile-empty.md

    Returns the updated text and the fragments that were folded. The caller
    deletes them only AFTER the backlog write succeeds — losing a filed item to a
    failed write would be exactly the silent loss this is meant to prevent.
    """
    if not INBOX_FRAGMENTS.is_dir():
        return text, []

    frags = sorted(
        p for p in INBOX_FRAGMENTS.iterdir()
        if p.suffix == ".md" and not p.name.startswith("_")
    )
    if not frags:
        return text, []

    additions = []
    folded = []
    for p in frags:
        try:
            body = p.read_text().strip()
        except OSError:
            continue
        # An empty fragment is still folded (and so deleted) — it carries nothing,
        # and leaving it would make it reappear in every future run's count.
        if body:
            # Coerce to a top-level bullet. The docstring asks for "the same bullet
            # form '## Inbox' already uses" and three fragments written on 2026-08-15
            # did not — they folded in as prose, so `_items()` (which counts lines
            # starting "- ") reported **0 inbox** while three real items sat there.
            # A filing route whose correctness depends on the writer remembering a
            # format is the kind of rule this project keeps proving does not hold, and
            # the failure is silent in the one number that would reveal it.
            if not body.lstrip().startswith(("- ", "-\t")):
                body = "- " + body
            additions.append(body)
        folded.append(p)

    if not additions:
        return text, folded

    head, _, tail = text.partition(INBOX_HEADING)
    block = _section(text, INBOX_HEADING)
    rest = tail[len(block):]

    # _section() runs to the next '## ', so the block carries the '---' rule that
    # closes the section. Appending past it puts new items visually OUTSIDE the
    # Inbox, under a horizontal rule that reads as "end of section" — which is
    # where the first version of this put them. Split the rule off, insert, and
    # put it back.
    body = block.rstrip("\n")
    trailer = ""
    if body.endswith("---"):
        body = body[: -len("---")].rstrip("\n")
        trailer = "\n\n---"

    merged = body + "\n" + "\n".join(additions) + trailer + "\n"
    return f"{head}{INBOX_HEADING}{merged}{rest}", folded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--persona", default=DEFAULT_PERSONA)
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--quiet", action="store_true", help="print nothing when there is nothing new")
    # Testing seam for due_now(), not a feature for normal use: at the time this
    # was written nothing in the real backlog comes due for three more days, so
    # without an override the ⚠ due: clause could not be observed at all until
    # then. A CLI flag rather than an env var to match how --server/--persona
    # already override this script's defaults, and so it's discoverable via
    # --help without reading source.
    ap.add_argument("--today", default=None,
                     help="override today's date (YYYY-MM-DD) for due-date checks; default real date")
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

    # Locally-filed items fold in alongside the VM's events, so a window with
    # something to file does not need the VM to be up for it to land.
    text, folded = fold_fragments(text)
    added += len(folded)

    if new or folded:
        BACKLOG.write_text(text)
        # Only now that the item is durably in the backlog. A fragment deleted
        # before a failed write is a silently lost change request.
        for frag in folded:
            try:
                frag.unlink()
            except OSError:
                pass

    inbox, now, later = count_items(text)
    # Show the three loudest by count, not all of them. The full tally is already in the
    # `N machine (M ⚠)` clause, so listing all eight 40-character fragments made the line
    # unreadable and buried the counts that precede it — which is what a SessionStart line
    # is for. `/backlog deep` reads the section itself; this is a pointer, not a report.
    escalations = sorted(
        escalated(text),
        key=lambda s: int(m.group(1)) if (m := re.search(r"×(\d+)$", s)) else 1,
        reverse=True,
    )
    shown = escalations[:3]
    more = f", +{len(escalations) - len(shown)} more" if len(escalations) > len(shown) else ""
    alert = f" · ⚠ {', '.join(shown)}{more}" if escalations else ""
    due_ids = due_now(text, args.today or date.today().isoformat())
    due_clause = f" · ⚠ due: {', '.join(due_ids)}" if due_ids else ""

    # [DB-0815-10] The line answers one question: how much work is actually sitting here?
    #
    #   inbox/now/later  the partition — every curated item is in exactly one
    #   workable         the derived number Mike asked for: items nothing is blocking
    #   parked           waiting on an event, or needing a session with him
    #   machine          monitoring, NOT workload — counted apart, never added to `later`
    #
    # Blocked counts ride in parentheses rather than as peers: they are properties of items
    # already counted, and printing them alongside inbox/now/later would read as five
    # sections and double-count the same item — the bug count_items() carries history about.
    st = count_states(text)
    parked = st["waiting"] + st["session"]
    workable = max(now + later - parked, 0)

    detail = [f"{st['waiting']} waiting" if st["waiting"] else "",
              f"{st['session']} session" if st["session"] else ""]
    # Kind counts are suppressed until most items carry a marker. Tagging is partial
    # (only items touched on 2026-08-15), so "6 bug, 4 feature" against 49 items reads as
    # a breakdown when it is a floor — a misleading number is worse than no number.
    if st["bug"] + st["feature"] >= (now + later) / 2:
        detail += [f"{st['bug']} bug" if st["bug"] else "",
                   f"{st['feature']} feature" if st["feature"] else ""]
    parked_clause = f" ({', '.join(p for p in detail if p)})" if any(detail) else ""

    machine, escalated_n = count_machine(text)
    machine_clause = f" · {machine} machine" if machine else ""
    if escalated_n:
        machine_clause += f" ({escalated_n} ⚠)"

    if new or not args.quiet or vm_warning:
        print(f"DEV_BACKLOG.md: {added} new · {inbox} inbox · {now} now · "
              f"{later} later · {workable} workable{parked_clause}"
              f"{machine_clause}{alert}{due_clause}{vm_warning}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Never let a backlog sync break a session start.
        sys.exit(0)
