# 2026-08-03 — Backlog Triage and Automatic Deploy Verification

Short session, continuing directly from the 2026-08-02 multi-surface testing work.
Two pieces: moving loose open items into `DEV_BACKLOG.md`, then building the deploy
guard that had been recorded as advice.

Commits: `5440021`, `9799ba3`. Both pushed to `main`.

---

## 1. Loose items filed into DEV_BACKLOG.md (`5440021`)

Four items were floating in conversation only. Filed with enough context to be
picked up cold.

### Check-in activity gating — **partially done, and the shipped half doesn't help**

Checked before filing rather than assuming, which was the right call. The gates
deployed earlier today (`quiet_after_user_minutes`, `min_gap_minutes` in
`core/scheduler.py:173`) solve *"don't interrupt a live conversation."*

The cost lever from the parked programme is the **inverse**: don't fire at all on a
day the user never spoke. That case survives — silence is exactly what
`quiet_after_user_minutes` reads as permission to fire. So the pathological case
from the original cost analysis (*~12 full multi-specialist pipelines/day talking
to itself while the app was broken*) is still live.

Filed with a design question rather than a spec, because the obvious build is wrong:
a hard skip means a user silent for three days gets nothing on the fourth morning,
which is arguably when a check-in matters most. A first-of-day exemption or an
escalating gap is probably the shape. `morning_brief`/`evening_close` stay ungated
per today's earlier decision.

### Sentence-chunked TTS — deferred, deliberately

Kokoro is at 2.8s/call (was 15.0s). Recorded with an explicit *don't build this yet*:
whether 2.8s is worth optimising is a judgement only usage can settle.

### Browser live-refresh on foreign messages

Terminal/app-originated messages reach the browser only after a manual reload.
Sync itself is confirmed working — this is a client render path. Shares a file and
region with the scroll fix and line-wrap items, so it's one pass.

### Roadmap D2 item 5 is mis-scoped

Targets the Coordinator on the assumption it runs ~7 turns. **Measured 2026-08-02:
Coordinator = 1 turn; `logistics` = 8.** Working the item as written would optimise
an already-minimal component. Filed with a caution to re-measure across several
specialists rather than swapping one assumed culprit for another.

---

## 2. Automatic deploy verification (`9799ba3`)

Filed initially as a manual habit (*check `git log --oneline -3` on the VM*), then
upgraded to run automatically at the user's direction. The upgrade was correct:
**the failure mode is silence, not an error**, so a manual check catches nothing on
the day nobody looks.

### What prompted it

Two false records on 2026-08-02, both caught only by a human happening to look:

1. A `./deploy.sh` failed at the SSH step and left the VM a commit behind with no
   visible complaint.
2. A parallel chat's *"NOT yet deployed"* note was already stale — a deploy from
   another window had shipped its commit as a side effect.

### Implementation

`deploy.sh` captures `git rev-parse HEAD` after the push succeeds, then re-SSHes
after the service restart and compares. Three outcomes:

| Outcome | Behaviour |
|---|---|
| Match | `Verified: VM HEAD matches.` → `Deploy complete.` |
| Mismatch | Prints both SHAs, *"you are about to test OLD CODE"*, and the `git status && git pull origin main` command that surfaces the real error. Exit 1. |
| Unreadable HEAD | Reports **unverified** — not success, not failure. Exit 1. |

### Two design calls

**A second SSH, not a parse of the first.** The deploy heredoc interleaves pip,
systemctl and per-5-second drain-loop output. A SHA pulled from that stream would
be pattern-matching against noise, and a verification step that can itself misread
is worse than none — it manufactures false confidence. A clean call costs seconds
and cannot be wrong.

**Case 3 refuses to guess.** The shortcut is to treat an unreadable HEAD as failure.
But *"I couldn't check"* and *"it's broken"* are different states; collapsing them
trains the reader to ignore the message when it fires on a flaky tunnel.

### Testing

- `bash -n` syntax check
- All three branches against simulated SHAs → rc 0 / 1 / 1 as intended
- Confirmed a failed SSH capture doesn't abort under `set -e` before reaching the
  friendly message (`|| REMOTE_SHA=""` handles it)

**Caveat carried forward:** not yet exercised against the live VM. The next real
`./deploy.sh` exercises the **match** path only; the failure paths remain
simulation-tested.

---

## Decisions

1. **Deploy verification is automatic, not documented.** A habit that depends on
   remembering doesn't address a silent failure mode.
2. **Activity gating needs a design answer before a build.** The naive version
   (hard skip on silence) is plausibly worse than the current behaviour.
3. **TTS chunking waits on real usage** rather than being built on the assumption
   that faster is better.

## Deferred / still open

- Scroll fix still **unconfirmed by the user** in the MacBook browser. Root cause was
  found and fixed 2026-08-02 (`body { min-height }` prevented `#conversation` from
  ever becoming a scroll container) but the fix has not been visually verified.
  Reload only — no APK install needed.
- Spend guard pricing rates still marked `VERIFY` in
  `config/modules/spend_guard.yaml`.
- Deploy assertion's failure paths untested against the live VM.

## Note for parallel sessions

The new assertion tells you **what is live**; it does not tell you **who put it
there**. With two chat windows open, either window's deploy ships whatever both have
committed, so a per-session "not deployed" note is only true until the other window
deploys.
