### 2026-08-15 (`/backlog attack` — two clusters, and two live faults found by reading the traces) — `5cf0a5e`, `451f622`, `bbda875`, `eb01025`, `5cf0a5e`, **deployed by Mike**

Outgoing handoff: the previous session closed `[DB-0815-03]` and `[DB-0815-01]`, left `## Now` at
7, and owed a `/backlog deep` sweep of `## Machine log`.

**Two clusters dispatched to worktree workers, both merged; the highest-value findings came from
the VM traces read in the coordinator window while they ran.**

**`[DB-0810-12]` — a Vertex 400 on a missing `thought_signature` destroyed the exchange.** Fixed
(`7214070`, merged `5cf0a5e`). Where a signature is demanded (Google endpoints only), a turn whose
assistant message carries unsigned function calls is recorded *signature-free* — assistant text
plus a user `[tool results]` message naming the tools that ran. Nothing left for Vertex to
validate; tools still dispatch once; the exchange survives, which was the reported harm.
**Both unsigned routes closed, not only the evidenced one:** `blocking_replay[...]` — flagged in
the item as never checked — was real, because the code appended `_signed` and classified it
afterwards. **Rejected:** porting `_openai_compat_loop`'s tc0-only workaround (serialises the
parallel dispatch — the documented regression); dropping the turn from history (side effects
repeat); retrying the blocking call (speculative). Tests verified discriminating — reverting only
`core/orchestrator.py` reproduces the live `400 … at position 2`.
**Closed at Mike's argument, not on the fortnight's silence.** He asked whether a recurrence would
simply raise a new ticket; for a *user-visible* recurrence it would, and the closed-item archive is
consulted before re-filing. The residual, and why the closing note carries a command rather than an
open item: **the fix converts a loud failure into a silent one** — the exchange now survives, so a
recurrence leaves only a `[signature_probe] … :neutralized` journal line that nothing sweeps.

**The Synthesizer read its own instructions aloud to Mike (new, found in the traces).** On
2026-08-12T00:14 the entire stored response was the model's deliberation, quoting `synthesizer.md`
verbatim and cut off mid-sentence. All three filter tiers passed it **correctly by their own
logic**: they hunt architecture *vocabulary*, and instruction prose contains none. Tier 4
(`bbda875`) keys on exactness instead — a 10-word contiguous span from the agent's own instruction
file or the constitution. **Persona files deliberately excluded**: they carry the user's own words,
and quoting the user back to himself is legitimate. Validated against **237 real Synthesizer
responses since 08-01: one suppression, the leak itself.** Filter security suite 88/88 GATE PASS.

**Metatron woke Mike at 00:11 (new).** `respect_quiet_hours` was opt-in and that job never set it.
Now opt-out (`451f622`): the two failure directions are not symmetric — a job held until morning is
a delay, a job fired at 00:11 is the product waking the user. **Mike's rule, built in:** a *one-off
the user asked for* that lands in quiet hours gets the disturb permission automatically; an
agent-invented job never does. Recurring jobs are excluded whoever asked — an interval job has no
single fire time to consent to, and a blanket exemption is not a permission.
**Found while building it, and worse than the change:** `fire_session` resolved `job_cfg` from
`scheduler.yaml` only, so **every agent-written job (`data/personas/{p}/schedules.yaml`) resolved
to `{}`** and could carry no setting to any gate. Harmless while all four gates defaulted
permissive; under opt-out quiet hours it would have silently held every user reminder until 07:00.

**`[DB-0814-02]` — stale context.** The brief the coordinator wrote was wrong and the worker built
it faithfully: grace keyed on the model resending a thread, but `open_threads` is replace-semantics
and **the Synthesizer rewrites the whole list on every response**, so that condition is true of
every live thread. It would have granted "post-travel recovery" grace on all two weeks of writes.
**Corrected (`37b0b03`)**: grace now requires the *user's* turn to engage the thread — the same
correction `82d394b` made to the repeated-instruction protocol, that the system's own output is not
evidence of user intent. Coordinator wired the plumbing (`5cf0a5e`), passing `None if is_proactive`,
because on a proactive session `user_input` is the scheduler's prompt — forwarding it would let the
system grace its own threads by talking to itself. **Stays open**: neither grace threshold has been
measured against real Synthesizer output, and the worker flagged material-change grace as
triggerable by a one-character diff.

**Corrected in-session:** the 00:11 firing was first reported as corroborating `[DB-0808-11]`
(`fire_function` skipping the gate stack). It does not — that job has a prompt, so it runs through
`fire_session`, where the gates did run. `[DB-0808-11]` remains real but unevidenced by this.

**`[DB-0809-02]` answered three days before its `due` date, and all three of its hypotheses are
wrong.** Mike's "three repetitive messages" (reported 08-12, about 08-11) were **four different
scheduled jobs** — `companion_checkin` 16:46, an inbox job 18:13, `companion_checkin` 19:48,
`evening_close` 20:00 — each independently picking up the unfinished evening ritual and re-asking
the same two questions. `_frame_proactive()` is working; `evening_close` is a victim, not the
culprit. The mechanism is that "raise a thing once" has no memory that a question was asked and not
answered.

**Worker cost, against estimate:** cluster A 143k vs ~64k estimated, cluster B 116k (then 185k on
rework) vs ~59k. Both ~2× and near the worst runs on record. The ledger medians are dominated by
*verification* work; these were **build** tasks — design a fix, write a suite, prove it
discriminates. Budget build work at ~2× the verification median until the ledger separates them.

**Reporting correction from Mike, mid-session:** lead with the problem in real terms, and do not
restate a worker's summary back to him — it is duplicative and costs tokens.

