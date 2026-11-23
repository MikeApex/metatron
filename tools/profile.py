"""
tools/profile.py — Capture and read stable biographical facts about the user.

The user gives these in passing, mid-conversation: an email address while asking
for a booking, an occupation while talking about work, a medication while talking
about sleep. Without a home they are lost, or — worse — filed wherever the model
can reach, which on 2026-08-02 meant an email, postal address and phone number
landing in the persona preferences file and riding in every system prompt from
then on.

So the split is deliberate:

    profile.yaml   stable facts about who the user is        <- this module
    {persona}.md   how the user wants to be dealt with       <- tools/persona.py
    context.json   this week's threads and follow-ups        <- tools/context_tracker.py

Reading is a separate tool from writing on purpose. `load_profile()` renders a
short summary into the system prompt for every head-layer call, and contact
details are deliberately excluded from it — a phone number does not need to be
restated to the model on every exchange. Agents that genuinely need one (Logistics
making a booking, Physical Health checking a standing condition) call
`read_profile` at the point of use.

Sensitive-tier, local-only. Written 0600.
"""

import os
import re
from pathlib import Path

import yaml

from core.persona import persona_config_dir

# Only these fields can be written. Not a security boundary — the model is not an
# attacker — but a schema boundary: without it the profile accretes invented keys
# that nothing reads, which is how the persona file filled up with a section no
# code knew about. An unknown field is a signal that something needs designing,
# so it is refused loudly rather than absorbed.
_SCALAR_FIELDS = {
    "name",
    "occupation",
    "household",
    "birth_year",
    "age",
}
_CONTACT_FIELDS = {"email", "phone", "address"}
_LOCATION_FIELDS = {"city", "country", "timezone"}

# [DB-0810-15]: input vs output language, independently settable, so a persona
# can send in one language and be answered in another. Deliberately two flat
# keys rather than one nested "language" dict, same reasoning as _LOCATION_FIELDS
# vs _CONTACT_FIELDS being separate groups — setting one must never touch the
# other, and a shared dict makes that guarantee a matter of code discipline
# instead of structure.
_LANGUAGE_FIELDS = {"input_language", "output_language",
                    "primary_language", "secondary_language"}

# TWO PAIRS, AND THE SPLIT IS THE POINT (Mike's schema, 2026-09-04). `input_language`
# and `output_language` are the LIVE SETTING — what the pipeline should read and write
# right now. `primary_language` and `secondary_language` are FACTS ABOUT THE PERSON —
# which languages they have, independent of what the tool is currently configured to do.
#
# They were conflated before, in the worst possible place: the wisdom store held THREE
# overlapping entries (`language_preference`, `language_preference_bulgarian`,
# `primary_language`) alongside the real `output_language` field the code reads, so a
# stated fact about the user and a runtime setting were the same kind of thing recorded
# in four places. Naming the axis is what stops it recurring — a fact has one home and a
# setting has another, and neither can be written by mistaking itself for the other.
#
# Deliberately NOT named `*_default`, which Mike's first sketch suggested: a "default"
# implies a per-session override that does not exist, and renaming the two live fields
# would break every reader of them for no behaviour change.

# Stored value is an ISO 639-1 code ("bg"), not the free-text name the user
# actually says ("Bulgarian"), for two reasons: (1) it's the canonical, unambiguous
# form other code can key off without re-parsing prose, matching how birth_year/age
# are normalized to int rather than kept as spoken text; (2) [DB-0815-02] (voice,
# filed Later) will need a stored language value to pick an edge-tts voice tag like
# "bg-BG" — an ISO 639-1 code is the language half of that tag and composes with a
# region without re-migrating this field, where a free-text name would need a
# separate normalization pass at that point anyway. _LANGUAGE_NAMES below is the
# small map from what a user actually says to the code that gets stored; it is not
# meant to be exhaustive, only to cover the languages Mike has actually used
# (English, Bulgarian) plus common neighbors, and a code can always be given
# directly. Free text that isn't recognized is refused rather than stored
# unnormalized — a value nothing downstream can key off of is worse than none.
_LANGUAGE_NAMES = {
    "english": "en",
    "bulgarian": "bg",
    "spanish": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "russian": "ru",
    "greek": "el",
    "turkish": "tr",
    "romanian": "ro",
    "serbian": "sr",
    "ukrainian": "uk",
}

