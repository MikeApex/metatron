### 2026-08-15 (the wisdom store gains a subject axis — knowledge layering phase 1) — `13134bc`, `a35acfa`, **deployed, migration applied**

Incoming handoff: `[DB-0810-15]` shipped and profile detail stopped riding every call
(`f9ffd2a`). `_PROMPT_EXCLUDED` had just been made to enforce, with `health_notes` moved behind
it, and Mike's rule stated: **detail the tool learns about a user belongs at the level that needs
it, retrieved when relevant, not broadcast on every call.** Oatmeal was the worked example.

**The design track's finding reframed the whole thing: the store already existed.**
`tools/wisdom.py` — the Life Wisdom Depot — was built in Phase 3 for exactly this class and says
so in its docstring ("stable facts… separate from logs (episodic) and journal (narrative)"). It
had a category axis, update-in-place by key, and merge/dedup tooling the CRM lacks. It was also
almost unreachable: **six agent files instruct `read_wisdom` and are not granted it**
(`finance`, `learning_growth`, `pattern_miner`, `recreation_hobbies`, `relationships`,
`work_vocation`), and the Synthesizer had neither instruction nor grant. Third instance of a
class already corrected twice — `relationships`/`search_memory` (08-10),
`logistics`/`write_agent_config` (08-05). So the track became *make the existing store correct,
reachable and selective*, not *build a knowledge layer*.

**Rejected homes, with reasons.** *The profile* — `WRITABLE` is a deliberately closed set, so
every new subject would be a code edit, which is the design failure the founding principle names;
and it stores flat scalars where subject knowledge accretes. `health_notes` is therefore the
migration case, not the pattern. *The memory index* — `core/memory.py` has no delete or update
path, so revising a standing fact would leave both versions indexed and ranked against each
other; that is the Eva/Iva no-merge-tooling problem rebuilt deliberately. Memory is the retrieval
mechanism over the home, not the home. *`config/personas/{p}/{subject}.md`* — right axis, wrong
class: `evening_ritual.md` is user-owned *procedure*, a learned fact is agent-written at runtime,
and `load_config()` loads persona config unconditionally so subjects there would either broadcast
or create a directory where some files load and some do not.

