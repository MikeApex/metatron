"""
tools/capture.py — capture fidelity: what the user said, against what was kept.

Plan: archive/plans/capture_fidelity_plan_2026-11-18.md. Review:
archive/plans/adversarial_review_capture_fidelity_plan_2026-11-18.md.

A user tells Metatron a fact about their life; the agent acknowledges it and never saves it.
Nothing tells either of them. An instruction to "save each fact in the turn it is given" did
not hold (trial_1029, 2026-10-29), so this is code: an independent extractor reads the user's
turn, code compares what it found with what the turn actually wrote, and the agent is shown
what is missing. **The agent stays the only writer** — this module proposes, never saves
(Mike, 2026-11-18: a wrong save does more harm than a missing one).

Two paths, one mechanism:

- **Ordinary turns** (`start` → `note_for_synthesizer` → `after_synthesizer`). The extractor
  runs on a thread beside the Coordinator; after the specialists it is joined, compared, and
  the misses reach the Synthesizer's single pass as a CAPTURE NOTE. After the Synthesizer,
  each shown proposal's outcome is recorded. During a user's measurement window one turn in
  five is a holdout — compared, never shown — because once the note exists it is the only way
  to see what the Synthesizer saves unprompted (plan review 1).
- **Interviews** (`snapshot` / `start` / `take_for_interview` / `after_interview_turn`). The
  interviewer has no stage to hide a call behind, so a miss is shown on the next turn's
  coverage block. What the turn wrote is the before/after diff of the stored record — the
  interviewer's own trace is gone by the time `run_turn` gets control back (plan review 2).

What is kept:

- `capture/pending.json` — proposals not yet shown, at most `cap`, each expiring after
  `expiry_hours`. These carry the user's facts: sensitive tier, in the persona's own
  directory like every other record of theirs.
- `capture/outcomes.jsonl` — the training record. **Content-free**: counts, kinds, targets,
  dispositions and outcomes, never a value or a quote (`_ROW_KEYS`, asserted by the tests).
  Append-only and never compacted, like the A9 rows.
- `capture/state.json` — the first day capture ran for this persona, which opens the window.

Extractor calls with no parent trace own one tagged `source="capture"`, which A9's rollup and
the backfill reader both skip, so a measurement run never measures itself (plan review 3).

CLI (on the VM, persona required):
    python3 -m tools.capture --report  --persona mike [--since YYYY-MM-DD]
    python3 -m tools.capture --backfill --persona mike --days 60
    python3 -m tools.capture --label    --persona mike
    python3 -m tools.capture --score    --persona mike
    python3 -m tools.capture --eval tests/fixtures/capture/trial_1029.json --persona mike
"""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import logging
import re
import threading
import time
import uuid
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from pathlib import Path

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parent.parent
_CONFIG = ROOT / "config" / "modules" / "capture.yaml"
AGENT = "capture_extractor"

# Which tool records each kind. The writer is whichever agent holds it on that path.
KIND_TOOLS = {
    "day_shape": "set_day_shape",
    "goal": "update_goal",
    "task": "open_task",
    "preference": "write_persona",
    "profile": "write_profile",
}
# Where else each kind is legitimately recorded. The backfill (2026-11-18) found most "misses"
# were saved, just not by the kind's own tool: Logistics files tasks as obligations, calendar
# events, shopping-archive items, horizon items and scheduled reminders; the Diarist files
# stated preferences as wisdom; Logistics keeps some as its own agent config. A write to any
# of these whose text carries the candidate's words counts as kept — the note must never ask
# the agent to save, a second time, what another agent already filed.
KIND_HOMES = {
    "day_shape": ("write_calendar_event", "update_calendar_event", "write_wisdom"),
    "goal": ("write_goals", "write_wisdom"),
    "task": ("open_obligation", "write_calendar_event", "write_archive", "record_horizon_item",
             "write_schedule", "request_build", "update_task"),
    "preference": ("write_wisdom", "write_agent_config", "write_profile"),
    "profile": ("write_wisdom", "write_persona"),
}
_RECORDING_TOOLS = frozenset(KIND_TOOLS.values()) | {t for v in KIND_HOMES.values() for t in v}

AGENT_KINDS = {
    "goals_interviewer": ("day_shape", "goal"),
    "synthesizer": ("day_shape", "goal", "task", "preference", "profile"),
}
DISPOSITIONS = ("save", "ask", "declined")

# The text a write is matched on, per tool — the free-text field the model phrases itself.
_TEXT_ARGS = {
    "open_task": ("what",),
    "update_goal": ("title", "shareable_what"),
    "write_persona": ("content",),
    "write_profile": ("field", "value"),
}

# Day-shape sections an extractor may propose. `calendars` needs a calendar id and
# `event_rules` a title match — neither is said in passing — so both are left to the agent.
_SHAPE_TARGETS = ("day", "windows", "routines", "meals", "children_home", "day_overrides",
                  "travel_mode", "location_sharing", "work_days", "work_start", "work_end")

# The same fact can be written in either of set_day_shape's two forms — a section entry, or
# a first-version field (`goals_interviewer.md` records working hours as `work_start`/
# `work_end`). A write to a related key whose times cover the candidate's counts as saved.
_RELATED = {
    "day": ("day", "wake", "bed", "wake_weekend", "bed_weekend"),
    "windows": ("windows", "focus", "personal", "work_start", "work_end", "work_days"),
    "meals": ("meals", "breakfast", "lunch", "dinner"),
    "work_start": ("work_start", "windows"), "work_end": ("work_end", "windows"),
    "work_days": ("work_days",),
}
_HM_RE = re.compile(r"\b\d{2}:\d{2}\b")

_ROW_KEYS = frozenset({
    "ts", "row", "request_id", "agent", "kind", "target", "disposition", "outcome",
    "holdout", "window_day", "candidates", "extractor_ms", "extractor_tokens_in",
    "extractor_tokens_out",
})

_DEFAULTS = {
    "enabled": False,
    "holdout_rate": 0.2,
    "window_days": 14,
    "join_bound_s": 0.5,
    "cap": 3,
    "expiry_hours": 24,
    "history_messages": 6,
    "saved_record_chars": 2400,
    "match_overlap": 0.5,
    # The plan's minimums (§ 5.3), so a capture.yaml missing them never makes a gate lenient.
    "minimums": {"precision": 0.90, "recall": 0.80, "matcher": 0.90,
                 "miss_rate_reduction": 0.75, "accept_rate": 0.75},
}


# --- config & paths ----------------------------------------------------------------------------

def config() -> dict:
    """capture.yaml over the defaults. Never raises — a bad file leaves capture off."""
    try:
        import yaml
        data = yaml.safe_load(_CONFIG.read_text()) or {}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[capture] config unreadable, capture off: {exc}")
        return dict(_DEFAULTS)
    merged = {**_DEFAULTS, **{k: v for k, v in data.items() if v is not None}}
    merged["minimums"] = {**_DEFAULTS["minimums"], **(data.get("minimums") or {})}
    return merged


def enabled() -> bool:
    return bool(config().get("enabled"))


