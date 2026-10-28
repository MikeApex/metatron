### 2026-10-28 (the second-user build, Stage 3 — a scheduler per user, nothing interrupts the first interview, and no request can borrow another's identity or delegation limit; Fable-reviewed and verified) — worktree `metatron-wt-multi-user`, branch `multi-user-build`: `6c728ab` — **nothing merged to `main`, nothing pushed from the branch, nothing deployed**

**Incoming handoff:** `archive/handoffs/2026-10-27-multi-user-build-stage-3-prompt.md` (on the
branch). Red files edited by hand with Mike approving each; Stage 3 diff reviewed by Fable, fixed,
verify round closed with no new findings.

**Built:** `persona_scope()` stops mirroring into `os.environ` — the new test reproduced the leak on
the old code (an unscoped third thread was served as `pepys`). Scheduler: the D2 interview hold;
per-persona push; single-agent jobs via `/internal/session`; `_claim_single_instance` (fcntl lock +
`/proc` scan that counts a sibling only if it does **not** hold the lock, so a new instance losing
the race cannot make the winner exit too); refusal of a persona with no identity file. Spend guard:
cross-process lock **and** an atomic day-file write — the control run under the old thread lock
lost **398 of 800** concurrent increments, and `check_before_session` read a torn file as a blank
day, i.e. **$0 spent**. `goals_interviewer.md`: Confidentiality, Mike's D6 Safety wording,
write-as-you-go, pause/finish (granted in both routing files). Template unit
`infra/systemd/metatron-scheduler@.service`. Records: `ROADMAP.md` § 0 consent amendment and § 3
ahead-of-Phase-7 note, `CLAUDE.md` trap 5 + privacy line (300/300), `docs/INFRASTRUCTURE.md`,
`.claude/rules/personas.md` (110/110).

**Mike's decisions:** D6 approved with pronouns made neutral ("the user/they") — the file serves
every user and never said "she"; Stage 2's model-facing interview strings were de-gendered to
match. **A function job's push during the first interview is dropped for that day** (option 1 of
two; letting urgent travel alerts through was rejected — the one thing allowed to interrupt would
be the most alarming, for a rare case early in her use).

**Fable review (all fixed, verified CLOSED):** S1 — the hold was by job *kind* and missed two
user-facing function jobs (travel push; day-plan nudges, which open a conversation once Stage C
turns them on); now enforced at `_dispatch`, `nudge_tick` and a server `held` backstop. S2 —
`run_subagent`'s depth lived in `os.environ`, so one user's nested specialist made the other's
Coordinator refuse to delegate (silently thinner answer); now thread-local in `core/trace.py`,
propagated at six thread boundaries. L1 a held one-off was popped then skipped — deleted unseen;
L2 doc symptom; L3 env-dependent resolver test; L4 a typo'd instance created a user's tree.

**Believed true and wasn't — four:** (1) the prompt's `"agent" in job_cfg` would have missed
one-off reminders, which carry no `agent` key; (2) I told Mike a held travel alert "waits" — it is
dropped, the job has already fired; (3) I first wrote that `deploy.sh` restarts the old scheduler
onto new code — it restarts only `@*`, so the old process stays lock-less, which made a real
`/proc` test on the VM possible (migration step 2a); (4) the live units carry `PYTHONUNBUFFERED=1`
and a `METATRON_HOST=vm` **drop-in** the doc never recorded, and `.service.d/` does not apply to `@`
instances — the migration would have silently dropped the marker; both now in the template.

**Slip:** my first real-process smoke left two scratch-tree schedulers running ~1 h (killed the
shell wrappers, not Python). No spend: the day planner logged `skipped_empty` and the Mac has no
spend file today. Re-run with direct pids.

**Verification:** 116/117 suites (the one failure fails identically on `main`); `qa_sweep` 12/12;
five JS suites; real two-scheduler run — both register, duplicate and typo refused.

**Next:** Stage 4 (deploy) and Stage 5 (verify, then Iva) from
`archive/handoffs/2026-10-28-multi-user-build-stage-4-prompt.md` — Mike reviews the three
permission texts first; the merge forecast is clean.

