import os
from openai import OpenAI
import json
import requests
import trafilatura
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "openrouter/free"

SERPER_API_KEY = os.environ["SERPER_API_KEY"]

search_tool = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": (
            "Search the web for current information. Use this when the user asks "
            "about recent events, specific facts, or anything you are uncertain about. "
            "Returns a list of search results with titles, URLs, and snippets."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query. Be specific and targeted.",
                }
            },
            "required": ["query"],
        },
    },
}

fetch_tool = {
    "type": "function",
    "function": {
        "name": "web_fetch",
        "description": (
            "Fetch and read the full content of a web page. Use this after web_search "
            "to read a specific result in detail. Prefer this for documentation, articles, "
            "and pages where the snippet is not enough."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The full URL to fetch, including https://",
                }
            },
            "required": ["url"],
        },
    },
}

TOOLS = [search_tool, fetch_tool]

def web_fetch(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
    response.raise_for_status()
    return response.text   

def fetch_clean(url: str) -> str:
    html = web_fetch(url)
    text = trafilatura.extract(html, include_comments=False, include_tables=True)
    return text or ""

MAX_CHARS = 8000
def fetch_for_agent(url: str) -> str:
    content = fetch_clean(url)
    if len(content) > MAX_CHARS:
        content = content[:MAX_CHARS] + "\n\n[...truncated]"
    return content

def smart_fetch(url: str) -> str:
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    try:
        resp = requests.get(f"{base}/llms.txt", timeout=5)
        if resp.status_code == 200:
            return f"[llms.txt found]\n\n{resp.text}\n\n---\nOriginal URL: {url}"
    except Exception:
        pass
    return fetch_for_agent(url)

def web_search(query: str, num_results: int = 5) -> list[dict]:
    response = requests.post(
        "https://google.serper.dev/search",
        headers={"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"},
        json={"q": query, "num": num_results},
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    results = []
    for item in data.get("organic", []):
        results.append({
            "title": item.get("title", ""),
            "link": item.get("link", ""),
            "snippet": item.get("snippet", ""),
        })
    return results

TOOL_REGISTRY = {"web_fetch": smart_fetch, "web_search": web_search}

def dispatch(tool_call) -> str:
    func_name = tool_call.function.name
    if func_name not in TOOL_REGISTRY:
        return json.dumps({"error": "Invalid tool name"})
    
    tool = TOOL_REGISTRY[func_name]
    args = json.loads(tool_call.function.arguments)
    result = tool(**args)
    return json.dumps(result)

MAX_ITERATIONS = 8

messages = [{"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."}]

def call_model(prompt: str) -> str:
    messages.append({"role": "user", "content": prompt})
    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason
        messages.append(message)

        if finish_reason == "stop":
            return message.content
        if finish_reason == "tool_calls":
            for tool_call in message.tool_calls:
                function_name = tool_call.function.name
                function_args = json.loads(tool_call.function.arguments)

                result = dispatch(tool_call)
                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
                print(f"Iteration {_}, Calling {function_name}, args {function_args}")

    return f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]"

def run_chatbot():
    global messages
    print("Chat started. Type 'exit' or 'quit' to quit.\n")

    while True:
        user_input = input("User: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            print("\nThank you for using the chatbot!")
            break
        if user_input == "/reset":
            messages = [messages[0]]
            print("\nChat history reset\n")
            continue
        result = call_model(user_input)
        print(result)

if __name__ == "__main__":
    run_chatbot()