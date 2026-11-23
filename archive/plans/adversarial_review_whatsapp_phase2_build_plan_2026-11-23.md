Adversarial review of `archive/plans/whatsapp_phase2_build_plan_2026-11-23.md` — reviewer: Fable (adversarial-reviewer), effort medium, 2026-11-23.
Clean-room access rules were passed to the reviewer as constraints; the report below is verbatim.

## STRUCTURAL

1. [§ 3.9, § 3.4, § 7 "Then (M5…)"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:set_share_list → _require_open; handle_events `dropped_not_shared`]
Wrong: The share list is posted only "on each change and after any night that reports newLinks", yet the walkthrough has Mike tick chats before M4, when the VM refuses that post with 403 `channel_off`, and the plan names no re-post for a share-list post that was refused or failed.
Fails: After M4 the VM's share list is still empty, so every event returns HTTP 200 counted as `dropped_not_shared`, which § 3.4 does not treat as a failed post and so records in the sent-hash list and skips from then on; the same gap leaves an un-tick whose post failed un-purged on the VM while the screen has said it is deleted.
Costs: Messages from chosen chats are silently and permanently lost from the first night, and an un-shared chat's facts can stay on the VM against W3 — high.

4. [§ 7 Session A and "Why this seam", § 4.4, § 3.2] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:get_cursor → _require_open; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_whatsapp_call]
Wrong: Session A is justified as the seam that "can be checked end to end", but every `/device/whatsapp/*` call is 403 until M4 and the run-report and missed endpoints deploy only with M4, so nothing the phone posts can be observed before the channel is live on real data.
Fails: A run starts with the cursor call, which returns `channel_off`, and the plan does not say whether the read, event build and report then happen at all, so "watch the first nightly run's report next morning" has no defined content and the first real exercise of skip / update / reply-marker posting is the production switch-on.
Costs: Posting defects (findings 1–3) surface only after M4, against Mike's real chats, with a sent-hash list already written — medium.

## LOCAL

2. [§ 0 item 2, § 3.4, § 3.10] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events (same-key `message` with equal `fp` → `duplicates`), _who]
Wrong: § 0 promises the nightly backup "fills in… the group sender", but the live path sends `sender ""` and the sent-hash list is a hash of the text alone, so the backup copy of an unchanged group message is skipped.
Fails: Same key, same hash means no event is sent, and even a re-sent `message` would be dropped by the VM as a duplicate without touching the sender; only `update` reaches `revise`, which is the only place the sender is rewritten.
Costs: Every group message that arrived live stays "a member of <group>" with `sender_known` false for good, so group facts never carry a name — high.

3. [§ 3.2 "post in batches of ≤ 500", § 1 row "The VM re-checks cheaply", § 3.8 DeviceClient] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events:646-650, MAX_TEXT_CHARS; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_read_capped; /Users/md-homefolder/Desktop/multi-model-mcp/android/app/src/main/java/com/mike/metatron/PushStore.java:TIMEOUT_MS]
Wrong: Batches are sized by count only, and the plan sets no client timeout and no handling for a per-event `rejected` or a 413, while the VM translates every event before its duplicate check (~0.1 s per Bulgarian message), caps a body at 512 KiB and rejects text over 4,000 characters.
Fails: On the 90-day first run (~5,400 messages) a 500-event batch takes on the order of 50 s on the VM; a client on the 8 s timeout of the HTTP code the plan reuses gives up, records nothing as sent, and re-sends the same batch, which is translated in full again before being dropped as duplicates.
Costs: The first run can loop without finishing while the VM pays repeated translation, and an over-long message or over-cap batch is re-sent nightly for the whole overlap — medium.

5. [§ 4.2, § 3.8 "Turn off WhatsApp link"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:context_lines; /Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:1028-1030]
Wrong: The stale line is added to `context_lines` with a raise condition (report older than 52 h, text gone, a refusal) but no once-per-onset state and no clearing condition, and "Turn off" deletes phone state only, leaving the VM's last report to age.
Fails: `context_lines` runs on every context load, and its existing line is limited by `delivered_at` within a 30-minute window; the new line has no such state, so it is given to Coordinator and Synth on every turn while stale, and permanently after a deliberate turn-off or with the phone off for two days.
Costs: The same "WhatsApp messages have not reached Metatron" line enters every conversation indefinitely and is raised again and again — medium.