def _dir(persona: str) -> Path:
    from core.persona import persona_data_dir
    d = persona_data_dir(persona) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    return d


@contextmanager
def _locked(persona: str):
    with open(_dir(persona) / ".lock", "w") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text()) if path.exists() else default
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1))
    tmp.replace(path)


def _now() -> datetime:
    return datetime.now()


# --- the window and the holdout ----------------------------------------------------------------

def window_day(persona: str, today: date | None = None) -> int:
    """Days since capture first ran for this persona; pins the first day on first call."""
    today = today or _now().date()
    path = _dir(persona) / "state.json"
    with _locked(persona):
        state = _read_json(path, {})
        first = state.get("first_day")
        if not first:
            first = today.isoformat()
            state["first_day"] = first
            _write_json(path, state)
    try:
        return (today - date.fromisoformat(first)).days
    except ValueError:
        return 0


def is_holdout(request_id: str, day: int, cfg: dict | None = None) -> bool:
    """A seeded draw: the same request always draws the same way, so a rerun cannot flip it."""
    cfg = cfg or config()
    rate = float(cfg.get("holdout_rate") or 0)
    if rate <= 0 or day >= int(cfg.get("window_days") or 0):
        return False
    n = int(hashlib.sha256(request_id.encode()).hexdigest()[:16], 16) / float(1 << 64)
    return n < rate


# --- what is already saved -----------------------------------------------------------------------

def _shape(persona: str) -> dict:
    try:
        from tools.day_shape import read_shape
        return read_shape(persona) or {}
    except Exception:  # noqa: BLE001
        return {}


def _goal_titles(persona: str) -> list[str]:
    """Titles only — never `private_why`, which no extractor input may carry."""
    import yaml
    from core.persona import persona_config_dir
    path = persona_config_dir(persona) / "goals.yaml"
    try:
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
    except Exception:  # noqa: BLE001
        return []
    out = []
    for items in (data or {}).values():
        for g in items if isinstance(items, list) else []:
            if isinstance(g, dict) and g.get("title"):
                out.append(str(g["title"]))
    return out


def _task_titles(persona: str) -> list[str]:
    try:
        from tools.obligations import _load
        return [str(t.get("what") or "") for t in _load(persona)
                if (t.get("status") or "open") == "open" and t.get("what")]
    except Exception:  # noqa: BLE001
        return []


def _profile_lines(persona: str) -> list[str]:
    import yaml
    from core.persona import persona_config_dir
    path = persona_config_dir(persona) / "profile.yaml"
    try:
        data = yaml.safe_load(path.read_text()) if path.exists() else {}
    except Exception:  # noqa: BLE001
        return []
    return [f"{k}: {v}" for k, v in (data or {}).items()
            if isinstance(v, (str, int, float)) and str(v).strip()]


def _preference_lines(persona: str) -> list[str]:
    from core.persona import persona_config_dir
    path = persona_config_dir(persona).parent / f"{persona}.md"
    try:
        text = path.read_text() if path.exists() else ""
    except OSError:
        return []
    return [ln.strip("-* ").strip() for ln in text.splitlines()
            if ln.strip().startswith(("-", "*")) and len(ln.strip()) > 3]


def saved_texts(persona: str, kinds: tuple[str, ...]) -> dict[str, list[str]]:
    """What is already recorded, per free-text kind — the matcher's "already held" side."""
    out: dict[str, list[str]] = {}
    if "goal" in kinds:
        out["goal"] = _goal_titles(persona)
    if "task" in kinds:
        out["task"] = _task_titles(persona)
    if "profile" in kinds:
        out["profile"] = _profile_lines(persona)
    if "preference" in kinds:
        out["preference"] = _preference_lines(persona)
    return out


def saved_record_text(persona: str, kinds: tuple[str, ...], limit: int | None = None) -> str:
    """The extractor's view of what is saved — readable entries, never `day_shape.digest()`,
    which is a 16-character hash for the planner's change gate (plan review 4)."""
    limit = limit or int(config()["saved_record_chars"])
    lines: list[str] = []
    if "day_shape" in kinds:
        shape = _shape(persona)
        for sec in _SHAPE_TARGETS:
            val = shape.get(sec)
            if val in (None, [], {}, ""):
                continue
            lines.append(f"day shape / {sec}: {json.dumps(val, ensure_ascii=False)}")
    labels = {"goal": "goal", "task": "open task", "profile": "profile",
              "preference": "preference"}
    for kind, texts in saved_texts(persona, kinds).items():
        for t in texts:
            lines.append(f"{labels[kind]}: {t}")
    text = "\n".join(lines) or "(nothing recorded yet)"
    return text if len(text) <= limit else text[:limit] + "\n(… more recorded)"


# --- the extractor ---------------------------------------------------------------------------------

def catalogue(kinds: tuple[str, ...]) -> str:
    """What each kind and day-shape target takes, generated from the tools' own tables so the
    extractor cannot drift from what they accept."""
    from tools.day_shape import FIELDS, SECTIONS
    lines = []
    if "day_shape" in kinds:
        lines.append("kind day_shape — the target is one of these sections, and proposal is the "
                     "entry exactly as described:")
        for sec in _SHAPE_TARGETS:
            desc = SECTIONS.get(sec) or FIELDS.get(sec, "")
            lines.append(f"  {sec}: {desc}")
    plain = {"goal": "something the user wants to achieve, stated as a goal",
             "task": "something the user needs or means to do (not something already done)",
             "preference": "how the user wants Metatron to behave with them",
             "profile": "a stable fact about who the user is (work, family, home, health basics)"}
    for kind in kinds:
        if kind in plain:
            lines.append(f"kind {kind} — {plain[kind]}. target is \"{kind}\"; proposal is one "
                         f"plain sentence.")
    return "\n".join(lines)


def build_input(persona: str, user_input: str, history: list[dict] | None,
                kinds: tuple[str, ...]) -> str:
    n = int(config()["history_messages"])
    convo = []
    for m in (history or [])[-n:]:
        if isinstance(m, dict) and isinstance(m.get("content"), str):
            convo.append(f"{m.get('role', '?')}: {m['content'][:1200]}")
    return (
        f"TODAY: {_now().date().isoformat()} ({_now():%A})\n\n"
        f"WHAT CAN BE RECORDED:\n{catalogue(kinds)}\n\n"
        f"ALREADY RECORDED:\n{saved_record_text(persona, kinds)}\n\n"
        f"RECENT CONVERSATION (oldest first):\n" + ("\n".join(convo) or "(none)") + "\n\n"
        f"THE USER'S MESSAGE THIS TURN:\n<user_words>\n{user_input}\n</user_words>"
    )


_JSON_RE = re.compile(r"\[.*\]", re.S)
_IDENT_RE = re.compile(r"\b[a-z]+_[a-z_]+\b")


