"""
tests/test_connections.py — a user connects her own Google account from the app, and the app
password lands in exactly one file (archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.10,
§ 6.1 item 13; review C1).

Pinned here:

  1. A failing test writes NOTHING and returns the remedy — calendar refused, calendar unreachable,
     mail refused, mail unreachable — and the remedy never carries the password, even when the
     underlying error text does.
  2. A passing connect writes exactly her three config files (caldav.yaml, email.yaml,
     credentials.yaml), chmod 600, plus the non-secret status file, and touches no other persona.
  3. After a connect the password string is in NO file under the temp tree except
     credentials.yaml, and the backup's own `--exclude` pattern (read from
     scripts/metatron-backup.sh, run through a real `tar`) leaves credentials.yaml out.
  4. `status()` never contains the password; `disconnect_google` deletes credentials.yaml and the
     not-connected path (§ 4.8) takes over.
  5. Mike's shape — inline passwords, no credentials.yaml — still loads its password, and the
     panel refuses to connect over it or disconnect it.
  6. The caldav and mail loaders (and intake's import of mail's) merge credentials.yaml.

EVERY LIVE METER IS STUBBED: sockets are blocked outright (DNS and connect — an attempt is counted
and raises), CalDAV is a fake Google-shaped server behind `requests.request`, IMAP is a fake
`imaplib.IMAP4_SSL`. Persona paths point at a temporary root (`core.persona._ROOT`) — no tracked
or real persona file is read or written.

    METATRON_AUTH_PASSWORD=x python3 tests/test_connections.py      # standalone
    python -m pytest -q tests/test_connections.py
"""
from __future__ import annotations

import imaplib
import importlib
import json
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from fnmatch import fnmatch
from pathlib import Path
from urllib.parse import quote, unquote, urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

import requests  # noqa: E402
import yaml  # noqa: E402

import core.connections as CONN  # noqa: E402
import core.persona as P  # noqa: E402
import tools.caldav as CAL  # noqa: E402
import tools.mail as MAIL  # noqa: E402

_REPO = Path(__file__).parent.parent
_PERSONA = "zz_conn_test"
_OTHER = "zz_conn_other"
_ADDRESS = "iva.example@gmail.com"
_PASSWORD = "qwertyuiopasdfgh"           # what Google would issue: 16 letters
_PASSWORD_SHOWN = "qwer tyui opas dfgh"   # how Google displays it, and how she may paste it
_CALLS: dict = {}


# --- the sandbox -----------------------------------------------------------------------------

