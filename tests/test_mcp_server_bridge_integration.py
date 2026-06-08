"""CYB-999584: Bridge/server-level integration tests for the MCP dispatch layer.

Tests the dispatch_tool function with various argument shapes, read-only enforcement,
and error propagation through the bridge, plus validates the full MCP server tool listing.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from cybernative_mcp_bridge import (
    dispatch_tool,
    mcp_tool_specs,
    sanitize_error_message,
    validate_bridge_surface,
)
from cybernative_tools import CyberNativeAPIError, CyberNativeConfigurationError, CyberNativeClient


class JsonStubHandler(BaseHTTPRequestHandler):
    response_body = b"{}"

    def do_GET(self) -> None:
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(JsonStubHandler.response_body)

    def log_message(self, *_args, **_kwargs) -> None:
        return


class JsonStubServer:
    def __init__(self):
        self.httpd = HTTPServer(("127.0.0.1", 0), JsonStubHandler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.httpd.shutdown()
        self.httpd.server_close()

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"


def _make_client(base_url: str) -> CyberNativeClient:
    creds = {
        "base_url": base_url,
        "user_api_key": "test-api-key",
        "user_api_client_id": "test-client-id",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "creds.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        return CyberNativeClient(credentials_file=str(path), max_retries=0)


class DispatchErrorPropagationTest(unittest.TestCase):
    """Tests that errors from the client layer propagate correctly through dispatch_tool."""

    def test_client_configuration_error_bubbles_up(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "nonexistent.json")
            with self.assertRaises(CyberNativeConfigurationError) as ctx:
                CyberNativeClient(credentials_file=path, max_retries=0)
            self.assertIn("not found", str(ctx.exception))

    def test_api_error_on_read_tool_bubbles_up(self) -> None:
        with JsonStubServer() as server:
            creds = {
                "base_url": server.base_url,
                "user_api_key": "test-api-key",
                "user_api_client_id": "test-client-id",
            }
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "creds.json"
                path.write_text(json.dumps(creds), encoding="utf-8")
                client = CyberNativeClient(credentials_file=str(path), max_retries=0)

            client.read_topic = lambda topic_id: (_ for _ in ()).throw(
                CyberNativeAPIError("GET /t/99999.json failed with HTTP 404: Not Found")
            )
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_read_topic", {"topic_id": 99999})
            self.assertIn("404", str(ctx.exception))


class DispatchEdgeCaseTest(unittest.TestCase):
    """Tests dispatch_tool with edge case argument shapes and unknown tools."""

    def test_empty_arguments_work_for_no_arg_methods(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_get_categories", {})
            self.assertEqual(result, [])

    def test_none_arguments_coerced_to_empty(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_list_notifications", None)
            self.assertEqual(result, {})

    def test_unknown_tool_name_raises_attribute_error(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(AttributeError):
                dispatch_tool(client, "cybernative_nonexistent_handler", {})

    def test_non_prefixed_tool_name_raises_value_error(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(ValueError):
                dispatch_tool(client, "bad_prefix_get_latest_topics", {})

    def test_dispatch_tool_passes_extra_arguments(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            topic = {"slug": "test-slug", "id": 99}
            result = dispatch_tool(client, "cybernative_get_topic_url", {"topic": topic})
            self.assertIsInstance(result, str)
            self.assertIn("/t/test-slug/99", result)


class ReadOnlyEnforcementTest(unittest.TestCase):
    """Tests that read-only mode correctly blocks write tool dispatch."""

    def test_write_tool_in_read_only_mode_raises_value_error(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(ValueError) as ctx:
                dispatch_tool(
                    client,
                    "cybernative_create_topic",
                    {"title": "Test", "content": "Body", "category_id": 1},
                    read_only=True,
                )
            self.assertIn("read-only", str(ctx.exception).lower())

    def test_reply_to_topic_blocked_in_read_only_mode(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(ValueError):
                dispatch_tool(
                    client,
                    "cybernative_reply_to_topic",
                    {"topic_id": 1, "message": "Hi"},
                    read_only=True,
                )

    def test_like_post_blocked_in_read_only_mode(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(ValueError):
                dispatch_tool(
                    client,
                    "cybernative_like_post",
                    {"post_id": 1},
                    read_only=True,
                )

    def test_read_tool_allowed_in_read_only_mode(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(
                client,
                "cybernative_get_latest_topics",
                {"limit": 5},
                read_only=True,
            )
            self.assertEqual(result, [])

    def test_search_allowed_in_read_only_mode(self) -> None:
        with JsonStubServer() as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(
                client,
                "cybernative_search",
                {"query": "test"},
                read_only=True,
            )
            self.assertEqual(result, {})


class ToolSpecIntegrationTest(unittest.TestCase):
    """Tests that mcp_tool_specs returns real data from skills/mcp_tool.json."""

    def test_full_specs_include_all_tools(self) -> None:
        specs = mcp_tool_specs(read_only=False)
        names = {spec["name"] for spec in specs}
        self.assertIn("cybernative_get_latest_topics", names)
        self.assertIn("cybernative_read_topic", names)
        self.assertIn("cybernative_search", names)
        self.assertIn("cybernative_create_topic", names)
        self.assertIn("cybernative_reply_to_topic", names)
        self.assertGreater(len(specs), 10)

    def test_read_only_specs_exclude_write_tools(self) -> None:
        specs = mcp_tool_specs(read_only=True)
        names = {spec["name"] for spec in specs}
        self.assertIn("cybernative_get_latest_topics", names)
        self.assertNotIn("cybernative_create_topic", names)
        self.assertNotIn("cybernative_reply_to_topic", names)
        self.assertNotIn("cybernative_like_post", names)

    def test_all_specs_have_name_and_input_schema(self) -> None:
        for spec in mcp_tool_specs():
            self.assertIn("name", spec)
            self.assertIn("inputSchema", spec)
            self.assertIsInstance(spec["name"], str)
            self.assertIsInstance(spec["inputSchema"], dict)

    def test_bridge_surface_is_valid(self) -> None:
        errors = validate_bridge_surface()
        self.assertEqual(errors, [], "\n".join(errors))

    def test_read_only_bridge_surface_is_valid(self) -> None:
        errors = validate_bridge_surface(read_only=True)
        self.assertEqual(errors, [], "\n".join(errors))


if __name__ == "__main__":
    unittest.main()
