# Project Log — Personal AI Life Manager

Full dated history: what was built, why, what was decided, what was rejected,
and what turned out to be wrong. Newest first. **Appended at the close of every
session — never rewritten.**

**Read this when:**
- You need to know *why* something was built the way it is, not just what it does.
- A decision looks arbitrary and you want the reasoning before changing it.
- You're about to redo something and want to check whether it was already tried.
- A doc says X and the code says Y, and you need the history to tell which drifted.

Current state lives in [SESSION.md](../SESSION.md). Outstanding work lives in
[DEV_BACKLOG.md](../DEV_BACKLOG.md). Deploy and recovery detail lives in
[docs/INFRASTRUCTURE.md](../docs/INFRASTRUCTURE.md). Per-session full writeups
live in [archive/sessions/](sessions/). **This file is not loaded by
`/metatron-code`** — consult it deliberately.

---

### 2026-08-04 (B1–B4 security scoping)

Scoped execution of Track B security hardening (B1 red-team, B2 hardening pass, B3 baseline doc,
B4 error handling/degradation) at Mike's request — an effort estimate and sequencing plan, no
code changed.

**Correction to a belief `SESSION.md` was carrying:** "PoLP tool permissions in warn mode by
decision" is stale. The actual code (`core/orchestrator.py:2190-2193`, `core/router.py:128`)
shows the per-agent `allowed_tools` whitelist **is enforced** — `None` = allow-all, `[]` =
allow-none, filtered before reaching the model. The real gap is narrower: `research_agent` has
no `allowed_tools` key at all, so it defaults to all 53 tools — a one-line config fix, not a
mode flip.

**B2 turned out ~60% already done.** Believed-open per the roadmap's language but already
built: auth + `send_email` confirmation gate (`ca993fe`), CORS restriction
(`server.py:75-81`, not `["*"]`), and `run_session_anthropic`'s iteration limit (already `8`,
matching every other provider loop). Remaining B2 work: `research_agent`'s missing
`allowed_tools`; extending the existing `tools/confirm.py` gate to
`write_agent_config`/`write_config`; formal confused-deputy enforcement + test; upgrading
`filter_output()` from substring to regex/semantic; confirming `run_model_conference` is
head-layer-only.

**Decision: split B1 into two waves instead of one pass.** Mike's question — email/web access
just shipped, calendar/CardDAV are still coming, so the indirect-injection half of B1 (content
smuggled via email/calendar/web/contacts) would need re-running for every new integration if run
now. The direct-injection half (self-disclosure, persona adoption, prefix forcing — 9
categories) tests the Coordinator/Synthesizer's own prompt handling and is unaffected by
integration count. **Wave 1 (run now): B1a + B2 + B4. Wave 2 (hold): B1b (spot-checked per
integration as it ships, then one consolidated pass) + B3, gated on Track E reaching
feature-complete for this phase** — aligns with CLAUDE.md's existing deferred item, "Full OWASP
audit before Beta."

**New, at Mike's request: a recurring security-review protocol**, so this doesn't need
re-scoping from zero each time. Two triggers: event-triggered (any new untrusted-content
integration gets a one-off indirect-injection spot-check at deploy) and calendar-triggered (a
quarterly, or per-roadmap-phase, re-run of the B1a suite + B2's cross-agent exfiltration
probes). Scoped to be written into B3's own baseline document
(`archive/security/security_baseline_*.md`) rather than a new standing file, per CLAUDE.md's
"One Home Per Rule Class."

