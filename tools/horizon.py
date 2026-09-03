"""
tools/horizon.py — a horizon finding is put to the user once, and only once.

`[DB-0822-09]`. On 2026-09-02 the `logistics` specialist did its job exactly right: it read
the inbox, judged a Death Cab for Cutie ticket confirmation to be worth Mike's attention, and
attached the coordination legs (travel, transit, pre-show dining near Troxy). It emitted all
of that as `HORIZON_ITEMS` in a 536-token package. The Synthesizer received 21,630 input
tokens including that package and replied with 177: *"Your focus window remains clear for the
Apex migration delivery, Mike."* The item never reached him, in any run, that day.

That is the second instruction-side fix for this behaviour to ship and not fire, so the report
moves out of the model's discretion — the same reasoning `enforce_pending_receipt` records.

**WHAT THIS MODULE DOES NOT DO: decide what is interesting.** That judgement is made upstream
by `logistics`, which reads the mail and knows the calendar, and it stays there. Measured
across the three runs where specialist output survives in the traces (2026-08-29, 08-30,
09-02), that judgement is sound: eight findings, zero junk. This module only answers a
question code *can* answer — **has the user already been told this?** — and that answer is
what makes guaranteed delivery safe rather than a daily false alarm.

**Why the ledger is load-bearing rather than a refinement.** The same three runs:

    08-29 10:31   dental · Jimmy Carr · George School socials
    08-30 20:46   dental · Jimmy Carr
    09-02 11:37   Jimmy Carr · Death Cab · George School London

Jimmy Carr appears in all three; the dental appointment in two. Delivering horizon items
without a record of what was already said would have told Mike about the same comedy show
every day until 13 September — turning a silent drop into a groundhog day, which is the
`[DB-0822-06]` carried-state failure through a new channel and strictly worse than the bug it
replaces. The Synthesizer's dropping was doing double duty: it was the fault *and* the noise
filter. Removing the fault means supplying the filter deliberately.

**Identity, not similarity.** Two findings are the same finding when they share a date and a
venue. That is a key comparison, not a semantic judgement — deliberately so, because the
adjacent `[DB-0827-07]` was closed to keep guessing of that kind out of this codebase. Prose
could not support it: across the three runs the same show was written *"Jimmy Carr
Performance: September 13th at 9:30 PM at The London Palladium"* and *"Jimmy Carr: Laughs
Funny at The London Palladium — Sunday, September 13, 2026 at 9:30 PM"*, which no title match
survives. `logistics.md` now emits the fields separately for exactly this reason.

**Discharge.** An item is offered until the user engages with it or `_MAX_OFFERS` sessions have
carried it, whichever comes first. One offer would reproduce the original bug the first time a
Synthesizer dropped it; unlimited offers would reproduce the repetition above. Engagement is
`tools/context_tracker._user_engages_thread`, the content-word overlap already used to keep an
open thread alive when the user's own turn touches it.
"""

from __future__ import annotations

import json
import logging
import re
import threading
from datetime import date, datetime
from pathlib import Path

from core.persona import persona_data_dir, resolve_persona

logger = logging.getLogger(__name__)

_LOCK = threading.Lock()

# How many sessions may carry an undelivered finding before it is written off. Two, not one,
# because a single offer is what the Synthesizer already failed at on 09-02; and not more,
# because the whole hazard this module exists to bound is repetition. A finding still unsaid
# after two sessions is one the model has judged not worth the room twice, and pressing it a
# third time is nagging.
_MAX_OFFERS = 2

# Both head-layer agents load context inside one exchange; this collapses those two reads
# into a single offer. Longer than a session, shorter than the gap between two.
_OFFER_WINDOW_SECONDS = 300

# Findings whose date has passed are dropped rather than delivered (see `_is_past`): telling
# the user about a concert the morning after it happened is the staleness this system keeps
# failing at. `kind` is carried for the model's benefit and deliberately not validated — an
# unrecognised value is not worth discarding a real finding over.

# Punctuation and case vary run to run ("The London Palladium" / "the london palladium,
# London"); the leading article does too. Normalised for the key only — the stored text the
# user sees is never rewritten.
_NON_WORD_RE = re.compile(r"[^a-z0-9]+")
_LEADING_ARTICLE_RE = re.compile(r"^(the|a|an)\s+")


