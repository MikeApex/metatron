# 2026-08-03 — Authentication, Injection Defense, Direct Web Access, Email

Working the plan at
[archive/plans/phase5_prompt_2026-08-03_security_web_email.md](../plans/phase5_prompt_2026-08-03_security_web_email.md).
Five items in dependency order; user scoped the session to **all five**, across multiple
sessions if needed, with item 5 held to a written scope decision plus at most one narrow
confirmed action.

*This file is written early and updated as work lands — VS Code can crash mid-session.*

---

## State found at session start (verified, not remembered)

- **Auth genuinely absent.** `core/server.py:56-61` — `allow_origins=["*"]`, comment reads
  *"local network only — no auth needed at this stage."* No auth on any of 17 endpoints.
  `/monitor/file` (`core/server.py:1070`) validates against path traversal but is otherwise
  open: any tailnet host reads the whole `data/` tree.
- **A login screen already exists** at `static/index.html:283-310`, with a password field whose
  placeholder reads `"not required"`. The client-side home for a token was already built.
- **Permissions ready to flip.** `TOOL_PERMISSION_MODE` at `core/orchestrator.py:847`,
  enforcement branch at `:902`. Denial log is small — two entries, both `physical_health`
  reaching for `read_agent_config` / `write_agent_config`.
- **`<untrusted_content>` documented in two files, implemented in none** — `tools/caldav.py`
  and `config/agents/logistics.md` both describe it; no code emits it.

---

## Decisions made this session

1. **Auth shape: password → cookie + bearer.** Shared password in `.env` on the VM. The
   existing login field posts to a new `/auth/login`, which sets an HttpOnly Secure cookie
   *and* returns a bearer token. Middleware accepts either.
   **Why both:** `EventSource` (`/session/stream`) and `WebSocket` (`/ws`) cannot set request
   headers — that is the real constraint. The cookie covers them automatically; the bearer
   covers the CLI, scripts and the Android app.
   **Rejected:** bearer-only with `?token=` on the SSE/WS URLs — simpler, but puts the secret
   in URLs and therefore in access logs and browser history.
   **Rejected:** gating normal endpoints only and leaving streaming open — that leaves the main
   conversational endpoint unauthenticated, which is most of the exposure.

2. **Missing auth password is fail-closed at startup**, not a warning. A server that silently
   runs unauthenticated because a variable failed to copy is exactly the failure item 1 exists
   to close.

---

## Sequencing traps flagged before starting

- **APK rebuild required.** `CLAUDE.md` mandates a rebuild whenever `static/index.html` changes
  the login flow. Item 1b does. The phone is down between deploy and sideload.
- **`.env` must reach the VM before the code that reads it.** `deploy.sh` cannot carry `.env`.
  Order: copy `.env` → `daemon-reload` if a unit changed → `./deploy.sh`.
- **A known adjacent bug will surface at the enforce flip and must not be blamed on it.**
  `synthesizer.md:355` instructs the Synthesizer to write `scheduler.yaml` via `write_config`,
  but `tools/config_writer.py:16` hard-whitelists two markdown files. This already fails
  silently today; it is not enforcement breakage.

---

## Work log

### Item 1 — Server authentication — **BUILT, COMMITTED, NOT DEPLOYED** (`11a166d`)

- **`core/auth.py`** (new) — password check, signed tokens, open-path list. Tokens are
  signed rather than stored: they survive a restart (the phone is not logged out by every
  deploy) and a password change revokes all of them at once.
- **`core/server.py`** — `@app.middleware("http")` gates everything except `/`, `/sw.js`,
  `/static/*`, `/auth/login`, `/favicon.ico`. New `POST /auth/login`. CORS moved off
  `allow_origins=["*"]` to an allowlist with `allow_credentials=True` (a wildcard is
  incompatible with credentialed requests anyway).
- **WebSocket gated separately, and it had to be.** Starlette runs no HTTP middleware for a
  WS handshake, so `/ws` requires `{"type":"auth","token":…}` as its first frame.
  `ConnectionManager.connect()` no longer calls `accept()` — the endpoint does, before the
  check — so an unauthenticated socket never joins a broadcast group.
- **`static/index.html`** — login field wired up, `authFetch()` wrapper on all six call
  sites, auth frame on WS connect, no auto-enter without a token, no reconnect loop after
  an auth failure.
- **Four internal clients would have broken.** They hold the password already and the
  signing key derives from it, so they mint tokens locally instead of calling `/auth/login`:
  `sync_dev_backlog.py`, `metatron_monitor.py`, `remote_client.py`, and the health checks in
  `deploy.sh` / `metatron-resume.sh` via new **`scripts/mint_token.py`**.
- **`core/auth.py` is stdlib-only with lazy annotations** — deliberately. The SessionStart
  hook runs `sync_dev_backlog.py` under the macOS system Python **3.9**, where a
  `str | None` annotation evaluated at import time is a `TypeError`. Caught by running it,
  not by reading it.
- **`tests/test_server_auth.py`** — 16 cases, all pass. Also verified against a live server
  on :8099: every gated endpoint 401s unauthenticated, both credential forms work, and all
  four WebSocket paths behave (non-auth frame → `auth_failed`, bad token → `auth_failed`,
  valid → `auth_ok` then history, silence → closed 1008 after 10s).
- **Password generated into the Mac `.env`.** Must be hand-copied to the VM *before*
  deploying, or the server refuses to start — by design.

### Item 2 — Tool permissions — **BLOCKED ON A DECISION, and bigger than the log showed**

The backlog inbox listed **2** `TOOL_DENIED` entries (`physical_health` → `read_agent_config`,
`write_agent_config`). Auditing every agent instruction file against its `allowed_tools` in
`routing_cloud.yaml` found **43 gaps across 11 agents**.

The denial log only records what actually *fired* in production. The audit records what the
instruction files *ask for*. Flipping `METATRON_TOOL_PERMISSIONS=enforce` against the log
alone would have broken the other 41 silently — which is exactly the failure `CLAUDE.md`
§ Security Architecture warns about: *"Every told-but-not-offered capability therefore works
by accident."*

`coordinator` → `write_quality_event` is **not** a live break: `allowed_tools: []` is
deliberate there (*"single-pass routing directive, no tools"*), so that one is a stale
instruction rather than a missing grant.

Full audit output is in the session transcript. Decision needed before the flip.

---

## ⚠ Live incident found mid-session — VM unreachable

Not caused by this session's work; found because `sync_dev_backlog.py` was quietly
returning nothing.

- **GCE reports `RUNNING`** (started 2026-08-01T09:23), **but the guest has no network at
  all**: the serial console shows continuous
  `dial tcp 169.254.169.254:80: connect: network is unreachable` — it cannot reach even the
  link-local metadata server.
- **Tailscale: offline, last seen ~4h** before 2026-08-04 00:30. Phone `jelly-star` also
  offline 2h.
- **SSH over IAP fails** — `4003: failed to connect to backend (port 22)`.
- **Not the 2026-07-31 billing freeze.** `billingEnabled: true`, account
  `013F3D-66B5CD-955A3A` linked.
- **Onset is not in the serial buffer** — retained output begins 2026-08-03T23:21 already in
  the failure state. No OOM, kernel panic, or NIC link event in what is retained.
- Serial log captured to the session scratchpad before any reboot destroys it.

**Consequence for this session:** deployment is blocked, so item 1 cannot be verified in
production, and `sync_dev_backlog.py` has been silently returning nothing — **the backlog
inbox read at session start is stale.**

---

## Deferred / carried forward

*(to be filled at close — anything still actionable goes to `DEV_BACKLOG.md`, not left here)*
