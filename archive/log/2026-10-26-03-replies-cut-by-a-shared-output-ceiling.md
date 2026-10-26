### 2026-10-26, third (replies cut short, blank or leaking internal text — thinking and reply shared one 4,096-token ceiling) — `core/orchestrator.py`, `core/trace.py`, `tests/test_native_stream_limits.py` — **uncommitted; Mike commits and deploys**

**The report (Mike):** "I did what I could on that, but couldn't finish the reply" at 18:22 and on
other recent turns, plus messages that read like Metatron's internal text.

**Diagnosed from VM traces and confirmed by a Fable review and a live probe.** `max_output_tokens`
was 4,096 at all four native Gemini config sites (since `2228511`, 06-24), and on Gemini 3.x
thinking counts against it. Across 1,275 Synthesizer rounds (08-10 → 10-26, on 3.1-pro and
3.8-flash) thinking + output never exceeded ~4,096. 3.8-flash rounds pile up at the wall (198 of
846 in the top 256-token bin): thinking stops near 3,930 and the reply gets ~160 tokens, about one
final reply in five. That one ceiling caused these symptoms:
- **blank replies** (`_NO_REPLY_LINE`);
- **replies cut mid-sentence** (Mike's "cut off after Frugality", 10-23);
- **a truncated `[CONTEXT]` block**, in 112 of 121 capped final rounds — the tracker silently
  missed those updates;
- **thinking or agent-file prose emitted as the reply** (10-22 17:35, 10-26 07:31): thinking
  force-stopped at the wall carried on in the visible channel.

**Believed true and wrong.** The 08-27 thinking probe
(`archive/plans/synthesizer_thinking_probe_2026-08-27.md`) read "max 3,930, no tail" as the model's
natural range and concluded the 4,096 budget "clips nothing". The 3,930 was this ceiling. The probe
named the possibility ("may reflect an implicit provider ceiling") and set it aside as irrelevant,
and a code comment said `max_output_tokens` does not limit thinking. The `[DB-0827-02]` close-out
rests on the same misreading. **Do not cite either for prompt sizing or thinking cost.**

**Live probe, 8 synthetic calls on the VM (gemini-3.8-flash):**
- **Wall reproduced:** 4,096/4,096 gave thinking 3,817 + reply 275, `MAX_TOKENS`, cut mid-sentence.
- **`thinking_budget` is a target, not a bound:** a budget of 1,024 thought 2,664, and a budget
  of 4,096 with room thought 5,673 (6,158 in total).
- **The final-reply 400 is the merged turn.** Function responses plus text in one user turn
  returns 400 "Requests ending with a model turn are not supported". A separate user turn, or a
  model bridge turn, answers.

**Changed:**
1. Output ceiling = thinking budget + 4,096 (8,192 for the Synthesizer).
2. The final-reply instruction is sent as its own user turn.
3. Cache creation is capped at 30 s: one hung 301 s at 16:16 and consumed the turn.
4. `finish_reason` is recorded on every native turn in the trace.
5. The thinking-cap event text is corrected.
6. A second Fable review of the final diff returned *ship with changes*. The changes taken:
   - `THINKING_CAP_HIT` is re-keyed to the hard ceiling (thinking + reply). Keyed on the
     overshot budget, it would have filled the Machine log with replies that were never cut.
   - One more stale "clips nothing" comment is removed.
   - A timeout-tail count is added to the post-deploy check.

Tests: `test_native_stream_limits.py` 14/14, `qa_sweep` 12/12.

**Rejected:**
- **Fable's 2,048-token reply room**, meant to bound how long a spill can run. The soft budget
  makes it unsafe: the 6,158-token probe call would have been cut.
- **Lowering the thinking budget.** It is not enforced, so it cannot bound anything.

**Not caused by the ceiling:**
- **10-26 18:25:** two consecutive 75 s read timeouts — Vertex slowness.
- **10-26 16:21:** the 301 s cache creation, then the 400.

**Left open:**
- **Specialists on 3.8-flash share the same 4,096 total** (physical_health peak 3,155); none has
  hit it yet.
- **The fallback-only compat path still sends `max_tokens: 4096`.**
- **Thinking spills still stream to the user before `filter_output` runs** — by design,
  `[DB-0815-11]`.

**Post-deploy check:** after a day, no Synthesizer turn with `finish_reason=MAX_TOKENS`, and none
whose reply opens mid-sentence or with `{`/`[CONTEXT]`.

