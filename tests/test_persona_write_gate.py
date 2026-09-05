"""
tests/test_persona_write_gate.py — [DB-0815-11] the approval gate on inferred
preferences, its toggle, and the pre-write redundancy check.

The incident these cover, 2026-08-18 at 09:17:27Z: the tool wrote an Interaction
Preference into `config/personas/mike.md` that nobody had asked for — *"Open sessions
with the most time-sensitive commitment, overdue follow-up, or unresolved thread,
naming it specifically…"* — and the next morning's rule audit scored it **0.88 against
`config/templates/scheduler.yaml:21`**. Every persona already had that instruction from
the template. Two silent failures in one write: it was self-applied, and it was a second
copy of a rule already in force.

Mike's ruling of 2026-08-28 splits into the two halves tested here:

  1. An **inferred** preference is proposed, not written. The user approving it in the
     app is what writes it, through the same fingerprinted `consume()` path
     `write_config` uses — the model is not in the consent path. A **stated** preference
     is ungated: that is the user speaking, not the tool guessing. And the gate is a
     **switch**, so it can be turned off once the inference earns trust.
  2. A preference that restates a rule already in force is **refused before it is
     written**, on both paths, with the reply naming where that rule lives.

Standalone runner, no pytest dependency — same shape as
tests/test_confirmation_gate.py.

Run:  python3 tests/test_persona_write_gate.py
"""

import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

os.environ.setdefault("METATRON_AUTH_PASSWORD", "test-password-not-the-real-one")
os.environ["METATRON_PERSONA"] = "test_persona_gate"

import yaml  # noqa: E402

import core.persona as PERSONA  # noqa: E402
import core.rule_classes as RC  # noqa: E402
import tools.confirm as CF  # noqa: E402
import tools.persona as PS  # noqa: E402

# The literal template prompt the 2026-08-18 write duplicated.
_TEMPLATE_PROMPT = (
    "Good morning. Open with whatever is most time-sensitive today — a commitment, an "
    "overdue follow-up, or an unresolved thread from recent context. Name it "
    "specifically rather than asking a general question. If genuinely nothing is "
    "outstanding, keep it to one line and ask what is on."
)

# The preference that was self-applied that morning, verbatim in shape.
_DUPLICATE_PREFERENCE = (
    "- Open sessions with the most time-sensitive commitment, overdue follow-up, or "
    "unresolved thread, naming it specifically rather than asking a general question."
)

_PERSONA_SEED = "# test_persona_gate\n\n## Identity\n\n- Lives in London.\n"


