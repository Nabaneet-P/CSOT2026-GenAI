import os
import sys
import uuid
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Callable, Dict, Any, List
from openai import OpenAI
from dotenv import load_dotenv

from tools import run_command, add_todos, get_todos, mark_todo, TOOL_REGISTRY, TOOLS

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

BASE_PROMPT = """You are Code Scout, a highly organized software engineering and research assistant built to operate universally across Windows and Linux development hosts.

CRITICAL WORKSPACE RULES:
1. System Path Agnosticism: Always use standard forward slashes (`/`) when declaring file paths in tool arguments. The underlying framework will automatically normalize them to the host operating system's standards.
2. Every tool call to `run_command` executes in a completely fresh, isolated shell instance. Global state changes like changing directories (`cd`) or setting environment variables DO NOT persist across tool calls.
3. You are FORBIDDEN from navigating directories via `run_command` using `cd`. You must always provide direct paths relative to the workspace root directory for all commands.

TOOL SELECTION PRIORITIES:
- To discover project structures or find files: Use `list_files`. DO NOT use host-specific commands like `dir` or `ls`.
- To inspect file code contents safely: Use `read_file` with explicit line slicing boundaries.
- To map classes/functions within Python assets quickly: Use `list_definitions`.

TASK TRACKING & EXECUTION:
1. When assigned a multi-step engineering or research task, you MUST break it down into explicit items via `add_todos` before invoking any other tool. This is mandatory for execution.
2. Track execution progress iteratively. Update item statuses instantly using `mark_todo` as they are completed; do not batch updates at the end.
3. A todo item involving text/code updates is FORBIDDEN from being marked as "completed" unless a relevant test or script has been executed via `run_command` and exits with code 0. You must cite this exit code in the evidence block.
4. If the user prompt is a simple conversational message or factual greeting requiring no software edits, reply directly with plaintext.
"""

class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None, callback: Callable[[str, Dict[str, Any]], None] = None):
        self.workspace = os.path.abspath(workspace)
        self.messages = []
        self.json_data = None
        self.file_path = None
        self.session_id = session_id
        self.callback = callback or self._default_callback
        
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

    def _build_system_prompt(self) -> str:
        system_prompt = BASE_PROMPT
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

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        answer = self._run_loop()
        self._save_session()
        return answer

    def _run_loop(self) -> str:
        for iteration in range(MAX_ITERATIONS):
            current_todos = get_todos()
            if current_todos and len(current_todos) > 0 and all(t["status"] == "completed" for t in current_todos):
                return f"Task completed successfully! All items resolved in {iteration} steps."

            self._emit("agent_thinking", iteration=iteration)
            
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=TOOLS if TOOLS else None,
                )
            except Exception as e:
                self._emit("error", message=f"API Connection Error: {str(e)}")
                time.sleep(2)
                continue

            if not response or not response.choices:
                self._emit("error", message="Empty payload returned from API.")
                time.sleep(2)
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
                    result = self.dispatch(tool_call)
                    self._emit("tool_result", name=tool_call.function.name, result=result)
                    
                    self.messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result
                    })
                    
        return f"[Agent terminated: Maximum execution limit ({MAX_ITERATIONS}) reached with items left outstanding]"

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception:
            return json.dumps({"success": False, "error": "Invalid JSON arguments layout parsing error."})

        if name not in TOOL_REGISTRY:
            return json.dumps({"success": False, "error": f"Tool '{name}' is not registered."})
        
        try:
            return json.dumps(TOOL_REGISTRY[name](**args))
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

    def run(self):
        print(f"Code Scout Engine [{self.agent.session_id}] Active — Enter /quit or /exit to exit.")
        while True:
            try:
                user_input = input("\n> ").strip()
            except (EOFError, KeyboardInterrupt):
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            response = self.agent.chat(user_input)
            print(f"\n{response}")

def main():
    parser = argparse.ArgumentParser(
        description="Research Desk: Choose between REPL, TUI, or running a specific session."
    )
    parser.add_argument("--tui", action="store_true", help="Launch the TUI interface")
    parser.add_argument("--session", type=str, metavar="SESSION_ID", help="Specify a session ID")
    parser.add_argument("command", nargs="?", type=str, help="Optional single command to run once")
    args = parser.parse_args()

    if args.tui:
        from tui import ResearchDeskApp
        ResearchDeskApp.run_app(session_id=args.session)
        return
    
    if args.command:
        agent = Agent(session_id=args.session)
        agent.run_once(args.command)
        return

    agent = REPLAgent(session_id=args.session)
    agent.run()
    
if __name__ == "__main__":
    main()