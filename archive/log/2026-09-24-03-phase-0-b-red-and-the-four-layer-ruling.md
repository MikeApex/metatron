### 2026-09-24, third (the coordinating window — phases 0 and B-Red land, and the graph gains two layers) — `505b254`, `760c260`, `224e5d4` + this close-out — **nothing deployed; the VM is still at `b2b1dc7`**

The Build v4.11 coordinating window: wrote the per-phase prompts
(`archive/plans/build_v4_phase_prompts_2026-09-24.md`), made every Red edit by hand with Mike
approving each, and verified each phase window's output by running it rather than reading its
handoff. Phase A itself is `2026-09-24-02`; this covers what the coordinating window decided.

**Phase 0's record commit had to split a file, and the split was not cosmetic.** Of
`core/orchestrator.py`'s twelve uncommitted hunks, ten were phase 4 and two were the headset
chat's `source` plumbing. Committing whole would have produced a commit that **raised `TypeError`
on every streamed turn**, because the committed `core/trace.py:188` took no `source` argument. The
phase-4 half was staged through `git apply --cached` of a generated patch. *Rejected:* committing
whole plus `core/trace.py`, which would have run but takes another chat's work into Build's commit
— the 2026-08-09 shape the whole plan is built to avoid.

**Mike's ruling, the substantial one: the graph is four layers, and leaf-first is reversed for the
trigger only.** User → Coordinator → ~12 category agents (routing, not doing) → tier-3 agent →
Synthesizer. The category agents lose their doing role and Build's purpose is to construct the
tier-3 agents beneath them; their instruction files are emptied manually at rollout. v3.7 § 2
already specified this as "the tier", deferred until four leaf capabilities — Mike brought the
trigger and the guard forward. Consequences taken now: `request_build` granted to the eight
personal specialists in both routing files at strict parity, and `tools/subagent.py`'s recursion
guard made depth-aware (`MAX_SUBAGENT_DEPTH = 2`) instead of binary.

*Rejected, with reasons.* **Granting `run_subagent` alongside it** — there are no tier-3 agents to
dispatch, and with depth 1 now admitted a category agent holding it could only call sideways into
another category agent, which is a loop forming rather than a design; it arrives with the first
landed capability. **Granting to `research_agent`** — it is the decontextualised cloud path; it
also already holds every registered tool because it omits `allowed_tools` entirely, a pre-existing
gap `ROADMAP.md` names and this session did not widen. **Writing instruction lines for the eight
now** — Mike writes them at rollout; the 16 class-2 advisories in `check_agent_tools.py` are the
marker. Live state to carry: the eight hold the tool with no filing condition, over-filing is
capped at `max_proposed: 12`, and nothing deploys until phase E.

**The sixth content gate (the tier gate), approved mid-phase.** v3's constitution check — that an
overlay record's `model_ref` named a *sensitive* tracked agent — died with `model_ref` at § 8 and
nothing replaced it. Replacement: a capability whose plan carries a `kind: history` source or a
`judgment` row fails if its routing entry names the bulk tier, with the tier resolved from
`quick_override` rather than a literal model id, run at N13 where the entry exists. **I first
argued this on privacy and that was wrong for this deployment** — everything routes to Vertex by
the 2026-08-26 ruling. It stands on *tier adequacy*, with ROADMAP § D2's measured precedent: the
`relationships` Steven/Stephen pair, opposite answers to the same evidence four minutes apart. The
local-mode half (`local: true` on the generated `routing.yaml` entry) is **deliberately unbuilt**,
recorded with its revival trigger in `gates.py` — Ollama is unused, so it would be a control for a
path nobody runs.

**Believed true earlier, wrong — four, and the first two were also wrong in phase A's handoff.**
(1) **`config/personas/mike*` does not exist on the Mac.** Only `data/personas/mike/` does; the
config is VM-only by `.claude/rules/personas.md`. The `--persona mike` pipeline turn was recorded
as an (M) blocked by being *in a worktree* and runnable in the main tree — it **cannot run on the
Mac at all**, and has moved to phase E where § 12's End-to-end row and ruling 12 already put
acceptance. The substitute run — `danny_park` against the landed main tree, carrying both Build's
and the headset chat's commits — passed. (2) **`SESSION.md` listed `core/trace.py` among phase 4's
files;** its uncommitted diff was entirely headset work, and phase 4's cost seam there was already
committed. Three more headset-dirty files were unnamed: `core/server.py`, `docs/INFRASTRUCTURE.md`,
`static/index.html`. (3) **The `(M)` to delete `data/personas/mike/traces/2026-09-19.jsonl` was
already done.** (4) **This window twice acted on stale state** — telling Mike to land a headset
commit already landed, and re-issuing the phase A prompt while phase A was running, with the signal
("any *other* phases") in front of it. Phase-state tracking is the coordinating window's job and
was not being done; it is now explicit.

**Four findings worth more than the work that produced them.** **Phase E's deploy is 18 commits
deep, not Build's** — `b2b1dc7..HEAD` — so it is a catch-up deploy with Build inside it and its
checklist must separate the two before blaming Build for anything the VM does afterwards.
**`static/index.html:783`** resolves `SERVER` to the VM whenever the page is opened on `localhost`,
so a local gate silently tests the VM; it surfaces as "the login button is broken". Use the
Tailscale hostname. **The confused-deputy control is architectural, not the depth guard** —
`_dispatch_from_coordinator` is fed only `coord_output` — which is exactly why a category router
must fan out by *calling* `run_subagent`: a second dispatch parser reading agent output would break
security check 6 directly. And **a live gate run dirties tracked fixture-persona files**, which
fired twice today (phase A's worktree, then the deputy suite in the main tree); `.gitignore` does
not untrack what was committed before the rule.

