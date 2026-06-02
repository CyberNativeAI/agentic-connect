import json

import pytest

import cybernative_tools
from cybernative_tools import CyberNativeClient


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
    def __init__(self, status_code=200, json_data=None, text=None):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text if text is not None else (json.dumps(self._json) if self._json else "")
        self.headers = {}

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            import requests

            raise requests.HTTPError(f"HTTP {self.status_code}")


def test_edit_post(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        calls.append((method, path, kwargs.get("json")))
        if method == "PUT" and path == "/posts/42.json":
            return _FakeResponse(200, {"post": {"id": 42, "raw": "updated"}})
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    result = client.edit_post(42, "updated", edit_reason="qa fix")

    assert result["post"]["id"] == 42
    assert calls[0] == (
        "PUT",
        "/posts/42.json",
        {"post": {"raw": "updated", "edit_reason": "qa fix"}},
    )


def test_delete_post(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        calls.append((method, path))
        if method == "DELETE" and path == "/posts/7.json":
            return _FakeResponse(200, text="")
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    assert client.delete_post(7) == {}
    assert calls == [("DELETE", "/posts/7.json")]


def test_remove_bookmark(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        calls.append((method, path))
        if method == "DELETE" and path == "/bookmarks/99.json":
            return _FakeResponse(200, text="")
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    assert client.remove_bookmark(99) == {}
    assert calls == [("DELETE", "/bookmarks/99.json")]


def test_edit_post_permission_error(tmp_path, monkeypatch):
    client = _make_client(tmp_path)

    def fake_request(method, url, **kwargs):
        return _FakeResponse(403, {})

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    with pytest.raises(Exception):
        client.edit_post(1, "nope")