# Passions (ranking_values_plan_2026-11-23 § 4.8, B15–B17): what the user lives for, as a list of
# {what, source: stated|inferred, since, basis, goals}. A STATED passion lifts the social and
# psychological costs of a task that serves it by one grade (tools/ranking.py); an inferred one
# never lifts — it is only a reason to ask. Tied to goals and mission (Mike, 2026-11-23): a passion
# named in the user's own mission or goal counts as their word — code checks the words are there.
_PASSIONS = "passions"
WRITABLE = _SCALAR_FIELDS | _CONTACT_FIELDS | _LOCATION_FIELDS | _LANGUAGE_FIELDS | {"other", _PASSIONS}

# Code -> display name, for the one consumer that has to show a language to a model rather
# than key off it (`load_profile()` in core/orchestrator.py). Built by inverting the map above
# so the two can never disagree; a code with no name maps to itself, which is the correct
# degradation for a code given directly that _LANGUAGE_NAMES does not spell out.
def language_name(code: str) -> str:
    """Display name for a stored ISO 639-1 code, or the code itself if unmapped."""
    return _CODE_TO_NAME.get((code or "").lower(), code)


_CODE_TO_NAME = {v: k.title() for k, v in _LANGUAGE_NAMES.items()}

# Never rendered into the system prompt by load_profile(). Retrieved on demand via read_profile.
#
# THIS IS NOW ENFORCED. Until 2026-08-15 it was not: this constant had exactly one reference in
# the codebase — its own definition — while `load_profile()` in core/orchestrator.py rendered a
# hand-written per-field list that never consulted it. Contact details stayed out of the prompt
# only because that list happened not to render them, so adding an `email` line there would have
# leaked a contact detail into every head-layer prompt with nothing to catch it, while this
# module's docstring went on claiming they were "deliberately excluded". `load_profile()` now
# skips any field named here, so the constant is the control it always read as.
#
# `health_notes` LIVED HERE FROM 2026-08-15 TO 2026-08-18 AND IS GONE ON PURPOSE — do not
# re-add it. Mike's value was "Standard oatmeal: 60g oats, 100g 2% milk, 100g almond milk, 20g
# nuts", and the rule he stated when it was first hidden from the prompt generalises past this
# one field: **detail the tool learns about a user belongs at the level that needs it,
# retrieved when relevant, not broadcast on every call.** Excluding it from the prompt treated
# the symptom; the fact still had no home but a profile slot named for a domain rather than for
# what it was about. It now lives in the wisdom store as `standard_breakfast`, domain `food`,
# where the Coordinator fetches it on a food turn and nothing else pays for it. Migrated on the
# VM 2026-08-18 by scripts/migrate_health_notes.py; the empty `oatmeal_formula` placeholder
# that had been sitting beside it is archived with a merged_into pointer.
#
# A health fact a SAFETY FLAG classifies from was never this field's job and still is not:
# medication lives in agent_config.json behind _GUARDED_KEYS, where physical_health.md requires
# it to be read every time rather than at a model's discretion.
_PROMPT_EXCLUDED = _CONTACT_FIELDS


# [DB-0815-05] profile.yaml's `name` field was found holding the literal sentence
# "Contact name updated from Ada to Ida." — a CRM correction that landed in the
# user's own identity instead of tools/crm.py's write_contact, and rendered into
# every head-layer system prompt via load_profile() until caught. Narrow guard,
# not broad heuristic: needs a subject word AND a correction verb AND a
# "from ... to ..." span all at once, or (for 'name' specifically) an
# implausibly long value that ends like a sentence. An ordinary fact — "Allergic
# to peanuts.", "Prefers to work from home.", "Mike Pearson" — trips none of these.
_CORRECTION_SUBJECT_WORDS = {"contact", "name"}
_CORRECTION_VERB_WORDS = {"updated", "changed", "corrected", "renamed", "fixed"}
_FROM_TO_RE = re.compile(r"\bfrom\b.+\bto\b", re.IGNORECASE)


