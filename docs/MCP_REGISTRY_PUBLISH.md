# MCP Registry publish (zero lead time after CYB-189)

This repo ships `cybernative-mcp` on PyPI and `io.github.cybernativeai/cybernative` on the MCP Registry. Publishing is blocked on CYB-189 (PyPI trusted publisher + registry credentials). Until then, keep artifacts and validation green locally.

## Pre-publish checklist (local, no credentials)

```bash
python -m pip install -r requirements-dev.txt mcp build
pytest
python scripts/_ce_skill_validate.py
python scripts/_validate_mcp_manifest.py
python cybernative_mcp_server.py --validate
python cybernative_mcp_server.py --validate --read-only
python -m build
```

Expected `dist/` artifacts after build:

- `cybernative_mcp-1.3.2-py3-none-any.whl`
- `cybernative_mcp-1.3.2.tar.gz`

## One-command publish (after CYB-189 unlocks)

Tag push triggers [`.github/workflows/publish-mcp.yml`](../.github/workflows/publish-mcp.yml) (PyPI via trusted publisher, then MCP Registry via `mcp-publisher` GitHub OIDC):

```bash
git tag v1.3.2 && git push origin v1.3.2
```

## Read-only MCP hosts

For least-privilege deployments, run the stdio server with write tools omitted:

```bash
python cybernative_mcp_server.py --read-only
```

Validate the read-only surface without credentials:

```bash
python cybernative_mcp_server.py --validate --read-only
```

## Version sync

Keep these aligned on every release:

| File | Field |
| --- | --- |
| `pyproject.toml` | `[project].version` |
| `server.json` | `version` and `packages[0].version` |
| `skills/mcp_tool.json` | `version` |
| `README.md` | publish tag example |
