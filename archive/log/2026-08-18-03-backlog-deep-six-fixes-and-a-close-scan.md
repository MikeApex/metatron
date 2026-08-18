### 2026-08-18 (`/backlog deep` + one attack round — six fixes, and `/archive` learns to close what it fixed by accident) — `0a9e311`/`3a43f62`/`10fc9f6` merged, `87aad78`, `f4cc812` — **deployed**

**Incoming handoff:** `/backlog attack` shipped three clusters, the VM turned out to have been
OOM-killing itself unnoticed, and A9 product analytics was built. `## Now` was 2 items.

**Six Green-tier fixes shipped, verified first.** A `/backlog deep` sweep verified 11 items across
three read-only workers (234k against a 230k estimate; spread 66k–100k against a 78k sonnet
median). Only then did an attack round build. What the tool now does differently: answers no
longer render twice on reconnect (`[DB-0810-01]`); an obligation with a rough deadline stops being
dropped from context before undated ones (`[DB-0814-04]`); naming an internal term in a complaint
no longer suppresses the whole reply (`[DB-0808-05]`); The Book attributes nested calls correctly
(`[DB-0810-02]`); the clinical safety suite can be pointed at Flash-Lite, which serves most of that
traffic (`[DB-0808-17]`); and moving instruction text into a persona file no longer hides a missing
tool grant (`[DB-0810-03]`). All merged, all seven new test files green on the merged tree, filter
gate 88 checks PASS, `qa_sweep` 9/9 — no repeat of the 7/17 merge failure the previous session
recorded.

**`/archive` step 4 now runs `scripts/backlog_close_scan.py` instead of grepping filenames.** The
grep only ever found items that *name a file*; most are written as symptoms, because the filing bar
is what a user would notice. The class it missed entirely was **incidental closures** — an item
fixed by a commit aimed at something else. `[DB-0808-16]` is the worked example: closed inside
`7c70cd9` (*"Fix memory race, add clinical thread lifecycle, upgrade output filter"*, naming none of
it) and open for ten days after. The scan matches the **added lines** of the diff, because an
incidental closure is by definition one the commit message does not mention. The grep was deleted
rather than left beside it, per the standing rule in `.claude/rules/deploy.md` that new machinery
names what it retires.

**Believed true earlier, wrong — three, and two were mine.**

1. **I briefed a worker that four `_set_current_agent(_parent_agent)` calls were redundant
   workarounds to delete once `pop_agent()` restored properly.** They are not: they sit inside
   worker closures, seeding a new thread's empty thread-local, and `pop_agent()` cannot cross a
   thread boundary. Deleting them would have silently dropped every parallel specialist from the
   trace — the exact bug the comment there says it fixed. I also said neither caller used
   `push_agent()`'s return value; both do. Both errors came from my own verification pass, which I
   relayed as established fact after over-compressing it. The worker caught both.
2. **The TfL Inbox item's bug does not exist.** It described station names being passed as line IDs
   causing 404s. `tools/tfl_status.py` and `tools/travel_watch.py` only ever pass line names matched
   against a fixed table and *cannot* emit a station query; there is no National Rail station
   integration at all. The entry was filed five minutes after a logged research-agent empty-search
   for the same Greenwich-line question. Acting on the description would have commissioned an
   integration for a bug that was never there — the standing rule earning its keep.
3. **Three successive versions of the close scan reported "no candidates" and looked correct.** A
   section parser split on the first literal `## Now`, which is inside backticks in the Markers
   prose hundreds of lines above the real heading; and record files in the diff let every item match
   its own text (44 of ~50 scored). **Zero results is indistinguishable from a clean sweep**, so
   anything of this shape needs a known-positive fixture or it silently certifies nothing.

**Clustering was done at the wrong level, twice, and that is a communication rule now.** The sweep
clustered `## Machine log` *signatures* — raw runtime events — and presented the counts as a
workload. Mike's correction: cluster at the **item** level, grouping the `DB-` to-dos for one
feature so the feature can be retired, and omit anything `@waiting:`/`@session:` entirely, because
the point of a backlog pass is what can be done now. A signature says a problem is real; it is not
work and nobody can pick it up. Filed as `feedback-backlog-cluster-at-item-level`. Related
correction the same session: lead with **what** the tool does differently, then a little of the how,
and name a defect by what a user sees rather than its mechanism.

**A regression found by a test nobody was reading.** `tests/test_action_provenance.py` had been
9/10 since 2026-08-18's earlier round: `merge_contacts`, `import_contacts_file` and `fetch_rendered`
shipped classified in neither `ACTION_TOOLS` nor `READ_TOOLS`, so a state-changing tool could run
without appearing on the ACTIONS line. That is the `[DB-0810-13]` class, closed on 08-15 and
regressed by the next batch of tools three days later. Fixed in `f4cc812`. **`_WORLD_AFFECTING` in
`tools/analytics.py` deliberately untouched** — whether a contact merge counts as absorbed work sets
the headline metric and is Mike's call per `ROADMAP.md` § A9a.

**Cluster A (standing preferences not sticking) parked, and the reasoning matters.** Mike judged it
addressed by the persona-level knowledge work. The last user correction of the check-in rule is
**08-12**; the evening-ritual move and the knowledge layering landed **08-15 and 08-18** — so the
silence *starts three days before the fix* and cannot be attributed to it. The whole machine log
also went quiet in that window (zero entries on 08-13 and 08-14, 7 across 08-15→08-18, against
10–12/day earlier) while the VM was OOM-killing itself. Plausibly fixed, not demonstrated; it needs
a week of normal use, not investigation.

**Travel is the largest actionable cluster and none of it is filed.** Three distinct problems: no
National Rail/Southeastern integration exists at all (TfL works, which is why it reads as
operational); the tool assumes Mike is flying when he is dropping someone off (~6 entries, twice on
BA 892 — an inference failure, not a data-feed gap); and the research agent returns blank on live
web queries. Carried to the next session's prompt rather than filed here, since `/archive` does not
triage.

**Also filed:** graceful refusal messages — *"I can't do that now because xyz"* instead of an error
(Mike, 2026-08-18). Already scoped as `ROADMAP.md` § B4 and tracked in aggregate as
`[DB-0804-02]`, but buried inside Track B where nobody would find it; the fragment names the wording
half B4 under-specifies, and the `CLAUDE.md` § Discretion constraint that makes it hard.

**Owed, both cheap, neither built:** the A4 Flash-Lite run (~$0.02, closes `[DB-0808-17]`) and one
VM run of `scripts/check_agent_tools.py` (closes the persona half of `[DB-0810-03]` — a Mac run
proves nothing, and the guard now says so itself). `[DB-0810-01]` needs one live reconnect from
Mike; the mechanism was verified, the device was not.
