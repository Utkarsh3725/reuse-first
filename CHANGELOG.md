# Changelog

## v0.1.0 (2026-11-10)

First release.

- Claude Code plugin: MCP server with `find_repos`, `blueprint` and `scaffold_project`, plus a skill that runs search, compare, scaffold and build.
- Ranking by recency, stars, open-issue load and keyword fit. Missing data counts as unknown, not zero. Unlicensed and archived repos are excluded; copyleft only when allowed.
- Blueprints: languages, frameworks, layers, entrypoints, dependencies and a build plan. Scaffolds mirror the layout and write `ARCHITECTURE.md` and `ATTRIBUTIONS.md`. No code is copied.
- Command line with no install: `python server/cli.py find | blueprint | scaffold`, standard library only.
- GitHub errors are one readable line (rate limit, bad token, not found); the CLI exits with code 2.
- Web demo (`demo/app.py`).
