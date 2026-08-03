#!/bin/bash
#
# Deploys code and shared config to the VM via GitHub.
#
# DO NOT ADD A PERSONA-CONFIG PUSH HERE. It is tempting, because
# config/personas/{persona}.md and config/personas/{persona}/ are gitignored and
# therefore never travel with a deploy — which looks like a gap. It is not.
#
# The VM is the source of truth for persona config, because the running system
# writes to it: write_persona() edits config/personas/{persona}.md and
# write_config() edits prime_directive.md and mission.md, both on the VM, in
# response to what the user asks for mid-conversation. Pushing the Mac's copy
# over the top destroys whatever the user has changed since it was last copied
# down. Verified 2026-08-03: the VM's mike.md held five preferences recorded that
# morning that the Mac copy knew nothing about.
#
# Authoring a genuinely new persona file: write it, scp it once, and let the VM
# own it from then on. Do not keep a Mac copy in config/personas/ — a stale copy
# is the thing that gets pushed by mistake.
#
#   gcloud compute scp <file> metatron-vm:~/multi-model-mcp/config/personas/<p>/ \
#     --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap
#
# Backup runs the other way: scripts/metatron-backup.sh pulls the VM's
# config/personas and data down to backups/vm/, and scripts/daily-backup.sh
# archives that.
#
set -e
echo "Pushing to GitHub..."
git push origin main
echo "Deploying to VM..."
# --tunnel-through-iap is required since the 2026-07-31 VPC rebuild: metatron-net
# has no public SSH ingress, only tcp:22 from the IAP range (35.235.240.0/20).
# Without it, ssh times out against the external IP.
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap -- bash -s <<'REMOTE'
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
