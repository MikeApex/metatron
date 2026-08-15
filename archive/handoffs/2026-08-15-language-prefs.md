# Handoff — 2026-08-15 — [DB-0810-15] language preferences, data layer

**Shipped:** `tools/profile.py` — `input_language` and `output_language`, two new
independent per-persona fields, stored as normalized ISO 639-1 codes (a small
name→code map accepts what a user actually says, e.g. "Bulgarian" → `bg`;
a bare code is also accepted directly). Unset = no preference, never defaults
to English. Unknown text is refused loudly, same style as every other field.
Commit: `9a46608`.

**Tests:** `tests/test_profile_language.py`, 13/14 pass (standalone runner,
`python3 tests/test_profile_language.py`).

**Do NOT close `[DB-0810-15]` on this commit.** It is the data layer only.
The one failing test (`fields land in core.orchestrator.load_profile()'s
prompt`) documents a real gap: the system-prompt summary the Synthesizer
actually sees is built by `core/orchestrator.py`'s `load_profile()`, a
hand-written per-field list (`if profile.get("name"): ...`) that does **not**
derive from `tools/profile.py`'s `WRITABLE`/`_PROMPT_EXCLUDED` — contrary to
what my brief assumed. `_PROMPT_EXCLUDED` has zero other references in the
codebase; it's documentary only. Closing needs two more lines in
`core/orchestrator.py::load_profile()` (outside my manifest) plus the
Synthesizer-side translation-boundary work the coordinating window owns.

**For `SESSION.md`:** `[DB-0810-15]` data layer done (`9a46608`); still
blocked on a `core/orchestrator.py::load_profile()` edit + the Synthesizer
translation instruction before it can close.
