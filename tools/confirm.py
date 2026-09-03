"""
tools/confirm.py — human-in-the-loop confirmation for irreversible actions.

Roadmap B2 requires this, and item 5 of the Phase 5 plan makes it a prerequisite for any
outward-facing tool. Until 2026-08-04 the entire control was a prompt: `synthesizer.md`
described action tiers requiring confirmation, and nothing enforced them.

**Why a prompt was not enough.** On 2026-08-03 `logistics` was not granted
`write_agent_config`, its instruction file described the capability, and it called the
tool three times in production — the dispatcher executed each one. Being *told* is not
being *prevented*. A confirmation rule written in an agent file has exactly the same
standing as that grant did.

## The design decision that matters: consent does not pass through the model

A token the model receives and later presents back is a token the model can present
without ever having asked. A model that has been talked into acting by a hostile email
is precisely the model whose claim "the user said yes" cannot be trusted — and that is
the case this exists for, so relying on its word would defeat the mechanism at the only
moment it is needed.

So approval is recorded **out of band**: the user taps a control in the app, the server
records it against the token, and the model is not in that path. The model can propose;
only the user can approve. `POST /confirm` in `core/server.py` is the only writer.

## Flow

    1. Agent calls send_email(...)                     → tool returns PENDING_CONFIRMATION,
                                                          performs nothing
    2. Synthesizer surfaces the description to the user
    3. User taps Approve in the app                    → POST /confirm {token}
                                                          server marks it approved and
                                                          calls execute(), which spends it

The approval is spent by the **server**, not by a second model call. The pending record
stores the *exact* arguments from step 1, and `consume()` refuses if they have changed —
so an approval for "email Sarah the itinerary" cannot be spent on "email everyone the
medical file".

**Why the server finishes the job (2026-08-15, `[DB-0815-03]`).** Until this change the
flow had a fourth step — *the agent calls the tool again with `confirm_token`* — and that
step had nothing that could reach it. The token is returned inside a tool result, which
lives only in the pipeline session that produced it; by the user's next turn it is gone
from the model's context by construction, so the retry the design depended on could not
happen even when the app nudged the pipeline after the tap. Observed live: Mike approved
a real email, and the reply told him it was "waiting for your approval in the app". The
approval then expired silently at the TTL.

That is the failure `synthesizer.md` calls the worst available outcome — the user has
performed the deliberate act the whole mechanism rests on and has every reason to believe
it landed. Executing here takes the model out of the *execution* path as well as the
*consent* path, which was always this file's stated intent. It does not weaken the
mechanism: `execute()` still goes through `consume()`, so single-use, expiry and the
argument fingerprint all apply exactly as before.

Pending requests expire (default 10 minutes). An approval the user granted an hour ago,
for something they have forgotten, is not consent.

## Declining (2026-08-27, `[DB-0827-01]`)

Until this date "No" did nothing at all: the app dismissed the card client-side and the
record stayed pending, so the five-second poll put the same prompt back on screen every
five seconds for the remaining ten minutes. Mike, on the first decline ever performed:
*"If I decline it keeps asking in a loop. In the end I approved to break the loop."*

A gate whose cheapest escape is consent authorises by exhaustion, which is the exact
inversion of everything above. `decline()` removes the pending record so the poll stops,
and — because "the user said no to this" is a fact worth keeping, not a non-event —
appends it to a ledger beside the pending store with its action fingerprint intact. The
fingerprint is what lets a later proposal be recognised as the same action already
refused; see `recent_declines()`.
"""

from __future__ import annotations

import json
import secrets
import threading
import time
from pathlib import Path
from typing import Any

from core.persona import persona_data_dir

TTL_SECONDS = 600
_LOCK = threading.Lock()


def _store_path(persona: str | None = None) -> Path:
    p = persona_data_dir(persona) / "pending_confirmations.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _declined_path(persona: str | None = None) -> Path:
    p = persona_data_dir(persona) / "declined_confirmations.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def _load(persona: str | None = None) -> dict:
    path = _store_path(persona)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        # A corrupt store must not authorise anything. Starting empty means outstanding
        # approvals are lost and must be re-granted, which is the safe direction.
        return {}


def _save(data: dict, persona: str | None = None) -> None:
    path = _store_path(persona)
    path.write_text(json.dumps(data, indent=2))
    try:
        path.chmod(0o600)
    except OSError:
        pass


