### 2026-11-18 (prompt audit of the Claude Code configuration; the instruction files stop describing gaps that were already closed, and the deny-lift hook is retired) — `84630b7` + this close-out — **dev-side only; no deploy needed**

**Outgoing handoff carried:** unchanged from § 2026-11-16; this session did no product work.

**What ran.** `/claude-api prompt-audit` over everything that loads into a Claude Code session here:
root `CLAUDE.md`, the five rule files, seven commands, seven subagents, the global
`~/.claude/CLAUDE.md`, and a report-only pass over the synced Anthropic skills. Target model: Opus 5.5
(Fable for the subagents that pin it). **The prompting itself was clean**: no CRITICAL/MUST stacks,
no step-by-step scaffolds, and rules carry their reasons. Every real finding was a stale fact.

**Believed true, and wrong — the three that mattered:**
- *"`dispatch_tool()` does no whitelist check"* (`orchestrator.md`, `agent-files.md`). It does
  (`core/orchestrator.py:2818`), but blocks only under `METATRON_TOOL_PERMISSIONS=enforce`; the
  default is `warn`, so the call still runs. The trap is real; the stated cause was not.
- *Injection wrapping is "Deferred — build at Deliverable 6".* `tools/untrusted.py` already wraps
  email, web, calendar, intake and attachments.
- *CLAUDE.md listed the plan-scoped deny lift as a mechanism.* `deploy.md` recorded the same day
  that it does not work. After `/compact` only CLAUDE.md survives, so a session would have trusted it.

Also corrected: a CLAUDE.md ceiling given as 200 (it is 300); `/backlog deep` pointing at a CLAUDE.md
section that does not exist (the bound is `ITEM_CEILINGS`); closed items routed to the August file;
`qa_sweep` check counts (said 7 and 9; it runs 12); the Synthesizer named as "Pro" (it is
`gemini-3.8-flash`); "nine personas"; a ban on the removed `answer_interview_item`; two dated
asides; `./deploy.sh` moved from Red to Denied in `/fix` to match settings.json; terminology-table
model names now point at the routing files (Mike: option a).

**Decisions (Mike):**
- **Deny-lift hook retired.** It could only ever emit "allow", so it guarded nothing; the probe
  finding stays in `deploy.md`. The `.gitignore` entry for `.claude/deny_lift.json` stays for now,
  because that file carries another session's uncommitted lines.
- **`deploy.md` ceiling 100 → 140.** It was 131; it is 110 after the removal.
- **Session writeups: leave as is.** The global rule still asks for `archive/sessions/` files and the
  project rule says they stopped on 08-09. Two were written on 09-03, none since.
  *Rejected:* a project-side override line (CLAUDE.md is at 300/300); reinstating writeups.
- **Tool-permission enforcement is its own session**, filed to the Inbox with a testing phase before
  the flip. Mike's note in the item: warn mode was left on deliberately, so it would not hold up
  development and so the denials would show which ungranted tools agents need.
- **No second-agent review.** The findings were fact checks against the repo, re-verified in-session.

**Left alone:** the "ruling 7" references and the comment in `build-inquiry.md` (that file is dirty
from another session; Build is not active).

