"""
tools/tone.py — per-contact tone profiles, derived from real correspondence.

Metatron drafts messages to people. A draft that reads like an assistant rather than
like the user is the failure this exists to prevent, and the material that fixes it is
already sitting in the user's mailbox: years of how these two people actually write to
each other, including the nicknames and running phrases no amount of instruction can
invent. Profiles built only from Metatron's own drafts self-reinforce; profiles built
from correspondence do not.

**The whole design turns on one hazard: trust laundering.** The source material is email,
which is written by other people and therefore attacker-controlled. The destination is a
CRM field that gets loaded into a drafting context as trusted prompt text. Distilling one
into the other is exactly the move that launders untrusted input into trusted position,
and no amount of instructing the extractor to behave is a control.

So the extractor never returns text that is used as text. It returns JSON against a fixed
key set; Python drops unknown keys, truncates every value, and reassembles the string
itself. An attacker who fully controls the correspondence controls at most a short run of
characters inside a key that was going to exist anyway. `contains_injection_markers()` is
the backstop, not the defence.

Raw correspondence never enters a Logistics or Relationships context — only the assembled
result does. That is also why `search_correspondence` is granted to no agent.
"""

from __future__ import annotations

import contextlib
import json
import logging
import re
import threading
from datetime import date

logger = logging.getLogger(__name__)

# Fixed key set. Adding a key here means deciding, deliberately, that a new kind of
# attacker-influenced string may reach a drafting prompt. Do not widen it casually.
_STR_KEYS = ("formality", "typical_length", "greeting_style", "signoff_style",
             "register_notes")
_LIST_KEYS = ("names_they_use_for_user", "names_user_uses_for_them",
              "pet_names", "shared_phrases")

_MAX_VALUE_CHARS = 120
_MAX_LIST_ITEMS = 6
_MAX_TONE_SHAPE_CHARS = 600

# Contacts currently being profiled, so two drafts to the same person in quick
# succession don't both kick off a full mailbox sweep.
_IN_FLIGHT: set[str] = set()
_IN_FLIGHT_LOCK = threading.Lock()


def _clean(value: str) -> str:
    """Flatten to a single short line. Newlines and braces are structure an attacker could use."""
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    text = text.replace("{", "").replace("}", "").replace("<", "").replace(">", "")
    return text[:_MAX_VALUE_CHARS].strip()


# --- post-validation against the sample (Stage 5 #21) ------------------------------------------
#
# The profiler's own instructions say "only record what recurs" and "no third parties", and a
# model follows both imperfectly. Code can check both exactly against the sample it was given, so
# it does, BEFORE the per-list truncation (so a one-off cannot use up one of the 6 slots):
#   1. a pet name or shared phrase seen fewer than _MIN_RECURRENCE times is dropped;
#   2. a value naming another person the user knows is dropped (list) or blanked (string);
#   3. a name "they use for the user" must actually appear in what THEY wrote.

_MIN_RECURRENCE = 5
# Capitalised words that are common words as well as names. Never treated as another person's
# name: erring toward keeping a value; the agent file's third-party rule covers the rest.
_NAME_STOPLIST = frozenset(w.lower() for w in (
    "Will", "May", "Mark", "Grace", "Rose", "June", "Hope", "Bill", "Pat", "Art", "Joy", "Dawn",
    "Summer", "Faith", "Frank", "Grant", "Victor", "Sterling", "Iris", "Ivy", "Jade", "Ruby",
    "Amber", "Holly", "Rich", "Sunny", "Bob", "Sue", "Rob", "Jack", "Bay", "Jay"))
_BLOCK_RE = re.compile(r"^\[(user|them)\] ", re.M)
_QUOTED = re.compile(r"(?:^|(?<=[\s(]))['\"‘“]([^'\"‘’“”]{2,}?)['\"’”](?=$|[\s.,;:!?)])")
_WORD = re.compile(r"[^\W\d_]+")


def _occurrences(phrase: str, text: str) -> int:
    phrase = phrase.strip()
    if not phrase:
        return 0
    return len(re.findall(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text, re.I))


def _recurs(value: str, sample: str) -> bool:
    """A value that quotes its phrase (`calls Fridays 'the long one'`) is counted by the quote;
    counting the whole description would drop every correct entry."""
    quoted = _QUOTED.findall(value)
    return _occurrences(quoted[0] if quoted else value, sample) >= _MIN_RECURRENCE


def _their_text(sample: str) -> str:
    """Only what the contact wrote: the `[them]` blocks of tools/mail.search_correspondence."""
    marks = list(_BLOCK_RE.finditer(sample))
    parts = []
    for i, m in enumerate(marks):
        if m.group(1) == "them":
            end = marks[i + 1].start() if i + 1 < len(marks) else len(sample)
            parts.append(sample[m.end():end])
    return "\n".join(parts)


