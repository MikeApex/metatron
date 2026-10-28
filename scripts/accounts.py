#!/usr/bin/env python3
"""
scripts/accounts.py — Mike's decisions on account requests. Run ON THE VM.

Plan: archive/plans/multi_user_accounts_plan_2026-10-26.md § 4.4.

    .venv/bin/python scripts/accounts.py list
    .venv/bin/python scripts/accounts.py approve iva
    .venv/bin/python scripts/accounts.py reject <u> | disable <u> | enable <u>
    .venv/bin/python scripts/accounts.py reset-password <u>
    .venv/bin/python scripts/accounts.py seed-consent mike --scopes correspondence_read,tone_profile \\
        --evidence "Mike's rulings 2026-08-26, 2026-08-28"

Claude Code runs it over `gcloud compute ssh … --tunnel-through-iap`, the path deploy.sh
already uses. **Account changes go over SSH, never HTTP**, so the server has no endpoint
that can approve, disable or reset anyone — fewer things to protect the day it is
reachable from outside.

**On the VM, because the VM owns live persona config** (.claude/rules/personas.md): the
new persona is created where it will live, never on the Mac.

**Every provisioning write is create-only** — `approve` can be re-run to finish a step that
failed, and it will never overwrite a file that exists (verify N1). In particular an
existing `interview/state.json` is never reset, so a re-run cannot restart an interview
that has begun. A `disabled` account is re-admitted with `enable`, which re-runs the same
create-only provisioning — nothing that exists is touched, anything missing is finished.

Set METATRON_SYSTEMCTL to replace the `sudo systemctl` prefix (tests use `true`).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core import accounts, consent  # noqa: E402
from core.persona import persona_data_dir  # noqa: E402

UNIT = "metatron-scheduler@{}"


def _say(step: str, outcome: str) -> None:
    print(f"  {outcome:<9} {step}", flush=True)


def _systemctl(*args: str) -> bool:
    prefix = shlex.split(os.environ.get("METATRON_SYSTEMCTL", "sudo systemctl"))
    result = subprocess.run(prefix + list(args), capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FAILED    systemctl {' '.join(args)}: {result.stderr.strip()}", flush=True)
        return False
    return True


def _create_only(path: Path, text: str, step: str) -> None:
    if path.exists():
        _say(step, "exists")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    os.chmod(path, 0o600)
    _say(step, "created")


def _identity_text(username: str, display: str) -> str:
    # Same shape new_persona.sh writes, with the name she asked to be called by.
    return (f"# User: {display}\n\n"
            f"Primary user of this system. Address them as \"{display}\" in every response.\n\n"
            "## Interaction Preferences\n\n"
            "<!-- Filled in as preferences emerge, or written by the write_persona tool\n"
            "     when the user states one explicitly. -->\n")


def _profile_text(entry: dict) -> str:
    """The template profile, with her name, city and timezone filled in."""
    text = (ROOT / "config" / "templates" / "profile.yaml").read_text()
    def fill(pattern: str, value: str) -> None:
        nonlocal text
        new, n = re.subn(pattern, lambda m: m.group(1) + json.dumps(value), text, count=1,
                         flags=re.M)
        if n != 1:
            raise RuntimeError(f"profile template no longer has a line matching {pattern!r}")
        text = new
    fill(r'^(name: )""$', entry.get("display_name") or entry["username"])
    if entry.get("city"):
        fill(r'^(  city: )""$', entry["city"])
    if entry.get("timezone"):
        fill(r'^(  timezone: )"UTC"$', entry["timezone"])
    return text


def provision(entry: dict) -> None:
    """Create everything an approved account needs, each step create-only."""
    u = entry["username"]
    cfg = ROOT / "config" / "personas"
    # Identity and profile BEFORE new_persona.sh, so it finds them and leaves them alone.
    _create_only(cfg / f"{u}.md", _identity_text(u, entry.get("display_name") or u),
                 f"config/personas/{u}.md")
    _create_only(cfg / u / "profile.yaml", _profile_text(entry),
                 f"config/personas/{u}/profile.yaml")
    result = subprocess.run([str(ROOT / "scripts" / "new_persona.sh"), u],
                            capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"new_persona.sh failed: {result.stderr.strip()}")
    _say("scripts/new_persona.sh (create-only)", "ran")
    # The one file the interview start and the scheduler's hold gate read (plan § 4.6, 4.7).
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    _create_only(persona_data_dir(u) / "interview" / "state.json",
                 json.dumps({"status": "not_started", "created_at": now}, indent=2) + "\n",
                 f"data/personas/{u}/interview/state.json")
    wrote = consent.seed_from_account(u, entry.get("consents") or {})
    _say(f"data/personas/{u}/consents.json (sign-up permission)",
         "created" if wrote else "exists")


def cmd_list(_args) -> int:
    rows = accounts.list_accounts()
    if not rows:
        print("No accounts.")
        return 0
    for r in rows:
        print(f"{r['username']:<20} {r['status']:<9} {r.get('display_name', ''):<24} "
              f"asked {r.get('created_at', '')}  decided {r.get('decided_at') or '-'}")
    return 0


def cmd_approve(args) -> int:
    entry = accounts.get(args.username)
    if entry is None:
        print(f"No account named {args.username!r}.", file=sys.stderr)
        return 1
    status = entry.get("status")
    if status not in ("pending", "active"):
        hint = " — use `enable` to re-admit it" if status == "disabled" else ""
        print(f"{args.username} is {status}; approve takes pending accounts only{hint}.",
              file=sys.stderr)
        return 1
    print(f"Approving {entry['username']} ({entry.get('display_name')}):")
    provision(entry)
    if status == "pending":
        accounts.update(entry["username"], status="active")
        _say("account → active", "done")
    else:
        _say("account already active (finishing a half-done approval)", "exists")
    if not args.no_scheduler:
        if _systemctl("enable", "--now", UNIT.format(entry["username"])):
            _say(f"systemctl enable --now {UNIT.format(entry['username'])}", "done")
        else:
            return 1
    print("Approved. She can sign in now.")
    return 0


def cmd_reject(args) -> int:
    entry = accounts.get(args.username)
    if entry is None or entry.get("status") != "pending":
        print("reject takes pending accounts only.", file=sys.stderr)
        return 1
    accounts.update(args.username, status="rejected", note=args.note or "")
    print(f"{args.username} rejected.")
    return 0


def cmd_disable(args) -> int:
    entry = accounts.get(args.username)
    if entry is None or entry.get("status") != "active":
        # A pending request is refused with `reject`. Disabling one would let `enable`
        # later activate an account that was never provisioned (review F2).
        print("disable takes active accounts only — use `reject` for a pending request.",
              file=sys.stderr)
        return 1
    accounts.update(args.username, status="disabled", note=args.note or "")
    _say("account → disabled (her tokens revoked)", "done")
    ok = args.no_scheduler or _systemctl("disable", "--now", UNIT.format(args.username))
    print(f"{args.username} disabled. Nothing of hers was deleted.")
    return 0 if ok else 1


def cmd_enable(args) -> int:
    entry = accounts.get(args.username)
    if entry is None or entry.get("status") != "disabled":
        print("enable takes disabled accounts only.", file=sys.stderr)
        return 1
    # Re-run provisioning rather than test one file (verify NEW-1): every step is
    # create-only, so on a complete persona it changes nothing — and on one an earlier
    # approve left half-built it finishes the job instead of re-admitting a broken account.
    print(f"Re-admitting {entry['username']}:")
    provision(entry)
    accounts.update(args.username, status="active")
    _say("account → active", "done")
    ok = args.no_scheduler or _systemctl("enable", "--now", UNIT.format(args.username))
    print(f"{args.username} re-admitted; her persona was not touched.")
    return 0 if ok else 1


def cmd_reset_password(args) -> int:
    if accounts.get(args.username) is None:
        print(f"No account named {args.username!r}.", file=sys.stderr)
        return 1
    temp = accounts.generate_temporary_password()
    accounts.update(args.username, password_hash=accounts.hash_password(temp))
    print(f"Temporary password for {args.username} (shown once, pass it on, then forget it):")
    print(f"  {temp}")
    return 0


def cmd_seed_consent(args) -> int:
    scopes = [s.strip() for s in args.scopes.split(",") if s.strip()]
    for scope in scopes:
        rec = consent.grant(scope, args.persona, text_version="ruling", evidence=args.evidence)
        _say(f"{args.persona}: {scope} (granted {rec['granted_at']})", "ok")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Account decisions — run on the VM.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list").set_defaults(fn=cmd_list)
    for name, fn in (("approve", cmd_approve), ("disable", cmd_disable), ("enable", cmd_enable)):
        p = sub.add_parser(name)
        p.add_argument("username")
        p.add_argument("--no-scheduler", action="store_true",
                       help="skip systemctl (tests, or a host without the unit)")
        if name == "disable":
            p.add_argument("--note", default="")
        p.set_defaults(fn=fn)
    p = sub.add_parser("reject")
    p.add_argument("username")
    p.add_argument("--note", default="")
    p.set_defaults(fn=cmd_reject)
    p = sub.add_parser("reset-password")
    p.add_argument("username")
    p.set_defaults(fn=cmd_reset_password)
    p = sub.add_parser("seed-consent")
    p.add_argument("persona")
    p.add_argument("--scopes", required=True)
    p.add_argument("--evidence", required=True)
    p.set_defaults(fn=cmd_seed_consent)
    args = ap.parse_args()
    try:
        return args.fn(args)
    except accounts.AccountError as e:
        print(str(e), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
