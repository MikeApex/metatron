"""
tests/test_memory_watch_and_session_line.py — plan multi_user_accounts_plan_2026-10-26.md
§ 6.1 item 16 (Stage 1.14, D10 a) and the session-start half of Stage 1.9.

The VM's memory trouble was recorded and nobody was told (§ 3.12): the watchdog wrote a file
nothing read, and its one alert posted to a route that does not exist. Three things are
asserted here, every /proc read and every HTTP call stubbed — no network, no VM:

1. A watchdog run records the server's and each scheduler's resident memory, schedulers
   with their persona, and attempts no push.
2. The session-start line shows a new OOM kill and a new low-memory day ONCE, and nothing
   on the next run — and a first run against an existing log reports nothing.
3. The line carries "N account(s) awaiting approval" when sign-ups are pending, and nothing
   at zero or when the route fails.

Plus the constraint that makes (2) and (3) safe to ship: sync_dev_backlog.py still parses
and imports under the macOS system python3 (3.9), which is what the SessionStart hook
often gets.

Run: .venv/bin/python -m pytest -q tests/test_memory_watch_and_session_line.py
"""

import io
import json
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sync_dev_backlog as sync                           # noqa: E402
import vm_memory_watch as vmw                             # noqa: E402

SERVER = "https://vm.test:8001"


# ── 1. The watchdog ──────────────────────────────────────────────────────────

def _proc(root: Path, pid: int, argv: list, rss_kb=None) -> None:
    d = root / str(pid)
    d.mkdir()
    (d / "cmdline").write_bytes(b"".join(a.encode() + b"\0" for a in argv))
    status = "Name:\tpython\n"
    if rss_kb is not None:
        status += f"VmRSS:\t {rss_kb} kB\n"
    (d / "status").write_text(status)


@pytest.fixture
def watchdog(tmp_path, monkeypatch):
    proc = tmp_path / "proc"
    proc.mkdir()
    venv = "/home/u/multi-model-mcp/.venv/bin/python"
    _proc(proc, 101, [venv, "core/server.py", "--persona", "mike", "--port", "8001"], 2_097_152)
    _proc(proc, 202, [venv, "core/scheduler.py", "--persona", "mike"], 71_680)
    _proc(proc, 203, [venv, "core/scheduler.py", "--persona=iva"], 65_536)
    _proc(proc, 303, [venv, "/home/u/multi-model-mcp/core/tts_worker.py"], 1_048_576)
    # Must NOT be recorded: a grep naming the server, the watchdog itself, a kernel thread
    # (empty cmdline), and a zombie (no VmRSS line).
    _proc(proc, 404, ["grep", "core/server.py"], 1_024)
    _proc(proc, 505, [venv, "scripts/vm_memory_watch.py"], 20_480)
    _proc(proc, 606, [], None)
    _proc(proc, 707, [venv, "core/scheduler.py", "--persona", "ghost"], None)
    (proc / "self").mkdir()           # non-numeric entries are skipped

    monkeypatch.setattr(vmw, "PROC_ROOT", proc)
    monkeypatch.setattr(vmw, "STATE_PATH", tmp_path / "memory_watch_state.json")
    monkeypatch.setattr(vmw, "ALERT_LOG", tmp_path / "memory_alerts.jsonl")
    monkeypatch.setattr(vmw, "SAMPLE_LOG", tmp_path / "memory_samples.jsonl")
    monkeypatch.setattr(vmw, "_meminfo",
                        lambda: {"MemTotal": 3900, "MemAvailable": 420, "SwapTotal": 2048})
    monkeypatch.setattr(vmw, "_oom_kill_count", lambda: 1)
    monkeypatch.setattr(vmw, "_boot_id", lambda: "boot-1")

    def _no_network(*a, **k):
        raise AssertionError("the watchdog attempted a network call")
    monkeypatch.setattr(urllib.request, "urlopen", _no_network)
    return tmp_path


def test_watchdog_records_server_and_scheduler_rss_with_personas(watchdog):
    assert vmw.check() == 0

    lines = (watchdog / "memory_samples.jsonl").read_text().splitlines()
    assert len(lines) == 1, "one compact line per run"
    sample = json.loads(lines[0])
    assert sample["available_mb"] == 420
    assert sample["procs"] == [
        {"role": "scheduler", "pid": 203, "rss_mb": 64, "persona": "iva"},
        {"role": "scheduler", "pid": 202, "rss_mb": 70, "persona": "mike"},
        {"role": "server", "pid": 101, "rss_mb": 2048},
        {"role": "tts_worker", "pid": 303, "rss_mb": 1024},
    ]

    vmw.check()
    assert len((watchdog / "memory_samples.jsonl").read_text().splitlines()) == 2


