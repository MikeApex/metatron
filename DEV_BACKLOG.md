# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

*(nothing new)*

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. **The `config/agents/*.md` freeze was lifted 2026-08-03 (`ae252ab`)** — these are now directly editable.

- **`[CONTEXT]` block silently discarded when the model emits invalid JSON.** Observed live 2026-08-02 on `sarah_chen`: the Synthesizer wrote a literal newline inside a JSON string value, `split_context_block` (`core/orchestrator.py:678`) failed to parse it, logged a warning and returned `None` — so the context tracker was not updated *and* the `dev_request` for that exchange was lost. Silent data loss on a path with no retry. Options: repair common malformations before parsing, or have the Synthesizer re-emit. *Found while testing the self-development work.*

- **`synthesizer.md:355` promises a capability that does not exist.** It instructs the Synthesizer to use `write_config` to write `config/modules/scheduler.yaml` for recurring proactive sessions. `tools/config_writer.py:16` hard-whitelists `{prime_directive.md, mission.md}` and returns an error string for anything else. So every attempt to create a standing check-in silently fails, and the Synthesizer believes it succeeded. Either widen the whitelist (with path validation) or correct the instruction. *Found 2026-08-02 while scoping the self-development work.*

---

## Open — needs building

Capabilities that do not exist yet.

### Recovered from conversation, 2026-08-01/02

- **Data breadth — sleep is nearly the only thing consistently logged.** This is the *root cause* behind "too much focus on sleep": with one reliable signal and little else, any reasoning leans on it by default. The 2026-08-03 `synthesizer.md` rules mitigate the symptom (don't over-read a thin record; ask for what's missing) but cannot fix it. Needs a real answer on capturing training, food, work and mood with low enough friction that they actually get logged. Mike has also asked that sleep tracking itself shift to **total hours plus interruptions** rather than a disruption narrative (2026-08-03).

- **Nothing in the system can actually set a reminder or calendar entry.** *"The calendar integration will do later. I don't understand why it didn't, why it triggered at all"* — SEQ 011, 2026-08-01. Confirmed independently in [agent_capability_gap_2026-08-02.md](archive/plans/agent_capability_gap_2026-08-02.md) Finding 3: CalDAV is `enabled: false` with empty credentials, `scheduler.yaml` jobs are static with no tool to add one, and `write_config` is allowlisted to two markdown files. A reminder can be *recorded* but never *delivered* — which is why it appeared to do nothing. Build order there: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store a delivery preference.

- **Voice transcription times out repeatedly.** *"There are transcription issues to address. Multiple timeouts"* — SEQ 014, 2026-08-02. Known cause on record: `/transcribe` and `/tts` run without `run_in_executor` (`core/server.py:597-646`, `561-594`), blocking the event loop for the whole of ffmpeg + Whisper; Whisper is `base.en` at float32, `beam_size=5`, no VAD, never warm-loaded, so the first call after every restart pays model construction on the loop. The correct pattern is already used at `server.py:252/311/425`.

- **Dictated email addresses come through wrong and need correcting by hand.** Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus `diamond.like.gmail.com` at SEQ 006. Partly Whisper tuning (above), but a known-values pass would fix it outright — the user's own email is in `profile.yaml`, so a transcript token close to a known contact string should snap to it rather than be passed through.

- **Cannot take an action on an external website.** *"Can you go on the R website and reserve tickets for us"* — SEQ 006, 2026-08-02. No browsing-with-actions capability exists. Worth an explicit decision on whether this is ever in scope, since it is the first request of its kind and carries a real security surface: the same message handed over an email address, postal address and phone number.

- **No tool can write a biographical fact.** Closing the misfiling hole (`write_persona` now rejects non-preference sections) leaves the user with no way to give the system a durable personal detail at all — email, phone, address, occupation, household. The tool correctly refuses and says so, but the right destination has no door: `profile.yaml` is read-only to the runtime. Needs a `write_profile(field, value)` against a fixed field whitelist, keeping the unrendered `contact:` block out of the prompt. **Until this exists, biographical facts given in conversation are lost.** *Raised by closing the 2026-08-02 contact-details misfiling.*

---

## Open — housekeeping

Stale docs, paths, and low-priority corrections.

