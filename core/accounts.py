"""
core/accounts.py — the account store: who may sign in with their own password.

Plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.2, § 4.4.

Until the second user, one shared password opened every persona and the request named
whichever one it wanted. An account is the per-user half of the replacement: a username
(which is also the persona's folder name), a scrypt hash of a password that user chose,
and a status Mike sets by hand — a request is `pending` until he approves it.

    data/accounts/accounts.json      chmod 600, outside data/personas/ on purpose

Outside the persona tree because an account exists before its persona does: a sign-up
request has no data directory yet, and must not create one until Mike approves it.

**Stdlib only, 3.9-compatible, imported lazily.** `core/auth.py` is imported by the
SessionStart hook's system Python 3.9, The Book's slim venv and the VM's system
python3, and imports this module only inside login and `user`-token verification —
never while minting a service token. A 3.10-only construct or a venv-only import here
would break those callers silently (`deploy.sh` reads a failed mint as "no active
streams" and restarts the server mid-turn). `hashlib.scrypt` is looked up at call
time for the same reason: LibreSSL builds of Python lack it, and only the server's
venv ever hashes.

**Two processes write this file** — the server (a sign-up) and `scripts/accounts.py`
on the VM (approve, reject, disable). Every write is read-modify-write under an
`fcntl` lock and lands by atomic rename, so neither can lose the other's change.

**Nothing is ever deleted.** Rejected and disabled accounts keep their entry (the
archive rule): the record of who asked, when, and what Mike decided is the audit trail.
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import hashlib
import hmac
import json
import os
import secrets
import tempfile
from datetime import datetime, timezone
from pathlib import Path

_ROOT = Path(__file__).parent.parent
ACCOUNTS_PATH = _ROOT / "data" / "accounts" / "accounts.json"

STATUSES = ("pending", "active", "rejected", "disabled")

# A sign-up name becomes the persona's folder name, so it must also clear
# core.persona.validate_persona_name. These are refused on top of that: names that
# would read as the system's own, Mike's, or a test fixture's.
RESERVED = frozenset({"admin", "root", "system", "service", "default", "mike"})
RESERVED_PREFIXES = ("test",)

MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 256   # scrypt cost scales with input; an open route must bound it
MAX_PENDING = 3

# scrypt parameters, stated here rather than taken from a library default so a hash
# written today can be verified by whatever reads it later. N=2**14, r=8 costs ~16 MB
# and tens of milliseconds — fine for a login, slow enough to make a stolen file dear.
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_DKLEN = 32


class AccountError(ValueError):
    """A refused account operation. `code` is stable; the message is for a person."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


