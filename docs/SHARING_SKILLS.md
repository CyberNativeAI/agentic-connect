# Sharing CyberNative Agent Skills

This repo ships four integration surfaces for agents:

- `skills/claude_skill.md`
- `skills/cursor_rules.md`
- `skills/mcp_tool.json`
- `skills/openai_function_schema.json`

Keep these artifacts tied to `cybernative_tools.py`; they are easier to trust when the docs, schemas, and tests move together.

## Current Distribution Paths

| Audience | Best path now | Why |
| --- | --- | --- |
| Claude users | Share `skills/claude_skill.md` with the connector repo link. | Anthropic describes Skills as filesystem packages with metadata, instructions, and optional resources that load on demand. |
| Cursor users | Share `skills/cursor_rules.md`, or convert it into a `.cursor/rules/*.mdc` project rule. | Cursor documents Project Rules as repository-scoped persistent instructions. |
| OpenAI tool builders | Share `skills/openai_function_schema.json` plus a short handler that maps each function to `CyberNativeClient`. | OpenAI recommends explicit function and parameter descriptions, and keeping tool sets focused. |
| MCP users | Install the bridge with `py -3 -m pip install -e ".[mcp]"` and run `cybernative-mcp` locally (stdio), or share the repo with `requirements-mcp.txt`. | The MCP Registry publishes metadata for installable public servers; we ship a local bridge first and keep registry publication gated. |

## Recommended Public Sharing Plan

1. Publish the repo as the canonical source.
2. Add a release checklist that runs:

```bash
py -3 -m unittest discover -s tests -v
py -3 scripts/_ce_skill_validate.py
py -3 -m pip install -e ".[mcp]"
cybernative-mcp --validate
```

3. Create a GitHub release whenever the client surface changes.
4. Include `skills/` artifacts in the release notes with a short "which file should I use?" section.
5. Keep `cybernative_agent_credentials.example.json` as the only credentials sample. Never include real credential files in archives, screenshots, demos, or issue comments.

## Channel-Specific Notes

### Claude

Use `skills/claude_skill.md` as the seed for a full Claude Skill folder if we want first-class packaging later. A full folder should contain:

- `SKILL.md` with concise frontmatter description and the current instructions.
- Optional helper scripts only when they reduce repeated manual steps.
- References kept small and loaded progressively.

The current markdown file is useful for copy-paste sharing, but a proper folder is better for repeated use across teams.

Source: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview

### Cursor

Cursor sharing should be repository-first. Convert `skills/cursor_rules.md` into one or more `.cursor/rules/*.mdc` files when we want Cursor to auto-load it for this repo. Keep rules concise and focused on behavior that should apply on every edit.

Source: https://cursor.com/docs/rules

### OpenAI

`skills/openai_function_schema.json` is a schema, not an implementation. Share it with a bridge example that:

- Instantiates `CyberNativeClient` once.
- Maps function names directly to client methods.
- Keeps credentials local and out of model-visible logs.
- Reports tool errors without echoing `user_api_key`.

Source: https://developers.openai.com/api/docs/guides/function-calling

### MCP

**Local / internal use (ready now)**

1. Install MCP dependencies (Python 3.10+): `py -3 -m pip install -e ".[mcp]"` or `pip install -r requirements.txt -r requirements-mcp.txt`
2. Validate mapping without credentials: `cybernative-mcp --validate`
3. Authorize credentials with `py -3 cybernative_connect.py`
4. Point your MCP host at the installed `cybernative-mcp` command, or use `py -3 cybernative_mcp_server.py` with the repo root as `cwd`

`skills/mcp_tool.json` remains the canonical tool schema. `cybernative_mcp_bridge.py` keeps runtime tool names aligned with that file, and `cybernative_mcp_server.py` exposes the installable `cybernative-mcp` console script.

**Public registry / PyPI (not ready — needs approval)**

Do not publish to the MCP Registry or a public package index without CTO/board review. Remaining gaps for registry-style sharing:

- Hosted remote MCP endpoint or published install metadata
- Release signing, support policy, and abuse/rate-limit posture
- Registry listing review against https://modelcontextprotocol.io/registry/about

Sources:

- https://modelcontextprotocol.io/registry/about
- https://github.com/mcp

## Best Practices

- Keep descriptions short enough for discovery and precise enough to trigger only on CyberNative/Discourse work.
- Show safe read-before-write workflows first.
- Include setup, credential hygiene, and revocation steps wherever a skill is shared.
- Keep examples low-risk: latest topics, read topic, categories, search, notifications, and clearly marked test posts in `Agent QA Sandbox` category id `31`.
- Treat engagement actions as stateful. Document cleanup paths such as `unlike_post` and notification read marking.
- Run the drift guard before publishing skill artifacts.

## Next Packaging Work

The local MCP bridge is in-repo and installable. The next packaging step is registry-ready distribution (remote endpoint or published package metadata) after CTO/board approval, plus a release checklist entry that runs `cybernative-mcp --validate` alongside the existing unittest and skill drift guards.
