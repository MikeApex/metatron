#!/usr/bin/env python3
"""
scripts/vertex_cache_admin.py — list and delete Vertex context caches.

Two jobs, both from the 2026-08-20 cache-cost work:

  --list        the interim check. Pass condition: never more than one cache per
                model, every entry carries an owning displayName, and no
                expireTime lies more than the TTL ahead. (Last-use time is not
                exposed by the list API; expireTime under the sliding scheme is
                the verifiable proxy.)

  --delete-all  the ONE-TIME rollout action. Caches created before the sliding
                TTL landed carry no displayName, so no running process will ever
                claim them and the in-process sweep leaves them alone by design.
                They bill by the wall-clock hour until their midnight expiry.
                Run this once, at the deploy that ships the TTL.

Location comes from GOOGLE_CLOUD_LOCATION (this deployment sets `global`);
nothing here hardcodes a region, because a cache listed in the wrong location
reads as "no caches" rather than as an error.

Run on the VM:
    cd ~/multi-model-mcp && source .venv/bin/activate
    python3 scripts/vertex_cache_admin.py --list
    python3 scripts/vertex_cache_admin.py --delete-all
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--list", action="store_true", help="show every cache in the project")
    g.add_argument("--delete-all", action="store_true", help="delete every cache (one-time rollout action)")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation prompt on --delete-all")
    args = ap.parse_args()

    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

    import core.orchestrator as orch

    project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if not project:
        print("GOOGLE_CLOUD_PROJECT is not set — nothing to do (not on Vertex).")
        return 1

    client = orch._get_vertex_native_client()
    if client is None:
        print("No native Vertex client available.")
        return 1

    location = orch._vertex_location()
    entries = list(client.caches.list())
    now = datetime.datetime.now(datetime.timezone.utc)

    print(f"project={project} location={location} caches={len(entries)}")
    print(f"this process would claim: {orch._vertex_cache_owner()}")
    print()
    for e in entries:
        expire = getattr(e, "expire_time", None)
        remaining = f"{(expire - now).total_seconds() / 60:6.1f} min" if expire else "     ? min"
        owner = getattr(e, "display_name", None) or "(unowned — pre-TTL cache)"
        model = getattr(e, "model", "?")
        tokens = getattr(getattr(e, "usage_metadata", None), "total_token_count", "?")
        print(f"  {e.name}\n      expires in {remaining}  tokens={tokens}  model={model}\n      owner={owner}")

    if args.list:
        stale = [e for e in entries if not getattr(e, "display_name", None)]
        if stale:
            print(f"\n{len(stale)} unowned cache(s) — these predate the sliding TTL and nothing will "
                  f"reap them early. Run --delete-all once.")
        return 0

    if not entries:
        print("Nothing to delete.")
        return 0

    if not args.yes:
        answer = input(f"\nDelete all {len(entries)} cache(s)? They rebuild on the next call. [y/N] ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Aborted.")
            return 1

    deleted = 0
    for e in entries:
        try:
            client.caches.delete(name=e.name)
            deleted += 1
            print(f"  deleted {e.name}")
        except Exception as exc:
            print(f"  FAILED  {e.name}: {exc}")
    print(f"\n{deleted}/{len(entries)} deleted.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
