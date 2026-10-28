"""
tests/test_consent_enforcement.py — tone profiling runs only under her permission, withdrawing
it removes what was learned, and the code-only agents cannot be dispatched by another agent.

Plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.11 and § 6.1 item 15 (the parts
owned by tools/tone.py, tools/crm.py and tools/subagent.py); review findings P2 and P4.

  1. `get_tone_shape()` for a persona with no current `tone_profile` record returns
     `not_permitted` — no contact lookup, no mailbox read, ZERO model calls. With a grant it
     behaves as before (seeds in the background, then answers `ready`). Withdrawal takes effect
     on the very next call. `_extract()` refuses the same way, and re-checks before it writes.
  2. `forget_tone_profiles()` deletes `tone_shape` from every contact — and from the CRM archive,
     so an unmerge after a re-grant cannot restore a profile learned under the withdrawn
     permission — and `read_contact`/`list_contacts`/`search_contacts` then return none.
  3. A stored `tone_shape` is HIDDEN from those reads whenever no current record exists, even
     without a forget (the in-flight race, and merge-snapshot restores).
  4. `run_subagent` (and `run_model_conference`) refuse each of the five code-only agents with
     zero model calls; a normal specialist still dispatches; no `config/agents/*.md` names one.

Fail-closed is what makes these refusals provable: a persona with no consents.json has no
permission, and every persona here starts with none.

EVERY LIVE METER IS STUBBED: sockets are blocked (an attempt is counted and raises), the model
(`core.orchestrator.run_session`) is a counter, the mailbox (`tools.mail.search_correspondence`)
is a counter. `core.persona._ROOT` points at a temporary directory, so every persona path — the
contact store, its archive, consents.json — lives there; no tracked persona is touched.

    python3 tests/test_consent_enforcement.py        # standalone
    python -m pytest -q tests/test_consent_enforcement.py
"""
from __future__ import annotations

import json
import re
import socket
import sys
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.consent as CONSENT  # noqa: E402
import core.orchestrator as ORC  # noqa: E402
import core.persona as P  # noqa: E402
import tools.confirm as CF  # noqa: E402
import tools.crm as CRM  # noqa: E402
import tools.mail as MAIL  # noqa: E402
import tools.profile as PR  # noqa: E402
import tools.subagent as SUB  # noqa: E402
import tools.tone as TONE  # noqa: E402

_REPO = Path(__file__).parent.parent
_TMP = Path(tempfile.mkdtemp(prefix="consent_enforcement_"))
_CALLS: dict = {}
_MODEL_REPLY = json.dumps({
    "formality": "casual", "greeting_style": "Hey", "signoff_style": "x",
    "names_user_uses_for_them": ["Sam"],
})
CODE_ONLY = ("tone_profiler", "intake_extractor", "accountability_judge", "day_planner",
             "crm_sweep")


# --- the sandbox -----------------------------------------------------------------------------

class _Patches:
    """setattr with restore — so nothing leaks into other suites in one pytest process."""

    def __init__(self):
        self._saved: list[tuple[object, str, object]] = []

    def set(self, obj, name, value):
        self._saved.append((obj, name, getattr(obj, name)))
        setattr(obj, name, value)

    def restore(self):
        for obj, name, value in reversed(self._saved):
            setattr(obj, name, value)
        self._saved.clear()


def _blocked(kind):
    def fn(*args, **kwargs):
        _CALLS["network"].append(kind)
        raise OSError(f"network blocked in test ({kind})")
    return fn


def _run_session(agent_name, *args, **kwargs):
    _CALLS["model"].append(agent_name)
    hook = _CALLS.get("on_model")
    if hook:
        hook()
    return _MODEL_REPLY if agent_name == "tone_profiler" else f"{agent_name}: stub reply"


def _search_correspondence(address, *args, **kwargs):
    _CALLS["mail"].append(address)
    return {"sent_folder_found": True, "counts": {"sampled": 6},
            "security_note": "", "correspondence": "Hey Sam — see you Thursday. x"}


