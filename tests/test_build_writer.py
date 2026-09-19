"""
tests/test_build_writer.py — the choke point, tested harder than anything else.

THE CLAIM UNDER TEST: Build never writes a tracked file, never holds a grant
outside its allowlist, and never leaves anything half-applied.

This suite is deliberately heavier than the others in tests/. The writer is the
one component of Build where a defect is UNRECOVERABLE rather than merely wrong
— a bad question set costs a retry, a bad write costs the tracked tree — and the
undo journal is new machinery with no prior art anywhere in this repo. v2 had a
git worktree beside it as a second line; v3 removed the worktree, so the journal
must be tested harder, not less.

"AT ALL THREE CEILINGS" below means the three `autonomy.ceiling` values —
generated_registration, amber, red. The claim being tested is that the deny
list, the tracked-path rule and the grant allowlist are HARDCODED and so are not
relaxed by raising the ceiling. A ceiling that could widen them would make
"the ceiling is config, and anything that edits config can raise it" true.

The fixture is a REAL git repository. `git ls-files` actually runs in it, so the
tracked-path rule is exercised rather than stubbed — including the belt-and-
braces case the plan calls out: a path that is tracked AND under an allow-root.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_writer.py

Exits 0 if every check passes, 1 otherwise.
"""

import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J          # noqa: E402
from core.build import constitution as C   # noqa: E402
from core.build import overlay as OV       # noqa: E402
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


# ---------------------------------------------------------------------------
# The fixture repository
# ---------------------------------------------------------------------------

TMP = Path(tempfile.mkdtemp(prefix="build_writer_test_"))
FIXTURE = TMP / "repo"
PERSONA = "mike"

ROUTING_LOCAL = """\
local_enabled: true
local:
  model: qwen3:14b
agents:
  mental_wellbeing:
    local: true
    model: qwen3:14b
  local_only_agent:
    local: true
"""

ROUTING_CLOUD = """\
agents:
  mental_wellbeing:
    provider: gemini
    model: gemini-3.8-flash
  cloud_only_agent:
    provider: gemini
    model: gemini-3.8-flash
"""

BUILD_YAML = """\
autonomy:
  ceiling: "generated_registration"
  may_create_agent_files: true
agent_construction:
  max_lines: 220
  required_sections: [Role, Scope, Output format, Confidentiality]
"""


def _git(*args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=str(FIXTURE), check=True, capture_output=True)


def build_fixture() -> None:
    (FIXTURE / "config" / "agents").mkdir(parents=True)
    (FIXTURE / "config" / "modules").mkdir(parents=True)
    (FIXTURE / "scripts").mkdir(parents=True)

    # time_director: an agent FILE with no routing entry. The half-wired agent
    # that is in the real tree today, and the reason the name rule reads three
    # sets rather than the two routing files.
    (FIXTURE / "config" / "agents" / "time_director.md").write_text("# Time Director\n")
    (FIXTURE / "config" / "agents" / "coordinator.md").write_text(
        "## Output format\n\n"
        '**Valid `"agent"` values** — copy these strings exactly, character for character:\n'
        '`"Mental Wellbeing"` · `"Physical Health"` · `"Logistics"` · `"Pattern Miner"`\n\n'
        "## Specialist directory\n\n**Logistics**\nCall when: arrangements.\n\n"
        "## Tools available\n")
    (FIXTURE / "config" / "constitution.md").write_text("# Tier 0\n")
    (FIXTURE / "config" / "modules" / "routing.yaml").write_text(ROUTING_LOCAL)
    (FIXTURE / "config" / "modules" / "routing_cloud.yaml").write_text(ROUTING_CLOUD)
    (FIXTURE / "config" / "modules" / "build.yaml").write_text(BUILD_YAML)

    # The real tool-name checker, so the grant gate runs the SAME regex and the
    # same evidence gate the tracked-tree check runs. A copy here would drift.
    os.symlink(ROOT / "scripts" / "check_agent_tools.py",
               FIXTURE / "scripts" / "check_agent_tools.py")

    overlay_agents = FIXTURE / "data" / "personas" / PERSONA / "build" / "overlay" / "agents"
    overlay_agents.mkdir(parents=True)
    (overlay_agents / "tracked_agent.md").write_text("# tracked, and under an allow-root\n")

    _git("init", "-q", "-b", "main")
    _git("add", "-A")
    # Force-added: data/personas/*/ is gitignored in the real repo, and the
    # point of this file is to be tracked AND inside an allow-root at once.
    _git("add", "-f", "data/personas/mike/build/overlay/agents/tracked_agent.md")
    _git("commit", "-qm", "fixture")


