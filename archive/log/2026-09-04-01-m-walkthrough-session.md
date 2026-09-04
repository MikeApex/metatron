### 2026-09-04 (the (M)-walkthrough — six Mike-gated items worked live; the confirms found the defects) — `tools/{intake,intake_extract,wisdom}.py`, `tests/{run_intake_eval,build_intake_corpus}.py`, `config/agents/{intake_extractor,work_vocation}.md` + 3 variant files, both routing files, `config/modules/spend_guard.yaml`, `config/templates/intake.yaml`, `android/app/src/main/AndroidManifest.xml`, `docs/INFRASTRUCTURE.md`, `DEV_BACKLOG.md`, `archive/backlog_closed_2026-09.md` — **not committed, not deployed; individual files scp'd to the VM for the eval**

**First application of CLAUDE.md § *Mike-gated work gets a walkthrough, not a wait*.** Six (M)
items had been standing on lists with nothing scheduled to close them. Three closed, two were
re-dated by Mike's word, one is half done. **Three of the seven were not the shape the handoff
prompt described, and probing that before he sat down saved most of the session.**

**BigQuery needed no console work — it was live the whole time.** 62,764 rows through the
current day. It was reported dead on 08-22, corrected the same day, and the correction never
reached the two places repeating it — including `spend_guard.yaml`'s comment, which was the
stated justification for the `unmetered_uplift: 1.176` factor. The residual that factor
estimates is now directly attributable per SKU via `scripts/vertex_cost_reconcile.py`.

**Location closed on a live ping, and the confirm is what found the bug.** Mike stood near a
named zone, tapped "Share where I am now," and got *"Could not get a location fix"* — with no
permission prompt, which is the tell. `AndroidManifest.xml` declared internet, mic, audio
settings and vibrate, and **no location permission at all**; Android refuses
`navigator.geolocation` at the OS level before the app sees it. The item had shipped with
"JS test 11/11" — browser tests, where geolocation needs no manifest. **The Android packaging
layer had never been exercised.** Two lines, rebuilt, `aapt2 dump badging` confirms both
permissions inside the artifact. Close evidence is server-side: transitions file at `600`, one
transition, `context_block()` → `home since 20:22`, no coordinate anywhere in it.

**Rejected: the `@capacitor/geolocation` plugin.** It does not replace `navigator.geolocation`,
so adopting it meant rewriting `readPosition()` and breaking the 11 passing JS tests and the
browser path together. Two manifest lines keep one code path working in both places.

