"""
tests/test_scheduler_multi_user.py — the scheduler's Stage 3 changes for a second user
(archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.6, § 6.1.7).

1. The interview hold (D2, review L6): session jobs hold while the state file says
   not_started or active; never for paused/complete; never with no file (an empty
   goals.yaml included); never for function jobs; one-off reminders (no "agent" key)
   are held like any session job.
2. Push reaches only the persona the job belongs to, and a push failure is logged in
   that persona's tree.
3. Single-agent jobs run on the server through /internal/session — never in-process.
4. One scheduler per persona: a second instance exits on the lock (real processes);
   an instance beside a lock-less `--persona <p>` process exits on the /proc scan
   (a fake /proc tree — the Mac has none; the VM run is Stage 4 step 3).

Every live meter is stubbed: send_one, run_internal_session and send_push never reach
a server. Personas live in a temp tree (core.persona._ROOT), never the real one.

Run: python3 tests/test_scheduler_multi_user.py
"""

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import time
from pathlib import Path
from unittest import mock

REPO = Path(__file__).parent.parent
sys.path.insert(0, str(REPO))

import core.persona  # noqa: E402
from core import scheduler  # noqa: E402

_results: list[tuple[bool, str]] = []


def check(label: str, condition: bool) -> None:
    _results.append((condition, label))
    print(f"  {'PASS' if condition else 'FAIL'}  {label}")


CFG = {"schedules": {}}   # no quiet hours configured → the quiet-hours gate never fires
SESSION_JOB = {"enabled": True, "time": "07:30", "days": "daily", "agent": "coordinator",
               "respect_quiet_hours": False}
ONE_OFF = {"at": "2026-10-28T09:00", "prompt": "remind me", "respect_quiet_hours": False}
FUNCTION_JOB = {"enabled": True, "time": "05:30", "days": "daily",
                "function": "tools.x.y", "respect_quiet_hours": False}


def _set_interview(persona: str, status: str | None) -> None:
    path = core.persona.persona_data_dir(persona) / "interview" / "state.json"
    if status is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"status": status}))


def _blocked(job_cfg: dict, persona: str) -> str | None:
    with mock.patch.object(scheduler, "_activity_gate_blocks", return_value=None):
        return scheduler._gates_block("job", job_cfg, CFG, persona)


def part_hold() -> None:
    print("Interview hold — D2, review L6")
    p = "zz_hold"
    for status, held in (("not_started", True), ("active", True),
                         ("paused", False), ("complete", False)):
        _set_interview(p, status)
        check(f"session job {'held' if held else 'fires'} when the interview is {status}",
              (_blocked(SESSION_JOB, p) == "holding for the first interview") is held)
    _set_interview(p, "active")
    check("a one-off reminder (no 'agent' key) is held too",
          _blocked(ONE_OFF, p) == "holding for the first interview")
    check("a function job is never held", _blocked(FUNCTION_JOB, p) is None)

    _set_interview(p, None)
    goals = core.persona.persona_config_dir(p) / "goals.yaml"
    goals.parent.mkdir(parents=True, exist_ok=True)
    goals.write_text("short_term: []\nmedium_term: []\nlong_term: []\n")
    check("no state file never holds — even with an empty goals.yaml",
          _blocked(SESSION_JOB, p) is None)

    # Through fire_session end to end: a held job reaches no server and records no fire.
    _set_interview(p, "not_started")
    sent, rec = [], []
    with mock.patch.object(scheduler, "_load_config", return_value=CFG), \
         mock.patch.object(scheduler, "_activity_gate_blocks", return_value=None), \
         mock.patch.object(scheduler, "_record_fire", side_effect=lambda *a: rec.append(a)), \
         mock.patch("core.remote_client.send_one", side_effect=lambda *a, **k: sent.append(a)):
        scheduler.fire_session("morning_brief", "coordinator", "p", "push", p,
                               job_cfg=SESSION_JOB)
    check("a held brief reaches no server and is not recorded as a fire", not sent and not rec)
    _set_interview(p, None)


def part_push() -> None:
    print("Push per persona, and errors in the right tree")
    calls = []
    with mock.patch("core.push.send_push",
                    side_effect=lambda **k: calls.append(k) or {"sent": 1}):
        scheduler._dispatch("push", "Morning Brief", "body", "zz_iva")
    check("send_push is told whose devices", calls and calls[0].get("persona") == "zz_iva")

    def boom(**k):
        raise RuntimeError("no VAPID key")
    with mock.patch("core.push.send_push", side_effect=boom):
        scheduler._dispatch("push", "T", "b", "zz_iva")
    err_iva = core.persona.persona_data_dir("zz_iva") / "logs" / "scheduler_errors.json"
    err_mike = core.persona.persona_data_dir("mike") / "logs" / "scheduler_errors.json"
    logged = err_iva.exists() and "no VAPID key" in err_iva.read_text()
    check("a push failure is logged in that persona's tree, not another's",
          logged and not err_mike.exists())


