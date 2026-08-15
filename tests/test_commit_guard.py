"""tests/test_commit_guard.py — scripts/hook_commit_guard.py, against real git trees.

The guard has been corrected five times (heredoc bodies, the inoperative override,
untracked files in a new directory, worktree root resolution, an attached semicolon
that disabled it entirely) and every one of those was found by a human tripping over
it in production rather than by a test. Four of the five were fail-OPEN or
block-routine-work defects — the two failure modes that are invisible until they
matter. This file exists so the sixth is found here.

Each case builds a throwaway git repo, writes real manifests into
`.claude/.session_edits/`, and runs the hook as the harness runs it: a JSON payload
on stdin, exit code 0 (allow) or 2 (block).

Run:  python tests/test_commit_guard.py
"""

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
GUARD = REPO / "scripts" / "hook_commit_guard.py"

SESSION = "1111aaaa-0000-0000-0000-000000000000"
OTHER = "2222bbbb-0000-0000-0000-000000000000"


def _run(cwd: Path, *args: str) -> None:
    subprocess.run(args, cwd=cwd, check=True,
                   capture_output=True, text=True)


def _new_repo() -> Path:
    root = Path(tempfile.mkdtemp())
    _run(root, "git", "init", "-q")
    _run(root, "git", "config", "user.email", "t@t.t")
    _run(root, "git", "config", "user.name", "t")
    (root / "seed.txt").write_text("seed\n")
    _run(root, "git", "add", "seed.txt")
    _run(root, "git", "commit", "-qm", "seed")
    return root


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(root: Path, session: str, entries: dict) -> None:
    d = root / ".claude" / ".session_edits"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{session}.json").write_text(json.dumps(entries))


def _check(root: Path, command: str, session: str = SESSION) -> tuple[int, str]:
    """Run the PreToolUse check. Returns (exit_code, stderr)."""
    payload = {
        "hook_event_name": "PreToolUse",
        "session_id": session,
        "cwd": str(root),
        "tool_input": {"command": command},
    }
    env = dict(os.environ)
    env["CLAUDE_PROJECT_DIR"] = str(root)
    env.pop("METATRON_COMMIT_GUARD", None)
    out = subprocess.run(
        [sys.executable, str(GUARD)],
        input=json.dumps(payload), capture_output=True, text=True, env=env,
    )
    return out.returncode, out.stderr


# --- the incident this guard exists for ------------------------------------

def test_another_sessions_edit_still_blocks():
    """2026-08-09, replayed. It must survive every change to this file."""
    root = _new_repo()
    f = root / "routing.yaml"
    f.write_text("mine\n")
    _manifest(root, SESSION, {"routing.yaml": _sha(f)})
    f.write_text("theirs\n")                       # session B writes after us
    _manifest(root, OTHER, {"routing.yaml": _sha(f)})

    code, err = _check(root, "git add routing.yaml")
    assert code == 2, f"the 2026-08-09 shape was allowed through\n{err}"
    assert "routing.yaml" in err
    assert OTHER[:8] in err, "the blocking message does not name the other session"


# --- what [DB-0815-01] fixed ------------------------------------------------

def test_own_bash_rewrite_no_longer_blocks():
    """The whole point: my Edit, then my own script. Nobody else claims it."""
    root = _new_repo()
    f = root / "DEV_BACKLOG.md"
    f.write_text("edited by me\n")
    _manifest(root, SESSION, {"DEV_BACKLOG.md": _sha(f)})
    f.write_text("rewritten by my own sync script\n")   # no manifest update

    code, err = _check(root, "git add DEV_BACKLOG.md")
    assert code == 0, f"own-tooling rewrite still blocked\n{err}"
    assert "not a collision" in err, "the advisory did not explain itself"


def test_unchanged_file_is_silent():
    root = _new_repo()
    f = root / "a.py"
    f.write_text("x\n")
    _manifest(root, SESSION, {"a.py": _sha(f)})
    code, err = _check(root, "git add a.py")
    assert code == 0, err
    assert "not a collision" not in err, "advisory fired on an unchanged file"


def test_stale_manifest_cannot_manufacture_a_collision():
    """An old session's entry carries the OLD hash, so it claims nothing now."""
    root = _new_repo()
    f = root / "b.py"
    f.write_text("v1\n")
    old = _sha(f)
    _manifest(root, OTHER, {"b.py": old})          # they edited, then it moved on
    f.write_text("v2 by me\n")
    _manifest(root, SESSION, {"b.py": _sha(f)})
    f.write_text("v3 by my script\n")

    code, err = _check(root, "git add b.py")
    assert code == 0, f"a stale manifest entry produced a false block\n{err}"


def test_corrupt_manifest_is_ignored_not_trusted():
    root = _new_repo()
    f = root / "c.py"
    f.write_text("mine\n")
    _manifest(root, SESSION, {"c.py": _sha(f)})
    f.write_text("changed\n")
    d = root / ".claude" / ".session_edits"
    (d / f"{OTHER}.json").write_text("{not json")

    code, err = _check(root, "git add c.py")
    assert code == 0, f"a torn manifest was treated as a claim\n{err}"


# --- the fail-open regressions, pinned --------------------------------------

def test_attached_semicolon_does_not_blind_the_guard():
    """`echo hi; git add x` once parsed as one non-git segment and passed."""
    root = _new_repo()
    f = root / "routing.yaml"
    f.write_text("mine\n")
    _manifest(root, SESSION, {"routing.yaml": _sha(f)})
    f.write_text("theirs\n")
    _manifest(root, OTHER, {"routing.yaml": _sha(f)})

    code, err = _check(root, "echo hi; git add routing.yaml")
    assert code == 2, f"guard went blind on an attached semicolon\n{err}"


def test_heredoc_body_does_not_break_parsing():
    """A commit message with an apostrophe once made the command unparseable."""
    root = _new_repo()
    f = root / "routing.yaml"
    f.write_text("mine\n")
    _manifest(root, SESSION, {"routing.yaml": _sha(f)})
    f.write_text("theirs\n")
    _manifest(root, OTHER, {"routing.yaml": _sha(f)})

    cmd = "git add routing.yaml && git commit -F - <<'MSG'\nthis session's work\nMSG"
    code, err = _check(root, cmd)
    assert code == 2, f"heredoc body broke the check\n{err}"


def test_override_prefix_is_honoured():
    root = _new_repo()
    f = root / "routing.yaml"
    f.write_text("mine\n")
    _manifest(root, SESSION, {"routing.yaml": _sha(f)})
    f.write_text("theirs\n")
    _manifest(root, OTHER, {"routing.yaml": _sha(f)})

    code, _ = _check(root, "METATRON_COMMIT_GUARD=off git add routing.yaml")
    assert code == 0, "the documented inline override did not work"


def test_non_git_command_is_ignored():
    root = _new_repo()
    code, err = _check(root, "ls -la")
    assert code == 0 and not err.strip()


# --- untracked files in a new directory (2026-08-14) ------------------------

def test_new_directory_files_named_explicitly_are_not_unresolved():
    root = _new_repo()
    d = root / "newdir"
    d.mkdir()
    (d / "one.md").write_text("a\n")
    (d / "two.md").write_text("b\n")
    code, err = _check(root, "git add newdir/one.md newdir/two.md")
    assert code == 0, f"explicitly-named new files were refused\n{err}"


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
