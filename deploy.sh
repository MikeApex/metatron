#!/bin/bash
set -e
echo "Pushing to GitHub..."
git push origin main
echo "Deploying to VM..."
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 -- bash -s <<'REMOTE'
set -e
cd ~/multi-model-mcp
git pull origin main
source .venv/bin/activate
pip install -q -r requirements.txt

# Scheduler has no active connections — restart immediately.
sudo systemctl restart metatron-scheduler

# Drain active SSE streams before restarting the server.
# Waits up to 3 minutes for in-flight pipelines to finish; force-restarts after timeout.
# Note: new requests can still arrive during the drain window (server stays up).
# A "no new sessions" mode is tracked in archive/plans/future_phases.md (Fix 3 scope).
echo "Checking for active SSE streams..."
timeout=180; elapsed=0; interval=5
while [ "$elapsed" -lt "$timeout" ]; do
    active=$(curl -sk https://localhost:8001/active 2>/dev/null \
        | python3 -c 'import sys,json; print(json.load(sys.stdin)["active_streams"])' 2>/dev/null \
        || echo 0)
    [ "$active" = "0" ] && { echo "No active streams — restarting server."; break; }
    echo "Draining: $active stream(s) active — ${elapsed}s / ${timeout}s elapsed..."
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
[ "$elapsed" -ge "$timeout" ] && echo "Drain timeout (${timeout}s) — restarting anyway."
sudo systemctl restart metatron-server
REMOTE
echo "Deploy complete."