class _Patches:
    """setattr with restore — nothing leaks into other suites run in the same process."""

    def __init__(self):
        self._saved: list[tuple[object, str, object]] = []

    def set(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved.clear()


def _blocked(kind):
    def fn(*args, **kwargs):
        _CALLS["network"].append(kind)
        raise OSError(f"network blocked in test ({kind})")
    return fn


class _Resp:
    def __init__(self, status, text=""):
        self.status_code, self.text = status, text

    def raise_for_status(self):
        if self.status_code >= 400:
            err = requests.HTTPError(f"{self.status_code} Client Error")
            err.response = self
            raise err


def _multistatus(*responses: str) -> str:
    return ('<?xml version="1.0"?><D:multistatus xmlns:D="DAV:" '
            'xmlns:caldav="urn:ietf:params:xml:ns:caldav">' + "".join(responses) + "</D:multistatus>")


class FakeGoogle:
    """Google's CalDAV shape as probed 2026-10-24 (tests/test_caldav_multi_calendar.py): the
    principal is answered only at /calendar/dav/. Refuses 401 unless the auth is exactly the
    expected address + app password. `mode="down"` refuses every connection (discovery swallows
    those per start point, as it always has); `mode="down_late"` answers the principal and then
    raises a connection error that quotes the credentials, to prove the remedy scrubs it."""

    def __init__(self, address=_ADDRESS, password=_PASSWORD, mode="ok"):
        self.address, self.password, self.mode = address, password, mode

    def request(self, method, url, data=None, headers=None, auth=None, timeout=None, **_):
        _CALLS["caldav"].append((method, url))
        if self.mode == "down":
            raise requests.ConnectionError(f"connection reset (sent auth {auth})")
        if tuple(auth or ()) != (self.address, self.password):
            return _Resp(401)
        path = unquote(urlparse(url).path)
        if self.mode == "down_late" and path != "/calendar/dav/":
            raise requests.ConnectionError(f"connection reset (sent auth {auth})")
        enc = quote(self.address, safe="")
        if method != "PROPFIND":
            return _Resp(207, _multistatus())
        if path == "/calendar/dav/":
            return _Resp(207, _multistatus(
                "<D:response><D:href>/calendar/dav/</D:href><D:propstat><D:prop>"
                f"<D:current-user-principal><D:href>/calendar/dav/{enc}/user</D:href>"
                "</D:current-user-principal></D:prop></D:propstat></D:response>"))
        if path == f"/calendar/dav/{self.address}/user":
            return _Resp(207, _multistatus(
                f"<D:response><D:href>/calendar/dav/{enc}/user/</D:href><D:propstat><D:prop>"
                f"<caldav:calendar-home-set><D:href>/calendar/dav/{enc}/</D:href>"
                "</caldav:calendar-home-set></D:prop></D:propstat></D:response>"))
        if path == f"/calendar/dav/{self.address}/":
            def entry(href, name, is_cal=True):
                rtype = "<D:collection/><caldav:calendar/>" if is_cal else "<D:collection/>"
                return (f"<D:response><D:href>{href}</D:href><D:propstat><D:prop>"
                        f"<D:displayname>{name}</D:displayname><D:resourcetype>{rtype}"
                        f"</D:resourcetype></D:prop></D:propstat></D:response>")
            return _Resp(207, _multistatus(
                entry(f"/calendar/dav/{enc}/", "", is_cal=False),
                entry(f"/calendar/dav/{enc}/events/", self.address),
                entry("/calendar/dav/family%40group.calendar.google.com/events/", "Shared with Mike"),
                entry("/calendar/dav/hu.hungarian%23holiday%40group.v.calendar.google.com/events/",
                      "Holidays in Hungary"),
            ))
        if path.startswith("/.well-known"):
            return _Resp(404)
        return _Resp(207, _multistatus())

    def get(self, url, **_):
        _CALLS["caldav"].append(("GET", url))
        return _Resp(404)


def _fake_imap(password=_PASSWORD, mode="ok"):
    class FakeIMAP:
        def __init__(self, host, timeout=None):
            _CALLS["imap"].append(("connect", host))
            if mode == "down":
                raise OSError(f"timed out talking to {host} with {password}")
            self.host = host

        def login(self, user, pw):
            _CALLS["imap"].append(("login", user))
            if (user, pw) != (_ADDRESS, password) or mode == "refuse":
                raise imaplib.IMAP4.error(b"[AUTHENTICATIONFAILED] Invalid credentials (Failure)")
            return ("OK", [b"logged in"])

        def logout(self):
            _CALLS["imap"].append(("logout", self.host))
            return ("BYE", [])
    return FakeIMAP


@contextmanager
def _sandbox(*, cal: FakeGoogle | None = None, imap=None):
    """A temporary root holding two personas — the one connecting and another whose files must
    never change — with every meter stubbed."""
    # The day-plan suites replace tools.caldav._query_events with a fixture stub for good when
    # pytest runs them in the same process; reload so the real function is the one under test.
    global CAL
    qe = CAL._query_events
    if getattr(getattr(qe, "__code__", None), "co_filename", "") != CAL.__file__:
        CAL = importlib.reload(CAL)

    root = Path(tempfile.mkdtemp(prefix="connections_"))
    for persona in (_PERSONA, _OTHER):
        (root / "config" / "personas" / persona).mkdir(parents=True)
        (root / "data" / "personas" / persona).mkdir(parents=True)
    (root / "config" / "personas" / _PERSONA / "profile.yaml").write_text(
        'name: "Iva"\nlocation:\n  city: "Budapest"\n  country: "Hungary"\n'
        '  timezone: "Europe/Budapest"\n')
    # What scripts/new_persona.sh / approve provisions: the templates, `enabled: false`.
    for name in ("caldav.yaml", "email.yaml"):
        shutil.copy(_REPO / "config" / "templates" / name,
                    root / "config" / "personas" / _PERSONA / name)
    other = root / "config" / "personas" / _OTHER
    (other / "caldav.yaml").write_text(_inline_caldav("other@example.com", "other-secret-1234"))
    (other / "email.yaml").write_text(_inline_email("other@example.com", "other-secret-1234"))
    (root / "data" / "personas" / _OTHER / "note.txt").write_text("hers\n")

    _CALLS.update(network=[], caldav=[], imap=[])
    p = _Patches()
    p.set(P, "_ROOT", root)
    # Re-point any binding another suite replaced, so every path resolves through _ROOT above.
    for mod in (CAL, MAIL):
        p.set(mod, "persona_config_dir", P.persona_config_dir)
    p.set(CONN, "persona_config_dir", P.persona_config_dir)
    p.set(CONN, "persona_data_dir", P.persona_data_dir)
    p.set(socket, "getaddrinfo", _blocked("dns"))
    p.set(socket, "create_connection", _blocked("connect"))
    p.set(socket.socket, "connect", _blocked("connect"))
    server = cal or FakeGoogle()
    p.set(CAL.requests, "request", server.request)
    p.set(CAL.requests, "get", server.get)
    p.set(imaplib, "IMAP4_SSL", imap or _fake_imap())
    CAL._discovery_cache.clear()
    # She has given the read permission, as the panel's screen records before Connect.
    # connect_google re-checks it under its write lock (Stage 2 review F1).
    from core import consent
    consent.grant("correspondence_read", _PERSONA, "v1")
    try:
        with P.persona_scope(_PERSONA):
            yield root
    finally:
        p.restore()
        CAL._discovery_cache.clear()
        shutil.rmtree(root, ignore_errors=True)


def test_withdrawn_permission_writes_nothing():
    """Stage 2 review F1: a withdrawal between the route's check and the write wins."""
    with _sandbox() as root:
        from core import consent
        consent.withdraw("correspondence_read", _PERSONA)
        out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
        assert out["ok"] is False and out["step"] == "consent", out
        assert not (root / "config" / "personas" / _PERSONA / "credentials.yaml").exists()


def _inline_caldav(user, pw) -> str:
    return (f'enabled: true\ncalendar_url: "https://www.google.com/calendar/dav/{user}/events"\n'
            f'auth:\n  username: "{user}"\n  password: "{pw}"\ntimezone: "Europe/London"\n')


def _inline_email(user, pw) -> str:
    return (f'enabled: true\nhost: "imap.gmail.com"\nauth:\n  username: "{user}"\n'
            f'  password: "{pw}"\n')


def _tree(root: Path) -> dict[str, bytes]:
    return {str(f.relative_to(root)): f.read_bytes() for f in sorted(root.rglob("*")) if f.is_file()}


def _cfg(root: Path, persona=_PERSONA) -> Path:
    return root / "config" / "personas" / persona


def _assert_no_password(obj, *extra: str) -> None:
    text = json.dumps(obj) if not isinstance(obj, str) else obj
    for s in (_PASSWORD, _PASSWORD_SHOWN, "qwer", "dfgh") + extra:
        assert s not in text, f"password fragment {s!r} leaked: {text[:300]}"


# --- 1. a failing test writes nothing --------------------------------------------------------

def test_calendar_refused_writes_nothing_and_names_the_remedy():
    with _sandbox(cal=FakeGoogle(password="the-right-one-xyz")) as root:
        before = _tree(root)
        out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
        assert out["ok"] is False and out["step"] == "calendar", out
        assert "app password" in out["remedy"] and "Connections panel" in out["remedy"], out
        assert "auth.password line" not in out["remedy"], "told her to edit a server file"
        _assert_no_password(out)
        assert _tree(root) == before, "a refused calendar test wrote something"
        assert _CALLS["imap"] == [], "IMAP tried after the calendar failed"
        assert _CALLS["network"] == [], _CALLS["network"]


def test_calendar_unreachable_writes_nothing_and_scrubs_the_error():
    for mode in ("down", "down_late"):
        with _sandbox(cal=FakeGoogle(mode=mode)) as root:
            before = _tree(root)
            out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
            assert out["ok"] is False and out["step"] == "calendar", (mode, out)
            assert "Could not reach Google Calendar" in out["remedy"], (mode, out)
            if mode == "down_late":
                assert "[redacted]" in out["remedy"], "the error quoted the password unscrubbed"
            _assert_no_password(out)
            assert _tree(root) == before, mode
            assert _CALLS["imap"] == [], mode


def test_mail_refused_writes_nothing_and_names_imap():
    with _sandbox(imap=_fake_imap(mode="refuse")) as root:
        before = _tree(root)
        out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
        assert out["ok"] is False and out["step"] == "mail", out
        assert "IMAP" in out["remedy"] and "Connections panel" in out["remedy"], out
        _assert_no_password(out)
        assert _tree(root) == before, "a refused mail test wrote something"
        assert _CALLS["caldav"], "the calendar test never ran first"


def test_mail_unreachable_writes_nothing_and_scrubs_the_error():
    with _sandbox(imap=_fake_imap(mode="down")) as root:
        before = _tree(root)
        out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
        assert out["ok"] is False and out["step"] == "mail", out
        assert "Could not reach Gmail" in out["remedy"], out
        _assert_no_password(out)
        assert _tree(root) == before


def test_bad_input_writes_nothing_and_calls_nothing():
    with _sandbox() as root:
        before = _tree(root)
        for address, pw in (("not-an-address", _PASSWORD), ("a@b", _PASSWORD),
                            ("x@gmail.com/../evil", _PASSWORD), (_ADDRESS, "   "), (_ADDRESS, None)):
            out = CONN.connect_google(_PERSONA, address, pw)
            assert out["ok"] is False and out["step"] == "input", (address, out)
        assert _tree(root) == before
        assert _CALLS["caldav"] == [] and _CALLS["imap"] == []


# --- 2. a passing connect --------------------------------------------------------------------

def test_connect_writes_exactly_three_files_600_and_no_other_persona():
    with _sandbox() as root:
        before = _tree(root)
        out = CONN.connect_google(_PERSONA, _ADDRESS.upper(), _PASSWORD_SHOWN)
        assert out == {"ok": True, "address": _ADDRESS,
                       "calendars": [_ADDRESS, "Shared with Mike", "Holidays in Hungary"]}, out
        after = _tree(root)
        changed = {k for k in after if before.get(k) != after[k]}
        cfg = f"config/personas/{_PERSONA}/"
        assert changed == {cfg + "caldav.yaml", cfg + "email.yaml", cfg + "credentials.yaml",
                           f"data/personas/{_PERSONA}/connections/google.json"}, changed
        assert not [k for k in before if k not in after], "a file was removed"
        for rel in changed:
            mode = stat.S_IMODE((root / rel).stat().st_mode)
            assert mode == 0o600, (rel, oct(mode))

        caldav = yaml.safe_load((_cfg(root) / "caldav.yaml").read_text())
        assert caldav["enabled"] is True, caldav
        assert caldav["calendar_url"] == f"https://www.google.com/calendar/dav/{_ADDRESS}/events"
        assert "apidata.googleusercontent.com" not in caldav["calendar_url"]
        assert caldav["auth"] == {"username": _ADDRESS, "password": ""}, caldav["auth"]
        assert caldav["timezone"] == "Europe/Budapest", caldav
        # Built from the template, so its Google warnings survive into her file.
        assert "401s on app passwords" in (_cfg(root) / "caldav.yaml").read_text()

        email = yaml.safe_load((_cfg(root) / "email.yaml").read_text())
        assert email["enabled"] is True and email["host"] == "imap.gmail.com", email
        assert email["auth"] == {"username": _ADDRESS, "password": ""}, email["auth"]
        assert email["check_interval_minutes"] == 240, "a template default was lost"
        assert "IMAP enabled" in (_cfg(root) / "email.yaml").read_text()

        creds = yaml.safe_load((_cfg(root) / "credentials.yaml").read_text())
        assert creds == {"google": {"address": _ADDRESS, "app_password": _PASSWORD}}, \
            "spaces Google displays must be stripped"
        assert _CALLS["network"] == [], _CALLS["network"]


def test_password_is_in_no_file_but_credentials_yaml():
    with _sandbox() as root:
        out = CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)
        assert out["ok"], out
        holders = [k for k, v in _tree(root).items() if _PASSWORD.encode() in v]
        assert holders == [f"config/personas/{_PERSONA}/credentials.yaml"], holders
        _assert_no_password(out)


