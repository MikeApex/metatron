"""
core/connections.py — a user connects her own Google account from the app.

Multi-user plan archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.10. A second user
(an account persona) enters her Google address and ONE Google app password — the same app
password serves CalDAV (calendar), IMAP (reading mail) and SMTP (sending it) — and the server
tests both before it writes anything. This module is what the HTTP routes call:

    connect_google(persona, address, app_password) -> dict   POST   /connections/google
    status(persona) -> dict                                   GET    /connections
    disconnect_google(persona) -> dict                        DELETE /connections/google

**The caller must check consent first.** `POST /connections/google` refuses without a current
`correspondence_read` record (§ 4.11: `core.consent.is_granted("correspondence_read", persona)`).
That check belongs to the route, not here, so this module stays usable from a provisioning
script or a test without a consent store — but no user-facing path may reach `connect_google`
without it. Withdrawing `correspondence_read` must call `disconnect_google`.

**Where the password lives — and only there (review C1).** The app password is written to
`config/personas/{p}/credentials.yaml` and nowhere else: never into caldav.yaml/email.yaml,
which `scripts/metatron-backup.sh` copies to Mike's Mac as a plaintext tarball (it excludes
`*/credentials.yaml`), never into the status file, a log line, a return value or an exception
message. `tools/caldav.py` and `tools/mail.py` merge it in at their single config loaders
(`_load_config`, review C1: every password read goes through them), via `apply_credentials`
below. Mike's inline passwords keep working: with no credentials.yaml the loaders return
exactly what they always did.

**The credentials.yaml schema — one record per provider, not per service:**

    google:
      address: her@gmail.com
      app_password: abcdefghijklmnop

One record because Google issues one app password for all three protocols and § 4.10 tells
her exactly that; per-service keys would let calendar and mail drift onto two values that a
single Disconnect must both delete. Keyed by provider (`google:`) so a later connection — a
work account, Mark 2's OAuth route — sits beside it rather than overwriting it. `address` is
kept with the password so the loaders can fill an empty auth.username from it.

Mike-safety: a persona whose caldav.yaml or email.yaml already holds an INLINE password was
configured by hand on the VM (Mike's own persona today). Connect and Disconnect both refuse it
(`step: "existing"`): the panel is for account users, and one tap must not replace or disable a
working hand-built configuration — nor, by connecting over it, leave the old inline password
sitting in every backup while the panel claims the credential lives only on the VM.
"""

from __future__ import annotations

import json
import logging
import os
import re
import tempfile
import threading
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from core.persona import persona_config_dir, persona_data_dir, validate_persona_name

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).parent.parent
_TEMPLATES = _ROOT / "config" / "templates"

CREDENTIALS_FILENAME = "credentials.yaml"

# Shape check only — Google is the authority on whether the account exists. It also keeps
# anything path- or URL-shaped out of the calendar URL the address is interpolated into.
_ADDRESS = re.compile(r"^[A-Za-z0-9._%+-]{1,64}@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}$")
_MAX_PASSWORD_CHARS = 128

# One writer at a time in this process: connect and disconnect each touch three files, and a
# double-tapped Connect must not interleave two half-written sets.
_WRITE_LOCK = threading.Lock()

_CREDENTIALS_HEADER = (
    "# Google app password for this persona — written by core/connections.py when the user\n"
    "# connected her account in the app (plan § 4.10). This is the ONLY place it is stored:\n"
    "# caldav.yaml and email.yaml leave auth.password empty and tools/caldav.py and\n"
    "# tools/mail.py read it from here. scripts/metatron-backup.sh excludes this file and\n"
    "# .gitignore ignores it. Disconnect in the app deletes it. Do not copy it anywhere.\n"
)

_PASSWORD_LINE_NOTE = "  # held in credentials.yaml beside this file (core/connections.py)"


# --- the credentials file, read by the tool loaders ----------------------------------------

def credentials_path(config_dir: Path) -> Path:
    return Path(config_dir) / CREDENTIALS_FILENAME


def read_credentials(config_dir: Path) -> dict:
    """The parsed credentials.yaml beside a persona's configs, or {} when absent or unreadable.

    Unreadable is logged WITHOUT the parser's message: a YAML error quotes the offending line,
    and the offending line is the password.
    """
    path = credentials_path(config_dir)
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except Exception as exc:  # noqa: BLE001
        logger.warning("[connections] %s is unreadable (%s) — ignored", path, type(exc).__name__)
        return {}
    return data if isinstance(data, dict) else {}


