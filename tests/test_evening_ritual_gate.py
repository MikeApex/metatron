"""
tests/test_evening_ritual_gate.py — the evening ritual reaches only the evening session.

[DB-0822-10]. On 2026-08-21 the complete 13-item virtue list went out at 16:27, 18:24,
19:28 and 20:00. Only 20:00 was the evening job. The cause was not a missing rule:
config/agents/synthesizer.md already scopes the ritual to "when the session opens with
the evening_close scheduler prompt", and that instruction was simply not followed. The
cause was core/orchestrator.py injecting config/personas/{p}/evening_ritual.md into
EVERY session's system prompt, so the text was always sitting there to be recited.

So the fix is structural, and this suite checks the structure rather than the prose:
text that is never injected cannot be recited, whatever the model decides to do.

The match is against the persona's OWN configured evening_close prompt, read from
scheduler.yaml — not a literal in the code. The VM owns the live persona config, so a
hard-coded copy would go stale the first time Mike reworded the prompt, and would do it
silently by un-gating the ritual again.

Standalone runner (no pytest dependency), matching tests/test_contact_dedup_gate.py.

Usage:
    python tests/test_evening_ritual_gate.py

Exits 0 if every test passes, 1 otherwise.
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

_results: list[tuple[str, bool, str]] = []

EVENING_PROMPT = (
    "How did today go? Anything worth capturing before the day closes? Reference "
    "anything that was left open earlier today rather than asking in the abstract."
)
RITUAL_MARKER = "TEMPERANCE-SILENCE-ORDER-RESOLUTION"


def check(name: str, condition: bool, detail: str = "") -> None:
    _results.append((name, bool(condition), detail))


def _run() -> None:
    tmp = tempfile.mkdtemp(prefix="evening_gate_")
    cfg_dir = Path(tmp) / "persona_config"
    cfg_dir.mkdir(parents=True, exist_ok=True)
    os.environ["METATRON_PERSONA"] = "test_confirm"

    (cfg_dir / "evening_ritual.md").write_text(
        f"# Evening ritual\n\nReview the thirteen virtues: {RITUAL_MARKER}\n"
    )
    (cfg_dir / "scheduler.yaml").write_text(
        "schedules:\n"
        "  evening_close:\n"
        "    enabled: true\n"
        '    time: "20:00"\n'
        f'    prompt: "{EVENING_PROMPT}"\n'
    )

    import core.orchestrator as ORC
    real_cfg_dir = ORC.persona_config_dir
    real_persona_md = ORC.persona_md
    ORC.persona_config_dir = lambda persona=None: cfg_dir

    # load_config fails closed on a missing identity file (personas.md rule), so the
    # fixture supplies one rather than borrowing a real persona's.
    identity = Path(tmp) / "identity.md"
    identity.write_text("Test persona for the evening ritual gate.\n")
    ORC.persona_md = lambda persona=None: identity

    try:
        # --- session_kind: what counts as the evening session ------------------------
        check("the configured evening_close prompt is recognised",
              ORC.session_kind(EVENING_PROMPT, "mike") == "evening_close")
        check("case and whitespace drift still match — it round-trips through the app",
              ORC.session_kind("  HOW DID TODAY GO?   Anything worth capturing before "
                               "the day closes? Reference anything that was left open "
                               "earlier today rather than asking in the abstract.  ",
                               "mike") == "evening_close",
              "the prompt is normalised, not compared byte-for-byte")
        check("an ordinary typed turn is not the evening session",
              ORC.session_kind("Add Marcus Whitfield to my contacts.", "mike") is None)
        check("another scheduled prompt is not the evening session",
              ORC.session_kind("Check in.", "mike") is None,
              "10:30 and 13:32 check-ins were two of the four 08-21 recitals")
        check("an empty turn is not the evening session",
              ORC.session_kind("", "mike") is None)

        # A persona with no scheduler.yaml must not crash the session, and must fail
        # toward the quieter prompt.
        bare = Path(tmp) / "bare_config"
        bare.mkdir(parents=True, exist_ok=True)
        ORC.persona_config_dir = lambda persona=None: bare
        check("a persona with no scheduler.yaml yields no session kind",
              ORC.session_kind(EVENING_PROMPT, "nobody") is None)
        ORC.persona_config_dir = lambda persona=None: cfg_dir

        # --- load_config: the injection itself ---------------------------------------
        as_evening = ORC.load_config(persona="mike", kind="evening_close")
        check("the evening session still gets the ritual",
              RITUAL_MARKER in as_evening,
              "gating it must not delete it — 20:00 is what it is for")

        as_ordinary = ORC.load_config(persona="mike", kind=None)
        check("an ordinary session does NOT carry the ritual",
              RITUAL_MARKER not in as_ordinary,
              "this is the whole item: text not injected cannot be recited")

        check("omitting kind entirely defaults to the quieter prompt",
              RITUAL_MARKER not in ORC.load_config(persona="mike"),
              "a caller that does not know the session kind must not get the ritual")

        check("an unrelated session kind does not open the gate",
              RITUAL_MARKER not in ORC.load_config(persona="mike", kind="morning_open"))

        check("gating the ritual removes real prompt weight from every other session",
              len(as_ordinary) < len(as_evening),
              f"{len(as_ordinary)} vs {len(as_evening)} chars")
    finally:
        ORC.persona_config_dir = real_cfg_dir
        ORC.persona_md = real_persona_md


def main() -> int:
    _run()
    passed = sum(1 for _, ok, _ in _results if ok)
    for name, ok, detail in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok and detail:
            print(f"        {detail}")
    total = len(_results)
    print(f"\n{passed} passed, {total - passed} failed, {total} total")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
