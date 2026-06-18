# Goals Interview — Setup and Run Guide
*Phase 5 / D5. Run this in a terminal session, not in Claude Code.*
*All data stays local. No cloud API calls.*

---

## What this is

The Goals Interview populates the three core config files that every specialist agent depends on:

- `config/prime_directive.md` — Tier 1: your terminal values and life philosophy
- `config/mission.md` — Tier 2: your current life chapter
- `config/goals.yaml` — Tier 3: 90-day, weekly, and daily goals

It uses a Motivational Interviewing approach — open questions, reflective listening, surfacing implicit values behind stated goals. No time limit. The interviewer follows wherever the conversation goes and returns to template phases opportunistically.

**After the interview, run `write_aspirational_baseline`** (see final section) while the session is fresh — it captures your "1 in 100" best/worst days anchoring, which Pattern Miner uses for cold-start analysis.

---

## Step 1 — Start Ollama

Open a terminal. Check whether Ollama is already running:

```bash
curl -s http://localhost:11434/api/tags | python3 -m json.tool 2>/dev/null | grep name
```

If you see `qwen3:14b` in the output, Ollama is running and the model is ready. Skip to Step 2.

If Ollama is not running, start it:

```bash
ollama serve
```

Leave that terminal open. In a new terminal window, verify the model is available:

```bash
ollama list
```

You should see `qwen3:14b` in the list. If not, pull it:

```bash
ollama pull qwen3:14b
```

---

## Step 2 — Run the interview

Navigate to the project directory and activate the virtual environment:

```bash
cd ~/Desktop/multi-model-mcp
source .venv/bin/activate
```

Start the Goals Interview:

```bash
python core/orchestrator.py --agent goals_interviewer --provider ollama
```

**What `--provider ollama` does:** Forces all model calls to the local Ollama server (`localhost:11434`) using `qwen3:14b`. This overrides `local_enabled` in `config/modules/routing.yaml` — the interview runs fully locally regardless of routing configuration. No data leaves your machine.

**What to expect:**
- The interviewer will guide you through phases: Discovery → Visioning → Detailing
- It will ask about what you're working on, what matters, what's getting in the way
- It will surface implicit values, not just stated goals
- It will write to the three config files as the conversation develops (via `write_config` tool)
- Redirect it freely: "let's come back to that" / "I want to talk about X first" / "I've said enough on this"
- The interview has no time limit and can be paused and resumed in a subsequent session

**If Ollama is slow:** qwen3:14b on CPU is slower than cloud models. Responses may take 15-30 seconds. This is normal. If you need faster throughput, check `ollama ps` to see if the model is loaded in memory, or try a smaller model (edit `OLLAMA_MODEL` in `core/orchestrator.py` — but note that smaller models will be less capable for this task).

---

## Step 3 — Verify the output

After the interview, check that the three files have been populated:

```bash
head -20 config/prime_directive.md
head -20 config/mission.md
python3 -c "import yaml; d=yaml.safe_load(open('config/goals.yaml')); print(len(d.get('goals',[])), 'goals written')"
```

All three should contain real content, not placeholder text.

---

## Step 4 — Run the aspirational baseline

While the session is fresh, run a follow-up to capture your "1 in 100" anchoring data for Pattern Miner. This is a short additional conversation (5-10 minutes):

```bash
python core/orchestrator.py --provider ollama
```

In this session, ask the Synthesizer to run `write_aspirational_baseline`. It will ask you to describe:
- A period when you were at your best (1 in 100 good weeks)
- A period that was unusually hard (1 in 100 hard weeks)
- What your best days looked like (peak_days)
- What your floor days looked like (floor_days)

These become anchors that Pattern Miner uses from day one, before months of behavioral data accumulate.

**Note:** The aspirational baseline is a dated snapshot, not a permanent fixture. It will be updated as new highs and lows emerge and as the current-events context that shaped past memories shifts.

---

## Routing confirmation

Everything in this interview stays local:

| What | Goes where |
|---|---|
| Model inference (qwen3:14b) | `localhost:11434` — your machine |
| `config/prime_directive.md` | Local file, chmod 600 |
| `config/mission.md` | Local file, chmod 600 |
| `config/goals.yaml` | Local file, chmod 600 |
| `data/baselines/` (aspirational baseline) | Local file |
| Session context | Not persisted between CLI sessions |

`--provider ollama` ensures all LLM calls use Ollama regardless of what `routing.yaml` says. There is no cloud fallback when this flag is set.

---

## If something goes wrong

**Ollama connection refused:**
```bash
ollama serve   # start the server
```

**Model not found error:**
```bash
ollama pull qwen3:14b   # download the model (~8GB)
```

**`write_config` tool fails / files not populated:**
Check that you're in the right directory and the `.venv` is activated. The tool writes relative to the project root.

**Interview loops or gets confused:**
You can restart the session. The interviewer is stateless — it will start from the beginning. If partial content was written to the config files, review and edit them directly before restarting.

---

## After the interview

Once the three config files are populated and the aspirational baseline is written, run a quick verification session:

```bash
python core/orchestrator.py --provider ollama
```

Say something like "Good morning. What should I focus on today?" — the Synthesizer should respond with specific reference to your actual goals and values, not generic advice. If it gives generic advice, check that the config files were written correctly (Step 3 above).
