import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cybernative_mcp_bridge import dispatch_tool
from cybernative_tools import CyberNativeClient, CyberNativeAPIError


def _make_client(**kwargs):
    creds = {
        "base_url": "https://cybernative.ai/",
        "user_api_key": "test-api-key",
        "user_api_client_id": "test-client-id",
    }
    td = tempfile.TemporaryDirectory()
    path = Path(td.name) / "creds.json"
    path.write_text(json.dumps(creds), encoding="utf-8")
    client = CyberNativeClient(
        credentials_file=str(path), max_retries=kwargs.pop("max_retries", 0), **kwargs
    )
    client._tempdir = td
    return client


def _mock_response(status_code=200, json_data=None, ok=True, headers=None):
    resp = Mock()
    resp.status_code = status_code
    resp.ok = ok
    resp.headers = headers or {}
    resp.reason = "OK" if ok else "Error"
    resp.raise_for_status = Mock()
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("not json")
    resp.text = json.dumps(json_data) if json_data is not None else "not json"
    return resp


class McpIntegrationHappyPathTest(unittest.TestCase):
    """Integration tests for the 3 most-used MCP tool handlers."""

    @patch("cybernative_tools.requests.request")
    def test_dispatch_get_latest_topics_integration(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={
                "topic_list": {
                    "topics": [
                        {"id": 1, "title": "Welcome", "slug": "welcome"},
                        {"id": 2, "title": "Announcements", "slug": "announcements"},
                        {"id": 3, "title": "General Discussion", "slug": "general-discussion"},
                    ]
                }
            }
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 2})

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[0]["title"], "Welcome")
        self.assertEqual(result[1]["id"], 2)
        mock_request.assert_called_once()
        self.assertEqual(mock_request.call_args[0][1], "https://cybernative.ai/latest.json")

    @patch("cybernative_tools.requests.request")
    def test_dispatch_get_latest_topics_with_default_limit(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={
                "topic_list": {
                    "topics": [
                        {"id": i, "title": f"Topic {i}", "slug": f"topic-{i}"}
                        for i in range(1, 16)
                    ]
                }
            }
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_get_latest_topics", {})

        self.assertEqual(len(result), 10)
        self.assertEqual(result[0]["id"], 1)
        self.assertEqual(result[9]["id"], 10)

    @patch("cybernative_tools.requests.request")
    def test_dispatch_search_topics_integration(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={
                "topics": [
                    {"id": 42, "title": "How to use MCP?", "slug": "how-to-use-mcp"},
                    {"id": 99, "title": "Agent integration guide", "slug": "agent-integration"},
                ],
                "posts": [{"id": 100}, {"id": 101}],
                "grouped_search_result": {"more_full_page_results": False},
            }
        )
        client = _make_client()

        result = dispatch_tool(
            client, "cybernative_search_topics", {"query": "MCP integration", "limit": 5}
        )

        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], 42)
        self.assertEqual(result[0]["title"], "How to use MCP?")
        self.assertEqual(result[1]["id"], 99)
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertIn("params", call_args.kwargs)
        self.assertEqual(call_args.kwargs["params"]["q"], "MCP integration")

    @patch("cybernative_tools.requests.request")
    def test_dispatch_search_topics_with_default_limit(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={
                "topics": [{"id": 1, "title": "Hello", "slug": "hello"}],
                "posts": [],
            }
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_search_topics", {"query": "hello"})

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Hello")

    @patch("cybernative_tools.requests.request")
    def test_dispatch_read_topic_integration(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={
                "id": 777,
                "title": "MCP server setup guide",
                "post_stream": {
                    "posts": [
                        {
                            "id": 1001,
                            "username": "admin",
                            "cooked": "<p>Here is how to set up the MCP server...</p>",
                            "created_at": "2026-06-01T12:00:00Z",
                        },
                        {
                            "id": 1002,
                            "username": "developer",
                            "cooked": "<p>Thanks, this helped!</p>",
                            "created_at": "2026-06-01T12:30:00Z",
                        },
                    ]
                },
            }
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_read_topic", {"topic_id": 777})

        self.assertEqual(result["id"], 777)
        self.assertEqual(result["title"], "MCP server setup guide")
        self.assertEqual(len(result["post_stream"]["posts"]), 2)
        self.assertEqual(result["post_stream"]["posts"][0]["username"], "admin")
        mock_request.assert_called_once()
        self.assertEqual(mock_request.call_args[0][1], "https://cybernative.ai/t/777.json")


class McpErrorHandlingTest(unittest.TestCase):
    """Error-handling integration tests for MCP tool dispatch."""

    @patch("cybernative_tools.requests.request")
    def test_timeout_raises_api_error(self, mock_request):
        from requests.exceptions import ReadTimeout
        mock_request.side_effect = ReadTimeout("Connection timed out")
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})

        self.assertIn("failed before receiving a response", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_connection_error_raises_api_error(self, mock_request):
        from requests.exceptions import ConnectionError as ReqConnectionError
        mock_request.side_effect = ReqConnectionError("Connection refused")
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_read_topic", {"topic_id": 1})

        self.assertIn("failed before receiving a response", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_auth_failure_403_raises_api_error(self, mock_request):
        mock_request.return_value = _mock_response(
            status_code=403,
            ok=False,
            json_data={"errors": ["You are not permitted to view the requested resource."]},
        )
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_search_topics", {"query": "secret"})

        self.assertIn("403", str(ctx.exception))
        self.assertIn("not permitted", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_server_error_500_raises_api_error(self, mock_request):
        mock_request.return_value = _mock_response(
            status_code=500,
            ok=False,
            json_data={"error": "Internal Server Error"},
        )
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_get_latest_topics", {})

        self.assertIn("500", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_malformed_json_response_raises_api_error(self, mock_request):
        mock_request.return_value = Mock()
        mock_request.return_value.ok = True
        mock_request.return_value.status_code = 200
        mock_request.return_value.headers = {}
        mock_request.return_value.raise_for_status = Mock()
        mock_request.return_value.json.side_effect = ValueError("not json")
        mock_request.return_value.text = "not json"
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_read_topic", {"topic_id": 1})

        self.assertIn("non-JSON", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_unexpected_response_structure(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={"unexpected": "structure", "no_topics_here": True}
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_get_latest_topics", {})

        self.assertEqual(result, [])

    @patch("cybernative_tools.requests.request")
    def test_429_rate_limit_exhausted_raises_api_error(self, mock_request):
        mock_request.return_value = _mock_response(
            status_code=429, ok=False, json_data={"errors": ["Too many requests"]}
        )
        client = _make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            dispatch_tool(client, "cybernative_get_latest_topics", {})

        self.assertIn("429", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_search_topics_empty_results(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={"topics": [], "posts": []}
        )
        client = _make_client()

        result = dispatch_tool(client, "cybernative_search_topics", {"query": "nonexistent"})

        self.assertEqual(result, [])


class McpIntegrationReadOnlyTest(unittest.TestCase):
    """Read-only mode integration tests."""

    @patch("cybernative_tools.requests.request")
    def test_get_latest_topics_in_read_only_mode(self, mock_request):
        mock_request.return_value = _mock_response(
            json_data={"topic_list": {"topics": [{"id": 1, "title": "Test", "slug": "test"}]}}
        )
        client = _make_client()

        result = dispatch_tool(
            client, "cybernative_get_latest_topics", {"limit": 3}, read_only=True
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["id"], 1)

    def test_write_tool_rejected_in_read_only_mode(self):
        client = _make_client()

        with self.assertRaisesRegex(ValueError, "read-only mode"):
            dispatch_tool(client, "cybernative_create_topic", {}, read_only=True)


if __name__ == "__main__":
    unittest.main()
