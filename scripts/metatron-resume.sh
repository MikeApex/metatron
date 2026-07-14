#!/bin/bash
# Restarts the metatron-vm instance and waits for the server to come back
# up (metatron-server, metatron-scheduler are systemd-enabled and start
# automatically on boot). Confirms health before exiting.
set -e
echo "Resuming Metatron — starting metatron-vm..."
gcloud compute instances start metatron-vm --zone=us-central1-a --project=metatron-ai-499810
echo "VM started. Waiting for server to come up..."

timeout=120; elapsed=0; interval=5
while [ "$elapsed" -lt "$timeout" ]; do
    status=$(gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 \
        --command="curl -sk http://localhost:8001/health" 2>/dev/null || echo "")
    if [ -n "$status" ]; then
        echo "Server is up: $status"
        exit 0
    fi
    echo "Waiting for boot... (${elapsed}s / ${timeout}s)"
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
echo "Timed out waiting for server after ${timeout}s — check manually: gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810"
