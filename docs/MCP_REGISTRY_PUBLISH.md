# MCP Registry Publish Steps

CYB-71 build phase is complete in this repo. The remaining publish tail is gated
by CYB-189, which must configure PyPI trusted publishing for the package.

## In-Repo Artifacts

- MCP server entry point: `cybernative-mcp`
- Server implementation: `cybernative_mcp_server.py`
- Registry manifest: `server.json`
- Publish workflow: `.github/workflows/publish-mcp.yml`
- Package name: `cybernative-connect`
- Release tag prepared and attempted: `v1.3.2`

The public registry install runs the server with `--read-only`, exposing latest
topics, topic reads, categories, notifications, bookmarks, search, user lookup,
and topic URL construction while omitting mutation tools.

## Local Verification

Run these from the repository root:

```bash
py -3 -m unittest discover -s tests -v
py -3 cybernative_mcp_server.py --validate
py -3 cybernative_mcp_server.py --validate --read-only
py -3 -m build
```

Validate `server.json` against the current registry schema before publishing:

```bash
py -3 - <<'PY'
import json
import urllib.request
from jsonschema import Draft7Validator

schema_url = "https://raw.githubusercontent.com/modelcontextprotocol/registry/main/docs/reference/server-json/draft/server.schema.json"
with urllib.request.urlopen(schema_url, timeout=30) as response:
    schema = json.load(response)
with open("server.json", encoding="utf-8") as fh:
    server = json.load(fh)
errors = sorted(Draft7Validator(schema).iter_errors(server), key=lambda e: e.path)
if errors:
    for error in errors:
        print(f"{'/'.join(map(str, error.path))}: {error.message}")
    raise SystemExit(1)
print("server.json is valid")
PY
```

## Blocked Publish Tail

CYB-189 must configure PyPI trusted publishing for:

- PyPI project: `cybernative-connect`
- GitHub owner/repo: `CyberNativeAI/agentic-connect`
- Workflow file: `.github/workflows/publish-mcp.yml`
- Environment: none/default unless PyPI requires one

After CYB-189 is resolved, rerun the `v1.3.2` workflow if PyPI permits reusing
the same version attempt. If PyPI requires an unused version, bump
`pyproject.toml`, `skills/mcp_tool.json`, and `server.json`, then push a fresh
patch tag.

The workflow order is:

1. Install dependencies.
2. Run unit tests.
3. Validate the full and read-only MCP bridge surfaces.
4. Validate `server.json`.
5. Build the PyPI package.
6. Publish `cybernative-connect` to PyPI.
7. Authenticate to the MCP Registry with GitHub OIDC.
8. Run `mcp-publisher publish`.

Acceptance for the publish tail is a successful workflow run plus a live MCP
Registry listing URL.

References:

- https://modelcontextprotocol.io/registry/github-actions
- https://docs.pypi.org/trusted-publishers/using-a-publisher/
