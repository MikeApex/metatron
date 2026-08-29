#!/usr/bin/env bash
# Pull live data off metatron-vm onto the MacBook.
#
# Why this exists: nothing on the VM is captured by git. data/personas/ is
# gitignored (correctly — it is real user data), and config/personas/mike/ is
# hand-copied, so neither travels through the repo. The 2026-07-31 VPC incident
# required deleting and rebuilding the instance; the data survived only because
# the boot disk was deliberately detached first. That was a near miss, not a
# backup.
#
# This is the PULL half of the chain. Once the data is on the Mac it lands
# inside the project directory, where the existing scripts/backup.sh (Restic →
# external drives, versioned and encrypted) carries it the rest of the way.
# Run this before those, or let the Restic run pick up whatever is here.
#
# Usage:
#   ./scripts/metatron-backup.sh            # pull, keep last 7 pulls
#   ./scripts/metatron-backup.sh --gcs      # also copy the tarball to GCS
#   RETAIN=14 ./scripts/metatron-backup.sh  # keep more local pulls

set -euo pipefail

VM="metatron-vm"
ZONE="us-central1-a"
PROJECT="metatron-ai-499810"
REMOTE_ROOT="multi-model-mcp"

LOCAL_ROOT="$HOME/Desktop/multi-model-mcp"
DEST="$LOCAL_ROOT/backups/vm"
RETAIN="${RETAIN:-7}"
GCS_BUCKET="gs://metatron-billing-state/vm-backups"

STAMP="$(date +%Y-%m-%d_%H%M%S)"
OUTFILE="$DEST/metatron-vm-data-$STAMP.tgz"
ERRLOG="$DEST/.last-run-stderr.log"

USE_GCS=0
[[ "${1:-}" == "--gcs" ]] && USE_GCS=1

log() { echo "[$(date '+%H:%M:%S')] $*"; }
die() { echo "ERROR: $*" >&2; exit 1; }

mkdir -p "$DEST"

# launchd gives a job a minimal PATH — /usr/bin:/bin:/usr/sbin:/sbin — which does
# not include Homebrew, so a bare `gcloud` resolves when this script is run by hand
# and not when the daily job runs it. Every scheduled run from 2026-08-04 to
# 2026-08-29 died on "gcloud: command not found", and because daily-backup.sh treats
# a failed pull as non-fatal, 26 days of encrypted archives shipped VM data frozen
# at 2026-08-03 while reporting success. Resolve the binary absolutely.
GCLOUD="$(command -v gcloud || true)"
if [[ -z "$GCLOUD" ]]; then
    for candidate in \
        /opt/homebrew/bin/gcloud \
        /usr/local/bin/gcloud \
        "$HOME/google-cloud-sdk/bin/gcloud" \
        /opt/homebrew/share/google-cloud-sdk/bin/gcloud \
        /usr/local/share/google-cloud-sdk/bin/gcloud
    do
        [[ -x "$candidate" ]] && { GCLOUD="$candidate"; break; }
    done
fi
[[ -n "$GCLOUD" ]] || die "gcloud not found on PATH or at any known SDK location."

# What we pull, and why:
#   data/personas/     — all persona data: logs, journals, traces, memory, CRM.
#                        The irreplaceable part.
#   config/personas/   — includes mike/, which is gitignored and hand-copied,
#                        so the repo has no copy of it at all.
#   data/conversations/metatron.db — Android chat history. Lives in the legacy
#                        directory and is still actively written.
#   data/baselines/    — cold-start semantic anchors; regenerating them costs
#                        a full Goals Interview.
#
# Deliberately excluded: .faiss indexes (rebuildable from the journals we do
# take, and large), __pycache__, .venv, tools/kokoro.
log "Pulling data from $VM ..."
if ! "$GCLOUD" compute ssh "$VM" --zone="$ZONE" --project="$PROJECT" --tunnel-through-iap \
        --command "cd ~/$REMOTE_ROOT && tar -czf - \
            --exclude='*/__pycache__' \
            --exclude='*.pyc' \
            --exclude='*.faiss' \
            data/personas config/personas data/baselines \
            data/conversations/metatron.db 2>/dev/null" \
        > "$OUTFILE" 2>"$ERRLOG"; then
    rm -f "$OUTFILE"
    die "pull failed — see $ERRLOG"
fi

# Prove the archive is good BEFORE pruning anything. A backup script that
# deletes old copies on the strength of an unverified new one is worse than
# no backup script.
[[ -s "$OUTFILE" ]] || { rm -f "$OUTFILE"; die "archive is empty"; }
FILE_COUNT="$(tar -tzf "$OUTFILE" 2>/dev/null | wc -l | tr -d ' ')"
[[ "$FILE_COUNT" -gt 10 ]] || { rm -f "$OUTFILE"; die "archive has only $FILE_COUNT entries — refusing"; }
tar -tzf "$OUTFILE" >/dev/null 2>&1 || { rm -f "$OUTFILE"; die "archive failed integrity check"; }

SIZE="$(du -h "$OUTFILE" | cut -f1)"
log "OK — $FILE_COUNT files, $SIZE → $OUTFILE"

# Stable-named hardlink to the newest verified pull. daily-backup.sh includes
# this one file and skips the dated history, so the daily encrypted archive
# always carries current VM data without compounding every previous pull into
# every future backup. A hardlink costs no extra disk.
ln -f "$OUTFILE" "$DEST/metatron-vm-latest.tgz"
log "latest → $DEST/metatron-vm-latest.tgz"

if [[ "$USE_GCS" -eq 1 ]]; then
    log "Copying to $GCS_BUCKET ..."
    "$GCLOUD" storage cp "$OUTFILE" "$GCS_BUCKET/" --project="$PROJECT" \
        && log "GCS copy done." \
        || log "WARNING: GCS copy failed — local copy is still good."
fi

# Prune only now that the new archive is verified.
KEEP=$(ls -1t "$DEST"/metatron-vm-data-*.tgz 2>/dev/null | tail -n +$((RETAIN + 1)) || true)
if [[ -n "$KEEP" ]]; then
    echo "$KEEP" | while read -r old; do
        log "pruning $(basename "$old")"
        rm -f "$old"
    done
fi

log "Done. $(ls -1 "$DEST"/metatron-vm-data-*.tgz 2>/dev/null | wc -l | tr -d ' ') pull(s) retained."
log "Restic (scripts/backup.sh) will carry these to the external drives."
