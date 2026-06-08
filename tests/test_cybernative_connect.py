import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import cybernative_connect as connect


class BuildAuthUrlTest(unittest.TestCase):
    def test_output_contains_expected_params(self) -> None:
        url = connect.build_auth_url(
            base_url="https://cybernative.ai",
            app_name="TestApp",
            scopes="read",
            client_id="cid-1",
            public_key_pem="-----BEGIN PUBLIC KEY-----",
            auth_redirect="http://127.0.0.1:8787/callback",
            nonce="nonce123",
        )
        self.assertIn("cybernative.ai/user-api-key/new", url)
        self.assertIn("application_name=TestApp", url)
        self.assertIn("client_id=cid-1", url)
        self.assertIn("scopes=read", url)
        self.assertIn("nonce=nonce123", url)

    def test_base_url_trailing_slash_is_handled(self) -> None:
        url = connect.build_auth_url(
            base_url="https://cybernative.ai/",
            app_name="X",
            scopes="read",
            client_id="c",
            public_key_pem="k",
            auth_redirect="http://127.0.0.1:8787/cb",
            nonce="n",
        )
        self.assertIn("cybernative.ai/user-api-key/new?", url)


class MaskSecretTest(unittest.TestCase):
    def test_long_secret_is_masked(self) -> None:
        result = connect.mask_secret("abcdefghijklmnopqrstuvwxyz123456", visible=4)
        self.assertEqual(result, "abcd...3456")

    def test_short_secret_is_hidden(self) -> None:
        result = connect.mask_secret("short", visible=4)
        self.assertEqual(result, "<hidden>")

    def test_exact_double_visible_is_hidden(self) -> None:
        result = connect.mask_secret("12345678", visible=4)
        self.assertEqual(result, "<hidden>")


class ExtractUserKeyTest(unittest.TestCase):
    def test_extracts_key_field(self) -> None:
        key = connect.extract_user_key({"key": "my-api-key"})
        self.assertEqual(key, "my-api-key")

    def test_extracts_user_api_key_field(self) -> None:
        key = connect.extract_user_key({"user_api_key": "my-key"})
        self.assertEqual(key, "my-key")

    def test_extracts_api_key_field(self) -> None:
        key = connect.extract_user_key({"api_key": "my-key"})
        self.assertEqual(key, "my-key")

    def test_raises_when_no_key_found(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            connect.extract_user_key({"other": "value"})
        self.assertIn("Could not locate", str(ctx.exception))

    def test_raises_when_key_is_not_string(self) -> None:
        with self.assertRaises(RuntimeError):
            connect.extract_user_key({"key": 12345})


class ValidateNonceTest(unittest.TestCase):
    def test_matching_nonce_passes(self) -> None:
        connect.validate_nonce({"nonce": "abc123"}, "abc123")

    def test_mismatched_nonce_raises(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            connect.validate_nonce({"nonce": "abc123"}, "xyz789")
        self.assertIn("did not match", str(ctx.exception))

    def test_missing_nonce_raises(self) -> None:
        with self.assertRaises(RuntimeError) as ctx:
            connect.validate_nonce({"other": "val"}, "abc123")
        self.assertIn("did not include", str(ctx.exception))

    def test_non_string_nonce_raises(self) -> None:
        with self.assertRaises(RuntimeError):
            connect.validate_nonce({"nonce": 12345}, "abc123")


class DecryptPayloadErrorsTest(unittest.TestCase):
    def test_non_base64_payload_raises(self) -> None:
        from Cryptodome.PublicKey import RSA

        rsa_key = RSA.generate(2048)
        with self.assertRaises(RuntimeError) as ctx:
            connect.decrypt_payload(rsa_key, "!!!not-valid-base64!!!")
        self.assertIn("not valid base64", str(ctx.exception))

    def test_garbage_ciphertext_raises(self) -> None:
        import base64

        from Cryptodome.PublicKey import RSA

        rsa_key = RSA.generate(2048)
        garbage = base64.b64encode(b"\x00" * 256).decode("ascii")
        with self.assertRaises(RuntimeError) as ctx:
            connect.decrypt_payload(rsa_key, garbage)
        self.assertIn("Could not decrypt", str(ctx.exception))


class CyberNativeAgentCredsTest(unittest.TestCase):
    def test_headers_returns_expected_dict(self) -> None:
        creds = connect.CyberNativeAgentCreds(
            base_url="https://cybernative.ai",
            user_api_key="my-key",
            user_api_client_id="client-1",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )
        headers = creds.headers()
        self.assertEqual(headers["User-Api-Key"], "my-key")
        self.assertEqual(headers["User-Api-Client-Id"], "client-1")
        self.assertEqual(headers["Accept"], "application/json")


class LoadCredentialsFileMissingFieldsTest(unittest.TestCase):
    def test_missing_user_api_client_id_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "secret-key",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                connect.load_credentials_file(str(path))
            self.assertIn("user_api_client_id", str(ctx.exception))


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

    @patch("cybernative_connect.requests.get")
    def test_main_probe_public_cli_success(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": "CLI topic one"},
                            {"title": "CLI topic two"},
                        ]
                    }
                }
            ),
        )

        stdout = StringIO()
        with redirect_stdout(stdout):
            code = connect.main(["--probe-public", "--limit", "2"])

        self.assertEqual(code, 0)
        output = stdout.getvalue()
        self.assertIn("PROBE OK", output)
        self.assertIn("CLI topic one", output)
        mock_get.assert_called_once()


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
