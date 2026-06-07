#!/usr/bin/env python3
"""CYB-999402: No-credential CLI smoke check for --probe-public.

Runs cybernative_connect.py --probe-public against a local stub /latest.json
(no OAuth, vault secrets, or external credentials required).

Usage: python tests/run_probe_public_smoke.py
"""

from __future__ import annotations

import json
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


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
                        {"title": "Stub topic A"},
                        {"title": "Stub topic B"},
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


def main() -> int:
    httpd = HTTPServer(("127.0.0.1", 0), LatestJsonHandler)
    port = httpd.server_address[1]
    base_url = f"http://127.0.0.1:{port}"
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        proc = subprocess.run(
            [
                sys.executable,
                str(ROOT / "cybernative_connect.py"),
                "--probe-public",
                "--base-url",
                base_url,
                "--limit",
                "2",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=15,
        )
        combined = (proc.stdout or "") + (proc.stderr or "")
        print(combined, end="")
        if proc.returncode != 0:
            print(f"FAIL: exit {proc.returncode}", file=sys.stderr)
            return proc.returncode
        if "PROBE OK" not in combined:
            print("FAIL: expected PROBE OK in output", file=sys.stderr)
            return 1
        if "Stub topic A" not in combined:
            print("FAIL: expected stub topic titles in output", file=sys.stderr)
            return 1
        print("OK: --probe-public CLI smoke passed (local stub, no credentials)")
        return 0
    finally:
        httpd.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
