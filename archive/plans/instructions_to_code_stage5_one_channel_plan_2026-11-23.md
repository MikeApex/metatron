# Stage 5 plan — C4, one channel per signal (2026-11-23)

*Planner: Opus 5.5. Read-only. Nothing was edited, built or called except this file. Read: the
sweep (§ 6 first), the Fable review, the driver prompt (§ Stage 5 and § Standing rules),
`.claude/rules/agent-files.md`, and the code below. **Revised against HEAD `8ef2edf`** (the
ranking chat committed `e134948`, `129f3fb` and close-outs). Line numbers are this HEAD's. The
Stage 5 files are clean at this HEAD; a WhatsApp chat has uncommitted lines only in
`core/server.py`, `tools/intake_whatsapp.py`, Android sources and two tests, none of which this
stage touches. Sibling plans read: Stage 2 (M7 owns `CLARIFICATION_NEEDED`) and Stage 4 (#16 per
4-3).*

## Revision 1 (2026-11-23)

Inputs:
- the Fable 5.2 review
  ([…_review_2026-11-23_fable-5-2.md](instructions_to_code_stage5_one_channel_plan_review_2026-11-23_fable-5-2.md));
- the driver's dispositions and Mike's rulings
  ([instructions_to_code_plan_review_stop_2026-11-23.md](instructions_to_code_plan_review_stop_2026-11-23.md)
  §§ 1–3, § 5 binding).

| Review finding | Resolution |
|---|---|
| **S2** — the scrub fails open through `lookup_guard._full_names` | **Resolved (17c = own reader).** `tools/research_scrub.py` reads the profile and contacts itself. It **refuses the Research dispatch** when either store exists but cannot be read. No import from `lookup_guard`. *Evidence note:* the committed `lookup_guard._full_names` (HEAD :91-125) now raises `_Unreadable` rather than returning `[]`, so the review's premise was true only of the untracked copy it read. The ruling stands regardless, and the two readers are now separate on purpose. |
| **S3** — D12's opening edits contradict the code-built `length_ask` note | **Resolved.** O10 and O11 move to the **closing** round (now C7, C8), in the same build as the `length_ask()` string change. `tools/day_plan.py` is clean at HEAD, so the builder makes that change (HEAD :3098-3100). |
| **S4** — Recreation's only channel is unsafe; the JSON-key form is never seen | **Resolved (11 = both channels).** #11 *adds* the `HORIZON_ITEMS:` line and keeps the `follow_up` + `CONSULT_NEEDED: logistics` route. `_file_horizon_items` also accepts a `"HORIZON_ITEMS": [...]` key inside a JSON object. A parse failure in either form writes a `HORIZON_BLOCK_UNPARSED` quality event. No routing grant is needed, and O3 still needs no new code (the line form works with today's parser). |
| **S5** — `CLARIFICATION_NEEDED` would reach the Synthesizer twice | **Resolved.** M7 (Stage 2) owns it. #19's block leaves it out, and C1 no longer mentions it. |
| **L1** — a bare clinical token after a lifted flag leaves the veto's view | **Resolved.** The sign-off veto (`_signoff_skip`, `_signoff_note`) scans the specialist text built **before** any lift. A lifted body stops at the next upper-case token, bare or with a colon. A flag whose body would contain a clinical token is never lifted. Fixtures pin token order, including a bare clinical token after a lifted flag on one line. No live A4 run (19 as ruled). |
| **L6** — exact match misses reformatted identifiers and silently rewrites public terms | **Resolved.** The scrub **refuses with a reason**, like `lookup_guard`, instead of rewriting. Phone numbers compare as digits only, and postcodes upper-case with spaces removed. The address matches only its street segment (the first comma segment, and only when it holds a house number) plus its postcode, never a bare district or city. Contacts with an organisation `relationship_type` are skipped. |
| **L7** — `write_persona` defaulting to "add" keeps a corrected preference beside its replacement | **Resolved.** `"replace"` stays the default. `"add"` is an explicit mode. |
| **L8** — the tone check drops the profiled contact's own name through a duplicate or namesake | **Resolved.** "Another contact's name" means a name word held by another contact **and not** by the profiled contact (name, first name, nickname, preferred name, `referred_to_as`) or by the user. |
| **L9** — an alphabetical `PROFILE_GAP` pick starves health gaps | **Resolved.** Losing gaps are queued per persona and rotate: oldest first, then by the agent that won least recently. Each has a 7-day expiry and a cap of 10. |
| #16 placement | **Moved to Stage 4** (Mike, 4-3). Only a pointer remains in § 1. Stage 5 names no `relationships.md` text for it, so Stage 4's C8 is Stage 4's to word. |

| § 2b.3, the two homes for the decontextualisation rule | **Revised.** Because the scrub refuses rather than rewrites, code enforces the identifier half instead of carrying it. Both writers keep the rule. C3 is dropped. C4 adds one sentence on what a `refused:` reply means. |

**Red counts after revision:**
- **Opening round:** 15 Red + 1 Amber.
- **Closing round:** 8 Red + 2 Amber.

*Superseded in part by Revision 2:* the second identifier reader and the `employer` field are
withdrawn.

## Revision 2 (2026-11-23, from the Fable re-check)

Rows are in the coordinator's order. Each supersedes the matching part of Revision 1.

| # | Re-check finding | Resolution |
|---|---|---|
| 1 | 17c's premise is false: the committed `lookup_guard.py` (:87-151) already fails closed. Keep one home. | **Reversed to one reader.** The Research check is `lookup_guard.check_research()`, inside `tools/lookup_guard.py` (Amber). It reuses `_full_names` and `_names_in` (first and last with up to two words between, or reversed with a comma). The user's own email, phone and address are added there in `_own_identifiers()`, which raises `_Unreadable` like `_full_names`. No `tools/research_scrub.py`. Tests include "First M. Last" and "Last, First". |
| 2 | Under refuse-not-rewrite, an employer is a public organisation name, and every query about it would be refused. | **17a dropped.** No `employer` field, no `tools/profile.py` change, and no employer check. |
| 3 | #19 stopped a body at any capitalised word of 4+ letters, so acronyms (HMRC, ADHD) cut bodies short. | **Explicit stop list.** A body stops only at a known token: the flag names defined in the agent files' flag lists (enumerated at HEAD, § 1 #19), the output-section labels, and the clinical tokens. A test reads the agent files' flag bullets and fails if any is missing from the list. Fixtures have HMRC and ADHD inside bodies. |
| 4 | The `PROFILE_GAP` queue could be spent on a turn where the Synthesizer never runs. | **Consumed only when the Synthesizer runs.** `lift()` is read-only. `commit_rotation()` is called after the sign-off skip decision, only when the Synthesizer runs. It is never called on a day-plan nudge or with empty specialist outputs. |
| 5 | #21's name match was case-insensitive and would hit org names and common words. | **Tightened.** Case-sensitive, on capitalised tokens only. Organisation contacts are skipped (`lookup_guard._ORG_TYPES`, the same rule). A stoplist covers common words that are also names (`Will`, `May`, `Mark`, `Grace`, `Rose`, `June`, `Hope`, `Bill`, `Pat`, `Art`, `Joy`, `Dawn`, `Summer`, `Faith`, `Frank`, `Grant`, `Victor`, `Sterling`, …, kept in `tools/tone.py`). Tests cover "School Office", Will, May and Mark. |
| 6 | A refusal on the `lookup_public_fact` path spent the daily cap and came back wrapped as web content. | **Refund and plain refusal.** `check_research`'s refusal starts with a fixed prefix (`RESEARCH_REFUSED`, exported from `lookup_guard`). `lookup_public_fact` (:187-220) checks for it after `run_session`, gives the day's place back (the existing refund block), and returns the refusal unwrapped. |
| — | New uncommitted edits by other chats in `core/orchestrator.py`, `tools/obligations.py`, `tools/day_plan.py`, `config/agents/synthesizer.md` and `synthesizer_scheduled_sessions.md` | **Planned against HEAD.** § 5 lists which hunks sit near theirs. Two Red/Amber targets carry other chats' lines (`synthesizer.md`, `synthesizer_scheduled_sessions.md`), so the stop-and-ask rule applies at the opening round. |

**Red counts unchanged:**
- **Opening round:** 15 Red + 1 Amber.
- **Closing round:** 8 Red + 2 Amber. C4's wording drops "an employer".

