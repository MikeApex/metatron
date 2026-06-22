"""
tools/metatron_monitor.py — The Book

Visual monitor for Metatron's internal traffic and flow.
Connects to the VM server via Tailscale and reads /monitor/* endpoints.

Usage:
    python3 tools/metatron_monitor.py
    python3 tools/metatron_monitor.py --server http://100.64.226.49:8001
    python3 tools/metatron_monitor.py --server http://localhost:8001   # local dev

Requires: pip install textual httpx
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import threading
from datetime import datetime
from typing import Any

try:
    import httpx
    from textual import on, work
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
    from textual.css.query import NoMatches
    from textual.reactive import reactive
    from textual.screen import Screen
    from textual.widget import Widget
    from textual.widgets import (
        Button, Collapsible, Footer, Header, Label, ListItem,
        ListView, Select, Static, Tree,
    )
    from textual.widgets.tree import TreeNode
except ImportError:
    print("Missing dependencies. Run: pip install textual httpx")
    sys.exit(1)


DEFAULT_SERVER = "http://100.64.226.49:8001"


# ---------------------------------------------------------------------------
# Data helpers
# ---------------------------------------------------------------------------

def fmt_ts(ts: str) -> str:
    try:
        dt = datetime.fromisoformat(ts)
        return dt.strftime("%H:%M:%S")
    except Exception:
        return ts[:19]


def fmt_tokens(inp: int, out: int) -> str:
    return f"{inp:,}in / {out:,}out"


def truncate(text: str, n: int = 120) -> str:
    text = text.replace("\n", " ")
    return text[:n] + "…" if len(text) > n else text


# ---------------------------------------------------------------------------
# Custom widgets
# ---------------------------------------------------------------------------

class DragHandle(Widget):
    """Vertical drag handle between two panes."""

    DEFAULT_CSS = """
    DragHandle {
        width: 1;
        background: $panel;
        color: $text-muted;
        content-align: center middle;
    }
    DragHandle:hover {
        background: $accent;
    }
    """

    def render(self) -> str:
        return "┃"

    def on_mouse_down(self, event) -> None:
        event.prevent_default()
        self.capture_mouse()
        self._drag_start_x = event.screen_x

    def on_mouse_up(self, event) -> None:
        self.release_mouse()

    def on_mouse_move(self, event) -> None:
        if self.app.is_mouse_captured(self):
            dx = event.screen_x - getattr(self, "_drag_start_x", event.screen_x)
            self._drag_start_x = event.screen_x
            self.app.on_drag_handle(self.id, dx)


class MessageBlock(ListItem):
    """A single [user, synth] or [proactive, user, synth] message block in Column 1."""

    def __init__(self, entry: dict, trace: dict | None, **kwargs):
        super().__init__(**kwargs)
        self.entry = entry
        self.trace = trace  # may be None if trace not yet available

    def compose(self) -> ComposeResult:
        ts = fmt_ts(self.entry.get("ts", ""))
        persona = self.entry.get("persona") or "—"
        user_text = truncate(self.entry.get("user", ""), 80)
        synth_text = truncate(self.entry.get("response", ""), 80)
        is_proactive = self.trace.get("is_proactive", False) if self.trace else False

        lines = []
        if is_proactive:
            lines.append(f"[bold cyan]{ts}[/] [dim]{persona}[/] [yellow]⊕ proactive[/]")
        else:
            lines.append(f"[bold cyan]{ts}[/] [dim]{persona}[/]")
        lines.append(f"[dim]You:[/] {user_text}")
        lines.append(f"[dim]M:[/]  {synth_text}")
        yield Static("\n".join(lines))


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
        tool_names = []
        for t in turns:
            for tc in t.get("tool_calls", []):
                tool_names.append(tc.get("name", "?"))

        model_short = model.split("/")[-1] if "/" in model else model
        header = f"[bold]{name}[/]  [dim]{provider}/{model_short}[/]"
        tokens = f"[green]{total_in:,}[/] in / [yellow]{total_out:,}[/] out  [dim]{duration}ms[/]"
        turns_line = f"[dim]{len(turns)} turn{'s' if len(turns) != 1 else ''}[/]"
        if tool_names:
            turns_line += "  " + "  ".join(f"[blue]{t}[/]" for t in tool_names[:4])
            if len(tool_names) > 4:
                turns_line += f"  [dim]+{len(tool_names)-4} more[/]"

        # Subagents
        sublines = []
        for s in r.get("subagents", []):
            s_name = s.get("agent", "?")
            s_in = s.get("total_input_tokens", 0)
            s_out = s.get("total_output_tokens", 0)
            s_dur = s.get("duration_ms", 0)
            sublines.append(f"  [dim]↳ {s_name}  {s_in:,}in / {s_out:,}out  {s_dur}ms[/]")

        lines = [header, tokens, turns_line] + sublines
        yield Static("\n".join(lines))


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

BOOK_CSS = """
Screen {
    layout: vertical;
}