6. [§ 2 item 7, § 3.9] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:set_share_list, _who]
Wrong: A group's `senders` map is built from the senders seen in the window, but the share list is re-posted only on a tick change or a `newLinks` night.
Fails: A member who first writes after the last post, or whose contact name is added later, is never in the VM's `senders`, so `_who` returns "a member of <group>" even though the backup supplied the sender id.
Costs: Group sender names decay to whatever was known on the day the chat was ticked — medium.

7. [§ 3.11] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:native_key]
Wrong: "Hashes the shared text and looks it up in the sent-hash list" treats the hash as identifying one message, but the list is keyed by `chat|second|ordinal` and the share intent carries no chat or time.
Fails: Any text sent more than once in nine days across shared chats ("ok", "yes", a repeated question) matches several keys and the plan has no rule for which one is posted, so the VM diagnoses some other message.
Costs: The missed report — the only measure of misses — records the wrong outcome for exactly the short messages most likely to repeat — medium.

## VERIFY — 2026-11-23 (round 1, same reviewer)

Verify pass on /Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_phase2_build_plan_2026-11-23.md (re-read from disk). Five of the seven findings are closed, two are partial, and the revision introduced four new defects.

### VERDICTS

1. PARTIAL — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events `dropped_not_shared`; set_share_list] The nightly path is closed: the list is re-posted at the start of every run and a batch with drops records nothing. The live path (§ 3.10) still treats only a failed post as unrecorded, so a live one-to-one message that returns 200 with a drop, while a tick is "not yet sent to Metatron", is hashed as sent and then skipped by the backup, because its text and sender hashes match.

2. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events `update` branch → revise] A live group copy sent with `sender ""` now differs in sender hash from the backup copy, goes as `update`, and `revise` rewrites `sender` and `sender_display`. One-to-one rows carry no sender on either path (`FullBackupMessages.read`, `IncrementReader.message`), so they are not re-sent needlessly.

3. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events:646-650, MAX_TEXT_CHARS, MAX_EVENTS; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_read_capped] 100 events at ~0.1 s each sits well inside a 120 s read timeout, 256 KiB is under the 512 KiB cap, and a 4,000-character prefix passes `_validate` and is the thing hashed. See NEW 4 for what the smaller batches do to the first run.

4. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:_require_open, channel_open; /Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_whatsapp_call] The dry run gives session A a defined, observable result on real data before M4, and § 7 now deploys the VM change first. The fix depends on § 4.0, which is where NEW 1 comes from.

5. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:context_lines `delivered_at`, delete_all] Per-onset state in the existing delivery-window pattern bounds the line to once per onset. `delete_all` already unlinks `whatsapp_state.json`, and a revoke that fails now costs one raise, not a standing line.

6. PARTIAL — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:_analyse → _who; set_share_list] § 3.2 posts the share list before `NightlyRead`, so a map "rebuilt from that night's senders" can only hold the previous night's. A new member's first-night messages are analysed as "a member of <group>", and the next night their text and sender hashes match what was sent, so they are skipped and never named.

7. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:native_key] Several matches are now posted as up to five keys marked ambiguous and counted apart, so the report no longer attributes a flag to an arbitrary message.

### NEW

1. [§ 3.12, § 4.0, § 4.4 "the order is free" against § 7 walkthrough step 1] [/Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_whatsapp_call (hardcoded `detail="channel_off"`); /Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:_require_open]
Wrong: The single APK's consent gate is the phone reading `no_consent` against `channel_off` in the 403 detail, but the VM as deployed answers `channel_off` for every closed gate, and § 4.4 still says the VM change may deploy in any order.
Fails: Against any VM without § 4.0, a paired user with no consent record gets `channel_off`, which § 3.12 defines as "consent recorded", so the app offers key entry, All-files access and contacts and runs the nightly dry-run decrypt.
Costs: The every-user APK fails open on consent on the phone, for the user who has not consented, whenever the APK reaches a phone before the VM deploy — high.

2. [§ 3.9 "at the start of every run… nothing is removed", § 8 Unseen 2] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:set_share_list (`removed` → purge_chat)]
Wrong: The whole-replace share list is now posted unattended every night from `share.json`, a file the plan itself says a reinstall loses, with no rule for a list that is empty or was never accepted by the VM.
Fails: A run with a lost, reset or unreadable local list posts `chats: []`; `set_share_list` treats every chat on the VM as un-shared and purges its facts, flags and reply markers before replying.
Costs: Phone-side state loss becomes an irreversible deletion of everything WhatsApp left on the VM, with no user action — medium.

