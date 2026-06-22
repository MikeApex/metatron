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
import sys
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
        Button, Collapsible, Footer, Header, Label, ListItem,
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
        ts = fmt_ts(self.entry.get("ts", ""))
        persona = self.entry.get("persona") or "—"
        user_text = truncate(self.entry.get("user", ""), 80)
        synth_text = truncate(self.entry.get("response", ""), 80)
        is_proactive = self.trace.get("is_proactive", False) if self.trace else False

        if is_proactive:
            header = f"[bold cyan]{ts}[/] [dim]{persona}[/] [yellow]⊕ proactive[/]"
        else:
            header = f"[bold cyan]{ts}[/] [dim]{persona}[/]"

        yield Static(f"{header}\n[dim]You:[/] {user_text}\n[dim]M:[/]  {synth_text}")


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
"""


# ---------------------------------------------------------------------------
# File viewer modal
# ---------------------------------------------------------------------------

class FileViewerScreen(ModalScreen):
    """Full-screen overlay showing the content of a data file."""

    DEFAULT_CSS = """
    FileViewerScreen {
        align: center middle;
    }
    #fv-container {
        width: 90%;
        height: 90%;
        background: $surface;
        border: solid $accent;
        padding: 1 2;
        layout: vertical;
    }
    #fv-title  { height: 1; color: $accent; }
    #fv-scroll { height: 1fr; }
    #fv-footer { height: 1; color: $text-muted; }
    """
    BINDINGS = [Binding("escape,q", "dismiss", "Close")]

    def __init__(self, path: str, content: str, **kwargs):
        super().__init__(**kwargs)
        self._path = path
        self._content = content

    def compose(self) -> ComposeResult:
        with Container(id="fv-container"):
            yield Label(self._path, id="fv-title")
            yield ScrollableContainer(Static(self._content), id="fv-scroll")
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
    ]

    selected_persona: reactive[str | None] = reactive(None)
    live_mode: reactive[bool] = reactive(True)

    def __init__(self, server: str = DEFAULT_SERVER, **kwargs):
        super().__init__(**kwargs)
        self.server = server.rstrip("/")
        self.conversations: list[dict] = []
        self.traces: list[dict] = []
        self._sse_worker = None

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def compose(self) -> ComposeResult:
        yield Header()
        with Container(id="toolbar"):
            yield Select([], id="persona-select", prompt="— select persona —", allow_blank=True)
            yield Label("● LIVE", id="live-label")
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
        yield Footer()

    # ------------------------------------------------------------------
    # Startup
    # ------------------------------------------------------------------

    def on_mount(self) -> None:
        self.load_personas()

    @work(exclusive=True)
    async def load_personas(self) -> None:
        self._set_status("Loading personas…")
        try:
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                r = await client.get(f"{self.server}/monitor/personas")
                r.raise_for_status()
                personas = r.json().get("personas", [])

            sel = self.query_one("#persona-select", Select)
            sel.set_options([(p, p) for p in personas])
            self._set_status(f"Loaded {len(personas)} persona(s). Select one to begin.")
        except Exception as e:
            print(f"[load_personas error] {e}", file=sys.stderr)
            self._set_status(f"Error: {e}")

    # ------------------------------------------------------------------
    # Persona selection
    # ------------------------------------------------------------------

    @on(Select.Changed, "#persona-select")
    def persona_changed(self, event: Select.Changed) -> None:
        if event.value == Select.BLANK:
            return
        self.selected_persona = str(event.value)
        self.load_data()

    @work(exclusive=True)
    async def load_data(self) -> None:
        persona = self.selected_persona
        if not persona:
            return
        self._set_status(f"Loading {persona}…")
        try:
            async with httpx.AsyncClient(timeout=30, verify=False) as client:
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
            self._set_status(
                f"{persona} — {len(self.conversations)} messages, "
                f"{len(self.traces)} traces"
            )

            # Start live SSE stream
            if self._sse_worker is not None:
                self._sse_worker.cancel()
            if self.live_mode:
                self._sse_worker = self.run_worker(
                    self._sse_loop(persona), exclusive=False, name="sse"
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
        for entry in self.conversations:
            trace = self._trace_for_conv(entry)
            lst.append(MessageBlock(entry, trace))
        if self.conversations:
            lst.scroll_end(animate=False)

    def _append_col1(self, entry: dict, trace: dict | None) -> None:
        lst = self.query_one("#msg-list", ListView)
        lst.append(MessageBlock(entry, trace))
        lst.scroll_end(animate=False)

    # ------------------------------------------------------------------
    # Column 1 → Column 2
    # ------------------------------------------------------------------

    @on(ListView.Selected, "#msg-list")
    def msg_selected(self, event: ListView.Selected) -> None:
        item = event.item
        if not isinstance(item, MessageBlock):
            return
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
        await self._populate_col3(item.agent_rec)

    def _clear_col3(self) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

    async def _populate_col3(self, agent_rec: dict) -> None:
        scroller = self.query_one("#detail-scroll", ScrollableContainer)
        scroller.remove_children()

        sections = agent_rec.get("context_sections", {})
        turns = agent_rec.get("turns", [])

        name = agent_rec.get("agent", "?")
        provider = agent_rec.get("provider", "")
        model = agent_rec.get("model", "")
        total_in = agent_rec.get("total_input_tokens", 0)
        total_out = agent_rec.get("total_output_tokens", 0)
        dur = agent_rec.get("duration_ms", 0)

        widgets = [
            Static(
                f"[bold]{name}[/]  [dim]{provider}[/]  [cyan]{model}[/]\n"
                f"[green]{total_in:,}[/] in / [yellow]{total_out:,}[/] out  [dim]{dur}ms[/]"
            )
        ]

        for key, label in [
            ("agent_file", "Agent Instructions"),
            ("config", "Config (constitution + goals)"),
            ("recent_context", "Recent Context"),
        ]:
            content = sections.get(key, "")
            if content:
                widgets.append(Collapsible(Static(content), title=label, collapsed=True))

        for t in turns:
            turn_num = t.get("turn", "?")
            t_in = t.get("input_tokens", 0)
            t_out = t.get("output_tokens", 0)
            tool_calls = t.get("tool_calls", [])
            title = f"Turn {turn_num}  [green]{t_in:,}[/]in  [yellow]{t_out:,}[/]out"

            tc_widgets = []
            for tc in tool_calls:
                tc_name = tc.get("name", "?")
                tc_dur = tc.get("duration_ms", 0)
                tc_args = json.dumps(tc.get("args", {}), indent=2)
                tc_result = tc.get("result_preview", "")
                tc_widgets.append(
                    Collapsible(
                        Static(f"Args:\n{tc_args}\n\nResult:\n{tc_result}"),
                        title=f"⚙ {tc_name}  [dim]{tc_dur}ms[/]",
                        collapsed=True,
                    )
                )

            if tc_widgets:
                widgets.append(Collapsible(*tc_widgets, title=title, collapsed=True))
            else:
                widgets.append(
                    Collapsible(Static("[dim]No tool calls.[/]"), title=title, collapsed=True)
                )

        # Output files written by this agent's tool calls
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
            async with httpx.AsyncClient(timeout=10, verify=False) as client:
                r = await client.get(
                    f"{self.server}/monitor/file", params={"path": path}
                )
                r.raise_for_status()
                data = r.json()
            await self.push_screen(FileViewerScreen(data["path"], data["content"]))
            self._set_status(f"Viewing {path}")
        except Exception as e:
            print(f"[open_file error] {e}", file=sys.stderr)
            self._set_status(f"Cannot read {path}: {e}")

    # ------------------------------------------------------------------
    # Live SSE
    # ------------------------------------------------------------------

    async def _sse_loop(self, persona: str) -> None:
        url = f"{self.server}/monitor/stream"
        try:
            async with httpx.AsyncClient(timeout=None, verify=False) as client:
                async with client.stream("GET", url, params={"persona": persona}) as resp:
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
                            self._append_col1(new_entry, trace)
                        self._set_status(
                            f"{persona} — {len(self.conversations)} messages  ● live"
                        )
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"[sse_loop error] {e}", file=sys.stderr)
            self._set_status(f"SSE disconnected: {e}")

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
            if self.selected_persona and self._sse_worker is None:
                self._sse_worker = self.run_worker(
                    self._sse_loop(self.selected_persona), exclusive=False, name="sse"
                )
        else:
            label.update("○ paused")
            if self._sse_worker is not None:
                self._sse_worker.cancel()
                self._sse_worker = None

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
