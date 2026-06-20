"""
Paper search and read tools — Hugging Face Papers API (arXiv index).

Implement:
  - paper_search(query, limit) -> {papers: [{arxiv_id, title, abstract, url}, ...]}
  - read_paper(arxiv_id) -> {title, abstract, content, url, ...}

API docs: week_3/3_paper_tools.md
"""

import requests
from typing import List, Dict

BASE_URL = "https://huggingface.co"

def paper_search(query: str, limit: int = 5) -> List[Dict]:
    url = f"{BASE_URL}/api/papers/search"
    try:
        response = requests.get(
            url=url,
            params={"q": query, "limit": limit},
            timeout=10
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
    except requests.exceptions.HTTPError as e:
        return [{"error": f"Hugging Face paper search failed (HTTP Error): {e}"}]
    except Exception as e:
        return [{"error": f"Hugging Face paper search failed: {str(e)}"}]

def read_paper(arxiv_id: str) -> Dict:
    url = f"{BASE_URL}/api/papers/{arxiv_id}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        md_url = f"{BASE_URL}/papers/{arxiv_id}.md"
        try:
            md_response = requests.get(md_url, timeout=5)
            content = md_response.text if md_response.status_code == 200 else "Content unavailable."
        except Exception:
            content = "Content unavailable due to a network error."
        return {
            "arxiv_id": arxiv_id,
            "title": data.get("title", ""),
            "abstract": data.get("summary", ""),
            "content": content,
            "url": f"{BASE_URL}/papers/{arxiv_id}",
            "upvotes": data.get("upvotes", 0),
            "published_at": data.get("publishedAt", "")
        }
    except requests.exceptions.HTTPError as e:
        return {"error": f"Failed to retrieve paper {arxiv_id} (HTTP Error): {e}"}
    except Exception as e:
        return {"error": f"Failed to retrieve paper {arxiv_id}: {str(e)}"}