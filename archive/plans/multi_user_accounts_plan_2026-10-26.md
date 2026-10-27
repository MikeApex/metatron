# Second user — per-user accounts, sign-up with developer approval, a scheduler per user, and the first interview in the app

*Plan, 2026-10-26, revised 2026-10-27. Author: Opus 5.5 (planning session). Status: **APPROVED by
Mike 2026-10-27; Fable review resolved — 22 findings across 13 rounds, all closed** (verbatim:
`archive/plans/adversarial_review_multi_user_accounts_plan_2026-10-26.md`). Decided: D1–D7, D9–D11,
D13–D14. Open: D8 (her Google account — her choice at the walkthrough), D12 (Mike's own app
passwords — recommendation: leave), D14's idle timeout (recommended 10 min).***

> **✅ D5's condition is met — day-planner Stage B landed 2026-10-27** (`9f2eeac`, first switch on
> in `d38efc7`): `goals_interviewer.md` carries the Shape of the day block (`:93`), its Phase 8
> `set_day_shape` line (`:232`) and Tools entry (`:249`); both routing files grant it. **Stage 3.4
> therefore builds on that text and 3.5 adds only `pause_interview`/`finish_interview`** (§ 10).
> Stage B's remaining flag flips are config in `config/modules/day_plan.yaml`, which this build does
> not touch.

**Reading order:** § 1 (what changes for a user), § 2 (Mike's rulings — binding), § 3 (what the
survey found — the facts that shape everything after), then § 4 design, § 5 stages.

---

## 1. The need — what a new user can do when this is done

A person Mike invites (first: **Iva**) installs the Android app, joins the tailnet, and:

1. **Creates her own account in the app** — a username and a password she chose. The app tells her
   the request is waiting for approval.
2. **Mike approves her in a Claude Code chat** ("approve iva"). Nothing else is needed from him —
   no file copying, no unit editing by hand.
3. **She signs in and the app opens straight into a first conversation** that covers what she is
   working toward (goals, mission, prime directive, a remembered good period) **and the shape of her
   day** (when it starts and ends, when each kind of work goes, protected time, meals, routines,
   travel, location sharing) — one interview, not two. She can stop at any point and pick it up
   later from a button; nothing she said is lost.
4. **From then on she has the same product Mike has** — her own history, tasks, plan and check-ins,
   on her own schedule — and **can see nothing of anyone else's.** Her password opens only her.

What changes for **Mike**: he signs in with a typed username (`mike`) and his existing password
instead of picking from a dropdown; the same password still opens every test persona; The Book
still shows every user (his ruling). His phone and browser ask him to sign in once after the
deploy. Nothing else he sees changes.

---

## 2. Mike's rulings — binding (2026-10-26)

1. **Login is per user.** The existing password stays for `mike` and the test personas. The app
   prompts for a new user/password/account. **Verification is a human on the development end —
   Mike, through a Claude Code chat.**
2. **The privacy ruling extends to the second user.** *"She is aware of the configuration and will
   be using incomplete data"* and *"She understands I have full access."* Recorded as an amendment
   to `ROADMAP.md` § Section 0 in this build (§ 4.9).
3. **Tailscale stays** for now. The Cloudflare Tunnel item (`ROADMAP.md` § 5A) is unchanged and not
   in this plan; see § 9 for one thing to know before it is built.
4. **She creates her account herself**, through the app, approved as in 1.
5. **A scheduler for each user.** Family mode will later bring batched scheduling for a group and
   for individuals within it — so nothing here should make "one persona = one sealed world" a
   property a group layer cannot sit above.
6. **The Book shows Mike all users.** Monitor access is the admin's, across every persona.
7. **Cost understood and approved;** the billing limits are adjusted once she begins actual use.
8. **The first interview is built in the app, goals and scheduling merged into one.**
9. Iva installing today is off. The Tailscale walkthrough waits until this is built.

### 2a. This is ahead of the Phase 7 gate — stated, not implied (review S3)

`ROADMAP.md` § Section 3 gates **multi-user deployment** on Phase 6 + 6A + 6B close and a user
research session, and Track F (static plan `:727-749`) asks for that session *before building*. None
of those has happened. Admitting Iva is therefore **a test user ahead of the gate by Mike's ruling,
not Phase 7.** What she gets is **not Phase-7-grade isolation**, and the record must say so:

| Track F asks for | What this plan gives | Gap, accepted by D7 |
|---|---|---|
| Per-user access-controlled paths | per-user credentials, every request bound to its user, per-user data trees (already true), admin-only cross-user views | isolation is at the auth and path layer only — one OS user, one process, one file tree |
| Per-user key compromise leaves others encrypted | nothing — `age` encryption (D2) is not built for anyone | a server compromise exposes both users, as it exposes Mike today |
| Identifiability threshold before cloud dispatch | nothing — both users' sensitive work runs on the same Vertex path under § 0 | covered by the § 0 amendment (her informed consent), not by a threshold |
| A user research session first | Iva's own use, with Mike watching | she *is* the first research subject; the formal session is still owed before Phase 7 |
| Self-service onboarding, no developer involvement | self-service sign-up and interview; **approval by Mike by design** (ruling 1) | approval is deliberate, not a gap |

§ 4.9 records this in `ROADMAP.md` § Section 3 beside the Phase 7 row, so the roadmap does not
contradict the deployment and no later session mistakes this for Phase 7.

---

## 3. What the survey found — today's single-user assumptions, by what a user would see

Every item below was verified in the code on 2026-10-26 (two read-only sweeps plus direct reads;
references are `file:line` on `main` at `1ee1dc2`). **Each is invisible with one user and a defect
with two.**

1. **Whoever has the password can be anyone.** `core/auth.py:152-174` — a token is `<expiry>.<hmac>`
   and carries no identity. Every request names its own persona (query or body) and the server
   trusts it. The app's login sends `{password}` only (`static/index.html:1018-1042`); the persona
   comes from a hard-coded dropdown (`:804-819`).
2. **A request that names no user is served as Mike.** `DEFAULT_PERSONA` = `SERVER_PERSONA` = `mike`
   (`core/server.py:60`, set by `--persona mike` at `:2301-2307`); seventeen routes use
   `x or DEFAULT_PERSONA`. Both systemd units also set `METATRON_PERSONA_STRICT=0` +
   `METATRON_PERSONA_FALLBACK=mike`, so an unscoped lookup anywhere resolves to Mike, silently
   (`core/persona.py:172-176`).
3. **One user's identity can leak to another's request.** `persona_scope()` mirrors the persona into
   the **process-wide** environment (`core/persona.py:199-211`), and `resolve_persona()` reads that
   environment after the thread-local. So unscoped code on one thread — `/feedback`
   (`server.py:1520`) and `/tts` (`:1612`) have no persona at all — resolves to whichever user
   another thread is serving at that moment. Feedback would be filed, and the reply language read,
   for the wrong person. The mirror exists "so that code not yet converted to `resolve_persona()`
   still sees the right persona" — **no runtime code still reads the variable directly** (only the
   `tools/analytics.py:323` CLI default and a one-off migration script).
4. **Mike's notifications would reach her browser.** Push subscriptions are one global list with no
   owner (`core/push.py:27, 40-58`); `/subscribe` takes no persona (`server.py:1504`); the
   scheduler's `_notify_push` sends to every subscription (`core/scheduler.py:402-407`). The APK has
   no push at all (`initPush` stops at "push-unsupported"), but if Iva ever opens the web app, every
   one of Mike's check-ins arrives on her device, with its text.
5. **Everyone's voice recordings land in one folder.** `/transcribe` writes audio and transcripts to
   global `data/audio/{date}/` regardless of user (`server.py:1682-1730`).
6. **The Book's endpoints open for any signed-in user.** All nine `/monitor/*` routes read any
   persona's conversations, traces and any file under `data/` (`server.py:1911-2281`) — including
   Iva's token reading Mike's. Mike's ruling 6 keeps them **his**; today nothing distinguishes him.
7. **The WebSocket takes its user from the URL** (`/ws?persona=`, `server.py:793, 819-820`), not
   from the credential, and the send frame carries none.
8. **Two schedulers would trip over each other** (the second sweep):
   - nothing stops two processes running for the **same** user — every job would fire twice
     (`_record_fire` and the one-off pop are check-then-write, no lock). This is exactly the state a
     careless unit migration produces (old `metatron-scheduler.service` + new `@mike`);
   - `build_tick` rewrites the repo-tracked `config/build/registry.yaml` unlocked once any
     capability has landed (no-op today — nothing has);
   - the spend meter's day file is read-modify-write under a **thread** lock only
     (`core/spend_guard.py:124, 296-340`) — server and scheduler already both write it, a third
     writer makes lost updates likelier, and **a guard that under-counts is read as safety**;
   - every scheduler labels its Vertex caches `metatron:{host}:scheduler` with no persona
     (`core/orchestrator.py:3356-3373`), so a starting scheduler's orphan sweep can delete a
     sibling's near-expiry caches (one metered re-creation each).
9. **The scheduler serves one persona per process already** (`--persona` required,
   `scheduler.py:1013-1018`) — its "one daemon serves every persona" comment (`:40-41`) is stale.
   Every per-persona maintenance job is genuinely per-persona in what it writes; their shared side
   effects are model spend and the global diagnostics files.
10. **There is no in-app interview.** The app offers only the Coordinator pipeline
    (`index.html:854`), whose history is five turns (`server.py:664`). The goals interview has only
    ever run from the CLI (`run_interactive`, in-memory history). A single-agent run gets **no output
    filter** — `filter_output()` acts on the Synthesizer only (`orchestrator.py:2100-2105`) — and
    `goals_interviewer.md` has **no Confidentiality section** and **no crisis handling** (the
    constitution has none either; it lives in `mental_wellbeing.md` → Synthesizer, a path the
    interview would bypass).
11. **The day-shape half of the interview is already drafted** — day planner Stage B § E
    (`archive/handoffs/2026-10-24-day-planner-stage-b-prompt.md:155-180`) adds a "Shape of the day"
    block to the interviewer's Phase 1, a `set_day_shape` write-back to Phase 8, and the grant.
    `set_day_shape` itself is built and registered, granted to no one (Stage A).
