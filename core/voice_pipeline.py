"""
core/voice_pipeline.py — Whisper STT + TTS pipeline.

Laptop voice mode: record from mic → Whisper transcription → orchestrator → speak.
Run directly for an interactive voice session:
    python core/voice_pipeline.py
    python core/voice_pipeline.py --persona pepys --provider openai

TTS: edge-tts (Microsoft neural voices) with Piper as offline fallback.
To change voice: update EDGE_VOICE. Run `edge-tts --list-voices` to see options.
Good alternatives: en-US-GuyNeural, en-US-ChristopherNeural, en-GB-RyanNeural
"""

import argparse
import asyncio
import os
import re
import subprocess
import tempfile
from pathlib import Path


import numpy as np

# ---------------------------------------------------------------------------
# Whisper STT settings
#
# Env-overridable so a model change is a config edit, not a code edit, and so
# tests/bench_whisper_stt.py can sweep combinations without patching this file.
#
# SIZING CONSTRAINT — read before raising WHISPER_MODEL_SIZE. STT runs on a
# dedicated single-worker pool (`_STT_EXECUTOR` in core/server.py:178) on a
# 2-vCPU e2-medium. A model that is 2x slower does not make one transcription
# 2x slower; it makes concurrent requests *queue*, because there is no second
# worker to take them. Measure on the VM, not the Mac: an M-series laptop is
# several times faster and will make an unaffordable model look fine.
# Benchmark: `python3 tests/bench_whisper_stt.py` — run it on the VM.
# ---------------------------------------------------------------------------
_whisper_model = None
# MEASURED ON THE VM 2026-08-08 (tests/bench_whisper_stt.py, report in
# tests/stt_bench_report_2026-08-08_vm.md). small.en was evaluated and REJECTED:
#
#   base.en  beam=5 vad=on   2.38s median   RTF 0.36   WER 3.9%
#   small.en beam=5 vad=on  14.86s median   RTF 2.23   WER 5.0%
#
# small.en is 5.9x slower and *not* more accurate on this set. RTF above 1.0 means it
# transcribes slower than the audio arrives, which on a one-worker pool turns a second
# concurrent request into a queue. Do not adopt it on 2 vCPUs. Revisit only on D1 hardware.
WHISPER_MODEL_SIZE = os.getenv("METATRON_WHISPER_MODEL", "base.en")
# beam=1 was measured too: 15% faster, but WER worsened (3.9% -> 9.2% on the earlier scoring).
# Not worth it — decode time is not the bottleneck at RTF 0.36.
WHISPER_BEAM_SIZE = int(os.getenv("METATRON_WHISPER_BEAM", "5"))
# VAD drops non-speech spans before decoding: ~7% faster at identical WER, and it suppresses
# the filler Whisper hallucinates on silence ("Thank you.", "Bye.") — which the synthetic
# benchmark fixtures cannot exercise but a real mic with room tone produces routinely. Do
# not disable it to fix truncation — tune it instead (below).
WHISPER_VAD = os.getenv("METATRON_WHISPER_VAD", "1") != "0"
# [DB-0803-01], diagnosed 2026-08-09: at Silero's defaults (threshold=0.5,
# speech_pad_ms=400), a clause trailing off in volume crosses the threshold before real
# silence, and 400ms of padding isn't enough to recover it. 18-16-16.webm ended
# "...communicating" instead of "...communicating with what we put in." — the whole
# trailing clause dropped, silently, no error.
#
# Tuned 2026-08-10 against all 108 files retained in data/audio/ (report:
# /tmp/vad_final.log, not committed — regenerate with the script in that session's
# archive/PROJECT_LOG.md entry if these values are ever revisited). Measured against a
# VAD-off transcription as the practical ceiling for each file:
#
#   defaults (0.5  / 400ms)   97.6% avg recovered, 0 files with hallucination markers
#   tuned    (0.30 / 1500ms)  98.1% avg recovered, 0 files with hallucination markers,
#                             and the one file that motivated this — 18-16-16.webm —
#                             goes from 85.9% to a full match.
#
# The corpus is 108 files of real dictated speech and cannot exercise VAD's OTHER job —
# suppressing hallucinated filler on pure silence/room tone, which needs an accidental
# recording with no real speech in it at all. Zero hallucination markers here is evidence
# this tuning doesn't obviously break that, not proof it's untouched. That is the reasoning
# for tuning VAD rather than disabling it: loosen the parameters that caused the measured
# failure, keep the mechanism whose failure mode this corpus can't measure.
WHISPER_VAD_THRESHOLD = float(os.getenv("METATRON_WHISPER_VAD_THRESHOLD", "0.30"))
WHISPER_VAD_SPEECH_PAD_MS = int(os.getenv("METATRON_WHISPER_VAD_SPEECH_PAD_MS", "1500"))
SAMPLE_RATE = 16000              # Whisper expects 16kHz

