"""
core/build/coherence.py — NC. Everything Build has made, read as a SET.

THE FAILURE THIS GUARDS AGAINST is a collection of individually sensible files
that together say something nobody chose. That is an incremental builder's
CHARACTERISTIC failure, not an edge case — each capability passed its own checks
on the day it landed, and nothing ever asks whether the tenth contradicts the
third. Standing requirement 2 of plan section 1.

TWO PROPERTIES MAKE IT AFFORDABLE AND FALSIFIABLE — section 13.7's answer to
"the coherence review is expensive and unfalsifiable".

  1. THE CORPUS IS CODE-ASSEMBLED AND SMALL. One-liners, file lists,
     registration rows, surface maps, grants and dispositions — never source,
     never agent-file bodies, never the ledgers. A set of fifty capabilities is
     still a few thousand tokens, so this stays cheap as the count grows, which
     is the only way a periodic whole-system pass survives contact with success.

  2. EVERY FINDING MUST NAME TWO CAPABILITY IDS AND THE ARTIFACT WHERE THEY
     COLLIDE. A finding that cannot is REJECTED here, in code, before anyone
     reads it. That is what makes the output falsifiable: "the capabilities are
     drifting" is unarguable, and "`home_care` and `garden_care` both claim
     `create` on `plant_watering` in their surface maps" can be checked in a
     minute and can be WRONG.

`orphan` is the one finding class that names one id, and it says so: an orphan
has nothing to collide with, which is the finding. It names the id and the
artifact that should have referenced it and does not.

THE CODE PASS RUNS FIRST AND IS NOT ADVISORY. Duplicate surface claims, dangling
`replaces[]` targets and capabilities absent from the overlay are all decidable
by comparison, so no model is asked about them — the same rule that generates
the node graph, applied to the review of the graph's output. The model pass sees
only what code could not decide.

Plan: archive/plans/build_vertical_plan_2026-09-18.md section 1 (requirement 2),
section 3 (NC), section 13.7
"""

from __future__ import annotations

import json
from datetime import date
from typing import Any

# The closed enum. A finding outside it is dropped, not renamed: a review that
# can invent a category can always find something, which is the unfalsifiable
# version of this feature.
FINDING_KINDS: tuple[str, ...] = ("drift", "overlap", "contradiction", "orphan")

# The one kind that legitimately names a single capability, because having
# nothing to collide with IS the finding.
_SINGLE_ID_KINDS: frozenset[str] = frozenset({"orphan"})

AGENT = "build_coherence"


# ---------------------------------------------------------------------------
# The corpus
# ---------------------------------------------------------------------------

def corpus(persona: str | None = None) -> dict:
    """
    What Build has produced, as a comparable set. Code-assembled, no model.

    Reads the REGISTRY for what landed and the OVERLAY for what is live, and
    reports the difference rather than trusting either — a capability in one and
    not the other is exactly the half-wired state the single record exists to
    prevent, and it is cheaper to notice here than at a dispatch.
    """
    from core.build import overlay as O
    from core.build import policy as P
    from core.build import registry as R

    registered = R.capabilities(persona)
    records = O.records_for(persona)
    policies = P.list_policies(persona)

    entries: list[dict] = []
    for name in sorted(set(registered) | set(records)):
        row = registered.get(name) or {}
        record = records.get(name) or {}
        routing = (record.get("routing") or {}).get("local") or {}
        entries.append({
            "id": name,
            "kind": row.get("kind") or ("agent" if record else ""),
            "disposition": row.get("disposition", ""),
            "theme": row.get("theme") or "",
            "one_line": row.get("one_line", ""),
            "version": row.get("version"),
            "job_id": row.get("job_id", ""),
            "files": row.get("files") or [],
            "replaces": row.get("replaces") or [],
            "display_name": record.get("display_name", ""),
            "grants": sorted(routing.get("allowed_tools") or []),
            "knowledge_domains": sorted(record.get("knowledge_domains") or []),
            "execution_mode": (record.get("execution_mode")
                               or (row.get("run") or {}).get("execution_mode", "")),
            "surface": _surface_of(row, record),
            "in_registry": name in registered,
            "in_overlay": name in records,
        })

    return {
        "schema": "coherence_corpus/1",
        "generated_at": date.today().isoformat(),
        "capabilities": entries,
        "policies": [{"id": p.get("id", ""), "domain": p.get("domain", ""),
                      "applies_to": p.get("applies_to", ""),
                      "review_date": p.get("review_date", ""),
                      "job_id": p.get("job_id", "")}
                     for p in policies],
        "counts": {"capabilities": len(entries), "policies": len(policies)},
    }


