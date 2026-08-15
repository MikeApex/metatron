#!/usr/bin/env python3
"""Block a commit that carries another session's uncommitted work.

THE INCIDENT (2026-08-09). Session A edited `routing*.yaml`; session B edited the
same files; B ran `git add <file> && git commit` and swept up A's `send_email`
grant transfer. `deploy.sh` put it live while the agent instructions governing it
sat uncommitted, so email sending was dead in production. **Staging by explicit
filename was already the discipline and did not help** — the collision was at line
granularity inside a file B legitimately meant to stage.

WHY NOT HUNK FINGERPRINTING. The first design recorded each `git diff` hunk after
every edit. It has a fatal false negative: the recorder runs `git diff` on a
*shared* tree, so it returns **both** sessions' hunks and B's manifest silently
ingests A's as its own. It would not have caught the incident it was built for.

WHAT THIS DOES INSTEAD. Hash the whole file right after this session writes it; at
stage time, re-hash on disk. "Is this file exactly as I left it?" is a byte
comparison, not a diff parse, and cannot be fooled by where the other writer's
lines landed.

TWO SEVERITIES, and the split is the whole design (revised after review):

  BLOCK  a file this session wrote that has changed underneath it. This is the
         2026-08-09 shape exactly, and it is the only case proven to need a block.
  WARN   a dirty file this session never wrote. Legitimate constantly — `/archive`
         stages `DEV_BACKLOG.md`, which `sync_dev_backlog.py` writes via Bash and
         no PostToolUse hook ever sees. Blocking it would fire on every close-out,
         and **a guard that blocks routine work trains a permanent override, which
         disables it for the real case.** Noise is not caution.

FAIL CLOSED ON UNCERTAINTY. If git cannot be queried — a concurrent session holding
`.git/index.lock` is the exact parallel-worker case — the guard says so and blocks,
rather than passing silently. Likewise a path expression it cannot resolve.

Escape hatch, named in every message:  METATRON_COMMIT_GUARD=off git commit ...

KNOWN RESIDUAL. If B writes, A writes, then B writes *again*, B's re-hash covers
A's lines and they pass. Narrow, requires interleaving, and fully closed by running
workers in separate worktrees. This guard is the backstop for the main tree.

WHICH TREE (2026-08-15, [DB-0815-01]). The root is resolved from the git command's
own cwd (or its `-C`), never from `CLAUDE_PROJECT_DIR` alone — that env var still
names the MAIN tree inside a worktree session, so the guard used to check the wrong
tree and refuse every solo worktree commit. See `_resolve_root`.

THE SECOND BLIND SPOT IS STILL OPEN, DELIBERATELY. Staging a file this session
edited *and* a Bash-invoked script then rewrote (the `sync_dev_backlog.py` ->
`DEV_BACKLOG.md` case) still BLOCKS: the file is in the manifest, its hash moved,
and nothing distinguishes "my own script did that" from "another session did that".
[DB-0815-01] proposes trusting a session's own recent Bash writes. **Rejected on
inspection 2026-08-15:** the manifest holds files this session wrote via Edit, so
re-hashing them after any Bash call would absorb a *parallel* session's lines into
this session's baseline — reopening 2026-08-09, the incident this guard exists for,
in exchange for removing a one-token override. A narrower fix (script->output
mapping) is a hand-maintained list, which is the [DB-0805-01] antipattern. Left for
Mike to decide; the override is the interim answer and it works.
"""
from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path

STATE_DIR = ".claude/.session_edits"

# git subcommands that can move working-tree content into a commit.
_WRITING = {"add", "commit", "stash"}
# `git stash` forms that only read.
_STASH_READONLY = {"list", "show"}
_SEPARATORS = {"&&", "||", ";", "|", "&"}
_GLOB_CHARS = "*?["


def _env_root() -> Path:
    return Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()


def _common_dir(where: Path):
    """The shared `.git` directory for `where`'s repo, or None.

    Every worktree of a repository reports the *main* tree's git dir here, which
    is what makes it a reliable identity for "same repository, any tree".
    """
    out = _git(where, "rev-parse", "--path-format=absolute", "--git-common-dir")
    if not out:
        return None
    try:
        return Path(out[0]).resolve()
    except OSError:
        return None


