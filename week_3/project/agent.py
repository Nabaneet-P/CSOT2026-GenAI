"""
Research Desk — Week 3 Project
===============================
Class hierarchy:
  Agent       — brain: chat(), _run_loop(), dispatch(), sessions
  REPLAgent   — terminal REPL + one-shot CLI
  TUIAgent    — Textual UI (in tui.py)

Usage:
  python agent.py                              # REPLAgent.run()
  python agent.py "What is quantum computing?" # REPLAgent.run_once()
  python agent.py --tui                        # TUIAgent.run()
  python agent.py --session abc123 "continue"
"""
import os
import sys
import uuid
import tools
import json
import argparse
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)
MODEL = "openrouter/free"

SESSIONS_DIR = Path("week_3/.agent/sessions")
AGENTS_PATHS = (Path("AGENTS.md"), Path("week_3/.agent/AGENTS.md"))
BASE_PROMPT = """You are Research Desk, a helpful research assistant.
Whenever a user asks you to research a topic, find papers, or look up information, you MUST save your findings by calling the `write_file` or `edit_file` tools to create/update a markdown note file in the `week_3/notes/` directory. 
Do not just output the research in the chat. Your chat response should be a very brief summary pointing to the file you created (e.g., "I have compiled the research notes on this topic in `week_3/notes/computer-vision-advancements.md`").
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
        for _ in range(tools.MAX_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=self.messages,
                tools=tools.TOOLS,
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
        return f"[Agent stopped after {tools.MAX_ITERATIONS} iterations without reaching a final answer]"

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        args = json.loads(tool_call.function.arguments)
        if name not in tools.TOOL_REGISTRY:
            return json.dumps({"success": False, "error": f"Tool \"{name}\" is not registered."})
        tool = tools.TOOL_REGISTRY[name]
        return json.dumps(tool(**args))

    def _emit(self, event: str, **data) -> None:
        pass

class REPLAgent(Agent):
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