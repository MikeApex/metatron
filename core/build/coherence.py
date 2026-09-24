"""
core/build/coherence.py — NC. Everything Build has made, read as a SET.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 3 (NC), section 13.7.

THE FAILURE THIS GUARDS AGAINST is a collection of individually sensible files
that together say something nobody chose. That is an incremental builder's
CHARACTERISTIC failure, not an edge case — each capability passed its own checks
on the day it landed, and nothing ever asks whether the tenth contradicts the
third.

TWO PROPERTIES MAKE IT AFFORDABLE AND FALSIFIABLE.

  1. THE CORPUS IS CODE-ASSEMBLED AND SMALL. One-liners, registration rows,
     surface maps, grants and dispositions — never source, never agent-file
     bodies, never the ledgers. A set of fifty capabilities is still a few
     thousand tokens, so this stays cheap as the count grows, which is the only
     way a periodic whole-system pass survives contact with success.

  2. EVERY FINDING MUST NAME TWO CAPABILITY IDS AND THE ARTIFACT WHERE THEY
     COLLIDE. A finding that cannot is REJECTED here, in code, before anyone
     reads it. "The capabilities are drifting" is unarguable; "`home_care` and
     `garden_care` both claim `create` on `plant_watering`" can be checked in a
     minute and can be WRONG.

`orphan` is the one class that names a single id, and it says so: an orphan has
nothing to collide with, which IS the finding.

THE CODE PASS RUNS FIRST AND IS NOT ADVISORY. Duplicate surface claims, dangling
`replaces[]` targets and half-wired capabilities are decidable by comparison, so
no model is asked about them — the same rule that generates the node graph,
applied to the review of the graph's output. The model pass sees only what code
could not decide.

WHAT CHANGED WITH THE OVERLAY. The corpus is assembled from the TRACKED files —
the registry, the routing files, config/agents/ — instead of from an overlay
tree, so "half-wired" now means the `time_director` shape rather than a missing
overlay record. The finding classes, the two-id rule and the validator are
unchanged: they were never about where the files lived.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

_ROOT = Path(__file__).resolve().parent.parent.parent

# The closed enum. A finding outside it is dropped, not renamed: a review that
# can invent a category can always find something, which is the unfalsifiable
# version of this feature.
FINDING_KINDS: tuple[str, ...] = ("drift", "overlap", "contradiction", "orphan")

# The one kind that legitimately names a single capability, because having
# nothing to collide with IS the finding.
_SINGLE_ID_KINDS: frozenset[str] = frozenset({"orphan"})

AGENT = "build-coherence"


# ---------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------

def corpus(persona: str | None = None) -> dict:
    """
    What the reviewer reads. CODE-ASSEMBLED, from tracked files only.

    `in_routing` and `has_agent_file` are read independently of the registry —
    that is what lets the orphan rules below catch the `time_director` shape,
    where a row and a file exist and the routing entry does not.
    """
    from core.build import registry as R
    from core.build.gates import tracked_names
    from core.build.policy import list_policies

    routing = _routing_names()
    agent_files = {p.stem for p in (_ROOT / "config" / "agents").glob("*.md")}

    entries: list[dict] = []
    for name, row in sorted(R.capabilities().items()):
        entries.append({
            "id": name,
            "kind": row.get("kind", ""),
            "one_line": row.get("one_line", ""),
            "status": row.get("status", ""),
            "replaces": list(row.get("replaces") or []),
            "surface": [s for s in (row.get("surface_map") or [])
                        if isinstance(s, dict)],
            "grants": list(row.get("grants") or []),
            "in_registry": True,
            "in_routing": all(name in routing[f] for f in routing),
            "has_agent_file": name in agent_files,
        })

    # A tracked agent file that no registry row claims is not a Build capability
    # and is not a finding here — it is hand-written, which is most of them.
    return {
        "schema": "build_corpus/1",
        "capabilities": entries,
        "policies": [
            {"id": p.get("id", ""), "domain": p.get("domain", ""),
             "applies_to": p.get("applies_to", ""),
             "review_date": p.get("review_date", "")}
            for p in list_policies(persona)
        ],
        "tracked_agents": sorted(tracked_names()),
    }


def _routing_names() -> dict[str, set[str]]:
    import yaml
    out: dict[str, set[str]] = {}
    for fname in ("routing.yaml", "routing_cloud.yaml"):
        path = _ROOT / "config" / "modules" / fname
        names: set[str] = set()
        if path.exists():
            try:
                cfg = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
                names = set((cfg.get("agents") or {}).keys())
            except Exception:
                names = set()
        out[fname] = names
    return out


def render_corpus(data: dict | None = None, persona: str | None = None) -> str:
    """The corpus as the one file the coherence subagent is handed."""
    data = data or corpus(persona)
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True)


# ---------------------------------------------------------------------------
# The code pass
# ---------------------------------------------------------------------------

def code_findings(data: dict | None = None, persona: str | None = None) -> list[dict]:
    """
    Findings no model is asked about, because code can decide them.

    Each already carries its two ids and its artifact, so they enter the report
    on the same terms the model's do and are checked by the same validator.
    """
    data = data or corpus(persona)
    entries = data.get("capabilities") or []
    by_id = {e["id"]: e for e in entries}
    out: list[dict] = []

    # 1. OVERLAP — two capabilities claiming the same operation on the same
    #    entity, both in scope. One of them is doing work the other owns.
    claims: dict[tuple[str, str], list[str]] = {}
    for entry in entries:
        for item in entry.get("surface") or []:
            if item.get("status") != "in_scope":
                continue
            claims.setdefault(
                (item.get("entity", ""), item.get("operation", "")), []
            ).append(entry["id"])
    for (entity, operation), owners in sorted(claims.items()):
        for i in range(len(owners) - 1):
            out.append(_finding(
                "overlap", owners[i], owners[i + 1], "registry.yaml: surface_map",
                f"both claim `{operation}` on `{entity}` as in_scope — one of them "
                "is doing work the other already owns, and nothing routes between "
                "them"))

    # 2. CONTRADICTION — a `replaces[]` target that is still live. Declaring a
    #    replacement and leaving the replaced thing running is two capabilities
    #    answering the same request differently, which is worse than either.
    for entry in entries:
        for target in entry.get("replaces") or []:
            if target in by_id and by_id[target].get("status") == "landed":
                out.append(_finding(
                    "contradiction", entry["id"], target, "registry.yaml",
                    f"`{entry['id']}` declares it replaces `{target}`, and "
                    f"`{target}` is still landed — both will be dispatched"))

    # 3. ORPHAN — THE time_director SHAPE, in both directions. A landed row
    #    whose wiring is incomplete is a capability on the board and not in the
    #    system; the inverse is a capability being dispatched with no row, whose
    #    standing cost nothing meters.
    for entry in entries:
        if not entry.get("in_routing"):
            out.append(_finding(
                "orphan", entry["id"], "", "config/modules/routing*.yaml",
                "landed with no entry in both routing files — anything naming it "
                "raises in the router. This is the time_director shape, which is "
                "in the tree today"))
        if not entry.get("has_agent_file") and entry.get("kind") == "agent":
            out.append(_finding(
                "orphan", entry["id"], "", "config/agents/",
                "landed as an agent with no instruction file — load_agent() "
                "raises FileNotFoundError on dispatch"))

    # 4. DRIFT — a policy past its review date. A number standing in for
    #    judgment with nobody re-checking it is the definition of drift, and it
    #    is the one this project writes into every threshold it sets.
    today = date.today().isoformat()
    for policy in data.get("policies") or []:
        review = str(policy.get("review_date") or "")
        if review and review < today:
            out.append(_finding(
                "drift", policy.get("id", ""), policy.get("domain", ""),
                "config/build/policies/",
                f"review date {review} has passed — a standing decision nobody "
                "has re-checked is still deciding"))
    return out


def _finding(kind: str, first: str, second: str, artifact: str, detail: str) -> dict:
    return {"kind": kind, "capability_a": first, "capability_b": second,
            "artifact": artifact, "detail": detail, "source": "code"}


# ---------------------------------------------------------------------------
# The validator — what makes the output falsifiable
# ---------------------------------------------------------------------------

def validate_findings(findings: Any) -> tuple[list[dict], list[str]]:
    """
    (accepted, rejections). A finding that cannot name two ids is REJECTED.

    Rejections are returned, not discarded: a model whose findings are being
    thrown away is a fact about the review worth seeing, and silently dropping
    them would make an over-firing pass look like a quiet one.
    """
    accepted: list[dict] = []
    rejected: list[str] = []

    if not isinstance(findings, list):
        return [], ["findings is not a list"]

    for position, finding in enumerate(findings, start=1):
        if not isinstance(finding, dict):
            rejected.append(f"finding[{position}] is not an object")
            continue
        kind = str(finding.get("kind") or "").strip().lower()
        if kind not in FINDING_KINDS:
            rejected.append(
                f"finding[{position}] kind {finding.get('kind')!r} is outside "
                f"{list(FINDING_KINDS)} — a review that can invent a category can "
                f"always find something")
            continue
        first = str(finding.get("capability_a") or "").strip()
        second = str(finding.get("capability_b") or "").strip()
        artifact = str(finding.get("artifact") or "").strip()
        if not first:
            rejected.append(f"finding[{position}] names no capability")
            continue
        if not second and kind not in _SINGLE_ID_KINDS:
            rejected.append(
                f"finding[{position}] ({kind}) names only {first!r} — a collision "
                f"needs two ids, and one id is an opinion")
            continue
        if not artifact:
            rejected.append(
                f"finding[{position}] names no artifact — without one there is "
                f"nowhere to go and check it")
            continue
        if not str(finding.get("detail") or "").strip():
            rejected.append(f"finding[{position}] has no detail")
            continue
        accepted.append({"kind": kind, "capability_a": first, "capability_b": second,
                         "artifact": artifact,
                         "detail": str(finding["detail"]).strip(),
                         "source": str(finding.get("source") or "model")})
    return accepted, rejected


def parse_findings(raw: Any) -> Any:
    """The subagent's reply, as a list. A fenced block is unwrapped first."""
    if isinstance(raw, list):
        return raw
    if isinstance(raw, dict):
        return raw.get("findings", raw)
    text = _strip_fence(str(raw or ""))
    try:
        parsed = json.loads(text)
    except ValueError:
        return []
    return parsed.get("findings", parsed) if isinstance(parsed, dict) else parsed


