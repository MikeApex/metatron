"""
tests/test_build_coherence.py — the set review, and what makes it falsifiable.

Plan section 3 (NC), section 13.7.

THE PROPERTY UNDER TEST is not "does the review find things". It is that a
finding which cannot name two capability ids and an artifact is REJECTED — in
code, before anyone reads it. "The capabilities are drifting" is unarguable;
"`home_care` and `garden_care` both claim `create` on `watering`" can be checked
in a minute and can be WRONG. The second is worth having precisely because it
can be wrong.

AND that the code pass runs FIRST and is not advisory. Duplicate surface claims,
dangling `replaces[]` targets and half-wired capabilities are decidable by
comparison, so no model is asked about them.

Usage:
    python3 tests/test_build_coherence.py
"""

import shutil
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import coherence as C                    # noqa: E402
from tests.support.runner import Suite, hit              # noqa: E402

suite = Suite("build coherence")
check = suite.check

_TMP = Path(tempfile.mkdtemp(prefix="build-coherence-"))


def cap(cap_id: str, **overrides) -> dict:
    entry = {
        "id": cap_id, "kind": "agent", "one_line": f"{cap_id} does things",
        "status": "landed", "replaces": [], "surface": [], "grants": [],
        "in_registry": True, "in_routing": True, "has_agent_file": True,
    }
    entry.update(overrides)
    return entry


def claim(entity: str, operation: str, status: str = "in_scope") -> dict:
    return {"entity": entity, "operation": operation, "status": status}


def corpus(*caps: dict, policies: list | None = None) -> dict:
    return {"schema": "build_corpus/1", "capabilities": list(caps),
            "policies": policies or [], "tracked_agents": []}


# ---------------------------------------------------------------------------
# The code pass
# ---------------------------------------------------------------------------

@check("a consistent set produces NO findings")
def _():
    data = corpus(cap("home_care", surface=[claim("watering", "create")]),
                  cap("garden_care", surface=[claim("mowing", "create")]))
    assert C.code_findings(data) == []


@check("two capabilities claiming the same operation on the same entity OVERLAP")
def _():
    data = corpus(cap("home_care", surface=[claim("watering", "create")]),
                  cap("garden_care", surface=[claim("watering", "create")]))
    findings = C.code_findings(data)
    assert len(findings) == 1, findings
    assert findings[0]["kind"] == "overlap"
    assert {findings[0]["capability_a"], findings[0]["capability_b"]} == {
        "home_care", "garden_care"}


@check("a claim that is NOT in_scope does not collide")
def _():
    data = corpus(cap("home_care", surface=[claim("watering", "create")]),
                  cap("garden_care", surface=[
                      claim("watering", "create", "not_applicable")]))
    assert C.code_findings(data) == [], (
        "a capability that explicitly declines an operation is the opposite of "
        "one that claims it")


@check("a `replaces[]` target that is still landed is a CONTRADICTION")
def _():
    data = corpus(cap("home_care", replaces=["garden_care"]), cap("garden_care"))
    findings = [f for f in C.code_findings(data) if f["kind"] == "contradiction"]
    assert len(findings) == 1, findings
    assert "both will be dispatched" in findings[0]["detail"]


@check("a `replaces[]` target that is gone is not a finding")
def _():
    data = corpus(cap("home_care", replaces=["retired_thing"]))
    assert [f for f in C.code_findings(data) if f["kind"] == "contradiction"] == []


@check("a landed capability missing from the routing files is an ORPHAN")
def _():
    data = corpus(cap("home_care", in_routing=False))
    findings = [f for f in C.code_findings(data) if f["kind"] == "orphan"]
    assert len(findings) == 1, findings
    assert "time_director shape" in findings[0]["detail"], (
        "this is the defect that is in the tree TODAY — the finding should say "
        f"so: {findings[0]}")


@check("a landed AGENT with no instruction file is an ORPHAN")
def _():
    data = corpus(cap("home_care", has_agent_file=False))
    findings = [f for f in C.code_findings(data) if f["kind"] == "orphan"]
    assert any("FileNotFoundError" in f["detail"] for f in findings), findings


@check("a landed TOOL with no instruction file is NOT an orphan")
def _():
    data = corpus(cap("home_care", kind="tool", has_agent_file=False))
    assert [f for f in C.code_findings(data) if "FileNotFound" in f["detail"]] == []


