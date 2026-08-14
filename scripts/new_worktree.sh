#!/usr/bin/env bash
# scripts/new_worktree.sh — create an isolated worktree for parallel work.
#
# Two windows working the same tree collide at line granularity. On 2026-08-09 a
# commit staged by explicit filename swept up another session's routing change and
# ./deploy.sh put it live while its governing instructions sat uncommitted. A
# worktree makes that class of collision structurally impossible: separate
# checkout, separate branch, separate index.
#
# Usage:
#   ./scripts/new_worktree.sh <slug>                  # ../metatron-wt-<slug>
#   ./scripts/new_worktree.sh <slug> --with-personas  # + synthetic fixtures
#
# A fresh checkout lacks everything gitignored, which is most of what the runtime
# needs to start. This symlinks those back to the main tree so `import
# core.orchestrator` works and the server can boot.
#
# Persona data is NOT linked by default. Two separate reasons, and only the second
# is about safety:
#   1. config/personas/mike/ is VM-owned. The standing rule is that a stale Mac
#      copy is what gets pushed by mistake, and N worktrees means N places for one
#      to appear. mike is excluded by name from --with-personas for that reason.
#   2. data/personas/*/ is gitignored, but .gitignore DOES NOT UNTRACK, and seed
#      fixtures committed before the rule landed are still tracked. So a worktree
#      does not lack the synthetic fixtures — it gets a HOLLOW version of them.
#      Measured 2026-08-13: sarah_chen is 3 tracked files out of 26 on disk;
#      danny_park 9, maya_torres 3, cal_newport 3.
#
#      That is worse than absent, and it is why this flag exists. An absent
#      fixture fails loudly on the first open. A hollow one is a directory that
#      exists, so a suite can get far enough to produce a result — against
#      incomplete data. mike is the exception at 0 tracked files, so the one tree
#      that must never appear here genuinely does not.
#
# --with-personas COPIES rather than symlinks, overlaying the hollow checkout with
# the main tree's full contents. The fixtures total ~9MB, so the copy is cheap,
# and a symlink would put three concurrent workers' suite runs into the same
# context.json — reintroducing the exact collision class worktrees exist to
# remove. The copy is a snapshot: changes in it do not flow back.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

SLUG=""
WITH_PERSONAS=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --with-personas)
            WITH_PERSONAS=1
            shift
            ;;
        -h|--help)
            echo "usage: $0 <slug> [--with-personas]"
            exit 0
            ;;
        -*)
            echo "error: unknown option '$1'" >&2
            echo "usage: $0 <slug> [--with-personas]" >&2
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
    echo "usage: $0 <slug> [--with-personas]" >&2
    echo "  slug must match ^[a-z0-9][a-z0-9_-]{0,39}\$ — it becomes a directory" >&2
    echo "  name and a branch name." >&2
    exit 1
fi

# Same shape as the persona-name rule: this becomes a filesystem path and a git
# ref, so reject rather than sanitise.
if ! [[ "$SLUG" =~ ^[a-z0-9][a-z0-9_-]{0,39}$ ]]; then
    echo "error: '$SLUG' is not a valid worktree slug." >&2
    echo "  must match ^[a-z0-9][a-z0-9_-]{0,39}\$ — lowercase letters, digits," >&2
    echo "  underscores and hyphens only." >&2
    exit 1
fi

DEST="$(dirname "$ROOT")/metatron-wt-$SLUG"
BRANCH="wt/$SLUG"

if [[ -e "$DEST" ]]; then
    echo "error: $DEST already exists." >&2
    echo "  remove it first:  ./scripts/rm_worktree.sh $SLUG" >&2
    exit 1
fi

if git -C "$ROOT" show-ref --verify --quiet "refs/heads/$BRANCH"; then
    echo "error: branch '$BRANCH' already exists." >&2
    echo "  a previous worktree with this slug was removed but its branch kept." >&2
    echo "  either pick another slug, or delete it:  git branch -D $BRANCH" >&2
    exit 1
fi

echo "Creating worktree '$SLUG'"
echo "  path    $DEST"
echo "  branch  $BRANCH  (from $(git -C "$ROOT" rev-parse --short HEAD))"
echo

git -C "$ROOT" worktree add -b "$BRANCH" "$DEST" HEAD

echo
echo "Linking gitignored runtime dependencies:"

# Absolute targets: the worktree sits beside the main tree, but a relative link
# would break if either is moved and would fail silently at import time.
link_back() {
    local rel="$1"
    local src="$ROOT/$rel"
    local dst="$DEST/$rel"

    if [[ ! -e "$src" ]]; then
        echo "  absent   $rel  (not present in the main tree — skipped)"
        return 0
    fi

    mkdir -p "$(dirname "$dst")"

    if [[ -e "$dst" || -L "$dst" ]]; then
        echo "  exists   $rel  (worktree already has it — left alone)"
        return 0
    fi

    ln -s "$src" "$dst"
    echo "  linked   $rel"
}

