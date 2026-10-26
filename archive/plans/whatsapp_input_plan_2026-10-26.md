# WhatsApp input — plan (2026-10-26)

*Status: **Fable review — 21 findings over six rounds; 20 verified closed, the last (N-L1, the
learned-ledger rule in V4) fixed and not re-verified**
(`archive/plans/adversarial_review_whatsapp_input_plan_2026-10-26.md`); written in Opus 5.5 after an
exploratory session with Mike. **Mike decided W1–W10 the same day (§ 5), with a pushback on W2
that changed the design to chat-level sharing; those changes went back to the same reviewer.
APPROVED by Mike 2026-10-26 ("Proceed with Stage 0"). Phase 0a done the same day —
`archive/plans/whatsapp_backup_format_2026-10-26.md` + `tests/fixtures/whatsapp_backup/`; the
roadmap pointer (§ 8a) written. Next: Phase 0b + probes, in a fresh session —
`archive/handoffs/2026-10-26-whatsapp-phase-0b-clean-room-and-probes-prompt.md`.** The local-model checkpoint is named **LM** (not C0, which is Track C's
Alpha-agreement item). Decisions marked W1–W10 are owed
before the phase that needs them (named on each). W-numbers are used so they do not collide with
the day planner's or the second-user plan's D-numbers.*

> **⛔ SEQUENCING: Phases 1–3 build AFTER the second-user build has landed**
> (`archive/plans/multi_user_accounts_plan_2026-10-26.md`, itself gated on day-planner Stage B).
> That build rewrites login, how a request's user is resolved, the server and the app — the same
> files this plan touches — and amends the privacy basis this plan rests on (§ 1, ruling 2).
> **Phase 0 (phone-only probes) may run before it.**

---

## 0. What this gives the user

1. **You choose, on your phone, which chats Metatron may see** — one-to-one chats and groups.
   Nobody is shared until you tick them. **A group is shared or not as a whole;** a person in a
   shared group is included only for what they say in that group (W2).
2. **When a message in a shared chat needs something from you** — a proposal with a time, a
   question waiting on your answer — Metatron raises it in your next conversation, and (W5) as a
   phone notification within about a minute.
3. **A message that looks objectionable never reaches any model.** You get a card saying who sent
   it and in which chat, and you read it in WhatsApp yourself.
4. **Metatron keeps facts, not words.** WhatsApp stays the only record of what was said.
5. **Un-sharing a chat stops collection at once and deletes Metatron's WhatsApp store for it**
   — facts, cards, reply markers. **What Metatron already raised in a conversation stays
   in that conversation's record, like anything else said there** (W3 states the choice).

**Need met:** fully on Android after Phase 3. **iPhone has no route** (§ 8.1). Replying on the
user's behalf — approval-gated first, then trusted — is designed for and deferred (§ 9).

---

## 1. Rulings on record (Mike, 2026-10-26)

| # | Ruling |
|---|---|
| 1 | **The source is the phone:** a notification listener (live) plus the nightly WhatsApp backup (history, and what the listener misses). WhatsApp Desktop's database on the Mac is a development convenience only — the Mac is not a generic user's device. |
| 2 | **"Two active users" = the Metatron user and any WhatsApp contact** — contacts are third parties exactly as email correspondents are. **The basis is the 08-28 ruling (`ROADMAP.md` § Section 0) as the second-user plan extends it (2026-10-26, § 2.2 / § 4.9 there):** it covers users who have given informed consent, not "single-user". **Enabled for `mike` first, and built per-user from the start for Iva** — her WhatsApp switches on once her informed consent explicitly covering WhatsApp is recorded (W10). |
| 3 | **No verbatim chat text in any prompt.** Code on the VM screens objectionable content — flagged to the user *before and instead of* any prompt — and extracts facts. Reason: Vertex keeps classifier-flagged prompts ≤90 days, and **Google does not otherwise hold WhatsApp content**, so the 2026-08-26 reasoning ("Google already has my calendar and email") does not extend to it. |
| 4 | **The tone profiler does not read WhatsApp** — reverses Mike's earlier request the same day. |
| 5 | **E1's "no integration before B2" is waived for WhatsApp**, as it was in practice for email. |
| 6 | **B1b gets a WhatsApp injection row** — required, not optional. |
| 7 | **End-to-end encrypted backup with the 64-digit key** — turned on by Mike 2026-10-26. Prerequisite for the nightly reader. |
| 8 | **TABLED: a local model** (Gemini Nano on the phone, a bundled Gemma, or a small model on the VM). Mike: *"raise it again before build time"* → checkpoint **LM**, § 4. |

---

## 2. Measured 2026-10-26

Mike decrypted his own `msgstore.db.crypt15` on the Mac with the 64-digit key (`wa-crypt-tools`)
and ran counts-only queries; no message text or number left his terminal, and the folder was
deleted afterwards.

- **50,316 messages, oldest 2017-10-23.** Whether phone changes left gaps is unmeasured.
- **Last 30 days: 1,844 (~60/day)** — 675 sent, 1,168 received, of which **~828 in groups (~71%)**
  and ~340 one-to-one. *Groups carry most of the traffic; under W2 each is shared as a whole.*
