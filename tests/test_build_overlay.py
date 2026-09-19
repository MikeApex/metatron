"""
tests/test_build_overlay.py — the four load seams.

THE CLAIM UNDER TEST: a generated capability is reachable through every path the
runtime uses to reach a specialist, a TRACKED agent is never shadowed or
disturbed by one, and a broken overlay record cannot take a session down.

The four seams, and what each would break if it were missing:

  1  load_agent()          no instruction file    -> FileNotFoundError mid-turn
  2  _load_routing()       no model, no grants    -> "no entry in the routing config"
  3  the Coordinator prompt  the name is not in the closed valid-name list, so
                            the model has been TOLD the capability is invalid
  4  consequence / filter /  a failure names the agent; the name is unfiltered;
     domain map             its wisdom domain reaches nobody

Seam 3 is the one with a subtlety worth stating: the valid-name list is a CLOSED
list inside a cached system prompt. The alternative — injecting the new name as
a context block — was withdrawn because it leaves the system prompt saying the
name is invalid and a context block saying it is valid, on a model whose own
_AGENT_NAME_MAP comment records that it cannot reliably copy even the existing
list. So the sentence itself is rewritten at assembly, IN MEMORY, and this suite
asserts config/agents/coordinator.md is byte-unchanged afterwards.

Records here are written DIRECTLY rather than through core/build/writer.py. That
is deliberate: this suite tests what the seams do with a record, and coupling it
to the writer would mean a writer bug could hide a seam bug.

Standalone runner (no pytest dependency), matching tests/ convention.

Usage:
    python3 tests/test_build_overlay.py

Exits 0 if every check passes, 1 otherwise.
"""

import hashlib
import os
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import core.build.jobs as J          # noqa: E402
import tools.wisdom as WIS           # noqa: E402
from core.build import overlay as OV  # noqa: E402

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


TMP = Path(tempfile.mkdtemp(prefix="build_overlay_test_"))

# Kept, because the PersonaError check below has to put it back. The stub
# defaults to "mike" and so never calls resolve_persona() — which means the
# unbound-persona path is UNREACHABLE while it is installed, and a test of that
# path written against the stub would pass without exercising anything.
_REAL_PERSONA_DATA_DIR = J.persona_data_dir
J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or "mike")

COORDINATOR_MD = ROOT / "config" / "agents" / "coordinator.md"
COORDINATOR_SHA = hashlib.sha256(COORDINATOR_MD.read_bytes()).hexdigest()

AGENT_TEXT = "# Home Care\n\n## Role\nHousehold upkeep.\n"


def write_record(persona: str, name: str, display: str,
                 domains: list[str] | None = None, **overrides) -> None:
    import yaml
    overlay = J.build_dir(persona) / "overlay"
    (overlay / "agents").mkdir(parents=True, exist_ok=True)
    (overlay / "capabilities").mkdir(parents=True, exist_ok=True)
    (overlay / "agents" / f"{name}.md").write_text(AGENT_TEXT, encoding="utf-8")
    record = {
        "schema": "overlay_capability/1",
        "name": name,
        "display_name": display,
        "job_id": "BLD-0918-01",
        "version": 1,
        "generated_at": "2026-09-18T12:00:00",
        "agent_file": f"agents/{name}.md",
        "agent_sha256": hashlib.sha256(AGENT_TEXT.encode()).hexdigest(),
        "routing": {
            "local": {"local": True, "allowed_tools": ["get_weather", "read_wisdom"]},
            "cloud": {"model_ref": "mental_wellbeing",
                      "allowed_tools": ["get_weather", "read_wisdom"]},
        },
        "coordinator": {"directory_entry": f"**{display}**\nCall when: it is due."},
        "unavailable_consequence": "their household upkeep",
        "confidential_names": [name],
        "knowledge_domains": domains if domains is not None else ["home"],
        "execution_mode": "blocking",
        "latency_budget_ms": 8000,
    }
    record.update(overrides)
    (overlay / "capabilities" / f"{name}.yaml").write_text(
        yaml.safe_dump(record, sort_keys=False), encoding="utf-8")