def _third_party_correction_reason(field: str, text: str) -> str:
    """
    Returns a refusal reason if `text` reads as a note about someone *else's*
    contact record being corrected rather than a fact about the user, or ""
    if the value looks ordinary. Two independent checks — either is enough:

    1. All three of: a subject word ('contact'/'name'), a correction verb
       ('updated'/'changed'/'corrected'/'renamed'/'fixed'), and a "from ... to
       ..." span in the same value. The recorded failure text hits all three;
       an everyday fact essentially never does, because it needs neither the
       subject nor the verb, and rarely both prepositions together.
    2. field == 'name' specifically, and the value is long (more than 5 words)
       and ends in sentence punctuation (. ! ?) — a real name is short and is
       not a sentence. Five words comfortably clears a name with a suffix
       ("Robert Smith Jr." is 3), so this does not catch an ordinary long name.

    Deliberately does not attempt to catch arbitrary third-party facts in
    general (e.g. "Catherine's birthday is July 10th") — that needs real entity
    recognition and would risk refusing legitimate 'other' entries; this only
    catches the specific "a contact's name/info was corrected" phrasing that
    produced the recorded bug.
    """
    lower = text.lower()
    words = {w.strip(".,!?;:'\"") for w in lower.split()}
    if (
        (words & _CORRECTION_SUBJECT_WORDS)
        and (words & _CORRECTION_VERB_WORDS)
        and _FROM_TO_RE.search(lower)
    ):
        return (
            f"'{text}' reads like a note that a contact's name or details were "
            f"corrected, not a fact about the user."
        )
    if field == "name" and len(text.split()) > 5 and text.rstrip().endswith((".", "!", "?")):
        return f"'{text}' reads like a sentence describing an event, not a name."
    return ""


def _profile_path() -> Path:
    return persona_config_dir() / "profile.yaml"


def _load() -> dict:
    path = _profile_path()
    if not path.exists():
        return {}
    try:
        return yaml.safe_load(path.read_text()) or {}
    except yaml.YAMLError as e:
        raise ValueError(f"profile.yaml is not valid YAML: {e}") from e


def _save(data: dict) -> Path:
    path = _profile_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True))
    os.chmod(path, 0o600)
    return path


_PASSION_STOP = frozenset({"the", "and", "with", "for", "from", "into", "their", "they", "them",
                           "more", "most", "time", "some", "about", "being", "doing", "make"})


def _words(text: str) -> list[str]:
    import re as _re
    return [w for w in _re.findall(r"[a-z']{4,}", str(text or "").lower()) if w not in _PASSION_STOP]


def _named_in(what: str, text: str) -> bool:
    """Whether a text names the passion: EVERY word of it appears there, by a shared stem of 5
    letters ("gardening" in "grow vegetables in the garden") — one shared word is not enough
    ("chess with the children" is not named by "raise the children well"; Fable #6)."""
    have = _words(text)
    want = _words(what)

    def stem(a: str, b: str) -> bool:      # the first 5 letters, or all of a 4-letter word
        n = min(5, len(a), len(b))
        return a[:n] == b[:n]
    return bool(want) and all(any(stem(w, h) for h in have) for w in want)


