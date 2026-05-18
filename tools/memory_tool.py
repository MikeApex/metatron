"""
tools/memory_tool.py — search_memory tool wrapper.

Thin bridge between the orchestrator tool dispatch layer and core/memory.py.
The actual FAISS logic lives in core/memory.py; this file provides the
tool schema and the callable handler registered in orchestrator.register_tools().
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.memory import search_memory as _search_memory


def search_memory(query: str, k: int = 5) -> list[dict]:
    """
    Search past logs and journal entries semantically.

    Args:
        query: Natural language search query.
        k: Number of results to return (1–10).

    Returns:
        List of relevant past entries with text, source, date, and relevance score.
    """
    k = max(1, min(k, 10))
    return _search_memory(query=query, k=k)


SEARCH_MEMORY_SCHEMA = {
    "name": "search_memory",
    "description": (
        "Semantically search past log and journal entries to surface relevant context. "
        "Use when the user references something from the past ('how was I sleeping last month?', "
        "'when did I last mention the bookstore finances?', 'what did I think about that film?'). "
        "Returns the most relevant past entries ranked by semantic similarity."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language search query describing what to look for.",
            },
            "k": {
                "type": "integer",
                "description": "Number of results to return. Default 5, maximum 10.",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}
