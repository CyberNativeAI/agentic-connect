# CYB-999448: Agentic-connect Reliability Audit

Audit date: 2026-06-08
Auditor: JuniorEngineer (7a5ea3bc-f48d-4f37-a970-0775cbf3919)
Repo: agentic-connect v1.3.2
Scope: code quality, error handling, test coverage of all four source modules

## Verification Run

| Check | Result |
|-------|--------|
| `py -3 -m pytest tests/ -v` | **96 passed** in 10.40s (4 test files) |
| `py -3 cybernative_mcp_server.py --validate` | OK (16 tools, full mode) |
| `py -3 cybernative_mcp_server.py --validate --read-only` | OK (9 tools) |
| `py -3 tests/run_probe_public_smoke.py` | OK (local stub) |
| `py -3 tests/run_negative_path_checks.py` | All checks pass (config, network, CLI) |
| `py -3 cybernative_connect.py --probe-public` | **Live OK**: HTTP 200, 3 topics shown |
| `py -3 scripts/_ce_skill_validate.py` | OK: all 16 client methods in MCP, OpenAI, markdown docs |

## Source Modules Audited

### 1. `cybernative_connect.py` (477 lines)

**Error handling: Good.** All external I/O paths have try/except with descriptive RuntimeError wrappers. Timeout, nonce mismatch, decryption failure, and base64 errors all produce actionable messages.

