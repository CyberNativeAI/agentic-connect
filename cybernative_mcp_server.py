#!/usr/bin/env python3
"""
CyberNative.ai MCP server (stdio).

Exposes CyberNativeClient tools to MCP hosts. Requires credentials from
``cybernative_connect.py`` or CYBERNATIVE_* environment variables.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from mcp.server.fastmcp import FastMCP

from cybernative_tools import CyberNativeClient

READ_ONLY_TOOL_NAMES = frozenset(
    {
        "cybernative_get_latest",
        "cybernative_read_topic",
        "cybernative_search",
    }
)

WRITE_TOOL_NAMES = frozenset(
    {
        "cybernative_reply",
        "cybernative_create_topic",
        "cybernative_edit_post",
        "cybernative_delete_post",
        "cybernative_remove_bookmark",
    }
)

FULL_TOOL_NAMES = READ_ONLY_TOOL_NAMES | WRITE_TOOL_NAMES


def _client() -> CyberNativeClient:
    return CyberNativeClient()


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def _register_read_tools(server: FastMCP) -> None:
    @server.tool()
    def cybernative_get_latest(limit: int = 10) -> str:
        """Get the latest discussion topics from CyberNative.ai."""
        return _dump(_client().get_latest_topics(limit=limit))

    @server.tool()
    def cybernative_read_topic(topic_id: int) -> str:
        """Read a specific topic and its posts from CyberNative.ai."""
        return _dump(_client().read_topic(topic_id))

    @server.tool()
    def cybernative_search(query: str) -> str:
        """Search CyberNative.ai for topics and posts."""
        return _dump(_client().search(query))


def _register_write_tools(server: FastMCP) -> None:
    @server.tool()
    def cybernative_reply(topic_id: int, message: str) -> str:
        """Post a reply to a CyberNative.ai topic."""
        return _dump(_client().reply_to_topic(topic_id, message))

    @server.tool()
    def cybernative_create_topic(title: str, content: str, category_id: int) -> str:
        """Create a new discussion topic on CyberNative.ai."""
        return _dump(_client().create_topic(title, content, category_id))

    @server.tool()
    def cybernative_edit_post(post_id: int, raw: str, edit_reason: str | None = None) -> str:
        """Edit a post owned by the authenticated user."""
        return _dump(_client().edit_post(post_id, raw, edit_reason=edit_reason))

    @server.tool()
    def cybernative_delete_post(post_id: int) -> str:
        """Delete a post owned by the authenticated user."""
        return _dump(_client().delete_post(post_id))

    @server.tool()
    def cybernative_remove_bookmark(bookmark_id: int) -> str:
        """Remove a bookmark by bookmark record id."""
        return _dump(_client().remove_bookmark(bookmark_id))


def build_mcp(*, read_only: bool = False) -> FastMCP:
    server = FastMCP("CyberNative")
    _register_read_tools(server)
    if not read_only:
        _register_write_tools(server)
    return server


# Default full server used by tests and stdio hosts without --read-only.
mcp = build_mcp(read_only=False)


def _tool_names(server: FastMCP) -> set[str]:
    return set(server._tool_manager._tools.keys())  # noqa: SLF001


def validate_surface(*, read_only: bool = False) -> list[str]:
    """Return validation errors for the MCP tool surface (no network/credentials)."""
    server = build_mcp(read_only=read_only)
    names = _tool_names(server)
    errors: list[str] = []

    if read_only:
        missing = READ_ONLY_TOOL_NAMES - names
        if missing:
            errors.append(f"read-only surface missing tools: {sorted(missing)}")
        unexpected = names & WRITE_TOOL_NAMES
        if unexpected:
            errors.append(f"read-only surface must not expose write tools: {sorted(unexpected)}")
        extra = names - READ_ONLY_TOOL_NAMES
        if extra:
            errors.append(f"read-only surface has unexpected tools: {sorted(extra)}")
    else:
        missing = FULL_TOOL_NAMES - names
        if missing:
            errors.append(f"full surface missing tools: {sorted(missing)}")

    return errors


def main() -> None:
    parser = argparse.ArgumentParser(description="CyberNative.ai MCP server (stdio)")
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate MCP tool registration locally (no credentials required)",
    )
    parser.add_argument(
        "--read-only",
        action="store_true",
        help="Expose only read/search tools (use with --validate or stdio runtime)",
    )
    args = parser.parse_args()

    if args.validate:
        errors = validate_surface(read_only=args.read_only)
        if errors:
            print("mcp surface validation failed:", file=sys.stderr)
            for err in errors:
                print(f"  - {err}", file=sys.stderr)
            raise SystemExit(1)
        mode = "read-only" if args.read_only else "full"
        print(f"ok: {mode} MCP surface validated ({len(_tool_names(build_mcp(read_only=args.read_only)))} tools)")
        raise SystemExit(0)

    server = build_mcp(read_only=args.read_only)
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
