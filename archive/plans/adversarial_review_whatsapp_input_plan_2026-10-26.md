*Adversarial review of `archive/plans/whatsapp_input_plan_2026-10-26.md` (draft, pre-revision).*
*Reviewer: Fable (adversarial-reviewer agent), effort: medium, 2026-10-26. Verbatim report below.*

## STRUCTURAL

1. [§ 1 ruling 2, § 8.8, § 11] [archive/plans/multi_user_accounts_plan_2026-10-26.md § 1–2; ROADMAP.md § Section 0 amendment 2026-08-28]
Wrong: The plan's entire privacy basis is "single-user", yet a second-user plan approved by Mike the same day (gated only on day-planner Stage B, which SESSION.md names as next) is absent from § 11's recent-work check and neither plan gates on the other.
Fails: WhatsApp Phases 1–4 and the Iva account land in overlapping weeks, at which point third-party WhatsApp content is flowing to Vertex under a basis § 8.8 itself says has lapsed, with no step in either plan that notices.
Costs: Irreversible disclosure of other people's messages under a ruling that no longer holds, approved because the plan was read in isolation — high.

2. [§ 0.5, § 3 V8, § 5 W3] [core/server.py:_log_conversation, core/server.py:_save_exchange, tools/diarist.py:98 → core/memory.py:index_entry, tools/logger.py:382, tools/obligations.py:open_task]
Wrong: "Un-sharing someone deletes everything Metatron derived from them" is promised to the user, but V8 deletes only intake rows, seen, flags and cursors — every fact Synth raised persists in the conversation store, the Diarist's journal, the daily log, the FAISS index (which the plan concedes has no delete path) and any task opened from it.
Fails: The first un-share after a fact has surfaced leaves that person's proposal, name and chat in five stores V8 never touches, and W3's recommendation ("hard delete") is accepted on that false guarantee.
Costs: A consent-withdrawal promise that cannot be honoured, discovered only when someone checks — high.

3. [§ 3 P2, P3, V4] [tools/intake.py:Envelope, tools/intake.py:envelope_id, tools/intake.py:sweep (seen-set keyed on env.id)]
Wrong: V4 sets `native_id` to WhatsApp's message key, but the live notification path (P2) carries no such key — only the nightly backup (P3) does — so the same message produces two envelope ids.
Fails: Every live-ingested message is re-ingested that night as a fresh envelope: two records, two surfaced facts, two `match_envelope` proposals and a double-firing awaiting-reply backstop; Phase 0's probe list does not look for a dedup key because none exists in the notification.
Costs: The envelope contract is wrong from Phase 1 and the user sees every proposal twice from the first live day — high.

5. [§ 3 V4, V5] [tools/intake.py:collapse_threads, tools/obligations.py:_resolve_source (source_thread ← record thread_id), tools/obligations.py:match_envelope (thread basis)]
Wrong: The plan never states what `thread_id` a WhatsApp envelope carries, and that unstated choice decides V5's behaviour in both directions.
Fails: If `thread_id` is the chat, a WhatsApp chat is one thread for life, so every later message from that contact proposes a close on every open task opened from that chat; if it is empty, the "thread" basis never fires and V5's "picks up later replies" rests on `_sender_matches`, whose non-email branch is a substring test on display name.
Costs: Phase 1 either floods the proposal card or silently never links replies, and the plan's "verify it matches" note cannot catch a defect it did not define — high.

6. [§ 4 Phase 0 exit, § 3 P2, V1, § 0.1] [core/server.py V1 as specified: drop by ID against the VM share-list copy]
Wrong: The pre-committed fallback "if notifications carry names only, match by chat and display name, the backup corrects it" defeats the share list on the live path, because a WhatsApp display name is set by the sender and a name-matched event carries no ID for V1's second check.
Fails: A non-shared group member who adopts a shared member's display name is ingested live and can raise an alert before the nightly correction; V1's "second check behind the phone's" has nothing to check.
Costs: § 0.1's guarantee ("nobody is shared until you tick them") is false on the live path in a branch the plan has already accepted as a design change rather than a stop — medium.