def part_review_fixes() -> None:
    print("Stage 3 review fixes — S1, L1, L4")
    p = "zz_held"
    import yaml

    # S1: a function job's push waits too — the hold is at _dispatch, not only the gate.
    _set_interview(p, "active")
    calls = []
    with mock.patch("core.push.send_push",
                    side_effect=lambda **k: calls.append(k) or {"sent": 1}), \
         mock.patch.object(scheduler, "_notify_terminal") as term:
        scheduler._dispatch("both", "Travel Check", "Your 08:12 is cancelled", p)
        held = not calls and not term.called
        _set_interview(p, "paused")
        scheduler._dispatch("push", "Travel Check", "Your 08:12 is cancelled", p)
    check("a function job's push is held during the interview (no push, no terminal)", held)
    check("…and delivered once the interview is paused", len(calls) == 1)

    # S1: nudge_tick returns before opening a conversation or marking anything handled.
    from tools import day_plan
    _set_interview(p, "not_started")
    with core.persona.persona_scope(p), \
         mock.patch.object(day_plan, "_flag", return_value=True), \
         mock.patch.object(day_plan, "_quiet_now", return_value=False), \
         mock.patch("core.remote_client.send_one",
                    side_effect=AssertionError("opened a conversation")) as so:
        out = day_plan.nudge_tick()
    check("nudge_tick holds for the first interview and opens no conversation",
          out == "nudges: holding for the first interview" and not so.called)

    # L1: a one-off due while held stays in the file, then fires once the hold lifts.
    sched = scheduler._agent_schedules_path(p)
    sched.parent.mkdir(parents=True, exist_ok=True)
    sched.write_text(yaml.dump({"call_mum": {"one_off": True, "at": "2026-01-01T09:00",
                                             "prompt": "Remind me to call Mum"}}))
    fired = []
    with mock.patch.object(scheduler, "fire_session",
                           side_effect=lambda *a, **k: fired.append(a[0])):
        _set_interview(p, "active")
        scheduler._fire_due_one_offs(p)
        kept = "call_mum" in (yaml.safe_load(sched.read_text()) or {})
        fired_while_held = list(fired)
        _set_interview(p, "paused")
        scheduler._fire_due_one_offs(p)
    check("a reminder due during the interview is kept, not deleted unseen",
          kept and fired_while_held == [])
    check("…and fires (and is removed) once the hold lifts",
          fired == ["call_mum"] and "call_mum" not in (yaml.safe_load(sched.read_text()) or {}))
    _set_interview(p, None)

    # L4: a typo'd instance name refuses before creating anything.
    with mock.patch.object(sys, "argv", ["core/scheduler.py", "--persona", "zz_typo"]):
        try:
            scheduler.main()
            refused = False
        except SystemExit as e:
            refused = e.code == 1
    check("a scheduler for a persona with no identity file exits 1",
          refused and not core.persona.persona_data_dir("zz_typo").exists())


def part_internal_session() -> None:
    print("Single-agent jobs run on the server")
    p = "zz_iva"
    got, dispatched = [], []
    with mock.patch.object(scheduler, "_load_config", return_value=CFG), \
         mock.patch.object(scheduler, "_activity_gate_blocks", return_value=None), \
         mock.patch.object(scheduler, "_record_fire"), \
         mock.patch.object(scheduler, "_dispatch",
                           side_effect=lambda *a: dispatched.append(a)), \
         mock.patch("core.remote_client.run_internal_session",
                    side_effect=lambda *a, **k: got.append(a) or "report"), \
         mock.patch("core.orchestrator.run_session",
                    side_effect=AssertionError("ran in-process")) as in_proc:
        scheduler.fire_session("weekly_pattern_miner", "pattern_miner", "analyse", "push", p,
                               job_cfg={**SESSION_JOB, "agent": "pattern_miner"})
    check("pattern_miner goes to /internal/session with its persona",
          got == [("pattern_miner", "analyse", p)])
    check("the in-process run_session is never called", not in_proc.called)
    check("its result is dispatched to the same persona",
          dispatched and dispatched[0][-1] == p and dispatched[0][2] == "report")