def parse(raw: str, kinds: tuple[str, ...]) -> tuple[list[dict], int]:
    """(candidates, rejected). Malformed output is no candidates — never an exception."""
    m = _JSON_RE.search(raw or "")
    if not m:
        return [], (0 if (raw or "").strip() in ("", "[]") else 1)
    try:
        items = json.loads(m.group(0))
    except ValueError:
        return [], 1
    if not isinstance(items, list):
        return [], 1
    out, rejected = [], 0
    for it in items:
        c = _validate_candidate(it, kinds)
        if c is None:
            rejected += 1
        else:
            out.append(c)
    return out, rejected


def _validate_candidate(it, kinds: tuple[str, ...]) -> dict | None:
    if not isinstance(it, dict):
        return None
    kind = str(it.get("kind") or "").strip()
    disp = str(it.get("disposition") or "").strip()
    if kind not in kinds or disp not in DISPOSITIONS:
        return None
    say = " ".join(str(it.get("say") or "").split())[:200]
    quote = " ".join(str(it.get("quote") or "").split())[:120]
    if not say or _IDENT_RE.search(say):
        return None     # the note travels in the turn's input: no identifiers (plan § 4.5)
    target = str(it.get("target") or kind).strip()
    proposal = it.get("proposal")
    if kind == "day_shape":
        if target not in _SHAPE_TARGETS:
            return None
        clean = _validate_shape(target, proposal)
        if clean is None and disp != "declined":
            return None
        proposal = clean
    else:
        target = kind
        proposal = " ".join(str(proposal or say).split())[:200]
    return {"kind": kind, "target": target, "proposal": proposal, "disposition": disp,
            "say": say, "quote": quote}


def _validate_shape(section: str, proposal):
    """day_shape's own validators — a day-shape note never proposes what the tool refuses."""
    from tools import day_shape as ds
    if isinstance(proposal, str):
        try:
            proposal = json.loads(proposal)
        except ValueError:
            pass
    if section in ds._LIST_SECTIONS:
        if not isinstance(proposal, dict):
            return None
        clean, why = ds._validate_entry(section, proposal)
        return None if why else clean
    clean, why = ds._validate(section, proposal)
    return None if why else clean


def _agent_tokens(trace, name: str = AGENT) -> tuple[int, int]:
    def walk(recs):
        tin = tout = 0
        for r in recs or []:
            if getattr(r, "agent", None) == name:
                for t in getattr(r, "turns", []):
                    tin += int(getattr(t, "input_tokens", 0) or 0)
                    tout += int(getattr(t, "output_tokens", 0) or 0)
            a, b = walk(getattr(r, "subagents", []))
            tin, tout = tin + a, tout + b
        return tin, tout
    return walk(getattr(trace, "pipeline", [])) if trace is not None else (0, 0)


def _within_spend() -> bool:
    """The daily spend cap and the hourly stop, WITHOUT counting this call as a session.

    `_spend_gate()` also calls `note_session_start()`, so every extractor call would count
    toward `stop_sessions_per_hour` (60): an interview turn would count twice and could refuse
    the user mid-interview, and the backfill would stop itself after 60 calls. An extractor
    call is part of a turn, not a session. Fails open, as `_spend_gate()` does."""
    try:
        from core.spend_guard import SpendLimitExceeded, check_before_session
        try:
            check_before_session()
        except SpendLimitExceeded as exc:
            logger.warning(f"[capture] extractor skipped by the spend guard: {exc}")
            return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[capture] spend check error, allowing: {exc}")
    return True


def extract(persona: str, user_input: str, history: list[dict] | None,
            kinds: tuple[str, ...], trace=None) -> dict:
    """One extractor call. With `trace`, it nests in the user's turn; without, it owns a
    `source="capture"` trace and checks the spend guard itself (plan review 3)."""
    from core import trace as _tr
    from core.orchestrator import run_session
    from core.persona import persona_scope
    t0 = time.monotonic()
    result = {"candidates": [], "rejected": 0, "ok": False, "ms": 0, "tin": 0, "tout": 0}
    text = build_input(persona, user_input, history, kinds)
    owned = None
    with persona_scope(persona):
        try:
            if trace is not None:
                _tr.set_trace(trace)
            else:
                if not _within_spend():
                    return result
                owned = _tr.start_request_trace(user_input[:200], persona, is_proactive=True,
                                                source="capture")
            raw = run_session(AGENT, user_input=text, persona=persona, complexity="quick",
                              bare=True, proactive=True)
            result["candidates"], result["rejected"] = parse(raw, kinds)
            result["ok"] = True
            result["tin"], result["tout"] = _agent_tokens(owned or trace)
        except Exception as exc:  # noqa: BLE001 — capture must never take a turn down
            logger.warning(f"[capture] extractor failed: {exc}")
        finally:
            if owned is not None:
                _tr.finish_request_trace("")
            _tr.set_trace(None)
    result["ms"] = int((time.monotonic() - t0) * 1000)
    return result


class Job:
    """An extractor call on its own thread. `wait` is bounded; a result that arrives after the
    caller stopped waiting is handed to `late` (it becomes pending for the next turn)."""

    def __init__(self, persona: str, agent: str, request_id: str):
        self.persona, self.agent, self.request_id = persona, agent, request_id
        self.result: dict | None = None
        self._done = threading.Event()
        self._lock = threading.Lock()
        self._late = None

    def _run(self, *args) -> None:
        self.result = extract(*args)
        with self._lock:
            self._done.set()
            late = self._late
        if late is not None:
            try:
                late(self.result)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[capture] late result dropped: {exc}")

    def wait(self, timeout: float, late=None) -> dict | None:
        if self._done.wait(timeout):
            return self.result
        with self._lock:
            if self._done.is_set():
                return self.result
            self._late = late
        return None


def start(persona: str, user_input: str, history: list[dict] | None, agent: str,
          trace=None) -> Job | None:
    """Start the extractor for a real user turn, or None when capture is off. The caller has
    already established the turn is the user's own (`has_real_user_turn`)."""
    if not enabled() or agent not in AGENT_KINDS or not (user_input or "").strip():
        return None
    rid = getattr(trace, "trace_id", None) or uuid.uuid4().hex[:12]
    job = Job(persona, agent, rid)
    hist = [dict(h) for h in history] if history else None     # never the caller's live list
    threading.Thread(target=job._run, daemon=True, name="capture",
                     args=(persona, user_input, hist, AGENT_KINDS[agent], trace)).start()
    return job


# --- what this turn wrote ----------------------------------------------------------------------

def writes_from_trace(trace) -> list[tuple[str, dict]]:
    """Every write-tool call in the turn's trace, with its arguments, subagents included."""
    out: list[tuple[str, dict]] = []
    wanted = _RECORDING_TOOLS

    def walk(rec) -> None:
        for turn in getattr(rec, "turns", []):
            for call in getattr(turn, "tool_calls", []):
                name = getattr(call, "name", "")
                if name in wanted and getattr(call, "ok", True):
                    out.append((name, dict(getattr(call, "args", {}) or {})))
        for sub in getattr(rec, "subagents", []):
            walk(sub)

    for rec in getattr(trace, "pipeline", []) if trace is not None else []:
        walk(rec)
    return out


