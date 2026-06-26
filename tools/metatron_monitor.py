"""
tools/metatron_monitor.py — The Book

Visual monitor for Metatron's internal traffic and flow.
Connects to the VM server via Tailscale and reads /monitor/* endpoints.

Usage (MacBook):
    cd ~/Desktop/multi-model-mcp && source .venv-monitor/bin/activate
    python3 tools/metatron_monitor.py
    python3 tools/metatron_monitor.py --server https://100.64.226.49:8001   # VM via Tailscale
    python3 tools/metatron_monitor.py --server https://localhost:8001        # local dev

Requires: pip install textual httpx
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shlex
import sys
import tempfile
from datetime import datetime

try:
    import httpx
    from textual import on, work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.css.query import NoMatches
    from textual.reactive import reactive
    from textual.screen import ModalScreen
    from textual.widgets import (
        Button, Collapsible, Footer, Header, Input, Label, ListItem,
        ListView, Select, Static,
    )
except ImportError:
    print("Missing dependencies. Run: pip install textual httpx")
    sys.exit(1)


DEFAULT_SERVER = "https://100.64.226.49:8001"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return ts[:19]


def fmt_ts_short(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M")
    except Exception:
        return ts[11:16]


def truncate(text: str, n: int = 120) -> str:
    text = text.replace("\n", " ")
    return text[:n] + "…" if len(text) > n else text


# ---------------------------------------------------------------------------
# Custom list items
# ---------------------------------------------------------------------------

class MessageBlock(ListItem):
    """A [user, synth] or [proactive, user, synth] block in Column 1."""

    def __init__(self, entry: dict, trace: dict | None, **kwargs):
        super().__init__(**kwargs)
        self.entry = entry
        self.trace = trace

    def compose(self) -> ComposeResult:
        ts_raw = self.entry.get("ts", "")
        persona = self.entry.get("persona") or "—"
        user_full = self.entry.get("user", "")
        synth_full = self.entry.get("response", "")
        is_proactive = self.trace.get("is_proactive", False) if self.trace else False
        seq = self.entry.get("seq", "")

        proactive_tag = " [yellow]⊕[/]" if is_proactive else ""
        if seq:
            ts_prefix = f"[dim]#{seq}[/] [bold cyan]{fmt_ts_short(ts_raw)}[/]"
        else:
            ts_prefix = f"[bold cyan]{fmt_ts(ts_raw)}[/]"
        title = (
            f"{ts_prefix} [dim]{persona}[/]{proactive_tag}  "
            f"[dim]{truncate(user_full, 60)}[/]"
        )
        yield Collapsible(
            Static(f"[dim]You:[/]\n{user_full}\n\n[dim]Metatron:[/]\n{synth_full}"),
            title=title,
            collapsed=True,
        )


class AgentLogItem(ListItem):
    """One agent call row in Column 2."""

    def __init__(self, agent_rec: dict, **kwargs):
        super().__init__(**kwargs)
        self.agent_rec = agent_rec

    def compose(self) -> ComposeResult:
        r = self.agent_rec
        name = r.get("agent", "?")
        provider = r.get("provider", "")
        model = r.get("model", "")
        total_in = r.get("total_input_tokens", 0)
        total_out = r.get("total_output_tokens", 0)
        duration = r.get("duration_ms", 0)
        turns = r.get("turns", [])

        tool_names = [
            tc.get("name", "?")
            for t in turns
            for tc in t.get("tool_calls", [])
        ]
        model_short = model.split("/")[-1] if "/" in model else model
        indent = "  " if r.get("_indent") else ""

        header = f"{indent}[bold]{name}[/]  [dim]{provider}/{model_short}[/]"
        tokens = f"{indent}[green]{total_in:,}[/] in / [yellow]{total_out:,}[/] out  [dim]{duration}ms[/]"
        turns_line = f"{indent}[dim]{len(turns)} turn{'s' if len(turns) != 1 else ''}[/]"
        if tool_names:
            shown = "  ".join(f"[blue]{t}[/]" for t in tool_names[:4])
            turns_line += f"  {shown}"
            if len(tool_names) > 4:
                turns_line += f"  [dim]+{len(tool_names) - 4} more[/]"

        sublines = [
            f"  [dim]↳ {s.get('agent','?')}  "
            f"{s.get('total_input_tokens',0):,}in / {s.get('total_output_tokens',0):,}out  "
            f"{s.get('duration_ms',0)}ms[/]"
            for s in r.get("subagents", [])
        ]

        yield Static("\n".join([header, tokens, turns_line] + sublines))


# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

BOOK_CSS = """
Screen { layout: vertical; }

