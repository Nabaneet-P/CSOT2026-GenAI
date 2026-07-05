import threading
from typing import Optional, Dict, Any
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Grid
from textual.widgets import Header, Footer, Input, RichLog, Label, Button
from textual.screen import ModalScreen
from agent import Agent

class ConfirmModal(ModalScreen[bool]):
    def __init__(self, title: str, body: str):
        super().__init__()
        self.title_text = title
        self.body_text = body

    def compose(self) -> ComposeResult:
        yield Grid(
            Label(f"[bold yellow]{self.title_text}[/bold yellow]", id="modal-title"),
            Label(self.body_text, id="modal-body"),
            Button("Approve", variant="success", id="btn-approve"),
            Button("Deny", variant="error", id="btn-deny"),
            id="modal-dialog"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-approve":
            self.dismiss(True)
        else:
            self.dismiss(False)

class CodeScoutApp(App):
    TITLE = "CodeScout TUI"
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

    ConfirmModal {
        align: center middle;
        background: rgba(0, 0, 0, 0.6);
    }
    #modal-dialog {
        layout: grid;
        grid-size: 2;
        grid-columns: 1fr 1fr;
        padding: 1 2;
        background: $surface;
        border: thick $primary;
        width: 65;
        height: 18;
    }
    #modal-title { 
        column-span: 2; 
        text-align: center; 
        margin-bottom: 1; 
        text-style: bold; 
        color: $accent;
    }
    #modal-body { 
        column-span: 2; 
        margin-bottom: 1; 
        height: 5;
    }
    #btn-approve { width: 100%; }
    #btn-deny { width: 100%; }
    """
    theme = "tokyo-night"

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
        yield Input(placeholder="Ask CodeScout anything... (Press Enter)")
        yield Footer()

    def on_mount(self) -> None:
        self.agent = Agent(
            session_id=self.session_id, 
            callback=self.handle_agent_events
        )
        chat_log = self.query_one("#chat-log", RichLog)
        display_session = self.agent.session_id if self.agent.session_id else "Default"
        chat_log.write(f"[bold green]Welcome to CodeScout[/bold green] [bold red][Session: {display_session}][/bold red]")

    async def on_unmount(self) -> None:
        if self.agent and self.agent.mcp_manager:
            try:
                await self.agent.mcp_manager.close()
            except RuntimeError as e:
                if "cancel scope" in str(e):
                    pass
                else:
                    raise e

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
        elif event_type == "request_user_approval":
            evt = threading.Event()
            self.call_from_thread(lambda: self.run_worker(self.process_ui_approval(data, evt)))
            evt.wait()

    async def process_ui_approval(self, data: Dict[str, Any], evt: threading.Event) -> None:
        modal = ConfirmModal(
            title=f"Security Confirmation: {data['tool_name']}",
            body=f"The agent is attempting to run:\n\n{data['target']}"
        )
        approved = await self.push_screen_wait(modal)
        data["storage"]["approved"] = bool(approved)
        data["storage"]["handled"] = True
        evt.set()

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
        
        if user_message.startswith("/mcp"):
            parts = user_message.split()
            cmd = parts[1] if len(parts) > 1 else ""
            if cmd == "list":
                chat_log.write("\n[bold yellow]Configured MCP Servers:[/bold yellow]")
                for name in self.agent.mcp_config.keys():
                    status = "CONNECTED" if name in self.agent.mcp_manager.active_sessions else "DISCONNECTED"
                    chat_log.write(f" - {name}: [{status}]")
            elif cmd == "enable" and len(parts) > 2:
                srv_name = parts[2]
                if srv_name in self.agent.mcp_config:
                    res = await self.agent.mcp_manager.connect_server(srv_name, self.agent.mcp_config[srv_name])
                    chat_log.write(f"\n[green]{res}[/green]")
                else:
                    chat_log.write(f"\n[red]Server '{srv_name}' not found in config.json.[/red]")
            elif cmd == "disable" and len(parts) > 2:
                srv_name = parts[2]
                res = await self.agent.mcp_manager.disconnect_server(srv_name)
                chat_log.write(f"\n[yellow]{res}[/yellow]")
            else:
                chat_log.write("\nUnknown command. Usage: /mcp [list | enable <name> | disable <name>]")
            
            input_widget.disabled = False
            input_widget.focus()
            return
        self.run_worker(self.process_agent_chat(user_message, chat_log, input_widget), thread=False)

    async def process_agent_chat(self, message: str, chat_log: RichLog, input_widget: Input) -> None:
        try:
            if self.agent:
                answer = await self.agent.chat(message)
                chat_log.write(f"[bold blue][CodeScout][/bold blue] {answer}")
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
    CodeScoutApp.run_app()