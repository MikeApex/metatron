### 2026-10-27 (the second-user build, Stages 0–2 — accounts, per-user binding, the in-app interview, Connections and permissions; built, Fable-reviewed, not merged) — worktree `metatron-wt-multi-user`, branch `multi-user-build`: `ef24032` (Stage 1), `79e42e0` (Stage 2), `de47c73` (Stage 3 handoff) — **nothing merged to `main`, nothing pushed from the branch, nothing deployed**

**Incoming handoff:** `archive/handoffs/2026-10-27-multi-user-build-prompt.md` (plan approved, Fable
22/22). Built in Opus in a worktree; each stage's diff reviewed by Fable, fixed, verify-rounded.

**Stage 0 contradicted the plan, and the first explanation was wrong.** `persona_audit.jsonl` does
not exist on the VM. I first read that as `.env` setting `METATRON_PERSONA` (which would also have
let systemd's `EnvironmentFile` override a per-user unit's `%i`) and proposed two guards. Mike's
check on the VM showed neither `.env` nor either unit names any persona variable — the **live units
are already strict** (recorded 09-25; `docs/INFRASTRUCTURE.md`'s stanza is stale). The guards were
withdrawn. Fable confirmed, and found § 3.3's env mirror **worse** than planned: overlapping scopes
leave a stale value, so an unscoped lookup can borrow someone nobody is serving (Stage 3.1 removes
it). Other Stage 0 facts: nothing reads `data/audio/`; the `torch 2.12.0+cpu` cp311 wheel exists;
four of six no-integration readers were already silent.

**Mike's decisions:** D14 idle timeout 10 min (after asking what is held — Metatron's TTS model,
not her recordings); template gains his check-in pacing and Monday week-ahead, **not** his check-in
wording (it restates `synthesizer.md`); skip the day planner's reshuffle on an empty day (~$0.05/day
an idle approved user would otherwise pay, invisible to every meter); optional city on sign-up;
**recordings backed up for `mike` and `iva` only, later accounts' not**; "if there are this many
issues, bring in a Fable reviewer… until reconciliation".

**Stage 1 (`ef24032`):** `core/accounts.py` (scrypt, `cred_version`, fcntl + atomic rename, 3.9);
v2 tokens `v2.<persona|*>.<role>.<cred>.<exp>.<hmac>`; `bound_persona()` on every route and the WS;
`/auth/register` with the sign-up notice's version recorded; `/monitor` and `/internal` refuse
account users; admin password never opens an account (D1); per-persona push and audio;
`scripts/accounts.py` (create-only provisioning, `enable` re-runs it); backups and `.gitignore`;
voice in its own helper (`core/tts_worker.py`); schedulers delegate models via `/internal/*`; CPU
torch in `deploy.sh`; not-connected calendar reads as nothing to do; memory samples + pending
sign-ups on the session-start line. Fable: no high; F1–F6, F8, F9 fixed; **F7 declined** —
falling through to the admin password on a corrupt account store would open an account (D1);
Fable agreed. A backup-quoting bug (a `case` inside `$( )`) was caught only by running the real
command against a throwaway tree.

**Stage 2 (`79e42e0`):** `core/interview.py` + WS routing (start-once claim, full interview
history from `channel='interview'` rows, coverage from stored data in plain words because
`filter_output` exempts identifiers the user "typed"); `core/connections.py` (test-before-write,
password only in `credentials.yaml`, Mike's inline configs refused); permission records enforced in
tone/CRM/`run_subagent`, **and in Coordinator dispatch — a second door the plan's P4 missed**.
Fable: no high; F1 (connect landing after withdrawal) fixed by a re-check under the write lock;
F3 — **my widened completion regex would have replaced honest "I've written the email — waiting"
replies; scoped to write_config cards**; the waiting line now names actions in plain words, never
`(write_config)`.

**Known, not this build's:** two pytest combinations fail identically on `main` (import-time
`DB_PATH` rebinding). Test leftovers (`zz_*`) sit gitignored in the worktree — the deny rule on
`data/personas/**` blocked deleting them. **Lesson:** a test must point every module-level root
(`core.persona._ROOT`, `core.trace.ROOT`, `core.accounts._ROOT`) at a temp tree in setup/teardown,
never at import, or it pollutes the tree and other suites.

**Next:** Stage 3 (Red, Mike present) from `archive/handoffs/2026-10-27-multi-user-build-stage-3-prompt.md`
on the branch — all other outstanding items travel with it.

