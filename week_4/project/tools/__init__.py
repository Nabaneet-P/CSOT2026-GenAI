from .files import read_file, write_file, edit_file, list_files
from .papers import paper_search, read_paper
from .web import web_fetch, web_search

TOOLS = [
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
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Writes fresh content to a file. Automatically creates parent directories if they don't exist.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The target file path relative to workspace root (e.g., 'week_3/notes/topic.md')."
                    },
                    "content": {
                        "type": "string",
                        "description": "The structural text content to write into the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Modifies an existing file by performing operations like replace, insert, or delete on specific lines.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "The target file path relative to workspace root to edit."
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "insert", "delete"],
                        "description": "The mutation type to execute on the file lines."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "The 1-indexed starting line number for the target operation."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "The 1-indexed ending line number (inclusive) for 'replace' or 'delete' operations. If omitted, defaults to start_line."
                    },
                    "content": {
                        "type": "string",
                        "description": "The structural text to insert or substitute. Unused during 'delete' operations."
                    }
                },
                "required": ["path", "operation", "start_line"]
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
            "name": "paper_search",
            "description": "Searches an academic database for research papers matching a specific text query.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The research topic, title, keywords, or query string to search for."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of paper results to return. Defaults to 5.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description": "Retrieves the full structural details, abstract, metadata, and markdown body content of a specific research paper by its arXiv ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {
                        "type": "string",
                        "description": "The unique arXiv ID identifier for the target academic paper."
                    }
                },
                "required": ["arxiv_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Executes a traditional organic web search via Serper API to gather top matching live links and text snippets.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search term or phrase to query on the web."
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "The exact number of top search results to return. Defaults to 5.",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Downloads and cleans the textual contents of a targeted webpage. Evaluates and prioritizes optimized 'llms.txt' formats if available, fallback parsing via html text stripping.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The explicit target URL protocol path to retrieve text contents from."
                    }
                },
                "required": ["url"]
            }
        }
    }
]

TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
    "edit_file": edit_file,
    "list_files": list_files,
    "paper_search": paper_search,
    "read_paper": read_paper,
    "web_search": web_search,
    "web_fetch": web_fetch,
}

MAX_ITERATIONS = 10