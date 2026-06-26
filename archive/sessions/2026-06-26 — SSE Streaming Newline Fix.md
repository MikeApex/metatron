# 2026-06-26 — SSE Streaming Newline Fix

## What was fixed

**Bug:** Streaming responses from Metatron were showing truncated text, missing content mid-sentence, and adjacent chunks splicing together without expected whitespace or punctuation (e.g. "June 26, 202I'm here, Mike.").

**Root cause:** When the LLM streams a chunk containing a literal newline character (e.g. `"June 26, 2026.\nI'm here,"`), the server embedded it directly into the SSE `data:` line:
```
data: June 26, 2026.
I'm here,

```
The client's `buf.split('\n')` parser treated the second line (`I'm here,`) as a non-`data:`-prefixed line and silently dropped it. Text after any newline in a chunk was lost.

## Changes

**[core/server.py](../../core/server.py)** (line ~185) — escape `\r` and `\n` in text chunks before embedding in the SSE `data:` line:
```python
safe = item.replace('\r', '').replace('\n', r'\n')
yield f"data: {safe}\n\n"
```
Control tokens (`[DONE]`, `[RETRACT]`, `[ERROR]`) emitted in separate branches — unaffected.

**[static/index.html](../../static/index.html)** (line ~476) — unescape `\n` sequences when accumulating received text:
```javascript
accumulated += payload.replace(/\\n/g, '\n');
```

## Deployment

Committed `ba84c6d`, deployed to VM via `./deploy.sh`. Hard reload required on client to pick up the `static/index.html` change.

## Outcome

User confirmed fix working: "Looks better."

## Deferred / follow-on

None. Standalone fix.
