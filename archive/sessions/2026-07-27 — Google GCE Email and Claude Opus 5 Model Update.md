# 2026-07-27 — Google GCE Email and Claude Opus 5 Model Update

## What happened

**1. Google Compute Engine email (Guest Environment Packages regional rollout)**
- Reviewed Google's notice that GCE's default package repos move from global to regional rollout starting 2026-09-03 (up to 2-week staged delivery window).
- Assessed impact against `metatron-vm` (single instance, single region, `us-central1-a`).
- **Conclusion: no action needed.** The risk (version drift) only applies to multi-region deployments; this project has one VM in one region.

**2. Claude Opus 5 announcement — model config updates**
- User forwarded Anthropic's Opus 5 launch email (Managed Agents beta, advisor strategy, mid-conversation tool changes, fast mode, automatic fallbacks, thinking-required-at-xhigh/max).
- Investigated whether Metatron's routing actually uses Anthropic models: confirmed **no** — both `routing_cloud.yaml` (all Gemini) and `routing.yaml` (Ollama + Gemini for `research_agent`) never route to `anthropic`. The `ANTHROPIC_MODEL` constant in `core/orchestrator.py` only feeds `run_model_conference`'s `anthropic` branch, which isn't currently reachable via either routing config.
- Confirmed Opus 5's real API model ID (`claude-opus-5`) via the current model catalog rather than guessing.
- Updated two files:
  - `~/.claude/mcp_servers/ask_claude.py` — `opus` alias now points to `claude-opus-5`; added `opus-5` and `opus-4-7` explicit aliases, kept `opus-4-8` — all three older versions remain reachable for pinning/reproducibility.
  - `core/orchestrator.py:61` — `ANTHROPIC_MODEL` fallback constant bumped from `claude-sonnet-4-6` to `claude-sonnet-5`.
- No deploy needed (`./deploy.sh`) — neither change touches a live routing path on the VM.

**3. Discussion: which model for future refactor/security-audit work**
- User asked what model *I* (this Claude Code session) run on: Sonnet 5.
- Discussed whether switching Claude Code's own model would help for this project's dev work — concluded Sonnet 5 is well-suited for the Python/YAML/config work here; Opus 5 or Fable 5 flagged as worth trying for the harder, multi-file reasoning tasks still ahead (notably the deferred Phase 5 full OWASP security audit, and a "later" refactor the user named specifically).
- User's own read: Fable 5 is likely the best fit for that future refactor. Agreed as reasonable — Fable is positioned for the hardest long-horizon/multi-file reasoning — but flagged that Opus 5 now matches Fable in many domains at half the price, so worth trying Opus 5 first and reaching for Fable only if it under-delivers. No commitment made; decision deferred to when that work actually starts.

## Decisions made

- No action required on the GCE regional-rollout email.
- `ask_claude` MCP model aliases updated to include Opus 5, with older Opus versions preserved as pinned aliases.
- Orchestrator's unused Anthropic fallback model bumped to current (`claude-sonnet-5`).
- Deferred: which model (Opus 5 vs. Fable 5) to use for the future refactor / security audit — revisit when that work is scheduled.

## Deferred / carried forward

- Future refactor and the Phase 5 full OWASP security audit (already tracked in memory as deferred) — model choice (Opus 5 vs. Fable 5) to be decided when work begins.
- `ask_gpt`/`ask_gemini` MCP servers were noted as already self-updating via `refresh_models` (live API queries) — no action needed there; only `ask_claude.py`'s static `MODELS` dict needs manual upkeep on new Anthropic releases.
