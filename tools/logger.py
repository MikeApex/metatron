"""
tools/logger.py — first working tool.

Provides write_log() and read_log() for storing and retrieving daily check-in records.
All logs are stored locally in data/logs/YYYY-MM-DD.json — Sensitive-tier from day one.
"""

import json
import os
import re
import threading
from datetime import date, datetime
from pathlib import Path

from core.persona import PersonaError, persona_data_dir, persona_scope, resolve_persona
from tools.record_rules import RELATIVE_REFERENCES
from core.background import run_background


# [DB-0815-09] A model asked to fill a slot in a structured output template answers the slot
# rather than deleting it, so "no correction happened" arrives as the word "None" instead of an
# absent line. These are the forms actually observed in 93 of 174 live USER_CORRECTION events on
# 2026-08-15 — not a speculative list. Bracketed variants are included because the Coordinator
# wraps its non-answers: "[N/A - the user's message is a shift in intent, not a correction]".
#
# Deliberately NOT a substring match. "None of the medication was taken" is a real correction and
# must survive; this compares the whole stripped value, and the long-bracketed form is caught by
# the prefix rule below rather than by widening the set.
_NULL_ISH = {
    "none", "n/a", "na", "null", "nil", "nothing", "no correction", "not applicable",
    "no corrections", "-", "--", "—", "[none]", "[n/a]", "()", "[]",
}


# [DB-0827-07] The same template failure one slot along. Where [DB-0815-09] saw the slot
# answered with the word "None", 33 live events since 2026-08-18 have a detail that is
# exactly `CLARIFICATION_NEEDED:` — the model filled the USER_CORRECTION slot with the
# label of the template line next to it and no content at all. A bare label is a fragment
# of the output format, never something that happened, so it is a non-answer in the same
# sense as "N/A".
#
# The match is deliberately narrow: ALL-CAPS word (underscores, hyphens or single spaces
# between words) followed by a colon, and it is only null-ish if what FOLLOWS the colon is
# empty or itself null-ish. "CLARIFICATION_NEEDED: which Bill?" is real signal and survives.
_TEMPLATE_LABEL_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:[ _-][A-Z0-9]+)*\s*:(.*)$", re.DOTALL)


def _null_value(text: str) -> bool:
    """The scalar half of is_null_ish(): is this value itself a non-answer?"""
    stripped = (text or "").strip().strip("[](){}\"'").strip().rstrip(".!?").strip().lower()
    if not stripped:
        return True
    if stripped in _NULL_ISH:
        return True
    # "[N/A - the user's message is a shift in intent, not a correction of a past error.]"
    return any(stripped.startswith(f"{tag} -") or stripped.startswith(f"{tag} —")
               for tag in ("n/a", "na", "none"))


def is_null_ish(text: str) -> bool:
    """
    True when `text` is a model's way of saying "this field does not apply".

    Whole-value comparison after stripping surrounding brackets, quotes and terminal
    punctuation — never a substring test, so a genuine correction that merely begins with
    the word "none" is unaffected. The one prefix rule covers the observed bracketed
    explanation form ("[N/A - ...]"), which is a non-answer of arbitrary length.

    Also true for a bare template label with nothing behind it — `CLARIFICATION_NEEDED:` —
    which is the same template-filling reflex leaving a piece of the output format in the
    payload. A label WITH content after the colon is kept, label and all: the label is
    part of what the model meant, and stripping it would rewrite the record.
    """
    if _null_value(text):
        return True
    match = _TEMPLATE_LABEL_RE.match((text or "").strip().strip("[](){}\"'").strip())
    return bool(match) and _null_value(match.group(1))


# --- ROUTING_MISS that reports a success ------------------------------------
#
# [DB-0902-01]. From 2026-06-22 to 2026-08-29 every ROUTING_MISS in the live log was a
# real routing fault, and several became backlog items — the referent-resolution work of
# [DB-0826-01] started as one. From 2026-09-01 the same event type began carrying
# *"Coordinator handled morning session prompt successfully."*, *"Routed inbox check and
# logistics task appropriately."*, *"...without routing error."* Measured on the live log
# 2026-09-03: 19 events before 09-01, of which 0 are noise; 15 from 09-01 on, of which 13
# are. The break is exactly the 09-01 fleet migration, with no code change between.
#
# The cause is an instruction gap the model change exposed: `config/agents/coordinator.md`
# defines USER_CORRECTION at length and **never defines ROUTING_MISS at all** — line 208
# lists it as an available event type and nothing tells the Coordinator what one is. Only
# `synthesizer.md` carries the definition. gemini-3.1-pro-preview inferred it correctly for
# three months; gemini-3.7-flash fills the slot with a description of what it just did.
# That half is an agent-file fix and is not made here.
#
# What IS made here is the half code can decide without guessing: an event whose detail
# asserts the routing went RIGHT is self-contradictory with its own type, whatever the
# model meant. This is deliberately NOT the is_null_ish() test from [DB-0827-07] — these
# payloads are non-empty and that check correctly passes them.
#
# The rule is tuned for precision, not recall, because the two errors cost very different
# things: dropping a noise event costs nothing, and dropping a real routing fault costs the
# signal this event type exists to carry. Measured against all 34 events in the live log:
# **0 of 21 genuine misses rejected**, 8 of 13 noise events rejected. The 5 it lets
# through assert nothing about success — they are merely descriptive ("Coordinator test run
# check"), which is a different defect and one that cannot be separated from a real report
# without the semantic guessing this guard exists to avoid.

_SUCCESS_CLAIM_RE = re.compile(
    r"\b(successful(?:ly)?|correctly|appropriately|properly|as required|as expected|"
    r"valid(?:ly)?|without (?:a |any )?(?:routing )?(?:error|miss|issue|problem)s?|"
    r"no (?:routing )?(?:error|miss|issue)s?)\b", re.I)

# "Agents not called successfully" is a failure report that happens to contain the word
# "successfully" — a real 2026-06-26 event, and the one case that made a naive keyword
# rule reject a genuine miss.
_NEGATOR_RE = re.compile(
    r"\b(not|never|no|without|fail(?:ed|s|ing)?|unable|rather than|instead of|"
    r"lack(?:ing|ed)?|absent|missing)\b", re.I)

_FAILURE_CLAIM_RE = re.compile(
    r"\b(miss(?:ed|es|ing)|mis(?:interpret|ident|underst|read|took|rout|handl)\w*|"
    r"instead of|rather than|fail(?:ed|ure|s)|did ?n[o']t|does ?n[o']t|was ?n[o']t|"
    r"were ?n[o']t|could ?n[o']t|not (?:called|routed|surfaced|executed|taken|"
    r"come through|received)|no (?:response|specialist|output|data)|incorrect\w*|"
    r"wrong\w*|unable|omitted|skipped|lost|error|gap|should have)\b", re.I)


