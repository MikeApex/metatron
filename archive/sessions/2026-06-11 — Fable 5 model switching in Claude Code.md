# 2026-06-11 — Fable 5 model switching in Claude Code

## What happened

Short session focused on how to switch to `claude-fable-5` in Claude Code, specifically in the VS Code extension environment.

## Key findings

- `/model claude-fable-5` is not available in the VS Code extension environment — returns "not available in this environment"
- The General Config panel (reached via `/config`) does not expose a model field
- `~/.claude/settings.json` `"model"` field sets the model globally across all projects/chats — not suitable for a one-off session
- **The only session-scoped option** is the CLI flag: `claude --model claude-fable-5` in a terminal

## Fable 5 API notes (from claude-api skill)

- Model ID: `claude-fable-5`
- Do NOT send `thinking: {type: "disabled"}` — returns 400; omit the param entirely instead
- `budget_tokens` fully removed
- `temperature`, `top_p`, `top_k` not accepted
- Adaptive thinking only: `thinking: {type: "adaptive"}`

## Deferred / unresolved

- User launched `claude --model claude-fable-5` in the VS Code terminal but was unsure if it connected. Left unclear — user may need to revisit.
- User opened `config/agents/work_vocation.md` during the session — possibly unrelated, or a next task.

## Files

- Verbatim transcript: `archive/sessions/2026-06-11 — Fable 5 model switching in Claude Code.txt`
