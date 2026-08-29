#!/usr/bin/env bash
# Daily encrypted backup of ~/Desktop/multi-model-mcp.
#
# Fired by launchd at noon. Shows a native macOS password dialog.
# Cancel or dismiss = exits silently. Enter passphrase = backs up immediately.
# If today's backup already exists, exits without prompting.

set -euo pipefail

SOURCE="$HOME/Desktop/multi-model-mcp"
BACKUP_DIR="$HOME/Library/Application Support/life-manager-backups"
LOGFILE="$HOME/Library/Logs/life-manager-backup.log"
RETAIN_DAYS=30

TODAY="$(date +%Y-%m-%d)"
OUTFILE="$BACKUP_DIR/life-manager-backup-$TODAY.enc"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

# Skip silently if already backed up today.
if [[ -f "$OUTFILE" ]]; then
    exit 0
fi

# Show native macOS password prompt.
PASSPHRASE=$(osascript \
    -e 'display dialog "Life Manager backup" & return & "Enter passphrase to back up now, or Cancel to skip." default answer "" with hidden answer with title "Life Manager Backup" buttons {"Cancel", "Back Up"} default button "Back Up"' \
    -e 'text returned of result' 2>/dev/null) || exit 0

# Exit silently if they clicked Cancel or left it blank.
[[ -z "$PASSPHRASE" ]] && exit 0

export PASSPHRASE

mkdir -p "$BACKUP_DIR"
log "=== Backup started ==="

# Pull current data off the VM first, so the archive below contains live server
# state and not just whatever is on this Mac. The VM holds the real persona data
# — logs, journals, traces — and none of it is in git.
#
# Best-effort: a VM that is paused, unreachable, or missing gcloud in launchd's
# PATH must not stop the local backup from running. A local-only backup is worth
# far more than no backup.
VM_NOTE=""
if [[ -x "$SOURCE/scripts/metatron-backup.sh" ]]; then
    log "Pulling VM data..."
    if "$SOURCE/scripts/metatron-backup.sh" >>"$LOGFILE" 2>&1; then
        log "VM pull OK."
    else
        log "WARNING: VM pull failed — archiving local state only."
        VM_NOTE="VM pull failed"
    fi
fi

# A failed pull leaves the previous metatron-vm-latest.tgz in place, so the archive
# below still contains VM data — just stale data, indistinguishable from current once
# it is encrypted. That is how the 2026-08-04 → 2026-08-29 gap stayed invisible: every
# run finished with a "Backup complete." notification and nobody had reason to look in
# the log. Age the file, and put the bad news where it will actually be seen.
VM_LATEST="$SOURCE/backups/vm/metatron-vm-latest.tgz"
if [[ -f "$VM_LATEST" ]]; then
    VM_AGE_DAYS=$(( ( $(date +%s) - $(stat -f %m "$VM_LATEST") ) / 86400 ))
    log "VM data in this archive is $VM_AGE_DAYS day(s) old."
    if (( VM_AGE_DAYS >= 2 )); then
        VM_NOTE="VM data is $VM_AGE_DAYS days old"
    fi
else
    log "WARNING: no VM data present — this archive is local state only."
    VM_NOTE="no VM data in this backup"
fi

tar -czf - \
    --exclude="$SOURCE/certs" \
    --exclude="$SOURCE/.venv" \
    --exclude="$SOURCE/__pycache__" \
    --exclude="$SOURCE/**/__pycache__" \
    --exclude="$SOURCE/**/*.pyc" \
    --exclude="$SOURCE/data/voices" \
    --exclude="$SOURCE/tools/kokoro" \
    --exclude="$SOURCE/data/personas/*/memory/*.faiss" \
    --exclude="$SOURCE/backups/vm/metatron-vm-data-*.tgz" \
    "$SOURCE" \
| openssl enc -aes-256-cbc -pbkdf2 -iter 600000 \
    -pass "env:PASSPHRASE" \
    -out "$OUTFILE"

# Prune backups older than 30 days.
find "$BACKUP_DIR" -name "life-manager-backup-*.enc" -mtime +"$RETAIN_DAYS" -delete

log "Backup complete: $OUTFILE ($(du -sh "$OUTFILE" | cut -f1))"

# Confirm the outcome with a notification. A degraded run must not look like a clean
# one — the local archive did get written either way, so "complete" alone is true but
# misleading when the irreplaceable half of the data is stale.
if [[ -n "$VM_NOTE" ]]; then
    log "WARNING: local archive written, but $VM_NOTE."
    osascript -e "display notification \"Local archive written, but $VM_NOTE.\" with title \"Life Manager Backup\" subtitle \"VM data NOT current\"" 2>/dev/null || true
else
    osascript -e 'display notification "Backup complete, VM data current." with title "Life Manager Backup"' 2>/dev/null || true
fi
