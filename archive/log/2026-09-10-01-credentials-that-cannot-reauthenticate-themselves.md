### 2026-09-10 (credentials that cannot reauthenticate themselves) — no code change

Mike reported through `/fix` that reauthentication "should have happened automatically" after he
changed his Google account password. **The premise did not hold, and `/fix` stopped at step 2
without dispatching a worker.** Recording it because the wrong diagnosis is the attractive one and
a future session will reach for it again.

**What was actually true.** Both `config/personas/mike/email.yaml` (mtime 2026-08-04) and
`caldav.yaml` (mtime 2026-08-03) still carried the *same* app-specific password — identical hash
prefix across the two files — and it had been dead since the account password changed, because
Google revokes every app password when that happens. Live probes from the VM: IMAP
`AUTHENTICATIONFAILED Invalid credentials`, CalDAV `401`. Nothing in the code failed.

**Why "automatic reauth" is not a lost behaviour but an impossible one on this path.** An
app-specific password is a secret the system cannot learn, derive or refresh — there is no OAuth
and no refresh token on the mail/CalDAV path (the OAuth flow in `tools/google_contacts.py` is a
different integration entirely). Two things were checked and ruled out so they are not chased
again: neither `tools/mail.py` nor `tools/caldav.py` caches config — both call `_load_config()`
per invocation — so **no restart is ever needed after a credential edit**, and the agent's
"connection test still failing" in exchange 003 was accurate reporting, not a stale answer.

**Where the system genuinely misled him, and this is the part worth fixing.** Exchange 001 asked
for "credential re-authentication whenever you're ready"; exchange 003 said to update the
app-specific password "in your account settings" (`tools/mail.py:219-223`). Mike did exactly
that — and the retest then ran against a file nobody had written to. **The message names half the
job.** Regenerating in Google does nothing until the value is written into the persona's
`email.yaml`/`caldav.yaml` on the VM. Filed as `[DB-0910-01]`.

**Resolved by walkthrough, not by a commit.** These files are Denied tier and VM-owned, so Mike
ran the edit himself against a prepared `read -rsp` block that prompts without echoing, strips
the spaces Google displays the password with, backs up, rewrites only the real `password:` line
in each file (the commented example lines start with `#` and do not match) and re-asserts `600`.
Verified from here by live probe afterwards: **IMAP login OK with INBOX select, CalDAV `207`** —
a pass, not an absence of errors. Backups deleted. Calendar writes and invite dispatch unblocked;
the 24 September reception logged at exchange 005 remained unwritten at session close.

**One handling lesson, because it cost a cleanup.** Mike pasted the password into the chat, which
put it in the session JSONL — and I then repeated it back in both spaced and concatenated form
while answering which format to use, doubling the copies. **Restating a secret to confirm its
format is the avoidable half.** Checked: zero occurrences anywhere in the repo and no transcript
written, so nothing was ever staged for a push. This session was deliberately **not archived** —
the transcript would have carried the secret into `archive/transcripts/` and out on the next
push — and the JSONL was scrubbed by hand after close. Both forms needed scrubbing.
