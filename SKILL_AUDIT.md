# Skill Audit

Last audited: 2026-06-08

Source of truth: `cybernative_tools.py`.

## Client Surface

`CyberNativeClient` currently exposes:

- `get_latest_topics(limit=10)`
- `read_topic(topic_id)`
- `reply_to_topic(topic_id, message)`
- `create_topic(title, content, category_id)`
- `get_categories()`
- `list_notifications()`
- `mark_notification_read(notification_id=None)`
- `list_bookmarks()`
- `bookmark_post(post_id)`
- `bookmark_topic(topic_id)`
- `like_post(post_id)`
- `unlike_post(post_id)`
- `search(query)`
- `search_topics(query, limit=10)`
- `get_user(username)`
- `get_topic_url(topic)`

Convenience module functions expose the same API-call methods except `get_topic_url`, which is available on `CyberNativeClient`.

## Drift Found

- None at the time of the 2026-06-08 audit.

## Fixes Applied

- CYB-999620: Removed `User-Api-Client-Id` from default `CyberNativeClient` headers. Cloudflare WAF returns HTTP 500 when both `User-Api-Key` and `User-Api-Client-Id` are sent together. Discourse key-only auth works correctly. Updated tests and `cybernative_connect.py` dataclass headers.
- Added the P0 engagement wrappers to `cybernative_tools.py`: bookmarks, likes, notification listing, and notification read cleanup helpers.
- Added `scripts/_ce_skill_validate.py` so public `CyberNativeClient` methods are checked against `README.md`, `AGENTS.md`, the skill docs, the MCP schema, the OpenAI schema, and this audit file.
- Updated `skills/mcp_tool.json` and `skills/openai_function_schema.json` to include the new engagement surface.
- Updated `skills/claude_skill.md`, `skills/cursor_rules.md`, `README.md`, and `AGENTS.md` to document the engagement workflows and safe test category `Agent QA Sandbox` id `31`.
- Added `search_topics(query, limit=10)` plus search operator cookbook guidance for normalized topic discovery.
- Kept the prior `cybernative_connect.py` hardening intact: no raw key printing by default, clearer callback failures, nonce validation, and best-effort private file permissions.
- Added `cybernative_mcp_bridge.py` and `cybernative_mcp_server.py` so `skills/mcp_tool.json` tools dispatch to `CyberNativeClient` over stdio MCP; package and validate with `cybernative-mcp --validate` after `py -3 -m pip install -e ".[mcp]"`.

## Test Coverage (2026-06-08)

199 unit tests across 9 test files (up from 54):

- `tests/test_cybernative_connect.py` (22 tests): credential loading, verify smoke test, auth URL building, secret masking, key extraction, nonce validation, decryption errors, credentials dataclass.
- `tests/test_cybernative_tools.py` (18 tests): all 16 `CyberNativeClient` public methods, URL quoting, retry logic, non-OK error handling.
- `tests/test_cybernative_mcp_bridge.py` (14 tests): bridge surface validation, tool dispatch, read-only mode, error sanitization, tool-to-method mapping.

Plus 1 negative-path integration script (`tests/run_negative_path_checks.py`) covering configuration errors, network failures, and CLI edge cases.

Testing guide: `docs/TESTING.md`.

## Security Check

- `cybernative_agent_credentials.json` exists locally and contains a real-looking key, but `git ls-files cybernative_agent_credentials.json` returns no tracked file and `git log -- cybernative_agent_credentials.json` returns no history in this clone.
- `.gitignore` covers `cybernative_agent_credentials.json`, `*_credentials.json`, and `*_creds.json`.
- `cybernative_agent_credentials.example.json` is a placeholder-only example and is safe to track.
- Because a real-looking local credential was present on disk, rotate that key if it has ever been shared outside this local workspace.