def _prune(data: dict) -> dict:
    now = time.time()
    return {k: v for k, v in data.items() if v.get("expires_at", 0) > now}


def _fingerprint(action: str, args: dict) -> str:
    """Stable identity for an action plus its arguments."""
    return json.dumps({"action": action, "args": args}, sort_keys=True, default=str)


# How long a refusal stands against being re-proposed from carried context.
#
# [DB-0827-01] This is a lifetime, so it is chosen rather than defaulted. 24 hours is the
# span over which the SAME context is carried: `load_recent_context` reads the tracker and
# the last five days of logs, the scheduler runs its jobs on a daily cycle, and every one of
# those runs re-reads the material the first proposal came from. A window shorter than a day
# leaves the next morning's scheduled run free to raise the identical card off the identical
# context, which is the loop; a window materially longer starts suppressing proposals whose
# grounds have genuinely moved on, and does it silently.
#
# What it costs: nothing standing. No process, no timer, no stored state beyond the ledger
# entry that tools/confirm.decline() already writes, and one read of a small local JSON file
# per confirmation request. Nothing here is billed by wall-clock time and no meter needs to
# watch it.
#
# What happens at expiry: the window closing does not delete or alter anything. The ledger
# record persists — capped by count at _DECLINED_LIMIT, never by age — so "was this refused?"
# stays answerable afterwards; only the automatic suppression lapses. Archive-on-merge: the
# refusal is kept, it simply stops being enforced.
_REPROPOSE_WINDOW_SECONDS = 24 * 60 * 60


def _recently_declined(action: str, args: dict, persona: str | None = None) -> dict | None:
    """
    The most recent refusal of this exact action within the window, or None.

    Matched on the fingerprint, so "email Sarah the itinerary" being refused does not
    suppress "email Sarah the address". A record whose args did not survive the tamper check
    in decline() carries no fingerprint and matches nothing — X is not known, so it cannot be
    used to suppress a proposal of X.
    """
    fingerprint = _fingerprint(action, args)
    matches = [r for r in declined(_REPROPOSE_WINDOW_SECONDS, persona)
               if r.get("fingerprint") == fingerprint]
    return matches[-1] if matches else None


def request(action: str, args: dict, description: str,
            persona: str | None = None) -> dict:
    """
    Record a pending action and return the payload a tool should hand back instead of acting.

    `description` is what the user will read and approve. Write it so it stands alone —
    they may see it without the surrounding conversation, and it is the only thing
    standing between a persuasive email and a real send.

    **A refusal stands.** [DB-0827-01] The decline path stopped the five-second poll putting
    the same card straight back; it did not stop the next turn proposing the identical action
    again off the same carried context, which is the same loop one layer up and just as
    slow to escape. So a request matching an action refused inside
    `_REPROPOSE_WINDOW_SECONDS` raises no card at all unless something genuinely new has
    happened since the refusal — the user speaking, or a new item arriving — which
    tools/turn_context.py answers and this function does not attempt to judge.

    When a re-proposal IS allowed, the pending record remembers that it follows a refusal, so
    the user can be told they are being asked again. Being asked twice without being told is
    the same discourtesy in a quieter register.
    """
    prior = _recently_declined(action, args, persona)
    if prior is not None:
        from tools.turn_context import new_trigger_since
        if not new_trigger_since(prior.get("declined_at") or 0, persona):
            when = time.strftime("%H:%M", time.localtime(prior.get("declined_at") or 0))
            # User-fact language only. This payload is read by the Synthesizer and can reach
            # the user's reply, so it says what the user did and what did not happen —
            # never how that was determined. Same discipline as PENDING_CONFIRMATION above.
            return {
                "status": "DECLINED_RECENTLY",
                "description": prior.get("description", "") or description,
                "declined_at": when,
                "instruction": (
                    f"The user declined this at {when} and it has not been raised again. "
                    "Nothing has been performed and nothing is waiting for them. Do not "
                    "ask them to reconsider and do not offer it again in this session — "
                    "their answer was no. If they raise it themselves, or something "
                    "genuinely new about it comes up, it can be proposed then."
                ),
            }

    token = secrets.token_urlsafe(16)
    with _LOCK:
        data = _prune(_load(persona))
        data[token] = {
            "action": action,
            "args": args,
            "fingerprint": _fingerprint(action, args),
            "description": description,
            "created_at": time.time(),
            "expires_at": time.time() + TTL_SECONDS,
            "approved": False,
            # Set only when this action was refused earlier and something new brought it
            # back. The card can then say so, rather than presenting itself as a first ask.
            "after_decline": (prior or {}).get("declined_at"),
        }
        _save(data, persona)

    payload = {
        "status": "PENDING_CONFIRMATION",
        "confirm_token": token,
        "description": description,
        "expires_in_seconds": TTL_SECONDS,
        "instruction": (
            "This action has NOT been performed. Show the user the description above and "
            "ask them to approve it in the app. Approving it there is what carries it out — "
            "so do not claim it is done, do not retry, and do not call this tool again at "
            "all. You will not be the one to complete it, and a second call is refused."
        ),
    }
    if prior is not None:
        payload["previously_declined_at"] = time.strftime(
            "%H:%M", time.localtime(prior.get("declined_at") or 0))
        payload["instruction"] += (
            f" The user declined this at {payload['previously_declined_at']}; say so when "
            "you raise it, so they know they are being asked again and why."
        )
    return payload


