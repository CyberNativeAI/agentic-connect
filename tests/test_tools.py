import json

import pytest

import cybernative_tools
from cybernative_tools import DEFAULT_USER_AGENT, CyberNativeClient


def _make_client(tmp_path):
    creds_path = tmp_path / "creds.json"
    creds_path.write_text(
        json.dumps(
            {
                "base_url": "https://cybernative.ai",
                "user_api_key": "secret",
                "user_api_client_id": "client",
            }
        ),
        encoding="utf-8",
    )
    return CyberNativeClient(credentials_file=str(creds_path), retry_backoff=0)


class _FakeResponse:
    def __init__(self, status_code=200, json_data=None, headers=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.headers = headers or {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests_http_error(self.status_code)


def requests_http_error(status_code):
    import requests

    err = requests.HTTPError(f"HTTP {status_code}")
    return err


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


def test_client_sends_descriptive_user_agent(tmp_path):
    client = _make_client(tmp_path)
    assert client.headers["User-Agent"] == DEFAULT_USER_AGENT
    assert "Python-urllib" not in client.headers["User-Agent"]


def test_request_retries_on_429_then_succeeds(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []
    sleeps = []
    monkeypatch.setattr(cybernative_tools.time, "sleep", lambda s: sleeps.append(s))

    responses = [
        _FakeResponse(429, headers={"Retry-After": "2"}),
        _FakeResponse(200, {"ok": True}),
    ]

    def fake_request(method, url, **kwargs):
        calls.append((method, url))
        return responses[len(calls) - 1]

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    resp = client._request("GET", "/latest.json")

    assert resp.json() == {"ok": True}
    assert len(calls) == 2
    assert sleeps == [2.0]  # honored the Retry-After header


def test_request_gives_up_after_max_retries(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    client.max_retries = 1
    monkeypatch.setattr(cybernative_tools.time, "sleep", lambda s: None)

    def always_429(method, url, **kwargs):
        return _FakeResponse(429)

    monkeypatch.setattr(cybernative_tools.requests, "request", always_429)

    with pytest.raises(Exception):
        client._request("GET", "/latest.json")


def test_get_notifications_and_whoami(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    payloads = {
        "/notifications.json": {"notifications": [{"id": 1}]},
        "/session/current.json": {"current_user": {"username": "tester"}},
    }

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        return _FakeResponse(200, payloads[path])

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    assert client.list_notifications() == [{"id": 1}]
    assert client.get_notifications() == [{"id": 1}]
    assert client.whoami() == {"username": "tester"}