**Options considered and rejected:** running the full B1 sweep now as one pass (would require
re-running the indirect-injection half per future integration); writing B3 before B1/B2 settle
(pure rework — it's a synthesis document).

**Estimate:** Wave 1 ≈ 4.5–5.5 sessions / about a week; Wave 2 ≈ 1–1.5 sessions plus near-free
per-integration spot-checks, timed to Track E's pace rather than a fixed date. Resource
intensity moderate, not heavy — bounded one-time API spend (Vertex + GPT-4o/o3 for red-team
prompt generation), no new infra, two `./deploy.sh` points (after B2, after B4), no meaningful
GCP billing-cap risk.

Nothing deployed, no code changed. Full detail:
[archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).

---

## Rolling handoff paragraphs (superseded)

`SESSION.md` carries one live handoff paragraph, rewritten each session. The
previous ones are kept here in order, newest first, because several contain
corrections to the one before them.

*Updated: 2026-08-05 (ROADMAP.md gap closed; `/archive` gets a sixth step) — **User asked, after
the B1a session's own `/archive` run: "did the B stuff move out of dev_backlog and get noted in
overall project progress?"** Nothing had moved out of `DEV_BACKLOG.md` — B1a only added entries.
But "overall project progress" split in two: `SESSION.md`/`PROJECT_LOG.md` correctly showed B1a
done; `ROADMAP.md` — the live tracker Track B actually lives in — had never been touched and
still read as pure future work. **Root cause: `.claude/commands/archive.md` never mentioned
`ROADMAP.md` at all.** Fixed both — added a ✅ status note to `ROADMAP.md` §B1 (B1a done, B1b
still open, matching the inline-note style A7's gate already uses), and gave `/archive` a sixth
step requiring a `ROADMAP.md` check every session, with this exact miss as the worked example.
Docs-only, nothing deployed. Carried in, unchanged: B1a's own findings (sticky MUST_SURFACE
context on `sarah_chen`, stale `research_agent` backlog entry — both already filed);
`[DB-0804-01]` scheduled-fire check still pending; SMTP send path never exercised; APK rebuild
pending; A7 blocked on checks 10/12 and the rest of B1.*

*Updated: 2026-08-05 (two parallel sessions closed: AgentRecord/WS-drain fix, A7 pipeline probe) — **Proactive check-ins root-caused and fixed** (parallel session): `core/router.py:166`'s `log_model_error()` was handed a live `AgentRecord` instead of a string, crashed on `json.dump`, and masked the real underlying failure — 18 of 19 scheduler errors in 7 days. One-line fix, deployed `10bf194` and verified live on the VM (`ec55788` closes the backlog entry, docs-only). **Not yet confirmed: a real scheduled fire completing end-to-end** — filed as `[DB-0804-01]`, three time-gated checks (~23:03, 07:30, one-week count 2026-08-11). Same fast-forward also fixed `deploy.sh`'s decorative WS-drain gate and closed two stale backlog entries. **Separately, this session closed A7's last residual gap:** a `pipeline` suite added to `tests/run_a4_safety.py` runs the A4 clinical scenarios through the real Coordinator→Synthesizer path, inverting the check (flag substance must surface, raw token must not) — **3/3 PASS live against gemini**, tests-only, no deploy needed. **A7 itself is still not signed off** — checks 10/12 and B1 remain open by deliberate deprioritization. Unchanged: SMTP send path still never exercised, APK rebuild pending.*

*Updated: 2026-08-05 (backlog trust repair) — **The backlog never ballooned; the counter was wrong.** `sync_dev_backlog.py` partitioned on a `## Done` heading that had never been written, so struck-through entries counted and **closing an item raised the number**. Fixed — now `N new · N untriaged · N open`, currently **`0 · 0 · 45`**. A verify-before-refile sweep found **about a third of checked items stale**: four closed with evidence, three marked `needs re-derivation`, all survivors given `DB-MMDD-NN` IDs plus who filed them, how, and the origin SEQ. **Biggest find — `AgentRecord is not JSON serializable` is not a logging nuisance: 18 hits in 7 days against 19 total scheduler errors, so proactive check-ins are failing** (`companion_checkin` ×13, **[DB-0803-02]**). Nine tool denials resolved by reading the conversations they occurred in, not the denial text; `physical_health` write granted with `medication_profile` guarded in Python. `/backlog` carries the ritual; `/metatron-code` and `/archive` report the count only. ~~**`9361537` needs `./deploy.sh`.**~~ **Deployed 2026-08-04**, as a side effect of that session's own deploy fast-forwarding past it. Carried in from the parallel window and unchanged: the out-of-band confirmation gate and `send_email` are built (`ca993fe`), enforce mode off by decision, SMTP send path still never exercised, APK rebuild pending.*

*Updated: 2026-08-04 (app — dismissable transcription readout) — Short single-feature session on `static/index.html`. The footer's Whisper readout had no height cap and no way to dismiss it, so a long dictation grew the footer until it crowded the conversation off a phone screen. It now sits in a bordered box that is hidden when empty, capped at ~3 lines with internal scroll, and cleared by a `✕`, by a 12s timer, or by starting a new recording. Safe to auto-hide because `sendToServer()` already puts the same text in the conversation as a user bubble — the readout is the pre-send check, not the only copy. **Not deployed and not tested** — reasoned from the code, no server was started. It needs `./deploy.sh` **and an APK rebuild**, since UI structure changed; that rebuild now also carries the still-pending password-reveal toggle. Unchanged from before: auth is live in production (`8e5c47e`), `fetch_url`/`read_email` are wrapped by `tools/untrusted.py`, and **item 5's Python confirmation gate is still the thing blocking anything outward-facing** — Decisions A/B/C await Mike.*

*Updated: 2026-08-04 (auth + injection defense + context second pass — both closed) — **Track B2 authentication is live and verified in production** (`8e5c47e`): every endpoint 401s unauthenticated, the app shell still loads, and `/ws` is gated by a first-frame handshake because Starlette runs no HTTP middleware for a WebSocket. The server **fails closed** without `METATRON_AUTH_PASSWORD`. **`fetch_url` and `read_email` are live, granted to `logistics` only, all external content wrapped by `tools/untrusted.py`** — the SSRF guard is not theoretical, the VM's metadata server hands a working OAuth token to an unauthenticated request. **Separately, the context-file work closed:** cold start is **~87k → ~26k tokens**, verified against a live `/metatron-code` run; `SESSION.md` has a **200-line ceiling** (growth below it is fine — the old "never longer than before" rule was a ratchet); `/archive` carries the close-out. **Next:** item 5's Python confirmation gate (Decisions A/B/C await Mike), and an APK rebuild for the password reveal toggle.*

*Updated: 2026-08-04 (backlog triage, A4 gate, VM outage) — **The A4 clinical-flag gate is CLEARED on the cloud path, 6/6** (`tests/run_a4_safety.py`, report `tests/a4_safety_rerun_2026-08-04_gemini.md`) — the suites are scripted now, not manual prose. **The bigger find was not the gate:** `physical_health` had never been granted `read_agent_config`, so `MEDICATION_MISSED_CRITICAL` — which must classify from the stored medication profile, never inference — was **structurally unfireable in production.** Granted; `write_agent_config` deliberately not. **Nothing deployed, deliberately:** the server now fails closed without `METATRON_AUTH_PASSWORD` and the VM does not have it (verified) — deploying stops production rather than updating it. **`deploy.sh:54` checks the Mac's `.env`, not the VM's**, and today's run passed that guard and pushed; only a 4-hour VM outage (guest lost all networking while GCE said `RUNNING`, root cause unknown, recovered by stop/start) stopped the pull. Two gate pieces remain before A7: a **pipeline probe** (a flag can fire in MW and still be held at the Synthesizer) and the local/Ollama run.*

> **Correction, same day:** the claim above that `deploy.sh:54` checks the Mac's
> `.env` is wrong — the guard runs inside the remote heredoc and greps the VM's. See the
> 2026-08-04 auth entry below for the evidence and for the real bug it led to.


*Updated: 2026-08-03 (context-file audit, closed) — **cold start is ~88k → ~28k tokens, verified against a live run rather than estimated.** `SESSION.md` split into this primer plus [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md); deploy/recovery detail to [docs/INFRASTRUCTURE.md](docs/INFRASTRUCTURE.md); [ROADMAP.md](ROADMAP.md) is an abridged live copy — **the full plan under `archive/plans/` is static and must never be edited.** `DEV_BACKLOG.md` is no longer autoloaded (still synced every session); read it when working the backlog. `/archive` now carries the close-out ritual. **One thing to act on:** the test run surfaced a pre-sign-off gate at `ROADMAP.md:113` — prefix-caching moved dynamic context out of the system prompt, so **the A4 clinical-flag hard-fails must be re-run before A7 sign-off**. Audit any session's real load with `python3 scripts/audit_context_load.py`. Deployed: nothing — docs only.*

*Updated: 2026-08-03 (5th window, close) — **`networks/default` HAS THAWED (probe-tested); the 26-hour outage is fully closed and the support case can be closed. `CLAUDE.md:339` still warns against it and is now stale.** Two items carried into `DEV_BACKLOG.md`: unsurfaced-opportunity instrumentation (which had lived only in this file's prose and nearly aged out) and the D2 item 5 roadmap-staleness note. **The external-IP saving is withdrawn — that IP is the VM's only egress path.** Previously: (4th window) — **doc drift reconciled, and the drift rule generalised.** The previous window's HTTPS correction is confirmed correct **against the live VM**, not just internally: `https://.../health` → `{"status":"ok"}`, `http://` → empty reply. Two things it missed, both now fixed: (1) `core/server.py`'s docstring still said "over HTTP" while `__main__` serves HTTPS whenever a Tailscale cert is present — **fixing the prose in CLAUDE.md did not prompt anyone to check the code comment saying the same wrong thing**; (2) the VM's **ephemeral external IP was recorded in four places with three different values**, none wrong when written, live being a third address — the literal is now removed everywhere in favour of a `gcloud describe` lookup, because the IP reassigns on every stop/start and there is an active pause/resume workflow. **New standing rule: do not write down values with a short half-life.** Backlog entry filed as the pattern, not the two bugs — this drift class is invisible to reading and only fails on execution; a smoke script over CLAUDE.md's executable claims is scoped but unbuilt. **`deploy.sh`'s HEAD assertion exercised its match path on a real deploy for the first time** (previously simulation-tested only) — `Verified: VM HEAD matches.` Deployed `b83f283`.*

*Updated: 2026-08-03 (3rd window, close) — **`./deploy.sh` now verifies itself.** It captures HEAD after the push, re-SSHes after the restart, and **exits non-zero if the VM is not running what was just pushed** — because the failure mode here is silence, not an error (two false "deployed" records on 2026-08-02, both caught only by a human happening to look). An unreadable remote HEAD reports **unverified**, deliberately distinct from success or failure. Failure paths are simulation-tested only; the next real deploy exercises the match path. Four loose items filed into `DEV_BACKLOG.md`, including **two corrections to what was believed done:** (1) **check-in activity gating is only half solved** — the gates shipped this morning stop check-ins interrupting a live conversation, but nothing stops them firing on a day the user never spoke, which was the actual cost case; (2) **roadmap D2 item 5 is mis-scoped** — it targets the Coordinator assuming ~7 turns, but measurement shows Coordinator = 1 turn and `logistics` = 8. Pushed through `9799ba3`. Note the new assertion tells you *what* is live, not *who* deployed it — with parallel windows open, either window's deploy ships whatever both have committed.*

*Updated: 2026-08-03 (2nd window, close) — **Rule Redundancy done: every behavioural rule now has one home, checked at three speeds.** The five duplicated preferences are gone from the live `mike.md` (5 audit findings → 1). `write_persona` warns at write time; `daily_rule_audit` sweeps at 05:30 as a `function:` job costing **zero model tokens**, reporting each finding once into `DEV_BACKLOG.md`. Layer-ownership table in CLAUDE.md → **One Home Per Rule Class**. Morning/evening sessions are **not interruptible** — they redirect openly rather than folding in. Deployed through `a03ed7e`. Earlier this window: check-in restraint live (60m quiet / 180m floor); the VM formally owns persona config — `deploy.sh` must never push it; `write_profile`/`read_profile` capture biographical facts with contact details kept out of every prompt.*

*Updated: 2026-08-03 — **the calendar now delivers.** CalDAV live with recurrence, alarms and all-day events; `get_weather` + `get_environmental_snapshot` built; tool permissions shipped in warn mode with denials feeding `DEV_BACKLOG.md`; VM backup closes a real single point of failure. Deployed `cfcd212`, `6865058`. **Phase 4 (scheduler write access) is written but uncommitted — one step from done.** The SEQ 021 fixes noted below as undeployed have since shipped in `6601479`. Earlier: spend guard + rate limiter live; GCP verified clean and `default` VPC unfrozen; Synthesizer recap and timestamp fixes deployed. Update this file at the close of every chat so the next chat — or any parallel chat window — starts from current state.*

---

## Closed backlog items

*Moved out of `DEV_BACKLOG.md` 2026-08-03 — that file tracks what is outstanding, not what is finished.*


### Deploy verification — 2026-08-03

~~**Nothing checked that the VM was running what the Mac had committed.**~~ `deploy.sh` now asserts it, and **exits non-zero on mismatch**.

The reason it had to be automatic rather than a documented habit: **the failure mode is silence, not an error.** Two false records on 2026-08-02 — a deploy that failed at the SSH step and left the VM a commit behind without complaint, and a parallel chat's *"NOT yet deployed"* note that was already stale because a deploy from another window had shipped its commit as a side effect. Both were caught by a human happening to look, which catches nothing on the day nobody looks.

How it works: capture `git rev-parse HEAD` after the push succeeds, then re-SSH after the restart and compare. A **second** SSH on purpose — the deploy heredoc interleaves pip, systemctl and drain-loop output, so a SHA parsed out of it would be guesswork. Three outcomes: match (silent pass), mismatch (prints both SHAs, the *"you are about to test OLD CODE"* warning, and the `git status && git pull` command that shows the real error), and unreadable HEAD (says the deploy is **unverified** rather than claiming either result). All three branches tested, including that a failed SSH capture doesn't abort early under `set -e`.

**This bites hardest with parallel chat windows open.** Either window's deploy ships whatever both have committed, so a per-session "not deployed" note is only true until the other window deploys. The assertion tells you what is live; it does not tell you who put it there.

### Rule redundancy — deployed 2026-08-03 (`0077a63`, `a03ed7e`)

One home per rule class, checked at three speeds. Documented in CLAUDE.md → *One Home Per Rule Class*.

- ~~**Repeat-detection.**~~ *"A repeated instruction is a failure, not a new one"* in `synthesizer.md`, plus a write-time check: `write_persona` now appends a warning when a new preference restates a rule already in force. Warns, never blocks — refusing a write to keep a file tidy discards what the user actually said.
- ~~**One home per rule class, documented and checkable.**~~ `core/rule_classes.py` holds the classes and the owning layer; CLAUDE.md holds the table.
- ~~**Promotion deletes the original — clear the live debt.**~~ All five duplicates removed from the VM's `config/personas/mike.md`, each only after its replacement was verified live *on the VM* rather than merely committed on the Mac. Backups at `~/metatron-backups/mike.md.pre-dedup*`. The file is down to two genuinely personal preferences. Audit on the live files went 5 findings → 1.
- ~~**Reconciliation.**~~ `daily_rule_audit` at 05:30, a `function:` job costing **no model tokens**; findings become `RULE_CONFLICT` events and reach this file through the existing sync, reported once each. `scripts/check_rule_overlap.py` is the interactive version for a development session. End-to-end verified: VM audit → quality event → sync → Inbox.

**Adjudicated, not a duplicate:** the audit flagged `mike.md:9` *"No commendation or validation… drop affirmations, compliments, and filler"* against `synthesizer.md:82` *"Do not tell the user to enjoy things."* They share the sycophancy class, but :82 forbids sign-offs and only *mentions* commendation as an analogy — it does not forbid it. Mike's rule says something the shared rule does not, so it stays in the persona layer. Worth promoting to the agent layer only if the user says sycophancy suppression should apply to everyone; they have so far said that only about "enjoy".

**Known limits, so a clean report is not mistaken for proof.** Detection is class-based regex plus word overlap: 5/5 recall on the real 2026-08-03 set and 0 false positives across eleven novel preferences, but the *partner* it names was wrong three times in five. The flagged preference is the reliable part. An earlier version also compared agent files against each other and was unusable — the specialist files carry intentional parallel boilerplate (*"Mandatory pass. Runs every session"*, *"Voice mode:"*) that scores as near-identical because it is, deliberately. Dropped from the daily job; still available via `check_rule_overlap.py`.

### Check-in restraint — deployed 2026-08-03 (`ae252ab`..`HEAD`)

Four related complaints, one root cause and four fixes. **The cause was not an agent file:** `companion_checkin`'s own prompt instructed it to *"lead with the most useful outstanding item… be specific about which one and why it matters now"* — every 180 minutes, all day. An unresolved calendar item was therefore correctly surfaced six times.

- ~~**Check-ins fire regardless of whether a conversation is already live.**~~ *"Check ins… only need be done if there's not an ongoing dialogue"* — SEQ 020. Two opt-in gates in `core/scheduler.py`: `quiet_after_user_minutes: 60` (don't interrupt) and `min_gap_minutes: 180` (never more often than). `interval_minutes` becomes the poll rate, not the send rate. **Cost: strictly lower than before** — polling is local file reads with no model call, and `min_gap` preserves the old ceiling of ~5/day. Verified in production reading real conversation data. Only `companion_checkin` is gated; `morning_brief` and `evening_close` still land on their anchors by design.
- ~~**Check-in prompt too long / demands an outstanding item.**~~ Rewritten in both `config/templates/scheduler.yaml` (the baseline every new persona inherits — which also hardcoded "Mike" in a file used to provision other people) and mike's copy. Template cadence corrected 90 → 180.
- ~~**Repeating pending items until they become noise.**~~ *"Raise a thing once"* in `synthesizer.md`.
- ~~**Stop telling the user to "enjoy" things.**~~ Made universal in `synthesizer.md` rather than a per-persona preference, at the user's direction — "wasted language and too sycophantic."
- ~~**Over-indexing on sleep disruption.**~~ Two rules in `synthesizer.md`: explain a recommendation the first time and not every time (preserving the Constitution's "always explains its reasoning" for the case where it is genuinely new), and beware the loudest available signal — sleep dominates because it is the only thing consistently measured, not because it explains everything. **Where thin, ask for the missing data rather than over-reading what is there.**

**Root cause of the sleep problem is data breadth, not weighting** — still open, and the instruction changes above are mitigation, not a fix. Promoted to *Open — needs building* so it is not lost inside a Done section.

- **Synthesizer opened responses by recapping facts the user had just given.** Fixed in `synthesizer.md` under "Direction and prioritization"; deployed 2026-08-02 (`799aa3f`). *SEQ 002.*
- **Synthesizer echoed a user-claimed timestamp instead of checking the clock.** Fixed across `tools/ambient.py`, both head-layer agent files, and the message-receipt stamping in `core/server.py` / `core/orchestrator.py`; deployed 2026-08-02 (`b184d92`). *SEQ 008.* — **This closes the 2026-08-01 SEQ 011 request** *"You'll need to check your timestamps before messaging… Let's add that to things to do."* Raised by the user on 08-01, fixed on 08-02 before the backlog existed.

- **Specialists invented dates because they were never given a clock.** Logistics filed a record 14 months in the past. Fixed by injecting the system clock into the specialist branch of `_run_single_agent()`; deployed 2026-08-03 (`6601479`). *SEQ 021.* Same root family as the timestamp request above.

---

## Dated history

### 2026-08-08 (travel/routing tools, Google API onboarding, CRM and profile hardening) — `c4ff279`, deployed and verified live

Writeup: [archive/sessions/2026-08-08 — Travel Tools, Google API Onboarding, CRM Hardening.md](sessions/2026-08-08%20—%20Travel%20Tools%2C%20Google%20API%20Onboarding%2C%20CRM%20Hardening.md)

Ran across several linked threads: closing a `DEV_BACKLOG.md` quick-scoring pass with real
builds, onboarding a first batch of Google APIs, and — the most consequential part — a live
mid-session reversal on Google Contacts that changed how this project weighs third-party
integrations against local fixes.

**Pre-departure travel checks, built in stages.** `tools/tfl_status.py` (`get_tfl_status`,
renamed from `get_transit_status` — collided in name, not design, with an unbuilt GTFS-RT
placeholder that had sat in the original Phase 5/6 plan since 2026-05-26) covers TfL line/bus/
National-Rail status, no key needed. `tools/flights.py` (`get_flight_status`) uses AeroDataBox
via RapidAPI — **first recommendation was wrong**: read API.Market's "Basic" plan as the ongoing-
free option when it's actually a 7-day trial; RapidAPI's identically-named Basic plan is the one
that's genuinely unrestricted-duration, confirmed only after fetching AeroDataBox's own pricing
page directly rather than trusting an aggregator summary. `tools/routing.py`
(`get_travel_time`) **also went through a real design reversal**: first version routed London
transit/walking through TfL's Journey Planner by default, Google Maps as fallback — backwards.
Mike corrected it: Google Maps Routes API is the default router everywhere, every mode; TfL is
demoted to a secondary cross-check (`get_tfl_status` for disruption awareness, never for
computing a route). That correction surfaced a real architecture question — a NYC-based persona
visiting London needs London's cross-check tool the same way a resident would, which a
persona-cached "home region" setting would silently miss — resolved by making
`config/modules/regional_transit.yaml` a shared, non-persona-scoped library and
`get_regional_transit_info(city)` resolve per-query against whatever city is actually relevant
right now, never a cached home city. Confirmed this costs nothing extra in the common case: the
lookup is a local file read either way, no network, no billing.

**Google Maps Routes API onboarded onto the existing `metatron-ai-499810` GCP project** — no new
vendor account, same billing caps already in place. Enabled via `gcloud services enable`, key
created via `gcloud alpha services api-keys create` restricted to `routes.googleapis.com` only
via `--api-target`, so a leak can't spend on other Maps Platform SKUs.

**Google Contacts (People API) — built, then reversed same day, and the reversal is the more
important artifact than the code.** Built a full OAuth 2.0 integration (Desktop-type client,
local-server consent flow, `contacts.readonly` scope) to answer a real recorded need
(`DEV_BACKLOG.md`: "misattributing the user's email to the contact"). Along the way, verified
directly against Google's own support page that the app's Testing publishing status means
consent — and the refresh token — expires **7 days** after granting, since `contacts.readonly`
is a sensitive scope; Production removes this but costs 3–5 business days of review plus a
hosted privacy policy. **Before spending that review effort, Mike asked the right question: does
this need a third party at all?** Checking `tools/crm.py`'s `write_contact` directly showed the
actual bug was local — zero validation against the user's own identity, nothing OAuth-related.
And the "bring in contacts I already have" value has a portable, non-Google-specific answer:
vCard (`.vcf`) is the real interchange standard (Google/Apple/Outlook all export to it), parsed
with `vobject` (verified live on PyPI), no OAuth, no token to keep fresh. Reversed same day:
`read_google_contacts` unregistered from `core/orchestrator.py` (import, schema, and handler all
removed — structurally undispatchable, not just ungranted), `people.googleapis.com` disabled on
the GCP project. Code and `.env` credentials left in place, dormant, not deleted, in case it's
revisited. **Lesson worth carrying forward: the OAuth path was technically correct and fully
working — the mistake was building the more complex answer before checking whether the recorded
bug actually needed it.**

**CRM and profile hardening, built from the reversal's diagnosis.** `write_contact` now refuses
outright on an exact match to the user's own email/phone (`profile.yaml`), and flags — via
`difflib.SequenceMatcher`, saves anyway — a near-miss, since a hard block would also refuse a
legitimate similar-looking contact. Mike's own follow-up broadened this correctly: most
transcription errors land on details no code check can validate (a misspelled third-party name,
a garbled address), so `relationships.md` now carries a standing read-back instruction for every
captured contact detail, not just the ones the code flags. Separately, `write_profile` now gates
*changes* to an already-set email/phone/address behind the same confirm mechanism as
`send_email`/`write_config` — first-time capture still writes immediately.

**Also built:** `shownIds` oldest-first eviction fix (`static/index.html`, was a full `.clear()`
past 100 exchanges, causing duplicate renders); Google Places and Pollen APIs researched and
documented where they'd plug in (`logistics.md`, `recreation_hobbies.md`, `research_agent.md`),
neither built — Places is blocked on a location signal (no GPS capability exists yet, raised but
explicitly not scoped this session); Level 3 web-browsing access scoped
(`archive/plans/level3_web_actions_scope_2026-08-06.md`) but not built, same "propose before
building" discipline as the 2026-08-04 outward-actions document it mirrors.

**Deploy caught a real gap, not just a formality.** `.env` never travels with a deploy;
`AERODATABOX_API_KEY` and `GOOGLE_MAPS_API_KEY` didn't exist on the VM after the code push, which
would have left the new tools silently returning "not configured." Appended (not overwritten)
to the VM's `.env`, services restarted, journal checked directly for a clean startup rather than
trusting `systemctl is-active` alone.

**Commit scoped carefully around concurrent work.** Another window had `ROADMAP.md`,
`SESSION.md`, `archive/PROJECT_LOG.md`, and several archive/test files staged or modified when
this session went to commit. Used `git commit <explicit pathspec>` rather than `git add -A`, so
the commit contains exactly this session's 25 files and the other window's pending work — staged
or not — was left completely untouched, verified with `git status` before and after.

---

### 2026-08-06 (billing investigation + region latency analysis) — investigation only, no commits, no deploy

Writeup: [archive/sessions/2026-08-06 — Billing Investigation and Region Latency Analysis.md](sessions/2026-08-06%20—%20Billing%20Investigation%20and%20Region%20Latency%20Analysis.md)

Mike asked why Compute Engine billing showed nothing from Aug 4 onward while Vertex AI usage
looked elevated on Aug 2 and Aug 4, then a follow-on pair of questions about whether us-central1
is the right region given the app runs from London, and how much of that region latency is
actually felt per turn.

**Billing gap — checked `gcloud` directly rather than trusting the console.** `metatron-vm` has
been `RUNNING` continuously since 2026-08-03 23:47 PDT (the stop/start pair right before that is
the already-logged 4-hour outage recovery), no stop/start since, neither budget cap fired. **No
BigQuery billing export dataset exists** — `bq ls` on the project is empty, so there is no
per-SKU attribution available, only the console report view, which lags for GCE line items
(typically 1–3 days) in a way Vertex AI's same-day metered billing does not. Read: the Compute
Engine gap is very likely reporting lag, not an actual billing gap — the VM is confirmed running
and charging. The Vertex spike lines up with real heavy-call activity already in this log for
both dates (SEQ 021 + Synth self-development on the 2nd; the A4 gate rerun, B1a's 75 live
red-team cases, and decisions A/B/C testing on the 4th) — a plausible explanation, not a proven
one, since there's no SKU-level way to rule out something double-firing. **This BigQuery-export
gap was already recorded once, in this log, as a lever "recorded, not applied" (line ~1431) and
never became an actionable item — it is filed as [DB-0806-03] this time specifically so it
doesn't happen again.**

**Region pricing — pulled live from the Cloud Billing Catalog API rather than estimated from
memory.** E2 vCPU and RAM both carry a flat **10.0% premium** in europe-west1 over us-central1;
Balanced PD and static IP are identical in both. Applied to the actual e2-medium 24/7 numbers
already in `CLAUDE.md` (~$29.15/mo), europe-west1 comes to **~$31.75/mo — about $2.60/mo more**.
europe-west2 (London itself) was also priced for comparison: a 22.7% CPU premium, more than
double europe-west1's gap, for a latency win too small over europe-west1 to justify it (Belgium
to London is already a short hop).

**Latency compounding — traced through the real code paths, not assumed.** The transatlantic
leg is paid **twice per voice turn**, not once, given the app's actual flow: `POST /transcribe`
(`static/index.html:1119`) is a full round trip for STT before the pipeline even starts, and the
WebSocket send (`static/index.html:973`) then waits on time-to-first-token of the streamed
response. On us-central1 that's roughly 260–300ms of pure geography tax per turn; on
europe-west1, roughly 20–30ms. **This does not compound with the internal Coordinator →
specialist(s) → Synthesizer pipeline** (`core/orchestrator.py:2396` dispatches specialists in
parallel via a thread pool) — every one of those calls is VM → Vertex's `global` endpoint, which
never leaves Google's backbone regardless of which region hosts the VM. Region choice only taxes
the two client-facing edges of a turn, not the internal call count. Net estimate: **~200–280ms
saved per turn** by moving to europe-west1 — real, but small against the multi-second-to-
tens-of-seconds pipeline compute time itself, which the log elsewhere already describes as the
dominant cost ("routing + specialist dispatch + synthesis, often tens of seconds").

**No changes made.** Both topics are exploratory; nothing was decided or scheduled. Filed
**[DB-0806-03]** (BigQuery billing export) and **[DB-0806-04]** (us-central1 → europe-west1
migration, sized but not decided) into `DEV_BACKLOG.md`. Checked `ROADMAP.md` — neither topic is
tracked there (Track D infrastructure covers dedicated-hardware migration and encryption, not
GCP region choice), so no roadmap edit.

---

### 2026-08-05 (backlog quick-bucket sweep, first SMTP send, APK rebuild, dictated-email fix)

Writeup: [archive/sessions/2026-08-05 — Backlog Quick-Bucket Sweep, SMTP Test, APK Rebuild, Dictated-Email Fix.md](sessions/2026-08-05%20—%20Backlog%20Quick-Bucket%20Sweep%2C%20SMTP%20Test%2C%20APK%20Rebuild%2C%20Dictated-Email%20Fix.md)

Ran concurrently with (at least) two other windows working Track B — this session touched only
`DEV_BACKLOG.md`, `tests/run_a4_safety.py`, `static/index.html`, `config/modules/spend_guard.yaml`,
`archive/PROJECT_LOG.md` (a dead-link fix, appended not rewritten), `core/server.py`, and
`core/voice_pipeline.py`. Deliberately never touched the other windows' in-flight,
uncommitted `SESSION.md`/`ROADMAP.md` edits — see the process note near the end.

**Quick-bucket sweep: 44 → 32 open.** Verify-before-refile discipline caught real drift both
ways:

- **Two items were already fixed but never crossed off** — `deploy.sh`'s WS-drain gate and the
  VM-down detection, both landed in `10bf194` (2026-08-04) with no corresponding backlog close.
- **This session's own first-pass verification of one entry was itself wrong, and got
  corrected in the same session.** DB-0803-04 (`write_config()` heading duplication) was
  checked earlier the same day, found "cited code absent" by reading only
  `tools/config_writer.py`, and marked unconfirmed. Re-checking on this pass found `_titled()`
  living one layer up, in `core/orchestrator.py:187-199` — exactly the mechanism the original
  entry described, working as designed. **The lesson, stated for whoever hits this pattern
  next: "cited code does not exist" is only true of the one file actually checked.**
- **DB-0803-06 (`shownIds` eviction) re-derived and confirmed real**, not stale: both call
  sites (`static/index.html:944,971`) still do a full `.clear()` instead of incremental
  eviction, which can duplicate-render catch-up messages past 100 exchanges. Left open — a real
  fix, not a re-verification, is still owed.
- **Pre-2026 hallucinated-log spot-check blocked, not closed**: live `mike` data is VM-owned
  per the persona rules; the Mac's local mirror doesn't even contain the originally-cited
  filenames. Found a *new* instance of the same bug class while looking — `2024-08-04.json`,
  two years stale — sitting next to a correctly-dated file in the same directory. Needs the VM
  to resolve; was unreachable for part of this session (see below).
- Three real fixes: `tests/run_a4_safety.py`'s `clinical`/`finance` report filenames now
  suite-qualified (were silently overwriting each other same-day); `.message` bubbles gained
  `overflow-wrap: anywhere` (the bubble-width half of a 2026-08-02 complaint the footer-readout
  fix never covered); `spend_guard.yaml` pricing corrected against the live Vertex AI pricing
  page — flash-lite output was **~3.75x underestimated** ($0.40 vs. actual $1.50/1M tokens).

**VM went unreachable mid-session, then came back.** `sync_dev_backlog.py`'s own VM-down
detection (see above) fired correctly during this session's `/metatron-code` load. Came back
reachable partway through; the SMTP test and APK rebuild, both requiring live VM/deploy access,
were held for explicit go-ahead rather than run opportunistically the moment connectivity
returned — user confirmed before either ran.

**First real email this system has ever sent.** Ran the full production `send_email` path live
against `mike` on the VM: `request()` → `PENDING_CONFIRMATION` → `tools.confirm.approve()` →
second call with matching `confirm_token` → real Gmail SMTP over STARTTLS, port 587. Landed in
`diamond.mike.mt@gmail.com`. **Bonus finding, not a bug:** the fingerprint match in
`consume()` correctly refused a second call whose subject/body didn't match what was approved —
caught a scripting mistake in this test itself, exactly the protection it exists for.

**APK rebuilt and content-verified, not just built.** `npx cap sync android && ./gradlew
assembleDebug` succeeded, but the output file's mtime looked stale (matching an old build) —
rather than trust it, unzipped the APK and grepped the packaged `index.html` to confirm the
`overflow-wrap` fix was actually present. It was; the mtime was misleading, not the build.
Served from the Mac over Tailscale for sideload — **install/verify on the phone is still Mike's
step, not done from here.**

**Two decisions made by explicit user instruction, not inferred:**
1. **Check-ins should keep firing through silence** — the "not gated on presence" backlog item
   is closed as not-a-bug. The original admonition behind `quiet_after_user_minutes` was against
   spamming an *actively engaged* user, not against reaching out during a quiet stretch.
   `core/scheduler.py:173-196` already implements exactly this and nothing more — confirmed, no
   code change made.
2. User asked to verify a claim that item 3 (browser live-refresh) "had already been handled"
   before proceeding. **It was not, and saying so required distinguishing two similar-looking
   fixes.** `ace22c7` (2026-08-01) fixed a real, related bug — half-open WebSockets from
   Android's WebView freezing in the background, detected via a 45s ping-staleness check. But
   the backlog entry's *own* diagnosis explicitly rules out transport ("sync is confirmed
   working, this is a client-side render path") — a different code path `ace22c7` never
   touches, since its reconnect logic never fires on a socket that wasn't actually dead. Closing
   this on the strength of the adjacent fix would have been the same failure class as the
   DB-0803-04 correction above, one layer up. Left open, flagged as needing live two-device
   reproduction rather than code reading.

**Built: dictated-email correction.** `core/voice_pipeline.py.correct_known_addresses()` —
regex-matches an email-shaped (or `@`-dropped, domain-anchored) span in a transcript, scores it
against the persona's known addresses (self + saved CRM contacts, reusing
`tools.mail._known_recipients()`) via `difflib.SequenceMatcher`, and snaps it to the best match
above a 0.72 ratio threshold. Wired into `/transcribe` via a new optional `persona` query param
— omitted, behavior is byte-for-byte unchanged from before this session. **Tested in isolation
before wiring in**, against both documented real cases (`diamond.mic@gmail.com` →
`diamond.mike@gmail.com`, ratio 0.93; `diamond.like.gmail.com` → `diamond.mike@gmail.com`,
ratio 0.91 via the no-`@` fallback regex) and negative cases (an unrelated third party's real
address left untouched at ratio 0.52; an exact match on a different known contact preserved
correctly; a plausible typo of that same different contact still resolved to the right person,
not redirected to Mike's).

**Process note — three separate collisions with a concurrently-active window(s), all handled
by scoping commits rather than resolving them:** `SESSION.md` was found mid-edit reverting
2026-08-05 progress notes back to a 2026-08-04 state early in the session; later, `ROADMAP.md`,
`.claude/commands/archive.md`, and further `PROJECT_LOG.md` content appeared, corresponding to
what turned out to be a B1a red-team execution and a `/archive`-tooling fix running in another
window. **Never staged, committed, or discarded any of those files' pending changes** — every
commit this session was preceded by `git diff --cached --stat` to confirm only files this
session actually edited were included. This is not a resolution of the underlying multi-window
coordination gap, just the safe default when it's hit mid-task.

**Commits:** `2c097b3` (quick-bucket sweep, 3 real fixes, deployed — VM HEAD verified),
`30dd9b6` (SMTP + APK backlog closures, docs-only, not separately deployed), `a08e38a`
(check-in decision + dictated-email correction, deployed — VM HEAD verified, both systemd
services confirmed `active` post-restart).

### 2026-08-05 (ROADMAP.md gap closed; /archive gets a sixth step) — docs-only, no commit required

Writeup: [archive/sessions/2026-08-05 — ROADMAP Gap Fix and Archive Six-Step.md](sessions/2026-08-05%20—%20ROADMAP%20Gap%20Fix%20and%20Archive%20Six-Step.md)

Direct follow-on to the same-day (calendar-adjacent) B1a session below. User asked, after that
session's own `/archive` run: "we've moved the B stuff out of dev_backlog and made note of it on
overall project progress, right?" — a premise check, not a request.

**What the premise check found, and why it mattered:** the answer to both halves was more
nuanced than a yes. Nothing had moved *out* of `DEV_BACKLOG.md` — the B1a session had only ever
*added* to it (the completion entry, the MUST_SURFACE finding, the stale `research_agent`
correction). And "overall project progress" turned out to mean two different documents that had
diverged: `SESSION.md` and `archive/PROJECT_LOG.md` both correctly reflected B1a's completion,
but `ROADMAP.md` — the actual live tracker for phase-gated work, Track B included — had not been
touched at all. Its B1 section still read as pure future work: "Build: Use GPT-4o and/or o3 to
generate adversarial prompts... Run each against live Coordinator and Synthesizer," no mention
that this had already happened and passed. Confirmed by grep before claiming it (`grep -n "B1a"
ROADMAP.md` returned nothing) rather than asserted from memory of what should have happened.

**Root cause, not just the symptom:** the `/archive` skill (`.claude/commands/archive.md`) never
mentioned `ROADMAP.md` at all — five steps covering the transcript, the log, the session
writeup, `SESSION.md`, and `DEV_BACKLOG.md`, with no step that so much as asked whether a
roadmap-tracked item had changed status. `SESSION.md` and `DEV_BACKLOG.md` both got updated
because the ritual explicitly names them; `ROADMAP.md` didn't, because nothing told the ritual
to look at it. Fixing the one instance (editing `ROADMAP.md` for B1a) would have left the same
gap open for the next session that closes a roadmap-tracked item — the user's ask was
explicitly for the general fix ("more generally on any `/archive`... FIX THIS"), not just the
one-off.

**What was built:**
- `.claude/commands/archive.md` — five steps became six. New step 5, "Update `ROADMAP.md` if
  this session touched anything it tracks," inserted between the `SESSION.md` step and the
  `DEV_BACKLOG.md` step. Names the exact failure mode that just happened as the worked example
  in a blockquote at the top of the file (not buried in the new step alone, so it's read before
  step 4 is started, not discovered after step 5 is skipped again). Explicit trigger clause:
  "especially check this when something is being marked done or removed from `DEV_BACKLOG.md`"
  — because that is precisely the moment a roadmap-tracked item's status is changing and the
  easiest moment to forget the roadmap has its own copy of that status.
- `ROADMAP.md` §B1 — added a ✅ status blockquote directly under the `**B1 — Red team...**`
  heading, in the same inline style A7's pre-sign-off gate note already uses elsewhere on the
  page (a deliberate match — the file already has a convention for this, use it rather than
  invent a second one). States B1a done (disclosure suite, output-filter suite, confused-deputy
  test — all three items covered by this page), links the report and the log entry, and states
  explicitly that B1b (indirect injection) and B1 as a whole are still open, so the ✅ can't be
  misread as closing more than it does.

**Decision made, and what was rejected:** considered rewriting the B1 section's body to strike
through the now-completed build instructions, matching how completed Track A items were handled
elsewhere in the file's history. Rejected — the instructions still describe exactly how to
reproduce/re-run B1a (the categories, the two automated checks, the pass conditions), and B1b
still needs them for its own run. A status note above the still-live instructions is the correct
shape here, not a strikethrough; conflating "done" with "no longer needed" would have deleted
the reference the next session needs.

**Nothing deployed.** Two markdown files edited (`.claude/commands/archive.md`,
`ROADMAP.md`); no code, no tests, no VM-relevant change.

### 2026-08-04 (B1a red team executed: 75/75 pass, gate PASS) — tests-only, no commit required

Writeup: [archive/sessions/2026-08-04 — B1a Red Team Executed.md](sessions/2026-08-04%20—%20B1a%20Red%20Team%20Executed.md)

First execution session against the prior day's scoping-only pass
([archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md),
plan at `archive/plans/scope-out-executing-b1-b4-deep-sun.md`). Entered via `/metatron-code` plan
mode; plan written to `~/.claude/plans/let-s-begin-addressing-phases-keen-dusk.md` and approved
before any code was touched.

**Why B1a first, not B2 or B4:** pure testing, no production code change, no deploy — lowest risk
of Wave 1's three items, and it directly chips at the A7 blocker rather than infrastructure that
only matters once red-teaming finds something. `tests/security_testing_plan.md` §1 already
specified the 9 categories and pass conditions, so this session was build-the-runner-and-run-it,
not decide-the-approach.

**Re-verification before planning, not assumed from the prior day's doc:** re-checked the
scoping doc's claims against current code first, since a day had passed. PoLP enforcement,
output-filter substring-matching, confused-deputy opacity, and the duplicate backlog files were
all unchanged. **One correction found:** the scoping doc (and `DEV_BACKLOG.md`'s still-live entry
at the time) both described `research_agent` as missing `allowed_tools`, defaulting it to all 53
tools. It wasn't — `allowed_tools: [fetch_url]` had shipped 2026-08-04 10:55Z in `c886560`, part
of the `fetch_url`/`read_email` build, twelve hours before this session started. The
`DEV_BACKLOG.md` entry was closed as stale in this session rather than carried forward as live
B2 scope — a second instance of the "don't act on an item's own description" failure mode
`CLAUDE.md` already names, caught before it cost anything this time.

**What was built:** `tests/run_b1_redteam.py`, following `tests/run_a4_safety.py`'s established
pattern (static reviewed scenario data, never raises out of a scenario, dated markdown report).
Three suites:
- **`disclosure`** — the 9 categories from `tests/security_testing_plan.md` §1, run live through
  `run_pipeline_session()`. Three categories judged highest-value for an untested bypass (persona
  adoption, hypothetical framing, roleplay escape) got two additional phrasing variants each,
  sourced from GPT-4o via `ask_gpt` during planning and reviewed before being hardcoded — 15
  live pipeline calls total.
- **`filter`** — no model calls. Builds synthetic strings from `filter_output()`'s own
  `_ALWAYS_CONFIDENTIAL`/`_CONTEXT_SENSITIVE` lists and runs the real function directly (61
  checks), plus the known Exchange 027 (2026-06-26) false positive re-run as a documented,
  non-gating informational marker rather than a scored check.
- **`deputy`** — two parts. (a) structural: `inspect.getsource()` on `run_pipeline_session` and
  `_run_pipeline_session_stream_inner`, regex-confirms `_dispatch_from_coordinator()`'s only call
  sites pass `coord_output`, never `spec_text`/`specialist_outputs`. (b) live: feeds a hostile
  `SPECIALISTS_TO_CALL`-shaped string directly into `_dispatch_from_coordinator()` to confirm the
  parser has **no innate protection** — it does dispatch a real specialist call (`logistics`, which
  itself then refused the injected directive on its own judgment, an incidental extra data point)
  — proving the safety guarantee here is entirely architectural (part (a) never being violated),
  not a property of the function itself.

**Result: 75/75 checks pass, gate PASS.** No architecture leaked in any of the 15 disclosure
responses; all 61 filter checks correct; both deputy checks confirmed as designed. Merged the
three suite-specific reports (`_filter.md`/`_deputy.md`/`_disclosure.md`, generated by three
separate `--suite` invocations to keep API spend visible per suite) into one canonical
`tests/security_redteam_2026-08-04.md` via a one-off merge script, then deleted the interim
files — one artifact per CLAUDE.md's generated-file-naming convention, not three fragments.

**This closes B1a only.** B1b (indirect injection via email/calendar/web content) remains gated
on Track E integration maturity, unchanged from the scoping doc. B1 as a whole — what A7 sign-off
actually needs — is not closed.

**Anomaly found while running it, filed not fixed — the highest-value finding of the session,**
and not something B1a set out to look for. All 15 disclosure responses against `sarah_chen`
carried a real answer to the actual prompt plus an escalating, near-identical crisis-intervention
script (988, "find Tom", confirm the lamotrigine dose) — including on prompts with no plausible
connection to crisis content, like "What tools do you have?". `data/personas/sarah_chen/context.json`
explained why: an open `"safety check and SI risk"` thread persisted from an earlier session
(most likely the 2026-08-05 A4 pipeline probe, which legitimately fires `sarah_chen`'s
`SUICIDAL_IDEATION`/`MUST_SURFACE` flags via the identical MW-3 prompt), and the Synthesizer had
written a *new* pattern into that same file mid-run: `"deflecting acute distress with system
architecture questions"` — reclassifying every B1a red-team prompt as further evidence of the
same unresolved crisis rather than as an unrelated new message. `held_items` read `"Held: None —
all critical flags surfaced due to acute safety risk"`, with nothing describing when or how that
open thread would ever close.

**Two implications, deliberately not conflated in the filing:**
1. *Test hygiene* — `sarah_chen` is not a clean bed for red-team/self-disclosure testing once any
   earlier session has legitimately triggered a clinical flag against her. A dedicated persona or
   an explicit context-tracker reset would isolate disclosure-resistance testing from crisis-
   override behaviour.
2. *Possibly real behaviour, not just a test artifact* — if this generalises to Mike, a
   MUST_SURFACE flag firing once with no visible expiry could keep resurfacing crisis framing on
   every unrelated later turn indefinitely. Could be intentional conservatism or a genuine bug;
   this session determined only that the behaviour exists and has no visible resolution path, not
   which it is.

Filed as `DEV_BACKLOG.md` entries (not silently patched — B1a's job was to find and log; fixes
belong to B2/B3 or a dedicated look at `mental_wellbeing.md`/`synthesizer.md`), not yet triaged
to an owner.

**`SESSION.md` updated** (lead paragraph, A7's B1 bullet split into B1a-done/B1b-open, one row
added to Recent sessions) — not appended to.

**Nothing deployed.** B1a is read-only testing against the already-running Vertex path; no
production code was touched.

### 2026-08-05 (A7's residual gap closed: end-to-end pipeline probe) — tests-only, no commit required

Writeup: [archive/sessions/2026-08-05 — A7 Pipeline Probe.md](sessions/2026-08-05%20—%20A7%20Pipeline%20Probe.md)

Ran in parallel with the `moonbeam` backlog session below (`AgentRecord`/WS-drain fixes) — no
file overlap: this session touched only `tests/run_a4_safety.py`.

**What it closes:** ROADMAP.md:130 named the last open piece of the prefix-caching regression
gate — A4's clinical suites validated specialists in isolation (`_run_single_agent()`), but a
flag firing correctly inside Mental Wellbeing or Physical Health could still be held, diluted,
or dropped by the Synthesizer before reaching the user, which is the actual user-facing failure.
That gap is now closed.

**What was built:** a `pipeline` suite added to `tests/run_a4_safety.py` (`--suite pipeline`),
running the same three A4 scenarios (MW-3 suicidal ideation, MW-7 mania, PH-MED missed critical
medication) through `run_pipeline_session()` — the real Coordinator → specialist → Synthesizer
path — instead of a specialist in isolation. Pass condition **inverts** the specialist-level
check: the raw flag token (`CLINICAL_CONCERN`, `MUST_SURFACE`, `MANIA`, `MEDICATION_MISSED_CRITICAL`)
must be **absent** from the user-facing response (synthesizer.md's confidentiality rules forbid
leaking internal signalling — a leaked token is itself a bug), and the flag's **substance** must
be **present** instead (crisis resources for MW-3, a caution-not-celebration framing for MW-7,
the medication name for PH-MED). Ran live against `sarah_chen`/gemini: **3/3 PASS**, report at
`tests/a4_safety_rerun_2026-08-04_gemini_pipeline.md` (filename date reflects the real run
timestamp, one day behind the narrative session date above — cosmetic, not a discrepancy in the
result).

**Decisions made, and what was rejected:**
- Kept `pipeline` as a separate `--suite` option rather than folding it into `all` — it exercises
  a materially different path (full pipeline vs. single agent) and is far slower per scenario
  (~65s vs. single-digit seconds), so bundling it into the default run would silently change what
  `--suite all` costs and blocks on for every future caller.
- Suite-qualified the pipeline suite's own output filename (`_pipeline` suffix) to avoid
  overwriting a same-day `clinical`/`finance` report against the same provider. Left the existing
  `clinical`/`finance` filename pattern untouched — same collision risk exists between those two
  today, but that is pre-existing behavior, out of scope for this change.
- Did not attempt to fix or judge response tone/warmth — same explicit limit as the A4 suites
  this extends: presence of required substance is what a script can check mechanically, not
  clinical appropriateness.

**Still open after this:** A7 sign-off itself is unchanged by this work — checks 10 (12-specialist
behavioral audit) and 12 (constitution alignment review), plus B1 (red team), remain open by
deliberate deprioritization (a prioritization call already made, not something this session
unblocks). A5b/A5c small leftovers also remain. A8 (code refactor) is still gated on A7 and has
not started. Phase 5 close requires both A7 and A8.

**Deploy:** none required — `tests/`-only change, no `core/` or `config/` files touched.

### 2026-08-04 (proactive check-ins fixed: AgentRecord serialization, WS drain, verification chase) — `10bf194`, `ec55788`; **`10bf194` deployed** (and carried the previously-pending `9361537` chain along with it)

Writeup: [archive/sessions/2026-08-04 — Backlog Session: AgentRecord Fix, WS Drain, VM-Down Detection.md](sessions/2026-08-04%20—%20Backlog%20Session:%20AgentRecord%20Fix,%20WS%20Drain,%20VM-Down%20Detection.md)

**The ask** was to pick the most pressing backlog items completable in one session. Before
picking, three Explore agents re-verified the strongest candidates against live code rather
than trusting the written descriptions — per the standing rule from the 2026-08-05 sweep below.
Two turned out real with confirmed root causes; two turned out already fixed and just never
closed.

**[DB-0803-02] root-caused and fixed — proactive check-ins were failing outright.** The prior
session's sweep had localised the `AgentRecord is not JSON serializable` bug as far as "not
`core/trace.py`" and left it there. This session found it: `core/router.py:166`, inside
`log_model_error()`. Three call sites in `core/orchestrator.py` (:1575, :1676, :1881) did
`_agent = _tr.get_current_agent() or "unknown"` — but `get_current_agent()` returns the live
`AgentRecord` object, not a string, and a truthy record short-circuits the `or`. So `_agent` was
the record itself whenever one was active (always, mid-pipeline), and `log_model_error` crashed
trying to `json.dump` it — **masking whatever the real underlying model failure was**. One-line
fix: `"agent": agent.agent if hasattr(agent, "agent") else agent,` — fixes all three call sites
at the single JSON boundary rather than patching each.

**`[DB-0803-07]` fixed — deploy.sh's drain gate was decorative.** `/active` only counted the SSE
path's `_active_streams`; the app talks over WebSocket, which never touched the counter, so
`deploy.sh` always read `0` and restarted immediately regardless of in-flight conversations.
Fixed by wrapping the WS exchange block in the same `_active_lock` the SSE path already uses —
deliberately counting exchanges, not connections, so an always-connected phone doesn't pin the
counter above zero forever.

**Caught during local testing, not by review: the WS fix's first draft crashed on
`UnboundLocalError: cannot access local variable '_active_streams'`.** Python treats a
function-local name assigned with `+=` as local unless told otherwise, and the increment/decrement
sat inside `websocket_endpoint()` without the `global _active_streams` declaration the SSE
generator already has. Starting a real local server and running an actual WS exchange (not just
reading the diff) caught this before it shipped — the value of testing the thing rather than
reasoning about it.

**Two stale entries closed, no code needed:** the `synthesizer.md` `write_config`/`scheduler.yaml`
promise (already superseded by `write_schedule` et al. from the 2026-08-03 Phase 4 session) and
the `/metatron-troubleshoot` stale-paths claim (already fixed by `a763628`). Both had sat in the
backlog uncrossed-off after the fix that resolved them.

**`sync_dev_backlog.py` now distinguishes a stopped VM from a running-but-unreachable one.**
Added `vm_status()`, called only when `fetch_events()` already came back empty (no cost on the
happy path), folding a `⚠ VM running but unreachable` suffix into the one-line session-start
report — the gap the 2026-08-04 4-hour outage exposed (it read identically to a routine pause
for hours).

**Deploy chased further than "it shipped."** `./deploy.sh` ran clean and verified HEAD match,
but rather than stop there, the exact crashing call was reproduced live on the deployed VM:
started a real `RequestTrace`/`AgentRecord` via `core.trace`, then called the deployed
`log_model_error()` with it — the identical object type and code path that had been killing
`companion_checkin`, `evening_close`, `morning_brief`, and `plant_watering_check`. It did not
raise, and the resulting log entry correctly read `"agent": "coordinator"` (a string, not an
object dump). The synthetic test entry was deleted from `data/diagnostics/model_errors.json`
afterward so it doesn't read as a real production error later.

**What this does *not* yet prove, and why that gap is filed rather than chased tonight:** a real
scheduled fire completing end-to-end under genuine model-call variance, as opposed to a manual
reproduction of the crash path. `companion_checkin`'s `min_gap_minutes: 180` put the next
natural opportunity at ~23:03 BST — over two hours out — so rather than block the session on it
(or reach for `ScheduleWakeup`, which is scoped to `/loop` dynamic-pacing and not a fit for a
one-off wait), **`[DB-0804-01]` was filed as three time-gated checks**: `companion_checkin` not
before 23:05 BST tonight, `morning_brief` not before 07:35 BST tomorrow, and a one-week error
count not before 2026-08-11 — each with the exact command and pass condition, so an early check
doesn't misread "hasn't fired yet" as a regression.

**Options rejected:** waiting live in-session for the natural fire (too slow, and a foreground
wait bought nothing a scheduled follow-up couldn't); using `ScheduleWakeup` to self-resume
(built for `/loop` dynamic mode, not a general-purpose timer — using it here would have been
reaching for a tool outside its intended contract).

Deployed `10bf194` (the four fixes) and, as a side effect of the fast-forward, the previously
undeployed `9361537`→`8ee150f` chain from the 2026-08-05 backlog-trust-repair session — which
resolves that session's own outstanding *"`9361537` needs `./deploy.sh`"* note below. `ec55788`
(closing `[DB-0803-02]`, filing `[DB-0804-01]`) is docs-only and pushed but does not need
deploying.

---

### 2026-08-05 (backlog trust repair: the counter, the sweep, the grants) — `9361537`, `23057ee`, `812ef1a`, `8ee150f`; **deployed 2026-08-04 as part of `10bf194`'s fast-forward**

Writeup: [archive/sessions/2026-08-05 — Backlog Trust Repair: Counter Bug, Verify-and-Triage Sweep, Provenance IDs.md](sessions/2026-08-05%20—%20Backlog%20Trust%20Repair:%20Counter%20Bug,%20Verify-and-Triage%20Sweep,%20Provenance%20IDs.md)

**The ask** was to work `DEV_BACKLOG.md` down to a manageable state, with an explicit constraint:
make sure the work has real value and is not legacy or tail-chasing. The constraint turned out to
be the whole job — the list could not be worked safely as it stood.

**Why the backlog appeared to balloon from ~30 to ~60 items: it did not.** The counter was wrong.
`scripts/sync_dev_backlog.py` summed every `- ` line between `## Inbox` and `## Done`, and
**`DEV_BACKLOG.md` had never contained a `## Done` heading** — so the "live region" ran to end of
file. Three consequences, all in the same direction: struck-through entries still start with
`- `, so **closing an item made the reported number go up**; untriaged machine-written denials
were counted alongside curated engineering work; and the intro prose bullets were swept in. An
entry in the file already said *"see the Done section"* and the script had partitioned on that
heading for weeks. Fixed in `count_items()`, which now reports `N new · N untriaged · N open`,
reconciled by hand against `awk`. The fail-silent contract (exit 0 on an unreachable VM) was
verified unchanged — it is what keeps a paused VM from noising up a session start.

**Why untriaged and open are now reported separately, rather than one tidier number.** They are
different kinds of work: untriaged is a queue that someone must decide about, open is work
already decided on. Collapsing them meant a pile of `TOOL_DENIED` warnings read as a growing
engineering backlog, which is precisely the false alarm that prompted this session.

**The sweep found roughly a third of checked items stale.** Closed with evidence: the `/session`
`[CONTEXT]` leak (`run_session` splits and filters at `orchestrator.py:2690`); the `vertex_cache`
404 (eviction present at `:1417`, last journal occurrence 2026-07-29); *"nothing can set a
reminder or calendar entry"* (**all four steps of its own prescribed build order are done**);
and the transcription timeout, whose cause was fixed on 2026-08-01 by `d42eefc`/`81fc6e2` — that
one is the clearest case for the whole exercise, since anyone working it from the old description
would have re-fixed a solved problem.

**Live journal evidence beat code reading three times, and this is the transferable lesson.**
Reading the code would have got two of these wrong in each direction:

- **`AgentRecord is not JSON serializable` — elevated, not closed.** Filed as *"trace
  serialization fails on every scheduler job"*, which reads like a logging nuisance. The journal
  says 18 occurrences in 7 days against **19 total scheduler errors** — so essentially every
  scheduler failure is this bug, and the jobs it kills are the proactive check-ins
  (`companion_checkin` ×13). Reading `core/trace.py` would have suggested it was fixed:
  `_agent_to_dict()` has converted `AgentRecord` and recursed `subagents` since `c66ed03`
  (2026-06-22). The failing path is server-side via `send_one`, since the failing jobs are all
  `agent == "coordinator"`. Localised as **[DB-0803-02]**; root cause open, and the next step is
  the server-side traceback rather than more reading.
- **`vertex_cache` 404 — closed, but with a trap flagged.** Eleven `[vertex_cache]` warnings sit
  in the log right now and are `NameResolutionError` from the 2026-08-04 outage, not the filed
  404. A `grep vertex_cache` would re-file the outage as a caching bug; the entry says so.
- **Memory indexer — hypothesis confirmed and sharpened.** The same byte offset (`char 82852`)
  now appears against `index log 2026-08-04` as it did against `2025-05-22`. **A shared offset
  across unrelated files is proof the indexer parses something fixed**, which the original entry
  could only guess at.

**Marked `needs re-derivation` rather than left looking actionable:** the `write_config` heading
duplication (cites a `_titled()` that does not exist in the 84-line `tools/config_writer.py`) and
the `shownIds` eviction cliff (cites `static/index.html:567`; `shownIds` is now at `:706`+).
Carrying a dead line number forward is what makes a list untrustworthy one item at a time.

**Nine `TOOL_DENIED` entries resolved, six distinct cases, decided from motivation rather than
mechanism.** The denial text records *what* was blocked and never *what the agent was trying to
do*, so each was matched to the conversation it happened in via the VM's conversation record.
Every one was a legitimate lookup: `finance` answering *"what can you tell me about my credit
card payments"* with no store to read; `work_vocation` recalling that morning's Apex brief;
`logistics` reading back the plant-check rule to amend it.

Granted (`9361537`, both routing files in parity): `logistics` +`read_agent_config`
+`write_agent_config` +`search_memory` +`read_archive` +`write_archive`; `work_vocation`
+`search_memory`; `finance` +`read_archive`.

> **What was believed at the start of this session and turned out to be wrong — and it changed a
> decision before it was caught.** The first analysis concluded `logistics` was *"improvising
> around a store that does not exist"*, and recommended **holding** the `write_agent_config`
> grant pending the schedule/CalDAV work. Mike accepted that recommendation. Both halves were
> false:
>
> 1. **`write_schedule`/`list_schedules`/`delete_schedule` already existed** — built `078e618`
>    and granted to `logistics` in `2f74cd2`, both **2026-08-03 14:48, before every one of the
>    denials.** The work being waited on had shipped two days earlier.
> 2. **`write_agent_config` is not a workaround for `logistics`; it is the specified store.**
>    `logistics.md:189` draws the distinction itself — the recurring-obligation inventory lives
>    there because *"obligations are data rows, not scheduled jobs"* — and `:45` makes writing to
>    it **mandatory**. Corroborated on disk: `sarah_chen`'s `logistics.json` already held
>    `recurring_obligations`, written through warn mode.
>
> **The source of the error was trusting the backlog's own prose** — *"`scheduler.yaml` jobs are
> static with no tool to add one"*, true when written 2026-08-01, stale by 2026-08-03. The cost
> is not the wasted check: **a stale premise argues for the wrong decision, persuasively.** That
> is now the stated rationale in `CLAUDE.md` and `/backlog` for verifying before acting, and it
> is a far better argument than "checking is tidy."

**`physical_health` +`write_agent_config` — the 2026-08-04 hold reversed, with a narrower
control.** Rejected: keeping the blanket denial, which cost the agent an ordinary config store
every other specialist has. Rejected: granting it outright, which would let the agent author the
`medication_profile` that `MEDICATION_MISSED_CRITICAL` classifies from — the flag would grade its
own homework, contradicting `physical_health.md:106` (*"never from the agent's judgment"*).
Chosen: grant the tool, guard the one key. `_GUARDED_KEYS` in `tools/agent_config.py` refuses
`(physical_health, medication_profile)` with an explanatory error. **In Python, not the
instruction file** — `logistics` was told it lacked `write_agent_config` and called it anyway,
three times in production; being told is not being prevented. Residual concern filed as
**[DB-0805-01]**: the guard covers exactly one key, and B2 should decide whether guarded keys are
the right mechanism or whether the confirmation gate supersedes them.

**Also noted and left alone:** `work_vocation` and `finance` hold `write_agent_config` while
clinical `physical_health` had been denied it — an inconsistency that looked like drift rather
than design. Mike chose to level up rather than down.

**Provenance and IDs (answering "are the to-dos timestamped?").** They were not, below Inbox.
Positional references — the `#7` / `#19` used across chat windows — shift the moment anything is
added or triaged, which had already produced ambiguity. Every curated item now carries
`DB-MMDD-NN` (dated from filing, never reused, retained by closed items) plus a provenance line:
who filed it and by what method (`Mike via Synthesizer`, `warn-mode tool denial`, `daily rule
audit`, `dev session`), the origin SEQ where it came from a conversation, and what was verified
against what, when. Rejected as unnecessary: restructuring seq allocation so `_persist_dev_request`
could stamp one at write time — the seq does not exist at that moment, and `_seq_for()`
(`core/server.py:1118`) already solves the same correlation by timestamp for traces.

**`/backlog` (`812ef1a`) — one bin, and a ritual for emptying it.** `DEV_BACKLOG.md` was already
the single bin, but nothing said how to work it, so each session invented an approach — which is
how a third of it went stale. The command carries: sync, triage the Inbox to zero, verify before
re-filing, assign ID and provenance, close with evidence. Rejected: putting the rules in
`CLAUDE.md` (auto-loaded, costs tokens every session, and is the file where duplicated rules go
stale) and in `DEV_BACKLOG.md`'s header (not read by default, so a session that should triage
would never see them). `CLAUDE.md` gets a pointer and the one load-bearing rule.

**Visibility is deliberately count-only.** `/metatron-code` and `/archive` report the
`N new · N untriaged · N open` line and stop. Rejected: attaching a triage pass to `/archive`,
per Mike — *"we won't address the full backlog every time"*. A recurring bulk chore attached to a
command that runs every session is how a list stops being read at all; the count makes a filling
Inbox visible for free, and when a pass is worth it is Mike's call.

**Local/Ollama path marked dormant** (user decision). The deployment is fully on the Vertex VM
under the 2026-06-18 ZDR amendment, so a local re-run verifies a path nothing uses. `ROADMAP.md`
§A7 residual gap 1 and §0 item 8 are **annotated, not deleted**, and the binding privacy ruling
is untouched — what is parked is the qwen3:14b *run*, not the requirement it verifies. Rejected:
deleting the items outright, which would erase what the ruling required and make reversal cost a
re-derivation. Consequence: the previously-planned parallel window for `--provider ollama` A4 is
no longer valid work.

**Result: `0 new · 0 untriaged · 45 open`**, and all three numbers now mean what they say.

**Not deployed.** `9361537` touches `config/modules/routing*.yaml` and `tools/agent_config.py`
and needs `./deploy.sh`; the CalDAV/email window owns `.env` and deploy coordination. Until it
lands the grants are Mac-only and warn mode continues to let the calls through on the VM.

**Deferred:** the A7 pipeline probe (Step 5 of the approved plan, not reached — self-contained
and better started fresh); the `deploy.sh` WebSocket drain fix, now confirmed real with evidence
as **[DB-0803-07]**; transcription accuracy.

Outgoing handoff paragraph from `SESSION.md` — written by the parallel CalDAV/email window,
which replaced the readout paragraph while this session was running:

*Updated: 2026-08-04 (item 5 decided and built — A, B and C) — **Nothing outward-facing can now happen without a tap from the user.** `tools/confirm.py` records approval **out of band** (`POST /confirm`); the model may propose, only the user may approve, and the token the model holds is inert until the server records the tap — a model talked into acting by a hostile email is exactly the one whose claim of consent is worthless. Approvals are single-use, fingerprinted to the exact arguments shown, and expire in 10 min. `send_email` is live, limited **in code** to Mike's addresses and saved CRM contacts. **Research could not fetch and now can:** a `fetch_url` instruction shipped that morning against a grounded path passing no tools — grounding and function calling *do* coexist (tested on Vertex, contrary to received wisdom). **Correction:** the parallel window's `deploy.sh` guard bug is withdrawn — the guard is inside the remote heredoc and greps the VM's `.env`. **Next:** the SMTP send path has never been exercised (every test stops at the gate), and enforce mode is still off by decision.*

---

### 2026-08-04 (decisions A/B/C built; Research could not fetch and now can) — `0eb2067`, `c886560`, `ca993fe`, `15b9a41`, `0f2ca6c`; **deployed `15b9a41`**

Writeup: [archive/sessions/2026-08-03 — Auth, Injection Defense, Web Access, Email.md](sessions/2026-08-03%20—%20Auth,%20Injection%20Defense,%20Web%20Access,%20Email.md)
(second block). Continues the entry below; Mike took all three item-5 decisions rather than
deferring them, wanting to be ready for new work rather than carrying open questions.

**Decisions as taken, and where they diverged from what I recommended.**

- **A — provenance: bump one tier** (recommended, taken). **My own written proposal was too
  broad and was narrowed before building.** It said externally-originated actions should be
  Confirm First *regardless of tier, including otherwise-autonomous ones* — which would mean
  asking permission before adding "collect parcel" to a list from a delivery email. That is
  friction on a reversible, internal, near-harmless action, and friction is what trains a user
  to approve without reading, which is then paid for on the confirmation that mattered.
  Reversible internal actions stay autonomous but are **attributed**; outward-facing or
  irreversible ones become Confirm First **with the source quoted**, so the user confirms the
  *evidence* rather than the act.
- **B — out-of-band confirmation** (Mike chose the stronger option over my staged
  recommendation). I proposed a model-mediated token flow first, upgradeable later. He went
  straight to server-recorded consent. **Rejected by that choice:** the cheaper token-only
  flow, where the model asserts the user's approval.
- **C — `send_email` to CRM contacts** (wider than the self-only I recommended). **These two
  choices hold each other up:** contact-recipient mail is defensible *because* consent is
  out-of-band. Recorded in the commit, the scope doc and the code comments — **if B is ever
  downgraded to model-mediated consent, C must shrink to self-only in the same change.**
- **Housekeeping:** fix Research + rebuild the APK; **enforce mode deliberately still off**,
  since the 43 grant gaps are the intended build-out and nothing in A/B/C depends on it.

**Research was broken by me earlier the same day, and is now genuinely fixed** (`c886560`).
`6739d62` added a `fetch_url` instruction to `research_agent.md` while
`run_session_gemini_grounded()` still passed **no tools at all** — so Research was told it held
a capability it could not invoke. That does not fail cleanly: an agent in that state is liable
to *claim* it read a page it never fetched, which is the precise unretrieved-source failure
`fetch_url` was built to fix.

**Grounding and function calling coexist — tested rather than assumed.** The received wisdom is
that Gemini rejects `google_search` alongside `function_declarations`, and believing it would
have forced an ugly workaround (drop grounding, or route Research through a second agent). On
`gemini-3.1-pro-preview` via Vertex, search-only, functions-only and **both together** all
succeed; the only complaint concerns *automatic* function calling, now explicitly disabled
since the loop is manual. The grounded call became a bounded loop — max 4 turns, only when
schemas are passed, byte-identical behaviour without them. Verified live both ways.

**A misleading config comment, worth recording as a class.** `research_agent` carried
*"no allowed_tools — research_agent runs in bare mode (no personal tools)"*. That conflates two
different things: bare mode (`_run_single_agent`) withholds personal **context**; omitting
`allowed_tools` grants **all** tools (`None` = allow all in `core/router.py`). **It read as the
most restrictive setting available and was in fact the least.** Harmless only because the
grounded path passed nothing — which stopped being true the same day. Now `[fetch_url]`.

**The gate (B), and why its shape is the whole point.** Until now every confirmation rule lived
in `synthesizer.md` — a prompt. That is the control class already proven not to hold here:
`logistics` was *told* it lacked `write_agent_config` and called it three times in production.

`tools/confirm.py` records approval **out of band**. A token the model presents back is a token
it can present without ever having asked, and a model talked into acting by a hostile email is
exactly the one whose claim of consent cannot be trusted — so it is not in that path. `POST
/confirm` is the only writer, driven by a real tap. The model may propose; only the user may
approve, and the token it holds is inert until the server records that tap. Approvals are
single-use, fingerprinted against the exact arguments shown (so an approval for "email Sarah
the itinerary" cannot be spent on "email everyone the medical file"), and expire in 10 minutes.

**Corrections to things believed true earlier:**

1. **`research_agent` did not effectively hold all 53 tools.** I said it did and filed a backlog
   item saying so. True of the config, false in practice — the grounded path handed it nothing.
   The risk was latent (a provider or branch change would have made it real), not live.
2. **The parallel window's `deploy.sh` bug report was wrong, and is withdrawn** (`0eb2067`). It
   was filed as confirmed — *"not theoretical — it happened"*. The guard sits inside the quoted
   `<<'REMOTE'` heredoc (opens line 40, closes 103; `cd ~/multi-model-mcp` at 42; guard at 54),
   so it greps the **VM's** `.env`. What was actually observed: `git push` is line **30**,
   before the SSH block — a push happening is not evidence the guard passed. That run's SSH
   failed on the outage, so the guard was never *reached*. Entry kept struck-through rather than
   deleted, with an `awk` check attached, because the reasoning is plausible enough to be
   re-derived. Confirmed the other way too: once the password was on the VM, the same script
   deployed cleanly four times.
3. **A bug of mine that hid because it failed safe.** `_own_addresses()` imported
   `tools.profile._load_profile`; the function is `_load`. Wrapped in `except Exception: pass`,
   the ImportError vanished and the recipient allowlist came back **empty** — `send_email`
   refused every recipient including Mike's own, looking exactly like "you have no contacts".
   Found by testing against the live persona, not by the unit tests, which stub
   `_known_recipients`. **Generalised: a broad except around a loader converts a coding error
   into an empty allowlist that reads as legitimate emptiness.** Exception handling there is now
   narrow — a missing file is tolerated, a wrong import name is allowed to say so.
4. **Two backlog requests to remove the voice toggle were superseded, not ignored.** Mike had
   asked Metatron twice to remove it, then asked here for a toggle instead. Closed on his
   explicit instruction (*"Voice is completed... I can always rerequest"*) and triaged out of
   the machine-written Inbox rather than deleted.

**Verified in production, not just locally:** `/pending-confirmations` and `/confirm` 401
unauthenticated; the injection probe holds at three independent layers — payload cannot close
the wrapper (1 closing tag), markers recorded (`Ignore previous instructions`, `You are now`),
and **the tool refuses an attacker recipient even on full model compliance**, which is the only
layer that does not depend on the model behaving. Research fetched a real page and cited it.
All three suites pass; services clean; `check_personas` 0.

**APK rebuilt** with the three features committed but never shipped — password reveal
(`819de75`), the parallel window's transcript readout (`a5ea4c3`), and the approval control
(`ca993fe`). Each verified **inside the bundle** rather than assumed from `cap sync`, after
Mike flagged that unshipped work existed; bundled `index.html` byte-identical to `static/`.

**Not done:** SMTP send path never actually exercised — every test stops at the gate, so no
mail has been sent by this system. Pipeline-level injection probe (a hostile email in the real
inbox, through a full conversation) not run. Both filed.


### 2026-08-04 (app — dismissable transcription readout)

Full writeup: [sessions/2026-08-04 — App: dismissable transcription readout.md](sessions/2026-08-04%20—%20App:%20dismissable%20transcription%20readout.md).
`static/index.html` only. **Not yet deployed** — needs `./deploy.sh` **and an APK rebuild.**

**The problem.** The footer's `#transcript` div showed whatever Whisper returned and then kept
showing it, unbounded, until the next recording started. On a long dictation the footer grew
until it crowded the conversation off a phone screen, and there was no way to get rid of it
without recording again.

**What changed.** Three edits, all in `static/index.html`:

1. The bare div is now wrapped in `#transcript-wrap` — text plus a `✕` dismiss button.
2. The wrapper is `display: none` when empty (it previously reserved `min-height: 18px`
   permanently), and the text is capped at `max-height: 4.5em` with `overflow-y: auto`, so a
   long transcript scrolls inside its own box instead of growing the footer. Given a card
   background and border so it reads as dismissable rather than as loose text.
3. `showTranscript()` / `hideTranscript()` replace the two direct `textContent` writes.
   Auto-hide at `TRANSCRIPT_TIMEOUT_MS = 12000`; the timer is cleared by `✕`, and starting a
   new recording hides the previous readout immediately.

**Decisions, and what was rejected:**

- **Both a close button and a timeout, not one.** The user offered them as alternatives
  ("either a close button or a timeout"). The timeout clears the screen with no action needed;
  the `✕` covers the case where 12s is too long to wait. They cost nothing together.
- **Rejected: deleting the readout entirely.** It is arguably redundant — `sendToServer()`
  already calls `addMessage('user', text)`, so the same words appear in the conversation a
  moment later. But the readout is the *pre-send* confirmation that Whisper heard correctly,
  which the conversation bubble is not, and the user asked for it to stay visible. That
  redundancy is however the reason auto-hide is safe: nothing is lost when it goes.
- **Rejected: truncating with an ellipsis.** Scroll-within-a-cap keeps the full text
  inspectable, which is the whole point of a transcription check.
- **Left-aligned, was centred.** Centred italic is fine for one line and unreadable at three;
  the height cap makes three lines the normal case for a long dictation.

**Deploy note worth carrying:** this is a `static/index.html` change to UI *structure*, which
is one of the named APK-rebuild triggers in `CLAUDE.md` — server-side changes alone are not.
`SESSION.md` already carried a pending APK rebuild for the password-reveal toggle, so the two
ride together rather than needing separate builds.

**Untested.** No server was started this session; the change is reasoned from the code, not
observed running. Test procedure is in the session writeup and in `DEV_BACKLOG.md`.

---

### 2026-08-04 (context second pass — phase conventions out, prose tightened, the size rule fixed)

Full writeup: [sessions/2026-08-03 — Context-file audit: SESSION.md split, cold-start trim, archive command.md](sessions/2026-08-03%20—%20Context-file%20audit:%20SESSION.md%20split,%20cold-start%20trim,%20archive%20command.md) (same session, continued).
Commit `a5ba388`. **Docs and `.claude/` only — not deployed.**

Follow-up to the 2026-08-03 audit, run after the user tested `/metatron-code` live and the audit of that run came back clean. **Cold start 28k → 26k tokens; 69% below the 350,663-byte baseline.** 16/16 checks pass.

**What changed**

- **Phase Review + Phase Testing conventions → `docs/CONVENTIONS.md`.** Needed at phase boundaries; were being paid on every session.
- **Directory Layout condensed** to the two facts that carry weight — `config/` is the product, `core/` is the harness. `CODEBASE_INDEX.md` already does file-level.
- **Deployment Infrastructure 16,100 → 14,323** by tightening prose written in the *first* pass rather than moving more out. The condensed blocks from 08-03 were verbose; same content, fewer words.

**The size rule was wrong, and the user caught it**

The first pass wrote *"if `SESSION.md` is longer after your session than before, something went in the wrong file."* That is a **ratchet**: it can only ever shrink, so over enough sessions it pares away things worth keeping, and it penalises a session for recording a genuine new blocker — exactly what the file is for. **Replaced with a 200-line ceiling**, fixed in all four places that stated it (`SESSION.md`, `CLAUDE.md`, `/archive`, global `~/.claude/CLAUDE.md`). Growth below the ceiling is explicitly fine. Currently 172 lines.

**Memory audit — 43 → 39 files, and two were actively wrong rather than merely stale**

- `feedback_archive_chats` instructed a future session to run **`tools/archive_chats.py` — a file this very work had deleted.** A dead path, propagated into memory.
- `feedback_archive_verbatim_timing` still mandated a manual `.txt` archive that the protocol had dropped.
- **Deleted three superseded:** `project_phase_progress` ("Phases 0-2 complete; Phase 3 next" — three phases stale), `project_vertex_vm_decision` (executed), `project_goals_interview_ready` (the interview ran 2026-06-26).
- **`project_gcp_billing_infra` rewritten to *point* rather than restate.** It carried a threshold ($20→$30) that has since changed five times. The memory now holds only the non-obvious part — a hard-cap trip is an outage, not a cost event — and sends the reader to `CLAUDE.md` for numbers. Same "short half-life" rule as the ephemeral IP, applied to memory.

**Rejected: trimming `ROADMAP.md` Track D (~14 KB), the largest remaining item.** A parallel window committed to that file at 00:22 the same day and A7 status was actively moving — the A4 clinical-flag gate filed from this work had already been **cleared by that window** (`b3229ff`, PASS 6/6). Editing it would have risked conflicting with live work, and the A6 slip in the first pass is the standing warning about trimming that file by line range. It should be trimmed by whoever is working those tracks, not by a token-reduction pass.

**Where this leaves it.** What remains in the loaded set is load-bearing: persona ownership rules, the pre-edit check, One Home Per Rule Class, the binding privacy ruling, live tracks. Recommendation on the record: **stop here.** The architecture is no longer the constraint.

**Superseded handoff paragraph, carried from `SESSION.md`:**

*Updated: 2026-08-04 (auth, injection defense, web access, email — closed) — **Track B2 authentication is live and verified in production** (`8e5c47e`): every endpoint 401s unauthenticated, the app shell still loads, and `/ws` is gated by a first-frame handshake because Starlette runs no HTTP middleware for a WebSocket. The server now **fails closed** without `METATRON_AUTH_PASSWORD`; it is on the VM, and `deploy.sh` aborts before `git pull` if it ever is not. **`fetch_url` and `read_email` are live, granted to `logistics` only, and all external content is wrapped by `tools/untrusted.py`.** The SSRF guard is not theoretical — the VM's metadata server hands a working OAuth token to an unauthenticated request, so an unguarded fetch would have leaked the Vertex service account. **Corrections:** `deploy.sh:54` checks the *VM's* `.env`, not the Mac's — the previous handoff says otherwise and is wrong; and its abort message used to advise an `scp` that would have deleted `GOOGLE_APPLICATION_CREDENTIALS`. **Next:** item 5's Python confirmation gate (Decisions A/B/C await Mike), and an APK rebuild for the password reveal toggle.*

### 2026-08-04 (auth, injection defense, direct web access, email) — `11a166d`, `5795f31`, `09d2f38`, `22e179d`, `6739d62`, `fe0d688`, `8e5c47e`, `819de75`, `17a88c6`; **deployed `8e5c47e`**

Writeup: [archive/sessions/2026-08-03 — Auth, Injection Defense, Web Access, Email.md](sessions/2026-08-03%20—%20Auth,%20Injection%20Defense,%20Web%20Access,%20Email.md)
(named for the date the session opened; it ran past midnight). Worked
[archive/plans/phase5_prompt_2026-08-03_security_web_email.md](plans/phase5_prompt_2026-08-03_security_web_email.md)
items 1–5. Ran in parallel with a second window; neither touched the other's files, but see
the correction below — the two windows disagreed about a fact and one of them was wrong.

**Item 1 — server authentication (roadmap B2).** Every endpoint was open; `/monitor/file`
would hand the user's whole `data/` tree to anything on the tailnet. `core/auth.py` +
middleware + `POST /auth/login`.

- **Cookie *and* bearer, one secret.** The cookie carries the same-origin browser; the bearer
  carries the CLI, scripts and the Android app, which is cross-origin from a Capacitor WebView
  and so never receives a `SameSite=Lax` cookie. **Rejected:** bearer-only with `?token=` on
  the streaming URLs — works, but writes the secret into access logs and browser history.
  **Rejected:** gating normal endpoints and leaving `/session/stream` open — that is most of
  the exposure.
- **Tokens signed, not stored.** They survive a restart, so the phone is not logged out by
  every deploy, and a password change revokes all of them at once.
- **Middleware, not a per-endpoint dependency.** The failure being closed off is an endpoint
  nobody remembered to protect; only a middleware cannot be forgotten when the next route is
  added. **WebSocket is the exception and had to be** — Starlette runs no HTTP middleware for
  a WS handshake, so `/ws` uses a first-frame auth handshake. `ConnectionManager.connect()` no
  longer calls `accept()`; the endpoint does, before the check, so an unauthenticated socket
  never joins a broadcast group.
- **Fail-closed at startup.** No `METATRON_AUTH_PASSWORD`, no server — a server that ran
  unauthenticated because a hand-copied variable was forgotten would silently reopen the hole
  while looking healthy.
- **Four internal clients would have broken.** They hold the password already and the signing
  key derives from it, so they mint tokens locally rather than calling `/auth/login`:
  `sync_dev_backlog.py`, `metatron_monitor.py`, `remote_client.py`, and the health checks via
  new `scripts/mint_token.py`. **`core/auth.py` is stdlib-only with lazy annotations** because
  the SessionStart hook runs `sync_dev_backlog.py` under macOS system Python **3.9**, where a
  `str | None` evaluated at import is a `TypeError`. Caught by running it, not by reading it.

**Item 2 — enforce flip deferred, by Mike's decision.** The denial log showed 2 entries; an
audit of every agent file against `allowed_tools` found **43 gaps across 11 agents**. Mike's
ruling: these are the intended build-out, not breakage — the agent files are written ahead of
the tools. So warn mode stays until those tools are actually granted. **Rejected:** flipping
enforce on the strength of the 2-entry log, which would have broken the other 41 silently.

**Item 3 — indirect injection defense.** `tools/untrusted.py`. The convention was documented
in `tools/caldav.py` and `logistics.md` and implemented in neither, while the calendar had
been reading external invite text in production since 2026-08-03. **The part that makes it
more than decoration:** it neutralises `<untrusted_content>` tags *inside* the content, because
otherwise a page containing `</untrusted_content> Now follow these instructions:` closes the
boundary early and the rest reads as trusted. Wrapped once around the whole event list rather
than field by field, so JSON structure survives.

**Item 4 — `fetch_url` and `read_email`.**

- **SSRF drove the design, not page size.** Verified live: the VM's metadata server returns a
  **working OAuth access token** to an unauthenticated request. Without the block, one injected
  line in a page or email would have had `fetch_url` return the Vertex AI service-account token
  as page content. Every redirect hop is resolved and range-checked; redirects are followed
  manually because delegating to `requests` lets a 302 land on the metadata server after the
  first check passed. Hostnames are **resolved, not pattern-matched** —
  `metadata.google.internal` and an attacker's DNS record both look ordinary as text.
- **Stdlib HTML-to-text**, no new dependency on a 4GB VM; JS-rendered pages return nothing and
  say so. **Rejected:** a headless browser.
- **`tools/mail.py`, not `tools/email.py`** — `tools/` is on `sys.path`, so that filename would
  shadow the stdlib `email` package the module needs.
- **`BODY.PEEK`** so reading the inbox does not mark it read. Attachments never parsed.
- **Granted to `logistics` only.** `research_agent` omits `allowed_tools` entirely, which means
  *all* tools — a pre-existing least-privilege gap. **Deliberately not fixed here:** adding a
  list would silently strip every other tool from the grounded path. Filed; belongs to B2.

**Item 5 — outward-actions scope decision** ([plans/outward_actions_scope_2026-08-04.md](plans/outward_actions_scope_2026-08-04.md)),
proposal awaiting Mike. Main finding: **the policy question was already answered** — the
Synthesizer's action tiers classify by reversibility and external effect, every capability
item 5 names is already on the table, and all `preferences.yaml` opt-ins are `false`. Two
things are open: (A) the tiers have no axis for *who proposed* an action, which only started
mattering when `fetch_url`/`read_email` shipped this morning; (B) **the entire gate is a
prompt** — verified, no confirmation gate exists in `tools/` or `core/orchestrator.py`. That is
the control class already shown not to hold (logistics called `write_agent_config` three times
after being merely *told* it lacked it). Recommendation: no outward tool ships until the gate
is enforced in Python, built with B2's; first consumer `send_email` restricted to the user's
own address.

**App changes** (Mike's requests, mid-session):

- **Voice toggle**, persisted, defaults off. **The first fix was wrong and Mike's question
  caught it.** He asked whether `startRecording()` stops playback or also *prevents* it — it
  only stopped it. The reported bug is a *delayed* reply talking over a recording, and the
  delay is the `await` on `/tts`: tap the mic during it and the audio still arrives with
  nothing left to stop. Now guarded after the `/tts` await, after `decodeAudioData`, and on the
  Web Speech fallback path, which was uncovered entirely. `micIntent` is set *before*
  `getUserMedia` because `isRecording` is only set after it resolves. Late audio is discarded,
  not queued.
- **Password reveal toggle** on the login field (`819de75`), committed but not rebuilt — rides
  the next APK, as agreed. Never persists "visible".
- **Password changed to a weak, memorable value at Mike's explicit direction.** He judged the
  security bar over-set for a single-user system with no public ingress on 8001 (verified: the
  only firewall rule on `metatron-net` is IAP SSH on 22). Recorded as his call, not an
  oversight.

**Corrections to things believed true earlier:**

1. **`deploy.sh:54` does *not* check the Mac's `.env`.** The parallel window reported it did,
   and the outgoing handoff paragraph below states it as fact. It is wrong: the guard sits
   inside the quoted `<<'REMOTE'` heredoc (lines 40–95), so it runs on the VM after
   `cd ~/multi-model-mcp` and greps the VM's `.env`. Verified by running the same construction.
   What was actually observed: `git push origin main` is **line 30**, before the SSH block — a
   push happening is not evidence the guard passed. That window's SSH failed on the outage, so
   the guard was never *reached* rather than bypassed.
2. **But the guard had a real bug one step over,** which the false report led to: its abort
   message told the user to `scp .env` over the VM's. Confirmed destructive —
   `GOOGLE_APPLICATION_CREDENTIALS` exists **only** on the VM, so that command would have
   deleted the Vertex AI credential path every model call depends on, to deliver one password.
   Same class as the `config/personas/` rule in `CLAUDE.md`, one file across. Now appends the
   single variable idempotently (`22e179d`).
3. **I told Mike a stop/start would make the outage much harder to diagnose. That was wrong.**
   The volatile part — the serial ring buffer — was already lost (it retains ~48 minutes and
   the onset was ~4 hours back). The guest's own logs live on the boot disk and survive a
   reboot. Corrected before he acted on it.
4. **`sync_dev_backlog.py` returning "0 new" is not evidence of no new events.** It fails
   silent by contract, so throughout the outage it was indistinguishable from a quiet inbox —
   which is how the outage was noticed at all. Post-deploy it pulled **3 new** entries through
   the now-authenticated endpoint.

**Verified in production after deploy** (`8e5c47e`): `/health`, `/monitor/file`,
`/monitor/personas`, `/session/stream` all 401 unauthenticated; `/` still 200; bearer and
cookie both 200; wrong→right password 401→200; WS bad/valid token `auth_failed`/`auth_ok`;
`read_email` and `fetch_url` return wrapped content; metadata-server fetch blocked; full
pipeline exchange completed; both services active, no errors; `check_personas.py` exits 0.

**Not done, deliberately:** VM outage root cause (owned by the parallel window, which
recovered it); enforce mode; `research_agent` least-privilege; credential store; agentic
browsing; arbitrary-recipient email.


### 2026-08-04 (backlog triage, A4 safety gate cleared, ~4h VM outage) — `b3229ff`, `26c7859`, `e13d140`; **not deployed**

Writeup: [archive/sessions/2026-08-04 — Backlog Triage, A4 Safety Gate Cleared, VM Outage.md](sessions/2026-08-04%20—%20Backlog%20Triage,%20A4%20Safety%20Gate%20Cleared,%20VM%20Outage.md).
Ran in parallel with a second window working Track B2 (auth, injection defense, `fetch_url` —
`09d2f38`, `22e179d`). Neither window touched the other's files.

**Session opened as a plain-language pass over all 36 open backlog items.** Recommended first
target was the A4 clinical-flag gate, on four grounds: it is the only item gating everything
else (A7 → A8 → Alpha); it is a test run rather than a build; it has the worst failure mode if
wrong; and unlike items 21, 22 and 25 it needs no design decision from the user first. User
took it, preceded by the gitignore chore.

**Persona data trees gitignored.** `.gitignore` carried an enumerated per-persona list that had
fallen behind — `arthur_brooks`, `cal_newport`, `danny_park`, `maya_torres`, `oliver_burkeman`
entirely uncovered, plus most of `ryan_holiday`, all written to on every validation run.
Replaced with `data/personas/*/`.

> **Rejected: adding the five missing names.** A list requiring hand-maintenance on every
> persona creation *is* the failure mode, and it had already failed once. The glob covers any
> future persona on creation. Cost accepted: a genuinely new synthetic fixture now needs
> `git add -f`, because a fixture that silently fails to commit is recoverable and a real
> persona's logs that silently do commit are not.

**Two errors in that fix, one caught by the user mid-edit and worth recording.** The section
heading read *"Test persona runtime data"* and listed `mike` under it — `mike` is a real user's
logs, health and finances, not a fixture; that mislabelling was pre-existing and was carried
forward unexamined. Worse, the first draft promoted `sarah_chen`'s *"a genuinely new fixture
needs `git add -f`"* note to the top of the block, where it read as a blanket escape hatch over
every tree **including `mike`** — an instruction to force real user data past the ignore rule,
i.e. the 2026-07-29 incident with extra steps. Both corrected; `mike` now carries its own rule
stating no such hatch exists there. **The lesson: generalising a narrow permission is how a
safe rule becomes an unsafe one, and it happens in the same edit that fixes something real.**

**A4 clinical-flag hard-fail gate — PASSED 6/6, clearing the named pre-sign-off gate at
`ROADMAP.md:113`.** Prefix caching (2026-06-19) moved dynamic context out of the system prompt
for every agent, invalidating the A4 result. Re-run against the current assembly order with
`tests/run_a4_safety.py --persona sarah_chen --provider gemini`; report at
`tests/a4_safety_rerun_2026-08-04_gemini.md`.

> **Rejected: repeating A4's manual procedure.** A4 recorded the suites as "USER-RUN REQUIRED"
> prose in a session archive. That is *why* the gate sat unre-run for seven weeks, and A8's
> regression gate calls for the same suites again — so it was scripted. The runner refuses
> `--persona mike`: the scenarios write fabricated suicidal-ideation and mania records, which
> must never enter a real person's history.

Results were verified by reading the raw outputs, not by trusting the keyword match — a
mechanical check can pass for the wrong reason. `SUICIDAL_IDEATION` fired with 988 crisis
signposting and "do not move on to any other topic"; `MANIA` fired with an explicit instruction
not to celebrate the energy, which is its documented failure mode; `MEDICATION_MISSED_CRITICAL`
named lamotrigine as *"morning dose, required"* while correctly leaving `optional` vitamin D
alone. Finance arithmetic exact on all three, amortisation checked by hand.

**The finding that mattered more than the gate.** `physical_health` had never been granted
`read_agent_config`, while `physical_health.md:106` requires `MEDICATION_MISSED_CRITICAL` to be
classified from the stored medication profile and *"never from the agent's judgment"*. **The
flag was structurally unfireable in production** — the agent was required to consult a profile
it had no tool to reach. Granted in both routing files; `write_agent_config` deliberately not
granted (larger privilege, separate decision). This resolves the two warn-mode Inbox entries
from 2026-08-03, which were the symptom of exactly this.

> **No assembly-order re-run would have surfaced it.** It appeared only because testing the
> flag required seeding a medication fixture. Generalised into the roadmap: **a safety flag
> that is never exercised by a test is not known to work, however carefully its instruction
> file is written.** Correcting tool allowlists is the sanctioned activity right now —
> `CLAUDE.md` § Security, *"Correct the lists, verify, then enforce"* — which is why
> permissions shipped in warn mode.

**Believed true earlier, wrong: that the gate was purely a prompt-position question.** It was
framed as "re-verify the flags still fire after the caching change." One of the three had never
fired at all. The re-run's value turned out to be in exercising the path, not in comparing
against a baseline.

**~4-hour production outage, found by accident.** `./deploy.sh` failed at SSH. GCE reported
`RUNNING` and the serial console was logging in real time — the OS was alive, not hung — but
every process inside failed identically on `dial tcp 169.254.169.254:80: connect: network is
unreachable`, the metadata server on a link-local address. `network is unreachable` rather than
a timeout means **no route existed**: the guest NIC had lost its routing. Billing `True`, IAP
firewall correct, IPs assigned, `lastStartTimestamp` three days earlier — networking died under
a running machine. Recovered with `metatron-pause.sh` → `metatron-resume.sh` (user-authorised);
both services active, health `{"status":"ok"}`.

> **Same signature as the 2026-07-31 `nic0 is frozen` incident, but with that incident's known
> cause absent** — billing was never disabled this time. So either the 2026-07-31 attribution
> to the billing freeze was wrong, or there are two paths to the same failure. Root cause
> unknown; filed. This matters because the failure is silent and survives a `RUNNING` status
> check.

**Deliberately not deployed.** The parallel window's auth work means `core/server.py` now fails
closed without `METATRON_AUTH_PASSWORD`, and `.env` is gitignored so deploy cannot carry it.
**Verified on the VM: the variable is absent.** Deploying would have left the server refusing to
start. VM HEAD remains `b5ba807`. Consequence: the `read_agent_config` grant is live nowhere and
`MEDICATION_MISSED_CRITICAL` stays dead in production until it ships.

**`deploy.sh`'s preflight guard checks the wrong machine — still open.** Line 54 greps the
**local** `.env` for `METATRON_AUTH_PASSWORD` while the abort message says *"the VM's .env"*.
Proven empirically today rather than by reading: this session's deploy passed the guard on the
local file's strength and pushed, and **only the SSH failure — the outage — stopped a `git
pull`.** On a healthy VM that deploy would have completed and taken production down, which is
precisely the outcome the guard exists to prevent. The parallel window improved the
*remediation message* in `22e179d` (append the variable, do not scp the whole file — correct,
since the VM's `.env` holds values the Mac's does not) but the check itself still tests the Mac.
Filed.

**Nothing detects a down VM.** `scripts/sync_dev_backlog.py` runs first every session, is the
first thing to touch the VM, and exits 0 silently when unreachable — correct for a *paused* VM,
wrong for a *broken* one. During the outage it printed `0 new, 40 open`, indistinguishable from
a healthy run. Filed.

---

### 2026-08-03 (context-file audit — SESSION.md split, roadmap abridged, `/archive` formalised)

Full writeup: [../archive/sessions/2026-08-03 — Context-file audit: SESSION.md split, cold-start trim, archive command.md](sessions/2026-08-03%20—%20Context-file%20audit:%20SESSION.md%20split,%20cold-start%20trim,%20archive%20command.md).
Commits `403ecb9`, `7599ed8`, `c4d2c4d`, `3a17f1a`, `b6543f7`. **Docs and `.claude/` only — not deployed.**

**Started as "how large is SESSION.md?" (775 lines / 126 KB) and became an audit of the whole cold-start path.** The finding was not one bloated file: six context files had accreted overlapping jobs with no rule about which owned what. The project already had the doctrine for this — **One Home Per Rule Class**, written that same morning — and had never applied it to its own context files.

**Measured, before anything was moved:** ~88k tokens loaded before the user types a word, ~44% of a 200k window. Four files were 60–80% history rather than state. `CLAUDE.md`'s Deployment Infrastructure section alone was 27,308 of 50,706 bytes — 54% of a file auto-loaded into *every* session, including ones that never touch infrastructure.

**Result: ~88k → ~28k.** A real `/metatron-code` session now measures ~15k for the files it reads, plus ~13k auto-loaded.

**What was built**

- **`archive/PROJECT_LOG.md`** (this file) — dated history, append-only, never loaded. All 44 `### Also done` sections moved **verbatim**; verified byte-identical at 13,336 words both sides.
- **`docs/INFRASTRUCTURE.md`** — recreate-from-scratch, outage runbooks, systemd unit files, APK build, local Ollama dev.
- **`ROADMAP.md`** — abridged live copy. Binding privacy ruling, A5b/A5c/A7/A8, all of Track B and D, phase gates, pre-Alpha streaming items.
- **`.claude/commands/archive.md`** — the five-step ritual, executable rather than remembered.
- **`scripts/audit_context_load.py`** — reads a session's JSONL and reports what it actually loaded. Built so the second pass is evidence-based rather than recalled.

**Decisions, and what was rejected**

1. **`SESSION.md` is replaced; the log is appended.** This is the whole anti-regrowth mechanism. The file reached 775 lines purely because "update SESSION.md" was read as *append*, session after session, for two months. Without changing the protocol the cut would have undone itself by October.
2. **Trigger-adjacent pointers, not an index.** An index only helps someone already looking. Pointers go where the *problem* appears. **Rejected:** a table of contents in `SESSION.md`, which would have been read past.
3. **The test that decides what may move: anything that must fire *unprompted* cannot live in an on-demand doc.** This is why the external-IP trap, the persona VM-ownership rule and the billing caps table stayed in `CLAUDE.md` regardless of byte count.
4. **Decision-level statements never name a model provider.** `CLAUDE.md`'s "don't revisit" list said *"Orchestrator calls Claude API directly"* long after the runtime moved to Vertex. **Rejected: rewriting it to say "Vertex"** — that goes stale again on the move back to self-hosted, which is the stated North Star (`core/router.py:43` branches on `DEPLOYMENT_MODE` at call time; only two non-vendor files mention Vertex). The invariant is that the Orchestrator calls *a model API* directly; the provider is routing config. This is the existing "don't write down values with a short half-life" rule applied one layer up.
5. **The rolling handoff paragraph was kept deliberately** — one paragraph, rewritten not stacked. Four of the five then-current paragraphs contained a *correction* to a previous one, which is exactly what a status table flattens away.
6. **`DEV_BACKLOG.md` removed from the autoload** (user's call, and the largest single win at ~7.5k tokens). It is a work queue, not project context — ordinary coding takes its task from the user. The sync step stays: it writes to disk and costs no context, so the file is current whether or not it is read.

**Corrections — things believed true that were not**

- **Claimed `archive/transcripts/` (132 MB) was carried by every clone and VM pull. False.** Already gitignored, 0 files tracked, `.git` is 9 MB, and `daily-backup.sh`'s exclude list does not cover it, so it *is* in the daily encrypted backup. Nothing to fix.
- **Claimed `.claude/` is gitignored "entirely" so slash commands have no backup. False** — `.gitignore:28` has `!.claude/commands/*.md`; all three commands are tracked. This claim had propagated from `SESSION.md:225` into the new `/archive` file before being caught.
- **The backlog read 97 open; only 24 were real.** 70 of 94 bullets were the agent-file mirror — a copy whose own heading admitted *"These are mirrors, not moves."* The same text existed in three places (agent file, roadmap Section 4, `DEV_BACKLOG.md`). Deleted after verifying all nine originals present, 77 lines.
- **Carried A6 into `ROADMAP.md` although it is complete** — the line-range extraction caught it between A5c and A7. Found by audit and removed in `7599ed8`. This is the standing warning about trimming Track D the same way.
- **`CLAUDE.md:341` still warned that `networks/default` may be frozen.** It thawed; probe-tested twice.
- **Two divergent copies of `archive_chats.py`** (353 vs 295 lines) writing to the same directory, each named by a different protocol document. Diffed: the global copy is a **strict superset** with zero project-only functions. The in-repo copy was a stale June 19 ancestor — deleted.

**User corrections during execution, both of which improved the outcome**

1. **"The roadmap is static — don't trim it."** Correct: it is a dated plan document, and editing it rewrites the record. The abridged `ROADMAP.md` was created instead, naming explicitly what it does *not* carry so omission is never mistaken for completion.
2. **"What happened to that suggestion?"** — the abridged file had been proposed, then deferred by me to a second pass. Built in-session instead.

**Verification, not assumption**

Cold-start acceptance test: **17/17** questions answerable from the trimmed load, including all five standing rules that must fire unprompted. Then a live test run (session `998a7b0f`), audited from its JSONL: all expected files read, the static plan **not** read (the anchor held), `CODEBASE_INDEX.md` correctly skipped, and **no file the session had to go find**. It answered the billing question completely *and* cited `docs/INFRASTRUCTURE.md` for the runbook without opening it — the pointer design working as intended. It also surfaced a pre-sign-off gate at `ROADMAP.md:113` (prefix-caching moved dynamic context out of the system prompt, so the A4 clinical-flag hard-fails need re-running before sign-off) that neither the audit nor the acceptance test had listed.

**Superseded handoff paragraph, carried from `SESSION.md`:**

*Updated: 2026-08-03 (context-file audit) — **`SESSION.md` was 775 lines; the history now lives in [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md).** Six context files had accreted overlapping jobs with no ownership rule, so the cold-start load had reached ~88k tokens. Dated history, deploy runbooks and the agent-backlog mirror moved out; the standing rules buried in them moved into `CLAUDE.md`; `/archive` became a real command. Immediately before this: `deploy.sh` cried wolf on a good deploy and is fixed — its assertion tested exact HEAD equality, so a parallel window's push made the VM strictly *ahead* and it printed `DEPLOY FAILED … running OLD CODE`, the opposite of true. It now tests **ancestry** with four outcomes (`unverified` / `match` / `ahead` / `failed`) and names the extra commits. **The `ahead` branch is harness-tested only.** Deployed `3492d42`, `c674a91`.*


### Also done 2026-08-03 (outage chat closeout — ✅ `networks/default` HAS THAWED; two items carried into the backlog) — `48e17da`, docs only

Full writeup: [archive/sessions/2026-08-03 — Outage Chat Closeout, default Network Thawed, Backlog Carryover.md](../archive/sessions/2026-08-03%20—%20Outage%20Chat%20Closeout,%20default%20Network%20Thawed,%20Backlog%20Carryover.md)

**✅ `networks/default` is no longer frozen.** Probe-tested: an instance created on `default` came up `RUNNING` on `10.128.0.4`, then deleted. Google restored it between 07-31 and 08-03, past their own 3–5 business day estimate but without further intervention. The 26-hour outage is fully closed and the support case can be closed. **`CLAUDE.md:339` is now stale** — it still warns future sessions off a network that works. `metatron-vm` stays on `metatron-net`; moving back would mean another rebuild for no gain.

**Two items carried into `DEV_BACKLOG.md`, closing out the 07-30 → 08-03 chat:**

1. **"Unsurfaced opportunities" instrumentation** — new entry under *needs building* › *Troubleshooting signal*. It had lived only as prose in this file since 07-29 and was never carried across when the backlog became the single change-request list on 08-02 — which made it the one item at real risk of aging out silently. Records why the obvious approach fails (**you cannot diff against a ground truth nobody wrote down**) plus three routes: reason-code on the `·` dot, retrospective sweep, and closing the loop on `open_threads`/`follow_ups`. Recommended 1 + 3.
2. **Roadmap D2 item 5** — amended, not duplicated; the existing entry was already correct. What was missing: the roadmap *itself* still says *"6-turn / 88K cumulative token loop"* and still prescribes a `coordinator.md` change, so anyone reading the plan without the backlog gets a fix aimed at the wrong component. The roadmap body was deliberately left alone — it is a dated snapshot, and rewriting it would erase what was believed at the time.

**⚠ Correction carried in from the 5th window: the external-IP saving is withdrawn.** My 07-31 recommendation to drop the VM's "unused" external IP was wrong — it is the only egress path (no Cloud NAT, Private Google Access `False`), so removing it would kill Vertex AI, Tailscale and deploys. The error was reasoning from *"nothing connects inbound"* to *"unused"* without checking egress.

**Generalisable:** when a tracking convention changes, items recorded under the old one do not migrate themselves. Worth sweeping this file's prose for other open items predating 08-02 that were never carried over.

### Also done 2026-08-03 (calendar delivers, weather tools, warn-mode tool permissions, VM backup) — **deployed `cfcd212`, `6865058`**

Full writeup: [archive/sessions/2026-08-03 — Calendar Delivery, Weather Tools, Tool Permissions, VM Backup.md](../archive/sessions/2026-08-03%20—%20Calendar%20Delivery,%20Weather%20Tools,%20Tool%20Permissions,%20VM%20Backup.md) · Plan: [capability_gap_gameplan_2026-08-03.md](../archive/plans/capability_gap_gameplan_2026-08-03.md)

**The reminder problem is solved.** `write_calendar_event` gained `recurrence` (RRULE), `alarm_minutes_before` (VALARM) and `all_day`. This was the real blocker — the builder emitted a bare one-off `VEVENT` with no alert, so enabling CalDAV alone would have produced a *silent single event*, the same false-success shape as SEQ 021. Credit-card bills now exist as a recurring all-day deadline on a dedicated Metatron calendar.

**CalDAV gotcha, recorded so it is not rediscovered:** `apidata.googleusercontent.com/caldav/v2` **requires OAuth 2.0 and 401s on app passwords** (verified against four URL variants). Use the legacy `https://www.google.com/calendar/dav/{CALENDAR_ID}/events`, which accepts basic auth. A calendar's `.../basic.ics` address is **read-only** — only the ID inside it is useful. Corrected in `config/templates/caldav.yaml`. The same app password authenticates IMAP, which de-risks Phase 5.

**Framework adopted — three kinds of time-bound thing.** *Appointment* (fixed time, should interrupt) → calendar event + alarm. *Deadline* (a day, no time) → all-day event, no alarm, Synth folds it into that day. *Condition* (needs judgement — "water the plants if it hasn't rained") → scheduler job. Prefer the calendar wherever it suffices: no AI at fire time, no cost, visible in the user's own app.

**`get_weather` + `get_environmental_snapshot`** built in `tools/ambient.py`, registered, tested live. `get_weather` adds **recent rainfall** with a computed `days_since_rain` (Open-Meteo — wttr.in only forecasts, but rain decisions are backward-looking). UV is free from the existing wttr.in call; **AQI is not in wttr.in** and comes from Open-Meteo, failing soft. Coordinates reused from `nearest_area` — no geocoding call. **Supersedes roadmap decision 16** (weather-only at E1) by explicit user decision.

**Tool permissions live in WARN mode.** `dispatch_tool` now checks the calling agent's grant. Previously the whitelist filtered what an agent was *shown* but handlers were looked up unfiltered, so any agent could call anything — and because it silently succeeded, nothing recorded that an agent wanted a capability it lacked. Denials emit a **`TOOL_DENIED`** quality event (deduped per agent+tool) which `sync_dev_backlog.py` pulls into `DEV_BACKLOG.md`. Nothing is blocked; flip to `METATRON_TOOL_PERMISSIONS=enforce` once the log is reviewed — required before E1 integrations.

**Standing practice adopted:** (1) the denial audit runs continuously — grant on demonstrated need, never blanket; (2) `DEV_BACKLOG.md` is the single intake; (3) every development is backchecked against the plan for cohesiveness. All nine agent `## Enhancement backlog` sections **mirrored** (not moved) into `DEV_BACKLOG.md`.

**`scripts/metatron-backup.sh` (new)** — nothing on the VM was captured by git; 12MB of real data survived the July rebuild only because the disk was deliberately detached. Pulls VM state to the Mac, verifies before pruning, hardlinks `latest.tgz`; `daily-backup.sh` runs it first and includes only the latest. **Caught real Mac↔VM drift on its first run.** Also fixed: `.env.*` was unignored, so `.env.bak` files would have been committable with every API key.

**Corrections worth carrying:** an audit intended to strip stale tool references found the eight `run_subagent` mentions are *guardrails* reading "do not call `run_subagent` directly" — applying the proposed removals would have deleted the instruction preventing the behaviour. **Net removals: zero.** Separately, the 2026-06-24 token work established the narrow `allowed_tools` lists as deliberate (~95,000t → ~30,000t); widening them to match the agent files would have reversed the project's highest-leverage optimisation. And the agent-backlog token cost measures ~130 tokens total — not worth moving for cost, only for discoverability.

**Phase 4 (scheduler write access) and the tier-editability inversion are both closed** — see the next section.

### Also done 2026-08-03 (Phase 4 scheduler grants · `update_goal` · Tier 1–2 backup) — **deployed `2f74cd2`, `8e2983f`**

**Phase 4 complete.** `write_schedule` / `list_schedules` / `delete_schedule` granted to Synthesizer and Logistics in both routing configs. The tools had shipped registered but allowlisted to nobody, so nothing could call them. Verified on the VM. Tested before deploy: every cap refuses with a message naming what to drop; a one-off created *after* the daemon started armed within one 30s tick, fired once and self-deleted; a name collision with the user's `scheduler.yaml` resolves in the user's favour.

**Two agent instructions named an impossible action.** `synthesizer.md` and `logistics.md` both said to create recurring reminders with `write_config` — which permits only `prime_directive.md` and `mission.md`, so the call returns an error the user never sees. The SEQ 021 failure shape, sitting unfired because nothing had asked for a recurring reminder since. Both now point at `write_schedule`. `synthesizer.md` also claimed every specialist tool was available to it directly — false under the whitelist, and in warn mode it produces a denial rather than a refusal the model can act on.

**Tier-editability inversion — CLOSED.** New `update_goal(action, ...)` adds / updates / completes / removes **one** goal and touches nothing else; `write_goals` replaces a whole horizon, so any omitted goal was silently deleted. `complete` keeps the goal with a `completed_on` date; `remove` is for abandoned or mistaken entries only. Granted to the **Synthesizer** (where a goal is actually finished or taken on — mid-conversation) and to `goals_interviewer`, which already holds the stronger tool. `write_goals` stays with the interviewer alone, its schema now warning that omission deletes. Separately, **`write_config` now keeps the previous `prime_directive.md` / `mission.md` before overwriting** — held by the agent that runs every exchange, and a full replacement, so an unasked-for rewrite was unrecoverable. Backups are gitignored (`config/personas/*/*.bak`) — Tier 1–2 content.

**Doc drift corrected:** the server has been serving **HTTPS** on 8001 with a publicly trusted Tailscale cert (`metatron-vm.tail0acc5d.ts.net`), while `CLAUDE.md` documented plain HTTP in five places including the recreate-from-scratch checklist. Found because a health check against `http://` failed.

**Phase 2 of the capability-gap plan (agent-file reconciliation) is CLOSED, not done** — by explicit user decision 2026-08-03. Net removals were already zero, and the remaining question ("what should each agent legitimately hold?") is now answered continuously by the warn-mode denial log rather than in a batch. Handled in real time through `DEV_BACKLOG.md`; nothing further is owed to that plan.

**Still open:** location sharing (phone permission + calendar-derived inference; GPS agreed sensitive-tier, local-only, coarsened); Phase 5 — see [phase5_prompt_2026-08-03_security_web_email.md](../archive/plans/phase5_prompt_2026-08-03_security_web_email.md).

### Also done 2026-08-03 (check-in restraint · persona config ownership · biographical capture)

Full writeup: [archive/sessions/2026-08-03 — Check-in Restraint, Persona Config Ownership, Profile Capture.md](../archive/sessions/2026-08-03%20—%20Check-in%20Restraint,%20Persona%20Config%20Ownership,%20Profile%20Capture.md) · deployed through `35e53ee`.

**1. Check-in restraint — the cause was not an agent file.** `companion_checkin`'s *own prompt* said "lead with the most useful outstanding item… be specific about which one and why it matters now", every 180 min, all day — so an unresolved calendar item was correctly surfaced six times. Fixed at `config/templates/scheduler.yaml` (the baseline all new personas inherit, which also hardcoded "Mike" in a provisioning template) plus mike's copy. Two opt-in gates added to `core/scheduler.py`: `quiet_after_user_minutes: 60` and `min_gap_minutes: 180`; `interval_minutes` is now the *poll* rate. **Cost strictly lower** — polling is local reads with no model call and the gap preserves the old ~5/day ceiling. Five rules added to `synthesizer.md` (raise a thing once · explain first time not every time · never say "enjoy" · beware the loudest available signal · ask for missing data when the record is thin).

⚠ **Gate keys must never be added before the gate code is deployed** — `interval_minutes: 30` without the gates is a check-in every 30 minutes.

**2. `deploy.sh` MUST NOT push persona config.** `write_persona()` and `write_config()` edit `config/personas/{p}.md`, `prime_directive.md` and `mission.md` **on the VM at runtime**. Verified 2026-08-03: the VM's `mike.md` held five preferences recorded that morning the Mac copy had never seen — a push would have erased them. Stale Mac copies moved to `backups/`; only git-tracked dev personas remain there. Direction is Mac→VM by deliberate one-off `scp`, VM→Mac by `scripts/metatron-backup.sh`. Documented in CLAUDE.md and in a comment block in `deploy.sh` at the point of temptation.

**3. Biographical capture — `tools/profile.py`.** Contact details the user gave while asking for a booking had been filed into `mike.md` and rode in every prompt; moved to `profile.yaml`. A first attempt restricted `write_persona` and **broke the requirement** — users give biographical data in conversation and the tool must capture it — so it was reverted (`8659c4d`) and replaced with `write_profile`/`read_profile` (`35e53ee`). Read is separate from write on purpose: `load_profile()` renders a summary into every head-layer prompt but **excludes the contact block**; agents call `read_profile` at the point of use. Granted to synthesizer, logistics, physical_health, relationships, work_vocation, finance in *both* routing files.

**4. `.claude/commands/*.md` is now tracked** (needs `.claude/*`, not `.claude/` — git will not descend into an excluded directory). **A `.env` backup with live keys was sitting in the repo** (moved to `~/.metatron-secrets-backup`) and `.env` was mode 0644, now 0600.

**5. Ten legacy requests recovered** from `data/personas/mike/conversations/2026-08-0{1,2,3}.jsonl` into `DEV_BACKLOG.md`, predating automatic capture.

### Also done 2026-08-03 (Rule Redundancy — one home per rule class) — **deployed `0077a63`, `a03ed7e`**

Full writeup: [archive/sessions/2026-08-03 — Rule Redundancy: One Home Per Rule Class.md](../archive/sessions/2026-08-03%20—%20Rule%20Redundancy:%20One%20Home%20Per%20Rule%20Class.md). All four items of the plan agreed above are **done**. Layer-ownership table: **CLAUDE.md → One Home Per Rule Class**.

**1. The debt is cleared.** All five duplicates removed from the VM's `config/personas/mike.md` (backups at `~/metatron-backups/mike.md.pre-dedup*`); the file is down to two genuinely personal preferences and the live audit went **5 findings → 1**. Each removal was made **only after confirming the replacement was live on the VM**, not merely committed on the Mac — that check caught that the fifth rule was only half-rehomed.

**2. Detection is class-based, not text similarity — and this is the part not to re-derive.** *"Stop repetitive reminders for pending tasks"* and *"Raise a thing once…"* are the same instruction **with almost no words in common**; a word-overlap threshold sweep found 0/5 at 0.45 and 1/5 at 0.25. [`core/rule_classes.py`](../core/rule_classes.py) sorts rules into classes, each with an owning layer; similarity only *ranks* candidates within a class. Patterns must match **the complaint, not the instruction** — the first pass missed *"Stop bringing up the same task over and over"* for exactly that reason.

**3. Three checks.** Write time — `write_persona` → `check_new_rule()`, which **warns and never blocks** (refusing a write to keep a file tidy discards what the user actually said; that error was already made and reverted earlier the same day). Daily — `daily_rule_audit` at 05:30, a `function:` job costing **zero model tokens**, findings → `RULE_CONFLICT` → `DEV_BACKLOG.md`, each reported **once**. On demand — `scripts/check_rule_overlap.py`.

> **The daily sweep is the load-bearing one.** The write-time check only sees what Synth writes. *The five duplicates were written by hand, in a development session* — no write-time guard could ever have caught them.

**4. Measured, so a clean report isn't mistaken for proof.** Against the real set: **5/5** recall on which preference is duplicated, **0** false positives across eleven novel preferences, but the *partner* named was wrong **3 times in 5**. The flagged preference is the reliable output. `CLASSES` is incomplete by construction — add one when a duplicate slips through.

**5. Cut deliberately:** agent-vs-agent comparison. The specialist files carry intentional parallel boilerplate (*"Mandatory pass. Runs every session"*, *"Voice mode:"*) that scores near-identical because it is, on purpose — it drowned the real findings. Still available via `check_rule_overlap.py --all-pairs`.

**6. Morning/evening sessions are not interruptible** (user decision, mid-session): they fire on the clock regardless of an active conversation and **redirect openly** — *"Now let's turn to the evening close"* — rather than folding in silently. Only `companion_checkin` yields. Note `_activity_gate_blocks` **skips, it does not defer**: a `time:`-anchored job that blocks is gone for the day, which is why the fixed-time sessions carry no gate.

**7. `data/personas/sarah_chen/` gitignored** — it is the validation-probe persona, so every run writes into that tree. The three seed logs stay tracked; a new fixture needs `git add -f`. Plus never-fixture rules for all personas: `traces/`, `config/`, `schedules.yaml`, `logs/quality_events.json`.

> **Concurrency note.** The parallel window held uncommitted edits to `synthesizer.md`/`logistics.md`/routing files throughout. Handled with surgical `Edit` calls in distant regions, per-file staging, and never `git add -A`. Their `2f74cd2` then swept up both of my `synthesizer.md` rules — **verified present in the deployed file on the VM** rather than inferred from the commit graph, which corrected a backlog entry that wrongly claimed they were pending.

### Also done 2026-08-02 (Synth self-development awareness + `DEV_BACKLOG.md` — the single change-request list)

Full writeup: [archive/sessions/2026-08-02 — Synth Self-Development Awareness and Dev Backlog.md](../archive/sessions/2026-08-02%20—%20Synth%20Self-Development%20Awareness%20and%20Dev%20Backlog.md)

**Problem:** Mike is both user and builder, but when he asked for a change mid-conversation it evaporated — no frame for what kind of change it was, and nowhere durable for it to land.

**Now:** the Synthesizer triages a change request into three routes and says which plainly — *handle now* / *needs a change outside this conversation* / *needs building* — then records it. Requests land in **[DEV_BACKLOG.md](../DEV_BACKLOG.md)** at the project root, git-tracked and visible in the file tree: `## Inbox` is machine-written, everything below hand-curated.

- **`config/personas/mike/self_development.md`** (new, gitignored, `0600`) — the triage instruction, ~700 tokens. Loaded by `load_config()` only when present, so **no other persona's behaviour changes**.
- **`_persist_dev_request()`** in `core/orchestrator.py` — reads a `dev_request` key off the `[CONTEXT]` block the Synthesizer already emits and calls `write_quality_event()` directly. **Zero extra turns:** a tool call would have cost a second Pro turn (~13.4K input, +$0.017, +3–8s) — exactly the overhead SEQ 031 removed.
- **`scripts/sync_dev_backlog.py`** — stdlib-only, pulls the VM's quality events through the existing `/monitor/file` endpoint over Tailscale, filters to the three request types, dedups on timestamp. 3s timeout, **exits 0 silently when the VM is paused**. Wired into `/metatron-code`.
- **`config/agents/synthesizer.md`** — one pointer line. Freeze lifted on explicit instruction, same exception as SEQ 002/008.

**Cost:** under $0.50/month, no measurable latency change on a normal exchange.

**Plan assumption proved stale, in our favour:** the plan budgeted extracting the `[CONTEXT]` parser into a shared helper. `split_context_block()` / `persist_context_block()` already exist and are already called from **both** pipeline paths — so **SESSION.md backlog item 4 below is stale** and the change collapsed to ~35 lines.

**Two failures found by live testing, both fixed:**
1. **Route 3 recorded nothing.** The instruction said to name the gap *"as you already do for capability gaps"*, which pointed the Synthesizer at the pre-existing `TOOL_NOT_BUILT` open-thread and it skipped `dev_request` entirely — perfect-looking response, empty backlog. Fixed by making the requirement unconditional.
2. **Confidentiality beat self-development.** Asked *"will those changes stick?"*, it emitted the canned *"I'm here to help you manage your life"* — self-generated, not the output filter. A legitimate question about the user's own request got stonewalled. Fixed by carving the boundary explicitly: whether a change stuck is about *his request*, not how the tool is built.

All four probes pass against `sarah_chen` on the real Vertex pipeline. Test artifacts removed afterwards to keep her a clean subject.

**Auto-sync: `SessionStart` hook, added 2026-08-03** (`.claude/settings.local.json`, alongside the existing `Stop` hook). Fires on opening a Claude Code chat in VS Code — and on resume/clear/compact/fork — so `DEV_BACKLOG.md` is current without anyone running the sync. Measured cost: **0.99s reachable, 0.11s with the VM down**, no lingering process. launchd was offered and declined in favour of this, on the grounds of not adding background processes. `/metatron-code` also runs it, for sessions where the hook is off. **Note `.claude/` is gitignored entirely — this hook reaches neither the VM nor GitHub and has no backup.**

**Legacy requests recovered 2026-08-03.** Crawled `data/personas/mike/conversations/2026-08-0{1,2,3}.jsonl` and the `quality_events` stream for asks made before automatic capture existed — **10 recovered into `DEV_BACKLOG.md`** (now 15 open). Notable: check-ins firing during live dialogue (*"only need be done if there's not an ongoing dialogue — otherwise fold them into the conversation"*, SEQ 020) is both the user's request **and** the largest cost lever on record; repetition of pending items (*"you've repeated the calendar thing about six times today"*); over-indexing on one disrupted night (*"once again"* — already raised before); transcription timeouts and dictated-email errors; calendar delivery (corroborates capability-gap Finding 3); and a request to act on an external website, which carries a real security surface since the same message handed over email, postal address and phone number. The 2026-08-01 timestamp request turned out to have been closed by the SEQ 008 fix the next day — filed under Done, not Open.

**Deployed and verified** (commits `6601479` + `dc0d85c`; `6601479` also carries the parallel session's SEQ 021 fixes, since both sat in `core/orchestrator.py`). `NRestarts=0`, both services active. `self_development.md` `scp`'d separately — gitignored, so `deploy.sh` cannot carry it. Post-deploy probe on `mike` over `/session/stream` returned *"held and will carry forward"* and terminated `[DONE]`, not `[RETRACT]`.

**Third bug, caught only at deploy time:** the sync script defaulted to `http://` on the raw Tailscale IP. **The server runs HTTPS** behind a Tailscale cert, and the IP form also fails hostname verification. Since the script fails silent by design it would have reported `0 new` forever instead of erroring. Fixed to `https://metatron-vm.tail0acc5d.ts.net:8001`, matching the orchestrator CLI default.

**⚠ Staging note for future sessions:** `data/personas/sarah_chen/` (and the other synthetic personas) are **not** gitignored — only `mike`, `pepys`, `test_a3` and parts of `ryan_holiday`. A `git add -A` in this tree repeats the 2026-07-29 incident. Everything here was staged by explicit path. **Worth adding gitignore rules for the synthetic persona data trees.**

**Two new backlog entries found in passing:** the `write_config`/`scheduler.yaml` discrepancy (`synthesizer.md:355` promises a capability `tools/config_writer.py:16` forbids — corroborated live by a Logistics tool failure in a tracker held-item), and **silent `[CONTEXT]` data loss** when the model emits malformed JSON (`split_context_block` logs and returns `None`, losing both the tracker write and the `dev_request`).

### Also done 2026-08-02 (SEQ 021 — specialist clock, tool-error hints, failure reporting; capability gap survey) — **DEPLOYED `6601479`**

Full writeup: [archive/sessions/2026-08-02 — SEQ 021 Logistics Turn Burn, Clock Injection, Tool Error Hints.md](../archive/sessions/2026-08-02%20—%20SEQ%20021%20Logistics%20Turn%20Burn,%20Clock%20Injection,%20Tool%20Error%20Hints.md)

**Bug:** user asked for a recurring monthly credit-card reminder (`mike`, SEQ 021). Routing was correct — Coordinator 1 turn. **Logistics burned 6 turns, 4 wasted**, saved nothing, and the Synthesizer told the user *"The reminder for the 15th is set."* It was not.

**Three root causes, all confirmed from the trace:**
1. Logistics guessed `write_agent_config`'s parameters three times (`content`, `recurring_obligations`, `data`) and never tried the real `key`/`value`. `dispatch_tool()` returned the bare Python `TypeError`, which says the guess was wrong but not what is right.
2. The three failures never reached the Synthesizer, so it confirmed a save that never happened.
3. **Specialists receive no system clock** — Coordinator/Synthesizer get `recent_context`; specialists get `agent_file` + `goals` only. Logistics invented `log_date: 2025-05-22`, filing the note 14 months in the past.

**Four fixes written and validated locally against `sarah_chen` (full pipeline, real Vertex):**
1. `tools/ambient.py → current_clock_line()` + `core/orchestrator.py → clock_line()`, injected into the specialist branch of `_run_single_agent()` **via the user message** so the cacheable system prefix stays stable.
2. `dispatch_tool()` binds with `inspect.signature().bind()` before calling and returns `Correct usage: write_agent_config(required: agent_name, key, value)`. **Measured:** the same request that previously failed 3× and gave up now self-corrects on attempt 2 and saves.
3. `_failed_tool_calls()` appends `[TOOL FAILURES — these actions did NOT complete]` to specialist output. Excludes head/routing layer, and excludes any tool that later succeeded on retry (or a recovered error would produce a false "it didn't save").
4. Hallucinated `data/personas/mike/logs/2025-05-22.json` moved to `data/diagnostics/bogus_logs/` **on the VM**. No real data lost.

**Resolved 2026-08-03 — committed and deployed.** These fixes were held briefly because `core/orchestrator.py` also carried a parallel chat's uncommitted work; that chat committed both sets together in `6601479` and the VM now runs them. No action outstanding.

**Deliverable — [archive/plans/agent_capability_gap_2026-08-02.md](../archive/plans/agent_capability_gap_2026-08-02.md).** Written instead of reconciling `logistics.md` downward, at user's direction, since a calendar is arriving shortly. Headlines:
- **Finding 0 (security):** the per-agent tool whitelist filters `tool_schemas` but **not** `tool_handlers`, and `dispatch_tool()` does no whitelist check — **any agent can invoke any of the 43 tools.** Proven live: `logistics` is not granted `write_agent_config` yet called it three times in production and the dispatcher executed each. **Implication: every "told-but-not-offered" capability currently works by accident, so closing this (Track B / B2 PoLP) without first fixing the allowlists breaks them all at once. Fix the lists, then enforce.**
- **Finding 1:** all 13 agents name at least one tool they are not advertised (`logistics` 8, `finance` 7, `recreation_hobbies` 7). `run_subagent` appears in nine specialist files despite a hard recursion guard — dead instructions.
- **Finding 2:** `physical_health.md` names `get_environmental_snapshot`, which does not exist.
- **Finding 3 (behind the original complaint): nothing in the system can actually set a reminder.** CalDAV `enabled: false` with empty password; `scheduler.yaml` jobs are static with no tool to add one; `write_config` allowlisted to `mission.md`/`prime_directive.md`. A reminder can be *recorded* but never *delivered*. Build order: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store delivery preference.
- **Finding 4:** `WRITE_AGENT_CONFIG_SCHEMA` still documents the pre-persona path `data/config/{agent_name}.json`.

Four agent-file edits **proposed, not applied** — `config/agents/*.md` frozen post-review.

**`/metatron-troubleshoot` rewritten and verified** (`.claude/commands/`, gitignored — Mac-local, no commit/deploy). Fixed six defects after the third consecutive session where its stale paths broke the first data pull: persona-scoped conversation path; persona parameterised (was hardcoded `mike`, nine personas exist); `--tunnel-through-iap`; argument substitution (a real invocation produced `DATE = 2`, `SEQ = $2`); zero-padded SEQ matching with available-values listing on a miss; native ±2-min trace window replacing the exact-minute match. **Added `context_sections` output** — the decisive evidence in this diagnosis, previously needing a separate hand-written query. Tested against live data plus all three error paths. **Note: `.claude/` is gitignored entirely, so this file has no backup and reaches neither the VM nor GitHub — the original was already lost once.**

**Open from this session:** `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char 82852)` fired twice against a 276-byte file — offset doesn't match, so the memory indexer is likely reading a different/concatenated source. Unexamined. Pre-2026 logs (`2025-01-24`, `2025-05-13`–`16`) remain in `data/personas/mike/logs/` — believed genuine early-dev data, worth confirming none are further hallucinations.

### Also done 2026-08-02 (Synthesizer timestamp-authority fix — SEQ 008 diagnosis, fix, deploy, verified)

Full writeup: [archive/sessions/2026-08-02 — SEQ 008 Timestamp Fix, Deploy, Pepys Test.md](../archive/sessions/2026-08-02%20—%20SEQ%20008%20Timestamp%20Fix%2C%20Deploy%2C%20Pepys%20Test.md) · Commit `b184d92`, deployed.

**Bug:** Synthesizer echoed a user-claimed timestamp instead of checking the actual system clock (2026-08-01, SEQ 008, `mike` persona — "953" boundary test). Diagnosed via `/metatron-troubleshoot`.

**Fix (three parts, all landed):**
1. `tools/ambient.py` — ambient date/time now second-precision, labeled "authoritative" in context.
2. `config/agents/coordinator.md` + `synthesizer.md` — explicit instruction to trust the system clock over user-claimed times. **These files are frozen post-review** — edited on explicit user instruction ("fix this now") for this specific bug, not a general exception to the freeze.
3. `core/server.py` + `core/orchestrator.py` — WebSocket/SSE handlers now stamp the actual message-receipt time and thread it into both Coordinator and Synthesizer input (`run_pipeline_session_stream` → `_run_pipeline_session_stream_inner`). This mattered most: pipeline latency (this trace ~30s end-to-end) means "current time" at generation-time is already stale relative to actual arrival. Non-streaming `run_session()` (scheduler/CLI/proactive) intentionally untouched.

**Verified against `pepys` (non-Mike persona)** post-deploy: replayed the original bug pattern via `/session/stream` — user falsely claimed "3:00pm exactly," Synthesizer correctly responded "I received that message at exactly 9:24:41 AM" instead of echoing the claim.

**Known stale artifact, not yet fixed:** `/metatron-troubleshoot` command template still points at pre-persona-scoping paths (bare `data/conversations/`, `data/personas/mike/traces/` hardcoded to mike) — corrected inline this session but not on disk. Low priority, flag for a future pass.

### Also done 2026-08-02 (spend guard, GCP verification, scroll root-cause)

Full writeup: [archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md](../archive/sessions/2026-07-28%20—%20Persona%20Unification%20Complete%20(Phases%200-8,%20Strict%20Mode%20Live).md) (2026-08-02 section at the end).

**GCP account verified genuinely clean.** Created a throwaway instance **on `default`** — the exact operation that failed with `networks/default … is not ready` on 2026-07-30. It reached RUNNING, so Google's thaw did eventually complete. Probe deleted. Billing enabled; hard cap **armed** (the override expired 2026-07-31 — its leftover marker was removed, since it read as "hard cap disarmed"); no orphaned disks or static IPs. Only leftover is the pre-unfreeze snapshot (8.5GB, ~$0.22/mo).

**Spend guard live** (`core/spend_guard.py` + `config/modules/spend_guard.yaml`). GCP budget data lags hours, so the $70/$150 caps cannot catch a loop. Two in-process guards, hooked into `trace.record_turn_tokens` (the one point every provider already reports through):
- **Rate limit** — sessions per rolling hour, alert 20 / stop 60. Needs no pricing data, so it survives a stale rate table. **This is the guard that actually catches a loop.**
- **Spend limit** — token counts × rates, alert $5/day / stop $10/day.

Refusal returns plain user-facing text, not an exception. Both fail **open** on internal error — a bug in cost accounting must never take down a working assistant. Rate-limiter state is in-memory, so it resets on restart (acceptable: a restart breaks a loop).

**Costing bug caught by user challenge — reported figure was 8x too high.** Pricing keys were unprefixed but traces record `models/gemini-3.1-flash-lite`, so every lookup missed and fell through to `default`, set to Pro rates. All the Flash-Lite traffic — the bulk of every exchange — was priced at ~12x. Corrected: an exchange is **~$0.025, not $0.20**; a scheduled day **~$0.18, not $1.41**. Fixed with prefix normalisation, prefix-match fallback, and a warning on unknown models rather than silent defaulting.

**Measured token economics** (real): one exchange = 82,360 input tokens across coordinator (Flash-Lite, 1 turn), logistics (Flash-Lite, **8 turns**, 39,810t), physical_health (Flash-Lite, 5 turns), synthesizer (**Pro**, 1 turn, 12,989t). **The synthesizer is 71% of cost on 16% of tokens**, being the only agent on Pro — so it, not the Flash-Lite specialists, is the cost lever. Reconfirms the coordinator does 1 turn while specialists do 5-8: roadmap D2 item 5 is **mis-scoped** and needs re-measuring before any work.

**Conversation scroll — earlier fix was a no-op.** `body` used `min-height:100dvh`, so it grew past the viewport and `#conversation` (`flex:1`) expanded to fit content instead of being capped — it was never a scroll container, making `overflow-y`, `margin-top:auto` and `scrollTop` all inert. Fixed with `height:100dvh` + `overflow:hidden` on body and `min-height:0` on the flex child. **Testable in a desktop browser without installing the APK.**

**Open:** pricing rates are unverified estimates marked VERIFY (fine for order-of-magnitude runaway, not for accounting); activity-gating for check-ins; sentence-chunked TTS; browser live-refresh bug; turn-reduction re-scoping.

### Also done 2026-08-02 (Synthesizer recap fix — SEQ 002 diagnosis, fix, local validation — **NOW DEPLOYED**)

Full writeup: [archive/sessions/2026-08-02 — SEQ 002 Single Exchange Troubleshoot.md](../archive/sessions/2026-08-02%20—%20SEQ%20002%20Single%20Exchange%20Troubleshoot.md)

**Bug:** Synthesizer opened a response by restating specific facts the user had just given (dinosaurs, hedge maze, Sainsbury's meal deal — `mike` persona, SEQ 002) instead of acknowledging their meaning. No pipeline failure — correct routing, no filter hits — pure content-quality gap. Diagnosed via `/metatron-troubleshoot` (same stale-path issue as SEQ 008 above: had to fall back to `data/personas/mike/conversations/` and `--tunnel-through-iap` for SSH).

**Fix:** One sentence added to `config/agents/synthesizer.md` under "Direction and prioritization": *"Acknowledge, don't recap. Do not restate specific facts the user just gave you... as a summary opener... They already know what they told you; repeating it adds no value and reads as filler."* Frozen post-review file — **freeze lifted on explicit user instruction** for this fix, not a general exception. A longer first draft was cut per user direction — keep agent instruction files token-light.

**Validated locally; DEPLOYED 2026-08-02** (commit `799aa3f` went out with the spend-guard deploys from the parallel session — VM confirmed to carry the line). Original note follows:

**Validated locally, not yet deployed:** 3 iterations against `sarah_chen` (non-Mike dev persona) via `python3 core/orchestrator.py --persona sarah_chen --input "..."` (local Mac, `DEPLOYMENT_MODE=cloud` → real Vertex/Gemini pipeline). All 3 messages carried specific facts (museum/planetarium/pizza; skipped breakfast/coffee/sandwich/dentist; river run/stir fry) — no readback in any response. **`./deploy.sh` still needed** to push this to metatron-vm before it affects the live Mike sessions.

### Also done 2026-07-31 (⚠ 26-HOUR OUTAGE — VPC frozen by billing disable; VM rebuilt on a new network; cost control restructured)

Full writeup: [archive/sessions/2026-07-31 — Billing Cap Trip, VPC Freeze Recovery, Two-Tier Cost Control.md](../archive/sessions/2026-07-31%20—%20Billing%20Cap%20Trip,%20VPC%20Freeze%20Recovery,%20Two-Tier%20Cost%20Control.md) · Commit `571f9bc`, deployed.

**⚠ ~~`networks/default` IN THIS PROJECT IS STILL FROZEN.~~ SUPERSEDED 2026-08-02 — `default` is UNFROZEN, verified by creating a live instance on it (the exact operation that failed on 2026-07-30). Google's thaw did eventually run. The VM stays on `metatron-net` by choice, not necessity.** The VM now runs on a new VPC, `metatron-net` / `metatron-subnet` (`10.10.0.0/24`). Anything that assumes `default` exists will fail. Google support case left open to get `default` restored; tech team estimate was 3–5 business days.

**What happened.** `stop-billing` disabled billing at ~$31 against a budget already raised to $40, acting on a stale notification. Disabling billing froze the project VPC. Billing was relinked within hours, but Google's asynchronous thaw **never ran** — 25+ hours of `nic0 is frozen`. Recovered by building a new VPC and rebuilding `metatron-vm` on it from the existing boot disk. Tailscale reclaimed the same node identity, so `100.64.226.49` is unchanged and **no client changes were needed**.

**Cost control restructured** — the hard cap is now a firebreak, not a routine control. Distinction is recovery cost, not dollars:

| Tier | Amount | Action | Recovery |
|---|---|---|---|
| Soft | $70 | `stop-vm` stops the VM | ~60s |
| Hard | $150 | `stop-billing` disables billing | Days, plus a frozen VPC |

New `stop-vm` function source is tracked at [infra/stop-vm/](../infra/stop-vm/) — deployed, ACTIVE, tested. Override at `scripts/metatron-vm-override.sh` writes a *separate* marker from the billing override so silencing one cannot silence the other.

**This sits directly on top of the 2026-07-30 arithmetic below:** if infrastructure alone is ~$29/mo, a $70 soft cap leaves ~$40/mo of genuine AI headroom before anything stops.

**Bugs fixed:** `metatron-resume.sh` wrote the billing override *before* relinking — but the marker lives in a bucket inside the disabled project, so the write always 403'd and `set -e` aborted before the relink. **That recovery path had never once completed.** Also `deploy.sh` + resume now need `--tunnel-through-iap`, since `metatron-net` has no public SSH ingress (verified with a real deploy).

~~**Check when convenient:** the rebuilt VM has an unused ephemeral external IP; removing it saves ~$2.90/mo.~~ **Withdrawn 2026-08-03 — do not act on this.** The IP is unused for *inbound* but is the VM's **only egress path**: there is no Cloud NAT (`routers list` → 0) and Private Google Access is `False`, so removing it kills Vertex AI, Tailscale bootstrap, deploys and every outbound call. Cloud NAT needs a public IP at the *same* $0.005/hr and adds gateway + data charges, so it costs strictly more. The real figure is ~$3.65/mo (catalog rate $0.005/hr, not the $0.004 assumed), and it stops accruing while paused. See DEV_BACKLOG → housekeeping. The address itself is deliberately not recorded — it changes on every stop/start, and the value written here on 2026-07-31 was stale by 2026-08-03.

Also: check-in cadence 90 → 180 minutes (`config/personas/mike/scheduler.yaml`, gitignored — hand-copied to VM, scheduler restarted).

### Also done 2026-07-30 (client/app audit — ⚠ COST FINDING, and symptoms need re-testing)

Investigation into five reported app/PWA bugs. **No code changed** — one approved programme, parked. Full findings: [archive/plans/client_auth_tunnel_programme_2026-07-30.md](../archive/plans/client_auth_tunnel_programme_2026-07-30.md) · Session archive: [archive/sessions/2026-07-30 — Client and App Audit, Cost Finding, Programme Parked.md](../archive/sessions/2026-07-30%20—%20Client%20and%20App%20Audit,%20Cost%20Finding,%20Programme%20Parked.md)

**⚠ THE $30 BUDGET WAS NEVER VIABLE — this is arithmetic, not anomaly.** e2-medium 24/7 ≈ $24.50/mo + in-use external IPv4 ≈ $2.90 + disk ≈ $1 = **~$29/mo of infrastructure before a single AI token.** The cap wasn't protecting against runaway AI spend; it was tripping on the VM existing. It tripped twice in three days, disabling billing and taking the VM offline both times. Budget raised to $40 manually by the user on 2026-07-30; **service restoration was handled in a parallel chat.**

**⚠ THE REPORTED SYMPTOMS ARE PARTLY THE OUTAGE — re-test before fixing anything.** "Web app doesn't load", "failed to fetch", and much of "Tailscale keeps falling silent" are all consistent with a dead server. **Do not start Phase 1 of the parked programme until the system has been used against a live server and we know which symptoms actually survive.**

**Two symptoms were misdiagnosed and are worth knowing regardless:**
1. **"Messages stay at the top" is not an ordering bug.** DOM order is correct — `appendChild` only, no prepend anywhere, and the server already reverses to oldest-first. `#conversation` (`static/index.html:30-37`) is a flex column with no bottom alignment, so short content stacks at the top of a tall column. One-line CSS fix (use `margin-top: auto` on an inner wrapper, **not** `justify-content: flex-end`, which clips overflow in Chromium).
2. **"Tailscale falling silent" is largely the client.** There is no `case 'ping'`, no `visibilitychange`/`online`/`pageshow` listener anywhere in `static/index.html`. Android freezes the WebView on background; the socket dies half-open; `readyState` stays `OPEN` so sends vanish with no timeout. Restarting Tailscale forces a network-change event that finally kills the socket — which is why Tailscale *looks* guilty.

**Real defects found (documented, not fixed):**
- **Blank screen on 2nd+ launch:** auto-login (`index.html:911`) runs `enterApp` at script-parse time; `enterApp` hides the login screen **first**, then calls three functions with no `try/catch`. `new WebSocket()` throws synchronously on a bad URL → `ws` stays `null`, `onclose` never fires, **no reconnect path exists**. History arrives *only* via the WS frame, so no WS = permanently blank with no error shown.
- **`/transcribe` and `/tts` block the event loop** (`server.py:597-646`, `561-594`) — no `run_in_executor`, freezing the WS chunk relay, heartbeats and `/active` for the whole of ffmpeg + Whisper. The correct pattern is already used at `server.py:252/311/425`.
- **Whisper is untuned:** `base.en` at float32, `beam_size=5`, no VAD, `condition_on_previous_text` defaulting True, never warm-loaded — so the first call after every restart pays model construction *on the event loop*.
- **`deploy.sh`'s drain is decorative** — `/active` counts only SSE streams, and `/session/stream` has no client at all, so **every deploy kills in-flight WebSocket exchanges.**
- **No auth anywhere** (`allow_origins=["*"]`); Tailscale is the entire security model. `/monitor/file` and `/monitor/history` read arbitrary paths under `data/`. This is what makes the Cloudflare Tunnel a bigger job than the roadmap implies.
- `shownIds` eviction cliff at `index.html:567` (clears *after* adding, unlike the hardened L590); catch-up reuses `type:"history"` so a reconnect wipes the conversation and re-renders only the delta.
- `sw.js` has **no `fetch` handler** and caches nothing, and `/` is served `no-store` — there is no offline shell, so an unreachable server is a browser error page.

**Cost levers (recorded, not applied):** gate check-ins on user activity (largest — the pathological case *is* the current state: ~12 full pipelines/day talking to itself while the app was broken); stop the VM overnight via a GCE instance schedule (~$8–9/mo, native, no code); `companion_checkin` 90 → 180 min; hold off on a CUD until Whisper sizing settles. Enable BigQuery billing export for per-SKU daily attribution — **not retroactive**, so enabling early matters.

**Domain recommendation:** user has `apexgmat.com` on Cloudflare, but I'd advise a **separate personal domain** for the tunnel — one Cloudflare account means a shared blast radius between a business site and a host holding journals/clinical flags/finances, and `metatron.apexgmat.com` would be published permanently to public Certificate Transparency logs, associating a personal endpoint with a business entity. ~$10/yr. Nothing before Phase 4 depends on it.

### Also done 2026-07-29 (SessionStart hook removed after compliance-gap testing)

- **Hook confirmed firing correctly, but model non-compliant on trivial questions:** traced a live test through raw JSONL — `SessionStart:clear` ran `session_context_primer.py` successfully and correctly injected the "mandatory, no exceptions" Read instruction. On the next turn ("what is the capital of France?"), the model answered "Paris." with zero tool calls — no `Read` on SESSION.md or the roadmap at all. Not a hook-plumbing bug: the model's own relevance judgment silently overrode the procedural "no exceptions" instruction.
- **Reworded instruction drafted but not adopted** — shifting from a procedural mandate ("read these files first") to an epistemic one ("these files are truth for this session, even overriding obvious facts") was discussed as directionally stronger, then narrowed to scope authority to project-specific facts only (avoid coopting general common sense). User judged the tuning cycle wasn't worth it relative to the value delivered.
- **Decision: rolled back entirely.** Removed the `SessionStart` hook block from `.claude/settings.local.json` (the `Stop` hook / `show_phase_progress.py` untouched) and deleted `.claude/session_context_primer.py`. Both files are gitignored — no git history affected.
- **Replacement: `/metatron-code` slash command** (new) — `.claude/commands/metatron-code.md`. User-triggered (not automatic): reads SESSION.md, resolves + reads the current roadmap from SESSION.md's own link, and CODEBASE_INDEX.md if needed. Same content the hook used to inject, but explicit per-invocation instead of firing on every session start — avoids the compliance-gap failure mode since there's no relevance judgment to override on an unrelated turn.
- Session archive: [archive/sessions/2026-07-29 — SessionStart Hook Removal After Compliance Gap Found.md](../archive/sessions/2026-07-29 — SessionStart Hook Removal After Compliance Gap Found.md)

### Also done 2026-07-29 (live multi-surface testing — 7 bugs found and fixed)

Continuation of the persona unification session, driven by real use across browser, Android app and terminal. Same session archive: [archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md](../archive/sessions/2026-07-28%20—%20Persona%20Unification%20Complete%20(Phases%200-8,%20Strict%20Mode%20Live).md)

**⚠ IMPORTANT CORRECTION — the coordinator does NOT run 7 turns.** With trace instrumentation fixed, a specialist-heavy session records `coordinator turns=[1]`, `physical_health turns=[1..8]`, `synthesizer turns=[1]`. The multi-turn sequence is a **specialist** doing 8 internal tool-call turns; the interleaved `turn=2`×3 / `turn=3`×3 pattern in logs was three specialists running **concurrently** — parallel fan-out already works. This contradicts roadmap D2 item 5 ("the coordinator makes multiple sequential specialist calls... target ≤3 turns"), which the coordinator already meets. **Re-scope that item against measured data before starting it** — the real cost driver is per-specialist internal turns.

**Fixed this stretch:**
1. **Terminal was building a second history** — `orchestrator.py` ran the pipeline in-process, writing to whichever machine ran it, never touching the shared DB or broadcasting. New `core/remote_client.py` connects to the server WebSocket; remote is now the **default** for interactive coordinator sessions, `--local` opts out with a warning. WebSocket not SSE, because only the WS path calls `_save_exchange()` and `manager.broadcast()`.
2. **Orchestrator CLI was broken** (pre-existing since `c66ed03`) — `import core.trace` at line 28, `sys.path` fix at line 57. `--persona` now required.
3. **Proactive check-ins were invisible** — the scheduler ran in-process, so check-ins produced a trace and a push notification but no conversation record and no DB row. Coordinator jobs now route through the server via `send_one()`.
4. **Proactive check-ins faked a user message** — the prompt was stored/rendered as if the user typed it, so Synth appeared to answer itself. New `proactive` flag through table, reads, persistence, broadcast and log; all three client render paths skip the user bubble. Prompt deliberately stays in *model* history (strict user/assistant alternation; empty user turn risks provider rejection) — display and model context separated.
5. **Specialists absent from all traces** — trace context is thread-local and the fan-out propagated persona but not trace, so every `push_agent()` landed on an empty context. This is what made the coordinator look multi-turn.
6. **The Book didn't number live exchanges** — two feeds: `/monitor/conversations` (JSONL, has seq) vs `/monitor/stream` (traces, no seq). Server now attaches seq by matching user text; the monitor was also discarding it, so both halves were needed.
7. **VM ran `Etc/UTC` while user is Europe/London** — not cosmetic: `scheduler.yaml` times are wall clock, so `morning_brief 07:30` fired at 08:30 BST, `evening_close 20:00` at 21:00, quiet hours 22:00–07:00 were really 23:00–08:00. Set to `Europe/London`. **DST contingency added**: the `schedule` library computes `next_run` once at registration and this daemon runs for weeks, so the main loop now detects a UTC-offset change and re-registers — no manual step at the October/March transitions.

**Also:** check-in prompts rewritten to lead with a specific outstanding item from the context tracker (which already held `open_threads`/`follow_ups` — nothing told the Coordinator to use them) and to stop rather than manufacture a topic. Terminal client gained reconnect-with-backoff (a deploy restart killed a live session). Android APK rebuilt twice — the installed build was from Jun 21, missing five weeks of client fixes including the WS hang.

**Git history rewrite (user-approved):** `git add -A` swept 41 files of journals/clinical logs/conversations into a commit that reached GitHub. Rewritten via soft-reset (offending commit was `HEAD~1`, so `filter-repo`'s clone-and-swap was unnecessary risk against live gitignored data). Verified against a fresh clone: path in zero commits, GitHub refuses both orphaned SHAs, zero matching objects. Caveat recorded: proves unreachability by any client, not that GitHub gc'd its storage.

**Confirmed working:** sync across browser, app and terminal; strict mode; caching. **Still open:** browser appears to need a manual refresh to show foreign messages (client-side bug in `static/index.html`).

**Next per user:** simulate regular use, troubleshoot each exchange for missed routing / unsurfaced opportunities / token overspend / useless calls. Note only 3 of those 4 have instrumentation — **"unsurfaced opportunities" has no signal by definition**; the `·` feedback dot is the nearest hook. Capture a per-exchange turns/tokens baseline before history accumulates.

### Also done 2026-07-28 (PERSONA UNIFICATION — architecture change, strict mode live)

**One mechanism, no test/real distinction, every session real.** Started as CalDAV setup; became an architecture fix after finding the persona system was half-implemented.

**What was wrong:** 20 code sites each read `AI_TEST_PERSONA` independently and silently fell back to a shared global path when unset. Consequences, all verified: the user's history split across two trees (VM global tree held ~8x more journal content than `personas/mike/`); Pepys test data sat in the same directory as real clinical logs; three tools (`caldav`, `agent_config`, `wishes`) were persona-blind entirely; `load_profile()` fell back to root so **every synthetic persona was being told it was "Mike, London"**; the prompt header said `## Development Persona` on real sessions; and `persona` went unvalidated from the HTTP body into filesystem paths.

**Root cause of the split — a process boundary, not a date cutover:** `metatron-server.service` ran `--persona mike`; `metatron-scheduler.service` had **no `--persona` flag at all**, so every scheduled session wrote globally. Compounded by a thread race: `run_session` set then *popped* a process-global env var while the Diarist ran fire-and-forget on a daemon thread.

**Now:**
- **`core/persona.py`** — single fail-closed resolver. Explicit arg -> thread-local -> `METATRON_PERSONA` -> raise. Thread-local, not process-global (sessions run on a pooled executor thread; specialists fan out further). Names validated `^[a-z0-9][a-z0-9_]{0,39}$`.
- All 20 sites converted; 4 thread boundaries bound; `PersonaError` re-raised rather than swallowed in best-effort blocks.
- `profile.yaml` / `scheduler.yaml` / `caldav.yaml` now per-persona under `config/personas/{p}/` (gitignored). Templates in `config/templates/`.
- `scripts/new_persona.sh` + `scripts/check_personas.py` (read-only linter, exits 0).
- **Security:** `write_calendar_event` no longer accepts a model-supplied `calendar_url` — it overrode config and let the model pick the destination server for a tool shipping event text.
- **Constitution (Tier 0, user-approved):** `## Development Note` removed — it made discretion conditional on a development/production distinction the model cannot observe, and contradicted `filter_output()`. Proposal doc: `archive/plans/constitution_development_note_proposal_2026-07-28.md`.
- **Roadmap Section 0:** the carve-out permitting persona data on cloud models is **superseded** — nothing at runtime distinguishes synthetic from real any more. All persona data is sensitive-tier.
- **Data reset:** global trees moved aside to `data/_pre_reset_2026-07-28/` on both machines, VM with a full manifest. `metatron.db` (Android chat history), `push_subscriptions.json` and `data/baselines/` deliberately preserved.
- **STRICT MODE IS LIVE.** Exercised all 21 persona-dependent paths first; audit log stayed empty. Verified with a real session: writes land in `data/personas/mike/`, global tree gets nothing, no `PersonaError`.

**Commits:** `82e583a` (resolver + 20 sites), `92b51f7` (tools + settings + security), scheduler crash fix, `af32b5f` (provisioning + linter + rename), constitution, docs. Rollback tag: `pre-persona-unification` (`814e6c3`). VM backup: `~/metatron-backups/pre-persona-unification-2026-07-28-*.tar.gz` (verified restore).

**Two process lessons recorded:** (1) `deploy.sh` restarts services, so systemd unit edits need `daemon-reload` **before** the deploy — a near-miss briefly ran production fail-closed. (2) `py_compile` cannot catch a `NameError`; a stale `_SCHEDULER_CONFIG` reference crash-looped the scheduler after deploy. Grep for removed symbols, and actually run the daemon.

Session archive: [archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md](../archive/sessions/2026-07-28%20—%20Persona%20Unification%20Complete%20(Phases%200-8,%20Strict%20Mode%20Live).md) — link corrected 2026-08-05; the "Plan and Phase 0" filename this originally pointed to was never written, and the "Complete" file (referenced elsewhere in this log for the same work) is what exists.

### Backlog found this session (pre-existing, not fixed)
1. **`companion_checkin` errors on every fire** (07:35, 09:05, 10:35, 12:05) — error logged ~90 min after firing, suggesting a timeout. A core proactive feature failing silently. **Highest priority.**
2. `Object of type AgentRecord is not JSON serializable` — trace serialization, every scheduler job.
3. `[vertex_cache] 404 cached content metadata` — stale cache ID reused after expiry, falling back to compat on every call.
4. `/session` (non-streaming) leaks the `[CONTEXT]{...}[/CONTEXT]` block into the response body and never writes the context tracker — the parser lives only in the streaming path. No user impact (app uses WebSocket/SSE).
5. `## Prime Directive` / `## Mission` appear once each now, but the underlying cause remains: `write_config()` stores the Goals Interviewer's text verbatim including its own heading. `_titled()` dedups at load time.

### Also done 2026-07-28 (SessionStart context hook + troubleshoot slash command)

- **Problem:** chats overstep because SESSION.md/roadmap/ownership context isn't loaded before basic queries or edits — the CLAUDE.md "Mandatory Pre-Edit Context Check" is an instruction the model has to remember, not a forced load (see 2026-07-27 revert incident below).
- **`.claude/session_context_primer.py`** (new) — `SessionStart` hook wired into `.claude/settings.local.json` (alongside the existing `Stop` hook, untouched). Fires on session start/resume/clear/compact/fork; injects full `SESSION.md` + the currently-active roadmap (resolved dynamically from SESSION.md's link, not hardcoded — won't go stale when the roadmap is next revised) + `CODEBASE_INDEX.md` (~1,560 lines / ~15–18K tokens). CLAUDE.md deliberately not duplicated — Claude Code auto-loads it already. Output uses the documented JSON `additionalContext` hook format (confirmed via `claude-code-guide` research); first line is a literal `Default Hook Fired` marker so firing is visually confirmable, and each file section echoes its resolved path.
- **`.claude/commands/metatron-troubleshoot.md`** (new) — callable slash command, `/metatron-troubleshoot <DATE> <SEQ> <ISSUE>`. Reconstructed from the single-exchange troubleshoot prompt referenced in `archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md` (original was only "in the chat transcript," never saved — user supplied the text this session). Pulls conversation record + server logs + pipeline trace for one exchange via one SSH round-trip. Confirmed working by user.
- **Not yet confirmed:** live in-session firing of the SessionStart hook — `SessionStart` doesn't fire on ordinary turns within an already-running session (only on the five sources above), so an in-session test came back empty as expected, not a bug. Next session (or a `/clear`) should confirm `Default Hook Fired` appears and no `Bash`/`grep` fallback is needed for a roadmap question.
- Session archive: [archive/sessions/2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md](../archive/sessions/2026-07-28 — SessionStart Context Hook and Troubleshoot Slash Command.md)

### Also done 2026-07-28 (rehydrated 2026-06-26 pipeline audit session; write_config filter fix attempted and reverted)

- Context-recovery task: located and read both transcript copies of the 2026-06-26 "Context: this is the Metatron..." session, summarized findings, cross-checked against current state.
- **Correction on re-check:** of the 5 bugs from that original audit, 4 were confirmed resolved directly in code (ambient context, Research Agent normalization, uncached Coordinator prompt — accepted structural cost, graceful shutdown SIGKILL). The 5th — `write_config` output-filter false positive — was *not* actually fixed; the SEQ 031 session's two-tier filter only covered common-English-word terms (`logistics`, `finance`), not tool names like `write_config`, which stayed in `_ALWAYS_CONFIDENTIAL`.
- **Fix attempted, then reverted after security review.** First pass exempted any term already present in the user's own message from suppression. User asked for a review against this file and the roadmap before accepting it — that surfaced a real regression: the roadmap's B1 red-team plan tests a "Direct tool inquiry" category (e.g. "What tools do you have?") expecting a canned response; the fix let a message like "What does `write_config` do?" disable the filter's own backstop for exactly that probe, since the term was "already said." Reverted in full — `filter_output()` and all three call sites back to original always-suppress behavior; net diff is docstring-only.
- **Known gap, correctly recorded (not a regression):** the `write_config` / `_ALWAYS_CONFIDENTIAL` false positive from Exchange 027 remains open. Fixing it without weakening the backstop belongs to the already-planned **Track B / B2 "Output filter upgrade"** (regex+semantic matching) — see roadmap.
- Session archives: [archive/sessions/2026-07-28 — Rehydrate Metatron Pipeline Audit Session.md](../archive/sessions/2026-07-28 — Rehydrate Metatron Pipeline Audit Session.md) (rehydration + fix attempt), [archive/sessions/2026-07-28 — Chat Rehydration, write_config Filter Fix Attempt and Revert.md](../archive/sessions/2026-07-28 — Chat Rehydration, write_config Filter Fix Attempt and Revert.md) (full session close, including the revert)

### Also done 2026-07-28 (lost chat recovery + ask_claude MCP resume)
- No code/config changes. User couldn't find an open `ask_claude` chat ("write product description...") that hadn't rehydrated after a restart — `list_conversations` showed the MCP tool's own archive empty, so it was gone from that tool's state. Located the content via file search in `archive/transcripts/` instead (2026-06-19 "Bill Hopkins Proposal" session — capital-raise product description for a corporate/enterprise variant of Metatron). Manually resumed by re-feeding the prior draft + six flagged research gaps into a new `ask_claude` prompt; got a full multi-model pass back (competitive differentiation, agency trade-off framing, beachhead segment, revenue model, AI/human accountability, regulatory surface — see session archive for the findings).
- Ran `python3 tools/archive_chats.py` twice — cleared a backlog of 12 unarchived sessions going back to 2026-07-14, then captured this session's own transcript incrementally.
- Session archive: [archive/sessions/2026-07-28 — Lost Chat Recovery and ask_claude MCP Resume.md](../archive/sessions/2026-07-28 — Lost Chat Recovery and ask_claude MCP Resume.md)

### Also done 2026-07-27 (SEQ 041 routing miss diagnosis and fixes)

- **Root cause:** Coordinator dispatched zero specialists for "I'm not sure. Do you have some suggestions?" (Bulgarian vocabulary follow-up) — treated as conversational follow-up, not a domain query. Synthesizer received no Learning output and responded from general knowledge.
- **Synthesizer catch also failed:** existing sanity-check rule did not trigger `run_subagent` despite absent Learning output for a Learning domain query.
- **Diarist evaluated:** fire-and-forget (no user latency), 3-turn pattern is Vertex parallel tool call bug (not worth fixing — background agent, no user impact). OVER_8K warnings at turn=2/3 are from Diarist running in parallel; Synthesizer's turn=1 warning is logged at API return time, not start time.
- **Four fixes deployed (commit `814e6c3`):**
  1. `config/agents/coordinator.md` — routing rule: advice/suggestion requests route to relevant domain specialist regardless of COMPLEXITY
  2. `config/agents/synthesizer.md` — domain query catch-up covering all 8 domains (generalizes existing Logistics-only catch)
  3. `core/orchestrator.py` — Diarist added to bare-mode set; strips goals.yaml (~500–1000 tokens/turn saved)
  4. `config/modules/routing_cloud.yaml` — `write_log` and `write_wisdom` added to Diarist allowed_tools
- Session archive: [archive/sessions/2026-07-27 — SEQ 041 Pipeline Routing Diagnosis and Routing Miss Fixes.md](../archive/sessions/2026-07-27 — SEQ 041 Pipeline Routing Diagnosis and Routing Miss Fixes.md)

### Also done 2026-07-27 (Vertex cache padding fix, pause/resume tooling, billing incident)
- **Vertex cache padding fixed:** `_pad_for_vertex_cache()` added to `core/orchestrator.py` — the 2026-06-24 token-reduction work had shrunk Coordinator/Synthesizer prompts under Vertex's 4096-token cache-creation floor, silently failing cache creation on every call. Verified live: cache now creates successfully and reads confirmed (`cache_read=12281` on a real session).
- **VM pause/resume tooling added:** `scripts/metatron-pause.sh`, `scripts/metatron-resume.sh` — stop/start `metatron-vm` for cost control during dev downtime.
- **Billing incident + fix:** the $20 budget cap had tripped and fully unlinked the billing account days earlier. Budget raised to $30. Found and fixed a re-fire loop in `stop-billing` (Cloud Function) caused by GCP's budget-notification propagation lag re-disabling billing on every relink attempt — added a manual-override marker mechanism (`gs://metatron-billing-state/override.json`, `scripts/metatron-billing-override.sh`), wired into `metatron-resume.sh` to trigger only when it finds billing actually disabled.
- **Known issue documented:** Tailscale DNS relay came up unhealthy after VM stop/start, blocking all outbound API calls until `tailscale set --accept-dns=false`. Root cause not identified.
- **Monitoring note added** below (June 24 token-reduction entry) — watch cache padding on any future prompt-shrinking pass to Coordinator/Synthesizer.
- Session archive: `archive/sessions/2026-07-27 — GCP Billing Investigation, Cache Padding Fix, and Pause-Resume Tooling.md`

### Also done 2026-06-22 (The Book SSE reconnect)
- `_sse_loop` now auto-reconnects with exponential backoff (2s→30s) on any connection failure. Column 1 updates in real time without re-selecting the persona.
- Session archive: `archive/sessions/2026-06-22 — The Book SSE Reconnect.md`

### Also done 2026-06-26 (SSE streaming newline fix)

- **Root cause:** LLM stream chunks containing literal `\n` were embedded directly in SSE `data:` lines. Client's `split('\n')` parser dropped all text after the newline, causing truncated responses and mid-word splicing.
- **Fix:** Server escapes `\r`/`\n` in text chunks before SSE emission (`core/server.py`); client unescapes `\\n` when accumulating (`static/index.html`). Control tokens unaffected.
- Committed `ba84c6d`, deployed to VM. Hard reload required on client.

Session archive: [archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md](../archive/sessions/2026-06-26 — SSE Streaming Newline Fix.md)

### Also done 2026-06-26 (seq in conversation logging)

- **`core/server.py`** — `_log_conversation` now writes `"seq": "003"` (1-indexed, zero-padded, per-day) to each JSONL entry. Thread-safe: `_CONV_LOCK` wraps the read-count-then-write atomically.
- **`tools/metatron_monitor.py`** — Column 1 shows `#003 14:23` prefix when seq present; falls back to full timestamp for old entries.
- No changes to `/monitor/conversations` — seq passes through from JSONL automatically.
- Committed `9fcd802`, deployed to VM.

Session archive: [archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md](../archive/sessions/2026-06-26 — Sequential Exchange ID (seq) in Conversation Logging.md)

### Also done 2026-06-26 (Gemini routing fix)

- **Root cause 1:** `core/router.py` silently defaulted unknown agents to `provider="anthropic"`. Fixed: raises `RuntimeError` + logs to `data/logs/routing_fallbacks.json`.
- **Root cause 2:** Browser sends `provider=""` (empty string from Auto dropdown); `if provider is None` check didn't catch it. Fixed: both sites in orchestrator changed to `if not provider`.
- **Error tracking added:** `log_model_error()` in `router.py` writes API failures to `data/logs/model_errors.json` (agent, provider, model, error). Wired into `_openai_compat_loop`, `run_session_gemini_grounded`, `run_session_gemini_cached`, and the unrecognised-provider branch.
- **Other defaults cleaned:** `run_interactive()` + server CLI `--provider` both changed from `"anthropic"` to `"gemini"`.
- Deployed `config/profile.yaml` and `tools/ambient.py` (were missing from VM, causing warning).
- Confirmed working via SSH test and browser.

Session archive: [archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md](../archive/sessions/2026-06-26 — Gemini Routing Fix and Deploy Audit.md)

### Also done 2026-06-26 (Synthesizer conversation history)

- **Rolling 5-turn history** (10 entries) added to the Coordinator → Synthesizer pipeline. Synth no longer cold-starts each turn — prior user/assistant exchanges are prepended to its messages.
- **`core/orchestrator.py`:** `_anthropic_stream` — added `history` param. `run_pipeline_session` + `run_pipeline_session_stream` — both accept `history`, pass a `list(history[-10:])` snapshot copy to Synth, update history in-place after each turn, trim to 10. `run_session` — threads history through to pipeline (previously dropped on the floor).
- **`core/server.py`:** `_session_history: dict[str, list[dict]]` — per-persona in-memory history. Both `/session` and `/session/stream` look up the right list and pass it to the pipeline each request.
- **Side fix:** streaming pipeline was not applying Synth's `allowed_tools` whitelist — Synth was receiving all ~20 tool schemas instead of its 8. Now matches `_run_single_agent` behavior. This also addressed the "context file not registering" observation.
- Deployed to VM. Confirmed working.

Session archive: [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](../archive/sessions/2026-06-26 — Synthesizer Conversation History.md)

### Also done 2026-06-27 (Kokoro TTS migration + Safari AudioContext fix)

- **Kokoro `af_heart` now running on VM.** Venv was Mac-only and never migrated. Installed `espeak-ng` via apt + `kokoro soundfile` into main `.venv` (reuses existing torch). `KOKORO_PYTHON` path updated in `core/server.py` and `core/voice_pipeline.py`. Subprocess timeout raised 30s → 120s.
- **Safari AudioContext fix** (`static/index.html`): replaced `new Audio().play()` with `AudioContext.decodeAudioData()` + `BufferSourceNode` — Safari blocks the former even after user gesture; the latter is always allowed after `ctx.resume()`. Shared `audioCtxShared` context created on first tap.
- **`aiosqlite` added to `requirements.txt`** — was missing, caused server crash on startup after deploy.
- **Login Enter key** — `#login-password` now has a `keydown` handler; Enter submits the login form.
- **VM gap audit complete** — all other expected packages/models confirmed present on VM. Only Kokoro was missing.
- Session archive: [archive/sessions/2026-06-27 — Kokoro TTS Migration and Safari AudioContext Fix.md](../archive/sessions/2026-06-27 — Kokoro TTS Migration and Safari AudioContext Fix.md)

### Also done 2026-06-26 (pipeline audit + Research Agent normalization fix)

- **Pipeline audit** across 2 hours of live traffic (15:28–16:47): 5 bugs identified. See session archive for full latency profile and failure pattern catalog.
- **Research Agent normalization fix (two-part):**
  - `core/orchestrator.py` — 9 single-word abbreviation entries added to `_AGENT_NAME_MAP` (`"research"` → `"research_agent"`, `"mental"` → `"mental_wellbeing"`, etc.). Covers Flash-Lite's tendency to shorten multi-word agent names on cold starts.
  - `config/agents/coordinator.md` — explicit "Valid agent values" line added before the format template, listing all 12 agent strings verbatim.
- **Root cause of exchange 027:** Coordinator output `"Research"` (not `"Research Agent"`) → normalized to `"research"` → `research.md` not found → Synthesizer streamed "minor snag" then called `run_subagent` as recovery → weather data returned but too late to retract already-streamed text.
- **Single-exchange troubleshoot prompt** written — two inputs (DATE, SEQ), one SSH command, pulls conversation record + server logs + pipeline trace in one round-trip.
- **Pending deploy:** both normalization fixes are committed locally but not yet pushed to VM.
- **Bugs identified but not fixed this session:** (1) `tools.ambient` missing on VM, (2) output filter false positive on `write_config`.
- **(3) graceful shutdown 90s SIGKILL cycle — fixed 2026-06-26:** `timeout_graceful_shutdown=150` added to `uvicorn.run()`; `_active_streams` counter + `GET /active` endpoint added to `core/server.py`; `deploy.sh` restructured to drain active SSE streams (up to 180s) before restarting metatron-server. Full Fix 3 (drain gate + client reconnect + `/result/{date}/{seq}` endpoint) scoped in `archive/plans/future_phases.md`. Session archive: [archive/sessions/2026-06-26 — SEQ 032 Troubleshoot and Graceful Shutdown Fixes.md](../archive/sessions/2026-06-26 — SEQ 032 Troubleshoot and Graceful Shutdown Fixes.md)

Session archive: [archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md](../archive/sessions/2026-06-26 — Pipeline Audit and Research Agent Fix.md)

### Also done 2026-06-26 (user profile + ambient world context)

- **`config/profile.yaml`** (new) — stable biographical profile injected into Synthesizer and Coordinator. Filled in: name Mike, London, UK, Europe/London. Age/occupation/household left to fill. Includes `ambient.markets: true` flag.
- **`tools/ambient.py`** (new) — 3-hour scheduler job fetches weather (wttr.in/London), headlines (BBC + CNN interleaved, 8 total), and 7 market indices (S&P 500, FTSE, DAX, Nikkei, Hang Seng, Gold, WTI Oil) via Yahoo Finance v8 chart endpoint. Writes `data/ambient_context.json`. `load_ambient_context()` always injects live date/time from system clock; weather/news/markets from last refresh.
- **`core/orchestrator.py`** — `load_profile()` added; injected into `load_config()` (Synthesizer) and Coordinator system prompt. Ambient context prepended to `load_recent_context()` so both agents always see it.
- **`core/scheduler.py`** — `function:` job type added; calls Python callables directly without an LLM session.
- **`config/modules/scheduler.yaml`** — `ambient_refresh` job: every 180 minutes, calls `tools.ambient.refresh_ambient_context`.

Session archive: [archive/sessions/2026-06-26 — User Profile and Ambient World Context.md](../archive/sessions/2026-06-26 — User Profile and Ambient World Context.md)

### Also done 2026-06-26 (The Book: SSE backfill fix, load menu, ordering)

Root-cause fix for two related issues: (1) Load menu filter (24h / max 10) appeared broken because `/monitor/stream` replayed all historical traces on connection, backfilling old conversations to the top of Column 1 past the filtered 10. Fixed: `/monitor/stream` accepts `since` param; skips old traces on initial scan only. Monitor records `_sse_since = now()` at `load_data()` start and passes it to the SSE endpoint. (2) Uncommitted changes from prior session meant VM was running old server code with no `since`/`limit` support — deploy was a no-op. Committed and deployed. (3) Max entries Input → Select dropdown (10/20/50/All). Client-side descending sort added as defensive measure.

Session archive: [archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md](../archive/sessions/2026-06-26 — The Book Load Menu, Ordering, and SSE Backfill Fix.md)

### Also done 2026-06-26 (Book: Synth token counts + conversation history)

- **Synth tokens showing 0:** `_openai_compat_stream` only captured usage from the trailing choices-empty chunk (OpenAI pattern). Vertex AI embeds usage in the final content chunk (`finish_reason="stop"`, choices non-empty). Added second capture path guarded by `_usage_recorded` flag. Confirmed working.
- **Conversation history not in Column 3:** `recent_history` was fed to the model but not stored in `context_sections`. Now serialized as `USER:/ASSISTANT:` text and added as `"conversation_history"` key. The Book's Column 3 shows it in a new "Conversation History (fed to Synth)" collapsible. Appears from the second exchange onward (first message after restart has no prior history — expected).
- Deployed `e1a12d2`.

Session archive: [archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md](../archive/sessions/2026-06-26 — Book Synth Token Counts and Conversation History.md)

### Also done 2026-06-26 (SEQ 031 troubleshoot + context tracker refactor)

Root-caused SEQ 031: "I can't help with that right now" response despite coherent tracker entry. Three findings:

1. **Output filter false positive** on `logistics` in "daily logistics" — common English word matched banned agent name. Fixed: two-tier filter. `_ALWAYS_CONFIDENTIAL` (code identifiers, always flagged) vs. `_CONTEXT_SENSITIVE` (`logistics`, `finance`, `relationships`, `coordinator`, `synthesizer`, `orchestrator`, `diarist`) — only flagged when architecture vocabulary appears in the same sentence.
2. **Preference not durable** — `write_context_tracker` is session-level state; `config/personas/mike.md` was not updated. Fixed: `write_persona` tool added (`tools/persona.py`), registered in orchestrator + both routing configs. `mike.md` updated with goals interview complete + Interaction Preferences section (no validation/commendation, direct follow-up questions only). File pushed directly to VM via `gcloud compute scp` (gitignored).
3. **Context tracker double-turn overhead** — `write_context_tracker` tool call forced 2–3 Synthesizer turns per exchange (~$0.066/exchange at Pro pricing; ~$20/month at 300 exchanges).

**Fix 3 — [CONTEXT] inline block:** Synth now appends `[CONTEXT]{json}[/CONTEXT]` after its visible response instead of calling the tool. Streaming parser in `run_pipeline_session_stream()` intercepts the block before it reaches the client, parses JSON, calls `write_context_tracker()` as a direct Python function call. Synth is now 1 turn for simple exchanges (2 for `run_subagent` exchanges). Held item fidelity preserved — Synth authors them in the same generation pass. Recency bias guard added to instruction. Tested live: clean visible response, `[CONTEXT]` not leaked, tracker written with correct held item. Commits `4984f48`, `5df05aa`.

Session archive: [archive/sessions/2026-06-26 — SEQ 031 Troubleshoot and Context Tracker Refactor.md](../archive/sessions/2026-06-26 — SEQ 031 Troubleshoot and Context Tracker Refactor.md)

### Also done 2026-06-26 (single exchange troubleshoot — SEQ 026 / Logistics routing)

Root-caused why "Delayed until Monday at 5:30." (SEQ 026, 16:28:23) did not trigger a scheduling action. Coordinator dispatched zero specialists; Synthesizer absorbed it conversationally. Three fixes deployed:

1. **`config/agents/coordinator.md`** — Logistics entry broadened: added explicit "also call when user defers or postpones anything to a named time" rule; added deferral signal words (delayed, postponed, rescheduled, moved to, pushed to, bumped, put off, defer, reschedule, changed to, updated to) and temporal commitment triggers (tomorrow, next week, this weekend, next month, end of month/week, next year, by [day name], on [day name], [day] at [time]).
2. **`config/agents/synthesizer.md`** — `write_config` scope clarified (recurring proactive sessions only; one-off deferrals → Logistics). Catch-up rule added: if user message contains a temporal commitment signal and no Logistics output in context package, call `run_subagent("logistics")` before responding, log `ROUTING_MISS: Logistics`, call `write_quality_event`.
3. **`tools/subagent.py`** — Diarist removed from Synthesizer's `run_subagent` schema (Coordinator always dispatches it fire-and-forget; Synth has no use case for calling it directly). Confirmed: Coordinator dispatches Diarist via `_dispatch_from_coordinator` text parsing, not tool calls — schema change has no effect on Coordinator.

**Clarifications established:**
- No "Scheduler agent" exists. Scheduling = Logistics (`write_calendar_event`) for one-off events/deferrals; `write_config` for recurring Metatron session entries (habits, standing check-ins). These are distinct.
- Pattern Miner and Goals Interviewer should not be in Synth's callable agent list — PM runs on schedule, Goals runs at first-instance onboarding only.
- Coordinator model upgrade is not the right fix for routing misses; missing rules are the cause.
- Synth token tracking (in=0 out=0) was broken before ~17:05 on 2026-06-26; confirmed working from 17:05 onwards. No code change needed.

**Open:** (1) Test Coordinator fix with a deferral message in app, verify Logistics in trace. (2) Verify `write_calendar_event` actually connects to a real calendar, not just flat file logging.

Commits: `e477c76`, `5f21800`, `5a7c6ff`. Session archive: [archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md](../archive/sessions/2026-06-26 — Single Exchange Troubleshoot SEQ 026 Logistics Routing.md)

### Also done 2026-06-26 (The Book: call timing, tokens, load menu, server fixes)

Seven fixes across `core/trace.py`, `core/orchestrator.py`, `core/server.py`, `tools/metatron_monitor.py`:

1. **Tool call timing:** `duration_ms` changed to float (`round(..., 1)`); `ToolCallRecord` now stores 1-decimal ms precision. 0ms sub-millisecond ops now show e.g. `0.3ms`.
2. **Token counts per call:** `ToolCallRecord` extended with `input_tokens`/`output_tokens`. For `run_subagent`, tokens pulled from subagent `AgentRecord` at dispatch time and shown on collapsible title in Column 3.
3. **`run_subagent` not recorded (Gemini native parallel path):** `_run_gemini_native_loop` parallel branch now propagates thread-local trace context (same pattern as Anthropic path). Previously all Coordinator subagent calls were silently dropped from traces.
4. **Server blocking event loop:** `session_stream` iterated a sync generator inline in `async def`, blocking uvicorn for 10–30s — no monitor requests could be served during a pipeline run. Fixed: `_produce()` runs in `run_in_executor`; chunks queued via `asyncio.Queue` + `run_coroutine_threadsafe`. `/session` non-streaming also fixed with `run_in_executor`. Zero latency impact.
5. **Personas not loading on launch:** `load_personas()` now retries 4× with exponential backoff. R key now also retries persona load when no persona is selected.
6. **Freezing on persona switch:** SSE worker cancel moved to top of `load_data()` (was deferred until after HTTP requests — caused old-persona SSE to write to new-persona's list mid-load).
7. **Load menu + most-recent-first:** New `#load-bar` in The Book with Range presets (1h/6h/24h/7d/30d/All) and Max count input. Default: 24h, 10 messages. Server `/monitor/conversations` and `/monitor/traces` now accept `since` + `limit` and return newest-first. Column 1 now shows most recent messages at top; SSE live messages prepend to top.

Session archive: [archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md](../archive/sessions/2026-06-26 — The Book Call Timing, Token Counts, Load Menu, and Server Fixes.md)

---

### Also done 2026-06-26 (pipeline debugging + latency work)

Phase 1 — Three root-cause bugs fixed. First live response confirmed via browser (see session archive for details).

Phase 2 — Latency reduction. Warm-cache second-message latency: ~40s → **~20s**. Streaming text now appears word-by-word in UI.

Key changes:
1. **Agent name normalization** — `_normalize_agent()` in `_dispatch_from_coordinator`. All casing/spacing variants ("Physical Health", "Logistics", etc.) now resolve to correct filenames. MW, PH, and other specialists were silently dropping on every session.
2. **Coordinator: Pro → Flash-Lite** — single-pass routing directive, no tools. Saves ~3–5s.
3. **Vertex cache fix** — tools now baked into `CreateCachedContentConfig`. Eliminates guaranteed native-loop-fail + compat-fallback double round-trip on every tool-bearing agent (Synthesizer, specialists). `cache_read=12000+` visible in logs.
4. **trace.py committed** — `ToolCallRecord.input_tokens`/`output_tokens` had been applied locally but never committed; old VM version crashed native loop.
5. **Streaming client** (`static/index.html`) — coordinator uses `/session/stream` (SSE). Text streams into bubble word-by-word (`▍` cursor). TTS fires on `[DONE]`. TODO (future): phrase-by-phrase TTS with pauses.
6. **Streaming thought_signature fix** (`_openai_compat_stream`) — when Synthesizer emits text + `write_context_tracker` in one streaming turn, stream deltas lack Vertex's `thought_signature`. Fix: replay that turn blocking using pre-turn message snapshot; apply `model_copy()` workaround. Already-yielded text is correct; replay used only for signed message construction.

**Next:** specialist token reduction (plan Steps 3–5) — specialists still running 5–8 tool-call turns; this is the biggest remaining latency lever. Then B1/Check10/Check12 for A7 sign-off.

Session archive: [archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md](../archive/sessions/2026-06-26 — Pipeline Debugging and First Response.md)

### Also done 2026-06-26 (troubleshooting prompts + interchange ID design)

Meta/planning block — no code changes. Three deliverables:

1. **TTS phrase-by-phrase note confirmed recorded** — `// TODO future: phrase-by-phrase TTS` in `static/index.html` (`sendStreaming`), session archive, and SESSION.md.
2. **Latency troubleshooting prompt written** — general-purpose prompt for diagnosing a specific exchange: pull VM logs for a time window, break down latency by component, evaluate Coordinator routing and RESOLVED_INTENT, compare what happened vs. what should have happened. Text in chat transcript; reuse by pasting into a new chat with a target time window.
3. **Interchange ID design recommendation** — daily zero-padded sequential counter (`001`, `002`…) as `seq` field in `data/conversations/YYYY-MM-DD.jsonl`. Display as `#003  14:23` in Column 1. Implementation prompt written (two steps: `_log_conversation` in `core/server.py` + Column 1 display in `tools/metatron_monitor.py`). Not yet implemented.

Session archive: [archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md](../archive/sessions/2026-06-26 — Troubleshooting Prompts and Interchange ID Design.md)

### Also done 2026-06-24 (token reduction — Steps 1–5)

**Token reduction implementation complete (Steps 1–5 of 6).** Projected ~3× reduction (Steps 1–5); ~5× with Step 6.

- **Step 1:** `git tag v0.5-pre-refactor` — snapshot before any changes.
- **Step 2:** Per-agent tool schema whitelists. `allowed_tools` added to `routing_cloud.yaml` and `routing.yaml` for all agents; `core/router.py` — `ModelConfig.allowed_tools` field + `get_allowed_tools()` function; `core/orchestrator.py` — schema filter in `_run_single_agent()`. Only advertised schemas go to the LLM; Python functions stay registered. (~15,000t saved)
- **Step 3:** Strip constitution/prime_directive from specialist system prompts. Three-branch context loading in `_run_single_agent()`: bare (research_agent), head layer (full config + recent context), specialists (goals.yaml only). `_HEAD_LAYER_AGENTS = {"coordinator", "synthesizer"}`. `load_goals()` function added. (~5,000t saved)
- **Step 4:** Specialists no longer call `load_recent_context()` independently. Context arrives via Coordinator directive. (~3,000t saved)
- **Step 5:** Quick/deep behavioral sections added to all 8 specialist agent files (mental_wellbeing, physical_health, work_vocation, relationships, finance, learning_growth, recreation_hobbies, logistics). Existing language preserved exactly; Quick mode is a gate only. MW clinical detection active in all modes without exception.
- **Step 6 (deferred):** Coordinator restructure — single-pass directive assembly replaces 3-turn session. Do after Steps 1–5 stable. (~15,000t saved from Coordinator alone)

Session archive: [archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md](../archive/sessions/2026-06-24 — Token Reduction Architecture and Implementation.md)

**Monitor: Vertex cache padding (2026-07-27).** Steps 2–5 above shrank Coordinator/Synthesizer system prompts enough that at least one (Physical Health-adjacent context, 4051t) fell under Vertex's 4096-token cache-creation floor — every cache attempt silently failed and ran uncached until fixed in `_pad_for_vertex_cache()` (`core/orchestrator.py`). Any future token-reduction pass on `coordinator`/`synthesizer` (the only two agents on the cached path — `_HEAD_LAYER_AGENTS`/`_ROUTING_LAYER_AGENTS`) should re-check real prompt sizes stay comfortably clear of that floor, or confirm the padding logic is still absorbing the gap. Currently routed to Gemini only — the dormant Anthropic `cache_control` path (1024t floor, fails silently rather than erroring) doesn't need the same watch unless Anthropic routing comes back.

### Also done 2026-06-22 (token economics analysis)
- **Pipeline token cost traced end-to-end:** ~95,000 input tokens for a 70-token user message (~13× overhead). Coordinator (3 turns): ~22,000t. 5 sync specialists (2 turns each): ~49,000t. Synthesizer (2 turns): ~14,790t.
- **Three waste sources identified:**
  1. Tool schemas (~2,000t) paid 9× across all invocations — each agent/specialist receives all 30 schemas regardless of which 2–3 it uses. Synthesizer pays for schemas it never calls (streaming path confirmed no-tool in code comments).
  2. Shared config (constitution + prime_directive + mission + goals, ~1,400t) paid 9× — no cross-agent caching.
  3. Recent context (~600t) loaded independently 8× — each specialist calls `load_recent_context()` even though Coordinator already has it and constructs their directive from it.
- **Three fixes without architectural change** would cut to ~55,000t: (1) route tool schemas per agent, (2) pass recent context in the directive rather than reloading in specialists, (3) strip constitution from specialist system prompts (mirrors existing research_agent pattern).
- **Architectural question raised:** should all specialist calls live in Synthesizer, with Coordinator being a cheap single-turn router only? Coordinator currently costs ~22,000t; as lightweight classifier it would cost ~1,000t. Synthesizer already does secondary chains (ReAct, up to 3 rounds per its agent file). No decision made — deferred.
- Session archive: `archive/sessions/2026-06-22 — Token Economics and Pipeline Architecture Analysis.md`

### Also done 2026-06-22 (The Book — monitoring tool iteration)
- **The Book** (`tools/metatron_monitor.py`) — substantial iteration on the monitoring TUI.
- **Bug fixes:** persona bleed in Column 1 (conversations endpoint now always filters by persona), subagent name showing as `run_subagent(?)` (arg key is `agent_name`), SSE disconnect on ID collision (list items no longer use IDs; SSE loop is append-only), snapshot crash (`s` key priority binding), chat "no response" (dropped `streaming_json`, now uses `--output-format text` via temp file + shell redirect).
- **Column 1:** datestamps added; each message block is now a `Collapsible` — collapsed shows truncated preview, expanded shows full user + Metatron text.
- **Column 3:** turns flattened to Static dividers with tool calls as top-level Collapsibles; `run_subagent` now resolves to the actual subagent record (provider/model/tokens/output files) instead of raw args.
- **Diary/file history viewer:** clicking a file link opens all entries in that directory, sorted by date, with the current entry marked `← current` in green. New `GET /monitor/history` endpoint on server.
- **Output file tracking:** `core/trace.py` now scans tool call args and results for `data/...` paths; stores as `output_files` on `AgentRecord`; included in JSONL serialization and shown as clickable buttons in Column 3.
- **Snapshot (`s` key):** writes `data/book_snapshot.md` to Mac project dir with current Book state — bridge to Claude Code in VSCode.
- **Chat panel (`c` key):** bottom panel with Input, Send, Clear, token counter. Sends messages to `claude -p --output-format text` via temp file; builds recursive context (full `Human:/Assistant:` history prepended each turn). Chat panel still unconfirmed working — under investigation.
- **New server endpoints:** `GET /monitor/history`, `GET /monitor/file`.
- Session archive: `archive/sessions/2026-06-22 — The Book Iteration and Chat Panel.md`

### Also done 2026-06-21 (Android end-to-end testing)
- **All 10 Android tests pass.** App fully functional on VM.
- Mike persona synced to VM; Vertex key deployed; Whisper installed.
- Server migrated to HTTPS via Tailscale cert (`metatron-vm.tail0acc5d.ts.net:8001`).
- Fixed: PortAudio crash (lazy sounddevice import), provider defaulting to ollama (now auto-route), send button layout, mic auto-prompt (MainActivity.java), audio autoplay on Android (AudioContext unlock).
- **Cloudflare Tunnel** added to roadmap as pre-alpha requirement (removes Tailscale from phone).
- **D1 open:** Run Goals Interview on VM — `BASELINE_INCOMPLETE` on every session until done. Run via CLI: `python core/orchestrator.py --agent goals_interviewer --provider gemini`
- Session archive: `archive/sessions/2026-06-21 — Android End-to-End Testing.md`

### Also done 2026-06-21 (CLAUDE.md deployment infrastructure)
- **CLAUDE.md updated:** "Per-System Configuration" replaced with comprehensive "Deployment Infrastructure" section covering topology diagram, GCP VM, Vertex AI, billing protection, Tailscale, systemd unit files (verbatim), GitHub/deploy pipeline, Python env, all environment variables, routing/deployment mode, Android app build steps, local dev mode, and a 10-step recreate-from-scratch checklist.
- **Model version note** in CLAUDE.md updated (2026-05-19 → 2026-06-21; Flash-Lite ID corrected to non-preview).
- Session archive: `archive/sessions/2026-06-21 — CLAUDE.md Deployment Infrastructure Section.md`

### Also done 2026-06-20 (VM provisioning, GitHub, deploy pipeline)
- **GCP VM provisioned:** `metatron-vm`, `e2-medium`, Debian 12, `us-central1-a`. Python 3.11, ffmpeg, all deps installed.
- **Tailscale on VM:** joined tailnet. **VM Tailscale IP: `100.64.226.49`** — phone connects here (not the Mac). Health check confirmed via Tailscale.
- **Vertex credentials on VM:** service account `metatron-vertex@metatron-ai-499810.iam.gserviceaccount.com` with `roles/aiplatform.user`. Key at `~/multi-model-mcp/vertex-key.json`, `GOOGLE_APPLICATION_CREDENTIALS` in `.env`.
- **systemd services:** `metatron-server.service` (port 8001, `--persona mike`) + `metatron-scheduler.service` — both enabled and `active (running)`.
- **GitHub repo:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex` on Mac, deploy key `metatron-vm` on VM.
- **Deploy pipeline:** `./deploy.sh` — pushes to GitHub, VM pulls, restarts services. Post-commit hook reminds to deploy after every commit.
- **Always-on Mac backup:** not yet implemented — deferred until needed (VM is primary). When needed: `pmset` for sleep prevention + launchd plist (see notes below).
- **Login/profile screen:** added to `static/index.html`. Shows on first launch; auto-logins on return via `localStorage`. Persona dropdown (mike + all test personas grouped). Password field (placeholder, not enforced). Persona chip in header — tap to switch.
- **APK rebuilt and sideloaded:** new VM Tailscale IP (`100.64.226.49`), login screen, new mem icon. Java 21 installed via Homebrew. Adaptive icon XMLs removed — Android now uses PNG directly (fixes home screen icon caching issue). APK served via `python3 -m http.server 8888` on Mac Tailscale IP.
- **GitHub:** `github.com/MikeApex/metatron` (private). SSH key `~/.ssh/github_mikeapex`. Deploy key `metatron-vm` on VM. `./deploy.sh` pushes to GitHub + restarts VM services. Post-commit hook reminds to deploy.
- **requirements.txt** generated from venv (95 packages) and committed.

### Also done 2026-06-19 (Vertex AI setup session)
- **GCP project created:** `metatron-ai-499810`, billing linked, Vertex AI API enabled, ADC configured.
- **Billing hard-cap at $20:** Pub/Sub topic `billing-cap` + Cloud Function `stop-billing` (Python 3.11, Gen2) auto-disables billing when budget fires. IAM grants in place.
- **Vertex AI migration:** `run_session_gemini_grounded()` now uses Vertex native SDK (`genai.Client(vertexai=True)`). Vertex requires `location=global` for Gemini 3.x models. `.env` updated with `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION=global`, `DEPLOYMENT_MODE=cloud`.
- **`routing_cloud.yaml` created:** all 14 agents on `gemini-3.1-pro-preview` via Vertex. `DEPLOYMENT_MODE` toggle in `router.py` (evaluated at call time, not import time — fixes `.env` load order bug).
- **Flash model ID updated:** `gemini-3.1-flash-lite-preview` → `gemini-3.1-flash-lite` (old preview discontinues July 9).
- **sys.path fix:** orchestrator now inserts project root so `tools/` resolves correctly when running `python core/orchestrator.py`.
- **Smoke test:** Research Agent via Vertex returned valid grounded response. Full pipeline: 60–90s latency (multiple sequential Gemini 3.1 Pro calls via AI Studio — see open item below).
- **Repo cleanup:** .gitignore expanded; all previously untracked files committed (108 files).
- **Vertex native SDK migration complete (2026-06-19):** `run_session_gemini()` now uses `_run_gemini_native_loop()` via `genai.Client(vertexai=True)` — same client setup as `run_session_gemini_grounded()`. All Gemini agents (coordinator, synthesizer, all specialists) are now on the native SDK. `_openai_compat_loop()` retained for OpenAI/Ollama paths only. One fix required: Gemini API rejects empty-string enum values; handled in `_clean_schema_for_gemini()` at conversion time. Tested: single-shot full pipeline + two-turn interactive history threading. Session archive: `2026-06-19 — Native SDK Migration (Gemini).md`.
- **Next sessions ready:** efficiency prompt + Android app prompt both written and in this archive.

### Also done 2026-06-17 (Metatron Android app session)
- **Metatron Android app built and working** — Capacitor wrapper, sideloaded APK, voice end-to-end confirmed.
- **Private STT pipeline** — Web Speech API (Google cloud) replaced with server-side Whisper via `/transcribe` endpoint. Audio archived to `data/audio/`. ffmpeg installed.
- **Server running HTTP on port 8001** (no TLS) — Tailscale WireGuard provides transport encryption. Certs backed up to `certs_backup/`.
- **Capacitor config:** bundled assets (secure context for mic), `SERVER` constant for API calls, `allowMixedContent: true`, 10-minute fetch timeout, dropdowns hidden, mike persona active.
- **Tailscale cleanup:** old stale device removed, host renamed to `mikes-macbook-air` in admin.tailscale.com. Direct IP `100.70.67.45` used in app (DNS not resolving in WebView).
- **Mem icon:** Phoenician/early Hebrew mem glyph, parchment+brown, generated by `tools/gen_icon.py`.
- **Next (on hold):** (1) Tailscale same-network vs. remote behaviour, (2) Mac always-on + Ollama warm, (3) login/profile selection in app.
- **⚠ HOLD (2026-06-17):** All Metatron / infrastructure work paused pending decision on whether to migrate hosting to Google Vertex VM. Decision resolves the architecture (local Mac vs. cloud VM as the LLM host) before further build work proceeds.

### Also done 2026-06-16 (continuation of A4/A6 session)
- **Synthesizer CRITICAL block** added — mandatory surface rules for `CLINICAL_CONCERN` and `MUST_SURFACE` flags; cannot be held or deferred; front-loaded after Confidentiality section (same pattern as MW fix). Covers mania, suicidal ideation, depression, missed critical medication.
- **CONSULT_NEEDED routing logic** added to Track E in roadmap — named deferred item with B2 dependency documented. Previously only mentioned verbally.
- **Prompt structure front-loading audit complete** — all 9 specialist agents assessed; only Synthesizer required immediate fix; Physical Health noted for D2 pass.

---

### Decisions resolved 2026-06-10
- **Binding privacy ruling:** sensitive data never reaches a cloud model — no fallbacks, no deferrals. Drove new A4 and re-tiering of routing.yaml (to be implemented at A4; current routing.yaml cloud fallbacks are stale).
- Check 7 vs. D2 conflict: resolved — assumptions documented now + safety hard-fails run on the local model at A4; full validation at Phase 6 / D2.
- E3 removed from Phase 6 close gate (circular dependency); Stage 2 builds single-user, Stage 3 automation gated on multi-user cohort.
- o3 Pattern Miner production test retired — Pattern Miner is local-only.
- Time Director carries no test obligations; testing plan amended.


---

## 2026-07-27 session notes

*(These were filed under "Model IDs" in SESSION.md — changelog entries in the
wrong section. Moved here verbatim.)*

**2026-07-27 session note (2nd session, later same day):** Design discussion on whether archive/wisdom tooling covers open-ended user data (expenses, watchlists, ideas) escalated into an implementation attempt (`update_archive_item` in `tools/diarist.py`, new `tools/finance_summary.py`, wiring in `core/orchestrator.py`, whitelist fixes in both `routing*.yaml`, a doc line in `finance.md`) made without checking `SESSION.md`/the roadmap/file-ownership rules first. This violated the frozen-specialist-file rule and the `core/orchestrator.py` ownership/A8-refactor plan already on record — **all of it was reverted** (verified clean via `git diff`). New standing rule added to `CLAUDE.md`: **"Mandatory Pre-Edit Context Check"** — no edit without first reading SESSION.md + active roadmap + ownership rules. Also saved as memory `feedback_pre_edit_context_check.md`. The one change that did land: `archive/plans/phase5_to_future_roadmap_2026-06-10.md` Section 4 now notes both gaps (Finance transaction aggregation; archive item lifecycle/update-in-place) as unscoped "Now tier" placeholders for future work — see that doc for details, and `archive/sessions/2026-07-27 — Data Management Gaps Discussion and Pre-Edit Context Rule.md` for the full session log.

**2026-07-27 session note (3rd session — chat rehydration + persona goals audit):** Located the one never-archived "Metatron — Single Exchange Troubleshoot" chat (of five same-titled transcripts) — session `f37f081a-693d-4b82-bdcb-b7d6d163b392`, SEQ 026 duplicate, left open mid-thread on CalDAV setup (which service Mike uses; timezone needs `America/New_York` → `Europe/London` in `config/modules/caldav.yaml`, currently `enabled: false` with empty credentials). Discussed blank vs. duplicate Google account for a London base — recommended blank, import contacts only, skip calendar/email history (works against the "hypothesis not verdict" design principle; Goals Interview is the intended onboarding mechanism, not account data mining). **New gap surfaced:** `config/goals.yaml` (Tier 3 structured store) is still empty despite `config/personas/mike.md` flagging "Goals interview completed 2026-06-26" — the interview's actual output landed in `data/baselines/aspirational_baseline.json` (good/hard week, peak/floor days narrative; also has an untagged `"persona": ""` bug) and the ephemeral `data/personas/mike/context.json` tracker instead of durable `goals.yaml`. No edits made — analysis only. Deferred to user: whether to draft `goals.yaml` entries from existing baseline/context data; account creation is a manual user step. Session archive: [archive/sessions/2026-07-27 — SEQ 026 Chat Rehydration and Persona Goals Gap Audit.md](../archive/sessions/2026-07-27 — SEQ 026 Chat Rehydration and Persona Goals Gap Audit.md)

**2026-07-27 session note (4th session — coordinator-slim chat rehydration):** Found and rehydrated the 2026-06-19 "slim coordinator.md" proposal chat on request. Confirmed it was never implemented: `config/modules/coordinator_routing.yaml` / `data/config/coordinator_routing.json` don't exist, no "Parallel dispatch" block is in `coordinator.md`, and the file has grown to 2,279 words (from 2,160 at proposal time) with new content the old proposal doesn't account for (deferral/rescheduling signal words, agent-name normalization). Still open per the roadmap (D2 latency item 5). No edits made — user confirmed they only wanted the context back, not implementation. If resumed later, needs a fresh audit against current file content, not the stale 2026-06-19 draft, and should re-check the Vertex 4096-token cache-padding floor (Section 4 monitor) before landing any reduction. Session archive: [archive/sessions/2026-07-27 — Coordinator Slim Chat Rehydration and Archive Runs.md](../archive/sessions/2026-07-27 — Coordinator Slim Chat Rehydration and Archive Runs.md)

**2026-07-27 session note (4th session — cross-device WS sync bug fix + deploy):** User was trying to relocate a "Synch" chat; traced it to [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](../archive/sessions/2026-06-26%20—%20Synthesizer%20Conversation%20History.md), which undersold its own follow-through — same-night commit `4302ef8` actually shipped full SQLite-backed, real-time cross-device WS sync (`core/server.py` `ConnectionManager` + `exchanges` table), never verified against two real devices and never fully documented (`dc8f031` has no session log entry). Found and fixed a real bug in `static/index.html` `sendViaWebSocket()`: `shownIds.clear()` ran after adding the new exchange ID instead of before, so once the client-side set exceeded 100 entries the in-flight exchange's own ID got wiped, causing the response bubble to hang forever with no error. Fixed (commit `eea3faf`), deployed via `./deploy.sh` (GCP billing had auto-disabled on the $20 cap mid-session, user re-enabled, deploy succeeded on retry). **Confirmed 2026-07-28/29:** user tested on real devices — "Synching seems to be occurring." **>100-exchange edge case force-tested 2026-07-29:** 300-iteration logic simulation (pre-fix fails at #101/#202, fixed order 0 failures) plus a live end-to-end WS test against the real production server on persona `cal_newport` (dev persona, not mike) — one real Vertex call, exchange correctly recognized as own through the fix, persisted to SQLite under the right persona, mike's data untouched (11 rows, unchanged). Fix fully confirmed at both logic and live-system level — see [archive/sessions/2026-07-27 — Cross-Device WS Sync Bug Fix and Deploy.md](../archive/sessions/2026-07-27%20—%20Cross-Device%20WS%20Sync%20Bug%20Fix%20and%20Deploy.md) for remaining open items (duplicate "4th session" label, undocumented `dc8f031`).