**Tiers, from `.claude/settings.json`.** Red (`ask`): `config/agents/*.md`, both routing files,
`core/{router,persona,scheduler,spend_guard}.py`. **`config/modules/synthesizer_*.md` are Amber.**
They are not in the `ask` list. **There is no `day_plan.md` in the repo.** The sweep's
"`day_plan.md:11`" is `config/modules/synthesizer_day_plan.md:11` (Amber). The persona copies
(`config/personas/mike*`) are VM-only here and Denied, so any change to them is Mike's to make. The
module edits are judgement text, so the driver makes them in the same rounds as the Red edits, but
they need no approval prompt. **No routing-file edit is needed in this stage.**

**Two findings that shaped this stage (both resolved in Revision 1):**

1. **Recreation holds no `record_horizon_item` grant**, so a `HORIZON_ITEMS` line alone would be
   its only channel. It keeps its `follow_up` route as well (both channels, ruling 11).
2. **D12 needs one string in `tools/day_plan.py` `length_ask()`** (HEAD :3072; the f-string at
   :3098-3100). That string puts "ask once … record their answer with set_minutes as stated"
   into every plan block. So D12's agent text goes in the closing round, beside that change.

---

## 1. Per item

### #7 — Logistics' false sentence (instruction honesty; both channels stay, D5)
- **What a user would notice:** nothing directly. Logistics stops believing that a finding listed
  only in its block is lost. That belief is the reason it pays a round-trip per finding even when
  the block would carry it.
- **Mechanism:** none. Verified: `_file_horizon_items` (orchestrator HEAD :6582) parses
  `HORIZON_ITEMS:` from every specialist's output, files it through `tools.horizon.record`, and
  strips it before the Synthesizer sees it. Two sentences are therefore false:
  - `:101-102` "a finding in the block that you never filed will not reach anyone";
  - `:81` and `:99-100`: the block is "a summary … not the delivery", "so the Synthesizer can see
    the shape". The Synthesizer never sees it.

  `record` dedupes by `item_key`, so a finding in both places is filed once.
- **Files:** `config/agents/logistics.md` (Red). Opening round, O1.
- **Tests:** `check_agent_tools.py`. Logic unchanged.
- **Cost:** 0.
- **Risk:** the model may start skipping tool calls. That is what D5 wants checked before a
  channel is removed, and the edit keeps "the tool call is the channel to rely on".

### #11 — Recreation adds `HORIZON_ITEMS`, keeping `follow_up` (ruling 11: both channels)
- **What a user would notice:** a concert or plan Recreation spots is raised once, through the
  horizon record. A far-off one that needs tickets or travel booked is raised when that has to
  happen. If the record line goes missing, the `follow_up` route still carries it, as it does
  today.
- **Mechanism:**
  1. **Agent text (opening round, needs no new code):** Recreation adds a `HORIZON_ITEMS:` line
     after its JSON object. Today's parser already matches that form (`_HORIZON_ITEMS_RE`, HEAD
     :6573: the literal `HORIZON_ITEMS:` and then `[`). It keeps `follow_up` and
     `CONSULT_NEEDED: logistics` unchanged. The array goes on one line with no `]` inside any
     value (the bare form is non-greedy to the first `]`), the same constraint Logistics lives
     under. `tools/horizon._valid` requires a title and rejects a malformed `date` or
     `precursor_by`.
  2. **Code (Amber):**
     - `_file_horizon_items` (HEAD :6582) also accepts the key form `"HORIZON_ITEMS": [...]`
       inside a JSON object. Change the early `"HORIZON_ITEMS:" not in text` test to a test for
       either form.
     - Strip the key form together with one adjacent comma, so the object stays readable.
     - **On a `JSONDecodeError` in either form** (HEAD :6616), write `HORIZON_BLOCK_UNPARSED`
       (`source_agent` = the agent; detail = the first 300 characters of the raw block), shaped
       like `CONTEXT_BLOCK_UNPARSED`, beside the existing warning.
     - Register the type in `scripts/sync_dev_backlog.py` (`MACHINE_TYPES` and the label map).

  An absent line cannot be detected; that is what keeping `follow_up` covers.
- **Files:** `config/agents/recreation_hobbies.md` (Red; O2, O3), `core/orchestrator.py`,
  `scripts/sync_dev_backlog.py` (Amber).
- **Tests:** offline, in `tests/test_horizon_ledger.py`:
  1. a Recreation-shaped output (a JSON object, then a `HORIZON_ITEMS:` line) is filed and
     stripped, and the JSON object is intact;
  2. the key form inside the object is filed and stripped, and the object still parses;
  3. a malformed array in either form writes one `HORIZON_BLOCK_UNPARSED` and never raises;
  4. `tests/test_quality_event_reconciliation.py` passes with the new type.
- **Cost:** about 60 output tokens on Flash-Lite when Recreation has a find. Run ≈ 0.
- **Risk:** a find raised through both channels could be said twice in one reply. The horizon
  block arrives with its own delivery instruction, and the Synthesizer already treats two
  outputs naming one fact as one observation (`synthesizer.md:107`). A Recreation follow-up
  called through `run_subagent` is still not filed, as is already true for Logistics.

### #16 — moved to Stage 4
Mike ruled 4-3: #16 is built at Relationships dispatch beside #12, in
[the Stage 4 plan](instructions_to_code_stage4_evidence_plan_2026-11-23.md) (§ #12, "#16 hook").
Stage 5 builds nothing for it and names no `relationships.md` text for it.

### #17 — a Research query carrying a known identifier is refused, plus § 2b.3
- **What a user would notice:** a research lookup never carries their full name, a contact's
  full name, or their own street address, postcode, email or phone into a web search, even when
  the agent writing the query forgot to take it out. A query that does is sent back to be
  rephrased, never silently altered.
- **Mechanism — one identifier reader, in `tools/lookup_guard.py` (Revision 2):**
  - **One choke point.** Every Research call reaches `_run_single_agent`'s `research_agent`
    branch (HEAD :5702): Coordinator dispatch, `run_subagent`, and `lookup_public_fact` (which
    calls `run_session`).
    - There, before any provider call, `why = lookup_guard.check_research(user_input, persona)`
      runs under `persona_scope(resolve_persona(persona))`.
    - When `why` is set, the session returns
      `f"{RESEARCH_REFUSED} the question carries {why}. Nothing left this device. Ask it again
      without that."`, where `RESEARCH_REFUSED = "refused before sending:"` is exported from
      `lookup_guard`. The model is never called.
  - **`check_research(query, persona) -> str | None`, added to `lookup_guard.py`:**
    - **names:** `_full_names(persona)` + `_names_in(_norm(query), names)`, both reused as they
      are (:91-151). That covers the user's and contacts' first and last names (and nickname +
      last, `name`, `spouse_name`, `referred_to_as`), with up to two words between or reversed
      with a comma; organisation contacts and one-word names are skipped (17b).
    - **the user's own contact details:** a new `_own_identifiers(persona)` in the same file,
      read from the profile's `contact` (`tools/profile.py` `_CONTACT_FIELDS`, :47). It returns:
      - the email, lower-cased;
      - the phone, as digits only, and the same with a leading `0` swapped for `44` and the
        reverse (the builder tests the rule);
      - the postcode found in the address, upper-cased with spaces removed;
      - the address's first comma segment, only when it holds a digit, whitespace-collapsed.

      It raises `_Unreadable` on a profile read error, as `_full_names` does.
    - **Matching (review L6):**
      - the email by case-insensitive substring;
      - the phone against every digit run of 7+ in the query after removing spaces, dots,
        dashes, brackets and a leading `+`;
      - the postcode against the query upper-cased with spaces removed;
      - the street segment by case-insensitive substring.
      - A bare district or city never matches.
    - **Not applied here:** `check()`'s general pattern refusals (any email-, phone-, address-,
      money- or health-shaped text). Research legitimately asks about dosages and prices. Only
      the user's *known* identifiers are refused. `lookup_public_fact` still runs `check()` first,
      unchanged.
    - **Fail-closed:** `_Unreadable` from either reader refuses: `the user's records could not be
      read, so nothing was sent`. A missing file is not an error; it holds nothing.
  - **On the `lookup_public_fact` path** (:187-220): after `run_session` returns, an answer
    starting with `RESEARCH_REFUSED` gives the day's place back (the existing refund block, moved
    into a small helper both paths call) and is returned as the plain refusal, **not** passed to
    `wrap_untrusted`.
  - **Trace:** `[RESEARCH] refused: <kind>`, the kind only, never the value.
  - **No employer check** (Revision 2: 17a dropped).
- **§ 2b.3:** the rule is in two homes, `coordinator.md:235` and `synthesizer.md:117-124`.
  - Both agents write Research queries, and the Coordinator never sees `synthesizer.md`, so both
    keep the rule. Code now **enforces** the exact-identifier half by refusing; it does not
    carry it.
  - The closing round adds one sentence to the Synthesizer (C4) on what a `refused:` reply
    means. The Synthesizer is the one writer that can re-ask: a Coordinator-dispatched refusal
    reaches it as Research's output.
  - The Coordinator's copy is unchanged (C3: not edited).
