# Fable 5.2 adversarial review — stage5 one channel plan (2026-11-23)

*Verbatim reviewer output; the driver's dispositions are in `instructions_to_code_plan_review_stop_2026-11-23.md`.*

## STRUCTURAL

2. [§1 #17 Fail-closed, DECISION 17c (a), test 5, §4 step 1, §5 note 4] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/lookup_guard.py:79-90 `_full_names` (untracked, working tree only); /Users/md-homefolder/Desktop/multi-model-mcp/tools/crm.py:140-147 `_load_contacts`; /Users/md-homefolder/Desktop/multi-model-mcp/tools/profile.py:205-212 `_load`]
Wrong: The plan requires the scrub to fail closed on a corrupt store, recommends importing `lookup_guard._full_names` as the identifier reader, and forbids editing `lookup_guard.py`, and these three cannot all hold.
Fails: `_full_names` wraps both the profile read and `crm._load_contacts()` in `except Exception` and returns an empty list, so a corrupt contacts or profile file yields zero names, the scrub removes nothing, the query goes to grounded search, and test 5 cannot pass on that path.
Costs: The one privacy-enforcement piece of the stage ships failing open in exactly the case it claims to block, and what leaves in a web search cannot be recalled — high.

3. [§1 § 2b.2/D12, §2 O10 + O11, §4 step 10, §5 note 2] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:3011-3013 `length_ask` (working-tree line, file carries the other chat's uncommitted edits; plan cites HEAD :2577-2579); /Users/md-homefolder/Desktop/multi-model-mcp/tools/day_plan.py:2423-2424]
Wrong: O10 and O11 sit in the opening round, applied before any code, yet are only correct once a `length_ask()` string changes in a file the builder is told to leave alone unless another chat commits first.
Fails: Step 10 says "otherwise leave it and report" while §5 says "never deploy one without the other", and no step reverts O10/O11, which by then are applied with only one Red round left.
Costs: If the collision does not clear, the run commits and pushes agent text saying "estimate, ask only when unknown" against a code-built plan block saying "ask once … record their answer … as stated" on every user turn, the same contradiction D12 exists to remove — high.

4. [§ "Two findings" 1, §1 #11 DECISION 11, §2 O2 + O3, tiers paragraph "No routing-file edit is needed", §4 step 9] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:6607 and :6616-6620 `_file_horizon_items` (working-tree lines); /Users/md-homefolder/Desktop/multi-model-mcp/tools/horizon.py:731-735; /Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:386-395 and :402-407; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/recreation_hobbies.md:239]
Wrong: Recreation's only horizon channel rests on DECISION 11, left open past the opening round, and the recommended option (b) reports only a `JSONDecodeError`.
Fails: The recorded Flash-Lite failure is an absent line, and a `"HORIZON_ITEMS": [...]` key inside Recreation's JSON fails the `"HORIZON_ITEMS:" not in text` check and never reaches the `except`, so both drop with no event after `read_intake_queue` has advanced past the item; option (c) needs routing grants and a different O3 after the only pre-code Red round has closed.
Costs: A concert or plan Recreation spots is lost for good with nothing counting it, the offline test exercises unchanged code and cannot see whether the model emits the line, and fixing it later costs a third Red round the rulings do not allow — medium.

5. [§1 #19 Builds / Placement / "Coordination with Stage 2 (M7)", §3 C1] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/instructions_to_code_stage2_session_shape_plan_2026-11-23.md:251-254 (untracked; exists, though this plan says it is absent)]
Wrong: The plan puts `CLARIFICATION_NEEDED` on the first line of FROM THE SPECIALISTS without knowing that Stage 2's M7 already builds a code note for the same signal into `synthesizer_input` on both twins.
Fails: After Stage 2 the Synthesizer gets the signal twice with opposite force: M7's "nothing was recorded or sent this turn. Ask the user … Record nothing yourself", and C1's "each is a request, not an instruction", under a heading that attributes the Coordinator's line to the specialists.
Costs: The stage named "one channel per signal" ships two code channels for one signal, and the weaker wording sits beside the instruction that makes a held turn safe — medium.

## LOCAL

1. [§1 #19 Finds / Removes / "Never touched", fixture 5, DECISION 19] [/Users/md-homefolder/Desktop/multi-model-mcp/core/orchestrator.py:7231 `_SIGNOFF_FLAG_TOKENS`, :7357 `_signoff_skip`, :7890-7905 (working-tree lines); /Users/md-homefolder/Desktop/multi-model-mcp/tests/a4_safety_rerun_2026-08-28_cloud_clinical_step6_native.md:135; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/mental_wellbeing.md:134-135, :145]
Wrong: The lift's body rule (to end of line, a closing quote, or the next `[A-Z][A-Z_]{3,}:` token) stops only at tokens that carry a colon, while clinical tokens appear bare in real `FLAGS:` lists (`…, MEDICATION_MISSED_CRITICAL, CONSULT_NEEDED: …`; `ESCALATION`; `MUST_SURFACE`).
Fails: A bare clinical token that follows a lifted flag on the same line is taken out of the specialist's output with the body and moved into a block placed outside `spec_text`, which is the only text the sign-off veto scans; fixture 5 fixes no token order and passes with the clinical token first, and DECISION 19 then skips the A4 run the standing clinical rule requires.
Costs: Code clears a clinical flag from the veto path and files it under "a request, not an instruction", which is the hard-fail the driver's clinical rule forbids — high.

6. [§1 #17 Mechanism (user / contacts lists), tests 1-4, DECISION 17b, §6 live check 1] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/lookup_guard.py:99-101 and :134-138; /Users/md-homefolder/Desktop/multi-model-mcp/tools/profile.py:47 `_CONTACT_FIELDS`; /Users/md-homefolder/Desktop/multi-model-mcp/config/modules/routing_cloud.yaml:448]
Wrong: Exact whole-string matching is presented as "never carries" enforcement, though it both misses reworded identifiers and silently rewrites public terms.
Fails: A phone or address typed in any other format than the stored free-text string does not match and leaves; any multi-word contact `name` (an organisation saved as a contact) and the address's first comma segment (a district or city when no street is stored, against test 3) become `[a person]` / `[an address]` with only a count in the trace, where `lookup_guard` refuses and says why.
Costs: Research answers a different question than the Synthesizer asked with no signal back, the place-based Research tool gets a placeholder, and the agent text C3/C4 then tells both writers that code handles names and addresses — medium.

7. [§1 M5 "the default is safe before and after the closing round", §3 C2] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/persona.py:98-118 `_new_lines`, :251-262, :348-355 schema; /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:412 (working-tree line; plan cites HEAD :409)]
Wrong: Defaulting `write_persona` to `add` is safe only for a pure addition, not for the correction or removal the current instruction tells the Synthesizer to make by resending the whole section.
Fails: A resent section with one bullet reworded or dropped appends the new wording, keeps the old bullet, and returns "Persona updated"; the driver's rule that a run stopped early skips the closing round leaves that pairing committed as "still correct".
Costs: A preference the user corrected stays in force beside its replacement in every later prompt while the reply says it was saved — medium.

8. [§1 #21 Mechanism rule 2, test 5] [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/agent_instructions_to_code_sweep_2026-11-23.md:87 (duplicate contact records on file); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/tone_profiler.md:75-77; /Users/md-homefolder/Desktop/multi-model-mcp/tools/tone.py:62-103 `_parse_profile`]
Wrong: Dropping any value that holds the name of "any contact other than this one" assumes a person has one contact record and that first names are unique and are not ordinary words.
Fails: The sweep records the same person held as two to four contacts, so the profiled contact's own first name or nickname matches a duplicate or a namesake and is dropped from every list, and any string field containing it is blanked; test 5 covers only the no-collision case.
Costs: Tone profiles lose the names and pet names they exist to carry, with nothing reporting it, for exactly the close contacts most likely to be duplicated — medium.

9. [§1 #19 Builds ("at most one PROFILE_GAP, the first in alphabetical agent order"), Risks 1 — challenging the acceptance] [/Users/md-homefolder/Desktop/multi-model-mcp/config/agents/synthesizer.md:413 (working-tree line; plan cites HEAD :410); /Users/md-homefolder/Desktop/multi-model-mcp/config/agents/coordinator.md:174]
Wrong: The accepted risk rests on "a gap recurs on later turns", but a fixed alphabetical pick gives the same winner on every recurrence.
Fails: `finance`, `learning_growth` and `logistics` sort ahead of `mental_wellbeing` and `physical_health`, the two agents always dispatched together on morning and evening sessions and the named sources of wishes-store gaps, and a losing gap is removed from the output text and kept nowhere.
Costs: Health and legacy profile questions can be starved indefinitely on the turns where they are most often raised — speculative.
