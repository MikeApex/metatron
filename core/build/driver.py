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
from datetime import datetime
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

# The SAME bound, expressed as the thing send_back() counts. One send-back means
# v1 and v2 exist, so one rejection is allowed and the second parks. DERIVED
# rather than written twice: two constants that could disagree about one bound is
# the defect class this module exists to prevent.
#
# WHY REJECTIONS AND NOT PLAN FILES ARE THE TRIGGER. Counting plan files can only
# park AFTER v3 has been written, which is after the planner has already run —
# one Opus call past the bound that exists to refuse it. Counting rejections
# parks before send_back() deletes anything or names a step. MAX_PLAN_VERSIONS
# stays as the backstop for a v3 that arrives by any other route.
MAX_SEND_BACKS = MAX_PLAN_VERSIONS - 1

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
    # A DURABLE PARK OUTRANKS EVERYTHING. park() writes this, and only unpark()
    # clears it, so a boundary violation — a deny-list write, a patch whose path
    # set is wrong — stops the job on disk rather than in whoever's head read
    # the refusal. Before this existed the only way to park was to fail a node
    # twice, so a violation that must never be retried was answered with a
    # retry.
    held = J.read_artifact(job_id, "park", persona)
    if held:
        return Step(str(held.get("node") or "-"), "parked",
                    detail=str(held.get("reason") or "parked"),
                    defects=[str(p) for p in (held.get("paths") or [])])

    # THE JOB-LEVEL BOUNDS, BEFORE THE NODE WALK. Each must be checked here
    # rather than at the node they belong to: a node whose artifact already
    # exists is skipped by the cursor, so a bound expressed inside the walk is
    # a bound the walk never reaches. The review's send-back is exactly that
    # shape — N7 has written a plan, so N7 is `done`, and the count that says
    # it has written three of them would never be read.
    if len(J.attempts(job_id, persona)) >= MAX_ATTEMPTS_PER_JOB:
        return Step("-", "parked", detail=(
            f"{MAX_ATTEMPTS_PER_JOB} node attempts on this job — the retry "
            "product cap is reached. Read attempts.jsonl before re-running."))

    if rejections(job_id, persona) > MAX_SEND_BACKS:
        return Step("N8", "parked", detail=(
            f"the review sent the plan back {MAX_SEND_BACKS} time(s) — a "
            "second structural finding parks the job for Mike"))

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

        # N7's attempt number is WHICH PLAN this is, not how many times the node
        # has crashed — a send-back is a second plan, not a failed first one,
        # and retry_prompt reads this to say so.
        attempt = failures + 1
        if node.name == "N7":
            attempt = max(attempt, len(J.plan_versions(job_id, persona)) + 1)

        return Step(node.name, node.kind, artifact=node.artifact,
                    agent=node.agent, attempt=attempt,
                    defects=J.last_defects(job_id, node.name, persona))

    return Step("-", "done", detail="every node has produced its artifact")


def rejections(job_id: str, persona: str | None = None) -> int:
    """
    How many times the review has sent this plan back. The send-back counter.

    Read from attempts.jsonl rather than from the plan files, because the count
    has to be available BEFORE the replacement plan is written — that is the
    whole reason this exists beside MAX_PLAN_VERSIONS (see the constant).
    """
    return sum(1 for row in J.attempts(job_id, persona)
               if str(row.get("node")) == "N8"
               and str(row.get("outcome")) == "rejected")


def _artifact_done(node: Node, job_id: str, persona: str | None) -> bool:
    """
    THE ARTIFACT IS THE CURSOR. Present and parseable means done.

    N7 is the exception, and the rule is NOT "a plan exists". A rejected plan is
    a plan that exists and must be replaced, so N7 is done only when there are
    MORE plan versions than rejections. v1 with no rejection is done; v1 with
    one rejection is not, and the walk names N7 again — which is what makes the
    send-back a step the driver hands out rather than a sequence someone
    remembers.
    """
    if node.name == "N7":
        return len(J.plan_versions(job_id, persona)) > rejections(job_id, persona)
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


def begin(job_id: str, step: Step, persona: str | None = None) -> dict | None:
    """
    Record that a step is STARTING. Only a subagent node gets a row.

    Call it before every step; this decides which ones count. A `started` row at
    every node spends nine of MAX_ATTEMPTS_PER_JOB's sixteen before anything has
    gone wrong, and one send-back plus two single retries then reaches exactly
    sixteen on a job that is inside every other bound — a legitimate job parked
    at the product cap.

    A subagent node is where a kill loses real work, so that is where a crash
    has to be paid for. A code node is deterministic and cheap to redo, and a
    GATE is not a step at all — recording one would let re-entering [N9] a few
    times park the job.
    """
    if step.kind != "agent":
        return None
    return J.record_attempt(job_id, step.node, step.attempt, "started",
                            None, persona)


