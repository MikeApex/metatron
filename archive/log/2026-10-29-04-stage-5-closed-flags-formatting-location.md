### 2026-10-29, fourth (the second-user build's Stage 5 closes: a scheduled session no longer raises clinical flags, replies keep their shape, location consent is per user, the trial accounts deleted) — `8dcb290`, `0167a7a`, `2af90ba`, `3cca677`, `60f1cd4`, `ebfe50b`, `0b143a9` + this close-out — **through `ebfe50b` deployed by Mike in-session; `0b143a9` committed, not deployed**

**Incoming handoff:** `archive/handoffs/2026-10-29-multi-user-stage-5-close-and-iva-prompt.md`,
now consumed. Mike asked first for a reconciliation against the 10-28 log. It held, with five
gaps: the trial accounts barely exercised step-2 nudges; M3 measured a load nobody will run;
Stage 4 step 5 had never been recorded; two users were given the same `BLD-1028-01` id; and push
idle-failures belonged in the Iva walkthrough.

**Stage 5: all seven checks pass.** Check 6 items 1–2 were clean, and step 2 on a calendar-less
user worked. Stage 4 step 5 passed: Mike's tone shape gave 102 "written" results and no "not
permitted". The deploy step was moot, since `fe5847b` was already on the VM. Check 7: four
accounts disabled by Claude and **deleted by Mike** (`purge_log.jsonl`: four lines, 49
conversation rows); no folder, row or unit remains.

**Check 6 item 3 failed, and the cause was a loop, not wording.** After `trial_2026_10c`'s
crisis probe, eight scheduled sessions in 22 hours each recited the full support-number block to
a user who never replied. Mental Wellbeing re-raised `CLINICAL_CONCERN` + `ESCALATION` from its
own earlier log entries, Physical Health invented "severely depleted", and the Synthesizer did
what its file says. Proposed: a cadence cap plus fixed-wording check-ins. **Mike instead
curtailed flagging until the agent rewrite**: on a turn with no user words, Mental Wellbeing's
clinical items are dropped and no thread or escalation is written (`8dcb290`). Verified live at
14:03, with no flag and no block. *Rejected:* the session-start clinical alert and flag
deduplication (curtailed with the rest).

**Check 2 closed on findings (Mike).** The interviewer's own sample questions were suppressed by
the leak filter as instruction text (`0167a7a`: questions now exempt, like quoted lines on
10-28). Facts were saved in-turn for 5 of 8; the misses were work hours (twice), weekend times and
a slump. The card read "Save your purpose" with no file named. **Mike's directions:** drop
theme-at-a-time; bullets for several questions, Synthesizer included; one register per turn,
since a purpose mixed with logistics was "off-putting". The app had collapsed reply line breaks
and shown `>`/`**` raw; `replyText()`/`speechText()` fix that (`2af90ba`). The approval colon and
the doubled waiting line are fixed (`3cca677`).

**Location: three wrong turns, stated plainly.** (1) A yes in the interview never reached an
app that asks once per load, so each interview reply now re-arms one more ask. (2) **The choice
was stored per browser**, so one account's stored value blocked another's. Made per user
(`60f1cd4`), but **my migration handed the old value to the first account to sign in, which was
trial_1029**, and the fix failed again. The value is now dropped and each user's server answer
decides (`ebfe50b`). (3) The help said "icon beside the address", which Safari lacks. It now names
Safari's Settings → Websites and the device-level Location Services step (`0b143a9`). A private
window cannot turn on notifications. Mike asked that every permission explain itself, so the mic
and notifications help works the same way. The app side is verified; no Mac location reading
arrived.

**Security (Mike's question).** Access to the VM needs IAP plus his Google identity (the only
Owner) plus one SSH key. The two `default`-network SSH/RDP rules open to `0.0.0.0/0` were deleted.
The VM service account's Editor + billing roles, the passphrase-less key, Time Machine holding the
key and gcloud token, 2-step verification and a lost-device drill all went into `[DB-1029-20]`.

**Outgoing:** Iva onboarding at the weekend, with full account linking
(`archive/handoffs/2026-10-29-iva-account-walkthrough-prompt.md`; APK rebuild first). The
capture-fidelity planning session ("show it what it missed", Mike: build sooner) is
`archive/handoffs/2026-10-29-capture-fidelity-plan-prompt.md`. **M3 restarts on Iva's approval
day.** The duplicate-request-id question was never answered; it is still open.

