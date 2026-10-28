Model: Opus 5.5. Effort: high — an operational session with Mike at the keyboard: a merge into a tree holding another session's uncommitted work, a push, a unit migration on the live VM, and the first real sign-up. Every command is prepared in advance and Mike runs the VM and deploy steps; nothing here is delegated.

# Second user — Stage 4 (deploy) and Stage 5 (verify, then Iva) (paste into a fresh chat)

**Budget:** ~0.5–1M Opus tokens for the session. Mike: ~30 min consent-text review, ~30 min
deploy and migration, ~15 min APK, ~30 min Stage 5 smoke, then the Iva walkthrough (~30 min, with
her). **Run cost once live:** unchanged from the plan § 7 — Iva ~$1.50–2.00/day if her use is like
Mike's, her interview ~$1.70 once (~$3.40 if Gemini 3.8's introductory rate ends); one more
scheduler process (~40–140 MB, no model). The spend caps are shared by both users (plan § 9 risk 4).

---

/metatron-code Continue the second-user build at Stage 4. Read first, in full and in order:
`archive/plans/multi_user_accounts_plan_2026-10-26.md` **in the worktree**
(`/Users/md-homefolder/Desktop/metatron-wt-multi-user`) — its banner carries the build-session
decisions — then `docs/INFRASTRUCTURE.md` **in the worktree**, § systemd unit files (the migration,
steps 1–7) and § Accounts, then this prompt.

## Where it stands

- **Branch `multi-user-build`** (worktree above), off `main` at `2073252`: Stage 1 `ef24032`, Stage 2
  `79e42e0`, Stage 3 prompt `de47c73`, **Stage 3 `6c728ab`**. All three stages Fable-reviewed, every
  finding fixed and verified closed. **Nothing merged, pushed or deployed.**
- **Merge forecast (checked 2026-10-28):** since the branch point `main` changed only
  `DEV_BACKLOG.md`, `SESSION.md`, `archive/PROJECT_LOG.md`, `archive/log/*` and this handoff — no file
  the branch touches. Re-check before merging; something may have landed since.
- **The main tree holds another session's uncommitted work** — `.claude/agents/build-inquiry.md`,
  `archive/plans/inquiry_rewrite_2026-09-26.md`, four untracked
  `archive/handoffs/2026-09-24-build-phase-*.patch`. The branch touches none of them. **Never stage,
  stash, reset or commit them**; a merge leaves them alone as long as it does not conflict on them.
- **Decided (Mike):** D14 idle timeout 10 min; check-in pacing + Monday week-ahead in the scheduler
  template; skip the reshuffle on an empty day; optional city at sign-up; recordings backed up for
  `mike` and `iva` only (`AUDIO_BACKUP_PERSONAS` in `scripts/metatron-backup.sh` — change it at
  approval if her username is not `iva`); D6 crisis wording as approved, pronouns neutral; **2026-10-28:
  a function job's push during the first interview (e.g. a travel alert) is dropped for that day,
  not deferred** — reminders she sets are kept and fire after.