def park(job_id: str, node: str, reason: str, persona: str | None = None,
         paths: list[str] | None = None) -> Step:
    """
    Stop this job on disk until a human clears it. THE DURABLE PARK.

    The only park the driver had was "fail a node twice", which means the one
    class of event that must never be retried — a boundary violation: a write to
    a deny-list path, a patch whose path set is not the plan's — was answered
    with a retry, and the second spawn ran before the park arrived. A refusal
    recorded here holds across a restart and outranks every other state in
    next_step().
    """
    J.write_artifact(job_id, "park", {
        "node": str(node),
        "reason": str(reason),
        "paths": [str(p) for p in (paths or [])],
        "at": datetime.now().isoformat(timespec="seconds"),
    }, persona)
    return Step(str(node), "parked", detail=str(reason),
                defects=[str(p) for p in (paths or [])])


def unpark(job_id: str, persona: str | None = None) -> bool:
    """Clear a durable park. Mike's call, never a step's."""
    path = J.artifact_path(job_id, "park", persona)
    existed = path.exists()
    path.unlink(missing_ok=True)
    return existed


def defect_lines(findings) -> list[str]:
    """
    A defect list from whatever N8 produced. Strings pass through; a parsed
    finding gives up its `wrong` sentence.

    HERE RATHER THAN IN THE COMMAND, because a hand-written
    `[f["wrong"] for f in structural]` is a promise the command file makes and
    nothing keeps: the reviewer emits markdown, so that index raised on the
    first real structural finding — at the node the send-back bound depends on.
    """
    out: list[str] = []
    for finding in (findings or []):
        if isinstance(finding, dict):
            text = (finding.get("wrong") or finding.get("title")
                    or finding.get("detail") or "")
        else:
            text = str(finding)
        text = " ".join(str(text).split())
        if text:
            out.append(text)
    return out


def send_back(job_id: str, persona: str | None = None,
              findings=None,
              mode: str = "construct") -> Step:
    """
    The review rejected the plan structurally. Rewind the cursor, and return the
    next step — which is the park when the bound is spent.

    WHAT IS THE MODEL'S AND WHAT IS THIS FUNCTION'S. Whether a finding is
    structural is a judgement and stays with the reader. Everything after that
    is here: the count, the bound, and the two artifacts that have to go.

    THE ORDER IS THE BOUND. The rejection is recorded, then the bound is
    checked, and ONLY THEN is anything deleted. A version that deleted first and
    checked later would spend a planner call past the bound that exists to
    refuse it, and would leave a parked job with no brief to diagnose it from.
    """
    already = rejections(job_id, persona)
    J.record_attempt(job_id, "N8", already + 1, "rejected",
                     defect_lines(findings), persona)

    if already + 1 > MAX_SEND_BACKS:
        # Parked. brief.md and review.json are deliberately left on disk: this
        # is the moment someone has to read them.
        return next_step(job_id, persona, mode)

    for name in ("brief.md", "review"):
        J.artifact_path(job_id, name, persona).unlink(missing_ok=True)
    return next_step(job_id, persona, mode)


# The three artifacts a MODEL writes, and the validator each is climbed
# through. Anything not here is code-written and is landed as-is — `climb` is a
# validator lookup and raises KeyError on a kind it has none for.
_MODEL_KINDS: dict[str, str] = {
    "N2": "question_set",
    "N4": "answer_ledger",
    "N7": "build_plan",
}

# Artifacts that are TEXT, not JSON, and the filename each lands under.
_TEXT_ARTIFACTS: dict[str, str] = {
    "brief": "brief.md",
    "implementation": "implementation.patch",
}