build_fixture()

W._ROOT = FIXTURE
W._CONFIG_PATH = FIXTURE / "config" / "modules" / "build.yaml"
C._ROOT = FIXTURE
J.persona_data_dir = lambda persona=None: FIXTURE / "data" / "personas" / (persona or PERSONA)


def set_ceiling(value: str, may_create: bool = True) -> None:
    W._CONFIG_PATH.write_text(
        BUILD_YAML.replace('"generated_registration"', f'"{value}"')
                  .replace("may_create_agent_files: true",
                           f"may_create_agent_files: {str(may_create).lower()}"))


CEILINGS = ("generated_registration", "amber", "red")


TRACKED_IN_ALLOW_ROOT = "data/personas/mike/build/overlay/agents/tracked_agent.md"


def reset() -> str:
    """
    Wipe Build's state and return a fresh job id already in a writable state.

    The tracked-and-under-an-allow-root fixture file is RESTORED afterwards: it
    has to live under build/ to be inside an allow-root at all, which is exactly
    where this wipe lands. Without the restore it vanishes after the first test
    and the belt-and-braces case silently stops being tested.
    """
    build = J.build_dir(PERSONA)
    if build.exists():
        shutil.rmtree(build)
    tracked = FIXTURE / TRACKED_IN_ALLOW_ROOT
    tracked.parent.mkdir(parents=True, exist_ok=True)
    tracked.write_text("# tracked, and under an allow-root\n")
    OV.clear_cache()
    set_ceiling("generated_registration", may_create=True)
    return J.create("a gap", trigger="test", state="briefed", persona=PERSONA)["job_id"]


# ---------------------------------------------------------------------------
# Building a valid pair
# ---------------------------------------------------------------------------

GRANT = ["get_log_window", "get_weather", "read_wisdom"]


def agent_text(display: str = "Home Care") -> str:
    return f"""# {display}

## Role
You look after recurring household obligations.

## Scope
Watering, bins and filters. Call `get_log_window` for what was logged and
`get_weather` for what the weather did.

## Output format
Compact JSON.

## Confidentiality

{C.CLAUSE}
"""


def record_for(name: str, job_id: str, display: str, text: str,
               grant: list[str] | None = None, **overrides) -> dict:
    grant = GRANT if grant is None else grant
    record = {
        "schema": "overlay_capability/1",
        "name": name,
        "display_name": display,
        "job_id": job_id,
        "version": 1,
        "generated_at": "2026-09-18T12:00:00",
        "agent_file": f"agents/{name}.md",
        "agent_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "routing": {
            "local": {"local": True, "allowed_tools": list(grant)},
            # No `provider`: it is INHERITED from the agent model_ref names.
            "cloud": {"model_ref": "mental_wellbeing",
                      "allowed_tools": list(grant)},
        },
        "coordinator": {"directory_entry": f"**{display}**\nCall when: it is due."},
        "unavailable_consequence": "their household upkeep",
        "confidential_names": [name],
        "knowledge_domains": ["home"],
        "execution_mode": "blocking",
        "latency_budget_ms": 8000,
    }
    record.update(overrides)
    return record


