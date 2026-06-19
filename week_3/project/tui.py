"""
TUIAgent — full-screen Textual UI inheriting from Agent.

Usage:
  python agent.py --tui

Tasks:
  1. class TUIAgent(Agent) — override _emit() for tool log panel
  2. class ResearchDeskApp(App) — layout, input, key bindings
  3. on_input_submitted -> worker -> self.chat() (inherited from Agent)
  4. Ctrl+L / Ctrl+K / Ctrl+Q from Week 2
"""
from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Input, Log, RichLog
from agent import Agent

from contextlib import AsyncExitStack

class TUIAgent(Agent):
    def __init__(self, app_log: RichLog, **kwargs):
        super().__init__(**kwargs)
        self.app_log = app_log

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            tool_name = data.get('name')
            self.app_log.write(f"[Tool Call] Executing: {tool_name}")

class ResearchDeskApp(App):
    TITLE = "Research Desk TUI"
    CSS = """
    Screen { layout: vertical; }
    RichLog { height: 1fr; border: solid $primary; padding: 0 1; }
    Input { dock: bottom; height: 3; }
    """
    theme = "dracula"

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
            yield RichLog(id="tool-log", wrap=True, highlight=True)
        yield Input(placeholder="Ask Research Desk anything... (Press Enter)")
        yield Footer()

    def on_mount(self) -> None:
        tool_log_widget = self.query_one("#tool-log", RichLog)
        self.agent = TUIAgent(app_log=tool_log_widget)
        chat_log = self.query_one("#chat-log", RichLog)
        chat_log.write(f"--- Welcome to Research Desk [Session: {self.agent.session_id}] ---")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_message = event.value.strip()
        input_widget = event.input
        chat_log = self.query_one("#chat-log", RichLog)
        input_widget.value = ""
        chat_log.write(f"\n[bold blue]You:[/bold blue] {user_message}")
        input_widget.disabled = True
        self.run_worker(self.process_agent_chat(user_message, chat_log, input_widget), thread=True)

    async def process_agent_chat(self, message: str, chat_log: RichLog, input_widget: Input) -> None:
        try:
            answer = self.agent.chat(message)
            chat_log.write(f"[bold green]Research Desk:[/bold green] {answer}")
        except Exception as e:
            chat_log.write(f"[bold red]Error:[/bold red] {str(e)}")
        finally:
            input_widget.disabled = False
            input_widget.focus()

    @classmethod
    def run_app(cls):
        app = cls()
        app.run()