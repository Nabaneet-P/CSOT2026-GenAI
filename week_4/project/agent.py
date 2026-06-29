import os
import sys
import uuid
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
from tools import run_command, add_todos, get_todos, mark_todo, TOOL_REGISTRY, TOOLS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openrouter/free"
MAX_ITERATIONS = 40

STORAGE_DIR = Path(BASE_DIR) / ".agent"
SESSIONS_DIR = STORAGE_DIR / "sessions"
AGENTS_PATHS = (Path(BASE_DIR) / "AGENTS.md", STORAGE_DIR / "AGENTS.md")

BASE_PROMPT = """You are Code Scout, a highly organized software engineering and research assistant.

INSTRUCTIONS:
1. When assigned a multi-step task, break it down into explicit engineering items via `add_todos` immediately.
2. Track execution progress iteratively. You are FORBIDDEN from finishing your task until all scheduled todo list actions are successfully marked as "completed".
3. Any todo items involving text/code updates must run and pass explicit testing validation parameters via `run_command` before updating status via `mark_todo`.
4. If you need to make code updates or create notes, use the `write_file` or `edit_file` tools.
"""

class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
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
        for iteration in range(MAX_ITERATIONS):
            time.sleep(5)
            current_todos = get_todos()
            if current_todos and all(t["status"] == "completed" for t in current_todos):
                return f"Task completed successfully! All items resolved in {iteration} steps."

            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=TOOLS,
                )
            except Exception as e:
                print(f"\n[API Connection Error]: {e}.", file=sys.stderr)
                continue
            if not response or not getattr(response, "choices", None) or len(response.choices) == 0:
                print(f"\n[API Warning]: OpenRouter returned an empty payload. ", file=sys.stderr)
                time.sleep(5)
                continue

            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason
            self.messages.append(message.model_dump(exclude_none=True))
            
            if finish_reason == "stop":
                if current_todos and any(t["status"] != "completed" for t in current_todos):
                    self.messages.append({
                        "role": "user",
                        "content": "You have remaining uncompleted tasks on your todo tracker list. Resolve them."
                    })
                    continue
                elif not current_todos:
                    print("\n[System]: Agent failed to initialize todos.", file=sys.stderr)
                    self.messages.append({
                        "role": "user",
                        "content": "CRITICAL: You must call `add_todos` immediately in your next turn to outline your plan. Do not reply with normal text until you do so.",
                    })
                    continue
                return message.content if message.content else ""
                
            elif finish_reason == "tool_calls" and message.tool_calls:
                for tool_call in message.tool_calls:
                    self._emit("tool_call", name=tool_call.function.name, arguments=tool_call.function.arguments)
                    result = self.dispatch(tool_call)
                    
                    self.messages.append({
                        "role": "tool", 
                        "tool_call_id": tool_call.id, 
                        "content": result
                    })
        return f"[Agent terminated: Maximum iteration limit ({MAX_ITERATIONS}) reached with active items left outstanding]"

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception:
            return json.dumps({"success": False, "error": "Invalid JSON arguments payload layout."})

        if name not in TOOL_REGISTRY:
            return json.dumps({"success": False, "error": f"Tool \"{name}\" is not registered."})
        
        try:
            return json.dumps(TOOL_REGISTRY[name](**args))
        except Exception as e:
            return json.dumps({"success": False, "error": str(e)})

    def _emit(self, event: str, **data) -> None:
        pass

class REPLAgent(Agent):
    def run(self) -> None:
        print(f"Code Scout [{self.session_id}] — /quit to exit")
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
    for agent_path in AGENTS_PATHS:
        if agent_path.exists():
            with open(agent_path, "r", encoding="utf-8") as f:
                system_prompt += "\n\n" + f.read()
            break
    return system_prompt

def main():
    parser = argparse.ArgumentParser(
        description="Code Scout: A software engineering assistant"
    )
    parser.add_argument("--session", type=str, metavar="SESSION_ID", help="Specify a session ID")
    parser.add_argument("command", nargs="?", type=str, help="Optional single command to run once")
    args = parser.parse_args()
    
    if args.command:
        agent = Agent(session_id=args.session)
        print(agent.run_once(args.command))
        return

    agent = REPLAgent(session_id=args.session)
    agent.run()

if __name__ == "__main__":
    main()