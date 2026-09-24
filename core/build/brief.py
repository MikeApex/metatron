"""
core/build/brief.py — N10. The one file the reviewer and Mike both read.

Plan: archive/plans/build_vertical_plan_2026-09-24.md section 3 (N10, N8).

ONE FILE, TWO READERS, AND THAT IS WHY THE TABLE IS IN IT. `/build` spawns the
`adversarial-reviewer` agent with the same three-line prompt `/adversarial-review`
sends — a path, an effort level, a repo root — and nothing else. So the only way
the question table reaches the reviewer is BY BEING IN THE FILE IT IS HANDED
(finding 6). Rendering the table as a separate artifact and hoping the reviewer
opens it is the design that was rejected.

IT IS NOT REDACTED, and that is a change from v3, not an oversight. The v3 brief
was written ON THE VM and read on the Mac, so it crossed a boundary and had to
be masked. This brief is written on the Mac, in Mike's own session, from
artifacts already in that session's context — masking it would hide from Mike
what the session already holds, while costing the reviewer the evidence it
needs.

WHAT STILL HOLDS IS THE STRUCTURAL HALF. The renderer emits ONLY DECLARED
FIELDS. The inventory appears as source, form and period; a gap appears as the
words the Librarian wrote. No sample, no read row, no tool arguments. That was
the layer doing the real work in v3 too — the mask was only ever the proof that
it had worked.

THE REVIEW LANDS HERE, appended by the driver after N8, so nothing tracked is
written before [N9]. The `/adversarial-review` command itself is untouched: it
stays what it is, a tool for plans in archive/plans/.
"""

from __future__ import annotations

import json
import re
from datetime import datetime

from core.build import table as TBL

# ---------------------------------------------------------------------------
# N8's output contract, in one place
#
# THE REVIEWER EMITS MARKDOWN AND TWO CONSUMERS WANTED STRUCTURE, AND NOTHING
# CONVERTED BETWEEN THEM. `adversarial-reviewer.md` returns `Wrong:` / `Fails:`
# / `Costs:` prose under `## STRUCTURAL` and `## LOCAL`; append_review() below
# renders `finding['title']` and `finding['detail']`; and the send-back reads
# the defect text out of each finding. Three shapes, no parser — so the first
# structural finding at N8 either raised on the index or wrote `**?** —` into
# the brief, at the one node the send-back bound depends on.
#
# The parse lives HERE, next to the renderer, for the same reason
# coherence.parse_findings() lives beside its own report: the module that owns
# the artifact owns the shape of it. One canonical dict carries every key all
# three layers already ask for, so no consumer had to change.
# ---------------------------------------------------------------------------

REVIEW_SCHEMA = "review/1"

_BLOCK_RE = re.compile(r"^#{1,4}\s*(STRUCTURAL|LOCAL|NEW)\b", re.I)
_START_RE = re.compile(r"^(\d+)\.\s+(.*)$")
_FIELD_RE = re.compile(r"^\**(Wrong|Fails|Costs)\**\s*:\s*(.*)$", re.I)
_NONE_RE = re.compile(r"^\**\(?none\)?\**\.?$", re.I)
_VERDICT_RE = re.compile(r"^\**VERDICT\**\s*:\s*(.*)$", re.I | re.S)
_CONFIDENCE_RE = re.compile(r"\b(high|medium|speculative)\b\.?\s*$", re.I)


