#!/bin/bash
# Restarts the metatron-vm instance and waits for the server to come back
# up (metatron-server, metatron-scheduler are systemd-enabled and start
# automatically on boot). Confirms health, then the VM's outbound DNS, before exiting.
#
# If billing is currently disabled (the $-cap safety net tripped while paused),
# relinks it and then sets a manual billing-override marker: GCP's budget
# notification pipeline can take several minutes to reflect a raised budget,
# and stale notifications would otherwise re-disable billing right after this
# script relinks it. The override tells stop-billing to skip disabling for a
# few hours so the relink actually sticks. Only runs in the recovery case —
# a routine resume where billing was never disabled skips this entirely.
#
# Order is load-bearing (fixed 2026-07-30): the override marker lives in
# gs://metatron-billing-state, a bucket in the very project being disabled, so
# writing it while billing is off returns 403 "billing account ... is disabled".
# Under `set -e` that aborted the script before it ever reached the relink, so
# this recovery path never once completed. Relink first, then write the marker.
set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Outbound DNS from the VM — CLAUDE.md infrastructure trap 7. A resume has brought
# Tailscale's DNS relay up unhealthy, silently blocking ALL outbound name resolution,
# while /health (a constant, served on localhost) still says ok. Every model call then
# fails with NameResolutionError, so "Server is up" alone was false in exactly the
# failure a resume is known to cause (review 2026-11-05 #48).
#
# The remote prints a marker rather than relying on the exit code, so an SSH hiccup is
# reported as "could not check", not misdiagnosed as broken DNS. Retried twice: the
# fix changes VM config, so one transient miss must not prescribe it.
check_outbound_dns() {
    local out attempt
    echo "Checking outbound DNS from the VM..."
    for attempt in 1 2 3; do
        out=$(gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
            --tunnel-through-iap --command="timeout 15 getent hosts aiplatform.googleapis.com >/dev/null && echo DNS_OK || echo DNS_FAIL" 2>/dev/null || echo "")
        case "$out" in
            *DNS_OK*)   echo "Outbound DNS ok."; return 0 ;;
            *DNS_FAIL*) [ "$attempt" -lt 3 ] && sleep 5 ;;
            *)          echo "Could not reach the VM to check outbound DNS — unverified. Check by hand:" >&2
                        echo "  gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command='getent hosts aiplatform.googleapis.com'" >&2
                        exit 1 ;;
        esac
    done
    echo "" >&2
    echo "RESUME INCOMPLETE — the server is up, but the VM cannot resolve aiplatform.googleapis.com." >&2
    echo "Every reply and scheduled job will fail (NameResolutionError). Known cause: Tailscale" >&2
    echo "DNS came up unhealthy after the resume (CLAUDE.md infrastructure trap 7)." >&2
    echo "" >&2
    echo "Check, on the VM:  sudo tailscale status" >&2
    echo "Fix, on the VM:    sudo tailscale set --accept-dns=false" >&2
    echo "  gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \\" >&2
    echo "    --tunnel-through-iap --command='sudo tailscale status; sudo tailscale set --accept-dns=false'" >&2
    echo "Then re-run this script to confirm." >&2
    exit 1
}

BILLING_ENABLED=$(gcloud billing projects describe metatron-ai-499810 --format="value(billingEnabled)" 2>/dev/null || echo "False")
if [ "$BILLING_ENABLED" != "True" ]; then
    echo "ALERT: billing is currently disabled on metatron-ai-499810 (budget cap likely tripped)."
    gcloud billing projects link metatron-ai-499810 --billing-account=013F3D-66B5CD-955A3A
    echo "Billing relinked. Setting a manual override to survive budget-notification propagation lag..."
    "$SCRIPT_DIR/metatron-billing-override.sh" 4
fi

echo "Resuming Metatron — starting metatron-vm..."
gcloud compute instances start metatron-vm --zone=us-central1-a --project=metatron-ai-499810
echo "VM started. Waiting for server to come up..."

timeout=240; elapsed=0; interval=10
while [ "$elapsed" -lt "$timeout" ]; do
    # --tunnel-through-iap required since the 2026-07-31 VPC rebuild (no public SSH ingress).
    # /health requires authentication as of 2026-08-03. The token is minted on the VM,
    # which holds METATRON_AUTH_PASSWORD; scripts/mint_token.py is standard-library only,
    # so the system python3 is enough and the venv does not need activating.
    status=$(gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
        --tunnel-through-iap --command="cd ~/multi-model-mcp && curl -sk -H \"Authorization: Bearer \$(python3 scripts/mint_token.py)\" https://localhost:8001/health" 2>/dev/null || echo "")
    # Match on the payload, not on "did curl print anything". A 401 body
    # ({"detail":"Authentication required."}) is non-empty, so a bare -n test would
    # report a healthy server when the token mint had in fact failed — declaring
    # success at exactly the moment the server was unreachable to every client.
    case "$status" in
        *'"status"'*ok*)
            echo "Server is up: $status"
            check_outbound_dns
            exit 0
            ;;
        *"Authentication required"*)
            echo "Server responded but rejected the health token." >&2
            echo "METATRON_AUTH_PASSWORD is probably missing or different in the VM's .env." >&2
            exit 1
            ;;
    esac
    echo "Waiting for boot... (${elapsed}s / ${timeout}s)"
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
echo "Timed out waiting for server after ${timeout}s — check manually: gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap"
exit 1