# ---------------------------------------------------------------------------
# Passwords
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    """`scrypt$N$r$p$<salt>$<hash>`, both base64. A fresh salt per call."""
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=_SCRYPT_N, r=_SCRYPT_R,
                            p=_SCRYPT_P, dklen=_SCRYPT_DKLEN)
    return "scrypt${}${}${}${}${}".format(
        _SCRYPT_N, _SCRYPT_R, _SCRYPT_P,
        base64.b64encode(salt).decode(), base64.b64encode(digest).decode())


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check against a stored hash. Any malformed hash is a refusal."""
    try:
        scheme, n, r, p, salt_b64, hash_b64 = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = base64.b64decode(hash_b64)
        got = hashlib.scrypt(password.encode(), salt=base64.b64decode(salt_b64),
                             n=int(n), r=int(r), p=int(p), dklen=len(expected))
    except Exception:
        return False
    return hmac.compare_digest(got, expected)


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _empty() -> dict:
    return {"version": 1, "accounts": {}}


def _read(path: Path) -> dict:
    if not path.exists():
        return _empty()
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("accounts"), dict):
        # A store that does not parse as a store is not "no accounts" — treating it so
        # would let a corrupted file lock every user out silently. Fail loudly.
        raise AccountError("corrupt", f"{path} is not a valid account store")
    return data


def _write(path: Path, data: dict) -> None:
    """Atomic: write a sibling temp file, chmod 600, rename over the original."""
    path.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(path.parent, 0o700)
    fd, tmp = tempfile.mkstemp(prefix=".accounts.", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            f.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except Exception:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(tmp)
        raise


@contextlib.contextmanager
def _locked(path: Path):
    """Exclusive lock for a read-modify-write, held on a sidecar so rename is safe."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lock_path = path.with_name(path.name + ".lock")
    with open(lock_path, "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


# Read cache for token verification, which runs on every request a `user` token makes.
# Keyed on mtime_ns + size so a write by the other process is seen on the next request.
_cache: dict = {"key": None, "data": None, "path": None}


def load(path: Path | None = None) -> dict:
    """The whole store, cached until the file changes. Treat the result as read-only."""
    path = path or ACCOUNTS_PATH
    try:
        st = path.stat()
        key = (st.st_mtime_ns, st.st_size)
    except FileNotFoundError:
        key = None
    if _cache["path"] == path and _cache["key"] == key and _cache["data"] is not None:
        return _cache["data"]
    data = _read(path)
    _cache.update(key=key, data=data, path=path)
    return data


def get(username: str, path: Path | None = None) -> dict | None:
    """One account entry, or None. Never raises for an unknown name."""
    return load(path)["accounts"].get((username or "").strip().lower())


def public_view(entry: dict) -> dict:
    """An entry with everything secret removed — what `list` and /monitor/accounts show."""
    return {k: v for k, v in entry.items() if k not in ("password_hash",)}


def list_accounts(path: Path | None = None) -> list[dict]:
    accounts = load(path)["accounts"]
    return [public_view(accounts[u]) for u in sorted(accounts)]


# ---------------------------------------------------------------------------
# Sign-up
# ---------------------------------------------------------------------------

def _name_in_use(username: str) -> bool:
    """True if the name is already a persona identity, config tree or data tree."""
    return any((
        (_ROOT / "config" / "personas" / f"{username}.md").exists(),
        (_ROOT / "config" / "personas" / username).exists(),
        (_ROOT / "data" / "personas" / username).exists(),
    ))


def check_username(username: str) -> str:
    """The cleaned name, or AccountError saying plainly what is wrong with it."""
    from core.persona import PersonaError, validate_persona_name
    cleaned = (username or "").strip().lower()
    try:
        validate_persona_name(cleaned)
    except PersonaError:
        raise AccountError(
            "invalid_username",
            "Usernames are 1–40 characters: lowercase letters, digits and underscores, "
            "starting with a letter or digit.")
    if cleaned in RESERVED or cleaned.startswith(RESERVED_PREFIXES):
        raise AccountError("taken", "That name is taken.")
    return cleaned


def _one_line(text: str, limit: int) -> str:
    """Printable, single-line, collapsed whitespace. `display_name` lands in the persona's
    identity file — loaded into every prompt — and in Mike's terminal (review F6)."""
    cleaned = "".join(ch if ch.isprintable() else " " for ch in (text or ""))
    return " ".join(cleaned.split())[:limit]


def _valid_timezone(name: str) -> str:
    """The IANA zone name if it is one, else "" (provisioning then keeps the template's)."""
    name = (name or "").strip()[:64]
    if not name:
        return ""
    try:
        from zoneinfo import ZoneInfo
        ZoneInfo(name)
        return name
    except Exception:
        return ""


def register(username: str, display_name: str, password: str, timezone_name: str,
             consent: dict, city: str = "", path: Path | None = None) -> dict:
    """
    Record a sign-up request as `pending`. Returns the public view of the new entry.

    `consent` is the base-configuration permission the sign-up screen records
    (plan § 4.11, D11): `{"scope": "base_configuration", "text_version": "..."}`. It is
    stored on the account because at this moment there is no persona directory to hold
    it; `approve` copies it into the persona's consents.json.
    """
    path = path or ACCOUNTS_PATH
    name = check_username(username)
    display = _one_line(display_name, 80)
    if not display:
        raise AccountError("invalid_display_name", "Please enter the name to call you by.")
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LENGTH:
        raise AccountError("weak_password",
                           f"Passwords need at least {MIN_PASSWORD_LENGTH} characters.")
    if len(password) > MAX_PASSWORD_LENGTH:
        raise AccountError("weak_password",
                           f"Passwords can be at most {MAX_PASSWORD_LENGTH} characters.")
    if (not isinstance(consent, dict) or consent.get("scope") != "base_configuration"
            or not str(consent.get("text_version") or "").strip()):
        raise AccountError("no_consent", "Please read and accept the notice to continue.")
    tz = _valid_timezone(timezone_name)
    city_clean = _one_line(city, 80)

    password_hash = hash_password(password)   # outside the lock: deliberately slow
    with _locked(path):
        data = _read(path)
        accounts = data["accounts"]
        if name in accounts or _name_in_use(name):
            raise AccountError("taken", "That name is taken.")
        if sum(1 for a in accounts.values() if a.get("status") == "pending") >= MAX_PENDING:
            raise AccountError("limit", "Try again later.")
        now = _now()
        entry = {
            "username": name,
            "display_name": display,
            "status": "pending",
            "password_hash": password_hash,
            "cred_version": 1,
            "timezone": tz,
            "city": city_clean,
            "created_at": now,
            "decided_at": None,
            "decided_by": None,
            "note": "",
            "consents": {
                "base_configuration": {
                    "scope": "base_configuration",
                    "granted_at": now,
                    "text_version": str(consent["text_version"]).strip()[:40],
                    "withdrawn_at": None,
                },
            },
        }
        accounts[name] = entry
        _write(path, data)
    return public_view(entry)


def authenticate(username: str, password: str, path: Path | None = None) -> dict | None:
    """
    The account entry if `password` is right for `username`, else None.

    Status is NOT checked here — the caller reports pending/rejected/disabled, and only
    after a correct password, so a wrong guess never learns whether a name is waiting.
    """
    entry = get(username, path)
    if not entry or not password:
        return None
    if not verify_password(password, entry.get("password_hash", "")):
        return None
    return entry


# ---------------------------------------------------------------------------
# Mike's decisions — called by scripts/accounts.py on the VM, never over HTTP
# ---------------------------------------------------------------------------

def update(username: str, by: str = "mike", path: Path | None = None, **changes) -> dict:
    """
    Apply `changes` to one entry under the lock. Returns the public view.

    `status` changes stamp `decided_at`/`decided_by`. Any change to status other than to
    `active`, and any password change, bumps `cred_version` — which is what revokes every
    token that user holds at once without touching anyone else's.
    """
    path = path or ACCOUNTS_PATH
    name = (username or "").strip().lower()
    with _locked(path):
        data = _read(path)
        entry = data["accounts"].get(name)
        if entry is None:
            raise AccountError("unknown", f"No account named {name!r}.")
        status = changes.get("status")
        if status is not None and status not in STATUSES:
            raise AccountError("bad_status", f"Unknown status {status!r}.")
        bump = ("password_hash" in changes) or (status is not None and status != "active")
        entry.update(changes)
        if status is not None:
            entry["decided_at"] = _now()
            entry["decided_by"] = by
        if bump:
            entry["cred_version"] = int(entry.get("cred_version") or 1) + 1
        _write(path, data)
    return public_view(entry)


def remove(username: str, path: Path | None = None) -> bool:
    """
    Delete one entry — the store's only deletion, and only of a `disabled` account. Called by
    `scripts/accounts.py purge` as its last step, after everything the account owned is gone;
    every other decision changes a status and keeps the entry (archive rule). False when there
    is no such entry, so a re-run purge finishes cleanly.
    """
    path = path or ACCOUNTS_PATH
    name = (username or "").strip().lower()
    with _locked(path):
        data = _read(path)
        entry = data["accounts"].get(name)
        if entry is None:
            return False
        if entry.get("status") != "disabled":
            raise AccountError("not_disabled", f"{name} is {entry.get('status')}; only a "
                                               "disabled account can be removed.")
        del data["accounts"][name]
        _write(path, data)
    return True


def generate_temporary_password() -> str:
    """A password Mike reads out once (D3). Long enough to clear MIN_PASSWORD_LENGTH."""
    return secrets.token_urlsafe(12)
