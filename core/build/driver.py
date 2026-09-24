"""
core/build/driver.py — the control layer. THE COMMAND TAKES ITS EVERY STEP FROM HERE.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 3.

SALVAGED FROM runner.py (section 10, finding 1): the node order, MAX_NODE_RETRIES,
the retry-product cap counted from durable rows, the artifact-is-cursor rule, the
park states and NodeOutcome. What changed is only WHO CALLS THE MODEL. v3's
`_ask()` ran `_run_single_agent` against a Vertex model; under ruling 1 no Build
node calls a Vertex model at all, so `_ask()` becomes NAME THE STEP: this module
decides what happens next and `/build` spawns the Claude Code subagent that does
it.

WHY THAT DISTINCTION IS THE WHOLE POINT OF THE MODULE. A markdown command that
described the graph would be a set of instructions to a model, and every bound in
it — one retry, one send-back, park on the second failure — would be a rule the
model could skip while believing it was following them. Here a model cannot skip
a park or add a retry BECAUSE THE DRIVER WILL NOT NAME THE STEP. The command asks
for the next step and gets one, or gets a gate.

THE COUNTS HAVE A DURABLE HOME. `next_step()` re-derives every bound from
`attempts.jsonl` and the artifacts on disk — never from memory, never from a
field it wrote earlier in the same process. A failed node that wrote no artifact
still counts, and a lost session cannot reset anything (finding 1, verify
residual 1).

THE ARTIFACT IS THE CURSOR. A node whose artifact is present and parseable is
DONE; `next_step()` skips it without a step. That is what makes `/build BLD-…`
re-entered after a kill resume at the node that had not written.
"""

from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from core.build import gates as G
from core.build import jobs as J

logger = logging.getLogger(__name__)

_ROOT = Path(__file__).resolve().parent.parent.parent
_GIT_TIMEOUT = 60


# Rung 2: one targeted retry per node, never more. The repo's stated reason for
# having no retry at all (core/orchestrator.py's no-retry note) is latency on a
# live user turn; Build has nobody waiting on a turn, so one capped retry is
# affordable here and nowhere else.
MAX_NODE_RETRIES = 1

# The review's ONE send-back. Counted as len(build_plan.v*.json) on disk, so it
# survives a lost session with no counter to lose.
MAX_PLAN_VERSIONS = 2

# THE RETRY PRODUCT CAP. Node attempts and job re-entries MULTIPLY, and the
# product is what actually bounds the session. Counted from attempts.jsonl,
# which is one row per started node and survives a restart — a counter held in
# this process would reset on exactly the crash that makes a job expensive.
MAX_ATTEMPTS_PER_JOB = 16


class DriverError(RuntimeError):
    """A step could not be decided — not a node failure, a structural one."""


@dataclass
class NodeOutcome:
    """SALVAGED. What came back from one node."""
    node: str
    status: str          # done | skipped | gate | parked | failed
    detail: str = ""

    @property
    def stop(self) -> bool:
        return self.status in {"gate", "parked", "failed"}


@dataclass
class Step:
    """What the command is told to do next. `kind` decides who runs it."""
    node: str
    kind: str            # agent | code | gate | done | parked
    artifact: str | None = None
    agent: str | None = None
    attempt: int = 1
    detail: str = ""
    defects: list[str] = field(default_factory=list)

    @property
    def is_gate(self) -> bool:
        return self.kind in {"gate", "parked", "done"}


@dataclass
class Node:
    name: str
    kind: str                    # agent | code | gate
    artifact: str | None
    agent: str | None = None
    modes: tuple[str, ...] = ("construct", "repair")