class _fixture:
    """Point tools.persona, tools.confirm and the rule corpus at temp directories.

    Each module binds its persona helpers by name at import, so each needs its own
    patch — same reasoning as tests/test_crm_merge_guard.py. `core.rule_classes.ROOT`
    is patched too, so the redundancy corpus is the fixture's and not the live repo's:
    the 08-18 case is reproduced here rather than depended upon in a file that other
    sessions edit.
    """

    def __init__(self, template_prompt: str | None = _TEMPLATE_PROMPT,
                 auto_accept: bool | None = None, prefs_text: str | None = None):
        self._template_prompt = template_prompt
        self._auto_accept = auto_accept
        self._prefs_text = prefs_text

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)

        self.persona_file = self.path / "personas" / "test_persona_gate.md"
        self.persona_file.parent.mkdir(parents=True, exist_ok=True)
        self.persona_file.write_text(_PERSONA_SEED)

        # A rule corpus of exactly one shared rule, on line 21 of the template — the
        # citation the 2026-08-19 audit produced.
        fake_root = self.path / "root"
        agents = fake_root / "config" / "agents"
        agents.mkdir(parents=True, exist_ok=True)
        # One agent rule of the `repetition` class, sharing no vocabulary with the
        # preference that matches it. That is the case the class matcher exists for,
        # and the case that must warn rather than refuse.
        (agents / "synthesizer.md").write_text(
            "# Synthesizer\n\n"
            "**Raise a thing once.** An open item you have already surfaced is not "
            "raised again in a later session unless something about it changed.\n")
        templates = fake_root / "config" / "templates"
        templates.mkdir(parents=True, exist_ok=True)
        lines = [f"# padding line {i}" for i in range(1, 21)]
        if self._template_prompt:
            lines.append(f'    prompt: "{self._template_prompt}"')
        (templates / "scheduler.yaml").write_text("\n".join(lines) + "\n")

        # The persona's own config dir, which is where a preferences.yaml override lives.
        self.config_dir = self.path / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if self._prefs_text is not None:
            (self.config_dir / "preferences.yaml").write_text(self._prefs_text)
        elif self._auto_accept is not None:
            (self.config_dir / "preferences.yaml").write_text(yaml.safe_dump(
                {"proactive": {"persona": {"inferred_write_auto_accept": self._auto_accept}}}))

        self._orig = {
            "ps_md": PS.persona_md,
            "cf_data": CF.persona_data_dir,
            "rc_root": RC.ROOT,
            "config_dir": PERSONA.persona_config_dir,
        }
        PS.persona_md = lambda persona=None: self.persona_file
        CF.persona_data_dir = lambda persona=None: self.path / "data"
        RC.ROOT = fake_root
        PERSONA.persona_config_dir = lambda persona=None: self.config_dir
        return self

    def __exit__(self, *exc):
        PS.persona_md = self._orig["ps_md"]
        CF.persona_data_dir = self._orig["cf_data"]
        RC.ROOT = self._orig["rc_root"]
        PERSONA.persona_config_dir = self._orig["config_dir"]
        self._tmp.cleanup()

    def text(self) -> str:
        return self.persona_file.read_text()


_NEW_PREFERENCE = "- Never open with a pleasantry; start with the substance."


# ---------------------------------------------------------------------------
# 1. The gate on inferred preferences
# ---------------------------------------------------------------------------

def test_inferred_write_with_the_gate_on_proposes_and_writes_nothing():
    with _fixture() as fx:
        before = fx.text()
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="inferred")
        assert isinstance(result, dict), result
        assert result["status"] == "PENDING_CONFIRMATION", result
        assert result["confirm_token"], result
        assert "NOT been performed" in result["instruction"], result
        # The whole point: the file is byte-identical afterwards.
        assert fx.text() == before, "an inferred preference was written before approval"


def test_the_proposal_card_stands_alone_and_says_it_was_not_asked_for():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="inferred")
        desc = result["description"]
        assert "Interaction Preferences" in desc, desc
        assert "pleasantry" in desc, desc
        assert "did not ask" in desc, desc
        assert fx.text() == _PERSONA_SEED


def test_the_confirm_path_writes_the_preference():
    with _fixture() as fx:
        pending = PS.write_persona(section="Interaction Preferences",
                                   content=_NEW_PREFERENCE, source="inferred")
        token = pending["confirm_token"]
        assert CF.approve(token) is True
        outcome = CF.execute(token)
        assert outcome["status"] == "executed", outcome
        assert "Persona updated" in outcome["result"], outcome
        assert _NEW_PREFERENCE in fx.text(), fx.text()
        assert "## Interaction Preferences" in fx.text(), fx.text()


def test_write_persona_is_wired_into_the_confirm_executor_registry():
    # Without this the user taps Approve and the server has nothing to call — the
    # [DB-0815-03] failure ("waiting for your approval in the app", forever).
    assert CF._EXECUTORS.get("write_persona") == ("tools.persona", "write_persona"), \
        CF._EXECUTORS


def test_an_approval_cannot_be_spent_on_different_content():
    with _fixture() as fx:
        pending = PS.write_persona(section="Interaction Preferences",
                                   content=_NEW_PREFERENCE, source="inferred")
        token = pending["confirm_token"]
        CF.approve(token)

        swapped = PS.write_persona(section="Interaction Preferences",
                                   content="- Always call me by my surname.",
                                   source="inferred", confirm_token=token)
        assert isinstance(swapped, str) and swapped.startswith("Error: not written."), swapped
        assert "surname" not in fx.text(), fx.text()


