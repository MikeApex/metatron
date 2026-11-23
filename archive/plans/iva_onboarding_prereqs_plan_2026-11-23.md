# Iva's onboarding — the prerequisites, the interview additions and the walkthrough (2026-11-23)

**Status:** plan, pre-review. Mike approved the shape in chat 2026-11-23 and asked for a Fable
review of everything before code, with an explicit hunt for onboarding edges ("the onboarding
should be seamless"). Builder: Opus 5.5 in the planning chat (Red-tier files, not delegated).

**Need:** Iva signs up and Metatron works for her the way it works for `mike`: every user-facing
feature `mike` has, and the knowledge `mike`'s account accumulated over months gathered in her
first interview instead of over months.

**Facts established before this plan (read, not assumed):**
- `accounts.py list` shows no accounts. Iva's phone: **Motorola Edge 40 Neo, Android**.
- `scripts/metatron-backup.sh:90` already holds `AUDIO_BACKUP_PERSONAS="mike iva"` — the
  10-29 handoff's `.env` step is stale and is dropped.
- `mike` on the VM: `intake.yaml` enabled (extractor enabled), `crm_sweep.yaml` enabled,
  caldav/email enabled, consents `correspondence_read` + `tone_profile` + `base_configuration`,
  one custom scheduler job `manny_school`, no `zones.yaml`, no Google Contacts OAuth token.
- Approval (`scripts/accounts.py provision`, :105-126) creates `iva.md`, `profile.yaml`,
  prime_directive/mission/goals stubs, scheduler/caldav/email from templates, interview state
  `not_started`, `consents.json` with `base_configuration`, and enables
  `metatron-scheduler@iva`. It does **not** create `intake.yaml` or `crm_sweep.yaml`
  (templates `enabled: false`).
- Day-plan flags and capture are global (`config/modules/day_plan.yaml`, `capture.yaml`).
- `mike`'s wisdom: 79 entries — people and their logistics (kids' activities, providers),
  household division of labour, protected time (post-20:30), work-block priorities, health
  providers/urgent care, routines. Profile: city, timezone, address, phone, emails,
  input/output language.
- The interviewer (`config/agents/goals_interviewer.md`) is granted only
  `read_goals, write_goals, write_config, write_retrospective, create_semantic_anchor,
  write_aspirational_baseline, update_goal, write_baseline_period, set_day_shape,
  pause_interview, finish_interview` (`config/modules/routing_cloud.yaml:248`; same block
  expected in `routing.yaml`).
- Interview coverage block: `core/interview.py:228` `coverage_block()`.
- `config/agents/capture_extractor.md` has **uncommitted changes from another session** —
  this plan does not touch it.

---

## A. Code, before deploy

### A1. Build notes are not shown to a non-developer (review #40) — `tools/build.py`
`context_block(persona)` returns `""` unless the persona is the developer's. Resolve "developer"
from the account store if a role exists (an approved account with role `user` → not developer);
a persona with no account record (`mike`, test personas) is the developer. Delete the
"Mention these only if relevant…" sentence. Test: an account-user persona with a pending ticket
→ empty block; `mike` unchanged.

### A2. Build tickets keyed by persona (review #41) — `core/build/registry.py`, `core/build/tickets.py`
`rows_by_ticket` → keyed `(persona, ticket)`; callers filter on `row["persona"]`;
`mark_abandoned` names the row `abandoned_<persona>_<ticket>`. Existing registry rows: all
`mike`'s, so a row without a persona is read as `mike`'s. Update
`tests/test_build_tickets.py:180-189` (two personas mint the same id — still true, now harmless).

### A3. The backlog sync reads every approved account — `scripts/sync_dev_backlog.py`
Personas = `mike` + every `approved` row from `/monitor/accounts`. For each: `fetch_events`,
tag the event with its persona. Non-`mike` entries render with a `[iva]` prefix; the seen-set
key becomes `persona:timestamp` for non-`mike` (bare timestamp kept for `mike` so the existing
ledger stays valid). `--persona` still forces a single persona.

### A4. The first interview gathers the practical knowledge — Red
**`config/agents/goals_interviewer.md`** — a new short block under Phase 1 (its own register:
practical, never in a purpose turn), each item saved the turn it is given:
- People: partner, children (names, ages, schools, regular activities), anyone she cares for
  or relies on; GP, dentist, out-of-hours care → `write_contact`.
