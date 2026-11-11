#!/bin/bash
#
# Deploys code and shared config to the VM via GitHub.
#
# DO NOT ADD A PERSONA-CONFIG PUSH HERE. It is tempting, because
# config/personas/{persona}.md and config/personas/{persona}/ are gitignored and
# therefore never travel with a deploy — which looks like a gap. It is not.
#
# The VM is the source of truth for persona config, because the running system
# writes to it: write_persona() edits config/personas/{persona}.md and
# write_config() edits prime_directive.md and mission.md, both on the VM, in
# response to what the user asks for mid-conversation. Pushing the Mac's copy
# over the top destroys whatever the user has changed since it was last copied
# down. Verified 2026-08-03: the VM's mike.md held five preferences recorded that
# morning that the Mac copy knew nothing about.
#
# Authoring a genuinely new persona file: write it, scp it once, and let the VM
# own it from then on. Do not keep a Mac copy in config/personas/ — a stale copy
# is the thing that gets pushed by mistake.
#
#   gcloud compute scp <file> metatron-vm:~/multi-model-mcp/config/personas/<p>/ \
#     --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap
#
# Backup runs the other way: scripts/metatron-backup.sh pulls the VM's
# config/personas and data down to backups/vm/, and scripts/daily-backup.sh
# archives that.
#
set -e

# --- Deploy lock: one deploy at a time ----------------------------------------
#
# Two windows deploying at once is not hypothetical. The post-deploy assertion
# below already carries the scar: on 2026-08-03 a parallel window pushed between
# this script's push and the VM's pull, and the VM ended up running two sessions'
# commits — which the assertion then had to learn to describe rather than call a
# failure. This lock stops the interleave happening in the first place.
#
# mkdir, not flock: flock is util-linux and DOES NOT EXIST on macOS, which is
# where this script runs. `mkdir` is atomic on POSIX — it either creates the
# directory or fails — which is the whole property a lock needs.
#
# It refuses LOUDLY and names the holder. A lock that silently blocks or hangs
# would be worse than none: the second window would sit there learning nothing,
# and the 2026-08-09 incident is precisely a case where a person needed to be
# told what the other session was doing.
# The lock path must be SHARED BY EVERY WORKTREE, not derived from this script's
# own location. A worktree carries its own tracked copy of deploy.sh, so a
# BASH_SOURCE-relative path resolved to metatron-wt-<slug>/.deploy.lock — a
# different directory — and both `mkdir` calls succeeded. Two deploys then pushed
# and SSH'd the same VM: exactly the 2026-08-09 interleave this lock exists to
# prevent, reintroduced by the worktree system (confirmed live 2026-08-13).
#
# `git rev-parse --git-common-dir` resolves to the MAIN tree's .git from inside
# any worktree, which is the one directory every worktree agrees on. It is
# resolved relative to this script's directory, not the caller's cwd, and made
# absolute — the raw output is the relative string ".git" when run from a repo
# top level, which would put the lock wherever the caller happened to be standing.
# Falls back to the old behaviour outside a git repo, or on a git too old to know
# the flag, because a lock in the wrong place still beats an unbound `set -e`.
_deploy_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_deploy_common_dir="$(cd "$_deploy_script_dir" && git rev-parse --git-common-dir 2>/dev/null)" || _deploy_common_dir=""
if [ -n "$_deploy_common_dir" ] &&
   _deploy_lock_root="$(cd "$_deploy_script_dir" && cd "$_deploy_common_dir" 2>/dev/null && pwd)" &&
   [ -n "$_deploy_lock_root" ]; then
    LOCK_DIR="$_deploy_lock_root/.deploy.lock"
else
    LOCK_DIR="$_deploy_script_dir/.deploy.lock"
