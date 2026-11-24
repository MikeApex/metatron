"""
core/prefetch.py — a specialist's fixed first-turn reads, made by code before it starts
(instructions-to-code Stage 4, #22; 4-2's speculative calendar read; the #14/#15 evidence).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #22, as amended.
The list of reads is policy and lives in config/modules/prefetch.yaml.

What a user notices: a reply that needs the calendar, the tasks or a specialist's saved
settings comes back sooner — measured, Logistics spent its first model round on exactly these
reads on about half its calls.

The rules this module keeps, each tested in tests/test_prefetch.py:

1. **The block goes in the USER message, never the system prompt.** The cached Vertex prefix is
   byte-identical with and without it (CLAUDE.md trap 6: the 4,096-token cache floor).
2. **Prefetch never widens a grant.** Each read kind maps to the tool it stands for
   (READ_TOOLS); an entry for a tool the agent is not granted is refused at load and logged.
   Reads call the tool's own function directly — not dispatch_tool — so they leave no tool-call
   record (a failed prefetch read must not be reported upward as a failed action).
3. **Never crosses personas.** Every read runs in a worker thread with the persona bound inside
   it, resolved on the calling thread; an unresolvable persona prefetches nothing.
4. **Never for the Research Agent, a bare run, or anything outside the eight personal
   specialists** (review L2). Never email (DECISION 4-1).
5. **Calendar text stays untrusted.** Events are wrapped in `<untrusted_content>` exactly as
   read_calendar wraps them, and the wrapper is never sliced: the event LIST is cut to fit before
   wrapping ("+N more events — call read_calendar"), and code's own lines (the unverified count,
   the notes) sit before the wrapped block. A block that carried at least one calendar event
   adds its agent to `prefetched_untrusted_agents` on the request trace, and
   _file_wisdom_proposals forces THAT agent's proposals to `observed` (review L3, scoped).
6. **A read never writes.** The calendar block counts `[VERIFY]` events from structured rows
   (tools/caldav.read_calendar_rows) and never re-checks one (review S6, 4-7 = no). The intake
   count reads the queue WITHOUT advancing its cursor — read_intake_queue itself consumes the
   queue, so it is not called.
7. **A failed or slow read is one line**, "(not read in advance: call `<tool>`)". It never
   fails the dispatch. Everything here returns "" rather than raise. A speculative calendar read
   not ready within the budget is that line too — never a second fetch.
8. **Readers see the real caller.** Each worker binds the dispatching agent as the current agent
   (the thread-local the tool dispatcher sets), so a reader that keys on the caller — the
   ledger's medication-link tags, the data-object read gate — answers as it would for that
   agent's own tool call.
9. **"Today" is the persona's day**, placed the way the medication view places doses
   (tools/domain_counters.day_entry): each field by its write time in the persona's zone and day
   boundary, read from the same-date file and both neighbours.

Cost: Logistics ≈ 4–5k tokens re-sent on each remaining turn (uncached user message); PH and MW
≈ 1.5k. Nothing persists between requests — the speculative calendar future dies with it.
"""

from __future__ import annotations

import json
import logging
import threading
from concurrent.futures import Future, TimeoutError as _FutureTimeout
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable

logger = logging.getLogger(__name__)

_CONFIG_PATH = Path(__file__).resolve().parent.parent / "config" / "modules" / "prefetch.yaml"

# Each read kind, and the tool the agent must already hold for it.
READ_TOOLS: dict[str, str] = {
    "agent_config": "read_agent_config",
    "open_tasks": "list_tasks",
    "calendar": "read_calendar",
    "intake_count": "read_intake_queue",
    "log_field": "read_log",
    "data_object": "read_data_object",
    "counters": "read_log",
    "skill_habits": "list_tasks",
}

# Which reads put text written by someone other than the user in front of the model.
_UNTRUSTED_KINDS = {"calendar"}

_HEADING = ("[PREFETCHED — read by code before your first turn, as of {hhmm}. Use these; call a "
            "tool only for something not here.]")