def asserts_routing_success(detail: str) -> bool:
    """True when a ROUTING_MISS detail claims the routing went right and names nothing
    that went wrong — an event asserting the opposite of its own type.

    Both halves are required. A detail that claims success AND names a failure is kept:
    *"...handled appropriately as an anticipatory logistics pass"* alongside a real
    complaint is ambiguous, and ambiguity resolves in favour of keeping the event.
    """
    text = detail or ""

    claims_success = False
    for m in _SUCCESS_CLAIM_RE.finditer(text):
        # "without a routing error" and "no routing miss" carry their own negator and
        # are success assertions as they stand — matched whole, so exempt from the
        # look-back below.
        if m.group(0).lower().startswith(("without", "no ")):
            claims_success = True
            continue
        if not _NEGATOR_RE.search(text[max(0, m.start() - 40):m.start()]):
            claims_success = True

    if not claims_success:
        return False

    # Strip the success phrases before looking for failure words, or the "miss" inside
    # "without routing miss" reads as a report of a miss.
    return not _FAILURE_CLAIM_RE.search(_SUCCESS_CLAIM_RE.sub(" ", text))


# [DB-0902-01] — the second half of the routing-miss noise. A scheduler-opened session has no
# words from the user, and the Coordinator keeps filing that fact as a ROUTING_MISS ("scheduled
# quiet check-in, no user message", "the anticipatory pass was treated as a user message") —
# ~25 of 56 events 10-29 -> 11-26, burying the real ones. coordinator.md:46-50 already forbids
# it and is ignored, so the control is here. Applied ONLY on a no-user-words turn (see
# _no_user_words) and tuned for precision like asserts_routing_success: a detail is refused
# only when it describes the session's own nature AND names no specialist and no output fault.
# A real miss on a scheduled turn names who was missed ("never reached physical_health").
_SESSION_NATURE_RE = re.compile(
    r"\b(scheduled\s+(?:session|prompt|run|check-?in|quiet|anticipatory|morning|evening|"
    r"day-?close|pass|trigger|job|directive|message|brief|opening|background|greeting|"
    r"silent|proactive)|scheduler|automated|programmatic|system[- ](?:prompt|directive|"
    r"instruction)|session prompt|quiet check-?in|anticipatory (?:logistics )?pass|"
    r"no user (?:message|input|utterance|speech|words)|without (?:a )?user (?:message|input)|"
    r"user did not send|day-?close session)\b", re.I)

_NAMED_SPECIALIST_RE = re.compile(
    r"\b(physical[_ ]health|mental[_ ]wellbeing|diarist|goals?[_ ](?:specialist|agent)|"
    r"finance|relationships|work[_ ]vocation|research[_ ]agent|synthesizer|"
    r"(?:no|any|without|missing|omitted|skipped)\s+(?:the\s+)?specialists?|"
    r"specialists?\s+(?:call|dispatch|consult)\w*|"
    r"structured format|parse\w*|malformed|truncat\w*|incomplete|unhandled|"
    # every agent in config/agents/*.md, bare or underscored, plus the short forms the
    # Coordinator uses; and ordinary fault phrasing — a real miss names who or says what failed.
    r"logistics|recreation(?:[_ ]hobbies)?|learning(?:[_ ]growth)?|time[_ ]director|"
    r"pattern[_ ]miner|day[_ ]planner|project[_ ]planner|goals|health|wellbeing|"
    r"work[_ ]vocation|tone[_ ]profiler|task[_ ]judge|crm[_ ]sweep|"
    r"not\s+(?:consulted|called|dispatched|routed)|never\s+(?:called|consulted|dispatched|"
    r"reached)|routed\s+to\s+nobody|did\s+not\s+reach|missed\s+the|should\s+have)\b", re.I)


def describes_scheduled_session(detail: str) -> bool:
    """True when a ROUTING_MISS detail is only the Coordinator remarking that the session was
    scheduler-opened, with no named specialist and no output fault. Call it on no-user-words
    turns only; on a user turn the same words can be a real report."""
    text = re.sub(r"anticipatory logistics pass", "anticipatory pass", detail or "", flags=re.I)
    return bool(_SESSION_NATURE_RE.search(text)) and not _NAMED_SPECIALIST_RE.search(text)


_WRITE_LOG_LOCK = threading.Lock()
_WRITE_QUALITY_EVENT_LOCK = threading.Lock()

_ROOT = Path(__file__).parent.parent


def _logs_dir() -> Path:
    return persona_data_dir() / "logs"


def _deep_merge(base: dict, incoming: dict) -> dict:
    """
    Merge `incoming` into `base`, recursing into nested dicts.

    This used to be `base.update(incoming)`, which is correct for the flat top-level keys
    the log accumulated in practice and silently destructive for the nested blocks the
    specialists actually declare. Physical Health writing `{"health": {"sleep_hours": 7.5,
    "sleep_quality": "good"}}` in the morning and `{"health": {"energy": "low"}}` in the
    evening ended the day with `health` holding energy alone — the morning's two fields
    replaced wholesale, no error, no trace.

    That is very likely part of why nothing ever adopted the nested shape: across 70 log
    files the `health` and `wellbeing` blocks appear in 4, while flat `mood`/`energy`/`focus`
    appear in ~60. A flat scalar survives `update()`; a nested sibling does not. So this
    function is the guard that has to exist *before* anything encourages nested writes —
    doing it the other way round would have converted a schema mismatch into data loss.
    (`[DB-0809-20]`.)

    Lists are replaced rather than concatenated. `tasks_completed` is a restatement of the day's
    state, not an append-only feed — merging it would duplicate every entry on the second write of
    the day. `medications_logged` reaches here already merged by medicine name
    (`_merge_medications`, 2026-11-23), so replacing it loses nothing.
    """
    out = dict(base)
    for key, value in incoming.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


# [DB-0822-06] Per-field write times, kept in one flat map at the top of the log rather than
# by wrapping each value as {"value": ..., "at": ...}.
#
# The wrapping shape was rejected: it changes what every existing reader sees — read_log,
# get_log_window, tools/analytics.py, the memory index — and it invalidates every log file
# already on the VM, all at once, for a benefit that is purely additive. A sidecar key is
# ignored by anything that does not know about it, so a file written before this shipped
# reads exactly as it did, and no migration runs anywhere.
#
# The map is DERIVED, never model-supplied. A specialist that can write its own timestamp can
# claim a stale field is fresh, which is the failure this exists to catch, so an incoming
# `_written_at` is discarded rather than merged (same discipline as _thread_tier in
# tools/context_tracker.py).
_WRITTEN_AT_KEY = "_written_at"

