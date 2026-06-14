import os
import json
import datetime
import asyncio
from contextlib import AsyncExitStack

import httpx
import requests
import trafilatura
from dotenv import load_dotenv
from openai import OpenAI  

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog

load_dotenv()

ALPHAXIV_MCP_URL = "https://api.alphaxiv.org/mcp/v1"
TOKEN_FILE = ".alphaxiv_tokens.json"

class FileTokenStorage:
    def __init__(self):
        self.tokens = None
        self.client_info = None
        if os.path.exists(TOKEN_FILE):
            try:
                data = json.loads(open(TOKEN_FILE).read())
                if data.get("tokens"):
                    self.tokens = OAuthToken(**data["tokens"])
                if data.get("client_info"):
                    self.client_info = OAuthClientInformationFull(**data["client_info"])
            except Exception:
                pass

    def _save(self):
        data = {}
        if self.tokens:
            data["tokens"] = self.tokens.model_dump(mode="json")
        if self.client_info:
            data["client_info"] = self.client_info.model_dump(mode="json")
        with open(TOKEN_FILE, "w") as f:
            f.write(json.dumps(data, indent=2))

    async def get_tokens(self) -> OAuthToken | None: 
        return self.tokens
        
    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens
        self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None: 
        return self.client_info
        
    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info
        self._save()


class ChatAgent:
    def __init__(self, model="openrouter/free"):
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=os.environ["OPENROUTER_API_KEY"],
        )
        self.model = model
        self.last_response = None
        self.messages = [{
            "role": "system", 
            "content": (
                "You are an elite research agent. Always look up academic topics or specific papers using "
                "the AlphaXiv tools (discover_papers, get_paper_content). Use web_search or smart_fetch "
                "exclusively for general web knowledge, news, or looking up documentation links."
            )
        }]

        self.max_iterations = 10
        self.serper_api_key = os.environ["SERPER_API_KEY"]
        self.unified_tools = []
        self.mcp_session = None
        self.local_schemas = [
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the live web for recent information or general background context.",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "smart_fetch",
                    "description": "Fetch parsed text content from a specific web link.",
                    "parameters": {"type": "object", "properties": {"url": {"type": "string"}}, "required": ["url"]}
                }
            }
        ]

    async def _smart_fetch(self, url: str) -> str:
        def _run():
            try:
                headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
                response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
                response.raise_for_status()
                text = trafilatura.extract(response.text, include_comments=False, include_tables=True)
                content = text or ""
                return content[:8000] + "\n\n[...truncated]" if len(content) > 8000 else content
            except Exception as e:
                return f"Failed to fetch URL: {e}"
        return await asyncio.to_thread(_run)

    async def _web_search(self, query: str, num_results: int = 5) -> list[dict]:
        def _run():
            response = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_api_key, "Content-Type": "application/json"},
                json={"q": query, "num": num_results},
                timeout=10,
            )
            response.raise_for_status()
            results = []
            for item in response.json().get("organic", []):
                results.append({
                    "title": item.get("title", ""),
                    "link": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                })
            return results
        return await asyncio.to_thread(_run)

    async def call_agent(self, user_message: str, log_widget: RichLog):
        self.messages.append({"role": "user", "content": user_message})
        for _ in range(self.max_iterations):
            def _get_completion():
                return self.client.chat.completions.create(
                    model=self.model,
                    messages=self.messages,
                    tools=self.unified_tools if self.unified_tools else None
                )
            
            response = await asyncio.to_thread(_get_completion)
            self.last_response = response

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            self.messages.append(message.model_dump(exclude_none=True))
            
            if finish_reason == "stop":
                log_widget.write(f"[bold blue][Assistant][/bold blue] {message.content}\n")
                break
                
            elif finish_reason == "tool_calls":
                for tool_call in message.tool_calls:
                    name = tool_call.function.name
                    args = json.loads(tool_call.function.arguments)
                    
                    if name == "web_search":
                        log_widget.write(f"[italic magenta] -> [Executing LOCAL: web_search][/italic magenta]\n")
                        res = await self._web_search(**args)
                        output = str(res)
                    elif name == "smart_fetch":
                        log_widget.write(f"[italic magenta] -> [Executing LOCAL: smart_fetch][/italic magenta]\n")
                        output = await self._smart_fetch(**args)
                    else:
                        log_widget.write(f"[italic magenta] -> [Executing REMOTE ALPHAXIV: {name}][/italic magenta]\n")
                        mcp_result = await self.mcp_session.call_tool(name, args)
                        output = "".join([c.text for c in mcp_result.content])
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": name,
                        "content": output
                    })
    
    def write_token_usage(self, log_widget: RichLog) -> None:
        if self.last_response and hasattr(self.last_response, "usage"):
            usage = self.last_response.usage
            log_widget.write("\n[bold yellow] Token Usage Summary [/bold yellow]")
            log_widget.write(f"[bold] Prompt Tokens:[/bold] {usage.prompt_tokens}")
            log_widget.write(f"[bold] Completion Tokens:[/bold] {usage.completion_tokens}")
            log_widget.write(f"[bold magenta] Total Tokens Used:[/bold magenta] {usage.total_tokens}\n")
        else:
            log_widget.write("\n[italic red]No API token history compiled for this session yet.[/italic red]\n")


