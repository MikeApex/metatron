### 2026-08-29 (the confirm drain — four items close live, the deploy that wasn't, and intake goes on) — `DEV_BACKLOG.md`, `archive/backlog_closed_2026-08.md`, `archive/handoffs/2026-08-30-red-session-four-prompt.md`, `data/personas/mike/intake.yaml` (VM, Mike's edit) — commits `9805662` + close-out — **deployed by Mike mid-session and again at close**

**The session opened on a wrong premise, believed by both parties: Mike said the deploy of
`78aeb4f` was done, and the VM was on `398c575`.** Verified before anything else ran — the VM's
HEAD was four commits behind, so session ③'s entire batch (email surfacing, judgment gate,
decline guard, asked-state) was not live. Mike ran `./deploy.sh` in-session; VM confirmed on
`c1ee928`, `/health` ok, one live exchange coherent. Lesson re-learned, cheaply this time:
*verify the deploy against the VM's HEAD, not against anyone's memory of having deployed.*

**The interactive confirm drain closed four items on live evidence** (all in
`archive/backlog_closed_2026-08.md` § Closed 2026-08-29): profile-rewrite guard `[DB-0815-05]`,
dictation readout `[DB-0809-16]`, reconnect doubling `[DB-0810-01]` (both environments, plus the
multi-device broadcast set), offline page `[DB-0803-05]` (real outage test, server stopped live).
The decline path `[DB-0827-01]` produced its live decline (13:05:53, record retained, re-propose
guard held on the follow-up turn) — **left open solely for the 18:24-run tail**, which rides Red
session ④.

**The drain's failures were more valuable than its passes.** (1) Two apparent client failures —
a decline that didn't land, a canned "I can't help with that right now" replacing a legitimate
amended reply — were both **one stale cached `index.html`** in Mike's browser; hard refresh
cured both. (2) *"Now set it back to Iva"* was resolved by the Coordinator to a **declined
email** instead of the just-discussed rename: unrequested re-proposal (declined again),
a false "rename done" claim (no `write_contact` call), and a fabricated "user reversed his
decline" log entry — filed as the **fifth instance on `[DB-0826-01]`**, with the system's own
`ROUTING_MISS` event self-diagnosing it. (3) The 13:00 exchange wrote *"user sent an email to
Iva"* into the day log while the send sat ungated-unapproved — **new item `[DB-0829-01]`**
(Mike's instruction): the receipt enforcer corrects the user-facing text but nothing corrects
the same-turn log dispatch. Also observed: the `FALSE_ACTION_CLAIM` detector (`e673330`) did
not fire on the unbacked rename claim — plausibly satisfied by the *other* write-family call in
the turn; noted in `[DB-0829-01]`'s adjacent line rather than filed separately.

**Intake went live** — Mike created `config/personas/mike/intake.yaml` (`enabled: true`, one
line; the template supplies the rest, extractor stays off behind `[DB-0820-03]`'s eval gate).
First sweep 13:54: 24 messages, 1 promotion, 23 unclear surfacing — correct cold-start shape.
`[DB-0822-09]`'s confirm and `[DB-0820-03]`'s corpus accumulation both now run on real mail.

**Decisions.** The `/backlog deep` triage table (8 Inbox entries) and the three `@session`
decisions were presented and **parked by Mike until capstone close** — rulings live in the Red
④ prompt's step 5. Ruled immediately: the three calendar duplicate pairs (Mover's/Arbitration,
Apex ×2, Mousetrap) are real duplicates, keep either — execution closes `[DB-0809-21]`.
The CRM sweep was **built in a parallel window** (`f75a338`), overtaking `[DB-0827-03]`'s
plan-re-review gate by Mike's own hand; it deployed with the close-out deploy.

**Machine log swept 71 → 64**: recreation_hobbies' tool denial cleared by the grants pass
(`routing_cloud.yaml:235`), four referent events pointered into `[DB-0826-01]`, both
FALSE_COMPLETION claims accounted (enforcer working; residue = `[DB-0829-01]`), the empty-label
event pointered to `[DB-0827-07]`. Kept: the dental-forwarding cluster (rides the untriaged
Inbox), the re-ask corrections (tomorrow's re-measure is their confirm), the ×1
agent-named-itself discretion slip (check-5 evidence).

**Rejected in-session:** re-verifying `## Now` by worker fan-out (every item's evidence was
hours old); filing the detector gap as its own item (Mike not asked); deleting the
dental-forwarding machine entries (their Inbox twins are untriaged, so the pointer would dangle).

**Next session is written:** `archive/handoffs/2026-08-30-red-session-four-prompt.md` — the
re-measure, the `[DB-0822-08]` decision, the clock-gated confirm drain (incl. the unobserved
18:24/20:00 runs), the parked synthesizer `source` line, and the capstone close-out review.