def apply_credentials(cfg: dict, config_dir: Path) -> dict:
    """
    Merge the Google app password from credentials.yaml into a loaded caldav/email config.

    Called by tools/caldav.py and tools/mail.py `_load_config` with the directory the config
    was read from — not a persona name, so a test or caller that redirected the loader's
    directory gets the credentials file from that same directory and never another persona's.
    credentials.yaml wins over an inline password: it is the file the app manages and
    Disconnect deletes, so an inline value beside it can only be stale. With no credentials
    file the config comes back unchanged — Mike's inline passwords work exactly as before.
    """
    google = read_credentials(config_dir).get("google") or {}
    password = str(google.get("app_password") or "")
    if not password:
        return cfg
    auth = dict(cfg.get("auth") or {})
    auth["password"] = password
    if not str(auth.get("username") or "").strip():
        auth["username"] = str(google.get("address") or "")
    merged = dict(cfg)
    merged["auth"] = auth
    return merged


# --- small helpers -------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _scrub(text: str, secrets: tuple[str, ...]) -> str:
    """Remove every form of the password a message could carry. Belt and braces: no library
    error seen so far quotes it, but an error message is the one place it could leak from."""
    out = str(text)
    for s in secrets:
        if s and len(s) >= 4:
            out = out.replace(s, "[redacted]")
    return out


def _secret_forms(raw: str, normalised: str) -> tuple[str, ...]:
    # Google shows an app password as four groups of four; she may paste it either way.
    groups = tuple(g for g in raw.split() if len(g) >= 4)
    return (raw, raw.strip(), normalised) + groups


def _raw_yaml(path: Path) -> dict:
    """The file as written — NOT through the tool loaders, which would merge credentials.yaml
    in and make an app-managed password look inline."""
    if not path.exists():
        return {}
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:  # noqa: BLE001
        return {}
    return data if isinstance(data, dict) else {}


def _inline_password(path: Path) -> bool:
    return bool(str(((_raw_yaml(path).get("auth") or {}).get("password")) or "").strip())


def _write_private(path: Path, text: str) -> None:
    """Atomic write, 600 from the first byte — never a moment where the file is world-readable."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=f".{path.name}.")
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    except BaseException:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


def _profile_timezone(persona: str) -> str:
    """The persona's IANA zone from profile.yaml (`location.timezone`), else UTC."""
    prof = _raw_yaml(persona_config_dir(persona) / "profile.yaml")
    tz = str(((prof.get("location") or {}).get("timezone")) or "").strip()
    if tz:
        try:
            ZoneInfo(tz)
            return tz
        except Exception:  # noqa: BLE001 — a bad value must not block connecting
            pass
    return "UTC"


def _set_lines(text: str, edits: list[tuple[str, str]]) -> str:
    """Replace whole lines, keeping each line's indentation. `edits` is (key regex, new value
    text). Line edits rather than a YAML round-trip so the template's comments — which carry
    the Google-specific warnings — survive into her file."""
    for key, value in edits:
        pattern = re.compile(rf"^(\s*)({key}):.*$", re.M)
        text = pattern.sub(lambda m, v=value: f"{m.group(1)}{m.group(2)}: {v}", text, count=1)
    return text


def _render(base_texts: list[str], edits: list[tuple[str, str]], expect: dict) -> str:
    """
    Apply `edits` to the first base text whose result parses to exactly the expected values,
    with every other key unchanged. The persona's existing file is tried first (it may carry
    settings of hers — extra_calendars, a check interval), then the template. If neither edits
    cleanly — a hand-rewritten file, a template that has drifted — the values are dumped plainly:
    a file that loses its comments is acceptable; a file with a wrong value in it is not.
    """
    def apply(data: dict) -> dict:
        out = json.loads(json.dumps(data, default=str))
        for dotted, value in expect.items():
            node = out
            *parents, leaf = dotted.split(".")
            for p in parents:
                if not isinstance(node.get(p), dict):
                    node[p] = {}
                node = node[p]
            node[leaf] = value
        return out

    last_base: dict = {}
    for base in base_texts:
        if base is None:
            continue
        try:
            base_data = yaml.safe_load(base) or {}
            if not isinstance(base_data, dict):
                continue
            wanted = apply(base_data)
            new = _set_lines(base, edits)
            if json.loads(json.dumps(yaml.safe_load(new) or {}, default=str)) == wanted:
                return new if new.endswith("\n") else new + "\n"
            last_base = base_data
        except Exception:  # noqa: BLE001
            continue
    return yaml.safe_dump(apply(last_base), sort_keys=False, allow_unicode=True)


