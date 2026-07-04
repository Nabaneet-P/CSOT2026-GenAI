from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container
from textual.widgets import Header, Footer, Input, RichLog
from agent import Agent
from typing import Optional, Dict, Any

class ResearchDeskApp(App):
    TITLE = "Research Desk TUI"
    CSS = """
    Screen { layout: vertical; }
    #main-container {
        layout: grid;
        grid-size: 2;
        grid-columns: 7fr 3fr;
        height: 1fr;
    }
    RichLog { height: 1fr; border: solid $primary; padding: 0 1; }
    Input { dock: bottom; height: 3; }
    """
    theme = "dracula"

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, session_id: Optional[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.session_id = session_id
        self.agent: Optional[Agent] = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="main-container"):
            yield RichLog(id="chat-log", wrap=True, highlight=True, markup=True)
            yield RichLog(id="tool-log", wrap=True, highlight=True, markup=True)
        yield Input(placeholder="Ask Research Desk anything... (Press Enter)")
        yield Footer()

    def on_mount(self) -> None:
        self.agent = Agent(
            session_id=self.session_id, 
            callback=self.handle_agent_events
        )
        chat_log = self.query_one("#chat-log", RichLog)
        display_session = self.agent.session_id if self.agent.session_id else "Default"
        chat_log.write(f"[bold green]Welcome to Research Desk[/bold green] [bold red][Session: {display_session}][/bold red]")

    def handle_agent_events(self, event_type: str, data: Dict[str, Any]) -> None:
        tool_log = self.query_one("#tool-log", RichLog)
        if event_type == "tool_call":
            tool_name = data.get('name')
            log_line = f"[bold blue][Tool Call][/bold blue] [bold red]Executing: {tool_name}[/bold red]"
            self.call_from_thread(tool_log.write, log_line)
        elif event_type == "agent_thinking":
            step = data.get('iteration', 0)
            log_line = f"[bold yellow][Thinking][/bold yellow] Step {step} processing..."
            self.call_from_thread(tool_log.write, log_line)
        elif event_type == "error":
            err_msg = data.get('message', 'Unknown Error')
            log_line = f"[bold red][Error][/bold red] {err_msg}"
            self.call_from_thread(tool_log.write, log_line)

    def action_clear_display(self) -> None:
        chat_log = self.query_one("#chat-log", RichLog)
        tool_log = self.query_one("#tool-log", RichLog)
        chat_log.clear()
        tool_log.clear()
        display_session = self.agent.session_id if self.agent and self.agent.session_id else "Default"
        chat_log.write(f"[bold green]Display Cleared.[/bold green] [bold red][Session: {display_session}][/bold red]")

    def action_clear_history(self) -> None:
        if not self.agent:
            return
        input_widget = self.query_one(Input)
        if input_widget.disabled:
            self.query_one("#chat-log", RichLog).write("[bold red]Cannot reset context while the Agent is running an execution loop.[/bold red]")
            return
        chat_log = self.query_one("#chat-log", RichLog)
        tool_log = self.query_one("#tool-log", RichLog)
        base_system_prompt = self.agent.messages[0]
        self.agent.messages = [base_system_prompt]
        self.agent._save_session() 
        chat_log.clear()
        tool_log.clear()
        chat_log.write("[bold yellow]Conversation history and context memory have been reset[/bold yellow]")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        user_message = event.value.strip()
        if not user_message:
            return
        input_widget = event.input
        chat_log = self.query_one("#chat-log", RichLog)
        input_widget.value = ""
        chat_log.write(f"\n[bold cyan][You][/bold cyan] {user_message}")
        input_widget.disabled = True
        self.run_worker(self.process_agent_chat(user_message, chat_log, input_widget), thread=True)

    async def process_agent_chat(self, message: str, chat_log: RichLog, input_widget: Input) -> None:
        try:
            if self.agent:
                answer = self.agent.chat(message)
                chat_log.write(f"[bold blue][Research Desk][/bold blue] {answer}")
        except Exception as e:
            chat_log.write(f"[bold red]Error Processing Request:[/bold red] {str(e)}")
        finally:
            input_widget.disabled = False
            input_widget.focus()

    @classmethod
    def run_app(cls, session_id: Optional[str] = None):
        app = cls(session_id=session_id)
        app.run()

if __name__ == "__main__":
    ResearchDeskApp.run_app()