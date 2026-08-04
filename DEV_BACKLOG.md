# Development Backlog

Every change Metatron needs, in one place. Two sources feed it:

- **Mike, in conversation.** Requests are triaged in-session and recorded automatically; `scripts/sync_dev_backlog.py` pulls them from the VM into `## Inbox` below.
- **Development sessions.** Anything found while working — bugs, stale docs, deferred fixes — added directly to the Open sections.

**`## Inbox` is machine-written. Do not hand-edit it.** Triage entries out of Inbox into an Open section (rewriting them properly), or into Done. The sync script only appends; it never touches anything below Inbox.

Refresh: `python3 scripts/sync_dev_backlog.py`

---

## Inbox

*(nothing new — last triaged 2026-08-05)*

---

## Triaged out of Inbox — 2026-08-05

Fourteen entries cleared. Nine were `TOOL_DENIED` warnings covering six distinct cases; each was
matched to the conversation it happened in before any decision was taken, because the denial
text alone says what was blocked and not what the agent was trying to do.

- ~~`logistics` → `read_agent_config`, `write_agent_config` (×4), `search_memory`,
  `write_archive`; `work_vocation` → `search_memory`; `finance` → `read_archive`~~ —
  **granted 2026-08-05, `9361537`.** Not a widening on request: `logistics.md:45` makes the
  config store mandatory, `:189` states the recurring-obligation inventory lives there because
  *"obligations are data rows, not scheduled jobs"*, and `:187` assigns `write_archive` four
  named lists. **`write_schedule` was already granted 2026-08-03 (`2f74cd2`) and did not stop
  the denials** — it is a different mechanism for a different thing, exactly as `:189` says.
  Corroborated on disk: `sarah_chen`'s `logistics.json` already held `recurring_obligations`,
  written through warn mode.

- ~~`physical_health` → `read_agent_config`~~ — **already granted 2026-08-04 (`b3229ff`)**;
  the warn-mode entry predated the grant. Stale on arrival.

- **[DB-0805-01] `physical_health` can now write the profile its own safety flag reads.**
  `write_agent_config` was granted 2026-08-05 (`9361537`), reversing the 2026-08-04 hold, with
  `medication_profile` guarded in Python (`_GUARDED_KEYS`,
  [tools/agent_config.py](tools/agent_config.py)). The guard is narrow by design and **only
  covers the one key**. `physical_health.md:106` requires `MEDICATION_MISSED_CRITICAL` to
  classify from stored data and *"never from the agent's judgment"* — if any other flag grows a
  similar dependency, its key needs adding to the same set. **B2 should decide whether guarded
  keys are the right mechanism or whether the confirmation gate supersedes them.**
  *filed 2026-08-05 by dev session (Claude Code) · found while applying the grant decisions ·
  origin SEQ — · verified 2026-08-05 against tools/agent_config.py*

- **[DB-0805-02] Email approval prompt does not render in the app, and no live Google Contacts
  read exists.** Two user reports, 2026-08-04 12:42Z and 12:49Z. **Owned by the CalDAV/email
  window** — filed here for completeness, not for this session to work.
  *filed 2026-08-04 by Mike via Synthesizer · origin SEQ 016/017 · not verified — other window's
  active work*

- **[DB-0803-01] Text doubling / input cut off mid-sentence in the app.** Reported 2026-08-03
  17:12Z. The calendar half of the same report is **done** (CalDAV live 2026-08-03, `cfcd212`).
  The text-doubling half is untouched and unverified — `static/index.html`. Note SEQ 004 on
  2026-08-04 shows the Synthesizer asking whether the features being tested were aimed at *"that
  text doubling bug"*, so it was still live then.
  *filed 2026-08-03 by Mike via Synthesizer · origin SEQ 012 · not verified this session*

---

## Triaged out of Inbox — 2026-08-04

- ~~**Remove the voice activation toggle from the app** (×2 — `2026-08-03T17:16Z`,
  `2026-08-04T07:57Z`)~~ — **superseded, closed 2026-08-04 by Mike's decision** (*"Voice is
  completed as far as I can see. Remove any requests for it. I can always rerequest."*).

  Both requests were about voice output cutting into message input. What shipped addresses
  the cause rather than removing the feature: a persisted toggle **defaulting to off**
  (`fe0d688`), so behaviour matches "removed" unless switched on, plus the fix that actually
  mattered (`8e5c47e`) — speech is now blocked at every point playback could begin, including
  after the `/tts` await and after `decodeAudioData`. The first attempt only *stopped* audio
  already playing, which did not fix the reported bug at all: the delay complained about **is**
  the `/tts` await, so a reply could still start speaking mid-recording.

- ~~`physical_health` attempted `read_agent_config` (×3 warn-mode entries)~~ — **granted
  2026-08-04**, `b3229ff`, in both `routing_cloud.yaml` and `routing.yaml`. Not a judgement call:
  `physical_health.md:106` requires `MEDICATION_MISSED_CRITICAL` to be classified from the stored
  medication profile and *"never from the agent's judgment"*, so without the read grant the flag
  was structurally unfireable. **Not yet deployed** — see the deploy-blocked item below.

- ~~**`physical_health` attempted `write_agent_config` — still open, deliberately.**~~ —
  **settled 2026-08-05, `9361537`.** Granted, with `medication_profile` guarded in Python rather
  than the whole tool withheld. The blanket denial was costing the agent an ordinary config store
  that every other specialist has, while the thing it protected — that
  `MEDICATION_MISSED_CRITICAL` must classify from a profile the agent did not author — is
  preserved exactly by the narrow guard. See **[DB-0805-01]** for the residual concern.
  The `logistics` and `finance` entries this one pointed at were resolved in the same pass.

