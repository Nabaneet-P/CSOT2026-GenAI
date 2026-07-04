---
name: programming
description: Activate when the user wants to write code, refactor files, debug errors, build features, manage git workflows, or run test suites.
---

## Tool Selection Priorities
- To discover project structures or find files: Use `list_files`. DO NOT use host-specific commands like `dir` or `ls`.
- To inspect file code contents safely: Use `read_file` with explicit line slicing boundaries.
- To map classes/functions within Python assets quickly: Use `list_definitions`.

## Task Tracking & Execution
1. When assigned an engineering task, you MUST break it down into explicit items via `add_todos` before invoking any other tool.
2. Track execution progress iteratively. Update item statuses instantly using `mark_todo` as they are completed.
3. A todo item involving text/code updates is FORBIDDEN from being marked as "completed" unless a relevant test or script has been executed via `run_command` and exits with code 0. You must cite this exit code in your evidence block.