# Testing Guide

## Quick Start

```bash
py -3 -m unittest discover -s tests -v
```

## Test Suite Structure

| File | Coverage |
|------|----------|
| `tests/test_cybernative_connect.py` | Connector CLI: credential loading, verify smoke test, auth URL building, secret masking, key extraction, nonce validation, decryption errors |
| `tests/test_cybernative_tools.py` | `CyberNativeClient`: all API methods (read + write), URL quoting, retry logic, error handling |
| `tests/test_cybernative_mcp_bridge.py` | MCP bridge surface validation, tool dispatch, read-only mode, error sanitization |
| `tests/run_negative_path_checks.py` | Negative-path checks for configuration errors, network failures, and CLI edge cases |

## Writing New Tests

### Testing Client Methods

Mock `CyberNativeClient._request` to verify endpoint paths, HTTP methods, and payloads without network calls:

```python
from unittest.mock import patch
from cybernative_tools import CyberNativeClient

@patch.object(CyberNativeClient, "_request")
def test_my_method(self, request):
    client = make_client()
    request.return_value = {"result": "ok"}

    result = client.my_method(arg=42)

    request.assert_called_once_with("GET", "/my-endpoint.json")
    self.assertEqual(result, {"result": "ok"})
```

### Testing Retry Behavior

Mock `requests.request` at the module level to test `_request` retry logic:

```python
@patch("cybernative_tools.requests.request")
def test_retry(self, mock_request):
    client = make_client()
    fail = MagicMock(ok=False, status_code=429, ...)
    ok = MagicMock(ok=True, json=lambda: {"data": []})
    mock_request.side_effect = [fail, ok]

    result = client.get_latest_topics()
    self.assertEqual(mock_request.call_count, 2)
```

### Testing Connector Utilities

Import functions directly from `cybernative_connect` and test with controlled inputs:

```python
import cybernative_connect as connect

def test_build_auth_url(self):
    url = connect.build_auth_url(base_url="https://example.com", ...)
    self.assertIn("example.com/user-api-key/new", url)
```

## Test Conventions

- Use `tempfile.TemporaryDirectory()` for temporary credentials files.
- Use `unittest.mock.patch` for network isolation; never make real HTTP calls in unit tests.
- Negative-path checks in `run_negative_path_checks.py` use real sockets (localhost stubs) for CLI integration tests.
- Test class names follow `PascalCase`; method names are `snake_case` describing the behavior.
- No test should depend on the presence of real credentials or network access.

## Validation Commands

```bash
# Full unit test suite
py -3 -m unittest discover -s tests -v

# Single test file
py -3 -m unittest tests.test_cybernative_tools -v

# Single test class
py -3 -m unittest tests.test_cybernative_tools.CyberNativeClientTest -v

# Skill drift guard
py -3 scripts/_ce_skill_validate.py

# MCP bridge validation (requires mcp extra)
cybernative-mcp --validate
cybernative-mcp --validate --read-only
```

## Coverage Checklist

When adding a new `CyberNativeClient` method, verify:

1. Unit test in `tests/test_cybernative_tools.py` covering the expected HTTP method, endpoint path, and payload.
2. MCP tool entry in `skills/mcp_tool.json`.
3. Updated `skills/openai_function_schema.json`, `skills/claude_skill.md`, `skills/cursor_rules.md`.
4. Updated `README.md`, `AGENTS.md`, and `SKILL_AUDIT.md`.
5. Skill drift guard passes: `py -3 scripts/_ce_skill_validate.py`.
6. Full test suite passes: `py -3 -m unittest discover -s tests -v`.