- Who handles what at home (payments, school admin, appointments) → `write_wisdom`.
- Weekly or recurring commitments not on a calendar → `set_day_shape` if daily, else
  `write_wisdom`.
- Protected time and how she wants to be checked on (never-ping windows, directness,
  frequency) → `write_wisdom`.
- Home and work addresses; languages she writes/speaks in and wants replies in →
  `write_profile`.
- Health conditions that shape her day → `write_profile` (health notes). Medication and clinical
  facts are **not** saved by the interview (their home is `write_agent_config`, which carries the
  safety check) — ordinary chat later.
- Work calendar: "Is there a work calendar I can't see — Google Workspace or Outlook?" →
  `write_wisdom` (so the planner treats work hours as spoken for).
Tools Available section lists the three new tools.

**`config/modules/routing_cloud.yaml` + `routing.yaml`** — add `write_profile, write_wisdom,
write_contact` to `goals_interviewer.allowed_tools`.

**`core/interview.py` `coverage_block`** — three lines: people saved (count of contacts),
standing facts saved (count of wisdom), home address / reply language set or not. Tests in the
interview suite.

### A5. Walkthrough prompt refreshed — `archive/handoffs/2026-11-23-iva-onboarding-walkthrough-prompt.md`
Supersedes the 10-29 prompt. Carries: the phone checklist (Moto Edge 40 Neo exact taps), the
phone test, the work-calendar decision, the feature switch-on step (B2), the household-seeding
ruling (none — her own words), and the corrected prep list.

## B. During the walkthrough

### B1. Phone settings (Moto Edge 40 Neo, Android 13–15)
1. Install unknown apps: allow for the app that opens the APK; revoke after.
2. Microphone + Notifications: Allow.
3. Channel "Nudges and check-ins": sound, lock screen, pop on screen. DND exceptions her call.
4. Location: While using the app, Precise on.
5. Battery: Metatron and Tailscale → Unrestricted.
6. "Pause app activity if unused": off for Metatron.
7. Tailscale: Always-on VPN on; Block connections without VPN off.
8. Data saver: unrestricted data for both if on.

