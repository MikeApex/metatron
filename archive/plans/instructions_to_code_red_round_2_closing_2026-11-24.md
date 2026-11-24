# Instructions → code build — Red round 2 (closing), 2026-11-24

*Every edit that deletes or rewrites instruction text the new code now carries, for Mike's
approval. Exact current and replacement text is in each stage plan's § 3; edits are anchored on
quoted text, not line numbers. Agent files are Amber since 11-24 but are still edited only in the
main session.*

**Total: 52 edits across 12 files** (8 + 4 + 30 + 10). Held back by Mike's no-live-runs ruling and the unbuilt
4f, and **not in this round**:
- Stage 3 X1–X4, Physical Health's own medication check;
- Stage 4 C20–C22, Physical Health setting its sleep, energy and food flags;
- Stage 4 C33, Logistics' quick-mode section;
- Stage 2 D1–D2, the Coordinator's clarification hold, which ships in shadow.

In each of these, the instruction and the code both stay, and the code only adds.

## Stage 2 — session shape (8; `…stage2…` § 3)
1. **The Coordinator's whole-person rule now covers only greetings the user types.** The
   scheduled brief and close get both specialists from code. C1, `coordinator.md`.
2. **A routing miss is recorded as a `routing_miss` key, not by a tool call.** C2–C6,
   `synthesizer.md` (5 edits, including the new field definition).
3. **The Synthesizer's round limit is described as code now enforces it.** "Say what you couldn't
   check" replaces a flag nothing read. C7–C8, `synthesizer.md`.

## Stage 3 — Finance (4; `…stage3…` § 3)
4. **Finance reads code's period figures, adds only this turn's transactions, and stops storing
   its own budget verdict.** X6, X7, X8 (nothing reads `budget_status`, re-checked), `finance.md`.
5. **Finance knows transaction ids:** correct by id; to correct an id-less entry, use
   `{"id": <new>, "replaces": <old>}` (the code's route); remove by `{"id", "remove": true}`.
   X9, `finance.md`, worded to match the built code.

## Stage 4 — evidence handed in (30; `…stage4…` § 3, minus C20–C22 and C33)
6. **"Call `read_agent_config` / `list_tasks` / the calendar at session start" becomes "start
   from what is handed to you"** in Logistics, Relationships, Work & Vocation, Recreation,
   Physical Health (data source only), Mental Wellbeing, Learning & Growth and Finance. C1, C2,
   C8, C15, C16, C18, C24, C26, C28 (first hunk) and C29.
7. **Logistics:** pending confirmations live as ledger `waiting` rows (C3–C5); code writes its log
   entry (C6); `[VERIFY]` is re-checked for it on its own calendar read (C7).
8. **Relationships:** named people arrive resolved (C9); overdue and dates lists are handed over
   (C10); the stored tone shape arrives with the record (C11–C12); it never reads details back,
   because the reply does (C13); on-file context about the recipient arrives (C14).
9. **Work & Vocation** uses today's prefetched health and wellbeing fields for its flow
   cross-check (C17).
10. **Gap flags cite the counted evidence:** LEISURE_GAP/HOBBY_LAPSE (C19), SLEEP_MISSING/
    EXERCISE_GAP (C23), PRACTICE_LAPSE/SLEEP_CONCERN (C27), LEARNING_GAP (C28), and cessation as
    "last logged use", never a streak (C25).
11. **Pattern Miner** (C30, **reworded**): "**On the weekly run**, already in your input: the two
    latest reports, the wisdom store, the logs per window, the duplicate groups and your baseline
    row — use them, and don't fetch them again; code writes the report and patterns from your
    reply. On any other run, call the tools as before." C31: on the weekly run the baseline row is
    handed over.
12. **Held items** (C32, **reworded** after amendment 1 was reversed), `synthesizer.md:265`, plus
    the `held_items` field definition at `:258`: "Each held item shows how long it has been held.
    Re-send the full held list each turn. Leave an item out once you have raised it, or when it is
    no longer worth holding. Past a week, surface it or drop it. Omit the key only to mean no
    change."

## Stage 5 — one channel per signal (10; `…stage5…` § 3)
13. **The Synthesizer is told what the FROM THE SPECIALISTS block is** (C1); **how to add one
    preference without re-typing the rest** (C2, M5); **what a `refused` research reply means**
    (C4, adding: "if it says the user's records could not be read, answer without the lookup").
14. **Closed venues come back under `closed_then`** (C5, Logistics and Recreation).
15. **Line and flight checks report disruptions only** (C6 ×2, Logistics).
16. **Task lengths: estimate and record, update on the user's word, ask only with no basis**,
    in one home (C7, `synthesizer.md`; C8 ×2, `synthesizer_day_plan.md`, Amber). This lands
    beside the built `length_ask()` change.

## After applying
`check_agent_tools` exits 0 and the claims check holds. Then **one Fable review of all the Red
diffs together** (both rounds), and the full test set again. Each cached specialist's prefix
shrinks a little; `_pad_for_vertex_cache` pads it, so the cache floor is unaffected (check after
deploy: turn-1 `cached_tokens` is non-zero).

## Mike's to make (Denied), once live on the VM
Remove any "How are you feeling this morning?" opening and any task-length ask/estimate line from
`config/personas/mike.md` and `config/personas/mike/scheduler.yaml`.
`scripts/check_rule_overlap.py --persona mike` on the VM finds them.
