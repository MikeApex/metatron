#!/bin/bash
# Tells the stop-vm Cloud Function to leave metatron-vm running for the next N
# hours even while month-to-date spend is over the soft cap ($70).
#
# Use when you knowingly want to keep working past the internal budget — the
# soft cap is a speed bump, not a wall. The hard cap ($150, stop-billing) is
# unaffected by this and still applies.
#
# Deliberately a SEPARATE marker object from the billing override
# (override.json), so silencing the soft cap never silences the hard cap too.
#
# Usage: ./scripts/metatron-vm-override.sh [hours, default 8]
set -e
HOURS="${1:-8}"
UNTIL=$(python3 -c "
import datetime
print((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=$HOURS)).isoformat())
")
echo "{\"until\": \"$UNTIL\"}" | gsutil cp - gs://metatron-billing-state/override-vm.json
echo "VM soft-cap override active until $UNTIL ($HOURS hour(s) from now)."
echo "Hard cap (\$150, disables billing) still applies."