def writes_from_trace_dict(record: dict) -> list[tuple[str, dict]]:
    """The same, from a serialised trace line — the backfill's input."""
    out: list[tuple[str, dict]] = []
    wanted = _RECORDING_TOOLS

    def walk(rec: dict) -> None:
        for turn in rec.get("turns") or []:
            for call in turn.get("tool_calls") or []:
                if call.get("name") in wanted and call.get("ok", True):
                    out.append((call["name"], dict(call.get("args") or {})))
        for sub in rec.get("subagents") or []:
            walk(sub)

    for rec in record.get("pipeline") or []:
        walk(rec)
    return out


def snapshot(persona: str) -> dict:
    """The interviewer's two records, for the before/after diff (plan review 2)."""
    return {"shape": json.loads(json.dumps(_shape(persona), default=str)),
            "goals": _goal_titles(persona)}


def writes_from_snapshots(before: dict, after: dict) -> list[tuple[str, dict]]:
    out: list[tuple[str, dict]] = []
    b, a = before.get("shape") or {}, after.get("shape") or {}
    for sec in _SHAPE_TARGETS:
        bv, av = b.get(sec), a.get(sec)
        if isinstance(av, list):
            old = [json.dumps(x, sort_keys=True) for x in (bv if isinstance(bv, list) else [])]
            for e in av:
                if json.dumps(e, sort_keys=True) not in old:
                    out.append(("set_day_shape", {"section": sec, "entry": e}))
        elif av != bv and av not in (None, ""):
            out.append(("set_day_shape", {"section": sec, "value": av}))
    for t in after.get("goals") or []:
        if t not in (before.get("goals") or []):
            out.append(("update_goal", {"title": t}))
    return out


# --- matching ------------------------------------------------------------------------------------------

_STOP = frozenset("""a an the to and or of in on at for with by from my me i im i'm is are was be been
it this that these those do does did have has had will would should can could just about
really very so up out over into then than as but not no yes we our you your they them their
he she his her its get got go going want need like""".split())
_WORD_RE = re.compile(r"[a-z0-9']+")


def _stem(w: str) -> str:
    return w[:-1] if len(w) > 3 and w.endswith("s") and not w.endswith("ss") else w


def _words(text: str) -> set[str]:
    return {_stem(w) for w in _WORD_RE.findall((text or "").lower().replace("_", " "))
            if w not in _STOP and len(w) > 1}


def text_overlap(candidate: str, written: str) -> float:
    cw = _words(candidate)
    return len(cw & _words(written)) / len(cw) if cw else 0.0


def _write_text(tool: str, args: dict) -> str:
    return " ".join(str(args.get(k) or "") for k in _TEXT_ARGS.get(tool, ()))


def _shape_write(args: dict):
    """(section, clean value) from a set_day_shape call's arguments, either calling form."""
    sec = str(args.get("section") or args.get("field") or "").strip().lower()
    val = args.get("entry") if args.get("entry") is not None else args.get("value")
    if args.get("date") and isinstance(val, (dict, str)):
        val = {**(json.loads(val) if isinstance(val, str) else val), "date": args["date"]}
    return sec, _validate_shape(sec, val)


