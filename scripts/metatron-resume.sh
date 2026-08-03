#!/bin/bash
# Restarts the metatron-vm instance and waits for the server to come back
# up (metatron-server, metatron-scheduler are systemd-enabled and start
# automatically on boot). Confirms health before exiting.
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
    if [ -n "$status" ]; then
        echo "Server is up: $status"
        exit 0
    fi
    echo "Waiting for boot... (${elapsed}s / ${timeout}s)"
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
echo "Timed out waiting for server after ${timeout}s — check manually: gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap"
exit 1
