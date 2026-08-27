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
import logging
import os
import re
from datetime import date, datetime
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

# ---------------------------------------------------------------------------
# Open-thread timestamps and expiry
#
# WHY THIS EXISTS: "post-travel recovery" stayed listed as live context for two weeks after it
# stopped being true — `open_threads` carried no metadata at all, so nothing could even ask how
# old an entry was, let alone decide it was stale. Timestamping (`added`, below) shipped first
# and closed [DB-0814-02] as scoped. This comment records two follow-on decisions: an auto-drop
# policy (Mike, 2026-08-15), and a same-day correction to it once the first version turned out
# to be inert against the exact incident it was built for.
#
# DECISION: auto-drop at write time, nothing destroyed.
#   - Cutoff: 7 days (`_OPEN_THREAD_EXPIRY_DAYS`). The originating incident ran for two weeks —
#     clearly too long — and this project's rhythm is daily-ish sessions, so a thread that has
#     survived a full week of sessions without being dropped by the model itself is the one worth
#     querying, not silently trusting. Half the incident's duration was chosen deliberately: long
#     enough that a thread spanning a busy week (the ordinary case) never gets cut mid-relevance,
#     short enough that it cannot re-create a two-week stale belief.
#   - A thread that crosses the cutoff is *moved*, not deleted, to `expired_open_threads` in the
#     same tracker file — same archive-on-merge spirit as the rest of the project. That list is
#     capped at `_EXPIRED_OPEN_THREADS_CAP` entries (oldest dropped first) so the file cannot grow
#     unbounded, and it is loaded on disk but never returned by `read_context_tracker()` — the
#     same "archived but never loaded" pattern already used for resolved clinical threads below.
#   - The model is never asked to judge staleness, for the same reason `added` is server-stamped
#     below: asked "is this still relevant," a model will get it wrong and reset the clock every
#     turn, which is the original incident's exact failure mode.
#   - Threads with no `added` date (legacy data written before timestamping existed, see
#     `_normalize_open_threads`) are never auto-expired — there is no reliable age to test, and
#     guessing would risk silently dropping live context that predates this feature.
#
# CORRECTION (Mike, 2026-08-15, same day): the first cut of the grace rule treated "the thread's
# text is present in this write's `open_threads`" as proof of active re-assertion. It is not.
# `open_threads` is replace-semantics and the Synthesizer re-emits the *entire* list on every
# single turn via the inline [CONTEXT] block — not the Diarist, not once per session. So "resent
# this turn" was true of every live thread, every write, which means the grace condition could
# never be false for a thread that was still nominally open — exactly the shape of the original
# incident: "post-travel recovery" would have been granted grace on every one of the dozens of
# writes across those two weeks and never expired. The first version was correct against its own
# tests and inert against the bug it was written to fix.
#
# This is the same class of mistake `_frame_proactive()` in core/orchestrator.py was built to
# fix (commit 82d394b): the system's own repeated output was being read as evidence of the
# user's intent, because nothing distinguished who actually produced the text. The fix there was
# to stop trusting *origin* (scheduler prompt labelled as user speech); the fix here is to stop
# trusting *mere presence* (Synthesizer re-listing labelled as active re-assertion). Same
# principle: the system re-stating its own prior output is not evidence of anything.
#
# CORRECTED GRACE RULE: a thread past the cutoff is archived unless one of two things is true.
# Mere presence in `open_threads` this turn is no longer sufficient on its own.
#
#   1. The USER's own turn engages the thread (`user_text`, an optional parameter on
#      `write_context_tracker` — defaults to None so every existing caller is unaffected).
#      Matched by content-word overlap (`_user_engages_thread`) rather than substring, because
#      most input here is speech-to-text: wording, tense and filler vary turn to turn, so
#      byte-identical matching would almost never fire. The threshold is a named constant
#      (`_USER_ENGAGEMENT_OVERLAP`) for the same reason the cutoff is a named constant — so the
#      next session tuning it does not have to go hunting for a magic number.
#   2. The thread's TEXT MATERIALLY CHANGED. This needs no new matching code, and the reason is
#      the existing carry-forward logic in `_merge_open_threads` below: it keys entirely on exact
#      text. A thread the Synthesizer has genuinely reworded arrives this turn as text that does
#      not match the stored entry, so `_merge_open_threads` already treats it as a brand-new
#      thread and stamps it with today's date — that *is* "the clock resets," achieved by the
#      pre-existing mechanism, not by this rework. The only piece this rework's expiry step
#      (`_expire_open_threads`) needs to get right is the OLD wording: since it does not appear
#      in `incoming` this turn either, it is evaluated purely on age and user engagement like any
#      other omitted thread — if it was already past the cutoff, it is archived (correctly: it
#      has been superseded by the reworded entry, not merely dropped); if not, it is silently
#      dropped by ordinary replace semantics, exactly as reword-without-expiry has always
#      behaved. No special-casing was added for "changed text" because none was needed — it
#      would have duplicated behaviour the merge step already provides.
#
# EXTENSION beyond the literal brief, needed to make the correction actually hold: the same
# "mere presence is not evidence" principle has to apply AFTER a thread is archived too, not
# only at the instant it crosses the cutoff. Without this, a thread archived on this write would
# immediately re-enter `open_threads` on the SAME write — `_merge_open_threads` sees text with no
# match in `still_eligible` (it was just moved out) and treats it as a brand-new thread, stamped
# today. On a caller that keeps resending identical text turn after turn (per the CORRECTION
# above, this project's actual caller), that reproduces the original incident one write later,
# forever, oscillating archived/revived every other write. `write_context_tracker` therefore
# filters `open_threads` against the full archive (prior + newly expired) before merging, and a
# match is dropped unless `_user_engages_thread` grants grace for it too. See the comment at that
# filter for the mechanics.
#
# The date is server-stamped, never taken from the model, for the same reason `raised` is
# server-stamped on clinical threads above: a model asked to invent "when did this start" will
# get it wrong or reset it, and the resend-the-same-sentence-every-turn behaviour that caused the
# original incident would just reset the clock each time. So the model-facing shape is unchanged
# (a plain string per thread); `_merge_open_threads` below is what turns that into a timestamped
# record, matching an existing entry by exact text so a thread that is simply carried forward
# keeps its original `added` date instead of looking freshly opened every session.
# ---------------------------------------------------------------------------

