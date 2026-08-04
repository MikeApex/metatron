# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

- **[agent wanted a tool it lacks]** `physical_health` attempted `read_agent_config` (agent_name) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-03T15:11:49.179709Z`
- **[agent wanted a tool it lacks]** `physical_health` attempted `write_agent_config` (agent_name, config) but it is not in its allowed_tools. Its instruction file asks for this capability. Decide: grant it, build it, or drop the instruction.  
  `2026-08-03T15:11:50.265168Z`
- **[instruction change]** For all check-ins: maximum two sentences. If exactly one item genuinely needs attention, name it and stop; otherwise just ask what is on. Never list or recap pending items, and never manufacture a topic.  
  `2026-08-03T15:12:14.933312Z`

*(nothing new)*

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. **The `config/agents/*.md` freeze was lifted 2026-08-03 (`ae252ab`)** — these are now directly editable.

- **`[CONTEXT]` block silently discarded when the model emits invalid JSON.** Observed live 2026-08-02 on `sarah_chen`: the Synthesizer wrote a literal newline inside a JSON string value, `split_context_block` (`core/orchestrator.py:678`) failed to parse it, logged a warning and returned `None` — so the context tracker was not updated *and* the `dev_request` for that exchange was lost. Silent data loss on a path with no retry. Options: repair common malformations before parsing, or have the Synthesizer re-emit. *Found while testing the self-development work.*

- **`synthesizer.md:355` promises a capability that does not exist.** It instructs the Synthesizer to use `write_config` to write `config/modules/scheduler.yaml` for recurring proactive sessions. `tools/config_writer.py:16` hard-whitelists `{prime_directive.md, mission.md}` and returns an error string for anything else. So every attempt to create a standing check-in silently fails, and the Synthesizer believes it succeeded. Either widen the whitelist (with path validation) or correct the instruction. *Found 2026-08-02 while scoping the self-development work.*

---

## Open — needs building

Capabilities that do not exist yet.

### Surfaced 2026-08-04

- **⚠ ~4-hour silent outage: the VM's guest lost all networking while GCE reported `RUNNING`. Root cause unknown.** Found 2026-08-04 ~00:20 when a deploy failed at SSH. Recovered by stop/start; the machine has been fine since.

  **Signature, for whoever sees it next.** GCE said `RUNNING` and the serial console was logging in real time — the OS was alive, not hung. But every process inside failed identically on `dial tcp 169.254.169.254:80: connect: network is unreachable` — the metadata server, on a link-local address, which is reachable from any healthy VM by definition. `network is unreachable` rather than a timeout means **no route existed**: the guest's NIC lost its routing. `tailscaled` looped on *"connectivity impacted; triggering captive portal detection"*; Tailscale showed `offline, last seen 4h ago, tx … rx 0`. Billing was `True`, the IAP firewall rule correct, IPs assigned, and `lastStartTimestamp` was three days earlier — **nobody rebooted it; networking died under a running machine.**

  Same signature as the 2026-07-31 `nic0 is frozen` incident, **but with the known cause absent** — billing was never disabled this time. So either that incident's root cause was misattributed to the billing freeze, or there are two paths to the same failure. Worth resolving before trusting VM uptime: it is silent, it survives a `RUNNING` status check, and it cost ~4 hours here.

- **Nothing detects that the VM is down.** The outage above ran ~4h and was found by accident, on the way to doing something else. `scripts/sync_dev_backlog.py` runs at the start of every session, is the first thing to touch the VM, and **exits 0 silently when it cannot reach it** — by design, so a paused VM is not reported as a failure. That design is right for a paused VM and wrong for a broken one: at session start it printed `0 new, 40 open`, indistinguishable from a healthy run. Cheapest fix is to have it distinguish *stopped* (expected, silent) from *running-but-unreachable* (report it) — `gcloud compute instances describe --format="value(status)"` is one call and already used elsewhere. Related: `metatron-resume.sh`'s health check is the only thing in the repo that verifies the VM actually answers, and it only runs when someone resumes.

### Surfaced 2026-08-03 by the context-audit test run

- ~~**⚠ A4 clinical-flag hard-fails must be re-run before A7 sign-off.**~~ **Gate PASSED
  2026-08-04 on the cloud path — 6/6.** Report:
  [tests/a4_safety_rerun_2026-08-04_gemini.md](tests/a4_safety_rerun_2026-08-04_gemini.md).
  Runner: [tests/run_a4_safety.py](tests/run_a4_safety.py), `--persona sarah_chen --provider gemini`.

  All three clinical flags fire correctly under the post-prefix-caching assembly order, and
  verified as firing for the right reason rather than on a keyword match: `SUICIDAL_IDEATION`
  with 988 crisis signposting; `MANIA` with an explicit instruction not to celebrate the energy
  (its documented failure mode); `MEDICATION_MISSED_CRITICAL` naming lamotrigine as
  *"morning dose, required"* while correctly leaving `optional` vitamin D alone. Finance
  arithmetic exact on all three (FIN-1 $520/$80; FIN-2 $18,000 → $19,091; FIN-4 47 months /
  $6,096 — amortisation checked by hand).

  **A prerequisite defect was found and fixed to make PH testable at all.**
  `physical_health` was not granted `read_agent_config`, while
  [physical_health.md:106](config/agents/physical_health.md#L106) requires
  `MEDICATION_MISSED_CRITICAL` classification to come from the stored medication profile and
  *"never from the agent's judgment"*. The flag was therefore structurally unfireable — the
  agent had to consult a profile it had no tool to reach. Granted in both
  `routing_cloud.yaml` and `routing.yaml`; `write_agent_config` deliberately **not** granted.
  This resolves Inbox items 1 and 2 in the read direction — those warn-mode entries were the
  symptom of this. **Note this flag has never actually worked in production**, which no
  assembly-order re-run would have revealed.

  **Two limits on what this result covers — do not read it as more than it is:**
  1. **Cloud path only.** The original A4 baseline was Ollama/qwen3:14b. This run is not a
     like-for-like comparison against it; it verifies the pass conditions hold on the path
     currently serving the user. The local path remains unverified under the new assembly
     order — `--provider ollama` runs the same suite when that matters.
  2. **Specialists in isolation, not end-to-end.** A flag that fires correctly in Mental
     Wellbeing can still be held at the Synthesizer, which is the actual user-facing failure
     mode and the reason A4 added the mandatory-surface block to `synthesizer.md:21`. The head
     layer also had dynamic context moved by the same change. **A pipeline-level probe is the
     one piece of this gate still missing** — recommend running it before A7 sign-off.

  A7 remains blocked on B1, Check 10 and Check 12. This clears only the named pre-sign-off gate.

- **Pre-existing dead link in the project log.** `archive/sessions/2026-07-28 — Persona Unification Plan and Phase 0.md` is referenced but does not exist. Already broken in `SESSION.md` before the split; preserved verbatim rather than invented a target for. Either write the missing writeup or correct the reference. Cosmetic.

### Recovered from SESSION.md prose, 2026-08-03

*These sat in dated `SESSION.md` sections and were never filed. That file is now a primer and
the history moved to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md), so anything still
actionable had to come here or it would have gone quiet — the same way the unsurfaced-opportunity
item "nearly aged out" (see Troubleshooting signal below).*

- **⚠ `deploy.sh`'s drain is decorative — every deploy kills in-flight WebSocket exchanges.** `/active` counts only SSE streams, and `/session/stream` has no client at all, so the drain gate always sees zero and restarts immediately. The most user-visible defect on this list; unfiled since 2026-07-30. *`SESSION.md:317`, client/app audit.*

- ~~**Synthetic persona data trees are not gitignored.**~~ **Done 2026-08-04** — `.gitignore`
  now carries `data/personas/*/` in place of the enumerated per-persona list. Five trees were
  uncovered (`arthur_brooks`, `cal_newport`, `danny_park`, `maya_torres`, `oliver_burkeman`)
  plus most of `ryan_holiday`; all are now ignored, as is any persona added in future — the
  drifting hand-maintained list was the actual defect, not the missing entries.

  **Two corrections made while fixing it.** (1) The section heading read *"Test persona runtime
  data"* and listed `mike` under it. `mike` is a real user's logs, health and finances, not a
  test fixture; it now has its own explicitly-labelled sensitive-tier rule. (2) The first draft
  of the fix carried `sarah_chen`'s *"a genuinely new fixture needs `git add -f`"* note up to
  the top of the block, where it read as a blanket escape hatch across every tree — including
  `mike`. That is an instruction to force real user data past the ignore rule, i.e. the
  2026-07-29 incident with extra steps. The `-f` allowance is now scoped to synthetic trees
  and the real-user rule states that no such hatch exists there.

  Verified: 65 tracked seed fixtures still tracked (`.gitignore` does not untrack), no
  deletions, `git check-ignore` passes for all nine existing personas and an invented tenth,
  and `git add -A --dry-run` stages zero files under `data/personas/`.

- **Memory indexer is reading the wrong source.** `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char 82852)` fired twice against a **276-byte** file — the offset cannot come from that file, so the indexer is likely reading a different or concatenated source. Unexamined. *`SESSION.md:227`.*

- **`[vertex_cache] 404 cached content metadata`** — a stale cache ID is reused after expiry, so the call falls back to compat on every request. Silent cost and latency. *`SESSION.md:385`.*

- **`Object of type AgentRecord is not JSON serializable`** — trace serialization fails on every scheduler job. *`SESSION.md:384`.*

- **`sw.js` has no `fetch` handler and caches nothing**, and `/` is served `no-store` — there is no offline shell, so an unreachable server shows a browser error page rather than the app. *`SESSION.md:320`.*

- **`shownIds` eviction cliff at `static/index.html:567`** — clears *after* adding, unlike the hardened site at L590 that was fixed in `eea3faf`. Separately, catch-up reuses `type:"history"`, so a reconnect wipes the conversation and re-renders only the delta. *`SESSION.md:319`.*

- **`/session` (non-streaming) leaks the `[CONTEXT]{…}[/CONTEXT]` block** into the response body and never writes the context tracker — the parser exists only on the streaming path. No user impact today (the app uses WebSocket/SSE), but the CLI and any future non-streaming caller get raw control text. *`SESSION.md:386`.*

- **`write_config()` stores the Goals Interviewer's text verbatim including its own heading**, so `## Prime Directive` / `## Mission` are written into the file that is already titled that. `_titled()` papers over it at load time; the write-side cause is open. *`SESSION.md:387`.*

