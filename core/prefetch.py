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
10. **Names resolve exactly, or not at all** (4c, tools/contact_resolution.py): a person is
    never picked from several, merged or created, and the stored tone shape is handed over but
    `get_tone_shape` is never called (it would start a mailbox sweep).

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
    # The weekly Pattern Miner's fixed steps 1, 2, 3b and 4, and M16's baseline row (4e).
    "recent_insights": "read_recent_insights",
    "wisdom": "read_wisdom",
    "log_windows": "get_log_window",
    "wisdom_duplicates": "find_duplicate_wisdom",
    "baseline_row": "get_baseline_context",
    "baseline_periods": "read_baseline_periods",
    "people": "read_contact",
}

# Not an evidence agent (it gets no PROACTIVE_FLAGS and no headline), but its fixed reads are
# made by code — on its scheduled single-agent run only (see `pattern_miner_run`).
_ANALYSIS_AGENTS = frozenset({"pattern_miner"})

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
    if agent in _ANALYSIS_AGENTS:
        return not pattern_miner_run()
    return agent == "research_agent" or agent in _UNTRUSTED_OUTPUT_AGENTS \
        or agent not in _eligible_agents()


def pattern_miner_run(rec=None) -> bool:
    """Is this the scheduler's own Pattern Miner job? Keyed on the explicit marker the scheduled
    single-agent path sets (`trace.scheduled_job`, set by run_session(scheduled_job=True) from
    /internal/session only when scheduler.yaml names the Pattern Miner for the matched job) —
    never on "proactive" alone. And the Pattern Miner must be the request's root agent: before
    its record exists (`rec` None) no agent has started; after, `rec` is the root. A Pattern Miner
    the Coordinator dispatches (on any turn, proactive included), a run_subagent consult or a
    fire-and-forget run gets no bulk reads, and code writes no report from it."""
    try:
        from core import trace as _tr
        t = _tr.get_trace()
        if t is None or not getattr(t, "scheduled_job", None):
            return False
        if rec is None:
            return not t.pipeline
        return bool(t.pipeline) and t.pipeline[0] is rec
    except Exception:  # noqa: BLE001
        return False


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


# --- the Pattern Miner's fixed reads (#20, M16) --------------------------------------------------

def _entry_cap(e: dict, ctx: dict) -> int:
    return int(e.get("cap_chars") or ctx["cap"])


