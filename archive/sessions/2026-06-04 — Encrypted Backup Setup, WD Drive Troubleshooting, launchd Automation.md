# 2026-06-04 — Encrypted Backup Setup, WD Drive Troubleshooting, launchd Automation

## What was built

### Restic backup infrastructure (scripts ready, drives pending)
- [scripts/backup.sh](../../scripts/backup.sh) — full Restic backup to Drive 1, rsync mirror to Drive 2, forget/prune policy (7 daily / 4 weekly / 12 monthly), integrity spot-check
- [scripts/backup-setup-passphrase.sh](../../scripts/backup-setup-passphrase.sh) — one-time keychain passphrase storage helper
- [scripts/com.life-manager.backup.plist](../../scripts/com.life-manager.backup.plist) — launchd plist that fires on drive mount (WatchPaths)
- Excludes: `certs/`, `.venv/`, `__pycache__/`, `*.pyc`, `data/voices/`, `tools/kokoro/`, `data/personas/*/memory/*.faiss`

### Interim single-file encrypted backup (active now)
- Manual one-liner: `tar | openssl enc -aes-256-cbc -pbkdf2 -iter 600000`
- Confirmed working — backup verified at 8.5 MB (kokoro excluded, compresses well)
- Backups land in `~/Library/Application Support/life-manager-backups/`

### Daily automated backup via launchd
- [scripts/daily-backup.sh](../../scripts/daily-backup.sh) — fires osascript password dialog at noon; Cancel = skip, passphrase entry = immediate backup; skips silently if today's backup already exists
- [scripts/com.life-manager.daily-backup.plist](../../scripts/com.life-manager.daily-backup.plist) — LaunchAgent, StartCalendarInterval Hour=12
- Installed at `~/Library/LaunchAgents/com.life-manager.daily-backup.plist`
- Retains 30 days of backups, auto-prunes older files

## Decisions made

- **Passphrase approach changed mid-session**: originally used macOS Keychain (`security find-generic-password`); changed to interactive osascript dialog at user's request — simpler, no keychain dependency, user controls when backup actually runs
- **Noon over midnight**: user-initiated prompt at noon preferred over silent midnight automation
- **kokoro excluded**: discovered mid-session that `tools/kokoro` is 903 MB (TTS model, re-downloadable); added to exclude list in both scripts
- **Backup destination**: `~/Library/Application Support/life-manager-backups/` — hidden from Finder by default (use Cmd+Shift+G or Option+Go menu to reach)

## Troubleshooting resolved

### WD Elements drive not recognized
- USB-A → USB-C adapter was power-only (no data pins) — confirmed by phone also failing to mount
- Resolution deferred: user needs USB-C hub with USB-A port, or USB-C to Micro-USB cable
- Existing PC data on drive must be preserved — no reformatting

### launchd exit code 126 / "Operation not permitted"
- Root cause: launchd does not inherit Terminal's Full Disk Access; `~/Desktop` is FDA-protected
- Fix: added `/bin/bash` to Full Disk Access (System Settings → Privacy & Security → Full Disk Access → + → /bin/bash)
- Confirmed working after fix

## Deferred

- Restic full setup (drives, `restic init`, passphrase in keychain, drive-mount plist) — blocked on working USB-C hub/adapter
- Older backups at `~/Desktop/Life Mgr Backups/` (May 26, May 28) — not yet consolidated or cleaned up
- 3-2-1 rule not yet met — currently only 1 copy (on-machine encrypted file)

## Verification commands

```bash
# List backups
ls -lh "$HOME/Library/Application Support/life-manager-backups/"

# Verify a backup
openssl enc -d -aes-256-cbc -pbkdf2 -iter 600000 \
  -in "$HOME/Library/Application Support/life-manager-backups/life-manager-backup-$(date +%Y-%m-%d).enc" \
| tar -tzf - | head -40

# Manual backup one-liner
mkdir -p "$HOME/Library/Application Support/life-manager-backups" && \
tar -czf - \
  --exclude="$HOME/Desktop/multi-model-mcp/certs" \
  --exclude="$HOME/Desktop/multi-model-mcp/.venv" \
  --exclude="$HOME/Desktop/multi-model-mcp/__pycache__" \
  --exclude="$HOME/Desktop/multi-model-mcp/data/voices" \
  --exclude="$HOME/Desktop/multi-model-mcp/tools/kokoro" \
  "$HOME/Desktop/multi-model-mcp" \
| openssl enc -aes-256-cbc -pbkdf2 -iter 600000 \
  -out "$HOME/Library/Application Support/life-manager-backups/life-manager-backup-$(date +%Y-%m-%d).enc"
```
