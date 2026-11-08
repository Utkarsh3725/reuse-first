"""End-to-end check: launch the MCP server over stdio exactly as Claude does,
then call every tool against live GitHub.

    python tests/e2e_live.py "pdf table extraction"
"""
import asyncio
import json
import sys
import tempfile
from pathlib import Path

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = Path(__file__).resolve().parents[1] / "server" / "server.py"


async def main(query: str):
    params = StdioServerParameters(command=sys.executable, args=[str(SERVER)])
    async with stdio_client(params) as (r, w), ClientSession(r, w) as s:
        await s.initialize()
        tools = [t.name for t in (await s.list_tools()).tools]
        print("tools:", tools)

        res = await s.call_tool("find_repos", {"query": query, "limit": 5})
        assert not res.isError, res.content[0].text
        repos = [json.loads(c.text) for c in res.content]
        if len(repos) == 1 and isinstance(repos[0], list):
            repos = repos[0]
        print(f"\nfind_repos({query!r}):")
        for x in repos:
            print(f"  {x['full_name']:40} *{x['stars']:<7} {str(x['license']):14}"
                  f" score={x['score']} conf={x['confidence']} excluded={x['excluded']}")

        eligible = [x for x in repos if not x["excluded"]] or repos
        top = eligible[0]["full_name"]
        res = await s.call_tool("blueprint", {"full_name": top})
        assert not res.isError, res.content[0].text
        bp = json.loads(res.content[0].text)
        print(f"\nblueprint({top}): stack={bp['stack']} files={bp['total_files']}")
        print("  layers:", json.dumps(bp["layers"], indent=None)[:400])
        print("  key deps:", bp["key_dependencies"][:12])
        assert bp["stack"], "no stack detected"

        with tempfile.TemporaryDirectory() as tmp:
            res = await s.call_tool("scaffold_project", {
                "full_name": top, "project_name": "demo app", "idea": query, "output_dir": tmp})
            assert not res.isError, res.content[0].text
            out = json.loads(res.content[0].text)
            root = Path(out["root"])
            print(f"\nscaffold_project -> {len(out['files'])} files:", out["files"])
            for f in ("ARCHITECTURE.md", "ATTRIBUTIONS.md", "README.md"):
                assert (root / f).is_file(), f"missing {f}"
            assert top in (root / "ATTRIBUTIONS.md").read_text(encoding="utf-8")
        print("\nE2E OK")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "pdf table extraction"))
