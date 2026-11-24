"""
tools/recipient_context.py — what is already on file about the people a Relationships turn names
(instructions-to-code Stage 4, 4c: #16, DECISION 4-3, built in the shape Stage 5 specified and
Mike ruled "as the plan says").

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #12 (#16 bullet).
Read by core/prefetch.py's `people` read, after tools/contact_resolution.py has resolved who is
named. Never a tool, never in a schema.

What a user notices: before the Relationships specialist drafts something to a person, it is
shown what is on file that names them — a gift idea saved for them, an open task that names
them, a standing fact, a past entry — so a message never gives away the surprise it is about.

The rules, each tested in tests/test_recipient_context.py:

1. **Evidence, not a verdict.** The block is handed to the drafter; whether any of it is the
   subject of a message is the model's judgement. Nothing here blocks or edits a send.
2. **No trigger words.** It runs on every Relationships call that resolves someone — the first
   draft's draft/send word list was withdrawn as a fuzzy relevance test.
3. **Never widens a grant.** Each source is read only when the agent holds the tool that reads
   it (`read_data_object`, `list_tasks`, `read_wisdom`, `search_memory`); the lists in the user's
   logs also pass the data-object read rule for that agent.
4. **A memory hit counts only if it contains the name literally** (local FAISS search, no model).
5. **Empty means nothing is appended; any error gives "".** It never costs a turn.

Caps: 3 people, 6 lines each, 160 characters a line. Cost: one local FAISS search per resolved
person (~0.5 s, run in parallel), ≈400 tokens on a call that has hits.
"""

from __future__ import annotations

import contextlib
import logging
import re
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

HEADING = ("ON FILE ABOUT PEOPLE NAMED HERE (from code — before anything addressed to one of "
           "them, check whether they are its subject)")
MAX_PEOPLE = 3
MAX_LINES = 6
LINE_CHARS = 160
MEMORY_HITS = 3
_MEMORY_K = 6
_MEMORY_TIMEOUT_S = 3.0


def _names(contact: dict) -> list[str]:
    out = []
    for k in ("name", "first_name", "nickname"):
        v = " ".join(str(contact.get(k) or "").split())
        if v and v.casefold() not in {x.casefold() for x in out}:
            out.append(v)
    return out


def _names_in(text: str, names: list[str]) -> bool:
    text = str(text or "")
    return any(re.search(rf"(?<![A-Za-z]){re.escape(n)}(?![A-Za-z])", text, re.IGNORECASE)
               for n in names if len(n) >= 2)


def _line(text: str) -> str:
    text = " ".join(str(text or "").split())
    return text if len(text) <= LINE_CHARS else text[:LINE_CHARS - 1] + "…"


@contextlib.contextmanager
def _as_agent(agent: str):
    """Bind `agent` as the calling agent on this thread for the duration, so the data-object read
    rule (tools/data_objects.may_read) binds for the agent the block is for — exactly as it does
    when that agent calls `read_contact` itself. Restored afterwards."""
    from core import trace as _tr
    prev = _tr.get_current_agent()
    _tr._set_current_agent(_tr.AgentRecord(agent=agent, provider="", model="", parent=prev))
    try:
        yield
    finally:
        _tr._set_current_agent(prev)


def _granted(agent: str) -> set[str] | None:
    from core.router import get_allowed_tools
    allowed = get_allowed_tools(agent)
    return None if allowed is None else set(allowed)


def _holds(granted: set[str] | None, tool: str) -> bool:
    return granted is None or tool in granted


def _list_entries(contact: dict, agent: str) -> list[str]:
    from tools.data_objects import entries_for_contact
    with _as_agent(agent):
        rows = entries_for_contact(contact)
    out = []
    for r in rows:
        what = next((str(r[k]) for k in ("title", "text", "item", "idea", "description", "what")
                     if str(r.get(k) or "").strip()), "")
        if not what:
            what = ", ".join(f"{k}: {v}" for k, v in r.items()
                             if k not in ("list", "n", "for", "added", "updated") and v)
        out.append(f"in your {r.get('list') or 'list'}: {what}")
    return out


def _task_lines(contact: dict, names: list[str]) -> list[str]:
    from tools import obligations as O
    out = []
    for t in (O._norm(t) for t in O._load()):
        if t.get("status") != "open":
            continue
        if _names_in(t.get("what"), names) or _names_in(t.get("notes") or t.get("note"), names):
            out.append(f"open task {t['id']}: {t['what']}")
    return out


def _wisdom_lines(names: list[str]) -> list[str]:
    from tools.wisdom import _all_entries
    out = []
    for e in _all_entries():
        if not isinstance(e, dict) or e.get("retired"):
            continue
        if _names_in(e.get("key"), names) or _names_in(e.get("value"), names):
            out.append(f"on file ({e.get('key')}): {e.get('value')}")
    return out


def _memory_lines(contact: dict, names: list[str]) -> list[str]:
    from core.memory import search_memory
    hits = search_memory(names[0], k=_MEMORY_K) or []
    out = []
    for h in hits:
        text = str((h or {}).get("text") or "")
        if not _names_in(text, names):          # rule 4: the name, literally
            continue
        when = str(h.get("date") or "")[:10]
        out.append(f"past entry{f' ({when})' if when else ''}: {text}")
        if len(out) >= MEMORY_HITS:
            break
    return out


def on_file_block(resolved: list[dict], agent: str = "relationships") -> str:
    """The ON FILE block for the resolved people, or "" when nothing is on file (or on error)."""
    try:
        people = [c for c in (resolved or []) if isinstance(c, dict)][:MAX_PEOPLE]
        if not people:
            return ""
        granted = _granted(agent)
        from core.persona import current_persona, persona_scope
        persona = current_persona()

        futures = {}
        if _holds(granted, "search_memory"):
            def _search(c):
                with (persona_scope(persona) if persona else contextlib.nullcontext()):
                    return _memory_lines(c, _names(c))
            pool = ThreadPoolExecutor(max_workers=len(people), thread_name_prefix="on-file")
            futures = {str(c.get("id")): pool.submit(_search, c) for c in people if _names(c)}
            pool.shutdown(wait=False)

        sections = []
        for c in people:
            names = _names(c)
            if not names:
                continue
            lines: list[str] = []
            for source, wanted in ((lambda: _list_entries(c, agent), "read_data_object"),
                                   (lambda: _task_lines(c, names), "list_tasks"),
                                   (lambda: _wisdom_lines(names), "read_wisdom")):
                if not _holds(granted, wanted):
                    continue
                try:
                    lines += source()
                except Exception as exc:  # noqa: BLE001 — one source failing loses only it
                    logger.warning(f"[recipient_context] {wanted} source skipped: {exc}")
            fut = futures.get(str(c.get("id")))
            if fut is not None:
                try:
                    lines += fut.result(timeout=_MEMORY_TIMEOUT_S)
                except Exception as exc:  # noqa: BLE001
                    logger.warning(f"[recipient_context] memory search skipped: {exc}")
            seen, kept = set(), []
            for ln in lines:
                ln = _line(ln)
                if ln.casefold() not in seen:
                    seen.add(ln.casefold())
                    kept.append(ln)
            if kept:
                sections.append(f"{names[0]} ({c.get('id')}):\n"
                                + "\n".join(f"- {x}" for x in kept[:MAX_LINES]))
        if not sections:
            return ""
        return f"{HEADING}:\n" + "\n".join(sections)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[recipient_context] block not built: {exc}")
        return ""
