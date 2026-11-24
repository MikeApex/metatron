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
3. **Only text that names THIS person.** Case-sensitive, capitalised. The full name (first +
   last, either order) always counts. The first name or nickname alone counts only when no other
   contact shares it and it is not also an ordinary word (`contact_resolution.COMMON_WORD_NAMES`:
   Will, Mark, Rose, May, …). Stored facts: the relationships domain by that rule, any other
   domain only by full name.
4. **Grants.** The user's lists pass the data-object read rule for the agent; stored facts and
   past entries are read only when the agent holds `read_wisdom` / `search_memory`. Open tasks
   are read by code, read-only, for the task's wording and due date only — never a medication
   link or any other field (driver ruling, review of 56cce4f item 4).
5. **Never slows the records down.** Built after the records, overdue and dates parts; the past-
   entry searches share one budget of `MEMORY_BUDGET_S` for the whole block, in parallel.
6. **Empty means nothing is appended; any error gives "".** It never costs a turn.

Caps: 3 people, 6 lines each (all sources together), 160 characters a line. Cost: one local
FAISS search per resolved person, together ≤1.5 s; ≈400 tokens on a call that has hits.
"""

from __future__ import annotations

import contextlib
import logging
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)

HEADING = ("ON FILE ABOUT PEOPLE NAMED HERE (from code — before anything addressed to one of "
           "them, check whether they are its subject)")
MAX_PEOPLE = 3
MAX_LINES = 6
LINE_CHARS = 160
MEMORY_HITS = 3
MEMORY_BUDGET_S = 1.5
_MEMORY_K = 6
_RELATIONSHIPS_DOMAIN = "relationships"


# --- who a piece of text is about (rule 3) ----------------------------------------------------

def _cap_words(value) -> list[str]:
    return [w for w in re.findall(r"[A-Za-z][A-Za-z'\-]*", str(value or ""))]


def _full_patterns(contact: dict) -> list[re.Pattern]:
    first = _cap_words(contact.get("first_name"))
    last = _cap_words(contact.get("last_name"))
    name = _cap_words(contact.get("name"))
    if not (first and last) and len(name) >= 2:
        first, last = name[:1], name[-1:]
    seqs = []
    if first and last:
        seqs += [first + last, last + first]
    if len(name) >= 2:
        seqs.append(name)
    out, seen = [], set()
    for seq in seqs:
        key = tuple(seq)
        if key in seen:
            continue
        seen.add(key)
        out.append(re.compile(r"(?<![A-Za-z])" + r"\s+".join(re.escape(w) for w in seq)
                              + r"(?![A-Za-z])"))
    return out


def _single_names(contact: dict, counts: Counter) -> list[str]:
    """The one-word names that are safe to match alone for this contact (rule 3)."""
    from tools.contact_resolution import COMMON_WORD_NAMES
    out = []
    for raw in (contact.get("first_name") or (_cap_words(contact.get("name")) or [""])[0],
                contact.get("nickname")):
        words = _cap_words(raw)
        if len(words) != 1:
            continue
        w = words[0]
        low = w.lower()
        if len(w) < 2 or low in COMMON_WORD_NAMES or counts.get(low, 0) != 1:
            continue
        out.append(w[0].upper() + w[1:])
    return out


def matcher(contact: dict, contacts: list[dict]):
    """(names_full, names_single) → a function text -> bool telling whether text names this
    contact under rule 3, and a function for full-name-only matching."""
    from tools.contact_resolution import _singles
    counts: Counter = Counter()
    for c in contacts or [contact]:
        for w in _singles(c):
            counts[w] += 1
    full = _full_patterns(contact)
    singles = [re.compile(rf"(?<![A-Za-z]){re.escape(w)}(?![A-Za-z])")
               for w in _single_names(contact, counts)]

    def by_full(text) -> bool:
        return any(p.search(str(text or "")) for p in full)

    def by_rule(text) -> bool:
        t = str(text or "")
        return by_full(t) or any(p.search(t) for p in singles)
    return by_rule, by_full


def _label(contact: dict) -> str:
    return " ".join(str(contact.get("name") or "").split()) or " ".join(
        x for x in (contact.get("first_name"), contact.get("last_name")) if x) or str(
        contact.get("nickname") or contact.get("id") or "")


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


# --- the sources --------------------------------------------------------------------------------

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


def _task_lines(names_it) -> list[str]:
    """Open tasks whose wording names the person — the wording and the due date only. Read-only
    (tools/obligations.py is never written from here)."""
    from tools import obligations as O
    out = []
    for t in (O._norm(t) for t in O._load()):
        if t.get("status") != "open" or not names_it(t.get("what")):
            continue
        due = str(t.get("due") or "").strip()
        out.append(f"open task: {t['what']}" + (f" (due {due[:10]})" if due else ""))
    return out


def _wisdom_lines(by_rule, by_full) -> list[str]:
    from tools.wisdom import _all_entries
    out = []
    for e in _all_entries():
        if not isinstance(e, dict):
            continue
        text = f"{e.get('key') or ''} {e.get('value') or ''}"
        in_domain = str(e.get("domain") or "").lower() == _RELATIONSHIPS_DOMAIN
        if (by_rule(text) if in_domain else by_full(text)):
            out.append(f"on file: {e.get('value')}")
    return out


def _memory_lines(contact: dict, names_it) -> list[str]:
    from core.memory import search_memory
    hits = search_memory(_label(contact), k=_MEMORY_K) or []
    out = []
    for h in hits:
        text = str((h or {}).get("text") or "")
        if not names_it(text):          # the name, literally, by rule 3
            continue
        when = str(h.get("date") or "")[:10]
        out.append(f"past entry{f' ({when})' if when else ''}: {text}")
        if len(out) >= MEMORY_HITS:
            break
    return out


def on_file_block(resolved: list[dict], agent: str = "relationships",
                  contacts: list[dict] | None = None) -> str:
    """The ON FILE block for the resolved people, or "" when nothing is on file (or on error).
    `contacts`: the whole contact list, for "does anyone else share this first name"; loaded
    when not given."""
    try:
        people = [c for c in (resolved or []) if isinstance(c, dict) and c.get("id")][:MAX_PEOPLE]
        if not people:
            return ""
        if contacts is None:
            from tools import crm as CRM
            contacts = CRM._load_contacts()
        granted = _granted(agent)
        match = {str(c["id"]): matcher(c, contacts) for c in people}
        from core.persona import current_persona, persona_scope
        persona = current_persona()

        # Rule 5: every past-entry search starts now, in parallel, under one shared budget.
        futures = {}
        deadline = time.monotonic() + MEMORY_BUDGET_S
        if _holds(granted, "search_memory"):
            def _search(c):
                with (persona_scope(persona) if persona else contextlib.nullcontext()):
                    return _memory_lines(c, match[str(c["id"])][0])
            pool = ThreadPoolExecutor(max_workers=len(people), thread_name_prefix="on-file")
            futures = {str(c["id"]): pool.submit(_search, c) for c in people}
            pool.shutdown(wait=False)

        sections = []
        for c in people:
            by_rule, by_full = match[str(c["id"])]
            lines: list[str] = []
            sources = [("lists", lambda: _list_entries(c, agent), True),
                       ("tasks", lambda: _task_lines(by_rule), True),
                       ("facts", lambda: _wisdom_lines(by_rule, by_full),
                        _holds(granted, "read_wisdom"))]
            for label, source, allowed in sources:
                if not allowed:
                    continue
                try:
                    lines += source()
                except Exception as exc:  # noqa: BLE001 — one source failing loses only it
                    logger.warning(f"[recipient_context] {label} source skipped: {exc}")
            fut = futures.get(str(c["id"]))
            if fut is not None:
                try:
                    lines += fut.result(timeout=max(0.0, deadline - time.monotonic()))
                except Exception as exc:  # noqa: BLE001 — a slow search loses only itself
                    logger.warning(f"[recipient_context] past-entry search skipped: "
                                   f"{type(exc).__name__}: {exc}")
            seen, kept = set(), []
            for ln in lines:
                ln = _line(ln)
                if ln.casefold() not in seen:
                    seen.add(ln.casefold())
                    kept.append(ln)
            if kept:
                sections.append(f"{_label(c)} ({c.get('id')}):\n"
                                + "\n".join(f"- {x}" for x in kept[:MAX_LINES]))
        if not sections:
            return ""
        return f"{HEADING}:\n" + "\n".join(sections)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[recipient_context] block not built: {exc}")
        return ""
