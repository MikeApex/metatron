# Capstone cluster review — deep-run conclusions and progress tracker
*Written 2026-08-27 at the close of the `/backlog deep` planning chat. This is the handoff
artifact: the deep run's Parts 1–3 with status updated through the same-day attack run and
Mike's deploy. A fresh chat continuing the capstone plan starts here (after `/metatron-code`).*

**The stated goal (Mike, 2026-08-27):** finish the current build-out with existing features
(email, CRM, research, geomapping/transit, etc.) in reasonable working order — address errors,
complete core-functionality build-outs, then begin full testing while the code-dominant rebuild
question proceeds separately. National Rail and geolocation are **first-draft features** by his
ruling; Cluster H below is the parked-for-rebuild bucket he has seen once and not yet finally
ruled on.

---

## Part 1 — Deep-run findings (2026-08-27, all verified against code/VM, not descriptions)

1. All 9 then-`## Now` items verified **real**; no stale premises. One drift repointed
   (Diarist dispatch → `core/orchestrator.py:4660`).
2. `[DB-0822-08]` (nothing proposed, only reported): `synthesizer.md` shrank 52.4k → 41.9k bytes
   in the 08-27 audit but the Proactive Anticipation section is untouched — **re-measure
   adherence against the post-audit file before writing any fix** (one scheduled-run day of
   traces).
3. `[DB-0822-09]` (email discarded): cheaper than filed — intake queue + per-agent grants exist
   (disabled); missing only the Synthesizer surfacing rule + coordination-check instruction
   (Red, agent files).
4. Machine-log ⚠ diagnosed: Coordinator filled its USER_CORRECTION slot with a bare
   `CLARIFICATION_NEEDED:` label 33× since 08-18 → filed `[DB-0827-07]`, fixed same day.
5. The 10:00 anticipation pass fired correctly on first run (trace `56ec3ec9`); its one blemish
   (stale "Teams link still missing") is the `[DB-0822-06]` carried-state class — folded in as
   its fourth instance. Observation item closed.
6. Thread expiry `[DB-0814-02]`: `expired_open_threads` still 0 after 12 days — audit-line data
   source built same day; measure after a few deployed days.
7. Mousetrap duplicate-calendar machine entries (08-25) are almost certainly the live candidate
   `[DB-0809-21]` was waiting for — confirm emitter, Mike resolves the three duplicate events.

## Part 2 — Dispositions (all applied 2026-08-27, Mike approved)

- Inbox emptied: session-opening instruction **closed** (already in force — it is the
  `morning_brief` template prompt); anticipation observation **closed** (done); ZDR ruling →
  `[DB-0827-08]` (@session + @waiting Google ~09-05); Accountability Index → `[DB-0827-09]`.
- `[DB-0822-01]` merged into `[DB-0820-05]` (one Pro-routing decision, `due: 2026-09-15`).
- Machine log swept 46 → 32 with pointers (then 32 → 50: see the recovered events below).
- `[DB-0818-04]` National Rail + `[DB-0815-12]` real-time location promoted to **first-draft
  features** (Mike). Darwin API key registration is Mike's; location's privacy-tier design pass
  is @session.

## Part 3 — Functional clusters, status as of 2026-08-27 (post-attack, post-deploy)

Tier = change tier. Est = rough Claude wall-clock. **(M)** = Mike's minutes.
Status: ✅ closed · 🔶 built+deployed, awaiting one live confirmation · ⬜ open.

### Cluster A — Scheduled-session hygiene
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| 🔶 | [DB-0822-05] | Journal recorded days never spoken — dispatch gate built (`e6bde3d`) | Green | done; confirm: one scheduler-only day journal stays empty AND one answered check-in still journals |
| 🔶 | [DB-0827-07] | 33 empty CLARIFICATION_NEEDED events — null-label filter built (`24dabae`) | Green | done; confirm: one clean day in the VM quality log |
| 🔶 | [DB-0822-06] | Stale state as fact — age annotation built (`cbd5ca3`); **intraday half built + derived-count half retired as stale-premised (second attack, `4cc9e3e`)** | Amber | done; confirm: one same-day case post-deploy |
| ⬜ | [DB-0822-07] | Two jobs fire 7 min apart — suppress the collision | **Red** (`core/scheduler.py`) | 1–2h supervised |
| ⬜ | [DB-0809-02] | Same unanswered question re-asked by every job | Red @session | decision + 2–4h |

