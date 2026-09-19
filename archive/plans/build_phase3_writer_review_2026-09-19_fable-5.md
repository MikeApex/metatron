# Build phase 3 — second-model review of the writer, the seams and verify

**Reviewer:** Fable 5.1, 2026-09-19. **Scope:** the uncommitted phase-3 diff against
`archive/plans/build_vertical_plan_2026-09-18.md` § 6 and § 12. **Method:** every claim confirmed
by running tests, not by reading — the three shipped suites plus two rounds of adversarial probe
scripts that reuse `tests/test_build_writer.py`'s real-git fixture repo. No file outside this one
was edited by the reviewer. Probe scripts lived in the session scratchpad and are not in the
repo; each probe's construction is described beside its result so it can be rebuilt.

Two passes are recorded here: the **first review** (six defects, ranked) and the **re-check**
after Mike's session fixed all six on the working tree (six closed, three new defects, two
observations).

---

## Part 1 — First review (before fixes)

### Claims confirmed by running

Shipped suites as they stood: `test_build_writer.py` 27/27, `test_build_verify.py` 15/15,
`test_build_overlay.py` 19/19. Probe round 1 on top:

| Claim | Probe | Result |
|---|---|---|
| Every hardcoded deny path refused at all three ceilings | 21 paths including nested `.env.local`, `a/b/my-key.json`, `core/build/new.py`, `.git/hooks/pre-commit`, a second persona's overlay — each at `generated_registration`, `amber`, `red` | held |
| Every `git ls-files` path refused at all ceilings | fixture's 7 tracked paths × 3 ceilings | held |
| A grant outside the read set refused even when no refused list names it | all 46 live `register_tools()` names outside `ALLOWED_GRANTS` × 3 ceilings | held |
| `revert()` restores byte-identical by sha256 | a non-UTF-8 prior file overwritten then reverted | held |
| § 12 "same checks" equality over the declared shared subset | `SHARED_CHECKS` == live sweep set (11), `ADDED_CHECKS` exact, no orphans | held |

### Defects, ranked

1. **Build could rewrite any file on disk, tracked or deny-listed, through the undo path.**
   `_kind_of()` classed anything under the job directory as an "artifact", so `apply()` accepted
   an edit whose path was the job's own `undo.jsonl`. `revert()` then replayed that journal with
   no path rule, no ceiling and no allow-root check. Probe: one `apply()` writing a forged journal
   entry, one `revert()` — the fixture's `config/constitution.md` and a file outside the
   repository were both overwritten. Reverts fire on refusal, failed check, abandon and the
   writer's own exception handler, so this was reachable without any caller asking for it.

2. **A generated capability could capture every dispatch to a tracked specialist.** The schema
   checked the record `name` against three tracked sets but never `display_name`. A record named
   `home_care` displaying `Logistics` landed; seam 3 then added `logistics → home_care` to the
   Coordinator name map by `setdefault`, and the literal map had no `logistics` key to win. Same
   for `Relationships`, `Finance`, `Diarist` — all in the closed list at `coordinator.md:85`.

3. **An agent file naming a refused tool landed if the name was not in backticks.** Both writer
   scans and the tracked `check_agent_tools.py` regex required a backtick. "When done, call
   send_email with the summary" landed, and the `--overlay` verify pass exited 0 on it.

4. **Record fields that go into prompts were not gated for narration.** `directory_entry` and
   `display_name` are spliced into the Coordinator system prompt; `unavailable_consequence`
   reaches the Synthesizer notice. `constitution.py` scanned only the agent text. A record
   carrying `gemini-3.8-flash`, `send_email` and `routing.yaml` in those fields landed and reached
   both prompts. A `display_name` containing a quote and backtick injected a second entry,
   `"Send Email"`, into the closed valid-name list.

5. **A record could land routed to a provider that does not serve its model.** `provider: openai`
   with `model_ref: mental_wellbeing` landed; seam 2 resolved it to openai serving a Gemini id.

6. **The `find_places` ⇒ `risks[]` condition in § 6.3 was unenforced.** `apply()` accepted `plan`
   and never read it; `find_places` landed with `plan=None` and with `risks: []`.

---

## Part 2 — Re-check after the fixes (working tree, 2026-09-19)

### Nothing that held was reopened

- Shipped suites now: writer **33/33** (+6 `REVIEW` checks), verify **17/17** (+2), overlay
  **21/21** (+2), schemas 31/31, jobs 20/20, manifest 16/16, probe 38/38, spine 12/12,
  `test_action_provenance.py` 10/10, `test_a4_complexity_threading.py` PASS,
  `qa_sweep.sh` **11/11**.
- Probe round 1 re-run unchanged against the fixed tree: **14/14 hold** — the five
  first-pass claims and the nine defect probes (each now refused).

### The six, each closed or open