def _passion_basis(what: str, source: str, basis: str) -> tuple[str, list[str], str]:
    """(source as it may be stored, linked goal ids, a note) — a STATED passion must stand on the
    user's own word: said in this turn ("chat"), or written in their mission or a goal. Anything
    that cannot show it is kept as inferred, and the note says so."""
    goals: list[str] = []
    b = str(basis or "chat").strip()
    if b.lower() == "mission":
        try:
            text = (persona_config_dir() / "mission.md").read_text(encoding="utf-8")
        except OSError:
            text = ""
        if source == "stated" and not _named_in(what, text):
            return "inferred", goals, " (kept as inferred: the mission does not name it)"
        return source, goals, ""
    if b.lower() != "chat":
        try:
            from tools.obligations import _goal_index
            g = _goal_index().get(b)
        except Exception:  # noqa: BLE001
            g = None
        if g is None:
            return "inferred" if source == "stated" else source, goals, \
                f" (no goal {b!r} on file — kept as inferred)" if source == "stated" else ""
        text = f"{g.get('title') or ''} {g.get('shareable_what') or ''}"
        # The tie is the goal's own words, whatever the source (Fable #6: re-recording a stated
        # passion against any goal id must not tie it to that goal's tasks).
        if not _named_in(what, text):
            return ("inferred" if source == "stated" else source), goals, \
                f" (not tied: goal {b} does not name it" + \
                (", kept as inferred)" if source == "stated" else ")")
        return source, [b], ""
    if source == "stated":
        try:
            from tools.turn_context import current as _turn
            turn = _turn()
        except Exception:  # noqa: BLE001
            turn = None
        # Fail-closed (Fable #6): the user's word needs a user turn, so no turn bound — a
        # worker, a scheduled run — is no word of theirs.
        if turn is None or not turn.get("user_turn"):
            return "inferred", goals, " (kept as inferred: nothing from the user this turn)"
    return source, goals, ""


def _write_passion(data: dict, text: str, source: str, basis: str) -> str:
    from datetime import date as _date
    src = str(source or "inferred").strip().lower()
    if src not in ("stated", "inferred"):
        return "Error: `source` for a passion is stated or inferred."
    src, goals, note = _passion_basis(text, src, basis)
    rows = [r for r in (data.get(_PASSIONS) or []) if isinstance(r, dict) and r.get("what")]
    key = text.strip().lower()
    row = next((r for r in rows if str(r["what"]).strip().lower() == key), None)
    if row is None:
        row = {"what": text.strip()[:60], "source": src, "since": _date.today().isoformat(),
               "basis": str(basis or "chat").strip()[:40]}
        rows.append(row)
    elif src == "stated" and row.get("source") != "stated":
        # An inference never replaces the user's own word; their word upgrades an inference.
        row.update(source="stated", basis=str(basis or "chat").strip()[:40])
    elif src == "inferred" and goals and row.get("source") == "stated":
        goals = []          # an inference never ties a stated passion to a new goal
    if goals:
        row["goals"] = sorted(set(row.get("goals") or []) | set(goals))
    data[_PASSIONS] = rows
    _save(data)
    return f"Profile updated: passion '{row['what']}' ({row['source']}){note}"


def stated_passions() -> list[dict]:
    """The passions the user stated — the only ones that lift a grade (§ 4.8)."""
    try:
        rows = _load().get(_PASSIONS) or []
    except Exception:  # noqa: BLE001
        return []
    return [r for r in rows if isinstance(r, dict) and r.get("source") == "stated" and r.get("what")]