- **Identity:** 4,603 chat rows — 3,842 keyed by phone number, 629 by hidden ID (`lid`), 130
  groups. **827 of 828 recent group messages came from a hidden ID.** WhatsApp's own `jid_map`
  links **90 of 91** recent group senders and **582 of 629** hidden-ID chats to a phone number.
- **Decryption with the 64-digit key works.**
- **Not measured, owed to Phase 0:** how live notifications identify a sender (walkthrough step 4
  was deferred); whether a notification's message time matches the backup's for the same message
  (the dedup key, P2); history gaps; decrypted database size; on-phone decrypt time; the phone's
  model, Android version and on-device AI support (for LM).

---

## 3. Architecture

### Phone — the Metatron APK (all native code here is new)

**P1. Share list.** Built from the backup: chat list, `jid_map`, `lid_display_name`, group
subjects — plus Android contacts for names of phone-number IDs (`READ_CONTACTS`, new). **Its
entries are chats, not people (W2):** a one-to-one chat or a group, each shared or not as a whole.
Sharing a group includes every member's messages *in that group* and nothing of theirs elsewhere;
an individually shared person's messages in an unshared group stay out. Default per **W1**
(nobody), held as a setting so it can change later. Stored natively; only the IDs of shared chats
go to the VM.

**One ID per person and per chat.** WhatsApp gives the same person a phone-number ID in one-to-one
chats and a hidden ID in groups (§ 2: 827 of 828 recent group messages) — **and one-to-one chats
split the same way** (§ 2: 629 keyed by hidden ID, 582 of them linked to a number). Group IDs
(`@g.us`) do not split. So the phone **canonicalises every chat ID and every sender ID** through last
night's `jid_map` before the share list, the live feed, the backup reader or the VM sees it: a
hidden ID it links to a number becomes that number's ID; one it does not link stays a hidden ID,
named by its `lid_display_name`. A hidden ID that gains a link later is migrated on the phone and
the VM is told to merge the two. **A one-to-one chat arriving live under a hidden ID the map does
not yet link is held for the nightly backup**, which delivers it once mapped. **An unmappable sender
in a shared group is not dropped** — scope is the chat — and is attributed by its hidden ID.

**P2. Live feed.** A `NotificationListenerService` for `com.whatsapp`. Reads the messaging-style
notification; identifies the **chat by its WhatsApp ID** (the conversation shortcut — **Phase 0
confirms**) and drops anything whose chat is not on the list **on the phone**. **An event with no
chat ID is never sent** (the VM rejects one anyway, V1): a chat's display name can be set by others,
so matching on it could widen what is shared. If Phase 0 finds no chat ID in notifications, that is
a **stop**, not a fallback (§ 4). **Within a shared group, the sender** is the notification's person
key, canonicalised, if it carries one. **If it carries none, the live event goes without a sender:**
`sender_address` empty, the card reads "a member of <group>", nothing is sender-matched (V5), and
that night's backup copy arrives as an **update** supplying the canonical sender. **A display name —
which the sender sets — is never stored as a sender anywhere.**

**The phone is the de-duplicator.** Both paths see the same message — live at arrival, again in
that night's backup — and only the backup carries WhatsApp's own message key. So the phone builds
one **message key** from fields both paths share and that an edit cannot change: **canonical chat
ID + message time** (plus an ordinal if two share a timestamp). **No text and no sender go into the
key** — an edited message, a long one the notification trimmed, or a group message whose live
notification carried no sender would otherwise key differently on the two paths. Because the key is deterministic, the VM's `seen` set catches any
re-send, including a whole window re-sent after a reinstall.

The phone keeps, privately, a 72-hour list of keys it sent live, with each message's text length
and an edit flag. When the backup copy of one of those messages **differs** — edited, longer than
the trimmed notification, or now carrying a sender the live event lacked — the phone sends an
**update** for that key and the VM re-extracts and replaces the fact (V4). Otherwise the backup
copy is skipped. That key is the envelope's `native_id`. **Phase 0 confirms the notification's
message time matches the backup's** — if it does not, the phone pairs the two copies within a
±10-minute window in the same chat by text length, and keeps the live key.

**P3. Nightly backup reader.** WorkManager, charging and idle, after WhatsApp's nightly backup.
Needs All-files access to read `Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15`.
Decrypts in Java (written per **W9**) into the app's `no_backup` directory, extracts messages since
the last cursor for shared chats, deletes the decrypted copy before returning, and posts to the VM.
**The cursor lives on the VM** — the phone asks for it at the start of each run — so a reinstall
or cleared app data resumes where it left off rather than re-sending the whole W6 window.
An app-start sweep deletes any copy a crash left behind. **The user's own sent messages travel as
reply markers only — chat ID and time, no text** — the signal the listener cannot see, used by V6
and nothing else.

**P4. The key.** Entered in a native screen, never the WebView — the WebView's `localStorage` is
where the session token sits today (`static/index.html:986`). Stored wrapped by the Android
Keystore. **`AndroidManifest.xml` has `allowBackup="true"`**, so this phase sets it false or
excludes the key file — otherwise Android's own auto-backup copies the key to Google Drive.

