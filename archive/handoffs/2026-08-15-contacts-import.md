# 2026-08-15 — Contacts import (DB-0810-17, pieces 2 & 3)

**Shipped:** `tools/contacts_import.py` (new) — `import_google_contacts(query="")` pulls via
`tools/google_contacts.py`'s `read_google_contacts` and writes/updates the CRM; `import_contacts_file(path, source_format="auto")`
parses vCard (`.vcf`, hand-rolled RFC 6350 parser — no new dependency) and CSV (stdlib `csv`,
tolerant header mapping covering Google/Outlook export shapes; unmapped columns land in `notes`,
never dropped). Both funnel through `_import_batch`, which dedups on identity (email → phone →
exact case-insensitive name) for idempotence, and otherwise leaves near-match surfacing to
`tools/crm.py`'s existing `write_contact`/`_dedup_candidates` — never calls `merge_contacts`
itself. `tools/crm.py` was read only, not edited.

**Tests:** `tests/test_contacts_import.py`, 17 tests, standalone runner (no pytest), all passing —
`python3 tests/test_contacts_import.py`. Covers creation, idempotent re-run (email match, phone
match, exact-name match), soft-match evidence surfacing (not auto-merge), CSV/vCard field mapping,
unmapped-column preservation, missing-file/bad-format errors. No live Google API calls —
`tools.google_contacts.read_google_contacts` is mocked.

**Backlog:** Close DB-0810-17 pieces 2 and 3. Piece 1 (registering `read_google_contacts` in
`register_tools()` + routing grants) is still open — explicitly not mine, coordinator/Red-tier.

**For the coordinator to register:** `tools.contacts_import.import_google_contacts` and
`tools.contacts_import.import_contacts_file`, with schemas `IMPORT_GOOGLE_CONTACTS_SCHEMA` and
`IMPORT_CONTACTS_FILE_SCHEMA` already defined at the bottom of the module. Both are sensitive-tier
(CRM data) — same routing posture as the existing CRM tools. `import_google_contacts` additionally
needs whatever grant `read_google_contacts` gets, since it's a runtime dependency, not just an
import-time one.

**For SESSION.md:** DB-0810-17 is now fully unblocked pending only the piece-1 registration; note
`tools/contacts_import.py` and its schemas as ready for wiring.

**qa_sweep:** 9/9 pass.
