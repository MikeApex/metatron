### 2026-11-21, second (goal–task network phase 1 checked on three live days — four misses fixed and deployed, checks 2–4 cleared, the event-move check under way) — `tools/day_plan.py`, `core/orchestrator.py`, `config/modules/day_plan.yaml`, tests — `52a1c8b` — **deployed by Mike 11-21; VM at `52a1c8b`**

**Incoming handoff:** phase 1 built and deployed 11-18 (log § 11-18 fifth). Mike asked how many of
the four live checks Claude Code could run itself, from existing activity or by starting them.

**Read on the VM, read-only (IAP SSH), 11-18 21:10 → 11-21.** Working: three preps opened by
themselves at deploy (Bupa pre-authorisation, echo travel, Aisha's reply) and were placed, nudged
and closed when their events started; Show and Tell's was refused, its event past; 07:00 and 19:30
nudges were carried into the 07:30 brief and the 20:00 close; the 11-19 brief said "the George
School donation has slipped three days"; briefs carried one new finding, not a flood.

**Four misses, fixed in `52a1c8b`** (plan § 14): a 09:35 "leave now" for a 10:00 meeting was held for
the 10:00 session and never said (`_ref_done` reads an event ref as a closed task); slips were
stamped asked at render — four on 11-20, none said; nudge wakes spent new findings' offers unsaid;
the Bupa prep lost "before 15:30" on the day (the `precursor_by` branch returned first). Plus
`manny_school` (Sun 16:00) missing from `shield_jobs` — now every `agent: coordinator` fixed job
shields. **Fable 5.1 review of the fix: 2 structural + 4 local; 5 fixed, 1 noted** (stamp taken
before the confidentiality filter, as `note_raised`'s already is). The review changed the design
twice: a "leave now" is never held at all (the first fix would have said it after the meeting
started), and "said" needs the task's words AND words of that question, with slips rotating.

**Checks 2 and 4 replayed on a throwaway copy of `mike`'s data on the VM** (`/tmp`, code + data +
persona config copied, every meter stubbed, deleted after): 17/17 — two replay-script checks
miscounted semicolons in line headers; the lines were right.

**Check 1's event move, live:** Mike made a Boots passport-photo event (22 Nov 14:00). Said in chat,
the precursor became a plain task with no event link; fed by email, Logistics filed the finding and
the prep opened linked to the event, due the evening before, placed 13:00 with nudge and check.
Mike moved the event to 23 Nov; a read-only watcher is polling for the prep to follow. **Three gaps
for phase 2, written into its prompt:** a chat-stated precursor is not linked to its event; a prep
and that chat task are two tasks for one job (`_same_commitment` is strict); a precursor written as
a list ("Completed renewal form and old passport") is used verbatim as the task title.

**Believed true and wasn't.**
- SESSION.md (another window, 11-21) said phase 1 went live "unannounced with the capture deploys
  (11-20/21)". Mike deployed it 11-18; the plan log's first prep is 11-18 21:10.
- The same handoff said capture (`f878ead`) was not deployed. Mike's 11-21 deploy of `52a1c8b`
  carries it — capture is live from 11-21.
- Phase 1's R10 test "proved" finding #5 fixed; live, travel nudges were still lost. A deterministic
  test of the shield said nothing about refs that are events, not tasks.

**Decisions.** Phase 2 runs on Opus at **high** effort (Mike asked; not medium — the agent file and
Synth's vetting conduct are judgement-heavy; not xhigh — the plan is already Fable-reviewed). Phase 2
may start while the event-move check finishes; a defect it finds goes to the phase 2 chat, not
edited here in parallel.

