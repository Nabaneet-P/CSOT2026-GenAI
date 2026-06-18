"""
Paper search and read tools — Hugging Face Papers API (arXiv index).

Implement:
  - paper_search(query, limit) -> {papers: [{arxiv_id, title, abstract, url}, ...]}
  - read_paper(arxiv_id) -> {title, abstract, content, url, ...}

API docs: week_3/3_paper_tools.md
"""

import requests

BASE_URL = "https://huggingface.co"

def paper_search(query: str, limit: int = 5) -> list[dict]:
    url = f"{BASE_URL}/api/papers/search"
    response = requests.post(
        url=url,
        json={"q": query, "num": limit}
    )
    response.raise_for_status()
    data = response.json()
    results = []
    for item in data:
        arxiv_id = item.get("id", "")
        results.append({
            "arxiv_id": arxiv_id,
            "title": item.get("title", ""),
            "abstract": item.get("summary", ""),
            "url": f"{BASE_URL}/papers/{arxiv_id}",
        })
    return results

def read_paper(arxiv_id: str) -> dict:
    url = f"{BASE_URL}/api/papers/{arxiv_id}"
    response = requests.get(url)
    response.raise_for_status()
    data = response.json()
    
    md_url = f"{BASE_URL}/papers/{arxiv_id}.md"
    md_response = requests.get(md_url)
    
    content = md_response.text if md_response.status_code == 200 else "Content unavailable."

    return {
        "arxiv_id": arxiv_id,
        "title": data.get("title", ""),
        "abstract": data.get("summary", ""),
        "content": content,
        "url": f"{BASE_URL}/papers/{arxiv_id}",
        "upvotes": data.get("upvotes", 0),
        "published_at": data.get("publishedAt", "")
    }