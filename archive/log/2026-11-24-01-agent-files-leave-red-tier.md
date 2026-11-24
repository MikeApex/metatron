### 2026-11-24 (agent instruction files stop prompting on edit — moved from Red to Amber; still never handed to a worker) — **committed and pushed; dev-side only, no VM deploy**

**Incoming handoff:** none. Mike's ask via `/metatron-code`: "Remove agent files from red tier for smoother editing. Leave venv and other restricted edits as they are."

**What changed for Mike:** editing `config/agents/*.md` in a Claude Code session no longer raises a permission box. Every other Red rule (`routing*.yaml`, `core/{router,persona,scheduler,spend_guard}.py`, `git push`) and the whole Denied row are unchanged. Nothing in settings named the venv, so the "leave venv" instruction had nothing to touch.

**How:** one line removed from `permissions.ask` in `.claude/settings.json`, with a dated note in `_comment_ask`. `scripts/hook_context_gate.py::_tier` reads settings.json, so the edit-time briefing reclassifies agent files without a code change. Tier tables brought into line in `CLAUDE.md` § Change tiers, `docs/WORKFLOW.md` and `.claude/commands/fix.md`.

**Decision made in-session, flagged to Mike:** "Red" carried two meanings — prompts on edit, *and* never delegated to a worker. Only the first was removed. Agent files stay main-session-only (CLAUDE.md now says so beside the Red line; `/fix` has an "Amber, not delegated" row), `build-implementer`/`build-planner` still list them as off-limits, and Build's hardcoded deny list in `core/build/gates.py` is untouched. *Rejected:* making them fully Amber (delegable) — Mike's stated reason was editing friction, not who builds, and the rule's reason ("there the judgement is the work") still holds. Reversing it is two agent files plus the `/fix` row if Mike wants it.

**Corrected in passing:** `_comment_ask` said "all nine Edit rules below" when there were seven; it now says "every Edit rule".

**Ceilings:** `CLAUDE.md` briefly hit 301/300 from the added sentence; folded back into the existing line, now 300/300. claims check 47/47.

**Owed (Mike, ~1 min):** in a new session, edit any agent file and revert — no box should appear; then try `config/modules/routing.yaml` and decline — the box should still appear.

**Pre-edit check, honestly:** `SESSION.md` and `settings.json` read in full; `ROADMAP.md` searched for agent-file/tier wording (no hits) rather than read in full.

