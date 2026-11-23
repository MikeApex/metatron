Model: Opus 5.5, effort high. An (M) session run live with Mike and Iva; her account touches identity and per-user config, and the judgement is the work, so nothing is delegated.

# Iva's onboarding — prepare, then walk her through it (paste into a fresh chat)

**Supersedes** `archive/handoffs/2026-10-29-iva-account-walkthrough-prompt.md`. Plan, rulings and
the Fable review this rests on: `archive/plans/iva_onboarding_prereqs_plan_2026-11-23.md`.

**Budget:** ~0.2–0.4M Opus tokens. Mike: ~20 min of preparation, then **~1½–2 h with Iva**
(most of it her first interview, which she can pause). **Run cost:** her use ~$1.50–2.00/day if
like Mike's (~$45–60/month), the first interview ~$2.20 once, one more scheduler process
(~40–140 MB, no model). New persistent objects: her two config files (§ 3.4), deleted with her
account.

---

/metatron-code Walk Iva onto Metatron. Read the plan above first — its "Review round 1" table
says what each step below protects against.

## 0. Before this session (Mike, done in the 11-23 session or after it)

1. **The code the onboarding needs is committed and deployed.** Committed 11-23 (check
   `git log`): her build notes hidden (#40); build tickets kept per user (#41); the backlog sync
   reads every active account, tagged `[from iva]`; the first interview gathers people and
   practicalities; a paused interview invites her back once a day, three times in all. Confirm the
   VM HEAD equals the Mac's: `git rev-parse HEAD` on both.
2. **The APK is rebuilt** from that HEAD: `./scripts/check_apk_sync.sh`, then
   `npx cap sync android && cd android && ./gradlew assembleDebug`. Mike installs it on his own
   phone first and checks that sign-in works, a reply arrives with bullets, and 🔊 speaks. It
   must be built **on this Mac**: the push key accepts only this Mac's debug signing
   certificate (`docs/INFRASTRUCTURE.md`). `assembleDebug` carries none of the WhatsApp probe.
3. **The monthly billing caps stay as they are** (Mike, 11-23); § 6 says what to watch.
4. **Not needed:** `.env` / `AUDIO_BACKUP_PERSONAS` — `scripts/metatron-backup.sh:90` already
   reads `"mike iva"`.

## 1. Her phone — Motorola Edge 40 Neo (Android 13–15)

Claude reads these out one at a time; Iva taps. Menu names differ slightly between Android 13 and
14 — find the nearest match.

1. **Tailscale.** Mike shares **only `metatron-vm`** with her from the Tailscale admin console
   (Machines → metatron-vm → ⋯ → Share). She installs Tailscale from the Play Store, signs in,
   and accepts the share.
2. **Prove she can reach the server before anything else.** In Chrome on her phone, open
   `https://metatron-vm.tail0acc5d.ts.net:8001`. A page loads → continue. "Can't reach" → the
   share is not accepted or Tailscale is off. Without this the app says only "Cannot reach the
   server."
3. **Tailscale reconnects on its own.** Settings → Network & internet → VPN → ⚙ beside Tailscale
   → **Always-on VPN: on**. Leave **Block connections without VPN: off**.
4. **Install the APK.** Mike sends the file directly to her. Opening it asks to allow installs
   from that app: allow it. Once installed, **turn that permission back off**: Settings → Apps →
   Special app access → Install unknown apps → that app → off.
5. **First launch.** Allow **Microphone** and **Notifications** when asked.
6. **Battery.** Settings → Apps → See all apps → **Metatron** → App battery usage →
   **Unrestricted** (on Android 14, also turn on *Allow background usage*). Then the same for
   **Tailscale**. Mike's failed pings all followed long idle.
7. **Don't let Android strip permissions.** App info → Metatron → **Pause app activity if
   unused: off**.
8. **Notification style.** App info → Metatron → Notifications → **Nudges and check-ins** →
   sound on, lock screen on, pop on screen on. Do Not Disturb exceptions are her choice. (The
   channel appears after the first notification. Come back to it after § 5 step 1 if it is not
   there yet.)
9. **Data saver.** Settings → Network & internet → Data Saver. If it is on, set Metatron and
   Tailscale to unrestricted data.
10. **Location — when the interview asks.** Choose **While using the app**, with **Use precise
    location: on**. Approximate breaks noticing she has arrived somewhere.

**Rule for the whole session: nobody else signs in on her phone.** There is no Sign out yet, and
the phone's notifications belong to whoever signed in last. If Mike checks something as himself
on her phone, his nudges go to her until the app's data is cleared.

## 2. Sign-up and approval

1. **She signs up** in the app (*Create an account*). Username `iva` unless she prefers
   otherwise. **She reads the notice herself and accepts it herself (D9).** The notice says:
   Google's Vertex terms apply; the app is early and incomplete; **Mike can read everything**;
   read-aloud in a language the local voice cannot speak goes to Microsoft's online voice. While
   she waits she sees "Your account is waiting for approval."
2. **"approve iva" in chat** → `.venv/bin/python scripts/accounts.py approve iva` over the VM
   line. Then confirm, read-only, that:
   - `metatron-scheduler@iva` is active;
   - `consents.json` holds the sign-up permission;
   - her interview state is `not_started`;
   - `config/personas/iva/profile.yaml` has **`timezone: Europe/London`**. If it says UTC or
     is blank, the sign-up form sent nothing usable; fix the one line on the VM.

   **Record the date and time: the week-long memory watch (M3) starts now** — seven days with
   both users and both schedulers, a Sunday included. Write the end date into `SESSION.md` at
   close.
3. **She does not start chatting yet.** Her first message opens the interview. § 3 comes first,
   so the interview can ask which calendars are hers.

## 3. Her Google account — before the interview

**What it gives her:** Metatron reads her calendar and mail in conversation, plans her day around
real events, adds events and drafts emails (each send waits for her tap), sorts her inbox every
hour, and builds her contacts from her mail — the same as Mike's account.

### 3.1 Which account — decided: a dedicated Metatron Gmail (D8 (a), Mike's own setup)

She creates `iva.<something>.mt@gmail.com` with a password she keeps herself (a password
manager, not Mike). Anything Metatron sends goes from that address, not her real one. A fresh
inbox also means the hourly sorting has no backlog of old mail to chew through.

### 3.2 Her work calendar — ask her now

*"Is your work calendar Google Workspace, Outlook / Microsoft 365, or something else?"*
- **Google Workspace:** share it to the dedicated account like her personal calendars (§ 3.3
  step 1), if her employer allows sharing outside the company. Otherwise treat it as "neither".
- **Outlook / Microsoft 365:** it cannot connect directly yet. If Outlook can **publish** the
  calendar (Outlook on the web → Settings → Calendar → Shared calendars → Publish a calendar →
  ICS link), she subscribes to that link in the dedicated account's Google Calendar (Other
  calendars → + → From URL). It then arrives like any other calendar. Work mail stays out.