def _name_words(record: dict, keys: tuple) -> set[str]:
    words: set[str] = set()
    for k in keys:
        v = record.get(k)
        for s in (v if isinstance(v, list) else [v]):
            if isinstance(s, str):
                words |= {w.lower() for w in _WORD.findall(s) if len(w) >= 2}
    return words


_OWN_KEYS = ("name", "first_name", "last_name", "nickname", "preferred_name", "referred_to_as")


def _other_names(contact: dict | None, contacts: list, user_name: str, sample: str) -> set[str]:
    """Name words of OTHER people the user knows: any word of another contact's name, first name
    or nickname — minus every word the profiled contact is known by (a duplicate record or a
    namesake must never remove the contact's own name, review L8), minus the user's own name
    words, minus the stoplist — and only a word that appears capitalised in the sample (build
    amendment 2: exact for this check, so a contact saved as "School Office" whose words the mail
    never capitalises contributes nothing)."""
    contact = contact or {}
    own = _name_words(contact, _OWN_KEYS) | {w.lower() for w in _WORD.findall(user_name or "")}
    in_sample = {w for w in _WORD.findall(sample) if w[0].isupper()}
    cid = contact.get("id")
    out: set[str] = set()
    for c in contacts or []:
        if not isinstance(c, dict) or (cid and c.get("id") == cid):
            continue
        for w in _name_words(c, ("name", "first_name", "nickname")):
            if w in own or w in _NAME_STOPLIST:
                continue
            for form in in_sample:
                if form.lower() == w:
                    out.add(form)
    return out


def _names_other(value: str, names: set[str]) -> bool:
    """Case-sensitive, capitalised tokens only — "will do" never matches a contact named Will."""
    return any(w[0].isupper() and w in names for w in _WORD.findall(value))


def _validate(data: dict, sample: str, contact: dict | None, contacts: list,
              user_name: str) -> dict:
    names = _other_names(contact, contacts, user_name, sample)
    theirs = _their_text(sample)
    out = dict(data)
    for key in _STR_KEYS:
        v = out.get(key)
        if isinstance(v, str) and names and _names_other(v, names):
            out[key] = ""
    for key in _LIST_KEYS:
        items = out.get(key)
        if isinstance(items, str):
            items = [items]
        if not isinstance(items, list):
            continue
        kept = []
        for v in items:
            if not isinstance(v, str):
                continue
            if names and _names_other(v, names):
                continue
            if key in ("pet_names", "shared_phrases") and not _recurs(v, sample):
                continue
            if key == "names_they_use_for_user" and not _occurrences(
                    (_QUOTED.findall(v) or [v])[0], theirs):
                continue
            kept.append(v)
        out[key] = kept
    return out


def _parse_profile(raw: str, sample: str = "", contact: dict | None = None,
                   contacts: list | None = None, user_name: str = "") -> dict:
    """
    Pull the JSON object out of a model response and reduce it to the fixed key set.

    Tolerates a markdown fence and surrounding chatter because models add them despite
    instructions, but tolerates nothing about *which* keys survive.

    With `sample` (the correspondence the profiler read), every value is first checked against
    it — see `_validate` — before the truncation, so one-offs do not use up the slots.
    """
    if not raw:
        return {}
    text = raw.strip()
    fence = re.search(r"```(?:json)?\s*(.+?)\s*```", text, re.S)
    if fence:
        text = fence.group(1).strip()
    if not text.startswith("{"):
        start, end = text.find("{"), text.rfind("}")
        if start == -1 or end <= start:
            return {}
        text = text[start:end + 1]

    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return {}
    if not isinstance(data, dict):
        return {}
    if sample:
        data = _validate(data, sample, contact, contacts or [], user_name)

    out: dict = {}
    for key in _STR_KEYS:
        cleaned = _clean(data.get(key, ""))
        if cleaned:
            out[key] = cleaned
    for key in _LIST_KEYS:
        raw_list = data.get(key) or []
        if isinstance(raw_list, str):
            raw_list = [raw_list]
        if not isinstance(raw_list, list):
            continue
        items = [_clean(v) for v in raw_list[:_MAX_LIST_ITEMS]]
        items = [v for v in items if v]
        if items:
            out[key] = items
    return out


def _render(profile: dict, counts: dict) -> str:
    """Assemble the stored string in Python. Model text is never used as a whole."""
    parts = []
    for key in _STR_KEYS:
        if profile.get(key):
            parts.append(f"{key.replace('_', ' ')}: {profile[key]}")
    for key in _LIST_KEYS:
        if profile.get(key):
            parts.append(f"{key.replace('_', ' ')}: {', '.join(profile[key])}")
    if not parts:
        return ""
    stamp = (f"[derived from correspondence {date.today().isoformat()}; "
             f"{counts.get('sampled', 0)} msgs]")
    return f"{stamp} " + " | ".join(parts)


