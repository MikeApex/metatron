#!/usr/bin/env bash
# Encrypted backup for ~/Desktop/multi-model-mcp using Restic.
#
# Triggered by launchd when Drive 1 mounts. Mirrors to Drive 2 via rsync.
# Passphrase is read from the system keychain — never stored on disk in plain text.
#
# To store passphrase in keychain (one-time setup):
#   security add-generic-password -a "$USER" -s "restic-life-manager" -w
# Then enter your passphrase at the prompt.

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────

SOURCE="$HOME/Desktop/multi-model-mcp"

# Volume names of your drives — edit these to match what macOS calls your drives.
DRIVE1_NAME="LifeBackup1"
DRIVE2_NAME="LifeBackup2"

DRIVE1="/Volumes/$DRIVE1_NAME"
DRIVE2="/Volumes/$DRIVE2_NAME"

REPO="$DRIVE1/restic-life-manager"
MIRROR="$DRIVE2/restic-life-manager-mirror"

LOGFILE="$HOME/Library/Logs/life-manager-backup.log"

KEYCHAIN_SERVICE="restic-life-manager"

# ── Helpers ──────────────────────────────────────────────────────────────────

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOGFILE"
}

die() {
    log "ERROR: $*"
    exit 1
}

# ── Pre-flight ────────────────────────────────────────────────────────────────

log "=== Backup started ==="

[[ -d "$DRIVE1" ]] || die "Drive 1 ($DRIVE1_NAME) is not mounted. Aborting."

# Read passphrase from keychain so it never touches the filesystem.
RESTIC_PASSWORD="$(security find-generic-password -a "$USER" -s "$KEYCHAIN_SERVICE" -w 2>/dev/null)" \
    || die "Passphrase not found in keychain. Run setup-passphrase to add it."
export RESTIC_PASSWORD

# ── Restic backup to Drive 1 ─────────────────────────────────────────────────

log "Running Restic backup → $REPO"

restic \
    --repo "$REPO" \
    backup "$SOURCE" \
    --exclude "$SOURCE/certs" \
    --exclude "$SOURCE/__pycache__" \
    --exclude "$SOURCE/.venv" \
    --exclude "$SOURCE/**/__pycache__" \
    --exclude "$SOURCE/**/*.pyc" \
    --exclude "$SOURCE/data/voices" \
    --exclude "$SOURCE/tools/kokoro" \
    --exclude "$SOURCE/data/personas/*/memory/*.faiss" \
    --tag "auto" \
    --verbose \
    2>&1 | tee -a "$LOGFILE"

log "Restic backup complete."

# ── Forget + prune ───────────────────────────────────────────────────────────

log "Running forget + prune (7 daily / 4 weekly / 12 monthly)..."

restic \
    --repo "$REPO" \
    forget \
    --keep-daily 7 \
    --keep-weekly 4 \
    --keep-monthly 12 \
    --prune \
    2>&1 | tee -a "$LOGFILE"

log "Prune complete."

# ── rsync mirror to Drive 2 (if mounted) ─────────────────────────────────────

if [[ -d "$DRIVE2" ]]; then
    log "Drive 2 ($DRIVE2_NAME) is mounted. Mirroring repo..."
    mkdir -p "$MIRROR"
    rsync \
        --archive \
        --delete \
        --checksum \
        --human-readable \
        --info=progress2 \
        "$REPO/" "$MIRROR/" \
        2>&1 | tee -a "$LOGFILE"
    log "Mirror complete → $MIRROR"
else
    log "Drive 2 ($DRIVE2_NAME) not mounted — skipping mirror (not an error)."
fi

# ── Integrity check (quick, on every run) ────────────────────────────────────

log "Spot-checking repo integrity (--read-data-subset=5%)..."

restic \
    --repo "$REPO" \
    check \
    --read-data-subset=5% \
    2>&1 | tee -a "$LOGFILE"

log "=== Backup finished ==="
