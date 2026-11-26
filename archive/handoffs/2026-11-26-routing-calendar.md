# Handoff — routing-calendar (2026-11-26), branch wt/routing-calendar

Two commits on top of 2293026; manifest files only. Verified with the main tree's venv
(the worktree has none): new tests pass, test_routing_miss_success, test_calendar_update_in_place,
test_caldav_multi_calendar, test_calendar_invite pass; `scripts/qa_sweep.sh` 12/12.

1. 5ee2da2 — Fix 1 `[DB-0902-01]`: `describes_scheduled_session()` in tools/logger.py; write_quality_event
   refuses (ValueError, same shape as the success guard) a ROUTING_MISS on a no-user-words turn
   (existing `_no_user_words()`: bound turn without user words, else proactive trace) whose detail
   describes the session's nature (scheduled/automated/quiet check-in/no user message/system prompt)
   AND names no specialist and no output fault. Measured: 14 of 14 noise refused on a proactive
   trace; 0 of 10 genuine refused; the same noise is accepted on a user turn (a user can really
   report a scheduled thing wrong). Kept by design (named-specialist/fault exemptions): "missed routing
   the morning greeting to Mental Wellbeing...", "no specialist calls", "without valid structured
   format", "routed ... to Synthesizer without any specialist consultation".
   Limit: noise that happens to name a specialist or the Synthesizer, or says "incomplete", slips
   through (precision over recall). Corpus is paraphrased from the machine log, generic names.
2. (second commit) — Fix 2 `[DB-1029-10]` code half: tools/caldav.py `_placeholder_uid_error`
   (update + delete; "", "...", "…", "<uid>", "uid", "<id>", "id", "none", "null", "n/a", "tbd",
   "unknown", "xxx", quotes stripped) and `_internal_title_error` (write + update when title given;
   `\buser(?:'s)?\b`, case-insensitive). Both return `{"error": ...}` before any config/HTTP.
   Legitimate titles it refuses: "User group meetup", "User research interview", "User testing";
   not refused: "Usernames workshop", "Superuser audit". Reviewer to judge the trade-off.
3. Close evidence: DB-0902-01 — test counts above; confirm live by 12-03 re-count of ROUTING_MISS
   from scheduler sessions (they now never reach the log). DB-1029-10 — code half done; the
   place-in-`location` instruction remains an agent-file item (not done, not mine).
4. SESSION.md: nothing structural; deploy needed for both (tools/ -> VM).

Addendum (coordinator request): write_calendar_event had no `location` at all. Added optional `location: str = ""` (signature, docstring, schema), written as `LOCATION:` with the same `_esc` as update, and passed to `_compute_conflicts` (was hard-coded ""), so travel-time flags see created events. Default empty = no LOCATION line. Commit c193243. Tests in tests/test_caldav_event_titles.py. Deploy: tools/ -> VM. The SubagentStop QA gate swept a temp partial copy (no core/, .claude/, yaml) and failed there; this worktree own sweep is 12/12.
