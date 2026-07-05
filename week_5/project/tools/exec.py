import os
import shlex
import subprocess
from pathlib import Path
from .exceptions import ToolApprovalRequired

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TIMEOUT_DEFAULT = 10
MAX_OUTPUT_CHARS = 8_000

READ_ONLY_PREFIXES = (
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git log", "git diff", "git status", "git blame", "git show",
    "pytest", "python -m pytest", "ruff", "flake8", "mypy",
)

DESTRUCTIVE_PATTERNS = (
    "rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --",
    "pip install", "npm install", "curl ", "sudo ", "chmod ",
)


def paths_within_sandbox(command: str, workspace_root: str) -> bool:
    root_path = Path(workspace_root).resolve()
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    for token in tokens:
        if token.startswith("$") or token.startswith("-"):
            continue
        if '/' in token or '\\' in token or '.' in token:
            try:
                token_path = Path(token)
                if not token_path.is_absolute():
                    token_path = root_path / token_path
                resolved_token_path = token_path.resolve()
                common = os.path.commonpath([str(root_path), str(resolved_token_path)])
                if common != str(root_path):
                    return False
            except (ValueError, RuntimeError):
                return False
    return True

def classify_command(command: str) -> str:
    clean_command = command.strip()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in clean_command:
            return "ask"
    for prefix in READ_ONLY_PREFIXES:
        if clean_command == prefix or clean_command.startswith(prefix + " "):
            return "read_only"
    return "ask"

def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:
    if not paths_within_sandbox(command, cwd):
        return {"error": "blocked: command references a path outside the workspace"}
    clean_cmd = command.strip().lower()
    if ".env" in clean_cmd:
        return {"error": "blocked: shell access to configuration environment targets is prohibited"}
    classification = classify_command(command)
    if classification != "read_only":
        raise ToolApprovalRequired(
            tool_name="run_command",
            target=command, 
            callback=lambda: _execute_shell_subprocess(command, cwd, timeout),
            args=(),
            kwargs={}
        )
    return _execute_shell_subprocess(command, cwd, timeout)

def _execute_shell_subprocess(command: str, cwd: str, timeout: int) -> dict:
    try:
        current_env = os.environ.copy()
        current_env.pop("GITHUB_PAT", None)
        current_env.pop("OPENROUTER_API_KEY", None)
        current_env.pop("SERPER_API_KEY", None)
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            env=current_env 
        )
        stdout = result.stdout or ""
        stderr = result.stderr or ""
        was_truncated = len(stdout) > MAX_OUTPUT_CHARS or len(stderr) > MAX_OUTPUT_CHARS
        if len(stdout) > MAX_OUTPUT_CHARS:
            stdout = stdout[:MAX_OUTPUT_CHARS] 
        if len(stderr) > MAX_OUTPUT_CHARS:
            stderr = stderr[:MAX_OUTPUT_CHARS]
        return {
            "stdout": stdout,
            "stderr": stderr,
            "exit_code": result.returncode,
            "truncated": was_truncated,
        }
    except subprocess.TimeoutExpired as e:
        stdout = e.stdout if isinstance(e.stdout, str) else (e.stdout or b"").decode(errors='replace')
        stderr = e.stderr if isinstance(e.stderr, str) else (e.stderr or b"").decode(errors='replace')
        was_truncated = len(stdout) > MAX_OUTPUT_CHARS or len(stderr) > MAX_OUTPUT_CHARS
        return {
            "error": f"command timed out after {timeout} seconds",
            "stdout": stdout[:MAX_OUTPUT_CHARS],
            "stderr": stderr[:MAX_OUTPUT_CHARS],
            "exit_code": -1,
            "truncated": was_truncated,
        }
    except Exception as e:
        return {"error": f"execution failed: {str(e)}"}