def _q(value: str) -> str:
    """A YAML double-quoted scalar (JSON strings are valid YAML)."""
    return json.dumps(value)


def _status_path(persona: str) -> Path:
    return persona_data_dir(persona) / "connections" / "google.json"


def _read_status_file(persona: str) -> dict:
    path = _status_path(persona)
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001
        return {}


def _write_status_file(persona: str, data: dict) -> None:
    # Non-secret by construction: callers pass address, calendar names and timestamps only.
    _write_private(_status_path(persona), json.dumps(data, indent=2) + "\n")


def _template(name: str) -> str:
    return (_TEMPLATES / name).read_text()


def _existing(path: Path) -> str | None:
    return path.read_text() if path.exists() else None


def _snapshot(paths: list[Path]) -> dict[Path, bytes | None]:
    return {p: (p.read_bytes() if p.exists() else None) for p in paths}


def _restore(snap: dict[Path, bytes | None]) -> None:
    for path, content in snap.items():
        try:
            if content is None:
                path.unlink(missing_ok=True)
            else:
                _write_private(path, content.decode())
        except Exception as exc:  # noqa: BLE001
            logger.error("[connections] could not restore %s (%s)", path, type(exc).__name__)


def _fail(step: str, remedy: str) -> dict:
    return {"ok": False, "step": step, "remedy": remedy}


_EXISTING_REMEDY = (
    "This account's calendar or mail was set up by hand on the server, so it cannot be "
    "changed from the app. Nothing was changed. Ask the developer to move it to the app's "
    "Connections panel if you want to manage it here."
)

_WRITE_REMEDY = (
    "Google accepted the address and app password, but saving the connection failed on the "
    "server. Nothing was changed. Try again in a minute; if it keeps failing, tell the developer."
)


# --- the three operations ------------------------------------------------------------------