**A standing rule came out of the sideload, and it fixed a live exposure.**
`docs/INFRASTRUCTURE.md` told every session to run `python3 -m http.server 8888` **from the repo
root, with no `--bind`** — publishing `.env`, `vertex-key.json` and `data/personas/mike/**` to
anything on the local network. Now: stage the APK alone, bind to the Tailscale address, always
`http://100.70.67.45:8888/app-debug.apk` (Mike's rule). The IP is recorded as a deliberate
exception to *don't write down short-half-life values* — a Tailscale address is stable for the
life of the node, unlike the VM's reassigning external IP.

**The intake corpus turned out to be impossible as written, and the eval had never been run.**
The mailbox holds **33 messages from 9 senders**, total — the item asks for ~50, and at ~1/day
the 09-09 date buys six more. Two structural facts the item did not know: the swept
`records.jsonl` **stores no bodies by design**, so the pile the prompt pointed at could never
build the corpus; and `intake_email.fetch()` returns everything with bodies immediately, so no
waiting was needed either. `tests/build_intake_corpus.py` (new) writes stubs; Mike labelled all
33 in session. **`run_intake_eval.py` died in `resolve_persona()` before reading a fixture** —
it had never been run against a real corpus at all.

**The finding that outranks the gate: a single run cannot gate this.** Identical corpus,
identical agent file, consecutive runs returned **1, 3, 1, 1, 2** `action_required` false
negatives. `--runs N` now repeats and **gates on the worst run** — a classifier that silences an
obligation one time in five silences it in production.

**Mike ruled against relaxing the gate.** The gate fails on any non-`unclear` answer, which is
stricter than its own docstring — it fails on `correspondence`, which *surfaces*, so the message
still reaches the user. Proposed narrowing it to `digest`/`silent`, the outcomes that actually
hide something. He declined: *"unclear needs to come up more for this to have any validity in
the future."* Fix the model, not the test. **Recorded because the relaxation is the obvious
future suggestion and it has already been considered and refused.**

**The domain axis is the session's clear win, and it came from Mike reading his own mail.**
`intake.yaml` had claimed since 2026-08-19 that disposition and domain are independent axes;
`_effective_domain()` derived domain from category **one-to-one**, so `action_required` always
meant logistics and a bill needing payment could not reach finance. Three instances surfaced in
one labelling pass. His ruling: a triplet `{domain, category, importance}` — *"different defined
axes that can always be further expanded and are easy for simple models to categorize."*
Built: extractor returns all three, axes fail independently (a bad domain never collapses a good
category), precedence is user rule → model → category default.

**`work_vocation` gained `read_intake_queue` in the same change, deliberately.** A domain the
extractor can file to whose agent cannot read the queue is a black hole — mail sorted correctly
and never seen, worse than misfiling it somewhere read. Granting the tool is part of adding the
domain, not a follow-up (`.claude/rules/agent-files.md` § a named tool is a specification).

**Corrected mid-session, and the correction inverted a number I had reported.** I labelled the
Prudential thread `work_vocation`; Mike ruled it `finance` — a financial adviser writing about
his money is finance, however professional the correspondence reads. **The model had been right
and my labels wrong**, so the 85% domain score I reported was measuring my error. The rule now
sits in the agent file explicitly: *someone else's profession is not the recipient's vocation.*

**The `unclear` problem, and the A/B/C test that produced no winner.** Measured 2026-09-03: the
extractor answered `unclear` **zero times in 33 messages** despite an agent file encouraging it,
and the casualty was real — a budget alert that is both a money matter and a machine notice was
filed as `notification`, which is **silent**. A sharpened instruction pass moved it to one.
Mike proposed making the model counterargue against its own judgement. Tested three variants ×
three runs.

**Run 3 of every variant collapsed identically** (32/33 unclear, domain 0/20) on a transient call
failure — every call hitting the defensive `unclear` floor, which is the floor working, but it
voids a third of the data. **I nearly reported the resulting 37–44% "unclear rate" as a
result.** The per-run table is what caught it, and the outer log filter stripping `WARNING`
lines is what hid the cause. Reading runs 1–2 only: base 5/66 unclear at 1,1 gate misses;
**counterargue 12/66 but 2,2 misses and domain 14–15/20 — it raises doubt *and* degrades
accuracy**; confidence 10/66 at 1,1 with accuracy intact; both 6/66 at 1,1.
**Counterargue should not ship. The confidence axis is the better lever.**

**Why the confidence route was preferred over more prompt-pushing, stated because it is the
project's own principle:** a behaviour obtainable only by asking nicely is not a behaviour you
have. `apply_confidence_floor()` puts the decision in Python beside `_effective_disposition()`
and `filter_output()`, and it is **inert by default** — the threshold must come from a
confidence-vs-correctness sweep, never intuition, because that dial *is* the product: too low
silences obligations, too high hands the user back their inbox. Cost was checked and is not the
objection: ~120 extra output tokens/message on Flash-Lite is ~$4/year at 40 messages/day.

**Wisdom store: 80 → 72, and the proposal was stale.** Built from a 08-15 read of 59 entries; the
live store held 80, two of the 24 were already gone, and **21 entries written since had never
been assessed** — carrying the same faults, worse: language settings duplicated **three** ways
against `profile.yaml`'s real field, instructions-to-the-tool stored as facts
(`no_prudential_review_talk`), contact facts filed as wisdom. **Cleaning without fixing the
writer buys three weeks.** Groups C–G executed with Mike's per-group approval after a backup.

**`retire_wisdom_entries()` added rather than reusing `merge_wisdom_entries`.** The proposal said
"plain deletion" for eleven entries; this codebase has no delete by design, and forcing them
through a merge would have written a `merged_into` pointer naming an entry that does not hold the
same fact — a lie in the archive. Retirement records a reason instead.

**Group B (3 obligations) was held back and this was reported, not quietly dropped.**
Transplanting a recurring obligation needs the entry's *value* read and its recurrence judged.
That is a decision, not a move, so it belongs with Group A's sitting.

**Mike's open design question, answered and not built:** how to stop complaints being recorded as
wisdom. The answer is that `write_wisdom` **already** refuses a class of write and names the
right destination (`_RESERVED_KEY_TERMS`, for safety-flag facts). The complaint case is the same
shape: the test is *does this describe the user, or the tool?* What is missing is a drawer — the
specialists have exactly one durable-storage verb, so a complaint goes in it. A `FRICTION:` line
beside `WISDOM_PROPOSAL:`, routing to `log_quality_event`, is the other half. **Same structure as
the intake `unclear` finding: an escape hatch has to exist and be attractive, or the model routes
around it.** Not filed — he asked the question, he did not order the build.

**Two items left with a destination rather than a date, both by Mike's word.** The **Darwin API
key** was deferred into Mark 2 after the registration walkthrough was prepared and shown
(*"too involved"*) — do not re-propose it as a standalone (M). The **off-machine backup** was
declined twice with no date; 4.8 GB of dailies sit on the internal disk with Restic installed and
no drive mounted. **Recorded as an accepted named risk so it stops being an unfiled ⚠** — which
is the failure this session's governing rule exists to prevent.

**`VERTEX_CACHE_DISABLED` measured from the billing export: the recommendation is to flip it on.**
The 2026-08-21 finding that caching was net-negative for its whole life has **reversed** — over
14 days, 3.5 Flash-Lite cached reads cost $0.119 against the $1.19 they would have cost uncached,
for $0.13 of storage: **net +$0.94**. The sliding-TTL work fixed it. Mike flips it; no session
reads `.env`.

**Process note.** `## Machine log` grew 90 → 107 from this session's own eval traffic; those
signatures are test artifacts, not production signal. The three
`config/agents/intake_extractor_{counterargue,confidence,both}.md` files are A/B artifacts with
no routing entry — the driver swaps them over the production file and checksums the restore.
Delete them when the confidence question closes.
