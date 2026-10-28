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

**The Android app is reached through FCM, and the text never travels through Google
(day planner Stage C, plan § 14 D1 b, 2026-10-28).** The WebView implements no Push API, so
the APK registers an FCM token instead. `send_push` stores the message here under a random id
(the outbox, 24 h) and sends a **data-only** ping carrying that id and nothing else; the app's
native service wakes, fetches the text over its signed-in channel (`fetch_message`, bound to
the same persona) and shows the notification. FCM *accepting* a ping is not delivery — the
phone's fetch is, so both are written to the persona's `push_log.jsonl`, content-free.

Usage (from scheduler or any other module):
    from core.push import send_push
    send_push(title="Morning Brief", body="Here's your day...", persona="mike")
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import secrets
import time
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

_ROOT = Path(__file__).parent.parent
_SUBSCRIPTIONS_FILE = _ROOT / "data" / "push_subscriptions.json"
_FCM_TOKENS_FILE = _ROOT / "data" / "fcm_tokens.json"
_OUTBOX_FILE = _ROOT / "data" / "push_outbox.json"
_LOCK_FILE = _ROOT / "data" / ".push.lock"
# A message the phone has not fetched in a day is not worth showing. Every write prunes, so the
# file holds at most a day of check-ins (a few KB) and a restart orphans nothing.
_OUTBOX_TTL_S = 24 * 3600
_FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
# Tests inject a callable(token, data) -> (http_status, response_text); production posts to FCM.
_FCM_SEND = None


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


def save_subscription(subscription: dict, persona: str, replaces: str | None = None) -> str:
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
    if replaces and replaces != endpoint:
        # Only this persona's own entry: an endpoint is not proof of ownership of someone else's.
        kept = [s for s in subs if not (s.get("endpoint") == replaces and s.get("persona") == persona)]
        if len(kept) != len(subs):
            subs = kept
            _write_subscriptions(subs)
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


def send_push(title: str, body: str, urgency: str = "normal", *, persona: str,
              tasks: list[dict] | None = None) -> dict:
    """
    Send a push notification to one persona's devices, and nobody else's — browsers by Web
    Push, the Android app by an FCM ping.

    Args:
        title:   Notification title shown on the device.
        body:    Notification body text.
        urgency: "very-low" | "low" | "normal" | "high" (default "normal")
        persona: whose devices receive it. Required, with no default, so a caller that
                 forgets cannot fall back to broadcasting.
        tasks:   ledger tasks this message is about, `[{"id", "title"}]` — the app offers
                 Done / Not yet / Skipped on each, one at a time. Reaches the app only.

    Returns:
        Dict with 'sent' count and any 'errors'.
    """
    if not persona:
        raise ValueError("send_push needs the persona whose devices should receive it")
    web = _send_web(title, body, urgency, persona)
    fcm = _send_fcm(title, body, persona, tasks)
    sent = web["sent"] + fcm["sent"]
    errors = web["errors"] + fcm["errors"]
    if not sent and not errors and not web["devices"] and not fcm["devices"]:
        errors = ["No registered subscriptions"]
    return {"sent": sent, "errors": errors}


def _send_web(title: str, body: str, urgency: str, persona: str) -> dict:
    all_subs = _load_subscriptions()
    subs = [s for s in all_subs if s.get("persona") == persona]
    if not subs:
        return {"sent": 0, "errors": [], "devices": 0}
    from pywebpush import webpush, WebPushException
    from cryptography.hazmat.primitives.serialization import (
        load_pem_private_key, Encoding, PrivateFormat, NoEncryption,
    )
    import base64

    private_key_pem = os.environ.get("VAPID_PRIVATE_KEY", "").replace("\\n", "\n")
    claims_sub = os.environ.get("VAPID_CLAIMS_SUB", "mailto:user@example.com")

    if not private_key_pem:
        return {"sent": 0, "errors": ["VAPID_PRIVATE_KEY not set in .env"], "devices": len(subs)}

    # py_vapid expects a base64url-encoded DER key, not a PEM string.
    try:
        _key = load_pem_private_key(private_key_pem.strip().encode(), password=None)
        _der = _key.private_bytes(Encoding.DER, PrivateFormat.TraditionalOpenSSL, NoEncryption())
        vapid_key = base64.urlsafe_b64encode(_der).rstrip(b"=").decode()
    except Exception as e:
        return {"sent": 0, "errors": [f"VAPID key parse error: {e}"], "devices": len(subs)}

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

    return {"sent": sent, "errors": errors, "devices": len(subs)}


