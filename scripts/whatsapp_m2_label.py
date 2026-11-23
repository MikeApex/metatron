#!/usr/bin/env python3
"""
scripts/whatsapp_m2_label.py — label a WhatsApp sample, then score the shipped extraction on it.

WhatsApp M2 (plan archive/plans/whatsapp_input_plan_2026-10-26.md § 7; session prompt
archive/handoffs/2026-11-23-whatsapp-m2-labelling-prep-prompt.md). Before any WhatsApp fact
surfaces, measure how well Phase 1's code decides "this message needs the user".

    .venv/bin/python scripts/whatsapp_m2_label.py ~/Downloads/m2_sample.jsonl
    .venv/bin/python scripts/whatsapp_m2_label.py ~/Downloads/m2_sample.jsonl --rescore

**RUN BY THE USER, IN THEIR OWN TERMINAL — NEVER BY CLAUDE CODE.** This script prints other
people's messages to the screen; anything a Claude Code tool call prints enters that conversation.
Only the final summary block is meant to be pasted anywhere, and it is code-tested never to carry
a message's text (tests/test_whatsapp_m2_label.py).

For each row of the export (probe button 8: n, chat_kind, time_s, text — no ids, no names) it
runs `tools.intake_whatsapp._analyse` — the shipped screen, Bulgarian translation and fact code,
called directly — with a neutral share entry (label "Contact"), shows the text, our verdict
(held back / needs you / chat) and the fact line, and takes the user's answer:

    y  needs action          p  needs action, and it is a proposal with a date or time
    n  no action needed      s  skip            u  undo the last answer      q  save and stop

Answers are saved after every one to a resume file in --state-dir (default: the export's own
folder). **The resume file holds no text**: per row only the answer, our prediction, the fact
type, the language, the screen category and whether it carried a time. Ctrl-C loses nothing;
run the same command again to carry on.

`--rescore` recomputes every prediction from the export and the saved answers without asking
again — for re-scoring after a change to config/templates/whatsapp_screen.yaml. It needs the
export, because the resume file has no text to re-analyse.

At the end it prints numbers only, then offers to delete the export and the resume file.

Retires with M2: once WhatsApp facts are live, a re-measurement reuses it, and it is deleted with
the waprobe build when that goes (plan § 4).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import intake_whatsapp as wa  # noqa: E402

KINDS = ("one_to_one", "group")
ANSWERS = {"y", "p", "n", "s"}
NEUTRAL_LABEL = "Contact"
VERDICT_TEXT = {"needs_you": "NEEDS YOU", "chat": "chat (recorded only)", "held_back": "HELD BACK"}
LANG_TEXT = {"en": "English", "bg": "Bulgarian", "other": "other script"}
# Shown above every question (Mike, 11-23), so the key never has to be remembered.
KEY = ("   y = needs action   p = needs action, a proposal with a date/time   n = no action needed\n"
       "   s = skip   u = undo the last answer   q = save and stop")


class Refused(Exception):
    """A clear, user-facing reason the script will not run."""


# ---------------------------------------------------------------------------
# The export and the resume file
# ---------------------------------------------------------------------------

def load_export(path: Path) -> tuple[list[dict], int]:
    """(rows by n, malformed-line count). A malformed line is counted, never shown."""
    rows, bad, seen = [], 0, set()
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            n, kind, t, text = int(r["n"]), r["chat_kind"], int(r["time_s"]), r["text"]
            if kind not in KINDS or not isinstance(text, str) or n in seen:
                raise ValueError
        except Exception:  # noqa: BLE001
            bad += 1
            continue
        seen.add(n)
        rows.append({"n": n, "kind": kind, "time_s": t, "text": text})
    rows.sort(key=lambda r: r["n"])
    return rows, bad


def export_id(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def state_path(state_dir: Path, eid: str) -> Path:
    """The resume file for this export: found again by its id, named with the day it was begun."""
    found = sorted(state_dir.glob(f"whatsapp_m2_labels_*_{eid}.json"))
    if found:
        return found[0]
    return state_dir / f"whatsapp_m2_labels_{date.today().isoformat()}_{eid}.json"


def load_state(path: Path, eid: str) -> dict:
    if not path.exists():
        return {"export_id": eid, "labels": {}}
    state = json.loads(path.read_text())
    if state.get("export_id") != eid:
        raise Refused(f"{path.name} belongs to a different export — move it aside or pass another --state-dir.")
    state.setdefault("labels", {})
    return state


def save_state(path: Path, state: dict) -> None:
    """Atomic, owner-only. No text is ever in `state` — see record()."""
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(state, sort_keys=True, indent=1))
    os.chmod(tmp, 0o600)
    tmp.replace(path)


# ---------------------------------------------------------------------------
# Our prediction — the shipped code, called directly
# ---------------------------------------------------------------------------

def predict(row: dict) -> dict:
    """The VM's verdict on one row, plus what the screen shows. Only `record()`'s fields persist."""
    kind = row["kind"]
    ev = {"text": row["text"], "time": row["time_s"], "chat": "m2-chat", "ordinal": 0,
          "sender": "m2-sender" if kind == "group" else "", "kind": "message", "source": "backup"}
    entry = {"kind": kind, "label": NEUTRAL_LABEL, "senders": {}}
    result = wa._analyse(ev, entry)
    lang = wa.script_of(row["text"])
    lang = {"latin": "en", "cyrillic": "bg"}.get(lang, "other")
    fact = result.get("fact") or {}
    if result.get("category"):
        pred = "held_back"
    elif fact.get("action"):
        pred = "needs_you"
    else:
        pred = "chat"
    return {"pred": pred, "type": fact.get("type"), "lang": lang, "category": result.get("category"),
            "has_when": bool(fact.get("when")), "subject": fact.get("subject") or ""}


def record(row: dict, answer: str, p: dict) -> dict:
    """What the resume file keeps for one row. **No text, no subject, no translation.**"""
    return {"answer": answer, "kind": row["kind"], "pred": p["pred"], "type": p["type"],
            "lang": p["lang"], "category": p["category"], "has_when": p["has_when"]}


def model_check() -> None:
    """Refuse, rather than score Bulgarian as unscreened, when the translation model is absent."""
    spec = ((wa.screen_config().get("languages") or {}).get("bg") or {})
    where = spec.get("model_dir") or "data/models/opus-mt-bg-en-ct2"
    if wa.screen_config().get("_broken"):
        raise Refused("config/templates/whatsapp_screen.yaml could not be read — every message would be held back.")
    if wa.translate("Здравей", "bg") is None:
        raise Refused(f"The Bulgarian translation model is not usable at {where}.\n"
                      "Fetch it first:  .venv/bin/python scripts/fetch_whatsapp_translation_model.py\n"
                      "then run this again. (Without it every Bulgarian message would score as held back.)")


# ---------------------------------------------------------------------------
# Labelling
# ---------------------------------------------------------------------------

def _safe(s: str) -> str:
    return (s or "").encode("utf-8", "replace").decode("utf-8")


def show(row: dict, p: dict, i: int, total: int, out) -> None:
    out("")
    out(f"──── {i} of {total} · #{row['n']} · {row['kind'].replace('_', '-')} · {LANG_TEXT[p['lang']]} ────")
    out(_safe(row["text"]))
    if p["lang"] == "bg":
        english, _ = wa.english_for(row["text"])
        out(f"   English: {_safe(english) if english else '(no translation)'}")
    verdict = VERDICT_TEXT[p["pred"]]
    if p["pred"] == "held_back":
        verdict += f" — {p['category']}"
    out(f"   Our verdict: {verdict}" + (f"   ·   {p['subject']}" if p["subject"] else ""))


def label_loop(rows: list[dict], state: dict, path: Path, ask=input, out=print) -> bool:
    """Ask about every unlabelled row in n order. True when every row has an answer."""
    labels = state["labels"]
    order: list[str] = state.setdefault("order", [k for k in labels])
    pending = [r for r in rows if str(r["n"]) not in labels]
    by_n = {str(r["n"]): r for r in rows}
    out(f"{len(labels)} answered, {len(pending)} to go.")
    i = 0
    while i < len(pending):
        row = pending[i]
        p = predict(row)
        show(row, p, len(labels) + 1, len(rows), out)
        out(KEY)
        ans = ask("   Needs action? [y/p/n/s/u/q] ").strip().lower()
        if ans == "q":
            out(f"Saved {len(labels)} answers. Run the same command to carry on.")
            return False
        if ans == "u":
            if not order:
                out("   Nothing to undo.")
                continue
            last = order.pop()
            labels.pop(last, None)
            save_state(path, state)
            if last in by_n:
                pending.insert(i, by_n[last])
            continue
        if ans not in ANSWERS:
            out("   Please answer y, p, n, s, u or q.")
            continue
        labels[str(row["n"])] = record(row, ans, p)
        order.append(str(row["n"]))
        save_state(path, state)
        i += 1
    return True


def rescore(rows: list[dict], state: dict) -> int:
    """Recompute every saved prediction from the export; the answers are kept. Returns changes."""
    changed = 0
    for row in rows:
        key = str(row["n"])
        old = state["labels"].get(key)
        if not old:
            continue
        new = record(row, old["answer"], predict(row))
        if new != old:
            changed += 1
        state["labels"][key] = new
    return changed


# ---------------------------------------------------------------------------
# The summary — numbers only
# ---------------------------------------------------------------------------

def _pct(a: int, b: int) -> str:
    return f"{100 * a / b:5.1f}%" if b else "    —"


def _scores(recs: list[dict]) -> tuple[int, int, int, int]:
    """(caught, missed, false alarms, needs action) over answered, non-skipped records."""
    caught = sum(1 for r in recs if r["answer"] in ("y", "p") and r["pred"] == "needs_you")
    missed = sum(1 for r in recs if r["answer"] in ("y", "p") and r["pred"] != "needs_you")
    false_alarms = sum(1 for r in recs if r["answer"] == "n" and r["pred"] == "needs_you")
    return caught, missed, false_alarms, caught + missed


def summary(state: dict, total_rows: int, malformed: int = 0, rescored: int | None = None) -> str:
    labels = list(state["labels"].values())
    answered = [r for r in labels if r["answer"] != "s"]
    skipped = sum(1 for r in labels if r["answer"] == "s")
    lines = ["=== WhatsApp M2 summary — paste this block ===",
             f"rows in export {total_rows}"
             + (f" (+{malformed} unreadable lines)" if malformed else "")
             + f" · answered {len(answered)} · skipped {skipped} · not yet asked {total_rows - len(labels)}"]
    if rescored is not None:
        lines.append(f"re-scored from saved answers: {rescored} predictions changed")
    c, m, f, need = _scores(answered)
    lines.append(f"needs action (your answer): {need} of {len(answered)}")
    lines.append(f"{'':16}{'need':>6}{'caught':>8}{'missed':>8}{'f.alarm':>9}{'precision':>11}{'recall':>8}")

    def line(name: str, recs: list[dict]) -> str:
        c, m, f, need = _scores(recs)
        return f"{name:16}{need:>6}{c:>8}{m:>8}{f:>9}{_pct(c, c + f):>11}{_pct(c, c + m):>8}"

    lines.append(line("overall", answered))
    for kind in KINDS:
        lines.append(line(kind.replace("_", "-"), [r for r in answered if r["kind"] == kind]))
    for lang in ("en", "bg", "other"):
        recs = [r for r in answered if r["lang"] == lang]
        if recs or lang != "other":
            lines.append(line(LANG_TEXT[lang], recs))
    hard = [r for r in answered if r["answer"] == "p" and r["kind"] == "one_to_one"]
    lines.append(f"one-to-one proposals with a date/time (your 'p'): {len(hard)}, "
                 f"missed {sum(1 for r in hard if r['pred'] != 'needs_you')}")
    group_p = [r for r in answered if r["answer"] == "p" and r["kind"] == "group"]
    if group_p:
        lines.append(f"group proposals with a date/time (your 'p'): {len(group_p)}, "
                     f"missed {sum(1 for r in group_p if r['pred'] != 'needs_you')}")

    def tally(recs: list[dict]) -> str:
        counts: dict[str, int] = {}
        for r in recs:
            k = f"{r['kind'].replace('_', '-')}·{r['lang']}·{r['pred']}·{r['type'] or r['category'] or '-'}"
            counts[k] = counts.get(k, 0) + 1
        return ", ".join(f"{k}={v}" for k, v in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))) or "none"

    lines.append("misses by kind·language·our verdict·our type: "
                 + tally([r for r in answered if r["answer"] in ("y", "p") and r["pred"] != "needs_you"]))
    lines.append("false alarms by kind·language·our verdict·our type: "
                 + tally([r for r in answered if r["answer"] == "n" and r["pred"] == "needs_you"]))
    held = [r for r in answered if r["pred"] == "held_back"]
    cats: dict[str, int] = {}
    for r in held:
        cats[r["category"]] = cats.get(r["category"], 0) + 1
    lines.append(f"screen: held back {len(held)} of {len(answered)} ({_pct(len(held), len(answered)).strip()}), "
                 f"of which you said needs action {sum(1 for r in held if r['answer'] in ('y', 'p'))}; "
                 "by category {" + ", ".join(f"{k}={v}" for k, v in sorted(cats.items())) + "}")
    lines.append(f"unscreened (no translation model or another script): "
                 f"{sum(1 for r in answered if r['category'] == 'unscreened')}")
    lines.append("=== end ===")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Deleting
# ---------------------------------------------------------------------------

def offer_delete(export: Path, spath: Path, ask=input, out=print) -> bool:
    """Default yes. True when the files were deleted."""
    paths = [export, spath, spath.with_suffix(".json.tmp")]
    out("")
    out("The export holds other people's messages in plain text; no meter or sweep will ever remove it.")
    out("Keep both files only if you will re-score after a tuning change (--rescore needs the export).")
    ans = ask("Delete the export and the resume file now? [Y/n] ").strip().lower()
    if ans in ("", "y", "yes"):
        for p in paths:
            p.unlink(missing_ok=True)
        out("Deleted." if not any(p.exists() for p in paths) else "NOT all deleted — remove them by hand.")
        return True
    out(f"Kept: {export} and {spath}")
    return False


# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None, ask=input, out=print) -> int:
    ap = argparse.ArgumentParser(description="WhatsApp M2 — label a sample and score the shipped extraction.")
    ap.add_argument("export", type=Path, help="m2_sample.jsonl from probe button 8")
    ap.add_argument("--state-dir", type=Path, default=None,
                    help="where the resume file lives (default: the export's own folder)")
    ap.add_argument("--rescore", action="store_true",
                    help="recompute predictions from the export and saved answers; ask nothing")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.WARNING, stream=sys.stderr)

    try:
        export = args.export.expanduser()
        if not export.is_file():
            raise Refused(f"No export at {export}.")
        state_dir = (args.state_dir or export.parent).expanduser()
        state_dir.mkdir(parents=True, exist_ok=True)
        model_check()
        rows, malformed = load_export(export)
        if not rows:
            raise Refused("The export has no readable rows.")
        eid = export_id(export)
        spath = state_path(state_dir, eid)
        state = load_state(spath, eid)
    except Refused as exc:
        out(f"REFUSED: {exc}")
        return 2

    rescored = None
    if args.rescore:
        if not state["labels"]:
            out("REFUSED: no saved answers to re-score — label first.")
            return 2
        rescored = rescore(rows, state)
        save_state(spath, state)
    else:
        try:
            done = label_loop(rows, state, spath, ask=ask, out=out)
        except (KeyboardInterrupt, EOFError):
            out(f"\nStopped. {len(state['labels'])} answers are saved; run the same command to carry on.")
            return 130
        if not done:
            return 0

    out("")
    out(summary(state, len(rows), malformed, rescored))
    offer_delete(export, spath, ask=ask, out=out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
