"""
tools/crm.py — Contact Relationship Manager.

Provides structured, persistent contact records for the Relationships agent.
Contacts are stored locally in data/crm/contacts.json (sensitive-tier).

For persona testing: data/personas/{persona}/crm/contacts.json.
"""

import difflib
import json
import os
import re
import threading
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from core.persona import persona_data_dir

_CRM_LOCK = threading.Lock()

# Above this similarity to the user's own email/phone (but not an exact match, which is
# refused outright) a captured value is flagged rather than blocked — a voice
# transcription near-miss ("diamond.mic@gmail.com" for "diamond.mike@gmail.com") is the
# recorded failure mode, but a genuinely different, similar-looking address (a family
# member, a colleague on the same domain) is a real case a hard block would wrongly
# refuse. difflib.SequenceMatcher, same tool tools/scheduling.py already uses for
# near-duplicate title matching — evidence for the agent to weigh, not a verdict.
_OWN_IDENTITY_SIMILARITY_THRESHOLD = 0.80

# [DB-0815-07] Same shape of check as _OWN_IDENTITY_SIMILARITY_THRESHOLD, applied to
# *other* contacts' names instead of the user's own identity, so a new record whose
# name closely resembles an existing one is surfaced before write_contact creates a
# duplicate — the recorded case: "Eva" and "Iva Diamond" were the same family member,
# corrected by the user five separate times because nothing ever merged the records.
# Set with tools/scheduling.py's _TITLE_SIMILARITY_THRESHOLD (0.6) as precedent rather
# than a fresh guess: whole-string "eva"/"iva diamond" scores low (0.29, different
# lengths), but the first-token comparison _name_similarity() also takes ("eva"/"iva"
# = 0.67, "kathaleen"/"kathleen" = 0.94) clears 0.6 for both of the recorded
# speech-to-text near-misses without it being tuned to that pair specifically.
_NAME_SIMILARITY_THRESHOLD = 0.6

# A short form is a PREFIX, not a typo, and edit distance cannot see the difference.
# "Jon"/"Jonathan" scores 0.545 and "Jon"/"Jonathan Whitfield" 0.545 — both under the
# 0.6 bar above, so the very case that motivated this check slipped through it, while
# "Jonathan"/"Jonathan Whitfield" (1.00) was already caught. Raising the threshold is
# the wrong lever: it would start matching genuinely different people, which is the
# opposite and worse failure. So a prefix is scored as its own signal instead.
#
# 0.75 deliberately: clears the candidate bar, stays below an exact match, so a prefix
# hit can never be mistaken for a certain one. Minimum length 3 because two characters
# prefix far too many names ("Jo" reaches Joanna, John, Josh, Jordan) to be evidence
# of anything.
_PREFIX_SIMILARITY = 0.75
_MIN_PREFIX_LEN = 3

# RFC 2606 reserves these for documentation/testing — a real person's email is never
# on one of them. "example.com" turning up in a contact record (the recorded case:
# tools/crm.py accepted and persisted "eva@example.com") is not a mistyped real
# address, it is a model-invented placeholder that slipped past a schema with no
# opinion on domain validity. Reserved TLDs from the RFC; the explicit domains cover
# the "example.com/.net/.org used under a normal-looking TLD" case the TLD check alone
# would miss.
_PLACEHOLDER_EMAIL_DOMAINS = {
    "example.com", "example.net", "example.org", "example.edu",
    "test", "invalid", "localhost",
}
_RESERVED_EMAIL_TLDS = {"test", "example", "invalid", "localhost"}

# [DB-0815-06] Same refusal as the email guard above, extended to phone, address,
# social handle, and name — the recorded pattern is one root cause (a field that
# looks required gets filled with something plausible rather than left out), not
# four separate ones. Each registry below is scoped to values that are *known*
# placeholders — reserved ranges, textbook example strings, literal stock names —
# never to "looks fake" heuristics, because a false positive here blocks real
# input. Where a value could plausibly be real (e.g. "123 Main Street" with a real
# city attached, "Doe" as a real surname), it is deliberately left uncaught; see
# each _is_placeholder_* docstring for the specific line it draws.

# NANP reserves the 555 exchange with subscriber numbers 0100-0199 nationwide for
# fiction/directory-assistance use — no real subscriber is ever issued one of
# these, regardless of area code. Ofcom reserves 07700 900000-900999 the same way
# for UK film/TV/drama use (a real UK mobile is 07700 8xxxxx, 07700 1xxxxx, etc. —
# never the 900xxx block). Matched against normalized digits so formatting
# (spaces, dashes, brackets, a +/00 international prefix) doesn't hide the match.
_NANP_FICTIONAL_RE = re.compile(r"55501\d\d$")
_UK_DRAMA_RE = re.compile(r"7700900\d{3}$")
_PLACEHOLDER_PHONE_EXACT_DIGITS = {"1234567890", "0123456789"}

# Bare textbook street addresses with nothing else attached — a real address this
# short and this exact ("123 Main Street", full stop) is the specific shape a
# model reaches for; the same street number+name followed by a real city/state
# does not match this set and is not caught (see _is_placeholder_address).
_PLACEHOLDER_ADDRESS_EXACT = {
    "123 main st", "123 main street",
    "1234 elm st", "1234 elm street",
}

# Generic placeholder handles used in documentation/examples — never issued as a
# real platform username, so an exact match (case-insensitive, leading @ ignored)
# carries no false-positive risk the way a "looks fake" heuristic would.
_PLACEHOLDER_SOCIAL_HANDLES = {"username", "handle", "example", "yourname", "yourhandle"}

# The two canonical stand-in names for "a person" in English-language documents
# and forms. Matched only against the *full* name (or first+last combined) so a
# real surname "Doe" paired with any other first name still passes.
_PLACEHOLDER_NAMES = {"john doe", "jane doe"}

_ROOT = Path(__file__).parent.parent

# Frequency preference → days before overdue
_FREQUENCY_DAYS: dict[str, int | None] = {
    "daily": 1,
    "weekly": 7,
    "monthly": 30,
    "quarterly": 90,
    "as_needed": None,
}


def _crm_path() -> Path:
    """Return the path to this persona's contacts.json."""
    return persona_data_dir() / "crm" / "contacts.json"


def _load_contacts() -> list[dict]:
    """Read contacts.json; return empty list if file does not exist."""
    path = _crm_path()
    if not path.exists():
        return []
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else []


def _save_contacts(contacts: list[dict]) -> None:
    """Write contacts list atomically."""
    path = _crm_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(contacts, f, indent=2)
    os.chmod(path, 0o600)


def _crm_archive_dir() -> Path:
    """Where merged-away contact records live — never deleted, resolvable by id via
    the merged_into pointer each carries. Same layout tools/wisdom.py already uses:
    persona_data_dir()/archive/<domain>, one JSON file per archived record."""
    return persona_data_dir() / "archive" / "crm"


def _load_archived_record(contact_id: str) -> dict | None:
    """Look up an archived (merged-away) record by its original id."""
    archive_dir = _crm_archive_dir()
    if not archive_dir.exists():
        return None
    for path in archive_dir.glob(f"{contact_id}_*.json"):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            continue
    return None


def _archive_stamp() -> str:
    """Second-resolution timestamp for archive filenames. Date alone is not enough
    for the snapshot files below: two merges of the same pair on the same day would
    land on one filename, and the second would overwrite the first — a deletion, in
    a subsystem whose entire premise is that nothing is deleted."""
    return datetime.now().strftime("%Y-%m-%dT%H-%M-%S")


def _write_pre_merge_snapshot(keep_record: dict, keep_id: str, merge_id: str) -> Path:
    """
    [DB-0822-03] Store what `keep_id` looked like immediately before `merge_id` was
    folded into it, so the merge can be reversed.

    Filed under a `premerge_` prefix deliberately. `_load_archived_record()` finds an
    archived record by globbing `{contact_id}_*.json`, and a snapshot named that way
    would be returned in place of a genuine archived record — silently breaking the
    chained-merge walk in `_resolve_merged()`, where an id can be both a survivor and
    a later loser. The prefix keeps the two file families disjoint.

    It also carries no `merged_into` key, which is what keeps it out of the archive
    scans in `_find_by_name()` and `search_contacts()`: both skip any archived record
    without one. A snapshot is a previous state of a *live* contact, not a redirect,
    and must never be followed as one.
    """
    archive_dir = _crm_archive_dir()
    archive_dir.mkdir(parents=True, exist_ok=True)
    snapshot = json.loads(json.dumps(keep_record))
    snapshot["record_type"] = "pre_merge_snapshot"
    snapshot["snapshot_of_merge"] = {"keep_id": keep_id, "merge_id": merge_id}
    snapshot["archived"] = date.today().isoformat()
    path = archive_dir / f"premerge_{merge_id}_{_archive_stamp()}.json"
    with open(path, "w") as f:
        json.dump(snapshot, f, indent=2)
    os.chmod(path, 0o600)
    return path


def _load_pre_merge_snapshot(merge_id: str) -> dict | None:
    """The most recent pre-merge snapshot for `merge_id`, or None if there is none —
    which is the expected answer for every merge made before 2026-08-22. Most recent
    rather than first: a pair can be merged, unmerged and merged again, and the undo
    has to target the merge that is currently in effect."""
    archive_dir = _crm_archive_dir()
    if not archive_dir.exists():
        return None
    paths = sorted(archive_dir.glob(f"premerge_{merge_id}_*.json"))
    for path in reversed(paths):
        try:
            return json.loads(path.read_text())
        except (OSError, ValueError):
            continue
    return None


def _retire_merge_archives(merge_id: str, keep_id: str) -> None:
    """Rename the archive files describing a now-reversed merge out of the way.

    Renamed, never deleted — archive-on-merge applies to the undo as much as to the
    merge. The rename does two jobs: it stops the loser's `merged_into` pointer
    resolving (that id is a live contact again, so the pointer would be a lie), and
    it stops a second `unmerge_contacts` call finding a snapshot for a merge that has
    already been reversed."""
    archive_dir = _crm_archive_dir()
    if not archive_dir.exists():
        return
    stamp = _archive_stamp()
    targets = list(archive_dir.glob(f"{merge_id}_*.json"))
    targets += list(archive_dir.glob(f"premerge_{merge_id}_*.json"))
    for path in targets:
        try:
            path.rename(archive_dir / f"reverted_{stamp}_{path.name}")
        except OSError:
            # A failed rename must not undo the restore that already succeeded. The
            # cost is a stale pointer, which read_contact resolves live-record-first
            # anyway, not lost data.
            continue