- **Transcript lines run too long on screen.** *"The transcript liners too long on the screen"* — SEQ 014, 2026-08-02. Client-side line wrapping / bubble width in `static/index.html`. Note the conversation-scroll fix (`height:100dvh` + `overflow:hidden` on body, `min-height:0` on the flex child) is in the same area and is testable in a desktop browser without rebuilding the APK.

- **`/metatron-troubleshoot` command template points at pre-persona-scoping paths.** Uses bare `data/conversations/` and hardcodes `data/personas/mike/traces/`, so it has to be corrected inline every time it runs, and it fails outright for any other persona. Also missing `--tunnel-through-iap` on its SSH command, which is now required since the VM moved to `metatron-net`. *Recorded in SESSION.md 2026-08-02.*
- **Spend guard pricing rates are unverified estimates.** `config/modules/spend_guard.yaml` is marked VERIFY — fine for order-of-magnitude runaway detection, not for cost accounting. Check against current Vertex AI pricing before trusting any dollar figure derived from it.
- **VM has an unused ephemeral external IP** (`136.112.188.80`). All access is over Tailscale. An in-use external IPv4 is ~$2.90/mo. *Recorded in SESSION.md 2026-07-31.*

---

## Done

### Check-in restraint — deployed 2026-08-03 (`ae252ab`..`HEAD`)

Four related complaints, one root cause and four fixes. **The cause was not an agent file:** `companion_checkin`'s own prompt instructed it to *"lead with the most useful outstanding item… be specific about which one and why it matters now"* — every 180 minutes, all day. An unresolved calendar item was therefore correctly surfaced six times.

- ~~**Check-ins fire regardless of whether a conversation is already live.**~~ *"Check ins… only need be done if there's not an ongoing dialogue"* — SEQ 020. Two opt-in gates in `core/scheduler.py`: `quiet_after_user_minutes: 60` (don't interrupt) and `min_gap_minutes: 180` (never more often than). `interval_minutes` becomes the poll rate, not the send rate. **Cost: strictly lower than before** — polling is local file reads with no model call, and `min_gap` preserves the old ceiling of ~5/day. Verified in production reading real conversation data. Only `companion_checkin` is gated; `morning_brief` and `evening_close` still land on their anchors by design.
- ~~**Check-in prompt too long / demands an outstanding item.**~~ Rewritten in both `config/templates/scheduler.yaml` (the baseline every new persona inherits — which also hardcoded "Mike" in a file used to provision other people) and mike's copy. Template cadence corrected 90 → 180.
- ~~**Repeating pending items until they become noise.**~~ *"Raise a thing once"* in `synthesizer.md`.
- ~~**Stop telling the user to "enjoy" things.**~~ Made universal in `synthesizer.md` rather than a per-persona preference, at the user's direction — "wasted language and too sycophantic."
- ~~**Over-indexing on sleep disruption.**~~ Two rules in `synthesizer.md`: explain a recommendation the first time and not every time (preserving the Constitution's "always explains its reasoning" for the case where it is genuinely new), and beware the loudest available signal — sleep dominates because it is the only thing consistently measured, not because it explains everything. **Where thin, ask for the missing data rather than over-reading what is there.**

**Root cause of the sleep problem is data breadth, not weighting** — still open, and the instruction changes above are mitigation, not a fix.

- **Synthesizer opened responses by recapping facts the user had just given.** Fixed in `synthesizer.md` under "Direction and prioritization"; deployed 2026-08-02 (`799aa3f`). *SEQ 002.*
- **Synthesizer echoed a user-claimed timestamp instead of checking the clock.** Fixed across `tools/ambient.py`, both head-layer agent files, and the message-receipt stamping in `core/server.py` / `core/orchestrator.py`; deployed 2026-08-02 (`b184d92`). *SEQ 008.* — **This closes the 2026-08-01 SEQ 011 request** *"You'll need to check your timestamps before messaging… Let's add that to things to do."* Raised by the user on 08-01, fixed on 08-02 before the backlog existed.

- **Specialists invented dates because they were never given a clock.** Logistics filed a record 14 months in the past. Fixed by injecting the system clock into the specialist branch of `_run_single_agent()`; deployed 2026-08-03 (`6601479`). *SEQ 021.* Same root family as the timestamp request above.
