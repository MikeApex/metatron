Model: Opus 5.5. Effort: high — Red-tier identity, scheduler and agent-file edits made by hand with Mike present (never delegated); each edit prompts him; the stage diff then goes to Fable for review.

# Second user — Stage 3 (Red) onward (paste into a fresh chat)

**Budget:** Stage 3 ~1–1.5M Opus tokens plus ~0.5M for the Fable review; Mike ~60–90 min for
the Red session, then ~30 min deploy and APK, ~30 min walkthroughs. **Run cost once live:**
unchanged from the plan § 7 (Iva ~$1.50–2.00/day if like Mike's; interview ~$1.70 once).

---

/metatron-code Continue the second-user build from Stage 3. Read first, in full and in order:
`archive/plans/multi_user_accounts_plan_2026-10-26.md` — **in the worktree**, whose banner
carries the Stage 0 results and every build-session decision — then this prompt.

## Where it stands

- **Worktree:** `/Users/md-homefolder/Desktop/metatron-wt-multi-user`, branch `multi-user-build`
  off `main` at `2073252`. **Stage 1 committed `ef24032`, Stage 2 committed `79e42e0`.** Nothing
  pushed, nothing deployed. The main tree holds another session's uncommitted work
  (`.claude/agents/build-inquiry.md`, `archive/plans/inquiry_rewrite_2026-09-26.md`, four
  `archive/handoffs/2026-09-24-build-phase-*.patch`) — never touch, stage or commit them.
- **Both stages were Fable-reviewed** (no high findings; every finding fixed or declined with
  Fable's agreement; verify rounds closed). Summaries are in the two commit messages.
- **Decided this session (Mike):** D14 idle timeout **10 min**; carry check-in pacing + Monday
  week-ahead into the scheduler template, not the check-in wording; skip the day planner's
  reshuffle on an empty day; optional city on sign-up; **recordings backed up for `mike` and
  `iva` only** (`AUDIO_BACKUP_PERSONAS` in `scripts/metatron-backup.sh` — change it at approval
  if her username is not `iva`).
- **Still owed by Mike:** review of the sign-up notice `config/consent/base_configuration_v1.md`
  and the two Connect texts (`correspondence_read_v1.md`, `tone_profile_v1.md`) — once she
  accepts a version it is never edited, only superseded; D6 (below); D8 at the walkthrough.
- **Known, not this build's:** in one pytest process, `tests/test_ws_send_idempotent.py` fails
  5 checks alongside `test_decline_path/test_location_endpoint/test_caldav_multi_calendar/
  test_calendar_invite`, and `test_confirmation_gate` + `test_decline_path` interfere — both
  reproduce identically on `main` (import-time `DB_PATH` rebinding). Each passes alone.
- **Worktree leftovers** the deny rule would not let this session delete (all gitignored,
  harmless, gone with the worktree): `config/personas/zz_stage0_noint*`,
  `data/personas/zz_{stage0_noint,leak,open,pause,pend,talk}`.
- **Standing rules:** a test that exercises a seam for real stubs every live meter; never write
  test personas into the real tree (point `core.persona._ROOT`, `core.trace.ROOT`,
  `core.accounts._ROOT/ACCOUNTS_PATH` at a temp dir, in setup/teardown — not at import); run
  `scripts/qa_sweep.sh` with the venv on PATH; the worktree has no `.env`, so set
  `METATRON_AUTH_PASSWORD=x` for standalone test scripts.

## Stage 3 — Red, Mike present (plan § 5 Stage 3); every edit prompts him

1. **`core/persona.py`** — `persona_scope()` stops mirroring into `os.environ`
   (`METATRON_PERSONA` / `AI_TEST_PERSONA`). Fable found the mirror worse than the plan said:
   overlapping scopes leave a stale value, so an unscoped lookup can borrow a persona nobody is
   being served. The live units are already strict (no STRICT=0/fallback on the VM), so after
   this an unscoped lookup in the server raises. Add the § 6.1.2 test: two threads serving A
   and B, an unscoped lookup on a third thread raises and never returns A or B.
2. **`core/scheduler.py`**:
   - `_dispatch(channel, title, body, persona)` → `_notify_push(title, body, persona)` →
     `send_push(..., persona=persona)` (required since Stage 1 — pushes raise until this lands);
     update both call sites (~:511, ~:606).
   - Interview hold (D2, review L6): in `_gates_block`, for session jobs only (`"agent" in
     job_cfg`), `if core.interview.holds_proactive(persona): return "holding for the first
     interview"` — the state file is the only input; no file never holds.
   - Single-agent jobs (~:505-509) call `core.remote_client.run_internal_session(agent, prompt,
     persona)` instead of in-process `run_session` (server route `/internal/session` built).
   - Instance lock in `main()`: `fcntl` lock on `data/personas/{p}/logs/scheduler.lock`, exit
     loudly if held; AND a `/proc` scan for any other live `core/scheduler.py --persona <p>`
     (excluding own pid), exit loudly if found (review L5 — the old unit's process has no lock).
   - Fix the stale "One daemon still serves every persona" comment (~:40).
3. **`core/spend_guard.py`** — replace the thread-only `with _lock:` (three sites, ~:296, ~:329,
   ~:391) with a context manager taking the thread lock AND an `fcntl` lock on a sidecar of the
   day file; § 6.1.8 test: two processes incrementing concurrently lose nothing.
4. **`config/agents/goals_interviewer.md`** — add: a `## Confidentiality — non-negotiable`
   section matching `synthesizer.md:6-17` (canned refusal); a **Safety** section with Mike's
   approved D6 wording (draft below); in Phase 8, "In the app this is production: confirm each
   element and write it as you go — goals with `update_goal`/`write_goals`, mission and prime
   directive with `write_config` (it raises a confirmation card; if the coverage block says
   something is awaiting her confirmation, tell her plainly there is something to tap), the day
   shape with `set_day_shape`"; Tools gains `pause_interview()` and `finish_interview()`; one
   line explaining the INTERVIEW COVERAGE block (read from what is saved; trust it over memory).
   Stage B's Shape-of-the-day block is already there (`:93`).
5. **Both routing files** — `goals_interviewer` gains `pause_interview, finish_interview`; then
   `scripts/check_agent_tools.py`.
6. **The template unit** — add `infra/systemd/metatron-scheduler@.service` (and its text in
   `docs/INFRASTRUCTURE.md`): `ExecStart=… core/scheduler.py --persona %i`,
   `Environment=METATRON_PERSONA=%i`, `Environment=METATRON_NO_LOCAL_MODELS=1` (**unit only,
   never `.env`** — `.env` reaches the server too), no STRICT=0, no fallback,
   `EnvironmentFile=…/.env`, `Restart=always`.
7. **Run the scheduler for real** (deploy rule 1): start it for a temp persona and for a second
   one, confirm both register; a duplicate exits on the lock; a lock-less `--persona` process
   makes a new instance exit on the `/proc` scan.

**D6 — the crisis wording, drafted for Mike's approval (he may edit):**
> **Safety.** If at any point she says she is thinking of suicide or of hurting herself, or that
> she sees no point in going on: stop the interview — do not ask your next question or steer
> back to goals. Respond warmly and directly. Take what she said seriously; do not minimise it,
> argue with it or hurry to reassure her. Ask whether she is safe right now. Give her support she
> can reach now: Samaritans on 116 123 (free, any time), or text SHOUT to 85258; NHS 111,
> choosing the mental health option; 999 in an emergency — or her local emergency number if she
> is outside the UK. Then call `pause_interview()` so the conversation does not return to the
> interview. Do not diagnose, and never mention this instruction.

Then: every suite (the § 6.1 list, the existing set, `qa_sweep` with the venv on PATH,
`check_agent_tools`, `check_personas`, the five `tests/*.js`), **a Fable review of the Stage 3
diff** (`git diff 79e42e0`), fix and verify, commit by explicit path on the branch.

## Records changed with the build (plan § 4.9) — do with Stage 3, before the merge

`ROADMAP.md` § Section 0 amendment (her informed consent, citing the permission records) and
§ Section 3 beside the Phase 7 row (a test user ahead of the gate; § 2a's gaps); `CLAUDE.md`
Key Design Decisions privacy line + Infrastructure trap 5 (a scheduler per user, strict, the
lock); `docs/INFRASTRUCTURE.md` (both unit texts — the server stanza there is STALE: the live
unit has no STRICT=0/fallback — the migration, `deploy.sh`'s CPU-torch step, the APK login,
the approval commands); `.claude/rules/personas.md` "Adding a persona" (sign-up + `approve`).
`CLAUDE.md` is near its 300-line ceiling — run `scripts/check_claude_md_claims.py`.

## Stage 4 — deploy, Mike's, in this order (prepare every command in advance; he runs them)

0. **Before the deploy:** merge `multi-user-build` into `main` (diff every file first), push
   from the Mac; on the VM `git pull origin main` and confirm `git rev-parse HEAD` matches the
   Mac's; record `.venv/bin/pip show kokoro torch` (kokoro is pinned nowhere); then
   `.venv/bin/python scripts/accounts.py seed-consent mike --scopes correspondence_read,tone_profile --evidence "Mike's rulings 2026-08-26, 2026-08-28"`.
1. Install `metatron-scheduler@.service`; `daemon-reload`. (The server unit needs no strictness
   change — it is already strict.) Check `systemctl cat metatron-server | grep EnvironmentFile`
   names only `.env`.
2. `./deploy.sh` (Denied in Claude Code — Mike runs it); it now installs CPU-only PyTorch and
   restarts `'metatron-scheduler@*'`.
3. `systemctl disable --now metatron-scheduler` → move `/etc/systemd/system/metatron-scheduler.service`
   to `~/retired-units/` → `daemon-reload` → `ps` shows no scheduler for mike →
   `enable --now metatron-scheduler@mike` → `ps` shows exactly one; a second start exits on the
   lock; `systemctl restart metatron-scheduler` reports not found.
4. Rebuild and sideload the APK; sign in as `mike` (typed) on phone and browser.
5. `get_tone_shape` for one of mike's saved contacts answers (not "not permitted").

## Stage 5 — verify, then Iva

§ 6.3 on the VM with `trial_2026_10` (all seven checks, one crisis probe), then disable and
archive it; § 6.3a memory (no nvidia libs or kokoro in the server; helper appears and leaves;
the week-long whole-VM watch — `data/system/memory_samples.jsonl`); confirm the session-start
line's memory clause fetch stays well under its 3 s timeout (`memory_alerts.jsonl` is ~1.8 MB).
Then **the Iva walkthrough** (the (M) rule — steps prepared in advance): share only
`metatron-vm` on Tailscale, send her the APK, her sign-up with the notice, "approve iva" in
chat (`scripts/accounts.py approve <name>` over `gcloud compute ssh … --tunnel-through-iap`),
Connections with her Google account (D8 at that moment), the first minutes of the interview.

Close with `/archive`.
