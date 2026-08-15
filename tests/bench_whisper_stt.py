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

# [DB-0810-15] Bulgarian sample set, parallel in shape to _SAMPLE_TEXTS, so the multilingual
# "base" model can be swept against real dictation-shaped Bulgarian rather than just English.
# core/voice_pipeline.py's WHISPER_MODEL_SIZE stays "base.en" (English-only, cannot decode
# Bulgarian at any language setting) until a VM run of this script produces the RTF number —
# this fixture set is what makes that run possible, it does not itself decide anything.
_SAMPLE_TEXTS_BG = {
    "log_short_bg": "Записах, че тази сутрин направих пет километра бягане и се почувствах добре.",
    "calendar_bg": "Запиши час при зъболекар за следващия вторник в девет и половина.",
    "reflective_bg": (
        "Тази седмица ми беше трудно да се концентрирам. Мисля, че е защото не спя добре, "
        "а крайният срок за отчетите непрекъснато се мести."
    ),
}

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

# [DB-0810-15] No numeral-rendering overrides needed for the Bulgarian set yet — none of the
# three sample texts spell out a number the way "five kilometre" does above. Add entries here
# the same way if a future Bulgarian fixture needs one.
_EXPECTED_TRANSCRIPTS_BG: dict[str, str] = {}

# Per-language fixture config: sample text set, edge-tts voice, and the fixture subdirectory.
# "en" keeps its existing flat layout (tests/fixtures/stt/*.wav) for backward compatibility
# with any report or script that already points there; other languages get their own
# subdirectory (tests/fixtures/stt/<lang>/) so fixture sets never collide.
_LANGUAGES = {
    "en": {
        "texts": _SAMPLE_TEXTS,
        "expected": _EXPECTED_TRANSCRIPTS,
        "voice": "en-GB-RyanNeural",
        "dir": FIXTURE_DIR,
    },
    "bg": {
        "texts": _SAMPLE_TEXTS_BG,
        "expected": _EXPECTED_TRANSCRIPTS_BG,
        "voice": "bg-BG-BorislavNeural",
        "dir": FIXTURE_DIR / "bg",
    },
}

# The sweep. base.en/beam5/no-VAD is production as of 2026-08-08. "lang" defaults to "en" for
# every pre-existing row so the original English sweep is untouched. The two "base" rows are
# [DB-0810-15]'s addition: "base" (multilingual) on English isolates the cost of switching
# model family alone; "base" on "bg" is the actual number needed to decide whether Bulgarian
# is affordable on the VM's single-worker STT pool — that decision is NOT made by this file,
# only measured by it. Run with e.g. `--models base --languages en,bg` to sweep just those.
_CONFIGS = [
    {"model": "base.en", "beam": 5, "vad": False, "lang": "en"},
    {"model": "base.en", "beam": 5, "vad": True, "lang": "en"},
    {"model": "base.en", "beam": 1, "vad": True, "lang": "en"},
    {"model": "small.en", "beam": 5, "vad": False, "lang": "en"},
    {"model": "small.en", "beam": 5, "vad": True, "lang": "en"},
    {"model": "small.en", "beam": 1, "vad": True, "lang": "en"},
    {"model": "base", "beam": 5, "vad": True, "lang": "en"},
    {"model": "base", "beam": 5, "vad": True, "lang": "bg"},
]


def _normalise(text: str) -> list[str]:
    """Lowercase, strip punctuation. WER should not punish comma placement.

    Unicode-aware ([^\\w\\s] rather than [^a-z0-9\\s]) so Cyrillic (Bulgarian) tokens survive
    normalisation instead of being stripped to nothing, which would silently zero out WER for
    every non-Latin fixture. Behaviour for English text is unchanged — \\w is a superset of
    a-z0-9 there.
    """
    return re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE).split()


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


def generate_fixtures(language: str = "en") -> int:
    """Synthesize the sample utterances to 16kHz mono wav. Run on the Mac (needs network)."""
    import asyncio
    import subprocess

    import edge_tts

    lang_cfg = _LANGUAGES[language]
    fixture_dir = lang_cfg["dir"]
    texts = lang_cfg["texts"]
    expected = lang_cfg["expected"]
    voice = lang_cfg["voice"]

    fixture_dir.mkdir(parents=True, exist_ok=True)

    async def _one(name: str, text: str) -> None:
        mp3 = fixture_dir / f"{name}.mp3"
        wav = fixture_dir / f"{name}.wav"
        await edge_tts.Communicate(text, voice).save(str(mp3))
        subprocess.run(
            ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp3),
             "-ar", "16000", "-ac", "1", str(wav)],
            check=True,
        )
        mp3.unlink(missing_ok=True)
        (fixture_dir / f"{name}.txt").write_text(expected.get(name, text))
        print(f"  wrote {wav.name}")

    async def _all() -> None:
        for name, text in texts.items():
            await _one(name, text)

    asyncio.run(_all())
    print(f"\n{len(texts)} '{language}' fixtures in {fixture_dir}")
    print("Copy to the VM:")
    print("  gcloud compute scp --recurse tests/fixtures/stt "
          "metatron-vm:~/multi-model-mcp/tests/fixtures/ "
          "--zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap")
    return 0