def _surface_of(row: dict, record: dict) -> list[dict]:
    """{entity, operation, status} triples, the comparable part of a surface map."""
    raw = row.get("surface_map") or record.get("surface_map") or []
    out = []
    for item in raw:
        if isinstance(item, dict) and item.get("entity") and item.get("operation"):
            out.append({"entity": str(item["entity"]),
                        "operation": str(item["operation"]),
                        "status": str(item.get("status") or "")})
    return out


def render_corpus(data: dict | None = None, persona: str | None = None) -> str:
    """The corpus as the compact text the agent reads. Never source."""
    data = data or corpus(persona)
    return json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False)


# ---------------------------------------------------------------------------
# The code pass — everything decidable by comparison
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
    #    entity, both in scope. The registry's own duplicate-work detector.
    claims: dict[tuple[str, str], list[str]] = {}
    for entry in entries:
        for item in entry.get("surface") or []:
            if item.get("status") != "in_scope":
                continue
            claims.setdefault((item["entity"], item["operation"]), []).append(entry["id"])
    for (entity, operation), owners in sorted(claims.items()):
        if len(owners) < 2:
            continue
        for i in range(len(owners) - 1):
            out.append(_finding(
                "overlap", owners[i], owners[i + 1], "surface_map",
                f"both claim `{operation}` on `{entity}` as in_scope — one of them "
                f"is doing work the other already owns, and nothing routes between them"))

    # 2. CONTRADICTION — a `replaces[]` target that is still live. Declaring a
    #    replacement and leaving the replaced thing running is two capabilities
    #    answering the same request differently, which is worse than either.
    for entry in entries:
        for target in entry.get("replaces") or []:
            if target in by_id and by_id[target].get("in_overlay"):
                out.append(_finding(
                    "contradiction", entry["id"], target, "registry.jsonl",
                    f"`{entry['id']}` declares it replaces `{target}`, and `{target}` "
                    f"is still live in the overlay — both will be dispatched"))

    # 3. ORPHAN — landed and not loadable, or loadable and unregistered. The
    #    half-wired state in both directions.
    for entry in entries:
        if entry.get("in_registry") and not entry.get("in_overlay"):
            out.append(_finding(
                "orphan", entry["id"], "", "overlay/capabilities/",
                "registered as landed with no overlay record — nothing can load it, "
                "so it is a capability on the board and not in the system"))
        elif entry.get("in_overlay") and not entry.get("in_registry"):
            out.append(_finding(
                "orphan", entry["id"], "", "registry.jsonl",
                "live in the overlay with no registry row — it is dispatched and its "
                "standing cost is unmetered, which is the row the sweep exists to require"))

    # 4. DRIFT — a policy past its review date. A number standing in for
    #    judgment with nobody re-checking it is the definition of drift, and it
    #    is the one this project writes into every threshold it sets.
    today = date.today().isoformat()
    for policy in data.get("policies") or []:
        review = str(policy.get("review_date") or "")
        if review and review < today:
            out.append(_finding(
                "drift", policy.get("id", ""), policy.get("domain", ""), "build/policies/",
                f"review date {review} has passed — a standing decision nobody has "
                f"re-checked is still deciding"))
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


# ---------------------------------------------------------------------------
# The review
# ---------------------------------------------------------------------------

