### 2026-08-28 (post-deploy rulings — the Pro flip dies, intentions become a list, zones get a growth path)

Mike deployed the spinoff batch the same evening and ruled on the open questions it raised,
in the same chat. Recorded in the items; reasoning here.

- **Pro flip DECLINED (`[DB-0820-05]`).** 11s/reply is a non-starter, and the deeper reason
  is architectural: Pro is incrementally better at routing, but *a routing system* is what
  matters, and the Coordinator is redesigned after the capstone anyway — paying latency and
  money for a temporary patch on a component with a scheduled redesign is backwards. The
  capped-thinking re-probe was dropped as moot (option rejected: flip with capped budget —
  never tested, no longer needed). Fable concurred with one shaping point, accepted: the fix
  should be structural (code-computed referent context, `tools/turn_context.py` pattern)
  rather than instruction-only, because Pro's winning move was following a rule
  `coordinator.md` already states and Flash-Lite ignores — the adherence class, where
  instruction-only fixes have repeatedly failed. `[DB-0826-01]` is the fix path and now
  carries the probe's reproduction suite (B-hard).
- **Intentions become a LIST (`[DB-0827-09]` ruling a).** Not just to stop the same-day
  overwrite: repeated statements of one intention are kept so **frequency can score
  urgency**. Diarist write-shape line is Red, rides session ③; index counts restatements.
- **Judgment gate cleared for the Vertex path (`[DB-0827-09]` ruling b)** under Amendment
  2026-08-28 — same basis as `intake_extractor`; the routing entry records it when built.
  Daily cadence confirmed sufficient; the 05:40 rollup counts already satisfy it.
- **Zone suggestion by reverse-geocode authorised (`[DB-0815-12]` next draft).** A ping in
  no zone → code queries Google Places → propose-and-confirm → Python writes the zone. This
  is the vendor decision the 08-28 design had explicitly reserved; Mike made it (consistent
  with the running-it-lite ruling — Google already holds his location by other routes).
  Zones need defining only at key places; everywhere else is `away` by design. The live
  `zones.yaml` stays Mike's to create on the VM — Denied from dev sessions, per the standing
  VM-owns-persona-data rule.
- **`[DB-0828-01]` dated at deploy per its own rule: `due: 2026-09-07`.**

Believed earlier, corrected: the close-out had "capped-budget re-probe recommended" as the
next step on `[DB-0820-05]` — superseded within hours by the decline; the estimate
(~3.5–5s/reply at a 128-token floor) never needed testing.

Commit: this fragment + `SESSION.md`/`DEV_BACKLOG.md` updates; spinoff batch itself deployed
by Mike 2026-08-28 evening (APK sideload still owed for location's client half).
