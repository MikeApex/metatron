# Session ⑦ — the capstone remainder: provenance, B4 slice, clinical escalation (launch prompt)

Model: Fable 5. Mixed decision + Red-adjacent work with Mike present — two of the three items
carry judgement halves, and Red work is never delegated. (If the provenance build turns out
purely Amber after the session's first hour, its code half may be handed to a fresh Opus
window and reviewed here — the split rule, applied only if the boundary is clean.)

**Budget:** ~half a day to a day with Mike present. Build cost dominated by [DB-0818-08]
(~half day); run-cost delta near zero (provenance adds a small field per stored fact — bytes,
no new standing resources); [DB-0804-02]'s slice is wording + small guards; [DB-0808-06] is a
design decision with at most a small build.

**Why this session exists:** these three were listed in the 08-27 capstone plan's remaining
investment and never claimed by any scheduled session — surfaced at the 09-02 close-out when
Mike asked why the capstone wasn't complete. His ruling: fold them in. **The capstone now
closes at THIS session's end**, after ⑤ (referent fix) and ⑥ (three bugs).

---

/metatron-code Session ⑦ — the last capstone session. Work in order, stopping at anything
decision-shaped:

1. **Nothing records where a fact came from ([DB-0818-08]).** Design decided 2026-08-28 (both
   halves + the hedge test — the full decided shape is in the item's `DEV_BACKLOG.md` entry;
   re-open it against current code first, per the standing rule). This is the one item of the
   three that was always capstone-shaped: it protects every store the other features write.
   Any agent-file wording is Red and prompts Mike.

2. **The B4 capstone slice ([DB-0804-02]).** The item bundles B4's five degradation paths,
   B2's confused-deputy remainder and friends. **Honest scope:** Phase 6A cannot fully close
   before E1, so this session takes the *buildable-now* slice — the user-facing degradation
   wording (specialist failure, context-tracker corruption, max-chain-depth: coherent,
   architecture-opaque messages) and any small guards — and explicitly re-homes the rest to
   Track B in the item, with Mike's word. A4 is suspended; the B1 red-team suite is the
   regression gate if `filter_output()` or degradation paths are touched.

3. **A flagged clinical thread can never be closed ([DB-0808-06]).** Decision-shaped: tier-2
   `CLINICAL_CONCERN` threads have no administrative-close mechanism, deliberately — design
   the escalation/close path with Mike (who may close one, on what evidence, and what the
   record keeps). Build only if the ruled design is small; otherwise file the build with the
   design attached. The clinical-thread lifecycle notes in `ROADMAP.md` § A7 (the 2026-08-08
   block) are required reading before proposing anything.

4. **Then the capstone CLOSES.** The ritual: a dated close-out note in
   `archive/plans/capstone_cluster_review_2026-08-27.md` (what closed, what re-homed, what the
   testing phase starts with), `SESSION.md` refreshed to the testing-phase footing, and the
   `CLAUDE.md` restructure debt checked (307/300 as of 09-02 — if still unpaid, it needs its
   own small pass, Mike's call on what moves out). State plainly whether anything **owes a
   commit, then a deploy.** /archive at close.

No new fronts: anything discovered here that is not these three items gets filed or reported,
not fixed.