# Stage 4 #14: beside each write time, WHO the write came from — "user" (a real user turn, the
# Diarist's background write included), "scheduled" (a turn with no user words: a scheduled
# session, a weekly job's proactive trace) or "unknown" (no turn, no trace: a script). Derived,
# never model-supplied, exactly as `_written_at` is. Code's domain counters
# (tools/domain_counters.py) count only "user" leaves, so a log the system wrote during a
# scheduled check-in never becomes evidence about the user.
_WRITTEN_ON_KEY = "_written_on"


def _write_provenance() -> str:
    """Where this write_log call came from: "user" | "scheduled" | "unknown". Never raises.

    A bound turn answers decisively. With none bound: the Diarist is "user" (its dispatch is
    refused on a turn with no user words, [DB-0822-05], and its thread binds no turn on purpose
    — the decline guard in tools/confirm.py reads an unbound thread); otherwise the trace's own
    real-user-turn status (Stage 4 build-time amendment 3) — a proactive trace is "scheduled",
    any other trace is a user's (a user turn's background hand-off, the CLI). No trace at all is
    "unknown"."""
    try:
        from tools.turn_context import current
        turn = current()
        if turn is not None:
            return "user" if turn.get("user_turn") else "scheduled"
        from core.trace import get_current_agent, get_trace
        trace = get_trace()
        # A proactive trace first: a Diarist handed off from a turn-less proactive job (a weekly
        # single-agent run's run_subagent) is writing the system's words, not the user's.
        if trace is not None and trace.is_proactive:
            return "scheduled"
        if str(getattr(get_current_agent(), "agent", "") or "") == "diarist":
            return "user"
        if trace is not None:
            return "user"
    except Exception:  # noqa: BLE001 — provenance must never cost the write
        pass
    return "unknown"


def _leaf_paths(node: dict, prefix: str = "") -> list[str]:
    """
    Dotted path of every leaf value in `node` — "notes", "health.energy".

    Nested dicts recurse so siblings are stamped independently: the whole reason
    _deep_merge exists is that a morning write of `health.sleep_hours` and an evening write
    of `health.energy` are two separate assertions, and a single stamp on `health` would
    re-date the morning's field every evening. Lists are leaves — _deep_merge replaces them
    wholesale, so the list is one assertion.

    `date` and the map itself are skipped at the top level: neither is something a person
    told us.
    """
    paths: list[str] = []
    for key, value in node.items():
        if not prefix and key in (_WRITTEN_AT_KEY, _WRITTEN_ON_KEY, "date"):
            continue
        path = f"{prefix}{key}"
        if isinstance(value, dict) and value:
            paths.extend(_leaf_paths(value, f"{path}."))
        else:
            paths.append(path)
    return paths


# [DB-0827-09] ruling (a), Mike 2026-08-28: intentions accumulate as a LIST.
#
# The Diarist writes one intention per `write_log` call as a top-level scalar
# (`config/agents/diarist.md` § "A user-stated intention IS loggable"), and _deep_merge
# replaces a top-level scalar wholesale — so a second intention voiced the same day
# silently overwrote the first, and a restatement left no trace at all. Nothing is
# deduped: **every statement appends, restatements included**, because how often an
# intention is voiced is the signal ("frequency scores urgency"), and a dedup here would
# destroy exactly the thing the ruling asked to keep.
#
# Special-cased in write_log rather than in _deep_merge, which stays general. Lists in
# the day log are restatements of the day's *state* — `tasks_completed`,
# `medications_logged` — so an appending merge would duplicate every one of them on the
# second write of the day. This one key is a feed; the merge rule is not the place to say so.
#
# Legacy scalar `intention` keys already on disk are left exactly as they are: no
# migration runs anywhere, and tools/accountability.py reads both shapes.
_INTENTIONS_KEY = "intentions"


# The day's health notes as a FEED, beside the scalars they would otherwise overwrite.
#
# `health.symptoms` and `health.medical_notes` are one free-text scalar each, and
# _deep_merge replaces a scalar, so every write replaced the one before. 2026-11-13 to
# 11-16: Mike's cardiac event log (time + what he was doing, for his cardiologist) lost
# four of six events that way — the 11:42 entry overwritten by the evening close, the
# 15:08 one by a 17:10 write — and nothing reported it. Same failure, same repair as
# `intentions` above: the scalars keep merging exactly as before, so no reader changes, and
# every value written is also appended here with when it was written and, where the client
# stamped one, when it was spoken. An exact repeat of the field's previous entry is not
# appended again — unlike an intention, a restated note carries no frequency signal.
_HEALTH_NOTES_KEY = "health_notes"
_HEALTH_NOTE_FIELDS = ("symptoms", "medical_notes")


def _health_note_entries(content: dict, written_at: str) -> list[dict]:
    """The feed entries this write adds — one per non-empty health note field it carries."""
    health = content.get("health")
    if not isinstance(health, dict):
        return []
    from tools.turn_context import current_spoken
    spoken = current_spoken()
    entries = []
    for field in _HEALTH_NOTE_FIELDS:
        text = health.get(field)
        if not isinstance(text, str) or not text.strip():
            continue
        entry = {"field": field, "text": text.strip(), "written_at": written_at}
        if spoken:
            entry["spoken"] = spoken
        entries.append(entry)
    return entries


def _append_health_notes(feed, entries: list[dict]) -> list:
    """`feed` with `entries` appended, skipping one identical to its field's last entry."""
    feed = list(feed) if isinstance(feed, list) else []   # a non-list is corrupt
    for entry in entries:
        last = next((e for e in reversed(feed)
                     if isinstance(e, dict) and e.get("field") == entry["field"]), None)
        if last is not None and last.get("text") == entry["text"]:
            continue
        feed.append(entry)
    return feed


def _split_intention(content: dict) -> tuple[dict, dict | None]:
    """
    Lift a top-level scalar `intention` (plus its optional `stated_for`) out of `content`.

    Returns `(content without those keys, the entry to append)`, or `(content, None)`
    when the write carries no intention. A `stated_for` with no `intention` beside it is
    left in place untouched — it means nothing on its own, and inventing an intention to
    hang it on would be this function writing a record nobody asserted.
    """
    intention = content.get("intention")
    if not isinstance(intention, str) or not intention.strip():
        return content, None
    rest = {k: v for k, v in content.items() if k not in ("intention", "stated_for")}
    stated_for = content.get("stated_for")
    return rest, {
        "intention": intention.strip(),
        "stated_for": stated_for.strip() if isinstance(stated_for, str) else "",
    }