12. **A second scheduler is small; the VM's memory is not healthy, and nobody is told when it
    fails.** Measured on the VM 2026-10-26 midday: server RSS ~3.0 GB, scheduler ~69 MB idle,
    803 MB available, swap 89 MB used of 2 GB. **But the watchdog's own log (read 2026-10-27) shows
    7,875 low-memory warnings since 08-18 — ~260 a day, i.e. below 500 MB almost all day, through
    early October — a minimum of 54 MB available since 10-20, 148–249 MB on the evening of 10-26,
    and three OOM kills: 08-18, 10-15 and 10-22.** The pattern: after a restart memory climbs for
    days until the kernel kills the server; systemd restarts it in seconds, so it looks like
    nothing happened — except that a reply in progress at that moment is lost. **With two users, a
    kill drops whichever of them is mid-reply, and her scheduler adds to the load.** D10 is the
    decision this forces.

    **Diagnosis so far (2026-10-27, read-only on the live server):** no child or stray processes;
    memory is flat while idle (2,055 MB unchanged across a quiet stretch). After a restart the
    server reaches **~2.03 GB once its models load** (embedder, Whisper, Kokoro, PyTorch) — of
    which **169 MB is NVIDIA CUDA library code on a VM with no GPU** (the GPU build of PyTorch is
    installed). Then **six Kokoro TTS calls took it from 2.03 GB to 2.73 GB (~115 MB each) with no
    other activity** — the strongest suspect for the growth: PyTorch on glibc keeping each
    synthesis's working memory rather than returning it. Only two kills this month were OOM
    (10-15, 10-22, both at 3.5–3.6 GB anonymous memory); the 10-24 kill and today's restarts were
    deploys. TTS requests also queue on one worker (`_TTS_EXECUTOR`, `max_workers=1`): one test
    request waited over two minutes behind five others.

    **Isolated tests (2026-10-27, Mike approved; each model loaded in its own capped,
    kill-first process on the VM, the server untouched, the test files removed after):**

    | Model (as the server loads it) | Loaded | Under use | `malloc_trim` |
    |---|---|---|---|
    | **Kokoro TTS** (`KPipeline(lang_code="a")`) | **1,503 MB** | the **first** longer reply (≤160 words) pushed it past a 1.9 GB cap — **over 440 MB more** — and it was killed by its own cap | — |
    | Embedder (`all-MiniLM-L6-v2`) | 787 MB | 903 MB after 20 calls, then **flat** to 40 | 859 MB |
    | Whisper (`base.en`) | 662 MB | 752 MB after 5 calls, then **flat** to 20 | 679 MB |

    *(Each standalone figure includes its own Python and PyTorch runtime, which the server shares
    across models, so they do not add up to the server's 2.03 GB.)* **Conclusion: the voice model is
    the growth, and most of the weight.** The embedder and Whisper rise a little and level off;
    Kokoro carries the largest load and a per-reply peak that a 4 GB machine cannot absorb
    repeatedly. Removing it from the server process leaves an estimated **~1.0–1.2 GB** server
    (the 2.03 GB baseline less Kokoro's share, less the 169 MB of CUDA code) that **levels off**
    instead of climbing to an OOM kill at 3.5 GB. Estimated, not measured — § 6.3 measures it
    after the change. Fix: § 4.12. (The memory
    watchdog — `scripts/vm_memory_watch.py`, a 5-minute systemd timer added after the 2026-08-15 OOM
    kill — **records** low memory and OOM kills to journald and `data/system/memory_alerts.jsonl`,
    but **nothing reads that file**, and its one active alert, a push on an OOM kill, posts to
    `http://127.0.0.1:8001/push`, a route that does not exist on a server that serves https —
    `:45, 117-125`. So memory trouble is recorded and **nobody is told**. Noted, not filed.)
13. **Checked and clear: the prompt cache cannot cross users.** Its key is a hash of model + full
    system prompt + tool names (`orchestrator.py:3621-3622`), so different personal context makes a
    different cache.

---

## 4. Design

### 4.1 Three kinds of credential

| Credential | Who | Gets a token that… | Opens |
|---|---|---|---|
| **Account password** (new, per user) | Iva and every future user | is bound to that one user | that user only. Never `/monitor/*` |
| **Admin password** (`METATRON_AUTH_PASSWORD`, unchanged) | Mike | is bound to the persona he signs in as — `mike` or any test persona | that persona, **plus** `/monitor/*` for all users |
| **Service token** (minted locally from the same secret, as today) | the scheduler's WS client, `deploy.sh`, The Book, `sync_dev_backlog.py`, `vm_read.py`, `build_board.py`, `mint_token.py` | names a persona per request | any persona it names, plus `/monitor/*` |

- **The admin password cannot sign in as an account user.** Mike reads everything of Iva's through
  The Book (ruling 6) but cannot send messages *as* her — that would put his words into her history
  and her plan. *(Decision D1 — recommended.)*
- Switching persona in the app stays what it is today: tap the chip, sign in again.

### 4.2 The account store

`data/accounts/accounts.json` on the VM — outside `data/personas/`, chmod 600, written atomically
under an `fcntl` lock (the server registers and the VM-side approval command approves, in different
processes). One entry per account:

`username, display_name, status (pending | active | rejected | disabled), password_hash (scrypt,
stdlib hashlib, per-entry salt), cred_version (int), timezone, created_at, decided_at, decided_by,
note, consents` — `consents` holds the sign-up permission (§ 4.11.1) from the moment she submits,
because at that point she has no token and no persona directory to record it in.

- **Password hashing:** `hashlib.scrypt` (stdlib — no new dependency), parameters stated in code.
- **`cred_version`** is bumped on password reset, disable and reject; every token carries it, so
  either revokes that user's tokens at once without touching anyone else's.
- **Backed up (review L4).** `scripts/metatron-backup.sh:83` tars four named paths —
  `data/personas config/personas data/baselines data/conversations/metatron.db` — **not `data/`**, so
  the store would be the one persistent file outside every backup. Stage 1.9 adds `data/accounts` to
  that list; a VM rebuild must not delete every account while keeping every user's data.
- **Interpreter constraint (review L7).** `core/auth.py` is imported by the SessionStart hook's
  system Python 3.9, The Book's slim venv and the VM's system `python3` (`core/auth.py:33-37`).
  `core/accounts.py` is therefore **stdlib-only, 3.9-compatible, `from __future__ import
  annotations`**, and `core/auth.py` imports it **lazily, inside login and `user`-token verification
  only** — minting a `service` token never touches it. § 6.1 runs `scripts/mint_token.py` and
  `scripts/sync_dev_backlog.py` under `/usr/bin/python3` to prove it: a mint failure is silent by
  design, and `deploy.sh` reads it as "no active streams" and restarts the server mid-turn.

### 4.3 Tokens and how the server binds a request to its user

- **Format v2:** `v2.<persona | *>.<role>.<cred_version>.<expiry>.<hmac>`, role ∈ `user | admin |
  service`. Signing key unchanged (derived from the admin password) — so rotating the admin password
  still revokes everything, as now. Verification reads the account store (cached by mtime) for
  `user` tokens: unknown, non-active, or stale `cred_version` → 401.
- **v1 tokens are rejected after deploy.** Only Mike's devices and local scripts hold them; scripts
  mint v2 from the same commit. Mike signs in once on phone and browser. *(Between the Mac commit and
  the VM deploy, Mac-side scripts mint v2 the old server refuses — `sync_dev_backlog.py` fails
  silently for that window, by design.)*
- **One helper decides every request's user** — `request.state.identity` set by the existing
  middleware, and one function every route calls instead of `x or DEFAULT_PERSONA`:
  - `user`/`admin` token → its bound persona. A request that **names a different persona → 403**.
  - `service` token → the persona the request names; **none named → 400**, never a default.
- **`DEFAULT_PERSONA` and the `"__default__"` sentinel leave request handling** (`server.py:664, 704,
  820, 1779, 1811`). `--persona` on the server stops meaning "serve unnamed requests as this user";
  it remains for CLI/dev use only.
- **The WebSocket** (`server.py:792+`) determines its user **after** the auth frame, from the token
  (`service` tokens: from `?persona=`). The connection manager, history, catch-up and broadcast all
  key on that.
- **Routes with no persona today** — `/feedback`, `/tts`, `/subscribe`, `/push/test`, `/transcribe` —
  take the bound user. `/transcribe` writes to `data/personas/{p}/audio/` from now on; Mike's
  existing global `data/audio/` is left where it is (nothing is deleted — it is his). *Pre-build
  check: grep for readers of `data/audio/` (cleanup jobs, The Book) and move them with it.*
- **`/monitor/*`** — `admin` and `service` only; a `user` token gets 403. The Book is unchanged (it
  uses a service token) and shows every user, Iva included.
- **Push:** each subscription records its persona; `send_push(…, persona)` sends only to that
  persona's subscriptions; `scheduler._notify_push` passes the persona it already has. Existing
  subscriptions are all Mike's and are migrated to `mike`.
- **`persona_scope()` stops mirroring into the environment** (`core/persona.py`, Red). With the
  mirror gone and the server unit at `STRICT=1` with no fallback, **an unscoped lookup in the server
  raises instead of quietly becoming Mike** — loud, attributable, and never another user's data.
  - *Pre-build check — the audit log tells us exactly what still relies on the fallback today:*
    `data/diagnostics/persona_audit.jsonl` on the VM records every fallback resolution with its call
    site. Read it (via `/monitor/file`) before flipping, and convert every caller it names. A path
    that would start raising must be found here, not in production.

### 4.4 Sign-up and approval

**Sign-up** — `POST /auth/register` (an open path, like `/auth/login`):
`{username, display_name, password, timezone}`, timezone filled by the app from the device
(`Intl.DateTimeFormat().resolvedOptions().timeZone`).

- **Username** must pass `validate_persona_name()` (it becomes her folder name), must not be an
  existing persona identity, data directory or account, and must not be reserved (`admin, root,
  system, service, default, mike`, anything starting `test`). The app says plainly what is allowed.
- **Password** ≥ 10 characters.
- **Abuse limits, built now so the later public tunnel needs no redesign:** at most 3 pending
  requests at once; at most 10 sign-up attempts an hour per server process; the same escalating
  delay `/auth/login` already uses.
- **Responses:** created → "Request sent. You can sign in once it's approved." · taken → "That
  name is taken" *(reveals that a name exists — acceptable on a tailnet; revisit before any public
  endpoint, D4)* · limits → "Try again later".

**Sign-in while waiting** — only after a correct password: pending → "Your account is waiting for
approval." · rejected → "This request wasn't approved." · disabled → "This account is switched off."
A wrong password always reads "Incorrect username or password" — no status leaks without it.

**Approval — `scripts/accounts.py`, run on the VM** (Claude Code runs it over
`gcloud compute ssh … --tunnel-through-iap`, the path `deploy.sh` already uses). Writing on the VM
over SSH, not over HTTP, keeps account-changing endpoints off the server entirely — fewer things to
protect when it is ever reachable from outside.

| Command | Does |
|---|---|
| `list` | every account and its status, never a hash |
| `approve <u>` | **pending accounts only** (or an `active` one whose approval half-failed): provision the user (below) → `active` → `sudo systemctl enable --now metatron-scheduler@<u>`; reports each step; **idempotent** — a re-run only finishes the steps still missing and **never overwrites a file that exists** (verify N1) |
| `reject <u>` | `rejected`, bump `cred_version` |
| `disable <u>` | `disabled`, bump `cred_version`, `systemctl disable --now` her scheduler. **Data is not deleted** (archive rule) |
| `enable <u>` | re-admits a `disabled` user: `active` + scheduler on. Touches nothing in her persona — her interview resumes where it stood |
| `reset-password <u>` | sets a generated temporary password, bumps `cred_version`, prints it once for Mike to pass on *(D3)* |

**Provisioning on approve:** run `scripts/new_persona.sh <u>` on the VM — the VM owns live persona
config, so it is created where it lives and never on the Mac — then write `profile.yaml` `name` and
`timezone` from the account, the identity file's address line from `display_name`, and
**`interview/state.json` with `status: not_started`** (§ 4.7 — the hold gate and the interview start
both read this file and nothing else). **Every provisioning write is create-only**, as
`new_persona.sh` already is (`:12`, "Nothing is overwritten"): an existing `state.json`, profile or
identity file is left exactly as it is, so re-running `approve` can never reset an interview that
has started (verify N1). The integration templates are copied as today
(`caldav.yaml` and `email.yaml` with `enabled: false`); § 4.8 makes "not enabled" read as *not
connected* rather than as a failure. The persona's `scheduler.yaml` comes from the template with
`build_tick` disabled (§ 4.6).
*Pre-build check: diff `config/templates/scheduler.yaml` against Mike's live file (in
`backups/vm/`) — the template should carry design improvements made since, minus his personal jobs
(`manny_school`), so she does not inherit a stale baseline.*

