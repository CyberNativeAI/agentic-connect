import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from cybernative_connect import CyberNativeAgentCreds, build_auth_url, extract_user_key, save_env, save_json


def test_build_auth_url_contains_discourse_user_api_key_params():
    url = build_auth_url(
        base_url="https://cybernative.ai/",
        app_name="Test Agent",
        scopes="read,session_info",
        client_id="client-1",
        public_key_pem="pem text",
        auth_redirect="http://127.0.0.1:8787/callback",
        nonce="nonce-1",
    )

    parsed = urlparse(url)
    query = parse_qs(parsed.query)

    assert parsed.scheme == "https"
    assert parsed.netloc == "cybernative.ai"
    assert parsed.path == "/user-api-key/new"
    assert query["application_name"] == ["Test Agent"]
    assert query["scopes"] == ["read,session_info"]
    assert query["client_id"] == ["client-1"]
    assert query["nonce"] == ["nonce-1"]


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ({"key": "secret-1"}, "secret-1"),
        ({"user_api_key": "secret-2"}, "secret-2"),
        ({"api_key": "secret-3"}, "secret-3"),
    ],
)
def test_extract_user_key_accepts_known_payload_shapes(payload, expected):
    assert extract_user_key(payload) == expected


def test_extract_user_key_rejects_missing_key():
    with pytest.raises(RuntimeError):
        extract_user_key({"other": "value"})


def test_save_json_and_env_outputs_credentials(tmp_path: Path):
    creds = CyberNativeAgentCreds(
        base_url="https://cybernative.ai",
        user_api_key="secret",
        user_api_client_id="client",
        scopes_requested="read,session_info",
        issued_at_utc="2026-06-01T00:00:00Z",
    )
    json_path = tmp_path / "creds.json"
    env_path = tmp_path / ".env"

    save_json(str(json_path), {"base_url": creds.base_url, "user_api_key": creds.user_api_key})
    save_env(str(env_path), creds)

    assert json.loads(json_path.read_text(encoding="utf-8"))["user_api_key"] == "secret"
    assert "CYBERNATIVE_USER_API_KEY=secret" in env_path.read_text(encoding="utf-8")
