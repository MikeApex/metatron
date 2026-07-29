# 2026-07-27 — Cross-Device WS Sync Bug Fix and Deploy

## Context

User remembered a chat titled starting "Synch" and couldn't find it. Search of all Claude Code session history (`~/.claude/projects/*/*.jsonl`) turned up nothing literally titled "Synch" — closest matches referenced "Synth" (the Metatron agent name). User then recalled it was likely about **syncing Metatron chats across devices**, which pointed to [archive/sessions/2026-06-26 — Synthesizer Conversation History.md](2026-06-26%20—%20Synthesizer%20Conversation%20History.md).

## What was found

That 6/26 session's own "Deferred" note said history was in-memory only, no persistence planned. That turned out to be wrong within hours: same night, commit `4302ef8` (mislabeled as a Kokoro TTS commit) added full SQLite-backed, real-time cross-device sync to `core/server.py`:

- `exchanges` SQLite table, `_load_history_from_db` / `_get_recent_exchanges` / `_catchup_since` / `_save_exchange`
- Startup hydration of `_session_history` from SQLite per persona
- `ConnectionManager` broadcasting `stream_start` / `chunk` / `done` / `retract` / `message` / `error` to all WebSocket clients on the same persona in real time
- Reconnect catch-up via `{type: "catchup", since_id}` → `_catchup_since`
- Follow-up commit `dc8f031` (next day) fixed exchanges being wiped on sender mid-stream disconnect

**Gap identified:** none of this was ever documented as tested against two real simultaneous devices. `dc8f031` itself was never logged in any session archive — an archiving-convention miss.

## Bug found and fixed

In `static/index.html`, `sendViaWebSocket()`:

```js
const exchangeId = crypto.randomUUID();
shownIds.add(exchangeId);
if (shownIds.size > 100) shownIds.clear();   // could wipe the ID just added
```

Once the client-side `shownIds` set exceeded 100 entries (accumulated over a long session), `.clear()` ran *after* adding the new exchange's ID — wiping it immediately. The client would then fail to recognize its own `chunk`/`done` messages (routed to the "foreign" branch instead, where no `foreignBubbles` entry exists since the sender is excluded from its own `stream_start` broadcast). Result: the response bubble hangs on "▍" forever, `setLoading(false)` never fires, response text is lost — silently, no error shown. Reproduces only after >100 exchange IDs accumulate client-side, which is likely why it was never noticed.

**Fix:** reordered to clear before adding, so the in-flight exchange ID always survives the cap. Commit `eea3faf`.

## Deploy

`./deploy.sh` hit a snag: GCP billing had been auto-disabled (the `stop-billing` Cloud Function tripped on the $20/month cap — see CLAUDE.md Billing Protection section). User re-enabled billing in the GCP Console. Retried deploy — first attempt still failed (`ssh: Could not resolve hostname github.com` from the VM, DNS not yet settled post billing-restore); second retry succeeded. VM pulled `eea3faf`, no active SSE streams blocked restart, both services restarted, `/health` confirmed OK.

## Follow-up (2026-07-28/29)

User ran the test on real devices and confirmed: "Synching seems to be occurring." Cross-device sync is working post-fix.

**Not independently re-verified by Claude Code this session** — this is the user's own observation, not a re-check of logs/DB. If confirmation with hard evidence is wanted later (e.g. `exchanges` table row count matching across a live two-device exchange, or checking `/monitor` traces), that's still open.

## >100-exchange edge case: force-tested (2026-07-29)

Two-part verification, no mike-persona involvement, minimal cost:

**1. Pure logic proof (zero cost, no server/persona touched).** Extracted the exact `sendViaWebSocket()` Set ordering into a standalone Node harness (scratchpad only, not committed to the repo), ran 300 simulated sequential sends for both orderings:
- **Pre-fix order** (`add` then `clear`): fails at send #101 and #202 — exactly the predicted pattern, recurring every time the set crosses the 100-entry cap.
- **Fixed order** (`clear` then `add`, deployed): 0 failures across all 300.

**2. Live end-to-end proof (one real Vertex call, persona=`cal_newport`, a dev/test persona, not mike).** Wrote a Python WebSocket client implementing the exact deployed (fixed) client logic, pre-seeded its local `shownIds` with 100 synthetic exchange IDs to recreate the real boundary condition (no need to actually send 100 real messages), then sent one real message through the live production server:
- `exchange_id` correctly survived the clear-then-add check (`shownIds` size went 100 → 101, no clear, since the check fires on size *before* adding and 100 is not `> 100`)
- Server `chunk` → `done` correctly recognized as the client's own exchange
- Response streamed back and completed normally: *"Test received and acknowledged."*
- Confirmed via direct SQLite read on the VM: the exchange persisted under `persona='cal_newport'`; `mike`'s row count (11) was untouched — no cross-persona contamination.

**Verdict: fix confirmed at both the isolated-logic level and the live production-server level.** This closes out the one item from the deploy session that hadn't been directly forced.

## Deferred / open (remaining)

1. Commit `dc8f031` has no session archive entry from when it landed — noted here retroactively, not separately logged.
2. Duplicate "4th session" label on 2026-07-27 in `SESSION.md` (this entry and the earlier "coordinator-slim chat rehydration" one) — cosmetic, offered to fix, not done.
