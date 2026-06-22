"""
Build 1: Command Execution
============================
A sandboxed run_command tool: search, inspect history, run tests — and,
once a human approves, make real changes to the repo.

Tasks:
  1. paths_within_sandbox(command, workspace_root) -> bool
  2. classify_command(command) -> "read_only" | "ask"
  3. run_command(command, cwd=WORKSPACE_ROOT, timeout=10) -> dict
  4. Wire run_command into the OpenAI tool schema (TOOLS)

Run directly: a read-only command should run immediately; a destructive
one should print a warning and wait for y/n before doing anything.
"""

import os
import shlex
import subprocess
from pathlib import Path

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
TIMEOUT_DEFAULT = 10
MAX_OUTPUT_CHARS = 8_000

# Known-safe: run immediately once the path check passes.
READ_ONLY_PREFIXES = (
    "grep", "find", "ls", "cat", "head", "tail", "wc",
    "git log", "git diff", "git status", "git blame", "git show",
    "pytest", "python -m pytest", "ruff", "flake8", "mypy",
)

# Known-destructive: always ask, even if they'd otherwise look harmless.
DESTRUCTIVE_PATTERNS = (
    "rm ", "mv ", ">", ">>", "git commit", "git push", "git checkout --",
    "pip install", "npm install", "curl ", "sudo ", "chmod ",
)


def paths_within_sandbox(command: str, workspace_root: str) -> bool:
    """
    Token-level check: no path-looking argument in `command` may resolve
    outside `workspace_root`.

    This is a heuristic, not a guarantee — see Lesson 1's caveat about
    pipes and command substitution. Still worth doing.
    """
    root_path = Path(workspace_root).resolve()
    try:
        tokens = shlex.split(command)
    except ValueError:
        return False
    for token in tokens:
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
    """
    Return "read_only" if `command` matches a known-safe prefix and no
    destructive pattern, otherwise "ask".

    Default to "ask" for anything unclassified — see Lesson 1.
    """
    clean_command = command.strip()
    for pattern in DESTRUCTIVE_PATTERNS:
        if pattern in clean_command:
            return "ask"
    for prefix in READ_ONLY_PREFIXES:
        if clean_command == prefix or clean_command.startswith(prefix + " "):
            return "read_only"
    return "ask"


def run_command(command: str, cwd: str = WORKSPACE_ROOT, timeout: int = TIMEOUT_DEFAULT) -> dict:
    """
    Run a shell command, sandboxed to `cwd`.

    Behavior:
      - reject immediately if paths_within_sandbox() fails
      - if classify_command() == "read_only": execute right away
      - otherwise: print the command + a clear warning, input() for y/n,
        and block (return {"error": ...}) if the human declines
      - always: capture stdout/stderr/exit_code, truncate long output,
        and enforce `timeout`
    """
    if not paths_within_sandbox(command, cwd):
        return {"error": "blocked: command references a path outside the workspace"}
    classification = classify_command(command)
    if classification != "read_only":
        try:
            print("WARNING: the agent wants to run a command that may write, delete, or install:")
            print("    " + command)
            approved = input("Allow this command? [y/N]: ").strip().lower() == "y"
        except (KeyboardInterrupt, EOFError):
            approved = False  
        if not approved:
            return {"error": "blocked: user did not approve this command"}
        
    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True
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

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": (
                "Run a shell command in the workspace and return its output. "
                "Use this to search (grep/find), inspect history (git log/diff), "
                "run tests, or make a change. Read-only commands run immediately. "
                "Anything that writes, deletes, or installs will pause and ask the "
                "human operator for approval — expect that pause, it's not a failure."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The shell command to run.",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": f"Seconds before the command is killed. Default {TIMEOUT_DEFAULT}.",
                    },
                },
                "required": ["command"],
            },
        },
    }
]


if __name__ == "__main__":
    print("Read-only command (should run immediately):")
    print(run_command("git log --oneline -5"))

    print("\nDestructive command (should pause and ask for approval):")
    print(run_command("rm -rf ./does-not-exist-example"))