_OPEN_THREAD_EXPIRY_DAYS = 7
_EXPIRED_OPEN_THREADS_CAP = 50

# Overlap coefficient (shared-words / smaller-set-size, not Jaccard) between a thread's content
# words and the user's own turn. Dividing by the smaller set means a short thread description
# is not penalised against a long, rambling turn — same technique as core/rule_classes.py's
# similarity(), reimplemented locally rather than imported so this module's only cross-domain
# dependency stays the persona layer; the two callers (rule-conflict sweep vs. thread relevance)
# have different enough tuning needs that sharing the function would couple them for no benefit.
# 0.34 (~1/3 of the smaller side) was picked, not measured against real transcripts: it is loose
# enough that a short user turn ("still sorting the bookstore numbers") clears it against a
# thread text sharing two or three content words, tight enough that an unrelated turn sharing one
# stray word does not. Revisit against real speech-to-text transcripts once they exist — flagged
# in the handoff as the part most likely to need retuning.
_USER_ENGAGEMENT_OVERLAP = 0.34

_STOPWORDS = {
    "a", "about", "after", "again", "all", "also", "an", "and", "any", "are", "as", "at", "be",
    "been", "being", "but", "by", "can", "could", "did", "do", "does", "for", "from", "had",
    "has", "have", "how", "i", "if", "in", "into", "is", "it", "its", "just", "like", "me", "my",
    "no", "not", "of", "on", "or", "our", "should", "so", "some", "still", "that", "the", "their",
    "then", "there", "these", "this", "those", "to", "too", "very", "was", "we", "were", "what",
    "when", "where", "which", "who", "will", "with", "would", "you", "your",
}


