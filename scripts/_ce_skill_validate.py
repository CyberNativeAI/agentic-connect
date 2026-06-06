#!/usr/bin/env python3
"""
Skill-surface drift guard for agentic-connect.

Ensures every public CyberNativeClient method is documented in SKILL_AUDIT.md and
referenced in bundled skills under skills/.
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = REPO_ROOT / "cybernative_tools.py"
SKILL_AUDIT_PATH = REPO_ROOT / "SKILL_AUDIT.md"
SKILLS_DIR = REPO_ROOT / "skills"

# Methods that are public on the class but not part of the operator API surface.
EXCLUDED_METHODS = frozenset()


def public_client_methods() -> list[str]:
    tree = ast.parse(TOOLS_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CyberNativeClient":
            names: list[str] = []
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                    if item.name not in EXCLUDED_METHODS:
                        names.append(item.name)
            return sorted(names)
    raise RuntimeError("CyberNativeClient class not found in cybernative_tools.py")


def skill_corpus() -> str:
    parts = [SKILL_AUDIT_PATH.read_text(encoding="utf-8")]
    for path in sorted(SKILLS_DIR.iterdir()):
        if path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n".join(parts)


def validate() -> list[str]:
    errors: list[str] = []
    methods = public_client_methods()
    audit_text = SKILL_AUDIT_PATH.read_text(encoding="utf-8") if SKILL_AUDIT_PATH.exists() else ""
    corpus = skill_corpus()

    for name in methods:
        token = f"`{name}`"
        if token not in audit_text and name not in audit_text:
            errors.append(f"{name}: missing from SKILL_AUDIT.md")
        if name not in corpus:
            errors.append(f"{name}: missing from skills/* (and SKILL_AUDIT.md corpus)")

    return errors


def main() -> int:
    if not TOOLS_PATH.exists():
        print(f"error: {TOOLS_PATH} not found", file=sys.stderr)
        return 1
    if not SKILL_AUDIT_PATH.exists():
        print(f"error: {SKILL_AUDIT_PATH} not found", file=sys.stderr)
        return 1

    errors = validate()
    if errors:
        print("skill drift detected:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    print(f"ok: {len(public_client_methods())} public CyberNativeClient methods covered")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
