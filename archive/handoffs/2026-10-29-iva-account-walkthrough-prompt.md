Model: Opus 5.5, effort high. An (M) session run live with Mike and Iva: preparing her phone, her sign-up and approval, her first interview minutes. The judgement is the work, and her account touches Red-tier config, so nothing is delegated.

# Iva's account — prepare, then walk her through it (paste into a fresh chat, weekend of 2026-10-31)

**Budget:** ~0.2–0.4M Opus tokens. Mike: ~20 min of preparation (APK rebuild, `.env` line,
deploy), then ~30–45 min with Iva. **Run cost:** Iva's use ~$1.50–2.00/day if it is like Mike's
(`archive/plans/multi_user_accounts_plan_2026-10-26.md` § 7), her interview ~$1.70 once, one
more scheduler process (~40–140 MB, no model). Nothing new persists beyond her account.

---

/metatron-code Walk Iva onto Metatron. Read first, in order:
`archive/plans/multi_user_accounts_plan_2026-10-26.md` § 6.4 (Iva), § 4.10 (Connections) and § 9
(D8), then `archive/log/2026-10-29-04-stage-5-closed-flags-formatting-location.md` (what Stage 5
found and fixed), then this prompt.

## Where it stands (2026-10-29)

- **Stage 5 is closed: all seven checks pass** (check 2 closed on findings). The four trial
  accounts were deleted by Mike at his terminal; `accounts.py list` shows **no accounts**.
- **VM at `ebfe50b`.** Committed and not yet deployed: `0b143a9` (one line in Safari's location
  help) and the 10-29 `Archive:` commit. A deploy first is harmless and puts the VM at HEAD.
- **Live since 10-29, and what Iva will meet:**
  - Replies keep their line breaks; several questions come as bullets; the interviewer keeps one
    register per turn (purpose never shares a turn with schedules).
  - Location: a yes in her interview switches location on in the app with a note that her phone
    will ask. A refused permission says where to allow it (phone app: Settings → Apps → Metatron
    → Permissions).
  - **A scheduled session can no longer raise a clinical flag.** Mike, 10-29: the flagging system
    is curtailed until the agent rewrite. A disclosure **in her own words** still gets the
    interview's crisis reply and pauses the interview. **Nobody is alerted:** the escalation
    record routes nowhere, by design for now. Mike knows this.
- **Push delivery is not fully reliable.** On Mike's phone, 5 of 11 pings failed after long
  idle on 10-29, cause unknown. The phone app now retries and logs why to `push_log.jsonl`.

## 1. Before Iva arrives (Mike, with Claude checking)

1. **Rebuild the APK.** `static/index.html` changed on 10-29, so the bundled copy is behind:
   `./scripts/check_apk_sync.sh`, then `npx cap sync android && cd android && ./gradlew assembleDebug`.
   Mike sideloads it on **his own phone first** and confirms sign-in, a reply with bullets, and
   the 🔊 voice still working. The push key is restricted to this Mac's debug signing certificate,
   so her phone installs the same APK.
2. **Deploy** (`./deploy.sh`, Mike: it is denied to Claude). Claude confirms the VM HEAD equals
   the Mac's.
