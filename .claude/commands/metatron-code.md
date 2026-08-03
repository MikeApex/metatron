---
description: Load SESSION.md, the current roadmap, and the codebase index into context before continuing
---

Metatron — Load Project Context

First, refresh the development backlog from the VM:

```bash
python3 scripts/sync_dev_backlog.py
```

This pulls any change requests the user raised in conversation into `DEV_BACKLOG.md`. It exits 0 silently when the VM is stopped — that is expected, not a failure, so do not investigate or report it. If it reports new entries, mention the count in one line.

Then read, in full, in this order:

1. `SESSION.md` — current state.
2. The active roadmap — find its path from SESSION.md's "Read these before doing anything" section (currently `archive/plans/phase5_to_future_roadmap_2026-06-10.md`, but confirm from SESSION.md itself since it may have changed).
3. `DEV_BACKLOG.md` — the single list of outstanding changes, including anything just synced into `## Inbox`.
4. `CODEBASE_INDEX.md` — file/dir index, only if the task ahead needs it (locating a specific file/tool/plan).

Do not summarize the files back to the user — just read them so you're grounded in current state, then continue with whatever the user asks next in this session.
