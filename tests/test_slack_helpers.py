"""Tests: Slack helpers (with mocked AsyncWebClient)."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from slack_sdk.errors import SlackApiError
from slack_sdk.web.async_client import AsyncWebClient

from app.utils.slack_helpers import (
    clear_caches,
    get_bot_user_id,
    get_cellule_crise_channel_id,
    get_channel_by_name,
    get_sector_channel_id,
    get_user_info,
    open_dm,
    post_dm,
    post_to_cellule_crise,
    post_to_sector,
)


@pytest.fixture(autouse=True)
def _reset_caches():
    """Clear all caches before each test."""
    clear_caches()
    yield
    clear_caches()


@pytest.mark.asyncio
async def test_get_user_info_caches_results():
    """Two calls to get_user_info should hit the Slack API only once."""
    client = AsyncMock(spec=AsyncWebClient)
    client.users_info = AsyncMock(
        return_value={"user": {"profile": {"real_name": "Marie Dupont", "display_name": "Marie"}}}
    )

    info1 = await get_user_info(client, "U001")
    info2 = await get_user_info(client, "U001")

    assert info1["display_name"] == "Marie"
    assert info2["display_name"] == "Marie"
    assert client.users_info.call_count == 1  # cached


@pytest.mark.asyncio
async def test_get_user_info_returns_fallback_on_error():
    """On SlackApiError, get_user_info should return a fallback dict."""
    client = AsyncMock(spec=AsyncWebClient)
    client.users_info = AsyncMock(
        side_effect=SlackApiError("user_not_found", {"error": "user_not_found"})
    )

    info = await get_user_info(client, "U_UNKNOWN")
    assert info["id"] == "U_UNKNOWN"
    assert info["display_name"] == "U_UNKNOWN"


@pytest.mark.asyncio
async def test_get_channel_by_name_finds_existing_channel():
    """get_channel_by_name should return the channel ID for a known name."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(
        return_value={
            "channels": [
                {"id": "C001", "name": "cellule-crise"},
                {"id": "C002", "name": "secteur-1"},
            ]
        }
    )

    channel_id = await get_channel_by_name(client, "cellule-crise")
    assert channel_id == "C001"


@pytest.mark.asyncio
async def test_get_channel_by_name_returns_none_for_unknown():
    """Unknown channel names should return None."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(return_value={"channels": []})

    channel_id = await get_channel_by_name(client, "nonexistent")
    assert channel_id is None


@pytest.mark.asyncio
async def test_get_channel_by_name_strips_hash_prefix():
    """A leading # in the name should be stripped before lookup."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(
        return_value={"channels": [{"id": "C001", "name": "cellule-crise"}]}
    )

    channel_id = await get_channel_by_name(client, "#cellule-crise")
    assert channel_id == "C001"


@pytest.mark.asyncio
async def test_get_sector_channel_id_uses_config_prefix():
    """get_sector_channel_id should use the configured sector prefix."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(
        return_value={"channels": [{"id": "C011", "name": "secteur-11"}]}
    )

    channel_id = await get_sector_channel_id(client, 11)
    assert channel_id == "C011"


@pytest.mark.asyncio
async def test_get_cellule_crise_channel_id_uses_env_first():
    """If SLACK_CELLULE_CRISE_CHANNEL_ID is set, it should be used directly."""
    import os

    os.environ["SLACK_CELLULE_CRISE_CHANNEL_ID"] = "C_FROM_ENV"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    client = AsyncMock(spec=AsyncWebClient)
    channel_id = await get_cellule_crise_channel_id(client)
    assert channel_id == "C_FROM_ENV"

    del os.environ["SLACK_CELLULE_CRISE_CHANNEL_ID"]
    _config_mod.get_config.cache_clear()


@pytest.mark.asyncio
async def test_open_dm_caches_channel_id():
    """Two calls to open_dm should hit the Slack API only once."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_open = AsyncMock(
        return_value={"channel": {"id": "DM001"}}
    )

    dm1 = await open_dm(client, "U001")
    dm2 = await open_dm(client, "U001")

    assert dm1 == "DM001"
    assert dm2 == "DM001"
    assert client.conversations_open.call_count == 1


@pytest.mark.asyncio
async def test_open_dm_returns_none_on_error():
    """On SlackApiError, open_dm should return None."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_open = AsyncMock(
        side_effect=SlackApiError("api_error", {"error": "api_error"})
    )

    dm = await open_dm(client, "U_BAD")
    assert dm is None


@pytest.mark.asyncio
async def test_post_dm_returns_message_ts_on_success():
    """post_dm should return the message timestamp on success."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_open = AsyncMock(return_value={"channel": {"id": "DM001"}})
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "123.456"})

    ts = await post_dm(client, "U001", text="Hello")
    assert ts == "123.456"


@pytest.mark.asyncio
async def test_post_dm_returns_none_when_dm_open_fails():
    """post_dm should return None if the DM can't be opened."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_open = AsyncMock(
        side_effect=SlackApiError("api_error", {"error": "api_error"})
    )

    ts = await post_dm(client, "U_BAD", text="Hello")
    assert ts is None


@pytest.mark.asyncio
async def test_post_to_sector_returns_ts_on_success():
    """post_to_sector should resolve the channel and post the message."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(
        return_value={"channels": [{"id": "C011", "name": "secteur-11"}]}
    )
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "789.012"})

    ts = await post_to_sector(client, 11, text="Check-in OK")
    assert ts == "789.012"


@pytest.mark.asyncio
async def test_post_to_sector_returns_none_for_unknown_channel():
    """post_to_sector should return None if the sector channel doesn't exist."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(return_value={"channels": []})

    ts = await post_to_sector(client, 99, text="Hello")
    assert ts is None


@pytest.mark.asyncio
async def test_post_to_cellule_crise_returns_ts_on_success():
    """post_to_cellule_crise should post in the cellule-crise channel."""
    client = AsyncMock(spec=AsyncWebClient)
    client.conversations_list = AsyncMock(
        return_value={"channels": [{"id": "C001", "name": "cellule-crise"}]}
    )
    client.chat_postMessage = AsyncMock(return_value={"ok": True, "ts": "999.999"})

    ts = await post_to_cellule_crise(client, text="Alerte canicule")
    assert ts == "999.999"


@pytest.mark.asyncio
async def test_get_bot_user_id_returns_id_on_success():
    """get_bot_user_id should return the bot's Slack user ID."""
    client = AsyncMock(spec=AsyncWebClient)
    client.auth_test = AsyncMock(return_value={"user_id": "U_VIGIE_BOT"})

    bot_id = await get_bot_user_id(client)
    assert bot_id == "U_VIGIE_BOT"


@pytest.mark.asyncio
async def test_get_bot_user_id_returns_none_on_error():
    """get_bot_user_id should return None on auth failure."""
    client = AsyncMock(spec=AsyncWebClient)
    client.auth_test = AsyncMock(
        side_effect=SlackApiError("api_error", {"error": "api_error"})
    )

    bot_id = await get_bot_user_id(client)
    assert bot_id is None


def test_clear_caches_does_not_raise():
    """clear_caches should be safe to call on an empty cache."""
    clear_caches()
    clear_caches()  # idempotent
