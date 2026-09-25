### 2026-09-25, third (the orchid refusal was right, phase F narrows to run 1) — the F1 prompt; **nothing deployed beyond `4f0a6c3`**

Short segment, two decisions and one correction to a diagnosis.

**Mike's ruling: the Coordinator refusing to file on an orchid question is CORRECT behaviour.** Asked
*"which of my orchids needs fertilizing this week?"* it said it had nothing on file and asked which
varieties and what routine — rather than filing a gap. *"It shouldn't be building an orchid tool
without knowing anything about what it actually needs to do."* That is § 3's N6 interview gate
reasoning arriving one layer earlier, and it narrows the defect recorded in this day's second entry:
**the Coordinator refuses correctly when it holds nothing, and over-reaches when it holds something
partial.** The fig question had watering records to assemble from; the orchid question had nothing.
So the failure is not "it will never admit a gap" — it is specifically shape 2 over an existing
history, which is a smaller and more tractable claim than the one I was making.

**Decision: proceed to phase F without the under-filing fixture.** § 12 puts
`tests/fixtures/build_trigger_requests.yaml` before run 1. Mike has chosen to run 1 first. Recorded
as a stated departure rather than an oversight, and the F1 prompt carries it in a section headed
*what this run does NOT close* so the window cannot report it as closed.

**Nothing filed to `DEV_BACKLOG.md`, and that is a reversal of what I proposed an hour earlier.** I
had recommended filing the measurement suite and the uninstructed specialists. Reading the plan
showed the first is **already** § 12's Under-filing row — Mike's own 09-24 ruling, ≥ 12 requests,
half file and half route, re-run whenever `coordinator.md` changes — and the second is already in
`SESSION.md` as a rollout condition. Filing either would have put a thinner second copy in a list
nobody reads while the authoritative copy sat in the plan. *Rejected: filing anyway for visibility.*

**The F1 prompt is scoped to run 1 alone**, against § 14's "runs 1–3 as one walkthrough". Reason: run
1 is the first end-to-end execution of the graph, and this build's repeated finding is that a first
execution finds defects — phase C's review found ten on a package with 236 green checks. A prompt
assuming run 1 succeeds would carry a broken driver into run 2. Runs 2 and 3 get their own prompt
once run 1 lands clean.

**Its first step is the trigger, deliberately.** Mike puts a real `home_care` question — one where
data exists, so the shape-2 case is live — to the deployed app before `/build` is touched. If a
ticket files, § 12's Trigger row closes and the verbatim question becomes the first known-good
should-file case for the fixture the plan still owes. If nothing files, the window hand-files and
**must name the two § 12 rows that stay open**: the Trigger row, and the first arrow of the
End-to-end row. `BLD-0925-01` proved hand-filing works, which is exactly why it needed saying that
using it is not the same as closing the row.

