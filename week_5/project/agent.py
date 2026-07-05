import os
import re
import sys
import uuid
import json
import time
import asyncio
import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, List
from contextlib import AsyncExitStack

from openai import OpenAI
from dotenv import load_dotenv

from mcp import ClientSession

from tools import run_command, add_todos, get_todos, mark_todo, TOOL_REGISTRY, TOOLS, ToolApprovalRequired

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
MODEL = "openrouter/free"
MAX_ITERATIONS = 40

STORAGE_DIR = Path(BASE_DIR) / ".agent"
SESSIONS_DIR = STORAGE_DIR / "sessions"
AGENTS_PATHS = (Path(BASE_DIR) / "AGENTS.md", STORAGE_DIR / "AGENTS.md")
CONFIG_PATH = Path(BASE_DIR) / "config.json"

BASE_PROMPT = """You are CodeScout, an advanced, adaptive AI system architecture operating across Windows and Linux development hosts. You possess specialized workspace execution skills that you can dynamically load on demand.

CRITICAL WORKSPACE RULES:
1. Always use standard forward slashes (`/`) when declaring file paths in tool arguments.
2. Every tool call to `run_command` executes in a completely fresh, isolated shell instance. Global state changes like `cd` or setting environment variables DO NOT persist.
3. You are FORBIDDEN from navigating directories via `run_command` using `cd`. Use direct paths relative to the workspace root.

DYNAMIC ROLE & TASK ACTIVATION:
1. You have access to specialized skills for various tasks. Analyze the user's initial request carefully.
2. If the user's task requires heavy code editing, engineering, or research workflows, you MUST immediately call `load_skill` to load the appropriate persona runbook before calling any other tool.
3. If the user prompt is a simple conversational message, factual greeting, or casual chat requiring no deep workspace actions, reply directly in plaintext without loading a skill.
"""

def load_mcp_config(path=CONFIG_PATH):
    if not Path(path).exists():
        return {}
    raw = open(path, encoding="utf-8").read()
    def substitute(match):
        var = match.group(1)
        value = os.environ.get(var)
        if value is None:
            raise RuntimeError(f"config.json references ${{{var}}}, but it isn't set in your .env")
        return value
    resolved = re.sub(r"\$\{([A-Z0-9_]+)\}", substitute, raw)
    try:
        return json.loads(resolved).get("mcpServers", {})
    except Exception:
        return {}

class MCPManager:
    def __init__(self):
        self.stack = AsyncExitStack()
        self.active_sessions = {}       
        self.mcp_openai_tools = {}      
        self.tool_to_session = {}       

    async def connect_server(self, name: str, cfg: dict):
        import httpx
        from mcp.client.streamable_http import streamable_http_client
        if name in self.active_sessions:
            return f"Server '{name}' is already connected."
        try:
            custom_headers = cfg.get("headers", {})
            http_client = await self.stack.enter_async_context(
                httpx.AsyncClient(headers=custom_headers)
            )
            read, write, _ = await self.stack.enter_async_context(
                streamable_http_client(
                    url=cfg["url"], 
                    http_client=http_client
                )
            )
            session = await self.stack.enter_async_context(ClientSession(read, write))
            await session.initialize()
            self.active_sessions[name] = session
            self.mcp_openai_tools[name] = []
            tools_list = await session.list_tools()
            for tool in tools_list.tools:
                self.tool_to_session[tool.name] = session
                self.mcp_openai_tools[name].append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.inputSchema,
                    },
                })
            return f"Connected '{name}': {len(tools_list.tools)} tools loaded."
        except Exception as e:
            return f"Failed to connect to '{name}': {str(e)}"

    async def disconnect_server(self, name: str):
        if name not in self.active_sessions:
            return f"Server '{name}' is not currently active."
        tools_to_remove = [tname for tname, sess in self.tool_to_session.items() if sess == self.active_sessions[name]]
        for tname in tools_to_remove:
            del self.tool_to_session[tname]
        del self.active_sessions[name]
        del self.mcp_openai_tools[name]
        return f"Disconnected server '{name}' and cleared its tools."

    async def call_tool(self, name: str, args: dict) -> str:
        result = await self.tool_to_session[name].call_tool(name, args)
        return result.content[0].text if result.content else ""

    async def close(self):
        await self.stack.aclose()

