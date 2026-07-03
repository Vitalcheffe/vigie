.PHONY: help install dev-install test lint format typecheck clean run-bot run-mcp seed simulate docker-build docker-up docker-down

PYTHON := python3
PIP := pip
VENV := .venv

help:
	@echo "Vigie — Makefile"
	@echo ""
	@echo "Setup:"
	@echo "  make install        Install production dependencies"
	@echo "  make dev-install    Install dev dependencies (test, lint, typecheck)"
	@echo "  make venv           Create virtualenv"
	@echo ""
	@echo "Development:"
	@echo "  make run-bot        Start the Slack Bolt app"
	@echo "  make run-mcp        Start the MCP server"
	@echo "  make seed           Seed the sandbox workspace"
	@echo "  make simulate       Run the canicule simulation"
	@echo ""
	@echo "Quality:"
	@echo "  make test           Run pytest"
	@echo "  make lint           Run ruff linter"
	@echo "  make format         Format with ruff"
	@echo "  make typecheck      Run mypy"
	@echo ""
	@echo "Docker:"
	@echo "  make docker-build   Build the Docker image"
	@echo "  make docker-up      Run everything with docker-compose"
	@echo "  make docker-down    Stop docker-compose stack"
	@echo ""
	@echo "Misc:"
	@echo "  make clean          Remove build artifacts and caches"

venv:
	$(PYTHON) -m venv $(VENV)
	@echo "Virtualenv created at $(VENV). Activate with: source $(VENV)/bin/activate"

install:
	$(PIP) install -e .

dev-install:
	$(PIP) install -e ".[dev]"
	@echo "Dev dependencies installed. Pre-commit hooks can be set with: pre-commit install"

run-bot:
	$(PYTHON) -m app.main

run-mcp:
	$(PYTHON) -m mcp_server.server

seed:
	$(PYTHON) -m scripts.seed_sandbox

simulate:
	$(PYTHON) -m scripts.simulate_canicule --accelerated

test:
	$(PYTHON) -m pytest

lint:
	$(PYTHON) -m ruff check app mcp_server scripts tests

format:
	$(PYTHON) -m ruff format app mcp_server scripts tests
	$(PYTHON) -m ruff check --fix app mcp_server scripts tests

typecheck:
	$(PYTHON) -m mypy app mcp_server

clean:
	rm -rf build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	rm -f vigie_cache.db
	rm -rf logs/

docker-build:
	docker build -t vigie:latest .

docker-up:
	docker compose up -d

docker-down:
	docker compose down
