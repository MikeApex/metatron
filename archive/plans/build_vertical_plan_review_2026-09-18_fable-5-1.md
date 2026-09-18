# Adversarial review of the Build vertical plan (v2, 2026-09-17)

*Reviewer: Fable 5.1, 2026-09-18. Plan reviewed: `~/.claude/plans/mossy-noodling-valiant.md`
(to be saved as `archive/plans/build_vertical_plan_2026-09-17.md`). Read-only review; no code
or plan text was changed. Mike reviewed these findings on 2026-09-18 and ruled as recorded in
§ 0. Every code claim below was checked against the working tree at commit `7bca654`.*

---

## 0. Rulings (Mike, 2026-09-18)

1. **All of Build runs on the VM.** Decided in the planning chat; the plan did not state it.
2. **Landing shape: option 1, overlay.** Generated capabilities live in a VM-owned, gitignored,
   backed-up directory and the runtime loads them. Build never writes a tracked file.
3. **Consequences accepted with option 1:** `split` and `extend` are deferred until a promotion
   path exists (copy an overlay capability into the repo for Mike to commit). `kind: tool`,
   `function_job` and `check` leave v1 — they need code, and nothing on the VM writes code;
   they go out as `needs_tool` briefs Mike implements on the Mac. The § 11 bootstrap is
   re-chosen around a config-only `new` capability; run 2's split of Logistics is out.
4. The recommendations in § 2 (local findings) are adopted as written unless the v3 prompt
   says otherwise.

---

## 1. Findings, ranked by cost of being wrong (as delivered)

1. [§ 3 "How Build is triggered", § 5 board, § 10, § 12 "Landing"] [`core/scheduler.py:fire_function`; `scripts/sync_dev_backlog.py:fetch_events`, fold of `.claude/backlog_inbox/*.md`; `deploy.sh:152` `git pull origin main`; `.gitignore` `data/personas/*/`]
   Wrong: The plan never says which machine Build runs on, and its pieces require both at once.
   Fails: The ledger `build_tick` writes lives in a gitignored VM directory the Mac never sees, so `build_board.py`/`build_brief.py` read nothing, the REPAIR hook in a Mac script has no write path to that ledger, `request_build`'s "also written to DEV_BACKLOG § Inbox" has no write path from the VM, and any tracked file the runtime writer edits on the VM checkout is overwritten or conflicts on the next `deploy.sh` pull with no route back into the repo for "Mike commits".
   Costs: Every human surface and both redundancy records are dead on arrival and generated capabilities are silently lost at the first deploy after they land — high.
   **Status: resolved by § 0.1–0.2.**

