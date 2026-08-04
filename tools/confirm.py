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
                                                          server marks it approved
    4. Agent calls send_email(..., confirm_token=...)  → gate finds the approval, executes

Step 4 is a second, explicit call. The pending record stores the *exact* arguments from
step 1, and `consume()` refuses if they have changed — so an approval for "email Sarah
the itinerary" cannot be spent on "email everyone the medical file".

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
            "ask them to approve it in the app. Do not claim it is done, do not retry, and "
            "do not call this tool again until they have approved it — a second call "
            "without approval will be refused in the same way."
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
