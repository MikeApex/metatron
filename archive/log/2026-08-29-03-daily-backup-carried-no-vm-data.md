### 2026-08-29 (the daily backup reported success for 26 days while carrying no current VM data) — uncommitted at time of writing, Mac-local scripts, no deploy

Mike asked where the daily backup file lands and whether it was hidden. It lands at
`~/Library/Application Support/life-manager-backups/life-manager-backup-YYYY-MM-DD.enc`, and it
is hidden — by macOS, not by the script: `~/Library` carries the filesystem `hidden` flag, so
Finder omits it. That was the whole of the question. The answer took two minutes; what the
lookup exposed took the session.

**The daily backup had not captured a single byte of live VM data since 2026-08-04.** Twenty-three
scheduled runs, zero successes — `grep -c "VM pull OK"` over the log returned **0**, for a log
that goes back to the feature's first day. Cause, one line in `backups/vm/.last-run-stderr.log`:
`gcloud: command not found`. launchd runs a job with a minimal `PATH`
(`/usr/bin:/bin:/usr/sbin:/sbin`) that excludes Homebrew, where gcloud lives
(`/opt/homebrew/bin/gcloud`), so a bare `gcloud` resolved when the script was run by hand — which
is how it was tested and how it "caught real Mac↔VM drift on its first run" (2026-08-03 entry) —
and never once when the daily job ran it.

**What that cost:** `metatron-vm-latest.tgz` was frozen at 2026-08-03 12:16, 3.9 MB. The fresh
pull is **27.9 MB, 454 files**. Every encrypted archive from 08-04 to 08-29 — 26 of them, the
whole 30-day retention window bar four days — shipped VM data 26 days stale. That data is the
irreplaceable half: `data/personas/` (logs, journals, traces, memory, CRM), `config/personas/mike/`
which is gitignored and hand-copied, `data/baselines/`, and the Android chat DB. None of it is in
git; that absence is the entire reason `metatron-backup.sh` exists.

**The correction worth carrying is not the PATH bug — it is that the failure was designed to be
quiet and nobody had modelled what quiet would cost.** `daily-backup.sh` treated a failed pull as
non-fatal, deliberately and correctly ("a local-only backup is worth far more than no backup"),
and its comment block *names* "missing gcloud in launchd's PATH" as an anticipated case. The
author foresaw the exact failure and then made it invisible. Two things compounded it: a failed
pull leaves the previous `metatron-vm-latest.tgz` in place, so the archive still *contained* VM
data — just old data, indistinguishable from current once encrypted; and the run still ended with
a `display notification "Backup complete."` A backup that degrades silently is worse than one that
fails loudly, because the loud one gets fixed the same day.

**Fixes, both Mac-local, no VM involvement and no `./deploy.sh`:**

1. **`scripts/metatron-backup.sh`** — resolve gcloud absolutely: `command -v` first, then a
   candidate list (`/opt/homebrew/bin`, `/usr/local/bin`, `~/google-cloud-sdk/bin`, both
   `share/google-cloud-sdk/bin` locations), and `die` with a clear message if none is executable.
   *Rejected: setting `PATH` via `EnvironmentVariables` in the plist.* The installed plist is a
   copy in `~/Library/LaunchAgents/`, so a repo-side edit changes nothing until an
   `unload`/`load`, and the fix would then live in a file the repo does not govern. Resolving in
   the script takes effect on the next run with no reload.
   *Rejected: hardcoding `/opt/homebrew/bin/gcloud`* — a value with a short half-life
   (Intel vs ARM Homebrew, a relocated SDK), which § *Infrastructure traps* rule 2 forbids.
2. **`scripts/daily-backup.sh`** — age `metatron-vm-latest.tgz` and route the bad news to the
   notification, which is the only surface Mike actually sees. Clean run says "Backup complete,
   VM data current."; ≥2 days stale says "VM data is N days old" with subtitle "VM data NOT
   current"; a missing file says so outright. The pull stays non-fatal — that call was right.

**Verification — the fix was proved under the failure condition, not in a shell where `PATH` hides
it:** `env -i HOME=… USER=… PATH=/usr/bin:/bin:/usr/sbin:/sbin /bin/bash scripts/metatron-backup.sh`
→ exit 0, 454 files, 27 MB, all nine persona dirs including `mike`, plus the Android DB. All three
notification branches exercised against real files (0 days → clean; the Aug-3 tarball → "25 days
old"; absent → "no VM data"). `bash -n` clean on both; `qa_sweep.sh` 9/9.

**Mike then rebuilt today's archive himself** (the script skips silently when the day's file
exists, and the rebuild needs his passphrase at the `osascript` dialog): 12:08:50 wrote the log's
**first-ever `VM pull OK.`** followed by the new `VM data in this archive is 0 day(s) old.`, and
the archive grew 240 MB → 273 MB, the delta matching the 27.9 MB VM tarball. Confirmed and closed.

**Two related gaps found and deliberately left, at Mike's "forget about the rest for now":**
`com.life-manager.backup.plist` — the Restic chain to the external drives — **is not installed**;
only `com.life-manager.daily-backup.plist` is in `~/Library/LaunchAgents/`, so there is currently
**no off-machine copy at all**, every archive sits on the internal disk. And the noon passphrase
dialog is a fragile trigger: run times scatter (12:00, 13:12, 15:11) as Mike notices the prompt,
and 08-11, 08-25 and 08-26 have no archive. Not filed to the backlog — he said to leave them —
recorded here so they are not lost.

**Close-out note:** a parallel window owned this tree throughout (Red session ③ — modified
`config/agents/*`, `core/scheduler.py`, `tools/accountability.py`, `tools/logger.py`,
`routing*.yaml`, plus two untracked A4 rerun test files and `accountability_judge.md`), and
`archive/handoffs/` held two files dated today. Per `/archive` step 0 and CLAUDE.md § Deploy
safety rule 4, this close-out staged **only** its own two scripts and this fragment, rewrote no
handoff paragraph belonging to session ③, and deleted no handoff files.

