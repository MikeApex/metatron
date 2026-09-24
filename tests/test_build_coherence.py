"""
tests/test_build_coherence.py — the review is falsifiable, or it is not a review.

THE ONE PROPERTY WORTH TESTING is the validator: every finding must name two
capability ids and the artifact where they collide, and one that cannot is
REJECTED in code before anyone reads it. "The capabilities are drifting" is
unarguable; "`home_care` and `garden_care` both claim `create` on
`plant_watering`" can be checked in a minute and can be WRONG. A review whose
findings cannot be wrong is not a review.

`orphan` is the deliberate exception and is tested as one: having nothing to
collide with IS the finding, so it names one id and its missing artifact.

The code pass is tested as the non-advisory half it is. Duplicate surface
claims, dangling `replaces[]` targets, half-registered capabilities and expired
policy review dates are all decidable by comparison, so no model is asked — the
same rule that generates the node graph, applied to the review of its output.

Standalone runner, no pytest, matching tests/ convention. No model is called:
review(use_model=False) is the whole surface under test.

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

import core.build.coherence as C    # noqa: E402
import core.build.jobs as J         # noqa: E402
import core.build.registry as R     # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    def wrap(fn):
        try:
            fn()
            _results.append((name, True, ""))
        except AssertionError as e:
            _results.append((name, False, f"assertion: {e}"))
        except Exception as e:
            _results.append((name, False, f"{type(e).__name__}: {e}"))
        return fn
    return wrap


TMP = Path(tempfile.mkdtemp(prefix="build_coherence_test_"))
PERSONA = "mike"
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or PERSONA)
R.persona_data_dir = J.persona_data_dir


def reset() -> None:
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    J.build_dir(PERSONA).mkdir(parents=True, exist_ok=True)


def corpus_of(capabilities: list[dict], policies: list[dict] | None = None) -> dict:
    return {"capabilities": capabilities, "policies": policies or [],
            "counts": {"capabilities": len(capabilities),
                       "policies": len(policies or [])}}


def cap(cap_id: str, surface=None, replaces=None, in_registry=True,
        in_overlay=True) -> dict:
    return {"id": cap_id, "kind": "agent", "surface": surface or [],
            "replaces": replaces or [], "in_registry": in_registry,
            "in_overlay": in_overlay, "theme": ""}


# ---------------------------------------------------------------------------
# The validator — what makes the output falsifiable
# ---------------------------------------------------------------------------

@check("a finding naming one capability is REJECTED — one id is an opinion")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "overlap", "capability_a": "home_care", "capability_b": "",
         "artifact": "surface_map", "detail": "feels like a lot of overlap"}])
    assert accepted == [], accepted
    assert rejected and "two ids" in rejected[0], rejected


@check("a finding outside the closed enum is REJECTED, never renamed")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "concern", "capability_a": "a_cap", "capability_b": "b_cap",
         "artifact": "registry.jsonl", "detail": "they feel related"}])
    assert accepted == [], accepted
    assert "outside" in rejected[0], rejected
    # A review that can invent a category can always find something.


@check("a finding with no artifact is REJECTED — there is nowhere to go and check it")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "overlap", "capability_a": "a_cap", "capability_b": "b_cap",
         "artifact": "", "detail": "they collide"}])
    assert accepted == [] and "no artifact" in rejected[0], (accepted, rejected)


@check("a finding with no detail is REJECTED")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "overlap", "capability_a": "a_cap", "capability_b": "b_cap",
         "artifact": "surface_map", "detail": "  "}])
    assert accepted == [] and "no detail" in rejected[0], (accepted, rejected)


@check("orphan is the ONE kind allowed a single id — nothing to collide with IS the finding")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "orphan", "capability_a": "home_care", "capability_b": "",
         "artifact": "registry.jsonl", "detail": "live with no registry row"}])
    assert len(accepted) == 1 and not rejected, (accepted, rejected)


@check("a well-formed finding is accepted and carries its source")
def _():
    accepted, _rejected = C.validate_findings([
        {"kind": "contradiction", "capability_a": "a_cap", "capability_b": "b_cap",
         "artifact": "registry.jsonl", "detail": "a replaces b, b is live"}])
    assert accepted[0]["source"] == "model", accepted
    assert accepted[0]["kind"] == "contradiction"


@check("rejections are RETURNED, not discarded — an over-firing pass must be visible")
def _():
    accepted, rejected = C.validate_findings([
        {"kind": "drift", "capability_a": "a_cap", "capability_b": "", "artifact": "x",
         "detail": "d"},
        {"kind": "nonsense", "capability_a": "a_cap", "capability_b": "b_cap",
         "artifact": "x", "detail": "d"},
        "not even an object",
    ])
    assert accepted == [], accepted
    assert len(rejected) == 3, rejected


@check("a non-list of findings is rejected whole, not iterated")
def _():
    accepted, rejected = C.validate_findings({"kind": "drift"})
    assert accepted == [] and rejected == ["findings is not a list"]


# ---------------------------------------------------------------------------
# The code pass — decidable by comparison, so no model is asked
# ---------------------------------------------------------------------------

@check("two capabilities claiming the same in_scope operation are an OVERLAP")
def _():
    claim = [{"entity": "plant_watering", "operation": "create", "status": "in_scope"}]
    findings = C.code_findings(corpus_of([cap("home_care", claim),
                                          cap("garden_care", claim)]))
    overlaps = [f for f in findings if f["kind"] == "overlap"]
    assert len(overlaps) == 1, findings
    assert {overlaps[0]["capability_a"], overlaps[0]["capability_b"]} == \
        {"home_care", "garden_care"}, overlaps
    assert overlaps[0]["source"] == "code", overlaps


@check("a DEFERRED operation is not an overlap — only in_scope claims collide")
def _():
    findings = C.code_findings(corpus_of([
        cap("home_care", [{"entity": "watering", "operation": "create",
                           "status": "in_scope"}]),
        cap("garden_care", [{"entity": "watering", "operation": "create",
                             "status": "deferred"}])]))
    assert [f for f in findings if f["kind"] == "overlap"] == [], findings


@check("declaring a replacement while the replaced thing is live is a CONTRADICTION")
def _():
    findings = C.code_findings(corpus_of([cap("home_care", replaces=["garden_care"]),
                                          cap("garden_care")]))
    contradictions = [f for f in findings if f["kind"] == "contradiction"]
    assert len(contradictions) == 1, findings
    assert contradictions[0]["capability_b"] == "garden_care", contradictions
    assert "both will be dispatched" in contradictions[0]["detail"]


@check("replacing something already retired is NOT a contradiction")
def _():
    findings = C.code_findings(corpus_of([
        cap("home_care", replaces=["garden_care"]),
        cap("garden_care", in_overlay=False)]))
    assert [f for f in findings if f["kind"] == "contradiction"] == [], findings


@check("half-registration is an ORPHAN in BOTH directions")
def _():
    findings = C.code_findings(corpus_of([cap("a_cap", in_overlay=False),
                                          cap("b_cap", in_registry=False)]))
    orphans = {f["capability_a"]: f for f in findings if f["kind"] == "orphan"}
    assert set(orphans) == {"a_cap", "b_cap"}, orphans
    assert "nothing can load it" in orphans["a_cap"]["detail"]
    assert "unmetered" in orphans["b_cap"]["detail"]


@check("a policy past its review date is DRIFT")
def _():
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    tomorrow = (date.today() + timedelta(days=1)).isoformat()
    findings = C.code_findings(corpus_of(
        [], [{"id": "weekend_business", "domain": "correspondence",
              "review_date": yesterday},
             {"id": "fresh_policy", "domain": "home", "review_date": tomorrow}]))
    drifts = [f for f in findings if f["kind"] == "drift"]
    assert len(drifts) == 1 and drifts[0]["capability_a"] == "weekend_business", findings


@check("every code finding passes the same validator the model's findings face")
def _():
    claim = [{"entity": "watering", "operation": "create", "status": "in_scope"}]
    findings = C.code_findings(corpus_of(
        [cap("a_cap", claim, replaces=["b_cap"]), cap("b_cap", claim),
         cap("c_cap", in_overlay=False)],
        [{"id": "p1", "domain": "home",
          "review_date": (date.today() - timedelta(days=1)).isoformat()}]))
    accepted, rejected = C.validate_findings(findings)
    assert not rejected, rejected
    assert len(accepted) == len(findings), (len(accepted), len(findings))


# ---------------------------------------------------------------------------
# The review
# ---------------------------------------------------------------------------

@check("the model pass is skipped below two capabilities — arithmetic already answered")
def _():
    reset()
    report = C.review(PERSONA, use_model=True)
    assert report["model_ran"] is False, report
    assert report["counts"]["capabilities"] == 0, report


@check("an empty system reviews clean rather than raising")
def _():
    reset()
    report = C.review(PERSONA, use_model=False)
    assert report["findings"] == [] and report["rejected"] == [], report
    assert "no findings" in C.render(report)


@check("the corpus reads the registry and reports the overlay difference")
def _():
    reset()
    R.record_landing("BLD-0919-01",
                     {"capability": {"id": "home_care", "kind": "agent",
                                     "execution_mode": "blocking",
                                     "latency_budget_ms": 8000,
                                     "one_line": "x", "disposition": "new"}},
                     ["a.md"], PERSONA)
    data = C.corpus(PERSONA)
    entry = data["capabilities"][0]
    assert entry["id"] == "home_care", data
    assert entry["in_registry"] and not entry["in_overlay"], entry
    # Registered with no overlay record: the code pass calls that an orphan,
    # which is correct — a landing whose record is gone cannot be dispatched.
    assert any(f["kind"] == "orphan" for f in C.code_findings(data))


@check("render names both ids, the artifact and the source")
def _():
    claim = [{"entity": "watering", "operation": "create", "status": "in_scope"}]
    report = {"counts": {"capabilities": 2, "policies": 0}, "model_ran": False,
              "findings": C.code_findings(corpus_of([cap("a_cap", claim),
                                                     cap("b_cap", claim)])),
              "rejected": []}
    text = C.render(report)
    assert "a_cap ↔ b_cap" in text and "surface_map" in text and "(code)" in text, text


# ---------------------------------------------------------------------------
# REVIEW ROUND 1 — the Fable 5.1 phase-4 review
# ---------------------------------------------------------------------------

@check("REVIEW D6: a BARE LIST reply is parsed, not dropped as 'findings is not a list'")
def _():
    # The prompt asked for "a JSON list"; repair_json — built for the
    # orchestrator's context blocks, which are objects — extracts the first
    # {…} from a list and returns THE FIRST FINDING as a dict. .get("findings")
    # was None, every well-formed reply was rejected, and `model_ran: True`
    # sat beside it so the board read as a review that found nothing.
    bare = ('[{"kind": "overlap", "capability_a": "a_cap", "capability_b": "b_cap",'
            ' "artifact": "surface_map", "detail": "both claim create"}]')
    parsed = C._parse_findings(bare)
    assert isinstance(parsed, list) and len(parsed) == 1, parsed
    accepted, rejected = C.validate_findings(parsed)
    assert len(accepted) == 1 and not rejected, (accepted, rejected)


@check("REVIEW D6: object, fenced list and fenced object all parse to the same findings")
def _():
    finding = ('{"kind": "orphan", "capability_a": "a_cap", "capability_b": "",'
               ' "artifact": "registry.jsonl", "detail": "no record"}')
    shapes = [
        f'[{finding}]',                                   # bare list
        f'{{"findings": [{finding}]}}',                   # the object asked for
        f'```json\n[{finding}]\n```',                     # fenced list
        f'```json\n{{"findings": [{finding}]}}\n```',     # fenced object
    ]
    for raw in shapes:
        parsed = C._parse_findings(raw)
        assert isinstance(parsed, list) and len(parsed) == 1, (raw[:30], parsed)
        assert C.validate_findings(parsed)[0], raw[:30]


@check("REVIEW D6: unparseable text yields [] rather than a crash or a fake finding")
def _():
    for raw in ("", "I could not find anything.", None, 7):
        assert C._parse_findings(raw) == [], raw


@check("REVIEW D5: the OVERLAP detector fires on a real registry row")
def _():
    # _surface_of read row.surface_map or record.surface_map; record_landing
    # wrote neither and the overlay record schema has no such field, so the
    # corpus carried `surface: []` for every capability and section 13.7's own
    # falsifiable example was the one comparison the pass could not make.
    reset()
    plan = {"capability": {"id": "home_care", "kind": "agent",
                           "execution_mode": "blocking", "latency_budget_ms": 8000},
            "surface_map": [{"entity": "watering", "operation": "read",
                             "status": "in_scope", "reason": "the whole job"}]}
    other = {**plan, "capability": {**plan["capability"], "id": "garden_care"}}
    R.record_landing("BLD-0919-01", plan, [], PERSONA)
    R.record_landing("BLD-0919-02", other, [], PERSONA)

    data = C.corpus(PERSONA)
    surfaces = {e["id"]: e["surface"] for e in data["capabilities"]}
    assert surfaces["home_care"], "the registry row carries no surface map"
    overlaps = [f for f in C.code_findings(data) if f["kind"] == "overlap"]
    assert len(overlaps) == 1, C.code_findings(data)
    assert {overlaps[0]["capability_a"], overlaps[0]["capability_b"]} == \
        {"home_care", "garden_care"}, overlaps


@check("REVIEW D5: the surface map on a registry row carries NO free text")
def _():
    # The row is read by render_markdown() into a TRACKED file, so the model's
    # `reason` prose stays out — the same rule that keeps `one_line` out.
    reset()
    plan = {"capability": {"id": "home_care", "kind": "agent",
                           "execution_mode": "blocking", "latency_budget_ms": 8000},
            "surface_map": [{"entity": "watering", "operation": "read",
                             "status": "in_scope",
                             "reason": "SECRETREASON about the household"}]}
    row = R.record_landing("BLD-0919-01", plan, [], PERSONA)
    assert row["surface_map"] == [{"entity": "watering", "operation": "read",
                                   "status": "in_scope"}], row["surface_map"]
    assert "SECRETREASON" not in R.render_markdown(PERSONA)


def main() -> int:
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}" + (f"\n      {detail}" if detail else ""))
    passed = sum(1 for _n, ok, _d in _results if ok)
    print(f"\n{passed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    return 0 if passed == len(_results) else 1


if __name__ == "__main__":
    sys.exit(main())
