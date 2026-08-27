# Handoff — psychiatric meds still rank the same as statins [DB-0808-14]

**Worker 3, parallel attack run, 2026-08-27. Scope done, build stopped at the Red-tier line —
Red-tier work is not delegated to a subagent per `CLAUDE.md` § Change tiers.**

---

## 1. Scope verdict: the premise is current, not stale

Verified against the running code, not the backlog description alone.

- `config/agents/physical_health.md:126-131` defines exactly **three** medication criticality
  levels — `required` / `as_needed` / `optional`. `required` covers "insulin, anticoagulants,
  antiepileptics, **psychiatric medications**, blood pressure meds" as one undifferentiated group.
  A missed statin (blood pressure/cardiac) and a missed SSRI (abrupt-discontinuation risk) are
  both `required` and nothing downstream distinguishes them.
- `tools/context_tracker.py:320-322`:
  ```python
  def _thread_tier(flag: str) -> int:
      """2 for any CLINICAL_CONCERN, 1 otherwise. Derived, never model-supplied — see above."""
      return 2 if "CLINICAL_CONCERN" in (flag or "").upper() else 1
  ```
  takes only the bare flag string. Every `MEDICATION_MISSED_CRITICAL` thread — statin or
  antipsychotic — gets tier 1: resolvable by a reassuring reply, no different from a missed
  vitamin flag once it clears the `required` bar.
- The module's own comment block (`tools/context_tracker.py:41-43`) records that the tier design
  was **motivated by this exact distinction** — *"the distinction asked for was 'missed heart
  medication' versus 'missed anti-psychotics' — one the user can resolve in conversation, one
  that must not close on a reassuring reply"* — and then built only two tiers: bare `MUST_SURFACE`
  (tier 1) vs. `CLINICAL_CONCERN` (tier 2). The distinction was named as the goal and never wired
  in. **Confirmed live defect, not stale.**

## 2. Why this stops at the Red-tier line

The fix needs two changes, and only one of them is buildable here:

1. **Schema/instruction change — `config/agents/physical_health.md` (Red tier).** Nothing in the
   stored `medication_profile` currently records *why* a medication is `required` — no drug class,
   no discontinuation-risk marker. `_thread_tier()` cannot honor "classification comes from the
   stored profile, never inference" (physical_health.md:106) without a field to read. This is a
   config/agents edit — Red tier, not delegated to a subagent; the judgement (what the field is
   called, which drug classes qualify, how the agent is instructed to identify them) **is** the
   design work here, per `CLAUDE.md` § Change tiers.
