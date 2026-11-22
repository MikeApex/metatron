# The user's own logs — phase 2 build plan: noticing and promotion (2026-11-22)

Phase 2 of `archive/plans/custom_logs_and_places_plan_2026-11-21.md` (§ 5 item 2), from
`archive/handoffs/2026-11-22-data-objects-phase-2-build-prompt.md`. Opus 5.5 builds; Fable
reviews this plan before any code, then the diff before deploy.

**What a user gets.** When they keep mentioning a kind of thing no log holds, Metatron asks once —
*"Want me to start a list of the places you've mentioned wanting to try?"* — and a tap starts it
with what they already said filed in. A no is remembered. If it really belongs in a list they
have, saying so puts it there. Mike can see, across users, which logs people invent. A writer
that would file entries from ordinary conversation runs in shadow and writes nothing until a
labelled score clears it.

## 1. Mike's calls at the start of this build (2026-11-22)

1. **The matcher is a new code-only agent, `data_object_matcher`** — *"so long as this is
   essentially code with an agent gate to make the judgement."* Code counts, holds, raises,
   files and records; the model makes one judgement per candidate and nothing else (§ 3.2).
2. **The question reaches the user as a line in the logs block the Synthesizer already
   receives**, plus one conduct line in `synthesizer.md` (§ 3.3).
3. **The card's lifetime may change** — *"600 sec is arbitrary."*
4. Fix the parent plan's contradictions (§ 6); Fable checks this plan before building.

## 2. What the code check found (2026-11-22, against HEAD `0e5a064`)

1. **A card raised at detection would expire before it is asked.** `tools/confirm.py`
   `TTL_SECONDS = 600`. Detection runs after a reply; the question is on the next one, often
   hours later. And the app polls `/pending-confirmations` every 5 s, so a card raised at
   detection appears on screen, unexplained, before anything has asked the question.
   → **The offer is held at detection and the card is raised at the start of the next real
   user turn** (§ 3.3), with its own lifetime (§ 3.3, 2 h).
2. **The zone suggestion is never announced in a reply.** It is raised inside `POST /location`
   and shown by the app's poll alone. It is the precedent for *a card raised by code*, not for
   *an announcement*. → Mike's call 2.
3. **`confirm.request()`'s 24-hour re-proposal guard matches on the exact arguments** — every
   offer carries a new `offer_id` and the facts held so far, so it never fires. "Not offered
   again unless its count doubles" is this phase's own rule (§ 3.4), read from the declined
   ledger the parent plan names.
4. **Already true:** `KIND_HOMES` carries `write_data_object` for task, place and health
   (`9542e34`); `create_object(origin="noticed")` exists, unused; `write_data_object(action=
   "create")` refuses any bound caller; the Diarist adds to a log only with a live marker
   (`880027c`). Nothing in this phase writes through the Diarist.
5. **`mike`'s consent record holds `correspondence_read` and `tone_profile` only**
   (`scripts/accounts.py` seed line), not `base_configuration` — which a signed-up user's
   approval copies in (`core/accounts.py`). See § 3.7.

## 3. The design

**The rule this phase is built on (phase 1, three failed holds):** every write to a user's log is
made by code — an unbound caller — never by asking a model not to. The one model judgement
(the matcher) returns a choice; code acts on it.

### 3.1 The detector — code, no model (R34, R28)

