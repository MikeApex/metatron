Plan reviewed: archive/plans/multi_user_accounts_plan_2026-10-26.md
Reviewer: Fable (adversarial-reviewer) · effort: high · 2026-10-26

## STRUCTURAL

3. [§ 2, § 4.9, § 11] [ROADMAP.md § Section 3 "Phase 7" gate row; archive/plans/phase5_to_future_roadmap_2026-06-10.md:727-749 "Track F"]
Wrong: The plan builds Phase 7's multi-user deployment past a roadmap gate (Phase 6 + 6A + 6B + user research session) and past Track F's "user research session required before building" without naming either, and its § 4.9 record changes leave `ROADMAP.md` saying multi-user is gated while a second user is live.
Fails: Track F's isolation design (separate access-controlled paths, the per-user key-compromise test that assumes D2 encryption) is pre-empted by auth-layer-only isolation with no recorded acceptance, and ROADMAP's own instruction to read Track F before working in the area was not followed.
Costs: The next session finds a roadmap that contradicts the deployment and either re-derives the override or treats Iva's isolation as Phase-7-grade when it is not — medium.

## LOCAL

1. [§ 4.7 "Writing as it goes", § 4.7 "Interview mode"] [core/orchestrator.py:run_session line 7225 applies only `filter_output`; `enforce_pending_receipt` runs only at 6713 and 7109 (pipeline); `pending_directive_note` at 6157]
Wrong: The interview routes turns through the single-agent `run_session` path, where the guard that stops a model reporting a pending `write_config` as done does not run — only the refusal half of "B2's gate, unchanged" is on that path.
Fails: `write_config` returns PENDING_CONFIRMATION to the interviewer, which can tell a first-time user her prime directive or mission is "recorded" while it sits in `pending_confirmations.json` awaiting a card she has never seen, and `finish_interview()` can close on unwritten Tier 1/2.
Costs: The 2026-08-05→08-15 class of failure (approved-and-never-performed, user believes it happened) lands on the one user with no prior model of the app, on the two files the interview exists to populate — high.

2. [§ 4.8, § 5 Stage 5, § 6.3.6, D5] [tools/caldav.py:_query_events lines 631-638; tools/day_plan.py:refresh_snapshot lines 318-331 and refresh_tick lines 2266-2270; scripts/new_persona.sh:81-92 provisions `caldav.yaml` with `enabled: false`]
Wrong: § 4.8's requirement that every calendar/mail/intake reader treat "not configured" as nothing to do has no stage that builds it, and it is false today: `_query_events` returns an error dict for a disabled calendar and `refresh_snapshot` records `error`/`failed_at` and logs `ok=False` on every refresh.
Fails: Once Stage B registers `refresh_tick` (D5 recommends Stage B lands first), Iva's scheduler re-fetches whenever the snapshot is over ten minutes old, so her day-plan state carries a standing calendar error and ~6 failed fetches an hour, with `current()`'s behaviour on an errored snapshot undetermined — discovered only by the day-long § 6.3.6 watch after everything is deployed.
Costs: The second user's first day runs on an error-laden planner, and the fix lands as an unplanned Stage 5 patch to `tools/day_plan.py` or `tools/caldav.py` under walkthrough pressure — medium.

4. [§ 4.2 "Pre-build check", Stage 0.2] [scripts/metatron-backup.sh:83 tars `data/personas config/personas data/baselines data/conversations/metatron.db`]
Wrong: The plan's premise that the backup "backs up `data/`" is false — it pulls four named paths, none of which contains `data/accounts/`, and no stage adds it.
Fails: Stage 0.2 confirms the gap and then nothing in Stages 1–5 acts on it, so `accounts.json` (hashes, status, `cred_version`) is the one new persistent store outside every backup.
Costs: A VM rebuild (the 2026-07-31 precedent) deletes every account while keeping every persona's data; each user re-registers and waits for approval against data that is still theirs — medium.

5. [§ 4.6 "One instance per user, enforced", § 3.8, Stage 4.3] [core/scheduler.py:_record_fire 212-229; docs/INFRASTRUCTURE.md lines 63-82 old unit with `Restart=always`]
Wrong: "This is what makes the migration safe" is false — the hazard § 3.8 names is the old `metatron-scheduler.service` process plus `@mike`, and the old process runs pre-lock code and holds no lock, so `@mike` starts regardless.
Fails: Only the stated disable-before-enable order protects, and `Restart=always` on the old unit means a `stop` that is not `disable --now` revives it beside `@mike` with every job firing twice through check-then-write `_record_fire`.
Costs: Duplicate morning briefs, check-ins and spend for `mike` until someone notices, with the plan having told Mike the lock covers it — medium.

