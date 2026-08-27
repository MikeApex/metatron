### 2026-08-27 (three gates close the ask-vs-assert cluster, and ZDR is refused) — `7069ea1`, `1b040bd`, `c6b21b0` — **`7069ea1` deployed mid-session; `1b040bd` and `c6b21b0` owe a deploy**

**Incoming handoff:** `archive/handoffs/2026-08-22-contact-tests-and-repair-prompt.md` — finish the
contact tests, repair Steven's record, answer two owed questions. Run across 08-22 and 08-26/27 with
Mike at the app and this session reading the VM's traces live. That pairing is again the method
finding: **every claim read out of a trace held; the two claims inferred from a reply's wording were
both wrong.**

**The cluster this closes was always one fault wearing three costumes: the model asserting where it
should have asked or checked.**

1. **`write_contact` gated creation but not update.** The premise in the code — *"an update by
   contact_id is a deliberate act on a record the caller already identified"* — failed live on
   08-22. Asked to *"add Stephen Ashworth"*, the model decided Stephen **was** the existing Steven,
   called `write_contact` with his id, and renamed a real friend's record. Twice, consecutively, no
   prompt shown. Updates are now gated, but **only on a change to an identity field** — enrichment
   stays ungated, so no tap appears in front of routine writes. The gate cannot ask *"did the user
   choose this id?"* (it is not told), so it asks the answerable question: *is this write about to
   change who the record is?* `contact_id` joined the approval fingerprint.
2. **The evening ritual was injected into every session.** Franklin's 13 virtues went out at 16:27,
   18:24, 19:28 and 20:00 on 08-21; only 20:00 was the job. `session_kind()` matches the turn
   against the persona's **own configured** `evening_close` prompt read from `scheduler.yaml` — not
   a literal, which would go stale silently the first time Mike reworded it on the VM.
3. **The Synthesizer reported a gated action as finished.** `merge_contacts` correctly returned
   `PENDING_CONFIRMATION` and merged nothing; the reply said *"That's done. I've merged the
   records."* `enforce_pending_receipt()` reads what is pending from the confirmation store —
   server state — and replaces a reply that claims completion. **The model was already out of the
   consent path and is now out of the report path.**

**Believed true earlier, wrong — five, and four were mine.**

- **"The deploy shipped the fixes."** It shipped nothing: the work was never committed, so
  `./deploy.sh` pushed the tree as it stood. Proved by the 20:35 check-in reciting the full virtue
  list. **A fix that is not committed is not deployed, and "I made the change" is not the same
  claim.**
- **"`[RETRACT]` then the corrected text"** — the first shape of the option-1 fix. `[RETRACT]` is
  terminal on both transports (`core/server.py` breaks its loop; the client nulls the bubble), so
  the correction was computed, recorded in the trace, and discarded on the wire. Mike saw *"I can't
  help with that right now"* — a refusal, the worst possible rendering of a message whose whole job
  is to say the action is waiting on him. Replaced by `[RETRACT_WITH]{text}`, one marker carrying
  its own replacement.
- **"The merge completed before approval."** It did not. The gate held; the model lied about it.
  Finding (3) above exists because the trace was read instead of the reply.
- **"The handoff's third gap is the instructed-but-unbuilt class."** The reply had offered to
  delete a contact, and no agent file mentions deletion — the model improvised the capability from
  nothing, which `scripts/check_agent_tools.py` structurally cannot catch.
- **Test 4 is not a test-design problem.** Three phrasings, three refusals to call the tool; even a
  zeroed UUID was reasoned about rather than passed. Every tool it can reach handles bad input
  gracefully **by design**, so the red flag is unreachable from conversation. `[DB-0810-07]` closed
  on that basis at Mike's agreement rather than kept alive with an unrunnable exit.

**Decisions.**

- **Merge confirmation is toggleable** (Mike): `proactive.crm.merge_auto_accept`, default false,
  read in Python, written by no tool. Recorded in three places that it is defensible **only while
  `unmerge_contacts` can reverse a merge from its snapshot** — if that goes, the toggle goes.
- **Google refused the ZDR opt-out.** The 2026-06-18 amendment's "verified ZDR" premise is now
  settled false rather than unverified. Mike ruled the `mike` persona keeps running on Vertex under
  the terms that do apply (flagged-only logging, ≤90 days, never training): *"Google Calendar
  already has my plans, and Google has my email correspondence. I'm gating it personally."*
  Recorded in `ROADMAP.md` § Section 0 with its single-user expiry, and in `docs/INFRASTRUCTURE.md`,
  which is the status authority. **Stated plainly there and worth repeating: real user data had
  been reaching Vertex throughout the period the premise was assumed. The ruling makes that a
  decision, not retroactive compliance.**
- **`[DB-0826-02]` (profile-photo contact enrichment) pre-cleared** against that ruling, deliberately
  and with its reasoning, so the § Section 0 tension is not re-litigated by a future session.
- **`## Recent sessions` removed from `SESSION.md`** — it duplicated this file. `/archive` step 3
  updated so it is not recreated; the ceiling check still measures the heading so recreation trips
  the budget.

**Found and filed, not fixed:** `[DB-0826-01]` — *"Undo that merge"* routed to `work_vocation`,
which searched for a Prudential/Apex **git** merge; the Synthesizer then had `relationships`
hand-reconstruct the record, which `relationships.md` explicitly forbids. `[DB-0827-01]` —
**declining a confirmation does nothing**: `POST /confirm` is approve-only, there is no reject
endpoint and no client handler, so a declined prompt returns every poll until the TTL and its only
exit is approving what you just refused. Present since 08-19, unnoticed because every prior test
approved.

**Tests:** 21/21 contact dedup gate (7 new), 30/30 merge guard (5 new), 17/17 pending receipt (new),
11/11 evening ritual gate (new); five other CRM suites unchanged and green.

