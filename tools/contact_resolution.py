"""
tools/contact_resolution.py — the people a Relationships dispatch names, matched EXACTLY to the
user's contacts by code, plus who is overdue and whose dates are coming up (instructions-to-code
Stage 4, 4c: #12, M2, M3) and the "newly saved — read it back" line for the Synthesizer (M1).

Plan: archive/plans/instructions_to_code_stage4_evidence_plan_2026-11-23.md § 1 #12 and M1, as
revised (review L8). Read by core/prefetch.py (the `people` read) and by the pipeline twins in
core/orchestrator.py (M1). Never a tool, never in a schema.

What a user notices: mention someone you know and the Relationships specialist starts from their
actual record instead of searching for them, and a new phone number or email you dictate is read
back to you in the reply, so a misheard detail is caught before it sits in the contact book.

The rules, each tested in tests/test_contact_resolution.py:

1. **Exact only.** Two consecutive words, any case, any position, that are a contact's first +
   last name, a multi-word name, or a multi-word `referred_to_as` phrase ("my brother"). A single
   word only when it is capitalised and not starting a sentence — the `tools/heard_names`
   rule, reused, not copied — and only against `first_name`, `nickname`, a one-word `name` or a
   one-word `referred_to_as`. **Never `last_name` alone:** a shared surname is not a person.
2. **Never a pick, never a merge, never a new contact.** A word that reaches two people uses the
   user's remembered answer (`crm._apply_resolution`) or is listed as "matches N contacts — ask
   which". A near-match (a nickname prefix) is listed as "possibly …" and never resolved: sounds
   and spellings stay the model's judgement and `write_contact`'s own evidence.
3. **Stored tone shape only (M2).** `get_tone_shape` is never called from here — with no profile
   it starts a background mailbox sweep and a model call, so prefetching it would seed a profile
   for every name mentioned. Without a current `tone_profile` consent nothing about tone is said.
4. **Read only.** Nothing here writes a contact, a resolution or anything else.

Cost: loading contacts.json once per Relationships dispatch (~50 ms at ~1k contacts); the block
is ≈0.5–3k tokens in the specialist's user message. Nothing persists between requests — the M1
snapshot lives on the request trace and dies with it.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import date, timedelta

logger = logging.getLogger(__name__)

MAX_PEOPLE = 3            # resolved records handed over
MAX_ASK_WHICH = 5         # disambiguation rows per ambiguous word
MAX_PREFIX = 3            # "possibly …" lines
MAX_OVERDUE = 8
MAX_UPCOMING = 8
NOTES_CHARS = 300
RECENT_INTERACTIONS = 3
DEFAULT_UPCOMING_DAYS = 14

_POSSESSIVE_RE = re.compile(r"'s$", re.IGNORECASE)

# First names that are also ordinary English words. A lone one of these is never enough to say a
# piece of text is ABOUT a person (tools/recipient_context.py): "I will", "mark the date", "a rose
# bush", "may be late". Resolution itself does not need it — it already requires a capital that
# is not starting a sentence — but free text such as a stored fact or a past entry has no such
# guarantee. Shared here so both modules use one list.
COMMON_WORD_NAMES = frozenset({
    "will", "mark", "rose", "bill", "may", "june", "april", "august", "grace", "hope", "faith",
    "joy", "amber", "ruby", "pearl", "holly", "ivy", "lily", "iris", "daisy", "dawn", "summer",
    "autumn", "winter", "sky", "rain", "storm", "sunny", "sandy", "penny", "pat", "frank",
    "rich", "sue", "don", "art", "jack", "bob", "gene", "ray", "rob", "chase", "hunter", "max",
    "guy", "victor", "drew", "lane", "dale", "glen", "cliff", "brook", "heath", "faye", "major",
    "earl", "duke", "king", "prince", "reed", "rusty", "red", "nick", "sly", "wade", "miles",
    "page", "carol", "harmony", "melody", "honey", "candy", "cherry", "ginger", "jasmine",
    "violet", "hazel", "olive", "sage", "jade", "crystal", "destiny", "patience", "trinity",
})


# --- the words a contact answers to -----------------------------------------------------------

def _words(value) -> list[str]:
    from tools.heard_names import _TOKEN_RE
    return [_POSSESSIVE_RE.sub("", w).strip("'-").lower()
            for w in _TOKEN_RE.findall(str(value or ""))]


def _phrases(c: dict) -> set[tuple[str, ...]]:
    """The multi-word keys a contact answers to, in any case and any position."""
    out: set[tuple[str, ...]] = set()
    first, last = _words(c.get("first_name")), _words(c.get("last_name"))
    if first and last:
        out.add(tuple(first + last))
    name = _words(c.get("name"))
    if len(name) >= 2:
        out.add(tuple(name))
    for ref in c.get("referred_to_as") or []:
        w = _words(ref)
        if len(w) >= 2:
            out.add(tuple(w))
    return {p for p in out if all(p)}


def first_word(c: dict) -> str:
    """The first name a contact goes by: `first_name`, else the first token of a multi-word
    `name` (a record saved as "Sam Hale" with no first_name is a Sam for ambiguity too)."""
    w = _words(c.get("first_name"))
    if len(w) == 1:
        return w[0]
    if w:
        return w[0]
    name = _words(c.get("name"))
    return name[0] if name else ""


def _singles(c: dict) -> set[str]:
    """The one-word keys a contact answers to. Never `last_name` (rule 1)."""
    out: set[str] = set()
    first = first_word(c)
    if first:
        out.add(first)
    w = _words(c.get("nickname"))
    if len(w) == 1:
        out.add(w[0])
    for value in [c.get("name")] + list(c.get("referred_to_as") or []):
        w = _words(value)
        if len(w) == 1:
            out.add(w[0])
    return {w for w in out if w}


def _archived_survivors(contacts: list[dict]) -> list[tuple[dict, dict]]:
    """(merged-away record, the live record it survives as) — so a name corrected away by a
    merge still reaches the person (follows `merged_into`, chained merges included)."""
    from tools import crm as CRM
    out: list[tuple[dict, dict]] = []
    try:
        archive = CRM._crm_archive_dir()
        if not archive.exists():
            return out
        for path in sorted(archive.glob("*.json")):
            if path.name.startswith("premerge_"):
                continue
            try:
                rec = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict) or not rec.get("merged_into") or not rec.get("id"):
                continue
            survivor = CRM._resolve_merged(contacts, str(rec["id"]))
            if survivor is not None:
                out.append((rec, survivor))
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[contact_resolution] archive not read: {exc}")
    return out


def _index(contacts: list[dict], cache: dict | None = None) -> tuple[dict, dict]:
    """key → [live contacts]. A merged-away record's keys are added only where no live contact
    carries the same key, pointing at its survivor. `cache` (the request's) memoises the archive
    scan, so a second build in one request does not re-read every archived record."""
    phrases: dict[tuple, list[dict]] = {}
    singles: dict[str, list[dict]] = {}

    def add(table, key, c):
        bucket = table.setdefault(key, [])
        if all(x.get("id") != c.get("id") for x in bucket):
            bucket.append(c)

    for c in contacts:
        for p in _phrases(c):
            add(phrases, p, c)
        for w in _singles(c):
            add(singles, w, c)
    live_p, live_s = set(phrases), set(singles)
    archived = None
    key = None
    if cache is not None:
        from core.persona import current_persona
        key = ("contact_resolution.archived", current_persona(), len(contacts))
        archived = cache.get(key)
    if archived is None:
        archived = _archived_survivors(contacts)
        if cache is not None:
            cache[key] = archived
    for rec, survivor in archived:
        for p in _phrases(rec):
            if p not in live_p:
                add(phrases, p, survivor)
        for w in _singles(rec):
            if w not in live_s:
                add(singles, w, survivor)
    return phrases, singles


# --- resolution -------------------------------------------------------------------------------

def _two_token_hits(text: str, phrases: dict) -> tuple[list[tuple[str, list[dict]]], list]:
    """(phrase as written, matches) for every multi-word key in `text`, longest first at each
    position; and the character spans they cover."""
    from tools.heard_names import _TOKEN_RE
    if not phrases:
        return [], []
    toks = [(m.start(), m.end(), _POSSESSIVE_RE.sub("", m.group(0)).strip("'-").lower())
            for m in _TOKEN_RE.finditer(text or "")]
    # A phrase never runs across punctuation: "Sam, Lee and Jo" names nobody called Sam Lee.
    joined = [bool(re.fullmatch(r"[ \t]+", text[toks[j][1]:toks[j + 1][0]]))
              for j in range(len(toks) - 1)]
    lengths = sorted({len(p) for p in phrases}, reverse=True)
    hits, spans, i = [], [], 0
    while i < len(toks):
        for n in lengths:
            if i + n > len(toks) or not all(joined[i:i + n - 1]):
                continue
            key = tuple(t[2] for t in toks[i:i + n])
            if key in phrases:
                start, end = toks[i][0], toks[i + n - 1][1]
                hits.append((text[start:end], phrases[key]))
                spans.append((start, end))
                i += n
                break
        else:
            i += 1
    return hits, spans


def _uncovered(word: str, text: str, spans: list) -> bool:
    """Does `word` occur in `text` at least once outside the two-token matches?"""
    return bool(_occurrences(word, text, spans))


def _occurrences(word: str, text: str, spans: list) -> list[tuple[int, int]]:
    return [(m.start(), m.end())
            for m in re.finditer(rf"(?<![A-Za-z']){re.escape(word)}(?![A-Za-z])", text)
            if not any(s <= m.start() < e for s, e in spans)]


def _sentence_initial(text: str, start: int) -> bool:
    from tools.heard_names import _ABBREV_BEFORE_RE, _BREAK_WINDOW, _SENTENCE_BREAK_RE
    if not text[:start].strip(" \"'([\t"):
        return True
    before = text[max(0, start - _BREAK_WINDOW):start]
    return bool(_SENTENCE_BREAK_RE.search(before) and not _ABBREV_BEFORE_RE.search(before))


def _foreign_neighbour(text: str, start: int, end: int, own: set[str]) -> str:
    """The name as written with the capitalised word right beside [start, end) — spaces only
    between — when that word is NOT on the matched contact's record; else "". "lunch with Sam
    Peters" when Sam Hale is the contact: "Peters" is somebody else's surname, so "Sam" there is
    not known to be Sam Hale. A sentence-initial neighbour ("Yesterday Sam called") and a known
    non-name are not names."""
    from tools.heard_names import _NOT_NAMES
    word = text[start:end]
    after = re.match(r"[ \t]+([A-Za-z][A-Za-z'\-]*)", text[end:])
    if after:
        w = _POSSESSIVE_RE.sub("", after.group(1)).strip("'-")
        if w[:1].isupper() and w.lower() not in own and w.lower() not in _NOT_NAMES:
            return f"{word} {w}"
    m = re.search(r"([A-Za-z][A-Za-z'\-]*)[ \t]+$", text[:start])
    if m:
        w = _POSSESSIVE_RE.sub("", m.group(1)).strip("'-")
        if (w[:1].isupper() and w.lower() not in own and w.lower() not in _NOT_NAMES
                and not _sentence_initial(text, m.start(1))):
            return f"{w} {word}"
    return ""


def _implied_only(c: dict, word: str) -> bool:
    """`word` reaches this contact only as the first token of a name with no first_name ("City
    Dental"): it counts toward "which one?", but never resolves alone ("the City council")."""
    if _words(c.get("first_name")):
        return False
    explicit = set(_words(c.get("nickname"))[:1])
    for value in [c.get("name")] + list(c.get("referred_to_as") or []):
        w = _words(value)
        if len(w) == 1:
            explicit.add(w[0])
    return word not in explicit and word == first_word(c)


def resolve(texts: list[str], contacts: list[dict] | None = None,
            cache: dict | None = None) -> dict:
    """Who the texts name, exactly. Returns
    {"resolved": [contact, …] (first-named first, unique by id),
     "ambiguous": [(word, [contact, …]), …],
     "prefix": [(word, contact), …],
     "possibly": [(as written, contact), …]}  — a single name beside someone else's name, or a
    name-only record's first word: never resolved, offered for the model to check.
    Never writes; never raises (an unreadable store resolves nobody)."""
    from tools import crm as CRM
    from tools.heard_names import _candidates, _contact_words, _known_words
    out = {"resolved": [], "ambiguous": [], "prefix": [], "possibly": []}
    try:
        contacts = CRM._load_contacts() if contacts is None else contacts
        if not contacts:
            return out
        phrases, singles = _index(contacts, cache)
        known = _known_words(contacts)
        seen_ids: set[str] = set()
        seen_keys: set[str] = set()

        def settle(word: str, matches: list[dict]) -> None:
            key = CRM._normalize_reference(word)
            if key in seen_keys:
                return
            seen_keys.add(key)
            if len(matches) > 1:
                remembered = CRM._apply_resolution(contacts, word, matches)
                if remembered is None:
                    out["ambiguous"].append((word, matches))
                    return
                matches = [remembered]
            c = matches[0]
            if c.get("id") not in seen_ids:
                seen_ids.add(c.get("id"))
                out["resolved"].append(c)

        prefix_seen: set[str] = set()
        for text in texts:
            text = str(text or "")
            if not text.strip():
                continue
            hits, spans = _two_token_hits(text, phrases)
            for written, matches in hits:
                settle(written, matches)
            for word in _candidates(text):
                low = word.lower()
                if not _uncovered(word, text, spans):
                    continue
                if low in singles:
                    matches = singles[low]
                    # Item 1 (review of 1c6f39d): a lone name beside another capitalised name
                    # that is not on the same record is somebody else — "Sam Peters", "Michael
                    # Jordan". Resolved only from an occurrence with no such neighbour.
                    own = set()
                    for c in matches:
                        own |= _contact_words(c)
                    clean, beside = False, ""
                    for start, end in _occurrences(word, text, spans):
                        other = _foreign_neighbour(text, start, end, own)
                        if not other:
                            clean = True
                            break
                        beside = beside or other
                    if not clean or all(_implied_only(c, low) for c in matches):
                        for c in matches[:MAX_PREFIX]:
                            if len(out["possibly"]) < MAX_PREFIX and \
                                    all(x[1].get("id") != c.get("id") for x in out["possibly"]):
                                out["possibly"].append((beside or word, c))
                        continue
                    settle(word, matches)
                    continue
                # Rule 2: a prefix of a contact's first name is offered, never resolved.
                if (low in known or low in prefix_seen or len(low) < CRM._MIN_PREFIX_LEN
                        or len(out["prefix"]) >= MAX_PREFIX):
                    continue
                for c in contacts:
                    first = first_word(c)
                    if len(first) > len(low) and first.startswith(low):
                        prefix_seen.add(low)
                        out["prefix"].append((word, c))
                        if len(out["prefix"]) >= MAX_PREFIX:
                            break
        # A person both resolved and offered as a prefix is not offered.
        out["prefix"] = [(w, c) for w, c in out["prefix"] if c.get("id") not in seen_ids]
        out["possibly"] = [(w, c) for w, c in out["possibly"] if c.get("id") not in seen_ids]
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[contact_resolution] nobody resolved: {exc}")
    return out


# --- what is handed over ----------------------------------------------------------------------

def _display(c: dict) -> str:
    return str(c.get("name") or " ".join(x for x in (c.get("first_name"), c.get("last_name"))
                                         if x) or c.get("nickname") or c.get("id") or "?")


def project(contact: dict, permitted: bool) -> dict:
    """The compact record handed over for one resolved person — never the full interaction log.
    Passed through `crm._gate_tone_shape`; the stored tone shape only, never fetched (M2)."""
    from tools import crm as CRM
    c = CRM._gate_tone_shape(contact, permitted)
    out = {k: c[k] for k in ("id", "name", "first_name", "last_name", "nickname",
                             "relationship_type", "relationship_quality", "last_contact",
                             "contact_frequency_preference", "important_dates", "contact_info")
           if c.get(k)}
    notes = str(c.get("notes") or "").strip()
    if notes:
        out["notes"] = notes[:NOTES_CHARS] + ("…" if len(notes) > NOTES_CHARS else "")
    log = [e for e in (c.get("interaction_log") or []) if isinstance(e, dict)]
    if log:
        out["recent_interactions"] = log[-RECENT_INTERACTIONS:]
    if permitted:
        shape = str(c.get("tone_shape") or "").strip()
        out["tone_shape"] = shape if shape else (
            "none stored; call `get_tone_shape` before drafting to them")
    return out


def overdue_lines(today: date) -> list[str]:
    """`list_contacts(overdue_only=True)`'s selection, most overdue first, capped."""
    from tools import crm as CRM
    rows = json.loads(CRM.list_contacts(overdue_only=True))
    dated, never = [], []
    for c in rows:
        freq = str(c.get("contact_frequency_preference") or "")
        days = CRM._FREQUENCY_DAYS.get(freq)
        last = str(c.get("last_contact") or "")
        try:
            due = date.fromisoformat(last) + timedelta(days=days or 0)
        except ValueError:
            never.append(f"- {_display(c)} · {c.get('id')} · never contacted · {freq}")
            continue
        past = (today - due).days
        if past > 0:
            dated.append((past, f"- {_display(c)} · {c.get('id')} · {last} · "
                                f"{past} days past {freq}"))
    lines = [t for _, t in sorted(dated, key=lambda x: -x[0])] + never
    extra = len(lines) - MAX_OVERDUE
    lines = lines[:MAX_OVERDUE]
    if extra > 0:
        lines.append(f"- (+{extra} more — `list_contacts(overdue_only=true)`)")
    return lines


def _next_occurrence(raw: str, today: date) -> date | None:
    """The next date on/after `today` an important date falls, from MM-DD or YYYY-MM-DD. 29 Feb
    falls on 28 Feb in a non-leap year. A YYYY-MM-DD whose first occurrence is still ahead of
    the occurrence found is not yet due (None)."""
    m = re.fullmatch(r"(?:(\d{4})-)?(\d{1,2})-(\d{1,2})", str(raw or "").strip())
    if not m:
        return None
    year, month, day = (int(m.group(1)) if m.group(1) else None), int(m.group(2)), int(m.group(3))
    for y in (today.year, today.year + 1):
        try:
            d = date(y, month, day)
        except ValueError:
            if month == 2 and day == 29:
                d = date(y, 2, 28)
            else:
                return None
        if d >= today:
            if year is not None and y < year:
                return None
            return d
    return None


def upcoming_lines(contacts: list[dict], today: date, days: int) -> list[str]:
    found = []
    for c in contacts:
        for entry in c.get("important_dates") or []:
            if not isinstance(entry, dict):
                continue
            d = _next_occurrence(entry.get("date", ""), today)
            if d is None or (d - today).days > days:
                continue
            n = (d - today).days
            when = "today" if n == 0 else ("tomorrow" if n == 1 else f"in {n} days")
            found.append((n, f"- {_display(c)} · {c.get('id')} · "
                             f"{entry.get('label') or 'date'} · {d.isoformat()} ({when})"))
    found.sort(key=lambda x: x[0])
    return [t for _, t in found[:MAX_UPCOMING]]


def people_block(directive: str, user_text: str, today: date,
                 upcoming_days: int = DEFAULT_UPCOMING_DAYS, contacts: list[dict] | None = None,
                 cache: dict | None = None) -> tuple[str, str, list[dict]]:
    """The `people` prefetch text in two parts — who is named (records, ask-which, prefixes) and
    the overdue/upcoming lists — and the resolved contacts (for #16's block, which goes between
    them so a cut at the cap loses the lists first). ("", "", []) on any failure — a hint, never
    a cost."""
    from tools import crm as CRM
    try:
        contacts = CRM._load_contacts() if contacts is None else contacts
        got = resolve([directive, user_text], contacts, cache)
        permitted = CRM._tone_profiles_permitted()
        parts: list[str] = []
        people = got["resolved"][:MAX_PEOPLE]
        if people:
            parts.append("Named in this turn and matched exactly (use these records; look up "
                         "only someone not here):")
            parts += [json.dumps(project(c, permitted), ensure_ascii=False, default=str)
                      for c in people]
            if len(got["resolved"]) > MAX_PEOPLE:
                more = ", ".join(_display(c) for c in got["resolved"][MAX_PEOPLE:])
                parts.append(f"(also named: {more} — `read_contact` for them)")
        for word, matches in got["ambiguous"]:
            parts.append(f"{word} matches {len(matches)} contacts — ask which:")
            parts += [json.dumps(CRM._disambiguation_entry(m), ensure_ascii=False, default=str)
                      for m in matches[:MAX_ASK_WHICH]]
            if len(matches) > MAX_ASK_WHICH:
                parts.append(f"(+{len(matches) - MAX_ASK_WHICH} more)")
        for written, c in got["possibly"]:
            parts.append(f"possibly {_display(c)} ({c.get('id')})? \"{written}\" may be "
                         f"someone else — read the record or ask before using it")
        for word, c in got["prefix"]:
            parts.append(f"possibly {_display(c)} ({c.get('id')}) for \"{word}\" (name prefix): "
                         f"read the record before writing a new contact")
        if not (people or got["ambiguous"] or got["prefix"] or got["possibly"]):
            parts.append("No one named in this turn matches a contact exactly.")
        lists: list[str] = []
        overdue = overdue_lines(today)
        lists.append("Overdue for contact:" if overdue else "Nobody is overdue for contact.")
        lists += overdue
        upcoming = upcoming_lines(contacts, today, upcoming_days)
        lists.append(f"Important dates in the next {upcoming_days} days:" if upcoming
                     else f"No important dates in the next {upcoming_days} days.")
        lists += upcoming
        return "\n".join(parts), "\n".join(lists), people
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[contact_resolution] people block not built: {exc}")
        return "", "", []


# --- M1: what was newly saved, read back by the reply -----------------------------------------

READBACK_HEADING = ("NEWLY SAVED — read each back in one clause (spell names and emails, group "
                    "the digits)")
MAX_READBACK = 6
CONTACT_WRITERS = frozenset({"write_contact"})
PROFILE_WRITERS = frozenset({"write_profile"})
_PROFILE_FIELDS = ("name", "email", "phone", "address", "occupation", "city")


def _norm(kind: str, value) -> str:
    text = " ".join(str(value or "").split())
    if kind == "phone":
        from tools.crm import _normalize_phone_digits
        return _normalize_phone_digits(text)
    return text.casefold()


def _contact_values(args: dict) -> list[tuple[str, str]]:
    """(kind, value as given) from write_contact's actual arguments."""
    out: list[tuple[str, str]] = []
    full = {w.casefold() for w in str(args.get("name") or "").split()}
    for field in ("name", "first_name", "last_name", "nickname"):
        value = str(args.get(field) or "").strip()
        if not value:
            continue
        # A first or last name already spelled inside the full name is said once, with it.
        if field in ("first_name", "last_name") and full and \
                {w.casefold() for w in value.split()} <= full:
            continue
        out.append(("name", value))
    info = args.get("contact_info") if isinstance(args.get("contact_info"), dict) else {}
    for kind in ("email", "phone", "address"):
        if str(info.get(kind) or "").strip():
            out.append((kind, str(info[kind]).strip()))
    for extra in info.get("other_emails") or []:
        if str(extra or "").strip():
            out.append(("email", str(extra).strip()))
    social = info.get("social") if isinstance(info.get("social"), dict) else {}
    for where, handle in social.items():
        if str(handle or "").strip():
            out.append((f"{where} handle", str(handle).strip()))
    if str(args.get("employer") or "").strip():
        out.append(("employer", str(args["employer"]).strip()))
    # A name already listed under another field (first_name inside name) is said once.
    seen, unique = set(), []
    for kind, value in out:
        k = (kind, _norm(kind, value))
        if k not in seen:
            seen.add(k)
            unique.append((kind, value))
    return unique


def _stored_contact_values(c: dict) -> set[tuple[str, str]]:
    args = {k: c.get(k) for k in ("name", "first_name", "last_name", "nickname", "employer")}
    args["contact_info"] = c.get("contact_info") or {}
    return {(kind, _norm(kind, v)) for kind, v in _contact_values(args)}


def _profile_values(data: dict) -> dict[str, str]:
    contact = data.get("contact") if isinstance(data.get("contact"), dict) else {}
    location = data.get("location") if isinstance(data.get("location"), dict) else {}
    return {"name": data.get("name") or "", "occupation": data.get("occupation") or "",
            "email": contact.get("email") or "", "phone": contact.get("phone") or "",
            "address": contact.get("address") or "", "city": location.get("city") or ""}


def take_snapshot(trace, contacts_too: bool, profile_too: bool) -> None:
    """What was on file before dispatch, held on the request trace for M1. Values only, as
    comparison keys; nothing is written anywhere. Never raises."""
    if trace is None or not (contacts_too or profile_too):
        return
    snap: dict = {"contacts": None, "profile": None}
    try:
        if contacts_too:
            from tools import crm as CRM
            snap["contacts"] = {str(c.get("id")): {"display": _display(c),
                                                   "values": _stored_contact_values(c)}
                                for c in CRM._load_contacts() if c.get("id")}
        if profile_too:
            from tools.profile import _load
            snap["profile"] = {k: _norm(k, v) for k, v in _profile_values(_load() or {}).items()}
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[contact_resolution] readback snapshot not taken: {exc}")
        return
    trace.readback_snapshot = snap


def _saved(tc) -> bool:
    """A write that landed: not failed, not refused, not waiting on a confirmation card."""
    from core.actions import designed_refusal
    preview = str(getattr(tc, "result_preview", "") or "").lstrip()
    if getattr(tc, "ok", True) is False or designed_refusal(preview):
        return False
    return not preview.startswith(("Error", "error", "{", "["))


def readback_block(trace, user_turn: bool) -> str:
    """The NEWLY SAVED line for the Synthesizer, from the arguments `write_contact` and
    `write_profile` actually received this request, keeping only values absent from the
    pre-dispatch snapshot. Real user turns only. "" when there is nothing new, or on error."""
    if not user_turn or trace is None:
        return ""
    try:
        from core.trace import _walk_agents
        snap = getattr(trace, "readback_snapshot", None) or {}
        stored_contacts = snap.get("contacts")
        stored_profile = snap.get("profile")
        items: list[str] = []
        said: set = set()
        created: dict[str, str] = {}      # a contact made this turn: its new id → who it is
        for rec in _walk_agents(list(trace.pipeline)):
            for turn in rec.turns:
                for tc in turn.tool_calls:
                    if not _saved(tc):
                        continue
                    args = tc.args if isinstance(tc.args, dict) else {}
                    if tc.name in CONTACT_WRITERS and stored_contacts is not None:
                        cid = str(args.get("contact_id") or "")
                        if cid and cid in created:
                            # Created earlier this turn and now enriched: the same person, so
                            # what was already read back is not read back again.
                            before, values, who, ident = None, set(), created[cid], cid
                        else:
                            before = stored_contacts.get(cid) if cid else None
                            values = (before or {}).get("values", set())
                            who = str(args.get("name") or "").strip() or (before or {}).get(
                                "display") or "the contact"
                            ident = cid
                            if not cid:
                                new_id = str(tc.result_preview or "").split("\n", 1)[0].strip()
                                ident = new_id or who.casefold()
                                if new_id:
                                    created[new_id] = who
                        announce = not cid
                        for kind, value in _contact_values(args):
                            key = (ident, kind, _norm(kind, value))
                            if (kind, _norm(kind, value)) in values or key in said:
                                continue
                            said.add(key)
                            items.append(f"new contact {who}" if (kind == "name" and announce
                                                                  and value == who)
                                         else f"{who} — {kind}: {value}")
                    elif tc.name in PROFILE_WRITERS and stored_profile is not None:
                        field = str(args.get("field") or "").strip().lower()
                        value = str(args.get("value") or "").strip()
                        if field not in _PROFILE_FIELDS or not value:
                            continue
                        if not str(tc.result_preview or "").startswith("Profile updated"):
                            continue
                        key = ("profile", field, _norm(field, value))
                        if stored_profile.get(field) == _norm(field, value) or key in said:
                            continue
                        said.add(key)
                        items.append(f"the user's own {field}: {value}")
        if not items:
            return ""
        shown = items[:MAX_READBACK]
        return f"{READBACK_HEADING}:\n" + "\n".join(f"- {x}" for x in shown)
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"[contact_resolution] readback not built: {exc}")
        return ""