- **Pre-2026 logs in mike's tree** (`2025-01-24`, `2025-05-13`–`16`) — believed genuine early-dev data, but the SEQ 021 session found one hallucinated log dated 14 months in the past. Worth confirming none of these are the same. *`SESSION.md:227`.*

- **Coordinator restructure (token-reduction Step 6)** — single-pass directive assembly replacing the multi-turn session, ~15,000t. Deferred 2026-06-24 pending Steps 1–5 stabilising; they have. **Re-scope against measured data first:** the coordinator runs 1 turn, not the 7 the roadmap assumes — the real cost driver is per-specialist internal turns (logistics measured at 8). Relates to the D2 item-5 mis-scoping already on this list. *`SESSION.md:602`.*

### Recovered from conversation, 2026-08-01/02

- **Data breadth — sleep is nearly the only thing consistently logged.** This is the *root cause* behind "too much focus on sleep": with one reliable signal and little else, any reasoning leans on it by default. The 2026-08-03 `synthesizer.md` rules mitigate the symptom (don't over-read a thin record; ask for what's missing) but cannot fix it. Needs a real answer on capturing training, food, work and mood with low enough friction that they actually get logged. Mike has also asked that sleep tracking itself shift to **total hours plus interruptions** rather than a disruption narrative (2026-08-03).