# One record per dose, PER MEDICINE (owner's ruling, 2026-11-23: "PH and the rest of Metatron work
# from the same data"; applied per medicine after the review the same day). A medicine with an
# open habit linked to it (`medication`) has its doses in the task ledger — the habit marked done
# — and "Medication taken today" reads them there (tools/obligations.medication_taken). For that
# medicine a `medications_logged` entry would be a second record of the same dose, written by a
# model from the conversation, and two records of one dose can disagree in a hard-fail domain:
# its entries are dropped, and the tool result names them so a model that still sends them
# learns. A medicine with NO linked habit keeps its entries: for it the daily log is the only
# record, and dropping it silenced every missed required dose of a medicine nobody had linked.
# When the ledger cannot be read, nothing is dropped — keeping a record can never hide a miss.
#
# A top-level `medications_logged` is the same record misplaced: what it keeps moves under
# `health`. Each kept entry is stamped `logged_at` (persona-local), and merged with the file's
# earlier ones BY NAME AND LEDGER DAY, not replaced as a list: a later write naming one medicine
# must not erase the only record of another's dose.
# Logs already on disk keep the values they hold — nothing here rewrites an earlier day.
_MEDICATIONS_KEY = "medications_logged"


def _medications_note(names: list[str]) -> str:
    return (f" — the medications_logged entr{'y' if len(names) == 1 else 'ies'} for "
            f"{', '.join(names)} {'was' if len(names) == 1 else 'were'} not stored: "
            f"{'that medication has' if len(names) == 1 else 'each has'} a habit, so a dose is "
            f"recorded by marking the habit done in the task ledger, and read back from "
            f"\"Medication taken today\". Entries for medications with no habit are kept.")


def _med_name_key(entry) -> str:
    name = entry.get("name") if isinstance(entry, dict) else None
    return " ".join(str(name or "").split()).casefold()


def _strip_medications(content: dict) -> tuple[dict, list[str]]:
    """`content` with the `medications_logged` entries of LINKED medicines removed and the rest
    gathered under `health`, and the names removed. See the note above."""
    top = content.get(_MEDICATIONS_KEY)
    health = content.get("health")
    nested = health.get(_MEDICATIONS_KEY) if isinstance(health, dict) else None
    if top is None and nested is None:
        return content, []
    try:
        from tools.obligations import linked_medication_keys
        linked = linked_medication_keys() or set()
    except Exception:  # noqa: BLE001 — cannot tell which are linked: keep every entry
        linked = set()
    entries = [e for part in (nested, top) if isinstance(part, list) for e in part]
    kept = [e for e in entries if not (_med_name_key(e) and _med_name_key(e) in linked)]
    dropped = [str(e.get("name")).strip() for e in entries
               if _med_name_key(e) and _med_name_key(e) in linked]
    content = {k: v for k, v in content.items() if k != _MEDICATIONS_KEY}
    if health is not None and not isinstance(health, dict):
        # A malformed `health` is not reshaped here; what is kept stays where it was sent.
        if kept:
            content[_MEDICATIONS_KEY] = kept
        return content, list(dict.fromkeys(dropped))
    rest = {k: v for k, v in (health or {}).items() if k != _MEDICATIONS_KEY}
    if kept:
        rest[_MEDICATIONS_KEY] = kept
    if rest:
        content["health"] = rest
    else:
        content.pop("health", None)
    return content, list(dict.fromkeys(dropped))


def _stamp_medications(content: dict) -> dict:
    """Each kept `health.medications_logged` entry stamped `logged_at` — when it was written, on
    the persona's own clock (second review, finding 5). The log FILE is dated by the machine's
    calendar; the medication view places an entry on the persona's ledger day by this stamp, so
    a dose logged at 01:30 on a day that starts at 04:00 counts for the day the user was still in.
    Always overwritten: a time a model chose is not evidence of when anything was written (the
    `_WRITTEN_AT_KEY` rule)."""
    health = content.get("health")
    entries = health.get(_MEDICATIONS_KEY) if isinstance(health, dict) else None
    if not isinstance(entries, list) or not entries:
        return content
    try:
        from tools.obligations import _stamp
        now = _stamp()
    except Exception:  # noqa: BLE001
        now = datetime.now().isoformat(timespec="seconds")
    stamped = [{**e, "logged_at": now} if isinstance(e, dict) else e for e in entries]
    return {**content, "health": {**health, _MEDICATIONS_KEY: stamped}}


def _entry_day(entry, log_date: str) -> str:
    """The ledger day an entry belongs to: its `logged_at`, else (an entry from before the stamp)
    the date of the file it is in."""
    stamp = entry.get("logged_at") if isinstance(entry, dict) else None
    if stamp:
        try:
            from tools.obligations import _stamp_day
            day = _stamp_day(stamp)
            if day:
                return day.isoformat()
        except Exception:  # noqa: BLE001
            pass
    return log_date


def _merge_medications(existing: dict, content: dict, log_date: str = "") -> dict:
    """`content` with its kept `health.medications_logged` merged into the file's earlier entries
    by medicine name AND ledger day — an entry for the same medicine on the same day replaces the
    earlier one; every other entry stays (one file can hold two ledger days around midnight)."""
    incoming = (content.get("health") or {}).get(_MEDICATIONS_KEY) \
        if isinstance(content.get("health"), dict) else None
    if not incoming:
        return content
    prior = (existing.get("health") or {}).get(_MEDICATIONS_KEY) \
        if isinstance(existing.get("health"), dict) else None
    if not isinstance(prior, list) or not prior:
        return content
    named = {(_med_name_key(e), _entry_day(e, log_date)) for e in incoming if _med_name_key(e)}
    merged = [e for e in prior
              if not (_med_name_key(e) and (_med_name_key(e), _entry_day(e, log_date)) in named)]
    return {**content, "health": {**content["health"], _MEDICATIONS_KEY: merged + incoming}}


