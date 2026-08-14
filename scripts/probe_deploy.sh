#!/usr/bin/env bash
# scripts/probe_deploy.sh — exercise deploy.sh's mutual exclusion WITHOUT deploying.
#
# §10b run 2, check 8: "two windows run ./deploy.sh at once; the second refuses,
# naming the first". That check cannot be run against the real script.
#
#   Never test a Bash permission rule by running the real command. The test only
#   reaches execution in the branch where the rule FAILS, so a negative result
#   *is* the damage. `./deploy.sh` is in `deny` in .claude/settings.json and stays
#   there. It has no argument parsing whatsoever — no `case`, no `getopts`, no
#   `$1` in 269 lines — so there is no "harmless flag" that makes it inert. It
#   ignores unknown arguments and proceeds to push, SSH the VM, pull, pip install
#   and restart both systemd units.
#
# So this runs deploy.sh's lock block and nothing else, extracted VERBATIM at run
# time by sed range — the same approach as scripts/check_deploy_lock.sh, and for
# the same reason. A hand-copied lock is a lock that keeps passing after someone
# edits the original: that is precisely the defect that made the first lock probe
# worthless (2026-08-13).
#
# The difference from check_deploy_lock.sh: that one asserts both trees compute
# the SAME lock path (H2). This one asserts the lock actually EXCLUDES a second
# holder, and that the refusal names the first. Path agreement does not imply
# mutual exclusion, which is why check 8 was still unobserved with the sweep green.
#
# Usage — run from two windows, first one then the other while it is still held:
#     ./scripts/probe_deploy.sh 60      # window A: acquires, holds 60s
#     ./scripts/probe_deploy.sh 5       # window B: must REFUSE, naming A's PID
#
# Exit 0 = acquired and released. Exit 1 = refused (which is a PASS for window B).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY="$ROOT/deploy.sh"
HOLD="${1:-30}"

[ -f "$DEPLOY" ] || { echo "probe_deploy: no deploy.sh at $DEPLOY" >&2; exit 1; }

# From the lock-path resolution through the stamping of the lock's own metadata.
# Deliberately stops at the `date ... > started` line: everything after it in
# deploy.sh is the actual deploy.
BLOCK="$(sed -n "/^_deploy_script_dir=/,/^date '+%Y-%m-%d/p" "$DEPLOY")"

if [ -z "$BLOCK" ] ||
   ! grep -q 'git-common-dir' <<<"$BLOCK" ||
   ! grep -q 'DEPLOY REFUSED' <<<"$BLOCK" ||
   ! grep -q 'mkdir "\$LOCK_DIR"' <<<"$BLOCK"; then
    cat >&2 <<EOF
probe_deploy: could not extract deploy.sh's lock block, or it no longer contains
  the three things this probe exists to exercise (git-common-dir resolution, the
  refusal message, the atomic mkdir).

  This probe runs the REAL block, so a restructure trips it by design. If the
  change was deliberate, re-point the sed range here and in
  scripts/check_deploy_lock.sh. Do not hand-copy the block in as a substitute —
  a copy tests a lock that is not the one deploy.sh uses.
EOF
    exit 1
fi

# HARD SAFETY ASSERTION — the whole point of the decoy is that it cannot deploy.
#
# If someone widens the sed range above (or deploy.sh is restructured so the
# range runs long), this script would eval a real push/SSH. That failure is
# silent and irreversible, and it is the exact shape of the mistake the decoy
# exists to avoid. So refuse to eval a block that contains any of it.
if grep -qE 'git push|gcloud|ssh |systemctl|pip install' <<<"$BLOCK"; then
    cat >&2 <<EOF
probe_deploy: ABORT — the extracted block contains deploy commands.

  The sed range has captured more than the lock. Evaluating this would push to
  GitHub and touch the VM, which is the one thing this script must never do.
  Narrow the range; do not suppress this check.

  Offending lines:
$(grep -nE 'git push|gcloud|ssh |systemctl|pip install' <<<"$BLOCK" | sed 's/^/    /')
EOF
    exit 1
fi

echo "probe_deploy: running deploy.sh's lock block verbatim ($(wc -l <<<"$BLOCK" | tr -d ' ') lines), no deploy."

# Substitute deploy.sh's real path for ${BASH_SOURCE[0]} textually, so the lock
# resolves to exactly what deploy.sh would compute — not to this script's path.
#
# Textually, not by assigning BASH_SOURCE: bash resets BASH_SOURCE on assignment,
# and check_deploy_lock.sh already shipped that bug once. It made both sides
# resolve to the empty string, which compared equal and printed "ok" — a check
# that passed by failing identically on both sides.
eval "${BLOCK//\$\{BASH_SOURCE\[0\]\}/$DEPLOY}"

echo ""
echo "probe_deploy: ACQUIRED"
echo "    lock:  $LOCK_DIR"
echo "    pid:   $$"
echo "    held:  ${HOLD}s — start the second window now"
echo ""

sleep "$HOLD"

echo "probe_deploy: releasing (trap removes $LOCK_DIR)"
exit 0
