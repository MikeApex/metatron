#!/usr/bin/env python3
"""
Step 10 of the knowledge-layer plan: move `health_notes` out of profile.yaml and into the
wisdom store, where it is retrieved when relevant instead of riding every head-layer prompt.

WHY THIS IS A SCRIPT AND NOT A ONE-LINER. It touches `data/personas/{p}/` and
`config/personas/{p}/profile.yaml` for a real user, on the VM, and it is destructive to the
profile field. Dry-run is the default; --apply is required; the value is printed for review
before anything is written. The plan names this the one step that is expensive to reverse.

RUN IT ON THE VM, AFTER the code deploy. Never from the Mac for `mike`: persona data is
VM-owned, and a Mac-side write would be overwritten or would fork the user's history.

    python scripts/migrate_health_notes.py --persona mike            # dry run
    python scripts/migrate_health_notes.py --persona mike --apply

Afterwards, `health_notes` can be retired from _SCALAR_FIELDS and _PROMPT_EXCLUDED in
tools/profile.py — a separate commit, because the data must be gone before the field is.
"""

import argparse
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_config_dir, persona_scope, resolve_persona  # noqa: E402
from tools.wisdom import (  # noqa: E402
    DOMAINS, _RESERVED_KEY_TERMS, find_related_wisdom, read_wisdom, write_wisdom,
)

# Mike's value is "Standard oatmeal: 60g oats, 100g 2% milk..." — a breakfast composition,
# which is `food` on the subject axis regardless of the field it was stored under being
# called "health". Filing it as `health` would repeat the naming error the axis re-cut fixed:
# the field name described who asked, not what the fact is about.
DEFAULT_KEY = "standard_breakfast"
DEFAULT_DOMAIN = "food"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--key", default=DEFAULT_KEY)
    ap.add_argument("--domain", default=DEFAULT_DOMAIN, choices=DOMAINS)
    ap.add_argument("--apply", action="store_true", help="write; otherwise dry-run")
    args = ap.parse_args()

    persona = resolve_persona(args.persona)
    profile_path = persona_config_dir(persona) / "profile.yaml"
    if not profile_path.exists():
        # Almost always one thing: this is the Mac. `mike`'s config and data tree exist only
        # on the VM (.gitignore: data/personas/*/), so a Mac-side run finds nothing — which is
        # the correct outcome, but "no profile at ..." reads like a missing file rather than a
        # wrong machine, and that is a message someone acts on by creating the file.
        print(f"No profile at {profile_path}")
        if not (persona_config_dir(persona) / "goals.yaml").exists():
            print(
                f"\nThere is no '{persona}' config on this machine at all.\n"
                f"If this is the Mac and '{persona}' is the real user: that is expected and "
                f"nothing is wrong — persona data is VM-owned. SSH to the VM and run it there.\n"
                f"Do NOT create the file here: a Mac-side copy forks the user's history."
            )
        return 1

    profile = yaml.safe_load(profile_path.read_text()) or {}
    value = (profile.get("health_notes") or "").strip()
    if not value:
        print(f"'{persona}' has no health_notes — nothing to migrate.")
        return 0

    print(f"persona     : {persona}\nprofile     : {profile_path}")
    print(f"health_notes: {value}")
    print(f"→ wisdom    : key='{args.key}' domain='{args.domain}' provenance='stated'")

    # The reserved-name guard refuses on the KEY; this catches the other half — a value that
    # is actually about medication has no business in a store read at a model's discretion,
    # whatever it is keyed as. Refuse and point at the profile store the safety flag reads.
    lowered = value.lower()
    hit = next((t for t in _RESERVED_KEY_TERMS if t in lowered), "")
    if hit:
        print(f"\nREFUSED: the value mentions '{hit}'. A safety flag must not depend on a "
              f"discretionary read — put this in write_agent_config (medication_profile), "
              f"not in the wisdom store. Migrate the rest by hand.")
        return 1

    with persona_scope(persona):
        existing = read_wisdom(key=args.key)
        if existing:
            print(f"\nNOTE: '{args.key}' already exists and will be OVERWRITTEN:\n  {existing.get('value')}")

        # A key match is not enough, and this is the case that proved it: mike's store already
        # held this exact fact under `oatmeal_formula`, so the key check reported "no collision"
        # and the migration would have written a second breakfast entry beside an empty
        # placeholder. Warn only — a near-duplicate and a genuine refinement are not
        # distinguishable automatically, and overwriting the refinement is the costly direction.
        related = find_related_wisdom(value, args.domain)
        if related:
            print(f"\nALREADY IN '{args.domain}' — REVIEW BEFORE APPLYING ({len(related)}):")
            for hit in related:
                print(f"  · {hit['key']}  [{hit['reason']}]\n      {hit['value'][:100]}")
            print("\n  Nothing here is merged automatically. If one of these IS this fact:")
            print(f"    - overwrite it:  --key {related[0]['key']}")
            print("    - or apply as-is, then archive the old one with merge_wisdom_entries().")

        if not args.apply:
            print("\ndry run — nothing written. Re-run with --apply.")
            return 0

        print("\n" + write_wisdom(args.key, value, domain=args.domain, provenance="stated"))

    # Clear the profile field only after the wisdom write succeeded, and only that key —
    # rewriting the whole file from the parsed dict would silently drop comments and any
    # field this script does not know about.
    profile.pop("health_notes", None)
    profile_path.write_text(yaml.safe_dump(profile, sort_keys=False, allow_unicode=True))
    profile_path.chmod(0o600)
    print(f"health_notes removed from {profile_path}")
    print("\nNext: python tests/run_a4_safety.py --suite pipeline  (required regression)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