def _resolve_root(anchor: Path):
    """The git root containing `anchor`, if it belongs to *this* repository.

    WHY THIS EXISTS (2026-08-15, [DB-0815-01]). `CLAUDE_PROJECT_DIR` still points
    at the MAIN tree inside a worktree session, so the guard ran `git status`
    against the wrong tree: the worktree's own modified files are not dirty there,
    `_match` could account for none of them, and every solo commit from a worktree
    was refused as "path expressions this guard could not account for" — a block
    with no second writer anywhere near it. Two `/backlog attack` workers each lost
    a full run to this on 2026-08-15. `hook_context_gate.py` had the identical gap
    and was fixed on 2026-08-14; this hook did not get the equivalent fix.

    Membership is checked via `--git-common-dir`, so an unrelated repo on the same
    machine is correctly not our business. Two anchors are accepted — where this
    script lives, and `CLAUDE_PROJECT_DIR` — because either alone is a single point
    of failure, and identity only needs one of them to hold.
    """
    start = anchor if anchor.is_dir() else anchor.parent
    while not start.exists() and start != start.parent:
        start = start.parent
    if not start.exists():
        return None

    top = _git(start, "rev-parse", "--show-toplevel")
    if not top:
        return None
    root_path = Path(top[0]).resolve()

    theirs = _common_dir(root_path)
    if theirs is None:
        return None

    anchors = [Path(__file__).resolve().parent.parent]
    env_dir = os.environ.get("CLAUDE_PROJECT_DIR")
    if env_dir:
        anchors.append(Path(env_dir))
    for known in anchors:
        try:
            if known.exists() and _common_dir(known) == theirs:
                return root_path
        except OSError:
            continue
    return None


def _git(root: Path, *args: str):
    """Run git. Returns list of lines, or None if git could not be queried.

    None is distinct from [] on purpose: [] means 'nothing dirty', None means
    'unknown', and unknown must never read as safe.
    """
    try:
        out = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True, text=True, timeout=10,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    if out.returncode != 0:
        return None
    return [ln for ln in out.stdout.splitlines() if ln.strip()]


def _sha(path: Path):
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def _manifest_path(root: Path, session_id: str) -> Path:
    return root / STATE_DIR / f"{session_id}.json"


def _load_manifest(root: Path, session_id: str) -> dict:
    try:
        with open(_manifest_path(root, session_id)) as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


# --------------------------------------------------------------------------
# PostToolUse — record what this session wrote
# --------------------------------------------------------------------------

def record(payload: dict) -> int:
    target = (payload.get("tool_input") or {}).get("file_path", "")
    if not target:
        return 0
    # Anchor on the file being written, so an edit inside a worktree records
    # against that worktree's manifest and not the main tree's.
    root = _resolve_root(Path(target)) or _env_root()
    try:
        rel = str(Path(target).resolve().relative_to(root))
    except ValueError:
        return 0

    digest = _sha(Path(target))
    if digest is None:
        return 0

    session_id = payload.get("session_id", "unknown")
    manifest = _load_manifest(root, session_id)
    manifest[rel] = digest
    try:
        path = _manifest_path(root, session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(manifest, indent=0, sort_keys=True))
        tmp.replace(path)          # atomic: sessions may write concurrently
    except OSError:
        pass
    return 0


# --------------------------------------------------------------------------
# Command parsing — token-level, so quoted text is never mistaken for a command
# --------------------------------------------------------------------------

