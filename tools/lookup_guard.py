"""
tools/lookup_guard.py — the one sanctioned way a question about a user's task leaves the machine:
`lookup_public_fact(question)`, and the code guard every such question passes first.

Plan: archive/plans/ranking_values_plan_2026-11-23.md § 4.7 (B22, "look up before asking"), as
§ 10 R7 amends it: a probe at mention may ask a PUBLIC fact (a fund's close date, how long a
passport takes) of the Research Agent before asking the user. Mike, B22: "A google search without
truly personal details is innocuous." R7 made that a tool of its own rather than a check inside
`run_subagent`, so the existing `run_subagent("research_agent", …)` traffic is unchanged.

THE GUARD IS CODE AND ALWAYS RUNS (privacy is enforced in Python, never in prompts —
.claude/rules/orchestrator.md). It refuses only full personal identifiers: the user's or a
contact's full name, an email, a phone number, a street address or postcode, an account or
reference number, and — `lookups.refuse_figures`, on by default — a money amount or a health
reading, which may be the user's own (plan § 4.7: "a health/financial figure from the user's
records"; the guard cannot tell one from a public figure, so it refuses both). A first name, an
organisation and a public place pass: "Grace School" passes with a contact named Grace; "Grace
Hopper", a contact's full name, does not — and neither does an organisation saved as a contact
under a two-word name (the refusal names the match, so it can be rephrased). A refusal says which
kind of detail to take out, so the question can be asked again without it; a refused question
costs nothing.

The Research Agent runs bare (core/orchestrator.py: no personal config, no context) and answers
from Google Search grounding — billed per search, seen by no spend meter (plan § 8, Unseen 1).
The daily cap in config/modules/ranking.yaml `lookups` is the only bound; its price is named
there. What comes back is outside content and is wrapped as such (tools/untrusted.py).
"""
from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

# --- what is refused --------------------------------------------------------------------------

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
# A phone number: ten or more digits, or a leading + (counted after the match) — so a year range
# ("2025-2026"), opening hours ("0900-1700") and a form and year ("1040 2025") pass (Fable #8).
_PHONE = re.compile(r"(?<![\w£$€])\+?\d[\d ().-]{5,}\d(?!\w)")
# A run of six or more digits: an account, a card, a reference, a policy number.
_LONG_DIGITS = re.compile(r"\d{6,}")
_IBAN = re.compile(r"\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b")
_NINO = re.compile(r"\b[A-CEGHJ-PR-TW-Z]{2} ?\d{2} ?\d{2} ?\d{2} ?[A-D]\b", re.I)
_SORT_CODE = re.compile(r"\b\d{2}-\d{2}-\d{2}\b")
_POSTCODE = re.compile(r"\b[A-Z]{1,2}\d[A-Z\d]? ?\d[A-Z]{2}\b", re.I)
_STREET = re.compile(
    r"\b\d{1,4}[a-z]?,? +(?:[A-Za-z']+ +){1,3}(?:street|st|road|rd|avenue|ave|lane|ln|drive|close|"
    r"way|crescent|court|place|terrace|gardens|grove|square|mews|row|hill)\b", re.I)
_MONEY = re.compile(r"[£$€¥] ?\d|\b\d[\d,.]*(?: ?(?:k|m|bn))? ?(?:pounds?|quid|dollars?|euros?|"
                    r"gbp|usd|eur|pence)\b", re.I)
# Dates are public: taken out before the digit checks, so "2026-11-30" is not a phone number.
_DATES = re.compile(r"\b\d{4}-\d{2}-\d{2}\b|\b\d{1,2}[/.]\d{1,2}[/.]\d{2,4}\b")
# Readings that are only ever a body's: always refused.
_HEALTH = re.compile(
    r"\b\d+(?:\.\d+)? ?(?:bpm|mmhg|mmol(?:/l)?)\b"
    r"|\b(?:[7-9]\d|1\d\d|2[0-4]\d) ?/ ?(?:[4-9]\d|1[0-4]\d)\b(?! ?/)"
    r"|\bbmi(?: of| is)? ?\d", re.I)