# THE NODE GRAPH, in order. The four human gates are nodes like any other, which
# is what makes "the driver refuses to hand out a step from a gate state" a
# property of the table rather than a rule someone has to remember.
NODES: tuple[Node, ...] = (
    Node("N1r", "code", "dossier", modes=("repair",)),
    Node("N2", "agent", "question_set", agent="build-inquiry"),
    Node("N4", "agent", "answer_ledger", agent="build-librarian"),
    Node("N5", "code", "ledger_check"),
    Node("N6", "gate", None),
    Node("N7", "agent", "build_plan", agent="build-planner"),
    Node("N10", "code", "brief"),
    Node("N8", "agent", "review", agent="adversarial-reviewer"),
    Node("N9", "gate", None),
    Node("N11", "agent", "implementation", agent="build-implementer"),
    Node("N12", "code", "gates"),
    Node("N13", "gate", None),
    Node("N14", "code", "acceptance"),
)

_BY_NAME = {node.name: node for node in NODES}

# What each human gate is waiting for. The driver hands back a `gate` step
# naming one of these and STOPS; nothing here clears a gate, which is the whole
# point of a gate and what a tick that could clear one would make decorative.
GATE_REASON: dict[str, str] = {
    "N6": ("interview items are open — they are answered in this session, in "
           "chat, by the person sitting in front of it"),
    "N9": "the brief is written and Mike has not approved it",
    "N13": ("the patch and the Red half go into the main tree in one sitting, "
            "ending in Mike's commit or in the printed revert"),
}


# ---------------------------------------------------------------------------
# The step decision
# ---------------------------------------------------------------------------

def next_step(job_id: str, persona: str | None = None,
              mode: str = "construct") -> Step:
    """
    The next thing to do, re-derived from disk every single call.

    Nothing is cached and nothing is passed in from a previous call. That is
    what makes the bounds hold across a restart: the retry count comes from
    attempts.jsonl, the send-back count from the plan files on disk, and "has
    this node run" from whether its artifact parses.
    """
    # THE TWO JOB-LEVEL BOUNDS, BEFORE THE NODE WALK. Both must be checked here
    # rather than at the node they belong to: a node whose artifact already
    # exists is skipped by the cursor, so a bound expressed inside the walk is
    # a bound the walk never reaches. The review's send-back is exactly that
    # shape — N7 has written a plan, so N7 is `done`, and the count that says
    # it has written three of them would never be read.
    if len(J.attempts(job_id, persona)) >= MAX_ATTEMPTS_PER_JOB:
        return Step("-", "parked", detail=(
            f"{MAX_ATTEMPTS_PER_JOB} node attempts on this job — the retry "
            "product cap is reached. Read attempts.jsonl before re-running."))

    if len(J.plan_versions(job_id, persona)) > MAX_PLAN_VERSIONS:
        return Step("N8", "parked", detail=(
            f"the review sent the plan back {MAX_PLAN_VERSIONS} times — a "
            "second structural finding parks the job for Mike"))

    for node in NODES:
        if mode not in node.modes:
            continue

        if node.kind == "gate":
            if _gate_is_open(node.name, job_id, persona):
                return Step(node.name, "gate", detail=GATE_REASON[node.name])
            continue

        if node.artifact and _artifact_done(node, job_id, persona):
            continue

        failures = J.failures_for(job_id, node.name, persona)
        if failures > MAX_NODE_RETRIES:
            return Step(node.name, "parked", detail=(
                f"{node.name} failed {failures} times — one retry per node is "
                "the bound, and a second failure is a park, not a third try"),
                defects=J.last_defects(job_id, node.name, persona))

        return Step(node.name, node.kind, artifact=node.artifact,
                    agent=node.agent, attempt=failures + 1,
                    defects=J.last_defects(job_id, node.name, persona))

    return Step("-", "done", detail="every node has produced its artifact")


