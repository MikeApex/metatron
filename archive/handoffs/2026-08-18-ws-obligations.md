# Handoff — ws-obligations worker, 2026-08-18

**Shipped**

1. **`[DB-0810-01]` doubled streaming reply on reconnect — fixed, client-side only.**
   `ensureConnected()` in `static/index.html` now detaches the dying socket, awaits its real
   `close` event, and only then calls `connectWebSocket()`. Option (i) as directed; `core/server.py`
   untouched, so the deliberate multi-device broadcast set is unchanged. Two supporting changes in
   the same file: every socket handler closes over a local `sock` and no-ops unless it is still the
   active socket (a superseded socket's late frames used to render into the live conversation — the
   second half of the doubling), and a `closePending` guard so focus/online/visibilitychange/the 20s
   interval cannot stack a second attempt during the wait.
   **Timeout fallback: `CLOSE_WAIT_MS = 1500`.** Chosen to sit below the existing 3000 ms passive
   reconnect delay (a deliberate reconnect must never be the slower path) and far below the 20000 ms
   `ensureConnected` interval (waits cannot stack). A real close handshake is tens of ms, and
   `close()` on a dead socket goes to CLOSED locally, so 1500 ms only ever fires on a socket emitting
   no events at all — the frozen-Android-WebView case.

2. **`[DB-0814-04]` vague due date dropped from context first — fixed.** `tools/obligations.py`
   replaces the `str(due or "9999")` lexical key with `_due_sort_key()`: `(0, iso_date)`,
   `(1, vague)`, `(2, "")`. Any stated urgency now outranks nothing stated. Single call site
   confirmed (`context_block`); `tools/calendar_reconcile.py` is the only other consumer of `_load`
   and uses it for token matching, not ordering.

**Tests** — `tests/test_obligation_due_sort.py` (5/5) and `tests/test_ws_reconnect_race.js` (5/5).
The JS test evaluates the WebSocket section extracted verbatim from `static/index.html` in a `vm`
sandbox against a fake WebSocket with an asynchronous `close`. **Both were run against `HEAD`
first and fail there** — the JS one reports "chunk rendered 2 times, expected 1", which is the
reported symptom reproduced, plus stranding on a missing close and 3 sockets from stacked calls.

**Verified vs. not verified.** Verified by execution: the race, the fallback, the no-doubling
property, no socket stacking, a healthy socket left alone, and the obligation ordering including
`_CONTEXT_MAX` truncation. `python3 -m py_compile tools/obligations.py` clean; `node --check` on the
extracted script block clean. **Not verified: a live reconnect from Mike's actual client** (browser
and Android WebView). The backlog entry warns a restart previously looked like a fix, so
`[DB-0810-01]` should close on a live device reconnect, not on this. `[DB-0814-04]` is closeable on
the test evidence.

**For `SESSION.md`** — nothing structural. Deploy: `static/index.html` and `tools/obligations.py`
both ship to the VM, so this needs `./deploy.sh` (not run — worker protocol).

**Commit:** see `git log` on `wt/ws-obligations`.