### Cluster B — Action integrity
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| 🔶 | [DB-0827-01] | Decline built (`0f8f528`) — **re-propose guard built too (second attack, `4cc9e3e`)**; confirm: one live decline that stays declined through the next scheduled run | Amber | done |
| 🔶 | [DB-0815-11] | False-action-claim detector built (`e673330`), events collected | Amber | done; **@session policy half open** (may `write_persona` self-apply?) |
| ✅ | [DB-0827-05] | ROUTING_MISS collected again (`5b444be`) — closed, +3 more types registered on main | Green | — |
| ⬜ | [DB-0826-01] | "Undo that merge" referent failure — **@waiting MET**: recovered ROUTING_MISS history holds 3 prior instances (08-10 "previous request", 08-15 "Approved", 08-18 "read that back") | Red (`coordinator.md`) | ~2–3h |

### Cluster C — Email/intake capstone
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| ⬜ | [DB-0822-09] | Email read then discarded — Synthesizer surfacing rule + coordination check; intake plumbing already exists | Red | ~half day |
| ⬜ | [DB-0820-03] | Intake extractor off until eval — (a) corpus labeling is **(M)**, then eval+review | Amber | 2–3h + (M) |
| ⬜ | [DB-0820-04] | Hostile email at the extractor (advances B1b/A7) | Amber | 1–2h, after intake on |

### Cluster D — CRM capstone
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| ⬜ | [DB-0827-03] | CRM sweep — gated on Mike's plan re-review **(M)**, then Opus build | Red | ~half day |
| ⬜ | [DB-0818-08] | Provenance tiers (decided: build both halves + hedge test) | Amber/Red | ~half day |
| 🔶 | [DB-0818-05] | Asks which Bill twice — resolution store built (second attack, `6b0a6d5`); confirm: ask-answer-ask-again, no second question | Amber | done |
| 🔶 | [DB-0818-06] | 24 non-facts in the wisdom store — per-entry proposal filed (`archive/plans/wisdom_store_cleanup_proposal_2026-08-27.md`); execution is Mike's review + a VM session **(M)** | Amber | proposal done |

### Cluster E — Cost & model routing
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| ⬜ | [DB-0820-01] | Caps → $100/$175 at Sept reset (evidence in) | chore | 15min, `due: 2026-09-01` |
| ⬜ | [DB-0820-05] | Which agents get Pro + Step-6 caching (A4-gated) — one decision | @session + Amber | decision + 2–3h, `due: 2026-09-15` |

### Cluster F — Verification waits (deploy DONE 2026-08-27 — these now drain on ordinary use)
[DB-0822-10] one afternoon turn without the virtue list + one 20:00 that carries it ·
[DB-0810-01] one reconnect · [DB-0815-05] one contact correction · [DB-0809-16] one dictated
turn · [DB-0809-21] confirm Mousetrap = reconcile candidate, Mike resolves the 3 dup events
**(M)** · [DB-0803-05] one online load then kill-server reload (deploy now done) ·
[DB-0814-02] read `context_audit.jsonl` after a few days · [DB-0810-05] data-gated (thin
mailbox). ~20–30 Mike-minutes total, spread over ordinary days.

### Cluster G — Safety & security remainder
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| ⬜ | [DB-0808-11] | Function jobs skip quiet hours — would push at 3am | **Red** (`core/scheduler.py`) | ~2h supervised |
| ⬜ | [DB-0808-14] | Psychiatric meds rank same as statins — scoped, confirmed live, **Red half remains** (spec: `archive/plans/medication_ranking_spec_2026-08-27.md`); owed A4 re-run DONE, PASS 3/3 | **Red** (`physical_health.md`) + Green follow-up | ~1h supervised + ~1h |
| ⬜ | [DB-0804-02] | B4 graceful-failure wording + security remainder | Amber/Red | ~half day |
| ⬜ | [DB-0808-06] | Clinical threads can never close — escalation design | postpone? | — |

### First-draft features (Mike's 2026-08-27 promotion)
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| ⬜ | [DB-0818-04] | National Rail backend (Darwin) — **blocked on Mike registering the API key (M)** | Amber | ~half day once key exists |
| ⬜ | [DB-0815-12] | Real-time location signal — @session privacy-tier design pass first | Red @session | design + build TBD |

