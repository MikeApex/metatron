# WhatsApp Phase 1 (VM side) — re-anchored build plan, 2026-11-23

*A dated delta on `archive/plans/whatsapp_input_plan_2026-10-26.md` (§ 3 V1–V9), written
clean-room. That plan's line numbers are a month stale. Each V-item below names where it lands
**now**, whether the plan's premise still holds, and what this build does. Where this file and the
plan disagree, this file governs Phase 1. Status: **revised after Fable's adversarial review (6 findings,
`archive/plans/adversarial_review_whatsapp_phase1_build_plan_2026-11-23.md`) and step 0's counts
(§ 5 A); verify round 1 closed 5 of 6, with 1 partial and 3 new, all addressed in place (group
classification, per-user salt, prune, `_empty_queue`). Awaiting Mike's go-ahead on § 6's todo
list.***

---

## 0. What the user gets from Phase 1

**Nothing visible while the channel is off,** and it ships off for every user. Once Mike switches
it on for himself (M4: the channel stanza **plus** a `whatsapp` consent record), the VM can do
four things:
1. accept messages from a paired phone;
2. hold back anything objectionable before any model sees it;
3. turn the rest into short facts that reach Coordinator and Synth;
4. raise an unanswered one-to-one question once more after 24 h.

The phone that sends (Phase 2) and the cards (Phase 3) come later. **The need is met for the VM
half only.** Nothing reaches a user until Phase 2 exists and M2 (labelling) has measured the
extractor.

---

## 1. Re-anchored: where each V-item lands now

