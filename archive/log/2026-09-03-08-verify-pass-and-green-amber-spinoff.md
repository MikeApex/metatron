### 2026-09-03, evening (the verify pass holds, and the Green/Amber spinoff closes four items in one sitting) — `core/{attachments,server}.py`, `tests/{test_attachment_persistence,run_intake_redteam}.py` (new), `config/templates/scheduler.yaml` (comments), `docs/INFRASTRUCTURE.md`, `DEV_BACKLOG.md`, `archive/backlog_closed_2026-09.md` — `d7c7fc7`, `764d218`, `003a83b`, `dc4cba4` + this close-out — **deployed by Mike in-session**

**A `/backlog verify` over all four `## Now` items found zero failed claims** — one Sonnet
worker confirmed every built half in-tree (tests 15/13/7/10, all passing), and the VM round-trip
confirmed the runtime story: the three morning ROUTING_MISS noise events all predate the 12:19
deploy, zero post-deploy; `pending_confirmations` empty; no post-deploy inbox job yet. All four
`@waiting` stand. The sweep beyond `## Now` found the real value: **the CRM-sweep entry
`[DB-0827-03]` had sat a full state behind reality since 08-29** (still "@waiting pre-build
review" while the ledger filled on the VM) — the retitle the 08-29 fragment had ordered was
applied here.

**Mike then ordered a Green/Amber spinoff — "none of this should be work you need to do."** Two
workers, disjoint manifests, own worktrees: an Opus 5 worker built **cross-turn attachment
persistence** (`d7c7fc7` — reference-match in Python, load-on-hit not always-carry, revived
content through the same `describe_for_prompt()` boundary, wording pinned by test; two clocks,
24h carry / 30d disk, after the worker correctly overruled my single-TTL brief because the
history UI serves old attachments). A Sonnet worker built the **hostile intake-email red team**
(`764d218`, gate PASS 5/0/0 — code tier provably uninfluenced, the model extractor refused the
injected instruction) and documented the scheduler `day:`/`days:` two-layer split.

**Four items closed with evidence** (`archive/backlog_closed_2026-09.md`): `[DB-0820-04]` on the
gate PASS; `[DB-0815-11]` on its clean-week exit (detector live since `4b6779e`, zero
`FALSE_ACTION_CLAIM` ever — closed hours before the literal week, stated not hidden);
`[DB-0903-03]` (the attachment item, filed and closed same day) on a scripted live confirm
against `danny_park` — codeword read back from a PDF three turns after upload, no re-upload;
and `[DB-0822-09]`-adjacent curation. `[DB-0903-02]` (loud day-name validation, Red,
`core/scheduler.py`) filed to Later as the remainder.

**Believed true earlier, corrected:** my brief specified one 24h TTL for the attachment store —
wrong, would have blanked history-UI images; the worker's two-clock split stands. And
`[DB-0814-02]`'s "either grace works or expiry is dead" ambiguity is now **measured: expiry is
structurally dead** — 111 audited writes, 0 expiries, and all four live threads carry
`added: 2026-09-03` including one verbatim in the 09-02 conversation, so the exact-text match
refreshes birthdates on rewording and a rephrased thread can never age. Marked `@session`
(thread identity is the `[DB-0827-07]` semantic-guessing class; fork is Mike's), due 09-05.

**Rejected:** spinning off `[DB-0902-05]`/`[DB-0902-06]` (the two remaining genuine Green
candidates) tonight — Now-before-Later is Mike's rule and everything in Now is time-gated;
recommended as one Sonnet worker next session. Also rejected: closing `[DB-0810-05]` — due
pushed to 10-01, the blocker is an empty mailbox, not effort.

**Worker ledger:** verify Sonnet 68k (est 60–80k, good); build Opus 82k (est 100–150k, under);
build Sonnet 159k (est 60–80k — **2× miss**: the live Vertex red-team harness; next time an
item that *runs* models gets the inherited-tier estimate, not the mechanical one).