| # | Defect | Status | Probe output |
|---|---|---|---|
| 1 | Undo journal writable; `revert()` unguarded | **Closed** | `undo.jsonl` and `undo.reverted.*.jsonl` edits → `REFUSED … the undo journal is written only by the writer itself`; a forged entry naming `config/constitution.md` → `revert skipped … refused by deny list`, file untouched; an entry outside the repo → skipped |
| 2 | `display_name` shadows a tracked agent | **Closed** | Against the **real** tree's names: `Logistics`, `Relationships`, `Finance`, `Diarist`, `Synthesizer`, `Coordinator`, `Time`, `Goals`, `LOGISTICS`, `Research Agent` all refused with a `display_name` defect; seam 3 independently skips such a record (`REVIEW 2b`) |
| 3 | Bare tool names bypass the grant gate | **Closed** | `call send_email now`, `(send_email)`, `send_email.`, `use write_calendar_event\nfor it` → `REFUSED … outside its own grant`. Match is case-sensitive whole-word against the live registry; `SEND_EMAIL` passes, which is correct — no registered name is upper-case and the dispatcher would not match it either |
| 4 | Prompt-bound record fields ungated | **Closed as filed, with a gap — see N3** | `directory_entry` with `gemini-3.8-flash` and `unavailable_consequence` with `routing.yaml` → refused, each defect naming its field; `display_name` with quote/backtick → refused by charset `^[A-Za-z0-9 &]+$` |
| 5 | Record could pin its own provider | **Closed** | `routing.cloud.provider: openai` → `REFUSED … provider is set`; seam 2 discards a provider found on a hand-placed record and takes both halves from the tracked agent (`REVIEW 5c`); a `model_ref` present in only one routing file → refused |
| 6 | `find_places` condition unenforced | **Closed** | With agent text naming only `find_places`: `plan=None` → refused, `risks: []` → refused, `risks: ["sends a composed query off-machine"]` (does not name it) → refused, `risks: ["find_places sends …"]` → `OK` |

### New defects the fixes introduced or left beside them, ranked

**N1. A second generated capability can capture another generated capability's dispatch.**
Display-name uniqueness is checked against tracked names and the Coordinator's closed list, not
against other overlay records or their names. Two probes, both landed:

- `home_care` displaying `Home Care`, then `garden` also displaying `Home Care` → both land;
  `coordinator_additions()` returns `['Home Care', 'Home Care']` (the splice dedups against the
  tracked listing only, so the closed list carries the string twice) and the name map holds one
  winner, `home care → home_care`, chosen by sort order.
- `garden` displaying `Garden Care`, then `weeding` displaying `Garden` → lands; the name map now
  says `garden → weeding`, where the generic fallback would have resolved `Garden` to the
  `garden` capability itself.

Not tracked shadowing — defect 2 stays closed — but the same mechanism one layer down, and it
arrives on the second landed capability, which is exactly the § 11 bootstrap sequence.

**N2. A look-alike of a tracked display name lands.** `Mental  Wellbeing` (two spaces) passes
the charset, normalises to `mental__wellbeing` which is not tracked, and lowercases to a string
not in the reserved set. It splices into the closed list beside `"Mental Wellbeing"`. It cannot
capture tracked dispatch (the exact string still maps to the tracked agent), but the Coordinator
is a model that its own map comment records cannot reliably copy the existing list, and it is now
being shown two entries one space apart. Low, and cheap to close in the same place defect 2 was.

**N3. The record-field narration gate matches the static confidential list, not the live tool
registry.** `_check_record_fields()` tests each field against `_ALWAYS_CONFIDENTIAL`, which
carries 37 of the 78 registered tool names. So `unavailable_consequence: "their send_email
digest"`, `"their read_email triage"` and `"their merge_contacts pass"` all land, while the
agent-file grant gate (defect 3's fix) would refuse the same tokens. The § 12 constitution row's
"a confidential identifier in `unavailable_consequence` must fail" holds for `routing.yaml` and
fails for a tool name, which is the canonical confidential identifier. Defect 4's closure was
confirmed on the paths the new test exercises; this is the path it does not.

**N4. (macOS only — not reachable on the VM.)** The journal name rule is a case-sensitive string
test and the development filesystem is case-insensitive. An edit to `Undo.jsonl` passes
`check_path()`, is the same inode as `undo.jsonl`, and replaces the journal. `revert()` now
refuses any entry outside the allow-roots, so a forged journal can no longer reach a tracked or
denied path — but it can restore arbitrary bytes into another capability's overlay agent file
**without the content gates**: the probe left `overlay/agents/other_cap.md` reading
`# names send_email`. On ext4 on the VM `Undo.jsonl` is a different file and this does not
arise. Recorded because tests run on the Mac and a fixture-green result would not show it.

### Observations, not defects

- **`revert()` with `git` unavailable** does what the correction says: nothing restored,
  journal kept, summary carries `N SKIPPED (failed the path rules)`, and a later revert once
  `git` is back completes the undo. The summary still opens with `reverted —`, which a phase-4
  caller matching on that prefix would misread; the `SKIPPED` clause is the signal to key on.
- **`scripts/check_build_registration.py`'s overlay pass** calls the validator without
  `reserved_display` or `model_ref_names`, so the sweep's independent re-assertion (its
  assertion 4) covers the three-set `name` rule and not the two rules added for defects 2 and
  5. The writer refuses both at write time; the second line does not yet look for them.
