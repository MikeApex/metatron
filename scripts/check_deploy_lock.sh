#!/usr/bin/env bash
# scripts/check_deploy_lock.sh — assert the deploy lock is shared across worktrees.
#
# `[H8].3`. H2 was: `LOCK_DIR` derived from the script's own directory, and a
# worktree carries its own tracked copy of `deploy.sh`, so each tree computed a
# different lock path, both `mkdir` calls succeeded, and both deploys pushed and
# SSH'd the same VM. Fixed 2026-08-13 via `git rev-parse --git-common-dir`.
#
# **Nothing stopped a later session simplifying that back**, which is exactly how
# H2 arrived in the first place. So the invariant gets a check rather than a
# comment.
#
# It executes deploy.sh's own lock block, extracted verbatim at run time — not a
# copy of the logic. A copy would keep passing after someone edited the original,
# which is the failure mode this exists to prevent.
#
# Exit 0 = both trees agree on one lock path. Exit 1 = they diverge, or the block
# could not be found (it was renamed or restructured — also worth failing on).

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY="$ROOT/deploy.sh"

[ -f "$DEPLOY" ] || { echo "deploy-lock: no deploy.sh at $DEPLOY"; exit 1; }

# The block runs from `_deploy_script_dir=` to the `fi` that closes the if.
BLOCK="$(sed -n '/^_deploy_script_dir=/,/^fi$/p' "$DEPLOY")"
if [ -z "$BLOCK" ] || ! grep -q 'git-common-dir' <<<"$BLOCK"; then
    cat <<EOF
deploy-lock: could not extract the lock block from deploy.sh, or it no longer
  resolves via 'git rev-parse --git-common-dir'.

  This check runs deploy.sh's real lock block, so a restructure trips it by
  design. If the change was deliberate, re-point the sed range in
  scripts/check_deploy_lock.sh — do not delete the check. Two windows deploying
  at once is what it prevents (H2, confirmed live 2026-08-13).
EOF
    exit 1
fi

# Resolve the lock path as deploy.sh would, for a given copy of the script.
#
# The path is substituted into the block textually rather than by assigning
# BASH_SOURCE. **The first version did assign it and produced a false pass**:
# bash resets BASH_SOURCE on assignment, so `${BASH_SOURCE[0]}` was an unset
# array element, `set -u` aborted the subshell mid-eval, and both trees returned
# the empty string — which compared equal and printed "ok". A check that passes
# by failing identically on both sides is worse than no check.
resolve_lock() (
    set +u   # the block is deploy.sh's, not ours; don't impose our shell options
    eval "${BLOCK//\$\{BASH_SOURCE\[0\]\}/$1}"
    echo "$LOCK_DIR"
)

assert_path() {
    if [ -z "$2" ]; then
        echo "deploy-lock: FAIL — the $1 lock path resolved to the empty string."
        echo "  The lock block did not evaluate. This check must never report ok on an"
        echo "  empty path: two empty strings compare equal and look like agreement."
        exit 1
    fi
}

MAIN_LOCK="$(resolve_lock "$DEPLOY")"
assert_path "main-tree" "$MAIN_LOCK"

WT="$(mktemp -d)"/wt
CLEANUP() {
    git -C "$ROOT" worktree remove --force "$WT" >/dev/null 2>&1
    rm -rf "$(dirname "$WT")" >/dev/null 2>&1
}
trap CLEANUP EXIT

# --detach, so this never creates or moves a branch. A check that mutates the
# repo's branch list is a check people disable.
if ! git -C "$ROOT" worktree add --detach "$WT" HEAD >/dev/null 2>&1; then
    echo "deploy-lock: SKIP — could not create a temporary worktree (not a git repo?)"
    exit 0
fi

if [ ! -f "$WT/deploy.sh" ]; then
    echo "deploy-lock: FAIL — the worktree has no deploy.sh, so the lock cannot be compared."
    exit 1
fi

WT_LOCK="$(resolve_lock "$WT/deploy.sh")"
assert_path "worktree" "$WT_LOCK"

if [ "$MAIN_LOCK" != "$WT_LOCK" ]; then
    cat <<EOF
deploy-lock: FAIL — the two trees compute DIFFERENT lock paths, so both can
  deploy at once. This is H2, reintroduced.

    main tree: $MAIN_LOCK
    worktree:  $WT_LOCK

  The lock must resolve from 'git rev-parse --git-common-dir', relative to the
  script's own directory, made absolute.
EOF
    exit 1
fi

echo "deploy-lock: ok — both trees resolve to $MAIN_LOCK"
exit 0
