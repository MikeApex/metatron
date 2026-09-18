"""
core/build/policy.py — standing decision frameworks.

`kind: policy` is a first-class Build output and often the right one. The
reference transcript's own conclusion is the general case: *"the actual
first-day deliverable is not an RSVP; it's the beginning of a standing
allocation policy."*

WHAT A POLICY IS ACTUALLY FOR: capabilities that improve with use. A tool that
consults an accumulating policy gets better at its job the more often it runs —
the policy is where the corrections, the standing commitments and the automatic
yeses and noes accrete. Making Inquiry cheaper and `depth: triage` possible is
a SIDE EFFECT of that, not the purpose. A capability without a policy behind it
performs identically on its thousandth run as on its first, which for anything
exercising judgment is a defect.

Every policy carries a `review_date`, for the same reason every threshold in
this project does: a number standing in for judgment needs an owner and a
re-check date.

STORAGE. One file per policy under data/personas/{p}/build/policies/, written
atomically. Persona-scoped, gitignored, inside the existing backup tar, and
inside the writer's allow-roots. They enter the capability manifest, so
settle.py resolves against them before touching data.
"""

from __future__ import annotations

import json
import os
import re
import tempfile
from datetime import date
from pathlib import Path

_POLICY_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,47}$")


class PolicyError(RuntimeError):
    """A policy could not be read or written."""


def policies_dir(persona: str | None = None) -> Path:
    from core.build.jobs import build_dir
    return build_dir(persona) / "policies"


def policy_path(policy_id: str, persona: str | None = None) -> Path:
    if not _POLICY_ID_RE.match(str(policy_id or "")):
        raise PolicyError(
            f"Invalid policy id {policy_id!r} — must match {_POLICY_ID_RE.pattern}"
        )
    return policies_dir(persona) / f"{policy_id}.json"


def list_policies(persona: str | None = None) -> list[dict]:
    """
    Every policy on file, sorted by id. A malformed file is skipped, not fatal
    — one bad policy must not hide the rest from the manifest.
    """
    directory = policies_dir(persona)
    if not directory.is_dir():
        return []
    out: list[dict] = []
    for path in sorted(directory.glob("*.json")):
        try:
            parsed = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        if isinstance(parsed, dict) and parsed.get("id"):
            out.append(parsed)
    return out


def read_policy(policy_id: str, persona: str | None = None) -> dict | None:
    path = policy_path(policy_id, persona)
    if not path.exists():
        return None
    try:
        parsed = json.loads(path.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        return None
    return parsed if isinstance(parsed, dict) else None


def write_policy(policy: dict, job_id: str, persona: str | None = None,
                 version: int = 1) -> Path:
    """
    Store a policy record. Validated against the same block the BuildPlan
    validator checks, so a policy cannot be written that a plan could not
    declare.
    """
    from core.build.schemas import _check_policy

    defects: list[str] = []
    _check_policy(policy, defects)
    if defects:
        raise PolicyError("; ".join(defects))

    record = {
        **policy,
        "schema": "build_policy/1",
        "job_id": job_id,
        "version": int(version),
        "written_at": date.today().isoformat(),
    }
    path = policy_path(record["id"], persona)
    path.parent.mkdir(parents=True, exist_ok=True)

    fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), prefix=path.name + ".",
                                    suffix=".tmp")
    os.close(fd)
    tmp = Path(tmp_name)
    try:
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False),
                       encoding="utf-8")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return path


# ---------------------------------------------------------------------------
# Resolution — what makes depth: triage possible
# ---------------------------------------------------------------------------

def due_for_review(persona: str | None = None,
                   today: date | None = None) -> list[dict]:
    """
    Policies whose review_date has passed.

    A review date is not a deadline: on that date, check whether the policy
    still describes the decision. If it does, push the date — do not silently
    drop it, which is how a standing rule outlives the reasoning behind it.
    """
    when = today or date.today()
    out = []
    for policy in list_policies(persona):
        raw = str(policy.get("review_date") or "").strip()
        try:
            if date.fromisoformat(raw) <= when:
                out.append(policy)
        except ValueError:
            continue
    return out


def resolve(question_text: str, question_class: str = "",
            persona: str | None = None,
            min_score: float = 0.62) -> dict | None:
    """
    The policy that already answers this question, or None.

    TWO PATHS, IN THIS ORDER, AND THE ORDER IS THE POINT.

    1. `retires_question_classes` — a policy that declares it retires a whole
       class retires it outright. This is exact, free, and the mechanism behind
       "every policy a prior run produced retires a class of question
       permanently."
    2. Semantic match against `applies_to`, through Build's own index. Needs an
       encoder, so it is second and it is optional: with no index available the
       class path still works and the residue simply reaches the Librarian,
       which is the correct-but-more-expensive outcome rather than a failure.
    """
    candidates = list_policies(persona)
    if not candidates:
        return None

    klass = str(question_class or "").strip().lower()
    if klass:
        for policy in candidates:
            retired = [
                str(c).strip().lower()
                for c in policy.get("retires_question_classes") or []
            ]
            if klass in retired:
                return {**policy, "_match": "class", "_score": 1.0}

    try:
        from core.build.index import nearest_policy
        hit = nearest_policy(question_text, persona)
    except Exception:
        return None
    if hit and hit.get("score", 0.0) >= min_score:
        policy = read_policy(hit["policy_id"], persona)
        if policy:
            return {**policy, "_match": "semantic", "_score": hit["score"]}
    return None
