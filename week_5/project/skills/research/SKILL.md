---
name: research
description: Activate when the user wants to investigate a topic, look up ML papers, compile a summary, crawl documentation, search the web, or manage research notes.
---

## Tool Selection & Execution Rules

### 1. Academic & ML Papers
- Use `paper_search` for ML research and literature questions.
- Use `read_paper` with the explicit `arxiv_id` obtained from search results — **do not guess IDs**.
- If `read_paper` returns a 404 error, fall back to executing `web_fetch` directly on `https://arxiv.org/abs/{arxiv_id}`.
- **Priority Guideline**: Do not use general `web_search` when `paper_search` is the correct domain tool.

### 2. General Web Exploration
- Use `web_search` before invoking `web_fetch` for all non-paper questions.
- **Resource Budgeting**: Do not fetch more than 3 pages per question unless the user explicitly requests deep coverage.

### 3. Managing Research Notes
- **Storage Target**: Save all completely new content using `write_file` targeted to the directory path: `week_5/project/.agent/notes/`.
- **Naming Convention**: Use strictly lowercase, hyphenated filenames (e.g., `week_3/notes/topic-name.md`).
- **File Mutation**: Update existing notes by calling `read_file` followed by targeted `edit_file` blocks. **DO NOT rewrite whole files unnecessarily**. Use clean operations: `append` for new sections, `replace` to revise, and `delete` to strip stale content.
- Keep all file interactions bound inside `week_5/project/.agent/notes/` unless explicitly overridden by user instructions.

## Output Formatting & Tone Guidelines
- **Citations**: Maintain rigorous evidence standards. Include source URLs inline using the exact format: `[title](url)`. For academic papers, format strictly as `[title](https://arxiv.org/abs/{arxiv_id})`. Prefer primary sources (official docs, papers) over blog summaries.
- **Tone Strategy**: Be highly concise and brief in direct chat messages; offload heavy details, data points, and tables directly into the note files in your workspace.