# A weight or a dose is public on its own ("23 kg baggage", "100 ml through security") and the
# user's own beside a body word ("is 80 kg healthy", "a 200 mg dose") — refused only then (#8).
_MEASURE = re.compile(r"\b\d+(?:\.\d+)? ?(?:mg|mcg|µg|ml|kg|kgs|lbs?|iu|stone)\b", re.I)
_BODY = re.compile(r"\b(?:weigh\w*|bmi|dose\w*|dosage|blood|heart|cholesterol|glucose|sugar|"
                   r"pressure|medic\w*|tablets?|pills?|prescri\w*|healthy|overweight|"
                   r"underweight|symptom\w*|diagnos\w*)\b", re.I)

_KINDS = (
    ("an email address", lambda q: _EMAIL.search(q)),
    ("a phone number", lambda q: any(len(re.sub(r"\D", "", m.group())) >= 10
                                     or m.group().startswith("+") for m in _PHONE.finditer(q))),
    ("an account or reference number", lambda q: _LONG_DIGITS.search(q) or _IBAN.search(q)
     or _NINO.search(q) or _SORT_CODE.search(q)),
    ("a street address or postcode", lambda q: _STREET.search(q) or _POSTCODE.search(q)),
)
_FIGURES = (
    ("a money amount", lambda q: _MONEY.search(q)),
    ("a health reading", lambda q: _HEALTH.search(q) or (_MEASURE.search(q) and _BODY.search(q))),
)


def _norm(text: str) -> str:
    # Apostrophes split too, so "Grace Hopper's party" still holds "grace hopper".
    return " " + re.sub(r"[^a-z0-9]+", " ", str(text or "").lower()).strip() + " "


class _Unreadable(Exception):
    """The names could not be read — the guard then refuses everything (fail-closed, #5)."""


def _capitalised(alias: str) -> bool:
    """An alias is a name only when every word in it is capitalised: "Aunt Ruth" is, "my wife"
    and "the dentist" are not (Stage 5 build amendment 3)."""
    words = re.findall(r"[^\W\d_]+", alias)
    return bool(words) and all(w[0].isupper() for w in words)


def _aliases(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value if isinstance(v, str)]
    return [str(value)] if isinstance(value, str) and value else []


def _load_profile() -> dict:
    try:
        from tools.profile import _load as _profile
        prof = _profile() or {}
    except Exception as exc:  # noqa: BLE001
        raise _Unreadable("profile") from exc
    return prof if isinstance(prof, dict) else {}


def _load_contacts() -> list[dict]:
    try:
        from tools import crm
        contacts = crm._load_contacts()
    except Exception as exc:  # noqa: BLE001
        raise _Unreadable("contacts") from exc
    return [c for c in contacts or [] if isinstance(c, dict)]


def _contact_label(c: dict) -> str:
    full = " ".join(x for x in (str(c.get("first_name") or "").strip(),
                                str(c.get("last_name") or "").strip()) if x)
    return str(c.get("name") or "").strip() or full or "a saved contact"


def _name_entries(persona: str | None) -> list[tuple[str, str, str]]:
    """Every (first, last, whose) the user's data holds: the user's own and each contact's — and
    a partner named on a contact. A one-word name is never a full identifier, so never listed.
    `whose` names the match, so a refusal can say what to take out. Every contact is checked:
    the CRM's `relationship_type` has no organisation value, so the old organisation skip never
    matched (build amendment 2); a contact saved under an organisation-like name costs, at worst,
    a rephrase. `referred_to_as` is read per alias, and an alias counts only when every word is
    capitalised (amendment 3). Raises `_Unreadable` when a store exists but cannot be read: an
    unread name must not pass (the privacy ruling is fail-closed)."""
    names: list[tuple[str, str, str]] = []

    def add(full: str, whose: str) -> None:
        parts = _norm(full).split()
        if len(parts) >= 2:
            names.append((parts[0], parts[-1], whose))

    add(str(_load_profile().get("name") or ""), "the user's own name")
    for c in _load_contacts():
        label = _contact_label(c)
        first = str(c.get("first_name") or "").strip()
        last = str(c.get("last_name") or "").strip()
        for given in (first, str(c.get("nickname") or "").strip()):
            if given and last:
                add(f"{given} {last}", label)
        add(str(c.get("name") or ""), label)
        spouse = str(c.get("spouse_name") or "").strip()
        if spouse:
            add(spouse, f"{spouse}, partner of {label}")
        for alias in _aliases(c.get("referred_to_as")):
            if _capitalised(alias):
                add(alias, label)
    return names


