"""
tools/escalation.py — the clinical escalation inbox. [DB-0808-06], built 2026-09-03.

THE PIECE THAT WAS MISSING (Mike's ruling, 2026-09-03)
------------------------------------------------------
`[DB-0808-06]` was filed as "a flagged clinical thread can never be marked resolved",
and both it and `ROADMAP.md` § A7 explain the refusal the same way: a tier-2 thread
closes only by "administrative acknowledgment", which is "a system that does not exist
yet — there is no next-of-kin or clinician channel anywhere in the codebase".

Reading it back on 2026-09-03, Mike named the actual gap, which is upstream of closing:
**a tier-2 clinical flag alerts nothing.** It surfaces once in conversation, moves to
`watch`, and then sits in a context file that only the model reads. Nobody is notified.
The close problem was the visible end of that; the alert problem is the whole of it.

So this is the destination. Every tier-2 clinical thread lands here the moment it is
raised, and stays as `pending` until something acknowledges it. One day that routing goes
to a next of kin or a physician. Today it goes nowhere, and THE RECORD SAYS SO IN SO MANY
WORDS rather than leaving the gap to be inferred — a queue that looks like it is being
read, and is not, is worse than an obviously empty one.

WHAT THIS IS NOT
----------------
It is not a crisis service and must never be described as one, here or anywhere a user
can see. It does not notify anyone, it is not monitored, and nothing about it is real
time. It is a durable record that a flag was raised, so that the flag is not carried
forever inside a file only a language model reads.

WHY THE TIER-2 REFUSAL STILL STANDS
------------------------------------
Nothing here lets a session resolve a tier-2 thread. `tools/context_tracker.py` still
coerces `resolved` to `watch` on the conversational path, for the reason it always did: a
crisis thread must not close on a reassuring reply. What changes is that there is now a
second path — code-raised, model-excluded, user-approved through `tools/confirm.py` — and
an archive that keeps the whole history when it is taken.

SENSITIVE TIER
--------------
Clinical flags are sensitive data. Persona-scoped, local-only, 0600, never sent anywhere
— the same handling as the context tracker this feeds from.
"""

import json
import logging
import os
from datetime import date, datetime
from pathlib import Path

from core.persona import persona_data_dir

logger = logging.getLogger(__name__)

# Stated on every record rather than assumed. When a real channel exists, this string is
# what a search finds — and until then it is what stops a reader assuming the queue is
# being routed somewhere.
NO_ROUTE_YET = (
    "not routed — no next-of-kin or clinician channel exists in this deployment yet; "
    "this record is a local trace only and notifies nobody"
)

_STATUSES = ("pending", "acknowledged", "archived")


def _inbox_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "clinical" / "escalations.json"


def _load(persona: str | None = None) -> list[dict]:
    path = _inbox_path(persona)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        # Same posture as tools/context_tracker._read_raw: a damaged inbox must not take
        # down the turn that is trying to write to it. The write below preserves rather
        # than replaces — see _save.
        logger.warning("[escalation] inbox unreadable; treating as empty for this read")
        return []


