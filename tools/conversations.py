"""
tools/conversations.py — search the verbatim conversation record.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 9. There was no
conversation search at all before this; the Librarian needs one.

WHICH STORE THIS READS, AND WHY IT IS NOT THE OTHER ONE. Conversation turns are
written twice, to two stores with different coverage:

  1. `data/personas/{p}/conversations/YYYY-MM-DD.jsonl` — appended by
     `core.server._log_conversation()` on EVERY turn path: /session,
     /session/stream, the WebSocket loop, and the confirm/decline endpoints.
  2. `data/conversations/metatron.db`, table `exchanges` — written by
     `_save_exchange()` on three of those five paths, and shared across personas
     with a `persona` column rather than being per-persona.

This module reads (1). It is the complete record, it is already what The Book
(`/monitor/conversations`) and `core/scheduler.py` read, and it carries `agent`
and `seq`, which the database row does not. Scoping is by DIRECTORY rather than
by a column, so a search cannot return another persona's turn even if the
scoping were wrong — which the database cannot say.

A hit is addressed by `date` + `seq`, deliberately: that is the pair
`/metatron-troubleshoot` already takes, so anything found here can be re-read in
full through a path that exists rather than by widening this tool.

The shared `data/conversations/*.jsonl` directory that predates the per-persona
layout is NOT read. It is not persona-scoped, so reading it would put another
persona's turns inside a persona-scoped result; no such file exists on the Mac.

CAPS. `k` defaults to 10 and is hard-capped at 50, matching the read door's cap
so the tool is bounded when called directly and not only when called through the
door. Each returned field is excerpted to 400 characters around the match, which
is the cap that actually bounds the payload — a Synthesizer reply is long, so a
result count alone bounds rows and not bytes.

THE SCAN WINDOW IS NOT CAPPED, and that is the one deliberate difference from
the door's other numbers. An `absent` verdict from the Librarian is a finding
(plan section 13.6); a search silently narrowed to a recent window would
manufacture false ones. So with no `since` this reads all of history, and the
result always reports the span actually searched so an `absent` carries its own
evidence.

Sensitive-tier, persona-scoped, read-only. Local files only; no model call.
"""

from datetime import date
from pathlib import Path

from core.persona import persona_data_dir

# `k` matches the read door's cap (plan section 6) rather than sitting under it:
# a tool ceiling below the door's would make the door's published cap a lie.
DEFAULT_K = 10
MAX_K = 50

# The real bound on payload size. Rows are capped by `k`; bytes are capped here.
SNIPPET_CHARS = 400


def _conversation_files(since: date | None) -> list[tuple[date, Path]]:
    """Dated day files for this persona, newest first. Empty when there are none."""
    conv_dir = persona_data_dir() / "conversations"
    if not conv_dir.is_dir():
        return []
    found: list[tuple[date, Path]] = []
    for path in conv_dir.glob("*.jsonl"):
        try:
            day = date.fromisoformat(path.stem)
        except ValueError:
            continue  # not a dated day file — a stray, not an error
        if since and day < since:
            continue
        found.append((day, path))
    found.sort(reverse=True)
    return found


def _rows(path: Path) -> list[dict]:
    """Every parseable row in a day file, in the order written (oldest first)."""
    import json
    out: list[dict] = []
    try:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                except ValueError:
                    continue  # a half-written line is not a reason to fail the read
                if isinstance(row, dict):
                    out.append(row)
    except OSError:
        return []
    return out


