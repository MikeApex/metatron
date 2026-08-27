# Handoff — the tool stops re-asking which Bill (2026-08-27)

Worker 2 of the parallel attack run. Branch: the worktree
`agent-a31094e5f8a3fa35c`. Nothing deployed; nothing pushed.

---

## What a user would notice, by commit

| Commit | What changes for the user |
|---|---|
| *Stop asking which Bill once the user has already said which Bill* (`tools/crm.py`) | Answering "which Bill?" now settles it. The next time that name is spoken, the tool uses the person the user named instead of asking again. Saying "no, the other one" replaces the answer. |
| *Test that a settled name stays settled, and that a stale memory asks again* (`tests/test_contact_resolution_memory.py`) | No user-visible change. Pins the guarantee that a remembered answer can never be the reason something lands on the wrong person. |
| *this handoff* | None. |

**What did not change:** the question itself. The tool still refuses to guess
the first time a name reaches several people, and still refuses whenever the
remembered answer no longer fits.

---

## Backlog items to close, and the evidence

**[DB-0818-05] — the tool asks which Bill, then asks again about the same Bill.**
The dangerous half (writing to the wrong Bill) closed 2026-08-18. This is the
remaining half, and it is now built.

Evidence: `python3 tests/test_contact_resolution_memory.py` — **16 passed, 0
failed**. The two that are the item itself:

- *read_contact does not ask again once the user has answered*
- *log_interaction does not ask again either, and files against the right Bill*

Regression, all unchanged and green: `test_contact_disambiguation.py` (all
checks pass), `test_crm_dedup_guards.py` (18/18), `test_crm_merge_guard.py`
(30/30), `test_crm_placeholders.py` (17/17), `test_contact_dedup_gate.py`
(21/21), `test_contacts_import.py` (21/21),
`test_check_agent_tools_personas.py` (PASS).

**Close condition — one live confirmation.** The unit tests exercise the tool
functions directly; what they cannot prove is that the model actually sends
`name` back alongside `contact_id` on the second call, which is what records the
answer. **The test Mike can run:** name an ambiguous contact, answer the
question, then name them the same way again in a later turn. Pass = the second
mention resolves without a second question. Fail = it asks again, and the cause
will be visible as an empty or missing
`data/personas/mike/crm/name_resolutions.json`.

---

## Must be carried by another owner

1. **`tools/` changes need Mike's VM deploy.** `./deploy.sh` is Denied and was
   not run. Until it is, this is dev-tree only and the live tool still re-asks.
2. **`DEV_BACKLOG.md` was not touched** — closing `[DB-0818-05]` and filing its
   evidence to `archive/backlog_closed_2026-08.md` belongs to the merging
   session, not to a parallel worker.
3. **A new data file appears in the persona tree on first use:**
   `data/personas/<persona>/crm/name_resolutions.json`, written `0600`. Created
   lazily — a persona that never disambiguates never gets one, and an existing
   persona with no such file behaves exactly as it did before (asserted in the
   tests). `data/personas/**` is Denied here, so nothing was pre-created.
   Storage cost is negligible: one small JSON object per persona, one entry per
   resolved reference, growing only on a genuine ambiguity. There is no
   expiry — an entry is superseded by a correction, never aged out, which is
   deliberate: a resolution that expired would resurrect the question this item
   exists to remove.
4. **Nothing was added to any agent file, and nothing needs to be.** A dedicated
   `resolve_contact_reference` tool was considered and rejected: a new tool is
   inert until it is granted in `config/agents/relationships.md`, which is Red.
   The capture rides on the existing `read_contact` / `log_interaction` calls
   instead. **If Mike would rather it were an explicit tool, that is a Red-tier
   edit and his call** — the recommendation is to leave it as is, because the
   implicit path needs no grant, no new instruction, and no per-agent rollout.
5. **A pre-existing matcher limit, deliberately not fixed here.**
   `_find_by_name` matches the `name` field only, so "Bill" does not reach a
   contact stored as "William Hart" with nickname "Bill". Widening it would drag
   every Bill toward every other Bill — the tension
   `tests/test_contact_disambiguation.py` exists to hold — so it is out of scope
   for this item. Recorded in the new test's fixture comment so a future
   widening does not silently change what these tests assert.
