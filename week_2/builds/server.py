from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent
import requests
import asyncio

app = Server("web-tools")

@app.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="web_fetch",
            description="Fetch the text content of a URL.",
            inputSchema={
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The URL to fetch"},
                },
                "required": ["url"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "web_fetch":
        url = arguments["url"]
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return [TextContent(type="text", text=response.text[:4000])]

    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as streams:
        await app.run(*streams, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())