def approve(token: str, persona: str | None = None) -> bool:
    """
    Mark a pending action approved. Called **only** by the server's /confirm endpoint,
    in response to a real user action. No agent-reachable tool calls this.
    """
    with _LOCK:
        data = _prune(_load(persona))
        entry = data.get(token)
        if not entry:
            return False
        entry["approved"] = True
        entry["approved_at"] = time.time()
        _save(data, persona)
        return True


def decline(token: str, persona: str | None = None) -> dict | None:
    """
    Record the user's refusal of a pending action. Returns the declined entry, or None
    if the token is unknown or already expired.

    Called **only** by the server's /decline endpoint, in response to a real user action —
    the same out-of-band discipline as `approve()`. No agent-reachable tool calls this,
    because a model that can decline on the user's behalf can also clear a card the user
    never saw.

    The pending record is removed, which is what stops the poll re-showing it. It is not
    discarded: the entry is appended to the declined ledger with its fingerprint, so a
    later proposal of the identical action can be recognised as one already refused.

    The fingerprint is re-derived from the stored action and args and checked against the
    stored value before anything is written, exactly as `consume()` does. A record whose
    arguments no longer match the fingerprint it was issued with has been tampered with on
    disk; refusing to file it as a clean "the user said no to X" is the safe direction,
    since X is then not known. The pending record is still removed either way — leaving it
    would restore the loop this exists to end.
    """
    with _LOCK:
        data = _prune(_load(persona))
        entry = data.pop(token, None)
        if not entry:
            return None
        _save(data, persona)

        args = entry.get("args")
        intact = (args is not None
                  and entry.get("fingerprint") == _fingerprint(entry.get("action", ""), args))

        record = {
            "status": "declined",
            "action": entry.get("action", ""),
            "args": args if intact else None,
            "fingerprint": entry.get("fingerprint") if intact else None,
            "description": entry.get("description", ""),
            "created_at": entry.get("created_at"),
            "declined_at": time.time(),
        }
        _append_declined(record, persona)

    return record


# The ledger is append-only and nothing prunes it on a schedule, so it is capped by count
# rather than by age: it is read to answer "was this just refused?", which only the recent
# end can answer, and an uncapped JSON file on the persona's data volume grows forever for
# no benefit. 200 declines is far more history than that question needs.
_DECLINED_LIMIT = 200


def _append_declined(record: dict, persona: str | None = None) -> None:
    """Append to the declined ledger. Caller holds _LOCK."""
    path = _declined_path(persona)
    try:
        existing = json.loads(path.read_text()) if path.exists() else []
        if not isinstance(existing, list):
            existing = []
    except (json.JSONDecodeError, OSError):
        # A corrupt ledger loses history; it must never block the decline itself, which is
        # the half that protects the user.
        existing = []
    existing.append(record)
    try:
        path.write_text(json.dumps(existing[-_DECLINED_LIMIT:], indent=2))
        path.chmod(0o600)
    except OSError:
        pass


def declined(within_seconds: float | None = None,
             persona: str | None = None) -> list[dict]:
    """
    Declined actions, newest last. `within_seconds` limits to recent ones.

    This is the readable half of "the user said no to X". Two things read it: the guard in
    request(), which is what actually stops a re-proposal, and context_block() below, which
    tells the model so it does not spend the turn trying.
    """
    path = _declined_path(persona)
    try:
        records = json.loads(path.read_text()) if path.exists() else []
    except (json.JSONDecodeError, OSError):
        return []
    if not isinstance(records, list):
        return []
    if within_seconds is None:
        return records
    cutoff = time.time() - within_seconds
    return [r for r in records if (r.get("declined_at") or 0) >= cutoff]


