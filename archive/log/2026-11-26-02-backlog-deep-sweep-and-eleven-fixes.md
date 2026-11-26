### 2026-11-26, second (`/backlog deep`: every item read against the VM and the tree; eleven Green/Amber fixes built, Fable-reviewed and merged) — `46fe856` … `0cb89db` — **committed, NOT deployed** (needs `./deploy.sh`: `core/`, `tools/`, `config/`)

**Incoming state:** the 11-25 handoff named this as the next step ("`/backlog deep`, then the 10-30 attack prompt"). The count stood at 35 inbox · 6 now · 44 later, 50 items against a ceiling of 45, with 15 items past their due date.

**How it ran.**
- One read-only SSH round-trip per question, covering the journal, traces and data files, read on the VM.
- Three read-only Sonnet verify workers: 54k, 67k and 68k tokens (189k against a ~250k estimate).
- Mike ruled "proceed as rec, Green/Amber only, nothing needing his manual check, Fable where questionable".
- Three Sonnet build workers, one per worktree via `new_worktree.sh`: 82–110k each, including resumes.
- A Fable 5.2 review of the merged range: 126k against ~175k. It found 7 defects.
- One Sonnet fix worker: 87k.
- Another chat was live in the main tree throughout (Places phase 3). All builds stayed in worktrees. Its uncommitted `[DB-1029-06]` edit was preserved, and its archive commit `a98fa10` took only its own hunks.

**The headline finding was not on the list.** 181 of 228 phone pings since 10-29 fell back to the textless "You have a message" (`UnknownHostException` on the phone's fetch). It is filed as `[DB-1126-01]` and ranked Now 1 by Mike. It needs an APK change, so it was not built today.

**Built.** Each item lists its user-visible effect first, then the cause:
1. **Registering a device for notifications failed while an ownerless pre-11-23 subscription remained.** `core/push.py:112` indexed `s['persona']`. The isolation test still asserted the old "legacy is Mike's" rule, which `388a91c` had reversed; it now asserts the opposite and passes 29/29 (`46fe856`).
2. **The goal talk's `note_expectation` was unclassified**, so the action record could misreport (`595ec01`).
3. **Scheduled sessions filed "this session was scheduled" as routing misses**, about 25 of 56 since 10-29. That count is what Now #3's 11-05 re-measure asked for: the class did not go away when the day plan took over check-ins. The guard is in `write_quality_event` and is precision-tuned (`5ee2da2`, `a13aea2`).
4. **Calendar events Metatron created could not carry a place at all.** `write_calendar_event` had no `location` parameter, so a named place could only go in the title. That is the real cause of "… and user at …". The fix adds the parameter, refuses person-shaped uses of "user" in titles and placeholder uids, and adds a `logistics.md` line (`902bf1b`, `c193243`, `3b692f9`, `299aa4b`).
5. **Forwarded mail now keeps who it was first sent to.** It is display only, kept out of `bulk_signals`, and carried to the queue specialists read; the extractor is told what the field means (`3eb96e3`, `3c59c60`, `0cb89db`).
6. **"I'm free today" for an older date vanished.** The override was pruned in the same write that recorded it. F8 had begun failing around 11-08 on the real clock (`521d864`).
7. **The weekly review missed aliases and blocked ordinary text on organisation-like names.** It now reuses `lookup_guard`'s readers (`571bee9`).
8. **First interviews never showed the "said but not kept" note, for anyone, since 11-21.** YAML read the bare `goals_interviewer: on` as `True`, so `mode()` returned off; on the VM it read `{'goals_interviewer': True}`. The value is now quoted, and `mode()` maps booleans (`2dab715`). No other bare on/off exists in `config/modules` or `config/templates`. Capture setup can no longer fail an interview turn (`5fbb1a0`). **Run cost:** one extractor call per interview turn, as designed on 11-21. It had been $0 only because the feature was off.

**Fable's 7 findings, all fixed in `wt/fable-fixes`:**
- The routing guard dropped real misses naming Logistics, Recreation and other unlisted agents.
- CRLF mail let a sender plant "originally sent to" addresses.
- The forwarding trail reached only the classifier, unlabelled.
- Alias delivery was read as a forward.
- The title rule refused "end-user training" and "User acceptance testing".
- A damaged capture file could fail an interview turn.
- A lone CR broke the iCalendar line format.

**Believed wrong, corrected:**
- Now #4's "calendar puts the place in the title" was read as a model-instruction fault. It was a missing tool parameter.
- Capture's live check 2 was read as "Iva's turns weren't eligible". The feature was off.
- The worker's first capture test passed because it never parsed the real YAML.
- F8 was "a day-plan bug since `fda9d80`". It was a pruning bug that a fixed simulated clock exposed.

**Rejected:**
- Moving " at <Place>" from a title into `location` in code, as the 10-30 attack prompt proposed. "Dinner at 7" would misfire, and the missing parameter was the cause.
- Two edits Mike had approved in principle: restoring the expired cardiac line and deleting the redundant six-hourly inbox job. Both are Denied-tier VM edits, and his ruling was Green/Amber only. They are in the walkthrough `[DB-1126-04]`.

**Backlog after:**
- 0 inbox · 6 now · 46 later, 52 items against a ceiling of 45. The walkthrough `[DB-1126-04]` closes eight.
- Six closed with VM evidence: `[DB-1026-01]`, `[DB-1029-16]`, `[DB-1029-17]`, `[DB-1029-01]`, `[DB-0808-09]`, `[DB-1029-04]`.
- Five merges.
- The ranking work's eight checks became `[DB-1126-06]` (by ~12-01); the instructions-to-code follow-ups became `[DB-1126-07]`.
- Evidence is in `archive/backlog_closed_2026-11.md`.