- **Nothing in the system can actually set a reminder or calendar entry.** *"The calendar integration will do later. I don't understand why it didn't, why it triggered at all"* — SEQ 011, 2026-08-01. Confirmed independently in [agent_capability_gap_2026-08-02.md](archive/plans/agent_capability_gap_2026-08-02.md) Finding 3: CalDAV is `enabled: false` with empty credentials, `scheduler.yaml` jobs are static with no tool to add one, and `write_config` is allowlisted to two markdown files. A reminder can be *recorded* but never *delivered* — which is why it appeared to do nothing. Build order there: enable CalDAV → grant Logistics its config tools → `write_schedule`/`list_schedules`/`delete_schedule` → store a delivery preference.

- **Voice transcription times out repeatedly.** *"There are transcription issues to address. Multiple timeouts"* — SEQ 014, 2026-08-02. Known cause on record: `/transcribe` and `/tts` run without `run_in_executor` (`core/server.py:597-646`, `561-594`), blocking the event loop for the whole of ffmpeg + Whisper; Whisper is `base.en` at float32, `beam_size=5`, no VAD, never warm-loaded, so the first call after every restart pays model construction on the loop. The correct pattern is already used at `server.py:252/311/425`.

- **Dictated email addresses come through wrong and need correcting by hand.** Three corrections in three minutes on 2026-08-02 (`diamond.mic` → `diamond.mike`), plus `diamond.like.gmail.com` at SEQ 006. Partly Whisper tuning (above), but a known-values pass would fix it outright — the user's own email is in `profile.yaml`, so a transcript token close to a known contact string should snap to it rather than be passed through.