def context_block(persona: str | None = None) -> str:
    """
    What the user has recently refused, as a section for load_recent_context. Empty when
    nothing was declined, so a user who has never said no pays nothing.

    The guard in request() is what enforces this; the block exists so the model does not
    spend a turn arriving at a proposal that will not be raised, and does not read the
    absence of a card as permission to ask in prose instead. Both halves are needed: an
    instruction alone has been ignored before, and a silent refusal invites the model to
    route around it.

    Descriptions are ours — they were written by the tool that proposed the action, not by
    an attacker — so nothing here needs the untrusted wrapper. Tool and argument names are
    never included: the user reads this layer's output, and the description already says
    what the action was in their own terms.
    """
    records = declined(_REPROPOSE_WINDOW_SECONDS, persona)
    if not records:
        return ""
    lines = ["## Declined by the user",
             "Things the user was asked to approve and refused. Their answer stands — do "
             "not propose these again, and do not work around them. Raise one only if the "
             "user brings it up themselves or something genuinely new about it arrives."]
    for r in records[-_CONTEXT_MAX_DECLINED:]:
        when = time.strftime("%H:%M on %d %b", time.localtime(r.get("declined_at") or 0))
        what = (r.get("description") or "").strip()
        if what:
            lines.append(f"- {what} — declined {when}")
    return "\n".join(lines) if len(lines) > 2 else ""


# Enough to cover a day of refusals without letting a bad afternoon crowd the context. The
# ledger keeps everything (_DECLINED_LIMIT); this caps only what is shown.
_CONTEXT_MAX_DECLINED = 10


def pending(persona: str | None = None) -> list[dict]:
    """Unexpired, unapproved requests — what the app shows as awaiting a decision."""
    with _LOCK:
        data = _prune(_load(persona))
        _save(data, persona)
    return [
        {"token": t, "description": e["description"], "action": e["action"],
         "expires_at": e["expires_at"]}
        for t, e in sorted(data.items(), key=lambda kv: kv[1]["created_at"])
        if not e.get("approved")
    ]


def consume(token: str | None, action: str, args: dict,
            persona: str | None = None) -> tuple[bool, str]:
    """
    Check an approval and spend it. Returns (ok, reason).

    Single-use, and matched against the exact arguments that were approved. Both matter:
    without single-use one approval authorises unlimited sends; without the fingerprint
    check an approval for a harmless action could be spent on a damaging one, which is
    the more dangerous of the two.
    """
    if not token:
        return False, "No confirmation token supplied."
    with _LOCK:
        data = _prune(_load(persona))
        entry = data.get(token)
        if not entry:
            return False, "That confirmation has expired or was never issued."
        if not entry.get("approved"):
            return False, "The user has not approved this yet."
        if entry["fingerprint"] != _fingerprint(action, args):
            return False, (
                "The details changed since this was approved. Nothing has been done — "
                "ask again with the new details."
            )
        del data[token]          # single use
        _save(data, persona)
    return True, "approved"


