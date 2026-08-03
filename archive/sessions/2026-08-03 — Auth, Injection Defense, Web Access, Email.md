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

*(appended as items land)*

### Item 1 — Server authentication

- Status: in progress

---

## Deferred / carried forward

*(to be filled at close — anything still actionable goes to `DEV_BACKLOG.md`, not left here)*