def edits_for(name: str, job_id: str, display: str = "Home Care",
              grant: list[str] | None = None, **overrides) -> list[dict]:
    import yaml
    text = agent_text(display)
    record = record_for(name, job_id, display, text, grant, **overrides)
    overlay = W.overlay_dir(PERSONA)
    return [
        {"path": str(overlay / "agents" / f"{name}.md"), "content": text},
        {"path": str(overlay / "capabilities" / f"{name}.yaml"),
         "content": yaml.safe_dump(record, sort_keys=False)},
    ]


# ---------------------------------------------------------------------------
# The happy path — everything else is a refusal, so this must hold first
# ---------------------------------------------------------------------------

@check("a valid record and agent file land together")
def _():
    job = reset()
    out = W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
    assert out.startswith("OK"), out
    overlay = W.overlay_dir(PERSONA)
    assert (overlay / "agents" / "home_care.md").exists()
    assert (overlay / "capabilities" / "home_care.yaml").exists()
    assert W.undo_path(job, PERSONA).exists(), "the journal must exist after a write"


@check("dry_run validates and writes nothing")
def _():
    job = reset()
    out = W.apply(job, None, edits_for("home_care", job), dry_run=True, persona=PERSONA)
    assert out.startswith("OK (dry run)"), out
    assert not (W.overlay_dir(PERSONA) / "agents" / "home_care.md").exists()


@check("an agent file with no record in the same call is refused")
def _():
    job = reset()
    only_agent = [edits_for("home_care", job)[0]]
    out = W.apply(job, None, only_agent, persona=PERSONA)
    assert "REFUSED" in out and "no capability record" in out, out


# ---------------------------------------------------------------------------
# Path rules
# ---------------------------------------------------------------------------

@check("every tracked path is refused, at all three ceilings")
def _():
    job = reset()
    tracked = subprocess.run(["git", "ls-files"], cwd=str(FIXTURE),
                             capture_output=True, text=True).stdout.split()
    assert len(tracked) >= 6, tracked
    for ceiling in CEILINGS:
        set_ceiling(ceiling)
        for rel in tracked:
            out = W.apply(job, None, [{"path": rel, "content": "x"}], persona=PERSONA)
            assert "REFUSED" in out, f"{rel} at ceiling {ceiling}: {out}"


@check("a tracked path that is ALSO under an allow-root is refused")
def _():
    job = reset()
    rel = TRACKED_IN_ALLOW_ROOT
    before = (FIXTURE / rel).read_text()
    for ceiling in CEILINGS:
        set_ceiling(ceiling)
        out = W.apply(job, None, [{"path": rel, "content": "overwritten"}],
                      persona=PERSONA)
        assert "REFUSED" in out and "tracked by git" in out, out
    assert (FIXTURE / rel).read_text() == before, "the file was modified"


@check("every deny-list path is refused")
def _():
    job = reset()
    for rel in ("config/constitution.md", "deploy.sh", ".claude/settings.json",
                "core/router.py", "core/persona.py", "core/spend_guard.py",
                "core/scheduler.py", "config/modules/build.yaml",
                "config/personas/mike.md", "core/build/writer.py",
                ".git/config", ".env", "vertex-key.json"):
        out = W.apply(job, None, [{"path": rel, "content": "x"}], persona=PERSONA)
        assert "REFUSED" in out, f"{rel}: {out}"


@check("Build may not raise its own ceiling or edit itself")
def _():
    job = reset()
    for rel in ("config/modules/build.yaml", "core/build/writer.py",
                "core/build/schemas.py"):
        out = W.apply(job, None, [{"path": rel, "content": "x"}], persona=PERSONA)
        assert "deny list" in out, f"{rel} must be refused BY THE DENY LIST: {out}"


@check("a path outside the allow-roots is refused")
def _():
    job = reset()
    for path in ("docs/NEW.md", "tests/test_new.py",
                 str(FIXTURE / "data" / "personas" / PERSONA / "logs" / "x.json"),
                 str(TMP / "outside_the_repo.txt")):
        out = W.apply(job, None, [{"path": path, "content": "x"}], persona=PERSONA)
        assert "REFUSED" in out, f"{path}: {out}"