2. **Consuming logic — `tools/context_tracker.py` (Green, buildable once #1 exists).**

I did not touch `config/agents/physical_health.md`. Below is the concrete spec for whoever picks
this up, so #2 can follow immediately without re-deriving the design.

## 3. Proposed fix, fully specified

**physical_health.md — two edits:**

- **"Medication profile" section (~line 126-131):** add a fourth field to the `required`
  medications, e.g. `discontinuation_risk: true`, scoped explicitly to classes with abrupt-
  stop risk — psychiatric medications (SSRIs/SNRIs, antipsychotics, mood stabilizers,
  benzodiazepines), not the whole `required` bucket. Keep the instruction as narrow and
  enumerable as the existing `required`/`as_needed`/`optional` prose — this is exactly the kind
  of addition the file's token-budget note (SEQ 002 precedent) asks to keep short.
- **"Data written" JSON schema (~line 158-165):** add the same boolean to each
  `medications_logged` entry:
  ```json
  {
    "name": "medication name",
    "criticality": "required | as_needed | optional",
    "discontinuation_risk": false,
    "taken": true,
    "notes": "null"
  }
  ```
- **Flag-naming convention.** `_thread_tier()` only ever sees the bare flag string
  (`MEDICATION_MISSED_CRITICAL`), never which medication triggered it. The existing
  `CLINICAL_CONCERN: SUICIDAL_IDEATION` convention already carries a colon-suffixed detail —
  extend the same pattern: instruct physical_health to emit
  `MEDICATION_MISSED_CRITICAL: <medication name>` when raising the flag, matching the name used
  in the stored profile.

**tools/context_tracker.py — one function, once the field exists:**

- Extend `_thread_tier()` (or wrap it at the `write_context_tracker`/`_merge_clinical_threads`
  call sites, `tools/context_tracker.py:448` and `:479`) to:
  1. Parse the medication name out of a `MEDICATION_MISSED_CRITICAL: <name>` flag.
  2. Read `medication_profile` via `tools/agent_config.py`'s read path
     (`agent_name="physical_health"`, `key="medication_profile"`) — never the free-text `note`,
     which is model-authored and exactly what "never from the agent's judgment" forbids trusting.
  3. If the named medication's stored entry has `discontinuation_risk: true`, return tier 2
     (the same non-resolvable "watch" lifecycle already built for `CLINICAL_CONCERN` — no new
     lifecycle state needed, this reuses the existing mechanism per `_CLINICAL_PROTOCOL`).
  4. Fall back to tier 1 if the name can't be parsed, the profile can't be read, or the entry
     lacks the field — fail toward the current (safe, if under-differentiated) behavior, never
     toward inventing a risk classification.
- **Standalone test:** `tests/test_medication_tier.py` (new, once buildable) — feed
  `_thread_tier()`/`_merge_clinical_threads()` a fixture profile with one `discontinuation_risk:
  true` entry (e.g. sertraline) and one `required`-but-false entry (e.g. atorvastatin/statin),
  assert the flags for each resolve to tier 2 and tier 1 respectively, plus the three fallback
  cases in point 4.
- **A4 re-run owed on this change too**, per the backlog item's own note — clinical tiering has
  named hard-fail criteria (`ROADMAP.md` § 0 clause 8). The `PH-MED` scenario in
  `tests/run_a4_safety.py`'s `CLINICAL` suite uses a seeded lamotrigine fixture (`required`, not
  psychiatric-tagged today) — that fixture should gain a `discontinuation_risk` case once the
  field exists, or a new scenario should be added.

## 4. This run's A4 gate re-run (owed regardless of the above)

Ran `python3 tests/run_a4_safety.py --persona sarah_chen --provider gemini --suite clinical
--complexity quick` (Vertex Gemini path, cloud, Flash-Lite quick tier — matches the convention of
the prior `2026-08-18` report and how live traffic actually routes this domain).

**Result: PASS — 3/3 (MW-3 suicidal ideation, MW-7 mania signal, PH-MED missed critical
medication).** Report: [`tests/a4_safety_rerun_2026-08-27_gemini_clinical_quick.md`](../../tests/a4_safety_rerun_2026-08-27_gemini_clinical_quick.md).

No `watch`-state clinical thread was in play for this run (fresh fixture, no prior context) —
not applicable here, noted per the task brief only because it's a common misread.

## 5. Backlog items to close, and the evidence

**None.** `[DB-0808-14]` stays open — the defect is confirmed live and the fix is scoped in
full above, but the Red-tier half (the `physical_health.md` schema/instruction addition) was not
built in this run. Closing it now would misrepresent unbuilt work as done.

## 6. Must be carried by another owner

1. **The `physical_health.md` edit itself** (§3 above) — Red tier, needs Mike's review/approval
   in an interactive session, not a subagent.
2. **The `tools/context_tracker.py` change** (§3) — Green tier, buildable immediately once #1
   lands, with the standalone test described above.
3. **A follow-up A4 clinical re-run** once both land, extending the `PH-MED` scenario/fixture to
   exercise `discontinuation_risk: true` explicitly.
4. **VM deploy** — once `tools/context_tracker.py` changes, `core/` and `tools/` behavior on the
   VM needs `./deploy.sh` (Denied tier, Mike-run only) to pick it up; `config/agents/*.md` also
   needs to reach the VM's live persona config per `.claude/rules/personas.md` (the VM owns live
   persona config, not the Mac's committed copy).
