#!/usr/bin/env bash
# scripts/qa_sweep.sh — the verification leg, as a script rather than a model pass.
#
# Every check chained here already existed and was fired only by memory. Zero model
# tokens, so it actually gets run: called by /fix before it hands you a diff, by the
# SubagentStop gate before a worker may report done, and by /qa on demand.
#
# Usage:
#   ./scripts/qa_sweep.sh            # one summary line, detail only on failure
#   ./scripts/qa_sweep.sh --verbose  # full output from every check
#
# Exit 0 = nothing broken. Exit 1 = at least one real failure, detail printed.
#
# WHAT THIS CANNOT TELL YOU
# -------------------------
# py_compile is not sufficient and this script says so on every run. It parses; it
# does not execute. A stale `_SCHEDULER_CONFIG` reference passed py_compile and then
# crash-looped the scheduler after deploy, and the commit guard shipped with a
# NameError that py_compile had happily accepted. A green sweep means "nothing
# statically detectable is broken", never "this works" -- run the thing.
#
# Deliberately NOT wired into the quality-event stream or DEV_BACKLOG.md. Volume
# teaches a reader to skip the output, which is the same reason check_agent_tools.py
# was kept out of it.

set -uo pipefail   # NOT -e: every check must run even after one fails, or the
                   # first failure hides the rest and you fix them one round-trip
                   # at a time.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

VERBOSE=0
[[ "${1:-}" == "--verbose" || "${1:-}" == "-v" ]] && VERBOSE=1

FAILURES=()
NAMES=()
OUTPUT_DIR="$(mktemp -d)"
trap 'rm -rf "$OUTPUT_DIR"' EXIT

PY=python3
[[ -x "$ROOT/.venv/bin/python" ]] && PY="$ROOT/.venv/bin/python"

run_check() {
    local name="$1"; shift
    local out="$OUTPUT_DIR/$name.log"

    if "$@" >"$out" 2>&1; then
        NAMES+=("$name ok")
        [[ "$VERBOSE" -eq 1 ]] && { echo "--- $name (pass) ---"; cat "$out"; }
        return 0
    fi

    FAILURES+=("$name")
    NAMES+=("$name FAIL")
    [[ "$VERBOSE" -eq 1 ]] && { echo "--- $name (FAIL) ---"; cat "$out"; }
    return 1
}

# --- 1. Agent files vs registered tools -------------------------------------
# Exit 1 only on live-but-unbuilt: a tool named in live instruction text that
# register_tools() does not provide, which the model reads as a real capability.
run_check "agent-tools" "$PY" scripts/check_agent_tools.py --quiet

# --- 2. Persona consistency --------------------------------------------------
run_check "personas" "$PY" scripts/check_personas.py

# --- 3. One home per rule class ----------------------------------------------
run_check "rule-overlap" "$PY" scripts/check_rule_overlap.py

# --- 4. PROJECT_LOG.md matches its fragments ---------------------------------
# Catches a hand-edit to the generated file, which a rebuild would silently
# discard.
run_check "project-log" "$PY" scripts/build_project_log.py --check

# --- 5. py_compile over our own Python -------------------------------------
# See the caveat at the top: this proves the files parse, nothing more.
#
# TRACKED files only, via git ls-files -- not `find`. The plan specified "a
# py_compile sweep over core/ + tools/", which sounds like tens of files and is
# actually 11,247: tools/kokoro is a vendored TTS library of 11,183 .py files, of
# which exactly 3 are tracked. The find-based version took ~20 minutes and read as
# a hang. git ls-files is also the right boundary on principle -- this checks OUR
# code, and it stays correct when the next vendored dependency lands.
compile_sweep() {
    local failed=0
    local f
    while IFS= read -r f; do
        [[ -f "$f" ]] || continue
        "$PY" -m py_compile "$f" || failed=1
    done < <(git ls-files | grep -E '^(core|tools|scripts)/.*\.py$')
    return $failed
}
run_check "py-compile" compile_sweep

# --- 6. Duplicate backlog IDs ------------------------------------------------
# Two windows reserving the same DB-MMDD-NN. The backlog_inbox fragment path
# makes this structurally hard now, but hand-edits still happen.
# Only IDs in DEFINING position count -- a bullet that opens an item, like
# `- **1. [DB-0810-13] Specialists report...`. An ID also appears inline in prose
# whenever one item references another, and it appears again in the closed archive
# once it is done. The first version counted all of those and reported 47
# "duplicates" on a healthy backlog, which is a check nobody would read twice.
dup_ids() {
    local dups
    dups=$(grep -hoE '^[[:space:]]*[-*][[:space:]]+\*\*[0-9.[:space:]]*\[DB-[0-9]{4}-[0-9]{2}\]' \
               DEV_BACKLOG.md 2>/dev/null \
           | grep -oE 'DB-[0-9]{4}-[0-9]{2}' | sort | uniq -d)
    if [[ -n "$dups" ]]; then
        echo "Backlog IDs defining more than one item in DEV_BACKLOG.md:"
        echo "$dups" | sed 's/^/  /'
        return 1
    fi
    return 0
}
run_check "backlog-ids" dup_ids

# --- 7. Dev markers left in shipped code -------------------------------------
# An open A8 item: `# dev` / `# debug` / `# temp` markers added during iterative
# work. The known one writes the coordinator context package -- which contains
# user data -- to stderr on every pipeline session.
# Tracked files only, for the same reason as py-compile: a recursive grep over
# tools/ walks the vendored kokoro venv and returns torch, spacy and pip's own
# comments. And the marker must be the WHOLE trailing comment (`x = 1  # dev`),
# not any comment starting with the word -- `# dev persona mode` in scheduler.py's
# usage block is documentation, and flagging it is how a check gets ignored.
dev_markers() {
    local hits
    hits=$(git ls-files | grep -E '^(core|tools|scripts)/.*\.py$' \
           | xargs grep -nE '#[[:space:]]*(dev|debug|temp)[[:space:]]*$' 2>/dev/null || true)
    if [[ -n "$hits" ]]; then
        echo "Dev/debug markers in shipped code:"
        echo "$hits" | sed 's/^/  /'
        return 1
    fi
    return 0
}
run_check "dev-markers" dev_markers

# --- Report ------------------------------------------------------------------
echo
if [[ ${#FAILURES[@]} -eq 0 ]]; then
    echo "qa_sweep: ${#NAMES[@]}/${#NAMES[@]} checks pass — $(IFS=', '; echo "${NAMES[*]}")"
    echo "  (py_compile parses; it does not execute. Run the thing you changed.)"
    exit 0
fi

echo "qa_sweep: ${#FAILURES[@]} of ${#NAMES[@]} checks FAILED — ${FAILURES[*]}"
echo
for name in "${FAILURES[@]}"; do
    echo "======================================================================"
    echo "FAILED: $name"
    echo "======================================================================"
    cat "$OUTPUT_DIR/$name.log"
    echo
done
echo "  (py_compile parses; it does not execute. A green sweep is not a test.)"
exit 1
