"""
tools/rule_audit.py — a daily sweep for rules stated in more than one place.

Runs as a `function:` scheduler job, so it costs **no model tokens at all** — it
is regex and set arithmetic over the config files, in the same class as
`ambient_refresh`.

Why a sweep is needed on top of the write-time check in `tools/persona.py`:
those two catch different failures, and the second one is the one that actually
bit.

  - The write-time check sees a *preference the tool records for the user*. It
    fires in the same second and stops the duplicate existing.
  - This sweep sees everything else — most importantly rules added by hand in a
    development session. On 2026-08-03 five of the user's preferences were
    generalised into `config/agents/synthesizer.md` while the originals stayed in
    `config/personas/mike.md`. Nothing wrote a preference that day, so no
    write-time check could have seen it. It took reading both files side by side.

Findings go into the quality-event stream as `RULE_CONFLICT`, which means they
travel the path already built for this: `scripts/sync_dev_backlog.py` pulls them
into `DEV_BACKLOG.md`, and the count appears when a development session opens.
An audit whose output nobody reads is not a control.

Each finding is written once. A daily job that re-reported the same overlap every
morning would train the reader to ignore it — the exact failure the "raise a
thing once" rule exists to prevent, and it would be poor form to build a tool
that commits it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from core.persona import persona_data_dir, persona_config_dir, resolve_persona
from core.rule_classes import (
    CLASSES,
    Rule,
    contradicts,
    read_bullets,
    shared_rules,
    similarity,
)
from tools.logger import write_quality_event

# Above this, two rules in different files are near-verbatim restatements and
# worth reporting regardless of class. Tuned against the real 2026-08-03 set:
# lower and the agent files report their own internal cross-references.
NEAR_DUPLICATE = 0.40

# A class collision alone is not enough to report — a persona file is *allowed*
# to hold a personal variant of a universal rule. Some lexical agreement on top
# of the shared class is what separates "restating it" from "refining it".
COLLISION_FLOOR = 0.12


def _seen_path(persona: str) -> Path:
    return persona_data_dir(persona) / "logs" / ".rule_audit_seen"


def _load_seen(persona: str) -> set[str]:
    p = _seen_path(persona)
    if not p.exists():
        return set()
    return {ln.strip() for ln in p.read_text().splitlines() if ln.strip()}


def _record_seen(persona: str, keys: set[str]) -> None:
    p = _seen_path(persona)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as f:
        for k in sorted(keys):
            f.write(k + "\n")
    p.chmod(0o600)


def _key(f: dict) -> str:
    """Stable id for a finding.

    Keyed on the preference text, not on the file and line: agent files get
    edited and every line below the edit shifts, which would re-report the whole
    file as new the next morning. Keyed on the preference alone rather than the
    pair, because the candidate list reshuffles whenever a shared rule is
    reworded — and a reshuffled candidate list for a preference already reported
    is not new information.
    """
    return hashlib.sha256(f["a"].text.strip().encode()).hexdigest()[:16]


def _persona_rules(persona: str) -> list[Rule]:
    return read_bullets(
        persona_config_dir(persona).parent / f"{persona}.md",
        "persona",
        section="Interaction Preferences",
    )


def find_conflicts(persona: str) -> list[dict]:
    """Personal preferences that restate a rule already applying to everyone.

    Deliberately only cross-layer. An earlier version also compared shared rules
    against each other and was unusable: the specialist agent files carry
    intentional parallel boilerplate — "Mandatory pass. Runs every session",
    "Voice mode:", "The system clock in your context is authoritative" — which
    scores as near-identical because it *is* near-identical, on purpose. Those
    findings drowned the real ones, and a daily report that is mostly noise gets
    ignored by week two. Shared-layer duplication is a development-session
    concern; `scripts/check_rule_overlap.py --all-pairs` is where to look for it.

    At most one finding per preference — the best partner. If a preference
    genuinely restates three agent rules, fixing it against the closest one
    resolves all three, and reporting it three times only obscures that.
    """
    personal = _persona_rules(persona)
    shared = shared_rules(persona)
    findings: list[dict] = []

    for p in personal:
        # A preference whose class the persona layer *owns* is exactly where it
        # belongs — `follow_up_style` is personal by definition, so flagging it
        # against a scheduler prompt that happens to say "follow-up" is noise
        # the reader has to dismiss every time the ledger is cleared.
        if all(CLASSES.get(c, {}).get("home") == "persona" for c in p.classes) and p.classes:
            continue

        cands = []
        for s in shared:
            shared_class = p.classes & s.classes
            score = similarity(p, s)
            # A shared class with some lexical agreement, or wording so close
            # that the class list not covering it is beside the point.
            if not ((shared_class and score >= COLLISION_FLOOR) or score >= NEAR_DUPLICATE):
                continue
            cands.append((score, sorted(shared_class)[0] if shared_class else "", s))
        if not cands:
            continue

        # Several candidates, not one. Lexical scores this low (0.15-0.30 is
        # typical for a real match) cannot reliably pick the *right* partner —
        # tested against the 2026-08-03 set, the top-scoring partner was wrong
        # three times in five. The class is the trustworthy signal; the score
        # only orders candidates within it. So the finding names the suspect
        # preference, which it gets right, and offers candidates for a human to
        # choose between rather than asserting a partner that is often wrong.
        cands.sort(key=lambda c: -c[0])
        top = cands[:3]
        findings.append({
            "kind": ("contradiction"
                     if any(c[1] and contradicts(p, c[2]) for c in top)
                     else "duplicate"),
            "score": top[0][0],
            "a": p,
            "cands": top,
            "n": len(cands),
            "cls": next((c[1] for c in top if c[1]), ""),
        })

    findings.sort(key=lambda f: (f["kind"] != "contradiction", -f["score"]))
    return findings


def _detail(f: dict) -> str:
    a = f["a"]
    lead = ("This preference may contradict a rule that already applies — one "
            "negates, the other does not, and whichever layer loads last wins."
            if f["kind"] == "contradiction" else
            "This preference may already be covered by a rule that applies to "
            "everyone.")
    cls = ""
    if f["cls"] in CLASSES:
        c = CLASSES[f["cls"]]
        cls = (f"\n  Class: {f['cls']} — {c['desc']}. A universal rule of this "
               f"class belongs in the {c['home']} layer.")

    lines = [f"{lead}{cls}",
             f"  Preference: {a.source}:{a.line} — {a.text[:220]}",
             f"  Candidate rule(s) it may restate:"]
    for score, cname, s in f["cands"]:
        tag = f" [{cname}]" if cname else " [wording only]"
        lines.append(f"    ({score:.2f}){tag} {s.source}:{s.line} — {s.text[:180]}")
    if f["n"] > len(f["cands"]):
        lines.append(f"    … and {f['n'] - len(f['cands'])} more")
    lines.append(
        "  Candidates are ranked by wording overlap, which is weak at this "
        "scale — the flagged preference is the reliable part, the partner is a "
        "starting point. If the preference says nothing the shared rule does "
        "not, delete it. If it is a genuine personal refinement, keep it and "
        "reword it so the difference is all it states.")
    return "\n".join(lines)


def audit_rules() -> str:
    """Scheduler entry point. Takes no arguments; persona comes from the scope.

    Never raises on a config problem: this runs unattended in a daemon, and a
    tidiness check that crash-loops the scheduler would be far more expensive
    than the duplication it is looking for.
    """
    try:
        persona = resolve_persona()
        findings = find_conflicts(persona)
    except Exception as e:
        return f"rule audit skipped: {e}"

    seen = _load_seen(persona)
    fresh = [f for f in findings if _key(f) not in seen]

    for f in fresh:
        write_quality_event(
            event_type="RULE_CONFLICT",
            source_agent="rule_audit",
            detail=_detail(f),
            session_id="rule_audit",
        )
    if fresh:
        _record_seen(persona, {_key(f) for f in fresh})

    return (f"{len(findings)} overlap(s) present, {len(fresh)} newly reported"
            if findings else "no rule overlaps")


if __name__ == "__main__":  # manual run: python3 -m tools.rule_audit
    import sys
    from core.persona import persona_scope

    who = sys.argv[1] if len(sys.argv) > 1 else "mike"
    with persona_scope(who):
        found = find_conflicts(who)
        for f in found:
            print(_detail(f) + "\n")
        print(f"{len(found)} finding(s).")
