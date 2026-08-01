"""
core/background.py — run best-effort work off the caller's thread.

Some work is genuinely fire-and-forget: nothing reads its result and a failure is
already tolerated. Memory indexing is the case this exists for — it was called
synchronously inside write_log() and write_journal(), which run during tool
dispatch, so every write added an embedding round trip (~150-200ms on the VM) to
the user's response for a result nobody waits on.

Deliberately a single worker: this is background work and must never compete
with the pipeline for cores. Queued tasks are dropped rather than blocking if
the worker is saturated, because a slow queue must not become back-pressure on
a user's session.
"""

from __future__ import annotations

import logging
import threading
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

logger = logging.getLogger(__name__)

_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="background")
_lock = threading.Lock()
_pending = 0
_MAX_PENDING = 32


def run_background(fn: Callable[[], None], label: str = "task") -> None:
    """Schedule fn to run off this thread. Never raises, never blocks."""
    global _pending
    with _lock:
        if _pending >= _MAX_PENDING:
            logger.warning(f"[background] queue full — dropping {label}")
            return
        _pending += 1

    def _wrapped() -> None:
        global _pending
        try:
            fn()
        except Exception as exc:
            logger.warning(f"[background] {label} failed: {exc}")
        finally:
            with _lock:
                _pending -= 1

    try:
        _EXECUTOR.submit(_wrapped)
    except Exception as exc:
        with _lock:
            _pending -= 1
        logger.warning(f"[background] could not schedule {label}: {exc}")
