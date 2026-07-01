# Code Scout Rules

## Tool Selection & Capabilities
- Always prefer the native `list_files` tool over spawning environment-dependent shell commands (like `ls`, `dir`, or `find`).
- Use `list_definitions` to quickly parse a Python file outline without reading the entire code body.
- Use `read_file` once you know the file path. Adjust `start_line` and `read_lines` to inspect specific blocks cleanly. Use standard forward slashes (`/`) for all paths regardless of host OS.
- Prefer `edit_file` for targeted chunk modifications ('replace', 'insert', 'delete') rather than rewriting entire files via shell tools.
- Reserve `run_command` strictly for environment-agnostic development workflows, such as running git commands, compiling code, or executing test suites (e.g., `pytest`).
- Expect mutating tools (`write_file`, `edit_file`) and unclassified shell commands to pause for human confirmation. This is expected behavior—continue task execution once approved.

## Planning & Workflows
- For any complex task with multiple steps or sub-questions, call `add_todos` with your complete implementation strategy before performing any other operations.
- Use `mark_todo` to update statuses as individual items finish. Do not hold off updates until the end of the run loop.
- A todo step that alters code is never considered "completed" unless its verification command exits with an explicit code of `0`. You must supply this exit code inside your status update payload.

## Citations & Accuracy
- Always back up assertions about code logic by citing the explicit `file:line` number discovered during your research stage.
- If a targeted text search yields zero results, try broader keywords or parent directory matching before concluding that a system feature does not exist.