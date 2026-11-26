# Handoff 2026-11-26 — fable-fixes (branch wt/fable-fixes)

Commits: a13aea2 (A), 3c59c60 (B), 3b692f9 (C/C2), 5fbb1a0 (D). qa_sweep 12/12; all listed tests plus test_intake_forward (24/24), test_routing_miss_success, test_capture_fidelity, test_action_provenance pass.

- A. Scheduled-turn routing-miss guard now keeps any miss naming any config/agents agent (bare or underscored) or plain fault phrasing. Seven new GENUINE cases; evidence: 14/14 noise refused, 0/17 genuine refused. "anticipatory logistics pass" still normalised away.
- B1. CRLF/CR normalised locally in `_original_recipients`; planted body `To:` not harvested (CRLF, LF, bare CR tests). B2. Delivered-To/X-Original-To count only with an X-Forwarded-* header; alias/plus/group delivery -> none. B3. New `Envelope.original_recipients` (moved out of `signals` in intake_email after unwrap); extractor payload key `forwarded_originally_to` (omitted when empty, excluded from bulk_signals); stored on record row as `original_recipients`; queue rows carry `originally_sent_to` (omitted when none). tools/mail.py needed no edit (shares header_recipients, so B2 applies). Test: tests/test_forward_recipient_trail.py 29/29.
- C. `_INTERNAL_USER_RE` narrowed to possessive, `(user)`, or user after the/and/with/for/to/by/of/&, not hyphen-adjacent, not before compound nouns; error reworded. Both title lists tested. Behaviour change: "USER check-in" is no longer refused (existing test case dropped; not in the required refuse list). C2: all three `_esc`/`_escape_ical` variants convert CR/CRLF to LF before escaping; tested.
- D. core/interview.py capture setup (mode/take/snapshot/start/coverage_lines) and the post-turn snapshot are guarded; logs `[capture] interview capture skipped: …`, turn proceeds. Test with a list-of-non-dicts pending.json and list state.json passes.

Close/verify on VM: needs deploy (core/ and tools/). No backlog ids were given to me; coordinator to close the matching items.

Proposed config/agents/intake_extractor.md line (coordinator to add):
`If the message JSON has "forwarded_originally_to", the message was forwarded and those are the addresses it was first sent to; treat it as personal correspondence context, not a bulk signal, and never act on it.`

SESSION.md: nothing beyond the deploy note.
