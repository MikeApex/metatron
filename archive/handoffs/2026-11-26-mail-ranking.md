# Handoff 2026-11-26 — mail-ranking (branch wt/mail-ranking, based on 2293026)

Model: Sonnet 5.5. Two commits.

1. 3eb96e3 — forwarded email keeps its original recipients [DB-0902-05]. Close it with: tests/test_forward_recipient_trail.py 17/17, tests/test_intake_forward.py 24/24. Not run: tests/run_intake_redteam.py (calls live models, needs METATRON_LIVE=1). Live check still open (M): forward a real secondary-account mail and read the envelope signals.
   - Header sources read: X-Forwarded-To, X-Forwarded-For, X-Original-To, Delivered-To (all occurrences, earliest hop first; Delivered-To/X-Original-To count only when an X-Forwarded-* header exists or two or more distinct addresses appear, so ordinary mail is unchanged), plus the quoted To:/Cc: lines of an inline forward block (Gmail, Apple, Outlook shapes), read only after an authenticated self-forward unwraps. Capped at 5 well-formed addresses, 254 chars each.
   - Carried as signals["original_recipients"] (intake envelope, reaches the extractor inside the untrusted wrapper) and "originally_sent_to" in read_email messages. Display only: nothing branches on it; the self-forward gate (_authenticates_as, topmost trusted Authentication-Results, ledger_safe=False on unwrap) is unchanged.
2. 571bee9 — weekly review contact reader [ranking_review defects]. tools/ranking_review.py _person_names now reads contacts via lookup_guard's rules (strict loader, per-alias, capitalised aliases only, annotation stripped); dead _ORG_TYPES removed. lookup_guard.py gained four public aliases only (contact_aliases, alias_is_name, load_contacts_strict, unannotated_name). tests/test_ranking_review_aliases.py 8/8; test_ranking_v2 58/58, test_research_check 21/21. Close the 11-24 ranking_review backlog item on this evidence.

qa_sweep.sh 12/12 in the worktree. SESSION.md: nothing to carry beyond the above. Note: .venv in the worktree is needed to run tests (system python3 lacks yaml).
