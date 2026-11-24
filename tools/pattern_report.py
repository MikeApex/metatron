"""
tools/pattern_report.py — the weekly Pattern Miner's fixed procedure, done by code
(instructions-to-code Stage 4, #20 and M16).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #20, as revised
(review L4) and amended.

What a user notices: the weekly pattern analysis reaches the Coordinator and the specialists
again. Measured: the weekly run wrote NO report for 12 straight Sundays — every run spent its 8
rounds on the fixed reads and hit the limit before saving, and the loop then returned its last
tool result, which nothing stored.

What lives here, each tested in tests/test_pattern_report.py:

1. **The data span and the baseline row (M16).** The first and last log dates on file give the
   span; the span picks one row of the baseline table in config/agents/pattern_miner.md — read
   from that file at run time, so the table has one home. A table that no longer has its six
   expected rows selects nothing (the span is still handed over, and the model picks).
2. **Free-text bands before 2026-08-09 are stripped** from handed-over log entries
   (`wellbeing.mood`, `wellbeing.intensity`, `health.energy`); `sleep_hours` is kept —
   pattern_miner.md's own rule, applied by code.
3. **The report is written by code only from a valid final reply**, and only when the run did
   not write one itself. Valid = at least one block carrying [EVIDENCE], [OBSERVATION] and
   [CONFIDENCE], and not a tool-result body. Anything else writes NOTHING (the last real report
   stays the most recent) and files a PATTERN_REPORT_MISSING quality event, so a failing Sunday
   reaches the machine log instead of vanishing again.
4. **The tracker gets patterns only**, through Stage 2's `merge_pattern_findings` — never the
   replace-semantics writer. Follow-ups, open threads, held items and clinical threads are
   untouched.

Local-only, sensitive tier: every read and write here is the bound persona's own store. No model
call is made in this module.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_AGENT_FILE = Path(__file__).resolve().parent.parent / "config" / "agents" / "pattern_miner.md"

# The final-round prompt (review L4). _FINAL_REPLY_PROMPT says "reply to the user"; this run has
# no user.
FINAL_PROMPT = ("Your tool budget is spent. Write the report now, in the output format, from "
                "what you have read. Begin with the first [EVIDENCE] block.")

# The analysis windows the weekly run covers (its scheduled prompt: this week, 30 and 90 days).
WINDOWS = (7, 30, 90)

# pattern_miner.md: comparable bands begin on this date; before it the same fields were prose.
BANDS_FROM = date(2026, 8, 9)
_FREE_TEXT_BANDS = (("wellbeing", "mood"), ("wellbeing", "intensity"), ("health", "energy"))


# --- 1. the data span and the baseline row (M16) ----------------------------------------------

def data_span(persona: str | None = None) -> tuple[date, date] | None:
    """(first, last) log date on file, or None when there is no log."""
    from core.persona import persona_data_dir
    logs = persona_data_dir(persona) / "logs"
    days: list[date] = []
    if logs.is_dir():
        for f in logs.glob("*.json"):
            try:
                days.append(date.fromisoformat(f.stem))
            except ValueError:
                continue
    return (min(days), max(days)) if days else None


def months_between(first: date, last: date) -> int:
    """Whole calendar months from `first` to `last` (a month counts once its day is reached)."""
    m = (last.year - first.year) * 12 + (last.month - first.month)
    if last.day < first.day:
        m -= 1
    return max(0, m)


# The table's six rows in order, each with the month floor it starts at and a pattern its label
# must still match — a reworded or reordered table selects nothing rather than the wrong row.
_ROW_FLOORS = (0, 3, 6, 12, 24, 36)
_ROW_LABELS = (r"<\s*3\s*months", r"3\s*[–-]\s*6\s*months", r"6\s*[–-]\s*12\s*months",
               r"1\s*year", r"2\s*[–-]\s*3\s*years", r"3\+\s*years")


def baseline_table(text: str | None = None) -> list[tuple[str, str]] | None:
    """The (data available, baseline to use) rows of pattern_miner.md's baseline table, or None
    when the table is not the six rows this code was written against."""
    try:
        text = text if text is not None else _AGENT_FILE.read_text()
    except OSError:
        return None
    section = text.split("## Baseline selection", 1)
    if len(section) != 2:
        return None
    body = re.split(r"\n## ", section[1], maxsplit=1)[0]
    rows: list[tuple[str, str]] = []
    for line in body.splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) != 2 or set(cells[0]) <= set("-: ") or cells[0].lower().startswith("data"):
            continue
        rows.append((cells[0], cells[1]))
    if len(rows) != len(_ROW_LABELS):
        return None
    for (label, _), pattern in zip(rows, _ROW_LABELS):
        if not re.search(pattern, label, re.IGNORECASE):
            return None
    return rows


def baseline_row(span: tuple[date, date] | None, table=None) -> tuple[str, str] | None:
    """The table row the span selects, or None (no logs, or a table code cannot read)."""
    if span is None:
        return None
    rows = table if table is not None else baseline_table()
    if not rows:
        return None
    months = months_between(*span)
    idx = max(i for i, floor in enumerate(_ROW_FLOORS) if months >= floor)
    return rows[idx]


def baseline_label(span: tuple[date, date] | None, table=None) -> str:
    """One line for the report's `baseline_used` and for the handed-over block."""
    if span is None:
        return "no logs on file — no baseline"
    first, last = span
    row = baseline_row(span, table)
    head = (f"data span {first.isoformat()} → {last.isoformat()} "
            f"({months_between(first, last)} whole months)")
    if row is None:
        return f"{head}; baseline row not selected by code — pick it from your table"
    return f"{head}: {row[0]} → {row[1]}"