def parse_review(raw) -> dict:
    """
    The reviewer's markdown → the one shape the brief and the send-back read.

    Returns {schema, structural[], local[], verdict, unparsed}. Each finding
    carries every key a consumer already expects:

        wrong / fails / costs   the three sentences, verbatim
        title                   the `wrong` sentence — what append_review() bolds
        detail                  fails + costs + the reference line
        rank                    the reviewer's GLOBAL rank, preserved across the
                                two blocks, which is why numbering is
                                non-contiguous within one
        refs, confidence

    A dict in is passed through, so a caller that already has structure (a
    replayed artifact, a test) is not re-parsed. TOLERANT BY DESIGN: a report
    that does not match the format at all lands whole in `unparsed` rather than
    raising — the review is evidence, and losing it to a format change would be
    worse than rendering it plainly.
    """
    if isinstance(raw, dict):
        return raw
    text = _strip_fence(str(raw or ""))
    out = {"schema": REVIEW_SCHEMA, "structural": [], "local": [],
           "verdict": "", "unparsed": ""}
    if not text.strip():
        return out

    # The ten-defect escape hatch: the agent returns this line and nothing else.
    verdict = _VERDICT_RE.search(text)
    if verdict and not _BLOCK_RE.search(text):
        out["verdict"] = " ".join(verdict.group(1).split())
        out["structural"] = [{
            "rank": 1, "title": out["verdict"], "detail": "",
            "wrong": out["verdict"], "fails": "", "costs": "",
            "refs": "", "confidence": "high",
        }]
        return out

    block, current, seen_block = None, None, False
    for line in text.splitlines():
        stripped = line.strip()
        heading = _BLOCK_RE.match(stripped)
        if heading:
            current = _close(current, out, block)
            name = heading.group(1).lower()
            # A `## NEW` block is a verify round's new findings; they are
            # structural for our purposes — they go back to the Planner.
            block = "local" if name == "local" else "structural"
            seen_block = True
            continue
        if block is None:
            continue
        if _NONE_RE.match(stripped):
            continue

        start = _START_RE.match(stripped)
        if start:
            current = _close(current, out, block)
            current = {"rank": int(start.group(1)), "refs": start.group(2).strip(),
                       "wrong": "", "fails": "", "costs": ""}
            continue
        if current is None:
            continue

        field = _FIELD_RE.match(stripped)
        if field:
            current["_last"] = field.group(1).lower()
            current[current["_last"]] = field.group(2).strip()
        elif stripped and current.get("_last"):
            current[current["_last"]] = (
                current[current["_last"]] + " " + stripped).strip()
        elif stripped and not current["wrong"]:
            current["refs"] = (current["refs"] + " " + stripped).strip()

    _close(current, out, block)

    if not seen_block:
        out["unparsed"] = text.strip()
    return out


def _close(current: dict | None, out: dict, block: str | None) -> None:
    """Finish one finding and file it under its block."""
    if not current or not block:
        return None
    wrong = current.get("wrong") or current.get("refs") or ""
    costs = current.get("costs", "")
    confidence = _CONFIDENCE_RE.search(costs)
    detail = " ".join(p for p in (current.get("fails", ""), costs) if p).strip()
    if current.get("refs") and current.get("wrong"):
        detail = f"{detail} `{current['refs']}`".strip()
    out[block].append({
        "rank": current.get("rank", 0),
        "title": wrong,
        "detail": detail,
        "wrong": wrong,
        "fails": current.get("fails", ""),
        "costs": costs,
        "refs": current.get("refs", ""),
        "confidence": (confidence.group(1).lower() if confidence else ""),
    })
    return None


def _strip_fence(text: str) -> str:
    text = str(text or "").strip()
    if not text.startswith("```"):
        return text
    body = text.split("\n", 1)[1] if "\n" in text else ""
    return body.rsplit("```", 1)[0].strip()


def render(job: dict, question_set: dict, ledger: dict, plan: dict,
           estimate: dict | None = None) -> str:
    """The whole brief as markdown. Everything below [N9] depends on this file."""
    capability = plan.get("capability") or {}
    out: list[str] = [
        f"# Build brief — {capability.get('one_line') or job.get('gap') or '?'}",
        "",
        f"*Job `{job.get('job_id', '?')}` · persona `{job.get('persona', '?')}` · "
        f"mode {job.get('mode', 'construct')} · rendered "
        f"{datetime.now().isoformat(timespec='seconds')}.*",
        "",
        "*Read the question table before the plan. It is the audit of whether",
        "every question travelled and whether every plan item rests on one.*",
        "",
        "---",
        "",
    ]
    out += _gap(job)
    out += _capability(capability)
    out += _sources(plan)
    out += _integrations(plan)
    out += _files(plan)
    out += _registration(plan)
    out += _surface(plan)
    out += _variables(plan)
    out += _risks(plan)
    out += _tests(plan)
    out += _cost(estimate)
    out += ["---", ""]
    out += [TBL.render(question_set, ledger, plan), ""]
    return "\n".join(out)