_HOLDER = textwrap.dedent("""
    import sys, time
    sys.path.insert(0, {repo!r})
    import core.persona
    from pathlib import Path
    core.persona._ROOT = Path({root!r})
    from core import scheduler
    scheduler._claim_single_instance({persona!r})
    print("CLAIMED", flush=True)
    time.sleep({hold})
""")


def _claimer(root: Path, persona: str, hold: float) -> subprocess.Popen:
    code = _HOLDER.format(repo=str(REPO), root=str(root), persona=persona, hold=hold)
    return subprocess.Popen([sys.executable, "-c", code], stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)


def part_lock(root: Path) -> None:
    print("One scheduler per persona — the lock (real processes)")
    first = _claimer(root, "zz_lock", hold=20)
    line = first.stdout.readline().strip()
    check("the first instance claims the lock", line == "CLAIMED")

    second = _claimer(root, "zz_lock", hold=0)
    out, err = second.communicate(timeout=20)
    check("a second instance for the same persona exits with status 1",
          second.returncode == 1 and "CLAIMED" not in out)
    check("…and says why, loudly", "REFUSING TO START" in err and "holds" in err)

    other = _claimer(root, "zz_other", hold=0)
    out, _ = other.communicate(timeout=20)
    check("a scheduler for a different persona is unaffected",
          other.returncode == 0 and "CLAIMED" in out)

    first.kill()
    first.wait(timeout=10)
    third = _claimer(root, "zz_lock", hold=0)
    out, _ = third.communicate(timeout=20)
    check("once the holder dies (even killed), a new instance claims it",
          third.returncode == 0 and "CLAIMED" in out)


def _fake_proc(base: Path, pid: str, argv: list[str], open_files: list[Path]) -> None:
    d = base / pid
    (d / "fd").mkdir(parents=True)
    (d / "cmdline").write_bytes(("\0".join(argv) + "\0").encode())
    for i, target in enumerate(open_files):
        os.symlink(target, d / "fd" / str(i))


def part_proc_scan(root: Path) -> None:
    print("One scheduler per persona — the /proc scan (fake tree)")
    lock = (core.persona.persona_data_dir("mike") / "logs" / "scheduler.lock")
    lock.parent.mkdir(parents=True, exist_ok=True)
    lock.touch()
    lock = lock.resolve()
    proc = root / "fakeproc"
    old_unit = ["/home/u/multi-model-mcp/.venv/bin/python", "core/scheduler.py",
                "--persona", "mike"]
    _fake_proc(proc, "100", old_unit, [])
    _fake_proc(proc, "101", old_unit, [lock])                       # a new instance, leaving
    _fake_proc(proc, "102", ["/usr/bin/python3", "/abs/core/scheduler.py", "--persona=iva"], [])
    _fake_proc(proc, "103", ["grep", "core/scheduler.py", "--persona", "mike"], [])
    _fake_proc(proc, str(os.getpid()), old_unit, [])                # this process: excluded
    with mock.patch.object(scheduler, "_PROC", proc):
        found = scheduler._lockless_siblings("mike", lock)
        found_iva = scheduler._lockless_siblings("iva", lock)
        found_none = scheduler._lockless_siblings("nin", lock)
    check("the old lock-less unit's process is found", found == ["100"])
    check("a new instance holding the lock file is not counted", "101" not in found)
    check("a non-python command line naming the script is ignored", "103" not in found)
    check("--persona=<p> form is recognised, per persona", found_iva == ["102"])
    check("a persona with no scheduler finds nothing", found_none == [])

    with mock.patch.object(scheduler, "_PROC", proc), \
         mock.patch.object(scheduler, "_INSTANCE_LOCK", None):
        try:
            scheduler._claim_single_instance("mike")
            exited = False
        except SystemExit as e:
            exited = e.code == 1
    check("an instance beside a lock-less --persona process exits on the scan", exited)

    with mock.patch.object(scheduler, "_PROC", root / "no_such_proc"):
        check("no /proc (the Mac) → scan finds nothing, the lock is the check",
              scheduler._lockless_siblings("mike", lock) == [])


def main() -> int:
    original = core.persona._ROOT
    with tempfile.TemporaryDirectory() as td:
        root = Path(td)
        core.persona._ROOT = root
        try:
            part_hold()
            part_push()
            part_review_fixes()
            part_internal_session()
            part_lock(root)
            part_proc_scan(root)
        finally:
            core.persona._ROOT = original
            handle = scheduler._INSTANCE_LOCK
            if handle is not None:
                handle.close()
                scheduler._INSTANCE_LOCK = None
    failed = [label for ok, label in _results if not ok]
    print(f"\n{len(_results) - len(failed)} passed, {len(failed)} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