### B2. Feature parity switch-on (after she connects Google)
Claude writes `config/personas/iva/intake.yaml` (enabled, extractor enabled) and
`crm_sweep.yaml` (enabled) on the VM, after she is told what hourly sorting does and agrees.
Tone profile: her tick in the connect panel. `manny_school` not copied — her version comes from
the interview or chat. WhatsApp: not available (probe build on Mike's phone only).

### B3. Phone test
1. `/push/test` as `iva`, app open → arrives.  2. Screen locked 5 min → sound + lock screen.
3. Next morning after overnight idle → arrives; read her `push_log.jsonl`.  4. Reboot, open
nothing → arrives (Tailscale reconnected).  5. Speak a message, 🔊 → reply in her language.
6. Message with location on → location recorded on the VM.

## Cost
Build: Opus ~0.6–1M tokens; Fable review ~0.2M. Mike: ~15 min approving Red edits, ~20 min
APK + deploy. Run: interview ~+$0.50 once; her intake hourly cost — to be read from `mike`'s
spend before B2 (unknown now). No new persistent object beyond her two config files.

## Rulings in this plan (Mike, 2026-11-23)
- Give her every feature `mike` has (including hourly inbox sorting — supersedes the 10-29
  "intake stays off until she asks"; she is told and can decline).
- No seeding of `mike`'s household facts into her account — her own words.
- The interviewer gathers the practical knowledge (A4); work calendar asked.

---

## Review round 1 — Fable, 2026-11-23: 17 findings (block 1: 3 structural, 7 local; block 2: 1 structural, 6 local) — dispositions

Mike's answers the same day: **language** — English primary and default; she may type or speak
Bulgarian. **Pause** — scheduled sessions start on pause as built (D2 stands), but she is
encouraged to finish.

| # | Finding (what she would see) | Disposition |
|---|---|---|
| S1 | "Don't ping me after X" / work hours saved where planner and nudges never read | **Accepted.** Protected time → `set_day_shape` `windows` (strength `protected`); weekly commitments → `routines` with their days; work hours → `day.work_start/end` (already in Phase 1). A never-ping window → her `scheduler.yaml` `quiet_hours`, set by Claude on the VM at walkthrough close (no tool writes it; `mike`'s is the 22:00–07:00 default). Wisdom only for what no code reads (who handles what). |
| S2 | Mailbox choice undecided; intake on her real Gmail drains ~500 old messages | **Accepted.** D8 = (a), the dedicated account, which is `mike`'s setup. Intake switched on only after forwarding is confirmed; the new mailbox has no backlog. |
| S3 | Extractor re-enabled against a settled ruling | **Plan error, dissolved.** `mike`'s `intake.yaml` has `forwarding.enabled: true` (line 3), not the extractor — re-read on the VM. Her file: `enabled: true`, `forwarding: {enabled: true, own_addresses: [her real address]}`, no extractor. |
| L4 | Sync filters on `approved`; no account ever has it | **Accepted.** Status is `active`. |
| L5 | No health field; one address; work address overwrites home | **Accepted.** `write_profile` for `household`, `address` (home), languages; health and work address → `write_wisdom` (`health` / `work`, stated). Medication never. |
| L6 | Interview wisdom held 14 days as `observed` | **Accepted.** Instruction: `provenance: stated`, one of the eleven domains. |
| L7 | Contact cards for same-surname family; untapped ones lost | **Accepted.** Interviewer told to say plainly there is a card to tap; coverage lists waiting contact cards. |
| L8 | Spend guard shared across users | **Accepted, stated.** Daily $15 stop has headroom (~$4/day for two). **Larger, found here:** the monthly GCP caps ($100 soft stops the VM, $175 hard disables billing) were sized for one user; two users + infra ≈ $125–150/mo now and the Gemini rates double on 2027-01-01. Decision for Mike. |
| L9 | Sync merges her events into Mike's entries | **Accepted.** Persona enters the signature for non-`mike` events. |
| L10 | Re-keying breaks `decided_awaiting_deploy`, `build_board.py`, `test_build_registry.py` | **Accepted.** All callers moved. |
| B2-S3 | Calendar connected after the interview never gets "which calendars are yours" | **Accepted.** Walkthrough order fixed: Google connect **before** the interview. |
| B2-1 | Interview replies never translated; read-aloud voice follows reply language | **Moot for English primary.** Instruction: replies stay English unless she asks; never set `output_language` unless she asks. |
| B2-2 | Speech-to-text is one server-wide English-only model | **Not in this pass.** Spoken Bulgarian does not work for `mike` either (`base.en`, [DB-0810-15]); a model swap + VM memory benchmark + toggle-vs-detect decision. Typed Bulgarian works today. Raised to Mike. |
| B2-4 | A pause releases briefs/check-ins against a near-empty account | **Mike: start on pause, encourage.** At pause the interviewer says in a sentence what finishing gives her; while paused, an invitation to continue reaches her at most once a day, three times in all. |
| B2-5 | "Cannot reach the server" if the tailnet share is missing | **Accepted.** Walkthrough: after the share, open the server URL in her phone's browser before installing the APK. |
| B2-6 | Anyone signing in on her phone takes over its notifications | **Accepted.** Walkthrough rule: nobody else signs in on her phone. |
| B2-7 | Timezone silently left at UTC | **Accepted.** Approval check: `profile.yaml` timezone is `Europe/London`; fix on the VM if not. |

## Code review — Fable, 2026-11-23, on the built diff: 5 findings, 3 test gaps

| # | Finding | Disposition |
|---|---|---|
| 1 | Home address never reads as set in coverage (stored under `contact`) | **Fixed**, with a test that writes a real address through `write_profile` |
| 2 | An untapped contact card lapses after 10 min with no trace; wording said "new" for any contact change | **Fixed in wording**: the line says cards lapse in ten minutes and to ask again if the count did not rise. TTL unchanged (system-wide `confirm.TTL_SECONDS`) |
| 3 | An invitation is spent when built, not when delivered; day is the server's | **Accepted as is** — three invitations is a soft limit; VM and both users are Europe/London |
| 4 | Session-start ⚠ line did not say whose problem | **Fixed**: `[iva]` prefix |
| 5 | Build block skipped the account check when persona was None | **Fixed**: resolves first, fails closed |
| T1 | Sync `main()` never run in tests | **Fixed**: end-to-end test (persona list, tagging, ledger, `--persona`) |
| T2 | Address test passed vacuously | Fixed with 1 |
| T3 | Unscoped `decided_awaiting_deploy` test only | Covered by the new scoped test |

Final: all 14 build suites, sync 8/8, interview 20/20 (+ orchestrator, capture, session-line: 82),
ritual 33 + 11, null-ish 43, reconciliation 5, `qa_sweep` 12/12.
