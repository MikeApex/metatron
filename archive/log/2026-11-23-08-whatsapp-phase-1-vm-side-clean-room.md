### 2026-11-23 (WhatsApp Phase 1, VM side, clean-room — the server receives, screens, translates Bulgarian, extracts facts and surfaces what needs the user; the channel ships off) — **committed `e45c7cd`, pushed; nothing deployed**

**Incoming handoff:** `archive/handoffs/2026-11-23-whatsapp-phase-1-vm-side-prompt.md` (log § 11-23 sixth). Clean-room rules held:
- no transcript opened;
- WhatsApp log entries read only in fragments titled "clean-room";
- nothing under `/private/tmp` outside the scratchpad;
- no crypt implementation, no web.

The Fable reviewer was given the same limits.

**Step 0 (probe, `src/waprobe/` only; one tap, done before 02:00 — the omitted messages were already in the two rotated sets).**
- Button 7 now counts `message_type` for the messages the increments carried and for those they left out. Types are read from the newest full backup while it is decrypted.
- **All 26 omitted own messages are type 90, all in one-to-one chats.** Type 90 is 3,362 rows in the whole backup, 0 with text.
- Every other kind of own message reached the increments the next night.
- What 90 is, is **not** known: the increments also carry a `call_log` delta, so it may be calls, an inference from shape only.

**Step 1 — the plan re-anchored** (`archive/plans/whatsapp_phase1_build_plan_2026-11-23.md`). Every V-item was placed at today's line.
- Premise killed: "any token can name any persona" — user and admin tokens have been bound since 10-27.
- New: the sweep (scheduler process) and the endpoint (server process) race on `seen`/`ledger`; consent had no WhatsApp scope; a push channel would warn "no adapter" every hour.
- **Fable review: 6 findings.** Rank 1: the WhatsApp sender basis matched nothing in Phase 1, because `expect_from` is the model's free text until Phase 3's "Track this". **Verify closed 5, left 1 partial and found 3 new**, all fixed in the plan before the build:
  - group `?` messages surfaced and lifted the decline guard;
  - the fingerprint was keyed to the rotatable password;
  - the `seen` prune was lost in the split;
  - `_empty_queue` would have counted recorded-only facts as "unrouted".

**Rulings (Mike).**
- **A, B: as recommended.** A redundant re-raise of a question answered only by a type-90 event is accepted. `info` facts are recorded only.
- **C amended:** consent withdrawal stops collection; deletion is the user's opt-in (`POST /whatsapp/delete-all`). Un-share still purges at once (W3).
- **D amended:** *"It should be able to intake other languages and translate them."*
  - Options put: a local translation model on the VM, per-language word lists, or cloud translation (refused by ruling 3).
  - Chosen after asking the costs: **the local OPUS-MT model, Bulgarian only**; other scripts are held back unscreened.
  - **This amends the 11-22 LM ruling** for translation only; extraction stays code.

**Built (`e45c7cd`, 19 files):**
- the device token and `/device/*` gate in the middleware;
- the events, cursor and share-list endpoints, plus pairing and opt-in deletion;
- `ingest()` split out of `sweep()` under one re-entrant cross-process lock;
- the WhatsApp classify branch, kept out of the ledger, the digest and the decline guard;
- `tools/intake_whatsapp.py`: screen, translation, facts, salted fingerprint, update, backstop, purge, expiry;
- one WhatsApp card per task, matched on the user's own name as whole words;
- `scripts/fetch_whatsapp_translation_model.py`.

**Tests:** `tests/test_intake_whatsapp.py` 35/35; intake pipeline 21/21 unchanged; isolation guard passing, with a new device-route check; probe 73/73.

**Believed true, wrong:**
1. **The model's licence is Apache-2.0, not the CC-BY told to Mike** (quoted from memory; read from the downloaded model card).
2. **My 150–250 MB RAM estimate looked wrong at first** (+368 MB on the Mac) until split: the `ctranslate2` library is ~205–250 MB and **the VM's server already maps it** for speech-to-text. The model's own cost is +159 MB.
3. **Unloading did not return memory** (366 of 396 MB stayed) — `malloc_trim` added for Linux.
4. **`data/models/` was not git-ignored**; the 82 MB model could have been committed.
5. **Staging `tools/obligations.py` whole would have committed the other window's hunk** (the `mike` default removed from its `__main__`). Caught by a per-hunk check, and only my hunks were staged.
6. On the real model, "19:00" was lost: dateparser matched only the day and the translation said "7:00". Fixed by taking the clock from the original. "Hi, how are you?" surfaced as a question; greeting questions are now chat.
7. The screen first listed everyday profanity and words like *speed*/*joint*. They were cut, because facts never carry those words.

**Pre-existing, not this session's:** `day_plan_round2` F8, `task_ledger_consult` (a "Nov 3, 2026" date now past), `a4_complexity_threading` and `instruction_leak_filter` fail identically on clean `HEAD`. Not filed (Mike did not ask).

**Next:**
- **M2 labelling walkthrough** (proposed below), including Bulgarian messages;
- then M4 for `mike`: seed the `whatsapp` consent, the stanza on, fetch the model and `--check` on the VM;
- Phase 2 (phone) builds to plan delta § 2.2, after the owed Fable review of `src/main/…/whatsapp/`.

**Deployed 11-23 13:27 by Mike from another chat** (VM at `388a91c`, which includes `e45c7cd` and `23ddb28`; `dateparser`/`sentencepiece`/`tzlocal` import on the VM; server and scheduler active). The first post-deploy intake sweep had not yet run when this window closed; its check is in `SESSION.md`. **M2 prep prompt:** `archive/handoffs/2026-11-23-whatsapp-m2-labelling-prep-prompt.md` (Opus 5.5) — Claude never sees a message text; Mike labels in his own terminal and pastes only the numbers.

