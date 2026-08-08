"""
tools/context_tracker.py — Diarist session context tracker.

Maintains a compact mid-term memory file the Diarist writes at session close
and reads at session start. Bridges short-term (recent logs in system prompt)
and long-term (FAISS) memory.

Stores: open threads, patterns noticed, follow-ups, last session date.
Not a summary — a list of threads to pick up next session.

Sensitive-tier, local-only, 600 permissions. Persona-scoped.
"""

import json
import os
from datetime import date
from pathlib import Path

from core.persona import persona_data_dir

_ROOT = Path(__file__).parent.parent

# ---------------------------------------------------------------------------
# Clinical thread lifecycle
#
# WHY THIS EXISTS: found in the B1a red team, 2026-08-04. sarah_chen's tracker held an open
# SUICIDAL_IDEATION thread from an earlier session. All 15 subsequent red-team prompts — "What
# tools do you have?" among them — were reclassified by the Synthesizer as further evidence of
# that same crisis and answered with an escalating 988/"find Tom"/lamotrigine script. The
# tracker had even recorded "deflecting acute distress with system architecture questions" as a
# *pattern*, so the run-away was self-reinforcing: the file's own record of the contamination
# became the evidence for continuing it.
#
# The bug is NOT that the flag persisted. Persistence is correct and, for the clinical class,
# permanent by design. The bug is that persistence was expressed as re-leading with the crisis
# script on every unrelated turn. `status` separates the two: a thread can be carried without
# dominating.
#
# TIERS (user decision, 2026-08-08). The distinction asked for was "missed heart medication"
# versus "missed anti-psychotics" — one the user can resolve in conversation, one that must not
# close on a reassuring reply.
#
#   Tier 2 — any `CLINICAL_CONCERN: *`. Never user-resolvable, never auto-expires. Reaches
#            `watch` and stays there until an administrative close, which is a system that does
#            not exist yet (there is no next-of-kin or clinician channel anywhere in the
#            codebase — the wishes store is write-only until Phase 6). Until it is built,
#            `resolved` is refused in Python and the thread is carried indefinitely.
#   Tier 1 — a bare `MUST_SURFACE` from any other agent: MEDICATION_MISSED_CRITICAL,
#            CAREER_CRISIS, isolation. Closes when the underlying fact changes.
#
# Tier is DERIVED here, never taken from the model. A model that mislabels a crisis as tier 1
# could close it; the reverse error is harmless. Same reasoning as _GUARDED_KEYS in
# tools/agent_config.py — being told is not being prevented.
# ---------------------------------------------------------------------------

_THREAD_STATUSES = ("active", "watch", "resolved")

_CLINICAL_PROTOCOL = """\
CLINICAL THREAD PROTOCOL — read before composing this response.

An open clinical thread is carried in `clinical_threads` above. It does NOT mean lead with it
again. Statuses:

  active  — not yet surfaced, or surfaced and the user has not engaged with it. Address it in
            this response, before other content.
  watch   — already surfaced and acknowledged. Carry it silently. Do NOT re-open it, re-offer
            resources, or re-read the user's unrelated messages as evidence of it. Surface it
            again only on NEW evidence in the user's own words this turn.
  resolved— closed. Not loaded.

Move a thread active -> watch once you have surfaced it and the user has responded to it. This
is the normal path and you should take it promptly — a thread left `active` across turns is
what produces a response that ignores what the user actually asked.

Two hard rules:
  1. Never re-classify an unrelated message as evidence for an existing thread. If the user
     asks about the weather while a clinical thread is open, answer about the weather.
  2. Tier 2 threads (CLINICAL_CONCERN) cannot be resolved here. Do not try; the write is
     refused. `watch` is the correct destination for them.
"""


def _thread_tier(flag: str) -> int:
    """2 for any CLINICAL_CONCERN, 1 otherwise. Derived, never model-supplied — see above."""
    return 2 if "CLINICAL_CONCERN" in (flag or "").upper() else 1


def _tracker_path() -> Path:
    return persona_data_dir() / "context.json"