- **`scripts/check_agent_tools.py` still requires backticks**, by the plan's stated decision (the
  evidence gate is what keeps 34 field names out of the tracked report). The `--overlay` verify
  pass therefore inherits the gap defect 3 closed in the writer; the writer's refusal is the
  only line for bare names, and a hand-placed overlay file is not re-checked for them.

---

## Part 3 — Re-check of N1–N4 and observation 2 (working tree, 2026-09-19, later)

### Nothing that held was reopened

- Probe round 1 re-run unchanged: **14/14 hold.** Probe round 2 re-run unchanged: **13/13
  hold** — including the four probes that were defects when round 2 was written (N1, N2b, N3,
  N5) and the macOS journal alias (N1 of round 2, N4 of Part 2).
- Shipped suites now: writer **36/36** (+3 `REVIEW N*`), verify **19/19** (+2), overlay
  **22/22** (+1), schemas 31/31, jobs 20/20, manifest 16/16, probe 38/38, spine 12/12,
  action provenance 10/10, a4 threading PASS, `qa_sweep.sh` **11/11**.

### The five fixes, each closed or open

| # | Item | Status | Probe output |
|---|---|---|---|
| N1 | Two records sharing a display name | **Closed** | `garden` displaying `Home Care` after `home_care` → `REFUSED … duplicates the display name of overlay capability 'home_care'`; `home  care` (whitespace/case variant) → refused; two records displaying `Plant Care` in **one** `apply()` → refused; re-landing `home_care` with its own display → `OK` (a record does not collide with its own old copy) |
| N1b | Display name equal to another record's name | **Closed** | `weeding` displaying `Garden` beside a `garden` capability → `REFUSED … resolves to overlay capability 'garden' — it would capture that capability's dispatch` |
| N2 | Double-spaced look-alike of a tracked name | **Closed** | `Mental  Wellbeing`, `mental wellbeing`, `Mental & Wellbeing`, `Mental and Wellbeing`, padded `  Mental Wellbeing  `, `Time  Director`, and the routing-only `Cloud Only Agent` all refused with a `display_name` defect |
| N3 | Live-registry tool name in `unavailable_consequence` | **Closed** | `send_email`, `read_email`, `merge_contacts`, `get_pollen_forecast` (off the static list) and the **granted** `get_weather` each refused naming the field; `fetch_url` in `directory_entry` refused; `"their weather-aware watering reminders"` lands |
| N4 | `Undo.jsonl` on this filesystem | **Closed** | `Undo.jsonl`, `UNDO.JSONL`, `undo.JSONL`, `Undo.reverted.x.jsonl` all refused; a subsequent `revert()` left the neighbouring `other_cap.md` intact. Also refused on a fresh job before any journal exists, so the name rule holds alone where the inode rule cannot |
| Obs 2 | Hand-placed records under `check_build_registration.py --overlay` alone | **Closed** | Six hand-placed records in a temp overlay against the real tree: `Logistics` display, `provider: openai`, `model_ref: time_director` (in neither routing file), two records displaying `Plant Care`, and `Mental  Wellbeing` — each named in a finding, exit 1; a clean seventh record produced no finding |

### New, ranked

**P3-1. Seam 3 does not collapse whitespace before resolving a display name.** `accepted_displays()`
calls `_resolves_to_tracked(display)` on the raw string, so a **hand-placed** record displaying
`Mental  Wellbeing` (two spaces) normalises to `mental__wellbeing`, misses the tracked set, and
is surfaced into the closed valid-name list and the name map. Confirmed against the real tree's
agent names: the double-space form is surfaced; the `&`, `and` and upper-case forms are
correctly excluded. Reach is narrow — the writer refuses the record (N2 above) and the sweep's
overlay pass flags it (observation 2 above), so it requires bypassing both lines — but it is the
one place where the seam and the schema no longer agree, which is the property the v3.2
corrections set out to hold. Low.

### Nothing else new

Round-three hunts that came back clean: two records in one `apply()` with the same display;
a record re-landing over its own earlier copy; the journal name rule on a job whose journal
does not yet exist; a granted tool name in a prompt-bound field; the sweep on a clean overlay
record beside six broken ones.