# .env and vertex-key.json are credentials; certs/ is machine-specific TLS.
# settings.local.json holds machine-specific paths. All four are gitignored, so a
# fresh checkout has none of them.
link_back ".venv"
link_back ".env"
link_back "vertex-key.json"
link_back "certs"
link_back ".claude/settings.local.json"

# .dev_backlog_seen is COPIED, not linked — the one exception above, and the
# asymmetry is the whole point.
#
# Without it a worktree starts with an empty ledger, so the SessionStart sync
# re-pulls the ENTIRE VM event history as new and writes it into that tree's
# DEV_BACKLOG.md. Measured 2026-08-14 in a §10b rehearsal: 29 new, 16 inbox, in a
# tree that was deleted minutes later. Committing that file from a worktree would
# resurrect already-closed items into the tracked backlog — precisely what the
# ledger exists to prevent (see its comment in sync_dev_backlog.py).
#
# Linking it back would be the obvious fix and is strictly worse. A shared ledger
# lets a worktree mark 29 events seen and then vanish with rm_worktree.sh, after
# which the main tree never pulls them again: a noisy duplicate becomes a SILENT
# LOST change request, which is the failure fold_fragments() is built to avoid.
# A copy is stale in the safe direction — the worst case is re-pulling an event
# into the main tree, where it gets filed properly.
if [[ -f "$ROOT/.dev_backlog_seen" ]]; then
    cp "$ROOT/.dev_backlog_seen" "$DEST/.dev_backlog_seen"
    echo "  copied   .dev_backlog_seen  (snapshot — see comment: NOT a symlink)"
else
    echo "  absent   .dev_backlog_seen  (main tree has none yet — skipped)"
fi

if [[ "$WITH_PERSONAS" -eq 1 ]]; then
    echo
    echo "Copying synthetic persona fixtures (--with-personas):"

    if [[ ! -d "$ROOT/data/personas" ]]; then
        echo "  error: $ROOT/data/personas does not exist — nothing to copy." >&2
        exit 1
    fi

    mkdir -p "$DEST/data/personas"
    copied=0

    for src in "$ROOT"/data/personas/*/; do
        [[ -d "$src" ]] || continue
        name="$(basename "$src")"

        # mike is a real person's logs, journal, health and finances. It is
        # excluded here for the same reason .gitignore names it explicitly: not
        # because the loop needs help, but because the exclusion should be
        # readable at the point where someone would wonder about it.
        if [[ "$name" == "mike" ]]; then
            echo "  skipped  $name  (real persona — never copied into a worktree)"
            continue
        fi

        # The checkout has already created this directory holding whatever is
        # tracked, so copy the CONTENTS over it rather than the directory itself.
        # `cp -R "$src" "$dst"` with $dst existing nests it as $dst/$name — which
        # is what this did before it was tested against a real worktree.
        mkdir -p "$DEST/data/personas/$name"
        cp -R "$src". "$DEST/data/personas/$name/"

        tracked=$(git -C "$ROOT" ls-files "data/personas/$name" | wc -l | tr -d ' ')
        total=$(find "$DEST/data/personas/$name" -type f | wc -l | tr -d ' ')
        echo "  filled   $name  ($tracked tracked in checkout -> $total files," \
             "$(du -sh "$DEST/data/personas/$name" | cut -f1))"
        copied=$((copied + 1))
    done

    echo
    echo "  $copied fixture tree(s) filled in. This is a SNAPSHOT — changes made in"
    echo "  the worktree do not flow back to the main tree, and vice versa."
else
    echo
    echo "Persona fixtures NOT filled in. The checkout carries only what is TRACKED,"
    echo "which for these fixtures is a small fraction of what is on disk — e.g."
    echo "sarah_chen is 3 files here against 26 in the main tree. The directories"
    echo "exist, so a suite will start and then fail on a missing file, or run"
    echo "against incomplete data."
    echo
    echo "If the work involves the A4 safety or B1 red-team suites, tear this down"
    echo "and re-create with --with-personas."
fi

echo
# Everything this script adds is gitignored, so a correctly-set-up worktree
# starts with a clean status. Checking it here is not decoration: the first
# version linked .venv while .gitignore said `.venv/`, and a trailing slash does
# not match a symlink — so every worktree began permanently dirty and
# rm_worktree.sh's "would this lose work?" check refused every time, which would
# have made --force the routine path. That surfaced at teardown; it belongs here.
RESIDUE="$(git -C "$DEST" status --porcelain)"
if [[ -n "$RESIDUE" ]]; then
    echo "WARNING: this worktree is not clean immediately after setup:" >&2
    echo "$RESIDUE" | sed 's/^/    /' >&2
    echo >&2
    echo "  Something this script created is not covered by .gitignore. Left as-is," >&2
    echo "  rm_worktree.sh will refuse to remove this worktree every time." >&2
    echo "  Fix the ignore rule rather than working around it with --force." >&2
    echo >&2
fi

echo "Worktree '$SLUG' ready."
echo
echo "  cd $DEST"
echo "  python3 -c 'import core.orchestrator'    # confirms the links took"
echo
echo "When done:  ./scripts/rm_worktree.sh $SLUG"
