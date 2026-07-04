import ast
import os
from pathlib import Path

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_GREP_RESULTS = 50
EXCLUDE_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build"}

def resolve_path(path: str) -> str | None:
    try:
        base = Path(WORKSPACE_ROOT).resolve()
        full = Path(base, path).resolve()
        if not full.is_relative_to(base):
            return None
        return str(full)
    except Exception:
        return None

def list_definitions(path: str) -> dict:
    resolved = resolve_path(path)
    if not resolved:
        return {"error": f"Path outside the sandbox: {path}"}
    if not os.path.isfile(resolved):
        return {"error": f"File not found: {path}"}
    try:
        with open(resolved, "r", encoding="utf-8", errors="replace") as f:
            source = f.read()
        tree = ast.parse(source, filename=resolved)
    except SyntaxError as e:
        return {"error": f"SyntaxError: {str(e)}"}
    except Exception as e:
        return {"error": str(e)}

    definitions = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kind = "async function" if isinstance(node, ast.AsyncFunctionDef) else "function"
            definitions.append({
                "kind": kind,
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })
        elif isinstance(node, ast.ClassDef):
            definitions.append({
                "kind": "class",
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })
            for sub_node in node.body:
                if isinstance(sub_node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    definitions.append({
                        "kind": "method",
                        "name": sub_node.name,
                        "line": sub_node.lineno,
                        "end_line": getattr(sub_node, "end_lineno", sub_node.lineno)
                    })
    return {"definitions": definitions}