def _save(entries: list[dict], persona: str | None = None) -> None:
    path = _inbox_path(persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    # If what is on disk is unreadable, keep it before replacing it. This file is the
    # only record that a crisis flag was ever raised; losing one silently is the failure
    # this module exists to prevent, not an acceptable cost of recovering from a bad
    # parse. Same guard, same reasoning, as tools/context_tracker._preserve_corrupt.
    if path.exists():
        try:
            json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            import shutil
            stamp = datetime.now().strftime("%Y%m%dT%H%M%S")
            kept = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
            try:
                if not kept.exists():
                    shutil.copy2(path, kept)
                    os.chmod(kept, 0o600)
                    logger.warning("[escalation] unreadable inbox preserved as %s",
                                   kept.name)
            except Exception:  # noqa: BLE001 — preservation must not break the write
                pass
    with open(path, "w") as f:
        json.dump(entries, f, indent=2)
    os.chmod(path, 0o600)


def raise_escalation(flag: str, note: str = "", raised: str = "",
                     persona: str | None = None) -> dict | None:
    """
    Record that a tier-2 clinical thread exists. Idempotent per flag.

    Called from Python when the thread is written — never by a model, which is the same
    rule `_thread_tier` follows: being told a thread is serious is not the same as
    deriving that it is.

    Idempotent because the Synthesizer re-submits its whole `clinical_threads` list every
    turn. Without this, one concern raised on a Tuesday would be a hundred identical
    escalations by Friday, and the queue that is supposed to make a flag visible would be
    the thing burying it. Returns the entry when one was created, else None.

    Never raises. An escalation that cannot be recorded must not cost the user the
    response that was being composed when the flag fired.
    """
    try:
        flag = str(flag or "").strip()
        if not flag:
            return None
        entries = _load(persona)
        for e in entries:
            if e.get("flag") == flag and e.get("status") != "archived":
                return None
        entry = {
            "flag": flag,
            "note": str(note or "").strip(),
            "raised": raised or date.today().isoformat(),
            "recorded": datetime.now().isoformat(timespec="seconds"),
            "status": "pending",
            "routed_to": NO_ROUTE_YET,
        }
        entries.append(entry)
        _save(entries, persona)
        logger.warning("[escalation] tier-2 clinical flag recorded: %s", flag)
        return entry
    except Exception as exc:  # noqa: BLE001 — see docstring
        logger.warning("[escalation] could not record %r: %s", flag, exc)
        return None


def list_escalations(status: str = "", persona: str | None = None) -> list[dict]:
    """Every escalation, or only those in one status. Newest last, as recorded."""
    entries = _load(persona)
    if status:
        return [e for e in entries if e.get("status") == status]
    return entries


def archive_escalation(flag: str, basis: str, persona: str | None = None) -> bool:
    """
    Close an escalation, keeping everything it held.

    `basis` is what the close rests on, in the closer's words. It is required and not
    defaulted: a close with no recorded basis cannot be reviewed later, and this is the
    one record that has to survive being read a year afterwards by someone reconstructing
    what happened. `tools/obligations.py` refuses an evidence-free close for the same
    reason.

    Archive, never delete — the project's standing rule. The entry keeps its flag, its
    note, when it was raised and that it was never routed; it gains who closed it and on
    what. Returns True if something was archived.
    """
    flag = str(flag or "").strip()
    basis = str(basis or "").strip()
    if not flag or not basis:
        return False
    entries = _load(persona)
    changed = False
    for e in entries:
        if e.get("flag") == flag and e.get("status") != "archived":
            e["status"] = "archived"
            e["archived"] = datetime.now().isoformat(timespec="seconds")
            e["archived_basis"] = basis
            # Recorded explicitly because the deployment is single-user: the person
            # closing a clinical escalation is also its subject. That is not a flaw to be
            # hidden in an omission; it is the standing limit of this design until a
            # third-party channel exists, and the record should say who acted.
            e["archived_by"] = "user, on review"
            changed = True
    if changed:
        _save(entries, persona)
        logger.warning("[escalation] archived: %s", flag)
    return changed


def pending_beyond(days: int, persona: str | None = None) -> list[dict]:
    """
    Pending escalations older than `days` — what the periodic review acts on.

    The dwell is the protection. A tier-2 thread must not be closeable in the same hour
    it was raised, because the person answering is the person it is about; time is the
    only thing standing in for the second opinion this deployment does not have.
    """
    out = []
    today = date.today()
    for e in _load(persona):
        if e.get("status") != "pending":
            continue
        try:
            raised = date.fromisoformat(str(e.get("raised") or ""))
        except ValueError:
            continue
        if (today - raised).days >= days:
            out.append(e)
    return out


# How long a tier-2 escalation sits before a close is even offered, and how long between
# offers once it is. Both are deliberately slow.
#
# COST, named at the moment the cadence is set (the standing rule): the review runs
# through core/scheduler.fire_function — a direct Python call with NO model session — on
# a daemon that is already running. Its marginal cost is a JSON read of a file holding a
# handful of records: no tokens, no standing resource, nothing billed by wall-clock time,
# and no meter needs to grow to cover it. Raising the cadence to hourly would not change
# that; the 14/7 figures are chosen entirely for what they do to a person, not for spend.
#
# 14 days, because the dwell IS the protection: the person answering the card is the
# person the flag is about, and time is the only thing standing in for the second opinion
# this deployment does not have. 7 days between offers, because a crisis flag that
# reappears every morning is a tool nagging someone about the worst thing in their life.
REVIEW_DWELL_DAYS = 14
REVIEW_REOFFER_DAYS = 7


def review_clinical_escalations(persona: str | None = None,
                                dwell_days: int = REVIEW_DWELL_DAYS) -> str:
    """
    The periodic check. Offers a close for escalations that have sat long enough.

    Raised BY CODE and never by a model — the `add_zone` rule in tools/confirm.py's
    executor table. A model that could raise this card could argue its way toward a
    closed crisis thread, which is the exact failure the tier-2 refusal exists to
    prevent. Nothing here decides anything: it puts the question to the user through the
    confirmation channel, where the model is not in the consent path at all.

    It NEVER auto-archives. There is no recipient to route to yet, so an automatic close
    would resolve a crisis flag on the strength of a timer and nothing else. Returns a
    one-line summary for the scheduler log.
    """
    from tools.confirm import request

    due = pending_beyond(dwell_days, persona)
    if not due:
        return "clinical escalation review: nothing due"

    entries = _load(persona)
    by_flag = {e.get("flag"): e for e in entries}
    today = date.today()
    offered = 0

    for item in due:
        flag = item.get("flag", "")
        last = str(item.get("last_review_raised") or "")
        if last:
            try:
                if (today - date.fromisoformat(last[:10])).days < REVIEW_REOFFER_DAYS:
                    continue
            except ValueError:
                pass
        raised = item.get("raised", "unknown")
        note = item.get("note") or "(no detail recorded)"
        description = (
            f"Close a flagged health concern?\n\n"
            f"  Raised {raised}\n"
            f"  {note}\n\n"
            f"This has been carried since it was raised and has not been reviewed. "
            f"Approve to close it and keep the full record; decline to keep carrying it. "
            f"Nothing about it has been sent to anyone."
        )
        try:
            request("close_clinical_escalation",
                    {"flag": flag, "basis": f"user review, {today.isoformat()}"},
                    description=description, persona=persona)
        except Exception as exc:  # noqa: BLE001
            logger.warning("[escalation] could not offer review for %r: %s", flag, exc)
            continue
        target = by_flag.get(flag)
        if target is not None:
            target["last_review_raised"] = today.isoformat()
        offered += 1

    if offered:
        _save(entries, persona)
    return f"clinical escalation review: {offered} offered, {len(due)} due"


def close_clinical_escalation(flag: str, basis: str, confirm_token: str = "",
                              persona: str | None = None) -> str:
    """
    Archive an escalation and administratively resolve its clinical thread.

    THE ONLY PATH BY WHICH A TIER-2 THREAD EVER REACHES `resolved`. Reached exclusively
    through tools/confirm.execute() after the user approves the card above — the token is
    required and spent here, so a direct call with no approval performs nothing. The
    conversational path in tools/context_tracker._merge_clinical_threads still coerces
    `resolved` to `watch` and is unchanged; a session cannot reach this.
    """
    from tools.confirm import consume

    args = {"flag": flag, "basis": basis}
    ok, reason = consume(confirm_token, "close_clinical_escalation", args, persona=persona)
    if not ok:
        return f"Error: not closed. {reason}"

    if not archive_escalation(flag, basis, persona):
        return f"Error: no open escalation found for '{flag}'."

    from tools.context_tracker import administratively_resolve
    administratively_resolve(flag, persona=persona)
    return f"Closed and archived: {flag}. The full record is kept."


def _register_confirm_executor() -> None:
    try:
        from tools.confirm import _EXECUTORS
        _EXECUTORS.setdefault("close_clinical_escalation",
                              ("tools.escalation", "close_clinical_escalation"))
    except Exception:  # noqa: BLE001
        # An import failure must not take the inbox down. The gate still refuses to close
        # anything without an approval, which is the half that matters.
        pass


_register_confirm_executor()
