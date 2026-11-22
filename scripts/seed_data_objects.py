#!/usr/bin/env python3
"""
Seed one user's data-object registry (archive/plans/custom_logs_and_places_plan_2026-11-21.md
phase 1, item 10): register the stores that already exist, every archive category already on
disk, and the cardiac log as `identity: occurrence`, `class: health`.

NOTHING MOVES (R27). Registering writes one file — data/personas/{p}/data_objects.json — and
never touches an entry. Re-running is safe: an id already registered is skipped.

RUN IT ON THE VM, AFTER the code deploy. Persona data is VM-owned (`data/personas/**` is Denied
to Claude Code), and a Mac-side write would fork the user's history.

    .venv/bin/python scripts/seed_data_objects.py --persona mike            # dry run
    .venv/bin/python scripts/seed_data_objects.py --persona mike --apply

The dry run reads only: no file is written, no model is called. --apply registers, then tags
each existing archive category with the relevance tagger — one bulk-tier call apiece
(≈ $0.0005 each; plan § 7). The cardiac log is not tagged by model: its class rule already
gives it both health agents, which is what the 11-16 rebuild named.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_data_dir, persona_scope, resolve_persona  # noqa: E402

# The stores that already exist, registered not moved (R27). Each keeps its own tools.
NATIVE_STORES = [
    ("wisdom", "Standing knowledge", "Facts and habits about the user that stay true."),
    ("contacts", "Contacts", "The people in the user's life and how to reach them."),
    ("tasks", "Tasks", "One-off and recurring tasks, what is due and recently closed."),
    ("profile", "Profile", "Stable biographical facts."),
    ("log", "Daily log", "The day-by-day log: wellbeing, health, focus, wins."),
    ("goals", "Goals", "The user's goals at every horizon."),
    ("calendar", "Calendar", "Events on the user's calendars."),
    ("day_shape", "Day shape", "How the user's days are usually laid out."),
    ("agent_config", "Agent settings", "Each area's standing settings for this user."),
]

CARDIAC = {
    "object_id": "cardiac_events",
    "name": "Cardiac events",
    "aliases": ["heart log", "cardiac log", "heart monitor log"],
    "description": "Times the heart monitor recorded something, with the reason.",
    "identity": "occurrence",
    "class_": "health",
}

# Bookkeeping fields every writer adds — not the object's own fields.
_BOOKKEEPING = {"date_added", "date_updated", "recorded_at", "previous", "occurrences",
                "merged_from"}


def _naming_agents(cat: str, DO) -> list[str]:
    """Areas that could read this category before it was registered and name it in their own
    instruction file — kept as readers, so registering never takes a list away from the area
    that keeps it (Fable review, 2026-11-22). Registration narrows who may read a category
    from "anyone holding write_archive" to its readers; this is the floor under that."""
    words = {cat.lower(), cat.lower().replace("_", " ")}
    out = []
    for a in DO.TAGGABLE_AGENTS:
        f = ROOT / "config" / "agents" / f"{a}.md"
        if not f.exists() or not DO._holds(a, "write_archive"):
            continue
        text = f.read_text().lower()
        if any(re.search(rf"\b{re.escape(w)}\b", text) for w in words):
            out.append(a)
    return out


def _fields_from_rows(rows: list) -> dict:
    keys: dict[str, str] = {}
    for r in rows:
        if isinstance(r, dict):
            for k, v in r.items():
                if k in _BOOKKEEPING:
                    continue
                keys.setdefault(k, "number" if isinstance(v, (int, float)) else "text")
    return keys


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--persona", required=True)
    ap.add_argument("--apply", action="store_true", help="write; otherwise dry-run")
    args = ap.parse_args()

    persona = resolve_persona(args.persona)
    user = persona_data_dir(persona)
    if not user.exists():
        # Almost always: this is the Mac. A user's data tree exists only on the VM.
        print(f"No data folder at {user} — run this on the VM, where {persona}'s data lives.")
        return 1

    with persona_scope(persona):
        from tools import data_objects as DO
        from tools.diarist import _archive_dir

        registered = {o["id"] for o in DO._stored()}
        template_ids = {t["id"] for t in DO._templates()}
        archive = _archive_dir()
        files = sorted(archive.glob("*.json")) if archive.exists() else []
        plan: list[tuple[str, dict]] = []

        for store, name, desc in NATIVE_STORES:
            if store not in registered:
                plan.append(("store", {"store": store, "name": name, "description": desc}))

        reserved = [f.name for f in files if f.stem.startswith("_")]
        for f in files:
            cat = f.stem
            if cat.startswith("_") or cat in registered:
                continue
            try:
                rows = json.loads(f.read_text())
            except (OSError, json.JSONDecodeError) as exc:
                print(f"  ! {f.name} unreadable ({exc}) — skipped")
                continue
            rows = rows if isinstance(rows, list) else []
            if cat == CARDIAC["object_id"]:
                plan.append(("cardiac", {**CARDIAC, "fields": _fields_from_rows(rows),
                                         "_rows": len(rows)}))
            elif cat in template_ids:
                # Already listed from its template; existing rows read as things with no
                # occurrences. Registered on its first write — nothing to do here.
                print(f"  = {cat}: a template — its {len(rows)} existing rows read as they are")
            elif DO.close_match(cat.replace("_", " ")) is not None:
                near = DO.close_match(cat.replace("_", " "))
                print(f"  ! {cat}: {len(rows)} rows, but the name is close to the existing "
                      f"'{near['name']}' — NOT registered, so its rows are not silently "
                      f"folded in. Decide with Mike: merge, or register it under its own name.")
            else:
                plan.append(("category", {"object_id": cat,
                                          "name": cat.replace("_", " ").capitalize(),
                                          "fields": _fields_from_rows(rows),
                                          "relevant_agents": _naming_agents(cat, DO),
                                          "_rows": len(rows)}))

        if CARDIAC["object_id"] not in registered and not any(k == "cardiac" for k, _ in plan):
            print(f"  ! no {CARDIAC['object_id']}.json in {archive} — the cardiac log was not "
                  f"found, so it is NOT registered. Check the archive before going on.")

        print(f"\n{'APPLY' if args.apply else 'DRY RUN'} — {persona}: "
              f"{len(plan)} to register, {len(registered)} already registered\n")
        for kind, spec in plan:
            if kind == "store":
                print(f"  + store     {spec['store']:<14} {spec['name']}")
            elif kind == "cardiac":
                print(f"  + cardiac   {spec['object_id']:<14} occurrence, class health, "
                      f"{spec['_rows']} rows, fields {sorted(spec['fields'])}")
            else:
                print(f"  + category  {spec['object_id']:<14} thing (today's merge), "
                      f"{spec['_rows']} rows, fields {sorted(spec['fields'])}, "
                      f"kept readable by {spec['relevant_agents'] or 'standing readers only'}")
        if reserved:
            print(f"\n  ! files starting with '_' in archive/ — not categories, now unreachable "
                  f"by any tool: {reserved}")

        stale_origin = [o["id"] for o in DO._stored()
                        if o.get("store") != "archive" and o.get("id") == o.get("store")
                        and o.get("origin") == "asked"]
        if stale_origin:
            print(f"\n  ~ stores marked as asked-for, to re-mark existing: {stale_origin}")

        if not args.apply:
            print("\nNothing written. Re-run with --apply to register.")
            return 0

        if stale_origin:
            print(f"  re-marked existing: {DO.repair_store_origins()}")

        for kind, spec in plan:
            spec = {k: v for k, v in spec.items() if not k.startswith("_")}
            if kind == "store":
                out = DO.register_store(spec["store"], name=spec["name"],
                                        description=spec["description"])
            elif kind == "cardiac":
                out = DO.create_object(spec.pop("name"), origin="existing", tag=False,
                                       persona=persona, **spec)
            else:
                out = DO.create_object(spec.pop("name"), identity="thing", origin="existing",
                                       tag=False, persona=persona, **spec)
                if out.get("created"):
                    tagged = DO.tag_relevance(out["object"]["id"], persona)
                    # tag_relevance returns [] on any failure — say so, never stay quiet.
                    print(f"  {'':<18} readers now {tagged}" if tagged else
                          f"  {'':<18} ! tagging returned nothing — readers stay "
                          f"{spec['relevant_agents'] or 'the standing readers only'}")
            label = (out.get("object") or out.get("match") or {}).get("id", "?")
            print(f"  {'registered' if out.get('created') else 'skipped (exists)':<18} {label}"
                  + (f"  — {out['error']}" if out.get("error") else ""))
        print(f"\nRegistry: {DO._registry_path()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