_DEFAULTS = {"enabled": True, "read_timeout_s": 4, "cap_chars": 6000, "agents": {}}


def load_config() -> dict:
    cfg = dict(_DEFAULTS)
    try:
        import yaml
        raw = yaml.safe_load(_CONFIG_PATH.read_text()) or {}
        if isinstance(raw, dict):
            cfg.update({k: v for k, v in raw.items() if v is not None})
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] config unreadable — nothing prefetched: {exc}")
        cfg["agents"] = {}
    return cfg


def _eligible_agents() -> frozenset[str]:
    from core.orchestrator import _EVIDENCE_AGENTS
    return _EVIDENCE_AGENTS


def _excluded(agent: str) -> bool:
    from core.orchestrator import _UNTRUSTED_OUTPUT_AGENTS
    return agent == "research_agent" or agent in _UNTRUSTED_OUTPUT_AGENTS \
        or agent not in _eligible_agents()


def plan_for(agent: str, cfg: dict | None = None) -> list[dict]:
    """The agent's reads from the yaml, each checked against its grant. An unknown kind or an
    ungranted tool is refused here and logged — prefetch never reads what the agent could not."""
    cfg = cfg or load_config()
    if not cfg.get("enabled") or _excluded(agent):
        return []
    entries = (cfg.get("agents") or {}).get(agent) or []
    from core.router import get_allowed_tools
    allowed = get_allowed_tools(agent)
    allowed_set = None if allowed is None else set(allowed)
    out: list[dict] = []
    for e in entries:
        if not isinstance(e, dict):
            continue
        kind = str(e.get("read") or "")
        tool = READ_TOOLS.get(kind)
        if tool is None:
            logger.warning(f"[prefetch] {agent}: unknown read kind {kind!r} refused")
            continue
        if kind == "data_object" and str(e.get("object") or "") == "":
            continue
        if allowed_set is not None and tool not in allowed_set:
            logger.warning(f"[prefetch] {agent}: {kind} needs {tool}, which {agent} is not "
                           f"granted — refused (prefetch never widens a grant)")
            continue
        out.append(dict(e))
    return out


# --- readers: each returns (heading, text, untrusted) and may raise ----------------------------

def _cap(text: str, cap: int, fallback: Callable[[], str] | None = None) -> str:
    if len(text) <= cap:
        return text
    if fallback is not None:
        return fallback()
    return text[:cap] + f"\n… (cut at {cap} characters — call the tool for the rest)"