def _merge_confirmation_description(keep: dict, merge: dict) -> str:
    """
    [DB-0822-03] What the user reads before approving a merge.

    Built from `_disambiguation_entry()` on both sides rather than from the ids the
    caller supplied, because a wrong id and a right id look exactly alike. The
    recorded failure is a merge into the wrong one of three same-named people; the
    only thing that would have caught it is seeing, in the sentence being approved,
    that the record being kept had a spouse and a dinner logged three weeks ago and
    the one being folded in was met at the gym.

    Stands alone deliberately — `tools/confirm.py`'s `request()` requires it, and the
    user may see this without the conversation around it.
    """
    def _lines(entry: dict) -> str:
        skip = {"id", "name"}
        labels = {
            "last_name": "surname", "relationship_type": "relationship",
            "occupation": "occupation", "employer": "employer",
            "how_met": "how you met", "nickname": "also called",
            "spouse_name": "spouse", "last_contact": "last spoken to",
            "tags": "tags",
        }
        out = []
        for key, value in entry.items():
            if key in skip:
                continue
            if isinstance(value, list):
                value = ", ".join(str(v) for v in value)
            out.append(f"    {labels.get(key, key)}: {value}")
        return "\n".join(out) or "    (no other details on record)"

    keep_entry = _disambiguation_entry(keep)
    merge_entry = _disambiguation_entry(merge)
    keep_log = len(keep.get("interaction_log") or [])
    merge_log = len(merge.get("interaction_log") or [])

    return (
        f"Merge two contacts into one?\n\n"
        f"KEEPING — '{keep_entry.get('name', '')}' ({keep_entry.get('id', '')}), "
        f"{keep_log} logged interaction(s):\n"
        f"{_lines(keep_entry)}\n\n"
        f"FOLDING IN AND ARCHIVING — '{merge_entry.get('name', '')}' "
        f"({merge_entry.get('id', '')}), {merge_log} logged interaction(s):\n"
        f"{_lines(merge_entry)}\n\n"
        f"Approve only if these are the SAME person. The kept record takes on the "
        f"other's details where its own are blank, so approving the wrong pair writes "
        f"one person's history onto another. Decline if they are different people, or "
        f"if the wrong one is being kept — nothing will be changed."
    )


def _resolve_merged(contacts: list[dict], contact_id: str) -> dict | None:
    """Follow merged_into pointers from an archived id to the live record it
    survives as. Handles a chained merge (A merged into B, B later merged into C)
    by following the chain rather than stopping at the first hop."""
    seen: set[str] = set()
    current = contact_id
    while True:
        archived = _load_archived_record(current)
        target_id = (archived or {}).get("merged_into")
        if not target_id or target_id in seen:
            return None
        seen.add(target_id)
        for c in contacts:
            if c.get("id") == target_id:
                return c
        current = target_id  # target itself was later merged again — keep following


def _contact_matches(contact: dict, needle: str) -> bool:
    """Substring match across the same fields search_contacts() checks. Shared so
    an archived (merged-away) record can be tested with the same rule a live one
    is, when resolving old names via the CRM archive."""
    scalar_fields = [
        "name", "first_name", "last_name", "nickname",
        "spouse_name", "education", "occupation", "employer",
        "how_met", "notes",
    ]
    if any(needle in str(contact.get(f, "")).lower() for f in scalar_fields):
        return True
    if any(needle in s.lower() for s in contact.get("referred_to_as", [])):
        return True
    if any(needle in s.lower() for s in contact.get("kids_names", [])):
        return True
    if any(needle in t.lower() for t in contact.get("tags", [])):
        return True
    return False


def _find_by_name(contacts: list[dict], name: str) -> list[dict]:
    """Case-insensitive substring match on name field, plus any contact whose
    *old* (merged-away) name matches — so a correction ("Eva" -> "Iva Diamond")
    does not strand lookups still made under the name that was corrected away."""
    needle = name.lower()
    matches = [c for c in contacts if needle in c.get("name", "").lower()]

    archive_dir = _crm_archive_dir()
    if archive_dir.exists():
        seen_ids = {m["id"] for m in matches}
        for path in sorted(archive_dir.glob("*.json")):
            try:
                archived = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            target_id = archived.get("merged_into")
            if not target_id or target_id in seen_ids:
                continue
            if needle not in str(archived.get("name", "")).lower():
                continue
            for c in contacts:
                if c.get("id") == target_id:
                    matches.append(c)
                    seen_ids.add(target_id)
                    break
    return matches


def _is_placeholder_email_domain(domain: str) -> bool:
    """True for RFC 2606 reserved / documentation-only domains — never a real
    person's address, so a value on one of these is refused rather than stored."""
    domain = domain.strip(".")
    if not domain:
        return False
    if domain in _PLACEHOLDER_EMAIL_DOMAINS:
        return True
    return domain.rsplit(".", 1)[-1] in _RESERVED_EMAIL_TLDS


def _normalize_phone_digits(phone: str) -> str:
    """Strip spaces/dashes/dots/brackets, then a leading +/00 international
    prefix, leaving only digits — so '555 010 0' and '+44 (0)7700 900123' match
    the same way their unformatted equivalents would."""
    s = re.sub(r"[\s\-.()]", "", phone or "")
    if s.startswith("+"):
        s = s[1:]
    elif s.startswith("00"):
        s = s[2:]
    return re.sub(r"\D", "", s)


def _is_placeholder_phone(phone: str) -> str | None:
    """Reason string if `phone` is a known fictional/reserved number or is too
    short to be a phone number at all, else None. Deliberately narrow: a real UK
    mobile outside 07700 900xxx (e.g. 07700 800123) and a real NANP number
    outside the 555-0100/0199 block are never flagged — only the specific ranges
    reserved for fiction/documentation are.

    [DB-0822-03] The stub case. A *supplied but meaningless* value — the recorded
    one is the literal string "ph", which reached a real friend's record through a
    merge — carried no digits at all and so returned None here, because the guard
    only ever asked "is this a reserved range?" and never "is this a number?".
    Two rules, both keyed on the normalized digit count:

      * zero digits — pure letters/punctuation ("ph", "n/a", "tbc"). Nothing that
        could be dialled is present.
      * one to four digits — shorter than any real subscriber number, including
        short codes (5 digits at minimum) and UK/NANP extensions written alone.

    An **absent or empty** value is still None: leaving a field out is correct
    behaviour and must never be flagged. The floor is 5 rather than something
    higher because an internal extension ("2481") is a plausible thing a user
    dictates, and a threshold that starts refusing real fragments would push the
    agent to invent a fuller-looking number instead — the exact failure this
    whole registry exists to stop.
    """
    raw = (phone or "").strip()
    if not raw:
        return None
    digits = _normalize_phone_digits(phone)
    if not digits:
        return (
            "no digits at all — a stub or note left in the phone field rather "
            "than a number"
        )
    if len(digits) < 5:
        return (
            f"only {len(digits)} digit{'s' if len(digits) != 1 else ''} — too "
            f"short to be a phone number"
        )
    if len(digits) >= 7 and _NANP_FICTIONAL_RE.search(digits):
        return "NANP fictional/directory-assistance range (555-0100 to 555-0199)"
    if _UK_DRAMA_RE.search(digits):
        return "UK Ofcom drama/fiction range (07700 900xxx)"
    if digits in _PLACEHOLDER_PHONE_EXACT_DIGITS:
        return "a textbook sequential placeholder number"
    if len(digits) >= 4 and re.fullmatch(r"0+", digits):
        return "an all-zero placeholder number"
    return None


def _normalize_address(address: str) -> str:
    s = (address or "").strip().casefold()
    s = re.sub(r"[.,]", "", s)
    return re.sub(r"\s+", " ", s)


def _is_placeholder_address(address: str) -> str | None:
    """Reason string if `address` is a known placeholder, else None. 'Anytown' is
    caught wherever it appears (it is never a real place name, so no legitimate
    address can contain it as a whole word). The bare street strings are only
    caught as an *exact, whole-field* match — '123 Main Street' with a real city
    and state attached does not match this set and is not flagged, because that
    combination is a plausible real address, not a known placeholder."""
    norm = _normalize_address(address)
    if not norm:
        return None
    if re.search(r"\banytown\b", norm):
        return "'Anytown' is a generic placeholder city name, never a real one"
    if norm in _PLACEHOLDER_ADDRESS_EXACT:
        return "a textbook placeholder street address with no real city/state attached"
    return None


def _is_placeholder_social_handle(handle: str) -> str | None:
    """Reason string if `handle` is a generic placeholder handle (leading @
    ignored, case-insensitive), else None."""
    norm = (handle or "").strip().casefold().lstrip("@")
    if norm in _PLACEHOLDER_SOCIAL_HANDLES:
        return f"'@{norm}' is a generic placeholder handle, not a real one"
    return None


def _is_placeholder_name(name: str) -> str | None:
    """Reason string if `name` is a canonical stand-in name ('John Doe' /
    'Jane Doe'), else None. Only the full name is checked — a real surname 'Doe'
    on its own, or paired with a different first name, is not flagged."""
    norm = re.sub(r"\s+", " ", (name or "").strip().casefold())
    if norm in _PLACEHOLDER_NAMES:
        return "a well-known stand-in name for 'a person', not a captured one"
    return None


def _name_similarity(a: str, b: str) -> float:
    """Best of whole-string and first-token similarity. Whole-string alone misses
    a name later expanded with a surname ("Iva" vs "Iva Diamond" scores 0.29);
    first-token alone misses a multi-word name matched against a single-word one
    the other direction. Taking the max of both catches either shape without
    either comparison mode hiding the other's hit."""
    a, b = (a or "").strip().lower(), (b or "").strip().lower()
    if not a or not b:
        return 0.0
    whole = difflib.SequenceMatcher(None, a, b).ratio()
    a_first, b_first = a.split()[0], b.split()[0]
    first = difflib.SequenceMatcher(None, a_first, b_first).ratio()
    # Prefix signal — see _PREFIX_SIMILARITY. Compared on first tokens so that
    # "Jon" reaches "Jonathan Whitfield" as well as bare "Jonathan"; edit distance
    # scores both at 0.545 and would surface neither.
    short, long = sorted((a_first, b_first), key=len)
    prefix = (_PREFIX_SIMILARITY
              if len(short) >= _MIN_PREFIX_LEN and long.startswith(short)
              else 0.0)
    return max(whole, first, prefix)


