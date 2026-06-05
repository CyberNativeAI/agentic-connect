import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import cybernative_mcp_server

REPO_ROOT = Path(__file__).resolve().parents[1]


def test_mcp_server_registers_expected_tools():
    tools = cybernative_mcp_server.mcp._tool_manager._tools  # noqa: SLF001
    names = set(tools.keys())
    assert cybernative_mcp_server.FULL_TOOL_NAMES.issubset(names)


def test_read_only_mcp_excludes_write_tools():
    server = cybernative_mcp_server.build_mcp(read_only=True)
    names = set(server._tool_manager._tools.keys())  # noqa: SLF001
    assert names == cybernative_mcp_server.READ_ONLY_TOOL_NAMES
    assert not names & cybernative_mcp_server.WRITE_TOOL_NAMES


def test_validate_full_surface_passes():
    assert cybernative_mcp_server.validate_surface(read_only=False) == []


def test_validate_read_only_surface_passes():
    assert cybernative_mcp_server.validate_surface(read_only=True) == []


def test_validate_read_only_rejects_write_tools(monkeypatch):
    full_server = cybernative_mcp_server.build_mcp(read_only=False)

    def fake_build(*, read_only: bool = False):
        return full_server if read_only else full_server

    monkeypatch.setattr(cybernative_mcp_server, "build_mcp", fake_build)
    errors = cybernative_mcp_server.validate_surface(read_only=True)
    assert any("write tools" in err for err in errors)


def test_validate_full_surface_reports_missing_tools(monkeypatch):
    server = cybernative_mcp_server.build_mcp(read_only=True)

    def fake_build(*, read_only: bool = False):
        return server

    monkeypatch.setattr(cybernative_mcp_server, "build_mcp", fake_build)
    errors = cybernative_mcp_server.validate_surface(read_only=False)
    assert any("missing tools" in err for err in errors)


@patch("cybernative_mcp_server.CyberNativeClient")
def test_get_latest_tool_returns_json(mock_client_cls):
    mock_client = MagicMock()
    mock_client.get_latest_topics.return_value = [{"id": 1, "title": "Hello"}]
    mock_client_cls.return_value = mock_client

    tools = cybernative_mcp_server.mcp._tool_manager._tools  # noqa: SLF001
    result = tools["cybernative_get_latest"].fn(limit=1)

    assert json.loads(result) == [{"id": 1, "title": "Hello"}]
    mock_client.get_latest_topics.assert_called_once_with(limit=1)


def test_cli_validate_read_only_exits_zero():
    result = subprocess.run(
        [sys.executable, "cybernative_mcp_server.py", "--validate", "--read-only"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "read-only MCP surface validated" in result.stdout


def test_cli_validate_full_exits_zero():
    result = subprocess.run(
        [sys.executable, "cybernative_mcp_server.py", "--validate"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "full MCP surface validated" in result.stdout
