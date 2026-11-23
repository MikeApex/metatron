*Adversarial review of `archive/plans/whatsapp_phase1_build_plan_2026-11-23.md`.*
*Model: Fable (adversarial-reviewer) · effort: medium · 2026-11-23 · clean-room reading limits applied.*

## STRUCTURAL

1. [§ 2.5 "sender basis only", § 4 T13, § 0 "cards (Phase 3) come later"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:_sender_matches, :open_task (`expect_from`), :match_envelope; /Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md § 3 "Track this"]
Wrong: The plan asserts "`expect_from` contains `@`, so it is an exact match", but the only thing that would write a canonical WhatsApp id into `expect_from` is the parent plan's "Track this" card button, which is Phase 3; today the field is model-supplied free text ("email address, domain or name").
Fails: In Phase 1 a real `expect_from` such as "Anna" takes `_sender_matches`' substring branch against `sender_display` (any contact label containing it), an email address never equals a WhatsApp id, and a one-to-one event whose `sender` is "" (§ 2.2 marks the field "groups") gives an empty address and display, so nothing matches at all.
Costs: V5 ships either dead for one-to-one chats or parking the single ever-allowed WhatsApp close card on the wrong person's message, while T13 passes only because the test plants an id no production path writes — high.

## LOCAL

2. [§ 2.3 `info` → `correspondence`/`silent`/`relationships`, § 5 decision B, § 2.7, § 7 Run] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:build_digest, :read_intake_queue, :context_block; /Users/md-homefolder/Desktop/multi-model-mcp/config/templates/intake.yaml `digest.include_silent: true`, `limits.max_queue_age_days: 7`]
Wrong: Decision B's recommendation ("left out of the morning digest") has no step, file change or test behind it, and § 3 lists no `build_digest` change.
Fails: `build_digest` lists silent rows individually while `include_silent` is true and escalates every non-surface queue row unread for more than 7 days with no cap, `read_intake_queue("relationships")` returns the whole unread queue, and the rendered digest text parked in `digest_state.json` is outside everything `purge_chat` deletes.
Costs: About 60 chat facts a day pile into the brief and the Relationships specialist's context against a stated run cost of 5–15 facts, and an un-shared chat's facts stay in a parked digest after the "at once" purge — high.

3. [§ 2.4 `ingest()` called from the events endpoint, § 7 Ancillary] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/turn_context.py:_newer_intake_row, :new_trigger_since; /Users/md-homefolder/Desktop/multi-model-mcp/tools/confirm.py:216]
Wrong: The plan does not list the declined-action guard as a dependent of `records.jsonl`, which treats any intake row newer than a decline as a genuinely new trigger.
Fails: WhatsApp pushes rows into `records.jsonl` all day (silent `info` facts included), so `new_trigger_since()` returns true almost always once the channel is on.
Costs: An action the user refused can be re-proposed from carried context alone, re-opening the loop that guard was built to end, with no test in § 4 that would show it — high.

4. [§ 2.4 "moved out unchanged", "inside a file lock", "`_append_record` takes the same lock", § 7 risk 2, T22] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:sweep lines 1159–1161, 1191, 1266–1271, :teach_intake lines 1036–1042; /Users/md-homefolder/Desktop/multi-model-mcp/core/consent.py:_locked]
Wrong: The range moved into `ingest()` (1203–1260) leaves out `sweep()`'s own load of `seen` before the fetch and its sibling-marking and saves after the loop, and the cited `_locked` pattern is not re-entrant.
Fails: `sweep()` still holds a `seen` copy read before a multi-second mail fetch and writes it back at 1270, overwriting entries the server added meanwhile; `ingest()` holding the lock while calling a locking `_append_record` blocks on itself; and `teach_intake` already writes `ledger.json` unlocked from the server process.
Costs: The race the lock exists to close survives in production while T22, with no fetch delay, passes; a lost `seen` entry turns a later `update` into a second row — medium.

5. [§ 2.2 message key and `ordinal`, § 7 risk 1 "a duplicate fact, never a lost one"] [/Users/md-homefolder/Desktop/multi-model-mcp/SESSION.md "increments leave some messages out entirely"; /Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:envelope_id, :sweep `seen` check]
Wrong: The claim that a same-second ordinal disagreement can only duplicate a fact is false.
Fails: If one path numbers message A as ordinal 0 and a later path numbers a different message B as 0 (A missed live, or left out of an increment and delivered by the next full backup), B's key equals a key already in `seen` and B is discarded as a duplicate.
Costs: A real message is dropped silently, the failure the intake module is built around, on a risk the plan accepts as "visible and harmless" — medium.

