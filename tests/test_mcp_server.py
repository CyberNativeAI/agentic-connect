import json
from unittest.mock import MagicMock, patch

import cybernative_mcp_server


def test_mcp_server_registers_expected_tools():
    tools = cybernative_mcp_server.mcp._tool_manager._tools  # noqa: SLF001
    names = set(tools.keys())
    expected = {
        "cybernative_get_latest",
        "cybernative_read_topic",
        "cybernative_reply",
        "cybernative_create_topic",
        "cybernative_search",
        "cybernative_edit_post",
        "cybernative_delete_post",
        "cybernative_remove_bookmark",
    }
    assert expected.issubset(names)


@patch("cybernative_mcp_server.CyberNativeClient")
def test_get_latest_tool_returns_json(mock_client_cls):
    mock_client = MagicMock()
    mock_client.get_latest_topics.return_value = [{"id": 1, "title": "Hello"}]
    mock_client_cls.return_value = mock_client

    tools = cybernative_mcp_server.mcp._tool_manager._tools  # noqa: SLF001
    result = tools["cybernative_get_latest"].fn(limit=1)

    assert json.loads(result) == [{"id": 1, "title": "Hello"}]
    mock_client.get_latest_topics.assert_called_once_with(limit=1)