def test_watchdog_alerts_carry_a_kind_and_no_push_is_attempted(watchdog):
    # The fixture's urlopen raises; a surviving push call would fail this run.
    vmw.check()
    alerts = [json.loads(ln) for ln in (watchdog / "memory_alerts.jsonl").read_text().splitlines()]
    assert [a["kind"] for a in alerts] == ["oom_kill", "low_memory"]
    assert alerts[0]["level"] == "critical"

    source = Path(vmw.__file__).read_text()
    assert "urlopen" not in source and "import urllib" not in source
    assert not hasattr(vmw, "SERVER_URL")


def test_script_role_only_counts_the_interpreters_script():
    py = "/x/.venv/bin/python3.11"
    assert vmw._script_role([py, "-u", "core/server.py"]) == "server"
    assert vmw._script_role([py, "-m", "core.tts_worker"]) == "tts_worker"
    assert vmw._script_role([py, "scripts/other.py", "core/server.py"]) is None
    assert vmw._script_role(["journalctl", "core/scheduler.py"]) is None
    assert vmw._script_role([py, "-m", "core.orchestrator"]) is None


# ── 2 and 3. The session-start line ──────────────────────────────────────────

BACKLOG_TEXT = """# DEV_BACKLOG

## Inbox

---

## Now

## Later

## Machine log

---
"""


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeVM:
    """Answers /monitor/file and /monitor/accounts from in-memory state."""

    def __init__(self):
        self.memory_log: list = []
        self.accounts = []
        self.accounts_error = None
        self.down = False
        self.calls: list = []

    def urlopen(self, req, timeout=None):
        url = urllib.parse.urlparse(req.full_url)
        self.calls.append(url.path)
        assert timeout == sync.TIMEOUT_SECONDS
        if self.down:
            raise urllib.error.URLError("unreachable")
        if url.path == "/monitor/accounts":
            if self.accounts_error:
                raise self.accounts_error
            return _Resp(json.dumps({"accounts": self.accounts}).encode())
        if url.path == "/monitor/file":
            path = urllib.parse.parse_qs(url.query)["path"][0]
            if path == "data/system/memory_alerts.jsonl":
                body = "".join(json.dumps(r) + "\n" for r in self.memory_log)
                return _Resp(json.dumps({"path": path, "content": body}).encode())
            raise urllib.error.HTTPError(req.full_url, 404, "not found", {}, None)
        raise AssertionError(f"unexpected route {url.path}")


@pytest.fixture
def vm(tmp_path, monkeypatch):
    backlog = tmp_path / "DEV_BACKLOG.md"
    backlog.write_text(BACKLOG_TEXT)
    monkeypatch.setattr(sync, "BACKLOG", backlog)
    monkeypatch.setattr(sync, "SEEN", tmp_path / ".dev_backlog_seen")
    monkeypatch.setattr(sync, "INBOX_FRAGMENTS", tmp_path / "no_fragments")
    monkeypatch.setattr(sync, "MEMORY_CURSOR", tmp_path / ".claude" / "dev_backlog_memory_cursor.json")
    monkeypatch.setattr(sync, "_UNREACHABLE", False)
    monkeypatch.setattr(sync, "_auth_header", lambda: {})
    monkeypatch.setattr(sync, "vm_status", lambda: "")
    fake = FakeVM()
    monkeypatch.setattr(urllib.request, "urlopen", fake.urlopen)
    fake.tmp = tmp_path
    return fake


def _line(monkeypatch, capsys, *extra) -> str:
    monkeypatch.setattr(sync, "_UNREACHABLE", False)   # a fresh process each session start
    monkeypatch.setattr(sys, "argv", ["sync_dev_backlog.py", "--server", SERVER, *extra])
    assert sync.main() == 0
    return capsys.readouterr().out.strip()


def _old(ts, message):
    """A record in the shape written before 2026-10-27 — no `kind`."""
    return {"ts": ts, "level": "warning" if message.startswith("VM") else "critical",
            "message": message, "available_mb": 300, "oom_kills": 1}


def _new(ts, kind, level="warning"):
    return {"ts": ts, "level": level, "kind": kind, "message": "…", "available_mb": 300}