---

## Open — instruction changes

Behavioural changes to how agents judge, prioritise, or decide what to raise. Applied by editing agent instruction files. **The `config/agents/*.md` freeze was lifted 2026-08-03 (`ae252ab`)** — these are now directly editable.

- **`[CONTEXT]` block silently discarded when the model emits invalid JSON.** Observed live 2026-08-02 on `sarah_chen`: the Synthesizer wrote a literal newline inside a JSON string value, `split_context_block` (`core/orchestrator.py:678`) failed to parse it, logged a warning and returned `None` — so the context tracker was not updated *and* the `dev_request` for that exchange was lost. Silent data loss on a path with no retry. Options: repair common malformations before parsing, or have the Synthesizer re-emit. *Found while testing the self-development work.*

- ~~**`synthesizer.md:355` promises a capability that does not exist.**~~ — **stale, closed
  2026-08-05. Already fixed by the 2026-08-03 Phase 4 scheduler-grants session; this entry was
  never crossed off.** Checked against current source: `synthesizer.md:408` documents
  `write_config` scoped to exactly `{prime_directive.md, mission.md}`, matching
  `tools/config_writer.py:16`'s `ALLOWED_FILES` — no mention of `scheduler.yaml` anywhere near
  it. Recurring proactive sessions go through the separate, already-correct
  `write_schedule`/`list_schedules`/`delete_schedule` tools (`synthesizer.md:406`,
  `tools/schedule.py:85`), which write `data/personas/{p}/schedules.yaml` — deliberately not the
  gitignored, hand-copied `config/modules/scheduler.yaml`.
  *Original entry filed 2026-08-02 · verified stale 2026-08-05 against synthesizer.md and
  tools/config_writer.py/schedule.py*

---

## Open — needs building

Capabilities that do not exist yet.

### Surfaced 2026-08-04 (evening)

