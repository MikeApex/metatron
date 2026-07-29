"""
tests/test_persona_resolver.py — unit tests for core/persona.py.

Standalone runner (no pytest dependency), matching the convention of the other
scripts in tests/.

Usage:
    python tests/test_persona_resolver.py

Exits 0 if every test passes, 1 otherwise.
"""

import os
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import persona as P  # noqa: E402

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


def _clear_env():
    for k in (P.ENV_PRIMARY, P.ENV_LEGACY, P.ENV_STRICT, P.ENV_FALLBACK):
        os.environ.pop(k, None)
    P._state.persona = None


def raises(exc, fn, *a, **kw):
    try:
        fn(*a, **kw)
    except exc:
        return True
    except Exception as e:
        raise AssertionError(f"expected {exc.__name__}, got {type(e).__name__}: {e}")
    raise AssertionError(f"expected {exc.__name__}, nothing raised")


# ---------------------------------------------------------------------------
# Name validation — the path-traversal guard
# ---------------------------------------------------------------------------

@check("valid names accepted")
def _():
    for good in ("mike", "pepys", "ryan_holiday", "test_a3", "a", "x9_9"):
        assert P.validate_persona_name(good) == good, good


@check("traversal and malformed names rejected")
def _():
    bad = [
        "../../etc", "..", ".", "/etc/passwd", "mike/../pepys",
        "Ryan Holiday", "Mike", "mike-1", "mike.md", "", "   ",
        "_leading", "9" * 41, "nul\x00byte",
    ]
    for name in bad:
        raises(P.PersonaError, P.validate_persona_name, name)


@check("non-string name rejected")
def _():
    raises(P.PersonaError, P.validate_persona_name, None)
    raises(P.PersonaError, P.validate_persona_name, 123)


@check("surrounding whitespace stripped, not rejected")
def _():
    assert P.validate_persona_name("  mike  ") == "mike"


# ---------------------------------------------------------------------------
# Resolution order
# ---------------------------------------------------------------------------

@check("explicit argument beats thread-local and env")
def _():
    _clear_env()
    os.environ[P.ENV_PRIMARY] = "pepys"
    with P.persona_scope("nin"):
        assert P.resolve_persona("mike") == "mike"
    _clear_env()


@check("thread-local beats env")
def _():
    _clear_env()
    os.environ[P.ENV_PRIMARY] = "pepys"
    with P.persona_scope("mike"):
        assert P.resolve_persona() == "mike"
    _clear_env()


@check("env used when nothing else set")
def _():
    _clear_env()
    os.environ[P.ENV_PRIMARY] = "pepys"
    assert P.resolve_persona() == "pepys"
    _clear_env()


@check("legacy AI_TEST_PERSONA still honoured")
def _():
    _clear_env()
    os.environ[P.ENV_LEGACY] = "aurelius"
    assert P.resolve_persona() == "aurelius"
    _clear_env()


@check("invalid value in env raises rather than silently passing through")
def _():
    _clear_env()
    os.environ[P.ENV_PRIMARY] = "../../etc"
    raises(P.PersonaError, P.resolve_persona)
    _clear_env()


# ---------------------------------------------------------------------------
# Fail-closed and audit mode
# ---------------------------------------------------------------------------

@check("strict is the default and raises when unresolved")
def _():
    _clear_env()
    assert P.is_strict() is True
    raises(P.PersonaError, P.resolve_persona)


@check("audit mode returns fallback and writes exactly one line")
def _():
    _clear_env()
    original = P._AUDIT_LOG
    with tempfile.TemporaryDirectory() as td:
        P._AUDIT_LOG = Path(td) / "audit.jsonl"
        os.environ[P.ENV_STRICT] = "0"
        os.environ[P.ENV_FALLBACK] = "mike"
        try:
            assert P.resolve_persona() == "mike"
            lines = P._AUDIT_LOG.read_text().strip().splitlines()
            assert len(lines) == 1, f"expected 1 audit line, got {len(lines)}"
            import json
            rec = json.loads(lines[0])
            assert rec["fallback_used"] == "mike"
            assert rec["stack"], "stack frames missing"
        finally:
            P._AUDIT_LOG = original
            _clear_env()


