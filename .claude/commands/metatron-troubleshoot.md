---
description: Single-exchange troubleshoot on Metatron pipeline — diagnose a specific conversation exchange by DATE and SEQ
---

Metatron — Single Exchange Troubleshoot

## Step 1 — resolve the parameters before running anything

```
DATE    = $1
SEQ     = $2
ISSUE   = $3
PERSONA = $4
```

**Do not trust the block above.** Positional substitution fails when the user phrases the request in prose or puts the command at the end of the message — a real invocation on 2026-08-02 produced `DATE = 2`, `SEQ = $2`, `ISSUE = $3`. If any value above is unsubstituted, empty, or not in the expected shape, **read the user's message and extract them yourself**:

- `DATE` — full ISO `YYYY-MM-DD`. Expand shorthand ("Aug 2" → `2026-08-02`) using today's date for the year.
- `SEQ` — zero-padded 3 digits (`21` → `021`).
- `PERSONA` — defaults to `mike` if not given. Nine personas exist; the tool is not Mike-only.
- `ISSUE` — the user's actual question, quoted at the end of this file.

State the four resolved values back to the user in one line before running the pull, so a misparse is caught immediately rather than after a confusing empty result.

Title the chat by date/seq for archiving.

## Step 2 — context

Metatron pipeline on `metatron-vm` (`us-central1-a`, project `metatron-ai-499810`). Coordinator (Flash-Lite) → parallel specialists → Synthesizer (Pro).

Paths are **persona-scoped** (since the 2026-07-28 persona unification):

| What | Path |
|---|---|
| Conversation log | `data/personas/{PERSONA}/conversations/{DATE}.jsonl` |
| Pipeline trace | `data/personas/{PERSONA}/traces/{DATE}.jsonl` |
| Server logs | `journalctl -u metatron-server` |

> **Two legacy directories still exist and will mislead you.** `data/conversations/` survives but now contains only `metatron.db` (the live Android chat DB) — so a stale path fails with `FileNotFoundError` on the *file*, which reads like a wrong date rather than a wrong path. `data/traces/` also survives, holding real-looking JSONL up to 2026-07-27. Reading either returns silence or stale data, never an obvious error. Use the persona-scoped paths above and nothing else.

## Step 3 — single data pull

Fill in the four variables on the first line, then run. `--tunnel-through-iap` is required: the `metatron-net` VPC built during the 2026-07-31 rebuild has no public SSH ingress.

```bash
PERSONA="mike"; DATE="YYYY-MM-DD"; SEQ="021"

gcloud compute ssh metatron-vm --zone=us-central1-a --project=metatron-ai-499810 --tunnel-through-iap --command "
cd ~/multi-model-mcp
PERSONA='$PERSONA' DATE='$DATE' SEQ='$SEQ' python3 - <<'PYEOF'
import json, os, subprocess, datetime

PERSONA = os.environ['PERSONA']
DATE    = os.environ['DATE']
SEQ     = os.environ['SEQ'].zfill(3)
BASE    = f'data/personas/{PERSONA}'

# ---- 1. Conversation record ------------------------------------------------
conv_path = f'{BASE}/conversations/{DATE}.jsonl'
if not os.path.exists(conv_path):
    print(f'No conversation log at {conv_path}')
    d = f'{BASE}/conversations'
    print('Available dates:', sorted(os.listdir(d)) if os.path.isdir(d) else f'({d} does not exist)')
    raise SystemExit(1)

with open(conv_path) as f:
    lines = [json.loads(l) for l in f if l.strip()]

entry = next((l for l in lines if str(l.get('seq','')).zfill(3) == SEQ), None)
if not entry:
    print(f'SEQ {SEQ} not found in {conv_path}')
    print('Available seqs:', [str(l.get('seq')) for l in lines])
    raise SystemExit(1)

print('=== CONVERSATION RECORD ===')
print(json.dumps(entry, indent=2)[:6000])

# ---- 2. Server logs, +/-3 min ----------------------------------------------
ts    = datetime.datetime.fromisoformat(entry['ts'])
since = (ts - datetime.timedelta(minutes=3)).strftime('%H:%M:%S')
until = (ts + datetime.timedelta(minutes=3)).strftime('%H:%M:%S')
print(f'\n=== SERVER LOGS {since}-{until} ===')
res = subprocess.run(['sudo','journalctl','-u','metatron-server',
                      '--since',since,'--until',until,'--no-pager'],
                     capture_output=True, text=True)
for line in res.stdout.splitlines():
    if 'GET /monitor' in line or 'GET /health' in line:
        continue
    print(line)

# ---- 3. Pipeline trace, +/-2 min window ------------------------------------
# A window, not an exact HH:MM prefix match: the trace is stamped at pipeline
# START and the conversation record at completion. A 20-30s exchange straddles a
# minute boundary often, and an exact match then reports 'no trace found' for a
# trace that exists.
lo, hi = ts - datetime.timedelta(minutes=2), ts + datetime.timedelta(minutes=2)
def in_window(r):
    try:
        return lo <= datetime.datetime.fromisoformat(r.get('ts','')) <= hi
    except Exception:
        return False

trace_path = f'{BASE}/traces/{DATE}.jsonl'
print('\n=== PIPELINE TRACE ===')
if not os.path.exists(trace_path):
    print(f'No trace file at {trace_path}')
    raise SystemExit(0)

with open(trace_path) as f:
    records = [json.loads(l) for l in f if l.strip()]
cands = [r for r in records if in_window(r)]
if not cands:
    print(f'No trace in +/-2min of {ts}. Last 10 trace timestamps:')
    print('  ', [r.get('ts') for r in records][-10:])

for trace in cands:
    print(f\"\n>>> trace ts={trace.get('ts')}\")
    for step in trace.get('pipeline', []):
        print(f\"\n--- {step['agent']} | {step.get('model','')} | {step.get('duration_ms','')}ms ---\")
        # What the agent was actually TOLD. Head/routing layer get recent_context
        # (system clock, logs, tracker); specialists get far less. Comparing these
        # across agents is often the fastest route to a root cause.
        for k, v in (step.get('context_sections') or {}).items():
            print(f'   [ctx:{k}] {str(v)[:220]}')
        for t in step.get('turns', []):
            print(f\"  turn {t['turn']}: in={t.get('input_tokens')} out={t.get('output_tokens')}\")
            for tc in t.get('tool_calls', []):
                print(f\"    TOOL {tc['name']}({json.dumps(tc.get('args',{}))[:220]})\")
                print(f\"      -> {str(tc.get('result_preview',''))[:300]}\")
        for sub in step.get('subagents', []):
            d = {k: v for k, v in sub.items() if k != 'context_sections'}
            print(f'  SUBAGENT {json.dumps(d)[:700]}')
PYEOF
"
```

