# 2026-08-05 — Backlog Quick-Bucket Sweep, SMTP Test, APK Rebuild, Dictated-Email Fix

Full reasoning and context: [archive/PROJECT_LOG.md](../PROJECT_LOG.md) (same-dated entry, this
title).

## What was built / changed

**Backlog quick-bucket sweep (44 → 32 open):**
- Closed: Inbox `logistics`/`search_memory` (stale), DB-0803-07 deploy.sh WS-drain (already
  fixed, never crossed off), VM-down detection (same), DB-0805-03 filename collision (fixed),
  dead PROJECT_LOG.md link (repointed), DB-0803-04 write_config heading (corrected a wrong
  same-day verification — not a bug), confirmation-gate-is-a-prompt entry (superseded, built),
  send_email Decision C (verified built), web-page-read entry (narrowed to the real remaining
  gap — level 3 only), spend guard pricing (verified + corrected against live pricing),
  transcript bubble line-wrap (fixed), dismissable readout (code-verified against every pass
  condition).
- Left open: DB-0803-06 shownIds eviction (re-derived, confirmed real, not fixed), pre-2026 log
  spot-check (blocked — VM-owned data, found a new hallucinated-date instance in the Mac mirror).
- Real code fixes: `tests/run_a4_safety.py` filename collision, `.message` bubble
  `overflow-wrap`, `config/modules/spend_guard.yaml` pricing (~3.75x low on flash-lite output).

**Deploy + first real SMTP send + APK rebuild:**
- `./deploy.sh` run twice, both VM-HEAD-verified.
- First real email this system has ever sent — full `send_email` confirm-gate path exercised
  live against `mike`, landed in `diamond.mike.mt@gmail.com`.
- APK rebuilt, content-verified by unzipping (mtime looked stale, contents weren't). Served for
  sideload over Tailscale; on-device install still pending, that step is Mike's.

**Two backlog items resolved by direct user decision:**
- Check-ins not gated on presence — **not a bug**, closed. Check-ins should keep firing through
  silence; the original admonition was against spamming an actively-engaged user only.
- Browser doesn't live-refresh on foreign messages — **user asked to verify a "probably already
  handled" claim before proceeding.** Found a real, related, but distinct fix already shipped
  (`ace22c7`, half-open socket detection) that does not cover what this entry actually
  diagnoses (a render-path gap, not transport). Left open.

**New feature: dictated-email correction.**
`core/voice_pipeline.py.correct_known_addresses()` — regex + `difflib` fuzzy match against
known addresses (self + CRM contacts), wired into `/transcribe` via an optional `persona` query
param. Tested against both documented real cases and three negative cases before wiring in.
Deployed; VM services confirmed active post-restart.

## Decisions made

1. Check-ins fire through silence (Mike, explicit).
2. Browser live-refresh entry stays open despite an adjacent-looking fix — the entry's own
   diagnosis is a different code path than what `ace22c7` addresses.
3. Held SMTP test and APK rebuild for explicit go-ahead rather than running them the moment VM
   connectivity returned mid-session.
4. Scoped every commit to only the files this session actually edited (verified via
   `git diff --cached --stat` each time) rather than touching files a concurrently-active
   window had mid-edit.

## Deferred / still open

- DB-0803-06 shownIds eviction — needs an actual fix (evict oldest-first, not `.clear()`).
- Pre-2026 log spot-check — needs the VM.
- Browser live-refresh — needs live two-device reproduction.
- APK — needs on-device install/verification (Mike's step).
- `tools/mail.py`'s module-level docstring still says "read-only... sending is deferred," stale
  since `send_email` shipped 2026-08-04 — not fixed this session, noted only.

## Commits

`2c097b3`, `30dd9b6`, `a08e38a` — all on `main`, pushed and deployed (except `30dd9b6`,
docs-only).