**P5. Native HTTP and a device token.** Java makes no HTTP calls today, and the server URL exists
only in JS (`static/index.html:964`). **The session token cannot be reused:** it lasts 30 days
(`core/auth.py:93`) and is minted only by a password login (`/auth/login`) — there is no refresh
route, so the listener would go dark every month until the app was opened and the password
re-entered. Instead: a **scoped device token**, minted once by a signed-in call from the app,
handed to native code through the existing JS bridge (`MainActivity` exposes `"Metatron"`) and
stored Keystore-wrapped. It is accepted **only** on the `/device/*` endpoints (V1), carries the user it was
issued to (designed on the second-user build's per-user accounts), is revocable from the app, and
records when it was last used. A refused token raises a native notification ("WhatsApp link needs
re-pairing") — never a silent gap. HTTPS only — the network config currently permits cleartext.

**P6 (W5 — approved, "if we can manage it"). Local notification** posted by the listener when the
VM's reply says "action needed". Code-written text, never model-written; respects quiet hours.
Standard Android (`POST_NOTIFICATIONS` is already in the manifest); **the condition is Phase 0's
survival probe** — it works only as long as the listener stays alive in the background.

### VM

**V1. Endpoint `POST /device/whatsapp/events`** (`core/server.py`), with its siblings
`GET /device/whatsapp/cursor` and `POST /device/whatsapp/share-list`. Accepts only the device token
(P5). **Verified in the `require_auth` middleware (`:96-118`), not in the handler:** the middleware
gains a path-scoped second verifier — **`/device/*` paths accept only device tokens, and device
tokens are refused on every other path.** The app's own WhatsApp endpoints (V7's cards and taps)
live under `/whatsapp/*` and use the ordinary session token, like everything else the WebView
calls. Neither prefix is ever added to `is_open_path` with a check inside the handler; that is the
per-endpoint pattern the middleware exists to prevent. **The user comes
from the token**, never from the request body — today any valid token can name any persona. **Body size capped before reading** — `/upload` reads the whole file first (`:1766`).
**Rejects any event without a chat ID**, and drops any chat not on the VM's copy of the share
list: a real second check behind the phone's, because every event carries a chat ID to check.

**V2. The objectionable screen** — code, new `tools/intake_whatsapp.py`. Word and pattern lists by
category (sexual, violence/weapons, self-harm, drugs, slurs/harassment), **tuned to over-flag**,
because Google's classifier cannot be seen and ours must be stricter. A hit becomes a held-back
flag — who, which chat, when, category, **no text** — and nothing reaches extraction or any model.
*No input-side screen exists anywhere today; `filter_output` is output-only
(`core/orchestrator.py:2100`).*

**V3. Fact extraction** — code, same file. Schema: sender (**the user's own contact name** for a
canonical sender; **"a member of <group>"** when the live event had none — never the WhatsApp
display name, which the sender sets), chat, type ∈ {proposal, question, request, info},
normalised date/time (`dateparser`, a new dependency), short named spans per **W7**, and an
awaiting-reply flag. No sentences.

**V4. Into intake, immediately.** Intake is pull-only today: `sweep()` (`tools/intake.py:1096`) is
the only path that classifies and records, run hourly by `intake_sweep`. Split its per-envelope
body (`:1153-1210`) into `ingest(envelopes)`, which the endpoint calls directly and `sweep()` keeps
calling. Envelope: `channel="whatsapp"`; `native_id` = the phone's message key (P2), identical on
both paths, so `seen` catches the nightly copy of a live message; an **update** event (P2) replaces
the stored fact for that envelope instead of adding one (a small `revise()` alongside `ingest()`);
`sender_address` = the sender's **canonical** WhatsApp ID, or **empty** when the live event had none
— and `sender_display` empty with it, so nothing is sender-matched; **`thread_id` =
empty** — a WhatsApp chat is one conversation for life, so treating it as a thread would propose
closing every task from that chat on every later message; `subject` = the fact — rows keep
`subject`, never `body` (`_record_row`, `:625`).

**A WhatsApp index beside intake's records.** The envelope has no chat field, `thread_id` must stay
empty, and `_record_row` (`:625-654`) persists nothing from `signals` — so chat, event time and
re-surface state have nowhere to live in intake's rows. `tools/intake_whatsapp.py` keeps its own
`intake/whatsapp_index.jsonl`, **keyed by envelope id**: canonical chat, the fact's event time (V3),
type, whether the sender is known, and whether V6 has re-surfaced it. V6, V7 and V8 join through
it; intake's own schema is untouched. **Reply markers (P3) never
enter `ingest()`**: they are not classified, not recorded as intake rows, not passed to
`match_envelope` — they go only to V6. **Classification needs a new
signal branch in `classify` (`:539`)**: code alone never yields `action_required` today
(`_header_lookup`, `:457`, returns only promotion or notification). **WhatsApp never touches the
learned sender ledger:** the branch reports its own source label (`"whatsapp"`), not `"rule"` or
`"headers"`, so `observe()` (`:350`, fired from `sweep` `:1205`) never learns from it, and `classify`
skips `_ledger_lookup` (`:327`) for the WhatsApp channel. Each message is classified on its own
facts — otherwise every sender-less group fact would pool under one `chan:whatsapp` key, and a
chatty friend's usual category would override their occasional request. *(The same reason Mike
gave for the settled intake ruling: a sender is not a category.)* Facts still pass
`wrap_untrusted` and `contains_injection_markers` (`tools/untrusted.py:66`, `:82`) — **an
extracted place name is a sender-controlled substring.**

