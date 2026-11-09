# Contributing

Thanks for helping. Small, focused pull requests are easiest to review.

## Set up

```bash
git clone https://github.com/beingaeditor/reuse-first
cd reuse-first
pip install -r server/requirements.txt pytest pytest-asyncio
python -m pytest tests -q
```

The unit tests need no network. `python tests/e2e_live.py "url shortener"` runs the whole flow against live GitHub; set `GITHUB_TOKEN` (a token with no scopes is enough) to avoid rate limits.

## Making a change

- New to the project? Look for issues labelled [good first issue](https://github.com/beingaeditor/reuse-first/labels/good%20first%20issue).
- For anything bigger than a small fix, open an issue or a Discussion first so we can agree on the approach.
- Add or update a test for any logic you change, and make sure `python -m pytest tests -q` passes.
- The core code (`server/` except `server.py`) uses only the Python standard library. Please keep it that way.

## Response time

New issues and pull requests get a first reply within one day.

## License

By contributing you agree that your contribution is licensed under the [MIT License](LICENSE).