def _read_recent_insights(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.pattern_miner import read_recent_insights
    n = int(e.get("n") or 2)
    got = read_recent_insights(n=n)
    text = (json.dumps(got, ensure_ascii=False, indent=1) if got
            else "no earlier report on file.")
    return (f"read_recent_insights(n={n}) — what has already been surfaced",
            _cap(text, _entry_cap(e, ctx)), False)


def _read_wisdom(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.wisdom import read_wisdom
    got = read_wisdom()
    text = json.dumps(got, ensure_ascii=False) if got else "the wisdom store is empty."
    return ("read_wisdom() — documented patterns (newest first, capped)",
            _cap(text, _entry_cap(e, ctx)), False)


def _read_log_windows(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    """One read of the widest window, most recent `max_entries` kept, bands before 2026-08-09
    stripped. The 7- and 30-day windows are subsets of it (≤ 30 entries each, so always inside
    the most recent 45) — listed by their dates, not sent twice."""
    from tools.pattern_miner import get_log_window
    from tools.pattern_report import BANDS_FROM, strip_free_text_bands, windows
    cap_n = int(e.get("max_entries") or 45)
    wins = windows(ctx["today"])
    widest = max(wins, key=lambda w: w[0])
    entries = get_log_window(widest[1].isoformat(), widest[2].isoformat())
    shown = strip_free_text_bands(entries[-cap_n:] if cap_n else entries)
    lines = []
    for n, start, end in wins:
        count = sum(1 for x in entries if start.isoformat() <= str(x.get("date", "")) <= end.isoformat())
        lines.append(f"- {n}-day window {start.isoformat()} → {end.isoformat()}: "
                     f"{count} day{'s' if count != 1 else ''} logged")
    head = "\n".join(lines)
    if cap_n and len(entries) > cap_n:
        head += (f"\n(the {widest[0]}-day window holds {len(entries)} logged days; the most "
                 f"recent {cap_n} are below — call `get_log_window` for earlier ones)")
    head += (f"\nEntries dated before {BANDS_FROM.isoformat()} have their free-text bands "
             f"(`wellbeing.mood`, `wellbeing.intensity`, `health.energy`) removed; "
             f"`sleep_hours` is kept.")
    body = "\n".join(json.dumps(x, ensure_ascii=False, default=str) for x in reversed(shown))
    text = f"{head}\n\nNewest first:\n{body}" if shown else f"{head}\n\nno logs in the window."
    return ("get_log_window — the analysis windows", _cap(text, _entry_cap(e, ctx)), False)


def _read_wisdom_duplicates(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.wisdom import find_duplicate_wisdom
    groups = find_duplicate_wisdom()
    text = (json.dumps(groups, ensure_ascii=False) if groups
            else "no near-duplicate groups found.")
    return ("find_duplicate_wisdom() — groups to consolidate with `merge_wisdom_entries`",
            _cap(text, _entry_cap(e, ctx)), False)


def _read_baseline_row(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.baselines import get_baseline_context
    from tools.pattern_report import baseline_label, data_span, windows
    lines = [f"Your baseline row: {baseline_label(data_span())}"]
    for n, start, end in windows(ctx["today"]):
        got = get_baseline_context(start.isoformat(), end.isoformat())
        names = [str(p.get("label") or p.get("name") or p.get("id") or "?") for p in got]
        lines.append(f"- {n}-day window overlaps labelled baseline period"
                     f"{'s' if len(names) != 1 else ''}: {', '.join(names) if names else 'none'}")
    return ("your baseline row for the data span, and the labelled periods each window overlaps",
            "\n".join(lines), False)


def _read_baseline_periods(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    from tools.baselines import read_baseline_periods
    got = read_baseline_periods()
    text = json.dumps(got, ensure_ascii=False) if got else "no labelled baseline periods."
    return ("read_baseline_periods() — labelled periods", _cap(text, _entry_cap(e, ctx)), False)
def _read_people(agent: str, e: dict, ctx: dict) -> tuple[str, str, bool]:
    """4c (#12, M2, M3, #16): the people this dispatch names, matched exactly to contacts, the
    overdue and upcoming-dates lists, and what is on file naming them. Resolved from the
    directive and — on a real user turn only — the user's words (build() blanks them otherwise).
    Never calls get_tone_shape; never writes."""
    from tools.contact_resolution import DEFAULT_UPCOMING_DAYS, people_block
    from tools.recipient_context import on_file_block
    try:
        days = int(e.get("upcoming_days") or DEFAULT_UPCOMING_DAYS)
    except (TypeError, ValueError):
        days = DEFAULT_UPCOMING_DAYS
    from tools.crm import _load_contacts
    try:
        contacts = _load_contacts()
    except Exception as exc:  # noqa: BLE001 — people_block reports and degrades on its own
        logger.warning(f"[prefetch] contacts unreadable: {exc}")
        contacts = None
    # Records, overdue and dates first; #16's block after, under its own time budget, so a slow
    # past-entry search can never cost the records (review of 56cce4f, item 5).
    named, lists, resolved = people_block(ctx.get("directive") or "",
                                          ctx.get("user_text") or "", ctx["today"], days,
                                          contacts=contacts, cache=ctx.get("request_cache"))
    on_file = on_file_block(resolved, agent, contacts) if resolved else ""
    body = "\n\n".join(x for x in (named, on_file, lists) if x)
    return ("people named here, overdue contacts and upcoming dates (matched exactly by code)",
            _cap(body, ctx["cap"]), False)


_READERS: dict[str, Callable[[str, dict, dict], tuple[str, str, bool]]] = {
    "agent_config": _read_agent_config,
    "open_tasks": _read_open_tasks,
    "calendar": _read_calendar,
    "intake_count": _read_intake_count,
    "log_field": _read_log_field,
    "data_object": _read_data_object,
    "counters": _read_counters,
    "skill_habits": _read_skill_habits,
    "recent_insights": _read_recent_insights,
    "wisdom": _read_wisdom,
    "log_windows": _read_log_windows,
    "wisdom_duplicates": _read_wisdom_duplicates,
    "baseline_row": _read_baseline_row,
    "baseline_periods": _read_baseline_periods,
    "people": _read_people,
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
          calendar_future: Future | None = None, now: datetime | None = None,
          local: bool = False) -> str:
    """The PREFETCHED block for `agent`, or "" when it has none.

    `local`: the agent runs on the local model. For the Pattern Miner the whole block is then
    held to `local_cap_chars` (prefetch.yaml) so it fits the local context window — each section
    cut in proportion, newest log entries kept (Fable review E).

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
        from core import trace as _tr
        _t = _tr.get_trace()
        ctx = {"request_cache": getattr(_t, "request_cache", None) if _t is not None else None,
               "cap": int(cfg.get("cap_chars") or 6000),
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
        # An entry may carry its own `timeout_s` (the Pattern Miner's duplicate scan loads the
        # embedder); the budget is the longest one asked for, never less than the default.
        budget = max([ctx["timeout"]] + [float(e.get("timeout_s") or 0) for e in plan])
        deadline = _monotonic() + budget
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
        if local and agent in _ANALYSIS_AGENTS:
            sections = _fit_sections(sections, int(cfg.get("local_cap_chars") or 16000))
        if untrusted:
            _mark_untrusted(agent)
        return _HEADING.format(hhmm=now.strftime("%H:%M")) + "\n\n" + "\n\n".join(sections)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] {agent}: nothing prefetched: {exc}")
        return ""


def _fit_sections(sections: list[str], cap: int) -> list[str]:
    """Cut each section to its proportional share of `cap` characters, with a note saying so."""
    total = sum(len(s) for s in sections)
    if total <= cap:
        return sections
    note = "\n… (cut to fit the local model's context — call the tool for the rest)"
    out = []
    for s in sections:
        share = max(200, int(cap * len(s) / total) - len(note))
        out.append(s if len(s) <= share else s[:share] + note)
    return out


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


# --- #6 (4e): the Pattern Miner headline -------------------------------------------------------

HEADLINE_MAX_AGE_DAYS = 14
_HEADLINE_MAX_ITEMS = 3
_HEADLINE_MAX_WORDS = 60


def _report_date(report: dict) -> datetime | None:
    for key in ("date", "generated_at"):
        raw = str(report.get(key) or "")[:10]
        try:
            return datetime.strptime(raw, "%Y-%m-%d")
        except ValueError:
            continue
    return None


def pattern_headline(persona: str | None = None, today=None) -> str:
    """Up to 3 moderate-or-strong observations from the latest Pattern Miner report, each at
    most 60 words, with the report's date — or "" when the report is missing, older than 14
    days, or has no observation of that confidence (a shapeless report). A stale report is
    how a pattern-from-nothing happens, so it is never passed. Never raises."""
    try:
        from core.persona import persona_scope, resolve_persona
        from tools.pattern_miner import read_recent_insights
        from tools.pattern_report import confidence_level
        p = resolve_persona(persona)
        with persona_scope(p):
            got = read_recent_insights(n=1)
            if today is None:
                today = _local_now().date()
        if not got or not isinstance(got[0], dict):
            return ""
        report = got[0]
        when = _report_date(report)
        if when is None or (today - when.date()).days > HEADLINE_MAX_AGE_DAYS \
                or when.date() > today:
            return ""
        lines: list[str] = []
        for o in report.get("observations") or []:
            if not isinstance(o, dict):
                continue
            level = o.get("confidence_level") or confidence_level(str(o.get("confidence") or ""))
            text = " ".join(str(o.get("observation") or "").split())
            if level not in ("moderate", "strong") or not text:
                continue
            words = text.split()
            if len(words) > _HEADLINE_MAX_WORDS:
                text = " ".join(words[:_HEADLINE_MAX_WORDS]) + " …"
            lines.append(f"- {text} (confidence: {level})")
            if len(lines) >= _HEADLINE_MAX_ITEMS:
                break
        if not lines:
            return ""
        return (f"PATTERN MINER HEADLINE (weekly report of {when.date().isoformat()} — patterns "
                f"in the user's own logs; hypotheses to weigh, not facts to announce):\n"
                + "\n".join(lines))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[prefetch] Pattern Miner headline unavailable: {exc}")
        return ""

