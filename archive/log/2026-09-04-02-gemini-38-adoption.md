### 2026-09-04, second (3.8 Flash adopted the day it became callable, and a negative result turns out to have had a shelf life) — `config/modules/{routing,routing_cloud,spend_guard}.yaml`, `SESSION.md`, `DEV_BACKLOG.md`, `docs/CONVENTIONS.md`, plus `~/.claude/mcp_servers/ask_gemini.py` and Chorus (`~/Desktop/chat/{server,insult_sim}.py`) — **committed; owes `./deploy.sh`**

**Prompted by a Google launch email for Gemini 3.8 Flash, not by the chore's due date.** That
distinction is the session's main finding and is now written into the chore itself.

**The adoption.** Reasoning tier moved `gemini-3.7-flash` → `gemini-3.8-flash` across all six
slots (synthesizer, pattern_miner, goals_interviewer, mental_wellbeing, physical_health,
research_agent) in one commit at Mike's direction. Bulk tier unchanged on `gemini-3.5-flash-lite`.
Same price, higher scores on every benchmark Google published. Verified through `resolve_model()`
for each agent, not just by YAML parsing.

**The 09-01 session's negative result was correct and had a three-day shelf life.** It recorded
`gemini-3.8-flash` as `200 GA` in the Vertex catalogue but `404` on `generateContent` at `global`,
and concluded "nothing to adopt." True that day. On 09-04 the same script reported it **newer and
callable**, and a live call answered. It had also landed on the Gemini Developer API, where the
09-01 note explicitly said it was *not reachable* — so both catalogues converged within three days,
independently.

> **The correction worth carrying: a negative availability result is a dated observation, not a
> standing fact.** The project already knew "catalogue presence is not availability" and had built
> `scripts/check_model_availability.py` to enforce it. The unexamined half was the inverse — a
> `404` was written down in four files in the present tense and read as settled. `SESSION.md`
> ("Two models look available and are not"), `routing_cloud.yaml`'s header, `ask_gemini.py`'s
> header and the chore entry all asserted it. All four are now dated or corrected. **Confirm with
> a live call before wiring a model in — and re-confirm before writing one off.**

**Cadence monthly → weekly (Mike, this session).** The 27-day worst-case blind spot on a
same-price upgrade was the argument. Cost was never the constraint and this is recorded so it is
not re-litigated: a run is ~20s and well under $0.001, nearly all of it in the free SKU/metadata
filter, and a week where nothing shipped makes **zero** billable probes. The date is now
explicitly **the floor, not the trigger** — run on any credible signal a model shipped.
`due:` 2026-10-01 → 2026-09-11.

**Pricing: the one figure that is inferred, and it errs in the unsafe direction.** 3.8's billing
SKUs now exist and read $1.50/$7.50/$0.15 — *identical to 3.7's SKUs*, which are the **list**
rates; we are actually billed $0.75/$3.75 under an introductory discount the SKU catalogue does
not express. Google's announcement says 3.8 ships at 3.7's price, so the intro rates were entered
with a `from: "2027-01-01"` block **copied from 3.7, not confirmed for 3.8** — its intro end date
is published only on the blog, and `WebFetch` is Denied here. Filed as `[DB-0904-02]`
(`due: 2026-09-12`), closing on the BigQuery billing export once real 3.8 traffic lands.

- **Rejected: pinning the list rates ($1.50/$7.50).** Safe against under-reporting, but it
  over-reports 2x today, and with caps at $100/$175 a spurious hard-cap trip on this project is an
  **outage**, not a cost event. The 3.7 entry set the precedent (intro rates + a dated switch) for
  exactly this reason.
- **Rejected: entering intro rates with no follow-up.** The error direction here makes the guard
  *under*-report, so the caps stop biting early — that needs an owner, not an assumption.

**Cache floor re-checked empirically, because it is per-model and fails silently.** Created a real
`CachedContent` on 3.8 at the orchestrator's own padding size (5,919 tokens) and on 3.7 as a
control; both succeeded, both deleted immediately. `_VERTEX_CACHE_MIN_TOKENS = 4096` needs no
change. Worth recording that the **first run of this probe was invalid** — both models failed
identically on a 1-minute `expire_time` (Vertex requires strictly more than 1 minute), which would
have read as "3.8 rejects caches" had the 3.7 control not failed the same way. *The control is what
made the result interpretable.*

**Three surfaces, three different availability questions — they do not share a catalogue.**
Metatron is Vertex; Chorus and the `ask_gemini` MCP are the Gemini Developer API. Each was
confirmed with its own live call.

1. **Metatron** — six routing slots + a `spend_guard.yaml` entry with **all four** keys (an entry
   that exists but omits `cache_storage_per_hour` bills storage at zero).
2. **Chorus** — Mike chose a **separate** `gemini-3.8` key over repointing `gemini-pro`, so both
   generations stay selectable. **It needed five table entries, not one:** `_MODEL_STYLE.get()`
   falls back to the *ollama* style, so a Gemini key with no style entry would have silently
   debated in the plain local-model voice. Added to `insult_sim.py` in step, per its own comment.
   Chorus is not a git repo — those edits are live on disk and need a server restart.
3. **`ask_gemini` MCP** — `flash` moved to 3.8 per the file's generation-tracking convention,
   `3.8flash` and `3.7flash` both pinned, `DEFAULT_MODEL` bumped, and the `set_model` docstring
   (user-facing tool description) corrected — it still advertised `flash (3.7 Flash)`.

**Left deliberately alone.** `docs/CONVENTIONS.md`'s worked example of the 09-01 trap is written in
explicit past tense ("that day", "observed 2026-09-01") and stays true as history — it was updated
only where it asserted the cadence. **Clinical safety testing: Mike's instruction was to ignore
it.** The `mental_wellbeing` routing comment was still corrected to record that this is now the
**second** consecutive model hop with no A4 run and that the last green run (6/6, 2026-08-04) was
against a model no longer in the fleet — the comment previously described one hop, which would have
read as understating it. No test was run and none is proposed.

**Got wrong in this session and fixed: a duplicate backlog id.** The new pricing item was minted
by hand as `[DB-0904-01]` mid-session — an id the (M)-walkthrough session had already used for
"a forwarded email is filed as if the user wrote it." Two live items shared one id across four
files. Caught by `backlog_close_scan.py` in step 4, which printed the *other* `[DB-0904-01]`;
renumbered to `[DB-0904-02]` in `DEV_BACKLOG.md`, `SESSION.md`, `spend_guard.yaml` and this
fragment. **This is precisely what `/archive`'s "file as a fragment in `.claude/backlog_inbox/`,
no id is minted here" rule prevents** — the collision-safe path was skipped because the item was
filed during the work, not at close-out. Minting an id by hand mid-session needs a `grep` for it
first, or it needs to go through the inbox.

**A second scan caveat, recorded because it will recur.** `backlog_close_scan.py` diffs
`HEAD~1..HEAD`, so at step 4 it was ranking the *previous* commit's changes — this session's work
was still uncommitted. Its fifteen candidates were evidence about the intake session, not this
one. Nothing was closed on the strength of it; the only affected item, `[DB-0901-01]`, is a
standing chore that records a run and pushes its date rather than closing.

**Not deployed.** `config/` changes need `./deploy.sh`, which is Denied — Mike's to run.

