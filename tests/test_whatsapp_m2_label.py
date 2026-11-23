"""
tests/test_whatsapp_m2_label.py — the M2 labelling script, offline, on planted texts.

Script: scripts/whatsapp_m2_label.py. What must hold, because the user pastes the summary into a
Claude Code chat and the resume file sits on disk: **the summary and the resume file never carry
a message's text, the neutral label, or a number from a message.** Also: the arithmetic, resuming
after Ctrl-C, undo, re-scoring without re-asking, the refusal without a translation model, and the
delete step. No network; the Bulgarian translator is a stand-in.

    .venv/bin/python tests/test_whatsapp_m2_label.py

Exits 0 if every check passes, 1 otherwise.
"""
from __future__ import annotations

import json
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.whatsapp_m2_label as M  # noqa: E402
import tools.intake_whatsapp as W  # noqa: E402

_root = Path(tempfile.mkdtemp(prefix="m2_label_test_"))
_results: list[tuple[str, bool, str]] = []

# Every planted text carries a token no summary or resume file may ever contain.
TOKENS = ["zqxalpha", "zqxbravo", "zqxcharlie", "zqxdelta", "zqxecho", "zqxfoxtrot", "zqxgolf"]
PLANTED_NUMBER = "07700900123"
FAKE_BG = {
    "Ще вечеряме ли в събота в 19:00? zqxfoxtrot": "Shall we have dinner on Saturday at 19:00? zqxfoxtrot",
    "Здравей": "Hello",
}
T0 = 1_763_870_400  # 2025-11-23 04:00 UTC, whole seconds


def _rows() -> list[dict]:
    return [
        {"n": 1, "chat_kind": "one_to_one", "time_s": T0, "text": "zqxalpha are you free Saturday at 19:00 for dinner?"},
        {"n": 2, "chat_kind": "one_to_one", "time_s": T0, "text": "zqxbravo lol ok"},
        {"n": 3, "chat_kind": "group", "time_s": T0, "text": "zqxcharlie who is coming tonight?"},
        {"n": 4, "chat_kind": "group", "time_s": T0, "text": "zqxdelta shall we meet on Sunday at 18:30?"},
        {"n": 5, "chat_kind": "one_to_one", "time_s": T0, "text": f"zqxecho can you call me back on {PLANTED_NUMBER} please"},
        {"n": 6, "chat_kind": "one_to_one", "time_s": T0, "text": "Ще вечеряме ли в събота в 19:00? zqxfoxtrot"},
        {"n": 7, "chat_kind": "one_to_one", "time_s": T0, "text": "zqxgolf Θα φάμε μαζί το Σάββατο;"},
    ]


def _export(name: str, rows: list[dict] | None = None) -> Path:
    d = _root / name
    d.mkdir(parents=True, exist_ok=True)
    p = d / "m2_sample.jsonl"
    p.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in (rows or _rows())), encoding="utf-8")
    return p


