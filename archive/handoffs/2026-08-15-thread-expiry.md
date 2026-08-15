# Handoff — open-thread expiry [DB-0814-02]

**Shipped:** `tools/context_tracker.py` — `open_threads` auto-drop 7 days after their `added`
date, archived (never deleted) to `expired_open_threads`, capped at 50, never returned by
`read_context_tracker()`. Test suite `tests/test_open_thread_expiry.py`, 19/19 passing.
`tests/test_clinical_threads.py` re-run clean (17/17) — no regression. Did not touch
`core/orchestrator.py` at any point.

**Two commits, the first one wrong:**
- `f4d18ca` — first version. Grace fired whenever a thread's text was present in `open_threads`
  that turn. **Corrected same day, before this reached the coordinator's review** — that
  condition is true of every live thread on every write, because the Synthesizer re-emits the
  full `open_threads` list every turn via the inline `[CONTEXT]` block (not the Diarist, not
  once per session). Against the actual "post-travel recovery" incident, that version would have
  granted grace on every one of the two weeks' worth of writes and never expired anything. Tests
  passed because the suite modelled "resent" but never modelled "resent, but nobody actually
  meant it" — the coordinator caught this, I hadn't.
- `37b0b03` — corrected version, what's live now. Grace requires one of two signals, neither of
  which is "presence in incoming":
  1. **The user's own turn engages the thread** (`user_text`, new optional parameter on
     `write_context_tracker`, defaults to `None` — no existing caller is affected). Matched by
     content-word overlap, not substring (`_user_engages_thread`, threshold
     `_USER_ENGAGEMENT_OVERLAP = 0.34`, a named constant) — substring match is too brittle
     against speech-to-text, which is most of this user's input.
  2. **The thread's wording materially changed.** No new code — `_merge_open_threads`'s existing
     exact-text carry-forward already treats reworded text as a brand-new thread stamped today;
     the only thing this rework had to get right was archiving the *old* wording correctly if it
     had already crossed the cutoff. Documented in the module comment rather than assumed.

**A third thing had to be fixed to make the correction actually hold, not asked for in the
brief but load-bearing:** removing the "presence = grace" rule exposed a same-write
resurrection hole. A thread archived on a given write would immediately re-enter `open_threads`
on that *same* write, because `_merge_open_threads` saw its text with no match in the
now-shrunk `still_eligible` list and treated it as brand-new. On a caller that resends identical
text every turn (the actual caller, per the correction above), that reproduces the incident one
write later, forever, flipping archived/revived every other write — I hit this as a test
failure before I could report anything. Fixed by filtering `open_threads` against the full
archive (prior + newly expired) before merging; a match is dropped unless a grace signal applies
to it too. Documented at the filter site and in the top comment as an "extension beyond the
literal brief."

**Kept unchanged, as instructed:** 7-day cutoff, the archive-not-delete pattern, the 50 cap, the
never-expire-undated-legacy rule, read-time migration, `chmod 600`, unchanged model-facing shape.

**Gameability — both grace signals, stated plainly:**
1. **Word-overlap grace can false-positive on short, generic thread text.** A thread like "call
   the dentist" (content words: `call`, `dentist`) against an unrelated user turn "call mom
   later" shares `call` — 1 of 2 words, overlap 0.5, clears the 0.34 threshold, grants grace on
   a thread the user never actually meant. Short entries with common verbs are the weak case;
   the 0.34 threshold was picked by reasoning, not measured against real transcripts, and this
   is the most likely place it needs retuning once real Diarist/Synthesizer output exists.
2. **Material-change grace is trivially triggerable by a one-character diff.** Since it rides on
   exact-text non-match, ANY change to a thread's wording — even whitespace or punctuation —
   counts as "materially changed" and resets the clock, because nothing here distinguishes a
   genuine rework from a caller that varies its phrasing slightly on every turn. This is
   arguably the more serious gap: it is close to a second copy of the exact bug this rework
   exists to close, just requiring one changed character per turn instead of zero. I did not
   build a similarity check for this because the brief explicitly frames it as "no new matching
   code, the merge step already does this" — but that framing assumes genuine rewording is rare
   and cosmetic rewording by the caller is not a pattern that occurs. **If this project's actual
   Synthesizer output style flags this as a live pattern, revisit with a similarity-based
   near-duplicate check on top of the exact-text merge, comparable to `core/rule_classes.py`'s
   `similarity()`.**

**What's proven by test vs. not:** the suite (`tests/test_open_thread_expiry.py`) exercises the
mechanism directly via back-dated `added` fields and controlled writes — cutoff, archive, both
grace signals (positive and negative), the resurrection fix, legacy migration, and the cap are
all verified, including the exact incident shape (20 identical resends, unrelated user turns,
confirmed to expire and stay archived rather than oscillate). **Not tested:** real
Diarist/Synthesizer output — whether `user_text` as wired by the coordinator's orchestrator
plumbing is genuinely the user's raw turn (it must be; if anything upstream ever includes
system-authored text in that parameter, both grace signals degrade toward the original bug this
whole rework exists to fix) and how often real conversation triggers signal 1's false positives
described above.

**Not deployed.** `tools/` deploys to the VM; this worktree change has not been pushed/deployed.

**Transcript archive:** `archive_chats.py` found no JSONL for this worktree path both times —
this worker runs as an in-process subagent dispatch, not a standalone Claude Code session, so no
`-Users-md-homefolder-Desktop-metatron-wt-thread-expiry` project transcript exists to export.

**For SESSION.md:** `[DB-0814-02]`'s remaining half is built and tested in this worktree,
current at `37b0b03` (supersedes `f4d18ca`, which had a real bug — not just an unpolished first
pass). Not merged, not deployed. Report evidence to the coordinator for the merge/closure
decision; not claimed closed here.