fi

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    LOCK_PID=$(cat "$LOCK_DIR/pid" 2>/dev/null || echo "")
    LOCK_WHEN=$(cat "$LOCK_DIR/started" 2>/dev/null || echo "unknown time")

    if [ -n "$LOCK_PID" ] && kill -0 "$LOCK_PID" 2>/dev/null; then
        echo "" >&2
        echo "DEPLOY REFUSED — another deploy is already running." >&2
        echo "" >&2
        echo "    holder PID:  $LOCK_PID" >&2
        echo "    started:     $LOCK_WHEN" >&2
        echo "    lock:        $LOCK_DIR" >&2
        echo "" >&2
        echo "    Nothing has been pushed and the VM is untouched." >&2
        echo "" >&2
        echo "    Wait for that deploy to finish, then re-run. Deploying on top of" >&2
        echo "    an in-flight deploy is how one window's uncommitted-adjacent work" >&2
        echo "    ends up live under another window's commit (2026-08-09)." >&2
        echo "" >&2
        echo "    If that PID is genuinely dead, clear it:  rm -rf \"$LOCK_DIR\"" >&2
        exit 1
    fi

    # Holder is gone — a previous deploy was killed before its trap ran. Take it
    # over rather than making someone clear it by hand, but say so: a lock that
    # was left behind means a deploy did not finish, and that is worth knowing
    # before starting another one.
    echo "Stale deploy lock from PID ${LOCK_PID:-unknown} (started $LOCK_WHEN) —" >&2
    echo "that deploy did not finish cleanly. Taking the lock over." >&2
fi

# Released on any exit path, including Ctrl-C and the `set -e` aborts below.
trap 'rm -rf "$LOCK_DIR"' EXIT INT TERM

mkdir -p "$LOCK_DIR"
echo "$$" > "$LOCK_DIR/pid"
date '+%Y-%m-%d %H:%M:%S' > "$LOCK_DIR/started"

echo "Pushing to GitHub..."
git push origin main

# The SHA the VM must be running once this script finishes. Captured after the
# push succeeds, so it is the commit GitHub actually accepted.
EXPECTED_SHA=$(git rev-parse HEAD)

echo "Deploying to VM..."
# --tunnel-through-iap is required since the 2026-07-31 VPC rebuild: metatron-net
# has no public SSH ingress, only tcp:22 from the IAP range (35.235.240.0/20).
# Without it, ssh times out against the external IP.
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap -- bash -s <<'REMOTE'
set -e
cd ~/multi-model-mcp

# --- Preflight: refuse to deploy into a server that cannot start ---------------
#
# As of 2026-08-03 core/server.py fails closed without METATRON_AUTH_PASSWORD, and
# .env is gitignored so this script cannot carry it — the variable reaches the VM only
# by hand. Checked BEFORE `git pull`, deliberately: once the pull lands, the restart
# further down takes production down, and the failure surfaces as a systemd crash loop
# that looks nothing like a deploy problem.
#
# This is the "config and its guard deploy together, guard first" rule from CLAUDE.md
# pointed the other way — here the code arrives before the config it needs.
if ! grep -q '^METATRON_AUTH_PASSWORD=.' .env 2>/dev/null; then
    echo "DEPLOY ABORTED — METATRON_AUTH_PASSWORD is not set in the VM's .env." >&2
    echo "" >&2
    echo "The server refuses to start without it, so deploying now would stop the" >&2
    echo "service rather than update it. Nothing has been pulled; the VM is untouched." >&2
    echo "" >&2
    echo "Fix: APPEND the one variable to the VM's .env — do not copy the whole file." >&2
    echo "The VM's .env is the live one and holds values the Mac's does not; scp'ing" >&2
    echo "over it would replace working production config to deliver one variable." >&2
    echo "" >&2
    echo "  PW=\$(grep '^METATRON_AUTH_PASSWORD=' .env)   # run on the Mac" >&2
    echo "  gcloud compute ssh metatron-vm --zone=us-central1-a \\" >&2
    echo "    --project=metatron-ai-499810 --tunnel-through-iap \\" >&2
    echo "    --command=\"grep -q '^METATRON_AUTH_PASSWORD=' ~/multi-model-mcp/.env \\" >&2
    echo "               || echo '\$PW' >> ~/multi-model-mcp/.env\"" >&2
    echo "" >&2
    echo "Then re-run ./deploy.sh" >&2
    exit 1
fi