@check("a policy past its review date is DRIFT")
def _():
    past = (date.today() - timedelta(days=2)).isoformat()
    data = corpus(cap("home_care"),
                  policies=[{"id": "weekend_correspondence", "domain": "logistics",
                             "review_date": past}])
    findings = [f for f in C.code_findings(data) if f["kind"] == "drift"]
    assert len(findings) == 1, findings
    assert "still deciding" in findings[0]["detail"], (
        "a number standing in for judgment with nobody re-checking it is the "
        "definition of drift")


@check("a policy whose review date is ahead is not drift")
def _():
    ahead = (date.today() + timedelta(days=30)).isoformat()
    data = corpus(cap("home_care"),
                  policies=[{"id": "p", "domain": "d", "review_date": ahead}])
    assert [f for f in C.code_findings(data) if f["kind"] == "drift"] == []


# ---------------------------------------------------------------------------
# The validator — what makes the model pass falsifiable
# ---------------------------------------------------------------------------

@check("a finding naming ONE id is REJECTED — one id is an opinion")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "drift", "capability_a": "home_care", "capability_b": "",
         "artifact": "registry.yaml", "detail": "it feels inconsistent"}])
    assert accepted == [], accepted
    assert hit(rejected, "one id is an opinion"), rejected


@check("an ORPHAN legitimately names one id — having nothing to collide with IS the finding")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "orphan", "capability_a": "home_care", "capability_b": "",
         "artifact": "config/modules/routing.yaml", "detail": "no routing entry"}])
    assert len(accepted) == 1, (accepted, rejected)


@check("a finding of an INVENTED kind is REJECTED")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "vibes", "capability_a": "a", "capability_b": "b",
         "artifact": "x", "detail": "y"}])
    assert accepted == []
    assert hit(rejected, "can always find something"), (
        "a review that can invent a category can always find something, which "
        f"is the unfalsifiable version of this feature: {rejected}")


@check("a finding naming NO artifact is REJECTED")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "overlap", "capability_a": "a", "capability_b": "b",
         "artifact": "", "detail": "they collide"}])
    assert accepted == []
    assert hit(rejected, "nowhere to go and check it"), rejected


@check("rejections are RETURNED, never silently discarded")
def _():
    _accepted, rejected = C.validate_findings(["not an object", {"kind": "drift"}])
    assert len(rejected) == 2, (
        "a model whose findings are being thrown away is a fact about the "
        f"review worth seeing: {rejected}")


@check("a non-list of findings is rejected whole, not iterated")
def _():
    accepted, rejected = C.validate_findings({"kind": "drift"})
    assert accepted == [] and rejected == ["findings is not a list"]


@check("parse_findings unwraps a fenced block and a {findings: [...]} envelope")
def _():
    fenced = '```json\n{"findings": [{"kind": "orphan"}]}\n```'
    assert C.parse_findings(fenced) == [{"kind": "orphan"}]
    assert C.parse_findings({"findings": [1]}) == [1]
    assert C.parse_findings("not json at all") == []


# ---------------------------------------------------------------------------
# The report
# ---------------------------------------------------------------------------

@check("the report carries code findings and accepted model findings together")
def _():
    result = C.report(model_findings=[
        {"kind": "overlap", "capability_a": "a", "capability_b": "b",
         "artifact": "registry.yaml", "detail": "they collide"},
        {"kind": "drift", "capability_a": "a", "capability_b": "",
         "artifact": "x", "detail": "vague"}])
    sources = {f["source"] for f in result["findings"]}
    assert "model" in sources, result
    assert result["rejected"], "the vague one must be reported as rejected"


@check("the rendered report says so plainly when there is nothing to report")
def _():
    text = C.render({"at": "2026-09-24", "capabilities_reviewed": 3,
                     "findings": [], "rejected": []})
    assert "No findings" in text, text
    assert "consistent with every other" in text, text


@check("the corpus is code-assembled and carries no agent-file bodies")
def _():
    data = C.corpus()
    assert set(data) == {"schema", "capabilities", "policies", "tracked_agents"}
    for entry in data["capabilities"]:
        assert "body" not in entry and "text" not in entry, entry


def _cleanup() -> None:
    shutil.rmtree(_TMP, ignore_errors=True)


try:
    code = suite.report()
finally:
    _cleanup()
sys.exit(code)