- **Neither works:** say so plainly. The interview asks about the work calendar it cannot see
  and saves her working hours, so the day plan still keeps them free.

### 3.3 The steps

1. **Share her calendars** to the dedicated address, from her *own* Google account on a computer
   (calendar.google.com; the phone app cannot share): ⚙ Settings → the calendar → *Share with
   specific people* → the dedicated address → **"Make changes to events"**. Repeat for each
   calendar, including any she shares with Mike. Then, **signed in as the dedicated account**,
   open each invitation email → *Add this calendar*. A share that has not been accepted does not
   appear.
2. **Forward her mail** from her own Gmail on a computer: ⚙ → *See all settings* → *Forwarding
   and POP/IMAP* → *Add a forwarding address* → the dedicated address. Open the code Gmail sends
   **to the dedicated inbox**, confirm it, then choose *Forward a copy… and keep Gmail's copy in
   the Inbox* → *Save Changes*.
3. **On the dedicated account:**
   - 2-Step Verification on (myaccount.google.com/signinoptions/two-step-verification);
   - an **app password** named "Metatron" (myaccount.google.com/apppasswords) — 16 letters, shown
     once;
   - IMAP on (Gmail → Settings → *Forwarding and POP/IMAP* → *Enable IMAP*).
4. **In the app: ⚙ → Google account** → the dedicated address and the app password →
   *Continue*. **"read my calendar and mail"** (required) and **"learn how I write"** (Mike has
   it on; her call) → *Connect*. **Never paste the app password into a chat** — it would land in
   the transcript archive and every backup after it. It goes only into this panel, to one chmod
   600 file on the VM that backups skip.
5. **Expect "Connected — found N calendar(s): …".** On failure the panel names the step to fix.

### 3.4 Claude switches on the rest — after telling her what it does

Say it plainly: *"Every hour Metatron sorts what arrives in that inbox and tells you about what
needs you. Overnight it adds the people who write to you to your contacts. Do you want both?"*
On a yes, write these two files on the VM. They copy Mike's settings, which keep the extractor
off — it is retired, per `SESSION.md` § Do not re-open:

