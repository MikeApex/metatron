# 2026-08-08 — Backlog Attack Command

## What happened

Mike asked for a prompt that scores `DEV_BACKLOG.md`'s open items and turns the top ones into
three independent, single-session work prompts — plus a `/` command to wrap it.

## What was built

- **[.claude/commands/backlog-attack.md](../../.claude/commands/backlog-attack.md)** — new slash
  command. Steps: load context via `/metatron-code` → score `## Open` items (importance 1–100
  relative to the project, difficulty 1–10 inverted so higher = easier) → verify only shortlist
  candidates against current code (per the standing backlog rule) → cluster top items into 3
  groups with zero file/directory/deploy-target overlap → output a scored table + 3
  self-contained hand-off prompts. Explicitly planning-only — stops before implementing.

## Decisions made

- **Iterated on the prompt before writing it**, rather than writing directly: added a mandatory
  `/metatron-code` load step (scoring needs actual phase-gate/freeze state, not a guess), made
  "verify before scoring" and "no overlap between clusters" explicit steps rather than assumed
  behavior.
- **New command name, not an edit to `/backlog`.** Mike asked to see `backlog.md`'s current
  content first (opened it in the IDE), confirmed it's a different job — `/backlog` works the
  bin (sync/triage/verify/ID-provenance), this new command scores and clusters it into parallel
  prompts — and named the new one `/backlog-attack`.

## Deferred / not done this session

- The command was created but **not run**. No scored list or cluster prompts exist yet for the
  current 44 open / 6 untriaged backlog.
- No backlog items were fixed, triaged, or filed this session — this was tooling only.

## Deploy

None needed — `.claude/commands/*.md` is read by Claude Code directly, not deployed to the VM.