@check("another job's directory is refused")
def _():
    job = reset()
    other = J.jobs_dir(PERSONA) / "BLD-0101-01" / "question_set.json"
    out = W.apply(job, None, [{"path": str(other), "content": "{}"}], persona=PERSONA)
    assert "REFUSED" in out, out


@check("with git unavailable, apply() refuses everything")
def _():
    job = reset()
    saved = W._GIT
    try:
        W._GIT = ["definitely-not-a-git-binary", "ls-files", "-z"]
        assert W._tracked_paths() is None, "a missing git must read as UNKNOWN, not empty"
        out = W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
        assert "REFUSED" in out and "could not be evaluated" in out, out
    finally:
        W._GIT = saved


# ---------------------------------------------------------------------------
# The record's shape
# ---------------------------------------------------------------------------

@check("a record with only one routing entry is refused")
def _():
    import yaml
    job = reset()
    for drop in ("local", "cloud"):
        edits = edits_for("home_care", job)
        record = yaml.safe_load(edits[1]["content"])
        record["routing"].pop(drop)
        edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
        out = W.apply(job, None, edits, persona=PERSONA)
        assert "REFUSED" in out and f"routing.{drop} is missing" in out, out


@check("routing entries whose grants differ are refused")
def _():
    import yaml
    job = reset()
    edits = edits_for("home_care", job)
    record = yaml.safe_load(edits[1]["content"])
    record["routing"]["cloud"]["allowed_tools"] = ["get_weather"]
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "differ" in out, out


@check("a record pinning a model id instead of a model_ref is refused")
def _():
    import yaml
    job = reset()
    edits = edits_for("home_care", job)
    record = yaml.safe_load(edits[1]["content"])
    record["routing"]["cloud"]["model_ref"] = "gemini-3.8-flash"
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "not an agent name" in out, out


@check("a record whose agent_sha256 does not match the file is refused")
def _():
    import yaml
    job = reset()
    edits = edits_for("home_care", job)
    record = yaml.safe_load(edits[1]["content"])
    record["agent_sha256"] = "0" * 64
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "agent_sha256" in out, out


@check("name collision across all three sets is refused")
def _():
    job = reset()
    # time_director: agent file only, in NEITHER routing file. A routing-only
    # check would pass it, and the record would then be split across the seams.
    for name in ("time_director", "local_only_agent", "cloud_only_agent"):
        out = W.apply(job, None, edits_for(name, job), persona=PERSONA)
        assert "REFUSED" in out and "collides with a tracked agent" in out, \
            f"{name}: {out}"


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------

@check("every refused grant is refused, at all three ceilings")
def _():
    job = reset()
    refused = ["send_email", "send_calendar_invite", "write_calendar_event",
               "update_calendar_event", "delete_calendar_event", "fetch_url",
               "fetch_rendered", "run_subagent", "run_model_conference",
               "write_agent_config", "write_config", "write_persona",
               "write_schedule", "delete_schedule", "open_obligation",
               "close_obligation", "reopen_obligation", "record_horizon_item",
               "write_goals", "update_goal", "merge_wisdom_entries"]
    for ceiling in CEILINGS:
        set_ceiling(ceiling)
        for tool in refused:
            out = W.apply(job, None, edits_for("home_care", job, grant=[tool]),
                          persona=PERSONA)
            assert "REFUSED" in out and "outside the read set" in out, \
                f"{tool} at ceiling {ceiling}: {out}"


