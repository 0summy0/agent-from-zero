import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "chapter_2_5_mcp",
    ROOT / "chapters" / "stage2-agent-core" / "mcp_minimal.py",
)
mcp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mcp)


@pytest.fixture
def client():
    with mcp.MCPClient() as connection:
        yield connection


def test_chapter_module_imports():
    assert mcp.CHAPTER_ID == "2.5-mcp"
    assert callable(mcp.run_minimal_path)


def test_initialize_negotiates_protocol_and_capabilities(client):
    response = client.request(
        "initialize",
        {
            "protocolVersion": mcp.PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "smoke-test", "version": "1"},
        },
    )
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["result"]["protocolVersion"] == mcp.PROTOCOL_VERSION
    assert response["result"]["capabilities"] == {"tools": {}}
    assert response["result"]["serverInfo"]["name"] == mcp.SERVER_NAME


def test_tools_list_exposes_add_schema(client):
    response = client.request("tools/list")
    tools = response["result"]["tools"]
    assert [tool["name"] for tool in tools] == ["add"]
    assert tools[0]["inputSchema"]["required"] == ["a", "b"]


def test_tools_call_adds_numbers(client):
    response = client.request(
        "tools/call",
        {"name": "add", "arguments": {"a": 17, "b": 25}},
    )
    result = response["result"]
    assert result["isError"] is False
    assert result["content"] == [{"type": "text", "text": "42"}]


def test_unknown_method_returns_json_rpc_error(client):
    response = client.request("unknown/method")
    assert response["jsonrpc"] == "2.0"
    assert response["id"] == 1
    assert response["error"]["code"] == -32601
    assert "error" in response
    assert "result" not in response


def test_process_closes_normally(client):
    assert client.close() == 0
    assert client.returncode == 0
    assert client.process.poll() == 0


def test_minimal_path_is_serializable_and_repeatable():
    first = mcp.run_minimal_path()
    second = mcp.run_minimal_path()
    assert first == second
    assert json.loads(json.dumps(first)) == first
    assert first["closed_normally"] is True
    assert first["add_call"]["result"]["content"][0]["text"] == "42"
