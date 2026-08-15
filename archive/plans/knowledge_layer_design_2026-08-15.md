# Personal knowledge layering — subject-scoped facts, retrieved when relevant

> **⚠ SUPERSEDED the same day it was written, 2026-08-15. Do not build from this file.**
> The authoritative version is the approved plan at
> `~/.claude/plans/to-be-clear-we-modular-knuth.md`. This draft is kept because its § 0–1
> reasoning — why the store already existed, and why the profile and the memory index are both
> the wrong home — is unchanged and is the argument the plan rests on. **Four things in it are
> now wrong:**
>
> 1. **The write model.** This draft says keep writes narrow. Mike's decision: the **Synthesizer**
>    is the main conversational writer, with direct write kept only where the proposal relay would
>    be lossy or does not exist (Diarist, Pattern Miner, Mental Wellbeing's bulk capture).
> 2. **`seasonal` as a domain.** It is a *kind*, not a domain — this draft reproduced the very
>    axis error it diagnoses. Dropped from the list.
> 3. **`kind: pattern|fact`.** Replaced by `provenance: stated|observed` — a question a model can
>    answer from its own context, where "pattern or fact?" is one it answers inconsistently.
> 4. **The oatmeal pass criterion.** Unachievable as written: `coordinator.md:145` lists
>    `ate, skipped meals, diet, weight` as Physical Health signal words and `:48` mandates
>    dispatch for advice requests, so a correct Coordinator fails this draft's test. The feature
>    needs a routing amendment this draft never scoped, plus a counter-test.
>
> Found by an adversarial Fable 5 review of the plan, which returned sixteen findings.

*Design track, 2026-08-15. Answers the open question: which axis owns subject knowledge, and
which agents read it automatically vs. on call.*

Precedents this builds on: `f9ffd2a` (`_PROMPT_EXCLUDED` made to enforce; `health_notes` moved
behind it), `6913ad7` (`evening_ritual.md` — the persona axis), [ROADMAP.md](ROADMAP.md) § D2
(the (a) behavioural rules vs (b) domain data split).

---

## 0. The finding that reframes the track

**The store already exists and it is the answer.** [tools/wisdom.py](tools/wisdom.py) — the Life
Wisdom Depot — was built for precisely this class of fact. Its docstring:

> Stores persistent background knowledge about the user: seasonal patterns, personal quirks,
> recurring annual events, evolving preferences. **Separate from logs (episodic) and journal
> (narrative). Wisdom entries are stable facts that accumulate over time and get surfaced
> proactively.**

It is per-persona (`data/personas/{p}/wisdom/wisdom.json`), sensitive-tier, `0600`, has a
`category` axis, updates in place by key rather than appending, and — notably — already has the
merge and dedup tooling the CRM was found to lack this morning (`find_duplicate_wisdom`,
`merge_wisdom_entries`, archive-on-merge with a `merged_into` pointer).

**It is also almost entirely unreachable.** Instruction-vs-grant, measured against
[routing_cloud.yaml](config/modules/routing_cloud.yaml):

| Agent | Agent file instructs wisdom | Granted |
|---|---|---|
| mental_wellbeing | ✅ ×3 | ✅ |
| physical_health | ✅ | ✅ |
| diarist | ✅ ×2 | ✅ write-only |
| **finance** | ✅ | ❌ |
| **learning_growth** | ✅ | ❌ |
| **pattern_miner** | ✅ | ❌ |
| **recreation_hobbies** | ✅ | ❌ |
| **relationships** | ✅ | ❌ |
| **work_vocation** | ✅ | ❌ |
| **synthesizer** | ❌ | ❌ |
| coordinator | ❌ | ❌ |

Six agents are instructed to use a tool they do not hold. This is the identical class already
corrected twice and recorded in the routing comments — `relationships`/`search_memory`
(2026-08-10: *"the agent was instructed to use a capability it did not have, and silently lost
recall"*) and `logistics`/`write_agent_config` (2026-08-05, eight warn-mode denials). It is the
same failure a third time, in a store nobody was looking at.

So the track is not *build a knowledge layer*. It is: **Wisdom is the knowledge layer. Give it a
manifest, give it reach, and correct one schema defect that is silently collapsing its subject
axis.**

---

## 1. The open question answered — where the subject axis lives

### Not the profile

[tools/profile.py](tools/profile.py) is the **identity spine**: name, location, timezone,
languages, contact, age. Three reasons it is the wrong home for subject knowledge, all of them
already written into the module:

1. `WRITABLE` is a deliberately closed set — *"an unknown field is a signal that something needs
   designing, so it is refused loudly rather than absorbed."* Every new subject would be a code
   edit to `_SCALAR_FIELDS`. That is a direct violation of the founding principle: config is the
   product; a behaviour change requiring a code change is a design failure.
2. It stores **flat scalars** — one string per field. Subject knowledge accretes. `health_notes`
   is already being asked to hold a paragraph.
3. Its prompt-rendered half must stay short, because it rides every head-layer and routing call.

**`health_notes` is therefore not the pattern — it is the migration case.** It is a field that
outgrew the schema, and this morning's fix (moving it behind `_PROMPT_EXCLUDED`) treated the
symptom. Its content — a standing breakfast composition — is a wisdom entry in the `food` domain.
Retire the field once migrated; leaving both homes open is a One Home Per Rule Class violation.

### Not the memory index

[core/memory.py](core/memory.py) is **episodic and append-only**. Its entire public API is
`index_entry()` / `search_memory()` — there is no delete and no update path. Consequences for
standing facts:

1. **Revision decays into duplication.** Change to 80g oats and both versions are indexed and
   ranked against each other; whichever embeds closer to the query wins. That is the Eva/Iva
   problem — *no merge or delete tooling* — recreated deliberately.
2. **Standing facts compete with dated noise.** A wisdom entry would contend for the same `k`
   slots as hundreds of daily log entries about unrelated things.

Memory is the **retrieval mechanism over the home, not the home** — which matches the decision
already taken (manifest first, retrieval second). See § 5.

### Not `config/personas/{p}/{subject}.md`

This is the closest call, since `evening_ritual.md` is the live precedent and the persona axis is
right. It fails on **class**, not axis:

1. `self_development.md` and `evening_ritual.md` are user-owned **procedure** — how to conduct
   something. A learned fact is a different class: written by an agent at runtime, not authored.
   Every other runtime-written user store already lives under `data/personas/{p}/` (crm, agent
   config, archive, wisdom, baselines).
2. `load_config()` loads persona config files **unconditionally**. Putting subjects there means
   either loading them all — the broadcast this track exists to remove — or introducing a
   directory whose rule is "some files here load and some don't", which is exactly the kind of
   unstated policy `_PROMPT_EXCLUDED` was found guilty of this morning.

The distinction to hold: **`config/personas/{p}/` holds procedure the user owns.
`data/personas/{p}/wisdom/` holds facts the tool learned.** `evening_ritual.md` stays where it is.

### Verdict

> **The subject axis lives in the Wisdom store, keyed by `category`. It is the home it was
> built to be. What it lacks is a manifest, reach, and a category schema that holds.**

---

## 2. The schema defect that must be fixed first

`write_wisdom()` coerces an unrecognised category to `"patterns"` **silently**:

```python
if category not in WISDOM_CATEGORIES:
    category = "patterns"
```

`profile.py` refuses an unknown field loudly on explicitly stated reasoning. Wisdom does the
opposite, so `category="diet"` written today lands in `patterns` and the subject axis quietly
collapses into one bucket. **A manifest built on top of this would enumerate categories that do
not reflect where anything actually went** — the same shape as `_PROMPT_EXCLUDED` promising
enforcement it did not provide. Fix before the manifest, not after.

Second, the six categories are an incoherent axis — a mix of **kind** (`patterns`, `quirks`,
`preferences`) and **domain** (`health`, `seasonal`, `annual`). One fact can be true of several:
a seasonal food preference is all three. Kind is load-bearing for nothing; domain is what the
manifest needs, because the question the manifest answers is *whose territory is this*.

**Recommendation: re-cut categories as domains aligned to the specialist roster** — `food`,
`health`, `work`, `relationships`, `money`, `learning`, `recreation`, `logistics`, `seasonal` —
and refuse an unrecognised one. Migration is a small mapping script over five synthetic personas
plus Mike's, and Mike's `wisdom.json` is VM-owned, so it runs there, not on the Mac.

*This is the one schema decision in the plan that goes beyond what was scoped. It is in scope
because the category axis **is** the subject axis, which is the open question.*

---

## 3. The manifest — where it renders, and to whom

Derived from the store, never hand-written. Distinct categories present in `wisdom.json`:

```
## What you have on file about the user

Standing knowledge is recorded under: food, health, work, seasonal.
Read it with read_wisdom(category=...) when the conversation turns to one of these.
Do not guess at what it contains.
```

~15–25 tokens, scaling at roughly one token per category. **Derived by enumerating the store**, so
it cannot drift from it — today's lesson applied at build time rather than after the leak.

### Placement

The prompt-assembly branches in `_run_single_agent()` ([core/orchestrator.py:3115](core/orchestrator.py#L3115))
decide this cleanly:

| Layer | Gets | Therefore |
|---|---|---|
| Head (Synthesizer) | `load_config()` → includes `load_profile()` | ✅ manifest |
| Routing (Coordinator) | `load_goals()` + `load_profile()` | ✅ manifest |
| Specialists | `load_goals()` **only — no profile at all** | ❌ manifest |
| Bare / research_agent / diarist | agent file only | ❌ manifest |

**Put the manifest in `load_profile()`.** One edit reaches exactly the two agents that need it.

- **Synthesizer** — this is the oatmeal case verbatim: a casual conversation about food, the
  manifest says `food` is on file, one `read_wisdom` call, no Physical Health dispatch.
- **Coordinator** — holds `allowed_tools: []`, so the manifest is the *only* form in which
  knowledge can reach it, and it is a genuine routing signal: knowing `food` is on file is what
  lets it decline to dispatch PH for a diet question. ~20 tokens on a Flash-Lite call.

Specialists do not need the manifest — the Coordinator's directive already tells them what they
were dispatched for. They need the **tool**.

> **Manifest to the head, tool to the hands.**

*Note for A8: this adds ~10 lines to `load_profile()`, which the refactor relocates wholesale to
`core/config.py`. No conflict, but the lines move.*

---

## 4. Automatic reads vs. callable — the three tiers

### Tier 1 — Pushed, never pulled (unchanged)

The identity spine in `load_profile()` and everything safety-bearing. No change.

**The safety carve-out, stated as what is actually enforceable.** `medication_profile` stays in
`agent_config.json` behind `_GUARDED_KEYS`, with `physical_health.md`'s **mandatory** read on the
`MEDICATION_MISSED_CRITICAL` path. Mike's rule — nothing safety-bearing behind a discretionary
read — is honoured not by keeping medication content out of Wisdom (unenforceable; a content
sniffer would be theatre) but by the stronger guarantee:

> **Wisdom is never the *sole* home of a fact a safety flag classifies from.**

Enforceable half in Python: `write_wisdom` refuses the reserved category names `medication`,
`clinical`, `crisis` and points at `write_agent_config`. Structural half: never remove the
mandatory `read_agent_config` from the flag path. A knowledge subject may supplement it; it may
never replace it.

### Tier 2 — Manifest + callable (the default, and where everything lands in phase 1)

Grant `read_wisdom` to the **six agents whose own files already instruct it** — `finance`,
`learning_growth`, `pattern_miner`, `recreation_hobbies`, `relationships`, `work_vocation`. This
is not a widening on request; it is the third instance of a correction already made twice, and
the instruction files are the specification.

Grant `read_wisdom` to the **Synthesizer** — the one addition beyond instruction parity, and the
worked example is the argument for it.

`write_wisdom` stays narrow: the three agents that hold it today. Reach is a read problem.

### Tier 3 — Auto-push a category into an agent's prompt

**Not built in phase 1**, and this is a decision with a trigger rather than a deferral.

The candidate is Physical Health + `food`: PH is dispatched for a diet question anyway, so the
`read_wisdom` call is a wasted extra turn through a Pro model — precisely § D2's latency argument.
But auto-push re-introduces broadcast at the specialist level, which is what we are leaving, and
**we cannot yet know which pairs deserve it.**

Promotion criterion: instrument `read_wisdom` in the trace, and after two weeks of real use
promote a (category, agent) pair to auto-push when that agent reads that category on **>70% of
its dispatches**. Below that, the call is cheaper than the broadcast. Front-matter or a routing
mapping declares it when the data justifies it — not before.

---

## 5. Retrieval, layered second

`read_wisdom(category=...)` returns the whole category. That is correct while categories are
small and is where phase 1 stops. Two things to know for phase 2:

1. **`find_duplicate_wisdom()` already does the semantic half — badly.** It instantiates
   `SentenceTransformer("all-MiniLM-L6-v2")` inline on every call, bypassing
   `core/memory.py`'s cached `_get_model()` singleton, so each invocation reloads ~80MB. Routing
   it through the singleton is a small fix and is the prerequisite for anything further.
2. **If Wisdom is ever indexed into FAISS, it goes in its own namespace** —
   `data/personas/{p}/memory/knowledge.faiss`, never the log index. Standing facts must not
   compete with dated entries for the same `k` slots, and the log index has no revision path.
   This is § 1's argument turned into a build constraint.

---

## 6. Build order

1. **Fix the silent category coercion** — refuse an unrecognised category, `profile.py`-style.
   *(Nothing else is trustworthy until this holds.)*
2. **Re-cut categories to domains** + migration script. VM-side for `mike`.
3. **`read_wisdom(category=...)`** — read-by-category alongside read-by-key, with a size cap.
4. **Manifest in `load_profile()`**, derived by enumerating the store.
5. **Grants** — `read_wisdom` to the six instructed agents + Synthesizer, both routing files in
   parity.
6. **Migrate `health_notes`** to a `food` wisdom entry; retire the field from `_SCALAR_FIELDS`
   and `_PROMPT_EXCLUDED`.
7. **Reserved safety category names** refused in `write_wisdom`.
8. **Trace instrumentation** on `read_wisdom`, for the Tier 3 promotion criterion.

Steps 1–3 are `tools/wisdom.py` only. Step 4 is `core/orchestrator.py` (Red tier — prompts). Step
5 is `routing*.yaml` (Red tier). Step 6 touches VM-owned persona data.

**Test after 4–5:** a food question to the Synthesizer with no PH dispatch in the trace, and the
oatmeal detail present in the response. Pass signal: `read_wisdom` appears in the trace,
`run_subagent(physical_health)` does not. Then `python tests/run_a4_safety.py --suite pipeline`
as the regression gate, since step 6 moves content that sits adjacent to the health domain.

---

## 7. Budget and model

| Step | Rough cost |
|---|---|
| 1–3 (wisdom.py schema + read-by-category) | ~30–50k tokens |
| 4 (manifest, derived) | ~20–30k |
| 5 (grants, two files in parity) | ~15k |
| 6 (health_notes migration, VM-side) | ~20k |
| 7–8 (reserved names, trace instrumentation) | ~20k |
| Test + A4 pipeline regression | ~25k |
| **Total** | **~130–160k tokens** |

**Execution model:** Sonnet 5 for steps 1–3 and 7–8 — mechanical, well-specified, single-file.
**Opus 5 for steps 4–6**, which touch Red-tier prompt assembly, routing grants and live persona
data, where the judgement is the work and Red-tier work is not delegated.

**Split worth taking:** build steps 1–3 with Sonnet 5, then review the category re-cut with Opus 5
before the migration runs — a wrong domain axis is cheap to fix before step 2's migration and
expensive after.
