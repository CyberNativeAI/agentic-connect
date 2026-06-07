import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
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


class ProbePublicSmokeTest(unittest.TestCase):
    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_success(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": "First topic"},
                            {"title": "Second topic"},
                            {"title": "Third topic"},
                        ]
                    }
                }
            ),
        )

        code = connect.run_probe_public(limit=2)

        self.assertEqual(code, 0)
        mock_get.assert_called_once()
        self.assertIn("/latest.json", mock_get.call_args.args[0])
        headers = mock_get.call_args.kwargs["headers"]
        self.assertEqual(headers["User-Agent"], connect.DEFAULT_CONNECTOR_USER_AGENT)

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_http_error(self, mock_get) -> None:
        mock_get.return_value = MagicMock(ok=False, status_code=403)

        code = connect.run_probe_public()

        self.assertEqual(code, 1)

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_empty_topics(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(return_value={"topic_list": {"topics": []}}),
        )

        code = connect.run_probe_public()

        self.assertEqual(code, 1)

    def test_main_probe_public_help(self) -> None:
        with self.assertRaises(SystemExit) as ctx:
            connect.main(["--help"])
        self.assertEqual(ctx.exception.code, 0)


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


class ConnectMainTest(unittest.TestCase):
    @patch.object(connect.RSA, "generate")
    @patch.object(connect, "run_callback_server")
    @patch.object(connect, "wait_for_payload")
    def test_timeout_exits_cleanly_without_traceback(self, wait_for_payload, run_callback_server, generate_rsa) -> None:
        httpd = MagicMock()
        run_callback_server.return_value = httpd
        wait_for_payload.side_effect = TimeoutError("Timed out after 3s waiting for approval callback.")
        generate_rsa.return_value.publickey.return_value.export_key.return_value = b"public-key"

        stdout = StringIO()
        with redirect_stdout(stdout):
            code = connect.main(["--read-only", "--timeout", "3", "--no-example"])

        self.assertEqual(code, 1)
        self.assertIn("scopes=read", stdout.getvalue())
        self.assertIn("ERROR: Timed out after 3s waiting for approval callback.", stdout.getvalue())
        self.assertNotIn("Traceback", stdout.getvalue())
        httpd.shutdown.assert_called_once()


if __name__ == "__main__":
    unittest.main()