**V5. The route to Synth — unchanged code.** `context_block` (`tools/intake.py:844`), called from
`load_recent_context` (`core/orchestrator.py:1267`), already surfaces `action_required` rows,
wrapped, to Coordinator and Synth. Synth raises it.

**Tasks: what this plan does and does not promise.** `open_task` (`tools/obligations.py:1117`) has
no consent gate — the only gate is on *closing* a task — and **this plan does not add one**: a gate
keyed on a model-supplied, optional `source_id` is bypassed by leaving it out, and a "user turn"
check passes on any turn the user spoke in. So **Synth can open a task about a WhatsApp fact, as it
can about an email today.** What the plan adds is the normal way in: a **"Track this" button on the
WhatsApp item card** (V7), a code path where the user's tap creates the task with `source_id` and
`expect_from` set by code, never by a model.

**Closing proposals, one card per task.** For a `waiting` task tracked from WhatsApp, `expect_from`
is the sender's canonical ID; it contains `@`, so `_sender_matches` (`:2365`) takes its
**exact-address branch** (`:2371`), not the display-name substring test. For a "reply to X" task,
the evidence is the user's own **reply marker** in that chat after the task opened (V6). Today
`add_proposal` (`:2230`) de-duplicates per *message*, so every later message from that sender would
park another card, and a decline would not stop the next. **Change (`tools/obligations.py`):** a
`"whatsapp"` proposal source — added to `_PROPOSAL_SOURCES` (`:2226`), or `add_proposal` coerces it
back to `"correspondence"` — keyed per task the way the `"location"` source already is (`key`,
`:2236`) — **one card per task, ever**; declining it ends WhatsApp proposals for that task.
`match_envelope` (`:2379`) gains the channel so it can pick that source. **Phase 1 test:** three
messages from that sender produce one card, and none after a decline.

**V6. Awaiting-reply backstop**, inside `sweep()` — already hourly, so **no edit to the Red
`core/scheduler.py`**. A question or proposal in a shared one-to-one chat, unanswered past **W8**
(24 h), re-surfaces **once, and only while still relevant** (Mike, W8): its event time **from the
WhatsApp index** has not passed (a fact with no event time counts as relevant for 72 hours), no
reply marker has arrived in that chat since, and the index's re-surfaced flag is not yet set.
**A reply marker (P3) in the same chat, timed after the fact, clears it.** Markers arrive with the
nightly backup, so a fact the user already answered can re-surface for up to a day; the VM keeps
only "last reply in this chat at", never the reply.

**V7. WhatsApp cards** — code-written, never model-written. Two kinds: a **held-back flag** (V2 —
who, which chat, "open WhatsApp to read it") and an **action item** (the fact, with **Track this**
and **Dismiss**). **Not confirmation cards:** their text is fed back to the model
(`core/server.py:1334-1338`). Built in the shape of task proposals (`GET /tasks/proposals`,
`_proposals_for_display` `:1430`): a parallel `GET /whatsapp/cards`, shown on the same 30-second
poll as `refreshProposal` (`static/index.html:~3985`); a tap posts to `POST /whatsapp/cards/act`, a
user-act endpoint the way `/tasks/act` is. Both take the **session token** (V1 keeps device tokens
on `/device/*` only). `_proposals_for_display` also gains a branch for V5's per-task `"whatsapp"`
proposals, which carry a `key`, not an `envelope_id` (`core/server.py:1450`).

**V8. Purge (W3).** Un-sharing a chat selects that chat's envelope ids **from the WhatsApp index**
and deletes their rows — records, seen, cards — plus the chat's reply markers and index entries,
scoped to `channel="whatsapp"`. This is an explicit exception to intake's "nothing is
deleted" (`tools/intake.py:69`). **What it does not reach, stated so the promise in § 0 matches
it:** once Synth has raised a fact, the conversation record (`core/server.py` `_save_exchange`),
the Diarist's journal and its FAISS entry (`tools/diarist.py:98` → `core/memory.py`, no delete
path), the daily log (`tools/logger.py:382`) and any task the user opened from it all hold
whatever was said in that conversation. WhatsApp facts are never written to FAISS directly.

**V9. Retention (W6).** Facts expire after 90 days unless attached to a task.

---

## 4. Phases

**Phase 0a — Format description (clean room, session 1; W9).** A session that **may** read the
`wa-crypt-tools` source (GPLv3+), installed in a scratch directory outside the repo and removed
afterwards. It writes `archive/plans/whatsapp_backup_format_{date}.md` — **facts only: no code, no
copied comments, no identifiers beyond the format's own field names** — and generates test vectors
by *running* the tool, never by copying from it. The description must cover, as a checklist the
implementation is later held to:
1. **Every variant the reference handles** — each format version and branch (crypt12/14/15, header
   fields and feature flags, compressed or not, a trailing checksum or not, key types, the
   multi-file and dated-copy names, the WhatsApp Business path) — each row marked **"we handle"**
   or **"we refuse, with this named error"** (e.g. crypt14 → "end-to-end backup is off";
   password-protected backup → "use the 64-digit key option").
2. **Integrity** — the authentication tag is checked, so a wrong key produces "key doesn't match",
   never garbage; any trailing checksum is verified; a file still being written (WhatsApp's own
   backup run) is detected and retried later, not half-read.