def _full_names(persona: str | None) -> list[tuple[str, str]]:
    """Every (first, last) the user's data holds — see `_name_entries`."""
    return [(f, l) for f, l, _w in _name_entries(persona)]


def _name_at(hay: str, names: list[tuple]) -> int | None:
    """The index of the first full name in the question: the first and last names with at most
    two words between ("Grace M. Hopper", "Grace Brewster Hopper"), or the last then the first
    ("Hopper, Grace")."""
    words = hay.split()
    for n, entry in enumerate(names):
        first, last = entry[0], entry[1]
        for i, w in enumerate(words):
            if w == first and last in words[i + 1:i + 4]:
                return n
            if w == last and i + 1 < len(words) and words[i + 1] == first:
                return n
    return None


def _names_in(hay: str, names: list[tuple]) -> bool:
    """A full name in the question — see `_name_at`."""
    return _name_at(hay, names) is not None


_NAME_KIND = "the full name of someone the user knows"


def _name_refusal(entry: tuple) -> str:
    # The kind first, the match in brackets: the logs split at " (" and so carry the kind only.
    return f"{_NAME_KIND} (matched: {entry[2]} — a first name alone is fine)"


def check(question: str, persona: str | None = None, refuse_figures: bool = True) -> str | None:
    """None when the question may leave; otherwise the kind of detail that must come out of it."""
    q = str(question or "")
    if not q.strip():
        return "nothing — the question is empty"
    hay = _norm(q)
    try:
        names = _name_entries(persona)
    except _Unreadable:
        return "nothing checkable right now — the user's contacts could not be read"
    at = _name_at(hay, names)
    if at is not None:
        return _name_refusal(names[at])
    q = _DATES.sub(" ", q)
    for kind, hit in _KINDS + (_FIGURES if refuse_figures else ()):
        if hit(q):
            return kind
    return None


# --- the Research check (Stage 5 #17) ----------------------------------------------------------
#
# Every Research call — Coordinator dispatch, run_subagent, lookup_public_fact — passes
# `research_refusal` in core/orchestrator.py `_run_single_agent` before any provider is called.
# Narrower than `check()` on purpose: Research legitimately asks about dosages, prices and public
# addresses, so only the user's KNOWN identifiers are refused — a full name the records hold, and
# the user's or a contact's stored email, phone, postcode or street. A refusal says what to take
# out; the query is never rewritten. One reader with `check()`, fail-closed the same way.

RESEARCH_REFUSED = "refused before sending:"
UNREADABLE = "the user's records could not be read (so nothing could be checked)"

_UNIT_WORDS = frozenset({"flat", "apartment", "apt", "unit", "suite", "floor", "room"})
# A postcode that is not UK-shaped: a digit-bearing code in a later segment of the address
# ("75001 Paris", "10115 Berlin", "D-10115", "90210-1234"). Matched whitespace- and
# case-normalised, as its own string (build amendment 4).
_OTHER_POSTCODE = re.compile(r"\b(?:[A-Z]{1,2}-)?\d{4,6}(?:-\d{3,4})?\b", re.I)


def _phone_key(raw: str) -> str:
    """Digits only, the last 9: the national number whatever the country code or leading 0."""
    digits = re.sub(r"\D", "", str(raw or ""))
    return digits[-9:] if len(digits) >= 7 else ""