# --- Finance transactions: ids set by code, merged by id (Stage 3 plan § 1.2, ruling E) -------
# `finance.transactions` is a list, and _deep_merge replaces lists — so a second Finance write in
# a day that sent only the new purchase erased every earlier one. Merging by content instead
# (a multiset) doubles a restated or corrected transaction. So code gives every stored transaction
# an id, and a write is merged against the stored list:
#   - an entry with a known `id` updates that entry in place, field by field (a correction;
#     amendment 5 — `type`, category and description stay unless resent), stamped `corrected_at`;
#   - `{"id": X, "remove": true}` marks entry X `removed: true` and keeps it (archive-on-merge);
#   - an entry with an unknown `id` is refused and not written;
#   - an entry with no `id` is NEW — except inside a RESTATEMENT: a write whose list carries the
#     id of every stored, not-removed transaction, when the stored list holds at least one id
#     (amendment 3: a legacy file with no ids is never a restatement). Only there are id-less
#     entries matched by shape against stored id-less entries; per shape, new = incoming count
#     minus stored count (floor 0);
#   - an earlier entry the write does not mention is always kept: a second write never erases.
#   - an entry carrying `"replaces": X` (with its own id, or none) is the correction of X in one
#     step: X is marked removed (`replaced_by`) and kept; only the replacing entry counts;
#   - an id from another day is refused with that day named, so it is resent there, never
#     re-recorded here as new.
# A new id-less entry with the same description as one already logged that day is recorded as new,
# and the reply names both ids and the exact `replaces` write that turns it into a correction —
# following it leaves one counted entry. Legacy id-less entries get ids after the merge; nothing is
# renumbered.
_TX_ID_RE = re.compile(r"^tx-\d{4}-\d{2}-\d{2}-(\d+)$")
_TX_DAY_RE = re.compile(r"^tx-(\d{4}-\d{2}-\d{2})-\d+$")


def _tx_shape(entry: dict) -> tuple:
    from tools.finance_totals import amount_cents, norm
    return (norm(entry.get("description")), amount_cents(entry.get("amount")),
            norm(entry.get("financial_category")), norm(entry.get("type")))


def _tx_label(entry: dict) -> str:
    from tools.finance_totals import amount_cents, money
    cents = amount_cents(entry.get("amount"))
    desc = str(entry.get("description") or "no description").strip()
    return f"{desc}, {money(cents) if cents is not None else entry.get('amount')}"


def _unknown_id_line(tid: str, log_date: str, what: str = "no transaction") -> str:
    """The refusal for an id this day's file does not hold. An id embeds its day, so one from
    another day is named as such — resending it without an id would record a duplicate
    (review item 4)."""
    m = _TX_DAY_RE.match(str(tid))
    if m and m.group(1) != log_date:
        return (f"Not written: {tid} belongs to {m.group(1)}, not {log_date}; resend it with "
                f"log_date: {m.group(1)}.")
    return (f"Not written: {what} with id {tid} is logged on {log_date}; to record a new "
            f"purchase, write it without an id.")


def _merge_transactions(existing: dict, content: dict, log_date: str) -> tuple[dict, list[str]]:
    """`content` with `finance.transactions` replaced by the full merged list (so _deep_merge's
    list replace then writes the merged result), and the reply lines. A write with no
    `finance.transactions` key is returned unchanged. See the note above."""
    fin = content.get("finance")
    if not isinstance(fin, dict) or "transactions" not in fin:
        return content, []
    incoming = fin.get("transactions")
    if not isinstance(incoming, list):
        rest = {k: v for k, v in fin.items() if k != "transactions"}
        content = {**content, "finance": rest} if rest else {
            k: v for k, v in content.items() if k != "finance"}
        return content, ["Transactions not written: `finance.transactions` must be a list."]
    try:
        from tools.obligations import _stamp
        now = _stamp()
    except Exception:  # noqa: BLE001
        now = datetime.now().isoformat(timespec="seconds")
    prior_fin = existing.get("finance") if isinstance(existing.get("finance"), dict) else {}
    prior_txs = prior_fin.get("transactions")
    stored = ([dict(e) for e in prior_txs if isinstance(e, dict)]
              if isinstance(prior_txs, list) else [])
    by_id = {e["id"]: e for e in stored if e.get("id")}
    live_ids = {i for i, e in by_id.items() if not e.get("removed")}
    top = max([int(m.group(1)) for i in by_id if (m := _TX_ID_RE.match(str(i)))] or [0])

    def next_id() -> str:
        nonlocal top
        top += 1
        return f"tx-{log_date}-{top}"

    lines: list[str] = []

    def set_aside(old: str, by: str) -> None:
        """`old` replaced by `by`: kept in the file, marked removed, never counted."""
        target = by_id[old]
        if not target.get("removed"):
            target.update(removed=True, removed_at=now, replaced_by=by)
            lines.append(f"Replaced: {old} ({_tx_label(target)}) is set aside; {by} counts "
                         f"instead.")

    incoming_ids = {e.get("id") for e in incoming if isinstance(e, dict) and e.get("id")}
    restatement = bool(live_ids) and live_ids <= incoming_ids
    new_entries: list[dict] = []
    replacing: list[dict] = []        # id-less entries that name the entry they replace
    idless: list[dict] = []
    for e in incoming:
        if not isinstance(e, dict):
            lines.append("Not written: a transaction that is not an object.")
            continue
        tid, old = e.get("id"), e.get("replaces")
        if old and (old not in by_id or old == tid):
            lines.append(_unknown_id_line(old, log_date, "nothing to replace: no transaction")
                         if old != tid else f"Not written: {tid} cannot replace itself.")
            continue
        if tid:
            if tid not in by_id:
                lines.append(_unknown_id_line(tid, log_date))
                continue
            target = by_id[tid]
            if e.get("remove") is True:
                if not target.get("removed"):
                    target.update(removed=True, removed_at=now)
                    lines.append(f"Removed: {tid} ({_tx_label(target)}).")
                continue
            fields = {k: v for k, v in e.items() if k not in ("id", "remove", "logged_at",
                                                               "corrected_at", "removed_at",
                                                               "replaced_by")}
            if any(target.get(k) != v for k, v in fields.items()):
                target.update(fields)
                target["corrected_at"] = now
                lines.append(f"Corrected: {tid} ({_tx_label(target)}).")
            if old:
                set_aside(old, tid)
            continue
        if e.get("remove") is True:
            lines.append("Not written: a removal needs the transaction's id.")
            continue
        clean = {k: v for k, v in e.items() if k not in ("remove", "removed", "removed_at",
                                                          "corrected_at", "replaced_by")}
        (replacing if old else idless).append(clean)
    if restatement:
        # Matched only against stored id-less (legacy) entries — see the note above.
        budget: dict[tuple, int] = {}
        for s_e in stored:
            if not s_e.get("id") and not s_e.get("removed"):
                budget[_tx_shape(s_e)] = budget.get(_tx_shape(s_e), 0) + 1
        for e in idless:
            shape = _tx_shape(e)
            if budget.get(shape, 0) > 0:
                budget[shape] -= 1
                continue
            new_entries.append(e)
    else:
        new_entries = idless
    for s_e in stored:            # legacy entries take ids after the merge; nothing renumbered
        if not s_e.get("id"):
            s_e["id"] = next_id()
    known_desc = {}
    for s_e in stored:
        if not s_e.get("removed") and str(s_e.get("description") or "").strip():
            known_desc.setdefault(_tx_shape(s_e)[0], s_e["id"])
    recorded = []
    for e in replacing:           # a one-step correction: the new entry, and the old set aside
        e = {**e, "id": next_id(), "logged_at": now}
        recorded.append(e)
        set_aside(e["replaces"], e["id"])
    for e in new_entries:
        e = {**e, "id": next_id(), "logged_at": now}
        recorded.append(e)
        same = known_desc.get(_tx_shape(e)[0]) if _tx_shape(e)[0] else None
        if same:
            lines.append(f"Recorded as new: '{e.get('description')}' {_tx_label(e).rsplit(', ', 1)[-1]} "
                         f"(id {e['id']}). An entry with the same description is already logged "
                         f"today (id {same}). If this was a correction of {same} rather than a "
                         f"second purchase, write {{\"id\": \"{e['id']}\", \"replaces\": "
                         f"\"{same}\"}}: {same} is then set aside and only {e['id']} counts.")
    if recorded:
        lines.insert(0, "Transactions recorded: " + "; ".join(
            f"{e['id']} ({_tx_label(e)})" for e in recorded) + ".")
    merged = stored + recorded
    return {**content, "finance": {**fin, "transactions": merged}}, lines