def _read_agent_config(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.agent_config import read_agent_config
    text = str(read_agent_config(agent_name=agent))

    def _keys() -> str:
        try:
            keys = list(json.loads(text).keys())
        except Exception:  # noqa: BLE001
            keys = []
        return (f"(your settings are too long to hand over whole; keys: "
                f"{', '.join(keys) or 'unreadable'} — call `read_agent_config(key=…)` for one)")
    return (f'read_agent_config(agent_name="{agent}")', _cap(text, ctx["cap"], _keys), False)


def _read_open_tasks(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.obligations import list_tasks
    return ("list_tasks() — open tasks", _cap(str(list_tasks()), ctx["cap"]), False)


def _calendar_rows(start: str, end: str) -> tuple[dict, list[dict]]:
    from tools.caldav import read_calendar_rows
    return read_calendar_rows(start, end)


def _calendar_range(ctx: dict) -> tuple[str, str]:
    today = ctx["today"]
    return today.isoformat(), (today + timedelta(days=1)).isoformat()


def _wrapper_source(wrapped: str) -> str:
    """The `source` read_calendar put on its wrapper, so the re-wrapped list says the same."""
    import re
    m = re.match(r'<untrusted_content source="([^"]*)">', str(wrapped or ""))
    return m.group(1) if m else "calendar"


def _render_calendar(result: dict, rows: list[dict], cap: int) -> tuple[str, int]:
    """(text, events shown). Code's own lines first — the unverified count, the "+N more" line
    and read_calendar's notes — then the events, wrapped ONCE and closed. When the whole would
    pass `cap`, the event list is cut BEFORE wrapping; the wrapper is never sliced open."""
    from tools.untrusted import wrap_untrusted
    if not isinstance(result, dict) or "events" not in result:
        # Not connected, or an error: code's text only, nobody else's.
        return json.dumps(result, ensure_ascii=False, indent=1)[:cap], 0
    unverified = sum(1 for r in rows
                     if str(r.get("conflict_check_status") or "").upper() == "FAILED")
    meta = {k: v for k, v in result.items() if k not in ("events", "count")}
    head = [f"{len(rows)} event{'s' if len(rows) != 1 else ''} in range."]
    if unverified:
        head.append(f"{unverified} event{'s' if unverified != 1 else ''} still unverified "
                    f"(`[VERIFY]`) — call `read_calendar` for this range to re-check "
                    f"{'them' if unverified != 1 else 'it'}.")
    source = _wrapper_source(result.get("events"))
    meta_text = json.dumps(meta, ensure_ascii=False, indent=1)
    shown = list(rows)
    while True:
        more = len(rows) - len(shown)
        lines = head + ([f"+{more} more event{'s' if more != 1 else ''} not shown — call "
                         f"`read_calendar` for them."] if more else [])
        wrapped = wrap_untrusted(json.dumps(shown, indent=2, ensure_ascii=False), source=source)
        text = "\n".join(lines) + "\n" + meta_text + "\n" + wrapped
        if len(text) <= cap or not shown:
            return text, len(shown)
        shown = shown[:-1]


def _read_calendar(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    start, end = _calendar_range(ctx)
    fut: Future | None = ctx.get("calendar_future")
    if fut is not None:
        # 4-2's read: used if it is ready within the budget. Never a second fetch — a read that
        # is late or failed raises here, and the block says "not read in advance".
        result, rows = fut.result(timeout=ctx["timeout"])
    else:
        result, rows = _calendar_rows(start, end)
    text, shown = _render_calendar(result, rows, ctx["cap"])
    return f'read_calendar(start_date="{start}", end_date="{end}")', text, shown > 0


def _read_intake_count(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.intake import _queue_rows
    domain = str(e.get("domain") or agent)
    n = len(_queue_rows(domain))          # read-only: the cursor is NOT advanced
    text = (f"{n} new item{'s' if n != 1 else ''} in your intake queue — call "
            f'`read_intake_queue(domain="{domain}")` to read them.' if n
            else "nothing new in your intake queue.")
    return f"intake queue ({domain}) — count only", text, False


def _read_log_field(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.domain_counters import day_entry
    field = str(e.get("field") or "")
    # The persona's today, each field placed by when it was written — not the server's file date.
    entry = day_entry(ctx["today"])
    value = entry.get(field) if isinstance(entry, dict) else None
    text = (json.dumps(value, ensure_ascii=False) if value not in (None, {}, [], "")
            else f"nothing logged today under `{field}` yet.")
    return f"today's log — `{field}` field", _cap(text, ctx["cap"]), False


def _read_data_object(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.data_objects import fetch
    name = str(e.get("object") or "")
    got = fetch(agent, name, wait=False)
    title = (got.get("object") or {}).get("name") if isinstance(got, dict) else None
    # The entries (or the native reader's result), not the object's registry metadata.
    body = got
    if isinstance(got, dict) and "error" not in got:
        body = got["result"] if "result" in got else {k: got[k] for k in ("entries", "total")
                                                      if k in got}
    return (f'read_data_object(object="{title or name}")',
            _cap(json.dumps(body, ensure_ascii=False, default=str), ctx["cap"]), False)


def _read_counters(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.domain_counters import PREFETCH_HEADING, evidence_block
    body = evidence_block(agent, ctx["today"])
    return PREFETCH_HEADING, body, False


def _read_skill_habits(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.domain_counters import skill_habit_lines
    body = skill_habit_lines()
    return ("your skill-practice habits (task ledger — the streaks and misses are the ledger's)",
            body or "no skill-practice habit is open yet (`open_task` with `kind: habit`, "
                    "`domain: learning` starts one).", False)


_READERS: dict[str, Callable[[str, dict, dict], tuple[str, str, bool]]] = {
    "agent_config": _read_agent_config,
    "open_tasks": _read_open_tasks,
    "calendar": _read_calendar,
    "intake_count": _read_intake_count,
    "log_field": _read_log_field,
    "data_object": _read_data_object,
    "counters": _read_counters,
    "skill_habits": _read_skill_habits,
}


# --- the request trace's taint ---------------------------------------------------------------

def _mark_untrusted(agent: str) -> None:
    """Review L3, scoped: `agent`'s input this request carried outsider text through prefetch,
    so a WISDOM_PROPOSAL from THAT agent is filed `observed`, never `stated`. Other agents on the
    same turn are untouched (their input held none of it)."""
    try:
        from core import trace as _tr
        t = _tr.get_trace()
        if t is None:
            return
        with getattr(t, "_lock", None) or threading.Lock():
            agents = getattr(t, "prefetched_untrusted_agents", None)
            if not isinstance(agents, set):
                agents = set()
                t.prefetched_untrusted_agents = agents
            agents.add(agent)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] could not mark the trace untrusted: {exc}")


def _submit(fn, name: str) -> Future:
    """Run `fn` on a DAEMON thread and return its future. A read abandoned past its budget must
    never hold the process open at shutdown (a ThreadPoolExecutor's workers are joined at exit)."""
    fut: Future = Future()

    def _run() -> None:
        if not fut.set_running_or_notify_cancel():
            return
        try:
            fut.set_result(fn())
        except BaseException as exc:  # noqa: BLE001
            fut.set_exception(exc)
    threading.Thread(target=_run, name=name, daemon=True).start()
    return fut


def _local_now() -> datetime:
    from tools.ambient import _now_local
    return _now_local()


def _today(now: datetime):
    """The persona's ledger day for `now` (its zone and `day_starts`), as the medication view
    and tools/domain_counters reckon it."""
    from tools.domain_counters import ledger_day
    return ledger_day(now)


# --- build -----------------------------------------------------------------------------------

def build(agent: str, directive: str = "", user_text: str = "", persona: str | None = None,
          user_turn: bool = False, *, bare: bool = False,
          calendar_future: Future | None = None, now: datetime | None = None) -> str:
    """The PREFETCHED block for `agent`, or "" when it has none.

    `directive` and `user_text` are carried for the providers that resolve names from them
    (4c); nothing here reads the user's words on a turn that has none (`user_turn` False
    blanks them). `calendar_future` is 4-2's read made beside the Coordinator, used for
    Logistics' calendar block in place of a second fetch."""
    try:
        if bare:
            return ""
        cfg = load_config()
        plan = plan_for(agent, cfg)
        if not plan:
            return ""
        from core.persona import persona_scope, resolve_persona, current_persona
        p = resolve_persona(persona)           # on THIS thread; raises → nothing prefetched
        if not user_turn:
            user_text = ""
        with persona_scope(p):
            now = now or _local_now()
            today = _today(now)
        ctx = {"cap": int(cfg.get("cap_chars") or 6000),
               "timeout": float(cfg.get("read_timeout_s") or 4),
               "now": now, "today": today, "calendar_future": calendar_future,
               "directive": directive, "user_text": user_text}

        from core import trace as _tr
        caller = _tr.AgentRecord(agent=agent, provider="", model="")

        def _work(entry: dict) -> tuple[str, str, bool]:
            # The dispatching agent as the current agent — the thread-local dispatch_tool's
            # callers set — so a reader keyed on the caller answers as for that agent's own call.
            _tr._set_current_agent(caller)
            try:
                with persona_scope(p):
                    if current_persona() != p:     # never read one user's data for another
                        raise RuntimeError("persona not bound in the prefetch worker")
                    return _READERS[entry["read"]](agent, entry, ctx)
            finally:
                _tr._set_current_agent(None)

        # Code's lines and counts first; the wrapped calendar last, so nothing of code's follows
        # outsider text.
        plan = sorted(plan, key=lambda e: e.get("read") in _UNTRUSTED_KINDS)
        futures = [(e, _submit(lambda e=e: _work(e), f"prefetch-{agent}")) for e in plan]
        deadline = _monotonic() + ctx["timeout"]
        sections: list[str] = []
        untrusted = False
        for e, fut in futures:
            tool = READ_TOOLS[e["read"]]
            try:
                heading, text, tainted = fut.result(timeout=max(0.0, deadline - _monotonic()))
            except (_FutureTimeout, Exception) as exc:  # noqa: BLE001
                logger.warning(f"[prefetch] {agent}: {e['read']} not read in advance: "
                               f"{type(exc).__name__}: {exc}")
                sections.append(f"(not read in advance: call `{tool}`)")
                continue
            if not text:
                continue
            untrusted = untrusted or bool(tainted and e["read"] in _UNTRUSTED_KINDS)
            sections.append(f"### {heading}\n{text}")
        if not sections:
            return ""
        if untrusted:
            _mark_untrusted(agent)
        return _HEADING.format(hhmm=now.strftime("%H:%M")) + "\n\n" + "\n\n".join(sections)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] {agent}: nothing prefetched: {exc}")
        return ""


def _monotonic() -> float:
    import time
    return time.monotonic()


# --- 4-2: the calendar read made beside the Coordinator --------------------------------------

def speculative_calendar(persona: str | None) -> Future | None:
    """Start Logistics' calendar read (today and tomorrow) now, beside the Coordinator call, and
    return its future — or None when Logistics would not prefetch the calendar. Read-only; held
    only on the request: used for Logistics' block at dispatch, otherwise dropped. Never
    re-checks or writes an event (S6)."""
    try:
        if not any(e.get("read") == "calendar" for e in plan_for("logistics")):
            return None
        from core.persona import persona_scope, resolve_persona
        p = resolve_persona(persona)
        with persona_scope(p):
            today = _today(_local_now())
        start, end = today.isoformat(), (today + timedelta(days=1)).isoformat()

        def _work() -> tuple[dict, list[dict]]:
            with persona_scope(p):
                return _calendar_rows(start, end)

        return _submit(_work, "prefetch-calendar")
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] speculative calendar read not started: {exc}")
        return None


# --- #6: the Coordinator's PROACTIVE_FLAGS -----------------------------------------------------

PROACTIVE_FLAGS_HEADING = ("COORDINATOR PROACTIVE FLAGS (signals noticed this turn — weigh them; "
                           "do not repeat them verbatim)")
_FLAG_MAX_LINES = 5
_FLAG_MAX_CHARS = 600


def parse_proactive_flags(coord_output: str) -> str:
    """The `- ` lines under `PROACTIVE_FLAGS:` (to the next blank line or header), capped at 5
    lines and 600 characters, or "" — for absent, empty, placeholder or malformed sections."""
    import re
    if not coord_output or "PROACTIVE_FLAGS:" not in coord_output:
        return ""
    first, _, rest = coord_output.split("PROACTIVE_FLAGS:", 1)[1].partition("\n")
    lines: list[str] = []
    for raw in ([first] if first.strip() else []) + rest.splitlines():
        line = raw.strip()
        if not line:
            if lines:
                break
            continue
        if re.match(r"^[A-Z][A-Z_ ]+:", line) or line.startswith("```"):
            break
        if not line.startswith("- "):
            break
        body = line[2:].strip()
        if not body or body.lower().strip(".") in {"none", "n/a", "no flags", "nothing"} \
                or body.startswith("[signal source]"):
            continue
        lines.append(f"- {body}")
        if len(lines) >= _FLAG_MAX_LINES:
            break
    text = "\n".join(lines)
    if len(text) > _FLAG_MAX_CHARS:
        text = text[:_FLAG_MAX_CHARS].rsplit("\n", 1)[0] or text[:_FLAG_MAX_CHARS]
    return text


def flags_block(coord_output: str) -> str:
    body = parse_proactive_flags(coord_output)
    return f"{PROACTIVE_FLAGS_HEADING}:\n{body}" if body else ""

