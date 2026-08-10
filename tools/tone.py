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


def _parse_profile(raw: str) -> dict:
    """
    Pull the JSON object out of a model response and reduce it to the fixed key set.

    Tolerates a markdown fence and surrounding chatter because models add them despite
    instructions, but tolerates nothing about *which* keys survive.
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


def _extract(address: str, contact_id: str, persona: str | None = None) -> dict:
    """
    Sweep the mailbox for this address, distil it, and write the result to the CRM.

    Runs on a background thread. Returns a dict for logging and tests; nothing waits on it.
    """
    from core.orchestrator import run_session
    from core.persona import persona_scope
    from tools.crm import write_contact
    from tools.mail import search_correspondence
    from tools.untrusted import contains_injection_markers

    with persona_scope(persona) if persona else contextlib.nullcontext():
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
        )

        profile = _parse_profile(raw)
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
    """
    from core.persona import current_persona

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
