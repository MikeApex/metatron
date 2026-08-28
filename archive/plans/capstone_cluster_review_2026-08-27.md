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

### Cluster H — Parked for rebuild / not-capstone (Mike to give final ruling)
[DB-0808-09] turn economics · [DB-0810-11] code-vs-model @session (rebuild notebook anchor) ·
[DB-0827-06] Synthesizer compression · [DB-0822-08] propose-don't-report (**re-measure
post-audit first** — may return to Cluster A if the instruction genuinely fails) ·
[DB-0815-13] semantic retrieval (trigger unfired) · [DB-0815-02] Bulgarian STT (held) ·
[DB-0820-02] APK file save · [DB-0819-01] subscriptions · [DB-0809-08] missed-opportunity
metric · [DB-0814-03] mailbox tickets · [DB-0826-02] contact enrichment · [DB-0827-04] field
promotion (gated) · [DB-0818-09] plausibility check (design with [DB-0818-08]) ·
[DB-0827-09] Accountability Index (@session design)

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
- **First-draft features:** `[DB-0815-12]` location 🔶 **server side deployed**; remaining is
  Mike's APK sideload + VM zones file, then the option-b zone-suggestion build — all bundled
  in `archive/handoffs/2026-08-28-location-launch-prompt.md`. Vendor ruling refined same day:
  Places is queried by expected-place NAME only; coordinates never leave the machine.
- **Cluster H graduate:** `[DB-0827-09]` Accountability Index 🔶 **code half built +
  deployed** (counts ride the 05:40 rollup; CLI report on demand). Judgment gate +
  intentions-as-list (frequency → urgency) ride session ③; audit `[DB-0828-01]`
  `due: 2026-09-07`.

Session order ②–④ unchanged and next; ③ now carries the ritual Red line, the judgment-gate
proposal, the Diarist list-shape line, and possibly the location proposal-voicing line.
