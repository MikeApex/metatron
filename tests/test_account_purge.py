#!/usr/bin/env python3
"""
tests/test_account_purge.py — deleting an account needs a person at a terminal.

WHY THIS EXISTS. Mike, 2026-10-29: "there must be a human approval before an account's
information is deleted." `scripts/accounts.py purge` is the only deletion of a user's data, and
its gates are what these checks pin: the account must already be disabled, the command must run
at a real terminal (a pipe or Claude Code's shell is refused), and the username must be typed
back. When it does run, it removes everything the account owned and nothing anyone else owns.

The script runs as its own process inside a throwaway copy of the files it needs, as in
tests/test_multi_user_isolation.py; a pseudo-terminal stands in for the person. systemctl is
stubbed (METATRON_SYSTEMCTL=true). No live meter is reached.

Run:
    python -m pytest -q tests/test_account_purge.py
    python tests/test_account_purge.py
"""

import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from core import accounts  # noqa: E402

TMP = Path(tempfile.mkdtemp(prefix="purge_test_"))
CONSENT = {"scope": "base_configuration", "text_version": "v1"}


def _sandbox() -> Path:
    """A repo copy with one approved-then-disabled account, `zz_gone`, and a bystander's data
    beside it in every shared store — `mike` in push, `zz_stays` in the conversation DB."""
    box = Path(tempfile.mkdtemp(dir=TMP))
    for rel in ("core/accounts.py", "core/consent.py", "core/persona.py", "core/push.py",
                "scripts/accounts.py", "scripts/new_persona.sh"):
        (box / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / rel, box / rel)
    shutil.copytree(ROOT / "config" / "templates", box / "config" / "templates")
    store = box / "data" / "accounts" / "accounts.json"
    accounts.register("zz_gone", "Gone", "gone-password-123", "Europe/London", CONSENT,
                      path=store)
    assert _run(box, "approve", "zz_gone").returncode == 0
    data = box / "data"
    (data / "push_subscriptions.json").write_text(json.dumps([
        {"endpoint": "https://push.example/gone", "keys": {}, "persona": "zz_gone"},
        {"endpoint": "https://push.example/mike", "keys": {}, "persona": "mike"}]))
    (data / "fcm_tokens.json").write_text(json.dumps([
        {"token": "t-gone", "persona": "zz_gone"}, {"token": "t-mike", "persona": "mike"}]))
    (data / "push_outbox.json").write_text(json.dumps({
        "m1": {"persona": "zz_gone", "title": "x", "created": 0},
        "m2": {"persona": "mike", "title": "y", "created": 0}}))
    db = data / "conversations" / "metatron.db"
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as c:
        c.execute("CREATE TABLE exchanges (exchange_id TEXT, persona TEXT, user TEXT)")
        c.execute("CREATE TABLE attachments (id TEXT, persona TEXT)")
        c.executemany("INSERT INTO exchanges VALUES (?, ?, ?)",
                      [("e1", "zz_gone", "hi"), ("e2", "zz_gone", "hey"), ("e3", "zz_stays", "yo")])
        c.execute("INSERT INTO attachments VALUES ('a1', 'zz_gone')")
    return box


def _env() -> dict:
    return dict(os.environ, METATRON_SYSTEMCTL="true")


def _run(box: Path, *args) -> subprocess.CompletedProcess:
    """No terminal — how Claude Code, a scheduler or a pipe runs it."""
    return subprocess.run([sys.executable, str(box / "scripts" / "accounts.py"), *args],
                          capture_output=True, text=True, env=_env(), cwd=box,
                          stdin=subprocess.DEVNULL)


def _run_at_terminal(box: Path, *args, typed: str) -> tuple[int, str]:
    """A pseudo-terminal on stdin and stdout, with `typed` entered at the prompt."""
    master, slave = os.openpty()
    p = subprocess.Popen([sys.executable, str(box / "scripts" / "accounts.py"), *args],
                         stdin=slave, stdout=slave, stderr=slave, env=_env(), cwd=box)
    os.close(slave)
    os.write(master, (typed + "\n").encode())
    out = b""
    while True:
        try:
            chunk = os.read(master, 4096)
        except OSError:
            break
        if not chunk:
            break
        out += chunk
    os.close(master)
    return p.wait(timeout=60), out.decode(errors="replace")