# Kokoro TTS settings.
# Voice IDs: af_heart, af_bella, af_sky, am_adam, bm_george — see tools/kokoro/speak.py
KOKORO_VOICE = "af_heart"
KOKORO_SPEAK = Path(__file__).parent.parent / "tools" / "kokoro" / "speak.py"
KOKORO_PYTHON = Path(__file__).parent.parent / ".venv" / "bin" / "python"

# edge-tts fallback voice (used if Kokoro venv not set up / network available).
EDGE_VOICE = "en-US-JennyNeural"

# Piper last-resort fallback.
VOICES_DIR = Path(__file__).parent.parent / "data" / "voices"
PIPER_VOICE = VOICES_DIR / "en_US-lessac-high.onnx"

_piper_voice = None


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
    silence_duration: float = 2.5,
    min_speech_duration: float = 1.0,
    max_duration: float = 120.0,
) -> np.ndarray:
    """
    Record from the default mic until silence is detected or max_duration reached.

    Silence detection only kicks in after min_speech_duration seconds of speech,
    preventing premature cutoff on natural mid-sentence pauses.

    Returns audio as a float32 numpy array at SAMPLE_RATE.
    """
    print("  [listening...]", end="", flush=True)

    chunk_size = int(SAMPLE_RATE * 0.1)       # 100ms chunks
    max_chunks = int(max_duration / 0.1)
    silence_chunks_needed = int(silence_duration / 0.1)
    min_speech_chunks = int(min_speech_duration / 0.1)

    audio_chunks = []
    silence_count = 0
    speech_chunk_count = 0
    recording_started = False

    import sounddevice as sd
    with sd.InputStream(samplerate=SAMPLE_RATE, channels=1, dtype="float32") as stream:
        for _ in range(max_chunks):
            chunk, _ = stream.read(chunk_size)
            rms = float(np.sqrt(np.mean(chunk ** 2)))

            if rms > silence_threshold:
                recording_started = True
                silence_count = 0
                speech_chunk_count += 1
            elif recording_started:
                silence_count += 1

            if recording_started:
                audio_chunks.append(chunk)

            # Only end on silence after minimum speech duration has been captured
            if (recording_started
                    and speech_chunk_count >= min_speech_chunks
                    and silence_count >= silence_chunks_needed):
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
    segments, _ = model.transcribe(
        audio,
        beam_size=WHISPER_BEAM_SIZE,
        language="en",
        vad_filter=WHISPER_VAD,
        vad_parameters={
            "threshold": WHISPER_VAD_THRESHOLD,
            "speech_pad_ms": WHISPER_VAD_SPEECH_PAD_MS,
        } if WHISPER_VAD else None,
    )
    return " ".join(seg.text.strip() for seg in segments).strip()


# A well-formed email, and a looser fallback for the case Whisper drops the "@"
# entirely (observed live: "diamond.like.gmail.com" for "diamond.mike@gmail.com") —
# a dotted run ending in a known free-mail domain, with no "@" required.
_EMAIL_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._%+-]*@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_BARE_DOMAIN_RE = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._%+-]*\.(?:gmail|yahoo|outlook|icloud|hotmail)\.[A-Za-z]{2,}",
    re.IGNORECASE,
)
_CORRECTION_THRESHOLD = 0.72  # SequenceMatcher ratio; tuned against the two known
                              # real cases (diamond.mic@… / diamond.like.gmail.com).