@check("the allowlist complement: every live tool outside the read set is refused")
def _():
    """
    The v3.1 assertion, and the reason the grant list is an ALLOWLIST.

    A deny list cannot enclose this surface: merge_contacts, unmerge_contacts,
    import_contacts_file, apply_crm_proposals, teach_intake,
    record_wisdom_response, log_interaction and create_semantic_anchor are all
    mutators that an "every write_*" rule misses entirely. This walks the LIVE
    register_tools() so the test tracks the surface as it grows, rather than a
    list someone has to remember to extend.
    """
    from core.orchestrator import register_tools
    schemas, handlers = register_tools()
    live = {s["name"] for s in schemas} | set(handlers)
    outside = sorted(live - W.ALLOWED_GRANTS)
    assert len(outside) > 30, f"expected a large complement, got {len(outside)}"
    for named in ("merge_contacts", "apply_crm_proposals", "teach_intake",
                  "log_interaction", "create_semantic_anchor"):
        assert named in outside, f"{named} should be outside the read set"

    job = reset()
    for tool in outside:
        out = W.apply(job, None, edits_for("home_care", job, grant=[tool]),
                      persona=PERSONA)
        assert "REFUSED" in out, f"{tool} was not refused: {out}"


@check("an agent file naming a tool outside its grant is refused")
def _():
    job = reset()
    edits = edits_for("home_care", job)
    edits[0]["content"] = edits[0]["content"].replace(
        "`get_weather` for what the weather did.",
        "`send_email` to tell them about it.")
    # The record's sha must still match, or that defect masks this one.
    import yaml
    record = yaml.safe_load(edits[1]["content"])
    record["agent_sha256"] = hashlib.sha256(
        edits[0]["content"].encode("utf-8")).hexdigest()
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "outside its own grant" in out, out


# ---------------------------------------------------------------------------
# The ceiling
# ---------------------------------------------------------------------------

@check("agent-file creation above the ceiling PARKS rather than drops")
def _():
    job = reset()
    set_ceiling("generated_registration", may_create=False)
    out = W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
    assert out.startswith("PARKED"), out
    assert J.get(job, PERSONA)["state"] == "awaiting_approval", J.get(job, PERSONA)
    assert not (W.overlay_dir(PERSONA) / "agents" / "home_care.md").exists()


@check("an over-length agent file is refused, and config cannot raise the floor")
def _():
    job = reset()
    W._CONFIG_PATH.write_text(BUILD_YAML.replace("max_lines: 220", "max_lines: 9999"))
    assert W.max_agent_lines() == W.MAX_AGENT_LINES, \
        "config raised the hardcoded floor"
    edits = edits_for("home_care", job)
    edits[0]["content"] = edits[0]["content"] + ("\nfiller\n" * 300)
    import yaml
    record = yaml.safe_load(edits[1]["content"])
    record["agent_sha256"] = hashlib.sha256(
        edits[0]["content"].encode("utf-8")).hexdigest()
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "line limit" in out, out


@check("an agent file without the confidentiality clause is refused")
def _():
    job = reset()
    edits = edits_for("home_care", job)
    edits[0]["content"] = edits[0]["content"].split("## Confidentiality")[0]
    import yaml
    record = yaml.safe_load(edits[1]["content"])
    record["agent_sha256"] = hashlib.sha256(
        edits[0]["content"].encode("utf-8")).hexdigest()
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "Confidentiality" in out, out


# ---------------------------------------------------------------------------
# Undo
# ---------------------------------------------------------------------------

@check("revert() restores byte-identical for agent file, record, policy and journal")
def _():
    job = reset()
    overlay, policies = W.overlay_dir(PERSONA), J.build_dir(PERSONA) / "policies"
    artifact = J.job_dir(job, PERSONA) / "evidence.jsonl"

    # Four PRE-EXISTING files, one of every kind the writer produces, each with
    # bytes that must come back exactly.
    prior = {
        overlay / "agents" / "home_care.md": "# an older agent file\nwith two lines\n",
        overlay / "capabilities" / "home_care.yaml": "schema: junk\nname: home_care\n",
        policies / "weekend_mail.json": '{"id": "weekend_mail", "v": 1}\n',
        artifact: '{"row": 1}\n{"row": 2}\n',
    }
    for path, content in prior.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    before = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in prior}

    edits = edits_for("home_care", job)
    edits.append({"path": str(policies / "weekend_mail.json"),
                  "content": '{"id": "weekend_mail", "v": 2}'})
    edits.append({"path": str(artifact), "content": '{"row": 99}\n'})
    out = W.apply(job, None, edits, persona=PERSONA)
    assert out.startswith("OK"), out
    for path in prior:
        assert hashlib.sha256(path.read_bytes()).hexdigest() != before[path], \
            f"{path.name} was not actually overwritten, so the revert proves nothing"

    assert "reverted" in W.revert(job, PERSONA)
    for path in prior:
        assert hashlib.sha256(path.read_bytes()).hexdigest() == before[path], \
            f"{path.name} did not come back byte-identical"