- **Files:** `tools/lookup_guard.py` (Amber: `check_research`, `_own_identifiers`,
  `RESEARCH_REFUSED`, the refund helper); `core/orchestrator.py` (Amber, one call).
- **Tests:** offline, in a new `tests/test_research_check.py` (the existing `lookup_guard` tests
  live in `tests/test_ranking_v2.py`),
  with the profile and contacts stubbed and `run_session_gemini_grounded` stubbed to record calls:
  1. Each of these is refused, and the provider is never called:
     - the user's full name;
     - a contact's "First Last", **"First M. Last"** and **"Last, First"**;
     - the email;
     - the phone written another way ("+44 7700 900123" against a stored "07700900123");
     - the postcode without its space;
     - the street segment.
  2. A single first name passes ("Grace School term dates" with a contact named Grace — B22).
  3. The address's city or district alone passes ("London" when the address is "…, London,
     SW1A 2AA").
  4. An organisation contact's name passes, and so does an employer-like organisation name.
  5. A dosage or price question passes; `check()`'s figure refusals are not applied here.
  6. A corrupt contacts file refuses; so does a corrupt profile. A missing file passes.
  7. The trace carries the kind and never the value.
  8. `lookup_public_fact` on a question refused by `check_research`:
     - the day's count is unchanged afterwards;
     - the return value starts with `RESEARCH_REFUSED`;
     - it carries no `<untrusted_content>` wrapper.
  9. `lookup_public_fact` still works end to end on a clean question, and every existing
     `lookup_guard` test in `tests/test_ranking_v2.py` passes unchanged.
- **Cost:** 0 tokens. Local string work. No new spend meter is needed, and none is blind to it.
  A refused query costs the writer one retry turn, which is rare by construction.
- **Risk:** Mike's real names are not testable here, because his profile is VM-only. Live check:
  ask a research question that names a contact's full name, and see a reply that answers without
  it.
- **Ruled, as revised:**
  - 17a (employer): dropped (Revision 2).
  - 17b (a lone first name is not refused): yes.
  - 17c: one reader, in `lookup_guard.py`, which fails closed (Revision 2 reverses the
    own-reader ruling on the evidence that `_full_names` already raises `_Unreadable`).

### #19 + D7 — one `FROM THE SPECIALISTS` block
- **What a user would notice:** a specialist's request for a consult, a lookup or a profile
  question is acted on or dropped deliberately instead of being lost in prose. At most one profile
  question reaches any turn, against "one per session" (several can reach a turn today).
- **Mechanism:** a new `tools/specialist_requests.py` with
  `lift(outputs: dict, persona: str | None) -> tuple[dict, str]`.
  - **Called on both twins**, right after `_drop_unprompted_clinical_flags` (HEAD :7883 and
    :8182).
  - **The sign-off veto never sees lifted text.** Each twin builds `veto_text` from the outputs
    **before** `lift()`, with the same join as `spec_text` (HEAD :7890, :8187), and passes it to
    `_signoff_skip` (:7905, :8198) and `_signoff_note` (:7913, :8208). Only the Synthesizer's
    `spec_text` is built from the lifted outputs.
  - **Finds** `CONSULT_NEEDED`, `RESEARCH_NEEDED` and `PROFILE_GAP` wherever they sit: on a
    `FLAGS:` line, as a bullet, or inside a JSON string (Recreation puts flags in
    `"flags": [...]`).
    - **The body stops** at the end of the line, a closing `"`, or the next **known token**,
      bare or with a colon (Revision 2). An acronym inside a body (HMRC, ADHD, NHS) never stops
      it. A bare `MEDICATION_MISSED_CRITICAL` after a lifted flag is never swallowed. The known
      tokens form one frozenset, `KNOWN_TOKENS`, in `tools/specialist_requests.py`:
      - every flag defined in an agent file's flag list. At HEAD that is the bulleted
        `**NAME**` definitions across `config/agents/*.md`, 131 names, from
        `ARCHITECTURE_GAP` to `WITHDRAWAL_CASCADE`, including `CONSULT_NEEDED`,
        `RESEARCH_NEEDED`, `PROFILE_GAP`, `RESEARCH_AVAILABLE`, `CONTEXT_NEEDED`,
        `LIVE_DATA_NEEDED`, `TOOL_NOT_BUILT`, `DEFLECT_TO_CONTACT`, the `MEDICATION_*` and
        `SLEEP_*` families, and `HORIZON_ITEM`. The builder generates the literal list once with
        `grep -ohE "^\s*-\s+\*\*[A-Z][A-Z_]{3,}" config/agents/*.md`.
      - the output-section labels specialists write: `FLAGS`, `MUST_SURFACE`,
        `PROACTIVE_OBSERVATIONS`, `MEDICATION_TAKEN`, `MEDICATION_NEEDS_LINK`,
        `MEDICATION_LINK_BROKEN`, `WISDOM_PROPOSAL`, `HORIZON_ITEMS`,
        `COORDINATION_OPPORTUNITIES`, `EXECUTION_TREE`, `PENDING_CONFIRMATION`, `NOTHING_LOGGED`,
        `CAPTURED`;
      - the clinical tokens (below).

      **Drift guard:** a test re-runs the same grep and fails if any agent-file flag is missing
      from `KNOWN_TOKENS`. A new flag added to an agent file without the list fails CI rather
      than silently becoming body text.
    - **Clinical tokens are never lifted:** if a body would contain any clinical token, that flag
      is left in place untouched. The clinical tokens are `MUST_SURFACE`, `CLINICAL_CONCERN`,
      `MEDICATION_MISSED_CRITICAL`, `ESCALATION` and every name in `_SIGNOFF_FLAG_TOKENS`
      (HEAD :7231), imported, never restated.
  - **Removes** each lifted flag from the output text, then tidies the separators it leaves.
  - **Builds** one block, headed `FROM THE SPECIALISTS (requests, from code)`.
    - The lifted `CONSULT_NEEDED` and `RESEARCH_NEEDED` lines, each prefixed with its agent's
      name (as the `--- agent ---` headers already are; internal input, never user output).
    - **At most one `PROFILE_GAP`**, picked by rotation (below).
    - **No `CLARIFICATION_NEEDED`.** Stage 2's M7 owns that signal and its code note (ruling;
      review S5).
  - **PROFILE_GAP rotation (review L9).** A per-persona queue in
    `persona_data_dir()/specialist_requests.json` (0600), holding `{agent, text, queued}` entries
    and `last_won` by agent.
    - **`lift()` only reads the queue** to make its pick (Revision 2). It returns the pick and the
      losers.
    - **`commit_rotation(persona, pick, losers)` writes the queue.** Each twin calls it only after
      the sign-off skip decision, and only when the Synthesizer is going to run.
    - **It is never called** on a sign-off skip, on a day-plan nudge (`nudge` true), or when
      `specialist_outputs` is empty. On those turns `lift()` is not called at all. So a queued
      question is spent only on a reply that could carry it.
    1. The pool is the queued entries plus this turn's gaps. The oldest queued entry wins.
       Among this turn's fresh gaps, the agent that won least recently wins.
    2. Every other gap is queued, one entry per agent; a newer text from the same agent replaces
       its entry.
    3. Entries expire after 7 days. The cap is 10, and the oldest is dropped past it.
    4. On a write failure, the turn still gets its one gap and the losers are not queued. Logged,
       never raised.
  - **The persistent-state answers.** The unit is a few hundred bytes of local disk per persona,
    and a longer expiry buys only staler questions. The 7-day expiry and the cap of 10 delete it.
    A restart leaves it intact and harmless. No meter needs to report it: it costs no money.
  - **No dispatch.** The block is text in the user message, so no cache effect.
  - **Placement:** at the head of the Synthesizer package, after the user's text and before
    `COORDINATOR ROUTING PACKAGE:` (HEAD :7938, :8231).
- **Files:** `tools/specialist_requests.py` (Amber, new); `core/orchestrator.py` (Amber), two
  call sites plus the `veto_text` change on both twins. Synthesizer line in the closing round (C1).