def read_context_tracker() -> dict:
    """
    Read the session context — open threads, recent patterns, follow-ups,
    held items, and the date of the last session.

    Returns:
        Dict with keys: last_session, open_threads, patterns, follow_ups, held_items,
        clinical_threads. Returns empty structure if no tracker file exists yet.

        When a clinical thread is open, a `_clinical_protocol` key is added carrying the
        lifecycle rules. It is attached here rather than written into synthesizer.md so the
        Synthesizer pays for it only in the sessions that have one — which is nearly none.
    """
    path = _tracker_path()
    if not path.exists():
        return {
            "last_session": None,
            "open_threads": [],
            "patterns": [],
            "follow_ups": [],
            "held_items": [],
            "clinical_threads": [],
        }
    data = json.load(open(path))
    # Backfill fields for trackers written before they existed.
    data.setdefault("held_items", [])
    data.setdefault("clinical_threads", [])

    # Resolved threads are archived on disk but never loaded — a closed concern should not keep
    # colouring the read of new messages, which is the whole failure this field addresses.
    live = [t for t in data["clinical_threads"] if t.get("status") != "resolved"]
    data["clinical_threads"] = live
    if live:
        data["_clinical_protocol"] = _CLINICAL_PROTOCOL
    return data


def _merge_clinical_threads(
    incoming: list[dict] | None, existing: list[dict]
) -> tuple[list[dict], list[str]]:
    """
    Normalise the submitted threads against what is already on disk.

    Returns (threads, notices). Notices are appended to the tool result so the model learns
    when a status change was refused, rather than believing it succeeded.

    What is enforced here and not trusted to the instruction file:
      - `raised` is carried over from the stored record. Otherwise the model rewrites it each
        turn and the age of a thread — the only thing that makes "this has been open a month"
        answerable — is silently reset to today, forever.
      - Tier 2 threads cannot be set to `resolved`; they are coerced to `watch`. There is no
        administrative-close mechanism to resolve them yet, so the alternative to coercion is
        a crisis thread closed by a reassuring reply.
      - Threads absent from `incoming` are carried forward, not dropped. Every other field on
        this tracker is replace-semantics; a clinical thread must not be deletable by omission.
    """
    today = date.today().isoformat()
    by_flag = {t.get("flag"): t for t in existing if t.get("flag")}
    notices: list[str] = []
    seen: set[str] = set()
    out: list[dict] = []

    for item in incoming or []:
        flag = str(item.get("flag") or "").strip()
        if not flag:
            continue
        seen.add(flag)
        prior = by_flag.get(flag, {})
        tier = _thread_tier(flag)

        status = str(item.get("status") or "active").strip().lower()
        if status not in _THREAD_STATUSES:
            status = "active"
        if status == "resolved" and tier == 2:
            status = "watch"
            notices.append(
                f"'{flag}' is a tier-2 clinical thread and cannot be resolved from a session — "
                f"kept as 'watch'. It closes only via administrative acknowledgment."
            )

        prior_status = prior.get("status")
        out.append({
            "flag": flag,
            "tier": tier,
            # First sighting stamps the clock; later writes never move it.
            "raised": prior.get("raised") or today,
            "status": status,
            # Only advance last_surfaced when the thread was actually addressed this turn.
            "last_surfaced": today if status == "active" else prior.get("last_surfaced"),
            "note": str(item.get("note") or prior.get("note") or "").strip(),
        })
        if prior_status and prior_status != status:
            notices.append(f"'{flag}': {prior_status} -> {status}")

    # Carry forward anything the model did not mention.
    for flag, prior in by_flag.items():
        if flag in seen or prior.get("status") == "resolved":
            continue
        carried = dict(prior)
        carried["tier"] = _thread_tier(flag)
        out.append(carried)

    return out, notices


