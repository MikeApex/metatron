"""
tools/clinical_checks.py — the clinical checks code can decide exactly, so no model has to.

Stage 3 of the instructions-to-code build
(archive/plans/instructions_to_code_stage3_hard_fail_plan_2026-11-23.md §§ 1.1, 1.4, 1.5):

1. **The medication check (#8).** `medication_note()` reads "Medication taken today"
   (tools/obligations.medication_taken) and states, from each row's own fields, which required
   medicine reads missed. Physical Health's model used to work this out from the same view on
   step 2 of its scan; now it is code on every Physical Health return
   (core/orchestrator._run_single_agent), so no mode, path or omitted step can skip it.
2. **Clinical companions (M8).** `complete_clinical_flags()` adds the `MUST_SURFACE` a
   `CLINICAL_CONCERN` must carry when the specialist left it out, and writes the journal record
   Mental Wellbeing owes when this turn's trace holds none.
3. **The crisis line (M9).** `crisis_line_for()` / `ensure_crisis_line()`: the configured line
   for the user's country (config/modules/crisis_lines.yaml), appended to a reply to a suicide
   disclosure only when the reply does not already carry one of its numbers.

THE CLINICAL RULE, binding on everything here: code may ADD a flag, an instruction or a line; it
never clears, suppresses or rewrites one a model wrote. A view that could not be read
(`ok: False`) is UNKNOWN — never "nothing missed". Every public function here returns its
add-only result and never raises into the turn.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent

# The FLAGS-item parse core/orchestrator._drop_unprompted_clinical_flags uses — one home, so the
# item that is dropped on a no-words turn is exactly the item M8 completes and M9 triggers on.
CLINICAL_FLAG_ITEM_RE = re.compile(r"^(CLINICAL_CONCERN\b.*|ESCALATION|MUST_SURFACE\b.*)$", re.I)
_CONCERN_RE = re.compile(r"^CLINICAL_CONCERN\b\s*:?\s*([A-Za-z_]+)", re.I)
_EMPTY_VALUES = {"", "none", "n/a", "na", "-", "omit", "no", "nothing"}
SUICIDAL_IDEATION = "SUICIDAL_IDEATION"


# ---------------------------------------------------------------------------
# #8 — the medication check
# ---------------------------------------------------------------------------

def _crit(row: dict) -> str:
    return str(row.get("criticality") or "").strip().lower()


def _is_critical(row: dict) -> bool:
    """Ruling C (stop doc § 5): a `required` row, or a LINKED row whose profile entry exists but
    carries no criticality. An unlinked entry with no criticality is not critical (a note only);
    a broken link is never critical through this rule (it has no profile entry)."""
    crit = _crit(row)
    if crit == "required":
        return True
    if crit in ("optional", "as_needed"):
        return False
    # A renamed medicine joined to its habit (`relink_to`) is read against the NEW profile entry,
    # which exists — so ruling C applies to it as to any linked row (review item 7).
    in_profile = bool(row.get("in_profile")) or bool(row.get("relink_to"))
    return bool(row.get("linked")) and in_profile


def _surfaced_by_model(model_text: str, name: str) -> bool:
    """The model's own output already raises this medicine's critical flag WITH a real
    MUST_SURFACE (an empty or placeholder value does not count — `_has_must_surface`), so the
    appended note does not add a second MUST_SURFACE line for it (it adds the flag regardless)."""
    if not model_text:
        return False
    return (f"MEDICATION_MISSED_CRITICAL: {name}".upper() in model_text.upper()
            and _has_must_surface(model_text))


def _record_sentence(row: dict) -> str:
    """What the Synthesizer can do if the user says this turn they took it — naming only actions
    that exist for the row type (re-check L4: the Synthesizer holds update_task, not write_log)."""
    if row.get("linked") and row.get("task_id"):
        return (f"If the user says this turn that they took it, mark the dose done on its habit "
                f"(update_task, {row['task_id']}) and confirm it rather than warn.")
    return ("It has no dose habit, so nothing you hold can mark it taken. If the user says this "
            "turn that they took it, acknowledge it rather than warn, and offer to link it to a "
            "habit.")


def medication_note(persona: str | None = None, model_text: str = "") -> dict:
    """The code's medication check for this moment, from `medication_taken(persona=…)` read once.

    Returns {"text": str, "flags": [str], "critical": [name]}. Built from each row's own fields
    (`missed`, `criticality`, `linked`, `in_profile`, `needs_link`, `link_broken`, `relink_to`);
    nothing here recomputes whether a dose is due. `text` is "" when there is nothing to say.
    `model_text`: the specialist's own output, read only to avoid a second MUST_SURFACE line
    for a medicine the model already surfaced — pass it ONLY when the note is appended to that
    same output; a note bound for the Synthesizer's bundle line always carries its own
    MUST_SURFACE (review item 3). Never raises."""
    empty = {"text": "", "flags": [], "critical": []}
    try:
        from tools.obligations import medication_taken
        view = medication_taken(persona=persona)
    except Exception as exc:  # noqa: BLE001
        logger.warning("[medication] check unavailable: %s", exc)
        return empty
    try:
        if not isinstance(view, dict) or not view.get("ok"):
            return {"text": ("The medication record could not be read: UNKNOWN; do not say a dose "
                             "was missed or that all were taken."),
                    "flags": [], "critical": []}
        flags: list[str] = []
        critical: list[dict] = []
        notes: list[str] = []
        for row in view.get("medications") or []:
            if not isinstance(row, dict):
                continue
            name = str(row.get("medication") or "").strip()
            if not name:
                continue
            if row.get("link_broken") or row.get("relink_to"):
                flags.append(f"MEDICATION_LINK_BROKEN: {name}")
                # A plain broken link has no profile entry: the link flag only, never the
                # critical one. A renamed medicine already joined to its habit (`relink_to`) is
                # read as any other row — physical_health.md's rule — and ruling C still applies
                # (its old link is not "in profile", so only `required` makes it critical).
                if not row.get("relink_to"):
                    continue
            if row.get("needs_link"):
                flags.append(f"MEDICATION_NEEDS_LINK: {name}")
            missed = row.get("missed")
            if missed is None:
                notes.append(f"{name}: record UNKNOWN for today; do not say it was missed or taken.")
                continue
            if missed is not True:
                continue
            if _is_critical(row):
                flags.append(f"MEDICATION_MISSED_CRITICAL: {name}")
                critical.append(row)
            elif _crit(row) in ("optional", "as_needed"):
                flags.append(f"MEDICATION_MISSED_OPTIONAL: {name}")
            else:
                notes.append(f"{name}: no criticality on file, reads not logged today.")
        lines = list(dict.fromkeys(flags))
        for row in critical:
            name = str(row["medication"]).strip()
            lead = ("" if _surfaced_by_model(model_text, name)
                    else f"MUST_SURFACE: {name}, a required medication, reads missed today. ")
            lines.append(f"{lead}{'' if lead else name + ': '}{_record_sentence(row)}")
        lines += notes
        return {"text": "\n".join(lines), "flags": list(dict.fromkeys(flags)),
                "critical": [str(r["medication"]).strip() for r in critical]}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[medication] check failed: %s", exc)
        return empty


# ---------------------------------------------------------------------------
# M8 — a clinical concern's companions, completed by code
# ---------------------------------------------------------------------------

_MARKUP = "*_#>-•` \t"
_FLAGS_HEAD_RE = re.compile(r"^FLAGS[*_` ]*:[*_` ]*", re.I)
_FIELD_RE = re.compile(r"^[A-Z][A-Z _/-]+[*_` ]*:")
_BULLET_RE = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s+")
_SI_RE = re.compile(r"SUICIDAL[ _-]IDEATION", re.I)
_CONCERN_ITEM_RE = re.compile(r"CLINICAL[ _]CONCERN[*_` ]*(?:[:\-—–]|\s)\s*(.*)$", re.I)


def flag_items(text) -> list[str]:
    """The items of an output's FLAGS field — never its prose. Tolerant of markup: leading
    `*_#>-` and spaces before `FLAGS:` ("**FLAGS:**", "- FLAGS:"), items split on commas, and a
    bulleted list under a FLAGS: line (until the next `FIELD:` line or a blank line)."""
    if not isinstance(text, str):
        return []
    items: list[str] = []
    in_list = False
    for line in text.splitlines():
        bare = line.strip().lstrip(_MARKUP).strip()
        head = _FLAGS_HEAD_RE.match(bare)
        if head:
            rest = bare[head.end():].strip()
            items += [i.strip().strip(_MARKUP).strip() for i in rest.split(",") if i.strip()]
            in_list = True
            continue
        if in_list:
            if not line.strip() or (_FIELD_RE.match(bare) and not _BULLET_RE.match(line)):
                in_list = False
                continue
            if _BULLET_RE.match(line) or line[:1] in (" ", "\t"):
                items += [i.strip().strip(_MARKUP).strip()
                          for i in _BULLET_RE.sub("", line).split(",") if i.strip()]
                continue
            in_list = False
    return [i for i in items if i]


def clinical_concerns(text) -> list[str]:
    """The concerns raised by `CLINICAL_CONCERN` items in an output's FLAGS field, as names, in
    order, deduped. The separator after CLINICAL_CONCERN may be `:`, `-`, `—` or none. An item
    whose text holds SUICIDAL_IDEATION or "suicidal ideation" anywhere (also "DEPRESSION /
    SUICIDAL_IDEATION") yields SUICIDAL_IDEATION. Prose outside a FLAGS item never counts."""
    out: list[str] = []
    for item in flag_items(text):
        m = _CONCERN_ITEM_RE.search(item)
        if not m:
            continue
        if _SI_RE.search(item):
            out.append(SUICIDAL_IDEATION)
        for name in re.findall(r"[A-Za-z][A-Za-z_]*", m.group(1)):
            if name.upper() not in ("SUICIDAL", "IDEATION"):
                out.append(name.upper())
                break
    return list(dict.fromkeys(out))


def _has_must_surface(text: str) -> bool:
    for line in text.splitlines():
        stripped = line.strip().lstrip("*_#>- ").strip()
        if stripped.upper().startswith("MUST_SURFACE"):
            value = stripped.split(":", 1)[1].strip().strip("*_ ") if ":" in stripped else ""
            if value.casefold() not in _EMPTY_VALUES and not value.startswith("["):
                return True
    return False


def _area(agent: str) -> str:
    return agent.replace("_", " ").title()


def _in_words(concern: str) -> str:
    return concern.replace("_", " ").lower()


def _journal_already_written(trace, concerns: list[str]) -> set[str]:
    """Which of `concerns` already have this turn's record: all of them when Mental Wellbeing
    made an ok `write_journal` call in this trace; else those code recorded earlier this turn."""
    from core.trace import _walk_agents
    for rec in _walk_agents(list(getattr(trace, "pipeline", []) or [])):
        if getattr(rec, "agent", "") != "mental_wellbeing":
            continue
        for turn in rec.turns:
            for call in turn.tool_calls:
                if call.name == "write_journal" and call.ok:
                    return set(concerns)
    done = getattr(trace, "_code_journal_flags", None) or set()
    return {c for c in concerns if c in done}


def _write_code_journal(concerns: list[str], persona: str | None, user_text: str) -> bool:
    from core.persona import persona_scope, resolve_persona
    from tools.diarist import write_journal
    words = " and ".join(_in_words(c) for c in concerns)
    said = " ".join(str(user_text or "").split())[:600]
    text = (f"Mental Wellbeing raised a concern ({words}) on the user's message at "
            f"{datetime.now().strftime('%H:%M')}, and no journal entry was written for it. "
            f"Their words: «{said}»")
    with persona_scope(resolve_persona(persona)):
        out = write_journal(text, tags=["clinical", "recorded_by_code", *concerns])
    return not str(out).startswith("Error")


def complete_clinical_flags(outputs: dict, persona: str | None, user_text: str,
                            user_turn: bool) -> dict:
    """Each output's `CLINICAL_CONCERN` items completed by code, add-only.

    Real user turns only (see the guard below).

    1. An output raising a concern with no `MUST_SURFACE` gets one appended.
    2. Mental Wellbeing on a real user turn: unless this turn's trace already holds its
       `write_journal` (ok) — or code's own record for that flag — code writes one journal
       entry naming every unrecorded concern. No trace means UNKNOWN, so code writes: a
       duplicate entry is the cheap error, a missing clinical record the expensive one.
       Deduped by this turn's trace only; thread state is not consulted (amendment 1).

    Call AFTER _drop_unprompted_clinical_flags, so a scheduled turn's dropped flag is never
    re-armed. Returns a new dict; every value is the old value or the old value plus a suffix."""
    if not outputs or not user_turn:
        # No completion on a turn with no user words: this parse is more tolerant of markup than
        # _drop_unprompted_clinical_flags, so an item that drop did not recognise must not be
        # armed here on a scheduled turn. Nothing is removed either way.
        return outputs
    out = dict(outputs)
    for agent, text in outputs.items():
        try:
            concerns = clinical_concerns(text)
            if not concerns:
                continue
            if not _has_must_surface(text):
                out[agent] = (f"{text.rstrip()}\n\nMUST_SURFACE: {' and '.join(concerns)} raised "
                              f"by {_area(agent)} — surface it in this reply (added by code; the "
                              f"specialist's flag carried no instruction)")
            if agent != "mental_wellbeing":
                continue
            from core.trace import get_trace
            trace = get_trace()
            todo = concerns if trace is None else [
                c for c in concerns if c not in _journal_already_written(trace, concerns)]
            if not todo:
                continue
            if _write_code_journal(todo, persona, user_text) and trace is not None:
                done = getattr(trace, "_code_journal_flags", None)
                if done is None:
                    done = set()
                    setattr(trace, "_code_journal_flags", done)
                done.update(todo)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[clinical] completion failed for %s: %s", agent, exc)
    return out


# ---------------------------------------------------------------------------
# M9 — the crisis line
# ---------------------------------------------------------------------------

_CRISIS_PATH = _ROOT / "config" / "modules" / "crisis_lines.yaml"

# The last-resort line when crisis_lines.yaml cannot be read, or the append itself fails on a
# reply with no text: the yaml's `default` entry, so a crisis turn never ends with nothing. A
# deliberate fail-safe copy — the yaml is the one code reads whenever it can.
BUILTIN_CRISIS_LINE = (
    "If you are thinking of ending your life or feel you might act on it, please reach out now: "
    "Samaritans on 116 123 (free, any time), or text SHOUT to 85258; NHS 111, choosing the mental "
    "health option; 999 in an emergency — or your local emergency number if you are outside the UK.")


def raises_suicidal_ideation(outputs: dict) -> bool:
    """Mental Wellbeing's FLAGS line carries `CLINICAL_CONCERN: SUICIDAL_IDEATION` (amendment 2:
    the flag item, never a word in prose)."""
    try:
        return SUICIDAL_IDEATION in clinical_concerns((outputs or {}).get("mental_wellbeing"))
    except Exception:  # noqa: BLE001
        return False


def _load_crisis_config() -> dict:
    import yaml
    data = yaml.safe_load(_CRISIS_PATH.read_text()) or {}
    return data if isinstance(data, dict) else {}


def _country(persona: str | None) -> str:
    try:
        from core.persona import persona_scope, resolve_persona
        from tools import profile
        with persona_scope(resolve_persona(persona)):
            loc = (profile._load() or {}).get("location") or {}
        return str(loc.get("country") or "").strip() if isinstance(loc, dict) else ""
    except Exception:  # noqa: BLE001 — no profile is the default entry, never an error
        return ""


def crisis_line_for(persona: str | None = None) -> dict:
    """{"key", "line", "match"} for the user's country (`profile.location.country`, matched
    exactly, casefolded, against each entry's `aliases`); the `default` entry for no country or
    an unmatched one. Never raises: an unreadable config gives a built-in default line."""
    try:
        cfg = _load_crisis_config()
        country = " ".join(_country(persona).split()).casefold()
        for key, entry in (cfg.get("countries") or {}).items():
            aliases = {" ".join(str(a).split()).casefold() for a in (entry.get("aliases") or [])}
            aliases.add(str(key).casefold())
            if country and country in aliases:
                return {"key": str(key), "line": str(entry["line"]).strip(),
                        "match": [str(m) for m in entry.get("match") or []]}
        d = cfg["default"]
        return {"key": "default", "line": str(d["line"]).strip(),
                "match": [str(m) for m in d.get("match") or []]}
    except Exception as exc:  # noqa: BLE001
        logger.warning("[crisis] config unreadable, built-in default used: %s", exc)
        return {"key": "builtin", "line": BUILTIN_CRISIS_LINE,
                "match": ["116 123", "85258", "Samaritans"]}


def _match_pattern(token: str) -> re.Pattern:
    """A number matches with spaces and dashes optional between its digits; a name matches as a
    whole word, case-insensitively."""
    digits = re.sub(r"[\s-]", "", token)
    if digits.isdigit():
        return re.compile(r"(?<!\d)" + r"[\s-]*".join(digits) + r"(?!\d)")
    return re.compile(r"\b" + re.escape(token) + r"\b", re.I)


def carries_crisis_line(reply: str, entry: dict) -> bool:
    return any(_match_pattern(m).search(reply or "") for m in entry.get("match") or [])


def ensure_crisis_line(reply: str, persona: str | None = None) -> str:
    """`reply` unchanged when it already carries one of the configured `match` entries; else
    `reply.rstrip() + "\\n\\n" + line` (the line alone for an empty reply). Add-only: the rest
    of the reply is byte for byte the same. Never raises."""
    try:
        entry = crisis_line_for(persona)
        if carries_crisis_line(reply, entry):
            return reply
        if not (reply or "").strip():
            return entry["line"]
        return reply.rstrip() + "\n\n" + entry["line"]
    except Exception as exc:  # noqa: BLE001
        logger.warning("[crisis] line not ensured: %s", exc)
        return reply if (reply or "").strip() else BUILTIN_CRISIS_LINE


def crisis_bundle_line(persona: str | None = None) -> str:
    """The Synthesizer's bundle line on a turn that raised SUICIDAL_IDEATION."""
    return f"CRISIS LINE (from code): {crisis_line_for(persona)['line']} — include it in this reply."
