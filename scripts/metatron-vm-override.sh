#!/bin/bash
# Tells the stop-vm Cloud Function to leave metatron-vm running for the next N
# hours even while month-to-date spend is over the soft cap.
#
# Use when you knowingly want to keep working past the internal budget — the
# soft cap is a speed bump, not a wall. The hard cap (stop-billing) is
# unaffected by this and still applies.
#
# Caps are $100 soft / $175 hard as of 2026-08-09, but they have been raised
# four times and the numbers below were stale for months before 2026-08-20.
# `docs/INFRASTRUCTURE.md` § Billing protection is the source of truth — read
# them there, not from this comment.
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
echo "The hard cap still applies — it disables billing, which is an outage, not a cost event."
