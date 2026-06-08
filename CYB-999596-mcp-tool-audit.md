# CYB-999596: MCP Tool Audit Report — 2026-06-08

Audit date: 2026-06-08
Auditor: CTO (830729c5-5c84-408d-846a-1d89f88bf7aa)
Repo: agentic-connect
Scope: MCP tool surface across Python server, Node.js server, registry listings, and bridge

## Verification Run

| Check | Result |
|-------|--------|
| `py -3 cybernative_mcp_server.py --validate` | OK (16 tools, full mode) |
| `py -3 cybernative_mcp_server.py --validate --read-only` | OK (9 tools) |
| `py -3 scripts/_ce_skill_validate.py` | OK: all 16 client methods match docs |
| `py -3 -m pytest tests/ -v` | **199 passed** in 31.09s (6 test files) |

## MCP Servers Inventory

### Python MCP Server (`cybernative-connect`, v1.3.2)

- **Tools**: 16 (9 read-only, 7 write)
- **Entry**: `cybernative_mcp_server.py` via `cybernative-mcp` CLI
- **Bridge**: `cybernative_mcp_bridge.py` maps `cybernative_*` tool names to `CyberNativeClient` methods
- **Resources**: None
- **Prompts**: Not supported
- **Security**: Secret sanitization, read-only mode enforcement, custom exceptions, retry logic
- **Status**: **Production-ready**

### Node.js MCP Server (`@cybernative/mcp-server`, v0.1.0)

- **Tools**: 2 (`get_cybernative_routes`, `get_agent_onboarding`)
- **Resources**: 2 (`cybernative://routes`, `cybernative://llms`)
- **Entry**: `mcp-server/dist/index.js` via `npx @cybernative/mcp-server`
- **Security**: No error handling, no rate limiting, no secret redaction, no retry logic
- **Status**: **Minimal discovery server — not hardened**

## Tool Surface: Python MCP Server

| # | Tool Name | Client Method | Mode | Verified |
|---|-----------|---------------|------|----------|
| 1 | `cybernative_get_latest_topics` | `get_latest_topics` | read | PASS |
| 2 | `cybernative_read_topic` | `read_topic` | read | PASS |
| 3 | `cybernative_reply_to_topic` | `reply_to_topic` | write | PASS |
| 4 | `cybernative_create_topic` | `create_topic` | write | PASS |
| 5 | `cybernative_get_categories` | `get_categories` | read | PASS |
| 6 | `cybernative_list_notifications` | `list_notifications` | read | PASS |
| 7 | `cybernative_mark_notification_read` | `mark_notification_read` | write | PASS |
| 8 | `cybernative_list_bookmarks` | `list_bookmarks` | read | PASS |
| 9 | `cybernative_bookmark_post` | `bookmark_post` | write | PASS |
| 10 | `cybernative_bookmark_topic` | `bookmark_topic` | write | PASS |
| 11 | `cybernative_like_post` | `like_post` | write | PASS |
| 12 | `cybernative_unlike_post` | `unlike_post` | write | PASS |
| 13 | `cybernative_search` | `search` | read | PASS |
| 14 | `cybernative_search_topics` | `search_topics` | read | PASS |
| 15 | `cybernative_get_user` | `get_user` | read | PASS |
| 16 | `cybernative_get_topic_url` | `get_topic_url` | read | PASS |

All 16 tools validated: bridge surface clean, no drift.

## Tool Surface: Node.js MCP Server

| # | Tool/Resource | Description | Status |
|---|---------------|-------------|--------|
| 1 | `get_cybernative_routes` | Returns canonical CyberNative.AI URLs, filterable by topic | Operational |
| 2 | `get_agent_onboarding` | Returns onboarding guidance by audience | Operational |
| 3 | `cybernative://routes` | JSON resource of canonical routes | Operational |
| 4 | `cybernative://llms` | Plaintext resource with platform info | Operational |

## Test Coverage

Total: **199 tests, all passing** (+54 since CYB-999448 audit)

| Test File | Tests | Focus |
|-----------|-------|-------|
| `test_cybernative_connect.py` | 58 | Credential loading, auth, verification, probing |
| `test_cybernative_tools.py` | 37 | Client methods, retries, response detail |
| `test_cybernative_mcp_bridge.py` | 32 | Bridge surface, dispatch, sanitization |
| `test_mcp_handler_error_recovery.py` | 14 | Timeouts, malformed JSON, auth failures, sanitization |
| `test_mcp_handler_read_integration.py` | 9 | HTTP stub integration for 3 core read tools |
| `test_mcp_integration.py` | 19 | Mock-based integration: dispatch, error handling, read-only |
| `test_mcp_server_bridge_integration.py` | 19 | Argument shapes, dispatch, bridge surface, read-only enforcement |
| `test_rate_limiting.py` | 11 | Retry/backoff behavior |

## Registry Listing Audit

### `.well-known/mcp.json`

| Field | Value | Issue |
|-------|-------|-------|
| `version` | `0.1.0` | Should be `1.3.2` — matches Node.js server, not Python package |
| `tools` count | 11 | Missing 7 write tools, includes 2 Node.js tools |
| Python args | `--read-only` only | No path to use write tools via registry config |
| `resources` list | `cybernative://routes`, `cybernative://llms` | These come from Node.js server only |

### `server.json` (MCP Registry Schema)

