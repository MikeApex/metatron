### 2026-08-27 (the 08-10 sink-gap session closes — and finds its subject broken again) — `DEV_BACKLOG.md`, `archive/plans/code_dominant_rebuild_notes.md`, **not deployed**

**A 17-day-old chat was reviewed against current state and closed as part of Mike's chat
clear-out.** The session (2026-08-10) had diagnosed the quality-event sink gap — 158 events
silently discarded by `sync_dev_backlog.py`'s allowlist — but shipped nothing: it stopped at a
scope question Mike never answered. Nearly everything its Part 1 would have built landed since
via other sessions (`048e937` registry + uid-pair signature, `214a547` null-correction filter),
so the diagnosis was not re-filed.

**One live finding survived the review: `ROUTING_MISS` is being silently discarded again, and
the guard built to prevent that is what certifies it.** The 08-15 fix classed the type into
`KNOWN_DEAD_TYPES` on the strength of a code grep — but the emitter is the Synthesizer calling
`write_quality_event` at runtime, instructed in 9 places in `synthesizer.md`, invisible to any
grep over Python. Verified against the live VM: 5 events since 08-11, latest 08-26, one of them
the runtime's own report of the `[DB-0826-01]` merge-undo misroute. Filed as **`[DB-0827-05]`**
in `## Now` (position 9) at Mike's instruction; fix is a two-line move plus rewording the
deadness criterion to include agent instruction files.

**The parked "Part 2" (code-vs-LLM-judgment) went to the rebuild notebook, not the backlog.**
Mike's call: with the code-dominant rebuild conversation now open, Part 2's fix-Metatron items
are stale but its reasoning feeds the inversion. Appended as round three of
`archive/plans/code_dominant_rebuild_notes.md`, four points: prompt-resident judgment breeds
artifact tensions (the Synthesizer fact-check round-trip vs PoLP joins round two's caching
example as a class); prose call graphs defeat static analysis — evidenced three times on one
pipeline, `[DB-0827-05]` being the third; the zero-token `function:` audit jobs are the
inversion already running at the edges; identity resolution belongs in code but thresholds stay
judgment gates (wisdom.py's own 3/5 wrong-partner finding).

**Wrong earlier, corrected here:** the resumed session's own 08-10 plan said clearing
`.calendar_dedup_seen` was required to surface the 7 calendar findings — verified false before
any fix shipped (the sync's own ledger had never seen them; clearing would have double-reported).
And the 08-13 deadness check was wrong in method, not diligence: "grepped the whole codebase"
is the wrong layer when the caller is an instruction file.

Options rejected: fixing `[DB-0827-05]` inline this session (Mike is mid clear-out, working the
backlog through `/backlog`, so it enters the ranked list instead); filing Part 2's 2A bug fixes
(wisdom.py SentenceTransformer reload, Diarist archive dedup) as backlog items — they correct
the v1 runtime the rebuild conversation may replace, and nothing a user notices today.

No commits before this close-out's own; nothing deployed.
