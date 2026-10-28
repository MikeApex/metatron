"""
core/auth.py — shared-secret authentication for the server.

Until 2026-08-03 every endpoint was open. The comment on the CORS middleware read
"local network only — no auth needed at this stage", which was true when the Mac was
the host and false once the VM went up: anything on the tailnet could read
`/monitor/file` and walk the user's entire private history.

Roadmap B2 chose a shared secret over a Tailscale ACL, because the Android app removes
the Tailscale substrate an ACL would depend on.

Two credentials, one secret:

  - **Cookie** (`mt_session`, HttpOnly + Secure + SameSite=Lax) — set by /auth/login.
    Carries the same-origin browser automatically, including on requests a header
    cannot reach.
  - **Bearer token** (`Authorization: Bearer <token>`) — the same token value, for the
    CLI, for scripts, and for the Android app, which calls the VM cross-origin from a
    Capacitor WebView and therefore never gets the cookie (SameSite=Lax withholds it).

The token is *signed, not stored*. There is no session table: the token carries its own
expiry and an HMAC over it, keyed on the password. Two consequences worth knowing —
tokens survive a server restart (the phone does not get logged out by every deploy),
and changing the password invalidates every issued token at once, which is the correct
behaviour for a revocation.

WebSocket auth does not live here — see `core/server.py`. `@app.middleware("http")`
never runs for a WebSocket handshake, so that path is gated explicitly at the endpoint
with a first-frame handshake rather than a query parameter. A `?token=` would put the
secret in URLs, and therefore in access logs and browser history.

**Tokens carry who they are for (v2, 2026-10-27).** Until then a token was
`<expiry>.<hmac>` and named nobody: whoever held one could ask for any persona, which was
harmless with one user and is the whole problem with two
(archive/plans/multi_user_accounts_plan_2026-10-26.md § 3.1, § 4.1, § 4.3). Now:

    v2.<persona | *>.<role>.<cred_version>.<expiry>.<hmac>

  - `user`    — an account user (`core/accounts.py`). Bound to that one persona; verified
                against the account store on every request, so disabling the account or
                resetting its password (both bump `cred_version`) revokes it at once.
  - `admin`   — Mike, signed in with METATRON_AUTH_PASSWORD as `mike` or a test persona.
                Bound to that persona, plus The Book's `/monitor/*` for everyone.
  - `service` — minted locally by internal clients (the scheduler, deploy.sh, The Book,
                the sync and read scripts). Names its persona per request; `*` here.

v1 tokens are refused. The signing key is unchanged, so rotating the admin password still
revokes every token of every kind.
"""

# Lazy annotations, so `str | None` does not evaluate at import time. This module is
# imported by callers running on whatever interpreter they happen to have — the
# SessionStart hook's `python3` (macOS system Python, 3.9), the monitor's slim venv,
# the VM's system python3 in deploy.sh — and only the project venv is guaranteed to be
# 3.11. Without this, mint_token.py dies with a TypeError on the older ones.
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from pathlib import Path

_ENV_PATH = Path(__file__).parent.parent / ".env"


def _load_env() -> None:
    """
    Load .env explicitly, without requiring python-dotenv.

    Explicitly, rather than relying on core.orchestrator's import-time call, because an
    auth check that reads an unset variable through an import-ordering accident is
    precisely the failure this module exists to prevent.

    Without python-dotenv, because every client that talks to the server needs to mint
    a token — including tools/metatron_monitor.py, which runs from its own slim venv
    (requirements-monitor.txt), and the health checks in deploy.sh, which run under the
    VM's system python. A hard dependency here would put the token logic out of reach of
    exactly the callers that need it, and the alternative — a second copy of the signing
    code — is the duplication CLAUDE.md § One Home Per Rule Class exists to prevent.
    """
    try:
        from dotenv import load_dotenv
        load_dotenv(_ENV_PATH)
        return
    except ImportError:
        pass
    if not _ENV_PATH.exists():
        return
    for line in _ENV_PATH.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if value[:1] in ("'", '"') and value[-1:] == value[:1] and len(value) > 1:
            value = value[1:-1]
        os.environ.setdefault(key, value)


_load_env()

logger = logging.getLogger(__name__)

COOKIE_NAME = "mt_session"

