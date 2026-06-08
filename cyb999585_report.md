## CYB-999585 E2E Test Results: agentic-connect MCP Server Tool Suite

### Verified (all pass)

| Check | Status |
|-------|--------|
| Bridge unit tests (32 tests) | PASS |
| Tools unit tests (43 tests) | PASS |
| Bridge surface validation (full mode, 16 tools) | PASS |
| Bridge surface validation (read-only, 9 tools) | PASS |
| Drift guard (`_ce_skill_validate.py`) | PASS - surface matches docs |
| Public connectivity probe (`--probe-public`) | PASS - HTTP 200 |
| `.well-known/mcp.json` tool listing (11 tools) | ACCURATE |
| Read-only gate blocks write tools | PASS |
| Secret sanitization redacts credentials | PASS |
| All tool-to-method mappings correct | PASS |
| Node.js MCP deps install (0 vulns) | PASS |

### Tool suite inventory

**Node.js MCP server** (`@cybernative/mcp-server`):
- 2 tools: `get_cybernative_routes`, `get_agent_onboarding`
- 2 resources: `cybernative://routes`, `cybernative://llms`
- Purely informational/static — no Discourse API integration

**Python MCP server** (`cybernative-connect`, 16 tools):
- 9 read-only: get_latest_topics, read_topic, get_categories, list_notifications, list_bookmarks, search, search_topics, get_user, get_topic_url
- 7 write: reply_to_topic, create_topic, mark_notification_read, bookmark_post, bookmark_topic, like_post, unlike_post
- 0 resources, 0 prompts

### Gaps found

1. **CRITICAL: Authenticated API returns HTTP 500** — All credential-authenticated requests (`/latest.json`, `/categories.json`, `/notifications.json`, `/bookmarks.json`, `/search.json`) return HTTP 500 from cybernative.ai. Unauthenticated public probe succeeds. The credential file at `cybernative_agent_credentials.json` contains non-placeholder values (key starts `6c79`, client ID starts `wLq1`). Reproduced with direct PowerShell Invoke-WebRequest — rules out Python client.

2. **HIGH: Node.js MCP server auto-connects on import** — `dist/index.js` runs `await server.connect(transport)` at top-level (line 112). This means `require()` or `import()` always starts the stdio server, blocking any programmatic inspection. Should be guarded with `if (process.argv[1] === fileURLToPath(import.meta.url))`.

3. **HIGH: No resources in Python MCP server** — Python server exposes 16 tools but zero resources. Node.js server exposes 2 resources. Inconsistent between the two packages registered under the same `.well-known/mcp.json` name.

4. **MEDIUM: Version misalignment** — `mcp_tool.json` v1.3.2, PyPI package v1.3.2, but Node.js npm package is v0.1.0. The `.well-known/mcp.json` lists both under the same `"name": "cybernative"` entry.

5. **MEDIUM: No health check tool** — No `cybernative_health` or `cybernative_probe` tool. Users must run `--probe-public` or `--verify` manually from CLI. An MCP tool would let AI agents check connectivity before attempting operations.

6. **MEDIUM: No OAuth/login flow as MCP tool** — Credentials must be pre-configured outside of MCP. Users must run `python cybernative_connect.py` manually to get credentials. No MCP-based credential setup or re-auth flow.

7. **LOW: No prompts** — `.well-known/mcp.json` lists `"prompts": false`. Neither server provides MCP prompts (e.g., for guided onboarding or community participation templates).

8. **LOW: `get_topic_url` accepts `object` inputSchema** — The `topic` parameter is `type: "object"` in JSON Schema. Through JSON-RPC transport, topic dict serialization needs to be verified end-to-end with a real MCP client (not just dispatch_tool).

### Recommendations

- **Immediate**: Investigate HTTP 500 on authenticated requests — may be a server-side Discourse configuration or credential issue. Unblock CTO.
- **Short-term**: Add `if-guard` to Node.js MCP server to prevent auto-connect on import. Add resources to Python MCP server for consistency.
- **Backlog**: Add health check tool, OAuth tool, prompts support, version alignment, and `get_topic_url` object transport verification.

### What was tested
- Full bridge validation (both modes)
- All 75 unit tests (bridge + tools)
- Drift guard script
- Public connectivity probe (real DNS + HTTP)
- Authenticated API via direct PowerShell (ruled out Python client bug)
- E2E dispatch of all 16 MCP tools through the bridge
- Read-only mode gate
- `.well-known/mcp.json` listing accuracy
- Node.js MCP server dependency install