#toolbar {
    height: 3;
    layout: horizontal;
    background: $surface;
    padding: 0 1;
    align: left middle;
}

#persona-select { width: 30; margin: 0 2 0 0; }
#live-label { width: auto; margin: 0 1; }

#load-bar {
    height: 3;
    layout: horizontal;
    background: $surface;
    padding: 0 1;
    align: left middle;
    border-top: solid $panel;
}
#range-select  { width: 18; margin: 0 1; }
#limit-select  { width: 10; margin: 0 1; }
#load-btn      { width: 8;  margin: 0 1; }
.load-label   { width: auto; margin: 0 1; color: $text-muted; }

#status-bar {
    height: 1;
    background: $panel;
    color: $text-muted;
    padding: 0 1;
}

#columns { layout: horizontal; height: 1fr; }

#col1 { width: 1fr; border-right: solid $panel; }
#col2 { width: 1fr; border-right: solid $panel; }
#col3 { width: 1fr; }

.col-header {
    height: 1;
    background: $panel;
    color: $text-muted;
    padding: 0 1;
}

#msg-list  { height: 1fr; }
#log-list  { height: 1fr; }

#detail-scroll { height: 1fr; padding: 1; }

MessageBlock  { padding: 0 1; border-bottom: solid $panel; }
MessageBlock:hover { background: $boost; }
MessageBlock.-highlighted { background: $accent 30%; }

AgentLogItem  { padding: 0 1; border-bottom: solid $panel; }
AgentLogItem:hover { background: $boost; }
AgentLogItem.-highlighted { background: $accent 30%; }

Collapsible { margin: 0 0 1 0; }

.file-link {
    height: 1;
    border: none;
    background: transparent;
    color: $accent;
    padding: 0 0;
    min-width: 0;
    width: 100%;
    text-align: left;
}
.file-link:hover { background: $boost; }

