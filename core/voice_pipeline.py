"""
core/voice_pipeline.py — Whisper STT + macOS TTS pipeline.

Laptop voice mode: record from mic → Whisper transcription → orchestrator → say.
Run directly for an interactive voice session:
    python core/voice_pipeline.py
    python core/voice_pipeline.py --persona pepys --provider openai
"""

import argparse
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import sounddevice as sd

# Whisper model is loaded once at module level to avoid reload cost per session.
_whisper_model = None
WHISPER_MODEL_SIZE = "base.en"   # base.en: fast, English-only, ~150MB. Upgrade to "small.en" for accuracy.
SAMPLE_RATE = 16000              # Whisper expects 16kHz


# ---------------------------------------------------------------------------
# Whisper STT
# ---------------------------------------------------------------------------

def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        _whisper_model = WhisperModel(WHISPER_MODEL_SIZE, device="auto", compute_type="auto")
    return _whisper_model


def record_until_silence(
    silence_threshold: float = 0.01,
    silence_duration: float = 1.5,
    max_duration: float = 60.0,
) -> np.ndarray:
    """
    Record from the default mic until silence is detected or max_duration reached.

    Returns audio as a float32 numpy array at SAMPLE_RATE.
    """
    print("  [listening...]", end="", flush=True)

    chunk_size = int(SAMPLE_RATE * 0.1)   # 100ms chunks
    max_chunks = int(max_duration / 0.1)
    silence_chunks_needed = int(silence_duration / 0.1)

    audio_chunks = []
    silence_count = 0
    recording_started = False

    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > silence_threshold:
                recording_started = True
                silence_count = 0
            elif recording_started:
                silence_count += 1

            if recording_started:
                audio_chunks.append(chunk)

            if recording_started and silence_count >= silence_chunks_needed:
                break

    print(" done.")

    if not audio_chunks:
        return np.zeros(0, dtype=np.float32)

    return np.concatenate(audio_chunks, axis=0).flatten()


def transcribe(audio: np.ndarray) -> str:
    """Transcribe audio array to text using faster-whisper."""
    if len(audio) == 0:
        return ""

    model = _get_whisper()
    segments, _ = model.transcribe(audio, beam_size=5, language="en")
    return " ".join(seg.text.strip() for seg in segments).strip()


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

def speak(text: str, voice: str = "Samantha") -> None:
    """
    Speak text using macOS `say`. Blocks until speech completes.
    Voice options: Samantha (default), Alex, Tom, Victoria, etc.
    Full list: `say -v ?` in terminal.
    """
    subprocess.run(["say", "-v", voice, text], check=False)


# ---------------------------------------------------------------------------
# Voice session
# ---------------------------------------------------------------------------

def run_voice_session(
    agent_name: str = "time_director",
    persona: str | None = None,
    provider: str = "anthropic",
) -> None:
    """
    Interactive voice session: listen → transcribe → run_session → speak.
    Press Ctrl+C to exit.
    """
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from core.orchestrator import run_session

    label = agent_name.replace("_", " ").title()
    if persona:
        label += f" [{persona}]"
    print(f"\nLife Manager Voice — {label} [{provider}]")
    print("Speak after the prompt. Pause to submit. Ctrl+C to exit.\n")

    # Warm up Whisper on first load
    print("Loading speech model...", end="", flush=True)
    _get_whisper()
    print(" ready.\n")

    while True:
        try:
            print("You:", end=" ", flush=True)
            audio = record_until_silence()

            if len(audio) == 0:
                print("  (no audio detected)")
                continue

            transcript = transcribe(audio)
            if not transcript:
                print("  (couldn't transcribe)")
                continue

            print(f"  → \"{transcript}\"")

            response = run_session(agent_name, transcript, persona=persona, provider=provider)
            print(f"\nAssistant: {response}\n")
            speak(response)

        except KeyboardInterrupt:
            print("\nGoodbye.")
            speak("Goodbye.")
            break
        except Exception as e:
            print(f"\nError: {e}\n")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Life Manager — Voice Mode")
    parser.add_argument("--agent", default="time_director")
    parser.add_argument("--persona", help="Dev persona (e.g. pepys)")
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai"])
    args = parser.parse_args()

    run_voice_session(args.agent, persona=args.persona, provider=args.provider)
