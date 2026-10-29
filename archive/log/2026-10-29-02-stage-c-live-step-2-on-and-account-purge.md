### 2026-10-29, second (day planner Stage C live on the phone, step 2 switched on, and deleting an account now needs Mike at a terminal) — one session across two chats (10-28 `cc3393e6`, resumed 10-29) — `a52b8ab`, `ec63e40`, `c8e6f7f`, `898f55c`, `6a3fd86`, `fac4c4c`, `474873c`, `86fa646`, `32115b6`, `3d3524a`, `d91a25f`, `fe5847b`, `9a9e73a` — **through `3d3524a` deployed by Mike (10-28 15:30 and 10-29 10:49) and the APK sideloaded; `d91a25f`, `fe5847b`, `9a9e73a` committed, not deployed**

**Incoming handoff:** `archive/handoffs/2026-10-27-day-planner-stage-c-push-and-step-2-prompt.md`,
now consumed except § 3 (the boys' times and the 10-27 leftovers, below). The 10-28 chat ran out
of room before `/archive`; this chat picked it up from its transcript with no recap needed.

**Stage C, built and live (10-28).** A nudge reaches the phone with the app closed: Google carries
a content-free ping with a random id, the app fetches the text from the VM, and each task gets
Done / Not yet / Skipped (`ec63e40`); Not yet offers Tomorrow (`c8e6f7f`). Live: Done on a
notification closed the ledger task with evidence "from the notification"; a ping to a phone
locked ~9 min was fetched in 2 s.
- **Firebase lives in its own project, `metatron-push`** (Spark, no billing, `474873c`). Adding
  Firebase to a GCP project **cannot be undone**, which I flagged only after Mike was on the terms
  page; a read-only check showed it had not been added to `metatron-ai-499810`. The VM's existing
  service account is granted the FCM sender role there, with its own `FCM_CREDENTIALS` setting, so
  leaving Vertex costs one `.env` line. The app tells Google no more than delivery needs (`fac4c4c`).
- **Safari held 35 push subscriptions for one browser**, re-subscribing on every page load and
  never telling the server; every check-in went to all 35. Pruned to the newest (VM backup
  `data/push_subscriptions.json.bak-2026-10-28`), and the page now keeps one (`86fa646`).
- **Reshuffle thinking: 6,000 → retry at 0 on a cut-off → 0 by default** (`a52b8ab`, `898f55c`,
  `6a3fd86`). Head-to-head on a day with an essential the code plan could not place: 3.8 Flash
  at 6,000 fitted it **0/3** (and overshot to 12.8k); at 0, **2/3** in 4–9 s; Flash-Lite 1/3,
  and once claimed a fit it had not made. Thinking made it more cautious, not better.
  **This contradicts 10-27**, when full thinking fitted the essential every time; nine runs on one
  day do not settle it, and live outcomes are logged. *Rejected:* **Haiku**, which Mike suggested.
  It is another vendor, so his 08-26 basis ("Google already has my calendar") does not cover it
  and Iva's consent names Vertex. It is also not cheaper than Flash at 0 (~$0.005 a call).

**Delivery is not yet reliable, and an earlier diagnosis was wrong.** On 10-28 one fetch in four
never reached the VM. I blamed Tailscale sleeping on the phone; it was connected and Unrestricted.
A locked-phone test then passed, and I concluded deep sleep was not the cause. **By 10-29 10:01 it
was 5 of 11**, and every failure followed long idle (18:01, then 07:31, 08:11, 10:01), so idle is
not ruled out. The phone now retries three times and reports a content-free reason to
`push_log.jsonl` (`32115b6`, sideloaded 10-29 10:09). None of the 5 ran on it, so the cause is
still unknown. Notifications also show their time now.

**Step 2 on (10-29, `3d3524a`): `nudges` and `owns_checkins`.** Mike's live job is
`companion_checkin`, read on the VM, so `replaces_jobs` stands. **Two scheduler suites read the
live switch file** and failed 12 checks on the correct skip; both now pin it. Five live checks need
days to pass, so they became one read-only command (`scripts/check_day_plan_step2.py`, `9a9e73a`)
and `[DB-1029-01]`, due 10-31. Mike asked for the item; I added the script. I could not offer to
check by myself in a few days: my scheduler only lives as long as this chat.

**Stage C had left the multi-user isolation suite red.** Its four new routes were never classified,
and that suite exists to catch exactly this. All four bind through `request_persona`; they are now
classified and each returns 403 to another user's name (`d91a25f`).

**Deleting an account now needs Mike at a terminal (`fe5847b`).** He asked to remove the trial
accounts entirely, and for a human approval before any account data is deleted. No code deleted an
account (`disable` keeps everything); a VM shell deleted with no gate. `accounts.py purge` is the
only deletion. It takes a disabled account only, at a real TTY, with the username typed back, and
never `mike`/`admin`. It runs in a set order and is idempotent, writes a content-free
`purge_log.jsonl`, and is unreachable from any route, tool or job. `.claude/settings.json` denies
Claude Code any command naming it, probed with an inert `echo`. That also blocks a commit message
containing the phrase. Tests: 6, and each gate, when removed, fails its own check. **Honest limit:**
anyone with an interactive VM shell can still `rm`, and Mac backups keep copies until they rotate.
*Rejected:* an environment-variable bypass for tests, because it is the same bypass an agent could
set. A pseudo-terminal stands in for the person instead.

**Outgoing:** `archive/handoffs/2026-10-29-multi-user-stage-5-close-and-iva-prompt.md`: check 6
first (due today), check 2 on a fresh account, disable, Mike purges, then prepare the Iva
walkthrough. It needs `fe5847b` deployed first. **Still owed from the Stage C handoff § 3:** the
boys' school hours and bedtimes (two numbers each, Mike to say them in the app); the J2/J3
day-shape phrases; whether three agents writing one task in a turn is worth an item; a salience
read of a brief and a close with the plan on.