def write_log(content: dict | None = None, log_date: str = "") -> str:
    """
    Write a daily log entry to data/logs/YYYY-MM-DD.json.

    Args:
        log_date: Date string in YYYY-MM-DD format. Defaults to today if empty.
        content: Dictionary of log fields (mood, energy, focus, tasks, etc.)

    Returns:
        Confirmation string with the path written.
    """
    if content is None:
        content = {}
    elif isinstance(content, str):
        content = {"notes": content}
    elif not isinstance(content, dict):
        content = {}
    else:
        content = dict(content)

    # A write time the model chose is not evidence of when anything was written. Discarded
    # before the merge, so a forged map can never displace the real one — see _WRITTEN_AT_KEY.
    content.pop(_WRITTEN_AT_KEY, None)
    content.pop(_WRITTEN_ON_KEY, None)    # same discipline: provenance is derived, never sent

    # One record per dose — see _strip_medications.
    content, dropped_meds = _strip_medications(content)

    # Held out of the merge entirely — see _split_intention. It is appended to the day's
    # `intentions` feed after the merge, so a scalar can never reach _deep_merge and
    # replace the statement before it.
    content, intention_entry = _split_intention(content)

    if not log_date:
        log_date = date.today().isoformat()
    else:
        # [DB-0809-12]: a specialist computing "today" itself, rather than reading the
        # clock line every directive carries, has invented a wrong year before — a
        # credit-card reminder landed in a log dated 2025-05-22, fourteen months in the
        # past, on 2026-08-02. Nine such files accumulated silently before anyone
        # noticed. No legitimate write needs a date this far from the real clock: a
        # session crossing midnight or backfilling a missed day explains ±1, nothing
        # explains ±1 year. Refused rather than warned — unlike a near-duplicate
        # obligation or an over-cap write, there is no reading of a year-old log_date
        # that this would wrongly block.
        try:
            parsed = date.fromisoformat(log_date)
        except ValueError:
            return (f"Error: log_date {log_date!r} is not a valid YYYY-MM-DD date. "
                    f"Omit it to default to today.")
        drift_days = abs((parsed - date.today()).days)
        if drift_days > 7:
            return (f"Error: log_date {log_date!r} is {drift_days} days from today "
                    f"({date.today().isoformat()}) — refused as a likely hallucinated "
                    f"date rather than a real backdate. Use the date from your clock "
                    f"line, or omit log_date to default to today.")

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{log_date}.json"

    with _WRITE_LOG_LOCK:
        existing = {}
        if log_path.exists():
            with open(log_path) as f:
                existing = json.load(f)
        # Stamps carried from the file, then overwritten only for the paths THIS write
        # touches. An untouched field keeps the time it was actually asserted, which is the
        # whole point: on 2026-08-27 the 07:14 run resolved the Teams link and the 10:00 run
        # still called it missing, because a merged day-file has one date and no way to say
        # that one field in it was three hours old and another three minutes.
        stamps = dict(existing.get(_WRITTEN_AT_KEY) or {})
        origins = dict(existing.get(_WRITTEN_ON_KEY) or {})
        origin = _write_provenance()
        now_iso = datetime.now().isoformat(timespec="seconds")
        for path in _leaf_paths(content):
            stamps[path] = now_iso
            origins[path] = origin

        health_entries = _health_note_entries(content, now_iso)
        # By medicine name and ledger day — see _merge_medications.
        content = _merge_medications(existing, _stamp_medications(content), log_date)
        # By code-assigned id — see _merge_transactions. Before _deep_merge, whose list replace
        # then writes the merged list.
        content, tx_lines = _merge_transactions(existing, content, log_date)
        existing = _deep_merge(existing, content)
        if health_entries:
            feed = _append_health_notes(existing.get(_HEALTH_NOTES_KEY), health_entries)
            if feed != existing.get(_HEALTH_NOTES_KEY):
                existing[_HEALTH_NOTES_KEY] = feed
                stamps[_HEALTH_NOTES_KEY] = now_iso
                origins[_HEALTH_NOTES_KEY] = origin
        if intention_entry is not None:
            feed = existing.get(_INTENTIONS_KEY)
            if not isinstance(feed, list):
                feed = []          # a non-list here is corrupt, not a shape to preserve
            feed.append(intention_entry)
            existing[_INTENTIONS_KEY] = feed
            # One stamp for the feed, not per entry: the list is one growing assertion,
            # the same reading _leaf_paths already applies to every other list.
            stamps[_INTENTIONS_KEY] = now_iso
            origins[_INTENTIONS_KEY] = origin
        existing["date"] = log_date
        if stamps:
            existing[_WRITTEN_AT_KEY] = stamps
        if origins:
            existing[_WRITTEN_ON_KEY] = origins
        with open(log_path, "w") as f:
            json.dump(existing, f, indent=2)
        os.chmod(log_path, 0o600)

    # Embedding costs ~150-200ms on the VM and nothing reads its result, but it
    # ran inline here — inside tool dispatch, on the user's critical path.
    # Persona is resolved on THIS thread (so a failure still surfaces, and so
    # fail-closed behaviour is preserved) and re-bound inside the worker, which
    # has no thread-local identity of its own.
    _persona = resolve_persona()
    # The stamp map is excluded from what gets embedded: it is bookkeeping, and a block of
    # ISO timestamps in the indexed text is noise a semantic search has to see past.
    _payload = json.dumps({k: v for k, v in existing.items()
                           if k not in (_WRITTEN_AT_KEY, _WRITTEN_ON_KEY)})

    def _index() -> None:
        from core.memory import index_entry
        with persona_scope(_persona):
            index_entry(text=_payload, source="log", entry_date=log_date)

    run_background(_index, f"index log {log_date}")

    return (f"Log written to {log_path}"
            + (_medications_note(dropped_meds) if dropped_meds else "")
            + ("\n" + "\n".join(tx_lines) if tx_lines else ""))


