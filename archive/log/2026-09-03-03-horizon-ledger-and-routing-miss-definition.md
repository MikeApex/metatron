### 2026-09-03 (both Red proposals land — and the question that reshaped the second)

Session ⑥'s two staged proposals, approved by Mike in the same conversation and built
immediately after. Commit `a4a9364`. The second one changed shape between being written and
being built, and the reason is the durable part of this entry.

**Proposal 1 — `coordinator.md` gains a `ROUTING_MISS` definition.** Applied as written, beside
the `USER_CORRECTION` rule it mirrors. It says what the code guard structurally cannot: routing
that worked is not an event, and there is no slot here to fill. The guard shipped earlier the
same day refuses events that assert success; this closes the five that merely describe the
session without asserting anything. Cache-safe by direction — the file grew, so it moves away
from the 4,096-token Vertex floor rather than toward it.

**Proposal 2 — the question that found the hole.** The proposal recommended making
`HORIZON_ITEMS` delivery structural rather than attempting a third instruction. Mike asked:
*"How would the code know whether something is of interest?"*

The first-order answer is that it does not and should not. `logistics` makes that judgement,
with the mail and the calendar in front of it, and it stays there — code would only guarantee
the relay, which is exactly what `_file_wisdom_proposals` does for wisdom facts and what its
docstring already generalises: *structured relay in this pipeline means Python parses it.*
Measured across the three runs where specialist output survives in the traces (08-29, 08-30,
09-02), that judgement is sound: eight findings, zero junk. So there is a real signal worth
preserving and "code cannot judge interest" is not an objection to preserving it.

**The second-order answer is what the proposal had missed, and it nearly inverted the
recommendation.** Those same three runs:

    08-29 10:31   dental · Jimmy Carr · George School socials
    08-30 20:46   dental · Jimmy Carr
    09-02 11:37   Jimmy Carr · Death Cab · George School London

Jimmy Carr in all three, the dental appointment in two. **Guaranteeing delivery without a
record of what had already been said would have told Mike about the same comedy show every day
until 13 September** — `[DB-0822-06]`'s carried-state failure arriving through a brand-new
channel, and strictly worse than the silent drop it replaces, because a daily false alarm
trains him to ignore the channel entirely. The Synthesizer's dropping was doing double duty all
along: it was the fault *and* the noise filter. Removing the fault means supplying the filter
deliberately.

This killed the cheaper option that had been under consideration (an injected must-deliver
block on the `crm_sweep` shape, no ledger) — it would have been actively worse than the bug.

**What code can decide is identity, and only because the format changed.** Two findings are the
same finding when they share a date and a venue: a key comparison, not a semantic judgement,
deliberately so because `[DB-0827-07]` was closed to keep guessing of that kind out of this
codebase. Prose could not support it — the same show was written *"Jimmy Carr Performance:
September 13th at 9:30 PM at The London Palladium"* by one run and *"Jimmy Carr: Laughs Funny at
The London Palladium — Sunday, September 13, 2026 at 9:30 PM"* by another, with no title string
in common. So the Red edit turned out to be a **format** change rather than an instruction:
`logistics.md` now emits `HORIZON_ITEMS` as JSON with `date` and `venue` as fields. That is a
better use of a Red edit than the one proposed, because it moves a judgement out of prose
instead of adding another rule to be ignored.

**Corrected during the build, by the tests rather than by review:** the first key normalised the
venue to a string, and `"The London Palladium"` versus `"the london palladium, London"` did not
match — the trailing city qualifier broke the very case the design exists to handle. The key is
now a sorted token *set*, under which both are `{london, palladium}` while `{troxy, london}`
stays distinct from `{london}`. A design whose whole justification is a dedupe that works, with
a dedupe that did not.

**Two placement decisions, each of which silently costs a finding one of its two chances:**

1. **The offer is charged where the block is served, not once per turn from the close-out.** A
   finding is filed by `logistics` partway through a turn, long after that turn's context block
   was built — charging it from the close-out bills it for an offer the user never saw. The
   window collapses the two head-layer context loads of one exchange into a single charge.
2. **The block is built after the sign-off veto, never before.** On an "over and out" turn the
   Synthesizer never runs, so a block built earlier would burn a chance on a reply that was
   never produced.

Both are asserted in `tests/test_horizon_ledger.py` against the source, because neither is
visible in behaviour until a finding has already been lost.

**Same-turn delivery, deliberately.** The block is wired in twice: into the Synthesizer bundle
after the sign-off veto (so a finding is put to the user in the exchange that discovered it) and
into `load_recent_context()` (so an undelivered one gets its second chance next session). An
inbox-summarize job that reads the mail, finds a concert and says nothing until tomorrow would
have been the `[DB-0822-09]` complaint almost exactly.

**A contract in a Red file changed and was updated rather than left to drift.**
`logistics.md` said of horizon findings that *"whether the user hears about it is Synth's
call."* That is no longer true — *how and when* remain Synth's call, *whether* does not. The
line now says so. Discovering that the code contradicted a stated instruction and leaving the
instruction in place is how the two drift apart.

**Not confirmed.** Both items are time-gated to 2026-09-12. `[DB-0822-09]`'s close needs one
live interest-level email reaching Mike **and** not being repeated afterwards — the second
direction is the one the ledger exists for, so a confirm that only checks delivery would miss
the failure this build was most at risk of introducing.
