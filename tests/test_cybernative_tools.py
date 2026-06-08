import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from cybernative_tools import CyberNativeClient, CyberNativeAPIError
import cybernative_tools as ct


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
    def test_mark_notification_read_none_sends_empty_payload(self, request) -> None:
        client = self.make_client()

        client.mark_notification_read(None)

        request.assert_called_once_with(
            "PUT",
            "/notifications/mark-read.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={},
        )

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
    def test_mark_notification_read_all_when_id_is_none(self, request) -> None:
        client = self.make_client()

        client.mark_notification_read(None)

        request.assert_called_once_with(
            "PUT",
            "/notifications/mark-read.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_list_notifications_returns_full_payload(self, request) -> None:
        expected = {
            "notifications": [{"id": 1, "notification_type": "mentioned"}],
            "total_rows_notifications": 1,
            "seen_notification_id": 0,
        }
        request.return_value = expected
        client = self.make_client()

        result = client.list_notifications()

        self.assertEqual(result, expected)

    @patch.object(CyberNativeClient, "_request")
    def test_list_notifications_raises_on_api_error(self, request) -> None:
        from cybernative_tools import CyberNativeAPIError

        request.side_effect = CyberNativeAPIError("GET /notifications.json failed with HTTP 500: boom")
        client = self.make_client()

        with self.assertRaises(CyberNativeAPIError) as ctx:
            client.list_notifications()
        self.assertIn("HTTP 500", str(ctx.exception))

    @patch.object(CyberNativeClient, "_request")
    def test_mark_notification_read_returns_payload(self, request) -> None:
        request.return_value = {"success": "ok"}
        client = self.make_client()

        result = client.mark_notification_read(1)

        self.assertEqual(result, {"success": "ok"})

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

    @patch.object(CyberNativeClient, "_request")
    def test_get_latest_topics_truncates_to_limit(self, request) -> None:
        client = self.make_client()
        request.return_value = {
            "topic_list": {
                "topics": [
                    {"id": 1, "title": "A"},
                    {"id": 2, "title": "B"},
                    {"id": 3, "title": "C"},
                    {"id": 4, "title": "D"},
                    {"id": 5, "title": "E"},
                ]
            }
        }

        topics = client.get_latest_topics(limit=3)

        request.assert_called_once_with("GET", "/latest.json")
        self.assertEqual(len(topics), 3)
        self.assertEqual(topics[0]["title"], "A")

    @patch.object(CyberNativeClient, "_request")
    def test_get_categories_uses_categories_endpoint(self, request) -> None:
        client = self.make_client()
        request.return_value = {"category_list": {"categories": [{"id": 1, "name": "General"}]}}

        cats = client.get_categories()

        request.assert_called_once_with("GET", "/categories.json")
        self.assertEqual(cats, [{"id": 1, "name": "General"}])

    @patch.object(CyberNativeClient, "_request")
    def test_create_topic_posts_to_posts_endpoint(self, request) -> None:
        client = self.make_client()

        client.create_topic("Test Title", "Test content", category_id=31)

        request.assert_called_once_with(
            "POST",
            "/posts.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"title": "Test Title", "raw": "Test content", "category": 31},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_reply_to_topic_posts_to_posts_endpoint(self, request) -> None:
        client = self.make_client()

        client.reply_to_topic(topic_id=123, message="Hello world")

        request.assert_called_once_with(
            "POST",
            "/posts.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={"topic_id": 123, "raw": "Hello world"},
        )

    @patch.object(CyberNativeClient, "_request")
    def test_search_uses_search_endpoint(self, request) -> None:
        client = self.make_client()

        client.search("hello world")

        request.assert_called_once_with("GET", "/search.json", params={"q": "hello world"})

    @patch.object(CyberNativeClient, "_request")
    def test_mark_notification_read_all_sends_empty_payload(self, request) -> None:
        client = self.make_client()

        client.mark_notification_read()

        request.assert_called_once_with(
            "PUT",
            "/notifications/mark-read.json",
            headers={
                "User-Api-Key": "test-api-key",
                "User-Api-Client-Id": "test-client-id",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            json={},
        )

    @patch("cybernative_tools.requests.request")
    def test_request_raises_api_error_on_non_ok(self, mock_request) -> None:
        from cybernative_tools import CyberNativeAPIError

        client = self.make_client()
        mock_response = unittest.mock.MagicMock()
        mock_response.ok = False
        mock_response.status_code = 404
        mock_response.reason = "Not Found"
        mock_response.json.side_effect = ValueError("no json")
        mock_response.text = "not found"
        mock_request.return_value = mock_response

        with self.assertRaises(CyberNativeAPIError) as ctx:
            client._request("GET", "/missing.json")

        self.assertIn("404", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    def test_request_retries_retryable_status_then_succeeds(self, mock_request) -> None:
        client = self.make_client()
        client.max_retries = 1

        fail_response = unittest.mock.MagicMock()
        fail_response.ok = False
        fail_response.status_code = 429
        fail_response.headers = {}
        fail_response.reason = "Too Many Requests"
        fail_response.json.side_effect = ValueError("no json")
        fail_response.text = "rate limited"

        ok_response = unittest.mock.MagicMock()
        ok_response.ok = True
        ok_response.raise_for_status = unittest.mock.MagicMock()
        ok_response.json.return_value = {"topic_list": {"topics": [{"id": 1}]}}

        mock_request.side_effect = [fail_response, ok_response]

        result = client.get_latest_topics(limit=5)

        self.assertEqual(mock_request.call_count, 2)
        self.assertEqual(result, [{"id": 1}])


class RetryBehaviorTest(unittest.TestCase):
    def make_client_with_mock(self, max_retries=2):
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            return CyberNativeClient(credentials_file=str(path), max_retries=max_retries)

    @patch("cybernative_tools.requests.request")
    def test_retries_on_429_then_succeeds(self, mock_request) -> None:
        mock_request.side_effect = [
            Mock(ok=False, status_code=429, headers={"Retry-After": "0"}, json=Mock(return_value={"errors": ["rate limited"]})),
            Mock(ok=True, status_code=200, json=Mock(return_value={"topic_list": {"topics": []}})),
        ]

        client = self.make_client_with_mock(max_retries=2)
        result = client.get_latest_topics()

        self.assertEqual(result, [])
        self.assertEqual(mock_request.call_count, 2)

    @patch("cybernative_tools.requests.request")
    def test_retries_on_502_then_succeeds(self, mock_request) -> None:
        mock_request.side_effect = [
            Mock(ok=False, status_code=502, headers={}, json=Mock(return_value={})),
            Mock(ok=True, status_code=200, json=Mock(return_value={"topic_list": {"topics": []}})),
        ]

        client = self.make_client_with_mock(max_retries=2)
        result = client.get_latest_topics()

        self.assertEqual(result, [])
        self.assertEqual(mock_request.call_count, 2)

    @patch("cybernative_tools.requests.request")
    def test_raises_after_exhausting_retries(self, mock_request) -> None:
        mock_request.return_value = Mock(
            ok=False, status_code=503, headers={}, json=Mock(return_value={})
        )

        client = self.make_client_with_mock(max_retries=1)
        with self.assertRaises(CyberNativeAPIError) as ctx:
            client.get_latest_topics()

        self.assertIn("503", str(ctx.exception))

    @patch("cybernative_tools.requests.request")
    @patch("cybernative_tools.time.sleep")
    def test_exponential_backoff_on_retries(self, mock_sleep, mock_request) -> None:
        mock_request.side_effect = [
            Mock(ok=False, status_code=503, headers={}, json=Mock(return_value={})),
            Mock(ok=False, status_code=503, headers={}, json=Mock(return_value={})),
            Mock(ok=True, status_code=200, json=Mock(return_value={"topic_list": {"topics": []}})),
        ]

        client = self.make_client_with_mock(max_retries=3)
        client.get_latest_topics()

        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)


class SingletonConvenienceTest(unittest.TestCase):
    def setUp(self) -> None:
        ct._default_client = None

    def tearDown(self) -> None:
        ct._default_client = None

    @patch.object(CyberNativeClient, "_request", return_value={"topic_list": {"topics": [{"id": 1, "title": "Test"}]}})
    def test_module_level_get_latest_topics_delegates(self, mock_request) -> None:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            with patch.object(CyberNativeClient, "__init__", return_value=None):
                client = CyberNativeClient()
                client.base_url = "https://cybernative.ai"
                client.headers = {
                    "User-Api-Key": "test-api-key",
                    "User-Api-Client-Id": "test-client-id",
                    "Accept": "application/json",
                }
                client.timeout = 30
                client.max_retries = 0
                mock_request.side_effect = None
                mock_request.return_value = {"topic_list": {"topics": [{"id": 1}]}}
                mock_request.reset_mock()

                with patch.object(CyberNativeClient, "_request", return_value={"topic_list": {"topics": [{"id": 1, "title": "Test"}]}}):
                    client._request = Mock(return_value={"topic_list": {"topics": [{"id": 1, "title": "Test"}]}})
                    ct._default_client = client

                    topics = ct.get_latest_topics(limit=1)

                    self.assertEqual(len(topics), 1)
                    self.assertEqual(topics[0]["title"], "Test")

    @patch.object(CyberNativeClient, "_request", return_value={"id": 1, "title": "Hello"})
    def test_module_level_read_topic_delegates(self, mock_request) -> None:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            with patch.object(CyberNativeClient, "_request", return_value={"id": 1, "title": "Hello"}):
                client = CyberNativeClient(credentials_file=str(path))
                client._request = mock_request
                ct._default_client = client

                result = ct.read_topic(1)

                self.assertEqual(result["title"], "Hello")

    @patch.object(CyberNativeClient, "_request", return_value={"id": 42})
    def test_module_level_search_delegates(self, mock_request) -> None:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            with patch.object(CyberNativeClient, "_request", return_value={"id": 42}):
                client = CyberNativeClient(credentials_file=str(path))
                client._request = mock_request
                ct._default_client = client

                result = ct.search("test query")

                self.assertEqual(result["id"], 42)
                mock_request.assert_called_once_with("GET", "/search.json", params={"q": "test query"})


if __name__ == "__main__":
    unittest.main()