def _leaf_text(value) -> str:
    """Every string in a tool call's arguments, for matching a write by its words."""
    if isinstance(value, dict):
        return " ".join(_leaf_text(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(_leaf_text(v) for v in value)
    if isinstance(value, str):
        try:
            return _leaf_text(json.loads(value)) if value[:1] in "{[" else value
        except ValueError:
            return value
    return ""


def kept_elsewhere(c: dict, writes: list[tuple[str, dict]], overlap: float | None = None) -> bool:
    """Was it recorded by another of the kind's homes (`KIND_HOMES`)?"""
    need = float(overlap if overlap is not None else config()["match_overlap"])
    homes = KIND_HOMES.get(c["kind"], ())
    phrasings = [t for t in (c.get("say"), c.get("proposal")) if isinstance(t, str) and t]
    return any(name in homes and max(text_overlap(t, _leaf_text(args)) for t in phrasings) >= need
               for name, args in writes if phrasings)


def match(c: dict, writes: list[tuple[str, dict]], overlap: float | None = None) -> str | None:
    """"same", "different" (day shape only), or None — the kind's own tool by the two rules of
    plan review 6, then any other home it can be kept in (`kept_elsewhere`)."""
    m = _match_own(c, writes, overlap)
    if m is None and kept_elsewhere(c, writes, overlap):
        return "same"
    return m


def _match_own(c: dict, writes: list[tuple[str, dict]], overlap: float | None = None) -> str | None:
    tool = KIND_TOOLS[c["kind"]]
    if c["kind"] == "day_shape":
        from tools import day_shape as ds
        found = None
        for name, args in writes:
            if name != tool:
                continue
            sec, clean = _shape_write(args)
            if sec != c["target"] or clean is None or c["proposal"] is None:
                continue
            if sec in ds._LIST_SECTIONS:
                # The same entry is the same thing on overlapping days: dinner on all seven
                # days IS the weekday dinner, saved differently; a weekend dinner is not.
                if _loose_key(sec, clean) != _loose_key(sec, c["proposal"]):
                    continue
                if not _days_overlap(clean, c["proposal"]):
                    continue
                same = _shape_equal(clean, c["proposal"])
            else:
                same = clean == c["proposal"]
            if same:
                return "same"
            found = "different"
        return found or _time_match(c, writes)
    need = float(overlap if overlap is not None else config()["match_overlap"])
    for name, args in writes:
        if name == tool and text_overlap(str(c["proposal"]), _write_text(name, args)) >= need:
            return "same"
    return None


_DAY_NAMES = frozenset({"mon", "tue", "wed", "thu", "fri", "sat", "sun"})


def _loose_key(section: str, entry: dict):
    """`_entry_key` without its day set — which thing this is, whatever days it holds for."""
    from tools import day_shape as ds
    key = ds._entry_key(section, entry)
    if isinstance(key, tuple) and key and all(isinstance(p, str) and p in _DAY_NAMES for p in key):
        return ()          # `day`: the key is the day set itself (plan review NEW 2)
    parts = key if isinstance(key, tuple) else (key,)
    return tuple(p for p in parts
                 if not (isinstance(p, (tuple, list)) and p and set(p) <= _DAY_NAMES))


def _days_overlap(a: dict, b: dict) -> bool:
    da, db = set(a.get("days") or []), set(b.get("days") or [])
    return not da or not db or bool(da & db)


def _times(value) -> set[str]:
    return set(_HM_RE.findall(json.dumps(value, default=str)))


def _time_match(c: dict, writes: list[tuple[str, dict]]) -> str | None:
    """The cross-form fallback: same when related writes carry all of the candidate's times,
    different when they carry only some (a bare `dinner: 18:00` against weekdays 18–19)."""
    want = _times(c["proposal"])
    related = _RELATED.get(c["target"], (c["target"],))
    got: set[str] = set()
    from tools import day_shape as ds
    for name, args in writes:
        sec = str(args.get("section") or args.get("field") or "").lower()
        # Only the other form: a section entry of the candidate's own section was already
        # judged structurally, and must not be re-read as a bag of times.
        if sec == c["target"] and sec in ds._LIST_SECTIONS:
            continue
        if name == "set_day_shape" and sec in related:
            got |= _times(args.get("entry") if args.get("entry") is not None
                          else args.get("value"))
    if not want or not got:
        return None
    return "same" if want <= got else ("different" if want & got else None)


def _shape_equal(a: dict, b: dict) -> bool:
    """Days and times decide it; the free-text parts (`what`, `place`) are the model's phrasing."""
    keys = ("days", "wake", "bed", "from", "to", "at", "latest", "skip", "date", "holds",
            "strength", "activity")
    norm = lambda d: {k: (sorted(d[k]) if isinstance(d.get(k), list) else d.get(k))  # noqa: E731
                      for k in keys if k in d}
    return norm(a) == norm(b)


def already_held(persona: str, c: dict, shape: dict | None = None,
                 texts: dict | None = None) -> bool:
    """Is this fact already in the stored record? A fact the user repeats is not a miss."""
    if c["kind"] == "day_shape":
        if c["proposal"] is None:
            return False
        shape = _shape(persona) if shape is None else shape
        stored = []
        for key in _RELATED.get(c["target"], (c["target"],)):
            cur = shape.get(key)
            for e in cur if isinstance(cur, list) else ([cur] if cur not in (None, "") else []):
                stored.append(("set_day_shape", {"section": key, "entry": e}
                               if isinstance(e, dict) else {"section": key, "value": e}))
        return match(c, stored) == "same"
    texts = saved_texts(persona, (c["kind"],)) if texts is None else texts
    need = float(config()["match_overlap"])
    return any(text_overlap(str(c["proposal"]), t) >= need for t in texts.get(c["kind"], []))


# --- pending, outcomes, rendering ------------------------------------------------------------------

def _row(persona: str, **kw) -> None:
    row = {k: v for k, v in kw.items() if k in _ROW_KEYS}
    row.setdefault("ts", _now().isoformat(timespec="seconds"))
    try:
        with _locked(persona):
            with open(_dir(persona) / "outcomes.jsonl", "a") as fh:
                fh.write(json.dumps(row) + "\n")
    except OSError as exc:
        logger.warning(f"[capture] outcome not recorded: {exc}")


def _outcome(persona: str, agent: str, rid: str, c: dict, outcome: str, holdout: bool,
             day: int) -> None:
    _row(persona, row="candidate", request_id=rid, agent=agent, kind=c["kind"],
         target=c["target"], disposition=c["disposition"], outcome=outcome, holdout=holdout,
         window_day=day)


def _turn_row(persona: str, agent: str, rid: str, res: dict | None, status: str,
              holdout: bool, day: int) -> None:
    res = res or {}
    _row(persona, row="turn", request_id=rid, agent=agent, outcome=status, holdout=holdout,
         window_day=day, candidates=len(res.get("candidates") or []),
         extractor_ms=res.get("ms"), extractor_tokens_in=res.get("tin"),
         extractor_tokens_out=res.get("tout"))


def _pending_path(persona: str) -> Path:
    return _dir(persona) / "pending.json"


def add_pending(persona: str, agent: str, items: list[dict]) -> None:
    if not items:
        return
    cfg = config()
    stamp = _now().isoformat(timespec="seconds")
    with _locked(persona):
        cur = [p for p in _read_json(_pending_path(persona), []) if _fresh(p, cfg)]
        for c in items:
            cur.append({**c, "agent": agent, "created": stamp, "id": uuid.uuid4().hex[:8]})
        _write_json(_pending_path(persona), cur[-int(cfg["cap"]):])


def _fresh(p: dict, cfg: dict) -> bool:
    try:
        made = datetime.fromisoformat(p["created"])
    except (KeyError, ValueError):
        return False
    return _now() - made < timedelta(hours=float(cfg["expiry_hours"]))


def _still_missing(persona: str, agent: str, rid: str, items: list[dict],
                   writes: list[tuple[str, dict]], day: int) -> list[dict]:
    """A proposal carried from an earlier turn is re-checked when it is shown: the writer
    may have saved it on that turn after the extractor was joined (plan review NEW 3)."""
    if not items:
        return []
    shape, texts = _shape(persona), saved_texts(persona, AGENT_KINDS[agent])
    out = []
    for c in items:
        if match(c, writes) == "same" or already_held(persona, c, shape, texts):
            _outcome(persona, agent, rid, c, "saved_late", False, day)
        else:
            out.append(c)
    return out


def take_pending(persona: str, agent: str) -> list[dict]:
    """Unexpired proposals for this writer, removed as they are taken — shown once."""
    cfg = config()
    with _locked(persona):
        cur = [p for p in _read_json(_pending_path(persona), []) if _fresh(p, cfg)]
        mine = [p for p in cur if p.get("agent") == agent
                or (agent == "synthesizer" and p.get("kind") in AGENT_KINDS["synthesizer"])]
        _write_json(_pending_path(persona), [p for p in cur if p not in mine])
    return mine


def _line(c: dict) -> str:
    if c.get("_mismatch"):
        return f"check: {c['say']} — it was saved differently this turn"
    return f"{'ask' if c['disposition'] == 'ask' else 'keep'}: {c['say']}"


def render_note(items: list[dict]) -> str:
    if not items:
        return ""
    return ("CAPTURE NOTE — from what the user said, not yet kept (keep it if it is what they "
            "meant, ask on an ask line, ignore a line that is wrong; never mention this note):\n"
            + "\n".join(f"- {_line(c)}" for c in items))


def coverage_lines(items: list[dict]) -> str:
    if not items:
        return ""
    return "- Said but not yet saved:\n" + "\n".join(f"  - {_line(c)}" for c in items)


# --- triage: one list of candidates into shown / silent ---------------------------------------------

def _triage(persona: str, agent: str, rid: str, cands: list[dict],
            writes: list[tuple[str, dict]], holdout: bool, day: int) -> list[dict]:
    """Drop what is held or already written the same way; return what would be shown."""
    shape, texts = _shape(persona), saved_texts(persona, AGENT_KINDS[agent])
    show = []
    for c in cands:
        if c["disposition"] == "declined":
            _outcome(persona, agent, rid, c, "declined", holdout, day)
            continue
        m = match(c, writes)
        if m == "same":
            _outcome(persona, agent, rid, c, "saved_by_agent", holdout, day)
            continue
        if m is None and already_held(persona, c, shape, texts):
            _outcome(persona, agent, rid, c, "already_held", holdout, day)
            continue
        show.append({**c, "_mismatch": m == "different"})
    return show


def _resolve(persona: str, agent: str, rid: str, shown: list[dict],
             writes: list[tuple[str, dict]], holdout: bool, day: int) -> None:
    for c in shown:
        m = match({**c}, writes)
        if holdout:
            out = "held_out_saved" if m in ("same", "different") else "held_out_unsaved"
        elif m == "same":
            out = "accepted"
        elif m == "different":
            out = "edited"
        else:
            out = "not_acted"
        _outcome(persona, agent, rid, c, out, holdout, day)


# --- the ordinary-turn path -----------------------------------------------------------------------

class SynthTurn:
    def __init__(self, persona: str, rid: str, shown: list[dict], holdout: bool, day: int):
        self.persona, self.rid, self.shown, self.holdout, self.day = (
            persona, rid, shown, holdout, day)
        self.note = "" if holdout else render_note(shown)


def note_for_synthesizer(persona: str, job: Job | None, trace) -> SynthTurn | None:
    """After the specialists: join (bounded), compare, draw the holdout, build the note."""
    if job is None:
        return None
    cfg = config()
    agent = "synthesizer"
    day = window_day(persona)
    holdout = is_holdout(job.request_id, day, cfg)
    cap = int(cfg["cap"])

    def late(res: dict) -> None:
        # The turn went on without it. Pended raw — the record read now may predate the
        # Synthesizer's write this turn, so held/saved is judged when it is shown.
        _turn_row(persona, agent, job.request_id, res, "late" if res.get("ok") else "failed",
                  False, day)
        keep = []
        for c in res.get("candidates") or []:
            if c["disposition"] == "declined":
                _outcome(persona, agent, job.request_id, c, "declined", False, day)
            else:
                keep.append(c)
        add_pending(persona, agent, keep)

    res = job.wait(float(cfg["join_bound_s"]), late=late)
    writes = writes_from_trace(trace)
    # A holdout measures THIS turn's unprompted saves; proposals from earlier turns wait for
    # the next turn that shows a note, never enter the holdout (plan review NEW 1).
    carried = [] if holdout else _still_missing(persona, agent, job.request_id,
                                                take_pending(persona, agent), writes, day)
    fresh: list[dict] = []
    if res is not None:
        _turn_row(persona, agent, job.request_id, res, "ran" if res.get("ok") else "failed",
                  holdout, day)
        fresh = _triage(persona, agent, job.request_id, res.get("candidates") or [],
                        writes, holdout, day)
    items = (fresh + carried)
    for c in items[cap:]:
        _outcome(persona, agent, job.request_id, c, "dropped_cap", holdout, day)
    return SynthTurn(persona, job.request_id, items[:cap], holdout, day)


def after_synthesizer(turn: SynthTurn | None, trace) -> None:
    if turn is None:
        return
    try:
        writes = writes_from_trace(trace)
        _resolve(turn.persona, "synthesizer", turn.rid, turn.shown, writes, turn.holdout,
                 turn.day)
        if turn.holdout:
            # Measured; now caught one turn late rather than lost — a holdout delays
            # prevention, it does not withhold it.
            add_pending(turn.persona, "synthesizer",
                        [{k: v for k, v in c.items() if k != "_mismatch"} for c in turn.shown
                         if match(c, writes) not in ("same", "different")])
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[capture] outcomes not recorded: {exc}")


def defer(turn: SynthTurn | None) -> None:
    """The Synthesizer never ran (sign-off): hold what would have been shown for next turn."""
    if turn is None or not turn.shown:
        return
    add_pending(turn.persona, "synthesizer",
                [{k: v for k, v in c.items() if k not in ("_mismatch", "agent", "created", "id")}
                 for c in turn.shown])


# --- the interview path -----------------------------------------------------------------------------

def take_for_interview(persona: str) -> list[dict]:
    if not enabled():
        return []
    return _still_missing(persona, "goals_interviewer", "carry",
                          take_pending(persona, "goals_interviewer"), [], window_day(persona))


def after_interview_turn(persona: str, job: Job | None, before: dict, after: dict,
                         shown: list[dict]) -> None:
    """After the reply: resolve what was shown, then queue this turn's misses for the next."""
    agent = "goals_interviewer"
    try:
        writes = writes_from_snapshots(before, after)
        day = window_day(persona) if (job or shown) else 0
        rid = job.request_id if job else uuid.uuid4().hex[:12]
        _resolve(persona, agent, rid, shown, writes, False, day)
        if job is None:
            return
        cfg = config()

        def finish(res: dict) -> None:
            _turn_row(persona, agent, rid, res, "ran" if res.get("ok") else "failed", False, day)
            show = _triage(persona, agent, rid, res.get("candidates") or [], writes, False, day)
            add_pending(persona, agent, [{k: v for k, v in c.items()} for c in show])

        res = job.wait(float(cfg["join_bound_s"]), late=finish)
        if res is not None:
            finish(res)
    except Exception as exc:  # noqa: BLE001 — never take the interview down
        logger.warning(f"[capture] interview capture failed: {exc}")


# --- the report ---------------------------------------------------------------------------------------------

def read_outcomes(persona: str, since: str | None = None) -> list[dict]:
    path = _dir(persona) / "outcomes.jsonl"
    rows = []
    for ln in path.read_text().splitlines() if path.exists() else []:
        try:
            r = json.loads(ln)
        except ValueError:
            continue
        if not since or str(r.get("ts", "")) >= since:
            rows.append(r)
    return rows


def summarise(rows: list[dict]) -> dict:
    """Per agent × kind: candidates, outcomes, miss rate and accept rate (plan § 4.6)."""
    turns: dict[str, dict] = {}
    for r in rows:
        if r.get("row") == "turn":
            t = turns.setdefault(r.get("agent", "?"), {"turns": 0, "ran": 0})
            t["turns"] += 1
            t["ran"] += 1 if r.get("outcome") in ("ran", "late") else 0
    table: dict[tuple, dict] = {}
    for r in rows:
        if r.get("row") != "candidate":
            continue
        k = (r.get("agent", "?"), r.get("kind", "?"))
        t = table.setdefault(k, {})
        t[r.get("outcome", "?")] = t.get(r.get("outcome", "?"), 0) + 1
    out = {"turns": turns, "kinds": {}}
    for (agent, kind), t in sorted(table.items()):
        shown = sum(t.get(o, 0) for o in ("accepted", "edited", "not_acted"))
        held = t.get("held_out_saved", 0) + t.get("held_out_unsaved", 0)
        if agent == "goals_interviewer":
            # The interviewer's comparison is made after its turn and before any note.
            pre = t.get("saved_by_agent", 0)
            miss_n = shown + t.get("dropped_cap", 0)
            miss = miss_n / (miss_n + pre) if (miss_n + pre) else None
        else:
            miss = t.get("held_out_unsaved", 0) / held if held else None
        out["kinds"][f"{agent}/{kind}"] = {
            **t, "miss_rate": miss,
            "accept_rate": (t.get("accepted", 0) + t.get("edited", 0)) / shown if shown else None,
        }
    return out


def _live_n(agent: str, t: dict) -> int:
    if agent == "goals_interviewer":
        return sum(t.get(o, 0) for o in ("accepted", "edited", "not_acted", "dropped_cap",
                                         "saved_by_agent"))
    return t.get("held_out_saved", 0) + t.get("held_out_unsaved", 0)


def report(persona: str, since: str | None = None) -> str:
    s = summarise(read_outcomes(persona, since))
    cfg = config()
    bench = (cfg.get("benchmark") or {})
    base = _read_json(_dir(persona) / "baseline.json", {}).get("kinds") or {}
    reduction = float((cfg.get("minimums") or {}).get("miss_rate_reduction") or 0)
    lines = [f"Capture fidelity — {persona}" + (f" since {since}" if since else "")]
    for agent, t in s["turns"].items():
        lines.append(f"  {agent}: extractor ran on {t['ran']} of {t['turns']} eligible turns")
    if not s["turns"]:
        lines.append("  no eligible turns recorded — capture off, or nothing said yet")
    for key, t in s["kinds"].items():
        fmt = lambda v: "—" if v is None else f"{v:.0%}"  # noqa: E731
        bar_m, bar_a = bench.get("miss_rate_max"), bench.get("accept_rate_min")
        verdict_m = "" if bar_m is None or t["miss_rate"] is None else (
            " pass" if t["miss_rate"] <= bar_m else " FAIL")
        verdict_a = "" if bar_a is None or t["accept_rate"] is None else (
            " pass" if t["accept_rate"] >= bar_a else " FAIL")
        # § 5.3: live miss ≤ (1 − reduction) × the backfill baseline, once the live sample
        # is big enough to mean anything.
        b = base.get(key)
        agent = key.split("/", 1)[0]
        n = _live_n(agent, t)
        if b and t["miss_rate"] is not None:
            bar = b["miss_rate"] * (1 - reduction)
            verdict_b = (f" vs baseline {b['miss_rate']:.0%} (bar {bar:.0%}): "
                         + ("too few to judge" if n < 20 else
                            "pass" if t["miss_rate"] <= bar else "FAIL") + f", n={n}")
        else:
            verdict_b = " · no baseline" if not b else ""
        counts = ", ".join(f"{k} {v}" for k, v in t.items() if isinstance(v, int))
        lines.append(f"  {key}: miss {fmt(t['miss_rate'])}{verdict_m}{verdict_b} · accept "
                     f"{fmt(t['accept_rate'])}{verdict_a} · {counts}")
    return "\n".join(lines)


def weekly_rollup() -> str:
    """Scheduler entry point (daily slot; writes on Mondays). Never raises."""
    try:
        from core.persona import resolve_persona
        persona = resolve_persona(None)
        today = _now().date()
        if today.weekday() != 0:
            return "capture weekly: not Monday"
        since = (today - timedelta(days=7)).isoformat()
        row = {"week_ending": today.isoformat(), **summarise(read_outcomes(persona, since))}
        with _locked(persona):
            with open(_dir(persona) / "weekly.jsonl", "a") as fh:
                fh.write(json.dumps(row) + "\n")
        return f"capture weekly: {len(row['kinds'])} kinds"
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[capture] weekly rollup failed: {exc}")
        return f"capture weekly failed: {exc}"


# --- backfill, labels, eval ----------------------------------------------------------------------------

def _trace_files(persona: str, days: int) -> list[Path]:
    from core.persona import persona_data_dir
    d = persona_data_dir(persona) / "traces"
    cutoff = (_now().date() - timedelta(days=days)).isoformat()
    return sorted(p for p in d.glob("*.jsonl") if p.stem >= cutoff) if d.exists() else []


def user_turns(persona: str, days: int):
    """(record, history) for every real user turn — never proactive, never capture's own."""
    for path in _trace_files(persona, days):
        hist: list[dict] = []
        for ln in path.read_text().splitlines():
            try:
                rec = json.loads(ln)
            except ValueError:
                continue
            if rec.get("source") == "capture" or rec.get("is_proactive"):
                continue
            text = str(rec.get("user_input") or "").strip()
            if not text:
                continue
            agents = {a.get("agent") for a in rec.get("pipeline") or []}
            # A user turn passes through the Coordinator or the interviewer. The Diarist's own
            # runs and the morning intake jobs own traces too, non-proactive, with a directive
            # where the user's words would be ("Log user's preference…") — not the user.
            if not agents & {"coordinator", "goals_interviewer"}:
                continue
            agent = "goals_interviewer" if "goals_interviewer" in agents else "synthesizer"
            yield rec, list(hist), agent
            hist += [{"role": "user", "content": text},
                     {"role": "assistant", "content": str(rec.get("synth_response") or "")}]
            hist = hist[-6:]


def backfill(persona: str, days: int = 60) -> str:
    """The pre-deploy baseline and the label set. Writes a review file holding the user's
    words — sensitive tier, in the persona's own directory, on the VM only."""
    out_path = _dir(persona) / f"backfill_review_{_now().date().isoformat()}.jsonl"
    n_turns = n_cands = n_failed = 0
    tally: dict[str, dict] = {}
    with open(out_path, "w") as fh:
        for rec, hist, agent in user_turns(persona, days):
            kinds = AGENT_KINDS[agent]
            res = extract(persona, rec["user_input"], hist, kinds, trace=None)
            writes = writes_from_trace_dict(rec)
            n_turns += 1
            n_failed += not res["ok"]
            items = []
            for c in res["candidates"]:
                items.append({**c, "matcher": _classify(persona, c, writes), "guess": "real"})
            n_cands += len(items)
            for c in items:
                if c["matcher"] in ("saved", "saved_elsewhere", "different", "unsaved"):
                    t = tally.setdefault(f"{agent}/{c['kind']}", {"n": 0, "unsaved": 0})
                    t["n"] += 1
                    t["unsaved"] += c["matcher"] == "unsaved"
            fh.write(json.dumps({"trace_id": rec.get("trace_id"), "ts": rec.get("ts"),
                                 "agent": agent, "user_input": rec["user_input"],
                                 "ok": res["ok"], "candidates": items},
                                ensure_ascii=False) + "\n")
    # The pre-deploy miss rate per agent/kind — what § 5.3's live miss rate is held against.
    # A candidate already held in today's record is left out, as live comparison does.
    head = f"backfill: {n_turns} turns, {n_cands} candidates, {n_failed} extractor failures → {out_path}"
    if n_failed:
        head += (f"\n  WARNING: {n_failed} of {n_turns} turns were not read — the baseline "
                 f"covers only the rest. Check the log for '[capture]' lines.")
    return _write_baseline(persona, days, n_turns, tally, head)


def _classify(persona: str, c: dict, writes: list[tuple[str, dict]]) -> str:
    if c["disposition"] == "declined":
        return "declined"
    own = _match_own(c, writes)
    return ("saved" if own == "same" else "different" if own == "different" else
            "saved_elsewhere" if kept_elsewhere(c, writes) else
            "held_now" if already_held(persona, c) else "unsaved")


def rematch(persona: str, days: int = 60) -> str:
    """Re-score the latest review file with the current matcher and turn filter — no model
    calls. For when the matcher changes after a backfill (2026-11-18: the first run counted
    only each kind's own tool, and read the Diarist's runs as user turns)."""
    path = _latest_review(persona)
    if path is None:
        return "no backfill review file — run --backfill first"
    traces = {rec.get("trace_id"): (rec, agent) for rec, _, agent in user_turns(persona, days)}
    kept, dropped, tally = [], 0, {}
    for ln in path.read_text().splitlines():
        if not ln.strip():
            continue
        t = json.loads(ln)
        hit = traces.get(t.get("trace_id"))
        if hit is None:
            dropped += 1           # not a user turn by the current filter
            continue
        writes = writes_from_trace_dict(hit[0])
        for c in t["candidates"]:
            c["matcher"] = _classify(persona, c, writes)
            if c["matcher"] in ("saved", "saved_elsewhere", "different", "unsaved"):
                k = tally.setdefault(f"{t['agent']}/{c['kind']}", {"n": 0, "unsaved": 0})
                k["n"] += 1
                k["unsaved"] += c["matcher"] == "unsaved"
        kept.append(t)
    path.write_text("".join(json.dumps(t, ensure_ascii=False) + "\n" for t in kept))
    return _write_baseline(persona, days, len(kept), tally,
                           f"rematch: kept {len(kept)} user turns, dropped {dropped}, "
                           f"{sum(len(t['candidates']) for t in kept)} candidates → {path}")


def _write_baseline(persona: str, days: int, n_turns: int, tally: dict, head: str) -> str:
    baseline = {"measured_on": _now().date().isoformat(), "days": days, "turns": n_turns,
                "kinds": {k: {"n": t["n"], "miss_rate": t["unsaved"] / t["n"]}
                          for k, t in tally.items() if t["n"]}}
    _write_json(_dir(persona) / "baseline.json", baseline)
    return "\n".join([head] + [f"  baseline {k}: miss {v['miss_rate']:.0%} (n={v['n']})"
                               for k, v in sorted(baseline["kinds"].items())])


def _latest_review(persona: str) -> Path | None:
    files = sorted(_dir(persona).glob("backfill_review_*.jsonl"))
    return files[-1] if files else None


def label(persona: str, precision_n: int = 100, recall_n: int = 50) -> str:
    """Mike's walkthrough: Enter accepts the tool's guess; one key changes it."""
    import random
    path = _latest_review(persona)
    if path is None:
        return "no backfill review file — run --backfill first"
    turns = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    cands = [(t, c) for t in turns for c in t["candidates"] if c["disposition"] != "declined"]
    empty = [t for t in turns if t["ok"] and not t["candidates"]]
    rng = random.Random(7)
    sample = rng.sample(cands, min(precision_n, len(cands)))
    empties = rng.sample(empty, min(recall_n, len(empty)))
    labels_path = path.with_name(path.stem.replace("backfill_review", "labels") + ".jsonl")
    with open(labels_path, "w") as fh:
        for i, (t, c) in enumerate(sample, 1):
            print(f"\n[{i}/{len(sample)}] USER: {t['user_input'][:600]}")
            print(f"  candidate: {c['disposition']} · {c['kind']} · {c['say']}")
            print(f"  proposal:  {json.dumps(c.get('proposal'), ensure_ascii=False)[:200]}")
            print(f"  matcher says: {c['matcher']}   guess: {c['guess']}")
            k = input("  Enter=real  n=not a fact  w=wrong kind  m=matcher wrong  q=quit > ")
            if k.strip() == "q":
                break
            lab = {"n": "not_a_fact", "w": "wrong_kind", "m": "matcher_wrong"}.get(
                k.strip(), "real")
            fh.write(json.dumps({"part": "precision", "trace_id": t["trace_id"],
                                 "kind": c["kind"], "label": lab}) + "\n")
        for i, t in enumerate(empties, 1):
            print(f"\n[recall {i}/{len(empties)}] USER: {t['user_input'][:600]}")
            k = input("  Enter=nothing missed  or type the fact it missed (q=quit) > ")
            if k.strip() == "q":
                break
            fh.write(json.dumps({"part": "recall", "trace_id": t["trace_id"],
                                 "missed": bool(k.strip())}) + "\n")
    return f"labels → {labels_path}\n{score(persona)}"


def score(persona: str) -> str:
    path = _latest_review(persona)
    if path is None:
        return "no labels yet"
    lp = path.with_name(path.stem.replace("backfill_review", "labels") + ".jsonl")
    if not lp.exists():
        return "no labels yet"
    rows = [json.loads(ln) for ln in lp.read_text().splitlines() if ln.strip()]
    prec = [r for r in rows if r["part"] == "precision"]
    rec = [r for r in rows if r["part"] == "recall"]
    real = sum(1 for r in prec if r["label"] in ("real", "matcher_wrong"))
    matcher_ok = sum(1 for r in prec if r["label"] != "matcher_wrong")
    missed = sum(1 for r in rec if r["missed"])
    # Recall estimate: real facts found in the sample, against those plus the misses Mike
    # named in the found-nothing sample, scaled to the backfill's proportions.
    turns = [json.loads(ln) for ln in path.read_text().splitlines() if ln.strip()]
    n_empty = sum(1 for t in turns if t["ok"] and not t["candidates"])
    n_cands = sum(len(t["candidates"]) for t in turns)
    found_real = n_cands * (real / len(prec)) if prec else 0
    missed_total = n_empty * (missed / len(rec)) if rec else 0
    recall = found_real / (found_real + missed_total) if (found_real + missed_total) else None
    fmt = lambda v: "—" if v is None else f"{v:.0%}"  # noqa: E731
    mins = config().get("minimums") or {}
    return (f"precision {fmt(real / len(prec) if prec else None)} (n={len(prec)}, min "
            f"{fmt(mins.get('precision'))}) · recall {fmt(recall)} (n={len(rec)}, min "
            f"{fmt(mins.get('recall'))}) · matcher {fmt(matcher_ok / len(prec) if prec else None)}"
            f" (min {fmt(mins.get('matcher'))})")


def run_eval(persona: str, fixture: Path, cap: int = 20) -> str:
    """Real extractor calls on the authored turns — opt-in, never in the suite."""
    data = json.loads(fixture.read_text())
    lines = []
    for i, turn in enumerate(data.get("turns", [])[:cap]):
        res = extract(persona, turn["user"], turn.get("history"),
                      AGENT_KINDS[data.get("agent", "goals_interviewer")], trace=None)
        got = [f"{c['disposition']}:{c['kind']}/{c['target']}" for c in res["candidates"]]
        lines.append(f"{i + 1}. expect {turn.get('expect')} · got {got}")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(prog="tools.capture")
    ap.add_argument("--persona", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--report", action="store_true")
    g.add_argument("--backfill", action="store_true")
    g.add_argument("--label", action="store_true")
    g.add_argument("--score", action="store_true")
    g.add_argument("--rematch", action="store_true")
    g.add_argument("--eval", metavar="FIXTURE")
    ap.add_argument("--since")
    ap.add_argument("--days", type=int, default=60)
    a = ap.parse_args()
    from core.persona import persona_scope
    with persona_scope(a.persona):
        if a.report:
            print(report(a.persona, a.since))
        elif a.backfill:
            print(backfill(a.persona, a.days))
        elif a.label:
            print(label(a.persona))
        elif a.score:
            print(score(a.persona))
        elif a.rematch:
            print(rematch(a.persona, a.days))
        else:
            print(run_eval(a.persona, Path(a.eval)))


if __name__ == "__main__":
    main()
