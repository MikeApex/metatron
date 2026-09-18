# Adversarial review of the Build vertical plan (v3, 2026-09-18) — scoped sections

*Reviewer: Opus 5, 2026-09-18. Plan reviewed: `~/.claude/plans/model-fable-5-architecture-sensitive-shimmying-lollipop.md`.
**Scope: § 4 registration matrix, § 6, § 10, § 11, § 12, § 14 only.** The v2 review
(`build_vertical_plan_review_2026-09-18_fable-5-1.md`) and Mike's § 0 rulings are treated as
closed — nothing there is re-raised. Read-only; no code or plan text changed. Every code claim
below was checked against the working tree at `7bca654`, and findings 1 and 2 were reproduced
by running the matcher.*

---

## Findings, ranked by cost of being wrong

### 1. A generated capability's own name suppresses the replies that carry its answers
*(§ 4 record `confidential_names`, § 6.5 seam 4; § 12's overlay-seams row does not test for it)*

**What is claimed.** `confidential_names: [home_care]` is "appended to `_ALWAYS_CONFIDENTIAL` at
filter time" (§ 4), and seam 4 makes "confidential names appended at filter time" (§ 6.5).

**What that list is.** [`core/orchestrator.py:1389-1391`](core/orchestrator.py) states the
invariant in its own header: *"Code identifiers: contain underscores, slashes, or are otherwise
impossible in natural prose. Always flag on substring match."* Tier 1 of `filter_output()`
([`core/orchestrator.py:1930`](core/orchestrator.py)) is **unconditional** — one match replaces
the entire Synthesizer response with `_CANNED_FALLBACK`. The list for names that *do* occur in
prose is `_CONTEXT_SENSITIVE` ([`:1415`](core/orchestrator.py)), which is sentence-gated on
architecture vocabulary. **The plan routes every generated name to the wrong one of the two
lists**, and § 4's `name` validation checks only the regex and collision with tracked agents.

**Reproduced.** `_term_regex(term, _TIGHT_JOINER)` splits on non-alphanumerics and rejoins with
a joiner that is *1–4 punctuation characters or empty*:

| term | Synthesizer text | tier 1 |
|---|---|---|
| `home_care` | "your **home-care** tasks are up to date" | HIT — whole reply suppressed |
| `home_care` | "**homecare** is due" | HIT |
| `garden` | "i watered the **garden** this morning" | HIT |
| `errands` | "a few **errands** left today" | HIT |

`^[a-z][a-z0-9_]{2,31}$` admits single-word names, and a single-token entry compiles to the bare
word with alphanumeric lookarounds — so `garden`, `errands`, `travel`, `recipes` each suppress
every reply containing that ordinary word.

**Why it costs the most.** Run 1's capability is named `home_care` and its subject is household
upkeep, so "home-care" is vocabulary the Synthesizer will reach for while relaying its output.
The acceptance in § 11 then returns the canned deflection, and the cause is a `warnings.warn`, not
an error — the same invisible-failure shape as the Vertex cache floor. § 12's overlay-seams row
asserts only that the name *is* seen by the filter, never that adding it leaves ordinary prose
intact.

**Recommendation.** Generated names go to `_CONTEXT_SENSITIVE`, not `_ALWAYS_CONFIDENTIAL` — the
sentence gate is exactly the mechanism for a name that is also English, and it is already built
and tested. Add to § 12's writer row: a record whose name is a common word must not suppress a
reply containing that word outside an architecture sentence.

---

### 2. The grant list is an allowlist in one sentence and a deny list everywhere else — and the deny half has a prefix-shaped hole
*(§ 6.3; § 12 writer row)*

§ 6.3's heading is "**Grant deny list**", its table is REFUSED / READ SET / LOGGING, and its
catch-all is *"every `write_*` not named in the read set"*. One sentence inside it says the
opposite: *"A generated capability may hold only tools from the read set."* § 12's writer test
asserts one direction only — *"every § 6.3 refused grant refused at all ceilings"*. An
implementer building to the heading, the catch-all and the test builds a deny list.

**Eight registered mutating tools fall through it.** None begins with `write_`, none is in the
REFUSED list, none is in the read set:

| tool | where | what it mutates |
|---|---|---|
| `merge_contacts` / `unmerge_contacts` | [`tools/crm.py:1766`](tools/crm.py), [`:1974`](tools/crm.py) | collapses or splits contact records |
| `import_contacts_file` | [`tools/contacts_import.py:464`](tools/contacts_import.py) | ingests a file into the contact store |
| `apply_crm_proposals` | [`tools/crm_sweep.py:918`](tools/crm_sweep.py) | applies queued CRM changes |
| `teach_intake` | [`tools/intake.py:922`](tools/intake.py) | writes a standing intake classification rule |
| `record_wisdom_response` | [`tools/wisdom.py:808`](tools/wisdom.py) | writes into the wisdom store |
| `log_interaction` | [`tools/crm.py:1504`](tools/crm.py) | writes a CRM interaction record |
| `create_semantic_anchor` | [`tools/baselines.py:280`](tools/baselines.py) | creates a baseline anchor |

**Cost.** This is the choke point's entire job, and the failure is silent: a generated capability
granted `teach_intake` or `apply_crm_proposals` passes every stated check.

**Recommendation.** State § 6.3 as an allowlist and delete the catch-all — a prefix rule cannot
enclose a tool surface where seven of the eight mutators are named for what they do rather than
for the verb `write`. Keep the REFUSED table as documentation of *why*, not as the enforcement.
Then § 12's writer row needs its complement: a grant not in the read set is refused **even when it
is in no refused list**, asserted over the live `register_tools()` handler names so the test tracks
the surface as it grows.

---

### 3. Seam 3 puts the new name in the weakest position in the prompt, and § 10 forbids changing the closed list that contradicts it
*(§ 6.5 seam 3; § 10 "Modified")*

[`config/agents/coordinator.md:84-85`](config/agents/coordinator.md) reads:

> **Valid `"agent"` values** — copy these strings exactly, character for character:
> `"Mental Wellbeing"` · … · `"Pattern Miner"`

That is a **closed** list in the cached system prompt. Seam 3 appends `## Additional specialists`
to `_load_coordinator_context()`'s return, which lands in `[Pre-loaded context]` at the *end of
the user turn* ([`core/orchestrator.py:6011`](core/orchestrator.py), [`:6231`](core/orchestrator.py)
— verified, the plan is right that the cache is undisturbed). § 10 then states "**no change** to
the valid-name list".

So the Coordinator — `models/gemini-3.5-flash-lite`
([`config/modules/routing_cloud.yaml:39`](config/modules/routing_cloud.yaml)) — holds a system
prompt saying `home_care` is not a valid value, and a context block saying it is. The repo already
records that this model cannot reliably copy the *existing* list: `_AGENT_NAME_MAP`'s own comment
at [`core/orchestrator.py:5516`](core/orchestrator.py) is *"Flash-Lite sometimes shortens
multi-word names."*

**Cost.** Run 1 fails to route, and the failure is indistinguishable from an ordinary
`ROUTING_MISS` — the exact signal class this vertical exists to consume, now generated by the
vertical itself.

**Trade-off and recommendation.** The plan chose context-injection to protect the Vertex prefix
cache. That buys a one-time re-cache per landing and pays for it with a permanent authority
inversion in the prompt. Recommend inverting: seam 3 rewrites the `coordinator.md` valid-name
paragraph at **prompt-assembly** time (still not editing the tracked file), so the closed list the
model reads is the complete one. If the cache cost is judged real, the minimum fallback is that
`coordinator.md`'s list stops claiming to be exhaustive and points at the context block — a
one-line tracked edit § 10 currently rules out.

---

### 4. The "same checks" diff cannot pass as specified, so the test that proves it will be loosened on first run
*(§ 6.8 run order vs § 12 "Same checks" row)*

§ 12: *"diff the name sets with `:overlay` stripped — **Must be identical**."* § 6.8's own order
is: `check_agent_tools.py` → `qa_sweep.sh` (the 10 + build-registration) → the three `--overlay`
passes → the capability's tests → `test_action_provenance.py`.

`scripts/qa_sweep.sh` runs exactly ten named checks — `agent-tools`, `confirm-executors`,
`personas`, `rule-overlap`, `project-log`, `py-compile`, `backlog-ids`, `dev-markers`,
`claude-md-claims`, `deploy-lock`. **`check_knowledge_domains.py` is not one of them**; it is a
standalone script. Neither is `tests/test_action_provenance.py`, which exists but no check invokes.

So after stripping `:overlay`, verify's set still holds `knowledge-domains`, the capability's own
tests and `action-provenance` — three names the sweep does not have. The assertion fails on day
one, gets relaxed to a superset check, and stops proving the thing § 12 says it proves.

**Recommendation.** Split the claim: an **equality** assertion over the checks verify claims to
share with the sweep (the 11), and a separate declared list of checks verify adds. Equality over a
declared subset still cannot drift; equality over the whole invocation never could.

---

### 5. The name-collision rule is stated two ways, and the narrower one admits the exact half-wired agent § 4 cites as its evidence
*(§ 4 registration matrix)*

Schema comment: `must NOT exist in either tracked routing file`. Prose two paragraphs later:
*"`name` must not shadow a tracked agent — tracked wins in every seam, so a collision would land a
record nothing ever loads."*

Those are different predicates, and the gap between them is populated. Agent files with **no entry
in either routing file**: `time_director` and `goals_interview_reference`. A record named
`time_director` passes the stated check, and then:

- seam 1 — `load_agent("time_director")` finds the **tracked** file and never reaches the overlay;
- seam 2 — there is no tracked routing entry to lose to, so the **overlay's** `allowed_tools` and
  model are merged in.

Result: tracked instruction prose driven by overlay tools and an overlay model — which is
precisely the `time_director` half-wiring § 4 offers as its live evidence that a checklist does not
hold. The prose rule is the correct one; the field comment is what an implementer will build.

**Recommendation.** The check is `name ∉ (agents in routing.yaml ∪ routing_cloud.yaml ∪
config/agents/*.md stems)`, and `check_build_registration.py` re-asserts it over all three.

---

### 6. `resolve_persona()` raises — it does not return "no persona"
*(§ 6, the paragraph justifying the overlay's location)*

> "the four seams resolve the persona exactly the way every tool does, `resolve_persona()` from
> thread scope, so a request with no persona in scope gets no overlay — fail-closed identity,
> unchanged."

[`core/persona.py:183-187`](core/persona.py) raises `PersonaError` when nothing resolves. Neither
of the two seams that need it takes a persona argument: `load_agent(name)`
([`core/orchestrator.py:681`](core/orchestrator.py)) and `_load_routing()`
([`core/router.py:56`](core/router.py)). So the sentence describes a third behaviour that exists
nowhere — either the seam catches `PersonaError` (new leniency in the Red-tier routing path, and
*not* "unchanged": [`core/orchestrator.py:649`](core/orchestrator.py) re-raises it deliberately),
or it propagates and `resolve_model()` starts raising where it does not today —
[`tests/test_a4_complexity_threading.py:107-108`](tests/test_a4_complexity_threading.py) calls
`resolve_model()` with no persona bound.

**Recommendation.** State it as the decision it is: `load_overlay()` catches `PersonaError` and
returns `{}`, and § 12's overlay-seams row keeps its "no persona in scope → no overlay" assertion
but adds that `resolve_model()` for a tracked agent still succeeds with none bound.

---

### 7. § 14 prices the factory and not the product
*(§ 14 "Run")*

The Run paragraph covers `build_tick`'s idle cost (zero tokens on an empty queue), the overlay's
kilobytes per job, and Build's index at ~1.5 KB per question. It does not price **the capabilities
Build ships**: each landed `kind: agent` capability is a specialist dispatched on every matching
turn, forever, at that turn's model price — and § 2 makes capability proliferation the explicit
goal ("it degrades well before 'hundreds'"), with the theme tier existing because the count is
expected to grow.

Under CLAUDE.md § Costs, Run is *"what the shipped thing costs per day, forever, once nobody is
looking"*, and the shipped thing here is the capability, not the builder.

**Recommendation.** One line per landed capability in the ledger — expected dispatches/day ×
its declared `latency_budget_ms` tier — and a stated figure at which the tier stops being "Later"
in § 16 and becomes due. `execution_mode` and `latency_budget_ms` are already required fields, so
the data exists; nothing meters it.

---

## Verification notes (below the bar for ranking)

1. **§ 10's index backup claim is wrong and harmless.** `data/personas/{p}/build/index/` is listed
   as "backed up by the existing tar", but [`scripts/metatron-backup.sh:78`](scripts/metatron-backup.sh)
   carries `--exclude='*.faiss'` with the reason stated inline (*"rebuildable from the journals we
   do take, and large"*). § 14 already says Build's index "is rebuilt from the job artifacts if
   lost", so the consequence is nil — but § 10 should not claim the backup.
2. **"The seven `get_*` feeds leave the machine" is six** — the read set names `get_weather`,
   `get_environmental_snapshot`, `get_tfl_status`, `get_flight_status`, `get_travel_time`,
   `get_regional_transit_info`. The seventh outbound read is `find_places`, which is not a `get_*`
   and does not fit the justification given ("no identifier beyond a city, line or flight number")
   — it takes a free-text query. Either name it in the sentence or state its own reason.
3. **Seam 4's `domain_agent_map()` cache is process-global.** [`tools/wisdom.py:353`](tools/wisdom.py)
   caches on one `(mtime, dict)` tuple for the whole process. Merging persona-scoped overlay names
   into it leaks one persona's capability names into another's domain map in the server. The cache
   key needs the persona.

## Confirmed against the tree (no finding)

- § 11's run 1 evidence: both 2026-09-08 Inbox filings exist at `08:53` and `08:54`; the machine
  log carries 09-11, 09-14 and 09-15 entries, and the 09-11 one does the arithmetic itself from
  *"Last watered Aug 4, 2026"*. Run 3's 2026-09-12 `08:53` policy filing exists.
- `logistics.md:41` lists weekly plant watering as an obligation type; `get_weather` returns
  `days_since_rain` ([`tools/ambient.py:232`](tools/ambient.py)) and is granted to `logistics`
  ([`config/modules/routing.yaml:175`](config/modules/routing.yaml)); the `home` wisdom domain
  exists ([`tools/wisdom.py:63`](tools/wisdom.py)).
- Every line number cited by § 6.5's seam table is correct: `load_agent` 681, `_load_routing` 56,
  `_load_coordinator_context` 641, `_AGENT_NAME_MAP` 5503, `_UNAVAILABLE_CONSEQUENCE` 5399,
  `_ALWAYS_CONFIDENTIAL` 1391, `domain_agent_map()` 358.
- § 6.2(b)/(c) hold mechanically: `.gitignore:148` carries `data/personas/*/`, and `deploy.sh`
  runs a plain `git pull origin main` at `:152` with **no** `git clean` or `git reset --hard`, so a
  gitignored overlay genuinely survives a deploy. § 12's Landing row is a sound test of that.
- `check_knowledge_domains.py`'s roster check runs map → routing, not routing → map, so § 10's
  "No change: `knowledge_domains.yaml`" is correct for the four tracked Build agents.
