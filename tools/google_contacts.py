"""
tools/google_contacts.py — read-only access to a persona's Google Contacts (People API).

Answers the standing gap named twice in DEV_BACKLOG.md: no live Google Contacts read
existed, and the local CRM (tools/crm.py) had misattributed a contact's email because
there was nothing to check a captured detail against. This is deliberately read-only —
the need on record is checking/onboarding against what Google already has, not writing
back to it; a write path is a separate decision if it's ever actually needed.

**Auth is per-persona, not per-project.** Unlike the Maps/Routes/AeroDataBox keys (server
credentials tied to the GCP project), Contacts data belongs to one specific Google
account, so this uses OAuth 2.0 user consent rather than an API key. The one-time consent
step is `scripts/google_contacts_authorize.py` — run once per persona, opens a browser,
the user signs into the Google account holding the contacts (for `mike`,
`diamond.mike.mt@gmail.com`, per `profile.yaml`'s `account_email` convention), and the
resulting refresh token is stored at `data/personas/{persona}/google_oauth_token.json`
(gitignored, 0600 — sensitive-tier, same posture as `pending_confirmations.json`).
`GOOGLE_OAUTH_CLIENT_ID`/`GOOGLE_OAUTH_CLIENT_SECRET` in `.env` identify the app itself
(one Desktop-type OAuth client, created once in Cloud Console — no gcloud CLI path exists
for that credential type, confirmed 2026-08-07) and are not persona-specific.

Scope requested: `contacts.readonly` only — the recorded need is reading, and granting
write access nothing calls would be exactly the over-broad-grant pattern this project's
own PoLP work (B2) exists to avoid.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import requests
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

from core.persona import persona_data_dir

SCOPES = ["https://www.googleapis.com/auth/contacts.readonly"]
_PEOPLE_BASE = "https://people.googleapis.com/v1"
TIMEOUT_SECONDS = 10


def _token_path(persona: str | None = None) -> Path:
    return persona_data_dir(persona) / "google_oauth_token.json"


def _credentials(persona: str | None = None) -> Credentials | None:
    path = _token_path(persona)
    if not path.exists():
        return None
    try:
        info = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None

    creds = Credentials(
        token=info.get("token"),
        refresh_token=info.get("refresh_token"),
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.environ.get("GOOGLE_OAUTH_CLIENT_ID"),
        client_secret=os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET"),
        scopes=SCOPES,
    )
    if not creds.valid and creds.refresh_token:
        try:
            creds.refresh(Request())
            # Persist the refreshed access token so the next call doesn't need to
            # refresh again immediately — the refresh token itself doesn't change.
            path.write_text(json.dumps({"token": creds.token, "refresh_token": creds.refresh_token}))
            os.chmod(path, 0o600)
        except Exception:
            return None
    return creds


def read_google_contacts(query: str = "") -> dict:
    """
    Read contacts from the persona's connected Google account.

    Args:
        query: Optional substring to filter by name or email (case-insensitive, matched
            client-side). Omit to return everything.

    Returns:
        {"contacts": [{"name", "emails": [...], "phones": [...]}]} or {"error": ...} —
        including an honest error if this persona hasn't completed the one-time
        authorization yet (run scripts/google_contacts_authorize.py), rather than a
        confusing empty result.
    """
    creds = _credentials()
    if creds is None:
        return {
            "error": (
                "Google Contacts is not connected for this persona. Run "
                "scripts/google_contacts_authorize.py once to authorize it."
            )
        }

    try:
        resp = requests.get(
            f"{_PEOPLE_BASE}/people/me/connections",
            headers={"Authorization": f"Bearer {creds.token}"},
            params={"personFields": "names,emailAddresses,phoneNumbers", "pageSize": 200},
            timeout=TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as e:
        return {"error": f"Google Contacts read failed: {e}"}
    except ValueError:
        return {"error": "Google Contacts returned an unparseable response."}

    out = []
    q = query.strip().lower()
    for person in data.get("connections", []):
        names = person.get("names") or [{}]
        name = names[0].get("displayName", "")
        emails = [e.get("value", "") for e in person.get("emailAddresses", [])]
        phones = [p.get("value", "") for p in person.get("phoneNumbers", [])]
        if q and q not in name.lower() and not any(q in e.lower() for e in emails):
            continue
        out.append({"name": name, "emails": emails, "phones": phones})

    return {"contacts": out}


READ_GOOGLE_CONTACTS_SCHEMA = {
    "name": "read_google_contacts",
    "description": (
        "Read contacts from the user's connected Google account — read-only. Use this to "
        "check a name, email, or phone number against what Google already has before "
        "writing a new CRM contact (write_contact) or correcting one, so a captured "
        "detail (e.g. a dictated or misheard email address) can be verified rather than "
        "trusted blind. If the account isn't connected yet, say so plainly rather than "
        "treating an empty result as 'no contacts exist'."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Optional name or email substring to filter by. Omit to list everything.",
            },
        },
        "required": [],
    },
}