class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None, callback: Callable[[str, Dict[str, Any]], None] = None):
        self.workspace = os.path.abspath(workspace)
        self.messages = []
        self.json_data = None
        self.file_path = None
        self.session_id = session_id
        self.callback = callback or self._default_callback
        self.mcp_manager = MCPManager()
        self.mcp_config = load_mcp_config()
        
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        system_prompt = self._build_system_prompt()

        if not session_id:
            self.session_id = uuid.uuid4().hex[:8]
            self.file_path = SESSIONS_DIR / f"{self.session_id}.json"
            time_now = datetime.now().isoformat(timespec='seconds')
            self.json_data = {
                "id": self.session_id,
                "title": "Untitled",
                "created_at": time_now,
                "updated_at": time_now,
                "messages": [{"role": "system", "content": system_prompt}],
            }
            self.messages = self.json_data["messages"]
            self._save_session()
        else:
            self.file_path = SESSIONS_DIR / f"{session_id}.json"
            with open(self.file_path, "r", encoding="utf-8") as f:
                self.json_data = json.load(f)
            self.messages = self.json_data["messages"]
            if self.messages and self.messages[0]["role"] == "system":
                self.messages[0]["content"] = system_prompt

    def _default_callback(self, event_type: str, data: Dict[str, Any]):
        pass

    def _emit(self, event_type: str, **kwargs):
        self.callback(event_type, kwargs)

    def _load_skills_metadata(self) -> str:
        skills_dir = Path(BASE_DIR) / "skills"
        if not skills_dir.exists() or not skills_dir.is_dir():
            return ""
        skills_list = []
        frontmatter_re = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE)
        for folder in skills_dir.iterdir():
            if folder.is_dir():
                skill_file = folder / "SKILL.md"
                if skill_file.exists():
                    try:
                        content = skill_file.read_text(encoding="utf-8")
                        match = frontmatter_re.match(content)
                        if match:
                            yaml_text = match.group(1)
                            name_match = re.search(r"^name:\s*(.+)$", yaml_text, re.MULTILINE)
                            desc_match = re.search(r"^description:\s*(?:>)?\s*(.+?)(?=\n\w+:|$)", yaml_text, re.DOTALL | re.MULTILINE)
                            if name_match and desc_match:
                                name = name_match.group(1).strip()
                                desc = desc_match.group(1).replace("\n", " ").strip()
                                skills_list.append(f"- **{name}**: {desc}")
                    except Exception:
                        pass 
        if not skills_list:
            return ""
        return (
            "\n\nAVAILABLE SYSTEM SKILLS:\n"
            "If the user task requires any complex workflow listed below, you MUST use the tool "
            "`load_skill` with the matching skill name to get step-by-step instructions before starting.\n"
            + "\n".join(skills_list)
        )

    def _build_system_prompt(self) -> str:
        system_prompt = BASE_PROMPT
        system_prompt += self._load_skills_metadata()
        for agent_path in AGENTS_PATHS:
            if agent_path.exists():
                with open(agent_path, "r", encoding="utf-8") as f:
                    system_prompt += "\n\n" + f.read()
                break
        return system_prompt

    def _save_session(self):
        self.json_data["messages"] = self.messages
        self.json_data["updated_at"] = datetime.now().isoformat(timespec='seconds')
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4)

    async def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        answer = await self._run_loop()
        self._save_session()
        return answer

    async def _run_loop(self) -> str:
        for iteration in range(MAX_ITERATIONS):
            current_todos = get_todos()
            if current_todos and len(current_todos) > 0 and all(t["status"] == "completed" for t in current_todos):
                return f"Task completed successfully! All items resolved in {iteration} steps."

            self._emit("agent_thinking", iteration=iteration)
            combined_tools = list(TOOLS) if TOOLS else []
            for server_tools in self.mcp_manager.mcp_openai_tools.values():
                combined_tools.extend(server_tools)

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=combined_tools if combined_tools else None,
                )
            except Exception as e:
                self._emit("error", message=f"API Connection Error: {str(e)}")
                await asyncio.sleep(2)
                continue

            if not response or not response.choices:
                self._emit("error", message="Empty payload returned from API.")
                await asyncio.sleep(2)
                continue

            choice = response.choices[0]
            message = choice.message
            finish_reason = choice.finish_reason

            msg_dict = {"role": "assistant"}
            if message.content:
                msg_dict["content"] = message.content
            if getattr(message, "tool_calls", None):
                msg_dict["tool_calls"] = [t.model_dump() for t in message.tool_calls]
            
            self.messages.append(msg_dict)

            if finish_reason == "stop":
                if current_todos and len(current_todos) > 0 and any(t["status"] != "completed" for t in current_todos):
                    self.messages.append({
                        "role": "user",
                        "content": "You have remaining uncompleted tasks on your todo tracker list. Resolve them before stopping."
                    })
                    continue
                return message.content or ""

            elif finish_reason == "tool_calls" and getattr(message, "tool_calls", None):
                for tool_call in message.tool_calls:
                    self._emit("tool_call", name=tool_call.function.name, arguments=tool_call.function.arguments)
                    try:
                        result = await self.dispatch(tool_call)
                    except ToolApprovalRequired as approval_event:
                        result = json.dumps(self._handle_ui_approval(approval_event))
                    self._emit("tool_result", name=tool_call.function.name, result=result)
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
                    
        return f"[Agent terminated: Maximum execution limit ({MAX_ITERATIONS}) reached with items left outstanding]"

    def _handle_ui_approval(self, event) -> dict:
        approval_container = {"approved": False, "handled": False}
        self._emit("request_user_approval", 
                   tool_name=event.tool_name, 
                   target=event.target,
                   storage=approval_container)
        if approval_container["handled"]:
            if approval_container["approved"]:
                return event.callback(*event.args, **event.kwargs)
            return json.dumps({
                "exit_code": 1,
                "stdout": "",
                "stderr": f"blocked: user denied execution of {event.tool_name}.",
                "error": "User denied execution"
            })
        print(f"\n [Approval Required]: {event.tool_name} requests permission to run:")
        print(f"    {event.target}")
        choice = input("Allow execution? [y/N]: ").strip().lower()
        if choice == "y":
            return event.callback(*event.args, **event.kwargs)
        return {
            "exit_code": 1,
            "stdout": "",
            "stderr": "blocked: user did not approve this execution request",
            "error": "User denied execution"
        }
    
    async def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception:
            return json.dumps({"success": False, "error": "Invalid JSON arguments layout parsing error."})

        if name in self.mcp_manager.tool_to_session:
            try:
                return await self.mcp_manager.call_tool(name, args)
            except Exception as e:
                return json.dumps({"success": False, "error": f"MCP execution error: {str(e)}"})
        if name not in TOOL_REGISTRY:
            return json.dumps({"success": False, "error": f"Tool '{name}' is not registered."})
        
        try:
            return json.dumps(TOOL_REGISTRY[name](**args))
        except ToolApprovalRequired:
            raise
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})


