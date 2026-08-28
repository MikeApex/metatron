"""
tools/persona.py — Write durable user preferences to the persona config file.

Used by the Synthesizer when the user states a preference about how they want to
interact. Writes to config/personas/{persona}.md so the preference persists across
all future sessions (not just the context tracker window).

Sensitive-tier, local-only.

## Two guards, added 2026-08-28 (`[DB-0815-11]`)

A preference written here rides in every prompt from then on, and nothing but the
user reading their own file ever surfaces it again. Three times the tool applied one
to itself with nobody asked — and the third, on 2026-08-18, is the one that could be
checked end to end: it wrote a real Interaction Preference into `mike.md` that the
next morning's rule audit scored **0.88 against `config/templates/scheduler.yaml:21`**.
The instruction was already in force for every persona. The self-applied copy said
nothing the shared one did not, and now there were two homes for one rule.

Mike's ruling of 2026-08-28 answers the two separable questions that raised:

  1. **May the tool self-apply a preference?** For the time being, not without asking.
     An *inferred* preference is proposed and written only when the user approves it,
     through the same fingerprinted `consume()` path `write_config` uses. A preference
     the user **stated** is ungated — that is them speaking, not the tool guessing.
     The gate is a **switch, not a hard rule** (`proactive.persona.inferred_write_auto_accept`
     in `preferences.yaml`): once the inference earns trust it can be turned off and
     inference permitted again.
  2. **Should a preference be checked against existing rules before it is written?**
     Yes, and on **both** paths — stated and inferred alike. `_existing_home()` runs
     before anything is written and before any approval is raised, and refuses when the
     preference restates a rule already in force somewhere better suited to holding it.

**This reverses the old "warn, never block" reasoning, deliberately.** That rule was
right about what it was protecting — refusing a write to keep a file tidy loses what the
user said — but a refusal that *names the existing home* loses nothing: the instruction
is already recorded, and the reply says where. The weaker signals (a shared rule class
without near-verbatim wording) still only warn, unchanged, because there the second copy
may be a genuine personal refinement.
"""

import os
import re
from pathlib import Path

from core.persona import persona_md

_ROOT = Path(__file__).parent.parent

# Sources the model may declare. Anything else — including nothing at all — is read as
# `inferred`, which is the gated side. A missing or unrecognised value must never be the
# cheap way past the gate.
_STATED = "user_stated"
_INFERRED = "inferred"


def _persona_path() -> Path:
    return persona_md()


def _inferred_write_auto_accept(persona: str | None = None) -> bool:
    """
    Has the user turned the approval gate on inferred preferences off? Default False.

    Same shape and same reasoning as `tools/crm.py::_merge_auto_accept`: the gate is the
    default, and switching it off is the user's deliberate act and never a model's —
    this reads a config file, and no tool writes that file.

    Per-persona file first, then the shared one: the VM owns live persona config, so a
    persona can carry its own answer without this needing to know about it. Any failure
    to read leaves the gate ON — a missing or unreadable file must not mean "allow".
    """
    import yaml
    from core.persona import persona_config_dir

    candidates = []
    try:
        candidates.append(persona_config_dir(persona) / "preferences.yaml")
    except Exception:  # noqa: BLE001
        # Identity resolution is fail-closed and raises with no persona in scope. Correct
        # there, and not a reason to take a session down here; the shared file answers.
        pass
    candidates.append(_ROOT / "config" / "preferences.yaml")
    for path in candidates:
        try:
            if not path.exists():
                continue
            with open(path) as f:
                cfg = yaml.safe_load(f) or {}
        except (OSError, ValueError, yaml.YAMLError):
            continue
        persona_cfg = ((cfg.get("proactive") or {}).get("persona") or {})
        if "inferred_write_auto_accept" in persona_cfg:
            return bool(persona_cfg["inferred_write_auto_accept"])
    return False


def _new_lines(previous: str, content: str) -> list[str]:
    """The lines this call would add that are not already somewhere in the file.

    Bullets when there are bullets, since that is what the schema asks for and what a
    preference looks like; otherwise ordinary prose lines, so a section written as a
    paragraph is not silently exempt from both checks below.

    A section rewrite carries the existing preferences forward verbatim (the schema
    requires it), and those are already in `previous` — so they drop out here and only
    the genuinely new material is examined. Re-approving a proposal therefore sees the
    same list it did when the proposal was raised.
    """
    def strip(line: str) -> str:
        return line.strip().lstrip("-* ").strip()

    existing = {strip(ln) for ln in previous.splitlines() if strip(ln)}
    bullets = [strip(ln) for ln in content.splitlines() if ln.strip().startswith(("-", "*"))]
    if bullets:
        return [b for b in bullets if b and b not in existing]
    return [strip(ln) for ln in content.splitlines()
            if strip(ln) and not ln.strip().startswith("#") and strip(ln) not in existing]