def _postcode_key(address: str, explicit: str = "") -> str:
    if explicit.strip():
        return re.sub(r"\s+", "", explicit).upper()
    m = _POSTCODE.search(address)
    if m:
        return re.sub(r"\s+", "", m.group()).upper()
    for seg in address.split(",")[1:]:
        m = _OTHER_POSTCODE.search(seg)
        if m:
            return re.sub(r"\s+", "", m.group()).upper()
    return ""


def _street_key(address: str) -> str:
    """The street segment: the first comma segment that holds a house number — never a bare
    district or city. A flat or unit number on its own ("Flat 3") is not the street, so the
    next segment is read instead."""
    for seg in address.split(",")[:2]:
        words = _norm(seg).split()
        if not any(any(ch.isdigit() for ch in w) for w in words):
            continue
        if all(w in _UNIT_WORDS or any(ch.isdigit() for ch in w) for w in words):
            continue
        return _norm(seg)
    return ""


def _details(info: dict, whose: str) -> list[tuple[str, str, str]]:
    """(kind, key, whose) for the email, phone, postcode and street in one contact block."""
    if not isinstance(info, dict):
        return []
    out: list[tuple[str, str, str]] = []
    for e in [info.get("email")] + list(info.get("other_emails") or []):
        e = str(e or "").strip().lower()
        if "@" in e:
            out.append(("an email address", e, whose))
    key = _phone_key(str(info.get("phone") or ""))
    if key:
        out.append(("a phone number", key, whose))
    address = str(info.get("address") or "").strip()
    explicit = str(info.get("postcode") or info.get("postal_code") or info.get("zip") or "")
    key = _postcode_key(address, explicit)
    if key:
        out.append(("a postcode", key, whose))
    key = _street_key(address)
    if key:
        out.append(("a street address", key, whose))
    return out


def _own_identifiers(persona: str | None) -> list[tuple[str, str, str]]:
    """The user's own stored email, phone, postcode and street (profile `contact`), and each
    contact's (CRM `contact_info`, build amendment 1), normalised for matching. Raises
    `_Unreadable` when either store exists but cannot be read, as `_name_entries` does."""
    out = _details(_load_profile().get("contact") or {}, "the user's own")
    for c in _load_contacts():
        out += _details(c.get("contact_info") or {}, f"of {_contact_label(c)}, a contact")
    return out


def _detail_in(kind: str, key: str, query: str) -> bool:
    if kind == "an email address":
        return key in query.lower()
    if kind == "a phone number":
        runs = re.findall(r"\d{7,}", re.sub(r"[\s.()\-+]", "", query))
        return any(key in r for r in runs)
    if kind == "a postcode":
        return key in re.sub(r"\s+", "", query).upper()
    return key in _norm(query)


def check_research(query: str, persona: str | None = None) -> str | None:
    """None when a Research query may leave; otherwise what must come out of it — the kind,
    then in brackets whose it is (a trace keeps the part before " (" only). Raises nothing: an
    unreadable store returns `UNREADABLE`, which refuses (fail-closed)."""
    q = str(query or "")
    try:
        names = _name_entries(persona)
        details = _own_identifiers(persona)
    except _Unreadable:
        return UNREADABLE
    at = _name_at(_norm(q), names)
    if at is not None:
        return _name_refusal(names[at])
    for kind, key, whose in details:
        if _detail_in(kind, key, q):
            return f"{kind} ({whose})"
    return None


def refusal_text(why: str) -> str:
    """The whole reply a refused Research query gets, from `check_research`'s reason."""
    if why == UNREADABLE:
        return (f"{RESEARCH_REFUSED} the user's records could not be read, so nothing was sent. "
                f"Answer without the lookup, or ask the user.")
    return (f"{RESEARCH_REFUSED} the question carries {why}. Nothing left this device. Ask it "
            f"again without that.")


# --- the tool ----------------------------------------------------------------------------------

def _cfg(persona: str | None) -> dict:
    from tools import ranking as RK
    return RK.cfg(persona).get("lookups") or {}


def lookup_public_fact(question: str) -> str:
    """Ask the Research Agent one public fact, through the guard and under the daily cap."""
    from core.persona import current_persona
    return ask_public(question, current_persona())


