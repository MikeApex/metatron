### 2026-11-26 (the user's own data, phase 3 — Places: built, Fable-reviewed, deployed, seeded and live-checked on mike) — `701949c`, `2293026`, `a624338` — **all deployed by Mike (VM at `a624338`)**

**Incoming handoff:** `archive/handoffs/2026-11-25-data-objects-phase-3-places-build-prompt.md` (Opus, high). Build plan: `archive/plans/data_objects_phase3_build_plan_2026-11-25.md`.

**What a user gets.** Name a place and Metatron saves it with its public position, opening hours, verdict (`go_to | try | avoid`) and occasion (`{kind, what, near}`). Arriving there is a transition like arriving home, so the day planner starts from it and the visit is recorded. A meal, an errand (a task whose `zone` is that place) or a free hour near a saved place that fits is attached to the Synthesizer and Logistics by code. An avoid place comes back to steer away. A name mentioned three times in 30 days without being saved gets one card.

**Mike's rulings, choices 1–8, all "as rec" except 7 and 8:**
- 7: M3 was run at the end of this chat, not in a separate session.
- 8: occasion kinds are extendable per user, never mapped onto the nearest base kind.
- **Mike's question on conflicting writers** became a provenance rule in `archive_write`, for any template's `guarded` fields: same-or-higher source wins with history kept; lower over higher is held and asked about on its second arrival; two stated values in one turn are asked once; a change is said once. Places guard `verdict` and `occasion`.
- **Opening hours:** "more data is better for places". They are fetched once with each lookup (Enterprise SKU).

**One writer, by code (phase 1's lesson).** The template says `writer: code`. Every model door refuses `places`: `write_archive`, `write_data_object`, amend's entry and whole-log acts, merge into it, the derived writer, and a noticed-list match. The Coordinator emits `PLACES` (`save | relocate | private | public | forget | confirm`), and `tools/saved_places.py` writes it. Instructions telling Diarist, Logistics and Recreation to file places were removed, with Mike approving each line.

**Checked against recent work:**
- No zone reader had changed since 11-21.
- The obligations check was at 2545, not ~2168.
- **Tasks already had a `zone` field**, so "task → place" widened it instead of adding a second field.
- `read_archive` was no longer a model tool, and `read_data_object` already stripped coordinates from `places`.
- Capture's place facts carried no name, so the extractor was given one.

**Fable diff review: 15 findings plus 4 on coordinates, all fixed except one.** The ones that mattered:
1. A merge INTO places carried a model-written position into `zone_for`.
2. "Add X to my places" ended in "did not save".
3. A bare "no" to another question permanently silenced raised places, the avoid warning included.
4. A fuzzy match overwrote a different place ("Brighton" became "Brixton").
5. A zone arrival visited a similarly named place.
6. A private place's name leaked.
7. `read_data_object(contains=<digits>)` worked as a coordinate oracle.
8. Plus Codes could reach a reply.
9. Exact distances to several places could reconstruct the last position; distances are now rounded to 50 m.

**Left, phase 4:** walking past a saved place counts as arriving, because dwell needs the background feed.

**M3, guided.**
- **Prices:** Text Search Pro is $32 / 1,000 with 5,000 free a month; hours are Enterprise, $35 / 1,000 with 1,000 free. That's $0 at this volume.
- **Seed:** `scripts/seed_places.py`, per-row corrections from a `/tmp` file of real names. 12 of 15 places are positioned and 3 skipped, with renames (a misspelt name kept as an alias; a wrong one, Itihaas → Preem, with no alias, because Itihaas is a real neighbour), purposes, visit dates, a private home found by postcode alone, and hours.
- **Live check on the VM as mike, TEST-marked: 12/12.** A place said aloud gained an address with no coordinate in any reply; a pizza question tonight named Bianco 43 "50 m away, open for dinner at 6:30" and not 108 Brasserie; arrival at the Wallace Collection moved the start point (run on a temporary copy). The TEST places are archived.

**Wrong earlier:**
1. "Tasks need a `place` reference." The `zone` field was already there.
2. "Avoid is an occasion." It's a verdict.
3. "A hand-run script sees the Places key." Only the server's unit loads `.env`, and the first `--apply` looked nothing up. The new missing-key warning is what said so.
4. "Bianco 43 can be arrived at." It sits inside the home circle, so home wins, which is correct.

**Pre-existing, not this session's:** `instruction_leak_filter`'s short-span check is position-dependent on `synthesizer.md` (it failed on 11-23 HEAD too); round-2 F8, `task_ledger_consult`, `a4_complexity_threading`, `multi_user_isolation`, `quality_event_reconciliation` and `action_provenance` 9/10 fail identically on clean HEAD.

**Outgoing:**
- **Mike (in the app):** "Clipstone is the restaurant in Fitzrovia" (it resolved to the Mansfield village); confirm Pizza Express on Greenwich Church Street.
- **A cosmetic leftover:** the first run's `lookup_failed_at` stamps aren't cleared by a successful lookup (an empty value is skipped by the merge). Harmless, since it's read only when there is no position.
- **Next:** phase 4, `archive/handoffs/2026-11-26-data-objects-phase-4-background-location-build-prompt.md` (Opus, high). Its first step is the gate: WhatsApp Phase 2's walkthrough through M4.