def reset(persona: str = "mike") -> None:
    build = J.build_dir(persona)
    if build.exists():
        shutil.rmtree(build)
    OV.clear_cache()
    WIS._domain_map_cache.clear()


# ---------------------------------------------------------------------------
# SEAM 1 — load_agent
# ---------------------------------------------------------------------------

@check("seam 1: load_agent returns the overlay file when no tracked file exists")
def _():
    from core.orchestrator import load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        assert load_agent("home_care").startswith("# Home Care"), "overlay not reached"


@check("seam 1: a tracked agent is never shadowed by an overlay record of that name")
def _():
    from core.orchestrator import load_agent
    from core.persona import persona_scope
    reset()
    tracked = load_agent("logistics")
    write_record("mike", "logistics", "Logistics")
    OV.clear_cache()
    with persona_scope("mike"):
        assert load_agent("logistics") == tracked, "the tracked file lost"
        assert "logistics" not in OV.records_for("mike"), "a tracked name was served"


@check("seam 1: an unknown agent still raises FileNotFoundError")
def _():
    from core.orchestrator import load_agent
    from core.persona import persona_scope
    reset()
    with persona_scope("mike"):
        try:
            load_agent("no_such_agent")
        except FileNotFoundError:
            return
    raise AssertionError("an unknown agent must still raise")


# ---------------------------------------------------------------------------
# SEAM 2 — routing
# ---------------------------------------------------------------------------

@check("seam 2: resolve_model returns the model_ref agent's live model and the grant")
def _():
    import yaml
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    tracked = yaml.safe_load((ROOT / "config" / "modules" / "routing_cloud.yaml")
                             .read_text())["agents"]["mental_wellbeing"]
    saved = os.environ.get("DEPLOYMENT_MODE")
    os.environ["DEPLOYMENT_MODE"] = "cloud"
    try:
        from core.router import resolve_model
        with persona_scope("mike"):
            cfg = resolve_model("home_care")
        assert cfg.model == tracked["model"], (cfg.model, tracked["model"])
        assert cfg.allowed_tools == ["get_weather", "read_wisdom"], cfg.allowed_tools
    finally:
        if saved is None:
            os.environ.pop("DEPLOYMENT_MODE", None)
        else:
            os.environ["DEPLOYMENT_MODE"] = saved


@check("seam 2: a model_ref that resolves to nothing is SKIPPED, not half-registered")
def _():
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care",
                 routing={"local": {"local": True, "allowed_tools": []},
                          "cloud": {"provider": "gemini",
                                    "model_ref": "no_such_agent",
                                    "allowed_tools": []}})
    saved = os.environ.get("DEPLOYMENT_MODE")
    os.environ["DEPLOYMENT_MODE"] = "cloud"
    try:
        from core.router import resolve_model
        with persona_scope("mike"):
            try:
                resolve_model("home_care")
            except RuntimeError as exc:
                assert "no entry in the routing config" in str(exc), exc
                return
        raise AssertionError("an unresolvable model_ref must not register an entry")
    finally:
        if saved is None:
            os.environ.pop("DEPLOYMENT_MODE", None)
        else:
            os.environ["DEPLOYMENT_MODE"] = saved


@check("seam 2: a tracked agent's routing is untouched by the overlay")
def _():
    from core.persona import persona_scope
    from core.router import resolve_model
    reset()
    before = resolve_model("logistics")
    write_record("mike", "home_care", "Home Care")
    OV.clear_cache()
    with persona_scope("mike"):
        after = resolve_model("logistics")
    assert (before.provider, before.model, before.allowed_tools) == \
           (after.provider, after.model, after.allowed_tools), (before, after)


# ---------------------------------------------------------------------------
# SEAM 3 — the Coordinator's prompt
# ---------------------------------------------------------------------------