@contextmanager
def _sandbox(name: str):
    """A throwaway persona root under the temp dir, the model and mailbox stubbed, sockets
    blocked. Yields the persona name, bound on this thread."""
    root = _TMP / name
    root.mkdir(parents=True, exist_ok=True)
    _CALLS.update(network=[], model=[], mail=[], on_model=None)

    p = _Patches()
    # Every persona path in core.persona is built from _ROOT, so one patch moves them all.
    p.set(P, "_ROOT", root)
    # Modules that bound the path helpers by name — re-pointed at the real helpers in case
    # another suite in the same process left its own lambda behind.
    p.set(CRM, "persona_data_dir", P.persona_data_dir)
    if hasattr(CF, "persona_data_dir"):
        p.set(CF, "persona_data_dir", P.persona_data_dir)
    if hasattr(PR, "persona_config_dir"):
        p.set(PR, "persona_config_dir", P.persona_config_dir)
    p.set(ORC, "run_session", _run_session)
    p.set(MAIL, "search_correspondence", _search_correspondence)
    p.set(socket, "getaddrinfo", _blocked("dns"))
    p.set(socket, "create_connection", _blocked("connect"))
    p.set(socket.socket, "connect", _blocked("connect"))
    TONE._IN_FLIGHT.clear()
    persona = f"zz_consent_{name}"
    try:
        with P.persona_scope(persona):
            yield persona
    finally:
        _wait_for_profilers()
        p.restore()