def read_log(log_date: str = "") -> dict:
    """
    Read a daily log entry from data/logs/YYYY-MM-DD.json.

    Args:
        log_date: Date string in YYYY-MM-DD format. Defaults to today if empty.

    Returns:
        Log contents as a dictionary, or empty dict if no log exists.
    """
    if not log_date:
        log_date = date.today().isoformat()

    log_path = _logs_dir() / f"{log_date}.json"

    if not log_path.exists():
        return {}

    with open(log_path) as f:
        return json.load(f)


# Event types whose duplicates within one trace are DIFFERENT FACTS, not a
# double-write, so the same-trace dedup below is skipped for them.
#
# The dedup exists because one detected correction has two legitimate writers in
# the same request ([DB-0810-03]) — the same event twice. Build's events are the
# opposite shape: each carries its own BLD- job id, so two in a turn are two
# distinct tickets or two distinct failed landings, and collapsing them drops
# one entirely. A Coordinator filing two gaps in one turn recorded one; two jobs
# failing their checks in one tick recorded one, so the second capability's
# revert had no signal at all — in exactly the turn the redundant record was
# supposed to earn its keep.
_NEVER_DEDUPED: frozenset[str] = frozenset({"BUILD_PROPOSED", "BUILD_CHECK_FAILED"})


# [DB-0902-01] / Stage 2 #1 (D-S2-1 option 3, Mike 2026-11-23). These four types each CLAIM the
# user did something — corrected the system, asked for a change, asked for a feature, applied a
# fix themselves. On a turn that carries no words from the user (a scheduled brief or close, a
# weekly single-agent job) the turn itself proves they did not: the Coordinator commenting on the
# scheduler's own prompt was filed as ~56 USER_CORRECTION and ~155 ROUTING_MISS events, which
# buried the real ones in the backlog and in Build's three-strikes count. The four are refused
# there. ROUTING_MISS is kept — a specialist can genuinely be missed on a scheduled turn — but
# written with `"scheduled": true`, and both readers that count it skip tagged events
# (scripts/sync_dev_backlog.fetch_events, core/build/tick._count_faults). Code-written types
# (CONTEXT_BLOCK_UNPARSED, FALSE_ACTION_CLAIM, CHAIN_LIMIT_REACHED, ...) are untouched.
_NEEDS_USER_WORDS: frozenset[str] = frozenset({
    "USER_CORRECTION", "INSTRUCTION_CHANGE_REQUEST", "FEATURE_REQUEST", "SELF_APPLIED",
})


def _no_user_words() -> bool:
    """
    True when the current turn provably carries no words from the user.

    A bound turn (tools/turn_context) answers decisively: its `user_turn` is
    has_real_user_turn(). With no bound turn, a bound proactive trace (the weekly single-agent
    `run_session` jobs bind no turn) is a no-words turn. Neither bound — a script, a scheduler
    function job, core/server.py's /feedback tap (a real user action from an HTTP handler) — is
    NOT a no-words turn, as before. Never raises.
    """
    try:
        from tools.turn_context import current
        turn = current()
        if turn is not None:
            return not bool(turn.get("user_turn"))
        from core.trace import get_trace
        trace = get_trace()
        return bool(trace is not None and trace.is_proactive)
    except Exception:  # noqa: BLE001 — never block a quality event on the turn lookup
        return False


def write_quality_event(
    event_type: str,
    source_agent: str = "",
    detail: str = "",
    session_id: str = "",
) -> str:
    """
    Append a quality event to data/logs/quality_events.json (JSON Lines format).

    Args:
        event_type: ROUTING_MISS | USER_CORRECTION (or any future type)
        source_agent: Which agent emitted or missed the signal
        detail: Brief description of what was missed or corrected. Required in
            practice despite the empty default kept for signature compatibility —
            see the ValueError below.
        session_id: Any string identifying the current session (date/time or short ID)

    Raises:
        ValueError: if `detail` is blank **or null-ish**. A quality event with no
            detail cannot be attributed to anything downstream —
            `scripts/sync_dev_backlog.py` reads these into a human-facing backlog,
            and an empty entry there is worse than a missing one. A sample of
            USER_CORRECTION events found ~70% with `detail: None` before this guard
            existed (2026-08-10), all written by a caller that skipped the parameter
            the schema never required.

            **Widened 2026-08-15 from "blank" to "blank or null-ish", because the
            2026-08-10 guard did not hold.** A live count that day: 93 of 174
            USER_CORRECTION events still carried no information — but as the literal
            strings "None", "None.", "N/A", "[N/A - the user's message is a shift in
            intent, not a correction of a past error.]". Those are not blank, so they
            passed the guard, reached the backlog, and collapsed into a single
            `None. ×90` entry that became the loudest signature in Mike's
            session-start line, crowding out the real ones.

            **The cause is a template, not a careless caller.**
            `config/agents/coordinator.md:88` carries `USER_CORRECTION:` as a slot in
            a fixed output block, annotated "omit if not applicable" — and a model
            filling a structured template answers the slot rather than deleting it.
            That instruction is already correct and is already ignored, which is
            precisely why the control belongs here in Python and not in the agent
            file. Same class as the invented `ada@example.com` that `tools/crm.py`
            now refuses: **a field that looks required gets filled with something
            plausible rather than left out.**

    Returns:
        Confirmation string.
    """
    detail = (detail or "").strip()
    if not detail:
        raise ValueError(
            f"write_quality_event({event_type!r}): detail is required and cannot be "
            "blank — pass a real description of what happened, not the empty default."
        )
    if is_null_ish(detail):
        raise ValueError(
            f"write_quality_event({event_type!r}): detail {detail!r} carries no "
            "information — this is the 'no correction happened' case, so do not "
            "write an event at all. See is_null_ish()."
        )
    # [DB-0902-01] — see asserts_routing_success(). Refused rather than rewritten: the
    # caller is describing correct behaviour, so there is no event here to salvage, and
    # a rewritten detail would be this module inventing a fault nobody observed.
    if event_type == "ROUTING_MISS" and asserts_routing_success(detail):
        raise ValueError(
            f"write_quality_event(ROUTING_MISS): detail {detail!r} describes routing "
            "that WORKED. A ROUTING_MISS records a signal the routing missed — a "
            "specialist that should have been called and was not, or an intent read "
            "wrongly. Routing that went as intended is not an event: do not log "
            "anything. See asserts_routing_success()."
        )

    # Stage 2 #1 — see _NEEDS_USER_WORDS.
    scheduled = False
    if (event_type in _NEEDS_USER_WORDS or event_type == "ROUTING_MISS") and _no_user_words():
        if event_type == "ROUTING_MISS" and describes_scheduled_session(detail):
            raise ValueError(
                f"write_quality_event(ROUTING_MISS): detail {detail!r} only remarks that this "
                "session was opened by the scheduler. That is how a scheduled session works, "
                "not a routing miss — do not log it. Log a ROUTING_MISS here only for a "
                "specialist that should have been called and was not, naming it. See "
                "describes_scheduled_session()."
            )
        if event_type in _NEEDS_USER_WORDS:
            raise ValueError(
                f"write_quality_event({event_type!r}): this turn carries no words from the "
                "user, so there is nothing to have corrected or requested — do not log it."
            )
        scheduled = True

    logs_dir = _logs_dir()
    logs_dir.mkdir(parents=True, exist_ok=True)
    events_path = logs_dir / "quality_events.json"

    event = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "session_id": session_id,
        "event_type": event_type,
        "source_agent": source_agent,
        "detail": detail,
    }
    if scheduled:
        event["scheduled"] = True

    with _WRITE_QUALITY_EVENT_LOCK:
        # Dedup backstop ([DB-0810-03] grants ruling, 2026-08-28). The Coordinator can now
        # call this tool directly AND the program layer writes template-slot events from its
        # output, so one detected correction has two legitimate writers in the same request
        # — and the Synthesizer is a third for ROUTING_MISS. Same trace + same event type
        # → no-op. State lives on the RequestTrace instance, so it dies with the request;
        # a call outside any trace (tests, scripts, scheduler functions) is never deduped.
        from core.trace import get_trace
        trace = get_trace()
        if trace is not None and event_type not in _NEVER_DEDUPED:
            seen = getattr(trace, "_quality_event_types", None)
            if seen is None:
                seen = trace._quality_event_types = set()
            if event_type in seen:
                return (f"Quality event {event_type} already logged this turn — "
                        "duplicate skipped.")
            seen.add(event_type)

        with open(events_path, "a") as f:
            f.write(json.dumps(event) + "\n")
        os.chmod(events_path, 0o600)

    return f"Quality event logged: {event_type}"


