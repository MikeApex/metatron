# Window B — §10b run 2, the collision half

*Paste the block below into a **second Claude Code window**, opened in
`/Users/md-homefolder/Desktop/multi-model-mcp` on the MacBook. Window A (the window that wrote
this file) is holding the other half of the collision and is waiting on you.*

**Brief window B as ordinary work, not as a test** — the standing rule. It is not being asked to
prove anything; it is being asked to make a small change and close out normally. That is what
makes the observation worth something.

---

## The prompt

```
Small job in /Users/md-homefolder/Desktop/multi-model-mcp on the MacBook. Another window is
also working in this tree right now, so diff before you stage.

1. In tools/obligations.py, _find() does a linear scan and returns None when nothing matches.
   Add a short comment above it saying that the None return is what open/close/reopen branch on
   to produce their "no such obligation" message — i.e. it is a real signal, not a lazy default.
   Comment only. Do not change behaviour and do not touch any other function in that file.

2. Write a log fragment at archive/log/2026-08-14-06-window-b-obligations-comment.md recording
   the change. Follow the format of the existing fragments in that directory exactly, including
   the trailing blank line each one owns. Do NOT edit archive/PROJECT_LOG.md — it is generated.

3. File a one-line note into .claude/backlog_inbox/ describing anything you noticed in
   tools/obligations.py that a user would notice or that blocks the roadmap. If there is nothing
   that meets that bar, write a file saying exactly that — do not invent an item.

4. Stage ONLY the two files you changed, by explicit path, and commit them with a one-line
   message. Report the exact output of the commit command, including any refusal, verbatim.

Then stop and tell me what happened. Do not deploy. Do not run ./deploy.sh.
```

---

## What window A is watching for

| # | Check | Pass |
|---|---|---|
| **4** | A wrote `tools/obligations.py` first; B then writes it; **A** commits | guard blocks A, **naming the file** — *the last unobserved check in the plan* |
| 13 | Both windows leave a log fragment | `build_project_log.py` renders both, newest-first, no conflict |
| — | Both file a backlog fragment | both fold into the Inbox on the next sync |

**B's own commit is expected to succeed.** B never wrote the file before A changed it, so B's
manifest has no stale hash — the guard is asymmetric by design, and that asymmetry is the thing
being observed. If B's commit is *also* blocked, that is a finding, not a pass.

> **Do not add a trailing `echo "exit=$?"` after `git commit`.** The guard fails closed on shell
> it cannot parse and will block the commit for that reason instead — the run would then read as
> a pass for entirely the wrong reason (plan § Verification, check 4).
