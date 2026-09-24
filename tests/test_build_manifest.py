"""
tests/test_build_manifest.py — THE CONTENT-FREE RULE, which had no test.

core/build/manifest.py's docstring has cited this file twice since phase A —
*"still enforced by tests/test_build_manifest.py's grep of every profile value"*
— and the file did not exist. Phase D found the citation; phase C writes the
test, because the manifest is rendered into the Librarian's prompt and phase C
is what writes that prompt.

THE RULE: the manifest names SOURCES, CAPABILITIES and POLICIES. It never
carries a value read from any of them. Every description in it is a literal
written in manifest.py — none is drawn from persona data, and none is generated.

WHY IT STILL MATTERS AFTER RULING 5 MOVED IT. Under v3 the manifest was
Inquiry's input and this rule was the privacy boundary for the whole vertical.
It is not that any more — ruling 10 is. What it still is, is the thing that
makes the manifest safe to RENDER INTO A PROMPT, and what makes `_SOURCES` a
table of calls rather than a table of answers. A manifest that carried one log
line would put persona content into the one artifact that is handed to a model
before any door has been opened, and would do it invisibly, because the leak
would read as a helpful description.

THE METHOD. Build a persona whose every file is full of values that exist
nowhere else — a pub name, a street, a sum of money, a person's name — render
the manifest for that persona, and grep every one of those values against the
rendered text. Then the structural half, which is the one that cannot be fooled
by a fixture whose tokens happen not to collide: assert that every description
and every probe argument in the rendered manifest is a literal that appears in
manifest.py's own source.

Usage:
    python3 tests/test_build_manifest.py
"""

import json
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.build import manifest as M                   # noqa: E402
from core.build import policy as PL                    # noqa: E402
from tests.support.runner import Suite                 # noqa: E402

suite = Suite("build manifest")
check = suite.check

PERSONA = "fixture_manifest"
_TMP = Path(tempfile.mkdtemp(prefix="build-manifest-"))

# Values that exist NOWHERE ELSE in this repository. Each one is planted in a
# different file of the fixture persona, so a leak names the path it came from.
PLANTED: dict[str, str] = {
    "profile.name":       "Wendeline Okonkwo-Braithwaite",
    "profile.field":      "Zarrowmead",
    "goals.private_why":  "Quillfeather",
    "goals.shareable":    "Bryndlecote",
    "log.entry":          "hydrangeas on the Marchmont sill",
    "journal.entry":      "Thrummerby",
    "wisdom.fact":        "Vaskerelle",
    "context.thread":     "Pemberwick",
    "crm.contact":        "Isambard Quillon",
    "money":              "4317.62",
}


# ---------------------------------------------------------------------------
# The fixture persona — populated, not empty
# ---------------------------------------------------------------------------

def _write(rel: str, text: str) -> Path:
    path = _TMP / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def _build_fixture_tree() -> None:
    """A tree with the shape manifest.build() walks, and a real corpus in it."""
    # capabilities() reads config/agents/*.md stems.
    for name in ("coordinator", "logistics", "physical_health"):
        _write(f"config/agents/{name}.md", f"# {name}\n\nRole: a specialist.\n")

    # The persona's own config and data — every file carrying a planted value.
    _write(f"config/personas/{PERSONA}/profile.yaml",
           f"name: {PLANTED['profile.name']}\n"
           f"home_area: {PLANTED['profile.field']}\n"
           f"monthly_float: {PLANTED['money']}\n")
    _write(f"config/personas/{PERSONA}/goals.yaml",
           "quarterly:\n  - id: q1\n    title: finish the thing\n"
           f"    private_why: {PLANTED['goals.private_why']}\n"
           f"    shareable_what: {PLANTED['goals.shareable']}\n")
    _write(f"data/personas/{PERSONA}/logs/2026-09-20.json",
           json.dumps({"entries": [{"at": "09:10",
                                    "text": PLANTED["log.entry"]}]}))
    _write(f"data/personas/{PERSONA}/journal/2026-09-20.md",
           f"# 2026-09-20\n\n{PLANTED['journal.entry']} again today.\n")
    _write(f"data/personas/{PERSONA}/wisdom/home.json",
           json.dumps({"facts": [{"text": PLANTED["wisdom.fact"]}]}))
    _write(f"data/personas/{PERSONA}/context.json",
           json.dumps({"open_threads": [PLANTED["context.thread"]]}))
    _write(f"data/personas/{PERSONA}/crm/contacts.json",
           json.dumps([{"name": PLANTED["crm.contact"]}]))

    # A standing policy — Build's own authored record, not read from the corpus.
    # The four fields the manifest copies, plus fields it must not.
    _write(f"config/build/policies/{PERSONA}/weekend_correspondence.yaml",
           "id: weekend_correspondence\n"
           "domain: relationships\n"
           "applies_to: inbound mail arriving Saturday or Sunday\n"
           "retires_question_classes:\n  - authority\n"
           "default_on_silence: hold until Monday\n"
           f"standing_commitments:\n  - {PLANTED['crm.contact']} is answered same day\n"
           f"budget:\n  unit: replies\n  period: week\n  limit: {PLANTED['money']}\n"
           "authored_with_user: true\n"
           "review_date: 2027-01-01\n")