def _backup_excludes() -> list[str]:
    """The --exclude globs scripts/metatron-backup.sh passes to tar — read from the script, so
    removing the credentials exclusion there fails this suite."""
    text = (_REPO / "scripts" / "metatron-backup.sh").read_text()
    return re.findall(r"--exclude='([^']+)'", text)


def test_backup_file_list_leaves_credentials_out():
    excludes = _backup_excludes()
    assert "*/credentials.yaml" in excludes, excludes
    with _sandbox() as root:
        assert CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)["ok"]
        tar = shutil.which("tar")
        if tar:
            # The real command shape: tar over config/personas and data/personas from the root.
            cmd = [tar, "-cf", "-"] + [f"--exclude={e}" for e in excludes] + [
                "config/personas", "data/personas"]
            archive = subprocess.run(cmd, cwd=root, capture_output=True, check=True).stdout
            listed = subprocess.run([tar, "-tf", "-"], input=archive, capture_output=True,
                                    check=True).stdout.decode().split()
            assert _PASSWORD.encode() not in archive, "the password is inside the backup archive"
        else:  # fnmatch carries tar's glob semantics for these patterns (`*` crosses `/`)
            listed = [rel for rel in _tree(root)
                      if not any(fnmatch(rel, e) for e in excludes)]
        assert f"config/personas/{_PERSONA}/caldav.yaml" in listed, listed  # the tar did run
        assert not [f for f in listed if f.endswith("credentials.yaml")], listed


