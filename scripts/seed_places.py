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
  3. Named places and corrections from a file you pass in (--add FILE). **Real names never go
     into the repo** (CLAUDE.md § Data Privacy): the file lives outside it, e.g. /tmp, and is
     deleted after. JSON, a list of {"name", "area"?, "kind"?, "verdict"?: go_to|try|avoid,
     "occasion"?: {"kind", "what"?, "near"?}, "notes"?}. An entry whose `name` — or `was`, when
     it renames — is a row already on file CORRECTS that row before its lookup (see `plan()`):
     also `skip`, `private`, `lookup_text` (sent instead of name + area), `visits` (dates) and
     `keep_old_name`. Each lookup also fetches opening hours (Enterprise SKU, Mike 2026-11-26).

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

# The Places key is in the VM's .env, which the server's unit loads and a hand-run script does
# not — the first M3 run (2026-11-26) wrote every correction and found no key for one lookup.
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


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
        steps, unmatched = plan(rows, adds)
        print(f"\n== 2. Places: {len(rows)} on file, {len(unmatched)} to add")
        for st in steps:
            print("   " + describe(st))
        for a in unmatched:
            print("   + " + describe({"row": None, "fix": a}))
        if args.apply:
            for st in steps + [{"row": None, "fix": a} for a in unmatched]:
                apply_step(st, persona, SP, DO)
    if not args.apply:
        print("\nDry run — nothing written, no lookup made. Add --apply to write.")
    elif args.add:
        print(f"\nDone. Delete {args.add} now — it holds real names.")
    return 0


# ---------------------------------------------------------------------------
# Corrections (M3, Mike 2026-11-26): an entry in the --add file whose `was` or `name` is a row
# already on file CORRECTS that row before its lookup — so it is never looked up with the old
# details first. Keys: name (the new name, with `was` the old), area, lookup_text (sent instead
# of name + area — a private home by its postcode alone), skip, private, kind, verdict,
# occasion, notes (added to what is there), visits (dates), keep_old_name (the old name stays
# an alias — false by default: a wrong name is not another name for the same place).
# ---------------------------------------------------------------------------

def _key(s: str) -> str:
    return " ".join(str(s or "").casefold().split())


def plan(rows: list[dict], adds: list[dict]) -> tuple[list[dict], list[dict]]:
    """Pure: pair each row on file with its correction, if any. Returns (steps for the rows
    on file, in file order; entries that correct no row — new places)."""
    by_key = {}
    for a in adds:
        # By its new name too, so a re-run — after the rename landed — still corrects the row.
        for k in (a.get("was"), a.get("name")):
            if k:
                by_key.setdefault(_key(k), a)
    used = set()
    steps = []
    for r in rows:
        fix = by_key.get(_key(r.get("name")))
        if fix is not None:
            used.add(id(fix))
        steps.append({"row": r, "fix": fix or {}})
    unmatched = [a for a in adds if id(a) not in used]
    return steps, unmatched


def describe(st: dict) -> str:
    r, f = st["row"] or {}, st["fix"] or {}
    name = f.get("name") or r.get("name")
    bits = []
    if r and f.get("name") and _key(f["name"]) != _key(r.get("name")):
        bits.append(f"renamed from “{r['name']}”"
                    + (" (old name kept as an alias)" if f.get("keep_old_name") else ""))
    if f.get("skip"):
        return f"{name}: SKIP — left exactly as it is"
    for k in ("kind", "verdict"):
        if f.get(k):
            bits.append(f"{k}={f[k]}")
    if f.get("occasion"):
        bits.append(f"occasion={f['occasion']}")
    if f.get("private"):
        bits.append("PRIVATE")
    if f.get("notes"):
        bits.append(f"note += “{f['notes']}”")
    if f.get("visits"):
        bits.append(f"visits {', '.join(f['visits'])}")
    if r and "lat" in r and not f.get("lookup_text") and not f.get("area"):
        bits.append("has a position — no lookup")
    else:
        q = f.get("lookup_text") or " ".join(x for x in (name, f.get("area")
                                                          or (r or {}).get("location")) if x)
        bits.append(f"lookup: “{q}”")
    return f"{name}: " + "; ".join(bits)


def apply_step(st: dict, persona: str, SP, DO) -> None:
    """One row (or new place): its corrections by code, then — after asking — its lookup."""
    r, f = st["row"], st["fix"] or {}
    if f.get("skip"):
        return
    name = (r or {}).get("name") or f["name"]
    if r is not None and f.get("name") and _key(f["name"]) != _key(name):
        _rename(SP, DO, name, f["name"], keep_alias=bool(f.get("keep_old_name")))
        name = f["name"]
    if r is None and f.get("was"):
        r = SP.find(f["name"], include_hidden=True)   # renamed on an earlier run
    entry = {"name": name, **{k: f[k] for k in ("kind", "verdict", "occasion") if f.get(k)}}
    if f.get("notes"):
        old = str((r or {}).get("notes") or "").strip()
        if f["notes"].casefold() in old.casefold():
            pass                                  # a re-run: the note is already there
        else:
            entry["notes"] = f"{old}; {f['notes']}" if old else f["notes"]
    out = SP.save(entry, source="said", persona=persona)
    name = out.get("name") or name
    if f.get("private"):
        SP.set_flag(name, "private", True, persona=persona)
    row = SP.find(name, include_hidden=True) or {}
    have = {(o.get("at"), o.get("kind")) for o in row.get("occurrences") or []}
    for d in f.get("visits") or []:
        if (d, "visit") not in have:
            SP._write({"name": name}, occurrence={"at": d, "kind": "visit"})
    if "lat" in row and not f.get("lookup_text") and not f.get("area"):
        print(f"   {name}: updated (already has a position)")
        return
    area = str(f.get("area") or (r or {}).get("location") or "")
    q = f.get("lookup_text") or f"{name} {area}".strip()
    if not _ask(f"   {name}: look up “{q}”?"):
        print("      no lookup — saved without a position")
        return
    res = SP.locate(name, area, persona=persona, text=f.get("lookup_text") or "",
                    relocate="lat" in row)
    if res.get("error"):
        print(f"      not found: {res['error']}")
        return
    tag = "AMBIGUOUS — saved unconfirmed" if res.get("ambiguous") else "one match"
    print(f"      → {res.get('address')}  [{tag}]")
    if not _ask("      keep this position?"):
        _undo_position(SP, DO, name)
        print("      position removed; the row is as it was.")


def _rename(SP, DO, old: str, new: str, keep_alias: bool) -> None:
    """A wrong or misspelt name, corrected on the row itself; the old one kept in `previous`
    (nothing is deleted) and, only when asked, as an alias."""
    from datetime import datetime
    with DO._locked():
        rows = SP._rows()
        for r in rows:
            if isinstance(r, dict) and r.get("name") == old and not r.get("removed"):
                r.setdefault("previous", []).append(
                    {"value": {"name": old}, "changed_at": datetime.now().isoformat(
                        timespec="seconds"), "reason": "renamed at M3"})
                r["name"] = new
                if keep_alias:
                    r["aliases"] = sorted(set(r.get("aliases") or []) | {old})
        DO._write_json(DO._archive_file("places"), rows)


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
        DO._write_json(DO._archive_file("places"), rows)


if __name__ == "__main__":
    sys.exit(main())