class ChatApp(App):
    TITLE = "Research Chatbot TUI"
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
        Binding("ctrl+t", "show_tokens", "Token Usage"),
        Binding("f2", "export_research", "Export Session"),
    ]

    def __init__(self):
        super().__init__()
        self.agent = ChatAgent()
        self._exit_stack = AsyncExitStack()
        self._agent_worker = None 

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        yield RichLog(id="log", wrap=True, markup=True, highlight=True)
        yield Input(placeholder="Initializing connection... Please wait.", disabled=True)
        yield Footer()

    def on_mount(self) -> None:
        log = self.query_one("#log", RichLog)
        log.write("[bold blue]Initializing AlphaXiv Client Engine...[/bold blue]")
        self.run_worker(self._initialize_agent())

    async def _initialize_agent(self) -> None:
        log = self.query_one("#log", RichLog)
        storage = FileTokenStorage()
        tokens = await storage.get_tokens()
        if not tokens or not tokens.access_token:
            log.write("[bold red]Error: No active login credentials session parsed.[/bold red]")
            log.write("[yellow]Please execute 'ouath.py' on the terminal line first.[/yellow]")
            return
        log.write("[bold green]Loading stored AlphaXiv credentials...[/bold green]")

        try:
            headers = {
                "Authorization": f"Bearer {tokens.access_token}"
            }
            
            http = await self._exit_stack.enter_async_context(
                httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=60)
            )
            read, write, _ = await self._exit_stack.enter_async_context(
                streamable_http_client(ALPHAXIV_MCP_URL, http_client=http)
            )
            self.agent.mcp_session = await self._exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            
            await self.agent.mcp_session.initialize()
            mcp_tools = await self.agent.mcp_session.list_tools()
            self.agent.unified_tools = list(self.agent.local_schemas)
            for remote_tool in mcp_tools.tools:
                self.agent.unified_tools.append({
                    "type": "function",
                    "function": {
                        "name": remote_tool.name,
                        "description": remote_tool.description, 
                        "parameters": remote_tool.inputSchema
                    }
                })
            log.write("[bold magenta]Initialization Succeeded! Agent is active.[/bold magenta]\n")
            input_field = self.query_one(Input)
            input_field.disabled = False
            input_field.placeholder = "Type a message and press Enter..."
            input_field.focus()

        except Exception as e:
            log.write(f"[bold red]Initialization Critical Failure: {e}[/bold red]\n")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        user_text = event.value.strip()
        if not user_text:
            return
        event.input.clear()
        log = self.query_one("#log", RichLog)
        log.write(f"[bold cyan][You][/bold cyan] {user_text}\n")
        self._agent_worker = self.run_worker(self.agent.call_agent(user_text, log))

    async def action_quit(self) -> None:
        if self._agent_worker and self._agent_worker.is_running:
            self._agent_worker.cancel()
            try: 
                await self._agent_worker.wait()
            except asyncio.CancelledError: 
                pass 

        try: 
            await self._exit_stack.aclose()
        except Exception: 
            pass
        self.exit()
    
    def _save_research_to_file(self) -> str:
        if not self.agent.messages or len(self.agent.messages) <= 1:
            return ""
        output_dir = "research_history"
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = os.path.join(output_dir, f"research_{timestamp}.md")

        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Research Log\n")
            f.write(f"Exported: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Model Engine: {self.agent.model}\n\n")
            f.write("---\n\n")

            for msg in self.agent.messages:
                role = msg.get("role", "").upper()
                content = msg.get("content", "")
                if role == "SYSTEM" or not content:
                    continue
                if role == "TOOL":
                    f.write(f"### Search API/Tool Invoked: \"{msg.get('name')}\"\n")
                    f.write(f"> **Preview data:** {content[:350]}...\n\n")
                    continue

                display_name = "User Query" if role == "USER" else "Research Assistant"
                f.write(f"## {display_name}\n")
                f.write(f"{content}\n\n")
                f.write("---\n\n")

        return filename
    
    def action_export_research(self) -> None:
        log = self.query_one("#log", RichLog)
        try:
            filename = self._save_research_to_file()
            if filename:
                log.write(f"\n[bold green] Export Successful: {filename}[/bold green]\n")
                self.notify(f" Saved session output to {filename}", title="Session Exported", severity="information")
            else:
                log.write("\n[italic yellow] Export Interrupted: No conversation history recorded yet.[/italic yellow]\n")
        except Exception as e:
            log.write(f"\n[bold red] Failed to write export file: {e}[/bold red]\n")
    
    def action_clear_display(self) -> None:
        self.query_one("#log", RichLog).clear()

    def action_clear_history(self) -> None:
        self.agent.messages = [self.agent.messages[0]] if self.agent.messages else []
        log = self.query_one("#log", RichLog)
        log.clear()
        log.write("[dim gray]Conversation history cleared.[/dim gray]\n")

    def action_show_tokens(self) -> None:
        log = self.query_one("#log", RichLog)
        self.agent.write_token_usage(log)

if __name__ == "__main__":
    ChatApp().run()