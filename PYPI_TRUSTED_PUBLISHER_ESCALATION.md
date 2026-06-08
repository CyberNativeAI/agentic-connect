# PyPI Trusted Publisher Escalation

## Summary

Configuring a PyPI trusted publisher requires a human with PyPI owner access to the `cybernative-connect` project. This cannot be automated — PyPI only exposes the trusted publisher configuration through its web UI. The repo-side setup (GitHub Actions workflow with `id-token: write` permission) is already complete.

## Exact Steps for the Board/PyPI Owner

### Step 1: Log into PyPI

Go to https://pypi.org/manage/projects/ and log in as an owner of the `cybernative-connect` project.

### Step 2: Navigate to project publishing settings

Click "Manage" on the `cybernative-connect` project, then click "Publishing" in the sidebar.

### Step 3: Add a GitHub Actions trusted publisher

Fill in the form with these exact values:

| Field | Value |
|-------|-------|
| GitHub repository owner | CyberNativeAI |
| GitHub repository name | agentic-connect |
| Workflow name | .github/workflows/publish-mcp.yml |
| Environment name | (leave empty) |

### Step 4: Click "Add"

The publisher will be registered immediately.

### Step 5: Rerun the v1.3.2 release

After the publisher is configured, rerun the failed workflow:

```bash
gh workflow run publish-mcp.yml --ref v1.3.2 --repo CyberNativeAI/agentic-connect
```

Or via the GitHub UI: go to https://github.com/CyberNativeAI/agentic-connect/actions/workflows/publish-mcp.yml and click "Run workflow" with branch/ref `v1.3.2`.

## What's Already Done (Repo Side)

- `.github/workflows/publish-mcp.yml` has `id-token: write` permission (required for OIDC)
- The workflow uses `pypa/gh-action-pypi-publish@release/v1` which supports trusted publishing out of the box
- The release tag `v1.3.2` exists at commit `06a664c`
- All tests, MCP bridge validation, server.json validation, and package build pass
- The only failure was `invalid-publisher` — PyPI had no matching trusted publisher

## Verification

After the workflow reruns, check:
1. The GitHub Actions run succeeds at the "Publish package to PyPI" step
2. The package appears at https://pypi.org/project/cybernative-connect/1.3.2/
3. The MCP Registry publish step produces a live registry listing URL