def write_profile(field: str, value: str, confirm_token: str = "", source: str = "",
                  basis: str = "") -> str | dict:
    """
    Record one stable biographical fact about the user.

    Args:
        field: One of the permitted field names (see WRITABLE).
        value: The value to store. For 'other', the entry is appended to a list
               rather than replacing what is already there. For 'input_language'/
               'output_language', a language name ('Bulgarian') or ISO 639-1 code
               ('bg') — the two are independent, and setting one never sets the
               other, since a persona can be spoken to in one language and
               answered in another.
        confirm_token: Only needed when *changing* an already-set contact field
            (email/phone/address) — the token from a PENDING_CONFIRMATION response,
            after the user has approved it. Omit for first-time capture of any field,
            and for every non-contact field always.

    Returns:
        Confirmation string once written, or a PENDING_CONFIRMATION dict when changing
        an existing contact field, or an error naming the permitted fields.
    """
    key = field.strip().lower()
    if key not in WRITABLE:
        return (
            f"Error: '{field}' is not a profile field. "
            f"Permitted: {', '.join(sorted(WRITABLE))}. "
            "Use 'other' for a stable fact that fits none of these. "
            "Interaction preferences — how the user wants to be spoken to — "
            "belong in the persona file instead. Anything about the user's health, diet, "
            "sleep, training or habits belongs in the knowledge store: call write_wisdom "
            "with the subject domain, not this tool."
        )

    text = str(value).strip()
    if not text:
        return f"Error: no value given for '{key}'."

    # [DB-0815-05]: refuse a correction about someone else's contact record before
    # it lands in the user's own profile — see _third_party_correction_reason.
    if key in {"name", "other"}:
        reason = _third_party_correction_reason(key, text)
        if reason:
            return (
                f"Error: not saved. {reason} write_profile is for stable facts "
                f"about the user; a correction to a contact's name or details "
                f"belongs in write_contact instead."
            )

    data = _load()

    if key == _PASSIONS:
        return _write_passion(data, text, source, basis)

    # Contact fields (email, phone, address) are the highest-consequence entries in this
    # store — a wrong one misdirects real communication, and they're exactly what voice
    # transcription gets wrong most often (see relationships.md's read-back protocol for
    # the same failure mode on CRM contacts). First-time capture writes immediately, same
    # as every other field — synthesizer.md's "confirm at capture" clause covers that
    # case with a spoken-back clause, not a blocking gate. *Changing* an already-set
    # value is different: that's an explicit correction or a genuine life change, either
    # way rare enough that a confirm-gate round trip costs nothing real. Same mechanism
    # as write_config/write_agent_config's guarded keys — gate it in Python, don't rely
    # on the agent remembering to ask.
    if key in _CONTACT_FIELDS:
        existing = (data.get("contact") or {}).get(key, "").strip()
        if existing and existing.lower() != text.lower():
            from tools.confirm import consume, request

            args = {"field": key, "value": text}
            ok, reason = consume(confirm_token or None, "write_profile_contact", args)
            if not ok:
                if confirm_token:
                    return f"Error: not changed. {reason}"
                return request(
                    "write_profile_contact", args,
                    description=f"Change stored {key} from '{existing}' to '{text}'?",
                )

    if key == "other":
        entries = list(data.get("other") or [])
        if text in entries:
            return f"Already recorded in profile: {text}"
        entries.append(text)
        data["other"] = entries
    elif key in _CONTACT_FIELDS:
        contact = dict(data.get("contact") or {})
        contact[key] = text
        data["contact"] = contact
    elif key in _LOCATION_FIELDS:
        loc = dict(data.get("location") or {})
        loc[key] = text
        data["location"] = loc
    elif key in {"age", "birth_year"}:
        try:
            data[key] = int(text)
        except ValueError:
            return f"Error: '{key}' must be a whole number, got '{text}'."
    elif key in _LANGUAGE_FIELDS:
        code = _LANGUAGE_NAMES.get(text.lower())
        if code is None and len(text) == 2 and text.isalpha() and text.lower() in _LANGUAGE_NAMES.values():
            code = text.lower()
        if code is None:
            return (
                f"Error: '{text}' is not a recognized language. Give a language name "
                f"(e.g. 'Bulgarian') or an ISO 639-1 code (e.g. 'bg'). Recognized names: "
                f"{', '.join(sorted(n.title() for n in _LANGUAGE_NAMES))}."
            )
        data[key] = code
    else:
        data[key] = text

    _save(data)
    where = "contact" if key in _CONTACT_FIELDS else ("location" if key in _LOCATION_FIELDS else key)
    return f"Profile updated: {where}.{key}" if where != key else f"Profile updated: {key}"