`config/personas/iva/intake.yaml`
```yaml
enabled: true
forwarding:
  enabled: true
  own_addresses:
  - <her real Gmail address>
```
`config/personas/iva/crm_sweep.yaml`
```yaml
enabled: true
```
Then chmod 600 both, and check that they are ignored by git (`git check-ignore`). Both are
read fresh on every run (`tools/intake.py`, `tools/crm_sweep.py` `load_config`), so the next
hourly sweep picks them up with no restart.

### 3.5 Claude verifies, read-only

- `caldav.yaml` and `email.yaml` show `enabled: true` and **no password**; `credentials.yaml`
  exists with mode 600.
- `consents.json` holds `correspondence_read` (and `tone_profile` if she ticked it).
- Her calendar read returns her events. Name the calendars back to her.
- `git status` on the VM shows none of her files.

## 4. The first interview

She sends her first message. Watch for these, and note them against `[DB-…]` ids only if they
recur:
- **Calendars:** it asks which are hers, which are shared and which to ignore. This only
  happens because § 3 came first.
- **People and practicalities** come in their own turns: partner, children, schools,
  activities; GP, dentist, out-of-hours care; who handles what at home; weekly routines;
  health limits (never medication); home address; the work calendar it cannot see; times she
  never wants to hear from it.
- **Contact cards:** family members with the same surname raise an "add as a new contact?"
  card. Make sure she **taps each one** — an untapped card is never saved.
- **Location yes** → the "Location is on…" note appears, and § 1 step 10.
- **Language:** replies stay English. She can type Bulgarian and be understood. **Spoken
  Bulgarian is not supported** for anyone yet (English-only speech model, [DB-0810-15]) — tell
  her before she tries.
- **Capture:** after a few turns, read her `day_shape.yaml` and her new contacts and standing
  facts, and record how many of the facts she gave were kept.
- **If she pauses:** check-ins and the brief start from what she has said so far, and invite
  her back once a day, three times at most. Encourage her to finish in this sitting if she can.

**After the interview — her never-ping window.** If she named times she never wants to hear from
Metatron that differ from the default 22:00–07:00, set `quiet_hours` in
`config/personas/iva/scheduler.yaml` on the VM to match. No tool writes it; Mike's is the
default.

## 5. The phone test

| # | Do | Pass |
|---|---|---|
| 1 | App open: `curl -sk -X POST -H "Authorization: Bearer $(python3 scripts/mint_token.py)" "https://metatron-vm.tail0acc5d.ts.net:8001/push/test?persona=iva"` from the Mac | arrives within seconds |
| 2 | Screen locked 5 min, send again | sound, and shown on the lock screen |
| 3 | **Next morning**, after the phone sat idle overnight, send again; then read `data/personas/iva/push_log.jsonl` on the VM | arrives; no fetch failure logged |
| 4 | Restart the phone, open nothing, send again | arrives (Tailscale reconnected by itself) |
| 5 | She speaks a message in English, then taps 🔊 | a reply arrives and is read aloud |
| 6 | A message with location on | a location is recorded for `iva` on the VM |

Test 3 is the case that failed 5 of 11 times on Mike's phone after long idle (10-29). If it
fails, battery (§ 1 step 6) is the first suspect.

## 6. Cost — watch it once she joins (Mike, 2026-11-23: caps stay as they are)

The monthly GCP caps stay at **$100 soft** (stops the VM, about 60 seconds to recover) and
**$175 hard** (disables billing; once meant a 26-hour outage). Mike chose to watch real
two-user spend before changing them. Two users plus the VM itself are estimated at ~$125–150 a
month, which is **above the soft cap**, and **Gemini rates double on 2027-01-01**
(`config/modules/spend_guard.yaml`). So:
- after her first full day, and again weekly, read the per-day spend from the spend guard's
  records and the billing console, and compare it against the month's running total;
- if the month is tracking past $100, raise it with Mike **before** the soft cap fires. When
  raising, change the hard cap first and keep the ~$100 gap
  (`docs/INFRASTRUCTURE.md` § Billing protection).

The daily $15 spend stop is shared and has room for two.

## Not in this session

- Spoken Bulgarian (model swap + VM memory benchmark + Mike's toggle-vs-detect decision).
- A real Sign out (`DEV_BACKLOG.md`); the reply-latency work; security `[DB-1029-20]`.
- WhatsApp reading (still a probe build on Mike's phone).

The VM line every read uses (read-only unless stated):
`gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command='cd ~/multi-model-mcp && …'`

Another chat may be working in this tree. `git diff` every file before staging, and never stage
another session's lines. Close with `/archive`.
