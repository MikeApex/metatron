"""
tests/generate_synthetic_data.py — Synthetic data generator for Phase 4 testing.

Generates 8 weeks of realistic daily log and journal entries for the
ryan_holiday persona, starting from a configurable date.

DESIGN PRINCIPLE:
Entries are generated WITHOUT planted correlations. Field values are drawn
from realistic distributions using randomness only — no deliberate "if X
then Y" logic. This means the Pattern Miner may surface real statistical
structure that emerged from the generator's own randomness. A finding
is a valid insight if the Pattern Miner surfaces it, regardless of whether
the generator intended it. The generator is not the oracle; the Pattern
Miner is. Absence of a planted pattern does not invalidate a finding.

See tests/testing_framework_notes.md for discussion of this methodology.

Usage:
    python tests/generate_synthetic_data.py
    python tests/generate_synthetic_data.py --start 2026-03-01 --weeks 8
    python tests/generate_synthetic_data.py --index   # also embed into FAISS
"""

from __future__ import annotations

import argparse
import json
import os
import random
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_ROOT = Path(__file__).parent.parent
_PERSONA = "ryan_holiday"

# ---------------------------------------------------------------------------
# Content pools — realistic Ryan Holiday persona texture
# ---------------------------------------------------------------------------

BOOKS = [
    "Meditations — Marcus Aurelius",
    "The War of Art — Pressfield",
    "On the Shortness of Life — Seneca",
    "Letters from a Stoic — Seneca",
    "Antifragile — Taleb",
    "The Obstacle Is the Way — Holiday",
    "Stillness Is the Key — Holiday",
    "Daily Stoic — Holiday",
    "The Republic — Plato",
    "Discourses — Epictetus",
    "Lives — Plutarch",
    "The Art of War — Sun Tzu",
    "On Living and Dying Well — Cicero",
    "Man's Search for Meaning — Frankl",
    "The Power of Myth — Campbell",
]

WRITING_FEELINGS = [
    "good flow, pages moving",
    "rough start, found rhythm by midmorning",
    "slow and resistant",
    "pushing through mud",
    "clear and sharp",
    "distracted, kept returning to research",
    "better than yesterday",
    "strong session, ran long",
    "blocked on structure",
    "productive but tired by end",
    "cards coming together",
    "argument not landing yet",
    "clean draft work",
    "rewriting more than writing",
]

BLOCKER_OPTIONS = [
    "chapter structure not resolved",
    "source material gap — need to research",
    "Cato section stalled",
    "too many anecdotes, not enough argument",
    "introduction still not right",
    "narrative thread not clear",
    "competing deadlines pulling focus",
    "tired from late night",
    "kids had rough night",
    "couldn't get quiet time until afternoon",
    "",  # no blocker
    "",
    "",
    "",
]

WIN_OPTIONS = [
    "got the morning walk in",
    "hit word count target",
    "finished a chapter draft",
    "good reading session",
    "resolved the structure problem",
    "strong email to editor",
    "cleared the inbox",
    "good run in the park",
    "family dinner together",
    "Liam read to me before bed",
    "found the right Seneca quote",
    "cards finally organized",
    "took the afternoon off — needed it",
    "finished a book",
    "workout done before 7am",
]

EXERCISE_OPTIONS = [
    "morning run",
    "trail run",
    "run with the boys",
    "strength training",
    "long walk",
    "bike ride",
    "swim",
    "yoga",
]

NOTES_TEMPLATES = [
    "Writing went {writing_feeling} today. {extra}",
    "Spent the morning on the {chapter} chapter. {extra}",
    "Reading {book} on the run. {extra}",
    "Good day overall. {extra}",
    "Rough start but finished strong. {extra}",
    "The {chapter} argument is starting to come together. {extra}",
    "Sent draft sections to editor. {extra}",
    "Research day — less writing, more reading. {extra}",
    "Family in town this week, writing schedule compressed. {extra}",
    "Travel tomorrow — trying to get ahead today. {extra}",
]

CHAPTER_OPTIONS = [
    "Cato", "Temperance", "Caesar", "Discipline", "Courage",
    "Justice", "prologue", "introduction", "conclusion", "first",
]

EXTRA_NOTES = [
    "Seneca on wasted time keeps coming up.",
    "Boys were up early — lost the quiet morning window.",
    "Good conversation with Nils about structure.",
    "Thinking about the throughline more carefully.",
    "Need to cut at least a third of this section.",
    "The Plutarch parallel is working.",
    "Deadline pressure starting to clarify things.",
    "",
    "",
    "",
]

MOODS = ["good", "great", "solid", "neutral", "rough", "tired", "focused", "energized"]
ENERGY_LEVELS = ["high", "medium", "medium", "low", "very low"]
FOCUS_LEVELS = ["sharp", "good", "moderate", "struggling", "scattered"]


# ---------------------------------------------------------------------------
# Entry generators
# ---------------------------------------------------------------------------

def _rand_sleep() -> float:
    """Sleep hours: roughly normal around 7.0, occasional short nights."""
    base = random.gauss(7.0, 1.2)
    return round(max(4.0, min(10.0, base)) * 2) / 2  # round to nearest 0.5


def _rand_writing_pages() -> int:
    """Writing output: 0-8 pages, with some zero days."""
    if random.random() < 0.12:
        return 0  # off day
    return max(0, round(random.gauss(3.5, 1.8)))