7. [§ 1 ruling 8, § 4 C0, § 3 V2–V3, § 6 Build] [SESSION.md § Do not re-open: "reads correspondence as code, never a model judgement — do not re-derive"]
Wrong: C0 is the fork that decides where V2/V3 live and whether Phase 2 gains a model runtime, yet Phase 0 — the only phone session before it — probes nothing C0 needs, and the plan does not surface the standing settlement that correspondence is read as code.
Fails: Mike rules at C0 with no device evidence and without the recorded ruling in front of him; a "phone model" answer re-shapes § 3, § 6 and the Phase 2 estimate after Phase 0's budget is spent.
Costs: Either a blind ruling or a second probe session, and a re-derivation SESSION.md forbids — medium.

10. [§ 8.2, § 8.4, § 8.5, § 4 Phase 0 step 2] [no in-repo reference; the only local crypt15 description is the GPL `wa-crypt-tools` source Mike installed]
Wrong: The plan requires a Java decrypt "written independently from the format" while stating the format is undocumented and web access is denied, which leaves the GPL implementation as the only readable specification.
Fails: The Phase 0 session can only reach the format by reading GPL code, which is the porting § 8.5 says will not happen; "throwaway" Phase 0 code then becomes P3 or is written twice.
Costs: A licence posture that is asserted rather than achievable, decided by whoever builds Phase 0 — medium.

## LOCAL

4. [§ 3 V5] [tools/obligations.py:open_task (1117, no turn or `_USER_ACT` check), tools/obligations.py:_close_refusal (2064 — the gate is on close), tools/obligations.py:_from_user_or_direct (1362 — gates day-start settings)]
Wrong: "`open_task` is user-gated" is false in code; the only code gate is on closing a task, and line 1362 gates a setting, not task creation.
Fails: Synth can file a task whose `what` is a stranger's extracted fact without the user's word, so a shared contact's message becomes tracked state with no consent step.
Costs: Third-party text creating obligations the plan told Mike only his word could create — high.

8. [§ 3 P5, § 6 Unseen 1] [core/auth.py:TOKEN_TTL_SECONDS (93, 30 days), core/auth.py:issue_token, core/server.py:auth_login (the only mint path, password-only; no refresh route)]
Wrong: "Refreshed when the token's expiry passes" names a mechanism that does not exist — tokens are minted only by password login in the WebView.
Fails: Thirty days after the last login the native listener's posts return 401 until the user opens the app and re-enters the password, adding a scheduled silent gap to the one the plan already lists.
Costs: A recurring month-boundary blackout of the live feed with no meter — high.

9. [§ 3 P3, V6] [tools/intake.py:sweep per-envelope body (classify, _record_row, match_envelope on every envelope)]
Wrong: The user's own sent messages are the only reply signal V6 has, yet the plan never says how they are distinguished in `ingest()` or how one clears an awaiting-reply flag.
Fails: As specified they enter the same body as inbound messages — classified, recorded as intake rows with the user as sender, fed to `match_envelope` — and nothing resolves the flag they were fetched to resolve.
Costs: V6 cannot be built from the plan as written and the user's own words become intake records — medium.

## VERIFY — 2026-10-26, round 2 (same reviewer, against the first revision)

