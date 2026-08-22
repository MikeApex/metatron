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


def request(action: str, args: dict, description: str,
            persona: str | None = None) -> dict:
    """
    Record a pending action and return the payload a tool should hand back instead of acting.

    `description` is what the user will read and approve. Write it so it stands alone —
    they may see it without the surrounding conversation, and it is the only thing
    standing between a persuasive email and a real send.
    """
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
        }
        _save(data, persona)

    return {
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
