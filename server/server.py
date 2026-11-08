"""MCP server: find existing GitHub codebases, extract their architecture, and
scaffold a new project shaped like the best one.

    python server.py            # stdio (Claude Code / Claude Desktop)
    python server.py --http     # streamable HTTP at :8000/mcp (ChatGPT connectors)
"""
import os
import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent))
from architecture import _slug as slug, make_blueprint, scaffold, snapshot  # noqa: E402
from cache import Cache  # noqa: E402
from github import search_repos  # noqa: E402
from scoring import rank  # noqa: E402

mcp = FastMCP("reuse-first")
cache = Cache(os.getenv("REUSE_FIRST_CACHE", str(Path.home() / ".reuse-first-cache.db")))

FIELDS = ("full_name", "url", "description", "stars", "pushed_at", "license",
          "license_note", "score", "confidence", "excluded", "language")


async def find(query: str, limit: int = 10, allow_copyleft: bool = False) -> list[dict]:
    repos = await search_repos(query, cache, max(limit * 2, 10))
    ranked = rank(repos, query, allow_copyleft=allow_copyleft)[:limit]
    return [{k: r[k] for k in FIELDS} for r in ranked]


async def get_blueprint(full_name: str) -> dict:
    return make_blueprint(await snapshot(full_name, cache))


@mcp.tool()
async def find_repos(query: str, limit: int = 10, allow_copyleft: bool = False) -> list[dict]:
    """Search GitHub for existing projects matching a description and rank them by
    health, adoption and fit. Repos with no/unsuitable license or archived are marked
    in `excluded` and listed last. `score` is 0..1; `confidence` is how much data backed it."""
    return await find(query, limit, allow_copyleft)


@mcp.tool()
async def blueprint(full_name: str) -> dict:
    """Extract a reusable architecture blueprint from a repo ('owner/repo'): stack,
    layers (api/domain/services/data/ui/cli/tests/infra), entrypoints, key dependencies,
    a build plan, and a README excerpt. Use it to design the user's project."""
    return await get_blueprint(full_name)


@mcp.tool()
async def scaffold_project(full_name: str, project_name: str, idea: str,
                           output_dir: str = ".") -> dict:
    """Create a starter project in `output_dir` shaped like `full_name`'s architecture:
    layer folders, a dependency manifest, ARCHITECTURE.md with the build plan, and
    ATTRIBUTIONS.md. Copies no source code. Then implement features layer by layer."""
    bp = await get_blueprint(full_name)
    out = Path(output_dir).expanduser().resolve()
    files = scaffold(bp, project_name, idea, out)
    return {"root": str(out / slug(project_name)), "files": files,
            "build_plan": bp["build_plan"]}


if __name__ == "__main__":
    if "--http" in sys.argv:
        mcp.settings.host, mcp.settings.port = "0.0.0.0", int(os.getenv("PORT", "8000"))
        mcp.run(transport="streamable-http")
    else:
        mcp.run()