3. **Key input** — what a valid key is after stripping spaces and case, and how the decryption key
   is derived from it.
4. **Choosing the file** — the newest *complete* backup among `msgstore.db.crypt15` and its dated
   copies.
5. **Phone limits** — decrypt and decompress as a stream (never the whole file in memory); check
   free space before writing the decrypted copy.
6. **Unknown version** — fails loudly ("WhatsApp changed its backup format") and feeds the
   freshness check (§ 6, Unseen 2), never returns an empty result.
7. **Schema drift** — the tables and columns P1–P3 read (`message`, `chat`, `jid`, `jid_map`,
   `lid_display_name`, …), checked at runtime; a missing one refuses loudly.
8. **Test vectors** — one synthetic backup per "we handle" row, produced with the reference's own
   encryptor from a known small database and a known key, plus the expected decrypted result.

**Phase 0b — Implementation (clean room, session 2).** A **fresh** session given only the
description and the test vectors. Its prompt forbids reading, installing or fetching the
reference; before writing, it confirms the package is absent from the project's environment
(`pip show wa-crypt-tools` fails) and that no copy exists in the repo. **Coverage check:** every
row of the variants table has a passing test vector or a passing refusal test; acceptance is
Mike's real backup on his phone reproducing the 2026-10-26 Mac counts (§ 2). Session 1 may then
run the vectors against the result as a **black-box** check — behaviour, never code. Both
sessions' transcripts, the description and the prompts go to the project log as the clean-room
record (legal check L1, § 8a).

**Phase 0 — Probes.** A debug build; ~1 session + ~30 Mike-minutes (M1), after 0a/0b. The listener
probe is throwaway; **the decrypt module from 0b is not** — it becomes P3's core.
1. **Listener:** for each WhatsApp notification, report the shortcut-ID and person-key *format*
   (digits masked to `#`), whether messaging style is present, text length, and the message time —
   one-to-one and group.
2. **Backup:** the All-files grant works; the Java decrypt matches the Mac counts above; decrypt
   time; decrypted size; messages per year (history gaps).
3. **Dedup key:** for messages seen both live and in the next backup — **including one edited after
   sending and one long enough to be trimmed** — does the message time match, and does the
   edit/length difference show up? (Reports match/no-match counts only.)
4. **Survival:** the listener still delivers after 24 hours screen-off (OEM battery killers).
5. **For LM:** phone model, Android version, RAM and free storage, whether AICore (the system app
   that runs Gemini Nano) is present.

*Exit:* a **chat ID** in live notifications for one-to-one **and** group messages **that equals the
share list's key for that chat**; whether group notifications also carry a sender ID (if not, live
attribution is unverified until the backup — P2); on-phone decrypt works; the dedup key aligns (or its ±10-minute fallback does); timings acceptable. **If
notifications carry no chat ID, stop and bring it back to Mike** — the options then are a
live feed for one-to-one chats only, matched on his own address-book name (which a sender cannot
set), with groups waiting for the nightly backup; or no live feed at all (alerts a day late).
Neither is pre-accepted.

**LM — before Phase 1: Mike's ruling on the tabled local model**, with Phase 0's device facts in
hand. It decides whether V2/V3 stay as code on the VM or gain a local model (and if on the phone,
move there). **Put the standing settlement in front of him at the same time:** `SESSION.md` § Do
not re-open records that correspondence is read **as code, never a model judgement** (`[DB-0905-01]`,
the parked intake extractor). That was decided for email on price; a local model removes the price
and the third party, but adopting one for WhatsApp is still a departure from a settled ruling and
needs his explicit word, recorded with its reason. **If LM puts a model on the phone, Phase 2 grows
by ~2–4M tokens** (§ 6).

**Phase 1 — VM side** (~1–2 sessions; **after the second-user build has landed**). V1–V9; offline tests on synthetic messages in the
`tests/test_intake_pipeline.py` pattern (fake adapter, monkeypatched persona directory). **Then
measure the extractor on Mike's labelled sample (M2) before any alert goes live.**

**Phase 2 — Phone** (~2 sessions). P1–P5.

**Phase 3 — Alerts and security** (~1 session). P6 if W5; the WhatsApp cards (V7); **B1b WhatsApp rows** in
`tests/run_intake_redteam.py` — an injection inside a place name, inside a display name, and an
instruction-shaped message from a shared contact; quiet hours.

**Phase 4 — Watch a week of real use.** Alert precision; flags per day; misses against the
labelled set; listener and backup freshness.

---

## 5. Decisions

**Decided by Mike, 2026-10-26** (the table below keeps the options as they were put):

