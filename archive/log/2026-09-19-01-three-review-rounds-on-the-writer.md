### 2026-09-19 (phase 3 reviewed three times — and each round's defect class was the last round's fix)

The § 14 second-model review of Build phase 3 ran in Fable 5 and came back in three parts. All
twelve findings confirmed and fixed: **six**, then **five**, then **one**. Suites now writer
36/36, overlay 23/23, verify 19/19 (was 27/19/15 at first submission), phase 1–2 unchanged at
117, `qa_sweep` 11/11. **Mike committed the whole phase as `12d7dd2`** — the working tree is
clean but the commit is **not yet pushed or deployed**; phases 1–6 still reach the VM as one
deploy.

**The finding worth keeping is the shape of the sequence, not any single defect.** Each round's
defect class is the previous round's fix, examined one level closer:

- **Round 1 (six) — prose never made mechanism.** Every one was a place where the plan stated a
  rule and the implementation honoured the prose exactly, so the gate existed, read correctly
  and did nothing. `revert()` replayed whatever the undo journal named, and the journal sits
  inside an allow-root — a write primitive with no path rules, bypassing the deny list, the
  tracked-path rule and the allow-roots at once. `display_name` was checked against nothing
  while `name` was checked against three sets. Both tool scans required backticks. Three record
  fields reach a prompt and none was scanned. `model_ref` governed the model while `setdefault`
  let the record's own `provider` always win. `find_places`'s "must list it in `risks[]`" was a
  sentence and nothing read it.
- **Round 2 (five) — mechanisms scoped to the probe that prompted them.** The round-1 fixes
  closed their reported cases exactly and stopped there. Display uniqueness covered tracked
  agents and not other overlay records, so the *second* landed capability could capture the
  first's dispatch — which is precisely § 11's bootstrap sequence. `Mental  Wellbeing` passed
  every check by having two spaces. The record-field gate read the static confidential list
  (37 of 78 tool names) while its sibling read the live registry. The journal rule was
  case-sensitive on a case-insensitive filesystem. And `check_build_registration.py` — the
  second line whose entire job is independent re-assertion — was looking for less than the
  writer.
- **Round 3 (one) — a mechanism improved in only one of its two homes.** The whitespace collapse
  added in round 2 went into the schema and not into the seam that exists to agree with the
  schema independently. Reach was narrow (the writer refuses the record; the sweep flags it) but
  it broke the one property the whole sequence was establishing. **Fixed as a shared import
  rather than a second collapse call: a rule duplicated in two places holds until one copy is
  improved.**

**Decisions and their reasons.**
- **`scripts/check_agent_tools.py` left alone, deliberately**, though it shares the backtick gap
  the writer closed. On a tracked file its evidence gate is what keeps 34 field names out of the
  report; that trade is right there and wrong only in the writer. Recorded in the plan so the
  next session does not "fix" it.
- **`_AGENT_NAME_MAP` hoisted to module scope** because both the validator and the seam had to
  read it. That surfaced a second, latent fault nobody reported: the seam-3 merge was mutating
  the map in place, so one persona's display names would have persisted into the next request on
  the same process. Callers take a copy now.
- **`revert()` fails closed when `git` cannot be asked** — nothing restored, journal kept,
  summary carries `N SKIPPED`. Leaving an overlay half-applied is recoverable; writing an
  unchecked path is not. **The summary still opens with `reverted —`**, which a phase-4 caller
  matching on that prefix would misread; the `SKIPPED` clause is the signal to key on, and that
  is now in the plan rather than only in the reviewer's notes.
- **A test of mine was wrong and the corrected version is stronger.** The P3-1 test first
  asserted the display string was absent from the assembled prompt — wrong for
  `  Mental Wellbeing  `, which strips to a string already in the closed list as the *tracked*
  entry. It now asserts the prompt is byte-identical to the no-overlay baseline. Re-run with the
  fix reverted to confirm it still failed before.
- **Beyond the literal instruction, and stated as such:** observation 2 asked for
  `reserved_display` and `model_ref_names`; `peer_displays` was passed too, since the script
  already reads every record and omitting it would have left the sweep unable to see the
  duplicate-display rule — the one rule it would otherwise still check less of than the writer.

**Believed true earlier and wrong:** the first submission's report said phase 3 was complete with
"two gates that were inert" already corrected. Three review rounds later that reads as an
underestimate of what a single-model pass catches on a security surface — twelve findings, none
of which the 61 passing checks had detected, because each test was written by the same reasoning
that wrote the defect.

**Outside the plan, at Mike's request:** `~/.claude/show_usage.py` hardcoded
`CONTEXT_WINDOW = 200_000` and reported **95%** on a session running `opus[1m]` that had already
carried 236,769 tokens — past its own denominator while reading as "about to compact". It now
resolves the window from the configured model (the only place the `[1m]` suffix survives; the
transcript records a bare `claude-opus-5`), cross-checks against observed usage, gates the
promotion on model family so a mid-session `/model` switch cannot under-report, and prints the
denominator. Backup at `show_usage.py.bak-2026-09-18`.

**Plan is at v3.4** — three correction blockquotes in § 6 and `[v3.2]`/`[v3.3]`/`[v3.4]`
assertions on § 12's writer, overlay-seam and constitution rows.

**Deployed: NO. Pushed: not at time of writing** — `12d7dd2` was local-only; this close-out's
push carries it offsite. Commits: `12d7dd2` (Mike's, the whole phase) and this close-out.