def _disambiguation_entry(contact: dict) -> dict:
    """
    The smallest set of fields that tells two same-named people apart, for asking the
    user which one they meant.

    Deliberately not the whole record. The point is to let the agent ask a natural
    question — "Bill Thompson from work, or Bill the plumber?" — and a full record
    invites it to answer from the data instead of asking. Only populated fields are
    returned, so a sparse contact yields a short entry rather than a wall of empty keys.

    [DB-0822-03] `spouse_name` and `last_contact` were added on 2026-08-22. Three
    contacts named some spelling of "Steven" were told apart, in the record, by
    exactly those two fields — one had a spouse and a dinner logged three weeks
    earlier, the other two were gym acquaintances with neither. The entry the user
    would have been shown carried neither field, so the one detail that made the
    answer obvious was the one detail missing from the question.
    """
    handle = {"id": contact.get("id", ""), "name": contact.get("name", "")}
    for field in ("last_name", "relationship_type", "occupation", "employer",
                  "how_met", "nickname", "spouse_name", "last_contact"):
        value = contact.get(field)
        if value:
            handle[field] = value
    tags = contact.get("tags") or []
    if tags:
        handle["tags"] = tags
    return handle


def _ambiguous_match(name: str, matches: list[dict], action: str) -> str:
    """
    The response when a name reaches more than one person.

    **No record is returned and nothing is written.** The previous behaviour picked
    `matches[0]` and appended a note saying so — which reads to a model as an answer
    with a caveat, not as a question it must ask. The observed shapes that motivates
    this: four people can share the spoken name "Bill" (a colleague, a tradesman, a
    friend named William, and that friend's father), and the tool cannot rank them.
    Returning one of them means a note lands on the wrong person's record or a message
    is drafted about the wrong person — both silent, both things the user only finds
    out later.

    Asking is the correct answer here and the agents do it well when they know there is
    something to ask about. This makes sure they know.
    """
    return json.dumps({
        "ambiguous": True,
        "query": name,
        "matches": [_disambiguation_entry(m) for m in matches],
        "_instruction": (
            f"{len(matches)} contacts match '{name}', so no record was returned and "
            f"nothing was {action}. Do not guess and do not pick the first. Ask the user "
            "which one they mean, using whatever distinguishes them in the matches above "
            "(surname, how you know them, what they do). Then repeat this call with that "
            f"contact_id AND name='{name}' — passing the name back alongside the id is what "
            "records the answer, so this question is not asked again next time."
        ),
    }, indent=2)


# ---------------------------------------------------------------------------
# Remembering a disambiguation once the user has made it  [DB-0818-05]
# ---------------------------------------------------------------------------
#
# `_ambiguous_match` above stopped the tool writing to the wrong Bill. It did not
# stop it asking about the same Bill a second time, a third time, and every time
# after — the user answers the question, the answer is used for exactly one tool
# call, and then it is gone. The four Bills are the hard case precisely because
# they are sparse: nothing in the records will ever rank them, so the only thing
# that can settle "Bill" is the user's own past answer.
#
# So the answer is stored. The store is a separate file from contacts.json:
# a spoken-reference resolution is a fact about how *this user* talks, not a
# field of any one person's record, and keeping it out of contacts.json means an
# existing persona's data file needs no migration and no new key.
#
# Two rules keep this from becoming the failure it exists to prevent:
#
#   1. **Only a genuine answer is stored.** A resolution is recorded only when
#      the name was ambiguous at the moment it was made — more than one live
#      contact matched, and the id supplied was one of them. Recording every
#      name→id pair would mean that "Bill", stored when there was only one Bill,
#      would later silently swallow a second Bill added months afterwards. That
#      is the exact wrong-person write `_ambiguous_match` exists to refuse.
#   2. **Nothing is deleted.** A correction pushes the previous resolution into
#      `history` with a `superseded` stamp, matching the archive-on-merge rule
#      the CRM already follows for records.
#
# Resolutions are followed through merge_contacts at read time via
# `_resolve_merged`, so folding one Bill into another does not strand the answer
# and no rewrite of this file is needed when a merge happens.

_RESOLUTION_LOCK = threading.Lock()

# Lock ordering: this is only ever acquired on its own. Callers holding
# _CRM_LOCK must release it before recording a resolution — see log_interaction.

_RESOLUTIONS_VERSION = 1


def _resolutions_path() -> Path:
    """Where this persona's remembered name→contact resolutions live."""
    return persona_data_dir() / "crm" / "name_resolutions.json"


def _load_resolutions() -> dict:
    """
    Read the resolution store, tolerating every shape a file that has never
    existed can take.

    Returns `{}` for missing, empty, malformed or unexpectedly-shaped content
    rather than raising: a corrupt memory of who "Bill" is must degrade to
    asking the question again, never to a crashed contact lookup.
    """
    path = _resolutions_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(data, dict):
        return {}
    resolutions = data.get("resolutions")
    return resolutions if isinstance(resolutions, dict) else {}


def _save_resolutions(resolutions: dict) -> None:
    """Write the resolution store with the same 0600 permissions as contacts.json —
    who the user means by a first name is personal data."""
    path = _resolutions_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"version": _RESOLUTIONS_VERSION, "resolutions": resolutions}
    with open(path, "w") as f:
        json.dump(payload, f, indent=2)
    os.chmod(path, 0o600)


def _normalize_reference(name: str) -> str:
    """
    The key a spoken reference is stored under.

    Lowercased, whitespace-collapsed, and stripped of trailing punctuation, so
    "Bill", "bill" and "Bill?" are one key. Deliberately nothing cleverer: a
    stored answer is applied only on an exact key match, so "Bill" never
    resolves "Bill Thompson" (which has its own, usually unambiguous, lookup)
    and a fuzzy key can never hand back a person the user did not name.
    """
    return re.sub(r"\s+", " ", name.strip().strip(".,!?;:")).lower()


def _resolution_target(contacts: list[dict], entry: dict,
                       candidate_ids: set[str]) -> str:
    """The live contact id a stored resolution points at, or "" if it no longer
    points at one of `candidate_ids`. Follows merge_contacts."""
    contact_id = entry.get("contact_id", "") if isinstance(entry, dict) else ""
    if not contact_id:
        return ""
    if contact_id in candidate_ids:
        return contact_id
    merged = _resolve_merged(contacts, contact_id)
    if merged is not None and merged.get("id") in candidate_ids:
        return merged["id"]
    return ""


def _apply_resolution(contacts: list[dict], name: str,
                      matches: list[dict]) -> dict | None:
    """
    The contact a previous answer settled this reference on, or None.

    Returns None — and so falls through to asking again — whenever the stored
    answer no longer fits: the person was deleted, or the set of people the name
    now reaches has changed such that the remembered one is not among them. The
    fail-open direction is deliberate; a remembered answer must never be the
    reason a note lands on the wrong person.
    """
    key = _normalize_reference(name)
    if not key:
        return None
    entry = _load_resolutions().get(key)
    if not isinstance(entry, dict):
        return None
    candidate_ids = {m.get("id", "") for m in matches}
    target_id = _resolution_target(contacts, entry, candidate_ids)
    if not target_id:
        return None
    for contact in matches:
        if contact.get("id") == target_id:
            return contact
    return None


def _record_resolution(name: str, contact_id: str, source: str) -> bool:
    """
    Remember that the user, asked which `name` they meant, said this one.

    Recorded only when the reference was genuinely ambiguous and the id is one
    of the people it reached — see the two rules above. Returns True if
    something was written, so callers and tests can tell a stored answer from a
    silently skipped one.

    Never raises. A CRM read or write that succeeded must not fail afterwards
    because a memory of it could not be saved.
    """
    key = _normalize_reference(name)
    if not key or not contact_id:
        return False
    try:
        contacts = _load_contacts()
        matches = _find_by_name(contacts, name)
        if len(matches) < 2:
            return False
        if contact_id not in {m.get("id", "") for m in matches}:
            # An id that was merged away is still a valid answer — store the
            # record it survives as, not the pointer.
            merged = _resolve_merged(contacts, contact_id)
            if merged is None or merged.get("id") not in {m.get("id", "") for m in matches}:
                return False
            contact_id = merged["id"]

        stamp = datetime.now().isoformat(timespec="seconds")
        with _RESOLUTION_LOCK:
            resolutions = _load_resolutions()
            previous = resolutions.get(key)
            if isinstance(previous, dict) and previous.get("contact_id") == contact_id:
                # Same answer again — refresh when it was last confirmed, but do
                # not manufacture a history entry for a correction that did not
                # happen.
                previous["confirmed"] = stamp
                resolutions[key] = previous
                _save_resolutions(resolutions)
                return True

            history = []
            if isinstance(previous, dict):
                prior_history = previous.get("history")
                if isinstance(prior_history, list):
                    history = prior_history
                superseded = {k: v for k, v in previous.items() if k != "history"}
                superseded["superseded"] = stamp
                history = history + [superseded]

            entry = {
                "contact_id": contact_id,
                "recorded": stamp,
                "confirmed": stamp,
                "source": source,
            }
            if history:
                entry["history"] = history
            resolutions[key] = entry
            _save_resolutions(resolutions)
        return True
    except Exception:
        return False


def _resolution_note(name: str, contact: dict) -> str:
    """What a remembered answer tells the calling agent — including how the user
    overrides it, which is the only route by which a wrong memory gets fixed."""
    return (
        f"'{name}' was resolved to this contact because the user previously "
        f"answered that question. Do not re-ask and do not mention the lookup. "
        f"If the user indicates a different person, repeat the call with the "
        f"corrected contact_id and name='{name}' to replace the stored answer."
    )


def _dedup_candidates(contacts: list[dict], name: str) -> list[dict]:
    """Existing contacts whose name/first_name/nickname/referred_to_as comes close
    enough to `name` to be worth surfacing before a new record is created —
    evidence for the calling agent to weigh, not a verdict: write_contact still
    creates the record and returns this alongside the new id, same non-blocking
    shape as the own-identity email/phone warning above and
    tools/scheduling.py's near_duplicate_candidates."""
    if not name:
        return []
    candidates = []
    for c in contacts:
        variants = [c.get("name", ""), c.get("first_name", ""), c.get("nickname", "")]
        variants += list(c.get("referred_to_as") or [])
        best = max((_name_similarity(name, v) for v in variants if v), default=0.0)
        if best >= _NAME_SIMILARITY_THRESHOLD:
            candidates.append({"id": c["id"], "name": c.get("name", ""), "similarity": round(best, 2)})
    candidates.sort(key=lambda x: -x["similarity"])
    return candidates[:5]


# ---------------------------------------------------------------------------
# Public tool functions
# ---------------------------------------------------------------------------

