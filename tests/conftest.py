"""Pytest configuration — shared fixtures and env setup for tests."""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Set test environment variables BEFORE any vigie module is imported.
# This allows the Pydantic settings to load without requiring real Slack creds.
_TEST_ENV = {
    "SLACK_BOT_TOKEN": "xoxb-test-bot-token",
    "SLACK_SIGNING_SECRET": "test-signing-secret",
    "SLACK_APP_TOKEN": "xapp-test-app-token",
    "SLACK_WORKSPACE_NAME": "Test-Workspace",
    "SLACK_NUM_SECTORS": "12",
    "MCP_SERVER_TOKEN": "test-mcp-token",
    "MCP_TRANSPORT": "stdio",
    "LOG_LEVEL": "WARNING",
    "LOG_FORMAT": "text",
    "VIGIE_NUM_BENEFICIARIES": "50",
    "VIGIE_NUM_VOLUNTEERS": "12",
}

for key, value in _TEST_ENV.items():
    os.environ.setdefault(key, value)

# Make sure the project root is on the path
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# Clear the config cache so test env vars take effect
from app.utils import config as _config_mod  # noqa: E402

_config_mod.get_config.cache_clear()
