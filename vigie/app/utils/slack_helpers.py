"""
Vigie — Slack helper utilities.

Wraps common Slack Web API calls behind typed helpers so handlers stay
small and testable. Includes:
  - get_user_info(client, user_id) — cached user lookup
  - get_channel_by_name(client, name) — resolve channel name to ID
  - post_to_sector(client, sector, blocks) — post a message in #secteur-N
  - post_to_cellule_crise(client, blocks) — post in #cellule-crise
  - open_dm(client, user_id) — open a DM channel and return its ID
  - publish_canvas(client, channel_id, blocks) — update the cellule canvas
"""

from __future__ import annotations

from functools import lru_cache
from typing import Any

from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.utils.config import get_config
from app.utils.logging import get_logger

log = get_logger("vigie.utils.slack_helpers")


# ============================================================
# User info (cached for 5 min)
# ============================================================

_user_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_USER_CACHE_TTL = 300.0


async def get_user_info(client: AsyncWebClient, user_id: str) -> dict[str, Any]:
    """Return Slack user info (name, real_name, email if visible). Cached 5 min."""
    import time

    now = time.time()
    cached = _user_cache.get(user_id)
    if cached and (now - cached[0]) < _USER_CACHE_TTL:
        return cached[1]

    try:
        resp = await client.users_info(user=user_id)
        info = resp.get("user", {}).get("profile", {})
        info["id"] = user_id
        info["display_name"] = info.get("display_name") or info.get("real_name") or user_id
        _user_cache[user_id] = (now, info)
        return info
    except SlackApiError as e:
        log.warning("slack.user_info_failed", user=user_id, error=e.response.get("error"))
        return {"id": user_id, "display_name": user_id}


# ============================================================
# Channel resolution
# ============================================================

@lru_cache(maxsize=128)
def _channel_cache_key(workspace: str, name: str) -> str:
    return f"{workspace}:{name}"


async def get_channel_by_name(client: AsyncWebClient, name: str) -> str | None:
    """Find a public channel's ID by name. Returns None if not found."""
    cfg = get_config()
    name = name.lstrip("#")
    cache_key = _channel_cache_key(cfg.slack.workspace_name, name)
    if cache_key in _channel_id_cache:
        return _channel_id_cache[cache_key]

    try:
        resp = await client.conversations_list(types="public_channel", limit=200)
        for ch in resp.get("channels", []):
            if ch["name"] == name:
                _channel_id_cache[cache_key] = ch["id"]
                return ch["id"]
    except SlackApiError as e:
        log.warning("slack.channel_list_failed", error=e.response.get("error"))
    return None


_channel_id_cache: dict[str, str] = {}


async def get_sector_channel_id(client: AsyncWebClient, sector: int | str) -> str | None:
    """Get the #secteur-N channel ID for a sector number."""
    cfg = get_config()
    name = f"{cfg.slack.secteur_prefix}{sector}"
    return await get_channel_by_name(client, name)


async def get_voisins_channel_id(client: AsyncWebClient, sector: int | str) -> str | None:
    """Get the #voisins-N channel ID for a sector number."""
    cfg = get_config()
    name = f"{cfg.slack.voisins_prefix}{sector}"
    return await get_channel_by_name(client, name)


async def get_cellule_crise_channel_id(client: AsyncWebClient) -> str | None:
    """Get the #cellule-crise channel ID (from env or by name lookup)."""
    cfg = get_config()
    if cfg.slack.cellule_crise_channel_id:
        return cfg.slack.cellule_crise_channel_id
    return await get_channel_by_name(client, "cellule-crise")


# ============================================================
# Posting helpers
# ============================================================

async def post_to_sector(
    client: AsyncWebClient,
    sector: int | str,
    *,
    text: str = "",
    blocks: list[dict[str, Any]] | None = None,
    thread_ts: str | None = None,
) -> str | None:
    """Post a message in #secteur-N. Returns the message timestamp."""
    channel_id = await get_sector_channel_id(client, sector)
    if not channel_id:
        log.warning("slack.post_sector_no_channel", sector=sector)
        return None
    return await _post(client, channel_id, text=text, blocks=blocks, thread_ts=thread_ts)


