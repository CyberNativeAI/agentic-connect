#!/usr/bin/env python3
"""Validate that public CyberNativeClient methods stay represented in skills/docs."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLIENT_PATH = ROOT / "cybernative_tools.py"
SKILL_AUDIT_PATH = ROOT / "SKILL_AUDIT.md"
MARKDOWN_FILES = [
    ROOT / "README.md",
    ROOT / "AGENTS.md",
    ROOT / "skills" / "claude_skill.md",
    ROOT / "skills" / "cursor_rules.md",
    SKILL_AUDIT_PATH,
]
MCP_PATH = ROOT / "skills" / "mcp_tool.json"
OPENAI_PATH = ROOT / "skills" / "openai_function_schema.json"


def public_client_methods() -> list[str]:
    tree = ast.parse(CLIENT_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CyberNativeClient":
            methods = [
                item.name
                for item in node.body
                if isinstance(item, ast.FunctionDef)
                and not item.name.startswith("_")
                and item.name != "__init__"
            ]
            return methods
    raise RuntimeError("Could not locate CyberNativeClient in cybernative_tools.py")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_json_functions(methods: list[str]) -> list[str]:
    errors: list[str] = []

    mcp = load_json(MCP_PATH)
    mcp_names = {tool["name"] for tool in mcp.get("tools", []) if isinstance(tool, dict)}
    expected_mcp = {f"cybernative_{name}" for name in methods}
    missing_mcp = sorted(expected_mcp - mcp_names)
    if missing_mcp:
        errors.append(f"mcp_tool.json missing: {', '.join(missing_mcp)}")

    openai = load_json(OPENAI_PATH)
    openai_names = {fn["name"] for fn in openai.get("functions", []) if isinstance(fn, dict)}
    missing_openai = sorted(set(methods) - openai_names)
    if missing_openai:
        errors.append(f"openai_function_schema.json missing: {', '.join(missing_openai)}")

    return errors


def check_markdown(methods: list[str]) -> list[str]:
    errors: list[str] = []
    for path in MARKDOWN_FILES:
        text = path.read_text(encoding="utf-8")
        missing = [name for name in methods if not re.search(rf"\b{re.escape(name)}\b", text)]
        if missing:
            errors.append(f"{path.relative_to(ROOT)} missing: {', '.join(missing)}")
    return errors


def main() -> int:
    methods = public_client_methods()
    errors = check_json_functions(methods) + check_markdown(methods)

    print("CyberNative skill surface validation")
    print(f"Public client methods: {', '.join(methods)}")
    if errors:
        print("\nDrift found:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: client surface matches bundled skills/docs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
