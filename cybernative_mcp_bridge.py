"""Map skills/mcp_tool.json tools to CyberNativeClient without logging secrets."""

from __future__ import annotations

import inspect
import json
import re
from pathlib import Path
from typing import Any

from cybernative_tools import CyberNativeClient

ROOT = Path(__file__).resolve().parent
MCP_TOOL_PATH = ROOT / "skills" / "mcp_tool.json"
TOOL_PREFIX = "cybernative_"
READ_ONLY_TOOL_NAMES = {
    "cybernative_get_latest_topics",
    "cybernative_read_topic",
    "cybernative_get_categories",
    "cybernative_list_notifications",
    "cybernative_list_bookmarks",
    "cybernative_search",
    "cybernative_search_topics",
    "cybernative_get_user",
    "cybernative_get_topic_url",
}
_SECRET_PATTERNS = (
    re.compile(r"(user[_-]?api[_-]?key['\"]?\s*[:=]\s*)[^\s'\"]+", re.IGNORECASE),
    re.compile(r"\b[A-Za-z0-9]{20,}\b"),
)


def load_mcp_tool_catalog() -> dict[str, Any]:
    return json.loads(MCP_TOOL_PATH.read_text(encoding="utf-8"))


def mcp_tool_specs(read_only: bool = False) -> list[dict[str, Any]]:
    catalog = load_mcp_tool_catalog()
    tools = [
        tool
        for tool in catalog.get("tools", [])
        if isinstance(tool, dict) and tool.get("name")
    ]
    if read_only:
        return [tool for tool in tools if tool["name"] in READ_ONLY_TOOL_NAMES]
    return tools


def tool_to_method_name(tool_name: str) -> str:
    if not tool_name.startswith(TOOL_PREFIX):
        raise ValueError(f"unexpected MCP tool name: {tool_name}")
    return tool_name[len(TOOL_PREFIX) :]


def public_client_method_names() -> set[str]:
    return {
        name
        for name, member in inspect.getmembers(CyberNativeClient, predicate=inspect.isfunction)
        if not name.startswith("_")
    }


def validate_bridge_surface(read_only: bool = False) -> list[str]:
    """Return validation errors; empty list means the bridge surface is aligned."""
    errors: list[str] = []
    methods = public_client_method_names()
    mapped_methods: set[str] = set()

    for spec in mcp_tool_specs(read_only=read_only):
        tool_name = spec["name"]
        try:
            method_name = tool_to_method_name(tool_name)
        except ValueError as exc:
            errors.append(str(exc))
            continue

        mapped_methods.add(method_name)
        if method_name not in methods:
            errors.append(f"{tool_name} has no CyberNativeClient.{method_name}")

        if "inputSchema" not in spec:
            errors.append(f"{tool_name} is missing inputSchema")

    if read_only:
        configured = {tool["name"] for tool in mcp_tool_specs()}
        unknown_read_only = sorted(READ_ONLY_TOOL_NAMES - configured)
        if unknown_read_only:
            errors.append("read-only tool set has unknown tools: " + ", ".join(unknown_read_only))
    else:
        missing_tools = sorted(methods - mapped_methods)
        if missing_tools:
            errors.append(
                "mcp_tool.json missing tools for client methods: "
                + ", ".join(f"cybernative_{name}" for name in missing_tools)
            )

    return errors


def sanitize_error_message(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[redacted]", redacted)
    return redacted


def dispatch_tool(
    client: CyberNativeClient,
    tool_name: str,
    arguments: dict[str, Any] | None,
    read_only: bool = False,
) -> Any:
    if read_only and tool_name not in READ_ONLY_TOOL_NAMES:
        raise ValueError(f"tool is not available in read-only mode: {tool_name}")
    method_name = tool_to_method_name(tool_name)
    method = getattr(client, method_name)
    return method(**(arguments or {}))