**Code quality findings:**

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| C1 | Low | `load_credentials_file` does not validate URL scheme (https:// or http://), unlike `CyberNativeClient._load_credentials` which does. A credentials file with `"base_url": "ftp://evil.example"` would pass validation in `--verify` mode but fail at request time with a confusing error. | `cybernative_connect.py:214-246` |
| C2 | Low | `save_json` silently swallows OSError on `os.chmod` (line 204). If chmod fails (e.g., on a filesystem that doesn't support Unix permissions like FAT32/NTFS), the credentials file may be world-readable without any warning. | `cybernative_connect.py:202-205` |
| C3 | Low | Module-level `_CALLBACK: dict[str, str]` is mutable global state (line 72). If `main()` is called concurrently from multiple threads, callbacks can collide. `main()` does call `_CALLBACK.clear()` at line 392, but the race window exists between clear and the callback handler writing to the dict. | `cybernative_connect.py:72` |
| C4 | Info | `CallbackHandler.log_message` suppresses all HTTP server logs (line 97-99). While this keeps the console clean and avoids leaking callback URLs, it also suppresses legitimate error logs from the HTTP server that could help debug connectivity issues. | `cybernative_connect.py:97-99` |
| C5 | Info | `_print_line` uses a double-encode/decode pattern for cross-encoding safety (line 107-108). This works but is unusual; a comment explaining the motivation would help maintainers. | `cybernative_connect.py:106-110` |
| C6 | Low | No input validation on `--scopes` CLI argument. An invalid scope string like `"read,write,garbage"` is sent to CyberNative.ai as-is and may produce a confusing error. | `cybernative_connect.py:378-379` |

### 2. `cybernative_tools.py` (464 lines)

**Error handling: Excellent.** Custom exception hierarchy (`CyberNativeConfigurationError`, `CyberNativeAPIError`), retry logic with exponential backoff, Retry-After header respect, JSON parsing guards, URL scheme validation, placeholder field detection.

**Code quality findings:**

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| T1 | Low | `_get_client()` singleton (line 376-380) is not thread-safe. If two threads call a module-level convenience function simultaneously before the singleton is initialized, they may both try to instantiate `CyberNativeClient()`, potentially opening two credentials files. | `cybernative_tools.py:376-380` |
| T2 | Info | `_request()` retry loop uses `time.sleep(2**attempt)` which produces delays of 1s, 2s, 4s, 8s... This is good. The `Retry-After` header parsing uses `retry_after.isdigit()` which correctly rejects date-format values and falls back to exponential. | `cybernative_tools.py:101-143` |
| T3 | Low | `read_topic` and `get_user` type hint their parameters as `int` and `str` respectively, but the `str()` and `quote()` calls inside handle non-int/non-str inputs at runtime. The parameter type hints are misleading if callers pass string IDs. | `cybernative_tools.py:179,346` |
| T4 | Info | `_response_detail()` handles three common error key names (`errors`, `error`, `message`) which covers Discourse API variations well. | `cybernative_tools.py:145-155` |

### 3. `cybernative_mcp_bridge.py` (117 lines)

**Error handling: Good.** `validate_bridge_surface` catches missing tools, missing methods, and unknown read-only tools. `sanitize_error_message` redacts secrets before they hit MCP clients.

**Code quality findings:**

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| B1 | Medium | `sanitize_error_message` regex `\b[A-Za-z0-9]{20,}\b` (line 29) can over-redact. Any alphanumeric string ≥20 chars (e.g., a UUID without dashes, a long topic slug, or a long error ID) will be replaced with `[redacted]`, potentially making error messages harder to debug. Consider narrowing to patterns that look like actual secrets (high entropy, mixed case+digits). | `cybernative_mcp_bridge.py:29` |
| B2 | Low | `dispatch_tool` passes `arguments or {}` directly to the client method via `**`. If `arguments` contains extra keys not matching the method's parameters, the call will raise a `TypeError` rather than a more descriptive error. The MCP server catches this in its general `except Exception` guard, but the error message will include the raw method signature. | `cybernative_mcp_bridge.py:117` |
| B3 | Info | `validate_bridge_surface` only checks method existence, not parameter alignment between MCP tool `inputSchema` and Python method signatures. Parameter type/drift between the JSON schema and the Python function signature is not caught. | `cybernative_mcp_bridge.py:63-97` |

### 4. `cybernative_mcp_server.py` (138 lines)

**Error handling: Good.** Specific exception catches (`CyberNativeConfigurationError`, `CyberNativeAPIError`, `ValueError`) before the catch-all `Exception` guard, with secret sanitization on all error paths.

**Code quality findings:**

| # | Severity | Finding | Location |
|---|----------|---------|----------|
| S1 | Info | `call_tool` returns errors as `TextContent` with type `"text"` (line 59). This is the correct MCP protocol behavior -- errors are returned as content, not exceptions -- but agents consuming the output need to distinguish error text from success text by content rather than type. | `cybernative_mcp_server.py:48-62` |
| S2 | Low | `build_server` is defined as a factory function but creates a closure over `credentials_file` via `get_client()`. If `build_server` were called with different credentials files in the same process, the client holder dict design prevents cross-contamination, but the pattern is subtle. | `cybernative_mcp_server.py:25-64` |

## Test Coverage Assessment

**96 unit tests across 4 files, all passing.** Coverage is strong in the following areas:

| Area | Tests | Quality |
|------|-------|---------|
| Auth URL building | 2 | Good |
| Secret masking | 3 | Good |
| Key extraction | 5 | Good (all three key name variants + edge cases) |
| Nonce validation | 4 | Good (match, mismatch, missing, non-string) |
| Decryption errors | 2 | Good (bad base64, garbage ciphertext) |
| Credentials dataclass | 1 | Minimal |
| Probe-public | 8 | Good (success, HTTP error, empty, network, JSON error, custom URL, limit, CLI) |
| Verify smoke test | 5 | Good (success, missing file, corrupt JSON, network error, live path) |
| Timeout handling | 1 | Good |
| Client methods (all 16) | 18 | Good (endpoint, headers, quoting, error propagation) |
| Retry behavior | 8 | Excellent (429, 502, exhaustion, exponential backoff, Retry-After, ConnectionError, non-retryable statuses) |
| Rate limiting | 10 | Excellent (max retries zero, exhaustion, per-status, Retry-After header, non-numeric fallback) |
| MCP bridge surface | 14 | Good (validate, dispatch, read-only, sanitization) |
| Convenience singleton | 3 | Adequate (heavy mocking) |

**Coverage gaps:**

| # | Severity | Gap |
|---|----------|-----|
| G1 | Medium | `cybernative_mcp_server.build_server` async `list_tools` and `call_tool` handlers have no direct unit tests. Only the `--validate` path (which skips stdio) is tested. The async stdio path requires `mcp` library integration which is hard to unit test, but the server building and error-to-text conversion can be tested with a mock server. |
| G2 | Medium | `example_read_latest` function body is never exercised. In `test_cybernative_connect.py`, the verify smoke test patches `example_read_latest` with a mock. The actual `requests.get` call and topic printing logic is untested. |
| G3 | Low | `_response_detail` helper is exercised only indirectly through `_request` error paths. The specific branches (JSON errors dict, JSON error string, JSON message, fallback to text) are not individually tested. |
| G4 | Low | CLI flags `--read-only`, `--print-secret`, and `--scopes` have no direct test coverage for their behavior (e.g., asserting that `--read-only` sets scopes to `"read"` or that `--print-secret` outputs the raw key). |
| G5 | Low | `save_json` chmod-OSError path is untested. The function silently ignores permission-setting failures, so there's no way to verify this doesn't regress. |
| G6 | Low | `load_credentials_file` placeholder detection and missing-fields for all required keys (not just `user_api_client_id`) are not all tested. Only `user_api_client_id` is tested in `test_cybernative_connect.py:136-151`. |

## Security Notes

- `.gitignore` covers `cybernative_agent_credentials.json`, `*_credentials.json`, `*_creds.json` -- no credential leakage risk.
- `sanitize_error_message` in MCP bridge redacts API keys before they reach MCP clients.
- `mask_secret` defaults to showing only first/last 4 chars; `--print-secret` is opt-in.
- `CallbackHandler.log_message` suppresses HTTP server log output to avoid callback URL leaks.
- RSA key is ephemeral (generated per-run, never persisted).
- Nonce validation uses `secrets.compare_digest` (constant-time comparison).

## Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Error handling | **Strong** | Custom exceptions, retry logic, descriptive messages, secret redaction |
| Test coverage | **Good** | 96 tests, all passing; 6 identified gaps (G1-G6) |
| Code quality | **Good** | 4 source modules, 15 findings (0 critical, 0 high, 1 medium, 11 low, 3 info) |
| Security posture | **Strong** | Credentials gitignored, secret redaction, ephemeral keys, constant-time comparison |
| Live connectivity | **Verified** | `--probe-public` returns HTTP 200 with topic data |

**Bottom line:** The agentic-connect codebase is in good shape. The most actionable items are:

1. **B1 (Medium):** Narrow `sanitize_error_message` regex to reduce false-positive redactions of non-secret strings ≥20 characters.
2. **C1 (Low):** Add URL scheme validation to `load_credentials_file` for consistency with `CyberNativeClient._load_credentials`.
3. **G1 (Medium):** Add direct unit tests for `build_server` error-to-TextContent conversion path.
4. **G2 (Medium):** Add a test that exercises `example_read_latest` against a local HTTP stub.
