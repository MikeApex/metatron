#!/usr/bin/env python3
"""
scripts/vm_read.py — the Mac client for the VM's read doors.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 6, ruling 11.

THE LIBRARIAN'S ONLY PERMITTED BASH FORM. `build-librarian.md` (phase C) grants
`Bash(python3 scripts/vm_read.py *)` and nothing else, so this file is the whole
of what that subagent can run against the VM. It reads; it cannot write. There is
no write path from the Mac to the VM and none is added here.

WHAT IT RETIRES. Nothing existed for this before — the standing rule against new
harness machinery (`.claude/rules/deploy.md`) asks for the build that will retire
it instead: this is Build's read path, and it goes when Build's Librarian does.
It is deliberately not a general-purpose VM client. `sync_dev_backlog.py` mints
its own token the same way and reads `/monitor/file`; the two do not share code
because this one has a different caller (a subagent) and a different failure
contract (loud, so the model can correct itself).

    python3 scripts/vm_read.py --persona mike presence log
    python3 scripts/vm_read.py --persona mike read read_wisdom '{"domains":["home"]}'
    python3 scripts/vm_read.py --list

`presence` takes a SOURCE ID, not arguments — the VM runs the fixed, code-chosen
call from `core/build/manifest.py` and returns a state, a count and a window with
no content. `read` takes a tool name from the door's allowlist and a JSON object
of arguments, validated on the VM against a per-tool schema.

`--list` is answered LOCALLY, from the tracked allowlist and source table in this
same checkout — not by a call. The VM runs the same code, so the two agree by
construction, and asking the VM what it would accept is a round trip that buys
nothing.

FAILURE IS LOUD AND STRUCTURED, which is the point. A refusal is printed as JSON
on stdout and exits 1. A 400 carries the schema the arguments broke, so the model
that wrote them can fix them without a second question; a 403 says whether the
name was outbound or merely outside the read set; a 501 says the tool is not
built yet rather than not allowed. Swallowing any of those into "the read failed"
would put the Librarian back to guessing, which is what the doors exist to stop.

Standard library only, like `sync_dev_backlog.py` — `core.auth` is stdlib-only by
design so that a token can be minted by whatever interpreter the caller happens
to have.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# HTTPS and the Tailscale hostname rather than the raw IP: the server runs behind
# a Tailscale-issued cert, so the IP form fails hostname verification. Matches
# sync_dev_backlog.py and the orchestrator CLI's own --server default.
DEFAULT_SERVER = "https://metatron-vm.tail0acc5d.ts.net:8001"
DEFAULT_PERSONA = "mike"

# A research read can load an embedding model on first use, so this is generous
# where sync_dev_backlog.py's 3s is not. It is still bounded: a Librarian hanging
# on a door is a session Mike is sitting in front of.
TIMEOUT_SECONDS = 120


def _auth_header() -> dict:
    """
    Mint a short-lived bearer for the monitor API.

    The Mac holds the same password the VM does (both read `.env`) and the
    signing key derives from it, so the token is minted locally rather than by
    calling /auth/login. Unlike sync_dev_backlog.py this does NOT fail silently:
    a missing password here means every read fails 401, and a Librarian told
    "no data" when the truth is "no credential" would record a wrong inventory
    row that the whole plan is then built on.
    """
    sys.path.insert(0, str(ROOT))
    from core.auth import bearer_header
    return bearer_header(ttl_seconds=600)


def _call(server: str, params: dict) -> tuple[int, dict]:
    url = f"{server.rstrip('/')}/monitor/tool?{urllib.parse.urlencode(params)}"
    req = urllib.request.Request(url, headers=_auth_header())
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            payload = json.loads(body)
        except ValueError:
            payload = {"detail": {"error": body.strip() or exc.reason}}
        return exc.code, payload
    except (urllib.error.URLError, OSError) as exc:
        return 0, {"detail": {
            "error": f"the VM did not answer: {exc}",
            "reason": "unreachable",
            "server": server,
        }}


def _emit(status: int, payload: dict) -> int:
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    if status == 200:
        return 0
    print(f"\n[vm_read] HTTP {status or 'no response'} — the read did not happen.",
          file=sys.stderr)
    return 1


def _list_local() -> int:
    """What this door will accept, read from the tracked code in this checkout."""
    sys.path.insert(0, str(ROOT))
    from core.build import doors, manifest
    print(json.dumps({
        "read_set": sorted(doors.READ_SET),
        "pending_build": sorted(doors.pending_tools()),
        "refused_outbound": sorted(doors.live_feed_tools()),
        "caps": {
            "window_days": doors.MAX_WINDOW_DAYS,
            "k": doors.MAX_K,
            "max_entries": doors.MAX_ENTRIES,
        },
        "presence_sources": manifest.source_ids(),
        "schemas": {n: doors.public_schema(n) for n in sorted(doors.READ_SET)},
    }, indent=2, ensure_ascii=False))
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Read the VM's persona data through the Build read doors.")
    ap.add_argument("--persona", default=DEFAULT_PERSONA,
                    help="the persona the door is bound to (default: mike)")
    ap.add_argument("--server", default=DEFAULT_SERVER)
    ap.add_argument("--list", action="store_true",
                    help="print the allowlist, caps and schemas, without calling")
    ap.add_argument("mode", nargs="?", choices=["presence", "read"])
    ap.add_argument("target", nargs="?",
                    help="a manifest source id for presence, a tool name for read")
    ap.add_argument("args", nargs="?", default="{}",
                    help="JSON object of arguments, for read")
    opts = ap.parse_args(argv)

    if opts.list:
        return _list_local()

    if not opts.mode or not opts.target:
        ap.print_usage(sys.stderr)
        print("error: give a mode (presence|read) and a target, or --list",
              file=sys.stderr)
        return 2

    if opts.mode == "presence":
        params = {"persona": opts.persona, "presence": opts.target}
    else:
        try:
            parsed = json.loads(opts.args)
        except ValueError as exc:
            print(f"error: args is not valid JSON: {exc}", file=sys.stderr)
            return 2
        if not isinstance(parsed, dict):
            print("error: args must be a JSON object", file=sys.stderr)
            return 2
        params = {"persona": opts.persona, "name": opts.target,
                  "args": json.dumps(parsed)}

    return _emit(*_call(opts.server, params))


if __name__ == "__main__":
    sys.exit(main())
