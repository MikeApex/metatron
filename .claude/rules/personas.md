---
paths:
  - "config/personas/**"
  - "core/persona.py"
  - "scripts/new_persona.sh"
  - "scripts/check_personas.py"
---

# Personas and identity resolution

Relocated from `CLAUDE.md` on 2026-08-14, in full.

A persona is a user. There is no test-versus-real distinction: every session belongs to exactly
one persona and is treated as real.

Each persona owns a complete universe:

```
config/personas/{name}.md              identity + interaction preferences (required)
config/personas/{name}/
    prime_directive.md  mission.md  goals.yaml     tiers 1-3
    profile.yaml  scheduler.yaml  caldav.yaml      settings (gitignored)
data/personas/{name}/                  logs, journal, memory, traces, conversations,
                                       crm, wisdom, archive, config, baselines
```

**Identity resolution is fail-closed.** `core/persona.py` is the single source of truth.
`resolve_persona()` checks, in order: an explicit argument, thread-local state (set by
`persona_scope()`), then `METATRON_PERSONA`. If none resolves it **raises** — it never falls back
to a shared path. Every entry point must name a persona: `--persona` is required on both
`core/server.py` and `core/scheduler.py`.

Never read the environment variable directly. Call `resolve_persona()`, `persona_data_dir()`,
`persona_config_dir()` or `persona_md()`.

Identity is thread-local, not process-global, because sessions run on a pooled executor thread
and specialists fan out across further threads. Anything that spawns a thread must bind the
persona inside it — see the four boundaries in `core/orchestrator.py` and `tools/subagent.py`. A
fire-and-forget subagent (the Diarist) outlives its request, so it resolves identity on the
*calling* thread before the parent scope exits.

Persona names are validated against `^[a-z0-9][a-z0-9_]{0,39}$`. They become filesystem paths and
arrive from the HTTP request body, so an invalid name is rejected rather than sanitised.

**Adding a persona:** `./scripts/new_persona.sh <name>`, then fill in `profile.yaml` and run the
Goals Interview. Settings files are gitignored, so copy them to the VM manually — `deploy.sh`
will not carry them.

---

## The VM owns live persona config — the Mac does not (established 2026-08-03)

`config/personas/{persona}.md` and `config/personas/{persona}/` are gitignored *and* deliberately
absent from the deploy. This is not a gap to be closed:

- **The running system writes to them.** `write_persona()` edits `config/personas/{persona}.md`;
  `write_config()` edits `prime_directive.md` and `mission.md`. Both happen on the VM, in response
  to what the user asks for mid-conversation. On 2026-08-03 the VM's `mike.md` held five
  interaction preferences recorded that morning which the Mac copy knew nothing about — a Mac→VM
  push would have erased all five.
- **They hold Tier 1–3 content**, which is sensitive-tier under the data-privacy table in
  `CLAUDE.md`. A private repo is not a reason to relax that; the 2026-07-29 history rewrite is the
  precedent for what it costs to get this wrong.

So the rule is directional:

| Direction | Mechanism | When |
|---|---|---|
| Mac → VM | one-off `gcloud compute scp`, deliberately | authoring a genuinely new file (e.g. `self_development.md`) |
| VM → Mac | `scripts/metatron-backup.sh` into `backups/vm/`, archived by `scripts/daily-backup.sh` | routine backup |

**Do not keep a Mac copy in `config/personas/` after scp'ing.** A stale copy is the thing that
gets pushed by mistake. Only synthetic/dev personas, which are git-tracked and not written to at
runtime, live on the Mac. `deploy.sh` carries a comment block explaining this at the point where
someone would be tempted to add the push.

**Editing live persona config:** pull it down (`scripts/metatron-backup.sh`), or edit on the VM
directly and let the next backup capture it. Never reconstruct it from memory on the Mac.

**Checking consistency:** `python scripts/check_personas.py` reports drift between identity files,
config directories and data directories. Exits non-zero on real breakage.

**Transition note:** `AI_TEST_PERSONA` is a deprecated alias for `METATRON_PERSONA`. It still
works and warns once.

---

## Which layer a persona rule belongs in

A preference stated by the user is **design by default**, not a persona deviation — and promotion
into an agent file deletes the persona copy in the same pass. That rule, its 2026-08-03 evidence
and the three checks that enforce it live in `.claude/rules/agent-files.md` § One Home Per Rule
Class. It is not repeated here, because two copies of a rule about duplicated rules is the exact
failure both files describe.
