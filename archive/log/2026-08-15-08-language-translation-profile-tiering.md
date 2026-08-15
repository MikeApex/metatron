### 2026-08-15, eighth (a persona can be answered in its own language; profile detail stops riding every call) — `9a46608`, `b3ff108`, `8a7d1d7`, `4afbe3f`, `f9ffd2a` — **deployed by Mike**

Ran `/backlog attack`. **The attack itself was the first finding: it could not run.** Three of six
`## Now` items were unworkable — blocked on a real calendar candidate, on a mailbox with no
correspondence, and on decisions only Mike could make — and the two that *were* workable shared
`tools/context_tracker.py`, so they could not be given disjoint manifests. One worker ran, not
three. **`## Now` had stopped meaning "workable", which is what made the ranked list misleading.**

**Mike's fix, and it is structural:** time-gated items move to `## Later` with a `due:` marker.
`due_now()` in `scripts/sync_dev_backlog.py` already scanned **both** sections and surfaces a
`⚠ due:` clause on the sync line **at every session start** — so parked items wake themselves
without anyone running `/backlog deep`. Zero code change. The date is a **review date, not a
deadline**; pushing it is the correct outcome when a condition has not arrived. Also cleared a
spent `due: 2026-08-17` on `[DB-0809-02]` that would have false-woken on the 17th — `DUE_RE`
matches inside backticks.

**`[DB-0814-02]`'s close condition was checked against the VM and does not work.** "Read a week of
real `context.json` writes" cannot be done: the file is overwritten in place (no history), the
7-day expiry shipped the same day so `expired_open_threads` cannot be non-empty before ~08-22, and
`write_context_tracker` does not appear in traces at all. **A worker was scoped for this at
150–190k and would have spent it discovering it had nothing to measure.** Recorded as time-gated
with the cheapest instrumentation option named (append a dated audit line per write).

**`[DB-0810-15]` — the language feature, built across two rejected designs.**

The worker built the storage half and **found an error in its own brief rather than working around
it**: `load_profile()` lives in `core/orchestrator.py`, not `tools/profile.py`, and is a
hand-written per-field list. It left the render test *failing on purpose* with a comment, which is
why the item finished rather than appearing to. ISO 639-1 codes were chosen over free text so
`[DB-0815-02]`'s `edge-tts` locale tags (`bg-BG`) compose without re-migration.

**Two designs rejected before the shipped one, both by Mike, and the second rejection was the
better one:**
1. **Translation rules as prose in `synthesizer.md`** — rejected on cost: durable tokens in a file
   loaded on every head-layer call, for a setting that changes almost never.
2. **A `translate` tool the Synthesizer calls** — rejected here, not by Mike, on analysis: a tool
   call is a round trip *through* the model, so it costs an **extra turn on the most expensive
   model** — more than the cheap call it was meant to save — and it depends on the model choosing
   to invoke it, which `search_memory` and `write_agent_config` have both already failed to do in
   production. Mike's own second framing ("route the response through the translator before it
   exits Synth's purview") was the correct one and is what shipped.

**Shipped:** `core/translate.py`, Python post-processing, swappable backend, fails open.
- **Runs AFTER `filter_output()`.** Reversed, the English confidentiality regexes and the tier-4
  verbatim check go blind on translated text and nothing else would catch it.
- **Visible message only.** `[CONTEXT]`, history and traces stay English — `open_threads` is
  matched by exact text and word overlap, so a translated thread would silently break the expiry
  and grace logic shipped hours earlier.
- **Streaming is withheld** for a translated persona and delivered once. Streaming English and
  replacing it would show a language the user did not ask for, and TTS would already have spoken it.
- **Privacy resolved without a new ruling.** Cloud Translation API was researched and is
  defensible (no storage, no training) but is a **separate product** needing its own ruling; a
  model call on the Vertex path is pre-cleared by `ROADMAP.md` § 0's 2026-08-09 clarification.
  Backend left swappable so cost can reopen it deliberately.
- **Bulgarian speech-out** via `edge-tts`; Kokoro has no Bulgarian model, so an English voice would
  read it phonetically. Closes `[DB-0815-02](b)`.

**Verified live on Mike's persona and it works** — he confirmed Bulgarian in and out, then reverted
to English. **One defect found by that test: the app renders Latin transliteration though the agent
receives Cyrillic correctly** (`[DB-0815-04]`). Two candidates, and the cheap one first: the
translation prompt says "Bulgarian" without saying *in Cyrillic script*, which a model can satisfy
with romanisation.

**Found while verifying the render, and worth more than the feature:** Mike's `profile.yaml` `name`
field contained **"Contact name updated from Eva to Iva."**, and `other` held six facts about other
people. `load_profile()` renders all of it, so **every head-layer call was told the user's name was
that sentence** — the likely mechanism behind a correction he has made **five times**. Same class as
the 2026-08-02 incident `tools/profile.py` was built for, recurred in the opposite direction.
Data corrected on the VM; **the write path is not fixed** (`[DB-0815-05]`).

**`_PROMPT_EXCLUDED` was enforcing nothing** — one reference in the codebase, its own definition,
while `load_profile()` rendered an unstated parallel policy. Now derived. `health_notes` joined it
on Mike's rule: **detail the tool learns about a user belongs at the level that needs it, retrieved
when relevant, not broadcast on every call.**

**CRM dump on request exposed three faults in eight records.** `Eva` and `Iva Diamond` were **one
person** (family, surname Diamond, first name spoken as "Eva") — merged by hand with an archive
pointer, because **the CRM has no merge or delete tooling at all** and the project's standing
archive-on-merge rule is unimplemented there. `eva@example.com` was a **fabricated** address on the
IANA documentation domain, stored as fact (`[DB-0815-06]`). `Kathaleen`/`Kathleen` differ by
speech-to-text; Mike wants the *class* caught, not that instance (`[DB-0815-07]`).

**Standing design rule, Mike, 2026-08-15:** clinical hard-fails do **not** gate feature work until
the tool goes live in Alpha or Beta. Recorded so it stops resurfacing as a blocker on every
safety-adjacent build. The A4 gap a translated persona opens is filed, not treated as blocking.

**Rejected:** running A4 now (no persona is translated, so it is a no-op and would prove nothing);
forcing a session against Mike's real persona to test translation (writes a synthetic exchange into
his real history — he tested it himself instead).