def write_contact(
    name: str,
    first_name: str = "",
    last_name: str = "",
    nickname: str = "",
    referred_to_as: list[str] | None = None,
    primary_contact_type: str = "",
    relationship_type: str = "",
    relationship_quality: str = "",
    last_contact: str = "",
    contact_frequency_preference: str = "",
    spouse_name: str = "",
    kids_names: list[str] | None = None,
    education: str = "",
    occupation: str = "",
    employer: str = "",
    how_met: str = "",
    timezone: str = "",
    contact_info: dict | None = None,
    important_dates: list[dict] | None = None,
    tags: list[str] | None = None,
    notes: str = "",
    tone_shape: str = "",
    contact_id: str = "",
    confirm_token: str = "",
    _bulk: bool = False,
) -> str:
    """
    Create or update a contact record.

    If contact_id is provided and matches an existing record, that record is
    updated with any non-empty fields supplied. If contact_id is empty, a new
    contact is created.

    Returns the contact ID (new or existing).

    Refuses if `contact_info` would attribute the user's own email or phone to this
    contact — the recorded failure mode this guards against is a captured detail (a
    dictated email, an inferred number) landing on the wrong record. Checked against
    `profile.yaml`, in Python rather than relying on the agent noticing — being told not
    to is not being prevented, the same reasoning `tools/mail.py`'s recipient check and
    `tools/agent_config.py`'s `_GUARDED_KEYS` already apply elsewhere.

    Also refuses known-placeholder values in email, phone, address, social handle,
    and name — a real address/number/name is never one of these, so a value there
    is an invented placeholder, not a captured one. Covers: an email on a
    reserved/placeholder domain (example.com, .test, .invalid, localhost, ...); a
    phone in the NANP 555-0100/0199 or UK Ofcom 07700 900xxx fictional ranges, or a
    sequential/all-zero number; a bare textbook street address ('123 Main Street'
    with nothing else) or one containing 'Anytown'; a generic social handle
    ('@username', '@handle', ...); or the name 'John Doe'/'Jane Doe'. Each check is
    scoped to known placeholders only — a real address with a real city, a real
    UK/NANP number outside those exact ranges, and a real surname 'Doe' all still
    save. [DB-0815-06]: a fabricated address ('eva@example.com') was previously
    accepted and persisted.

    When creating a new contact (contact_id empty), also checks `name` against
    existing contacts and, if a close match is found, returns it as evidence
    alongside the new id rather than refusing or silently merging — see
    `_dedup_candidates`. [DB-0815-07]: three duplicate-person records were found
    with no dedup on the write path.
    """
    from tools.confirm import consume, request

    today = date.today().isoformat()

    # Arguments as the confirmation will fingerprint them. Built from the supplied
    # values only, deterministically, so the replay through confirm.execute() rebuilds
    # an identical dict — anything else is refused by consume(), correctly.
    # confirm_token is excluded: it is not part of the action. contact_id IS included
    # (2026-08-26) — the update path is gated too now, and an approval to rename one
    # record must not be spendable on another. It is empty on the creation path, so
    # `if v` drops it there and every pre-existing creation fingerprint is unchanged.
    _gate_args = {k: v for k, v in (
        ("contact_id", contact_id),
        ("name", name), ("first_name", first_name), ("last_name", last_name),
        ("nickname", nickname), ("referred_to_as", referred_to_as),
        ("primary_contact_type", primary_contact_type),
        ("relationship_type", relationship_type),
        ("relationship_quality", relationship_quality),
        ("last_contact", last_contact),
        ("contact_frequency_preference", contact_frequency_preference),
        ("spouse_name", spouse_name), ("kids_names", kids_names),
        ("education", education), ("occupation", occupation),
        ("employer", employer), ("how_met", how_met), ("timezone", timezone),
        ("contact_info", contact_info), ("important_dates", important_dates),
        ("tags", tags), ("notes", notes), ("tone_shape", tone_shape),
    ) if v}

    _approved = False
    if confirm_token:
        _ok, _reason = consume(confirm_token, "write_contact", _gate_args)
        if not _ok:
            # Say so rather than silently reopening a fresh request, which would read
            # to the model as a retry loop. Same shape as send_email's rejection.
            return f"Error: not saved. {_reason}"
        _approved = True

    # [DB-0815-06] Same refusal shape as the email domain check below, applied to
    # name: a canonical stand-in ("John Doe"/"Jane Doe") reached for when a name
    # looks required is refused rather than persisted.
    for _candidate_name in (name, f"{first_name} {last_name}".strip()):
        if _candidate_name:
            _name_reason = _is_placeholder_name(_candidate_name)
            if _name_reason:
                return (
                    f"Error: not saved. '{_candidate_name}' looks like a placeholder "
                    f"name ({_name_reason}) rather than a real contact. Ask the user "
                    f"for the real name, or omit the contact rather than inventing one."
                )

    if contact_info:
        given_email = str(contact_info.get("email", "")).strip().lower()
        if given_email and "@" in given_email:
            domain = given_email.rsplit("@", 1)[-1]
            if _is_placeholder_email_domain(domain):
                return (
                    f"Error: not saved. '{given_email}' uses a reserved/placeholder "
                    f"domain ('{domain}') — example.com and similar RFC 2606 domains "
                    f"are never real addresses; this looks like an invented value, not "
                    f"a captured one. Ask the user for the real address, or leave "
                    f"contact_info without an email until you have one."
                )

        given_phone_raw = str(contact_info.get("phone", "")).strip()
        if given_phone_raw:
            _phone_reason = _is_placeholder_phone(given_phone_raw)
            if _phone_reason:
                return (
                    f"Error: not saved. '{given_phone_raw}' falls in a known "
                    f"placeholder/fictional number range ({_phone_reason}) — this "
                    f"looks like an invented value, not a captured one. Ask the user "
                    f"for the real number, or leave contact_info without a phone "
                    f"until you have one."
                )

        given_address_raw = str(contact_info.get("address", "")).strip()
        if given_address_raw:
            _address_reason = _is_placeholder_address(given_address_raw)
            if _address_reason:
                return (
                    f"Error: not saved. '{given_address_raw}' looks like a "
                    f"placeholder address ({_address_reason}) rather than a "
                    f"captured one. Ask the user for the real address, or leave "
                    f"contact_info without an address until you have one."
                )

        given_social = contact_info.get("social")
        if isinstance(given_social, dict):
            for _platform, _handle in given_social.items():
                _handle_reason = _is_placeholder_social_handle(str(_handle))
                if _handle_reason:
                    return (
                        f"Error: not saved. contact_info.social['{_platform}'] = "
                        f"'{_handle}' — {_handle_reason} rather than a captured one. "
                        f"Ask the user for the real handle, or leave that platform "
                        f"out of social until you have one."
                    )

        from tools.profile import _load as _load_profile
        try:
            own = _load_profile().get("contact") or {}
        except (OSError, ValueError):
            own = {}
        own_email = str(own.get("email", "")).strip().lower()
        own_phone = str(own.get("phone", "")).strip().lower()
        given_phone = str(contact_info.get("phone", "")).strip().lower()
        if own_email and given_email == own_email:
            return (
                f"Error: not saved. '{given_email}' is the user's own email, not this "
                f"contact's — this looks like a misattribution. Confirm the correct "
                f"address with the user before retrying."
            )
        if own_phone and given_phone == own_phone:
            return (
                f"Error: not saved. '{given_phone}' is the user's own phone number, not "
                f"this contact's — this looks like a misattribution. Confirm the correct "
                f"number with the user before retrying."
            )

    # Not an exact match, but close enough to be a plausible transcription error rather
    # than a coincidence — saved (a hard block here would refuse legitimate similar-
    # looking contacts, e.g. a family member on the same email domain), but flagged so
    # the calling agent surfaces it instead of treating the capture as final.
    _warning = ""
    if contact_info:
        if own_email and given_email and given_email != own_email:
            ratio = difflib.SequenceMatcher(None, given_email, own_email).ratio()
            if ratio >= _OWN_IDENTITY_SIMILARITY_THRESHOLD:
                _warning = (
                    f"'{given_email}' closely resembles the user's own email "
                    f"('{own_email}') — likely a mis-transcription (common with voice "
                    f"input on proper nouns/addresses), not necessarily wrong. Confirm "
                    f"with the user before treating it as final."
                )
        if not _warning and own_phone and given_phone and given_phone != own_phone:
            ratio = difflib.SequenceMatcher(None, given_phone, own_phone).ratio()
            if ratio >= _OWN_IDENTITY_SIMILARITY_THRESHOLD:
                _warning = (
                    f"'{given_phone}' closely resembles the user's own phone number "
                    f"('{own_phone}') — likely a transcription error, not necessarily "
                    f"wrong. Confirm with the user before treating it as final."
                )

    # String fields that follow the same update pattern
    _str_fields = [
        ("name", name),
        ("first_name", first_name),
        ("last_name", last_name),
        ("nickname", nickname),
        ("primary_contact_type", primary_contact_type),
        ("relationship_type", relationship_type),
        ("relationship_quality", relationship_quality),
        ("last_contact", last_contact),
        ("contact_frequency_preference", contact_frequency_preference),
        ("spouse_name", spouse_name),
        ("education", education),
        ("occupation", occupation),
        ("employer", employer),
        ("how_met", how_met),
        ("timezone", timezone),
        ("notes", notes),
        # Assembled in Python by tools/tone.py from a fixed key set — never free model
        # text. It is derived from correspondence, which is attacker-writable, and it is
        # read back as trusted prompt text when drafting. See tone.py for the schema.
        ("tone_shape", tone_shape),
    ]
    # List/dict fields: update when not None (passing [] or {} clears the field)
    _collection_fields = [
        ("referred_to_as", referred_to_as),
        ("kids_names", kids_names),
        ("contact_info", contact_info),
        ("important_dates", important_dates),
        ("tags", tags),
    ]

    with _CRM_LOCK:
        contacts = _load_contacts()

        if contact_id:
            for contact in contacts:
                if contact.get("id") == contact_id:
                    # THE UPDATE GATE (2026-08-26). The creation gate below rested on
                    # "an update by contact_id is a deliberate act on a record the
                    # caller already identified". Live on 2026-08-22 that premise
                    # failed exactly as the creation case had: asked to "add Stephen
                    # Ashworth", the model decided Stephen WAS the existing Steven,
                    # called this function with his id, and renamed a real friend's
                    # record. Twice, in consecutive turns, with no prompt shown —
                    # because the id was never the user's, it was the model's own
                    # near-match resolved silently. Third instance of ask-vs-assert.
                    #
                    # What is gated is narrow on purpose: only a change to an IDENTITY
                    # field — who this record is — and only when the incoming value
                    # actually differs from what is stored. Enriching a correctly
                    # identified person (a phone, an employer, a note, a logged
                    # interaction) is the common case and stays ungated, so this does
                    # not put a tap in front of routine field writes. Renaming someone
                    # is rare, and it is the operation that silently destroys the
                    # link between a record and the person it describes.
                    #
                    # The gate cannot ask "did the user choose this id?" — the tool is
                    # not told. It asks the answerable question instead: is this write
                    # about to change who the record is? That catches the 08-22 shape
                    # precisely, because asserting a rename is how a mis-resolved id
                    # becomes visible damage.
                    # Compared case- and whitespace-insensitively: `name` is a required
                    # argument, so EVERY update carries one and most of them are just
                    # the stored name echoed back. A re-capitalisation is not a change
                    # of identity, and gating one would put a tap in front of the
                    # routine writes this is careful not to touch.
                    _identity_changes = [
                        (f, str(contact.get(f) or ""), v)
                        for f, v in (("name", name), ("first_name", first_name),
                                     ("last_name", last_name), ("nickname", nickname))
                        if v and v.strip().casefold()
                        != str(contact.get(f) or "").strip().casefold()
                    ]
                    if _identity_changes and not _approved and not _bulk:
                        _who = str(contact.get("name") or "").strip() or contact_id
                        _pending_update = (
                            f"Rename an EXISTING contact?\n\n"
                            f"  {_who}\n"
                            + "\n".join(
                                f"    {f}: {(cur or '(empty)')} → {new}"
                                for f, cur, new in _identity_changes
                            )
                            + "\n\nApprove only if this is the same person under a "
                              "corrected name. Decline if they are a different person "
                              "— nothing will be changed, and they can be added as a "
                              "separate contact instead."
                        )
                        # request() takes its own lock and writes a different file, and
                        # nothing acquires _CRM_LOCK while holding it, so there is no
                        # lock-order cycle. Nothing has been written to the record.
                        return json.dumps(request(
                            "write_contact", _gate_args, description=_pending_update))

                    for field, value in _str_fields:
                        if value:
                            contact[field] = value
                    for field, value in _collection_fields:
                        if value is not None:
                            contact[field] = value
                    contact["updated"] = today
                    _save_contacts(contacts)
                    return f"{contact_id}\n\nWarning: {_warning}" if _warning else contact_id
            return f"Error: no contact found with id '{contact_id}'"

        new_contact: dict = {
            "id": str(uuid.uuid4()),
            "name": name,
            "first_name": first_name,
            "last_name": last_name,
            "nickname": nickname,
            "referred_to_as": referred_to_as if referred_to_as is not None else [],
            "primary_contact_type": primary_contact_type,
            "relationship_type": relationship_type,
            "relationship_quality": relationship_quality,
            "last_contact": last_contact,
            "contact_frequency_preference": contact_frequency_preference,
            "spouse_name": spouse_name,
            "kids_names": kids_names if kids_names is not None else [],
            "education": education,
            "occupation": occupation,
            "employer": employer,
            "how_met": how_met,
            "timezone": timezone,
            "contact_info": contact_info if contact_info is not None else {},
            "important_dates": important_dates if important_dates is not None else [],
            "tags": tags if tags is not None else [],
            "notes": notes,
            "tone_shape": tone_shape,
            "interaction_log": [],
            "created": today,
            "updated": today,
        }
        # Computed against the pre-append contact list, so the new record never
        # matches itself.
        dedup_candidates = _dedup_candidates(contacts, name)

        # THE GATE. Until 2026-08-19 this was evidence the calling agent could weigh,
        # and the record was created either way. Live on 2026-08-19 the agent weighed
        # identical evidence two ways four minutes apart — turn 1 it surfaced the
        # existing Steven and offered to merge, turn 2 it announced "Stephen with a
        # 'ph' is added as a separate contact" and made the duplicate this whole item
        # exists to prevent.
        #
        # Neither of the other two actors can decide it, and both were measured rather
        # than assumed:
        #
        #   The SCORE cannot. Stephen/Steven is 0.77 and is the same person;
        #   Dave Bennett/Dan Bennett is 0.87 and is two people; Anna/Hannah is 0.80
        #   and is two people. No threshold separates them, so "raise the bar",
        #   "auto-merge above X" and "only ask when confident" are all dead ends.
        #
        #   The AGENT cannot, per the two turns above. relationships runs on
        #   Flash-Lite, so a stronger model is a fair question — but turn 1 shows the
        #   model is capable of asking and simply did not do so reliably. That is
        #   variance, not a ceiling, and a stronger model lowers the rate without
        #   reaching zero. See ROADMAP.md § D2 for the Pro/Flash comparison this owes.
        #
        # So the user is asked, and the ask is not optional — the model is not in the
        # consent path at all (tools/confirm.py's whole design). A duplicate cannot
        # come into existence unasked.
        #
        # The frequency objection does not survive the numbers: in 786 production tool
        # calls write_contact ran 5 times, against 3 for send_email, which is already
        # behind this exact gate. This fires on the subset of those 5 with a near-match.
        #
        # ── PRODUCTION NOTE — this gate is expected to become unnecessary. ──────────
        # It exists because today's model, on today's tier, cannot be relied on to ask.
        # That is a statement about 2026 models, not about the design. The models of
        # tomorrow are not the models of today, and when a model asks reliably, the
        # right move is to REMOVE this and go back to evidence-not-verdict — which is
        # the lighter, better design and remains the intent everywhere else in this
        # file. Do not treat the gate as the settled architecture. Re-test it against
        # whatever is current before assuming it is still earning its friction; the
        # test is in the tests/ suite named below and takes minutes.
        # ───────────────────────────────────────────────────────────────────────────
        #
        # This gate covers creation. Updates are gated separately and much more
        # narrowly, at the top of the contact_id branch above — only a change to an
        # identity field, because "an update by contact_id is a deliberate act on a
        # record the caller already identified" is what 2026-08-22 disproved. Routine
        # field writes on an update still pass without a tap.
        # _bulk exempts an import, and it is DELIBERATELY ABSENT FROM THE TOOL SCHEMA
        # — same discipline as tone_shape above, so no model can set it; only
        # tools/contacts_import.py passes it, in-process. Without the exemption a
        # 200-contact import raises one blocking confirmation per soft name
        # resemblance, each expiring in 10 minutes: unusable, and it would push the
        # user to approve a long queue unread, which is worse than no gate at all.
        # An import already handles this correctly at batch level — it collects the
        # near-match evidence and reports it for review afterwards, which is the right
        # shape for a bulk operation and is the pre-existing behaviour.
        if dedup_candidates and not _approved and not _bulk:
            _pending = (
                f"Add '{name}' as a NEW contact?\n\n"
                + "Similar existing contact(s):\n"
                + "\n".join(f"  • {c['name']} (similarity {c['similarity']})"
                            for c in dedup_candidates)
                + "\n\nApprove to create a separate record. Decline if this is the same "
                  "person — nothing will be saved and they can be merged instead."
            )
        else:
            _pending = None
            contacts.append(new_contact)
            _save_contacts(contacts)

    # Raised outside the CRM lock: request() takes its own lock and writes a different
    # file, so nesting them would be safe but pointless. Nothing has been saved.
    if _pending:
        return json.dumps(request("write_contact", _gate_args, description=_pending))

    cid = new_contact["id"]
    notes_out = []
    if _warning:
        notes_out.append(f"Warning: {_warning}")
    if dedup_candidates:
        listing = "; ".join(
            f"'{c['name']}' (id: {c['id']}, similarity {c['similarity']})"
            for c in dedup_candidates
        )
        if _approved:
            # The user was shown these and said it is a different person. Stated as
            # settled, so the agent does not re-ask something already answered.
            notes_out.append(
                f"Created as a separate record with the user's explicit approval, despite "
                f"resembling: {listing}. Do not re-raise this — they were asked and answered. "
                f"If they later say it is the same person, merge_contacts(keep_id, merge_id)."
            )
        else:
            # _bulk: nobody has been asked. Evidence for batch-level review, which is
            # what the import collects and reports at the end of the run.
            notes_out.append(
                f"Possible existing match(es) for '{name}': {listing}. If this is the "
                f"same person, use merge_contacts(keep_id, merge_id) to fold this new "
                f"record into (or out of) the existing one rather than leaving both — "
                f"confirm with the user first if it's not obvious from context."
            )
    return f"{cid}\n\n" + "\n".join(notes_out) if notes_out else cid


