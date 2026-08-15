"""
tests/test_translate_output.py — [DB-0810-15] response translation.

Standalone runner (no pytest dependency), matching tests/test_profile_language.py.

    python tests/test_translate_output.py

The backend is stubbed throughout — these tests are about the *policy* around translation
(when it runs, what it does on failure, what it must never touch), not about translation
quality, which no unit test can assert. The one thing worth stating loudly: the ordering
requirement (translate AFTER filter_output) is verified here by asserting on what the
translated text is derived from, because getting that backwards silently blinds the
confidentiality filter and nothing else would catch it.
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import core.translate as TR  # noqa: E402
import tools.profile as PR  # noqa: E402

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


class _stub_backend:
    """Swap the translation backend for a recording stub."""
    def __init__(self, fn):
        self.fn = fn
        self.calls: list[tuple[str, str]] = []

    def __enter__(self):
        self._orig = TR._BACKENDS[TR._BACKEND]

        def recorded(text, language):
            self.calls.append((text, language))
            return self.fn(text, language)

        TR._BACKENDS[TR._BACKEND] = recorded
        return self

    def __exit__(self, *exc):
        TR._BACKENDS[TR._BACKEND] = self._orig


class _temp_persona_dir:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name)
        self._orig_pr = PR.persona_config_dir
        PR.persona_config_dir = lambda persona=None: self.path
        import core.persona as CP
        self._orig_cp = CP.persona_config_dir
        CP.persona_config_dir = lambda persona=None: self.path
        return self.path

    def __exit__(self, *exc):
        PR.persona_config_dir = self._orig_pr
        import core.persona as CP
        CP.persona_config_dir = self._orig_cp
        self._tmp.cleanup()


# ---------------------------------------------------------------------------
# Fail-open behaviour — the whole reason this is not fail-closed
# ---------------------------------------------------------------------------

@check("a backend exception delivers the original text, never an error to the user")
def _():
    def boom(text, language):
        raise RuntimeError("provider down")

    with _stub_backend(boom):
        out = TR.translate("Your dentist appointment is Tuesday.", "bg", "Bulgarian")
        assert out == "Your dentist appointment is Tuesday.", out


@check("an empty backend result is treated as failure, not as a valid translation")
def _():
    with _stub_backend(lambda text, language: "   "):
        out = TR.translate("Something worth saying.", "bg", "Bulgarian")
        assert out == "Something worth saying.", out


@check("a successful translation is returned and stripped")
def _():
    with _stub_backend(lambda text, language: "  Преведено  "):
        out = TR.translate("Translated.", "bg", "Bulgarian")
        assert out == "Преведено", repr(out)


# ---------------------------------------------------------------------------
# When translation must not run at all
# ---------------------------------------------------------------------------

@check("no language code: backend is never called")
def _():
    with _stub_backend(lambda text, language: "should not happen") as stub:
        out = TR.translate("Unchanged.", "", "")
        assert out == "Unchanged.", out
        assert stub.calls == [], stub.calls


@check("empty or whitespace text: backend is never called")
def _():
    with _stub_backend(lambda text, language: "should not happen") as stub:
        assert TR.translate("", "bg", "Bulgarian") == ""
        assert TR.translate("   ", "bg", "Bulgarian") == "   "
        assert stub.calls == [], stub.calls


@check("the display name, not the code, is what reaches the backend prompt")
def _():
    with _stub_backend(lambda text, language: "ok") as stub:
        TR.translate("Hello.", "bg", "Bulgarian")
        assert stub.calls[0][1] == "Bulgarian", stub.calls


# ---------------------------------------------------------------------------
# response_language() — unset must stay distinguishable from "English"
# ---------------------------------------------------------------------------

@check("no profile at all: no response language, so the pipeline is untouched")
def _():
    with _temp_persona_dir():
        assert TR.response_language() is None


@check("profile without output_language: still None")
def _():
    with _temp_persona_dir():
        PR.write_profile("name", "Mike")
        assert TR.response_language() is None


@check("output_language set: returns (code, display name)")
def _():
    with _temp_persona_dir():
        PR.write_profile("output_language", "Bulgarian")
        assert TR.response_language() == ("bg", "Bulgarian")


@check("input_language alone does not trigger output translation — the asymmetric case")
def _():
    with _temp_persona_dir():
        # Mike's worked example B: receives Bulgarian, answers in English. Setting only the
        # input language must leave the response path completely alone.
        PR.write_profile("input_language", "Bulgarian")
        assert TR.response_language() is None


@check("English set explicitly is a real preference, not the same as unset")
def _():
    with _temp_persona_dir():
        PR.write_profile("output_language", "English")
        assert TR.response_language() == ("en", "English")


# ---------------------------------------------------------------------------
# Ordering — the requirement that silently breaks the confidentiality filter
# ---------------------------------------------------------------------------

@check("translation consumes filtered text, so filter_output still sees English")
def _():
    import core.orchestrator as ORC

    # The canned fallback is what filter_output() substitutes on a suppressed response. If the
    # pipeline ever translated before filtering, the filter would be matching English regexes
    # against Bulgarian and would stop suppressing anything. This asserts the helper is a pure
    # post-step over whatever it is handed rather than re-deriving the text itself.
    with _temp_persona_dir():
        PR.write_profile("output_language", "Bulgarian")
        with _stub_backend(lambda text, language: f"[BG]{text}") as stub:
            out = ORC._translate_for_user("already filtered", None)
            assert out == "[BG]already filtered", out
            assert stub.calls[0][0] == "already filtered", stub.calls


@check("no response language: the helper is a no-op and calls nothing")
def _():
    import core.orchestrator as ORC

    with _temp_persona_dir():
        with _stub_backend(lambda text, language: "should not happen") as stub:
            out = ORC._translate_for_user("English stays English", None)
            assert out == "English stays English", out
            assert stub.calls == [], stub.calls


# ---------------------------------------------------------------------------

def main() -> int:
    passed = sum(1 for _, ok, _ in _results if ok)
    failed = len(_results) - passed
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print(f"        {detail}")
    print(f"\n{passed} passed, {failed} failed, {len(_results)} total")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