def test_an_approval_is_single_use():
    with _fixture():
        pending = PS.write_persona(section="Interaction Preferences",
                                   content=_NEW_PREFERENCE, source="inferred")
        token = pending["confirm_token"]
        CF.approve(token)
        assert CF.execute(token)["status"] == "executed"

        again = PS.write_persona(section="Interaction Preferences",
                                 content=_NEW_PREFERENCE, source="inferred",
                                 confirm_token=token)
        assert isinstance(again, str) and again.startswith("Error: not written."), again


# ---------------------------------------------------------------------------
# 2. Stated preferences are ungated, and the safe default when nothing is said
# ---------------------------------------------------------------------------

def test_a_stated_preference_writes_straight_through():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="user_stated")
        assert isinstance(result, str), result
        assert "Persona updated" in result, result
        assert _NEW_PREFERENCE in fx.text(), fx.text()
        # And it raised nothing for the user to approve.
        assert CF.pending() == [], CF.pending()


def test_an_absent_source_is_treated_as_inferred():
    # The safe side. A model that omits the field must not get the ungated path for free.
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE)
        assert isinstance(result, dict) and result["status"] == "PENDING_CONFIRMATION", result
        assert fx.text() == _PERSONA_SEED


def test_an_unrecognised_source_is_treated_as_inferred():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="obviously_stated")
        assert isinstance(result, dict) and result["status"] == "PENDING_CONFIRMATION", result
        assert fx.text() == _PERSONA_SEED


# ---------------------------------------------------------------------------
# 3. The toggle
# ---------------------------------------------------------------------------

def test_the_gate_is_on_by_default():
    # No persona preferences file at all: the shipped config/preferences.yaml answers,
    # and a missing or silent config must never mean "skip the gate".
    with _fixture():
        assert PS._inferred_write_auto_accept() is False


def test_the_toggle_off_lets_an_inferred_preference_write_directly():
    with _fixture(auto_accept=True) as fx:
        assert PS._inferred_write_auto_accept() is True
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="inferred")
        assert isinstance(result, str) and "Persona updated" in result, result
        assert _NEW_PREFERENCE in fx.text(), fx.text()
        assert CF.pending() == [], CF.pending()


def test_the_toggle_switches_back_on():
    with _fixture(auto_accept=False) as fx:
        assert PS._inferred_write_auto_accept() is False
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="inferred")
        assert isinstance(result, dict), result
        assert fx.text() == _PERSONA_SEED


def test_an_unreadable_preferences_file_leaves_the_gate_on():
    with _fixture(prefs_text="proactive: [this is not a mapping\n"):
        assert PS._inferred_write_auto_accept() is False, \
            "failing toward the confirmation is the only safe direction here"


# ---------------------------------------------------------------------------
# 4. The pre-write redundancy check — the 2026-08-18 duplicate
# ---------------------------------------------------------------------------

def test_a_preference_already_held_by_the_template_is_refused_by_name():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_DUPLICATE_PREFERENCE, source="user_stated")
        assert isinstance(result, str), result
        assert result.startswith("Error: not written."), result
        # It must say WHERE the rule already lives — that is what makes the refusal
        # lossless. A refusal that only says "duplicate" throws the instruction away.
        assert "config/templates/scheduler.yaml:21" in result, result
        assert "Good morning." in result, result
        assert "INSTRUCTION_CHANGE_REQUEST" in result, result
        assert fx.text() == _PERSONA_SEED, "a refused write still changed the file"


def test_the_same_refusal_applies_to_an_inferred_preference_and_raises_no_card():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_DUPLICATE_PREFERENCE, source="inferred")
        assert isinstance(result, str) and result.startswith("Error: not written."), result
        # Refused before the gate: asking the user to approve something that will then
        # be refused is noise in the approval queue.
        assert CF.pending() == [], CF.pending()
        assert fx.text() == _PERSONA_SEED