# --- 3. status and disconnect ----------------------------------------------------------------

def test_status_never_contains_the_password():
    with _sandbox() as root:
        assert CONN.status(_PERSONA) == {"connected": False, "managed_in_app": True, "address": None,
                                         "calendars": [], "checked_at": None}
        assert CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)["ok"]
        st = CONN.status(_PERSONA)
        assert st["connected"] is True and st["managed_in_app"] is True, st
        assert st["address"] == _ADDRESS and "Shared with Mike" in st["calendars"], st
        assert st["checked_at"], st
        _assert_no_password(st)
        _assert_no_password((root / "data" / "personas" / _PERSONA / "connections" /
                             "google.json").read_text())


def test_disconnect_deletes_credentials_and_not_connected_takes_over():
    with _sandbox() as root:
        assert CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)["ok"]
        out = CONN.disconnect_google(_PERSONA)
        assert out == {"ok": True, "connected": False}, out
        assert not (_cfg(root) / "credentials.yaml").exists(), "credentials.yaml survived"
        for name in ("caldav.yaml", "email.yaml"):
            data = yaml.safe_load((_cfg(root) / name).read_text())
            assert data["enabled"] is False, (name, data)
            mode = stat.S_IMODE((_cfg(root) / name).stat().st_mode)
            assert mode == 0o600, (name, oct(mode))
        assert not [k for k, v in _tree(root).items() if _PASSWORD.encode() in v]
        _CALLS["caldav"].clear()
        for mode in ("own", "all"):
            raw = CAL._query_events("2026-10-26", "2026-10-28", persona=_PERSONA, calendars=mode)
            assert raw == {"events": [], "connected": False}, (mode, raw)
        assert _CALLS["caldav"] == [] and _CALLS["network"] == []
        st = CONN.status(_PERSONA)
        assert st["connected"] is False and st["calendars"] == [], st
        assert CONN.disconnect_google(_PERSONA)["ok"], "disconnect is not idempotent"


