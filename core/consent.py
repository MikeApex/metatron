"""
core/consent.py — the user's own permissions, as records code can check.

Plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.11 (D9, D11).

Mike's ruling (2026-10-27): *"She should be notified through the app and provide permission
herself."* So a permission is not a sentence somebody remembers — it is a record, written
when she taps *I understand* in the app, checked in Python before the thing it permits runs,
and withdrawable. Privacy is enforced in code, never in prompts (CLAUDE.md).

    data/personas/{p}/consents.json      {"records": [ {scope, granted_at, text_version,
                                                         withdrawn_at, evidence?}, ... ]}

**Fail-closed by construction.** A persona with no file has no permission for anything.
That is every synthetic persona, so their tests prove the refusals; `mike` gets records
citing his own rulings, written on the VM by `scripts/accounts.py seed-consent` (§ 4.11).

Records are appended, never edited in place except to stamp `withdrawn_at`: the history
of what was agreed, to which text, and when it was withdrawn is the evidence the
ROADMAP § 0 amendment points at.

Stdlib only — `scripts/accounts.py` imports this on the VM.
"""

from __future__ import annotations

import contextlib
import fcntl
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

SCOPES = ("base_configuration", "correspondence_read", "tone_profile", "contact_enrichment")

# The texts the user is shown live in config/consent/<scope>_<version>.md, so the record's
# `text_version` points at exactly what she read.
TEXT_DIR = Path(__file__).parent.parent / "config" / "consent"

# The version the app shows now. Changing a text means adding a new file and bumping this —
# never editing a shipped one, or a record would point at words its holder never read.
CURRENT_VERSIONS = {"base_configuration": "v1", "correspondence_read": "v1",
                    "tone_profile": "v1"}

# What the app may grant and withdraw through /consents. base_configuration is given at
# sign-up and lives with the account; contact_enrichment is not built (its build adds it).
APP_SCOPES = ("correspondence_read", "tone_profile")


def current_text(scope: str) -> tuple[str, str]:
    """(version, markdown) of the text the app shows for a scope now."""
    version = CURRENT_VERSIONS[scope]
    return version, text_path(scope, version).read_text()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(persona: str) -> Path:
    from core.persona import persona_data_dir
    return persona_data_dir(persona) / "consents.json"


def _read(path: Path) -> dict:
    if not path.exists():
        return {"records": []}
    with open(path) as f:
        data = json.load(f)
    if not isinstance(data, dict) or not isinstance(data.get("records"), list):
        # Unreadable is not "no permission recorded" — but refusing is the safe reading of
        # it, and the raise makes the corruption visible rather than silently revoking.
        raise ValueError(f"{path} is not a valid consent file")
    return data


def _write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".consents.", dir=str(path.parent))
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
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path.with_name(path.name + ".lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)


def text_path(scope: str, version: str) -> Path:
    return TEXT_DIR / f"{scope}_{version}.md"


def records(persona: str) -> list[dict]:
    """Every record for the persona, oldest first. Empty when there is no file."""
    return list(_read(_path(persona))["records"])


def current(scope: str, persona: str) -> dict | None:
    """The live (granted, not withdrawn) record for a scope, or None."""
    try:
        recs = records(persona)
    except Exception:
        return None   # fail closed: an unreadable file grants nothing
    live = [r for r in recs if r.get("scope") == scope and not r.get("withdrawn_at")]
    return live[-1] if live else None


def is_granted(scope: str, persona: str) -> bool:
    return current(scope, persona) is not None


def grant(scope: str, persona: str, text_version: str, evidence: str | None = None) -> dict:
    """Record a permission. Idempotent: a scope already granted returns its live record."""
    if scope not in SCOPES:
        raise ValueError(f"unknown consent scope {scope!r}")
    path = _path(persona)
    with _locked(path):
        data = _read(path)
        for r in reversed(data["records"]):
            if r.get("scope") == scope and not r.get("withdrawn_at"):
                return r
        rec = {"scope": scope, "granted_at": _now(), "text_version": text_version,
               "withdrawn_at": None}
        if evidence:
            rec["evidence"] = evidence
        data["records"].append(rec)
        _write(path, data)
    return rec


def withdraw(scope: str, persona: str) -> bool:
    """Stamp every live record for the scope as withdrawn. True if anything was live."""
    path = _path(persona)
    with _locked(path):
        data = _read(path)
        changed = False
        for r in data["records"]:
            if r.get("scope") == scope and not r.get("withdrawn_at"):
                r["withdrawn_at"] = _now()
                changed = True
        if changed:
            _write(path, data)
    return changed


def seed_from_account(persona: str, account_consents: dict) -> bool:
    """
    Copy the sign-up permission from the account entry into consents.json at approval.

    **Create-only** (plan § 4.4, verify N1): if the persona already has a consents file it
    is left exactly as it is, so re-running `approve` can never rewrite or duplicate what
    she has granted or withdrawn since. Returns True if it wrote the file.
    """
    path = _path(persona)
    with _locked(path):
        if path.exists():
            return False
        recs = []
        for scope, rec in sorted((account_consents or {}).items()):
            if scope in SCOPES and isinstance(rec, dict) and rec.get("granted_at"):
                recs.append({"scope": scope, "granted_at": rec["granted_at"],
                             "text_version": rec.get("text_version", ""),
                             "withdrawn_at": rec.get("withdrawn_at")})
        _write(path, {"records": recs})
    return True
