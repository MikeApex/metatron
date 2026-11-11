import base64
import json
import os
from datetime import datetime, timezone

from google.cloud import storage
from google.api_core.exceptions import NotFound
from googleapiclient import discovery


PROJECT_ID = os.environ.get("GCP_PROJECT", "metatron-ai-499810")
PROJECT_NAME = f"projects/{PROJECT_ID}"
OVERRIDE_BUCKET = "metatron-billing-state"
OVERRIDE_OBJECT = "override.json"


def _override_active() -> bool:
    """
    Checks for a manual-override marker written by a human intentionally
    re-enabling billing (e.g. scripts/metatron-resume.sh). Budget notification
    propagation after an edit can take several minutes, during which stale
    notifications carrying the old (lower) budget keep arriving and re-disabling
    billing the human just restored. The override gives a fixed cooldown window
    where this function logs instead of acting, so a deliberate relink sticks.
    """
    try:
        client = storage.Client()
        blob = client.bucket(OVERRIDE_BUCKET).blob(OVERRIDE_OBJECT)
        marker = json.loads(blob.download_as_text())
        until = datetime.fromisoformat(marker["until"])
        return datetime.now(timezone.utc) < until
    except (NotFound, KeyError, ValueError):
        return False


def stop_billing(data, context):
    """Disable billing on the project when budget threshold is exceeded."""
    pubsub_data = base64.b64decode(data["data"]).decode("utf-8")
    budget_data = json.loads(pubsub_data)

    cost_amount = budget_data.get("costAmount", 0)
    budget_amount = budget_data.get("budgetAmount", 0)

    if cost_amount <= budget_amount:
        print(f"Cost {cost_amount} under budget {budget_amount} — no action.")
        return

    if _override_active():
        print(f"Cost {cost_amount} exceeded budget {budget_amount} — manual override active, skipping disable.")
        return

    print(f"Cost {cost_amount} exceeded budget {budget_amount} — disabling billing.")
    billing = discovery.build("cloudbilling", "v1", cache_discovery=False)
    billing.projects().updateBillingInfo(
        name=PROJECT_NAME,
        body={"billingAccountName": ""},
    ).execute()
    print("Billing disabled.")
