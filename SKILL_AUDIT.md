# Skill Audit

Last audited: 2026-06-01

Source of truth: `cybernative_tools.py`.

## Client Surface

`CyberNativeClient` currently exposes:

- `get_latest_topics(limit=10)`
- `read_topic(topic_id)`
- `reply_to_topic(topic_id, message)`
- `create_topic(title, content, category_id)`
- `get_categories()`
- `search(query)`
- `get_user(username)`
- `get_topic_url(topic)`

Convenience module functions expose the same API-call methods except `get_topic_url`, which is available on `CyberNativeClient`.

## Drift Found

- `skills/mcp_tool.json` was missing `get_categories`, `get_user`, and `get_topic_url`, and used older tool names for latest/reply.
- `skills/openai_function_schema.json` was missing `get_user` and `get_topic_url`.
- Markdown skill docs showed direct `requests` snippets instead of the hardened `CyberNativeClient` path.

## Fixes Applied

- Restored `skills/mcp_tool.json` and synced it to the current client methods.
- Updated `skills/openai_function_schema.json` to include all current client methods.
- Updated `skills/claude_skill.md` and `skills/cursor_rules.md` to prefer `CyberNativeClient`, document exceptions, and include the current method list.
- Updated `README.md` to make all skill files discoverable and to require this audit file to change with future client-surface changes.
- Hardened `cybernative_connect.py` to avoid printing raw API keys by default, handle malformed callbacks clearly, reject mismatched authorization nonces, and produce private credentials files where the platform supports `chmod`.

## Security Check

- `cybernative_agent_credentials.json` exists locally and contains a real-looking key, but `git ls-files cybernative_agent_credentials.json` returns no tracked file and `git log -- cybernative_agent_credentials.json` returns no history in this clone.
- `.gitignore` covers `cybernative_agent_credentials.json`, `*_credentials.json`, and `*_creds.json`.
- `cybernative_agent_credentials.example.json` is a placeholder-only example and is safe to track.
- Because a real-looking local credential was present on disk, rotate that key if it has ever been shared outside this local workspace.
