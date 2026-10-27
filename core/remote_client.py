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


async def _connect_authed(websockets, url: str, insecure: bool):
    """
    Open a WebSocket and complete the auth handshake.

    The server requires the first frame to be {"type": "auth", "token": ...} — a
    WebSocket cannot carry an Authorization header, and a token in the query string
    would land in the access log. Every connect path goes through here, including the
    reconnect loop: a reconnect that skipped the handshake would be closed by the
    server and retried forever.
    """
    from core.auth import client_token

    conn = await websockets.connect(url, ssl=_ssl_context(url, insecure), max_size=None)
    await conn.send(json.dumps({"type": "auth", "token": client_token(ttl_seconds=86400)}))
    reply = json.loads(await conn.recv())
    if reply.get("type") != "auth_ok":
        await conn.close()
        raise PermissionError(
            "Server rejected the session token. Check METATRON_AUTH_PASSWORD in .env "
            "matches the value set on the server."
        )
    return conn


def _ssl_context(url: str, insecure: bool):
    # https:// as well as wss:// since the internal HTTP routes (`post_internal`) share this
    # TLS handling with the WebSocket client — one place decides how the Tailscale cert is
    # trusted, so the two paths from the scheduler to the server cannot drift apart.
    if not url.startswith(("wss://", "https://")):
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
        conn = await _connect_authed(websockets, url, insecure)
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
    _closed = False

    async def receive() -> None:
        nonlocal streaming_own, conn
        while True:
            try:
                await _receive_once()
            except Exception as exc:
                # A deploy restarts the server mid-session (close code 1012).
                # The browser reconnects with backoff; this did not, so the
                # session died with an unretrieved-task traceback.
                if _closed:
                    return
                print(f"\n{_YELLOW}[connection lost: {type(exc).__name__}] reconnecting…{_RESET}")
                delay = 2.0
                while not _closed:
                    await asyncio.sleep(delay)
                    try:
                        conn = await _connect_authed(websockets, url, insecure)
                        print(f"{_YELLOW}[reconnected]{_RESET}")
                        break
                    except Exception:
                        delay = min(delay * 2, 30.0)
                        print(f"{_DIM}  retry in {delay:.0f}s…{_RESET}")
                if _closed:
                    return

    async def _receive_once() -> None:
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
                # Another device is talking, or Metatron opened a check-in.
                if msg.get("proactive"):
                    print(f"\n{_CYAN}[Metatron checking in]{_RESET}")
                else:
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
                    if msg.get("proactive"):
                        print(f"\n{_CYAN}[Metatron checking in]{_RESET}")
                    else:
                        print(f"\n{_CYAN}[from another device] {msg.get('user','')}{_RESET}")
                    print(f"{_CYAN}{msg.get('assistant','')}{_RESET}\n")
                    _prompt()

    def _prompt() -> None:
        sys.stdout.write("> ")
        sys.stdout.flush()

    async def send_loop() -> None:
        nonlocal _closed
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
                _closed = True
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
        _closed = True
        try:
            await conn.close()
        except Exception:
            pass


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
                    insecure: bool, timeout: float, nudge: bool = False) -> str:
    import websockets

    url = _ws_url(server, persona)
    ws = await _connect_authed(websockets, url, insecure)
    try:
        await ws.recv()  # history handshake
        xid = str(uuid.uuid4())
        await ws.send(json.dumps({
            "type": "send", "exchange_id": xid, "input": text,
            "provider": provider, "proactive": True,
            # A day-plan nudge (tools/day_plan.py): the server buffers it, skips the
            # Coordinator, and records and broadcasts it only if the Synthesizer speaks.
            **({"nudge": True} if nudge else {}),
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
            elif kind in ("retract", "held"):
                return ""
            elif kind == "error":
                raise RuntimeError(msg.get("text", "server reported an error"))
    finally:
        # Was an `async with` before the auth handshake was added; the handshake has
        # to happen between connect and first use, so the close is explicit now.
        await ws.close()


def send_one(persona: str, text: str, server: str | None = None,
             provider: str | None = None, insecure: bool = True,
             timeout: float = 600.0, nudge: bool = False) -> str:
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
        _send_one(persona, text, server or DEFAULT_SERVER, provider, insecure, timeout,
                  nudge=nudge)
    )


# ---------------------------------------------------------------------------
# Service-only internal routes — the scheduler's model-free path (plan § 4.12.3)
# ---------------------------------------------------------------------------
#
# WHY these exist. A per-user scheduler that ran a non-coordinator session in-process
# loaded the embedding model (~0.9 GB) on its first `write_log`, kept it for the life of
# the process, and — through tools/baselines.py's private copy — could load it twice. Two
# schedulers would undo the whole memory saving (review M1). So every scheduled session
# runs on the server, where the model already lives once, and a scheduler process
# (`METATRON_NO_LOCAL_MODELS=1`) hands its index/search calls to the server too.
#
# Same server and TLS handling as `send_one` (DEFAULT_SERVER, `insecure=True` against the
# Tailscale cert) — deliberately no new address setting: a second one is a second place to
# go stale. Service token from `core.auth.bearer_header()`: the routes are `/internal/*`,
# which the server's middleware refuses to any `user`/`admin` token, so the persona must
# travel in the body and the server binds it per request.

# A scheduled pattern-miner run makes several model calls and tool rounds and has taken
# minutes; the server holds the HTTP response until the run ends, so this bounds the whole
# run, not an idle gap. 15 min is ~3x the longest single-agent run we expect and well under
# the weekly cadence of the jobs that use it. On timeout the server's run is NOT cancelled
# (uvicorn imposes no request timeout) — its tool writes still land; only the notification
# text is lost, and the scheduler has already recorded the fire, so it does not retry.
INTERNAL_SESSION_TIMEOUT_SECONDS = 900.0


class InternalCallError(RuntimeError):
    """A `/internal/*` call that did not return 200. `status` is 0 when nothing answered."""

    def __init__(self, path: str, status: int, detail: str) -> None:
        self.path = path
        self.status = status
        self.detail = detail
        where = f"HTTP {status}" if status else "no response"
        super().__init__(f"{path} failed ({where}): {detail}")


def post_internal(path: str, body: dict, timeout: float, server: str | None = None,
                  insecure: bool = True) -> dict:
    """
    POST JSON to a service-only `/internal/*` route and return the decoded JSON reply.

    Raises InternalCallError on any non-200 or transport failure — never returns a
    fallback, because a caller that silently fell back to running locally would load the
    model this path exists to keep out of the process.
    """
    import urllib.error
    import urllib.request

    from core.auth import bearer_header

    url = f"{(server or DEFAULT_SERVER).rstrip('/')}{path}"
    # TTL a little past the timeout: the token is checked once, at the start of the
    # request, but there is no reason to mint one that could expire in a queue.
    headers = {"Content-Type": "application/json",
               **bearer_header(ttl_seconds=int(timeout) + 300)}
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout,
                                    context=_ssl_context(url, insecure)) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            status = resp.status
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(detail).get("detail", detail)
        except (ValueError, AttributeError):
            pass
        raise InternalCallError(path, exc.code, str(detail).strip() or str(exc.reason)) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise InternalCallError(path, 0, str(exc)) from exc
    if status != 200:
        raise InternalCallError(path, status, raw[:500])
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise InternalCallError(path, status, f"reply was not JSON: {raw[:200]}") from exc


def run_internal_session(agent: str, text: str, persona: str, server: str | None = None,
                         insecure: bool = True,
                         timeout: float = INTERNAL_SESSION_TIMEOUT_SECONDS) -> str:
    """
    Run one scheduled NON-coordinator session (pattern_miner, physical_health, …) on the
    server and return its response text.

    Replaces the scheduler's in-process `run_session` (plan § 4.12.3 item 1). Not `/session`:
    that route writes every run to the conversation log, which the nightly CRM sweep reads
    as things the user said (review M1-N1). `/internal/session` runs
    `run_session(agent, input, persona=…, proactive=True)` and writes no conversation
    record — exactly what the in-process run produced. Coordinator sessions still go
    through `send_one`, because those ARE conversation.

    Raises on failure rather than falling back to in-process, for the reason `send_one`
    gives and one more: the fallback would load the model into the scheduler.
    """
    reply = post_internal(
        "/internal/session",
        {"agent": agent, "input": text, "persona": persona, "proactive": True},
        timeout=timeout, server=server, insecure=insecure,
    )
    response = reply.get("response") if isinstance(reply, dict) else None
    if not isinstance(response, str):
        raise InternalCallError("/internal/session", 200, "reply carried no 'response' text")
    return response
