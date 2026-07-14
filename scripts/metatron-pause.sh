#!/bin/bash
# Stops the metatron-vm instance entirely — halts Compute Engine and
# scheduler-driven Vertex AI billing while not actively developing.
# systemd (metatron-server, metatron-scheduler) come back up automatically
# on next boot; no state is lost. Run scripts/metatron-resume.sh to restart.
set -e
echo "Pausing Metatron — stopping metatron-vm..."
gcloud compute instances stop metatron-vm --zone=us-central1-a --project=metatron-ai-499810
echo "VM stopped. Compute Engine and scheduler billing paused."
