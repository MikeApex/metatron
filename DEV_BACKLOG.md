# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

*(nothing yet)*

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. Note that `config/agents/*.md` are **frozen post-review** — each edit needs an explicit freeze lift.

### Recovered from conversation, 2026-08-01/02 (pre-dated the automatic capture)

- **Over-indexing on sleep disruption.** *"Once again, you're making too much of the sleep disruption"* — SEQ 020, 2026-08-02, and "once again" means it had already been raised. One interrupted night keeps being treated as a standing health signal. Physical Health / Synthesizer weighting: a single disrupted night is not a pattern and should not lead a response.

- **Repeating pending items until they become noise.** *"You've repeated the calendar thing about six times today. That's not constructive"* — SEQ 020. Open threads and follow-ups carry forward correctly, but nothing decays or suppresses them once raised and acknowledged. Needs a rule: an item already surfaced and not acted on is not re-raised every exchange.

- **Stop telling the user to "enjoy" things.** Two corrections logged within a minute (14:04, 14:05, 2026-08-02) after "Enjoy the museum." `config/personas/mike.md` already bans commendation and validation; this is the same instinct in a different shape. Extend the existing `Interaction Preferences` rather than adding a new one.

### Recovered — cross-cutting

- **Check-ins fire regardless of whether a conversation is already live.** *"Check ins are set for every [three] hours but only need be done if there's not an ongoing dialogue. Otherwise fold them into the conversation"* — SEQ 020. This is the **single largest cost lever on record**: the pathological case already happened, ~12 full pipelines/day talking to itself while the app was broken. Needs both a scheduler gate on recent user activity *and* an instruction change for how a due check-in folds into live dialogue instead of interrupting it. Cadence is already 90 → 180 min; that treated the symptom.

- **`[CONTEXT]` block silently discarded when the model emits invalid JSON.** Observed live 2026-08-02 on `sarah_chen`: the Synthesizer wrote a literal newline inside a JSON string value, `split_context_block` (`core/orchestrator.py:678`) failed to parse it, logged a warning and returned `None` — so the context tracker was not updated *and* the `dev_request` for that exchange was lost. Silent data loss on a path with no retry. Options: repair common malformations before parsing, or have the Synthesizer re-emit. *Found while testing the self-development work.*

- **`synthesizer.md:355` promises a capability that does not exist.** It instructs the Synthesizer to use `write_config` to write `config/modules/scheduler.yaml` for recurring proactive sessions. `tools/config_writer.py:16` hard-whitelists `{prime_directive.md, mission.md}` and returns an error string for anything else. So every attempt to create a standing check-in silently fails, and the Synthesizer believes it succeeded. Either widen the whitelist (with path validation) or correct the instruction. *Found 2026-08-02 while scoping the self-development work.*

---

## Open — needs building

Capabilities that do not exist yet.

### Recovered from conversation, 2026-08-01/02

- **Nothing in the system can actually set a reminder or calendar entry.** *"The calendar integration will do later. I don't understand why it didn't, why it triggered at all"* — SEQ 011, 2026-08-01. Confirmed independently in [agent_capability_gap_2026-08-02.md](archive/plans/agent_capability_gap_2026-08-02.md) Finding 3: CalDAV is `enabled: false` with empty credentials, `scheduler.yaml` jobs are static with no tool to add one, and `write_config` is allowlisted to two markdown files. A reminder can be *recorded* but never *delivered* — which is why it appeared to do nothing. Build order there: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store a delivery preference.

- **Voice transcription times out repeatedly.** *"There are transcription issues to address. Multiple timeouts"* — SEQ 014, 2026-08-02. Known cause on record: `/transcribe` and `/tts` run without `run_in_executor` (`core/server.py:597-646`, `561-594`), blocking the event loop for the whole of ffmpeg + Whisper; Whisper is `base.en` at float32, `beam_size=5`, no VAD, never warm-loaded, so the first call after every restart pays model construction on the loop. The correct pattern is already used at `server.py:252/311/425`.

- **Dictated email addresses come through wrong and need correcting by hand.** Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus `diamond.like.gmail.com` at SEQ 006. Partly Whisper tuning (above), but a known-values pass would fix it outright — the user's own email is in `profile.yaml`, so a transcript token close to a known contact string should snap to it rather than be passed through.

- **Cannot take an action on an external website.** *"Can you go on the R website and reserve tickets for us"* — SEQ 006, 2026-08-02. No browsing-with-actions capability exists. Worth an explicit decision on whether this is ever in scope, since it is the first request of its kind and carries a real security surface: the same message handed over an email address, postal address and phone number.

- **Confirm personal data points offered mid-conversation are actually stored.** Same message: *"You can archive these data points in personal information."* Unverified whether the address and phone number reached `profile.yaml`, the CRM, or nothing at all. Check before deciding anything else here.

---

## Open — housekeeping

Stale docs, paths, and low-priority corrections.

- **Transcript lines run too long on screen.** *"The transcript liners too long on the screen"* — SEQ 014, 2026-08-02. Client-side line wrapping / bubble width in `static/index.html`. Note the conversation-scroll fix (`height:100dvh` + `overflow:hidden` on body, `min-height:0` on the flex child) is in the same area and is testable in a desktop browser without rebuilding the APK.

- **`/metatron-troubleshoot` command template points at pre-persona-scoping paths.** Uses bare `data/conversations/` and hardcodes `data/personas/mike/traces/`, so it has to be corrected inline every time it runs, and it fails outright for any other persona. Also missing `--tunnel-through-iap` on its SSH command, which is now required since the VM moved to `metatron-net`. *Recorded in SESSION.md 2026-08-02.*
- **Spend guard pricing rates are unverified estimates.** `config/modules/spend_guard.yaml` is marked VERIFY — fine for order-of-magnitude runaway detection, not for cost accounting. Check against current Vertex AI pricing before trusting any dollar figure derived from it.
- **VM has an unused ephemeral external IP** (`136.112.188.80`). All access is over Tailscale. An in-use external IPv4 is ~$2.90/mo. *Recorded in SESSION.md 2026-07-31.*

---

## Done

- **Synthesizer opened responses by recapping facts the user had just given.** Fixed in `synthesizer.md` under "Direction and prioritization"; deployed 2026-08-02 (`799aa3f`). *SEQ 002.*
- **Synthesizer echoed a user-claimed timestamp instead of checking the clock.** Fixed across `tools/ambient.py`, both head-layer agent files, and the message-receipt stamping in `core/server.py` / `core/orchestrator.py`; deployed 2026-08-02 (`b184d92`). *SEQ 008.* — **This closes the 2026-08-01 SEQ 011 request** *"You'll need to check your timestamps before messaging… Let's add that to things to do."* Raised by the user on 08-01, fixed on 08-02 before the backlog existed.

- **Specialists invented dates because they were never given a clock.** Logistics filed a record 14 months in the past. Fixed by injecting the system clock into the specialist branch of `_run_single_agent()`; deployed 2026-08-03 (`6601479`). *SEQ 021.* Same root family as the timestamp request above.