def read_profile(field: str = "") -> str:
    """
    Read stored biographical facts, including the ones kept out of the prompt.

    Call this at the point of use — when a booking needs an email address, or a
    health question needs a standing condition — rather than assuming the value
    is already in context. Contact details in particular are never in the prompt.

    Args:
        field: A single field name to read. Omit to get everything on file.

    Returns:
        The value, or a readable summary of the whole profile.
    """
    data = _load()
    if not data:
        return "No profile recorded yet."

    flat: dict[str, str] = {}
    for k, v in data.items():
        if k in {"contact", "location"} and isinstance(v, dict):
            flat.update({ik: str(iv) for ik, iv in v.items() if iv not in (None, "")})
        elif k == "other" and isinstance(v, list):
            for i, item in enumerate(v, 1):
                flat[f"other_{i}"] = str(item)
        elif k == _PASSIONS and isinstance(v, list):
            flat[k] = ", ".join(f"{r.get('what')} ({r.get('source')})" for r in v
                                if isinstance(r, dict) and r.get("what"))
        elif k == "ambient":
            continue
        elif v not in (None, "", [], {}):
            flat[k] = str(v)

    if field:
        key = field.strip().lower()
        if key in flat:
            return f"{key}: {flat[key]}"
        return f"'{field}' is not recorded in the profile. On file: {', '.join(sorted(flat)) or 'nothing'}."

    return "\n".join(f"{k}: {v}" for k, v in flat.items()) or "No profile recorded yet."


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

WRITE_PROFILE_SCHEMA = {
    "name": "write_profile",
    "description": (
        "Record a stable biographical fact the user has given you — email, phone, "
        "address, occupation, household, health notes, age, where they live, or which "
        "language to use with them. "
        "Use this whenever the user supplies such a detail in passing, so it is "
        "not lost: they should never have to give you the same detail twice. "
        "This is for facts about who they are. Preferences about how they want to "
        "be spoken to go to the persona file instead, and anything that is only "
        "true this week belongs in the context tracker. First-time capture of email/"
        "phone/address writes immediately — say back what you captured in your reply. "
        "*Changing* an already-set email, phone, or address returns PENDING_CONFIRMATION "
        "instead of writing — show the user the change and leave it with them. Approving it "
        "in the app is what applies it; do not call this tool a second time, same as send_email. "
        "'input_language' and 'output_language' are independent — set one without the other. "
        "'input_language' is what the user writes/speaks to you in; 'output_language' is what "
        "you respond in. They do not have to match. "
        "This tool is for facts about the user themselves — a note that someone else's contact "
        "record was corrected (e.g. 'Contact name updated from Ada to Ida') is refused; that "
        "correction belongs in write_contact instead. "
        "'passions' records one thing the user lives for (a hobby, a craft, a cause) per call, "
        "with `source` and `basis`; it is added to the list."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": "Which fact is being recorded.",
                "enum": sorted(WRITABLE),
            },
            "value": {
                "type": "string",
                "description": (
                    "The value to store, exactly as the user gave it. For 'other', "
                    "a single short sentence stating one stable fact; it is appended "
                    "to the existing list rather than replacing it."
                ),
            },
            "source": {
                "type": "string", "enum": ["stated", "inferred"],
                "description": (
                    "passions only: stated — the user said they love it, or it is in their "
                    "mission or a goal (name which in `basis`); inferred — your reading, which "
                    "is only a reason to ask them. Default inferred."
                ),
            },
            "basis": {
                "type": "string",
                "description": (
                    "passions only: where it comes from — \"chat\" (their words this turn), "
                    "\"mission\", or the id of the goal that names it."
                ),
            },
            "confirm_token": {
                "type": "string",
                "description": (
                    "Not for you to set. The app supplies this when it carries out a "
                    "contact change the user has approved; leave it out of every call "
                    "you make."
                ),
            },
        },
        "required": ["field", "value"],
    },
}

READ_PROFILE_SCHEMA = {
    "name": "read_profile",
    "description": (
        "Look up a stored fact about the user. Contact details (email, phone, "
        "address) are deliberately not included in your context, so call this when "
        "you actually need one — for a booking, a form, or a message. Omit the "
        "field name to see everything on file. If the value you need is not "
        "recorded, ask the user for it rather than guessing."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "field": {
                "type": "string",
                "description": (
                    "Field to read, e.g. 'email'. Omit to return the whole profile."
                ),
            },
        },
        "required": [],
    },
}
