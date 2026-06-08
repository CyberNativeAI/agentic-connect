"""CYB-999584: Error recovery integration tests for MCP tool handlers.

Tests timeout, malformed JSON responses, auth failures, and server errors
through the CyberNativeClient -> dispatch_tool bridge layer.
"""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from cybernative_mcp_bridge import dispatch_tool, sanitize_error_message
from cybernative_tools import CyberNativeAPIError, CyberNativeClient


class ErrorStubHandler(BaseHTTPRequestHandler):
    """Configurable stub that returns errors based on class-level flags."""

    response_status = 200
    response_content_type = "application/json"
    response_body = b"{}"
    slow_response_delay = 0
    read_request_count = 0

    def do_GET(self) -> None:
        ErrorStubHandler.read_request_count += 1
        if ErrorStubHandler.slow_response_delay > 0:
            import time

            time.sleep(ErrorStubHandler.slow_response_delay)
        self.send_response(ErrorStubHandler.response_status)
        self.send_header("Content-Type", ErrorStubHandler.response_content_type)
        self.end_headers()
        self.wfile.write(ErrorStubHandler.response_body)

    def log_message(self, *_args, **_kwargs) -> None:
        return


class ErrorStubServer:
    def __init__(self):
        self.httpd = HTTPServer(("127.0.0.1", 0), ErrorStubHandler)
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


def _make_client(base_url: str, timeout: int = 5) -> CyberNativeClient:
    creds = {
        "base_url": base_url,
        "user_api_key": "test-api-key",
        "user_api_client_id": "test-client-id",
    }
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "creds.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        return CyberNativeClient(credentials_file=str(path), timeout=timeout, max_retries=0)


def _reset_stub() -> None:
    ErrorStubHandler.response_status = 200
    ErrorStubHandler.response_content_type = "application/json"
    ErrorStubHandler.response_body = b"{}"
    ErrorStubHandler.slow_response_delay = 0
    ErrorStubHandler.read_request_count = 0


class MalformedResponseTest(unittest.TestCase):
    def setUp(self):
        _reset_stub()

    def test_html_instead_of_json_raises_api_error(self) -> None:
        ErrorStubHandler.response_status = 200
        ErrorStubHandler.response_content_type = "text/html"
        ErrorStubHandler.response_body = b"<html><body>Welcome to nginx!</body></html>"

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertIn("200", str(ctx.exception))

    def test_empty_response_body_raises(self) -> None:
        ErrorStubHandler.response_status = 200
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = b""

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertIn("200", str(ctx.exception))


class AuthFailureTest(unittest.TestCase):
    def setUp(self):
        _reset_stub()

    def test_http_403_forbidden_raises_api_error(self) -> None:
        ErrorStubHandler.response_status = 403
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"errors": ["You are not permitted to view the requested resource"]}).encode()

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertIn("403", str(ctx.exception))

    def test_http_401_unauthorized_raises_api_error(self) -> None:
        ErrorStubHandler.response_status = 401
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"error": "Invalid API key"}).encode()

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_read_topic", {"topic_id": 1})
            self.assertIn("401", str(ctx.exception))


class ServerErrorTest(unittest.TestCase):
    def setUp(self):
        _reset_stub()

    def test_http_500_internal_server_error_raises(self) -> None:
        ErrorStubHandler.response_status = 500
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"errors": ["Internal server error"]}).encode()

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertIn("500", str(ctx.exception))

    def test_http_502_bad_gateway_raises(self) -> None:
        ErrorStubHandler.response_status = 502
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"error": "Bad Gateway"}).encode()

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_search", {"query": "test"})
            self.assertIn("502", str(ctx.exception))

    def test_http_503_service_unavailable_raises(self) -> None:
        ErrorStubHandler.response_status = 503
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"errors": ["Service unavailable"]}).encode()

        with ErrorStubServer() as server:
            client = _make_client(server.base_url)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_read_topic", {"topic_id": 1})
            self.assertIn("503", str(ctx.exception))