- **Tests:** offline fixtures in each agent's real format:
  1. a Logistics `FLAGS:` line with two flags;
  2. a Recreation JSON object whose `flags` array holds `CONSULT_NEEDED` and `PROFILE_GAP`, still
     valid JSON after the lift;
  3. Research's `CONSULT_NEEDED`.
  4. **Token order** (review L1). Each must leave the clinical token byte-for-byte in the output,
     and `_signoff_skip` must still be vetoed:
     - `FLAGS: PROFILE_GAP: x, MEDICATION_MISSED_CRITICAL, CONSULT_NEEDED: finance — y`;
     - `FLAGS: CONSULT_NEEDED: logistics — z ESCALATION`;
     - `FLAGS: CLINICAL_CONCERN: …, PROFILE_GAP: …`;
     - `MUST_SURFACE:` on its own line after a lifted bullet.
  5. A body containing a clinical token is not lifted.
  5b. **Acronyms** (Revision 2): `PROFILE_GAP: does the user file with HMRC themselves?` and
     `CONSULT_NEEDED: mental_wellbeing — possible ADHD pattern in focus notes` are lifted whole,
     with the body intact through the acronym. The drift-guard test passes at HEAD.
  5c. **Consumption** (Revision 2):
     - a sign-off-skipped turn leaves the queue file byte-identical;
     - so does a nudge turn;
     - so does a turn with empty specialist outputs;
     - a turn where the Synthesizer runs serves the queued gap and removes it.
  6. Rotation:
     - two gaps on one turn: one wins and one is queued;
     - next turn with no fresh gap: the queued one is served;
     - an agent that won last time loses a tie;
     - a queued entry expires at 7 days;
     - the cap of 10 holds;
     - an unwritable queue still yields one gap.
  7. No flags at all: the outputs are unchanged and the block is "".
  8. `CLARIFICATION_NEEDED` in the Coordinator package is not in the block.

  Also re-run `tests/run_b1_redteam.py --suite deputy`. This adds a parser of agent output, but
  not a dispatch parser, and check 6 must still hold.
- **Cost:** 0 tokens, since text moves rather than grows. State: the queue file, answered above.
- **Risk:** outputs from the Synthesizer's own `run_subagent` follow-ups are not lifted. They
  arrive as tool results.
- **Ruled 19:** no live A4 run. The veto scans unmodified text, clinical tokens are never lifted,
  and the token-order fixtures pin both.

### #21 — tone-profile post-validation
- **What a user would notice:** a draft no longer slips in a pet name used once in years of mail,
  or another person's name, or calls the user by a name only they use for the contact.
- **Mechanism:** in `tools/tone.py`, `_parse_profile(raw, sample="")`, validated **before** the
  `_MAX_LIST_ITEMS` truncation so one-offs do not use up the 6 slots. Split `sample` on
  `^\[(user|them)\] ` blocks (the format `tools/mail.search_correspondence` emits, mail.py :680).
  1. `pet_names` and `shared_phrases`: count whole-phrase, case-insensitive occurrences across
     the sample, and drop a value with fewer than `_MIN_RECURRENCE = 5`. **If a value quotes the
     phrase** (`calls Fridays 'the long one'`, the agent file's own correct example), count the
     quoted part. Counting the whole description would drop every correct entry.
  2. **Other people's names.** Every list value and every string value: drop a list item, or
     blank a string, that contains a whole-word **other-person name word**.
     - An other-person name word is any word of another contact's name, first name or nickname,
       **minus every word held by the profiled contact** (name, first name, last name, nickname,
       preferred name, `referred_to_as`) **and minus the user's own name words**.
     - So a duplicate record of the same person, or a namesake, never removes the profiled
       contact's own name (review L8). `_extract` already has the `contact_id`; it loads that
       record.
     - **How it matches (Revision 2):**
       - case-sensitively, only against capitalised tokens in the value, so "will", "may" and
         "mark" in ordinary text never match;
       - **organisation contacts are skipped**, using the same rule as the Research check
         (`lookup_guard._ORG_TYPES` on `relationship_type`, imported), so a contact saved as
         "School Office" contributes no name words;
       - a **stoplist** of capitalised words that are common words as well as names (`Will`,
         `May`, `Mark`, `Grace`, `Rose`, `June`, `Hope`, `Bill`, `Pat`, `Art`, `Joy`, `Dawn`,
         `Summer`, `Faith`, `Frank`, `Grant`, `Victor`, `Sterling`, `Iris`, `Ivy`, `Jade`,
         `Ruby`, `Amber`, `Holly`, `Rich`, `Sunny`) is never treated as an other-person name
         word. It is a module constant in `tools/tone.py`. This errs toward keeping a value, and
         the agent file's third-party rule still covers the rest.
  3. `names_they_use_for_user`: keep only values that occur in `[them]` blocks.

  `_extract` passes `sample.get("correspondence")` and the profiled contact's record.
- **Files:** `tools/tone.py` (Amber).
- **Tests:** in `tests/test_tone_own_copies.py` or a new `tests/test_tone_validation.py`:
  1. 4 uses dropped and 5 kept;
  2. a quoted phrase counted by its quote;
  3. a third party's name blanked from `register_notes` and dropped from `shared_phrases`;
  4. a nickname seen only in `[user]` blocks dropped from `names_they_use_for_user`;
  5. the contact's own name kept;
  6. **with a duplicate record of the same person, and a namesake contact, on file:** the
     profiled contact's first name and nickname are kept in every field.
  7. **Revision 2:**
     - an organisation contact "School Office" on file: `register_notes` "writes like a school
       office memo" and "warm but Office-formal" are both kept;
     - contacts named Will, May and Mark on file: `shared_phrases` "will do", "May the force" and
       "mark my words", and `register_notes` "Will often signs off first", are all kept
       (lower-case tokens, or stoplisted);
     - a contact named "Tobias" on file: `register_notes` "mentions Tobias often" is blanked.
- **Cost:** 0. It runs in the background extraction.
- **Risk:** a non-contact third party can't be detected. The agent file's rule stays for that.

### #23 — drop Finance's task pre-check
- **What a user would notice:** a little less latency when Finance opens a task.
- **Mechanism:** none. Verified: the ledger's re-filing guards refuse a duplicate
  (`tools/obligations.py` :146 onward, HEAD).
- **Files:** `config/agents/finance.md` (Red). Opening round, O5.
- **Cost:** −1 Flash-Lite turn when it fires.

### #24 — Research's complexity text is dead (review LOCAL 7)
- **What a user would notice:** nothing directly. A research answer's depth now follows what the
  query asks for, because that is the only thing Research actually receives.
- **Mechanism:** none. Verified: `run_subagent` uses `complexity` only to pick a model
  (`tools/subagent.py:122`), and the schema enum is `quick` / `deep`. `research_agent.md:70-78`
  and `synthesizer.md:123` describe a hint Research never sees, plus an `intensive` tier that
  does not exist.
- **Named-tool rule:** `intensive` and `RESEARCH_INTENSIVE` are an aspiration, so they are marked
  as planned rather than deleted.
- **Files:** `research_agent.md` and `synthesizer.md` (Red). Opening round, O6, O7 and O8.
- **Cost:** 0.

### #25 — `find_places` with `at` separates closed venues instead of hiding them (review LOCAL 6)
- **What a user would notice:** a venue suggested for later is not one that is shut then. A named
  place searched with a time comes back as "closed then", not "not found".
- **Mechanism:** in `tools/places.py` `find_places`, when `at_dt` is set, split the summaries into
  two lists:
  - `places`: open, or unknown hours;
  - `closed_then`: name and address only, for results with `open_at_time is False`.

  If none are open, omit `places` and add `note: "Every result is closed at that time."`. That
  keeps the docstring's never-an-empty-list rule. Without `at`, nothing changes. Update the `at`
  description in `FIND_PLACES_SCHEMA`.
- **Why not omit on "open discovery":** code cannot tell open discovery from a named-place search
  without a new model-set flag. That is the class of signal this sweep moves away from. A
  separate list is the exact version: a model picking from `places` cannot pick a closed venue,
  and a named search still sees it. **Ruled 25:** the split, as recommended. A `named: bool`
  parameter was rejected.
- **Files:** `tools/places.py` (Amber). Agent text in the closing round (C5).
- **Tests:** in `tests/test_places_open_at.py`:
  1. a mix of open, closed and unknown is split correctly;
  2. all closed yields `closed_then` plus `note` and no empty `places`;
  3. no `at` gives output identical to HEAD.
- **Cost:** 0.

### § 2b.1 — one morning opening
- **What a user would notice:** the morning brief opens on the one thing that matters today, not
  "How are you feeling this morning?" (an observed correction).
- **Files:** `config/modules/synthesizer_scheduled_sessions.md:31` (Amber). Opening round, O9.
  Mike: if `mike.md` or his `scheduler.yaml` morning prompt still asks "how are you feeling" first,
  that copy is his to remove.

### § 2b.2 / D12 — estimate task lengths, update on evidence, ask only when unknown
- **What a user would notice:** they are no longer asked how long things take. Lengths are
  estimated quietly, corrected when they say otherwise, and asked about only for something nobody
  could guess.
- **One home:** the task-ledger bullet in `synthesizer.md` (:395), because it is always loaded and
  lengths matter whether or not a plan block is present. `synthesizer_day_plan.md:11` (its first
  sentence) and `:36` (the length bullet) are removed into it.
- **Code:** `tools/day_plan.py` `length_ask()` (HEAD :3072): its returned f-string
  (:3098-3100) and its docstring. The task is still named once and still at most
  `length_asks_per_day`, but the text becomes: `No length on file for {title} \`{id}\` — record
  your estimate with set_minutes as estimated, without announcing it. Ask in passing only if you
  have no basis for a guess. No other task's length this turn.` The file is clean at HEAD, so the
  builder makes this change.
- **"Update on evidence"** is what the user says: a correction, or how long it took, recorded as
  `stated`. Learning durations from completion timestamps is **not** in § 6 and is not built.
- **Timing (review S3):** the agent text goes in the **closing** round (C7, C8), after the
  `length_ask()` change is built and tested in this stage. The two land in the same commit
  series, so neither is ever live without the other.
- **Files:**
  - `synthesizer.md` (Red, C7);
  - `synthesizer_day_plan.md` (Amber, C8);
  - `tools/day_plan.py` (Amber).
  - **Mike's to make:** the "estimate, don't ask" line in `config/personas/mike.md`, if present.
    Promotion deletes the original, after the agent rule is live on the VM. Find it with
    `python3 scripts/check_rule_overlap.py --persona mike` on the VM.
- **Tests:** `tests/test_day_plan_*` still pass. One assertion on the new `length_ask` text: it
  contains `estimated` and not `stated`.
- **Cost:** fewer asking turns. Run 0.

### § 2b.4 — new-goal questions against the M-goal rule
- **What a user would notice:** a new goal is checked in one question. Six specialists no longer
  work as if an interview were about to happen.
- **Mechanism:** none. The six identical paragraphs tell a specialist to "ask", but specialists
  never speak. `synthesizer.md:180-187` already treats what they return as material for the check
  and the plan. The paragraph is reworded to "return", in six files.
- **Files:** finance, learning_growth, relationships, physical_health, work_vocation and
  recreation_hobbies (`.md`, Red). Opening round, O12. One replacement, used six times.

### § 2b.5 — Recreation's one-JSON rule against `WISDOM_PROPOSAL`
Fixed with #11, in O2.

### § 2b.6 — Finance's false "no cloud routing" line
- False under the VM amendment, and it narrates routing to a model, which can do nothing with it.
  The line is deleted. Finance has no Research grant, so the sentence protects nothing.
- **Files:** `finance.md:28` (Red). Opening round, O4.

### M5 — `write_persona` add mode
- **What a user would notice:** saving one new preference can no longer drop the others in that
  section, and correcting or removing one still works.
- **Mechanism:** in `tools/persona.py` (Amber; `core/persona.py` is the Red one), add
  `mode`: `"replace"` (**the default**, today's behaviour) or `"add"` (explicit; review L7).
  - **In add mode:** append to the section only the bullets or lines that `_new_lines` finds new
    against that section, or create the section. Nothing existing is altered or removed.
  - **Replace stays the default**, so a model still following today's instruction (resend the
    whole section, including to correct or drop a line) behaves exactly as now. That holds
    before the closing round, and also if the run stops early and skips it.
  - **`mode` goes into `args`** for `request` and `consume`, so an approved card replays the
    same mode (`tools/confirm.execute` calls `fn(**args, confirm_token=…)`).
  - **Bundled fix:** `pattern.sub(new_block, text)` (HEAD :260) treats backslashes in user
    content as group escapes. Use `pattern.sub(lambda _m: new_block, text)`.
  - **Schema** (`WRITE_PERSONA_SCHEMA`, HEAD :320):
    - add `mode` with enum `["replace", "add"]` and the description "`add` appends only what is
      new and keeps every existing line; `replace` (the default) writes the whole section as
      given — use it to correct or remove a preference";
    - the `content` description says "with `replace`, include every preference the section
      should keep".
- **Files:** `tools/persona.py` (Amber); `synthesizer.md:412` in the closing round (C2).
- **Tests:** in `tests/test_persona_write_gate.py`:
  1. `add` to an existing section keeps the old bullets and appends the new one;
  2. a full-section resend with `add` duplicates nothing;
  3. no `mode` replaces, exactly as today;
  4. `replace` with one bullet reworded drops the old wording;
  5. a new section is created in both modes;
  6. an inferred write's approval replays `mode`;
  7. content containing `\1` is written literally;
  8. the redundancy refusal still fires.
- **Cost:** fewer output tokens per preference write. Run ≈ 0.

### M18 — flight and line checks report only disruptions, plus a throttle
- **What a user would notice:** nothing on a clean travel day; this item is small. A second flight
  check in quick succession no longer fails on the one-request-a-second limit.
- **Mechanism:**
  - `tools/tfl_status.py`: `lines` holds only disrupted lines; add `good_service: [names]`.
    `tools/travel_watch.py` already filters on `disrupted`, so it is unaffected.
  - `tools/flights.py`: each flight gains `disrupted: bool`. Move travel_watch's rule (HEAD
    :250: either leg `delayed`, or status cancelled/canceled/diverted) into
    `flights.is_disrupted(f)` so the rule has one home. travel_watch calls it. Details are kept,
    because "which terminal?" is still a fair question.
  - **Throttle:** a module-level lock plus a `time.monotonic()` stamp. Sleep until 1.05 s have
    passed since the last request. It is per process: two processes (the server and a scheduler
    unit) can still collide, so the existing 429 message stays.
  - Update both schema descriptions.
