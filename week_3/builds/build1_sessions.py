"""
Build 1: Session Store
========================
Save and resume conversations on disk. Load AGENTS.md into the system prompt.

Tasks:
  1. create_session() -> session_id
  2. save_session(session_id, messages, title?)
  3. load_session(session_id) -> {id, title, messages, ...}
  4. list_sessions() -> [{id, title, updated_at}, ...]
  5. build_system_prompt() -> base + AGENTS.md contents

Run twice: save a session in run 1, load it in run 2 and confirm messages restored.
"""

import json
import os
import uuid
from pathlib import Path
from datetime import datetime

SESSIONS_DIR = Path("week_3/.agent/sessions")
AGENTS_PATHS = (Path("AGENTS.md"), Path("week_3/.agent/AGENTS.md"))

BASE_PROMPT = "You are Research Desk, a helpful research assistant."


def create_session() -> str:
    """Return a new 8-char hex session ID."""
    SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
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
        "messages": [{"role": "system", "content": build_system_prompt()}],
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)
    print(f"Session file created at: {file_path}")
    return id

def save_session(session_id: str, messages: list, title: str = "Untitled") -> None:
    """Write session JSON to .agent/sessions/{id}.json"""
    time = datetime.now()
    formatted_time = time.isoformat(timespec='seconds')
    file = f"{session_id}.json"
    file_path = SESSIONS_DIR / file

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    created = data["created_at"]

    json_data = {
        "id": session_id,
        "title": title,
        "created_at": created,
        "updated_at": formatted_time,
        "messages": messages,
    }
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=4)

def load_session(session_id: str) -> dict:
    """Load and return session dict including messages list."""
    file = f"{session_id}.json"
    file_path = SESSIONS_DIR / file
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data

def list_sessions() -> list[dict]:
    """Return sessions sorted by updated_at descending."""
    sessions = []
    for file_path in SESSIONS_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                session = json.load(f)
                sessions.append({
                    "id": session["id"],
                    "title": session["title"],
                    "updated_at": datetime.fromisoformat(session["updated_at"])
                })
        except (json.JSONDecodeError, KeyError):
            continue
    sessions.sort(key=lambda x: x["updated_at"], reverse=True)
    return sessions[:5]

def build_system_prompt() -> str:
    """Base prompt + AGENTS.md if it exists."""
    system_prompt = BASE_PROMPT
    agent_path = AGENTS_PATHS[1]
    with open(agent_path, "r", encoding="utf-8") as f:
        system_prompt += "\n\n" + f.read()
    return system_prompt

if __name__ == "__main__":
    sid = create_session()
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": "What is a surface code?"},
        {"role": "assistant", "content": "A surface code is a type of quantum error correcting code."},
    ]
    save_session(sid, messages, title="Quantum error correction")
    print(f"Saved session: {sid}")
    print(list_sessions())