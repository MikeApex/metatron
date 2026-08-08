"""
tests/bench_whisper_stt.py — Whisper STT accuracy/latency sweep.

Answers one question: can the STT path afford a bigger model or a VAD filter?

RUN THIS ON THE VM, not the Mac. STT runs on a dedicated single-worker pool
(`_STT_EXECUTOR`, core/server.py:178) on a 2-vCPU e2-medium. A model that is 2x slower does
not make one transcription 2x slower — it makes concurrent requests queue behind each other,
because there is no second worker. An M-series laptop is several times faster than the VM and
will make an unaffordable model look comfortable.

    # on the VM
    cd ~/multi-model-mcp && source .venv/bin/activate
    python3 tests/bench_whisper_stt.py

Fixtures: tests/fixtures/stt/*.wav with a matching *.txt reference transcript. Generate them
with `python3 tests/bench_whisper_stt.py --generate` on the Mac (uses edge-tts), then scp the
directory to the VM. Synthetic speech is cleaner than a real phone mic, so treat the absolute
WER as a floor and the *relative* ordering between configs as the signal. The latency numbers
are real either way, and latency is the gating question.

Reports, per config: median and p90 wall time, real-time factor (RTF = decode time / audio
duration), and word error rate against the reference.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "stt"

# Dictation-shaped utterances: the things actually said to this system, including the
# address case that already produced a live failure (see correct_known_addresses).
_SAMPLE_TEXTS = {
    "log_short": "Log that I went for a five kilometre run this morning and felt good afterwards.",
    "calendar": "Put a dentist appointment in the calendar for next Tuesday at half past nine.",
    "email_address": "Send an email to diamond dot mike dot m t at gmail dot com about the invoice.",
    "reflective": (
        "I have been finding it hard to concentrate this week. I think it is because I have not "
        "been sleeping properly, and the deadline on the bookstore accounts keeps moving."
    ),
    "list_items": (
        "Add milk, ibuprofen, coffee beans and a new toothbrush to the shopping list, "
        "and remind me to call Tom about the weekend."
    ),
    "long_dictation": (
        "So today was reasonably productive overall. I finished the first draft of the chapter, "
        "went to the gym at lunchtime, and had a long conversation with Sarah about whether we "
        "should take the trip in September or wait until the spring. I am leaning towards "
        "September, but I want to look at the flight prices before deciding anything."
    ),
}

# Where a correct transcription legitimately differs from what was spoken. Whisper is
# *supposed* to render "dot"/"at" as punctuation and spelled-out numbers as numerals — scoring
# those as errors makes a good transcription look like a 35% WER and hides the real signal.
# Only list a fixture here when the written form differs from the spoken one.
_EXPECTED_TRANSCRIPTS = {
    "email_address": "Send an email to diamond.mike.mt@gmail.com about the invoice.",
    "log_short": "Log that I went for a 5 km run this morning and felt good afterwards.",
}

# The sweep. base.en/beam5/no-VAD is production as of 2026-08-08.
_CONFIGS = [
    {"model": "base.en", "beam": 5, "vad": False},
    {"model": "base.en", "beam": 5, "vad": True},
    {"model": "base.en", "beam": 1, "vad": True},
    {"model": "small.en", "beam": 5, "vad": False},
    {"model": "small.en", "beam": 5, "vad": True},
    {"model": "small.en", "beam": 1, "vad": True},
]


def _normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation. WER should not punish comma placement."""
    return re.sub(r"[^a-z0-9\s]", " ", text.lower()).split()


def _wer(reference: str, hypothesis: str) -> float:
    """Word error rate via Levenshtein distance over word tokens."""
    ref, hyp = _normalise(reference), _normalise(hypothesis)
    if not ref:
        return 0.0
    prev = list(range(len(hyp) + 1))
    for i, r in enumerate(ref, 1):
        cur = [i]
        for j, h in enumerate(hyp, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (r != h)))
        prev = cur
    return prev[-1] / len(ref)


def generate_fixtures() -> int:
    """Synthesize the sample utterances to 16kHz mono wav. Run on the Mac (needs network)."""
    import asyncio
    import subprocess

    import edge_tts

    FIXTURE_DIR.mkdir(parents=True, exist_ok=True)

    async def _one(name: str, text: str) -> None:
        mp3 = FIXTURE_DIR / f"{name}.mp3"
        wav = FIXTURE_DIR / f"{name}.wav"
        await edge_tts.Communicate(text, "en-GB-RyanNeural").save(str(mp3))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
             "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
        mp3.unlink(missing_ok=True)
        (FIXTURE_DIR / f"{name}.txt").write_text(_EXPECTED_TRANSCRIPTS.get(name, text))
        print(f"  wrote {wav.name}")

    async def _all() -> None:
        for name, text in _SAMPLE_TEXTS.items():
            await _one(name, text)

    asyncio.run(_all())
    print(f"\n{len(_SAMPLE_TEXTS)} fixtures in {FIXTURE_DIR}")
    print("Copy to the VM:")
    print("  gcloud compute scp --recurse tests/fixtures/stt "
          "metatron-vm:~/multi-model-mcp/tests/fixtures/ "
          "--zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap")
    return 0