- **Files:** `tools/tfl_status.py`, `tools/flights.py` and `tools/travel_watch.py` (Amber).
  Logistics text in the closing round (C6).
- **Tests:** offline, with `requests.get` stubbed:
  1. a mixed TfL result keeps only disrupted lines and names the good ones;
  2. `is_disrupted` matches the old travel_watch rule on its four cases, including an early
     arrival being not disrupted;
  3. two back-to-back flight calls sleep for the remainder. Stub `time.sleep` and
     `time.monotonic`; never sleep for real.

  Re-run `tests/test_unattended_job_failures.py` and `tests/test_scheduler_gates.py`.
- **Cost:** 0 tokens. At most 1 s of latency, only on a second flight check within a second.
  Persistent state: the in-process stamp only, which dies with the process.

### M19 — a quality event on an "enjoy …" reply
- **What a user would notice:** nothing in the reply, since detection is only that. When "Enjoy the
  museum" slips through, it is counted, and a count is what can prove the rule is or is not
  holding.
- **Mechanism:**
  - **The list:** a new `config/modules/filler_phrases.yaml`, a list of sentence-start patterns:
    `enjoy (the|your|it|yourself)`, `have a (great|good|lovely|wonderful) time`,
    `have fun`, `hope it goes well`. The comment says the rule lives at `synthesizer.md:101`;
    this is only its detector's list.
  - **The detector:** `tools/reply_checks.py` `check_filler(reply) -> str | None`. It matches only
    at a sentence start, because "you'd enjoy the quieter route" is advice, not filler. It writes
    at most one `FILLER_PHRASE` event per reply (detail: the sentence, ≤120 characters) and
    re-reads the yaml when its mtime changes.
  - **Called** beside `check_false_action_claims(visible)` on both twins (HEAD :7967 and :8430).
  - **Register** `FILLER_PHRASE` in `scripts/sync_dev_backlog.py` `MACHINE_TYPES` and its label
    map. An unregistered type is silently discarded, which is the file's own lesson.
- **Where the phrases live now:** `synthesizer.md:101` (three examples) and, by the agent-files
  rule's own account, `config/personas/mike.md` ("never say 'enjoy'", a deviation, VM-only). Both
  are unchanged.
- **Files:** `config/modules/filler_phrases.yaml` (new); `tools/reply_checks.py` (new);
  `core/orchestrator.py`; `scripts/sync_dev_backlog.py` (all Amber).
- **Tests:**
  1. "Enjoy the museum." fires;
  2. "You'd enjoy the quieter route." does not;
  3. one event for two matches in one reply;
  4. the reply text is unchanged;
  5. `tests/test_quality_event_reconciliation.py` passes with the new type.
- **Cost:** 0 tokens. Machine-log volume at the observed rate (×2 so far).

---

## 2. Red edits — OPENING round (before any code)

Final. Every "Current" below was checked character for character against HEAD `8ef2edf`. Apply
verbatim. O9 is an Amber module file: same round, no prompt. None of these depends on code this
stage builds.

