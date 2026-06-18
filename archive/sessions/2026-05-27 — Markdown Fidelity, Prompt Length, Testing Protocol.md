# 2026-05-27 — Markdown Fidelity, Prompt Length, Testing Protocol

---

## Topics covered

### Markdown structure and formatting
- Explained heading hierarchy (`#` through `####`), text formatting (`**bold**`, `*italic*`, backticks), lists, code blocks, tables, and horizontal rules
- Clarified that colors in VS Code are editor theme overlays, not Markdown features — not a special notation to learn

### How markdown ordering affects model output
- Primacy and recency bias: beginning and end of a prompt are weighted most heavily
- "Lost in the middle" problem: content buried in long documents is under-attended
- Later instructions tend to override earlier ones when conflicts arise
- Heading hierarchy creates semantic grouping — a rule under `## Confidentiality` carries different authority than one in a bullet list
- First sentence sets a frame the model tends to maintain throughout
- Example placement late in a file anchors output style more than explicit instructions

### Ideal file length for current models
- Individual agent files in this project (300–800 tokens) are well within the reliable attention zone
- The real risk is **cumulative prompt length per session**: Constitution + Prime Directive + Mission + Goals + agent file + tool schemas + conversation history stacking to 10K–20K tokens
- Thresholds: <8K reliable; 8K–15K monitor; 15K–30K significant risk; >30K design problem

### Behavioral audit of agent files
- Syntactic audit (structure, word count) is necessary but not sufficient
- Behavioral audit is more valuable: adversarial probing, instruction stress tests, omission tests, conversation-length constraint hold
- Agreed: a reusable `tests/agent_audit_template.md` is the right artifact

---

## Changes made to testing protocol

### `tests/testing_framework_notes.md`
Added "Cumulative prompt length tracking" section:
- Why cumulative length (not individual file length) is the risk
- Exact API fields to read per provider: `response.usage.input_tokens` (Anthropic), `response.usage.prompt_tokens` (OpenAI), `response.usage_metadata.prompt_token_count` (Gemini), `response.prompt_eval_count` (Ollama)
- Warning thresholds table (8K / 15K / 30K) with interpretation for each
- Implementation target: orchestrator accumulates and logs per session in Phase 5

### `tests/agent_audit_template.md` — new file
7-probe reusable behavioral checklist for any agent file:
1. Identity and role boundary
2. Confidentiality hold (4 attack vectors: tools, instructions, model identity, inter-agent routing)
3. Instruction priority under conflict
4. Omission handling
5. Sensitive data routing signal
6. Conversation-length constraint hold (re-probe at turn 15+)
7. Prompt budget check (token counts per turn during the length probe)

Includes sign-off block with Pass/Conditional/Fail.

### `tests/phase5_testing_plan.md`
Added two new checks:
- **Check 10:** Every specialist module must clear `agent_audit_template.md` before being considered complete
- **Check 11:** Orchestrator must log cumulative input tokens per turn; multi-agent sessions must stay under 15K; turns over 8K emit a warning log line

---

## Key decisions

- Tracking prompt length via API response usage fields is the only reliable method — local estimators (tiktoken etc.) can be off 10–20% depending on the model's tokenizer
- Behavioral audit and prompt budget check are now gating requirements for Phase 5 specialist completion, not optional
- No code changes made this session — all changes are to test protocol files