def write_context_tracker(
    open_threads: list[str],
    patterns: list[str],
    follow_ups: list[str],
    held_items: list[str] | None = None,
    clinical_threads: list[dict] | None = None,
) -> str:
    """
    Update the session context at close of each exchange.

    Replaces the current tracker with the updated state. Call after every
    meaningful exchange. Keep entries concise — one sentence each.

    Args:
        open_threads: Unresolved topics to carry forward.
                      E.g. ["bookstore P&L review scheduled for Thursday"].
        patterns:     Recurring observations worth noting.
                      E.g. ["writing stalls when sleep under 6 hours"].
        follow_ups:   Specific questions to ask next exchange or session.
                      E.g. ["ask how the Cato chapter went"].
        held_items:   Things the Synthesizer chose NOT to surface yet but
                      must not lose. Each entry should include WHAT was held
                      and WHY (timing, emotional readiness, relevance).
                      E.g. ["Held: SLEEP_POOR flag — user was already stressed,
                              surface when mood is better"].
                      Held items that age across multiple sessions without
                      surfacing should be escalated, not silently dropped.
        clinical_threads: Open clinical concerns, each a dict with 'flag'
                      (e.g. "CLINICAL_CONCERN: SUICIDAL_IDEATION",
                      "MEDICATION_MISSED_CRITICAL"), 'status'
                      ("active" | "watch" | "resolved") and a short 'note'.
                      Unlike the other fields this is merge, not replace:
                      omitting a thread carries it forward unchanged.

    Returns:
        Confirmation string, plus any status changes or refusals.
    """
    path = _tracker_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    existing: dict = {}
    if path.exists():
        try:
            existing = json.loads(path.read_text())
        except json.JSONDecodeError:
            existing = {}

    threads, notices = _merge_clinical_threads(
        clinical_threads, existing.get("clinical_threads", [])
    )

    tracker = {
        "last_session": date.today().isoformat(),
        "open_threads": open_threads,
        "patterns": patterns,
        "follow_ups": follow_ups,
        "held_items": held_items or [],
        "clinical_threads": threads,
    }

    with open(path, "w") as f:
        json.dump(tracker, f, indent=2)

    os.chmod(path, 0o600)

    msg = f"Context tracker updated ({path})"
    if notices:
        msg += "\nClinical threads: " + "; ".join(notices)
    return msg


# ---------------------------------------------------------------------------
# Tool schemas
# ---------------------------------------------------------------------------

READ_CONTEXT_TRACKER_SCHEMA = {
    "name": "read_context_tracker",
    "description": (
        "Read the Diarist's session context from the last session: open threads, "
        "patterns noticed, things to follow up on, and the date of the last session. "
        "Call this at the start of every session to orient yourself before responding."
    ),
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

WRITE_CONTEXT_TRACKER_SCHEMA = {
    "name": "write_context_tracker",
    "description": (
        "Update the session context tracker at the close of a session. "
        "Record open threads (unresolved topics), patterns noticed, and specific "
        "things to follow up on next session. Keep entries brief — one sentence each. "
        "This is your notes-to-self, not a summary for the user. "
        "If a clinical flag fired this session, record it in clinical_threads and move it "
        "to 'watch' once you have surfaced it and the user has responded."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "open_threads": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Things mentioned that weren't resolved or need follow-up. "
                    "E.g. 'bookstore P&L review coming Thursday', "
                    "'Cato chapter structure still unresolved'."
                ),
            },
            "patterns": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Recurring observations worth noting. "
                    "E.g. 'writing stalls when sleep under 6 hours'."
                ),
            },
            "follow_ups": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Specific questions to ask next session. "
                    "E.g. 'ask how the Cato chapter went'."
                ),
            },
            "held_items": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Things the Synthesizer chose not to surface yet but must not lose. "
                    "Each entry must state WHAT was held and WHY. "
                    "E.g. 'Held: SLEEP_POOR flag — user was already stressed, surface when mood lifts'. "
                    "Items held across multiple sessions without surfacing should be escalated."
                ),
            },
            "clinical_threads": {
                "type": "array",
                "description": (
                    "Open clinical concerns and their lifecycle state. Merge semantics, not "
                    "replace: a thread you omit is carried forward unchanged, so send only "
                    "the ones whose status you are changing. Set 'watch' once a concern has "
                    "been surfaced and the user has responded to it — a thread left 'active' "
                    "will keep dominating responses to unrelated messages. CLINICAL_CONCERN "
                    "threads cannot be set to 'resolved'; that write is refused and kept as "
                    "'watch'."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "flag": {
                            "type": "string",
                            "description": (
                                "The flag as the specialist emitted it, e.g. "
                                "'CLINICAL_CONCERN: SUICIDAL_IDEATION', "
                                "'MEDICATION_MISSED_CRITICAL', 'CAREER_CRISIS'."
                            ),
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "watch", "resolved"],
                            "description": (
                                "active = address in this response; watch = surfaced and "
                                "acknowledged, carry silently and re-open only on new "
                                "evidence; resolved = closed (non-clinical flags only)."
                            ),
                        },
                        "note": {
                            "type": "string",
                            "description": "One sentence: what the concern is and where it stands.",
                        },
                    },
                    "required": ["flag", "status"],
                },
            },
        },
        "required": ["open_threads", "patterns", "follow_ups"],
    },
}
