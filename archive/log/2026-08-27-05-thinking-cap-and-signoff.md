### 2026-08-27 (the thinking cap lands as insurance, "over and out" ends an exchange in code — and two deploys pulled nothing)

**The probe `[DB-0827-02]` asked for ran first, and it killed the item's economic premise.**
105 live Synthesizer replies off the VM (08-19 → 08-27, clean post-Option-A window): max
observed thinking **3,930 tokens with no tail above it** — p95 was 3,217. The whole cost
exposure measured **~$0.26/day**. So the "clip the expensive outliers" theory had no outliers
to clip, and Mike's decision followed the data: **cap at 4,096 as insurance, not economy** —
it clips nothing today and converts "no `thinking_config` anywhere in the codebase" into
"bounded at observed-max". A latency-motivated cap (1,024–1,536) was **rejected for now** — it
would touch 60–85% of replies, making it a quality experiment, not a config edit. Report:
`archive/plans/synthesizer_thinking_probe_2026-08-27.md`. Built: `_SYNTH_THINKING_BUDGET`,
Synthesizer only, both native paths, per-request (cannot touch the cache key);
`_note_thinking_cap_hit()` writes a `THINKING_CAP_HIT` quality event within 64 tokens of the
budget — Mike's addition, so a moved distribution announces itself. A4 pipeline gate PASS 3/3
with the cap live; item removed from the backlog with evidence in `backlog_closed_2026-08.md`.

**"Over and out" now ends an exchange without the Pro Synthesizer pass** — Mike's build order
after three sessions of discussion (the 2026-08-18 Synth-economics chat first raised it).
Detection is Python (`_is_signoff()`): Damerau ≤1 edit per word on the final three tokens,
never mid-message, never on a question — **routing it through Coordinator judgment was
rejected**: a Flash-Lite opinion adds two failure modes to a decision an exact match makes.
Coordinator and specialists still run (the work lands; only the reply is skipped); any
`MUST_SURFACE`/`CLINICAL_CONCERN`/`MEDICATION_MISSED_CRITICAL` in specialist output vetoes the
skip **in code**. Ack is a fixed phrase ("Received — talk to you later."), upgraded from `👍`
at Mike's call. `tests/test_signoff.py` (37 checks); verified live via a `danny_park` pipeline
run before commit. Damerau replaced plain Levenshtein mid-build because a transposition
("adn") is the most common real typo and plain distance prices it at 2.

**Wrong twice, and the second one cost Mike two deploys:** (1) the first live test failure was
blamed on punctuation (Mike's hypothesis, reasonable) — the actual cause was that **neither
the cap nor the sign-off had ever been committed**; both of Mike's deploys pulled nothing, and
the "closed" status on `[DB-0827-02]` was true of the build and gates but not of the VM. The
work sat uncommitted because the session asked "one commit or two?" and treated "Deployed" as
an answer. Committed as `a620f10`, pushed; **deployed by Mike and passed live.** (2) Early in
the session, the 28% `synthesizer.md` trim was still being weighed partly on cost — the
caching fix had already cut that case 4× and the audit's own addendum said so; adherence was
always the real argument.

**The compliance-ceiling experiment is deferred into the rebuild conversation** (Mike:
more valuable against the rebuilt agents than fixing v1 compliance) — design, price (~$15–20),
the weakest-model rule, and the sign-off as a worked example of the inversion are round four
of `archive/plans/code_dominant_rebuild_notes.md`. The specialist-digest-in-history and
ack-tier-routing ideas from the 08-18 chat were re-priced and stay dead (adherence findings
argue against growing the prompt; `[DB-0820-05]` points the routing question the other way).

Commits: `a620f10` — **deployed and live-tested by Mike**. That deploy also carried `1b040bd`
and `c6b21b0` (the ask-vs-assert commits that had been owing one — deploy pulls main), so
**nothing owes a deploy** at close.
