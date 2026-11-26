"""
tests/test_ranking_review_aliases.py — the weekly review reads contacts as the public-fact
guard does (82c490e): each alias on its own, only a capitalised alias counts as a name, and
there is no organisation skip (the CRM's relationship_type has no such value).

    python3 tests/test_ranking_review_aliases.py
"""
from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tools.crm as CRM  # noqa: E402
import tools.ranking_review as RR  # noqa: E402

_TMP = Path(tempfile.mkdtemp())
_CONTACTS = _TMP / "contacts.json"
CRM._crm_path = lambda: _CONTACTS

checks = []


def check(name, ok):
    checks.append((name, bool(ok)))


def hits(text: str) -> bool:
    names = RR._person_names(None)
    return any(p.search(text.lower()) for p in names)


_CONTACTS.write_text(json.dumps([
    {"first_name": "Grace", "last_name": "Hopper", "name": "Grace Hopper",
     "referred_to_as": ["Grace Brewster Hopper", "my wife", "Gracie"]},
    {"name": "School Office", "relationship_type": "friend"},
    "not a contact",
]))
check("a full-name alias in a list matches", hits("send Grace Brewster Hopper the form"))
check("a capitalised one-word alias matches", hits("call Gracie back"))
check("a relational alias is not a name", not hits("my wife needs a lift"))
check("an organisation-like name matches only itself", hits("email the School Office")
      and not hits("book the school trip, ask the office"))
check("unrelated ordinary text is not caught", not hits("renew the car insurance"))

_CONTACTS.write_text(json.dumps({"not": "a list"}))
check("a wrongly shaped store is unreadable (None, fail-closed)", RR._person_names(None) is None)
_CONTACTS.unlink()
check("no store is no names, not unreadable", RR._person_names(None) == [])
check("the dead organisation list is gone", not hasattr(RR, "_ORG_TYPES"))

passed = sum(ok for _, ok in checks)
for n, ok in checks:
    print(f"  {'PASS' if ok else 'FAIL'}  {n}")
print(f"\n{passed}/{len(checks)} checks pass")
sys.exit(0 if passed == len(checks) else 1)