_build_fixture_tree()
M._ROOT = _TMP          # type: ignore[assignment]
PL._ROOT = _TMP         # type: ignore[assignment]

MANIFEST = M.build(PERSONA)
RENDERED = json.dumps(MANIFEST, indent=2, ensure_ascii=False)
SOURCE = (ROOT / "core" / "build" / "manifest.py").read_text(encoding="utf-8")


_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'’\-]{3,}|\d[\d.,]{3,}")


def _scalars(node) -> list[str]:
    """
    Every VALUE in a parsed document, and no key.

    Keys are structure — `name:`, `entries:`, `open_threads:` — and a manifest
    that contained the word "name" would not have leaked anything. What this
    rule is about is the right-hand side.
    """
    if isinstance(node, dict):
        return [v for child in node.values() for v in _scalars(child)]
    if isinstance(node, (list, tuple)):
        return [v for child in node for v in _scalars(child)]
    return [str(node)] if node is not None else []


def _corpus_values() -> list[tuple[str, str]]:
    """
    (path, value token) for every scalar in the persona's OWN files.

    `config/build/policies/` is deliberately excluded: a policy is a standing
    decision authored with the user at build time, and `applies_to` is inside
    the content-free rule by design. It gets its own check below, which is the
    stricter one — an exact field list rather than a grep.
    """
    import yaml

    out: list[tuple[str, str]] = []
    roots = [_TMP / "config" / "personas" / PERSONA,
             _TMP / "data" / "personas" / PERSONA]
    for root in roots:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            rel, text = str(path.relative_to(_TMP)), path.read_text(encoding="utf-8")
            if path.suffix == ".json":
                values = _scalars(json.loads(text))
            elif path.suffix in (".yaml", ".yml"):
                values = _scalars(yaml.safe_load(text))
            else:
                values = [text]          # prose: the whole file is content
            for value in values:
                for token in _TOKEN_RE.findall(value):
                    out.append((rel, token))
    return out


# ---------------------------------------------------------------------------
# The grep — the claim manifest.py's docstring makes
# ---------------------------------------------------------------------------

@check("NO VALUE from a populated persona appears in the rendered manifest")
def _():
    values = _corpus_values()
    assert values, "the fixture persona is empty — this check would pass vacuously"
    leaked = sorted({(rel, v) for rel, v in values if v in RENDERED})
    assert not leaked, (
        f"{len(leaked)} persona value(s) reached the manifest: {leaked[:6]}")


@check("every PLANTED value is absent — named one by one, so a leak says which")
def _():
    for where, value in PLANTED.items():
        assert value not in RENDERED, (
            f"{where} leaked into the manifest: {value!r}")


