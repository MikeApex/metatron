"""
Kokoro TTS speaker — called as a subprocess by voice_pipeline.py.

Usage: echo "text to speak" | python speak.py
       python speak.py --voice af_heart

Reads text from stdin, synthesises with Kokoro, plays via afplay.
Voice can be overridden with --voice flag.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro import KPipeline

DEFAULT_VOICE = "af_heart"
SAMPLE_RATE = 24000

_pipeline: KPipeline | None = None


def get_pipeline() -> KPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = KPipeline(lang_code="a")
    return _pipeline


def speak(text: str, voice: str = DEFAULT_VOICE, output: str | None = None) -> None:
    pipeline = get_pipeline()
    chunks = [audio for _, _, audio in pipeline(text, voice=voice)]
    if not chunks:
        return
    audio = np.concatenate(chunks)
    if output:
        sf.write(output, audio, SAMPLE_RATE)
    else:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            wav_path = Path(f.name)
        sf.write(str(wav_path), audio, SAMPLE_RATE)
        subprocess.run(["afplay", str(wav_path)], check=False)
        wav_path.unlink(missing_ok=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--output", default=None, help="Write WAV to this path instead of playing")
    args = parser.parse_args()

    text = sys.stdin.read().strip()
    if text:
        speak(text, voice=args.voice, output=args.output)