6. [§ 4.6 D2 "Proactive sessions hold", § 4.7 "Start", Stage 3.2] [scripts/new_persona.sh:76 writes `goals.yaml` as three empty lists; core/scheduler.py:_gates_block line 353]
Wrong: The hold gate's rule for a persona with no state file — "no state file + goals present = complete" — is undefined for exactly the persona it exists for, because `approve` provisions a `goals.yaml` that exists and is empty before she has signed in.
Fails: Read as file-exists, the gate marks an un-signed-in account complete and her scheduler (enabled at `approve`) fires the morning brief and three-hourly check-ins into an empty app; read as non-empty, `mike`-style existing personas with thin goals are held — the plan does not say which, and nothing creates a `not_started` state file at approval.
Costs: The outcome D2 was adopted to prevent (proactive sessions landing in an empty app, token spend on an unseen user) depends on an implementer's reading of "present" — medium.

7. [§ 4.3 "Verification reads the account store", Stage 1.2, Stage 1.11] [core/auth.py:33-37 header — imported by the SessionStart hook's system Python 3.9, the monitor's slim venv and the VM's system python3; deploy.sh:168-173 mint failure → `active=0`]
Wrong: The plan moves account-store verification (scrypt, `fcntl`, mtime cache) into `core/auth.py`'s token path without naming the interpreter constraint that file carries for its minting clients.
Fails: A module-level import of `core/accounts.py` with 3.10+ syntax or a venv-only dependency breaks `scripts/mint_token.py` and `scripts/sync_dev_backlog.py`, which fail silently by design: `deploy.sh` reads `active=0` and restarts the server mid-exchange, and the "account awaiting approval" line never appears.
Costs: Two silent harness failures, one of which force-restarts production under a live turn on every deploy — speculative.

8. [§ 4.4 "How Mike hears about a request" vs § 4.3 "`/monitor/*` — `admin` and `service` only"] [scripts/sync_dev_backlog.py:327-336 mints via `bearer_header` → `client_token`, which Stage 1.2 makes a `service` token]
Wrong: `GET /monitor/accounts` is specified as "admin-only" in § 4.4 while its only caller holds a `service` token under § 4.3's role model.
Fails: Built literally, the session-start read returns 403 and `sync_dev_backlog.py` swallows it, so the `· 1 account awaiting approval` line — the plan's sole mechanism for Mike learning a request exists — never fires.
Costs: Iva's request waits indefinitely with no signal, and the limit the plan states ("he sees it when a session opens") is silently false — low.

## VERIFY — 2026-10-26 (same reviewer, Fable)

3. CLOSED — [ROADMAP.md:924 Phase 7 gate row; archive/plans/phase5_to_future_roadmap_2026-06-10.md:727-749 Track F] § 2a names the gate and Track F against the real rows, tabulates the isolation gap honestly (auth/path layer only, one OS user per docs/INFRASTRUCTURE.md:50/71, no D2 encryption), § 4.9.5 writes it beside the Phase 7 row, D7 puts the override to Mike.

1. CLOSED — [core/orchestrator.py:enforce_pending_receipt 1972; _pending_tokens 1951; _pending_raised_since 1962; tools/confirm.py:pending 396] The three helpers are module-level and take `(persona)`/`(text, new_pending)` exactly as the pipeline uses them at 6583/6713, so the interview runner can apply them around `run_session` without touching the pipeline, and `finish_interview()`'s refusal has a real source in `confirm.pending(persona)` filtered on `action == "write_config"`.

2. CLOSED — [tools/caldav.py:_query_events 631-638; tools/day_plan.py:refresh_snapshot 318-331; scripts/new_persona.sh:81-92] Stage 1.13 now builds the not-connected path and 6.1.11 tests it; the unenumerated consumers of the new return shape (`read_calendar` 800-804, `scheduling.check_calendar_conflicts` 202-206, `obligations._link_calendar_if_exact` 2908-2911, `accountability` 557-562, `location` 334-336) all branch on `"error" in raw` and otherwise iterate `events`, so `{"events": [], "connected": false}` reads as nothing-to-do in every one without a code change.

4. CLOSED — [scripts/metatron-backup.sh:83 tar list] Stage 1.9 names the file and the path; the four-path premise is now stated correctly in § 4.2.

5. CLOSED — [core/scheduler.py:_record_fire 212-229; docs/INFRASTRUCTURE.md:63-82] The false "lock makes it safe" claim is gone, order is named as primary, and a `/proc` cmdline scan does see the pre-lock process (its ExecStart is `python core/scheduler.py --persona mike`); the `mask` step the revision added is a new defect, below.

6. CLOSED — [scripts/new_persona.sh:76 empty-list goals.yaml; core/scheduler.py:_gates_block 353; core/persona.py:persona_data_dir] The gate and the start both read `persona_data_dir(p)/interview/state.json` only, `approve` creates it, and `goals.yaml` is explicitly not consulted; `new_persona.sh` creates no data dir, so the state write is what first creates `data/personas/{p}/` — same OS user as the server and scheduler.

7. CLOSED — [core/auth.py:33-37, :212-226 client_token/bearer_header; deploy.sh:168-173] Minting stays on `issue_token` with no store access; the lazy import is confined to login and `user`-token verification, which run only in the server's 3.11 venv; 6.1.12 exercises the two system-Python callers.

8. CLOSED — [scripts/sync_dev_backlog.py:327-336 bearer_header → client_token] `/monitor/accounts` now admits `service`, matching its only caller's role.

### NEW

#### STRUCTURAL
none

#### LOCAL

1. [§ 4.4 "Provisioning on approve", `approve <u>` "idempotent — a re-run finishes a half-done approval", § 4.7 "Start"] [scripts/new_persona.sh:12,42-79 — create-only, "Nothing is overwritten"; the `interview/state.json` write is new and has no such guard]
Wrong: The revision makes `approve` write `interview/state.json` with `status: not_started` and keeps `approve` re-runnable, without saying the write is create-only.
Fails: A re-run after she has signed in — to finish a failed `systemctl enable`, or to re-admit a `disabled` user, for which no other command exists — rewrites an `active`/`paused`/`complete` file to `not_started`, and the next connection restarts the interview from its opening on top of the existing transcript.
Costs: Her interview position is lost and the opening repeats as though she were new, in the one path the plan tells Mike is safe to re-run — speculative.

2. [§ 4.6 "Migration", Stage 4.3 "`disable --now` and `mask` `metatron-scheduler`"] [docs/INFRASTRUCTURE.md:63 — the old unit file lives at `/etc/systemd/system/metatron-scheduler.service`]
Wrong: `systemctl mask` creates a `/dev/null` symlink at `/etc/systemd/system/<unit>` and refuses when a real unit file already occupies that path ("already exists"), which is where this unit lives; the premise that `Restart=always` revives a unit after `systemctl stop` is also false — `Restart=` never applies to an explicit stop.
Fails: Stage 4.3's `mask` errors on the VM mid-migration, leaving Mike to improvise (skip it, or delete the unit file by hand) on a step the plan presents as protective.
Costs: An unplanned decision during the one window the plan calls the migration's hazard, for a step that buys nothing even when it works — low.

## VERIFY 2 — 2026-10-26 (same reviewer, Fable)

N1. CLOSED — [scripts/new_persona.sh:12,42-92 — create-only, "Nothing is overwritten"] The `state.json`, profile and identity writes now carry the same create-only rule the script already enforces, `approve` is scoped to pending (or half-approved active) accounts and refuses `disabled`, re-admission is a separate `enable` that touches nothing under `data/personas/{p}/`, and 6.1.5 asserts an existing `active`/`paused`/`complete` file survives a re-run.

N2. CLOSED — [docs/INFRASTRUCTURE.md:63 unit at `/etc/systemd/system/metatron-scheduler.service`; deploy.sh:157 the only scripted `restart metatron-scheduler`] `disable --now` first removes the `multi-user.target.wants` symlink, moving the unit file out of `/etc/systemd/system/` plus `daemon-reload` makes the name unknown to systemd, so a stale `restart` fails "not found" rather than starting the lock-less process; the one scripted caller is rewritten to `'metatron-scheduler@*'` in the same deploy, and § 4.9.3 owns the runbook text.

### NEW

#### STRUCTURAL
none

#### LOCAL
none

## § 4.10 REVIEW — 2026-10-26 (same reviewer, Fable) — the Connections section added after Mike's walkthrough

### STRUCTURAL
none

### LOCAL

1. [§ 4.10 "Why in the app" and "The password goes nowhere else", § 6.1.13, D9] [scripts/metatron-backup.sh:83 tars `config/personas` into `backups/vm/metatron-vm-data-*.tgz` (RETAIN 7) and :105 hardlinks `metatron-vm-latest.tgz`; scripts/daily-backup.sh:63 feeds that file to Restic; .gitignore:216 keeps `backups/` out of git only]
Wrong: "Exactly one place: her own config file on the VM" is false — the backup chain the plan itself extends in Stage 1.9 copies her `caldav.yaml`/`email.yaml`, app password in clear, to Mike's Mac as a plaintext tarball (seven dated copies plus `latest`) and from there into the Restic archives, and § 6.1.13's assertion is scoped to `data/` and `config/` so it cannot see this.
Fails: The section's stated reason for the in-app route (keep the credential out of Mike's archives) is only half delivered, `Disconnect` blanks the live file but not the retained tarballs, and D9's consent sentence covers reading her mail on Vertex, not holding a credential to her whole Google account on the developer's laptop and drives.
Costs: A second person's full-mailbox-and-send-as credential replicated off the VM without her being told, in the one plan section written to prevent exactly that — high.