@check("revert() removes files that did not exist before")
def _():
    job = reset()
    W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
    agent = W.overlay_dir(PERSONA) / "agents" / "home_care.md"
    assert agent.exists()
    W.revert(job, PERSONA)
    assert not agent.exists(), "a file the writer created must be removed"


@check("a second revert is a no-op, and the journal survives as a record")
def _():
    job = reset()
    W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
    W.revert(job, PERSONA)
    again = W.revert(job, PERSONA)
    assert "nothing to revert" in again, again
    replayed = list(J.job_dir(job, PERSONA).glob("undo.reverted.*.jsonl"))
    assert len(replayed) == 1, replayed


@check("the journal is written BEFORE the bytes")
def _():
    job = reset()
    W.apply(job, None, edits_for("home_care", job), persona=PERSONA)
    entries = [json.loads(ln) for ln in
               W.undo_path(job, PERSONA).read_text().splitlines() if ln.strip()]
    assert len(entries) == 2, entries
    for entry in entries:
        assert entry["existed"] is False, entry
        assert entry["sha256_before"] == "", entry


# ---------------------------------------------------------------------------
# A name that is also an English word
# ---------------------------------------------------------------------------

@check("a common-word name lands and does not suppress ordinary prose")
def _():
    from core.orchestrator import filter_output, _CANNED_FALLBACK
    from core.persona import persona_scope

    job = reset()
    out = W.apply(job, None, edits_for("garden", job, display="Garden"),
                  persona=PERSONA)
    assert out.startswith("OK"), out
    OV.clear_cache()

    with persona_scope(PERSONA):
        assert "garden" in OV.confidential_names(), OV.confidential_names()

        ordinary = "I watered the garden this morning."
        assert filter_output(ordinary, "synthesizer") == ordinary, \
            "an ordinary sentence was suppressed by a capability name"

        # The mechanism, isolated: `garden` alone is harmless, `garden` beside
        # architecture vocabulary is not. Nothing in this sentence is on any
        # tracked list, so only the overlay name can be doing the work.
        leak = "The garden specialist was dispatched to handle that."
        assert filter_output(leak, "synthesizer") == _CANNED_FALLBACK, \
            "the capability name never reached the sentence-gated tier"

        # The plan's own example. Belt and braces: `routing.yaml` would trip
        # tier 1 on its own, so this asserts the outcome, not the mechanism.
        assert filter_output("the garden agent's routing.yaml entry",
                             "synthesizer") == _CANNED_FALLBACK


@check("a hyphenated form of an underscore name is left alone")
def _():
    from core.orchestrator import filter_output
    from core.persona import persona_scope

    job = reset()
    assert W.apply(job, None, edits_for("home_care", job),
                   persona=PERSONA).startswith("OK")
    OV.clear_cache()
    with persona_scope(PERSONA):
        ordinary = "Your home-care tasks are up to date."
        assert filter_output(ordinary, "synthesizer") == ordinary, \
            "home_care on the UNCONDITIONAL list would have eaten this reply"


# ---------------------------------------------------------------------------
# The six defects from the phase 3 second-model review (2026-09-19)
# ---------------------------------------------------------------------------

