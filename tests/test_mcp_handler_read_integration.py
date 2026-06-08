"""CYB-999584: Integration tests for MCP read tool handlers against local HTTP stubs.

Tests the 3 most-used MCP tool handlers (get_latest_topics, read_topic, search)
through the CyberNativeClient -> dispatch_tool bridge layer, using local
HTTPServer stubs that mock Discourse API responses.
"""

from __future__ import annotations

import json
import re
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from cybernative_mcp_bridge import dispatch_tool
from cybernative_tools import CyberNativeClient


class DiscourseStubHandler(BaseHTTPRequestHandler):
    """Multi-route handler that mimics key Discourse API endpoints."""

    latest_json_response = None
    topic_responses = {}
    search_response = None

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/latest.json" and self.latest_json_response is not None:
            self._send_json(200, self.latest_json_response)
        elif path == "/search.json" and self.search_response is not None:
            self._send_json(200, self.search_response)
        elif (m := re.match(r"^/t/(\d+)\.json$", path)):
            topic_id = int(m.group(1))
            data = self.topic_responses.get(topic_id)
            if data is not None:
                self._send_json(200, data)
            else:
                self._send_json(404, {"errors": ["Not found"]})
        else:
            self.send_response(404)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"errors": ["Not found"]}).encode())

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs) -> None:
        return


class StubServer:
    """Context-managed local HTTPServer bound to an OS-assigned port."""

    def __init__(self, handler_class):
        self.httpd = HTTPServer(("127.0.0.1", 0), handler_class)
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


class GetLatestTopicsIntegrationTest(unittest.TestCase):
    def test_dispatch_get_latest_topics_returns_topic_list(self) -> None:
        DiscourseStubHandler.latest_json_response = {
            "topic_list": {
                "topics": [
                    {"id": 1, "title": "Welcome to Discourse", "slug": "welcome-to-discourse"},
                    {"id": 2, "title": "Agent Collaboration Tips", "slug": "agent-collaboration-tips"},
                    {"id": 3, "title": "MCP Integration Guide", "slug": "mcp-integration-guide"},
                    {"id": 4, "title": "Security Best Practices", "slug": "security-best-practices"},
                    {"id": 5, "title": "Community Showcase", "slug": "community-showcase"},
                ]
            }
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 3})

        self.assertEqual(len(result), 3)
        self.assertEqual(result[0]["title"], "Welcome to Discourse")
        self.assertEqual(result[1]["id"], 2)
        self.assertEqual(result[2]["slug"], "mcp-integration-guide")

    def test_dispatch_get_latest_topics_default_limit(self) -> None:
        DiscourseStubHandler.latest_json_response = {
            "topic_list": {
                "topics": [
                    {"id": 1, "title": "Topic A"},
                    {"id": 2, "title": "Topic B"},
                ]
            }
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_get_latest_topics", {})

        self.assertEqual(len(result), 2)

    def test_dispatch_get_latest_topics_empty_result(self) -> None:
        DiscourseStubHandler.latest_json_response = {"topic_list": {"topics": []}}

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})

        self.assertEqual(result, [])


class ReadTopicIntegrationTest(unittest.TestCase):
    def test_dispatch_read_topic_returns_full_topic(self) -> None:
        DiscourseStubHandler.topic_responses = {
            42: {
                "id": 42,
                "title": "How to build MCP servers",
                "post_stream": {
                    "posts": [
                        {
                            "id": 100,
                            "username": "alice",
                            "cooked": "<p>Here is a guide on building MCP servers.</p>",
                        },
                        {
                            "id": 101,
                            "username": "bob",
                            "cooked": "<p>Great write-up! One addition: handle errors gracefully.</p>",
                        },
                    ]
                },
            }
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_read_topic", {"topic_id": 42})

        self.assertEqual(result["id"], 42)
        self.assertEqual(result["title"], "How to build MCP servers")
        self.assertEqual(len(result["post_stream"]["posts"]), 2)
        self.assertEqual(result["post_stream"]["posts"][0]["username"], "alice")

    def test_dispatch_read_topic_large_id(self) -> None:
        DiscourseStubHandler.topic_responses = {
            99999: {"id": 99999, "title": "Buried topic", "post_stream": {"posts": []}}
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_read_topic", {"topic_id": 99999})

        self.assertEqual(result["id"], 99999)
        self.assertEqual(result["title"], "Buried topic")


class SearchIntegrationTest(unittest.TestCase):
    def test_dispatch_search_returns_results(self) -> None:
        DiscourseStubHandler.search_response = {
            "posts": [{"id": 200, "blurb": "MCP is a protocol for AI agent integration"}],
            "topics": [
                {"id": 10, "title": "MCP Server Setup"},
                {"id": 11, "title": "Agent Communication Patterns"},
            ],
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_search", {"query": "MCP server"})

        self.assertIn("posts", result)
        self.assertEqual(len(result["topics"]), 2)
        self.assertIn("MCP", result["posts"][0]["blurb"])

    def test_dispatch_search_no_results(self) -> None:
        DiscourseStubHandler.search_response = {"posts": [], "topics": []}

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)
            result = dispatch_tool(client, "cybernative_search", {"query": "nonexistentxyz123"})

        self.assertEqual(result["topics"], [])
        self.assertEqual(result["posts"], [])


class MultiToolIntegrationTest(unittest.TestCase):
    """Exercise multiple tools against the same stub server to verify state isolation."""

    def test_multiple_tools_against_same_server(self) -> None:
        DiscourseStubHandler.latest_json_response = {
            "topic_list": {"topics": [{"id": 1, "title": "Latest"}]}
        }
        DiscourseStubHandler.topic_responses = {
            1: {"id": 1, "title": "Latest", "post_stream": {"posts": [{"id": 1, "username": "admin"}]}}
        }
        DiscourseStubHandler.search_response = {
            "topics": [{"id": 1, "title": "Latest"}],
            "posts": [],
        }

        with StubServer(DiscourseStubHandler) as server:
            client = _make_client(server.base_url)

            topics = dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertEqual(len(topics), 1)

            topic = dispatch_tool(client, "cybernative_read_topic", {"topic_id": 1})
            self.assertEqual(topic["post_stream"]["posts"][0]["username"], "admin")

            search = dispatch_tool(client, "cybernative_search", {"query": "MCP"})
            self.assertEqual(len(search["topics"]), 1)

        DiscourseStubHandler.latest_json_response = None
        DiscourseStubHandler.topic_responses = {}
        DiscourseStubHandler.search_response = None


if __name__ == "__main__":
    unittest.main()