- **Where it runs.** `tools/capture.py` `record_uncategorised()` already keeps every `other`
  fact (category, the extractor's one-line summary, timestamp) on real user turns only. After it
  writes, it calls `tools/noticed_logs.consider(persona, category)`. A daily catch-up,
  `noticed_logs.sweep(persona)`, runs inside the existing `capture_weekly_rollup` job (daily
  slot) for anything a restart interrupted. **No new scheduler job; `core/scheduler.py`
  untouched.**
- **The count.** Rows in `capture/uncategorised.jsonl` with that category inside
  `noticed_window_days` (30). At `noticed_raise_count` (3) the category is a candidate.
- **No candidate when:** the switch is off; the category is attached to an earlier offer
  (§ 3.2 `same_offer`) and that offer's own rule does not yet allow it; the category already finds a log
  (`data_objects.resolve(category)` — e.g. it became an alias); an offer for it is matching,
  held or open; it was declined and the held count is below twice the count at the decline
  (§ 3.4); its last offer expired unanswered and fewer than `noticed_raise_count` new facts have
  arrived since; or the matcher said no list (§ 3.2) and the count has not doubled since.
- **Then** the matcher runs on a daemon thread, inside `persona_scope` — never on the reply's
  path. Its result becomes a **held offer**.
- **The developer alert is unchanged** (5 in 30 days → Inbox, `raise_new_categories`).

### 3.2 The matcher — one agent judgement, code around it

`config/agents/data_object_matcher.md` (new, Red), bulk tier, bare dispatch, empty grant, an
entry in both routing files (Red; `local: true` in `routing.yaml`, fail-closed).

- **In:** the category; up to 3 of its held summaries (the extractor's own one-liners — needed to
  name the list well); the user's active, non-private logs and stores — id, name, aliases,
  one-line description; **and the user's earlier offers that were declined, expired or judged
  no list** — their name and `ask` line (review R6: every offer memory was keyed on the
  extractor's category label, which varies, so "place try" declined could return as "restaurant
  wishlist" and be asked as new). **Never an entry.** Privacy statement in its routing entry: Sensitive
  tier on the Vertex path, the same basis as `capture_extractor`.
- **Out — one JSON object, one of three judgements:**
  - `{"verdict": "match", "log": "<id>"}` — an existing log or store already fits;
  - `{"verdict": "new", "name": …, "description": …, "ask": …, "identity": "thing"|"occurrence"}`
    — `ask` completes *"Want me to start …?"* (e.g. "a list of the places you've mentioned
    wanting to try");
  - `{"verdict": "none"}` — not something a person keeps a list of;
  - `{"verdict": "same_offer", "offer": "<offer_id>"}` — the same thing as an earlier offer.
    Code attaches the category to that offer: no card, and that offer's rule (doubling after a
    no, three more after an expiry) now counts the facts of every category it carries.
- **Code validates everything:** `log` must be one of the ids it was given; name 1–40 chars,
  description ≤ 120, `ask` ≤ 90 and starting "a list" / "a log"; no `snake_case` identifier
  anywhere; identity one of two. **Anything invalid → no offer** (`matcher_failed`, counted),
  retried once by the next sweep. R15 — an object nobody wanted must not happen — is why a bad
  answer offers nothing rather than a code-built fallback.
- **A match on a registered store** (contacts, tasks, wisdom …) raises no card: the facts are
  the extractor's misclassification of an existing kind, not a list. Recorded `home_exists`
  and printed by the capture report, which is where a missing kind is read.

### 3.3 The card and the question (Mike's call 2)

- **Raised at the next real user turn**, by `_take_log_offer(persona, user_turn)` in
  `core/orchestrator.py` (both twins; **A8: stays in `core/orchestrator.py` beside
  `_unsaved_log_notes()`**). Called after the sign-off veto, so an offer is never spent on a
  turn the Synthesizer does not run; never on a nudge or a scheduled session; one offer per
  turn; none while another offer card is open.
- **Card**, `confirm.request(…, ttl_seconds=…)`:
  - new log: action `create_data_object`, args `{offer_id, name, description, identity}`;
  - match on an archive-store log: action `alias_data_object`, args `{offer_id, log}`.
  **The facts are not in the args** (review R1/R7): the executor reads the offer's held facts
  from `capture/uncategorised.jsonl` at tap time, every category the offer carries, so a mention
  made between the question and the tap is filed too. The `offer_id` in the fingerprint is what
  ties the tap to the offer.
  The description is an action, because `POST /confirm` echoes its first line as
  "✅ Done — …": *"Start a list: the places you've mentioned wanting to try (3 so far)"* /
  *"Keep the places you've mentioned wanting to try in your Restaurants list (3 so far)"*.
- **Its lifetime: 2 hours, and it never holds the slot against a real approval** (review R3).
  The app shows one card, the oldest (`static/index.html` `refreshPending`, `pending[0]`), and
  hides the task-suggestion bar while any card is shown. So `pending()` sorts offer cards
  **after** every other card — a send, merge or config card raised later still takes the footer
  — and the lifetime is `noticed_card_ttl_hours: 2` (capture.yaml): long enough to answer a
  question read a little late, short enough not to sit over task suggestions all day.
  `request()` gains an optional `ttl_seconds`; every other card keeps 600 s. *Cost: bytes per
  card in `pending_confirmations.json`; pruned on every read once expired; a restart keeps it;
  no meter, none needed. Unseen: while it shows, task suggestions wait behind it — at most 2 h.*
- **The question.** `_data_object_block()` gains one fact line: *"Offered this turn: 'Want me to
  start a list of …?' — the user answers with the card in the app."* `synthesizer.md` (Red)
  gains one conduct line: ask it once, in those words, and say the answer is the card — a yes
  in words starts nothing; if they say it belongs in a list they already keep, add their name for
  it to that list.
- **The offer cards are kept OUT of `enforce_pending_receipt()`** (review R2): that function
  REPLACES a reply that matches a completion claim when a card was raised this turn, and an offer
  rides on a turn about something else ("I've added milk to your list" would be discarded and a
  false `FALSE_COMPLETION_CLAIM` filed). `_pending_raised_since()` skips both offer actions, as
  it skips `_PENDING_INFORMATIONAL`, so neither the reply nor the Diarist's directive note is
  touched. Instead `_offer_receipt(text, offer)` (orchestrator, beside `_take_log_offer`, A8
  likewise) **appends** the code-written question — *"Want me to start a list of …? Tap Yes or
  No in the app."* — only when the reply does not already point at the app
  (`_ASKS_FOR_APPROVAL_RE`). It never replaces. On the streaming path an appended line goes
  through the existing replace-with-corrected-text marker, as the receipt line does.

### 3.4 The answers — the card is the answer, never the reply's wording

- **Yes → `POST /confirm` → `tools/noticed_logs.create_noticed_log(…, confirm_token)`**
  (registered in `confirm._EXECUTORS`): `consume()` the token; `create_object(origin="noticed",
  aliases=[category], identity=…)`; file each held fact by code with `archive_write` as
  `{"text": …, "noted_at": <date>, "source": "noticed"}`. **If `create_object` returns any
  match, nothing is filed** (review R1 — its fuzzy `close_match` is the one phase 1 refused for
  filing, and the match may be a store, archived or private): the executor returns an error the
  server shows as *"⚠️ Not done — … you already keep something close: X"*, and the offer is
  marked `failed`. Otherwise the offer is marked `yes`. **`alias_noticed_log`** files only into
  an exact, active, non-private, archive-store log by id (else `failed`), adds the offer's
  categories as aliases through a code path in `tools/data_objects.py` (`add_alias()` —
  `amend_data_object` refuses an unbound caller), and files the facts the same way.
- **No → `POST /decline`** → the confirm ledger (`declined_confirmations.json`) holds the args
  with the `offer_id`; the count at the decline is in the offer's own record. Not offered again
  until the held count reaches twice that. **The decline line the server writes is per action**
  (review R8): today it says *"I won't ask about it again"* for every card, which a re-offer at
  double would break. `confirm.py` carries a small map of decline lines; for the offers:
  *"No list started. I'll only ask again if it keeps coming up a lot."* `core/server.py`
  `/decline` reads it (Amber).
- **Unanswered → expires**, counts as neither; re-offered only after `noticed_raise_count`
  more facts.
- **"That belongs in my X list" → a second card, never a filing** (review R4, R5). The
  Synthesizer adds the user's name for it as an alias of X (`amend_data_object add_alias` — it
  holds the tool; a change to a log is its). It does not know the internal category label and
  need not: at most one offer card is open per user, so code, after any `add_alias` by the
  Synthesizer on an active, non-private archive-store log **while an offer's create card is
  open**, withdraws that card (`confirm.withdraw()` — removes the pending record, writes no
  decline; the offer is marked `superseded`) and raises an `alias_data_object` card for the same
  offer on X: *"Keep the places you've mentioned wanting to try in your X list (3 so far)"*.
  **The facts are filed only on that tap.** No model call declines a card or files an entry. An
  unrelated alias added while a card is open costs the user one odd card to decline — nothing is
  written.
- **Outcome, from card records only.** Each offer's status is reconciled from server state:
  executor ran → `yes` (or `failed`); `offer_id` in the declined ledger → `no`; withdrawn by
  code → `superseded` (its alias card is an offer outcome of its own); token still pending →
  `open`; otherwise → `expired`. A ledger record whose args failed `decline()`'s tamper check
  carries no `offer_id` and cannot be attributed — it reads as `expired`, the conservative
  side. **Yes rate = yes / (yes + no)**, per user, in
  `python3 -m tools.capture --report`. Content-free rows (`row: "offer"`, kind, outcome, no
  category) go to `capture/outcomes.jsonl`; the offer state with its words stays in
  `capture/noticed.json` (sensitive tier, the persona's own folder).
- **The config stays on ask** (`noticed_logs: ask | off`). Create-and-tell (R5) is not built —
  Mike's switch later, once the yes rate supports it.

### 3.5 The derived writer — in shadow (§ 3.4 "Derived", R15)

- **The extractor gains an `entry` kind** (`capture_extractor.md`, Red): a fact that is plainly
  an entry for one of the user's logs, listed in its input under THE USER'S LOGS (archive-store
  active logs: id, name, description, field names — never entries). `target` is the log id;
  `proposal` is `{field: value}` in the log's fields. The relative-reference rule
  (`tools/record_rules.py`) is appended to the kind's line by code, its one home.
- **Code validates:** `target` is a listed id; fields are the log's own (or `text`/`notes`);
  values strings ≤ 200.
- **Never shown.** `entry` is handled before the note in `_triage()` and in the `late` path, so
  it can never reach a CAPTURE NOTE, pending or carried.
- **Skipped as already kept** when this turn wrote to that log (`write_data_object` /
  `write_archive` in its trace) **or touched it at all** — `note_for_synthesizer()` is passed
  the ids of every log in `data_turn` `started`, `adding`, `amending` and `delegated` (review
  R9: a correction or a "start a log of …" read as an entry is phase 1's double-entry failure),
  because the Diarist's write and the Synthesizer's amend land after this check.
- **Shadow (`derived_entries: shadow`, the default):** the proposal is recorded in
  `capture/derived.jsonl` (sensitive tier: request id, time, target, proposal, quote) and a
  content-free outcome `derived_shadow`. **Nothing is written** — test 5.
- **On (not until the score passes):** code writes it with `archive_write` as
  `{**proposal, "derived": true, "source_turn": <request id>}` — archive-store logs only. A
  proposal for a log kept in another store (sleep, exercise) is recorded and never written.
- **Scored like capture:** `--label-derived` / `--score-derived` on `tools.noticed_logs`
  against capture's precision minimum (0.90). M4 is the labelling.

### 3.6 Capture (§ 3.10)

`KIND_TOOLS["entry"] = "write_data_object"`; `KIND_HOMES["entry"] = ("write_data_object",
"write_archive")`; `event` gains `write_data_object` (`other` takes no home — it is never
matched, it is the detector's input); `entry` joins
`AGENT_KINDS["synthesizer"]`. `raise_new_categories` keeps its alert. The capture report adds:
categories that crossed the threshold, matcher verdicts, cards raised, offered / yes / no /
moved / expired / open and the yes rate, and the derived writer's shadow proposals.

### 3.7 Promotion (R6, R21, R29)

- **`tools/analytics.py`** daily row gains **counts only**: `data_objects_asked`, `_noticed`,
  `_template` (templates the user has written to), `_existing`, and `data_object_fields_added`
  (`write_data_object(add_field)` increments a per-object `fields_added`). A snapshot of the
  registry when the row is built, not that day's events — said in the docstring. Test 6 asserts
  no log name, alias or field name appears in any value.
- **`scripts/data_object_report.py`** — VM, developer-only, prints to the terminal, writes
  nothing. Every user's asked and noticed logs: names, aliases, field names, grouped by their
  distinguishing words (`data_objects._core`) side by side, plus each user's offer yes rate.
  **A user without a current `base_configuration` record is excluded by code** (test 7) — the
  sign-up consent whose text says Mike can read what they tell Metatron.
  **Plan's choice, for Mike:** `mike` has no such record. Seed one on the VM
  (`accounts.py seed-consent mike --scopes base_configuration --evidence …`) rather than give
  the developer a special case in code.

### 3.8 The reverse check (R26)

`scripts/check_data_object_relevance.py --agent <id> [--persona <p> | --all] [--apply]` — the
existing `data_object_tagger`, run per log with that one agent's remit; prints what it would add;
`--apply` adds it. Dry run by default; on the VM by Mike or at his instruction. Step added to
`docs/CONVENTIONS.md` § adding a module.

## 4. Files

| Tier | Files |
|---|---|
| **Red** (shown line by line, made with Mike) | `config/agents/data_object_matcher.md` (new) · `config/modules/routing.yaml`, `routing_cloud.yaml` (matcher entry) · `config/agents/capture_extractor.md` (`entry`) · `config/agents/synthesizer.md` (one line) |
| **Amber / Green** | `tools/noticed_logs.py` (new) · `tools/capture.py` · `config/modules/capture.yaml` · `tools/confirm.py` (`ttl_seconds`, offer cards sorted last, `withdraw()`, per-action decline lines, two executors) · `core/server.py` (`/decline` reads the line) · `tools/data_objects.py` (`add_alias`, `fields_added`, the offer hook after `amend_data_object` add_alias) · `core/orchestrator.py` (`_take_log_offer`, `_offer_receipt`, the block line, offer actions out of `_pending_raised_since`, the touched-log ids to capture) · `tools/analytics.py` · `scripts/data_object_report.py`, `scripts/check_data_object_relevance.py` · `docs/CONVENTIONS.md` · `tests/test_noticed_logs.py` |
| **Denied / VM data** | `mike`'s `base_configuration` record (if Mike agrees) |

## 5. Tests — every live meter stubbed (matcher, extractor, tagger, FCM, Places)

New `tests/test_noticed_logs.py`, confirmed failing on HEAD:
1. 3 in 30 days → an offer is held; 2 → none; 3 outside the window → none.
2. A matcher `match` on an archive log → an `alias_data_object` card; on a store → none.
3. A declined category is not re-offered at 5; is at 6 (count at decline 3).
4. Yes creates the log with `origin: noticed`, the category as alias, the held facts as entries.
5. The derived writer writes nothing in shadow (log file byte-identical), records the proposal.
6. The analytics row contains no log name, alias or field name.
7. The report excludes a persona without a `base_configuration` record.
8. The card is raised at the next user turn, not at detection; none on a scheduled turn.
9. An invalid matcher answer raises no card.
10. "Belongs in X": a Synthesizer alias while a create card is open withdraws it (no decline
    written) and raises an alias card on X; **nothing is filed until that card is approved**.
11. `entry` never reaches a CAPTURE NOTE or `pending.json`, on time or late.
12. A reply that says "I've added milk to your list" on an offer turn is kept as written, gains
    the code-written question, and files no `FALSE_COMPLETION_CLAIM`.
13. An offer card sorts behind a `send_email` card raised after it.
14. Yes with a close-match log present files nothing and returns "you already keep something
    close"; the alias executor refuses an archived, private or non-archive target.
15. A `same_offer` verdict raises no card and attaches the category to the earlier offer.
16. The decline line for an offer card does not say "won't ask about it again".
17. The derived writer skips a log the turn started, amended or delegated.

Regression: `tests/test_data_objects.py` (53), the capture suite, `test_health_notes_feed.py`,
`tests/run_knowledge_routing.py --persona danny_park` (live, `METATRON_LIVE=1`),
`scripts/check_agent_tools.py`, `bash scripts/qa_sweep.sh`; restore any dirtied tracked
`data/personas/danny_park/…` file.

## 6. Contradictions in the parent plan, fixed (edits made there, marked "phase 2 build")

1. **§ 3.1 puts the detection threshold in `config/modules/data_objects.yaml`; the build prompt
   puts the switches in `capture.yaml`.** → `capture.yaml`, beside the `other` route it reads.
2. **§ 3.4 "the same mechanism the zone suggestion uses, announced in the next reply"** — the
   zone card is never announced, and a card raised at detection expires (§ 2.1–2.2). → held at
   detection, raised at the next turn, announced in the logs block.
3. **§ 3.6 counts by origin "asked / noticed / template"** — phase 1 added `existing` for
   registered stores. → four origins.
4. **§ 3.10 "`place` gains `write_data_object`"** — done in phase 1. → only `event` and `entry`
   remain; `other` is never matched, so a home for it would mean nothing.

## 7. Cost

- **Build:** ~0.5–0.7M Opus, ~0.15M Fable (this plan) + ~0.15M Fable (the diff), ~25 min Mike (M4).
- **Run, per user:** matcher ~$0.0005 per threshold crossing (a few a month); the extractor's
  input grows by the log list (~20 tokens per log, ~300–400 at mike's size) and its output by
  ~50 tokens on entry turns — together ≈ $0.0002/turn on the bulk tier, **≈ $0.005–0.01/day**,
  paid in shadow too; cards, the report and the reverse check's dry run cost no model call
  (an `--apply` run costs one tagger call per log, ~$0.0005 each).
- **Persists:** cards (bytes, 2 h, pruned on read, restart-safe, no meter); the declined ledger
  (bytes, capped at 200 by confirm.py, restart-safe); `capture/noticed.json` (bytes per offer,
  never deleted — it is the yes rate's record; a `matching` offer a restart orphaned is retried
  by the next sweep after 10 minutes); `capture/derived.jsonl` (bytes a turn, kept until the
  score is taken; no meter — the capture report reads it).
- **Unseen:** a dead detector reads as "no new logs needed" — the capture report prints
  crossings, verdicts and cards; a matcher failing every time reads the same — `matcher_failed`
  is printed.

## 8. Known limits, stated

0. **After a yes, the list grows only by explicit adds until the derived writer is switched on**
   (review R7). Later mentions of the same thing reach the extractor as `entry` proposals for the
   new log — and the derived writer is in shadow by the build prompt's binding rule (R15: the
   extractor invents values, 87% precision). So until M4's score passes, "add X to my list"
   files an entry and an unasked mention does not. **Plan's choice, for Mike:** keep it so — the
   shadow then measures exactly the entries a noticed list would have received. The alternative,
   writing derived entries into noticed logs only, is an 87%-precision writer on the user's
   record without a score.

1. A "yes" typed in chat may make the Coordinator start an `asked` log of a similar name; a tap
   afterwards files the facts into it, and an untapped card expires. Accepted — the card stays
   the answer.
2. The held facts are the extractor's one-line summaries (87% precision), filed only after the
   user taps yes on a card that says how many there are.
3. The derived writer goes `on` only after M4's score — its duplicate guard covers this turn's
   asked entries and writes; a duplicate across turns is what the labelling measures.

## 9. Fable's review of this plan, reconciled (2026-11-22)

Nine findings, one ranking. Each was checked against the code before it was accepted; all nine
hold. **Everything below is already folded into §§ 3–8.**

| # | What the user would have seen | Change |
|---|---|---|
| R1 | "✅ Done — Start a list" while the facts went into a near-named, archived or dead log | any close match files nothing; the alias executor accepts only an exact, active, non-private archive log (§ 3.4) |
| R2 | a correct reply ("I've added milk") replaced by "Waiting for your approval…", plus a false quality event | offer cards kept out of `enforce_pending_receipt`; a code-written question is appended, never a replacement (§ 3.3) |
| R3 | an email awaiting approval never shown, because a 24 h offer card held the app's one card slot | offer cards sort last; lifetime 2 h (§ 3.3) |
| R4 | entries filed into a log on a model's alias call, with no tap | "belongs in X" raises an alias card; filing only on its tap; no model call declines (§ 3.4) |
| R5 | "belongs in my X list" doing nothing live while its test passed (the category label is gone by the next turn) | the hook keys on "an offer card is open", not the label (§ 3.4) |
| R6 | a declined list asked again as new under a different label | the matcher sees earlier declined/expired/none offers; `same_offer` verdict (§ 3.1–3.2) |
| R7 | a noticed list frozen at its first entries | facts read at tap time; the freeze after a yes is stated, with the plan's choice for Mike (§ 3.3, § 8.0) |
| R8 | "I won't ask about it again", then asked again at double | per-action decline lines (§ 3.4) |
| R9 | (once `on`) a correction or a "start a log" filed as a derived entry | the guard covers every log the turn touched (§ 3.5) |

## 10. Fable's review of the diff, reconciled (2026-11-22)

Eight findings, all checked against the code and accepted; each has a check in
`tests/test_noticed_logs.py` (F1–F8). The design is unchanged; what moved:

| # | What the user would have seen | Change |
|---|---|---|
| F1 | a declined or unanswered list never offered again (the matcher, shown its own earlier offer, kept saying "the same") | a re-offer reuses the earlier verdict with no model call; the topic being judged is never in `earlier_offers` |
| F2 | "that belongs in my X list", said on the next turn, did nothing | an open offer is reported on every turn while it waits ("Still waiting … do not ask it again"); `synthesizer.md` line extended to "offered or still waiting" |
| F3 | a card with no question, when another card's receipt line was added the same turn | the question check reads the Synthesizer's own words, not the receipt line |
| F4 | a Yes answered "⚠️ Not done — you already keep something close" | a `new` verdict that `close_match` would refuse is `home`, checked at judgement and again at raise |
| F5 | a spend pause or outage silenced a topic for good | a call that could not be made is `deferred` and retried; a bad answer waits for its count to double, never closed |
| F6 | an unrelated alias, then a reasonable No, removed the list offer for good | a declined or ignored alias offer hands the topic back to its list offer (`expired`) |
| F7 | the user's log id in the content-free outcomes file | the outcome row carries `entry`; the log is in `derived.jsonl` only |
| F8 | `--sweep` printed success and judged nothing | the CLI judges inline; an orphaned `matching` offer is re-asked in place |