def connect_google(persona: str, address: str, app_password: str) -> dict:
    """
    Test a Google address + app password, and only if both tests pass, save the connection.

    The caller checks `core.consent.is_granted("correspondence_read", persona)` first (plan
    § 4.11) for a fast refusal; it is checked again under the write lock before anything is
    written, so a withdrawal during the probes still wins.

    Order (§ 4.10): CalDAV discovery against Google's legacy endpoint, then an IMAP login.
    Either failing writes NOTHING. On success writes three files under
    config/personas/{persona}/, each chmod 600: caldav.yaml and email.yaml (enabled, built from
    config/templates/ with auth.password left empty) and credentials.yaml (the app password —
    its only home), plus the non-secret status file.

    Returns:
        {"ok": True, "address": str, "calendars": [display names found]}
        {"ok": False, "step": "input"|"existing"|"calendar"|"mail"|"write", "remedy": str}
    The password never appears in any return value, log line or file other than credentials.yaml.
    """
    persona = validate_persona_name(persona)
    raw_password = app_password if isinstance(app_password, str) else ""
    # Google displays an app password as "abcd efgh ijkl mnop"; the spaces are display only.
    password = "".join(raw_password.split())
    secrets = _secret_forms(raw_password, password)
    address = (address or "").strip().lower() if isinstance(address, str) else ""

    if not _ADDRESS.match(address) or len(address) > 254:
        return _fail("input", "That does not look like a Google email address. Check it and try again.")
    if not password or len(password) > _MAX_PASSWORD_CHARS:
        return _fail("input", "Enter the app password Google gave you (16 letters, from "
                              "myaccount.google.com/apppasswords).")

    cfg_dir = persona_config_dir(persona)
    caldav_path, email_path = cfg_dir / "caldav.yaml", cfg_dir / "email.yaml"
    if _inline_password(caldav_path) or _inline_password(email_path):
        return _fail("existing", _EXISTING_REMEDY)

    from tools import caldav, mail   # lazy: both tools import this module's apply_credentials

    try:
        cal = caldav.probe_google_calendar(address, password)
    except Exception as exc:  # noqa: BLE001 — a probe must never raise the password out
        cal = {"ok": False, "auth": False, "error": f"{type(exc).__name__}: {exc}"}
    if not cal.get("ok"):
        if cal.get("auth"):
            remedy = ("Google refused this address and app password for the calendar. Check the "
                      "address, and that the password is an app password from "
                      "myaccount.google.com/apppasswords (2-Step Verification must be on) — not "
                      "your ordinary Google password." + caldav._credential_remedy(persona, in_app=True))
        else:
            remedy = ("Could not reach Google Calendar to check the connection "
                      f"({_scrub(cal.get('error', ''), secrets)}). Nothing was saved — try again "
                      "in a minute.")
        logger.info("[connections] %s: calendar test failed (auth=%s)", persona, bool(cal.get("auth")))
        return _fail("calendar", _scrub(remedy, secrets))

    email_defaults = _raw_yaml(_TEMPLATES / "email.yaml")
    imap_host = str(email_defaults.get("host") or "imap.gmail.com").strip()
    try:
        login = mail.probe_imap_login(address, password, host=imap_host)
    except Exception as exc:  # noqa: BLE001
        login = {"ok": False, "auth": False, "error": f"{type(exc).__name__}: {exc}"}
    if not login.get("ok"):
        if login.get("auth"):
            remedy = ("Google accepted the calendar but refused the mail login. "
                      + mail.IMAP_LOGIN_HINT + mail._credential_remedy(persona, in_app=True))
        else:
            remedy = ("Could not reach Gmail to check the connection "
                      f"({_scrub(login.get('error', ''), secrets)}). Nothing was saved — try again "
                      "in a minute.")
        logger.info("[connections] %s: mail test failed (auth=%s)", persona, bool(login.get("auth")))
        return _fail("mail", _scrub(remedy, secrets))

    calendars = [str(n) for n in cal.get("calendars") or []]
    calendar_url = cal.get("calendar_url") or caldav.google_calendar_url(address)
    tz = _profile_timezone(persona)

    caldav_text = _render(
        [_existing(caldav_path), _template("caldav.yaml")],
        [("enabled", "true"), ("calendar_url", _q(calendar_url)), ("username", _q(address)),
         ("password", '""' + _PASSWORD_LINE_NOTE), ("timezone", _q(tz))],
        {"enabled": True, "calendar_url": calendar_url, "auth.username": address,
         "auth.password": "", "timezone": tz},
    )
    email_text = _render(
        [_existing(email_path), _template("email.yaml")],
        [("enabled", "true"), ("host", _q(imap_host)), ("username", _q(address)),
         ("password", '""' + _PASSWORD_LINE_NOTE)],
        {"enabled": True, "host": imap_host, "auth.username": address, "auth.password": ""},
    )
    creds_text = _CREDENTIALS_HEADER + yaml.safe_dump(
        {"google": {"address": address, "app_password": password}}, sort_keys=False)

    creds_path = credentials_path(cfg_dir)
    status_path = _status_path(persona)
    with _WRITE_LOCK:
        # Re-checked HERE, under the lock disconnect_google also takes (Stage 2 review F1):
        # the probes above take seconds, and a withdrawal in that window must not be followed
        # by a connection landing with no live permission behind it. Either order now ends
        # disconnected. The route's own check is still the fast refusal.
        from core import consent
        if not consent.is_granted("correspondence_read", persona):
            return _fail("consent", "Permission to read your calendar and mail was withdrawn, "
                                    "so nothing was connected.")
        snap = _snapshot([creds_path, email_path, caldav_path, status_path])
        try:
            # credentials first: an enabled config is never on disk without its password.
            _write_private(creds_path, creds_text)
            _write_private(email_path, email_text)
            _write_private(caldav_path, caldav_text)
            _write_status_file(persona, {
                "address": address, "calendars": calendars,
                "checked_at": _now(), "connected_at": _now(),
            })
        except Exception as exc:  # noqa: BLE001
            _restore(snap)
            logger.error("[connections] %s: saving the connection failed (%s)",
                         persona, type(exc).__name__)
            return _fail("write", _WRITE_REMEDY)

    logger.info("[connections] %s: Google connected (%d calendars)", persona, len(calendars))
    return {"ok": True, "address": address, "calendars": calendars}