def ask_public(question: str, persona: str, source: str = "lookup_public_fact",
               max_chars: int | None = None) -> str:
    """The one guarded path out (shared by `lookup_public_fact` and the goal talk's research,
    goal network plan § 18): the guard, the daily cap, the bare Research Agent, the wrap. Every
    refusal or failure is a sentence that starts "refused", "not available" or "the lookup"."""
    lc = _cfg(persona)
    if not lc.get("enabled"):
        # Off until Mike has checked the grounding price and ruled on figures (Fable #1: the
        # tool is live at deploy otherwise, spending on a meter nothing sees).
        return "not available yet — ask the user instead."
    why = check(question, persona, refuse_figures=bool(lc.get("refuse_figures", True)))
    if why:
        logger.info("[lookup] refused: %s", why.split(" (")[0])
        return (f"refused: the question carries {why}. Nothing left this device. Ask it again "
                f"without that — a public fact needs no detail of the user's own (\"how long does "
                f"a passport renewal take\", not theirs) — or ask the user instead.")
    from tools import ranking as RK
    import tools.day_plan as D
    today = D._today().isoformat()
    cap = int(lc.get("per_day", 5))
    with D._locked(persona):
        st = RK.load_state(persona)
        used = st.get("lookups") or {}
        n = int(used.get("n") or 0) if used.get("day") == today else 0
        if n >= cap:
            return (f"refused: today's {cap} lookups are used. Ask the user instead, or say you "
                    f"will find out tomorrow.")
        st["lookups"] = {"day": today, "n": n + 1}
        RK.save_state(st, persona)
    from core.spend_guard import check_before_session
    from core.trace import get_subagent_depth, set_subagent_depth
    from core.orchestrator import run_session
    from tools.untrusted import wrap_untrusted
    try:
        check_before_session()
        depth = get_subagent_depth()
        set_subagent_depth(depth + 1)
        try:
            # Bare by the orchestrator's own rule for research_agent: the question is all it sees.
            answer = run_session("research_agent", user_input=str(question).strip(),
                                 persona=persona, complexity="quick")
        finally:
            set_subagent_depth(depth)
    except Exception as exc:  # noqa: BLE001 — a failed lookup is a question for the user
        logger.warning("[lookup] failed: %s", type(exc).__name__)
        # Nothing ran: give the place back (Fable #11).
        _refund(persona, today)
        return "the lookup did not come back — ask the user instead."
    answer = str(answer or "")
    if answer.startswith(RESEARCH_REFUSED):
        # Refused by the Research check before any search: nothing was spent, so the day's
        # place comes back, and the refusal is code's own text — not outside content.
        _refund(persona, today)
        return answer
    text = answer
    if max_chars:
        text = text[:max_chars]      # cut before wrapping, so the closing tag is never lost
    return wrap_untrusted(text, source=f"research_agent:{source}")


def _refund(persona: str | None, today: str) -> None:
    """Give back one of today's lookups — for a lookup that never reached a search."""
    from tools import ranking as RK
    import tools.day_plan as D
    with D._locked(persona):
        st = RK.load_state(persona)
        used = st.get("lookups") or {}
        if used.get("day") == today and int(used.get("n") or 0) > 0:
            st["lookups"] = {"day": today, "n": int(used["n"]) - 1}
            RK.save_state(st, persona)


LOOKUP_PUBLIC_FACT_SCHEMA = {
    "name": "lookup_public_fact",
    "description": (
        "Look up one PUBLIC fact a task turns on, before asking the user — a fund's closing "
        "date, how long a passport renewal takes, when a school term starts. Only general "
        "facts: no full name of anyone the user knows, no contact details, no address, no "
        "account or reference number, no money amount or health reading of theirs (a refused "
        "question says what to take out). A few a day at most; when it is refused or used up, "
        "ask the user."
    ),
    "input_schema": {
        "type": "object",
        "properties": {"question": {"type": "string",
                                    "description": "The public question, in a sentence."}},
        "required": ["question"],
    },
}