2. [§ 3 N11 "Claude Code session", § 6.7 "two mechanisms because there are two actors", § 6.8 verify `cwd=ROOT`, § 12 "Landing"] [`core/build/writer.py apply()` is the deny list, shape gate, ceiling, undo journal and constitution check; nothing states whether it or the Claude Code session writes the capability's files]
   Wrong: The plan leaves undecided which actor writes which file, and that decision determines whether the phase-3 safety surface guards anything.
   Fails: If the executing session writes, every file bypasses the deny lists, the parity gate, the size floor and `revert()`, and `verify.py` runs against a root tree the worktree's changes are not in; if the writer writes, N11 has no defined input and `edits` has no producer.
   Costs: Phase 3 is either the wrong component or unbuildable — high.
   **Status: resolved by § 0.1 — the runtime writer writes; N11 is removed; the Planner (or the brief for `needs_tool`) is the producer of file contents.**

3. [§ 4 "Declared-variable homes", § 4 "Policies live beside the persona", § 6.2 deny list] [`config/personas/{p}/profile.yaml` exists only on the VM (`deploy.sh` header); the writer hardcodes `config/personas/**` and `data/personas/**` as refused; `.claude/settings.json` denies the same paths]
   Wrong: Two of the three declared-variable homes and the policy store are on the writer's own hardcoded deny list.
   Fails: A `this_persona` row validates and then every write to it is refused by `apply()`; `kind: policy` has nowhere it is permitted to land.
   Costs: The mechanism that makes Inquiry cheaper over time cannot store a single policy or persona-scoped variable — high.
   **Status: resolved — `this_persona` and `query_only` variables are declared through the existing `write_profile` / `write_wisdom` tools (runtime-owned files, already a write path), never the file writer; policies live under `data/personas/{p}/build/policies/`.**

4. [§ 11 Run 2, § 6.4 ceiling defaults, § 4 registration matrix, § 10 "Modified"] [`config/modules/build.yaml` ships `may_create_agent_files: false` and `ceiling: generated_registration`; run 2 creates an agent file, edits prose in two Red-tier files, and must add the name to the copy-exactly list at `coordinator.md:84-85` and `_AGENT_NAME_MAP` at `orchestrator.py:5503`, which § 10 says do not change]
   Wrong: Run 2 cannot pass the writer under the plan's own v1 defaults, and § 10 and § 11 disagree on whether the Coordinator's name list changes.
   Fails: Creating an agent file is barred, the prose edits park, and a leaf not in the copy-exactly list is never dispatched.
   Costs: The first proving run instead proves the ceiling blocks it — medium.
   **Status: dissolves — run 2 is re-chosen under § 0.3. The surviving rule: the bootstrap runs execute with the ceiling raised by hand in `build.yaml`; v1 defaults apply from the first post-bootstrap run; Coordinator names are injected from the overlay at prompt assembly, not edited into `coordinator.md`.**

5. [§ 11 "Remove the venue paragraph from logistics.md", § 13.13] [`config/agents/logistics.md:76` and `:298` call `find_places` inside the horizon scan; `config/templates/scheduler.yaml:76` fires that scan via the Coordinator; `tools/subagent.py:40` refuses `run_subagent` at depth ≥ 1; `recreation_hobbies` also holds `find_places`]
   Wrong: The venue capability is a dependency of the scheduled anticipatory-logistics pass, not a paragraph.
   Fails: After the split Logistics cannot call a sibling and the Coordinator cannot dispatch one with a location only Logistics learns from the calendar.
   Costs: A live scheduled feature degrades silently the day run 2 lands — medium.
   **Status: dissolves with run 2. Standing lesson for any future `split`: the surface map must list every scheduled job that exercises the carved-out capability, and the disposition evidence must name every agent holding the tool.**

6. [§ 3 "REPAIR is filed by code… No model decides this — it is counting", § 11 Run 3] [`tools/logger.py:411` `write_quality_event(source_agent=…)` is model-filled; only `coordinator` and `synthesizer` hold the grant (`routing.yaml:41`, `:50`)]
   Wrong: The signal that fires REPAIR is a model-attributed field, not a count of anything the runtime observed.
   Fails: A capability answering wrongly emits nothing by itself; a REPAIR needs three user corrections each attributed by the Synthesizer to the right capability.
   Costs: Run 3 either never fires or fires on the wrong capability — medium.
   **Adopted: code writes the correction event and attributes it to the specialist that ran on the previous turn (what `tools.turn_referent` already knows). Run 3's REPAIR is filed by hand from the board, because run 3 tests the dossier, not the trigger; the trigger is a separate later test.**

7. [§ 1 requirement 1, § 12 "three agents nested", § 14 "advances one node and returns"] [`core/orchestrator.py:6553` — every `run_session` opens its own request trace; `core/trace.py:229-233` nests only with a parent on the same thread; one `RequestTrace` written per request]
   Wrong: One node per tick and one nested trace per job are mutually exclusive under the trace unit that exists.
   Fails: Three nodes across three ticks are three top-level traces with no parent.
   Costs: The first standing requirement is unmeetable as designed — medium.
   **Adopted: Inquiry → probe → Librarian → Planner run in one tick as one request with the three agents nested; per-node atomic artifacts remain the resume cursor. § 14's zero-idle claim still holds.**

8. [§ 4 "Encoding questions with FAISS", § 9] [`core/memory.py:202-228` `index_entry` appends to one `IndexFlatIP` with `{text, source, date}` metadata; `search_memory(query, k)` has no source filter and is granted to eleven specialists]
   Wrong: The index the plan wants to hold Build's questions is the same unfiltered index every personal specialist searches as memory.
   Fails: Inquiry's questions come back as recalled entries; the phase-6 reindex makes it retroactive.
   Costs: Specialist recall contaminated with build-time scaffolding presented as memory — medium.
   **Adopted: Build gets its own index file under its own directory. The reindex path is no longer a prerequisite for question dedupe; § 9 "moves early" and phase 6's position in § 16 change accordingly.**

9. [§ 7 Rung 1] [§ 4's QuestionSet field is `class` with eight spine values; no artifact carries `tier`; § 4 itself rejects `kind: orienting` as a slot to fill]
   Wrong: Two of the five coercion targets name fields and values that do not exist in the artifacts the same plan defines.
   Fails: A class coerced to `orienting` then fails the ordering constraint, so rung 1 hands rung 3 a guaranteed rejection.
   Costs: The retry ladder is built against a superseded schema — medium.
   **Adopted: rewrite the table against § 4. Unknown `class` → move the question to `declined_to_ask[]` with the defect noted (no safe class exists). Delete `tier`. Add `disposition unknown → new`.**

10. (Verification note, below the significance bar for ranking.) [§ 6.3] `relationships` holds `send_email` and `send_calendar_invite` at `routing.yaml:142`. The deny list is unaffected, but § 6.3 must enumerate the grants, not the holders.

---

## 2. What the VM ruling and option 1 change in the plan

**The fact that forces it.** Every registration target in v2 is a tracked file in the VM's
production checkout. The VM's deploy is a plain `git pull` (`deploy.sh:152`) with no
dirty-tree handling; git refuses to pull over a locally modified tracked file, so the first
`extend`/`split` Build lands blocks every subsequent deploy. A new file at a tracked path
survives pulls but is in no commit and no backup (`scripts/metatron-backup.sh:83` captures
only `data/personas`, `config/personas`, baselines and the chat DB). The VM already has a
pattern for runtime-owned config git never sees — `config/personas/{p}/` — and option 1 is
that pattern applied to capabilities.

**Option 1 — overlay.** A VM-owned, gitignored directory (add it to the backup list) holds
generated capabilities. Four runtime load seams, built as ordinary deployed code in the Build
phases:

1. `load_agent` (`core/orchestrator.py:681`) falls back to the overlay directory.
2. `_load_routing` (`core/router.py:56`) merges an overlay routing record — one record carrying
   both the local and the cloud entry, so parity is a schema property rather than a two-file
   gate. **Red tier.**
3. Coordinator valid-name list and `_AGENT_NAME_MAP` (`orchestrator.py:5503`) are extended
   from the overlay at prompt assembly; `coordinator.md` is not edited.
4. `_UNAVAILABLE_CONSEQUENCE`, `_ALWAYS_CONFIDENTIAL` and `knowledge_domains` entries come
   from the overlay record.

Tool registration (`register_tools`) is **not** a seam in v1, because `kind: tool` is out.

**Option 2 — branch and merge (rejected).** Build writes into a second VM worktree and pushes
a branch; Mike merges on the Mac; deploy lands it. Every disposition and kind possible, git is
the undo. Rejected because it needs push credentials on the production VM (a new outbound
grant), acceptance can only run after a deploy, and `kind: tool` still needs a code-writing
agent.

**Other settlements under the VM ruling.**
- N11 "Claude Code session" is removed. The Planner produces the agent-file text and the
  overlay record; the writer applies them. `needs_tool` rows become briefs for Mike.
- The undo journal (§ 6.7, § 13.6) stays — it is now the only undo, since there is no
  worktree. The writer's deny list gains one derived rule above the hardcoded ones: **any
  path in `git ls-files` is refused.** That is what makes option 1 hold mechanically.
- `request_build`'s redundancy record is a quality event (`BUILD_PROPOSED`) — the existing
  VM→Mac fetch in `sync_dev_backlog.py` already surfaces it. The REPAIR hook moves from the
  Mac script into `build_tick`, importing `signature()` from `scripts/sync_dev_backlog.py`.
- `build_board.py` / `build_brief.py` read the ledger over the existing read-only
  `/monitor/file` fetch, or run on the VM over ssh. Both are read-only.
- Verification (§ 6.8, § 12): `qa_sweep.sh`'s checks grep `git ls-files`, so they do **not**
  see overlay files. `verify.py` must run the same checks over the overlay explicitly, and
  the § 12 "same checks" diff still applies.
- "Build never commits; Mike commits" becomes "Build never writes a tracked file; Mike
  promotes" — the promotion path is deferred and is the gate for `split`/`extend`.

**Salvage map.** Unchanged: § 2, § 3's rule and node graph up to N10, § 4's three artifacts
except the registration matrix and variable homes, § 5, § 7, § 8, § 9 (with the index change),
§ 13, § 15. Rewritten: § 4 registration matrix, § 6 writer targets and shape gate, § 10 files,
§ 11 bootstrap, § 12's writer and landing rows, § 14 phases 3 and 7.

**Bootstrap under option 1.** Run 2 as designed (split of Logistics) is out. The first real
run must be a `new`, config-only, agent-kind capability over existing read tools, with an
explicit gap the Coordinator currently misses. The Librarian-gap tools in § 9 are
`needs_tool` briefs, implemented on the Mac by ordinary development before the runs that
need them.
