### 2026-11-11 (the 11-05 review's High and Medium findings fixed, Fable-checked twice, and deployed) — `6ce66b2`, `b17af10`, `eb08522`, `2bd1236`, `f61d1e5`, `968a8a0` — **deployed by Mike in-session; VM at `968a8a0`**

**Outgoing handoff carried:** the 11-05 primer asked for `/backlog` triage from the review report.
Mike instead had the findings fixed directly: High and Medium only (the Lows wait for the next
review), nothing that touches an active build, his own items first in the main chat.

**Plan:** `archive/plans/codebase_review_fixes_plan_2026-11-11.md` (rev. 2, Phase 1 outcomes at
the end). **Fable adversarial review** (`…/adversarial_review_codebase_review_fixes_plan_2026-11-11.md`)
found 5, then 2 more in the revision, all fixed before building: the tracker's "preserved copy"
keeps nothing for a zero-length file, so a `.lastgood` copy became the recovery source (refreshed
by copy, never by moving the tracker); the tool-schema guard had to land with the schema it
checks, or the SubagentStop sweep blocks every builder; editing `static/index.html` would force an
APK rebuild through the uncommitted WhatsApp tree; the provider drop had to be unconditional
(the scheduler sends `provider: None`); a `Traceback` grep cries wolf on a deploy, and systemd
resets `NRestarts` on an explicit restart, so the baseline is read after it.

**Mike's calls:** W1 — one of `OPENAI_API_KEY`/`ANTHROPIC_API_KEY` WAS set on the VM, so finding 1
was a live path; removed from `.env` (nothing reads either: every client passes its key
explicitly). W2 (#11, second-user data in developer channels) deferred. W3 (#27) done as a Red
edit. W4 (#29, wishes grants) skipped. W5 allowed the VM read. W6 held all day-planner (#5, #33)
and Build (#9, #10, #40, #41) fixes.

**Built** by three Opus builders in worktrees, each diff read and re-tested on main: #1 #2 #3 #4
#15 #16 #21 (`eb08522`), #3 #6 #7 #22 (`2bd1236`), #8 #48 #44-docs (`6ce66b2`), #44-VM
(`f61d1e5`: cert-renew units, `host.conf`, stop-billing source now tracked). Lead changes: server
`--provider` kept parseable-but-ignored so no unit can crash-loop; `CALENDAR_UNREADABLE`
registered in the sync. **Fable code review** of the merged diff: no High; its Medium (intake
queue, calendar and Research proposals still filed `stated`) and two regressions (series invite
prompt showing the first date; account URL in the journal) fixed in `968a8a0`.

**Believed true and wasn't:** `SESSION.md` said the VM was at `ebfe50b`; it was at `4637dfb`.
And "Iva's onboarding this weekend" — `accounts.py list` shows **no accounts**; she has not
signed up, so `2 unit(s) active` (server + `@mike`) is correct.

**Left:** 2 of 7 Highs unfixed, both held (#5 nudges dropped near fixed sessions; #9 Build cannot
land). Before Iva signs up: #11, #40, #41. Known limits: moving a series' time does not shift its
EXDATEs, and a series with moved occurrences may now 400 on a time move. Seven test files outside
the sweep fail on pre-existing HEAD (one is a fixture dated 3 Nov). Deploys take ~25 s longer.
Not run: the reminder-survives-a-move live check, and deleting `~/multi-model-mcp/.env.bak-2026-11-11`.

