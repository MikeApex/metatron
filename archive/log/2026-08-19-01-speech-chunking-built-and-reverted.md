### 2026-08-19 (the app's turns reach the prompt cache and stream; spoken chunking built, measured and reverted) — `core/orchestrator.py`, `core/server.py`, `static/index.html`, `ROADMAP.md` — `81be0f7`…`c6f6dc2`, **deployed mid-session, final revert owes one**

**Incoming handoff:** `archive/handoffs/2026-08-18-caching-fix-prompt.md`. Reviewed in Fable, built
in Opus. **Mike's standing decision from that split: plan and review in Fable, build in Opus** — the
review turned the first build into a one-line branch and caught five constraints the brief did not
carry.

**What shipped and stays.** The interactive Synthesizer path reaches the Vertex prompt cache *and*
streams: `run_session_gemini_cached_stream()` → `_run_gemini_native_stream()`. Verified live —
**19,157 of a 20,534-token turn served from cache (93%)**, **9 chunks on the wire**. Cost per turn
**$0.0685 → $0.0397** at $2/$12. Simpler than the brief predicted: streamed `function_call` parts
carry `thought_signature` (probed, 6,330 bytes), so none of `_openai_compat_stream`'s blocking
replay is needed.

**What was built and reverted the same day — sentence-chunked TTS.** Mike, after using it:
*"30 second delay after the language populated. Too many resources for an incremental gain."*
**The measurement is the finding, and it generalises:** the whole reply arrives in **~0.6s**; 86% of
Synthesizer-generated tokens are **thinking**; sentence release was never the bottleneck (first
sentence out **0.15s** after the first text chunk). **Chunked speech pays only when generation is
slow relative to synthesis** — here generation is a sub-second burst and the wait is thinking.
Reverting also **closed a security gap rather than solving it**: spoken audio cannot be retracted,
so `filter_output` (LLM06) was weaker on the voice path than on the screen. Full record kept in
`ROADMAP.md` § 5A so nobody re-opens it unknowingly.

**Four of this session's own claims were wrong, and every one was caught by running something.**
1. **The brief's "46×"** compared an interactive median against a scheduled median dominated by
   **19 near-empty turns**; real scheduled turns cost what interactive ones do. The defect was real,
   the causal story was not.
2. **"Option A closes `[DB-0818-10]`"** — written into three files, then corrected the same day:
   86% thinking means streaming shortens no silence.
3. **"The speech change cannot affect Coordinator dispatch"** — it could. In-band `[SPEAK]` markers
   broke the contract that every non-control chunk is display text, so consumers reassembling with
   `"".join(...)` got the reply doubled. **`run_knowledge_routing.py` caught it**; replaced with an
   out-of-band `on_speak` callback.
4. **A degenerate reply** (`think=0`, 36 tokens of gibberish) failed the A4 clinical gate once.
   HEAD 3/3, re-run 3/3, no reproduction — and a first hypothesis (exhausted output budget) died on
   measurement (`out+think` never exceeded 2,284 of 4,096).

**Two things Mike killed, both correctly.** A backlog item for that degenerate reply — *"if it was a
one off, does it require research so long as it doesn't happen again? A coherence check should
either be done now or not at all"*: the research half was **an item with no exit**, and framing the
guard as an open question was filing instead of deciding. Removed; **decision recorded as do not
build**, since a guard tuned on one unreproducible sample is likelier to suppress a good reply.
And option (c) of `[DB-0818-10]`, a "thinking" affordance, was found **already built** — the mic
button reads `Thinking...` for the whole wait; its informative version is barred by § Discretion.

**Two infrastructure facts established by running things, both of which had been distorting
readings:** `prompt_token_count` **includes** cached tokens (so caching is invisible in trace data),
and **INFO never reaches `journalctl`** (units log WARNING+), so any turn under 8k leaves no log
record at all.

**Deploy friction worth remembering:** `deploy.sh` aborted because a committed A4 report used the
runner's **default** filename and collided with the VM's own untracked report of the same name.
Renamed this end's copy rather than clearing the VM's, which was real evidence. **This recurs** —
the VM regenerates that default name whenever A4 runs there. Separately, the **commit guard fired**
on `core/server.py` because `git revert` writes outside what it tracks; overridden only after
verifying the staged diff held no foreign lines and the file was byte-identical to `46f31b5`.

**Closed:** `[DB-0818-10]`, written up in `archive/backlog_closed_2026-08.md`.
**Rejected:** capping the thinking budget here (Mike is handling it elsewhere); a coherence guard;
keeping spoken chunking behind a tighter buffer.