# Tool schemas — registered with the Claude API in orchestrator.register_tools()

WRITE_LOG_SCHEMA = {
    "name": "write_log",
    "description": (
        "Save a daily log entry. Use this after a check-in to record how the day went. "
        "Merges with any existing entry for that date, including inside nested blocks, "
        "so writing twice in one day is safe.\n\n"
        "RECORD BOTH A COMPARABLE VALUE AND THE REAL WORDS. Days have to be rankable "
        "against each other or nothing can be read as a trend: 'anxious' and 'mixed' sit "
        "on no scale, while sleep hours do — which is why sleep ends up explaining "
        "everything. So put the coarse value in the field that has a fixed set, and the "
        "specific description in `notes` beside it. Never flatten the description away, "
        "and never invent a value the user did not give: if they said 'shattered', that is "
        "energy `low` plus notes 'shattered', not a number they never stated.\n\n"
        "LOG ONLY WHAT THE USER'S WORDS NAMED AS DONE. A vague report — 'sorted the "
        "finance stuff' — records those words, not your guess at which item they meant: "
        "never write 'X sorted', 'X paid' or X in `tasks_completed` unless the user named "
        "X. A logged guess reads later as fact, and on 2026-10-24 one decided which task "
        "got closed. Same for a plan: what the user means to do today is not done.\n\n"
        "Shape: `wellbeing` = {mood: low|neutral|positive|mixed, intensity: "
        "low|moderate|high, trajectory: rising|stable|declining|unclear, stress: "
        "low|moderate|high, notes: free text}. `health` = {sleep_hours: number, "
        "sleep_quality: good|fair|poor, energy: low|moderate|high, food_logged: bool, "
        "exercise: {type, duration_minutes, intensity_rpe}, symptoms, medical_notes}. "
        "Top level also takes `focus`, `blockers`, `wins`, `tasks_completed`, `notes`. "
        "Medication doses: a medication with a habit in the task ledger is recorded by marking "
        "that habit done, and its `health.medications_logged` entries are not stored; a "
        "medication with no habit is recorded here, in `health.medications_logged` "
        "[{name (as the medication profile gives it), taken: bool, notes}]. "
        "Your own agent file's `## Data written` section is authoritative for your domain."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "log_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
            "content": {
                "type": "object",
                "description": (
                    "Log fields to record, in the shape described above — domain values "
                    "inside their `wellbeing` / `health` block, using the fixed vocabulary, "
                    "with the specific wording in the `notes` beside them. Top level takes "
                    "focus, blockers, wins, tasks_completed, notes. " + RELATIVE_REFERENCES
                ),
                "additionalProperties": True,
            },
        },
        "required": ["content"],
    },
}

READ_LOG_SCHEMA = {
    "name": "read_log",
    "description": "Read a daily log entry for a given date.",
    "input_schema": {
        "type": "object",
        "properties": {
            "log_date": {
                "type": "string",
                "description": "Date in YYYY-MM-DD format. Leave empty for today.",
            },
        },
        "required": [],
    },
}

WRITE_QUALITY_EVENT_SCHEMA = {
    "name": "write_quality_event",
    "description": (
        "Log a quality event for the self-improvement protocol. "
        "Use event_type ROUTING_MISS when the original message carried a signal no specialist surfaced. "
        "Use event_type USER_CORRECTION when the user re-states or corrects a prior turn. "
        "`detail` is required and rejected if blank — a quality event nobody can read back is worse "
        "than no event at all."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "event_type": {
                "type": "string",
                "description": "ROUTING_MISS or USER_CORRECTION",
            },
            "source_agent": {
                "type": "string",
                "description": "Which agent emitted or missed the signal (e.g. 'synthesizer', 'mental_wellbeing')",
            },
            "detail": {
                "type": "string",
                "description": (
                    "What actually happened, specifically — for a USER_CORRECTION, name what was "
                    "wrong and what the user said instead, not just 'user corrected something'. "
                    "Required — the call is rejected if this is blank."
                ),
            },
            "session_id": {
                "type": "string",
                "description": "Any string identifying this session — use the date/time or a short ID",
            },
        },
        "required": ["event_type", "detail"],
    },
}
