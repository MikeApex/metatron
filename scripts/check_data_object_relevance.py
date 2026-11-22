#!/usr/bin/env python3
"""
The reverse check (R26): when an agent is added, which of the users' existing logs concern it?

archive/plans/data_objects_phase2_build_plan_2026-11-22.md § 3.8. A log is tagged with the agents
it matters to when it is created (tools/data_objects.tag_relevance). An agent added later would
never be told about the logs that already exist — this runs the same tagger, once per log, with
only that agent's one-line remit, across each user's registry.

ON THE VM (persona data is VM-owned), by Mike or at his instruction:

    .venv/bin/python scripts/check_data_object_relevance.py --agent recreation_hobbies --all
    .venv/bin/python scripts/check_data_object_relevance.py --agent recreation_hobbies --all --apply

Dry run by default: it prints what it would add and writes nothing. Each log costs one bulk-tier
`data_object_tagger` call (≈ $0.0005), dry run included — the dry run is the judgement. The
tagger sees a log's name, description and field names, never an entry. `--apply` adds the agent
to `relevant_agents`; nothing is removed. Private, archived and merged logs, and registered
stores themselves, are skipped.

The agent must already be in `TAGGABLE_AGENTS` and have an italic remit line in its agent file
(docs/CONVENTIONS.md § Adding a new module, step 5).
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.persona import persona_scope  # noqa: E402


def check(agent: str, personas: list[str], apply: bool = False) -> list[str]:
    from tools import data_objects as DO
    remit = DO.agent_remits().get(agent)
    if not remit:
        return [f"{agent}: no remit — add it to TAGGABLE_AGENTS and give its agent file an "
                f"italic one-line remit under the title"]
    out = []
    for p in personas:
        with persona_scope(p):
            for o in DO._stored():
                if (o.get("status") != "active" or o.get("merged_into")
                        or (o.get("store") != "archive" and o["id"] == o.get("store"))):
                    continue
                if agent in (o.get("relevant_agents") or []):
                    continue
                payload = json.dumps({"object": {"name": o["name"],
                                                 "description": o.get("description") or "",
                                                 "fields": sorted(o.get("fields") or {})},
                                      "agents": {agent: remit}}, ensure_ascii=False)
                try:
                    raw = DO._call_tagger(payload, p)
                    m = re.search(r"\[.*?\]", raw or "", re.S)
                    chosen = json.loads(m.group(0)) if m else []
                except Exception as exc:  # noqa: BLE001
                    out.append(f"  {p}: {o['name']} — tagger failed ({exc})")
                    continue
                if agent not in chosen:
                    continue
                if apply:
                    with DO._locked():
                        objs, s = DO._materialise(o["id"], DO._stored())
                        s["relevant_agents"] = sorted(set(s["relevant_agents"]) | {agent})
                        DO._save(objs)
                out.append(f"  {p}: {o['name']} — {'added' if apply else 'would add'} {agent}")
    return out or [f"  no existing log concerns {agent}"]


def main() -> int:
    ap = argparse.ArgumentParser(prog="check_data_object_relevance")
    ap.add_argument("--agent", required=True)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--persona")
    g.add_argument("--all", action="store_true")
    ap.add_argument("--apply", action="store_true")
    a = ap.parse_args()
    if a.all:
        d = ROOT / "data" / "personas"
        personas = sorted(x.name for x in d.iterdir() if x.is_dir() and
                          (x / "data_objects.json").exists())
    else:
        personas = [a.persona]
    print("\n".join(check(a.agent, personas, a.apply)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