def _content_words(text: str) -> set[str]:
    """Lowercase alpha tokens, 3+ letters, minus `_STOPWORDS`. See `_USER_ENGAGEMENT_OVERLAP`."""
    return {w for w in re.findall(r"[a-z']{3,}", (text or "").lower()) if w not in _STOPWORDS}


def _user_engages_thread(thread_text: str, user_text: str | None) -> bool:
    """
    Grace signal 1: does the USER's own turn plausibly reference this thread?

    `user_text` must come from the user's message, never from anything the system generated —
    that distinction is the entire point of this rework (see CORRECTION above). This function
    only does the matching; the caller is responsible for the origin guarantee.
    """
    if not user_text:
        return False
    thread_words = _content_words(thread_text)
    turn_words = _content_words(user_text)
    if not thread_words or not turn_words:
        return False
    overlap = len(thread_words & turn_words) / min(len(thread_words), len(turn_words))
    return overlap >= _USER_ENGAGEMENT_OVERLAP


def _merge_open_threads(incoming: list | None, existing: list[dict]) -> list[dict]:
    """
    Stamp incoming open threads with an `added` date, carrying it forward when a thread is
    simply being re-sent unchanged.

    `open_threads` is replace-semantics like `patterns`/`follow_ups` (unlike `clinical_threads`,
    which merges) — a thread the model omits this turn is dropped. What this function preserves
    is only the *age* of a thread that survives: if the same text was open last session, its
    original `added` date carries over; new text gets stamped today.

    Accepts plain strings (the normal, model-facing shape) or already-timestamped dicts
    (round-tripping data this module itself produced), so a caller passing either shape back
    through does not need special-casing.
    """
    today = date.today().isoformat()
    existing_by_text = {t.get("text"): t.get("added") for t in existing if t.get("text")}

    out: list[dict] = []
    for item in incoming or []:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            added = item.get("added")
        else:
            text = str(item or "").strip()
            added = None
        if not text:
            continue
        out.append({"text": text, "added": added or existing_by_text.get(text) or today})
    return out


def _expire_open_threads(
    existing: list[dict], user_text: str | None, today: str
) -> tuple[list[dict], list[dict]]:
    """
    Split the on-disk open threads (already normalized) into (still_eligible, newly_expired)
    based on `_OPEN_THREAD_EXPIRY_DAYS`, BEFORE `_merge_open_threads` runs.

    `still_eligible` feeds straight into `_merge_open_threads` unchanged — a thread inside the
    cutoff window is untouched here and gets the normal carry-forward-the-original-date
    treatment exactly as before this feature existed.

    A thread that has crossed the cutoff is handled here instead of there. There is
    deliberately no "is this text present in `open_threads` this turn" check — see the
    CORRECTION note above `_OPEN_THREAD_EXPIRY_DAYS`; the Synthesizer re-emits the whole list on
    every turn, so presence proves nothing about relevance:
      - `_user_engages_thread(text, user_text)` is true (grace signal 1, the user's own turn
        references it) -> stays in `still_eligible` with `added` cleared, so `_merge_open_threads`
        treats it as a brand new thread and stamps it with today's date — one fresh stamp.
      - otherwise -> `newly_expired`. Archived with its original `added` date plus an
        `expired_on` stamp; never deleted. This also covers a thread that was reworded (grace
        signal 2): the old wording is not in `incoming` either way, and if it has crossed the
        cutoff by the time it is superseded, archiving it here is correct — see the comment
        above for why no separate handling is needed for that case.

    A thread with `added is None` (legacy pre-timestamp data, or unparseable) is always kept in
    `still_eligible` — there is no reliable age to test, so it is never auto-expired.
    """
    still: list[dict] = []
    expired: list[dict] = []
    for t in existing:
        text = t.get("text")
        added = t.get("added")
        if not text or not added:
            still.append(t)
            continue
        try:
            age_days = (date.today() - date.fromisoformat(added)).days
        except ValueError:
            still.append(t)
            continue
        if age_days <= _OPEN_THREAD_EXPIRY_DAYS:
            still.append(t)
        elif _user_engages_thread(text, user_text):
            still.append({"text": text, "added": None})
        else:
            expired.append({**t, "expired_on": today})
    return still, expired