# --- 2. bands before 2026-08-09 ---------------------------------------------------------------

def strip_free_text_bands(entries: list[dict]) -> list[dict]:
    """Copies of `entries` with the free-text bands removed from days before BANDS_FROM.
    `sleep_hours` (always numeric) and every other field are kept."""
    out: list[dict] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        e = json.loads(json.dumps(entry, default=str))
        try:
            day = date.fromisoformat(str(e.get("date") or ""))
        except ValueError:
            day = None
        if day is not None and day < BANDS_FROM:
            for block, field in _FREE_TEXT_BANDS:
                if isinstance(e.get(block), dict):
                    e[block].pop(field, None)
        out.append(e)
    return out


# --- 3. the final reply: validate and parse ---------------------------------------------------

_TAGS = ("EVIDENCE", "OBSERVATION", "HYPOTHESIS", "CONFIDENCE", "ACTION")
_TAG_RE = re.compile(r"\**\[(" + "|".join(_TAGS) + r")\]\**\s*:?\s*", re.IGNORECASE)
_REQUIRED = ("evidence", "observation", "confidence")
# What a tool result (not a report) starts with — the loop used to return one of these.
_TOOL_RESULT_PREFIXES = ("error", "log written", "insight report written", "patterns:",
                         "context tracker updated", "quality event")
_SCALE_RE = re.compile(r"\b(7|30|90|365)[- ]day\b|\ball[- ]time\b", re.IGNORECASE)
_HEADING_RE = re.compile(r"^\s*(#{1,6}\s+.+|\*\*[^*]{1,80}\*\*:?|[A-Z0-9][^.]{0,60}:)\s*$")


def is_tool_result_body(text: str) -> bool:
    t = (text or "").strip()
    if not t:
        return True
    if t.lower().startswith(_TOOL_RESULT_PREFIXES):
        return True
    if t[0] in "[{":
        try:
            return isinstance(json.loads(t), (dict, list))
        except ValueError:
            return False
    return False


def confidence_level(text: str) -> str:
    """weak / moderate / strong — the LOWEST named, so "weak to moderate" reads weak; "" if
    none is named."""
    low = (text or "").lower()
    for level in ("weak", "moderate", "strong"):
        if re.search(rf"\b{level}\b", low):
            return level
    return ""


def _split_trailing_headings(text: str) -> tuple[str, str]:
    """(content, trailing heading lines) — a scale heading before the next block lands at the
    end of the previous block's last field."""
    lines = text.rstrip().splitlines()
    tail: list[str] = []
    while lines and (not lines[-1].strip() or _HEADING_RE.match(lines[-1])):
        tail.insert(0, lines.pop())
    return "\n".join(lines).strip(), "\n".join(tail).strip()


def parse_blocks(text: str) -> tuple[list[dict], str]:
    """(observations, notes). Each observation has the five fields, `confidence_level` and
    `scale` (from the nearest heading before it). Notes is the text outside every block — the
    merges and recommendations the run lists — kept, not dropped."""
    matches = list(_TAG_RE.finditer(text or ""))
    if not matches:
        return [], (text or "").strip()
    notes = [text[:matches[0].start()].strip()]
    pending_heading = notes[0]
    blocks: list[dict] = []
    current: dict | None = None
    for i, m in enumerate(matches):
        tag = m.group(1).lower()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        value = text[m.end():end]
        if tag == "evidence" or current is None or tag in current:
            current = {"_heading": pending_heading}
            blocks.append(current)
            pending_heading = ""
        nxt = matches[i + 1].group(1).lower() if i + 1 < len(matches) else None
        if nxt is None or nxt == "evidence":
            value, heading = _split_trailing_headings(value)
            if nxt is None:
                # After the last block: anything past a blank line is a closing note.
                head, sep, rest = value.partition("\n\n")
                if sep and rest.strip():
                    value, heading = head, (rest.strip() + ("\n" + heading if heading else ""))
                if heading:
                    notes.append(heading)
            else:
                pending_heading = heading
        current[tag] = value.strip()
    observations: list[dict] = []
    for b in blocks:
        if not all(b.get(k) for k in _REQUIRED):
            continue
        scale = _SCALE_RE.search(b.get("_heading") or "")
        observations.append({
            "evidence": b.get("evidence", ""),
            "observation": b.get("observation", ""),
            "hypothesis": b.get("hypothesis", ""),
            "confidence": b.get("confidence", ""),
            "action": b.get("action", ""),
            "confidence_level": confidence_level(b.get("confidence", "")),
            "scale": scale.group(0).lower().replace(" ", "-") if scale else "",
        })
    return observations, "\n\n".join(n for n in notes if n).strip()


