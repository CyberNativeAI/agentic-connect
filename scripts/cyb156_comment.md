## CYB-156 complete — installable MCP sharing bridge

Shipped a local stdio MCP server that dispatches every `skills/mcp_tool.json` tool to `CyberNativeClient` without logging secrets.

### Changed files
- `cybernative_mcp_bridge.py` — tool→method mapping, dispatch, drift validation
- `cybernative_mcp_server.py` — stdio MCP server CLI (`--validate`, `--credentials-file`)
- `requirements-mcp.txt` — optional MCP SDK deps (Python 3.10+)
- `tests/test_cybernative_mcp_bridge.py` — mapping + dispatch tests
- `README.md`, `docs/SHARING_SKILLS.md`, `SKILL_AUDIT.md` — install/use + local vs registry guidance

### Verification
```text
py -3 cybernative_mcp_server.py --validate  → OK (15 tools)
py -3 scripts/_ce_skill_validate.py         → OK
py -3 -m unittest discover -s tests -v    → OK (13 tests)
```

### Residual risk
- MCP SDK requires Python 3.10+ (`requirements-mcp.txt`); core connector still documents 3.9+.
- Public MCP Registry / PyPI publication **not** done — needs CTO/board approval per issue scope.

### Next owner
- **CTO** — review bridge for internal rollout; decide on registry/public package publication.
