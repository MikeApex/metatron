### 2026-08-22 (ZDR opt-out submitted — answered as an individual, not as an entity) — `docs/INFRASTRUCTURE.md`, `DEV_BACKLOG.md`, `SESSION.md`, `archive/security/zdr_optout_form_answers_2026-08-21.md`, **not deployed**

**Mike submitted Google's abuse-monitoring opt-out form on 2026-08-22.** Decision expected by
~2026-09-05 (Google states ~2 weeks' review, plus 5–7 business days to allowlist if approved).
**It is not in force until granted** — the approval/rejection email to `diamond.mike@gmail.com` is
the only evidence that will exist, since `gcloud` reports no status for the exception. The status
row in `docs/INFRASTRUCTURE.md` § Vertex AI credentials records the submission and remains the
single authority.

**The form was never read by a session.** `WebFetch` is Denied and the 2026-08-20 per-occasion lift
had been reverted, so the answers were prepared blind from the terms evidence and then matched
field-by-field against the form text Mike pasted in. Rejected: re-lifting the deny to read a form
Mike was about to open anyway.

**Two judgement calls, both resolved toward accuracy over approval odds.**
1. *Organization Name / Website / business email are required and no entity exists.* Mike asked
   whether to use a placeholder or a defunct company. **Neither** — a dead website is the first
   thing a reviewer clicks, and a defunct entity is a misrepresentation on a compliance request.
   Answered as an individual developer with the same Gmail. Having no organization is the
   *qualifying* condition here: the form's scope is customers on the self-serve GCP Terms of
   Service, which is exactly what this account is.
2. *Sensitive domains.* Read literally, three boxes applied (health, finance, companionship);
   read as intended — what industry do you serve — none did, since there is no second user.
   **Ticked therapy/wellness/companionship only**, the one that describes what the product *is*
   rather than data it holds. Named the trade-off explicitly: that box is the most likely cause of
   extra scrutiny, and an exception granted on an incomplete declaration is worth less than one
   that survives being checked.

**Still open, and it does not wait on Google:** the proposed § Section 0 amendment
(`archive/security/zdr_terms_evidence_2026-08-20.md`) is drafted and unruled. It states what the
sensitive-tier permission rests on *now* — the gap the 2026-08-20 correction opened — not what it
will rest on after a grant. No code written; nothing to deploy.