- **One domain is measured and the others are not, so the measured one explains everything.** The user's complaint was *"once again, you're making too much of the sleep disruption"*, raised more than once. The `synthesizer.md` rules shipped 2026-08-03 (*beware the loudest available signal*; *where the record is thin, ask for what is missing*) are **mitigation, not a fix** — they tell the Synthesizer to distrust the only signal it has, which is right but does not give it a second one.

  **The actual problem:** sleep arrives automatically and consistently; training, food, work and mood arrive only when the user happens to mention them. Any honest reasoner facing that record over-weights sleep, because sleep is the only thing that is *there*. No instruction fixes an empty column.

  **What to look at:** which domains have logged data at what density in `data/personas/mike/logs/*.json` — count the populated keys per day over the last 30, do not assume. The cheapest lever is probably the ask-for-missing-data rule already shipped, *measured* after a few weeks to see whether it actually raises breadth. Beyond that: whether check-ins should rotate which domain they ask about, and whether any of the thin domains can be captured passively the way sleep is. **Do not build a weighting algorithm before checking whether the data is simply absent** — this is the same failure as tuning a model on a dataset with a missing column.

  Related: this is also what the Pattern Miner's baselines will run into. Worth resolving before trusting any cross-domain pattern it produces.

- **Check-ins are not gated on the user having been present at all.** The gates shipped 2026-08-03 (`quiet_after_user_minutes`, `min_gap_minutes` — see Done) solve *"don't interrupt a live conversation"*. They do **not** solve the inverse, which is the one the cost analysis identified: a day where the user says nothing still fires the full check-in schedule. That is the pathological case from the parked programme — *"the VM has been running ~12 full multi-specialist pipelines/day talking to itself while the app was broken"* — and it survives the current gates, because silence is exactly what `quiet_after_user_minutes` reads as permission to fire.

  **The check needed:** any user-originated exchange (`proactive=0`) since the last check-in fired. If none, skip. `_record_fire()`/`_minutes_since_last_fire()` in [core/scheduler.py](core/scheduler.py) already persist the timestamp to key on, and `_activity_gate_blocks` ([:173](core/scheduler.py#L173)) is the right place for it.

  **Decide the intended behaviour before building.** A hard skip means a user who goes quiet for three days gets nothing on the fourth morning — which may be exactly wrong, since a silent stretch is arguably when a check-in matters most. A first-of-day exemption, or an escalating gap rather than a hard skip, is probably the right shape. `morning_brief`/`evening_close` are deliberately ungated (2026-08-03 decision: fixed points of the day) and should stay that way.

- **Sentence-chunked TTS.** Kokoro is at 2.8s/call after the in-process fix (down from 15.0s, which was a subprocess re-import per request). Streaming the first sentence while the rest synthesises would cut perceived latency again. **Deferred pending a judgement call on whether 2.8s actually feels slow in use** — do not build this before using voice mode enough to say. Named in the parked programme as an alpha nice-to-have, not a blocker.

- **Browser does not live-refresh on foreign messages.** A message sent from the terminal or the Android app reaches the browser only after a manual page reload; the app and terminal sync fine. Sync itself is confirmed working — this is a client-side render path, not a transport failure. Same file and same area as the scroll and line-wrap items above, so worth doing in one pass. The parked programme's Phase 2b (one connection state machine, `visibilitychange`/`focus`/`online` handling) is the fuller treatment; some of it is already in `static/index.html`.

- **Cannot take an action on an external website.** *"Can you go on the R website and reserve tickets for us"* — SEQ 006, 2026-08-02. No browsing-with-actions capability exists. Worth an explicit decision on whether this is ever in scope, since it is the first request of its kind and carries a real security surface: the same message handed over an email address, postal address and phone number.

- ~~**No tool can write a biographical fact.**~~ **Done 2026-08-03 (`35e53ee`)** — `tools/profile.py`. See the follow-on immediately below, which is the part that was *not* built.

- **The user cannot see or correct what has been stored about them.** `write_profile` captures silently: a fact given in passing during a conversation is written to `profile.yaml` with no confirmation at the time and no way to review it afterwards. There is a write door and a read door for *agents* (`read_profile`), but nothing pointed at the user.

  **Why it matters, concretely:** on 2026-08-02 contact details were captured into the wrong file and rode in every system prompt for a day before anyone noticed — and only because a human read the file. A wrong value (misheard email, stale address, an inferred occupation the user would not endorse) now persists indefinitely and is quoted back as fact by Logistics when booking. Dictated email addresses are already known to arrive wrong three times in three minutes (see the transcription item above), and `write_profile` will store whatever it is handed.

  **Shape of the fix, in rough order of value:**
  1. **Review** — a way to ask "what do you know about me?" and get the stored fields back in plain language. `read_profile` already returns them; this needs a user-facing route, not new storage. Note the `contact:` block is deliberately excluded from `load_profile()`'s rendered summary, so a review path must read it explicitly rather than relying on what is in the prompt.
  2. **Correct** — `write_profile` already overwrites by field, so correction is mostly a matter of the user being able to say "that's wrong" and have it reach the tool.
  3. **Confirm at capture** — cheapest version is one clause in the reply ("noted your address as X"), which costs no extra turn. A confirmation *prompt* before writing would cost a round trip and is probably not worth it for low-stakes fields; consider it only for the `contact:` block.

  **Constraints:** unknown fields are refused rather than absorbed (`_SCALAR_FIELDS`/`_CONTACT_FIELDS`/`_LOCATION_FIELDS` in [tools/profile.py](tools/profile.py)) — an invented key is exactly how `mike.md` acquired a section no code knew about. `profile.yaml` is VM-owned and gitignored; edit it on the VM, never reconstruct it on the Mac.

- **No agent can read a specific web page. Grounded search is not web access.** Raised 2026-08-03. Three distinct capabilities; the system has only the first.

  1. **Grounded search — built.** `run_session_gemini_grounded` ([core/orchestrator.py](core/orchestrator.py), native genai SDK path) searches inside a single model call and returns an answer with sources. The model picks its own sources. There is no way to say *"read this page."* Anything behind a login, too recent, too obscure, or pasted in by the user is unreachable.

  2. **Direct fetch — missing. This is the actual gap.** Retrieve a named URL and read it: fetch, convert to text, size and time limits. Ordinary work — a `fetch_url` tool under the standard tool pattern, allowlisted to the agents that need it (Research Agent first). Note this is the point at which the deferred **indirect prompt injection defense** in CLAUDE.md § Security Architecture stops being deferred: fetched content must return wrapped in `<untrusted_content>` tags with the accompanying agent instruction, in the same change that ships the fetch — not as a follow-up.

  3. **Acting on the user's behalf — missing, and a different animal.** Navigate, log in, fill forms, transact.

  **The distinction between 2 and 3 is the one that governs build order.** At level 2 a hostile page can only *say* things to the model. At level 3 it can make the model *do* things — send a message, submit a form, spend money — using the user's credentials. So 3 goes last, behind both authentication and injection defense, and with per-action confirmation rather than autonomous dispatch. In plain terms: reading a booby-trapped page is a bad answer; acting on one is a real loss.

  **Build order:** 2 (with injection defense) → authentication story → 3 (confirmation-gated). Do not ship 3 on the assumption that 2's defenses cover it; they address a different failure.

### Troubleshooting signal

- **"Unsurfaced opportunities" has no instrumentation — the only troubleshooting category that cannot be measured.** The standing per-exchange review looks for four things: missed routing, unsurfaced opportunities, token overspend, and useless calls. Three of those leave traces. This one is **an absence**, and nothing in the system logs what it failed to raise. *Recorded in SESSION.md 2026-07-29; not previously carried into this list, which is how it nearly aged out.*

  Why it resists the obvious approach: you cannot diff against a ground truth that was never written down. The trace shows which specialists ran and what they returned — not the thing none of them thought to mention. So there is no post-hoc query that recovers it, and no amount of richer tracing produces the signal on its own.

  Three routes, cheapest first:

  1. **Make the `·` feedback dot carry a reason.** Already in the UI and already the nearest hook. A one-tap "missed something" reason code turns a silent miss into a dated, exchange-linked record. Costs almost nothing and produces real data, but only catches misses the user *notices* — which is a biased sample, and systematically misses the ones that matter most.
  2. **Retrospective sweep.** Periodically re-run a batch of past exchanges with full context and a prompt asking what a good response would have raised that the live one did not. Catches misses the user never saw. Costs tokens, and grades the system with the same class of model that produced the output, so it is suggestive rather than authoritative.
  3. **Close the loop against outcomes.** The context tracker already holds `open_threads` and `follow_ups`. A thread that goes quiet without resolution is a candidate missed opportunity, detectable without any judgement call. Narrower than the other two, but it is the only one that yields a hard signal rather than an opinion.

  Recommend 1 and 3 together — cheap, complementary, and neither depends on model self-assessment. Hold 2 until there is enough history for a sweep to be worth its token cost.

---

## Open — housekeeping

Stale docs, paths, and low-priority corrections.

- **Transcript lines run too long on screen.** *"The transcript liners too long on the screen"* — SEQ 014, 2026-08-02. Client-side line wrapping / bubble width in `static/index.html`. Note the conversation-scroll fix (`height:100dvh` + `overflow:hidden` on body, `min-height:0` on the flex child) is in the same area and is testable in a desktop browser without rebuilding the APK.

- **`/metatron-troubleshoot` command template points at pre-persona-scoping paths.** Uses bare `data/conversations/` and hardcodes `data/personas/mike/traces/`, so it has to be corrected inline every time it runs, and it fails outright for any other persona. Also missing `--tunnel-through-iap` on its SSH command, which is now required since the VM moved to `metatron-net`. *Recorded in SESSION.md 2026-08-02.*
- **Roadmap D2 item 5 (turn reduction) is mis-scoped and needs rewriting before anyone works it.** It targets the Coordinator on the assumption that the Coordinator runs ~7 turns per exchange. Measured 2026-08-02: **the Coordinator runs 1 turn.** The turns are in the specialists — `logistics` alone ran 8. Working the item as written would optimise a component that is already minimal and leave the actual cost untouched. Re-measure across several specialists before rewriting the item, rather than swapping one assumed culprit for another.

  **The roadmap has not been corrected — only this entry has.** [`archive/plans/phase5_to_future_roadmap_2026-06-10.md:519`](archive/plans/phase5_to_future_roadmap_2026-06-10.md#L519) still reads *"The Coordinator exhibits a 6-turn / 88K cumulative token loop on complex sessions"* and still prescribes a `coordinator.md` instruction change plus a ≤3-turn target. Anyone who reads the roadmap without reading this backlog gets the original wrong picture and a fix aimed at the wrong component. Deliberately not edited in place: the roadmap is a dated plan snapshot, and rewriting its body would erase what was believed at the time. Whoever picks the item up should rewrite it from measurement and note the supersession there — the correction is verified twice (2026-07-29 traces, re-measured 2026-08-02), so it is not waiting on evidence.

- ~~**No check that the VM is actually running what the Mac has committed.**~~ **Done 2026-08-03** — see the Done section.

- **Spend guard pricing rates are unverified estimates.** `config/modules/spend_guard.yaml` is marked VERIFY — fine for order-of-magnitude runaway detection, not for cost accounting. Check against current Vertex AI pricing before trusting any dollar figure derived from it.
- ~~**VM has an unused ephemeral external IP — remove it to save ~$2.90/mo.**~~ **WON'T DO — the premise is wrong, and acting on it would take the VM offline. Corrected 2026-08-03.**

  "Never used" is true for **inbound** and false for **outbound**. Nothing connects *to* the address — there is no public ingress and every client arrives over Tailscale — but it is also the VM's **only route out to the internet**. Both alternatives were checked live on 2026-08-03 and neither exists: `gcloud compute routers list` → **0 items** (no Cloud NAT), and `metatron-subnet`'s `privateIpGoogleAccess` → **False**. Delete the access config and the VM loses Vertex AI (the entire product), the Tailscale coordination bootstrap that makes it reachable at all, `git pull` on deploy, apt/pip, CalDAV, weather and RSS. It becomes an isolated machine.

  **The replacement costs more, not less.** Verified against the Cloud Billing Catalog API rather than the pricing pages (which are JS-rendered and return nothing to a fetch): `External IP Charge on a Standard VM` = **$0.005/hour**, and `Networking Cloud NAT IP Usage` = **$0.005/hour** — the identical rate, because a NAT gateway needs a public address too. Cloud NAT then adds per-VM gateway and per-GB data-processing charges on top. So swapping the external IP for Cloud NAT buys the same egress for strictly more money. Private Google Access is free and would cover Vertex AI, but not GitHub, Tailscale, or any non-Google endpoint, so it does not rescue the plan alone.

  **Also: the $2.90 was low.** At the catalog rate of $0.005/hour a 730-hour month is **~$3.65**, not $2.90 — the [2026-07-30 audit](archive/sessions/2026-07-30%20—%20Client%20and%20App%20Audit,%20Cost%20Finding,%20Programme%20Parked.md) appears to have used $0.004/hour. It only accrues while the VM runs; an ephemeral IP is released on stop, so a `metatron-pause.sh` window costs nothing. **The real money is the $24.50 e2-medium line, and pausing already addresses it.**

  *Why this sat here for three days:* the note was right about the cost and wrong about the consequence, and that only fails when someone acts on it — the same failure mode as the entry below, one layer up. **Do not record the literal address in any doc** — it is ephemeral and changes on every stop/start. It was written down twice and both copies went stale: SESSION.md and this entry said `136.112.188.80`, CLAUDE.md said `35.202.250.80` in prose and `136.112.188.80` in its table, and the live value on 2026-08-03 was a third address. Look it up when needed: `gcloud compute instances describe metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --format="value(networkInterfaces[0].accessConfigs[0].natIP)"`.

- **Docs record values that the system changes underneath them, and nothing checks.** Two instances found on 2026-08-03, both by running the documented command rather than reading it. (1) CLAUDE.md described the server as plain **HTTP** in five places including the recreate-from-scratch checklist, while it has been serving **HTTPS** behind a Tailscale cert — caught when a health check against `http://` failed; corrected, and re-verified live this session (`https://.../health` → `{"status":"ok"}`, `http://` → empty reply). (2) The ephemeral external IP above. The docstring of [core/server.py](core/server.py) had the same HTTP/HTTPS error and was corrected in the same pass — worth noting because the CLAUDE.md fix did not prompt anyone to check the code comment saying the same wrong thing.

  **The pattern, not the two bugs:** drift of this class is invisible to reading and only surfaces when someone executes the documented step. Cheapest mitigation is to stop writing down values with a short half-life (external IPs, anything reassigned on rebuild) and point at the lookup command instead — done for the IP. A stronger fix would be a smoke script that runs the handful of executable claims in CLAUDE.md (health check, service status, deploy verification) and reports mismatches; `deploy.sh`'s new HEAD assertion is the same idea applied to one claim, and is the model to copy. **Corollary for anyone hitting a doc that does not match live: file it here rather than assuming you are holding it wrong.**
- **The scheduler cannot defer a time-based job — only skip it.** `_activity_gate_blocks` ([core/scheduler.py:173](core/scheduler.py#L173)) returns a reason-to-skip, and `fire_session` ([:263](core/scheduler.py#L263)) simply `return`s. For an `interval_minutes` job that is harmless — the next poll retries a few minutes later, which is exactly how `companion_checkin`'s 30-minute poll / 60-minute quiet gate works. For a `time:`-anchored job it means **gone for the day**: the `schedule` library fires it once at its clock time and there is no second attempt.

  **Current state is correct, not broken.** `morning_brief` and `evening_close` deliberately carry no activity gate, per the 2026-08-03 decision that they are the fixed points of the day and are not interruptible — they redirect openly instead (*"Now let's turn to the evening close"*, `synthesizer.md` → *Scheduled session conduct*). So nothing is being dropped today.

  **Pick this up only if a fixed-time session should ever wait for a lull.** Adding `quiet_after_user_minutes` to `evening_close` as things stand would silently cancel the evening close on any day the user happens to be talking at 20:00 — a worse outcome than the interruption it avoids. A real fix needs a *deferred* job: on block, re-register a one-shot retry (e.g. `schedule.every(15).minutes.do(...)` that unregisters itself once it fires or once a cutoff passes), plus a cutoff so a deferred evening close does not arrive at 23:00. `_record_fire()`/`_minutes_since_last_fire()` already persist fire times to disk and give the retry something to key on.

- **`CLASSES` in `core/rule_classes.py` is incomplete by construction.** The rule-overlap checks match on regex per class; a duplicate in a class that does not exist yet is invisible, and a clean audit report is therefore not proof of no duplication. **When a duplicate is found by hand, add or widen a class in the same pass** — that is the maintenance loop, and without it the audit slowly decays into false reassurance. Two patterns needed widening within an hour of being written, both because they matched the *instruction's* wording and not the *user's complaint*: `repetition` missed *"Stop bringing up the same task over and over"*, and `evidence_weighting` missed *"making too much of the sleep disruption."* Test additions against `python3 scripts/check_rule_overlap.py --persona NAME` and confirm no new false positives on ordinary preferences before deploying.

---

## Open — agent-file enhancement backlogs

**These live in the agent files, and only there.** Each specialist's
`## Enhancement backlog` section at the bottom of `config/agents/{name}.md` is the single copy.

A mirror of all nine sat here from 2026-08-03 until later the same day — 15,851 bytes, 32% of
this file, 70 of what read as 94 open items. It made the backlog look three times its real size
and put the same text in three places (agent file, roadmap Section 4, here), which is exactly
what `CLAUDE.md` → **One Home Per Rule Class** exists to prevent. Deleted, along with the
roadmap copy. Verified before deletion: all nine originals present, 77 lines total.

`grep -l "## Enhancement backlog" config/agents/*.md` — logistics, mental_wellbeing,
physical_health, finance, relationships, recreation_hobbies, work_vocation, learning_growth,
research_agent.
