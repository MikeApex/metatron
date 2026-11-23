# Closed Backlog Archive — 2026-11

**Items closed in November 2026, with the evidence that closed them.** Rolls monthly;
the previous file is [`backlog_closed_2026-10.md`](backlog_closed_2026-10.md).

**Search this before re-filing anything.** A closed item is removed from
[`../DEV_BACKLOG.md`](../DEV_BACKLOG.md) entirely — this is where its proof lives.

---

## ✅ [DB-0810-11] Where should code replace model judgment? — closed 2026-11-23

**Closed into a document, by Mike's ruling D1:**
[`plans/agent_instructions_to_code_sweep_2026-11-23.md`](plans/agent_instructions_to_code_sweep_2026-11-23.md).
That sweep read every runtime agent instruction file against the code that loads it, at medium
effort. It found 25 moves (bins A–C) and 6 One Home contradictions. A Fable review
([`plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md`](plans/agent_instructions_to_code_sweep_review_2026-11-23_fable-5-1.md))
confirmed 21 of the 25 rows and added 19 misses. Mike ruled D1–D13 in § 6 of the sweep document.
The build runs from `handoffs/2026-11-23-instructions-to-code-build-driver-prompt.md`, held until
the data-object project finishes.

**Where each strand went:**
- **(a) Lookups feeding agents evidence:** the sweep's cluster C2. Contact-name matching is done.
  The nickname-prefix signal (`Jon` / `Jonathan` scoring 0.545 against a 0.6 bar) goes to finding
  #12.
- **(b) Code removing agent calls:** clusters C1 and C3.
- **(c) A standing review protocol:** the sweep's method (four bins, silent first) becomes one
  lens of the next codebase review. It is not a standing backlog item.
- **`write_archive` dedup:** built. `tools/diarist.py:324` (`[DB-0810-03]` grants ruling,
  2026-08-28).
- **`temperature`, not plumbed through any provider path:** its own inbox line, per the review
  (filed 2026-11-23).

**The item as it stood when closed:**

- **[DB-0810-11] Where should code replace model judgment?** Raised by Mike 2026-08-05, never
  given its own session. Three strands: (a) deterministic lookups feeding agents evidence instead
  of asking them to recall it, with `tools/scheduling.py` as the worked example; (b) code that
  removes agent calls entirely; (c) a standing code/agent review protocol. Also parked here:
  `temperature`. Parked to the rebuild notebook by Mike on 2026-09-02, then left without a home
  when Mark 2 ended on 2026-11-18. *Filed 2026-08-10.*