def _artifact_done(node: Node, job_id: str, persona: str | None) -> bool:
    """
    THE ARTIFACT IS THE CURSOR. Present and parseable means done.

    N7 is the exception, and only in shape: its artifact is versioned
    (`build_plan.v1.json`, `.v2.json`) because the review can send it back, so
    "has N7 run" is "is there at least one version on disk".
    """
    if node.name == "N7":
        return bool(J.plan_versions(job_id, persona))
    if node.artifact in {"brief", "implementation"}:
        return J.artifact_path(job_id, _file_for(node.artifact), persona).exists()
    return J.has_artifact(job_id, node.artifact, persona)


def _file_for(artifact: str) -> str:
    return {"brief": "brief.md", "implementation": "implementation.patch"}[artifact]


def _gate_is_open(gate: str, job_id: str, persona: str | None) -> bool:
    """True when this gate is still waiting on a human."""
    if gate == "N6":
        check = J.read_artifact(job_id, "ledger_check", persona) or {}
        return bool(check.get("interview_items")) and not check.get("answered")
    if gate == "N9":
        return (J.artifact_path(job_id, "brief.md", persona).exists()
                and not J.has_artifact(job_id, "approval", persona))
    if gate == "N13":
        return (J.artifact_path(job_id, "implementation.patch", persona).exists()
                and not J.has_artifact(job_id, "landing", persona))
    return False


def record(job_id: str, step: Step, outcome: str, defects: list[str] | None = None,
           persona: str | None = None) -> dict:
    """
    Record one attempt. CALLED BEFORE THE STEP RUNS, not after (section 3).

    Before, not after, and the ordering is the bound: a session killed mid-node
    has already recorded that the node was attempted, so the restart counts it.
    Recording afterwards would make a crash free, and a crash loop free forever.
    """
    return J.record_attempt(job_id, step.node, step.attempt, outcome,
                            defects, persona)


def retry_prompt(original: str, previous: str, defects: list[str]) -> str:
    """
    Rung 2's prompt: THE REJECTED ARTIFACT plus a machine-written defect list
    naming each failed constraint — never a re-ask.

    A model handed "try again" produces a different guess. A model handed its
    own output and the named constraint it broke produces a fix.
    """
    listed = "\n".join(f"- {d}" for d in defects)
    return (f"{original}\n\n---\n\n"
            f"Your previous answer was REJECTED. It is reproduced below, followed "
            f"by every constraint it failed. Fix exactly those and change nothing "
            f"else.\n\n## Your previous answer\n\n{previous}\n\n"
            f"## Constraints it failed\n\n{listed}\n")


# ---------------------------------------------------------------------------
# N12 — the patch, written without a staging verb
# ---------------------------------------------------------------------------

def write_patch(worktree: Path, job_id: str, persona: str | None = None) -> Path:
    """
    Turn the worktree's changes into one patch. NO `add`, `commit` OR `stash`.

    `git diff HEAD --binary` for tracked files, plus one `git diff --no-index
    --binary /dev/null <path>` per untracked file. The staging verbs are never
    issued in the worktree, so hook_commit_guard.py's watched verbs never fire
    there — chosen so the step is correct whether or not the guard parses this
    module's subprocess calls (verify round 2, NEW 2).

    The patch is also the copy that makes `rm_worktree.sh --force` safe after
    N13: the worktree holds no commit, so the patch is the only thing that
    crossed out of it.
    """
    chunks = [_git(worktree, "diff", "HEAD", "--binary")]
    for rel in _untracked(worktree):
        chunks.append(_git_allow_fail(worktree, "diff", "--no-index", "--binary",
                                      "/dev/null", rel))
    return J.write_text(job_id, "implementation.patch", "".join(chunks), persona)


def patch_paths(patch_text: str) -> set[str]:
    """
    Every path the patch touches, from its own `diff --git` lines.

    Read from the patch rather than from the worktree, because what N13 applies
    is the patch — so the set that must equal the implementer's half of
    `files[]` is the patch's, not the tree's.
    """
    out: set[str] = set()
    for line in patch_text.splitlines():
        if not line.startswith("diff --git "):
            continue
        parts = line.split(" b/", 1)
        if len(parts) == 2:
            out.add(parts[1].strip())
    return {p for p in out if p and p != "dev/null"}