# 30 days. Long deliberately: this is a single-user personal system reached from a
# phone, and a login prompt that reappears weekly trains the user to pick a weak
# password. Revocation is by changing METATRON_AUTH_PASSWORD, which is immediate.
TOKEN_TTL_SECONDS = int(os.environ.get("METATRON_AUTH_TTL_SECONDS", 30 * 24 * 3600))

# Paths reachable without credentials. Deliberately tiny, and deliberately a prefix
# match on nothing but the app shell: the PWA has to load before it can log in.
#
# Note what is NOT here: /health. A liveness probe that reports the server is up is a
# small disclosure, but it is also the single most useful endpoint to an unauthenticated
# scanner, and deploy.sh is the only thing that calls it — it can carry a token.
#
# /auth/register is open because the person signing up has no credential yet. What it can
# do is bounded in core/server.py: create one `pending` entry, rate-limited, never a token.
# /auth/notice is the sign-up notice text — it must be readable before the account exists.
OPEN_PATHS = frozenset({"/", "/sw.js", "/auth/login", "/auth/register", "/auth/notice",
                        "/favicon.ico"})
OPEN_PREFIXES = ("/static/",)


class AuthNotConfigured(RuntimeError):
    """Raised at startup when no password is set. Never raised per-request."""


def _password() -> str | None:
    return os.environ.get("METATRON_AUTH_PASSWORD") or None


def require_configured() -> None:
    """
    Fail closed at startup if no password is set.

    This raises rather than warning, and that is the whole point. `.env` is gitignored,
    so `deploy.sh` cannot carry it — a new variable reaches the VM only by hand. A server
    that starts and runs unauthenticated because that hand-copy was forgotten would
    reproduce the exact hole this module closes, silently, while looking healthy.
    """
    if not _password():
        raise AuthNotConfigured(
            "METATRON_AUTH_PASSWORD is not set. The server will not start without it.\n"
            "Set it in .env on this machine (.env is gitignored — deploy.sh cannot "
            "carry it, so it must be copied by hand):\n"
            "    METATRON_AUTH_PASSWORD='<the shared password>'\n"
            "Generate one with: python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
        )


def _signing_key() -> bytes:
    """
    Derive the HMAC key from the password.

    Deriving rather than taking a second secret keeps the operator's job to one value.
    The cost is that rotating the password invalidates outstanding tokens — which is the
    behaviour we want from a password change anyway.
    """
    pw = _password()
    if not pw:
        # Only reachable if require_configured() was not called at startup. Refuse to
        # mint or verify anything rather than falling back to a fixed key.
        raise AuthNotConfigured("METATRON_AUTH_PASSWORD is not set.")
    return hashlib.sha256(b"metatron-session-v1|" + pw.encode()).digest()


def _sign(payload: str) -> str:
    return hmac.new(_signing_key(), payload.encode(), hashlib.sha256).hexdigest()


ROLES = ("user", "admin", "service")
_store_warned: str | None = None
_ANY_PERSONA = "*"


class Identity:
    """
    Who a verified token belongs to. `persona` is None for a service token, which names
    its persona per request instead.
    """
    __slots__ = ("persona", "role", "cred_version")

    def __init__(self, persona: str | None, role: str, cred_version: int = 0) -> None:
        self.persona = persona
        self.role = role
        self.cred_version = cred_version

    @property
    def is_admin_or_service(self) -> bool:
        return self.role in ("admin", "service")

    def __repr__(self) -> str:   # never the token, only what it decoded to
        return f"Identity(persona={self.persona!r}, role={self.role!r})"


def issue_token(ttl_seconds: int | None = None, *, persona: str | None = None,
                role: str = "service", cred_version: int = 0) -> str:
    """
    Mint a signed v2 token. With no arguments this is a service token — the form every
    internal client uses. `user` and `admin` tokens are minted only by /auth/login.
    """
    if role not in ROLES:
        raise ValueError(f"unknown role {role!r}")
    if role in ("user", "admin") and not persona:
        raise ValueError(f"a {role} token must be bound to a persona")
    bound = _ANY_PERSONA if role == "service" else persona
    # ttl_seconds=0 would mean "already expired"; only None takes the default.
    exp = int(time.time()) + (TOKEN_TTL_SECONDS if ttl_seconds is None else ttl_seconds)
    payload = f"v2.{bound}.{role}.{int(cred_version)}.{exp}"
    return f"{payload}.{_sign(payload)}"


