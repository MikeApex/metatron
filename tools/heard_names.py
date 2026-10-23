"""
tools/heard_names.py — names the user said, checked against the people they know.

Plan: archive/plans/heard_names_plan_2026-10-23.md (revised after its Fable review).

Dictated names arrive misheard, and the agents that save things act on them as heard: on
2026-10-15 Relationships created a contact "Eva" for Iva, and on 2026-10-22 Logistics put
"Eva & Benny" (Iva and Manny) in the calendar. Telling a Flash-Lite Coordinator to watch for
mishearings fixed a place 3/3 and a name only 1/3 — "Ella" and "Benny" are plausible real
names, and the model will not assume them away without evidence. This module supplies the
evidence, as a NOTE on the Coordinator's input:

  1. A contact's own name is never noted (name, first_name or last_name on a live record).
     A word that is only a contact's nickname or referred_to_as gets a note saying who it
     means — the Coordinator never sees contact records, so "Eva" on Iva's referred_to_as
     did not stop "Eva & Benny" reaching the calendar (measured on Mike's data, 2026-10-23).
  2. A name the user has corrected before ("it's Manny, not Benny") is noted with the
     correction. So is the name of a contact that was merged away into another.
  3. An unknown name that sounds like a known one is noted as possibly that person.

**Nothing here rewrites what the user said.** That is the whole design, and the reason
is Mike's (2026-10-23): a rewrite that turns every "Bonnie" into "Johnny" means a real
Bonnie can never be registered — even "Bonnie is a real person" would arrive as "Johnny
is a real person". A note leaves the words intact, so a message that introduces a new
person still says so; and once that person is a contact, rule 1 silences the note.

**Corrections are kept out of contact lookup, deliberately.** They live in their own file,
crm/misheard_names.json, never in contacts.json and never in name_resolutions.json — both
of which `read_contact`/`search_contacts` consult. A correction visible to lookup would make
`read_contact("Benny")` return Manny, which is the same trap by another route. Same storage
rules as name_resolutions.json otherwise: 0600, one file per persona, nothing deleted (a
replaced correction moves to `history`).

Every reader here degrades to "no note" on any failure. A note is a hint; a broken contacts
file must cost a hint, never a turn.
"""

from __future__ import annotations

import difflib
import json
import logging
import os
import re
import threading
from contextlib import nullcontext
from datetime import datetime
from pathlib import Path

import tools.crm as CRM

logger = logging.getLogger(__name__)

# Spelling similarity, first token against first token, no prefix signal. Deliberately
# stricter than the CRM's write-gate threshold (0.6): that one has a human approving every
# hit, and this one runs unsupervised on every turn. At 0.6 with the prefix rule, a review
# measured "Tomorrow"→Tom, "Been"→Ben, "Same"→Sam, "Maybe"→Manny — a hint on most turns.
NEAR_NAME_THRESHOLD = 0.80
SOUND_KEY_MIN_RATIO = 0.60
MAX_NOTES = 3
# Whisper's hotword/prompt budget is small; recent contacts are the likeliest to be spoken.
VOCABULARY_LIMIT = 30

