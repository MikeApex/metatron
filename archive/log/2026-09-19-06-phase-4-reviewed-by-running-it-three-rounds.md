### 2026-09-19 (Build phase 4 reviewed by running it — three rounds, seventeen defects, all closed)

Review-only session on Fable 5.1 against the uncommitted phase-4 diff (runner, brief, registry,
coherence, board scripts, wiring) and plan § 3/5/7/8/12/14. One artifact:
`archive/plans/build_phase4_runner_review_2026-09-19_fable-5.md`, three parts — the first review
and two re-checks after Mike's fixing session, which ran in the other window. Nothing built here,
nothing deployed, nothing else edited.

**Method, and why it mattered.** Every claim was produced by running, not reading: the writer
suite's real git fixture repo and its fixture persona, the model stubbed exactly as the runner
suite stubs it, both live meters stubbed — and **the real writer and the real 18-check
`verify.run_all()` in the loop**, ~10 s a landing. Ten probes from the brief (one job to `landed`
through every node; three capabilities; `kill -9`; a failing check; budget; `request_build`;
REPAIR; coherence; trace shape; empty tick and a write-path audit). Each re-check re-ran every
earlier probe unchanged on fresh fixture copies before probing the fixes.

**Round 1: fourteen defects, ranked by cost of being wrong.** The four worth remembering:
`refuse()` had no state check and deleted a *landed* capability's overlay while the registry kept
saying landed; a job crossing its spend limit *during* the Planner call was failed terminally
(the writer's dry-run was budget-gated) instead of parking for approval — the likeliest way run 1
would have answered the placeholder-limit question; correction attribution blamed whatever wrote
the newest trace, which after a tick is Build's own agents and after most turns the Diarist, so
the REPAIR trigger could never reach three; and the manifest's fixed probe for the `log` source
did not fit `get_log_window`'s signature, so the primary corpus probed as `error` on every question
— a phase-2 defect that phase 4's first real walk exposed. Also: coherence blind in both halves
(no surface map reached it; the model's bare-list reply was mangled by `repair_json`), the
ceiling-park resume stranding a job, REPAIR re-filing per correction because the count sat in the
fingerprinted gap, and every documented VM command needing an unstated persona.

**Round 2 closed all fourteen; three small ones left** (landed brief said `executing`; the
previous-turn block still read a tick as the exchange; landing-day run counts wrote `0.0 over
1d`). **Round 3 closed those three; nothing new.** Suites grew from 86 to 59+18+24+21+41+36+14+16
across the nine Build files plus `test_turn_referent.py` 22/22; `qa_sweep` 11/11 throughout.

**Believed true earlier, wrong.** The phase-4 close-out recorded "every prior suite unchanged" as
evidence the phases-1–2 surface was sound; the first end-to-end walk showed the probe table had
never been exercised against real handler signatures (`log`, `calendar`, `email`, `archive`,
`memory`, `intake_queue`, `agent_config` all wrong, and seven live feeds that would have made real
outbound calls per question). Also the round-1 kill probe's driver read a stale ledger on re-run,
so round 2's kill landed between N2 and N3 rather than mid-N4 — reported, and the resume held
either way.

**Design change surfaced by the fixes, worth knowing:** a scheduled session now counts as an
exchange for both the previous-turn block and correction attribution, so a correction after a
morning check-in is attributed to the specialist it dispatched. Consistent across both readers.

**Left open, owned elsewhere:** `answer_interview_item` is granted to no agent (phase 5's routing
files, with `request_build`); The Book's rendering of a tick has not been opened (phase 7's
criterion). Phase 4 itself remains uncommitted in the tree, by instruction, alongside the other
window's headset-mode changes — `git diff` each file before staging.