### Cluster H — Parked for rebuild / not-capstone (RULED at the 2026-09-02 close-out review)
**No longer awaiting a final ruling — the 09-02 review dispositioned its graduates and Mike
confirmed the rest stay parked.** Departed the cluster: [DB-0822-08] (closed 2026-09-02 on the
re-measure — the post-audit instruction proposes; no fix written) · [DB-0827-09] (graduated to
built-and-live 08-28/29; only its live-leftover confirm remains) · [DB-0810-11] (ruled: rides
the code-dominant rebuild notebook, decided before A8) · [DB-0814-03] (ruled: parked
post-capstone, scope-against-obligations first). Still parked, unchanged: [DB-0808-09] turn
economics · [DB-0827-06] Synthesizer compression · [DB-0815-13] semantic retrieval (trigger
unfired) · [DB-0815-02] Bulgarian STT (held) · [DB-0820-02] APK file save · [DB-0819-01]
subscriptions · [DB-0809-08] missed-opportunity metric · [DB-0826-02] contact enrichment ·
[DB-0827-04] field promotion (gated) · [DB-0818-09] plausibility check (design with
[DB-0818-08], which itself moved INTO the close path — session ⑦).

### Decisions batch — one working session covers all
ZDR amendment `[DB-0827-08]` (`due: 2026-09-05`) · 39 tool grants `[DB-0810-03]` (**blocks A7
check 10 — capstone path**) · ritual fix shape `[DB-0809-02]` · `write_persona` self-apply
`[DB-0815-11]` · Pro routing `[DB-0820-05]` · knowledge seeding `[DB-0818-07]` (A7-relevant) ·
Accountability Index scope `[DB-0827-09]` · location privacy tier `[DB-0815-12]`.

---

## Remaining investment (post-second-attack, 2026-08-27 late)

The second attack run closed the open halves of [DB-0822-06]/[DB-0827-01], built [DB-0818-05],
filed the [DB-0818-06] proposal, and specced [DB-0808-14] to the Red line (A4 re-run PASS 3/3)
— merged `bb9ebdb`…`4cc9e3e`, **deploy owed**. Remaining: **~4–6h Green/Amber** (Cluster C
intake pair once Mike's VM edits land, [DB-0820-05]'s build half, National Rail once keyed,
[DB-0808-14]'s Green follow-up) · **the Red work with Mike** (scheduler pair, email surfacing,
CRM sweep, provenance, referent fix, medication schema — specs ready where noted) · **one
decisions session** (Mike prefers a single chat for the whole batch) · **~30 Mike-minutes**
draining Cluster F, now plus three more one-shot confirmations from this run.

## Suggested next sessions, in order
1. **One decisions session** (Fable, with Mike, single chat per his ruling) — the batch below;
   several cheap builds are gated behind it. The wisdom-store proposal review can ride along
   (it is a per-entry approve/amend pass, decision-shaped).
2. **Red pair in `core/scheduler.py`** (supervised): [DB-0822-07] + [DB-0808-11] together — same
   file, same gate-stack extraction shape. The medication schema edit ([DB-0808-14], spec at
   `archive/plans/medication_ranking_spec_2026-08-27.md`) fits the same supervised session.
3. **Email surfacing session** (Red, with Mike): [DB-0822-09], plus the [DB-0822-08]
   re-measurement read from a scheduled-run day.
