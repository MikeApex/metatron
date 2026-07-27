#!/bin/bash
# Writes a manual-override marker that tells the stop-billing Cloud Function
# to skip auto-disabling billing for the next N hours, even if a budget
# notification still reports cost over budget. Needed because GCP's budget
# notification pipeline can take several minutes to propagate a raised budget,
# during which stale notifications (carrying the old, lower budget) keep
# arriving and would otherwise re-disable billing right after you relink it.
#
# Usage: ./scripts/metatron-billing-override.sh [hours, default 4]
set -e
HOURS="${1:-4}"
UNTIL=$(python3 -c "
import datetime
print((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=$HOURS)).isoformat())
")
echo "{\"until\": \"$UNTIL\"}" | gsutil cp - gs://metatron-billing-state/override.json
echo "Manual billing override active until $UNTIL ($HOURS hour(s) from now)."
