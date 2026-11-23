### 2026-11-23, fifteenth (ranking Part B phase 2 — the public-fact lookup price checked, figures refused, lookup switched on in config)

**What changed for a user:** once deployed, Metatron may look up a public fact (a fund's closing
date, how long a renewal takes) before asking about a task — at most 5 a day, and a question that
carries a money amount or health reading is refused and rephrased without it. `129f3fb`, one file:
`config/modules/ranking.yaml` (`lookups.enabled: true`, `refuse_figures: true`).

**Why it was safe to flip:** the lookup is Google Search grounding, billed per query and seen by no
spend meter (plan § 8 Unseen 1), so the 5-a-day cap is the only bound. The price had been recalled,
not verified. Mike checked it: `research_agent` is `models/gemini-3.8-flash`, the Gemini 3-series
row — **$14 per 1,000 search queries, first 5,000 a month per account free**. 5 a day × ~3 queries =
$0.21/day/user worst case, before the allowance. The recalled figures were right.

**Decisions:** figures in a question — **refuse** (Mike), the built and recommended option. Rejected:
let them through — it sends the user's real quotes, balances and readings into Google searches,
against the sensitive-tier ruling.

**Caveats recorded, not hidden:** the price came from a pasted summary of the pricing page, not the
page; the comment in `ranking.yaml` says so. Gemini pricing doubles 2027-01-01 (SESSION.md) — the
comment asks for a re-check then. No test was run; the pass signal is a public-fact question being
looked up rather than asked, and a question with the user's own figure being rephrased.

**Deploy:** Mike said he deployed in another chat. This session did not deploy and cannot see the
VM; whether `129f3fb` itself was on the VM at that deploy was not checked (it was unpushed until
this close-out). Check `lookups.enabled` on the VM if it matters.

**Still open from phase 2:** the passion tie (Mike to confirm); the protected-time and behind
shadows, three days each; phase 3 prompt is written.

**Outgoing SESSION.md handoff, phase-2 sentence:** "Phase 2 — BUILT in shadow, NOT deployed
(`e134948`)… `lookup_public_fact` ships OFF… Open with Mike: call 2 (refuse money/health figures in
a lookup; built on) and confirming the passion tie. (M): the grounding price check, then the switch."

