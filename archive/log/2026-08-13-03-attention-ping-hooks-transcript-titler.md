### 2026-08-13 (attention-ping hooks, and the transcript titler that had been mangling names since June) — no repo commits; changes are in `~/.claude/`, **not deployed**

Started as a question about VS Code audible alerts and turned into two harness fixes. No
Metatron code, config, agent or persona touched. A parallel window held the repo throughout
and archived just before this one (`2f49479`).

**Built:** `~/.claude/alert.sh` plus a `Notification` hook (Funk — permission prompt or idle
wait) and a second `Stop` hook (Glass — turn over, your move), both `async`. Toggle is the
shell function `alert` in `~/.zshrc`, flipping the marker file `~/.claude/.alerts_off`.

**Three things asserted earlier in this same session were wrong, and all three were acted on
before being caught.** The first half ran on Haiku 4.5; the corrections came after switching to
Opus 5, when Mike asked for a review before implementing:

1. **A shell variable cannot gate a hook.** The proposed design toggled `ALERT_ENABLED` in
   `.zshrc` and had the hook read it. Hooks run in a subprocess spawned by Claude Code and
   never see the interactive shell's environment. The toggle has to be a *file* — which is
   also why one `alert` now flips every running session at once, a better outcome than the
   original.
2. **`PreToolUse` was the wrong event** — it fires on every tool call, so the "ping when work
   stops" feature would have pinged hundreds of times a session. `Notification` and `Stop` are
   the events that actually mean *the user is needed*.
3. **The VS Code extensions recommended in the first answer were unverified** and read as
   fabricated. The real built-in is `accessibility.signals.*`, not `notification.sound`.

**Then the archive itself surfaced a live defect.** This session's transcript was written as
`2026-08-13 — local-command-caveatCaveat The messages below were genera (2).md`. Cause, in
`~/.claude/tools/archive_chats.py`: a slash command expands into **five** tags and only
`<command-name>` was in `SYSTEM_TAG_PATTERNS`, so the caveat boilerplate survived into the
message text — polluting **transcript bodies too**, not just titles, since `strip_system_tags`
feeds both. Second, compounding defect: the title took the first user message unconditionally,
so a session opening with `/model haiku` was titled from the command rather than from what Mike
typed next. Both fixed; title now skips messages that strip to nothing, with the command name
kept as a fallback so an all-slash-command session titles `archive` rather than `untitled`.
Verified across all **109** sessions in this project: 0 garbage, 0 `untitled`, no regressions.

**Correction to something done earlier in the session:** hand-renaming the bad transcript file
was pointless. The script locates a session by the `*Session ID:*` marker *inside* the file,
unlinks it and rewrites under a freshly derived name — so any manual rename is erased on the
next run. Fixing the generator was the only durable move.

**Backfill:** 31 of 32 historical transcripts retitled from their own JSONL (`2026-08-10 —
Verify [DB-0810-14]…` where there had been 13 identical caveat names). One left alone —
its JSONL is deleted, so a title could only have been invented. **Rejected:** renaming the 32
straight off. They are historical records, so the mapping was produced as a dry run and shown
before anything moved.

`archive_chats.py` is the single global copy, so both fixes apply to every project. Nothing
here is committed to this repo — the script lives in `~/.claude/` and `archive/transcripts/`
is gitignored.

