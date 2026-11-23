### 2026-11-23, seventeenth (ranking Part B phase 2 — the lookup switch-on reached the VM on a second deploy; the live check is a backlog item) — no code — **Mike deployed twice**

**Wrong earlier:** the sixteenth's close-out took "deployed" to cover the lookup switch-on. Mike's
`git log` on the VM showed `eb809a5` on top — phase 2 (`e134948`) was there, `129f3fb` was not, so
the lookup still answered "not available yet". **Mike deployed again** the same evening. Read on
the VM (`/monitor/file`, keys and counts only): the 17:30 plan build carried phase 1's shadow but no
phase 2 keys, and `ranking_state.json` held only `shadow`. Consistent with a deploy after 17:30 and
no rebuild since; the day's first build tomorrow writes the phase 2 shadows.

**The live check could not be run from Claude Code.** It needs the user's own words in the app, and
sending them for him would put tasks he did not state into his ledger. **Filed** (Mike asked): the
backlog item now carries the VM confirmation command, "start after a morning brief", and what a
Claude Code session reads on the VM afterwards. The protected-time and behind walkthroughs are
already filed, and they also start counting tomorrow.

**Next:** phase 3, `archive/handoffs/2026-11-23-ranking-part-b-phase-3-build-prompt.md` (Opus, high).

