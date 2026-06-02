import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cybernative_tools import CyberNativeClient


class CyberNativeClientTest(unittest.TestCase):
    def make_client(self) -> CyberNativeClient:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            return CyberNativeClient(credentials_file=str(path), max_retries=0)

    def test_get_topic_url_quotes_path_segments(self) -> None:
        client = self.make_client()

        url = client.get_topic_url({"slug": "hello world/a", "id": "12/34"})

        self.assertEqual(url, "https://cybernative.ai/t/hello%20world%2Fa/12%2F34")

    @patch.object(CyberNativeClient, "_request")
    def test_read_topic_quotes_topic_id(self, request) -> None:
        client = self.make_client()

        client.read_topic("12/34")

        request.assert_called_once_with("GET", "/t/12%2F34.json")

    @patch.object(CyberNativeClient, "_request")
    def test_get_user_quotes_username(self, request) -> None:
        client = self.make_client()

        client.get_user("alice/bob")

        request.assert_called_once_with("GET", "/u/alice%2Fbob.json")

    @patch.object(CyberNativeClient, "_request")
    def test_list_notifications_uses_notifications_endpoint(self, request) -> None:
        client = self.make_client()

        client.list_notifications()

        request.assert_called_once_with("GET", "/notifications.json")

    @patch.object(CyberNativeClient, "_request")
    def test_mark_notification_read_sends_notification_id(self, request) -> None:
        client = self.make_client()

        client.mark_notification_read(42)

        request.assert_called_once_with(
            "PUT",
            "/notifications/mark-read.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"id": 42},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_list_bookmarks_uses_bookmarks_endpoint(self, request) -> None:
        client = self.make_client()

        client.list_bookmarks()

        request.assert_called_once_with("GET", "/bookmarks.json")

    @patch.object(CyberNativeClient, "_request")
    def test_bookmark_post_posts_bookmarkable_payload(self, request) -> None:
        client = self.make_client()

        client.bookmark_post(77)

        request.assert_called_once_with(
            "POST",
            "/bookmarks.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"bookmarkable_id": 77, "bookmarkable_type": "Post"},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_bookmark_topic_uses_topic_bookmark_endpoint(self, request) -> None:
        client = self.make_client()

        client.bookmark_topic(88)

        request.assert_called_once_with("PUT", "/t/88/bookmark.json")

    @patch.object(CyberNativeClient, "_request")
    def test_like_post_posts_like_action(self, request) -> None:
        client = self.make_client()

        client.like_post(99)

        request.assert_called_once_with(
            "POST",
            "/post_actions.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"id": 99, "post_action_type_id": 2},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_unlike_post_deletes_like_action(self, request) -> None:
        client = self.make_client()

        client.unlike_post(100)

        request.assert_called_once_with("DELETE", "/post_actions/100", params={"post_action_type_id": 2})

    @patch.object(CyberNativeClient, "search")
    def test_search_topics_returns_limited_topic_list(self, search) -> None:
        client = self.make_client()
        search.return_value = {
            "topics": [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"},
                {"id": 3, "title": "Third"},
            ],
            "posts": [{"id": 10}],
        }

        topics = client.search_topics("status:unsolved agent", limit=2)

        search.assert_called_once_with("status:unsolved agent")
        self.assertEqual(
            topics,
            [
                {"id": 1, "title": "First"},
                {"id": 2, "title": "Second"},
            ],
        )


if __name__ == "__main__":
    unittest.main()
