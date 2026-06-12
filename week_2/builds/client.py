import os
import sys
import json
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "openrouter/free"
MAX_ITERATIONS = 8 

current_dir = Path(__file__).parent
server_path = current_dir / "server.py"
server_params = StdioServerParameters(
    command=sys.executable,
    args=[str(server_path)]
)

async def main():
    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as mcp_session:
            await mcp_session.initialize()
            mcp_tools = await mcp_session.list_tools()

            tools = []
            for tool in mcp_tools.tools:
                tools.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description, 
                        "parameters": tool.inputSchema
                    }
                })
            print("Chat started. Type 'exit' or 'quit' to quit.\n")
            messages = [{"role": "system", "content": "You are a helpful assistant with access to web tools."}]

            while True:
                user_input = input("You: ").strip()
                if user_input.lower() in ["exit", "quit"]:
                    break
                messages.append({"role": "user", "content": user_input})
                for _ in range(MAX_ITERATIONS):
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=tools,
                    ) 
                    message = response.choices[0].message
                    finish_reason = response.choices[0].finish_reason
                    messages.append(message)

                    if finish_reason == "tool_calls":
                        for tool_call in message.tool_calls:
                            tool = tool_call.function.name
                            args = json.loads(tool_call.function.arguments)
                            print(f"\n[Using MCP Tool: {tool} with args {args}]")

                            result = await mcp_session.call_tool(tool, args)
                            tool_output = "".join([content.text for content in result.content])
                            messages.append({
                                "role": "tool",
                                "tool_call_id": tool_call.id,
                                "name": tool,
                                "content": tool_output
                            })
                    elif finish_reason == "stop":
                        print(f"\n{message.content}\n")
                        break

if __name__ == "__main__":
    asyncio.run(main())                       