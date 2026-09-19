"""
tests/test_build_verify.py — "the same checks, not equivalents", PROVED.

TWO CLAIMS UNDER TEST.

1. VERIFY RUNS THE SWEEP'S CHECKS, NOT LOOKALIKES OF THEM. The sweep is actually
   run, its check names parsed from its own --verbose output, and compared with
   what core.build.verify.run_all() reports. A declared list that has quietly
   fallen behind qa_sweep.sh fails here rather than at a landing.

   It is TWO equalities and not one, because a single equality over the whole
   invocation could never pass: check_knowledge_domains.py is a standalone
   script the sweep does not run, and neither the capability's own tests nor
   test_action_provenance.py are sweep checks. So SHARED_CHECKS must equal the
   sweep's set exactly with ':overlay' stripped, ADDED_CHECKS must equal its
   declared list exactly, and nothing may fall outside both.

2. THE SWEEP CANNOT SEE AN OVERLAY FILE, AND THE OVERLAY PASS CAN. This is the
   whole reason the overlay pass exists. qa_sweep.sh's greps go through
   `git ls-files` and its check scripts glob config/agents/*.md, so a generated
   agent naming `send_email` would draw eleven green checks. Asserted by
   putting a real overlay on disk and showing the sweep never mentions it.

Also here, because it needs the same machinery: the constitution row — an agent
with '## Confidentiality' deleted and one over max_lines must BOTH fail
constitution.check().

Standalone runner (no pytest dependency), matching tests/ convention.
Slower than its siblings: it runs qa_sweep.sh twice, ~10s each.

Usage:
    python3 tests/test_build_verify.py

Exits 0 if every check passes, 1 otherwise.
"""

import hashlib
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import constitution as C   # noqa: E402
from core.build import verify as V         # noqa: E402
from core.build import writer as W         # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_verify_test_"))
OVERLAY = TMP / "overlay"
CAPABILITY = "home_care"

AGENT_TEXT = f"""# Home Care

## Role
You look after recurring household obligations.

## Scope
Watering and bins. Call `get_weather` for what the weather did.

## Output format
Compact JSON.

## Confidentiality

{C.CLAUSE}
"""