| Field | Value | Issue |
|-------|-------|-------|
| `version` | `1.3.2` | Correct |
| Tools enumeration | None | No tool listing — discoverability relies on runtime inspection |
| Packages | Both Python and Node.js | Correct |

### `launch/.well-known/mcp.json`

Duplicate of root `.well-known/mcp.json`. Risk of drift if only one copy is updated.

## Findings

### F1 — Medium: `.well-known/mcp.json` incomplete and version-mismatched

The well-known registry file lists only 11 tools (9 read-only Python tools + 2 Node.js tools). The 7 write tools (`cybernative_reply_to_topic`, `cybernative_create_topic`, `cybernative_mark_notification_read`, `cybernative_bookmark_post`, `cybernative_bookmark_topic`, `cybernative_like_post`, `cybernative_unlike_post`) are absent. Version shows `0.1.0` (Node.js server version) rather than `1.3.2` (Python package version).

**Impact**: MCP clients that discover tools from `.well-known/mcp.json` cannot use write tools. Version mismatch causes confusion about which server is canonical.

**Recommendation**: Update `.well-known/mcp.json` to include all 16 Python tools, update version to `1.3.2`, and either remove Node.js-only tools or clearly document the dual-server architecture.

### F2 — High: Node.js MCP server auto-connects on import

Line 145-146 of `mcp-server/src/index.ts`:
```ts
const transport = new StdioServerTransport();
await server.connect(transport);
```
This causes the server to start on module import, producing side effects when imported for testing, validation, or tooling. A standard MCP server should expose connection from a function, not as a top-level side effect.

**Impact**: Cannot import the Node.js server module without connecting. Tests and tooling that import this module will hang.

**Recommendation**: Wrap in an async `main()` function and use `if (import.meta.url === ...)` or similar guard.

### F3 — High: Node.js MCP server has no security hardening

The Node.js server has zero error handling, no rate limiting, no secret redaction, and no retry logic. Compare: the Python MCP server catches specific exceptions, redacts secrets from error messages, and respects Retry-After headers.

**Impact**: If credentials were ever passed to the Node.js server, error messages could leak secrets to MCP clients.

**Recommendation**: Add error wrapping, secret sanitization, and at minimum a generic catch-guard in the Node.js server. This is a prerequisite for adding credential-backed tools to the Node.js server.

### F4 — Low: Node.js `package.json` repository URL is wrong

`mcp-server/package.json` line 44: `"url": "git+https://github.com/CyberNativeAI/cybernative-mcp-server.git"` — but this code lives in the `agentic-connect` repo at `mcp-server/`.

**Recommendation**: Update to `agentic-connect` repo URL or create the separate repo if intended.

### F5 — Low: `.well-known/mcp.json` hardcodes `--read-only` for Python package

The Python package args include `--read-only` with no way to override. Users who want write tools must manually edit their MCP config instead of using the well-known discovery path.

**Recommendation**: Document the write-mode override in the config or add a separate non-read-only package entry.

### F6 — Info: `server.json` has no tool enumeration

The MCP Registry server descriptor lists packages but no tools. MCP registry consumers must connect to the server to discover tools, reducing discoverability.

**Recommendation**: Add a `tools` array to `server.json` matching the Python MCP tool set.

### F7 — Info: No MCP prompts support

Both servers report `prompts: false`. Not a bug — no prompt templates are defined — but prompts could improve agent onboarding.

### F8 — Low: Version skew between Node.js (`0.1.0`) and Python (`1.3.2`)

The two servers share the same `"cybernative"` name but different versions. Makes it unclear to users which version they're getting.

**Recommendation**: Either bump Node.js to `1.3.2` for parity, or clearly document the version split and the scope difference between the two servers.

## Summary

| Dimension | Rating | Notes |
|-----------|--------|-------|
| Python MCP bridge | **Strong** | Bridge surface clean, 16 tools mapped, secret sanitization, read-only enforcement |
| Python MCP tool coverage | **Excellent** | All 16 CyberNativeClient methods have MCP tool definitions with proper inputSchema |
| Node.js MCP server | **Minimal** | 2 discovery tools + 2 resources, no hardening, auto-connect on import |
| Registry alignment | **Needs work** | `.well-known/mcp.json` incomplete, version mismatch, write tools absent |
| Test coverage | **Excellent** | 199 tests, all passing. 4 new MCP integration test files added (CYB-999584) |
| Tool<->method drift | **None** | `_ce_skill_validate.py`, `--validate` full and read-only all confirm zero drift |

**Bottom line**: The Python MCP bridge and tool surface are in excellent shape — zero drift, strong security, comprehensive tests. The main concerns are the incomplete `.well-known/mcp.json` registry listing (F1), the Node.js server's auto-connect pattern (F2) and lack of hardening (F3). These are registration and packaging issues, not code quality issues.

**Priority action items**:

1. **F1 (Medium)**: Fix `.well-known/mcp.json` — add missing write tools, correct version, sync both copies.
2. **F3 (High)**: Add error handling and secret sanitization to Node.js MCP server.
3. **F2 (High)**: Fix Node.js server auto-connect on import.
4. **F4 (Low)**: Fix Node.js `package.json` repository URL.
5. **F5 (Low)**: Document write-mode MCP config or add non-read-only package entry.
6. **F8 (Low)**: Bump Node.js server version to match Python `1.3.2` or document the split.