async def post_to_cellule_crise(
    client: AsyncWebClient,
    *,
    text: str = "",
    blocks: list[dict[str, Any]] | None = None,
    thread_ts: str | None = None,
) -> str | None:
    """Post a message in #cellule-crise. Returns the message timestamp."""
    channel_id = await get_cellule_crise_channel_id(client)
    if not channel_id:
        log.warning("slack.post_cellule_no_channel")
        return None
    return await _post(client, channel_id, text=text, blocks=blocks, thread_ts=thread_ts)


async def _post(
    client: AsyncWebClient,
    channel_id: str,
    *,
    text: str,
    blocks: list[dict[str, Any]] | None,
    thread_ts: str | None,
) -> str | None:
    try:
        kwargs: dict[str, Any] = {"channel": channel_id, "text": text or "Vigie"}
        if blocks:
            kwargs["blocks"] = blocks
        if thread_ts:
            kwargs["thread_ts"] = thread_ts
        resp = await client.chat_postMessage(**kwargs)
        return resp.get("ts")
    except SlackApiError as e:
        log.error("slack.post_failed", channel=channel_id, error=e.response.get("error"))
        return None


# ============================================================
# DM helpers
# ============================================================

_dm_cache: dict[str, str] = {}


async def open_dm(client: AsyncWebClient, user_id: str) -> str | None:
    """Open a DM channel with a user. Returns the channel ID (cached)."""
    if user_id in _dm_cache:
        return _dm_cache[user_id]
    try:
        resp = await client.conversations_open(users=user_id)
        channel_id = resp.get("channel", {}).get("id")
        if channel_id:
            _dm_cache[user_id] = channel_id
        return channel_id
    except SlackApiError as e:
        log.warning("slack.dm_open_failed", user=user_id, error=e.response.get("error"))
        return None


async def post_dm(
    client: AsyncWebClient,
    user_id: str,
    *,
    text: str = "",
    blocks: list[dict[str, Any]] | None = None,
) -> str | None:
    """Open (if needed) and post to a DM with a user. Returns message ts."""
    channel_id = await open_dm(client, user_id)
    if not channel_id:
        return None
    return await _post(client, channel_id, text=text, blocks=blocks, thread_ts=None)


# ============================================================
# Canvas
# ============================================================

async def publish_canvas(
    client: AsyncWebClient,
    *,
    channel_id: str,
    title: str,
    blocks: list[dict[str, Any]],
) -> bool:
    """
    Publish or update a Slack Canvas in a channel.

    Slack Canvas API: client.canvas_edit or via chat_postMessage with
    metadata. The exact endpoint depends on the workspace's Canvas
    availability — this is a best-effort wrapper.
    """
    try:
        # Try the canvas_create endpoint (if available in this SDK version)
        if hasattr(client, "canvas_create"):
            await client.canvas_create(  # type: ignore[attr-defined]
                channel_id=channel_id,
                document={
                    "type": "markdown",
                    "title": title,
                    "blocks": blocks,
                },
            )
            log.info("slack.canvas_published", channel=channel_id, title=title)
            return True
        else:
            log.warning("slack.canvas_api_unavailable")
            return False
    except SlackApiError as e:
        log.warning("slack.canvas_failed", error=e.response.get("error"))
        return False


# ============================================================
# Misc
# ============================================================

async def get_bot_user_id(client: AsyncWebClient) -> str | None:
    """Return the bot's own user ID (for self-message filtering)."""
    try:
        resp = await client.auth_test()
        return resp.get("user_id")
    except SlackApiError as e:
        log.warning("slack.auth_test_failed", error=e.response.get("error"))
        return None


def clear_caches() -> None:
    """Invalidate all Slack helper caches (for tests)."""
    _user_cache.clear()
    _channel_id_cache.clear()
    _dm_cache.clear()
    _channel_cache_key.cache_clear()