6. [§ 1 V6 "holds, subject to step 0", § 2.6 "Step 0 sets the tolerance", § 5 decision A, § 6 item 7] [/Users/md-homefolder/Desktop/multi-model-mcp/SESSION.md "Owed before Phase 1's V6"; /Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md § 4 "P3 BUILT"]
Wrong: The todo list has no step 0 and nothing gating item 7 on it, decision A has no options, and § 2.6 defines no tolerance parameter for it to set.
Fails: Mike's go-ahead on § 6 authorises building the backstop on reply markers before the count of omitted own messages is in, with T14/T15 written against the unadjusted 24-hour rule.
Costs: If the omitted messages are reply kinds, V6 re-raises questions the user already answered for up to about 6 days and is reworked after it is built and tested — medium.

## VERIFY — 2026-11-23 (round 1, same reviewer)

1. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/obligations.py:open_task (line 1822), :_sender_matches, :match_envelope] `expect_from` is written only for `waiting` tasks as free text, and § 2.5's whole-word match against the user's own label, with the chat id as the one-to-one `sender_address` (T28), gives the sender basis a real producer in Phase 1; one leftover is that § 2.4's envelope bullet still says `sender_address` is "the canonical id, or `""`", which contradicts § 2.5 and T28.

2. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:_unconsumed_by_domain, :build_digest, :read_intake_queue] a row with `domain` None is skipped by `_unconsumed_by_domain`, so it reaches no queue, no queue count and no escalation, and the `channel == "whatsapp"` skip in `build_digest` keeps WhatsApp text out of the parked digest in `digest_state.json`; see NEW 3 for a side effect.

3. PARTIAL — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/turn_context.py:_newer_intake_row; /Users/md-homefolder/Desktop/multi-model-mcp/tools/confirm.py:216] silent `info` rows no longer lift a decline, but § 2.3 still classifies any message containing a `?` from any member of any shared chat, groups included, as `action_required`, so third parties lift the guard at chat frequency rather than at the hourly mail cadence it was built around.

4. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:sweep (lines 1159, 1266–1271), :teach_intake (lines 1036–1042); /Users/md-homefolder/Desktop/multi-model-mcp/core/consent.py:_locked] `ingest()` re-reading `seen` and `ledger` under a thread-re-entrant lock, with the sibling marking inside it and `teach_intake` locked, removes the stale write-back and the self-block, and T22's 2-second fetch delay can now fail; see NEW 2 for what the move left unassigned.

5. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:envelope_id, :sweep `seen` check] a backup `message` on a seen key with a different fingerprint is re-keyed deterministically, so the dropped-as-duplicate path is gone and a re-send of the same clash lands on the same re-key; the cost moved to duplicates, which the plan names, and to NEW 1.

6. CLOSED — [/Users/md-homefolder/Desktop/multi-model-mcp/archive/plans/whatsapp_input_plan_2026-10-26.md § 4 "P3 BUILT" (26 omitted own messages); /Users/md-homefolder/Desktop/multi-model-mcp/SESSION.md "Owed before Phase 1's V6"] decision A now has counts, options and a stated tolerance, § 6 gates item 7 on Mike's ruling, and under (a) § 2.6 needs no parameter; the step-0 counts are phone-side and cannot be checked from the repo, and the plan itself marks what type 90 is as unconfirmed.

### NEW

1. [§ 2.2 "keyed fingerprint … under the server's signing key", § 2.1 "rotating `METATRON_AUTH_PASSWORD` revokes every one"] [/Users/md-homefolder/Desktop/multi-model-mcp/core/auth.py:_signing_key]
Wrong: The fingerprint that decides duplicate versus clash is keyed to a secret the plan elsewhere treats as routinely rotated.
Fails: After a password rotation every stored fingerprint differs from a freshly computed one, so each backup-sourced `message` on an already-seen key reads as a clash and is re-keyed and ingested as new.
Costs: The re-send dedupe that `seen` gave inverts into duplicate facts, including duplicate `action_required` lines in head-layer context, exactly when the phone must be re-paired — medium.

2. [§ 2.4 "Its own early `seen` load (`:1159`) is used only for the adapters' `skip` predicate", § 1 V9 "already prunes `seen`"] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:_prune_seen, :sweep line 1159; /Users/md-homefolder/Desktop/multi-model-mcp/tests/test_intake_pipeline.py]
Wrong: The only call to `_prune_seen` wraps the load the revision demotes to a read-only copy, and nothing says `ingest()`'s re-read prunes.
Fails: The pruned copy is no longer the one saved, and `test_intake_pipeline.py` has no prune assertion, so "must pass unchanged" passes either way.
Costs: `seen.json` stops shrinking while WhatsApp adds about 60 ids a day and the whole file is rewritten on every events post, and V9's stated premise is silently false — medium.

3. [§ 2.3 `info` → domain `None`, T25] [/Users/md-homefolder/Desktop/multi-model-mcp/tools/intake.py:_empty_queue]
Wrong: `_empty_queue` counts every row with no domain as "ingested message(s) currently carry no domain", and the plan lists no change to it.
Fails: Recorded-only `info` facts add about 50 a day to that count, which is put in the note handed to any specialist that reads an empty queue, beside the line that classification is not active.
Costs: Specialists are told thousands of messages went unrouted, an explanation written for unclassified mail, and may act on or relay it — speculative.
