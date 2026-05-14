"""
Audition Kokoro voices blind — numbered, randomized, revealed at the end.
Run: tools/kokoro/venv/bin/python tools/kokoro/audition.py
"""
import random
import subprocess
from pathlib import Path

SPEAK = Path(__file__).parent / "speak.py"
PYTHON = Path(__file__).parent / "venv" / "bin" / "python"

# Full shortlist preference order (blind runs, 2026-05-14):
#   Male:   am_liam > am_puck > bm_lewis > am_michael
#   Female: af_heart > bf_lily > bf_isabella > af_sky  (af_bella dismissed)
#   Active voice: af_heart (set in core/voice_pipeline.py → KOKORO_VOICE)
SHORTLIST = [
    "af_heart",
    "af_sky",
    "bf_isabella",
    "bf_lily",
]

SAMPLE = "Good morning. I have three things for your attention today — none urgent, but each with a cost to leaving it open."


def audition() -> None:
    voices = SHORTLIST[:]
    random.shuffle(voices)

    picks: list[str] = []
    reveal: list[tuple[int, str]] = []

    print(f"\nAuditioning {len(voices)} voices, blind. Note the numbers you like.\n")

    for i, voice_id in enumerate(voices, 1):
        text = f"Voice number {i}. {SAMPLE}"
        print(f"  Voice {i} of {len(voices)}")
        subprocess.run(
            [str(PYTHON), str(SPEAK), "--voice", voice_id],
            input=text,
            text=True,
        )
        reveal.append((i, voice_id))
        input("    Press Enter for next, or Ctrl+C to stop...\n")

    print("\n--- Results ---")
    for num, voice_id in reveal:
        print(f"  {num}: {voice_id}")
    print("\nTell me your picks by number.")


if __name__ == "__main__":
    try:
        audition()
    except KeyboardInterrupt:
        print("\nStopped.")