@check("REVIEW 1: the undo journal cannot be written, and revert() re-checks every path")
def _():
    """
    revert() was a WRITE PRIMITIVE WITH NO PATH RULES. It replayed whatever the
    journal named, and the journal sits inside an allow-root — so a plan that
    could write one entry could name any path on the machine and have revert()
    restore it. apply()'s three rules were bypassed by the undo mechanism.
    """
    job = reset()

    # (a) the journal itself is not a writable artifact
    out = W.apply(job, None,
                  [{"path": str(W.undo_path(job, PERSONA)), "content": "{}"}],
                  persona=PERSONA)
    assert "REFUSED" in out, out

    # (b) a forged entry naming a deny-listed path is skipped, not replayed
    assert W.apply(job, None, edits_for("home_care", job),
                   persona=PERSONA).startswith("OK")
    target = FIXTURE / "core" / "router.py"
    assert not target.exists(), "fixture precondition"
    forged = {"path": str(target), "rel": "core/router.py", "existed": True,
              "sha256_before": hashlib.sha256(b"pwned").hexdigest(),
              "size_before": 5,
              "bytes_before": base64.b64encode(b"pwned").decode("ascii")}
    with open(W.undo_path(job, PERSONA), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(forged) + "\n")
    W.revert(job, PERSONA)
    assert not target.exists(), "revert() wrote a deny-listed tracked path"


@check("REVIEW 2: a display_name that resolves to a tracked agent is refused")
def _():
    """
    The NAME was checked against three sets; the DISPLAY NAME was not checked at
    all. It is the string the Coordinator copies and the string seam 3 splices
    into the closed valid-name list, so a record displaying "Mental Wellbeing"
    puts a duplicate in that list and points its directory entry at a tracked
    agent — shadowing by the one field the name rule did not cover.
    """
    job = reset()
    for display in ("Mental Wellbeing", "Time Director", "Research",
                    "Logistics", "Pattern Miner"):
        out = W.apply(job, None, edits_for("home_care", job, display=display),
                      persona=PERSONA)
        assert "REFUSED" in out and "display_name" in out, f"{display}: {out}"


@check("REVIEW 3: a tool named WITHOUT backticks is still caught")
def _():
    """
    Both scans required backticks. `send_email` written as bare prose passed
    every gate, and a model writing an instruction file has no reason to
    backtick consistently.
    """
    import yaml
    job = reset()
    edits = edits_for("home_care", job)
    edits[0]["content"] = edits[0]["content"].replace(
        "Compact JSON.", "When it matters, send_email the household about it.")
    record = yaml.safe_load(edits[1]["content"])
    record["agent_sha256"] = hashlib.sha256(
        edits[0]["content"].encode("utf-8")).hexdigest()
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "outside its own grant" in out, out


@check("REVIEW 5: a record that sets its own provider is refused")
def _():
    """
    `model_ref` existed so a record could not pin a stale model id — and the
    record could still pin a PROVIDER, which seam 2 honoured via setdefault. A
    record could therefore route itself to a different vendor entirely while
    every field looked correct.
    """
    import yaml
    job = reset()
    edits = edits_for("home_care", job)
    record = yaml.safe_load(edits[1]["content"])
    record["routing"]["cloud"]["provider"] = "anthropic"
    edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
    out = W.apply(job, None, edits, persona=PERSONA)
    assert "REFUSED" in out and "provider" in out, out


@check("REVIEW 5b: a model_ref absent from EITHER routing file is refused")
def _():
    import yaml
    job = reset()
    for ref in ("local_only_agent", "cloud_only_agent"):
        edits = edits_for("home_care", job)
        record = yaml.safe_load(edits[1]["content"])
        record["routing"]["cloud"]["model_ref"] = ref
        edits[1]["content"] = yaml.safe_dump(record, sort_keys=False)
        out = W.apply(job, None, edits, persona=PERSONA)
        assert "REFUSED" in out and "model_ref" in out, f"{ref}: {out}"


