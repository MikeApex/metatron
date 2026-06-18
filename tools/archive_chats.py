#!/usr/bin/env python3
"""
Archive Claude Code chat sessions to human-readable markdown and raw JSONL copies.

Run from project root:
    python3 tools/archive_chats.py

Archives all new sessions (skips already-archived ones).

Source:  ~/.claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp/*.jsonl
Output:
  archive/transcripts/raw/{uuid}.jsonl    — verbatim JSONL copy
  archive/transcripts/{date} — {topic}.md — readable transcript
"""

import json
import re
import shutil
import sys
from pathlib import Path

SOURCE_DIR = Path.home() / ".claude/projects/-Users-md-homefolder-Desktop-multi-model-mcp"
PROJECT_ROOT = Path(__file__).parent.parent
RAW_DIR = PROJECT_ROOT / "archive/transcripts/raw"
READABLE_DIR = PROJECT_ROOT / "archive/transcripts"

# System-injected tags to strip from user messages (not typed by the human)
SYSTEM_TAG_PATTERNS = [
    re.compile(r"<ide_opened_file>.*?</ide_opened_file>", re.DOTALL),
    re.compile(r"<ide_selection>.*?</ide_selection>", re.DOTALL),
    re.compile(r"<system-reminder>.*?</system-reminder>", re.DOTALL),
    re.compile(r"<user-prompt-submit-hook>.*?</user-prompt-submit-hook>", re.DOTALL),
    re.compile(r"<command-name>.*?</command-name>", re.DOTALL),
]


def strip_system_tags(text: str) -> str:
    for pat in SYSTEM_TAG_PATTERNS:
        text = pat.sub("", text)
    return text.strip()


def load_session(path: Path) -> list[dict]:
    """Load JSONL, deduplicate by message id (keep last), return ordered entries."""
    entries_by_id: dict[str, dict] = {}
    ordered_ids: list[str] = []

    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            uid = entry.get("uuid") or entry.get("sessionId") or id(entry)
            if uid not in entries_by_id:
                ordered_ids.append(uid)
            entries_by_id[uid] = entry

    return [entries_by_id[uid] for uid in ordered_ids]


def extract_user_text(message: dict) -> str | None:
    """Extract human-typed text from a user message, stripping tool results and system tags."""
    content = message.get("content", "")
    if isinstance(content, str):
        cleaned = strip_system_tags(content)
        return cleaned or None

    texts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        # Skip tool results (automated, not typed by the user)
        if block.get("type") == "tool_result":
            continue
        if block.get("type") == "text":
            cleaned = strip_system_tags(block.get("text", ""))
            if cleaned:
                texts.append(cleaned)

    return "\n".join(texts).strip() or None


def extract_assistant_content(message: dict) -> list[tuple[str, str]]:
    """
    Return list of (kind, text) tuples from an assistant message.
    kind is 'text' or 'tool'.
    """
    content = message.get("content", [])
    if isinstance(content, str):
        return [("text", content)] if content.strip() else []

    parts = []
    for block in content:
        if not isinstance(block, dict):
            continue
        kind = block.get("type")
        if kind == "text":
            text = block.get("text", "").strip()
            if text:
                parts.append(("text", text))
        elif kind == "tool_use":
            name = block.get("name", "tool")
            inp = block.get("input", {})
            # Show a compact one-line summary
            if "command" in inp:
                summary = inp["command"].split("\n")[0][:120]
            elif "file_path" in inp:
                summary = inp["file_path"]
            elif "query" in inp:
                summary = inp["query"][:120]
            else:
                summary = str(inp)[:120]
            parts.append(("tool", f"{name} — {summary}"))
        # Skip 'thinking' blocks (internal reasoning, not output)

    return parts


def session_date_and_first_message(entries: list[dict]) -> tuple[str, str]:
    """Return (YYYY-MM-DD, first_user_message_snippet)."""
    date = "unknown"
    first_msg = "untitled"

    for entry in entries:
        if entry.get("type") not in ("user", "assistant"):
            continue
        ts = entry.get("timestamp", "")
        if ts and date == "unknown":
            date = ts[:10]

        if entry.get("type") == "user":
            msg = entry.get("message", {})
            text = extract_user_text(msg)
            if text and first_msg == "untitled":
                # Truncate to ~60 chars, clean for filename
                snippet = text.replace("\n", " ")[:60].strip()
                snippet = re.sub(r'[<>:"/\\|?*]', "", snippet)
                snippet = snippet.rstrip(". ")
                first_msg = snippet
                break

    return date, first_msg


def unique_output_path(readable_dir: Path, date: str, topic: str) -> Path:
    """Return a non-colliding path for the readable transcript."""
    base = f"{date} — {topic}"
    path = readable_dir / f"{base}.md"
    if not path.exists():
        return path
    i = 2
    while True:
        path = readable_dir / f"{base} ({i}).md"
        if not path.exists():
            return path
        i += 1


def render_markdown(entries: list[dict], session_id: str) -> str:
    date, topic = session_date_and_first_message(entries)
    lines = [f"# {date} — {topic}", f"*Session ID: {session_id}*", ""]

    last_role = None
    pending_tool_lines: list[str] = []

    def flush_tools():
        nonlocal pending_tool_lines
        if pending_tool_lines:
            lines.extend(pending_tool_lines)
            lines.append("")
            pending_tool_lines = []

    for entry in entries:
        etype = entry.get("type")
        if etype == "user":
            msg = entry.get("message", {})
            text = extract_user_text(msg)
            if not text:
                continue
            flush_tools()
            if last_role != "user":
                lines.append("---")
                lines.append("")
            lines.append(f"**You:** {text}")
            lines.append("")
            last_role = "user"

        elif etype == "assistant":
            msg = entry.get("message", {})
            parts = extract_assistant_content(msg)
            if not parts:
                continue

            for kind, content in parts:
                if kind == "text":
                    flush_tools()
                    if last_role != "assistant":
                        pass  # no separator needed between tool and text
                    lines.append(f"**Claude:** {content}")
                    lines.append("")
                    last_role = "assistant"
                elif kind == "tool":
                    pending_tool_lines.append(f"> *[{content}]*")

    flush_tools()
    return "\n".join(lines)


def archive_session(jsonl_path: Path) -> tuple[bool, str]:
    """Copy JSONL and write readable markdown. Returns (was_new, output_path)."""
    session_id = jsonl_path.stem
    raw_dest = RAW_DIR / jsonl_path.name

    # Skip if already archived
    if raw_dest.exists():
        return False, str(raw_dest)

    entries = load_session(jsonl_path)
    if not entries:
        return False, ""

    # Copy raw JSONL
    shutil.copy2(jsonl_path, raw_dest)

    # Write readable markdown
    date, topic = session_date_and_first_message(entries)
    out_path = unique_output_path(READABLE_DIR, date, topic)
    out_path.write_text(render_markdown(entries, session_id), encoding="utf-8")

    return True, str(out_path)


def main():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    READABLE_DIR.mkdir(parents=True, exist_ok=True)

    jsonl_files = sorted(SOURCE_DIR.glob("*.jsonl"))
    if not jsonl_files:
        print(f"No JSONL files found in {SOURCE_DIR}")
        sys.exit(0)

    new_count = 0
    for path in jsonl_files:
        was_new, out = archive_session(path)
        if was_new:
            new_count += 1
            print(f"  archived → {Path(out).name}")
        else:
            print(f"  skipped  (already archived) {path.stem}")

    print(f"\nDone. {new_count} new session(s) archived to archive/transcripts/")


if __name__ == "__main__":
    main()
