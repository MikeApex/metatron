Diff review of the WhatsApp Phase 2 build (`archive/plans/whatsapp_phase2_build_plan_2026-11-23.md`) — reviewer: Fable 5.2 (codebase-reviewer, read-only), 2026-11-23, clean-room. Asked: "what in this diff breaks, leaks, or loses a message?" Given the plan, its adversarial review, the 72-file diff and the lead's ten integration decisions. The findings are summarised below as returned; the lead's disposition of each follows.

## Findings, most severe first

1. **A chosen chat silently stops reaching Metatron for good when its link first appears in a full backup — CONFIRMED (High, lost).** `BackupCombiner.newLinks` lists only ids unlinked in the base and linked after the fold, so a hidden id already linked in the base never migrates; the allowlist keeps the hidden id while the combine canonicalises the chat's messages to the phone-number id; `ShareStore.postNightly` stores links only for already-shared canonical ids, so `canonicalShared` is null for both raw ids. Direction: migrate any shared hidden id that tonight's `hiddenToCanonical` maps.
2. **On the night a shared chat gains a link, up to 8 days of its messages are sent again and recorded as second facts — CONFIRMED (High, duplicates).** Sent-hash keys are `hiddenId|second|ordinal`; after the fold the messages carry the phone-number id, so every lookup misses. The VM's `_apply_merges` renames the index row's chat but the envelope id is still the old key's hash, and ingest dedupes by id. Needs re-keying on both sides.
3. **Un-ticking then re-ticking a chat loses its last ~9 days — CONFIRMED (Medium-High, lost).** The un-tick purges on the VM, but the chat's keys stay in the sent-hash list, so after the re-tick every message is "unchanged" and skipped. Same root: after the page's delete-all without "Turn off", the VM cursor is null and the newest 9 days are never re-sent.
4. **A message whose newest increment copy has no text is never sent if it was not sent before — PLAUSIBLE (Medium, lost).** The combiner lets a later copy replace the base row outright ("a re-sent copy without text"); `EventPlan` then skips it as no-text.
5. **After a system stop mid-post, the nightly job can vanish — PLAUSIBLE (Medium, Android-only).** `onStopJob` flags cancel; a POST can block 120 s; a restarted job finding `current` set returns finished; the old thread exits cancelled and skips the reschedule.
6. **Any 403 stops the phone, and only opening the WhatsApp screen restarts it — CONFIRMED (Medium).** `onAppOpen` returns on `!allowed` without asking the VM again; the link notices are screen-only.
7. **A message unread across a nightly run can be recorded twice when its notification text differs from the backup text — PLAUSIBLE (Low-Medium, duplicates).** The nightly `update` replaces the key's hash; a re-shown notification line after the 6-h memo gets a new ordinal.
8. **"Turn off" after a reinstall or re-pair still raises "not reaching Metatron" 52 h later — CONFIRMED (Low).** `device_revoked` keeps the report while an orphaned earlier pairing counts as live for 30 days.
9. **"Dry run started — nothing is sent" can be shown while a real run posts — CONFIRMED (Low).**
10. **The link fails silently when the device token cannot be opened or the server address stops being https — PLAUSIBLE (Low).** The client's local pseudo-statuses (−2, −3) leave the gate unchanged.

Minor: a live post in flight during "Turn off" can re-persist `ever_opened`/`OPEN` through `Gate.observe`; a run racing "Turn off" can re-create `job.json` and the last-report file (counts and times only).

## Checked and found sound (reviewer)

Nothing recorded unless the VM took it; the per-batch cursor (never backwards, withheld after an unaccepted batch, inside the 8-day overlap and 9-day prune); a retried batch cannot double-ingest; a later group sender goes as `update`; no unattended shrink of the share list; **no leak** of text, sender ids, display names or tokens (no logging or `getMessage()` path, FLAG_SECURE screens, decrypted copy and key destroyed in `finally` with three sweeps); **the consent gate does not fail open** (only an exact `consented_off`; `channel_off` reads as no consent; every device handler gated; components disabled until OPEN); the dry run posts and records nothing and is bounded; the VM side (fixed 403 words, integer-and-code report, once-per-onset line, the missed endpoint's validation and purge/merge/expiry/delete-all).

Not read: `IncrementReader`, `FullBackupMessages`, `BackupDecryptor`, `SelfTest`, `RunStatusView`, `LastReport`, `WaBootReceiver`, `MetatronApp`, the `waprobe` manifest, the tests.

## Disposition (lead, 2026-11-23)

All ten were sent to one fix worker (Opus) with a fixed design per item: F1 canonical allowlist and migration on any mapped shared hidden id; F2 `SentHashes.rekeyChat` before the event build plus VM merge aliases in the dedupe; F3 `removeChat` on a re-tick and `clear()` on a null cursor; F4 a later textless copy keeps the earlier text (reversible in one line); F5 a blocked start or a system stop reschedules; F6 `onAppOpen` re-asks the VM when once-open and closed; F7 live memo 72 h by live text hash; F8 any successful revoke deletes the stored report; F9 the dry-run confirmation reworded; F10 −2/−3 move the gate to UNPAIRED. The fix worker also kept the VM alias on the night the merged hidden id drops off the list (removing it then would make an edit in the rest of the overlap a second fact).

## Verify round (same reviewer, re-read from disk)

**9 CLOSED, 1 PARTIAL, 1 NEW.**
- **F7 PARTIAL — accepted as a known limit:** the live memo is memory only, so a listener process restarted between the nightly `update` and the re-show of a line whose notification text differs from the backup's still duplicates. Closing it means keeping text-derived state on disk across restarts, which the plan rules out (no text queued on disk, § 3.10).
- **F2 residual — fixed by the lead:** the phone re-keyed only merges the nightly post itself carried; it now also re-keys every hidden id tonight's tables link (idempotent; a no-op writes nothing).
- **F4 residual — fixed by the lead:** an empty-string later copy keeps the earlier text, as a null one does.
- **NEW-1 (Medium, CONFIRMED) — fixed by the lead:** F3's null-cursor clear also fired on the first real night (live posts never carry a cursor), wiping the live feed's keys from switch-on day. The phone now remembers the newest cursor the VM ever answered (`cursor_seen` in `job.json`) and clears only when a cursor it once had comes back null. Tests: the first night's null cursor keeps the live keys; a cursor once answered is remembered; every linked hidden id is re-keyed without a merge that night; an empty copy keeps its text.

Final: phone suites 299 / 349, 0 failures; VM 49/49.
