#!/usr/bin/env python3
"""Stop hook: report this session's real billed token total.

`[H8].2`. The work-block gate in the throughput plan requires an estimate up
front and an actual at close-out. On 2026-08-13 the estimate was 45-60k and the
actual 438k -- a 7x miss -- because **a model estimating its own context growth
is not measuring the billed total**. Context growth is what the model can feel;
billed tokens are cache reads plus cache writes plus input plus output across
every API request, which is a much larger number and is not introspectable.

So the arithmetic moves to the harness. Zero model tokens, deterministic, and it
gives every future estimate something to be checked against.

**Dedup by `requestId` is load-bearing, not tidiness.** The transcript writes one
assistant record per content block, so a turn with text plus a tool call yields
two records carrying the *same* usage object. Measured on this project's own
session 93462e3b: 41 assistant records against 25 real requests, and a naive
per-record sum reported 3,496,735 tokens against a true 2,006,891 -- **1.74x
over**. That is the `worker_ledger.py` failure class exactly (a ledger that
reported confidently and measured the wrong thing), so it is checked here rather
than assumed: the duplicate records were confirmed to carry byte-identical usage,
19 of 19.

Sidechain (subagent) turns are totalled separately. A work block that delegated
needs to see what the delegation cost, not a merged figure.

Writes a one-line JSON record per stop to `.claude/token_ledger.jsonl` so the
estimate-vs-actual history survives the session, and prints the running total to
the window.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

# The four usage fields that are actually billed. `cache_creation` /
# `iterations` / `server_tool_use` are breakdowns of these, not additions to
# them -- summing them too would double-count. Verified against the live shape:
# every record's `iterations` summed exactly to its top-level figures.
BILLED = (
    "input_tokens",
    "cache_creation_input_tokens",
    "cache_read_input_tokens",
    "output_tokens",
)

# **A raw sum of those four is not a usable number, and reporting one would have
# repeated this project's own mistake in a new costume.** Measured on the
# session that wrote this hook: 3,039k "billed" tokens, of which 2,914k -- 96%
# -- were cache *reads*, which bill at a tenth of the input rate. A headline
# figure that is 96% made of the cheapest thing tells a work-block gate almost
# nothing, and would make every estimate look catastrophically wrong.
#
# So the total below is weighted into **input-token equivalents**: each field
# scaled by its price ratio relative to plain input. These are *ratios*, not
# dollar prices -- deliberately, per `CLAUDE.md`'s standing rule against
# recording values with a short half-life. Ratios are a property of the caching
# design; per-MTok prices change.
#
# Cache-write weight is chosen per record from the `cache_creation` breakdown
# rather than assumed: the 5m and 1h TTLs are priced differently (1.25x vs 2x),
# and the record says which bucket the tokens landed in. This session's writes
# were entirely `ephemeral_1h`, so assuming 5m would have understated them 60%.
W_INPUT = 1.0
W_CACHE_READ = 0.1
W_CACHE_WRITE_5M = 1.25
W_CACHE_WRITE_1H = 2.0
# Output is priced per model, not per cache tier. 5.0 is Opus 5's ratio
# ($25 out / $5 in). Sessions on another model will be wrong in the output term
# only -- the model is recorded per record so this can be made per-model if a
# second model ever runs here.
W_OUTPUT_BY_MODEL = {"claude-opus-5": 5.0, "claude-sonnet-5": 5.0}
W_OUTPUT_DEFAULT = 5.0


def _totals(transcript_path: str) -> dict:
    """Billed totals for a transcript, deduplicated by requestId."""
    main: dict[str, dict] = {}
    side: dict[str, dict] = {}
    if not transcript_path or not os.path.exists(transcript_path):
        return {}

    try:
        with open(transcript_path, errors="ignore") as fh:
            for line in fh:
                # Cheap prefilter -- these transcripts reach tens of MB.
                if '"assistant"' not in line:
                    continue
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                if rec.get("type") != "assistant":
                    continue
                message = rec.get("message") or {}
                usage = message.get("usage")
                if not isinstance(usage, dict):
                    continue
                # A record with no requestId cannot be deduplicated against
                # anything, so it is keyed by its own uuid and counted once.
                key = rec.get("requestId") or rec.get("uuid") or repr(usage)
                bucket = side if rec.get("isSidechain") else main
                bucket[key] = (usage, message.get("model"))
    except OSError:
        return {}

    def rollup(bucket: dict) -> dict:
        out = {f: 0 for f in BILLED}
        weighted = 0.0
        for usage, model in bucket.values():
            for f in BILLED:
                out[f] += usage.get(f, 0) or 0

            creation = usage.get("cache_creation") or {}
            write_1h = creation.get("ephemeral_1h_input_tokens", 0) or 0
            write_5m = creation.get("ephemeral_5m_input_tokens", 0) or 0
            # Fall back to the flat field when the breakdown is absent, priced
            # at the cheaper 5m rate so the estimate never overstates.
            if not (write_1h or write_5m):
                write_5m = usage.get("cache_creation_input_tokens", 0) or 0

            weighted += (
                (usage.get("input_tokens", 0) or 0) * W_INPUT
                + (usage.get("cache_read_input_tokens", 0) or 0) * W_CACHE_READ
                + write_5m * W_CACHE_WRITE_5M
                + write_1h * W_CACHE_WRITE_1H
                + (usage.get("output_tokens", 0) or 0)
                * W_OUTPUT_BY_MODEL.get(model, W_OUTPUT_DEFAULT)
            )

        out["requests"] = len(bucket)
        out["raw_total"] = sum(out[f] for f in BILLED)
        out["weighted"] = round(weighted)
        return out

    return {"main": rollup(main), "sidechain": rollup(side)}


def _fmt(n: int) -> str:
    """148,231 -> '148.2k'. The window has one line; k is the readable unit."""
    return f"{n / 1000:.1f}k" if n >= 1000 else str(n)


def _append_ledger(root: Path, payload: dict, totals: dict) -> None:
    """Append one record. Never raises -- a ledger write must not break a stop."""
    try:
        ledger = root / ".claude" / "token_ledger.jsonl"
        ledger.parent.mkdir(parents=True, exist_ok=True)
        with open(ledger, "a") as fh:
            fh.write(json.dumps({
                "session_id": payload.get("session_id"),
                "cwd": payload.get("cwd"),
                "main": totals["main"],
                "sidechain": totals["sidechain"],
            }) + "\n")
    except (OSError, KeyError, ValueError):
        pass


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except ValueError:
        return 0  # malformed input is never a reason to interfere with a stop

    totals = _totals(payload.get("transcript_path", ""))
    if not totals or not totals["main"]["requests"]:
        return 0

    root = Path(os.environ.get("CLAUDE_PROJECT_DIR", ".")).resolve()
    _append_ledger(root, payload, totals)

    m, s = totals["main"], totals["sidechain"]
    # The weighted figure leads because it is the one an estimate can be
    # checked against; the raw sum trails it so the gap stays visible rather
    # than being quietly smoothed away.
    msg = f"[tokens: {_fmt(m['weighted'])} weighted over {m['requests']} requests"
    if s["requests"]:
        msg += f" | subagents {_fmt(s['weighted'])} over {s['requests']}"
    msg += (
        f" | raw {_fmt(m['raw_total'])}"
        f" = in {_fmt(m['input_tokens'])}"
        f" · cache-write {_fmt(m['cache_creation_input_tokens'])}"
        f" · cache-read {_fmt(m['cache_read_input_tokens'])}"
        f" · out {_fmt(m['output_tokens'])}]"
    )
    print(json.dumps({"systemMessage": msg}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