def review(persona: str | None = None, use_model: bool = True) -> dict:
    """
    One coherence pass. Returns {corpus_counts, findings, rejected, model_ran}.

    The code pass ALWAYS runs. The model pass is skipped when there is nothing
    for it to judge — fewer than two capabilities cannot collide, so calling a
    model to confirm that would be paying for an answer arithmetic already gave.

    Never raises. A coherence review that takes down a tick would make the
    periodic pass the most dangerous thing in the package, which is the exact
    inversion of its job.
    """
    data = corpus(persona)
    findings = code_findings(data)
    rejected: list[str] = []
    model_ran = False

    if use_model and len(data.get("capabilities") or []) >= 2:
        try:
            raw = _ask_model(data, persona)
            accepted, rejected = validate_findings(raw)
            findings.extend(accepted)
            model_ran = True
        except Exception as exc:
            rejected.append(f"model pass unavailable: {type(exc).__name__}: {exc}")

    return {
        "generated_at": data.get("generated_at"),
        "counts": data.get("counts"),
        "findings": findings,
        "rejected": rejected,
        "model_ran": model_ran,
    }


def _ask_model(data: dict, persona: str | None) -> Any:
    """
    The one model call. Output is parsed through the orchestrator's own repair
    ladder, then handed to validate_findings() — never trusted as shaped.
    """
    from core.orchestrator import _run_single_agent

    prompt = (
        "Below is every capability Build has produced, as a set. Read them "
        "TOGETHER and report only what their combination says that no single one "
        "does.\n\n"
        'Return a JSON OBJECT of the form {"findings": [...]}. Each finding '
        f"needs: kind (one of {list(FINDING_KINDS)}), capability_a, capability_b "
        "(required except for orphan), artifact (where they collide), detail.\n\n"
        "A finding that cannot name two capability ids will be rejected before "
        "anyone reads it. Report nothing rather than reaching for something — "
        'an empty {"findings": []} is a complete answer.\n\n'
        f"{render_corpus(data)}"
    )
    raw = _run_single_agent(AGENT, prompt, persona=persona)
    return _parse_findings(raw)


def _parse_findings(raw: Any) -> Any:
    """
    The reply, as a list of findings — whatever shape it arrived in.

    THE BARE LIST IS TRIED FIRST, AND THAT ORDER IS THE FIX. The prompt used to
    ask for "a JSON list", and `repair_json` — built for the orchestrator's
    context blocks, which are objects — extracts the first `{…}` it finds. Given
    a list of findings it returned the FIRST FINDING as a dict, `.get("findings")`
    was None, and every well-formed reply was rejected as "findings is not a
    list" with `model_ran: True` beside it. The board read as a review that had
    run and found nothing, which is the most expensive way to be wrong here.
    The prompt now asks for an object AND both shapes are accepted, because the
    parser must not depend on a model following a format instruction.
    """
    if isinstance(raw, (list, dict)):
        parsed: Any = raw
    else:
        text = str(raw or "").strip()
        parsed = None
        try:
            parsed = json.loads(_strip_fence(text))
        except ValueError:
            # repair_json lives in core.build.schemas and reaches into
            # core.orchestrator, which is heavy — imported here rather than at
            # module scope so a coherence pass that parses cleanly (every
            # ordinary one) never loads it.
            try:
                from core.build.schemas import repair_json
                parsed, _how = repair_json(text)
            except Exception:
                parsed = None
    if isinstance(parsed, dict):
        return parsed.get("findings", [])
    return parsed if isinstance(parsed, list) else []


def _strip_fence(text: str) -> str:
    """```json … ``` -> … . Cheaper than a repair pass and the common case."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    body = stripped.split("\n", 1)[-1]
    return body.rsplit("```", 1)[0].strip()


def render(report: dict) -> str:
    """The review as the board prints it."""
    counts = report.get("counts") or {}
    lines = [
        f"coherence — {counts.get('capabilities', 0)} capability(ies), "
        f"{counts.get('policies', 0)} policy(ies), "
        f"model {'ran' if report.get('model_ran') else 'not run'}",
    ]
    findings = report.get("findings") or []
    if not findings:
        lines.append("  no findings")
    for finding in findings:
        pair = finding["capability_a"] + (
            f" ↔ {finding['capability_b']}" if finding.get("capability_b") else "")
        lines.append(f"  [{finding['kind']}] {pair} in {finding['artifact']}"
                     f" ({finding.get('source', 'model')})")
        lines.append(f"      {finding['detail']}")
    for rejection in report.get("rejected") or []:
        lines.append(f"  (rejected) {rejection}")
    return "\n".join(lines)