@check("seam 3: the display name appears exactly once inside the closed list")
def _():
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        prompt = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
    line = [ln for ln in prompt.splitlines()
            if ln.startswith('`"Mental Wellbeing"`')]
    assert len(line) == 1, f"expected one valid-name line, got {len(line)}"
    assert line[0].count('`"Home Care"`') == 1, line[0]
    assert '`"Pattern Miner"`' in line[0], "the existing list was damaged"


@check("seam 3: the directory entry lands INSIDE the Specialist directory")
def _():
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        prompt = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
    start = prompt.find("## Specialist directory")
    nxt = prompt.find("\n## ", start + 1)
    section = prompt[start:nxt if nxt != -1 else len(prompt)]
    assert "**Home Care**" in section, "the entry is outside the directory section"
    assert "Additional specialists" not in prompt, \
        "a second directory is a second place to look; the Coordinator reads one"


@check("seam 3: coordinator.md on disk is byte-unchanged after assembly")
def _():
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
    assert hashlib.sha256(COORDINATOR_MD.read_bytes()).hexdigest() == COORDINATOR_SHA, \
        "seam 3 wrote to the tracked file — it must rewrite in memory only"


@check("seam 3: with no overlay the prompt is returned untouched")
def _():
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    original = load_agent("coordinator")
    with persona_scope("mike"):
        assert _overlay_coordinator_prompt(original, "mike") == original


@check("seam 3: the display name maps back to the record name")
def _():
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        assert OV.name_map_additions("mike") == {"home care": "home_care"}


# ---------------------------------------------------------------------------
# SEAM 4 — consequence, filter, domain map
# ---------------------------------------------------------------------------

@check("seam 4: a failure names the consequence, never the agent")
def _():
    from core.orchestrator import _unavailable_notice
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    with persona_scope("mike"):
        notice = _unavailable_notice("home_care")
    assert "their household upkeep" in notice, notice
    assert "home_care" not in notice, "the agent's name reached the notice"


@check("seam 4: the domain map carries the capability under its declared domain")
def _():
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care", domains=["home"])
    with persona_scope("mike"):
        mapping = WIS.domain_agent_map()
    assert "home_care" in mapping.get("home", []), mapping.get("home")
    assert "logistics" in mapping.get("home", []), "a tracked agent was displaced"


@check("seam 4: a record may join an existing domain, never create one")
def _():
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care", domains=["not_a_domain"])
    with persona_scope("mike"):
        mapping = WIS.domain_agent_map()
    assert "not_a_domain" not in mapping, mapping.keys()


@check("seam 4: the domain map cache is keyed by persona, in either call order")
def _():
    from core.persona import persona_scope
    for order in (("mike", "danny_park"), ("danny_park", "mike")):
        reset("mike")
        reset("danny_park")
        write_record("mike", "home_care", "Home Care", domains=["home"])
        write_record("danny_park", "bike_care", "Bike Care", domains=["recreation"])
        WIS._domain_map_cache.clear()
        OV.clear_cache()
        seen = {}
        for persona in order:
            with persona_scope(persona):
                seen[persona] = WIS.domain_agent_map()
        assert "home_care" in seen["mike"]["home"], (order, seen["mike"]["home"])
        assert "bike_care" not in seen["mike"].get("recreation", []), \
            f"order {order}: danny_park's capability leaked into mike's map"
        assert "bike_care" in seen["danny_park"]["recreation"], order
        assert "home_care" not in seen["danny_park"].get("home", []), \
            f"order {order}: mike's capability leaked into danny_park's map"


# ---------------------------------------------------------------------------
# Robustness — the seams fail OPEN
# ---------------------------------------------------------------------------

@check("a malformed record is skipped, and every tracked agent still loads")
def _():
    from core.orchestrator import load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    overlay = J.build_dir("mike") / "overlay" / "capabilities"
    (overlay / "broken.yaml").write_text("{{{ not yaml at all", encoding="utf-8")
    (overlay / "wrong_schema.yaml").write_text(
        "schema: something_else/9\nname: wrong_schema\n", encoding="utf-8")
    OV.clear_cache()
    with persona_scope("mike"):
        records = OV.load_overlay("mike")
        assert set(records) == {"home_care"}, set(records)
        assert load_agent("logistics").strip(), "a tracked agent stopped loading"
        assert load_agent("home_care").startswith("# Home Care")