def _load_fixtures() -> list[tuple[str, "object", float, str]]:
    import numpy as np
    import soundfile as sf

    items = []
    for wav in sorted(FIXTURE_DIR.glob("*.wav")):
        ref_path = wav.with_suffix(".txt")
        if not ref_path.exists():
            print(f"  skipping {wav.name} — no reference transcript")
            continue
        audio, rate = sf.read(str(wav), dtype="float32")
        if audio.ndim > 1:
            audio = audio.mean(axis=1)
        items.append((wav.stem, np.ascontiguousarray(audio), len(audio) / rate, ref_path.read_text()))
    return items


def run_bench(repeats: int, configs: list[dict]) -> int:
    from faster_whisper import WhisperModel

    fixtures = _load_fixtures()
    if not fixtures:
        print(f"No fixtures in {FIXTURE_DIR}. Run with --generate on the Mac first.")
        return 1

    total_audio = sum(f[2] for f in fixtures)
    print(f"\n{len(fixtures)} fixtures, {total_audio:.1f}s of audio, {repeats} repeat(s) each")
    print(f"Python {sys.version.split()[0]}\n")

    rows = []
    for cfg in configs:
        label = f"{cfg['model']} beam={cfg['beam']} vad={'on' if cfg['vad'] else 'off'}"
        print(f"[{label}] loading model...", flush=True)
        load_start = time.perf_counter()
        model = WhisperModel(cfg["model"], device="auto", compute_type="auto")
        load_s = time.perf_counter() - load_start

        # Warm-up pass — first decode pays one-off allocation costs that are not
        # representative of steady-state latency.
        model.transcribe(fixtures[0][1], beam_size=cfg["beam"], language="en",
                         vad_filter=cfg["vad"])

        times, rtfs, wers = [], [], []
        for _ in range(repeats):
            for name, audio, duration, reference in fixtures:
                start = time.perf_counter()
                segments, _ = model.transcribe(
                    audio, beam_size=cfg["beam"], language="en", vad_filter=cfg["vad"]
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                elapsed = time.perf_counter() - start
                times.append(elapsed)
                rtfs.append(elapsed / duration)
                wers.append(_wer(reference, text))

        row = {
            "config": label,
            "model": cfg["model"],
            "beam": cfg["beam"],
            "vad": cfg["vad"],
            "load_s": round(load_s, 2),
            "median_s": round(statistics.median(times), 3),
            "p90_s": round(sorted(times)[int(len(times) * 0.9) - 1], 3),
            "median_rtf": round(statistics.median(rtfs), 3),
            "mean_wer": round(sum(wers) / len(wers), 4),
            "worst_wer": round(max(wers), 4),
        }
        rows.append(row)
        print(f"  median {row['median_s']}s  p90 {row['p90_s']}s  "
              f"RTF {row['median_rtf']}  WER {row['mean_wer']:.1%}\n", flush=True)
        del model

    baseline = next((r for r in rows if r["model"] == "base.en" and r["beam"] == 5
                     and not r["vad"]), rows[0])

    print("=" * 84)
    print(f"{'config':<30}{'median':>9}{'p90':>9}{'RTF':>8}{'WER':>9}{'vs base':>10}{'load':>9}")
    print("-" * 84)
    for r in rows:
        delta = r["median_s"] / baseline["median_s"] if baseline["median_s"] else 0
        print(f"{r['config']:<30}{r['median_s']:>8.3f}s{r['p90_s']:>8.3f}s"
              f"{r['median_rtf']:>8.3f}{r['mean_wer']:>8.1%}{delta:>9.2f}x{r['load_s']:>8.1f}s")
    print("=" * 84)
    print("\nRTF < 1.0 means faster than real time. On a single-worker pool, RTF is also the")
    print("queueing factor: at RTF 0.5 a 10s utterance occupies the only STT worker for 5s.")

    out = Path(__file__).parent / f"stt_bench_{time.strftime('%Y-%m-%d')}.json"
    out.write_text(json.dumps(rows, indent=2))
    print(f"\nWrote {out}")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Whisper STT accuracy/latency sweep")
    parser.add_argument("--generate", action="store_true",
                        help="Synthesize fixtures with edge-tts (run on the Mac)")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--models", help="Comma-separated subset, e.g. 'base.en,small.en'")
    args = parser.parse_args()

    if args.generate:
        sys.exit(generate_fixtures())

    configs = _CONFIGS
    if args.models:
        wanted = {m.strip() for m in args.models.split(",")}
        configs = [c for c in configs if c["model"] in wanted]
    sys.exit(run_bench(args.repeats, configs))