def _load_fixtures(language: str = "en") -> list[tuple[str, "object", float, str]]:
    import numpy as np
    import soundfile as sf

    fixture_dir = _LANGUAGES[language]["dir"]
    items = []
    for wav in sorted(fixture_dir.glob("*.wav")):
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

    # Load fixtures per language lazily and cache — most sweeps use only "en", and a config
    # naming an unsupported/ungenerated language should fail on that config, not up front.
    fixtures_by_lang: dict[str, list] = {}
    for cfg in configs:
        lang = cfg.get("lang", "en")
        if lang not in fixtures_by_lang:
            loaded = _load_fixtures(lang)
            if not loaded:
                print(f"No '{lang}' fixtures in {_LANGUAGES[lang]['dir']}. "
                      f"Run with --generate --language {lang} on the Mac first.")
            fixtures_by_lang[lang] = loaded

    if not any(fixtures_by_lang.values()):
        return 1

    print(f"Python {sys.version.split()[0]}\n")

    rows = []
    for cfg in configs:
        lang = cfg.get("lang", "en")
        fixtures = fixtures_by_lang[lang]
        if not fixtures:
            continue  # already warned above

        label = (f"{cfg['model']} beam={cfg['beam']} vad={'on' if cfg['vad'] else 'off'} "
                  f"lang={lang}")
        total_audio = sum(f[2] for f in fixtures)
        print(f"[{label}] {len(fixtures)} fixtures, {total_audio:.1f}s audio — "
              f"loading model...", flush=True)
        load_start = time.perf_counter()
        model = WhisperModel(cfg["model"], device="auto", compute_type="auto")
        load_s = time.perf_counter() - load_start

        # Warm-up pass — first decode pays one-off allocation costs that are not
        # representative of steady-state latency.
        model.transcribe(fixtures[0][1], beam_size=cfg["beam"], language=lang,
                         vad_filter=cfg["vad"])

        times, rtfs, wers = [], [], []
        for _ in range(repeats):
            for name, audio, duration, reference in fixtures:
                start = time.perf_counter()
                segments, _ = model.transcribe(
                    audio, beam_size=cfg["beam"], language=lang, vad_filter=cfg["vad"]
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
            "lang": lang,
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

    if not rows:
        return 1

    baseline = next((r for r in rows if r["model"] == "base.en" and r["beam"] == 5
                     and not r["vad"] and r["lang"] == "en"), rows[0])

    print("=" * 96)
    print(f"{'config':<42}{'median':>9}{'p90':>9}{'RTF':>8}{'WER':>9}{'vs base':>10}{'load':>9}")
    print("-" * 96)
    for r in rows:
        delta = r["median_s"] / baseline["median_s"] if baseline["median_s"] else 0
        print(f"{r['config']:<42}{r['median_s']:>8.3f}s{r['p90_s']:>8.3f}s"
              f"{r['median_rtf']:>8.3f}{r['mean_wer']:>8.1%}{delta:>9.2f}x{r['load_s']:>8.1f}s")
    print("=" * 96)
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
    parser.add_argument("--language", default="en", choices=sorted(_LANGUAGES),
                        help="Language to synthesize fixtures for with --generate "
                             "(default 'en'; [DB-0810-15] adds 'bg' for the Bulgarian sweep)")
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--models", help="Comma-separated subset, e.g. 'base.en,small.en,base'")
    parser.add_argument("--languages", help="Comma-separated subset of config languages to run, "
                        "e.g. 'bg' to run only the Bulgarian rows")
    args = parser.parse_args()

    if args.generate:
        sys.exit(generate_fixtures(args.language))

    configs = _CONFIGS
    if args.models:
        wanted = {m.strip() for m in args.models.split(",")}
        configs = [c for c in configs if c["model"] in wanted]
    if args.languages:
        wanted_langs = {l.strip() for l in args.languages.split(",")}
        configs = [c for c in configs if c.get("lang", "en") in wanted_langs]
    sys.exit(run_bench(args.repeats, configs))
