#!/usr/bin/env python3
"""
scripts/fetch_whatsapp_translation_model.py — fetch and convert the Bulgarian→English model.

Decision D (Mike, 2026-11-23; archive/plans/whatsapp_phase1_build_plan_2026-11-23.md § 5):
WhatsApp messages in Bulgarian are translated ON THE VM by a small local model, so the text
never leaves the machine. This downloads the OPUS-MT model from Hugging Face once (a download —
nothing of the user's is sent), converts it to CTranslate2 int8 and writes it where
config/templates/whatsapp_screen.yaml points (`languages.bg.model_dir`).

    .venv/bin/python scripts/fetch_whatsapp_translation_model.py            # bg → en
    .venv/bin/python scripts/fetch_whatsapp_translation_model.py --check    # load + one sentence

Run on the VM (and on the Mac for a local check). Idempotent: an existing model is kept unless
--force. Prints the model card's licence line — Apache-2.0 when fetched on 2026-11-23; plan § 8a
owes its licence and notice with any distribution beyond Mike and Iva.
"""
from __future__ import annotations

import argparse
import re
import shutil
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPO_ID = "Helsinki-NLP/opus-mt-bg-en"
OUT = ROOT / "data" / "models" / "opus-mt-bg-en-ct2"


def _rss_mb() -> float:
    """Current resident memory of this process, in MB."""
    import os
    import subprocess
    if Path("/proc/self/status").exists():
        return int(Path("/proc/self/status").read_text().split("VmRSS:")[1].split()[0]) / 1024
    return int(subprocess.check_output(["ps", "-o", "rss=", "-p", str(os.getpid())])) / 1024


def fetch(force: bool) -> None:
    if (OUT / "model.bin").exists() and not force:
        print(f"already present: {OUT}")
        return
    from huggingface_hub import snapshot_download
    import ctranslate2.converters as conv
    with tempfile.TemporaryDirectory() as tmp:
        src = Path(snapshot_download(REPO_ID, cache_dir=tmp))
        card = (src / "README.md").read_text(errors="replace") if (src / "README.md").exists() else ""
        lic = re.search(r"(?im)^\s*license:\s*(.+)$", card)
        print(f"licence (model card): {lic.group(1).strip() if lic else 'NOT STATED — check before use'}")
        if OUT.exists():
            shutil.rmtree(OUT)
        conv.TransformersConverter(str(src)).convert(str(OUT), quantization="int8", force=True)
        for name in ("source.spm", "target.spm"):
            shutil.copy(src / name, OUT / name)
        if (src / "README.md").exists():
            shutil.copy(src / "README.md", OUT / "MODEL_CARD.md")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"written: {OUT} ({size:.0f} MB)")


def check() -> None:
    sys.path.insert(0, str(ROOT))
    import ctranslate2  # noqa: F401 — the server already has it loaded (speech-to-text),
    import sentencepiece  # noqa: F401 — so only what comes AFTER this is the model's own cost
    from tools.intake_whatsapp import _Translator
    before = _rss_mb()
    t = _Translator(OUT, idle_seconds=5)
    start = time.time()
    out = t("Ще вечеряме ли в събота в 19:00?")
    first = time.time() - start
    start = time.time()
    t("Здравей, как си? Утре в 10 ч. имам среща.")
    second = time.time() - start
    print(f"translation: {out!r}")
    print(f"first call (load + translate) {first:.2f}s; next call {second:.2f}s")
    loaded = _rss_mb()
    print(f"model's own cost: +{loaded - before:.0f} MB resident (process {before:.0f} → {loaded:.0f} MB)")
    time.sleep(6)
    print(f"after the idle unload: {_rss_mb():.0f} MB")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    if args.check:
        check()
    else:
        fetch(args.force)
    return 0


if __name__ == "__main__":
    sys.exit(main())