def validate(text: str) -> tuple[bool, str]:
    """(valid, reason). Valid = not a tool-result body, and at least one complete block."""
    if is_tool_result_body(text):
        return False, "the final reply was empty or a tool result, not a report"
    observations, _ = parse_blocks(text)
    if not observations:
        return False, ("the final reply had no block carrying [EVIDENCE], [OBSERVATION] and "
                       "[CONFIDENCE]")
    return True, ""


def build_report(text: str, today: date, span: tuple[date, date] | None = None,
                 table=None) -> dict:
    observations, notes = parse_blocks(text)
    scales = sorted({o["scale"] for o in observations if o["scale"]},
                    key=lambda s: (len(s), s))
    report = {
        "date": today.isoformat(),
        "scale": ", ".join(scales) or ", ".join(f"{n}-day" for n in WINDOWS),
        "baseline_used": baseline_label(span, table),
        "data_window": (f"{span[0].isoformat()} to {span[1].isoformat()}" if span else ""),
        "observations": observations,
        "written_by": "code, from the Pattern Miner's final reply",
    }
    if notes:
        report["notes"] = notes[:4000]
    return report


def tracker_patterns(report: dict, limit: int = 3) -> list[str]:
    """Up to `limit` observation sentences for the tracker, strongest confidence first."""
    rank = {"strong": 0, "moderate": 1, "weak": 2, "": 3}
    obs = sorted(report.get("observations") or [],
                 key=lambda o: rank.get(o.get("confidence_level", ""), 3))
    out: list[str] = []
    for o in obs[:limit]:
        text = " ".join(str(o.get("observation") or "").split())
        first = re.split(r"(?<=[.!?])\s", text, maxsplit=1)[0]
        if first:
            out.append(first[:240])
    return out


# --- 4. the post-run hook ---------------------------------------------------------------------

def _called_ok(agent_rec, tool: str) -> bool:
    """Did this run call `tool` and have it succeed?"""
    for turn in getattr(agent_rec, "turns", None) or []:
        for tc in getattr(turn, "tool_calls", None) or []:
            if tc.name != tool or getattr(tc, "ok", True) is False:
                continue
            if not str(tc.result_preview or "").startswith("Error"):
                return True
    return False


def _last_report_date(persona: str | None) -> str:
    try:
        from tools.pattern_miner import read_recent_insights
        got = read_recent_insights(n=1, persona=persona or "")
        return str(got[0].get("date") or "") if got else ""
    except Exception:  # noqa: BLE001
        return ""


def write_from_reply(reply: str, agent_rec=None, persona: str | None = None,
                     today: date | None = None) -> str:
    """The Pattern Miner's post-run step. Returns a one-line status (logged, never shown).
    Never raises: a failure here must not fail the scheduled job's notification."""
    try:
        if _called_ok(agent_rec, "write_insight_report"):
            return "report written by the run itself — nothing written by code"
        ok, reason = validate(reply)
        if not ok:
            last = _last_report_date(persona)
            detail = (f"weekly Pattern Miner run ended without a report: {reason}. Nothing was "
                      f"written; the most recent report on file stays "
                      f"{('the one dated ' + last) if last else 'absent'}.")
            logger.warning(f"[pattern_report] {detail}")
            try:
                from tools.logger import write_quality_event
                write_quality_event("PATTERN_REPORT_MISSING", source_agent="pattern_miner",
                                    detail=detail)
            except Exception as exc:  # noqa: BLE001
                logger.warning(f"[pattern_report] quality event not written: {exc}")
            return f"no report: {reason}"
        today = today or date.today()
        span = data_span(persona)
        report = build_report(reply, today, span)
        from tools.pattern_miner import write_insight_report
        report["generated_at"] = datetime.now().isoformat()
        status = write_insight_report(today.isoformat(), report, persona=persona or "")
        if not _called_ok(agent_rec, "write_context_tracker"):
            patterns = tracker_patterns(report)
            if patterns:
                # Stage 2's merge: adds to `patterns` only. NEVER the replace-semantics writer.
                from tools.context_tracker import merge_pattern_findings
                merge_pattern_findings(patterns=patterns)
        return status
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[pattern_report] post-run step failed: {exc}")
        return f"post-run step failed: {exc}"


# --- the handed-over block's pieces (core/prefetch.py calls these) ----------------------------

def windows(today: date) -> list[tuple[int, date, date]]:
    from datetime import timedelta
    return [(n, today - timedelta(days=n - 1), today) for n in WINDOWS]