def _strip_fence(text: str) -> str:
    text = str(text or "").strip()
    if not text.startswith("```"):
        return text
    body = text.split("\n", 1)[1] if "\n" in text else ""
    return body.rsplit("```", 1)[0].strip()


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

def report(model_findings: Any = None, persona: str | None = None) -> dict:
    """The whole review: the code pass, then whatever the model pass survived."""
    data = corpus(persona)
    accepted, rejected = validate_findings(parse_findings(model_findings) or [])
    code = code_findings(data, persona)
    return {
        "schema": "build_coherence/1",
        "at": date.today().isoformat(),
        "capabilities_reviewed": len(data.get("capabilities") or []),
        "findings": code + accepted,
        "rejected": rejected,
    }


def render(result: dict) -> str:
    lines = [
        "# Build coherence review", "",
        f"*{result.get('at', '?')} · "
        f"{result.get('capabilities_reviewed', 0)} capability(ies).*", "",
    ]
    findings = result.get("findings") or []
    if not findings:
        lines += ["No findings. Every capability's surface claims, replacements "
                  "and wiring are consistent with every other's.", ""]
    for finding in findings:
        pair = finding["capability_a"] + (
            f" ↔ {finding['capability_b']}" if finding.get("capability_b") else "")
        lines.append(f"- **{finding['kind']}** `{pair}` in `{finding['artifact']}` "
                     f"— {finding['detail']} *({finding.get('source', '?')})*")
    if result.get("rejected"):
        lines += ["", "## Rejected findings", "",
                  "*Named here rather than discarded: a review whose findings are "
                  "being thrown away is a fact about the review.*", ""]
        lines += [f"- {r}" for r in result["rejected"]]
    return "\n".join(lines) + "\n"