def land(job_id: str, step: Step, payload, persona: str | None = None,
         upstream: dict | None = None, **checks) -> tuple[object, list[str]]:
    """
    Validate and write ONE node's artifact. (artifact, defects).

    THE ONLY WAY AN ARTIFACT LANDS, and that is the point: every node's landing
    rule differs in a way that is invisible until it bites.

      · N7 must go through write_plan(). A plain write_artifact() lands
        `build_plan.json`, which plan_versions() does not glob — so N7 reads as
        never-done and loops, while the send-back counter counts nothing.
      · brief and implementation are TEXT; the rest are JSON.
      · Only N2, N4 and N7 have validators. Climbing a code node raises
        KeyError.

    A failure records `failed` with the defect list here, so the retry the
    driver hands out is always carrying what the last attempt broke.
    """
    from core.build import schemas as S

    kind = _MODEL_KINDS.get(step.node)
    if kind:
        inject = {"job_id": job_id, "generated_at": S.now_stamp(),
                  "upstream_fingerprint": S.artifact_fingerprint(upstream or {})}
        artifact, defects, _notes = S.climb(kind, payload, inject=inject, **checks)
        if defects:
            J.record_attempt(job_id, step.node, step.attempt, "failed",
                             defects, persona)
            return None, defects
        if step.node == "N7":
            J.write_plan(job_id, artifact, persona)
        else:
            J.write_artifact(job_id, step.artifact, artifact, persona)
        return artifact, []

    if step.artifact in _TEXT_ARTIFACTS:
        J.write_text(job_id, _TEXT_ARTIFACTS[step.artifact], str(payload), persona)
    else:
        J.write_artifact(job_id, step.artifact, payload, persona)
    return payload, []


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
    # The restore is here as well as in implementer_gate(), deliberately: this
    # is the last point before the diff is taken, and a fixture file left dirty
    # at this instant goes INTO the patch and then into Mike's tree at N13.
    # Cheap, idempotent, and it makes the guarantee a property of the function
    # rather than of the caller having remembered.
    G.restore_fixtures(worktree)

    chunks = [_git(worktree, "diff", "HEAD", "--binary")]
    for rel in _untracked(worktree):
        chunks.append(_git_allow_fail(worktree, "diff", "--no-index", "--binary",
                                      "/dev/null", rel))
    return J.write_text(job_id, "implementation.patch", "".join(chunks), persona)


def implementer_half(plan: dict) -> list[str]:
    """The paths the implementer may touch. Everything else in files[] is Red."""
    return [str(e.get("path")) for e in (plan.get("files") or [])
            if isinstance(e, dict) and e.get("half") == "implementer"
            and e.get("path")]


def all_files(plan: dict) -> list[str]:
    """Every path in files[], both halves — what N13 lands and Mike stages."""
    return [str(e.get("path")) for e in (plan.get("files") or [])
            if isinstance(e, dict) and e.get("path")]


def channel_baseline(job_id: str, worktree: Path, main_tree: Path,
                     persona: str | None = None) -> dict:
    """
    The before-snapshot, taken ONCE PER JOB and kept on disk.

    Re-taking it before a retry takes the baseline with the PREVIOUS attempt's
    deny-list write already in place — so the hash delta is empty and channels
    (b) and (c) pass the exact change they refused a minute earlier, including a
    hook planted through the worktree's `.git` pointer, which would then run
    under Mike's own commit at N13.

    Keeping it is therefore not an optimisation. It is the difference between a
    channel that watches and a channel that has been re-armed by the thing it
    was watching for.
    """
    existing = J.read_artifact(job_id, "channels_before", persona)
    if existing:
        return existing
    taken = G.snapshot(worktree, main_tree)
    J.write_artifact(job_id, "channels_before", taken, persona)
    return taken


def implementer_gate(job_id: str, worktree: Path, main_tree: Path, plan: dict,
                     persona: str | None = None,
                     spawned: bool = True) -> tuple[Path | None, list[str], list[str]]:
    """
    Everything between the implementer returning and the patch existing.
    (patch_path, refusals, notes). A non-empty refusal list means the job is
    PARKED — durably, by park(), not by a rule someone has to remember.

    THE ORDER IS THE WHOLE FUNCTION, and every step of it was a separate defect:

      1. restore the fixture trees FIRST. The implementer runs the suites itself
         before reporting, and `data/personas/` is on the deny list — so a
         benign test side-effect is otherwise refused as a boundary violation.
      2. the four channels, against the KEPT baseline.
      3. the capability's own tests and the sweep.
      4. restore again — step 3 just re-ran the same suites.
      5. the patch, whose path set must equal the implementer's half of files[].

    `spawned=False` is the RE-ENTRY form: it runs 1 and 2 and stops. An
    uncleared violation still on disk refuses again having cost no model call,
    and the second recorded failure is what the driver parks on — rather than
    the park arriving one implementer spawn late.
    """
    before = channel_baseline(job_id, worktree, main_tree, persona)
    notes: list[str] = []

    restored = G.restore_fixtures(worktree)
    if restored:
        notes.append("restored tracked fixture-persona files dirtied by the "
                     f"implementer's own test run: {sorted(restored)}")

    after = G.snapshot(worktree, main_tree)
    impl = set(implementer_half(plan))
    refusals, channel_notes = G.check_channels(
        before.get("worktree_hashes") or {}, after["worktree_hashes"],
        before.get("main_hashes") or {}, after["main_hashes"],
        after["worktree_changed"],
        set(before.get("main_dirty") or []), set(after["main_dirty"]),
        impl)
    notes.extend(channel_notes)

    if refusals:
        park(job_id, "N11", "a channel refused the implementer's worktree — a "
             "boundary violation is not a defect in the output, so it is a park "
             "and never a retry. The worktree is left in place to be read.",
             persona, paths=refusals)
        return None, refusals, notes

    if not spawned:
        return None, [], notes

    from core.build import verify as V
    report = V.code_checks(worktree, implementer_half(plan),
                           [str(t) for t in (plan.get("tests") or [])])
    if not report.ok:
        defects = [f"{r.name}: {r.output[-400:]}" for r in report.failures]
        J.record_attempt(job_id, "N11", _attempt_for(job_id, "N11", persona),
                         "failed", defects, persona)
        return None, defects, notes

    G.restore_fixtures(worktree)
    patch = write_patch(worktree, job_id, persona)
    landed = patch_paths(patch.read_text(encoding="utf-8", errors="replace"))
    if landed != impl:
        park(job_id, "N11",
             "the patch's path set is not the implementer's half of files[] — "
             f"extra {sorted(landed - impl)}, missing {sorted(impl - landed)}",
             persona, paths=sorted(landed ^ impl))
        patch.unlink(missing_ok=True)
        return None, [f"patch path set != files[]: {sorted(landed ^ impl)}"], notes

    return patch, [], notes