def append_review(brief_text: str, review: dict) -> str:
    """
    The reviewer's two ranked blocks, appended by the driver.

    Appended rather than rendered into the body, so the file the reviewer READ
    and the file Mike reads are the same document plus one section — and it is
    obvious which part the reviewer could not have seen.
    """
    out = [brief_text.rstrip(), "", "---", "", "## Adversarial review", ""]
    for heading, key in (("Structural", "structural"), ("Local", "local")):
        findings = review.get(key) or []
        out += [f"### {heading}", ""]
        if not findings:
            out += ["*(none)*", ""]
            continue
        for position, finding in enumerate(findings, start=1):
            if isinstance(finding, dict):
                out.append(f"{position}. **{finding.get('title', '?')}** — "
                           f"{finding.get('detail', '')}")
            else:
                out.append(f"{position}. {finding}")
        out.append("")
    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Sections
# ---------------------------------------------------------------------------

def _gap(job: dict) -> list[str]:
    return [
        "## The gap", "",
        str(job.get("gap") or "*(not recorded)*"), "",
        f"*Trigger: {job.get('trigger') or 'not recorded'} · ticket "
        f"`{job.get('job_id', '?')}`.*", "",
    ]


def _capability(capability: dict) -> list[str]:
    return [
        "## What is proposed", "",
        f"- **Name** `{capability.get('id', '?')}` · kind "
        f"{capability.get('kind', '?')} · {capability.get('disposition', '?')}",
        f"- **In one line** {capability.get('one_line', '?')}",
        f"- **Generalises to** {capability.get('generalizes_to', '?')}",
        f"- **Runs** {capability.get('execution_mode', '?')}, budget "
        f"{capability.get('latency_budget_ms', '?')} ms",
        f"- **Why not an existing specialist** "
        f"{capability.get('disposition_evidence', '?')}",
        "",
    ]


def _sources(plan: dict) -> list[str]:
    entries = plan.get("information_sources") or []
    out = ["## Where it gets its information", "",
           "*This section becomes the agent file's own \"where to look\".*", ""]
    if not entries:
        return out + ["*(none declared)*", ""]
    out += ["| ledger row | tool | if the user lacks it |", "|---|---|---|"]
    for entry in entries:
        out.append(f"| {entry.get('row_id', '?')} | `{entry.get('tool', '?')}` "
                   f"| {entry.get('if_user_lacks_it', '?')} |")
    return out + [""]


def _integrations(plan: dict) -> list[str]:
    entries = plan.get("integrations") or []
    if not entries:
        return []
    out = ["## Outbound sources", "",
           "*An (M) item is something only Mike can do — registering a key. It "
           "is named here, before approval, not after.*", "",
           "| source | key is an (M) item | per call | per month | privacy |",
           "|---|---|---|---|---|"]
    for entry in entries:
        out.append(
            f"| {entry.get('source', '?')} "
            f"| {'YES — (M)' if entry.get('key_registration_is_m_item') else 'no'} "
            f"| {entry.get('cost_per_call', '?')} | {entry.get('cost_per_month', '?')} "
            f"| {entry.get('privacy_tier', '?')} |")
    return out + [""]


