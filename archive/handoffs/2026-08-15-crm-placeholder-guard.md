# 2026-08-15 — CRM placeholder guard, widened to phone/address/social/name

**Shipped:** `write_contact` in `tools/crm.py` now refuses known-placeholder values in
phone (NANP 555-0100/0199, UK Ofcom 07700 900xxx, sequential/all-zero numbers,
normalized against spaces/dashes/brackets/+/00 prefixes), address (bare "123 Main
Street"-class strings and anything containing "Anytown", as whole-field matches only),
social handles (`@username`/`@handle`/`@example`/`@yourname` etc., case-insensitive),
and name (`John Doe`/`Jane Doe`, checked on `name` and on `first_name + last_name`).
Same refuse-and-explain error shape as the existing email guard.

**Close [DB-0815-06]** (widened form) — evidence: `tests/test_crm_placeholders.py`,
17/17 passing, run directly (not just qa_sweep). Existing `tests/test_crm_dedup_guards.py`
still 18/18 — no regression to the email guard or dedup path.

**False-positive care:** address only blocks a *bare* placeholder string (no city/state
attached) or the literal word "Anytown" — `"123 Main Street, Springfield, IL 62704"`
passes. UK/NANP phone checks are scoped to the exact reserved sub-ranges, not the whole
prefix — `+44 7700 800123` and ordinary `555-xxxx` numbers pass. Name only blocks the
full "John Doe"/"Jane Doe" string — a real surname "Doe" alone passes. Verified in the
test file's "real-looking values must pass" cases.

**Not caught, by design:** a model-fabricated but plausible-looking phone/address/name
(not a known placeholder) — no source of truth exists to check against, per the backlog
item's stated limit.

**Shared-registry question:** recommend leaving the placeholder registries in
`tools/crm.py` for now, not extracting to a shared module. Only `tools/crm.py` currently
writes contact fields with this fabrication risk; `tools/mail.py`/`tools/agent_config.py`
guard different things (recipient identity, guarded keys) with different shapes, not the
same placeholder-domain problem. Extract when a second tool needs the *same* registries
(e.g. an address book import, a second write path for phone/social) — premature now would
add an abstraction with one caller.

**SESSION.md:** no changes made (out of manifest) — flag that [DB-0815-06] can be closed
(widened form) and this handoff + `tests/test_crm_placeholders.py` are the evidence.