**Subject axis, not the agent roster — and the record should say it won on two arguments, not
four.** Mike's instinct was `physical_health/diet`; he changed his mind after pushback, then
asked for it to be re-checked, which a Fable 5 review did. Carrying: a roster change must never
become a user-data migration (`time_director` folded in, `tone_profiler` added within a month),
and facts are many-to-many with agents (`food` is read by physical_health, relationships and
logistics, so one agent's namespace asserts false ownership). **Overstated at the time and
corrected here: the `agent_config.json` collision argument.** Those two stores also differ by
provenance and content class, not "only by file format". The zero-specialist argument is
cosmetic. Note also the chosen list is substantially the roster renamed with `physical_health`
split four ways — the practical delta was smaller than the debate implied. The agent coupling
moves to `config/modules/knowledge_domains.yaml` (unbuilt, step 4).

**Two schema decisions.** `seasonal` is **not** a domain — seasonality is temporal and
orthogonal, so keeping it rebuilds the kind/domain collapse being removed. And `provenance:
stated|observed` replaced a drafted `kind: pattern|fact`: "prefers oat milk" is a fact if Mike
said it and a pattern if the Diarist inferred it, so only provenance is a question a model can
answer from its own context.

**Fable 5 reviewed the full plan and returned 16 findings; 3 blocking, 2 of those errors in my
draft.** (a) The oatmeal pass criterion was **unachievable** — `coordinator.md:145` lists `ate,
skipped meals, diet, weight` as Physical Health signal words and `:48` mandates dispatch for
advice requests, so a correct Coordinator fails the test. The feature needs a routing amendment
never scoped, plus a counter-test that PH *is* still dispatched for "log what I ate" — fixing
over-dispatch by creating under-dispatch is the real risk. (b) `seasonal`, above. (c) Strict
refusal on the fire-and-forget Diarist path would convert silent misfiling into silent fact
**loss**. Also caught: `diet`→`food` share no characters, so the drafted fuzzy matcher could
never have worked; an alias map was required.

**Built (`13134bc`).** `category` → `domain` + `provenance`; alias map (modelled on
`_LANGUAGE_NAMES`) with fuzzy matching for typos only at a **measured** cutoff of 0.75 (11/11
typos resolved, 0/12 novel subjects absorbed; 0.70 swallows "gardening" and "politics").
Refusal is never terminal — the fact always lands, in `other` with `proposed_domain` if
unresolved, because the Diarist writes in a discarded-output daemon thread. Multi-domain capped
`read_wisdom` (15, newest-first; uncapped for consolidation only). Derived `domains_present()`
for the manifest.

**Found while building, not planned: `write_wisdom` had no lock on a read-modify-write.** Under
40 concurrent writes it kept **2**; with a `FileLock`, 40. Verified discriminating by stubbing
the lock out. Rare today only because writers are rare — the planned Synthesizer write grant
would have made it routine. `core/memory.py` had the pattern already, added after an interleaved
write corrupted `metadata.json`. Also took `find_duplicate_wisdom`'s ~80MB-per-call
`SentenceTransformer` reload onto that cached singleton (one strand of `[DB-0810-11]`).

**The migration was the most instructive part, and the review pass is the only reason it is not
wrong (`a35acfa`).** First run against Mike's live 59-entry store: the keyword fallback matched
bare **substrings**, so `"eat"` fired inside *w-eat-her* and `"ate"` inside *str-ate-gy*,
*upd-ate*, *w-ate-r*. `plant_care_hot_weather`, `fitness_strategy`, `crm_update_friction` and
`communication_preferences` all classified as **food** — roughly half of thirty keyword
assignments wrong. Word-boundary matching fixed the egregious cases and left ambiguous ones
(`"run"` still matched *payroll runs*). **Conclusion: heuristics were the wrong instrument for a
59-entry store.** All 59 assigned individually by reading them — which is what the plan specified
and what an earlier "mechanical script" assumption had got wrong.

**Reading all 59 found more than domains — 24 of 59 do not belong in the fact store.** Eight are
interaction preferences belonging in the persona file (`communication_style_preference`,
`system_framing_preference`, `admin_comms_reduction`, …). Three are tool defects filed against
the user. Two pairs are near-duplicates. `grocery_check_in_cycle` records only *that* a
correction happened, not what it was. `language_preference` duplicates the
`profile.yaml output_language` field `[DB-0810-15]` shipped the same day and can drift from it.
**And `oatmeal_formula` — the worked example this entire track was designed around — is an
unfilled placeholder** reading *"[User needs to specify their formula details here]"*. The real
composition was in `profile.yaml health_notes`, which is precisely the relocation the track
exists to perform. All 24 migrate in place and are reported; moving them is a separate act.

**Security: `vertex-key.json`, a live GCP service account key, was neither tracked nor
gitignored** — showing `??` on the VM, one `git add -A` from a public remote. `CLAUDE.md` lists
it in the Denied row, which governs what a session may edit and does nothing to stop git. The gap
was structural: this repo's *data* ignore rules are systematic while its *credential* rules were
incidental (`.env` and `caldav.yaml` each added when someone thought of them). Closed with
patterns, not a filename; `git ls-files` confirmed nothing tracked was shadowed.

**Deploy friction worth recording.** The first `./deploy.sh` aborted at the VM's `git pull`:
`tests/bench_whisper_stt.py` had uncommitted local changes on the VM from the parallel Bulgarian
STT session, which had edited it *there* to run the benchmark and then committed the same lines
from the Mac. Byte-identical (same blob hashes), so discarding was safe — but it was checked
before discarding, not assumed. Separately, that parallel session's `/archive` swept this
session's `[DB-0815-13]` backlog edit into `ff93f31`; the item survived intact. Two windows on
one tree, twice in one session.

**Order that matters and was nearly got wrong:** code must deploy *before* the data migrates.
The VM's old `wisdom.py` reads `category`, so migrating first yields a mixed-schema store as the
old write path re-adds it. The reverse gap is harmless because no caller filters by domain yet.

**State at close:** phase 1 of 12 steps done and live. Steps 4–12 unbuilt — the domain→agent map,
the manifest in `load_profile()`, `KNOWLEDGE_TO_LOAD` pre-fetch through **both** pipeline paths,
`WISDOM_PROPOSAL` parsing, grants, and the Coordinator routing amendment, which the review
identified as the highest-judgment text in the plan. **Nothing is wired at runtime yet** — no
agent reads by domain, so today's change is inert beyond the store being correct. Plan:
`~/.claude/plans/to-be-clear-we-modular-knuth.md`.
