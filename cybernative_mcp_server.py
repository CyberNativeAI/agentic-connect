#!/usr/bin/env python3
"""Stdio MCP server that dispatches tools to CyberNativeClient."""

from __future__ import annotations

import argparse
import asyncio
import json
import sys

from cybernative_mcp_bridge import (
    dispatch_tool,
    load_mcp_tool_catalog,
    mcp_tool_specs,
    sanitize_error_message,
    validate_bridge_surface,
)
from cybernative_tools import (
    CyberNativeAPIError,
    CyberNativeConfigurationError,
    CyberNativeClient,
)


def build_server(credentials_file: str):
    from mcp.server import Server
    import mcp.types as types

    server = Server("cybernative")
    client_holder: dict[str, CyberNativeClient | None] = {"client": None}

    def get_client() -> CyberNativeClient:
        if client_holder["client"] is None:
            client_holder["client"] = CyberNativeClient(credentials_file=credentials_file)
        return client_holder["client"]

    @server.list_tools()
    async def list_tools(_request: types.ListToolsRequest) -> list[types.Tool]:
        return [
            types.Tool(
                name=spec["name"],
                description=spec.get("description", ""),
                inputSchema=spec.get("inputSchema", {"type": "object", "properties": {}}),
            )
            for spec in mcp_tool_specs()
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict | None) -> list[types.TextContent]:
        try:
            result = dispatch_tool(get_client(), name, arguments)
            if isinstance(result, str):
                payload = result
            else:
                payload = json.dumps(result, default=str)
            return [types.TextContent(type="text", text=payload)]
        except (CyberNativeConfigurationError, CyberNativeAPIError, ValueError) as exc:
            message = sanitize_error_message(str(exc))
            return [types.TextContent(type="text", text=message)]
        except Exception as exc:  # pragma: no cover - defensive guard for tool calls
            message = sanitize_error_message(f"Tool {name} failed: {exc}")
            return [types.TextContent(type="text", text=message)]

    return server


async def run_stdio_server(credentials_file: str) -> None:
    from mcp.server import NotificationOptions
    from mcp.server.models import InitializationOptions
    from mcp.server.stdio import stdio_server

    catalog = load_mcp_tool_catalog()
    server = build_server(credentials_file)

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name=str(catalog.get("name", "cybernative")),
                server_version=str(catalog.get("version", "1.0.0")),
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                ),
            ),
        )


def run_validate() -> int:
    errors = validate_bridge_surface()
    print("CyberNative MCP bridge validation")
    print(f"Tools in skills/mcp_tool.json: {len(mcp_tool_specs())}")
    if errors:
        print("\nDrift found:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("OK: MCP tool names map to CyberNativeClient methods.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run or validate the CyberNative MCP sharing bridge."
    )
    parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate tool mapping without loading credentials or starting stdio.",
    )
    parser.add_argument(
        "--credentials-file",
        default="cybernative_agent_credentials.json",
        help="Path to CyberNative agent credentials JSON.",
    )
    args = parser.parse_args(argv)

    if args.validate:
        return run_validate()

    try:
        asyncio.run(run_stdio_server(args.credentials_file))
    except KeyboardInterrupt:
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