def test_a_preference_covered_by_nothing_proceeds():
    with _fixture() as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_NEW_PREFERENCE, source="user_stated")
        assert isinstance(result, str) and "Persona updated" in result, result
        assert _NEW_PREFERENCE in fx.text(), fx.text()


def test_with_no_shared_rule_present_the_same_preference_writes():
    # Proves the refusal above comes from the template rule and not from the wording.
    with _fixture(template_prompt=None) as fx:
        result = PS.write_persona(section="Interaction Preferences",
                                  content=_DUPLICATE_PREFERENCE, source="user_stated")
        assert isinstance(result, str) and "Persona updated" in result, result
        assert "time-sensitive" in fx.text(), fx.text()


def test_rewriting_a_section_does_not_trip_on_its_own_existing_lines():
    # The schema requires the full section content on every update, so a rewrite
    # re-sends every preference already in the file. Only genuinely new lines are
    # checked — otherwise the second edit of any section would be refused forever.
    with _fixture() as fx:
        first = PS.write_persona(section="Interaction Preferences",
                                 content=_NEW_PREFERENCE, source="user_stated")
        assert "Persona updated" in first, first

        second = PS.write_persona(
            section="Interaction Preferences",
            content=_NEW_PREFERENCE + "\n- Use British spelling.",
            source="user_stated")
        assert isinstance(second, str) and "Persona updated" in second, second
        assert "British spelling" in fx.text(), fx.text()
        # And the section was replaced, not appended twice.
        assert fx.text().count("## Interaction Preferences") == 1, fx.text()


def test_the_weaker_class_overlap_still_only_warns():
    # A shared rule CLASS without near-verbatim wording may be a genuine personal
    # refinement, so it is recorded with a note rather than refused. Unchanged
    # behaviour, asserted so the refusal above cannot quietly swallow this case.
    with _fixture() as fx:
        result = PS.write_persona(
            section="Interaction Preferences",
            content="- Do not keep bringing up the same task over and over.",
            source="user_stated")
        assert isinstance(result, str) and "Persona updated" in result, result
        assert "may already be covered" in result, result
        assert "bringing up" in fx.text(), fx.text()


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append(name)
                print(f"  FAIL  {name}: {type(exc).__name__}: {exc}")
    print()
    print(f"{len(failures)} failed" if failures else "all passed")
    sys.exit(1 if failures else 0)


def test_a_one_word_rule_is_never_a_home():
    """`prompt: "Check in."` scored 1.000 against anything mentioning a check-in.

    The overlap coefficient divides by the smaller set, so a rule reducing to a single
    content word matched everything and out-ranked every genuine candidate. On
    2026-09-05 that refused a real user instruction while citing a line reading
    `prompt: "Check in."` as the rule's home — a refusal Mike could not verify, and one
    that would have sent him to edit the wrong file.
    """
    from core.rule_classes import Rule, similarity
    tiny = Rule("Check in.", "config/templates/scheduler.yaml", "scheduler", 52)
    real = Rule("During check-ins with nothing urgent to share, use the opportunity "
                "to ask what is going on.", "<new>", "persona")
    assert len(tiny.words) == 1, tiny.words
    score = similarity(real, tiny)
    assert score < 0.4, f"a one-word rule still out-ranks everything: {score}"


def test_the_floor_leaves_genuine_short_rules_alone():
    """Three content words, not more: a real short rule must still be able to be a home."""
    from core.rule_classes import Rule, similarity
    short = Rule("Do not tell the user to enjoy things.", "config/agents/synthesizer.md",
                 "agent", 82)
    restated = Rule("Never tell me to enjoy something.", "<new>", "persona")
    assert len(short.words) >= 3, short.words
    assert similarity(restated, short) >= 0.4, similarity(restated, short)


def test_shared_rules_covers_the_modules_conduct():
    """The corpus went stale when the scheduled-session conduct moved out of the agent
    files in the 2026-08-27 audit — nothing moved the corpus with it."""
    from core.rule_classes import shared_rules
    sources = {r.source for r in shared_rules(None)}
    assert any("config/modules/" in s for s in sources), sorted(sources)