@check("a record whose name does not match its filename is skipped")
def _():
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    path = J.build_dir("mike") / "overlay" / "capabilities" / "home_care.yaml"
    path.write_text(path.read_text().replace("name: home_care", "name: something_else"),
                    encoding="utf-8")
    OV.clear_cache()
    with persona_scope("mike"):
        assert OV.load_overlay("mike") == {}, OV.load_overlay("mike")


@check("PersonaError: no persona bound means no overlay, and nothing tracked breaks")
def _():
    from core.orchestrator import load_agent
    from core.router import resolve_model
    reset()
    write_record("mike", "home_care", "Home Care")
    OV.clear_cache()
    from core.persona import PersonaError, resolve_persona
    saved_env = {k: os.environ.pop(k, None)
                 for k in ("METATRON_PERSONA", "AI_TEST_PERSONA",
                           "METATRON_PERSONA_FALLBACK")}
    J.persona_data_dir = _REAL_PERSONA_DATA_DIR
    try:
        try:
            resolve_persona()
            raise AssertionError("this environment resolves a persona with none "
                                 "bound, so the check cannot mean anything here")
        except PersonaError:
            pass
        # The three assertions that matter: no overlay, and NOTHING TRACKED
        # BREAKS. Letting PersonaError propagate would make a tracked agent's
        # routing raise where it does not today — a change to the Red-tier path
        # rather than an inheritance, which is why the loader swallows it.
        assert OV.load_overlay() == {}, "an unbound persona must yield no overlay"
        assert load_agent("logistics").strip(), "a tracked agent stopped loading"
        assert resolve_model("logistics") is not None, "tracked routing raised"
    finally:
        J.persona_data_dir = lambda persona=None: TMP / "personas" / (persona or "mike")
        for key, value in saved_env.items():
            if value is not None:
                os.environ[key] = value


@check("the cache picks up a new record without a restart")
def _():
    from core.persona import persona_scope
    reset()
    with persona_scope("mike"):
        assert OV.load_overlay("mike") == {}
        write_record("mike", "home_care", "Home Care")
        assert set(OV.load_overlay("mike")) == {"home_care"}, \
            "the mtime fingerprint did not notice a new record"


# ---------------------------------------------------------------------------
# The phase 3 review (2026-09-19) — the seam halves
# ---------------------------------------------------------------------------

@check("REVIEW 2b: seam 3 skips a display name that resolves to a tracked agent")
def _():
    """
    The schema refuses such a record, but the seam must agree independently —
    a record that reached the overlay by any other route must not be able to
    put a duplicate into the Coordinator's closed valid-name list.
    """
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Mental Wellbeing")
    with persona_scope("mike"):
        prompt = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
        line = [ln for ln in prompt.splitlines()
                if ln.startswith('`"Mental Wellbeing"`')][0]
        assert line.count('`"Mental Wellbeing"`') == 1, \
            f"seam 3 duplicated a tracked display name: {line}"
        assert "mental wellbeing" not in OV.name_map_additions("mike"), \
            "the overlay remapped a tracked display name"


@check("REVIEW 5c: seam 2 ignores a provider set on the record")
def _():
    """
    model_ref must carry BOTH provider and model from the tracked agent. A
    record that could pin a provider could route itself to another vendor.
    """
    import yaml
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    path = J.build_dir("mike") / "overlay" / "capabilities" / "home_care.yaml"
    record = yaml.safe_load(path.read_text())
    record["routing"]["cloud"]["provider"] = "anthropic"
    path.write_text(yaml.safe_dump(record, sort_keys=False), encoding="utf-8")
    OV.clear_cache()

    tracked = yaml.safe_load((ROOT / "config" / "modules" / "routing_cloud.yaml")
                             .read_text())["agents"]["mental_wellbeing"]
    saved = os.environ.get("DEPLOYMENT_MODE")
    os.environ["DEPLOYMENT_MODE"] = "cloud"
    try:
        from core.router import resolve_model
        with persona_scope("mike"):
            cfg = resolve_model("home_care")
        assert cfg.provider == tracked.get("provider", "gemini"), \
            f"seam 2 honoured the record's provider: {cfg.provider}"
    finally:
        if saved is None:
            os.environ.pop("DEPLOYMENT_MODE", None)
        else:
            os.environ["DEPLOYMENT_MODE"] = saved


