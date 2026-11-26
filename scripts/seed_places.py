#!/usr/bin/env python3
"""
M3 for data-objects phase 3 (archive/plans/data_objects_phase3_build_plan_2026-11-25.md § 2
ruling 7): bring one user's places up to the phase 3 shape, on the VM, run by Mike.

Three steps, each shown before anything is written:

  1. The registry entry. `places` was registered from the existing archive category before it
     had a template (origin `existing`, identity `thing`); it takes the template's identity,
     fields and description, keeping its readers. Policy (writer: code, guarded fields) already
     comes from the template at read time — this makes the stored copy say the same.
  2. The rows already on file. Each row with no position is looked up by name (its free-text
     `location`, if any, is the area). You accept or skip each one; a skipped row stays as it
     is — no position, never matched, never deleted.
  3. Named places from a file you pass in (--add FILE). **Real names never go into the repo**
     (CLAUDE.md § Data Privacy): the file lives outside it, e.g. /tmp, and is deleted after.
     JSON, a list of {"name", "area"?, "kind"?, "verdict"?: go_to|try|avoid,
     "occasion"?: {"kind", "what"?, "near"?}, "notes"?}.

RUN IT ON THE VM, AFTER the code deploy. `data/personas/**` is VM-owned.

    .venv/bin/python scripts/seed_places.py --persona mike                    # dry run: reads only
    .venv/bin/python scripts/seed_places.py --persona mike --add /tmp/p.json  # dry run, with adds
    .venv/bin/python scripts/seed_places.py --persona mike --add /tmp/p.json --apply

COST. The dry run writes nothing and calls nothing. --apply makes one Places Text Search per
row looked up and per added place (~16 for `mike`), priced at M3 — and asks before each.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_scope, resolve_persona  # noqa: E402


def _ask(prompt: str) -> bool:
    try:
        return input(f"{prompt} [y/N] ").strip().lower() in ("y", "yes")
    except EOFError:
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--persona", required=True)
    ap.add_argument("--add", help="JSON file of places to add (kept OUTSIDE the repo)")
    ap.add_argument("--apply", action="store_true", help="write (asks before each lookup)")
    args = ap.parse_args()
    persona = resolve_persona(args.persona)

    from tools import data_objects as DO
    from tools import saved_places as SP

    adds = []
    if args.add:
        p = Path(args.add).resolve()
        if ROOT in p.parents:
            print(f"Refused: {p} is inside the repo — real place names never go there.")
            return 2
        adds = [a for a in json.loads(p.read_text()) if isinstance(a, dict) and a.get("name")]

    with persona_scope(persona):
        tmpl = next((t for t in DO._templates() if t["id"] == "places"), None)
        if tmpl is None:
            print("No places template — is the phase 3 code deployed?")
            return 1
        current = DO.get("places")
        print(f"== 1. Registry entry for {persona}")
        print(f"   now:   identity={current.get('identity')}  origin={current.get('origin')}  "
              f"readers={current.get('relevant_agents')}")
        readers = sorted(set(current.get("relevant_agents") or [])
                         | set(tmpl.get("relevant_agents") or []))
        print(f"   after: identity={tmpl['identity']}  fields={list(tmpl['fields'])}  "
              f"readers={readers}")
        if args.apply:
            with DO._locked():
                objs, s = DO._materialise("places", DO._stored())
                s.update(identity=tmpl["identity"], description=tmpl["description"],
                         relevant_agents=readers,
                         fields={**tmpl["fields"], **(s.get("fields") or {})},
                         aliases=sorted(set(s.get("aliases") or []) | set(tmpl["aliases"])))
                DO._save(objs)
            print("   written.")

        rows = [r for r in SP._rows() if SP._live(r, include_hidden=True)]
        todo = [r for r in rows if "lat" not in r]
        print(f"\n== 2. Rows on file: {len(rows)}, without a position: {len(todo)}")
        for i, r in enumerate(todo, 1):
            area = str(r.get("location") or "")
            print(f"   {i:2}. {r['name']}" + (f"  (area: {area})" if area else ""))
        if args.apply:
            for r in todo:
                area = str(r.get("location") or "")
                if not _ask(f"   look up “{r['name']}”{' near ' + area if area else ''}?"):
                    continue
                res = SP.locate(r["name"], area, persona=persona)
                if res.get("error"):
                    print(f"      not found: {res['error']}")
                    continue
                tag = "AMBIGUOUS — saved unconfirmed" if res["ambiguous"] else "confirmed"
                print(f"      → {res.get('address')}  [{tag}]")
                if not _ask("      keep this position?"):
                    _undo_position(SP, DO, r["name"])
                    print("      position removed; the row is as it was.")

        print(f"\n== 3. Places to add: {len(adds)}")
        for a in adds:
            print(f"   - {a['name']}  verdict={a.get('verdict', '-')}  "
                  f"occasion={a.get('occasion', '-')}")
        if args.apply:
            for a in adds:
                if not _ask(f"   save and look up “{a['name']}”?"):
                    continue
                out = SP.save(a, source="said", persona=persona)
                res = SP.locate(out["name"], str(a.get("area") or ""), persona=persona)
                print(f"      {out['status']}; "
                      + (f"→ {res.get('address')}" if not res.get("error") else res["error"]))
    if not args.apply:
        print("\nDry run — nothing written, no lookup made. Add --apply to write.")
    elif args.add:
        print(f"\nDone. Delete {args.add} now — it holds real names.")
    return 0


def _undo_position(SP, DO, name: str) -> None:
    """Take back a position just stored, keeping it in `previous` (nothing is deleted)."""
    from datetime import datetime
    with DO._locked():
        rows = SP._rows()
        for r in rows:
            if isinstance(r, dict) and r.get("name") == name and "lat" in r:
                r.setdefault("previous", []).append(
                    {"value": {k: r.pop(k) for k in ("lat", "lon", "radius_m", "address")
                               if k in r},
                     "changed_at": datetime.now().isoformat(timespec="seconds"),
                     "reason": "rejected at M3"})
        path = DO._archive_file("places")
        path.write_text(json.dumps(rows, indent=2))
        path.chmod(0o600)


if __name__ == "__main__":
    sys.exit(main())