@check("the fixture really is readable — the grep is not passing on an empty tree")
def _():
    for where, value in PLANTED.items():
        planted_in = [p for p in _TMP.rglob("*")
                      if p.is_file() and value in p.read_text(encoding="utf-8")]
        assert planted_in, f"{where} was never written to the fixture tree"


# ---------------------------------------------------------------------------
# The structural half — a fixture cannot fool this one
# ---------------------------------------------------------------------------

@check("every source DESCRIPTION is a literal in manifest.py's own source")
def _():
    for source in MANIFEST["sources"]:
        description = source["description"]
        assert description in SOURCE, (
            f"source {source['id']!r} carries a description that is not written "
            f"in manifest.py: {description!r} — it was generated or read")


@check("every PROBE argument is a literal, or a date the code filled in")
def _():
    iso = re.compile(r"^\d{4}-\d{2}-\d{2}$")
    for source in MANIFEST["sources"]:
        for field, value in (source.get("probe") or {}).items():
            if isinstance(value, str) and (value == "" or iso.match(value)):
                continue        # _probe_dates fills these; a literal would go stale
            assert f'"{field}"' in SOURCE, f"{source['id']}.{field} is not declared"
            assert str(value) in SOURCE, (
                f"{source['id']}.probe[{field}] = {value!r} is not a literal in "
                "manifest.py — the model names a source and CODE chooses the call")


@check("a source carries only declared keys — no field arrives from anywhere else")
def _():
    allowed = {"id", "tool", "kind", "description", "probe", "probe_dates",
               "answers", "live", "available"}
    for source in MANIFEST["sources"]:
        extra = set(source) - allowed
        assert not extra, f"source {source['id']!r} carries undeclared keys: {extra}"


@check("capabilities are NAMES ONLY — a stem and its origin, nothing read from a file")
def _():
    names = {c["id"] for c in MANIFEST["capabilities"]}
    assert names == {"coordinator", "logistics", "physical_health"}, names
    for entry in MANIFEST["capabilities"]:
        assert set(entry) == {"id", "origin"}, entry
    assert "Role: a specialist." not in RENDERED, (
        "an agent file's CONTENT reached the manifest, not just its stem")


@check("a policy contributes EXACTLY four fields, and its other fields stay out")
def _():
    policies = MANIFEST["policies"]
    assert len(policies) == 1, policies
    assert set(policies[0]) == {"id", "domain", "applies_to",
                                "retires_question_classes"}, policies[0]
    assert policies[0]["applies_to"].startswith("inbound mail"), policies[0]
    for absent in ("hold until Monday", "authored_with_user", "2027-01-01"):
        assert absent not in RENDERED, (
            f"a policy field outside the four reached the manifest: {absent!r}")


@check("availability is DERIVED from the live handler set, never asserted")
def _():
    none_live = {s["id"] for s in M.sources(registered=set()) if s["available"]}
    assert not none_live, f"available: true with no handlers registered: {none_live}"
    two = {"read_wisdom", "read_goals"}
    got = {s["id"] for s in M.sources(registered=two) if s["available"]}
    assert got == {"wisdom", "goals"}, got


@check("the fingerprint covers ids and availability, NOT descriptions")
def _():
    before = M.fingerprint(MANIFEST)
    reworded = json.loads(RENDERED)
    reworded["sources"][0]["description"] = "a completely different sentence"
    assert M.fingerprint(reworded) == before, (
        "rewording a description changed the fingerprint — it would invalidate "
        "every question set for an edit that changes nothing answerable")
    reworded["sources"][0]["available"] = not reworded["sources"][0]["available"]
    assert M.fingerprint(reworded) != before, (
        "a tool landing or disappearing must invalidate a stale question set")


@check("the whole manifest is JSON-serialisable — it is rendered into a prompt")
def _():
    assert json.loads(RENDERED)["schema"] == "manifest/1"
    assert MANIFEST["fingerprint"] == M.fingerprint(MANIFEST)


if __name__ == "__main__":
    try:
        code = suite.report()
    finally:
        shutil.rmtree(_TMP, ignore_errors=True)
    sys.exit(code)
