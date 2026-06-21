#!/bin/bash
set -e
echo "Pushing to GitHub..."
git push origin main
echo "Deploying to VM..."
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 -- \
  "cd ~/multi-model-mcp && git pull origin main && source .venv/bin/activate && pip install -q -r requirements.txt && sudo systemctl restart metatron-server metatron-scheduler"
echo "Deploy complete."
