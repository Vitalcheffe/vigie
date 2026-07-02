"""
Vigie — Structured logging setup.

Uses structlog for JSON-formatted logs that play nice with Railway / Render
log streams and observability tools.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any

import structlog

from app.utils.config import get_config


def setup_logging() -> structlog.stdlib.BoundLogger:
    """
    Configure structured logging for the entire Vigie application.

    Returns a bound logger that can be used as:
        log = setup_logging()
        log.info("vigie.started", bot_user="U123", workspace="Reseau-Soligarde-Paris")
    """
    cfg = get_config().logging

    # Shared processors for both structlog and stdlib logging
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if cfg.format == "json":
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(cfg.level)

    # Replace any existing handlers
    for handler in list(root_logger.handlers):
        root_logger.removeHandler(handler)

    # stdout handler (Railway / Render capture stdout)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    root_logger.addHandler(stdout_handler)

    # Optional file handler
    if cfg.file:
        cfg.file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(cfg.file)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # Reduce noise from libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("slack_bolt").setLevel(logging.INFO)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    log = structlog.get_logger("vigie")
    log.info(
        "logging.configured",
        level=cfg.level,
        format=cfg.format,
        file=str(cfg.file) if cfg.file else None,
    )
    return log


def get_logger(name: str = "vigie") -> structlog.stdlib.BoundLogger:
    """Get a child logger bound with the given name."""
    return structlog.get_logger(name)