# ---------------------------------------------------------------------------
# Part 2 of the review (2026-09-19)
# ---------------------------------------------------------------------------

@check("REVIEW N1b: seam 3 skips a duplicate display name")
def _():
    """
    The schema refuses the second record; the seam must agree independently, so
    the closed valid-name list can never carry the same string twice whatever
    reached the overlay.
    """
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope
    reset()
    write_record("mike", "home_care", "Home Care")
    write_record("mike", "garden", "Home Care")
    with persona_scope("mike"):
        names, _entries = OV.coordinator_additions("mike")
        assert names.count("Home Care") == 1, names
        prompt = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
        line = [ln for ln in prompt.splitlines()
                if ln.startswith('`"Mental Wellbeing"`')][0]
        assert line.count('`"Home Care"`') == 1, line
        assert len(OV.name_map_additions("mike")) == 1, OV.name_map_additions("mike")


@check("REVIEW P3-1: seam 3 collapses whitespace before resolving a display name")
def _():
    """
    The schema collapses internal whitespace before every display-name
    comparison (N2); the seam did not, and resolved the RAW string. So a
    hand-placed record displaying `Mental  Wellbeing` normalised to
    `mental__wellbeing`, missed the tracked set, and was surfaced into the
    closed valid-name list and the name map.

    Reach is narrow — the writer refuses such a record and the sweep's overlay
    pass flags it, so this needs both lines bypassed. It matters because it is
    the one place the seam and the schema stopped agreeing, and seam/schema
    agreement is the property the whole correction round set out to hold.

    Built from the reviewer's probe: the double-space form was surfaced; the
    `&`, `and`, padded and upper-case forms were already excluded, and are
    asserted here so a fix to one cannot regress the others.
    """
    from core.orchestrator import _overlay_coordinator_prompt, load_agent
    from core.persona import persona_scope

    # The prompt as assembled with NO overlay. A skipped record must leave it
    # byte-identical — a stronger claim than "the string is absent", and the
    # correct one: `  Mental Wellbeing  ` strips to a string that is already in
    # the closed list as the TRACKED entry, so absence is not what is being
    # asserted here.
    reset()
    with persona_scope("mike"):
        baseline = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")

    for display in ("Mental  Wellbeing", "Mental & Wellbeing",
                    "Mental and Wellbeing", "  Mental Wellbeing  ",
                    "MENTAL WELLBEING", "Time  Director"):
        reset()
        write_record("mike", "home_care", display)
        with persona_scope("mike"):
            names, entries = OV.coordinator_additions("mike")
            assert names == [], f"{display!r} was surfaced: {names}"
            assert entries == [], f"{display!r} added a directory entry: {entries}"
            assert OV.name_map_additions("mike") == {}, \
                f"{display!r} entered the name map: {OV.name_map_additions('mike')}"
            prompt = _overlay_coordinator_prompt(load_agent("coordinator"), "mike")
            assert prompt == baseline, \
                f"{display!r} changed the assembled Coordinator prompt"


# ---------------------------------------------------------------------------

if __name__ == "__main__":
    failed = 0
    for name, ok, detail in _results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}{'' if ok else '  — ' + detail}")
        failed += 0 if ok else 1
    print(f"\n{len(_results) - failed}/{len(_results)} passed")
    shutil.rmtree(TMP, ignore_errors=True)
    sys.exit(1 if failed else 0)