def _existing_home(added: list[str]) -> str:
    """Is one of these preferences already in force somewhere better suited to it?

    Returns a refusal message naming that home, or "" to proceed. Checked against every
    rule that applies beyond this one persona file — the agent files, the persona's own
    `scheduler.yaml`, and the `config/templates/scheduler.yaml` every persona inherits —
    which is `shared_rules()`, the same corpus `tools/rule_audit.py` sweeps each morning.

    The bar is `rule_audit.NEAR_DUPLICATE`, imported rather than restated so the two
    checks cannot drift apart. It is deliberately the *high* bar of the two the audit
    uses: at that score the wording is a restatement, and the audit's own caveat about
    weak scores picking the wrong partner does not apply. A shared rule *class* with
    lower lexical agreement is not refused — a persona layer is allowed to hold a
    personal refinement of a universal rule — and still reaches `_redundancy_warning()`.

    The 2026-08-18 line scores 0.86 here against `config/templates/scheduler.yaml:21`.

    Never raises: this runs on a write path, and a check that cannot run must not take
    the write down with it. Failing open leaves exactly the behaviour that existed
    before this function did.
    """
    if not added:
        return ""
    try:
        from core.rule_classes import Rule, shared_rules, similarity
        # One home for the threshold. tools/rule_audit.py tuned it against the real
        # 2026-08-03 duplicate set; a second copy of the number here would drift.
        from tools.rule_audit import NEAR_DUPLICATE

        persona = None
        try:
            from core.persona import resolve_persona
            persona = resolve_persona()
        except Exception:  # noqa: BLE001
            pass

        shared = shared_rules(persona)
        for text in added:
            candidate = Rule(text, "<new>", "persona")
            best = None
            for existing in shared:
                score = similarity(candidate, existing)
                if best is None or score > best[0]:
                    best = (score, existing)
            if best is None or best[0] < NEAR_DUPLICATE:
                continue

            rule = best[1]
            return (
                f'"{text[:120]}" is already in force. It is held at '
                f'{rule.source}:{rule.line} — "{rule.text[:180]}" — which applies '
                "without being copied into this user's file. Writing it here would give "
                "one instruction two homes, and the copies drift apart the first time "
                "either is edited. Nothing has been written. Tell the user the tool "
                "already has this. If it plainly is not producing the behaviour they "
                "want, that is a change to the rule where it lives — record an "
                "INSTRUCTION_CHANGE_REQUEST rather than leaving a second copy."
            )
        return ""
    except Exception:  # noqa: BLE001
        return ""