# Capitalised words that are not names, and that a dictated sentence routinely carries
# mid-sentence. Sentence-initial words are skipped wholesale (see _candidates), so this
# only needs the mid-sentence offenders.
_NOT_NAMES = {
    "i", "i'm", "i'll", "i've", "i'd", "ok", "okay", "metatron", "mr", "mrs", "ms", "dr",
    "mum", "mom", "dad", "god", "english", "british", "american", "uk", "us", "usa",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june", "july", "august",
    "september", "october", "november", "december", "christmas", "easter",
    # Abbreviations, because the voice tray's batch stamps ("[Fri 23 Oct, 15:41]") put
    # them mid-sentence in every multi-recording message.
    "mon", "tue", "wed", "thu", "fri", "sat", "sun", "jan", "feb", "mar", "apr", "jun",
    "jul", "aug", "sep", "sept", "oct", "nov", "dec",
    # A capital after a colon is not a sentence start here (so "Reminder: Benny at 3" is
    # checked), which lets these through as often as anything — none is ever a name.
    "the", "this", "that", "these", "those", "there", "then", "we", "you", "he", "she",
    "it", "they", "my", "our", "your", "his", "her", "their", "and", "but", "also",
    "please", "yes", "not", "just", "still",
}
# Titles and abbreviations whose period is not the end of a sentence: "Dr. Benny said".
_ABBREV_BEFORE_RE = re.compile(r"\b(?:dr|mr|mrs|ms|st|prof|e\.g|i\.e|vs)\.\s*$", re.IGNORECASE)
# How far back the sentence-break check looks, and how many words one message may have
# checked. Both bound the cost on a pasted document: the first version re-scanned the
# whole prefix per capitalised word, measured at ~0.65s on a 21 KB message.
_BREAK_WINDOW = 12
_MAX_CANDIDATES = 40

_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'\-]*")
# What ends a sentence for the purpose of "this capital is just the sentence starting":
# terminal punctuation, a line break, or the closing bracket of a batch stamp
# ("[Fri 23 Oct, 15:41] Benny…").
_SENTENCE_BREAK_RE = re.compile(r"(^|[.!?\n\]])\s*[\"'(\[]*\s*$")

_STORE_LOCK = threading.Lock()
_STORE_VERSION = 1


# ---------------------------------------------------------------------------
# Who is known
# ---------------------------------------------------------------------------

def _words(value) -> list[str]:
    if isinstance(value, (list, tuple)):
        return [w for v in value for w in _words(v)]
    return [w.lower() for w in _TOKEN_RE.findall(str(value or ""))]


def _contact_words(c: dict) -> set[str]:
    words = set()
    for field in ("name", "first_name", "last_name", "nickname", "referred_to_as"):
        words.update(_words(c.get(field)))
    return words


def _name_words(c: dict) -> set[str]:
    words = set()
    for field in ("name", "first_name", "last_name"):
        words.update(_words(c.get(field)))
    return words


def _known_words(contacts: list[dict]) -> set[str]:
    known: set[str] = set()
    for c in contacts:
        known |= _contact_words(c)
    return known


def _display(c: dict) -> str:
    return str(c.get("name") or c.get("first_name") or c.get("nickname") or "").strip()


def _spoken_first(c: dict) -> str:
    """The name the user would actually say: nickname, else first name, else the first
    word of the full name."""
    for v in (c.get("nickname"), c.get("first_name")):
        if v and str(v).strip():
            return str(v).strip()
    words = _TOKEN_RE.findall(str(c.get("name") or ""))
    return words[0] if words else ""


# ---------------------------------------------------------------------------
# Sounds-like
# ---------------------------------------------------------------------------

def _sound_key(word: str) -> str:
    """
    A coarse phonetic key: same key means "a transcriber could hear one as the other".
    Vowels after the first sound are dropped, and the consonants a speech model confuses
    most are merged — the lip sounds b/p/m (the measured Benny for Manny), d/t, f/v, g/k,
    s/z. That catches what spelling similarity scores low: Benny/Manny is 0.60 by
    spelling, Eva/Iva 0.67. Spelling handles the rest (Ella/Bella 0.89).
    """
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return ""
    for a, b in (("ph", "f"), ("ck", "k"), ("gh", "g"), ("kn", "n"), ("wr", "r"),
                 ("x", "ks"), ("q", "k"), ("z", "s"), ("c", "k")):
        w = w.replace(a, b)
    w = w.translate(str.maketrans("bmdvgz", "pptfks"))
    head = "a" if w[0] in "aeiouy" else w[0]
    tail = re.sub(r"[aeiouyhw]", "", w[1:])
    key = head + tail
    return re.sub(r"(.)\1+", r"\1", key)


