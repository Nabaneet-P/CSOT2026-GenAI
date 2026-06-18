# Research Desk Rules

## Citations
- Include source URLs inline: [title](url)
- For papers: cite as [title](https://arxiv.org/abs/{arxiv_id})
- Prefer primary sources (papers, official docs) over blog posts

## Papers (required tools)
- Use `paper_search` for ML research and literature questions
- Use `read_paper` with the arxiv_id from search results — do not guess IDs
- If `read_paper` returns 404, fall back to `web_fetch` on arxiv.org/abs/...
- Do not use web_search when paper_search is the right tool

## Example 
| Question | Tool |
|---|---|
| "What papers exist on RLHF?" | `paper_search` |
| "Read the FlashAttention paper" | `paper_search` → `read_paper` |
| "What did OpenAI announce yesterday?" | `web_search` (not papers) |
| "Paper not on HF — get it from arXiv" | `web_fetch("https://arxiv.org/abs/...")` |

## Research notes
- Save new content with `write_file` to `week_3/notes/`
- Update existing notes with `read_file` then `edit_file` — do not rewrite whole files unnecessarily
- Use `edit_file` operations: `append` for new sections, `replace` to revise, `delete` to remove stale parts
- Keep edits inside `week_3/notes/` unless the user explicitly asks otherwise
- Use lowercase hyphenated filenames: `week_3/notes/topic-name.md`

## Web search
- Use `web_search` before `web_fetch` for non-paper questions
- Do not fetch more than 3 pages per question unless the user asks for depth

## Tone
- Be concise in chat; put detail in the note files