"""
tests/test_fetch_rendered.py — fetch_rendered, the headless-browser read tool.

[DB-0806-02] rendering half. Scope: archive/plans/level3_web_actions_scope_2026-08-06.md.

Three groups, same split as tests/test_untrusted_and_fetch.py:

1. SSRF/validation — offline, must never depend on a network or on Playwright being
   installed. These are the ones that matter most: they prove fetch_rendered goes
   through the exact same guards fetch_url does.
2. Graceful degradation — offline. Playwright is an optional dependency; the VM may
   never have it. This is the path production is most likely to actually exercise, so
   it is asserted explicitly rather than left to "well, it imports fine."
3. Live render — skipped unless METATRON_NETWORK_TESTS=1 AND Playwright + its Chromium
   binary are actually installed on this machine. Proves the real path once, when
   available; never required for a normal run.

Run:
    python tests/test_fetch_rendered.py
    METATRON_NETWORK_TESTS=1 python tests/test_fetch_rendered.py   (needs Playwright installed)
"""

import importlib.util
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.untrusted import TAG  # noqa: E402
from tools.web import fetch_rendered  # noqa: E402

LIVE = os.environ.get("METATRON_NETWORK_TESTS") == "1"
PLAYWRIGHT_AVAILABLE = importlib.util.find_spec("playwright") is not None


# --- module import must never depend on Playwright --------------------------

def test_module_imports_without_playwright():
    """
    tools/web.py must import cleanly on a machine with no Playwright at all — this is
    the whole point of the lazy import. Re-import in a subprocess with playwright made
    unresolvable, so this test is meaningful even on a dev machine where Playwright
    happens to be installed.
    """
    import subprocess
    code = (
        "import sys, builtins\n"
        "real_import = builtins.__import__\n"
        "def blocked(name, *a, **k):\n"
        "    if name == 'playwright' or name.startswith('playwright.'):\n"
        "        raise ImportError('playwright deliberately blocked for this test')\n"
        "    return real_import(name, *a, **k)\n"
        "builtins.__import__ = blocked\n"
        "import tools.web as w\n"
        "print('IMPORT_OK')\n"
        "r = w.fetch_rendered('https://example.com')\n"
        "assert 'error' in r, r\n"
        "assert 'Playwright is not installed' in r['error'], r\n"
        "print('DEGRADE_OK')\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(Path(__file__).parent.parent),
        capture_output=True, text=True, timeout=30,
    )
    assert "IMPORT_OK" in proc.stdout, f"module failed to import without playwright: {proc.stderr}"
    assert "DEGRADE_OK" in proc.stdout, (
        f"fetch_rendered did not degrade cleanly without playwright: {proc.stdout} {proc.stderr}"
    )
    assert proc.returncode == 0, proc.stderr


# --- graceful degradation, exercised directly in-process ---------------------

def test_returns_clean_error_when_playwright_absent_or_present():
    """
    Whatever this machine's Playwright state is, fetch_rendered on a blocked SSRF
    target must fail via the same validation fetch_url uses — before ever touching
    Playwright. Proves _check_url runs first regardless of the optional dependency.
    """
    r = fetch_rendered("http://127.0.0.1:8001/")
    assert "error" in r
    assert "Playwright" not in r["error"], "SSRF check should short-circuit before Playwright is touched"


def test_no_traceback_ever_on_missing_dependency():
    """The exact path the VM is expected to exercise: no traceback, no crash, just {error}."""
    r = fetch_rendered("https://example.com")
    assert isinstance(r, dict)
    if not PLAYWRIGHT_AVAILABLE:
        assert "error" in r
        assert "unavailable" in r["error"].lower()


# --- SSRF and validation: identical guards to fetch_url, offline ------------

def test_metadata_server_is_blocked():
    r = fetch_rendered("http://169.254.169.254/computeMetadata/v1/")
    assert "error" in r and "link-local" in r["error"]


def test_localhost_is_blocked():
    for target in ["http://127.0.0.1:8001/monitor/file?path=data/",
                   "http://localhost:8001/health"]:
        r = fetch_rendered(target)
        assert "error" in r, f"{target} was not blocked"


def test_private_ranges_are_blocked():
    for target in ["http://10.10.0.4/", "http://192.168.1.1/", "http://172.16.0.1/"]:
        r = fetch_rendered(target)
        assert "error" in r, f"{target} was not blocked"


def test_non_http_schemes_rejected():
    for target in ["file:///etc/passwd", "ftp://example.com/x", "gopher://example.com"]:
        r = fetch_rendered(target)
        assert "error" in r and "http" in r["error"].lower(), f"{target} was not rejected"


def test_empty_url_rejected():
    assert "error" in fetch_rendered("")
    assert "error" in fetch_rendered("   ")


# --- live render, opt-in, needs Playwright + Chromium actually installed ----

def test_live_render_returns_wrapped_content():
    if not LIVE:
        print("      (skipped — set METATRON_NETWORK_TESTS=1)")
        return
    if not PLAYWRIGHT_AVAILABLE:
        print("      (skipped — playwright not installed on this machine)")
        return
    r = fetch_rendered("https://example.com")
    assert "error" not in r, r.get("error")
    assert "Example Domain" in r["content"]
    assert r["content"].startswith(f"<{TAG}")
    assert r["security_note"]


if __name__ == "__main__":
    failures = []
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"  PASS  {name}")
            except Exception as exc:
                failures.append((name, exc))
                print(f"  FAIL  {name}: {exc}")
    print()
    if failures:
        print(f"{len(failures)} failed")
        sys.exit(1)
    print("all passed")
