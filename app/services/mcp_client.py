"""
Vigie — MCP server HTTP client.

The Bolt app uses this module to call the MCP server (which runs as a
separate process / container). All MCP tool invocations go through here
so we have a single place for auth, retries, and error handling.

The MCP server exposes a JSON-RPC 2.0 interface over streamable-http.
This client wraps the three Vigie tools (assign_checkins, record_checkin,
escalate) and provides typed Python return values.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.services.mcp_client")


class MCPClientError(Exception):
    """Raised when the MCP server returns an error or is unreachable."""

    def __init__(self, message: str, *, status: int | None = None, payload: dict | None = None):
        super().__init__(message)
        self.status = status
        self.payload = payload


class MCPClient:
    """HTTP client for the Vigie MCP server."""

    def __init__(self, base_url: str | None = None, token: str | None = None) -> None:
        cfg = get_config()
        self.base_url = (base_url or f"http://{cfg.mcp.host}:{cfg.mcp.port}").rstrip("/")
        self.token = token or cfg.mcp.server_token.get_secret_value()
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> MCPClient:
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
            },
            timeout=httpx.Timeout(30.0, connect=5.0),
        )
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _call_tool(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke an MCP tool via JSON-RPC and return the parsed result."""
        if self._client is None:
            raise MCPClientError("client not opened — use async with")

        payload = {
            "jsonrpc": "2.0",
            "id": f"vigie-{tool_name}",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
        }

        try:
            resp = await self._client.post("/mcp", json=payload)
        except httpx.HTTPError as e:
            log.error("mcp.transport_failed", tool=tool_name, error=str(e))
            raise MCPClientError(f"transport error calling {tool_name}: {e}") from e

        if resp.status_code >= 400:
            log.error("mcp.http_error", tool=tool_name, status=resp.status_code, body=resp.text[:500])
            raise MCPClientError(
                f"MCP server returned {resp.status_code}",
                status=resp.status_code,
                payload={"body": resp.text[:500]},
            )

        # MCP streamable-http returns SSE; the final "data:" line carries the JSON-RPC response.
        body = resp.text
        rpc_response = _extract_sse_payload(body) if "data:" in body else json.loads(body)

        if "error" in rpc_response:
            err = rpc_response["error"]
            log.warning("mcp.rpc_error", tool=tool_name, error=err)
            raise MCPClientError(f"RPC error from {tool_name}: {err.get('message', err)}", payload=err)

        # The result is wrapped in {result: {content: [{type: "text", text: "..."}]}}
        result = rpc_response.get("result", {})
        content = result.get("content", [])
        if not content:
            return result

        # Concatenate text parts (Vigie tools return a single JSON-encoded text part)
        text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
        joined = "\n".join(text_parts)
        try:
            return json.loads(joined)
        except json.JSONDecodeError:
            return {"raw": joined}

    # ============================================================
    # Vigie tool wrappers
    # ============================================================

    async def assign_checkins(
        self,
        volunteer_ids: list[str] | None = None,
        date: str | None = None,
        sector_filter: str | None = None,
    ) -> dict[str, Any]:
        """Assign daily check-in lists to volunteers."""
        log.debug("mcp.assign_checkins.call", date=date, sector=sector_filter)
        return await self._call_tool(
            "assign_checkins",
            {
                "volunteer_ids": volunteer_ids,
                "date": date,
                "sector_filter": sector_filter,
            },
        )

    async def record_checkin(
        self,
        beneficiary_id: str,
        volunteer_id: str,
        transcript: str,
        channel_type: str = "voice",
        detected_signals: list[str] | None = None,
    ) -> dict[str, Any]:
        """Record a volunteer's check-in return."""
        log.debug(
            "mcp.record_checkin.call",
            beneficiary=beneficiary_id,
            volunteer=volunteer_id,
            channel=channel_type,
        )
        return await self._call_tool(
            "record_checkin",
            {
                "beneficiary_id": beneficiary_id,
                "volunteer_id": volunteer_id,
                "transcript": transcript,
                "channel_type": channel_type,
                "detected_signals": detected_signals,
            },
        )

    async def escalate(
        self,
        beneficiary_id: str,
        level: int,
        triggered_by: str,
        reason: str | None = None,
        include_neighbor_referent: bool = True,
    ) -> dict[str, Any]:
        """Trigger an escalation (level 1, 2, or 3)."""
        log.info(
            "mcp.escalate.call",
            beneficiary=beneficiary_id,
            level=level,
            triggered_by=triggered_by,
        )
        return await self._call_tool(
            "escalate",
            {
                "beneficiary_id": beneficiary_id,
                "level": level,
                "triggered_by": triggered_by,
                "reason": reason,
                "include_neighbor_referent": include_neighbor_referent,
            },
        )

    # ============================================================
    # Resource reads (for dashboards)
    # ============================================================

    async def list_beneficiaries(self) -> list[dict[str, Any]]:
        """Read the full beneficiary registry."""
        result = await self._call_resource("vigie://beneficiary-registry")
        return result.get("beneficiaries", [])

    async def get_beneficiary(self, beneficiary_id: str) -> dict[str, Any] | None:
        """Read a single beneficiary by ID."""
        result = await self._call_resource(f"vigie://beneficiary-registry/{beneficiary_id}")
        if "error" in result:
            return None
        return result

    async def list_weather_alerts(self) -> list[dict[str, Any]]:
        """Read active weather alerts."""
        result = await self._call_resource("vigie://weather-alerts")
        return result.get("alerts", [])

    async def _call_resource(self, uri: str) -> dict[str, Any]:
        """Read an MCP resource by URI."""
        if self._client is None:
            raise MCPClientError("client not opened — use async with")

        payload = {
            "jsonrpc": "2.0",
            "id": "vigie-resource",
            "method": "resources/read",
            "params": {"uri": uri},
        }

        try:
            resp = await self._client.post("/mcp", json=payload)
        except httpx.HTTPError as e:
            raise MCPClientError(f"transport error reading {uri}: {e}") from e

        if resp.status_code >= 400:
            raise MCPClientError(f"MCP server returned {resp.status_code}", status=resp.status_code)

        body = resp.text
        rpc_response = _extract_sse_payload(body) if "data:" in body else json.loads(body)

        if "error" in rpc_response:
            raise MCPClientError(f"RPC error reading {uri}: {rpc_response['error']}")

        result = rpc_response.get("result", {})
        contents = result.get("contents", [])
        if not contents:
            return {}

        text = contents[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw": text}


def _extract_sse_payload(body: str) -> dict[str, Any]:
    """Extract the last JSON payload from an SSE-formatted response body."""
    last_data = None
    for line in body.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            data = line[5:].strip()
            if data:
                last_data = data
    if last_data is None:
        return {"error": "no data in SSE stream"}
    try:
        return json.loads(last_data)
    except json.JSONDecodeError as e:
        return {"error": f"invalid JSON in SSE: {e}"}