If SSH fails with `Connection is already closed` / `ConnectionCreationError`, that is a transient IAP tunnel drop — just retry.

## Step 4 — what to look for

Read the three sections in order.

**Conversation record** — does the response address the user's actual message? Watch for hedging ("minor snag", "I don't have that") signalling a silent specialist failure, and for confident confirmations ("that's set", "I've saved it") that the trace does not support.

**Server logs:**
- `[PIPELINE] X failed: Agent not found: .../X.md` → X is what the Coordinator emitted; a normalization miss if it differs from the real filename
- `[SECURITY] Output filter: 'X' found` → Synthesizer response suppressed; check whether the user used that term first (false positive)
- `[context] ambient load failed` → no live date/time/weather for Coordinator/Synthesizer
- `[context] clock line failed` → specialists lost their system clock; expect invented dates in any dated write
- `[vertex_cache] creation failed (N tokens)` → uncached; not a functional failure if N < 4096
- `[vertex_cache] 404 cached content metadata` → stale cache ID reused after expiry
- `[fire_and_forget] diarist failed` → journal not updated
- `[token_budget] OVER_8K turn=N` → cumulative input growth; a high turn count here is the signal for turn-burn
- `[spend_guard]` → rate or spend limit alerting/refusing

**Pipeline trace:**
- **Turn count per agent.** Coordinator should be 1. Specialists doing 5–8 internal turns is the real cost and latency driver — check what the extra turns are *doing* before assuming routing is at fault.
- **`Error calling tool 'X': … Correct usage: …`** → the model got a signature wrong. One occurrence followed by success is healthy self-correction. Repeated failures on the same tool means the agent file describes it differently from its real contract.
- **`Error: 'X' is not allowed`** → a permission denial, not a bug in the call. Usually means the agent is instructed to do something it has no working capability for — see [archive/plans/agent_capability_gap_2026-08-02.md](../../archive/plans/agent_capability_gap_2026-08-02.md).
- **`[TOOL FAILURES — these actions did NOT complete]`** in a specialist's output → writes that never landed. If the Synthesizer told the user it succeeded anyway, that is the finding.
- **`[ctx:...]` sections** — compare across agents. Missing `recent_context` or `clock` explains invented dates and lost context. A specialist gets `agent_file`, `goals`, `clock`; head/routing agents get much more.
- Missing specialist in pipeline steps → it failed before the trace was written
- Synthesizer calling `run_subagent` → a recovery attempt; check whether the result arrived before the response streamed
- `write_context_tracker` absent from Synthesizer tool calls → context tracker is stale
- Synthesizer output `""` → text-discard bug in the streaming thought_signature path

## Step 5 — report

Findings in this format:

> (component) failed/took (time) because (reason).
> Routing was (correct/incorrect) because (reason).
> Synthesizer response (addressed/missed) the user's need because (reason).

Pair each technical finding with a plain-language statement of what it meant for the user in practice — keep both, and do not drop the specifics when restating plainly.

Before proposing any fix, run the **Mandatory Pre-Edit Context Check** in `CLAUDE.md`: `SESSION.md`, the active roadmap, and the file-ownership rules. `config/agents/*.md` are ordinary editable config — the post-review freeze was lifted 2026-08-02 — but they are the product and they are token-sensitive, so keep additions short.

**Fix it here if you can, and file nothing.** A one-file fix found by a troubleshoot belongs in this session, not in `DEV_BACKLOG.md`. File only what a user would notice or what blocks the roadmap.

**When it is bigger than that, hand it to `/fix` directly — do not retype the diagnosis.** `/fix` accepts a troubleshoot finding as its input: this command answers *what went wrong*, `/fix` answers *make this change*. Pass the finding, the file(s) implicated, and what was already ruled out, so step 2's premise check starts from evidence rather than from a restatement. (`.claude/commands/fix.md` carries the same line pointing back here, so neither drifts from the other.)

---

The issue reported for this exchange: $3
