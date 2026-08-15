### 2026-08-15 (Bulgarian speech-in benchmarked on the VM, held indefinitely)

**Mike reported "Latin characters in my speaking transliteration" in Bulgarian mode.** This
looked at first like a repeat of the same-day `[DB-0815-04]` render defect (the Synthesizer's
*response* script), already fixed in `core/translate.py` (`8a7d1d7`) and confirmed deployed —
the VM's checked-out commit (`19cfd12`) is a descendant. It was not that. Mike clarified live:
the defect is in the **transcript of his own spoken Bulgarian**, not the assistant's reply — a
different half of the pipeline entirely, tracked separately as `[DB-0815-02](a)`.

**Root cause:** `WHISPER_MODEL_SIZE` is `base.en` — an English-only faster-whisper model that
cannot emit Cyrillic at any language setting, regardless of the `language=` parameter passed to
it (which is wired correctly and env-overridable via `METATRON_WHISPER_LANGUAGE`, but inert
against an English-only model). This also explains a `SELF_APPLIED` event found earlier the same
day, where the Synthesizer read Mike's forced-Latin STT output as a standing preference and
silently applied it — a separate defect, `[DB-0815-11]`.

**Benchmarked on the VM (never the Mac — an M-series laptop understates real cost):**

| Model | Lang | RTF | WER |
|---|---|---|---|
| `base` (multilingual) | en | 0.247 | 5.0% |
| `base` | bg | 0.305 | 46.4% |
| `small` (multilingual) | en | 0.767 | 6.1% |
| `small` | bg | 0.967 | 27.6% |

`small`'s multilingual config didn't exist in `tests/bench_whisper_stt.py` — only `small.en`
(English-only) was defined. Added two rows to `_CONFIGS` (`base`/`bg` and `en` already existed
from the earlier `[DB-0815-04]` work; `small`/`en`+`bg` added this session) rather than a
one-off script, so the sweep is repeatable if a better local model shows up later.

**Decision: hold `[DB-0815-02](a)` in `## Later` indefinitely — Mike's call, not a default.**
Neither candidate clears an acceptable bar. `base` gets the right script but is wrong roughly
half the time. `small` roughly halves the error rate (27.6%) but its Bulgarian RTF (0.967) is
functionally real-time on the VM's single-worker STT pool — almost no queueing headroom, and
adopting it unconditionally would also regress English RTF 0.247 → 0.767. **No per-language
model-selection design (small for `bg` only, keep `base.en` for `en`) was attempted** — the WER
floor itself, ~28% best case, was judged not worth engineering around. Revisit only if a
materially better local multilingual STT model or different hardware becomes available; not
scheduled.

Deployed: no code shipped (backlog note + benchmark config only). Commits: none this session
beyond the fragment/backlog/log update below — `tests/bench_whisper_stt.py`'s two new `_CONFIGS`
rows are staged for commit in this close-out.