2. [§ 4.10 "error text never echoes it", Stage 2.7] [core/server.py — no `@app.exception_handler` for `RequestValidationError` anywhere; requirements.txt:21 fastapi==0.136.1, :62 pydantic==2.12.5]
Wrong: FastAPI's default 422 response on this version includes an `input` field carrying the submitted value — the whole body, password included, when a field is missing — so the claim holds for the handler's own errors and not for validation errors unless a handler is added.
Fails: A malformed connect (missing field, wrong type) returns her app password back inside the error JSON, which the Connections panel renders as the failure text on screen.
Costs: The credential displayed in an error bubble on her phone and in any screenshot she sends Mike to ask what went wrong — low.

## § 4.10 VERIFY — 2026-10-26 (same reviewer, Fable)

C1. CLOSED — [scripts/metatron-backup.sh:79-84 — the tar runs on the VM's GNU tar with `--exclude` globs already, so `*/credentials.yaml` is a one-line addition the file list can be asserted against; tools/caldav.py:81-85 and tools/mail.py:69-73 `_load_config` are the single loaders every password read goes through (caldav :651/:761/:1066/:1260/:1319, mail :229/:508/:677/:790), and tools/intake_email.py:44 imports mail's loader, so a loader-level merge of `credentials.yaml` reaches all nine sites and the intake adapter without touching them] The credential now has one home the backup provably skips, *Disconnect* deletes rather than blanks, and D9 tells her where it lives.