def _store_path(persona: str | None = None) -> Path:
    directory = persona_data_dir(persona) / "horizon"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / "ledger.json"


def _read(persona: str | None = None) -> dict:
    path = _store_path(persona)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[horizon] ledger unreadable, starting empty: {exc}")
        return {}


def _write(data: dict, persona: str | None = None) -> None:
    path = _store_path(persona)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False))
    tmp.replace(path)


def _norm(text: str) -> str:
    """Normalise to a sorted set of content tokens.

    A **set**, not a string, and that is what makes the key survive real data. The same venue
    was written "The London Palladium" by one run and "the london palladium, London" by
    another; as strings those differ, as token sets they are both {london, palladium}. A
    trailing city qualifier, a repeated word and a stray comma all vanish, while genuinely
    different venues stay different — {troxy, london} is not {london}, so a finding at Troxy
    is never merged with one that says only "London".
    """
    lowered = (text or "").strip().lower()
    lowered = _LEADING_ARTICLE_RE.sub("", lowered)
    tokens = {t for t in _NON_WORD_RE.sub(" ", lowered).split() if t}
    return " ".join(sorted(tokens))


def item_key(item: dict) -> str:
    """The identity of a finding: its date and its venue.

    Falls back to the title only when there is no venue — an undated, unvenued finding has
    nothing stable to key on, and two of those with the same title are the same finding by
    the only evidence available. Never falls back to `detail`, which is the sentence most
    likely to be rewritten between runs.
    """
    date_part = _norm(str(item.get("date") or ""))
    venue_part = _norm(str(item.get("venue") or ""))
    anchor = venue_part or _norm(str(item.get("title") or ""))
    return f"{date_part}|{anchor}"


def _valid(item) -> bool:
    """A finding the ledger can hold. Rejects rather than repairs: a malformed item is the
    specialist's output to fix, and silently coercing one would put an invented date into a
    record whose whole purpose is being trustworthy about dates."""
    if not isinstance(item, dict):
        return False
    if not str(item.get("title") or "").strip():
        return False
    raw_date = str(item.get("date") or "").strip()
    if raw_date:
        try:
            date.fromisoformat(raw_date)
        except ValueError:
            return False
    return item_key(item).strip(" |") != ""


def _is_past(item: dict, today: date | None = None) -> bool:
    raw = str(item.get("date") or "").strip()
    if not raw:
        return False
    try:
        return date.fromisoformat(raw) < (today or date.today())
    except ValueError:
        return False


def record(items: list, persona: str | None = None) -> dict:
    """File this run's findings. Returns {"new": n, "known": n, "invalid": n}.

    A finding already in the ledger is *not* reset — that is the entire point. Its stored
    text is refreshed, because a later run's wording usually carries more detail (the 09-02
    Death Cab entry gained its ticket provenance), but its offer count and delivery state
    carry forward untouched.
    """
    tally = {"new": 0, "known": 0, "invalid": 0}
    if not items:
        return tally

    persona = resolve_persona(persona)
    now = datetime.now().isoformat(timespec="seconds")
    with _LOCK:
        data = _read(persona)
        for item in items:
            if not _valid(item):
                tally["invalid"] += 1
                continue
            if _is_past(item):
                # Not counted as new: there is nothing to tell the user about a date that
                # has gone by, and filing it would only give it two offers it cannot use.
                tally["known"] += 1
                continue
            key = item_key(item)
            existing = data.get(key)
            if existing:
                existing["item"] = item
                existing["last_seen"] = now
                tally["known"] += 1
            else:
                data[key] = {
                    "item": item,
                    "first_seen": now,
                    "last_seen": now,
                    "offers": 0,
                    "delivered_at": None,
                }
                tally["new"] += 1
        _write(data, persona)
    return tally