def _attempt_for(job_id: str, node: str, persona: str | None) -> int:
    return J.failures_for(job_id, node, persona) + 1


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

def tree_split(main_tree: Path) -> list[str]:
    """
    Refusals when the job store and the landing tree are different checkouts OF
    THE SAME REPOSITORY. Empty means go.

    `core.build` resolves its root from wherever it was imported, so a `/build`
    run from a worktree keeps its job directory, its registry and its manifest
    THERE while N13 applies the patch and writes the Red half to `main_tree`.
    The job then exists in two places, and `mark_landed` raises against a
    registry that has no row — mid-sitting, after Mike's prompts have been
    spent.

    THE TEST IS "SAME REPOSITORY, DIFFERENT CHECKOUT", not "same path", and
    that precision is what makes this safe to run unconditionally: a fixture
    tree in a suite is its own repository, so it is not a split and is not
    refused. Two worktrees of this repo share a common git dir, and that is
    exactly the case that must never reach a landing.
    """
    if _ROOT == Path(main_tree).resolve():
        return []
    mine, theirs = _common_git_dir(_ROOT), _common_git_dir(Path(main_tree))
    if not mine or not theirs or mine != theirs:
        return []
    return [
        f"the job store is in {_ROOT} and the landing tree is {main_tree} — two "
        "checkouts of one repository. /build runs in the main tree; from a "
        "worktree the patch lands in one tree while the registry, the job "
        "directory and the manifest stay in the other."
    ]


def _common_git_dir(tree: Path) -> str:
    proc = subprocess.run(["git", "rev-parse", "--git-common-dir"],
                          cwd=str(tree), capture_output=True, text=True,
                          timeout=_GIT_TIMEOUT)
    if proc.returncode != 0:
        return ""
    found = Path(proc.stdout.strip())
    if not found.is_absolute():
        found = Path(tree) / found
    try:
        return str(found.resolve())
    except OSError:
        return ""


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

    split = tree_split(main_tree)
    if split:
        return split

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

def finish_landing(job_id: str, main_tree: Path, plan: dict, ledger: dict,
                   agent_text: str, persona: str | None = None
                   ) -> tuple[bool, list[str]]:
    """
    The second half of N13, once the Red files are in the tree. (ok, lines).

    `lines` is what goes on the board: the staging manifest and the advisory
    sweep note on green, the failing check and the exact revert command on red.

    THIS IS ONE CALL BECAUSE THE SEQUENCE IS THE GATE. Written out as four
    steps for a reader to follow, the content gate is the one that gets
    skipped — it is last, it reads inputs nothing else needs, and skipping it
    produces no error. A capability landing with an unscanned record and no
    peer comparison looks exactly like one that passed.

    `mark_landed` is inside for the same reason and in this order: the wiring
    checks assert routing parity and the Coordinator entry only for a `landed`
    row, so flipping it is what arms them.
    """
    from core.build import registry as R
    from core.build import verify as V

    name = str((plan.get("record") or {}).get("name")
               or (plan.get("capability") or {}).get("id") or "")
    files = all_files(plan)

    R.mark_landed(name)

    report = V.wiring_gate(main_tree, name, files)
    content = V.content_gate_for(plan, ledger, agent_text)

    if report.ok and not content:
        lines = [staging_manifest(files), report.summary()]
        return True, lines

    failed = [r.line for r in report.failures] + content
    park(job_id, "N13", "the wiring or content gate refused the landing",
         persona, paths=failed)
    return False, failed + [revert_line(files, main_tree)]


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