C2. CLOSED — [core/server.py — still no `@app.exception_handler(RequestValidationError)`; requirements.txt:21,62 FastAPI 0.136 / pydantic 2.12 default echoes `input`] An app-wide handler returning field names only is the standard FastAPI override and covers the three password-carrying routes; 6.1.13 asserts it on each.

### NEW

#### STRUCTURAL
none

#### LOCAL

1. [§ 4.10 item 1 "credentials.yaml (chmod 600)", § 4.4 provisioning on the VM] [.gitignore:190-207 — ignores `config/personas/mike.md`, `config/personas/mike/`, and per-file only `profile.yaml`, `scheduler.yaml`, `caldav.yaml`, `*.bak`; neither `credentials.yaml` nor `email.yaml` nor any non-`mike` account persona's `.md`/`prime_directive.md`/`mission.md`/`goals.yaml`]
Wrong: The plan introduces a new credential file class and provisions account personas under names the repo's ignore rules do not cover, so on the VM checkout `config/personas/iva/credentials.yaml` and her Tier 1–3 files are untracked-but-stageable, unlike every equivalent file of Mike's.
Fails: The VM never commits in normal operation, but a `git add -A`, `git stash` or "commit what's here" during a recovery (the 2026-07-31 rebuild was hand-driven) stages her Google credential and terminal values into the private repo's history, which the 2026-07-29 rewrite shows is expensive to undo.
Costs: One `git add` on the VM away from the credential and her Tier 1–2 content entering history, for want of the same two ignore lines `caldav.yaml` already has — low.

## C3 VERIFY — 2026-10-26 (same reviewer, Fable)

C3. CLOSED — [.gitignore:13,34-53,103-117 — the only negation rules are `.env.example`, `.claude/*` and `android/*`, none under `config/personas`; .gitignore:188 `data/personas/*/` with tracked `data/personas/danny_park/…` beneath it (SESSION.md:27-30 "a live gate run dirties TRACKED fixture-persona files") is this repo's existing proof that an ignore pattern leaves already-tracked files tracked; `git check-ignore` without `--no-index` never reports a tracked path as ignored, so § 6.1.14's two assertions test opposite outcomes correctly; scripts/qa_sweep.sh:99,137 and the hooks consult `git ls-files`/`git status`, neither of which the new patterns change] The seven patterns make every file `approve` and Connections create for an account persona untracked-and-ignored on the VM, synthetic fixtures stay tracked, and `git add -f` is the stated cost for a new fixture.

### NEW

#### STRUCTURAL
none

#### LOCAL
none

## § 4.11 REVIEW — 2026-10-27 (same reviewer, Fable) — her permission, given in the app

### STRUCTURAL

1. [§ 4.11 screen 1 / D11, § 4.11 "Enforced in code" ("written only by the two screens' routes, bound to her token"), § 4.2 account fields, § 4.4 approve, § 4.9.1] [core/auth.py:101 OPEN_PATHS — `/auth/register` joins `/auth/login` as unauthenticated; scripts/new_persona.sh:33-37 creates `config/personas/{p}/` only, and the plan's own `approve` is what first creates `data/personas/{p}/`; the § 4.2 field list carries no consent field]
Wrong: The sign-up permission is taken on an open route from someone who has no token and no persona directory, yet the only record store the plan defines is `data/personas/{p}/consents.json` written "bound to her token".
Fails: Screen 1's acceptance has nowhere to land at register time and nothing carries it to `approve`, so the base-configuration consent — Vertex processing and the developer's full access, the thing ruling 2 and D11 exist to record — is the one permission with no record, while § 4.9.1 cites "those records" as the evidence of her consent.
Costs: The § 0 amendment's evidence is missing for exactly the consent it was rewritten to point at, and the gap is in the account-store schema and the approve step, not in a screen — high.

### LOCAL

2. [§ 4.11 screen 3 "withdrawing the second stops tone profiling at once", § 6.1.15] [tools/tone.py:_extract:182 writes the profile onto the CRM contact via `write_contact(tone_shape=…)`; tools/tone.py:get_tone_shape:215-217 serves that stored field with no model call; tools/crm.py:1901 keeps `tone_shape` as a scalar contact field, and tone.py's own `_resolve:190` reads it back through `read_contact`; routing_cloud.yaml:284 grants Relationships `read_contact`, `search_contacts`, `list_contacts`]
Wrong: Gating `get_tone_shape()`/`_extract()` stops new extraction and the tool's own reply, but every profile already extracted lives on her contact records and is returned by `read_contact`/`search_contacts` to the same agent after she withdraws.
Fails: Relationships keeps drafting in a voice learned from correspondence she has withdrawn permission for, and § 6.1.15's "no model call" assertion passes while the derived data stays in use.
Costs: A withdrawal the app shows as effective is only half effective, for every contact profiled before it — medium.

3. [§ 4.11 "`mike` is seeded with records", Stage 2.10, Stage 4 steps 1-4, § 6.1.15] [plan lines 700-710 — Stage 4 has no data-write step; `data/personas/mike/` is VM-owned data that `git pull` does not carry (.claude/rules/personas.md § The VM owns live persona config); config/agents/relationships.md:163 "Before drafting to a saved contact, call `get_tone_shape`"]
Wrong: The seed is listed as if it were code (Stage 2.10, `core/consent.py`) but it is a record in Mike's VM data tree, and no stage writes it on the VM.
Fails: From the deploy until someone writes the file by hand, `get_tone_shape` refuses for `mike` on every draft to a saved contact, returning "not permitted" to an agent instructed to call it first — a silent downgrade that no test on the Mac can see, since `mike`'s tree is not there.
Costs: Mike's own tone profiling, the feature § 4.11 promises "nothing changes for him", breaks on deploy until an unlisted step is performed — medium.

4. [§ 4.11 "the one path to the `tone_profiler` model"] [tools/subagent.py:18-92 — `run_subagent(agent_name, …)` passes any name straight to `run_session` with no agent allowlist; config/modules/routing_cloud.yaml:147 routes `tone_profiler`; routing_cloud.yaml:81 grants `run_subagent` to the head layer and § the eight category routers]
Wrong: `tools/tone.py` is the one path that carries correspondence (`search_correspondence` is granted to no agent, tone.py:24), but it is not the one path to the model — `run_subagent("tone_profiler", …)` from any agent holding `run_subagent` reaches it with whatever text the caller passes, below the consent check.
Fails: The gate sits in a tool one layer above the dispatch it is meant to guard, so the fail-closed property § 4.11 claims ("enforced in Python") holds for her mailbox and not for the model.
Costs: Exposure is text already in the conversation rather than her correspondence, so the harm is small; the premise the enforcement design rests on is still false — low.

## § 4.11 VERIFY — 2026-10-27 (same reviewer, Fable)

P1. CLOSED — [core/auth.py:101 — `/auth/register` as an open path can carry a body field with no token; scripts/new_persona.sh:12,42-79 — create-only provisioning is the pattern `approve`'s copy into `consents.json` now follows] The sign-up permission has a home from the moment she submits (`accounts.json` `consents`), one copy-forward at `approve`, and a stated fallback if D11 is declined.

P2. CLOSED — [tools/tone.py:182 the only writer; tools/crm.py:1395 `read_contact`, :1443 `list_contacts`, :1631 `search_contacts` the only agent-facing readers; tools/crm_sweep.py:60,131 already exclude `tone_shape`; core/memory.py contains no contact or CRM reference, so FAISS never indexes a record; core/orchestrator.py's only `tone_shape`-adjacent lines are tool registration (1392/1568) and the confidentiality list (1696), so no context package carries it; the merge snapshot at crm.py:1895 and the archived loser can restore an old `tone_shape` via `unmerge_contacts`, but the read gate hides it while no current record exists] Deletion plus a record-gated read path closes every path an agent can reach; the raw file remains reachable only by Mike through `/monitor/file` and the backup, which ruling 2 already covers.

P3. PARTIAL — [deploy.sh:152 — `git pull origin main` inside `deploy.sh` is the only way a new script reaches the VM; scripts/accounts.py does not exist on the VM until that pull] The mechanism (an idempotent VM-side write of `data/personas/mike/consents.json`, checked at step 5) is right, but Stage 4 step 0 as written runs a script the VM does not yet have — see NEW 1.

P4. CLOSED — [tools/tone.py:151, tools/intake_extract.py:242, tools/day_plan.py:2237, tools/crm_sweep.py:653, tools/accountability.py:827 — all five reach their agent through `run_session`, never `run_subagent`; `config/agents/*.md` names none of the five; config/modules/routing_cloud.yaml:90,102,118,129,147 routes all five] A name-based refusal in `run_subagent` cannot touch any existing caller, and no agent file instructs a dispatch it would now lose.

### NEW

#### STRUCTURAL
none

#### LOCAL

1. [§ 4.11 "written on the VM by a command before the deploy", Stage 4 step 0 "before the deploy"] [deploy.sh:152 `git pull origin main` is where the VM first obtains `scripts/accounts.py`; deploy.sh:157,180 restart both units in the same run]
Wrong: Step 0 invokes `scripts/accounts.py seed-consent mike` on the VM before the only step that puts that script on the VM.
Fails: Run literally, step 0 fails "No such file"; Mike either pulls by hand first (which the plan does not say, and which is harmless only because the running processes keep old code until the restart) or proceeds to `deploy.sh`, at which point the new server starts refusing `get_tone_shape` for `mike` until he returns to run the seed — the exact window step 0 was added to remove.
Costs: A deploy-day stumble on the step that exists to prevent a deploy-day regression, resolved by an unstated manual pull or by accepting the window — low.

## P3-N1 VERIFY — 2026-10-27 (same reviewer, Fable)

P3-N1. PARTIAL — [deploy.sh:107-108 `git push origin main` is the deploy path's only push and it runs inside `deploy.sh`, after step 0; deploy.sh:152 `git pull origin main` exits 0 on an already-current tree, :132-150 is the only preflight and reads `.env` not tree state, :154 `pip install` installs nothing the seed needs (plan: stdlib-only), :218-264 reports `match` when VM HEAD equals the pushed SHA] Every `deploy.sh` concern the coordinator raised is clean — the no-op pull, the preflight and the assertion all tolerate a VM that is already current — but step 0's pull fetches whatever GitHub `main` holds at that moment, and nothing before step 0 puts the build's commits there; see NEW 1.

### NEW

#### STRUCTURAL
none

#### LOCAL

1. [Stage 4 step 0 "`git pull origin main` … the script does not exist on the VM until then", § 5 "Built in a git worktree off `main`"] [deploy.sh:107-108 — the push to GitHub happens inside `deploy.sh`, i.e. at step 2; .claude/commands/archive.md pushes but "never deploys" and is not a Stage 4 step]
Wrong: Step 0 pulls `origin main` on the VM before anything in the plan has pushed the merged build to `origin main`, so the pull that exists to deliver `scripts/accounts.py` delivers the previous `main` instead.
Fails: Run in the plan's order after the Red session, step 0 reports "Already up to date" and then "No such file" for `scripts/accounts.py` — the identical failure P3-N1 was meant to remove, one commit earlier — unless Mike happens to have pushed by another route first, which the plan neither states nor checks.
Costs: The seed-before-restart ordering only works by accident of whether `/archive` or a manual push preceded Stage 4; otherwise the `get_tone_shape` refusal window reopens on deploy day — low.

## P3-N2 VERIFY — 2026-10-27 (same reviewer, Fable)

P3-N2. CLOSED — [deploy.sh:108 `git push origin main` under `set -e` exits 0 with "Everything up-to-date" when nothing is to push; :112 `EXPECTED_SHA=$(git rev-parse HEAD)` is taken from the Mac's HEAD regardless of whether the push moved anything; :152 the VM pull exits 0 on a current tree; :218-264 the assertion is an ancestry test that reports `match` when VM HEAD equals that SHA; nothing in the script counts commits pushed or assumes it performed the first push] The three ordered steps make the seed run against the exact commit `deploy.sh` will then restart onto, and every later step of `deploy.sh` degrades to a no-op that still passes its own check.

### NEW

#### STRUCTURAL
none

#### LOCAL
none

## § 4.12 REVIEW — 2026-10-27 (same reviewer, Fable) — memory monitoring, the diagnosis, CPU PyTorch, the voice helper

### STRUCTURAL

1. [§ 3.12 "scheduler ~69 MB idle", § 4.12 "What it buys", § 7 Run and persistence tables ("~69 MB idle each … more while an in-process agent job runs"), D10 (c) "no upgrade is needed on this evidence", § 6.3a.3] [core/scheduler.py:470-474 — non-coordinator jobs (`weekly_physical_review`, `weekly_pattern_miner`, config/templates/scheduler.yaml:80-94) run `run_session` in the scheduler process; tools/logger.py:374-384 and tools/diarist.py:96 hand `index_entry` to core/background.py:25, a thread pool inside whichever process called `write_log`; core/memory.py:40-44 loads `SentenceTransformer` on first use and never releases it; routing_cloud.yaml:170 grants `pattern_miner` `score_against_anchors`/`shuffled_null_score`, whose tools/baselines.py:44-48 holds a second, separate copy of the same model; tools/wisdom.py:725 a third entry point]
Wrong: The 69 MB scheduler is a fresh-process figure — measured 2026-10-26 after that day's deploy restarts, before any in-process writing job — and the plan's whole memory arithmetic, the "levels off" conclusion and D10's "no upgrade needed" rest on it, when the first `write_log` from a weekly review loads the embedder (§ 3.12's own 787→903 MB standalone figure) into each scheduler for the life of the process, and a pattern-miner run can load it twice.
Fails: Two per-user schedulers that now restart only on deploy settle at ~0.8–1.0 GB each after their first Sunday, so with the server at the estimated 1.0–1.2 GB and the voice helper at 1.5 GB when someone speaks the 4 GB machine is back at the 3.5 GB anonymous-memory line the kills happened at — while § 6.3a's pass criterion watches only the server "levelling off", so the measurement the plan says will catch a wrong estimate is pointed at the one process this does not affect.
Costs: D10's conclusion (c) is reached on a premise that is false for the deployment this plan creates, and the next OOM kill lands after the second user is live and after the window in which an upgrade or a design change (embedding in one process) was cheap — high.

### LOCAL

2. [§ 4.12.2 items 1-2 "the server stops loading Kokoro at startup … on the first spoken reply the server starts a helper", § 6.1.17 "the server starts with no Kokoro loaded" with "Kokoro stubbed"] [core/server.py:1561-1566 `_kokoro_available()` is `import kokoro`; :1641 `/tts` calls it in the server process on every request before deciding the engine; :1573-1574 that import is the ~7 s the plan cites]
Wrong: The plan removes the warm-up's `_load_kokoro` but says nothing about the engine-selection check, which imports `kokoro` (and everything it pulls in beyond the torch the embedder already holds) into the server on the first `/tts`, so "no Kokoro in the server" holds only for the pipeline weights, not for the import.
Fails: The first spoken reply still grows the server by whatever `import kokoro` costs and the 7 s it takes, in the process the helper exists to protect, and a test with Kokoro stubbed cannot see it because the stub replaces the import under test.
Costs: Part of the memory the helper was built to move stays in the server, unmeasured and un-asserted, on a path the plan describes as costing nothing when voice is unused — medium.

## § 4.12 VERIFY — 2026-10-27 (same reviewer, Fable)

M1. PARTIAL — [core/scheduler.py:470-474 the in-process branch the plan removes; core/memory.py:40-44 the one loader `index_entry`/`search_memory` and tools/wisdom.py:725 go through, so one guard covers all three; `_resolve_knowledge` is called only at core/orchestrator.py:6801 and :7052 (pipeline), never in `_run_single_agent`; the four function-job agents that still run `run_session` in-process — tools/accountability.py:827, tools/crm_sweep.py:653, tools/day_plan.py:2237, tools/intake_extract.py:242 — are bare/specialist runs with `allowed_tools: []` (routing_cloud.yaml:90,102,118,129) and none of their modules calls `write_log`/`write_journal`/`search_memory`, so they load no model; core/build/index.py:51-56 is a second unguarded loader but reachable only via `core/build/policy.resolve`, which nothing calls; `/session` already owns a trace and runs `_spend_gate` for a non-coordinator agent (core/orchestrator.py:7203-7212) with `history=None` (server.py:664), and `proactive` is a `run_session` parameter the route can pass (:7168)] The embedder leaves the scheduler on every path that exists, and `/session` carries a scheduled single-agent session correctly for tracing, spend and history — but the route logs every agent's run as a conversation (NEW 1), which the plan does not address.

M2. CLOSED — [core/server.py:1561-1566 the `import kokoro` check; `importlib.util.find_spec` reads package metadata without executing it; :1569-1588 `_get_kokoro` moves with the pipeline into the helper] The server's module table stays free of `kokoro`, and the test's stub sits where the import now is.

### NEW

#### STRUCTURAL
none

#### LOCAL

1. [§ 4.12.3 item 1 "non-coordinator agents go to the existing `/session` route", Stage 1.17, Stage 3.2] [core/server.py:669 `/session` calls `_log_conversation(req.input, response, agent, persona)` for every agent, with `proactive` defaulting to False; :281-311 appends it to `data/personas/{p}/conversations/{day}.jsonl` as a sequenced exchange; tools/crm_sweep.py:389-406 reads every row of that file as "[user] … [assistant] …" with no `agent` or `proactive` filter; tools/day_plan.py:2087 filters on `proactive` only]
Wrong: Moving `weekly_pattern_miner`, `weekly_physical_review` and the like onto `/session` turns each run's prompt and multi-thousand-token report into a conversation record, which the in-process path never produced, and the plan adds `proactive` to the request without saying it reaches `_log_conversation` or that these runs should be logged at all.
Fails: The next night's CRM sweep ingests a pattern-miner analysis and a physical-health review as things the user said and the assistant replied, proposes contact updates quoting them as evidence, and The Book's conversation view shows the analysis as an exchange — for both users, every week.
Costs: Derived analysis re-enters the record as primary evidence through a sweep whose whole design is provenance by quote, and the ledger rows it files are append-only — medium.

## M1-N1 VERIFY — 2026-10-27 (same reviewer, Fable)

M1-N1. CLOSED — [core/scheduler.py:505-514 — the single-agent branch's only use of the response is `_dispatch(notification, title, response)`, with errors going to `_log_error`/`_notify_terminal`, so an HTTP call that returns the same string preserves the notification path exactly; the run's own outputs (pattern_miner's `write_insight_report`, physical_health's `write_log`) are tool writes against `persona_data_dir()` on the same VM, identical from the server process; core/orchestrator.py:7187-7229 `run_session` with `proactive=True` owns the trace and spend gate as the in-process call did; server.py:281-311 `_log_conversation` is called only by the user-facing routes, so an internal route that omits it leaves the conversation file untouched; uvicorn imposes no server-side request timeout and the route's `run_in_executor` thread is not bounded, so the response of a multi-minute pattern-miner run survives as long as the scheduler's client timeout is set as the plan states] The result still reaches the scheduler for dispatch, nothing else ever consumed it, and the conversation record the previous shape would have created is not written.

### NEW

#### STRUCTURAL
none

#### LOCAL
none
