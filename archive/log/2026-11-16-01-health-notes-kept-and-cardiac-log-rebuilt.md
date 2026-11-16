### 2026-11-16 (health notes stop overwriting each other; Mike's cardiac log rebuilt into a file Metatron can read) — `23f1e59` + this close-out; VM data/persona edits run by Mike — **deployed by Mike in-session; VM at `23f1e59`**

**Outgoing handoff carried:** unchanged from § 2026-11-11; this session continued § 2026-11-13.

**Did the 11-13 routing exception work?** Partly. All four voice entries after it
(11-13 19:09, 11-15 15:08 and 16:48, 11-16 13:48) were acknowledged with no symptom question.
Physical Health was still called on 2 of 4, with the cardiac line the only health content.
**Mike: don't pursue routing further; it's temporary.**

**The finding that mattered: the log was losing entries.** `health.symptoms` and
`health.medical_notes` are one free-text scalar per day, and `_deep_merge` replaces a scalar, so
each write replaced the last. Of six events only two survived with times. The 11:42 entry was
overwritten by the 20:01 evening close and the 15:08 one by a 17:10 write; 19:09 was reworded
to "worn continuously"; 16:48 lost its time. The separate file Mike asked for on 11-13 (seq
004) never existed. The conversation records were complete and timestamped throughout, which
made a rebuild possible.

**Built (`23f1e59`):**
- `tools/logger.py`: every non-empty health note is also appended to a `health_notes` list in
  the day log, with write time and spoken time. It follows the pattern used for `intentions`
  (08-28), and the scalar fields are unchanged, so no reader changes. An exact repeat of a
  field's last entry is skipped.
- **Spoken time.** Mike asked whether recording time reaches the VM. It does, but only as text:
  the client prefixes `[<time>]` when a snippet is sent late or batched (`stampIfLate`,
  `composeBatch`), and until now only the model saw it.
  - `tools/turn_context.spoken_stamps()` lifts the stamps into the turn.
  - Both pipeline entry points bind them.
  - The Diarist's fire-and-forget thread receives them via `adopt_spoken()`, deliberately not
    `adopt()`, because binding a turn there would change `new_trigger_since()` for the Diarist.
  - Stamps are kept as the client's raw locale text, never parsed.
- **Known limit:** a batched message gives each note all of that message's stamps.
- **Tests:** `tests/test_health_notes_feed.py`, 8/8 on Mac and VM. Related suites are clean
  apart from two failures that also fail on HEAD: `read_day_plan` is unclassified in
  `test_action_provenance`, and F8 fails in `test_day_plan_round2`.

**Rebuilt log (VM, run by Mike):**
- `data/personas/mike/health/cardiac_events_2026-11.md` (human copy) and
  `archive/cardiac_events.json` (readable through `read_archive`, which Physical Health is
  granted). Six entries, verified read back as `mike` through the tool.
- The temporary `profile.yaml` line now points routing at that archive for "show me the log".
- Both files are regenerated from the conversation records, not from the damaged day logs.

**Wrong earlier, corrected:**
1. The first deploy carried nothing, because I asked Mike to deploy before committing, and
   `deploy.sh` pulls from git. **Commit and push before asking for a deploy.**
2. The first rebuild missed 16:48, whose segment opened "Council tax is paid, cardiac monitor…",
   because the matcher required a segment to start with "cardiac monitor".
3. A pasted command containing `!` was rejected by zsh history expansion. Keep `!` out of
   commands handed to Mike.

**Rejected:** a dedicated health-event tool or an agent-file instruction (Red, and model-read).
The guarantee belongs in code, under the "privacy and records enforced in Python" rule.

**Open, in `[DB-1113-01]`:** re-run the rebuild on 11-18; first live check of `health_notes`
on the next entry; remove the profile line on 11-21.

