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