| # | Ruling |
|---|---|
| W1 | **Nobody shared by default** — for now; likely to change later, so the default is a setting, not hard-coded. |
| W2 | **Pushback, adopted: groups function as a whole.** A group is opted in or not; individuals in it are opted in only for their participation in that group. The share list's entries are chats (P1). |
| W3 | **(a)** — the WhatsApp store only; **no scrub from Metatron's history.** |
| W4 | **Text only now.** Video, voice messages, and photos/files to be added later (§ 9). |
| W5 | **Real-time notification, if it can be managed** — conditional on Phase 0's survival probe (P6). |
| W6 | **Yes** — 90 days. |
| W7 | **Yes** — short named spans. |
| W8 | **Yes, if still relevant** — re-surface once, only while its time has not passed and no reply since (V6). |
| W9 | **Clean room** (after a fuller explanation). Licence confirmed 2026-10-26 from the package metadata: `wa-crypt-tools` 0.1.0 is **GPLv3 or later**. Mike also directed: **research the gaps a clean-room version might have and cover them in ours** — Phase 0a's checklist and 0b's coverage check (§ 4) — **and add the legal checks for this and for WhatsApp** (§ 8a). |
| W10 | **Yes for `mike`; plan for Iva's use as well** — Mike expects her consent. Built per-user throughout; her channel switches on once her consent explicitly covering WhatsApp is recorded and legal checks L1–L3 are done (§ 8a). **Her phone is Android** (Mike, 2026-10-26), so the design covers her. |

**Options as originally put:**

| # | Question | Recommendation | Needed by |
|---|---|---|---|
| W1 | Default: **allowlist** (nobody until ticked) or **all-except** | **Allowlist** — adding later costs nothing; removing after ingest means a purge | Phase 2 |
| W2 | **Groups** | Each group is its own entry; an excluded person's messages are dropped even inside an allowed group | Phase 1 |
| W3 | **What un-sharing deletes**: (a) the WhatsApp store only — facts, cards, reply markers — and say plainly that what already came up in a conversation stays there; or (b) also hunt that person's facts out of conversation records, journals, logs, tasks and memory | **(a).** "Nothing is deleted" governs merges, not withdrawn consent, so (a) is a hard delete of what the channel owns. (b) means editing five stores, one of which (FAISS memory) has no delete path and would need rebuilding — a large build for a promise the rest of the product does not make about anything else said in a conversation | Phase 1 |
| W4 | **Media** | **Text only.** Videos are separate files on the phone, not in the backup | Phase 2 |
| W5 | **Real-time delivery**: a local Android notification from the listener, or wait until the app is opened | **Local notification.** The only real-time route — the APK has no push and nothing reaches a closed app. A narrow first instance of the native notifications already recommended as the day planner's Stage C | Phase 3 |
| W6 | **History**: how far back to load facts | **90 days**; older history only as per-person last-contact dates | Phase 1 |
| W7 | **Named spans**: may a fact carry a short place/event name (≤40 chars)? | **Yes**, never a sentence — without it "dinner Sat 19:00" loses where | Phase 1 |
| W8 | **Awaiting-reply window** | **24 h for one-to-one; off for groups** (noise) | Phase 1 |
| W9 | **How the Java decrypt gets written.** The only readable description of crypt15 here is the source of `wa-crypt-tools`, which is GPL-3.0 *(verify)*, and web access is denied. (a) **Clean room:** one session reads that source and writes a short format description — facts only, no code; a different session writes the Java from the description alone. (b) Port it and accept GPL-3.0 for the app. (c) Lift web access once to read a public write-up | **(a).** The APK is about to be installed by a second person (Iva) — handing it to her is distribution, which is when GPL obligations attach, so (b) costs something now. (a) costs one short extra session | Phase 0 |
| W10 | **WhatsApp for any user other than `mike`** | **Not in this build.** The channel stays off by default (`config/templates/intake.yaml`); turning it on for another user needs Mike's ruling and that user's informed consent, as the second-user plan's D9 does for her mail | Phase 1 |

---

## 6. Costs

**Build.** Phase 0a (format description) ~0.5–1M Opus 5.5 tokens on the subscription; Phase 0b
(clean-room decrypt + coverage) ~1–2M; Phase 0 probes ~1M; Phase 1 ~3–5M; Phase 2 ~4–7M (native Android, the heaviest; **+2–4M if LM puts a
model on the phone**); Phase 3 ~1–2M; Fable 5.1 plan and diff reviews ~1.5–2.5M together.
**Mike-minutes ~3 h total** across the probe, labelling, permissions and share list, deploys and
APK sideloads.

**Run.** **No per-message model calls** — screening and extraction are code. Facts surface in
Coordinator and Synth context: ~5–15 rows × ~40 tokens ≈ 200–600 input tokens per agent per turn;
at 3.8 Flash's introductory $0.75/M input (`config/modules/spend_guard.yaml`) and ~30 turns a day,
**~$0.01–0.03/day (~$0.30–0.90/month), doubling when the introductory price ends.** VM processor:
pattern matching and date parsing on ~60 messages a day — negligible. Phone: one decrypt a night,
while charging.

**Ancillary.** `dateparser` on the VM; a transient decrypted database on the phone (size
unmeasured — Phase 0); one more 30-second poll.

**Unseen — no existing meter reports these:**
1. **The listener stops** (battery optimisation, a revoked permission) — a silent gap. Mitigation:
   "last live event" and "last backup processed" timestamps, surfaced when stale.
2. **WhatsApp changes its format** (a crypt16, a schema change) — the backup reader must fail
   loudly, never quietly return nothing.
3. **Google's flag-and-keep still applies to facts that reach Synth** — reduced, not zero.
4. **The key on the phone opens every chat** — an app compromise exposes all of them.

**Things that persist between runs** — unit, what deletes it, which meter:
- **Decrypted database copy:** deleted at the end of each run; a crash leaves it → the app-start
  sweep. Meter: none, hence the freshness check.
