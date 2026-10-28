### 2026-10-28, second (the second-user build is live — merged, deployed, schedulers migrated, Stage 5 smoke 5 of 7 with two interviewer fixes held for the Stage C deploy) — `42a3c21`, `bc37590` (merge), `8e07d94`, `469a575`, `c8de0e5`, `ca3173b`, `c990a3e` — **`8e07d94` and `469a575` deployed by Mike; `c8de0e5`, `ca3173b` held to ship with Stage C**

**Incoming handoff:** `archive/handoffs/2026-10-28-multi-user-build-stage-4-prompt.md`, now consumed.

**Stage 4, done.**
- **Consent texts.** Checked every promise against code: disconnect deletes the credential, no
  backup carries it, sending needs a tap, and tone withdrawal deletes what was learned.
  **Found:** read-aloud in a language Kokoro can't speak (Bulgarian, `[DB-0810-15]`) goes to
  Microsoft's online `edge-tts`, and the notice named only Google. Mike chose to disclose it, with
  no code change: one line (`42a3c21`). v1 had never shipped, so it was edited in place. The
  recordings line and the "switching off keeps your data" line were offered and declined.
- **Merge and checks.** Merged `--no-ff` (`bc37590`). The other session's six uncommitted files
  were untouched. `test_subagent_depth` crashed on `main` on a non-UTF-8 file in the Mac-only
  `tools/kokoro/venv`; fixed with `errors="replace"` (`8e07d94`). Before the push: the merge holds
  only the reviewed commits, the diff has no persona data or secrets, and all 19 touched suites
  pass. `test_memory_watch_and_session_line` is pytest-only, so running it as a script proves nothing.
- **Deploy and migration.** VM had been at `d698019` (`SESSION.md` said `08ee9d0`). Before:
  kokoro 0.9.4, torch 2.12.0 (CUDA). After: `2.12.0+cpu`, 0 `nvidia-*`. Mike's consent records
  were seeded. The `/proc` scan refused for real; the old unit was retired to `~/retired-units/`;
  `metatron-scheduler@mike` holds the lock, and a second copy exits 1. **A guard of mine
  matched its own `bash -c` line** and aborted between retiring the old scheduler and starting
  the new one, leaving none for a few minutes. Fixed with `ps -C python…`. The APK was rebuilt
  and sideloaded; The Book needed a restart (a pre-deploy process holds an old-format token).

**Stage 5 so far:** checks 1, 3, 4, 5 pass. 13 of 13 GET routes, a write, the socket and
`/monitor/file` all refuse a trial token naming `mike`. M1: server 1,184 MB, no `nvidia`/`kokoro`.
M2: helper **2.24 GB** (plan said ~1.5), VM down to **714 MB** with four schedulers; cold reply
78 s, warm ~12 s; the helper gone at 10 idle minutes and all memory back. Most was run by a
socket client of mine (Mike's call); Mike did a UI pass on `trial_1026_10b`, steps 1–4 pass.

**Found and fixed:**
- **The first interview opened on the canned refusal.** Tier 4 blocked the interviewer saying its
  scripted opener (`goals_interviewer.md:91`). Stage 2 had put the interviewer behind the filter.
  Quoted spans are now left out of the instruction fingerprint (`469a575`), and the new checks fail
  on the old code. **14 Synthesizer sample lines were blockable too, but only 1 of 1,280 of Mike's
  replies since 07-29 was the canned line**, and that one was correct. *Rejected:* rewriting the 24
  lines (leaves the Synthesizer exposed); raising the threshold (weakens the check everywhere).
- **Day-shape facts were acknowledged ("Got it") but not saved.** 2 of 3 were lost. Now each is
  saved in the turn it's given, as `preferred` unless the user said it's kept to; questions are
  grouped by theme (Mike: try it) (`c8de0e5`).
- **The purpose taken at face value, and a card reading "Update mission.md".** Mike's idea was to
  draft then revise; I pushed back on repeated revisions (a card each time, and a written draft
  anchors). Decided: draft, explore, revise once. User-facing names **purpose** and **guiding
  star** (`ca3173b`).

**Latency, investigated:** generation runs ~10 s per 1k tokens. Mike's slow replies come from extra
Synthesizer calls for bookkeeping tools, more thinking, and cache misses. The handoff is
`c990a3e`. **The 10-24 "defer the writes" rejection is carried as constraints to solve.**

**Wrong earlier:** `SESSION.md`'s VM hash; my "only the Synthesizer is filtered" reading. **Noticed,
not filed:** a `BLD-1028-01` id was given to both Mike's refill gap and a trial account's swim
question; the app has no real sign-out (Mike: after Stage 5); `accounts.py` prints "She can sign in".

