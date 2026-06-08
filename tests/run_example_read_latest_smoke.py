#!/usr/bin/env python3
"""CYB-999602: HTTP stub smoke test for example_read_latest.

Runs example_read_latest against a local stub /latest.json (no OAuth,
vault secrets, Discourse API, or external credentials required).

Usage: python tests/run_example_read_latest_smoke.py
"""

from __future__ import annotations

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import cybernative_connect as connect  # noqa: E402


class LatestJsonHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path != "/latest.json":
            self.send_response(404)
            self.end_headers()
            return
        body = json.dumps(
            {
                "topic_list": {
                    "topics": [
                        {"title": "Stub topic A", "slug": "stub-a", "id": 1},
                        {"title": "Stub topic B", "slug": "stub-b", "id": 2},
                        {"title": "Stub topic C", "slug": "stub-c", "id": 3},
                    ]
                }
            }
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args, **_kwargs) -> None:
        return


def _captured_output(func, *args, **kwargs):
    buf = StringIO()
    try:
        _real_print = print
        import builtins

        def _patched_print(*pa, **pk):
            kwargs_inner = dict(pk)
            kwargs_inner.setdefault("file", buf)
            kwargs_inner.setdefault("flush", False)
            return _real_print(*pa, **kwargs_inner)

        builtins.print = _patched_print
        result = func(*args, **kwargs)
        return result, buf.getvalue()
    finally:
        builtins.print = _real_print


def main() -> int:
    httpd = HTTPServer(("127.0.0.1", 0), LatestJsonHandler)
    port = httpd.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()

    try:
        creds = connect.CyberNativeAgentCreds(
            base_url=base_url,
            user_api_key="test-key",
            user_api_client_id="test-client",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )

        count, output = _captured_output(connect.example_read_latest, creds, limit=2)

        if count != 3:
            print(f"FAIL: expected topic count 3, got {count}", file=sys.stderr)
            return 1
        if "Stub topic A" not in output:
            print("FAIL: expected 'Stub topic A' in output", file=sys.stderr)
            return 1
        if "Stub topic B" not in output:
            print("FAIL: expected 'Stub topic B' in output", file=sys.stderr)
            return 1

        print("OK: example_read_latest smoke passed (local HTTP stub)")
        return 0
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
