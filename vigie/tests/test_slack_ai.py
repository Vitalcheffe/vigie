"""Tests: Slack AI service (with mocked OpenAI client)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.slack_ai import SlackAIService, _safe_json


def test_safe_json_parses_valid_json():
    """_safe_json should parse valid JSON."""
    result = _safe_json('{"level": 1, "signals": ["weak"]}', default={"level": 0})
    assert result["level"] == 1
    assert result["signals"] == ["weak"]


def test_safe_json_strips_code_fences():
    """_safe_json should handle ```json fenced blocks."""
    result = _safe_json('```json\n{"level": 2}\n```', default={"level": 0})
    assert result["level"] == 2


def test_safe_json_extracts_json_from_text():
    """_safe_json should find the first {...} block in noisy text."""
    result = _safe_json('Here is the result: {"level": 3, "signals": ["critical"]} done.', default={"level": 0})
    assert result["level"] == 3


def test_safe_json_returns_default_on_invalid_input():
    """_safe_json should return the default on completely invalid input."""
    result = _safe_json("not json at all", default={"level": 0, "fallback": True})
    assert result["level"] == 0
    assert result["fallback"] is True


def test_safe_json_returns_default_on_empty_string():
    """_safe_json should return the default on empty input."""
    result = _safe_json("", default={"empty": True})
    assert result["empty"] is True


def test_safe_json_handles_partial_json_gracefully():
    """_safe_json should not crash on truncated JSON."""
    result = _safe_json('{"level": 1, "signals":', default={"level": 0})
    assert result["level"] == 0


def test_slack_ai_service_init_with_openai_key():
    """SlackAIService should initialize with an OpenAI key as fallback."""
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["SLACK_AI_ENABLED"] = "false"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    svc = SlackAIService()
    assert svc.openai_key == "sk-test-key"
    assert svc.use_native_slack_ai is False


@pytest.mark.asyncio
async def test_slack_ai_classify_anomaly_uses_openai_fallback():
    """classify_anomaly should call OpenAI when Slack AI is unavailable."""
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["SLACK_AI_ENABLED"] = "false"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    svc = SlackAIService()

    # Mock the OpenAI client
    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"level": 2, "signals": ["unreachable"], "recommended": "escalade_coord", "confidence": 0.9}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    mock_client.close = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        level, signals, recommended = await svc.classify_anomaly("Pas de réponse après 3 appels")

    assert level == 2
    assert "unreachable" in signals
    assert recommended == "escalade_coord"


@pytest.mark.asyncio
async def test_slack_ai_classify_anomaly_clamps_level_to_valid_range():
    """classify_anomaly should clamp levels outside 0-3 to the valid range."""
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["SLACK_AI_ENABLED"] = "false"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    svc = SlackAIService()

    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"level": 7, "signals": [], "recommended": "ok"}'  # invalid level
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    mock_client.close = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        level, _, _ = await svc.classify_anomaly("test")

    assert level == 3  # clamped to max


@pytest.mark.asyncio
async def test_slack_ai_classify_anomaly_falls_back_for_invalid_recommended():
    """classify_anomaly should map invalid 'recommended' values to a safe default."""
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["SLACK_AI_ENABLED"] = "false"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    svc = SlackAIService()

    mock_client = AsyncMock()
    mock_choice = MagicMock()
    mock_choice.message.content = '{"level": 3, "signals": [], "recommended": "unknown_action"}'
    mock_resp = MagicMock()
    mock_resp.choices = [mock_choice]
    mock_client.chat.completions.create = AsyncMock(return_value=mock_resp)
    mock_client.close = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=mock_client):
        level, _, recommended = await svc.classify_anomaly("critical situation")

    assert level == 3
    assert recommended == "escalade_samu"  # mapped from level 3


@pytest.mark.asyncio
async def test_slack_ai_extract_structured_raises_on_api_failure():
    """extract_structured should raise if the LLM API is down.

    The caller (orchestrator) is responsible for catching the exception
    and providing a fallback. This is intentional: we want errors to be
    visible, not silently masked.
    """
    import os
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["SLACK_AI_ENABLED"] = "false"
    from app.utils import config as _config_mod
    _config_mod.get_config.cache_clear()

    svc = SlackAIService()

    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(side_effect=Exception("API down"))
    mock_client.close = AsyncMock()

    with patch("openai.AsyncOpenAI", return_value=mock_client), pytest.raises(Exception, match="API down"):
        await svc.extract_structured("test text")