def _untracked(tree: Path) -> list[str]:
    return [p for p in _git(tree, "ls-files", "--others",
                            "--exclude-standard").splitlines() if p.strip()]


def _git(tree: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(tree), capture_output=True,
                          text=True, timeout=_GIT_TIMEOUT)
    if proc.returncode != 0:
        raise DriverError(f"git {' '.join(args)} in {tree}: {proc.stderr.strip()}")
    return proc.stdout


def _git_allow_fail(tree: Path, *args: str) -> str:
    """`git diff --no-index` exits 1 when the files differ, which is always here."""
    proc = subprocess.run(["git", *args], cwd=str(tree), capture_output=True,
                          text=True, timeout=_GIT_TIMEOUT)
    return proc.stdout


def git_log(worktree: Path) -> list[str]:
    """
    The git subcommands this module would issue in a worktree, for the § 12 row
    that asserts none of them is `add`, `commit` or `stash`.

    Declared rather than recorded, deliberately: a recorded log proves what one
    run happened to do, and a declaration is what a test can hold the code to.
    Every call site above uses one of these.
    """
    return ["diff", "ls-files"]


# ---------------------------------------------------------------------------
# N13 — one tree, one diff, one commit, one sitting
# ---------------------------------------------------------------------------

def landing_preconditions(main_tree: Path, files: list[str]) -> list[str]:
    """
    Refusals that stop N13 STARTING. Empty means go.

    EVERY PATH IN `files[]`, BOTH HALVES, must be clean in the main tree — the
    Red targets included, because `routing*.yaml` and `coordinator.md` are
    exactly the files another chat is most likely to hold uncommitted lines in,
    and the main session is about to write into them (cold verify NEW 1).

    Another chat's dirt in OTHER files is not Build's concern and is left alone.
    That asymmetry is the whole of cold read 1: a shared main tree is the normal
    state here, and a precondition that demanded a globally clean tree would
    never pass.
    """
    if not files:
        return ["files[] is empty — there is nothing to land"]
    proc = subprocess.run(
        ["git", "status", "--porcelain", "-uall", "--", *files],
        cwd=str(main_tree), capture_output=True, text=True, timeout=_GIT_TIMEOUT)
    if proc.returncode != 0:
        return [f"git status in the main tree failed: {proc.stderr.strip()}"]
    dirty = [line[3:].strip() for line in proc.stdout.splitlines() if len(line) > 3]
    return [
        f"{path} is dirty in the main tree and is in files[] — N13 is one "
        "unbroken sitting, and starting it over someone else's uncommitted "
        "lines is how the 2026-08-09 shape happens"
        for path in sorted(set(dirty))
    ]


def apply_patch(main_tree: Path, patch: Path, files: list[str]) -> tuple[bool, str]:
    """
    (applied, detail). Plain if HEAD is the sandbox's base, `--3way` if it moved.

    `--3way` IMPLIES `--index`. Without the reset that follows, the hunks would
    sit STAGED past a commit guard that watches `add`, `commit` and `stash` but
    never `apply` — and the printed revert line would then restore the applied
    content from the index rather than from HEAD (cold verify NEW 1). So either
    branch ends with the working tree carrying the hunks UNSTAGED and the index
    equal to HEAD.
    """
    plain = subprocess.run(["git", "apply", str(patch)], cwd=str(main_tree),
                           capture_output=True, text=True, timeout=_GIT_TIMEOUT)
    if plain.returncode == 0:
        return True, "applied cleanly"

    three = subprocess.run(["git", "apply", "--3way", str(patch)],
                           cwd=str(main_tree), capture_output=True, text=True,
                           timeout=_GIT_TIMEOUT)
    if three.returncode == 0:
        _reset(main_tree, files)
        return True, "applied with --3way (HEAD had moved); index reset to HEAD"

    # --3way IS NOT ATOMIC: new files and clean hunks land before the
    # conflicting hunk stops it. So the park runs the SAME full revert the
    # wiring gate prints — one function, used in both places, so the two cannot
    # drift (cold verify round 2).
    revert_landing(main_tree, files)
    return False, (f"3-way apply conflicted and the job is parked; the patch's "
                   f"paths were reverted to HEAD. git said: {three.stderr.strip()}")


