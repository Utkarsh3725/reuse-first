"""GitHub repository search with caching and ETag revalidation. Standard library only."""
import json
import os
import urllib.error
import urllib.parse
import urllib.request

from cache import Cache

API = "https://api.github.com"
_open = urllib.request.urlopen  # tests replace this


class GitHubError(Exception):
    """str() is a one-line message meant for the person running the tool."""
    def __init__(self, status: int, url: str):
        if status in (403, 429):
            hint = ("wait a minute and try again" if os.getenv("GITHUB_TOKEN") else
                    "set GITHUB_TOKEN to a GitHub token (no scopes needed) and try again")
            msg = f"GitHub rate limit reached (HTTP {status}): {hint}."
        elif status == 401:
            msg = "GitHub rejected GITHUB_TOKEN (HTTP 401): it is wrong or expired. Fix or unset it."
        else:
            msg = f"GitHub returned HTTP {status} for {url}."
        super().__init__(msg)
        self.status = status


def _headers(etag: str | None = None) -> dict:
    h = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
         "User-Agent": "reuse-first"}
    if token := os.getenv("GITHUB_TOKEN"):
        h["Authorization"] = f"Bearer {token}"
    if etag:
        h["If-None-Match"] = etag
    return h


def get(path: str, params: dict | None = None, etag: str | None = None,
        timeout: float = 20) -> tuple[int, dict | list | None, str | None]:
    """GET an API path. Returns (status, json body or None, etag); never raises on HTTP status."""
    url = f"{API}{path}" + (f"?{urllib.parse.urlencode(params)}" if params else "")
    req = urllib.request.Request(url, headers=_headers(etag))
    try:
        with _open(req, timeout=timeout) as r:
            return r.status, json.loads(r.read()), r.headers.get("ETag")
    except urllib.error.HTTPError as e:  # urllib raises for 304 and every 4xx/5xx
        return e.code, None, e.headers.get("ETag") if e.headers else None


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


def search_repos(query: str, cache: Cache, limit: int = 20) -> list[dict]:
    key = f"search:{query}:{limit}"
    cached, _ = cache.get(key)
    if cached is not None:
        return cached
    stale, etag = cache.get(key, allow_stale=True)

    status, body, new_etag = get("/search/repositories", {
        "q": query, "sort": "stars", "order": "desc", "per_page": limit}, etag)
    if status == 304 and stale is not None:  # unchanged: refresh timestamp, reuse stale body
        cache.put(key, stale, etag)
        return stale
    if status != 200:
        raise GitHubError(status, "/search/repositories")
    repos = [normalize(i) for i in body.get("items", [])]
    cache.put(key, repos, new_etag)
    return repos
