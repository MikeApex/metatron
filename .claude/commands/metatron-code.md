---
description: Load SESSION.md, the current roadmap, and the codebase index into context before continuing
---

Metatron — Load Project Context

First, refresh the backlog from the VM:

```bash
python3 scripts/sync_dev_backlog.py
```

It writes to disk and **costs no context**, which is why it runs even though the file is not
read below. Exits 0 silently when the VM is stopped — expected, not a failure; do not
investigate or report it.

**Report its output as one line and stop there** — `N new · N inbox · N now · N later`, plus a
`⚠ machine:` clause if a runtime signature has recurred. That is the whole mechanism: the count
makes a filling Inbox visible without anyone paying to read the file, and Mike decides when a
`/backlog` pass is worth it. **Do not summarise the backlog, propose items, or open the file.**
The four numbers mean different things — *inbox* is untriaged, *now* is prioritised work,
*later* is real but unprioritised — which is why it stopped reporting one number.

*(A `SessionStart` hook normally runs this too. Repeated deliberately: ~1s, idempotent, and the
equivalent hook was removed once before on 2026-07-29.)*

Then read, in full, in this order:

1. `SESSION.md` — current state.
2. The active roadmap — resolve its path from SESSION.md's "Read these before doing anything"
   section (currently `ROADMAP.md`, but confirm from SESSION.md since it may have changed).
   **Read only that file.** The full plan it points to is static reference — open it only for
   an area `ROADMAP.md` states it does not carry (Tracks C, E, F, completed Track A detail).
3. `CODEBASE_INDEX.md` — only if the task ahead needs it to locate a file, tool, or plan.

Do not summarise these back to Mike. Read them, then continue with whatever he asks next.

---

## Do not read these by default

| File | Read it when |
|---|---|
| `DEV_BACKLOG.md` | **Working the backlog** — picking up an item, triaging, or asked what's outstanding. Kept current by the sync whether or not it is read. Not for ordinary coding, where the task comes from Mike. |
| `archive/PROJECT_LOG.md` | You need **why** something was built as it is, whether an approach was already tried, or which of two conflicting docs drifted. |
| `archive/backlog_closed_*.md` | Checking whether something was already fixed, or why an item was withdrawn. |
| `docs/INFRASTRUCTURE.md` | Deploying, recovering from a billing/VPC incident, rebuilding the VM, building the APK, or setting up local Ollama. |
| `docs/WORKFLOW.md` | Unsure which command to fire, or when. |

Reading one on the right trigger is correct. Reading one "to be thorough" is the habit this
split exists to break. `CLAUDE.md` is auto-loaded — do not read it again here.

---

*Note for whoever edits `SESSION.md`:* step 2 **parses** it — the heading
`## Read these before doing anything` and the numbered link beneath it are a load-bearing
anchor. Rename or restructure them and this command silently loads the wrong roadmap, with no
error.
