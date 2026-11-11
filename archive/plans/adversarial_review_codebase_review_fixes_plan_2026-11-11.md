# Adversarial review — codebase_review_fixes_plan_2026-11-11.md
**Model:** Fable (adversarial-reviewer) · **Effort:** medium · **Date:** 2026-11-11

## STRUCTURAL

1. [§ Phase 2 Builder B #22; § 5 Run] [tools/context_tracker.py:_preserve_corrupt, :_read_raw; tests/test_degradation_paths.py:163-176]
Wrong: The step's recovery source — "carry `clinical_threads` and `_CARRIED_KEYS` from the preserved copy" — does not exist in the form claimed: `_preserve_corrupt` copies the unparseable file byte-for-byte and keeps nothing at all when the file is zero-length (`st_size == 0` returns `""`), which is exactly the torn state the step's own test names.
Fails: The test "zero-length torn file + `close_scheduled_run` → clinical threads survive" has no source to survive from unless the builder adds a last-known-good copy written on every successful write, which § 5's "nothing new persists" rules out and no step authorises.
Costs: The builder either ships a lock-and-atomic-write that only protects future writes while the test is quietly weakened to match, or invents an unplanned persisted artifact with no owner or expiry — and the clinical-thread loss the item was ranked for stays open under a green test — high.

2. [§ Phase 2 preamble; Builder C "4 (guard)"; § 4 commit order] [scripts/check_agent_tools.py:_load_registered_tools (:191-196), :524; scripts/qa_sweep.sh check 1; scripts/hook_subagent_gate.py:_dirty_worktrees (:96-160), :206]
Wrong: Builder C's guard change is specified to fail on `2dd492a` and pass only after Builder A's schema lands, yet every builder works in a parallel worktree branched from `2dd492a` and must pass `qa_sweep.sh` before it may report done — and the SubagentStop gate sweeps every dirty worktree in the repo, not just the worker's own.
Fails: If the guard's new class drives `check_agent_tools.py`'s exit code (as it must to be a guard rather than a report line), qa_sweep check 1 fails in C's worktree the moment the edit lands and, via `_dirty_worktrees`, in every other builder's gate run while C's tree is dirty; if it does not drive the exit code, the plan has built the "no reader exists" pattern it is elsewhere deleting.
Costs: Either all five builders are blocked from reporting done by one tree until the lead hand-sequences C after A's merge (which the plan does not say), or the finding-4 guard ships inert — high.

## LOCAL

3. [§ Phase 2 Builder A #1; § 4 "VM-affecting: A"; § Scope rule 2] [static/index.html:940 `provider-select`; scripts/check_apk_sync.sh:19-37; android/app/src/main/AndroidManifest.xml (modified, uncommitted)]
Wrong: Removing the provider selector from `static/index.html` puts the shipped APK's bundled `index.html` out of sync, which `check_apk_sync.sh` fails loudly on, and the only cure is an APK rebuild in `android/` — the WhatsApp active-build area the plan's own scope rule 2 says it will not touch — while the plan classes A as VM-only and never names the APK.
Fails: The next `check_apk_sync.sh` run (or Iva's APK rebuild, which `SESSION.md` already gates her onboarding on) reports drift from a cosmetic edit, forcing a rebuild from a tree carrying another build's uncommitted `build.gradle`/manifest changes.
Costs: An unplanned APK rebuild entangled with the WhatsApp tree for an edit that removes a selector whose only option is already "Auto" — high on mechanism, medium on consequence.

4. [§ Phase 2 Builder A #1; § 6 risk 4] [core/remote_client.py:_send_one (:299-305), :send_one; core/scheduler.py (no `provider`)]
Wrong: The fix branches on "a grep finds a service-token caller that sends `provider`", and the scheduler's own path `core/remote_client._send_one` always sends the key (`"provider": provider`, value `None`), but `core/remote_client.py` is absent from the § 6 grep list and the plan never states that a key sent with `None` is not a caller that needs it.
Fails: A builder whose grep does include it takes the weaker branch — keep honouring `provider` from `service` tokens — for a caller that never sets a value, leaving the override live on exactly the "stale developer tool holding a service token" path finding 1 names; a builder whose grep follows the list as written never sees the key at all.
Costs: Finding 1's control is either left half-open by a conditional the evidence does not support, or decided by which grep the builder happens to run — medium.

5. [§ Phase 2 Builder C #8] [core/server.py:990 `logger.exception` on pipeline failure; deploy.sh:173-194 drain, :221-224 "cries wolf" note]
Wrong: The post-restart verdict greps `journalctl --since <deploy start>` for `Traceback`, but the server writes a full traceback to journald for any pipeline failure, including the in-flight turns the restart itself kills after the drain ("new requests can still arrive during the drain window") and any transient model error in the window.
Fails: A deploy during ordinary use reports failure from a traceback that is a consequence of the restart, not a startup fault, and the script's own 2026-08-03 note says an alarm that cries wolf costs the detection it was added to provide.
Costs: The crash-loop check that finding 8 exists for gets learned-past within a few deploys, or Mike re-deploys a healthy VM to clear a verdict he cannot distinguish from a real one — speculative.

## VERIFY — 2026-11-11 (rev. 1)

1. CLOSED — [tools/context_tracker.py:_preserve_corrupt (:589-591), :_write_raw (:620-625)] the recovery source is now a `.lastgood` copy that exists independently of the torn file, the zero-length case has a source, and the persisted artifact is costed in § 5 Run with unit, deleter and meter stated.

2. CLOSED — [scripts/check_agent_tools.py:_load_registered_tools (:191-196); core/orchestrator.py:register_tools (:1481-1531, :1549); scripts/hook_subagent_gate.py:_dirty_worktrees (:206)] the guard and the one handler-only tool it would flag (`record_wisdom_response`, the only name in `handlers` absent from `schemas`) now land in the same worktree, so no tree exists where the guard fails without the schema; § 6 risk 1 names the all-dirty-worktrees sweep and B/C/E carry no cross-builder dependency.

3. CLOSED — [scripts/check_apk_sync.sh:19-37; static/index.html:2783 sends `provider: providerSelect.value || null`] `static/index.html` is untouched so the bundled copy cannot drift, and the client's `null` is ignored by the unconditional server-side drop; § 6 risk 5 fences `static/`, `android/`, `.gitignore`.

4. CLOSED — [core/remote_client.py:_send_one (:299-305), :_run (:252-257); core/server.py:1414, :354] the fix is unconditional for every token role, so the override dies regardless of what any caller sends; one note for the lead, not a reopening: `_run` (:256) — the `--remote` REPL — also sends a real `provider` from `run_interactive_remote(provider=args.provider)` (core/orchestrator.py:7864), which risk 4 says is "reported, not accommodated", so that CLI flag goes silently dead rather than removed.

5. CLOSED — [core/server.py:990 `logger.exception`; core/scheduler.py:1191,1200,1235 `REFUSING TO START`; infra/systemd/metatron-scheduler@.service:35-36 `Restart=always`, `RestartSec=10`] the generic `Traceback` grep is gone; the journal term now matches only the scheduler's own refusal lines, and the test requires a pipeline traceback not to fail the verdict.

### NEW

1. [§ Builder B #22 (b)/(c)] [tools/context_tracker.py:_read_raw (:608-610 `if not path.exists(): return {}`), :read_context_tracker (:1057-1064 "Returns empty structure if no tracker file exists")]
Wrong: Refreshing `.lastgood` by `os.replace`-ing the outgoing tracker aside before the new temp file is `os.replace`d in creates a window with no tracker at all, and the recovery trigger in (c) is "a decode error or zero-length tracker" — a missing file is neither.
Fails: A crash or kill between the two renames leaves `.lastgood` valid and the tracker absent; every reader treats absence as an empty tracker, the next write persists that emptiness, and the carried `clinical_threads` are gone with a valid copy sitting beside the file that nothing consulted.
Costs: The revision reintroduces the exact loss it was written to close, on a narrower but real window, under a test suite that only fixtures decode errors and zero-length files — medium.

2. [§ Builder C #8] [deploy.sh:171, :194 `systemctl restart`; infra/systemd/metatron-scheduler@.service:35-36]
Wrong: The verdict records `NRestarts` "before restarting" and requires it "unchanged since the restart", but systemd resets a unit's `NRestarts` to 0 on an explicit `systemctl restart`, so the pre-restart figure is not the baseline the post-settle comparison needs.
Fails: A unit with a prior auto-restart count of N compared against its post-restart count masks a crash loop that has restarted exactly N times inside the settle window and fails a healthy unit whenever N ≠ 0; the stubbed shell test feeds the verdict function its own numbers and cannot see which baseline the script reads.
Costs: The crash-loop detector finding 8 exists for is wrong in both directions until the baseline is taken after the manual restart, and nothing in the plan's test would reveal it — speculative.