def _files(plan: dict) -> list[str]:
    entries = plan.get("files") or []
    out = ["## Files", "",
           "*The implementer's half is written in a sandbox worktree. The main "
           "session's half is Red and is written in this session, where each "
           "write prompts you.*", ""]
    if not entries:
        return out + ["*(none)*", ""]
    for half, label in (("implementer", "Implementer (sandbox worktree)"),
                        ("main_session", "This session (Red — prompts you)")):
        paths = [e.get("path") for e in entries
                 if isinstance(e, dict) and e.get("half") == half]
        out += [f"**{label}**", ""]
        out += [f"- `{p}`" for p in paths] or ["- *(none)*"]
        out += [""]
    return out


def _registration(plan: dict) -> list[str]:
    entries = plan.get("registration") or []
    if not entries:
        return []
    out = ["## Registration", "",
           "*Every one of these is written in this session, on disk, in the main "
           "tree. A half-wired agent is already in the tree today — that is what "
           "the matrix exists to end.*", ""]
    for entry in entries:
        if isinstance(entry, dict):
            out.append(f"- **{entry.get('what', '?')}** → `{entry.get('path', '?')}`"
                       + (f" — {entry['detail']}" if entry.get("detail") else ""))
        else:
            out.append(f"- {entry}")
    return out + [""]


def _surface(plan: dict) -> list[str]:
    entries = plan.get("surface_map") or []
    out = ["## Surface map", "",
           "*Every operation carries a disposition. Absence is indistinguishable "
           "from an oversight, so nothing may be silently missing.*", "",
           "| entity | operation | status | note |", "|---|---|---|---|"]
    for entry in entries:
        note = entry.get("reason") or entry.get("ticket") or ""
        out.append(f"| {entry.get('entity', '?')} | {entry.get('operation', '?')} "
                   f"| {entry.get('status', '?')} | {note} |")
    return out + [""]


def _variables(plan: dict) -> list[str]:
    entries = plan.get("variables") or []
    if not entries:
        return []
    out = ["## New variables", "", "| name | scope | home | if absent |",
           "|---|---|---|---|"]
    for entry in entries:
        out.append(f"| `{entry.get('name', '?')}` | {entry.get('scope', '?')} "
                   f"| {entry.get('home', '?')} "
                   f"| {entry.get('if_user_lacks_it', '?')} |")
    return out + [""]


def _risks(plan: dict) -> list[str]:
    entries = plan.get("risks") or []
    out = ["## Risks", "",
           "*A tool grant outside the Librarian's read set is listed here rather "
           "than refused. Your approval is the control — so the gate's job is to "
           "make sure you were actually shown it.*", ""]
    out += [f"- {r}" for r in entries] or ["- *(none declared)*"]
    return out + [""]


def _tests(plan: dict) -> list[str]:
    entries = plan.get("tests") or []
    acceptance = plan.get("acceptance") or {}
    out = ["## Tests and acceptance", ""]
    out += [f"- `{t}`" for t in entries] or ["- *(none declared)*"]
    out += ["",
            "**Acceptance runs on two personas**, on the VM, after deploy: "
            f"`{acceptance.get('primary', 'mike')}` and "
            f"`{acceptance.get('fixture', '?')}` — the second has no history, "
            "which is where the \"if the user lacks it\" branch actually fires.",
            ""]
    return out


def _cost(estimate: dict | None) -> list[str]:
    if not estimate:
        return []
    return [
        "## Cost", "",
        f"- Subagent calls expected: {estimate.get('subagent_calls', '?')}",
        f"- Files touched: {estimate.get('files_touched', '?')}",
        f"- Tools granted: {estimate.get('tools_granted', '?')}",
        "",
        "*Build bills nothing per token on the subscription. What this costs is "
        "window — visible to whoever is sitting in the session — and it is "
        "measured after the fact from the transcript, not guessed here.*",
        "",
    ]


def write(job_id: str, text: str, persona: str | None = None):
    """Land the brief in the JOB DIRECTORY, not in archive/plans/."""
    from core.build import jobs as J
    return J.write_text(job_id, "brief.md", text, persona)


def debug_dump(payload: dict) -> str:
    """The raw artifact, for a session that needs to see what the renderer read."""
    return json.dumps(payload, indent=2, ensure_ascii=False, default=str)