@check("audit mode WITHOUT a fallback still raises")
def _():
    _clear_env()
    os.environ[P.ENV_STRICT] = "0"
    raises(P.PersonaError, P.resolve_persona)
    _clear_env()


@check("audit mode with an INVALID fallback still raises")
def _():
    _clear_env()
    os.environ[P.ENV_STRICT] = "0"
    os.environ[P.ENV_FALLBACK] = "../evil"
    raises(P.PersonaError, P.resolve_persona)
    _clear_env()


# ---------------------------------------------------------------------------
# persona_scope
# ---------------------------------------------------------------------------

@check("scope sets and restores cleanly")
def _():
    _clear_env()
    assert P.current_persona() is None
    with P.persona_scope("mike"):
        assert P.resolve_persona() == "mike"
        assert os.environ[P.ENV_PRIMARY] == "mike"
        assert os.environ[P.ENV_LEGACY] == "mike"   # mirror for unconverted code
    assert P.current_persona() is None
    assert P.ENV_PRIMARY not in os.environ
    assert P.ENV_LEGACY not in os.environ


@check("scope restores even when the block raises")
def _():
    _clear_env()
    try:
        with P.persona_scope("mike"):
            raise ValueError("boom")
    except ValueError:
        pass
    assert P.current_persona() is None
    assert P.ENV_PRIMARY not in os.environ


@check("nested scopes restore the outer persona")
def _():
    _clear_env()
    with P.persona_scope("mike"):
        with P.persona_scope("pepys"):
            assert P.resolve_persona() == "pepys"
        assert P.resolve_persona() == "mike"
        assert os.environ[P.ENV_PRIMARY] == "mike"
    assert P.current_persona() is None


@check("scope preserves a pre-existing env value on exit")
def _():
    _clear_env()
    os.environ[P.ENV_PRIMARY] = "aurelius"
    with P.persona_scope("mike"):
        assert P.resolve_persona() == "mike"
    assert os.environ[P.ENV_PRIMARY] == "aurelius"
    _clear_env()


@check("invalid persona rejected at scope entry")
def _():
    _clear_env()
    raises(P.PersonaError, P.persona_scope("../../etc").__enter__)


# ---------------------------------------------------------------------------
# Thread isolation — the concurrency bug this module exists to fix
# ---------------------------------------------------------------------------

@check("concurrent threads do not see each other's persona")
def _():
    _clear_env()
    seen: dict[str, list[str]] = {}
    barrier = threading.Barrier(2)

    def worker(name: str):
        with P.persona_scope(name):
            barrier.wait(timeout=5)      # force overlap inside both scopes
            seen[name] = [P.resolve_persona() for _ in range(3)]

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("mike", "pepys")]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert seen.get("mike") == ["mike"] * 3, seen.get("mike")
    assert seen.get("pepys") == ["pepys"] * 3, seen.get("pepys")
    _clear_env()


# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

@check("path helpers build the expected locations")
def _():
    _clear_env()
    with P.persona_scope("mike"):
        assert P.persona_config_dir().as_posix().endswith("config/personas/mike")
        assert P.persona_data_dir().as_posix().endswith("data/personas/mike")
        assert P.persona_md().as_posix().endswith("config/personas/mike.md")
    _clear_env()


@check("path helpers reject a traversal name")
def _():
    _clear_env()
    raises(P.PersonaError, P.persona_data_dir, "../../etc")


@check("path helpers raise when no persona is bound")
def _():
    _clear_env()
    raises(P.PersonaError, P.persona_data_dir)


@check("list_personas finds mike and skips invalid names")
def _():
    names = P.list_personas()
    assert "mike" in names, names
    assert all(P._VALID_NAME.match(n) for n in names), names


# ---------------------------------------------------------------------------

def main() -> int:
    _clear_env()
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
