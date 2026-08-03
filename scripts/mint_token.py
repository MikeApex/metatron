#!/usr/bin/env python3
"""
Print a short-lived bearer token for the server. Standard library only.

Exists so shell callers do not have to embed a Python one-liner inside an SSH
heredoc — deploy.sh and metatron-resume.sh both health-check the server from inside
`gcloud compute ssh --command="..."`, and the quoting for an inline mint is
unreadable enough to be its own bug source.

Usage:
    curl -sk -H "Authorization: Bearer $(python3 scripts/mint_token.py)" \
         https://localhost:8001/health

    python3 scripts/mint_token.py 3600     # custom TTL in seconds (default 600)

Reads METATRON_AUTH_PASSWORD from the environment or .env, and derives the same
signing key the server uses — so no round trip to /auth/login is needed. Prints
nothing and exits 1 if no password is configured.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.auth import AuthNotConfigured, client_token  # noqa: E402

if __name__ == "__main__":
    ttl = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    try:
        print(client_token(ttl_seconds=ttl))
    except AuthNotConfigured:
        print("METATRON_AUTH_PASSWORD is not set — cannot mint a token.", file=sys.stderr)
        sys.exit(1)
