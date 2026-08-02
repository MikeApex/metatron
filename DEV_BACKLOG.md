# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

*(nothing yet)*

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. Note that `config/agents/*.md` are **frozen post-review** — each edit needs an explicit freeze lift.

- **`[CONTEXT]` block silently discarded when the model emits invalid JSON.** Observed live 2026-08-02 on `sarah_chen`: the Synthesizer wrote a literal newline inside a JSON string value, `split_context_block` (`core/orchestrator.py:678`) failed to parse it, logged a warning and returned `None` — so the context tracker was not updated *and* the `dev_request` for that exchange was lost. Silent data loss on a path with no retry. Options: repair common malformations before parsing, or have the Synthesizer re-emit. *Found while testing the self-development work.*

- **`synthesizer.md:355` promises a capability that does not exist.** It instructs the Synthesizer to use `write_config` to write `config/modules/scheduler.yaml` for recurring proactive sessions. `tools/config_writer.py:16` hard-whitelists `{prime_directive.md, mission.md}` and returns an error string for anything else. So every attempt to create a standing check-in silently fails, and the Synthesizer believes it succeeded. Either widen the whitelist (with path validation) or correct the instruction. *Found 2026-08-02 while scoping the self-development work.*

---

## Open — needs building

Capabilities that do not exist yet.

*(nothing yet)*

---

## Open — housekeeping

Stale docs, paths, and low-priority corrections.

- **`/metatron-troubleshoot` command template points at pre-persona-scoping paths.** Uses bare `data/conversations/` and hardcodes `data/personas/mike/traces/`, so it has to be corrected inline every time it runs, and it fails outright for any other persona. Also missing `--tunnel-through-iap` on its SSH command, which is now required since the VM moved to `metatron-net`. *Recorded in SESSION.md 2026-08-02.*
- **Spend guard pricing rates are unverified estimates.** `config/modules/spend_guard.yaml` is marked VERIFY — fine for order-of-magnitude runaway detection, not for cost accounting. Check against current Vertex AI pricing before trusting any dollar figure derived from it.
- **VM has an unused ephemeral external IP** (`136.112.188.80`). All access is over Tailscale. An in-use external IPv4 is ~$2.90/mo. *Recorded in SESSION.md 2026-07-31.*

---

## Done

- **Synthesizer opened responses by recapping facts the user had just given.** Fixed in `synthesizer.md` under "Direction and prioritization"; deployed 2026-08-02 (`799aa3f`). *SEQ 002.*
- **Synthesizer echoed a user-claimed timestamp instead of checking the clock.** Fixed across `tools/ambient.py`, both head-layer agent files, and the message-receipt stamping in `core/server.py` / `core/orchestrator.py`; deployed 2026-08-02 (`b184d92`). *SEQ 008.*
