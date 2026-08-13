#!/usr/bin/env bash
# scripts/rm_worktree.sh — tear down a worktree created by new_worktree.sh.
#
# Usage:
#   ./scripts/rm_worktree.sh <slug>           # refuses if work would be lost
#   ./scripts/rm_worktree.sh <slug> --force   # removes anyway
#
# Removal is the dangerous half of the pair, so the checks are the point of the
# script. It refuses when the worktree holds uncommitted changes, or commits that
# are not reachable from main — either of which means removing it destroys work
# that exists nowhere else.
#
# What it deliberately does NOT do: delete the branch when commits are unmerged.
# A branch costs nothing to keep and is the only recovery path if the removal was
# a mistake. Fully-merged branches are deleted, because leaving them means the
# next new_worktree.sh with the same slug fails on a stale ref.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SLUG=""
FORCE=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --force|-f)
            FORCE=1
            shift
            ;;
        -h|--help)
            echo "usage: $0 <slug> [--force]"
            exit 0
            ;;
        -*)
            echo "error: unknown option '$1'" >&2
            echo "usage: $0 <slug> [--force]" >&2
            exit 1
            ;;
        *)
            if [[ -n "$SLUG" ]]; then
                echo "error: unexpected argument '$1' (slug already set to '$SLUG')" >&2
                exit 1
            fi
            SLUG="$1"
            shift
            ;;
    esac
done

if [[ -z "$SLUG" ]]; then
    echo "usage: $0 <slug> [--force]" >&2
    echo
    echo "Current worktrees:" >&2
    git -C "$ROOT" worktree list >&2
    exit 1
fi

if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9_-]{0,39}$ ]]; then
    echo "error: '$SLUG' is not a valid worktree slug." >&2
    exit 1
fi

DEST="$(dirname "$ROOT")/metatron-wt-$SLUG"
BRANCH="wt/$SLUG"

if [[ ! -d "$DEST" ]]; then
    echo "error: no worktree at $DEST" >&2
    echo
    echo "Current worktrees:" >&2
    git -C "$ROOT" worktree list >&2
    exit 1
fi

# Confirm this is actually a worktree of THIS repo before removing anything. The
# path is derived from a slug, and a directory that merely happens to sit at that
# name is not something to delete.
if ! git -C "$ROOT" worktree list --porcelain | grep -qx "worktree $DEST"; then
    echo "error: $DEST exists but is not a registered worktree of this repo." >&2
    echo "  refusing to remove it. Inspect it by hand." >&2
    exit 1
fi

echo "Removing worktree '$SLUG'"
echo "  path    $DEST"
echo "  branch  $BRANCH"
echo

# Uncommitted work. Ignored files (the symlinks, copied fixtures) do not appear
# here, which is what makes this check meaningful rather than always-dirty.
DIRTY="$(git -C "$DEST" status --porcelain)"

# Commits that exist only on this branch. `main` is the integration branch for
# this project; a worktree branch ahead of it holds work that is nowhere else.
UNMERGED=""
if git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    UNMERGED="$(git -C "$ROOT" log --oneline "main..$BRANCH" 2>/dev/null || true)"
fi

if [[ -n "$DIRTY" || -n "$UNMERGED" ]]; then
    if [[ "$FORCE" -eq 0 ]]; then
        echo "REFUSING — this worktree holds work that would be lost." >&2
        echo >&2
        if [[ -n "$DIRTY" ]]; then
            echo "  Uncommitted changes:" >&2
            echo "$DIRTY" | sed 's/^/    /' >&2
            echo >&2
        fi
        if [[ -n "$UNMERGED" ]]; then
            echo "  Commits on $BRANCH not reachable from main:" >&2
            echo "$UNMERGED" | sed 's/^/    /' >&2
            echo >&2
        fi
        echo "  Merge or discard first, or re-run with --force to remove anyway." >&2
        exit 1
    fi

    echo "  --force: removing despite uncommitted changes and/or unmerged commits."
    if [[ -n "$UNMERGED" ]]; then
        echo "  The branch $BRANCH is KEPT so those commits remain recoverable."
    fi
    echo
fi

# --force on `git worktree remove` bypasses its refusal over ignored/untracked
# files — the symlinks and any copied fixtures. The checks above are what decide
# whether removal is safe; this flag only stops git second-guessing them.
#
# The symlinks point at the main tree's .venv, .env and certs. Removing a symlink
# removes the link, never the target — verified, and worth stating because
# getting it wrong would delete the main tree's virtualenv.
git -C "$ROOT" worktree remove --force "$DEST"
echo "  removed  $DEST"

if [[ -n "$UNMERGED" ]]; then
    echo "  kept     branch $BRANCH (holds unmerged commits)"
    echo
    echo "Recover with:  git -C $ROOT log $BRANCH"
    echo "Delete it with: git -C $ROOT branch -D $BRANCH"
elif git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    git -C "$ROOT" branch -d "$BRANCH" >/dev/null
    echo "  deleted  branch $BRANCH (fully merged)"
fi

echo
echo "Worktree '$SLUG' removed."
