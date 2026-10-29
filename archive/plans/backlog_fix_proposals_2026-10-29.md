# Backlog fix proposals — 2026-10-29 (overdue checks + Inbox triage session)

Mike's instruction: put together proposals for every fix the session found, run the ones beyond a
single area by Fable, and execute. Each fix names the defect as the user sees it first.

**Budget (build):** F1–F4 ~120k Opus tokens in the coordinating window + one Fable review ~60k.
**Run cost:** F2 adds at most one speak-only Synthesizer round on a reply that would otherwise be
garbage — measured rate 1 in 52 turns since 10-26 (~$0.04–0.07 each, `spend_guard.yaml` prices);
F1, F3, F4 add none. **Ancillary / unseen:** none — nothing persistent is created.
**Model:** built here on Opus 5.5; Fable 5.1 reviews F2 and F4.

---

## F1 — Updating a contact's details can erase the rest of them `[DB-1029-02]` — single area

**Defect.** `write_contact` replaces `contact_info` wholesale on update (`tools/crm.py:1246`), so a
write carrying only `{"email": …}` drops phone, address and social handles. A contact holds one
`email`; on 09-07 Mike's "keep both addresses" ended with the work address filed under
`social.work_email`, and the reply said both were preserved.

**Change (`tools/crm.py`, `tools/mail.py`):**
1. On update, `contact_info` **merges per key** with what is stored; `social` merges per platform.
   An explicit `{}` still clears it (the documented "passing {} clears" contract).
2. A contact may hold several emails: `contact_info.other_emails` (list). When an update brings an
   `email` different from the stored one, the stored address moves into `other_emails` instead of
   being lost — Mike's rule: *preserve across categories unless told to remove or replace*. To drop
   an address the caller passes `other_emails` explicitly without it.
3. `_known_recipients()` (`tools/mail.py:689`) admits `other_emails` too, so a preserved work
   address is still sendable.
4. The checked-detail confirmation gate is unchanged: replacing a *verified* primary still asks.

**Test:** `tests/test_crm_contact_info_merge.py` — fails on the old code (phone lost; old email lost).

## F2 — A reply made of the model's own prompt text reached Mike `[DB-1026-01]` — reply path, Fable

**Defect.** 10-28 18:35: thinking ran to 7,865 of 8,192 tokens, the round ended `MAX_TOKENS`, and
the 323 tokens emitted (a fragment of the prompt's "ALREADY ASKED…" block) were delivered.

**Change (`core/orchestrator.py`):** in both native Gemini loops, a round that ends `MAX_TOKENS`
with **no function call** is treated as a reply that did not finish:
- **Non-streaming** (`_run_gemini_native_loop` — scheduled sessions, pushes): discard the text and
  run the existing `_final_reply_round()` (speak-only, its own user turn). Empty → `_NO_REPLY_LINE`.
- **Streaming** (`_run_gemini_native_stream`): the text is already on screen. Yield a sentinel the
  pipeline turns into the existing `[RETRACT_WITH]{replacement}` marker, replacing the shown text
  with the final-round reply (or `_NO_REPLY_LINE`).
- A `MAX_TOKENS` round that *did* request tools is left alone — the tools run and the loop
  continues as today.
Log `[reply_limits] reply cut at MAX_TOKENS — replaced`.

**Test:** stub client whose stream ends `MAX_TOKENS` with text; assert the fragment is not the
returned/final text in either path, and that a `STOP` round is untouched.

## F3 — A calendar that refused to answer is traced as a success `[DB-0910-02]` — single area

**Defect.** CalDAV failures return `{"error": "CalDAV request failed: 401 …"}`; `dispatch_tool`
JSON-encodes the dict, so neither `_TOOL_ERROR_PREFIX_RE` nor `_failed_tool_calls` (which checks
`startswith("Error")`) sees it — `ok: true`, no `[TOOL FAILURES]` marker to the Synthesizer.

**Change (`core/orchestrator.py`):** `dispatch_tool` marks `ok=False` when the tool returned a dict
with a non-empty `error` key (one place, before JSON encoding); `_failed_tool_calls` reads the
recorded `ok` flag as well as the `Error` prefix. 18 tool files share the `{"error": …}` shape, so
this corrects the trace for all of them.

**Test:** extend the existing tool-failure checks: a dict-error tool → `ok False`, listed by
`_failed_tool_calls`; a dict without `error` → ok.

## F4 — The Accountability Index calls nearly everything "indeterminate" `[DB-0827-09]` — two areas, Fable

**Defect.** 13 of 14 verdicts indeterminate. (a) Requests *to Metatron* are logged as intentions.
(b) An intention that is a still-open ledger task never reaches the join — `_find_obligation_match`
only reads closed work, and `accountability_items()` only emits closed work.

**Change:**
1. `tools/obligations.py` `accountability_items()` also emits open one-off tasks
   (`status: "open"`, `opened_at`). `tools/accountability.py` gains `_find_open_task_match()`; in
   `resolve_intention`, after no closed match and with the window closed, an intention matching an
   open task resolves **unfulfilled** ("matched open task … still not done after the window") —
   code answering what code can, before the gate.
2. **Red, `config/agents/diarist.md:34`** — add to the boundaries: *a request made to Metatron —
   look something up, check the inbox, change how it behaves, report a problem, set a reminder — is
   not an intention and is never logged with an `intention` key.*

**Test:** `tests/test_accountability.py` new cases — open matching task + closed window →
unfulfilled; open task + window still open → indeterminate "window still open"; closed task still
wins.

---

## Needs Mike before it can run

**F5 — Metatron saves a standing rule and then says it can't `[DB-1029-04]`.** The cause is the
VM-owned `config/personas/mike/self_development.md`: route 2 is *"anything about your judgement,
priorities, what you notice, or when you raise things"*, which covers every standing rule the wisdom
store holds. Proposed wording for route 1: *"…standing preferences on tone, length or follow-ups,
**and standing rules about people, timing or what to check — anything you can hold as a stored
preference or wisdom entry.** Store it and say it's saved."* And under route 2: *"Only if storing it
would not change what you do. If you have saved it this turn, it is route 1 — never say it needs a
change on your side."* **Denied tier and VM-owned:** needs Mike's explicit lift, then an edit on
the VM (pull first, never reconstruct on the Mac).

**F6 — Midday meal check-ins `[DB-1029-03]`.** Recommendation: a daily habit `Log meals and snacks`,
`every: day, times: 3`, created by Mike in the app — the day planner already nudges ledger habits
with Done / Not yet. No code. Alternative (code): a fixed planner check-in at ~13:00 and ~16:00; more
reliable, but it reintroduces the fixed check-ins step 2 just retired. Mike's choice.

**F7 — Suggestions that can't be acted on `[DB-0902-03]`.** `tools/places.py` already returns
`open_now` (`currentOpeningHours.openNow`). Gap: that is "open now", not "open when you'd get there",
and nothing requires the check before a venue is suggested. Proposal: return the day's opening
periods from Places, and require Logistics/Recreation to pass the suggestion time through it before
naming a venue (agent-file rule, Red, plus a field in `places.py`). Its own session.

**F8 — Tone from the mailbox (Mike's question on `[DB-0810-05]`).** Answered in chat; a change is
proposed there, not here.
