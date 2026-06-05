#!/usr/bin/env python3
"""
Validate server.json for MCP Registry publish readiness.

Checks structure, version sync with pyproject.toml, and PyPI mcp-name marker in README.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_JSON = REPO_ROOT / "server.json"
README = REPO_ROOT / "README.md"
PYPROJECT = REPO_ROOT / "pyproject.toml"

REQUIRED_TOP_LEVEL = ("name", "title", "description", "version", "packages")
MCP_NAME_RE = re.compile(r"mcp-name:\s*(\S+)")


def _read_pyproject_version() -> str | None:
    if not PYPROJECT.exists():
        return None
    for line in PYPROJECT.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("version = "):
            return stripped.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def validate() -> list[str]:
    errors: list[str] = []

    if not SERVER_JSON.exists():
        return ["server.json not found"]

    manifest = json.loads(SERVER_JSON.read_text(encoding="utf-8"))
    for key in REQUIRED_TOP_LEVEL:
        if key not in manifest:
            errors.append(f"server.json missing required field: {key}")

    server_name = manifest.get("name", "")
    packages = manifest.get("packages") or []
    if not packages:
        errors.append("server.json packages[] is empty")
    else:
        pkg = packages[0]
        for field in ("registryType", "identifier", "version", "transport"):
            if field not in pkg:
                errors.append(f"packages[0] missing {field}")
        if pkg.get("registryType") != "pypi":
            errors.append("packages[0].registryType must be pypi for this repo")
        transport = pkg.get("transport") or {}
        if transport.get("type") != "stdio":
            errors.append("packages[0].transport.type must be stdio")

    py_version = _read_pyproject_version()
    if py_version and manifest.get("version") != py_version:
        errors.append(
            f"version mismatch: server.json={manifest.get('version')} pyproject.toml={py_version}"
        )
    if py_version and packages and packages[0].get("version") != py_version:
        errors.append(
            f"package version mismatch: packages[0]={packages[0].get('version')} pyproject.toml={py_version}"
        )
    if py_version and packages and packages[0].get("identifier"):
        expected_pkg = "cybernative-mcp"
        if packages[0]["identifier"] != expected_pkg:
            errors.append(f"packages[0].identifier must be {expected_pkg}")

    readme = README.read_text(encoding="utf-8") if README.exists() else ""
    mcp_match = MCP_NAME_RE.search(readme)
    if not mcp_match:
        errors.append("README.md missing mcp-name marker for PyPI ownership verification")
    elif mcp_match.group(1) != server_name:
        errors.append(
            f"README mcp-name ({mcp_match.group(1)}) does not match server.json name ({server_name})"
        )

    mcp_server = REPO_ROOT / "cybernative_mcp_server.py"
    if not mcp_server.exists():
        errors.append("cybernative_mcp_server.py not found")

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("mcp manifest validation failed:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1
    print("ok: server.json manifest ready for MCP Registry publish")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