- **Facts on the VM:** 90-day expiry; purge on un-share. Storage trivial.
- **The WhatsApp index (V4):** one small row per fact; expires and purges with the fact it
  indexes, so it can never outlive the rows it points to. Meter: none needed — bounded by the facts.
- **Share list:** on both sides; an un-share deletes the VM copy's entry and triggers V8.
- **Device token (P5):** long-lived by design — that is what stops the monthly blackout. The cost
  of a longer life is risk, not money: a stolen phone keeps posting until revoked. Deleted by
  revoking it in the app, or by the developer; uninstalling the app abandons it, so the VM also
  expires any token unused for 30 days. Meter: its own last-used time.
- **The 72-hour sent-key list (P2):** on the phone, pruned as it ages; keys, text lengths and edit
  flags — no text. Lost on reinstall, which costs only missed edit-updates for that window: the
  VM's `seen` still blocks duplicates, because the key is deterministic.
- **The backup cursor (P3):** on the VM, per user; the phone reads it each run. Deleted with the
  channel's purge.

---

## 7. Steps only Mike can do — each run as a guided session

- **M1 — Phase 0 probe on the phone** (~30 min): sideload the debug build, grant Notification
  access and All-files access, enter the key, read the results.
- **M2 — Labelling** (~45 min): ~200 recent received messages, marked "needs action" yes/no in a
  local script on the Mac. Texts and labels never leave the Mac; scoring prints numbers only.
- **M3 — Share list, first pass** (~15 min).
- **M4 — Enable the `whatsapp` channel in `mike`'s intake config on the VM.** The VM owns live
  persona config, and `config/personas/mike/**` is Denied here.
- **M5 — Deploy and sideload** at the end of each phase.
- **M6 — WhatsApp's terms, read and recorded** (~20 min, before Iva — L3, § 8a): the current Terms
  of Service sections on reverse engineering, automated access and automated messaging. Web access
  is denied here, so Mike reads them himself, or lifts the block once for a session to quote them.
- **M7 — Iva's switch-on, a guided session with her** (~30 min, after L1–L3): Mike reads her the
  WhatsApp consent text (L2) and records it in `ROADMAP.md` § Section 0; she turns on end-to-end
  backup with the 64-digit key, grants the two permissions, pairs the device and picks her chats;
  Mike enables the `whatsapp` channel in her intake config on the VM (VM-owned, as M4 is for `mike`).

---

## 8. Risks and limits

1. **Android only.** iPhone has no notification listener and no readable backup on the device —
   only manual export through the share sheet.
2. **Undocumented formats.** crypt15 and the database schema can change with any WhatsApp update.
3. **Listener blind spots:** muted chats, a chat open on screen, the user's own replies — all filled
   by the next morning's backup.
4. **WhatsApp's terms.** Reading your own backup with your own key, and reading your own
   notifications, never contact WhatsApp's servers; no ban route identified. *(Verify the current
   wording — web access is denied on this project.)*
5. **Licence.** `wa-crypt-tools` is **GPLv3 or later** (confirmed from its package metadata,
   2026-10-26) and is the only readable description of the format here, so the Java is written as
   a clean room — W9, Phases 0a/0b. **What a clean room can miss** is the reference's knowledge of
   edge cases; 0a's variants checklist and 0b's coverage check exist to close exactly that gap.
6. **A friend's distress message** is caught by the screen and flagged to the user. **It is never
   routed to the clinical system**, which concerns the user's own wellbeing.
7. **Extraction quality.** Code misses indirect phrasing; the backstop (V6) and the measurement (M2)
   bound it.
8. **The privacy basis is per consenting user, and other people never consented.** The 08-28
   ruling as extended on 2026-10-26 covers users who have given informed consent; the people whose
   messages arrive are third parties, covered only because the user chose to share them — the same
   footing as email. It lapses for any user who has not consented (W10).

---

## 8a. Legal checks (Mike, 2026-10-26: "add the legal checks for this and WhatsApp")

*Not legal advice — a list of what must be checked, when, and by whom. The binding home for
anything commercial is Track C's legal brief (`archive/plans/phase5_to_future_roadmap_2026-06-10.md`
§ Track C, Phase 6B), whose "Relationship data — third parties without their consent" bullet this
feature falls squarely under.*

**Before WhatsApp is switched on for Iva** (W10) — personal use, but the app is now in a second
person's hands:

| # | Check | Owner |
|---|---|---|
| L1 | **Clean-room record complete** — 0a's description and transcript, 0b's prompt and its "reference absent" check, the coverage results — so the APK she installs carries no GPL-derived code | build sessions; logged |
| L2 | **Her informed consent explicitly covers WhatsApp:** her shared chats' content — other people's words — processed on the VM and, as facts, by Vertex under Google's default terms; Mike's full access; the 64-digit key held on her phone; how to un-share and what un-sharing does not erase (W3). Recorded in the second-user plan's `ROADMAP.md` § Section 0 amendment | Mike, with Iva |
| L3 | **WhatsApp's terms read** (M6) — reverse engineering, automated access — with the account-level risk to Mike's and Iva's WhatsApp accounts stated and accepted. *(Reading your own backup with your own key and reading your own notifications never contact WhatsApp's servers; that lowers detection risk, not the terms question.)* | Mike |