def read_contact(contact_id: str = "", name: str = "") -> str:
    """
    Read a single contact record by ID or name (fuzzy/case-insensitive match).

    Returns a JSON string of the contact record, or an error string if not found.
    If multiple name matches are found, returns the first and notes the ambiguity.

    An id or name that belonged to a record later folded into another one via
    merge_contacts still resolves — it follows the merged_into pointer to the
    surviving record rather than returning a stub or nothing.

    Passing `contact_id` and `name` together is how the user's answer to "which
    Bill?" gets remembered — see the resolution store above. Passing `name`
    alone will use that answer if one was given.
    """
    contacts = _load_contacts()

    if contact_id:
        if name:
            _record_resolution(name, contact_id, "read_contact")
        for contact in contacts:
            if contact.get("id") == contact_id:
                return json.dumps(contact, indent=2)
        merged = _resolve_merged(contacts, contact_id)
        if merged is not None:
            result = merged.copy()
            result["_merged_note"] = (
                f"'{contact_id}' was merged into this record ('{merged.get('id')}')."
            )
            return json.dumps(result, indent=2)
        return f"Error: no contact found with id '{contact_id}'"

    if name:
        matches = _find_by_name(contacts, name)
        if not matches:
            return f"Error: no contact found matching name '{name}'"
        if len(matches) > 1:
            remembered = _apply_resolution(contacts, name, matches)
            if remembered is None:
                return _ambiguous_match(name, matches, "returned")
            result = remembered.copy()
            result["_resolution_note"] = _resolution_note(name, remembered)
            return json.dumps(result, indent=2)
        return json.dumps(matches[0], indent=2)

    return "Error: provide either contact_id or name"


def list_contacts(
    relationship_type: str = "",
    relationship_quality: str = "",
    tag: str = "",
    overdue_only: bool = False,
) -> str:
    """
    List contacts with optional filters.

    Filters are ANDed together. overdue_only returns only contacts where
    last_contact + contact_frequency_preference < today (as_needed contacts
    are excluded from overdue logic).

    Returns a JSON array of matching contact records.
    """
    contacts = _load_contacts()
    today = date.today()
    results = []

    for contact in contacts:
        if relationship_type and contact.get("relationship_type") != relationship_type:
            continue
        if relationship_quality and contact.get("relationship_quality") != relationship_quality:
            continue
        if tag and tag not in contact.get("tags", []):
            continue

        if overdue_only:
            freq = contact.get("contact_frequency_preference", "")
            days = _FREQUENCY_DAYS.get(freq)
            if days is None:
                # as_needed — skip from overdue logic
                continue
            last = contact.get("last_contact", "")
            if not last:
                # Never contacted — overdue immediately
                results.append(contact)
                continue
            try:
                last_date = date.fromisoformat(last)
            except ValueError:
                continue
            due_date = last_date + timedelta(days=days)
            if due_date < today:
                results.append(contact)
        else:
            results.append(contact)

    return json.dumps(results, indent=2)


