### 2026-08-27 (token audit closed into the backlog; the rebuild conversation gets a home)

A month-old parked chat (the Aug-9 token audit, itself grown from a hunt for the June
"slim coordinator.md" proposal) was reviewed for relevance and closed out into durable homes
instead of being resumed. What survived, and where it went:

- **The specialist turn-count question is measured, and the answer reverses the June diagnosis'
  target.** Aug 20–27 traces: every specialist tool-turn is single-call — 392 turns, not one
  batched — so turns/call (relationships 4.2 → diarist 2.6) is pure sequential tool use, each
  re-sending full context. The "sequential not parallel" defect the June plan pinned on the
  Coordinator (measured wrong, superseded 08-08) is real *in the specialists*. Filed into
  `[DB-0808-09]` with the table, the `{1:N}` histogram, and three candidate fixes ranked:
  instructed batching (a trim), code-side prefetch of predictable reads (the strong one —
  Mike's proposal; reads-then-one-write is the measured shape), read/write agent split
  (weakest — same tokens under two prompts). Step 1 of that item closed; Steps 2–3 open.
- **Synthesizer thinking is unbounded — filed as decision `[DB-0827-02]`.** No thinking_config
  anywhere; `max_output_tokens` doesn't bound Gemini thinking; ~86% of Synth output is thinking
  at $12/M. Key nuance kept in the item: the 08-18 rejection of `thinking_budget: 0` rejected
  *disabling* for a formatting leak — a non-zero *cap* was never evaluated, and never on cost.
  Needs the A4 pipeline gate if acted on (clinical-flag voice). Cross-linked `[DB-0820-05]`.
- **Wrong earlier, corrected in-session:** the Aug-9 audit's 62.8:1 input:output ratio and
  Synthesizer cost share were computed from pre-`c41baa0` traces (thinking tokens uncounted) —
  Mike caught it; only turn counts and input-side shares survived. Also, the audit's "caching
  never worked" first read was false (INFO lines aren't captured in prod; a live probe showed
  cache_read); and "slimming coordinator.md saves zero because padding re-inflates" no longer
  holds as stated — the file has grown to ~5,184 tokens, past the pad target, noted in
  `[DB-0808-09]`.
- **The code-dominant rebuild conversation now has a standing home:**
  `archive/plans/code_dominant_rebuild_notes.md` — living notebook, dated rounds appended, no
  length limit (Mike's call), thinking-only, retires into the refactor plan when the rebuild is
  commissioned. Round one = abstract of the 08-22 "built backwards?" snapshot (which Mike
  couldn't find a week later — the motivating failure); round two = this session's audit read
  architecturally, including the caching-vs-context-file tension. Anchored from `[DB-0810-11]`
  and back-pointed from the 08-22 doc (its only edit — a forwarding line). Rejected: per-round
  dated snapshots (just failed discoverability); carrying notes in the backlog (items are
  evidence-bound work, not essays). Memory file written so every session knows to append there.
- **CLAUDE.md gained the bare-id rule** (problem in plain language before any `[DB-…]` id) —
  Mike's second raise of it; memory alone wasn't carrying it. File sits at exactly 300/300
  lines: the next binding rule forces a restructure.

No deploy — every change is dev-context (CLAUDE.md, DEV_BACKLOG.md, archive/, memory). Commit:
this close-out's own.

