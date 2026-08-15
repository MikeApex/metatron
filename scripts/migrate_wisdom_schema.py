#!/usr/bin/env python3
"""
scripts/migrate_wisdom_schema.py — one-off migration of wisdom.json to the domain/provenance schema.

Run this ON THE VM. The VM owns live persona data (.claude/rules/personas.md); the Mac copy is
stale — at the time this was written, the newest Mac-side backup was 12 days old and the local
data/personas/mike/ had no wisdom/ directory at all. Migrating from a snapshot would silently
discard every entry written since that snapshot.

    python3 scripts/migrate_wisdom_schema.py --persona mike            # review only, writes nothing
    python3 scripts/migrate_wisdom_schema.py --persona mike --apply    # writes, after a backup

WHAT IT DOES
    category -> domain + provenance, per tools/wisdom.py.

    The six legacy categories (patterns, quirks, preferences, health, seasonal, annual) carry
    almost no domain signal — nothing derives `food` from `preferences` — so a purely mechanical
    pass is not possible. Three tiers, in order:

      1. KEY_MAP below: hand-assigned domains for entries known to exist as of 2026-08-03,
         reviewed individually against their text.
      2. Keyword heuristics for entries written since, scored over key + value.
      3. Anything unresolved lands in `other` with proposed_domain preserved, which is the
         designed overflow queue — visible to the Pattern Miner sweep, never a silent guess.

    Provenance defaults to `observed` — the tentative surfacing register. The stored records
    carry NO provenance signal whatsoever, so `stated` is only ever set from KEY_MAP, where a
    human judged the entry's own wording ("User requested…", "User expressed…"). Guessing
    `stated` from text would manufacture a confidence the data does not contain.

WHAT IT DOES NOT DO
    It never deletes and never relocates an entry to another store. Entries that do not belong
    in wisdom at all are REPORTED under `misfiled` with a suggested destination, and are still
    migrated in place so nothing is lost. Moving them is a separate, deliberate act.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.wisdom import DOMAINS, OVERFLOW_DOMAIN, PROVENANCE  # noqa: E402

# Hand-assigned, one line of judgement per entry. (domain, provenance, note)
# `note` is non-empty only where the entry looks like it belongs in a different store.
KEY_MAP: dict[str, tuple[str, str, str]] = {
    "sleep_external_disruption": ("sleep", "observed", ""),
    "sleep_debt_pattern_june_2026": (
        "sleep", "observed",
        "dated episodic observation (June 2026), not standing knowledge — belongs in the log/journal",
    ),
    "lunch_options": ("food", "stated", ""),
    "exercise_schedule": ("fitness", "stated", ""),
    "personal_contact_update_2026_08_02": (
        "identity", "observed",
        "an event record, not standing knowledge — the contact data itself belongs in the profile "
        "(see [DB-0815-05])",
    ),
    "voice_transcription_issues": (
        "other", "stated",
        "a report about the tool, not knowledge about the user — belongs in DEV_BACKLOG.md",
    ),
    "fitness_energy_conflict": ("fitness", "observed", ""),
    "dietary_analysis_interest": ("food", "observed", ""),
    "salad_dressing_habit": ("food", "stated", ""),
    "beverage_choices": ("food", "stated", ""),
    "conversational_preferences": (
        "identity", "stated",
        "an interaction preference — how the user wants to be dealt with belongs in "
        "config/personas/{persona}.md via write_persona, not in the fact store",
    ),
    "user_preference_interaction_fluidity": (
        "identity", "stated",
        "an interaction preference — belongs in the persona file, not the fact store",
    ),
    "monthly_financial_reminder": (
        "money", "stated",
        "a recurring obligation — obligations are data rows (open_obligation/list_obligations), "
        "per logistics.md:189",
    ),
    "exercise_sustainability": ("fitness", "observed", ""),
    "communication_style_preference": (
        "identity", "stated",
        "an interaction preference — belongs in the persona file, not the fact store",
    ),
}

# Fallback for entries written after 2026-08-03. Ordered: first domain with a hit wins, so the
# more specific subjects are listed before the broader ones they would otherwise be swallowed by.
KEYWORD_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("sleep",         ("sleep", "slept", "insomnia", "bedtime", "woke", "nap", "rest", "tired")),
    ("food",          ("eat", "ate", "food", "diet", "meal", "lunch", "dinner", "breakfast",
                       "snack", "oats", "protein", "sugar", "sodium", "drink", "coffee",
                       "espresso", "tea", "caffeine", "hydrat", "milk", "fruit", "vegetable",
                       "beer", "alcohol", "cook", "recipe", "portion")),
    ("fitness",       ("exercise", "workout", "training", "gym", "run", "ruck", "lift",
                       "cardio", "weights", "strength", "steps", "walk")),
    ("health",        ("health", "symptom", "illness", "pain", "injur", "doctor", "medical",
                       "medication", "prescription", "diagnos", "throat", "headache")),
    ("money",         ("money", "spend", "budget", "financ", "cost", "payment", "bill",
                       "invoice", "saving", "credit card", "tax")),
    ("work",          ("work", "job", "career", "employer", "meeting", "deadline", "client",
                       "colleague", "office", "project")),
    ("relationships", ("friend", "family", "wife", "partner", "kids", "children", "social",
                       "contact", "relationship", "conversation with")),
    ("learning",      ("learn", "study", "book", "reading", "course", "skill", "practice",
                       "language", "guitar")),
    ("recreation",    ("hobby", "hobbies", "leisure", "game", "film", "movie", "music",
                       "holiday", "weekend", "fun", "camping", "collect", "photograph")),
    ("home",          ("home", "house", "chore", "errand", "shopping", "tidy", "garden",
                       "admin", "household")),
    ("identity",      ("personality", "value", "trait", "big five", "self", "identity",
                       "believes", "temperament", "disposition")),
]


def classify(entry: dict) -> tuple[str, str, str, str]:
    """Return (domain, provenance, note, how) for one legacy entry."""
    key = entry.get("key", "")
    if key in KEY_MAP:
        domain, provenance, note = KEY_MAP[key]
        return domain, provenance, note, "reviewed"

    haystack = f"{key} {entry.get('value', '')}".lower()
    for domain, needles in KEYWORD_RULES:
        if any(n in haystack for n in needles):
            return domain, "observed", "", "keyword"

    return OVERFLOW_DOMAIN, "observed", "", "overflow"


def migrate(path: Path, apply: bool) -> int:
    if not path.exists():
        print(f"No wisdom store at {path} — nothing to migrate.")
        return 0

    entries = json.loads(path.read_text())
    before = len(entries)

    rows, misfiled = [], []
    counts: Counter = Counter()
    how_counts: Counter = Counter()

    for entry in entries:
        if "domain" in entry and "provenance" in entry:
            counts[entry["domain"]] += 1
            how_counts["already-migrated"] += 1
            continue

        legacy = entry.pop("category", "")
        domain, provenance, note, how = classify(entry)

        entry["domain"] = domain
        entry["provenance"] = provenance
        if domain == OVERFLOW_DOMAIN and legacy:
            entry["proposed_domain"] = legacy

        counts[domain] += 1
        how_counts[how] += 1
        rows.append((entry.get("key", "?"), legacy, domain, provenance, how))
        if note:
            misfiled.append((entry.get("key", "?"), note))

    width = max((len(r[0]) for r in rows), default=10)
    print(f"\n{path}  —  {before} entries\n")
    print(f"  {'key'.ljust(width)}  {'was':<12} {'domain':<14} {'provenance':<10} via")
    print(f"  {'-' * width}  {'-' * 12} {'-' * 14} {'-' * 10} ---")
    for key, legacy, domain, provenance, how in rows:
        print(f"  {key.ljust(width)}  {legacy:<12} {domain:<14} {provenance:<10} {how}")

    print(f"\n  domains:  {dict(counts)}")
    print(f"  assigned: {dict(how_counts)}")

    if misfiled:
        print(f"\n  ⚠ {len(misfiled)} entries look like they belong in a different store.")
        print("    Migrated in place regardless — nothing is lost. Moving them is a separate act.\n")
        for key, note in misfiled:
            print(f"      · {key}\n          {note}")

    assert len(entries) == before, "entry count changed — refusing to write"

    if not apply:
        print(f"\n  Review only. Nothing written. Re-run with --apply to write.\n")
        return 0

    backup = path.with_suffix(f".json.bak-{date.today().isoformat()}")
    shutil.copy2(path, backup)
    path.write_text(json.dumps(entries, indent=2))
    print(f"\n  Backed up → {backup}")
    print(f"  Wrote {len(entries)} entries → {path}\n")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--persona", required=True, help="Persona whose store to migrate.")
    ap.add_argument("--apply", action="store_true", help="Write. Omit to review only.")
    args = ap.parse_args()

    import os
    os.environ["METATRON_PERSONA"] = args.persona
    from core.persona import persona_data_dir

    return migrate(persona_data_dir() / "wisdom" / "wisdom.json", args.apply)


if __name__ == "__main__":
    raise SystemExit(main())
