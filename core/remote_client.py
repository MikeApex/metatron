"""
core/remote_client.py — terminal client that talks to the running server.

Without this, `python core/orchestrator.py` runs the pipeline in-process on the
local machine: it writes to *this* machine's data/personas/{persona}/ tree, never
touches the server's SQLite store, and never notifies other clients. Used
alongside the phone and browser that is not "a fourth client" — it is a second,
parallel history for the same person on a different machine, which is the same
split-brain the persona work exists to prevent.

This module connects to the server's WebSocket instead, so the terminal becomes a
real client: same server, same database, same broadcast. Messages typed here
appear on the phone and in the browser, and vice versa.

Why WebSocket rather than the SSE endpoint: only the WebSocket path calls
_save_exchange() and manager.broadcast(). POST /session/stream writes the daily
JSONL log but neither persists to the shared store nor notifies anyone, so it
would fix the split tree while leaving the terminal invisible to other devices.

Usage (via the orchestrator CLI) — remote is the default for coordinator:
    python core/orchestrator.py --persona mike
    python core/orchestrator.py --persona mike --server https://host:8001
    python core/orchestrator.py --persona mike --local     # in-process, no sync
"""

from __future__ import annotations

import asyncio
import json
import ssl
import sys
import threading
import uuid

DEFAULT_SERVER = "https://metatron-vm.tail0acc5d.ts.net:8001"

# ANSI — the terminal is the one surface where distinguishing local from remote
# activity matters, since foreign messages arrive unprompted mid-session.
_DIM = "\033[2m"
_CYAN = "\033[36m"
_YELLOW = "\033[33m"
_GREEN = "\033[32m"
_RESET = "\033[0m"


def _ws_url(server: str, persona: str) -> str:
    base = server.rstrip("/")
    if base.startswith("https://"):
        base = "wss://" + base[len("https://"):]
    elif base.startswith("http://"):
        base = "ws://" + base[len("http://"):]
    return f"{base}/ws?persona={persona}"


def _ssl_context(url: str, insecure: bool):
    if not url.startswith("wss://"):
        return None
    ctx = ssl.create_default_context()
    if insecure:
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
    return ctx