def _store(box: Path) -> dict:
    return json.loads((box / "data/accounts/accounts.json").read_text())["accounts"]


def _rows(box: Path, persona: str) -> int:
    with sqlite3.connect(box / "data/conversations/metatron.db") as c:
        return sum(c.execute(f"SELECT COUNT(*) FROM {t} WHERE persona = ?", (persona,)).fetchone()[0]
                   for t in ("exchanges", "attachments"))


def _untouched(box: Path) -> bool:
    return ((box / "data/personas/zz_gone").is_dir() and (box / "config/personas/zz_gone.md").exists()
            and "zz_gone" in _store(box) and _rows(box, "zz_gone") == 3)


def test_an_active_account_is_refused():
    box = _sandbox()
    code, out = _run_at_terminal(box, "purge", "zz_gone", "--no-scheduler", typed="zz_gone")
    assert code == 1 and "disable" in out, out
    assert _untouched(box)


def test_no_terminal_is_refused_even_with_the_name_piped_in():
    box = _sandbox()
    assert _run(box, "disable", "zz_gone").returncode == 0
    r = subprocess.run([sys.executable, str(box / "scripts/accounts.py"), "purge", "zz_gone",
                        "--no-scheduler"], input="zz_gone\n", capture_output=True, text=True,
                       env=_env(), cwd=box)
    assert r.returncode == 1 and "terminal" in r.stderr, r.stderr
    assert _untouched(box)


def test_the_wrong_name_typed_stops_it():
    box = _sandbox()
    assert _run(box, "disable", "zz_gone").returncode == 0
    code, out = _run_at_terminal(box, "purge", "zz_gone", "--no-scheduler", typed="yes")
    assert code == 1 and "Nothing was deleted" in out, out
    assert _untouched(box)


def test_reserved_names_and_non_accounts_are_refused():
    box = _sandbox()
    for name in ("mike", "admin", "danny_park"):
        code, out = _run_at_terminal(box, "purge", name, "--no-scheduler", typed=name)
        assert code == 1, (name, out)


def test_a_confirmed_purge_removes_everything_hers_and_nothing_else():
    box = _sandbox()
    assert _run(box, "disable", "zz_gone").returncode == 0
    code, out = _run_at_terminal(box, "purge", "zz_gone", typed="zz_gone")
    assert code == 0 and "zz_gone purged." in out, out
    assert not (box / "data/personas/zz_gone").exists()
    assert not (box / "config/personas/zz_gone").exists()
    assert not (box / "config/personas/zz_gone.md").exists()
    assert "zz_gone" not in _store(box)
    assert _rows(box, "zz_gone") == 0 and _rows(box, "zz_stays") == 1
    data = box / "data"
    assert [s["persona"] for s in json.loads((data / "push_subscriptions.json").read_text())] == ["mike"]
    assert [t["persona"] for t in json.loads((data / "fcm_tokens.json").read_text())] == ["mike"]
    assert list(json.loads((data / "push_outbox.json").read_text())) == ["m2"]
    log = [json.loads(l) for l in (data / "accounts/purge_log.jsonl").read_text().splitlines()]
    assert [e["username"] for e in log] == ["zz_gone"] and log[0]["conversation_rows"] == 3
    # Nothing left to purge, and saying so is not an error that leaves state behind.
    code, _ = _run_at_terminal(box, "purge", "zz_gone", "--no-scheduler", typed="zz_gone")
    assert code == 1


def test_the_store_removes_only_a_disabled_entry():
    store = TMP / "store_only" / "accounts.json"
    accounts.register("zz_live", "Live", "live-password-123", "Europe/London", CONSENT, path=store)
    try:
        accounts.remove("zz_live", path=store)
        raise AssertionError("removed a pending account")
    except accounts.AccountError:
        pass
    accounts.update("zz_live", status="disabled", path=store)
    assert accounts.remove("zz_live", path=store) is True
    assert accounts.remove("zz_live", path=store) is False


if __name__ == "__main__":
    failures = []
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc!r}")
    print(f"\n{len(failures)} failed" if failures else "\nall passed")
    sys.exit(1 if failures else 0)
