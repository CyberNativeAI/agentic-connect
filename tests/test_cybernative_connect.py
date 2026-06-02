import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

import cybernative_connect as connect


class LoadCredentialsFileTest(unittest.TestCase):
    def test_missing_file_raises(self) -> None:
        with self.assertRaises(FileNotFoundError):
            connect.load_credentials_file("definitely_missing_creds.json")

    def test_placeholder_fields_raise(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "<user_api_key>",
                        "user_api_client_id": "client-1",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                connect.load_credentials_file(str(path))

    def test_valid_file_loads(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "secret-key",
                        "user_api_client_id": "client-1",
                    }
                ),
                encoding="utf-8",
            )
            creds = connect.load_credentials_file(str(path))
            self.assertEqual(creds.base_url, "https://cybernative.ai")
            self.assertEqual(creds.user_api_key, "secret-key")


class VerifySmokeTest(unittest.TestCase):
    @patch.object(connect, "example_read_latest", return_value=5)
    @patch.object(connect, "load_credentials_file")
    def test_run_verify_smoke_test_success(self, load_creds, read_latest) -> None:
        load_creds.return_value = connect.CyberNativeAgentCreds(
            base_url="https://cybernative.ai",
            user_api_key="secret-key",
            user_api_client_id="client-1",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )

        code = connect.run_verify_smoke_test("creds.json", limit=2)

        self.assertEqual(code, 0)
        load_creds.assert_called_once_with("creds.json")
        read_latest.assert_called_once()
        self.assertEqual(read_latest.call_args.kwargs["limit"], 2)

    def test_main_verify_missing_file_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            missing = str(Path(tmpdir) / "missing.json")
            code = connect.main(["--verify", "--out", missing])
        self.assertEqual(code, 1)

    @patch("cybernative_connect.requests.get")
    def test_main_verify_live_request_path(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": "Hello", "slug": "hello", "id": 1},
                        ]
                    }
                }
            ),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "secret-key",
                        "user_api_client_id": "client-1",
                    }
                ),
                encoding="utf-8",
            )
            code = connect.main(["--verify", "--out", str(path), "--limit", "1"])

        self.assertEqual(code, 0)
        mock_get.assert_called_once()
        self.assertIn("/latest.json", mock_get.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