git pull origin main
source .venv/bin/activate

# PyTorch without the GPU code (2026-10-27, multi-user plan § 4.12.1, D13). The VM has no
# GPU, yet the default PyPI torch is the CUDA build: 15 nvidia-* packages, 2.7 GB of disk
# and ~169 MB resident in the server. The CPU build comes from PyTorch's own index, in its
# OWN step — never `--extra-index-url` in requirements.txt, which would let that index
# supply any package it carries a higher version of, not just torch. Idempotent: an
# installed 2.12.0+cpu satisfies this and the `torch==2.12.0` pin below (PEP 440 ignores
# the +cpu label), so the requirements install never swaps the CUDA build back in.
pip install -q --index-url https://download.pytorch.org/whl/cpu torch==2.12.0+cpu
NVIDIA_PKGS=$(pip list --format=freeze 2>/dev/null | grep -o '^nvidia-[^=]*' || true)
[ -n "$NVIDIA_PKGS" ] && pip uninstall -q -y $NVIDIA_PKGS
pip install -q -r requirements.txt

# --- Import check: refuse to restart into code that cannot load ------------------
#
# Both units are Type=simple, so `systemctl restart` returns 0 the moment the process
# forks — an ImportError (HEAD importing a file that was never committed, rule 4 in
# .claude/rules/deploy.md) or a module-level NameError (rule 1) would restart cleanly
# and then crash-loop under Restart=always. Importing both entry points here, BEFORE
# either restart, aborts while the old processes are still serving. It is not a run:
# a NameError inside a function still gets past it — the post-restart verdict below
# is the net for that. </dev/null because this script IS this shell's stdin.
if ! .venv/bin/python -c "import core.server, core.scheduler" </dev/null; then
    echo "" >&2
    echo "DEPLOY ABORTED — the pulled code does not import (error above)." >&2
    echo "" >&2
    echo "Nothing was restarted: the old processes are still serving the previous code." >&2
    echo "But the VM's checkout is now at the new commit, so a crash, reboot or resume" >&2
    echo "would start the broken code. Fix forward (usually: commit the file it imports)" >&2
    echo "and re-run ./deploy.sh promptly." >&2
    exit 1
fi

# Journal window for the post-restart verdict: everything from here on is new processes.
VERIFY_SINCE=$(date '+%Y-%m-%d %H:%M:%S')

# Schedulers have no active connections — restart immediately. One per user since
# 2026-10-27 (metatron-scheduler@<persona>, plan § 4.6); the quoted glob restarts every
# loaded instance. The old single `metatron-scheduler` unit is retired at the migration
# (its file moved out of /etc/systemd/system), so nothing here can start it again.
sudo systemctl restart 'metatron-scheduler@*'

# NRestarts baseline, read IMMEDIATELY after the restart: an explicit restart resets the
# counter, so a figure read before it is not a baseline. Same set of units the glob just
# restarted (loaded instances); --all so one already crashed into auto-restart is listed.
SCHED_UNITS=$(systemctl list-units --all --no-legend --plain --type=service 'metatron-scheduler@*' 2>/dev/null \
    | grep -w loaded | grep -o 'metatron-scheduler@[^ ]*\.service' || true)
NRESTARTS_BASE=$(for u in $SCHED_UNITS; do echo "$u $(systemctl show -p NRestarts --value "$u" 2>/dev/null)"; done)

# Drain active SSE streams before restarting the server.
# Waits up to 3 minutes for in-flight pipelines to finish; force-restarts after timeout.
# Note: new requests can still arrive during the drain window (server stays up).
# A "no new sessions" mode is tracked in archive/plans/future_phases.md (Fix 3 scope).
echo "Checking for active SSE streams..."
# /active requires authentication as of 2026-08-03. Minted here rather than fetched:
# this machine holds METATRON_AUTH_PASSWORD, which is what the signing key derives
# from. If the mint fails the curl 401s, `active` falls back to 0, and the drain
# proceeds as it did before — the same behaviour as an unreachable server.
MT_TOKEN=$(python3 scripts/mint_token.py 900 2>/dev/null || echo "")
timeout=180; elapsed=0; interval=5
while [ "$elapsed" -lt "$timeout" ]; do
    active=$(curl -sk -H "Authorization: Bearer $MT_TOKEN" https://localhost:8001/active 2>/dev/null \
        | python3 -c 'import sys,json; print(json.load(sys.stdin)["active_streams"])' 2>/dev/null \
        || echo 0)
    [ "$active" = "0" ] && { echo "No active streams — restarting server."; break; }
    echo "Draining: $active stream(s) active — ${elapsed}s / ${timeout}s elapsed..."
    sleep "$interval"
    elapsed=$((elapsed + interval))
