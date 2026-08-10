#!/usr/bin/env python3
"""
PostToolUse hook — run the agent-tool guard when an agent file or a routing grant changes.

Why a hook and not a line in CLAUDE.md: the `get_weather` split survived a week
(2026-08-03 to 08-10) because the grant and the documentation drifted apart in the same
commit and nothing re-checked them. A written rule depends on whoever is editing
remembering to run a check at the moment they are absorbed in something else.
CLAUDE.md's own principle applies — enforce at the tool layer, not in prompts.

**Scoped to what actually changed.** An agent-file edit reports on that agent. A routing
edit reports only on the agents whose `allowed_tools` moved in the diff — not the fleet.
An unscoped sweep emits 37 findings on every grant edit, which is the volume that trains
a reader to skip the output; that is the same failure `rule_audit.py` was written to
avoid, and the reason this project keeps the guard off the backlog sync entirely.

Reports only classes 1 and 2 — the two a person can act on. Planned tools and large
grants are inventory; `python3 scripts/check_agent_tools.py` shows those on demand.

Never blocks and never fails the tool call: exits 0 no matter what.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PY = ROOT / ".venv" / "bin" / "python3"
GUARD = ROOT / "scripts" / "check_agent_tools.py"

# An agent key in a routing file: two-space indent, name, colon, nothing else.
_AGENT_KEY_RE = re.compile(r'^  ([a-z][a-z0-9_]*):\s*$')
# Hunk header: @@ -old,+new @@ — we want the new-side start line.
_HUNK_RE = re.compile(r'^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@')


def _changed_agents(path: Path) -> list[str]:
    """Agents whose block contains a changed line, from the uncommitted diff."""
    try:
        diff = subprocess.run(["git", "diff", "-U0", "--", str(path)],
                              cwd=ROOT, capture_output=True, text=True, timeout=10).stdout
        lines = path.read_text().splitlines()
    except Exception:
        return []

    changed_lines: set[int] = set()
    for line in diff.splitlines():
        m = _HUNK_RE.match(line)
        if m:
            start = int(m.group(1))
            count = int(m.group(2) or 1)
            changed_lines.update(range(start, start + count))

    agents: list[str] = []
    for n in sorted(changed_lines):
        # Walk up to the nearest agent key above the changed line.
        for i in range(min(n, len(lines)) - 1, -1, -1):
            m = _AGENT_KEY_RE.match(lines[i])
            if m:
                if m.group(1) not in agents:
                    agents.append(m.group(1))
                break
    return agents


def _findings_for(agent: str | None) -> list[str]:
    """Class 1 and 2 lines from the guard, for one agent or all."""
    cmd = [str(PY if PY.exists() else sys.executable), str(GUARD), "--routing", "cloud", "--quiet"]
    if agent:
        cmd += ["--agent", agent]
    try:
        out = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=60).stdout
    except Exception:
        return []

    keep, cls = [], 0
    for line in out.splitlines():
        if line.startswith("1. NAMED AS LIVE"):
            cls = 1
        elif line.startswith("2. NAMED BUT NOT GRANTED"):
            cls = 2
        elif line.startswith(("0. PLANNED", "3. GRANTED")):
            cls = 0
        elif cls and line.startswith(("  ✗", "  !")):
            keep.append(line.rstrip())
    return keep


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0
    ti = payload.get("tool_input") or {}
    tr = payload.get("tool_response") or {}
    file_path = ti.get("file_path") or (tr.get("filePath") if isinstance(tr, dict) else None)
    if not file_path:
        return 0

    p = Path(file_path)
    parts = p.as_posix()

    if "/config/agents/" in parts and p.suffix == ".md":
        agents, scope = [p.stem], p.stem
    elif "/config/modules/routing" in parts and p.suffix in (".yaml", ".yml"):
        agents = _changed_agents(p)
        if not agents:
            return 0  # nothing in the diff resolved to an agent block
        scope = ", ".join(agents)
    else:
        return 0

    findings: list[str] = []
    for a in agents:
        findings += _findings_for(a)
    # Same finding can appear once per routing file; keep first occurrence only.
    seen, unique = set(), []
    for f in findings:
        if f not in seen:
            seen.add(f)
            unique.append(f)
    if not unique:
        return 0

    msg = (f"check_agent_tools — {len(unique)} finding(s) after editing {scope}\n"
           + "\n".join(unique)
           + "\nA tool named in an agent file is a specification: build it, grant it, or "
             "move it under a deferred heading. Deleting the line is the last resort "
             "(CLAUDE.md § A tool named in an agent file is a specification).")
    print(json.dumps({
        "systemMessage": msg,
        "hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": msg},
    }))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        raise SystemExit(0)
