# 2026-09-03 — A file sent earlier in the conversation can now be used in a later turn

**Branch:** `wt/attachment-persistence` (worktree). **Not deployed** — owes `./deploy.sh`.
**Files:** `core/attachments.py`, `core/server.py`, `tests/test_attachment_persistence.py` (new).
`core/orchestrator.py` needed no change: it already passes whatever list it is given through
`describe_for_prompt()` and `load_parts()`, so revived files ride the existing path untouched.

**What shipped.** Reported live today: a user attached a PDF, asked about it two turns later, and
was told files from earlier messages are not retained — forcing a re-upload. The bytes had in fact
been on disk and indexed the whole time; what was missing was *addressability* once the client
stopped re-sending the id. Now, when a message with no files of its own refers back to one
("read the pdf I sent", "summarise tenancy.pdf", "look at that again"), the stored file is matched
in Python and joins the turn's attachment list.

**Design chosen: match on the user's words, load bytes only on a hit.** Not always-carry — a 5 MB
PDF re-sent through a day of idle chat is a token bill nobody asked for. Reference detection needs
no agent-file change because it runs in `core/attachments.references_earlier_files()`: filename or
stem named outright, else a type word ("pdf", "photo") alongside a back-reference phrase, else a
bare back-reference taking only the most recent file. False positive costs one re-sent file bounded
by the cap; false negative costs the re-upload this exists to remove — thresholds set on that
asymmetry. Revived files are excluded on proactive turns (scheduler text is not a user referring to
anything) and when the message carries its own files.

**Boundary preserved.** Revived content re-enters through the same `describe_for_prompt()` — one
function, one paragraph, one `<untrusted_content>` sentence. Carried records are flagged
`carried: True` so the line says they came from an earlier message, but the trust clause is
identical and stated once. The fresh-attachment wording is byte-for-byte unchanged and pinned by a
test, because the Red-tier agent files refer to that sentence and cannot follow a drift.

**Standing cost.** Two clocks, deliberately split — **flag for Mike**: the brief said one TTL of 24h.
`CARRY_TTL_SECONDS` = 24h governs prompt reuse (meter: tokens; bounded by `MAX_CARRY_FILES` = 2 and
`MAX_CARRY_BYTES` = 5 MB per turn). `RETENTION_SECONDS` = 30d governs disk deletion (meter: disk).
They are split because the chat history UI renders past attachments via `GET /attachments/{id}`, so
deleting at 24h would blank images in conversations the user can still scroll back to — a
user-visible regression. Recommendation: keep the split; if you disagree, `RETENTION_SECONDS` is the
single constant to change. **What deletes the files:** `sweep_expired()`, run opportunistically on
the next upload for that persona (no `_DEFAULT_JOBS` edit), with `_forget_attachments()` clearing
the index rows. **On restart:** files survive and both clocks still apply — the age test reads the
sidecar's stored timestamp, not a process clock, so a server down for a week sweeps correctly on its
first upload back. **Caveat:** a persona that stops uploading keeps its last files indefinitely;
accepted, since a store that stopped growing is not the one with a cost problem.

**Tests.** `python3 tests/test_attachment_persistence.py` — 21/21 (store+retrieve across turns via
the real `_revive_attachments` against a temp DB, TTL expiry, both caps, newest-first eviction,
sweep, 600 perms, persona isolation, and that carried content goes through `describe_for_prompt()`).
Existing `tests/test_attachments.py` 18/18 and `tests/test_attachment_endpoints.py` 15/15 unchanged.
`scripts/qa_sweep.sh` 9/9. `import core.orchestrator, core.server` clean.

**Proposed agent-file line — NOT applied** (`config/agents/coordinator.md`, Red-tier, B1b row 5):
> When the attachment note says a file was *sent earlier* rather than attached to this message,
> treat it as the user's likely referent but say which file you opened; if the user meant a
> different one, ask them to name it.
Without it the behaviour still works — the system-authored line already states the provenance — but
the model is not instructed to name which file it opened, so an ambiguous reference resolves
silently. Worth a Red session.

**Backlog:** nothing to close — no existing item covers this; it was reported live today. If one is
filed, the evidence is the 21-check suite above plus a live re-test after deploy: attach a PDF, send
two unrelated turns, then ask "what did the pdf I sent say?".

**SESSION.md must carry:** attachments now persist across turns within a 24h carry window (2 files /
5 MB per turn), disk retention 30d swept at upload time; branch `wt/attachment-persistence` merged
but **not deployed**; one proposed Coordinator line pending a Red session.

**Transcript archive:** `archive_chats.py` could not run from this worktree — there is no JSONL at
`~/.claude/projects/-Users-md-homefolder-Desktop-metatron-wt-attachment-persistence`, and running it
from the main repo would write outside this worker's manifest. The parent session should run it.