def log_interaction(
    contact_id: str = "",
    name: str = "",
    interaction_type: str = "",
    summary: str = "",
    follow_up: str = "",
    date: str = "",
) -> str:
    """
    Append an interaction entry to a contact's interaction_log.
    Also updates the contact's last_contact date to the interaction date.

    Passing `contact_id` and `name` together records the user's answer to "which
    Bill?" so the question is not asked again; passing `name` alone reuses an
    answer already given.

    Returns a confirmation string.
    """
    from datetime import date as _date
    interaction_date = date if date else _date.today().isoformat()

    # Deferred until _CRM_LOCK is released — _record_resolution reads contacts.json
    # itself, and the two locks are never held together.
    resolution_to_record: tuple[str, str] | None = None

    with _CRM_LOCK:
        contacts = _load_contacts()
        today = _date.today().isoformat()

        target = None
        if contact_id:
            if name:
                resolution_to_record = (name, contact_id)
            for contact in contacts:
                if contact.get("id") == contact_id:
                    target = contact
                    break
            if target is None:
                return f"Error: no contact found with id '{contact_id}'"
        elif name:
            matches = _find_by_name(contacts, name)
            if not matches:
                return f"Error: no contact found matching name '{name}'"
            # Refuse rather than log. This is a *write*: an interaction filed against
            # the wrong person is worse than one not filed at all, because the record
            # then asserts a conversation that never happened and nothing later
            # contradicts it.
            #
            # Unless the user has already answered this exact question — a
            # remembered answer is the user's own instruction, not a guess.
            if len(matches) > 1:
                remembered = _apply_resolution(contacts, name, matches)
                if remembered is None:
                    return _ambiguous_match(name, matches, "logged")
                matches = [remembered]
            target = matches[0]
            ambiguity = ""
        else:
            return "Error: provide either contact_id or name"

        entry: dict = {
            "date": interaction_date,
            "type": interaction_type,
            "summary": summary,
        }
        if follow_up:
            entry["follow_up"] = follow_up

        if "interaction_log" not in target:
            target["interaction_log"] = []
        target["interaction_log"].append(entry)
        target["last_contact"] = interaction_date
        target["updated"] = today

        _save_contacts(contacts)

    if resolution_to_record is not None:
        _record_resolution(*resolution_to_record, "log_interaction")

    msg = f"Interaction logged for {target['name']} (id: {target['id']})"
    if "ambiguity" in locals() and ambiguity:
        msg += f". Note: {ambiguity}"
    return msg


def search_contacts(query: str) -> str:
    """
    Search contacts by substring match across name, tags, notes,
    and interaction log summaries/follow-ups.

    Also matches a name a contact used to go by before being folded into another
    record via merge_contacts — the surviving record is returned (once), not the
    archived one, so a search for an old/corrected name still finds the person.

    Returns a JSON array of matching contact records.
    """
    if not query:
        return "Error: query must not be empty"

    needle = query.lower()
    contacts = _load_contacts()
    results = []

    for contact in contacts:
        # Scalar text fields to search
        scalar_fields = [
            "name", "first_name", "last_name", "nickname",
            "spouse_name", "education", "occupation", "employer",
            "how_met", "notes",
        ]
        if any(needle in contact.get(f, "").lower() for f in scalar_fields):
            results.append(contact)
            continue

        # referred_to_as and kids_names (lists of strings)
        if any(needle in s.lower() for s in contact.get("referred_to_as", [])):
            results.append(contact)
            continue
        if any(needle in s.lower() for s in contact.get("kids_names", [])):
            results.append(contact)
            continue

        # tags
        if any(needle in t.lower() for t in contact.get("tags", [])):
            results.append(contact)
            continue

        # contact_info values (email, phone, address, social handles)
        ci = contact.get("contact_info", {})
        ci_text = " ".join(
            str(v) for v in ci.values() if isinstance(v, str)
        )
        social = ci.get("social", {})
        if isinstance(social, dict):
            ci_text += " " + " ".join(social.values())
        if needle in ci_text.lower():
            results.append(contact)
            continue

        # interaction log
        matched = False
        for entry in contact.get("interaction_log", []):
            if needle in entry.get("summary", "").lower():
                matched = True
                break
            if needle in entry.get("follow_up", "").lower():
                matched = True
                break
        if matched:
            results.append(contact)

    # Archived (merged-away) records: resolve any that match the query to the
    # live record they survive as, skipping ones already found directly above.
    archive_dir = _crm_archive_dir()
    if archive_dir.exists():
        seen_ids = {c["id"] for c in results}
        for path in sorted(archive_dir.glob("*.json")):
            try:
                archived = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            target_id = archived.get("merged_into")
            if not target_id or target_id in seen_ids:
                continue
            if not _contact_matches(archived, needle):
                continue
            for contact in contacts:
                if contact.get("id") == target_id:
                    results.append(contact)
                    seen_ids.add(target_id)
                    break

    return json.dumps(results, indent=2)


def _merge_auto_accept(persona: str | None = None) -> bool:
    """
    Has the user turned the merge confirmation off? Default False.

    Mike's ruling, 2026-08-26: confirm every merge, "but make it toggleable — if merges
    begin happening all the time the user should be able to auto-accept once trust is
    built." So the gate is the default, and switching it off is the user's deliberate
    act and never a model's: this reads a config file, and no tool writes that file.

    It is only defensible because unmerge_contacts() exists. An auto-accepted merge is
    still recoverable from the pre-merge snapshot, so the toggle trades a confirmation
    for a possible undo, not for an irreversible write. **If the snapshot ever stops
    being written, this toggle has to go with it.**

    Per-persona file first, then the shared one: the VM owns live persona config, so a
    persona can carry its own answer without this needing to know about it. Any failure
    to read leaves the gate ON — the one place where a missing file must not mean
    "allow".
    """
    import yaml
    from core.persona import persona_config_dir
    candidates = []
    try:
        candidates.append(persona_config_dir(persona) / "preferences.yaml")
    except Exception:  # noqa: BLE001
        # Identity resolution is fail-closed and raises when no persona is in scope
        # (core/persona.py). That is correct there and must not propagate here — a
        # preference lookup is not a reason to take a session down, and the shared
        # file below still answers.
        pass
    candidates.append(Path(__file__).parent.parent / "config" / "preferences.yaml")
    for path in candidates:
        try:
            if not path.exists():
                continue
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}
        except (OSError, ValueError, yaml.YAMLError):
            continue
        crm_cfg = ((cfg.get("proactive") or {}).get("crm") or {})
        if "merge_auto_accept" in crm_cfg:
            return bool(crm_cfg["merge_auto_accept"])
    return False


