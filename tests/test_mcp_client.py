"""Tests: MCP client SSE extraction and error handling."""

from __future__ import annotations

import pytest

from app.services.mcp_client import MCPClient, MCPClientError, _extract_sse_payload


def test_extract_sse_payload_returns_last_json():
    """SSE responses contain multiple data: lines; we want the last JSON one."""
    body = """event: message
data: {"jsonrpc": "2.0", "id": "1", "result": {"content": [{"type": "text", "text": "{\\"ok\\": true}"}]}}

event: message
data: {"jsonrpc": "2.0", "id": "2", "result": {"content": [{"type": "text", "text": "{\\"ok\\": false}"}]}}
"""
    result = _extract_sse_payload(body)
    assert result["id"] == "2"
    assert "result" in result


def test_extract_sse_payload_handles_empty_body():
    """An empty SSE body should return an error dict, not raise."""
    result = _extract_sse_payload("")
    assert "error" in result


def test_extract_sse_payload_handles_invalid_json():
    """If the data line is not JSON, return an error."""
    body = "data: not valid json\n\n"
    result = _extract_sse_payload(body)
    assert "error" in result


def test_mcp_client_error_carries_status_and_payload():
    """MCPClientError should preserve status and payload for debugging."""
    err = MCPClientError("transport failed", status=503, payload={"why": "timeout"})
    assert err.status == 503
    assert err.payload == {"why": "timeout"}
    assert "transport failed" in str(err)


@pytest.mark.asyncio
async def test_mcp_client_requires_open_context():
    """Calling a tool without opening the client should raise."""
    client = MCPClient(base_url="http://localhost:8000", token="test")
    with pytest.raises(MCPClientError, match="client not opened"):
        await client.assign_checkins()


def test_mcp_client_singleton_state_isolation():
    """Each MCPClient should be independent (no shared state)."""
    a = MCPClient(base_url="http://a:8000", token="t1")
    b = MCPClient(base_url="http://b:8000", token="t2")
    assert a.base_url != b.base_url
    assert a.token != b.token