done
[ "$elapsed" -ge "$timeout" ] && echo "Drain timeout (${timeout}s) — restarting anyway."
sudo systemctl restart metatron-server
NRESTARTS_BASE="$NRESTARTS_BASE
metatron-server $(systemctl show -p NRestarts --value metatron-server 2>/dev/null)"

# --- Post-restart verdict: is the new code actually running? -------------------
#
# `systemctl restart` returning 0 proves only that a process forked (Type=simple). A
# deploy that left the server or a scheduler crash-looping used to print "Deploy
# complete" regardless (review 2026-11-05 #8; the 08-04 near miss). Four inputs, and the
# Mac's success line depends on all four, because this heredoc exits 1 on any of them:
#   1. `is-active` = active for metatron-server and every scheduler instance
#   2. NRestarts unchanged from the post-restart baseline above — a crash systemd
#      quietly restarted is still a crash
#   3. /health 200, with the token minted for the drain
#   4. no `REFUSING TO START` in the journal since the restarts (a scheduler's own
#      single-instance refusal, core/scheduler.py)
#
# The settle wait must outlast RestartSec (10s schedulers, 5s server): a process that
# dies just after the restart is only counted when systemd restarts it.
#
# Deliberately NOT a generic `Traceback` grep. The journal window includes the old
# server's last minutes, and the restart itself kills in-flight turns — an ordinary
# pipeline traceback there says nothing about the new code, and an alarm that fires on
# good deploys is one people learn to ignore (the 2026-08-03 lesson below).
#
# A function taking its inputs as text, so tests/test_deploy_verdict.py can feed it
# failing ones — it extracts this body from deploy.sh verbatim, so keep the shape.
deploy_verdict() {
    # $1 "unit state" lines   $2 "unit NRestarts" baseline   $3 the same, after settling
    # $4 /health HTTP code    $5 journal text since the restarts
    local states="$1" base="$2" after="$3" health="$4" journal="$5"
    local ok=0 unit state n0 n1
    [ -n "$states" ] || { echo "  no unit states could be read" >&2; ok=1; }
    while read -r unit state; do
        [ -n "$unit" ] || continue
        [ "$state" = "active" ] || { echo "  $unit is ${state:-unreadable}, not active" >&2; ok=1; }
    done <<< "$states"
    [ -n "$base" ] || { echo "  no NRestarts baseline could be read" >&2; ok=1; }
    while read -r unit n0; do
        [ -n "$unit" ] || continue
        n1=$(printf '%s\n' "$after" | awk -v u="$unit" '$1 == u {print $2; exit}')
        case "$n0" in ''|*[!0-9]*) echo "  $unit: NRestarts baseline unreadable" >&2; ok=1; continue ;; esac
        case "$n1" in ''|*[!0-9]*) echo "  $unit: NRestarts unreadable after the settle wait" >&2; ok=1; continue ;; esac
        if [ "$n1" -ne "$n0" ]; then
            echo "  $unit: systemd restarted it $((n1 - n0)) time(s) since the deploy did — it is crashing" >&2
            ok=1
        fi
    done <<< "$base"
    case "$health" in
        200) ;;
        401) echo "  /health refused the token (401) — mint failed or .env changed; server unverified" >&2; ok=1 ;;
        *)   echo "  /health returned ${health:-nothing} (000 = no answer), not 200" >&2; ok=1 ;;
    esac
    if printf '%s\n' "$journal" | grep -q 'REFUSING TO START'; then
        echo "  a scheduler logged REFUSING TO START since the restart:" >&2
        printf '%s\n' "$journal" | grep 'REFUSING TO START' | tail -n 3 | sed 's/^/    /' >&2
        ok=1
    fi
    return $ok
}