def _sounds_like(heard: str, name: str) -> bool:
    h, n = heard.lower(), name.lower()
    if not h or not n or h == n:
        return False
    ratio = difflib.SequenceMatcher(None, h, n).ratio()
    # A matching key alone is too weak for short names: their 2-character keys collide
    # with ordinary words (review, 2026-10-23: Sam~"Zoom", Dan~"Tony", Ben~"Piano"). The
    # spelling floor keeps the real cases — Eva/Iva 0.67, Benny/Manny 0.60 — and drops those.
    key = _sound_key(h)
    # And a key of one sound means nothing: "Day" and "Dad" both reduce to "t".
    if len(key) >= 2 and key == _sound_key(n) and ratio >= SOUND_KEY_MIN_RATIO:
        return True
    return ratio >= NEAR_NAME_THRESHOLD


# ---------------------------------------------------------------------------
# Corrections store
# ---------------------------------------------------------------------------

def _store_path() -> Path:
    return CRM.persona_data_dir() / "crm" / "misheard_names.json"


def _load_store() -> dict:
    """{heard_lower: {"heard", "contact_id", "recorded", "history"}}; {} on any problem."""
    path = _store_path()
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    entries = data.get("misheard") if isinstance(data, dict) else None
    return entries if isinstance(entries, dict) else {}


def _save_store(entries: dict) -> None:
    path = _store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps({"version": _STORE_VERSION, "misheard": entries}, indent=2,
                              ensure_ascii=False))
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def _live_contact(contacts: list[dict], contact_id: str) -> dict | None:
    for c in contacts:
        if c.get("id") == contact_id:
            return c
    # Merged away since the correction was recorded: follow it to the survivor.
    return CRM._resolve_merged(contacts, contact_id)


def _resolve_meant(contacts: list[dict], meant: str) -> tuple[dict | None, str]:
    """The one live contact `meant` names, or (None, why not)."""
    target = meant.strip().lower()
    if not target:
        return None, "no correct name given"
    whole = [c for c in contacts if _display(c).lower() == target]
    if len(whole) == 1:
        return whole[0], ""
    first = _words(target)[:1]
    hits = [c for c in contacts if first and first[0] in _contact_words(c)]
    if len(hits) == 1:
        return hits[0], ""
    if not hits:
        return None, f"no contact is called {meant}"
    return None, f"more than one contact is called {meant}"


def record_misheard(heard: str, meant: str, persona: str | None = None) -> str:
    """
    Remember that `heard` is how the user's `meant` gets misheard. Returns a short result
    line; never raises.

    Refuses when `heard` already belongs to a contact — that name is somebody, and
    recording it as a mishearing of someone else is the Bonnie trap.
    """
    try:
        with (_scope(persona)):
            word = (heard or "").strip().strip('"\'').strip()
            if not re.fullmatch(r"[A-Za-z][A-Za-z'\-]{1,30}", word):
                return f"not recorded: '{heard}' is not a single name"
            contacts = CRM._load_contacts()
            if word.lower() in _known_words(contacts):
                return f"not recorded: {word} is a contact's name"
            contact, why = _resolve_meant(contacts, meant or "")
            if not contact:
                return f"not recorded: {why}"
            with _STORE_LOCK:
                entries = _load_store()
                key = word.lower()
                prev = entries.get(key)
                if prev and prev.get("contact_id") == contact.get("id"):
                    return f"already recorded: {word} -> {_display(contact)}"
                history = list((prev or {}).get("history") or [])
                if prev:
                    superseded = {k: v for k, v in prev.items() if k != "history"}
                    superseded["superseded"] = datetime.now().isoformat(timespec="seconds")
                    history.append(superseded)
                entries[key] = {
                    "heard": word,
                    "contact_id": contact.get("id"),
                    "recorded": datetime.now().isoformat(timespec="seconds"),
                    "history": history,
                }
                _save_store(entries)
            return f"recorded: {word} -> {_display(contact)}"
    except Exception as e:  # noqa: BLE001 — a correction must never fail the turn
        logger.warning(f"[heard_names] record failed: {e}")
        return "not recorded: error"