# --- the Android app: FCM tokens, the outbox, the ping -------------------------------------

@contextmanager
def _locked():
    # The server registers tokens and serves fetches; each user's scheduler sends. Three
    # processes, two files — every read-modify-write holds this.
    _LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(_LOCK_FILE, "a") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _read_json(path: Path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w") as f:
        json.dump(obj, f, indent=2)
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def _log_delivery(persona: str, event: str, **fields) -> None:
    """Content-free: ids, counts and outcomes, never a title or body. Never raises."""
    try:
        from core.persona import persona_data_dir
        path = persona_data_dir(persona) / "push_log.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"at": time.strftime("%Y-%m-%dT%H:%M:%S"), "event": event, **fields}
        with open(path, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass


_FAILURE_PART = re.compile(r"[^A-Za-z0-9 _.:\-]")


def note_phone_failure(persona: str, report: str) -> None:
    """The phone's own record of a fetch that never reached the VM — the one place that knows
    why. Written as `fcm_fetch_failed`; every part is stripped to a safe, short token, since
    the phone is the author."""
    reason, _, rest = str(report or "").partition("|")
    id8, _, at = rest.partition("|")
    _log_delivery(persona, "fcm_fetch_failed",
                  reason=_FAILURE_PART.sub("", reason)[:60],
                  id=_FAILURE_PART.sub("", id8)[:8],
                  phone_at=_FAILURE_PART.sub("", at)[:19])


def save_fcm_token(token: str, persona: str) -> str:
    """Register the Android app's FCM token for one persona — the persona bound to the caller's
    sign-in, never one the request names. A phone signed in as someone else moves to them."""
    if not persona:
        raise ValueError("an FCM token must belong to a persona")
    token = (token or "").strip()
    if not token or len(token) > 4096:
        return "No token"
    with _locked():
        tokens = [t for t in _read_json(_FCM_TOKENS_FILE, []) if t.get("token") != token]
        tokens.append({"token": token, "persona": persona, "registered": int(time.time())})
        _write_json(_FCM_TOKENS_FILE, tokens)
    return "Registered"


def remove_fcm_token(token: str, persona: str) -> str:
    """Sign-out: the phone stops receiving this persona's pings. Only the owner removes it."""
    with _locked():
        tokens = _read_json(_FCM_TOKENS_FILE, [])
        kept = [t for t in tokens if not (t.get("token") == token and t.get("persona") == persona)]
        if len(kept) != len(tokens):
            _write_json(_FCM_TOKENS_FILE, kept)
            return "Removed"
    return "Not registered"


def fetch_message(msg_id: str, persona: str) -> dict | None:
    """The text behind a ping, for the persona it was sent to and nobody else. None when the id
    is unknown, expired or someone else's — the three are deliberately indistinguishable."""
    now = time.time()
    with _locked():
        box = _read_json(_OUTBOX_FILE, {})
        msg = box.get(msg_id)
        if not msg or msg.get("persona") != persona or now - msg.get("created", 0) > _OUTBOX_TTL_S:
            return None
        first = not msg.get("fetched")
        msg["fetched"] = msg.get("fetched") or int(now)
        _write_json(_OUTBOX_FILE, box)
    if first:
        _log_delivery(persona, "fcm_fetched", id=msg_id[:8],
                      after_s=int(now - msg.get("created", now)))
    return {"title": msg["title"], "body": msg["body"], "tasks": msg.get("tasks") or []}


def _store(title: str, body: str, persona: str, tasks: list[dict] | None) -> str:
    now = time.time()
    msg_id = secrets.token_urlsafe(16)
    clean = [{"id": str(t.get("id", ""))[:80], "title": str(t.get("title", ""))[:120]}
             for t in (tasks or []) if t.get("id")]
    with _locked():
        box = {k: v for k, v in _read_json(_OUTBOX_FILE, {}).items()
               if now - v.get("created", 0) <= _OUTBOX_TTL_S}
        box[msg_id] = {"persona": persona, "title": title, "body": body, "tasks": clean,
                       "created": int(now)}
        _write_json(_OUTBOX_FILE, box)
    return msg_id


_session = None


def _fcm_credentials():
    """The sender's identity, kept separate from Vertex's on purpose (Mike, 2026-10-28).

    FCM_CREDENTIALS set → that service-account key file, scoped to FCM only. Unset → the VM's
    default credential (today the Vertex account, granted the FCM sender role in the push-only
    Firebase project, FCM_PROJECT_ID). Leaving Vertex is then one .env line, not a code change:
    docs/INFRASTRUCTURE.md § Push notifications (FCM)."""
    path = os.environ.get("FCM_CREDENTIALS", "").strip()
    if path:
        from google.oauth2 import service_account
        creds = service_account.Credentials.from_service_account_file(path, scopes=[_FCM_SCOPE])
        return creds, creds.project_id
    import google.auth
    return google.auth.default(scopes=[_FCM_SCOPE])


def _fcm_post(token: str, data: dict) -> tuple[int, str]:
    """FCM HTTP v1, sent to the push-only Firebase project (FCM_PROJECT_ID) — not the project
    the VM runs in, so Firebase never touches it. Data-only and high priority: the app's native
    service, not the system tray, decides what is shown."""
    global _session
    from google.auth.transport.requests import AuthorizedSession
    if _session is None:
        creds, project = _fcm_credentials()
        _session = (AuthorizedSession(creds),
                    os.environ.get("FCM_PROJECT_ID") or project
                    or os.environ.get("GOOGLE_CLOUD_PROJECT", ""))
    session, project = _session
    r = session.post(f"https://fcm.googleapis.com/v1/projects/{project}/messages:send",
                     json={"message": {"token": token, "data": data,
                                       "android": {"priority": "high", "ttl": "3600s"}}},
                     timeout=10)
    return r.status_code, r.text


def _send_fcm(title: str, body: str, persona: str, tasks: list[dict] | None) -> dict:
    all_tokens = _read_json(_FCM_TOKENS_FILE, [])
    mine = [t["token"] for t in all_tokens if t.get("persona") == persona and t.get("token")]
    if not mine:
        return {"sent": 0, "errors": [], "devices": 0}
    msg_id = _store(title, body, persona, tasks)
    send = _FCM_SEND or _fcm_post
    sent, errors, dead = 0, [], []
    for token in mine:
        try:
            status, text = send(token, {"m": msg_id})
        except Exception as e:  # noqa: BLE001
            errors.append(f"fcm: {type(e).__name__}")
            continue
        if status == 200:
            sent += 1
        elif status == 404 or "UNREGISTERED" in (text or ""):
            # Uninstalled, or the token rotated. Pruned on FCM's word only — a 400 can be our own
            # malformed request, and pruning on it would silently drop every phone.
            dead.append(token)
        else:
            errors.append(f"fcm: HTTP {status}")
    if dead:
        with _locked():
            _write_json(_FCM_TOKENS_FILE, [t for t in _read_json(_FCM_TOKENS_FILE, [])
                                           if t.get("token") not in dead])
    _log_delivery(persona, "fcm_sent", id=msg_id[:8], accepted=sent, pruned=len(dead),
                  failed=len(errors), tasks=len(tasks or []))
    return {"sent": sent, "errors": errors, "devices": len(mine)}


def get_vapid_public_key() -> str:
    """Return the VAPID public key for the PWA to use when subscribing."""
    return os.environ.get("VAPID_PUBLIC_KEY", "")
