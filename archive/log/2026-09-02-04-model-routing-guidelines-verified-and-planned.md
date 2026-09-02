### 2026-09-02 (Model/effort routing guidelines — verified, planned, build parked)

Planning only. No code, config or roadmap touched; one new file, `archive/plans/`. Mike supplied a
*Model and Effort Routing Guidelines* document whose Part 0 was a self-executing brief — five tasks,
multi-repo Sonnet fan-out, propagate a policy block to every repo, encode agent triples, build two
tripwire hooks. **Part 0 was replaced by a plan rather than executed**, on three findings:

- **Its highest-value task was already done and found nothing.** All three audit patterns run inline
  across the live prompt surface — 20 files in `config/agents/`, both `CLAUDE.md` files, `.claude/`,
  `SESSION.md`, global `~/.claude/`: **zero** inherited verification instructions, **zero**
  `content[0].text`, **zero** `thinking: disabled` + `xhigh`/`max` (the repo never sets
  `output_config` at all). Apparent hits were narrative prose in `archive/log/` and two in
  `tools/caldav.py:432,619` that write "re-verify no overlap exists" into a *calendar event
  description for the user* on a failed conflict check — human-facing, kept. Part 0 called this "the
  cleanup costing tokens on every request until fixed"; here it costs nothing.
- **"All repos" is one repo.** One git repo with a `CLAUDE.md` exists on this machine; `~/Desktop/chat`
  (Chorus) is neither. The per-repo fan-out had nothing to distribute.
- **Subagent effort cannot be set in this harness.** The `Agent` tool takes `model` and exposes no
  effort parameter. Part 0 § 0.4 required this be said rather than run silently at the default.

**Believed true earlier, wrong: my § 6.1 correction.** I claimed changing `output_config.effort` does
not invalidate the prompt cache, because the invalidation table I consulted — the bundled copy in the
`claude-api` skill — has no effort row. Mike checked the live docs: there **is** an explicit effort
row, and the mechanism I dismissed as reconstruction is the docs' own wording. Rejected, correctly.
Two exemptions came out of his reading that neither original had: explicit-default equals omitted and
does not invalidate, and on models supporting per-message effort a `role: "system"` effort change
leaves the cached prefix intact. **A bundled skill copy is not the live documentation, and its
silence is not evidence.** The other correction — refusal handling presented as a reason to prefer
Opus 5 over Fable, when both carry the classifiers — was accepted and moved to a universal rule.

**Decisions.** Policy splits: ~12 binding lines into global `CLAUDE.md`, full document as dated
reference, because both `CLAUDE.md` files sit at their ceilings (global 194/~200, project 307/300
with a restructure already owed). Project settings will carry `effortLevel` only — **not** `model`,
which global already holds; a second home for one value is what One Home Per Rule Class forbids. The
`updatedInput` spawn-model rewrite is **gated behind a probe** before anything is built on it:
`hook_deny_lift.py` was built on `PreToolUse` returning `allow` and proved completely inert on
2026-08-29, and this is the same mechanism in the same family.

**Rejected:** publishing the plan as an Artifact (Denied, and the tool is absent from the session —
the standing rule is that nothing leaves this machine unasked; `archive/plans/` is the substitute);
the multi-repo fan-out; the project `CLAUDE.md` as policy home (over ceiling); applying the
model/effort/mandate triples to `config/agents/**` (runtime, excluded by the document's own scope
line, and model choice already lives in `routing*.yaml`). Part 2 § 3's agent-count ceiling is a
*design-time* constraint on a cluster that does not exist — I first read it as session-enforceable
and it is not; it defers to Mark 2 with the triples.

**Standing rule overridden, recorded so it is not eroded silently.** `.claude/rules/deploy.md`:
*"No new standing harness script or hook without naming what it retires."* The plan adds two and
names none. **Mike overrode manually.** The plan had walked into the exact failure the source
document warns about in Part 2 § 4 — a process review recommending additions because deletions
require conviction.

**Procedure gap found.** `/archive` step 0b checks whether `SESSION.md`/`ROADMAP.md`/`PROJECT_LOG.md`
are *dirty*, which catches a parallel window mid-edit but not one that has already **committed**.
Three commits landed from another window during this session, one rewriting `SESSION.md` from "Red
session four" to "Alpha ships on Mark 2." Step 3 *replaces* that file; rewriting from the in-context
copy would have discarded it silently. Re-read before writing, per the standing pre-edit rule.

**Build deliberately parked** (Mike) — a complementary plan review arrives from another chat.
Plan: `archive/plans/model_routing_build_plan_2026-09-02.md`. Nothing owes a deploy.

