### 2026-08-18, sixth (the clearing sweep — the backlog halves, and three items rested on a count the file itself calls invalid) — `ROADMAP.md`, `DEV_BACKLOG.md`, `scripts/check_claude_md_claims.py`, `tests/run_a4_safety.py`, **not deployed**

**Measured in items removed, which was the point.** `DEV_BACKLOG.md`: **41 open → 28**, `## Inbox`
**6 → 0**, `## Machine log` **91 → 49**, file **1,294 → 682 lines**. No item ended the pass
unchanged. Every closure carries its evidence in `archive/backlog_closed_2026-08.md` § Closed
2026-08-18 — the clearing sweep, and nothing about a closed item stayed in the backlog.

**The finding that mattered more than any single closure, because it invalidated three items at
once.** A `×N` in `## Machine log` written before 2026-08-15 is a **similarity chain length, not a
repeat count** — `SIMILARITY_THRESHOLD`'s comment in `scripts/sync_dev_backlog.py` documents sixteen
unrelated corrections reported under one signature. All three entries triaged into `## Inbox` on
2026-08-15 as *"Mike-originated, ×3/×4, clears the machine bar"* were **single events**, and every
one was also **older than the code that fixed it**: the email-transcription guard shipped 08-08
against 08-02 evidence; the due-date sort that plausibly dropped the Thursday deadline was fixed
`fd273bf` on 08-18 against 08-11 evidence. **Both halves of the promotion argument were false and
neither was checked.** The caveat existed, in this same file, one section above the items. Third
time an item's own description has argued persuasively for the wrong decision.

**Two items were fixed rather than filed.**

- **`[DB-0810-14]` — the A4 clinical hard-fails could not be run with a response language set, and
  the instruction on the item would have raised a false safety alarm.** The pipeline suite proves a
  flag reached the user by matching `"crisis"`, `"hotline"`, `"medication"`; translation renders
  exactly those, so a **correct** response reported FAIL. `tests/run_a4_safety.py` now runs the two
  checks on different text — `token_forbid` on the delivered string (a leaked all-caps token is a
  leak in any language), `surface_expect_any` on the pre-translation English, captured by wrapping
  `_translate_for_user()`, the single call site. `tests/test_a4_translated_substance.py`, 10 checks.
  **The equivalence is what makes it safe to leave on permanently:** for an untranslated persona —
  every persona today — the two texts are identical.
- **`[DB-0810-06]` — the backlog is now bounded by items, not lines.** Mike named the replacement
  metric on 08-15: *"a backlog's ceiling should probably be tied to the number of items in it, not
  its line count."* `DEV_BACKLOG.md` leaves `CEILINGS` for a new `ITEM_CEILINGS` at 45 open items,
  counted by importing `sync_dev_backlog.count_items` rather than reimplementing it. Verified by
  fault injection. **The reasoning is the durable half:** item count bounds the workload; line count
  pressures a session to cut *evidence* out of entries, and the evidence is what the file's own
  standing rule ("no item is acted on from its own description") depends on. `SESSION.md`'s line
  ceiling is untouched — the argument is specific to a backlog.

**`[DB-0815-04]` closed by running it, not by waiting for a live turn.** `translate("Good morning.
Your meeting is at three.", "bg", "Bulgarian")` against the real backend returns `'Добро утро.
Срещата ви е в три.'` — candidate (a) fixed and proven at the source. (c) was eliminated 08-15 by
Mike's grep; (b), the client, has no transliteration call anywhere in `static/index.html` or
`core/server.py` and declares `charset=UTF-8`. No candidate remains, so it closed on evidence rather
than joining the pile waiting on one ordinary use. **That pile is the whole diagnosis of why this
file grew** — 11 of 43 items were finished, deployed code with no exit.

**Options rejected.**

- **Building the offline shell (`[DB-0803-05]`) as a do-it-now.** A service-worker `fetch` handler
  is small, but a wrong SW cache is sticky and hard to recover, it needs a deploy and an APK
  rebuild, and **`./deploy.sh` is Denied** — so confirmation could not happen in the session making
  the fix, which is the rule this session was run under. Left unbuilt with the shape recorded
  (a dedicated `offline.html` plus a navigation-failure fallback, never caching `/`).
- **Fixing `[DB-0808-14]` (statin vs. anti-psychotic) as "small and specific".** It is small; it is
  not cheap to confirm. Clinical tiering has named hard-fail criteria (§0 clause 8), so the change
  owes an A4 re-run. Recorded on the item so the next session does not mistake size for cost.
- **Trimming `ROADMAP.md` Track D (`[DB-0809-14]`).** Real cost — 22 KB of a 71 KB file loaded every
  session — but it is a **development-process defect, not Metatron work**, and `## Inbox`'s own
  standing caution says those do not belong in this file. Removed rather than kept as a chore.
  Same reasoning retired `[DB-0805-05]`.
- **Keeping `[DB-0806-03]` and `[DB-0806-04]` as backlog items.** Both are one-word decisions for
  Mike, not engineering work. They moved to the decision batch; whichever he says yes to gets
  re-filed as a build item.

**Believed true earlier, wrong.** The 2026-08-18 inventory called the Thursday-deadline entry *"the
single most repeated complaint in the log"* at ×4 and treated all three machine entries as clearing
their bar. Under the corrected reading of `×N` each is one event. The inventory is otherwise sound
and its central finding — finished work has no exit — is what this session acted on.

**`[DB-0818-03]` left the backlog and `ROADMAP.md` § A9a gained `2026-10-01` as a review date.** A
condition with no clock is exactly how eleven items accumulated; a backlog entry that only points at
a roadmap section is a duplicate of it. The date is what makes the removal safe.

**`## Machine log` swept properly for the first time.** Its standing rule — *an entry is deleted
once its signal is promoted or its cause is fixed* — had been written but never executed, so
addressed signatures kept their `⚠` and kept leading the session-start line. 42 entries deleted,
each with a pointer recorded in the file. `.dev_backlog_seen` is what makes it safe; regenerating
the section from the VM source would resurrect all of them.

**Not done, and stated plainly:** the interactive half of the session's brief. Ten items are
finished code waiting on one ordinary use each and cannot be closed without Mike driving the app;
that list is with him, not re-parked in the backlog. Nothing deployed — `core/orchestrator.py` and
`tools/crm.py` still owe one, as does `f4cc812`.

