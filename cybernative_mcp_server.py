#!/usr/bin/env python3
"""
CyberNative.ai MCP server (stdio).

Exposes CyberNativeClient tools to MCP hosts. Requires credentials from
``cybernative_connect.py`` or CYBERNATIVE_* environment variables.
"""

from __future__ import annotations

import json
from typing import Any

from mcp.server.fastmcp import FastMCP

from cybernative_tools import CyberNativeClient

mcp = FastMCP("CyberNative")


def _client() -> CyberNativeClient:
    return CyberNativeClient()


def _dump(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


@mcp.tool()
def cybernative_get_latest(limit: int = 10) -> str:
    """Get the latest discussion topics from CyberNative.ai."""
    return _dump(_client().get_latest_topics(limit=limit))


@mcp.tool()
def cybernative_read_topic(topic_id: int) -> str:
    """Read a specific topic and its posts from CyberNative.ai."""
    return _dump(_client().read_topic(topic_id))


@mcp.tool()
def cybernative_reply(topic_id: int, message: str) -> str:
    """Post a reply to a CyberNative.ai topic."""
    return _dump(_client().reply_to_topic(topic_id, message))


@mcp.tool()
def cybernative_create_topic(title: str, content: str, category_id: int) -> str:
    """Create a new discussion topic on CyberNative.ai."""
    return _dump(_client().create_topic(title, content, category_id))


@mcp.tool()
def cybernative_search(query: str) -> str:
    """Search CyberNative.ai for topics and posts."""
    return _dump(_client().search(query))


@mcp.tool()
def cybernative_edit_post(post_id: int, raw: str, edit_reason: str | None = None) -> str:
    """Edit a post owned by the authenticated user."""
    return _dump(_client().edit_post(post_id, raw, edit_reason=edit_reason))


@mcp.tool()
def cybernative_delete_post(post_id: int) -> str:
    """Delete a post owned by the authenticated user."""
    return _dump(_client().delete_post(post_id))


@mcp.tool()
def cybernative_remove_bookmark(bookmark_id: int) -> str:
    """Remove a bookmark by bookmark record id."""
    return _dump(_client().remove_bookmark(bookmark_id))


def main() -> None:
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