SETTLE=20
echo "Server restarted. Settling ${SETTLE}s, then checking the new processes..."
sleep "$SETTLE"
# /health is polled, not read once: a slow start is not a failure. Up to 60s more.
health=000; waited=0
while :; do
    health=$(curl -sk -o /dev/null -w '%{http_code}' -H "Authorization: Bearer $MT_TOKEN" \
        https://localhost:8001/health 2>/dev/null || true)
    { [ "$health" = "200" ] || [ "$waited" -ge 60 ]; } && break
    sleep 5; waited=$((waited + 5))
done
VERIFY_UNITS="metatron-server $SCHED_UNITS"
STATES=$(for u in $VERIFY_UNITS; do echo "$u $(systemctl is-active "$u" 2>/dev/null)"; done)
NRESTARTS_AFTER=$(for u in $VERIFY_UNITS; do echo "$u $(systemctl show -p NRestarts --value "$u" 2>/dev/null)"; done)
VERDICT_FAIL=0
if ! JOURNAL=$(sudo journalctl -u metatron-server -u 'metatron-scheduler@*' --since "$VERIFY_SINCE" --no-pager 2>/dev/null); then
    echo "  the journal could not be read, so a refusing scheduler would be invisible" >&2
    VERDICT_FAIL=1
fi
[ -n "$SCHED_UNITS" ] || echo "NOTE: no metatron-scheduler@ instance is loaded — no user's scheduled jobs will run." >&2
deploy_verdict "$STATES" "$NRESTARTS_BASE" "$NRESTARTS_AFTER" "$health" "$JOURNAL" || VERDICT_FAIL=1

if [ "$VERDICT_FAIL" -ne 0 ]; then
    echo "" >&2
    echo "DEPLOY FAILED — the new code is on the VM but is NOT running cleanly (reasons above)." >&2
    echo "Users may be getting nothing: no replies, no scheduled briefs." >&2
    echo "" >&2
    echo "Last journal lines since the restart:" >&2
    printf '%s\n' "$JOURNAL" | tail -n 25 | sed 's/^/    /' >&2
    echo "" >&2
    echo "Full log, from the Mac:" >&2
    echo "  gcloud compute ssh metatron-vm --zone=us-central1-a \\" >&2
    echo "    --project=metatron-ai-499810 --tunnel-through-iap \\" >&2
    echo "    --command=\"sudo journalctl -u metatron-server -u 'metatron-scheduler@*' --since '$VERIFY_SINCE' --no-pager\"" >&2
    echo "" >&2
    echo "Fix forward, or git revert the commit, then re-run ./deploy.sh." >&2
    exit 1
fi
echo "Post-restart check passed: $(printf '%s\n' "$STATES" | grep -c ' active$') unit(s) active, no crash restarts, /health 200."
REMOTE

# --- Post-deploy assertion -------------------------------------------------
#
# Confirm the VM is actually running the commit that was just pushed. This is
# not belt-and-braces: the failure mode here is SILENCE, not an error. On
# 2026-08-02 a deploy failed at the SSH step and left the VM a commit behind
# with no visible complaint, and a parallel chat's "not yet deployed" note was
# simultaneously stale because a deploy from another window had already shipped
# its commit. Both were caught by hand, which does not scale.
#
# Deliberately a second SSH rather than reading the first one's output: that
# heredoc interleaves pip, systemctl and drain-loop chatter, so any SHA parsed
# out of it would be guesswork. A clean call costs a few seconds and cannot
# misread.
#
# Runs even when the deploy above reports success — a deploy that "succeeded"
# while leaving the VM behind is exactly the case this exists to catch.
#
# This block answers only WHICH code is live. Whether it is RUNNING (is-active,
# NRestarts, /health, journal) is the post-restart verdict inside the heredoc,
# which exits 1 — aborting this script under `set -e` — before reaching here.
#
# The test is ANCESTRY, not equality. The question worth answering is "is the
# commit I just pushed live on the VM?" — not "is the VM's HEAD character-for-
# character mine?" Those differ whenever a parallel chat window pushes between
# this script's push and the VM's pull: the VM ends up strictly AHEAD, running
# your commit plus someone else's. Equality called that a failure and told the
# reader they were "running OLD CODE", which was the opposite of true.
#
# That false alarm fired for real on 2026-08-03, one day after this assertion
# was added. It matters more than a cosmetic wrong message: an alarm that cries
# wolf on a good deploy is one people learn to ignore, which costs exactly the
# silent-failure detection this block exists to provide.
#
# So there are four outcomes, deliberately distinct:
#   unverified  — HEAD unreadable; may or may not have worked
#   match       — VM HEAD is exactly the pushed commit
#   ahead       — pushed commit is an ancestor of VM HEAD; it IS live, and
#                 something else shipped too (name it, don't hide it)
#   failed      — pushed commit is absent from the VM's history
echo "Verifying VM is running ${EXPECTED_SHA:0:8}..."
REMOTE_OUT=$(gcloud compute ssh metatron-vm --zone=us-central1-a \
    --project=metatron-ai-499810 --tunnel-through-iap --quiet \
    --command "cd ~/multi-model-mcp && git rev-parse HEAD && \
      { git merge-base --is-ancestor $EXPECTED_SHA HEAD 2>/dev/null \
        && echo CONTAINS || echo MISSING; } && \
      git log --oneline $EXPECTED_SHA..HEAD 2>/dev/null" 2>/dev/null) || REMOTE_OUT=""

REMOTE_SHA=$(printf '%s\n' "$REMOTE_OUT" | sed -n '1p' | tr -d '[:space:]')
CONTAINS=$(printf  '%s\n' "$REMOTE_OUT" | sed -n '2p' | tr -d '[:space:]')
EXTRA=$(printf     '%s\n' "$REMOTE_OUT" | sed -n '3,$p')

if [ -z "$REMOTE_SHA" ]; then
    echo ""
    echo "!!! DEPLOY UNVERIFIED — could not read the VM's HEAD."
    echo "    The deploy may have worked. It may not have. Do not assume."
    echo "    Check by hand:"
    echo "      gcloud compute ssh metatron-vm --zone=us-central1-a \\"
    echo "        --project=metatron-ai-499810 --tunnel-through-iap \\"
    echo "        --command 'cd ~/multi-model-mcp && git log --oneline -3'"
    exit 1
elif [ "$CONTAINS" != "CONTAINS" ]; then
    echo ""
    echo "!!! DEPLOY FAILED — your commit is NOT in the VM's history."
    echo "    expected: $EXPECTED_SHA"
    echo "    VM has:   $REMOTE_SHA"
    echo ""
    echo "    Whatever you were about to test is running OLD CODE."
    echo "    Usual cause: the git pull failed on the VM (divergent branch,"
    echo "    deploy-key expiry, or a dirty working tree). Get the real error with:"
    echo "      gcloud compute ssh metatron-vm --zone=us-central1-a \\"
    echo "        --project=metatron-ai-499810 --tunnel-through-iap \\"
    echo "        --command 'cd ~/multi-model-mcp && git status && git pull origin main'"
    exit 1
elif [ "$REMOTE_SHA" != "$EXPECTED_SHA" ]; then
    # Your commit is live; the VM is simply further along. Not a failure — but
    # not silent either, because "something I did not push is also running" is
    # worth a human knowing before they test against it.
    echo ""
    echo "Verified: ${EXPECTED_SHA:0:8} is live — but the VM is AHEAD of it."
    echo "    VM HEAD:  $REMOTE_SHA"
    echo "    Almost certainly a parallel chat window deployed after this push."
    echo "    Also running, on top of yours:"
    printf '%s\n' "$EXTRA" | sed 's/^/      /'
    echo ""
    echo "Deploy complete."
    exit 0
fi

echo "Verified: VM HEAD matches."
echo "Deploy complete."
