from .files import read_file, write_file, edit_file, list_files
from .exec import run_command
from .plan import add_todos, get_todos, mark_todo
from .search import list_definitions  

def approved_file_tool_wrapper(tool_func, name: str):
    def wrapped(*args, **kwargs):
        target_path = kwargs.get('path') or (args[0] if len(args) > 0 else 'unknown')
        print(f"\nWARNING: The agent wants to execute a mutating file operation [{name}]:")
        print(f"    Target Path: {target_path}")
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
    "read_file": read_file,
    "list_files": list_files,
    "write_file": approved_file_tool_wrapper(write_file, "write_file"),
    "edit_file": approved_file_tool_wrapper(edit_file, "edit_file"),
    "list_definitions": list_definitions, 
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
    },
    {
        "type": "function",
        "function": {
            "name": "list_definitions",
            "description": "Parse a Python file with ast and return every function/class it declares, in source order, with line numbers — a structural outline without reading the file's full body.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "The relative file path to analyze (e.g., 'src/auth.py')"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Recursively searches and lists tracked files matching a specific pattern inside a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative directory path to search from. Defaults to current directory '.'",
                        "default": "."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "A glob pattern used to filter file matches (e.g., '*.py'). Defaults to '*'.",
                        "default": "*"
                    }
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Reads specific lines of content from a file within the workspace safely.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The relative path to the file within the workspace."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The starting line number to read (1-indexed). Defaults to 1.",
                        "default": 1
                    },
                    "read_lines": {
                        "type": "integer",
                        "description": "The number of lines to read from the start line. Defaults to 200.",
                        "default": 200
                    }
                },
                "required": ["path"]
            }
        }
    }
]