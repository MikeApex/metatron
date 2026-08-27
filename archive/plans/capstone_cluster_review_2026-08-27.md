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
| 🔶 | [DB-0822-06] | Stale state as fact — age annotation built (`cbd5ca3`); **derived-count + intraday halves still open** | Amber | open halves need a design pass (~2h) |
| ⬜ | [DB-0822-07] | Two jobs fire 7 min apart — suppress the collision | **Red** (`core/scheduler.py`) | 1–2h supervised |
| ⬜ | [DB-0809-02] | Same unanswered question re-asked by every job | Red @session | decision + 2–4h |

### Cluster B — Action integrity
| Status | Item | One line | Tier | Est |
|---|---|---|---|---|
| 🔶 | [DB-0827-01] | Decline built (`0f8f528`) — confirm: one live decline that stays declined | Amber | done; **re-propose half open** (~1–2h, orchestrator context) |
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
| ⬜ | [DB-0818-05] | Asks which Bill twice — store the resolution | Amber | 2–4h |
| ⬜ | [DB-0818-06] | 24 non-facts in the wisdom store — per-entry cleanup, VM-owned data | Amber | 1–2h |

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
| ⬜ | [DB-0808-14] | Psychiatric meds rank same as statins — owes A4 re-run | Amber | 2–3h |
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

## Remaining investment (post-attack)

The attack + deploy removed ~10–12h of the original ~18–25h Green/Amber estimate. Remaining:
**~8–12h Green/Amber** (Clusters C/D/E code halves, the two supervised Red scheduler items,
National Rail once keyed) · **2–3 Red agent-file sessions with Mike** (email surfacing, CRM
sweep, provenance, referent fix) · **one decisions session** · **~30 Mike-minutes** draining
Cluster F. Model split per Mike: plan/review in Fable, build in Opus, Red-tier never delegated.

## Suggested next sessions, in order
1. **Decisions session** (Fable, with Mike) — the batch above; several cheap builds are gated
   behind it.
2. **Red pair in `core/scheduler.py`** (supervised): [DB-0822-07] + [DB-0808-11] together — same
   file, same gate-stack extraction shape.
3. **Email surfacing session** (Red, with Mike): [DB-0822-09], plus the [DB-0822-08]
   re-measurement read from a scheduled-run day.
4. **CRM sweep build** (Opus, after Mike's plan re-review) — [DB-0827-03], with [DB-0818-08]
   provenance either bundled or immediately after.

*Evidence trails: `archive/backlog_closed_2026-08.md` § Closed 2026-08-27 (both sections);
worker handoffs `archive/handoffs/2026-08-27-{session-hygiene,decline-path,routing-miss}.md`;
deploy by Mike 2026-08-27 evening.*