3. **`AUDIO_BACKUP_PERSONAS` in the VM's `.env` names `iva`** — Mike's file, Mike edits it
   (`.env` is denied to Claude). It decides whether her voice recordings enter the Mac backup
   (plan, Stage 1.9: Mike's and Iva's are backed up, later accounts' are not).
4. **Claude prepares the walkthrough script below as a short numbered list Mike can read from**,
   with the exact taps for her Android version once Mike says which phone she has.

## 2. The walkthrough, live

1. **Tailscale:** share **only `metatron-vm`** with her, nothing else on the tailnet. She
   installs Tailscale and accepts the share.
2. **Battery: set both Tailscale and Metatron to Unrestricted** (Settings → Apps → each →
   Battery). Mike's failed pings all followed long idle. Tell her a notification that says
   only "You have a message" means "open the app".
3. **The APK**, sent to her directly; she installs it. At first launch Android asks for the
   **microphone and notifications**: Allow both.
4. **Her sign-up.** She reads the notice herself: Google's Vertex terms, early and incomplete,
   **Mike can read everything**, and read-aloud in a language the local voice cannot speak going
   to Microsoft's online voice. **She accepts it herself (D9).** Username `iva` unless she
   prefers otherwise.
5. **"approve iva" in chat** → Claude runs `.venv/bin/python scripts/accounts.py approve iva`
   over the VM line, then confirms `metatron-scheduler@iva` is active, her `consents.json` holds
   the sign-up permission, and her interview state is `not_started`.
   **Record the date and time: the week-long memory watch (M3) starts now** (plan § 6.3a.3): seven
   days with both users and both schedulers, a Sunday included. Claude writes the end date into
   `SESSION.md` at close.
6. **Link her accounts:** § 3 below, start to finish. It can come before or after the first
   interview minutes. Before is better: once a calendar is connected, the interview asks which of
   her calendars are hers, which are shared and which to ignore.
7. **The first minutes of her interview.** Watch for, and note against `[DB-…]` ids only if they
   recur:
   - **When she says yes to location,** the "Location is on…" note appears and her phone asks.
     Allow.
   - **Questions arrive as bullets,** and purpose questions never share a turn with schedule ones.
   - **Each day fact she gives is saved in the turn she gives it.** Claude reads her `day_shape.yaml`
     on the VM after a few turns. Misses here are the evidence for the capture-fidelity build
     (`archive/handoffs/2026-10-29-capture-fidelity-plan-prompt.md`): record how many of how many.
   Then her use decides.

## 3. Linking her accounts — calendar and mail

**What it gives her:** Metatron reads her calendar and mail in conversation, plans her day
around her real events, and can add events or draft emails. Each send waits for her tap. **Mail
intake, the automatic hourly inbox sorting, stays off** until she asks for it. Connecting does
not start a sweep of her inbox. Design: plan § 4.10; permissions § 4.11.

**How it works:** one Google *app password* covers calendar, reading mail and sending. She enters
it in the app's **⚙ → Google account** panel, never in a chat. It goes in one request to one file
on the VM (`config/personas/iva/credentials.yaml`, chmod 600), which the backups skip, so **it is
never on Mike's Mac or in this transcript.** Tell her that, and that Mike, as developer, can reach
the VM. *Disconnect* in the same panel deletes it. **Never let her paste the app password into a
chat**: it would land in the verbatim transcript archive and every backup after it.

### Decision D8 at this moment: which Google account — her choice; recommend (a)

- **(a) A dedicated Metatron Gmail (recommended),** the convention Mike's own persona follows
  (`diamond.mike.mt@gmail.com`). Anything Metatron sends, including one a hostile email talked it
  into, goes from that address, not her real one. She chooses what reaches it, and turning it off
  is one share and one forward to undo. **Cost:** ~15 minutes more setup.
- **(b) Her own Gmail directly.** The least setup. The system reads all her mail and sends as
  her real address.

### (a) Dedicated account — the steps, in order

1. **Create the account** on her phone or a browser: e.g. `iva.<surname>.mt@gmail.com`, with a
   password she keeps (a password manager, not Mike).
2. **Share her calendar(s) to it,** from her *own* Google account on a computer
   (calendar.google.com; the phone app cannot share): ⚙ Settings → under *Settings for my
   calendars* pick the calendar → *Share with specific people* → add the dedicated address →
   permission **"Make changes to events"** (needed for Metatron to add events; "See all event
   details" if she wants it read-only). Repeat for each calendar she wants it to see, including
   any she shares with Mike. Then, **signed in as the dedicated account**, open the invitation
   email and click *Add this calendar*. A share not accepted does not appear.
3. **Forward her mail to it,** from her *own* Gmail on a computer: ⚙ → *See all settings* →
   *Forwarding and POP/IMAP* → *Add a forwarding address* → the dedicated address. Gmail emails a
   confirmation code **to the dedicated inbox**: open it there, then back in her own Gmail choose
   *Forward a copy… and keep Gmail's copy in the Inbox* → *Save Changes*. *(If she would rather
   send it only some mail, a filter with "Forward it to" instead of forwarding everything.)*
4. **On the dedicated account,** the three steps the panel lists:
   - turn on **2-Step Verification**
     (myaccount.google.com/signinoptions/two-step-verification). It needs her phone number;
   - create an **app password** named "Metatron" (myaccount.google.com/apppasswords). It is shown
     once, 16 letters, so copy it straight into the panel in the next step;
   - in that account's Gmail, **turn on IMAP** (Settings → *Forwarding and POP/IMAP* → *Enable
     IMAP*).
5. **In the Metatron app: ⚙ → Google account** → the dedicated address and the app password →
   *Continue* → two permission screens:
   - **"read my calendar and mail"** is required to connect. That is her `correspondence_read`
     record: it covers what other people wrote to her reaching Vertex.
   - **"learn how I write"** (tone profiling) is optional. Her call, withdrawable any time from the
     same panel.

   → *Connect*.
6. **Expect "Connected — found N calendar(s): …"** with her shared calendars named. If it fails,
   the panel names the specific step to fix (wrong password, IMAP off, 2-Step off). Fix it and
   retry; nothing is saved until both checks pass.

### (b) Her own Gmail — the steps

Steps 4–6 of (a), on her own account. Steps 1–3 are not needed.

### Work accounts

- **Google Workspace** connects the same way *if her employer allows app passwords*. Many turn
  them off. If the app-password page says it is not available, that is the reason.
- **Microsoft 365 / Outlook** cannot connect yet: it needs Mark 2's OAuth route (settled, not
  re-proposed: `SESSION.md` § Do not re-open). **Interim for a work calendar:** if it can publish
  an ICS link, she subscribes to it *in her Google Calendar* (Other calendars → + → From URL). It
  then arrives through her Google connection like any other calendar. Work mail stays out.

### Claude verifies on the VM, read-only, after she connects

- `config/personas/iva/caldav.yaml` and `email.yaml` show `enabled: true` and **no password**.
  `credentials.yaml` exists, mode 600.
- Her `consents.json` now holds `correspondence_read` (and `tone_profile` if she ticked it).
- `.venv/bin/python -c` calling her calendar read through the tool returns her events. Name the
  calendars back to her and let her say which are hers, which are shared and which to ignore
  (the interviewer asks too).
- Nothing of hers appears in `git status` on the VM: `git check-ignore` covers her files (plan
  § 4.10, 1a).

## Not in this session

- **Capture fidelity ("show it what it missed")**: its own planning session, prompt above.
- **A real Sign out in the app**: the next build (`DEV_BACKLOG.md`).
- **Reply latency**: `archive/handoffs/2026-10-28-reply-latency-defer-thinking-cache-prompt.md`.
- **The VM's service account can control the whole project**, plus Mike's SSH passphrase,
  Time Machine encryption and 2-step verification: all in `[DB-1029-20]`.
- **Day planner step 2's live checks**: `[DB-1029-01]`, one command.

The VM line every read uses (read-only unless stated):
`gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command='cd ~/multi-model-mcp && …'`

Another chat may be working in this tree. `git diff` every file before staging, and never stage
another session's lines.

Close with `/archive`.
