"""MCP 服务端协议测试。"""

import json

import pytest

import mcp_server


@pytest.mark.asyncio
async def test_initialize_handshake() -> None:
    response = await mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {}},
        }
    )
    assert response is not None
    result = response["result"]
    assert result["protocolVersion"] == mcp_server.PROTOCOL_VERSION
    assert result["serverInfo"]["name"] == "dafeiyu-workbench"
    assert "tools" in result["capabilities"]


@pytest.mark.asyncio
async def test_initialized_notification_has_no_response() -> None:
    response = await mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert response is None


@pytest.mark.asyncio
async def test_tools_list_shape() -> None:
    response = await mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    tools = response["result"]["tools"]
    names = {item["name"] for item in tools}
    assert names == {"merge_documents", "find_references", "rewrite_style", "deai_check"}
    for tool in tools:
        assert tool["description"]
        assert tool["inputSchema"]["type"] == "object"


@pytest.mark.asyncio
async def test_unknown_tool_returns_error() -> None:
    response = await mcp_server.handle(
        {"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "nope", "arguments": {}}}
    )
    assert response["error"]["code"] == -32602


@pytest.mark.asyncio
async def test_unknown_method_returns_error() -> None:
    response = await mcp_server.handle({"jsonrpc": "2.0", "id": 4, "method": "wat"})
    assert response["error"]["code"] == -32601


@pytest.mark.asyncio
async def test_call_deai_check() -> None:
    response = await mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 5,
            "method": "tools/call",
            "params": {
                "name": "deai_check",
                "arguments": {"text": "首先，值得注意的是——这个方法非常有效。"},
            },
        }
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert "score" in payload
    assert isinstance(payload["issues"], list)
    assert response["result"]["isError"] is False


@pytest.mark.asyncio
async def test_call_merge_documents() -> None:
    response = await mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "tools/call",
            "params": {
                "name": "merge_documents",
                "arguments": {
                    "title": "合并稿",
                    "documents": [
                        {"title": "绪论", "content": "# 一、绪论\n\n这是绪论内容，介绍研究背景。\n"},
                        {"title": "方法", "content": "# 二、方法\n\n这是方法内容，说明技术路线。\n"},
                    ],
                },
            },
        }
    )
    payload = json.loads(response["result"]["content"][0]["text"])
    assert payload["stats"]["sections"] == 2
    assert "合并稿" in payload["markdown"]


@pytest.mark.asyncio
async def test_tool_failure_is_reported_not_raised() -> None:
    response = await mcp_server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "merge_documents", "arguments": {"documents": []}},
        }
    )
    assert response["result"]["isError"] is True
    assert "不能为空" in response["result"]["content"][0]["text"]
