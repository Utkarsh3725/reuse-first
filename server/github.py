"""GitHub repository search with caching and ETag revalidation."""
import os

import httpx

from cache import Cache

API = "https://api.github.com"


def _headers(etag: str | None = None) -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}
    if token := os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {token}"
    if etag:
        h["If-None-Match"] = etag
    return h


def normalize(item: dict) -> dict:
    """Keep only the fields the scorer needs; missing values stay None (= unknown)."""
    lic = item.get("license") or {}
    return {
        "full_name": item["full_name"],
        "url": item["html_url"],
        "description": item.get("description"),
        "stars": item.get("stargazers_count"),
        "forks": item.get("forks_count"),
        "open_issues": item.get("open_issues_count"),
        "pushed_at": item.get("pushed_at"),
        "archived": item.get("archived", False),
        "license": lic.get("spdx_id"),  # None or "NOASSERTION" => unknown
        "topics": item.get("topics", []),
        "language": item.get("language"),
    }


async def search_repos(query: str, cache: Cache, limit: int = 20,
                       client: httpx.AsyncClient | None = None) -> list[dict]:
    key = f"search:{query}:{limit}"
    cached, _ = cache.get(key)
    if cached is not None:
        return cached
    _, etag = cache.get(key, allow_stale=True)

    own = client is None
    client = client or httpx.AsyncClient(timeout=20)
    try:
        r = await client.get(
            f"{API}/search/repositories",
            params={"q": query, "sort": "stars", "order": "desc", "per_page": limit},
            headers=_headers(etag),
        )
        if r.status_code == 304:  # unchanged: refresh timestamp, reuse stale body
            stale, _ = cache.get(key, allow_stale=True)
            cache.put(key, stale, etag)
            return stale
        r.raise_for_status()
        repos = [normalize(i) for i in r.json().get("items", [])]
        cache.put(key, repos, r.headers.get("etag"))
        return repos
    finally:
        if own:
            await client.aclose()
