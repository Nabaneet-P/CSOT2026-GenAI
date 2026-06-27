from .files import write_file, edit_file
from .exec import run_command
from .plan import add_todos, get_todos, mark_todo

def approved_file_tool_wrapper(tool_func, name: str):
    def wrapped(*args, **kwargs):
        print(f"\nWARNING: The agent wants to execute a mutating file operation [{name}]:")
        print(f"    Target Path: {kwargs.get('path', 'unknown')}")
        try:
            approved = input("Allow this file change? [y/N]: ").strip().lower() == "y"
        except (KeyboardInterrupt, EOFError):
            approved = False
        
        if not approved:
            return {"success": False, "error": "blocked: user did not approve this file modification command"}
        return tool_func(*args, **kwargs)
    return wrapped

TOOL_REGISTRY = {
    "add_todos": add_todos,
    "get_todos": get_todos,
    "mark_todo": mark_todo,
    "run_command": run_command, 
    "write_file": approved_file_tool_wrapper(write_file, "write_file"),
    "edit_file": approved_file_tool_wrapper(edit_file, "edit_file"),
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "add_todos",
            "description": "Adds structured items to your plan list. Use this to break down large engineering changes into clear steps.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todos": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string", "description": "Short description of target change step"},
                                "description": {"type": "string", "description": "Detailed explanation of what needs to be accomplished"},
                                "verification_method": {"type": "string", "description": "The command or script to run to prove this step succeeded (e.g., 'pytest tests/test_core.py')"}
                            },
                            "required": ["title", "description", "verification_method"]
                        }
                    }
                },
                "required": ["todos"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_todos",
            "description": "Retrieves the current workflow task list items.",
            "parameters": {
                "type": "object",
                "properties": {
                    "status_filter": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "mark_todo",
            "description": "Updates progress state. To mark a todo as 'completed', you MUST supply evidence containing an exit_code of 0.",
            "parameters": {
                "type": "object",
                "properties": {
                    "todo_id": {"type": "integer"},
                    "status": {"type": "string", "enum": ["pending", "in_progress", "completed", "blocked"]},
                    "evidence": {
                        "type": "object",
                        "properties": {
                            "command_run": {"type": "string"},
                            "exit_code": {"type": "integer", "description": "Must be 0 to complete a task successfully."},
                            "output": {"type": "string"}
                        },
                        "required": ["exit_code"]
                    }
                },
                "required": ["todo_id", "status"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "Runs a shell command inside the workspace. Read-only commands run immediately; anything else triggers human approval.",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "The shell command to execute."},
                    "timeout": {"type": "integer", "description": "Execution timeout limit."}
                },
                "required": ["command"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes fresh text contents directly to a specific path file layout inside the sandbox workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Applies targeted chunk modifications ('replace', 'insert', or 'delete') within specific line bounds on an existing file asset.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "insert", "delete"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"}
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    }
]