#toolbar {
    height: 3;
    layout: horizontal;
    background: $surface;
    padding: 0 1;
    align: left middle;
}

#persona-select {
    width: 30;
    margin: 0 2 0 0;
}

#live-label {
    width: auto;
    margin: 0 1;
}

#status-bar {
    height: 1;
    background: $panel;
    color: $text-muted;
    padding: 0 1;
}

#columns {
    layout: horizontal;
    height: 1fr;
}

#col1 {
    width: 1fr;
    border-right: solid $panel;
}

#col2 {
    width: 1fr;
    border-right: solid $panel;
}

#col3 {
    width: 1fr;
}

.col-header {
    height: 1;
    background: $panel;
    color: $text-muted;
    padding: 0 1;
    text-align: left;
}

#msg-list {
    height: 1fr;
    overflow-y: scroll;
}

#log-list {
    height: 1fr;
    overflow-y: scroll;
}

#detail-scroll {
    height: 1fr;
    overflow-y: scroll;
    padding: 1;
}

MessageBlock {
    padding: 0 1;
    border-bottom: solid $panel;
}

MessageBlock:hover {
    background: $boost;
}

MessageBlock.-selected {
    background: $accent 30%;
}

AgentLogItem {
    padding: 0 1;
    border-bottom: solid $panel;
}

AgentLogItem:hover {
    background: $boost;
}

AgentLogItem.-selected {
    background: $accent 30%;
}

Collapsible {
    margin: 0 0 1 0;
}