def _strip_heredocs(command: str) -> str:
    """Remove heredoc *bodies*, keeping the command line that introduces them.

    A heredoc body is data, not shell. It routinely contains apostrophes — every
    commit message with the word "session's" in it — and feeding that to shlex
    raises on unbalanced quotes. That made the guard silently pass on exactly the
    commits it exists to check: `git commit -F - <<'MSG' … MSG` was unparseable,
    and unparseable used to mean pass. Demonstrated live on this guard's own
    close-out commit, 2026-08-13.
    """
    out, lines, i = [], command.split("\n"), 0
    while i < len(lines):
        line = lines[i]
        out.append(line)
        m = re.search(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1", line)
        if m:
            marker = m.group(2)
            i += 1
            while i < len(lines) and lines[i].strip() != marker:
                i += 1                      # drop the body
            if i < len(lines):
                i += 1                      # drop the closing marker too
            continue
        i += 1
    return "\n".join(out)


def _segments(command: str):
    """Split a shell command into token lists at separators. None if unparseable."""
    try:
        tokens = shlex.split(_strip_heredocs(command), comments=False)
    except ValueError:
        return None                       # still unbalanced — caller fails CLOSED
    segments, current = [], []
    for tok in tokens:
        if tok in _SEPARATORS:
            if current:
                segments.append(current)
            current = []
        else:
            current.append(tok)
    if current:
        segments.append(current)
    return segments


def _git_writes(command: str):
    """[(subcommand, flags, paths)] for git calls that can stage content.

    Returns None if the command could not be parsed — the caller fails closed.
    Only a token in *command position* counts, so a `git add` inside a quoted
    string literal is correctly ignored.
    """
    segments = _segments(command)
    if segments is None:
        return None
    found = []
    for seg in segments:
        # skip leading env assignments (FOO=bar git ...)
        i = 0
        while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
            i += 1
        if i >= len(seg) or os.path.basename(seg[i]) != "git":
            continue
        rest = seg[i + 1:]
        # skip git's own global options (-C path, -c k=v, --no-pager …)
        j = 0
        while j < len(rest) and rest[j].startswith("-"):
            j += 2 if rest[j] in ("-C", "-c") else 1
        if j >= len(rest):
            continue
        sub = rest[j]
        if sub not in _WRITING:
            continue
        args = rest[j + 1:]
        if sub == "stash" and args and args[0] in _STASH_READONLY:
            continue
        flags = [a for a in args if a.startswith("-")]
        paths = [a for a in args if not a.startswith("-")]
        if sub == "stash" and paths and paths[0] in ("push", "save"):
            paths = paths[1:]
        found.append((sub, flags, paths))
    return found


def _git_c_dir(command: str):
    """The first `git -C <dir>` value in the command, if any.

    An explicit -C overrides the session's cwd for that git call, so it is the
    most authoritative statement of which tree is about to be staged.
    """
    segments = _segments(command)
    if segments is None:
        return None
    for seg in segments:
        i = 0
        while i < len(seg) and "=" in seg[i] and not seg[i].startswith("-"):
            i += 1
        if i >= len(seg) or os.path.basename(seg[i]) != "git":
            continue
        rest = seg[i + 1:]
        for j, tok in enumerate(rest):
            if tok == "-C" and j + 1 < len(rest):
                return rest[j + 1]
            if not tok.startswith("-"):
                break
    return None


def _root_for_command(payload: dict) -> Path:
    """Which tree is this git command about to stage from?

    Precedence: an explicit `git -C <dir>`, then the session's cwd, then
    `CLAUDE_PROJECT_DIR`. The cwd step is the one that matters for worktrees —
    see `_resolve_root`. Falls back to the old env-only behaviour so a payload
    without cwd is never worse off than before.
    """
    command = (payload.get("tool_input") or {}).get("command", "")
    for anchor in (_git_c_dir(command), payload.get("cwd")):
        if not anchor:
            continue
        root = _resolve_root(Path(anchor))
        if root is not None:
            return root
    return _resolve_root(_env_root()) or _env_root()


def _wants_all(flags) -> bool:
    """True for -a / -am / --all. Only real flag tokens are inspected, so a
    commit message containing '-allocator' can never trigger this."""
    for f in flags:
        if f == "--all":
            return True
        if f.startswith("-") and not f.startswith("--") and "a" in f[1:]:
            return True
    return False


# --------------------------------------------------------------------------
# PreToolUse — check what is about to be staged
# --------------------------------------------------------------------------

def _status(root: Path):
    """(tracked_modified, untracked). None if git could not be queried.

    `-uall` matters: without it git collapses untracked files in a *new*
    directory to a single "newdir/" entry, so an explicitly-named new file
    inside one matches nothing in the pool and lands in `unresolved` -- a block,
    on a file with no other writer. A new file in an already-tracked directory
    is listed individually and was always fine, which is why this went unnoticed
    until `.claude/rules/` was created on 2026-08-14 and blocked its own commit.
    Ignored files stay hidden either way, so this does not enumerate junk.
    """
    lines = _git(root, "status", "--porcelain=v1", "-uall")
    if lines is None:
        return None
    tracked, untracked = [], []
    for line in lines:
        if len(line) < 4:
            continue
        code, name = line[:2], line[3:].strip()
        if " -> " in name:
            name = name.split(" -> ", 1)[1]
        name = name.strip('"')
        (untracked if code == "??" else tracked).append(name)
    return tracked, untracked


def _match(paths, candidates, root: Path):
    """Resolve path expressions against candidate files.

    Returns (matched, unresolved). `unresolved` is non-empty when an expression
    matched nothing it could account for — the caller fails closed on it rather
    than treating 'no match' as 'nothing to check'.
    """
    matched, unresolved = set(), []
    for raw in paths:
        p = raw.strip()
        if p.startswith("./"):
            p = p[2:]
        p = p.rstrip("/")
        if not p or p == ".":
            return set(candidates), []          # `git add .` — everything
        hits = {c for c in candidates
                if c == p
                or c.startswith(p + "/")
                or fnmatch.fnmatch(c, p)
                or fnmatch.fnmatch(os.path.basename(c), p)}
        if hits:
            matched |= hits
        elif any(ch in p for ch in _GLOB_CHARS) or (root / p).exists():
            # A glob the shell already expanded, or a real path git will accept.
            # Either way we cannot account for it — do not call that "clean".
            unresolved.append(raw)
    return matched, unresolved


def _override_requested(command: str) -> bool:
    """Is the escape hatch being invoked, by either route?

    The documented form is an inline prefix -- METATRON_COMMIT_GUARD=off git
    commit ... -- and reading os.environ ALONE never sees it. This hook runs as
    a separate process spawned with the SESSION's environment; the prefix lives
    only in the command string it is handed, and is applied by the shell to the
    git process afterwards. So the documented override was inoperative: it
    blocked, printed "METATRON_COMMIT_GUARD=off to override", and then blocked
    that too. Found by trying to use it (2026-08-13).

    Both routes are honoured now: the inline prefix, and a session-wide env var
    for anyone who wants it off for a whole session.
    """
    if os.environ.get("METATRON_COMMIT_GUARD", "").lower() == "off":
        return True
    return re.search(
        r"(?:^|[;&|]|\s)METATRON_COMMIT_GUARD=(?:off|'off'|\"off\")(?:\s|$)",
        command,
        re.IGNORECASE,
    ) is not None


def check(payload: dict) -> int:
    command = (payload.get("tool_input") or {}).get("command", "")
    if _override_requested(command):
        return 0

    if "git" not in command:
        return 0                                   # cheap prefilter only

    writes = _git_writes(command)
    if writes is None:
        # Unparseable even after heredoc bodies are stripped. The command mentions
        # git, so it may well stage something — and "cannot determine" must never
        # read as safe. This is the same fail-closed stance as an unqueryable git.
        print(
            "COMMIT GUARD: cannot parse this command well enough to tell what it "
            "stages (unbalanced quoting). Refusing to vouch for it.\n"
            "  split it into separate calls, or METATRON_COMMIT_GUARD=off to override.",
            file=sys.stderr,
        )
        return 2
    if not writes:
        return 0

    root = _root_for_command(payload)
    status = _status(root)
    if status is None:
        print(
            "COMMIT GUARD: cannot read git status (index lock held by another "
            "session, or git unavailable). Refusing to vouch for this commit.\n"
            "  retry, or METATRON_COMMIT_GUARD=off to override.",
            file=sys.stderr,
        )
        return 2                                   # fail closed on uncertainty
    tracked, untracked = status

    targets, unresolved = set(), []
    for sub, flags, paths in writes:
        if sub == "commit" and not _wants_all(flags) and not paths:
            staged = _git(root, "diff", "--cached", "--name-only")
            if staged is None:
                print("COMMIT GUARD: cannot read the staged set. Refusing.", file=sys.stderr)
                return 2
            targets |= set(staged)
            continue
        if sub == "commit" and _wants_all(flags):
            targets |= set(tracked)                # -a cannot stage untracked files
            continue
        pool = tracked + untracked
        if not paths:
            targets |= set(pool)
        else:
            hit, miss = _match(paths, pool, root)
            targets |= hit
            unresolved += miss

    session_id = payload.get("session_id", "unknown")
    manifest = _load_manifest(root, session_id)

    blocking = [f for f in sorted(targets)
                if f in manifest and _sha(root / f) != manifest[f]]
    warning = [f for f in sorted(targets) if f not in manifest]

    if blocking or unresolved:
        out = ["COMMIT GUARD: blocked.", ""]
        if blocking:
            out.append("Changed by another writer since this session wrote them:")
            out += [f"  ! {f}" for f in blocking]
            out += [
                "",
                "  This is the 2026-08-09 shape exactly: a file you legitimately",
                "  meant to stage, with someone else's lines inside it.",
                "",
            ]
        if unresolved:
            out.append("Path expressions this guard could not account for:")
            out += [f"  ? {p}" for p in unresolved]
            out.append("")
        out += [
            "Do one of:",
            "  git diff -- <file>          see whose lines those are",
            "  git add <your files>        stage explicitly, by name",
            "  METATRON_COMMIT_GUARD=off   deliberate override",
        ]
        print("\n".join(out), file=sys.stderr)
        return 2

    if warning:
        print(
            "COMMIT GUARD (advisory, not blocking): staging "
            + str(len(warning))
            + " file(s) this session did not write via Edit/Write — "
            + ", ".join(warning[:6])
            + ("…" if len(warning) > 6 else "")
            + ". Normal for script-generated files; check they are yours to commit.",
            file=sys.stderr,
        )
    return 0


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0
    event = payload.get("hook_event_name", "")
    if event == "PostToolUse":
        return record(payload)
    if event == "PreToolUse":
        return check(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