def status(persona: str) -> dict:
    """
    What the Connections panel shows. Never the password.

    Returns {"connected": bool, "managed_in_app": bool, "address": str | None,
             "calendars": [names found at the last successful check], "checked_at": ISO-8601 UTC
             or None}.
    `connected` is read from the files, not the status file: true when the configs are enabled
    and have a password to use. `managed_in_app` is false for a hand-configured persona (inline
    password — Mike's); the panel should show it as connected but offer no Disconnect, which
    `disconnect_google` would refuse anyway.
    """
    persona = validate_persona_name(persona)
    cfg_dir = persona_config_dir(persona)
    caldav_cfg = _raw_yaml(cfg_dir / "caldav.yaml")
    email_cfg = _raw_yaml(cfg_dir / "email.yaml")
    has_creds = bool(str(((read_credentials(cfg_dir).get("google") or {}).get("app_password")) or ""))
    inline = _inline_password(cfg_dir / "caldav.yaml") or _inline_password(cfg_dir / "email.yaml")
    recorded = _read_status_file(persona)

    if has_creds and not inline:
        connected = bool(caldav_cfg.get("enabled")) and bool(email_cfg.get("enabled"))
        managed = True
    elif inline:
        connected = bool(caldav_cfg.get("enabled")) or bool(email_cfg.get("enabled"))
        managed = False
    else:
        connected, managed = False, True

    address = (recorded.get("address")
               or str(((caldav_cfg.get("auth") or {}).get("username")) or "").strip() or None)
    return {
        "connected": connected,
        "managed_in_app": managed,
        "address": address if (connected or recorded) else None,
        "calendars": list(recorded.get("calendars") or []) if connected else [],
        "checked_at": recorded.get("checked_at") if connected else None,
    }


def disconnect_google(persona: str) -> dict:
    """
    Disconnect: `enabled: false` in caldav.yaml and email.yaml, credentials.yaml DELETED (no
    retained copy — § 4.10 item 3), status updated. Afterwards the not-connected path (§ 4.8,
    Stage 1.13) takes over: `tools.caldav._query_events` returns {"events": [], "connected": False}.

    Idempotent: disconnecting a persona with nothing connected returns ok. Refuses a persona
    with an inline password (`step: "existing"`) — see the module docstring.

    Returns {"ok": True, "connected": False} or {"ok": False, "step": "existing"|"write", "remedy": str}.
    """
    persona = validate_persona_name(persona)
    cfg_dir = persona_config_dir(persona)
    caldav_path, email_path = cfg_dir / "caldav.yaml", cfg_dir / "email.yaml"
    if _inline_password(caldav_path) or _inline_password(email_path):
        return _fail("existing", _EXISTING_REMEDY)

    creds_path = credentials_path(cfg_dir)
    status_path = _status_path(persona)
    with _WRITE_LOCK:
        snap = _snapshot([caldav_path, email_path, status_path])
        try:
            # Configs first, then the credential: a config that still says enabled is never
            # left pointing at a password that is gone.
            for path in (caldav_path, email_path):
                text = _existing(path)
                if text is None:
                    continue
                data = yaml.safe_load(text) or {}
                if isinstance(data, dict) and data.get("enabled"):
                    _write_private(path, _render([text], [("enabled", "false")], {"enabled": False}))
            recorded = _read_status_file(persona)
            _write_status_file(persona, {
                "address": recorded.get("address"), "calendars": [],
                "checked_at": recorded.get("checked_at"), "disconnected_at": _now(),
            })
            creds_path.unlink(missing_ok=True)
        except Exception as exc:  # noqa: BLE001
            _restore(snap)
            logger.error("[connections] %s: disconnect failed (%s)", persona, type(exc).__name__)
            return _fail("write", "Disconnecting failed on the server. Try again in a minute; "
                                  "if it keeps failing, tell the developer.")

    logger.info("[connections] %s: Google disconnected", persona)
    return {"ok": True, "connected": False}