def test_memory_clause_shows_new_oom_and_low_day_once(vm, monkeypatch, capsys):
    vm.memory_log = [
        _old("2026-10-22T04:10:00.000000+00:00", "OOM kill on the VM: 1 new (…)"),
        _old("2026-10-26T20:00:00.000000+00:00", "VM memory low: 180MB available of 3900MB"),
        _old("2026-10-27T08:00:00.000000+00:00", "VM memory low: 240MB available of 3900MB"),
    ]

    # First run: history is not dumped; the cursor starts at the log's end.
    first = _line(monkeypatch, capsys)
    assert first.startswith("DEV_BACKLOG.md: 0 new")
    assert "memory" not in first
    cursor = json.loads(sync.MEMORY_CURSOR.read_text())
    assert cursor == {"cursor": "2026-10-27T08:00:00+00:00", "low_days": []}

    vm.memory_log += [
        _new("2026-10-28T03:00:00.000000+00:00", "oom_kill", "critical"),
        _new("2026-10-28T03:05:00.000000+00:00", "low_memory"),
        _new("2026-10-28T09:00:00.000000+00:00", "low_memory"),
        _new("2026-10-29T01:00:00.000000+00:00", "low_memory"),
        _new("2026-10-29T02:00:00.000000+00:00", "no_swap"),     # a warning, not a low reading
    ]
    second = _line(monkeypatch, capsys)
    assert second.endswith(" · ⚠ memory: OOM kill 2026-10-28; 2 low-memory days")

    # Same log, next session: nothing.
    assert "memory" not in _line(monkeypatch, capsys)

    # More readings on a day already shown stay silent; a new day is shown once.
    vm.memory_log.append(_new("2026-10-29T13:00:00.000000+00:00", "low_memory"))
    assert "memory" not in _line(monkeypatch, capsys)
    vm.memory_log.append(_new("2026-10-30T13:00:00.000000+00:00", "low_memory"))
    assert _line(monkeypatch, capsys).endswith(" · ⚠ memory: 1 low-memory day")
    assert "memory" not in _line(monkeypatch, capsys)


def test_memory_clause_prints_even_under_quiet(vm, monkeypatch, capsys):
    vm.memory_log = [_new("2026-10-27T08:00:00.000000+00:00", "low_memory")]
    assert _line(monkeypatch, capsys, "--quiet") == ""          # first run: nothing new
    vm.memory_log.append(_new("2026-10-28T08:00:00.000000+00:00", "oom_kill", "critical"))
    assert "⚠ memory: OOM kill 2026-10-28" in _line(monkeypatch, capsys, "--quiet")


def test_unreachable_vm_leaves_no_cursor_and_stops_after_one_request(vm, monkeypatch, capsys):
    vm.down = True
    line = _line(monkeypatch, capsys)
    assert "memory" not in line and "awaiting" not in line
    assert not sync.MEMORY_CURSOR.exists(), "a cursor set blind would swallow the backlog"
    assert len(vm.calls) == 1, "one timeout per session start, not one per clause"


def test_accounts_clause_counts_pending_only(vm, monkeypatch, capsys):
    row = {"display_name": "x", "created_at": "2026-10-27", "decided_at": None, "decided_by": None}
    vm.accounts = [dict(row, username="iva", status="pending"),
                   dict(row, username="trial_2026_10", status="pending"),
                   dict(row, username="mike", status="active"),
                   dict(row, username="old", status="rejected")]
    assert " · 2 accounts awaiting approval" in _line(monkeypatch, capsys)

    vm.accounts = vm.accounts[1:]
    assert " · 1 account awaiting approval" in _line(monkeypatch, capsys)

    vm.accounts = [dict(row, username="mike", status="active")]
    line = _line(monkeypatch, capsys)
    assert line.startswith("DEV_BACKLOG.md:") and "awaiting" not in line


def test_accounts_clause_absent_on_http_error(vm, monkeypatch, capsys):
    vm.accounts = [{"username": "iva", "status": "pending"}]
    vm.accounts_error = urllib.error.HTTPError(SERVER, 403, "forbidden", {}, None)
    line = _line(monkeypatch, capsys)
    assert line.startswith("DEV_BACKLOG.md:") and "awaiting" not in line

    vm.accounts_error = ValueError("garbled reply")
    line = _line(monkeypatch, capsys)
    assert line.startswith("DEV_BACKLOG.md:") and "awaiting" not in line


# ── The 3.9 constraint ───────────────────────────────────────────────────────

SYSTEM_PY = Path("/usr/bin/python3")


@pytest.mark.skipif(not SYSTEM_PY.exists(), reason="no system python3 on this machine")
def test_sync_script_parses_and_imports_under_system_python():
    script = ROOT / "scripts" / "sync_dev_backlog.py"
    parse = subprocess.run(
        [str(SYSTEM_PY), "-c",
         "import ast,sys; ast.parse(open(sys.argv[1]).read(), feature_version=(3,9))", str(script)],
        capture_output=True, text=True, timeout=30)
    assert parse.returncode == 0, parse.stderr

    # --help exits inside argparse, before any request is made.
    helped = subprocess.run([str(SYSTEM_PY), str(script), "--help"],
                            capture_output=True, text=True, timeout=30, cwd=str(ROOT))
    assert helped.returncode == 0, helped.stderr
    assert "--persona" in helped.stdout

    # Importing defines every function, so a 3.10-only annotation evaluated at def time
    # would fail here rather than silently killing the session-start line.
    imported = subprocess.run(
        [str(SYSTEM_PY), "-c",
         "import sys; sys.path.insert(0, sys.argv[1]); import sync_dev_backlog as s; "
         "print(s.memory_clause(['2026-10-28'], ['2026-10-28']))", str(ROOT / "scripts")],
        capture_output=True, text=True, timeout=30)
    assert imported.returncode == 0, imported.stderr
    assert imported.stdout.strip() == "· ⚠ memory: OOM kill 2026-10-28; 1 low-memory day"