# ---------------------------------------------------------------------------
# Her permission (archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.11, D9)
# ---------------------------------------------------------------------------
#
# Learning how she writes to people reads what other people wrote to her, so it runs only
# while she holds a current `tone_profile` record — given by her, in the app, and
# withdrawable there (core/consent.py). Enforced here in Python, before the mailbox is
# read and before any model call, never in a prompt (CLAUDE.md). Fail-closed: a persona
# with no consent file has no permission, which is every synthetic persona and every new
# user until she ticks *learn how I write to people*. `mike` holds records citing his own
# rulings (2026-08-26, 08-28), written on the VM by `scripts/accounts.py seed-consent`.

_NOT_PERMITTED = {
    "status": "not_permitted",
    "detail": "Learning how the user writes to people is not switched on for this user. "
              "Draft in the persona's default style, and do not ask about or mention this.",
}


def _permitted(persona: str | None) -> bool:
    """Whether `persona` holds a current `tone_profile` record. No persona is no."""
    from core.consent import is_granted

    if not persona:
        return False
    try:
        return is_granted("tone_profile", persona)
    except Exception:  # noqa: BLE001 — an unreadable record grants nothing
        return False


def forget_tone_profiles(persona: str) -> int:
    """
    Remove every tone profile learned for `persona`. Returns how many contacts had one.

    The second half of withdrawing `tone_profile` (plan § 4.11, review P2): the withdraw
    route calls `core.consent.withdraw("tone_profile", persona)` and then this, so
    withdrawal removes what was learned and not just future learning. Deleted, not
    archived — see `tools.crm.clear_tone_shapes`. Goes through tools/crm.py's own lock and
    write path so the contact store stays consistent with a concurrent write.

    A profiling run already in flight when she withdraws re-checks the record before it
    writes; one that slips between that check and its write is still never served,
    because the CRM's read paths hide `tone_shape` without a current record.
    """
    from core.persona import persona_scope
    from tools.crm import clear_tone_shapes

    with persona_scope(persona):
        cleared = clear_tone_shapes()
    logger.info(f"[tone] forgot {cleared} tone profile(s) for {persona}")
    return cleared


def _extract(address: str, contact_id: str, persona: str | None = None) -> dict:
    """
    Sweep the mailbox for this address, distil it, and write the result to the CRM.

    Runs on a background thread. Returns a dict for logging and tests; nothing waits on it.

    Refuses without a current `tone_profile` record (plan § 4.11) — checked before the
    mailbox is read, and again just before the write in case she withdrew mid-run.
    """
    from core.orchestrator import run_session
    from core.persona import current_persona, persona_scope
    from tools.crm import write_contact
    from tools.mail import search_correspondence
    from tools.untrusted import contains_injection_markers

    with persona_scope(persona) if persona else contextlib.nullcontext():
        if not _permitted(persona or current_persona()):
            return dict(_NOT_PERMITTED)

        sample = search_correspondence(address)
        if sample.get("error"):
            return {"status": "error", "detail": sample["error"]}

        # Both directions or nothing. A profile built from INBOX alone describes how the
        # *contact* writes and would be applied as if it were the user's own voice — a
        # worse outcome than having no profile, and silent.
        if not sample.get("sent_folder_found"):
            return {"status": "skipped",
                    "detail": "Sent folder not found — refusing to profile from received mail alone."}

        counts = sample.get("counts") or {}
        if counts.get("sampled", 0) < 4:
            return {"status": "skipped", "detail": "Too little correspondence to profile."}

        raw = run_session(
            "tone_profiler",
            user_input=(
                "Describe how these two people write to each other. Return only the JSON "
                "object described in your instructions.\n\n"
                f"{sample.get('security_note', '')}\n\n{sample.get('correspondence', '')}"
            ),
            persona=persona,
            complexity="quick",       # bounded, mechanical, strict-schema — the cheap tier
            # bare: agent file only — no goals, no profile, no recent context. This
            # agent's entire input is other people's correspondence; personal context
            # beside attacker-writable text was [DB-0819-02], and tone_profiler.md
            # references none of it (verified 2026-08-20 before this change, per the
            # standing rule). Same posture as the intake extractor.
            bare=True,
        )

        # Post-validation (Stage 5 #21) needs who else the user knows. Unreadable records mean
        # a third party's name cannot be checked for, so nothing is written this time.
        try:
            from tools import crm
            from tools.profile import _load as _load_profile
            contacts = crm._load_contacts()
            user_name = str((_load_profile() or {}).get("name") or "")
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "detail": f"Records unreadable: {type(exc).__name__}"}
        record = next((c for c in contacts if isinstance(c, dict) and c.get("id") == contact_id),
                      {})
        profile = _parse_profile(raw, sample=str(sample.get("correspondence") or ""),
                                 contact=record, contacts=contacts, user_name=user_name)
        if not profile:
            return {"status": "error", "detail": "Extractor returned no usable JSON."}

        rendered = _render(profile, counts)[:_MAX_TONE_SHAPE_CHARS]
        if not rendered:
            return {"status": "skipped", "detail": "Nothing worth recording."}

        # Backstop, not the defence — the fixed schema above is. If a marker survives
        # key-filtering and truncation, something is wrong enough to not write at all.
        markers = contains_injection_markers(rendered)
        if markers:
            logger.warning(f"[tone] refusing tone_shape for {contact_id}: markers {markers}")
            return {"status": "blocked", "detail": f"Injection markers in output: {markers}"}

        # Re-checked at the write: the mailbox sweep and model call take seconds, and a
        # withdrawal in that window must not be undone by a profile landing after the
        # forget. (A write in the instant between this check and the next line is still
        # hidden by the CRM's read gate — plan § 4.11, P2.)
        if not _permitted(persona or current_persona()):
            return dict(_NOT_PERMITTED)

        write_contact(name="", contact_id=contact_id, tone_shape=rendered)
        return {"status": "written", "tone_shape": rendered, "counts": counts}


