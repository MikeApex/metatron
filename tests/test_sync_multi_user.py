"""
tests/test_sync_multi_user.py — the backlog sync reads every live account, and keeps each
user's entries apart (archive/plans/iva_onboarding_prereqs_plan_2026-11-23.md § A3, review
findings L4 and L9).

What a reader of DEV_BACKLOG.md would see go wrong without each check:
  · a second user's problems never arrive (the account filter matched no status);
  · her event folds into Mike's entry, so the ×N mixes two people and the line names
    whoever fired last;
  · two users' events with one timestamp — the second is taken as already seen.

Usage:
    python3 tests/test_sync_multi_user.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import sync_dev_backlog as sync                            # noqa: E402
from tests.support.runner import Suite                     # noqa: E402

suite = Suite("backlog sync, more than one user")
check = suite.check

DENIAL = "TOOL_DENIED"


def _event(detail: str, persona: str | None = None, ts: str = "2026-11-23T10:00:00",
           kind: str = "USER_CORRECTION") -> dict:
    e = {"event_type": kind, "detail": detail, "timestamp": ts}
    if persona:
        e["_persona"] = persona
    return e


@check("only `active` accounts are read — approval sets `active`; there is no `approved`")
def _():
    real = sync._get_json
    try:
        sync._get_json = lambda server, route, params=None: {"accounts": [
            {"username": "iva", "status": "active"},
            {"username": "waiting", "status": "pending"},
            {"username": "gone", "status": "disabled"},
        ]}
        assert sync.account_personas("x") == ["iva"]
        sync._get_json = lambda server, route, params=None: None
        assert sync.account_personas("x") == [], "an unreachable store must degrade to []"
    finally:
        sync._get_json = real


@check("her entry is tagged with her name; Mike's carries no tag")
def _():
    assert "[from iva]" in sync.render(_event("the reminder was wrong", "iva"))
    assert "[from" not in sync.render(_event("the reminder was wrong"))


@check("her event never folds into Mike's identical entry, in either section")
def _():
    block = "\n" + sync.render(_event("the reminder for the dentist was wrong")) + "\n"
    for machine in (False, True):
        merged, appended, count = sync.merge(
            block, _event("the reminder for the dentist was wrong", "iva"), machine)
        assert appended and count == 1, (machine, merged)
        assert merged.count("- ") == 2, merged


@check("her repeat still folds into her own entry")
def _():
    block = "\n" + sync.render(_event("the reminder for the dentist was wrong", "iva")) + "\n"
    merged, appended, count = sync.merge(
        block, _event("the reminder for the dentist was wrong", "iva",
                      ts="2026-11-23T11:00:00"), False)
    assert not appended and count == 2, merged
    assert "[from iva]" in merged


@check("a denial signature is per user, and her repeat denial still merges with hers")
def _():
    detail = "`logistics` attempted `write_agent_config`, which is not in its allowed tools"
    assert sync.DENIAL_RE.search(detail), "the denial shape changed — update this sample"
    mine = _event(detail, kind=DENIAL)
    hers = _event(detail, "iva", kind=DENIAL)
    assert sync.signature(mine) != sync.signature(hers)
    block = "\n" + sync.render(hers) + "\n"
    _, appended, count = sync.merge(block, _event(detail, "iva", ts="2026-11-23T12:00:00",
                                                  kind=DENIAL), True)
    assert not appended and count == 2


@check("one timestamp, two users: both are new; Mike's ledger key is unchanged")
def _():
    mine, hers = _event("a", ts="2026-11-23T09:00:00"), _event("b", "iva", ts="2026-11-23T09:00:00")
    assert sync._seen_key(mine) == "2026-11-23T09:00:00", "Mike's existing ledger would be invalidated"
    assert sync._seen_key(hers) != sync._seen_key(mine)


@check("a detail that itself opens with a bracket is not read as a persona tag")
def _():
    line = sync.render(_event("[already applied by the tool] saved a rule"))
    assert sync._line_persona(line) == sync.DEFAULT_PERSONA


@check("a full run reads mike and every active account, tags hers, and --persona reads one")
def _():
    import tempfile
    tmp = Path(tempfile.mkdtemp(prefix="sync-multi-"))
    saved = {k: getattr(sync, k) for k in ("BACKLOG", "SEEN", "fetch_events", "account_personas",
                                            "_get_json", "vm_status", "fold_fragments")}
    read = []

    def fake_fetch(server, persona):
        read.append(persona)
        return [_event(f"the reminder for {persona} was wrong", ts="2026-11-23T08:00:00")]
    try:
        sync.BACKLOG = tmp / "DEV_BACKLOG.md"
        sync.SEEN = tmp / "seen"
        sync.BACKLOG.write_text("# B\n## Inbox\n\n---\n## Machine log\n\n---\n")
        sync.SEEN.write_text("")
        sync.fetch_events = fake_fetch
        sync.account_personas = lambda server: ["iva"]
        sync._get_json = lambda *a, **k: None
        sync.vm_status = lambda: "RUNNING"
        sync.fold_fragments = lambda text: (text, [])
        argv = sys.argv
        sys.argv = ["sync", "--quiet"]
        try:
            sync.main()
        finally:
            sys.argv = argv
        text = sync.BACKLOG.read_text()
        assert read == ["mike", "iva"], read
        assert "[from iva] the reminder for iva" in text, text
        assert "the reminder for mike" in text and "[from mike]" not in text, text
        seen = sync.SEEN.read_text().split()
        assert "2026-11-23T08:00:00" in seen and "iva:2026-11-23T08:00:00" in seen, seen

        read.clear()
        sys.argv = ["sync", "--quiet", "--persona", "iva"]
        try:
            sync.main()
        finally:
            sys.argv = argv
        assert read == ["iva"], read
    finally:
        for k, v in saved.items():
            setattr(sync, k, v)


sys.exit(suite.report())
