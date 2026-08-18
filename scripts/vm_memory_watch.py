#!/usr/bin/env python3
"""
scripts/vm_memory_watch.py — alert when the VM is close to an OOM kill, or has had one.

WHY THIS EXISTS
On 2026-08-15 15:02 the kernel OOM-killed metatron-server.service (3.6 GB RSS on a
3.9 GB machine with no swap). systemd restarted it five seconds later, so from the
outside it looked like nothing happened — the only record was in `dmesg`, which
nobody reads. Two more kills sit in the same log. An outage that leaves no trace
anyone sees is an outage that recurs.

WHAT IT ALERTS ON
  1. A NEW OOM kill since the last run — always critical, always reported.
  2. Available memory below THRESHOLD_WARN_MB — the leading indicator.
  3. Swap absent — a standing condition, reported once per boot, because with no
     swap the kernel has no soft failure mode available to it at all.

WHERE THE ALERT GOES, and why more than one place: the case being detected is
"the server may be dying", so a channel that depends on the server is exactly the
channel that fails when it matters.
  - stdout/stderr → journald (survives anything; `journalctl -u metatron-memory-watch`)
  - data/system/memory_alerts.jsonl → durable, greppable, survives a restart
  - the server's push endpoint → best-effort only, skipped silently if unreachable

Run it from a systemd timer. Install both units with --install-units.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = ROOT / "data" / "system" / "memory_watch_state.json"
ALERT_LOG = ROOT / "data" / "system" / "memory_alerts.jsonl"

THRESHOLD_WARN_MB = 500     # below this, a Chromium render or a Whisper spike is a coin flip
SERVER_URL = "http://127.0.0.1:8001"


def _meminfo() -> dict[str, int]:
    """MemTotal/MemAvailable/SwapTotal in MB."""
    out: dict[str, int] = {}
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                if key in ("MemTotal", "MemAvailable", "SwapTotal"):
                    out[key] = int(rest.split()[0]) // 1024
    except (OSError, ValueError, IndexError):
        pass
    return out


def _oom_kill_count() -> int:
    """
    Number of OOM kills the kernel has logged this boot.

    Uses `journalctl -k` rather than `dmesg` because dmesg needs root on this image
    and the timer should not have to run privileged just to count lines.
    """
    for cmd in (["journalctl", "-k", "-b", "--no-pager"], ["dmesg"]):
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError):
            continue
        if res.returncode == 0:
            return len(re.findall(r"Out of memory: Killed process", res.stdout))
    return 0


def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text())
    except (OSError, ValueError):
        return {}


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATE_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2))
    tmp.replace(STATE_PATH)


def _boot_id() -> str:
    try:
        return Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        return "unknown"


def _emit(level: str, message: str, detail: dict) -> None:
    """Write the alert everywhere it can go. Never raises."""
    event = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "level": level,
        "message": message,
        **detail,
    }
    print(f"[{level}] {message} :: {json.dumps(detail)}", file=sys.stderr)
    try:
        ALERT_LOG.parent.mkdir(parents=True, exist_ok=True)
        with ALERT_LOG.open("a") as fh:
            fh.write(json.dumps(event) + "\n")
    except OSError:
        pass
    if level == "critical":
        try:
            req = urllib.request.Request(
                f"{SERVER_URL}/push",
                data=json.dumps({"message": message}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5).read()
        except (urllib.error.URLError, OSError, ValueError):
            pass  # server down is the expected case here, not an error


def check() -> int:
    mem = _meminfo()
    if not mem:
        print("cannot read /proc/meminfo — not a Linux host?", file=sys.stderr)
        return 0

    state = _load_state()
    boot = _boot_id()
    same_boot = state.get("boot_id") == boot
    kills = _oom_kill_count()
    prev_kills = state.get("oom_kills", 0) if same_boot else 0

    total = mem.get("MemTotal", 0)
    avail = mem.get("MemAvailable", 0)
    swap = mem.get("SwapTotal", 0)
    detail = {"available_mb": avail, "total_mb": total, "swap_mb": swap, "oom_kills": kills}
    alerted = False

    if kills > prev_kills:
        _emit("critical",
              f"OOM kill on the VM: {kills - prev_kills} new (the kernel killed a process "
              f"outright; check `journalctl -k | grep -i 'out of memory'`)", detail)
        alerted = True

    if avail < THRESHOLD_WARN_MB:
        _emit("warning",
              f"VM memory low: {avail}MB available of {total}MB", detail)
        alerted = True

    if swap == 0 and not state.get("warned_no_swap_boot") == boot:
        _emit("warning",
              "VM has no swap configured — the kernel has no soft failure mode; "
              "run scripts/vm_add_swap.sh", detail)
        state["warned_no_swap_boot"] = boot
        alerted = True

    state.update({"boot_id": boot, "oom_kills": kills, "last_check": datetime.now(timezone.utc).isoformat(),
                  "last_available_mb": avail})
    _save_state(state)

    if not alerted:
        print(f"ok: {avail}MB available of {total}MB, swap {swap}MB, {kills} OOM kills this boot")
    return 0


UNIT_SERVICE = """[Unit]
Description=Metatron VM memory watchdog

[Service]
Type=oneshot
WorkingDirectory={root}
# Runs as the repo owner, not root: the only privileged thing here is installing
# the units. /proc/meminfo and `journalctl -k` are both readable unprivileged
# (verified on the VM 2026-08-18), and running as root would leave root-owned
# files in data/system/ that the server (uid 1000) could not later write.
User={user}
Group={user}
ExecStart={python} {script}
"""

UNIT_TIMER = """[Unit]
Description=Run the Metatron memory watchdog every 5 minutes

[Timer]
OnBootSec=2min
OnUnitActiveSec=5min
Unit=metatron-memory-watch.service

[Install]
WantedBy=timers.target
"""


def install_units() -> int:
    svc = Path("/etc/systemd/system/metatron-memory-watch.service")
    tmr = Path("/etc/systemd/system/metatron-memory-watch.timer")
    if os.geteuid() != 0:
        print("--install-units must run as root (sudo)", file=sys.stderr)
        return 1
    # SUDO_USER is the human who ran `sudo`, which is the repo owner; falling back
    # to the directory's owner keeps this correct if it is ever run some other way.
    owner = os.environ.get("SUDO_USER") or ROOT.owner()
    svc.write_text(UNIT_SERVICE.format(root=ROOT, python=sys.executable,
                                       script=Path(__file__).resolve(), user=owner))
    tmr.write_text(UNIT_TIMER)
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "--now", "metatron-memory-watch.timer"], check=False)
    print("installed and started metatron-memory-watch.timer (every 5 min)")
    print("  logs:  journalctl -u metatron-memory-watch -f")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--install-units", action="store_true", help="install+enable the systemd timer (run on the VM as root)")
    args = ap.parse_args()
    sys.exit(install_units() if args.install_units else check())
