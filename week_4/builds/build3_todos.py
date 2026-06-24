"""
Build 3: Todo Tools
======================
A todo list the model maintains itself — what it's planning to do, what
it's actually done, and how it'll know each item really worked.

This build is intentionally less prescriptive than Builds 1 and 2. You
decide the exact shape of a todo and how the list is stored — in memory,
in a dict, in a JSON file under .agent/, however you like. The one hard
requirement, from Lesson 2: every todo needs a short title, a
description, and a verification method — some concrete, checkable way
to know the item is actually done ("run pytest tests/test_auth.py and
confirm exit code 0"), not just a status flag the model sets on its own
say-so.

Tasks (design these yourself — the signatures below are a starting
point, not a contract you have to match):
  1. add_todos(...)  — add one or more todos to the list
  2. get_todos(...)  — return the current list, however you choose to
     filter or shape it
  3. mark_todo(...)  — update a todo's status
  4. Once you've settled on a shape, write the TOOLS schema yourself
     and wire it into the agent loop's stop condition (Lesson 2) — the
     loop shouldn't consider itself done while a todo is incomplete.

Questions to resolve before you write code — there's no single right
answer, but you should be able to defend whatever you pick:
  - What does "status" need to express? pending/in_progress/completed
    is Lesson 2's minimum — is that enough once verification enters
    the picture, or do you need something like "blocked" too?
  - Should mark_todo require evidence (e.g. a command's exit code)
    before it'll accept "completed," and refuse otherwise? Lesson 2's
    "Completed Should Mean Verified, Not Just Claimed" argues yes —
    decide how strict to make that in code.
  - Where does the list live, and what survives a resumed session
    (Week 3)? A module-level list won't survive a process restart;
    is that good enough for this build, or do you need it on disk?
  - Should add_todos take one todo or a whole plan at once? (Lesson 2's
    todo_write always sends the full current list back — you don't
    have to copy that design, but know why it might matter.)

Run directly once you've implemented something real: add a couple of
todos, mark one in_progress, try to mark it completed without evidence
and see whether your own rules let that happen, then get_todos() and
confirm the list reflects what you'd expect.
"""
import json
import os
from typing import List, Dict, Any, Optional

# TODO: pick your own storage. A plain list/dict at module scope is fine
# to start; revisit once you decide whether todos need to survive a
# resumed session.

# implement the following: add_todos, get_todos, mark_todo

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if "builds" in BASE_DIR:
    PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, "..", "project"))
else:
    PROJECT_DIR = os.path.abspath(os.path.join(BASE_DIR, ".agent"))
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
    """Adds one or more todos to the list."""
    current_todos = _load_todos()
    
    # Calculate next starting ID
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
    """Returns the current list of todos, optionally filtered by status."""
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

# TODO: once the functions above have a settled shape, write the TOOLS
# schema for add_todos / get_todos / mark_todo yourself. Lesson 6 has
# the guidance on what makes a tool description the model actually
# follows — apply it here instead of copying Lesson 2's example verbatim.
TOOLS = [
    {
        "name": "add_todos",
        "description": "Adds one or more structured items to your plan/todo list. Use this whenever you break down a user's large goal into discrete, verifiable engineering tasks.",
        "parameters": {
            "type": "object",
            "properties": {
                "todos": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string", "description": "Short action-oriented title"},
                            "description": {"type": "string", "description": "Detailed explanation of what needs to be accomplished"},
                            "verification_method": {"type": "string", "description": "The exact shell command or script to run to prove this task succeeded (e.g., 'pytest tests/test_auth.py')"}
                        },
                        "required": ["title", "description", "verification_method"]
                    }
                }
            },
            "required": ["todos"]
        }
    },
    {
        "name": "get_todos",
        "description": "Retrieves the current active todo items. Use this at the start of your loop or context window to determine your next action item.",
        "parameters": {
            "type": "object",
            "properties": {
                "status_filter": {
                    "type": "string", 
                    "enum": ["pending", "in_progress", "completed", "blocked"],
                    "description": "Optional status to filter results by."
                }
            }
        }
    },
    {
        "name": "mark_todo",
        "description": "Updates a task's progress state. IMPORTANT: You are forbidden from setting status to 'completed' unless you supply an 'evidence' dictionary containing an 'exit_code' of 0 from your verification step.",
        "parameters": {
            "type": "object",
            "properties": {
                "todo_id": {"type": "integer", "description": "The numeric ID of the todo item."},
                "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
                "evidence": {
                    "type": "object",
                    "properties": {
                        "command_run": {"type": "string", "description": "The command you ran to verify success."},
                        "exit_code": {"type": "integer", "description": "The actual exit code of the execution. Must be 0 to complete a task."},
                        "output": {"type": "string", "description": "Truncated stdout/stderr snippet showing success."}
                    },
                    "required": ["exit_code"]
                }
            },
            "required": ["todo_id", "status"]
        }
    }
]

if __name__ == "__main__":
    # TODO: exercise add_todos / get_todos / mark_todo once they're real,
    # including the case where you try to mark something completed
    # without evidence — does your code stop you, or let it through?
    if os.path.exists(TODO_FILE):
        os.remove(TODO_FILE)
    print(f"Target Database Location: {TODO_FILE}")
    add_res = add_todos([
        {
            "title": "Implement User Authentication Router",
            "description": "Build the POST /login endpoint matching the spec.",
            "verification_method": "pytest tests/test_auth.py"
        }
    ])
    print(add_res)

    progress_res = mark_todo(todo_id=1, status="in_progress")
    print(progress_res)

    fail_res_1 = mark_todo(todo_id=1, status="completed")
    print("Result:", fail_res_1)

    fail_res_2 = mark_todo(
        todo_id=1, 
        status="completed", 
        evidence={"command_run": "pytest tests/test_auth.py", "exit_code": 1, "output": "1 failed"}
    )
    print("Result:", fail_res_2)

    success_res = mark_todo(
        todo_id=1, 
        status="completed", 
        evidence={"command_run": "pytest tests/test_auth.py", "exit_code": 0, "output": "All tests passed"}
    )
    print("Result:", success_res)

    print(json.dumps(get_todos(), indent=2))