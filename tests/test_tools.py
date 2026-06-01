import json

from cybernative_tools import CyberNativeClient


def test_client_loads_json_credentials(tmp_path):
    creds_path = tmp_path / "creds.json"
    creds_path.write_text(
        json.dumps(
            {
                "base_url": "https://cybernative.ai/",
                "user_api_key": "secret",
                "user_api_client_id": "client",
            }
        ),
        encoding="utf-8",
    )

    client = CyberNativeClient(credentials_file=str(creds_path))

    assert client.base_url == "https://cybernative.ai"
    assert client.headers["User-Api-Key"] == "secret"
    assert client.headers["User-Api-Client-Id"] == "client"


def test_client_loads_env_credentials(monkeypatch):
    monkeypatch.setenv("CYBERNATIVE_BASE_URL", "https://cybernative.ai")
    monkeypatch.setenv("CYBERNATIVE_USER_API_KEY", "secret")
    monkeypatch.setenv("CYBERNATIVE_USER_API_CLIENT_ID", "client")

    client = CyberNativeClient(credentials_file=None)

    assert client.base_url == "https://cybernative.ai"
    assert client.headers["User-Api-Key"] == "secret"