# The actions the server may finish on the user's behalf, mapped to the tool that
# performs them. Hard-coded rather than resolved from the record: the action name comes
# out of a JSON file on disk, and turning a string in that file into an importable
# callable would make the store a code path. Only `write_profile_contact` differs from
# its tool's name — it gates one branch of `write_profile`, not the whole tool.
_EXECUTORS: dict[str, tuple[str, str]] = {
    "send_email":            ("tools.mail",          "send_email"),
    "write_config":          ("tools.config_writer", "write_config"),
    "write_profile_contact": ("tools.profile",       "write_profile"),
    "write_agent_config":    ("tools.agent_config",  "write_agent_config"),
    # Gates ONE branch of write_contact — creating a record that resembles an existing
    # one — not the whole tool. An update by contact_id is ungated. [DB-0815-07].
    "write_contact":         ("tools.crm",           "write_contact"),
    # Every merge, no exceptions — a merge folds one real person's history into
    # another's and pre-08-22 merges cannot be reversed. tools/crm.py also
    # setdefault-registers this at import as a fallback; this line is the durable
    # copy and wins. [DB-0822-03].
    "merge_contacts":        ("tools.crm",           "merge_contacts"),
    # A taught intake rule silences mail permanently — the quiet, compounding kind
    # of change that must complete server-side from the user's own approval.
    "teach_intake":          ("tools.intake",        "teach_intake"),
    # Gates ONE branch of write_persona — a preference the tool INFERRED rather than
    # was told. A stated preference is ungated and never reaches here. [DB-0815-11].
    "write_persona":         ("tools.persona",       "write_persona"),
    # The ONE write path to data/personas/{p}/zones.yaml ([DB-0815-12] option b,
    # 2026-08-28). The card is raised by code in tools/location.py — never by a model,
    # which holds no zone tool — and the args carry the PLACE's public geocoded
    # coordinate, never the user's ping.
    "add_zone":              ("tools.location",      "append_zone"),
    # The batch tap on the nightly CRM sweep ([DB-0827-03]). One card for a whole
    # accepted set, not one per suggestion — the review already happened in
    # conversation, and a tap per row is how a review queue becomes a rubber stamp.
    # The args are ids only, so the replay writes exactly the ledger rows the user
    # read; there is no content here for a re-statement to drift on.
    "apply_crm_proposals":   ("tools.crm_sweep",     "apply_crm_proposals"),
    # THE ONLY PATH BY WHICH A TIER-2 CLINICAL THREAD EVER CLOSES ([DB-0808-06],
    # 2026-09-03). The card is raised by the scheduler's periodic review — by code, never
    # by a model, the same rule as add_zone above — because a model that could raise it
    # could argue its way toward a closed crisis thread. The conversational path still
    # refuses `resolved` outright. This line is the DURABLE registration: tools/escalation
    # also setdefault-registers it at import, but nothing imports that module at startup,
    # so without this entry an approved close would land as "nothing here knows how to
    # carry that out".
    "close_clinical_escalation": ("tools.escalation", "close_clinical_escalation"),
}


def execute(token: str, persona: str | None = None) -> dict:
    """
    Perform the action behind an approved token, and report what happened.

    Called by `POST /confirm` immediately after `approve()`, and by nothing else. The
    model is not in this path — it proposed the action and is not consulted again, which
    is the point (see the module docstring for what went wrong when it was).

    The approval is spent through the tool's own `consume()` call, by passing the token
    back in: that keeps single-use, expiry and the argument fingerprint on exactly one
    code path rather than duplicating the check here. `args` is replayed verbatim from
    the record, so a tool that re-derives its fingerprint from them gets an identical
    one — anything else would be refused, correctly.

    Returns a dict carrying `status`, and never raises: a failure here has to reach the
    user as words on the screen, not as a 500 the app renders as "could not approve"
    when the approval was in fact recorded.
    """
    import importlib

    with _LOCK:
        entry = _prune(_load(persona)).get(token)

    if not entry:
        return {"status": "expired",
                "message": "That approval expired before it could be carried out."}
    if not entry.get("approved"):
        return {"status": "not_approved",
                "message": "That action has not been approved."}

    action = entry.get("action", "")
    description = entry.get("description", "")
    args = entry.get("args")
    if args is None:
        # A record written before args were stored (2026-08-15). Nothing can replay it,
        # and guessing the arguments from the fingerprint string is not a thing to do
        # with a send. Records live 10 minutes, so this is self-clearing after a deploy.
        return {"status": "unexecutable", "action": action, "description": description,
                "message": "That request was raised before an update and has to be asked for again."}

    target = _EXECUTORS.get(action)
    if not target:
        return {"status": "unexecutable", "action": action, "description": description,
                "message": f"Nothing here knows how to carry out '{action}'."}

    module_name, fn_name = target
    try:
        fn = getattr(importlib.import_module(module_name), fn_name)
        result = fn(**args, confirm_token=token)
    except Exception as e:                                   # noqa: BLE001 — see docstring
        return {"status": "failed", "action": action, "description": description,
                "message": f"It could not be completed: {e}"}

    # The four gated tools report failure two ways: a dict with an "error" key, or a
    # string opening "Error:". Neither raises, so a result has to be read, not assumed.
    failure = None
    if isinstance(result, dict) and result.get("error"):
        failure = str(result["error"])
    elif isinstance(result, str) and result.startswith("Error"):
        failure = result

    if failure:
        return {"status": "failed", "action": action, "description": description,
                "message": failure, "result": result}

    return {"status": "executed", "action": action, "description": description,
            "result": result}