def decode_token(token: str | None) -> Identity | None:
    """
    The Identity a token belongs to, or None if it is not a valid, current v2 token.

    A `user` token is also checked against the account store: unknown, not `active`, or
    an older `cred_version` than the account now has → None. That lookup is the only
    place this module touches `core.accounts`, and it is lazy, so minting and verifying
    service tokens never import it (see the interpreter note at the top of this file).
    """
    if not token or not token.startswith("v2."):
        return None
    payload, _, signature = token.rpartition(".")
    try:
        expected = _sign(payload)
    except AuthNotConfigured:
        return None
    # compare_digest, not ==, so a wrong signature costs the same time as a right one.
    if not hmac.compare_digest(signature, expected):
        return None
    parts = payload.split(".")
    if len(parts) != 5:
        return None
    _v, persona, role, cred, exp = parts
    try:
        if int(exp) <= int(time.time()):
            return None
        cred_version = int(cred)
    except ValueError:
        return None
    if role not in ROLES:
        return None
    if role == "service":
        return Identity(None, "service", 0) if persona == _ANY_PERSONA else None
    if persona == _ANY_PERSONA:
        return None
    if role == "user":
        from core import accounts
        try:
            entry = accounts.get(persona)
        except Exception as e:
            # Fail closed, and say so once per broken state rather than on every request.
            global _store_warned
            if _store_warned != str(e):
                _store_warned = str(e)
                logger.error(f"[auth] account store unreadable — refusing user tokens: {e}")
            return None
        if (not entry or entry.get("status") != "active"
                or int(entry.get("cred_version") or 0) != cred_version):
            return None
    return Identity(persona, role, cred_version)


def verify_token(token: str | None) -> bool:
    """True if the token is a valid, current v2 token of any role."""
    return decode_token(token) is not None


# Brute-force blunting. A generated 32-byte password is not guessable in any practical
# sense, so this is defence against a weak one the user chose by hand rather than the
# primary control. Per-process and deliberately simple — a real lockout store would be
# more state than a single-user system earns.
_failed_attempts = 0
_MAX_DELAY_SECONDS = 5.0


def is_admin_password(supplied: str | None) -> bool:
    """Constant-time check of the admin password. Records nothing — see note_login_*."""
    pw = _password()
    if not pw or not supplied:
        return False
    return hmac.compare_digest(supplied, pw)


def note_login_failure() -> None:
    """Count a failed sign-in — admin or account, the same counter and the same delay."""
    global _failed_attempts
    _failed_attempts += 1
    logger.warning(f"[auth] failed login attempt ({_failed_attempts} since last success)")


def note_login_success() -> None:
    global _failed_attempts
    _failed_attempts = 0


def check_password(supplied: str | None) -> bool:
    """
    Constant-time admin-password check, with an escalating delay on repeated failure.

    The delay is applied by the caller awaiting it — see /auth/login — so it never
    blocks the event loop here.
    """
    if is_admin_password(supplied):
        note_login_success()
        return True
    note_login_failure()
    return False


def failure_delay() -> float:
    """Seconds the caller should wait before answering a failed login."""
    if _failed_attempts <= 1:
        return 0.0
    return min(0.25 * (2 ** min(_failed_attempts - 1, 5)), _MAX_DELAY_SECONDS)


def client_token(ttl_seconds: int = 3600) -> str:
    """
    Mint a token for an internal client (the monitor, the terminal client, deploy.sh).

    These never call /auth/login. They hold the password already — it is in the same
    `.env` — and the signing key is derived from it, so a token minted here verifies on
    the VM without a round trip. Short-lived by default: nothing internal needs the
    30-day life the phone gets.

    Always a `service` token: it names no persona, so the request must name one, and it
    may read The Book. It never touches the account store, which is what keeps it safe
    to call from the 3.9 system Python the hook and deploy.sh use.
    """
    return issue_token(ttl_seconds, role="service")


def bearer_header(ttl_seconds: int = 3600) -> dict:
    """`{"Authorization": "Bearer ..."}` for an internal client, ready to pass to a request."""
    return {"Authorization": f"Bearer {client_token(ttl_seconds)}"}


def credential_from_headers(auth_header: str | None, cookie: str | None) -> str | None:
    """Pull the token out of an Authorization header or the session cookie."""
    if auth_header and auth_header.lower().startswith("bearer "):
        return auth_header[7:].strip()
    return cookie or None


def is_open_path(path: str) -> bool:
    """True for the handful of paths reachable before login (the app shell)."""
    return path in OPEN_PATHS or path.startswith(OPEN_PREFIXES)
