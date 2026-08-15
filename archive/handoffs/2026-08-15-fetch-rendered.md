# Handoff — fetch_rendered (2026-08-15)

**Shipped:** `fetch_rendered(url)` in `tools/web.py`, the rendering half of
`[DB-0806-02]` (scope: `archive/plans/level3_web_actions_scope_2026-08-06.md`). Read-only
headless-browser fetch, reusing `fetch_url`'s exact trust boundary — same `_check_url`/
`_is_blocked_address` SSRF guards run before Playwright is ever touched, same
`wrap_untrusted`/`contains_injection_markers` handling, same return shape
(`{url, final_url, title, content, truncated, security_note}` / `{error}`).

**Symbols to register (coordinator's job, not done here):**
`from tools.web import fetch_rendered, FETCH_RENDERED_SCHEMA` — register in
`core/orchestrator.py` alongside `fetch_url`/`FETCH_URL_SCHEMA`, grant in routing config to
Logistics and Research alongside `fetch_url`, per the scope doc. Not registered or granted
by this worker (Red-tier files, out of manifest).

**Graceful degradation — the path that matters most:** Playwright is imported lazily inside
the function. Verified three ways: (1) `tools/web.py` imports cleanly via subprocess with
`playwright` import blocked at the `__import__` level — proves no import-time dependency;
(2) with Playwright's Python package installed but no browser binary, `launch()` fails and is
caught, returning `{"error": "...could not launch headless Chromium..."}`, no traceback; (3)
with Playwright + Chromium both installed, a live fetch against `https://example.com` returns
correctly wrapped content. All three are asserted in `tests/test_fetch_rendered.py`.

**Playwright footprint observed (installed locally on the Mac to test, then removed):**
Python package ≈ 134 MB (`pip install playwright`); `playwright install chromium` added
≈ 367 MB (Chromium) + ≈ 196 MB (headless-shell variant) ≈ 563 MB of browser binaries under
`~/Library/Caches/ms-playwright`. Total footprint for this one browser ≈ 700 MB. `pip
uninstall`'d the package afterward and confirmed the module still imports and degrades
cleanly with it gone. Could not remove the cached Chromium binaries themselves — `rm -rf` on
`~/Library/Caches/ms-playwright/...` was denied by this session's sandbox; they're outside the
repo and harmless to leave, but the coordinator should know ~560 MB is still cached on this
Mac if that matters. **Did not touch the VM, any deploy script, or any requirements file** —
the VM install decision is explicitly the coordinator's per the task brief, given the scope
doc's own note that Chromium's ~150–300 MB resident footprint on an already-loaded `e2-medium`
(4 GB, Whisper + Kokoro TTS + scheduler) is unmeasured.

**Bounds implemented:** `RENDER_TIMEOUT_MS = 15_000` hard page-load cap, additional
`RENDER_NETWORK_IDLE_MS = 5_000` bounded (not indefinite) wait for SPA network-idle, output
capped at `MAX_TEXT_CHARS` (shared constant with `fetch_url`). Browser instance is opened and
closed per call inside a `with sync_playwright()` block — no persistent global instance in
this pass; the scope doc's "single global instance + lock" is a further optimization the
coordinator can decide to add before granting this at scale.

**Tests:** `tests/test_fetch_rendered.py`, 9 tests, all offline except one opt-in live case
(`METATRON_NETWORK_TESTS=1`). All 9 pass locally; `tests/test_untrusted_and_fetch.py` (14
tests) re-run to confirm no regression to `fetch_url` — all pass.
`./scripts/qa_sweep.sh` — 9/9 checks pass.

**Close `[DB-0806-02]` rendering half** — evidence: this commit, the three-way degradation
verification above, and the scope doc's requirements all met (read-only, no new trust
boundary, bounded timeouts). Interactive Level 3 remains explicitly unbuilt per the scope doc.

**For `SESSION.md`:** the coordinator should register `fetch_rendered`/`FETCH_RENDERED_SCHEMA`
and grant it to Logistics/Research, then make the VM-install call on Playwright + Chromium
using the footprint numbers above (not yet installed or measured on the VM itself).