def generate_log(entry_date: date) -> dict:
    """Generate a single daily log entry."""
    sleep = _rand_sleep()
    writing_feeling = random.choice(WRITING_FEELINGS)
    mood = random.choice(MOODS)
    energy = random.choice(ENERGY_LEVELS)
    focus = random.choice(FOCUS_LEVELS)
    pages = _rand_writing_pages()

    tasks = []
    if random.random() < 0.8:
        tasks.append(random.choice(EXERCISE_OPTIONS))
    if random.random() < 0.7:
        tasks.append("morning writing session")
    if random.random() < 0.4:
        tasks.append("reading")
    if random.random() < 0.3:
        tasks.append("email and correspondence")
    if random.random() < 0.2:
        tasks.append("research")

    blockers = []
    b = random.choice(BLOCKER_OPTIONS)
    if b:
        blockers.append(b)

    wins = random.sample(WIN_OPTIONS, k=random.randint(1, 3))

    reading = []
    if random.random() < 0.6:
        reading.append(random.choice(BOOKS))

    note_template = random.choice(NOTES_TEMPLATES)
    notes = note_template.format(
        writing_feeling=writing_feeling,
        chapter=random.choice(CHAPTER_OPTIONS),
        book=random.choice(BOOKS),
        extra=random.choice(EXTRA_NOTES),
    ).strip()

    return {
        "date": entry_date.isoformat(),
        "sleep_hours": sleep,
        "writing_feeling": writing_feeling,
        "writing_pages": pages,
        "tasks_completed": tasks,
        "mood": mood,
        "energy": energy,
        "focus": focus,
        "blockers": blockers,
        "wins": wins,
        "reading": reading,
        "notes": notes,
    }


def generate_journal(entry_date: date, log: dict) -> dict:
    """Generate a short journal entry consistent with the day's log."""
    fragments = []

    if log["sleep_hours"] < 6:
        fragments.append(
            f"Short night — {log['sleep_hours']} hours. "
            f"Tried to get to the desk early anyway."
        )
    elif log["sleep_hours"] >= 8:
        fragments.append(
            f"Slept well, {log['sleep_hours']} hours. "
            f"Woke up with some clarity about the chapter."
        )

    if log["writing_pages"] > 0:
        fragments.append(
            f"Writing went {log['writing_feeling']}. "
            f"Got {log['writing_pages']} pages done."
        )
    elif log["writing_feeling"]:
        fragments.append(f"Writing: {log['writing_feeling']}.")

    if log["blockers"]:
        fragments.append(f"Stuck on: {log['blockers'][0]}.")

    if log["reading"]:
        fragments.append(f"Reading: {log['reading'][0]}.")

    if log["wins"]:
        fragments.append(f"Best thing today: {random.choice(log['wins'])}.")

    text = " ".join(f for f in fragments if f)
    if not text:
        text = f"Ordinary day. Mood: {log['mood']}."

    return {
        "date": entry_date.isoformat(),
        "entries": [
            {
                "timestamp": f"{entry_date.isoformat()}T08:{random.randint(0,59):02d}:00",
                "text": text,
                "tags": [log["mood"], log["energy"], "synthetic"],
            }
        ],
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def generate(start_date: date, weeks: int, also_index: bool) -> None:
    persona_dir = _ROOT / "data" / "personas" / _PERSONA
    logs_dir = persona_dir / "logs"
    journal_dir = persona_dir / "journal"
    logs_dir.mkdir(parents=True, exist_ok=True)
    journal_dir.mkdir(parents=True, exist_ok=True)

    days_total = weeks * 7
    generated = 0
    skipped = 0

    print(f"Generating {days_total} days of synthetic data for '{_PERSONA}'...")
    print(f"Start: {start_date}  End: {start_date + timedelta(days=days_total - 1)}")

    for i in range(days_total):
        d = start_date + timedelta(days=i)

        log_path = logs_dir / f"{d.isoformat()}.json"
        journal_path = journal_dir / f"{d.isoformat()}.json"

        if log_path.exists() or journal_path.exists():
            skipped += 1
            continue

        log = generate_log(d)
        journal = generate_journal(d, log)

        with open(log_path, "w") as f:
            json.dump(log, f, indent=2)
        os.chmod(log_path, 0o600)

        with open(journal_path, "w") as f:
            json.dump(journal, f, indent=2)
        os.chmod(journal_path, 0o600)

        generated += 1

        if also_index:
            os.environ["AI_TEST_PERSONA"] = _PERSONA
            from core.memory import index_entry
            index_entry(
                text=log["notes"] + " " + journal["entries"][0]["text"],
                source="synthetic_log",
                entry_date=d.isoformat(),
            )

    print(f"Done. Generated: {generated}  Skipped (already exist): {skipped}")
    if also_index:
        print("Entries embedded into FAISS index.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic persona data for Phase 4 testing")
    parser.add_argument("--start", default="2026-03-01", help="Start date YYYY-MM-DD (default: 2026-03-01)")
    parser.add_argument("--weeks", type=int, default=8, help="Number of weeks to generate (default: 8)")
    parser.add_argument("--index", action="store_true", help="Also embed entries into FAISS")
    args = parser.parse_args()

    generate(
        start_date=date.fromisoformat(args.start),
        weeks=args.weeks,
        also_index=args.index,
    )
