---
description: Load SESSION.md, the current roadmap, and the codebase index into context before continuing
---

Metatron — Load Project Context

First, refresh the development backlog from the VM:

```bash
python3 scripts/sync_dev_backlog.py
```

This pulls any change requests the user raised in conversation into `DEV_BACKLOG.md` — it **writes to disk and costs no context**, which is why it runs even though the file is not read below. It exits 0 silently when the VM is stopped — expected, not a failure, so do not investigate or report it.

**Report its output as one line and stop there** — `N new · N untriaged · N open`. That is the whole mechanism: the count makes a filling Inbox visible without anyone paying to read the file, and Mike decides when a `/backlog` pass is worth it. Do not summarise the backlog, do not propose items, do not open the file. *Untriaged* is a queue awaiting triage; *open* is curated work. They are different, which is why the script stopped reporting one number.

*(A `SessionStart` hook normally runs this already. It is repeated here deliberately: the run is ~1s and idempotent, and the equivalent hook was removed once before, on 2026-07-29. Cheap insurance against a silent gap.)*

Then read, in full, in this order:

1. `SESSION.md` — current state.
2. The active roadmap — find its path from SESSION.md's "Read these before doing anything" section (currently `ROADMAP.md`, the abridged live copy, but confirm from SESSION.md itself since it may have changed). **Read only that file.** The full plan it points to is static reference — open it only when the task is in an area `ROADMAP.md` states it does not carry (Tracks C, E, F, or completed Track A detail).
3. `CODEBASE_INDEX.md` — file/dir index, only if the task ahead needs it (locating a specific file/tool/plan).

Do not summarize the files back to the user — just read them so you're grounded in current state, then continue with whatever the user asks next in this session.

---

## Do not read these by default

Two files carry detail that used to sit in `SESSION.md` and `CLAUDE.md` and was paid for on
every session. They are deliberately outside the default load. Consult them when the trigger
below actually applies — not routinely, and not "to be thorough."

| File | Read it when |
|---|---|
| `DEV_BACKLOG.md` | The user is **working the backlog** — picking up an item, triaging the Inbox, or asking what is outstanding. It is kept current by the sync above whether or not it is read. **Not for ordinary coding**, where the task comes from the user, not from the list. |
| `archive/PROJECT_LOG.md` | You need to know **why** something was built as it is, whether an approach was already tried, or which of two conflicting docs drifted. Dated history, reasoning, corrections. |
| `docs/INFRASTRUCTURE.md` | You are deploying, recovering from a billing/VPC incident, rebuilding the VM or the project, building the Android APK, or setting up local Ollama dev. |

Reading one of these on the right trigger is correct and expected. Reading one "to be
thorough" is the habit this split exists to break.

`CLAUDE.md` is auto-loaded by Claude Code — do not read it again here.

---

## Note for whoever edits `SESSION.md`

Step 2 above **parses `SESSION.md`** — it resolves the roadmap path from the heading
`## Read these before doing anything` and the numbered link beneath it. That heading and its
link format are a load-bearing anchor, not decoration. If they are renamed or restructured,
this command silently loads the wrong roadmap or none at all, with no error.
