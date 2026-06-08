import json
import os
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests as requests_lib

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


class LoadCredentialsFileTest(unittest.TestCase):
    def test_success_loads_valid_credentials(self) -> None:
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
            self.assertEqual(creds.user_api_client_id, "client-1")

    def test_success_strips_trailing_slash(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai/",
                        "user_api_key": "secret-key",
                        "user_api_client_id": "client-1",
                    }
                ),
                encoding="utf-8",
            )
            creds = connect.load_credentials_file(str(path))
            self.assertEqual(creds.base_url, "https://cybernative.ai")

    def test_file_not_found_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "nonexistent.json"
            with self.assertRaises(FileNotFoundError) as ctx:
                connect.load_credentials_file(str(path))
            self.assertIn("not found", str(ctx.exception))

    def test_invalid_json_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text("not valid json", encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                connect.load_credentials_file(str(path))
            self.assertIn("not valid JSON", str(ctx.exception))

    def test_missing_required_fields_raises(self) -> None:
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

    def test_missing_multiple_fields_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(json.dumps({}), encoding="utf-8")
            with self.assertRaises(ValueError) as ctx:
                connect.load_credentials_file(str(path))
            self.assertIn("base_url", str(ctx.exception))
            self.assertIn("user_api_key", str(ctx.exception))

    def test_placeholder_field_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "<replace-me>",
                        "user_api_client_id": "client-1",
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError) as ctx:
                connect.load_credentials_file(str(path))
            self.assertIn("placeholder", str(ctx.exception))

    def test_invalid_url_scheme_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            for bad_url in ("ftp://evil.example", "://missing-scheme", "just-a-string"):
                path.write_text(
                    json.dumps(
                        {
                            "base_url": bad_url,
                            "user_api_key": "secret-key",
                            "user_api_client_id": "client-1",
                        }
                    ),
                    encoding="utf-8",
                )
                with self.subTest(base_url=bad_url):
                    with self.assertRaises(ValueError) as ctx:
                        connect.load_credentials_file(str(path))
                    self.assertIn("base_url", str(ctx.exception))

    def test_optional_fields_default_to_empty(self) -> None:
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
            self.assertEqual(creds.scopes_requested, "")
            self.assertEqual(creds.issued_at_utc, "")

    def test_reads_scopes_and_issued_at(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text(
                json.dumps(
                    {
                        "base_url": "https://cybernative.ai",
                        "user_api_key": "secret-key",
                        "user_api_client_id": "client-1",
                        "scopes_requested": "read,write",
                        "issued_at_utc": "2026-06-01T00:00:00Z",
                    }
                ),
                encoding="utf-8",
            )
            creds = connect.load_credentials_file(str(path))
            self.assertEqual(creds.scopes_requested, "read,write")
            self.assertEqual(creds.issued_at_utc, "2026-06-01T00:00:00Z")


class CallbackHandlerTest(unittest.TestCase):
    def setUp(self) -> None:
        connect._CALLBACK.clear()

    def _make_handler(self, path: str) -> connect.CallbackHandler:
        handler = connect.CallbackHandler.__new__(connect.CallbackHandler)
        handler.path = path
        handler.client_address = ("127.0.0.1", 8787)
        handler.server = MagicMock()
        handler.server.callback_path = "/callback"
        handler.wfile = MagicMock()
        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()
        return handler

    def test_valid_path_with_payload_sets_callback(self) -> None:
        handler = self._make_handler("/callback?payload=test-payload")
        handler.do_GET()
        self.assertEqual(connect._CALLBACK["payload"], "test-payload")

    def test_wrong_path_returns_404(self) -> None:
        handler = self._make_handler("/wrong-path")
        handler.do_GET()
        self.assertEqual(handler.send_response.call_args[0][0], 404)

    def test_missing_payload_returns_400(self) -> None:
        handler = self._make_handler("/callback")
        handler.do_GET()
        self.assertEqual(handler.send_response.call_args[0][0], 400)

    def test_log_message_suppressed(self) -> None:
        handler = self._make_handler("/callback")
        handler.log_message("GET", "/callback", 200, 0)


class IsoUtcNowTest(unittest.TestCase):
    def test_returns_iso_8601_format(self) -> None:
        result = connect.iso_utc_now()
        self.assertRegex(result, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

    def test_ends_with_z(self) -> None:
        result = connect.iso_utc_now()
        self.assertTrue(result.endswith("Z"))


class SaveJsonTest(unittest.TestCase):
    def test_writes_file_with_correct_content(self) -> None:
        obj = {"key": "value", "nested": {"a": 1}}
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.json")
            connect.save_json(path, obj)
            self.assertTrue(os.path.isfile(path))
            with open(path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            self.assertEqual(loaded, obj)

    def test_file_ends_with_newline(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.json")
            connect.save_json(path, {"a": 1})
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertTrue(content.endswith("\n"))

    def test_indent_is_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "test.json")
            connect.save_json(path, {"a": 1})
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn('  "a"', content)


class ExampleReadLatestTest(unittest.TestCase):
    @patch("cybernative_connect.requests.get")
    def test_returns_topic_count(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            raise_for_status=MagicMock(),
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": "A", "slug": "a", "id": 1},
                            {"title": "B", "slug": "b", "id": 2},
                        ]
                    }
                }
            ),
        )
        creds = connect.CyberNativeAgentCreds(
            base_url="https://cybernative.ai",
            user_api_key="key",
            user_api_client_id="client",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )

        count = connect.example_read_latest(creds, limit=2)

        self.assertEqual(count, 2)
        mock_get.assert_called_once()
        self.assertIn("/latest.json", mock_get.call_args.args[0])

    @patch("cybernative_connect.requests.get")
    def test_handles_empty_topics(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            raise_for_status=MagicMock(),
            json=MagicMock(return_value={"topic_list": {"topics": []}}),
        )
        creds = connect.CyberNativeAgentCreds(
            base_url="https://cybernative.ai",
            user_api_key="key",
            user_api_client_id="client",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )

        count = connect.example_read_latest(creds)

        self.assertEqual(count, 0)


