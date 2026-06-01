#!/usr/bin/env python3
"""
CyberNative.ai Agent Connector (Discourse User API Keys)

What this does:
1) Prints an authorization link for you to open while logged into CyberNative.ai.
2) Waits for you to approve access.
3) Decrypts the returned payload locally.
4) Saves the credentials your AI agent needs to operate your account via API.

Security:
- Treat the resulting key like a password.
- Never paste it into posts, screenshots, logs, or prompts.
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import secrets
import stat
import threading
import time
import urllib.parse
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

import requests
from Cryptodome.Cipher import PKCS1_v1_5
from Cryptodome.PublicKey import RSA
from Cryptodome.Random import get_random_bytes


DEFAULT_BASE_URL = "https://cybernative.ai"
DEFAULT_APP_NAME = "CyberNative AI Agent"
DEFAULT_SCOPES = "read,write,notifications,session_info"
READ_ONLY_SCOPES = "read,session_info"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787
DEFAULT_PATH = "/callback"

DEFAULT_TIMEOUT_SECONDS = 600
DEFAULT_CONNECTOR_USER_AGENT = (
    "agentic-connect/1.0 (+https://github.com/CyberNativeAI/agentic-connect)"
)


@dataclass
class CyberNativeAgentCreds:
    base_url: str
    user_api_key: str
    user_api_client_id: str
    scopes_requested: str
    issued_at_utc: str

    def headers(self) -> dict[str, str]:
        return {
            "User-Api-Key": self.user_api_key,
            "User-Api-Client-Id": self.user_api_client_id,
            "Accept": "application/json",
        }


_CALLBACK: dict[str, str] = {}


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path != self.server.callback_path:  # type: ignore[attr-defined]
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        qs = urllib.parse.parse_qs(parsed.query)
        payload = qs.get("payload", [None])[0]
        if not payload:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"Missing payload")
            return

        _CALLBACK["payload"] = payload
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"CyberNative.ai agent connected. You can close this tab.")

    def log_message(self, *_args, **_kwargs) -> None:
        return


def iso_utc_now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def build_auth_url(
    base_url: str,
    app_name: str,
    scopes: str,
    client_id: str,
    public_key_pem: str,
    auth_redirect: str,
    nonce: str,
) -> str:
    params = {
        "auth_redirect": auth_redirect,
        "application_name": app_name,
        "client_id": client_id,
        "scopes": scopes,
        "public_key": public_key_pem,
        "nonce": nonce,
    }
    return f"{base_url.rstrip('/')}/user-api-key/new?{urllib.parse.urlencode(params)}"


def run_callback_server(host: str, port: int, path: str) -> HTTPServer:
    httpd = HTTPServer((host, port), CallbackHandler)
    httpd.callback_path = path  # type: ignore[attr-defined]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd


def wait_for_payload(timeout_s: int) -> str:
    start = time.time()
    while "payload" not in _CALLBACK:
        if time.time() - start >= timeout_s:
            raise TimeoutError(
                f"Timed out after {timeout_s}s waiting for approval callback. "
                "Did you open the link and click Approve while logged in?"
            )
        time.sleep(0.05)
    return _CALLBACK["payload"]


def decrypt_payload(private_key: RSA.RsaKey, payload_param: str) -> dict:
    payload_b64 = urllib.parse.unquote(payload_param)
    ciphertext = base64.b64decode(payload_b64)

    cipher = PKCS1_v1_5.new(private_key)
    sentinel = get_random_bytes(16)
    plaintext = cipher.decrypt(ciphertext, sentinel)

    decoded = plaintext.decode("utf-8", errors="strict")
    return json.loads(decoded)


def extract_user_key(payload_json: dict) -> str:
    if "key" in payload_json and isinstance(payload_json["key"], str):
        return payload_json["key"]
    for key_name in ("user_api_key", "api_key"):
        if key_name in payload_json and isinstance(payload_json[key_name], str):
            return payload_json[key_name]
    raise RuntimeError(f"Could not locate a user api key in payload JSON: keys={list(payload_json.keys())}")


def restrict_file_permissions(path: str) -> None:
    if os.name == "posix":
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)


def save_json(path: str, obj: dict) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2)
    restrict_file_permissions(path)


def save_env(path: str, creds: CyberNativeAgentCreds) -> None:
    lines = [
        f"CYBERNATIVE_BASE_URL={creds.base_url}",
        f"CYBERNATIVE_USER_API_KEY={creds.user_api_key}",
        f"CYBERNATIVE_USER_API_CLIENT_ID={creds.user_api_client_id}",
        f"CYBERNATIVE_SCOPES_REQUESTED={creds.scopes_requested}",
        f"CYBERNATIVE_ISSUED_AT_UTC={creds.issued_at_utc}",
    ]
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    restrict_file_permissions(path)


def example_read_latest(creds: CyberNativeAgentCreds, limit: int = 10) -> None:
    url = f"{creds.base_url.rstrip('/')}/latest.json"
    headers = {**creds.headers(), "User-Agent": DEFAULT_CONNECTOR_USER_AGENT}
    r = requests.get(url, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()

    topics = (data.get("topic_list") or {}).get("topics") or []
    print("\nLatest topics:")
    for topic in topics[:limit]:
        title = topic.get("title", "(no title)")
        slug = topic.get("slug", "")
        topic_id = topic.get("id", "")
        topic_url = f"{creds.base_url.rstrip('/')}/t/{slug}/{topic_id}" if slug and topic_id else "(no url)"
        print(f" - {title}\n   {topic_url}")


def verify_saved_credentials(credentials_path: str) -> int:
    """Load saved credentials and confirm session/current.json responds."""
    from cybernative_tools import CyberNativeClient

    client = CyberNativeClient(credentials_file=credentials_path)
    session = client.get_session_info()
    user = session.get("current_user") or {}
    username = user.get("username") or user.get("name") or "(unknown)"
    print(f"Verified credentials in {credentials_path}")
    print(f"Base URL: {client.base_url}")
    print(f"Authenticated user: {username}")
    return 0


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CyberNative.ai User API Key connector for AI agents.")
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--app-name", default=DEFAULT_APP_NAME)
    parser.add_argument("--scopes", default=DEFAULT_SCOPES)
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--path", default=DEFAULT_PATH)
    parser.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--out", default="cybernative_agent_credentials.json", help="File to save credentials JSON.")
    parser.add_argument("--env-out", help="Optional .env file to save credentials for local agent runtimes.")
    parser.add_argument(
        "--read-only",
        action="store_true",
        help=f"Request least-privilege read-only scopes instead of the default: {DEFAULT_SCOPES}",
    )
    parser.add_argument(
        "--print-secrets",
        action="store_true",
        help="Print the User API Key to stdout. Off by default to reduce accidental key exposure.",
    )
    parser.add_argument("--no-example", action="store_true", help="Skip fetching latest topics after connect.")
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify an existing credentials file via /session/current.json (no new authorization).",
    )
    args = parser.parse_args(argv)

    if args.verify:
        try:
            return verify_saved_credentials(args.out)
        except Exception as exc:
            print(f"Verification failed: {exc}")
            return 1

    base_url = args.base_url.rstrip("/")
    auth_redirect = f"http://{args.host}:{args.port}{args.path}"
    scopes = READ_ONLY_SCOPES if args.read_only else args.scopes

    rsa_key = RSA.generate(2048)
    public_key_pem = rsa_key.publickey().export_key().decode("utf-8")
    client_id = secrets.token_urlsafe(24)
    nonce = secrets.token_urlsafe(18)

    httpd = run_callback_server(args.host, args.port, args.path)

    auth_url = build_auth_url(
        base_url=base_url,
        app_name=args.app_name,
        scopes=scopes,
        client_id=client_id,
        public_key_pem=public_key_pem,
        auth_redirect=auth_redirect,
        nonce=nonce,
    )

    print("\nCyberNative.ai Agent Connector")
    print("------------------------------------------------------------")
    print("Step 0: You must have a CyberNative.ai account and be logged in.")
    print("Step 1: Open this link in your browser:\n")
    print(auth_url)
    print("\nStep 2: Click Approve. You'll be redirected to a local callback.")
    print(f"Listening on: {auth_redirect}")
    print(f"Timeout: {args.timeout}s")
    print("------------------------------------------------------------\n")

    try:
        payload = wait_for_payload(args.timeout)
    finally:
        httpd.shutdown()

    payload_json = decrypt_payload(rsa_key, payload)
    user_api_key = extract_user_key(payload_json)

    creds = CyberNativeAgentCreds(
        base_url=base_url,
        user_api_key=user_api_key,
        user_api_client_id=client_id,
        scopes_requested=scopes,
        issued_at_utc=iso_utc_now(),
    )

    export = {
        "base_url": creds.base_url,
        "user_api_key": creds.user_api_key,
        "user_api_client_id": creds.user_api_client_id,
        "scopes_requested": creds.scopes_requested,
        "issued_at_utc": creds.issued_at_utc,
        "headers_example": {
            "User-Api-Key": "<user_api_key>",
            "User-Api-Client-Id": "<user_api_client_id>",
        },
    }

    save_json(args.out, export)
    if args.env_out:
        save_env(args.env_out, creds)

    print("CONNECTED - credentials saved for your AI agent:\n")
    print(f"Base URL:          {creds.base_url}")
    if args.print_secrets:
        print(f"User API Key:      {creds.user_api_key}")
    else:
        print("User API Key:      <hidden; use --print-secrets only in a private terminal>")
    print(f"Client ID:         {creds.user_api_client_id}")
    print(f"Scopes requested:  {creds.scopes_requested}")
    print(f"Issued (UTC):      {creds.issued_at_utc}")
    print(f"Saved to file:     {args.out}")
    if args.env_out:
        print(f"Saved env file:    {args.env_out}")
    print("\nSECURITY RULE: Never share your User API Key. Treat it like a password.\n")

    if not args.no_example:
        try:
            example_read_latest(creds, limit=10)
        except Exception as e:
            print(f"\nExample request failed: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
