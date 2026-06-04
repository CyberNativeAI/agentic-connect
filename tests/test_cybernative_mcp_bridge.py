import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import cybernative_mcp_server
from cybernative_mcp_bridge import (
    READ_ONLY_TOOL_NAMES,
    dispatch_tool,
    mcp_tool_specs,
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


if __name__ == "__main__":
    unittest.main()
