"""tests/test_deploy_verdict.py — deploy.sh's post-restart verdict, and the resume DNS check.

Review 2026-11-05 #8: both units are Type=simple, so `systemctl restart` returns 0 the
moment a process forks, and a deploy that left the server or a scheduler crash-looping
still printed "Deploy complete". deploy.sh now ends its remote heredoc with
`deploy_verdict`, which these tests extract from deploy.sh VERBATIM (a copy would keep
passing after the original was edited) and feed failing inputs — plus the one input that
must NOT fail it: an ordinary pipeline Traceback in the journal, which the restart's own
killing of in-flight turns produces on a perfectly good deploy.

Review #48: metatron-resume.sh said "Server is up" while Tailscale DNS (CLAUDE.md
infrastructure trap 7) blocked every outbound call. Run here against a stubbed `gcloud`
on PATH — nothing reaches the VM, nothing is deployed.

Run:  python tests/test_deploy_verdict.py     (or pytest)
"""

import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEPLOY = REPO / "deploy.sh"
RESUME = REPO / "scripts" / "metatron-resume.sh"


# --- #8: the verdict function ------------------------------------------------

def _verdict_source() -> str:
    text = DEPLOY.read_text()
    m = re.search(r"^deploy_verdict\(\) \{\n.*?^\}\n", text, re.S | re.M)
    assert m, "deploy_verdict() not found in deploy.sh — renamed or restructured?"
    return m.group(0)


def _verdict(states: str, base: str, after: str, health: str, journal: str = ""):
    src = _verdict_source() + 'deploy_verdict "$@"\n'
    p = subprocess.run(["bash", "-c", src, "_", states, base, after, health, journal],
                       capture_output=True, text=True)
    return p.returncode, p.stderr


GOOD_STATES = ("metatron-server active\n"
               "metatron-scheduler@mike.service active\n"
               "metatron-scheduler@iva.service active")
GOOD_BASE = ("metatron-scheduler@mike.service 0\n"
             "metatron-scheduler@iva.service 0\n"
             "metatron-server 0")
GOOD_AFTER = ("metatron-server 0\n"
              "metatron-scheduler@mike.service 0\n"
              "metatron-scheduler@iva.service 0")

# What the journal looks like after a good deploy: the drain timed out on a long turn,
# the restart killed it, and it logged a traceback. Nothing is wrong with the new code.
PIPELINE_TRACEBACK = """\
Nov 11 09:00:01 metatron-vm python[1234]: Traceback (most recent call last):
Nov 11 09:00:01 metatron-vm python[1234]:   File "/home/md-homefolder/multi-model-mcp/core/orchestrator.py", line 812, in run_pipeline_session_stream
Nov 11 09:00:01 metatron-vm python[1234]: asyncio.exceptions.CancelledError
Nov 11 09:00:02 metatron-vm systemd[1]: Stopping metatron-server.service - Metatron FastAPI Server...
Nov 11 09:00:09 metatron-vm python[2345]: [warmup] embedding model ready (6.1s)"""

REFUSING = ("Nov 11 09:00:03 metatron-vm python[3456]: [scheduler] REFUSING TO START for iva: "
            "another scheduler holds data/personas/iva/logs/scheduler.lock")


def test_healthy_deploy_passes():
    code, err = _verdict(GOOD_STATES, GOOD_BASE, GOOD_AFTER, "200")
    assert code == 0, err


def test_ordinary_pipeline_traceback_does_not_fail():
    code, err = _verdict(GOOD_STATES, GOOD_BASE, GOOD_AFTER, "200", PIPELINE_TRACEBACK)
    assert code == 0, f"a killed in-flight turn's traceback failed a good deploy:\n{err}"


def test_server_not_active_fails():
    states = GOOD_STATES.replace("metatron-server active", "metatron-server activating")
    code, err = _verdict(states, GOOD_BASE, GOOD_AFTER, "200")
    assert code == 1 and "metatron-server is activating" in err, err


def test_scheduler_failed_fails():
    states = GOOD_STATES.replace("@iva.service active", "@iva.service failed")
    code, err = _verdict(states, GOOD_BASE, GOOD_AFTER, "200")
    assert code == 1 and "iva.service is failed" in err, err


def test_crash_restart_counted_fails_even_when_active():
    # The crash loop caught mid-cycle looking healthy: active, health 200, but systemd
    # has restarted it twice since the deploy did.
    after = GOOD_AFTER.replace("@mike.service 0", "@mike.service 2")
    code, err = _verdict(GOOD_STATES, GOOD_BASE, after, "200")
    assert code == 1 and "restarted it 2 time(s)" in err, err


def test_nrestarts_unreadable_fails():
    after = GOOD_AFTER.replace("metatron-server 0", "metatron-server")
    code, err = _verdict(GOOD_STATES, GOOD_BASE, after, "200")
    assert code == 1 and "unreadable after the settle" in err, err
    code, err = _verdict(GOOD_STATES, "", GOOD_AFTER, "200")
    assert code == 1 and "no NRestarts baseline" in err, err


