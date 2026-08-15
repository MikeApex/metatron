"""
tests/test_profile_language.py — unit tests for the [DB-0810-15] language fields
in tools/profile.py: input_language and output_language.

Standalone runner (no pytest dependency), matching the convention of
tests/test_persona_resolver.py.

Usage:
    python tests/test_profile_language.py

Exits 0 if every test passes, 1 otherwise.

One test below (`fields land in core.orchestrator.load_profile()'s prompt`) is
expected to FAIL as shipped. tools/profile.py stores the two fields correctly
and read_profile() renders them on demand, but the system-prompt summary that
actually reaches the model is built by a *separate*, hand-written function —
core/orchestrator.py's load_profile() — which lists each renderable field by
name (`if profile.get("name"): ...`, `if profile.get("occupation"): ...`, etc.)
rather than deriving from tools/profile.py's WRITABLE or _PROMPT_EXCLUDED.
core/orchestrator.py is outside this change's file manifest, so the two new
`if profile.get("input_language")` / `if profile.get("output_language")` lines
that would make this pass are not added here. Left failing on purpose rather
than deleted, so the gap is visible instead of silently unverified.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.orchestrator as ORC  # noqa: E402
import tools.profile as PR  # noqa: E402

_results: list[tuple[str, bool, str]] = []


def check(name: str):
    """Decorator: run a test function, record pass/fail rather than aborting."""
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


class _temp_persona_dir:
    """
    Point both tools.profile and core.orchestrator at an empty temp directory
    for the duration of the block, so tests never touch a real persona's
    profile.yaml. Both modules bind persona_config_dir by name at import time
    (`from core.persona import persona_config_dir`), so each needs its own
    patch — patching core.persona itself would not reach either copy.
    """
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig_pr = PR.persona_config_dir
        self._orig_orc = ORC.persona_config_dir
        PR.persona_config_dir = lambda persona=None: self.path
        ORC.persona_config_dir = lambda persona=None: self.path
        return self.path

    def __exit__(self, *exc):
        PR.persona_config_dir = self._orig_pr
        ORC.persona_config_dir = self._orig_orc
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Independent settability
# ---------------------------------------------------------------------------

@check("input_language settable on its own, output_language stays unset")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("input_language", "Bulgarian")
        assert "Profile updated" in result, result
        assert PR._load().get("input_language") == "bg", PR._load()
        assert "output_language" not in PR._load(), PR._load()


@check("output_language settable on its own, input_language stays unset")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("output_language", "English")
        assert "Profile updated" in result, result
        assert PR._load().get("output_language") == "en", PR._load()
        assert "input_language" not in PR._load(), PR._load()


@check("setting one after the other leaves the first untouched — the asymmetric case")
def _():
    with _temp_persona_dir():
        # Mike's worked example: input Bulgarian, output English.
        PR.write_profile("input_language", "Bulgarian")
        PR.write_profile("output_language", "English")
        data = PR._load()
        assert data.get("input_language") == "bg", data
        assert data.get("output_language") == "en", data


@check("both set to the same language — the matching case is not special-cased away")
def _():
    with _temp_persona_dir():
        PR.write_profile("input_language", "Bulgarian")
        PR.write_profile("output_language", "Bulgarian")
        data = PR._load()
        assert data.get("input_language") == "bg", data
        assert data.get("output_language") == "bg", data


# ---------------------------------------------------------------------------
# Representation
# ---------------------------------------------------------------------------

@check("a bare ISO 639-1 code is accepted directly, lowercased")
def _():
    with _temp_persona_dir():
        PR.write_profile("input_language", "BG")
        assert PR._load().get("input_language") == "bg"


@check("a language name is normalized to its ISO 639-1 code, not stored as prose")
def _():
    with _temp_persona_dir():
        PR.write_profile("output_language", "english")
        assert PR._load().get("output_language") == "en"


# ---------------------------------------------------------------------------
# Unset is a valid state
# ---------------------------------------------------------------------------

@check("neither field set: read_profile shows no language entry")
def _():
    with _temp_persona_dir():
        PR.write_profile("name", "Test Persona")
        summary = PR.read_profile()
        assert "input_language" not in summary, summary
        assert "output_language" not in summary, summary


@check("no profile at all: read_profile says nothing recorded")
def _():
    with _temp_persona_dir():
        assert PR.read_profile() == "No profile recorded yet."


# ---------------------------------------------------------------------------
# Refusal style
# ---------------------------------------------------------------------------

@check("unrecognized language text is refused, module's existing Error: style")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("input_language", "Klingon")
        assert isinstance(result, str) and result.startswith("Error:"), result
        assert PR._load().get("input_language") is None


@check("empty value is refused same as any other field")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("input_language", "   ")
        assert result.startswith("Error:"), result


@check("unknown field name is still refused loudly, and the two language fields are listed")
def _():
    with _temp_persona_dir():
        result = PR.write_profile("preferred_language", "Bulgarian")
        assert result.startswith("Error:"), result
        assert "input_language" in result and "output_language" in result, result


# ---------------------------------------------------------------------------
# Rendering into read_profile() (this module's own summary)
# ---------------------------------------------------------------------------

@check("both fields appear in read_profile()'s summary once set")
def _():
    with _temp_persona_dir():
        PR.write_profile("input_language", "Bulgarian")
        PR.write_profile("output_language", "English")
        summary = PR.read_profile()
        assert "input_language: bg" in summary, summary
        assert "output_language: en" in summary, summary


@check("read_profile('input_language') answers a targeted lookup")
def _():
    with _temp_persona_dir():
        PR.write_profile("input_language", "Bulgarian")
        assert PR.read_profile("input_language") == "input_language: bg"


# ---------------------------------------------------------------------------
# Rendering into the actual system-prompt summary — core.orchestrator.load_profile()
#
# This is the requirement that matters for the feature to work at all: the
# Synthesizer only sees what reaches the system prompt. See module docstring —
# expected to fail until core/orchestrator.py's load_profile() is given two
# more lines matching its existing per-field pattern; that file is outside
# this change's manifest.
# ---------------------------------------------------------------------------

@check("fields land in core.orchestrator.load_profile()'s prompt")
def _():
    with _temp_persona_dir():
        PR.write_profile("input_language", "Bulgarian")
        PR.write_profile("output_language", "English")
        prompt = ORC.load_profile()
        assert "bg" in prompt, prompt
        assert "en" in prompt, prompt


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed

    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")

    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
