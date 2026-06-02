#!/usr/bin/env python3
"""Local negative-path checks for CYB-101. Run: python tests/run_negative_path_checks.py"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from cybernative_tools import CyberNativeAPIError, CyberNativeClient, CyberNativeConfigurationError


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def expect_config_error(label: str, fn) -> None:
    try:
        fn()
        print(f"FAIL {label}: expected CyberNativeConfigurationError")
    except CyberNativeConfigurationError as exc:
        print(f"OK   {label}")
        print(f"     {exc!r}")
    except Exception as exc:
        print(f"FAIL {label}: got {type(exc).__name__}: {exc}")


def expect_api_error(label: str, fn) -> None:
    try:
        fn()
        print(f"FAIL {label}: expected CyberNativeAPIError")
    except CyberNativeAPIError as exc:
        print(f"OK   {label}")
        print(f"     {exc!r}")
    except Exception as exc:
        print(f"FAIL {label}: got {type(exc).__name__}: {exc}")


def write_creds(tmp: Path, content: str) -> str:
    path = tmp / "creds.json"
    path.write_text(content, encoding="utf-8")
    return str(path)


def test_credentials() -> None:
    section("Credentials / configuration")
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        expect_config_error(
            "missing file",
            lambda: CyberNativeClient(credentials_file=str(tmp / "missing.json"), max_retries=0),
        )

        path = write_creds(tmp, "{not valid json")
        expect_config_error(
            "malformed JSON",
            lambda: CyberNativeClient(credentials_file=path, max_retries=0),
        )

        path = write_creds(
            tmp,
            json.dumps({"base_url": "https://cybernative.ai", "user_api_key": "k"}),
        )
        expect_config_error(
            "missing user_api_client_id",
            lambda: CyberNativeClient(credentials_file=path, max_retries=0),
        )

        path = write_creds(
            tmp,
            json.dumps(
                {
                    "base_url": "https://cybernative.ai",
                    "user_api_key": "<user_api_key>",
                    "user_api_client_id": "cid",
                }
            ),
        )
        expect_config_error(
            "placeholder fields",
            lambda: CyberNativeClient(credentials_file=path, max_retries=0),
        )

        path = write_creds(
            tmp,
            json.dumps(
                {
                    "base_url": "ftp://evil.example",
                    "user_api_key": "k",
                    "user_api_client_id": "cid",
                }
            ),
        )
        expect_config_error(
            "invalid base_url scheme",
            lambda: CyberNativeClient(credentials_file=path, max_retries=0),
        )


def test_network_and_api() -> None:
    section("Network / API errors (mocked or local stub)")

    with tempfile.TemporaryDirectory() as tmpdir:
        creds = {
            "base_url": "http://127.0.0.1:9",  # likely closed port
            "user_api_key": "test-key",
            "user_api_client_id": "test-client",
        }
        path = Path(tmpdir) / "creds.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        client = CyberNativeClient(credentials_file=str(path), timeout=1, max_retries=0)
        expect_api_error("unreachable host", lambda: client.get_latest_topics(limit=1))

    with tempfile.TemporaryDirectory() as tmpdir:
        creds = {
            "base_url": "https://cybernative.ai",
            "user_api_key": "invalid-key-on-purpose",
            "user_api_client_id": "invalid-client-on-purpose",
        }
        path = Path(tmpdir) / "creds.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        client = CyberNativeClient(credentials_file=str(path), timeout=10, max_retries=0)
        expect_api_error("invalid API credentials (live)", lambda: client.get_latest_topics(limit=1))

    class HtmlHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<html>not json</html>")

        def log_message(self, *_args, **_kwargs) -> None:
            return

    httpd = HTTPServer(("127.0.0.1", 0), HtmlHandler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            creds = {
                "base_url": f"http://127.0.0.1:{port}",
                "user_api_key": "k",
                "user_api_client_id": "c",
            }
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            client = CyberNativeClient(credentials_file=str(path), max_retries=0)
            expect_api_error("non-JSON 200 response", lambda: client.get_latest_topics(limit=1))
    finally:
        httpd.shutdown()

    with tempfile.TemporaryDirectory() as tmpdir:
        creds = {
            "base_url": "https://cybernative.ai",
            "user_api_key": "k",
            "user_api_client_id": "c",
        }
        path = Path(tmpdir) / "creds.json"
        path.write_text(json.dumps(creds), encoding="utf-8")
        client = CyberNativeClient(credentials_file=str(path), max_retries=0)

        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 429
        mock_response.headers = {}
        mock_response.json.side_effect = ValueError("no json")
        mock_response.text = "rate limited"
        mock_response.reason = "Too Many Requests"

        with patch("cybernative_tools.requests.request", return_value=mock_response):
            expect_api_error("HTTP 429 after retries", lambda: client.get_latest_topics(limit=1))


def test_connector_cli() -> None:
    section("Connector CLI")
    py = sys.executable
    connect = str(ROOT / "cybernative_connect.py")

    def run_cli(args: list[str], timeout: int = 5) -> tuple[int, str, str]:
        proc = subprocess.run(
            [py, connect, *args],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        return proc.returncode, combined[:800], combined

    code, out, _ = run_cli(["--help"])
    print(f"OK   --help exit={code}")
    print(f"     first line: {out.splitlines()[0] if out.splitlines() else '(empty)'}")

    code, out, _ = run_cli(["--not-a-real-flag"], timeout=3)
    if code != 0 and "unrecognized" in out.lower() or "error" in out.lower():
        print(f"OK   invalid flag exit={code}")
        print(f"     {out.strip()[:200]}")
    else:
        print(f"WARN invalid flag exit={code}: {out[:200]}")

    # Occupied port: start server then run connector with same port, short timeout
    class QuietHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.end_headers()

        def log_message(self, *_args, **_kwargs) -> None:
            return

    httpd = HTTPServer(("127.0.0.1", 8787), QuietHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        code, out, _ = run_cli(["--port", "8787", "--timeout", "2"], timeout=8)
        if code != 0 and "port" in out.lower():
            print(f"OK   occupied port exit={code}")
            print(f"     {out.strip()[:300]}")
        else:
            print(f"WARN occupied port exit={code}: {out[:300]}")
    finally:
        httpd.shutdown()

    code, out, _ = run_cli(
        ["--path", "/weird-callback-path", "--timeout", "1", "--no-example"],
        timeout=6,
    )
    if "weird-callback-path" in out or "/weird-callback-path" in out:
        print("OK   unusual callback path accepted in auth URL")
        print(f"     listening line contains custom path")
    else:
        print(f"WARN unusual path output: {out[:300]}")


def main() -> int:
    print("CYB-101 negative-path checks")
    test_credentials()
    test_network_and_api()
    test_connector_cli()
    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