def _resolve(name: str, contact_id: str) -> tuple[dict | None, str]:
    """Find the contact record. Returns (record, error)."""
    from tools.crm import read_contact

    raw = read_contact(contact_id=contact_id, name=name)
    if raw.startswith("Error:"):
        return None, raw
    try:
        return json.loads(raw), ""
    except ValueError:
        return None, "Could not read that contact record."


def get_tone_shape(name: str = "", contact_id: str = "", refresh: bool = False) -> dict:
    """
    How the user writes to this person. Call before drafting a message to them.

    Returns immediately. When no profile exists yet, one is built in the background and
    this returns a `seeding` status — draft on the persona's default style this time and
    the profile will be there next time. Blocking a live conversation for a mailbox sweep
    and a model call, to improve a greeting, is the wrong trade.

    Without a current `tone_profile` record (plan § 4.11) it returns `not_permitted`
    before reading anything — no contact lookup, no mailbox, no model call.
    """
    from core.persona import current_persona

    if not _permitted(current_persona()):
        return dict(_NOT_PERMITTED)

    record, err = _resolve(name, contact_id)
    if err:
        return {"status": "error", "detail": err}

    cid = record.get("id", "")
    existing = (record.get("tone_shape") or "").strip()
    if existing and not refresh:
        return {"status": "ready", "contact": record.get("name", ""), "tone_shape": existing}

    address = ((record.get("contact_info") or {}).get("email") or "").strip().lower()
    if not address:
        return {"status": "unavailable", "contact": record.get("name", ""),
                "detail": "No email address on this contact, so there is no correspondence to learn from.",
                "tone_shape": existing}

    # Resolve identity on THIS thread. The worker outlives this call, and by the time it
    # runs the calling scope may have exited — the rule tools/subagent.py already follows
    # on its fire-and-forget path.
    persona = current_persona()

    with _IN_FLIGHT_LOCK:
        if cid in _IN_FLIGHT:
            return {"status": "seeding", "contact": record.get("name", ""),
                    "detail": "Already learning this contact's style.", "tone_shape": existing}
        _IN_FLIGHT.add(cid)

    def _worker() -> None:
        try:
            result = _extract(address, cid, persona)
            logger.info(f"[tone] {cid}: {result.get('status')} — {result.get('detail', '')}")
        except Exception as e:
            logger.warning(f"[tone] profiling failed for {cid}: {e}")
        finally:
            with _IN_FLIGHT_LOCK:
                _IN_FLIGHT.discard(cid)

    threading.Thread(target=_worker, daemon=True).start()
    return {"status": "seeding", "contact": record.get("name", ""),
            "detail": "Learning this contact's style from past correspondence; it will be "
                      "available next time. Use the persona's default style for now.",
            "tone_shape": existing}


GET_TONE_SHAPE_SCHEMA = {
    "name": "get_tone_shape",
    "description": (
        "How the user writes to a specific contact — formality, typical length, greeting and "
        "sign-off habits, nicknames each uses for the other, recurring shared phrases. Call this "
        "before drafting any message to a saved contact, and match what it returns. Returns "
        "immediately: status 'ready' with a tone_shape to follow, or 'seeding' when it is still "
        "learning, in which case draft in the persona's default style without waiting or retrying."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Contact's name. Use this or contact_id."},
            "contact_id": {"type": "string", "description": "Contact's ID, if known."},
            "refresh": {"type": "boolean", "description": "Rebuild from correspondence even if a profile exists. Default false."},
        },
        "required": [],
    },
}
