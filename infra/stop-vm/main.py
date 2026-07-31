"""
stop-vm — soft-cap cost control.

Stops metatron-vm when month-to-date spend crosses the internal budget. This is
the light switch. The hard cap (stop-billing, on the billing-cap topic) is the
grid tripping, and after 2026-07-30 we know what that costs: disabling billing
froze the project's VPC for over 25 hours, and Google's own restore never ran.
The VM had to be rebuilt on a new network to recover.

So the ordering is deliberate:

    ~$70   this function      stop the VM          recovery: one API call, ~60s
    ~$150  stop-billing       disable billing      recovery: days, and a frozen VPC

Stopping the VM removes the dominant cost (an e2-medium running 24/7, plus the
scheduler's periodic Vertex AI calls) while leaving every resource intact.

Triggered by a budget notification on the budget-soft-cap Pub/Sub topic rather
than by polling. GCP re-evaluates budgets several times a day and re-notifies
while spend stays over, which is more responsive than a daily poll and needs no
BigQuery billing export.

Note on notification payloads: costAmount and budgetAmount both come from the
message. A raised budget takes 10+ minutes to propagate, during which stale
notifications arrive carrying the OLD budget figure. That is what tripped the
hard cap on 2026-07-30 at ~$31 against a budget already raised to $40. The
override mechanism below exists for exactly that window.
"""

import base64
import json
import os
from datetime import datetime, timezone

import googleapiclient.discovery
from google.cloud import storage

PROJECT = os.environ.get("TARGET_PROJECT", "metatron-ai-499810")
ZONE = os.environ.get("TARGET_ZONE", "us-central1-a")
INSTANCE = os.environ.get("TARGET_INSTANCE", "metatron-vm")
OVERRIDE_BUCKET = os.environ.get("OVERRIDE_BUCKET", "metatron-billing-state")
OVERRIDE_BLOB = os.environ.get("OVERRIDE_BLOB", "override-vm.json")


def _override_active() -> bool:
    """
    True if a manual override marker exists and has not expired.

    Shares the mechanism (but not the object) with stop-billing, so pausing one
    safety net does not silently pause the other. Fails OPEN — if the check
    errors, we proceed to stop the VM. Stopping is cheap and reversible; the
    failure mode we care about is not stopping when we should.
    """
    try:
        blob = storage.Client().bucket(OVERRIDE_BUCKET).blob(OVERRIDE_BLOB)
        if not blob.exists():
            return False
        until = json.loads(blob.download_as_text()).get("until")
        if not until:
            return False
        return datetime.now(timezone.utc) < datetime.fromisoformat(until)
    except Exception as exc:  # noqa: BLE001 - see docstring: fail open
        print(f"override check failed ({exc}); proceeding as if no override")
        return False


def stop_vm(event, context):  # noqa: ARG001 - Cloud Functions signature
    payload = json.loads(base64.b64decode(event["data"]).decode("utf-8"))
    cost = float(payload.get("costAmount", 0))
    budget = float(payload.get("budgetAmount", 0))

    if cost <= budget:
        print(f"cost {cost} within budget {budget}; no action")
        return

    if _override_active():
        print(f"cost {cost} over budget {budget}, but manual override active; skipping")
        return

    compute = googleapiclient.discovery.build("compute", "v1", cache_discovery=False)

    state = compute.instances().get(
        project=PROJECT, zone=ZONE, instance=INSTANCE
    ).execute().get("status")

    # TERMINATED already means a previous notification acted. Budget alerts
    # re-fire repeatedly while spend stays over budget, so without this every
    # subsequent notification would issue a redundant stop.
    if state == "TERMINATED":
        print(f"{INSTANCE} already TERMINATED; nothing to do")
        return

    compute.instances().stop(project=PROJECT, zone=ZONE, instance=INSTANCE).execute()
    print(f"SOFT CAP HIT: cost {cost} > budget {budget}. Stopped {INSTANCE} "
          f"(was {state}). Restart with: gcloud compute instances start {INSTANCE} "
          f"--zone={ZONE} --project={PROJECT}")