**Before any distribution beyond Mike and Iva** — for Track C's brief. **Where these live so a
Phase 6B session finds them:** Track C's only home is the static plan, which is never edited, and
`ROADMAP.md` does not carry Track C. So **on approval, the first build session adds one line to
`ROADMAP.md` § Not carried over** — *"Track C additions since the static plan: WhatsApp legal checks
L4–L8, `archive/plans/whatsapp_input_plan_2026-10-26.md` § 8a"* — the file a 6B session opens first.

| # | Check |
|---|---|
| L4 | **Third parties' data:** a product processes messages from people who never agreed to it. Personal use sits in household exemptions; an operator does not. Lawful basis, transparency, and deletion requests from people who are not users, under GDPR/UK GDPR, CCPA and equivalents. Also confirm the reading of on-device notifications is recipient-side processing, not interception, in the jurisdictions served |
| L5 | **WhatsApp/Meta:** whether a commercial product may decrypt users' backups or read their notifications under WhatsApp's terms and Meta's platform policies; use of the WhatsApp name in the product (trademark guidelines); and **the deferred reply features** (§ 9), which touch the terms' automated-messaging rules directly |
| L6 | **Licence:** counsel confirms the clean-room record is sufficient, and the app's own licence is chosen |
| L7 | **App-store policy**, if ever distributed through Google Play: notification-listener access and All-files access are restricted permissions that need a declaration and Google's approval. Sideloading is unaffected |
| L8 | **Vertex for third-party content at scale** — a data-processing agreement and the ZDR question, at the multi-user transition `ROADMAP.md` § Section 0 already names |

---

## 9. Deferred — designed for, not built here

- **Replying with approval:** WhatsApp opens with Metatron's draft filled in; the user taps Send.
  Works on iPhone too.
- **Replying by trust:** the notification's own Reply action, no tap. Android only, only while the
  notification is showing, and a grey area in WhatsApp's terms.
- **Media — to be added later (Mike, W4): video, voice messages, photos and files.** None of it is
  in the backup database — the files sit in the phone's WhatsApp media folders — so each is a
  separate feed. Voice messages and photos would also need the no-verbatim rule (ruling 3) worked
  out for them: a transcript is verbatim text.
- The local model (LM); WhatsApp as a tone source (ruling 4); iPhone; memory indexing.

---

## 10. Files, tiers and models

| File | Tier | Phase |
|---|---|---|
| `tools/intake_whatsapp.py` (new), `tools/intake.py` | Amber | 1 |
| `core/server.py` | Amber | 1, 3 |
| `core/auth.py` (the scoped device token — on top of the second-user build's per-user auth) | Amber | 1 |
| `tools/obligations.py` (a `"whatsapp"` proposal source keyed per task; `match_envelope` takes the channel; "Track this" sets `source_id`/`expect_from` in code) | Amber | 1 |
| `static/index.html` | Amber | 2, 3 |
| `android/**` (listener, backup worker, key screen, native HTTP, manifest) | Amber | 0, 2, 3 |
| `config/templates/intake.yaml` (channel stanza, **off by default**) | Amber | 1 |
| `requirements.txt` (`dateparser`) | Amber | 1 |
| `tests/test_intake_whatsapp.py` (new), `tests/run_intake_redteam.py` | Green | 1, 3 |
| `config/personas/mike/**` | **Denied** — Mike, on the VM (M4) | 1 |
| Iva's persona intake config | **VM-owned** — Mike, on the VM (M7) | after L1–L3 |
| `ROADMAP.md` — § Section 0 (Iva's WhatsApp consent record, M7) and § Not carried over (the Track C pointer, § 8a) | edited — the pointer on approval, the consent record at M7 | approval, M7 |
| `core/scheduler.py`, `config/agents/*.md` | **Red — not expected to be touched.** If Phase 4 shows Synth mishandling WhatsApp facts, one line in `synthesizer.md`, written in the main session, never delegated | 4 |

**Models:** plan in Opus 5.5 (this file); review in **Fable 5.1**; build each phase in **Opus 5.5**;
a Fable diff review for Phases 2 and 3 (key handling, the endpoint, the screen). Per
`docs/WORKFLOW.md` (Mike, 2026-09-24): independence of the reviewer, not capability.

---

## 11. Checked against recent work

The last eight commits touching these files were read for intent:
`27c570f` (task ledger) built `match_envelope`, which V5 relies on — **confirmed**.
`45739a2`/`1d824a9` (day plan, Today panel) added the 30-second poll V7 joins — **confirmed**.
**Killed by the check:** routing WhatsApp facts through day-planner event triage (`answer_event`,
`tools/day_plan.py:2450`, needs a calendar event and a user turn) and through the escalation inbox
(`tools/escalation.py`, clinical only, no UI). Nothing recent changes intake's adapter seam.

**Missed by the first draft, caught in review:** `archive/plans/multi_user_accounts_plan_2026-10-26.md`,
written and decided the same day (uncommitted at the time of this revision). It changes three
things this plan depends on — **login and how a request's user is resolved** (so V1 and P5 are
designed on it, and Phases 1–3 sequence after it); **the privacy basis** (extended to consenting
users — § 1 ruling 2, § 8.8); and **the app and server files** both plans touch.