def merge_contacts(keep_id: str, merge_id: str, confirm_token: str = "") -> str:
    """
    [DB-0815-07] Fold `merge_id`'s contact record into `keep_id`, resolving a
    duplicate the way the standing archive-on-merge rule requires: nothing is
    deleted. `merge_id`'s record is written to the CRM archive with a
    `merged_into` pointer at `keep_id`, and both `read_contact` and
    `search_contacts` follow that pointer — old id, old name, all still resolve.
    Same shape as tools/wisdom.py's merge_wisdom_entries.

    **[DB-0822-03] Requires the user's approval, given in the app.** The first
    call returns PENDING_CONFIRMATION and changes nothing; the merge happens when
    the user approves it there, and the model is not in that path — the same
    design as the near-match create gate on `write_contact` (`6d6d46c`) and for
    the same reason, one step further along.

    Live on 2026-08-19: "Steven from the gym and Stephen from the gym are the same
    person. Merge them, keeping Steven." **There were three Stevens.** The keep_id
    chosen was the user's actual friend — a different person, with a spouse and a
    dinner logged three weeks earlier — and *both* gym records were folded into him
    across two calls, with no question asked. His record now says he was met at the
    gym.

    The ambiguity was in the *instruction*, and `_ambiguous_match` could not see it:
    that guard fires on name lookups, and this tool takes ids, so by the time the
    ids arrive the choice has already been made and nothing downstream can tell a
    considered choice from a coin flip. The description below is therefore built
    from both records' `_disambiguation_entry()` — spouse, employer, how they were
    met, when they were last spoken to — so what the user approves is two named
    people, not two opaque ids. If the wrong Steven is in it, it is visible.

    A merge is also **destructive in a way the archive does not fully undo**: the
    keep record is edited in place, so fields it inherits cannot be told apart from
    fields it always had. `unmerge_contacts` exists for that and works from the
    pre-merge snapshot this function now writes.

    Field-by-field: any scalar field empty on `keep_id` is filled in from
    `merge_id`; a field already set on `keep_id` is left alone. List fields
    (referred_to_as, kids_names, tags, important_dates) are unioned.
    contact_info is filled in key-by-key where `keep_id` doesn't already have
    that key (social handles merged the same way one level down). notes are
    concatenated when both sides have different text. interaction_log entries
    from both records are combined and re-sorted by date. last_contact becomes
    whichever of the two is more recent, so overdue tracking doesn't regress.

    Args:
        keep_id:  id of the record to keep as the surviving, canonical contact.
        merge_id: id of the duplicate record to archive into keep_id.
        confirm_token: Not for the model to set. The app supplies this when
            carrying out a merge the user has approved.

    Returns:
        Confirmation string naming both records and the archive path, a
        PENDING_CONFIRMATION JSON payload on the first call, or an Error string
        if either id doesn't resolve to a live contact.
    """
    from tools.confirm import consume, request

    if not keep_id or not merge_id:
        return "Error: both keep_id and merge_id are required."
    if keep_id == merge_id:
        return "Error: keep_id and merge_id must name two different records."

    # Fingerprinted exactly as the replay through confirm.execute() will rebuild
    # them — the two ids and nothing else, so an approval for "fold Stephen into
    # Steven-from-the-gym" cannot be spent on a different pair.
    _gate_args = {"keep_id": keep_id, "merge_id": merge_id}

    _approved = False
    if confirm_token:
        _ok, _reason = consume(confirm_token, "merge_contacts", _gate_args)
        if not _ok:
            return f"Error: not merged. {_reason}"
        _approved = True
    elif _merge_auto_accept():
        # The user has switched the confirmation off (see _merge_auto_accept). Logged
        # rather than silent: the whole point of the toggle is that it can be forgotten,
        # so a merge that skipped the gate has to be findable afterwards.
        _approved = True
        try:
            from tools.logger import write_quality_event
            write_quality_event(
                event_type="MERGE_AUTO_ACCEPTED",
                source_agent="crm",
                detail=f"merge_contacts ran without confirmation "
                       f"(keep={keep_id}, merge={merge_id}); "
                       f"proactive.crm.merge_auto_accept is on. Reversible via "
                       f"unmerge_contacts.",
            )
        except Exception:  # noqa: BLE001
            pass

    with _CRM_LOCK:
        contacts = _load_contacts()
        keep = next((c for c in contacts if c.get("id") == keep_id), None)
        merge = next((c for c in contacts if c.get("id") == merge_id), None)
        if keep is None:
            return f"Error: no contact found with id '{keep_id}'"
        if merge is None:
            return f"Error: no contact found with id '{merge_id}'"

        # THE GATE. Both records are resolved first so the description names real
        # people rather than echoing back the ids it was handed — an id the caller
        # got wrong reads identically to one it got right.
        if not _approved:
            _pending = _merge_confirmation_description(keep, merge)
        else:
            _pending = None

    if _pending:
        # Raised outside the CRM lock, as write_contact's gate is: request() takes
        # its own lock and writes a different file. Nothing has been merged.
        return json.dumps(request("merge_contacts", _gate_args, description=_pending))

    with _CRM_LOCK:
        contacts = _load_contacts()
        keep = next((c for c in contacts if c.get("id") == keep_id), None)
        merge = next((c for c in contacts if c.get("id") == merge_id), None)
        if keep is None:
            return f"Error: no contact found with id '{keep_id}'"
        if merge is None:
            return f"Error: no contact found with id '{merge_id}'"

        today = date.today().isoformat()

        # The pre-merge state of the KEEP record, captured before a single field is
        # touched. Without it there is no unmerge: the loser is archived whole, but
        # the survivor is edited in place, and afterwards nothing distinguishes a
        # field it inherited from one it always had. Written under the same lock as
        # the merge so the snapshot and the mutation cannot disagree.
        _keep_snapshot = json.loads(json.dumps(keep))

        scalar_fields = [
            "name", "first_name", "last_name", "nickname", "primary_contact_type",
            "relationship_type", "relationship_quality", "contact_frequency_preference",
            "spouse_name", "education", "occupation", "employer", "how_met",
            "timezone", "tone_shape",
        ]
        for field in scalar_fields:
            if not keep.get(field) and merge.get(field):
                keep[field] = merge[field]

        if merge.get("notes") and merge["notes"] != keep.get("notes"):
            keep["notes"] = (
                f"{keep['notes']}\n\n{merge['notes']}" if keep.get("notes") else merge["notes"]
            )

        for field in ("referred_to_as", "kids_names", "tags"):
            combined = list(keep.get(field) or [])
            for item in merge.get(field) or []:
                if item not in combined:
                    combined.append(item)
            keep[field] = combined

        combined_dates = list(keep.get("important_dates") or [])
        existing_pairs = {(d.get("label"), d.get("date")) for d in combined_dates}
        for d in merge.get("important_dates") or []:
            pair = (d.get("label"), d.get("date"))
            if pair not in existing_pairs:
                combined_dates.append(d)
                existing_pairs.add(pair)
        keep["important_dates"] = combined_dates

        keep_ci = dict(keep.get("contact_info") or {})
        for k, v in (merge.get("contact_info") or {}).items():
            if k == "social" and isinstance(v, dict):
                keep_social = dict(keep_ci.get("social") or {})
                for sk, sv in v.items():
                    keep_social.setdefault(sk, sv)
                if keep_social:
                    keep_ci["social"] = keep_social
            else:
                keep_ci.setdefault(k, v)
        keep["contact_info"] = keep_ci

        combined_log = list(keep.get("interaction_log") or []) + list(merge.get("interaction_log") or [])
        combined_log.sort(key=lambda e: e.get("date") or "")
        keep["interaction_log"] = combined_log

        keep_last = keep.get("last_contact") or ""
        merge_last = merge.get("last_contact") or ""
        if merge_last and merge_last > keep_last:
            keep["last_contact"] = merge_last

        keep["updated"] = today

        archive_dir = _crm_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)
        archived = dict(merge)
        archived["merged_into"] = keep_id
        archived["archived"] = today
        archive_path = archive_dir / f"{merge_id}_{today}.json"
        with open(archive_path, "w") as f:
            json.dump(archived, f, indent=2)
        os.chmod(archive_path, 0o600)

        snapshot_path = _write_pre_merge_snapshot(_keep_snapshot, keep_id, merge_id)

        contacts = [c for c in contacts if c.get("id") != merge_id]
        _save_contacts(contacts)

    return (
        f"Merged '{merge.get('name', '')}' ({merge_id}) into '{keep.get('name', '')}' "
        f"({keep_id}). Archived at {archive_path} with merged_into='{keep_id}'; "
        f"'{merge_id}' still resolves via read_contact and search_contacts. "
        f"This merge can be reversed with unmerge_contacts('{merge_id}')."
    )


def unmerge_contacts(merge_id: str) -> str:
    """
    [DB-0822-03] Reverse a merge: bring `merge_id` back as its own live contact and
    put the record it was folded into back the way it was.

    **This only works for merges performed on or after 2026-08-22.** Reversing a
    merge needs the pre-merge state of the *surviving* record, and nothing captured
    that until `merge_contacts` started writing a snapshot. Every merge made before
    then — including the 2026-08-19 Steven merges that motivated this — has no
    snapshot and cannot be unmerged here; this refuses and says so rather than
    half-reversing. Those have to be repaired by hand from the archived loser
    record, which does still exist and is complete.

    Nothing is deleted, in either direction. Before the survivor is rolled back,
    its current post-merge state — the possibly-wrong one being discarded — is
    itself archived, so a mistaken unmerge loses nothing either.

    Args:
        merge_id: id of the record that was folded away, i.e. the `merge_id` given
            to the original `merge_contacts` call.

    Returns:
        Confirmation string naming both restored records, or an Error string.
    """
    if not merge_id:
        return "Error: merge_id is required."

    with _CRM_LOCK:
        contacts = _load_contacts()
        if any(c.get("id") == merge_id for c in contacts):
            return (
                f"Error: '{merge_id}' is already a live contact — it is not currently "
                f"merged into anything, so there is nothing to reverse."
            )

        archived = _load_archived_record(merge_id)
        if archived is None or not archived.get("merged_into"):
            return (
                f"Error: no merge found for '{merge_id}'. Nothing in the CRM archive "
                f"records that id being folded into another contact."
            )
        keep_id = archived["merged_into"]

        snapshot = _load_pre_merge_snapshot(merge_id)
        if snapshot is None:
            return (
                f"Error: this merge cannot be reversed. '{merge_id}' was folded into "
                f"'{keep_id}' before pre-merge snapshots existed (they start "
                f"2026-08-22), so there is no record of what '{keep_id}' looked like "
                f"beforehand and restoring it would be guesswork. The archived copy of "
                f"'{merge_id}' is intact and complete — repair the two records by hand "
                f"from it rather than reversing automatically. Nothing has been changed."
            )

        keep = next((c for c in contacts if c.get("id") == keep_id), None)
        if keep is None:
            return (
                f"Error: '{merge_id}' was merged into '{keep_id}', but '{keep_id}' is "
                f"no longer a live contact. Nothing has been changed."
            )

        today = date.today().isoformat()
        archive_dir = _crm_archive_dir()
        archive_dir.mkdir(parents=True, exist_ok=True)

        # Archive-on-merge, applied to the undo. The post-merge survivor is the state
        # being thrown away, and it may be the state the user actually wanted — so it
        # is written out before it is overwritten. No `merged_into` key: the archive
        # scans in _find_by_name and search_contacts skip records without one, which
        # is right, because this id is about to be live again and must not also
        # resolve as a pointer to itself.
        discarded = json.loads(json.dumps(keep))
        discarded["record_type"] = "post_merge_discarded"
        discarded["unmerged_away_from"] = merge_id
        discarded["archived"] = today
        discarded_path = archive_dir / f"unmerged_{keep_id}_{_archive_stamp()}.json"
        with open(discarded_path, "w") as f:
            json.dump(discarded, f, indent=2)
        os.chmod(discarded_path, 0o600)

        restored_keep = json.loads(json.dumps(snapshot))
        restored_keep.pop("record_type", None)
        restored_keep.pop("snapshot_of_merge", None)
        restored_keep.pop("archived", None)
        restored_keep["updated"] = today

        restored_merge = json.loads(json.dumps(archived))
        restored_merge.pop("merged_into", None)
        restored_merge.pop("archived", None)
        restored_merge["updated"] = today

        contacts = [restored_keep if c.get("id") == keep_id else c for c in contacts]
        contacts.append(restored_merge)
        _save_contacts(contacts)

        # The two archive files that described the merge are retired rather than
        # deleted — renamed out of the way so neither keeps resolving as a live
        # pointer, and so a second unmerge of the same pair finds nothing to redo.
        _retire_merge_archives(merge_id, keep_id)

    return (
        f"Unmerged: '{restored_merge.get('name', '')}' ({merge_id}) is a separate "
        f"contact again, and '{restored_keep.get('name', '')}' ({keep_id}) is back to "
        f"its pre-merge state. The discarded merged version of '{keep_id}' is archived "
        f"at {discarded_path} — nothing was deleted."
    )


# ---------------------------------------------------------------------------
# Tool schemas — registered with the Claude API in orchestrator.register_tools()
# ---------------------------------------------------------------------------

