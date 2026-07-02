"""
Vigie — Configuration and settings.

Loads from environment variables with type-safe Pydantic models.
All secrets are read from .env, never hardcoded.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class SlackSettings(BaseSettings):
    """Slack app credentials and workspace configuration."""

    bot_token: SecretStr = Field(..., alias="SLACK_BOT_TOKEN")
    signing_secret: SecretStr = Field(..., alias="SLACK_SIGNING_SECRET")
    app_token: SecretStr | None = Field(None, alias="SLACK_APP_TOKEN")  # Socket Mode

    workspace_name: str = Field("Reseau-Soligarde-Paris", alias="SLACK_WORKSPACE_NAME")
    cellule_crise_channel_id: str | None = Field(None, alias="SLACK_CELLULE_CRISE_CHANNEL_ID")
    secteur_prefix: str = Field("secteur-", alias="SLACK_SECTEUR_PREFIX")
    voisins_prefix: str = Field("voisins-", alias="SLACK_VOISINS_PREFIX")
    num_sectors: int = Field(12, alias="SLACK_NUM_SECTORS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class SlackAISettings(BaseSettings):
    """Slack AI integration + LLM fallback."""

    enabled: bool = Field(True, alias="SLACK_AI_ENABLED")
    model: str = Field("claude-3-5-sonnet", alias="SLACK_AI_MODEL")

    # Fallback LLM (OpenAI-compatible)
    openai_api_key: SecretStr | None = Field(None, alias="OPENAI_API_KEY")
    openai_model: str = Field("gpt-4o-mini", alias="OPENAI_MODEL")
    openai_whisper_model: str = Field("whisper-1", alias="OPENAI_WHISPER_MODEL")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class MCPSettings(BaseSettings):
    """MCP server configuration."""

    transport: Literal["stdio", "sse", "streamable-http"] = Field(
        "streamable-http", alias="MCP_TRANSPORT"
    )
    host: str = Field("0.0.0.0", alias="MCP_HOST")
    port: int = Field(8000, alias="MCP_PORT")
    server_token: SecretStr = Field(..., alias="MCP_SERVER_TOKEN")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class RTSSettings(BaseSettings):
    """Real-Time Search API configuration."""

    api_endpoint: str | None = Field(None, alias="RTS_API_ENDPOINT")
    api_key: SecretStr | None = Field(None, alias="RTS_API_KEY")
    cache_ttl_seconds: int = Field(1800, alias="RTS_CACHE_TTL_SECONDS")
    refresh_interval_seconds: int = Field(1800, alias="RTS_REFRESH_INTERVAL_SECONDS")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class ExternalDataSettings(BaseSettings):
    """External API endpoints (Météo-France, NWS, OSM, INSEE)."""

    meteo_france_api_key: SecretStr | None = Field(None, alias="METEO_FRANCE_API_KEY")
    meteo_france_vigilance_url: str = Field(
        "https://public-api.meteofrance.fr/public/DPVigilance/v1/",
        alias="METEO_FRANCE_VIGILANCE_URL",
    )

    nws_api_base: str = Field("https://api.weather.gov", alias="NWS_API_BASE")
    nws_alerts_endpoint: str = Field("/alerts/active", alias="NWS_ALERTS_ENDPOINT")

    overpass_api_url: str = Field(
        "https://overpass-api.de/api/interpreter", alias="OVERPASS_API_URL"
    )

    insee_api_base: str = Field("https://api.insee.fr", alias="INSEE_API_BASE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class CacheSettings(BaseSettings):
    """Cache layer (Redis optional, SQLite fallback)."""

    redis_url: str | None = Field(None, alias="REDIS_URL")
    sqlite_cache_path: Path = Field(Path("./vigie_cache.db"), alias="SQLITE_CACHE_PATH")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class LoggingSettings(BaseSettings):
    """Logging configuration."""

    level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field("INFO", alias="LOG_LEVEL")
    format: Literal["json", "text"] = Field("json", alias="LOG_FORMAT")
    file: Path | None = Field(None, alias="LOG_FILE")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DemoSettings(BaseSettings):
    """Demo / simulation parameters."""

    num_beneficiaries: int = Field(50, alias="VIGIE_NUM_BENEFICIARIES")
    num_volunteers: int = Field(12, alias="VIGIE_NUM_VOLUNTEERS")
    heat_threshold_orange: float = Field(32.0, alias="VIGIE_HEAT_THRESHOLD_ORANGE")
    heat_threshold_red: float = Field(36.0, alias="VIGIE_HEAT_THRESHOLD_RED")
    scenario_path: Path = Field(
        Path("./mcp_server/data/scenario_canicule_juillet.json"),
        alias="VIGIE_SCENARIO_PATH",
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class DeploymentSettings(BaseSettings):
    """Deployment environment."""

    port: int = Field(3000, alias="PORT")
    railway_volume_mount_path: str | None = Field(None, alias="RAILWAY_VOLUME_MOUNT_PATH")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class SecuritySettings(BaseSettings):
    """Security configuration."""

    allowed_user_ids: list[str] = Field(default_factory=list, alias="VIGIE_ALLOWED_USER_IDS")
    data_encryption_key: SecretStr | None = Field(None, alias="VIGIE_DATA_ENCRYPTION_KEY")

    @field_validator("allowed_user_ids", mode="before")
    @classmethod
    def parse_user_ids(cls, v):
        if isinstance(v, str):
            return [uid.strip() for uid in v.split(",") if uid.strip()]
        return v or []

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


class VigieConfig:
    """Aggregate all settings in one accessor."""

    def __init__(self) -> None:
        self.slack = SlackSettings()
        self.slack_ai = SlackAISettings()
        self.mcp = MCPSettings()
        self.rts = RTSSettings()
        self.external = ExternalDataSettings()
        self.cache = CacheSettings()
        self.logging = LoggingSettings()
        self.demo = DemoSettings()
        self.deployment = DeploymentSettings()
        self.security = SecuritySettings()

    @property
    def base_dir(self) -> Path:
        return Path(__file__).resolve().parent.parent


@lru_cache(maxsize=1)
def get_config() -> VigieConfig:
    """Cached config accessor — loads once per process."""
    return VigieConfig()