class DecryptPayloadSuccessTest(unittest.TestCase):
    def test_roundtrip_decrypts_valid_payload(self) -> None:
        import base64
        import urllib.parse

        from Cryptodome.Cipher import PKCS1_v1_5
        from Cryptodome.PublicKey import RSA

        rsa_key = RSA.generate(2048)
        cipher = PKCS1_v1_5.new(rsa_key.publickey())
        plaintext = json.dumps({"key": "my-secret-api-key", "nonce": "nonce123"}).encode("utf-8")
        ciphertext = cipher.encrypt(plaintext)
        payload_param = urllib.parse.quote(base64.b64encode(ciphertext).decode("ascii"))

        result = connect.decrypt_payload(rsa_key, payload_param)

        self.assertEqual(result["key"], "my-secret-api-key")
        self.assertEqual(result["nonce"], "nonce123")

    def test_decrypted_payload_not_valid_json_raises(self) -> None:
        import base64
        import urllib.parse

        from Cryptodome.Cipher import PKCS1_v1_5
        from Cryptodome.PublicKey import RSA

        rsa_key = RSA.generate(2048)
        cipher = PKCS1_v1_5.new(rsa_key.publickey())
        ciphertext = cipher.encrypt(b"not json")
        payload_param = urllib.parse.quote(base64.b64encode(ciphertext).decode("ascii"))

        with self.assertRaises(RuntimeError) as ctx:
            connect.decrypt_payload(rsa_key, payload_param)
        self.assertIn("not valid JSON", str(ctx.exception))


class ExtractUserKeyPriorityTest(unittest.TestCase):
    def test_prefers_key_over_user_api_key(self) -> None:
        key = connect.extract_user_key({"key": "key-field", "user_api_key": "uak-field"})
        self.assertEqual(key, "key-field")

    def test_falls_back_to_user_api_key_when_key_is_not_string(self) -> None:
        key = connect.extract_user_key({"key": 12345, "user_api_key": "uak-field"})
        self.assertEqual(key, "uak-field")

    def test_falls_back_to_api_key_when_others_not_present(self) -> None:
        key = connect.extract_user_key({"api_key": "ak-field"})
        self.assertEqual(key, "ak-field")


class WaitForPayloadTest(unittest.TestCase):
    def setUp(self) -> None:
        connect._CALLBACK.clear()

    def test_returns_payload_when_set(self) -> None:
        connect._CALLBACK["payload"] = "test-value"
        result = connect.wait_for_payload(timeout_s=1)
        self.assertEqual(result, "test-value")


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

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_network_error(self, mock_get) -> None:
        mock_get.side_effect = requests_lib.ConnectionError("connection refused")

        code = connect.run_probe_public()

        self.assertEqual(code, 1)

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_non_json_response(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(side_effect=ValueError("not JSON")),
        )

        code = connect.run_probe_public()

        self.assertEqual(code, 1)

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_custom_base_url(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": "Topic A"},
                        ]
                    }
                }
            ),
        )

        code = connect.run_probe_public(base_url="https://custom.example.com")

        self.assertEqual(code, 0)
        mock_get.assert_called_once()
        self.assertIn("custom.example.com", mock_get.call_args.args[0])

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_shows_only_limit_topics(self, mock_get) -> None:
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(
                return_value={
                    "topic_list": {
                        "topics": [
                            {"title": f"Topic {i}"} for i in range(1, 11)
                        ]
                    }
                }
            ),
        )

        code = connect.run_probe_public(limit=3)

        self.assertEqual(code, 0)
        args, _ = mock_get.call_args
        self.assertIn("/latest.json", args[0])

    @patch("cybernative_connect.requests.get")
    def test_run_probe_public_large_limit_shows_all(self, mock_get) -> None:
        topics = [{"title": "A"}, {"title": "B"}]
        mock_get.return_value = MagicMock(
            ok=True,
            status_code=200,
            json=MagicMock(return_value={"topic_list": {"topics": topics}}),
        )

        code = connect.run_probe_public(limit=10)

        self.assertEqual(code, 0)

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

    @patch.object(connect, "example_read_latest")
    @patch.object(connect, "load_credentials_file")
    def test_run_verify_smoke_test_request_exception(self, load_creds, read_latest) -> None:
        load_creds.return_value = connect.CyberNativeAgentCreds(
            base_url="https://cybernative.ai",
            user_api_key="secret-key",
            user_api_client_id="client-1",
            scopes_requested="read",
            issued_at_utc="2026-06-01T00:00:00Z",
        )
        read_latest.side_effect = requests_lib.ConnectionError("network unreachable")

        code = connect.run_verify_smoke_test("creds.json")

        self.assertEqual(code, 1)

    def test_main_verify_corrupt_json_exits_nonzero(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "creds.json"
            path.write_text("not valid json", encoding="utf-8")
            code = connect.main(["--verify", "--out", str(path)])
        self.assertEqual(code, 1)


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