.detail-label {
    color: $text-muted;
    text-style: bold;
    margin: 1 0 0 0;
}
"""


class TheBookApp(App):
    """The Book — Metatron traffic monitor."""

    TITLE = "The Book — Metatron Monitor"
    CSS = BOOK_CSS
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
        Binding("l", "toggle_live", "Toggle Live"),
    ]

    personas: reactive[list[str]] = reactive([])
    selected_persona: reactive[str | None] = reactive(None)
    conversations: reactive[list[dict]] = reactive([])
    traces: reactive[list[dict]] = reactive([])
    live_mode: reactive[bool] = reactive(True)
    status: reactive[str] = reactive("Connecting…")

    def __init__(self, server: str = DEFAULT_SERVER, **kwargs):
        super().__init__(**kwargs)
        self.server = server.rstrip("/")
        self._selected_conv_idx: int | None = None
        self._selected_agent_idx: int | None = None
        self._sse_task: asyncio.Task | None = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="toolbar"):
            yield Select([], id="persona-select", prompt="— select persona —", allow_blank=True)
            yield Label("● LIVE", id="live-label")
        yield Label("", id="status-bar")
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
        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.load_personas()

    @work(exclusive=True)
    async def load_personas(self) -> None:
        self.status = "Loading personas…"
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                r = await client.get(f"{self.server}/monitor/personas")
                r.raise_for_status()
                data = r.json()
                self.personas = data.get("personas", [])
                opts = [(p, p) for p in self.personas]
                sel = self.query_one("#persona-select", Select)
                sel.set_options(opts)
                self.status = f"Loaded {len(self.personas)} personas. Select one to begin."
        except Exception as e:
            self.status = f"Error loading personas: {e}"

    # ------------------------------------------------------------------
    # Persona selection
    # ------------------------------------------------------------------

    @on(Select.Changed, "#persona-select")
    async def persona_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        self.selected_persona = str(event.value)
        await self.load_data()

    @work(exclusive=True)
    async def load_data(self) -> None:
        persona = self.selected_persona
        self.status = f"Loading data for {persona}…"
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                conv_r = await client.get(
                    f"{self.server}/monitor/conversations",
                    params={"persona": persona},
                )
                conv_r.raise_for_status()
                trace_r = await client.get(
                    f"{self.server}/monitor/traces",
                    params={"persona": persona},
                )
                trace_r.raise_for_status()

            self.conversations = conv_r.json().get("entries", [])
            self.traces = trace_r.json().get("traces", [])
            self._populate_col1()
            self.status = (
                f"{persona} — {len(self.conversations)} messages, "
                f"{len(self.traces)} traces"
            )

            # Start SSE stream for live updates
            if self._sse_task:
                self._sse_task.cancel()
            if self.live_mode:
                self._sse_task = asyncio.create_task(self._sse_loop(persona))

        except Exception as e:
            self.status = f"Error loading data for {persona}: {e}"

    def _trace_for_conv(self, entry: dict) -> dict | None:
        """Match a conversation entry to its trace by timestamp proximity."""
        conv_ts = entry.get("ts", "")
        for t in self.traces:
            if t.get("ts", "")[:19] == conv_ts[:19]:
                return t
            # Loose match: same user_input prefix
            if (t.get("user_input", "")[:50] == entry.get("user", "")[:50]
                    and t.get("persona") == entry.get("persona")):
                return t
        return None

    def _populate_col1(self) -> None:
        lst = self.query_one("#msg-list", ListView)
        lst.clear()
        for i, entry in enumerate(self.conversations):
            trace = self._trace_for_conv(entry)
            lst.append(MessageBlock(entry, trace, id=f"mb-{i}"))
        # Scroll to bottom (newest)
        if self.conversations:
            lst.index = len(self.conversations) - 1

    # ------------------------------------------------------------------
    # Column 1 → Column 2
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#msg-list")
    def msg_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, MessageBlock):
            return
        self._selected_conv_idx = self.conversations.index(item.entry)
        self._populate_col2(item.entry, item.trace)
        self._clear_col3()

    def _populate_col2(self, entry: dict, trace: dict | None) -> None:
        lst = self.query_one("#log-list", ListView)
        lst.clear()
        if trace is None:
            lst.append(ListItem(Static("[dim]No trace available for this message.[/]")))
            return
        pipeline = trace.get("pipeline", [])
        for i, agent_rec in enumerate(pipeline):
            lst.append(AgentLogItem(agent_rec, id=f"al-{i}"))
            # Show subagents inline as separate (indented) items
            for j, sub in enumerate(agent_rec.get("subagents", [])):
                sub_copy = dict(sub)
                sub_copy["_indent"] = True
                lst.append(AgentLogItem(sub_copy, id=f"al-{i}-sub-{j}"))

    # ------------------------------------------------------------------
    # Column 2 → Column 3
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#log-list")
    def log_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, AgentLogItem):
            return
        self._populate_col3(item.agent_rec)

    def _clear_col3(self) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

    def _populate_col3(self, agent_rec: dict) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

        sections = agent_rec.get("context_sections", {})
        turns = agent_rec.get("turns", [])

        widgets = []

        # Summary header
        name = agent_rec.get("agent", "?")
        provider = agent_rec.get("provider", "")
        model = agent_rec.get("model", "")
        total_in = agent_rec.get("total_input_tokens", 0)
        total_out = agent_rec.get("total_output_tokens", 0)
        dur = agent_rec.get("duration_ms", 0)
        widgets.append(Static(
            f"[bold]{name}[/]  [dim]{provider}[/]  [cyan]{model}[/]\n"
            f"[green]{total_in:,}[/] in / [yellow]{total_out:,}[/] out  [dim]{dur}ms[/]"
        ))

        # Context sections (collapsible)
        section_labels = {
            "agent_file": "Agent Instructions",
            "config": "Config (constitution + goals)",
            "recent_context": "Recent Context",
        }
        for key, label in section_labels.items():
            content = sections.get(key, "")
            if content:
                widgets.append(self._collapsible_text(label, content))

        # Per-turn breakdown
        for t in turns:
            turn_num = t.get("turn", "?")
            t_in = t.get("input_tokens", 0)
            t_out = t.get("output_tokens", 0)
            tool_calls = t.get("tool_calls", [])
            summary = f"Turn {turn_num}  [green]{t_in:,}[/]in [yellow]{t_out:,}[/]out"
            inner_widgets = []
            for tc in tool_calls:
                tc_name = tc.get("name", "?")
                tc_args = json.dumps(tc.get("args", {}), indent=2)
                tc_result = tc.get("result_preview", "")
                tc_dur = tc.get("duration_ms", 0)
                inner_widgets.append(self._collapsible_text(
                    f"⚙ {tc_name}  [dim]{tc_dur}ms[/]",
                    f"Args:\n{tc_args}\n\nResult:\n{tc_result}",
                ))
            if inner_widgets:
                col = Collapsible(*inner_widgets, title=summary, collapsed=True)
            else:
                col = Collapsible(Static("[dim]No tool calls this turn.[/]"),
                                  title=summary, collapsed=True)
            widgets.append(col)

        scroller.mount(*widgets)

    def _collapsible_text(self, title: str, content: str) -> Collapsible:
        return Collapsible(Static(content), title=title, collapsed=True)

    # ------------------------------------------------------------------
    # Live SSE
    # ------------------------------------------------------------------

    async def _sse_loop(self, persona: str) -> None:
        url = f"{self.server}/monitor/stream"
        params = {"persona": persona}
        try:
            async with httpx.AsyncClient(timeout=None) as client:
                async with client.stream("GET", url, params=params) as resp:
                    async for line in resp.aiter_lines():
                        if not line.startswith("data: "):
                            continue
                        raw = line[6:]
                        try:
                            msg = json.loads(raw)
                        except Exception:
                            continue
                        if msg.get("type") == "trace":
                            trace = msg["data"]
                            self.traces.append(trace)
                            # Check if there's a matching conversation entry already;
                            # if not, synthesise one from the trace
                            user_input = trace.get("user_input", "")
                            synth_resp = trace.get("synth_response", "")
                            existing = any(
                                e.get("user", "")[:50] == user_input[:50]
                                for e in self.conversations
                            )
                            if not existing:
                                self.conversations.append({
                                    "ts": trace.get("ts", ""),
                                    "agent": "coordinator",
                                    "persona": trace.get("persona"),
                                    "user": user_input,
                                    "response": synth_resp,
                                })
                            self.call_from_thread(self._refresh_live)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            self.call_from_thread(lambda: setattr(self, "status", f"SSE error: {e}"))

    def _refresh_live(self) -> None:
        self._populate_col1()
        self.status = (
            f"{self.selected_persona} — {len(self.conversations)} messages, "
            f"{len(self.traces)} traces  [live]"
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def action_refresh(self) -> None:
        if self.selected_persona:
            self.load_data()

    def action_toggle_live(self) -> None:
        self.live_mode = not self.live_mode
        label = self.query_one("#live-label", Label)
        if self.live_mode:
            label.update("● LIVE")
            if self.selected_persona and self._sse_task is None:
                self._sse_task = asyncio.create_task(self._sse_loop(self.selected_persona))
        else:
            label.update("○ paused")
            if self._sse_task:
                self._sse_task.cancel()
                self._sse_task = None

    # ------------------------------------------------------------------
    # Reactive watchers
    # ------------------------------------------------------------------

    def watch_status(self, value: str) -> None:
        try:
            self.query_one("#status-bar", Label).update(value)
        except NoMatches:
            pass

    # ------------------------------------------------------------------
    # Drag-to-resize (simple column width adjustment)
    # ------------------------------------------------------------------

    def on_drag_handle(self, handle_id: str, dx: int) -> None:
        # Textual doesn't expose width in characters easily from here;
        # this is a stub for future implementation via CSS width mutation.
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
    app = TheBookApp(server=args.server)
    app.run()


if __name__ == "__main__":
    main()