def correct_known_addresses(transcript: str, persona: str) -> str:
    """
    Snap a dictated email address to the closest known address (the user's own,
    or a saved CRM contact) when Whisper mis-transcribes it.

    Scope, deliberately narrow: this fixes wrong characters in an address that
    is otherwise recognizably email-shaped — the documented failure mode
    (diamond.mic -> diamond.mike, a dropped "@"). It does not attempt to parse
    "spelled out" dictation ("d as in dog, i, a, ...") or invent an address
    with no known match; unmatched spans are left as Whisper produced them.
    """
    import difflib

    from core.persona import persona_scope
    from tools.mail import _known_recipients

    with persona_scope(persona):
        try:
            known = list(_known_recipients().keys())
        except Exception:
            known = []
    if not known:
        return transcript

    def _best_match(candidate: str) -> str | None:
        best_addr, best_ratio = None, 0.0
        for addr in known:
            ratio = difflib.SequenceMatcher(None, candidate.lower(), addr.lower()).ratio()
            if ratio > best_ratio:
                best_addr, best_ratio = addr, ratio
        return best_addr if best_ratio >= _CORRECTION_THRESHOLD else None

    def _replace(m: re.Match) -> str:
        match = _best_match(m.group(0))
        return match if match else m.group(0)

    corrected = _EMAIL_RE.sub(_replace, transcript)
    corrected = _BARE_DOMAIN_RE.sub(_replace, corrected)
    return corrected


# ---------------------------------------------------------------------------
# TTS
# ---------------------------------------------------------------------------

def _get_piper():
    global _piper_voice
    if _piper_voice is None:
        from piper.voice import PiperVoice
        _piper_voice = PiperVoice.load(str(PIPER_VOICE))
    return _piper_voice


def _strip_markdown(text: str) -> str:
    """Remove markdown formatting so TTS reads cleanly."""
    text = re.sub(r"#{1,6}\s*", "", text)          # headings
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)   # bold
    text = re.sub(r"\*(.+?)\*", r"\1", text)        # italic
    text = re.sub(r"`(.+?)`", r"\1", text)          # inline code
    text = re.sub(r"^\s*[-*+]\s+", "", text, flags=re.MULTILINE)  # bullets
    text = re.sub(r"^\s*\d+\.\s+", "", text, flags=re.MULTILINE)  # numbered lists
    text = re.sub(r"\n{2,}", "\n", text)            # collapse blank lines
    return text.strip()


def _speak_kokoro(text: str) -> None:
    """Speak via Kokoro (local neural TTS, Python 3.12 venv subprocess)."""
    result = subprocess.run(
        [str(KOKORO_PYTHON), str(KOKORO_SPEAK), "--voice", KOKORO_VOICE],
        input=text,
        text=True,
        check=True,
    )


async def _speak_edge(text: str) -> None:
    import edge_tts
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
        mp3_path = Path(f.name)
    communicate = edge_tts.Communicate(text, EDGE_VOICE)
    await communicate.save(str(mp3_path))
    subprocess.run(["afplay", str(mp3_path)], check=False)
    mp3_path.unlink(missing_ok=True)


def _speak_piper_fallback(text: str) -> None:
    import wave
    piper_voice = _get_piper()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
        wav_path = Path(f.name)
    with wave.open(str(wav_path), "wb") as wav:
        piper_voice.synthesize_wav(text, wav)
    subprocess.run(["afplay", str(wav_path)], check=False)
    wav_path.unlink(missing_ok=True)


def speak(text: str) -> None:
    """Speak via Kokoro → edge-tts → Piper, in order of preference."""
    clean = _strip_markdown(text)
    if KOKORO_PYTHON.exists():
        try:
            _speak_kokoro(clean)
            return
        except Exception:
            pass
    try:
        asyncio.run(_speak_edge(clean))
    except Exception:
        _speak_piper_fallback(clean)


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
    parser.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "ollama", "gemini"])
    args = parser.parse_args()

    run_voice_session(args.agent, persona=args.persona, provider=args.provider)
