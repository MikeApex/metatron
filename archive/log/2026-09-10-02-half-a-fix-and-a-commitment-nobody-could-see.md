### 2026-09-10 (half a fix, and a commitment nobody could read) — `tools/mail.py`, `tools/caldav.py`

Follow-on from `-01-` the same day. That session restored the revoked app-specific password by
walkthrough and filed `[DB-0910-01]` against the message that had misled Mike. This one built the
message fix and, in the course of troubleshooting the exchange it came from, found a second and
worse fault in the same exchange.

**The message fix — `[DB-0910-01]`, closed.** Auth failures on both integrations now name the
second half of the job: generate a new app-specific password in Google, **then write it into this
persona's `email.yaml` / `caldav.yaml`** — with the resolved path named, and a statement that no
restart is needed (`_load_config()` runs per invocation). `_credential_remedy()` in
[tools/mail.py](../../tools/mail.py) at four sites (both IMAP `login rejected` paths, both SMTP
paths, the latter gated on `SMTPAuthenticationError` so an ordinary send failure is not decorated
with credential advice); the same helper plus `_auth_hint()` in
[tools/caldav.py](../../tools/caldav.py) at all five `RequestException` sites, gated on 401/403.

Three things decided rather than defaulted:

1. **Two numbered steps, second flagged as the one usually missed.** A specialist paraphrases this
   text before Mike sees it, and the 09-10 failure *was* a paraphrase dropping the unflagged half.
   Prose that merely contains both halves would have reproduced the fault.
2. **Duplicated across both files rather than shared.** The two integrations hold the same password
   in two separate files, and an account-password change kills both — the helper has to name the
   file it belongs to.
3. **`_safe_config_path()` added after a live failure in test.** `persona_config_dir()` fails
   closed with no persona in scope (deliberate, `.claude/rules/personas.md`) — so the first version
   of the builder raised `PersonaError` when called outside a scope. An error-message builder that
   raises converts a clean tool error into a traceback. Falls back to the bare filename.

**Rejected, and the item says so explicitly:** auto-recovery. An app-specific password cannot be
learned, derived or refreshed — there is no OAuth or refresh token on this path.

Verified by direct invocation, not inspection: rendered text printed in and out of a
`persona_scope`; `_auth_hint` returns the remedy on 401, empty on 500 and on a response-less
exception. `test_calendar_invite` 19/19, `run_calendar_conflict_tests` 24/24,
`test_intake_forward` 24/24, `qa_sweep` 10/10. **Not verified:** how a specialist paraphrases the
new text — that needs a live credential failure, and the next real one is the test.

**The worse fault, found in the same exchange and filed as `[DB-0910-02]`.** Exchange `001`
(07:30, proactive morning session): `logistics` got CalDAV `401` and IMAP `AUTHENTICATIONFAILED`,
fell back to two `search_memory` calls, and the Synthesizer opened with *"Today's primary
commitment is the BRS Elul lecture with Jonathan Hall at 7:30 PM"* — stated flat, as a confirmed
diary item, **on a turn where no diary was readable.** The lecture came from journal text. The same
reply mentioned the credential failure later, as separate housekeeping, so both facts were present
and never connected. This is the fact-provenance class firing on the silent-failure path: the
2026-09-03 provenance work covers what a specialist reports, not a specialist substituting recall
for a source that just errored. **The open question decides the fix's shape** — whether the
Synthesizer receives any marker distinguishing "read from calendar" from "recalled from memory".
If yes, agent-file wording; if no, a package-format change in code. Not yet verified against
current code, deliberately: the item records the question rather than a guessed answer.

Two lesser finds from the same trace, not filed — `logistics` burned 5 turns / 87.5k cumulative
input on a morning greeting, and the Coordinator logged a false-positive `USER_CORRECTION`
claiming Mike had injected system instructions, against its own proactive directive.

Committed as the close-out below. **Not deployed** — `tools/` needs `./deploy.sh`, Mike's to run,
and `0e154b9` is still owed from 09-09, so one deploy carries both.

