# 2026-08-02 — SEQ 002 Single Exchange Troubleshoot

## Issue reported
Synthesizer response for 2026-08-02 SEQ 002 repeated back facts the user had just stated (dinosaurs, hedge maze, Sainsbury's meal deal) as a recap opener instead of adding value.

## Diagnosis
- Pulled conversation record, server logs, and pipeline trace via `/metatron-troubleshoot` against metatron-vm.
- SSH required `--tunnel-through-iap` (direct external-IP SSH timed out — VM firewall only allows the IAP range; this matches `CLAUDE.md` deployment notes).
- Conversation/trace data lives under `data/personas/mike/conversations/` and `data/personas/mike/traces/` — the top-level `data/conversations/` path referenced in the troubleshoot skill template is stale (now a `metatron.db` file there instead).
- No pipeline failure: Coordinator routed correctly to `physical_health` and `mental_wellbeing`; both specialists ran and wrote logs; no `[SECURITY]` filter hits, no `[PIPELINE] X failed`, no context/ambient load errors.
- Root cause: **content-quality gap in `config/agents/synthesizer.md`**, not a pipeline bug. The file's "acknowledge first" pattern (originally meant for opening a follow-up-question thread) had no guardrail against literally restating the user's own just-given details as a summary opener.
- Minor unrelated finding: `[background] index log 2026-08-02 failed: Extra data: line 557 column 2` warnings in server logs — cosmetic JSON parse issue on the day's log file, not connected to this response.

## Change made
User explicitly lifted the specialist-agent-file freeze for this fix (per `CLAUDE.md` mandatory pre-edit rule, specialist files are otherwise frozen post-review).

Added one sentence to `config/agents/synthesizer.md`, in the "Direction and prioritization" section:

> **Acknowledge, don't recap.** Do not restate specific facts the user just gave you — activities, foods, times, names of places — back to them as a summary opener ("You went to X, saw Y, and had Z"). They already know what they told you; repeating it adds no value and reads as filler.

A longer first draft (explaining what acknowledgment *should* do instead) was cut at the user's direction — too much instruction, and the project is deliberately keeping agent instruction files token-light.

## Validation
Ran 3 local test iterations against the `sarah_chen` dev persona (`python3 core/orchestrator.py --persona sarah_chen --input "..."`, local Mac, `DEPLOYMENT_MODE=cloud` in `.env` so it hits the real Vertex/Gemini pipeline, not Ollama), each with a message carrying specific factual details (activities, foods, times) similar in shape to the SEQ 002 trigger:
1. Science museum / planetarium / dinosaur exhibit / pizza from Marion's — no readback.
2. Skipped breakfast / 6am coffee / turkey sandwich / Tom + dentist run — no readback.
3. 4-mile river trail run / chicken-broccoli stir fry / kids in bed by 8 — no readback.

All 3 passed: each response acknowledged the meaning of what was shared (energy, stress, relief) and moved to direction or a follow-up question, without restating the specific facts back. User asked for 3 iterations (scaled down from an initial 5-10 request) as sufficient confirmation.

## Deferred
- Change is not yet deployed to the live pipeline. `./deploy.sh` needed to push `config/agents/synthesizer.md` to metatron-vm before it takes effect for the actual Mike persona in production.
- The stale `data/conversations/` path reference in the troubleshoot skill template could be updated to point at the persona-scoped path directly (avoids the timeout/retry churn seen this session) — not done, flagging for later.