def _undelivered(data: dict, today: date | None = None) -> list[tuple[str, dict]]:
    rows = []
    for key, row in data.items():
        if row.get("delivered_at"):
            continue
        if (row.get("offers") or 0) >= _MAX_OFFERS:
            continue
        item = row.get("item") or {}
        if _is_past(item, today):
            continue
        rows.append((key, row))
    # Soonest first: a thing happening this week matters more than one in October.
    rows.sort(key=lambda kv: (str((kv[1].get("item") or {}).get("date") or "9999-12-31"),
                              kv[0]))
    return rows


def context_block(persona: str | None = None) -> str:
    """The head layer's horizon block. "" when nothing is waiting.

    Registered in `core/orchestrator.load_recent_context()` alongside obligations, confirm,
    intake and the rest. Like `crm_sweep`'s, it carries its own delivery instruction rather
    than relying on one in `synthesizer.md`: that file is 44KB, its own audit named
    length-versus-adherence as the failure mode, and the rule this replaces was added on
    2026-08-29 and did not fire on its first live test.

    **An offer is counted here, when the item is actually served, and nowhere else.** The
    obvious alternative — counting once per turn from the pipeline's close-out — silently
    burns a chance: a finding is filed by `logistics` partway through the turn, long after
    this block was built, so it would be charged for an offer the user never saw. Counting at
    the point of service cannot make that mistake. The window collapses the two head-layer
    reads of one session (coordinator and synthesizer both load context) into a single offer.
    """
    try:
        persona = resolve_persona(persona)
        with _LOCK:
            data = _read(persona)
            rows = _undelivered(data)
            if rows and _charge_offers(data, [key for key, _ in rows]):
                _write(data, persona)
        if not rows:
            return ""

        lines = []
        for _key, row in rows:
            item = row.get("item") or {}
            when = str(item.get("date") or "").strip() or "no date"
            where = str(item.get("venue") or "").strip()
            detail = str(item.get("detail") or "").strip()
            lines.append(
                f"- {item.get('title')} — {when}"
                + (f", {where}" if where else "")
                + (f". {detail}" if detail else ""))

        return (
            "[HORIZON — findings the user has NOT yet been told about. Each has been checked "
            "against a record of what has already been raised, so nothing here is a repeat "
            "and none of it needs hedging as 'you may already know'. Put these to the user "
            "in this exchange, in your own voice and wherever they sit naturally — one line "
            "each is usually enough, and the detail is there if they pick it up. Judge the "
            "placement and the wording; do not judge whether to mention them. Never present "
            "this as a list you were handed.]\n" + "\n".join(lines))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[horizon] context block failed: {exc}")
        return ""


def _charge_offers(data: dict, keys: list[str], now: datetime | None = None) -> bool:
    """Count one offer against each key, unless it was already counted this session.

    Returns True when anything changed. The window exists because `context_block()` runs once
    for the Coordinator and again for the Synthesizer inside a single exchange; charging both
    would halve every finding's real chances. Anything longer than a session and shorter than
    the gap between them works — the failure direction of too long is *more* chances, which is
    the safe one.
    """
    now = now or datetime.now()
    changed = False
    for key in keys:
        row = data.get(key)
        if row is None:
            continue
        last = row.get("last_offered_at")
        if last:
            try:
                if (now - datetime.fromisoformat(last)).total_seconds() < _OFFER_WINDOW_SECONDS:
                    continue
            except (TypeError, ValueError):
                pass
        row["offers"] = (row.get("offers") or 0) + 1
        row["last_offered_at"] = now.isoformat(timespec="seconds")
        changed = True
    return changed


def mark_engaged(user_text: str | None, persona: str | None = None) -> int:
    """Discharge every finding the user's own turn engages with. Returns how many.

    `user_text` must come from the user's message and never from anything the system
    generated — the same origin guarantee `_user_engages_thread` is documented under, and the
    reason the scheduler's own check-in prompt cannot silently discharge a finding it happens
    to word similarly.
    """
    if not user_text:
        return 0
    try:
        from tools.context_tracker import _user_engages_thread

        persona = resolve_persona(persona)
        now = datetime.now().isoformat(timespec="seconds")
        with _LOCK:
            data = _read(persona)
            hit = 0
            for key, row in data.items():
                if row.get("delivered_at"):
                    continue
                item = row.get("item") or {}
                text = " ".join(str(item.get(f) or "") for f in ("title", "venue", "detail"))
                if _user_engages_thread(text, user_text):
                    row["delivered_at"] = now
                    hit += 1
            if hit:
                _write(data, persona)
            return hit
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[horizon] mark_engaged failed: {exc}")
        return 0