def write_persona(section: str, content: str, source: str = _INFERRED,
                  confirm_token: str = "") -> str | dict:
    """
    Add or replace a named section in the user's persona config file.

    If the section already exists, its content is replaced. If it does not
    exist, it is appended. Use for durable preferences that should persist
    across all sessions — not for session-level context (use write_context_tracker
    for that).

    Two guards run before anything is written; see the module docstring for the
    incidents that bought them.

      * **Redundancy, on every call.** If the preference restates a rule already in
        force at a shared layer, the write is refused and the reply names where that
        rule lives. Checked before the approval gate as well as before the write, so
        the user is never asked to approve something that is going to be refused.
      * **Approval, on inferred preferences only.** With the gate on (the default),
        an inferred preference returns PENDING_CONFIRMATION and writes nothing; the
        user approving it in the app is what writes it. A stated preference writes
        straight through.

    Args:
        section: Section heading, e.g. "Interaction Preferences".
        content: Full content for the section as a markdown-formatted string.
                 Use bullet points for lists of preferences.
        source: "user_stated" if the user asked for this in their own words this turn,
                "inferred" if the tool worked it out. Anything else, including omitting
                it, is treated as inferred — the gated side.
        confirm_token: Supplied by the server when carrying out an approved write.
                 Not for the model to set.

    Returns:
        Confirmation string once written, an "Error: not written." string when refused,
        or a PENDING_CONFIRMATION dict.
    """
    from tools.confirm import consume, request

    path = _persona_path()
    if not path.exists():
        raise FileNotFoundError(f"Persona file not found: {path}")

    text = path.read_text()
    added = _new_lines(text, content)

    # Both sources, and before the gate: a pending card the user can only usefully
    # decline is noise in the approval queue (same ordering as merge_contacts).
    already = _existing_home(added)
    if already:
        return f"Error: not written. {already}"

    if source != _STATED and not _inferred_write_auto_accept():
        args = {"section": section, "content": content, "source": source}
        ok, reason = consume(confirm_token or None, "write_persona", args)
        if not ok:
            if confirm_token:
                return f"Error: not written. {reason}"
            preview = content if len(content) <= 400 else content[:400] + " […]"
            return request(
                "write_persona", args,
                description=(
                    f"Record this under '{section}' as a lasting preference, kept and "
                    f"applied from now on:\n\n{preview}\n\n"
                    "You did not ask for this — it was worked out from the conversation."
                ),
            )

    # Build the replacement block
    new_block = f"## {section}\n\n{content.strip()}\n"

    # Look for an existing section with this heading
    pattern = re.compile(
        rf'^## {re.escape(section)}\n.*?(?=^## |\Z)',
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(text):
        updated = pattern.sub(new_block, text)
    else:
        updated = text.rstrip('\n') + f"\n\n{new_block}"

    path.write_text(updated)
    os.chmod(path, 0o600)

    confirmation = f"Persona updated: '{section}' written to {path.name}"

    warning = _redundancy_warning(text, content)
    return confirmation + warning if warning else confirmation


def _redundancy_warning(previous: str, content: str) -> str:
    """Flag newly-added preferences that share a rule CLASS with one already in force.

    The weaker of the two redundancy signals, and the one that still only warns. A
    shared class without near-verbatim wording is exactly the case where the persona
    layer may legitimately be refining a universal rule rather than restating it, so
    refusing here would throw away real personal detail. The near-verbatim case — where
    there is nothing to lose, because the instruction demonstrably already exists — is
    refused before the write by `_existing_home()`.

    The write has already happened by the time this runs. It costs no model call and no
    extra turn, just regex over the config files, so it is safe on a write path.

    Catches only what this tool writes. Rules added by hand in a development
    session are invisible here, which is how the 2026-08-03 duplicates arose;
    `tools/rule_audit.py` sweeps for those.
    """
    try:
        from core.rule_classes import check_new_rule

        added = _new_lines(previous, content)

        notes = []
        for rule in added:
            for cls, other, _score in check_new_rule(rule, limit=1):
                notes.append(f'"{rule[:70]}" overlaps an existing {cls} rule')
                break
        if not notes:
            return ""

        return (
            "\n\nNOTE — this may already be covered: " + "; ".join(notes) + ". "
            "If the user is restating something you were already told, the "
            "instruction you hold is not working; that is a change to record, "
            "not a preference to store twice. Tell them you already have it and "
            "that it plainly isn't showing, and record an "
            "INSTRUCTION_CHANGE_REQUEST rather than leaving two copies."
        )
    except Exception:
        # A tidiness check must never break a write that already succeeded.
        return ""


# ---------------------------------------------------------------------------
# Tool schema
# ---------------------------------------------------------------------------

WRITE_PERSONA_SCHEMA = {
    "name": "write_persona",
    "description": (
        "Write a durable user preference to the persona config file. "
        "Use this when the user states how they want to interact "
        "or how they want responses shaped — preferences that should persist "
        "indefinitely, not just for this session. "
        "Pass the section name (e.g. 'Interaction Preferences') and the full "
        "updated content for that section as markdown bullet points. "
        "Existing section content is replaced; new sections are appended. "
        "Always set 'source'. A preference you worked out rather than being told "
        "may return PENDING_CONFIRMATION and write nothing — show the user what it "
        "would record and leave it with them. Approving it in the app is what writes "
        "it; do not call this tool a second time, and never say it is written before "
        "that. A preference that merely restates a rule the tool already follows is "
        "refused, and the reply names where that rule already lives."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "section": {
                "type": "string",
                "description": (
                    "Section heading in the persona file. Use existing headings "
                    "when updating (e.g. 'Interaction Preferences'). "
                    "Use a new heading only for genuinely new categories."
                ),
            },
            "content": {
                "type": "string",
                "description": (
                    "Full content for the section as a markdown-formatted string. "
                    "Write bullet points for lists of preferences. "
                    "This replaces the entire section, so include all existing "
                    "preferences when updating — do not write partial updates."
                ),
            },
            "source": {
                "type": "string",
                "enum": ["user_stated", "inferred"],
                "description": (
                    "Where this preference came from. "
                    "'user_stated' — the user asked for it in their own words in this "
                    "conversation ('stop asking me twice', 'keep answers short'). Their "
                    "instruction, quoted or closely paraphrased. "
                    "'inferred' — you worked it out: from how they reacted, from a "
                    "pattern across sessions, from something they implied but did not "
                    "ask for, or from your own judgement that it would suit them. "
                    "If you cannot point to the turn where they said it, it is inferred. "
                    "Being unsure is itself inferred; an inferred preference is asked "
                    "about rather than refused, so there is no cost to saying so."
                ),
            },
            "confirm_token": {
                "type": "string",
                "description": "Not for you to set. The app supplies this when it carries out an action the user has approved; leave it out of every call you make.",
            },
        },
        "required": ["section", "content", "source"],
    },
}
