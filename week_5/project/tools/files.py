import os
import json
import fnmatch
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_READ_CHARS = 12_000
SESSIONS_DIR = Path("week_3/.agent/sessions")
AGENTS_PATHS = (Path("AGENTS.md"), Path("week_3/.agent/AGENTS.md"))

BASE_PROMPT = "You are Research Desk, a helpful research assistant."

def resolve_path(path: str) -> str:
    base = Path(WORKSPACE_ROOT).resolve()
    full = Path(base, path).resolve()
    if not full.is_relative_to(base):
        raise ValueError(f"Path escapes workspace: {path}")
    normalized_path = full.name.lower()
    if normalized_path.startswith(".env") or ".env" in full.parts:
        raise PermissionError("Access Denied: High-privilege environment files are strictly isolated.")
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