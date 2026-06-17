"""
Build 2: Agent + REPLAgent
===========================
Agent = brain (loop, tools, sessions). REPLAgent = terminal UI.

Before running:
  mkdir -p notes

Tasks:
  1. Agent — chat(), run_once(), _run_loop(), dispatch(), _emit(), session I/O
  2. REPLAgent(Agent) — run() interactive loop
  3. resolve_path, read_file, write_file, list_files, edit_file
  4. main() — one-shot: python build2_agent_class.py "hello"

TUIAgent comes in the project (tui.py). No Textual imports here.
"""

import os
import sys
import json
import uuid
import fnmatch
from datetime import datetime
from pathlib import Path
import glob as glob_module
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 10
MAX_READ_CHARS = 12_000

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openrouter/free"

SESSIONS_DIR = Path("week_3/.agent/sessions")
AGENTS_PATHS = (Path("AGENTS.md"), Path("week_3/.agent/AGENTS.md"))

BASE_PROMPT = "You are Research Desk, a helpful research assistant."

# --- File tools ---

def resolve_path(path: str) -> str:
    base = Path(WORKSPACE_ROOT).resolve()
    full = Path(base, path).resolve()
    if not full.is_relative_to(base):
        raise ValueError(f"Path escapes workspace: {path}")
    return str(full)

def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    full = resolve_path(path)
    if not os.path.isfile(full):
        return {"success": False, "error": f"File not found: {path}"}
    with open(full, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
    
    start = start_line-1
    end = start + read_lines
    sliced = lines[start:end]
    data = {
        "success": True,
        "data": {
            "content": "".join(sliced),
            "start_line": start_line,
            "lines_returned": len(sliced),
            "total_lines": len(lines)
        }
    }
    return data

def write_file(path: str, content: str) -> dict:
    try:
        safe_path = resolve_path(path)
        os.makedirs(os.path.dirname(safe_path), exist_ok=True)
        with open(safe_path, "w", encoding="utf-8") as f:
            f.write(content)
        return {"success": True, "message": f"Successfully wrote to {path}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def edit_file(
    path: str,
    operation: str,
    start_line: int,
    end_line: int | None = None,
    content: str | None = None,
) -> dict:
    try:
        full = resolve_path(path)
        if not os.path.isfile(full):
            return {"success": False, "error": f"File not found for editing: {path}"}
        with open(full, "r", encoding="utf-8") as f:
            lines = f.readlines()

        start = start_line - 1
        end = (end_line if end_line is not None else start_line) - 1
        new_lines = [line + '\n' if not line.endswith('\n') else line 
                     for line in (content or "").splitlines()] if content else []

        if operation == "replace":
            lines[start:end + 1] = new_lines
        elif operation == "insert":
            lines[start:start] = new_lines
        elif operation == "delete":
            lines[start:end + 1] = []
        else:
            return {"success": False, "error": f"Unknown operation: {operation}"}

        with open(full, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return {"success": True, "message": f"Operation \"{operation}\" executed successfully."}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_files(path: str = ".", pattern: str = "*") -> dict:
    try:
        full = resolve_path(path)
        if not os.path.isdir(full):
            return {"success": False, "error": f"Directory not found: {path}"}
        matched = []
        for root, _, filenames in os.walk(full):
            for filename in fnmatch.filter(filenames, pattern):
                filepath = os.path.join(root, filename)
                workspace_base = resolve_path(".")
                rel_to_workspace = os.path.relpath(filepath, workspace_base)
                matched.append(rel_to_workspace)
        return {"success": True, "data": {"files": sorted(matched)}}
    except Exception as e:
        return {"success": False, "error": str(e)}

TOOL_DATA = [
    {
        "name": "read_file",
        "description": "Reads specific line ranges from a file securely. Uses 1-indexed line numbers.",
        "function": read_file,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The relative path to the file inside the workspace."},
                "start_line": {"type": "integer", "description": "The 1-indexed line number to start reading from.", "default": 1},
                "read_lines": {"type": "integer", "description": "The total number of lines to read.", "default": 200}
            },
            "required": ["path"]
        }
    },
    {
        "name": "write_file",
        "description": "Creates a new file or overwrites an existing one with new content.",
        "function": write_file,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The relative path where the file should be written."},
                "content": {"type": "string", "description": "The full file text content."}
            },
            "required": ["path", "content"]
        }
    },
    {
        "name": "edit_file",
        "description": "Modifies an existing file via 'replace', 'insert', or 'delete' actions at specific lines.",
        "function": edit_file,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The relative path to the file inside the workspace."},
                "operation": {"type": "string", "description": "The editing action to perform.", "enum": ["replace", "insert", "delete"]},
                "start_line": {"type": "integer", "description": "The 1-based line number where the operation begins."},
                "end_line": {"type": "integer", "description": "The 1-based line number where the operation ends (required for replace/delete)."},
                "content": {"type": "string", "description": "The new content text (required for replace/insert)."}
            },
            "required": ["path", "operation", "start_line"]
        }
    },
    {
        "name": "list_files",
        "description": "Lists files recursively inside a target directory matching a glob pattern.",
        "function": list_files,
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "The directory to scan.", "default": "."},
                "pattern": {"type": "string", "description": "The glob pattern filter (e.g. '*.py').", "default": "*"}
            }
        }
    }
]  

