Model: Fable 5.1. A whole-codebase review weighs findings against this project's own stated
intent across eight areas, and the project's standing rule is "review in Fable". That
judgement is the work.

# Whole-codebase review — read-only, findings with fixes

You are the lead reviewer for a whole-codebase review of this repository. Your job is to find
what is wrong, unfinished or obsolete, and say how to fix it. You fix nothing yourself.

## 1. Hard boundaries

1. **Read-only, with exactly three exceptions:**
   1. Create one pinned worktree.
   2. Write one report file.
   3. Remove the worktree at the end.

   No other edits, no commits, no pushes, no deploys.
2. **Review committed HEAD, in a pinned worktree.** Other chat windows edit the main tree, and
   it holds uncommitted work under separate review. Create the worktree with
   `./scripts/new_worktree.sh codebase-review-<YYYY-MM-DD>` (an ordinary worktree, **not**
   `--sandbox`), and read only inside it. Leave it clean: a dirty registered worktree stalls
   every subagent in every window. Remove it at the end with
   `./scripts/rm_worktree.sh codebase-review-<YYYY-MM-DD>`.
3. **Out of scope:**
   - uncommitted and untracked files, including the WhatsApp reader under
     `android/…/metatron/whatsapp/`, which awaits Mike's own review
   - `archive/` (except the specific files §2 and §4 name)
   - `data/`
   - `tests/*.md` report files (except as evidence of when something last ran)
   - build outputs, `__pycache__`, model weights
4. **Clean-room rule:** never open the 2026-10-26 transcripts in `archive/transcripts/`.
5. **Commands you may run:** read-only git (`log`, `show`, `diff`, `ls-files`, `blame`) and
   the zero-model-token static checks:
   - `./scripts/qa_sweep.sh`
   - `scripts/check_agent_tools.py`
   - `scripts/check_confirm_executors.py`
   - `scripts/check_claude_md_claims.py`
   - `scripts/check_personas.py`
   - `scripts/check_knowledge_domains.py`
   - `scripts/check_rule_overlap.py`

   **Never run:** any live test runner (`tests/run_*.py` and anything that calls a model or
   an external API: they hit live meters and dirty tracked fixture-persona files),
   `scripts/vm_read.py` or anything touching the VM, `./deploy.sh`, or anything that installs
   or migrates.
6. **Nothing leaves this machine.** No web fetches, no published pages or artifacts, no
   external services. Do not substitute `/code-review ultra`: it bundles the code to the
   cloud.
7. **Personal data:** do not read `data/` or `config/personas/mike*` beyond confirming a code
   path exists. The report quotes code, never user content.
8. **One output file:**
   `<main-tree>/archive/plans/codebase_review_<YYYY-MM-DD>_fable-5-1.md`. Write it to the
   **main tree** by absolute path, never inside the worktree.
9. **File nothing to `DEV_BACKLOG.md`.** Mike triages the report with `/backlog`.
10. If a boundary blocks something you need, record it under "Not covered". Never work
    around it.

## 2. Orient before you judge

**Lead reads, in order:**
1. `SESSION.md`
2. `ROADMAP.md`
3. `CODEBASE_INDEX.md`
4. all five `.claude/rules/*.md`
5. `.claude/settings.json`, the **authority** on change tiers; the table in `CLAUDE.md` is
   a summary
6. `DEV_BACKLOG.md`, lead only, about 58k tokens

`CLAUDE.md` is auto-loaded.

**Each area reviewer reads:** `SESSION.md`, `ROADMAP.md`, the `.claude/rules/` file for its
area, and your orientation notes. Path-scoped rules do not reliably reach subagents, so name
the rule file in each brief.

**Treat these docs as locators, not truth.** They have drifted: the index (dated 09-10) puts
`run_pipeline_session` at line 621, and ROADMAP's A8 describes a 1,870-line orchestrator that
is now 7,873 lines. Judge against what the code does. Report doc drift only where it would
send a session to the wrong file or the wrong conclusion.

**Write down from orientation:**
- what the project says it is for and how it is built
- the deployed commit, read from `SESSION.md` § Built at run time (never from this prompt)
- which commits after it await deploy
- the settled decisions
- the accepted risks
- the change tiers
- where plans for unbuilt work live

**Settled decisions** live in SESSION.md's "⛔ Do not re-open" table, CLAUDE.md's Key Design
Decisions and ROADMAP §0. Respect them by default. Challenge one only when the code shows it
causing a concrete defect, and then cite both.

**Accepted risks are never findings.** Mention one only if the code has made it worse than
the ruling assumed:
- clinical safety testing (A4) suspended until before Alpha
- no off-machine backup
- quick-tier routing able to reach the clinical agents
- Vertex running without ZDR under Mike's 08-26 ruling
- ROADMAP still reading A8 as live (Mike updates it by hand)
- A7 check 8's wording

**Before any area work, run `./scripts/qa_sweep.sh` in the worktree.** If it fails on HEAD:
- Record the failure as a finding.
- Expect the subagent-stop gate to block every reviewer from reporting until the sweep
  passes.
- If that happens, stop and tell Mike rather than working around the gate.

