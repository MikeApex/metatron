Model: Opus 5.5, high effort — head-layer prompt assembly, a new store every later phase rests on, and Red files built with Mike present; review the diff in Fable before deploy.

# User data objects — phase 1 build (paste into a fresh chat)

/metatron-code This session **builds phase 1** of
`archive/plans/custom_logs_and_places_plan_2026-11-21.md`: the registry, the general store, and
the asked-for path end to end — so that on `mike` I can say *"start a log of …"*, add entries,
read it straight back, change one, and archive it.

## Read first, in order

1. The plan, in full — especially § 2 (my rulings, R1–R34; do not re-open them), § 3.1–3.5,
   § 4, § 5 phase 1, § 6 tests 1–3 and 6.
2. `archive/plans/adversarial_review_custom_logs_and_places_plan_2026-11-21.md` — the review,
   its verify round, and the note that four items were revised **without** a third
   verification. Phase 1 owns three of them: the write verification and retry (§ 3.4), the read
   rule for stores with no read tool (§ 3.3), and the confirmation card (§ 3.4 — phase 2 builds
   the card itself, but phase 1's tool shapes must not preclude it).
3. The current state of every file in § 4 you are about to touch — not the plan's description
   of it.

## Before writing any code

- **Collision check.** On 2026-11-21, 22 files were uncommitted from the goal–task network
  phase 2 chat (`core/orchestrator.py`, `tools/subagent.py`, `tools/obligations.py`,
  `config/agents/coordinator.md`, `synthesizer.md`, both routing files, others). Run
  `git status` and `git log --oneline -15`. If phase 2's work is still uncommitted in those
  files, **stop and tell me** — do not build on top of another chat's uncommitted lines. Check
  `archive/plans/parallel_chats_index_*.md` for current ownership.
- **Diff the plan against recent work.** For each file in § 4, read the commits since
  2026-11-21 and say in your plan what that check confirmed and what it killed.
- **A8 claim:** `core/orchestrator.py` carries the A8 module-split plan (`ROADMAP.md` § A8). The
  two new helpers go beside `_knowledge_manifest()` / `_resolve_knowledge()`, and their A8
  destination is named in the commit.
- Show me the todo list and wait for my go-ahead before executing it.

## Phase 1 scope (plan § 5, item 1)

1. `tools/data_objects.py` — the registry at `data/personas/{p}/data_objects.json` (**outside**
   `archive/`); identity rules (`thing` / `occurrence` / `thing+occurrences`); edit history
   (`previous`); `active` / `archived` / `private`; `merged_into`; aliases and close-match
   refusal.
2. `tools/diarist.py` — a repeat `write_archive` **keeps today's merge for every category**;
   occurrences only from an explicit occurrence write; `occurrence`-identity objects always
   append; `_`-prefixed category names refused by both tools; unregistered categories
   byte-identical to HEAD.
3. The four tools (`list_data_objects`, `read_data_object`, `write_data_object`,
   `amend_data_object`) with schemas, and **the read rule**: a registered store is served only
   to an agent holding that store's own read tool, through the same `tools/untrusted.py`
   wrapping; stores with no read tool go only to the object's `relevant_agents`; location-tier
   stores never return a coordinate. Writes to a non-archive store are handed to that store's
   own tool.
4. Templates in `config/data_objects/*.yaml`, limits in `config/modules/data_objects.yaml`
   (start high — R29).
5. Relevance tagging at creation (one bulk-tier call; `class: health` always adds both health
   agents).
6. The per-agent manifest (`_data_object_manifest(agent)`) **in the per-turn user message,
   never the cached system prompt** — assert the cached prefix is unchanged by creating an object.
7. The Coordinator's resolution and pre-fetch, riding the `KNOWLEDGE_TO_LOAD` path.
8. The Diarist write after the reply, with the pending marker, **verification, one retry on
   the reasoning tier, and the push + next-reply "didn't save" note**; the reply says "adding",
   not "added".
9. Grants — made once, for this path only (Red; with me, in the session). Pattern Miner's
   grants are **phase 5**, not now.
10. A seed script for the VM (registry seed with existing stores registered; the cardiac log
    registered as `identity: occurrence`, `class: health`). `data/personas/**` is Denied — **I
    run it on the VM**; prepare the exact command and a dry-run mode.

**Red files in this phase** — `config/modules/routing.yaml`, `routing_cloud.yaml`,
`config/agents/coordinator.md`, `synthesizer.md`, `diarist.md`. **Not delegated.** Each edit is
shown to me line by line before it is made.

## Tests (plan § 6) — every live meter stubbed

Tests 1, 2, 3 (the phase 1 parts) and 6, written and **confirmed failing on HEAD first** where
they pin a fix. Model calls, CalDAV, FCM and the Places API stubbed in every suite. Run the
regression set: `tests/run_knowledge_routing.py --persona danny_park`, the capture suite,
`tests/test_health_notes_feed.py`, `scripts/check_agent_tools.py`. Before generating any patch,
`git checkout HEAD --` any tracked fixture-persona files a live run dirtied
(`data/personas/danny_park/…`).

## Close

1. Fable review of the diff (`/code-review` or a fresh Fable read), specifically re-checking the
   three unverified revisions named above.
2. `git diff` every file before staging; commit; **push before asking me to deploy**
   (`./deploy.sh` is Denied and mine to run).
3. Hand me: the deploy line, the seed command (dry run, then real), and the live check — *"start
   a log of …"*, three entries, *"read me the … log"* immediately, change one, archive it — with
   the pass/fail signal for each step.
4. `/archive`.

## Cost budget

- **Build:** ~0.8–1.2M Opus tokens (phase 1 now carries the writer and tagging — plan § 7 said
  0.7–1.0M before the review moved them in), plus ~0.15M Fable for the diff review.
- **Run, once live:** ~$0.006–0.015/day per user for the manifest; ~$0.0005 per object created;
  under $0.001 per explicit entry; a reasoning-tier retry only on a failed write.
- **Persists:** the registry (kilobytes, never deleted by ruling, restart-safe, no meter) and
  pending markers (2-minute expiry that raises the "didn't save" note — never silent).
