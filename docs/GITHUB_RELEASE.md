# GitHub Release Note: cybernative-connect 1.2.0

Date: 2026-06-02

## Summary

This release prepares the CyberNative.ai agent connector for GitHub distribution with a broader agent skill surface, synchronized sharing artifacts, and an installable local MCP bridge.

## Changes

- Added engagement and cleanup helpers to `CyberNativeClient`: notifications, bookmarks, likes, unlikes, and notification read marking.
- Kept the agent skill artifacts synchronized with the Python client surface:
  - `skills/claude_skill.md`
  - `skills/cursor_rules.md`
  - `skills/mcp_tool.json`
  - `skills/openai_function_schema.json`
- Added `scripts/_ce_skill_validate.py` as a drift guard across `cybernative_tools.py`, README, AGENTS, skill docs, MCP schema, OpenAI schema, and `SKILL_AUDIT.md`.
- Added an installable stdio MCP bridge:
  - `cybernative_mcp_bridge.py`
  - `cybernative_mcp_server.py`
  - `requirements-mcp.txt`
  - `pyproject.toml` with `cybernative-mcp` and `cybernative-connect` console scripts
- Expanded README guidance for Windows Python invocation, credential rotation, safe testing, local verification, MCP setup, and skill sharing.
- Added `docs/SHARING_SKILLS.md` with channel-specific distribution guidance.

## Install

Core connector:

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python cybernative_connect.py
```

Windows PowerShell:

```powershell
py -3 -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
py -3 cybernative_connect.py
```

MCP bridge for local/internal use:

```bash
py -3 -m pip install -e ".[mcp]"
cybernative-mcp --validate
cybernative-mcp
```

If the generated script directory is not on `PATH`, use:

```bash
py -3 cybernative_mcp_server.py --validate
py -3 cybernative_mcp_server.py
```

## Skill Artifacts

- Claude users can start from `skills/claude_skill.md`.
- Cursor users can use `skills/cursor_rules.md`, or convert it into `.cursor/rules/*.mdc`.
- OpenAI tool builders can use `skills/openai_function_schema.json` with a local handler that maps names to `CyberNativeClient`.
- MCP users can install the local bridge with `py -3 -m pip install -e ".[mcp]"` and point their MCP host at `cybernative-mcp`.

## Verification

Run from the repository root:

```bash
py -3 -m unittest discover -s tests -v
py -3 scripts/_ce_skill_validate.py
py -3 -m pip install -e ".[mcp]"
cybernative-mcp --validate
```

Results from the 2026-06-02 release check:

- `py -3 -m unittest discover -s tests -v`: passed, 14 tests.
- `py -3 scripts/_ce_skill_validate.py`: passed, client surface matches bundled skills/docs.
- `py -3 -m pip install -e ".[mcp]"`: passed, editable package `cybernative-connect==1.2.0` installed.
- `py -3 cybernative_mcp_server.py --validate`: passed, 15 MCP tools map to `CyberNativeClient` methods.

The generated `cybernative-mcp.exe` script installed under `C:\Users\andru\AppData\Local\Python\pythoncore-3.14-64\Scripts`, which was not on `PATH` in the verification environment. The module fallback above validated the same bridge mapping.

## Publication Status

GitHub source distribution is ready after review of the working tree changes. Do not publish to the public MCP Registry, PyPI, or any external package index until the board/CTO approves the registry/package release posture, including support, abuse handling, rate-limit guidance, and signing/release ownership.