1. CLOSED — [archive/plans/multi_user_accounts_plan_2026-10-26.md § 2 ruling 2, § 4.9 item 1, § 9 D9; ROADMAP.md § Section 0 (still unamended)] the extension ruling 2 cites exists in the second-user plan as a build-time amendment, and the banner sequences Phases 1–3 behind that build, so the consent basis is written before any WhatsApp content reaches the VM.
2. CLOSED — [core/server.py:_save_exchange, tools/diarist.py:98 → core/memory.py:index_entry, tools/logger.py:382, tools/obligations.py:open_task] § 0.5 and V8 now name exactly the stores the purge does not reach, and W3 puts the choice to Mike rather than promising past it.
3. NEW SHAPE — [tools/intake.py:envelope_id, tools/intake.py:sweep (seen-set keyed on env.id)] one `native_id` on both paths removes the duplicate for an unchanged message, but the key hashes the text, and the two renderings diverge for an edited message (the notification carried the original, the backup holds the edit) and for system-trimmed long text, while Phase 0 step 3 probes only the time field — the duplicate survives for that class and the probe cannot see it.
4. NEW SHAPE — [tools/obligations.py:_from_user_or_direct:1362–1366, tools/turn_context.py:37–45 (`user_turn` = the user said something), tools/obligations.py:open_task:1123 (`source_id` optional), tools/obligations.py:_close_refusal → _named_by:2028] the proposed gate passes on any turn containing user speech — it never checks that the words name the fact, unlike the close gate — and keys on a model-supplied optional `source_id`, so Synth opens the task on an unrelated user turn or by omitting `source_id`, and "exists only because the user said so" is still false.
5. NEW SHAPE — [tools/obligations.py:add_proposal:2253 (dedup by envelope_id only), tools/obligations.py:match_envelope:2405 (expect_from basis), tools/obligations.py:open_task:1174–1178 (`expect_from` kept for `waiting` only)] empty `thread_id` removes the chat-as-thread flood but the sender basis replacing it parks one proposal per message from that sender on every open one-off task, `add_proposal` dedups per envelope not per task, declining never stops the next message, and the Phase 1 test the plan writes ("one proposal per task, not three") fails on current code with the change that would pass it in no file row.
6. CLOSED — [tools/intake.py:Envelope.sender_address, tools/intake.py:_record_row:634] every event now carries an ID the VM can check, and a no-ID result is a stop, not a fallback.
7. CLOSED — [SESSION.md:45 (code-not-model settlement); plan § 4 Phase 0 step 5, C0] the device facts are gathered before C0 and the settled ruling is put in front of Mike at the checkpoint.
8. CLOSED — [core/auth.py:issue_token:152 (expiry-only HMAC, no subject or scope), core/server.py:require_auth:97] the nonexistent refresh is replaced by a new token type the plan correctly treats as new code with its own lifetime, deletion path and meter.
9. CLOSED — [tools/intake.py:sweep:1153–1210 (the body `ingest()` is split from), tools/intake.py:sweep:1104–1107 (early returns V6 inherits)] markers carry chat ID and time only, bypass `ingest()`, and clear the flag in V6.
10. CLOSED — [no in-repo anchor: `wa-crypt-tools` is in Mike's environment, not `requirements.txt`] the contradiction is resolved into W9 with the clean-room option recommended and the Phase 0 module no longer called throwaway.

### NEW — STRUCTURAL

N1. [§ 2 Identity, P1, P2, V1, V4, V5] [tools/obligations.py:_sender_matches:2371–2372 (exact address compare), tools/intake.py:_record_row:634 (`sender` = sender_address)]
Wrong: The revision makes the sender's WhatsApp ID load-bearing for the share-list check (V1) and task-reply matching (V5, exact compare), but § 2 measured that one person has two IDs — a phone JID one-to-one and a hidden `@lid` in groups (827 of 828 group messages) — and nothing in P1/P2/V4 canonicalises an event's sender to one form.
Fails: A person ticked under one form is dropped on the phone and the VM when they write under the other, a task opened from a group message never matches that person's one-to-one reply, and Phase 0's exit asks only for "a WhatsApp ID", not one that maps to the share list's key.
Costs: Most group traffic — the majority the plan says the list "must work inside" — is silently dropped or never links, and the exact-match fix for finding 5 matches nothing across contexts — medium.

### NEW — LOCAL

N2. [P5, V1] [core/server.py:require_auth:97–118, core/auth.py:is_open_path, core/auth.py:verify_token:159]
Wrong: "Accepts only the device token" must pass a middleware that verifies every non-open path with `auth.verify_token` and was written so no endpoint carries its own auth — the plan does not say whether `/whatsapp/*` becomes an open path with an endpoint-level check or the middleware gains a path-scoped second verifier.
Fails: The easy route — add the path to `is_open_path`, check inside the handler — is exactly the per-endpoint pattern the middleware's docstring exists to forbid, and it is the one a Phase 1 build reaches for first.
Costs: A third-party-data ingestion endpoint whose authentication regresses to the design the project already rejected, decided by whoever builds V1 — medium.

N3. [P2 (per-install salt), P3 (phone-held cursor), § 6 persistent objects, M5 sideloads] [tools/intake.py:envelope_id (seen keyed on channel + native_id)]
Wrong: The dedup key is salted with a per-install secret and the backup cursor lives on the phone, but § 6 lists neither as a persistent object and nothing says what a reinstall or clear-data does to them.
Fails: A reinstall resets cursor and salt together, so the next backup re-sends up to W6's 90 days under keys the VM's `seen` has never held — every one a new record, fact and proposal.
Costs: A duplicate flood of the whole window after any uninstall/reinstall across the phase sideloads, reversible only by a channel-wide purge — medium.

## VERIFY — 2026-10-26, round 3 (same reviewer, against the second revision)

3. CLOSED — [tools/intake.py:envelope_id:201, tools/intake.py:sweep:1141 (`env.id not in seen`), tools/intake.py:_append_record:589] a text-free deterministic key gives both paths one `native_id` that an edit cannot change, so `seen` blocks the nightly copy and any reinstall re-send; the edit/trim case is carried by the update path, whose `revise()` replaces a row in the append-only `records.jsonl` through the same channel-scoped rewrite exception V8 already establishes, and Phase 0 step 3 now probes both divergence cases.
4. CLOSED — [tools/obligations.py:open_task:1117 (no consent gate), tools/obligations.py:_close_refusal:2064 (the only gate), tools/obligations.py:_user_act:2013 and act_from_app:2426 (the user-act pattern "Track this" reuses), tools/obligations.py:open_task:1174–1178 (`expect_from` stored for `waiting`)] the false claim is withdrawn and the true code state is stated; the consented path is a code tap setting `source_id`/`expect_from` on a `waiting` task, which is the kind that already keeps `expect_from`.
5. CLOSED — [tools/obligations.py:_PROPOSAL_SOURCES:2226 (must gain `"whatsapp"` or `add_proposal:2240` coerces it to `"correspondence"` and the per-envelope dedup returns), tools/obligations.py:add_proposal:2260 (key-based dedup, the location pattern), tools/obligations.py:resolve_proposal:2310 (a declined proposal stays on the task with status `declined`, so a key check blocks every later card), core/server.py:_proposals_for_display:1450 (reads `p["envelope_id"]` for every non-location source — a per-task-keyed proposal needs its own branch here, in a file already in the Phase 1 row)] one card per task, ever, with decline terminal, holds on the mechanism the plan names.
N1. CLOSED — [tools/obligations.py:_sender_matches:2371 (exact compare, now on canonical IDs), tools/intake.py:_record_row:634 (`sender` = canonical ID)] canonicalisation through last night's `jid_map` happens on the phone before the share list, live feed, backup reader or any VM field sees an ID, an unmappable live ID is dropped until the next backup maps it, and Phase 0's exit now requires the canonicalised live ID to equal the share-list key.
N2. CLOSED — [core/server.py:require_auth:97–118, core/auth.py:is_open_path:236 and OPEN_PATHS:101] the second verifier lives in the middleware, path-scoped, and `/whatsapp/*` is barred from `is_open_path` by the plan's own text.
N3. CLOSED — [tools/intake.py:envelope_id:201 (deterministic, so the VM's `seen` holds across reinstall)] the salt is gone with the text, the backup cursor is a VM-held per-user object the phone reads each run, and § 6 now lists both the 72-hour list and the cursor with unit, deletion and meter.

### NEW — STRUCTURAL
none

### NEW — LOCAL

R3-1. [§ 3 V1 ("`/whatsapp/*` paths accept only device tokens, and device tokens are refused on every other path"), § 3 V7 ("`GET /whatsapp/cards`, shown on the same 30-second poll as `refreshProposal`"; "a tap posts to a user-act endpoint the way `/tasks/act` does")] [static/index.html:refreshProposal:3991 (`authFetch` — session token/cookie), static/index.html:authFetch:992, core/server.py:require_auth:97]
Wrong: The verifier N2 asked for is scoped to the whole `/whatsapp/*` prefix and admits only device tokens, while V7 puts the user's card poll and "Track this"/"Dismiss" taps under that same prefix from the WebView, which holds only a session token.
Fails: The middleware refuses every `GET /whatsapp/cards` and every card tap with 401, so the held-back-flag card (§ 0.3) and the consented "Track this" path (V5) — the two user-facing surfaces this plan adds — never render, and `authFetch`'s 401 handling drops the user to the login screen on every 30-second poll.
Costs: The card surface and the only consented task path are unreachable as specified, discovered on the first Phase 3 sideload — high.

## VERIFY — 2026-10-26, round 4 (R3-1 only)

R3-1. CLOSED — [core/server.py:require_auth:97–118 (single gate, now with a `/device/*`-scoped device-token verifier), core/auth.py:OPEN_PATHS:101 / OPEN_PREFIXES:102 / is_open_path:236 (neither `/device/` nor `/whatsapp/` is open, and no existing route in `core/server.py` sits under either prefix), static/index.html:authFetch:992 and refreshProposal:3991 (the WebView's session token now reaches `GET /whatsapp/cards` and `POST /whatsapp/cards/act`), core/server.py:_proposals_for_display:1450 and tools/obligations.py:_PROPOSAL_SOURCES:2226 (the two round-3 notes on item 5 are now named changes)] the device-only prefix and the session-token prefix no longer overlap, so the card poll and the taps are admitted by the same middleware that refuses device tokens there.

### NEW — STRUCTURAL
none

### NEW — LOCAL
none

## VERIFY — 2026-10-26, round 5 (Mike's W1–W10 decisions applied: chat-level sharing, per-user, clean room, legal checks)

**(a) W2 — per-chat sharing**

A1 (S). [P2 unverified-sender branch; P2 dedup key; V3 sender rule; V4 `sender_address`; V5 exact-address match] [tools/intake.py:Envelope.sender_address:225, tools/intake.py:_record_row:634 (`sender`), tools/intake.py:Envelope.ledger_key:248 (`addr:` from sender_address), tools/obligations.py:_sender_matches:2371–2372]
Wrong: P2 now pre-accepts a live group sender identified only by display name ("marked unverified"), but nothing downstream has an unverified state — the dedup key still takes "canonical sender ID", V4 still sets `sender_address` to a canonical ID, V3 still promises the user's own contact name, and V5's exact branch assumes `sender_address` is never sender-set text.
Fails: Such a message's live key has no canonical sender while its backup copy does, so the two key differently and `seen` admits both; whatever is written to `sender_address` becomes the record's `sender`, its `addr:` ledger key and the name on cards, and a display name containing `@` and set to a shared person's ID passes the exact branch and parks a close on that person's waiting task.
Costs: Duplicates and mis-attributed or impersonated facts on 827 of 828 group messages if Phase 0 finds no person key in group notifications — a branch the plan accepts without tracing it — high.

A2 (S). [V4 (`thread_id` = empty, `subject` = the fact); V1 scope; V6 "same chat"; V7 "which chat"; V8 per-chat purge] [tools/intake.py:Envelope:214–230 (no chat field; `signals` advisory), tools/intake.py:_record_row:625–654 (persists no `signals`, no chat), tools/obligations.py:_resolve_source:2355 → match_envelope:2403]
Wrong: Per-chat sharing makes the chat ID the key for V8's purge, V6's reply-marker join and V7's card, yet the envelope the plan maps onto has no chat field, `thread_id` is deliberately empty, and `_record_row` persists nothing from `signals`.
Fails: Un-sharing a chat has no row field to select, so V8 cannot find the rows it must delete and V6/V7 cannot join a fact to its chat; carrying the chat in `thread_id` instead restores `source_thread` and the thread-basis flood finding 5 closed.
Costs: The W3 promise "deletes Metatron's WhatsApp store for it" is not executable per chat without a record-schema addition no file row names, and the obvious shortcut reopens 5 — high.

A3 (L). [P1 "chat ID, which has no such split — a group's ID is stable"; § 2 identity counts] [tools/intake.py:_record_row:634]
Wrong: P1 asserts chat IDs have no phone/hidden split, but § 2's own count has 629 one-to-one chat rows keyed by hidden ID, 582 linked by `jid_map` to a phone number — the split exists for exactly the one-to-one chats V5 and W8 serve.
Fails: A one-to-one chat ticked under one form and notified under the other is dropped by the phone and the VM as "not shared" — N1's mechanism moved from sender to chat — and Phase 0's exit probes the chats tested, not the rule.
Costs: Silent loss of live one-to-one messages for lid-migrated contacts, with canonicalisation already built for senders and withheld from chats on a false premise — medium.

**(b) W8 — re-surface once while relevant**

B1 (L). [V6 "only while its date/time has not passed", "once"] [tools/intake.py:_record_row:625–654 (`received` is the message time; no field for the fact's event time; `outstanding:651` is the available once-flag)]
Wrong: The relevance test compares the fact's extracted event time, which V3 produces but no persisted field holds — the row keeps the fact as `subject` text and the message's `received` time only.
Fails: Without the event time (and the chat, A2) on the row, the test degrades to "received more than 24 h ago", which re-surfaces facts whose moment has passed — the case W8 was decided to exclude.
Costs: W8 as ruled is unimplementable on the stated row and the fallback is the behaviour Mike declined — medium.

**(c) W10 — per-user for Iva**

C1 (L). [Ruling 2, W10, L2, § 7, § 10] [tools/intake.py:load_config:149–164 (per-persona `intake.yaml` over the template), config/templates/intake.yaml:31–34 (`channels`), CLAUDE.md § Mike-gated work]
Wrong: Iva's switch-on is a per-persona `channels.whatsapp: true` on the VM plus her share list, device pairing and the L2 consent record in `ROADMAP.md` § Section 0 — all Mike-executed — yet § 7 lists no M-step for her and § 10 has no `ROADMAP.md` row for the record L2 requires.
Fails: "Switches on once consent is recorded and L1–L3 are done" names no session that performs the switch or writes the record, so it stands on a list — the failure the (M) rule exists to prevent.
Costs: Her channel either never turns on or turns on in an unplanned session without the consent text in front of her — medium.

**(d) W9 — Phase 0a/0b clean room**

CLEAN — [no code anchor exists: 0a/0b produce only new code; § 4 sequences Phase 0 after 0b and lands 0b's acceptance (Mike's phone reproducing § 2's counts) in M1; § 6 carries the added budget] nothing here touches an earlier closed finding.

**(e) § 8a, M6, C0 → LM**

E1 (L). [§ 8a L4–L8 "added to Track C's brief"] [ROADMAP.md:1065–1070 (Track C not carried; lives only in the static plan), .claude/rules/docs-and-logs.md (`archive/plans/phase5_to_future_roadmap_2026-06-10.md` is never edited), archive/plans/phase5_to_future_roadmap_2026-06-10.md:409 (C0 exists — the rename is sound)]
Wrong: L4–L8 are "added to Track C's brief", but the brief is Phase 6B's future output, Track C's only present home is the static plan that is never edited, and `ROADMAP.md` does not carry Track C — so no file a 6B session reads holds them.
Fails: The Phase 6B session opens the static plan and `ROADMAP.md`, finds no WhatsApp items, and the checks survive only in this plan's § 8a.
Costs: L4–L8 lost before the brief is written — the recorded-only-in-a-narrative failure — medium.

### REOPENED

- **3** (dedup) — by A1, for the unverified-sender branch: live key lacks the canonical sender the backup key carries.
- **5** (sender match / one card per task) — by A1 (exact-address branch now reachable by sender-set text) and by A2's shortcut (chat in `thread_id` restores the thread basis).
- **N1** (one person, one ID, used everywhere) — by A1 (no canonical ID for unverified senders) and A3 (chat IDs exempted from canonicalisation on a false premise).
- **6** — not reopened: scope is still gated on a chat ID the sender cannot set.

## VERIFY — 2026-10-26, round 6 (round-5 items only)

A1. CLOSED — [tools/intake.py:Envelope.sender_address:225 (empty admissible), tools/intake.py:Envelope.ledger_key:250 (falls to `chan:whatsapp` on an empty address — see N-L1), tools/obligations.py:_sender_matches:2371–2376 (an `@` expect never equals an empty address; the non-`@` branch tests `expect in display`, so `sender_display` must stay empty for sender-less events too, or `match_envelope` is skipped for them), tools/intake.py:sweep:1141 (`seen` on a key carrying no sender)] a sender-set name is never stored, the key no longer contains a field one path lacks, and the backup's update supplies the canonical sender.

A2. CLOSED — [tools/intake.py:_record_row:625–654 (untouched), tools/intake.py:_intake_dir:171 (the `intake/` directory the index sits beside `records.jsonl` in), plan § 6:413–414 (listed, bounded by the facts it indexes)] chat, event time, type, sender-known and re-surfaced state live in `intake/whatsapp_index.jsonl` keyed by envelope id, and V6/V7/V8 join through it with `thread_id` still empty.

A3. CLOSED — [plan § 2:64–66 (629 hidden-ID one-to-one chats, 582 linked); tools/intake.py:_record_row:634] the "no split" premise is withdrawn, chat IDs canonicalise through `jid_map` exactly as senders do, and an unmapped live one-to-one chat is held for the backup rather than dropped.

B1. CLOSED — [tools/intake.py:sweep:1104–1107 (V6 inside `sweep()`, inheriting its quiet-hours skip); plan V4 index fields (event time, re-surfaced flag)] the relevance test reads a persisted event time and a once-flag, with a stated 72-hour rule when extraction found no time.

C1. CLOSED — [tools/intake.py:load_config:149–164 (per-persona `intake.yaml` layered over the template), config/templates/intake.yaml:31–34 (`channels`), plan § 7:441–444 (M7), § 10:533–534] the switch-on is a named guided session, and both her VM-owned config and the `ROADMAP.md` consent record have file rows.

E1. CLOSED — [ROADMAP.md:1065–1070 (§ Not carried over exists and is the file a 6B session opens); plan § 8a:489–493, § 10:534] a one-line pointer in the live roadmap carries L4–L8 to Phase 6B without editing the static plan.

### NEW — STRUCTURAL
none

### NEW — LOCAL

N-L1. [V4 "the ledger key falls back to the channel"; V4 "a new signal branch in `classify`" (source label unnamed)] [tools/intake.py:Envelope.ledger_key:250 (`chan:whatsapp` for every sender-less envelope), tools/intake.py:sweep:1205–1207 (`observe()` fires when `result.source in ("rule","headers")`), tools/intake.py:observe:350–356, tools/intake.py:_ledger_lookup:327–347 (five observations at ≥80% dominance → classifies), tools/intake.py:classify:563–577 (the ledger outranks the header/signal stage)]
Wrong: The plan treats the empty-sender ledger fallback as benign, but every sender-less group fact now shares one ledger key, and if the new signal branch reports `source="headers"` — the label the existing code teaches from — `observe()` pools their categories under `chan:whatsapp`.
Fails: After five sender-less facts with one dominant category, `_ledger_lookup` fires ahead of the signal branch and stamps that category on every later sender-less WhatsApp envelope, so a proposal-with-a-time from a group is filed under whatever that group usually sends; the same mechanism, per canonical sender, learns a chatty friend into their usual category and overrides their occasional request.
Costs: Mis-filed domains and queues for exactly the group traffic W2 brought into scope, decided by a one-word source label the plan never names — medium.

### REOPENED
none — 3, 5, N1 and 6 stay closed on the anchors above.

*Author's note (not the reviewer's): N-L1 fixed in V4 after this round — WhatsApp reports source `"whatsapp"`, never feeds `observe()`, and `classify` skips `_ledger_lookup` for the channel; `sender_display` stays empty for sender-less events (A1's note). Not re-verified.*
