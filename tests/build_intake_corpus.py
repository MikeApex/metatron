"""
tests/build_intake_corpus.py — turn a real mailbox into labelled-corpus stubs.

WHY THIS EXISTS. `[DB-0820-03]`'s gate needs a hand-labelled corpus of real messages
before the intake extractor is switched on. Hand-writing one JSON file per message is
the reason that step sat undone from 2026-08-20 to 2026-09-03: the work is not the
judgement, it is the transcription. This script does the transcription and leaves only
the judgement — every field is filled from the live envelope except `label`, which is
the user's and is deliberately left empty.

WHY IT FETCHES RATHER THAN READS records.jsonl. The sweep's record rows are
content-light by design (tools/intake.py `_record_row`): subject yes, **body no**. The
`--extractor` half of the eval grades a model on the body, so a corpus built from
records could never run it. `tools.intake_email.fetch()` returns full envelopes, and
without `skip=` it returns the newest `limit` regardless of what the sweep has already
seen — so the corpus does not have to wait for mail to accumulate.

THE OUTPUT IS PERSONAL DATA. `tests/intake_fixtures/` is gitignored (line 171) and the
files are written `600`. Run this on the machine that holds the mailbox — the VM, for
mike. Never commit the output, and never copy it to a machine the mailbox is not on.

IDEMPOTENT ON PURPOSE. A stub that already carries a non-empty `label` is never
rewritten, so re-running after more mail arrives adds the new messages and leaves
finished work alone. Filenames derive from the envelope id, so the same message maps to
the same file across runs.

    python3 tests/build_intake_corpus.py                # write stubs, print the sheet
    python3 tests/build_intake_corpus.py --limit 50
    python3 tests/build_intake_corpus.py --sheet-only   # print, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.persona import persona_scope                  # noqa: E402

FIXTURES_DIR = Path(__file__).parent / "intake_fixtures"

# Kept in lockstep with run_intake_eval.CATEGORIES and config/templates/intake.yaml.
# Duplicated rather than imported so a corpus build cannot be blocked by an import
# cycle at the moment someone is mid-labelling.
CATEGORIES = (
    "action_required", "correspondence", "booking_confirmation", "bill_statement",
    "invitation", "announcement", "promotion", "notification", "unclear",
)

# The second axis (2026-09-03). `""` in a stub means unlabelled; `null` is a real
# answer meaning "queue this nowhere".
DOMAINS = (
    "logistics", "finance", "relationships", "work_vocation", "recreation", "null",
)


def _safe_name(envelope_id: str) -> str:
    """A filename that survives a round trip through any filesystem."""
    return re.sub(r"[^A-Za-z0-9_.-]", "_", envelope_id)[:120] + ".json"


def _existing_label(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return (json.loads(path.read_text()).get("label") or "").strip()
    except Exception:
        return ""


def build(limit: int, write: bool) -> int:
    import tools.intake_email as intake_email

    envelopes = intake_email.fetch(limit=limit)
    if not envelopes:
        print("No envelopes fetched. Email is unconfigured, disabled, or the folder is empty.")
        return 2

    if write:
        FIXTURES_DIR.mkdir(parents=True, exist_ok=True)

    written = kept = 0
    by_sender: dict[str, list] = defaultdict(list)

    for env in envelopes:
        by_sender[env.sender_address or "(no sender)"].append(env)
        if not write:
            continue
        path = FIXTURES_DIR / _safe_name(env.id)
        if _existing_label(path):
            kept += 1
            continue
        stub = {
            "label": "",
            "domain": "",
            "sender": env.sender_address,
            "sender_display": env.sender_display,
            "subject": env.subject,
            "body": env.body,
            "received": env.received,
            "signals": env.signals or {},
            "note": "",
        }
        path.write_text(json.dumps(stub, indent=2, sort_keys=True))
        try:
            path.chmod(0o600)
        except OSError:
            pass
        written += 1

    if write:
        print(f"corpus: {written} stub(s) written, {kept} already labelled "
              f"→ {FIXTURES_DIR}")
        print(f"labels still empty: {written}\n")

    # ── The review sheet ──────────────────────────────────────────────────────
    # Sender-first, because a sender is usually reliably one thing and labelling by
    # sender collapses most of the corpus into a handful of decisions. The per-message
    # lines are what is left to judge individually.
    print(f"{len(envelopes)} message(s) from {len(by_sender)} sender(s)\n")
    order = sorted(by_sender.items(), key=lambda kv: -len(kv[1]))
    for i, (sender, envs) in enumerate(order, 1):
        display = (envs[0].sender_display or "").strip()
        bulk = sum(1 for e in envs if (e.signals or {}).get("list_unsubscribe"))
        print(f"[S{i}] {display or sender}  <{sender}>")
        print(f"      {len(envs)} message(s)" + (f", {bulk} bulk-headed" if bulk else ""))
        for e in envs:
            print(f"      · {e.received[:10]}  {e.subject[:96] or '(no subject)'}")
        print()

    print("Categories: " + ", ".join(CATEGORIES))
    print("Domains:    " + ", ".join(DOMAINS))
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=50,
                    help="how many of the newest messages to pull (default 50)")
    ap.add_argument("--persona", default="mike")
    ap.add_argument("--sheet-only", action="store_true",
                    help="print the review sheet, write no files")
    args = ap.parse_args()

    with persona_scope(args.persona):
        return build(args.limit, write=not args.sheet_only)


if __name__ == "__main__":
    raise SystemExit(main())
