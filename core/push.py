"""
core/push.py — Web Push notification delivery.

Sends push notifications to one persona's registered PWA subscriptions.
Uses VAPID authentication; keys are stored in .env and never
leave the machine.

Subscriptions are stored in data/push_subscriptions.json.
This file is local-only and not committed to git.

**Every subscription belongs to one persona (2026-10-27).** Until the second user the
list had no owner and `send_push` went to all of it — so once a second person's browser
subscribed, every one of Mike's check-ins, with its text, would have arrived on her
device (archive/plans/multi_user_accounts_plan_2026-10-26.md § 3.4). `persona` is now
required on both ends. Entries written before this carry no owner and were all Mike's;
they are read as `mike` and stamped so on the next write.

Usage (from scheduler or any other module):
    from core.push import send_push
    send_push(title="Morning Brief", body="Here's your day...", persona="mike")
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_ROOT = Path(__file__).parent.parent
_SUBSCRIPTIONS_FILE = _ROOT / "data" / "push_subscriptions.json"


# Subscriptions registered before they carried an owner were all Mike's — he was the only
# user. Reading them as his is the migration; nothing else needs to run.
_LEGACY_OWNER = "mike"


def _load_subscriptions() -> list[dict]:
    if not _SUBSCRIPTIONS_FILE.exists():
        return []
    try:
        with open(_SUBSCRIPTIONS_FILE) as f:
            subs = json.load(f)
    except Exception:
        return []
    for sub in subs:
        sub.setdefault("persona", _LEGACY_OWNER)
    return subs


def _write_subscriptions(subs: list[dict]) -> None:
    _SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_SUBSCRIPTIONS_FILE, "w") as f:
        json.dump(subs, f, indent=2)


def save_subscription(subscription: dict, persona: str) -> str:
    """
    Register a browser push subscription for one persona.

    Called by the FastAPI /subscribe endpoint, which passes the persona bound to the
    caller's token — never one the request names. Deduplicates by endpoint URL; a device
    that re-subscribes after a different user signed in on it moves to that user, so a
    shared browser never keeps receiving the previous user's notifications.
    """
    if not persona:
        raise ValueError("a push subscription must belong to a persona")
    subs = _load_subscriptions()
    endpoint = subscription.get("endpoint", "")
    if not endpoint:
        return "Subscription has no endpoint"
    entry = {**subscription, "persona": persona}
    for i, existing in enumerate(subs):
        if existing.get("endpoint") == endpoint:
            if existing.get("persona") == persona:
                return "Subscription already registered"
            subs[i] = entry
            _write_subscriptions(subs)
            return "Subscription moved to this account"
    subs.append(entry)
    _write_subscriptions(subs)
    return f"Subscription registered ({sum(1 for s in subs if s['persona'] == persona)} for this account)"


def send_push(title: str, body: str, urgency: str = "normal", *, persona: str) -> dict:
    """
    Send a push notification to one persona's subscriptions, and nobody else's.

    Args:
        title:   Notification title shown on the device.
        body:    Notification body text.
        urgency: "very-low" | "low" | "normal" | "high" (default "normal")
        persona: whose devices receive it. Required, with no default, so a caller that
                 forgets cannot fall back to broadcasting.

    Returns:
        Dict with 'sent' count and any 'errors'.
    """
    if not persona:
        raise ValueError("send_push needs the persona whose devices should receive it")
    from pywebpush import webpush, WebPushException
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key, Encoding, PrivateFormat, NoEncryption,
    )
    import base64

    private_key_pem = os.environ.get("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
    claims_sub = os.environ.get("VAPID_CLAIMS_SUB", "mailto:user@example.com")

    if not private_key_pem:
        return {"sent": 0, "errors": ["VAPID_PRIVATE_KEY not set in .env"]}

    # py_vapid expects a base64url-encoded DER key, not a PEM string.
    try:
        _key = load_pem_private_key(private_key_pem.strip().encode(), password=None)
        _der = _key.private_bytes(Encoding.DER, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        vapid_key = base64.urlsafe_b64encode(_der).rstrip(b"=").decode()
    except Exception as e:
        return {"sent": 0, "errors": [f"VAPID key parse error: {e}"]}

    all_subs = _load_subscriptions()
    subs = [s for s in all_subs if s.get("persona") == persona]
    if not subs:
        return {"sent": 0, "errors": ["No registered subscriptions"]}

    payload = json.dumps({"title": title, "body": body})
    sent = 0
    errors = []
    stale = []

    for sub in subs:
        try:
            webpush(
                # Only what the push service needs — the owner field is ours.
                subscription_info={"endpoint": sub.get("endpoint"), "keys": sub.get("keys", {})},
                data=payload,
                vapid_private_key=vapid_key,
                vapid_claims={"sub": claims_sub},
                headers={"urgency": urgency},
            )
            sent += 1
        except WebPushException as e:
            if e.response and e.response.status_code in (404, 410):
                # Subscription expired or unsubscribed — mark for removal
                stale.append(sub.get("endpoint"))
            else:
                errors.append(str(e))
        except Exception as e:
            errors.append(str(e))

    # Remove stale subscriptions
    if stale:
        _write_subscriptions([s for s in all_subs if s.get("endpoint") not in stale])

    return {"sent": sent, "errors": errors}


def get_vapid_public_key() -> str:
    """Return the VAPID public key for the PWA to use when subscribing."""
    return os.environ.get("VAPID_PUBLIC_KEY", "")
