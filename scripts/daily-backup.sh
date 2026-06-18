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

tar -czf - \
    --exclude="$SOURCE/certs" \
    --exclude="$SOURCE/.venv" \
    --exclude="$SOURCE/__pycache__" \
    --exclude="$SOURCE/**/__pycache__" \
    --exclude="$SOURCE/**/*.pyc" \
    --exclude="$SOURCE/data/voices" \
    --exclude="$SOURCE/tools/kokoro" \
    --exclude="$SOURCE/data/personas/*/memory/*.faiss" \
    "$SOURCE" \
| openssl enc -aes-256-cbc -pbkdf2 -iter 600000 \
    -pass "env:PASSPHRASE" \
    -out "$OUTFILE"

# Prune backups older than 30 days.
find "$BACKUP_DIR" -name "life-manager-backup-*.enc" -mtime +"$RETAIN_DAYS" -delete

log "Backup complete: $OUTFILE ($(du -sh "$OUTFILE" | cut -f1))"

# Confirm success with a notification.
osascript -e 'display notification "Backup complete." with title "Life Manager Backup"' 2>/dev/null || true
