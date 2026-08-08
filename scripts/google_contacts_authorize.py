#!/usr/bin/env python3
"""
scripts/google_contacts_authorize.py — one-time OAuth consent for tools/google_contacts.py.

Opens a browser, the user signs into the Google account holding the contacts to read
(for `mike`, that's `diamond.mike.mt@gmail.com` — not whatever account this machine's
`gcloud` is authenticated as, which is a separate identity), approves the
`contacts.readonly` scope, and the resulting refresh token is saved to
`data/personas/{persona}/google_oauth_token.json` (0600). Run once per persona; the
stored token is reused and auto-refreshed by `tools/google_contacts.py` after that.

Requires GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env — a Desktop-type
OAuth client created once in Cloud Console (no gcloud CLI path exists for that credential
type; confirmed 2026-08-07). Usage:

    python3 scripts/google_contacts_authorize.py --persona mike
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv
from google_auth_oauthlib.flow import InstalledAppFlow

from core.persona import persona_data_dir, persona_scope
from tools.google_contacts import SCOPES

load_dotenv()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--persona", required=True)
    args = parser.parse_args()

    client_id = os.environ.get("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET")
    if not client_id or not client_secret:
        print("GOOGLE_OAUTH_CLIENT_ID / GOOGLE_OAUTH_CLIENT_SECRET not set in .env.", file=sys.stderr)
        sys.exit(1)

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    with persona_scope(args.persona):
        flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
        print(f"Opening a browser for consent — sign in with the Google account this "
              f"persona's contacts should come from, not necessarily your default account.")
        creds = flow.run_local_server(port=0)

        path = persona_data_dir(args.persona) / "google_oauth_token.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"token": creds.token, "refresh_token": creds.refresh_token}))
        os.chmod(path, 0o600)

    print(f"Saved: {path}")


if __name__ == "__main__":
    main()