#chat-panel {
    height: 14;
    border-top: solid $accent;
}
#chat-history { height: 1fr; padding: 0 1; }
#chat-controls {
    height: 3;
    padding: 0 1;
    align: left middle;
}
#chat-input  { width: 1fr; margin-right: 1; }
#chat-send   { width: 8; }
#chat-clear  { width: 9; margin-left: 1; }
#chat-tokens { width: 14; color: $text-muted; content-align: right middle; }
.chat-user      { color: $text; margin-top: 1; }
.chat-assistant { color: $success; }
.chat-error     { color: $error; }
"""


# ---------------------------------------------------------------------------
# File viewer modal
# ---------------------------------------------------------------------------

class FileViewerScreen(ModalScreen):
    """Full-screen overlay showing a file or full directory history."""

    DEFAULT_CSS = """
    FileViewerScreen { align: center middle; }
    #fv-container {
        width: 92%;
        height: 92%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
        layout: vertical;
    }
    #fv-title  { height: 1; color: $accent; }
    #fv-scroll { height: 1fr; }
    #fv-footer { height: 1; color: $text-muted; }
    .fv-divider { color: $accent; margin: 1 0; }
    .fv-current { color: $success; }
    """
    BINDINGS = [Binding("escape,q", "dismiss", "Close")]

    def __init__(self, path: str, sections: list[dict], current: str, **kwargs):
        """
        sections: list of {filename, stem, content} dicts in date order.
        current:  filename of the entry to mark as current (just-written).
        If sections has one item it's a plain file view; multiple = history view.
        """
        super().__init__(**kwargs)
        self._path = path
        self._sections = sections
        self._current = current

    def compose(self) -> ComposeResult:
        count = len(self._sections)
        title = f"{self._path}  ({count} entr{'y' if count == 1 else 'ies'})"
        with Container(id="fv-container"):
            yield Label(title, id="fv-title")
            with ScrollableContainer(id="fv-scroll"):
                for sec in self._sections:
                    is_current = sec["filename"] == self._current
                    label_cls = "fv-current" if is_current else "fv-divider"
                    marker = "  ← current" if is_current else ""
                    yield Static(
                        f"─── {sec['stem']}{marker} ───",
                        classes=label_cls,
                    )
                    yield Static(sec["content"])
            yield Label("Esc / Q  close", id="fv-footer")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

class TheBookApp(App):
    """The Book — Metatron traffic monitor."""

    TITLE = "The Book — Metatron Monitor"
    CSS = BOOK_CSS
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("l", "toggle_live", "Toggle Live"),
        Binding("s", "snapshot", "Snapshot → Claude Code", priority=True),
        Binding("c", "toggle_chat", "Chat", priority=True),
    ]

    selected_persona: reactive[str | None] = reactive(None)
    live_mode: reactive[bool] = reactive(True)

    def __init__(self, server: str = DEFAULT_SERVER, **kwargs):
        super().__init__(**kwargs)
        self.server = server.rstrip("/")
        self.conversations: list[dict] = []
        self.traces: list[dict] = []
        self._sse_worker = None
        self._selected_trace: dict | None = None
        self._selected_agent_rec: dict | None = None
        self._chat_history: list[tuple[str, str]] = []
        self._approx_tokens: int = 0
        self._range_hours: int = 24   # 0 = all time
        self._limit: int = 10         # 0 = all (no limit param sent)
        self._sse_since: str = ""     # ISO timestamp; SSE ignores traces older than this

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="toolbar"):
            yield Select([], id="persona-select", prompt="— select persona —", allow_blank=True)
            yield Label("● LIVE", id="live-label")
        with Horizontal(id="load-bar"):
            yield Label("Range:", classes="load-label")
            yield Select(
                [
                    ("Last 1h",    "1"),
                    ("Last 6h",    "6"),
                    ("Last 24h",   "24"),
                    ("Last 7d",    "168"),
                    ("Last 30d",   "720"),
                    ("All time",   "0"),
                ],
                id="range-select",
                value="24",
                allow_blank=False,
            )
            yield Label("Max:", classes="load-label")
            yield Select(
                [
                    ("10",  "10"),
                    ("20",  "20"),
                    ("50",  "50"),
                    ("All", "0"),
                ],
                id="limit-select",
                value="10",
                allow_blank=False,
            )
            yield Button("Load", id="load-btn", variant="primary")
        yield Label("Connecting…", id="status-bar")
        with Horizontal(id="columns"):
            with Vertical(id="col1"):
                yield Label("  Conversations", classes="col-header")
                yield ListView(id="msg-list")
            with Vertical(id="col2"):
                yield Label("  Agent calls", classes="col-header")
                yield ListView(id="log-list")
            with Vertical(id="col3"):
                yield Label("  Context & detail", classes="col-header")
                yield ScrollableContainer(id="detail-scroll")
        with Vertical(id="chat-panel"):
            yield ScrollableContainer(id="chat-history")
            with Horizontal(id="chat-controls"):
                yield Input(placeholder="Ask about the current trace… (Enter to send)", id="chat-input")
                yield Button("Send", id="chat-send", variant="primary")
                yield Button("Clear", id="chat-clear")
                yield Label("~0 tok", id="chat-tokens")
        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.query_one("#chat-panel").display = False
        self.load_personas()

    @work(exclusive=True)
    async def load_personas(self) -> None:
        for attempt in range(4):
            if attempt > 0:
                self._set_status(f"Connecting… (attempt {attempt + 1}/4)")
                await asyncio.sleep(2 ** attempt)  # 2s, 4s, 8s
            else:
                self._set_status("Loading personas…")
            try:
                async with httpx.AsyncClient(timeout=10, verify=False) as client:
                    r = await client.get(f"{self.server}/monitor/personas")
                    r.raise_for_status()
                    personas = r.json().get("personas", [])
                sel = self.query_one("#persona-select", Select)
                sel.set_options([(p, p) for p in personas])
                self._set_status(f"Loaded {len(personas)} persona(s). Select one to begin.")
                return
            except Exception as e:
                print(f"[load_personas attempt {attempt + 1}] {e}", file=sys.stderr)
        self._set_status(f"Cannot reach server. Press R to retry.")

    # ------------------------------------------------------------------
    # Persona selection
    # ------------------------------------------------------------------

    @on(Select.Changed, "#persona-select")
    def persona_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        self.selected_persona = str(event.value)
        self.load_data()

    @on(Button.Pressed, "#load-btn")
    def load_btn_pressed(self) -> None:
        try:
            raw = self.query_one("#range-select", Select).value
            self._range_hours = int(raw) if raw != Select.BLANK else 24
        except (ValueError, TypeError):
            self._range_hours = 24
        try:
            raw_limit = self.query_one("#limit-select", Select).value
            val = int(raw_limit) if raw_limit != Select.BLANK else 10
            self._limit = val  # 0 = All (no limit sent to server)
        except (ValueError, TypeError):
            self._limit = 10
        self.load_data()

    @work(exclusive=True)
    async def load_data(self) -> None:
        persona = self.selected_persona
        if not persona:
            return

        # Stop the old SSE worker immediately so it stops writing to self.conversations
        # while we clear and repopulate. Deferring this until after the HTTP requests
        # was the root cause of the freeze-on-switch bug.
        if self._sse_worker is not None:
            self._sse_worker.cancel()
            self._sse_worker = None

        # Record now as the SSE cutoff — the SSE stream will skip any trace older
        # than this, so historical backfill can't corrupt the filtered HTTP view.
        from datetime import datetime as _dt
        self._sse_since = _dt.now().isoformat()

        # Build query params from current load settings
        params: dict = {"persona": persona}
        if self._range_hours > 0:
            from datetime import datetime as _dt, timedelta as _td
            since = (_dt.now() - _td(hours=self._range_hours)).isoformat()
            params["since"] = since
        if self._limit > 0:
            params["limit"] = self._limit

        range_label = f"last {self._range_hours}h" if self._range_hours > 0 else "all time"
        self._set_status(f"Loading {persona} ({range_label}, max {self._limit})…")
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                conv_r = await client.get(
                    f"{self.server}/monitor/conversations", params=params,
                )
                conv_r.raise_for_status()
                trace_r = await client.get(
                    f"{self.server}/monitor/traces", params=params,
                )
                trace_r.raise_for_status()

            self.conversations = conv_r.json().get("entries", [])
            self.traces = trace_r.json().get("traces", [])
            self._populate_col1()
            self._set_status(
                f"{persona} — {len(self.conversations)} messages, "
                f"{len(self.traces)} traces  [{range_label}]"
            )

            if self.live_mode:
                self._sse_worker = self.run_worker(
                    self._sse_loop(persona, self._sse_since), exclusive=False, name="sse"
                )

        except Exception as e:
            print(f"[load_data error] {e}", file=sys.stderr)
            self._set_status(f"Error loading {persona}: {e}")

    # ------------------------------------------------------------------
    # Column 1 population
    # ------------------------------------------------------------------

    def _trace_for_conv(self, entry: dict) -> dict | None:
        conv_ts = entry.get("ts", "")
        user_prefix = entry.get("user", "")[:50]
        for t in self.traces:
            if t.get("ts", "")[:19] == conv_ts[:19]:
                return t
            if (t.get("user_input", "")[:50] == user_prefix
                    and t.get("persona") == entry.get("persona")):
                return t
        return None

    def _populate_col1(self) -> None:
        lst = self.query_one("#msg-list", ListView)
        lst.clear()
        sorted_convs = sorted(self.conversations, key=lambda e: e.get("ts", ""), reverse=True)
        for entry in sorted_convs:
            trace = self._trace_for_conv(entry)
            lst.append(MessageBlock(entry, trace))
        lst.scroll_home(animate=False)

    def _prepend_col1(self, entry: dict, trace: dict | None) -> None:
        """Insert a new (most recent) message at the top of Column 1."""
        lst = self.query_one("#msg-list", ListView)
        block = MessageBlock(entry, trace)
        if lst.children:
            lst.mount(block, before=lst.children[0])
        else:
            lst.mount(block)
        lst.scroll_home(animate=False)

    # ------------------------------------------------------------------
    # Column 1 → Column 2
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#msg-list")
    def msg_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, MessageBlock):
            return
        self._selected_trace = item.trace
        self._selected_agent_rec = None
        self._populate_col2(item.trace)
        self._clear_col3()

    def _populate_col2(self, trace: dict | None) -> None:
        lst = self.query_one("#log-list", ListView)
        lst.clear()
        if trace is None:
            lst.append(ListItem(Static("[dim]No trace for this message — run a conversation after deploying.[/]")))
            return
        pipeline = trace.get("pipeline", [])
        for agent_rec in pipeline:
            lst.append(AgentLogItem(agent_rec))
            for sub in agent_rec.get("subagents", []):
                sub_copy = dict(sub)
                sub_copy["_indent"] = True
                lst.append(AgentLogItem(sub_copy))

    # ------------------------------------------------------------------
    # Column 2 → Column 3
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#log-list")
    async def log_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, AgentLogItem):
            return
        self._selected_agent_rec = item.agent_rec
        await self._populate_col3(item.agent_rec)

    def _clear_col3(self) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

    async def _populate_col3(self, agent_rec: dict) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

        ctx = agent_rec.get("context_sections", {})
        turns = agent_rec.get("turns", [])
        subagents = agent_rec.get("subagents", [])
        name = agent_rec.get("agent", "?")
        provider = agent_rec.get("provider", "")
        model = agent_rec.get("model", "")
        total_in = agent_rec.get("total_input_tokens", 0)
        total_out = agent_rec.get("total_output_tokens", 0)
        dur = agent_rec.get("duration_ms", 0)

        widgets: list = [
            Static(
                f"[bold]{name}[/]  [dim]{provider}[/]  [cyan]{model}[/]\n"
                f"[green]{total_in:,}[/] in / [yellow]{total_out:,}[/] out  [dim]{dur}ms[/]"
            )
        ]

        # Context sections — each a top-level Collapsible
        for key, label in [
            ("agent_file", "Agent Instructions"),
            ("config", "Config (constitution + goals)"),
            ("recent_context", "Recent Context"),
            ("conversation_history", "Conversation History (fed to Synth)"),
        ]:
            content = ctx.get(key, "")
            if content:
                widgets.append(Collapsible(Static(content), title=label, collapsed=True))

        # Build a lookup of subagent records by name for run_subagent resolution
        sub_by_name: dict[str, dict] = {s.get("agent", ""): s for s in subagents}

        # Turns — Static divider per turn, then each tool call as its own top-level Collapsible
        for t in turns:
            turn_num = t.get("turn", "?")
            t_in = t.get("input_tokens", 0)
            t_out = t.get("output_tokens", 0)
            tool_calls = t.get("tool_calls", [])

            widgets.append(Static(
                f"\n[dim]── Turn {turn_num}  "
                f"[green]{t_in:,}[/]in  [yellow]{t_out:,}[/]out ──[/]"
            ))

            if not tool_calls:
                widgets.append(Static("  [dim]no tool calls[/]"))
                continue

            for tc in tool_calls:
                tc_name = tc.get("name", "?")
                tc_dur = tc.get("duration_ms", 0)

                if tc_name == "run_subagent":
                    # Resolve to the actual subagent record instead of showing raw args
                    called = (tc.get("args", {}).get("agent_name", "")
                              or tc.get("args", {}).get("agent", "")
                              or tc.get("args", {}).get("name", ""))
                    sub = sub_by_name.get(called)
                    if sub:
                        s_in = sub.get("total_input_tokens", 0)
                        s_out = sub.get("total_output_tokens", 0)
                        s_dur = sub.get("duration_ms", 0)
                        s_model = sub.get("model", "").split("/")[-1]
                        s_files = sub.get("output_files", [])
                        s_turns = sub.get("turns", [])

                        inner: list = [Static(
                            f"[dim]{sub.get('provider','')}/{s_model}[/]  "
                            f"[green]{s_in:,}[/]in / [yellow]{s_out:,}[/]out  [dim]{s_dur}ms[/]"
                        )]
                        for st in s_turns:
                            stcs = st.get("tool_calls", [])
                            stc_line = "  ".join(
                                f"[blue]⚙ {stc.get('name','?')}[/]" for stc in stcs
                            )
                            inner.append(Static(
                                f"  Turn {st.get('turn')}  "
                                f"[green]{st.get('input_tokens',0):,}[/]in  "
                                f"[yellow]{st.get('output_tokens',0):,}[/]out"
                                + (f"  {stc_line}" if stc_line else "")
                            ))
                        if s_files:
                            inner.append(Static("[bold]Output Files[/]"))
                            for fp in s_files:
                                inner.append(Button(fp, name=fp, classes="file-link"))

                        tok_str = f"  [green]{s_in:,}[/]in/[yellow]{s_out:,}[/]out" if (s_in or s_out) else ""
                        widgets.append(Collapsible(
                            *inner,
                            title=f"→ {called}{tok_str}  [dim]{s_dur:.1f}ms[/]",
                            collapsed=True,
                        ))
                    else:
                        # Subagent record not found — fall back to raw args
                        widgets.append(Collapsible(
                            Static(json.dumps(tc.get("args", {}), indent=2)),
                            title=f"run_subagent({called or '?'})  [dim]{tc_dur:.1f}ms[/]",
                            collapsed=True,
                        ))
                else:
                    tc_args = json.dumps(tc.get("args", {}), indent=2)
                    tc_result = tc.get("result_preview", "")
                    tc_in = tc.get("input_tokens", 0)
                    tc_out = tc.get("output_tokens", 0)
                    tok_str = f"  [green]{tc_in:,}[/]in/[yellow]{tc_out:,}[/]out" if (tc_in or tc_out) else ""
                    widgets.append(Collapsible(
                        Static(f"Args:\n{tc_args}\n\nResult:\n{tc_result}"),
                        title=f"⚙ {tc_name}{tok_str}  [dim]{tc_dur:.1f}ms[/]",
                        collapsed=True,
                    ))

        # Output files written by this agent
        output_files = agent_rec.get("output_files", [])
        if output_files:
            widgets.append(Static("\n[bold]Output Files[/]"))
            for path in output_files:
                widgets.append(Button(path, name=path, classes="file-link"))

        await scroller.mount(*widgets)

    # ------------------------------------------------------------------
    # File viewer
    # ------------------------------------------------------------------

    @on(Button.Pressed, ".file-link")
    async def file_link_pressed(self, event: Button.Pressed) -> None:
        path = event.button.name or str(event.button.label)
        self._set_status(f"Opening {path}…")
        try:
            async with httpx.AsyncClient(timeout=15, verify=False) as client:
                # Try history endpoint first — returns full directory for dated files
                r = await client.get(
                    f"{self.server}/monitor/history", params={"path": path}
                )
                r.raise_for_status()
                data = r.json()
            await self.push_screen(
                FileViewerScreen(data["path"], data["sections"], data["current"])
            )
            self._set_status(f"Viewing {path} ({len(data['sections'])} entries)")
        except Exception as e:
            print(f"[open_file error] {e}", file=sys.stderr)
            self._set_status(f"Cannot read {path}: {e}")

    # ------------------------------------------------------------------
    # Live SSE
    # ------------------------------------------------------------------

    async def _sse_loop(self, persona: str, since: str = "") -> None:
        url = f"{self.server}/monitor/stream"
        sse_params: dict = {"persona": persona}
        if since:
            sse_params["since"] = since
        retry_delay = 2
        while True:
            try:
                async with httpx.AsyncClient(timeout=None, verify=False) as client:
                    async with client.stream("GET", url, params=sse_params) as resp:
                        retry_delay = 2  # reset on successful connection
                        self._set_status(
                            f"{persona} — {len(self.conversations)} messages  ● live"
                        )
                        async for line in resp.aiter_lines():
                            if not line.startswith("data: "):
                                continue
                            try:
                                msg = json.loads(line[6:])
                            except Exception:
                                continue
                            if msg.get("type") != "trace":
                                continue

                            trace = msg["data"]
                            self.traces.append(trace)
                            user_input = trace.get("user_input", "")
                            if not any(e.get("user", "")[:50] == user_input[:50]
                                       for e in self.conversations):
                                new_entry = {
                                    "ts": trace.get("ts", ""),
                                    "agent": "coordinator",
                                    "persona": trace.get("persona"),
                                    "user": user_input,
                                    "response": trace.get("synth_response", ""),
                                }
                                self.conversations.append(new_entry)
                                self._prepend_col1(new_entry, trace)
                            self._set_status(
                                f"{persona} — {len(self.conversations)} messages  ● live"
                            )
            except asyncio.CancelledError:
                return  # intentional shutdown — don't retry
            except Exception as e:
                print(f"[sse_loop error] {e}", file=sys.stderr)
                self._set_status(
                    f"{persona} — SSE reconnecting in {retry_delay}s…"
                )
                await asyncio.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, 30)  # backoff up to 30s

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        if self.selected_persona:
            self.load_data()
        else:
            self.load_personas()

    def action_toggle_live(self) -> None:
        self.live_mode = not self.live_mode
        label = self.query_one("#live-label", Label)
        if self.live_mode:
            label.update("● LIVE")
            if self.selected_persona and self._sse_worker is None:
                self._sse_worker = self.run_worker(
                    self._sse_loop(self.selected_persona), exclusive=False, name="sse"
                )
        else:
            label.update("○ paused")
            if self._sse_worker is not None:
                self._sse_worker.cancel()
                self._sse_worker = None

    def action_toggle_chat(self) -> None:
        panel = self.query_one("#chat-panel")
        panel.display = not panel.display
        if panel.display:
            self.query_one("#chat-input", Input).focus()

    @on(Input.Submitted, "#chat-input")
    def chat_submitted(self, event: Input.Submitted) -> None:
        self._send_message(event.value)
        event.input.clear()

    @on(Button.Pressed, "#chat-send")
    def chat_send_pressed(self) -> None:
        inp = self.query_one("#chat-input", Input)
        self._send_message(inp.value)
        inp.clear()

    @on(Button.Pressed, "#chat-clear")
    async def chat_clear_pressed(self) -> None:
        self._chat_history.clear()
        self._approx_tokens = 0
        container = self.query_one("#chat-history", ScrollableContainer)
        container.remove_children()
        self._update_token_label()

    def _send_message(self, text: str) -> None:
        text = text.strip()
        if not text:
            return
        self._run_chat(text)

    def _snapshot_text(self) -> str:
        lines = [f"Persona: {self.selected_persona or 'none'}"]
        if self._selected_trace:
            t = self._selected_trace
            lines.append(
                f"Selected conversation: {t.get('ts','')}  "
                f"User: {(t.get('user_input') or t.get('user',''))[:120]}"
            )
            lines.append(f"Total duration: {t.get('duration_ms','?')}ms")
            for ag in t.get("pipeline", []):
                m = ag.get("model","").split("/")[-1]
                lines.append(
                    f"  Agent {ag.get('agent')}  {ag.get('provider')}/{m}  "
                    f"{ag.get('total_input_tokens',0):,}in/{ag.get('total_output_tokens',0):,}out  "
                    f"{ag.get('duration_ms',0)}ms  {len(ag.get('turns',[]))} turns"
                )
                for sub in ag.get("subagents", []):
                    sm = sub.get("model","").split("/")[-1]
                    lines.append(
                        f"    ↳ {sub.get('agent')}  {sub.get('provider')}/{sm}  "
                        f"{sub.get('total_input_tokens',0):,}in/{sub.get('total_output_tokens',0):,}out  "
                        f"{sub.get('duration_ms',0)}ms"
                    )
                    for fp in sub.get("output_files", []):
                        lines.append(f"       wrote: {fp}")
        if self._selected_agent_rec:
            ag = self._selected_agent_rec
            lines.append(
                f"Focused agent: {ag.get('agent')}  "
                f"{ag.get('total_input_tokens',0):,}in/{ag.get('total_output_tokens',0):,}out  "
                f"{len(ag.get('turns',[]))} turns"
            )
            for turn in ag.get("turns", []):
                tcs = [tc.get("name","?") for tc in turn.get("tool_calls", [])]
                if tcs:
                    lines.append(f"  Turn {turn.get('turn')}: {', '.join(tcs)}")
        return "\n".join(lines)

    def _update_token_label(self) -> None:
        try:
            self.query_one("#chat-tokens", Label).update(f"~{self._approx_tokens:,} tok")
        except NoMatches:
            pass

    @work(exclusive=False, name="chat")
    async def _run_chat(self, question: str) -> None:
        container = self.query_one("#chat-history", ScrollableContainer)
        await container.mount(Static(f"[bold]You:[/] {question}", classes="chat-user"))
        container.scroll_end(animate=False)

        context = self._snapshot_text()
        prompt_parts = [
            "You are analyzing Metatron, a personal AI life manager built on a multi-agent "
            "pipeline. The Book is its monitoring tool. Answer questions about its internal "
            "traffic, routing decisions, token usage, and agent behavior based on the current state.\n\n"
            f"Current Book state:\n{context}\n"
        ]
        for u, a in self._chat_history:
            prompt_parts.append(f"\nHuman: {u}\nAssistant: {a}")
        prompt_parts.append(f"\nHuman: {question}\nAssistant:")
        full_prompt = "".join(prompt_parts)

        self._approx_tokens += len(full_prompt) // 4
        self._update_token_label()

        response_widget = Static("[dim]Thinking…[/]", classes="chat-assistant")
        await container.mount(response_widget)
        container.scroll_end(animate=False)

        tmp_path = None
        try:
            # Write prompt to a temp file — avoids TTY/stdin detection issues
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as f:
                f.write(full_prompt)
                tmp_path = f.name

            cmd = f"claude -p --output-format text < {shlex.quote(tmp_path)}"
            proc = await asyncio.create_subprocess_shell(
                cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            response_text = ""
            # Stream stdout line-by-line for live display
            async for raw in proc.stdout:
                chunk = raw.decode()
                response_text += chunk
                response_widget.update(f"[green]Claude:[/] {response_text.rstrip()}")
                container.scroll_end(animate=False)

            _, stderr_bytes = await proc.communicate()

            if not response_text:
                err = stderr_bytes.decode().strip()
                print(f"[chat stderr] {err}", file=sys.stderr)
                response_widget.update(
                    f"[red]No response.[/]\n[dim]{err[:400] if err else 'claude produced no output'}[/]"
                )
            else:
                self._chat_history.append((question, response_text))
                self._approx_tokens += len(response_text) // 4
                self._update_token_label()

        except FileNotFoundError:
            response_widget.update(
                "[red]'claude' not found in PATH.[/]\n"
                "[dim]Ensure Claude Code CLI is installed and your shell PATH is set.[/]"
            )
        except Exception as e:
            print(f"[chat error] {e}", file=sys.stderr)
            response_widget.update(f"[red]Error: {e}[/]")
        finally:
            if tmp_path and os.path.exists(tmp_path):
                os.unlink(tmp_path)

        container.scroll_end(animate=False)

    def action_snapshot(self) -> None:
        """Write current Book state to data/book_snapshot.md for Claude Code."""
        lines = [
            "# Book Snapshot",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Server: {self.server}",
            f"Persona: {self.selected_persona or '—'}",
            f"Conversations loaded: {len(self.conversations)}",
            f"Traces loaded: {len(self.traces)}",
            "",
        ]

        if self._selected_trace:
            t = self._selected_trace
            lines += [
                "## Selected Conversation",
                f"Timestamp: {t.get('ts', '—')}",
                f"User: {t.get('user_input', t.get('user', '—'))}",
                f"Response: {(t.get('synth_response', '') or '')[:300]}",
                f"Duration: {t.get('duration_ms', '—')}ms",
                "",
                "### Pipeline",
            ]
            for i, ag in enumerate(t.get("pipeline", []), 1):
                lines.append(
                    f"{i}. {ag.get('agent','?')}  {ag.get('provider','')}/{ag.get('model','').split('/')[-1]}"
                    f"  {ag.get('total_input_tokens',0):,}in / {ag.get('total_output_tokens',0):,}out"
                    f"  {ag.get('duration_ms',0)}ms"
                )
                for sub in ag.get("subagents", []):
                    lines.append(
                        f"   ↳ {sub.get('agent','?')}  {sub.get('total_input_tokens',0):,}in"
                        f" / {sub.get('total_output_tokens',0):,}out  {sub.get('duration_ms',0)}ms"
                    )
                    for fp in sub.get("output_files", []):
                        lines.append(f"      wrote: {fp}")
                for fp in ag.get("output_files", []):
                    lines.append(f"      wrote: {fp}")
            lines.append("")

        if self._selected_agent_rec:
            ag = self._selected_agent_rec
            lines += [
                "## Selected Agent (Column 3 focus)",
                f"Agent: {ag.get('agent','?')}",
                f"Provider/Model: {ag.get('provider','')}/{ag.get('model','')}",
                f"Tokens: {ag.get('total_input_tokens',0):,}in / {ag.get('total_output_tokens',0):,}out",
                f"Duration: {ag.get('duration_ms',0)}ms",
                f"Turns: {len(ag.get('turns',[]))}",
                "",
            ]
            for turn in ag.get("turns", []):
                tcs = turn.get("tool_calls", [])
                if tcs:
                    lines.append(f"  Turn {turn.get('turn')}: " + ", ".join(
                        f"{tc.get('name','?')} ({tc.get('duration_ms',0)}ms)" for tc in tcs
                    ))
            if ag.get("output_files"):
                lines.append("  Output files: " + ", ".join(ag["output_files"]))
            lines.append("")

        try:
            snapshot_path = Path(__file__).parent.parent / "data" / "book_snapshot.md"
            snapshot_path.parent.mkdir(parents=True, exist_ok=True)
            snapshot_path.write_text("\n".join(lines))
            self._set_status("Snapshot written → data/book_snapshot.md  (tell Claude Code to read it)")
        except Exception as e:
            print(f"[snapshot error] {e}", file=sys.stderr)
            self._set_status(f"Snapshot failed: {e}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _set_status(self, text: str) -> None:
        try:
            self.query_one("#status-bar", Label).update(text)
        except NoMatches:
            pass


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="The Book — Metatron Monitor")
    parser.add_argument(
        "--server",
        default=DEFAULT_SERVER,
        help=f"Metatron server URL (default: {DEFAULT_SERVER})",
    )
    args = parser.parse_args()
    TheBookApp(server=args.server).run()


if __name__ == "__main__":
    main()