@check("REVIEW 6: find_places needs a named risks[] entry in the plan")
def _():
    """
    The plan says a capability wanting find_places "must list it in risks[],
    which N8b reads and the brief shows Mike". Nothing enforced that, so the one
    outbound grant carrying user-composed free text was handed out silently.
    """
    job = reset()
    grant = GRANT + ["find_places"]

    out = W.apply(job, None, edits_for("home_care", job, grant=grant),
                  persona=PERSONA)
    assert "REFUSED" in out and "find_places" in out, out

    out = W.apply(job, {"risks": ["the tool sends a composed query off-machine"]},
                  edits_for("home_care", job, grant=grant), persona=PERSONA)
    assert "REFUSED" in out, "a risks[] entry that does not NAME the grant passed"

    out = W.apply(job, {"risks": ["find_places sends a composed query off-machine"]},
                  edits_for("home_care", job, grant=grant), persona=PERSONA)
    assert out.startswith("OK"), out


# ---------------------------------------------------------------------------
# Part 2 of the review (2026-09-19) — what the first round's fixes left beside them
# ---------------------------------------------------------------------------

@check("REVIEW N1: a display_name colliding with another OVERLAY record is refused")
def _():
    """
    Defect 2 stopped a generated capability capturing a TRACKED agent's
    dispatch. It said nothing about a second generated capability capturing the
    first one's — and the second landed capability is exactly the Section 11
    bootstrap sequence.
    """
    job = reset()
    assert W.apply(job, None, edits_for("home_care", job, display="Home Care"),
                   persona=PERSONA).startswith("OK")

    # (a) the same display string twice — the closed list would carry it twice
    out = W.apply(job, None, edits_for("garden", job, display="Home Care"),
                  persona=PERSONA)
    assert "REFUSED" in out and "display_name" in out, out

    # (b) a display that normalises to another record's NAME
    assert W.apply(job, None, edits_for("garden", job, display="Garden Care"),
                   persona=PERSONA).startswith("OK")
    out = W.apply(job, None, edits_for("weeding", job, display="Garden"),
                  persona=PERSONA)
    assert "REFUSED" in out and "display_name" in out, out


@check("REVIEW N2: a display_name differing only by whitespace or case is refused")
def _():
    """
    `Mental  Wellbeing` passes the charset, normalises to `mental__wellbeing`
    which is not tracked, and lowercases to a string not in the reserved set —
    so it splices into the closed list one space away from the real entry, on a
    model whose own map comment records it cannot reliably copy that list.
    """
    job = reset()
    for display in ("Mental  Wellbeing", "Time  Director", "MENTAL  WELLBEING"):
        out = W.apply(job, None, edits_for("home_care", job, display=display),
                      persona=PERSONA)
        assert "REFUSED" in out and "display_name" in out, f"{display!r}: {out}"


@check("REVIEW N4: the undo journal rule is case-insensitive and inode-aware")
def _():
    """
    macOS only, and recorded because the tests run there. The name rule was a
    case-sensitive string test on a case-insensitive filesystem, so `Undo.jsonl`
    passed check_path() and is the SAME INODE as the journal. revert() now
    refuses paths outside the allow-roots, so a forged journal cannot reach a
    tracked file — but it could still restore arbitrary bytes into another
    capability's overlay agent file, bypassing every content gate.
    """
    job = reset()
    assert W.apply(job, None, edits_for("home_care", job),
                   persona=PERSONA).startswith("OK")
    journal = W.undo_path(job, PERSONA)
    assert journal.exists(), "fixture precondition"
    before = journal.read_bytes()
    for name in ("Undo.jsonl", "UNDO.JSONL", "Undo.JSONL",
                 "undo.reverted.20260101T000000.jsonl"):
        out = W.apply(job, None,
                      [{"path": str(journal.parent / name), "content": "forged"}],
                      persona=PERSONA)
        assert "REFUSED" in out, f"{name}: {out}"
    assert journal.read_bytes() == before, "the journal was modified"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