class REPLAgent:
    def __init__(self, session_id: str | None = None):
        self.agent = Agent(session_id=session_id, callback=self.handle_agent_events)

    def handle_agent_events(self, event_type: str, data: dict):
        if event_type == "agent_thinking":
            print(f" [Thinking Step {data['iteration']}]...", end="\r", file=sys.stderr)
        elif event_type == "tool_call":
            print(f"\n  [Tool Invocation] {data['name']}({data['arguments']})", file=sys.stderr)
        elif event_type == "error":
            print(f"\n  [Error]: {data['message']}", file=sys.stderr)

    async def run(self):
        print(f"CodeScout Engine [{self.agent.session_id}] Active — Enter /quit or /exit to exit.")
        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            if user_input.startswith("/mcp"):
                parts = user_input.split()
                cmd = parts[1] if len(parts) > 1 else ""
                if cmd == "list":
                    print("\n Configured MCP Servers ")
                    for name in self.agent.mcp_config.keys():
                        status = "CONNECTED" if name in self.agent.mcp_manager.active_sessions else "DISCONNECTED"
                        print(f" - {name}: [{status}]")
                    continue
                elif cmd == "enable" and len(parts) > 2:
                    srv_name = parts[2]
                    if srv_name in self.agent.mcp_config:
                        res = await self.agent.mcp_manager.connect_server(srv_name, self.agent.mcp_config[srv_name])
                        print(f"\n{res}")
                    else:
                        print(f"\nServer '{srv_name}' not found in config.json.")
                    continue
                elif cmd == "disable" and len(parts) > 2:
                    srv_name = parts[2]
                    res = await self.agent.mcp_manager.disconnect_server(srv_name)
                    print(f"\n{res}")
                    continue
                else:
                    print("\nUnknown command. Usage: /mcp [list | enable <name> | disable <name>]")
                    continue
            response = await self.agent.chat(user_input)
            print(f"\n{response}")
        await self.agent.mcp_manager.close()

def main():
    parser = argparse.ArgumentParser(
        description="CodeScout: Choose between REPL, TUI, or running a specific session."
    )
    parser.add_argument("--tui", action="store_true", help="Launch the TUI interface")
    parser.add_argument("--session", type=str, metavar="SESSION_ID", help="Specify a session ID")
    parser.add_argument("command", nargs="?", type=str, help="Optional single command to run once")
    args = parser.parse_args()

    if args.tui:
        from tui import CodeScoutApp
        CodeScoutApp.run_app(session_id=args.session)
        return
    
    if args.command:
        agent = Agent(session_id=args.session)
        async def run_single():
            res = await agent.chat(args.command)
            print(f"\n{res}")
            await agent.mcp_manager.close()
        asyncio.run(run_single())
        return

    agent = REPLAgent(session_id=args.session)
    asyncio.run(agent.run())
    
if __name__ == "__main__":
    main()