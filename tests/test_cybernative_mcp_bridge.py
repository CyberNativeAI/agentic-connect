import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import cybernative_mcp_server
from cybernative_mcp_bridge import (
    READ_ONLY_TOOL_NAMES,
    dispatch_tool,
    load_mcp_tool_catalog,
    mcp_tool_specs,
    sanitize_error_message,
    tool_to_method_name,
    validate_bridge_surface,
)
from cybernative_tools import CyberNativeClient


class CyberNativeMcpBridgeTest(unittest.TestCase):
    def test_validate_bridge_surface_is_clean(self) -> None:
        errors = validate_bridge_surface()
        self.assertEqual(errors, [], "\n".join(errors))

    def test_validate_read_only_surface_is_clean(self) -> None:
        errors = validate_bridge_surface(read_only=True)
        self.assertEqual(errors, [], "\n".join(errors))

    def test_read_only_specs_exclude_write_tools(self) -> None:
        tool_names = {spec["name"] for spec in mcp_tool_specs(read_only=True)}

        self.assertEqual(tool_names, READ_ONLY_TOOL_NAMES)
        self.assertNotIn("cybernative_create_topic", tool_names)
        self.assertNotIn("cybernative_reply_to_topic", tool_names)
        self.assertNotIn("cybernative_like_post", tool_names)

    def test_every_mcp_tool_maps_to_client_method(self) -> None:
        client_methods = {
            name
            for name in dir(CyberNativeClient)
            if not name.startswith("_") and callable(getattr(CyberNativeClient, name))
        }
        for spec in mcp_tool_specs():
            method_name = tool_to_method_name(spec["name"])
            self.assertIn(method_name, client_methods, spec["name"])

    def test_dispatch_tool_calls_client_method(self) -> None:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            client = CyberNativeClient(credentials_file=str(path), max_retries=0)

        topic = {"slug": "hello", "id": 1}
        with patch.object(CyberNativeClient, "get_topic_url", return_value="https://example.test/t/hello/1") as mocked:
            result = dispatch_tool(client, "cybernative_get_topic_url", {"topic": topic})

        self.assertEqual(result, "https://example.test/t/hello/1")
        mocked.assert_called_once_with(topic=topic)

    def test_dispatch_tool_rejects_write_tool_in_read_only_mode(self) -> None:
        client = object()

        with self.assertRaisesRegex(ValueError, "read-only mode"):
            dispatch_tool(client, "cybernative_create_topic", {}, read_only=True)

    def test_validate_mode_skips_stdio_server(self) -> None:
        with patch.object(
            cybernative_mcp_server,
            "run_stdio_server",
            side_effect=AssertionError("stdio should not run during validation"),
        ):
            self.assertEqual(cybernative_mcp_server.main(["--validate"]), 0)

    def test_validate_read_only_mode_skips_stdio_server(self) -> None:
        with patch.object(
            cybernative_mcp_server,
            "run_stdio_server",
            side_effect=AssertionError("stdio should not run during validation"),
        ):
            self.assertEqual(cybernative_mcp_server.main(["--validate", "--read-only"]), 0)

    def test_tool_to_method_name_raises_on_bad_prefix(self) -> None:
        with self.assertRaisesRegex(ValueError, "unexpected MCP tool name"):
            tool_to_method_name("bad_prefix_get_topics")

    def test_dispatch_tool_unknown_tool_raises(self) -> None:
        client = self.make_client()

        with self.assertRaises(AttributeError):
            dispatch_tool(client, "cybernative_nonexistent_method", {})

    def test_sanitize_error_message_redacts_api_key(self) -> None:
        result = sanitize_error_message(
            'user_api_key=abc123secretkeyxyz789 something else'
        )
        self.assertNotIn("abc123secretkeyxyz789", result)
        self.assertIn("[redacted]", result)

    def test_sanitize_error_message_redacts_user_api_key_colon(self) -> None:
        result = sanitize_error_message(
            "User-Api-Key: my-super-secret-token-12345 header invalid"
        )
        self.assertNotIn("my-super-secret-token-12345", result)
        self.assertIn("[redacted]", result)

    def test_sanitize_error_message_passes_clean_message(self) -> None:
        result = sanitize_error_message("Connection refused: timeout after 30s")
        self.assertEqual(result, "Connection refused: timeout after 30s")

    def test_load_mcp_tool_catalog_returns_dict(self) -> None:
        catalog = load_mcp_tool_catalog()
        self.assertIn("tools", catalog)
        self.assertIsInstance(catalog["tools"], list)
        self.assertGreater(len(catalog["tools"]), 0)

    def make_client(self) -> CyberNativeClient:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            return CyberNativeClient(credentials_file=str(path), max_retries=0)


class SanitizeErrorMessageTest(unittest.TestCase):
    def test_redacts_user_api_key_pattern(self) -> None:
        message = "Failed with user_api_key=abc123secretkey on request"
        result = sanitize_error_message(message)
        self.assertNotIn("abc123secretkey", result)
        self.assertIn("[redacted]", result)

    def test_redacts_user_api_key_with_dashes(self) -> None:
        message = 'user-api-key: sk-1234567890abcdef and something else'
        result = sanitize_error_message(message)
        self.assertNotIn("sk-1234567890abcdef", result)
        self.assertIn("[redacted]", result)

    def test_redacts_hex_token_like_strings(self) -> None:
        message = "The key a1b2c3d4e5f6a7b8c9d0 was rejected"
        result = sanitize_error_message(message)
        self.assertNotIn("a1b2c3d4e5f6a7b8c9d0", result)
        self.assertIn("[redacted]", result)

    def test_clean_message_passes_through_unchanged(self) -> None:
        message = "Request failed with HTTP 403: Forbidden"
        result = sanitize_error_message(message)
        self.assertEqual(result, "Request failed with HTTP 403: Forbidden")

    def test_multiple_secrets_all_redacted(self) -> None:
        message = "user_api_key=key1 and also a1b2c3d4e5f6a7b8c9d0 leaked"
        result = sanitize_error_message(message)
        self.assertNotIn("key1", result.split("[redacted]")[0] if "[redacted]" in result else "key1")
        self.assertNotIn("a1b2c3d4e5f6a7b8c9d0", result)

    def test_short_token_not_falsely_redacted(self) -> None:
        message = "HTTP 404"
        result = sanitize_error_message(message)
        self.assertEqual(result, "HTTP 404")


if __name__ == "__main__":
    unittest.main()
