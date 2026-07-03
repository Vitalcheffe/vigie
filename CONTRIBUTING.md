# Contributing to Vigie

Thanks for considering a contribution. Vigie is a small project with a specific scope (Slack agent for elder watch during heatwaves), so this guide is short.

## Setup

```bash
git clone https://github.com/Vitalcheffe/vigie.git
cd vigie
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pre-commit install
cp .env.example .env  # then fill in your credentials
```

## Running locally

```bash
make run-mcp    # MCP server (terminal 1)
make run-bot    # Slack Bolt app (terminal 2)
```

## Code style

- Python 3.11+, type hints required on public functions.
- `ruff` for lint + format (line length 100).
- `mypy --strict` should pass on `app/` and `mcp_server/`.
- Tests in `tests/` mirroring the source structure.
- Docstrings: Google style, concise. No marketing fluff.

## Commit messages

Conventional commits, please:

```
feat(scope): summary
fix(scope): summary
docs: summary
test: summary
chore: summary
```

## Scope

Vigie intentionally stays narrow. Pull requests adding unrelated features (general-purpose chatbot, web dashboard, mobile app) will be declined. If you're unsure, open an issue first.

## Ethical note

No real beneficiary data should ever land in this repository. All test fixtures are simulated. If you contribute code that touches beneficiary records, make sure it never logs PII and never persists real personal data.