async def _run(persona: str, server: str, provider: str | None, insecure: bool) -> None:
    try:
        import websockets
    except ImportError:
        print("Remote mode needs the 'websockets' package: pip install websockets",
              file=sys.stderr)
        raise SystemExit(1)

    url = _ws_url(server, persona)
    print(f"\nLife Manager — {persona} {_DIM}(remote: {server}){_RESET}")

    try:
        conn = await websockets.connect(url, ssl=_ssl_context(url, insecure), max_size=None)
    except Exception as exc:
        print(f"\nCould not reach the server at {server}\n  {exc}\n\n"
              f"Check the server is running and Tailscale is up. To run the pipeline\n"
              f"locally instead, pass --local (note: that writes to this machine, not\n"
              f"the server, and does not sync with the phone or browser).",
              file=sys.stderr)
        raise SystemExit(1)

    # Exchange ids this terminal originated, so foreign traffic can be labelled.
    own: set[str] = set()
    pending: dict[str, list[str]] = {}
    streaming_own = False

    async def receive() -> None:
        nonlocal streaming_own
        async for raw in conn:
            msg = json.loads(raw)
            kind = msg.get("type")
            xid = msg.get("exchange_id")

            if kind == "ping":
                continue

            if kind == "history":
                msgs = msg.get("messages", [])
                if msgs:
                    print(f"{_DIM}--- last {len(msgs)} exchange(s) from the shared history ---{_RESET}")
                    for m in msgs[-5:]:
                        print(f"{_DIM}  you: {m['user'][:90]}{_RESET}")
                        print(f"{_DIM}   me: {m['assistant'][:90]}{_RESET}")
                    print(f"{_DIM}---{_RESET}")
                print("\nType a message and press Enter. Ctrl+C or 'exit' to quit.\n")
                _prompt()

            elif kind == "stream_start":
                # Another device is talking. This is the sync signal.
                print(f"\n{_CYAN}[from another device] {msg.get('user','')}{_RESET}")
                pending[xid] = []

            elif kind == "chunk":
                if xid in own:
                    if not streaming_own:
                        # Label the reply. Without this it is indistinguishable
                        # from the terminal's echo of what you just typed.
                        streaming_own = True
                        sys.stdout.write(f"\n{_GREEN}")
                    sys.stdout.write(msg.get("text", ""))
                    sys.stdout.flush()
                else:
                    pending.setdefault(xid, []).append(msg.get("text", ""))

            elif kind == "done":
                if xid in own:
                    streaming_own = False
                    print(f"{_RESET}\n")
                    _prompt()
                else:
                    text = "".join(pending.pop(xid, []))
                    if text:
                        print(f"{_CYAN}{text}{_RESET}\n")
                    _prompt()

            elif kind == "retract":
                pending.pop(xid, None)
                if xid in own:
                    streaming_own = False
                print(f"\n{_YELLOW}[response withheld]{_RESET}\n")
                _prompt()

            elif kind == "error":
                print(f"\n{_YELLOW}[error] {msg.get('text','(no detail)')}{_RESET}\n")
                _prompt()

            elif kind == "message":
                # Catch-up record for an exchange completed while disconnected.
                if xid not in own:
                    print(f"\n{_CYAN}[from another device] {msg.get('user','')}{_RESET}")
                    print(f"{_CYAN}{msg.get('assistant','')}{_RESET}\n")
                    _prompt()

    def _prompt() -> None:
        sys.stdout.write("> ")
        sys.stdout.flush()

    async def send_loop() -> None:
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue = asyncio.Queue()

        # A DAEMON thread, not run_in_executor. sys.stdin.readline() is an
        # uninterruptible syscall; the default executor's threads are
        # non-daemon, so Ctrl-C would raise in the main thread and then hang
        # forever waiting for the reader to return.
        def _reader() -> None:
            while True:
                line = sys.stdin.readline()
                loop.call_soon_threadsafe(queue.put_nowait, line)
                if not line:
                    return

        threading.Thread(target=_reader, daemon=True).start()

        while True:
            line = await queue.get()
            if not line:
                break
            text = line.strip()
            if not text:
                _prompt()
                continue
            if text.lower() in ("exit", "quit"):
                break
            xid = str(uuid.uuid4())
            own.add(xid)
            await conn.send(json.dumps({
                "type": "send",
                "exchange_id": xid,
                "input": text,
                "provider": provider,
            }))

    recv_task = asyncio.create_task(receive())
    send_task = asyncio.create_task(send_loop())
    try:
        done, pending_tasks = await asyncio.wait(
            {recv_task, send_task}, return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending_tasks:
            task.cancel()
    finally:
        await conn.close()


def run_interactive_remote(persona: str, server: str | None = None,
                           provider: str | None = None, insecure: bool = True) -> None:
    """
    Interactive REPL against the running server.

    insecure defaults to True: the server presents a Tailscale certificate and
    the rest of the tooling (curl, deploy checks) already uses -k against it.
    Transport is still encrypted, and Tailscale is the only route to the host.
    """
    try:
        asyncio.run(_run(persona, server or DEFAULT_SERVER, provider, insecure))
    except KeyboardInterrupt:
        print("\n")


async def _send_one(persona: str, text: str, server: str, provider: str | None,
                    insecure: bool, timeout: float) -> str:
    import websockets

    url = _ws_url(server, persona)
    async with websockets.connect(url, ssl=_ssl_context(url, insecure), max_size=None) as ws:
        await ws.recv()  # history handshake
        xid = str(uuid.uuid4())
        await ws.send(json.dumps({
            "type": "send", "exchange_id": xid, "input": text,
            "provider": provider, "proactive": True,
        }))
        parts: list[str] = []
        while True:
            msg = json.loads(await asyncio.wait_for(ws.recv(), timeout=timeout))
            kind = msg.get("type")
            if msg.get("exchange_id") != xid:
                continue
            if kind == "chunk":
                parts.append(msg.get("text", ""))
            elif kind == "done":
                return "".join(parts)
            elif kind == "retract":
                return ""
            elif kind == "error":
                raise RuntimeError(msg.get("text", "server reported an error"))


def send_one(persona: str, text: str, server: str | None = None,
             provider: str | None = None, insecure: bool = True,
             timeout: float = 600.0) -> str:
    """
    Send one message through the server and return the response.

    Used by the scheduler so proactive sessions are ordinary exchanges: they get
    a conversation record (and therefore a seq), land in the shared database, and
    are broadcast live to every connected device.

    Running the pipeline in-process instead — as the scheduler did — produces a
    trace and a push notification but no conversation record and no database row,
    so Metatron initiates a conversation that then appears nowhere in the user's
    history. Raises on failure rather than falling back to in-process, because a
    silent fallback recreates exactly that invisibility.
    """
    return asyncio.run(
        _send_one(persona, text, server or DEFAULT_SERVER, provider, insecure, timeout)
    )