TOOL_REGISTRY = {t["name"]: t["function"] for t in TOOL_DATA}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": tool["name"],
            "description": tool["description"],
            "parameters": tool["parameters"]
        }
    }
    for tool in TOOL_DATA
]

class Agent:
    """Core agent: loop, tools, sessions. No UI."""

    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
        # TODO: session_id, load messages
        system_prompt = build_system_prompt()
        self.messages = []
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        self.json_data = None
        self.file_path = None
        self.session_id = session_id

        if not session_id:
            full_id = uuid.uuid4()
            id = full_id.hex[:8]
            file = f"{id}.json"
            file_path = SESSIONS_DIR / file

            time = datetime.now()
            formatted_time = time.isoformat(timespec='seconds')
            json_data = {
                "id": id,
                "title": "Untitled",
                "created_at": formatted_time,
                "updated_at": formatted_time,
                "messages": [{"role": "system", "content": system_prompt}],
            }
            self.messages = json_data["messages"]
            self.json_data = json_data
            self.file_path = file_path
            self.session_id = id
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(json_data, f, indent=4)
        else:
            file = f"{session_id}.json"
            file_path = SESSIONS_DIR / file
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.messages = data["messages"]
            self.json_data = data
            self.file_path = file_path

    def chat(self, user_message: str) -> str:
        # TODO: append user msg, _run_loop(), save session, return answer
        self.messages.append({"role": "user", "content": user_message})
        answer = self._run_loop()
        self.json_data["messages"] = self.messages
        self.json_data["updated_at"] = datetime.now().isoformat(timespec='seconds')
        with open(self.file_path, "w", encoding="utf-8") as f:
            json.dump(self.json_data, f, indent=4)
        return answer

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)   

    def _run_loop(self) -> str:
        # TODO: agent loop — call self.dispatch(), self._emit() on tool calls
        for _ in range(MAX_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=TOOLS,
            )
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            self.messages.append(message.model_dump(exclude_none=True))
            
            if finish_reason == "stop":
                return message.content if message.content else ""
            elif finish_reason == "tool_calls":
                for tool_call in message.tool_calls:
                    self._emit("tool_call", name=tool_call.function.name, arguments=tool_call.function.arguments)
                    result = self.dispatch(tool_call)
                    
                    self.messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call.id, 
                        "content": result
                    })
        return f"[Agent stopped after {MAX_ITERATIONS} iterations without reaching a final answer]"

    def dispatch(self, tool_call) -> str:
        # TODO: route to file tools, return JSON string
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if name not in TOOL_REGISTRY:
            return json.dumps({"success": False, "error": f"Tool \"{name}\" is not registered."})
        tool = TOOL_REGISTRY[name]
        return json.dumps(tool(**args))

    def _emit(self, event: str, **data) -> None:
        """Override in REPLAgent/TUIAgent for tool logging."""
        pass


class REPLAgent(Agent):
    """Terminal REPL + one-shot CLI."""

    def run(self) -> None:
        print(f"Research Desk [{self.session_id}] — /quit to exit")
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            print(self.chat(user_input))
            print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)


def build_system_prompt() -> str:
    system_prompt = BASE_PROMPT
    agent_path = AGENTS_PATHS[1]
    with open(agent_path, "r", encoding="utf-8") as f:
        system_prompt += "\n\n" + f.read()
    return system_prompt

def main():
    agent = REPLAgent()
    if len(sys.argv) > 1:
        print(agent.run_once(" ".join(sys.argv[1:])))
        return
    agent.run()


if __name__ == "__main__":
    main()