| V | Lands now | The plan's premise | This build |
|---|---|---|---|
| **V1** endpoints + device token | `require_auth` `core/server.py:115-149`; `bound_persona` `:156`; `Identity` `core/auth.py:180`, `issue_token` `:200`, `decode_token` `:217`; tokens are v2 `persona.role.cred_version.expiry.hmac` | **Partly stale.** *"Any valid token can name any persona"* is no longer true: user and admin tokens are bound to one persona (since 10-27). A **service** token still names its persona per request, so `/device/*` must refuse it. Middleware enforcement still holds as designed. | § 2.1 |
| **V2** screen | new `tools/intake_whatsapp.py`; no input-side screen exists (`filter_output` is output-only) | holds | § 2.3 |
| **V3** facts | same file; `dateparser` **not installed** in `.venv` or `requirements.txt` | holds; the sender name needs a source (§ 2.2: the share list carries the user's own labels) | § 2.3 |
| **V4** `ingest()` / `revise()` | `sweep()` `tools/intake.py:1142`; per-envelope body `:1203-1260`; `classify` `:539`; `_header_lookup` `:457`; `_ledger_lookup` `:327`; `observe` `:350` (called `:1257`); `_record_row` `:625`; `match_envelope` call `:1239` | holds. **New finding:** `sweep()` runs in the **scheduler process** and `ingest()` would run in the **server process**. Both load-modify-save `seen.json` and `ledger.json` without a lock, so concurrent writes clobber each other. `records.jsonl` is append-only, but `revise()`, the purge and the expiry all rewrite it. **Review 4:** `sweep()` loads `seen` (`:1159`) *before* a fetch that takes seconds and saves it at `:1270`, so the lock must cover the reload as well as the body, and `teach_intake` (`:1036-1042`) writes `ledger.json` from the server unlocked. **Review 3:** the declined-action guard (`tools/turn_context.py:_newer_intake_row` `:109`, used by `tools/confirm.py:216`) treats *any* intake row newer than a decline as a new trigger. | § 2.4, § 2.8 |
| **V5** proposals | `_PROPOSAL_SOURCES` `tools/obligations.py:3199`; `add_proposal` `:3203` (de-dupes per message `:3226`); `_sender_matches` `:3338`, exact branch `:3344`; `match_envelope` `:3352`; `open_task` `:1757` (`source_id` resolved `:1891`, `_resolve_source` `:3320`); `_proposals_for_display` `core/server.py:1960` | holds: one card per message today, so a chatty sender would park many | § 2.5 |
| **V5** route to Synth | `context_block` `tools/intake.py:844` surfaces `surface` rows until the domain's queue is read; returns `""` unless intake `enabled` | holds | unchanged; § 2.6 adds the V6 line |
| **V6** backstop | inside `sweep()`, so `core/scheduler.py` (Red) stays untouched; the `intake_sweep` job is `core/scheduler.py:804` | holds, **subject to step 0** (§ 5) | § 2.6 |
| **V7** cards | Phase 3 | — | not built; § 2.5 adds only the display branch an existing proposal card needs |
| **V8** purge | records "nothing is deleted" `tools/intake.py` header; append-only `_append_record` `:589` | holds. The rewrite needs the § 2.4 lock. | § 2.7 |
| **V9** 90-day expiry | `seen_retention_days: 90` already prunes `seen` (`_prune_seen` `:304`) | holds | § 2.7 |
| consent (W10) | `core/consent.py`; `SCOPES` `:35`, `is_granted` `:123`, fail-closed; `seed-consent` writes `text_version: "ruling"` (`scripts/accounts.py:323`) | **new:** there is no WhatsApp scope | add `"whatsapp"` to `SCOPES` only. Not in `APP_SCOPES`, and no text file: Iva's text is L2/M7. |
| channel loop | `_load_adapters` `:275` warns for any enabled channel with no adapter; the `sweep` pull loop `:1166` | **new:** WhatsApp is **push**. Left as is, every sweep would log that warning and record the channel as attempted. | `_PUSH_CHANNELS = {"whatsapp"}` is skipped by both |

**Checked against recent work:**
- `acc2a24` (P3 reader) fixes the phone's record (`WaMessage`: chat, key_id, from-me, time, sender, text, row id). The phone keeps the full backup's milliseconds when a second matches; an increment carries seconds.
- The second-user build (`core/accounts.py`, `core/consent.py`, v2 tokens) is in, and V1 is designed on it.
- No recent commit touches `tools/intake.py`'s sweep body.
- **Killed by the check:** the plan's "user from token" fix is already true for user/admin tokens, so it narrows to "device tokens, and service tokens refused on `/device/*`".

---

## 2. Design

### 2.1 V1 — the device token and `/device/*`

**Token.** `d1.<persona>.<device_id>.<hmac>`, signed with the same key as v2 tokens, so rotating
`METATRON_AUTH_PASSWORD` revokes every one. It carries no expiry of its own; life is decided by a
registry, because revocation and the 30-day-unused expiry both need state:

    data/personas/{p}/devices.json   {device_id: {created, last_used, revoked_at, label}}

- Nothing secret is stored: the token is derivable only with the signing key.
- `last_used` is written at most once an hour, so a busy listener does not mean a file write per
  request.
- A token **unused for 30 days, revoked, or unknown to the registry is refused.**
- For an account user, the account must also still be `active`, so disabling Iva's account kills
  her device too. `mike` has no account entry: skipped.

**`core/auth.py`:** `issue_device_token(persona, label)`, `decode_device_token(token)` →
`Identity(persona, "device")`, `revoke_device(persona, device_id)`, `list_devices(persona)`.
`decode_token` already refuses anything not starting `v2.`, so a device token can never pass as a
session token.

**`require_auth`**, one new branch before the existing ones:
- path under `/device/` → **only** `decode_device_token` (401 otherwise). A session token and a
  service token are both refused there.
- any other path presented a `d1.` token → 401.

**`bound_persona`:** role `device` → `identity.persona`, and a named persona that differs → 403.
**The body never names a user;** the schema has no persona field.

**Pairing (session token, `user`/`admin` only, never `service`):**
- `POST /whatsapp/device/pair {label}` → the token, **shown once**;
- `GET /whatsapp/devices` → ids, labels, created, last used — no tokens;
- `POST /whatsapp/device/revoke {device_id}`.

Pairing works with the channel off; it is harmless. Events are refused until the channel's gate
opens (§ 2.2).

**Body cap, before parsing.** `/device/*` handlers take the raw `Request` and read
`request.stream()` up to **512 KiB**, returning 413 past it. A `Content-Length` over the cap is
refused before anything is read; a chunked body is counted as it streams. Then JSON, then the
pydantic models below. **At most 500 events per request:** the phone batches, and a first run
over W6's 90-day window is about 5,400 messages, so about 11 posts.

### 2.2 The endpoint schema — the contract Phase 2 builds to

**The gate**, checked on every `/device/whatsapp/*` call (403 `channel_off` otherwise, which the
phone shows as "WhatsApp link is off"). The channel is open only when all three hold:
1. intake is `enabled`;
2. `channels.whatsapp` is `true`;
3. `consent.is_granted("whatsapp", persona)`.

```
POST /device/whatsapp/share-list            (replaces the VM's copy whole)
{ "chats": [ { "chat": "<canonical chat id>",
               "kind": "one_to_one" | "group",
               "label": "<the user's own address-book name | the group's subject>",
               "senders": { "<canonical sender id>": "<the user's own contact name>" } } ],
  "merges": [ { "from": "<hidden id>", "to": "<canonical id>" } ] }       // P1's migration
→ { "shared": n, "removed": m, "purged_facts": k }
```
- A chat in the old list but not the new one is **un-shared → V8 purge, at once**, before the
  reply is sent.
- `label` for a group is its subject, which any member can set, so it is untrusted text: wrapped
  wherever it reaches a model, and capped at 60 characters.
- `senders` holds only names from the user's own address book (P1). A WhatsApp display name never
  arrives here.
- `merges` rewrites index and marker entries from the hidden id to the canonical one.

```
POST /device/whatsapp/events
{ "events": [ {
    "kind":    "message" | "update" | "reply_marker",
    "chat":    "<canonical chat id>",          // REQUIRED — an event without one is rejected
    "time":    <int, SECONDS since the epoch>,  // REQUIRED — see the key below
    "ordinal": <int ≥ 0, default 0>,            // among this chat's messages in the same second
    "sender":  "<canonical id>" | "",           // groups only; "" when the live event had none.
                                                // For a one-to-one chat the VM uses the chat id
    "text":    "<string ≤ 4,000 chars>",        // message/update only; never on a reply_marker
    "source":  "live" | "backup" } ],
  "cursor": <int seconds, optional> }           // backup runs only: the newest time now delivered
→ { "accepted": a, "duplicates": d, "updated": u, "dropped_not_shared": s,
    "held_back": h, "rejected": [ {"index": i, "reason": "..."} ], "action_needed": bool }
```

**The message key, defined here and built by the VM, not trusted from the phone:**

    native_id = f"{chat}|{time}|{ordinal}"      time = whole SECONDS

- **Seconds, because increments carry seconds** (format description § 12, `1.3` = timestamp/1000
  on 605/605), while the full backup and live notifications carry milliseconds. The phone floors
  every time to the second before sending.
- **The VM refuses any `time` ≥ 10¹¹** (that is a millisecond value). So a live message and its
  nightly copy can only key differently if their seconds differ, and Phase 0's probe 3 measures
  exactly that.
- No text and no sender in the key (plan P2).
- `ordinal` is the phone's: the 0-based position among the same chat's messages in that second,
  by row id from a backup and by arrival order live.
- **A same-second clash must not lose a message (review 5).** If one path numbers message A
  ordinal 0 and the other path numbers a different message B ordinal 0, B would otherwise be
  dropped as a duplicate of A. So the index stores a **keyed fingerprint** of each fact's source
  text: HMAC-SHA256 under a **per-user random salt** (32 bytes, made on first use, kept in
  `whatsapp_state.json`, deleted by the channel purge), 16 hex characters. It is **not** the
  auth signing key: rotating the password must not turn every re-send into a "clash" (verify
  new 1). The fingerprint is not text, and it cannot be reversed without the salt.
  - A `message` event whose key is already seen, from `backup`, with a **different**
    fingerprint is a clash. It is re-keyed `chat|time|ordinal|<fp8>` and ingested as new.
  - The worst case is a **duplicate** fact (for example a trimmed live copy whose 72-hour list
    the phone lost on a reinstall), **never a lost one**.

**Per event, in order:**
1. reject if no chat or no time, a ms-shaped time, an unknown kind, or text on a `reply_marker`;
2. drop if the chat is not on the VM's share list (counted, nothing stored);
3. `reply_marker` → the marker store only (§ 2.6), never `ingest()`;
4. `message` → screen (V2); a hit → a held-back flag, nothing else; otherwise → facts (V3) →
   `ingest()`;
5. `update` → screen again, then `revise()` on the envelope for that key. If the key was never
   seen, it is treated as a `message`.

The text is held in memory for the length of the request and **never written anywhere.**

`GET /device/whatsapp/cursor` → `{"cursor": <int seconds | null>}`, per user, in
`intake/whatsapp_state.json`. It is moved forward by a `cursor` on an events post, and only after
that post's events are recorded.

`action_needed` is true when any accepted event became `action_required`. P6 (Phase 3) reads it.

### 2.3 V2 screen and V3 facts — `tools/intake_whatsapp.py`

**Config, not code:** the word and pattern lists and the type markers live in
`config/templates/whatsapp_screen.yaml` (Amber). Their categories: sexual, violence/weapons,
self-harm, drugs, slurs/harassment.

**Matching:**
- case-folded, on word boundaries;
- after a light de-obfuscation pass: `0→o 1→i 3→e 4→a 5→s @→a $→s`, runs of 3+ letters squeezed to
  2, and separators (`. - _ *`) between single letters removed;
- **tuned to over-flag** (plan V2).

**A hit is a flag:** `{envelope_id, chat, sender, time, category}` appended to
`intake/whatsapp_flags.jsonl`, with **no text**. Nothing reaches extraction, intake, a record or a
model. Phase 3's card reads these.

**Facts (V3), code only:**
- `type`: `question` (a `?`, or an interrogative opener); `proposal` (a date or time found plus a
  proposal marker: "shall we", "how about", "let's", "are you free", "want to"); `request` ("can
  you", "could you", "please", an imperative opener from the list); otherwise `info`.
- `when`: `dateparser.search.search_dates`, relative to the message's own time, preferring
  future dates. The first hit is normalised to ISO; none → no event time.
- `spans` (W7): at most two, ≤ 40 characters each — a capitalised run after "at"/"@"/"in", and the
  matched event noun ("dinner", "drinks", "call"). **They are sender-controlled substrings:**
  checked by `contains_injection_markers`, and a span carrying a marker is dropped, not kept.
- `who`: the share list's `senders[sender]` for a group sender, or the chat's `label` for a
  one-to-one chat. An unknown sender is "a member of <group label>". It is never the WhatsApp
  display name.
- **The fact string is the record's `subject`**, e.g.
  `question · from Anna · "dinner" · 2026-11-28 19:00`. It is never a sentence of theirs.
- `awaiting_reply`: `question`/`proposal`/`request` in a one-to-one chat.

**`classify` (`tools/intake.py:539`) gains a WhatsApp branch.** It sits after user rules (a rule
the user taught still wins) and **before the ledger, which WhatsApp never reads or teaches:**
- **one-to-one** `question`/`proposal`/`request` → `action_required`, which surfaces to logistics;
- **in a group, only a `proposal` carrying a date or time** → `action_required`. A group question
  or request → `info`. W8 already turns the awaiting-reply backstop off for groups as noise, and a
  `?` from any member would otherwise surface, and lift the declined-action guard (§ 2.8), at
  chat frequency (verify 3);
- `info` → `correspondence`, disposition `silent`, **domain `None`** (record only: no queue,
  so it never reaches the Relationships specialist's context) (§ 5, decision B).

**`build_digest` (`tools/intake.py:1297`) skips `channel == "whatsapp"` rows entirely (review
2).** Silent `info` facts are never listed. An `action_required` fact left unread for 7 days is
not escalated into the digest either: it keeps surfacing through `context_block` until logistics
reads its queue. So **a parked digest never holds WhatsApp text**, and the purge has nothing to
miss in `digest_state.json`.

The branch's source label is `"whatsapp"`, so `observe()` at `:1257` (which fires on `rule` and
`headers` only) never learns from it.

### 2.4 V4 — `ingest()`, `revise()`, and the lock

- **One lock, `_state_lock(persona)`** (`intake/.state.lock`, `fcntl.flock`), **re-entrant
  within a thread** through a thread-local depth count. `core/consent.py:_locked` is not
  re-entrant, so it is not copied (review 4).
- **`ingest(envelopes, persona) -> dict`**, under the lock:
  - it **re-reads** `seen` and `ledger`, and **prunes `seen` on that re-read**
    (`_prune_seen`, `seen_retention_days`). This is now the only prune, because the early load
    is no longer saved (verify new 2);
  - runs the per-envelope body (`:1203-1260`) **plus** the sibling marking (`:1266-1268`);
  - saves both.
- **`sweep()` fetches outside the lock and then calls `ingest()`.** Its own early `seen` load
  (`:1159`) is used only for the adapters' `skip` predicate. That is a read-only, stale-tolerant
  use: at worst an adapter downloads something already seen, and `ingest()` drops it.
- The events endpoint calls `ingest()` on a worker thread inside `persona_scope` (the
  `_task_call` pattern, `core/server.py:1883`).
- **`_append_record`, `revise()`, the purge, the expiry, and `teach_intake`'s ledger
  read-modify-write (`:1036-1042`) all take the same lock.**
- **`revise(envelope_id, new_subject, classification, persona)`** rewrites `records.jsonl` under
  the lock: it replaces the `whatsapp` row with that id and keeps its `seen_at`, so a fact already
  read by its domain does not re-surface by being edited. It also refreshes the index entry. Only
  `channel == "whatsapp"` rows are ever rewritten.
- **WhatsApp envelope:**
  - `channel="whatsapp"`, `native_id` = the key;
  - `received` = the message time;
  - `sender_address` = the **chat id** in a one-to-one chat; in a group, the canonical sender
    id, or `""` when the live event had none (§ 2.5);
  - `sender_display` = the user's own name for them, or `""` (empty whenever `sender_address` is);
  - `subject` = the fact;
  - `body=""`, `thread_id=""`;
  - `signals={"whatsapp": {...}}`, which carries the fact's type.
- **The index:** `intake/whatsapp_index.jsonl`, keyed by envelope id:
  `{chat, kind, time, event_time, type, sender_known, awaiting_reply, resurfaced_at, task_ids}`.
  It is rewritten under the same lock.

### 2.5 V5 — one WhatsApp card per task

**`_PROPOSAL_SOURCES`** becomes `("correspondence", "location", "whatsapp")`. A `whatsapp`
proposal:
- is keyed `whatsapp:<task id>`, and **any** existing one on the task — pending, accepted or
  declined — blocks another. That gives one card per task, ever, and a decline ends WhatsApp
  proposals for that task;
- also stores the `envelope_id` of the message that raised it, so the card can show what arrived.

**`match_envelope(..., channel="")`:** for `whatsapp`, the **sender basis only.** The thread
basis is empty by construction, and the subject basis is skipped because the subject is our own
fact string.

**In Phase 1 `expect_from` is model-written free text ("Anna"), not an id (review 1).** Only
Phase 3's "Track this" writes a canonical id. So the WhatsApp sender basis is:
- `sender_address` is **the chat id for a one-to-one chat** (the chat *is* the sender) and the
  canonical sender id in a group;
- an `expect_from` containing `@` is an **exact** id match (`:3344`), for Phase 3's
  code-written ids;
- otherwise `expect_from` must match the **user's own name for that sender** (`sender_display`,
  taken from the share list's one-to-one `label` or group `senders` map, never a group subject or
  a WhatsApp display name) **as whole words, case-folded**. "Anna" matches "Anna Petrova", not
  "Joanna".
- `_sender_matches` is unchanged; this is a WhatsApp-only helper. Its substring test is the
  reason a single ever-allowed card could otherwise land on the wrong person.

A match parks a `whatsapp`-source proposal.

**Reply-marker basis:** an open one-off task whose `source_id` is a WhatsApp envelope of type
`question`/`request`/`proposal` gets a proposal when a reply marker arrives in that chat after the
task opened. Same key, so still one card ever.

**`_proposals_for_display`** (`core/server.py:1960`) treats `whatsapp` like `correspondence` for
the record join. The sender shown is `sender_display`, the user's own name.

**Test (T13):**
- the task is opened through `open_task(expect_from="Anna")` (the model's path), and the share
  list labels the chat "Anna Petrova";
- three messages from that sender → one card;
- after a decline → none;
- a message in a chat labelled "Joanna" → none.

### 2.6 V6 — the awaiting-reply backstop (inside `sweep()`)

**Reply markers** go to `intake/whatsapp_state.json → last_reply[chat] = time`. The reply itself
is never kept.

**`backstop(persona)`**, run from `sweep()` after the pull loop, marks a fact for re-surfacing
once when **all** of these hold:
- one-to-one chat, `awaiting_reply`, type `question` or `proposal` (W8: off for groups);
- received more than **24 h** ago (W8);
- still relevant: its `event_time` has not passed, or, with no event time, it was received under
  72 h ago;
- no reply marker in that chat timed after the fact;
- `resurfaced_at` not yet set.

**Delivery:** `context_block` gains one line, `[WhatsApp — still unanswered]`, with the fact
inside `wrap_untrusted`.
- It is offered to every context load within **30 minutes** of the first one that showed it (the
  digest's delivery-window pattern, `:841`), so Coordinator and Synth of one session both see it,
  and then never again.
- A reply marker that arrives first clears it.

**Step 0 sets the tolerance** (§ 5, decision A). Under its recommendation (a) the rule above is
built as written, with the stated tolerance (one possible redundant re-raise for a question
answered only by a type-90 event). Under (b) it is still built as written, with a second marker
source added in Phase 2.

### 2.7 V8 purge and V9 expiry

**`purge_chat(persona, chat)`** — the un-share path, run before the share-list reply is sent. For
the chat's envelope ids (from the index) it deletes:
- the `records.jsonl` rows (`channel == "whatsapp"` only);
- the `seen` entries;
- the index entries;
- the flags;
- `last_reply[chat]`;
- **pending** `whatsapp` proposals naming those envelopes. Answered ones stay: they record a tap
  the user made.

**`purge_channel(persona)`** does that for every chat, plus the share list and the cursor. It runs
from `sweep()` when **consent has been withdrawn** and a WhatsApp store still exists (decision C).
Switching the stanza off does **not** purge: it is how a revert is done.

**Expiry (W6/V9)**, from `sweep()`: facts over 90 days old are deleted the same way, **unless a
task carries the envelope** (`source_id`) or a proposal names it. The index is checked first, so
an hour with nothing to expire costs one small read, and no rewrite.

### 2.8 The declined-action guard (review 3)

`_newer_intake_row` (`tools/turn_context.py:109`) **skips `channel == "whatsapp"` rows unless
their category is `action_required`.**
- A chat fact that needs the user is a genuinely new event, so it still counts.
- An `info` fact arriving every few minutes is not, and would otherwise lift every decline.
- Email's behaviour is unchanged.

**T26:** after a decline, a WhatsApp `info` row arrives → `new_trigger_since` is false; an
`action_required` WhatsApp row → true.

**What none of this reaches**, as plan V8 states: conversations, the Diarist's journal and FAISS,
the daily log, and tasks the user opened.

---

## 3. Files and tiers

| File | Tier | Change |
|---|---|---|
| `core/auth.py` | Amber | device token: issue, decode, revoke, list |
| `core/server.py` | Amber | `require_auth` branch; `bound_persona` `device`; `/device/whatsapp/{events,cursor,share-list}`; `/whatsapp/device/{pair,revoke}`, `/whatsapp/devices`; `_proposals_for_display` branch |
| `core/consent.py` | Amber | `"whatsapp"` in `SCOPES` |
| `tools/intake.py` | Amber | `ingest()` split; lock; `revise()`; WhatsApp `classify` branch; `_PUSH_CHANNELS`; `sweep()` calls backstop, expiry, consent purge; `context_block` line; `build_digest` skips WhatsApp; `_empty_queue`'s no-domain count skips WhatsApp; `teach_intake` ledger write locked |
| `tools/intake_whatsapp.py` | Amber, new | screen, facts, index, markers, flags, backstop, purge, expiry, share list, cursor |
| `tools/obligations.py` | Amber | `whatsapp` proposal source; `match_envelope(channel)`; whole-word name basis; reply-marker basis |
| `tools/turn_context.py` | Amber | `_newer_intake_row` skips non-action WhatsApp rows (§ 2.8) |
| `config/templates/intake.yaml` | Amber | `channels.whatsapp: false` plus a comment naming the consent gate |
| `config/templates/whatsapp_screen.yaml` | Amber, new | lists and markers |
| `requirements.txt` | Amber | `dateparser` |
| `tests/test_intake_whatsapp.py` | Green, new | § 4 |
| `core/scheduler.py`, `config/agents/*.md`, `config/personas/mike/**` | Red / Denied | **not touched** |

---

## 4. Tests — `tests/test_intake_whatsapp.py` (the `test_intake_pipeline.py` pattern)

Standalone runner, temporary persona directory, no network, no model. The FastAPI app is driven
through `TestClient`, with `METATRON_AUTH_PASSWORD` set in-test.

| # | Test | Proves |
|---|---|---|
| T1 | `device_token_refused_off_device_paths` | a `d1.` token → 401 on `/tasks/today` |
| T2 | `session_and_service_tokens_refused_on_device_paths` | user and service v2 tokens → 401 on `/device/whatsapp/events` |
| T3 | `user_comes_from_token_not_body` | a body carrying `persona: "other"` writes only under the token's persona |
| T4 | `revoked_and_stale_device_tokens_refused` | revoke → 401; `last_used` 31 days old → 401; password rotated → 401 |
| T5 | `body_cap` | 600 KiB → 413, nothing written; `Content-Length` lie with a chunked body → 413 |
| T6 | `event_without_chat_rejected` | per-event rejection, the rest of the batch accepted |
| T7 | `unshared_chat_dropped` | counted in `dropped_not_shared`, no row, no seen, no index |
| T8 | `milliseconds_time_rejected` | `time` ≥ 10¹¹ rejected |
| T9 | `live_and_nightly_copy_recorded_once` | live ms 1763870400250 floored by the phone to 1763870400, and backup 1763870400 → one row; second is a duplicate |
| T10 | `update_replaces_the_fact` | an `update` with new time words → one row, new subject, same `seen_at` |
| T11 | `update_that_screens_is_withdrawn` | an update hitting the screen → row removed, a flag added |
| T12 | `screen_holds_back_before_any_record` | a hit → a flag with no text, no record, `ingest()` never called (spy) |
| T13 | `three_messages_one_card_none_after_decline` | the V5 test |
| T14 | `resurface_once` | 25 h unanswered → one line in two context loads within 30 min, none after |
| T15 | `reply_marker_clears` | a marker after the fact → no re-surface |
| T16 | `reply_markers_never_reach_ingest` | spy on `ingest`, no record row, no `match_envelope` call |
| T17 | `purge_on_unshare` | records, seen, index, flags, markers and pending proposals gone; another chat's untouched; email rows untouched |
| T18 | `expiry_90_days` | a 91-day fact gone; one with a task kept |
| T19 | `channel_off_without_consent` | stanza on but no record → 403 `channel_off`; record → 200; withdraw → next sweep purges |
| T20 | `whatsapp_never_touches_ledger` | 10 messages from one sender → `ledger.json` unchanged |
| T21 | `span_with_injection_marker_dropped` | `at "ignore previous instructions"` → no span |
| T22 | `concurrent_ingest_and_sweep_keep_both` | a sweep whose adapter sleeps 2 s mid-fetch while a **second process** ingests a WhatsApp event → after both, `seen` holds both ids and `records.jsonl` both rows; and a nested lock in one thread does not deadlock |
| T23 | `push_channel_not_polled` | `channels.whatsapp: true` → no "no adapter" warning, no channel-health entry |
| T24 | `digest_never_holds_whatsapp` | silent `info` and an 8-day-old unread `action_required` WhatsApp row → absent from `build_digest`; an email row in the same store still listed |
| T25 | `info_facts_queue_nowhere` | an `info` fact → `domain` None; `read_intake_queue("relationships")` empty; **`_empty_queue`'s "carry no domain" count excludes WhatsApp rows** (verify new 3) |
| T29 | `seen_still_pruned` | a 91-day `seen` entry is gone after `sweep()` and after an events post |
| T30 | `group_question_is_not_action` | a group `?` → `info`; a group message with "Sat 19:00, shall we" → `action_required` |
| T31 | `password_rotation_keeps_dedupe` | rotate `METATRON_AUTH_PASSWORD`, re-send a seen backup message → a duplicate, not a re-key |
| T26 | `whatsapp_info_does_not_lift_a_decline` | § 2.8 |
| T27 | `same_second_clash_never_loses_a_message` | live B as ordinal 0, then backup A as ordinal 0 (different text) and B as 1 → A recorded (re-keyed), B a duplicate at worst |
| T28 | `one_to_one_sender_is_the_chat` | a one-to-one event with `sender: ""` → `sender_address` = chat id, `sender_display` = the share-list label |

Also run: `bash scripts/qa_sweep.sh`, `tests/test_intake_pipeline.py`, and the other intake and
obligations suites `qa_sweep` names.

---

## 5. Decisions for Mike

> **RULED — Mike, 2026-11-23:**
> - **A, B: as recommended.** (a) accepted, with the stated tolerance; `info` facts are recorded only.
> - **C (amended):** withdrawing WhatsApp consent **stops collection only**. Deleting the stored
>   facts is a **separate opt-in** by the user — `POST /whatsapp/delete-all` (session token) in
>   Phase 1, with its button among Phase 3's cards. Otherwise facts expire at 90 days. Un-sharing
>   a chat still deletes that chat at once (W3, unchanged).
> - **D (amended):** *"It should be able to intake other languages and translate them."* Put to
>   him as three options (local translation model on the VM / per-language word lists / cloud
>   translation, the last refused by ruling 3); he chose **a small translation model on the VM,
>   Bulgarian only for now**, after asking its costs (*"Proceed as rec"*):
>   - an OPUS-MT Bulgarian→English model (`Helsinki-NLP/opus-mt-bg-en`), converted to CTranslate2 int8 (about 80 MB),
>     run in the server process;
>   - loaded only when a Bulgarian message arrives, unloaded after 10 idle minutes;
>   - about 150–250 MB RAM while loaded, against 2.9 GB available measured 11-23 12:3x;
>   - $0 a month;
>   - the text never leaves the VM and is never stored; the English output goes through the
>     same screen and code extraction; dates are read from the original by `dateparser`;
>   - any other non-English message is held back as `unscreened` until it has a model.
>
>   **This amends the 11-22 LM ruling** ("no local model; V2/V3 stay code on the VM") deliberately:
>   that ruling was about extraction judgement, and this model only translates — extraction stays
>   code. **Owed at build:** the peak with speech-to-text and the embedder loaded at once, and the
>   licence read from the downloaded model card. **Owed to M2:** Bulgarian messages in the labelled
>   sample. **Owed to § 8a:** the model's licence and notice shipped with any distribution beyond
>   Mike and Iva.
>
>   **Measured at build, 11-23.**
>   - **Licence: Apache-2.0**, read from the downloaded model card. **CC-BY, as told to Mike, was
>     wrong** — it was quoted from memory. Apache-2.0 is more permissive; it still requires the
>     licence and notice with a distribution.
>   - **Memory:** 82 MB on disk. On the Mac the model's own cost is **+159 MB resident** (the
>     `ctranslate2` library itself is about 205–250 MB more), load 0.3 s, 0.1 s a message.
>     **On the VM the server already maps `ctranslate2`** (12 maps, from speech-to-text), so only
>     the model's own cost is new there.
>   - **Unload:** freed memory is not returned to the OS by default, so the unload calls glibc's
>     `malloc_trim` (Linux; no effect on the Mac, where 366 of 396 MB stayed).
>   - **Owed at M4:** `scripts/fetch_whatsapp_translation_model.py` then `--check` on the VM,
>     which prints the model's own cost there and the memory after the idle unload.

**A — V6's tolerance. Step 0 counted it** (probe button 7, 11-23 12:07, both rotated sets; counts
only, `message_type` beside the whole backup's rows/with-text for that type).

**What the increments leave out is one kind of message, and only that kind of the user's own.**
- **Every one of the 26 omitted from-me messages is `message_type` 90, and every one is in a
  one-to-one chat** (20 + 6, across 7 + 4 chats). Not-from-me omissions are 90 (23) and 1 (6).
- In the whole newest backup, type 90 is 3,362 rows, **0 with text**.
- The increments **did** carry 27 other type-90 messages, so the kind is not always left out.
- **Every kind a written or media reply could take reached the increments:** 0 (705, always with
  text), 1 (75; 1,358 of its 4,632 backup rows have text), 2, 3, 7, 15, 92, 99, 118.
- So a written reply, a photo or a voice note is a reply marker by the next night. Only type 90
  can lag up to about 6 days.
- **What type 90 is, the counts do not say.** It is always textless, both directions, almost all
  one-to-one, and about 6.5% of all messages. The increments also carry a `call_log` table delta
  (plan § 4, 11-23), so 90 may be how a call shows in the message table. **That is an inference
  from shape, unconfirmed.** Mike can settle it: did he have WhatsApp calls with about seven
  people between 11-11 and 11-16?

**Options:**
- **(a) Accept, as built — recommended.** V6 treats any from-me message as a reply marker, as
  planned. The stated tolerance: **a question answered only by a type-90 event, and not by any
  written or media reply, may be re-raised once**, up to the next full backup. W8 already limits
  a re-raise to once, so the cost is at most one redundant reminder per such question.
- **(b) Also read markers from the increments' `call_log` delta** (Phase 2, phone side). That
  needs one counts-first clean-room probe to map its fields, about 0.3M tokens and one tap. Do it
  only if Phase 4 shows (a)'s redundant re-raises. Not chosen now, because nothing yet shows the
  cost is real.
- *(c) Hold V6 until the full backup confirms* — rejected: a 6-day wait defeats a 24-hour
  backstop.

Under (a), § 2.6 needs no tolerance parameter. The decision is the stated tolerance above.

**B — what an `info` fact does.** About 60 messages a day, most of them `info`.
- *Recommended:* **recorded only.** Silent, queued nowhere, and left out of the morning digest,
  which skips every WhatsApp row (§ 2.3). Only questions, proposals and requests ever surface.
  (Review 2: queueing them to relationships would have put about 60 a day into that
  specialist's context.)
- *Alternative:* the digest lists them too, as it does for silent email. That is about 50 lines
  of chat facts a day in the brief.

**C — what withdrawing WhatsApp consent does.**
- *Recommended:* it purges the whole WhatsApp store at the next hourly sweep. A withdrawal is
  un-sharing everything.
- *Alternative:* it only stops collection, and the facts expire at 90 days.

**D — messages the screen cannot read.** The lists are English, and Mike's chats include
Bulgarian. A Cyrillic message passes an English screen unexamined, and its spans could carry
words the screen would have held back.
- *Recommended:* a message more than half in a script the lists don't cover is **held back as
  `unscreened`**, a flag with no text, in keeping with "tuned to over-flag". M2 will show how
  many that is.
- *Alternative:* extract from it anyway. Spans ≤ 40 characters bound the exposure, and no text
  goes in.

---

## 6. Todo list (build order; nothing starts before Mike's go-ahead)

0. **Done 11-23: step 0.** The omitted messages were counted (§ 5 A). **Item 7 is gated on
   Mike's decision A.**
1. `core/consent.py`: `whatsapp` scope. `config/templates/intake.yaml`: stanza off.
   `requirements.txt` + `.venv`: `dateparser`.
2. `core/auth.py` device token, plus registry → T1–T4.
3. `tools/intake.py`: re-entrant lock, `ingest()` split with the re-read and prune
   (`test_intake_pipeline.py` must pass unchanged), `_PUSH_CHANNELS`, `teach_intake` locked →
   T22, T23, T29.
4. `tools/intake_whatsapp.py` and `config/templates/whatsapp_screen.yaml`: screen, facts,
   fingerprint salt, index, `classify` branch (one-to-one vs group), `revise()`; `build_digest`
   and `_empty_queue` skip WhatsApp → T10–T12, T20, T21, T24, T25, T27, T28, T30, T31.
5. `core/server.py`: `/device/whatsapp/*` with gate, body cap and schema; pairing routes → T3,
   T5–T9, T16, T19.
6. `tools/obligations.py`: `whatsapp` source, `match_envelope(channel)`, whole-word name basis,
   reply-marker basis; display branch. `tools/turn_context.py` guard → T13, T26.
7. V6 backstop and context line → T14, T15. Not started until decision A is ruled.
8. V8 purge, V9 expiry, consent purge → T17–T19.
9. `qa_sweep.sh` and the intake/obligations suites; a review pass on the diff; Mike's review and
   commit.

---

## 7. Costs and risks

**Build:** about 3–4M Opus 5.5 tokens (smaller than the plan's 3–5M, because the per-user auth V1
needed is already built), plus about 0.3M for Fable's review of this delta.

**Run:** nothing while off. Once on, about $0.01–0.03 a day (plan § 6: no per-message model calls;
about 5–15 facts in head-layer context). The V6 line adds at most a few facts a week.

**Ancillary:**
- `dateparser` on the VM. `deploy.sh`'s pip step installs it, and it pulls `regex` and `tzlocal`
  (pure wheels).
- The hourly sweep gains one small index read.

**Persistent state:**

| What | Unit of standing cost | What deletes it | Meter |
|---|---|---|---|
| `whatsapp_index.jsonl` | about 200 B per fact, about 60 a day → about 1 MB at 90 days | expiry and purge, with its fact | none needed — bounded by the facts |
| `whatsapp_flags.jsonl` | about 150 B per flag | the purge; **expiry at 90 days too**, added here because the plan did not name it | none |
| `whatsapp_state.json` (share list, cursor, last reply per chat, fingerprint salt) | about 10 KB | the channel purge | none |
| `devices.json` | about 200 B per device | revocation; refused after 30 days unused, **but the entry stays** until revoked — a few hundred bytes | its own `last_used`; no existing meter reports one |
| `.state.lock` | an empty file | none needed | — |

**Risks:**
1. **Two messages in one chat in the same second.** The two paths could assign different
   ordinals. Without the fingerprint (§ 2.2) that would **lose** a message, as review 5 showed;
   with it, it is at worst a duplicate fact. Phase 0 probe 3 counts how often it happens.
2. **The lock is advisory.** Any future writer of `seen.json` that skips it re-opens the race. A
   comment at both call sites says so.
3. **Code extraction quality is unmeasured until M2.** The channel stays off for alerts until then
   (plan § 4 Phase 1).