def _wait_for_profilers(timeout: float = 5.0) -> None:
    """get_tone_shape profiles on a daemon thread; wait until none is in flight."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with TONE._IN_FLIGHT_LOCK:
            if not TONE._IN_FLIGHT:
                return
        time.sleep(0.01)
    raise AssertionError("tone profiler thread did not finish")


def _seed_contacts(*records: dict) -> None:
    CRM._save_contacts([{"interaction_log": [], "tags": [], **r} for r in records])


def _grant(persona: str) -> None:
    CONSENT.grant("tone_profile", persona, "v1", evidence="test fixture")


_SAM = {"id": "c_sam", "name": "Sam Okafor", "contact_info": {"email": "sam@okafor.org"},
        "tone_shape": "[derived from correspondence 2026-10-01; 6 msgs] formality: casual"}
_ROSA = {"id": "c_rosa", "name": "Rosa Lind", "contact_info": {"email": "rosa@lind.org"},
         "tone_shape": "[derived from correspondence 2026-10-02; 9 msgs] formality: warm"}
_NOPROFILE = {"id": "c_kim", "name": "Kim Park", "contact_info": {}, "tone_shape": ""}


def _reads() -> list[dict]:
    """Every contact record the three agent-facing read paths hand back."""
    out = [json.loads(CRM.read_contact(contact_id="c_sam")),
           json.loads(CRM.read_contact(name="Rosa"))]
    out += json.loads(CRM.list_contacts())
    out += json.loads(CRM.search_contacts("o"))          # matches every seeded name
    return out


# --- 1. tone profiling only under her permission ---------------------------------------------

def test_no_record_means_not_permitted_and_no_model_call():
    with _sandbox("none"):
        _seed_contacts({**_SAM, "tone_shape": ""})
        for kw in ({"name": "Sam"}, {"contact_id": "c_sam"}, {"contact_id": "c_sam",
                                                              "refresh": True}):
            result = TONE.get_tone_shape(**kw)
            assert result["status"] == "not_permitted", result
            assert "tone_shape" not in result, result
        _wait_for_profilers()
        assert _CALLS["model"] == [], f"model called: {_CALLS['model']}"
        assert _CALLS["mail"] == [], f"mailbox read: {_CALLS['mail']}"
        assert _CALLS["network"] == [], _CALLS["network"]


def test_extract_refuses_without_a_record():
    with _sandbox("extract_none") as persona:
        _seed_contacts({**_SAM, "tone_shape": ""})
        result = TONE._extract("sam@okafor.org", "c_sam", persona)
        assert result["status"] == "not_permitted", result
        assert _CALLS["model"] == [] and _CALLS["mail"] == [], _CALLS
        assert not CRM._load_contacts()[0]["tone_shape"]


def test_with_a_grant_it_behaves_as_before():
    with _sandbox("granted") as persona:
        _grant(persona)
        _seed_contacts({**_SAM, "tone_shape": ""})
        first = TONE.get_tone_shape(name="Sam")
        assert first["status"] == "seeding", first
        _wait_for_profilers()
        assert _CALLS["model"] == ["tone_profiler"], _CALLS["model"]
        assert _CALLS["mail"] == ["sam@okafor.org"], _CALLS["mail"]
        second = TONE.get_tone_shape(name="Sam")
        assert second["status"] == "ready", second
        assert "formality: casual" in second["tone_shape"], second
        assert len(_CALLS["model"]) == 1, "a ready profile must not call the model again"
        # And the CRM serves it, as it always has, while the record is current.
        assert "formality: casual" in json.loads(CRM.read_contact(contact_id="c_sam"))["tone_shape"]
        assert _CALLS["network"] == [], _CALLS["network"]


def test_withdrawal_takes_effect_on_the_next_call():
    with _sandbox("withdraw_next") as persona:
        _grant(persona)
        _seed_contacts(_SAM)
        assert TONE.get_tone_shape(name="Sam")["status"] == "ready"
        assert CONSENT.withdraw("tone_profile", persona) is True
        result = TONE.get_tone_shape(name="Sam")
        assert result["status"] == "not_permitted", result
        assert "tone_shape" not in result, result
        assert _CALLS["model"] == [], _CALLS["model"]
        # Re-granting restores the service — the record, not anything else, is the switch.
        _grant(persona)
        assert TONE.get_tone_shape(name="Sam")["status"] == "ready"


def test_a_withdrawal_during_a_profiling_run_stops_the_write():
    with _sandbox("withdraw_midrun") as persona:
        _grant(persona)
        _seed_contacts({**_SAM, "tone_shape": ""})
        _CALLS["on_model"] = lambda: CONSENT.withdraw("tone_profile", persona)
        result = TONE._extract("sam@okafor.org", "c_sam", persona)
        assert result["status"] == "not_permitted", result
        assert _CALLS["model"] == ["tone_profiler"], _CALLS["model"]
        assert not CRM._load_contacts()[0].get("tone_shape"), CRM._load_contacts()[0]


# --- 2. withdrawal removes what was learned --------------------------------------------------

def test_forget_deletes_every_profile_and_the_reads_return_none():
    with _sandbox("forget") as persona:
        _grant(persona)
        _seed_contacts(_SAM, _ROSA, _NOPROFILE)
        assert sum(1 for r in _reads() if r.get("tone_shape")) > 0   # served while granted

        CONSENT.withdraw("tone_profile", persona)
        cleared = TONE.forget_tone_profiles(persona)
        assert cleared == 2, cleared
        stored = CRM._load_contacts()
        assert all("tone_shape" not in c for c in stored), stored
        assert [c["id"] for c in stored] == ["c_sam", "c_rosa", "c_kim"], "a contact was lost"
        assert stored[0]["contact_info"] == _SAM["contact_info"], "another field was touched"

        for record in _reads():
            assert "tone_shape" not in record, record
        # Deleted, not hidden: a re-grant brings nothing back.
        _grant(persona)
        for record in _reads():
            assert not record.get("tone_shape"), record
        assert TONE.forget_tone_profiles(persona) == 0, "forget must be idempotent"


def test_forget_scrubs_the_archive_so_an_unmerge_cannot_restore_a_profile():
    with _sandbox("forget_archive") as persona:
        _grant(persona)
        _seed_contacts(_SAM, {**_ROSA, "id": "c_sam2", "name": "Sam O."})
        pending = CRM.merge_contacts(keep_id="c_sam", merge_id="c_sam2")
        token = json.loads(pending)["confirm_token"]
        assert CF.approve(token) is True
        assert CF.execute(token).get("status") == "executed"
        archived = list(CRM._crm_archive_dir().glob("*.json"))
        assert any("tone_shape" in json.loads(f.read_text()) for f in archived), archived

        CONSENT.withdraw("tone_profile", persona)
        assert TONE.forget_tone_profiles(persona) == 1
        for f in CRM._crm_archive_dir().glob("*.json"):
            rec = json.loads(f.read_text())
            assert "tone_shape" not in rec, (f.name, rec)
            assert rec.get("name"), "the archived record itself must survive"

        _grant(persona)
        assert CRM.unmerge_contacts(merge_id="c_sam2").startswith("Unmerged:")
        assert all(not c.get("tone_shape") for c in CRM._load_contacts()), CRM._load_contacts()


# --- 3. hidden without a current record, even without a forget -------------------------------

def test_a_stored_profile_is_hidden_without_a_current_record():
    with _sandbox("hidden") as persona:
        _seed_contacts(_SAM, _ROSA, _NOPROFILE)     # profiles on disk, no consents.json at all
        for record in _reads():
            assert "tone_shape" not in record, record
        # The store itself is untouched — the gate is on the read, not a write.
        assert CRM._load_contacts()[0]["tone_shape"] == _SAM["tone_shape"]

        _grant(persona)                              # the `mike` case: served exactly as before
        assert json.loads(CRM.read_contact(contact_id="c_sam"))["tone_shape"] == _SAM["tone_shape"]

        CONSENT.withdraw("tone_profile", persona)    # withdrawn but not yet forgotten
        for record in _reads():
            assert "tone_shape" not in record, record


def test_an_unreadable_consent_file_grants_nothing():
    with _sandbox("corrupt") as persona:
        _seed_contacts(_SAM)
        path = P.persona_data_dir(persona) / "consents.json"
        path.write_text("{not json")
        assert TONE.get_tone_shape(name="Sam")["status"] == "not_permitted"
        assert "tone_shape" not in json.loads(CRM.read_contact(contact_id="c_sam"))
        assert _CALLS["model"] == []


# --- 4. the code-only agents -----------------------------------------------------------------

def test_run_subagent_refuses_each_code_only_agent():
    with _sandbox("subagent"):
        variants = []
        for name in CODE_ONLY:
            variants += [name, name.upper(), name.replace("_", "-"), name.replace("_", " "),
                         f"../agents/{name}", f"./{name}.md"]
        for name in variants:
            for ff in (False, True):
                result = SUB.run_subagent(name, "describe this correspondence", fire_and_forget=ff)
                assert result.startswith("Error:") and "cannot be called" in result, (name, result)
            result = SUB.run_model_conference("x", ["cloud_fast"], agent_name=name)
            assert result.startswith("Error:"), (name, result)
        time.sleep(0.05)                              # any fire-and-forget thread would have run
        assert _CALLS["model"] == [], f"model called: {_CALLS['model']}"


def test_a_normal_specialist_still_dispatches():
    with _sandbox("specialist"):
        result = SUB.run_subagent("relationships", "who have I not called lately?")
        assert result == "relationships: stub reply", result
        assert _CALLS["model"] == ["relationships"], _CALLS["model"]


def test_the_code_callers_reach_their_agents_through_run_session_directly():
    """The refusal is name-based in run_subagent; the five callers must not route through it."""
    callers = {
        "tools/tone.py": "tone_profiler", "tools/intake_extract.py": "intake_extractor",
        "tools/accountability.py": "accountability_judge", "tools/day_plan.py": "day_planner",
        "tools/crm_sweep.py": "crm_sweep",
    }
    for rel, agent in callers.items():
        src = (_REPO / rel).read_text()
        assert "run_subagent" not in src, f"{rel} reaches run_subagent"
        # intake_extract.py names its agent through a variable (an eval-only override), so
        # the check is "calls run_session, and names the agent", not one call shape.
        assert "from core.orchestrator import run_session" in src, f"{rel} lost run_session"
        assert re.search(rf"[\"']{agent}[\"']", src), f"{rel} no longer names {agent}"
    assert set(SUB.CODE_ONLY_AGENTS) == set(CODE_ONLY)


def test_no_agent_file_names_a_code_only_agent():
    """An agent file that names one is where a dispatch instruction would start — via
    run_subagent or the Coordinator's SPECIALISTS_TO_CALL. Each agent's own file is exempt."""
    offenders = []
    for path in sorted((_REPO / "config" / "agents").glob("*.md")):
        text = path.read_text()
        for name in CODE_ONLY:
            if path.stem != name and re.search(rf"\b{name}\b", text):
                offenders.append(f"{path.name} names {name}")
    assert not offenders, offenders


# --- standalone ------------------------------------------------------------------------------

def main() -> int:
    tests = [(n, f) for n, f in list(globals().items())        # definition order
             if n.startswith("test_") and callable(f)]
    failed = 0
    for name, fn in tests:
        try:
            fn()
            print(f"  PASS  {name}")
        except Exception as exc:  # noqa: BLE001
            import traceback
            failed += 1
            print(f"  FAIL  {name}\n        {type(exc).__name__}: {exc}\n"
                  + "".join(traceback.format_exc().splitlines(True)[-4:]))
    print(f"\n{len(tests) - failed} passed, {failed} failed, {len(tests)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