- **[DB-0804-02] Track B security hardening (B1–B4) scoped, not started.** **Wave 1 — ready
  now, no dependency on integration count:** B1a (direct-injection red-team suite, 9 categories,
  live against Coordinator/Synthesizer); B2 remainder (`research_agent` missing `allowed_tools`
  — currently defaults to all 53 tools; extend the existing `POST /confirm` gate to
  `write_agent_config`/`write_config`; formalize confused-deputy enforcement + a regression
  test; upgrade `filter_output()` from substring to regex/semantic matching; confirm
  `run_model_conference` is scoped head-layer-only); B4 (5 degradation paths — specialist
  failure mid-pipeline, Ollama-unavailable fail-closed message, context-tracker fallback,
  retry-with-backoff, max-chain-depth handling, partial-fan-out threshold — plus 2
  deliberate-failure tests). ≈4.5–5.5 sessions. **Wave 2 — gated on Track E reaching
  feature-complete for this phase:** B1b (indirect-injection tests — email/calendar/web/contact
  sources — spot-checked per integration as it ships, one consolidated pass once integrations
  settle) + B3 (baseline doc at `archive/security/security_baseline_*.md`, to fold in a new
  recurring security-review protocol: event-triggered per-integration spot-check + a
  quarterly/per-phase health-check re-run of B1a + B2's cross-agent exfiltration probes).
  **Also found while scoping:** `SESSION.md` previously stated PoLP tool permissions were "in
  warn mode" — the code shows the `allowed_tools` whitelist is already enforced; corrected in
  `SESSION.md` this session. Full detail:
  [archive/sessions/2026-08-04 — B1-B4 Security Scoping.md](archive/sessions/2026-08-04%20—%20B1-B4%20Security%20Scoping.md).
  *filed 2026-08-04 by Mike via dev session (Claude Code) · scoping only, not verified by
  execution*

### Surfaced 2026-08-04

- **`ROADMAP.md` Track D is ~14 KB of a 47 KB file that loads on every `/metatron-code`, and parts of it have shipped.** D2 named cost analysis and model validation; the spend guard, rate limiter and measured token economics all landed 2026-08-02. Trimming it would take the cold-start load from ~26k to roughly ~22k. **Deliberately not done 2026-08-04:** a parallel window was committing to that file the same day, and trimming by line range is how the first pass silently carried completed item A6 into the abridged copy. **If picked up: go item-by-item against `SESSION.md` and `archive/PROJECT_LOG.md`, never by line range**, and check no window is mid-edit. Better done by whoever is actually working Track D than by a token-reduction pass. *Deferred from the context-file second pass, `a5ba388`.*


- ~~**⚠ `deploy.sh`'s preflight guard checks the wrong machine**~~ — **NOT A BUG. Withdrawn 2026-08-04 after checking the file.** Left in place rather than deleted, because the reasoning below is plausible and someone will re-derive it.

  **The guard runs on the VM.** `deploy.sh:40` opens `bash -s <<'REMOTE'` and the heredoc closes at line 103; line 42 is `cd ~/multi-model-mcp`; the guard is line 54 — inside, executing in the remote shell, greping the VM's `.env`. The heredoc is quoted, so nothing expands locally. (A `grep` for the check appears to match twice; the second, ~line 67, is the remediation command *echoed inside the abort text*, not a second test.)

  **What was actually observed:** `git push origin main` is **line 30 — before the SSH block**. A push happening is not evidence the guard passed. On 2026-08-04 the SSH failed on the outage, so the guard was never *reached* rather than bypassed. Confirmed the other way too: once `METATRON_AUTH_PASSWORD` was appended to the VM's `.env`, the same script deployed `8e5c47e` cleanly and its HEAD assertion verified.

  **Verify before re-filing** (not by reading — that is how this was got wrong twice): `awk` the line numbers of `<<'REMOTE'`, `^REMOTE$` and the guard, and check the guard falls between them.

  *Original entry, preserved:* the guard reads the Mac's `.env` while its message says the VM's; the Mac has the variable and the VM did not; therefore it passes on the machine you deploy from, always.

  **This is not theoretical — it happened on 2026-08-04.** A deploy passed the guard, pushed to GitHub, and reached the SSH step; **only an unrelated 4-hour VM outage stopped the `git pull`.** On a healthy VM it would have completed and left the server in a systemd crash loop, which is precisely the outcome the guard's own comment says it exists to prevent (*"the failure surfaces as a systemd crash loop that looks nothing like a deploy problem"*).

  **Fix:** check the remote. One SSH round-trip before the pull — `gcloud compute ssh … --command="grep -q '^METATRON_AUTH_PASSWORD=' ~/multi-model-mcp/.env"` — and abort on non-zero. Note the guard is otherwise well-designed: it runs before `git pull` so a refusal leaves the VM untouched, and `22e179d` fixed its remediation advice to append the variable rather than scp the whole file (correct — the VM's `.env` holds values the Mac's does not). Only the test target is wrong. *Owner note: `deploy.sh` was being edited by a parallel window on 2026-08-04; check current state before editing.*

- **⚠ ~4-hour silent outage: the VM's guest lost all networking while GCE reported `RUNNING`. Root cause unknown.** Found 2026-08-04 ~00:20 when a deploy failed at SSH. Recovered by stop/start; the machine has been fine since.

  **Signature, for whoever sees it next.** GCE said `RUNNING` and the serial console was logging in real time — the OS was alive, not hung. But every process inside failed identically on `dial tcp 169.254.169.254:80: connect: network is unreachable` — the metadata server, on a link-local address, which is reachable from any healthy VM by definition. `network is unreachable` rather than a timeout means **no route existed**: the guest's NIC lost its routing. `tailscaled` looped on *"connectivity impacted; triggering captive portal detection"*; Tailscale showed `offline, last seen 4h ago, tx … rx 0`. Billing was `True`, the IAP firewall rule correct, IPs assigned, and `lastStartTimestamp` was three days earlier — **nobody rebooted it; networking died under a running machine.**

  Same signature as the 2026-07-31 `nic0 is frozen` incident, **but with the known cause absent** — billing was never disabled this time. So either that incident's root cause was misattributed to the billing freeze, or there are two paths to the same failure. Worth resolving before trusting VM uptime: it is silent, it survives a `RUNNING` status check, and it cost ~4 hours here.

- ~~**Nothing detects that the VM is down.**~~ — **fixed, closed 2026-08-05 (found already
  shipped in `10bf194`, 2026-08-04, never crossed off).**
  [scripts/sync_dev_backlog.py:227-233](scripts/sync_dev_backlog.py#L227) now calls
  `vm_status()` and appends `⚠ VM running but unreachable` when the VM reports `RUNNING` but
  the sync can't reach it — distinct from the silent, expected case of a stopped VM. **This is
  live and firing right now**: this session's own startup hook printed exactly that warning.
  *filed 2026-08-04 by dev session · fixed 2026-08-04 `10bf194` · closed 2026-08-05, observed
  firing live at this session's own startup*

### Surfaced 2026-08-04 by the outward-actions scope decision

Full reasoning: [archive/plans/outward_actions_scope_2026-08-04.md](archive/plans/outward_actions_scope_2026-08-04.md).

> **✅ A, B and C were decided and built 2026-08-04** (`ca993fe`, `15b9a41`, deployed). The
> three items below are kept for their reasoning; the "proposed"/"awaiting" framing in them is
> historical. **What Mike chose differed from what was recommended in two places:** B is
> **out-of-band** confirmation (server-recorded tap, not a model-mediated token), and C is
> **CRM contacts**, not self-only. Those two hold each other up — **if B is ever downgraded to
> model-mediated consent, C must shrink back to self-only in the same change.**

**Still open from this block:**

- **The SMTP send path has never been exercised.** Every test — 11 unit cases and the live
  VM run — stops at the confirmation gate, deliberately, so no mail has ever left this system.
  `smtplib` config (`smtp_host`/`smtp_port` in `email.yaml`, STARTTLS, app-password login) is
  therefore **untested code on the first real send**. Expect the first send to be the test:
  do it to Mike's own address, with the journal open. Gmail SMTP on port 587 with an app
  password is the assumption; it has not been proven for this account, only IMAP has.

- **No pipeline-level injection probe has been run.** The 2026-08-04 probe tested three layers
  in isolation — wrapper escape, marker detection, and the tool's recipient refusal. What has
  *not* been run is the real thing: a hostile email sitting in the actual inbox, read through
  a full Coordinator→specialist→Synthesizer exchange, to see whether the pipeline surfaces it
  as analysis or acts on it. The layer that refuses in code will hold regardless; the open
  question is **agent behaviour**, which is exactly what the isolated tests cannot show. Fold
  into B1's red-team suite rather than building a separate harness.

- **Extend the gate to `write_agent_config` / `write_config`.** B2 requires a
  human-in-the-loop gate on these and `tools/confirm.py` now provides one, but they are not
  wired to it. This is also the standing answer to the open denial entries above
  (`physical_health`, `logistics` reaching for `write_agent_config`): gate it rather than
  granting or refusing outright.

- ~~**⚠ The confirmation gate is a prompt, not a control (Decision B).**~~ — **built, closed
  2026-08-05.** This entry predates the 2026-08-04 build (`ca993fe`, `15b9a41`). Verified today:
  [tools/confirm.py](tools/confirm.py) implements exactly the shape this entry proposed —
  `request()` returns a `PENDING_CONFIRMATION` token and performs nothing;
  `POST /confirm` ([core/server.py:702](core/server.py#L702)) is the only writer that can
  approve one; `consume()` gates the second call. `send_email` is wired to it end-to-end
  ([tools/mail.py:278-306](tools/mail.py#L278)) — two-step by design, first call always returns
  `PENDING_CONFIRMATION` and sends nothing. **What's still genuinely open is the separate bullet
  below** — `write_agent_config`/`write_config` are not yet wired to this same mechanism.
  *filed 2026-08-04 · superseded by the 2026-08-04 build · closed 2026-08-05 against
  tools/confirm.py, core/server.py:702, tools/mail.py:278-306*

- **Provenance modifier for the action tiers (Decision A).** The tiers classify actions by what they do, not by who proposed them. That was sufficient until `fetch_url` and `read_email` shipped (2026-08-04) and content written by strangers began entering the pipeline. `<untrusted_content>` marks the *data*; nothing marks an *action derived from* it.

  The failure case is not exotic: an email saying *"reply YES within 24 hours or your reservation is released"* satisfies every existing tier, and a legitimate email would be worded identically. Proposed rule — an action whose need is evidenced only by untrusted content is Confirm First regardless of tier and regardless of opt-in, and the confirmation must **quote the source** so the user confirms the evidence rather than just the act. One row plus a paragraph in the existing table; not a second framework.

- ~~**`send_email` restricted to the user's own address (Decision C).**~~ — **built, closed
  2026-08-05.** [tools/mail.py:229-262](tools/mail.py#L229) enforces it in Python: `_known_recipients()`
  allows the user's own addresses (`account_email` / `contact.email` from `profile.yaml`) plus
  saved CRM contacts — the docstring cites this exact decision by name ("Roadmap item 5, Decision
  C") and explains why it's enforced here rather than in an agent instruction: an injected email
  that talks the model into a different recipient fails this check regardless of how convincing
  it was. Broader than self-only per the block's header note (CRM contacts included, a deliberate
  choice), gated on Decision B which is also built (see above).
  *filed 2026-08-04 · built 2026-08-04 `ca993fe`/`15b9a41` · closed 2026-08-05 against
  tools/mail.py:229-262*

- **Not opened, deliberately:** credential store, agentic browsing (level 3), arbitrary-recipient email, transactions. The last three are gated on a credential store that does not exist and on the gate above.

- **`research_agent` omits `allowed_tools`, so it holds *all 53* tools** — including `fetch_url`, `read_email`, and every write tool. Pre-existing, not introduced by the 2026-08-04 work, and **deliberately not fixed there**: adding a list would silently strip every other tool from the grounded-search path, which is a behaviour change well beyond that item's remit. The file comment says *"bare mode (no personal tools)"*, which is the opposite of what an omitted `allowed_tools` means in `core/router.py` — so the config reads as more restrictive than it is. Belongs to **B2** (per-agent tool injection). Verify what the grounded path actually passes before changing it.

- **APK rebuild pending — password reveal toggle (`819de75`) *and* the dismissable transcription readout (2026-08-04).** Both committed, neither built. The readout change alters UI structure, which is a named rebuild trigger in `CLAUDE.md`; the password toggle was deferred by agreement (the session had already rebuilt twice). One rebuild covers both. `static/index.html` on the server already serves both to the browser PWA — **but the readout change has not been deployed either**, so `./deploy.sh` comes first.

- **Test the dismissable transcription readout — code-verified 2026-08-05, live dictation test
  still not run.** Re-checked `static/index.html` against every named pass condition:
  [:104-125](static/index.html#L104) caps `#transcript` at `max-height: 4.5em` with
  `line-height: 1.5` (= exactly 3 lines), `overflow-y: auto` for internal scroll;
  [:637](static/index.html#L637) sets `TRANSCRIPT_TIMEOUT_MS = 12000`; the close button
  ([:466](static/index.html#L466), [:655](static/index.html#L655)) calls the same `hideTranscript()`;
  `#transcript-wrap { display: none }` by default with `.shown` toggling `flex`
  ([:105,114](static/index.html#L105)), so footer height is untouched while hidden. Every
  clause the test asks for is present in code. **What this session could not do: dictate 30+
  seconds of real speech into a browser and watch it.** No mic/browser access here — this
  remains an actual human test, owed before it's called done.
  *filed 2026-08-04 · code-verified against every pass condition 2026-08-05 · live test still
  outstanding*

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

- ~~**Pre-existing dead link in the project log.**~~ — **fixed, closed 2026-08-05.**
  [archive/PROJECT_LOG.md:1165](archive/PROJECT_LOG.md#L1165) pointed at a "Plan and Phase 0"
  session file that was never written. The same section's content is covered by
  `archive/sessions/2026-07-28 — Persona Unification Complete (Phases 0-8, Strict Mode Live).md`
  — already the target of two other links in this log for adjacent parts of the same work.
  Repointed rather than inventing a new writeup.
  *filed 2026-08-03 by dev session · fixed 2026-08-05 against archive/PROJECT_LOG.md:1165*

### Recovered from SESSION.md prose, 2026-08-03

*These sat in dated `SESSION.md` sections and were never filed. That file is now a primer and
the history moved to [archive/PROJECT_LOG.md](archive/PROJECT_LOG.md), so anything still
actionable had to come here or it would have gone quiet — the same way the unsurfaced-opportunity
item "nearly aged out" (see Troubleshooting signal below).*

- ~~**[DB-0803-07] ⚠ `deploy.sh`'s drain is decorative — every deploy kills in-flight WebSocket
  exchanges.**~~ — **fixed, closed 2026-08-05 (found already shipped in `10bf194`, 2026-08-04,
  never crossed off).** The WS exchange loop now holds the same `_active_lock` as the SSE path
  around the full in-flight block, counting exchanges not connections —
  [core/server.py:616-618,668-669](core/server.py#L616). Verified live against current source,
  not just the commit message.
  *filed 2026-07-30 by dev session (client/app audit) · recovered from SESSION.md:317
  2026-08-03 · fixed 2026-08-04 `10bf194` · closed 2026-08-05 against core/server.py:616-669*

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

- **[DB-0803-03] Memory indexer is reading the wrong source — hypothesis now confirmed.**
  Original entry: `[background] index log 2025-05-22 failed: Extra data: line 557 column 2 (char
  82852)` against a 276-byte file, so the offset could not have come from the named file.

  **Verified 2026-08-05 and sharper than filed.** The VM journal still carries it, but the date
  has moved on while the offset has not: `index log 2026-08-04 failed: Extra data: line 557
  column 2 (char 82852)` — **the identical byte offset for a completely different log file**,
  three times on 2026-08-04. A shared offset across unrelated files is not a coincidence about
  the files; the indexer is parsing something fixed. `core/background.py` is where to start, and
  the thing to find is what it opens instead of the per-day log.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:227 · verified 2026-08-05 against
  the VM journal — still firing*

- ~~**`[vertex_cache] 404 cached content metadata`**~~ — **believed fixed; closed 2026-08-05.**
  Registry eviction on a 404 is present at [core/orchestrator.py:1417-1424](core/orchestrator.py#L1417)
  (`"not_found" in text or ("404" in text and "cach" in text)` → `_vertex_cache_registry.pop`).
  **Last occurrence in the VM journal: 2026-07-29 13:05** (cache id `3167247740363079680`), none
  in the seven days since. Closing on that basis, with the caveat stated: seven clean days is
  evidence, not proof, and 2026-07-29 sits at the edge of the retained window.

  **Do not confuse this with what is in the log now.** Eleven `[vertex_cache]` warnings on
  2026-08-04 are `NameResolutionError` on `oauth2.googleapis.com` — DNS failure during the
  four-hour outage, a different cause with a similar-looking line. Anyone re-filing this on the
  strength of a `grep vertex_cache` will re-file the outage.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:385 · verified 2026-08-05 against
  the VM journal + core/orchestrator.py:1417*

- ~~**[DB-0803-02] ⚠ `Object of type AgentRecord is not JSON serializable` — proactive sessions
  failing outright.**~~ — **root-caused and fixed 2026-08-04, deployed `10bf194`.**

  **Root cause:** `core/router.py:166`, inside `log_model_error()`. Three call sites in
  `core/orchestrator.py` (:1575, :1676, :1881 — the last is the Coordinator/Synthesizer
  OpenAI-compat loop every failing scheduled job passes through) did
  `_agent = _tr.get_current_agent() or "unknown"`. `get_current_agent()` returns the live
  `AgentRecord`, not a string, and a truthy record short-circuits the `or` — so `_agent` was the
  record object itself whenever one was active (always, mid-pipeline). `log_model_error` then
  crashed on `json.dump` trying to serialize it, **masking whatever the real underlying model
  failure was**. Confirms and completes the localisation two sessions had already narrowed down
  (`core/trace.py` was correctly ruled out both times).

  **Fix:** one line — `"agent": agent.agent if hasattr(agent, "agent") else agent,` — fixes all
  three call sites at one JSON boundary rather than patching each.

  **Verified two ways before calling this closed:**
  1. Local: called `log_model_error()` directly with both an `AgentRecord`-like mock and a plain
     string — no `TypeError` either way.
  2. **On the deployed VM, with the real object**, not a mock: started an actual
     `RequestTrace`/`AgentRecord` via `core.trace.start_request_trace` +
     `push_agent('coordinator', ...)`, then called `log_model_error()` with the real
     `get_current_agent()` return value — the exact call that was crashing in production. It
     did not raise, and the resulting log entry correctly read `"agent": "coordinator"` (a
     string, not the object dump a pre-fix run would have produced). The synthetic test entry
     was deleted from `data/diagnostics/model_errors.json` afterward so it doesn't read as a
     real production error.

  **What is *not* yet confirmed — a genuine scheduled fire completing end-to-end under real
  conditions** (not a manual reproduction). See **[DB-0804-01]** below for the time-gated checks
  that confirm this, and why they should not be run early.
  *filed 2026-08-03 by dev session · elevated 2026-08-05 · root-caused, fixed and deployed
  2026-08-04 by dev session · verified against core/router.py and live VM reproduction*

- **[DB-0804-01] Time-gated follow-up: confirm a real scheduled fire completes clean under
  [DB-0803-02]'s fix.** The fix above is verified against the exact crashing code path, but not
  yet against a live scheduler fire hitting real model-call variance. **Do not check any of
  these before the stated time — an early check just shows "hasn't fired yet," which reads as a
  regression and isn't one.**

  1. **`companion_checkin`, not before 2026-08-04 23:05 BST.** `min_gap_minutes: 180` from its
     last real fire (20:03 BST) puts the earliest next attempt at ~23:03. Check:
     `gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command="sudo journalctl -u metatron-scheduler --since '2026-08-04 22:55' | grep -E 'companion_checkin|AgentRecord'"`.
     Pass: a `firing companion_checkin` line with no following `AgentRecord is not JSON
     serializable` error. (A `skipping` line is a gate decision, not a failure — re-check at the
     next 30-minute poll rather than treating it as a fail.)
  2. **`morning_brief`, not before 2026-08-05 07:35 BST.** Fires daily at 07:30. Same journalctl
     pattern, grep `morning_brief`.
  3. **One-week count, not before 2026-08-11.** Re-run the exact baseline query:
     `sudo journalctl -u metatron-scheduler --since '7 days ago' | grep -c 'AgentRecord is not JSON serializable'`.
     Baseline was 18 in the 7 days to 2026-08-05. Pass: at or near 0 for the 7 days following
     deploy (2026-08-04 21:00 onward) — some non-zero count is possible if the *same* call sites
     hit a genuinely different, unrelated serialization issue, so read the actual log lines
     before treating a nonzero count as this bug recurring.

  *filed 2026-08-04 by dev session · depends on [DB-0803-02] · not to be actioned before the
  per-check times above*

- **[DB-0803-05] `sw.js` has no `fetch` handler and caches nothing**, and `/` is served
  `no-store` — no offline shell, so an unreachable server shows a browser error page rather than
  the app. **Confirmed still real 2026-08-05:** [static/sw.js](static/sw.js) registers exactly
  four listeners — `install`, `activate`, `push`, `notificationclick`. No `fetch`.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:320 · verified 2026-08-05 against
  static/sw.js*

- **[DB-0803-06] `shownIds` eviction wipes the whole set instead of evicting incrementally —
  re-derived and confirmed real 2026-08-05 (line numbers updated).** `shownIds` is declared at
  [static/index.html:706](static/index.html#L706). Two call sites do a full
  `if (shownIds.size > 100) shownIds.clear()` rather than dropping only the oldest entries —
  [:944](static/index.html#L944) in `renderHistory()` and [:971](static/index.html#L971) in
  `sendViaWebSocket()`.

  **Why it's a real bug, traced through the dedup logic:** every WS message type
  (`chunk`/`done`/`message`/`error`/`retract`, [:836-927](static/index.html#L836)) branches on
  `shownIds.has(msg.exchange_id)` to tell "my own exchange, already rendering" from "foreign or
  catch-up exchange, needs a fresh render." A full clear means that once a conversation crosses
  100 exchanges, the next reconnect's `renderHistory()` re-populates and immediately re-empties
  the set — so any subsequent `'message'` catch-up for an exchange the device already rendered
  looks unseen and gets rendered a second time. **Fix:** evict oldest-first (e.g. convert to an
  array-backed ring, or drop the first N insertion-ordered keys) instead of `clear()`, at both
  call sites.

  **`eea3faf` (2026-07-27) is real but fixes a narrower bug than this entry.** It swapped
  `sendViaWebSocket`'s clear/add order so the just-sent exchange's own ID survives the clear
  (previously `.add()` then `.clear()` wiped the ID that was just added, breaking the client's
  own chunk/done recognition — a stuck bubble, not a duplicate). It did not touch the
  clear-vs-evict question: both call sites still do a full `.clear()` today, just in the
  now-correct order relative to the current send. The duplicate-render risk traced above is a
  separate, still-open defect at the same two line numbers.
  *filed 2026-08-03 by dev session · recovered from SESSION.md:319 · re-derived and confirmed
  2026-08-05 against static/index.html:706,836-927,944,971 and commit eea3faf*

- ~~**`/session` (non-streaming) leaks the `[CONTEXT]{…}[/CONTEXT]` block**~~ — **fixed;
  closed 2026-08-05.** `run_session` now calls `split_context_block()` then `filter_output()`
  before returning ([core/orchestrator.py:2690](core/orchestrator.py#L2690)), and
  `persist_context_block()` writes the tracker on the same path — so both halves of the
  complaint (leaked control text, tracker never written) are covered. The comment there records
  the intent explicitly: *"one implementation so the two paths cannot drift apart again."*
  *filed 2026-08-03 by dev session · recovered from SESSION.md:386 · verified 2026-08-05 against
  core/orchestrator.py:2690*

- ~~**[DB-0803-04] `write_config()` heading duplication.**~~ — **not a bug; the described fix
  already exists and works. Closed 2026-08-05, correcting a wrong verification from earlier the
  same day.** The 2026-08-05 pass checked only [tools/config_writer.py](tools/config_writer.py)
  (confirmed: no heading logic there, writes verbatim) and stopped, concluding the symptom was
  unconfirmed. `_titled()` is not in that file — it's in
  [core/orchestrator.py:187-199](core/orchestrator.py#L187), and its docstring states the exact
  mechanism the entry described: *"The Goals Interviewer writes prime_directive.md and
  mission.md through write_config(), which stores the model's text verbatim — and the model
  includes its own heading. Without this check the system prompt carries the heading twice with
  an empty section between."* `load_config()` calls it at [:234](core/orchestrator.py#L234) for
  both files. Added in `6601479`, predating this entry. **The lesson: "cited code does not
  exist" is only true of the one file checked — the fix can live one layer up from where the
  write happens.**
  *filed 2026-08-03 by dev session · recovered from SESSION.md:387 · first verification
  2026-08-05 incomplete · corrected 2026-08-05 same session against core/orchestrator.py:187-234*

- **Pre-2026 logs in mike's tree** (`2025-01-24`, `2025-05-13`–`16`) — believed genuine early-dev
  data, but the SEQ 021 session found one hallucinated log dated 14 months in the past. Worth
  confirming none of these are the same.

  **Attempted 2026-08-05, blocked — real data lives on the VM, not the Mac.** Per `CLAUDE.md`
  → Personas, live persona data is VM-owned; the Mac copy is a stale mirror. Checked it anyway:
  `data/personas/mike/logs/` on the Mac has neither of the originally-cited filenames — either
  already cleaned up, or this mirror predates them — so this pass **cannot confirm or refute
  the original claim**. **New finding, same class of bug:** the same local directory has
  `2024-08-04.json` (`{"notes": "User re-engaged with the session.", "date": "2024-08-04"}`,
  74 bytes) sitting alongside a correctly-dated `2026-08-04.json` — a two-years-stale hallucinated
  date, not the 14-months-stale one previously found, but the identical failure mode. **Needs
  the VM to resolve properly**: `data/personas/mike/logs/` there is authoritative; this session's
  VM access was down (see the sync report). Check both the original two dates and whether
  `2024-08-04.json` has a live-VM counterpart when it's reachable.
  *`SESSION.md:227` · re-attempted 2026-08-05, blocked on VM reachability · new data point added,
  not closed*

- **Coordinator restructure (token-reduction Step 6)** — single-pass directive assembly replacing the multi-turn session, ~15,000t. Deferred 2026-06-24 pending Steps 1–5 stabilising; they have. **Re-scope against measured data first:** the coordinator runs 1 turn, not the 7 the roadmap assumes — the real cost driver is per-specialist internal turns (logistics measured at 8). Relates to the D2 item-5 mis-scoping already on this list. *`SESSION.md:602`.*

### Recovered from conversation, 2026-08-01/02

- **Data breadth — sleep is nearly the only thing consistently logged.** This is the *root cause* behind "too much focus on sleep": with one reliable signal and little else, any reasoning leans on it by default. The 2026-08-03 `synthesizer.md` rules mitigate the symptom (don't over-read a thin record; ask for what's missing) but cannot fix it. Needs a real answer on capturing training, food, work and mood with low enough friction that they actually get logged. Mike has also asked that sleep tracking itself shift to **total hours plus interruptions** rather than a disruption narrative (2026-08-03).

- ~~**Nothing in the system can actually set a reminder or calendar entry.**~~ — **the whole
  build order it prescribes is complete; closed 2026-08-05.** *"The calendar integration will do
  later. I don't understand why it didn't, why it triggered at all"* — SEQ 011, 2026-08-01.

  Its four steps, each verified: **enable CalDAV** — live 2026-08-03 (`cfcd212`), with
  recurrence, alarms and all-day support. **Grant Logistics its config tools** — 2026-08-05
  (`9361537`). **`write_schedule`/`list_schedules`/`delete_schedule`** — built and granted
  2026-08-03 (`078e618`, `2f74cd2`); present in [tools/schedule.py](tools/schedule.py) and
  registered in `core/orchestrator.py`. **Delivery preference** — push is live.

  **Worth recording, because it misled this session's own analysis:** the entry's claim that
  *"`scheduler.yaml` jobs are static with no tool to add one"* went stale on 2026-08-03 and was
  still being read as current on 2026-08-05, where it produced a recommendation to hold the
  `logistics` `write_agent_config` grant pending work that had already shipped two days earlier.
  A stale premise does not just waste the effort spent on it — it argues for the wrong decision,
  persuasively.
  *filed 2026-08-01 by Mike via Synthesizer · origin SEQ 011 · verified 2026-08-05 against
  tools/schedule.py, both routing files, and the CalDAV commit*

- **[DB-0802-01] Voice transcription — the recorded cause is fixed; the accuracy half is not.**
  *"There are transcription issues to address. Multiple timeouts"* — SEQ 014, 2026-08-02.

  ~~Blocking the event loop~~ — **done 2026-08-01** (`d42eefc`, `81fc6e2`), before this entry
  was ever re-read. `/transcribe` and `/tts` now run on dedicated single-worker pools
  (`_STT_EXECUTOR` / `_TTS_EXECUTOR`, [core/server.py:178](core/server.py#L178)), Whisper and
  the memory model warm-load at startup, and `_transcribe_blocking` carries a comment explaining
  the freeze it replaced. **Anyone working "transcription times out" from the old description
  would have re-fixed a solved problem** — this is the clearest case in the sweep for why an
  item is re-verified before it is worked.

  **What is left is accuracy, which is a different fix in a different file.** Whisper runs
  `base.en` with `beam_size=5` and no VAD
  ([core/voice_pipeline.py:26,119](core/voice_pipeline.py#L26)). Evaluate `small.en` and a VAD
  filter — but **measure on the VM's 2 vCPUs before adopting**, because STT is now on a
  single-worker pool and a slower model serialises rather than merely being slower. Pairs with
  the dictated-email item below; same root, different lever.
  *filed 2026-08-02 by Mike via Synthesizer · origin SEQ 014 · verified 2026-08-05 against
  core/server.py:178 and core/voice_pipeline.py:26 — cause closed, accuracy open*

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

- **No agent can act on a web page on the user's behalf (level 3).** Raised 2026-08-03 as three
  distinct capabilities. **Levels 1 and 2 are now both built — verified 2026-08-05, closing that
  part.** Grounded search (`run_session_gemini_grounded`) was already live. `fetch_url` shipped
  2026-08-04 ([tools/web.py:146](tools/web.py#L146)) with the injection defense that was named as
  its prerequisite, not a follow-up: returned content is wrapped in `<untrusted_content>` tags
  ([tools/untrusted.py](tools/untrusted.py)), confirmed at the `fetch_url` docstring itself.

  **What's left is level 3 only: navigate, log in, fill forms, transact — a different animal.**
  A hostile page reached via `fetch_url` can only *say* things to the model; level 3 lets a page
  make the model *do* things using the user's credentials. Explicitly deferred, not started:
  behind an authentication story that doesn't exist yet, and requires per-action confirmation
  (the mechanism for that now exists — see `tools/confirm.py` above — but nothing calls it here).
  Do not ship this on the assumption that `fetch_url`'s injection wrapping covers it; it doesn't,
  it addresses a different failure.
  *filed 2026-08-03 · levels 1-2 built 2026-08-04, closed as such 2026-08-05 against
  tools/web.py:146, tools/untrusted.py · level 3 remains open, not started*

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

- ~~**Transcript lines run too long on screen.**~~ — **the bubble-width half fixed, closed
  2026-08-05.** *"The transcript liners too long on the screen"* — SEQ 014, 2026-08-02. Two
  readings existed: the footer `#transcript` readout (capped to 3 lines with internal scroll,
  2026-08-04) and the conversation *bubble* width. Checked the second today: `.message` had
  `max-width: 88%` but no `overflow-wrap`, while `#transcript` and `#confirm-text` both already
  carry `overflow-wrap: anywhere` — an unbroken long token (URL, run-on dictated text) could
  overflow the bubble and run off-screen horizontally, matching the complaint exactly. Added
  `overflow-wrap: anywhere` to `.message` ([static/index.html:62](static/index.html#L62)).
  Client-only change — testable in a desktop browser, no APK/deploy needed to verify, but
  **does need `./deploy.sh`** to reach the live PWA and phone.
  *filed 2026-08-02 by Mike via Synthesizer · origin SEQ 014 · fixed 2026-08-05 against
  static/index.html:56-62*

- ~~**`/metatron-troubleshoot` command template points at pre-persona-scoping paths.**~~ —
  **stale, closed 2026-08-05. Already fixed, most recently by `a763628`.** All three claims
  re-checked against `.claude/commands/metatron-troubleshoot.md`: persona-scoped paths are in
  place with `data/conversations/` explicitly flagged as a legacy trap (line 39), `BASE =
  f'data/personas/{PERSONA}'` is fully parameterized (line 56), and `--tunnel-through-iap` is
  present on the SSH command (line 48).
  *Original entry recorded in SESSION.md 2026-08-02 · verified stale 2026-08-05 against
  .claude/commands/metatron-troubleshoot.md*
- **Roadmap D2 item 5 (turn reduction) is mis-scoped and needs rewriting before anyone works it.** It targets the Coordinator on the assumption that the Coordinator runs ~7 turns per exchange. Measured 2026-08-02: **the Coordinator runs 1 turn.** The turns are in the specialists — `logistics` alone ran 8. Working the item as written would optimise a component that is already minimal and leave the actual cost untouched. Re-measure across several specialists before rewriting the item, rather than swapping one assumed culprit for another.

  **The roadmap has not been corrected — only this entry has.** [`archive/plans/phase5_to_future_roadmap_2026-06-10.md:519`](archive/plans/phase5_to_future_roadmap_2026-06-10.md#L519) still reads *"The Coordinator exhibits a 6-turn / 88K cumulative token loop on complex sessions"* and still prescribes a `coordinator.md` instruction change plus a ≤3-turn target. Anyone who reads the roadmap without reading this backlog gets the original wrong picture and a fix aimed at the wrong component. Deliberately not edited in place: the roadmap is a dated plan snapshot, and rewriting its body would erase what was believed at the time. Whoever picks the item up should rewrite it from measurement and note the supersession there — the correction is verified twice (2026-07-29 traces, re-measured 2026-08-02), so it is not waiting on evidence.

- ~~**No check that the VM is actually running what the Mac has committed.**~~ **Done 2026-08-03** — see the Done section.

- ~~**Spend guard pricing rates are unverified estimates.**~~ — **verified and corrected,
  closed 2026-08-05.** Checked against `cloud.google.com/vertex-ai/generative-ai/pricing`
  (standard tier, ≤200K token context, text): the file's rates were low across the board —
  `gemini-3.1-pro-preview` input $1.25→**$2.00**, output $10.00→**$12.00**;
  `gemini-3.1-flash-lite` input $0.10→**$0.25**, output $0.40→**$1.50** (flash-lite output was
  ~3.75x under). Updated in [config/modules/spend_guard.yaml](config/modules/spend_guard.yaml)
  with a dated comment. Still order-of-magnitude, not billing-accurate — cached-input discounts,
  priority/flex tiers, and the >200K-token rate step are all ignored by design.
  *filed 2026-08-03 · verified and fixed 2026-08-05 against live Vertex AI pricing page*
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

- ~~**[DB-0805-03] `run_a4_safety.py`'s `clinical`/`finance` report filenames collide on a
  same-day, same-provider re-run.**~~ — **fixed, closed 2026-08-05.**
  [tests/run_a4_safety.py](tests/run_a4_safety.py) — `suite_suffix` now derives from `args.suite`
  for every suite (`"" if args.suite == "all" else f"_{args.suite}"`), so `clinical`, `finance`,
  and `pipeline` each get their own filename; `all` keeps the unsuffixed name as before. Docstring
  updated to match.
  *filed 2026-08-05 by dev session (Claude Code) · found while building the A7 pipeline probe ·
  fixed 2026-08-05 same session*

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

---

## Done

**Everything below is closed.** `scripts/sync_dev_backlog.py` stops counting at this heading,
so items parked here do not inflate the open count — which is the whole reason the heading
exists. It was referenced by an entry above ("see the Done section") and by the sync script
for weeks before anyone noticed it had never been written; without it the script's "live
region" ran to end of file and **closing an item made the reported number go up.**

Every entry keeps its ID and carries the commit or `file:line` that closed it. Closed without
one is not closed.