def _normalize_open_threads(raw: list | None) -> list[dict]:
    """
    Read-time migration: wrap old bare-string entries as `{"text": ..., "added": None}` rather
    than crashing on data written before this change. `added: None` (not today) so a thread that
    predates timestamping is not misreported as freshly opened.
    """
    out: list[dict] = []
    for item in raw or []:
        if isinstance(item, dict):
            out.append({"text": str(item.get("text") or ""), "added": item.get("added")})
        else:
            out.append({"text": str(item or ""), "added": None})
    return out


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


logger = logging.getLogger(__name__)


def _tracker_path() -> Path:
    return persona_data_dir() / "context.json"


def _audit_path() -> Path:
    return persona_data_dir() / "context_audit.jsonl"


def _append_audit(added: list[str], removed: list[str], expired: list[str],
                  open_count: int) -> None:
    """
    Append one line describing what this write did to the open threads.

    [DB-0814-02] `context.json` is overwritten in place, so it records a state and no
    history. Twelve days after thread expiry shipped the live file read
    `expired_open_threads: 0` with four threads open — which is equally consistent with
    "grace legitimately keeps everything alive" and "expiry has silently never fired", and
    nothing on disk could tell the two apart. One append-only line per write is what makes
    that question answerable: an expiry now leaves a mark whether or not the archive is
    later capped or the thread is later resent.

    Never raises. An audit line that could break a context write would be worse than no
    audit line — the tracker is on the response path.
    """
    try:
        path = _audit_path()
        entry = {
            "ts": datetime.now().isoformat(timespec="seconds"),
            "added": added,
            "removed": removed,
            "expired": expired,
            "open_count": open_count,
        }
        with open(path, "a") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        os.chmod(path, 0o600)
    except Exception as exc:
        logger.warning(f"[context_tracker] audit line not written: {exc}")


