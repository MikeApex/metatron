#!/bin/bash
# scripts/renew_cert.sh — keep the VM's TLS certificate alive.
#
# THE INCIDENT THIS EXISTS FOR (2026-09-19). The cert in certs/ was minted by hand
# with `tailscale cert` on 2026-06-21 and nothing was ever scheduled to renew it.
# Let's Encrypt certs last 90 days, so it expired at 12:23 UTC on 2026-09-19 and
# every client died at once — phone and desktop both — while the server itself was
# perfectly healthy: 29 days uptime, NRestarts=0, serving a full pipeline turn
# twenty minutes earlier.
#
# It was hard to see precisely because the server was fine. `curl -k` returned a
# clean 401 and `tailscale status` was green, so the first three checks all said
# "healthy". The distinguishing test is curl WITHOUT -k: a browser and the Android
# WebView both validate the cert, and -k is the one flag that skips exactly the
# thing that had broken.
#
# Run from a systemd timer (§ docs/INFRASTRUCTURE.md → TLS certificate renewal).
#
# RESTARTS ONLY IF THE CERT ACTUALLY CHANGED. `tailscale cert` returns the cached
# cert until it is close to expiry, so on almost every run there is nothing to do —
# and a daily unconditional restart would drop a live session 365 times a year to
# fix a problem that occurs four times. That is the standing rule here: act on
# actual change, never preemptively on a routine run.

set -euo pipefail

DOMAIN="metatron-vm.tail0acc5d.ts.net"
CERT_DIR="/home/md-homefolder/multi-model-mcp/certs"
CERT="$CERT_DIR/server.crt"
KEY="$CERT_DIR/server.key"
SERVICE="metatron-server"
OWNER="md-homefolder:md-homefolder"

before=""
[ -f "$CERT" ] && before="$(sha256sum "$CERT" | cut -d' ' -f1)"

# Writes both files. Idempotent: returns the existing cert unless it is near expiry.
tailscale cert --cert-file "$CERT" --key-file "$KEY" "$DOMAIN"

# `tailscale cert` runs as root under systemd, so both files land root-owned and the
# key at mode 600 — unreadable by the service user, which would take the server down
# on its next restart with a cert that is perfectly valid. This is the step that is
# easy to leave out and turns a fix into an outage.
chown "$OWNER" "$CERT" "$KEY"
chmod 644 "$CERT"
chmod 600 "$KEY"

after="$(sha256sum "$CERT" | cut -d' ' -f1)"

if [ "$before" = "$after" ]; then
    echo "cert unchanged ($(openssl x509 -in "$CERT" -noout -enddate | cut -d= -f2)) — no restart"
    exit 0
fi

echo "cert renewed, now valid to $(openssl x509 -in "$CERT" -noout -enddate | cut -d= -f2)"
# Certs are read at startup, so a new file on disk changes nothing until this runs.
systemctl restart "$SERVICE"
echo "restarted $SERVICE"
