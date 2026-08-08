# Whisper STT evaluation — base.en vs small.en, VAD on/off

**Date:** 2026-08-08
**Measured on:** `metatron-vm`, e2-medium, 2 vCPU, Debian 12, Python 3.11.2 — **not** the Mac
**Runner:** [tests/bench_whisper_stt.py](bench_whisper_stt.py), 6 fixtures / 51.7s audio / 3 repeats
**Backlog item:** voice transcription accuracy — evaluate `small.en` + VAD

---

## Verdict

| | |
|---|---|
| **`small.en`** | **Rejected.** 5.9x slower, RTF 2.23, and *not* more accurate. |
| **VAD filter** | **Adopted.** ~7% faster at identical WER, plus silence-hallucination suppression. |
| **`beam_size=1`** | **Rejected.** 15% faster, measurably worse accuracy. |
| **Net change** | `base.en`, `beam_size=5`, **`vad_filter=True`** (was `False`). |

---

## Numbers (VM, 2 vCPU)

| config | median | p90 | RTF | WER | vs base | model load |
|---|---|---|---|---|---|---|
| `base.en` beam=5 vad=off *(was production)* | 2.554s | 3.689s | 0.381 | 3.9% | 1.00x | 5.7s |
| **`base.en` beam=5 vad=on** *(now production)* | **2.384s** | 3.721s | **0.361** | **3.9%** | **0.93x** | 2.8s |
| `base.en` beam=1 vad=on | 2.163s | 4.114s | 0.357 | worse | 0.85x | 0.6s |
| `small.en` beam=5 vad=off | 15.011s | 22.702s | 2.053 | 5.0% | 5.88x | 12.2s |
| `small.en` beam=5 vad=on | 14.860s | 22.691s | 2.233 | 5.0% | 5.82x | 8.0s |
| `small.en` beam=1 vad=on | 14.450s | 17.776s | 1.960 | 5.0% | 5.66x | 5.5s |

WER figures are from the corrected-reference rescoring (see *Scoring correction* below); the
raw sweep reported 8.1% for every config because two references scored a correct
transcription as an error.

---

## Why `small.en` is disqualified on latency alone

**RTF 2.23 means it transcribes slower than the audio arrives.** A 20-second dictation takes
~45 seconds to transcribe. That is bad on its own, but the structural problem is worse: STT
runs on a **single-worker** pool (`_STT_EXECUTOR`, [core/server.py:178](../core/server.py#L178)).
There is no second worker. So a slower model does not degrade gracefully into "everything is a
bit slower" — a second request that arrives mid-transcription **queues behind the first**, and
the queue grows faster than it drains whenever RTF > 1. `base.en` at RTF 0.36 has ~2.8x
headroom; `small.en` has none.

This is exactly why the item specified measuring on the VM. On an M-series Mac `small.en` is
comfortable, and adopting it from a laptop measurement would have shipped a queue.

## And it is not more accurate anyway

Four of the six fixtures score **0% WER on both models**. The entire measurable difference is
two fixtures, and neither favours `small.en`:

- **`email_address`** — both models produce the identical error, `diamond.mic.mt at gmail.com`
  for `diamond.mike.mt@gmail.com`. This is the documented live failure that
  `correct_known_addresses()` ([core/voice_pipeline.py](../core/voice_pipeline.py)) already
  repairs downstream. A bigger acoustic model does not fix it; the existing fuzzy-match against
  known recipients does.
- **`log_short`** — `base.en` writes "Logged" for "Log" (6.7%); `small.en` gets that right but
  merges "5 km" into "5km" (13.3%). Net: `small.en` scores *worse* on this set.

## Scoring correction made during the run

The first sweep reported a flat 8.1% WER for every configuration, which was a red flag rather
than a result. Two reference transcripts were scoring *correct* behaviour as error: Whisper is
supposed to render spoken "dot"/"at" as punctuation and spelled-out numbers as numerals. The
references now hold the expected **written** form (`_EXPECTED_TRANSCRIPTS` in the runner), which
is what moved the numbers to 3.9% / 5.0% and made the two models distinguishable at all.

---

## Limits of this evidence — read before citing it

1. **The fixtures are synthesized speech** (edge-tts, `en-GB-RyanNeural`), not a phone mic.
   They have no background noise, no accent variation, no clipping, no room tone. This is the
   regime where `base.en` and `small.en` are most alike; real-world noisy audio is exactly where
   a larger model would be expected to pull ahead.
2. So the honest scope of the accuracy claim is: **`small.en` shows no benefit on clean
   dictation.** It has *not* been shown to lack benefit on real audio. What rules it out today
   is the latency, which is measured, decisive, and independent of audio quality.
3. **The VAD win is understated here.** The fixtures are wall-to-wall speech with no silence, so
   they cannot show VAD's main benefit — suppressing the filler Whisper hallucinates on silent
   spans ("Thank you.", "Bye.", subtitle credits). `record_until_silence()` deliberately captures
   2.5s of trailing silence before submitting, so production audio always has a silent tail that
   the benchmark audio does not.
4. Model **load time** is a cold-start cost only — the model is loaded once at server startup
   ([core/server.py:358](../core/server.py#L358)) and held for the process lifetime.

## Follow-ups worth filing

1. **Re-evaluate on real captured audio.** The accuracy question is genuinely open for noisy
   input. Needs a handful of real phone recordings with hand-written references — cheap to
   collect during ordinary use, and it would make this benchmark load-bearing rather than
   indicative.
2. **Revisit `small.en` at D1.** Dedicated hardware changes the RTF arithmetic completely; this
   rejection is a statement about 2 vCPUs, not about the model.
3. **Consider a second STT worker** if concurrent voice use ever becomes real. Single-worker is
   correct today (one user), but it is the thing that turns any future model upgrade into a
   queueing problem rather than a latency problem.
