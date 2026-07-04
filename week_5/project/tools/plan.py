import json
import os
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))
STORAGE_DIR = os.path.join(PROJECT_DIR, ".agent")
TODO_FILE = os.path.join(STORAGE_DIR, "todos.json")

def _load_todos() -> List[Dict[str, Any]]:
    if not os.path.exists(TODO_FILE):
        return []
    try:
        with open(TODO_FILE, "r") as f:
            return json.load(f)
    except json.JSONDecodeError:
        return []

def _save_todos(todos: List[Dict[str, Any]]) -> None:
    os.makedirs(STORAGE_DIR, exist_ok=True)
    with open(TODO_FILE, "w") as f:
        json.dump(todos, f, indent=2)

def add_todos(todos: List[Dict[str, str]]) -> str:
    current_todos = _load_todos()
    next_id = max([t["id"] for t in current_todos], default=0) + 1
    added_ids = []
    for todo in todos:
        new_todo = {
            "id": next_id,
            "title": todo["title"],
            "description": todo["description"],
            "verification_method": todo["verification_method"],
            "status": "pending"
        }
        current_todos.append(new_todo)
        added_ids.append(next_id)
        next_id += 1
        
    _save_todos(current_todos)
    return f"Successfully added {len(added_ids)} todo(s). IDs: {added_ids}"


def get_todos(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    todos = _load_todos()
    if status_filter:
        todos = [t for t in todos if t["status"] == status_filter]
    return todos

def mark_todo(todo_id: int, status: str, evidence: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    allowed_statuses = ["pending", "in_progress", "completed", "blocked"]
    if status not in allowed_statuses:
        return {"error": f"Invalid status '{status}'. Must be one of {allowed_statuses}."}
    todos = _load_todos()
    todo_item = next((t for t in todos if t["id"] == todo_id), None)
    if not todo_item:
        return {"error": f"Todo with ID {todo_id} not found."}
    if status == "completed":
        if not evidence:
            return {
                "error": (
                    f"Cannot mark todo #{todo_id} as 'completed' without evidence. "
                    f"You must provide the execution results of: '{todo_item['verification_method']}'"
                )
            }
        exit_code = evidence.get("exit_code")
        if exit_code is None or exit_code != 0:
            return {
                "error": (
                    f"Verification failed for todo #{todo_id}. "
                    f"The verification command exited with code {exit_code} (Expected: 0). "
                    f"Fix the issue and re-verify before completing."
                )
            }
    todo_item["status"] = status
    _save_todos(todos)
    return {"success": f"Todo #{todo_id} ('{todo_item['title']}') updated to status: '{status}'."}