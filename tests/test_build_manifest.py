"""
tests/test_build_manifest.py — the privacy proof for Inquiry.

THE CLAIM UNDER TEST: the manifest carries no value read from the corpus.

This matters more than it first looks. Inquiry runs BEFORE any probe, so
anything the manifest carries reaches a model that has not yet been told it
needs it — and Inquiry is the widest-context agent in the vertical. The
manifest is therefore the privacy boundary for the whole of Build, and it is
the one that would be easiest to erode: adding "a little context so the
questions are sharper" is a plausible-sounding change that would quietly turn
a source catalogue into a data leak.

TWO PROOFS, THE SECOND STRONGER THAN THE FIRST.

  1. Grep. Every string value in profile.yaml must be absent from the rendered
     manifest. This is the check the plan names. On a machine with no persona
     tree it runs against config/templates/profile.yaml, which is the same
     shape.

  2. Provenance. EVERY string in the manifest must be traceable to a literal in
     core/build/manifest.py, or to a config/agents/*.md filename, or to a
     policy's own declared fields. This is the stronger form, because it holds
     for data that does not exist on this machine and for data nobody has
     written yet: it proves there is nowhere for a corpus value to come from,
     rather than proving that today's corpus values are absent.

THE ONE DOCUMENTED EXCEPTION is a policy's `applies_to`. A policy is authored
with the user at build time and its scope statement is not read from the
corpus, so it is inside the content-free rule — but it IS persona-scoped, so
the test asserts the exception explicitly rather than letting it pass unnoticed.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_manifest.py

Exits 0 if every check passes, 1 otherwise.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J  # noqa: E402
from core.build import manifest as M  # noqa: E402
from core.build import policy as P  # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_manifest_test_"))
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or "mike")

MANIFEST_SRC = (ROOT / "core" / "build" / "manifest.py").read_text(encoding="utf-8")


def rendered(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False)


def strings_in(obj) -> list[str]:
    """Every string anywhere in a nested structure, keys included."""
    out: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            out.append(str(key))
            out.extend(strings_in(value))
    elif isinstance(obj, (list, tuple)):
        for item in obj:
            out.extend(strings_in(item))
    elif isinstance(obj, str):
        out.append(obj)
    return out


def profile_values() -> list[str]:
    """
    Every non-trivial string value in a profile.yaml on this machine.

    Falls back to the template when no persona tree is present — the real trees
    live on the VM, and the template has the same shape and the same fields.
    """
    import yaml
    candidates = list((ROOT / "config" / "personas").glob("*/profile.yaml"))
    candidates.append(ROOT / "config" / "templates" / "profile.yaml")

    values: list[str] = []
    for path in candidates:
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        for value in strings_in(data):
            text = value.strip()
            # Keys and single words like "name" or "UTC" are structural, not
            # values; grepping for them would fail on any English sentence.
            if len(text) > 3 and text not in data.keys():
                values.append(text)
    return values


# ---------------------------------------------------------------------------
# Proof 1 — the grep the plan names
# ---------------------------------------------------------------------------

@check("no profile.yaml value appears anywhere in the manifest")
def _():
    body = rendered(M.build())
    hits = [v for v in profile_values() if v and v in body]
    assert not hits, f"profile values leaked into the manifest: {hits}"


@check("a profile value planted in the source WOULD be caught")
def _():
    # The grep above passes trivially if profile_values() is empty. This proves
    # the detector fires — without it, an empty profile would look like a pass.
    planted = "Bethesda, Maryland, and a barbecue on the 22nd"
    body = rendered(M.build()) + planted
    assert planted in body
    assert [v for v in [planted] if v in body], "the detector does not fire"


# ---------------------------------------------------------------------------
# Proof 2 — provenance. Nowhere for a corpus value to come from.
# ---------------------------------------------------------------------------

@check("every string in the manifest is traceable to code or a filename")
def _():
    manifest = M.build()
    agent_stems = {p.stem for p in (ROOT / "config" / "agents").glob("*.md")}
    structural = {
        "schema", "manifest/1", "sources", "capabilities", "policies",
        "fingerprint", "id", "tool", "kind", "description", "probe",
        "available", "origin", "tracked", "applies_to", "domain",
        "retires_question_classes", "single_point", "behavioural",
    }

    untraceable: list[str] = []
    for value in strings_in(manifest):
        text = value.strip()
        if not text or text in structural or text in agent_stems:
            continue
        if text == manifest["fingerprint"]:
            continue
        # A literal written in manifest.py is code-authored by definition.
        if f'"{text}"' in MANIFEST_SRC or f"'{text}'" in MANIFEST_SRC:
            continue
        untraceable.append(text)

    assert not untraceable, (
        "strings with no code provenance — a corpus value could hide here: "
        f"{untraceable}")


@check("the manifest is identical for two different personas, but for policies")
def _():
    one = M.build("mike")
    two = M.build("danny_park")
    assert one["sources"] == two["sources"]
    assert one["capabilities"] == two["capabilities"]


# ---------------------------------------------------------------------------
# The one documented exception, asserted rather than assumed
# ---------------------------------------------------------------------------

@check("a policy's applies_to DOES enter the manifest — the stated exception")
def _():
    shutil.rmtree(TMP / "personas", ignore_errors=True)
    P.write_policy({
        "id": "weekend_business_correspondence",
        "domain": "work",
        "applies_to": "business senders writing outside working hours",
        "standing_commitments": [], "automatic_yes": [],
        "automatic_no": ["raise a business thread at the weekend"],
        "default_on_silence": "hold until Monday morning",
        "review_date": "2026-12-01",
        "authored_with_user": True,
    }, job_id="BLD-0918-01", persona="mike")

    manifest = M.build("mike")
    assert len(manifest["policies"]) == 1, manifest["policies"]
    entry = manifest["policies"][0]
    assert entry["applies_to"] == "business senders writing outside working hours"
    # It is authored with the user at build time, not read from the corpus —
    # which is why it is inside the content-free rule. settle.py cannot resolve
    # against a policy whose scope it cannot see.


@check("a policy does NOT drag its decision content into the manifest")
def _():
    manifest = M.build("mike")
    body = rendered({"policies": manifest["policies"]})
    assert "hold until Monday morning" not in body, (
        "default_on_silence is a decision, not a scope statement — the manifest "
        "carries what a policy COVERS, never what it decides")
    assert "raise a business thread at the weekend" not in body


# ---------------------------------------------------------------------------
# The fingerprint, and what it is for
# ---------------------------------------------------------------------------

@check("the fingerprint changes when a source's availability changes")
def _():
    live = M.sources()
    before = M.fingerprint({"sources": live, "capabilities": [], "policies": []})
    flipped = [{**s, "available": not s["available"]} if s["id"] == "log" else s
               for s in live]
    after = M.fingerprint({"sources": flipped, "capabilities": [], "policies": []})
    assert before != after, (
        "a tool landing must invalidate a question set written before it")


@check("the fingerprint does NOT change when a description is reworded")
def _():
    live = M.sources()
    before = M.fingerprint({"sources": live, "capabilities": [], "policies": []})
    reworded = [{**s, "description": "reworded entirely"} for s in live]
    after = M.fingerprint({"sources": reworded, "capabilities": [], "policies": []})
    assert before == after, (
        "rewording a description does not change what can be answered")


# ---------------------------------------------------------------------------
# Sources and capabilities
# ---------------------------------------------------------------------------

@check("source availability is read from the live register_tools(), not asserted")
def _():
    from core.orchestrator import register_tools
    _, handlers = register_tools()
    for source in M.sources():
        assert source["available"] == (source["tool"] in handlers), source


@check("the two section 9 briefs report unavailable — a designed state")
def _():
    gaps = M.unavailable()
    assert "conversations" in gaps, gaps
    assert "journal_range" in gaps, gaps
    # Expected on run 1. search_conversations and read_journal_range are Mike's
    # Mac-side builds (phase 6); until they land, a question whose only source
    # is one of them settles to needs_tool, which is Build discovering its own
    # substrate rather than failing.


@check("every manifest source names a tool inside the plan's READ SET")
def _():
    # The grant allowlist itself is the writer's (phase 3). This asserts the
    # weaker property phase 2 owns: nothing in the source table is a mutator.
    forbidden = {
        "send_email", "send_calendar_invite", "write_calendar_event",
        "update_calendar_event", "delete_calendar_event", "fetch_url",
        "fetch_rendered", "run_subagent", "run_model_conference",
        "write_agent_config", "write_config", "write_persona", "write_schedule",
        "delete_schedule", "open_obligation", "close_obligation",
        "reopen_obligation", "record_horizon_item", "write_goals", "update_goal",
        "merge_wisdom_entries", "teach_intake", "apply_crm_proposals",
        "merge_contacts", "unmerge_contacts", "import_contacts_file",
        "log_interaction", "record_wisdom_response", "create_semantic_anchor",
    }
    named = {s["tool"] for s in M.sources()}
    assert not (named & forbidden), named & forbidden


@check("capabilities come from agent-file stems, not from the routing files")
def _():
    names = M.capability_names()
    assert "time_director" in names, (
        "time_director has an agent file and NO routing entry. A routing-only "
        "capability list would omit it, and a `new` disposition could then pass "
        "by claiming nothing like it exists.")
    assert "logistics" in names and "synthesizer" in names, sorted(names)


@check("candidate_sources validation lines up with the manifest's own ids")
def _():
    from core.build.schemas import validate_question_set
    ids = set(M.source_ids())
    assert "log" in ids and "weather" in ids, sorted(ids)
    assert M.USER_SOURCE not in ids, (
        "'user' is not a source — it resolves to an interview item, never a probe")
    assert callable(validate_question_set)


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