class Script:
    """Scripted answers; records every prompt and every printed line."""

    def __init__(self, answers, interrupt_after: int | None = None):
        self.answers = list(answers)
        self.prompts: list[str] = []
        self.lines: list[str] = []
        self.interrupt_after = interrupt_after

    def ask(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.interrupt_after is not None and len(self.prompts) > self.interrupt_after:
            raise KeyboardInterrupt
        if not self.answers:
            raise AssertionError(f"unexpected prompt: {prompt!r}")
        return self.answers.pop(0)

    def out(self, line: str = "") -> None:
        self.lines.append(line)

    def text(self) -> str:
        return "\n".join(self.lines)

    def summary(self) -> str:
        t = self.text()
        start, end = t.index("=== WhatsApp M2 summary"), t.index("=== end ===")
        return t[start:end + len("=== end ===")]


def _run(export: Path, script: Script, *extra: str) -> int:
    return M.main([str(export), *extra], ask=script.ask, out=script.out)


def _resume_file(export: Path) -> Path:
    found = list(export.parent.glob("whatsapp_m2_labels_*.json"))
    assert len(found) == 1, found
    return found[0]


def _assert_clean(blob: str, where: str) -> None:
    for t in TOKENS + [PLANTED_NUMBER, "Contact", "Ще", "вечеряме", "Shall we", "dinner", "Saturday", "19:00"]:
        assert t not in blob, f"{t!r} leaked into {where}"


def check(name: str):
    def wrap(fn):
        W.set_translator(lambda t: FAKE_BG.get(t, "translated words"))
        try:
            fn()
            _results.append((name, True, ""))
        except Exception:  # noqa: BLE001
            _results.append((name, False, traceback.format_exc()))
        finally:
            W.set_translator(None)
        return fn
    return wrap


# ---------------------------------------------------------------------------

@check("the shipped code decides: one-to-one proposal needs you, group question is chat, other script held back")
def _():
    preds = {r["n"]: M.predict({"n": r["n"], "kind": r["chat_kind"], "time_s": r["time_s"], "text": r["text"]})
             for r in _rows()}
    assert preds[1]["pred"] == "needs_you" and preds[1]["type"] == "proposal" and preds[1]["has_when"], preds[1]
    assert preds[2]["pred"] == "chat", preds[2]
    assert preds[3]["pred"] == "chat" and preds[3]["type"] == "question", preds[3]   # group question → info
    assert preds[4]["pred"] == "needs_you" and preds[4]["type"] == "proposal", preds[4]  # group proposal with a time
    assert preds[5]["pred"] == "needs_you" and preds[5]["type"] == "request", preds[5]
    assert preds[6]["pred"] == "needs_you" and preds[6]["lang"] == "bg", preds[6]
    assert preds[7]["pred"] == "held_back" and preds[7]["category"] == "unscreened", preds[7]
    assert "from Contact" in preds[1]["subject"], preds[1]


@check("the summary and the resume file carry no planted text, label or number")
def _():
    export = _export("clean")
    s = Script(["y", "n", "y", "p", "y", "p", "s", "n"])  # seven answers, then keep the files
    assert _run(export, s) == 0
    _assert_clean(s.summary(), "the summary")
    resume = _resume_file(export)
    _assert_clean(resume.read_text(), "the resume file")
    state = json.loads(resume.read_text())
    keys = {k for rec in state["labels"].values() for k in rec}
    assert keys == {"answer", "kind", "pred", "type", "lang", "category", "has_when"}, keys
    # The texts were shown to the person labelling — that is the script's job.
    assert any("zqxalpha" in line for line in s.lines)
    assert any("English: Shall we have dinner" in line for line in s.lines)


@check("the arithmetic is right on a known set")
def _():
    def rec(answer, pred, kind="one_to_one", lang="en", typ=None, category=None):
        return {"answer": answer, "kind": kind, "pred": pred, "type": typ, "lang": lang,
                "category": category, "has_when": False}
    labels = [
        rec("y", "needs_you", typ="question"), rec("y", "needs_you", typ="request"),
        rec("p", "needs_you", typ="proposal"), rec("y", "needs_you", kind="group", typ="proposal"),
        rec("p", "chat", typ="info"),                                      # a missed one-to-one proposal
        rec("y", "held_back", lang="bg", category="unscreened"),          # a miss the screen made
        rec("n", "needs_you", typ="question"), rec("n", "needs_you", kind="group", typ="proposal"),
        rec("n", "chat", typ="info"), rec("n", "chat", kind="group", typ="question"),
        rec("s", "chat", typ="info"),
    ]
    state = {"labels": {str(i + 1): r for i, r in enumerate(labels)}}
    out = M.summary(state, total_rows=12)
    lines = out.splitlines()
    assert "rows in export 12 · answered 10 · skipped 1 · not yet asked 1" in lines[1], lines[1]
    assert "needs action (your answer): 6 of 10" in out, out
    row = {ln.split()[0]: ln.split()[1:] for ln in lines if len(ln.split()) == 7 and ln.split()[0] in
           ("overall", "one-to-one", "group", "English", "Bulgarian")}
    assert row["overall"] == ["6", "4", "2", "2", "66.7%", "66.7%"], row["overall"]
    assert row["one-to-one"] == ["5", "3", "2", "1", "75.0%", "60.0%"], row["one-to-one"]
    assert row["group"] == ["1", "1", "0", "1", "50.0%", "100.0%"], row["group"]
    assert row["Bulgarian"] == ["1", "0", "1", "0", "—", "0.0%"], row["Bulgarian"]
    assert "one-to-one proposals with a date/time (your 'p'): 2, missed 1" in out, out
    assert "misses by kind·language·our verdict·our type: one-to-one·bg·held_back·unscreened=1, " \
           "one-to-one·en·chat·info=1" in out, out
    assert "screen: held back 1 of 10 (10.0%), of which you said needs action 1; by category {unscreened=1}" in out, out
    assert "unscreened (no translation model or another script): 1" in out, out


@check("Ctrl-C keeps every answer; the next run asks only what is left")
def _():
    export = _export("resume")
    first = Script(["y", "n", "y"], interrupt_after=3)
    assert _run(export, first) == 130
    state = json.loads(_resume_file(export).read_text())
    assert sorted(state["labels"]) == ["1", "2", "3"], state["labels"].keys()
    second = Script(["p", "y", "p", "n", "n"])  # rows 4–7, then keep the files
    assert _run(export, second) == 0
    asked = [p for p in second.prompts if p.strip().startswith("Needs action?")]
    assert len(asked) == 4, asked
    assert "answered 7 · skipped 0 · not yet asked 0" in second.summary(), second.summary()


@check("undo re-asks the last answer")
def _():
    export = _export("undo")
    s = Script(["y", "u", "n", "n", "n", "n", "n", "n", "n", "n"])
    assert _run(export, s) == 0
    state = json.loads(_resume_file(export).read_text())
    assert state["labels"]["1"]["answer"] == "n", state["labels"]["1"]
    assert len(state["labels"]) == 7


@check("--rescore recomputes predictions from the export without asking again")
def _():
    export = _export("rescore")
    assert _run(export, Script(["y", "n", "y", "p", "y", "p", "n", "n"])) == 0
    original = W.screen
    W.screen = lambda text: "violence"       # stand-in for a tuning change that holds everything back
    try:
        s = Script(["n"])                    # only the delete prompt may be asked
        assert _run(export, s, "--rescore") == 0
    finally:
        W.screen = original
    assert len(s.prompts) == 1 and "Delete" in s.prompts[0], s.prompts
    out = s.summary()
    assert "re-scored from saved answers: 6 predictions changed" in out, out  # row 7 was already held back
    assert "screen: held back 7 of 7" in out, out
    _assert_clean(out, "the re-score summary")


@check("no translation model → refused, nothing asked, nothing written")
def _():
    export = _export("nomodel")
    W.set_translator(lambda t: None)
    s = Script([])
    assert _run(export, s) == 2
    assert "REFUSED" in s.text() and "fetch_whatsapp_translation_model.py" in s.text(), s.text()
    assert not list(export.parent.glob("whatsapp_m2_labels_*.json"))


@check("a resume file from another export is refused")
def _():
    export = _export("mismatch")
    assert _run(export, Script(["n", "q"])) == 0
    resume = _resume_file(export)
    state = json.loads(resume.read_text())
    state["export_id"] = "000000000000"   # same name, someone else's answers inside
    resume.write_text(json.dumps(state))
    s = Script([])
    assert _run(export, s) == 2 and "different export" in s.text(), s.text()


@check("the delete step defaults to yes and removes the export and the resume file")
def _():
    export = _export("delete")
    assert _run(export, Script(["n"] * 7 + [""])) == 0
    assert not export.exists()
    assert not list(export.parent.glob("whatsapp_m2_labels_*"))


@check("an unreadable line is counted, never shown")
def _():
    export = _export("malformed")
    with export.open("a", encoding="utf-8") as fh:
        fh.write('{"n": 99, "chat_kind": "zqxbroken", "text": "zqxhidden"}\nnot json zqxhidden\n')
    s = Script(["n"] * 7 + ["n"])
    assert _run(export, s) == 0
    assert "zqxhidden" not in s.text()
    assert "rows in export 7 (+2 unreadable lines)" in s.summary(), s.summary()


# ---------------------------------------------------------------------------

def main() -> int:
    failed = [r for r in _results if not r[1]]
    for name, ok, err in _results:
        print(f"  {'PASS' if ok else 'FAIL'}  {name}")
        if not ok:
            print("        " + err.replace("\n", "\n        "))
    shutil.rmtree(_root, ignore_errors=True)
    print(f"\n{len(_results) - len(failed)}/{len(_results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
