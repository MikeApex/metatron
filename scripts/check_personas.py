#!/usr/bin/env python3
"""
scripts/check_personas.py — read-only consistency check across persona files.

Every persona owns a complete universe:
    config/personas/{name}.md            identity (required)
    config/personas/{name}/              tier 1-3 config + settings
    data/personas/{name}/                everything written for that persona

This reports drift between those three: identity files with no config directory,
data directories with no persona, names that would be rejected by the resolver,
and personas missing a profile.

Read-only. Never writes, never deletes. Exits 1 if any error-level problem found
so it can gate a deploy; warnings alone exit 0.

Usage:
    python scripts/check_personas.py
    python scripts/check_personas.py --strict   # treat warnings as failures too
"""

import argparse
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import PersonaError, validate_persona_name  # noqa: E402

ROOT = Path(__file__).parent.parent
CONFIG_PERSONAS = ROOT / "config" / "personas"
DATA_PERSONAS = ROOT / "data" / "personas"

# Files a persona needs before it can hold a real session.
REQUIRED = ["prime_directive.md", "mission.md", "goals.yaml"]
SETTINGS = ["profile.yaml", "scheduler.yaml", "caldav.yaml"]

errors: list[str] = []
warnings: list[str] = []


def _identity_names() -> list[str]:
    if not CONFIG_PERSONAS.is_dir():
        return []
    out = []
    for p in sorted(CONFIG_PERSONAS.glob("*.md")):
        try:
            out.append(validate_persona_name(p.stem))
        except PersonaError as e:
            errors.append(f"config/personas/{p.name}: unusable persona name — {e}")
    return out


def _dir_names(base: Path) -> list[str]:
    if not base.is_dir():
        return []
    out = []
    for p in sorted(base.iterdir()):
        if not p.is_dir():
            continue
        try:
            out.append(validate_persona_name(p.name))
        except PersonaError:
            errors.append(
                f"{p.relative_to(ROOT)}: directory name is not a valid persona "
                f"— the resolver would reject it, so nothing can read or write here"
            )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Check persona file consistency (read-only).")
    ap.add_argument("--strict", action="store_true", help="Treat warnings as failures.")
    args = ap.parse_args()

    identities = _identity_names()
    config_dirs = _dir_names(CONFIG_PERSONAS)
    data_dirs = _dir_names(DATA_PERSONAS)

    if not identities:
        errors.append("No persona identity files found in config/personas/*.md")

    print(f"Personas with an identity file: {', '.join(identities) or '(none)'}\n")

    for name in identities:
        cdir = CONFIG_PERSONAS / name
        problems = []

        # load_config() tolerates missing tier files — it checks each one and
        # skips it. So these degrade the persona, they do not break it. Warning,
        # not error: a linter that reports non-problems stops being read.
        if not cdir.is_dir():
            warnings.append(
                f"{name}: no config directory — runs with identity only "
                f"(no prime directive, mission or goals)"
            )
        else:
            missing = [f for f in REQUIRED if not (cdir / f).exists()]
            if missing:
                warnings.append(f"{name}: missing " + ", ".join(missing))
            if not (cdir / "profile.yaml").exists():
                # Not fatal, but the persona gets no name/location/timezone at all
                # now that the root fallback is gone.
                warnings.append(
                    f"{name}: no profile.yaml — this persona runs with no name, "
                    f"location or timezone (there is no longer a shared fallback)"
                )
            for f in SETTINGS[1:]:
                if not (cdir / f).exists():
                    warnings.append(f"{name}: no {f}")

        if problems:
            errors.append(f"{name}: " + "; ".join(problems))
            print(f"  [ERROR] {name}: {'; '.join(problems)}")
        else:
            bits = []
            bits.append("full config" if cdir.is_dir() and not
                        [f for f in REQUIRED if not (cdir / f).exists()]
                        else "identity only")
            bits.append("has data" if name in data_dirs else "no data yet")
            print(f"  [ok]    {name:18s} ({', '.join(bits)})")

    # Orphans in both directions
    for name in config_dirs:
        if name not in identities:
            errors.append(
                f"config/personas/{name}/ exists but config/personas/{name}.md does not "
                f"— load_config() raises FileNotFoundError for this persona"
            )
    for name in data_dirs:
        if name not in identities:
            warnings.append(
                f"data/personas/{name}/ has no identity file — orphaned data, "
                f"nothing can read it"
            )

    # Scheduler drift — preference jobs only.
    #
    # The silent maintenance jobs no longer need checking: they register for
    # every persona from _DEFAULT_JOBS in core/scheduler.py (2026-08-08). What
    # still can't be defaulted is the class with a prompt or a notification
    # channel — a morning brief's wording and timing are genuinely personal, so
    # they stay in per-persona config and can therefore still drift from the
    # template as it gains entries. That is exactly how daily_travel_check would
    # have been missed, and how daily_calendar_dedup_audit was missed for three
    # days before the defaults existed.
    #
    # Reported as a warning, never an error: a persona legitimately may not want
    # the template's full set, and this script must stay safe to run in CI.
    tmpl_path = ROOT / "config" / "templates" / "scheduler.yaml"
    if tmpl_path.exists():
        try:
            tmpl_jobs = (yaml.safe_load(tmpl_path.read_text()) or {}).get("schedules", {}) or {}
        except Exception as e:
            warnings.append(f"could not read the scheduler template: {e}")
            tmpl_jobs = {}

        for name in sorted(identities):
            sched = ROOT / "config" / "personas" / name / "scheduler.yaml"
            if not sched.exists():
                continue
            try:
                have = (yaml.safe_load(sched.read_text()) or {}).get("schedules", {}) or {}
            except Exception as e:
                warnings.append(f"{name}: scheduler.yaml does not parse — {e}")
                continue
            missing = [j for j in tmpl_jobs if j not in have]
            if missing:
                warnings.append(
                    f"{name}: scheduler.yaml is missing {len(missing)} job(s) present in the "
                    f"template — {', '.join(sorted(missing))}. The template is copied once at "
                    f"persona creation and never re-synced, so these will not arrive on their "
                    f"own; add them to the persona's own scheduler.yaml (on the VM, if that is "
                    f"where the persona lives)."
                )

    print()
    for w in warnings:
        print(f"  [warn]  {w}")
    for e in errors:
        print(f"  [ERROR] {e}")

    print(f"\n{len(errors)} error(s), {len(warnings)} warning(s)")
    if errors:
        return 1
    if warnings and args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