3. [§ 3.2 dry run "from now − 90 days", § 3.12 `channel_off` state]
Wrong: The dry run is defined for every `channel_off` answer, not only the pre-M4 walkthrough, so a consented user whose channel is switched off keeps a job that decrypts and reads 90 days of the backup every night with no end condition.
Fails: Phase 1 says turning the stanza off "stops collection" (`tools/intake_whatsapp.py` module docstring), yet the phone goes on holding the key and producing would-send lists nightly for as long as the VM answers `channel_off`.
Costs: Switching the channel off no longer stops the phone reading the user's messages, an unattended privacy cost no meter reports — medium.

4. [§ 3.2 "The 90-day first run is ~54 posts", § 3.3 cursor, § 3.4 prune]
Wrong: The first run is ~54 sequential posts and about nine minutes of VM translation by Phase 1's own figures, inside one JobScheduler execution, and the plan does not say whether the cursor advances per batch.
Fails: If the system stops the job mid-run and the cursor has not moved, the next run starts again from 90 days back while the sent-hash list has been pruned to nine days, so the older batches are re-sent and re-translated each night.
Costs: The first backfill may never complete as a scheduled job and repeats its VM cost nightly — speculative.

QA sweep hook: this review has no write tools and changed no file. The five failing checks (agent-tools, personas, project-log, build-registration, scheduler-functions-resolve) are in the worktree /Users/md-homefolder/Desktop/multi-model-mcp/.claude/worktrees/agent-a669b7661748e9a65, which I never touched. Two fail on missing modules (`anthropic`, `yaml`) and one on existing `archive/PROJECT_LOG.md` drift; the output for the other two was truncated. None of them comes from this review.

## VERIFY — 2026-11-23 (round 2, same reviewer)

Verify round 2 on /Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_phase2_build_plan_2026-11-23.md (re-read from disk): all six claimed closures hold against the code, and I found no new defect that clears the significance bar.

### VERDICTS

- verify 1 (live path): CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events `dropped_not_shared` / `rejected`] The listener posts only while the VM holds the current share-list version, and a 200 reply that drops or rejects the event records nothing. The one-to-one case that used to be hashed and then skipped by the backup is now sent by the backup as a fresh `message`.

- verify 6: CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:_analyse → _who; set_share_list] The per-run order is now read, then share-list post, then events, so the `senders` map and any `merges` the VM reads when it analyses tonight's events are tonight's. § 3.9 still says "named from the next night"; that sentence is stale wording, not behaviour.

- new 1: CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/core/server.py:_whatsapp_call (`detail="channel_off"`); /Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:_require_open, channel_open] The phone unlocks only on the exact string `consented_off`, which the deployed VM never emits, so against today's VM a paired user is treated as not consented and is offered nothing. § 3.8 still says "403 → link is off"; § 3.6 and § 4.0 govern.

- new 2: CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:set_share_list (`removed` → purge_chat)] An unattended post now needs a list the user saved on this install that reads cleanly, and an empty list goes only at the user's own tap. A lost or reset `share.json` therefore posts nothing and cannot trigger the purge branch.

- new 3: CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py module docstring "Turning either off stops collection"; get_cursor → _require_open] Dry runs are limited to before the first open, on the user's tap, for at most seven nights. Once the channel has been open, any 403 cancels the job and the listener, so there is no nightly decrypt while the channel is off.

- new 4: CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake_whatsapp.py:handle_events `state["cursor"] = cursor`] The VM stores whatever cursor each accepted batch carries. With batches sent oldest first and the cursor withheld after any unaccepted batch, a stopped job resumes at the delivered point, and its read window (cursor − 8 days) lies inside what the sent-hash list keeps.

### NEW

none

QA sweep hook: this review has no write tools and changed no file. The five failing checks (agent-tools, personas, project-log, build-registration, scheduler-functions-resolve) are in the worktree /Users/md-homefolder/Desktop/multi-model-mcp/.claude/worktrees/agent-a669b7661748e9a65, which I never touched. Two fail on missing modules (`anthropic`, `yaml`) and one on existing `archive/PROJECT_LOG.md` drift; the output for the other two was truncated. None of them comes from this review.