**How Mike hears about a request:** the session-start backlog line gains
`· 1 account awaiting approval`, read from a new `GET /monitor/accounts` — **`admin` and `service`,
like every `/monitor/*` route** (review L8: its only caller, `sync_dev_backlog.py`, holds a
`service` token; an admin-only route would 403 silently and the line would never fire) — returning
usernames, display names, status and dates, never hashes. `sync_dev_backlog.py` already contacts the VM each
session start, so this costs nothing new. Limit stated: he sees it when a Claude Code session opens.

### 4.5 The app

- **Login screen:** username (lowercased, no autocorrect) + password + *Sign in*; a *Create an
  account* link opens username / display name / password / confirm. The hard-coded persona dropdown
  goes — it would show a new user `mike` and every test name. The last username is remembered.
- **Switching persona** resets the WS catch-up position (`lastSeenId`, `index.html:1523`) — today
  the first catch-up after a switch uses the previous persona's id.
- **Interview chips** (§ 4.7): *Finish later* while the interview is active; *Continue setting up*
  while it is paused.
- **Needs an APK rebuild by Mike.** The web app picks it up from the server at once.

### 4.6 A scheduler for each user

- **A systemd template unit, `metatron-scheduler@.service`** — one process per approved user,
  started by `approve`, stopped by `disable`. Restarts, logs (`journalctl -u
  metatron-scheduler@iva`) and failure isolation come from systemd. One user's slow session never
  delays another's check-in; one crash never stops both. *(Rejected: one daemon looping over users —
  the `schedule` library is process-global, jobs run serially on one thread, and a 20–70 s session
  for one user would hold the other's morning brief.)*
- **The unit sets `METATRON_PERSONA=%i`, `STRICT=1`, and no fallback.** The process serves exactly
  one user, so every unscoped lookup in it — push-error logging, `fire_session` — resolves to that
  user and never to Mike.
- **One instance per user, enforced — two checks, because the lock alone cannot see the old
  process (review L5).** At start the scheduler (1) takes an `fcntl` lock on
  `data/personas/{p}/logs/scheduler.lock` and exits if another holds it — which stops a second
  *new* instance — and (2) scans `/proc` for any other live `core/scheduler.py --persona <p>` and
  exits if one is found — which stops `@mike` running beside the **old, pre-lock**
  `metatron-scheduler.service` process, the exact hazard § 3.8 names. Either check refusing is
  logged loudly.
- **Migration — the order is still the primary protection:** `daemon-reload` first (deploy rule
  3); `systemctl disable --now metatron-scheduler`; then **retire the old unit file** — move
  `/etc/systemd/system/metatron-scheduler.service` to `~/retired-units/` and `daemon-reload` — so that
  anything still naming the old unit (a stale `deploy.sh` line, a runbook command) fails with "unit
  not found" instead of **starting** it: `systemctl restart` starts a stopped unit, and the old
  process carries no lock and no `/proc` scan, so it would run beside `@mike`. *(`mask` was the
  first revision's answer and is wrong here — it refuses when a real unit file occupies the path,
  and `Restart=` never revives an explicit stop; verify N2.)* Confirm with `ps` that no scheduler for
  `mike` runs; then `enable --now metatron-scheduler@mike`; confirm with `ps` that exactly one does.
  `deploy.sh` changes `restart metatron-scheduler` → `restart 'metatron-scheduler@*'`.
- **"Every user" means approved accounts plus `mike`** — never the test personas, which would spend
  tokens on check-ins nobody reads.
- **`build_tick`** is disabled in a new user's `scheduler.yaml` (config, not code — the persona file
  already wins per key). It stays on for `mike`. When Build capabilities serve other users, that
  global registry write needs a lock first — named here, not built.
- **Proactive sessions hold until the interview is finished or paused** *(D2)* — a new user who has
  not signed in yet, or is mid-interview, gets no morning brief or check-in landing in an empty app
  or cutting across the interview. A gate in the scheduler's existing stack (mechanism only). **Its
  rule is exact (review L6):** it holds **only** when `data/personas/{p}/interview/state.json`
  exists **and** its status is `not_started` or `active`. No file → never held — which is every
  existing persona, `mike` included, however thin its goals. It never infers state from
  `goals.yaml`, which `new_persona.sh` creates as three empty lists before she has signed in.
  Maintenance jobs are unaffected.
- **The spend meter's day file gets an `fcntl` lock** (`core/spend_guard.py`, Red) — three writers
  now, and an under-counting guard is the failure the cost rules name. Caps stay global across users
  (§ 9).
- **Vertex cache owner label gains the persona** — `metatron:{host}:scheduler:{persona}` — so one
  user's scheduler never sweeps another's caches.
- **Family mode later:** a group layer can sit above these per-user processes (a group job fans out
  to members' processes, or a group process reads members' state). Nothing here stores anything
  per-user that a group would need to span. Not designed further now.

### 4.7 The first interview, in the app — goals and the shape of the day, one conversation

**Interview mode.** While a user's interview is *active*, a message sent in the app goes **straight
to the Goals Interviewer**, with the whole interview so far as its history — not through the
Coordinator → Synthesizer pipeline, whose five-turn history would lose the thread, and whose relay
would put a second voice between her and the interviewer and double each turn's wait. When the
interview is finished or paused, messages go back to the pipeline as normal.

*(Rejected: running the interview through the pipeline with the interviewer as a specialist — five
turns of history, ~30 s a turn, and the Synthesizer paraphrasing a conversation whose method depends
on precise mirroring.)*

**State** — `data/personas/{p}/interview/state.json`: `status (not_started | active | paused |
complete), started_at, updated_at, turns`, and the transcript as ordinary **exchange rows** in the
conversation DB, so the app shows it in her history, The Book shows it, and once she leaves the
interview the pipeline's recent history includes its last turns ("as we were saying…" works).

**Start.** On the first signed-in connection of a user whose `interview/state.json` says
`not_started` — a file only `approve` writes (§ 4.4), so it exists for approved account users and
never for `mike` or a test persona — the server marks it `active` *before* generating (so a
reconnect cannot start it twice), runs the interviewer's opening, and saves it as the first
exchange. **No state file means no interview mode, ever** — that is every existing persona. One rule,
read by both this and the scheduler's hold gate (§ 4.6); neither looks at `goals.yaml`.

**Coverage, from what is stored — not from the model's memory.** Each turn the interviewer receives
a short code-built block: goals recorded per horizon, mission and prime directive written or not, a
baseline period recorded or not, and each day-shape section set or missing (`day`, `windows`,
`meals`, `routines`, `children_home`, `travel_mode`, `location_sharing`; `calendars` only if a
calendar is connected). That is what lets a paused interview resume days later knowing exactly what
is left, and it is code-derived, so it cannot drift from what was saved.

**Pause, resume, finish** — two new tools for the interviewer, `pause_interview()` (she wants to
stop for now) and `finish_interview()` (the first draft is done and she agrees), plus the app's
*Finish later* / *Continue setting up* chips. A paused interview resumes where coverage says it
stands. *(Considered and left out of v1: the Synthesizer offering to resume in conversation — it
needs a new Red grant and the chip already does it; add later if she does not find the chip.)*

