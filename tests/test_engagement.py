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


def test_bookmark_post_and_list_bookmarks(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        calls.append((method, path, kwargs.get("json")))
        if method == "POST" and path == "/bookmarks.json":
            return _FakeResponse(200, {"id": 99, "bookmarkable_id": 42})
        if method == "GET" and path == "/bookmarks.json":
            return _FakeResponse(200, {"bookmarks": [{"id": 99}]})
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    created = client.bookmark_post(42, name="qa")
    listed = client.list_bookmarks()

    assert created["id"] == 99
    assert listed == [{"id": 99}]
    assert calls[0] == (
        "POST",
        "/bookmarks.json",
        {"bookmarkable_id": 42, "bookmarkable_type": "Post", "name": "qa"},
    )
    assert calls[1][0:2] == ("GET", "/bookmarks.json")


def test_like_and_unlike_post(tmp_path, monkeypatch):
    client = _make_client(tmp_path)
    calls = []

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        calls.append((method, path, kwargs.get("json")))
        if method == "POST" and path == "/post_actions.json":
            return _FakeResponse(200, {"id": 7, "actions_summary": []})
        if method == "DELETE" and path == "/post_actions.json":
            return _FakeResponse(200, text="")
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    liked = client.like_post(7)
    unliked = client.unlike_post(7)

    assert liked["id"] == 7
    assert unliked == {}
    assert calls[0] == ("POST", "/post_actions.json", {"id": 7, "post_action_type_id": 2})
    assert calls[1] == ("DELETE", "/post_actions.json", {"id": 7, "post_action_type_id": 2})


def test_list_notifications(tmp_path, monkeypatch):
    client = _make_client(tmp_path)

    def fake_request(method, url, **kwargs):
        path = url.replace(client.base_url, "")
        if method == "GET" and path == "/notifications.json":
            return _FakeResponse(200, {"notifications": [{"id": 1, "notification_type": 1}]})
        raise AssertionError(f"unexpected {method} {path}")

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    assert client.list_notifications() == [{"id": 1, "notification_type": 1}]
    assert client.get_notifications() == [{"id": 1, "notification_type": 1}]


def test_like_post_duplicate_raises(tmp_path, monkeypatch):
    client = _make_client(tmp_path)

    def fake_request(method, url, **kwargs):
        return _FakeResponse(403, {})

    monkeypatch.setattr(cybernative_tools.requests, "request", fake_request)

    with pytest.raises(Exception):
        client.like_post(1)
