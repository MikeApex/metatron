Model: Opus 5.5. Effort: high — identity, isolation and consent code where one wrong default exposes one person's data to another; the Red stage is built by hand with Mike present (never delegated), and each stage's diff goes to Fable for review before the next.

# Second user — the build (paste into a fresh chat)

**Budget:** ~4.5–7M Opus tokens across Stages 0–3 (Stage 1 the largest), plus ~0.5–1M per Fable
diff review; ~2–3 Mike-hours (Red session 60–90 min, deploy and APK ~30 min, two walkthroughs ~30
min). **Run cost once live:** Iva's use ~$1.50–2.00/day if like Mike's (~$45–60/month, approved —
billing limits are adjusted when she starts); her interview ~$1.70 once (~$3.40 if Gemini 3.8's
introductory rate ends). Plan § 7 has all four cost classes and the persistence questions.

---

/metatron-code Build the second-user plan. Read first, in full and in this order:
`archive/plans/multi_user_accounts_plan_2026-10-26.md` (approved by Mike 2026-10-27; Fable review
resolved, 22 findings over 13 rounds, all closed), then its review
`archive/plans/adversarial_review_multi_user_accounts_plan_2026-10-26.md` — the dispositions in
the plan's § 12 say which section answers each finding. **D5's condition is met** (day-planner
Stage B landed in `9f2eeac`); the plan's banner records it.

## Before writing anything

1. **Ask Mike the one open parameter that changes code:** the voice helper's idle timeout (D14,
   recommended 10 minutes — ~1.5 GB held for that long after the last spoken reply; the first reply
   after it waits ~10 s). D8 (which Gmail Iva connects) and D12 (Mike's own app passwords —
   recommendation: leave) do not block the build.
2. **Stage 0, read-only,** exactly as the plan lists it (§ 5): the persona audit log on the VM, the
   `data/audio/` readers, the template vs live `scheduler.yaml` diff, every calendar/mail/intake
   reader on a no-integration persona, **and the `torch==2.12.0+cpu` wheel's existence for the VM's
   Python** (§ 4.12.1). Mike checks one thing himself: whether the VM's `.env` sets
   `METATRON_PERSONA` (this session cannot read `.env`). Report what Stage 0 found before Stage 1;
   anything that contradicts the plan goes to Mike, not around him.

## How to build

- **In a git worktree off `main`.** This tree holds another session's uncommitted work —
  `.claude/agents/build-inquiry.md`, `archive/plans/inquiry_rewrite_2026-09-26.md`, four
  `archive/handoffs/2026-09-24-build-phase-*.patch` files — never touch, stage or commit them.
  `git diff` every file before staging; stage by explicit path.
- **Stages in order — 1, 2, then 3** (plan § 5). Stages 1 and 2 are Amber/Green and may be built by
  this session; **no subagent writes `core/auth.py`, `core/accounts.py`, `core/consent.py` or the
  identity helper.** At the end of each stage: its § 6.1 tests and every existing suite green
  (`scripts/qa_sweep.sh`, `scripts/check_agent_tools.py`, `scripts/check_personas.py`, the auth,
  attachment, location, task-ledger, decline, WS-idempotency and day-plan suites), then **a Fable
  review of that stage's diff** (`/code-review high`, or `/adversarial-review` against the diff if
  a design question surfaces) before the next stage starts.
- **Stage 3 is Red** — `core/persona.py`, `core/scheduler.py`, `core/spend_guard.py`,
  `config/agents/goals_interviewer.md`, both routing files. Mike present; every edit prompts. The
  crisis wording in the interviewer's Safety section is shown to him there (D6). Run the scheduler
  for real afterwards (deploy rule 1 — importing it is not enough).
- **Standing rules that bite here:** a test that exercises a seam for real stubs every live meter
  it ends in (model, CalDAV, IMAP, push, Routes); a live gate run dirties tracked fixture-persona
  files (`data/personas/danny_park/…`) — `git checkout HEAD --` them before a patch or commit;
  `core/accounts.py` stays stdlib-only and 3.9-compatible (§ 4.2).
- **If context gets heavy, stop at a stage boundary** and write a continuation prompt to
  `archive/handoffs/` (model and effort on its first line, written out in full) rather than
  pressing on through a compaction — path-scoped rules drop at `/compact`.

## Deploy — Mike's, in the plan's order (§ 5 Stage 4)

Step 0 first: push from the Mac, pull on the VM and confirm the HEADs match, run
`scripts/accounts.py seed-consent mike …` — then the unit changes and `daemon-reload`, then
`./deploy.sh` (Denied here — Mike runs it), then the scheduler migration (disable, retire the old
unit file, `ps` checks either side), then the APK rebuild and Mike's sign-in on phone and browser,
then the `get_tone_shape` check for `mike`. Prepare each command in advance; Mike executes.

## Then verify, then Iva

1. § 6.3 on the real VM with the throwaway `trial_2026_10` account — all seven checks, including
   one crisis probe in the interview. Pass = all seven; it is disabled and archived after.
2. § 6.3a — the memory result, measured across the whole VM; the week-long part runs on its own.
3. **The Iva walkthrough (the (M) rule):** steps prepared in advance — share only `metatron-vm` on
   Tailscale, send her the APK file, her sign-up (with the sign-up permission screen), Mike's
   "approve iva" in chat, Connections with her Google account (D8 at that moment), and the first
   minutes of the interview.

Close with `/archive`.
