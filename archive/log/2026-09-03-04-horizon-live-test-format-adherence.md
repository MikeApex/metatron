### 2026-09-03 (the horizon build is live-tested — it works, and its input never arrives)

Post-deploy test of the `[DB-0822-09]` structural delivery built earlier the same day. Two runs
on the VM with the directive that failed on 09-02: *"Check my inbox for new messages and
summarize any relevant logistics details found."*

**The user-visible result is a pass, and it is worth stating first.** The reply carried Death
Cab for Cutie (Troxy, 26 Sep), Jimmy Carr, Iva's dental appointment and the George School
social — the precise set that was generated one layer down and silently dropped on 09-02 — and
went further than the item asked, noticing that the SE10 Sukkot celebration falls on the same
afternoon as the concert. If the test had stopped at reading the reply it would have been
recorded as a clean confirm.

**It was not a pass, and the ledger is what says so.**
`data/personas/mike/horizon/ledger.json` does not exist. Nothing was filed. The items reached
Mike through the Synthesizer's own compliance — the same channel that failed on 09-02 — and the
mechanism built to guarantee them played no part.

**Why: `logistics` emitted no `HORIZON_ITEMS:` line at all.** Not malformed, absent. The parser
logs a warning on unparseable JSON and files a trace line on success; neither appeared, and the
skip path for text without the marker is silent. A direct run confirmed it: the agent returned
conversational markdown with **none** of its documented output format — no `ACTIONS TAKEN:`, no
`FLAGS:`, no `HORIZON_ITEMS:`. On 2026-09-02 the same agent, on the same model
(`gemini-3.5-flash-lite`), emitted the full structured block. **Output-format adherence varies
run to run.**

**What this says about the fix that was built.** The Red edit made the *schema* precise, which
was the right diagnosis of the dedupe problem — a key cannot be extracted from prose — but it
left the *delivery of the block itself* resting on the model choosing to emit a template slot.
That is the same class of failure as every other item in this cluster, one level further out
than anyone had looked. The reasoning recorded when the format change was chosen — *"a better
use of a Red edit, because it moves a judgement out of prose instead of adding another rule to
be ignored"* — was half right: the judgement did move out of prose, and the *emission* stayed
in it.

**What closes it, and why it is not another instruction.** Make the relay a tool call —
`record_horizon_item(title, date, venue, kind, detail)` — instead of a template slot. A tool
call is structured by construction: it cannot be quietly replaced by prose, and its arguments
cannot be malformed and ignored. That is already this codebase's answer for structured relay
that must not be lost (`write_quality_event`, `open_obligation`), and it is what
`.claude/rules/agent-files.md` means by a named tool being a specification. Everything
downstream — the ledger, the dedupe key, the context block, the two placement decisions — is
built and tested; only the input path changes. Cost: one tool (Green), a grant in both routing
files (Red), one line in `logistics.md` (Red).

**A note on how nearly this was recorded as a success.** The reply contained every item the
backlog entry named. The only thing that contradicted it was a file that was not there. The
confirm condition written when the build landed — *"one live interest-level email that reaches
Mike, and is then NOT repeated"* — would have been marked half-satisfied on the strength of the
reply alone. It was the ledger check, not the reading, that found the build inert.

**One positive from the same window, recorded as a signal and not a confirm.** Three live
sessions that afternoon, post-deploy, produced no `ROUTING_MISS` at all — the only quality
event was a genuine `USER_CORRECTION`. `[DB-0902-01]`'s week-long clock stands.
