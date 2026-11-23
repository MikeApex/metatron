### 2026-11-23, fourth (Iva's onboarding prerequisites — the first interview learns what an account otherwise takes months to learn; her problems reach the backlog; nothing of Build reaches her) — `ca7d05c` — **DEPLOYED by Mike 11-23; VM at `ca7d05c`**

**Incoming handoff:** the primer's "Still next: Iva's onboarding (10-29 walkthrough prompt; #11/#40/#41
first)" and "before Iva signs up: the backlog sync fetches mike's quality events only". Mike asked
for the onboarding walked through, then for the prerequisites done in-chat, with every feature `mike`
has, the first interview gathering what `mike`'s account learned over months, and her work calendar
asked about. Plan, two Fable reviews and every disposition:
`archive/plans/iva_onboarding_prereqs_plan_2026-11-23.md`. Walkthrough (supersedes 10-29):
`archive/handoffs/2026-11-23-iva-onboarding-walkthrough-prompt.md`.

**Built (`ca7d05c`, 16 files):** the interviewer gathers people (`write_contact`), household/home
address/language (`write_profile`), who-does-what, health limits, work place, an unseen work calendar
and never-ping times (`write_wisdom`, `stated`), with routines/protected time in `set_day_shape` —
generic, granted in both routing files; coverage counts people/facts/home and names waiting contact
cards (they lapse in 10 min). A paused interview: D2 stands (Mike), but scheduled runs invite her to
finish once a day, three times in all. Build block only for a persona with no account record,
fail-closed (#40); registry scoped per persona, abandoned rows carry it (#41). Backlog sync reads
`mike` + every `active` account, `[from iva]`, never merged with Mike's. APK rebuilt (sha `4352d3c6`).

**Rulings (Mike):** monthly caps stay $100/$175 — monitor once she joins (estimate ~$125–150/mo is
above the soft cap; Gemini rates double 2027-01-01). English primary, **typed Bulgarian only** —
spoken needs a multilingual STT model + VM benchmark, and does not work for `mike` either
[DB-0810-15]. No seeding of `mike`'s household facts — her words. D8 = dedicated Metatron Gmail (his
setup). Hourly intake + CRM sweep on for her after she is told (supersedes 10-29 "off until asked").

**Rejected:** enabling her intake on her real Gmail (drains ~500 old messages); saving never-ping
times as wisdom alone (nothing in the nudge path reads wisdom — quiet hours are `scheduler.yaml`,
set by hand at the walkthrough); holding sessions while paused (Mike kept D2).

**Believed true, wrong:** (1) I said `mike`'s intake extractor was ON — line 3 of his `intake.yaml`
is `forwarding.enabled`; the extractor is off, as `SESSION.md` § Do not re-open says. (2) The 10-29
handoff's `.env` `AUDIO_BACKUP_PERSONAS` step was stale — `metatron-backup.sh:90` already names
iva. (3) My first phone list missed ~six settings (Always-on VPN, pause-if-unused, notification
channel, precise location, data saver, install-unknown revoke). (4) The plan said accounts are
`approved`; the status is `active`. (5) `write_profile` has no health field and one address,
stored under `contact`. (6) Port 8888 on the Mac is the WhatsApp session's server; this APK is on
8889 — same app ID, so installing it replaces the waprobe build.

**3.7 vs 3.8 Flash:** 3.7 is where the January doubling comes from; only 3.5 Flash-Lite has list
rates. Moving reasoning-tier agents down is a quality call, deferred to measured two-user spend.

