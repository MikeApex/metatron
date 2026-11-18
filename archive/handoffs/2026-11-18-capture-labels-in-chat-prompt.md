Model: Opus 5.5. Labelling is judgement about what counts as a fact, and Mike's in-line comments may turn into extractor-instruction changes.

# Capture fidelity — label mike's backfill candidates in chat (paste into a fresh chat)

/metatron-code Run the capture-fidelity labelling walkthrough with me IN CHAT, not in the
terminal: you fetch the items from the VM, present them, I label and comment in-line, you write
the labels file on the VM, and we read the score.

**Budget:** ~0.2–0.4M Opus tokens; no model calls on the VM (fetching and writing are plain
file reads/writes). Mike: ~20–30 min.

## Context — read these, nothing else first

1. `archive/plans/capture_fidelity_plan_2026-11-18.md` — § 4.3 (what counts as a fact), § 4.4
   (the matcher), § 5.2–5.3 (labels and the bar), § 9 decisions 13 (modes).
2. `config/agents/capture_extractor.md` — the extractor's own rules (Red tier: **propose edits,
   never make them without me**).
3. State: commits up to `f2984df` are on `main`. The VM is at `7decf28` (labelling needs nothing
   newer). `config/modules/capture.yaml` has `enabled: false`, `modes: synthesizer: shadow,
   goals_interviewer: on`. The review file on the VM was re-scored by `--rematch`: 160 real user
   turns, 18 candidates. The 2026-11-18 baseline: tasks 0% missed (n=12), preferences 0% (n=2),
   one each of day_shape/goal/profile unsaved and doubtful as facts.

## 1. Fetch the items (read-only — run on the MacBook, explain it to me first)

The sample is the same one `tools.capture --label` would draw (seed 7: all candidates, then 50
found-nothing turns), so the labels file you write later is exactly what `--score` expects.

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command 'cd ~/multi-model-mcp && .venv/bin/python - <<"PY"
import json, random
from pathlib import Path
d = Path("data/personas/mike/capture")
path = sorted(d.glob("backfill_review_*.jsonl"))[-1]
turns = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
cands = [(t, c) for t in turns for c in t["candidates"] if c["disposition"] != "declined"]
empty = [t for t in turns if t["ok"] and not t["candidates"]]
rng = random.Random(7)
sample = rng.sample(cands, min(100, len(cands)))
empties = rng.sample(empty, min(50, len(empty)))
print("FILE", path.name, "| precision items", len(sample), "| recall items", len(empties))
for i, (t, c) in enumerate(sample, 1):
    print()
    print("[P%d]" % i, t["ts"][:16], "USER:", t["user_input"][:900])
    print("  candidate:", c["disposition"], "·", c["kind"], "·", c["say"])
    print("  proposal: ", json.dumps(c.get("proposal"), ensure_ascii=False)[:240])
    print("  matcher says:", c["matcher"])
for i, t in enumerate(empties, 1):
    print()
    print("[R%d]" % i, t["ts"][:16], "USER:", t["user_input"][:900])
PY' 2>&1 | grep -v "NumPy\|increasing_the_tcp\|^$"
```

## 2. Walk me through them

- **Precision items (P1…):** present **five at a time**, one short block per item: my words
  (trimmed if long), what the extractor proposed, and the matcher's call. Ask the one question:
  *is this a fact from my own message that Metatron should keep, as this kind?* My answers:
  - **real** — a fact worth keeping, right kind, and the matcher's call looks right (or I can't tell)
  - **n** — not a fact (passing remark, mood, a request for Metatron to act now, a misread)
  - **w** — a fact, wrong kind (e.g. a habit filed as a profile fact)
  - **m** — right fact, but the matcher's saved/unsaved call is wrong to my knowledge
  Matcher calls: `saved` (its own tool kept it) · `saved_elsewhere` (another agent filed it —
  Logistics obligation, calendar, wisdom…) · `held_now` (already in my records) · `different`
  (saved with other days/values) · `unsaved` (nothing kept it).
- **Recall items (R1…):** ten at a time: *did this message contain something Metatron should
  have kept?* "none", or a few words naming the missed fact.
- When I comment or ask, answer briefly and record anything that bears on the extractor's rules
  or the matcher — that is the second output of this session.

## 3. Write the labels on the VM, then score

Build `{"p": {"1": "real" | "not_a_fact" | "wrong_kind" | "matcher_wrong", ...}, "r": {"1":
true|false, ...}}` (r = a fact was missed), show it to me, then — after I say go — write it with
this command (substitute the JSON for LABELS_JSON; plain words only, no single quotes):

```bash
gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command 'cd ~/multi-model-mcp && .venv/bin/python - <<"PY"
import json, random
from pathlib import Path
labels = json.loads("""LABELS_JSON""")
d = Path("data/personas/mike/capture")
path = sorted(d.glob("backfill_review_*.jsonl"))[-1]
turns = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
cands = [(t, c) for t in turns for c in t["candidates"] if c["disposition"] != "declined"]
empty = [t for t in turns if t["ok"] and not t["candidates"]]
rng = random.Random(7)
sample = rng.sample(cands, min(100, len(cands)))
empties = rng.sample(empty, min(50, len(empty)))
out = path.with_name(path.stem.replace("backfill_review", "labels") + ".jsonl")
with open(out, "w") as fh:
    for i, (t, c) in enumerate(sample, 1):
        if str(i) in labels["p"]:
            fh.write(json.dumps({"part": "precision", "trace_id": t["trace_id"], "kind": c["kind"], "label": labels["p"][str(i)]}) + "\n")
    for i, t in enumerate(empties, 1):
        if str(i) in labels["r"]:
            fh.write(json.dumps({"part": "recall", "trace_id": t["trace_id"], "missed": bool(labels["r"][str(i)])}) + "\n")
print("wrote", out)
PY
.venv/bin/python -m tools.capture --score --persona mike'
```

## 4. Then

- Write the notes from my comments to `archive/plans/capture_labels_notes_2026-11-18.md`:
  each extractor-rule or matcher issue, with the item it came from (trimmed, no more of my
  words than needed).
- Read the score against the minimums (precision ≥ 90%, recall ≥ 80%, matcher ≥ 90%) — and
  say plainly that at n≈18 precision is known only to about ±14 points.
- **Put the switch decision to me with a recommendation:** set `enabled: true` in
  `config/modules/capture.yaml` (modes stay shadow / on), commit with the explicit file list,
  and give me the full MacBook deploy command (`cd ~/Desktop/multi-model-mcp && ./deploy.sh`) —
  or, if a bar fails, propose the `capture_extractor.md` edit first.
- **After the deploy, give me the live checks** (plan § 7.3), each as a full command with its
  directory:
  1. VM: `cd ~/multi-model-mcp && git log --oneline -1` shows the enable commit.
  2. After a day of ordinary use, VM:
     `cd ~/multi-model-mcp && .venv/bin/python -m tools.capture --report --persona mike` —
     pass: "extractor ran on N of N eligible turns" for `synthesizer`, and only `held_out_*`
     outcomes (shadow shows nothing).
  3. Iva's first interview is the interviewer's first live run: the same `--report` with her
     persona name, the day of her interview.
- Close with `/archive`.