# ---------------------------------------------------------------------------
# The tool — how findings actually arrive
# ---------------------------------------------------------------------------
#
# Live-tested 2026-09-03, after the template-slot version deployed: `logistics` emitted no
# `HORIZON_ITEMS:` line at all — not malformed, absent — returning conversational markdown
# with none of its documented output format, no `ACTIONS TAKEN:` and no `FLAGS:` either. The
# same agent on the same model had emitted the full structured block the day before. Output
# format adherence varies run to run, so a template slot is not a channel: it is a request.
#
# A tool call is structured by construction. It cannot be quietly replaced by prose, its
# arguments cannot be malformed and silently ignored, and a refusal is visible. That is
# already this codebase's answer wherever a relay must not be lost — `write_quality_event`,
# `open_obligation` — and it is what `.claude/rules/agent-files.md` means by a named tool
# being a specification rather than a suggestion.
#
# The prose parser in core/orchestrator.py is kept as a second channel rather than removed:
# it costs one substring check per specialist output, and a run that does emit the block
# should not have its findings dropped for using the older route. Both land in the same
# ledger, and `record()` dedupes by key, so a finding arriving twice is filed once.


def record_horizon_item(title: str, date: str = "", venue: str = "",
                        kind: str = "", detail: str = "") -> str:
    """File one horizon finding. Called by the specialist, once per finding.

    Deliberately one call per item rather than a list: a model that has to assemble a JSON
    array is back to emitting a structure it can get wrong, which is the failure this tool
    exists to route around. Repeating a small call is the reliable shape.
    """
    item = {"title": title, "date": date, "venue": venue, "kind": kind, "detail": detail}
    if not _valid(item):
        # Stated plainly so the model can correct itself on the next call. `date` is the
        # field that goes wrong, and it must never be guessed at on the model's behalf —
        # the whole ledger turns on it being real.
        return ("Not filed: a horizon item needs a non-empty `title`, and `date` must be "
                "YYYY-MM-DD or empty — never a phrase like 'next Tuesday'. Nothing was "
                "recorded; call again with the corrected fields.")
    if _is_past(item):
        return (f"Not filed: {date} has already passed, so there is nothing to warn the "
                f"user about. This is not an error.")

    tally = record([item])
    if tally["new"]:
        return f"Filed: {title}. The user has not been told about this one yet."
    return (f"Already on file: {title}. It has been recorded before, so it will not be "
            f"raised with the user again. Nothing further is needed.")


RECORD_HORIZON_ITEM_SCHEMA = {
    "name": "record_horizon_item",
    "description": (
        "File one upcoming thing the user should be told about — an event, appointment, "
        "booking, deadline, errand or opportunity you found while scanning. Call it once "
        "per finding, as you find them. The system tracks which findings the user has "
        "already been told about and raises each one exactly once, so call this for "
        "everything you judge worth their attention and never skip an item because it "
        "might have been mentioned before — that check is not yours to make. Filing is "
        "not telling: what reaches the user is decided downstream."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "What it is, in the user's terms. No reference numbers or ids.",
            },
            "date": {
                "type": "string",
                "description": (
                    "The date the thing happens, as YYYY-MM-DD. Use the start date for a "
                    "range. Leave empty if it genuinely has no date — never invent one and "
                    "never write a phrase like 'next Tuesday'."
                ),
            },
            "venue": {
                "type": "string",
                "description": (
                    "Where it happens, if anywhere — a venue or place name. Leave empty "
                    "otherwise. Together with the date this is what identifies the finding, "
                    "so give the venue as plainly as you can."
                ),
            },
            "kind": {
                "type": "string",
                "description": ("One of: event, appointment, booking, deadline, errand, "
                                "opportunity."),
            },
            "detail": {
                "type": "string",
                "description": (
                    "One sentence on what makes this worth the user's attention, including "
                    "anything a coordination check turned up. This is the part they hear."
                ),
            },
        },
        "required": ["title"],
    },
}
