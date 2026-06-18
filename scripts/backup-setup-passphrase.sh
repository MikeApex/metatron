#!/usr/bin/env bash
# One-time helper: store your Restic passphrase in the macOS keychain.
# Run this once per machine. The passphrase is never written to disk in plain text.
#
# After running this, backup.sh will read the passphrase silently via
#   security find-generic-password -a "$USER" -s restic-life-manager -w

set -euo pipefail

SERVICE="restic-life-manager"

echo "Enter the Restic passphrase for '$SERVICE'."
echo "This will be stored in your macOS keychain (Keychain Access → login)."
echo "You will be prompted for your macOS login password to authorize the write."
echo ""

security add-generic-password \
    -a "$USER" \
    -s "$SERVICE" \
    -T "" \
    -w

echo ""
echo "Passphrase stored. Verify with:"
echo "  security find-generic-password -a \"\$USER\" -s \"$SERVICE\" -w"
