#!/usr/bin/env python3
"""
Check config/modules/knowledge_domains.yaml against the two things it couples.

The map is the only place subjects and the agent roster meet, which is what keeps a roster
change from becoming a user-data migration. That also makes it the only place they can drift
apart silently: rename an agent in routing*.yaml and the map still names the old one, so the
knowledge for that subject reaches nobody and no error is raised anywhere.

Three checks:
  1. Every key is a domain in tools/wisdom.py DOMAINS (plus the overflow queue).
  2. Every domain has a key — a missing one is a subject whose entries reach no specialist.
  3. Every named agent exists in BOTH routing files.

Stdlib plus PyYAML. Zero model tokens. Exit 1 on any finding.
"""

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tools.wisdom import DOMAINS, OVERFLOW_DOMAIN  # noqa: E402

MAP_PATH = ROOT / "config" / "modules" / "knowledge_domains.yaml"
ROUTING = [
    ROOT / "config" / "modules" / "routing.yaml",
    ROOT / "config" / "modules" / "routing_cloud.yaml",
]


def main() -> int:
    if not MAP_PATH.exists():
        print(f"MISSING: {MAP_PATH}")
        return 1

    mapping = (yaml.safe_load(MAP_PATH.read_text()) or {}).get("domains") or {}
    findings: list[str] = []

    valid_domains = set(DOMAINS) | {OVERFLOW_DOMAIN}
    for domain in mapping:
        if domain not in valid_domains:
            findings.append(f"unknown domain '{domain}' — not in tools/wisdom.py DOMAINS")
    for domain in valid_domains:
        if domain not in mapping:
            findings.append(
                f"domain '{domain}' has no entry — its knowledge reaches no specialist"
            )

    for routing_path in ROUTING:
        if not routing_path.exists():
            continue
        agents = set((yaml.safe_load(routing_path.read_text()) or {}).get("agents") or {})
        for domain, named in mapping.items():
            for agent in named or []:
                if agent not in agents:
                    findings.append(
                        f"'{domain}' names agent '{agent}', absent from {routing_path.name}"
                    )

    for finding in findings:
        print(f"  ! {finding}")
    print(f"\nknowledge_domains.yaml: {len(findings)} finding(s).")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