def test_reconnect_replaces_the_password_everywhere():
    with _sandbox(cal=FakeGoogle(password="zxcvbnmlkjhgfdsa"),
                  imap=_fake_imap(password="zxcvbnmlkjhgfdsa")) as root:
        # First connect under the old password is set up by hand through the module itself.
        CONN._write_private(_cfg(root) / "credentials.yaml", CONN._CREDENTIALS_HEADER + yaml.safe_dump(
            {"google": {"address": _ADDRESS, "app_password": _PASSWORD}}))
        out = CONN.connect_google(_PERSONA, _ADDRESS, "zxcvbnmlkjhgfdsa")
        assert out["ok"], out
        assert not [k for k, v in _tree(root).items() if _PASSWORD.encode() in v], \
            "the revoked password outlived the reconnect"


# --- 4. Mike's shape, and the loaders ---------------------------------------------------------

def test_inline_password_still_loads_with_no_credentials_file():
    with _sandbox() as root:
        assert not (_cfg(root, _OTHER) / "credentials.yaml").exists()
        assert CAL._load_config(_OTHER)["auth"]["password"] == "other-secret-1234"
        assert MAIL._load_config(_OTHER)["auth"]["password"] == "other-secret-1234"
        # A runtime 401 on a hand-configured persona still names the file to edit.
        assert "auth.password line" in CAL._credential_remedy(_OTHER)
        assert "auth.password line" in MAIL._credential_remedy(_OTHER)