# ---------------------------------------------------------------------------
# The note
# ---------------------------------------------------------------------------

def _scope(persona: str | None):
    if not persona:
        return nullcontext()
    from core.persona import persona_scope
    return persona_scope(persona)


def _candidates(text: str) -> list[str]:
    """
    Capitalised words that are not starting a sentence. Whisper capitalises proper nouns;
    every sentence also starts with a capital, so a sentence-initial word is skipped
    wholesale — the review measured that including them puts a false hint on most turns.
    The cost, accepted: a name that opens a sentence goes unchecked.
    """
    out, seen = [], set()
    text = text or ""
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0)
        if not tok[0].isupper():
            continue
        word = re.sub(r"'s$", "", tok).strip("'-")
        low = word.lower()
        if len(word) < 3 or low in _NOT_NAMES or low in seen:
            continue
        before = text[max(0, m.start() - _BREAK_WINDOW):m.start()]
        if m.start() <= _BREAK_WINDOW and not text[:m.start()].strip(" \"'([\t"):
            continue                                   # the message's first word
        if _SENTENCE_BREAK_RE.search(before) and not _ABBREV_BEFORE_RE.search(before):
            continue
        seen.add(low)
        out.append(word)
        if len(out) >= _MAX_CANDIDATES:
            break
    return out


def _archived_names(contacts: list[dict], known: set[str]) -> dict[str, dict]:
    """Words of merged-away records that no live contact carries → the survivor."""
    out: dict[str, dict] = {}
    try:
        archive = CRM._crm_archive_dir()
        if not archive.exists():
            return out
        for path in archive.glob("*.json"):
            if path.name.startswith("premerge_"):
                continue
            try:
                rec = json.loads(path.read_text())
            except (OSError, ValueError):
                continue
            if not isinstance(rec, dict) or not rec.get("merged_into"):
                continue
            survivor = _live_contact(contacts, rec.get("id") or "") or _live_contact(
                contacts, rec["merged_into"])
            if not survivor:
                continue
            for w in _contact_words(rec) - known:
                out.setdefault(w, survivor)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[heard_names] archive scan skipped: {e}")
    return out


def name_notes(text: str, persona: str | None = None) -> str:
    """
    The `[Name note: …]` lines for one user message, or "" when there is nothing to say.
    Appended to the Coordinator's input and nowhere else.
    """
    try:
        with _scope(persona):
            words = _candidates(text)
            if not words:
                return ""
            contacts = CRM._load_contacts()
            known = _known_words(contacts)
            store = _load_store()
            archived = None
            spoken = {}
            for c in contacts:
                s = _spoken_first(c)
                if s:
                    spoken.setdefault(s.lower(), c)
            named = set()
            for c in contacts:
                named |= _name_words(c)
            notes = []
            for word in words:
                low = word.lower()
                if low in named:
                    continue                                   # rule 1: never touched
                if low in known:
                    # Only a nickname or referred_to_as: say who it means.
                    who = [c for c in contacts if low in _contact_words(c)][:2]
                    names = " or ".join(_display(c) for c in who)
                    notes.append(
                        f'[Name note: "{word}" is what the user calls {names}. Read it as '
                        f'{names} unless the message introduces a new or different person.]')
                    if len(notes) >= MAX_NOTES:
                        break
                    continue
                corrected = None
                entry = store.get(low)
                if entry:
                    corrected = _live_contact(contacts, entry.get("contact_id") or "")
                if corrected is None:
                    if archived is None:
                        archived = _archived_names(contacts, known)
                    corrected = archived.get(low)
                if corrected is not None:
                    name = _display(corrected)
                    notes.append(
                        f'[Name note: "{word}" is not one of the user\'s contacts, and the user '
                        f'has corrected it to {name} before. Read it as {name} unless the message '
                        f'introduces a new or different person.]')
                else:
                    near = [c for s, c in spoken.items() if _sounds_like(low, s)]
                    if near:
                        names = " or ".join(_display(c) for c in near[:2])
                        # Wording chosen by A/B on Flash-Lite, 2026-10-23, five runs a side:
                        # this read a misheard Eva as Iva (or asked) 5/5 against 3-4/5 for
                        # "ask if unclear", and still kept a genuinely new Ella 5/5.
                        notes.append(
                            f'[Name note: "{word}" is not one of the user\'s contacts; it sounds '
                            f'like {names}. Read it as {names} unless the message makes clear '
                            f'this is someone else; if something would be saved or sent under '
                            f'either name and you are not sure, ask.]')
                if len(notes) >= MAX_NOTES:
                    break
            return ("\n\n" + "\n".join(notes)) if notes else ""
    except Exception as e:  # noqa: BLE001 — a hint must never cost a turn
        logger.warning(f"[heard_names] note skipped: {e}")
        return ""


