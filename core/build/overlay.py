"""
core/build/overlay.py — the one loader behind the four load seams.

LANDING IS THE OVERLAY. Generated capabilities live in a VM-owned, gitignored,
backed-up directory, and the runtime reaches them through four seams:

  1  load_agent(name)          core/orchestrator.py   the instruction file
  2  _load_routing()           core/router.py         model and allowed_tools   [RED]
  3  the Coordinator's prompt  core/orchestrator.py   valid names + directory
  4  consequence / filter /    core/orchestrator.py   the three literals a new
     domain map                tools/wisdom.py        specialist has to join

EVERY SEAM IS A FALLBACK THAT RUNS ONLY WHEN THE TRACKED SOURCE HAS NO ANSWER.
Tracked wins, always and everywhere. Two consequences, both deliberate:

  · A tracked agent can never be SHADOWED by a generated one. The writer refuses
    a colliding name up front; this is the second line, and it holds even if a
    record reached the overlay some other way.
  · A broken overlay record can never take down a tracked agent. The seams FAIL
    OPEN to "no overlay", logged. The fail-CLOSED half of this design is the
    writer and verify.run_all(), which is the right place for it: refusing to
    write costs nothing, refusing to load costs a live session.

PersonaError → {} (plan Section 6, Opus finding 6), and this is a DECISION
rather than an oversight. resolve_persona() raises when nothing is bound
(core/persona.py:183-187); neither load_agent(name) nor _load_routing() takes a
persona, and resolve_model() is called today with none bound — see
tests/test_a4_complexity_threading.py:107-108. Letting the error propagate would
make a TRACKED agent's routing raise where it does not today, which is a change
to the Red-tier path, not an inheritance. No persona in scope → no overlay, and
every tracked behaviour exactly as before.

Plan: archive/plans/build_vertical_plan_2026-09-18.md Section 6.5
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SCHEMA = "overlay_capability/1"

# (persona, fingerprint) -> records. Keyed BY PERSONA, not global: a single
# server process serves more than one persona, and a global cache would let one
# persona's capability names appear in another's routing, domain map or prompt.
_cache: dict[str, tuple[Any, dict[str, dict]]] = {}


def overlay_root(persona: str | None = None) -> Path | None:
    """The overlay directory, or None when no persona is in scope."""
    from core.persona import PersonaError
    try:
        from core.build.jobs import build_dir
        return build_dir(persona) / "overlay"
    except PersonaError:
        return None
    except Exception as exc:
        logger.warning("[overlay] root unresolved: %s", exc)
        return None


def _fingerprint(directory: Path) -> Any:
    """
    (dir mtime, per-file name/mtime/size). A stat per record, which is a handful.

    The directory mtime alone would be enough for the writer, which lands files
    by os.replace() and so always bumps it — but "enough for the only writer we
    have today" is how a cache becomes wrong later, and the files are few.
    """
    try:
        entries = sorted(
            (p.name, p.stat().st_mtime, p.stat().st_size)
            for p in directory.glob("*.yaml")
        )
        return (directory.stat().st_mtime, tuple(entries))
    except OSError:
        return None


def load_overlay(persona: str | None = None) -> dict[str, dict]:
    """
    name -> capability record, for the persona in scope. `{}` when there is none.

    Never raises. A malformed record is logged once and SKIPPED — the other
    records, and every tracked agent, keep working.
    """
    root = overlay_root(persona)
    if root is None:
        return {}
    capabilities = root / "capabilities"
    if not capabilities.is_dir():
        return {}

    key = root.as_posix()
    fingerprint = _fingerprint(capabilities)
    cached = _cache.get(key)
    if cached and cached[0] == fingerprint and fingerprint is not None:
        return cached[1]

    records: dict[str, dict] = {}
    try:
        import yaml
    except Exception as exc:
        logger.warning("[overlay] yaml unavailable, overlay ignored: %s", exc)
        return {}

    for path in sorted(capabilities.glob("*.yaml")):
        try:
            parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
        except Exception as exc:
            logger.warning("[overlay] %s unreadable, skipped: %s", path.name, exc)
            continue
        problem = _structural_problem(parsed, path.stem)
        if problem:
            logger.warning("[overlay] %s skipped: %s", path.name, problem)
            continue
        records[str(parsed["name"])] = parsed

    _cache[key] = (fingerprint, records)
    return records


def _structural_problem(record: Any, stem: str) -> str:
    """
    A CHEAP load-time check, not the full validator.

    Full validation is schemas.validate_overlay_capability() and it ran at write
    time, where being thorough is free. Here it would run on a routing lookup,
    so what is checked is only what the seams actually dereference — and a
    record failing any of it would produce a half-wired specialist, which is the
    exact state this whole mechanism exists to prevent.
    """
    if not isinstance(record, dict):
        return "not a mapping"
    if record.get("schema") != SCHEMA:
        return f"schema is {record.get('schema')!r}, not {SCHEMA!r}"
    if record.get("name") != stem:
        return f"name {record.get('name')!r} does not match filename stem {stem!r}"
    if not str(record.get("display_name") or "").strip():
        return "no display_name"
    routing = record.get("routing")
    if not isinstance(routing, dict):
        return "no routing block"
    for side in ("local", "cloud"):
        if not isinstance(routing.get(side), dict):
            return f"no routing.{side} entry — parity is a property of the record"
    return ""


def _tracked_names() -> set[str]:
    """
    Tracked agent names, cheaply. Tracked ALWAYS wins, in every seam.

    Read from the agent-file stems rather than the routing files because the
    routing files are not the complete set — time_director has a file and no
    routing entry, and shadowing it would be exactly the half-wiring this guards.
    """
    from core.build.writer import _ROOT
    agents = _ROOT / "config" / "agents"
    try:
        return {p.stem for p in agents.glob("*.md")}
    except OSError:
        return set()


def records_for(persona: str | None = None) -> dict[str, dict]:
    """load_overlay() minus anything colliding with a tracked name."""
    tracked = _tracked_names()
    return {
        name: record for name, record in load_overlay(persona).items()
        if name not in tracked
    }


# ---------------------------------------------------------------------------
# What each seam asks for
# ---------------------------------------------------------------------------

def agent_file(name: str, persona: str | None = None) -> Path | None:
    """SEAM 1. The overlay instruction file for `name`, if there is one."""
    record = records_for(persona).get(name)
    if not record:
        return None
    root = overlay_root(persona)
    if root is None:
        return None
    path = root / str(record.get("agent_file") or f"agents/{name}.md")
    return path if path.exists() else None


def routing_entries(mode: str, persona: str | None = None) -> dict[str, dict]:
    """
    SEAM 2. name -> the routing entry for this deployment mode.

    `model_ref` is resolved by the caller, which holds the merged tracked config
    — resolving it here would need a second read of the routing file this is
    about to be merged into.
    """
    side = "cloud" if mode == "cloud" else "local"
    out: dict[str, dict] = {}
    for name, record in records_for(persona).items():
        entry = (record.get("routing") or {}).get(side)
        if isinstance(entry, dict):
            out[name] = dict(entry)
    return out


def _display_helpers():
    """
    (collapse, resolve) — THE SCHEMA'S OWN, imported rather than reimplemented.

    One definition behind the seam and the schema is the whole point: this seam
    exists to agree with the validator independently, and two copies of a
    normalisation rule agree only until one of them is edited. The fallbacks are
    for the case where core.build.schemas cannot be imported at all, where
    refusing to surface anything is the safe direction.
    """
    try:
        from core.build.schemas import _collapse, _resolve_display
        return _collapse, _resolve_display
    except Exception:
        def _collapse(text):       # noqa: D401
            return " ".join(str(text or "").split())

        def _resolve_display(display):
            return _collapse(display).lower().replace(" & ", "_") \
                                     .replace(" and ", "_").replace(" ", "_")
        return _collapse, _resolve_display


def _resolves_to_tracked(display: str) -> bool:
    """
    True when a display string already means a TRACKED agent.

    The schema refuses such a record, and this is the seam agreeing
    independently — the same relationship every other seam has with the writer.
    A display name is not an identifier: "Mental Wellbeing" resolves to
    `mental_wellbeing` through the Coordinator's own normaliser whether or not
    anything registered it, so checking the record's `name` never covered it.

    THE COLLAPSE IS LOAD-BEARING and was missing. This resolved the RAW string
    while the schema resolved a whitespace-collapsed one, so a hand-placed
    record displaying `Mental  Wellbeing` normalised to `mental__wellbeing`,
    missed the tracked set, and was surfaced into the closed valid-name list
    beside the real entry. The writer refuses that record and the sweep flags
    it, so reach was narrow — but it was the one place the seam and the schema
    had stopped agreeing, which is the property these two checks exist to hold.
    """
    collapse, resolve = _display_helpers()
    collapsed = collapse(display)
    if not collapsed:
        return True
    try:
        from core.orchestrator import _AGENT_NAME_MAP
        if collapsed.casefold() in _AGENT_NAME_MAP:
            return True
        return resolve(collapsed) in _tracked_names()
    except Exception:
        return False


def accepted_displays(persona: str | None = None) -> dict[str, str]:
    """
    name -> display_name, for records whose display is SAFE TO SURFACE.

    One filter behind both halves of seam 3, so the closed valid-name list and
    the name map can never disagree about which capabilities exist. Three
    reasons a display is dropped, each the seam agreeing independently with a
    rule the schema also enforces:

      · it resolves to a TRACKED agent      — it would capture that dispatch
      · another record already claimed it   — the closed list would carry the
                                              same string twice, and the map
                                              would keep one winner by sort order
      · it resolves to another record's NAME — it would capture that capability

    First wins, by sorted name, so the outcome is stable across restarts rather
    than dependent on directory order.
    """
    records = records_for(persona)
    known = set(records)
    accepted: dict[str, str] = {}
    seen: set[str] = set()
    _collapse, _resolve_display = _display_helpers()

    for name in sorted(records):
        display = str(records[name].get("display_name") or "").strip()
        if not display:
            continue
        if _resolves_to_tracked(display):
            logger.warning("[overlay] display name %r resolves to a tracked "
                           "agent; not surfaced", display)
            continue
        key = _collapse(display).casefold()
        if key in seen:
            logger.warning("[overlay] display name %r is already claimed by "
                           "another capability; %r not surfaced", display, name)
            continue
        resolved = _resolve_display(display)
        if resolved in known and resolved != name:
            logger.warning("[overlay] display name %r resolves to capability "
                           "%r; %r not surfaced", display, resolved, name)
            continue
        seen.add(key)
        accepted[name] = display
    return accepted


def coordinator_additions(persona: str | None = None) -> tuple[list[str], list[str]]:
    """SEAM 3. (display names, directory entries) — in a stable, sorted order."""
    names, entries = [], []
    records = records_for(persona)
    surfaced = accepted_displays(persona)
    for name in sorted(records):
        record = records[name]
        display = surfaced.get(name, "")
        if not display:
            continue
        names.append(display)
        entry = str((record.get("coordinator") or {}).get("directory_entry") or "").strip()
        if entry:
            entries.append(entry)
    return names, entries


def name_map_additions(persona: str | None = None) -> dict[str, str]:
    """SEAM 3. {display_name.lower(): name}, for _normalize_agent()."""
    return {display.lower(): name
            for name, display in accepted_displays(persona).items()}


def unavailable_consequence(name: str, persona: str | None = None) -> str:
    """SEAM 4. What the user loses when this capability fails. "" if unknown."""
    record = records_for(persona).get(name) or {}
    return str(record.get("unavailable_consequence") or "").strip()


def confidential_names(persona: str | None = None) -> list[str]:
    """
    SEAM 4. Names for the SENTENCE-GATED list — never the unconditional one.

    _ALWAYS_CONFIDENTIAL is for identifiers "impossible in natural prose", and a
    single substring hit there replaces the whole reply with the canned
    fallback. Its matcher joins tokens across up to four punctuation characters
    or none, so `home_care` on that list suppresses "your home-care tasks", and
    a one-word name like `garden` suppresses every reply containing the word.
    _CONTEXT_SENSITIVE fires only inside a sentence carrying architecture
    vocabulary, which is exactly the mechanism for a name that is also English.
    """
    out: list[str] = []
    for name, record in sorted(records_for(persona).items()):
        names = record.get("confidential_names")
        if isinstance(names, list) and names:
            out.extend(str(n).strip() for n in names if str(n).strip())
        else:
            # A record that declared none still needs its OWN name filtered.
            # Falling back to it is what stops a malformed-but-loadable record
            # landing a capability the filter has never heard of.
            out.append(name)
    return sorted(set(out))


def domain_additions(persona: str | None = None) -> dict[str, list[str]]:
    """
    SEAM 4. domain -> capability names to append. EXISTING domains only.

    A record may join a domain; it may not create one. A new key here would be a
    subject nothing else reads and no tracked agent serves.
    """
    try:
        from tools.wisdom import DOMAINS, OVERFLOW_DOMAIN
        known = set(DOMAINS) | {OVERFLOW_DOMAIN}
    except Exception:
        return {}
    out: dict[str, list[str]] = {}
    for name, record in sorted(records_for(persona).items()):
        for domain in record.get("knowledge_domains") or []:
            if str(domain) in known:
                out.setdefault(str(domain), []).append(name)
    return out


def clear_cache() -> None:
    """Drop every persona's cached records. For tests and for a reload path."""
    _cache.clear()