## 3. Execution — eight areas, then verify

1. **Area reviewers.** Spawn one per area, in parallel, using the `codebase-reviewer` agent
   (read-only: Read, Grep, Glob). If that agent does not exist, use `general-purpose` and open
   its brief with: "Read-only. Never use Edit, Write, NotebookEdit, or any state-changing
   Bash." Do not use `Explore`: it locates code and does not audit it.

   | # | Area | Rule file | Approx. tokens |
   |---|---|---|---|
   | 1 | `core/orchestrator.py` alone | `orchestrator.md` | ~100k |
   | 2 | `core/server.py`, `auth`, `persona`, `push`, `attachments`, `translate`, `remote_client`; `static/` | `orchestrator.md`, `personas.md` | ~100k |
   | 3 | `core/scheduler.py`; `tools/` day_plan, day_plan_config, day_shape, obligations, accountability, analytics, escalation, schedule, horizon | `orchestrator.md` | ~120k |
   | 4 | Integrations: `tools/` mail, caldav, calendar_*, intake*, crm, crm_sweep, contacts_import, google_contacts, web, tone, untrusted, location, travel_watch, places, routing, flights | `orchestrator.md` | ~130k |
   | 5 | Context and memory: `tools/` context_tracker, wisdom, logger, diarist, memory_tool, baselines, pattern_miner, agent_config, config_writer, confirm, subagent, profile, persona, rule_audit; `core/` memory, router, spend_guard, trace, actions, rule_classes | `orchestrator.md`, `personas.md` | ~120k |
   | 6 | `core/build/`, `.claude/agents/build-*.md`, `.claude/commands/build.md` | `orchestrator.md` | ~60k |
   | 7 | `config/agents/*.md`, `config/modules/**`, `config/templates/**` (tool-grant parity across both routing files; behaviour hardcoded where config should own it) | `agent-files.md` | ~170k |
   | 8 | `scripts/`, `.claude/settings.json`, hooks, `deploy.sh`, `android/` (committed only) | `deploy.md` | ~70k |

   Each area reviews **its own tests** in `tests/`, because test adequacy can only be judged
   beside the code. Each brief carries: the area's paths, its rule file, your orientation
   notes, the accepted-risks list, §4, §5, and "return findings only, no prose".
2. **Cross-area pass (yourself).** Look for defects that only exist between areas:
   - caller and callee that disagree
   - a config key one side writes and nothing reads
   - a feature wired in one layer and missing in the next
   - drift between the local and cloud routing files
3. **Verify adversarially: one verifier per area**, given that area's candidates. Its job is
   to *disprove* each one: re-read the code, trace the path, find the guard that makes it a
   non-issue, and check the backlog item if one overlaps.
   - Keep only what survives.
   - Label credible but untraced findings **PLAUSIBLE**.
   - Before reporting a finding on a file, consult that file's `archive/log/` history, so you
     don't report an incident already fixed or a design already argued.

Total: one lead, eight reviewers, eight verifiers. Don't add agents beyond this without
recording why.

## 4. Review dimensions

All dimensions use one severity scale. None is a footnote.

1. **Correctness.** Logic errors, unhandled states, races, wrong outputs.
2. **Architectural coherence.**
   - Modules that contradict each other or the documented design.
   - Duplicated sources of truth.
   - Behaviour hardcoded in Python where the project says config owns it.
3. **Security and privacy boundary.**
   - Sensitive data reaching a path the § 0 ruling or its amendments don't cover.
   - Fail-open where the project requires fail-closed.
   - Untrusted content (mail, calendar, attachments, web, forwarded mail) reaching a decision
     without the sanitiser.
   - **Second-user isolation — high importance, new since 2026-10-26:** every request bound to
     its user, no cross-user reads or writes through persona scoping, and processing refused
     when a `consents.json` record is missing or withdrawn. Mark each finding here **"before
     a second user goes live"** where it applies.
4. **Loose ends and dead trails — high importance.**
   - **Unwired:** code, config, tools, jobs or settings that exist but are never reached, with
     no recorded plan. Look for plans in `ROADMAP.md`, `DEV_BACKLOG.md`,
     `AGENT_ENHANCEMENTS.md`, `archive/plans/future_phases.md` and `archive/handoffs/`.
     Unwired with a plan is fine; unwired with no plan is a finding.
   - **Half-wired:** connected at one layer but not the next; flags read but never set, or set
     but never read; tools granted but never named, or named but never granted.
   - **Obsolete:** mechanisms, fallbacks, branches, keys or files left behind after a decision
     superseded them. A superseded mechanism kept "as a fallback" is a finding, not a safety
     net.
   - **Orphaned references:** pointers to things that no longer exist.
   - Already-listed dead items (`config/modules/caldav.yaml` and `email.yaml`,
     `config/agents/time_director.md`, `tools/gen_icon.py`) count only if they cause harm or
     mislead.
