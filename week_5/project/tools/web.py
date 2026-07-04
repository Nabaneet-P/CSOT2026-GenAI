import os
import requests
import trafilatura
from urllib.parse import urlparse
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.environ["SERPER_API_KEY"]
MAX_CHARS = 8000

BROWSER_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5"
}

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

def web_fetch(url: str) -> str:
    base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
    try:
        resp = requests.get(f"{base}/llms.txt", timeout=5)
        if resp.status_code == 200:
            return f"[llms.txt found]\n\n{resp.text}\n\n---\nOriginal URL: {url}"
    except Exception:
        pass
    
    try:
        response = requests.get(url, headers=BROWSER_HEADERS, allow_redirects=True, timeout=10)
        response.raise_for_status()
        html = response.text
        content = trafilatura.extract(html, include_comments=False, include_tables=True)
        if not content:
            return "Error: Could not extract readable main text content from this page."
        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS] + "\n\n[...truncated]"
        return content
    except Exception as e:
        return f"Error fetching data: {str(e)}"