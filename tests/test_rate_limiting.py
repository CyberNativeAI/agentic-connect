import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests as requests_lib

from cybernative_tools import CyberNativeAPIError, CyberNativeClient


def _make_429_response():
    resp = MagicMock()
    resp.status_code = 429
    resp.ok = False
    resp.headers = {"Retry-After": "1"}
    resp.json.side_effect = ValueError
    resp.text = "rate limited"
    resp.reason = "Too Many Requests"
    return resp


def _make_500_response():
    resp = MagicMock()
    resp.status_code = 500
    resp.ok = False
    resp.headers = {}
    resp.json.side_effect = ValueError
    resp.text = "internal server error"
    resp.reason = "Internal Server Error"
    return resp


class RateLimitingTest(unittest.TestCase):
    def make_client(self, max_retries: int = 2) -> CyberNativeClient:
        creds = {
            "base_url": "https://cybernative.ai/",
            "user_api_key": "test-api-key",
            "user_api_client_id": "test-client-id",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps(creds), encoding="utf-8")
            return CyberNativeClient(credentials_file=str(path), max_retries=max_retries)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retries_on_429_exactly_max_retries_times(self, mock_request, mock_sleep) -> None:
        ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
        err_resp = _make_429_response()
        err_resp.headers = {}
        mock_request.side_effect = [err_resp, err_resp, ok_resp]

        client = self.make_client(max_retries=2)
        client.get_latest_topics()

        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retry_exhaustion_on_429_raises_api_error(self, mock_request, mock_sleep) -> None:
        mock_request.side_effect = [_make_429_response(), _make_429_response(), _make_429_response()]

        client = self.make_client(max_retries=2)
        with self.assertRaises(CyberNativeAPIError) as ctx:
            client.list_notifications()
        self.assertIn("HTTP 429", str(ctx.exception))
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retries_on_500_502_503_504(self, mock_request, mock_sleep) -> None:
        for status in (500, 502, 503, 504):
            mock_request.reset_mock()
            mock_sleep.reset_mock()
            err_resp = _make_500_response()
            err_resp.status_code = status
            ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
            mock_request.side_effect = [err_resp, err_resp, ok_resp]

            client = self.make_client(max_retries=2)
            client.get_latest_topics()

            self.assertEqual(mock_request.call_count, 3, f"status {status}: expected 3 requests")
            self.assertEqual(mock_sleep.call_count, 2, f"status {status}: expected 2 sleep calls")

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_no_retry_on_non_retryable_status(self, mock_request, mock_sleep) -> None:
        for status in (403, 404, 422):
            mock_request.reset_mock()
            mock_sleep.reset_mock()
            err_resp = MagicMock()
            err_resp.status_code = status
            err_resp.ok = False
            err_resp.headers = {}
            err_resp.json.side_effect = ValueError
            err_resp.text = f"error {status}"
            err_resp.reason = "Error"
            mock_request.return_value = err_resp

            client = self.make_client(max_retries=2)
            with self.assertRaises(CyberNativeAPIError) as ctx:
                client.list_notifications()
            self.assertIn(f"HTTP {status}", str(ctx.exception))
            self.assertEqual(mock_request.call_count, 1, f"status {status}: should not retry")
            mock_sleep.assert_not_called()

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_max_retries_zero_no_retry(self, mock_request, mock_sleep) -> None:
        mock_request.return_value = _make_429_response()

        client = self.make_client(max_retries=0)
        with self.assertRaises(CyberNativeAPIError):
            client.list_notifications()

        self.assertEqual(mock_request.call_count, 1)
        mock_sleep.assert_not_called()

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retry_respects_retry_after_header(self, mock_request, mock_sleep) -> None:
        ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
        err_resp = _make_429_response()
        err_resp.headers = {"Retry-After": "5"}
        mock_request.side_effect = [err_resp, ok_resp]

        client = self.make_client(max_retries=2)
        client.get_latest_topics()

        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_once_with(5)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retry_falls_back_to_exponential_when_retry_after_is_non_numeric(self, mock_request, mock_sleep) -> None:
        ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
        err_resp = _make_429_response()
        err_resp.headers = {"Retry-After": "Fri, 31 Dec 1999 23:59:59 GMT"}
        mock_request.side_effect = [err_resp, ok_resp]

        client = self.make_client(max_retries=2)
        client.get_latest_topics()

        self.assertEqual(mock_sleep.call_count, 1)
        mock_sleep.assert_called_once_with(1)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_retries_on_request_exception_then_succeeds(self, mock_request, mock_sleep) -> None:
        ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
        conn_err = requests_lib.ConnectionError("connection refused")
        mock_request.side_effect = [conn_err, ok_resp]

        client = self.make_client(max_retries=2)
        client.get_latest_topics()

        self.assertEqual(mock_request.call_count, 2)
        mock_sleep.assert_called_once_with(1)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_request_exception_exhaustion_raises_api_error(self, mock_request, mock_sleep) -> None:
        mock_request.side_effect = requests_lib.ConnectionError("connection refused")

        client = self.make_client(max_retries=2)
        with self.assertRaises(CyberNativeAPIError) as ctx:
            client.list_notifications()
        self.assertIn("connection refused", str(ctx.exception))
        self.assertEqual(mock_sleep.call_count, 2)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_exponential_backoff_uses_2_to_the_attempt(self, mock_request, mock_sleep) -> None:
        err_resp = _make_429_response()
        err_resp.headers = {}
        ok_resp = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={"topics": []}))
        mock_request.side_effect = [err_resp, err_resp, err_resp, ok_resp]

        client = self.make_client(max_retries=3)
        client.get_latest_topics()

        self.assertEqual(mock_sleep.call_count, 3)
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)
        mock_sleep.assert_any_call(4)

    @patch("time.sleep", return_value=None)
    @patch("cybernative_tools.requests.request")
    def test_non_json_response_after_retry_raises(self, mock_request, mock_sleep) -> None:
        resp = MagicMock(ok=True, status_code=200)
        resp.json.side_effect = ValueError("not JSON")
        mock_request.return_value = resp

        client = self.make_client(max_retries=0)
        with self.assertRaises(CyberNativeAPIError) as ctx:
            client.list_notifications()
        self.assertIn("non-JSON", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