def build_overlay() -> None:
    import yaml
    (OVERLAY / "agents").mkdir(parents=True, exist_ok=True)
    (OVERLAY / "capabilities").mkdir(parents=True, exist_ok=True)
    (OVERLAY / "agents" / f"{CAPABILITY}.md").write_text(AGENT_TEXT, encoding="utf-8")
    grant = ["get_weather", "read_wisdom"]
    record = {
        "schema": "overlay_capability/1",
        "name": CAPABILITY,
        "display_name": "Home Care",
        "job_id": "BLD-0918-01",
        "version": 1,
        "generated_at": "2026-09-18T12:00:00",
        "agent_file": f"agents/{CAPABILITY}.md",
        "agent_sha256": hashlib.sha256(AGENT_TEXT.encode()).hexdigest(),
        "routing": {
            "local": {"local": True, "allowed_tools": grant},
            "cloud": {"model_ref": "mental_wellbeing", "allowed_tools": grant},
        },
        "coordinator": {"directory_entry": "**Home Care**\nCall when: it is due."},
        "unavailable_consequence": "their household upkeep",
        "confidential_names": [CAPABILITY],
        "knowledge_domains": ["home"],
        "execution_mode": "blocking",
        "latency_budget_ms": 8000,
    }
    (OVERLAY / "capabilities" / f"{CAPABILITY}.yaml").write_text(
        yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


build_overlay()

# A capability test that passes, so `capability-tests` reports a real result
# rather than its "no tests declared" refusal. That refusal has its own check.
PASSING_TEST = TMP / "capability_test.py"
PASSING_TEST.write_text("print('capability ok')\n", encoding="utf-8")

# One run_all(), reused. It runs qa_sweep.sh internally (~10s), and the
# comparison below runs it a second time INDEPENDENTLY — which is the point:
# a self-referential comparison would prove nothing.
REPORT = V.run_all(overlay=OVERLAY, capability_tests=[str(PASSING_TEST)])
SWEEP_NAMES = V.sweep_check_names()


# ---------------------------------------------------------------------------
# Claim 1 — the same checks
# ---------------------------------------------------------------------------

@check("SHARED_CHECKS equals what qa_sweep.sh actually runs, exactly")
def _():
    assert SWEEP_NAMES == set(V.SHARED_CHECKS), \
        f"sweep {sorted(SWEEP_NAMES)} vs SHARED_CHECKS {sorted(V.SHARED_CHECKS)}"
    assert len(SWEEP_NAMES) == 11, f"expected the ten plus build-registration, got {len(SWEEP_NAMES)}"


@check("verify ran every shared check, with ':overlay' stripped")
def _():
    shared = {r.base for r in REPORT.results if r.base in V.SHARED_CHECKS}
    assert shared == SWEEP_NAMES, f"verify {sorted(shared)} vs sweep {sorted(SWEEP_NAMES)}"


@check("verify ran every added check, and exactly those")
def _():
    added = {r.base for r in REPORT.results if r.base in V.ADDED_CHECKS}
    assert added == set(V.ADDED_CHECKS), \
        f"ran {sorted(added)}, declared {sorted(V.ADDED_CHECKS)}"


@check("no check falls outside both declared sets")
def _():
    orphans = REPORT.base_names() - set(V.SHARED_CHECKS) - set(V.ADDED_CHECKS)
    assert not orphans, f"{sorted(orphans)} belongs to neither set"


@check("assert_same_checks() reports no findings")
def _():
    findings = V.assert_same_checks(REPORT)
    assert not findings, findings


@check("every check ran twice where it can: tracked AND overlay")
def _():
    overlay_passes = {r.base for r in REPORT.results
                      if r.name.endswith(V.OVERLAY_SUFFIX)}
    assert overlay_passes == {"agent-tools", "rule-overlap", "knowledge-domains",
                              "build-registration"}, sorted(overlay_passes)


# ---------------------------------------------------------------------------
# Claim 2 — the sweep is blind to the overlay; the overlay pass is not
# ---------------------------------------------------------------------------

@check("qa_sweep.sh reports ZERO overlay files — it cannot see them")
def _():
    sweep = V._run("qa-sweep", ["bash", "scripts/qa_sweep.sh", "--verbose"])
    assert CAPABILITY not in sweep.output, \
        "the sweep saw an overlay file; this suite's premise is wrong"


@check("the overlay pass reports the capability the sweep missed")
def _():
    by_name = {r.name: r for r in REPORT.results}
    seen = [name for name, r in by_name.items()
            if name.endswith(V.OVERLAY_SUFFIX) and CAPABILITY in r.output]
    assert seen, ("no overlay pass mentioned the capability — the pass is "
                  "running but not reading the overlay")


@check("an overlay agent naming an ungranted tool FAILS the overlay pass")
def _():
    leaky = TMP / "leaky"
    shutil.rmtree(leaky, ignore_errors=True)
    shutil.copytree(OVERLAY, leaky)
    path = leaky / "agents" / f"{CAPABILITY}.md"
    path.write_text(path.read_text().replace(
        "Call `get_weather` for what the weather did.",
        "Call `send_email` to tell them about it."), encoding="utf-8")
    result = V._run("agent-tools:overlay",
                    [V._python(), "scripts/check_agent_tools.py", "--quiet",
                     "--overlay", str(leaky)])
    assert not result.ok, "an ungranted tool in a generated agent passed the check"
    assert "send_email" in result.output, result.output[:400]


# ---------------------------------------------------------------------------
# The constitution row
# ---------------------------------------------------------------------------

@check("constitution.check fails an agent with '## Confidentiality' deleted")
def _():
    stripped = AGENT_TEXT.split("## Confidentiality")[0]
    defects = C.check(stripped)
    assert defects, "a missing confidentiality clause passed"
    assert any("Confidentiality" in d for d in defects), defects


@check("constitution.check fails an agent over max_lines")
def _():
    long_agent = AGENT_TEXT + ("\nfiller\n" * 300)
    defects = C.check(long_agent)
    assert any("line limit" in d for d in defects), defects


@check("constitution.check passes the valid agent it is given")
def _():
    import yaml
    record = yaml.safe_load(
        (OVERLAY / "capabilities" / f"{CAPABILITY}.yaml").read_text())
    defects = C.check(AGENT_TEXT, record)
    assert not defects, defects


@check("constitution.check fails a reworded confidentiality clause")
def _():
    reworded = AGENT_TEXT.replace(
        "This rule has no exceptions.", "Use your judgement about exceptions.")
    defects = C.check(reworded)
    assert any("canonical clause" in d for d in defects), defects


@check("the canonical clause has not drifted from the tracked tree")
def _():
    assert C.canonical_drift() == "", C.canonical_drift()


# ---------------------------------------------------------------------------
# capability-tests
# ---------------------------------------------------------------------------

@check("a capability with no declared tests does not land")
def _():
    report = V._capability_tests(V._python(), [])
    assert not report.ok, "a capability with no tests was allowed to land"


# ---------------------------------------------------------------------------
# The phase 3 review (2026-09-19) — defect 4
# ---------------------------------------------------------------------------

def _record() -> dict:
    import yaml
    return yaml.safe_load(
        (OVERLAY / "capabilities" / f"{CAPABILITY}.yaml").read_text())


@check("REVIEW 4: narration in a record field that reaches a prompt is caught")
def _():
    """
    The narration scan read the AGENT FILE only. Three record fields reach a
    prompt too — display_name and directory_entry are spliced into the
    Coordinator's system prompt by seam 3, and unavailable_consequence reaches
    the Synthesizer on a failure — and none of them was scanned at all.
    """
    record = _record()
    record["coordinator"] = {
        "directory_entry": '**Home Care**\nSay "I dispatched the sub-agent for you".'}
    defects = C.check(AGENT_TEXT, record)
    assert defects, "narration in directory_entry passed"
    assert any("directory_entry" in d for d in defects), defects

    record = _record()
    record["unavailable_consequence"] = "their routing.yaml entry and run_subagent calls"
    defects = C.check(AGENT_TEXT, record)
    assert any("unavailable_consequence" in d for d in defects), defects

    record = _record()
    record["display_name"] = "Home Care (gemini)"
    defects = C.check(AGENT_TEXT, record)
    assert any("display_name" in d for d in defects), defects


@check("REVIEW 4b: display_name is restricted to a safe character set")
def _():
    from core.build import schemas
    record = _record()
    for bad in ("Home/Care", "Home`Care", "Home\nCare", "Home_Care", "Home<Care>"):
        record["display_name"] = bad
        record["coordinator"] = {"directory_entry": f"**{bad}**\nCall when: due."}
        defects = schemas.validate_overlay_capability(record)
        assert any("display_name" in d for d in defects), f"{bad!r}: {defects}"
    for good in ("Home Care", "Work & Vocation", "Zone 2"):
        record["display_name"] = good
        record["coordinator"] = {"directory_entry": f"**{good}**\nCall when: due."}
        defects = [d for d in schemas.validate_overlay_capability(record)
                   if "display_name" in d]
        assert not defects, f"{good!r} was refused: {defects}"


# ---------------------------------------------------------------------------
# Part 2 of the review (2026-09-19)
# ---------------------------------------------------------------------------

@check("REVIEW N3: a LIVE tool name in a record field is caught")
def _():
    """
    The record-field gate matched _ALWAYS_CONFIDENTIAL, which carries 37 of the
    78 registered tool names — so `send_email`, `read_email` and
    `merge_contacts` landed in prompt-bound fields while the agent-file grant
    gate would refuse the same tokens. A tool name IS the canonical confidential
    identifier; the two gates now read the same set.
    """
    for value in ("their send_email digest", "their read_email triage",
                  "their merge_contacts pass"):
        record = _record()
        record["unavailable_consequence"] = value
        defects = C.check(AGENT_TEXT, record)
        assert any("unavailable_consequence" in d for d in defects), \
            f"{value!r}: {defects}"


@check("REVIEW O2: the sweep's overlay pass asserts all three record rules")
def _():
    """
    check_build_registration.py is the SECOND line — it re-asserts independently
    what the writer refuses at write time. It called the validator without
    reserved_display or model_ref_names, so it covered the three-set `name` rule
    and neither of the two rules added for defects 2 and 5.
    """
    import subprocess
    import yaml
    target = TMP / "obs2"
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(OVERLAY, target)
    path = target / "capabilities" / f"{CAPABILITY}.yaml"
    record = yaml.safe_load(path.read_text())
    record["display_name"] = "Mental  Wellbeing"          # reserved_display only
    record["coordinator"] = {"directory_entry": "**Mental  Wellbeing**\nCall when: due."}
    record["routing"]["cloud"]["model_ref"] = "no_such_agent"   # model_ref_names only
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")

    proc = subprocess.run(
        [V._python(), "scripts/check_build_registration.py", "--overlay", str(target)],
        cwd=str(ROOT), capture_output=True, text=True)
    assert proc.returncode == 1, f"sweep passed a record the writer refuses:\n{proc.stdout}"
    assert "display_name" in proc.stdout, proc.stdout
    assert "model_ref" in proc.stdout, proc.stdout


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