- **Still owed by Mike, before Iva signs up:** review the three permission texts —
  `config/consent/base_configuration_v1.md` (the sign-up notice), `correspondence_read_v1.md`,
  `tone_profile_v1.md`. Once she accepts a version it is never edited, only superseded — so **do this
  first, before the merge**, and any edits ship in the deploy. D8 (which Google account she
  connects) is hers, at the walkthrough. D12 (Mike's own app passwords) open, recommendation: leave.
- **Known, not this build's:** `tests/test_a4_complexity_threading.py` fails 2 checks identically on
  `main`; `.claude/rules/deploy.md` is 131/100 lines on `main`.

## Stage 4 — deploy, in this order. Prepare each command; Mike runs every VM and deploy step.

Every VM command is run **on the MacBook** as:
`gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command="cd ~/multi-model-mcp && <cmd>"`
(or interactively, dropping `--command`). `./deploy.sh` is Denied in Claude Code — Mike runs it.

0. **Consent texts** — walk Mike through the three files above; commit any edit on the branch.
1. **Merge (MacBook, `/Users/md-homefolder/Desktop/multi-model-mcp`):** `git diff --stat main...multi-user-build`
   and read every file's diff before merging (CLAUDE.md: `git diff` every file); confirm none of the
   other session's files appears; `git merge --no-ff multi-user-build`. Run, on `main`:
   `PATH=/Users/md-homefolder/Desktop/multi-model-mcp/.venv/bin:$PATH ./scripts/qa_sweep.sh` (12/12),
   `tests/test_scheduler_multi_user.py`, `tests/test_subagent_depth.py`,
   `tests/test_spend_guard_multiprocess.py`, `tests/test_multi_user_isolation.py`,
   `tests/test_interview_mode.py`.
2. **Push (MacBook):** `git push origin main` — with Mike's go (`git push` is unprompted here).
3. **VM:** `git pull origin main`; `git rev-parse HEAD` must equal the Mac's. Record
   `.venv/bin/pip show kokoro torch` (kokoro is pinned nowhere). Then
   `.venv/bin/python scripts/accounts.py seed-consent mike --scopes correspondence_read,tone_profile --evidence "Mike's rulings 2026-08-26, 2026-08-28"`.
4. **VM, migration step 1:** `sudo cp infra/systemd/metatron-scheduler@.service /etc/systemd/system/ && sudo systemctl daemon-reload`;
   `systemctl cat metatron-server | grep EnvironmentFile` names only `.env`; **pre-check**
   `sudo systemctl restart 'metatron-scheduler@*'; echo $?` must print `0` (deploy.sh runs that line
   under `set -e`).
5. **MacBook:** `./deploy.sh` (Mike). It installs CPU-only PyTorch, removes `nvidia-*`, restarts
   `'metatron-scheduler@*'` (none loaded yet) and then the server. **The old scheduler keeps running
   old code** — its coordinator sessions 401 until step 7 (expected; logged to
   `data/personas/mike/logs/scheduler_errors.json`). Keep steps 5–8 together.
6. **VM, migration step 2a — the `/proc` scan, for real:** `sudo systemctl start metatron-scheduler@mike`;
   `sudo journalctl -u metatron-scheduler@mike -n 5` shows `REFUSING TO START … a scheduler without
   the instance lock is already running`; `sudo systemctl stop metatron-scheduler@mike`.
7. **VM, steps 3–4:** `sudo systemctl disable --now metatron-scheduler`;
   `mkdir -p ~/retired-units && sudo mv /etc/systemd/system/metatron-scheduler.service /etc/systemd/system/metatron-scheduler.service.d ~/retired-units/ && sudo systemctl daemon-reload`.
8. **VM, steps 5–7:** `ps -eo pid,args | grep '[s]cheduler.py'` shows none for mike;
   `sudo systemctl enable --now metatron-scheduler@mike`; `ps` again shows exactly one;
   `systemctl show metatron-scheduler@mike -p Environment` lists `METATRON_HOST=vm`,
   `METATRON_PERSONA=mike`, `METATRON_NO_LOCAL_MODELS=1`; `.venv/bin/python core/scheduler.py --persona mike`
   exits 1 on the lock; `sudo systemctl restart metatron-scheduler` reports the unit not found.
9. **MacBook:** rebuild and sideload the APK (`docs/INFRASTRUCTURE.md` § Android app); Mike signs in
   as `mike` (typed) on phone and browser — every device signs in once after this deploy.
10. **Check:** `get_tone_shape` for one of mike's saved contacts answers (not "not permitted"); a
    normal message gets a normal reply; The Book shows mike.

## Stage 5 — verify on the VM (plan § 6.3, § 6.3a), then Iva

**§ 6.3 on a smoke-test account `trial_2026_10`** — all seven: (1) sign up in the app → "waiting" →
`/monitor/accounts` and the session-start line show it → `accounts.py approve trial_2026_10` → sign
in; (2) the interview opens unprompted; ~6 turns covering a goal and two day-shape items; confirm
they were written (The Book); (3) *Finish later* → a normal message gets a pipeline reply →
*Continue setting up* resumes with the right coverage; (4) **one crisis probe** inside the interview —
resources given, not minimised, interview pauses (evidence, not the A4 gate — A4 stays suspended);
(5) with the trial token, `?persona=mike` on three routes and the WS → 403 each, `/monitor/file` →
403; (6) leave it a day: its scheduler log and `quality_events.json` carry no repeating
"not configured" errors, and no brief fired while the interview held; (7) `disable` → its scheduler
stops, sign-in refused, directories archived not deleted. **Pass = all seven; anything else is fixed
before Iva.**

**§ 6.3a memory:** server RSS after warm-up with voice unused (estimate ~1.0–1.2 GB — record the real
figure), no `nvidia` library mapped, no `kokoro` loaded; ten spoken replies → the helper appears, the
server's RSS does not move, ten idle minutes later the helper is gone (`free -m`); then **the
week-long whole-VM watch** (`data/system/memory_samples.jsonl`, a Sunday included): each scheduler
under ~300 MB and never mapping `torch`/`sentence_transformers`, VM available memory never under
500 MB on an ordinary day. Confirm the session-start line's memory clause stays well under its 3 s
timeout (`memory_alerts.jsonl` is ~1.8 MB). Any miss → D10 (c), the upgrade, priced with that week.

**The Iva walkthrough — an (M) session, steps prepared in advance, Mike and Iva live:** share only
`metatron-vm` with her on Tailscale; send her the APK directly; her sign-up with the notice; "approve
iva" in chat (`accounts.py approve iva` over the SSH line above; check `AUDIO_BACKUP_PERSONAS`
matches her username); Connections with her Google account — **D8 at that moment** (recommended: a
dedicated Metatron Gmail, as Mike's own persona uses; her own is her choice); tell her where the app
password lives (only on the VM, never in a backup, reachable by Mike); the first minutes of the
interview. Then her use decides.

Close with `/archive`.
