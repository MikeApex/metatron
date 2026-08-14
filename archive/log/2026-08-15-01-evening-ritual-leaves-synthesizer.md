### 2026-08-15 (a persona's evening ritual leaves the agent file every persona loads) — `6913ad7`, **committed, not deployed**

Ran `/backlog deep`. Two things were open: `DEV_BACKLOG.md` at 598 lines against ~450, and the
`⚠ machine: ×5` on `mike.md:13` (consolidated evening check-in). The second one is the session.

**The correction is the point, and it inverted twice.** The `⚠` said the preference *"may already
be covered by a rule that applies to everyone."* Following `.claude/rules/agent-files.md` § Two
kinds of preference — which says **default to design** — I read it as design, wrote the
consolidated-delivery instruction into `config/agents/synthesizer.md`, and deleted the `mike.md`
copy on the VM. **Mike rejected it:** the Franklin virtue review is his personal ritual, not how
Metatron should behave for anyone. Then rejected the revert too — the *entire* Franklin block
should never have been in `synthesizer.md`. So the default is a default, not a verdict, and this
is the case that shows the difference: a ritual can be personal even when the *delivery format*
reads like generic good sense.

**What shipped.** `config/personas/mike/evening_ritual.md` (new, VM-only, gitignored) holds the 13
virtues, the consolidated single-message delivery rule, the `write_log` spec and the missed-review
catch-up. `load_config()` loads it through the same optional-file path `self_development.md`
already used — present for one persona, absent and inert for the rest, ~11 lines.
`synthesizer.md` § Evening close is now generic, as is its morning catch-up line, which had
hardcoded `franklin_virtues`.

**The token question was asked and inverted the premise.** Mike asked that the new mechanism not
bloat context. Measurement: the virtue block was 2,097 bytes (~520 tokens) sitting in a **global**
agent file that every persona loads. So the move is not an addition — it is **token-neutral for
Mike and a saving for every other persona**. `ROADMAP.md` § D2 already prescribes this pattern and
names *"virtue lists"* verbatim as domain data that should leave instruction files.

**Options rejected.** (1) `read_agent_config` on demand — `synthesizer` does not hold that grant
(a Red-tier `routing_cloud.yaml` edit), and it reads agent-authored JSON *state* under `data/`,
the wrong space for a hand-maintained ritual. (2) Putting the ritual in `scheduler.yaml`'s
`evening_close` prompt — that file's own comment says *"Shape of the opening now lives in
`config/agents/synthesizer.md` — do not restate it here."* (3) Leaving the block in
`synthesizer.md` and only relocating the delivery preference — rejected by Mike, and it would have
left every non-Mike persona paying for it.

**Believed true earlier, wrong:** that `mike.md:12` (food log) was part of the same ritual and
should move with it. Mike corrected this — the food log is a separate check-in item covering the
day's whole diet, not part of the virtue review. It stays in `mike.md`; `evening_ritual.md`
references the consolidated 14-point delivery without owning the food-log requirement.

**Two things found by verifying rather than assuming.** The `scp` landed `evening_ritual.md` at
`644` while every sibling in that directory is `600` — a Fail under the sensitive-path rule in
`ROADMAP.md` § D2, since persona config is Tier 1–3. Fixed with `chmod 600` and confirmed. And
the loader was tested against `danny_park` before being trusted: absent → no section, present →
section loaded with body intact, cleanup verified.

**One deliberate regression, recorded rather than hidden.** Moving the ritual's `write_log` call
into a persona file removed it from `scripts/check_agent_tools.py`'s view — that guard scans agent
files only. `synthesizer`'s missing `write_log` grant is unchanged and still works only because
`dispatch_tool()` does not enforce allowlists; what changed is that the guard can no longer see
it. Same class as `[DB-0810-03]`, noted in `DEV_BACKLOG.md` so a future clean report is not read
as proof.

**`DEV_BACKLOG.md` is 614 lines against ~450** — up 16, not down, because the machine-log sweep
replaced two raw entries with a fuller note recording the corrected judgement. The `deep` pass's
clustering half did not run: `## Later` was read for merge candidates and none were found that
were not already deliberately cross-referenced. The overage is evidence-dense `## Now` entries,
not narrative creep, so nothing was trimmed to hit a number.

**Deploy is owed.** `./deploy.sh` is Denied in `.claude/settings.json` and the deny is enforced for
Bash, so this session could not run it. Until Mike does, the VM runs the old `synthesizer.md`
while `mike.md:13` is already deleted — the consolidated instruction is in neither place the
running system reads, and `evening_ritual.md` sits on the VM unloaded.