# ---------------------------------------------------------------------------
# The Coordinator's MISHEARD line
# ---------------------------------------------------------------------------

_MISHEARD_LINE_RE = re.compile(r"^MISHEARD:\s*(.+)$", re.MULTILINE)
_PAIR_RE = re.compile(r'["“]?([A-Za-z][A-Za-z\'\-]*)["”]?\s*(?:->|→|=>)\s*["“]?([^";,\]]+?)["”]?\s*$')


def _said(word: str, text: str) -> bool:
    return bool(re.search(rf"\b{re.escape(word)}\b", text or "", re.IGNORECASE))


def handle_coordinator_output(coord_output: str, persona: str | None = None,
                              user_input: str | None = None) -> list[str]:
    """
    Record every `MISHEARD: "heard" -> Correct Name` pair the Coordinator wrote. Returns the
    result lines (for the log). A template slot filled with "None"/"N/A" is not a pair.

    **Only a correction the user actually made.** Both names must appear in the user's own
    message ("it's Manny, not Benny"). Without this a Flash-Lite Coordinator, reading this
    module's own sound-alike note, can fill the slot by reflex — the same template-filling
    that produced 93 of 174 null USER_CORRECTION events — and the store would then claim
    "the user has corrected it before" about a correction that never happened.
    """
    results = []
    try:
        from tools.logger import is_null_ish
        for m in _MISHEARD_LINE_RE.finditer(coord_output or ""):
            payload = m.group(1).strip()
            if is_null_ish(payload):
                continue
            for part in re.split(r"[;,]", payload):
                pm = _PAIR_RE.match(part.strip())
                if not pm:
                    continue
                heard, meant = pm.group(1), pm.group(2).strip()
                meant_first = (_TOKEN_RE.findall(meant) or [""])[0]
                if user_input is not None and not (_said(heard, user_input)
                                                   and _said(meant_first, user_input)):
                    results.append(f"not recorded: the user's message does not name both "
                                   f"{heard} and {meant_first}")
                    continue
                results.append(record_misheard(heard, meant, persona))
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[heard_names] MISHEARD handling failed: {e}")
    for r in results:
        logger.info(f"[heard_names] {r}")
    return results


# ---------------------------------------------------------------------------
# Whisper vocabulary
# ---------------------------------------------------------------------------

def vocabulary(persona: str | None = None, limit: int = VOCABULARY_LIMIT) -> list[str]:
    """
    The names this user is likeliest to say, most recently in touch first. CONTACTS ONLY —
    never a stored correction: biasing Whisper toward a corrected name would pull a new
    Bonnie toward Johnny before anything downstream could see it.
    """
    try:
        with _scope(persona):
            contacts = sorted(CRM._load_contacts(),
                              key=lambda c: str(c.get("last_contact") or ""), reverse=True)
    except Exception as e:  # noqa: BLE001
        logger.warning(f"[heard_names] vocabulary skipped: {e}")
        return []
    out, seen = [], set()
    for c in contacts:
        s = _spoken_first(c)
        if s and s.lower() not in seen:
            seen.add(s.lower())
            out.append(s)
        if len(out) >= limit:
            break
    return out