WRITE_CONTACT_SCHEMA = {
    "name": "write_contact",
    "description": (
        "Create or update a contact record in the CRM. "
        "If contact_id is provided, updates that record with the supplied fields. "
        "If contact_id is empty, creates a new contact and returns its ID. "
        "On creation, if the name closely matches an existing contact, NOTHING IS "
        "SAVED and the user is asked to approve creating a separate record. Show them "
        "the description you get back and stop — approving it in the app is what "
        "creates the contact. Do not say you have added them, do not retry, and do not "
        "call this tool again for that person. If they say it is the same person, use "
        "merge_contacts instead. Refuses known-placeholder values — an "
        "email on a reserved/placeholder domain (example.com and similar), a phone "
        "in a known fictional range, a textbook placeholder address, a generic "
        "social handle, or the name 'John Doe'/'Jane Doe' — rather than storing an "
        "invented value."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {
                "type": "string",
                "description": "Display name — how the user thinks of this person (e.g. 'Mom', 'Dr. Smith', 'Sarah').",
            },
            "first_name": {"type": "string", "description": "Legal or given first name."},
            "last_name": {"type": "string", "description": "Family name."},
            "nickname": {"type": "string", "description": "What you call them directly."},
            "referred_to_as": {
                "type": "array",
                "description": (
                    "All the ways the user refers to this person in speech — "
                    "e.g. ['Mom', 'my mother', 'my mom']. "
                    "Used to recognize mentions in unstructured text."
                ),
                "items": {"type": "string"},
            },
            "primary_contact_type": {
                "type": "string",
                "description": (
                    "Primary category for how this contact fits into the user's life. "
                    "One of: work_colleague, work_client, work_vendor, friend, family, "
                    "romantic_partner, acquaintance, service_provider, other. "
                    "Use relationship_type for the relational quality; use this field "
                    "for the functional category."
                ),
            },
            "relationship_type": {
                "type": "string",
                "description": (
                    "Category of relationship. "
                    "One of: friend, family, colleague, romantic, acquaintance, professional, other."
                ),
            },
            "relationship_quality": {
                "type": "string",
                "description": (
                    "Current quality of the relationship. "
                    "One of: close, warm, neutral, strained, lost_touch."
                ),
            },
            "last_contact": {
                "type": "string",
                "description": "Date of last contact in YYYY-MM-DD format.",
            },
            "contact_frequency_preference": {
                "type": "string",
                "description": (
                    "How often the user wants to stay in touch. "
                    "One of: daily, weekly, monthly, quarterly, as_needed."
                ),
            },
            "spouse_name": {"type": "string", "description": "Name of spouse or partner."},
            "kids_names": {
                "type": "array",
                "description": "Names of children.",
                "items": {"type": "string"},
            },
            "education": {
                "type": "string",
                "description": "Educational background, free text (e.g. 'Stanford MBA', 'PhD in biology').",
            },
            "occupation": {"type": "string", "description": "Job title or role."},
            "employer": {"type": "string", "description": "Company or organization."},
            "how_met": {"type": "string", "description": "How the user met this person (e.g. 'college roommate', 'intro from Sarah')."},
            "timezone": {
                "type": "string",
                "description": "IANA timezone string (e.g. 'America/Chicago'). Used for outreach timing.",
            },
            "contact_info": {
                "type": "object",
                "description": "Structured contact details.",
                "properties": {
                    "email": {"type": "string"},
                    "phone": {"type": "string"},
                    "address": {"type": "string"},
                    "social": {
                        "type": "object",
                        "description": "Social handles keyed by platform (e.g. {twitter: '@sarah', linkedin: 'sarah-chen'}).",
                    },
                },
            },
            "important_dates": {
                "type": "array",
                "description": (
                    "List of important dates. Each item: {label, date}. "
                    "date is MM-DD when year unknown, YYYY-MM-DD when known."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "label": {"type": "string"},
                        "date": {"type": "string"},
                    },
                    "required": ["label", "date"],
                },
            },
            "tags": {
                "type": "array",
                "description": "Free-form tags for grouping or searching (e.g. college, hiking, Austin).",
                "items": {"type": "string"},
            },
            "notes": {
                "type": "string",
                "description": "Free-text field for personality, context, and anything that doesn't fit the schema.",
            },
            # `tone_shape` is deliberately NOT offered here, though write_contact accepts it.
            # It is assembled in Python by tools/tone.py from a fixed key set and is read back
            # as trusted prompt text when drafting a message. Exposing it to a model would let
            # free text — ultimately derived from attacker-writable mail — be written straight
            # into that position, which is the whole thing the fixed schema prevents. Agents
            # read it via read_contact; only tone.py writes it. Do not add it as a property.
            "contact_id": {
                "type": "string",
                "description": (
                    "ID of an existing contact to update. "
                    "Leave empty to create a new contact."
                ),
            },
            "confirm_token": {
                "type": "string",
                "description": (
                    "Not for you to set. The app supplies this when it carries out an "
                    "action the user has approved; leave it out of every call you make."
                ),
            },
        },
        "required": ["name"],
    },
}

READ_CONTACT_SCHEMA = {
    "name": "read_contact",
    "description": (
        "Retrieve a single contact record by ID or name. "
        "Name matching is case-insensitive substring. "
        "If multiple contacts match the name, nothing is returned and you are asked "
        "to put the question to the user. "
        "An id or name that was merged away via merge_contacts still resolves — "
        "you get the surviving record back, with a note naming the merge."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Exact contact ID (UUID). Takes priority over name.",
            },
            "name": {
                "type": "string",
                "description": (
                    "Name or partial name to search for. When you already have the "
                    "contact_id because the user has just told you which person they "
                    "meant, pass the name they used here as well — that is what saves "
                    "the answer, so the same question is not asked again later."
                ),
            },
        },
        "required": [],
    },
}

LIST_CONTACTS_SCHEMA = {
    "name": "list_contacts",
    "description": (
        "List contacts with optional filters. All filters are ANDed. "
        "Use overdue_only=true to surface contacts who are past their contact frequency preference."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "relationship_type": {
                "type": "string",
                "description": (
                    "Filter by relationship type. "
                    "One of: friend, family, colleague, romantic, acquaintance, professional, other."
                ),
            },
            "relationship_quality": {
                "type": "string",
                "description": (
                    "Filter by relationship quality. "
                    "One of: close, warm, neutral, strained, lost_touch."
                ),
            },
            "tag": {
                "type": "string",
                "description": "Return only contacts that have this exact tag.",
            },
            "overdue_only": {
                "type": "boolean",
                "description": (
                    "If true, return only contacts whose last_contact date plus "
                    "their contact_frequency_preference interval is before today. "
                    "Contacts with as_needed preference are excluded."
                ),
            },
        },
        "required": [],
    },
}

LOG_INTERACTION_SCHEMA = {
    "name": "log_interaction",
    "description": (
        "Record an interaction with a contact. Appends an entry to the contact's "
        "interaction_log and updates their last_contact date."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "contact_id": {
                "type": "string",
                "description": "Exact contact ID. Takes priority over name.",
            },
            "name": {
                "type": "string",
                "description": (
                    "Contact name (fuzzy match) — used if contact_id is not provided. "
                    "If you have both because the user has just said which person they "
                    "meant, send both: the name is what saves their answer, so the "
                    "question is not asked again next time."
                ),
            },
            "interaction_type": {
                "type": "string",
                "description": (
                    "How they interacted. "
                    "One of: in_person, phone, video, message, email, other."
                ),
            },
            "summary": {
                "type": "string",
                "description": "Brief note on what was discussed or shared.",
            },
            "follow_up": {
                "type": "string",
                "description": "Optional: what was agreed or should be checked on later.",
            },
            "date": {
                "type": "string",
                "description": "Date of the interaction in YYYY-MM-DD format. Defaults to today.",
            },
        },
        "required": [],
    },
}

SEARCH_CONTACTS_SCHEMA = {
    "name": "search_contacts",
    "description": (
        "Search all contacts by substring match across name, tags, notes, "
        "and interaction log entries. Also matches a name a contact used to go by "
        "before being merged into another record, returning the surviving record. "
        "Returns a JSON array of matching contacts."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search string — matched case-insensitively across all text fields.",
            },
        },
        "required": ["query"],
    },
}

MERGE_CONTACTS_SCHEMA = {
    "name": "merge_contacts",
    "description": (
        "Resolve a duplicate contact by folding one record into another. Fills in "
        "any field empty on the kept record from the merged-away one, unions list "
        "fields (referred_to_as, kids_names, tags, important_dates, interaction_log), "
        "and keeps the more recent last_contact date. The merged-away record is never "
        "deleted — it is archived with a merged_into pointer, so its id and its old "
        "name both keep resolving via read_contact and search_contacts. "
        "Call this after write_contact or search_contacts surfaces a likely duplicate. "
        "Requires the user's explicit approval: the first call returns "
        "PENDING_CONFIRMATION and merges nothing — it shows the user both records side "
        "by side so they can see exactly who is being kept and who is being folded in. "
        "Approving it in the app is what carries out the merge; do not call this tool a "
        "second time, and never say it is done before that. If you are unsure WHICH of "
        "several similarly-named contacts is meant, read them first and ask — do not "
        "pick one and let the approval screen be the question."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "keep_id": {
                "type": "string",
                "description": "id of the contact to keep as the surviving, canonical record.",
            },
            "merge_id": {
                "type": "string",
                "description": "id of the duplicate contact to fold into keep_id and archive.",
            },
            "confirm_token": {
                "type": "string",
                "description": "Not for you to set. The app supplies this when it carries out an action the user has approved; leave it out of every call you make.",
            },
        },
        "required": ["keep_id", "merge_id"],
    },
}

UNMERGE_CONTACTS_SCHEMA = {
    "name": "unmerge_contacts",
    "description": (
        "Reverse a merge: bring a contact that was folded into another one back as a "
        "separate record, and restore the record it was folded into to its pre-merge "
        "state. Use when the user says two contacts were merged in error, or that the "
        "wrong person was kept. Nothing is deleted in either direction — the discarded "
        "merged version is archived too. IMPORTANT: only merges made on or after "
        "2026-08-22 can be reversed; earlier ones have no record of the surviving "
        "contact's previous state, and this will say so plainly rather than guessing. "
        "If it refuses for that reason, tell the user the merge has to be repaired by "
        "hand and do not attempt to reconstruct it yourself."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "merge_id": {
                "type": "string",
                "description": (
                    "id of the contact that was folded away — the merge_id from the "
                    "original merge_contacts call. Its old id still resolves via "
                    "read_contact, which reports the record it was merged into."
                ),
            },
        },
        "required": ["merge_id"],
    },
}


# ---------------------------------------------------------------------------
# Confirm-gate executor registration
# ---------------------------------------------------------------------------
# `POST /confirm` finishes an approved action by looking the action name up in
# tools/confirm.py's _EXECUTORS and calling the tool itself — the user's tap, not a
# second model call, is what carries it out. merge_contacts registers itself here
# rather than being listed there because this worktree owns tools/crm.py only.
#
# THIS IS A DEVIATION worth folding back: _EXECUTORS is hard-coded on purpose (see
# its comment) so that the mapping cannot be influenced by anything outside that
# file, and a registration performed as an import side effect is weaker in one real
# way — if the server process restarts between the user seeing the prompt and
# tapping Approve, and nothing has imported tools.crm yet, execute() reports that
# nothing knows how to carry out 'merge_contacts'. That fails safe (no merge
# happens, the user is told) and self-clears at the 10-minute TTL, but the durable
# form is the one line in tools/confirm.py. setdefault, so adding it there wins.
def _register_confirm_executor() -> None:
    try:
        from tools.confirm import _EXECUTORS
        _EXECUTORS.setdefault("merge_contacts", ("tools.crm", "merge_contacts"))
    except Exception:  # noqa: BLE001
        # An import failure here must not take the CRM down; the gate still refuses
        # to merge without an approval, which is the half that matters.
        pass


_register_confirm_executor()
