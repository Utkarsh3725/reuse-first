import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "server"))
from cache import Cache  # noqa: E402
from github import search_repos  # noqa: E402
from scoring import rank, score_repo  # noqa: E402

NOW = datetime(2026, 11, 9, tzinfo=timezone.utc)


def repo(**kw):
    base = dict(full_name="a/b", url="u", description="pdf table extraction", stars=1000,
                forks=1, open_issues=10, pushed_at="2026-10-01T00:00:00Z", archived=False,
                license="MIT", topics=["pdf"], language="Python")
    return {**base, **kw}


def test_missing_data_is_unknown_not_zero():
    r = score_repo(repo(stars=None, pushed_at=None, open_issues=None), "pdf table", NOW)
    assert r["signals"]["recency"] is None and r["signals"]["adoption"] is None
    assert r["confidence"] < 0.5          # low confidence...
    assert r["score"] == 1.0              # ...but not punished with zeros


def test_license_gate_excludes_unlicensed_and_archived():
    assert score_repo(repo(license=None), "pdf", NOW)["excluded"]
    assert score_repo(repo(license="GPL-3.0"), "pdf", NOW)["excluded"]
    assert not score_repo(repo(license="GPL-3.0"), "pdf", NOW, allow_copyleft=True)["excluded"]
    assert "archived" in score_repo(repo(archived=True), "pdf", NOW)["excluded"]


def test_excluded_repos_rank_last():
    good = repo(full_name="good/x", stars=50)
    bad = repo(full_name="bad/x", stars=100000, license=None)
    assert [r["full_name"] for r in rank([bad, good], "pdf table")] == ["good/x", "bad/x"]


def test_search_is_cached(tmp_path):
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        return httpx.Response(200, json={"items": [{
            "full_name": "a/b", "html_url": "u", "stargazers_count": 5}]},
            headers={"etag": "abc"})

    async def run():
        cache = Cache(str(tmp_path / "c.db"))
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
            return await search_repos("pdf", cache, client=c), await search_repos("pdf", cache, client=c)

    first, second = asyncio.run(run())
    assert first == second and calls == 1
    assert first[0]["license"] is None  # unknown stays None
