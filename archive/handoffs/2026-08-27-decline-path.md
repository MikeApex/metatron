# 2026-08-27 — the decline path (worker handoff, branch `wt/decline-path`)

**Shipped.** Tapping "No" on a confirmation card now ends it. `POST /decline` removes the pending
record so the five-second poll stops re-offering it, writes the refusal to the conversation and
broadcasts it, and appends the entry to a declined ledger beside `pending_confirmations.json`
(action, args, fingerprint, timestamp, `status: "declined"`) — so "the user said no to X" is a
fact the system keeps. Same auth, same out-of-band principle and the same fingerprint check
`consume()` uses; a record whose args no longer match its fingerprint is still removed but is not
filed as a clean refusal. Client-side, a failed call leaves the card up rather than pretending.

**Commit.** `0f8f528` — `core/server.py` (`/decline`, `_decline`), `tools/confirm.py`
(`decline`, `declined`, `_append_declined`, `_declined_path`), `static/index.html` (`confirm-no`
handler), `tests/test_decline_path.py` (14 tests, all pass; all fail on `ce94dd1` — `decline` did
not exist). `tests/test_confirmation_gate.py` and `tests/test_server_auth.py` still pass.

**Close `[DB-0827-01]`** on that commit plus the tests, in particular
`test_decline_endpoint_stops_the_poll_returning_it` (end-to-end: request → poll shows it →
`/decline` → poll empty → second tap 404s) and
`test_declined_entry_is_retained_with_status_and_fingerprint`. Mike's own check: propose a gated
action, tap No, and confirm the card does not return on the next poll.

**The open half.** A decline does not yet stop the model re-proposing the same action. The ledger
is readable via `confirm.declined(within_seconds=...)` with the fingerprint intact; the plug-in
point is the orchestrator's context assembly (owned by another worker this session, so untouched
here) — inject recent declines the way pending confirmations are surfaced, and match a proposed
action's `_fingerprint(action, args)` against them. The conversation row written by `/decline`
("🚫 Declined — …") is a partial stand-in until then, since it is in the model's context next turn.

**For `SESSION.md`.** `/decline` exists and is unshipped — this needs `./deploy.sh` (both
`core/` and `static/`), which a worker may not run. `data/personas/<p>/declined_confirmations.json`
is a new on-disk artefact, `600`, capped at 200 entries; no meter reports it and it is a few KB.
Pre-existing and not fixed here: `/confirm` and `/decline` both raise on `persona_scope(None)` if
`SERVER_PERSONA` is unset and the client omits `persona` — production sets it.

**Transcript.** `archive_chats.py` finds no JSONL for the worktree path (sessions log under
`-Users-md-homefolder-Desktop-multi-model-mcp`); the parent session's run covers this work.