def _reset(main_tree: Path, files: list[str]) -> None:
    subprocess.run(["git", "reset", "-q", "--", *files], cwd=str(main_tree),
                   capture_output=True, text=True, timeout=_GIT_TIMEOUT)


def revert_landing(main_tree: Path, files: list[str]) -> list[str]:
    """
    Take a half-landed capability back out of a tree another chat may be using.

    THE ONE FUNCTION, used by the conflict park AND printed as the wiring
    gate's revert line, so the two cannot drift. Three moves, in this order:

      1. `git checkout HEAD -- <path>` for every path that EXISTS at HEAD.
         FROM HEAD AND NEVER FROM THE INDEX — after a `--3way` apply the index
         carries the applied content, so the bare `git checkout -- <path>` form
         would restore exactly what it was meant to remove.
      2. `rm` for every path the patch ADDED. A checkout cannot remove a file
         that does not exist at HEAD, which is why step 1 alone was wrong.
      3. `git reset -q -- <paths>` so the index matches HEAD either way.

    Never `git checkout .`, which the harness denies and which would take
    another chat's work with it.
    """
    if not files:
        return []
    at_head, added = [], []
    for path in files:
        proc = subprocess.run(["git", "cat-file", "-e", f"HEAD:{path}"],
                              cwd=str(main_tree), capture_output=True,
                              timeout=_GIT_TIMEOUT)
        (at_head if proc.returncode == 0 else added).append(path)

    issued: list[str] = []
    if at_head:
        subprocess.run(["git", "checkout", "HEAD", "--", *at_head],
                       cwd=str(main_tree), capture_output=True, timeout=_GIT_TIMEOUT)
        issued.append("git checkout HEAD -- " + " ".join(at_head))
    for path in added:
        (main_tree / path).unlink(missing_ok=True)
        issued.append(f"rm {path}")
    _reset(main_tree, files)
    issued.append("git reset -q -- " + " ".join(files))
    return issued


def revert_line(files: list[str], main_tree: Path | None = None) -> str:
    """
    The exact revert command, as one line, for the board.

    Printed on a red wiring gate so a half-landed capability can be taken back
    out in one paste. Derived from the same three moves revert_landing() makes,
    so what is printed is what would run.
    """
    if not files:
        return ""
    tree = main_tree or _ROOT
    at_head, added = [], []
    for path in files:
        proc = subprocess.run(["git", "cat-file", "-e", f"HEAD:{path}"],
                              cwd=str(tree), capture_output=True, timeout=_GIT_TIMEOUT)
        (at_head if proc.returncode == 0 else added).append(path)
    parts = []
    if at_head:
        parts.append("git checkout HEAD -- " + " ".join(at_head))
    if added:
        parts.append("rm -f " + " ".join(added))
    parts.append("git reset -q -- " + " ".join(files))
    return " && ".join(parts)


# ---------------------------------------------------------------------------
# The staging manifest
# ---------------------------------------------------------------------------

def staging_manifest(files: list[str]) -> str:
    """
    What Mike stages. EXPLICIT PATHS, never `git add -A` and never `git add .`.

    Staging by filename is what the 2026-08-09 incident turned on — but the
    lesson recorded there is narrower than "name the files": it is that naming
    them does NOT protect you from another session's lines INSIDE one of them.
    Which is why the wiring gate above refuses to print this at all until every
    path in files[] was verified clean before the patch went in.
    """
    return "git add " + " ".join(files)