**Writing as it goes.** In the app this is production, so Phase 8's prototype branch (inline YAML)
does not apply: each element is confirmed conversationally and written when settled — goals with
`update_goal`/`write_goals`, mission and prime directive with `write_config` (which raises a
confirmation card every time — B2's gate, unchanged), day shape with `set_day_shape`, one entry per
call. A pause therefore loses nothing.

**A pending write is never reported as done (review L1).** `write_config` does not write — it raises
a card and returns `PENDING_CONFIRMATION`. On the pipeline, `enforce_pending_receipt()`
(`core/orchestrator.py:1972`, called at `:6713` and `:7109`) stops a reply claiming a pending action
happened; **the single-agent `run_session` path the interview would use does not call it** — only
`filter_output()` runs there (`:7225`). So the interview runner:
1. collects the turn's new pending confirmations exactly as the pipeline does and passes the reply
   through `enforce_pending_receipt()` before it reaches her;
2. the coverage block shows mission and prime directive in three states — *written*, *awaiting her
   confirmation*, *not yet* — so the interviewer is told, by code, that a card is waiting, and the
   agent file says to tell her plainly there is something to confirm;
3. `finish_interview()` **refuses while a Tier 1/2 write is still awaiting confirmation**, returning
   that to the interviewer — the interview cannot close on unwritten Tier 1/2.

§ 6.1 tests all three with a stubbed confirmation; § 6.3 confirms the card appears in the app for a
user who has never seen one.

**Leak control.** The interviewer now speaks to the user directly, so:
- `filter_output()` covers it — user-facing agents become an explicit set (`synthesizer`,
  `goals_interviewer`) rather than one name;
- `goals_interviewer.md` gains the **Confidentiality** section every user-facing agent carries.

**Crisis handling.** The interview bypasses `mental_wellbeing`, which is where clinical flags are
raised. `goals_interviewer.md` gains a short **Safety** section: an expression of suicidal thoughts,
self-harm intent or hopelessness about continuing stops the interview — respond with warmth and
directness, give professional resources, do not minimise, call `pause_interview()`. **State plainly:**
A4 safety testing is suspended (`ROADMAP.md` § 0 clause 8), so this path is untested by any suite;
§ 6.3 includes one manual probe on a test account. That probe is evidence, not the A4 gate.

**Agent-file and grant changes (Red):**
1. `goals_interviewer.md`: Confidentiality; Safety; Stage B § E's "Shape of the day" block in
   Phase 1 and its `set_day_shape` line in Phase 8 and Tools *(if Stage B has not applied them
   first — § 10)*; "in the app this is production — write as you go"; the two new tools; the
   coverage block explained in one line.
2. Both routing files: `goals_interviewer` gains `set_day_shape, pause_interview, finish_interview`.
   `scripts/check_agent_tools.py` after.

**Cost of one interview:** ~60 turns × ~25K input and ~2.5K output (thinking included) on
`gemini-3.8-flash` at the configured rates ($0.75 / $3.75 per 1M) ≈ **$1.70**, one-off per user —
**~$3.40 if 3.8's introductory pricing ends** (its end date is unverified, `spend_guard.yaml:178-189`).
The transcript is capped at the most recent ~60K tokens of history; older turns drop, and coverage
plus what was saved carry the facts.

### 4.8 What a user with nothing connected sees

Iva starts with no calendar and no mail. Every calendar-, mail- and intake-reading job and tool must
read "not configured" as *nothing to do* — no error text to her, no quality event every hour, no
retry loop. The day planner builds from her day shape alone.

**This is false today and is built, not just checked (review L2).** `tools/caldav.py:631-638`
returns `{"error": "CalDAV is not enabled…"}` for a disabled or absent config, and
`tools/day_plan.py` `refresh_snapshot` (`:318-331`) records it as `error`/`failed_at` with `ok=False`
on every refresh — so once Stage B registers `refresh_tick`, her planner would carry a standing
calendar error and re-fetch roughly six times an hour. Stage 1.13:
1. `_query_events` returns a distinct **not-connected** result (`{"events": [], "connected": false}`)
   when the config is absent or `enabled: false`; a real failure of a *configured* calendar stays an
   error, unchanged.
2. `day_plan._fetch`/`refresh_snapshot` store not-connected as a **successful, empty** snapshot
   (`discovery: "not_connected"`) — no `failed_at`, no re-fetch storm; `current()` and the plan
   builder are tested on it.
3. The same treatment for every scheduled reader that can run for her — `daily_calendar_dedup_audit`,
   `daily_calendar_reconcile`, `travel_check`, `intake_sweep`/`intake_digest` (mail) — each checked in
   Stage 0.6 against a synthetic no-integration persona, and each that reports an error or a quality
   event made silent.
4. Mike's configured calendar path is pinned unchanged by the existing day-plan suites.

§ 6.1 covers each reader; § 6.3's day-long watch confirms it on the real VM rather than discovering
it there.

### 4.10 Connecting her Google account — in the app, not by hand (Mike, after the walkthrough)

*"Iva will need to connect her Gmail and Google Calendar, possibly some work stuff as well. We CAN do
that manually for the time being, but it would be best if she were able to do so through the
Metatron app or webapp."*

**Why in the app, beyond convenience:** the manual route has her hand a Google app password to Mike
or paste it into a chat — where it lands in the verbatim transcript archive
(`~/.claude/tools/archive_chats.py`) and every backup after it. The app route puts it in exactly one
place — **her own credentials file on the VM, which the backups deliberately skip** (below; review
C1: without that exclusion the claim was false).

**Kept out of the backups, by design (review C1).** `scripts/metatron-backup.sh:83` tars all of
`config/personas` to Mike's Mac as a **plaintext** tarball — seven dated copies plus `latest` —
which `scripts/daily-backup.sh` then folds into its 30-day encrypted archives. A credential written
into `caldav.yaml`/`email.yaml` would be copied off the VM on every pull and outlive *Disconnect*
by a month. So:
1. Connections writes the app password **only** to `config/personas/{p}/credentials.yaml`
   (chmod 600); her `caldav.yaml`/`email.yaml` carry everything else and point at it.
   `tools/caldav.py` and `tools/mail.py` read the password from there when present — Mike's inline
   passwords keep working unchanged.
1a. **Never committable (review C3).** `.gitignore:190-207` protects `mike` by name and, for
   everyone else, only `profile.yaml`, `scheduler.yaml`, `caldav.yaml` and `*.bak` — so on the VM's
   checkout her `credentials.yaml`, `email.yaml`, identity file and Tier 1–3 files would be
   untracked-but-stageable, one `git add -A` during a hand-driven recovery away from history. Stage
   1.9 adds `config/personas/*.md`, `config/personas/*/credentials.yaml`, `email.yaml`,
   `intake.yaml`, `prime_directive.md`, `mission.md` and `goals.yaml`. **Already-tracked synthetic
   persona files stay tracked** (git ignores only untracked paths); a *new* synthetic persona needs
   `git add -f` from then on — the right default, since an untracked persona file is now presumed
   real. § 6.1 checks it with `git check-ignore` on an account persona's paths.
2. `metatron-backup.sh` excludes `*/credentials.yaml`. **After a VM rebuild she reconnects** — one
   minute in the panel — which is the price of never holding her Google credential on Mike's laptop
   or drives.
3. *Disconnect* deletes `credentials.yaml`; there is no retained copy to outlive it.
4. **She is told at the walkthrough** where it lives (only on the VM; not in any backup) and that
   Mike, as developer, can reach the VM.

*Noted, not changed: Mike's own app passwords sit inline in his `caldav.yaml`/`email.yaml` and so are
in those plaintext tarballs today. Moving them to `credentials.yaml` is a one-line choice for him;
it is not in this plan.*

**What she does** — a **Connections** panel in the app (and the web app):
1. The panel gives the three Google steps in plain words, with links: turn on 2-Step Verification;
   create an app password (myaccount.google.com/apppasswords); turn on IMAP in Gmail settings. One
   app password serves calendar, reading mail and sending it.
2. She enters the Google address and the app password, and taps *Connect*.
3. She sees either **"Connected — found 4 calendars: …"** or **the specific thing that failed and
   what to do** — reusing the remedies already written for this (`tools/caldav.py`
   `_credential_remedy`, `tools/mail.py`'s equivalent).
4. The panel then shows the address, the calendars found and when it last checked — never the
   password — with *Disconnect*.

**What the server does** — `POST /connections/google`, bound to her token like every route (§ 4.3):
1. **Tests before it writes anything:** CalDAV discovery against Google's endpoint for that address,
   then an IMAP login. Either failing → nothing written, the remedy returned.
2. On success, writes **her** `caldav.yaml` (`enabled: true`, `calendar_url` derived from the
   address — the legacy endpoint the template documents, since the OAuth one 401s on app passwords —
   `timezone` from her profile) and `email.yaml` (`enabled: true`, `imap.gmail.com`), and the app
   password to `credentials.yaml` alone, all chmod 600, under `config/personas/{p}/` on the VM.
   Nothing else changes.
3. `GET /connections` — status only. `DELETE /connections/google` — `enabled: false`,
   `credentials.yaml` deleted; § 4.8's not-connected path takes over.

**The password goes nowhere else.** It arrives in one HTTPS request body and is written to one
file. It is an HTTP route, not a chat message, so it never reaches a model, a conversation log, a
trace, `_WS_FRAME_LOG` or a quality event, and the route's own errors never echo it.

**Validation errors must not echo it either (review C2).** FastAPI's default 422 body
(`fastapi==0.136.1`, `pydantic==2.12.5`) carries an `input` field holding the submitted value —
the whole body, password included, when a field is missing — and `core/server.py` defines no
`RequestValidationError` handler. Stage 2.7 adds one **for the whole app**: a 422 returns the names
of the fields that failed and never a submitted value. It covers `/connections/google`, and equally
`/auth/register` and `/auth/login`, which carry passwords too.

§ 6.1 asserts both: after a connect the password string appears in no file under `data/` or
`config/` except `credentials.yaml`, **and not in the file list the backup command would pull**;
and a malformed request to any of the three routes returns no submitted value.

**After she connects:**
- **Her calendars get roles** — the interview's coverage block adds `calendars` the moment one is
  connected (§ 4.7), so the interviewer asks which are hers, which are shared family ones (her
  "Shared with Mike" calendar, presumably) and which to ignore. Connected after the interview, she
  tells the Synthesizer, which holds `set_day_shape` from Stage B. Until a roster exists, every
  calendar counts as hers — day planner D1's rule, unchanged.
- **Mail intake — the automatic inbox sorting — stays off** until she asks for it (`intake.yaml`
  template default). Connecting gives her the mail and calendar tools in conversation; it does not
  start an hourly sweep of her inbox.

**Work accounts — what works, and what waits for Mark 2:**
- **Google Workspace** connects the same way **if her employer allows app passwords** (many turn
  them off).
- **Microsoft 365 / Outlook** has no CalDAV, and its mail needs OAuth. That is Mark 2's OAuth route,
  already ruled (`SESSION.md` § Do not re-open) — not re-proposed here.
- **Interim for a work calendar:** if her work calendar can be subscribed to from her Google
  Calendar, it then arrives through her Google connection exactly as Mike's "UK Holidays" does today.

**Two decisions this adds (§ 9):** D8, which account she connects; D9, what her consent covers once
mail is connected — **decided: she is told in the app and gives permission herself** (§ 4.11).

### 4.11 Her permission, given in the app (D9, Mike, 2026-10-27)

*"She should be notified through the app and provide permission herself."*

**What she sees:**
1. **At sign-up** — one short screen, before the request can be sent: what Metatron does with what
   she tells it (processed by Google's Vertex AI under Google's terms: not used for training,
   logged only if flagged by Google's abuse classifier, kept up to 90 days); that the product is
   early and incomplete; and that **Mike, as its developer, can read everything she tells it.**
   *I understand — continue* records her permission. **Recommended (D11)** — the same principle as
   Mike's D9 ruling applied to the base configuration his ruling 2 covered verbally.
2. **At *Connect*** (§ 4.10) — a second screen: connecting lets Metatron read her calendar and
   mail, **including what other people wrote to her**; it may learn how she writes to particular
   people so it can draft in her voice (tone profiling) and, when built, fill in a contact's
   details from their public profile (contact enrichment); the app password is stored **only on the
   VM, never in a backup**, where Mike can reach it. Two separate ticks — *read my calendar and mail*
   (required to connect) and *learn how I write to people* (optional).
3. **In the Connections panel**, both permissions are shown with *Withdraw*. Withdrawing the first
   disconnects; withdrawing the second stops tone profiling at once.

**Disclosure here is the feature.** Naming Google, Vertex and the developer's access breaks the
usual "never surface which model or how" rule (`CLAUDE.md` § Discretion) on purpose — that rule's
own exception is "unless that transparency is an explicit design goal of the feature". It applies
to these two screens and nowhere else; no agent says any of it in conversation.

**Enforced in code, fail-closed** (`CLAUDE.md`: privacy is enforced in Python, never in prompts):
- Each permission is a record — `{scope, granted_at, text_version, withdrawn_at}` — in
  `data/personas/{p}/consents.json`. The exact text she saw is kept by version in
  `config/consent/` so the record shows what she agreed to.
- **The sign-up permission has a home before she does (review P1).** `/auth/register` is open — she
  has no token and no persona directory yet — so the request carries `{scope:
  "base_configuration", text_version}`, `/auth/register` refuses without it (if D11 is adopted), and
  it is stored in her **account entry** (§ 4.2). **`approve` copies it into her
  `consents.json`** (create-only, like every provisioning write), which is the one place read from
  then on. The Connect permissions are written by bound routes directly into `consents.json`. So
  every permission § 4.9.1 cites has a record. *(If D11 is declined, there is no sign-up record and
  § 4.9.1 cites Mike's ruling 2 for the base configuration instead.)*
- `POST /connections/google` refuses without a current `correspondence_read` record.
- **Tone profiling** — `tools/tone.py` `get_tone_shape()` / `_extract()` refuse for a persona
  without a current `tone_profile` record, returning a plain "not permitted" to the calling agent.
- **Withdrawal removes what was learned, not just future learning (review P2).** A profile is
  stored on the contact (`tools/tone.py:182` → `write_contact(tone_shape=…)`) and served back by
  `read_contact`/`search_contacts`/`list_contacts`, which Relationships holds. So withdrawing
  `tone_profile` (a) **removes `tone_shape` from every one of her contacts** — deleted, not
  archived: the archive-on-merge rule preserves a user's data through merges, and a withdrawn
  permission that leaves an archived copy has not been withdrawn — and (b) `tools/crm.py`'s read
  paths **omit `tone_shape` whenever no current `tone_profile` record exists**, which also covers
  any profile written in a race with the withdrawal.
- **The model itself is reachable only through that tool (review P4).** `run_subagent` passes any
  agent name to `run_session` (`tools/subagent.py:18-92`), so any agent holding it could call
  `tone_profiler` directly, below the check. `tools/subagent.py` gains a **code-only set** — the
  five agents whose input is built by code, each routed with an empty grant and bare dispatch:
  `tone_profiler`, `intake_extractor`, `accountability_judge`, `day_planner`, `crm_sweep`
  (`config/modules/routing_cloud.yaml:85-155`) — and `run_subagent` refuses them. Their code
  callers use `run_session` directly and are unaffected; § 6.1 greps `config/agents/` to confirm no
  agent file dispatches one.
- **Contact enrichment (`[DB-0826-02]`) is not built**; its build must check a
  `contact_enrichment` record the same way.
- **`mike` gets records citing his own rulings** (2026-08-26 and 08-28) as the evidence, so nothing
  changes for him — **and because `data/personas/mike/` is VM-owned data no deploy carries, they
  are written on the VM by a command before the deploy (review P3)**: Stage 4 step 0,
  `scripts/accounts.py seed-consent mike --scopes correspondence_read,tone_profile --evidence
  "Mike's rulings 2026-08-26, 2026-08-28"`, idempotent; Stage 4's check confirms `get_tone_shape`
  for `mike` still answers after the deploy. Every other persona starts with none, which is what
  makes it fail-closed; synthetic personas get none, so their tests prove the refusal.

**The § 0 amendment** (§ 4.9.1) records Mike's D9 ruling and points at these records as the
evidence of her consent, rather than restating it as something she said verbally.

### 4.12 The server's memory — voice out of the server, PyTorch without the GPU code (D10, D13, D14)

The diagnosis (§ 3.12) found the cause; Mike asked whether the graphics-card code can go (*"Can we
remove the graphics card part?"*) and whether curtailing spoken replies buys room (*"We don't
really use them right now"*). Both, in this build:

**1. PyTorch without the GPU code (D13).** The VM's PyTorch is the CUDA build: 15 `nvidia-*`
packages, **2.7 GB of disk, 169 MB resident in the server**, on a VM with no GPU. On the VM, PyTorch
is installed from PyTorch's CPU-only package index in **its own install step**, and the `nvidia-*`
packages are uninstalled. *Not* `--extra-index-url` in `requirements.txt`: that lets the second
index supply any package whose version it carries a higher number of, not just PyTorch.
`requirements.txt` keeps `torch==2.12.0` for every platform but Linux (the Mac's PyTorch has no CUDA
anyway), and `deploy.sh` runs the CPU install before `pip install -r requirements.txt`. Stage 0
confirms the `2.12.0+cpu` wheel exists for the VM's Python before anything is changed; if it does
not, the nearest CPU build that `kokoro` and `sentence-transformers` accept is used, and named.

**2. Voice in its own helper process (D14).** Spoken replies are **off by default** — only where 🔊
is switched on, or in headset mode (`static/index.html:2964, 3109`). So the voice model should cost
nothing when nobody is speaking, and must never be able to take the server down when someone is:
1. **The server stops loading Kokoro at startup** (`core/server.py` warm-up, `:635`).
2. **On the first spoken reply, the server starts a helper process** that loads Kokoro and
   synthesises; later replies reuse it. **After a stretch with no spoken reply it exits, and all
   its memory goes back to the system** — memory a running Python process frees is not reliably
   returned (§ 3.12: the per-reply growth), but a process that exits returns everything.
3. **The helper is the kernel's first choice in a memory squeeze** (it raises its own
   `oom_score_adj` to 1000 at start, which needs no privilege) — so a reply too big for the
   machine kills the helper and costs one spoken reply, never the server and everyone's
   conversation. It also **exits with the server** (`PR_SET_PDEATHSIG`), so a restart never orphans
   a 1.5 GB process.
4. **Replies are synthesised a sentence at a time** inside the helper and joined, which bounds the
   per-reply peak that killed the 1.9 GB test.
5. Requests still queue on one worker, as now; non-English replies keep going to `edge-tts`,
   unchanged ([DB-0810-15]).

**The trade-off, stated:** the first spoken reply after a quiet spell waits for Kokoro to load —
**~10 s** on the running server's evidence (`core/server.py:1574`: ~7 s import + ~3 s pipeline),
slower if the machine is busy. Every reply after it in the same spell is as fast as today.

**The idle timeout is a cost parameter (the global cost rules), so it is chosen here with its
figure:** while warm, the helper holds **~1.5 GB of RAM** (measured) — RAM, not money, on a VM
whose price does not change with use; a longer timeout buys fewer ~10 s cold starts at the price of
holding that memory longer, which is exactly the headroom a second user needs. **Recommended: 10
minutes** — a spoken conversation keeps it warm; a single reply costs 10 minutes of 1.5 GB. Set in
config (`config/modules/voice.yaml`, new), not code. What deletes it: the idle timer; server
restart (death signal); a crash (the server starts a fresh one on the next spoken reply). Meter:
the watchdog's per-process RSS records (Stage 1.14) — the helper appears as its own process.

**3. One copy of each model on the whole VM — the schedulers never carry one (review M1).** The
scheduler's "~69 MB" (and today's 39 MB) is a *fresh-process* figure. A scheduler runs
non-coordinator sessions **in its own process** (`core/scheduler.py:470-474` —
`weekly_pattern_miner`, `weekly_physical_review`, Mike's six-hourly `check_inbox_6h`), and the
first `write_log` there hands `index_entry` to `core/background.py`'s pool, which loads the
embedder (`core/memory.py:40-44`) **into that scheduler for the life of the process** — and
`tools/baselines.py:44-48` keeps a **second, separate copy** of the same model, which a pattern-miner
run loads too. So each per-user scheduler would settle near ~0.9 GB after its first Sunday, and two
of them would undo the saving. Fixed three ways:
1. **Scheduled sessions for every agent run on the server**, as the coordinator's already do
   (`send_one`): non-coordinator agents go to a new **`service`-only `/internal/session`** route —
   not the user-facing `/session`, which writes every run as a conversation exchange
   (`core/server.py:669`, `_log_conversation`) that the nightly CRM sweep then reads as things the
   user said (`tools/crm_sweep.py:389-406`; review M1-N1). `/internal/session` calls
   `run_session(agent, …, proactive=True)` — so it is traced as scheduled, spend-gated and
   history-free exactly as the in-process path was (`core/orchestrator.py:7168, 7203-7212`) — with a
   timeout long enough for the pattern miner, and **writes no conversation record**, matching what
   the in-process run produced. The models live once, in the server.
2. **The scheduler process never loads a model.** Its unit sets `METATRON_NO_LOCAL_MODELS=1`;
   `core/memory.py`'s index and search calls in such a process are **handed to the server** through
   two `service`-only internal routes (`/internal/index`, `/internal/search`) that run on the
   server's existing `_INDEX_EXECUTOR`; and `_get_model()` in that process **raises loudly** rather
   than loading — so a path nobody thought of fails visibly in the scheduler's log instead of
   quietly costing 900 MB.
3. **`tools/baselines.py` uses `core/memory._get_model()`**, not its own copy — one embedder per
   process, as its own comment ("Do not introduce a second embedding model") already intends.

**4. The engine check stops importing Kokoro (review M2).** `_kokoro_available()`
(`core/server.py:1561-1566`) is `import kokoro`, run in the server on every `/tts` — so the first
spoken reply would still pull Kokoro's code into the server. It becomes
`importlib.util.find_spec("kokoro") is not None`, which checks the package is installed without
importing it; only the helper imports Kokoro.

**What it buys — a budget for the whole VM, not one process** (3.9 GB total; 2 GB swap):

| | Voice unused (as now) | Someone speaking |
|---|---|---|
| Server (one copy of embedder + Whisper, no Kokoro, no CUDA) | ~1.0–1.2 GB *(estimate)* | same |
| Two schedulers (no model, ever) | ~0.1–0.3 GB | same |
| Voice helper | 0 | ~1.5 GB, plus the per-sentence peak |
| **Total** | **~1.1–1.5 GB** | **~2.6–3.0 GB** |

Against today's server alone at 2.0 GB climbing to an OOM kill at ~3.5 GB. **The upgrade question is
not settled by this table — it is settled by § 6.3a's measurement of the whole VM over a full week
with both users and both schedulers, a Sunday included.** If the "someone speaking" column measures
above ~3.2 GB, or available memory falls below the watchdog's 500 MB line on an ordinary day, the
upgrade is priced then (D10 c).

**And today, before any build: switch 🔊 off in the web app on the Mac** — the five spoken replies
on 10-27 came from there. That alone stops the per-reply growth until the build lands; the server
still loads the model at each start.

### 4.9 Records changed with the build

1. `ROADMAP.md` § Section 0 — **Amendment 2026-10-26 (Mike's ruling): the 08-26/08-28 basis extends
   to a second user, Iva,** who has been told the configuration — sensitive-tier processing on
   Vertex under Google's default terms (no training use; prompt logging only on classifier-flagged
   traffic, ≤ 90 days) — and that the developer has full access to her data, and who will be using
   incomplete data. **It lapses for any further user who has not given the same informed consent.**
   Connecting her mail and calendar (§ 4.10) brings their contents onto the same path. **D9 (Mike,
   2026-10-27): she is told in the app and gives permission herself** — the `tone_profiler` and
   contact-enrichment clearances apply to her only while her own permission record for each is
   current (§ 4.11), and the amendment cites those records as the evidence of her consent.
2. `CLAUDE.md` — the Key Design Decisions privacy line (its "single-user" lapse clause), and
   Infrastructure trap 5 (`--persona mike` on both units → a scheduler per user, `STRICT=1`, the
   instance lock).
3. `docs/INFRASTRUCTURE.md` — both unit texts, the migration, `deploy.sh`, the APK login, the
   approval commands.
4. `.claude/rules/personas.md` — "Adding a persona" now means sign-up + `approve`; test personas
   still via `new_persona.sh`.
5. `ROADMAP.md` § Section 3, beside the Phase 7 row — **a second test user admitted ahead of this
   gate by Mike's ruling 2026-10-26; not Phase 7.** Names § 2a's gaps (auth/path-layer isolation
   only, no per-user encryption, user research session still owed) so the roadmap and the deployment
   agree (review S3).

---

## 5. Stages, files and tiers

**Every Red file is edited by hand in this session with Mike present — never delegated.** Built in
a git worktree off `main`: this tree holds another window's uncommitted work
(`.claude/agents/build-inquiry.md`, `archive/plans/inquiry_rewrite_2026-09-26.md`, an untracked
`tools/rituals.py` and four `archive/handoffs/*.patch` files) — none of it is touched, and every
file is `git diff`-ed before staging.

### Stage 0 — read-only checks (before any code)

1. `persona_audit.jsonl` on the VM — every call site that resolved by fallback (§ 4.3).
2. ~~`metatron-backup.sh` covers `data/accounts/`~~ — answered by the review: it does not; Stage 1.9
   adds it (§ 4.2).
3. Readers of `data/audio/` (§ 4.3).
4. Template vs live `scheduler.yaml` diff (§ 4.4).
5. Whether `.env` on the VM sets `METATRON_PERSONA` — Mike checks (this session cannot read `.env`);
   if it does, it must go before the server runs strict.
6. Each calendar/mail/intake reader run against a synthetic persona with integrations disabled —
   which return an error, write a quality event, or retry (§ 4.8).

### Stage 1 — accounts, tokens, binding, isolation (Amber/Green)

| # | Work | Files |
|---|---|---|
| 1.1 | Account store, scrypt, `cred_version`, file lock | `core/accounts.py` (new) |
| 1.2 | Tokens v2, roles, verification against the store; `client_token` mints `service` | `core/auth.py` |
| 1.3 | `/auth/login` `{username, password}`; `/auth/register`; limits | `core/server.py` |
| 1.4 | The one identity helper; every route converted; `DEFAULT_PERSONA`/`__default__` out of request handling; WS user from token | `core/server.py` |
| 1.5 | `/feedback`, `/tts`, `/subscribe`, `/push/test`, `/transcribe` bound; per-persona audio | `core/server.py`, `core/voice_pipeline.py` (if it writes the path) |
| 1.6 | Push per persona + migration of existing subscriptions to `mike` | `core/push.py`, `core/server.py` |
| 1.7 | `/monitor/*` admin/service only; `GET /monitor/accounts` | `core/server.py` |
| 1.8 | Cache owner label with persona | `core/orchestrator.py` |
| 1.9 | `scripts/accounts.py` (VM-side); session-start line; `data/accounts` added to the backup; account-persona files made never-committable (§ 4.10 1a) | `scripts/accounts.py` (new), `scripts/sync_dev_backlog.py`, `scripts/metatron-backup.sh`, `.gitignore` |
| 1.10 | Login / sign-up screens, chip switch, `lastSeenId` reset | `static/index.html` |
| 1.11 | Every internal client mints `service` and names its persona | `core/remote_client.py`, `scripts/mint_token.py`, `tools/metatron_monitor.py`, `scripts/vm_read.py`, `scripts/build_board.py`, `deploy.sh` (token only) |
| 1.12 | Tests (§ 6.1) | `tests/` |
| 1.14 | Memory monitoring (D10 a): per-process RSS in the watchdog's records; OOM kills and low-memory days in the session-start line, new entries only; the dead push call removed | `scripts/vm_memory_watch.py`, `scripts/sync_dev_backlog.py` |
| 1.15 | PyTorch without the GPU code on the VM (§ 4.12.1): CPU install step, `nvidia-*` uninstalled, `requirements.txt` torch pin left for non-Linux | `deploy.sh`, `requirements.txt` |
| 1.16 | Voice in its own helper process (§ 4.12.2): no Kokoro at startup; helper started on demand, sentence-by-sentence, `oom_score_adj` 1000, death signal, idle exit from config; the engine check uses `find_spec`, never `import` (§ 4.12.4) | `core/tts_worker.py` (new), `core/server.py`, `config/modules/voice.yaml` (new) |
| 1.17 | One copy of each model (§ 4.12.3): `/internal/session`, `/internal/index` and `/internal/search` (service only; the first writes no conversation record); `core/memory.py` delegates and refuses to load under `METATRON_NO_LOCAL_MODELS`; `tools/baselines.py` uses the shared model | `core/server.py`, `core/remote_client.py`, `core/memory.py`, `tools/baselines.py` |
| 1.13 | Not-connected integrations read as nothing to do (§ 4.8) | `tools/caldav.py`, `tools/day_plan.py`, and whichever of `tools/calendar_audit.py`, `tools/calendar_reconcile.py`, `tools/travel_watch.py`, `tools/intake.py` Stage 0.6 implicates |

### Stage 2 — the interview mode (Amber/Green)

| # | Work | Files |
|---|---|---|
| 2.1 | Interview state, start-once, routing an active user's message to the interviewer with full history, exchange rows | `core/interview.py` (new), `core/server.py` |
| 2.2 | Coverage block from stored goals/config/day shape | `core/interview.py` |
| 2.3 | `pause_interview` / `finish_interview` tools (registered; granted in Stage 3) | `core/interview.py`, `core/orchestrator.py` (`register_tools`), `core/actions.py` |
| 2.4 | `filter_output()` user-facing set; `enforce_pending_receipt()` on the interview path; `finish_interview` refuses on pending Tier 1/2 | `core/orchestrator.py`, `core/interview.py` |
| 2.5 | Chips | `static/index.html` |
| 2.6 | Tests (§ 6.1) | `tests/` |
| 2.7 | Connections: `POST/GET/DELETE /connections/google`, test-before-write, config writers for her `caldav.yaml`/`email.yaml`, the password to `credentials.yaml` only; the backup excludes it; an app-wide 422 handler that never echoes a submitted value (§ 4.10) | `core/server.py`, `core/connections.py` (new), `tools/caldav.py`/`tools/mail.py` (expose discovery/login and remedy text; read the password from `credentials.yaml` when present), `scripts/metatron-backup.sh` |
| 2.8 | The Connections panel, with Google's three steps | `static/index.html` |
| 2.9 | Coverage adds `calendars` when one is connected | `core/interview.py` |
| 2.10 | Permission records and routes, versioned texts; the sign-up permission in the account entry, copied by `approve`; `seed-consent`; Connect refuses without `correspondence_read`; tone profiling refuses without `tone_profile`; withdrawal removes stored profiles and the read paths hide them; `run_subagent` refuses the code-only agents (§ 4.11) | `core/consent.py` (new), `config/consent/` (new texts), `core/accounts.py`, `scripts/accounts.py`, `core/server.py`, `core/connections.py`, `tools/tone.py`, `tools/crm.py`, `tools/subagent.py` |
| 2.11 | The sign-up notice (D11) and the Connect permission screen; *Withdraw* in the panel | `static/index.html` |

### Stage 3 — Red, Mike present

| # | Work | File |
|---|---|---|
| 3.1 | `persona_scope()` stops mirroring the environment | `core/persona.py` |
| 3.2 | Instance lock **and** `/proc` scan for a pre-lock process; interview hold gate (state file only); `_notify_push` passes persona; **every agent's scheduled session sent to the server, none run in-process** (§ 4.12.3); stale comment fixed; the template unit sets `METATRON_NO_LOCAL_MODELS=1` | `core/scheduler.py` |
| 3.3 | Day-file `fcntl` lock | `core/spend_guard.py` |
| 3.4 | Confidentiality, Safety, Shape of the day (if not already applied), write-as-you-go, tools | `config/agents/goals_interviewer.md` |
| 3.5 | Grants | `config/modules/routing.yaml`, `config/modules/routing_cloud.yaml` |

### Stage 4 — deploy (Mike)

0. **Before** `deploy.sh` (Mike, or Claude Code on his go), three steps in this order:
   1. **On the Mac:** `git push origin main` — the merged build must be on GitHub before the VM can
      pull it; `deploy.sh`'s own push (`:107-108`) comes too late for this step (verify P3-N2).
   2. **On the VM:** `cd ~/multi-model-mcp && git pull origin main`, then **confirm the VM's
      `git rev-parse HEAD` equals the Mac's** — the seed is never run against a tree that is behind.
   3. **On the VM:** `.venv/bin/python scripts/accounts.py seed-consent mike --scopes
      correspondence_read,tone_profile --evidence "Mike's rulings 2026-08-26, 2026-08-28"`
      (§ 4.11).

   **Why the pull comes first:** the script does not exist on the VM until then (verify P3-N1:
   `deploy.sh:152` is otherwise the only pull). It is harmless ahead of the deploy — the running
   server and scheduler keep the old code until `deploy.sh` restarts them, and `deploy.sh`'s own
   push and pull are then no-ops (its post-deploy HEAD assertion, `:218-264`, still reports a
   match). So `mike`'s tone profiling never sees a window where it refuses.
1. On the VM: install `metatron-scheduler@.service`; server unit to `STRICT=1`, no fallback;
   `daemon-reload`.
2. `deploy.sh` (Mike runs it — Denied here), with the `restart 'metatron-scheduler@*'` change.
3. `disable --now metatron-scheduler` → move its unit file to `~/retired-units/` → `daemon-reload`
   → `ps` shows no scheduler for `mike` → `enable --now metatron-scheduler@mike` → `ps` shows exactly
   one; a second start of `@mike` exits on the lock; `systemctl restart metatron-scheduler` now
   reports the unit not found (§ 4.6).
4. Rebuild and sideload the APK; sign in as `mike` on phone and browser.
5. Confirm `get_tone_shape` for one of `mike`'s saved contacts answers (ready or written), not
   "not permitted".

### Stage 5 — verify on the real VM, then Iva

§ 6.3, on a smoke-test account (`trial_2026_10`), then the Iva walkthrough (§ 6.4).

---

## 6. Tests

### 6.1 Unit and integration (synthetic personas; every live meter stubbed — model, CalDAV, push, Routes)

1. **Isolation, the headline suite:** a `user` token for A cannot read or write B through **any**
   route — a parametrised test over the full route table (so a route added later without binding
   fails the suite), WS included; a naming mismatch → 403; `/monitor/*` → 403 for `user`, 200 for
   `admin`/`service`.
2. Two threads serving A and B concurrently: an unscoped lookup on a third thread raises (no env
   mirror), and never returns A or B.
3. Tokens: v1 rejected; tampered, expired, stale `cred_version`, disabled, rejected, pending → 401;
   admin-password login as an account user refused.
4. Sign-up: validation, reserved and taken names, limits, pending/rejected/disabled sign-in messages
   only after a correct password.
5. `accounts.py`: approve is idempotent from every half-done state and **never overwrites an
   existing `state.json` (active, paused or complete stays as it was)**; approve refuses a
   `disabled` account; `enable` re-admits one without touching her persona; disable stops the unit
   (stubbed `systemctl`).
6. Push: B's notification reaches only B's subscriptions; migration assigns existing ones to `mike`.
7. Scheduler: a second instance exits on the lock; an instance started beside a lock-less
   `--persona <p>` process exits on the `/proc` scan; the interview hold blocks session jobs only,
   holds for `not_started`/`active` state files, and never for a persona with no state file (an
   empty `goals.yaml` included); `METATRON_PERSONA=%i` + strict → push-error logs land in the right
   tree.
8. Spend: two processes incrementing concurrently lose nothing.
9. Interview: starts once across a reconnect race; an active user's message reaches the interviewer
   with full history and never the pipeline; pause/finish route back; coverage reflects stored data;
   the filter suppresses a leak in an interviewer reply; a reply claiming a pending `write_config`
   was recorded is corrected by `enforce_pending_receipt()`; coverage shows *awaiting her
   confirmation*; `finish_interview()` refuses while one is pending.
11. Not connected (§ 4.8): each calendar/mail/intake reader on a no-integration persona returns
    nothing to do — no error, no quality event; the day planner stores an empty successful snapshot
    and does not re-fetch on every tick.
12. Interpreters (§ 4.2): `scripts/mint_token.py` and `scripts/sync_dev_backlog.py` run under
    `/usr/bin/python3` (3.9) and mint a token the server accepts.
13. Connections (§ 4.10), CalDAV and IMAP stubbed: a failing test writes nothing and returns the
    remedy; a passing one writes exactly her three files, chmod 600, and no other persona's; `GET`
    never returns the password; `DELETE` deletes `credentials.yaml` and leaves § 4.8's not-connected
    state; **after a connect the password string is found in no file under `data/` or `config/`
    except `credentials.yaml`, and `credentials.yaml` is absent from the backup's tar file list**;
    a malformed body to `/connections/google`, `/auth/register` or `/auth/login` returns a 422 with
    no submitted value in it; Mike's inline-password configs still connect; a `user` token cannot
    connect, read or disconnect another user's account.
14. Never committable (§ 4.10 1a): `git check-ignore` reports every file `approve` and Connections
    create for an account persona as ignored, and every currently tracked synthetic persona file as
    still tracked.
15. Permission (§ 4.11): Connect without a current `correspondence_read` record → refused;
    `get_tone_shape()` for a persona without `tone_profile` → "not permitted" and **no model call**
    (stubbed `tone_profiler` asserts zero calls); withdrawing either takes effect on the next call;
    `seed-consent` is idempotent and keeps `mike`'s tone profiling working unchanged; a record
    stores the text version shown; one user cannot grant or withdraw another's; `/auth/register`
    without the sign-up permission is refused (D11) and `approve` copies it into `consents.json`
    without overwriting one that exists; **after withdrawal no contact of hers carries
    `tone_shape`, and `read_contact`/`search_contacts`/`list_contacts` return none**;
    `run_subagent` refuses each of the five code-only agents while their code callers still run;
    no file in `config/agents/` names one as a `run_subagent` target.
16. Memory monitoring (D10 a): a watchdog run records server and scheduler RSS; the session-start
    line shows a synthetic OOM entry and a synthetic low day once, and nothing on the next run.
17. Voice helper (§ 4.12.2, Kokoro stubbed **only inside the helper**): the server starts with no
    Kokoro loaded; **after a `/tts` handled through a stub helper, `"kokoro"` is not in the server's
    `sys.modules`** (the engine check is `find_spec`); the first
    `/tts` starts exactly one helper and later calls reuse it; the helper exits after the configured
    idle time and the next call starts a fresh one; a helper killed mid-reply returns an error for
    that reply only and the server keeps serving; the helper's `oom_score_adj` reads 1000; killing
    the server takes the helper with it; a multi-sentence reply is synthesised per sentence and
    joined in order; non-English still goes to `edge-tts`.
18. One copy of each model (§ 4.12.3): a scheduled `pattern_miner` session reaches the server's
    `/internal/session`, is traced as proactive, and **adds no row to the conversation log** (so the
    CRM sweep never reads it); in a process with
    `METATRON_NO_LOCAL_MODELS=1`, `write_log` indexes through `/internal/index` and `search_memory`
    through `/internal/search`, and `_get_model()` raises; `tools/baselines.py` and `core/memory.py`
    return the same model object in one process; a `user` token gets 403 on all three internal routes.

### 6.3a On the VM, after Stage 4 — the memory result, measured across the whole VM

1. Server RSS after warm-up with voice unused — the § 4.12 estimate is ~1.0–1.2 GB; record the real
   figure. No `nvidia` library in the server's memory map; no `kokoro` module loaded.
2. Ten spoken replies with 🔊 on: the helper appears, the server's RSS does not move with them, and
   ten idle minutes later the helper is gone and its memory is back (`free -m`).
3. **For a full week with both users and both schedulers, a Sunday included** (the weekly
   in-process jobs are what loaded the embedder before), the per-process records (Stage 1.14) show:
   each scheduler stays under ~300 MB and never maps `torch` or `sentence_transformers`; the server
   levels off; **VM available memory never drops below the watchdog's 500 MB line on an ordinary
   day**. Any miss → D10 (c), the upgrade, is priced with that week's figures.
10. Existing suites green: `tests/test_server_auth.py` (its WS tests connect with no persona — they
    move to service tokens), the attachment, location, task-ledger, decline, WS-idempotency and
    day-plan wiring suites, `scripts/qa_sweep.sh`, `scripts/check_agent_tools.py`,
    `scripts/check_personas.py`.

### 6.2 Red-session smoke (Stage 3)

The scheduler runs for real (deploy rule 1 — import is not enough): start `mike`, start a test
persona, confirm both register, confirm a duplicate exits.

### 6.3 On the real VM (Stage 5) — a smoke-test account, then archived

1. Sign up as `trial_2026_10` in the app → "waiting" → `/monitor/accounts` shows it → the
   session-start line shows it → `approve` → sign in.
2. The interview opens unprompted; answer ~6 turns covering a goal and two day-shape items; confirm
   they were written (The Book).
3. *Finish later* → a normal message gets a pipeline reply → *Continue setting up* → it resumes with
   the right coverage.
4. **One crisis probe** inside the interview: the reply gives resources, does not minimise, and the
   interview pauses. Evidence, not the A4 gate.
5. With the trial token: try `?persona=mike` on three routes and the WS → 403 each; `/monitor/file`
   → 403.
6. Leave it a day: its scheduler log and `quality_events.json` carry no repeating "not configured"
   errors; no morning brief fired while the interview was paused-then-resumed-then-active *(per D2)*.
7. `disable` → its scheduler stops; sign-in refused. Its directories are archived, not deleted.

**Pass = all seven.** Anything else is fixed before Iva.

### 6.4 Iva

A guided walkthrough session (the (M) rule): steps prepared in advance, Mike and Iva live —
Tailscale share of `metatron-vm` only, APK file sent to her directly, sign-up, approval in chat, the
first few minutes of the interview. Then her use decides.

---

## 7. Cost

| Class | Figure |
|---|---|
| **Build** | Opus 5.5 on the subscription, ~4.5–7M tokens across Stages 1–3 (Stage 1 the largest; § 4.10's Connections ~0.5–1M of it); ~2–3 Mike-hours (Red session ~60–90 min, deploy and APK ~30 min, walkthroughs ~30 min). Fable review at high effort ~0.5–1M, plus a verify round |
| **Run** | Accounts and login: nothing. Iva's use: **~$1.50–2.00/day if like Mike's** (his real use measured 08-29, `docs/INFRASTRUCTURE.md` § Billing) ≈ **$45–60/month**, her check-ins included. Interview **~$1.70 once** (~$3.40 if the 3.8 intro rate ends). Mike approved; limits adjusted when she starts (ruling 7) |
| **Ancillary** | Her prompts make their own Vertex caches, so **cache storage now scales with users** — billed per wall-clock hour while a cache exists; `spend_guard` charges it on grant (2026-08-20 fix), so it is metered. A second scheduler: ~40–140 MB measured fresh; with § 4.12.3 it never loads a model, so it stays there — verified over a week by § 6.3a.3 |
| **Unseen** | 1) **Memory pressure is recorded but tells no one** (§ 3.12) — the watchdog writes a file nothing reads, and its push goes to a route that does not exist. With two users, a server OOM takes both down. 2) The spend caps are **global**: one user's runaway day stops every user's sessions, and nothing reports per-user spend. 3) The day-file lost-update risk, closed by § 4.6's lock |

**The three persistence questions**, for what this creates:

| Creates | Standing cost, and what more buys | What deletes it; restart/crash | Meter |
|---|---|---|---|
| A scheduler process per user | RAM (~40–140 MB each, model-free by § 4.12.3), plus her proactive sessions' tokens | `disable` → `systemctl disable --now`. systemd restarts on crash; the lock stops duplicates | spend guard for tokens; for RAM, the watchdog records but **tells no one** |
| The account store | none (a small file) | `disable`/`reject` change status; entries are not deleted (archive rule). Survives restart by design | none needed |
| Her interview transcript | none beyond storage | it is her data — archived with her persona, never pruned | none needed |
| Her Vertex caches | storage per hour while alive | TTL expiry; her scheduler's sweep owns only its own label (§ 4.6) | `spend_guard.record_cache_storage` |

---

## 8. Models

- **Build: Opus 5.5** — security- and identity-critical work across `core/`, the app and Red files.
- **Review: Fable, high effort** — an isolation defect leaks one person's life to another; this is
  the review the split exists for.
- **Not delegated:** Stage 3 (Red). Stage 1–2 may be built in a worktree by this session; no
  subagent writes `core/auth.py`, `core/accounts.py` or the identity helper.

---

## 9. Decisions for Mike, and risks stated now

**Decided by Mike, 2026-10-26, after the walkthrough:**

1. **D1 — the admin password cannot sign in as an account user.** ✅ Decided as recommended.
2. **D2 — proactive sessions hold until the interview is finished or paused.** ✅
3. **D3 — password reset is a Mike-run command printing a temporary password.** ✅
4. **D4 — "That name is taken" says so** (revisit before any public endpoint). ✅
5. **D5 — day-planner Stage B is completed before this build begins.** ✅ Approved on the
   condition that it is genuinely the better order — confirmed (§ 10): Stage B applies the
   interviewer's day-shape half and the `set_day_shape` grants this build's interview stands on,
   registers the day-plan ticks whose not-connected behaviour § 4.8 fixes, and edits the same Red
   files. **Mike asked to be stopped if he asks for this build before Stage B lands** — the banner
   at the top of this file and a project memory carry that.
6. **D6 — the crisis wording** is folded into the Stage 3 Red session. ✅
7. **D7 — Iva is admitted as a test user ahead of the Phase 7 gate, § 2a's gaps recorded in
   `ROADMAP.md`.** ✅ "That's fine."

**Open — added with § 4.10:**

8. **D8 — which Google account she connects.** (a) **A dedicated Metatron Gmail for her**, with her
   calendar shared to it and her mail forwarded — the convention Mike's own persona follows
   (`docs/INFRASTRUCTURE.md` § Account convention: `diamond.mike.mt@gmail.com`). A send the system
   makes — including one an injected email talked it into — goes from that address, not her real
   one, and she chooses what reaches it. More setup: a new account, a calendar share, a forwarding
   rule. (b) **Her own Gmail directly** — the least setup; the system reads all her mail and sends
   as her real address. **Recommended: (a)**, for the same reason Mike chose it for himself; the
   Connections panel works for either, so it is her choice at the walkthrough if she prefers (b).
9. **D9 — her consent once mail is connected.** ✅ **Decided (Mike, 2026-10-27): "she should be
   notified through the app and provide permission herself."** Built as § 4.11 — two in-app
   permission screens, stored records, enforced in code, withdrawable.

D8 stays open by design — it is effectively Iva's choice, made at the walkthrough; the panel works
either way.

**Open — added 2026-10-27:**

10. **D10 — the VM's memory (§ 3.12).** ✅ **Decided (Mike, 2026-10-27): monitor; find out whether
    something is eating memory it shouldn't; price an upgrade only if one is needed.** So:
    (a) **in this build, Stage 1.14** — the watchdog also records the server's and each
    scheduler's RSS on every run (the growth curve the diagnosis needs: 2.05 GB at 1 h 40 min up on
    10-27, 3.0 GB at 4 h 17 min on 10-26); the session-start line shows any OOM kill and any day
    spent below the threshold, reading only what is new since it last looked (the log is already
    7,878 lines); the watchdog's dead push call is removed (the APK has no push; the session-start
    line is the channel that works). (b) **diagnosis — done 2026-10-27** (§ 3.12): the voice model
    is the growth and most of the weight; the embedder and Whisper level off. Fixed in this build
    by § 4.12. (c) **The upgrade is decided by measurement, not by this plan's estimate** (review
    M1): § 6.3a.3's week across the whole VM, both users and both schedulers, a Sunday included.
    Priced from Google's SKU catalogue then, with that week's figures, if it misses.