def test_panel_refuses_a_hand_configured_persona():
    with _sandbox() as root:
        before = _tree(root)
        out = CONN.connect_google(_OTHER, "other@example.com", _PASSWORD)
        assert out["ok"] is False and out["step"] == "existing", out
        out = CONN.disconnect_google(_OTHER)
        assert out["ok"] is False and out["step"] == "existing", out
        assert _tree(root) == before, "a hand-configured persona was changed"
        assert _CALLS["caldav"] == [] and _CALLS["imap"] == [], "tested before refusing"
        st = CONN.status(_OTHER)
        assert st["connected"] is True and st["managed_in_app"] is False, st
        _assert_no_password(st, "other-secret-1234")


def test_loaders_merge_credentials_yaml():
    with _sandbox() as root:
        assert CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)["ok"]
        cal_cfg = CAL._load_config(_PERSONA)
        mail_cfg = MAIL._load_config(_PERSONA)
        assert cal_cfg["auth"] == {"username": _ADDRESS, "password": _PASSWORD}, cal_cfg["auth"]
        assert mail_cfg["auth"] == {"username": _ADDRESS, "password": _PASSWORD}, mail_cfg["auth"]
        import tools.intake_email as IE
        assert IE._load_config is MAIL._load_config or \
            IE._load_config(_PERSONA)["auth"]["password"] == _PASSWORD
        # A runtime 401 for an app-connected user points at the panel, not a server file.
        assert "Connections panel" in CAL._credential_remedy(_PERSONA)
        assert "Connections panel" in MAIL._credential_remedy(_PERSONA)
        # An empty username in the config is filled from the credentials record.
        text = (_cfg(root) / "email.yaml").read_text().replace(f'"{_ADDRESS}"', '""')
        (_cfg(root) / "email.yaml").write_text(text)
        assert MAIL._load_config(_PERSONA)["auth"]["username"] == _ADDRESS


def test_connected_calendar_reads_with_the_merged_password():
    # The end-to-end proof the merge reaches a real read path: the fake server 401s anything
    # but the app password, and caldav.yaml itself holds none.
    with _sandbox() as root:
        assert CONN.connect_google(_PERSONA, _ADDRESS, _PASSWORD)["ok"]
        assert yaml.safe_load((_cfg(root) / "caldav.yaml").read_text())["auth"]["password"] == ""
        raw = CAL._query_events("2026-10-26", "2026-10-28", persona=_PERSONA)
        assert raw.get("events") == [] and "error" not in raw, raw
        assert raw.get("connected") is not False, raw


# --- standalone ------------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in list(globals().items())        # definition order
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            import traceback
            failed += 1
            print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}\n"
                  + "".join(traceback.format_exc().splitlines(True)[-4:]))
    print(f"\n{len(tests) - failed} passed, {failed} failed, {len(tests)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    os.environ.setdefault("METATRON_AUTH_PASSWORD", "x")
    sys.exit(main())
