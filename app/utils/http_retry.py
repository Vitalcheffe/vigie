"""
Vigie — HTTP retry helper.

Wraps httpx calls with exponential backoff retry for transient failures
(5xx, 429, network errors). Used by all external API calls to make
Vigie resilient to flaky networks and rate limits.

Strategy:
  - Retry on: 5xx, 429, httpx.ConnectError, httpx.ReadTimeout
  - Do NOT retry on: 4xx (except 429), successful responses
  - Backoff: base_delay * 2^attempt (jittered ±25%)
  - Max attempts: 3 (default)
  - Max total wait: ~7 seconds (1 + 2 + 4)

Public API:
  - fetch_with_retry(method, url, **kwargs) -> httpx.Response
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from app.utils.logging import get_logger

log = get_logger("vigie.http_retry")

# Default retry config
DEFAULT_MAX_ATTEMPTS = 3
DEFAULT_BASE_DELAY = 1.0  # seconds
DEFAULT_MAX_DELAY = 8.0  # seconds

# Status codes that should trigger a retry
_RETRYABLE_STATUS = {429, 500, 502, 503, 504}

# Exception types that should trigger a retry
_RETRYABLE_EXCEPTIONS = (
    httpx.ConnectError,
    httpx.ReadTimeout,
    httpx.WriteTimeout,
    httpx.PoolTimeout,
    httpx.ConnectTimeout,
)


async def fetch_with_retry(
    method: str,
    url: str,
    *,
    client: httpx.AsyncClient | None = None,
    max_attempts: int = DEFAULT_MAX_ATTEMPTS,
    base_delay: float = DEFAULT_BASE_DELAY,
    max_delay: float = DEFAULT_MAX_DELAY,
    **kwargs: Any,
) -> httpx.Response:
    """
    Execute an HTTP request with exponential backoff retry.

    Args:
        method: HTTP method (GET, POST, ...)
        url: Target URL
        client: Optional pre-configured AsyncClient. If None, a fresh
               client is created and closed per call (less efficient).
        max_attempts: Maximum number of attempts (including the first)
        base_delay: Base delay in seconds (doubles each retry)
        max_delay: Maximum delay between retries (cap)
        **kwargs: Passed to client.request()

    Returns:
        httpx.Response on success (status < 400 OR non-retryable 4xx)

    Raises:
        httpx.HTTPStatusError: If the final attempt returns a 5xx/429
        httpx.HTTPError: If all attempts fail with network errors
    """
    own_client = client is None
    if own_client:
        client = httpx.AsyncClient(timeout=30.0)

    try:
        last_exc: Exception | None = None
        last_response: httpx.Response | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                response = await client.request(method, url, **kwargs)

                # Success or non-retryable error
                if response.status_code < 400 or response.status_code not in _RETRYABLE_STATUS:
                    if attempt > 1:
                        log.info(
                            "http_retry.succeeded_after_retry",
                            url=url,
                            method=method,
                            attempts=attempt,
                            status=response.status_code,
                        )
                    return response

                # Retryable status code
                last_response = response
                retry_after = _parse_retry_after(response.headers.get("retry-after"))
                if attempt < max_attempts:
                    delay = retry_after if retry_after else _compute_delay(attempt, base_delay, max_delay)
                    log.warning(
                        "http_retry.retryable_status",
                        url=url,
                        method=method,
                        status=response.status_code,
                        attempt=attempt,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    log.error(
                        "http_retry.exhausted_status",
                        url=url,
                        method=method,
                        status=response.status_code,
                        attempts=attempt,
                    )
                    # Raise an HTTPStatusError. The response may not have
                    # a request attached (e.g., mocked in tests).
                    try:
                        req = response.request
                    except RuntimeError:
                        req = httpx.Request(method, url)
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code} after {attempt} attempts",
                        request=req,
                        response=response,
                    )

            except _RETRYABLE_EXCEPTIONS as e:
                last_exc = e
                if attempt < max_attempts:
                    delay = _compute_delay(attempt, base_delay, max_delay)
                    log.warning(
                        "http_retry.retryable_exception",
                        url=url,
                        method=method,
                        error=type(e).__name__,
                        attempt=attempt,
                        delay=delay,
                    )
                    await asyncio.sleep(delay)
                else:
                    log.error(
                        "http_retry.exhausted_exception",
                        url=url,
                        method=method,
                        error=str(e),
                        attempts=attempt,
                    )
                    raise

        # Should not reach here, but just in case
        if last_response is not None:
            last_response.raise_for_status()
            return last_response
        if last_exc is not None:
            raise last_exc
        raise RuntimeError("fetch_with_retry: unreachable state")

    finally:
        if own_client:
            await client.aclose()


def _compute_delay(attempt: int, base_delay: float, max_delay: float) -> float:
    """Compute the delay for the given attempt with jitter.

    delay = min(max_delay, base_delay * 2^(attempt-1)) * (0.75 + 0.5 * random)
    """
    raw = base_delay * (2 ** (attempt - 1))
    capped = min(raw, max_delay)
    jitter = 0.75 + 0.5 * random.random()  # 0.75 to 1.25
    return capped * jitter


def _parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value (seconds or HTTP date)."""
    if not value:
        return None
    # Try integer seconds first
    try:
        return float(value)
    except ValueError:
        pass
    # Try HTTP date format
    try:
        from datetime import UTC, datetime
        from email.utils import parsedate_to_datetime

        target = parsedate_to_datetime(value)
        now = datetime.now(UTC)
        delta = (target - now).total_seconds()
        return max(0.0, delta)
    except (ValueError, TypeError, Exception):
        return None
