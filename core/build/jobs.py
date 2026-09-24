"""
core/build/jobs.py — the job directory on the Mac, and the two things in it.

Plan: archive/plans/build_vertical_plan_2026-09-24.md sections 3, 5.

    data/build/jobs/<persona>/BLD-MMDD-NN/
        question_set.json  answer_ledger.json  build_plan.v1.json  review.json
        question_table.md  brief.md  implementation.patch
        attempts.jsonl

THERE IS NO LEDGER AND NO STATE MACHINE HERE. v3 had seventeen states replayed
from an append-only ledger because a 30-minute tick had to rediscover where
every job was. Build now runs in a session Mike is sitting in, so the only state
a lost session needs is WHICH NODES HAVE PRODUCED OUTPUT — and the artifacts on
disk are that, exactly. `/build BLD-…` re-entered finds them present and skips
those nodes. The artifact IS the resume cursor (salvaged rule, section 10).

PERSONA-QUALIFIED EVERYWHERE (cold read 5). Ticket ids are allocated per persona
ledger on the VM, so two personas can mint the same BLD-MMDD-NN on one day. If
the job directory were not persona-qualified, the second one would resume into
the first one's artifacts and build the wrong capability from a valid-looking
cursor. `/build` takes `--persona`, defaulting to `mike`, and a fixture
persona's tickets are never built unless that persona is named.

WHY attempts.jsonl EXISTS, given the artifacts (v4.2 residual). A node that
FAILED wrote no artifact, so the artifacts alone cannot count a retry — and the
driver's two hard bounds are counts: one retry per node, one send-back per
review. Held in memory they reset on exactly the crash that makes a job
expensive. So the driver appends one row BEFORE it names a step, and re-derives
every bound from this file. It is a counter, not a state machine: nothing reads
it to decide WHERE a job is, only how many times something has been tried.

THIS IS THE FIRST PERSONA-DERIVED DATA THE MAC HOLDS BY DESIGN. Ruling 10 covers
it: gitignored under data/build/, and the standing rule that persona CONFIG is
VM-owned is untouched — nothing here is loaded by the runtime.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent.parent

DEFAULT_PERSONA = "mike"

_PERSONA_RE = re.compile(r"^[a-z][a-z0-9_]{1,31}$")
_ARTIFACT_RE = re.compile(r"^[a-z][a-z0-9_.]{0,47}$")

# The artifact each node produces, in node order. The driver reads this to
# decide the next step; nothing else defines "has this node run".
ARTIFACTS: dict[str, str] = {
    "N1r": "dossier",
    "N2": "question_set",
    "N4": "answer_ledger",
    "N5": "ledger_check",
    "N7": "build_plan",
    "N10": "brief",
    "N8": "review",
    "N11": "implementation",
    "N12": "gates",
    "N13": "landing",
    "N14": "acceptance",
}


class JobError(RuntimeError):
    """A job directory could not be read or written."""


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

def jobs_root() -> Path:
    """data/build/jobs/ — gitignored, one new line in .gitignore."""
    return _ROOT / "data" / "build" / "jobs"


def index_root() -> Path:
    """data/build/index/ — Build's own FAISS store, relocated to the Mac."""
    return _ROOT / "data" / "build" / "index"


def resolve_persona(persona: str | None = None) -> str:
    """
    The persona a job belongs to. Defaults to `mike`.

    CASE IS FOLDED; NOTHING ELSE IS. Folding is the safe direction — `Mike` and
    `mike` are the same person, and on a case-insensitive filesystem (which this
    one is) refusing `Mike` while `mike/` and `Mike/` would land in the same
    directory anyway buys nothing. Every OTHER malformation is REFUSED rather
    than cleaned: a name with a slash or a `..` in it is not a typo, and
    quietly rewriting one would put a job in a directory its caller did not name.
    """
    name = str(persona or DEFAULT_PERSONA).strip().lower()
    if not _PERSONA_RE.match(name):
        raise JobError(f"Invalid persona {persona!r} — must match {_PERSONA_RE.pattern}")
    return name


def persona_dir(persona: str | None = None) -> Path:
    return jobs_root() / resolve_persona(persona)


def job_dir(job_id: str, persona: str | None = None) -> Path:
    from core.build.ids import is_job_id
    if not is_job_id(job_id):
        raise JobError(f"Not a Build job id: {job_id!r}")
    return persona_dir(persona) / job_id


# Artifact names that already carry their own extension. Everything else gets
# `.json` appended.
#
# ENUMERATED, NOT INFERRED FROM "does the name contain a dot". That heuristic
# was here for one commit and it silently broke the versioned plan files:
# `build_plan.v1` contains a dot, so it was written with NO extension, and
# plan_versions() — which globs `build_plan.v*.json` and IS the send-back
# counter — found nothing. The review's one send-back would have been
# unbounded, and every symptom would have pointed at the driver.
_KNOWN_SUFFIXES: tuple[str, ...] = (".json", ".md", ".patch", ".jsonl")


def artifact_path(job_id: str, name: str, persona: str | None = None) -> Path:
    name = str(name or "")
    if not _ARTIFACT_RE.match(name):
        raise JobError(f"Invalid artifact name {name!r}")
    suffix = "" if name.endswith(_KNOWN_SUFFIXES) else ".json"
    return job_dir(job_id, persona) / f"{name}{suffix}"


def attempts_path(job_id: str, persona: str | None = None) -> Path:
    return job_dir(job_id, persona) / "attempts.jsonl"