5. **Cost — high importance.** Four classes:
   - **Build:** waste in the development loop.
   - **Run:** what runs daily with nobody watching. Redundant model calls, oversized prompts,
     polling, and **model-calling scheduled jobs now running once per user**, since each user
     has a scheduler.
   - **Ancillary:** retries that double calls, slow paths that burn tokens, storage growth.
   - **Unseen:** anything that persists between calls with no owner, no expiry, or no meter.
     Name what `core/spend_guard.py` cannot see (cache storage time, VM hours, Cloud
     Functions, FCM). Check that the Coordinator and Synthesizer prompts stay above Vertex's
     4,096-token cache floor.

   Never quote a billing threshold or price from memory; read it from
   `docs/INFRASTRUCTURE.md` or `config/modules/spend_guard.yaml`.
6. **Test adequacy — high importance.** Would the tests catch the failures that matter?
   - Separate the three kinds of file in `tests/`: unit tests, live runners, dated reports.
   - Flag mock-only assertions, critical paths with no test, tests that pass whether or not
     the code works, and live seams with an unstubbed meter.
   - A green `qa_sweep` means "nothing statically broken", never "works".
7. **Operational and deploy risk — high importance.**
   - Silent-failure modes, restart/crash/redeploy behaviour, duplicate processes, env-var
     overrides.
   - Use CLAUDE.md's seven *Infrastructure traps* as a checklist.
   - Weight silent failures above loud ones.
   - For every finding, state **live on the VM** (present at the deployed commit) or **HEAD
     only** (awaiting deploy).

## 5. Evidence standard

Every finding has all four:

1. **Location:** `file:line` as a markdown link.
2. **What a user would see:** the visible effect first ("the reminder fires twice", "Iva's
   question is answered from Mike's calendar"), and the mechanism second.
3. **Failure scenario:** the input or state that triggers it, and the wrong result.
4. **Verdict:** CONFIRMED (traced) or PLAUSIBLE.

Use project terminology: model and agent names by name, and plain language before any `DB-`
id. "Could be cleaner" is not a finding.

## 6. Out of scope

- Style, formatting, naming preferences, unrequested refactors.
- Re-arguing settled decisions or accepted risks without a concrete new defect (§2).
- Items already filed in the backlog. Confirm the overlap against the code (a third of
  checked items were once found stale), give it one line, and report it in full only if the
  item is wrong or understated.

## 7. Report format

`<main-tree>/archive/plans/codebase_review_<YYYY-MM-DD>_fable-5-1.md`:

1. **Summary**, five lines at most:
   - overall health
   - the three most serious findings in plain language
   - confirmed versus plausible counts
   - how many findings are marked "before a second user goes live"
2. **Findings**, numbered and ranked most severe first across all dimensions. Each one has:
   - **Title:** what a user would see.
   - Dimension · severity (Critical / High / Medium / Low) · CONFIRMED or PLAUSIBLE · tier
     of the file(s) touched, from `.claude/settings.json` · live on the VM or HEAD only.
   - Location, failure scenario, mechanism (§5).
   - **Fix:** the concrete change, with the files and what changes in each. No code.
   - **Deploy:** whether the fix needs a VM deploy (`core/`, `config/`, `tools/` do;
     `tools/metatron_monitor.py` and `scripts/` hooks don't). Mike runs `./deploy.sh`; it is
     Denied tier.
   - **For any finding touching a Red-tier file:**
     - **Token budget:** a main-session build, never delegated (Red tier is not handed to a
       worker), planned and built in Opus with review in Fable. Give estimated tokens per
       step.
     - **Programmer time:** hours of Mike's attention, covering:
       - approving each Edit prompt
       - review
       - the deploy
       - the live check that confirms the fix
       - any step only he can do
   - **For any finding touching a Denied-tier file:** say so separately. It needs Mike's
     explicit, plan-scoped lift.
   - **Every step only Mike can do** (an "(M)" item): name it, and propose a guided
     walkthrough session to close it.
3. **Cross-area findings:** if not already ranked above.
4. **Not covered:** areas skimmed, skipped or blocked, and why. A silent gap would be read as
   a clean bill of health.
5. **Review cost:** the actual figure reported by `scripts/hook_session_tokens.py` for this
   session, broken down by phase where the subagent results report it.
6. **Cleanup:** confirm the worktree was removed.

## 8. Budget and stopping rule

**Expected spend:** about $180 at Fable 5.1 API rates (range $120–300). That is roughly 3.4M
fresh input, 2M output including thinking, and 145M cache reads.

| Phase | Share |
|---|---|
| Lead (orientation, backlog, cross-area pass) | ~$30 |
| Area review | ~$110 |
| Verification | ~$40 |

The committed surface alone is about 1.7M tokens to read once.

**Cap: $250, or about 4M fresh input plus 2.5M output**, whichever comes first.
- At 80% of the cap, stop starting new areas, finish verifying what is in hand, and list the
  rest under "Not covered".
- Stop an area once a further pass turns up only Low findings.
- Breadth beats exhaustiveness: all eight areas at moderate depth are worth more than four
  done perfectly.

**Wall-clock:** about 1–2 hours unattended. Mike's reading and triage time afterwards is
about an hour.

**Persisting state:** the worktree is the only thing this review leaves behind, and §1 owns
its removal.
