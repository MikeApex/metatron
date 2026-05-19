"""
core/push.py — Web Push notification delivery.

Sends push notifications to all registered PWA subscriptions.
Uses VAPID authentication; keys are stored in .env and never
leave the machine.

Subscriptions are stored in data/push_subscriptions.json.
This file is local-only and not committed to git.

Usage (from scheduler or any other module):
    from core.push import send_push
    send_push(title="Morning Brief", body="Here's your day...")
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_ROOT = Path(__file__).parent.parent
_SUBSCRIPTIONS_FILE = _ROOT / "data" / "push_subscriptions.json"


def _load_subscriptions() -> list[dict]:
    if not _SUBSCRIPTIONS_FILE.exists():
        return []
    try:
        with open(_SUBSCRIPTIONS_FILE) as f:
            return json.load(f)
    except Exception:
        return []


def save_subscription(subscription: dict) -> str:
    """
    Register a browser push subscription.

    Called by the FastAPI /subscribe endpoint when the PWA registers.
    Deduplicates by endpoint URL.
    """
    _SUBSCRIPTIONS_FILE.parent.mkdir(parents=True, exist_ok=True)
    subs = _load_subscriptions()

    endpoint = subscription.get("endpoint", "")
    existing_endpoints = [s.get("endpoint") for s in subs]

    if endpoint and endpoint not in existing_endpoints:
        subs.append(subscription)
        with open(_SUBSCRIPTIONS_FILE, "w") as f:
            json.dump(subs, f, indent=2)
        return f"Subscription registered ({len(subs)} total)"
    return "Subscription already registered"


def send_push(title: str, body: str, urgency: str = "normal") -> dict:
    """
    Send a push notification to all registered subscriptions.

    Args:
        title:   Notification title shown on the device.
        body:    Notification body text.
        urgency: "very-low" | "low" | "normal" | "high" (default "normal")

    Returns:
        Dict with 'sent' count and any 'errors'.
    """
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

    subs = _load_subscriptions()
    if not subs:
        return {"sent": 0, "errors": ["No registered subscriptions"]}

    payload = json.dumps({"title": title, "body": body})
    sent = 0
    errors = []
    stale = []

    for sub in subs:
        try:
            webpush(
                subscription_info=sub,
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
        active = [s for s in subs if s.get("endpoint") not in stale]
        with open(_SUBSCRIPTIONS_FILE, "w") as f:
            json.dump(active, f, indent=2)

    return {"sent": sent, "errors": errors}


def get_vapid_public_key() -> str:
    """Return the VAPID public key for the PWA to use when subscribing."""
    return os.environ.get("VAPID_PUBLIC_KEY", "")