11. **D11 — a permission screen at sign-up as well** (§ 4.11.1), covering Vertex processing and
    the developer's full access. ✅ **Decided (Mike, 2026-10-27): implement it.**
12. **D12 — Mike's own Google app passwords** (for `diamond.mike.mt@gmail.com`, calendar and mail)
    sit filled-in inside every VM-pulled tarball in `backups/vm/` on the Mac — seven dated copies
    plus `latest`, unencrypted — and `backups/` is **included in Time Machine**, so every snapshot
    holds them too; `daily-backup.sh` adds 30 days of encrypted copies (checked 2026-10-27, field
    presence only — the values were never printed). Options: (a) after this build, move them into
    `credentials.yaml` (excluded from backups) **and rotate the app password in Google** — rotation
    is what makes the copies already in the tarballs and Time Machine worthless, without hunting
    them down; ~5 Mike-minutes; cost: after a VM rebuild he reconnects in the panel. (b) Leave as
    is. **Recommendation revised 2026-10-27, after Mike asked why: (b).** The Mac already holds
    stronger secrets in plain files (`.env` — the server password the Mac mints tokens with — and
    the gcloud/SSH credentials to the VM), so a thief of the Mac's files gains little extra from
    these. The only place the tarballs add exposure is the **Time Machine disk**, and if that is
    unencrypted the right fix is encrypting Time Machine, which covers everything at once. Iva's
    credential is kept out of backups for a different reason — it is another person's, on Mike's
    machine, without her consent — which does not apply to his own.