def ensure(job_id: str, persona: str | None = None) -> Path:
    directory = job_dir(job_id, persona)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def known_jobs(persona: str | None = None) -> list[str]:
    """Job ids with a directory on disk, newest id first."""
    directory = persona_dir(persona)
    if not directory.is_dir():
        return []
    from core.build.ids import is_job_id
    return sorted((p.name for p in directory.iterdir()
                   if p.is_dir() and is_job_id(p.name)), reverse=True)


# ---------------------------------------------------------------------------
# Artifacts — the resume cursor
# ---------------------------------------------------------------------------

def write_artifact(job_id: str, name: str, payload: dict,
                   persona: str | None = None) -> Path:
    """
    Write one artifact atomically: temp file in the same directory, then
    os.replace(). A reader sees the whole old file or the whole new one, never
    a half-written prefix — which is what lets read_artifact() be trusted as a
    "this node already ran" signal after a kill -9.
    """
    path = artifact_path(job_id, name, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    return _atomic_write(path, json.dumps(payload, indent=2, ensure_ascii=False))


def write_text(job_id: str, name: str, text: str,
               persona: str | None = None) -> Path:
    """The same guarantee for a rendered file — the table, the brief, the patch."""
    path = artifact_path(job_id, name, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    return _atomic_write(path, text)


def _atomic_write(path: Path, text: str) -> Path:
    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(text, encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


def read_artifact(job_id: str, name: str,
                  persona: str | None = None) -> dict | None:
    """
    The artifact if present and parseable, else None.

    None means "this node has not produced valid output", which is exactly the
    condition for running it. A present-but-unparseable file returns None too:
    it cannot have come from os.replace() of a complete write, so it is debris.
    """
    path = artifact_path(job_id, name, persona)
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


def read_text(job_id: str, name: str, persona: str | None = None) -> str | None:
    path = artifact_path(job_id, name, persona)
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def has_artifact(job_id: str, name: str, persona: str | None = None) -> bool:
    return read_artifact(job_id, name, persona) is not None


def plan_versions(job_id: str, persona: str | None = None) -> list[Path]:
    """
    Every `build_plan.v*.json` on disk, ascending.

    THE SEND-BACK COUNT IS len() OF THIS. A review that sends a plan back makes
    the Planner write v2; a second send-back would make v3, and the driver parks
    instead. Counting files rather than holding a number is what makes the bound
    survive a lost session (section 3).
    """
    directory = job_dir(job_id, persona)
    if not directory.is_dir():
        return []
    return sorted(directory.glob("build_plan.v*.json"),
                  key=lambda p: _version_of(p.name))


def _version_of(filename: str) -> int:
    match = re.search(r"\.v(\d+)\.json$", filename)
    return int(match.group(1)) if match else 0


def latest_plan(job_id: str, persona: str | None = None) -> dict | None:
    versions = plan_versions(job_id, persona)
    if not versions:
        return None
    try:
        parsed = json.loads(versions[-1].read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


def next_plan_name(job_id: str, persona: str | None = None) -> str:
    return f"build_plan.v{len(plan_versions(job_id, persona)) + 1}.json"


def write_plan(job_id: str, plan: dict, persona: str | None = None) -> Path:
    """
    Write the next plan VERSION. The only supported way to land a plan.

    Exists so no caller has to know the naming rule: the version number is the
    send-back count, so a caller that invented its own name — or stripped the
    extension — would be silently editing the review's bound.
    """
    return write_artifact(job_id, next_plan_name(job_id, persona), plan, persona)


# ---------------------------------------------------------------------------
# attempts.jsonl — the durable counters
# ---------------------------------------------------------------------------

def record_attempt(job_id: str, node: str, attempt: int, outcome: str,
                   defects: list[str] | None = None,
                   persona: str | None = None) -> dict:
    """
    One attempt row, appended BEFORE the step is named (section 3).

    Before, not after, and that ordering is the whole point: a process killed
    mid-node has already recorded that the node was attempted, so the restart
    counts it. Recording afterwards would make a crash free.
    """
    row = {
        "at": datetime.now().isoformat(timespec="seconds"),
        "node": str(node),
        "attempt": int(attempt),
        "outcome": str(outcome),
        "defects": list(defects or []),
    }
    path = attempts_path(job_id, persona)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
        handle.flush()
        os.fsync(handle.fileno())
    try:
        os.chmod(path, 0o600)
    except OSError:
        pass
    return row


def attempts(job_id: str, persona: str | None = None) -> list[dict]:
    """Every attempt row. A torn line is skipped, never fatal."""
    path = attempts_path(job_id, persona)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and row.get("node"):
            out.append(row)
    return out


def attempts_for(job_id: str, node: str, persona: str | None = None) -> int:
    """
    How many times `node` has been STARTED — including the ones that wrote
    nothing, which is the case the artifacts alone cannot see (finding 1).
    """
    return sum(1 for row in attempts(job_id, persona)
               if str(row.get("node")) == str(node))


def failures_for(job_id: str, node: str, persona: str | None = None) -> int:
    return sum(1 for row in attempts(job_id, persona)
               if str(row.get("node")) == str(node)
               and str(row.get("outcome")) in {"failed", "rejected"})


def last_defects(job_id: str, node: str,
                 persona: str | None = None) -> list[str]:
    """The defect list from the most recent failed attempt at `node`."""
    for row in reversed(attempts(job_id, persona)):
        if str(row.get("node")) == str(node) and row.get("defects"):
            return [str(d) for d in row["defects"]]
    return []