**O1 — `config/agents/logistics.md` :80-81 (#7)**
Current:
> **Call `record_horizon_item` once per finding, as you find them.** This is the channel; the
> output block below is a summary of what you filed, not the delivery.

Replace with:
> **Call `record_horizon_item` once per finding, as you find them.** This is the channel to rely
> on; the output line below is a second copy.

**O1b — `config/agents/logistics.md` :99-102 (#7)**
Current:
> Also include what you filed as `HORIZON_ITEMS` in your output block, as a **JSON array**, so
> the Synthesizer can see the shape of what you found. Omit the line if there are none. The tool
> call is what counts: a finding filed by tool and missing from the block is fine; a finding in
> the block that you never filed will not reach anyone.

Replace with:
> Also list what you found on a `HORIZON_ITEMS:` line in your output block — one line, a **JSON
> array** — and omit it if there are none. Code files that line too, and the record keeps one
> copy of each finding, so a finding in both places is filed once. A line that is not valid JSON
> is lost, which is why the tool call comes first.

*Reason:* both sentences were false (the line is filed by code and never reaches the Synthesizer).
Both channels stay (D5).

**O2 — `config/agents/recreation_hobbies.md` :138 (§ 2b.5)**
Current:
> **Your entire response must be a single JSON object. No prose. No preamble. No explanation. Begin your response with `{` and end with `}`.**

Replace with:
> **Your response is a single JSON object — no prose, no preamble, no explanation — beginning with `{`. After its closing `}` come only the `HORIZON_ITEMS:` and `WISDOM_PROPOSAL:` lines, when you have them.**

*Reason:* the file asks for both. Today's parsers match the line form (`NAME:` and then the
bracket), so the lines go after the object. This stage's code also accepts a
`"HORIZON_ITEMS"` key inside it, as a safety net, not as the instructed form.

**O3 — `config/agents/recreation_hobbies.md` :240 (#11; both channels, ruling 11)**
Current (the indented continuation under `read_intake_queue`, two-space indent):
> **An item the user is plausibly looking forward to is not just filed — it is surfaced ready.** A concert they have tickets for, an event by an artist or group they follow, a plan taking shape: put it in `follow_up` with what would make it actually happen, and flag `CONSULT_NEEDED: logistics` for the practical legs — getting there, parking or transit, food around it, calendar fit — and note when others may be going, so the Synthesizer can raise it once, as a plan-shaped item rather than a bare notice.

Replace with (same two-space indent; the first sentence and the `follow_up` route are unchanged,
and one sentence is appended):
> **An item the user is plausibly looking forward to is not just filed — it is surfaced ready.** A concert they have tickets for, an event by an artist or group they follow, a plan taking shape: put it in `follow_up` with what would make it actually happen, and flag `CONSULT_NEEDED: logistics` for the practical legs — getting there, parking or transit, food around it, calendar fit — and note when others may be going, so the Synthesizer can raise it once, as a plan-shaped item rather than a bare notice. Also put it on a `HORIZON_ITEMS:` line after your JSON — one line, a JSON array of `{"title", "date", "venue", "kind", "detail", "precursor", "precursor_by"}`: `date` and `precursor_by` are `YYYY-MM-DD` or `""`, never invented; `kind` is `event`, `booking` or `opportunity`; `detail` is one sentence of what would make it happen; `precursor` is what must happen first (tickets bought, travel booked) or `""`. Code files it, so it is raised once, and early when its precursor falls due.

**O4 — `config/agents/finance.md` :28 (§ 2b.6)**
Current:
> This is a sensitive-tier domain. All financial data stays local. No cloud routing.

Replace with: *(delete the line and the blank line after it)*

*Reason:* false under the VM amendment, and it narrates routing to a model that can do nothing
with it.

**O5 — `config/agents/finance.md` :79 (#23)**
Current (fragment):
> Before opening one, check `list_tasks` — something closed recently is refused rather than re-filed, and that refusal is correct.

Replace with:
> Something closed recently is refused rather than re-filed, and that refusal is correct.

**O6 — `config/agents/research_agent.md` :70-78 (#24)**
Current:
> Synthesizer controls the `complexity` hint for every call:
>
> - **quick** — direct answer; 1–3 sentences. Apply currency checks and professional-review notes where relevant.
> - **deep** — synthesis, multi-angle analysis, contested topics, nuanced explanation, background for a significant decision. Take the space the answer needs.
> - **intensive** — structured comparison across multiple options, comprehensive literature synthesis, or long-form analytical output. Use tables, ranked lists, or multi-section format as appropriate to the query.
>
> When no hint is provided, judge by the nature of the query.
>
> Flag `RESEARCH_INTENSIVE` when a query arrives as `deep` but warrants `intensive` treatment — Synthesizer decides whether to re-call at higher complexity.

Replace with:
> You are not told how deep to go — judge it from the query:
>
> - **A direct lookup** — 1–3 sentences. Apply currency checks and professional-review notes where relevant.
> - **Synthesis, contested topics, nuanced explanation, background for a significant decision** — take the space the answer needs.
> - **A structured comparison across options, or a literature synthesis** — tables, ranked lists or sections as the query needs.
>
> *(Planned, not built: an `intensive` tier the Synthesizer could request, and a `RESEARCH_INTENSIVE` flag to ask for it.)*

**O7 — `config/agents/research_agent.md` :101 (#24)**
Current:
> - **RESEARCH_INTENSIVE** — query was called as `deep` but warrants `intensive` treatment; Synthesizer should decide whether to re-call at higher complexity

Replace with: *(delete the bullet; it is recorded as planned in O6)*

**O8 — `config/agents/synthesizer.md` :123 (#24)**
Current:
> 4. **Set the complexity hint explicitly.** Pass `quick`, `deep`, or `intensive` — don't leave Research to guess. Mismatch wastes tokens or underserves the query.

Replace with:
> 4. **Say in the query how much you need** — a one-line fact, an explanation, or a comparison across options. Research sees only the query; `complexity` (`quick` for a lookup, `deep` for synthesis) is not passed to it.

**O9 — `config/modules/synthesizer_scheduled_sessions.md` :31 (§ 2b.1, Amber)**
Current:
> 1. **Open** — one question first: "How are you feeling this morning?" Follow any thread before moving on.

Replace with:
> 1. **Open** — on the one thing that matters most this morning, as above. Follow any thread before moving on.

*(O10 and O11 moved to the closing round as C7 and C8 — review S3.)*

**O12 — the same paragraph in six files (§ 2b.4):** `finance.md`, `learning_growth.md`,
`relationships.md`, `physical_health.md`, `work_vocation.md` and `recreation_hobbies.md`, each
under `## A newly stated goal`.
Current:
> **When your dispatch opens with `NEW_GOAL:`, ask before you plan.** A goal stated in one
> sentence has a target, a constraint, a deadline and a reason underneath it, and you will
> support it badly without them. Ask two or three questions **only your domain would think
> to ask** — not generic ones — and record what you learn with `write_agent_config` so the
> planning survives the session.
>
> **Do not produce a plan on the first turn.** A plan built on the one sentence is the
> failure this exists to prevent: it looks like help, it is acted on, and it is aimed at a
> goal nobody checked the shape of.

Replace with:
> **When your dispatch opens with `NEW_GOAL:`, return questions, not a plan.** A goal stated in
> one sentence has a target, a constraint, a deadline and a reason underneath it. Return the one
> or two questions **only your domain would think to ask** — not generic ones. The Synthesizer
> decides which, if any, the user hears now; the rest become details of the goal's plan. Record
> what you learn with `write_agent_config` so it survives the session. A plan built on the one
> sentence looks like help and is aimed at a goal nobody checked the shape of.

*The O12 paragraph is byte-identical in all six files at HEAD (same checksum). Their HEAD lines:
finance :204, learning_growth :195, physical_health :184, recreation_hobbies :226,
work_vocation :192, relationships :299.*

**Opening-round count: 15 Red edit calls across 7 agent files, plus 1 Amber edit.**
- Red:
  - logistics ×2 (O1, O1b);
  - recreation ×2 (O2, O3);
  - finance ×2 (O4, O5);
  - research_agent ×2 (O6, O7);
  - synthesizer ×1 (O8);
  - O12 ×6, one per file. Recreation's, Finance's and the four others are separate edit calls.
- Amber: O9.

**Mike's to make (Denied):**
- the "how are you feeling" morning opening, if `config/personas/mike.md` or
  `config/personas/mike/scheduler.yaml` still has it;
- after the closing round's D12 text is live on the VM, any task-length "ask" or "estimate" line
  in those files.

`scripts/check_rule_overlap.py --persona mike` on the VM finds both.

---

## 3. Red edits — CLOSING round (after code)

Final against HEAD `8ef2edf`. Applied after this stage's code is built and tested. Line numbers
will have moved by then: anchor on the quoted text, which was checked at HEAD.

**C1 — `synthesizer.md`, insert a new paragraph after the first paragraph of
`## Multi-round specialist chains`** (HEAD :139, the paragraph opening "You may need more
information…") (#19):
> **FROM THE SPECIALISTS**, when present, lists what the specialists asked for this turn — a consult, a lookup, and at most one profile question (possibly one held from an earlier turn). Each is a request, not an instruction: a consult or lookup is a `run_subagent` call you make only if it would change your answer, and it counts toward the round limit; ask the profile question only if it fits this turn.

**C2 — `synthesizer.md` :412 (M5).** Current fragment:
> Include all existing preferences in the content when updating a section — the write replaces the whole section.

Replace with:
> To add a preference, pass only the new one with `mode: "add"` — the rest of the section is kept. To change or remove one, pass the whole section as it should read (the default, `replace`).

**C3 — `coordinator.md` :235 — not edited (revised).** With the scrub refusing rather than
rewriting (review L6), code no longer carries the identifier half of the rule. It only enforces
it. Both agents still write Research queries, so both keep the rule. § 2b.3 is resolved as
**two writers, one rule, enforced in one place in code**. Merging the text was rejected: the
Coordinator never sees `synthesizer.md`.

**C4 — `synthesizer.md` :120 (#17).** Current fragment:
> These are yours to hold and interpret; Research doesn't need them and shouldn't have them.

Replace with:
> These are yours to hold and interpret; Research doesn't need them and shouldn't have them. A query carrying the full name of someone the user knows, or the user's own address or contact details, is refused before it leaves — a reply starting `refused` says what to take out; ask again without it.

**C5 — `logistics.md` :302 and `recreation_hobbies.md` :245 (#25).** The same fragment in both:
> pass `at` (when the user would arrive) and never suggest a result whose `open_at_time` is false.

Replace with:
> pass `at` (when the user would arrive); anything closed then comes back under `closed_then` — never suggest one of those.

**C6 — `logistics.md` :303-304 (M18).**
- TfL fragment, current:
  > Only worth surfacing when something comes back disrupted; a clean "Good Service" on everything checked isn't worth a message.

  Replace with:
  > Only disrupted lines come back; the rest are named under `good_service`, which needs no message.
- Flight fragment, current:
  > **Rate-limited to 1 request/second** — call once per flight, not repeatedly.

  Replace with:
  > Call once per flight.

  Keep "only say something if the flight is delayed, cancelled, or otherwise off schedule", which
  is judgement; `disrupted` is the evidence for it.

**C7 — `config/agents/synthesizer.md` :395 (D12, the one home; moved from the opening round,
review S3).** Applied only once the `length_ask()` string change (§ 1, D12) is built and tested.
Current (fragment inside the `open_task` bullet):
> Every task should carry how long it takes (`minutes`) so it can be placed in a day: when one has none, ask once in passing ("how long are your workouts, usually?") and record the answer with `set_minutes` as `stated`; if they don't say, record your own estimate as `estimated` — never present a guess as their figure.

Replace with:
> Every task should carry how long it takes (`minutes`) so it can be placed in a day. When one has none, estimate it and record it with `set_minutes` as `estimated`, without announcing it. When the user corrects a length or says how long something took, record that as `stated` — that is the evidence that updates an estimate. Ask only when you have no basis for a guess, once, in passing ("how long are your workouts, usually?"). Never present a guess as their figure.

**C8 — `config/modules/synthesizer_day_plan.md` :11 and :36 (D12, Amber, two edits).**
Current :11:
> **Say a task length you estimated by recording it** (`set_minutes`, `estimated`), not by announcing it. **"Takes the user's own time"** is said once per task — when the plan says it was already explained, it is not said again.

Replace with:
> **"Takes the user's own time"** is said once per task — when the plan says it was already explained, it is not said again.

Current :36:
> - How long a task takes. When the plan names one with no length on file, ask once, in passing, and record it with `set_minutes` as `stated`. Ask about no task the plan has not named.

Replace with: *(delete the bullet; the rule's home is the task-ledger bullet in `synthesizer.md`)*

**Not edited, with reasons:**
1. `tone_profiler.md` § Only record what recurs. Code is the backstop. The model's own filtering
   keeps one-offs from using up the 6-item cap before validation, so the text still earns its
   place.
2. `synthesizer.md:101` ("enjoy"). It is the rule; M19 only detects it.
3. Specialists' "The Coordinator or Synthesizer will decide" in `CONSULT_NEEDED` definitions. It
   is slightly inaccurate (the Coordinator never sees specialist output) but harmless; not in
   scope.

**Closing-round count: 8 Red edit calls, plus 2 Amber.**
- Red: C1, C2, C4 and C7 (synthesizer); C5 ×2 (logistics, recreation); C6 ×2 (logistics).
- Amber: C8 ×2.

---

## 4. Builder brief

Model: Opus 5.5 (Amber code with a privacy-enforcement piece, #17). Review: Fable 5.1.

You are building Stage 5 Amber code in a worktree from HEAD. That HEAD should include Stages 2–4;
anchor on function names, not line numbers. Write nothing in `config/agents/`, the routing files,
`config/modules/synthesizer_*.md` or `core/{router,persona,scheduler,spend_guard}.py`. Commit
nothing. No real names in code, comments or config ("Mike" alone is OK; tests are exempt).
Offline tests only: stub every network call, model call and clock.

Build, in this order:
1. **`tools/lookup_guard.py`** (#17; one identifier reader, Revision 2):
   - add `_own_identifiers(persona)`, which raises `_Unreadable` on a profile read error;
   - add `check_research(query, persona) -> str | None`. It reuses `_full_names` + `_names_in`
     as they are, then the normalised own-identifier match. It does **not** apply `check()`'s
     pattern or figure refusals;
   - add `RESEARCH_REFUSED = "refused before sending:"`;
   - move the existing refund block into a helper. In `lookup_public_fact`, an answer starting
     with `RESEARCH_REFUSED` is refunded and returned unwrapped.
   - Then, in `_run_single_agent`'s `research_agent` branch, before any provider call, return the
     refusal on a hit or on `_Unreadable`. The trace carries the kind only.
   - No `tools/research_scrub.py`; no `tools/profile.py` change.
2. **`tools/specialist_requests.py`** (#19), with `lift()` and `commit_rotation()`, plus calls on
   both twins after `_drop_unprompted_clinical_flags`:
   - build `veto_text` before the lift and pass it to `_signoff_skip` / `_signoff_note`;
   - the body stops only at `KNOWN_TOKENS` (generated from the agent files' flag bullets, the
     output-section labels and the clinical tokens), with the drift-guard test;
   - never lift a flag whose body would hold a clinical token;
   - no `CLARIFICATION_NEEDED`;
   - `lift()` reads the `PROFILE_GAP` queue (`persona_data_dir()/specialist_requests.json`,
     0600, 7-day expiry, cap 10). `commit_rotation()` writes it, called only after the sign-off
     skip decision when the Synthesizer runs. Neither is called on a nudge or with empty
     outputs;
   - the block goes before `COORDINATOR ROUTING PACKAGE:`.
3. **`_file_horizon_items`** (#11):
   - also accept the `"HORIZON_ITEMS": [...]` key form, stripping it with one adjacent comma;
   - a `JSONDecodeError` in either form writes `HORIZON_BLOCK_UNPARSED` (agent; first 300
     characters);
   - register the type in `scripts/sync_dev_backlog.py`.
4. **`tools/tone.py`** (#21): validation inside `_parse_profile(raw, sample, contact)`, before
   truncation:
   - the other-person names exclude every name word of the profiled contact and of the user;
   - they match case-sensitively, only against capitalised tokens;
   - organisation contacts are skipped (`lookup_guard._ORG_TYPES`);
   - the stoplist of name-words that are also common words is never treated as a name.

   `_extract` passes the sample and the profiled record.
5. **`tools/places.py`** (#25): the `places` / `closed_then` split when `at` is given; schema
   text.
6. **`tools/persona.py`** (M5): `mode`, default `"replace"`, `"add"` explicit; `mode` in
   `args`; the lambda replacement; schema text.
7. **M18:**
   - `tools/tfl_status.py`: disrupted-only `lines` + `good_service`;
   - `tools/flights.py`: `is_disrupted()`, the per-flight `disrupted` flag, the throttle;
   - `tools/travel_watch.py` uses `is_disrupted`;
   - schema text in both tools.
8. **M19:**
   - `config/modules/filler_phrases.yaml`;
   - `tools/reply_checks.py` `check_filler`;
   - calls beside `check_false_action_claims` on both twins;
   - register `FILLER_PHRASE` in `scripts/sync_dev_backlog.py` (`MACHINE_TYPES` + labels).
9. **D12:** the `length_ask()` f-string and docstring in `tools/day_plan.py` (HEAD :3072,
   :3098-3100). The driver applies C7 and C8 only after this passes its tests.

#16 is not in this stage (Stage 4).

Tests to write are listed per item in § 1. Run the suites in § 6. Return the diff, the test
output and anything you could not do.

---

## 5. Collision notes

*Re-checked for Revision 2 against the working tree on HEAD `8ef2edf`. Other chats now have
uncommitted lines in several Stage 5 files. Plan against HEAD; at merge time the standing rule
applies to every file below: if it still carries lines you did not write, stop and ask.*

1. **`core/orchestrator.py`** — other chats' uncommitted hunks (HEAD line numbers):
   - `session_kind` (:365-377);
   - `register_tools` (:1521, :1593, :1699);
   - `_horizon_block` (:6662, :6694-6695);
   - `_close_turn_bookkeeping` (:7680);
   - both twins' `_horizon_block(...)` call (:7935, :8228; adds `user_turn=`).

   Stage 5's hunks, and how close they sit:
   - **adjacent (≤5 lines):** the package-head insertion before `COORDINATOR ROUTING PACKAGE:`
     (:7938, :8231) sits 3 lines below their `_horizon_block` call edit (:7935, :8228). That is
     the likeliest textual conflict; resolve it by hand.
   - **near (≤40 lines):**
     - `_file_horizon_items` (:6582-6630), about 30 lines above their `_horizon_block` hunk;
     - the `veto_text`, `lift()` and `commit_rotation()` changes (:7883-7913, :8182-8208),
       about 25 lines above their twin edits;
     - `check_filler` beside `check_false_action_claims` (:7967, :8430), about 30 lines below.
   - **clear:** `_run_single_agent`'s research branch (:5702).
2. **`tools/obligations.py`** (their hunks at :1371, :1913, :2999, :3429, :4141): Stage 5 does
   not touch this file.
3. **`tools/day_plan.py`** (their hunk at :4279, `refresh_tick`): D12's `length_ask()` change
   (:3072-3100) is about 1,200 lines away. It is still a file with another chat's lines, so it is
   stop-and-ask at merge.
4. **`config/agents/synthesizer.md`** (one uncommitted line added after HEAD :409, a "weekly
   conversation" bullet): it carries no Stage 5 anchor, but every Stage 5 Synthesizer edit is in
   this file:
   - O8 (:123), in the opening round;
   - C1 (after :139), C2 (`write_persona`, :412 at HEAD and :413 in the working tree), C4 (:120)
     and C7 (:395), in the closing round.

   **Stop-and-ask before O8 if the line is still uncommitted.** C2's anchor is the quoted
   fragment, not the line number.
5. **`config/modules/synthesizer_scheduled_sessions.md`** (their hunk at :50-56, the weekly
   review): O9 is at :31, clear of it, but the file carries their lines. Stop-and-ask before O9.
6. **`tools/lookup_guard.py`:** committed, clean, and now **edited by this stage** (Revision 2:
   the single identifier reader). It is the ranking chat's file, so check `git log` for their
   newer commits before the builder starts.
7. **Routing files:** one uncommitted synthesizer-line change in `routing.yaml` (:55) and its
   twin. Stage 5 makes no routing edit.
8. **The WhatsApp chat** (`core/server.py`, `tools/intake_whatsapp.py`, Android, two tests):
   not touched.
9. Stages 2–4 also edit the twins and `_run_single_agent`. The merge order is 2 → 3 → 4 → 5, so
   build from the post-Stage-4 HEAD and expect every number above to have moved.

---

## 6. Test suites to re-run

1. `tests/test_places.py`, `tests/test_places_open_at.py`
2. `tests/test_tone_own_copies.py` + the new tone validation tests
3. `tests/test_persona_write_gate.py`, `tests/test_confirmation_gate.py`
4. `tests/test_horizon_ledger.py` (+ the line form, the key form, and the unparsed event)
5. `tests/test_false_action_claim.py`, `tests/test_false_claim_phrasings.py` (the neighbouring
   call sites)
6. `tests/test_quality_event_reconciliation.py` (`FILLER_PHRASE`, `HORIZON_BLOCK_UNPARSED`)
7. `tests/test_unattended_job_failures.py`, `tests/test_scheduler_gates.py` (travel_watch)
8. `tests/test_signoff.py` (the veto on unmodified text), `tests/test_subagent_depth.py`
9. `tests/run_b1_redteam.py --suite deputy` (check 6 after #19's parser)
10. `tests/test_day_plan_engine.py`, `test_day_plan_wiring.py`, `test_day_plan_round2.py`,
    `test_day_plan_ledger.py` (the `length_ask` text)
11. `tests/test_ranking_v2.py` (the existing `lookup_guard` / `lookup_public_fact` tests; `lookup_guard.py` is now edited)
12. the new test files: research check, specialist requests (incl. token order, acronyms, the drift guard, rotation and consumption),
    reply checks, flights/TfL, tone validation
13. `python3 scripts/check_agent_tools.py` (exit 0) and `python3 scripts/check_claude_md_claims.py`
14. **A4 live: not planned** (ruled 19). $0.

**Budget.**
- *Build:* about 170k tokens across 9 new or changed modules (`lookup_guard.py` edited in place of a new scrub module) and their tests (#16 left for
  Stage 4; the rotation queue and the key-form parser added), plus about 60k Fable diff review
  and about 25k for the narrow Fable re-check of this revision. The driver's Red work is 23 Red
  edit calls and 3 Amber.
- *Run:* 0 tokens. A refused Research query costs its writer one retry turn (Flash or Pro,
  under $0.001), which is rare by construction. M18 adds ≤1 s on a second flight check within a
  second.
- *Ancillary:* the machine log gains `FILLER_PHRASE` and `HORIZON_BLOCK_UNPARSED` events at
  their real rates.
- *Unseen:* none that bills. One new persistent file, the per-persona `PROFILE_GAP` queue (bytes;
  7-day expiry, cap 10; survives a restart harmlessly; no money, so no meter). The throttle stamp
  lives in memory and dies with the process.
- *Deploy:* yes (core/, tools/, config/). The driver hands the list to Mike.

**Live checks for Mike's deploy list:**
1. Ask a research question that includes a contact's full name. The reply answers without it,
   and the trace shows `[RESEARCH] refused: the full name of someone the user knows` followed by
   a second, clean Research call.
2. Tell Metatron a second style preference. The first is still in the persona file.
3. A morning brief opens on one thing, not "how are you feeling".
4. A new task gets a length with no question asked.
5. After a Recreation find (a concert email), the horizon record holds it, and the reply raises
   it once.

---

## Build-time amendments (driver, 2026-11-23, from the Fable confirm of Revision 2)

The confirm found nothing structural; rows 2, 3, 4 and 6 are closed. The builder applies these
fixes. Findings 2 and 3 are also **defects in the live `lookup_guard`** (`129f3fb`, deployed):
the fix changes the public-fact lookup too, and the commit message says so.

1. **Contacts' email, phone and address are checked too.** `check_research` reads each contact's
   stored email, phone and address from the CRM, the same way it reads the user's own, with the
   same normalisation. Tests cover a directive carrying a contact's email, phone and street.
2. **No dead organisation skip.** The CRM's `relationship_type` has no organisation value, so
   `_ORG_TYPES` never matches. Remove the skip. Every contact is checked, and the refusal names
   the matched contact so the writer can rephrase ("a school office" rather than the saved name).
   Accepted cost: an occasional rephrase for a contact saved under an organisation-like name.
   The tone check (#21) instead skips a candidate that is not a capitalised token **in the
   sample**, which is exact for that check. Tests use real `relationship_type` values only.
3. **`referred_to_as` read per alias.** Each alias is its own candidate. An alias counts as a
   name only when every token in it is capitalised ("Aunt Ruth" yes, "my wife" / "the dentist"
   no). Tests cover `['my wife']`, `['the dentist']` and a list holding a full-name alias.
4. **Phone and postcode normalisation is not UK-only.** Phones compare on digits only, keeping
   the last 9 (national number, any country code). A UK-shaped postcode uses the UK pattern; any
   other stored postcode matches as its whitespace- and case-normalised string. Tests include a
   non-UK number and postcode.
