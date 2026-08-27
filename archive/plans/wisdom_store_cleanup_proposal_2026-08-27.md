# Wisdom store cleanup proposal — `[DB-0818-06]`

*Proposal only — nothing in `data/personas/**` is touched by this file. Every DELETE below means
"propose Mike removes this," per the archive-on-merge principle: nothing is deleted by this
proposal itself.*

## Source used, and why

**The live wisdom store was not read directly.** `data/personas/mike/` does not exist in this
worktree's local `data/personas/` tree at all (only test personas — `arthur_brooks`,
`cal_newport`, `danny_park`, `maya_torres`, `oliver_burkeman`, `ryan_holiday`, `sarah_chen` — are
present locally; none is Mike's). An attempt to read `~/multi-model-mcp/data/personas/mike/wisdom/wisdom.json`
from `metatron-vm` over `gcloud compute ssh --tunnel-through-iap` (read-only `cat`) was blocked by
the permission classifier before it ran, correctly — Mike's persona data is Denied-tier and this
task did not carry an explicit lift of that gate.

**What was used instead:** [`scripts/migrate_wisdom_schema.py`](../../scripts/migrate_wisdom_schema.py)
`KEY_MAP`, committed `a35acfa` (2026-08-15, "Every live wisdom entry is assigned by hand, and the
key stops being committable"). That commit's message states it was produced by **reading all 59
entries of Mike's actual live store by hand** and assigning each one a domain, provenance, and — for
entries that don't belong in wisdom at all — a one-line note naming why and where it belongs
instead. This is a *better* source than a raw JSON dump would have been: it already carries the
human judgment this proposal exists to extend, not just the raw text.

**Entry count: 24 of 59** carry a non-empty note — confirmed by parsing `KEY_MAP` directly
(`24 of 59 total`, verified 2026-08-27). This matches `[DB-0818-06]`'s count exactly, so `KEY_MAP`'s
24 flagged entries **are** the 24 non-fact entries the backlog item names.

**Caveat on freshness:** `KEY_MAP` reflects the store as read on 2026-08-15. Per `[DB-0818-06]`'s
own text, "the writers are half-fixed, the store is not" — `write_wisdom`'s schema and
`synthesizer.md` were tightened after that date to stop new intention-shaped entries, but nothing
has removed the 24 already on file, and Mike's ordinary use since 08-15 may have added or removed
individual entries this proposal cannot see. Treat this as a dated proposal against a dated read,
not a live audit.

**What this proposal does not have:** the entries' actual stored `value` text. `KEY_MAP` carries
key names, the classification, and a reviewer's note — not the verbatim string. Where the note
itself quotes or closely paraphrases the value (e.g. `oatmeal_formula`'s literal placeholder
text), that is reproduced below; everywhere else, the "text" column is my tight summary of what
the note says the entry is, explicitly marked as inferred rather than verbatim.

## Classification method

The store's purpose is durable factual knowledge about Mike that stays true past today. Five
non-fact classes, per the task brief, all of which are represented in the 24:

| Class | What it looks like here |
|---|---|
| **Preference** | How Mike wants to be dealt with — belongs in the persona file (read every prompt), not a fact store (read only on lookup) |
| **Instruction-to-self / to-the-tool** | A standing directive, not an observation about Mike |
| **Transient state / dated observation** | True of one day, not standing knowledge — belongs in the log or journal |
| **Duplicate** | The same fact stored twice, in wisdom or across wisdom and another store |
| **Misfiled non-fact** | Not a fact about Mike at all — a tool defect report, a content-free placeholder |

**Every one of the 24 verdicts below is DELETE**, not because the *content* is worthless, but
because each was independently judged (2026-08-15) as not belonging in the fact store at all —
that is the definition of the 24, not an outcome I'm imposing. REWRITE would apply only where
content should stay *in wisdom*, reworded; none of the 24 fit that — each has a better home
elsewhere, or no home at all. "DELETE" therefore always carries a destination or reason, not a
bare removal.

## Summary count

| Verdict | Count | Sub-class |
|---|---|---|
| DELETE — relocate to persona file (`write_persona`) | 11 | interaction/behavioral preference |
| DELETE — relocate to obligation tracker (`open_obligation`) | 3 | recurring obligation (incl. one that's also a duplicate) |
| DELETE — merge into surviving duplicate (`merge_wisdom_entries`) | 2 | near-duplicate, consolidate |
| DELETE — misfiled tool defect, not a user fact | 3 | belongs in `DEV_BACKLOG.md`, two already tracked there |
| DELETE — dated/transient, not standing knowledge | 2 | belongs in log/journal or the profile event trail |
| DELETE — content-free or unfilled placeholder | 2 | records nothing usable |
| DELETE — duplicates a real config field | 1 | `profile.yaml`'s `output_language` |
| **Total** | **24** | |

(Counts sum to 24; `manny_swim_schedule` is counted once, under "merge," though its note also
flags it as an obligation — see its row.)

## Per-entry table

| Key | Text (summarised from the reviewer's note; verbatim only where the note quotes it) | Verdict | Destination / rewrite |
|---|---|---|---|
| `sleep_debt_pattern_june_2026` | A dated observation about a sleep-debt pattern in June 2026 | DELETE | Not standing knowledge — belongs in the log/journal, not the fact store |
| `personal_contact_update_2026_08_02` | Records that a piece of contact data changed on 2026-08-02 | DELETE | An event record, not standing knowledge — the contact data itself belongs in the profile (`[DB-0815-05]`) |
| `voice_transcription_issues` | A report of the tool mistranscribing speech | DELETE | Not knowledge about Mike — a tool defect; belongs in `DEV_BACKLOG.md` |
| `conversational_preferences` | How Mike wants conversations to be conducted | DELETE | Interaction preference — `write_persona`, not the fact store |
| `user_preference_interaction_fluidity` | A preference about how fluidly/rigidly interactions should proceed | DELETE | Interaction preference — `write_persona` |
| `monthly_financial_reminder` | A recurring monthly financial reminder | DELETE | A recurring obligation, not a fact — `open_obligation`/`list_obligations` per `logistics.md:189` |
| `communication_style_preference` | How Mike prefers to be communicated with | DELETE | Interaction preference — `write_persona` |
| `rowan_payroll_schedule` | Rowan's payroll runs monthly, 1st–5th | DELETE | A recurring obligation — `open_obligation` |
| `service_style_anticipation` | A preference for how proactively the tool should anticipate needs | DELETE | Interaction preference — `write_persona` |
| `avoid_travel_assumptions` | An instruction not to assume things about Mike's travel | DELETE | An instruction to the tool, not a fact about Mike — `write_persona` |
| `manny_swim_schedule` | Manny's swim class recurs on a fixed schedule | DELETE (merge + relocate) | Duplicate of `manny_swim_class`; also a recurring calendar constraint, not a fact — consolidate the pair into one `open_obligation`/calendar entry, not a wisdom fact |
| `manny_swim_class` | Manny's swim class (same fact as above, second copy) | DELETE (merge) | Near-duplicate of `manny_swim_schedule` — `merge_wisdom_entries`, archive-on-merge |
| `crm_update_friction` | A description of the CRM tool failing to update silently | DELETE | The friction described is a tool defect, not a fact about Mike — belongs in `DEV_BACKLOG.md` |
| `post_travel_recovery` | Mike's post-travel energy recovery pattern (second copy) | DELETE (merge) | Near-duplicate of `post_travel_energy_recovery` (not in this list — presumed to stay as the surviving fact) — `merge_wisdom_entries` |
| `reduced_prompting_preference` | A preference for fewer prompts/check-ins | DELETE | Interaction preference — `write_persona` |
| `communication_preferences` | General communication preferences | DELETE | Interaction preference — `write_persona`; the note also flags this as overlapping `communication_style_preference` and `admin_comms_reduction`, i.e. a third copy of adjacent content |
| `14_point_checkin_consolidation` | A preference to consolidate check-ins into fewer touchpoints | DELETE | Interaction preference — `write_persona` |
| `system_framing_preference` | A preference for how the system frames things to Mike | DELETE | Interaction preference — `write_persona` |
| `calendar_accountability_reconciliation` | A preference for how calendar accountability should be reconciled | DELETE | Interaction preference — `write_persona` |
| `admin_comms_reduction` | A preference to reduce administrative communications | DELETE | Interaction preference — `write_persona`; overlaps `communication_preferences` |
| `grocery_check_in_cycle` | Recorded only that a correction happened during a grocery check-in, not what the correction was | DELETE | Content-free — no usable information survives; outright removal, no relocation |
| `oatmeal_formula` | Verbatim, per the reviewer's note: value is literally `"[User needs to specify their formula details here]"` | DELETE | Unfilled placeholder; the real composition already lives in `profile.yaml` `health_notes` |
| `bulgarian_speech_to_text_issues` | A report of Bulgarian speech-to-text failing | DELETE | Tool defect, not a fact about Mike — already tracked as `[DB-0815-02]`/`[DB-0815-04]` |
| `language_preference` | Mike's output-language preference | DELETE | Duplicates `profile.yaml`'s real `output_language` field (`[DB-0810-15]`, shipped 2026-08-15) — the profile is authoritative; this copy can drift from it |

## Entries I was unsure how to classify

**The "eight interaction preferences" count in `[DB-0818-06]`'s own text does not match what I
count here.** The backlog item names three explicitly (`communication_style_preference`,
`reduced_prompting_preference`, `avoid_travel_assumptions`) "and five more" — eight total. Reading
every note in `KEY_MAP` that says "an interaction preference... belongs in the persona file," I
find **eleven**: the three named plus `conversational_preferences`,
`user_preference_interaction_fluidity`, `service_style_anticipation`, `communication_preferences`,
`14_point_checkin_consolidation`, `system_framing_preference`,
`calendar_accountability_reconciliation`, `admin_comms_reduction`. I cannot tell from the note text
alone whether Mike's "eight" collapsed some of these as effectively-the-same preference before
counting (the note on `communication_preferences` itself says it overlaps two others), or whether
three of my eleven are not really interaction preferences in his read. I have listed all eleven as
DELETE→persona-file since each individually reads that way from its note, but **the persona-file
transplant step should treat these eleven as a single review, not eleven independent writes** —
several likely collapse into one persona-file line once actually reworded, which is a judgment call
for whoever does that transplant, not for this proposal.

I am also not fully confident that `manny_swim_schedule` is correctly counted once rather than
twice (as both "duplicate" and "obligation") in the summary table — I have kept it in the "merge"
row only, noting its dual nature in the text column, but a stricter accounting might want it
counted under both.