def _excerpt(text: str, terms: list[str]) -> tuple[str, bool]:
    """
    A window of `text` around its first matching term, capped at SNIPPET_CHARS.

    Centred on the match rather than taken from the head, because the head of a
    long reply is usually its preamble and the match is the reason the turn was
    returned.
    """
    text = text or ""
    if len(text) <= SNIPPET_CHARS:
        return text, False
    lowered = text.casefold()
    at = -1
    for term in terms:
        found = lowered.find(term)
        if found != -1 and (at == -1 or found < at):
            at = found
    if at == -1:
        return text[:SNIPPET_CHARS].rstrip() + " …", True
    begin = max(0, at - SNIPPET_CHARS // 2)
    finish = min(len(text), begin + SNIPPET_CHARS)
    piece = text[begin:finish].strip()
    return (("… " if begin > 0 else "") + piece + (" …" if finish < len(text) else "")), True


def _empty(query: str, since: str, k: int, error: str = "") -> dict:
    """The result shape, with nothing in it. Returned on every failure path too."""
    return {
        "query": query,
        "since": since,
        "k": k,
        "matches": [],
        "returned": 0,
        "match_count": 0,
        "truncated": False,
        "searched_days": 0,
        "searched_from": "",
        "searched_to": "",
        "error": error,
    }


def search_conversations(query: str = "", k: int = 0, since: str = "") -> dict:
    """
    Find conversation turns whose text matches every term in `query`.

    Args:
        query: Space-separated search terms, case-insensitive, matched as
               substrings against the user's words and the reply together. A
               turn matches only if EVERY term appears. An empty query matches
               every turn, which is how a presence check asks "is there a
               corpus here" without naming anything.
        k:     Maximum turns to return, newest first. 0 or less uses the default
               of 10; anything above 50 is capped at 50.
        since: Optional ISO date (YYYY-MM-DD), inclusive lower bound. A datetime
               is accepted and truncated to its date. Omit it to search all of
               history.

    Returns:
        A dict, always the same shape:
          matches       list of {date, seq, ts, agent, proactive, user,
                        response, excerpted}, newest first
          returned      how many are in `matches`
          match_count   how many turns matched in total, before `k`
          truncated     True when match_count > returned
          searched_days how many day files were read
          searched_from oldest day read, searched_to newest — so an empty result
                        says what was looked at rather than only that nothing
                        was found
          error         "" when the read succeeded

        Never raises: an absent persona directory, an unreadable file and a
        half-written line all read as "nothing there", because a research read
        must not be able to fail a turn.
    """
    k = DEFAULT_K if k is None or k <= 0 else min(int(k), MAX_K)
    query = query or ""
    since = (since or "").strip()

    since_day: date | None = None
    if since:
        try:
            since_day = date.fromisoformat(since[:10])
        except ValueError:
            # Reported rather than ignored: a silently dropped bound would
            # return a wider window than the caller asked for and say so
            # nowhere, which is worse than no answer.
            return _empty(query, since, k,
                          error=f"since {since!r} is not an ISO date (YYYY-MM-DD).")

    terms = [t for t in query.casefold().split() if t]
    files = _conversation_files(since_day)
    if not files:
        return _empty(query, since, k)

    matches: list[dict] = []
    match_count = 0
    for day, path in files:
        for row in reversed(_rows(path)):
            user = row.get("user") or ""
            response = row.get("response") or ""
            # all([]) is True, so an empty query matches every turn.
            if not all(term in f"{user}\n{response}".casefold() for term in terms):
                continue
            match_count += 1
            if len(matches) >= k:
                continue  # keep counting, so `truncated` is honest
            user_text, user_cut = _excerpt(user, terms)
            reply_text, reply_cut = _excerpt(response, terms)
            matches.append({
                "date": day.isoformat(),
                "seq": row.get("seq", ""),
                "ts": row.get("ts", ""),
                "agent": row.get("agent", ""),
                "proactive": bool(row.get("proactive")),
                "user": user_text,
                "response": reply_text,
                "excerpted": user_cut or reply_cut,
            })

    return {
        "query": query,
        "since": since,
        "k": k,
        "matches": matches,
        "returned": len(matches),
        "match_count": match_count,
        "truncated": match_count > len(matches),
        "searched_days": len(files),
        "searched_from": files[-1][0].isoformat(),
        "searched_to": files[0][0].isoformat(),
        "error": "",
    }


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

SEARCH_CONVERSATIONS_SCHEMA = {
    "name": "search_conversations",
    "description": (
        "Search the verbatim record of past conversations for turns containing given "
        "terms. Returns the matching turns newest first, each with its date and "
        "sequence number. Use it to find what was actually said about something, and "
        "when — search_memory is a semantic index over logs and journal entries and "
        "does not cover conversation turns at all. Leave the query empty to see the "
        "most recent turns."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Space-separated terms, case-insensitive. A turn must contain all "
                    "of them. Leave empty to match every turn."
                ),
            },
            "k": {
                "type": "integer",
                "description": (
                    f"Maximum turns to return, newest first. Default {DEFAULT_K}, "
                    f"maximum {MAX_K}."
                ),
            },
            "since": {
                "type": "string",
                "description": (
                    "Optional earliest date to search, YYYY-MM-DD, inclusive. Omit to "
                    "search the whole history."
                ),
            },
        },
        "required": [],
    },
}
