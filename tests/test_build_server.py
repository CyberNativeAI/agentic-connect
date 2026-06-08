"""CYB-999601: Unit tests for build_server error-to-TextContent conversion.

Tests the async handlers registered by build_server() — list_tools and call_tool —
with direct invocation through the server's request_handlers registry.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import mcp.types as types

from cybernative_mcp_server import build_server
from cybernative_tools import CyberNativeAPIError, CyberNativeConfigurationError


def _make_creds_file() -> str:
    tmpdir = tempfile.mkdtemp()
    creds_path = Path(tmpdir) / "test_creds.json"
    creds_path.write_text(
        json.dumps(
            {
                "base_url": "http://127.0.0.1:9999",
                "user_api_key": "test-api-key",
                "user_api_client_id": "test-client-id",
            }
        ),
        encoding="utf-8",
    )
    return str(creds_path)


def _populate_tool_cache(server) -> None:
    asyncio.run(server.request_handlers[types.ListToolsRequest](None))


class BuildServerListToolsTest(unittest.TestCase):
    def test_list_tools_returns_all_tools_in_full_mode(self) -> None:
        creds_file = _make_creds_file()
        server = build_server(creds_file)
        handler = server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(handler(None))
        tools = result.root.tools
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 10)
        names = {t.name for t in tools}
        self.assertIn("cybernative_get_latest_topics", names)
        self.assertIn("cybernative_search", names)
        self.assertIn("cybernative_create_topic", names)
        self.assertIn("cybernative_reply_to_topic", names)

    def test_list_tools_read_only_mode_excludes_writes(self) -> None:
        creds_file = _make_creds_file()
        server = build_server(creds_file, read_only=True)
        handler = server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(handler(None))
        tools = result.root.tools
        names = {t.name for t in tools}
        self.assertIn("cybernative_get_latest_topics", names)
        self.assertIn("cybernative_search", names)
        self.assertNotIn("cybernative_create_topic", names)
        self.assertNotIn("cybernative_reply_to_topic", names)
        self.assertNotIn("cybernative_like_post", names)

    def test_list_tools_tools_have_required_fields(self) -> None:
        creds_file = _make_creds_file()
        server = build_server(creds_file)
        handler = server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(handler(None))
        for tool in result.root.tools:
            self.assertIsInstance(tool.name, str)
            self.assertGreater(len(tool.name), 0)
            self.assertIsInstance(tool.description, str)
            self.assertIsInstance(tool.inputSchema, dict)

    def test_list_tools_result_is_list_tools_result_type(self) -> None:
        creds_file = _make_creds_file()
        server = build_server(creds_file)
        handler = server.request_handlers[types.ListToolsRequest]
        result = asyncio.run(handler(None))
        self.assertIsInstance(result.root, types.ListToolsResult)


class BuildServerCallToolSuccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.creds_file = _make_creds_file()
        self.server = build_server(self.creds_file)
        _populate_tool_cache(self.server)
        self.handler = self.server.request_handlers[types.CallToolRequest]

    def _call_tool(self, tool_name: str, arguments: dict | None = None) -> types.ServerResult:
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name=tool_name,
                arguments=arguments if arguments is not None else {},
            ),
        )
        return asyncio.run(self.handler(req))

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_call_tool_returns_text_content_for_string_result(self, mock_dispatch) -> None:
        mock_dispatch.return_value = "simple string result"
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertEqual(len(result.root.content), 1)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].type, "text")
        self.assertEqual(result.root.content[0].text, "simple string result")

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_call_tool_returns_text_content_for_dict_result(self, mock_dispatch) -> None:
        mock_dispatch.return_value = {"key": "value", "nested": {"a": 1}}
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(
            result.root.content[0].text,
            json.dumps({"key": "value", "nested": {"a": 1}}),
        )

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_call_tool_returns_text_content_for_list_result(self, mock_dispatch) -> None:
        mock_dispatch.return_value = [1, 2, 3]
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].text, json.dumps([1, 2, 3]))

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_call_tool_returns_text_content_for_none_result(self, mock_dispatch) -> None:
        mock_dispatch.return_value = None
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].text, "null")


class BuildServerErrorToTextContentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.creds_file = _make_creds_file()
        self.server = build_server(self.creds_file)
        _populate_tool_cache(self.server)
        self.handler = self.server.request_handlers[types.CallToolRequest]

    def _call_tool(self, tool_name: str, arguments: dict | None = None) -> types.ServerResult:
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name=tool_name,
                arguments=arguments if arguments is not None else {},
            ),
        )
        return asyncio.run(self.handler(req))

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_cybernative_api_error_returns_text_content(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = CyberNativeAPIError("GET /t/99999.json failed with HTTP 404: Not Found")
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertEqual(len(result.root.content), 1)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].type, "text")
        self.assertIn("404", result.root.content[0].text)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_cybernative_configuration_error_returns_text_content(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = CyberNativeConfigurationError("Credentials file not found: missing.json")
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].type, "text")
        self.assertIn("Credentials file not found", result.root.content[0].text)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_value_error_returns_text_content(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = ValueError("tool is not available in read-only mode: cybernative_create_topic")
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].type, "text")
        self.assertIn("read-only", result.root.content[0].text)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_generic_exception_returns_text_content(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = RuntimeError("something unexpected")
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertIsInstance(result.root.content[0], types.TextContent)
        self.assertEqual(result.root.content[0].type, "text")
        self.assertIn("Tool cybernative_get_latest_topics failed", result.root.content[0].text)
        self.assertIn("something unexpected", result.root.content[0].text)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_errors_never_raise_through_handler(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = CyberNativeAPIError("API failure")
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_multiple_error_types_all_convert_to_text_content(self, mock_dispatch) -> None:
        errors_and_checks = [
            (CyberNativeAPIError("API 500 Server Error"), "500"),
            (CyberNativeConfigurationError("Bad config"), "Bad config"),
            (ValueError("Invalid argument for tool"), "Invalid argument"),
        ]
        for exc, expected_substring in errors_and_checks:
            mock_dispatch.side_effect = exc
            result = self._call_tool("cybernative_get_latest_topics")
            self.assertFalse(result.root.isError, f"Expected no error for {type(exc).__name__}")
            self.assertIsInstance(result.root.content[0], types.TextContent)
            self.assertIn(expected_substring, result.root.content[0].text)

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_error_message_does_not_expose_credentials(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = CyberNativeAPIError(
            "Request failed with user_api_key=sk-abc123secret user_api_key: deadbeef token=ABCDEF1234567890abcdef1234567890"
        )
        result = self._call_tool("cybernative_get_latest_topics")
        text = result.root.content[0].text
        self.assertNotIn("sk-abc123secret", text)
        self.assertNotIn("deadbeef", text)
        self.assertIn("[redacted]", text)


class BuildServerCallToolReadOnlyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.creds_file = _make_creds_file()
        self.server = build_server(self.creds_file, read_only=True)
        _populate_tool_cache(self.server)
        self.handler = self.server.request_handlers[types.CallToolRequest]

    def _call_tool(self, tool_name: str, arguments: dict | None = None) -> types.ServerResult:
        req = types.CallToolRequest(
            method="tools/call",
            params=types.CallToolRequestParams(
                name=tool_name,
                arguments=arguments if arguments is not None else {},
            ),
        )
        return asyncio.run(self.handler(req))

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_read_tool_allowed_with_read_only_server(self, mock_dispatch) -> None:
        mock_dispatch.return_value = "ok"
        result = self._call_tool("cybernative_get_latest_topics")
        self.assertFalse(result.root.isError)
        self.assertEqual(result.root.content[0].text, "ok")

    @patch("cybernative_mcp_server.dispatch_tool")
    def test_write_tool_blocked_with_read_only_server(self, mock_dispatch) -> None:
        mock_dispatch.side_effect = ValueError("tool is not available in read-only mode: cybernative_reply_to_topic")
        result = self._call_tool("cybernative_reply_to_topic", {"topic_id": 1, "message": "Hi"})
        self.assertFalse(result.root.isError)
        self.assertIn("read-only", result.root.content[0].text)


if __name__ == "__main__":
    unittest.main()
