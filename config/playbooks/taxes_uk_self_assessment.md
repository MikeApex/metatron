# Playbook — filing a UK Self Assessment tax return online

<!-- Method only: no user's content ever enters this file (goal–task network plan § 4.4). Shared by
every persona. Researched 2026-11-21 by the Research Agent with a decontextualised question
(no personal context); fact-checked the same day against GOV.UK (a web-grounded check, plus
two models from training data) and reviewed by Mike before it landed. Figures (deadlines, thresholds, lead
times) are as researched on that date and are checked against GOV.UK when a filing depends on
one — HMRC changes them. Read by tools/project_plan.py when a goal or task matches `applies_to`. -->

applies_to: self assessment, SA100, UK taxes, UK tax return, UK tax

## Stages, in order

1. **Registration and online access** — only for a first-time filer, or one who has lost access.
   Check whether a return is needed (£1,000 or less of trading or of property income usually needs
   none); register (SA1 for most individuals, CWF1 if self-employed) — have the National Insurance
   number and photo ID ready for the identity check; wait for the 10-digit UTR; create the HMRC
   online account and enter the activation code. Own effort 30–90 min. **Elapsed: 3–4 weeks**
   (UTR up to 15 days by post, 21 if abroad; activation code up to 10 working days). Skip the stage when the user already files online.
2. **Gather documents** — for the tax year 6 April → 5 April. Typical: P60 (and P45 if they changed
   job), P11D for benefits in kind, bank interest on non-ISA accounts, dividends, pension
   contributions (relief-at-source amounts), Gift Aid totals, and — only where they apply —
   self-employment or rental records, foreign income, capital gains. Own effort 2–4 h for simple
   affairs, 6–15 h for complex ones. **Elapsed: 1–3 weeks** when a document has to be requested
   from an employer, bank or provider. Split into one step per source the user has.
3. **Decide: accountant or not** — worth it for complex self-employment, cross-border income or
   residence questions, jointly owned or holiday lets, large capital disposals, or income over
   £100k. If yes: engagement and identity checks (1–3 days), then HMRC agent authorisation
   (online code by post 5–7 working days; paper 64-8 takes 2–5 weeks). Own effort 1–2 h.
   **Elapsed: 1–3 weeks** before the accountant can start. This decision comes before preparing
   the return, and early enough that the elapsed time still fits.
4. **Prepare the return** — online: answer the tailoring questions (they open the supplementary
   pages), enter income and expenses, reliefs, student loan plan; review the tax calculation.
   Own effort 1.5–5 h — split into sittings of at most 90 minutes. Needs stage 2 (and 3 if an
   accountant is used — then this stage is the accountant's, and the user's step is "send the
   accountant the documents" and "approve the draft").
5. **Submit** — run the validation, check the computation, sign and submit, **save the
   submission receipt** (the proof of on-time filing). 30 min. Needs stage 4.
6. **Pay** — balancing payment and, if due, the first payment on account, using the 11-character
   payment reference (the UTR + "K"). 15–30 min. A Direct Debit needs 5 working days the first
   time it is set up, 3 after that.

## Deadlines

- 5 October: register, if newly liable for the year just ended.
- 31 October: paper return.
- **30 December: online return, if the user wants up to £3,000 owed collected through their PAYE
  tax code instead of paid as a lump sum.** A user whose own date is the end of December is
  probably aiming at this one — plan to it, not to 31 January.
- **31 January: online return, the balancing payment, and the first payment on account.**
- 31 July: second payment on account.

## Planning notes

- Plan backwards from the user's deadline. Put waiting time (registration, documents requested,
  agent authorisation) in `eligible_from` gaps, not in a step's minutes.
- No registration stage when the user already files online. If the note does not say whether
  they do, make the first step "Check you can sign in to your HMRC online account" (5 min, from
  today); the registration steps follow only if that check fails.
- The accountant decision is the first step when affairs look complex; otherwise one short step
  after the documents are in.
- Leave at least a week between the last document step and the deadline.

## Common failure points

1. Registering in January for a 31 January deadline — the post takes 2–3 weeks; automatic £100 penalty.
2. Surprise at the first payment on account (the bill on 31 January can be 150% of the year's tax).
3. Pension contributions entered in the wrong box (workplace net-pay entered as personal relief).
4. P11D benefits left out, because only the P60 was used.
5. High Income Child Benefit Charge not declared (adjusted net income over £60,000).
6. Payment sent without the UTR + "K" reference.