def read_context_tracker() -> dict:
    """
    Read the session context — open threads, recent patterns, follow-ups,
    held items, and the date of the last session.

    Returns:
        Dict with keys: last_session, open_threads, patterns, follow_ups, held_items,
        clinical_threads. Returns empty structure if no tracker file exists yet.

        `open_threads` entries are dicts: `{"text": str, "added": <ISO date or None>}`.
        `added` is None for threads written before timestamping existed — see
        `_normalize_open_threads`. A thread older than `_OPEN_THREAD_EXPIRY_DAYS` is dropped
        from this list at write time and moved to `expired_open_threads` on disk — see
        `_expire_open_threads`. That field is never included in this return value, the same
        "archived but never loaded" pattern used for resolved clinical threads just below.

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
    # Migrate pre-timestamp open_threads (bare strings) rather than crashing on old data.
    data["open_threads"] = _normalize_open_threads(data.get("open_threads"))
    # Archived, never loaded into session context — see the module-level comment above
    # _OPEN_THREAD_EXPIRY_DAYS. Mirrors the resolved-clinical-thread filter just below.
    data.pop("expired_open_threads", None)

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
    open_threads: list,
    patterns: list[str],
    follow_ups: list[str],
    held_items: list[str] | None = None,
    clinical_threads: list[dict] | None = None,
    user_text: str | None = None,
) -> str:
    """
    Update the session context at close of each exchange.

    Replaces the current tracker with the updated state. Call after every
    meaningful exchange. Keep entries concise — one sentence each.

    Args:
        open_threads: Unresolved topics to carry forward, as plain strings.
                      E.g. ["bookstore P&L review scheduled for Thursday"].
                      Stamped with an `added` date on write (server-side, not model-supplied);
                      a thread re-sent with the same text keeps its original `added` date rather
                      than looking freshly opened every session. A thread older than
                      `_OPEN_THREAD_EXPIRY_DAYS` is auto-dropped and archived unless `user_text`
                      shows the user engaging it, or its wording has materially changed — see the
                      module comment above `_OPEN_THREAD_EXPIRY_DAYS`.
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
        user_text:    The USER's own turn this exchange — never system-generated text (see the
                      CORRECTION note above `_OPEN_THREAD_EXPIRY_DAYS`: the Synthesizer's own
                      re-listing of a thread is not evidence the thread is still relevant).
                      Optional; defaults to None so existing callers are unaffected. Used only
                      to grant a past-cutoff open thread grace when the user's words plausibly
                      reference it — see `_user_engages_thread`.

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

    today = date.today().isoformat()
    still_eligible, newly_expired = _expire_open_threads(
        _normalize_open_threads(existing.get("open_threads")), user_text, today
    )

    prior_expired_open_threads = existing.get("expired_open_threads") or []
    if not isinstance(prior_expired_open_threads, list):
        prior_expired_open_threads = []

    # An archived thread does not silently walk back into `open_threads` just because its exact
    # text is still present in `incoming` — that is the same "mere presence is not evidence"
    # principle this rework exists to enforce, and it has to apply AFTER archiving too, not only
    # at the moment a thread crosses the cutoff. Without this, a thread archived this very call
    # would immediately re-enter through `_merge_open_threads` treating its now-unmatched text as
    # a brand-new thread (stamped today) — undoing the drop in the same write that made it, and
    # on a caller that keeps resending identical text, reproducing the original incident exactly
    # one write later every time. Only the same two signals that grant grace before archiving can
    # bring a thread back afterwards: the user engaging it, or the caller sending different
    # wording (which is not "the same thread" under this module's exact-text identity anyway, and
    # is handled for free by `_merge_open_threads`'s normal new-thread path).
    archived_texts = {t.get("text") for t in prior_expired_open_threads if t.get("text")}
    archived_texts |= {t.get("text") for t in newly_expired if t.get("text")}

    def _text_of(item) -> str:
        return str((item.get("text") if isinstance(item, dict) else item) or "").strip()

    filtered_incoming = [
        item for item in (open_threads or [])
        if _text_of(item) not in archived_texts or _user_engages_thread(_text_of(item), user_text)
    ]

    stamped_open_threads = _merge_open_threads(filtered_incoming, still_eligible)

    expired_open_threads = prior_expired_open_threads
    if newly_expired:
        expired_open_threads = expired_open_threads + newly_expired
    if len(expired_open_threads) > _EXPIRED_OPEN_THREADS_CAP:
        expired_open_threads = expired_open_threads[-_EXPIRED_OPEN_THREADS_CAP:]

    tracker = {
        "last_session": today,
        "open_threads": stamped_open_threads,
        "patterns": patterns,
        "follow_ups": follow_ups,
        "held_items": held_items or [],
        "clinical_threads": threads,
        "expired_open_threads": expired_open_threads,
    }

    with open(path, "w") as f:
        json.dump(tracker, f, indent=2)

    os.chmod(path, 0o600)

    # [DB-0814-02] The audit line, beside the file it describes. `removed` is the third
    # category and is not the same as `expired`: a thread the model simply stopped sending
    # leaves under replace-semantics without ever reaching the cutoff, and reading those two
    # as one number is what would make "expiry never fires" invisible all over again.
    _before = {t.get("text") for t in _normalize_open_threads(existing.get("open_threads"))
               if t.get("text")}
    _after = {t.get("text") for t in stamped_open_threads if t.get("text")}
    _expired_now = [t.get("text") for t in newly_expired if t.get("text")]
    _append_audit(
        added=sorted(_after - _before),
        removed=sorted(_before - _after - set(_expired_now)),
        expired=_expired_now,
        open_count=len(stamped_open_threads),
    )

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
                    "Things mentioned that weren't resolved or need follow-up, as plain "
                    "sentences — the tracker stamps each with an open date itself, so do not "
                    "include a date here. "
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
