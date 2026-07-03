"""Tests: HTTP retry helper."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.utils.http_retry import (
    _compute_delay,
    _parse_retry_after,
    fetch_with_retry,
)


def test_compute_delay_increases_with_attempts():
    """The delay should increase exponentially with the attempt number."""
    d1 = _compute_delay(1, base_delay=1.0, max_delay=10.0)
    d2 = _compute_delay(2, base_delay=1.0, max_delay=10.0)
    d3 = _compute_delay(3, base_delay=1.0, max_delay=10.0)

    # With jitter, d2 should be roughly 2x d1, d3 roughly 4x d1
    assert d2 > d1
    assert d3 > d2


def test_compute_delay_capped_at_max():
    """The delay should never exceed max_delay."""
    delay = _compute_delay(10, base_delay=1.0, max_delay=5.0)
    # jitter is 0.75-1.25x, so max is 5.0 * 1.25 = 6.25
    assert delay <= 6.25


def test_parse_retry_after_seconds():
    """_parse_retry_after should parse integer seconds."""
    assert _parse_retry_after("5") == 5.0
    assert _parse_retry_after("0") == 0.0


def test_parse_retry_after_none():
    """_parse_retry_after should return None for missing/invalid input."""
    assert _parse_retry_after(None) is None
    assert _parse_retry_after("") is None
    assert _parse_retry_after("not a number") is None


@pytest.mark.asyncio
async def test_fetch_with_retry_succeeds_on_first_attempt():
    """A successful request should return immediately without retrying."""
    mock_response = httpx.Response(200, text="OK")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_with_retry("GET", "https://example.org")

    assert result.status_code == 200
    assert mock_client.request.call_count == 1  # no retry


@pytest.mark.asyncio
async def test_fetch_with_retry_retries_on_5xx():
    """A 503 response should trigger a retry."""
    mock_503 = httpx.Response(503, text="Service Unavailable")
    mock_200 = httpx.Response(200, text="OK")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=[mock_503, mock_200])
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=AsyncMock()):
        result = await fetch_with_retry("GET", "https://example.org", max_attempts=3)

    assert result.status_code == 200
    assert mock_client.request.call_count == 2  # 1 initial + 1 retry


@pytest.mark.asyncio
async def test_fetch_with_retry_retries_on_429():
    """A 429 (rate limit) response should trigger a retry."""
    mock_429 = httpx.Response(429, text="Too Many Requests")
    mock_200 = httpx.Response(200, text="OK")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=[mock_429, mock_200])
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=AsyncMock()):
        result = await fetch_with_retry("GET", "https://example.org")

    assert result.status_code == 200
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_does_not_retry_on_4xx():
    """A 404 response should NOT trigger a retry (client error, not transient)."""
    mock_404 = httpx.Response(404, text="Not Found")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_404)
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client):
        result = await fetch_with_retry("GET", "https://example.org")

    assert result.status_code == 404
    assert mock_client.request.call_count == 1  # no retry


@pytest.mark.asyncio
async def test_fetch_with_retry_retries_on_connect_error():
    """A ConnectError should trigger a retry."""
    mock_response = httpx.Response(200, text="OK")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(
        side_effect=[httpx.ConnectError("DNS failure"), mock_response]
    )
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=AsyncMock()):
        result = await fetch_with_retry("GET", "https://example.org")

    assert result.status_code == 200
    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_exhausts_attempts_on_persistent_5xx():
    """After max_attempts, a persistent 5xx should raise HTTPStatusError."""
    mock_503 = httpx.Response(503, text="Service Unavailable")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(return_value=mock_503)
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=AsyncMock()), pytest.raises(httpx.HTTPStatusError):
        await fetch_with_retry("GET", "https://example.org", max_attempts=3)

    assert mock_client.request.call_count == 3  # 3 attempts then give up


@pytest.mark.asyncio
async def test_fetch_with_retry_exhausts_attempts_on_persistent_connect_error():
    """After max_attempts, persistent ConnectError should re-raise the last error."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=httpx.ConnectError("DNS failure"))
    mock_client.aclose = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=AsyncMock()), pytest.raises(httpx.ConnectError):
        await fetch_with_retry("GET", "https://example.org", max_attempts=2)

    assert mock_client.request.call_count == 2


@pytest.mark.asyncio
async def test_fetch_with_retry_respects_retry_after_header():
    """A Retry-After header should override the computed backoff delay."""
    mock_429 = httpx.Response(429, headers={"retry-after": "10"}, text="Too Many Requests")
    mock_200 = httpx.Response(200, text="OK")
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.request = AsyncMock(side_effect=[mock_429, mock_200])
    mock_client.aclose = AsyncMock()

    sleep_mock = AsyncMock()

    with patch("app.utils.http_retry.httpx.AsyncClient", return_value=mock_client) as _, patch("app.utils.http_retry.asyncio.sleep", new=sleep_mock):
        result = await fetch_with_retry("GET", "https://example.org")

    assert result.status_code == 200
    # The sleep call should have used 10 seconds (from Retry-After header)
    sleep_mock.assert_called_once_with(10.0)