4. **CRM sweep build** (Opus, after Mike's plan re-review) — [DB-0827-03], with [DB-0818-08]
   provenance either bundled or immediately after.

*Evidence trails: `archive/backlog_closed_2026-08.md` § Closed 2026-08-27 (both sections);
worker handoffs `archive/handoffs/2026-08-27-{session-hygiene,decline-path,routing-miss}.md`;
deploy by Mike 2026-08-27 evening.*

---

## Status update 2026-08-28 — the decisions session ran; the batch is 8/8 decided

**Session ① is done.** Every item in the decisions batch is ruled on and recorded in its
`DEV_BACKLOG.md` entry (the authority for each disposition). One closed outright:
ZDR `[DB-0827-08]` — Amendment 2026-08-28 applied in `ROADMAP.md` § Section 0, `tone_profiler`
cleared for anything Mike shares. The rest converted from decisions to build work:

- `[DB-0815-11]` write_persona: approval-gated (toggleable) + pre-write redundancy check.
- `[DB-0809-02]` ritual: focus-rule reading confirmed; asked-state memory + ritual ownership.
- `[DB-0818-07]` knowledge seeding: yes, bundled into the A4 run Step-6 caching owes.
- `[DB-0820-05]` Pro routing: coordinator-only, offline probe before any flip; Step-6 approved.
- `[DB-0810-03]` grants: all 24 live pairs ruled (six clusters; journals route through Diarist;
  LG `write_config` redirected). **One supervised Red pass builds it — A7 check 10 unblocks.**
- `[DB-0827-09]` Accountability Index: designed (c=both surfaces); audit filed `[DB-0828-01]`.
- `[DB-0815-12]` location: extra-sensitive zone abstraction; app modes 1+2, ping default OFF.

**Revised session order (Mike, 2026-08-28 — grants are quick, so batched, not their own run):**
② supervised Red session: the `core/scheduler.py` pair (`[DB-0822-07]` + `[DB-0808-11]`) **+ the
grants pass (`[DB-0810-03]` routing files + instruction-text edits + archive dedup) + Step-6
caching behind the full A4 run (with `[DB-0818-07]` seeding)** · ③ email surfacing + the
`[DB-0822-08]` re-measure, picking up the ritual's one Red Synthesizer line and any agent-file
proposals from the spinoff · ④ CRM sweep build (Opus, after Mike's plan re-review). A
Green/Amber spinoff chat runs the probe, write_persona gate, ritual code halves, index build and
location first draft concurrently. (M): BigQuery billing export toggle; caps `[DB-0820-01]`
due 09-01.

---

## Status update 2026-08-28 (evening) — the spinoff ran, merged, and DEPLOYED

**The Green/Amber spinoff chat delivered all five items in one run** (five worktree workers,
Fable review, merges `c082fb6`/`75a91d6`/`6451b51`/`029905e`/`ec774da`; archive commits
`42f17ed`/`172b7ca`); **Mike deployed the batch the same evening** and ruled on everything it
raised. Handoffs with the Red proposals: `archive/handoffs/2026-08-28-*.md`.

- **Cluster A:** `[DB-0809-02]` ritual halves 🔶 **built + deployed** (asked-state memory,
  nothing-new focus gate, ritual ownership; one scheduled-run day confirms — the same day
  serves `[DB-0822-08]`'s re-measure). Its Red Synthesizer line rides session ③.
- **Cluster B:** `[DB-0815-11]` approval gate 🔶 **built + deployed** (toggle, redundancy
  refusal). `[DB-0826-01]` is now **the confirmed referent fix path** — probe-measured
  (Flash-Lite 6/12 vs Pro 12/12 on the competing-referent suite), structural fix preferred.
- **Cluster E:** `[DB-0820-05]` probe run; **Pro flip DECLINED by Mike** (11s/reply;
  Coordinator redesign post-capstone makes a flip a temporary patch). Remaining there:
  the A4-gated Step-6 caching commit only.
- **First-draft features:** `[DB-0815-12]` location 🔶 **server side deployed**; the launch
  (Mike's APK sideload + VM zones file + the option-b zone-suggestion build) is **folded into
  session ② as item 5** — ready-to-paste prompt:
  `archive/handoffs/2026-08-28-red-session-two-prompt.md`. Vendor ruling refined same day:
  Places is queried by expected-place NAME only; coordinates never leave the machine.
- **Cluster H graduate:** `[DB-0827-09]` Accountability Index 🔶 **code half built +
  deployed** (counts ride the 05:40 rollup; CLI report on demand). Judgment gate +
  intentions-as-list (frequency → urgency) ride session ③; audit `[DB-0828-01]`
  `due: 2026-09-07`.

Session order ②–④ unchanged and next; ③ now carries the ritual Red line, the judgment-gate
proposal, the Diarist list-shape line, and possibly the location proposal-voicing line.

---

## Status update 2026-08-29 — session ③ ran; all Red work in the capstone is DONE

**Session ③ (the last planned Red session) landed everything it carried**: email surfacing +
coordination check (`[DB-0822-09]` both halves, A4 PASS 3/3 × three suites), the ritual Red
focus-block line, the complete judgment gate (`[DB-0827-09]`: judge file, tier-commented
routing, 05:45 job, intentions-as-list, Sunday retro wording — Amber half Opus-built,
Fable-reviewed). The 08-28 handoff sweep consumed the write_persona `source` rider; the
location proposal-voicing line was confirmed moot (the card is app-side). **Not landed,
deliberately:** the `[DB-0822-08]` fix — the re-measure day had not elapsed; procedure +
framed decision in `archive/handoffs/2026-08-29-re-measure-and-0822-08-decision.md`.
**VM deploy owed (Mike).** Remaining in the capstone: ④ CRM sweep build (Opus, gated on
Mike's plan re-review `[DB-0827-03]`) — no Red work rides it.

---

## Status update 2026-09-02 — Red session ④ ran: the verification pass, and the close path is ruled

**The buildout is finished; this session verified it against four live days of traces
(08-29 → 09-02) and Mike ruled the close path.** Seven items closed on evidence in one pass:
`[DB-0822-08]` (proposals now attach — 3-of-4 raises vs the 0-of-13 baseline; closed on Mike's
ruling, no fix written, the structural-gate design stays in the 08-29 handoff), `[DB-0809-02]`
(ritual halves confirmed — empty-delta runs short, questions asked once, virtues only at 20:00),
`[DB-0822-05]`, `[DB-0822-10]`, `[DB-0827-01]`, `[DB-0827-07]`, and `[DB-0809-21]` (calendar
dedupe **executed live** per Mike's keep-sets — six deletes, verified; emitter confirmed as
`tools/calendar_audit.py` via `daily_calendar_dedup_audit`).

**The verification also found the residue, which is the remaining capstone work:**

- **Cluster A:** `[DB-0822-06]` REOPENED in substance — the exercise hiatus (ended 08-23) was
  described three different wrong ways across 08-30/31/09-02, spanning the model migration; the
  code-computed derived-facts line is back on the table.
- **Cluster C:** `[DB-0822-09]`'s surfacing half FAILED its first live test (Death Cab tickets:
  coordination legs generated internally, nothing reached Mike). Related new bug: the two inbox
  jobs disagree about the same inbox (`[DB-0902-02]`).
- **Cluster B residue:** `[DB-0826-01]` referent fix (unchanged, last Red build) and
  `[DB-0829-01]` pending-logged-as-done, plus `[DB-0902-01]` (ROUTING_MISS recording successes
  since the migration).

**Rulings (Mike, 2026-09-02):** the 08-29 Inbox table triaged 8→0 (1 closed live, 1 closed on
evidence, 2 merges, 4 filed: `[DB-0902-03..06]`) — evidence in
`archive/backlog_closed_2026-09.md` § Inbox triage. The three `@session` items: `[DB-0815-11]`
policy half closed (the gate is the policy); `[DB-0810-11]` parked to the rebuild notebook;
`[DB-0814-03]` parked post-capstone. `[DB-0820-03]` intake corpus parked `due: 2026-09-09`.
The `synthesizer.md` `source` line: declined forever. **A4 re-run removed from the close path**
(before-Alpha requirement unchanged — `ROADMAP.md` § Section 0 pt 8 amended).

**The close path (Mike agreed): two final sessions, then full testing.**

- **⑤ Referent fix** (Fable, Red, Mike present): `[DB-0826-01]` — prompt at
  `archive/handoffs/2026-09-02-red-session-five-referent-prompt.md`.
- **⑥ Three-bug code session** (Opus, Green/Amber): `[DB-0829-01]` + `[DB-0902-01]` +
  `[DB-0902-02]`, with `[DB-0822-06]`'s derived-facts line and `[DB-0822-09]`'s surfacing
  diagnosis riding along where the inbox-job fix touches them — prompt at
  `archive/handoffs/2026-09-02-code-session-three-bugs-prompt.md`.

**The capstone closes at the end of session ⑦ (amended same day — see below).** Post-capstone:
the confirm clocks (`[DB-0828-01]` due 09-07, accountability's first real leftover ~09-03/04,
CRM sweep's first live digest) and the rebuild question before A8. The (M) items get their own
walkthrough session rather than waiting — see the same-day amendment.

**Amendment, same day (Mike's question at close: "why is the capstone not complete?"):** three
items from this plan's own "remaining investment" were never claimed by any scheduled session
and the 09-02 close path silently treated them as post-capstone — surfaced at his challenge:
`[DB-0818-08]` provenance (decided 08-28, unstarted), `[DB-0804-02]` B4/security remainder,
`[DB-0808-06]` clinical-thread escalation. **RULED same day: all three fold into a new session
⑦** (`archive/handoffs/2026-09-02-session-seven-capstone-remainder-prompt.md`) — ⑦ takes
`[DB-0804-02]`'s buildable-now slice and re-homes its E1-gated rest to Track B with Mike's
word in-session; **the capstone now closes at ⑦'s end**, after ⑤ and ⑥.

**Second ruling, same day — (M) items get walkthroughs, not waits (now CLAUDE.md § Mike-gated
work):** anything only Mike can do closes in a guided session Claude proposes and prepares.
First application staged:
`archive/handoffs/2026-09-02-mike-walkthrough-session-prompt.md` — corpus labelling
(due 09-09), the wisdom-store review, the Darwin key, location zones + APK + ping, the
BigQuery export, and the Restic off-machine decision. Everything else that looks unaddressed
in this document is Cluster H, parked-for-rebuild by his 08-27 ruling and confirmed 09-02.

---

## Status note — 2026-09-03, session ⑥ ran (commit `54073b6`, deployed and VM-verified)

**All five items in the ⑥ brief are done; nothing from it is owed a commit or a deploy.**
The VM is on `54073b6`, both units active, and the four new suites pass there.

- **`[DB-0829-01]`** — a declined email no longer survives in the log as sent. Three fixes:
  the gated third outcome on the ACTIONS line (which also fixes the journal line),
  fire-and-forget dispatch deferred until the confirmation store is authoritative, and the
  completion-claim patterns widened to catch the live *"That's sent to Iva."*
  **Ready to close**; its confirm is one live gated-then-declined action on the VM.
- **`[DB-0902-01]`** — Green half built and measured (0 of 21 genuine misses rejected, 8 of
  13 noise). **Cannot close yet**: the remaining five noise events need the `coordinator.md`
  definition, staged as Red proposal 1.
- **`[DB-0902-02]`** — built. The queue was never filled, not drained: 24 of 25 records carry
  no domain because the extractor is off behind `[DB-0820-03]`. **Ready to close** on one
  live pipeline inbox job that no longer says "no new messages".
  *Note the coupling this exposes:* `[DB-0820-03]`'s corpus labelling (due 09-09, item 1 of
  the (M)-walkthrough) is what actually makes the intake queue carry anything. Until it runs,
  the queue is empty by construction and the fix here only stops it lying about that.
- **`[DB-0822-06]`** — the derived-facts line is built, validated against Mike's own journal
  date, and live. **Cannot close yet**: its condition is a dated count read back correctly on
  the VM, and the four stale counts age out of the 5-day window on 2026-09-04.
- **`[DB-0822-09]`** — diagnosed. The surfacing miss is **not** the inbox split; both 09-02
  runs read the same source and the Synthesizer dropped a 536-token package. Red proposal 2,
  with a recommendation to make it structural rather than a third instruction attempt.

**Two Red proposals await Mike** —
`archive/plans/red_proposals_2026-09-03_session_six.md`. Both are staged, neither applied;
the Green halves already remove the user-visible damage in each case, so neither is urgent.

**The capstone still closes at ⑦'s end.** ⑦ and the (M)-walkthrough remain unrun.

**Update, same day (post-deploy live test).** Both session-⑥ Red proposals were approved by
Mike, built and deployed (`a4a9364`). `[DB-0902-01]`'s definition is live and the afternoon's
sessions produced no ROUTING_MISS at all — a signal, not the week-long confirm.
**`[DB-0822-09]` does not close and the reason is worth carrying:** the delivery build is
correct and inert. The live test's reply carried every item the backlog named, but the ledger
file does not exist — `logistics` emitted no `HORIZON_ITEMS:` line at all, returning
conversational markdown with none of its documented output format, having emitted the full
structured block on 09-02 from the same model. Format adherence varies run to run, so the
schema fix left the *emission* resting on a template slot. Closing it needs the relay to become
a **tool call** (`record_horizon_item`) — Mike's call; everything downstream of it is built and
tested.