def test_health_not_200_fails():
    for health, needle in (("000", "000"), ("401", "refused the token"), ("500", "500"), ("", "nothing")):
        code, err = _verdict(GOOD_STATES, GOOD_BASE, GOOD_AFTER, health)
        assert code == 1 and needle in err, (health, err)


def test_refusing_to_start_fails():
    code, err = _verdict(GOOD_STATES, GOOD_BASE, GOOD_AFTER, "200",
                         PIPELINE_TRACEBACK + "\n" + REFUSING)
    assert code == 1 and "REFUSING TO START" in err, err


def test_no_states_fails():
    code, err = _verdict("", GOOD_BASE, GOOD_AFTER, "200")
    assert code == 1 and "no unit states" in err, err


def _remote_body() -> str:
    text = DEPLOY.read_text()
    m = re.search(r"<<'REMOTE'\n(.*?)^REMOTE$", text, re.S | re.M)
    assert m, "remote heredoc not found in deploy.sh"
    return m.group(1)


def test_remote_body_parses_and_orders_the_checks():
    body = _remote_body()
    p = subprocess.run(["bash", "-n"], input=body, capture_output=True, text=True)
    assert p.returncode == 0, p.stderr
    imp = body.index('import core.server, core.scheduler')
    sched = body.index("sudo systemctl restart 'metatron-scheduler@*'")
    server = body.index("sudo systemctl restart metatron-server")
    # Import check aborts with the old processes serving: before either restart.
    assert imp < sched < server
    # Baselines are read AFTER each restart (it resets the counter), not before.
    assert sched < body.index("NRESTARTS_BASE=$(") < server
    assert server < body.index('NRESTARTS_BASE="$NRESTARTS_BASE')
    # Settle outlasts the units' RestartSec=10.
    settle = int(re.search(r"^SETTLE=(\d+)$", body, re.M).group(1))
    assert settle > 10
    # The verdict runs, and a failing one exits non-zero, which aborts the Mac side.
    assert re.search(r'deploy_verdict "\$STATES".*\|\| VERDICT_FAIL=1', body)
    # A generic Traceback grep is explicitly out (review rev. 1 #5).
    assert not re.search(r"grep[^\n]*Traceback", DEPLOY.read_text())


def test_deploy_script_parses():
    p = subprocess.run(["bash", "-n", str(DEPLOY)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


# --- #48: outbound DNS after a resume ----------------------------------------

_GCLOUD_STUB = """#!/bin/bash
echo "$*" >> "$STUB_LOG"
case "$*" in
  *"billing projects describe"*) echo True ;;
  *"instances start"*) echo started ;;
  *getent*)
    case "$DNS_MODE" in
      ok) echo DNS_OK ;;
      fail) echo DNS_FAIL ;;
      *) exit 255 ;;
    esac ;;
  *health*) echo '{"status":"ok"}' ;;
esac
"""


def _resume(dns_mode: str):
    d = Path(tempfile.mkdtemp())
    for name, body in (("gcloud", _GCLOUD_STUB), ("sleep", "#!/bin/bash\nexit 0\n")):
        f = d / name
        f.write_text(body)
        f.chmod(f.stat().st_mode | stat.S_IXUSR)
    log = d / "calls.log"
    env = dict(os.environ, PATH=f"{d}:{os.environ['PATH']}", STUB_LOG=str(log), DNS_MODE=dns_mode)
    p = subprocess.run(["bash", str(RESUME)], capture_output=True, text=True, env=env, timeout=60)
    calls = log.read_text() if log.exists() else ""
    return p.returncode, p.stdout + p.stderr, calls.count("getent")


def test_resume_passes_when_dns_resolves():
    code, out, n = _resume("ok")
    assert code == 0 and "Outbound DNS ok" in out and n == 1, out


def test_resume_fails_with_trap7_fix_when_dns_broken():
    code, out, n = _resume("fail")
    assert code == 1, out
    assert "sudo tailscale set --accept-dns=false" in out and "sudo tailscale status" in out, out
    assert n == 3, f"expected 3 attempts before prescribing a config change, got {n}"


def test_resume_unreachable_is_unverified_not_misdiagnosed():
    code, out, n = _resume("unreachable")
    assert code == 1 and "unverified" in out, out
    assert "accept-dns" not in out, "an SSH failure was diagnosed as broken DNS"


def test_resume_script_parses():
    p = subprocess.run(["bash", "-n", str(RESUME)], capture_output=True, text=True)
    assert p.returncode == 0, p.stderr


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {exc}")
    print()
    print(f"{len(failures)} failed" if failures else "all passed")
    sys.exit(1 if failures else 0)
