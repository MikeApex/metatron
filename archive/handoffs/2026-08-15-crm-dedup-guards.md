# Handoff — 2026-08-15 — CRM merge/dedup tooling, placeholder-email refusal, third-party-correction guard

**Shipped, commit `97b777c`** (`tools/crm.py`, `tools/profile.py`,
`tests/test_crm_dedup_guards.py`):

1. **`[DB-0815-07]` merge path** — `merge_contacts(keep_id, merge_id)` in
   `tools/crm.py` (~line 604): folds a duplicate into the surviving record,
   archives the loser to `data/personas/{persona}/archive/crm/` with a
   `merged_into` pointer, never deletes — same shape as
   `tools/wisdom.py::merge_wisdom_entries`. `read_contact` and
   `search_contacts` (`tools/crm.py:444`, `:604`) now follow that pointer, so
   an old id or an old (corrected-away) name keeps resolving.
2. **`[DB-0815-07]` dedup on write** — `write_contact` (`tools/crm.py:228`)
   now checks the new name against existing contacts via `_name_similarity`/
   `_dedup_candidates` (`tools/crm.py:67-221`, threshold `0.6`, same
   `difflib` approach as the file's own-identity checks) and returns any
   close match as evidence alongside the new id — it still creates the
   record; the calling agent decides whether to `merge_contacts`.
3. **`[DB-0815-06]` placeholder-email refusal** — `write_contact` refuses an
   email on an RFC 2606 reserved/placeholder domain (`example.com`, `.test`,
   `.invalid`, `localhost`, ...) outright (`tools/crm.py:284-293`), instead
   of persisting an invented address.
4. **`[DB-0815-05]` third-party-correction guard** — `write_profile`
   (`tools/profile.py:144`) refuses a `name`/`other` value that reads as a
   correction to someone else's contact record via
   `_third_party_correction_reason` (`tools/profile.py:122-172`). Narrow:
   needs subject+verb+"from...to" together, or (name field only) an
   implausibly long value ending like a sentence. Verified not to catch
   "Robert Smith Jr." or an ordinary "other" fact containing "from"/"to".

**Evidence:** `python3 tests/test_crm_dedup_guards.py` — 18/18 pass, covering
merge field-folding + archive + pointer-resolution by id and by name, the
Eva/Iva and Kathaleen/Kathleen near-miss surfacing, unrelated names not
flagged, `example.com`/`.test`/`.invalid`/`localhost` refused, a legitimate
address still writing, the exact recorded correction sentence refused in both
`name` and `other`, and ordinary name/other writes (including a "from...to"
sentence and a suffixed name) still succeeding. `tests/test_profile_language.py`
re-run clean (16/16), no regression.

**`./scripts/qa_sweep.sh --verbose`:** 8/9 checks pass (py-compile,
backlog-ids, dev-markers, claude-md-claims 43/43, deploy-lock, line ceilings
warn-only). The one failure — `project-log` drift between
`archive/PROJECT_LOG.md` and its fragments — **predates this session**
(confirmed via `git log -1 -- archive/PROJECT_LOG.md`, last touched by an
earlier commit) and that file is outside my manifest; not fixed here.

**Not done, flagged not silently skipped:** `merge_contacts` and its schema
(`MERGE_CONTACTS_SCHEMA`, `tools/crm.py` near end) are **not yet registered**
in `core/orchestrator.py`'s tool list (~line 500-567) — that file is outside
my manifest. Whoever owns `core/orchestrator.py` needs to add
`merge_contacts, MERGE_CONTACTS_SCHEMA` to the existing `from tools.crm
import (...)` block and the `schemas = [...]` list, same pattern already used
for `write_contact` etc. Until that lands, `merge_contacts` exists as a
function/schema but is not callable by an agent.

**For `SESSION.md`:** `[DB-0815-07]`, `[DB-0815-06]`, `[DB-0815-05]` all have
code + passing tests on this commit; `[DB-0815-07]`'s merge tool needs one
more step (orchestrator registration, above) before an agent can actually
call it.