class ConnectionErrorTest(unittest.TestCase):
    def test_unreachable_host_triggers_connection_error(self) -> None:
        creds = {
            "base_url": "http://127.0.0.1:9",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            client = CyberNativeClient(credentials_file=str(path), timeout=1, max_retries=0)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            msg = str(ctx.exception).lower()
            self.assertTrue(
                "connection refused" in msg
                or "timed out" in msg
                or "connect" in msg,
                f"Expected connection error, got: {ctx.exception}",
            )


class RateLimitTest(unittest.TestCase):
    def setUp(self):
        _reset_stub()

    def test_http_429_exhausts_retries_and_raises(self) -> None:
        ErrorStubHandler.response_status = 429
        ErrorStubHandler.response_content_type = "application/json"
        ErrorStubHandler.response_body = json.dumps({"errors": ["Rate limit exceeded"]}).encode()

        with ErrorStubServer() as server:
            creds = {
                "base_url": server.base_url,
                "user_api_key": "test-api-key",
                "user_api_client_id": "test-client-id",
            }
            with tempfile.TemporaryDirectory() as tmpdir:
                path = Path(tmpdir) / "creds.json"
                path.write_text(json.dumps(creds), encoding="utf-8")
                client = CyberNativeClient(credentials_file=str(path), timeout=5, max_retries=0)

            with self.assertRaises(CyberNativeAPIError) as ctx:
                dispatch_tool(client, "cybernative_get_latest_topics", {"limit": 5})
            self.assertIn("429", str(ctx.exception))


class ErrorSanitizationTest(unittest.TestCase):
    """Verify sanitize_error_message works with real-looking error strings from handler paths."""

    def test_api_key_in_response_body_is_redacted(self) -> None:
        message = (
            "Error calling cybernative_get_latest_topics: "
            "HTTP 403 Forbidden with user_api_key=sk-abc123secret"
        )
        result = sanitize_error_message(message)
        self.assertNotIn("sk-abc123secret", result)
        self.assertIn("[redacted]", result)

    def test_all_lowercase_hex_token_passes_through(self) -> None:
        message = "Failed with token a1b2c3d4e5f6a7b8c9d0e1f2 in the response body"
        result = sanitize_error_message(message)
        self.assertEqual(result, message)

    def test_innocuous_error_message_passes_through(self) -> None:
        message = "HTTP 500: Internal Server Error at /latest.json"
        result = sanitize_error_message(message)
        self.assertEqual(result, message)

    def test_timeout_message_is_not_redacted(self) -> None:
        message = "Connection timed out after 30 seconds"
        result = sanitize_error_message(message)
        self.assertEqual(result, "Connection timed out after 30 seconds")

    def test_camelcase_error_name_passes_through(self) -> None:
        message = "Error: InternalServerErrorProcessorFailure in worker thread"
        result = sanitize_error_message(message)
        self.assertEqual(result, message)

    def test_mixed_sensitive_and_innocuous_text(self) -> None:
        message = "user_api_key=secret123 and request to /search.json failed with 503"
        result = sanitize_error_message(message)
        self.assertIn("[redacted]", result)
        self.assertNotIn("secret123", result)
        self.assertIn("/search.json", result)
        self.assertIn("503", result)

    def test_few_digit_slug_passes_through(self) -> None:
        message = "GettingStartedWithCyberNative2025 at http 503"
        result = sanitize_error_message(message)
        self.assertEqual(result, "GettingStartedWithCyberNative2025 at http 503")

    def test_request_id_with_enough_digits_is_redacted(self) -> None:
        message = "CorrelationId ReqX9Y8Z7W6V5U4T3S2R1Qp failed with 500"
        result = sanitize_error_message(message)
        self.assertIn("[redacted]", result)
        self.assertIn("500", result)


if __name__ == "__main__":
    unittest.main()