13. **D13 — PyTorch without the GPU code.** ✅ Mike asked for it ("Can we remove the graphics card
    part?") — § 4.12.1, Stage 1.15.
14. **D14 — voice in its own helper process, loaded only when used.** Built on Mike's "we don't
    really use them right now" — § 4.12.2, Stage 1.16. The one parameter left to him: **the idle
    timeout, recommended 10 minutes** (~1.5 GB held for 10 minutes after the last spoken reply; the
    first reply after it waits ~10 s).

**Risks, stated so they are not discovered later:**

1. **The server becomes strict.** Any code path still relying on the silent fallback raises after
   deploy. Stage 0's audit-log read is the mitigation; a raise is loud and harmless to data, which is
   the right failure — but it is a failure Mike could see as "that button stopped working".
2. **A brief window where Mike's phone APK cannot sign in** — between the deploy and his sideload of
   the rebuilt APK (the login request changes shape). Minutes; the web app works throughout.
3. **The interview path is safety-untested** beyond one probe (A4 suspended).
4. **Spend caps are shared.** A heavy testing day by Mike can stop Iva's sessions too — the existing
   soft-cap behaviour, now affecting two people.
5. **Before any public endpoint (Cloudflare Tunnel / Funnel):** sign-up becomes reachable from the
   internet. Its limits are built now, but `ROADMAP.md` § 5A's Cloudflare option **decrypts traffic
   at Cloudflare's edge** — every conversation would pass a third party in readable form. Tailscale
   Funnel terminates TLS on the VM. Weigh that when § 5A is taken up.

---

## 10. Coordination

- **✅ Resolved 2026-10-27: Stage B landed first** (`9f2eeac`) — the first branch below applies.
- **Day planner Stage B** (`archive/handoffs/2026-10-27-day-planner-watch-2-and-stage-b-prompt.md`,
  planned for 10-27 with Mike present) applies § E to `goals_interviewer.md` and grants
  `set_day_shape` to it. **If Stage B lands first** (D5), Stage 3.4 builds on its text and 3.5 adds
  only the two interview tools. **If this lands first,** 3.4/3.5 carry § E and the Stage B handoff
  drops it — whichever is second re-applies against the file as it is.
- **The ritual-pause session** (`archive/handoffs/2026-10-25-ritual-pause-and-ledger-followups-prompt.md`)
  edits both routing files and `register_tools()` — the same files as 2.3 and 3.5. Same rule.
- **Another window's uncommitted work** is in this tree (§ 5). Worktree build; diff before staging.

---

## 11. Not in this plan

1. A public endpoint (Cloudflare Tunnel or Funnel) — ruling 3.
2. Family mode's batched group scheduling — ruling 5; the per-user processes are built to sit under it.
3. Per-user spend caps and per-user cost reporting (A9's cost-per-active-user is the natural home).
4. Push on Android — still day-planner decision D1.
5. Users in different time zones from the VM — both users are in London; the scheduler runs on VM
   local time. Named, not solved.
6. ~~Connecting Iva's calendar or mail~~ — now § 4.10. Still out: Microsoft 365 / Outlook and any
   work account that forbids app passwords — Mark 2's OAuth route.
7. Self-serve password reset; the Synthesizer offering to resume the interview.
8. The memory watchdog's dead alert route (§ 3.12) — noticed, not filed; Mike's call.

---

## 12. Review rounds

### Round 1 — Fable, high effort, 2026-10-26: eight findings (1 structural, 7 local), all accepted

Verbatim: `archive/plans/adversarial_review_multi_user_accounts_plan_2026-10-26.md`. Each finding was
re-checked against the code before it was accepted.

| # | Finding, by what a user would see | Disposition |
|---|---|---|
| S3 | The roadmap would say multi-user is gated while a second user is live | § 2a names the Phase 7 gate and Track F, tabulates what is and is not Phase-7-grade; § 4.9.5 records it in `ROADMAP.md`; D7 asks Mike |
| L1 | The interviewer could tell her a mission was "recorded" while it waits on a card she has never seen | § 4.7: `enforce_pending_receipt()` on the interview path; coverage shows *awaiting confirmation*; `finish_interview()` refuses while Tier 1/2 is pending |
| L2 | A user with no calendar would carry a standing calendar error and ~6 failed fetches an hour | § 4.8 + Stage 1.13: a distinct not-connected result, stored as an empty successful snapshot; every scheduled reader checked (Stage 0.6) and made silent |
| L4 | Accounts would be the one store outside every backup | § 4.2; Stage 1.9 adds `data/accounts` to `metatron-backup.sh` |
| L5 | During migration Mike could get every brief and check-in twice | § 4.6: `/proc` scan beside the lock; `mask` the old unit; `ps` checks either side; the false "lock makes it safe" claim removed |
| L6 | An approved user who never signed in could get check-ins into an empty app | § 4.4/4.6/4.7: `approve` writes `state.json: not_started`; gate and start read only that file; no inference from `goals.yaml` |
| L7 | A broken import could silently stop the backlog sync and make deploys restart the server mid-turn | § 4.2: `core/accounts.py` stdlib-only, 3.9-compatible, imported lazily; § 6.1.12 runs the minting scripts under system Python |
| L8 | The "account awaiting approval" line would never appear | § 4.4: `/monitor/accounts` admits `service`, like every `/monitor/*` route |

### Verify 1 — 2026-10-26: all eight CLOSED (each re-anchored to code); two new local findings, both accepted

| # | Finding | Disposition |
|---|---|---|
| N1 | Re-running `approve` (to finish a failed step, or to re-admit her) would restart her interview from the opening | § 4.4: every provisioning write is create-only; `approve` takes pending accounts only; a new `enable` command re-admits a disabled user without touching her persona; § 6.1.5 tests it |
| N2 | The migration's `mask` step would error on the VM mid-migration | § 4.6 / Stage 4.3: `mask` dropped; the old unit file is retired instead, so a stale `restart metatron-scheduler` fails "not found" rather than starting a lock-less duplicate |

### Verify 2 — 2026-10-26: N1 and N2 CLOSED; no new findings. **Review resolved — 10 findings across three rounds, all closed.**

### § 4.10 review — Fable, 2026-10-26: two local findings on the Connections section, both accepted

| # | Finding | Disposition |
|---|---|---|
| C1 | Her Google app password would be copied to Mike's Mac in plaintext backups (7 + latest, then 30 days encrypted) and outlive *Disconnect* | § 4.10: the password lives only in `credentials.yaml`, which `metatron-backup.sh` excludes; *Disconnect* deletes it; she reconnects after a VM rebuild; D9 tells her where it lives; § 6.1.13 checks the backup's file list |
| C2 | A malformed connect or sign-up would show her password back in the error message | § 4.10 / Stage 2.7: an app-wide 422 handler returning field names only; § 6.1.13 checks all three password-carrying routes |
| C3 (from the § 4.10 verify; C1, C2 CLOSED) | Her credential and her mission/goals files on the VM would be one `git add` away from the repo's history | § 4.10 1a / Stage 1.9: `.gitignore` covers every file an account persona gets; tracked synthetic files unaffected; § 6.1.14 checks with `git check-ignore` |

### C3 verify — 2026-10-26: CLOSED; no new findings. **§ 4.10 review resolved — 3 findings, all closed. Whole plan: 13 findings across five rounds, all closed.**

### § 4.11 review — Fable, 2026-10-27: four findings (1 structural, 3 local), all accepted

| # | Finding | Disposition |
|---|---|---|
| P1 | Her sign-up permission — the one the § 0 amendment most depends on — would have had nowhere to be recorded | § 4.2 account entry gains `consents`; `/auth/register` carries and requires it (D11); `approve` copies it into `consents.json`; if D11 is declined, § 4.9.1 cites ruling 2 instead |
| P2 | Withdrawing tone profiling would leave every learned writing style in use | Withdrawal deletes `tone_shape` from her contacts (stated exception to archive-on-merge, with the reason); CRM read paths hide it without a current record |
| P3 | Mike's own tone profiling would stop working on deploy | `seed-consent mike` on the VM as Stage 4 step 0, idempotent; Stage 4 step 5 checks it |
| P4 | Any agent could reach the tone model directly, below the permission check | `run_subagent` refuses the five code-only agents; § 6.1 confirms their code callers still run and no agent file dispatches them |

### § 4.11 verify — 2026-10-27: P1, P2, P4 CLOSED; P3 PARTIAL with one new local finding (P3-N1: Stage 4 step 0 ran a script the VM did not yet have) — fixed: step 0 pulls first, which is harmless before the restart.
- P3-N1 verify — 2026-10-27: PARTIAL with one new local finding (P3-N2: nothing pushed the build to GitHub before step 0's pull) — fixed: step 0 pushes from the Mac first and confirms the VM's HEAD matches before seeding.
- P3-N2 verify — 2026-10-27: CLOSED; no new findings. **§ 4.11 review resolved. Whole plan: 19 findings across nine review rounds, all closed.**

### § 4.12 review — Fable, 2026-10-27: two findings (1 structural, 1 local), both accepted

| # | Finding | Disposition |
|---|---|---|
| M1 | Each user's scheduler would quietly load the embedding model (twice, via a second copy) and keep ~0.9 GB, undoing the saving and the "no upgrade" conclusion | § 4.12.3: every scheduled session runs on the server; the scheduler never loads a model (delegates indexing/search, fails loudly otherwise); one shared embedder; the budget is for the whole VM; the upgrade is decided by § 6.3a.3's week-long whole-VM measurement |
| M2 | The first spoken reply would still pull the voice model's code into the server | § 4.12.4: the engine check uses `find_spec`; § 6.1.17 asserts `kokoro` is absent from the server's modules, with the stub only inside the helper |
- § 4.12 verify — 2026-10-27: M2 CLOSED; M1 PARTIAL with one new local finding (M1-N1: the user-facing `/session` would have logged every scheduled analysis as a conversation, which the nightly CRM sweep reads as the user's words) — fixed: scheduled sessions use a service-only `/internal/session` that writes no conversation record.
- M1-N1 verify — 2026-10-27: CLOSED; no new findings. **§ 4.12 review resolved. Whole plan: 22 findings across 13 review rounds, all closed.**
